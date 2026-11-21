"""Quarterly pairwise time-series plots with frozen DEV residual percentile bands."""
from pathlib import Path
import json
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
ROOT=Path(__file__).resolve().parent
MODELS={'prediction_isotonic':'Isotonic','prediction_linear':'Linear','structural_persistence':'Structural persistence','prediction_lightgbm':'Uncalibrated LightGBM'}
TZ=ZoneInfo('Asia/Bangkok')

def make_report(folder=ROOT):
 folder=Path(folder);out=folder/'quarterly_plots';out.mkdir(exist_ok=True)
 f=pd.read_csv(folder/'all_time_predictions.csv.gz');f.decision_at=pd.to_datetime(f.decision_at,utc=True)
 f['decision_Bangkok']=f.decision_at.dt.tz_convert(TZ)
 f['quarter']=f.decision_Bangkok.dt.tz_localize(None).dt.to_period('Q').astype(str)
 dev=f.loc[f.period.eq('DEV')&f.y_ma5.notna()];assert len(dev)==4030
 quantiles=[];coverage=[];bounds=[];charts=[]
 frozen={}
 for col,name in MODELS.items():
  residual=(dev.y_ma5-dev[col]).to_numpy()
  q=np.quantile(residual,[.025,.05,.95,.975])
  frozen[col]=q
  quantiles.append(dict(model=name,column=col,DEV_rows=len(dev),residual_P025=q[0],residual_P05=q[1],residual_P95=q[2],residual_P975=q[3],
   width_90=q[2]-q[1],width_95=q[3]-q[0],estimated_from='Actual minus prediction on original DEV fit rows only; approximate in-sample residual bands'))
  d=f[['decision_at','quarter','period','provenance','y_ma5']].copy();d['model']=name;d['prediction']=f[col]
  for key,value in zip(['lower_95','P05_lower_90','P95_upper_90','upper_95'],q):d[key]=f[col]+value
  bounds.append(d)
 boundaries={period:(f.loc[f.period.eq(period),'decision_Bangkok'].min(),f.loc[f.period.eq(period),'decision_Bangkok'].max()) for period in ['DEV','OOT1']}
 selections=[(q,g) for q,g in f.groupby('quarter',sort=True)]+[('DEV',f.loc[f.period.eq('DEV')])]
 for label,g in selections:
  charts.append(draw(g,label,frozen,out,boundaries))
  scored=g.loc[g.y_ma5.notna()]
  for col,name in MODELS.items():
   q=frozen[col];res=scored.y_ma5-scored[col]
   coverage.append(dict(period=label,model=name,context_rows=len(g),scored_rows=len(scored),
    first_decision_Bangkok=str(g.decision_Bangkok.min()),last_decision_Bangkok=str(g.decision_Bangkok.max()),
    empirical_coverage_90=float(res.between(q[1],q[2]).mean()),empirical_coverage_95=float(res.between(q[0],q[3]).mean()),
    residual_below_P05_fraction=float(res.lt(q[1]).mean()),residual_above_P95_fraction=float(res.gt(q[2]).mean()),
    RMSE=float(np.sqrt(np.mean(res**2))),band_source='Frozen original DEV residual distribution',
    interpretation='2025 retrospective backcast using2026 parameters' if label.startswith('2025') else 'DEV in-sample; other periods previously inspected development/backtest data'))
 qtable=pd.DataFrame(quantiles);ctable=pd.DataFrame(coverage)
 qtable.to_csv(out/'DEV_residual_percentiles.csv',index=False);ctable.to_csv(out/'Quarterly_band_coverage.csv',index=False)
 pd.concat(bounds,ignore_index=True).to_csv(out/'All_time_prediction_bounds.csv.gz',index=False)
 notes=[('Meaning','P05/P95 form a central90% empirical prediction band. P2.5/P97.5 form a separate95% band. These are not confidence intervals for the conditional mean.'),
 ('Construction','Lower/upper bounds = saved model prediction + the corresponding quantile of Actual minus prediction on DEV. Asymmetric additive offsets remain frozen across every quarter. Each model has its own DEV residual quantiles.'),
 ('DEV','Original4030 calibration-fit rows,2026-02-12 to2026-04-21 Bangkok. Residuals are in-sample for calibrators; widths may be optimistic. No models are refitted.'),
 ('Coverage','Measured against actuals wherever labels exist. Nominal90/95% levels are not guaranteed under serial dependence or regime change. Coverage in later blocks is the empirical check.'),
 ('2025','Backcasts using base-training data and later2026 calibrator/band parameters. Bands are retrospective illustrations, not uncertainty forecasts available at the historical date.'),
 ('Dates','Quarters use Asia/Bangkok decision times. Actual is the next-bar trailing MA5 target aligned to decision time.2026Q4 is partial through the saved November7 snapshot.'),
 ('Plots','Each quarter has four separate actual/prediction panels. Darker blue is P05–P95 (90%); lighter blue is P2.5–P97.5 (95%). DEV and OOT1 boundaries are marked where present. No daily averaging or line smoothing.'),
 ('Numeric values','DEV residual percentile offsets and coverage are in this workbook. Every timestamp/model prediction and all four numeric bounds are in All_time_prediction_bounds.csv.gz.'),
 ('Scope','Previously inspected historical development evidence. No new prices fetched and no pickle or forecast values changed.')]
 with pd.ExcelWriter(folder/'Quarterly_Prediction_Bands.xlsx',engine='xlsxwriter',engine_kwargs={'options':{'strings_to_formulas':False,'strings_to_urls':False}}) as w:
  pd.DataFrame(notes,columns=['Topic','Explanation']).to_excel(w,sheet_name='Read_me',index=False)
  qtable.to_excel(w,sheet_name='DEV_percentiles',index=False);ctable.to_excel(w,sheet_name='Quarterly_coverage',index=False)
  for name,d in [('DEV_percentiles',qtable),('Quarterly_coverage',ctable)]:
   s=w.sheets[name];s.freeze_panes(1,0);s.autofilter(0,0,len(d),len(d.columns)-1);s.set_column(0,len(d.columns)-1,24)
  w.sheets['Read_me'].set_column(0,0,24);w.sheets['Read_me'].set_column(1,1,115,w.book.add_format({'text_wrap':True}))
  for i in range(1,len(notes)+1):w.sheets['Read_me'].set_row(i,55)
  for path in charts:
   sheet=w.book.add_worksheet(path.stem[:31]);sheet.insert_image('A1',str(path),{'x_scale':.7,'y_scale':.7})
 (out/'band_method.json').write_text(json.dumps({'percentiles':[.025,.05,.95,.975],'reference_period':'DEV','reference_rows':4030,'construction':'prediction + frozen empirical DEV residual percentile','confidence_interval_for_mean':False,'nominal_coverage_guaranteed':False,'timezone':'Asia/Bangkok','charts':[p.name for p in charts]},indent=2)+'\n')
 return qtable,ctable,charts

def draw(g,label,frozen,out,boundaries):
 fig,axes=plt.subplots(4,1,figsize=(14,12),sharex=True,constrained_layout=True)
 for ax,(col,name) in zip(axes,MODELS.items()):
  x=g.decision_Bangkok;pred=g[col].to_numpy();q=frozen[col]
  ax.fill_between(x,pred+q[0],pred+q[3],color='#729fd2',alpha=.18,label='95% band: P2.5–P97.5',linewidth=0)
  ax.fill_between(x,pred+q[1],pred+q[2],color='#326cb8',alpha=.25,label='90% band: P05–P95',linewidth=0)
  ax.plot(x,g.y_ma5,color='#202020',linewidth=.65,label='Actual next MA5');ax.plot(x,pred,color='#245daa',linewidth=.8,label=name)
  ax.set_ylabel('THB quote');ax.set_title(f'{name}: actual vs predicted',fontsize=10);ax.grid(alpha=.12)
  for period,color in [('DEV','#3b8c63'),('OOT1','#b67a28')]:
   for value,edge in zip(boundaries[period],['start','end']):
    if g.decision_Bangkok.min()<=value<=g.decision_Bangkok.max():
     ax.axvline(value,color=color,linestyle=':',linewidth=.7)
     if ax is axes[0]:ax.text(value,.98,f'{period} {edge}',transform=ax.get_xaxis_transform(),rotation=90,va='top',ha='right',fontsize=6,color=color)
  ax.legend(loc='upper left',ncol=4,fontsize=7)
 axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5,maxticks=9,tz=TZ));axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%d %b',tz=TZ));axes[-1].set_xlabel('Decision time (Asia/Bangkok); 15m observations, no aggregation')
 qualifier='2025 retrospective backcast; bands estimated with2026 DEV data' if label.startswith('2025') else 'DEV fit view: nominal coverage is in-sample' if label=='DEV' else 'Historical development/backtest view; bands fixed from DEV'
 partial=' — partial quarter through7 Nov2026' if label=='2026Q4' else ''
 fig.suptitle(f'{label}{partial}\n{qualifier}',fontsize=12)
 path=out/f'{label}_actual_vs_models.png';fig.savefig(path,dpi=120);plt.close(fig);return path

if __name__=='__main__':make_report()
