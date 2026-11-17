# GLD965 15-minute direction experiment

Predict the next contiguous 15-minute volatility-scaled log return. `Z_return_lag5` is the one-bar scaled return five observed bars ago, used as a candidate predictor and retained in all four final feature sets.

- [Executed training notebook](GLD965_15m_Training.ipynb)
- [Excel results and selection audit](GLD965_15m_Review.xlsx)
- [Report](GLD965_15m_Report.md) and [editable DOCX](GLD965_15m_Report.docx)

The waterfall drops nonlagged features, null rates >=20%, zero variance, all but the top three VARCLUS R-squared-ratio candidates per cluster, and iteratively the largest VIF above 10. A fixed-alpha Lasso ranks the survivors using chronological block permutation; the top 45 remain. Four outer TimeSeriesSplit folds use 30 context bars of embargo. Inside each outer training window, separate fit, permutation-ranking, and tuning blocks prevent outer validation from influencing any selection or tuning.

`waterfall.csv` records counts and removed features; `null_variance.csv`, `varclus.csv`, `vif.csv`, and `permutation.csv` preserve all stage diagnostics. `selected_features.csv` lists fold-specific final selections. `tuning.csv` records every trial; `schedule.csv` records boundaries and EWMA seeds. `predictions.csv.gz` includes every validation Z prediction and actual label. Fitted linear parameters and LightGBM text models include their preprocessing JSON.

Install `research/mts_gold/requirements-model1-15m.txt`. From the repository root:

```bash
python research/mts_gold/code/model1_15m_waterfall.py
# Or regenerate and execute the notebook (default kernel python3):
python research/mts_gold/code/build_model1_15m_notebook.py
```

Set `MTS_NOTEBOOK_KERNEL` to use a specific installed kernel. Rerunning overwrites these derived outputs. Original datasets and the previous 60m experiment are preserved. These are development folds across 2025–2026, not a fresh final holdout.
