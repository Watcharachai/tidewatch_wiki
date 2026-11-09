# MTS Gold Price and Return Forecast Architecture

Version 2.0 — 9 November 2026 (Asia/Bangkok)

Purpose: research forecasts for direct MTS Gold 96.5% (`GLD965`) and 99.99% (`GLD9999`) spot chart prices in THB. The user confirmed that `GLD9999`, rather than an exact 99.9% product, is the intended second series. This document supersedes the supplied draft's XAU/USD trading objective. It specifies price and return prediction. The Markov decision process (MDP) adjusts forecasts; its action is never a trade or position size.

## 1. Research question and scope

At a known decision time, does information from five structured news blocks improve future MTS gold return and price forecasts beyond completed market data alone? Test that question separately for each symbol and horizon: 15, 30 and 60 minutes; one observed daily candle; and seven Bangkok calendar days. Forecasts are informational outputs. Trade execution, P&L, Sharpe ratio, and autonomous order placement are outside this model's objective.

Keep direct MTS prices separate from Tidewatch's existing synthetic `GOLD965THB@mts` and `GOLD9999USD@mts`. The latter is quoted in USD, while direct `GLD9999` is THB. XAU/USD and USD/THB are useful explanatory inputs, not substitutes for the target. MTS symbol metadata exposes no volume series, so MTS volume prediction cannot be a validated target until an independent licensed volume source exists.

## 2. Prediction contract

For symbol `j` and horizon `h`, let `P(j,t)` be the close of the most recent fully completed MTS candle available at decision time `t`. Let `T(j,t,h)` be the future eligible completed candle chosen by the horizon rule. The target is `r(j,t,h) = log(P(j,T) / P(j,t))`; the corresponding future price is `P(j,T) = P(j,t) * exp(r(j,t,h))`. Publish both predicted log return and predicted THB price, with units and timestamps. The present research OHLC feed does not identify bid/ask/mid or weight basis; these are chart-price forecasts.

- For 15/30/60 minutes, issue at a completed 15-minute candle boundary and label with the first completed 15-minute candle whose completion time is at or after `t + h`. If the target is delayed more than 15 minutes by a closure or gap, mark the label unavailable rather than changing its meaning silently.
- For one day, issue after a native daily candle is complete and label with the next observed native daily candle. This is one observed trading session, with elapsed calendar time recorded.
- For seven days, issue after a native daily candle is complete and label with the first completed native daily candle at or after `t + 7 Bangkok calendar days`. Record actual elapsed time and exclude cases delayed more than three days by closures or source gaps. This is explicitly distinct from seven trading sessions and the historical 7-day OHLC aggregation.
- Do not create targets from candles that were incomplete at `t`. Do not interpolate across absent prices. A later model version may choose different closure tolerances, but must use a different target identifier and repeat evaluation.

The existing `return_1`, `return_3`, `return_7`, `return_14`, and `return_30` in `returns.csv.gz` are *past* returns and may be features. They are not the forward labels defined above. Each forecast row must store `symbol`, `horizon`, `decision_at`, `feature_cutoff_at`, `target_at`, `actual_elapsed_minutes`, `source_version`, `feature_version`, `model_version`, and eventual label status.

## 3. Two input streams

Quantitative stream: start with the direct MTS price series and available historical returns, realized volatility, range, session/calendar flags, and lagged features. Add XAU/USD, USD/THB, US yields, DXY, VIX, and scheduled macro releases only after their history and *first available publication times* are verified. Refresh rates differ: an unreleased CPI value or later-revised yield must never appear in an earlier 15-minute row. Fit transformations within training windows. Compare a regularized linear model and gradient-boosted trees before trying LSTM/GRU. The quantitative model produces a baseline predicted log return `F(j,t,h)`, plus its own estimate of uncertainty.

Qualitative stream: use Tidewatch's JEV capabilities to score five separately defined blocks: (1) US monetary policy and macro conditions, (2) geopolitical risk, (3) China demand and economic conditions, (4) global central-bank gold activity, and (5) broad financial-market stress. Each question must specify the source text, affected gold symbol or common gold market, a time horizon, and an unambiguous score direction. Return a score `S(i,t,h)` in `[-1,1]`, an uncertainty/confidence field `C(i,t,h)` in `[0,1]`, and explicit missing, not applicable, and source-unavailable states. The confidence field is a model output, not automatically a calibrated probability of a future price move.

Preserve each source's publication time, first ingestion time, JEV scoring time, prompt/model version, and document identity. At decision time `t`, only use a score if it was actually produced by `t`. Deduplicate syndicated and repeated coverage. Aggregate messages within each block using a declared time decay and source coverage count; retain the age of the latest eligible item. Do not turn a no-news interval into a neutral prediction. Historical text scored today must be labeled retrospective and must not masquerade as a real-time 2025 score.

## 4. Forecast-fusion MDP

Retain an MDP as the sequential adjustment layer. A state at `t` contains the baseline forecasts and uncertainty by horizon, recent completed market observations and volatility, five scored news blocks and their availability/age/coverage, session status, and the previous forecast adjustment. Its history must be sufficient for a useful approximation of the Markov property; the market itself is exogenous and does not respond to our forecast.

The action is a five-component bounded vector `a(i,t,h)` in `[-1,1]`. It expresses how the policy adjusts the forecast using each news block. It has no unit of contracts, THB exposure, or buy/sell instruction. For a block-availability mask `M(i,t)`, define `z(i,t,h) = M(i,t) * S(i,t,h) * C(i,t,h)`. A score's orientation must be tested, and the confidence term may be removed if calibration experiments show it hurts performance. Let `sigma(j,h)` be a return scale estimated only from the training window and `kappa(h)` a predeclared adjustment limit. Then:

`delta(j,t,h) = sigma(j,h) * clip(sum_i[a(i,t,h) * z(i,t,h)] / max(1, sum_i M(i,t)), -kappa(h), kappa(h))`

`r_hat(j,t,h) = F(j,t,h) + delta(j,t,h)`

`P_hat(j,t,h) = P(j,t) * exp(r_hat(j,t,h))`

These equations keep the adjustment in log-return units. When all blocks are unavailable, `delta = 0` and the baseline is preserved. One policy may emit actions for all horizons, but each horizon has its own scale, target, and score. A bounded correction reduces the risk of one noisy or incorrectly oriented news item overwhelming the baseline.

The observation transition advances to the next available prediction time; the policy's action changes its internal previous-adjustment state and future reward, not market prices. Delayed future prices provide training feedback only once their horizon has matured. Use a normalized forecast reward such as:

`reward(j,t,h) = -((r(j,t,h) - r_hat(j,t,h)) / sigma(j,h))^2 - lambda * (delta(j,t,h) / sigma(j,h))^2 - gamma * ||a(t,h) - a(t-1,h)||^2`

Choose `lambda`, `gamma`, and `kappa` on training/validation windows only. The first term scores return accuracy, the second limits unsupported corrections, and the third discourages unstable switching. Record price error and interval accuracy separately. Reward is calculated after the corresponding target matures; no reward or weight update may use future outcomes at an earlier decision time.

Because market transitions are exogenous to these forecast actions, this is close to a sequential contextual decision problem. PPO or SAC remains an *experimental* policy option, not an assumed superior choice. First compare the same bounded adjustment with a regularized supervised fusion model. Train the MDP policy only if there are sufficient real, timestamped news observations and an untouched period on which it can be judged. Mock JEV vectors can validate interfaces and reward bookkeeping, never predictive value.

## 5. Data and evaluation plan

The completed MTS pipeline covers January 2025 through the available part of November 2026. It already stores raw-response hashes, native candles, five derived timeframes, past returns, and observed gaps. It has no historical real-time JEV block archive, verified bid/ask quotes, or MTS volume. The 2026 daily-return standard deviation was about 1.9 times 2025's, so an average over both years can hide regime failure. The two purity series have about 0.99983 matched daily-return correlation; do not count them as independent evidence.

Build forward labels and a point-in-time feature table first. Freeze validation windows chronologically. A first experiment may fit on 2025 and evaluate on available 2026, then run walk-forward folds with an embargo at least as long as each future target horizon. Keep a final untouched test period after all architecture and threshold selection. Group uncertainty estimates by time blocks because overlapping multi-horizon labels are dependent. Evaluate separately by symbol, horizon, year, volatility regime, and news-present versus news-absent periods.

Compare in order: (A) no-change price forecast / zero return; (B) quantitative-only linear and boosted models; (C) quantitative model plus a simple supervised JEV fusion; (D) the bounded MDP policy. Where direct inputs exist, also compare an XAU/USD × USD/THB conversion baseline with a premium estimated only from prior data. Require each extra stage to improve an untouched evaluation set, not merely training loss.

Primary scores: return MAE/RMSE and skill relative to the zero-return baseline, price MAE in THB and percentage terms, and directional accuracy excluding a declared near-zero band. If forecasting intervals, use pinball loss, empirical coverage and interval width. Report uncertainty intervals for differences between models; do not infer significance from overlapping row counts. Record missingness, stale-feature rate, source revisions, and label availability beside forecast scores. A good price forecast is not automatically an executable trading strategy.

## 6. Staged implementation and acceptance

1. Extend the current collection pipeline with forward-label construction, source calendar checks and a feature-availability audit. Preserve the existing 2025–2026 raw archive and manifest.
2. Build numerical-only baselines. Produce out-of-time metrics for all five horizons and both MTS symbols before adding text or an MDP.
3. Define and version the five JEV questions, score real time-stamped historical text when available, assess score direction and confidence, and quantify the incremental benefit of each block. Use mocked scores solely for software tests.
4. Build simple bounded supervised fusion and test whether it beats the numerical-only model on the same untouched dates.
5. Implement the MDP environment and only then compare a constrained PPO/SAC policy against the supervised fusion on the same frozen data. Include zero-news, wrong-direction news, delayed-news and source-outage tests. Retain the simpler model if the policy does not improve out-of-time forecast quality consistently.
6. Publish forecast artifacts with model/version IDs, valid timestamps, point estimates, optional intervals, source coverage and data-freshness status. Monitor drift, error by horizon, and news-block contribution. Retrain or suspend a model according to predeclared thresholds.

No training or forecast-skill claim is made by this document. Permission to score text, use a model in Tidewatch, or trade would be addressed by separate implementation and review decisions.

## Appendix: early warning and future leading indicators

The proposed sentiment-block rate-of-change and acceleration features remain research hypotheses. Normalize them for irregular event arrival and source coverage, require enough observations, and compare against simple event-count changes and raw scores. Test whether any improvement precedes the MTS price move instead of merely describing news after the move. Expected gold volume remains out of scope until an observed, licensed volume series with stable units and publication timestamps exists.
