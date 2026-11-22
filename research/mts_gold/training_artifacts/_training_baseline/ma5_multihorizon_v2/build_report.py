from pathlib import Path
import pandas as pd,numpy as np,json,nbformat,os
from nbclient import NotebookClient
P=Path(__file__).resolve().parent
KERNEL=os.environ.get('MTS_NOTEBOOK_KERNEL','python3')
m=pd.read_csv(P/'Metrics.csv');p=pd.read_csv(P/'predictions.csv.gz');d=pd.read_csv(P/'dataset_X_y.csv.gz');q=pd.read_csv(P/'Feature_gain.csv')
assert len(m)==140 and len(p)>0
for h in range(1,6):
 c=d.close
 expected=pd.concat([c.shift(-k) for k in range(h-4,h+1)],axis=1).mean(axis=1)
 good=d[f'y_h{h}'].notna()
 np.testing.assert_allclose(d.loc[good,f'y_h{h}'],expected[good],rtol=1e-12)
 b=(pd.concat([c.shift(k) for k in range(5-h)],axis=1).sum(axis=1)+h*c)/5 if h<5 else c
 np.testing.assert_allclose(d.loc[good,f'baseline_h{h}'],b[good])
 np.testing.assert_allclose(d.loc[good,f'baseline_h{h}']+c[good]*d.loc[good,f'u_h{h}'],expected[good])
assert np.allclose(q.groupby(['fold','horizon','task']).gain_share.sum(),1)
assert not q.feature.str.contains('close').any()
summary=m.groupby(['task','horizon','model']).agg(mean_fold_accuracy=('accuracy','mean'),mean_balanced_accuracy=('balanced_accuracy','mean'),mean_RMSE=('RMSE','mean'),passing_skill_folds=('accepted','sum')).reset_index()
summary.to_csv(P/'Summary.csv',index=False)
# Rebuild workbook using one prediction sheet per horizon to stay within Excel's row limit.
with pd.ExcelWriter(P/'Preliminary_results.xlsx',engine='xlsxwriter',engine_kwargs={'options':{'strings_to_urls':False}}) as w:
 for name in ['Methodology','Snapshot','Summary','Metrics','Feature_gain','Feature_quality','Fold_schedule','Feature_dictionary']:
  t=pd.read_csv(P/f'{name}.csv');t.to_excel(w,sheet_name=name,index=False);w.sheets[name].freeze_panes(1,0);w.sheets[name].set_column(0,len(t.columns)-1,21)
 w.sheets['Methodology'].set_column(1,1,110,w.book.add_format({'text_wrap':True}))
 for i in range(1,12):w.sheets['Methodology'].set_row(i,50)
 for h,g in p.groupby('horizon'):g.to_excel(w,sheet_name=f'Predictions_h{h}',index=False)
 w.book.add_worksheet('Price_charts').insert_image('A1',str(P/'actual_vs_predicted.png'),{'x_scale':.65,'y_scale':.65})
nb=nbformat.v4.new_notebook()
nb.cells=[nbformat.v4.new_markdown_cell('# GLD965: direct MA5 residual regression and direction classification\n\nFive horizons, four chronological development folds. No untouched final holdout. All results use the saved source snapshot. Gain diversity is a separate requirement from skill. See Methodology and experiment.py for the complete reproducible training procedure.'),nbformat.v4.new_code_cell("from pathlib import Path\nimport pandas as pd\nfrom IPython.display import display, Image\nP=Path.cwd()\ndisplay(pd.read_csv(P/'Methodology.csv'))\ndisplay(pd.read_csv(P/'Snapshot.csv'))"),nbformat.v4.new_markdown_cell('## Reproduce training\nThe following callable retrains all fixed models and regenerates outputs. It is deliberately not invoked automatically when inspecting saved results.'),nbformat.v4.new_code_cell('from experiment import run\n# results = run()  # Uncomment to retrain all folds/horizons.'),nbformat.v4.new_code_cell("display(pd.read_csv(P/'Fold_schedule.csv'))\ndisplay(pd.read_csv(P/'Feature_dictionary.csv'))\ndisplay(pd.read_csv(P/'Feature_quality.csv').groupby('fold').agg(candidates=('feature','size'),retained=('selected','sum')))"),nbformat.v4.new_code_cell("metrics=pd.read_csv(P/'Metrics.csv')\ndisplay(pd.read_csv(P/'Summary.csv'))\ndisplay(metrics.query('model == \"LightGBM\"')[['fold','horizon','task','features_ge_5pct','gain_gate','gain_CI_low','gain_CI_high','accepted']])"),nbformat.v4.new_code_cell("importance=pd.read_csv(P/'Feature_gain.csv')\ndisplay(importance.sort_values('gain_share',ascending=False).groupby(['fold','horizon','task']).head(5).sort_values(['fold','horizon','task','gain_share'],ascending=[True,True,True,False]))"),nbformat.v4.new_code_cell("display(Image(filename=str(P/'actual_vs_predicted.png')))"),nbformat.v4.new_markdown_cell('## Interpretation\nA positive lower gain bound indicates improvement versus the structural baseline on that development fold. Regression uses paired MSE gain; classification uses paired accuracy gain. No classification price forecast is fabricated. A model is marked accepted per fold only if its skill criterion and (for LightGBM) gain-diversity gate both pass. Final deployment acceptance requires fresh data and stability across folds. Average-fold summaries are descriptive, not pooled statistical tests. Confidence intervals are exploratory and unadjusted for multiple comparisons.')]
nb.metadata['kernelspec']={'display_name':'mts-model1','language':'python','name':KERNEL}
NotebookClient(nb,timeout=300,kernel_name=KERNEL,resources={'metadata':{'path':str(P)}}).execute()
nbformat.write(nb,P/'MA5_Multihorizon_Training.ipynb')
(P/'verification.json').write_text(json.dumps(dict(metric_rows=len(m),prediction_rows=len(p),horizons=5,folds=4,independent_label_formula_check=True,residual_reconstruction_check=True,feature_gain_normalization=True,notebook_executed=True),indent=2))
print(m.query('model=="LightGBM"').groupby('task').agg(gain_gate_passes=('gain_gate','sum'),accepted=('accepted','sum')).to_string())
print(summary.to_string(index=False))
