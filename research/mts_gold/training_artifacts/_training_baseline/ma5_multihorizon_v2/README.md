# GLD965 15-minute MA5: direct multi-horizon experiment v2

Preliminary development results, 22 November 2026. Market data are the saved snapshot, not newly fetched observations.

## Deliverables

- `MA5_Multihorizon_Training.ipynb`: executed methodology, data/feature audit, model statistics, gain gates and price charts. Includes the training callable; automatic inspection loads saved results rather than retraining.
- `experiment.py`: full reproducible dataset preparation, training, scoring, bootstrap and export code. Run with the pinned dependencies in `requirements.txt`.
- `Preliminary_results.xlsx`: methodology, snapshot, feature definitions, training-fold selection diagnostics, gain importance, model metrics, confusion counts, bootstrap intervals and charts. Predictions occupy five sheets to respect Excel's row limit.
- `dataset_X_y.csv.gz`: all context rows, candidate X, horizon-specific Y, normalized residuals and structural baselines. `eligible` requires completed current MA5 plus five contiguous future bars; this common sample enables fair horizon comparisons. Unlabeled context remains for audit.
- `predictions.csv.gz`: all validation predictions, five horizons and seven model/task combinations. This long table repeats observations across models/horizons; rows are not independent samples.
- `fold*_*.pkl`: 80 fitted model/preprocessing bundles, for trusted local loading. Models output standardized residuals or class probabilities, never an untransformed price. For regression, invert target scaling then use `baseline + close * residual`.
- `verification.json`: independent label formula, residual reconstruction, importance normalization and executed-notebook checks.

## Main decisions

Predict MA5 at t+1 through t+5 (15–75 minutes), using five separate direct models. Structural persistence replaces future closes with the current close. Regression learns `(future MA5 - structural MA5)/close`; classification predicts `future MA5 > current observed MA5`, with ties nonpositive. Classification outputs are probabilities; no artificial price forecasts are generated for classifiers.

Features use completed current-bar data, own returns, rolling distribution/trend/volatility summaries, calendar context and inherited delayed reference returns. Raw absolute price levels and daily macro inputs are excluded in this first run. All null/variance screening, imputation, feature scaling and target scaling are fitted on each outer training fold only. There is no VIF/VARCLUS/Lasso gate, fine-tuning or calibration. Variance/std and overlapping windows are intentionally retained as first-pass candidates; correlated feature importance is not independent evidence and should be assessed in later group ablations.

Four expanding chronological folds use a 30-context-row gap and label maturity checks. All five horizons share the same eligible rows. Unlike a future prospective test, these 2025–2026 periods were already inspected in prior research. Parameters are fixed in advance; no best-fold deployment model is selected.

## Findings and selection rules

The requirement is interpreted as at least four features each contributing at least 5% of total LightGBM training split gain. Nineteen of twenty residual-regression fits pass. No classifier passes: each has only two or three such features. These are explicit failures of the requested gate; importances are not modified or redistributed.

Only fold 1 residual LightGBM horizons 1–3 pass both the gain gate and a positive lower 95% paired block-bootstrap MSE-improvement bound against structural persistence. Improvement is not stable across later folds. No model is accepted for deployment based on this experiment. A different random seed or forced feature balancing is not evidence of forecasting skill.

`accepted` in Metrics means **a single development fold passes its specified statistical and gain gates**, not that a model is approved globally. Regression compares MSE improvement; classification compares accuracy improvement. CIs use 1,000 circular 30-row bootstrap samples and have no multiplicity correction. Structural probabilities are degenerate 0/1 (clipped only for log loss), so their log loss is not a calibrated-probability benchmark; TrainPrior is the probability baseline.

Summary.csv contains arithmetic means of fold metrics, not pooled estimates or confirmatory tests. Price-level direction and R² can be mechanically strong because MA5 contains known prices. Compare with structural persistence, not a 50% threshold alone. For h=5, structural direction itself remains informative relative to current MA5 because it predicts the future average at the current close.

## Reproduce

```bash
python -m pip install -r requirements.txt
python experiment.py
```

Run from this directory or provide the script's path; its source path is relative to the experiment folder. Use Python 3.12. The original saved baseline directories are not overwritten.

To rebuild the summary workbook and execute the notebook after training, run `python build_report.py`. Set `MTS_NOTEBOOK_KERNEL` to your installed Jupyter kernel name (default `python3`). This also runs independent label/reconstruction checks.
