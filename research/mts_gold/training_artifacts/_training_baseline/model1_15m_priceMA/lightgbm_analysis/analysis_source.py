"""Audit saved MA5 LightGBM folds; reproduce original tuning, never select on outer results."""
from pathlib import Path
import json,hashlib,itertools,shutil
import numpy as np
import pandas as pd
from lightgbm import Booster
from sklearn.model_selection import TimeSeriesSplit
from model1_15m_priceMA import OUT,prepare,labels,matured,preprocess,estimator,loss_ci,price_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DEST=OUT/'lightgbm_analysis'
REPEATS=20

def blocked_indices(n,rng):
 blocks=[np.arange(i,min(i+30,n)) for i in range(0,n,30)]
 return np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])

def tuning_audit(f,outer_train,features,fold,saved):
 n=len(outer_train);a=int(n*.6);b=int(n*.8)
 ids=matured(f,outer_train[:a],f.loc[a,'decision_at'])
 inner,_=labels(f,ids)
 ids=matured(inner,ids,f.loc[a,'decision_at'])
 tune_ids=matured(inner,outer_train[b+30:],f.loc[outer_train[-1],'decision_at'])
 tr,tun=inner.loc[ids],inner.loc[tune_ids]
 A,T,_,_=preprocess(tr,tun,features)
 trials=saved.loc[saved.fold.eq(fold)&saved.model.eq('LightGBMRegressor')].copy()
 trials['rank']=trials.tuning_mse_scaled.rank(method='min').astype(int)
 preds={};rows=[]
 for r in trials.itertuples():
  params=json.loads(r.parameters);model=estimator('LightGBMRegressor',params).fit(A,tr.y_scaled)
  z=model.predict(T);mse=float(np.mean((tun.y_scaled-z)**2))
  np.testing.assert_allclose(mse,r.tuning_mse_scaled,rtol=1e-9,atol=1e-12)
  preds[r.parameters]=z*inner.attrs['target_scale']+inner.attrs['target_mean']
 winner=trials.sort_values('tuning_mse_scaled').iloc[0]
 for r in trials.itertuples():
  raw=preds[r.parameters];params=json.loads(r.parameters)
  q=pd.DataFrame({'fold':fold,'y_ma5':tun.y_ma5.to_numpy(),'y_hat':raw})
  vswinner=loss_ci(q,preds[winner.parameters]);vsbase=loss_ci(q,tun.structural_persistence)
  rows.append(dict(fold=fold,**params,parameters=r.parameters,rank=r.rank,selected=r.parameters==winner.parameters,
   tuning_mse_scaled=r.tuning_mse_scaled,tuning_RMSE_THB=float(np.sqrt(r.tuning_mse_scaled)*inner.attrs['target_scale']),
   inner_target_scale=inner.attrs['target_scale'],tuning_rows=len(tun),
   pct_MSE_above_winner=100*(r.tuning_mse_scaled/winner.tuning_mse_scaled-1),
   improvement_vs_winner_ci_low=vswinner['mse_improvement_ci_low'],improvement_vs_winner_ci_high=vswinner['mse_improvement_ci_high'],
   improvement_vs_structural_ci_low=vsbase['mse_improvement_ci_low'],improvement_vs_structural_ci_high=vsbase['mse_improvement_ci_high']))
 return pd.DataFrame(rows)

def run():
 DEST.mkdir(parents=True,exist_ok=True)
 original={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='LightGBM_Fold_Analysis.xlsx'}
 f,candidates,_,source=prepare()
 predictions=pd.read_csv(OUT/'predictions.csv.gz');saved_tuning=pd.read_csv(OUT/'tuning.csv')
 predictions.decision_at=pd.to_datetime(predictions.decision_at,utc=True)
 importances=[];fold_rows=[];ranges=[];tuning=[];checks=[];hours=[];months=[]
 selected_sets={}
 for fold,(outer_train,outer_test) in enumerate(TimeSeriesSplit(n_splits=4,gap=30).split(f),1):
  print(f'Fold {fold}: saved model, SHAP, validation permutations',flush=True)
  b=json.loads((OUT/f'fold{fold}_LightGBMRegressor.json').read_text());features=b['features'];selected_sets[fold]=set(features)
  mature_train=matured(f,outer_train,f.loc[outer_train[-1],'decision_at']+pd.Timedelta(minutes=15))
  full,_=labels(f,mature_train);train=full.loc[mature_train]
  p=predictions.loc[predictions.fold.eq(fold)&predictions.model.eq('LightGBMRegressor')].copy()
  validation=full.set_index('decision_at').loc[p.decision_at]
  med=pd.Series(b['medians'],index=features)
  def standardize(d):return (d[features].fillna(med).to_numpy()-np.array(b['means']))/np.array(b['scales'])
  X,V=standardize(train),standardize(validation)
  booster=Booster(model_file=str(OUT/f'fold{fold}_LightGBMRegressor.txt'))
  z=booster.predict(V,num_threads=1);raw=z*b['target_scale']+b['target_mean']
  np.testing.assert_allclose(raw,p.y_hat,rtol=1e-10,atol=1e-8)
  checks.append(dict(fold=fold,rows=len(p),prediction_reconstruction_max_error=float(np.abs(raw-p.y_hat).max()),model_features=booster.num_feature()))
  shap=booster.predict(V,pred_contrib=True,num_threads=1)
  np.testing.assert_allclose(shap.sum(axis=1),z,rtol=1e-9,atol=1e-10)
  gain=booster.feature_importance('gain');split=booster.feature_importance('split')
  imp=pd.DataFrame(dict(fold=fold,feature=features,gain=gain,gain_share=gain/gain.sum(),splits=split,
    mean_abs_SHAP_THB=np.abs(shap[:,:-1]).mean(axis=0)*b['target_scale'],mean_signed_SHAP_THB=shap[:,:-1].mean(axis=0)*b['target_scale']))
  rng=np.random.default_rng(42+fold);orders=[blocked_indices(len(V),rng) for _ in range(REPEATS)]
  base=np.mean((p.y_ma5.to_numpy()-raw)**2);pi=[]
  for j,feature in enumerate(features):
   differences=[]
   for indices in orders:
    altered=V.copy();altered[:,j]=V[indices,j]
    changed=booster.predict(altered,num_threads=1)*b['target_scale']+b['target_mean']
    differences.append(float(np.mean((p.y_ma5.to_numpy()-changed)**2)-base))
   pi.append(dict(feature=feature,permutation_MSE_increase=np.mean(differences),permutation_repeat_std=np.std(differences,ddof=1),
    permutation_repeat_p05=np.quantile(differences,.05),permutation_repeat_p95=np.quantile(differences,.95),positive_repeat_fraction=np.mean(np.array(differences)>0)))
  imp=imp.merge(pd.DataFrame(pi),on='feature',validate='one_to_one')
  for key,col in [('gain_rank','gain'),('SHAP_rank','mean_abs_SHAP_THB'),('permutation_rank','permutation_MSE_increase')]:imp[key]=imp[col].rank(method='min',ascending=False).astype(int)
  importances.append(imp)
  baseline=price_score(p.y_ma5,p.structural_persistence,p.structural_persistence)
  row=dict(fold=fold,**b['parameters'],**price_score(p.y_ma5,p.y_hat,p.structural_persistence),**loss_ci(p,p.structural_persistence))
  row.update(train_RMSE=price_score(train.y_ma5,booster.predict(X,num_threads=1)*b['target_scale']+b['target_mean'],train.structural_persistence)['RMSE'],
   baseline_RMSE=baseline['RMSE'],RMSE_ratio_to_baseline=row['RMSE']/baseline['RMSE'],
   mean_error_THB=float((p.y_hat-p.y_ma5).mean()),train_target_min=train.y_ma5.min(),train_target_max=train.y_ma5.max(),
   validation_target_min=p.y_ma5.min(),validation_target_max=p.y_ma5.max(),prediction_min=p.y_hat.min(),prediction_max=p.y_hat.max(),
   target_above_train_max_fraction=float(p.y_ma5.gt(train.y_ma5.max()).mean()),target_below_train_min_fraction=float(p.y_ma5.lt(train.y_ma5.min()).mean()),
   actual_above_max_prediction_fraction=float(p.y_ma5.gt(p.y_hat.max()).mean()),
   test_start_Bangkok=str(p.decision_at.min().tz_convert('Asia/Bangkok')),test_end_Bangkok=str(p.decision_at.max().tz_convert('Asia/Bangkok')),
   feature_count=len(features),used_features=int(np.sum(split>0)),trees=booster.num_trees())
  row['validation_train_RMSE_ratio']=row['RMSE']/row['train_RMSE'];fold_rows.append(row)
  for j,feature in enumerate(features):
   vals=validation[feature];lo,hi=train[feature].min(),train[feature].max()
   ranges.append(dict(fold=fold,feature=feature,train_min=lo,train_max=hi,validation_min=vals.min(),validation_max=vals.max(),
    validation_null_rate=float(vals.isna().mean()),fraction_observed_outside_train_range=float(((vals<lo)|(vals>hi)).sum()/vals.count()) if vals.count() else np.nan,
    max_abs_scaled_validation=float(np.abs(V[:,j]).max())))
  for column,dest in [('hour_Bangkok',hours),('month_Bangkok',months)]:
   p[column]=p.decision_at.dt.tz_convert('Asia/Bangkok').dt.hour if column.startswith('hour') else p.decision_at.dt.tz_convert('Asia/Bangkok').dt.strftime('%Y-%m')
   for value,g in p.groupby(column):dest.append(dict(fold=fold,**{column:value},**price_score(g.y_ma5,g.y_hat,g.structural_persistence)))
  print(f'Fold {fold}: reproducing 8 original inner tuning trials',flush=True)
  tuning.append(tuning_audit(f,outer_train,features,fold,saved_tuning))
 imp=pd.concat(importances,ignore_index=True);folds=pd.DataFrame(fold_rows)
 stability=[]
 for feature in candidates:
  g=imp.loc[imp.feature.eq(feature)]
  stability.append(dict(feature=feature,selected_folds=len(g),used_folds=int(g.splits.gt(0).sum()),
   top10_gain_folds=int(g.gain_rank.le(10).sum()),top10_SHAP_folds=int(g.SHAP_rank.le(10).sum()),
   positive_permutation_folds=int(g.permutation_MSE_increase.gt(0).sum()),
   mean_gain_share_when_selected=g.gain_share.mean(),median_SHAP_THB_when_selected=g.mean_abs_SHAP_THB.median(),
   median_permutation_MSE_when_selected=g.permutation_MSE_increase.median()))
 comparisons=[]
 for a,b in itertools.combinations(selected_sets,2):
  ga=set(imp.loc[imp.fold.eq(a)].nsmallest(10,'gain_rank').feature);gb=set(imp.loc[imp.fold.eq(b)].nsmallest(10,'gain_rank').feature)
  comparisons.append(dict(first_fold=a,second_fold=b,selected_intersection=len(selected_sets[a]&selected_sets[b]),selected_Jaccard=len(selected_sets[a]&selected_sets[b])/len(selected_sets[a]|selected_sets[b]),top10_gain_intersection=len(ga&gb),
   caution='Different historical regimes and training sizes; RMSE differences are descriptive, not a paired same-sample test'))
 pooled=predictions.loc[predictions.model.eq('LightGBMRegressor')]
 tables={'Fold_performance':folds,'Pooled_performance':pd.DataFrame([dict(model='LightGBMRegressor',**price_score(pooled.y_ma5,pooled.y_hat,pooled.structural_persistence),**loss_ci(pooled,pooled.structural_persistence))]),
  'Feature_importance':imp,'Top10_gain':imp.loc[imp.gain_rank.le(10)].sort_values(['fold','gain_rank']),
  'Top10_SHAP':imp.loc[imp.SHAP_rank.le(10)].sort_values(['fold','SHAP_rank']),
  'Top10_permutation':imp.loc[imp.permutation_rank.le(10)].sort_values(['fold','permutation_rank']),
  'Feature_stability':pd.DataFrame(stability),'Fold_overlap':pd.DataFrame(comparisons),
  'Tuning_trials':pd.concat(tuning,ignore_index=True),'Range_diagnostics':pd.DataFrame(ranges),
  'Bangkok_hour':pd.DataFrame(hours),'Bangkok_month':pd.DataFrame(months),'Reconstruction':pd.DataFrame(checks),
  'Original_Lasso_selection_PI':pd.read_csv(OUT/'permutation.csv'),
  'Original_all_model_scores':pd.read_csv(OUT/'fold_metrics.csv'),'Outer_model_comparison':pd.read_csv(OUT/'pairwise_comparison.csv'),'Overall_model_comparison':pd.read_csv(OUT/'summary.csv'),
  'Selection_lineage':selection_lineage(candidates),'Original_waterfall':pd.read_csv(OUT/'waterfall.csv'),
  'Fold_schedule':pd.read_csv(OUT/'schedule.csv')}
 tables['Tuning_winners']=tables['Tuning_trials'].loc[lambda d:d.selected].copy()
 for name,d in tables.items():d.to_csv(DEST/(name+'.csv'),index=False)
 plot(tables)
 export_excel(tables)
 for name,digest in original.items():assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest,f'Original changed: {name}'
 audit={'analysis':'Saved LightGBM audit; original models/selection/parameters unchanged. Original 32 inner trials refitted only to reproduce their scores and calculate paired loss intervals.',
  'original_hashes':original,'permutation_repeats':REPEATS,'permutation_block_rows':30,'SHAP':'LightGBM built-in TreeSHAP, path-dependent reference, all outer validation rows, output converted to THB quote units',
  'bootstrap':'1000 paired circular 30-observation blocks within folds; tuning-winner comparisons are post-selection descriptive intervals, without multiplicity correction',
  'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.glob('*') if p.is_file() and p.name!='analysis_manifest.json'}}
 (DEST/'analysis_manifest.json').write_text(json.dumps(audit,indent=2)+'\n')
 print(folds[['fold','RMSE','baseline_RMSE','R2','target_above_train_max_fraction']].to_string(index=False),flush=True)
 print(tables['Top10_gain'].groupby('fold').head(3)[['fold','feature','gain_share']].to_string(index=False),flush=True)
 return tables

def selection_lineage(candidates):
 waterfall=pd.read_csv(OUT/'waterfall.csv');rows=[]
 for fold in range(1,5):
  drops={}
  for r in waterfall.loc[waterfall.fold.eq(fold)].itertuples():
   if isinstance(r.dropped_features,str):
    for feature in r.dropped_features.split(';'):drops[feature]=r.stage
  for feature in candidates:rows.append(dict(fold=fold,feature=feature,status=drops.get(feature,'retained_final'),is_gold_price_level=('close' in feature and ('mts965' in feature or 'mts9999' in feature or 'mts_xauusd' in feature))))
 return pd.DataFrame(rows)

def plot(tables):
 fig,ax=plt.subplots(figsize=(8,4),constrained_layout=True);d=tables['Fold_performance'];x=np.arange(4)
 ax.bar(x-.2,d.RMSE,.4,label='LightGBM');ax.bar(x+.2,d.baseline_RMSE,.4,label='Structural baseline');ax.set(xticks=x,xticklabels=['F1','F2','F3','F4'],yscale='log',ylabel='Validation RMSE (THB quote units; log scale)');ax.legend();fig.savefig(DEST/'fold_RMSE.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(2,2,figsize=(13,8),constrained_layout=True)
 for (fold,g),ax in zip(tables['Feature_importance'].groupby('fold'),axes.flat):
  d=g.nlargest(10,'gain_share').sort_values('gain_share');ax.barh(d.feature,100*d.gain_share);ax.set_title(f'Fold {fold}: training gain importance');ax.set_xlabel('Share of total gain (%)');ax.tick_params(axis='y',labelsize=7)
 fig.savefig(DEST/'gain_top10.png',dpi=150);plt.close(fig)

def export_excel(tables):
 decisions=[]
 for fold,g in tables['Tuning_trials'].groupby('fold'):
  top=g.sort_values('rank').iloc[:2];runner=top.iloc[1];winner=top.iloc[0]
  decisions.append(dict(fold=fold,winner_parameters=winner.parameters,runnerup_parameters=runner.parameters,runnerup_pct_MSE_above_winner=runner.pct_MSE_above_winner,
   winner_advantage_CI_low=-runner.improvement_vs_winner_ci_high,winner_advantage_CI_high=-runner.improvement_vs_winner_ci_low,
   interval_excludes_zero=bool(runner.improvement_vs_winner_ci_high<0),caution='Conditional comparison on the tuning block used for selection; not confirmatory; no multiplicity correction'))
 tables['Tuning_decision_evidence']=pd.DataFrame(decisions)
 tables['Tuning_decision_evidence'].to_csv(DEST/'Tuning_decision_evidence.csv',index=False)
 findings=[]
 for r in tables['Fold_performance'].itertuples():
  top=tables['Feature_importance'].loc[lambda d:d.fold.eq(r.fold)].sort_values('gain_rank').iloc[0]
  findings.append(dict(fold=r.fold,dominant_feature=top.feature,dominant_gain_share=top.gain_share,
   validation_RMSE=r.RMSE,baseline_RMSE=r.baseline_RMSE,RMSE_multiple_of_baseline=r.RMSE_ratio_to_baseline,
   validation_train_RMSE_multiple=r.validation_train_RMSE_ratio,above_training_target_max_fraction=r.target_above_train_max_fraction,
   acceptance='passes CI rule' if r.acceptance_ci_positive else 'fails CI rule',
   tuned_tree_count_at_grid_max=r.n_estimators==250,
   conclusion='Tree count winner is at search boundary; global optimality is untested. Validation remains worse than persistence.'))
 tables['Findings']=pd.DataFrame(findings)
 tables['Findings'].to_csv(DEST/'Findings.csv',index=False)
 notes=[('Target','Next completed bar trailing MA5: [P(t-3)+P(t-2)+P(t-1)+P(t)+P(t+1)]/5. Four prices already known. All errors THB quote units.'),
 ('Scope','Audit saved 4 fold LightGBM models; no new outer-model fitting or tuning. Refits reproduce the 32 original inner tuning candidates.'),
 ('Critical benchmark','Structural persistence assumes P(t+1)=P(t). Price-level R2 can be high without next-price skill. All four saved LightGBM folds lose to this baseline.'),
 ('Gain and split','Training gain shares and split counts describe model usage, not validation usefulness or causality. Standardized columns are mapped using saved JSON feature order.'),
 ('SHAP','Built-in path-dependent TreeSHAP on every validation row. Mean absolute contribution measures influence, not accuracy improvement or causal effect. THB units after inverse target scaling.'),
 ('Permutation','Validation MSE increase after permuting each feature in 30-observation blocks, 20 repeats. Positive worsens loss; negative means perturbation improves this model. Correlated substitutes can mask importance; disrupted trends may be unrealistic.'),
 ('Repeat intervals','Permutation p05/p95 and std describe repeat dispersion, NOT inferential confidence intervals. Gain/SHAP/PI rankings answer different questions.'),
 ('Confidence intervals','Paired circular 30-observation bootstrap, 1000 samples, for MSE improvement against baseline. No multiplicity correction.'),
 ('Tuning','8 original candidates per fold: trees100/250, learning_rate .03/.07, min_child_samples50/150; depth3, leaves7, Huber objective, seed42. Rank by inner tuning MSE on train-standardized target.'),
 ('Tuning units','tuning_mse_scaled is comparable within a fold. RMSE_THB converts using that inner-fit target std. Different folds cover different periods; cross-fold candidate means do not identify a universal winner.'),
 ('Winner comparisons','Paired intervals compare candidates with the winner on the same inner tuning block used to pick it. Post-selection descriptive evidence, not independent significance or confirmatory tests. Statistically distinguishable superiority is not implied by rank1.'),
 ('No final holdout','2025–2026 folds are development evidence. New decisions based on this audit require nested evaluation or a later untouched period.'),
 ('Original selection PI','Original_Lasso_selection_PI is the old feature selector, NOT LightGBM validation importance. Feature_importance contains the new LightGBM-specific measurements.'),
 ('Fold comparison','Validation regimes differ; compare error ratios, train-validation gap, target range shifts and stability. Do not select an operational model solely because its fold has lowest RMSE.'),
 ('Training range','Trees use piecewise constant leaves and can struggle with unseen price levels. Above-train-range and prediction-ceiling diagnostics are empirical indicators, not an isolated causal proof.')]
 with pd.ExcelWriter(OUT/'LightGBM_Fold_Analysis.xlsx',engine='xlsxwriter',engine_kwargs={'options':{'strings_to_formulas':False,'strings_to_urls':False}}) as w:
  pd.DataFrame(notes,columns=['Topic','Explanation']).to_excel(w,sheet_name='Read_me',index=False)
  for name,d in tables.items():
   d.to_excel(w,sheet_name=name[:31],index=False,inf_rep='inf');sheet=w.sheets[name[:31]];sheet.freeze_panes(1,0);sheet.autofilter(0,0,len(d),len(d.columns)-1);sheet.set_column(0,len(d.columns)-1,24)
   if 'feature' in d:sheet.set_column(d.columns.get_loc('feature'),d.columns.get_loc('feature'),44)
  s=w.sheets['Read_me'];s.set_column(0,0,26);s.set_column(1,1,115,w.book.add_format({'text_wrap':True}));
  for row in range(1,len(notes)+1):s.set_row(row,48)
  charts=w.book.add_worksheet('Charts');charts.insert_image('A1',str(DEST/'fold_RMSE.png'));charts.insert_image('A34',str(DEST/'gain_top10.png'))

if __name__=='__main__':run()
