# Market data worker (tidewatch-bot)

**Summary**: Since slice 1, `tidewatch-bot` is a long-running worker. One `serve` process, holding the `runner:serve` advisory lock, runs the venue collectors, the synthetic engine, the indicator and list jobs, the subscription manager and the status publisher, which is the only writer of `px:last`. This page also records two durable venue gotchas: Binance TH refuses klines spans over 7 days, and OANDA is unavailable for the owner's region, which is why, since the 2026-10-07 fix, XAU/USD is priced from Binance TH `XAUTUSDT` and the USD/THB proxy is activated at `serve` start (FU-4 closed; see [[gold-feed-xaut-proxy]]). Since slice 2 (2026-10-08) the same worker also runs the `sim` paper-trading runner (see [[paper-trading]]), and since slice 2b (2026-10-09) the `bots` runner that evaluates the zone-transition bot (see [[zone-transition-bot]]). Since bot-activity (2026-10-10) that runner also records a per-instrument verdict on every evaluation and writes it to `bot_watch` (see [[bot-watch-verdicts]]). Since signals-ingest (slice 3a, 2026-10-11) the worker also runs `ingest` and `signals`, the 12th and 13th collectors. They read the source registry into `documents` and turn documents into `signals` (see [[source-registry-and-ingest]] and [[signals-pipeline]]). Since slice 6 (bots, tidewatch-bot #10, merged 2026-10-21, not deployed), the `bots` runner also runs the general engine for v2 bots, with a per-bot advisory lock on the runner's own lock session, run requests, a scheduler and the `bot_decide`/`bot_thesis` model stages (see [[bots-engine]]). Since the learning loop (slice 8, tidewatch-bot #17, merged and deployed 2026-10-30), the worker also runs `learning`, the **fourteenth** collector, which gives each eligible auto bot a monthly learning run (see [[learning-loop]]). That rollout also recorded a venue gotcha: **Alpaca allows one stream connection per key**, so a preview bot on the production key takes production's stream. **Since signals context (tidewatch-bot #18, merged 2026-10-30; deploy triggered, not verified),** `COLLECTOR_NAMES` has 15 entries: `learning` (14th, from the learning-loop build) and `context` (15th). The `context` runner computes coverage features, writes coverage signals and refreshes the event calendar (see [[context-features-and-coverage-signals]]). `ingest` gained the GDELT collector family, and `market-data` gained a streaming zip reader, `transport/stream-zip.ts`. **The production bot chart's collectors value does not list `context` yet,** so the runner is not running in production.

**Sources**: `raw/2026-10-07-market-data.md`; `raw/2026-10-07-fix-xau-feed-binance-th.md`; `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-21-bots.md` (the `bots` runner's general engine only); `raw/2026-10-30-learning-loop.md` (the `learning` runner and the Alpaca stream lesson only); `raw/2026-10-30-signals-context.md` (the `context` runner, the collector count and `stream-zip` only)

**Last updated**: 2026-10-31

---

## Shape

| Package | Role |
|---|---|
| `packages/indicators` | EMA, ATR14 and the CDC zone, no I/O (see [[market-timeseries]]) |
| `packages/market-data` | Collectors, jobs, subscription manager, status publisher, bar sink, transport, limiters, Redis publisher, metrics |
| `packages/shared` | `loadConfig` (now requires `REDIS_URL`), pino logger and redaction |
| `packages/worker` | The CLI: `serve` (default `CMD`) and `run <job>` |

- **`serve`** takes `runner:serve` first. Only the holder starts the runners, the status layer and the aggregate maintenance; a second `serve` stays in full standby. This makes serving all-or-nothing, so `px:last` and `status` keep a single writer (ORCH-36). Scheduled runs inside runners take no `job:<name>` lock (ORCH-35).
- **`run <job> [--list <code>]`** runs one of `list-refresh`, `indicators`, `yahoo-eod`, `alpaca-daily` or `gold-premium-check`. Exit codes: 0, 1 (a failure or a lock held elsewhere) and 2 (usage).
- **Shutdown.** SIGTERM triggers an ordered shutdown with a 10 s guard that logs `shutdown_timeout` and exits 1; compose therefore uses `stop_grace_period: 15s`.
- **Image.** `node packages/worker/dist/main.js` as non-root `node` (UID 1000), with no `EXPOSE` or `HEALTHCHECK`; compose owns the healthcheck.
- **HTTP on `0.0.0.0:9091`** inside the container, never published: `GET /health` (always 200), `GET /ready` (database `SELECT 1` and Redis `PING`, 2 s each, single-flight, cached 1 s; it does **not** check the schema version), `GET /metrics` (13 series). Other methods get 405, other paths 404.
- Stack: Node 24, pnpm 11.5.2, Nx 23.2.1, TypeScript ~6.0.3, Vitest 4. Libraries: `ws` 8, `redis` 6, `prom-client` 15, `luxon` 3, `node-html-parser` 9, `fflate` 0.8.

(source: raw/2026-10-07-market-data.md §Components, tidewatch-bot; §API, Bot HTTP endpoints; §Concept, ORCH-35, ORCH-36 and Libraries)

The bot has no compiled schema constant. Its SQL harness (`scripts/sql-integration.sh`) used to pin the applied maximum to migration C's version; since the XAU fix it requires C applied, requires D when the migrations checkout has it, and accepts a newer maximum (see [[centralized-migrations]]) (source: raw/2026-10-07-market-data.md §Database, Required-schema-version contract; raw/2026-10-07-fix-xau-feed-binance-th.md §Database).

## Collectors

| Collector | What it does |
|---|---|
| `binance-th` | Bare-endpoint stream with `SUBSCRIBE` frames and `<symbol>@kline_1m`. A closed kline is upserted; every kline publishes a tick. REST klines page in 1,000-minute windows. Weight limiter 4,800 per 60 s (klines cost 5), adopting `x-mbx-used-weight-1m`; honours 429 `Retry-After`; a 418 stops REST and logs `collector_banned`. Reconnects after 3 min of silence or at 23 h. Realtime set at most 20 instruments. Since the XAU fix: metadata indexes every `exchangeInfo` symbol (the THB subset stays for the "no THB symbols listed" guard and the `top20_binance_th` list job), every active `feed='binance-th'` instrument is subscribed regardless of quote asset (XAU/USD as a tier-0 member), and bars and ticks are stored only inside the instrument's own calendar (`calendar/in-session.ts`; see [[gold-feed-xaut-proxy]]). |
| `alpaca` | IEX stream (`bars`, `updatedBars`, at most 30 symbols). SIP `1Min` REST for backfill, 5-minute reconciliation (SIP replaces every window older than 15 minutes) and 1-minute delayed polling for names beyond 30, always with `end ≤ now − 15 min`. `1Day` SIP bars go to `candles_eod` on Tue–Sat 05:30–08:00 Bangkok. One sliding window of 180 requests per 60 s covers every caller. |
| `oanda` | Pricing stream at the mid (at most 4 per second), M1 candles every minute, a startup instrument check, and the `USDTTHB` proxy when `USD_THB` is missing. **Dormant on the owner's setup** (see the gotcha below); its `useProxy()` now delegates to the shared `core/usd-thb-source.ts` helper with reason `usd_thb_unavailable`. |
| `yahoo` | SET end-of-day at 18:00 Mon–Fri with retries to 20:00, then 07:30 Tue–Sat; a 400-day first load; one request per second. Thai stocks are end-of-day only (MD5). |
| `set-check` | Compares the Yahoo close with the SET site's `historical-trading` and writes `eod_close_checks`. It never changes `candles_eod`. |
| `gta` | Polls GTA prices every 2 minutes, 08:30–18:00; the Gold 96.5 premium check runs at 17:45. |
| `synthetic` | Builds `GO@tfex`, `GOLD9999USD@mts` and `GOLD965THB@mts` from XAU/USD and USD/THB (formula on [[instrument-master]]). Both legs are Binance TH proxies since the XAU fix (see [[gold-feed-xaut-proxy]]). |

`MARKET_DATA_COLLECTORS` defaulted to all nine at slice 1. Slice 2 added `sim` as a tenth entry, slice 2b `bots` as the eleventh, slice 3a `ingest` and `signals` as the twelfth and thirteenth, and slice 8 `learning` as the fourteenth (see below). A missing secret disables only its collector (MD13) (source: raw/2026-10-07-market-data.md §Components, packages/market-data and packages/shared; §Concept, MD8, MD9 and MD13; raw/2026-10-07-fix-xau-feed-binance-th.md §Components, tidewatch-bot).

## The `sim` runner (slice 2)

tidewatch-bot PR #4 (merge `6902f4e`, 2026-10-08) added `packages/sim` and a tenth `COLLECTOR_NAMES` entry, `sim`, which is on by default.
- `serve` starts it and wraps `writeLast` in a price-view recorder, so marks read the in-memory `px:last` record, not Redis.
- It holds the lock `runner:sim` and has no venue budget.
- Its fill pass is triggered by the bar sink's `persisted` event and by a 5 s sweep.
- It also runs hour and day_end marks, a 1-minute outcome sweep and a 15 s re-mark sweep, all under a shared gate of 3 (`SIM_CONCURRENCY`).
- `SERVE_POOL_MAX` stays 12.
- New metrics are the seven `sim_*` series. New error events: `sim_mark_failed` and `sim_outcome_failed`.
- Three bot comments still say "nine" collectors (`market-data/src/runtime/types.ts:76`, `metrics.ts:7`, `status/status-publisher.ts:115`). They were left as PRD-stable text.
- The calendar helpers in `packages/market-data/src/calendar/calendar.ts` are now exported for the fill rules and outcome horizons.
- The bot's SQL harness now asserts that migration E is applied.

Details are on [[paper-trading]] (source: raw/2026-10-08-simulation-engine.md §API, Bot runner `sim`; §Files touched, tidewatch-bot; §Open questions).

## The `bots` runner (slice 2b)

tidewatch-bot PR #5 (merge `ac80b04`, 2026-10-09) added the Nx library `packages/bots` (`@tidewatch-bot/bots`) and an eleventh `COLLECTOR_NAMES` entry, `bots`, after `sim`. It is on by default.
- `serve` starts it (`packages/worker/src/serve.ts`). It holds the lock `runner:bots`, has no venue budget and restarts with the usual backoff.
- It reads PostgreSQL, the reference cache and the same recorded `px:last` view as `sim`, never Redis. It has no HTTP to the service.
- One pass at start, then every 30 s (`BOTS_EVAL_INTERVAL_MS`), never overlapping. A run older than 5 minutes left `running` is swept to `failed` before the first pass.
- Disabling `bots` leaves zone bots idle. With `sim` disabled, bot orders stay pending.
- No new environment variable: `MARKET_DATA_COLLECTORS` accepts `bots`, and compose is unchanged. The store serialises every method on one queue and connection, so `SERVE_POOL_MAX` stays 12.
- New metrics are the six `bots_*` series; new logs include `bots_version_unsupported` (warn) and `bots_pass_failed` (error).
- The `Dockerfile` ships the `bots` dist. `serve.spec.ts` collector counts were raised by one on purpose.
- The SQL harness now runs the bots integration specs and asserts that migration F is applied. Last run: market-data 16, worker 2, sim 17, bots 9, all passing.
- **Follow-ups.** The pre-existing `runner_failed` log (`serve.ts:373-376`) prints the message and stack if `engine.run` rejects, so intake errors must stay off that path. The engine stops only between passes, so a slow-database pass may outlast `serve`'s 10 s shutdown guard.

The pass, the trading rules and the metrics are on [[zone-transition-bot]]; runs and versions are on [[bot-versions-and-runs]] (source: raw/2026-10-09-zone-transition-bot.md §API, Bot runtime; §Files touched, tidewatch-bot; §Test plan, Commands; §Open questions, Bot).

**Bot-activity changes (tidewatch-bot PR #6, merge `6b8cdb0`, 2026-10-10).**
- Each evaluation now ends with a `bot_watch` write: one statement outside any transaction, after the run is finished, never touching `paper_accounts`. A quiet pass still writes it, so it acts as the heartbeat the Watch's stale line reads (more than 120 s without a pass while running). Details on [[bot-watch-verdicts]].
- **One new log event**, `bots_watch_write_failed` (error level; exactly `bot_id`, `error_class` and `code` when a SQLSTATE exists). A failed watch write does not fail the evaluation; the next pass retries. It has no once-only memo, so a persistent failure logs every 30 s per bot (a follow-up).
- **Unchanged.** The six `bots_*` metric series and their label sets, the 30 s cadence, the Dockerfile, `.env.example`, `pnpm-lock.yaml` and `packages/bots/package.json`. Cost: one extra statement per evaluated bot per pass, plus one extra read per suppressed instrument. 48 passes on the preview averaged about 18 ms.
- **Passes are hard to see in logs.** `bots_pass_started` is debug-level, so the preview showed passes through SQL and metrics instead.
- The SQL harness asserts that migration G is applied and gates leftover `bot_watch` rows of spec bots (must be 0). Bots integration: 16/16 on G. `bots:test` 132/132.

(source: raw/2026-10-10-bot-activity.md §API, Bot runtime; §Files touched, tidewatch-bot; §Concept, Stage and Plan resolutions, Bot R-BA4; §Test plan, Commands, Acceptance status and Assumption outcomes; §Open questions, Bot)

**Slice-6 changes (tidewatch-bot PR #10, merge `81133bf`, 2026-10-21; not deployed).**
- **Two engines in one runner.** Each 30 s pass (`runEnginePass`) takes pending `bot_run_requests`, ends due probations, reads every auto bot that is `running` or `observing`, and dispatches each by vocabulary: v1 → the unchanged 2b evaluation; v2 → guard, manager, scout (see [[bots-engine]]). Without the worker's general dependencies, the 2b `runPass` runs alone.
- **Per-bot lock, no extra pool use.** Each bot is evaluated under `bot:<bot_id>`, taken with `tryLock` on the `LockSession` that holds `runner:bots`, outside any transaction, and released in a `finally`. It uses no pooled connection, so `SERVE_POOL_MAX` stays 12. A busy lock logs `bots_lock_busy` and skips the bot.
- **Start-up.** Runs left `running` over 5 minutes are finished `failed`/`interrupted` with their own loop's zero counts, and requests taken before this start without a run are released.
- **Model stages.** `bot_decide` and `bot_thesis` open on the signals router, ledger and ceiling (`openSignalsModels`). A stage start refusal is logged once and the runner continues, so the 2b pass never depends on the model tables. No new environment variable.
- **Wiring.** `packages/worker/src/serve.ts` and `serve.spec.ts` changed in bot S12; the `Dockerfile` ships `packages/waves` and the new bots dependencies.
- **Observability.** Thirteen `bots_*` series (seven new from `createGeneralBotsMetrics`) and fifteen log events (seven new). **FU-7:** `bots_running` is set by both passes and flips between 1 and 2.
- **Harness.** `scripts/sql-integration.sh` refuses to run unless J is applied; the bots specs went 30/30, 36/36, then 37/37 through the fix rounds. A market-data stream spec flaked under load and passed on a re-run.

(source: raw/2026-10-21-bots.md §The bot engine, Pass order, Start-up, Model stages and Observability; §Files touched, tidewatch-bot S1, S6, S12; §Concept, Stage, Verified locally; §Operations)

## The `ingest` and `signals` runners (slice 3a)

tidewatch-bot PR #7 (merge `0d7be6d`, 2026-10-11) added two `type:shared` Nx libraries. `@tidewatch-bot/ingest` depends on `shared` and `market-data`. `@tidewatch-bot/signals` depends on `shared`, `market-data` and `ingest`.

- **Collectors.** `COLLECTOR_NAMES` grows to thirteen: `ingest` is twelfth and `signals` thirteenth, both enabled by default. `MARKET_DATA_COLLECTORS` defaults to all thirteen.
- **Locks.** `runner:ingest` polls the source registry with one timer per enabled source (see [[source-registry-and-ingest]]). `runner:signals` sweeps every 10 s (see [[signals-pipeline]]). The new jobs `source-run`, `source-backfill`, `signals-requeue` and `signals-eval` each take their own `job:<name>` lock; the two ingest jobs use the `runner:ingest` budget.
- **Pool.** `SERVE_POOL_MAX` stays 12. The A7 probe measured an ingest peak of 1 and a signals peak of 1, a combined 2/12. Both runners stopped in 2.8 ms and 1.0 ms.
- **Image.** The Dockerfile ships eight `dist` trees, and `/app/tmp` is owned by `node`. The labelled eval set is not in the image (`**/fixtures` is excluded).
- **New third-party dependencies**, none with an install script (`allowBuilds` stays `nx`): `fast-xml-parser` ^5.11.2 (DOCTYPE and entity declarations refused), `node-html-parser` ^9, `unpdf` ^1.8.1, `ajv` ^8.20.0 and `prom-client` ^15.1.3.
- **`market-data` changes.** `redis/contract.ts` and `publisher.ts` gained the C-SIG-1 builder and `publishSignal` (see [[signal-message-contract]]). `transport/user-agents.ts` gained new `SOURCE_NAMES`, and the Wikipedia policy withholds an e-mail contact. The market-data transport `http.ts`, collectors, limits, core, db and status are unchanged, as are `bots`, `sim` and `indicators`.
- **Configuration** (`packages/shared/src/config.ts`). Five new variables: `JEV_API_KEY`, `OPENROUTER_API_KEY`, `FINNHUB_API_KEY`, `SET_MARKETPLACE_API_KEY` and `MODEL_SPEND_DAILY_CEILING_USD`. The four keys are optional, gate quietly and never stop `serve`. `secretValues` masks five values: the four keys and `TIDEWATCH_HTTP_CONTACT`. The root compose and `.env.example` gained the five variables in place, outside any PR (ORCH-4). What each gates is on [[model-routes-and-spend]] and [[source-registry-and-ingest]].
- **`TIDEWATCH_HTTP_CONTACT`** must now be e-mail-shaped for EDGAR, and is sent to sec.gov only (ORCH-11). Wikipedia gets `Tidewatch/<version> (personal research)` unless the contact is URL-form (R-SIG-39). Every new source uses the product User-Agent `Tidewatch/<version>`, never `browser`.
- **Observability.** Twelve new log events in a closed set, and nine new metric series with closed label sets. The existing `collector_disabled` gains the reasons `missing_contact` and `no_collector`.
- **Harness.** `scripts/sql-integration.sh` asserts migration H and pins its SHA-256, and runs the ingest and signals integration specs. Unit tests at `53cb76d`: signals 120, ingest 153, worker 54.
- **Rollback.** List the other eleven names in `MARKET_DATA_COLLECTORS` (dropping `ingest` and `signals`) and restart. The tables stay.

(source: raw/2026-10-11-signals-ingest.md §API, Bot runtime, Jobs, Observability and Environment; §Files touched, tidewatch-bot and Workspace root; §Concept, Stage, Verified locally; §Concept, ORCH-4 and ORCH-11; §Open questions, Rollout and rollback)

## The `learning` runner (slice 8)

tidewatch-bot PR #17 (merge `2a3a412`, head `435feb4`, merged and deployed to production on 2026-10-30) added the learning runner in `packages/bots/src/learning/`. What a run does is on [[learning-loop]].

- **Collectors.** `COLLECTOR_NAMES` grows to fourteen: `learning` is the fourteenth and last (`packages/shared/src/config.ts:48`). `serve` starts it; it is never a one-shot job. It holds `runner:learning`, with no per-bot lock, no account lock and no venue budget.
- **Switch (owner OQ-1).** There is no `LEARNING_ENABLED`. An empty or unset `MARKET_DATA_COLLECTORS` includes `learning`, and an explicit list must name it, so learning is switched off only by an explicit list that omits it. The production chart sets `collectors: ""`, so it runs with no owner action. To switch it off, set an explicit list without `learning`.
- **Configuration.** `LEARNING_EVAL_INTERVAL_MS` (default 60 000; an integer from 1 000 to 86 400 000; `config.ts:151-156`) is the only new variable. The labeller reads the existing `OPENROUTER_API_KEY` through the signals router. No dependency, lockfile, Dockerfile or Redis change.
- **The pass.** Every interval: sweep learning runs left `running` over 30 minutes; take the `learn` requests in one statement; read the learning bots (v2, `running` or `observing`, joined to `users` and `plans`); run requested bots as `manual`, then due bots as `scheduled` (the 1st of the month, 03:00 Bangkok). At start it releases `learn` requests taken without a run.
- **Pool.** Runs are sequential, so a pass holds at most one pooled connection, and no transaction spans a model call.
- **The bots runner ignores `learn` rows**, in its take and its start-up sweeps, because a learning run outlives the bots runner's 5-minute cutoff (see [[bots-engine]]).
- **Observability.** Five `learning_*` metric families and ten closed log events (on [[learning-loop]]); `bots_run_requests_total{loop}` gains `learn`.
- **In production.** After the bot rollout on 2026-10-30, `/ready` was ok, the `learning` collector started, and it made a first learning pass. No learning run has been requested in production yet, and the first scheduled run is due 2026-11-01 03:00 Bangkok.
- **Chart comment drift.** The tidewatch-kubernetes bot chart's comment on `collectors: ""` still says "all thirteen" and omits `learning`. The behaviour is right, because an empty list runs every collector.
- **Unverified (A8).** No ten-bot learning pass was timed.

(source: raw/2026-10-30-learning-loop.md §Concept, The runner; §Concept, Decisions during the build OQ-1; §Concept, Spec corrections, OQ-1; §API, Bot side, Configuration and Metrics; §Concept, Rollout to production; §Test plan, Results, Assumptions; §Open questions, Owner actions still open)

## The `context` runner and the GDELT streams (signals context, 2026-10-30)

tidewatch-bot #18 (merge `b083697`, 2026-10-30) added `packages/context` and the GDELT collector family in `packages/ingest`.

- **Collectors.** `COLLECTOR_NAMES` has **15** entries after the merges: `learning` is the 14th (from the learning-loop build) and `context` the 15th. Both are enabled by default when `MARKET_DATA_COLLECTORS` is empty. The image ships **10 packages**.
- **`runner:context`.** It makes no model call and uses at most one pooled connection, so `SERVE_POOL_MAX` stays 12. A window notifier shared with `ingest` (PB7) triggers it after each GDELT window commit, and a 60 s sweep of `source_files` recovers lost notices. See [[context-features-and-coverage-signals]] and [[event-calendar]].
- **Required wiring.** `worker/serve.ts` wires the context read model as the **required** `BotsRunnerGeneralDeps.createContextReadModel` (PB17), so the scout's discovery paths cannot silently never run (see [[bots-engine]]).
- **`runner:ingest`** gains `gdelt-gkg-en` and `gdelt-gkg-translation` on 300 s timers (see [[gdelt-gkg-ingest]]). There are 13 `SOURCE_CODES`.
- **`market-data` transport.** The new `transport/stream-zip.ts` (`streamZipEntry`, on `fflate`) streams one zip entry under caps of 64 MiB zipped and 256 MiB inflated, computing SHA-256 and MD5 as it goes. `fetch.ts` keeps its 4 MiB cap and was not edited. A spec enforces that only `fetch.ts` and `stream-zip` read bodies ("no-direct-network: only fetch.ts and stream-zip read bodies"). `transport/user-agents.ts` and `http.ts` were edited ("http: keeps Range across redirects").
- **Memory.** About 66 MiB per GDELT window at commit, 132 MiB for both streams, against the 576 MiB production heap.
- **Prompt versions.** 7 recorded, including the new `bot_thesis.v2` (see [[signals-pipeline]]).
- **Production.** **The production bot chart's collectors value does not list `context`.** Until the owner adds it in `tidewatch-kubernetes`, there are no context features, coverage signals or calendar refreshes in production. Per the bot docs, ingest still stores GDELT mentions while `context` is disabled, if the collectors value lists `ingest`.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 1, 3 and 4; §Concept, Runtime counts after the merges; §Files touched, tidewatch-bot; §Test plan, Ingest titles; §Open questions, Production collectors)

## Gotcha: Binance TH refuses klines spans over 7 days

**MD8 says Binance TH follows live behaviour, not its docs**, and this is the case that proved it (source: raw/2026-10-07-market-data.md §Concept, MD8).

- **What failed.** On the first preview (bot `9bf762d`), the first-start backfill requested 180-day spans. The venue answered `400` with code `-4088`, "Maximum time interval is 7 days.", and `binance_th_backfill_failed` was logged 8 times. BTC/THB and ETH/THB never went live, and FR-MD-INFRA-002 failed.
- **Undocumented.** Neither the PRD nor the venue docs name the limit. A live probe confirmed it; 7 days plus 1 minute still passed.
- **Fix (`99c8511`, ORCH-38).** The backfill pages in back-to-back 1,000-minute windows (`BACKFILL_WINDOW_MS`, one full `limit=1000` page). Each window ends at `min(now, start + 60,000,000 ms − 1)`. A 180-day first start is 260 calls per instrument, 1,300 weight of the 4,800 per minute. The backfill ends only when a window reaches now; an empty or short window moves on and leaves the cursor where it was.
- **Guard.** `fetchKlines` throws a `RangeError` for a span over 7 days, before charging the limiter or sending anything.
- **Test fidelity.** The fake transport answers any span over 7 days with the captured 400 (`packages/market-data/fixtures/binance-th/klines-error-4088.json`), so specs cannot pass on a request the venue refuses.
- **Follow-up fix (`06a9ab8`, ORCH-39).** The "closed" cutoff used to be read after the response arrived, so a minute that closed while the request was in flight could be stored as final with partial OHLCV. The filter is now `row.closeTime < now`, with `now` read before the request.
- **Result.** FR-MD-INFRA-002 passed on `06a9ab8`: BTCTHB 259,210 bars and ETHTHB 259,158 from 2026-04-10, `px:last` live, BTC price changing within 20 s.
- **Still unexercised (A5).** No 24 h soak, and real 429 and 418 responses were never seen. A pair with no history re-scans 260 windows per connect, and a persistent failure after empty windows can re-fetch them on each 30 s retry, up to 1,300 weight (security r4 I-1).

(source: raw/2026-10-07-market-data.md §Concept, Preview findings 1 and A5; §Open questions, Bot round-4 info notes)

## Gotcha: OANDA is unavailable for the owner's region (FU-4, closed 2026-10-07)

- The owner's Thai-region account is with OANDA Global Markets, which offers MT5 only. OANDA's v20 docs exclude that division, so `OANDA_DEMO_TOKEN` and `OANDA_DEMO_ACCOUNT_ID` can never be obtained (OWNER-4).
- The OANDA collector stays in the tree but dormant (`collector_disabled`, `missing_secrets`); the OANDA lines in the preview secrets file are empty. On the owner compose, leave the OANDA pair empty; a half-filled pair exits the bot. The owner is never asked for OANDA keys.
- **Consequences at the slice-1 merge.** `XAUUSD@oanda-demo`, `GOLD965THB@mts`, `GO@tfex` and `GOLD9999USD@mts` had no price source and read Stale while open; `USDTHB@oanda-demo` had no live source either, and the Binance TH `USDTTHB` proxy (A3) was created only inside the OANDA collector's `useProxy()`, which never runs without keys. Every XAU/USD-dependent check (parts of FR-MD-BOT-004, FR-MD-BOT-008, FR-MD-E2E-001, FR-MD-E2E-002 and the live half of FR-MD-GOLD-001) was unverified. The owner deferred the replacement as FU-4 on 2026-10-07.
- **Resolution, the same day.** `XAUUSD@oanda-demo` was repointed to Binance TH `XAUTUSDT` (migration D), the Binance TH collector gates its bars and ticks by the instrument's calendar, and `serve` activates the `USDTTHB@binance-th` proxy whenever `'oanda'` is not in the enabled collector set: `ensureUsdThbProxy()` runs after the first reference refresh and before the standby and runner loops start, logs `usd_thb_proxy_in_use` with `reason: 'oanda_disabled'`, and on failure logs `usd_thb_proxy_failed` and retries on each 60 s reference refresh. The XAU/USD-dependent checks passed on the fix preview. Details on [[gold-feed-xaut-proxy]].
- `USDTHB@oanda-demo` keeps `feed='oanda'` and stays inactive; the OANDA staleness rule (no `PRICE` for 2 min) now applies only to it. The specs' OANDA source (intent, PRD A3) is recorded as a deviation in `prd.md` §10, with the §4.1, §4.4 and A3 text left as written by design.

(source: raw/2026-10-07-market-data.md §Concept, Preview findings 2 and OWNER-4; §Open questions; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, The bug, Confirmed root cause and The correction; §Components, packages/worker/src/serve.ts; §Open questions)

## Other venue notes

- **Alpaca live with the owner's keys.** The IEX stream authenticated and the SIP backfill covered 180 days (NVDA 117,181 bars, AAPL 104,196). A6 is confirmed for SIP history and IEX auth. Live IEX bars and the SIP reconciliation need the US regular session (20:30–03:00 Bangkok under EDT, 21:30–04:00 after 2026-11-01); overnight rows read `stale` because the overnight session has no IEX trades.
- **Alpaca allows one stream connection per key (lesson, 2026-10-30).** During the learning-loop production bot rollout, the production bot's Alpaca stream looped on 406. The local preview bot (`forge-0199b29a-ll-f3bdc8b0-tidewatch-bot-1`) held the same Alpaca key and had taken Alpaca's single stream connection. Production re-authenticated at 18:45:09Z once the preview container was stopped. A preview or local bot that holds the production Alpaca key takes the stream from production whenever production restarts. **Stop preview bots, or give them another key, before a production bot rollout.** The preview container was left stopped and must not be restarted alongside production (see [[forge-preview-gateway]]) (source: raw/2026-10-30-learning-loop.md §Concept, Rollout to production; Lesson recorded (one Alpaca stream per key); §Open questions, Owner actions still open).
- **`ws` instead of Node's global WebSocket (A12).** The global one exposes no ping event and sends `User-Agent: node`.
- **Yahoo** answers `Mozilla/5.0` without a crumb (A7); **the Nasdaq API** needs a browser User-Agent (A8, one build-time capture only); **GTA** JSON has the classic page as fallback (A13, build-time captures only).

(source: raw/2026-10-07-market-data.md §Concept, Preview findings 3 and Assumptions)

## Subscriptions and realtime priority

- Realtime priority is watchlist position, then `realtime_requested_at` (MD13). Binance TH holds at most 20 live instruments; Alpaca at most 30, with names beyond that polled with a 15-minute delay.
- The subscription manager recomputes within about 1 s of an `md:subscriptions` message and every 60 s (see [[redis-market-contract]]). An instrument entering a set is backfilled before it goes live; Alpaca names evicted from the live set move to delayed polling.
- First start is slow by design: instruments are backfilled one after another, and each waits for its aggregate flush before subscribing, so prices take minutes to go live.

(source: raw/2026-10-07-market-data.md §Components, Runtime pieces; §Concept, MD9 and MD13; §Components, Recovery notes)

## Status and staleness

- The status publisher is the only writer of `px:last` and `status`, with a pass every 250 ms. Staleness rules live in `status/staleness.ts`.
- Row statuses (MD13): Live, Delayed 15 min, EOD, Synthetic, Closed · opens … (Bangkok) and Stale. Calendars (see [[instrument-master]]) decide open and closed.
- A disabled collector makes its instruments stale while their session is open. The overnight session is always stale while open.
- A Binance TH instrument on a non-crypto calendar (XAU/USD on `gold-23-5`) is judged by the Binance TH closed-bar rule inside its session and reads *Closed · opens …*, never *Stale*, outside it, because out-of-session bars and ticks are never stored or published. Expect up to ~60 s *Stale* at each `gold-23-5` open (the first in-session kline closes a minute after the open) and ~3 min on a fresh-DB first start (the stream opens after the last Binance TH backfill). See [[gold-feed-xaut-proxy]].

(source: raw/2026-10-07-market-data.md §Components, Runtime pieces; §Concept, MD13; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Caller-visible implications)

## Transport, limits and configuration

- `transport/http.ts` is the only `fetch` and `transport/ws.ts` the only WebSocket. Redirects are followed by hand: at most 3, `https` and same-origin only, and none for credentialed sources. One User-Agent table governs every request.
- `loadConfig` requires `REDIS_URL`. `ALPACA_KEY_ID`/`ALPACA_SECRET_KEY` and `OANDA_DEMO_TOKEN`/`OANDA_DEMO_ACCOUNT_ID` are both-or-neither: half a pair exits 1, naming the missing member.
- Optional: `GOLD965_PREMIUM_SEED_THB`, `TIDEWATCH_HTTP_CONTACT`, `MARKET_DATA_COLLECTORS` (default all nine at slice 1; all thirteen since slice 3a) and `METRICS_PORT` (default 9091). Slice 3a added five more optional variables (see "The `ingest` and `signals` runners" above).
- Redaction gains `key`, `apca-api-key-id` and `apca-api-secret-key`, and configured key values of 8 or more characters are masked in every string.
- Provider keys go only into the owner-filled secrets; Claude never handles them (OWNER-3).

(source: raw/2026-10-07-market-data.md §Components, packages/shared and Transport; §Concept, OWNER-3)

## Observability

13 Prometheus series on 9091: `market_data_stale{instrument_id}`, `market_data_last_update_age_seconds{instrument_id}`; `collector_enabled`, `collector_connected`, `collector_reconnects_total` and `backfill_bars_total` (by collector); `alpaca_requests_total{endpoint}`, `alpaca_rate_limited_total`, `binance_th_weight_used`; `indicator_job_lag_seconds{timeframe}`; `instrument_list_age_days{list_code}`, `instrument_list_status{list_code,status}`; `gold_premium_deviation_pct`. Logs are 171 structured snake_case events, matching the README rows (169 at the slice-1 merge; the XAU fix added `binance_th_bar_outside_session` and `usd_thb_proxy_failed`, gave `usd_thb_proxy_in_use` a `reason` and `binance_th_metadata_refreshed` a `symbols` count). Read metrics with `docker compose exec tidewatch-bot wget -qO- http://127.0.0.1:9091/metrics`; `collector_enabled{collector="oanda"}` is 0 while its pair is empty (source: raw/2026-10-07-market-data.md §Components, Observability; §Test plan, Manual reproduction; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Caller-visible implications).

## Recovery notes

- **Redis outage.** Rows read `stale` with session `unknown`; see [[redis-market-contract]].
- **Missing keys.** The affected collector is disabled and its instruments show `stale` while open. Nothing crashes. Half a pair is a configuration error and exits 1.
- **Restart gaps.** The bot backfills from `collector_cursors` on start and on reconnect. On the preview, a 10 min 30 s kill left 0 missing minutes for BTCTHB and ETHTHB; on the XAU fix preview a 12.6-minute kill left 0 missing minutes for XAUUSD, BTCTHB and ETHTHB.
- **After `migrate` applies D.** A running bot picks the migrated XAU row up within 60 s through the reference cache, but restart it so the proxy activation and the 180-day XAU and USDTTHB backfills are logged. Old bot + new row only logs `binance_th_symbol_not_trading`; new bot + old row is a no-op.
- **After first start.** Alpaca `1Day` and the lists do not run at start: use `run alpaca-daily` (only while `serve` does not hold `runner:alpaca`) or `run list-refresh`.
- **Interrupted deep backfill (FU-3).** See [[market-timeseries]] for the manual indicator repair.
- **Shutdown.** A catch-up slice still running at SIGTERM can make the exit code 1 with nothing lost.
- **Two serves.** The second stands by; up to about 25 s of overlap is possible if a lock loss goes undetected (security r3 I-2, accepted).

(source: raw/2026-10-07-market-data.md §Components, Recovery notes; §Open questions, Accepted security info items; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Caller-visible implications; §Test plan, Preview acceptance)

## Follow-ups

- **FU-2.** `prom-client` is deprecated upstream (replaced by `@prometheus-io/client`); at slice 1 only `metrics.ts` imported it. The owner decides on a later migration. Slice 3a added `prom-client` ^15.1.3 as a dependency of the new `ingest` and `signals` packages, which each have their own `metrics.ts` (source: raw/2026-10-11-signals-ingest.md §API, Bot runtime; §Files touched, tidewatch-bot).
- **FU-3.** Re-mark indicators after the catch-up refresh.
- **FU-4.** Replace OANDA practice as the XAU/USD source. **Resolved 2026-10-07** by the Binance TH XAUT proxy ([[gold-feed-xaut-proxy]]).
- **FU-5.** Log the expected "concurrent refresh" transient at warn with a distinct reason, or retry sooner.
- **FU-FIX-1 (pre-existing, recorded by the XAU fix).** Binance TH WebSocket sessions end every ~20–60 min (reason `closed`) and sometimes go silent; the collector reconnects only after 3 min without a message, so every Binance TH-fed row (BTC, ETH, XAU and the gold synthetics) can show *Stale* for up to ~3 min before recovery (the gap is backfilled, no bars missing). Consider ping/pong dead-connection detection or a shorter silence threshold.
- **Nits deferred from the XAU fix.** `usd_thb_proxy_in_use` is logged at `warn` though `reason: 'oanda_disabled'` is now the steady state (`info` for that reason would keep `warn` for the anomaly case); `calendars.name` for `gold-23-5` still mentions OANDA.

(source: raw/2026-10-07-market-data.md §Open questions, Follow-ups; raw/2026-10-07-fix-xau-feed-binance-th.md §Open questions)

## Related pages

- [[market-data]] — the slice overview
- [[market-timeseries]] — the tables the bar sink and indicator job write, and the refresh rules
- [[instrument-master]] — instruments, synthetic formulas, lists and calendars the worker evaluates
- [[redis-market-contract]] — what the status publisher and bar sink publish
- [[gold-feed-xaut-proxy]] — XAU/USD from Binance TH XAUT, calendar gating and the USD/THB proxy at `serve` start
- [[foundation-auth]] — the slice-0 connect-and-exit worker this replaced
- [[paper-trading]] — the `sim` runner's fills, marks, outcomes and re-marks
- [[zone-transition-bot]] — the `bots` runner's pass and trading rules
- [[bot-watch-verdicts]] — the verdicts and `bot_watch` write the `bots` runner adds at the end of each evaluation
- [[source-registry-and-ingest]] — the `ingest` runner, its sources, jobs and metrics
- [[signals-pipeline]] — the `signals` runner's stages, jobs and metrics
- [[model-routes-and-spend]] — the model keys and the daily spend ceiling variable
- [[signal-message-contract]] — the C-SIG-1 message `publishSignal` sends
- [[bots-engine]] — the general engine the `bots` runner runs for v2 bots since slice 6
- [[learning-loop]] — the `learning` runner, the fourteenth collector, and the Alpaca stream lesson from its rollout
- [[context-features-and-coverage-signals]] — the `context` runner (15th collector) since signals context
- [[gdelt-gkg-ingest]] — the GDELT streams under `runner:ingest` and the `stream-zip` transport they use
