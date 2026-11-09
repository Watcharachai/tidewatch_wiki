#!/usr/bin/env python3
"""Collect point-in-time-conscious market references and build lag features."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import StringIO
import hashlib
import json
import logging
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from pipeline import MTSClient, clean_bars, utc, write_json

ROOT = Path(__file__).resolve().parent
LAGS = (1, 5, 30)
FREQS = {"15m": ("15min", 15), "30m": ("30min", 30), "60m": ("60min", 60),
         "1d": ("1D", 1440), "7d": ("W-MON", 10080)}
FRED = {
    "sp500": "SP500", "nasdaq": "NASDAQCOM", "djia": "DJIA",
    "us_yield_3m": "DGS3MO", "us_yield_2y": "DGS2", "us_yield_10y": "DGS10",
    "us_yield_30y": "DGS30", "vix": "VIXCLS", "usdthb": "DEXTHUS",
    "wti_oil": "DCOILWTICO",
}
EXTERNAL = {
    "us_gold_future": "CME/COMEX gold futures: continuous-contract roll, exchange and volume definition required",
    "sg_gold_reference": "Singapore venue gold spot/future: venue, contract, currency and license required",
    "silver_spot": "Silver spot: currency/weight basis and quote side required",
    "silver_future": "Silver futures: continuous-contract roll and exchange required",
    "set_index": "SET Thailand index: official/licensed historical export required",
}
LOG = logging.getLogger("mts_features")


class CachedHTTP:
    def __init__(self, cache: Path, pause: float = .2):
        self.cache, self.pause = cache, pause
        self.audit: list[dict] = []

    def get(self, url: str) -> bytes:
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / f"{key}.bin"
        cached = path.exists()
        if cached:
            raw = path.read_bytes()
        else:
            for attempt in range(4):
                try:
                    req = Request(url, headers={"User-Agent": "Tidewatch-MTS-Research/1.0", "Accept": "application/json,text/csv,*/*"})
                    with urlopen(req, timeout=45) as response:
                        raw = response.read()
                    if not raw:
                        raise ValueError(f"Empty response: {url}")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)
                    time.sleep(self.pause)
                    break
                except (HTTPError, URLError, TimeoutError):
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)
        self.audit.append({"url": url, "cache_file": str(path), "cache_hit": cached,
                           "sha256": hashlib.sha256(raw).hexdigest()})
        return raw


def to_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="raise")


def validate(frame: pd.DataFrame, name: str, requires_volume: bool = False) -> pd.DataFrame:
    required = {"timestamp", "available_at", "close"} | ({"volume"} if requires_volume else set())
    if not required.issubset(frame):
        raise ValueError(f"{name}: missing columns {sorted(required - set(frame))}")
    frame = frame.copy()
    frame["timestamp"], frame["available_at"] = to_utc(frame.timestamp), to_utc(frame.available_at)
    for column in ("close", "volume"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame.timestamp.duplicated().any() or frame.timestamp.isna().any() or frame.available_at.isna().any():
        raise ValueError(f"{name}: duplicate or null timestamps")
    if not np.isfinite(frame.close).all() or frame.close.le(0).any():
        raise ValueError(f"{name}: invalid close")
    if "volume" in frame and frame.volume.notna().any():
        if frame.volume.dropna().lt(0).any() or not np.isfinite(frame.volume.dropna()).all():
            raise ValueError(f"{name}: invalid volume")
    if frame.available_at.lt(frame.timestamp).any():
        raise ValueError(f"{name}: availability before observation")
    return frame.sort_values("available_at").reset_index(drop=True)


def fetch_fred(http: CachedHTTP, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, pd.DataFrame]:
    result = {}
    for name, series_id in FRED.items():
        query = urlencode({"id": series_id, "cosd": start.date().isoformat(), "coed": end.date().isoformat()})
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?{query}"
        raw = http.get(url)
        if raw[:2] == b"PK":
            raise ValueError(f"{series_id}: expected one-series CSV; received ZIP")
        table = pd.read_csv(StringIO(raw.decode("utf-8-sig")))
        if list(table.columns) != ["observation_date", series_id]:
            raise ValueError(f"{series_id}: unexpected FRED columns {list(table.columns)}")
        table = table.dropna(subset=[series_id]).copy()
        if table.empty:
            raise ValueError(f"{series_id}: no observations")
        table["timestamp"] = pd.to_datetime(table.observation_date, utc=True)
        # Conservative research availability bound: two UTC days after the
        # observation date. This is an assumption, not a source release time.
        table["available_at"] = table.timestamp + pd.Timedelta(days=2)
        table = table.rename(columns={series_id: "close"})
        result[name] = validate(table[["timestamp", "available_at", "close"]], name)
        LOG.info("FRED %s: %s rows", series_id, len(result[name]))
    return result


def fetch_mts_xau(start: pd.Timestamp, end: pd.Timestamp, cache: Path) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    client = MTSClient(cache)
    info = client.get("symbols", {"symbol": "XAUUSD"})
    if info.get("currency_code") != "USD" or info.get("has_no_volume") != 1:
        raise ValueError("MTS XAUUSD metadata changed; inspect source before using it")
    output = {}
    for resolution, timeframe, duration, step in [("15", "15m", pd.Timedelta(minutes=15), pd.Timedelta(days=7)),
                                                   ("1D", "1d", pd.Timedelta(days=1), pd.Timedelta(days=365))]:
        freq = "15min" if timeframe == "15m" else "1D"
        cursor, horizon, chunks = start.ceil(freq), end.floor(freq), []
        while cursor < horizon:
            stop = min(cursor + step, horizon)
            chunks.append(client.history("XAUUSD", resolution, cursor, stop))
            cursor = stop
        bars = clean_bars(chunks, duration, end)
        output[timeframe] = validate(bars[["timestamp", "available_at", "close"]], "mts_xauusd")
        LOG.info("MTS XAUUSD %s: %s rows", timeframe, len(bars))
    return output, client.audit


def fetch_binance(http: CachedHTTP, symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    cursor, stop_all = start.floor("15min"), end.floor("15min")
    pieces = []
    while cursor < stop_all:
        stop = min(cursor + pd.Timedelta(days=7), stop_all)
        query = urlencode({"symbol": symbol, "interval": "15m", "startTime": int(cursor.timestamp() * 1000),
                           "endTime": int(stop.timestamp() * 1000) - 1, "limit": 1000})
        raw = http.get(f"https://api.binance.th/api/v1/klines?{query}")
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError(f"{symbol}: Binance error {payload}")
        if len(payload) >= 1000:
            raise ValueError(f"{symbol}: possible truncated Binance window")
        if payload:
            part = pd.DataFrame(payload)
            pieces.append(pd.DataFrame({"timestamp": pd.to_datetime(part[0], unit="ms", utc=True),
                                        "open": part[1], "high": part[2], "low": part[3], "close": part[4],
                                        "volume": part[5]}))
        cursor = stop
    if not pieces:
        raise ValueError(f"{symbol}: no Binance history")
    bars = pd.concat(pieces, ignore_index=True)
    bars["timestamp"] = to_utc(bars.timestamp)
    for col in ("open", "high", "low", "close", "volume"):
        bars[col] = pd.to_numeric(bars[col], errors="raise")
    bars = bars.drop_duplicates("timestamp").sort_values("timestamp")
    bars["available_at"] = bars.timestamp + pd.Timedelta(minutes=15)
    bars = bars.loc[bars.available_at.le(end)].copy()
    if (bars.low.gt(bars[["open", "close"]].min(axis=1)) |
            bars.high.lt(bars[["open", "close"]].max(axis=1))).any():
        raise ValueError(f"{symbol}: invalid OHLC")
    LOG.info("Binance TH %s 15m: %s rows", symbol, len(bars))
    return validate(bars, symbol, requires_volume=True)


def aggregate_binance(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule, minutes = FREQS[timeframe]
    if timeframe == "15m":
        return frame.copy()
    source = frame.set_index("timestamp")
    bars = source.resample(rule, closed="left", label="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    count = source.close.resample(rule, closed="left", label="left").count()
    minimum = {"30m": 2, "60m": 4, "1d": 96, "7d": 7 * 96}[timeframe]
    bars = bars.loc[count.eq(minimum)].dropna(subset=["close"]).reset_index()
    bars["available_at"] = bars.timestamp + pd.Timedelta(minutes=minutes)
    return validate(bars, f"binance_{timeframe}", requires_volume=True)


def build_mts_xau_frames(native: dict[str, pd.DataFrame], end: pd.Timestamp) -> dict[str, pd.DataFrame]:
    result = {k: v.copy() for k, v in native.items()}
    intraday = native["15m"].copy()
    intraday["source_count"] = 1
    # OHLC is not needed for close-based lags; native 15m bars have all OHLC in
    # the original MTS response, but here the cached research projection is close.
    # For derived reference closes use the last constituent only when all exist.
    for timeframe, count in (("30m", 2), ("60m", 4)):
        rule = FREQS[timeframe][0]
        g = intraday.set_index("timestamp").resample(rule, closed="left", label="left")
        bars = g.close.agg(["last", "count"])
        bars = bars.loc[bars["count"].eq(count)].reset_index().rename(columns={"last": "close"})
        bars["available_at"] = bars.timestamp + pd.Timedelta(minutes=FREQS[timeframe][1])
        result[timeframe] = validate(bars[["timestamp", "available_at", "close"]], "mts_xauusd")
    g = native["1d"].set_index("timestamp").resample("W-MON", closed="left", label="left")
    weekly = g.close.last().dropna().reset_index()
    weekly["available_at"] = weekly.timestamp + pd.Timedelta(days=7)
    result["7d"] = validate(weekly.loc[weekly.available_at.le(end)], "mts_xauusd")
    return result


def read_external(folder: Path, end: pd.Timestamp) -> dict[tuple[str, str], pd.DataFrame]:
    result = {}
    for name in EXTERNAL:
        for timeframe in FREQS:
            path = folder / f"{name}_{timeframe}.csv"
            legacy = folder / f"{name}.csv"
            if timeframe == "1d" and legacy.exists():
                if path.exists():
                    raise ValueError(f"{name}: supply either the plain daily CSV or _1d.csv, not both")
                path = legacy
            if not path.exists():
                continue
            frame = validate(pd.read_csv(path), f"{name}_{timeframe}")
            result[(name, timeframe)] = frame.loc[frame.available_at.le(end)].copy()
    return result


def fetch(root: Path, as_of: pd.Timestamp) -> None:
    data = root / "feature_data"
    data.mkdir(parents=True, exist_ok=True)
    mts = pd.read_csv(root / "data" / "bars.csv", parse_dates=["timestamp", "available_at"])
    end = min(as_of, to_utc(mts.available_at).max())
    start = utc("2025-01-01")
    http = CachedHTTP(data / "raw" / "http")
    references: dict[str, dict[str, pd.DataFrame]] = {}
    refs, mts_audit = fetch_mts_xau(start, end, data / "raw" / "mts")
    references["mts_xauusd"] = build_mts_xau_frames(refs, end)
    for name, symbol in (("xautusdt", "XAUTUSDT"), ("btcusdt", "BTCUSDT")):
        base = fetch_binance(http, symbol, start, end)
        references[name] = {tf: aggregate_binance(base, tf) for tf in FREQS}
    for name, frame in fetch_fred(http, start, end).items():
        references[name] = {"1d": frame}
    for (name, timeframe), frame in read_external(root / "external", end).items():
        references.setdefault(name, {})[timeframe] = frame
    inventory = []
    for name, by_tf in references.items():
        for tf, frame in by_tf.items():
            if frame.empty:
                continue
            frame = frame.loc[frame.available_at.le(end)].copy()
            frame.to_csv(data / f"{name}_{tf}.csv", index=False)
            inventory.append({"name": name, "timeframe": tf, "rows": len(frame),
                              "first": frame.timestamp.min().isoformat(), "last": frame.timestamp.max().isoformat(),
                              "volume_rows": int(frame.volume.notna().sum()) if "volume" in frame else 0})
    write_json(data / "manifest.json", {"as_of": end.isoformat(), "created_at": datetime.now(timezone.utc).isoformat(),
              "target_mts_bars_sha256": hashlib.sha256((root / "data" / "bars.csv").read_bytes()).hexdigest(),
              "inventory": inventory, "mts_requests": mts_audit, "http_requests": http.audit,
              "pending_external": {k: v for k, v in EXTERNAL.items() if k not in references},
              "notes": ["MTS UDF has_no_volume=1 for GLD965, GLD9999 and XAUUSD; no MTS volume is invented.",
                        "FRED daily availability = observation date + 2 UTC days (conservative assumption, not verified release time).",
                        "Yahoo 429 and SET 403 in this environment; no fabricated futures/SET/silver values."]})
    LOG.info("Saved %s reference series/timeframe files", len(inventory))


def lagged(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    frame = frame.sort_values("timestamp").copy()
    out = frame[["available_at", "close"]].rename(columns={"close": f"{prefix}_close"})
    out[f"{prefix}_observed_at"] = frame.timestamp
    for lag in LAGS:
        out[f"{prefix}_close_lag{lag}"] = frame.close.shift(lag)
        out[f"{prefix}_return_lag{lag}"] = frame.close / frame.close.shift(lag) - 1
        out[f"{prefix}_elapsed_min_lag{lag}"] = (frame.timestamp - frame.timestamp.shift(lag)).dt.total_seconds() / 60
    if "volume" in frame:
        out[f"{prefix}_volume"] = frame.volume
        for lag in LAGS:
            out[f"{prefix}_volume_lag{lag}"] = frame.volume.shift(lag)
    return out.drop_duplicates("available_at").sort_values("available_at")


def asof_join(target: pd.DataFrame, source: pd.DataFrame, prefix: str, max_age: pd.Timedelta) -> pd.DataFrame:
    joined = pd.merge_asof(target.sort_values("available_at"), lagged(source, prefix),
                           on="available_at", direction="backward", allow_exact_matches=True)
    age = joined.available_at - joined[f"{prefix}_observed_at"]
    invalid = age.gt(max_age) | age.lt(pd.Timedelta(0))
    columns = [c for c in joined if c.startswith(prefix + "_")]
    joined.loc[invalid, columns] = np.nan
    joined[f"{prefix}_age_minutes"] = age.dt.total_seconds() / 60
    joined.loc[invalid, f"{prefix}_age_minutes"] = np.nan
    return joined


def build(root: Path) -> None:
    data = root / "feature_data"
    manifest = json.loads((data / "manifest.json").read_text())
    if hashlib.sha256((root / "data" / "bars.csv").read_bytes()).hexdigest() != manifest["target_mts_bars_sha256"]:
        raise ValueError("MTS source bars changed since reference collection; rerun fetch")
    target = pd.read_csv(root / "data" / "bars.csv", parse_dates=["timestamp", "available_at"])
    for c in ("timestamp", "available_at"):
        target[c] = to_utc(target[c])
    target = target.loc[target.available_at.le(utc(manifest["as_of"]))].copy()
    available = {}
    for item in manifest["inventory"]:
        frame = pd.read_csv(data / f"{item['name']}_{item['timeframe']}.csv", parse_dates=["timestamp", "available_at"])
        available[(item["name"], item["timeframe"])] = validate(frame, item["name"])
    coverage, files = [], []
    artifact = root / "feature_artifacts"
    artifact.mkdir(exist_ok=True)
    for tf, group in target.groupby("timeframe", sort=False):
        group = group.sort_values("available_at").copy()
        # Both direct MTS purities are present on every target row.
        for symbol, name in (("GLD965", "mts965"), ("GLD9999", "mts9999")):
            source = group.loc[group.symbol.eq(symbol), ["timestamp", "available_at", "close"]]
            group = asof_join(group, source, f"{name}_{tf}", pd.Timedelta(days=4 if tf in ("1d", "7d") else 1))
        for (name, source_tf), source in available.items():
            if source_tf != tf and source_tf != "1d":
                continue
            prefix = f"{name}_{source_tf}"
            max_age = pd.Timedelta(days=5 if source_tf == "1d" else (9 if source_tf == "7d" else 1))
            group = asof_join(group, source, prefix, max_age)
            coverage.append({"target_timeframe": tf, "source": name, "source_timeframe": source_tf,
                             "matched_fraction": float(group[f"{prefix}_close"].notna().mean()),
                             "last_source_available_at": source.available_at.max().isoformat()})
        if all(f"us_yield_{x}_1d_close" in group for x in ("10y", "2y", "3m")):
            group["us_yield_curve_10y_2y_pct_points"] = group.us_yield_10y_1d_close - group.us_yield_2y_1d_close
            group["us_yield_curve_10y_3m_pct_points"] = group.us_yield_10y_1d_close - group.us_yield_3m_1d_close
        group = group.sort_values(["symbol", "timestamp"])
        path = artifact / f"market_features_{tf}.csv.gz"
        group.to_csv(path, index=False, compression="gzip")
        files.append({"file": path.name, "timeframe": tf, "rows": len(group), "columns": len(group.columns),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    pd.DataFrame(coverage).to_csv(artifact / "coverage.csv", index=False)
    write_json(artifact / "manifest.json", {"as_of": manifest["as_of"], "rows": sum(x["rows"] for x in files),
              "files": files, "lags": LAGS,
              "pending_external": manifest["pending_external"]})
    LOG.info("Saved %s feature rows in %s timeframe files", sum(x["rows"] for x in files), len(files))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "build", "run"])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--as-of", default=None, help="Optional UTC-aware collection cutoff")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if args.command in ("fetch", "run"):
        end = min(utc(args.as_of), pd.Timestamp.now(tz="UTC")) if args.as_of else pd.Timestamp.now(tz="UTC")
        fetch(args.root, end)
    if args.command in ("build", "run"):
        build(args.root)


if __name__ == "__main__":
    main()
