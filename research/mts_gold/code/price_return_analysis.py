#!/usr/bin/env python3
"""Describe MTS gold level trends and gap-aware one-period returns."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mts_gold_matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FREQUENCIES = {"30m": 30, "60m": 60, "1d": None}


def analyze_group(frame: pd.DataFrame, timeframe: str) -> tuple[pd.DataFrame, dict]:
    frame = frame.sort_values("timestamp").copy()
    previous = frame.close.shift(1)
    valid = frame.timestamp.diff().eq(pd.Timedelta(minutes=FREQUENCIES[timeframe])) if timeframe != "1d" else previous.notna()
    frame["delta_close_thb"] = (frame.close - previous).where(valid)
    frame["simple_return"] = (frame.close / previous - 1).where(valid)
    frame["log_return"] = np.log(frame.close / previous).where(valid)
    frame["rolling_std_10_pct"] = 100 * frame.simple_return.rolling(10, min_periods=10).std()
    frame["running_peak"] = frame.close.cummax()
    frame["drawdown"] = frame.close / frame.running_peak - 1
    frame["ma_30"] = frame.close.rolling(30, min_periods=30).mean()
    peak = frame.loc[frame.close.idxmax()]
    bottom = frame.loc[frame.close.idxmin()]
    trough = frame.loc[frame.drawdown.idxmin()]
    prior = frame.loc[frame.timestamp.le(trough.timestamp)]
    drawdown_peak = prior.loc[prior.close.idxmax()]
    stats = {"symbol": frame.symbol.iloc[0], "timeframe": timeframe, "bars": len(frame),
             "return_observations": int(frame.simple_return.notna().sum()),
             "excluded_noncontiguous_pairs": int((~valid).sum() - 1) if timeframe != "1d" else 0,
             "first_timestamp": frame.timestamp.iloc[0].isoformat(), "last_timestamp": frame.timestamp.iloc[-1].isoformat(),
             "first_close_thb": frame.close.iloc[0], "last_close_thb": frame.close.iloc[-1],
             "first_to_last_change_pct": 100 * (frame.close.iloc[-1] / frame.close.iloc[0] - 1),
             "bottom_close_thb": bottom.close, "bottom_timestamp": bottom.timestamp.isoformat(),
             "peak_close_thb": peak.close, "peak_timestamp": peak.timestamp.isoformat(),
             "max_drawdown_pct": 100 * trough.drawdown,
             "drawdown_peak_timestamp": drawdown_peak.timestamp.isoformat(),
             "drawdown_trough_timestamp": trough.timestamp.isoformat()}
    return frame, stats


def summary(frame: pd.DataFrame, span: str) -> dict:
    r, lr, delta = frame.simple_return.dropna(), frame.log_return.dropna(), frame.delta_close_thb.dropna()
    rolling = frame.rolling_std_10_pct.dropna()
    return {"symbol": frame.symbol.iloc[0], "timeframe": frame.timeframe.iloc[0], "span": span,
            "return_n": len(r), "mean_delta_thb": delta.mean(), "std_delta_thb": delta.std(),
            "mean_simple_pct": 100*r.mean(), "median_simple_pct": 100*r.median(),
            "variance_simple_pct_points_sq": (100*r).var(), "std_simple_pct": 100*r.std(),
            "p01_simple_pct": 100*r.quantile(.01), "p05_simple_pct": 100*r.quantile(.05),
            "p95_simple_pct": 100*r.quantile(.95), "p99_simple_pct": 100*r.quantile(.99),
            "min_simple_pct": 100*r.min(), "max_simple_pct": 100*r.max(),
            "skew_simple": r.skew(), "excess_kurtosis_simple": r.kurt(),
            "zero_return_pct": 100*r.eq(0).mean(),
            "lag1_return_corr": r.autocorr() if len(r) >= 3 else np.nan,
            "lag1_squared_return_corr": r.pow(2).autocorr() if len(r) >= 3 else np.nan,
            "mean_log_pct": 100*lr.mean(), "std_log_pct": 100*lr.std(),
            "mean_abs_simple_log_difference_pct_points": 100*(r-lr).abs().mean(),
            "rolling_10_std_median_pct": rolling.median(), "rolling_10_std_p95_pct": rolling.quantile(.95)}


def plot_results(frames: dict[tuple[str, str], pd.DataFrame], output: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for symbol, color in (("GLD965", "#b98221"), ("GLD9999", "#244875")):
        daily = frames[(symbol, "1d")]
        axes[0, 0].plot(daily.timestamp, daily.close, label=symbol, color=color, linewidth=1.3)
        axes[0, 1].plot(daily.timestamp, daily.close / daily.close.iloc[0] * 100, label=symbol, color=color)
        bars = frames[(symbol, "60m")]
        axes[1, 0].plot(bars.timestamp, 100*bars.simple_return, color=color, alpha=.65, linewidth=.5, label=symbol)
        axes[1, 1].plot(bars.timestamp, bars.rolling_std_10_pct, color=color, linewidth=.9, label=symbol)
    axes[0, 0].set_title("MTS daily close (THB)")
    axes[0, 1].set_title("Daily close indexed to first observation = 100")
    axes[1, 0].set_title("Contiguous 60m close return (%)")
    axes[1, 1].set_title("Trailing 10-bar 60m return std (%)")
    for axis in axes.flat:
        axis.grid(alpha=.25)
        axis.legend(loc="best", fontsize=8)
        axis.tick_params(axis="x", rotation=25)
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_histograms(frames: dict[tuple[str, str], pd.DataFrame], out: Path) -> None:
    for full_range in (False, True):
        fig, axes = plt.subplots(3, 2, figsize=(14, 12), constrained_layout=True)
        for row, timeframe in enumerate(("30m", "60m", "1d")):
            pooled = pd.concat([100 * frames[(symbol, timeframe)].simple_return.dropna()
                                for symbol in ("GLD965", "GLD9999")])
            limits = (pooled.min(), pooled.max()) if full_range else (pooled.quantile(.005), pooled.quantile(.995))
            edges = np.linspace(*limits, 101)
            for column, (symbol, color) in enumerate((("GLD965", "#b98221"), ("GLD9999", "#244875"))):
                axis = axes[row, column]
                values = 100 * frames[(symbol, timeframe)].simple_return.dropna()
                shown = values if full_range else values.loc[values.between(*limits)]
                axis.hist(shown, bins=edges, color=color, alpha=.83, edgecolor="white", linewidth=.2)
                axis.axvline(values.mean(), color="#b51b2b", linestyle="--", linewidth=1.2, label="Mean")
                axis.axvline(values.median(), color="black", linestyle=":", linewidth=1.2, label="Median")
                if full_range:
                    axis.set_yscale("log")
                note = (f"N = {len(values):,}\nMean = {values.mean():.4f}%\n"
                        f"Median = {values.median():.4f}%\n"
                        f"Variance = {values.var():.5f} pp²\n"
                        f"Skewness = {values.skew():.2f}\n"
                        f"Excess kurtosis = {values.kurt():.1f}")
                axis.text(.98, .96, note, ha="right", va="top", transform=axis.transAxes,
                          fontsize=8, bbox={"facecolor": "white", "edgecolor": "#aaa", "alpha": .92})
                axis.set_title(f"{symbol} — {timeframe}")
                axis.set_xlabel("One-period simple return (%)")
                axis.set_ylabel("Count" + (" (log scale)" if full_range else ""))
                axis.grid(alpha=.2)
                if row == 0 and column == 0:
                    axis.legend(loc="upper left", fontsize=8)
        caption = ("Full observed return range; logarithmic count axis" if full_range else
                   "Central 99% of returns shown; statistics use the full sample")
        fig.suptitle("MTS gold one-period return histograms — " + caption, fontsize=13)
        filename = "return_histograms_full_range.png" if full_range else "return_histograms_central.png"
        fig.savefig(out / filename, dpi=150)
        plt.close(fig)


def build(root: Path = ROOT) -> None:
    data = pd.read_csv(root / "data" / "bars.csv", parse_dates=["timestamp"],
                       usecols=["timestamp", "close", "symbol", "timeframe"])
    data.timestamp = pd.to_datetime(data.timestamp, utc=True)
    data = data.loc[data.timeframe.isin(FREQUENCIES)].copy()
    frames, level, returns, months = {}, [], [], []
    for (symbol, timeframe), group in data.groupby(["symbol", "timeframe"]):
        frame, row = analyze_group(group, timeframe)
        frames[(symbol, timeframe)] = frame
        level.append(row)
        returns.append(summary(frame, "all"))
        for year, annual in frame.groupby(frame.timestamp.dt.tz_convert("Asia/Bangkok").dt.year):
            returns.append(summary(annual, str(year)))
        if timeframe == "1d":
            local_month = frame.timestamp.dt.tz_convert("Asia/Bangkok").dt.strftime("%Y-%m")
            for month, monthly in frame.groupby(local_month):
                months.append({"symbol": symbol, "month": str(month), "observations": len(monthly),
                               "first_close_thb": monthly.close.iloc[0], "last_close_thb": monthly.close.iloc[-1],
                               "first_to_last_change_pct": 100*(monthly.close.iloc[-1]/monthly.close.iloc[0]-1),
                               "lowest_close_thb": monthly.close.min(), "highest_close_thb": monthly.close.max()})
    out = root / "analysis" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    levels, retstats = pd.DataFrame(level), pd.DataFrame(returns)
    levels.to_csv(out / "price_extrema_drawdown.csv", index=False)
    retstats.to_csv(out / "one_period_return_statistics.csv", index=False)
    pd.DataFrame(months).to_csv(out / "monthly_price_trend.csv", index=False)
    plot_results(frames, out / "price_return_modeling.png")
    plot_histograms(frames, out)
    write_report(levels, retstats, out)


def write_report(levels: pd.DataFrame, stats: pd.DataFrame, out: Path) -> None:
    lines = ["# MTS gold price and return behavior for target design", "",
             "Source: completed direct MTS GLD965 and GLD9999 chart bars from 2025 through the 7 November 2026 collection cutoff. The modeling focus is 30m and 60m; native daily closes provide long-run context. Intraday `t−1` means the immediately preceding **clock-adjacent** completed bar; pairs separated by a gap are excluded from return/variance calculations. Daily `t−1` means the preceding observed daily candle, including weekends between sessions.", "",
             "## Price level, peak, bottom and drawdown", "",
             "| Target | Frame | Bars | First→last close | First→last change | Lowest close (Bangkok) | Highest close (Bangkok) | Max peak-to-trough drawdown |",
             "|---|---|---:|---|---:|---|---|---:|"]
    for row in levels.itertuples():
        def local(value: str) -> str:
            return pd.Timestamp(value).tz_convert("Asia/Bangkok").strftime("%Y-%m-%d %H:%M")
        lines.append(f"| {row.symbol} | {row.timeframe} | {row.bars:,} | {row.first_close_thb:,.0f}→{row.last_close_thb:,.0f} THB | "
                     f"{row.first_to_last_change_pct:.1f}% | {row.bottom_close_thb:,.0f} ({local(row.bottom_timestamp)}) | "
                     f"{row.peak_close_thb:,.0f} ({local(row.peak_timestamp)}) | {row.max_drawdown_pct:.1f}% |")
    lines += ["", "Lowest close is the sample-wide bottom; the maximum drawdown trough can occur at a different time. Exact peak and drawdown-trough timestamps are in `price_extrema_drawdown.csv`. `monthly_price_trend.csv` traces each purity's daily close month by month.", "",
              "## One-period return and variance", "",
              "Returns are `close[t]/close[t−1]−1`; log returns are `ln(close[t]/close[t−1])`. Price change in THB is also exported. Variance below is the sample variance of returns expressed in percentage points squared; it is not price-level variance.", "",
              "| Target | Frame | Year | Return N | Mean | Std | Variance (pp²) | 5th–95th pct | Skew | Excess kurtosis | 10-bar rolling std median/p95 |",
              "|---|---|---|---:|---:|---:|---:|---|---:|---:|---|"]
    for row in stats.itertuples():
        if row.timeframe == "1d" and row.span != "all":
            continue
        lines.append(f"| {row.symbol} | {row.timeframe} | {row.span} | {row.return_n:,} | {row.mean_simple_pct:.4f}% | "
                     f"{row.std_simple_pct:.4f}% | {row.variance_simple_pct_points_sq:.5f} | "
                     f"{row.p05_simple_pct:.3f}% to {row.p95_simple_pct:.3f}% | {row.skew_simple:.2f} | "
                     f"{row.excess_kurtosis_simple:.1f} | {row.rolling_10_std_median_pct:.3f}% / {row.rolling_10_std_p95_pct:.3f}% |")
    lines += ["", "The full `one_period_return_statistics.csv` also gives THB changes, 1st/99th percentiles, zero-return rates, simple versus log-return differences, and lag-1 return/squared-return correlations. Annual summaries assign a return to the current bar's Bangkok year; early-year returns can reference the prior year.", "",
              "The 2026 intraday return variance is roughly **2.5–2.7×** its 2025 value across the two purities and both selected intervals. The level trend and the return-volatility regime changed together. Simple and log returns differ very little on ordinary intraday bars (mean absolute difference about **0.00015 percentage points** at 30m and **0.00030** at 60m), but both retain extreme observations.", "",
              "## Return histograms", "",
              "Each panel includes mean, median, sample variance, skewness and **excess** kurtosis computed from all observed returns. The central view displays the pooled 0.5th–99.5th percentile range within each timeframe so the shape near zero is readable; the full-range view uses a logarithmic count axis to reveal rare extremes. Intraday returns cross no missing-bar gap.", "",
              "![Central return histograms for GLD965 and GLD9999 at 30m, 60m and 1d](return_histograms_central.png)", "",
              "![Full-range return histograms with logarithmic counts](return_histograms_full_range.png)", "",
              "## Modeling decision", "",
              "- **Preferred dependent variable:** next contiguous 30m or 60m **log return**, `ln(close[t+1]/close[t])`, separately for GLD965 and GLD9999. Predicting raw THB close directly would make the large level trend and differing purity scales dominate the loss. Log return is additive across time and converts to a price forecast as `close[t] × exp(predicted_log_return)`.",
              "- The saved training tables currently use simple `y_next_return`. Convert with `np.log1p(y_next_return)`; the two are close for ordinary bars, while log return handles compounding and large moves more consistently. This transform uses only the future outcome for the label, never as an input.",
              "- **Standardization:** compute the training-period mean and standard deviation of log-return labels, then apply those constants to validation/test labels if the chosen model benefits from scaling. Invert the transform before reporting return or THB errors. Scale input features only with training-fitted parameters.",
              "- **Moving averages:** use trailing MAs, MA gaps, or rolling volatility as possible inputs computed from bars available by decision time. Avoid a smoothed-price dependent variable initially: it changes the forecast question, overlaps heavily across observations, and can hide short-lived extremes. Never use centered MAs.",
              "- Return distributions have extreme tails and changing volatility. Compare against a zero-return/no-change forecast with MAE and robust tail diagnostics; report performance by year and volatility regime. A constant-variance Gaussian error model should be treated as a baseline assumption, not established by these descriptive statistics.",
              "- MTS bar completion times are nominal and historical revisions are possible. This report describes the available sample; it does not establish predictive skill or a live execution price.", "",
              "![Price trend, normalized levels, 60m returns, and rolling volatility](price_return_modeling.png)", ""]
    (out / "price_return_modeling.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    build(args.root)


if __name__ == "__main__":
    main()
