# Frozen fold3 LightGBM with isotonic and linear calibration

This desktop package scores the saved GLD965 15m history from 1 January2025 to 7 November2026 (Bangkok time). It predicts the next completed bar's trailing five-close average price, in original THB quote units. It contains 42,803 context rows and 40,226 scoreable targets. The models are loaded from the existing fold3 artifacts; no full-history refitting is performed.

## Run on your desktop

Extract `Final_BaseModel_Desktop.zip`, then open a terminal in the extracted `_final_basemod` folder. Python3.12 is recommended; `requirements.txt` pins the export environment.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe predict_local.py
```

On macOS/Linux, create the environment with `python3.12 -m venv .venv`, then use `.venv/bin/python` for installation and execution. Open `Final_BaseModel_Local.ipynb` in VS Code/Jupyter and select that same environment. The notebook has saved execution results and needs no original repository checkout. For a browser UI, install JupyterLab separately in that environment.

```python
import pandas as pd
from predict_local import load_models, predict

data = pd.read_csv("validation_oot1_X_y.csv.gz")
forecasts = predict(data, load_models())
print(forecasts.head())
```

`predict_local.py` reproduces the full-history forecasts, descriptive statistical comparison, bootstrap intervals, plots and Excel workbook. It overwrites only derived outputs in this folder. It does not fit a model.

## Files and model units

- `prediction_bundle.pkl`: LightGBM Booster, isotonic and sklearn LinearRegression objects, and frozen preprocessing. Use `predict_local.predict()` for the complete workflow.
- `lightgbm_fold3.pkl`: the native LightGBM Booster. Its input is the ordered, median-imputed, standardized45-feature matrix and its output is the standardized MA5 target. Invert using target_mean and target_scale in `preprocessing.json` before calibration.
- `isotonic_fold3.pkl` and `linear_fold3.pkl`: calibration model objects. Their input is the physical-price LightGBM prediction, not the standardized target. Their output is calibrated price MA5. For linear, pass X as an n-by-1 matrix; for isotonic, a one-dimensional array.
- `lightgbm_fold3.txt`, `preprocessing.json` and `calibration_parameters.json`: original text/JSON representations. The linear object is reconstructed from saved coefficients; isotonic is reconstructed from saved fitted knots. Predictions are checked against the original calibration results.
- `feature_schema.csv`: exact45 feature names, original training medians and feature scaling. The supplied CSV columns are already lagged; do not shift them again or fit new preprocessing on all dates.
- `base_training_X_y.csv.gz`: the original24,087 matured fold3 base-training rows.
- `base_validation_X_y.csv.gz`: all8,062 original fold3 base-model validation rows, including the calibration-fit and evaluation windows.
- `calibration_dev_X_y.csv.gz`: original4,030 calibration-fit rows.
- `validation_oot1_X_y.csv.gz`: original4,001 later calibration-evaluation rows.
- `post_fold3_backtest_X_y.csv.gz`: later context after the original fold3 evaluation window; unlabeled rows are retained for audit.
- `all_time_X_y_context.csv.gz`: every context row, with45 prepared X columns, physical Y, decision/label times, close, structural baseline and provenance flags. Rows without contiguous MA labels have null Y.
- `all_time_predictions.csv.gz`: predictions for every context row; scores exclude null actuals.
- `Final_BaseModel_Comparison.xlsx`: actual-versus-prediction plots, scores by period and provenance, paired model-comparison intervals, coverage and every prediction.

The notebook supports local inference and inspection. A new training/tuning run on these datasets is a separate experiment; the frozen prediction function should not be refitted automatically. For new raw market data, use the original market-feature preparation pipeline to create the same45 columns and causal states.

## Periods and interpretation

`DEV` is the original calibration-fit block (12 February–21 April2026). `OOT1` is the original later calibration-evaluation block (22 April–26 June2026). `REST_2025` contains Bangkok calendar2025; these observations trained the base LightGBM and the calibrators are applied retrospectively using2026 parameters. They are backcasts, not independent test forecasts. `REST_2026` is the remainder and mixes base training, embargo/context and later backtesting. Use the finer `provenance` field to isolate those roles.

`is_base_training_member` and `is_calibrator_training_member` identify the exact original training membership. `ALL` statistics deliberately mix fitted and later observations and are descriptive. OOT1 and the later period have already been inspected during prior research, so they are not a new untouched final test.

Four of the five target prices are already known at the decision time. The structural baseline assumes the next close equals the current close. High price-level R2 does not establish next-price skill. These outputs forecast MA5, not trading PnL.

Isotonic calibration clips predictions outside its fitted input range. Applying it to earlier, lower2025 prices can produce severe errors. Compare both calibrators across all labeled periods rather than interpreting the highlighted OOT1 score alone.

All dates in period definitions use Asia/Bangkok. Plot axes use UTC. The package uses the latest saved snapshot; it does not fetch current prices. Paired MSE-gain CIs use1,000 circular30-row block-bootstrap samples stratified by provenance, without multiplicity correction. A positive gain favors the first named model.

## Quarterly actual/predicted charts and residual bands

The latest notebook includes four-model pairwise time-series panels for each quarter in2025 and2026, plus the exact DEV period.2026Q4 is partial through7 November. `quarterly_plots/` stores nine chart images, empirical coverage, model-specific DEV residual percentiles and all timestamp-level bounds. `Quarterly_Prediction_Bands.xlsx` embeds all charts and the percentile/coverage tables.

Run `python quarterly_bands.py` to reproduce these outputs without refitting any model. P05–P95 is a central90% prediction band. The separate95% band uses P2.5–P97.5. They are empirical prediction bands, not confidence intervals for a conditional mean. Bounds equal the saved prediction plus frozen DEV residual percentiles. DEV residuals are in-sample for the calibrators; nominal coverage is not guaranteed on later data.2025 bands apply2026-estimated parameters retrospectively and are not uncertainty forecasts available in2025. Quarter labels and chart axes use Asia/Bangkok decision time.
