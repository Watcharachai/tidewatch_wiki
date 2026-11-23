"""Verify assembled inference metrics, copied artifacts, monthly counts and reports."""
from pathlib import Path
import hashlib,json,zipfile
import numpy as np,pandas as pd,nbformat,openpyxl
from docx import Document
P=Path(__file__).resolve().parent

def run():
 expected={'TRAIN':24194,'TEST':10372,'OOT':3629}
 for part,n in expected.items():assert len(pd.read_csv(P/f'data/{part}_X_y.csv.gz'))==n
 rp=pd.read_csv(P/'evidence/Regression_performance.csv');cp=pd.read_csv(P/'evidence/Classification_performance.csv')
 source=pd.read_csv(P/'evidence/calibration_metrics.csv')
 for row in source.itertuples():
  report=rp if row.task=='regression' else cp
  z=report[(report.horizon==row.horizon)&(report.partition==row.partition)&(report.method==row.method)].iloc[0]
  assert z.n==row.n
  for name in (['RMSE','MAE'] if row.task=='regression' else ['Brier','ECE','accuracy','log_loss']):
   assert np.isclose(z[name],getattr(row,name),rtol=1e-8,atol=1e-9),(row.horizon,row.task,row.partition,row.method,name,z[name],getattr(row,name))
 mr=pd.read_csv(P/'evidence/Monthly_regression.csv');mc=pd.read_csv(P/'evidence/Monthly_classification.csv')
 for (part,h,method),g in mc.groupby(['partition','horizon','method']):
  assert g.n.sum()==expected[part]
  if method!='structural':
   z=cp[(cp.partition==part)&(cp.horizon==h)&(cp.method==method)].iloc[0]
   for name in ['TN','FP','FN','TP']:assert g[name].sum()==z[name]
   assert np.isclose((g.accuracy*g.n).sum()/g.n.sum(),z.accuracy)
 for (part,h,method),g in mr.groupby(['partition','horizon','method']):
  z=rp[(rp.partition==part)&(rp.horizon==h)&(rp.method==method)].iloc[0]
  assert g.n.sum()==expected[part]
  assert np.isclose(np.sqrt((g.RMSE**2*g.n).sum()/g.n.sum()),z.RMSE)
 for h in range(1,6):
  df=pd.read_csv(P/f'data/predictions_h{h}.csv.gz');assert len(df)==sum(expected.values())
  for method in ['raw','isotonic','linear','quadratic','cubic']:
   assert df['prob_'+method].between(0,1).all()
   assert np.array_equal(df['class_'+method],(df['prob_'+method]>.5).astype(int))
 metadata=json.loads((P/'package_metadata.json').read_text())
 assert hashlib.sha256((P/'data/Dataset_X_y.csv.gz').read_bytes()).hexdigest()==metadata['source_dataset_sha256']
 for path in (P/'models').glob('*.pkl'):
  assert hashlib.sha256(path.read_bytes()).hexdigest()==metadata['source_model_sha256'][path.name]
 assert len(list((P/'models').glob('*.pkl')))==50
 assert len(list((P/'plots').glob('*.png')))==25
 assert len(list((P/'notebooks').glob('*.ipynb')))==4
 nb=nbformat.read(P/'Final_Package_Review.ipynb',as_version=4)
 assert all(c.execution_count is not None and not any(o.output_type=='error' for o in c.outputs) for c in nb.cells if c.cell_type=='code')
 with zipfile.ZipFile(P/'Final_Model_Summary.xlsx') as z:assert z.testzip() is None
 book=openpyxl.load_workbook(P/'Final_Model_Summary.xlsx',read_only=True,data_only=True)
 assert len(book.sheetnames)==47
 for h in range(1,6):assert book[f'Predictions_h{h}'].max_row==sum(expected.values())+1
 book.close()
 doc=Document(P/'Model_Documentation.docx');assert len(doc.inline_shapes)==25
 result=dict(partition_rows=expected,base_models=10,calibrators=40,archived_notebooks=4,notebook_executed=True,plots=25,excel_sheets=47,docx_figures=25,source_model_hashes_identical=True,source_calibration_metrics_reproduced=True,monthly_confusion_counts_and_weighted_metrics_reconciled=True,probabilities_and_classes_consistent=True,model_refits=False)
 (P/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
 hashes={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(P.rglob('*')) if f.is_file() and f.name!='checksums.json' and '__pycache__' not in f.parts}
 (P/'checksums.json').write_text(json.dumps(hashes,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':run()
