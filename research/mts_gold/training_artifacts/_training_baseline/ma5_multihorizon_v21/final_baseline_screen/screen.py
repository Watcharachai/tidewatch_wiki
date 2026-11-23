"""Screen compact LightGBM MA5 candidates under hard gain and stability rules."""
from pathlib import Path
import json,pickle
import numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score,log_loss
from lightgbm import LGBMRegressor,LGBMClassifier
ROOT=Path(__file__).resolve().parent.parent;OUT=Path(__file__).resolve().parent;PR=ROOT/'parameter_review'
BASE=dict(colsample_bytree=.7,min_child_samples=150,reg_lambda=10,random_state=42,n_jobs=1,verbosity=-1)
def run():
 d=pd.read_csv(ROOT/'Dataset_X_y.csv.gz',low_memory=False);time=pd.to_datetime(d.decision_at,utc=True)
 sched=pd.read_csv(ROOT/'Schedule.csv');ids={r.partition:np.flatnonzero(time.between(pd.Timestamp(r.first),pd.Timestamp(r.last)) & d.eligible) for r in sched.itertuples()}
 columns=pd.read_csv(ROOT/'Feature_quality.csv').query('selected').feature.tolist();med=d.loc[ids['TRAIN'],columns].median();sc=StandardScaler().fit(d.loc[ids['TRAIN'],columns].fillna(med))
 mats={part:sc.transform(d.loc[ix,columns].fillna(med)) for part,ix in ids.items()}
 selected_params=pd.read_csv(PR/'selected_parameters.csv');orig=pd.read_csv(ROOT/'Metrics.csv')
 rows=[];selected=[];gains=[]
 for h in range(1,6):
  y={part:d[f'y_h{h}'].iloc[ix].to_numpy() for part,ix in ids.items()};b={part:d[f'baseline_h{h}'].iloc[ix].to_numpy() for part,ix in ids.items()};close={part:d.close.iloc[ix].to_numpy() for part,ix in ids.items()};current={part:d.ma5_current.iloc[ix].to_numpy() for part,ix in ids.items()};u=d[f'u_h{h}'].iloc[ids['TRAIN']];mu=u.mean();sd=u.std(ddof=0);binary={part:(y[part]>current[part]).astype(int) for part in ids}
  for task in ['regression','classification']:
   prior=selected_params.query('horizon==@h and task==@task and model=="LightGBM"').iloc[0];model0=pickle.load((PR/f'h{h}_{task}_LightGBM_selected.pkl').open('rb'))['model'];gain0=model0.booster_.feature_importance('gain');order=np.argsort(-gain0,kind='stable')
   candidate=[]
   for offset in (range(9) if h==2 and task=='classification' else [0,1,2]):
    for k in [3,4,5,6,8,10]:
     chosen=order[offset:offset+k];names=[columns[i] for i in chosen]
     for depth,leaves in [(2,3),(3,7)]:
      params={**BASE,**json.loads(prior.parameters),'max_depth':depth,'num_leaves':leaves}
      model=(LGBMRegressor(objective='huber',**params) if task=='regression' else LGBMClassifier(**params))
      model.fit(mats['TRAIN'][:,chosen],(u-mu)/sd if task=='regression' else binary['TRAIN'])
      raw=model.booster_.feature_importance('gain');shares=raw/raw.sum() if raw.sum() else raw*0
      record=dict(horizon=h,task=task,feature_rank_offset=offset,features=k,feature_names=json.dumps(names),max_depth=depth,num_leaves=leaves,parameters=json.dumps(params,sort_keys=True),min_gain_share=float(shares.min()),max_gain_share=float(shares.max()),gain_pass=bool((shares>=.05-1e-12).all() and (shares<=.70+1e-12).all()),count_over_5pct=int((shares>=.05).sum()))
      for part in ['TRAIN','TEST']:
       if task=='regression':
        forecast=b[part]+close[part]*(model.predict(mats[part][:,chosen])*sd+mu)
        rmse=np.sqrt(np.mean((y[part]-forecast)**2));base_rmse=np.sqrt(np.mean((y[part]-b[part])**2))
        record[f'{part}_RMSE']=float(rmse);record[f'{part}_relative_RMSE']=float(rmse/base_rmse);record[f'{part}_accuracy']=float(accuracy_score(binary[part],forecast>current[part]));record[f'{part}_log_loss']=np.nan
       else:
        prob=model.predict_proba(mats[part][:,chosen])[:,1];record[f'{part}_log_loss']=float(log_loss(binary[part],prob));record[f'{part}_accuracy']=float(accuracy_score(binary[part],prob>.5));record[f'{part}_RMSE']=np.nan;record[f'{part}_relative_RMSE']=np.nan
      # Relative gap normalizes the different target volatility of TRAIN and TEST.
      gap=(record['TEST_relative_RMSE']-record['TRAIN_relative_RMSE']) if task=='regression' else (record['TRAIN_accuracy']-record['TEST_accuracy'])
      record['train_test_gap']=float(gap);record['train_test_stable']=bool(gap<=.02)
      rows.append(record.copy());candidate.append((record,model,chosen,names,shares,params))
   metric='TEST_RMSE' if task=='regression' else 'TEST_log_loss'
   feasible=[x for x in candidate if x[0]['gain_pass'] and x[0]['train_test_stable']]
   if feasible:
    pick=min(feasible,key=lambda x:x[0][metric]);status='passed TRAIN/TEST hard gates'
   else:
    pick=min(candidate,key=lambda x:x[0][metric]);status='no candidate passed TRAIN/TEST hard gates; descriptive only'
   r,model,chosen,names,shares,params=pick
   part='OOT'
   if task=='regression':
    forecast=b[part]+close[part]*(model.predict(mats[part][:,chosen])*sd+mu);rmse=float(np.sqrt(np.mean((y[part]-forecast)**2)));base_rmse=float(np.sqrt(np.mean((y[part]-b[part])**2)));r['OOT_RMSE']=rmse;r['OOT_relative_RMSE']=rmse/base_rmse;r['OOT_accuracy']=float(accuracy_score(binary[part],forecast>current[part]));r['OOT_log_loss']=np.nan
    oot_gap=r['OOT_relative_RMSE']-r['TRAIN_relative_RMSE']
   else:
    prob=model.predict_proba(mats[part][:,chosen])[:,1];r['OOT_log_loss']=float(log_loss(binary[part],prob));r['OOT_accuracy']=float(accuracy_score(binary[part],prob>.5));r['OOT_RMSE']=r['OOT_relative_RMSE']=np.nan;oot_gap=r['TRAIN_accuracy']-r['OOT_accuracy']
   r['train_oot_gap']=float(oot_gap);r['train_oot_stable']=bool(oot_gap<=.02);r['status']=status;r['all_three_rules_pass']=bool(r['gain_pass'] and r['train_test_stable'] and r['train_oot_stable'])
   # Benchmark skill is a separate empirical gate: avoid calling a non-improving model useful.
   struct=orig.query('partition=="OOT" and horizon==@h and task==@task and model=="Structural"').iloc[0]
   r['OOT_structural_RMSE']=struct.RMSE;r['OOT_structural_accuracy']=struct.accuracy
   r['beats_structural_OOT']=bool(r['OOT_RMSE']<struct.RMSE) if task=='regression' else bool(r['OOT_accuracy']>struct.accuracy)
   selected.append(r.copy());gains.extend(dict(horizon=h,task=task,feature=n,gain_share=float(s),above_5pct=bool(s>=.05),below_70pct=bool(s<=.70)) for n,s in zip(names,shares))
   if r['all_three_rules_pass']:
    with (OUT/f'h{h}_{task}_compact.pkl').open('wb') as file:pickle.dump(dict(model=model,feature_names=names,medians=med.loc[names],means=sc.mean_[chosen],scales=sc.scale_[chosen],target_mean=mu if task=='regression' else None,target_scale=sd if task=='regression' else None,selected_on='TEST',rules='min gain share >=5%; max <=70%; relative RMSE or accuracy train gap <=2 percentage points'),file)
   print('done',h,task,r['all_three_rules_pass'],r['beats_structural_OOT'],flush=True)
 trials=pd.DataFrame(rows);summary=pd.DataFrame(selected);importance=pd.DataFrame(gains)
 trials.to_csv(OUT/'candidate_screen.csv',index=False);summary.to_csv(OUT/'selected_summary.csv',index=False);importance.to_csv(OUT/'selected_gain.csv',index=False)
 with pd.ExcelWriter(OUT/'Final_Baseline_Screen.xlsx',engine='xlsxwriter') as w:
  for name,tab in [('Candidates',trials),('Selected',summary),('Selected_gain',importance)]:tab.to_excel(w,sheet_name=name,index=False);w.sheets[name].freeze_panes(1,0);w.sheets[name].set_column(0,len(tab.columns)-1,21)
 print(summary[['horizon','task','features','min_gain_share','max_gain_share','train_test_gap','train_oot_gap','all_three_rules_pass','OOT_RMSE','OOT_accuracy','beats_structural_OOT']].to_string(index=False))
if __name__=='__main__':run()
