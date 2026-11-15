#!/usr/bin/env python3
"""Prepare all-date 60m features and fold-dependent two-model targets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from features import asof_join
from training import read_xauusdt, aggregate_60m, feature_columns

ROOT = Path(__file__).resolve().parent.parent
EPS = 1e-6
WINDOWS = (7, 15, 30)
LAGS = (1, 5, 30)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ewma_sigma(returns: pd.Series, half_life: float = 30, seed: float | None = None) -> pd.Series:
    """Recursive RMS volatility. Seed is mean SQUARED return, never a future label."""
    if half_life <= 0 or (seed is not None and (not np.isfinite(seed) or seed < 0)):
        raise ValueError("Invalid EWMA half-life or variance seed")
    alpha = 1 - 2 ** (-1 / half_life)
    state = seed
    result = []
    for value in returns:
        if pd.notna(value):
            state = value**2 if state is None else (1-alpha)*state + alpha*value**2
        result.append(np.sqrt(max(state, EPS**2)) if state is not None else np.nan)
    return pd.Series(result, index=returns.index, dtype=float)


def rolling_stat(series: pd.Series, window: int, operation: str) -> pd.Series:
    rolling = series.rolling(window, min_periods=window)
    if operation in ("skew", "kurt"):
        # Calculate moments within each window: pandas' optimized moments can
        # use whole-series centering and change past rounding when future prices change.
        def moment(values):
            n = len(values)
            centered = values - values.mean()
            m2 = np.mean(centered**2)
            if m2 == 0:
                return 0.0
            if operation == "skew":
                return np.sqrt(n*(n-1))/(n-2)*np.mean(centered**3)/m2**1.5
            return (n-1)/((n-2)*(n-3))*((n+1)*(np.mean(centered**4)/m2**2-3)+6)
        return rolling.apply(moment, raw=True)
    return getattr(rolling, operation)()


def observed_rolling(series: pd.Series, window: int, operation: str) -> pd.Series:
    """Last W valid hourly returns, spanning sessions; retain state at a gap bar."""
    valid = series.dropna()
    rolled = rolling_stat(valid, window, operation)
    return rolled.reindex(series.index).ffill()


def engineer(frame: pd.DataFrame, symbol: str) -> tuple[pd.DataFrame, dict]:
    f = frame.sort_values("timestamp").reset_index(drop=True).copy()
    for c in ("timestamp", "available_at"):
        f[c] = pd.to_datetime(f[c], utc=True)
    old_features = feature_columns(f)
    elapsed = f.timestamp.diff().dt.total_seconds()/60
    observed_return = np.log(f.close/f.close.shift())
    f["elapsed_minutes_previous_bar"] = elapsed
    f["session_open_flag"] = (elapsed.gt(60) | elapsed.isna()).astype(int)
    f["own_log_return"] = observed_return.where(elapsed.eq(60))
    f["gap_log_return"] = observed_return.where(elapsed.gt(60))
    local = f.available_at.dt.tz_convert("Asia/Bangkok")
    hour = local.dt.hour + local.dt.minute/60
    f["hour_sin"], f["hour_cos"] = np.sin(2*np.pi*hour/24), np.cos(2*np.pi*hour/24)
    f["weekday_sin"], f["weekday_cos"] = np.sin(2*np.pi*local.dt.dayofweek/7), np.cos(2*np.pi*local.dt.dayofweek/7)
    f["day_of_week"] = local.dt.dayofweek
    own = "mts965" if symbol == "GLD965" else "mts9999"
    cross = "mts9999" if symbol == "GLD965" else "mts965"
    for name, source in (("cross", cross), ("xauusd", "mts_xauusd"), ("btc", "btcusdt")):
        prefix = f"{source}_60m"
        same_bar = pd.to_datetime(f[prefix+"_observed_at"], utc=True).eq(f.timestamp)
        f[name+"_log_return"] = np.log1p(f[prefix+"_return_lag1"]).where(
            same_bar & f[prefix+"_elapsed_min_lag1"].eq(60))
    for name in ("own", "cross", "xauusd", "btc"):
        for lag in LAGS:
            f[f"{name}_log_return_shift{lag}"] = f[name+"_log_return"].shift(lag)
    for lag in LAGS:
        f[f"abs_log_return_shift{lag}"] = f.own_log_return.abs().shift(lag)
        own_prefix, ref_prefix = f"{own}_60m", "mts_xauusd_60m"
        same_window = (pd.to_datetime(f[ref_prefix+"_observed_at"], utc=True).eq(f.timestamp) &
                       f[own_prefix+f"_elapsed_min_lag{lag}"].eq(f[ref_prefix+f"_elapsed_min_lag{lag}"]))
        f[f"fair_return_gap_window{lag}"] = (np.log1p(f[own_prefix+f"_return_lag{lag}"]) -
            np.log1p(f[ref_prefix+f"_return_lag{lag}"])).where(same_window)
        f[f"har_rms_vol{lag}"] = np.sqrt(observed_rolling(f.own_log_return.pow(2), lag, "mean"))
    for window in WINDOWS:
        for stat in ("min", "max", "mean", "var", "skew", "kurt"):
            f[f"price_{stat}{window}"] = rolling_stat(f.close, window, stat)
            f[f"return_{stat}{window}"] = observed_rolling(f.own_log_return, window, stat)
        f[f"ma_gap{window}"] = f.close/f[f"price_mean{window}"]-1
        f[f"price_window_elapsed_min{window}"] = (f.timestamp-f.timestamp.shift(window-1)).dt.total_seconds()/60
        valid_time = f.timestamp.where(f.own_log_return.notna()).dropna()
        oldest = valid_time.shift(window-1).reindex(f.index).ffill()
        f[f"return_window_elapsed_min{window}"] = (f.timestamp-oldest).dt.total_seconds()/60
    # All rows are retained for history; gaps/last row have null future targets.
    next_time = f.timestamp.shift(-1)
    valid_label = next_time.sub(f.timestamp).eq(pd.Timedelta(hours=1))
    f["label_available_at"] = f.available_at.shift(-1).where(valid_label)
    f["y_next_close"] = f.close.shift(-1).where(valid_label)
    f["y_next_log_return"] = np.log(f.y_next_close/f.close)
    f["y_model2_log_abs"] = np.log(EPS + f.y_next_log_return.abs())
    f["label_valid"] = valid_label
    # This is a causal reference only; a real fold overrides the seed and half-life.
    f["sigma_ewma_hl30_causal"] = ewma_sigma(f.own_log_return)
    f["y_model1_z_causal"] = (f.y_next_log_return/f.sigma_ewma_hl30_causal).clip(-5, 5)
    engineered = [c for c in f.select_dtypes(include="number") if c not in old_features and
                  c not in ("purity_pct", "source_count", "sigma_ewma_hl30_causal") and not c.startswith("y_")]
    time_features = ["hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "session_open_flag", "elapsed_minutes_previous_bar"]
    model1 = [f"{n}_log_return_shift{k}" for n in ("own", "cross", "xauusd", "btc") for k in LAGS]
    model1 += [f"fair_return_gap_window{k}" for k in LAGS] + time_features + ["own_log_return", "cross_log_return"]
    model2 = [f"har_rms_vol{k}" for k in LAGS] + [f"abs_log_return_shift{k}" for k in LAGS] + time_features
    groups = {"existing_numeric": old_features, "engineered_numeric": engineered,
              "model1_core": model1, "model2_har": model2,
              "rolling_ablation": [c for c in engineered if c.startswith(("price_", "return_", "ma_gap"))],
              "macro_ablation": [c for c in old_features if c.startswith(("us_yield_", "vix_", "usdthb_", "wti_oil_"))]}
    assert len(model1) <= 25
    return f, groups


def materialize_fold(frame: pd.DataFrame, train_start: str, train_end: str,
                     validation_start: str, validation_end: str, half_life: float = 30,
                     embargo_bars: int = 30) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Half-open decision-time ranges; caller fits imputer/scaler on returned train only."""
    bounds = [pd.Timestamp(x) for x in (train_start, train_end, validation_start, validation_end)]
    if any(x.tzinfo is None for x in bounds) or not bounds[0] < bounds[1] <= bounds[2] < bounds[3]:
        raise ValueError("Supply ordered timezone-aware fold boundaries")
    if embargo_bars < 30:
        raise ValueError("At least 30 observed-bar embargo is required")
    f = frame.copy()
    f.available_at = pd.to_datetime(f.available_at, utc=True)
    f.label_available_at = pd.to_datetime(f.label_available_at, utc=True)
    f = f.sort_values("available_at").reset_index(drop=True)
    if f.symbol.nunique() != 1 or f.available_at.duplicated().any():
        raise ValueError("A fold must contain one symbol and unique bar times")
    ts, te, vs, ve = bounds
    train_context = f.available_at.ge(ts) & f.available_at.lt(te)
    embargo = f.available_at.ge(te) & f.available_at.lt(vs)
    if int(embargo.sum()) < embargo_bars:
        raise ValueError("Insufficient observed bars between training and validation")
    observed = f.loc[train_context, "own_log_return"].dropna()
    if len(observed) < 30:
        raise ValueError("Need at least 30 valid training returns to seed EWMA")
    seed = float(observed.pow(2).mean())
    context = f.loc[f.available_at.ge(ts) & f.available_at.lt(ve)].copy()
    context["sigma_t"] = ewma_sigma(context.own_log_return, half_life, seed)
    context["y_model1_z"] = (context.y_next_log_return/context.sigma_t).clip(-5, 5)
    train = context.loc[context.available_at.lt(te) & context.label_available_at.lt(te)].copy()
    validation = context.loc[context.available_at.ge(vs) & context.label_available_at.lt(ve)].copy()
    if train.empty or validation.empty:
        raise ValueError("Both fold segments need matured contiguous-bar labels")
    info = {"ewma_seed_variance": seed, "half_life": half_life, "embargo_context_bars": int(embargo.sum()),
            "train_rows": len(train), "validation_rows": len(validation)}
    return train, validation, info


def build(root: Path = ROOT) -> None:
    out = root/"training_artifacts"/"_training_baseline"
    out.mkdir(parents=True, exist_ok=True)
    base_path = root/"feature_artifacts"/"market_features_60m.csv.gz"
    base = pd.read_csv(base_path, low_memory=False, parse_dates=["timestamp", "available_at"])
    xau_path = root/"data"/"XAUUSDT_30m.csv"
    if "xauusdt_60m_close" not in base:
        base = asof_join(base, aggregate_60m(read_xauusdt(xau_path)), "xauusdt_60m", pd.Timedelta(hours=1))
    inventory, quality, dictionary = [], [], []
    for symbol in ("GLD965", "GLD9999"):
        f, groups = engineer(base.loc[base.symbol.eq(symbol)], symbol)
        filename = out/f"baseline_60m_{symbol}.csv.gz"
        f.to_csv(filename, index=False, compression={"method": "gzip", "mtime": 0})
        candidates = groups["existing_numeric"] + groups["engineered_numeric"]
        for c in candidates + ["y_next_log_return", "y_model2_log_abs", "y_model1_z_causal"]:
            s = f[c]
            quality.append({"symbol": symbol, "column": c, "count": int(s.count()),
                            "null_rate": float(s.isna().mean()), "mean": s.mean(), "std": s.std(),
                            "min": s.min(), "median": s.median(), "max": s.max()})
        for group, columns in groups.items():
            dictionary.extend({"symbol": symbol, "group": group, "column": c} for c in columns)
        inventory.append({"symbol": symbol, "file": filename.name, "rows": len(f),
                          "valid_labels": int(f.label_valid.sum()), "numeric_candidates": len(candidates),
                          "groups": groups, "sha256": digest(filename)})
    pd.DataFrame(quality).to_csv(out/"feature_quality.csv", index=False)
    pd.DataFrame(dictionary).to_csv(out/"feature_groups.csv", index=False)
    manifest = {"timeframe": "60m", "fixed_year_split": False, "epsilon": EPS,
                "source_feature_matrix_sha256": digest(base_path), "uploaded_xauusdt_sha256": digest(xau_path),
                "model1_target": "Fold-specific clip(y_next_log_return/sigma_t,-5,5); use materialize_fold",
                "reference_target": "y_model1_z_causal uses HL30 and first observed squared return seed; not the fold-fit target",
                "model2_target": "y_model2_log_abs = log(1e-6 + abs(y_next_log_return))",
                "outputs": inventory}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    for item in inventory:
        print(item["symbol"], item["rows"], "context rows;", item["valid_labels"], "labels;", item["numeric_candidates"], "candidates")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    build(parser.parse_args().root)
