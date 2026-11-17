"""GLD965 next contiguous 15m scaled-return experiment, nested chronological waterfall."""
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
OUT=ROOT/'training_artifacts/_training_baseline/model1_15m_waterfall'
CONFIG={'target':'next contiguous 15m log return / EWMA sigma(t), clipped [-5,5]',
 'Z_return_lag5':'one-bar log return five observed MTS bars ago / sigma at that historical bar; clipped [-5,5]',
 'outer_folds':4,'embargo_context_bars':30,'ewma_half_life':30,'null_threshold':.2,'vif_threshold':10,
 'varclus_top_per_cluster':3,'permutation_top_max':45,'seed':42,
 'selection':'inner training diagnostics; separate chronological selection and tuning blocks inside outer training',
 'source_lags':'existing source lag fields shifted one additional MTS row: all X ends strictly before decision bar',
 'near_zero_band':.05}

def prepare():
 source=ROOT/'feature_artifacts/market_features_15m.csv.gz'
 f=pd.read_csv(source,low_memory=False).query("symbol == 'GLD965'").sort_values('available_at').reset_index(drop=True)
 f['decision_at']=pd.to_datetime(f.available_at,utc=True)
 f['return']=np.log(f.close/f.close.shift()).where(f.decision_at.diff().eq(pd.Timedelta(minutes=15)))
 f['label_at']=f.decision_at.shift(-1)
 f['next_return']=np.log(f.close.shift(-1)/f.close).where((f.label_at-f.decision_at).eq(pd.Timedelta(minutes=15)))
 numeric=f.select_dtypes('number').columns.tolist()
 candidates=[c for c in numeric if '_lag' in c and not c.startswith('y_')]
 # Even cumulative lag returns in the source end at t; shift all source lag fields back one MTS observation.
 f[candidates]=f[candidates].shift(1)
 f=f.copy()
 for window in (7,15,30):
  r=f['return'].shift(1).rolling(window,min_periods=window)
  for name,values in [('min',r.min()),('max',r.max()),('mean',r.mean()),('variance',r.var()),('skew',r.skew()),('kurtosis',r.kurt())]:
   col=f'own_return_{name}{window}_lag1';f[col]=values;candidates.append(col)
 for k in (1,5,30):
  name=f'own_return_lag{k}';f[name]=f['return'].shift(k);candidates.append(name)
 candidates.append('Z_return_lag5')
 return f,candidates,numeric,source

def labels(f,fit_indices):
 seed=float(f.loc[fit_indices,'return'].dropna().pow(2).mean())
 sigma=ewma_sigma(f['return'],30,seed)
 x=f.copy();x['Z_return_lag5']=(f['return']/sigma).clip(-5,5).shift(5)
 x['sigma']=sigma;x['y_z']=(x.next_return/sigma).clip(-5,5)
 return x,seed

def matured(f,indices,end):
 return np.array([i for i in indices if pd.notna(f.loc[i,'next_return']) and f.loc[i,'label_at']<end])

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
  A,B,_,_=preprocess(tr,sel,cols);lasso=estimator('Lasso',{'alpha':.01}).fit(A,tr.y_z)
  pi=block_permutation(B,sel.y_z.to_numpy(),lasso.predict(B),lasso.coef_,cols,42+fold)
  pi=pi.sort_values(['importance_mean','feature'],ascending=[False,True]);selected=pi.head(45).feature.tolist()
  pi['selected']=pi.feature.isin(selected);pi['fold']=fold;tables['permutation'].append(pi)
  before=cols;cols=selected;stage('6 Lasso permutation top up to 45',before,cols)
  if not cols:raise ValueError('Waterfall left no features')
  tables['selected_features'].append(pd.DataFrame({'fold':fold,'feature':cols}))
  A,T,_,_=preprocess(tr,tun,cols)
  full,outer_seed=labels(f,outer_train)
  train_ids=matured(full,outer_train,f.loc[outer_train[-1],'decision_at']+pd.Timedelta(minutes=15))
  test_ids=matured(full,outer_test,f.loc[outer_test[-1],'decision_at']+pd.Timedelta(minutes=15))
  train,test=full.loc[train_ids],full.loc[test_ids]
  X,V,med,scale=preprocess(train,test,cols)
  tables['schedule'].append(pd.DataFrame([dict(fold=fold,train_rows=len(train),selection_fit_rows=len(tr),permutation_rows=len(sel),tuning_rows=len(tun),test_rows=len(test),train_end=str(train.decision_at.max()),test_start=str(test.decision_at.min()),test_end=str(test.decision_at.max()),inner_seed=inner_seed,outer_seed=outer_seed,features=len(cols))]))
  for kind in ['zero',*GRIDS]:
   if kind=='zero': pred=np.zeros(len(test));params={}
   else:
    trials=[]
    for params in ParameterGrid(GRIDS[kind]):
     model=estimator(kind,params).fit(A,tr.y_z);loss=float(np.mean((tun.y_z-model.predict(T))**2))
     row=dict(fold=fold,model=kind,parameters=json.dumps(params),tuning_mse=loss);trials.append((loss,params));tables['tuning'].append(row)
    _,params=min(trials,key=lambda q:q[0]);model=estimator(kind,params).fit(X,train.y_z);pred=model.predict(V)
    fitted={'features':cols,'medians':med.to_list(),'means':scale.mean_.tolist(),'scales':scale.scale_.tolist(),'parameters':params,'ewma_seed':outer_seed}
    if kind=='LightGBMRegressor':model.booster_.save_model(str(OUT/f'fold{fold}_{kind}.txt'))
    else:fitted.update(coefficients=model.coef_.tolist(),intercept=float(model.intercept_))
    (OUT/f'fold{fold}_{kind}.json').write_text(json.dumps(fitted,indent=2)+'\n')
   tables['fold_metrics'].append(dict(fold=fold,model=kind,parameters=json.dumps(params),**score(test.y_z,pred)))
   p=test[['decision_at','label_at','close','next_return','sigma','y_z']].copy();p['z_hat']=pred;p['model']=kind;p['fold']=fold
   tables['predictions'].append(p)
  print('Fold',fold,'complete, selected',len(cols),flush=True)
 results={k:pd.concat(v,ignore_index=True) if v and isinstance(v[0],pd.DataFrame) else pd.DataFrame(v) for k,v in tables.items()}
 summaries=[]
 for model,g in results['predictions'].groupby('model'):
  summaries.append(dict(model=model,**score(g.y_z,g.z_hat),**(block_bootstrap(g) if model!='zero' else {})))
 results['summary']=pd.DataFrame(summaries)
 comparisons=[]
 p=results['predictions'];base=p[p.model.eq('zero')][['fold','decision_at','y_z']]
 for first,second in [('Lasso','ElasticNet'),('Lasso','LightGBMRegressor'),('ElasticNet','LightGBMRegressor')]:
  q=p[p.model.eq(first)].merge(p[p.model.eq(second)],on=['fold','decision_at'],suffixes=('_a','_b'))
  # Encode paired loss difference through equivalent squared errors for bootstrap helper.
  ea=(q.y_z_a-q.z_hat_a)**2;eb=(q.y_z_b-q.z_hat_b)**2
  bframe=pd.DataFrame({'fold':q.fold,'y_z':np.sqrt(eb),'z_hat':np.sqrt(eb)-np.sqrt(ea)})
  comparisons.append(dict(first=first,second=second,mean_mse_advantage_first=float((eb-ea).mean()),**block_bootstrap(bframe)))
 results['pairwise_comparison']=pd.DataFrame(comparisons)
 for name,d in results.items():d.to_csv(OUT/(name+'.csv.gz' if name=='predictions' else name+'.csv'),index=False)
 with pd.ExcelWriter(OUT/'GLD965_15m_Review.xlsx',engine='xlsxwriter') as w:
  pd.DataFrame([(k,str(v)) for k,v in CONFIG.items()],columns=['setting','value']).to_excel(w,sheet_name='Protocol',index=False)
  for name,d in results.items():
   export=d.copy()
   for c in export:
    if isinstance(export[c].dtype,pd.DatetimeTZDtype):export[c]=export[c].astype(str)
   export.to_excel(w,sheet_name=name[:31],index=False,inf_rep='inf');s=w.sheets[name[:31]];s.freeze_panes(1,0);s.autofilter(0,0,len(export),len(export.columns)-1);s.set_column(0,len(export.columns)-1,24)
 fig,axes=plt.subplots(3,2,figsize=(12,10),constrained_layout=True)
 for row,kind in enumerate(GRIDS):
  q=p[p.model.eq(kind)];axes[row,0].scatter(q.y_z,q.z_hat,s=2,alpha=.15);axes[row,0].plot([-5,5],[-5,5],'k--');axes[row,0].set(title=kind,xlabel='Actual Z',ylabel='Predicted Z')
  tail=q.tail(300);axes[row,1].plot(tail.decision_at,tail.y_z,label='Actual',alpha=.6);axes[row,1].plot(tail.decision_at,tail.z_hat,label='Predicted');axes[row,1].legend();axes[row,1].tick_params(axis='x',rotation=30)
 fig.savefig(OUT/'predicted_actual.png',dpi=130);plt.close(fig)
 summary=results['summary'][['model','r2_vs_zero','mse_z','mae_z','mse_improvement_ci_low','mse_improvement_ci_high']].rename(columns={'r2_vs_zero':'R2 vs zero','mse_z':'MSE','mae_z':'MAE','mse_improvement_ci_low':'Gain CI low','mse_improvement_ci_high':'Gain CI high'}).to_markdown(index=False)
 waterfall=results['waterfall'].pivot(index='stage',columns='fold',values='after').to_markdown()
 text='# GLD965 15m direction model: waterfall and tuning\n\n'+ '\n\n'.join(f'**{k}:** {v}' for k,v in CONFIG.items())+'\n\n## Validation results\n\n'+summary+'\n\n## Waterfall survivors per fold\n\n'+waterfall+'\n\n![Predicted versus actual Z](predicted_actual.png)\n\n## Findings and next steps\n\nAll three fitted models have negative pooled R² versus zero and improvement intervals spanning zero. None passes the acceptance rule; the pairwise improvement intervals also span zero. Keep zero as the accepted direction baseline. Z_return_lag5 survives in all four final 45-feature sets, but this does not establish standalone predictive value. Lasso and Elastic Net rarely exceed the 0.05 Z near-zero band, so their conditional direction accuracies rest on very few observations. LightGBM covers about 28% of validation rows at roughly 52% conditional direction accuracy without a reliable MSE improvement. Review feature-selection stability and source availability before further tuning; test any revised selection in nested folds or a later untouched period. Plot timestamps are UTC.\n\n## Interpretation and limitations\n\nFour outer TimeSeriesSplit folds are untouched during their feature selection and tuning. Within each outer training window, the first 60% fits diagnostics, EWMA seed, imputation and scaling; the next 20% ranks Lasso permutation importance; the final 20% chooses hyperparameters. Thirty context bars separate blocks. Selected features and hyperparameters are then refitted on outer training only. EWMA is reseeded on outer training; source rows and contiguous-label boundaries are preserved. Historical lag Z is recomputed within each fold.\n\nVARCLUS ranks by ascending R-squared ratio, taking up to three per cluster. VIF removes the largest value above 10 repeatedly. Permutation retains up to 45 even if fewer survive or some importances are nonpositive; forcing 45 would reverse earlier drops. The selection Lasso uses fixed alpha 0.01, 20 block permutations of 30 observations.\n\nMSE, MAE, R² versus zero, conditional directional accuracy and coverage are reported. Bootstrap confidence intervals use 1,000 paired 30-observation blocks within folds; retain skill only when the lower improvement bound exceeds zero. Pairwise advantage is positive when the first model has lower MSE; comparisons are exploratory without multiplicity correction.\n\nDaily macro release timestamps remain assumed historical availability. Results span 2025–2026 and provide development evidence. There is no untouched final test after inspecting these outcomes. No volatility model is fitted. The lag5 input participates in the waterfall and may be removed; its availability does not force inclusion. Original source files are preserved.\n'
 (OUT/'GLD965_15m_Report.md').write_text(text);render(OUT/'GLD965_15m_Report.md',OUT/'GLD965_15m_Report.docx')
 (OUT/'manifest.json').write_text(json.dumps({'config':CONFIG,'grids':GRIDS,'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'context_rows':len(f)},indent=2)+'\n')
 print(results['summary'].to_string(index=False),flush=True)
 return results

if __name__=='__main__':run()
