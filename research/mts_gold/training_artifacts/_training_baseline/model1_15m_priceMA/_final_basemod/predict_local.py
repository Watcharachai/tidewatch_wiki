"""Standalone local inference/reporting for the frozen fold3 package. Run from any directory."""
from pathlib import Path
import pickle,json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def load_models(folder=ROOT):
 with (Path(folder)/'prediction_bundle.pkl').open('rb') as file:return pickle.load(file)

def predict(data,bundle):
 b=bundle['preprocessing'];names=b['features'];missing=set(names)-set(data.columns)
 if missing:raise ValueError(f'Missing prepared features: {sorted(missing)}')
 raw=data[names].replace([np.inf,-np.inf],np.nan).fillna(dict(zip(names,b['medians']))).to_numpy(dtype=float)
 x=(raw-np.array(b['means']))/np.array(b['scales'])
 base=bundle['base_model'].predict(x,num_threads=1)*b['target_scale']+b['target_mean']
 return pd.DataFrame({'prediction_lightgbm':base,'prediction_isotonic':bundle['isotonic'].predict(base),'prediction_linear':bundle['linear'].predict(base.reshape(-1,1))},index=data.index)

def metrics(y,p,baseline):
 y,p,b=np.asarray(y),np.asarray(p),np.asarray(baseline);err=p-y;mse=np.mean(err**2);den=np.sum((y-y.mean())**2);base=np.mean((b-y)**2)
 return dict(rows=len(y),RMSE=np.sqrt(mse),MAE=np.abs(err).mean(),MSE=mse,R2=1-np.sum(err**2)/den if den else np.nan,
  mean_error=err.mean(),median_absolute_error=np.median(np.abs(err)),skill_vs_structural=1-mse/base if base else np.nan)

def loss_interval(g,first,second,repeats=1000):
 # Positive means first has lower MSE than second. Preserve provenance strata.
 rng=np.random.default_rng(42);groups=[]
 for _,q in g.groupby('provenance',sort=True):
  difference=(q[second].to_numpy()-q.y_ma5.to_numpy())**2-(q[first].to_numpy()-q.y_ma5.to_numpy())**2;groups.append(difference)
 draws=[]
 for _ in range(repeats):
  total=0
  for d in groups:
   starts=rng.integers(0,len(d),size=int(np.ceil(len(d)/30)));idx=((starts[:,None]+np.arange(30))%len(d)).ravel()[:len(d)];total+=d[idx].sum()
  draws.append(total/len(g))
 return dict(MSE_gain_first=float(np.mean((g[second]-g.y_ma5)**2-(g[first]-g.y_ma5)**2)),CI_low=float(np.quantile(draws,.025)),CI_high=float(np.quantile(draws,.975)))

def report(folder=ROOT):
 folder=Path(folder);data=pd.read_csv(folder/'all_time_X_y_context.csv.gz',low_memory=False);data.decision_at=pd.to_datetime(data.decision_at,utc=True);data.label_at=pd.to_datetime(data.label_at,utc=True)
 pred=predict(data,load_models(folder));columns=['decision_at','label_at','symbol','close','y_ma5','ma5_current','structural_persistence','label_valid','period','provenance','is_base_training_member','is_calibrator_training_member']
 output=pd.concat([data[columns],pred],axis=1);output.to_csv(folder/'all_time_predictions.csv.gz',index=False)
 scored=output.loc[output.y_ma5.notna()].copy();performance=[];comparisons=[]
 slices=[('period','ALL',scored)]+[('period',p,g) for p,g in scored.groupby('period')]+[('provenance',p,g) for p,g in scored.groupby('provenance')]
 for typ,period,g in slices:
  for model in ['prediction_lightgbm','prediction_isotonic','prediction_linear','structural_persistence','ma5_current']:
   performance.append(dict(slice_type=typ,period=period,model=model,**metrics(g.y_ma5,g[model],g.structural_persistence)))
  for first,second in [('prediction_isotonic','prediction_linear'),('prediction_isotonic','prediction_lightgbm'),('prediction_linear','prediction_lightgbm'),('prediction_isotonic','structural_persistence'),('prediction_linear','structural_persistence')]:comparisons.append(dict(slice_type=typ,period=period,first=first,second=second,**loss_interval(g,first,second)))
  print('Scored',typ,period,len(g),flush=True)
 perf=pd.DataFrame(performance);ci=pd.DataFrame(comparisons)
 coverage=output.groupby(['period','provenance'],as_index=False).agg(context_rows=('decision_at','size'),labeled_rows=('y_ma5','count'),first_decision=('decision_at','min'),last_decision=('decision_at','max'))
 perf.to_csv(folder/'performance.csv',index=False);ci.to_csv(folder/'paired_comparison_CI.csv',index=False);coverage.to_csv(folder/'coverage_and_periods.csv',index=False)
 plot(output,folder)
 metadata=json.loads((folder/'package_metadata.json').read_text())
 tables={'Performance':perf,'Paired_comparison_CI':ci,'Coverage_and_periods':coverage,'Predictions':output,'Feature_schema':pd.read_csv(folder/'feature_schema.csv')}
 notes=[('Models','Frozen fold3 LightGBM, followed by original fold3 isotonic or linear calibration. No refit on full history.'),('Target','Next completed-bar trailing MA5 price: four known closes plus next close. All errors THB quote units.'),('DEV','Exact earlier original-fold3 calibration fit rows. Scores are fitted for the calibrators.'),('OOT1','Exact later original-fold3 calibration evaluation rows, after30-row embargo. These observations were already inspected in prior analyses.'),('REST_2025','All Bangkok2025 rows: base-training backcasts. Calibrators use2026 parameters retrospectively; not an independent historical test.'),('REST_2026','Mixed additional2026 rows. Use provenance slices to distinguish base-training, embargo and later post-fold3 backtesting.'),('ALL','Descriptive mix of fitted and later observations. Never interpret as a single out-of-sample test.'),('Intervals','1000 paired circular30-observation bootstrap samples stratified by provenance. Positive MSE gain favors first model. Descriptive development evidence; no multiplicity correction.'),('Desktop inference','Run python predict_local.py or execute the notebook. Prepared X columns already contain original lags and fold3 Z seed; do not shift or fit preprocessing again.'),('Snapshot',metadata['snapshot_end_Bangkok']),('Artifacts','Individual model pickle files plus prediction_bundle.pkl; text/JSON equivalents preserve original parameters. Pinned requirements capture the export environment.')]
 with pd.ExcelWriter(folder/'Final_BaseModel_Comparison.xlsx',engine='xlsxwriter',engine_kwargs={'options':{'strings_to_formulas':False,'strings_to_urls':False}}) as writer:
  pd.DataFrame(notes,columns=['Topic','Explanation']).to_excel(writer,sheet_name='Read_me',index=False)
  for name,d in tables.items():
   d=d.copy()
   for c in d:
    if isinstance(d[c].dtype,pd.DatetimeTZDtype):d[c]=d[c].astype(str)
   d.to_excel(writer,sheet_name=name,index=False);sheet=writer.sheets[name];sheet.freeze_panes(1,0);sheet.autofilter(0,0,len(d),len(d.columns)-1);sheet.set_column(0,len(d.columns)-1,24)
  writer.sheets['Read_me'].set_column(0,0,28);writer.sheets['Read_me'].set_column(1,1,115,writer.book.add_format({'text_wrap':True}))
  for i in range(1,len(notes)+1):writer.sheets['Read_me'].set_row(i,45)
  chart=writer.book.add_worksheet('Plots');chart.insert_image('A1',str(folder/'all_time_actual_prediction.png'),{'x_scale':.7,'y_scale':.7})
 return perf,ci

def plot(output,folder):
 fig,axes=plt.subplots(3,1,figsize=(14,11),constrained_layout=True)
 p=output.sort_values('decision_at');visible=p.iloc[::4]
 for model,label,color in [('y_ma5','Actual','#111111'),('prediction_isotonic','Isotonic','#20895b'),('prediction_linear','Linear','#326cb8'),('prediction_lightgbm','Base LightGBM','#b4a4a4')]:axes[0].plot(visible.decision_at,visible[model],label=label,color=color,linewidth=.8)
 for name,color in [('REST_2025','#aaaaaa'),('DEV','#8bbaf1'),('OOT1','#8bd29d')]:
  q=p.loc[p.period.eq(name)]
  if not q.empty:axes[0].axvspan(q.decision_at.min(),q.decision_at.max(),color=color,alpha=.16,label=name)
 dev=p.loc[p.period.eq('DEV')];oot=p.loc[p.period.eq('OOT1')]
 rest=p.loc[p.period.eq('REST_2026')]
 masks=[rest.decision_at.lt(dev.decision_at.min()),rest.decision_at.between(dev.decision_at.max(),oot.decision_at.min()),rest.decision_at.gt(oot.decision_at.max())]
 first=True
 for mask in masks:
  q=rest.loc[mask]
  if not q.empty:
   axes[0].axvspan(q.decision_at.min(),q.decision_at.max(),color='#edb56b',alpha=.15,label='REST_2026' if first else None);first=False
 axes[0].set(title='Frozen fold3 models on all saved history;2025 is a retrospective training backcast',ylabel='Next MA5 (THB quote)');axes[0].legend(ncol=4,fontsize=8)
 q=p.loc[p.period.isin(['DEV','OOT1'])].iloc[::3]
 for model,label in [('y_ma5','Actual'),('prediction_isotonic','Isotonic'),('prediction_linear','Linear'),('structural_persistence','Structural baseline')]:axes[1].plot(q.decision_at,q[model],label=label,linewidth=.8)
 axes[1].set(title='DEV and OOT1; fit and later evaluation',ylabel='Next MA5 (THB quote)');axes[1].legend(ncol=4,fontsize=8)
 for model,label in [('prediction_isotonic','Isotonic'),('prediction_linear','Linear'),('structural_persistence','Structural baseline')]:axes[2].plot(visible.decision_at,visible[model]-visible.y_ma5,label=label,linewidth=.8)
 axes[2].axhline(0,color='black');axes[2].set(ylabel='Prediction minus actual',xlabel='Decision time (UTC)');axes[2].legend(ncol=3)
 fig.savefig(folder/'all_time_actual_prediction.png',dpi=150);plt.close(fig)

if __name__=='__main__':report()
