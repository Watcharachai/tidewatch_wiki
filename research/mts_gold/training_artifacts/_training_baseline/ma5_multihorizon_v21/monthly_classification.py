"""Monthly directional validation and actual-price charts from frozen v2.1 predictions."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'monthly_classification'
MODELS=['Structural','Logistic','LightGBM','TrainPrior']
PARTITIONS=['TRAIN','TEST','OOT']

def run():
 OUT.mkdir(exist_ok=True)
 p=pd.read_csv(ROOT/'Predictions.csv.gz',low_memory=False)
 p=p.loc[p.task.eq('classification') & p.model.isin(MODELS)].copy()
 p['decision_at']=pd.to_datetime(p.decision_at,utc=True).dt.tz_convert('Asia/Bangkok')
 p['month']=p.decision_at.dt.strftime('%Y-%m')
 # One row per period, horizon, model, and Bangkok decision month.
 rows=[]
 for (part,h,month,model),g in p.groupby(['partition','horizon','month','model'],sort=True):
  actual=g.actual_class.to_numpy(dtype=int);pred=g.predicted_class.to_numpy(dtype=int)
  tn=int(((actual==0)&(pred==0)).sum());fp=int(((actual==0)&(pred==1)).sum())
  fn=int(((actual==1)&(pred==0)).sum());tp=int(((actual==1)&(pred==1)).sum());n=len(g)
  rows.append({'partition':part,'horizon':h,'month_Bangkok':month,'model':model,'rows':n,
   'actual_positive':int(actual.sum()),'predicted_positive':int(pred.sum()),'actual_positive_rate':actual.mean(),
   'TN':tn,'FP':fp,'FN':fn,'TP':tp,'accuracy':(tp+tn)/n,
   'precision_positive':tp/(tp+fp) if tp+fp else np.nan,
   'recall_positive':tp/(tp+fn) if tp+fn else np.nan,
   'balanced_accuracy':.5*(tp/(tp+fn)+tn/(tn+fp)) if (tp+fn and tn+fp) else np.nan})
 m=pd.DataFrame(rows).sort_values(['horizon','partition','month_Bangkok','model'])
 m.to_csv(OUT/'monthly_metrics.csv',index=False)
 # Match each classifier's row with the structural benchmark on the same date and horizon.
 baseline=m[m.model.eq('Structural')][['partition','horizon','month_Bangkok','accuracy']].rename(columns={'accuracy':'structural_accuracy'})
 m=m.merge(baseline,on=['partition','horizon','month_Bangkok'],validate='many_to_one')
 m['accuracy_minus_structural']=m.accuracy-m.structural_accuracy
 m.to_csv(OUT/'monthly_metrics_with_baseline.csv',index=False)
 snapshot=pd.read_csv(ROOT/'Dataset_X_y.csv.gz',usecols=['decision_at','close','ma5_current'],low_memory=False)
 snapshot['decision_at']=pd.to_datetime(snapshot.decision_at,utc=True).dt.tz_convert('Asia/Bangkok')
 q=p[p.partition.eq('OOT') & p.model.eq('Logistic')].merge(snapshot,on='decision_at',validate='many_to_one')
 q.to_csv(OUT/'oot_logistic_price_and_signals.csv.gz',index=False)
 for h in range(1,6):
  a=m[m.horizon.eq(h)].copy();fig,axes=plt.subplots(3,1,figsize=(15,10),sharex=True,constrained_layout=True)
  for ax,metric,label in zip(axes,['accuracy','precision_positive','recall_positive'],['Accuracy','Positive precision','Positive recall']):
   for model,color in [('Structural','#4b5563'),('Logistic','#2563eb'),('LightGBM','#ea580c')]:
    z=a[a.model.eq(model)].sort_values('month_Bangkok');ax.plot(pd.to_datetime(z.month_Bangkok),z[metric],marker='o',lw=1.6,label=model,color=color)
   ax.set(ylabel=label,ylim=(0,1));ax.grid(alpha=.25)
   for boundary in ['TEST','OOT']:
    t=p[p.partition.eq(boundary)].decision_at.min().tz_localize(None)
    ax.axvline(t,color='#8b5cf6' if boundary=='TEST' else '#059669',ls='--',alpha=.75,label=boundary+' starts')
  axes[0].legend(ncol=5,fontsize=8,loc='lower left');fig.suptitle(f'GLD965 MA5 direction · horizon {h} ({h*15} min) · Bangkok decision month')
  axes[-1].set_xlabel('Bangkok month; short boundary months have fewer observations')
  fig.savefig(OUT/f'h{h}_monthly_metrics.png',dpi=145);plt.close(fig)
  z=q[q.horizon.eq(h)].sort_values('decision_at');fig,ax=plt.subplots(figsize=(15,5),constrained_layout=True)
  segments=z.decision_at.diff().ne(pd.Timedelta(minutes=15)).cumsum()
  for i,(_,segment) in enumerate(z.groupby(segments)):
   ax.plot(segment.decision_at,segment.close,color='#929292',lw=.75,label='Current MTS close' if i==0 else None)
   ax.plot(segment.decision_at,segment.actual,color='#111827',lw=.85,label=f'Actual future MA5 (h={h})' if i==0 else None)
  wrong=z[z.actual_class.ne(z.predicted_class)]
  ax.scatter(wrong.decision_at,wrong.actual,s=9,c=np.where(wrong.predicted_class.eq(1),'#dc2626','#7c3aed'),alpha=.75,label='Logistic wrong calls (red=FP, purple=FN)')
  ax.set(title=f'OOT actual MTS close and next MA5 · Logistic direction errors · h={h}',xlabel='Decision time (Asia/Bangkok)',ylabel='THB chart quote');ax.legend(fontsize=8,loc='best');ax.grid(alpha=.2)
  fig.savefig(OUT/f'h{h}_oot_actual_price_and_errors.png',dpi=145);plt.close(fig)
 notes=pd.DataFrame([
  ('Meaning','Class 1 if future trailing MA5 > current observed MA5; ties=0. Positive precision=TP/(TP+FP), recall=TP/(TP+FN).'),
  ('Time','Months and chart x-axes use Bangkok decision time. Split boundaries follow original saved partition; the first/last month of a partition can be partial.'),
  ('Sample','All v2.1 common eligible rows for the corresponding partition/horizon; monthly rows can be small and noisy.'),
  ('Comparison','Structural uses same rows; accuracy difference = model accuracy minus structural accuracy. High MA5 accuracy can come from overlap/known prices.'),
  ('Price chart','Gray=current MTS close at decision; black=actual future MA5 aligned to that decision. Red/purple dots are Logistic false-positive/false-negative calls, plotted at actual future MA5.'),
  ('OOT status','Chronologically last two months, previously inspected in earlier research; not an untouched prospective test.')],columns=['topic','explanation'])
 with pd.ExcelWriter(OUT/'Monthly_Classification_Analysis.xlsx',engine='xlsxwriter',engine_kwargs={'options':{'strings_to_urls':False}}) as writer:
  notes.to_excel(writer,sheet_name='Read_me',index=False)
  writer.sheets['Read_me'].set_column(1,1,110,writer.book.add_format({'text_wrap':True}))
  for i in range(1,len(notes)+1):writer.sheets['Read_me'].set_row(i,48)
  m.to_excel(writer,sheet_name='Monthly_metrics',index=False)
  writer.sheets['Monthly_metrics'].freeze_panes(1,0)
  writer.sheets['Monthly_metrics'].set_column(0,len(m.columns)-1,19)
  for h in range(1,6):
   sheet=writer.book.add_worksheet(f'H{h}_charts')
   sheet.insert_image('A1',str(OUT/f'h{h}_monthly_metrics.png'),{'x_scale':.7,'y_scale':.7})
   sheet.insert_image('A48',str(OUT/f'h{h}_oot_actual_price_and_errors.png'),{'x_scale':.7,'y_scale':.7})
 print(m[m.partition.eq('OOT') & m.model.isin(['Logistic','LightGBM','Structural'])][['horizon','month_Bangkok','model','rows','accuracy','precision_positive','recall_positive','accuracy_minus_structural']].to_string(index=False))
 return m
if __name__=='__main__':run()
