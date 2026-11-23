# GLD965 MA5 compact-feature baseline assessment

Screened 23 November 2026 (Asia/Bangkok) on the saved v2.1 data. **All ten direct-horizon LightGBM candidates meet the three requested design screens; none demonstrates a statistically resolved gain over structural persistence on OOT.** They are final *research baseline candidates*, not approved live predictors.

## Hard rules

1. Use at least three retained features. **Every retained feature** must have >=5% of total TRAIN LightGBM split gain.
2. No retained feature may exceed 70% of total TRAIN gain.
3. Use a declared train/test/OOT stability screen: TEST and OOT degradation relative to TRAIN must each be <=2 percentage points. Regression compares RMSE/structural RMSE for each partition, accounting for different target volatility. Classification compares absolute accuracy. A negative gap means the later period scored better.

The third rule is a practical screen; finite historical data cannot prove absence of overfitting. Ridge and Logistic Regression have no tree split-gain shares, so this literal gain exercise applies to LightGBM only.

## Selection protocol

Models fit **TRAIN only**. A TRAIN gain ranking from the previous full-feature v2.1 model supplies candidate feature sets with 3, 4, 5, 6, 8 or 10 features. We consider the leading set and sets omitting the top one or two ranked features. For the difficult 30-minute classifier, we also test offsets up to eight. Each set uses depth 2 with 3 leaves or depth 3 with 7 leaves, while retaining the previously TEST-selected learning rate, tree count and leaf minimum. This produces **432 candidate fits** across five horizons and two tasks.

Candidate screening and parameter selection use TRAIN and TEST only. Among candidates passing the two gain bounds and TRAIN/TEST gap, we select lowest TEST RMSE (regression) or TEST log loss (classification). OOT scores only the selected model. The selected models are saved with their ordered features and TRAIN-fitted preprocessing. No OOT result is in `candidate_screen.csv`.

| Horizon | Regression features; OOT RMSE vs structural | Classification features; OOT accuracy vs structural |
|---|---|---|
| 15m | 5; 14.641 vs 14.665 | 4; 81.70% vs 84.24% |
| 30m | 3; 31.717 vs 31.751 | 5; 75.67% vs 81.23% |
| 45m | 6; 52.631 vs 52.626 | 3; 76.16% vs 77.60% |
| 60m | 5; 76.587 vs 76.578 | 3; 72.28% vs 74.62% |
| 75m | 4; 103.122 vs 103.118 | 3; 68.01% vs 69.69% |

All ten meet the gain and stability rules. The paired circular 30-row bootstrap, 1,000 samples, has **no positive lower 95% bound** for improvement versus structural persistence. Every classifier is worse than structural direction accuracy, with negative paired accuracy-improvement intervals. The small regression RMSE wins at 15 and 30 minutes have intervals spanning zero. Feature-gain diversity is a diagnostic, not evidence of additional forecast information. Structural persistence remains the practical benchmark and fallback.

## Files

- `Final_Baseline_Review.ipynb`: executed results notebook with selected features, gains, gate checks and OOT comparisons.
- `Final_Baseline_Screen.xlsx`: all candidates, ten selected models, and their feature gain shares.
- `candidate_screen.csv`: TRAIN/TEST metrics and gain checks for all 432 candidates. OOT is absent.
- `selected_summary.csv` and `selected_gain.csv`: ten selected configurations, hard-gate results, OOT scores and exact retained-feature weights.
- `h*_compact.pkl`: ten trusted pickle bundles, one per horizon and task, with model, feature order, medians/scales and regression target scale.
- `compact_OOT_predictions.csv.gz` and `paired_OOT_intervals.csv`: independently reconstructed forecasts and paired OOT intervals for MSE improvement (regression) or accuracy improvement (classification). Positive values favor the model.
- `screen.py` and `validate_selected.py`: reproducible training, selection and validation.

This OOT period was inspected in earlier research. The design rules do not address that reuse. A future untouched prospective sample is necessary before any predictive-skill claim or deployment decision.

The consolidated [final research package](final_research_package/README.md) bundles the datasets, model/calibrator pickles, notebooks, requested 3.1–3.10 Excel analysis, monthly plots and DOCX documentation for local review.
