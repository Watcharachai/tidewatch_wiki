# V2.1 model parameters and small tuning study

The saved v2.1 experiment trained GLD965 MA5 forecasts at direct horizons 1–5 (15–75 minutes). This review lists the **actual parameters of every saved fitted model** and compares a small, fixed parameter grid. The chronological TRAIN/TEST/OOT split and feature preparation are unchanged. TEST selects parameters; OOT is scored only for each TEST-selected setting. Since OOT dates were inspected during earlier project work, this remains exploratory research, not an independent final test.

## Original settings (all horizons)

- Regression LightGBM: objective `huber`, 150 trees, learning rate 0.03, max depth 3, seven leaves, minimum 150 child samples, column fraction 0.7, L2 penalty 10, random seed 42, one thread.
- Classification LightGBM: same settings, default binary objective.
- Ridge regression: alpha 10, intercept and otherwise scikit-learn defaults.
- Logistic Regression: C 0.1, 2,000 max iterations, intercept, lbfgs defaults. Class threshold is probability >0.5.
- All four fitted models per horizon use the same 36 TRAIN-screened features. `original_model_parameters.csv` contains the complete `get_params()` output for all 20 models. Structural persistence and train-prior are rules, with no fitted hyperparameters.

## Candidate search and selection

- LightGBM: 12 settings per task/horizon, crossing tree count {80, 150, 300}, learning rate {0.015, 0.03}, minimum child samples {150, 300}; other settings fixed as above.
- Ridge: alpha {0.1, 10, 100, 1000}.
- Logistic Regression: C {0.01, 0.1, 1, 10}.
- In total 160 candidates. Minimize TEST RMSE for regression and TEST probability log loss for classification. For LightGBM, require at least three features each with >=5% of total TRAIN gain if any candidate achieves it. If no candidate passes, retain the best TEST-loss candidate and explicitly mark the gate failure. The selected models are refitted on TRAIN only; TEST and OOT are never included in their fit.

## Findings

The TEST-selected Ridge alpha is 1000 at every horizon. The TEST-selected regression LightGBM is 80 trees, rate 0.015 and minimum child samples 300 at every horizon. This suggests the original 150-tree model was somewhat too flexible for the TEST period. The best classifier Logistic C remains 0.1 except horizon 4, where 0.01 minimizes TEST log loss. Classification LightGBM keeps 150 trees at horizon 2 and selects 300 at the others. Its >=3-feature gain gate passes at horizons 1–2 and fails at 3–5; tuning does not solve that constraint.

OOT gains are mixed and small. At horizon 1, tuned LightGBM regression RMSE is 14.643 versus original 14.631 (worse), while structural persistence is 14.665. At horizon 5, tuned Ridge RMSE is 102.979 versus original 102.968 and structural 103.118. The tuned classifiers still do not exceed structural direction accuracy on OOT. Therefore no tuned configuration is recommended for deployment merely from this search.

## Files

- `Parameter_Review.xlsx`: original parameters, all 160 tuning trials, selected settings and TRAIN/TEST/OOT comparison.
- `original_model_parameters.csv`: exact saved model `get_params()` for each of the 20 horizon/task/model combinations.
- `all_trials.csv`: every candidate's TRAIN and TEST metrics, plus gain count and pass/fail. OOT metrics are intentionally absent from this table.
- `selected_parameters.csv`: selected candidate plus its OOT score.
- `comparison.csv`: original versus selected model and structural benchmark by partition.
- `h*_selected.pkl`: 20 trusted pickle bundles containing the refitted selected model, feature order, training medians/scaler, and target scaling where relevant.
- `selected_model_verification.csv`: selected bundles reloaded/refitted and OOT scores reproduced.
- `tune.py` and `save_selected.py`: reproducible study and saved-model verification.

Gain diversity is a diagnostic, not proof of forecast skill. Repeated use of TEST to select among models makes the reported TEST winner optimistic. The OOT period was previously inspected, so future unseen data are needed before judging generalization.
