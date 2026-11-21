"""Export frozen fold3 LightGBM + existing calibrators as a self-contained desktop package."""
from pathlib import Path
import json,pickle,hashlib,shutil,importlib.metadata,platform
import numpy as np,pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression
from lightgbm import Booster
from model1_15m_priceMA import OUT as BASE,prepare,labels,matured
OUT=BASE/'_final_basemod'

def build():
 OUT.mkdir(parents=True,exist_ok=True)
 b=json.loads((BASE/'fold3_LightGBMRegressor.json').read_text())
 f,_,_,source=prepare();splits=list(TimeSeriesSplit(n_splits=4,gap=30).split(f));tr,te=splits[2]
 tr=matured(f,tr,f.loc[tr[-1],'decision_at']+pd.Timedelta(minutes=15))
 f,seed=labels(f,tr)
 np.testing.assert_allclose(seed,b['ewma_seed']);np.testing.assert_allclose(f.attrs['target_mean'],b['target_mean']);np.testing.assert_allclose(f.attrs['target_scale'],b['target_scale'])
 calib=json.loads((BASE/'_try_calibration/calibrator_parameters.json').read_text());iso=next(x for x in calib if x['fold']==3 and x['model']=='isotonic');lin=next(x for x in calib if x['fold']==3 and x['model']=='linear')
 isotonic=IsotonicRegression(increasing=True,out_of_bounds='clip').fit(iso['X_thresholds'],iso['Y_thresholds'])
 linear=LinearRegression();linear.coef_=np.array([lin['coefficients_raw_X'][1]]);linear.intercept_=lin['coefficients_raw_X'][0];linear.n_features_in_=1
 booster=Booster(model_file=str(BASE/'fold3_LightGBMRegressor.txt'))
 bundle=dict(base_model=booster,isotonic=isotonic,linear=linear,preprocessing=b,fold=3,target='next-bar trailing MA5 price, THB quote units')
 for name,model in [('lightgbm_fold3.pkl',booster),('isotonic_fold3.pkl',isotonic),('linear_fold3.pkl',linear),('prediction_bundle.pkl',bundle)]:
  with (OUT/name).open('wb') as file:pickle.dump(model,file,protocol=4)
 shutil.copy2(BASE/'fold3_LightGBMRegressor.txt',OUT/'lightgbm_fold3.txt')
 (OUT/'preprocessing.json').write_text(json.dumps(b,indent=2)+'\n')
 (OUT/'calibration_parameters.json').write_text(json.dumps([iso,lin],indent=2)+'\n')
 plan=pd.read_csv(BASE/'_try_calibration/Chronological_split.csv').query('fold==3').iloc[0]
 start,end,oot_start,oot_end=[pd.Timestamp(plan[c]) for c in ['fit_start_Bangkok','fit_end_Bangkok','evaluation_start_Bangkok','evaluation_end_Bangkok']]
 localyear=f.decision_at.dt.tz_convert('Asia/Bangkok').dt.year
 f['period']='REST_2026';f.loc[localyear.eq(2025),'period']='REST_2025'
 f.loc[f.decision_at.between(start,end)&f.y_ma5.notna(),'period']='DEV'
 f.loc[f.decision_at.between(oot_start,oot_end)&f.y_ma5.notna(),'period']='OOT1'
 f['provenance']='other_context';f.loc[tr,'provenance']='base_training'
 f.loc[f.decision_at.gt(f.loc[tr].decision_at.max())&f.decision_at.lt(start),'provenance']='base_embargo_or_boundary'
 f.loc[f.period.eq('DEV'),'provenance']='calibrator_training'
 f.loc[f.decision_at.gt(end)&f.decision_at.lt(oot_start),'provenance']='calibration_embargo_or_context'
 f.loc[f.period.eq('OOT1'),'provenance']='calibrator_later_evaluation'
 f.loc[f.decision_at.gt(oot_end),'provenance']='post_fold3_backtest'
 f['label_valid']=f.y_ma5.notna()
 f['is_base_training_member']=f.index.isin(tr)
 f['is_calibrator_training_member']=f.period.eq('DEV')
 cols=['decision_at','label_at','symbol','close','ma5_current','structural_persistence','y_ma5','label_valid','period','provenance','is_base_training_member','is_calibrator_training_member']+b['features']
 all_data=f[cols].copy();all_data.to_csv(OUT/'all_time_X_y_context.csv.gz',index=False)
 all_data.loc[tr].to_csv(OUT/'base_training_X_y.csv.gz',index=False)
 for period,name in [('DEV','calibration_dev_X_y.csv.gz'),('OOT1','validation_oot1_X_y.csv.gz')]:all_data.loc[all_data.period.eq(period)].to_csv(OUT/name,index=False)
 all_data.loc[all_data.provenance.eq('post_fold3_backtest')].to_csv(OUT/'post_fold3_backtest_X_y.csv.gz',index=False)
 feature_info=pd.DataFrame({'feature':b['features'],'imputation_median':b['medians'],'scaler_mean':b['means'],'scaler_std':b['scales']});feature_info.to_csv(OUT/'feature_schema.csv',index=False)
 original_pred=pd.read_csv(BASE/'predictions.csv.gz').query("fold==3 and model=='LightGBMRegressor'")
 all_data.set_index('decision_at').loc[pd.to_datetime(original_pred.decision_at,utc=True)].reset_index().to_csv(OUT/'base_validation_X_y.csv.gz',index=False)
 original_cal=pd.read_csv(BASE/'_try_calibration/Predictions.csv.gz').query('fold==3')
 versions={name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','scikit-learn','lightgbm','matplotlib','openpyxl','xlsxwriter','nbformat','nbclient','ipykernel']}
 (OUT/'requirements.txt').write_text('\n'.join(f'{name}=={version}' for name,version in versions.items())+'\n')
 metadata={'python_version':platform.python_version(),'source_file':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rows':len(all_data),'valid_labels':int(all_data.label_valid.sum()),'snapshot_start_Bangkok':str(f.decision_at.min().tz_convert('Asia/Bangkok')),'snapshot_end_Bangkok':str(f.decision_at.max().tz_convert('Asia/Bangkok')),
  'base_fold':3,'base_training_rows':len(tr),'versions':versions,'calibration_split':{str(k):str(v) for k,v in plan.items()},
  'period_definitions':{'ALL':'All scoreable saved rows; descriptive mix of fitted and later periods','REST_2025':'Bangkok calendar2025; base-training backcasts, calibration applied retrospectively','DEV':'Exact fold3 calibration-fit rows, 2026-02-12 to2026-04-21 Bangkok','OOT1':'Exact fold3 later calibration-evaluation rows, 2026-04-22 to2026-06-26 Bangkok','REST_2026':'All other2026 context; mixed base-training, embargo and post-fold3 backtest. Use provenance for clean slices'},
  'limitations':['No new market data fetched; latest saved snapshot only.','The original fold3 model used2025 plus early2026 for base training;2025 is not an untouched test.','Calibrators were fitted in2026 and are back-applied to earlier rows. Historical backcasts use parameters estimated later.','OOT1 and later data were already inspected in earlier project analyses; these are development/backtest results, not fresh final tests.','Predictions are next-bar trailing MA5 prices, not spot-return or trading PnL forecasts. Four of five target closes are already known.','Prepared feature CSVs include fold3-seeded historical Z lag; do not refit preprocessing or shift columns again.','Models remain frozen. The notebook loads them and reproduces predictions; retraining a different sample is a new experiment.']}
 (OUT/'package_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
 # Copy held-out reference rows only for build-time reproduction checks, not as package inputs.
 original_pred.to_csv('/tmp/final_base_reference.csv',index=False);original_cal.to_csv('/tmp/final_cal_reference.csv',index=False)
 print('Prepared frozen package',len(all_data),'rows',flush=True)

if __name__=='__main__':build()
