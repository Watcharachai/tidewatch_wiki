# Elliott and regime labeller (`internal/market/waves`)

**Summary**: Since charting (slice 5; tidewatch-service #11, merged 2026-10-16 as `1547a89`, not deployed), one pure, deterministic Go package in the service labels price series. It finds zigzag pivots on closes, proposes at most two Elliott candidate counts (impulse 0–5 or corrective A–B–C), each with a *fit* and an invalidation level, adds Fibonacci retracements for impulses, and names a regime (trend, volatility and `atr_pct`). All arithmetic is exact (`big.Rat` on the stored decimal text). Every constant lives in one `Tunables` table, and five byte-pinned fixtures fix the answers. The same functions serve the chart route and the signal detail's context. **Since slice 6 (tidewatch-bot #10, merged 2026-10-21, not deployed), the bot has its own port, `packages/waves`,** which is byte-identical to the service on all five fixtures; the fixtures and tunables are now shared contract **C13**. The general bot engine writes its `elliott` and `regime` into each decision's `market_state` and uses the first bullish candidate's invalidation as a candidate's `invalidation_px`. A change to any tunable is a fixture and contract change, made in the service and the bot at once. The number is called *fit*, never probability, and the sentence *Candidate counts are not forecasts.* always travels with it.

**Sources**: `raw/2026-10-16-charting.md`; `raw/2026-10-21-bots.md` (the bot port and its uses)

**Last updated**: 2026-10-21

---

## Why one implementation in the service (D3, D4, D5)

- **D3.** Elliott and regime are computed by the service, on read, in one deterministic Go implementation. It serves the chart (see [[chart-read-api]]) and the Signals detail (see [[signals-read-api]]). Slice 6's bot ports the labeller against the same committed fixtures. A web-only labeller was rejected, because it would leave the Signals lines unfilled.
- **D4.** The fixtures have answers known by construction: three synthetic series built from chosen pivots, plus two real captured series on which only the hard rules and the invalidation rule are checked. Owner hand-labelling was rejected, because it would block planning or gate acceptance on owner work.
- **D5.** Impulse and corrective candidates, the top two by fit. The number is *fit*, never probability.
- **Stored zones only.** The labeller reads stored bars and `indicators` rows. CDC zones are never recomputed on read; that is why 4h was deferred (D2, see [[market-timeseries]]).

(source: raw/2026-10-16-charting.md §Concept, Owner decisions (intent, 2026-10-14))

## The `elliott` object (contracts r2 §3)

```json
{"timeframe":"1h","threshold_pct":"2.5","as_of":"2026-10-14T05:00:00Z",
 "pivots":[{"ts":"2026-09-30T14:00:00Z","price":"171.2000","kind":"low"}, …],
 "candidates":[{"id":"impulse-5","kind":"impulse","stage":"Impulse, in wave 5","direction":"up","fit":"0.58",
   "points":[{"label":"0","ts":"…","price":"171.2000","forming":false}, …, {"label":"5","ts":"…","price":"189.1000","forming":true}],
   "invalidation":{"price":"183.4000","side":"below","wave":"4"},
   "fibonacci":{"from":"171.2000","to":"185.9000","levels":[{"ratio":"0.382","price":"180.2846"},{"ratio":"0.5","price":"178.5500"},{"ratio":"0.618","price":"176.8154"}]}}],
 "sentence":"Candidate counts are not forecasts."}
```

**Ids, kinds and stage words** (exact, with a U+2013 en dash):

| id | kind | stage |
|---|---|---|
| `impulse-complete` | impulse | "Impulse, complete 0–5" |
| `impulse-5` | impulse | "Impulse, in wave 5" |
| `impulse-3` | impulse | "Impulse, in wave 3" |
| `corrective-complete` | corrective | "Corrective A–B–C, complete" |
| `corrective-c` | corrective | "Corrective A–B–C, in wave C" |

**Field rules.**
- `fit` is a string with exactly two decimals, in `["0.30", "1.00"]`.
- A forming point carries the newest closed bar's `ts` and close, with `forming: true`.
- `invalidation.wave` is `4`, `2` or `B`. `side` is `below` (bullish) or `above` (bearish).
- `fibonacci` is `null` for a corrective.
- `sentence` is always exactly "Candidate counts are not forecasts."

(source: raw/2026-10-16-charting.md §API, The `elliott` object and the labeller)

## The algorithm (pinned; the bot port follows it)

All arithmetic is exact: `big.Rat` on the stored decimal text, with no floating point in the package.

- **W1, zigzag on closes.** The first `c[i]` at least `t` from `c[0]` sets the direction. A move of at least `t` against the extreme confirms a pivot. Pivot 0 is bar 0. A provisional final pivot is added only when the extreme is not the last bar. Fewer than three pivots means no candidate, and the service logs `waves_input_too_short` at debug.
- **W2, hypotheses** over the newest pivots, using `C` (the newest closed close) as a forming point where needed.
- **W3, rules.** Each present wave moves in its own direction.
  - R1: `q2 > q0`.
  - R2: `|p3−p2| ≥ min(|p1−p0|, |p5−p4|)`, with the forming 5 counting; only `> 0` for `impulse-3`.
  - R3: `q4 > q1`.
  - Corrective: `qA > q0`, `q0 < qB < qA`, and `qC > qA` for a complete count or `qC > qB` for in-wave-C.
- **W4, invalidation.** The level is point 4, 2 or B. A candidate is dropped when `q(C) ≤ q(invalidation)`.
- **W5, fit** `= 0.30 + 0.70 × mean(max(0, 1 − |r − ideal| / tolerance))`, rounded half away from zero to two decimals. The (ideal, tolerance) pairs are r2 (0.5, 0.5), r3 (1.618, 1.0), r4 (0.382, 0.4), r5 (1.0, 0.8), rB (0.5, 0.5) and rC (1.0, 0.8).
- **W6, ranking.** By two-decimal fit, then complete before forming, then impulse before corrective, then `impulse-5` before `impulse-3`. The first two are returned.
- **W7, Fibonacci.** Impulse only, on the leg 0→5, 0→3 or 0→1: `price = to − (to − from) × ratio`.

(source: raw/2026-10-16-charting.md §API, The `elliott` object and the labeller, Algorithm)

**Gap fills the owner accepted as a set (CH-OD-2, 2026-10-14).** These filled holes in the PRD, and the fixtures pin them:
- `atr_pct = 100 × atr14 ÷ close`, to two decimals.
- A corrective *in wave C* needs only that C has moved from B in its own direction. "Beyond A's end" applies to the complete corrective.
- The Fibonacci leg of an *in wave 3* count is 0→1.
- A forming 5 counts as present in R2.
- "A moves against the prior trend" holds vacuously when point 0 is the first pivot.
- Ranking uses the two-decimal fit.

(source: raw/2026-10-16-charting.md §Concept, Decisions taken during the build, CH-OD-2)

## The `Tunables` table (`waves.Tunables`, `tunables.go`)

Every constant is held as decimal text:
- `ThresholdPct`: 15m `"1.2"`, 1h `"2.5"`, 1d `"6"` (PD7).
- The six fit `Ideal`s above.
- `FitBase "0.30"`, `FitWeight "0.70"`, `FitDecimals 2`.
- `MaxCandidates 2`.
- `FibonacciRatios ["0.382", "0.5", "0.618"]`.
- `TrendATRMultiple "0.25"`, `VolPercentile 80`, `VolLookback 100`, `MinATRRows 20`, `ATRPctDecimals 2`.

**Changing a value is a fixture and contract change, made in the service and the bot at once.** Tuning the thresholds and percentiles after the owner has seen the fixtures is deferred by design (source: raw/2026-10-16-charting.md §API, The `Tunables` table; §Open questions, Deferred by design).

## The regime rule (contracts r2 §4)

`{"trend": "up" | "down" | "range", "vol": "normal" | "high", "atr_pct": "0.83"}`, or `null`.
- **R** is the newest closed bar whose row has finite `ema12`, `ema26` and `atr14`. The population is the finite `atr14` values of the newest ≤ 100 closed bars, up to and including R.
- **Null** when there is no R or fewer than 20 values.
- **Trend** is `up` when `ema12 − ema26 > 0.25 × atr14`, `down` when `ema26 − ema12 > 0.25 × atr14`, else `range`.
- **Vol** is `high` when `atr14 ≥` the nearest-rank 80th percentile, else `normal`.
- **`atr_pct`** is `100 × atr14 / R's close`, rounded to two decimals.
- **Web words:** "Trend up, normal vol", "Trend down, high vol", "Range, normal vol".

The EMA and ATR inputs are the stored CDC indicator values on [[market-timeseries]] (source: raw/2026-10-16-charting.md §API, Regime (contracts r2 §4)).

## Where it runs

| Caller | Timeframe | Input bars | Notes |
|---|---|---|---|
| `GET /instruments/{id}/chart`, head read | The chart's timeframe | The closed bars among the newest 1,000 read, whatever `limit` is (CH-OD-1) | Returns the full `elliott` object and `right_now.regime`. `elliott` is null on an earlier read or with no closed bar. See [[chart-read-api]] |
| `GET /signals/{id}`, `context` | The strip timeframe (`context.timeframe`) | `ChartRepo.Bars(strip timeframe, created_at − timeframe, 500)`, every bar with `ts + timeframe ≤ created_at`, eod bars included (CH-R6) | Returns only the first ranked candidate's `{stage, direction, fit, invalidation}`, and the regime. No look-ahead. See [[signals-read-api]] |

- **No look-ahead on the detail (CH-R6).** The "an eod bar is always closed" rule of the chart holds only at `generated_at`. The detail applies `ts + timeframe ≤ created_at` to every bar, so for a daily-strip instrument a session dated on or after `created_at`'s UTC day is never read.
- **Cost.** The analysis is linear in bars. The detail now reads ≤ 500 bars and runs the `big.Rat` analysis per request, which security review r1 accepted as a fixed, linear cost.

(source: raw/2026-10-16-charting.md §API, `GET /instruments/{id}/chart` and The signal detail's new context keys; §Concept, Planner reconciliations, Service CH-R6)

## The five fixtures (`internal/market/waves/testdata/`)

Each fixture directory holds `series.csv` (`ts,o,h,l,c`, LF, oldest first) and `expected.json`. `TestWaves_FixtureHashes` pins the SHA-256 of every file except the README, which derives the constructed answers by hand. The fixtures are byte-pinned like contracts C10 and C11 (CH-R9; see [[bot-watch-verdicts]]).

| Directory | Kind | Content and expected answer |
|---|---|---|
| `impulse-up-wave5` (1h, 2.5 %) | constructed, 47 bars | Pivots 100, 120, 110, 145, 132 and C = 140. Returns `impulse-5` at fit **0.84** and `corrective-c` at **0.57**; `impulse-3` (0.56) is cut by ranking. Invalidation 132.00 below. Fibonacci 0→3: 127.81 / 122.50 / 117.19 |
| `bear-impulse-then-c` (1d, 6 %) | constructed, 59 bars | A bearish impulse 200-160-180-110-130-100, then a correction 100-125-112 with C = 121. Returns `corrective-c` at **0.71** and `impulse-3` at **0.64**; `impulse-complete` is dropped by R3 and `impulse-5` by R1. Invalidation 112.00 below. Fibonacci 0→1: 115.45 / 112.50 / 109.55 |
| `no-valid-count` (15m, 1.2 %) | constructed, 41 bars | Wave 4 overlaps wave 1: `candidates: []`, with pivots still returned |
| `nvda-1h` | real, 300 rows | `NVDA@webull` `candles_1h` from 2026-09-17T13:00Z to 2026-10-14T08:00Z. Rule checks only: `pivots_alternate`, `at_most_two`, `points_are_pivots`, `hard_rules`, `invalidation_side`, `fit_range` |
| `btcthb-1h` | real, 300 rows | `BTCTHB@binance-th` from 2026-10-01T21:00Z to 2026-10-14T08:00Z. The same checks. Its newest bar is about 17.7 h before the capture, because ingestion into that database copy had stopped |

- **The real series** were captured at 2026-10-15T01:41:16Z from the retained preview database, read-only, with the query recorded in the README. They were copied byte for byte and verified with `cmp` against the orchestrator's captures. Engineers have no database access, and no repository file contains the word "preview" (CH-R8). How the capture ran is on [[forge-preview-gateway]].
- **An independent checker** in `waves_test.go` parses the real series with `big.Rat.SetString`, not the package's parser.

(source: raw/2026-10-16-charting.md §API, The five fixtures; §Concept, Planner reconciliations, Service CH-R8/CH-R9)

## Verification

- **Unit tests:** `TestWaves_Fixtures` (five subtests, one per fixture), `TestWaves_Deterministic`, `TestWaves_FixtureHashes`, `TestWaves_Regime`, `TestZigzag_Pivots`, `TestElliott_HardRules`, `TestElliott_FitAndRanking` and `TestElliott_Fibonacci`, plus `TestAnalyze_Inputs`, `TestTunables_Table` and `TestDecimal_Rounding`.
- **By hand.** Code review r1 re-derived `impulse-up-wave5`: fits 0.84 and 0.57, Fibonacci 127.81 / 122.50 / 117.19.
- **On real data (FR-CH-E2E-005, passed).** Round 1 read the chart route 33 times (11 instruments × 3 timeframes): 28 candidates in 17 pairs and 265 checks. An independent exact re-implementation (`waves.mjs`) was identical on all 26 non-empty pairs. Round 2 found 37 candidates in 21 pairs, and the drawn points equalled the first candidate in all 21.
- FR-CH-SVC-003 and FR-CH-SVC-004 passed.

(source: raw/2026-10-16-charting.md §Test plan, Named acceptance tests and Acceptance status)

## How the web shows it

- **Shared words.** `pages/workspace/util/elliott-words.ts` holds the words both the chart and the Signals detail use, so they cannot drift (CH-W-20). The strict readers live in the leaf module `data/elliott.model.ts`.
- **Chart.** The *Elliott, candidate counts* panel shows the fixed sentence, then at most two toggle buttons, "{stage} … fit {fit}"; the pressed one is drawn in `--brand`. Under them: "Invalidates if price closes below the wave 4 low, 183.40." Fibonacci is off by default and independent of the count. See [[charting]] and [[design-system-decisions]].
- **Signals detail.** *Elliott* reads "{stage} · fit {fit} · invalidates {below|above} {price}", and *Regime* reads the regime words. A null key reads "No candidate count" or "Not enough history" (see [[signals-page]]).
- **Rounding follow-up.** Levels go through `formatPrice` at the tick size (CH-OD-4), so GOLD965THB 1D 71,975.88 reads "71,976". Using the stored precision is an open web follow-up.

(source: raw/2026-10-16-charting.md §Components, Signals detail rows and The Chart screen; §Open questions, Web follow-ups)

## The bot's port: `packages/waves` (slice 6, C13)

Slice 6 (owner decision D7, FR-BT-BOT-012) ported the labeller to the bot, because the bot cannot call the service and needs Elliott and regime facts for its own decisions (see [[bots-engine]]).

- **The package.** A pure Nx library, `@tidewatch-bot/waves`, with a `BigInt` rational type (so the arithmetic stays exact, as `big.Rat` is in Go), zigzag, `analyze`, `computeRegime` and `TUNABLES`. No I/O and no runtime dependency.
- **C13, the shared fixtures.** The five fixture directories and `waves-tunables.v1.json` were copied into `packages/waves/fixtures/` with `cp` and are hash-pinned. The service gained `internal/market/waves/testdata/waves-tunables.v1.json`, pinned by `TestWaves_TunablesFixture`; the `waves` code and its five series are unchanged by design. A change to a tunable is therefore a contract change in both repositories at once.
- **The A1 gate.** `waves:test` passed 84/84, and an extra Go cross-check found the bot's JSON output byte-identical to the service's on all five fixtures. This was green before any engine step began.
- **Where the bot uses it.**
  - The scout writes `market_state.elliott` and `market_state.regime` on the manager timeframe into every decision (the slots were empty before slice 6; see [[decision-record]]).
  - A candidate's `invalidation_px` is the first ranked bullish candidate's invalidation, else `close − stop_atr × atr14`.
  - The manager's `elliott_filter` gate and the `elliott_wave2_holding` entry condition (D4) read it; the editor offers *Elliott* as filter, feature or off.
  - The Trade recommendation's fourth reason is the Elliott or regime line (see [[signal-cited-orders]]).

(source: raw/2026-10-21-bots.md §The bot engine, `packages/waves`, Scout and Manager; §Concept, Owner decisions D4/D7; §Files touched, tidewatch-service S1 and tidewatch-bot S1–S3; §Test plan, Named acceptance tests)

## What comes next

- **Slice 6 (done, 2026-10-21):** the bot ported the labeller against these fixtures, and bots read the Elliott invalidation and the regime (see above and [[bots]]).
- Tuning the thresholds and percentiles, and owner hand-labelled series as extra fixtures, are deferred by design.

(source: raw/2026-10-16-charting.md §Open questions, Deferred by design)

## Related pages

- [[charting]]: the slice-5 overview and the Chart screen that draws the candidates
- [[chart-read-api]]: the chart route and its analysis window
- [[signals-read-api]]: the detail's `elliott` and `regime` context keys, computed at `created_at`
- [[market-timeseries]]: the stored bars and `ema12`, `ema26`, `atr14` the labeller reads
- [[bot-watch-verdicts]]: contract C11, the byte-pinned fixture pattern these fixtures follow
- [[signal-message-contract]]: C-SIG-1, another cross-repo byte-pinned contract
- [[zone-transition-bot]]: the 2b bot side, which the slice-6 general engine sits beside
- [[bots-engine]]: the general engine that writes the ported labeller's facts into decisions
- [[bots]]: slice 6, which shipped the port as contract C13
- [[forge-preview-gateway]]: how the two real series were captured from the retained preview database
