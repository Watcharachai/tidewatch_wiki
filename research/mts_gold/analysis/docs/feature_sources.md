# Quantitative feature dataset: sources, coverage and requested exports

The feature builder extends the existing direct-MTS gold history. It uses the same `GLD965` (96.5% THB) and `GLD9999` (99.99% THB) target candles, with lags **1, 5, 30 observed bars** for each of 15m, 30m, 60m, 1d and 7d. The previously exported 1/3/7/14/30 historical-return analysis remains available; this is a separate predictive feature matrix. Each lag also records the actual elapsed minutes so a weekend crossing is visible. For references, an as-of join permits only bars available by the target's decision time. Missing and stale references remain null.

## Working public feeds

| Feature family | Series | Source and interpretation | Resolution |
|---|---|---|---|
| Direct MTS targets | 96.5%, 99.99% chart closes | MTS public UDF; THB; bid/ask and weight basis undisclosed | Native 15m, 1d; derived 30m, 60m, 7d |
| Reference gold spot | `XAUUSD` | MTS public UDF USD spot chart; not an independent US exchange quote | Native 15m, 1d; derived 30m, 60m, 7d |
| Tokenized gold and volume | `XAUTUSDT` | Binance TH spot trade price and base-token volume, not MTS physical-gold volume | Native 15m; derived 30m, 60m, 1d, 7d |
| Referenced asset and volume | `BTCUSDT` | Binance TH spot trade price and base-BTC volume | Same as tokenized gold |
| US equity indices | S&P 500 `SP500`, Nasdaq Composite `NASDAQCOM`, Dow Jones `DJIA` | FRED daily observations; index level, no volume | Daily |
| US yield curve | 3-month `DGS3MO`, 2-year `DGS2`, 10-year `DGS10`, 30-year `DGS30` | FRED daily percent yields; derived 10y−2y and 10y−3m in percentage points | Daily |
| Volatility | `VIXCLS` | FRED CBOE VIX close | Daily |
| Currency | `DEXTHUS` | FRED USD/THB rate | Daily |
| Oil | `DCOILWTICO` | FRED WTI crude spot in USD/barrel | Daily |

FRED data are labeled as available **two UTC days after their observation date** for a conservative research join. This is an assumption, not a verified historical release time or a revision-free vintage. No daily series is interpolated to look like native intraday data. The availability age is retained for every joined reference. MTS symbols report `has_no_volume=1`; the pipeline never creates an MTS volume field from price. A volume field on `XAUTUSDT` measures exchange-traded XAUT tokens, not gold spot volume in Thailand. Futures contract volume is a different measure again.

The public Yahoo chart API returned HTTP 429 in this environment, SET's public API returned HTTP 403, and accessible Stooq/Nasdaq Data Link attempts did not yield verified historical gold-futures data. No futures or SET series is labeled complete. A Singapore gold series also needs a specific venue/contract/currency definition and an authorized historical source; a generic SGD conversion is not a Singapore market observation.

## Exports requested from the project owner

Please collect the following **dated 2025–2026 historical exports** if you have an approved vendor, exchange or broker source. Priority 1 is COMEX gold futures and the SET index. Priority 2 is silver spot, silver futures, and a specific Singapore gold benchmark. These complete the requested reference families and allow an incremental-value test. We can run numerical baselines with the public feeds while those exports are sourced.

1. `external/us_gold_future.csv`: COMEX GC continuous futures close and traded contract volume. Supply the roll rule, active contract per observation, exchange timezone and units. An unadjusted front-month roll can create false returns and lags.
2. `external/set_index.csv`: official SET index close, and turnover or index volume only if the vendor defines it clearly. Source and timestamp should be explicit.
3. `external/silver_spot.csv` and `external/silver_future.csv`: spot XAG/USD and COMEX SI or comparable, with units and futures roll details.
4. `external/sg_gold_reference.csv`: a named Singapore spot benchmark or SGX futures contract. State venue, currency, physical unit, trading hours and settlement/roll convention. If no accessible, licensed historical source exists, leave it pending.
5. For actual MTS volume: request an MTS export that identifies **what** the volume counts (contracts, baht, baht-weight, orders, or turnover), its interval, timezone and publication time. The existing public chart provides none. Do not substitute XAUT volume for it.

Use one CSV per series and timeframe, with an explicit point-in-time availability stamp. The plain names above mean daily data; for intraday or weekly data use a suffix such as `us_gold_future_15m.csv`, `_30m.csv`, `_60m.csv` or `_7d.csv`. The loader uses the supplied bars at their named resolution and does not infer a higher resolution from a daily close. Supply complete, already aggregated bars in each file.

```csv
timestamp,available_at,close,volume
2025-01-02T00:00:00Z,2025-01-02T08:00:00Z,2650.25,120000
```

`timestamp` is the observation/bar time; `available_at` is when that value first became usable; both must be UTC-aware ISO 8601. `close` is required and positive. `volume` is optional if the series has no defensible measure. Do not put a row's later corrected value at its original publication time without preserving the revision. The loader rejects absent availability, invalid prices, duplicate timestamps and negative volume. These exports are local inputs under `research/mts_gold/external/`; only data whose sharing rights permit GitHub publication should be committed.

## Additional candidates for a later collection round

- COMEX futures basis versus spot, open interest and the term structure, with contract-aware rolls. These may matter more than raw futures price lags.
- Real yields and Treasury inflation breakevens (FRED TIPS series), since gold's opportunity cost can be tied to inflation-adjusted rates.
- USD index/DXY and USD/THB intraday rather than daily, if licensed histories exist. The THB conversion can dominate local MTS moves.
- Silver/gold ratio, oil, copper, and gold ETF holdings/flows as cross-asset measures; use only data available before each decision time.
- US CPI, payrolls, FOMC, Bank of Thailand policy, and important China releases, with scheduled/released/revised timestamps separated.
- Market-session, holiday, time-of-day, and stale-feed features. These are essential for 15–60 minute forecasts and reduce spurious weekend-lag effects.
- MTS versus XAU×USD/THB premium/basis, computed using only contemporaneously available quotes and a declared unit conversion.

## Running and interpreting the output

```bash
python research/mts_gold/code/features.py run
python research/mts_gold/code/features.py build
```

`run` fetches and builds; `build` recomputes from cached reference CSVs without network. The collector uses the current MTS `data/bars.csv` cutoff, so reference history cannot extend the target sample by itself. `feature_data/manifest.json` records fetched source URLs, hashes, coverage and still-pending exports. `feature_artifacts/market_features_<timeframe>.csv.gz` contains one wide matrix per timeframe, `coverage.csv` reports non-null join rates, and `manifest.json` lists row counts and output hashes. Each matrix includes both MTS purities as rows; `symbol` selects the forecast target. Unavailable features are null. The feature matrix is descriptive input preparation; no forecast labels are created here and no predictive accuracy is claimed.

The versioned `feature_artifacts/reference_sources_asof_2026-11-07.zip` preserves the fetched responses and normalized reference CSVs; `source_snapshot.json` records its checksum. To reproduce the saved feature matrices offline, first restore the MTS snapshot as described in the main README, then restore this reference archive and run `build`:

```bash
python -m zipfile -e research/mts_gold/feature_artifacts/reference_sources_asof_2026-11-07.zip research/mts_gold
python research/mts_gold/code/features.py build
```
