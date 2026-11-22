"""GLD965 direct MA5 horizons 1..5: chronological train/test and final two-month OOT."""
from pathlib import Path
import hashlib,json,pickle
import numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.metrics import confusion_matrix,accuracy_score,balanced_accuracy_score,matthews_corrcoef,log_loss
from lightgbm import LGBMRegressor,LGBMClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
SOURCE=P.parent/'model1_15m_priceMA/prepared_X_y_context.csv.gz'
PARAM=dict(n_estimators=150,learning_rate=.03,max_depth=3,num_leaves=7,min_child_samples=150,colsample_bytree=.7,reg_lambda=10,random_state=42,n_jobs=1,verbosity=-1)
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

 # Common eligible labels ensure all horizons are evaluated on identical decision rows.
 cutoff=dt.max().tz_convert('Asia/Bangkok')-pd.DateOffset(months=2)
 cutoff=cutoff.tz_convert('UTC')
 pre=np.flatnonzero(valid & (dt.shift(-5)<cutoff))
 oot=np.flatnonzero(valid & (dt>=cutoff))
 pivot=int(len(pre)*.7)
 train=pre[:pivot];test=pre[pivot:]
 # Purge any label that reaches across the train/test boundary.
 train=train[(dt.shift(-5).iloc[train]<dt.iloc[test[0]]).to_numpy()]
 assert dt.shift(-5).iloc[train[-1]]<dt.iloc[test[0]]
 assert dt.shift(-5).iloc[test[-1]]<cutoff<=dt.iloc[oot[0]]
 partitions={'TRAIN':train,'TEST':test,'OOT':oot}
 quality=pd.DataFrame({'feature':X.columns,'null_rate':X.iloc[train].isna().mean().values,'unique':X.iloc[train].nunique().values})
 quality['selected']=(quality.null_rate<.2)&(quality.unique>1)
 cols=quality.loc[quality.selected,'feature'].tolist()
 med=X.iloc[train][cols].median();scaler=StandardScaler().fit(X.iloc[train][cols].fillna(med))
 matrices={name:scaler.transform(X.iloc[index][cols].fillna(med)) for name,index in partitions.items()}
 metrics=[];gains=[];predictions=[]
 for h in range(1,6):
  y=context[f'y_h{h}'];b=context[f'baseline_h{h}'];u=context[f'u_h{h}'];direction=(y>ma).astype(int)
  mean=u.iloc[train].mean();std=u.iloc[train].std(ddof=0)
  fitted={}
  for task in ['regression','classification']:
   kinds=['Structural','Ridge','LightGBM'] if task=='regression' else ['Structural','TrainPrior','Logistic','LightGBM']
   for kind in kinds:
    model=None;count=np.nan;gate=np.nan
    if kind not in ['Structural','TrainPrior']:
     model=(Ridge(alpha=10) if kind=='Ridge' else LGBMRegressor(objective='huber',**PARAM)) if task=='regression' else (LogisticRegression(C=.1,max_iter=2000) if kind=='Logistic' else LGBMClassifier(**PARAM))
     model.fit(matrices['TRAIN'],((u.iloc[train]-mean)/std) if task=='regression' else direction.iloc[train])
     fitted[(task,kind)]=model
     with (P/f'h{h}_{task}_{kind}.pkl').open('wb') as file:pickle.dump({'model':model,'features':cols,'medians':med,'scaler':scaler,'target_mean':mean if task=='regression' else None,'target_std':std if task=='regression' else None},file)
     if kind=='LightGBM':
      values=model.booster_.feature_importance('gain');shares=values/values.sum() if values.sum() else values*0
      count=int((shares>=.05).sum());gate=bool(count>=3)
      gains.extend({'horizon':h,'task':task,'feature':f,'gain':float(v),'gain_share':float(s),'over_5pct':bool(s>=.05)} for f,v,s in zip(cols,values,shares))
    for part,index in partitions.items():
     truth=y.iloc[index].to_numpy();base=b.iloc[index].to_numpy();actual=direction.iloc[index].to_numpy();now=ma.iloc[index].to_numpy();price=c.iloc[index].to_numpy()
     if task=='regression':
      pred=base.copy() if kind=='Structural' else base+price*(model.predict(matrices[part])*std+mean)
      prob=np.full(len(index),np.nan);class_hat=(pred>now).astype(int)
      rmse=float(np.sqrt(np.mean((truth-pred)**2)));mae=float(np.mean(abs(truth-pred)))
     else:
      pred=np.full(len(index),np.nan);rmse=mae=np.nan
      prob=((base>now).astype(float) if kind=='Structural' else np.full(len(index),direction.iloc[train].mean()) if kind=='TrainPrior' else model.predict_proba(matrices[part])[:,1])
      class_hat=(prob>.5).astype(int)
     tn,fp,fn,tp=confusion_matrix(actual,class_hat,labels=[0,1]).ravel()
     metrics.append({'partition':part,'horizon':h,'task':task,'model':kind,'rows':len(index),'RMSE':rmse,'MAE':mae,'accuracy':accuracy_score(actual,class_hat),'balanced_accuracy':balanced_accuracy_score(actual,class_hat),'MCC':matthews_corrcoef(actual,class_hat),'TN':int(tn),'FP':int(fp),'FN':int(fn),'TP':int(tp),'precision_positive':tp/(tp+fp) if tp+fp else np.nan,'recall_positive':tp/(tp+fn) if tp+fn else np.nan,'log_loss':log_loss(actual,np.clip(prob,1e-6,1-1e-6)) if task=='classification' else np.nan,'features_ge_5pct':count,'gain_gate_ge3':gate})
     predictions.append(pd.DataFrame({'partition':part,'horizon':h,'task':task,'model':kind,'decision_at':dt.iloc[index].astype(str).values,'actual':truth,'structural':base,'predicted':pred,'actual_class':actual,'predicted_class':class_hat,'probability':prob}))
  print('Horizon',h,'finished',flush=True)
 m=pd.DataFrame(metrics);q=pd.DataFrame(gains);pred=pd.concat(predictions,ignore_index=True)
 m.to_csv(P/'Metrics.csv',index=False);q.to_csv(P/'Feature_gain.csv',index=False);quality.to_csv(P/'Feature_quality.csv',index=False)
 pd.DataFrame(defs,columns=['feature','definition']).to_csv(P/'Feature_dictionary.csv',index=False)
 pred.to_csv(P/'Predictions.csv.gz',index=False)
 pd.concat([context,X],axis=1).to_csv(P/'Dataset_X_y.csv.gz',index=False)
 schedule=pd.DataFrame([{'partition':name,'rows':len(index),'first':str(dt.iloc[index[0]]),'last':str(dt.iloc[index[-1]]),'first_label_h5':str(dt.shift(-5).iloc[index[0]]),'last_label_h5':str(dt.shift(-5).iloc[index[-1]])} for name,index in partitions.items()]);schedule.to_csv(P/'Schedule.csv',index=False)
 notes=pd.DataFrame([('source',str(SOURCE)),('source_sha256',hashlib.sha256(SOURCE.read_bytes()).hexdigest()),('oot_start_rule','Latest saved decision time minus two Bangkok calendar months; fixed before modeling.'),('oot_cutoff',str(cutoff)),('split','70%/30% of pre-OOT common eligible rows, chronological; train labels purged at TEST start; TEST labels mature before OOT cutoff.'),('target','Next trailing MA5 at h=1..5, all common rows have 5 future contiguous 15m bars.'),('regression','Predict normalized residual (Y-structural)/current close; reconstruct price.'),('classification','1 if future MA5>current observed MA5, else 0; threshold p>0.5.'),('feature_gate','At least 3 features with each >=5% of LightGBM total training gain; diagnostic only.'),('model','Fixed v2 hyperparameters; no model selection on OOT; previously inspected 2026 means OOT is not pristine.'),('parameters',json.dumps(PARAM))],columns=['item','value']);notes.to_csv(P/'Methodology.csv',index=False)
 fig,axes=plt.subplots(5,2,figsize=(15,16),constrained_layout=True)
 for h in range(1,6):
  for col,part in enumerate(['TEST','OOT']):
   z=pred.query('task=="regression" and horizon==@h and partition==@part')
   for model in ['Structural','Ridge','LightGBM']:
    s=z[z.model.eq(model)];time=pd.to_datetime(s.decision_at,utc=True).dt.tz_convert('Asia/Bangkok')
    axes[h-1,col].plot(time,s.predicted,lw=.65,label=model)
    if model=='Structural':axes[h-1,col].plot(time,s.actual,lw=.7,color='black',label='Actual')
   axes[h-1,col].set_title(f'h={h} {part}: next MA5 actual vs predicted');axes[h-1,col].legend(fontsize=7)
 fig.savefig(P/'Price_actual_vs_prediction.png',dpi=140);plt.close(fig)
 with pd.ExcelWriter(P/'V21_preliminary.xlsx',engine='xlsxwriter') as w:
  for name,tab in [('Methodology',notes),('Schedule',schedule),('Metrics',m),('Feature_gain',q),('Feature_quality',quality),('Feature_dictionary',pd.DataFrame(defs,columns=['feature','definition']))]:
   tab.to_excel(w,sheet_name=name,index=False);w.sheets[name].freeze_panes(1,0);w.sheets[name].set_column(0,len(tab.columns)-1,22)
  w.sheets['Methodology'].set_column(1,1,115)
  w.book.add_worksheet('Price_graph').insert_image('A1',str(P/'Price_actual_vs_prediction.png'),{'x_scale':.7,'y_scale':.7})
 print(schedule.to_string(index=False));print(m.query('partition=="OOT"')[['horizon','task','model','RMSE','accuracy','features_ge_5pct','gain_gate_ge3']].to_string(index=False))
 return m
if __name__=='__main__':run()
