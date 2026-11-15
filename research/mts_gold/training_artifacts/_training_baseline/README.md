# All-date 60m two-model baseline dataset

## Untuned Model 1 and manual feature review

The executed [training notebook](Model1_Training_Baseline.ipynb), [Excel review workbook](Model1_Baseline_Review.xlsx), and [results/development summary](Model1_Baseline_Summary.md) ([DOCX](Model1_Baseline_Summary.docx)) contain the baseline experiment. No candidate columns are deleted. The primary estimator uses the existing 23-feature core; a separate all-313-feature diagnostic estimator supplies wider permutation importance.

The workbook includes per-fold null-rate flags (>=20%), zero variance, VIF, VARCLUS, permutation importance, coefficients, scores, and editable `manual_decision`/`manual_notes` columns. All inputs and transformations are fitted on chronological training folds only. Once validation diagnostics guide manual selection, subsequent model comparisons require fresh or nested chronological evaluation.

Install `research/mts_gold/requirements-model1.txt` and run the notebook, or execute `python research/mts_gold/code/model1_baseline.py`. `python research/mts_gold/code/build_model1_notebook.py --execute` regenerates and executes the notebook using the current Python kernel. Re-running replaces derived results and the Excel workbook; save an edited manual-selection workbook separately first. The original baseline dataframes remain unchanged.

The input tables described below were prepared for separate GLD965 and GLD9999 experiments using every available date in the current research snapshot. The source tables have **no fixed 2025/2026 split**, no fitted imputer/scaler, and no global feature selection; the experiment above fits preprocessing separately inside each fold. The existing snapshot ends on 7 November 2026; preparation does not fetch newer observations.

| File | Context rows | Rows with next-hour labels | Numeric X candidates |
|---|---:|---:|---:|
| `baseline_60m_GLD965.csv.gz` | 10,338 | 9,830 | 313 |
| `baseline_60m_GLD9999.csv.gz` | 10,162 | 9,633 | 313 |

Each file retains all completed bars so lag/rolling calculations do not skip unlabeled session-end bars. `label_valid` identifies rows with an exact next-hour MTS bar; labels are null at gaps and at the final row. A contiguous pair crossing New Year is allowed in this combined dataset. The fold helper purges labels crossing each actual fold boundary.

## Inputs

The 235 existing numeric candidate features are retained, including uploaded XAU/USDT. This builder adds 78 numeric candidates. Timestamp and provenance fields remain in the tables for auditing but are excluded from the numeric feature groups. `feature_groups.csv` and `manifest.json` list every input column and the suggested groupings:

- **Model 1 core (23 inputs):** own/cross-purity, MTS XAU/USD and BTC log-return shifts at 1/5/30 observed MTS bars; matched-window MTS-minus-XAU log-return gaps over 1/5/30 bars; current own/cross log return; cyclic Bangkok decision hour/day-of-week; gap/session flag and elapsed minutes.
- **Model 2 HAR (12 inputs):** RMS realized volatility over the last 1/5/30 valid hourly returns; absolute log-return shifts at 1/5/30 observed bars; cyclic hour/day-of-week, gap/session flag and elapsed minutes.
- **Rolling-distribution ablation:** price and log-return min, max, mean, sample variance, adjusted skewness, and adjusted excess kurtosis over 7/15/30 observations. A trailing price mean is the MA; `ma_gapW = close/price_meanW − 1`. Window elapsed minutes expose market closures and missing observations.
- **Macro ablation:** existing yields/curve, VIX, USD/THB and oil fields. Add these in a separate experiment; they are not part of the 23-input core.

All rolling windows include only information through the current completed bar. Price windows use the last W observed MTS closes. Return windows/HAR use the last W **valid within-session hourly returns**, spanning previous sessions when necessary; a return across a gap is excluded, and the last rolling state is retained at a gap bar. This avoids permanently empty 30-hour windows in a market that closes daily. Full W-observation warm-up is required. Windows do not mean fixed wall-clock hours. Sample variance uses ddof=1; kurtosis is excess kurtosis, with the constant-window convention zero. No centered MA is used.

`own_log_return` is the current hourly log change only when the prior bar is exactly one hour earlier. `*_log_return_shift5` means the one-bar return observed five MTS rows ago; this differs from the existing five-bar cumulative `*_return_lag5`. Cross/XAU/BTC current returns require the source to end on the same bar and span exactly 60 minutes. The `fair_return_gap_windowW` uses cumulative MTS and XAU log returns with matching start/end windows; it is a return difference including FX/local effects, not a physical-gold pricing premium.

`session_open_flag` identifies the first available row or a gap exceeding 60 minutes; it is a **gap-based proxy**, not a verified exchange-session calendar. `gap_log_return` retains the separate between-session price move for optional study.

## Targets and EWMA

- `y_next_log_return = ln(close[t+1]/close[t])`, with the next completed bar required to be exactly one hour later.
- **Model 2:** `y_model2_log_abs = ln(1e-6 + abs(y_next_log_return))`.
- **Model 1:** `y_model1_z = clip(y_next_log_return/sigma_t, -5, 5)`, materialized **per fold** by the helper below.
- `label_available_at` records when the next bar completes; it must not be included in X. Future price `y_next_close` is for evaluation/reconstruction, never an input.

Because the fold boundaries and tuned half-life are not chosen yet, a single globally seeded Model 1 target would not implement the requested fold-fitted scheme. The CSV therefore includes `sigma_ewma_hl30_causal` and `y_model1_z_causal` as **reference-only** columns: HL=30, initialized at the first finite observed squared return, updated only forward. These are excluded from all feature candidate groups. They are not the target to use for actual cross-validation.

`materialize_fold()` estimates the EWMA variance seed as the mean squared hourly return from the selected fold training window, applies the chosen half-life, and returns `sigma_t` plus the correctly seeded `y_model1_z`. The recurrence is `v_t = (1-alpha)*v_previous + alpha*r_t^2`, with `alpha = 1 - 2^(-1/half_life)` and sigma floored at 1e-6. At gaps, the variance state is held; history during the embargo is processed causally before validation. Updating volatility from already-observed validation returns is permitted; validation future returns never seed training state.

Model 2 bias correction and magnitude-to-RMS calibration require a fitted model and must later be estimated within training folds. No such calibration has been fitted in this preparation step. Its inverse log label measures absolute-return magnitude, not automatically a standard deviation.

## Loading X/y for a chronological fold

Run from the repository root. The dates below illustrate a fold; no split is stored in the source files. Boundaries are timezone-aware, half-open decision-time ranges.

```python
import sys, json
from pathlib import Path
import pandas as pd
sys.path.insert(0, "research/mts_gold/code")
from prepare_baseline import materialize_fold

root = Path("research/mts_gold/training_artifacts/_training_baseline")
manifest = json.loads((root / "manifest.json").read_text())
entry = next(x for x in manifest["outputs"] if x["symbol"] == "GLD965")
data = pd.read_csv(root / entry["file"], low_memory=False)
train, validation, fold_info = materialize_fold(
    data,
    train_start="2025-01-01T00:00:00+07:00",
    train_end="2025-07-01T00:00:00+07:00",
    validation_start="2025-07-08T00:00:00+07:00",
    validation_end="2025-10-01T00:00:00+07:00",
    half_life=30, embargo_bars=30,
)
X1_train = train[entry["groups"]["model1_core"]]
y1_train = train["y_model1_z"]
X2_train = train[entry["groups"]["model2_har"]]
y2_train = train["y_model2_log_abs"]
# Select the same columns from validation; fit preprocessing on train only.
```

The helper requires at least 30 actual context bars between the training end and validation start and removes unmatured labels. Treat targets separately. The descriptive all-date `feature_quality.csv` is for inspection; do not use its future-period statistics to fit preprocessing or select features inside a fold. Existing sparse gold references and assumed FRED release timing remain limitations.

Rebuild the files and quality inventory with `python research/mts_gold/code/prepare_baseline.py`. This preparation does not train either model.
