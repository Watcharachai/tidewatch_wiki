#!/usr/bin/env python3
"""Build point-in-time 30m/60m MTS forecasting tables and data-quality reports."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from features import LAGS, asof_join, validate

ROOT = Path(__file__).resolve().parent.parent
TIMEFRAMES = {"30m": 30, "60m": 60}
SYMBOLS = ("GLD965", "GLD9999")
LABEL = "y_next_return"
LABEL_COLUMNS = (LABEL, "y_next_close", "label_available_at")
NON_FEATURES = {"timestamp", "available_at", "symbol", "purity_pct", "currency",
                "timeframe", "source", "source_count", *LABEL_COLUMNS}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_xauusdt(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    required = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(raw):
        raise ValueError(f"{path}: missing {sorted(required - set(raw))}")
    bars = raw.rename(columns={"Date": "timestamp", "Open": "open", "High": "high",
                               "Low": "low", "Close": "close", "Volume": "volume"})
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True)
    bars["available_at"] = bars.timestamp + pd.Timedelta(minutes=30)
    bars = validate(bars[["timestamp", "available_at", "open", "high", "low", "close", "volume"]],
                    "xauusdt_30m", requires_volume=True)
    if (bars.low.gt(bars[["open", "close"]].min(axis=1)) |
            bars.high.lt(bars[["open", "close"]].max(axis=1))).any():
        raise ValueError("XAUUSDT: inconsistent OHLC")
    if bars.timestamp.dt.minute.mod(30).ne(0).any() or bars.timestamp.dt.second.ne(0).any():
        raise ValueError("XAUUSDT: 30-minute bars are not wall-clock aligned")
    return bars


def aggregate_60m(bars: pd.DataFrame) -> pd.DataFrame:
    source = bars.set_index("timestamp")
    grouped = source.resample("60min", label="left", closed="left")
    out = grouped.agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    out = out.loc[grouped.close.count().eq(2)].reset_index()
    out["available_at"] = out.timestamp + pd.Timedelta(minutes=60)
    return validate(out, "xauusdt_60m", requires_volume=True)


def attach_labels(frame: pd.DataFrame, minutes: int) -> tuple[pd.DataFrame, dict]:
    frame = frame.sort_values(["symbol", "timestamp"]).copy()
    grouped = frame.groupby("symbol", sort=False)
    next_time = grouped.timestamp.shift(-1)
    next_close = grouped.close.shift(-1)
    next_available = grouped.available_at.shift(-1)
    contiguous = next_time.sub(frame.timestamp).eq(pd.Timedelta(minutes=minutes))
    current_year = frame.available_at.dt.tz_convert("Asia/Bangkok").dt.year
    label_year = next_available.dt.tz_convert("Asia/Bangkok").dt.year
    valid = contiguous & current_year.eq(label_year) & next_available.notna()
    audit = {"source_rows": len(frame), "dropped_no_contiguous_next_bar": int((~contiguous).sum()),
             "dropped_year_boundary": int((contiguous & current_year.ne(label_year)).sum()),
             "labeled_rows": int(valid.sum())}
    frame = frame.loc[valid].copy()
    frame["y_next_close"] = next_close.loc[valid].to_numpy()
    frame[LABEL] = frame.y_next_close / frame.close - 1
    frame["label_available_at"] = next_available.loc[valid].to_numpy()
    frame["split"] = np.where(frame.available_at.dt.tz_convert("Asia/Bangkok").dt.year.eq(2025), "train_2025", "test_2026")
    if (frame.label_available_at <= frame.available_at).any():
        raise ValueError("Label is not strictly after feature availability")
    return frame, audit


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [c for c in frame.select_dtypes(include="number").columns if c not in NON_FEATURES]


def load_xy(path: Path, columns: list[str] | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Return baseline numeric X and next-bar fractional-return y."""
    if columns is None:
        manifest = json.loads((path.parent / "manifest.json").read_text())
        entry = next((item for item in manifest["outputs"] if item["file"] == path.name), None)
        if entry is None:
            raise ValueError(f"No feature selection recorded for {path.name}")
        columns = entry["baseline_feature_columns"]
    frame = pd.read_csv(path, low_memory=False)
    return frame[columns].copy(), frame[LABEL].copy()


def describe(frame: pd.DataFrame, columns: list[str], timeframe: str, symbol: str) -> tuple[list[dict], list[dict]]:
    stats, missing = [], []
    for split, group in [("all", frame), *[(v, frame.loc[frame.split.eq(v)]) for v in ("train_2025", "test_2026")]]:
        for column in [*columns, LABEL]:
            series = pd.to_numeric(group[column], errors="raise")
            present = series.dropna()
            missing.append({"timeframe": timeframe, "symbol": symbol, "split": split,
                            "column": column, "rows": len(group), "null_count": int(series.isna().sum()),
                            "null_rate": float(series.isna().mean()) if len(group) else np.nan})
            stats.append({"timeframe": timeframe, "symbol": symbol, "split": split, "column": column,
                          "count": len(present), "mean": present.mean(), "std": present.std(),
                          "min": present.min(), "p05": present.quantile(.05), "median": present.median(),
                          "p95": present.quantile(.95), "max": present.max()})
    return stats, missing


def write_report(root: Path, manifest: dict, stats: pd.DataFrame, missing: pd.DataFrame) -> Path:
    lines = ["# MTS 30m and 60m training dataset", "",
             "Each row uses information available when the current MTS bar completes. The label is the fractional close return to the next **contiguous** completed bar of the same purity. Session gaps and year-boundary labels are excluded. The 2025/2026 split uses the decision time in Asia/Bangkok; the 2026 rows are held out.", "",
             "| Timeframe | MTS target | Labeled rows | 2025 train | 2026 test | Numeric X candidates | Baseline X columns | XAU/USDT present | Next-return mean | Next-return std | 5th–95th percentile |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",]
    for item in manifest["outputs"]:
        tf, sym = item["timeframe"], item["symbol"]
        y = stats.loc[(stats.timeframe.eq(tf)) & (stats.symbol.eq(sym)) &
                      (stats.split.eq("all")) & (stats.column.eq(LABEL))].iloc[0]
        lines.append(f"| {tf} | {sym} | {item['rows']:,} | {item['train_2025']:,} | {item['test_2026']:,} | "
                     f"{len(item['feature_columns'])} | {len(item['baseline_feature_columns'])} | "
                     f"{item['xauusdt_non_null']:,} | {100*y['mean']:.4f}% | {100*y['std']:.4f}% | "
                     f"{100*y['p05']:.3f}% to {100*y['p95']:.3f}% |")
    lines += ["", "## Missingness", "",
              "Null rates below are measured on the **labeled rows**. The XAU/USDT source begins 11 December 2025 and ends 31 October 2026, while the MTS snapshot runs through 6 November 2026. XAUT/USDT begins in March 2026. Thus neither additional gold series has a useful full-2025 training history.", "",
              "| Timeframe | Target | Feature | 2025 train null | 2026 test null |",
              "|---|---|---|---:|---:|"]
    for item in manifest["outputs"]:
        tf, sym = item["timeframe"], item["symbol"]
        for column in (f"xauusdt_{tf}_close", f"xauusdt_{tf}_return_lag30",
                       f"xautusdt_{tf}_close", f"btcusdt_{tf}_close", "us_yield_10y_1d_close"):
            selected = missing.loc[(missing.timeframe.eq(tf)) & (missing.symbol.eq(sym)) &
                                   (missing.column.eq(column))].set_index("split")
            lines.append(f"| {tf} | {sym} | `{column}` | "
                         f"{100*selected.loc['train_2025', 'null_rate']:.1f}% | "
                         f"{100*selected.loc['test_2026', 'null_rate']:.1f}% |")
    lines += ["", "All 235 numeric candidates and their statistics are in `../../training_artifacts/summary_statistics.csv`; per-column null counts and rates, including train/test splits, are in `../../training_artifacts/null_rates.csv`. Exactly 30 candidates are entirely null in the 2025 training portion, mainly the XAUT series. The baseline selection keeps numeric columns with at least 80% observed values and more than one distinct value **in 2025 training only**. It does not fit an imputer or scaler; those must be fit on training data during modeling.", "",
              "## Source and leakage assumptions", "",
              "- The new `xauusdt_30m_*` and `xauusdt_60m_*` features come from uploaded `data/XAUUSDT_30m.csv`. 60m bars aggregate exactly two complete 30m bars. The files carry no historical publication timestamps, so `available_at` is assumed to be the bar end. Confirm venue, symbol meaning, volume units and publication delay before using these fields in a strict point-in-time backtest.",
              "- The existing feature matrix supplies MTS, MTS XAU/USD, XAUT/USDT, BTC/USDT and delayed FRED references. FRED availability is an assumed observation date plus two UTC days, not a verified vintage. Existing MTS completion times are also nominal.",
              "- `y_next_return` and `y_next_close` are future outcomes. Use `load_xy()` or the manifest's `baseline_feature_columns` for X. Do not pass label columns or `label_available_at` as model inputs.",
              "- MTS purities are separate prediction tasks. Evaluate against a zero-return/no-change baseline using chronological validation; a random row split would leak adjacent market states.", ""]
    path = root / "analysis" / "reports" / "training_dataset_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def build(root: Path = ROOT) -> dict:
    input_xau = root / "data" / "XAUUSDT_30m.csv"
    xau_30 = read_xauusdt(input_xau)
    xau = {"30m": xau_30, "60m": aggregate_60m(xau_30)}
    output = root / "training_artifacts"
    output.mkdir(exist_ok=True)
    all_stats, all_missing, outputs = [], [], []
    for timeframe, minutes in TIMEFRAMES.items():
        source_path = root / "feature_artifacts" / f"market_features_{timeframe}.csv.gz"
        source = pd.read_csv(source_path, low_memory=False, parse_dates=["timestamp", "available_at"])
        source["timestamp"] = pd.to_datetime(source.timestamp, utc=True)
        source["available_at"] = pd.to_datetime(source.available_at, utc=True)
        source = asof_join(source, xau[timeframe], f"xauusdt_{timeframe}", pd.Timedelta(minutes=minutes))
        # Future labels are built only within each MTS symbol and only across an exact interval.
        labeled, audit = attach_labels(source, minutes)
        if not set(labeled.symbol.unique()).issubset(SYMBOLS):
            raise ValueError("Unexpected MTS target symbol")
        for symbol in SYMBOLS:
            table = labeled.loc[labeled.symbol.eq(symbol)].copy()
            columns = feature_columns(table)
            train = table.loc[table.split.eq("train_2025"), columns]
            baseline_columns = train.columns[(train.notna().mean().ge(.8)) &
                                             (train.nunique(dropna=True).gt(1))].tolist()
            file = output / f"training_{timeframe}_{symbol}.csv.gz"
            table.to_csv(file, index=False, compression={"method": "gzip", "mtime": 0})
            stats, missing = describe(table, columns, timeframe, symbol)
            all_stats.extend(stats)
            all_missing.extend(missing)
            outputs.append({"file": file.name, "timeframe": timeframe, "symbol": symbol,
                            "rows": len(table), "train_2025": int(table.split.eq("train_2025").sum()),
                            "test_2026": int(table.split.eq("test_2026").sum()),
                            "columns": len(table.columns), "feature_columns": columns,
                            "baseline_feature_columns": baseline_columns,
                            "xauusdt_non_null": int(table[f"xauusdt_{timeframe}_close"].notna().sum()),
                            "label_mean": float(table[LABEL].mean()), "label_std": float(table[LABEL].std()),
                            "sha256": sha256(file), "source_sha256": sha256(source_path),
                            "dropped_no_contiguous_next_bar_all_symbols": audit["dropped_no_contiguous_next_bar"],
                            "dropped_year_boundary_all_symbols": audit["dropped_year_boundary"]})
    stats_file = output / "summary_statistics.csv"
    missing_file = output / "null_rates.csv"
    stats_frame, missing_frame = pd.DataFrame(all_stats), pd.DataFrame(all_missing)
    stats_frame.to_csv(stats_file, index=False)
    missing_frame.to_csv(missing_file, index=False)
    manifest = {"label": "next contiguous completed MTS bar fractional close return",
                "decision_time": "current MTS bar available_at", "split_timezone": "Asia/Bangkok",
                "xauusdt_source": input_xau.name, "xauusdt_sha256": sha256(input_xau),
                "xauusdt_availability_assumption": "bar start plus 30 or 60 minutes; actual publication time unverified",
                "lags": LAGS, "outputs": outputs,
                "summary_statistics_sha256": sha256(stats_file), "null_rates_sha256": sha256(missing_file)}
    report = write_report(root, manifest, stats_frame, missing_frame)
    manifest["report_sha256"] = sha256(report)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    manifest = build(args.root)
    for item in manifest["outputs"]:
        print(item["file"], item["rows"], "rows", len(item["feature_columns"]), "X columns")


if __name__ == "__main__":
    main()
