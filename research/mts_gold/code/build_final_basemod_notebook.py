from pathlib import Path
import os
import nbformat as n
from nbclient import NotebookClient
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'training_artifacts/_training_baseline/model1_15m_priceMA/_final_basemod'
nb=n.v4.new_notebook(cells=[
 n.v4.new_markdown_cell('# Frozen fold3 LightGBM + isotonic/linear: desktop inference\n\nInstall requirements.txt in this folder using Python3.12. Open this notebook with that environment. This notebook uses only files in this folder; it does not refit any model. Target is next-bar trailing MA5 price. REST_2025 is an in-training retrospective backcast; DEV fits calibrators; OOT1 is their later evaluation; REST_2026 mixes other historical roles—inspect provenance. All previously inspected results are development evidence.'),
 n.v4.new_code_cell("from pathlib import Path\nimport sys,json,pickle\nimport pandas as pd\nfrom IPython.display import display,Image\npaths=[Path.cwd(),Path.cwd()/'research/mts_gold/training_artifacts/_training_baseline/model1_15m_priceMA/_final_basemod']\npackage=next(p for p in paths if (p/'prediction_bundle.pkl').exists())\nsys.path.insert(0,str(package))\nfrom predict_local import load_models,predict,report\nmetadata=json.loads((package/'package_metadata.json').read_text())\ndisplay(metadata['period_definitions'])\ndisplay(metadata['limitations'])"),
 n.v4.new_markdown_cell('## Load models and prepared data\n\nThe 45 feature columns already contain the original causal lags and fold3 EWMA seed. Target scaling, imputers and feature scalers are frozen in the bundle. Avoid recalculating them from the full dataset.'),
 n.v4.new_code_cell("data=pd.read_csv(package/'all_time_X_y_context.csv.gz')\nbundle=load_models(package)\npredictions=predict(data,bundle)\ndisplay(data.groupby(['period','provenance']).size().rename('context_rows'))\ndisplay(pd.concat([data[['decision_at','y_ma5','period','provenance']],predictions],axis=1).head(15))\nprint('All context predictions:',len(predictions))"),
 n.v4.new_markdown_cell('## Reproduce statistical comparison and Excel\n\nThe report scores labelled rows only. Paired MSE-gain intervals use1,000 circular30-row block-bootstrap draws, stratified by provenance. ALL and fitted blocks are descriptive, not independent test scores. The routine regenerates CSVs, plots and the Excel comparison.'),
 n.v4.new_code_cell("performance,comparison=report(package)\ndisplay(performance.query(\"slice_type=='period'\"))\ndisplay(comparison.query(\"slice_type=='period' and first=='prediction_isotonic' and second=='prediction_linear'\"))\ndisplay(Image(filename=str(package/'all_time_actual_prediction.png')))"),
 n.v4.new_markdown_cell('## Data supplied for further local work\n\nbase_training_X_y.csv.gz contains the original matured fold3 base-training rows; calibration_dev_X_y.csv.gz fits the two existing calibrators; validation_oot1_X_y.csv.gz is their later evaluation; post_fold3_backtest_X_y.csv.gz covers later context. all_time_X_y_context.csv.gz is the complete prepared feature/target table. Use package_metadata.json and feature_schema.csv to preserve feature order and transformations. Future raw market data must first pass through the original feature pipeline. Never pass y_ma5, period, provenance, or label timestamps as X. Quantitative trading backtests need additional trading assumptions; this notebook forecasts MA5 prices only.')
])
nb.metadata.kernelspec={'display_name':'Python3','language':'python','name':'python3'}
path=OUT/'Final_BaseModel_Local.ipynb'
try:NotebookClient(nb,timeout=1800,kernel_name=os.environ.get('MTS_NOTEBOOK_KERNEL','python3'),resources={'metadata':{'path':str(OUT)}}).execute()
finally:n.write(nb,path)
print(path)
