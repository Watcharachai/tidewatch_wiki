"""GLD965 next-bar five-period moving-average price experiment, nested chronological waterfall."""
import json, hashlib, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, ParameterGrid
from sklearn.linear_model import Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMRegressor
from model1_baseline import vif_diagnostics, varclus_diagnostics, block_permutation, block_bootstrap, score
from prepare_baseline import ewma_sigma
from render_model_summary import render
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'training_artifacts/_training_baseline/model1_15m_priceMA'
CONFIG={'target':'Y(t+1) = mean(P[t-3],P[t-2],P[t-1],P[t],P[t+1]); five contiguous 15m closes', 'target_scaling':'fold-training mean/std; forecasts inverted to original THB quote units',
 'Z_return_lag5':'one-bar log return five observed MTS bars ago / sigma at that historical bar; clipped [-5,5]',
 'outer_folds':4,'embargo_context_bars':30,'ewma_half_life':30,'null_threshold':.2,'vif_threshold':10,
 'varclus_top_per_cluster':3,'permutation_top_max':45,'seed':42,
 'selection':'inner training diagnostics; separate chronological selection and tuning blocks inside outer training',
 'source_lags':'existing source lag fields shifted one additional MTS row: all X ends strictly before decision bar',
 'near_zero_band':.05}

from model1_15m_waterfall import prepare as prepare_returns, labels as return_labels

def prepare():
 f,candidates,numeric,source=prepare_returns()
 # All five prices must form contiguous 15m bars; no rolling window crosses a session gap.
 contiguous=f.decision_at.diff().eq(pd.Timedelta(minutes=15))
 ma=f.close.rolling(5,min_periods=5).mean().where(contiguous.rolling(4,min_periods=4).sum().eq(4))
 f['ma5_current']=ma
 f['y_ma5']=ma.shift(-1).where(contiguous.shift(-1).fillna(False) & ma.notna())
 f['structural_persistence']=(f.close.rolling(4,min_periods=4).sum()+f.close)/5
 f['price_persistence']=f.close
 return f,candidates,numeric,source

def labels(f,fit_indices):
 x,seed=return_labels(f,fit_indices)
 target=x.loc[fit_indices,'y_ma5'].dropna()
 center=float(target.mean());scale=float(target.std(ddof=0))
 if not scale>0:raise ValueError('Target has no training variation')
 x['y_scaled']=(x.y_ma5-center)/scale
 x.attrs.update(target_mean=center,target_scale=scale)
 return x,seed

def matured(f,indices,end):
 return np.array([i for i in indices if pd.notna(f.loc[i,'y_ma5']) and f.loc[i,'label_at']<end])

def estimator(kind,params):
 if kind=='Lasso':return Lasso(max_iter=30000,tol=1e-5,**params)
 if kind=='ElasticNet':return ElasticNet(max_iter=30000,tol=1e-5,**params)
 return LGBMRegressor(objective='huber',max_depth=3,num_leaves=7,n_jobs=1,verbosity=-1,random_state=42,**params)

GRIDS={'Lasso':{'alpha':[.001,.01,.1]},'ElasticNet':{'alpha':[.001,.01,.1],'l1_ratio':[.25,.75]},
 'LightGBMRegressor':{'n_estimators':[100,250],'learning_rate':[.03,.07],'min_child_samples':[50,150]}}

def preprocess(train,other,cols):
 med=train[cols].median().fillna(0);scale=StandardScaler().fit(train[cols].fillna(med))
 return scale.transform(train[cols].fillna(med)),scale.transform(other[cols].fillna(med)),med,scale

def run():
 OUT.mkdir(parents=True,exist_ok=True)
 f,candidates,numeric,source=prepare(); tables={k:[] for k in ['waterfall','null_variance','varclus','vif','permutation','tuning','fold_metrics','predictions','selected_features','schedule']}
 for fold,(outer_train,outer_test) in enumerate(TimeSeriesSplit(n_splits=4,gap=30).split(f),1):
  print('Fold',fold,'start',flush=True)
  # Three ordered inner portions: diagnostic fit, permutation ranking, parameter tuning.
  n=len(outer_train); a=int(n*.60);b=int(n*.80)
  fit_ids=outer_train[:a]; select_ids=outer_train[a+30:b];tune_ids=outer_train[b+30:]
  fit_ids=matured(f,fit_ids,f.loc[a,'decision_at'])
  inner,inner_seed=labels(f,fit_ids)
  fit_ids=matured(inner,fit_ids,f.loc[a,'decision_at']);select_ids=matured(inner,select_ids,f.loc[b,'decision_at'])
  tune_ids=matured(inner,tune_ids,f.loc[outer_train[-1],'decision_at'])
  tr=inner.loc[fit_ids];sel=inner.loc[select_ids];tun=inner.loc[tune_ids]
  cols=candidates.copy()
  def stage(name,before,after):
   tables['waterfall'].append({'fold':fold,'stage':name,'before':len(before),'after':len(after),'dropped':len(before)-len(after),'dropped_features':';'.join(c for c in before if c not in after)})
  stage('1 strictly lagged inputs',list(dict.fromkeys(numeric+cols)),cols)
  quality=pd.DataFrame({'feature':cols,'null_rate':tr[cols].isna().mean().values,'variance':tr[cols].var().values,'unique':tr[cols].nunique().values})
  tables['null_variance'].append(quality.assign(fold=fold))
  before=cols;cols=quality.loc[quality.null_rate.lt(.2),'feature'].tolist();stage('2 null >=20%',before,cols)
  before=cols;cols=[c for c in cols if tr[c].nunique()>1];stage('3 zero variance',before,cols)
  vc,_=varclus_diagnostics(tr[cols]);vc['fold']=fold
  chosen=vc.sort_values(['cluster','r2_ratio','feature']).groupby('cluster').head(3).feature.tolist()
  vc['selected_top3']=vc.feature.isin(chosen);tables['varclus'].append(vc)
  before=cols;cols=chosen;stage('4 VARCLUS top 3 per cluster',before,cols)
  before=cols.copy();iteration=0
  while True:
   v=vif_diagnostics(tr[cols]);v['iteration']=iteration;v['fold']=fold;v['dropped_this_iteration']=False
   high=v.loc[v.vif.gt(10)].sort_values(['vif','feature'],ascending=[False,True])
   if high.empty:
    tables['vif'].append(v);break
   drop=high.feature.iloc[0];v.loc[v.feature.eq(drop),'dropped_this_iteration']=True;tables['vif'].append(v)
   cols.remove(drop);iteration+=1
  stage('5 iterative VIF >10',before,cols)
  A,B,_,_=preprocess(tr,sel,cols);lasso=estimator('Lasso',{'alpha':.01}).fit(A,tr.y_scaled)
  pi=block_permutation(B,sel.y_scaled.to_numpy(),lasso.predict(B),lasso.coef_,cols,42+fold)
  pi=pi.sort_values(['importance_mean','feature'],ascending=[False,True]);selected=pi.head(45).feature.tolist()
  pi['selected']=pi.feature.isin(selected);pi['fold']=fold;tables['permutation'].append(pi)
  before=cols;cols=selected;stage('6 Lasso permutation top up to 45',before,cols)
  if not cols:raise ValueError('Waterfall left no features')
  tables['selected_features'].append(pd.DataFrame({'fold':fold,'feature':cols}))
  A,T,_,_=preprocess(tr,tun,cols)
  outer_train_matured=matured(f,outer_train,f.loc[outer_train[-1],'decision_at']+pd.Timedelta(minutes=15))
  full,outer_seed=labels(f,outer_train_matured)
  train_ids=matured(full,outer_train,f.loc[outer_train[-1],'decision_at']+pd.Timedelta(minutes=15))
  test_ids=matured(full,outer_test,f.loc[outer_test[-1],'decision_at']+pd.Timedelta(minutes=15))
  train,test=full.loc[train_ids],full.loc[test_ids]
  X,V,med,scale=preprocess(train,test,cols)
  tables['schedule'].append(pd.DataFrame([dict(fold=fold,train_rows=len(train),selection_fit_rows=len(tr),permutation_rows=len(sel),tuning_rows=len(tun),test_rows=len(test),train_end=str(train.decision_at.max()),test_start=str(test.decision_at.min()),test_end=str(test.decision_at.max()),inner_seed=inner_seed,outer_seed=outer_seed,features=len(cols))]))
  for kind in ['MA_persistence','structural_persistence','price_persistence','train_mean',*GRIDS]:
   if kind not in GRIDS:
    raw_pred={'MA_persistence':test.ma5_current.to_numpy(),'structural_persistence':test.structural_persistence.to_numpy(),'price_persistence':test.close.to_numpy(),'train_mean':np.full(len(test),full.attrs['target_mean'])}[kind];params={}
   else:
    trials=[]
    for params in ParameterGrid(GRIDS[kind]):
     model=estimator(kind,params).fit(A,tr.y_scaled);loss=float(np.mean((tun.y_scaled-model.predict(T))**2))
     row=dict(fold=fold,model=kind,parameters=json.dumps(params),tuning_mse_scaled=loss);trials.append((loss,params));tables['tuning'].append(row)
    _,params=min(trials,key=lambda q:q[0]);model=estimator(kind,params).fit(X,train.y_scaled);pred=model.predict(V)
    fitted={'target_mean':full.attrs['target_mean'],'target_scale':full.attrs['target_scale'],'features':cols,'medians':med.to_list(),'means':scale.mean_.tolist(),'scales':scale.scale_.tolist(),'parameters':params,'ewma_seed':outer_seed}
    if kind=='LightGBMRegressor':model.booster_.save_model(str(OUT/f'fold{fold}_{kind}.txt'))
    else:fitted.update(coefficients=model.coef_.tolist(),intercept=float(model.intercept_))
    (OUT/f'fold{fold}_{kind}.json').write_text(json.dumps(fitted,indent=2)+'\n')
    raw_pred=pred*full.attrs['target_scale']+full.attrs['target_mean']
   for partition,actual,prediction,baseline in [('validation',test.y_ma5,raw_pred,test.structural_persistence)]:
    tables['fold_metrics'].append(dict(fold=fold,model=kind,partition=partition,parameters=json.dumps(params),**price_score(actual,prediction,baseline)))
   if kind in GRIDS:
    train_pred=model.predict(X)*full.attrs['target_scale']+full.attrs['target_mean']
    tables['fold_metrics'].append(dict(fold=fold,model=kind,partition='train',parameters=json.dumps(params),**price_score(train.y_ma5,train_pred,train.structural_persistence)))
   p=test[['decision_at','label_at','close','ma5_current','structural_persistence','y_ma5']].copy();p['y_hat']=raw_pred;p['model']=kind;p['fold']=fold
   tables['predictions'].append(p)
  print('Fold',fold,'complete, selected',len(cols),flush=True)
 results={k:pd.concat(v,ignore_index=True) if v and isinstance(v[0],pd.DataFrame) else pd.DataFrame(v) for k,v in tables.items()}
 p=results['predictions'];summaries=[];comparisons=[]
 for kind,g in p.groupby('model'):
  row=dict(model=kind,**price_score(g.y_ma5,g.y_hat,g.structural_persistence))
  row.update(loss_ci(g,g.structural_persistence));summaries.append(row)
 results['summary']=pd.DataFrame(summaries)
 names=list(GRIDS)
 for i,first in enumerate(names):
  for second in names[i+1:]:
   q=p[p.model.eq(first)].merge(p[p.model.eq(second)],on=['fold','decision_at'],suffixes=('_a','_b'))
   comparisons.append(dict(first=first,second=second,**loss_ci(q.rename(columns={'y_ma5_a':'y_ma5','y_hat_a':'y_hat'}),q.y_hat_b)))
 results['pairwise_comparison']=pd.DataFrame(comparisons)
 export(results,source,f)
 return results

def price_score(actual,pred,baseline):
 a,p,b=np.asarray(actual),np.asarray(pred),np.asarray(baseline)
 mse=float(np.mean((a-p)**2));base=float(np.mean((a-b)**2));den=float(np.sum((a-a.mean())**2))
 return dict(rows=len(a),RMSE=np.sqrt(mse),MAE=float(np.abs(a-p).mean()),R2=1-float(np.sum((a-p)**2))/den if den else np.nan,
             MSE=mse,skill_vs_structural=1-mse/base if base else np.nan)

def loss_ci(g,baseline):
 a=np.asarray(g.y_ma5);pred=np.asarray(g.y_hat);base=np.asarray(baseline)
 # Reuse paired block-bootstrap on equivalent errors; only loss-improvement output is retained.
 errors=pd.DataFrame({'fold':g.fold.to_numpy(),'y_z':a-base,'z_hat':pred-base})
 ci=block_bootstrap(errors)
 return {k:v for k,v in ci.items() if not k.startswith('r2_')}

def export(results,source,frame):
 import importlib.metadata
 p=results['predictions']
 for name,d in results.items():d.to_csv(OUT/(name+'.csv.gz' if name=='predictions' else name+'.csv'),index=False)
 # Fold-specific train-scaled targets and feature schema can be reproduced with labels().
 frame.to_csv(OUT/'prepared_X_y_context.csv.gz',index=False)
 with pd.ExcelWriter(OUT/'GLD965_15m_priceMA_Review.xlsx',engine='xlsxwriter') as w:
  pd.DataFrame([(k,str(v)) for k,v in CONFIG.items()],columns=['setting','value']).to_excel(w,sheet_name='Protocol',index=False)
  for name,d in results.items():
   d=d.copy()
   for c in d:
    if isinstance(d[c].dtype,pd.DatetimeTZDtype):d[c]=d[c].astype(str)
   d.to_excel(w,sheet_name=name[:31],index=False,inf_rep='inf');sheet=w.sheets[name[:31]];sheet.freeze_panes(1,0);sheet.autofilter(0,0,len(d),len(d.columns)-1);sheet.set_column(0,len(d.columns)-1,23)
 fig,axes=plt.subplots(3,2,figsize=(12,10),constrained_layout=True)
 for row,kind in enumerate(GRIDS):
  q=p[p.model.eq(kind)];low=min(q.y_ma5.min(),q.y_hat.min());high=max(q.y_ma5.max(),q.y_hat.max())
  axes[row,0].scatter(q.y_ma5,q.y_hat,s=2,alpha=.15);axes[row,0].plot([low,high],[low,high],'k--');axes[row,0].set(title=kind,xlabel='Actual next MA5 (THB quote)',ylabel='Predicted MA5 (THB quote)')
  tail=q.tail(200);axes[row,1].plot(tail.decision_at,tail.y_ma5,label='Actual');axes[row,1].plot(tail.decision_at,tail.y_hat,label='Predicted');axes[row,1].plot(tail.decision_at,tail.structural_persistence,label='Structural baseline',alpha=.5);axes[row,1].legend(fontsize=7);axes[row,1].tick_params(axis='x',rotation=30)
 fig.savefig(OUT/'predicted_actual.png',dpi=130);plt.close(fig)
 summary=results['summary'][['model','RMSE','MAE','R2','skill_vs_structural','mse_improvement_ci_low','mse_improvement_ci_high']].copy()
 summary.columns=['Model','RMSE','MAE','R2','Skill vs structural','Gain CI low','Gain CI high']
 waterfall=results['waterfall'].pivot(index='stage',columns='fold',values='after')
 lines=['# GLD965 15m: next-bar MA5 price forecast','',
 'Y(t+1) = [P(t-3)+P(t-2)+P(t-1)+P(t)+P(t+1)]/5. Decisions occur after bar t completes. This forecasts the next trailing five-bar average, rather than the average of five entirely future bars. Both the current and next five-bar windows must be contiguous 15-minute observations; session gaps and unmatured boundary labels are excluded. All price errors use original THB quote units.','',
 '## Design','',
 'The previous 15m lag-only feature design is retained: 196 candidates including fold-seeded Z_return_lag5, lagged source prices/returns/volumes and lagged rolling return moments. Drop null rate >=20%, zero variance, retain three candidates per VARCLUS cluster by smallest R-squared ratio, iteratively remove the largest VIF >10, then retain up to 45 by Lasso block-permutation importance. These are fold-local decisions. This experiment changes the target; it does not implement the previously suggested feature-timing ablations.','',
 'Four outer TimeSeriesSplit folds use 30 context bars of embargo. Inside each outer training window, the first 60% fits diagnostics and preprocessing, the next 20% ranks permutation importance, and the final 20% tunes hyperparameters, with 30-bar gaps. Each label must mature within its segment. Selected features and winning models are refitted on outer training only. Target mean and standard deviation are fitted on training labels only, independently for inner and outer fits; predictions are inverted to price units. This scaling keeps the previous regularization grids comparable. EWMA is used only for the historical Z lag input.','',
 '## Baselines and interpretation','',
 'Structural persistence predicts [P(t-3)+P(t-2)+P(t-1)+2*P(t)]/5, obtained by assuming P(t+1)=P(t). MA persistence predicts MA5(t). Price persistence predicts P(t); training mean predicts the fold-training target mean. Four of five target closes are already known at decision time. High conventional price-level R2 therefore does not demonstrate return predictability. Structural-baseline error equals [P(t+1)-P(t)]/5. Skill against this baseline is the principal measure; zero skill matches it.','',
 '## Out-of-fold results','',summary.to_markdown(index=False),'',
 '## Result interpretation','',
 f"Structural persistence has RMSE {results['summary'].set_index('model').loc['structural_persistence','RMSE']:.2f} THB quote units. The best fitted model has RMSE {results['summary'].loc[results['summary'].model.isin(GRIDS),'RMSE'].min():.2f}. Compare these errors before interpreting conventional price-level R2. All fitted models in this run perform worse than structural persistence; their gain confidence intervals are negative. The known four-price component makes persistence especially strong. Regularization, lag-only inputs and price-level extrapolation can leave fitted levels far from recent quotes; fold train/validation metrics expose this.",'',
 'The 95% intervals are paired circular block-bootstrap intervals of MSE improvement against structural persistence: 1,000 samples of 30 observations within folds. A positive lower bound is required to claim improvement. Pairwise comparisons are exploratory, without multiple-comparison correction. Train and validation scores are exported separately.','',
 '## Waterfall survivors','',waterfall.to_markdown(),'','![Predicted versus actual price MA5](predicted_actual.png)','',
 '## Limits and next steps','',
 'This is a price-level task and its R2 cannot be compared directly with the earlier return-target R2. LightGBM trees may struggle to extrapolate price levels above their training range. The retained lag-only rule excludes the freshest completed return and synchronized current references. A fixed top-45 list can include zero or negative permutation importance. Daily macro release timing is assumed; gold-reference coverage remains uneven. These are development folds across 2025–2026, with no untouched final holdout after inspection. Plot timestamps are UTC.','',
 'Before changing the target again, compare errors with structural persistence and inspect fold-specific train/validation gaps. A residual experiment forecasting the unknown next-price innovation can distinguish learning future moves from reconstructing the known part of this moving average.','']
 md=OUT/'GLD965_15m_priceMA_Report.md';md.write_text('\n'.join(lines).rstrip()+'\n');render(md,md.with_suffix('.docx'))
 # Snapshot the driver and dependency specifications with all generated artifacts.
 import shutil
 shutil.copy2(__file__,OUT/'experiment_source.py')
 manifest={'config':CONFIG,'grids':GRIDS,'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'context_rows':len(frame),'target_valid_rows':int(frame.y_ma5.notna().sum()),'versions':{k:importlib.metadata.version(k) for k in ['numpy','pandas','scikit-learn','lightgbm','varclushi']}}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(results['summary'].to_string(index=False),flush=True)

if __name__=='__main__':run()
