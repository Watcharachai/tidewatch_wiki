#!/usr/bin/env python3
"""Direct MTS Gold history and descriptive close-to-close return research."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import random
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

BASE_URL = "https://tradingview.mtsgold.co.th/mgb"
SYMBOLS = {"GLD965": "96.5", "GLD9999": "99.99"}
LAGS = (1, 3, 7, 14, 30)
TIMEFRAMES = ("15m", "30m", "60m", "1d", "7d")
OHLC = ("open", "high", "low", "close")
LOG = logging.getLogger("mts_gold")


def utc(value: str | pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("Asia/Bangkok").tz_convert("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


class MTSClient:
    """Polite, sequential UDF client with auditable, resumable response caching."""

    def __init__(self, cache: Path, pause: float = 0.15, refresh: bool = False):
        self.cache, self.pause, self.refresh = cache, pause, refresh
        self.audit: list[dict] = []

    def get(self, endpoint: str, params: dict | None = None, live: bool = False) -> dict:
        query = urlencode(params or {})
        url = f"{BASE_URL}/{endpoint}" + (f"?{query}" if query else "")
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / f"{key}.json"
        cached = path.exists() and not (live or self.refresh)
        if cached:
            envelope = json.loads(path.read_text())
            if envelope["url"] != url:
                raise ValueError("Cache URL mismatch")
        else:
            for attempt in range(5):
                try:
                    request = Request(url, headers={"User-Agent": "Tidewatch-MTS-Research/1.0", "Accept": "application/json"})
                    with urlopen(request, timeout=45) as response:
                        raw = response.read()
                    payload = json.loads(raw)
                    if not isinstance(payload, dict):
                        raise ValueError(f"Expected a JSON object from {url}")
                    envelope = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(),
                                "response_sha256": hashlib.sha256(raw).hexdigest(), "payload": payload}
                    write_json(path, envelope)
                    time.sleep(self.pause)
                    break
                except (HTTPError, URLError, TimeoutError) as error:
                    if isinstance(error, HTTPError) and error.code not in (429, 500, 502, 503, 504):
                        raise
                    if attempt == 4:
                        raise
                    retry_after = error.headers.get("Retry-After", "") if isinstance(error, HTTPError) else ""
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        try:
                            delay = (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds()
                        except (ValueError, TypeError, OverflowError):
                            delay = 2 ** attempt + random.random()
                    if not np.isfinite(delay):
                        delay = 2 ** attempt + random.random()
                    LOG.warning("Retry %s after %.1fs: %s", url, max(0, delay), error)
                    time.sleep(max(0, delay))
        self.audit.append({"url": url, "cache_file": str(path.resolve()), "cache_hit": cached,
                           "fetched_at": envelope["fetched_at"], "response_sha256": envelope["response_sha256"]})
        return envelope["payload"]

    def history(self, symbol: str, resolution: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        # Seven-day intraday windows contain at most 672 fifteen-minute bars.
        # The chart advertises maxResponseLength=1000; split any full page defensively.
        payload = self.get("history", {"symbol": symbol, "resolution": resolution,
                                      "from": int(start.timestamp()), "to": int(end.timestamp()) - 1})
        if len(payload.get("t", [])) >= 1000:
            midpoint = start + (end - start) // 2
            midpoint = midpoint.floor("s")
            if midpoint <= start or midpoint >= end:
                raise ValueError("History pagination made no progress")
            left = self.history(symbol, resolution, start, midpoint)
            right = self.history(symbol, resolution, midpoint, end)
            if left.empty:
                return right
            if right.empty:
                return left
            return pd.concat([left, right], ignore_index=True)
        return parse_history(payload, start, end)


def parse_history(payload: dict, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if payload.get("s") == "no_data":
        return pd.DataFrame(columns=["timestamp", *OHLC])
    if payload.get("s") != "ok":
        raise ValueError(f"MTS history error: {payload}")
    fields = ("t", "o", "h", "l", "c")
    if any(not isinstance(payload.get(k), list) for k in fields):
        raise ValueError("Missing UDF OHLC arrays")
    if len({len(payload[k]) for k in fields}) != 1:
        raise ValueError("Unequal UDF array lengths")
    frame = pd.DataFrame(dict(zip(["timestamp", *OHLC], [payload[k] for k in fields])))
    seconds = pd.to_numeric(frame.timestamp, errors="raise")
    if not np.isfinite(seconds).all() or (seconds % 1 != 0).any():
        raise ValueError("Invalid Unix-second timestamp")
    frame["timestamp"] = pd.to_datetime(seconds, unit="s", utc=True)
    frame[list(OHLC)] = frame[list(OHLC)].apply(pd.to_numeric, errors="raise")
    values = frame[list(OHLC)]
    invalid = (~np.isfinite(values).all(axis=1) | values.le(0).any(axis=1)
               | frame.low.gt(frame[["open", "close"]].min(axis=1))
               | frame.high.lt(frame[["open", "close"]].max(axis=1)) | frame.low.gt(frame.high))
    if invalid.any():
        raise ValueError(f"Invalid OHLC values: {int(invalid.sum())} bars")
    # UDF can return a preceding observation for an empty range. Never import it.
    return frame.loc[frame.timestamp.ge(start) & frame.timestamp.lt(end)].copy()


def clean_bars(frames: list[pd.DataFrame], duration: pd.Timedelta, as_of: pd.Timestamp) -> pd.DataFrame:
    nonempty = [f for f in frames if not f.empty]
    if not nonempty:
        return pd.DataFrame(columns=["timestamp", *OHLC, "available_at", "source_count"])
    frame = pd.concat(nonempty, ignore_index=True)
    duplicate = frame[frame.duplicated("timestamp", keep=False)]
    if not duplicate.empty and duplicate.groupby("timestamp")[list(OHLC)].nunique().gt(1).any().any():
        raise ValueError("Conflicting OHLC for the same timestamp")
    frame = frame.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    frame["available_at"] = frame.timestamp + duration
    frame["source_count"] = 1
    return frame.loc[frame.available_at.le(as_of)].reset_index(drop=True)


def fetch_dataset(client: MTSClient, start: pd.Timestamp, end: pd.Timestamp,
                  as_of: pd.Timestamp, output: Path) -> None:
    effective_end = min(end, as_of.floor("s"))
    if start >= effective_end:
        raise ValueError("The requested start must precede both end and as-of")
    output.mkdir(parents=True, exist_ok=True)
    metadata = {"source": BASE_URL, "config": client.get("config"), "symbols": {}}
    frames = []
    for symbol, purity in SYMBOLS.items():
        info = client.get("symbols", {"symbol": symbol})
        if info.get("currency_code") != "THB" or info.get("name") != symbol:
            raise ValueError(f"Unexpected source symbol/currency: {info}")
        metadata["symbols"][symbol] = info
        for resolution, timeframe, duration in [("15", "15m", pd.Timedelta(minutes=15)),
                                                ("1D", "1d", pd.Timedelta(days=1))]:
            # Query only closed intervals so a cached completed window cannot
            # preserve the in-progress last candle from an earlier run.
            frequency = "15min" if timeframe == "15m" else "1D"
            parts, cursor = [], start.ceil(frequency)
            horizon = min(end.ceil(frequency), as_of.floor(frequency))
            step = pd.Timedelta(days=7 if timeframe == "15m" else 365)
            while cursor < horizon:
                stop = min(cursor + step, horizon)
                parts.append(client.history(symbol, resolution, cursor, stop))
                LOG.info("Fetched %s %s %s to %s (%s bars)", symbol, timeframe, cursor.date(), stop.date(), len(parts[-1]))
                cursor = stop
            bars = clean_bars(parts, duration, as_of)
            bars = bars.loc[bars.timestamp.lt(end)].copy()
            # Native daily UDF timestamps are UTC midnight (07:00 Bangkok).
            alignment = 900 if timeframe == "15m" else 86400
            if not bars.empty and (bars.timestamp.astype("int64") // 10**9 % alignment != 0).any():
                raise ValueError(f"Unexpected timestamp alignment for {symbol}/{timeframe}")
            bars["symbol"], bars["purity_pct"], bars["currency"] = symbol, purity, "THB"
            bars["timeframe"], bars["source"] = timeframe, "mts-public-chart"
            frames.append(bars)
    native = pd.concat(frames, ignore_index=True)
    native.to_csv(output / "native_bars.csv", index=False)
    write_json(output / "source_metadata.json", metadata)
    write_json(output / "manifest.json", {
        "requested_start": start.isoformat(), "requested_end_exclusive": end.isoformat(),
        "as_of": as_of.isoformat(), "effective_end_exclusive": effective_end.isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(), "native_rows": len(native),
        "pipeline_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "native_csv_sha256": hashlib.sha256((output / "native_bars.csv").read_bytes()).hexdigest(),
        "requests": client.audit,
    })


def aggregate(frame: pd.DataFrame, rule: str, minutes: int | None = None) -> tuple[pd.DataFrame, int]:
    if frame.empty:
        return frame.copy(), 0
    grouped = frame.set_index("timestamp").resample(rule, closed="left", label="left", origin="start_day")
    bars = grouped.agg({"open": "first", "high": "max", "low": "min", "close": "last", "source_count": "sum"})
    bars = bars.dropna(subset=list(OHLC))
    discarded = 0
    if minutes:
        # Require every constituent 15m bar; no forward-filled or partial intraday OHLC.
        full = bars.source_count.eq(minutes // 15)
        discarded = int((~full).sum())
        bars = bars.loc[full].copy()
        duration = pd.Timedelta(minutes=minutes)
    else:
        duration = pd.Timedelta(days=7)
    bars = bars.reset_index()
    bars["available_at"] = bars.timestamp + duration
    return bars, discarded


def build_timeframes(native: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp,
                     as_of: pd.Timestamp) -> tuple[pd.DataFrame, list[dict]]:
    output, quality = [], []
    for symbol, purity in SYMBOLS.items():
        intraday = native.loc[(native.symbol == symbol) & (native.timeframe == "15m")].copy()
        daily = native.loc[(native.symbol == symbol) & (native.timeframe == "1d")].copy()
        candidates = {"15m": (intraday, 0), "1d": (daily, 0),
                      "30m": aggregate(intraday, "30min", 30), "60m": aggregate(intraday, "60min", 60),
                      "7d": aggregate(daily, "W-MON")}
        for timeframe in TIMEFRAMES:
            bars, dropped = candidates[timeframe]
            bars = bars.loc[bars.timestamp.ge(start) & bars.timestamp.lt(end) & bars.available_at.le(as_of)].copy()
            bars = bars.sort_values("timestamp")
            bars["symbol"], bars["purity_pct"], bars["currency"] = symbol, purity, "THB"
            bars["timeframe"], bars["source"] = timeframe, "mts-public-chart"
            gap = pd.to_datetime(bars.timestamp, utc=True).diff().dt.total_seconds() / 60
            base_minutes = {"15m": 15, "30m": 30, "60m": 60, "1d": 1440, "7d": 10080}[timeframe]
            quality.append({"symbol": symbol, "timeframe": timeframe, "bars": len(bars),
                            "first": bars.timestamp.min().isoformat() if len(bars) else None,
                            "last": bars.timestamp.max().isoformat() if len(bars) else None,
                            "discarded_partial_intraday_buckets": dropped,
                            "observed_gaps_over_nominal_step": int(gap.gt(base_minutes).sum()),
                            "max_observed_gap_minutes": float(gap.max()) if gap.notna().any() else None,
                            "zero_close_change_fraction": float(bars.close.diff().eq(0).iloc[1:].mean()) if len(bars) > 1 else None})
            output.append(bars)
    return pd.concat(output, ignore_index=True), quality


def add_returns(bars: pd.DataFrame) -> pd.DataFrame:
    results = []
    for _, frame in bars.groupby(["symbol", "timeframe"], sort=False):
        frame = frame.sort_values("timestamp").copy()
        for lag in LAGS:
            prior = frame.close.shift(lag)
            frame[f"return_{lag}"] = frame.close / prior - 1
            frame[f"log_return_{lag}"] = np.log(frame.close / prior)
            frame[f"elapsed_minutes_{lag}"] = (frame.timestamp - frame.timestamp.shift(lag)).dt.total_seconds() / 60
        results.append(frame)
    if not results:
        raise ValueError("No closed bars available for analysis")
    return pd.concat(results, ignore_index=True)


def summarize(returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    with_year = returns.assign(year=returns.timestamp.dt.tz_convert("Asia/Bangkok").dt.year.astype(str))
    all_years = with_year.assign(year="all")
    for (symbol, timeframe, year), frame in pd.concat([with_year, all_years]).groupby(["symbol", "timeframe", "year"]):
        for lag in LAGS:
            values = frame[f"return_{lag}"].dropna()
            elapsed = frame.loc[values.index, f"elapsed_minutes_{lag}"]
            row = {"symbol": symbol, "timeframe": timeframe, "year": year, "lag_bars": lag, "n": len(values)}
            stats = {"mean_pct": values.mean(), "median_pct": values.median(), "std_pct": values.std(ddof=1),
                     "min_pct": values.min(), "q01_pct": values.quantile(.01), "q05_pct": values.quantile(.05),
                     "q95_pct": values.quantile(.95), "q99_pct": values.quantile(.99), "max_pct": values.max()}
            row.update({k: v * 100 for k, v in stats.items()})
            row.update({"positive_fraction": values.gt(0).mean() if len(values) else np.nan,
                        "zero_fraction": values.eq(0).mean() if len(values) else np.nan,
                        "skew": values.skew(), "excess_kurtosis": values.kurt(),
                        "median_elapsed_minutes": elapsed.median(), "max_elapsed_minutes": elapsed.max()})
            rows.append(row)
    return pd.DataFrame(rows)


def plot_results(returns: pd.DataFrame, summary: pd.DataFrame, reports: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tidewatch-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    colors = {"GLD965": "#96731f", "GLD9999": "#16697a"}
    for symbol in SYMBOLS:
        daily = returns.loc[(returns.symbol == symbol) & (returns.timeframe == "1d")]
        if daily.empty:
            continue
        axes[0, 0].plot(daily.timestamp, daily.close, label=symbol, color=colors[symbol])
        axes[0, 1].plot(daily.timestamp, 100 * (daily.close / daily.close.iloc[0] - 1), label=symbol, color=colors[symbol])
        axes[1, 0].hist(100 * daily.return_1.dropna(), bins=70, alpha=.5, label=symbol, color=colors[symbol])
        vol = daily.return_1.rolling(30, min_periods=30).std() * 100
        axes[1, 1].plot(daily.timestamp, vol, label=symbol, color=colors[symbol])
    titles = ["Direct MTS daily close (THB; source price units)", "Change from first observed daily close (%)",
              "One observed-day close return (%)", "Rolling 30-observation daily return std (%)"]
    for ax, title in zip(axes.flat, titles):
        ax.set_title(title)
        ax.grid(alpha=.2)
        ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(reports / "prices_and_daily_returns.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, symbol in zip(axes, SYMBOLS):
        matrix = summary.loc[(summary.symbol == symbol) & (summary.year == "all")].pivot(index="timeframe", columns="lag_bars", values="std_pct").reindex(TIMEFRAMES)
        im = ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
        ax.set_xticks(range(len(LAGS)), LAGS)
        ax.set_yticks(range(len(TIMEFRAMES)), TIMEFRAMES)
        ax.set_xlabel("Lag in observed bars")
        ax.set_title(f"{symbol}: return std (%)")
        for i in range(len(TIMEFRAMES)):
            for j in range(len(LAGS)):
                ax.text(j, i, f"{matrix.iloc[i, j]:.2f}", ha="center", va="center", color="black", fontsize=9)
        fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(reports / "return_volatility.png", dpi=160)
    plt.close(fig)


def make_report(returns: pd.DataFrame, summary: pd.DataFrame, quality: list[dict], manifest: dict, reports: Path) -> None:
    daily_panel = returns.loc[returns.timeframe == "1d"].pivot(index="timestamp", columns="symbol", values="close").reindex(columns=list(SYMBOLS))
    matched_returns = daily_panel.dropna().pct_change(fill_method=None).dropna()
    correlation = matched_returns.corr().iloc[0, 1] if len(matched_returns) > 1 else np.nan
    mismatches = daily_panel.loc[daily_panel.isna().any(axis=1)]
    mismatches.to_csv(reports / "daily_alignment_gaps.csv")
    lines = ["# MTS Gold: historical data and return analysis", "", f"Analysis as of **{manifest['as_of']}**.", "",
             f"Requested window: {manifest['requested_start']} to {manifest['requested_end_exclusive']} (exclusive).",
             f"Effective collection cutoff: {manifest['effective_end_exclusive']}. No future observations are included.", "",
             "Source: [MTS public chart](https://tradingview.mtsgold.co.th/mgb/chart/), using its `/mgb/history` UDF endpoint.",
             "GLD965 is 96.5%; GLD9999 is 99.99% (confirmed by the user). Both source symbols quote THB.",
             "The endpoint does not publish the weight basis or whether OHLC represents bid, ask, or mid. These are chart-price returns, not executable trade P&L.", "",
             "## Coverage", "", "| Symbol | Timeframe | Closed bars | First timestamp (UTC) | Last timestamp (UTC) | Partial intraday buckets dropped |",
             "|---|---|---:|---|---|---:|"]
    for item in quality:
        lines.append(f"| {item['symbol']} | {item['timeframe']} | {item['bars']:,} | {item['first']} | {item['last']} | {item['discarded_partial_intraday_buckets']} |")
    lines += ["", "## Returns", "", "`R(t,k) = close(t) / close(t-k) - 1`; `log_R(t,k) = ln(close(t) / close(t-k))`.",
              "Lags 1, 3, 7, 14, 30 count observed bars separately in each timeframe. Intraday lags may cross overnight/weekend gaps; elapsed minutes are exported for every lag.",
              "Daily lags count observed daily candles. Seven-day bars are Monday-to-Monday calendar weeks, not rolling seven trading sessions.",
              "Returns in the data are decimal fractions; the table and summary columns ending `_pct` are percentages.", "",
              "| Symbol | Timeframe | Lag (bars) | N | Mean (%) | Std (%) | 5th pct (%) | 95th pct (%) | Median elapsed (minutes) |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summary.loc[summary.year == "all"].itertuples():
        lines.append(f"| {row.symbol} | {row.timeframe} | {row.lag_bars} | {row.n:,} | {row.mean_pct:.4f} | {row.std_pct:.4f} | {row.q05_pct:.4f} | {row.q95_pct:.4f} | {row.median_elapsed_minutes:.0f} |")
    lines += ["", "## Findings", ""]
    for symbol in SYMBOLS:
        selected = summary.loc[(summary.symbol == symbol) & (summary.timeframe == "1d") & (summary.lag_bars == 1)].set_index("year")
        if "2025" in selected.index and "2026" in selected.index:
            early, later = selected.loc["2025"], selected.loc["2026"]
            lines.append(f"- {symbol}: one-observation daily return standard deviation rose from **{early.std_pct:.3f}% in 2025** to **{later.std_pct:.3f}% in available 2026**, a {later.std_pct / early.std_pct:.2f}x change. The model should be evaluated across this volatility change.")
        pooled = selected.loc["all"]
        lines.append(f"- {symbol}: daily returns ranged from **{pooled.min_pct:.2f}%** to **{pooled.max_pct:.2f}%**; sample excess kurtosis was **{pooled.excess_kurtosis:.2f}**. Large tails in this sample make a normal-error assumption questionable.")
    lines += [f"- On {len(matched_returns):,} shared consecutive daily observation pairs, the two series' return correlation was **{correlation:.5f}**. Returns are recomputed after matching close dates so each comparison spans the same interval; the two gold series carry strongly overlapping daily price information.",
              f"- There are **{len(mismatches)} daily dates** on which only one gold series has a source candle; see `daily_alignment_gaps.csv`. These dates should be checked before cross-series model features are joined."]
    weekly = summary.loc[(summary.timeframe == "7d") & (summary.lag_bars == 30) & (summary.year == "all")]
    lines.append(f"- The 30-week return has only {', '.join(str(int(n)) for n in weekly.n)} observations for the two series, and these returns overlap heavily. Its descriptive mean should not be interpreted as a stable expected return.")
    lines += ["", "## Observed period movement", ""]
    for symbol in SYMBOLS:
        daily = returns.loc[(returns.symbol == symbol) & (returns.timeframe == "1d")]
        for year, frame in daily.groupby(daily.timestamp.dt.tz_convert("Asia/Bangkok").dt.year):
            movement = 100 * (frame.close.iloc[-1] / frame.close.iloc[0] - 1)
            lines.append(f"- {symbol}, {year}: {len(frame):,} daily candles; first-to-last observed close change **{movement:.2f}%**. This is within-year observed movement, not a full calendar-year return.")
    lines += ["", "## Method and limitations", "",
              "- Native 15-minute and daily OHLC come directly from MTS. The 30/60-minute bars require all constituent 15-minute candles; incomplete buckets are dropped. No prices or closed-market periods are filled.",
              "- Daily timestamps are UTC midnight, or 07:00 Bangkok. Daily availability is conservatively the next UTC midnight. Weekly bars aggregate native daily OHLC, anchored to Monday 07:00 Bangkok, and are available only after the full week ends. The first truncated week is excluded.",
              "- `available_at` is a nominal candle-completion boundary, not a measured historical publication timestamp. A historical download may contain source revisions; it is not a point-in-time vintage archive.",
              "- Source session metadata is preserved but not used to erase observations: observed bars can extend beyond its advertised hours. Gaps combine closures, holidays and possible outages; without a verified historical calendar they are not classified as missing trading bars.",
              "- Leading lag values have no pre-2025 warm-up and remain missing. A 30-bar weekly return needs 30 earlier weeks. The current partial candle/week and the unelapsed remainder of 2026 are excluded.",
              "- Per-year summaries use the current bar's Bangkok year; early-2026 lagged returns can reference 2025 prices. Full-period results pool both years.",
              "- Multi-bar returns overlap. Their sample count is not an independent sample size; these descriptive statistics do not establish predictability or statistical significance. No square-root-time annualization is assumed.",
              "- Tidewatch's existing `GOLD965THB@mts` and `GOLD9999USD@mts` are synthetic proxies. These direct THB series are kept separately as GLD965/GLD9999, without replacing production IDs or claiming equivalence to the USD synthetic.",
              "- For the later forecast stage: use chronological 2025 training and 2026 evaluation, fit preprocessing only on training data, and purge overlapping forward labels at split boundaries. Compare against a no-change price baseline. Current work collects data and analyzes past returns; it does not train a model.", "",
              "## Artifacts", "", "- `return_summary.csv`: all lags, timeframes, and separate 2025/2026/full-period summaries.",
              "- `coverage.csv`: observed gaps, flat prices and discarded partial intraday buckets.",
              "- `daily_alignment_gaps.csv`: source daily dates present for only one gold series.",
              "- `../../data/bars.csv` and `../../data/returns.csv.gz`: normalized candles and every simple/log return, with elapsed minutes.",
              "- `../../data/manifest.json`, `source_metadata.json`, and `raw/`: exact requests, retrieval times, raw-response hashes and reusable cached responses.", "",
              "![Prices and daily return analysis](prices_and_daily_returns.png)", "", "![Return volatility by lag and timeframe](return_volatility.png)", ""]
    (reports / "analysis.md").write_text("\n".join(lines))


def analyze(output: Path, reports: Path, plots: bool = True) -> None:
    manifest = json.loads((output / "manifest.json").read_text())
    expected = manifest["native_csv_sha256"]
    if hashlib.sha256((output / "native_bars.csv").read_bytes()).hexdigest() != expected:
        raise ValueError("Native CSV differs from the collection manifest")
    native = pd.read_csv(output / "native_bars.csv", parse_dates=["timestamp", "available_at"])
    for column in ("timestamp", "available_at"):
        native[column] = pd.to_datetime(native[column], utc=True)
    bars, quality = build_timeframes(native, utc(manifest["requested_start"]), utc(manifest["requested_end_exclusive"]), utc(manifest["as_of"]))
    if bars.empty:
        raise ValueError("No closed bars available for analysis")
    returns = add_returns(bars)
    summary = summarize(returns)
    reports.mkdir(parents=True, exist_ok=True)
    bars.to_csv(output / "bars.csv", index=False)
    returns.to_csv(output / "returns.csv.gz", index=False, compression="gzip")
    summary.to_csv(reports / "return_summary.csv", index=False)
    pd.DataFrame(quality).to_csv(reports / "coverage.csv", index=False)
    if plots:
        plot_results(returns, summary, reports)
    make_report(returns, summary, quality, manifest, reports)
    LOG.info("Wrote %s bars, %s summary rows, report %s", len(bars), len(summary), reports / "analysis.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "analyze", "run"])
    parser.add_argument("--start", default="2025-01-01", help="Inclusive; naive dates use Asia/Bangkok")
    parser.add_argument("--end", default="2027-01-01", help="Exclusive; default covers 2025 and 2026")
    parser.add_argument("--as-of", help="UTC-aware cutoff; defaults to current UTC time")
    root = Path(__file__).resolve().parent.parent
    parser.add_argument("--output", type=Path, default=root / "data")
    parser.add_argument("--reports", type=Path, default=root / "analysis" / "reports")
    parser.add_argument("--no-features", action="store_true", help="Skip reference collection and feature building during run")
    parser.add_argument("--refresh", action="store_true", help="Refetch cached completed request windows")
    parser.add_argument("--pause", type=float, default=.15, help="Seconds between uncached requests")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    if args.pause < 0:
        parser.error("--pause must be nonnegative")
    if args.command == "run" and not args.no_features and args.output.resolve() != (root / "data").resolve():
        parser.error("integrated feature collection requires the default --output; use --no-features with a custom output")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if args.command in ("fetch", "run"):
        start, end = utc(args.start), utc(args.end)
        now = pd.Timestamp.now(tz="UTC")
        as_of = min(utc(args.as_of), now) if args.as_of else now
        client = MTSClient(args.output / "raw", pause=args.pause, refresh=args.refresh)
        fetch_dataset(client, start, end, as_of, args.output)
    if args.command in ("analyze", "run"):
        analyze(args.output, args.reports, plots=not args.no_plots)
    if args.command == "run" and not args.no_features:
        from features import fetch as fetch_features, build as build_features
        fetch_features(root, as_of)
        build_features(root)


if __name__ == "__main__":
    main()
