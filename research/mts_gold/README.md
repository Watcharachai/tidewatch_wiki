# Direct MTS gold forecasting research — data and returns

This is a standalone Python research pipeline based on the Tidewatch wiki. It collects **actual MTS public chart OHLC** for **GLD965 (96.5%)** and **GLD9999 (99.99%, confirmed by the user)**. Both source symbols quote **THB**. It produces **15m, 30m, 60m, 1d, and 7d** candles and close returns at lags **1, 3, 7, 14, 30**. Model training is a later stage. The updated [forecast architecture](analysis/docs/Gold_Price_Predictive_Model_Architecture.md) is available as an editable Markdown source and a [DOCX](analysis/docs/Gold_Price_Predictive_Model_Architecture.docx). To regenerate the DOCX after editing the source, install `python-docx>=1.2,<2` and run `python research/mts_gold/render_architecture.py`.

The [quantitative feature collector](analysis/docs/feature_sources.md) adds 1/5/30 lags for both MTS gold series and available gold, cross-asset, macro and index references. It lists the historical futures, SET, silver and Singapore exports still needed from an approved source.

Run from the repository root, with Python 3.10+:

```bash
python -m venv .venv
.venv/bin/pip install -r research/mts_gold/requirements.txt
.venv/bin/python research/mts_gold/code/pipeline.py run --start 2025-01-01 --end 2027-01-01
```

`--end` is exclusive, so the defaults request all of 2025 and 2026. Naive dates use **Asia/Bangkok**. The pipeline clamps collection to the current time and includes only completed candles. Because this work began on 7 November 2026, 2026 is year-to-date; later 2026 observations can be collected by rerunning. No future data are invented.

```bash
# Explicit reproducible analysis cutoff; cannot exceed the actual current time.
python research/mts_gold/code/pipeline.py run --as-of 2026-11-07T00:00:00Z
# Resume collection after interruption; successful requests are cached.
python research/mts_gold/code/pipeline.py fetch
# Recompute all derived candles and analysis without network access.
python research/mts_gold/code/pipeline.py analyze
# Explicitly reload cached responses, for example to inspect source revisions.
python research/mts_gold/code/pipeline.py run --refresh
# Validation uses unittest and does not contact MTS.
python -m unittest discover -s research/mts_gold -v
```

The data client uses Python's standard-library HTTP client, inherited proxy/CA configuration and TLS verification. Runtime dependencies are pandas, NumPy and Matplotlib. `--output` and `--reports` select target artifact directories. The default `run` command also fetches and builds reference features after the MTS target analysis; it requires the default `--output` path. `--no-features` skips that stage and permits a custom output path. `fetch` collects MTS target data only, and `analyze` rebuilds the target return report offline. Run `python research/mts_gold/code/features.py build` for an offline feature rebuild. `--no-plots` skips Matplotlib rendering.

## Source and collection

The official [MTS home page](https://www.mtsgold.co.th/) embeds the [MTS chart](https://tradingview.mtsgold.co.th/mgb/chart/). The chart's published JavaScript identifies `/mgb` as its UDF datafeed and lists `GLD965`, `GLD9999`, `XAUUSD`, and `GLDGTA`. This pipeline uses only the first two symbols.

```text
https://tradingview.mtsgold.co.th/mgb/config
https://tradingview.mtsgold.co.th/mgb/symbols?symbol=GLD965
https://tradingview.mtsgold.co.th/mgb/symbols?symbol=GLD9999
https://tradingview.mtsgold.co.th/mgb/history?symbol=GLD965&resolution=15&from=1735776000&to=1735862399
```

Live validation found that **`15` and `1D` work**. The config advertises `1H`, but `1H` returned `no_data` for a range in which `60` returned prices; `1W` also returned `no_data` despite available daily history. Consequently, the implementation fetches native **15-minute and daily** candles and derives the other timeframes. It does not assume the advertised resolution aliases work. This is the public chart backend, with no documented stability or completeness guarantee.

Requests are sequential, separated by a configurable pause, bounded to seven-day intraday or 365-day daily windows, and retried for transient network errors/429/5xx responses. A full 1,000-bar page triggers recursive window splitting. `no_data` windows are retained in the audit trail, and out-of-window fallback observations are excluded. Each raw response is saved with URL, retrieval timestamp and original-body SHA-256. Only completed request intervals are cached, so the last in-progress candle is not frozen on a later rerun. Partial backfills resume from this cache; the final native CSV and manifest are written after collection succeeds. Conflicting duplicate timestamps, invalid OHLC, nonfinite prices and malformed responses fail explicitly.

## Candle and return definitions

- **15m:** source OHLC; **30m/60m:** wall-clock aligned OHLC from exactly 2/4 native 15m candles. Incomplete buckets are counted and dropped.
- **1d:** native daily MTS OHLC. UTC-midnight timestamps correspond to 07:00 Bangkok. Native daily bars need not equal a daily resample of the intraday series.
- **7d:** Monday-to-Monday calendar weeks from native daily OHLC, anchored to Monday 07:00 Bangkok. This is not a rolling seven-session horizon. First truncated and last unfinished weeks are excluded. Holidays need not supply five observations; observed daily count is retained.
- No forward/backward filling, invented volume, synthetic proxy substitution, or deletion based on an unverified historical market calendar. Source metadata says `0700-0300:34567`, but observed prices can extend outside those advertised hours, so source hours are not treated as a reliable filtering rule.
- `timestamp` is the source/aggregate bar start in UTC; `available_at` is the nominal completed-bar boundary. It prevents use of an unfinished candle, but does not establish the original publication time of historical data. Daily availability is conservatively the following UTC midnight. `source_count` is constituent source-bar count, not volume.

For **each symbol and timeframe**, the outputs contain:

```text
return_k     = close[t] / close[t-k] - 1
log_return_k = ln(close[t] / close[t-k])
k            = 1, 3, 7, 14, 30 observed bars
```

For example, `return_3` on `15m` spans 45 minutes in an uninterrupted session; on `1d`, it spans three observed daily candles. Intraday lags can cross weekends or closures, so each lag also has `elapsed_minutes_k`. Leading values without sufficient history remain missing; there is no pre-2025 warm-up. Returns are fractions in the row-level dataset and percentages in summary columns named `*_pct`. Per-year summaries assign a return to the current bar's Bangkok year, so early-2026 lags can reference 2025 prices.

## Outputs

| Path | Contents |
|---|---|
| `data/raw/*.json` | Cached raw UDF response envelopes |
| `data/source_metadata.json` | Original config and symbol descriptions |
| `data/manifest.json` | Request window, cutoff, raw-response hashes, retrieval times and native-CSV hash |
| `data/native_bars.csv` | Native 15m/daily OHLC, provenance and completion boundaries |
| `data/bars.csv` | Both gold series across all five requested timeframes |
| `data/returns.csv.gz` | All candles plus all simple/log returns and actual elapsed minutes |
| `analysis/reports/return_summary.csv` | N, mean, median, sample std, quantiles, extrema, skew, excess kurtosis, positive/zero fractions, elapsed times; by year and pooled |
| `analysis/reports/coverage.csv` | First/last observation, counts, observed gaps, flat-price fraction and discarded intraday buckets |
| `analysis/reports/daily_alignment_gaps.csv` | Daily dates observed for only one of the two source series |
| `analysis/reports/analysis.md` | Findings, definitions, limitations and charts |

`data/` is ignored by Git to keep generated working files separate from wiki source control. The complete collected dataset and raw-response cache are saved in the versioned [7 November 2026 snapshot](snapshots/mts_gold_2025_2026_asof_2026-11-07.zip), with its SHA-256 and collection metadata in [snapshot.json](snapshots/snapshot.json). Restore it from the repository root before running an offline analysis:

```bash
python -m zipfile -e research/mts_gold/snapshots/mts_gold_2025_2026_asof_2026-11-07.zip research/mts_gold
python research/mts_gold/code/pipeline.py analyze
```

Generated reports are reviewable in `analysis/reports/`. Bars missing from an open session cannot be distinguished from closures without a verified historical calendar; coverage measures **observed gaps**, not a promised missing-bar percentage. Raw UDF data expose OHLC only: bid/ask, quote-side semantics and weight basis are not specified, and returns exclude spreads and fees.

## Tidewatch integration and next model stage

The [instrument master](../../wiki/instrument-master.md) defines `GOLD965THB@mts` as a synthetic XAU × USDTHB conversion plus premium, and `GOLD9999USD@mts` as an XAU/USD synthetic. The [gold-feed note](../../wiki/gold-feed-xaut-proxy.md) documents their Binance TH proxy inputs. **The direct MTS GLD9999 series is THB, not the existing USD synthetic.** Research symbols remain separate; this change makes no production database updates. The [time-series note](../../wiki/market-timeseries.md) specifies 180-day raw intraday retention; retain this research archive independently to support the requested two-year study.

The repository contains documentation rather than the production collector source. Implementation therefore lives under `research/`. Its `CLAUDE.md` refers to `.claude/skills/wiki-llm/SKILL.md`, which is absent from this checkout. Existing wiki and immutable `raw/` pages are left untouched; this research README/report documents the new implementation.

Before forecasting, choose whether the five requested timeframes are **sampling intervals** (implemented here) or **elapsed future prediction horizons**. A week of observed candles and seven calendar days differ. Use 2025 for chronological training and available 2026 for evaluation; fit transformations only on training observations, purge overlapping forward labels across splits, and compare to a no-change price baseline. These descriptive overlapping returns do not establish forecast skill.
