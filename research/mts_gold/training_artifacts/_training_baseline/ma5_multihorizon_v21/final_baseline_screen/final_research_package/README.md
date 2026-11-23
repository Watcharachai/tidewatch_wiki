# Final GLD965 MA5 research package

Prepared 23 November 2026, Asia/Bangkok. Market snapshot ends **7 November 2026**. This package copies existing data, ten selected compact LightGBM model bundles, forty single-input calibrators, and four existing executed notebooks. It adds a standalone executed review notebook, consolidated Excel, DOCX documentation, monthly statistics, full predictions and 25 chart figures. No models or calibrators are retrained during assembly.

## Start here

- **`Final_Model_Summary.xlsx`**: all requested Excel topics 3.1–3.10. `Coverage_map` maps each requirement to sheets.
- **`Model_Documentation.docx`**: purpose, assumptions/data/model settings, development/selection, implementation, limitations, references, numerical results and the 25 chart figures.
- **`Final_Package_Review.ipynb`**: standalone executed review and local inference-reproduction checks. Run this notebook with this folder as its working directory.

## Files

- `data/Dataset_X_y.csv.gz`: original 42,803-row prepared context table, copied byte-for-byte. Includes candidate X, horizon-specific actual MA5, normalized residual labels and structural baselines. `eligible` controls the common contiguous five-horizon sample.
- `data/TRAIN_X_y.csv.gz`, `TEST_X_y.csv.gz`, `OOT_X_y.csv.gz`: exact partition members (24,194 / 10,372 / 3,629), with partition and Bangkok calendar fields added. Excluded context is preserved only in the full table.
- `data/predictions_h1.csv.gz` … `predictions_h5.csv.gz`: every partition row with actual/structural/raw/calibrated regression price and actual direction plus raw/all calibrated classification probabilities and classes. Excel `Predictions_h1`–`Predictions_h5` contain the same records.
- `models/h*_compact.pkl`: ten frozen models and their feature order, TRAIN imputation/scaling, and regression target transformation.
- `models/h*_{regression,classification}_{isotonic,linear,quadratic,cubic}.pkl`: forty original fitted calibrators. Regression selects **linear at all five horizons** using later-TEST RMSE; the other regression calibrators are retained as evidence. Classification retains all four methods.
- `notebooks/`: four original executed notebooks, preserved for audit. They keep their source-directory assumptions; use the standalone root notebook for local review.
- `evidence/`: parameters, feature gains, split/target summaries, model scores, monthly results, stability checks, deciles and original source snapshots. Source training scripts are archival and require the original repository hierarchy/helpers for retraining.
- `plots/`: raw/calibrated regression and classification monthly figures plus ECE/Brier reliability diagrams for every horizon.
- `requirements.txt`, `package_metadata.json`, `verification.json`, `checksums.json`: environment, provenance and verification.

## Excel contents

1. **3.1** `Dataset_description`: rows, positive/nonpositive counts and target fractions, train/test/OOT periods, price and price-change distributions.
2. **3.2** `Model_parameters`, `Calibrator_parameters`: selected ordered features and full estimator settings, target transforms and calibration equations/knots.
3. **3.3** `Regression_performance`, `Classification_performance`, `Stability_checks`: TRAIN, TEST, OOT, CAL_FIT and CAL_VALID performance, confusion counts and defined overfitting-gap checks. `Calibration_fit_statistics` includes original probability clipping/out-of-range statistics.
4. **3.4** `Predictions_h1`–`Predictions_h5`: full row-level actual and predicted outputs.
5. **3.5** `H*_raw_regression` + `Monthly_regression`: actual versus predicted MA5 across the monthly timeline, and monthly model/structural RMSE.
6. **3.6** `H*_raw_classification` + `Monthly_classification`: monthly accuracy/precision/recall, actual and predicted positive-class shares, average predicted probability.
7. **3.7** `Regression_features` and `Classification_features`: separate selected-model gain weights.
8. **3.8** `H*_calibration`, `Calibration_deciles`, classification/calibration performance: ECE/Brier diagrams and statistics.
9. **3.9** `H*_calibrated_regression` + `Monthly_regression`: selected calibrated regression price/RMSE results.
10. **3.10** `H*_calibrated_classification` + `Monthly_classification`: all calibrated classifiers and target-rate comparisons.

## Interpretation

All targets are future **trailing MA5**, h=1..5 (15–75 minutes). Class 1 means future MA5 exceeds the current observed MA5; ties count as 0. Regression predicts the unknown structural residual and reconstructs price. High MA5 direction accuracy partly comes from already-known price components.

Monthly groups use **Bangkok decision month**, with separate TRAIN/TEST/OOT rows. Split boundary months can be partial. Actual future MA5 is aligned to the decision timestamp, not the label-maturity timestamp. Price lines break at noncontiguous bars. “Predicted positive %” means share of predicted classes equal to 1; average probability is shown separately.

Base models are TRAIN-fitted. Calibrators fit earlier TEST with a 30-context-bar gap before later TEST validation. Regression chooses the smallest CAL_VALID RMSE; OOT is not used for choosing the calibrator. Classification retains all four. Full TEST combines fitted and validation observations. Calibrated TRAIN scores use later-fitted TEST parameters retrospectively. ECE uses fixed raw TRAIN probability deciles and set-specific count weights. Brier/accuracy should be compared alongside ECE; isotonic and polynomial calibrators do not guarantee future reliability. Polynomial classification outputs are clipped to valid probabilities.

The gain-diversity rules (all retained features >=5%, none >70%, at least three features) and <=2-point historical stability screen are design checks, not proof against overfitting. Structural-relative RMSE normalizes regression gaps across different volatility periods. No compact base model had a statistically resolved positive paired OOT gain over structural persistence. OOT dates were inspected in earlier research; these are development/backtest results, not a fresh prospective test.

## Local execution

Use Python 3.12:

```bash
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -r requirements.txt
# macOS/Linux:
.venv/bin/python -m pip install -r requirements.txt
```

Open `Final_Package_Review.ipynb` using that environment. Its inference checks load trusted bundled pickle objects, apply saved preprocessing, and reproduce forecasts without fitting. For new raw market observations, first generate the same causal completed-bar features with the original source pipeline.

`python build_package.py --report` regenerates reports from the copied data/models/evidence. The default `python build_package.py` additionally refreshes copies from the original repository folder structure. Neither command retrains models. Existing notebooks and DOCX/Excel are immediately reviewable without executing either command.
