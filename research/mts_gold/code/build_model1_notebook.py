#!/usr/bin/env python3
"""Create and optionally execute the reproducible baseline-training notebook."""
import argparse
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT/"training_artifacts"/"_training_baseline"/"Model1_Training_Baseline.ipynb"


def postfit_cells():
    return [nbf.v4.new_markdown_cell("""## Post-fit range checks: explaining unstable expanded-model forecasts

These checks use the already-fitted parameters and saved predictions. They do not tune, refit,
clip predictions, or drop features. The `extrapolation` and `worst_prediction_contributions`
Excel sheets show which validation values exceeded fold-training ranges and which terms
dominated each fold's worst forecast. Sparse late-starting XAU/USDT volume inputs require review.
The score chart separates the primary and expanded models so their different error scales remain visible."""),
            nbf.v4.new_code_cell("""from pathlib import Path
import pandas as pd
from IPython.display import display, Image
repo = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'research/mts_gold/code').is_dir())
baseline = repo / 'research/mts_gold/training_artifacts/_training_baseline'
results = {p.stem: pd.read_csv(p) for p in (baseline / 'model1_results').glob('*.csv')}
ranges = results['extrapolation'].merge(
    results['coefficients'][['symbol', 'fold', 'model', 'feature', 'coefficient_standardized_x']],
    on=['symbol', 'fold', 'model', 'feature'], validate='one_to_one')
display(ranges.query("model == 'elasticnet_all313_diagnostic' and coefficient_standardized_x != 0").nlargest(12, 'max_abs_standardized_validation'))
display(results['worst_prediction_contributions'].query("model == 'elasticnet_all313_diagnostic' and fold == 'F3'"))
display(Image(filename=str(baseline / 'model1_results/fold_scores.png')))
""")]


def build(execute: bool = False, kernel: str = "python3") -> Path:
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    notebook = nbf.v4.new_notebook(cells=[
        md("""# MTS 60m Model 1: untuned baseline and manual feature review

Two independent task runs (GLD965/GLD9999), with dependent market evidence. No candidates are deleted.
The primary estimator uses the predefined 23-feature core. A second, clearly labeled all-313-feature
diagnostic Elastic Net provides wider permutation results. No hyperparameter search is performed.

Install `research/mts_gold/requirements-model1.txt` first. This notebook runs offline against the saved
all-date baseline tables, writes the Excel and Markdown/DOCX summaries, and retains detailed CSVs.
Six expanding chronological folds use >=30 observed embargo bars. These are development folds;
there is no new untouched final test period after inspecting these results."""),
        code("""from pathlib import Path
import sys, json
import numpy as np
import pandas as pd
from IPython.display import display, Image, Markdown
repo = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / 'research/mts_gold/code').is_dir())
sys.path.insert(0, str(repo / 'research/mts_gold/code'))
from model1_baseline import CONFIG, FOLDS, run_experiment, sha
baseline = repo / 'research/mts_gold/training_artifacts/_training_baseline'
manifest = json.loads((baseline / 'manifest.json').read_text())
display(pd.DataFrame([{k: item[k] for k in ['symbol', 'file', 'rows', 'valid_labels', 'numeric_candidates']}
                      for item in manifest['outputs']]))
display(pd.DataFrame(CONFIG.items(), columns=['setting', 'value']))"""),
        md("""## Labels, features and preprocessing

For each fold, initialize EWMA variance from the mean squared **training** hourly return; keep half-life=30.
The fitted label is `clip(next_log_return / sigma_t, -5, 5)`, not the precomputed causal-reference label.
Fold preprocessing keeps every supplied column: train median imputation (zero for all-null columns),
then training-only StandardScaler. Null flags and zero variance do not trigger model-input deletion.

The zero predictor is the benchmark. The Elastic Net settings are fixed above. Model 2 is not fitted;
any price forecast shown here uses trailing sigma for diagnostic rescaling only."""),
        code("""for task in manifest['outputs']:
    assert len(task['groups']['model1_core']) <= 25
    print(task['symbol'], 'core features:')
    display(pd.DataFrame({'feature': task['groups']['model1_core']}))
display(pd.DataFrame(FOLDS, columns=['fold', 'train_end_Bangkok', 'validation_start_Bangkok', 'validation_end_Bangkok']))"""),
        md("""## Train the fixed baselines and export the audit

This cell performs all fold fits, train-only diagnostics, validation block permutation,
paired block bootstrap, and exports. It can take several minutes. Progress is written to
`model1_results/progress.log`. Re-running replaces derived results only; candidate tables remain unchanged."""),
        code("""results = run_experiment(baseline)
display(results['fold_schedule'])
display(results['cv_summary'])
for task in manifest['outputs']:
    assert sha(baseline / task['file']) == task['sha256']
print('Input hashes unchanged. No features removed.')"""),
        md("""## 1–2. Null rate and zero variance

`null_ge_20pct` flags >=20%, including exactly20%. All-null variance is undefined;
zero variance means one observed distinct value. All diagnostics below use fold-training rows only."""),
        code("""flags = results['null_variance'].groupby(['symbol', 'fold']).agg(
    null_ge_20pct=('null_ge_20pct', 'sum'), all_null=('all_null', 'sum'),
    zero_variance=('zero_variance', 'sum'))
display(flags)
display(results['null_variance'].query("fold == 'F6' and symbol == 'GLD965'").sort_values('null_rate', ascending=False).head(15))"""),
        md("""## 3. VIF for multicollinearity

VIF is reported for both core and full candidate scopes using training-imputed values.
Undefined constant/all-null fields stay in the export. `inf` marks numerical collinearity
at the recorded eigenvalue tolerance. No recursive VIF-based deletion is performed."""),
        code("""display(results['vif'].groupby(['symbol', 'fold', 'scope', 'vif_status']).size().unstack(fill_value=0))
display(results['vif'].query("scope == 'core23' and symbol == 'GLD965' and fold == 'F6'").sort_values('vif', ascending=False))"""),
        md("""## 4. VARCLUS candidate representatives

PCA/quartimax variable clustering splits until the second eigenvalue is <=1.
R²-own, R²-nearest-other-cluster and the R² ratio are exported. A low-ratio representative
is only a suggestion. Cluster IDs are local to each fold, not stable labels across time."""),
        code("""display(results['varclus_clusters'].groupby(['symbol', 'fold']).size().rename('cluster_count'))
display(results['varclus_features'].query("fold == 'F6' and symbol == 'GLD965' and representative_suggestion").sort_values('r2_ratio').head(20))"""),
        md("""## 5. Validation permutation importance

Importance is validation MSE increase after 30-observation block permutation (20 repeats).
Positive is useful for this fitted estimator; negative/zero is not proof of universal irrelevance.
Collinear substitutes can mask each other's importance. Repeat p05/p95 describe dispersion,
not inferential confidence intervals. Review both the compact core and wider diagnostic model."""),
        code("""for model in ['elasticnet_core23', 'elasticnet_all313_diagnostic']:
    for symbol in ['GLD965', 'GLD9999']:
        print(symbol, model)
        display(results['permutation_summary'].query('symbol == @symbol and model == @model').nlargest(10, 'weighted_mean_importance'))
display(Image(filename=str(baseline / 'model1_results/permutation_core.png')))"""),
        md("""## Scores, acceptance and regime diagnostics

R² is measured against a zero forecast. Direction accuracy excludes |z_hat|<=0.05 and actual zeros;
coverage is reported. Accept a stage only if the paired 30-observation block-bootstrap 95% CI
for MSE improvement has lower bound >0. Regimes use the training median sigma of each fold.
Both purities are near-duplicates and should not be counted as independent tests."""),
        code("""display(Image(filename=str(baseline / 'model1_results/fold_scores.png')))
display(results['regime_metrics'])
display(results['hour_metrics'].query("model == 'elasticnet_core23'"))
display(results['fold_metrics'].query("partition == 'validation'"))"""),
        md("""## Manual selection and saved deliverables

Fill `manual_decision` and `manual_notes` in Excel's `manual_review` sheet. Review recurring
missingness, source timing, redundancy and fold stability before choosing features. Any later
selection using these validation results needs fresh or nested chronological evaluation.
The Markdown/DOCX summary explains the findings and proposed next development steps."""),
        code("""display(results['manual_review'].head(15))
display(pd.DataFrame({'deliverable': ['Model1_Baseline_Review.xlsx', 'Model1_Baseline_Summary.md',
                                     'Model1_Baseline_Summary.docx'],
                      'exists': [(baseline / p).exists() for p in ['Model1_Baseline_Review.xlsx',
                                  'Model1_Baseline_Summary.md', 'Model1_Baseline_Summary.docx']]}))
audit = json.loads((baseline / 'model1_results/run_manifest.json').read_text())
display(pd.DataFrame(audit['versions'].items(), columns=['package', 'version']))"""),
    ])
    notebook.cells.extend(postfit_cells())
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    notebook.metadata.language_info = {"name": "python", "version": "3.12"}
    nbf.write(notebook, DESTINATION)
    if execute:
        client = NotebookClient(notebook, timeout=1800, kernel_name=kernel, allow_errors=False,
                                resources={"metadata": {"path": str(ROOT.parents[1])}},
                                on_cell_start=lambda **kw: print(f"Executing cell {kw['cell_index']}", flush=True))
        try:
            client.execute()
        finally:
            nbf.write(notebook, DESTINATION)
    nbf.validate(notebook)
    return DESTINATION


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--kernel", default="python3")
    args = parser.parse_args()
    print(build(args.execute, args.kernel))
