"""Frozen-design preliminary direct MA5 residual and direction experiments; no tuning."""
from pathlib import Path
import json,hashlib,pickle
import numpy as np,pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.metrics import confusion_matrix,accuracy_score,balanced_accuracy_score,log_loss,matthews_corrcoef
from lightgbm import LGBMRegressor,LGBMClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
SOURCE=P.parent/'model1_15m_priceMA/prepared_X_y_context.csv.gz'
PARAM=dict(n_estimators=150,learning_rate=.03,max_depth=3,num_leaves=7,min_child_samples=150,colsample_bytree=.7,reg_lambda=10,random_state=42,n_jobs=1,verbosity=-1)
NOTES=[('Target','GLD965 15m; direct next MA5 at horizons 1..5 (15..75 minutes).'),('Residual','u=(future MA5-structural baseline)/current close; reconstructed prediction=B+close*u_hat.'),('Direction','future MA5 > current observed MA5; ties=0; probability threshold=0.5.'),('Timing','Current completed own bar is allowed. Saved reference return lags retain their original extra one-MTS-row delay. No raw price levels.'),('Validation','Four expanding folds, gap=30 context rows; common contiguous labels for all five horizons; no tuning, calibration or final holdout. 2026 was previously inspected.'),('Selection','Train-only null >=20% and zero variance removal; no VIF/Lasso gate. Fixed interpretable candidate groups, no outcome-selected features.'),('Gain requirement','At least 4 features with >=5% of training total split gain, measured per fitted LightGBM. Diagnostic gate, not forced gain or proof of forecast skill.'),('Acceptance','Paired circular 30-row block bootstrap, 1000 samples within folds. Positive lower bound for MSE improvement (regression) or accuracy improvement (classification) vs structural baseline, plus gain gate. Exploratory, no multiplicity adjustment.'),('Model settings',json.dumps(PARAM)),('Linear settings','Ridge alpha=10, standardized X/Y; LogisticRegression C=0.1,max_iter=2000; no class weighting.'),('Data limitation','Daily macro excluded in this first experiment; no invented MTS volume or unverified fair-value unit conversions.')]
def ci(d):
 rng=np.random.default_rng(42);n=len(d);means=[]
 for _ in range(1000):
  ix=((rng.integers(n,size=int(np.ceil(n/30)))[:,None]+np.arange(30))%n).ravel()[:n];means.append(np.mean(d[ix]))
 return np.quantile(means,[.025,.975])
def run():
 f=pd.read_csv(SOURCE,low_memory=False);f['decision_at']=pd.to_datetime(f.decision_at,utc=True);f=f.sort_values('decision_at').reset_index(drop=True)
 c=f.close;dt=f.decision_at;adj=dt.diff().eq(pd.Timedelta(minutes=15));r=np.log(c/c.shift()).where(adj)
 X=pd.DataFrame(index=f.index);defs=[]
 def add(n,v,meaning):X[n]=v;defs.append((n,meaning))
 for k in [0,1,5,30]:add(f'log_return_lag{k}',r.shift(k),'Own single-bar log return, shift in observed rows; current completed bar allowed.')
 for w in [5,7,15,30]:
  rw=r.rolling(w,min_periods=w)
  add(f'vol{w}',rw.std(),'Sample standard deviation of completed contiguous own returns.')
  add(f'momentum{w}',rw.sum(),'Sum of own log returns over completed window.')
  if w!=5:
   for stat in ['min','max','skew','kurt']:add(f'return_{stat}{w}',getattr(rw,stat)(),f'Completed own returns: {stat}, window {w}; pandas kurt is excess.')
   add(f'variance{w}',rw.var(),'Sample variance; retained initially to audit redundancy.')
  good=adj.rolling(w-1).sum().eq(w-1)
  add(f'price_to_ma{w}',(c/c.rolling(w).mean()-1).where(good),'Relative price/MA gap; contiguous window.')
 add('bar_range',(f.high-f.low)/c,'Current completed high-low divided by close.')
 add('body',(c-f.open)/f.open,'Completed bar body relative to open.')
 hour=dt.dt.tz_convert('Asia/Bangkok').dt.hour+dt.dt.minute/60
 add('hour_sin',np.sin(hour*2*np.pi/24),'Bangkok time cyclical encoding.');add('hour_cos',np.cos(hour*2*np.pi/24),'Bangkok time cyclical encoding.')
 add('elapsed_minutes',dt.diff().dt.total_seconds()/60,'Elapsed since previous MTS bar.');add('session_open',(~adj).astype(float),'Previous bar not contiguous.')
 for source in ['mts_xauusd','btcusdt','mts9999']:
  for k in [1,5,30]:
   name=f'{source}_15m_return_lag{k}'
   add(name,f[name],'Inherited cumulative simple source return, already shifted one MTS row; NOT an own log-return lag.')
 X=X.replace([np.inf,-np.inf],np.nan)
 ma=c.rolling(5).mean();valid=adj.rolling(4).sum().eq(4)
 for k in range(1,6):valid &= (dt.shift(-k)-dt).eq(pd.Timedelta(minutes=15*k))
 context=pd.DataFrame({'decision_at':dt,'close':c,'ma5_current':ma,'eligible':valid})
 for h in range(1,6):
  y=ma.shift(-h).where(valid)
  b=(sum(c.shift(k) for k in range(5-h))+h*c)/5 if h<5 else c
  context[f'y_h{h}']=y;context[f'baseline_h{h}']=b;context[f'u_h{h}']=(y-b)/c
 pd.concat([context,X],axis=1).to_csv(P/'dataset_X_y.csv.gz',index=False)
 metrics=[];imps=[];quality=[];preds=[];schedules=[]
 for fold,(tr,va) in enumerate(TimeSeriesSplit(n_splits=4,gap=30).split(f),1):
  tr=tr[valid.iloc[tr].to_numpy()];va=va[valid.iloc[va].to_numpy()]
  tr=tr[(dt.shift(-5).iloc[tr]<dt.iloc[va[0]]).to_numpy()]
  assert dt.iloc[tr[-1]]+pd.Timedelta(minutes=75)<dt.iloc[va[0]]
  q=pd.DataFrame({'feature':X.columns,'null_rate':X.iloc[tr].isna().mean().values,'unique':X.iloc[tr].nunique().values,'variance':X.iloc[tr].var().values});q['selected']=(q.null_rate<.2)&(q.unique>1);q['fold']=fold;quality.append(q)
  cols=q.loc[q.selected,'feature'].tolist();med=X.iloc[tr][cols].median();scale=StandardScaler().fit(X.iloc[tr][cols].fillna(med));A=scale.transform(X.iloc[tr][cols].fillna(med));V=scale.transform(X.iloc[va][cols].fillna(med))
  schedules.append(dict(fold=fold,train_n=len(tr),validation_n=len(va),train_end=str(dt.iloc[tr[-1]]),validation_start=str(dt.iloc[va[0]]),validation_end=str(dt.iloc[va[-1]]),features=len(cols)))
  for h in range(1,6):
   y=context[f'y_h{h}'];b=context[f'baseline_h{h}'];u=context[f'u_h{h}'];a=(y>ma).astype(int);truth=y.iloc[va].to_numpy();base=b.iloc[va].to_numpy();actual=a.iloc[va].to_numpy();struct=(base>ma.iloc[va]).astype(int).to_numpy()
   for task in ['regression','classification']:
    kinds=['Structural','Ridge','LightGBM'] if task=='regression' else ['Structural','TrainPrior','Logistic','LightGBM']
    for kind in kinds:
     model=None;gainpass=None;gaincount=None
     if task=='regression':
      mean=u.iloc[tr].mean();std=u.iloc[tr].std(ddof=0)
      if kind=='Structural':yp=base.copy();trainpred=b.iloc[tr].to_numpy()
      else:
       model=Ridge(alpha=10) if kind=='Ridge' else LGBMRegressor(objective='huber',**PARAM)
       model.fit(A,(u.iloc[tr]-mean)/std)
       yp=base+c.iloc[va].to_numpy()*(model.predict(V)*std+mean)
       trainpred=b.iloc[tr].to_numpy()+c.iloc[tr].to_numpy()*(model.predict(A)*std+mean)
      cl=(yp>ma.iloc[va].to_numpy()).astype(int);prob=None;gain=(base-truth)**2-(yp-truth)**2
      mse=np.mean((yp-truth)**2);trainrmse=np.sqrt(np.mean((trainpred-y.iloc[tr])**2))
     else:
      yp=np.full(len(va),np.nan);trainrmse=np.nan;mse=np.nan
      if kind=='Structural':prob=struct.astype(float)
      elif kind=='TrainPrior':prob=np.full(len(va),a.iloc[tr].mean())
      else:
       model=LogisticRegression(C=.1,max_iter=2000) if kind=='Logistic' else LGBMClassifier(**PARAM)
       model.fit(A,a.iloc[tr]);prob=model.predict_proba(V)[:,1]
      cl=(prob>.5).astype(int);gain=(cl==actual).astype(float)-(struct==actual).astype(float)
     if kind=='LightGBM':
      gains=model.booster_.feature_importance('gain');shares=gains/gains.sum() if gains.sum() else gains*0
      gaincount=int((shares>=.05).sum());gainpass=gaincount>=4
      imps.extend(dict(fold=fold,horizon=h,task=task,feature=n,gain=float(g),gain_share=float(s)) for n,g,s in zip(cols,gains,shares))
     low,high=ci(np.asarray(gain));tn,fp,fn,tp=confusion_matrix(actual,cl,labels=[0,1]).ravel()
     metrics.append(dict(fold=fold,horizon=h,task=task,model=kind,n=len(va),RMSE=np.sqrt(mse),train_RMSE=trainrmse,MAE=np.mean(abs(yp-truth)),skill_vs_structural=1-mse/np.mean((base-truth)**2),accuracy=accuracy_score(actual,cl),balanced_accuracy=balanced_accuracy_score(actual,cl),MCC=matthews_corrcoef(actual,cl),TN=tn,FP=fp,FN=fn,TP=tp,log_loss=log_loss(actual,np.clip(prob,1e-6,1-1e-6)) if prob is not None else np.nan,gain_mean=np.mean(gain),gain_CI_low=low,gain_CI_high=high,features_ge_5pct=gaincount,gain_gate=gainpass,accepted=bool(low>0 and (gainpass if kind=='LightGBM' else True))))
     preds.append(pd.DataFrame(dict(fold=fold,horizon=h,task=task,model=kind,decision_at=dt.iloc[va].astype(str).values,label_at=dt.shift(-h).iloc[va].astype(str).values,actual=truth,baseline=base,predicted=yp,actual_class=actual,predicted_class=cl,probability=prob if prob is not None else np.nan)))
     if model is not None:
      with (P/f'fold{fold}_h{h}_{task}_{kind}.pkl').open('wb') as file:pickle.dump(dict(model=model,features=cols,medians=med,scaler=scale,target_mean=mean if task=='regression' else None,target_std=std if task=='regression' else None),file)
  print('Completed fold',fold,flush=True)
 results={'Metrics':pd.DataFrame(metrics),'Feature_gain':pd.DataFrame(imps),'Feature_quality':pd.concat(quality),'Fold_schedule':pd.DataFrame(schedules),'Feature_dictionary':pd.DataFrame(defs,columns=['feature','definition']),'Methodology':pd.DataFrame(NOTES,columns=['topic','description']),'Snapshot':pd.DataFrame([dict(rows=len(f),eligible=int(valid.sum()),features=len(X.columns),start=str(dt.min()),end=str(dt.max()),source=str(SOURCE),sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())])}
 pp=pd.concat(preds);pp.to_csv(P/'predictions.csv.gz',index=False)
 for name,tab in results.items():tab.to_csv(P/(name+'.csv'),index=False)
 fig,axes=plt.subplots(5,2,figsize=(16,18),constrained_layout=True)
 for h in range(1,6):
  for col,tail in enumerate([False,True]):
   for kind in ['Structural','Ridge','LightGBM']:
    z=pp.query('task=="regression" and horizon==@h and model==@kind').copy();z=z.tail(200) if tail else z
    time=pd.to_datetime(z.decision_at,utc=True).dt.tz_convert('Asia/Bangkok')
    axes[h-1,col].plot(time,z.predicted,lw=.65,label=kind)
    if kind=='Structural':axes[h-1,col].plot(time,z.actual,lw=.7,color='black',label='Actual')
   axes[h-1,col].set_title(f'Horizon {h}: '+('last 200 validation rows' if tail else 'all out-of-fold predictions'));axes[h-1,col].legend(fontsize=7);axes[h-1,col].tick_params(axis='x',rotation=25)
 fig.savefig(P/'actual_vs_predicted.png',dpi=140);plt.close(fig)
 with pd.ExcelWriter(P/'Preliminary_results.xlsx',engine='xlsxwriter') as writer:
  for name,tab in results.items():
   tab.to_excel(writer,sheet_name=name,index=False);writer.sheets[name].freeze_panes(1,0);writer.sheets[name].set_column(0,len(tab.columns)-1,20)
  writer.sheets['Methodology'].set_column(1,1,110,writer.book.add_format({'text_wrap':True}))
  for i in range(1,len(NOTES)+1):writer.sheets['Methodology'].set_row(i,48)
  sheet=writer.book.add_worksheet('Price_charts');sheet.insert_image('A1',str(P/'actual_vs_predicted.png'),{'x_scale':.65,'y_scale':.65})
  for horizon, group in pp.groupby('horizon'):
   group.to_excel(writer,sheet_name=f'Predictions_h{horizon}',index=False)
 print(results['Metrics'].query('model=="LightGBM"')[['fold','horizon','task','skill_vs_structural','accuracy','features_ge_5pct','accepted']].to_string(index=False))
 return results
if __name__=='__main__':run()
