# Chart read API (`GET /instruments/{id}/chart`)

**Summary**: Since charting (slice 5; tidewatch-service #11, merged 2026-10-16 as `1547a89`, not deployed), one gated route serves everything the Chart screen draws. It returns bars already LEFT JOINed with their `indicators` rows, a `right_now` block built exactly like the Market watch row, up to two Elliott candidate counts and the regime from [[elliott-regime-labeller]], and Slack Water's latest watch verdict as the `stance`. A head read analyses the closed bars among the newest 1,000 whatever `limit` asks for, so a short re-read returns the same overlays. An earlier read (`to`) returns bars only. The route writes nothing, creates nothing and adds no error code. Its sibling, the instrument-scoped signal read `GET /instruments/{id}/signals`, is on [[signals-read-api]].

**Sources**: `raw/2026-10-16-charting.md`; `raw/2026-10-29-accounts-roles.md` (the gate's role only)

**Last updated**: 2026-10-29

---

## Gate chain and conventions

These rules are contracts r2 §1, shared by both slice-5 routes.
- Both routes mount on the gated market group through `mountChart` in `internal/app/router.go`: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles, 2026-10-29; see [[accounts-and-roles]]) (see [[auth-model]]). They are GETs, so no CSRF header is needed.
- `TestRouter_ForcedChangeGatesNewRoutes` now counts **45** gated routes (42 production + 3 test probes), up from 43.
- **Queries are strict** (`parseQuery`). An unknown, repeated (`duplicate`) or unparsable parameter is `400 invalid_request` with `details.field`.
- **Bodies** are snake_case. Instants are RFC 3339 UTC. Absent values are `null`, never omitted.
- **Decimals are strings.** Candle prices and volume are the stored numeric text (`"182.10"`). Indicator values are the stored double written shortest (`strconv.FormatFloat(f, 'f', -1, 64)`). NaN or Inf is `null` and logs `indicator_value_not_finite`.
- **Zones:** `buy`, `pre_buy_2`, `pre_buy_1`, `pre_sell_1`, `pre_sell_2`, `sell` or `null`.
- **The closed rule.** A bar is closed at T when it is an eod bar or `ts + timeframe ≤ T`. On the chart route, T is `generated_at`.
- **No new error code.** `unknown_instrument` (404) and `timeframe_unavailable` (422) are reused; only their "When" text in the README error table changed. `TestCodes_Contract` passes.

(source: raw/2026-10-16-charting.md §API, Conventions (contracts r2 §1))

## Request and errors

| Query | Rule |
|---|---|
| `timeframe` | Required: `15m`, `1h` or `1d`. `1m`, `5m`, `4h` and anything else are `400` |
| `limit` | 1–5000, default 1000 |
| `to` | Optional instant. Without it the call is a head read; with it, an earlier read |
| any other parameter | `400`, `from` included |

Errors come in this order: `400` for the query; `404 unknown_instrument` for a malformed or unknown id; `422 timeframe_unavailable` for `15m` or `1h` on a `1d` base (see [[instrument-master]]). An instrument with no bars answers `200` with `bars: []` (source: raw/2026-10-16-charting.md §API, Conventions, route table).

## Head read and earlier read

- **Head read (no `to`).** Reads `max(limit, 1000)` bars at or before `generated_at`, in one statement.
- **Earlier read (`to` set).** Reads `limit` bars at or before `to`. `right_now`, `elliott` and `stance` are all `null`, and an empty `bars` means there is nothing earlier.
- **`bars`** holds the newest `limit`, oldest first. Each bar carries `ts, o, h, l, c, v, ema12, ema26, cdc_zone, atr14, closed`. All four indicator values are `null` when the row is missing.
- **`last_is_partial`** is true when the last bar is not closed.
- **Analysis window (owner decision CH-OD-1).** `right_now`, `elliott` and the regime use the closed bars among the newest 1,000 read. So `limit=8` gives the same overlays as a default read (`TestService_Chart_AnalysisWindow`). The web's 65 s / 180 s `limit=8` re-read after a bucket closes relies on this (see [[charting]]).

(source: raw/2026-10-16-charting.md §API, `GET /instruments/{id}/chart`; §Concept, Owner decisions CH-OD-1)

## `right_now` (head read only)

- **Zone run (CH-R2/CH-R3).** `zone`, `zone_age` and `zone_since` come from the trailing run over the newest ≤ 48 closed bars **whose indicator row exists**, following Market watch's row rule. `zone_age` is an integer, `0` with no zone.
- `ema12`, `ema26` and `atr14` come from that newest row. `regime` is computed on the chart timeframe.
- **Copied from Market watch.** `last {price, ts}`, `change_24h {reference_price, reference_ts, abs, pct}` and `status {mode, stale, session, next_open_at, delay_minutes}` are exactly the Market watch row's at `generated_at` (see [[market-data]]). The service builds them with Market watch's own row builder. Since RF1 it calls it as `(*MarketWatchService)(nil).row(...)`, so a field read would panic in tests instead of drifting silently (code review r1's should-fix).
- **The 60 s gap.** In the ≤ 60 s before the bot writes a closed bucket's row, the newest closed bar has `cdc_zone: null` while `right_now.zone` still reads the previous row, as Market watch does.

(source: raw/2026-10-16-charting.md §API, `GET /instruments/{id}/chart`; §Concept, Planner reconciliations, Service CH-R2/CH-R3; §Concept, Review history)

## `elliott` and `stance` (head read only)

- **`elliott`** is the labeller's object on the chart timeframe: pivots, at most two candidates and the fixed sentence (see [[elliott-regime-labeller]]). It is `null` only on an earlier read or when the window has no closed bar (CH-R11).
- **`stance`** is `{bot_id, bot_name, bot_status (running|observing|paused), verdict (one of the fourteen C11 values), rule (entry|exit|null), reasons[], timeframe, zone, zone_age, zone_run_started_at, held, pending_order, baseline_at, evaluated_at, decision_id, order_id}`, or `null`. It is the `bot_watch` row for this instrument of the session user's oldest `auto`/`zone_transitions` bot, the same bot `systemBots` picks (CH-R10). The route never creates a bot, account or watchlist (`TestChart_Stance_ScopedAndNoCreate`). See [[bot-watch-verdicts]].

(source: raw/2026-10-16-charting.md §API, `GET /instruments/{id}/chart`; §Concept, Planner reconciliations, Service CH-R10/CH-R11)

**Head read example** (contracts r2 §2, abridged):

```json
{"instrument_id":"NVDA@webull","timeframe":"1h","generated_at":"2026-10-14T06:12:09.418Z","base_timeframe":"1m","strip_timeframe":"1h",
 "bars":[{"ts":"2026-10-14T05:00:00Z","o":"188.4000","h":"189.3000","l":"188.1000","c":"189.1000","v":"802311",
          "ema12":"186.2214","ema26":"182.9071","cdc_zone":"buy","atr14":"1.5631","closed":true},
         {"ts":"2026-10-14T06:00:00Z","o":"189.1000","h":"189.4000","l":"188.9000","c":"189.2500","v":"120344",
          "ema12":null,"ema26":null,"cdc_zone":null,"atr14":null,"closed":false}],
 "last_is_partial":true,
 "right_now":{"zone":"buy","zone_age":11,"zone_since":"2026-10-13T18:00:00Z","ema12":"186.2214","ema26":"182.9071","atr14":"1.5631",
              "regime":{"trend":"up","vol":"normal","atr_pct":"0.83"},
              "last":{"price":"189.2500","ts":"2026-10-14T06:12:01Z"},
              "change_24h":{"reference_price":"185.7000","reference_ts":"2026-10-13T06:12:00Z","abs":"3.5500","pct":"1.9117"},
              "status":{"mode":"live","stale":false,"session":"open","next_open_at":null,"delay_minutes":null}},
 "elliott":{…},
 "stance":{"bot_name":"Slack Water","bot_status":"running","verdict":"holding","rule":null,"reasons":[],"timeframe":"1h",…}}
```

(source: raw/2026-10-16-charting.md §API, Head read example)

## The database reads

**No schema change, migration, index or write.** Every field read exists at migration I, and there is no `4h` relation (D2).

**The joined read (`internal/repository/postgres/chart.go`).** `ChartRepo.Bars` picks one statement from a closed map: `15m` → `candles_15m`, `1h` → `candles_1h`, `1d` → `candles_daily`, where the eod flag is `source <> 'aggregate'`. Each statement is built only from constant relation names, eod expressions and timeframe literals. The parameters are the instrument id, an upper `ts` bound and a row count. `TestChartRepo_Statements` pins the map.

```sql
SELECT b.ts, b.o::text, b.h::text, b.l::text, b.c::text, b.v::text, b.eod,
       ind.ts IS NOT NULL, ind.ema12, ind.ema26, ind.cdc_zone, ind.atr14
FROM (
    SELECT ts, o, h, l, c, v, <eod expr> AS eod
    FROM <candles_15m | candles_1h | candles_daily>
    WHERE instrument_id = $1 AND ts <= $2
    ORDER BY ts DESC
    LIMIT $3
) b
LEFT JOIN indicators ind
  ON ind.instrument_id = $1 AND ind.timeframe = '<15m | 1h | 1d>' AND ind.ts = b.ts
ORDER BY b.ts
```

**The stance read.** One statement selects the session user's oldest `kind = 'auto' AND template = 'zone_transitions'` bot (by `created_at`, then `bot_id`) and `CROSS JOIN LATERAL`s its `bot_watch` row for the instrument. `owner_user_id = $1` is in the bots filter, so another user's bot or rows are never read. It returns no row when there is no zone bot or no row for the instrument. The chart code contains no `INSERT`/`UPDATE`/`DELETE` and no `EnsureBots`/`EnsureAccount` call; the S2 verification greps for both.

**Assumptions that held.**
- **A1:** the `1d` indicator `ts` equals `candles_daily.ts`. `TestChart_Read_JoinsIndicators` covers an eod 1d instrument.
- **A5:** one statement for 5,000 rows stays under the query timeout. EXPLAIN ANALYZE ran read-only on the preview database, with the `chartSQL` text, `NVDA@webull`, a bound `now()` and `n = 5000`, on service `51e40c2`:

| Timeframe | Rows | Planning | Execution | Plan |
|---|---|---|---|---|
| 1h (`candles_1h`) | 2,010 (all available) | 4.1 ms | 12.1 ms (first run, colder cache) | ChunkAppend with bitmap index scans on `(instrument_id, ts)` per chunk; `indicators` primary-key index scans |
| 15m (`candles_15m`) | 5,000 (of 8,039) | 4.4 ms | 4.3 ms | same shape |

At integration level (S2), a 1,000-bar 15m read took 113 ms at the client, with a logged `duration_ms` of 34.958.

(source: raw/2026-10-16-charting.md §Database)

## Compatibility, load and logs

- **New web on an old service.** Both new routes answer `404 not_found` (an unmatched path), and the chart shows its error state ("Chart couldn't load."), never the unknown state.
- **Old web on the new service.** It ignores the two new signal-detail context keys.
- **Load bound.** A chart read is bounded by `limit ≤ 5000`, and the analysis reads at most `max(limit, 1000)` rows. The labeller is linear in bars, and the repository query timeout applies.
- **Logs.** `chart_read` at debug once per read (`instrument_id`, `timeframe`, `bars`, `candidates`), and `waves_input_too_short` at debug when the labeller has fewer than three pivots (`instrument_id`, `timeframe`, `pivots`). No new metric. The S5 orchestrator prompt wrongly said `duration_ms`; the engineer followed the contract, which has no such field.
- **Rollout.** Deploy the service before the web. Reverting the service removes both routes and the two context keys; nothing is stored.

(source: raw/2026-10-16-charting.md §API, Errors, compatibility and logs; §Concept, Operations)

## Tests and code layout

- **Unit:** `TestChartRepo_Statements`, `TestService_Chart_AnalysisWindow`, `TestService_Chart_RightNowRows`, `TestService_Chart_EarlierReadNulls`, `TestService_Chart_Logs`, `TestChartHandler_Query` and `TestChartHandler_Body`.
- **Integration:**
  - `TestChart_Read_JoinsIndicators`: 15m, 1h and an eod 1d instrument; strings, nulls for missing rows, `closed`, `last_is_partial`, `elliott` equal to `waves` on the returned closed bars, and the timing.
  - `TestChart_Read_EarlierPage` and `TestChart_Read_Errors`.
  - `TestChart_RightNow_MatchesMarketWatch`: BTCTHB, NVDA with `px:last`, and PTT.BK; a late indicator row; identical overlays at `limit=8`.
  - `TestChart_Stance_ScopedAndNoCreate`: null without a zone bot or row; nothing created; another user's row invisible; a paused bot shown.
- **Revised on purpose:** `TestRouter_ForcedChangeGatesNewRoutes` (43 → 45).
- **Code.** New `internal/repository/postgres/chart.go`, `internal/services/market/chart.go` and `internal/handlers/chart.go`. A new handler file keeps `instruments.go` byte-identical (CH-R12). `marketwatch.go`, `query.go`, the candle, indicator, marketwatch and bot repositories, the market services, and `internal/market/{timeframe,zone,decimal}.go` were verified byte-identical with the base. `api-spec-generator` was not run (CH-R13).

(source: raw/2026-10-16-charting.md §Test plan, Named acceptance tests; §Files touched, tidewatch-service; §Concept, Planner reconciliations, Service)

## Follow-ups

- Make `MarketWatchService.row` a free function when `marketwatch.go` is next opened.
- `chartRows` renders and logs `indicator_value_not_finite` per value on every head read (≥ 1,000 rows). Log once per read, or render only the returned rows plus the window.
- Share one bars → `waves.Bar` conversion between `services/market/chart.go` and `services/signals/detail.go`.

(source: raw/2026-10-16-charting.md §Open questions, Service follow-ups)

## Related pages

- [[charting]]: the slice-5 overview, the Chart screen and acceptance
- [[elliott-regime-labeller]]: the `elliott` object and the regime rule this route returns
- [[signals-read-api]]: the sibling `GET /instruments/{id}/signals`, and the detail's `elliott` and `regime`
- [[market-timeseries]]: the `candles_*` relations, `candles_daily` and the `indicators` rows joined here
- [[market-data]]: the Market watch row whose `last`, `change_24h` and `status` `right_now` copies
- [[bot-watch-verdicts]]: the `bot_watch` row and C11 verdict behind `stance`
- [[zone-transition-bot]]: Slack Water, the oldest `auto`/`zone_transitions` bot
- [[instrument-master]]: `base_timeframe` and the reused `timeframe_unavailable`
- [[auth-model]]: the gate chain, the 45 gated routes and the owner-scoped stance
- [[centralized-migrations]]: no migration; the route reads only what migration I already has
