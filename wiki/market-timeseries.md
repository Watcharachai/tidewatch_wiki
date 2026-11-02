# Market time series, aggregates and CDC indicators

**Summary**: How Tidewatch stores and derives price history: `candles` for intraday bars with 180-day retention, `candles_eod` for daily-native bars kept forever, three real-time continuous aggregates, the `candles_daily` view, and the `indicators` hypertable fed by the CDC ActionZone rules in `packages/indicators`. Includes the refresh rules that stop aggregates from silently losing history. Since slice 2b, the strip-timeframe `cdc_zone` is also the only trigger of the zone-transition bot. Since slice 4 (the signals page), the service also reads strip rows and the daily `atr14` to show each signal's market context and to count signals "contradicted by price". Since charting (slice 5, merged 2026-10-16, not deployed), the Chart reads `candles_15m`, `candles_1h` and `candles_daily` LEFT JOINed with `indicators` by primary key, and colours each candle by its own bucket's stored `cdc_zone`. The service derives Elliott counts and a regime from the stored closes, EMAs and ATR, and never recomputes a zone. There is still no 4h bar or indicator row.

**Sources**: `raw/2026-10-07-market-data.md`; `raw/2026-10-07-fix-xau-feed-binance-th.md`; `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-16-charting.md`; `raw/2026-10-30-signals-context.md` (the two context hypertables only)

**Last updated**: 2026-10-31

---

## The storage split (MD4, MD14)

- `candles` holds intraday bars only: 7-day chunks, columnstore after 30 days, retention 180 days.
- `candles_eod` holds daily-native bars with no retention, so retention can never delete daily history.
- Each instrument has a `base_timeframe` and a `daily_source` (`aggregate` or `eod`); `candles_daily` picks the daily source per instrument (see [[instrument-master]]).
- MD14: the intraday backfill depth equals the 180-day retention. Longer daily history comes from `candles_eod` or `candles_1d`.
- Since the XAU fix, the Binance TH collector stores bars only inside the instrument's calendar session, so `candles` holds no `XAUUSD@oanda-demo` rows on Saturday New York, after the Friday 17:00 close or in the weekday 17:00–18:00 break, while the collector cursor still advances across the gated minutes. The check is `SELECT count(*) FROM candles WHERE instrument_id='XAUUSD@oanda-demo' AND extract(isodow FROM ts AT TIME ZONE 'America/New_York') = 6`, which must be 0 (see [[gold-feed-xaut-proxy]]).

(source: raw/2026-10-07-market-data.md §Concept, MD4 and MD14; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Caller-visible implications; §Test plan, Manual reproduction)

## Objects (migration B)

| Object | Settings |
|---|---|
| `candles` (on `ts`) | PK `(instrument_id, ts)`; `numeric` OHLCV with `candles_ohlc_check` (`l > 0`, `l <= least(o, c)`, `h >= greatest(o, c)`, `v >= 0`); 7-day chunks; columnstore after 30 days (segment `instrument_id`, order `ts DESC`); retention 180 days |
| `candles_eod` (on `session_date`) | `source` is `yahoo` or `alpaca-1day`, plus `fetched_at` and the same OHLC check; 365-day chunks; columnstore after 365 days; no retention |
| `indicators` (on `ts`) | `timeframe` `15m`, `1h` or `1d`; `close`, `ema12`, `ema26`, `atr14` as `double precision`; `cdc_zone` one of six zones or NULL; `computed_at`; PK `(instrument_id, timeframe, ts)`; 28-day chunks; columnstore after 90 days; no retention |
| `candles_15m`, `candles_1h`, `candles_1d` | UTC `time_bucket` with no origin or offset (A16); `materialized_only = false` (real-time aggregation, A11); policies refresh the last 3 days up to one bucket ago, every 5 minutes, 15 minutes and 1 hour respectively |
| `candles_daily` (view) | `candles_eod` rows (`ts` = `session_date` at 00:00 UTC) for `daily_source = 'eod'`, `UNION ALL` `candles_1d` rows for `aggregate` |

The aggregates group by `time_bucket(...)`, never by `ts`, and carry a `bars` count. Migration B creates 3 hypertables, 3 aggregates and 7 policy jobs (source: raw/2026-10-07-market-data.md §Database, Migration B).

Settled assumptions: migration B runs in goose's default transaction, so the aggregates are created `WITH NO DATA` (A1); constraints are enforced on chunks and `ON CONFLICT DO UPDATE` into a compressed chunk works (A2); real-time aggregation must be set explicitly (A11) (source: raw/2026-10-07-market-data.md §Concept, Assumptions A1–A16).

## Two more time-series hypertables (migration N, signals context, 2026-10-30)

Signals context added two hypertables outside the price tables, on the same chunk, columnstore and retention conventions as migration B:

| Object | Settings |
|---|---|
| `gkg_mentions` (on `ts`) | Kept GDELT mentions; PK `(subject, ts, gkg_record_id)`; 7-day chunks; no default index; columnstore after 30 days (segment `subject`, order `ts DESC`); **retention 90 days**, N's one retention policy |
| `context_features` (on `ts`) | One row per subject per 15-minute window with trailing-24 h coverage and its z; PK `(subject, ts)`; 28-day chunks (like `indicators`); columnstore after 90 days; no retention; partial index `(instrument_id, ts DESC) WHERE instrument_id IS NOT NULL` |

`context_features.ts` is the GDELT window stamp + 15 minutes, and its baseline is the trailing 30 complete UTC days. See [[gdelt-gkg-ingest]] and [[context-features-and-coverage-signals]] (source: raw/2026-10-30-signals-context.md §Database; §Concept, How it runs, 4. Features).

## Writer and refresh rules

These are stated in both the migrations and the bot docs, and they are the easiest way to lose data:

- A writer that stores bars older than 3 days (outside the policy window) must call `refresh_continuous_aggregate` for the touched range on all three aggregates, **outside a transaction**.
- **Never refresh over a range whose raw chunks retention has already dropped, and never with a NULL start.** That silently deletes the materialized buckets, and past 180 days `candles_1d` is the only daily history for the seven `aggregate` instruments.

(source: raw/2026-10-07-market-data.md §Database, Writer rules; §Components, Recovery notes)

How the bot applies them: its bar sink persists, then publishes. Aggregate refreshes are deferred, flushed once per backfill run in calls of at most 7 days, clamped to the retention horizon, and carried forward on failure. An aggregate maintenance loop retries every 5 minutes and runs a daily catch-up (source: raw/2026-10-07-market-data.md §Components, Bar sink).

**Concurrent refresh is an expected transient.** On the preview, the bot's deferred flush collided with TimescaleDB's own policy on `candles_15m` and logged `aggregates_refresh_failed` at level 50; the 5-minute maintenance retry refreshed it at 04:47:50Z (from 04:43:14Z) and the indicator rows followed. No action is needed; FU-5 proposes logging it at warn with its own reason, or retrying sooner (source: raw/2026-10-07-market-data.md §Concept, Preview findings 4).

## Reading it back

- `GET /instruments/{id}/candles`: `1m` reads `candles`, `15m` and `1h` the aggregates, and `1d` reads `candles_daily`. Returns `{ts,o,h,l,c,v}` items and `last_is_partial`; `limit` 1–5000 (default 500).
- `GET /instruments/{id}/indicators`: `15m`, `1h` or `1d`; items `{ts, close, ema12, ema26, cdc_zone, atr14}`.
- ORCH-12: indicator values are decimal strings on REST and in the forwarded `zone` message, while the columns stay `double precision`. A NaN or infinite stored value is returned as `null` and logs `indicator_value_not_finite`.

(source: raw/2026-10-07-market-data.md §API, REST and Request rules; §Concept, ORCH-12)

## CDC ActionZone indicators

`packages/indicators` in `tidewatch-bot` is a shared library with zero runtime dependencies and no I/O.

- **EMA(n)** is SMA-seeded and `null` before n closes. **ATR14** uses Wilder's method with an SMA seed.
- **CDC zone** (MD12, following piriya33's *CDC ActionZone V3 2020*): computed from the close, EMA12 and EMA26, as one of `buy`, `pre_buy_2`, `pre_buy_1`, `sell`, `pre_sell_2` or `pre_sell_1`, or `null` on ties and during warm-up.
- A full-series function and an incremental `step(state, bar)` give identical results.
- **Fixture.** `fixtures/cdc-reference-1h.csv` holds 500 BTCTHB 1h bars captured once from Binance TH public REST: 200 warm-up bars, then 300 compared bar for bar against an independent Python oracle (`fixtures/cdc_reference.py`).
- **OI-1 (open).** The licence statement for the CDC script was not captured; the fixture README says "not determinable on 2026-10-06", and the Pine source is not vendored.
- Chart use of `packages/indicators` was deferred to slice 5. Slice 5 did not use it: the Chart draws zones from the stored `indicators` rows, and neither the service nor the web computes a CDC zone. Computing 4h zones on read was rejected as a second CDC implementation (D2; see "Consumers in slice 5" below).

(source: raw/2026-10-07-market-data.md §Components, packages/indicators; §Concept, MD12; §Open questions; raw/2026-10-16-charting.md §Concept, Owner decisions D2)

## The indicator job and the tide strip

- The bot writes one `indicators` row per closed 15m, 1h or 1d bucket within 60 s, and recomputes forward after corrections.
- A `zone` message is published on `px:<id>` only for strip-timeframe rows inside the 3-day correction window (see [[redis-market-contract]]).
- The Market watch `strip` uses timeframe `1h` or `1d`, up to 48 cells oldest first, and `current_zone` equals the last cell's zone. On the preview, the zone label equalled the strip's last cell (O3).
- A16 (pending owner review): US hourly strips are UTC-aligned, including extended hours.

(source: raw/2026-10-07-market-data.md §Components, Jobs; §API, Market watch row; §Concept, O3 and A16)

## Consumers in slice 2 (paper trading)

- **Fills read stored bars.** A market order fills at the open of the first closed 1-minute `candles` bar after placement. A limit order fills on the first later bar that trades through. A daily-only instrument (`PTT.BK@webull`) fills at the next session's open once that session's `candles_eod` row lands (see [[paper-trading]]).
- **Bar end, not bar start.** For marks, a stored close counts at `ts + 60 s ≤ t` for 1-minute bars, and at the session end for daily-only bars. FU-7: a 5m bar would end at `ts + 5 min` in the bot, but the service would use +1 min. No 5m instrument is seeded.
- **`indicators` feeds `market_state`.** Each decision records `market_state` from the latest strip-timeframe `indicators` row (see [[decision-record]]).
- **`ledger` follows the hypertable conventions.** Migration E's `ledger` is a hypertable on `ts` with 28-day chunks, `create_default_indexes => false`, no columnstore and no retention.

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design and C6; §Concept, Bot S4/S6 notes; §API, Intake order; §Database)

## Consumers in slice 2b (zone-transition bot)

The zone-transition bot trades on `indicators.cdc_zone` alone. It needs no signals, because a row exists for every closed 15m, 1h and 1d bucket within 60 s of the bucket's close (see [[zone-transition-bot]]).
- **Strip timeframe.** The bot reads the strip timeframe: `1h`, or `1d` for daily-only instruments such as PTT.BK (ZB2).
- **One bounded read (R4).** Per instrument and pass, the bot reads the latest 49 strip rows by count, bounded like the service's `stripQuery`. A time-window read was dropped because it cannot guarantee 48 rows for session-only US bars.
- **Zone run (R3).** A zone run starts at the earliest row of the trailing same-zone streak within those 49 rows. If the streak fills all 49, the start is unknown and the run is never entered.
- **Rules.** An entry needs a run that turned `buy` at or after the bot's `status_since`. An exit fires whenever the latest strip row is `sell` and the bot holds a position.
- A new strip row is also what opens a `bot_runs` row (see [[bot-versions-and-runs]]). On the 2b preview, runs were written only when a strip row advanced (`new_bars` 4, then 2).
- Each bot decision records `market_state` from these rows, like a user decision (see [[decision-record]]).

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Problem, ZB2, Proposed defaults and Plan resolutions, Bot R3/R4; §API, Bot runtime; §Test plan, Other preview results)

**Bot-activity (2026-10-10).** The bot now records, per instrument and evaluation, the zone facts it read from these strip rows: `bar_ts`, `zone`, `zone_run_started_at` and `zone_age` come from `zoneRun(rows)`, where `zone_age` is the streak over the latest 48 rows (null/null/null/0 with no rows). They are stored in `bot_watch` and `bot_runs.outcomes` beside the verdict, for example `no_zone` for a pre-zone or `run_start_unknown` when the Buy streak fills the 49-row window. The service's watch route never reads `indicators`; it shows what the bot stored (see [[bot-watch-verdicts]]) (source: raw/2026-10-10-bot-activity.md §API, Bot runtime, Entry facts and The fourteen verdicts; §API, Service routes).

## Consumers in slice 4 (Signals page)

The service reads `indicators` to show the market context at the time of each signal (the detail's `context`, see [[signals-read-api]]). Unlike the bot's verdicts, the service computes these values itself, with lateral lookups:
- **Timeframe.** The strip timeframe: `1h`, or `1d` for a daily base.
- **Zone run.** Up to 48 strip rows at or before the signal's `created_at`. The detail shows the zone, the run start ("since …") and its age in bars, or "No zone yet".
- **`close_at_signal`.** The latest strip close within the 7 days before `created_at`.
- **`atr14`.** From the latest `1d` row within the 30 days before `created_at`. With no such row, the web reads "No daily ATR for this instrument".
- **`latest_price`.** A usable `px:last`, else the latest strip close (see [[redis-market-contract]]).
- **"Contradicted by price".** A signal is contradicted when its direction is up or down, `p ≥ 0.600`, a daily ATR exists, and `latest_close − close_at_signal` goes against the call by more than that ATR. The summary count uses the latest stored close in place of the current price (S7), and a missing row counts as not contradicted.
- *Elliott* and *Regime* read "Arrives with Charting"; slice 4 shows no Elliott or regime values. (Filled since slice 5; see below.)
- **Assumption A3 is unverified.** It holds that the lateral `indicators` lookups are fast by primary key, but no explain-analyse is recorded.

(source: raw/2026-10-12-signals-page.md §API, `SignalDetail` and Summary; §Components, Expanded row, Context at the time; §Concept, Accepted defaults; §Test plan, Assumption outcomes A3)

## Consumers in slice 5 (Charting)

tidewatch-service #11 (merged 2026-10-16 as `1547a89`, not deployed) reads these tables for the Chart and for the signal detail's Elliott and regime. It adds **no schema change, migration, index or write**, and there is still no `4h` relation (D2). See [[charting]].

- **One joined read (S1).** `ChartRepo.Bars` reads `candles_15m`, `candles_1h` or `candles_daily` (eod flag `source <> 'aggregate'`), newest first up to a row count, and LEFT JOINs `indicators` on the same `(instrument_id, timeframe, ts)` key. A missing row gives `null` for all four indicator values. The SQL and the route are on [[chart-read-api]].
- **The closed rule.** A bar is closed at T when it is an eod bar or `ts + timeframe ≤ T`. The chart uses `generated_at` as T. The signal detail uses `created_at` and applies `ts + timeframe ≤ created_at` to every bar, eod bars included, so it never looks ahead (CH-R6).
- **Zone colour.** Each candle takes the stored `cdc_zone` of its own bucket. A warm-up row with a NULL zone, a row not yet landed, or the forming bar is drawn without a zone. On the preview, NVDA and BTC/THB at 1h and 15m matched `indicators` for 999 zoned bars per head window and for full histories of 2,000–17,456 bars, including 14–25 NULL-zone warm-up rows (FR-CH-E2E-001).
- **The 60 s gap.** In the ≤ 60 s before the bot writes a closed bucket's row, the newest closed bar has `cdc_zone: null`, and *Right now* keeps the previous row's zone, as Market watch does. The web re-reads the head 65 s after a bucket closes, again at 180 s if there is still no zone, and at once on a `zone` frame.
- **The `1d` key (A1, held).** The `1d` indicator `ts` equals `candles_daily.ts`, covered by an eod 1d instrument in `TestChart_Read_JoinsIndicators`.
- **Read cost (A5, held).** A read-only EXPLAIN ANALYZE on the preview database, for `NVDA@webull` with n = 5000: 1h read all 2,010 rows in 12.1 ms (colder cache), and 15m read 5,000 of 8,039 rows in 4.3 ms. Both plans use ChunkAppend with bitmap index scans on `(instrument_id, ts)` per chunk and `indicators` primary-key index scans.
- **Earlier bars and retention.** The first read is the last 1,000 bars. Scrolling left reads earlier pages until an empty or short answer, or past 180 days of intraday history, the `candles` retention (PD5).
- **Elliott and regime.** The labeller reads the stored closes, `ema12`, `ema26` and `atr14` of closed bars (see [[elliott-regime-labeller]]). The regime needs at least 20 finite `atr14` values.
- **The strip at 96.** The Chart's tide strip shows the last 96 closed bars that carry an indicator row, on the chart's timeframe. Market watch's strip is unchanged at 48 cells.

(source: raw/2026-10-16-charting.md §Database; §API, Conventions, `GET /instruments/{id}/chart`, Regime and The signal detail's new context keys; §Concept, Problem, Owner decisions D2 and PD5; §Components, Market watch link and the 96-slot strip and The Chart screen; §Test plan, Acceptance status FR-CH-E2E-001)

## Known gap: indicators after an interrupted backfill (FU-3)

GAP-BOT-CATCHUP-IND: after a restart, the clamped catch-up refresh rebuilds the aggregates but never re-marks indicators (`sink.ts` passes it an empty instrument map). After an interrupted backfill of bars older than 3 days, the 15m, 1h and 1d rows over the gap can stay missing, and later EMA and ATR values are computed across the gap. `run indicators` alone does not repair it. **Manual recovery:** delete the affected instrument's `indicators` rows from the start of the gap, for each affected timeframe; the next pass recomputes from there. The proposed fix is to mark each intraday instrument dirty at serve start from the earliest bucket that has an aggregate but no indicator row, or to persist the carried ranges (source: raw/2026-10-07-market-data.md §Open questions, Known gaps; §Components, Recovery notes).

## Verified behaviour

- The migrations harness checked aggregate equality across a refresh boundary on a disposable database.
- On the preview, `candles_1h` equalled the manual `GROUP BY` over 48 of 48 hours, with `EXCEPT` returning 0 rows both ways for BTCTHB and ETHTHB (not re-run over NVDA/AAPL).
- A 10 min 30 s bot outage left 0 missing minutes for BTCTHB and ETHTHB.
- After the Alpaca backfill the indicator job wrote NVDA 7,872 15m and 1,968 1h rows, and AAPL 7,871 and 1,968.
- XAU fix preview (2026-10-07): the 180-day XAU backfill stored 176,641 bars and dropped 920 (weekend page) plus 60 (daily break) as out-of-session; the database held 0 Saturday-NY, Friday ≥ 17:00 NY or weekday-break XAU bars; the synthetics rebuilt to the current minute (GOLD965THB 153,601, GOLD9999USD 153,601, GO 108,560 bars); a 12.6-minute outage left 0 missing minutes for XAUUSD, BTCTHB and ETHTHB; and the first live `gold_premium_checks` row deviated −0.021 % from GTA (see [[gold-feed-xaut-proxy]]).

(source: raw/2026-10-07-market-data.md §Test plan; §Concept, O2 and Preview findings 3; raw/2026-10-07-fix-xau-feed-binance-th.md §Test plan, Preview acceptance)

## Related pages

- [[market-data]] — the slice overview
- [[instrument-master]] — base timeframe and daily source per instrument
- [[market-data-worker]] — the collectors, bar sink and indicator job that write these tables
- [[redis-market-contract]] — how `bar` and `zone` messages reach the service
- [[gold-feed-xaut-proxy]] — why XAU bars are calendar-gated and where `gold_premium_checks.xau_usd` now comes from
- [[centralized-migrations]] — migration B and the down-migration warnings
- [[paper-trading]] — the fill and mark rules that read these bars
- [[zone-transition-bot]] — the auto bot that trades on strip-timeframe CDC zone runs
- [[bot-watch-verdicts]] — the zone facts and verdicts the bot records from these strip rows
- [[signals-read-api]] — the signal detail's context and the "contradicted by price" count read from these rows
- [[charting]] — slice 5, which draws these bars and zones on the Chart
- [[chart-read-api]] — the joined bars-and-indicators read and its EXPLAIN results
- [[elliott-regime-labeller]] — the Elliott counts and regime derived from the stored closes, EMAs and ATR
- [[context-features-and-coverage-signals]] — the `context_features` hypertable and its baseline rule
