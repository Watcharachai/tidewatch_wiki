# Reference feature dataset report

The saved feature matrix contains **148,796 target rows** across 15m, 30m, 60m, 1d and 7d, ending at the completed MTS daily cutoff of **2026-11-07 00:00 UTC**. It includes both `GLD965` and `GLD9999` as separate prediction targets. Each MTS purity and available reference has 1, 5 and 30 observed-bar price/return lags at its own resolution; the matrix also records elapsed time across gaps. No forecast target or accuracy estimate is included.

| Timeframe | Rows | Columns |
|---|---:|---:|
| 15m | 85,103 | 246 |
| 30m | 42,056 | 246 |
| 60m | 20,500 | 246 |
| 1d | 947 | 202 |
| 7d | 190 | 246 |

For 15-minute targets, the as-of match rate is effectively 100% for the MTS XAU/USD spot reference and 100% for Binance TH BTC/USDT, but **33.8%** for XAUT/USDT because its accessible history begins on 26 March 2026. Daily FRED indices, yields, VIX, USD/THB and WTI join only after their assumed availability date; their apparent high match rates do not establish historical publication-time accuracy. FRED availability is set to observation date plus two UTC days and requires a vintage-aware source before strict point-in-time backtesting.

MTS reports no volume for either purity or its XAU/USD chart. XAUT and BTC volumes measure trades in those Binance TH assets; they are not MTS volume. Verified 2025–2026 COMEX gold futures, SET, silver and Singapore gold histories were not obtainable from the public feeds checked, so those feature families remain absent. The [source and export specification](../docs/feature_sources.md) lists the exact data needed to add them. The [coverage CSV](../../feature_artifacts/coverage.csv) gives per-source/per-timeframe match rates, and the [manifest](../../feature_artifacts/manifest.json) records table hashes.
