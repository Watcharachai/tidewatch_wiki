"""Assemble an auditable local inference/report package from existing frozen models."""
from pathlib import Path
import hashlib,json,pickle,shutil,sys,importlib.metadata
import numpy as np,pandas as pd
from sklearn.metrics import confusion_matrix,accuracy_score,balanced_accuracy_score,log_loss,brier_score_loss
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

P=Path(__file__).resolve().parent
SOURCE=P.parent
V21=SOURCE.parent
EVIDENCE='e83d6dd'
METHODS=['raw','isotonic','linear','quadratic','cubic']
PARTS=['TRAIN','TEST','OOT']

def copy_sources():
 for name in ['data','models','notebooks','evidence','plots']: (P/name).mkdir(exist_ok=True)
 shutil.copy2(V21/'Dataset_X_y.csv.gz',P/'data/Dataset_X_y.csv.gz')
 for name in ['Schedule.csv','Feature_dictionary.csv','Feature_quality.csv']:shutil.copy2(V21/name,P/'data'/name)
 for name in ['selected_summary.csv','selected_gain.csv','candidate_screen.csv','paired_OOT_intervals.csv']:
  shutil.copy2(SOURCE/name,P/'evidence'/name)
 for name in ['metrics.csv','regression_selection.csv','split_audit.csv','calibrator_parameters.csv']:
  shutil.copy2(SOURCE/'calibration_study'/name,P/'evidence'/('calibration_'+name))
 for model in SOURCE.glob('h*_compact.pkl'):shutil.copy2(model,P/'models'/model.name)
 for model in (SOURCE/'calibration_study').glob('h*.pkl'):shutil.copy2(model,P/'models'/model.name)
 for nb in [SOURCE/'Final_Baseline_Review.ipynb',SOURCE/'Quick_Calibration_Regression_Check.ipynb',SOURCE/'calibration_study/Calibration_Study.ipynb',V21/'MA5_V21_Training_Results.ipynb']:
  shutil.copy2(nb,P/'notebooks'/nb.name)
 for f in [SOURCE/'screen.py',SOURCE/'validate_selected.py',V21/'experiment.py']:
  shutil.copy2(f,P/'evidence'/('source_'+f.name))
 versions={name:importlib.metadata.version(name) for name in ['numpy','pandas','scikit-learn','lightgbm','matplotlib','python-docx','xlsxwriter','nbformat','nbclient','ipykernel']}
 (P/'requirements.txt').write_text('\n'.join(f'{name}=={version}' for name,version in versions.items())+'\n')
 return versions

def infer(data,h,task):
 bundle=pickle.load((P/f'models/h{h}_{task}_compact.pkl').open('rb'))
 names=bundle['feature_names']
 x=data[names].replace([np.inf,-np.inf],np.nan).fillna(bundle['medians']).to_numpy(float)
 x=(x-np.asarray(bundle['means']))/np.asarray(bundle['scales'])
 pred=bundle['model'].predict_proba(x)[:,1] if task=='classification' else data[f'baseline_h{h}'].to_numpy()+data.close.to_numpy()*(bundle['model'].predict(x)*bundle['target_scale']+bundle['target_mean'])
 outputs={'raw':pred}
 for method in METHODS[1:]:
  calibrator=pickle.load((P/f'models/h{h}_{task}_{method}.pkl').open('rb'))
  values=calibrator.predict(pred if method=='isotonic' else pred.reshape(-1,1))
  outputs[method]=np.clip(values,1e-6,1-1e-6) if task=='classification' else values
 return outputs

def reliability(y,prob,cuts):
 indices=np.searchsorted(cuts,prob,side='left');result=[]
 for k in range(len(cuts)+1):
  mask=indices==k;n=int(mask.sum());mean=float(prob[mask].mean()) if n else np.nan;rate=float(y[mask].mean()) if n else np.nan
  result.append(dict(bin=k+1,n=n,weight=n/len(y),mean_probability=mean,positive_rate=rate,abs_gap=abs(mean-rate) if n else 0.))
 return result,sum(r['weight']*r['abs_gap'] for r in result)

def class_metrics(y,prob,cuts):
 pred=(prob>.5).astype(int);tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel();_,ece=reliability(y,prob,cuts)
 return dict(n=len(y),accuracy=accuracy_score(y,pred),balanced_accuracy=balanced_accuracy_score(y,pred),precision=tp/(tp+fp) if tp+fp else np.nan,recall=tp/(tp+fn) if tp+fn else np.nan,TN=int(tn),FP=int(fp),FN=int(fn),TP=int(tp),actual_positive_rate=float(y.mean()),predicted_positive_rate=float(pred.mean()),mean_predicted_probability=float(prob.mean()),Brier=brier_score_loss(y,np.clip(prob,1e-6,1-1e-6)),ECE=ece,log_loss=log_loss(y,np.clip(prob,1e-6,1-1e-6)))

def price_metrics(y,pred,b):
 mse=np.mean((y-pred)**2);bmse=np.mean((y-b)**2)
 return dict(n=len(y),RMSE=float(np.sqrt(mse)),MAE=float(np.mean(abs(y-pred))),mean_error=float(np.mean(pred-y)),relative_RMSE=float(np.sqrt(mse/bmse)),skill_vs_structural=float(1-mse/bmse))

def assemble():
 versions=copy_sources()
 d=pd.read_csv(P/'data/Dataset_X_y.csv.gz',low_memory=False);d['decision_at']=pd.to_datetime(d.decision_at,utc=True)
 schedule=pd.read_csv(P/'data/Schedule.csv');partition=pd.Series('EXCLUDED',index=d.index)
 for r in schedule.itertuples():partition.loc[d.decision_at.between(pd.Timestamp(r.first),pd.Timestamp(r.last)) & d.eligible]=r.partition
 d['partition']=partition
 d['decision_Bangkok']=d.decision_at.dt.tz_convert('Asia/Bangkok');d['month']=d.decision_Bangkok.dt.strftime('%Y-%m')
 for part in PARTS:d[d.partition.eq(part)].to_csv(P/f'data/{part}_X_y.csv.gz',index=False)
 split=pd.read_csv(P/'evidence/calibration_split_audit.csv').set_index('set')
 selections=pd.read_csv(P/'evidence/calibration_regression_selection.csv').set_index('horizon')
 detail=[];monthly_r=[];monthly_c=[];perf_r=[];perf_c=[];descriptions=[];deciles=[];parameters=[]
 for h in range(1,6):
  data=d[d.partition.ne('EXCLUDED')].copy().reset_index(drop=True)
  y=data[f'y_h{h}'].to_numpy();base=data[f'baseline_h{h}'].to_numpy();binary=(y>data.ma5_current.to_numpy()).astype(int)
  r=infer(data,h,'regression');c=infer(data,h,'classification');winner=selections.loc[h,'selected_method']
  cuts=np.unique(np.quantile(c['raw'][data.partition.eq('TRAIN')],np.arange(.1,1,.1)))
  wide=data[['decision_at','decision_Bangkok','partition','month','close','ma5_current']].copy()
  wide['horizon']=h;wide['actual_MA5']=y;wide['structural_MA5']=base;wide['regression_raw']=r['raw'];wide['regression_calibrated']=r[winner];wide['regression_calibrator']=winner
  wide['actual_class']=binary;wide['structural_class']=(base>data.ma5_current.to_numpy()).astype(int)
  for method in METHODS:wide['prob_'+method]=c[method]
  for method in METHODS:wide['class_'+method]=(c[method]>.5).astype(int)
  wide.to_csv(P/f'data/predictions_h{h}.csv.gz',index=False);detail.append(wide)
  for part in PARTS:
   take=data.partition.eq(part).to_numpy();yd=y[take];bd=base[take];yc=binary[take]
   changes=yd-data.ma5_current.to_numpy()[take]
   descriptions.append(dict(partition=part,horizon=h,n=int(take.sum()),positive=int(yc.sum()),nonpositive=int(len(yc)-yc.sum()),positive_rate=float(yc.mean()),first=str(data.decision_Bangkok[take].min()),last=str(data.decision_Bangkok[take].max()),target_mean=float(yd.mean()),target_std=float(yd.std(ddof=1)),target_min=float(yd.min()),target_max=float(yd.max()),change_mean=float(changes.mean()),change_std=float(changes.std(ddof=1))))
  all_sets={part:data.partition.eq(part).to_numpy() for part in PARTS}
  for part in ['CAL_FIT','CAL_VALID']:
   row=split.loc[part];all_sets[part]=data.decision_at.between(pd.Timestamp(row.first_Bangkok),pd.Timestamp(row.last_Bangkok)).to_numpy() & data.partition.eq('TEST').to_numpy()
  for part,take in all_sets.items():
   for method in METHODS:
    perf_r.append(dict(partition=part,horizon=h,method=method,selected=(method==winner),**price_metrics(y[take],r[method][take],base[take])))
    perf_c.append(dict(partition=part,horizon=h,method=method,**class_metrics(binary[take],c[method][take],cuts)))
    table,ece=reliability(binary[take],c[method][take],cuts)
    deciles.extend(dict(horizon=h,partition=part,method=method,**z) for z in table)
   perf_r.append(dict(partition=part,horizon=h,method='structural',selected=False,**price_metrics(y[take],base[take],base[take])))
  for (part,month),group in data.groupby(['partition','month']):
   take=group.index.to_numpy()
   for method in ['raw',winner,'structural']:
    pred=base if method=='structural' else r[method]
    monthly_r.append(dict(partition=part,month=month,horizon=h,method=method,**price_metrics(y[take],pred[take],base[take])))
   for method in METHODS+['structural']:
    prob=(base>data.ma5_current.to_numpy()).astype(float) if method=='structural' else c[method]
    monthly_c.append(dict(partition=part,month=month,horizon=h,method=method,**class_metrics(binary[take],prob[take],cuts)))
  for task in ['regression','classification']:
   bundle=pickle.load((P/f'models/h{h}_{task}_compact.pkl').open('rb'))
   parameters.append(dict(horizon=h,task=task,features=json.dumps(bundle['feature_names']),model_parameters=json.dumps(bundle['model'].get_params(),sort_keys=True),target_mean=bundle.get('target_mean'),target_scale=bundle.get('target_scale'),calibration=winner if task=='regression' else 'all four retained'))
  print('Scored horizon',h,flush=True)
 tables={'Dataset_description':pd.DataFrame(descriptions),'Model_parameters':pd.DataFrame(parameters),'Regression_performance':pd.DataFrame(perf_r),'Classification_performance':pd.DataFrame(perf_c),'Monthly_regression':pd.DataFrame(monthly_r),'Monthly_classification':pd.DataFrame(monthly_c),'Calibration_deciles':pd.DataFrame(deciles),'Selected_models':pd.read_csv(P/'evidence/selected_summary.csv'),'Regression_selection':selections.reset_index(),'Calibration_splits':split.reset_index(),'Calibrator_parameters':pd.read_csv(P/'evidence/calibration_calibrator_parameters.csv')}
 tables['Calibration_fit_statistics']=pd.read_csv(P/'evidence/calibration_metrics.csv')
 gains=pd.read_csv(P/'evidence/selected_gain.csv')
 tables['Regression_features']=gains[gains.task.eq('regression')];tables['Classification_features']=gains[gains.task.eq('classification')]
 stability=[]
 for task in ['regression','classification']:
  tab=tables['Regression_performance' if task=='regression' else 'Classification_performance']
  for (h,method),group in tab.groupby(['horizon','method']):
   if method=='structural':continue
   group=group.set_index('partition')
   if task=='regression':
    tr=group.loc['TRAIN','relative_RMSE'];te=group.loc['TEST','relative_RMSE'];oot=group.loc['OOT','relative_RMSE'];g1=te-tr;g2=oot-tr
   else:
    tr=group.loc['TRAIN','accuracy'];te=group.loc['TEST','accuracy'];oot=group.loc['OOT','accuracy'];g1=tr-te;g2=tr-oot
   stability.append(dict(horizon=h,task=task,method=method,TRAIN=tr,TEST=te,OOT=oot,train_test_gap=g1,train_oot_gap=g2,within_2point_screen=bool(g1<=.02 and g2<=.02),interpretation='Calibrated TRAIN uses later TEST parameters; this gap is descriptive, not proof against overfitting.' if method!='raw' else 'Raw base-model stability check; gap threshold is a convention.'))
 tables['Stability_checks']=pd.DataFrame(stability)
 for name,tab in tables.items():tab.to_csv(P/'evidence'/f'{name}.csv',index=False)
 make_plots(detail,tables)
 make_excel(detail,tables)
 make_document(tables,versions)
 manifest={'source_commit':EVIDENCE,'snapshot_end':'2026-11-07 Asia/Bangkok','models_copied':len(list((P/'models').glob('*.pkl'))),'rows':len(d),'partition_rows':d.partition.value_counts().to_dict(),'model_refits':False,'versions':versions,'source_model_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (P/'models').glob('*.pkl')},'source_dataset_sha256':hashlib.sha256((P/'data/Dataset_X_y.csv.gz').read_bytes()).hexdigest()}
 (P/'package_metadata.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return tables

def make_plots(detail,tables):
 for h in range(1,6):
  data=detail[h-1];mr=tables['Monthly_regression'];mc=tables['Monthly_classification'];winner=tables['Regression_selection'].set_index('horizon').loc[h,'selected_method']
  for calibrated in [False,True]:
   method=winner if calibrated else 'raw';stage='calibrated' if calibrated else 'raw'
   fig,axes=plt.subplots(2,3,figsize=(17,8),constrained_layout=True)
   for col,part in enumerate(PARTS):
    q=data[data.partition.eq(part)].copy();time=pd.to_datetime(q.decision_at,utc=True).dt.tz_convert('Asia/Bangkok')
    segment=time.diff().ne(pd.Timedelta(minutes=15)).cumsum()
    for j,(_,z) in enumerate(q.groupby(segment)):
     t=pd.to_datetime(z.decision_at,utc=True).dt.tz_convert('Asia/Bangkok')
     axes[0,col].plot(t,z.actual_MA5,color='black',lw=.65,label='Actual' if j==0 else None)
     axes[0,col].plot(t,z['regression_calibrated' if calibrated else 'regression_raw'],color='#2563eb',lw=.65,alpha=.75,label='Predicted' if j==0 else None)
    axes[0,col].set(title=part,ylabel='Future MA5 / THB quote');axes[0,col].legend(fontsize=7)
    for name in [method,'structural']:
     z=mr[(mr.horizon==h)&(mr.partition==part)&(mr.method==name)]
     axes[1,col].plot(pd.to_datetime(z.month),z.RMSE,'-o',ms=3,label=name)
    axes[1,col].set(ylabel='Monthly RMSE',xlabel='Bangkok decision month');axes[1,col].legend(fontsize=7)
    for row in range(2):axes[row,col].tick_params(axis='x',rotation=35);axes[row,col].grid(alpha=.2)
   fig.suptitle(f'H{h} ({15*h} min) · {stage} regression · monthly price path and RMSE; boundary months partial')
   fig.savefig(P/f'plots/h{h}_{stage}_regression.png',dpi=115);plt.close(fig)
   methods=METHODS[1:] if calibrated else ['raw']
   fig,axes=plt.subplots(2,3,figsize=(17,8),constrained_layout=True)
   for col,part in enumerate(PARTS):
    for name in methods:
     z=mc[(mc.horizon==h)&(mc.partition==part)&(mc.method==name)].sort_values('month');t=pd.to_datetime(z.month)
     for metric,style in [('accuracy','-'),('precision','--'),('recall',':')]:axes[0,col].plot(t,z[metric],style,lw=1,label=name+' '+metric)
     axes[1,col].plot(t,z.predicted_positive_rate,lw=1,label=name+' predicted class %')
     axes[1,col].plot(t,z.mean_predicted_probability,lw=.7,ls=':',alpha=.65,label=name+' mean p')
    z=mc[(mc.horizon==h)&(mc.partition==part)&(mc.method=='structural')].sort_values('month');t=pd.to_datetime(z.month)
    axes[0,col].plot(t,z.accuracy,color='black',lw=1.5,label='Structural accuracy')
    axes[1,col].plot(t,z.actual_positive_rate,color='black',lw=2,label='Actual positive %')
    for row in range(2):
     axes[row,col].set(ylim=(0,1),xlabel='Bangkok month');axes[row,col].tick_params(axis='x',rotation=35);axes[row,col].grid(alpha=.2);axes[row,col].legend(fontsize=5,ncol=2)
    axes[0,col].set_title(part);axes[0,col].set_ylabel('Accuracy / precision / recall');axes[1,col].set_ylabel('Positive class fraction / mean p')
   fig.suptitle(f'H{h} ({15*h} min) · {stage} classification monthly metrics and target prevalence')
   fig.savefig(P/f'plots/h{h}_{stage}_classification.png',dpi=115);plt.close(fig)
  fig,axes=plt.subplots(1,3,figsize=(16,5),constrained_layout=True)
  dec=tables['Calibration_deciles'];stats=tables['Classification_performance']
  for ax,part in zip(axes,PARTS):
   ax.plot([0,1],[0,1],'k--')
   for method in METHODS:
    q=dec[(dec.horizon==h)&(dec.partition==part)&(dec.method==method)&(dec.n>0)]
    r=stats[(stats.horizon==h)&(stats.partition==part)&(stats.method==method)].iloc[0]
    ax.plot(q.mean_probability,q.positive_rate,'-o',ms=3,label=f'{method}: ECE {r.ECE:.3f}; Brier {r.Brier:.3f}')
   ax.set(title=part,xlim=(0,1),ylim=(0,1),xlabel='Predicted probability',ylabel='Observed positive fraction');ax.legend(fontsize=6);ax.grid(alpha=.2)
  fig.suptitle(f'H{h}: calibration with fixed raw TRAIN probability deciles')
  fig.savefig(P/f'plots/h{h}_calibration.png',dpi=115);plt.close(fig)
 print('25 figures generated',flush=True)

def make_excel(detail,tables):
 import xlsxwriter
 workbook=xlsxwriter.Workbook(P/'Final_Model_Summary.xlsx',{'constant_memory':True,'strings_to_urls':False,'nan_inf_to_errors':True})
 fmt_percent=workbook.add_format({'num_format':'0.00%'});fmt_number=workbook.add_format({'num_format':'0.000'})
 head=workbook.add_format({'bold':True,'bg_color':'#DDEBF7','text_wrap':True})
 mapping=[('3.1','Dataset_description','Size, dates, class proportions and price/change statistics'),('3.2','Model_parameters','Base models and target transforms; full calibration parameters in separate sheet'),('3.3','Regression_performance','Raw and all calibration metrics; classification and stability sheets follow'),('3.4','Predictions_h1..h5','Every partition row with actual price/class, raw/selected price forecast, all classification methods'),('3.5','H*_raw_regression','Price line charts and monthly RMSE'),('3.6','H*_raw_classification','Accuracy/precision/recall, actual/predicted positive rates and mean probability'),('3.7','Regression_features / Classification_features','Retained feature gain weights, separated by task'),('3.8','H*_calibration / Classification_performance','ECE reliability plots, Brier, log loss, accuracy and fixed TRAIN deciles'),('3.9','H*_calibrated_regression','Selected regression calibration, monthly price and RMSE'),('3.10','H*_calibrated_classification','All four calibrators, monthly class metrics and target rates')]
 notes=[('Dataset snapshot','Saved history ends 7 November 2026; package date 23 November 2026. No new market data fetched.'),('TRAIN','Base-model fitting. Calibration on earlier TEST applied to TRAIN retrospectively.'),('TEST','Full TEST mixes calibrator fit and validation; use CAL_VALID for selection.'),('OOT','Previously inspected final two calendar months; chronological but not pristine.'),('Selection','Regressors use minimum CAL_VALID RMSE; linear wins all five. Classification keeps all four calibrators.'),('Overfitting','Base screen compares <=2-point train/test/OOT gap, normalized by structural RMSE for regression. Cannot prove no overfitting. CAL_FIT/CAL_VALID/OOT provide calibration generalization evidence.'),('Benchmark','No compact base model showed a positive lower paired OOT improvement interval vs structural persistence.'),('Probabilities','Polynomial outputs clipped to [1e-6,1-1e-6]. Repeated TRAIN decile quantiles merged. ECE weighted by set counts.'),('Monthly','Bangkok decision month; partial split boundary months; row counts reported. Charts align future MA5 to its decision time.'),('Target','Class 1 iff future MA5 > current MA5; regression future trailing MA5 h=1..5. Known-price overlap contributes to high accuracy.'),('Methods','Isotonic, linear, quadratic/square degree 2, cubic degree 3. Calibration fit first half TEST, 30 context-bar gap to later TEST validation.'),('Notebook archive','Original notebooks are preserved for evidence and need their original source directory; Final_Package_Review.ipynb is standalone within this package.')]
 def sheet(name,frame):
  ws=workbook.add_worksheet(name[:31]);ws.freeze_panes(1,0);ws.write_row(0,0,frame.columns.tolist(),head);ws.set_column(0,len(frame.columns)-1,20)
  for i,row in enumerate(frame.itertuples(index=False,name=None),1):
   for j,value in enumerate(row):
    if pd.isna(value):continue
    if isinstance(value,(np.integer,np.floating)):value=value.item()
    if isinstance(value,pd.Timestamp):value=str(value)
    ws.write(i,j,value)
  ws.autofilter(0,0,len(frame),len(frame.columns)-1)
  return ws
 ws=sheet('Read_me',pd.DataFrame(notes,columns=['topic','explanation']));ws.set_column(1,1,110)
 sheet('Coverage_map',pd.DataFrame(mapping,columns=['Requested_item','Sheet','Contents']))
 for name,tab in tables.items():sheet(name,tab)
 for h,frame in enumerate(detail,1):
  f=frame.copy()
  for col in ['decision_at','decision_Bangkok']:f[col]=f[col].astype(str)
  sheet(f'Predictions_h{h}',f)
 for h in range(1,6):
  for plot in ['raw_regression','raw_classification','calibrated_regression','calibrated_classification','calibration']:
   ws=workbook.add_worksheet(f'H{h}_{plot}'[:31]);ws.insert_image('A1',str(P/f'plots/h{h}_{plot}.png'),{'x_scale':.8,'y_scale':.8})
 workbook.close();print('Workbook generated',flush=True)


def make_document(tables,versions):
 doc=Document();section=doc.sections[0];section.top_margin=section.bottom_margin=Inches(.65)
 section.left_margin=section.right_margin=Inches(.65)
 doc.styles['Normal'].font.name='Calibri';doc.styles['Normal'].font.size=Pt(10)
 doc.add_heading('MTS GLD965 MA5 Baseline\nFinal Research Package',0)
 doc.add_paragraph('23 November 2026 · Asia/Bangkok · 15-minute bars · horizons 1–5',style='Subtitle')
 def para(text):doc.add_paragraph(text)
 def table(frame):
  t=doc.add_table(rows=1,cols=len(frame.columns));t.style='Light Shading Accent 1'
  for c,v in zip(t.rows[0].cells,frame.columns):c.text=str(v)
  for row in frame.itertuples(index=False,name=None):
   for c,v in zip(t.add_row().cells,row):c.text=(f'{v:.4f}' if isinstance(v,float) else str(v)) if not pd.isna(v) else '—'
  for row in t.rows:
   for c in row.cells:
    for p in c.paragraphs:
     for r in p.runs:r.font.size=Pt(8)
 def heading(text):doc.add_heading(text,1)
 heading('1. General purpose')
 para('Forecast direct MTS GLD965 future trailing five-close averages and their direction relative to the current observed MA5 at 15, 30, 45, 60 and 75 minutes. This package consolidates the selected compact LightGBM research models and single-input calibration experiments. Four-classifier calibrations are retained; regression calibration is chosen by later-TEST RMSE. The source snapshot ends 7 November 2026.')
 para('All ten compact base models pass the requested TRAIN gain constraints and declared historical stability screen. None demonstrated a positive lower paired OOT improvement interval over structural persistence. This is a reproducible research baseline package; model reliability still needs prospective evidence.')
 heading('2. Assumptions and model setting')
 doc.add_heading('2.1 Dataset description (Excel 3.1)',2)
 para('Base models fit 24,194 TRAIN rows, with 10,372 TEST and 3,629 OOT rows. The last two Bangkok calendar months form OOT. Earlier eligible history is split 70/30 by time; labels crossing boundaries are purged. A common eligible sample requires completed current MA5 and five future contiguous 15-minute bars. No market gaps are filled. All context rows are retained in the source table; separate split files contain the scored samples.')
 desc=tables['Dataset_description'];table(desc[['partition','horizon','n','positive_rate','target_mean','target_std']])
 para('The dataset dates and exact class counts are in Dataset_description and Schedule. TRAIN has more positive labels than OOT; volatility differs across periods. Intraday price quote units are THB chart units, with execution side and weight basis not independently verified. The original architecture’s GLD9999, other intervals, news and MDP layers are outside this frozen GLD965 package.')
 doc.add_heading('2.2 Target and baseline',2)
 para('Y_h = mean(P[t+h−4], …, P[t+h]). Structural persistence replaces every future required close with current close P[t]. Regression fits u_h=(Y_h−B_h)/P[t], then reconstructs Y_hat=B_h+P[t]*u_hat. Classification labels 1 when Y_h exceeds current MA5, else 0. At h=1 four of five target prices are already known, which makes MA5 direction and price-level R² mechanically strong. Structural persistence is the relevant benchmark.')
 heading('3. Model development')
 doc.add_heading('3.1 Features and parameters (Excel 3.2 and 3.7)',2)
 para('Raw price levels and daily macro inputs are excluded. Candidates include own completed log returns, rolling return moments and trend gaps, bar body/range, calendar context and inherited delayed source returns. TRAIN-only null >=20% and zero-variance screens precede the original search. Compact sets are derived from TRAIN gain rankings; model choice uses TEST RMSE or log loss. Every retained feature has >=5% TRAIN gain, maximum <=70%, and at least three features are retained. Feature weights are split-gain shares, not signed coefficients or causal effects. Separate regression and classification sheets provide every selected feature and weight.')
 selected=tables['Selected_models'];table(selected[['horizon','task','features','min_gain_share','max_gain_share']])
 para('LightGBM uses shallow depth 2 or 3, corresponding 3 or 7 leaves, column sampling 0.7, L2 penalty 10 and seed 42. Tree count, learning rate and minimum leaf samples follow the previous TEST-selected tuning. Regression uses Huber objective on standardized residuals; classification uses binary probabilities with p>0.5. Exact parameter JSON, ordered features, imputation medians, X scale and target transformation are preserved in each trusted model bundle and the workbook.')
 doc.add_heading('3.2 Performance and stability (Excel 3.3)',2)
 para('RMSE and MAE measure price error in original THB quote units. Classification reports accuracy, balanced accuracy, precision, recall, confusion counts, log loss, Brier and ECE. TRAIN and TEST/OOT base-model performance gaps are compared against a declared 2-point limit: relative RMSE=RMSE(model)/RMSE(structural) for regression; absolute accuracy gaps for classification. Passing this convention cannot prove no overfitting. Calibrated TRAIN results are retrospective because the calibrator is fitted later on TEST; their gap is descriptive. Calibration fit versus later validation provides the relevant fitting-optimism check.')
 para('TRAIN-derived model features and preprocessing are frozen. OOT dates have been viewed in earlier project work, and the feature search was broadened after earlier screens; results are exploratory. A future untouched prospective period is needed before a live-use claim. Original paired 1,000-sample 30-row circular bootstrap intervals show no compact model with statistically resolved positive OOT gain versus structural persistence; the intervals are exported under evidence.')
 doc.add_heading('3.3 Calibration and model selection (Excel 3.8)',2)
 para('Each calibrator receives only the base forecast. Regression X/Y are predicted/actual MA5 prices. Classification X is predicted probability and Y is the binary outcome. Fit methods: increasing isotonic with clipping outside fitted range, linear, quadratic/square (degree 2), and cubic (degree 3). Polynomial X is standardized within calibration fitting for numerical stability. Classification polynomial outputs are clipped to valid probabilities; raw out-of-range rates remain visible in original calibration metrics.')
 para('Calibrators fit the earlier half of TEST, filtering labels that mature before the split boundary, then leave a 30-original-context-bar gap to later TEST validation. Each regression horizon chooses lowest CAL_VALID RMSE among the four calibrators; linear wins all five. All four classification methods remain available. Full TEST mixes fitted and validation observations. OOT does not choose the calibrator. Isotonic price clipping performs poorly under OOT prices outside the fit range.')
 table(tables['Regression_selection'])
 para('ECE uses raw TRAIN probability-decile cutoffs, fixed across models and sets; quantile ties merge. ECE=sum_k (n_k/N)*|mean p_k−positive fraction_k|. Brier=mean((p−y)^2). Both are reported, since ECE depends on binning and Brier combines reliability and discrimination. Reliable probabilities alone do not establish greater directional skill than the structural rule.')
 doc.add_heading('3.4 OOT numerical comparison',2)
 table(tables['Regression_performance'].query('partition=="OOT" and method in ["raw","linear","structural"]')[['horizon','method','RMSE','MAE','relative_RMSE']])
 table(tables['Classification_performance'].query('partition=="OOT"')[['horizon','method','accuracy','precision','recall','Brier','ECE']])
 heading('4. Result implementation and empirical analysis')
 doc.add_heading('4.1 Actual versus prediction and monthly regression (Excel 3.4, 3.5, 3.9)',2)
 para('Each horizon has a full prediction CSV and Excel sheet with decision time, partition, actual close/current MA5, future actual target, structural forecast, raw base forecast, selected calibrated forecast, and all classification probabilities and classes. Monthly regression tables report row count, RMSE, MAE, bias and structural-relative error by Bangkok decision month and partition. Plots show actual/predicted MA5 and monthly RMSE for TRAIN, TEST and OOT; raw and selected calibrated results have separate pages. Lines break at noncontiguous bars. Price levels can overlap visually despite important error differences.')
 doc.add_heading('4.2 Monthly classification (Excel 3.6, 3.10)',2)
 para('Raw and all four calibrated classifiers are compared by month: accuracy, positive-class precision and recall, actual positive share, predicted positive-class share and average probability. Average predicted probability and predicted class prevalence measure different quantities, so both are plotted. Structural direction accuracy is shown alongside. Boundary months can be partial; their sample size is explicitly exported. These tables should be consulted before treating a high one-month score as stable skill.')
 doc.add_heading('4.3 Local inference',2)
 para('Create a Python 3.12 environment using requirements.txt. Open Final_Package_Review.ipynb from this folder and execute it to reproduce inference tables and display figures. Models are loaded from models/, data from data/. Run python build_package.py --report to regenerate derived reports using the bundled source artifacts; the default full build copies source evidence from the original repository hierarchy. No retraining is needed. The copied original notebooks in notebooks/ are archival evidence and retain their original working-directory assumptions.')
 para('Regression bundles require ordered features, saved median imputation and scaling; the Booster output is normalized residual Y. Invert target scaling and add structural baseline plus current-close scale before calibration. Polynomial calibrators accept an n-by-1 raw forecast; isotonic accepts 1-D. Classification clipping follows the original notebook. New raw live data require the original feature pipeline and causal state, not merely adding timestamps to the prepared file.')
 heading('5. Limitations and further improvement')
 para('Model selection, strict feature-gain diversity and prior inspection can increase research optimism. No feature is guaranteed to carry future information just because it has >=5% split gain. Classifiers had to drop dominant signals to meet diversity requirements, reducing predictive accuracy. Calibration cannot create future information absent from base output. Polynomial probabilities can exceed [0,1], and isotonic clips outside fit range. Daily macro timestamps and source availability remain data assumptions from the earlier pipeline. MA5 overlap induces serial dependence. No executable trading costs, position sizing, news policy or profitability model is included.')
 para('Next priorities: freeze the selected research package, collect genuinely new future data, verify timestamps and source freshness, monitor structural-relative error and calibration monthly, and test the unknown next-price innovation directly if the objective is return predictability. Retain structural persistence as the practical reference/fallback. Do not infer deployment acceptance from the gain or historical stability screens.')
 heading('6. GitHub file reference and coverage')
 prefix='https://github.com/Watcharachai/tidewatch_wiki/blob/main/research/mts_gold/training_artifacts/_training_baseline/ma5_multihorizon_v21/final_baseline_screen/'
 for label,path in [('Final workbook','final_research_package/Final_Model_Summary.xlsx'),('Standalone notebook','final_research_package/Final_Package_Review.ipynb'),('Package instructions','final_research_package/README.md'),('Original feature-selection notebook','Final_Baseline_Review.ipynb'),('Original calibration notebook','calibration_study/Calibration_Study.ipynb'),('Full calibration metrics','calibration_study/metrics.csv')]:
  p=doc.add_paragraph();h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(prefix+path,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True));r=OxmlElement('w:r');t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)
 para('Workbook coverage: 3.1 Dataset_description; 3.2 Model_parameters and Calibrator_parameters; 3.3 Regression_performance, Classification_performance and Stability_checks; 3.4 Predictions_h1–h5; 3.5/3.6 raw horizon charts and monthly tables; 3.7 separate feature sheets; 3.8 calibration plots and deciles; 3.9/3.10 calibrated horizon charts. All numeric source tables are also supplied as CSV under evidence/.')
 for h in range(1,6):
  for plot,title in [('raw_regression','Raw regression: actual/predicted and monthly RMSE'),('raw_classification','Raw classification: metrics and target prevalence'),('calibration','Calibration: ECE and Brier reliability diagrams'),('calibrated_regression','Calibrated regression: actual/predicted and monthly RMSE'),('calibrated_classification','Calibrated classification: all four methods monthly')]:
   doc.add_page_break();doc.add_heading(f'Horizon {h}: {15*h} minutes',1);doc.add_heading(title,2)
   doc.add_picture(str(P/f'plots/h{h}_{plot}.png'),width=Inches(7.1))
   para('TRAIN is base-model fitting; calibrated TRAIN applies TEST-fitted parameters retrospectively. Full TEST mixes calibration fitting and validation. OOT was previously inspected. All month labels use Bangkok decision time; boundary months are partial. Interpret charts with the exported row counts and structural comparisons.')
 doc.core_properties.title='MTS GLD965 MA5: Final Baseline and Calibration Research Package'
 doc.save(P/'Model_Documentation.docx');print('DOCX generated',flush=True)

if __name__=='__main__':
 if '--report' in sys.argv:
  # Build reports only from bundled artifacts, preserving source-copy provenance.
  copy_sources=lambda:json.loads((P/'package_metadata.json').read_text())['versions']
 assemble()
