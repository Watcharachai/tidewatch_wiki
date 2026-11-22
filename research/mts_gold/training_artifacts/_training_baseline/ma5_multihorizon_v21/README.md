# GLD965 MA5 multi-horizon experiment v2.1

Five direct next-MA5 horizons: 15, 30, 45, 60, and 75 minutes. The saved source data end 7 November 2026. This is a single chronological train/test/OOT design, with no folds or hyperparameter tuning.

The OOT cutoff is the last saved decision time minus two Bangkok calendar months: **7 September 2026 at 05:00 Asia/Bangkok**. Common eligible rows require a completed current MA5 and five contiguous future bars. From the earlier rows, 70%/30% form TRAIN/TEST in time order; labels crossing either boundary are purged. Counts: TRAIN 24,194; TEST 10,372; OOT 3,629. TEST begins 6 March 2026, OOT begins after the September cutoff. Exact UTC timestamps are in `Schedule.csv`.

Regression predicts `(future MA5 - structural persistence MA5)/current close`, then reconstructs the THB price. Classification predicts whether future MA5 exceeds current observed MA5, with ties set to zero. Both tasks compare against structural persistence. Models: Ridge and LightGBM regressor; Logistic Regression and LightGBM classifier; train-prior and structural baselines. Model settings are fixed from v2, no OOT tuning. Own completed-bar and lagged reference return features are used, without raw price levels. Feature null/variance screening and median/scaler fitting use TRAIN alone.

The requested feature rule is **at least three features, each with at least 5% of total training gain**, for each LightGBM. Every regression horizon passes (4, 4, 5, 11, 9 features). Classification horizons 1 and 2 pass (3 each); horizons 3–5 fail (2 each). This rule measures use of features, not forecasting skill. Failed models are reported without changing their gain.

**OOT finding:** Structural persistence has the best directional accuracy for all five horizons. LightGBM regression slightly lowers structural price RMSE at horizons 1–2; Ridge slightly lowers it at horizons 4–5. No fitted model consistently wins across all horizons and both criteria. OOT has already been viewed in previous project experiments, so it is chronological but not a fresh untouched holdout.

Files:

- `MA5_V21_Training_Results.ipynb`: executed notebook showing split, feature gain, model metrics, confusion counts, and chart.
- `experiment.py`: reproducible training and scoring source; `build_notebook.py`: rebuilds the executed notebook from saved outputs.
- `V21_preliminary.xlsx`: methodology, dates, full TRAIN/TEST/OOT metric and confusion tables, feature diagnostics/gain, and actual vs predicted chart.
- `Price_actual_vs_prediction.png`: TEST and OOT price comparisons by horizon. Price-level lines naturally overlap because MA5 includes known/current information; see RMSE for differences.
- `Dataset_X_y.csv.gz`: all candidate X and five Y/residual/baseline columns, with eligibility flag.
- `Predictions.csv.gz`: row-level predictions and classes for every partition/model/horizon.
- `h*_*.pkl`: trained models plus frozen preprocessing; load only trusted pickle files.

Run in a Python 3.12 environment with requirements from the adjacent v2 folder:

```bash
python -m pip install -r ../ma5_multihorizon_v2/requirements.txt
python experiment.py
python build_notebook.py
```

Monthly classification accuracy, positive precision and recall by horizon, plus OOT actual-price charts with direction errors, are in [monthly_classification](monthly_classification/README.md). Run `python monthly_classification.py` to regenerate them from the frozen predictions.

The [parameter review](parameter_review/README.md) lists all original horizon-specific fitted model settings and a small TEST-selected tuning experiment, including selected bundles and OOT comparisons.
