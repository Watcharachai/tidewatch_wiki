from pathlib import Path
import nbformat as n
from nbclient import NotebookClient
repo=Path(__file__).resolve().parents[3];out=repo/'research/mts_gold/training_artifacts/_training_baseline/model1_15m_priceMA';out.mkdir(parents=True,exist_ok=True)
nb=n.v4.new_notebook(cells=[n.v4.new_markdown_cell('# GLD965 15m: next-bar five-period price MA\n\nForecast the next bar’s trailing five-period average price. Four of five prices are known at decision time. Compare against structural price persistence, not just conventional price-level R2. Z_return_lag5 remains a historical candidate predictor. Four outer time-series folds, thirty-bar embargo, separate inner selection and tuning blocks. Source code records all thresholds and search grids.'),n.v4.new_code_cell("import sys\nfrom pathlib import Path\nrepo=Path('/workspace/tidewatch_wiki') if Path('/workspace/tidewatch_wiki').exists() else next(p for p in [Path.cwd(),*Path.cwd().parents] if (p/'research/mts_gold').exists())\nsys.path.insert(0,str(repo/'research/mts_gold/code'))\nfrom model1_15m_priceMA import run,CONFIG,GRIDS\nfrom IPython.display import display,Image\ndisplay(CONFIG)\ndisplay(GRIDS)\nresults=run()"),n.v4.new_code_cell("display(results['waterfall'])\ndisplay(results['schedule'])\ndisplay(results['selected_features'])\ndisplay(results['summary'])\ndisplay(results['pairwise_comparison'])"),n.v4.new_code_cell("display(results['fold_metrics'])\ndisplay(results['tuning'])\ndisplay(results['permutation'])\ndisplay(Image(filename=str(repo/'research/mts_gold/training_artifacts/_training_baseline/model1_15m_priceMA/predicted_actual.png')))\ndisplay(results['predictions'].head(20))")])
nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
p=out/'GLD965_15m_priceMA_Training.ipynb'
try:NotebookClient(nb,timeout=3600,kernel_name=__import__('os').environ.get('MTS_NOTEBOOK_KERNEL','python3'),resources={'metadata':{'path':str(repo)}}).execute()
finally:n.write(nb,p)
print(p)
