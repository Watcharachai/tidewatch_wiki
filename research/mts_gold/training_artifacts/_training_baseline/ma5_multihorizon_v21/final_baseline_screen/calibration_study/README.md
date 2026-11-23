# Single-input calibration study

Open `Calibration_Study.ipynb` for executed analysis, methodology notes before/after each horizon, probability reliability plots (TRAIN, TEST, calibration validation, OOT), and actual/predicted MA5 regression lines (TRAIN, TEST, OOT).

Each of the ten frozen compact LightGBM models is calibrated by isotonic, linear, quadratic/square (degree 2), and cubic (degree 3). Square and quadratic are synonyms; the fourth method follows the earlier cubic experiment. X is the base output (THB MA5 or positive-class probability); Y is actual MA5 or binary direction. Polynomial fits standardize X within calibration fitting and preserve full coefficients in `calibrator_parameters.csv`. Classification outputs are clipped to valid probability bounds; raw out-of-range frequency is reported.

The first half of TEST supplies calibration fits, subject to label maturity. Thirty original context bars are embargoed before later TEST validation. Regression chooses minimum calibration-validation RMSE among four methods, without OOT selection. Linear wins all five horizons. All four classification calibrators are retained; no classification winner is declared. Base models remain TRAIN-fitted. TRAIN calibration scores are retrospective backcasts with later parameters; full TEST includes fit and validation and should not be treated as an independent test. OOT was inspected previously in project research.

ECE is sample-weighted, using raw base TRAIN probability decile cutoffs applied unchanged to all sets and calibrators. Repeated quantiles merge. Brier, probability log loss, accuracy, out-of-range rate and decile statistics are exported.

Files include the executed notebook, `metrics.csv`, `regression_selection.csv`, `split_audit.csv`, coefficient/threshold details, classification deciles, ten figures and forty calibrator pickle files. Trusted pickle models take base output as input: 1-D for isotonic, n-by-1 for polynomial pipelines. Apply clipping to classification outputs as in the notebook.

Linear improves OOT regression RMSE slightly at horizons 1, 2, 4 and 5, and very slightly worsens it at horizon 3. Isotonic price calibration clips outside its fit range and performs poorly when prices move beyond that range. Small calibration gains are descriptive and do not establish superiority over structural persistence or prospective predictive skill.
