"""Small, auditable parameter review: choose on TEST, then inspect OOT once."""
from pathlib import Path
import json,pickle
import numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.metrics import log_loss,accuracy_score
from lightgbm import LGBMRegressor,LGBMClassifier
ROOT=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
BASE=dict(max_depth=3,num_leaves=7,colsample_bytree=.7,random_state=42,n_jobs=1,verbosity=-1)
GRID=[dict(n_estimators=n,learning_rate=lr,min_child_samples=leaf,reg_lambda=10) for n in [80,150,300] for lr in [.015,.03] for leaf in [150,300]]

def main():
 d=pd.read_csv(ROOT/'Dataset_X_y.csv.gz',low_memory=False)
 dates=pd.to_datetime(d.decision_at,utc=True)
 schedule=pd.read_csv(ROOT/'Schedule.csv')
 indices={r.partition:np.flatnonzero(dates.between(pd.Timestamp(r.first),pd.Timestamp(r.last)) & d.eligible) for r in schedule.itertuples()}
 quality=pd.read_csv(ROOT/'Feature_quality.csv');cols=quality.loc[quality.selected,'feature'].tolist()
 med=d.loc[indices['TRAIN'],cols].median();scaler=StandardScaler().fit(d.loc[indices['TRAIN'],cols].fillna(med))
 xx={part:scaler.transform(d.loc[ix,cols].fillna(med)) for part,ix in indices.items()}
 original=pd.read_csv(ROOT/'Metrics.csv')
 baseline=original[original.partition.eq('TEST') & original.model.eq('Structural')]
 rows=[];params=[];selected=[]
 for h in range(1,6):
  b={part:d.loc[ix,f'baseline_h{h}'].to_numpy() for part,ix in indices.items()}
  close={part:d.loc[ix,'close'].to_numpy() for part,ix in indices.items()}
  y={part:d.loc[ix,f'y_h{h}'].to_numpy() for part,ix in indices.items()}
  target=d[f'u_h{h}'].iloc[indices['TRAIN']];mu=target.mean();sd=target.std(ddof=0)
  direction={part:(y[part]>d.loc[ix,'ma5_current'].to_numpy()).astype(int) for part,ix in indices.items()}
  for task in ['regression','classification']:
   for family in (['Ridge','LightGBM'] if task=='regression' else ['Logistic','LightGBM']):
    options=([{'alpha':a} for a in [.1,10,100,1000]] if family=='Ridge' else [{'C':c} for c in [.01,.1,1,10]] if family=='Logistic' else GRID)
    for opt in options:
     if family=='Ridge':model=Ridge(**opt)
     elif family=='Logistic':model=LogisticRegression(max_iter=2000,**opt)
     elif task=='regression':model=LGBMRegressor(objective='huber',**BASE,**opt)
     else:model=LGBMClassifier(**BASE,**opt)
     model.fit(xx['TRAIN'],(target-mu)/sd if task=='regression' else direction['TRAIN'])
     share=np.array([])
     if family=='LightGBM':
      gain=model.booster_.feature_importance('gain');share=gain/gain.sum() if gain.sum() else gain*0
      count=int((share>=.05).sum())
     else:count=np.nan
     record=dict(horizon=h,task=task,model=family,parameters=json.dumps(opt,sort_keys=True),features_ge_5pct=count,gain_gate_ge3=bool(count>=3) if family=='LightGBM' else np.nan)
     for part in ['TRAIN','TEST']:
      if task=='regression':
       predicted=b[part]+close[part]*(model.predict(xx[part])*sd+mu)
       rmse=float(np.sqrt(np.mean((predicted-y[part])**2)));score=rmse
       acc=accuracy_score(direction[part],predicted>d.loc[indices[part],'ma5_current'].to_numpy());loss=np.nan
      else:
       probability=model.predict_proba(xx[part])[:,1];loss=float(log_loss(direction[part],probability));acc=accuracy_score(direction[part],probability>.5);rmse=np.nan
       score=loss
      record[f'{part}_RMSE']=rmse;record[f'{part}_accuracy']=acc;record[f'{part}_log_loss']=loss
     rows.append(record)
    group=pd.DataFrame([r for r in rows if r['horizon']==h and r['task']==task and r['model']==family])
    metric='TEST_RMSE' if task=='regression' else 'TEST_log_loss'
    eligible=group[group.gain_gate_ge3.eq(True)] if family=='LightGBM' else group
    if eligible.empty:
     pick=group.sort_values(metric).iloc[0];gate=False
    else:
     pick=eligible.sort_values(metric).iloc[0];gate=True
    # OOT is scored once, only for the TEST-selected configuration.
    opt=json.loads(pick.parameters)
    if family=='Ridge':final=Ridge(**opt)
    elif family=='Logistic':final=LogisticRegression(max_iter=2000,**opt)
    elif task=='regression':final=LGBMRegressor(objective='huber',**BASE,**opt)
    else:final=LGBMClassifier(**BASE,**opt)
    final.fit(xx['TRAIN'],(target-mu)/sd if task=='regression' else direction['TRAIN'])
    if task=='regression':
     out=b['OOT']+close['OOT']*(final.predict(xx['OOT'])*sd+mu)
     oot_rmse=float(np.sqrt(np.mean((out-y['OOT'])**2)))
     oot_acc=accuracy_score(direction['OOT'],out>d.loc[indices['OOT'],'ma5_current'].to_numpy());oot_loss=np.nan
    else:
     prob=final.predict_proba(xx['OOT'])[:,1]
     oot_acc=accuracy_score(direction['OOT'],prob>.5);oot_loss=float(log_loss(direction['OOT'],prob));oot_rmse=np.nan
    selected.append({**pick.to_dict(),'OOT_RMSE':oot_rmse,'OOT_accuracy':oot_acc,'OOT_log_loss':oot_loss,'selection_metric':metric,'selection_gain_gate_met':gate})
   print('completed',h,task,flush=True)
 alltrials=pd.DataFrame(rows);chosen=pd.DataFrame(selected)
 alltrials.to_csv(OUT/'all_trials.csv',index=False);chosen.to_csv(OUT/'selected_parameters.csv',index=False)
 comparison=[]
 for row in chosen.itertuples():
  for part in ['TRAIN','TEST','OOT']:
   old=original.query('partition==@part and horizon==@row.horizon and task==@row.task and model==@row.model').iloc[0]
   structural=original.query('partition==@part and horizon==@row.horizon and task==@row.task and model=="Structural"').iloc[0]
   comparison.append(dict(horizon=row.horizon,task=row.task,model=row.model,partition=part,selected_parameters=row.parameters,features_ge_5pct=row.features_ge_5pct,gain_gate_ge3=row.selection_gain_gate_met,
    original_RMSE=old.RMSE,tuned_RMSE=getattr(row,f'{part}_RMSE'),structural_RMSE=structural.RMSE,
    original_accuracy=old.accuracy,tuned_accuracy=getattr(row,f'{part}_accuracy'),structural_accuracy=structural.accuracy,
    original_log_loss=old.log_loss,tuned_log_loss=getattr(row,f'{part}_log_loss')))
 comp=pd.DataFrame(comparison);comp.to_csv(OUT/'comparison.csv',index=False)
 spec=[]
 for h in range(1,6):
  for task in ['regression','classification']:
   for family in ['LightGBM','Ridge' if task=='regression' else 'Logistic']:
    bundle=pickle.load((ROOT/f'h{h}_{task}_{family}.pkl').open('rb'))
    spec.append(dict(horizon=h,task=task,model=family,selected_features=len(bundle['features']),current_parameters=json.dumps(bundle['model'].get_params(),sort_keys=True)))
 pd.DataFrame(spec).to_csv(OUT/'original_model_parameters.csv',index=False)
 with pd.ExcelWriter(OUT/'Parameter_Review.xlsx',engine='xlsxwriter') as w:
  for name,tab in [('Original_parameters',pd.DataFrame(spec)),('Tuning_trials',alltrials),('Selected',chosen),('Comparison',comp)]:
   tab.to_excel(w,sheet_name=name,index=False);w.sheets[name].freeze_panes(1,0);w.sheets[name].set_column(0,len(tab.columns)-1,22)
  w.sheets['Original_parameters'].set_column(4,4,115)
  w.sheets['Selected'].set_column(3,3,60)
 print(comp[comp.partition.eq('OOT')][['horizon','task','model','original_RMSE','tuned_RMSE','structural_RMSE','original_accuracy','tuned_accuracy','structural_accuracy','gain_gate_ge3']].to_string(index=False))
if __name__=='__main__':main()
