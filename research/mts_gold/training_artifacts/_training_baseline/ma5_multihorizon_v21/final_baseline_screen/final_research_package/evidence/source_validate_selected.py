"""Reproduce compact OOT forecasts; paired block intervals versus structural persistence."""
from pathlib import Path
import pickle
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent.parent;OUT=Path(__file__).resolve().parent

def interval(gains,repeats=1000):
 rng=np.random.default_rng(42);n=len(gains);width=30;draws=[]
 for _ in range(repeats):
  starts=rng.integers(0,n,size=int(np.ceil(n/width)));ix=((starts[:,None]+np.arange(width))%n).ravel()[:n];draws.append(np.mean(gains[ix]))
 return np.quantile(draws,[.025,.975])

def main():
 d=pd.read_csv(ROOT/'Dataset_X_y.csv.gz',low_memory=False);dates=pd.to_datetime(d.decision_at,utc=True)
 s=pd.read_csv(ROOT/'Schedule.csv').query('partition=="OOT"').iloc[0];ix=np.flatnonzero(dates.between(pd.Timestamp(s['first']),pd.Timestamp(s['last'])) & d.eligible)
 selected=pd.read_csv(OUT/'selected_summary.csv');rows=[];forecasts=[]
 for r in selected.itertuples():
  if not r.all_three_rules_pass:continue
  bundle=pickle.load((OUT/f'h{r.horizon}_{r.task}_compact.pkl').open('rb'))
  cols=bundle['feature_names'];z=d.loc[ix,cols].replace([np.inf,-np.inf],np.nan).fillna(bundle['medians']).to_numpy(dtype=float)
  z=(z-np.asarray(bundle['means']))/np.asarray(bundle['scales'])
  y=d.loc[ix,f'y_h{r.horizon}'].to_numpy();b=d.loc[ix,f'baseline_h{r.horizon}'].to_numpy();actual=(y>d.ma5_current.iloc[ix].to_numpy()).astype(int);struct=(b>d.ma5_current.iloc[ix].to_numpy()).astype(int)
  if r.task=='regression':
   pred=b+d.close.iloc[ix].to_numpy()*(bundle['model'].predict(z)*bundle['target_scale']+bundle['target_mean'])
   gain=(y-b)**2-(y-pred)**2
   score=float(np.sqrt(np.mean((y-pred)**2)));expected=r.OOT_RMSE
   cls=(pred>d.ma5_current.iloc[ix].to_numpy()).astype(int)
  else:
   prob=bundle['model'].predict_proba(z)[:,1];cls=(prob>.5).astype(int)
   gain=(cls==actual).astype(float)-(struct==actual).astype(float)
   score=float((cls==actual).mean());expected=r.OOT_accuracy
   pred=np.full(len(ix),np.nan)
  assert np.isclose(score,expected,rtol=1e-10)
  low,high=interval(gain)
  rows.append(dict(horizon=r.horizon,task=r.task,rows=len(ix),gain_vs_structural=float(gain.mean()),CI_low=float(low),CI_high=float(high),positive_CI=bool(low>0),score=score,structural_score=r.OOT_structural_RMSE if r.task=='regression' else r.OOT_structural_accuracy))
  forecasts.append(pd.DataFrame(dict(decision_at=d.decision_at.iloc[ix].values,horizon=r.horizon,task=r.task,actual_price=y,structural_price=b,predicted_price=pred,actual_class=actual,predicted_class=cls)))
 pd.DataFrame(rows).to_csv(OUT/'paired_OOT_intervals.csv',index=False)
 pd.concat(forecasts,ignore_index=True).to_csv(OUT/'compact_OOT_predictions.csv.gz',index=False)
 print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__':main()
