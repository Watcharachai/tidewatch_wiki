"""Chronological calibration of saved LightGBM MA5 predictions; no base-model retraining."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.isotonic import IsotonicRegression
from statsmodels.stats.stattools import durbin_watson,jarque_bera
from model1_15m_priceMA import OUT as BASE,price_score,loss_ci
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=BASE/'_try_calibration'
MODELS={'linear':1,'quadratic':2,'cubic':3}

def polynomial_transform(center,scale,degree):
 # Matrix mapping coefficients of z=(X-center)/scale into coefficients of raw X.
 z=np.polynomial.Polynomial([-center/scale,1/scale]);transform=np.zeros((degree+1,degree+1))
 for k in range(degree+1):
  coef=(z**k).coef;transform[:len(coef),k]=coef
 return transform

def fit_polynomial(x,y,degree):
 center=float(np.mean(x));scale=float(np.std(x,ddof=0))
 if scale<=1e-8 or len(np.unique(x))<degree+1:raise ValueError('Insufficient variation to identify polynomial calibration')
 design=np.vander((np.asarray(x)-center)/scale,N=degree+1,increasing=True)
 fit=sm.OLS(np.asarray(y),design).fit()
 hac=fit.get_robustcov_results(cov_type='HAC',maxlags=30,use_correction=True)
 return fit,hac,center,scale,design

def polynomial_predict(fit,center,scale,degree,x):
 return np.vander((np.asarray(x)-center)/scale,N=degree+1,increasing=True)@fit.params

def coefficient_rows(fold,name,fit,hac,center,scale,degree):
 transform=polynomial_transform(center,scale,degree);raw=transform@fit.params;raw_cov=transform@hac.cov_params()@transform.T
 rows=[]
 for basis,params,se in [('standardized_X',hac.params,hac.bse),('raw_X',raw,np.sqrt(np.maximum(np.diag(raw_cov),0)))]:
  for i,(coef,error) in enumerate(zip(params,se)):
   t=coef/error if error>0 else np.nan
   dist=stats.t(df=fit.df_resid) if hac.use_t else stats.norm()
   cutoff=dist.ppf(.975)
   rows.append(dict(fold=fold,model=name,basis=basis,term=f'b{i}',coefficient=coef,HAC_standard_error=error,
    HAC_t_or_z=t,HAC_p_value=2*dist.sf(abs(t)),HAC_CI_low=coef-cutoff*error,HAC_CI_high=coef+cutoff*error,
    covariance='HAC 30 observed rows; conditional on fitted X mean/std',X_center=center,X_scale=scale,
    note='Use standardized coefficients for stable numerical prediction; raw X powers may have large cancelling coefficients.'))
 return rows

def run():
 OUT.mkdir(parents=True,exist_ok=True)
 source=BASE/'predictions.csv.gz';digest=hashlib.sha256(source.read_bytes()).hexdigest()
 base=pd.read_csv(source).query("model=='LightGBMRegressor'").sort_values(['fold','decision_at'])
 base['decision_at']=pd.to_datetime(base.decision_at,utc=True);base['label_at']=pd.to_datetime(base.label_at,utc=True)
 rows=[];coefficients=[];regressions=[];knots=[];plans=[];grid_rows=[];bundles=[]
 for fold,g in base.groupby('fold'):
  g=g.reset_index(drop=True);mid=len(g)//2
  fit=g.iloc[:mid].loc[lambda d:d.label_at.lt(g.decision_at.iloc[mid])].copy();evaluation=g.iloc[mid+30:].copy()
  assert fit.label_at.max()<evaluation.decision_at.min()
  assert len(g.iloc[mid:mid+30])==30
  x=fit.y_hat.to_numpy();y=fit.y_ma5.to_numpy();iso=IsotonicRegression(increasing=True,out_of_bounds='clip').fit(x,y)
  plans.append(dict(fold=fold,fit_rows=len(fit),evaluation_rows=len(evaluation),embargo_observations=30,
   fit_start_Bangkok=str(fit.decision_at.min().tz_convert('Asia/Bangkok')),fit_end_Bangkok=str(fit.decision_at.max().tz_convert('Asia/Bangkok')),
   evaluation_start_Bangkok=str(evaluation.decision_at.min().tz_convert('Asia/Bangkok')),evaluation_end_Bangkok=str(evaluation.decision_at.max().tz_convert('Asia/Bangkok')),
   fit_X_min=x.min(),fit_X_max=x.max(),evaluation_X_min=evaluation.y_hat.min(),evaluation_X_max=evaluation.y_hat.max(),
   evaluation_X_outside_fit_fraction=float((evaluation.y_hat.lt(x.min())|evaluation.y_hat.gt(x.max())).mean()),
   highlight_reason='Highest original outer validation R2 among LightGBM folds (post-hoc descriptive highlight)' if fold==3 else 'Comparison fold'))
  for a,b in zip(iso.X_thresholds_,iso.y_thresholds_):knots.append(dict(fold=fold,X_threshold=a,Y_threshold=b))
  bundles.append(dict(fold=int(fold),model='isotonic',X_thresholds=iso.X_thresholds_.tolist(),Y_thresholds=iso.y_thresholds_.tolist(),out_of_bounds='clip',increasing=True))
  grid=np.linspace(g.y_hat.min(),g.y_hat.max(),300);curves={'isotonic':iso.predict(grid),'uncalibrated':grid}
  predictors={'isotonic':iso.predict}
  regressions.append(dict(fold=fold,model='isotonic',fit_rows=len(fit),parameters=len(iso.X_thresholds_),fit_RMSE=float(np.sqrt(np.mean((y-iso.predict(x))**2))),
    R2_fit=1-np.sum((y-iso.predict(x))**2)/np.sum((y-y.mean())**2),inference_note='Stepwise monotone nonparametric fit: OLS coefficient standard errors, F-tests, AIC/BIC are not reported.'))
  for name,degree in MODELS.items():
   result,hac,center,scale,design=fit_polynomial(x,y,degree)
   predictors[name]=lambda values,res=result,c=center,s=scale,d=degree:polynomial_predict(res,c,s,d,values)
   curves[name]=predictors[name](grid);coefficients.extend(coefficient_rows(fold,name,result,hac,center,scale,degree))
   jb,jbp,skew,kurt=jarque_bera(result.resid)
   regressions.append(dict(fold=fold,model=name,fit_rows=len(fit),parameters=degree+1,R2_fit=result.rsquared,adjusted_R2=result.rsquared_adj,
    fit_RMSE=np.sqrt(np.mean(result.resid**2)),AIC=result.aic,BIC=result.bic,F_OLS=result.fvalue,F_OLS_p=result.f_pvalue,
    F_HAC=float(hac.fvalue),F_HAC_p=float(hac.f_pvalue),condition_number_scaled=np.linalg.cond(design),design_rank=np.linalg.matrix_rank(design),
    residual_mean=np.mean(result.resid),Durbin_Watson=durbin_watson(result.resid),Jarque_Bera=jb,JB_p=jbp,residual_skewness=skew,residual_kurtosis_Pearson=kurt,
    inference_note='Fit-block descriptive inference; serial dependence, price trends, previous data inspection and multiple comparisons limit interpretation. HAC lag30 is an assumption, not proof of stationarity.'))
   bundles.append(dict(fold=int(fold),model=name,degree=degree,X_center=center,X_scale=scale,coefficients_standardized_X=result.params.tolist(),
     coefficients_raw_X=(polynomial_transform(center,scale,degree)@result.params).tolist(),HAC_covariance_standardized_X=hac.cov_params().tolist()))
   summary_text=result.summary().as_text()+'\n\nHAC covariance summary\n'+hac.summary().as_text()
   (OUT/f'fold{fold}_{name}_OLS_summary.txt').write_text('\n'.join(line.rstrip() for line in summary_text.splitlines())+'\n')
  for name,values in curves.items():grid_rows.extend(dict(fold=fold,model=name,X_predicted=a,fitted_Y=b) for a,b in zip(grid,values))
  for partition,values in [('calibration_fit',fit),('later_evaluation',evaluation)]:
   for model in ['uncalibrated','structural_persistence','MA_persistence',*predictors]:
    pred=values.y_hat.to_numpy() if model=='uncalibrated' else values.structural_persistence.to_numpy() if model=='structural_persistence' else values.ma5_current.to_numpy() if model=='MA_persistence' else predictors[model](values.y_hat.to_numpy())
    q=values[['fold','decision_at','label_at','y_ma5','y_hat','structural_persistence','ma5_current']].copy().rename(columns={'y_hat':'base_prediction'})
    q['calibrated_prediction']=pred;q['calibrator']=model;q['partition']=partition;rows.append(q)
  print('Calibrated fold',fold,flush=True)
 predictions=pd.concat(rows,ignore_index=True);performance=[]
 for (fold,partition,model),g in predictions.groupby(['fold','partition','calibrator']):
  row=dict(fold=fold,partition=partition,calibrator=model,**price_score(g.y_ma5,g.calibrated_prediction,g.structural_persistence),
    mean_error=float((g.calibrated_prediction-g.y_ma5).mean()),median_absolute_error=float(np.median(np.abs(g.calibrated_prediction-g.y_ma5))))
  if partition=='later_evaluation':
   q=g.rename(columns={'calibrated_prediction':'y_hat'})
   raw_ci=loss_ci(q,g.base_prediction);struct_ci=loss_ci(q,g.structural_persistence)
   row.update(MSE_gain_vs_uncalibrated=float(np.mean((g.y_ma5-g.base_prediction)**2)-row['MSE']),
    gain_vs_raw_CI_low=raw_ci['mse_improvement_ci_low'],gain_vs_raw_CI_high=raw_ci['mse_improvement_ci_high'],
    gain_vs_structural_CI_low=struct_ci['mse_improvement_ci_low'],gain_vs_structural_CI_high=struct_ci['mse_improvement_ci_high'])
  performance.append(row)
 pooled=[]
 for model,g in predictions.query("partition=='later_evaluation'").groupby('calibrator'):
  q=g.rename(columns={'calibrated_prediction':'y_hat'});a=loss_ci(q,g.base_prediction);b=loss_ci(q,g.structural_persistence)
  pooled.append(dict(calibrator=model,**price_score(g.y_ma5,g.calibrated_prediction,g.structural_persistence),
   gain_vs_raw_CI_low=a['mse_improvement_ci_low'],gain_vs_raw_CI_high=a['mse_improvement_ci_high'],
   gain_vs_structural_CI_low=b['mse_improvement_ci_low'],gain_vs_structural_CI_high=b['mse_improvement_ci_high']))
 tables={'Performance_by_fold':pd.DataFrame(performance),'Pooled_later_evaluation':pd.DataFrame(pooled),
  'Regression_statistics':pd.DataFrame(regressions),'Regression_coefficients':pd.DataFrame(coefficients),
  'Isotonic_knots':pd.DataFrame(knots),'Chronological_split':pd.DataFrame(plans),'Fitted_curve_grid':pd.DataFrame(grid_rows),'Predictions':predictions}
 tables['Fold3_highlight']=tables['Performance_by_fold'].query("fold==3 and partition=='later_evaluation'").copy()
 for name,d in tables.items():d.to_csv(OUT/(name+'.csv.gz' if name=='Predictions' else name+'.csv'),index=False)
 (OUT/'calibrator_parameters.json').write_text(json.dumps(bundles,indent=2,allow_nan=False)+'\n')
 plots(tables);export_excel(tables)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
 import importlib.metadata,shutil
 shutil.copy2(__file__,OUT/'calibration_source.py')
 manifest={'source_predictions_sha256':digest,'source':str(source.relative_to(BASE)),
  'protocol':'Per original fold: first 50% of available prediction rows fits calibration, then 30 prediction-row embargo, later remainder evaluates; fit labels must mature before embargo. Existing LightGBM models unchanged.',
  'highlight_fold':3,'highlight_reason':'Highest original validation R2; chosen for descriptive emphasis, not independent model selection',
  'equations':['isotonic increasing, clipped outside fit range','b0+b1*X','b0+b1*X+b2*X^2','b0+b1*X+b2*X^2+b3*X^3'],
  'inference':'OLS and HAC30 fit-block statistics; paired circular30-row bootstrap1000 for evaluation MSE improvement. No multiplicity adjustment. Development evidence after prior inspection, not a fresh final test.',
  'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','statsmodels','scipy']},
  'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'}}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(tables['Pooled_later_evaluation'].to_string(index=False),flush=True)
 return tables

def plots(tables):
 p=tables['Predictions'];grids=tables['Fitted_curve_grid'];colors={'uncalibrated':'black','linear':'#2468ad','quadratic':'#e58b22','cubic':'#bc4640','isotonic':'#379669'}
 fig,axes=plt.subplots(2,2,figsize=(13,10),constrained_layout=True)
 for (fold,g),ax in zip(p.query("calibrator=='uncalibrated'").groupby('fold'),axes.flat):
  fit=g.query("partition=='calibration_fit'");ev=g.query("partition=='later_evaluation'")
  ax.scatter(fit.base_prediction,fit.y_ma5,s=3,alpha=.15,color='gray',label='Calibration-fit actual');ax.scatter(ev.base_prediction,ev.y_ma5,s=3,alpha=.2,color='#5676b8',label='Later actual')
  for model,curve in grids.query('fold==@fold').groupby('model'):ax.plot(curve.X_predicted,curve.fitted_Y,color=colors[model],label=model,linewidth=1.5)
  ax.set(title=f'Fold {fold}'+(' — highlighted' if fold==3 else ''),xlabel='X: saved LightGBM prediction (THB quote)',ylabel='Y: actual next MA5 (THB quote)');ax.legend(fontsize=6)
 fig.savefig(OUT/'calibration_fitted_lines.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(2,1,figsize=(12,7),constrained_layout=True)
 q=p.query("fold==3 and partition=='later_evaluation'")
 for model in ['uncalibrated',*MODELS,'isotonic','structural_persistence']:
  g=q.query('calibrator==@model').tail(250);axes[0].plot(g.decision_at,g.calibrated_prediction,label=model,alpha=.8)
  axes[1].plot(g.decision_at,g.calibrated_prediction-g.y_ma5,label=model,alpha=.8)
 a=q.query("calibrator=='uncalibrated'").tail(250);axes[0].plot(a.decision_at,a.y_ma5,color='black',linewidth=2,label='Actual');axes[0].legend(ncol=4,fontsize=7);axes[0].set_title('Fold 3: later evaluation, last 250 observations');axes[0].set_ylabel('Next MA5 (THB quote)');axes[1].axhline(0,color='black');axes[1].set_ylabel('Predicted minus actual');axes[1].set_xlabel('Decision time (UTC)')
 fig.savefig(OUT/'fold3_actual_and_gap.png',dpi=150);plt.close(fig)

def export_excel(tables):
 notes=[('Objective','X=saved tuned LightGBM MA5-price prediction; Y=actual next MA5. Cubic means X^3, interpreting the requested third-order expression.'),
 ('Most fitted','Fold3 had highest original validation R2 (0.6797), while fold1 had lowest absolute RMSE. Highlight fold3 descriptively; analyze all four to avoid hiding regime differences.'),
 ('Temporal protocol','First 50% of each original validation sequence fits calibrators. Fit labels mature before boundary. Skip next30 prediction observations, then evaluate remaining later observations. No calibrator sees later labels during fitting.'),
 ('Development status','Original validation periods have already been inspected. These later blocks are held out from calibrator fitting, but are development evidence, not a new untouched final test.'),
 ('Baselines','Compare with uncalibrated LightGBM and structural persistence. MA5 contains four known prices; high price-level R2 does not prove next-price skill.'),
 ('Isotonic','Monotone increasing fit, out_of_bounds=clip. It cannot extrapolate beyond fitted endpoint Y values. Knots exported. OLS standard errors/F tests/AIC do not apply.'),
 ('Polynomial stability','OLS fits powers of z=(X-fit_mean)/fit_std. Exact raw-X coefficient transform also exported. Use standardized coefficients for prediction: large raw powers can cancel numerically.'),
 ('Regression inference','Classical OLS F/AIC/BIC and HAC30 coefficient SE, p-values, CIs and robust joint F are fit-block descriptive statistics. Price trends, serial dependence, specification selection and repeated testing limit inferential validity.'),
 ('Regression diagnostics','Adjusted R2, fit RMSE, scaled-design condition number, rank, Durbin-Watson, Jarque-Bera, skewness and Pearson kurtosis are reported. HAC lag30 counts observed rows, not uniform wall-clock minutes.'),
 ('Evaluation uncertainty','1000 paired circular block-bootstrap samples, block30 observations, stratified by original fold for pooled results. CIs measure MSE improvement, positive favors calibration. No multiplicity correction.'),
 ('Model choice','Use later-evaluation performance to compare research candidates. A large fit R2, significant slope, or gain over a weak LightGBM alone does not establish improvement over structural persistence.'),
 ('Plots','Gray points are calibration-fit observations; blue points are later evaluation actuals. Lines are fitted calibrators, with identity line for uncalibrated model. Full-range extrapolation is displayed. Time-series plot uses UTC.'),
 ('Units','All actuals, fitted values, residuals, MAE and RMSE use original THB quote units. MSE and confidence bounds use squared THB quote units.')]
 with pd.ExcelWriter(OUT/'LightGBM_Calibration_Analysis.xlsx',engine='xlsxwriter',engine_kwargs={'options':{'strings_to_formulas':False,'strings_to_urls':False}}) as w:
  pd.DataFrame(notes,columns=['Topic','Explanation']).to_excel(w,sheet_name='Read_me',index=False)
  for name,d in tables.items():
   d=d.copy()
   for c in d:
    if isinstance(d[c].dtype,pd.DatetimeTZDtype):d[c]=d[c].astype(str)
   d.to_excel(w,sheet_name=name[:31],index=False,inf_rep='inf');sheet=w.sheets[name[:31]];sheet.freeze_panes(1,0);sheet.autofilter(0,0,len(d),len(d.columns)-1);sheet.set_column(0,len(d.columns)-1,23)
  w.sheets['Read_me'].set_column(0,0,26);w.sheets['Read_me'].set_column(1,1,115,w.book.add_format({'text_wrap':True}))
  for i in range(1,len(notes)+1):w.sheets['Read_me'].set_row(i,50)
  chart=w.book.add_worksheet('Plots');chart.insert_image('A1',str(OUT/'calibration_fitted_lines.png'),{'x_scale':.7,'y_scale':.7});chart.insert_image('A57',str(OUT/'fold3_actual_and_gap.png'),{'x_scale':.7,'y_scale':.7})

if __name__=='__main__':run()
