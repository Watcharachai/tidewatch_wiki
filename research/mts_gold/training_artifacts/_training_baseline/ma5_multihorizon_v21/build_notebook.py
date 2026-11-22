"""Execute a compact audit notebook from saved v2.1 outputs; no retraining."""
from pathlib import Path
import os,nbformat
from nbclient import NotebookClient
P=Path(__file__).resolve().parent
nb=nbformat.v4.new_notebook()
nb.cells=[
 nbformat.v4.new_markdown_cell('# GLD965 MA5 multi-horizon v2.1\n\nOne chronological 70/30 train/test split before the last two Bangkok calendar months, followed by OOT. Five direct horizons (15–75 minutes), residual regression and MA5 direction classification. Run `experiment.py` for model retraining.'),
 nbformat.v4.new_code_cell("from pathlib import Path\nimport pandas as pd\nfrom IPython.display import display, Image\nP=Path.cwd()\ndisplay(pd.read_csv(P/'Methodology.csv'))\ndisplay(pd.read_csv(P/'Schedule.csv'))"),
 nbformat.v4.new_code_cell("q=pd.read_csv(P/'Feature_quality.csv');g=pd.read_csv(P/'Feature_gain.csv');display(q.groupby('selected').size().rename('features'));display(g.groupby(['horizon','task']).over_5pct.sum().unstack())"),
 nbformat.v4.new_code_cell("m=pd.read_csv(P/'Metrics.csv');display(m[['partition','horizon','task','model','RMSE','MAE','accuracy','balanced_accuracy','MCC','features_ge_5pct','gain_gate_ge3']])"),
 nbformat.v4.new_markdown_cell('## Confusion matrices\nActual class: 1 if future MA5 exceeds current observed MA5; ties and decreases are 0. TN and TP are correct nonpositive and positive calls. Regression predictions are also converted into directional calls for comparison.'),
 nbformat.v4.new_code_cell("display(m[['partition','horizon','task','model','TN','FP','FN','TP','accuracy','balanced_accuracy','precision_positive','recall_positive']])"),
 nbformat.v4.new_code_cell("display(g.sort_values('gain_share',ascending=False).groupby(['horizon','task']).head(8).sort_values(['horizon','task','gain_share'],ascending=[True,True,False]))"),
 nbformat.v4.new_code_cell("display(Image(filename=str(P/'Price_actual_vs_prediction.png')))"),
 nbformat.v4.new_markdown_cell('## Interpretation\nThe 3-feature gain check is a diagnostic. It does not establish predictive improvement. The final two months were already inspected in earlier research, so OOT is chronological but not pristine. Compare price RMSE and directional accuracy with structural persistence, and confirm any improvement on future unseen data.')]
nb.metadata['kernelspec']={'display_name':os.environ.get('MTS_NOTEBOOK_KERNEL','python3'),'language':'python','name':os.environ.get('MTS_NOTEBOOK_KERNEL','python3')}
NotebookClient(nb,timeout=300,kernel_name=nb.metadata['kernelspec']['name'],resources={'metadata':{'path':str(P)}}).execute()
nbformat.write(nb,P/'MA5_V21_Training_Results.ipynb')
