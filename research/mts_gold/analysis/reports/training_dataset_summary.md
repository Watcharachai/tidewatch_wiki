# MTS 30m and 60m training dataset

Each row uses information available when the current MTS bar completes. The label is the fractional close return to the next **contiguous** completed bar of the same purity. Session gaps and year-boundary labels are excluded. The 2025/2026 split uses the decision time in Asia/Bangkok; the 2026 rows are held out.

| Timeframe | MTS target | Labeled rows | 2025 train | 2026 test | Numeric X candidates | Baseline X columns | XAU/USDT present | Next-return mean | Next-return std | 5th–95th percentile |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 30m | GLD965 | 20,659 | 11,122 | 9,537 | 235 | 182 | 9,899 | -0.0001% | 0.1758% | -0.238% to 0.236% |
| 30m | GLD9999 | 20,339 | 10,801 | 9,538 | 235 | 182 | 9,898 | 0.0003% | 0.1767% | -0.235% to 0.238% |
| 60m | GLD965 | 9,830 | 5,294 | 4,536 | 235 | 182 | 4,706 | -0.0012% | 0.2442% | -0.334% to 0.333% |
| 60m | GLD9999 | 9,633 | 5,097 | 4,536 | 235 | 182 | 4,705 | -0.0003% | 0.2457% | -0.329% to 0.334% |

## Missingness

Null rates below are measured on the **labeled rows**. The XAU/USDT source begins 11 December 2025 and ends 31 October 2026, while the MTS snapshot runs through 6 November 2026. XAUT/USDT begins in March 2026. Thus neither additional gold series has a useful full-2025 training history.

| Timeframe | Target | Feature | 2025 train null | 2026 test null |
|---|---|---|---:|---:|
| 30m | GLD965 | `xauusdt_30m_close` | 94.8% | 2.3% |
| 30m | GLD965 | `xauusdt_30m_return_lag30` | 95.0% | 2.3% |
| 30m | GLD965 | `xautusdt_30m_close` | 100.0% | 27.3% |
| 30m | GLD965 | `btcusdt_30m_close` | 0.0% | 0.0% |
| 30m | GLD965 | `us_yield_10y_1d_close` | 2.8% | 3.2% |
| 30m | GLD9999 | `xauusdt_30m_close` | 94.6% | 2.3% |
| 30m | GLD9999 | `xauusdt_30m_return_lag30` | 94.9% | 2.3% |
| 30m | GLD9999 | `xautusdt_30m_close` | 100.0% | 27.3% |
| 30m | GLD9999 | `btcusdt_30m_close` | 0.0% | 0.0% |
| 30m | GLD9999 | `us_yield_10y_1d_close` | 2.8% | 3.1% |
| 60m | GLD965 | `xauusdt_60m_close` | 94.8% | 2.3% |
| 60m | GLD965 | `xauusdt_60m_return_lag30` | 95.3% | 2.3% |
| 60m | GLD965 | `xautusdt_60m_close` | 100.0% | 27.3% |
| 60m | GLD965 | `btcusdt_60m_close` | 0.0% | 0.0% |
| 60m | GLD965 | `us_yield_10y_1d_close` | 2.8% | 3.1% |
| 60m | GLD9999 | `xauusdt_60m_close` | 94.6% | 2.3% |
| 60m | GLD9999 | `xauusdt_60m_return_lag30` | 95.2% | 2.3% |
| 60m | GLD9999 | `xautusdt_60m_close` | 100.0% | 27.3% |
| 60m | GLD9999 | `btcusdt_60m_close` | 0.0% | 0.0% |
| 60m | GLD9999 | `us_yield_10y_1d_close` | 2.8% | 3.1% |

All 235 numeric candidates and their statistics are in `../../training_artifacts/summary_statistics.csv`; per-column null counts and rates, including train/test splits, are in `../../training_artifacts/null_rates.csv`. Exactly 30 candidates are entirely null in the 2025 training portion, mainly the XAUT series. The baseline selection keeps numeric columns with at least 80% observed values and more than one distinct value **in 2025 training only**. It does not fit an imputer or scaler; those must be fit on training data during modeling.

## Source and leakage assumptions

- The new `xauusdt_30m_*` and `xauusdt_60m_*` features come from uploaded `data/XAUUSDT_30m.csv`. 60m bars aggregate exactly two complete 30m bars. The files carry no historical publication timestamps, so `available_at` is assumed to be the bar end. Confirm venue, symbol meaning, volume units and publication delay before using these fields in a strict point-in-time backtest.
- The existing feature matrix supplies MTS, MTS XAU/USD, XAUT/USDT, BTC/USDT and delayed FRED references. FRED availability is an assumed observation date plus two UTC days, not a verified vintage. Existing MTS completion times are also nominal.
- `y_next_return` and `y_next_close` are future outcomes. Use `load_xy()` or the manifest's `baseline_feature_columns` for X. Do not pass label columns or `label_available_at` as model inputs.
- MTS purities are separate prediction tasks. Evaluate against a zero-return/no-change baseline using chronological validation; a random row split would leak adjacent market states.
