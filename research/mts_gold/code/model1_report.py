"""Human-readable results and suggested next steps for the untuned Model 1 run."""
from pathlib import Path
import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mts_gold_matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from render_model_summary import render


def format_table(frame: pd.DataFrame, columns: list[str], digits: int = 5) -> list[str]:
    lines = ["| " + " | ".join(c.replace("_", " ") for c in columns) + " |",
             "|" + "|".join(["---"]*len(columns)) + "|"]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if pd.isna(value):
                values.append("undefined")
            elif isinstance(value, (float, np.floating)):
                values.append(f"{value:.{digits}f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def export_report(baseline: Path, results: dict, audit: dict) -> None:
    out = baseline/"model1_results"
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), constrained_layout=True)
    fold_metrics = results["fold_metrics"].query("partition == 'validation'")
    for column, symbol in enumerate(("GLD965", "GLD9999")):
        for row, (model, color, label) in enumerate((("elasticnet_core23", "#244875", "Primary: 23-feature core"),
                                    ("elasticnet_all313_diagnostic", "#b98221", "Diagnostic: all 313"))):
            axis = axes[row, column]
            f = fold_metrics.loc[fold_metrics.symbol.eq(symbol) & fold_metrics.model.eq(model)]
            axis.plot(f.fold, f.r2_vs_zero, marker="o", color=color, label=label)
            axis.axhline(0, color="black", linewidth=1)
            axis.set_title(symbol+" — "+label)
            axis.set_ylabel("Validation R² versus zero prediction")
            axis.grid(alpha=.2)
    fig.savefig(out/"fold_scores.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
    for axis, symbol in zip(axes, ("GLD965", "GLD9999")):
        pi = results["permutation_summary"].query("model == 'elasticnet_core23'")
        pi = pi.loc[pi.symbol.eq(symbol)].nlargest(12, "weighted_mean_importance").sort_values("weighted_mean_importance")
        axis.barh(pi.feature, pi.weighted_mean_importance,
                  color=np.where(pi.weighted_mean_importance.gt(0), "#244875", "#b34c44"))
        axis.axvline(0, color="black", linewidth=1)
        axis.set_title(symbol+": core-model permutation importance")
        axis.set_xlabel("Weighted validation MSE increase when permuted")
        axis.tick_params(axis="y", labelsize=8)
        axis.grid(axis="x", alpha=.2)
    fig.savefig(out/"permutation_core.png", dpi=150)
    plt.close(fig)

    cv = results["cv_summary"].query("model != 'zero'").copy()
    cv["model"] = cv.model.replace({"elasticnet_core23": "Core (23)",
                                    "elasticnet_all313_diagnostic": "Diagnostic (313)"})
    cv = cv.sort_values(["symbol", "model"])
    cv["decision"] = np.where(cv.acceptance_ci_positive.eq(True), "positive CV evidence", "does not pass CI rule")
    lines = ["# Model 1 baseline and manual feature review", "",
             "## Purpose and scope", "",
             "This run predicts the clipped volatility-scaled next-hour log return separately for GLD965 and GLD9999. Six expanding chronological folds span the available 2025–2026 history. There is no fixed year split and no separate untouched final test set in this run. After these validation results inform manual feature selection, they are development evidence, not a fresh final test.", "",
             "No feature has been removed from the candidate files. The primary model uses the predeclared **23-feature core**; an explicitly secondary **313-feature diagnostic model** supplies permutation importance for the wider candidate set. This wider model is not a replacement for the compact baseline. All-null and constant input columns remain in the diagnostic estimator schema.", "",
             "## Fixed, untuned model and label", "",
             "Both fitted estimators are Elastic Net with alpha=0.01, l1_ratio=0.5, max_iter=10,000, tol=1e-5 and an intercept. There was no hyperparameter search. The EWMA half-life is fixed at 30 observed returns; its variance seed is fitted separately from each fold's training returns. The target is `z = clip(next_log_return / sigma_t, -5, 5)`. Training-fold medians fill missing X values; entirely missing columns use zero. StandardScaler is fitted only on the fold's training rows.", "",
             "Model 2 has not been fitted. Exported return/price forecasts use the current trailing sigma solely as a labeled persistence-rescaling diagnostic; they are not the final two-model combination.", "",
             "## Out-of-fold results", "",
             "R² here is `1 − sum((z − z_hat)^2)/sum(z^2)`, relative to the zero predictor. Positive MSE improvement means a better forecast. The 95% interval uses 1,000 paired circular block-bootstrap samples of 30 validation observations within each fold. The acceptance rule requires the lower MSE-improvement bound to exceed zero.", ""]
    lines += format_table(cv, ["symbol", "model", "r2_vs_zero", "mse_improvement_ci_low", "mse_improvement_ci_high", "decision"])
    lines += ["", "The primary core model does not establish a reliable improvement over zero if its interval straddles zero, even when the point R² or conditional directional accuracy is positive. The all-candidate model is a stress test of retaining every input, including sparse ones; large negative scores are preserved without clipping or tuning.", ""]
    if "extrapolation" in results:
        extreme = results["extrapolation"].query("model == 'elasticnet_all313_diagnostic'").merge(
            results["coefficients"][["symbol", "fold", "model", "feature", "coefficient_standardized_x"]],
            on=["symbol", "fold", "model", "feature"], validate="one_to_one")
        extreme = extreme.loc[extreme.coefficient_standardized_x.ne(0)]
        extreme = extreme.sort_values("max_abs_standardized_validation", ascending=False).groupby("symbol", sort=False).head(3)
        lines += ["**Diagnostic failure analysis:** the expanded model extrapolates far beyond some fold-training feature ranges. In particular, sparse uploaded XAU/USDT volume histories can have a very small training scale and much larger later observations. The table below shows the largest validation standardized values among inputs with nonzero fitted coefficients; `worst_prediction_contributions` traces the resulting forecast errors to individual terms. All-null training inputs have zero coefficients and cannot explain these errors, even if their later standardized values are large. This is a reason for manual source/feature review, not an automatic deletion or a post-hoc prediction cap.", ""]
        lines += format_table(extreme, ["symbol", "fold", "feature", "train_observed_count", "max_abs_standardized_validation"])
    lines += ["", "Directional accuracy excludes abs(z_hat) <= 0.05 and realized zero returns; its prediction coverage is always reported. The bootstrap interval is for model loss improvement, not for individual permutation ranks. The two purities are strongly correlated and do not count as independent confirmations.", "",
              "![Forward-fold model scores](model1_results/fold_scores.png)", "",
              "## Chronological fold design", "",
              "Every fold begins training on 1 January 2025. Training expands to each listed end. A seven-calendar-day gap precedes validation, and the helper verifies at least 30 observed context bars in that gap. Labels crossing train/validation end boundaries are removed. Observed returns in the embargo update the EWMA state causally, without fitting estimator parameters.", ""]
    schedule = results["fold_schedule"].copy()
    for column in ("train_end", "validation_start", "validation_end"):
        schedule[column] = schedule[column].str.slice(0, 10)
    lines += format_table(schedule, ["symbol", "fold", "train_end", "validation_start", "validation_end", "train_rows", "validation_rows", "embargo_context_bars"])
    flags = results["null_variance"].groupby(["symbol", "fold"], as_index=False).agg(
        null_ge_20pct=("null_ge_20pct", "sum"), all_null=("all_null", "sum"), zero_variance=("zero_variance", "sum"))
    lines += ["", "## Feature diagnostics: review only", "",
              "Null rates and sample variances are calculated from the actual training rows in each fold, before imputation. A null rate **>=20%** is flagged, including exactly 20%. A column with one observed unique value has zero variance. Entirely missing columns are separately identified; their variance is undefined, not zero.", ""]
    lines += format_table(flags, ["symbol", "fold", "null_ge_20pct", "all_null", "zero_variance"])
    lines += ["", "**VIF:** both core-only and all-candidate scopes are reported. Train-median-imputed nonconstant columns define the correlation matrix. Undefined values for all-null/constant columns remain in the exported rows. Numerically singular dependencies are marked `inf`; warnings are >=5 and severe flags >=10. Correlation rank and tolerance are exported. No variable is iteratively deleted to reduce VIF.", "",
              "**VARCLUS:** the varclushi implementation uses PCA/quartimax splitting with a second-eigenvalue threshold of 1.0, no cluster-count cap and zero random starts. It uses training X only. For each candidate it reports its cluster, R² with its own cluster, R² with the nearest other cluster and `(1−R²_own)/(1−R²_nearest)`. The smallest ratio suggests a representative for your review. Cluster numbers are local to a fold and cannot be compared as stable IDs. Constants/all-null fields are mathematically ineligible for correlation clustering but remain in the dataset and review sheet.", "",
              "**Permutation importance:** evaluated on validation rows after training-fitted preprocessing, with 20 block-permutation repeats per feature. Positive values indicate increased MSE when that feature is disrupted. Correlated substitutes can each look unimportant. Repeat standard deviations and p05/p95 are dispersion measures, not confidence intervals for statistical significance. Zero importance can mean a zero Elastic Net coefficient; it does not prove the feature lacks value for every model.", "",
              "![Core feature permutation results](model1_results/permutation_core.png)", "",
              "## Manual decision and model development solution", "",
              "1. Review `manual_review` in the Excel workbook. It has editable `manual_decision` (keep/drop/review) and `manual_notes` fields. Nothing has been automatically removed. Use fold-to-fold stability, source quality and economic interpretation alongside flags.",
              "2. First review features that are repeatedly >=20% missing, entirely absent, or constant. Missing gold references that only appear late in the sample should not be judged as if they were available throughout training.",
              "3. Review clusters and VIF together to find redundant groups. Prefer interpretable, timely representatives, but do not blindly remove variables solely because a regularized linear model has high VIF or near-zero permutation importance.",
              "4. Use the compact baseline as the main reference. Any selected-feature experiment must be evaluated with nested chronological selection or a later unexamined period; selecting on these validation importance results and reusing the same scores would be optimistic.",
              "5. If the core model fails the positive-CI acceptance rule, retain zero as the accepted directional baseline. The trained models are still saved for inspection. Do not tune until the manual feature shortlist and evaluation protocol are fixed.",
              "6. Build the volatility model next with its own persistence-sigma comparison and train-fitted bias/magnitude calibration. Only then evaluate the full proposed rescaling against the natural inverse using current sigma. Report errors by volatility regime and Bangkok hour; the current workbook already supplies those diagnostics for Model 1.", "",
              "## Files and reproducibility", "",
              "`Model1_Training_Baseline.ipynb` executes the reproducible experiment. `Model1_Baseline_Review.xlsx` contains settings, hashes, schedules, metrics, null/variance, VIF, VARCLUS, coefficients, permutation results and all validation predictions. `model1_results/` preserves corresponding CSVs, fitted linear-model parameters/preprocessing, charts and a versioned run manifest. The initial candidate CSV files are unchanged.", "",
              "The source MTS prices end in early November 2026. MTS completion timestamps and FRED release delays are nominal rather than verified historical release vintages. Full-period candidate diagnostics are computed separately for each fold's training portion; future values are never used to fit its preprocessing.", ""]
    source = baseline/"Model1_Baseline_Summary.md"
    source.write_text("\n".join(lines).rstrip()+"\n")
    render(source, source.with_suffix(".docx"))
