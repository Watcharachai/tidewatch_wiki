# Market data and instruments (Slice 1)

**Summary**: Slice 1 gave Tidewatch its market data. It added the instrument master and TimescaleDB time series in three migrations, turned `tidewatch-bot` into a long-running worker with venue collectors, indicators and a Redis publisher, added 11 gated market REST routes and a `GET /ws` hub to the service, and replaced the Overview placeholder with the Market watch card. All four PRs merged on 2026-10-07. Nothing runs beyond the Forge preview. The four gold rows had no price source at merge (FU-4); a same-day corrective fix repointed XAU/USD to Binance TH XAUT and closed it (see [[gold-feed-xaut-proxy]]). Slice 2 (merged 2026-10-08) builds paper trading on these prices and puts a portfolio hero and KPI strip above Market watch (see [[simulation-engine]]). Slice 3a (signals-ingest, merged 2026-10-11) filled the Market watch *Signals* column, which had been a placeholder dash. Each row now carries `signals.today`, the Bangkok day's signal count, which rises live (see [[signals-ingest]]). Charting (slice 5, merged 2026-10-16, not deployed) made each Market watch symbol a link to its chart, and the Chart's *Right now* copies the Market watch row's price, change, status and zone (see [[charting]]).

**Sources**: `raw/2026-10-07-market-data.md`; `raw/2026-10-07-fix-xau-feed-binance-th.md`; `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-16-charting.md` (the symbol link, the strip `slots` input and the routes beside these); `raw/2026-10-29-accounts-roles.md` (the gate's role and the retired admin variables only); `raw/2026-10-30-signals-context.md` (the count's two origins only)

**Last updated**: 2026-10-31

---

## What this slice delivered

Prices are what every later slice is graded against. The simulation (slice 2) cannot fill an order without a bar, signals (slice 3) need a stable instrument identity to resolve to, and the tide strip is the product's signature. Before this slice, Overview was an empty state, the service had no market routes, Redis client or WebSocket library (its router tests expected `/ws` to answer 404), the bot was a one-shot database check, and the migrations held only the extensions and the auth tables (source: raw/2026-10-07-market-data.md §Concept).

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-migrations` | Migration A (16 reference tables and seeds), B (3 hypertables, 3 continuous aggregates, the `candles_daily` view), C (2026–2027 calendar exceptions). `RequiredSchemaVersion` moved to `20261006131346`. | [[centralized-migrations]], [[instrument-master]], [[market-timeseries]] |
| `tidewatch-bot` | `packages/indicators` (CDC ActionZone, EMA, ATR14) and `packages/market-data` (collectors, indicator job, list refresh, subscriptions, staleness and status, Redis publisher, metrics). `serve` is long-running, with `/health`, `/ready` and `/metrics` on 9091. | [[market-data-worker]], [[market-timeseries]] |
| `tidewatch-service` | 11 gated market REST routes, the `GET /ws` hub fed from Redis, eight new error codes, realtime metrics | [[realtime-websocket]], [[redis-market-contract]] |
| `tidewatch-web` | The Market watch card on Overview, with `TideStrip`, `ZoneLabel`, `Dialog`, `Toast` and the `.tag` and table styles | [[design-system-decisions]] |
| Workspace root | The bot became a long-running compose service with a `/ready` healthcheck; `db` runs with TimescaleDB telemetry off; the bot joined the Forge preview | [[forge-preview-gateway]] |

(source: raw/2026-10-07-market-data.md, summary block and §Components)

Authority documents: `tidewatch-specs/market-data/intent.md` (confirmed 2026-10-06; MD1–MD14, O1–O8), `prd.md` (§4 behaviour, §5 schema, §6 REST, `/ws` and Redis, §7 design, §8 operations, §9 `FR-MD-*` IDs, §10 known gaps, A1–A16), `build-prompt.md`, and the Market watch section of `documents/mockups/tidewatch-redesigned.html`. The acceptance ledger `.forge/features/market-data/verification.md` is the source of truth for passed, unverified and pending (source: raw/2026-10-07-market-data.md §Concept, Sources).

## Merge record

| Repo | PR | Reviewed head | Merge commit |
|---|---|---|---|
| tidewatch-migrations | tidewatch-labs/tidewatch-migrations#2 | `d77efa8` | `cb93cd5` |
| tidewatch-service | tidewatch-labs/tidewatch-service#3 | `04dec78` | `734ce35` |
| tidewatch-bot | tidewatch-labs/tidewatch-bot#2 | `06a9ab8` | `5a60477` |
| tidewatch-web | tidewatch-labs/tidewatch-web#3 | `a7cb23a` | `5611d79` |

All four merged at 2026-10-07T13:00:54+07:00 (06:00:54Z) at the owner's request (OWNER-5: "The only real remaining gap is the gold price (FU-4); merge the four PRs."), with `--match-head-commit` in the order migrations, service, bot, web. No CI exists (D4). The owner's compose stack has not been started, so nothing is deployed or running there (source: raw/2026-10-07-market-data.md §Files touched; §Concept, Build and owner decisions; §Test plan, Stages).

## Corrective fix: XAU/USD feed (2026-10-07)

A standalone `/forge-fix` (`fix-xau-feed-649e2a7a`, TB-24) closed FU-4 the same day as the merge: `XAUUSD@oanda-demo` is now priced from Binance TH `XAUTUSDT` through the existing Binance TH collector, with the instrument id, venue, `gold-23-5` calendar and USD quote unchanged. Migration D (tidewatch-migrations #3, merge `a2e7f81`) and tidewatch-bot #3 (merge `a420767`) merged at 16:51Z; tidewatch-service and tidewatch-web were not changed. On the fix preview XAU/USD went *Live*, the three synthetics rebuilt, a 12.6-minute restart left 0 missing XAU minutes and the first live premium row deviated −0.021 % from GTA. FU-4, OI-4 and GAP-GOLD-LIVE are resolved in the feature state, the PRD deviation is recorded in `prd.md` §10 and the verification ledger has a §10 post-fix close-out. The full account is on [[gold-feed-xaut-proxy]] (source: raw/2026-10-07-fix-xau-feed-binance-th.md, summary block; §Test plan, Preview acceptance; §Open questions).

## Outcomes O1 to O8

| # | Outcome | Result |
|---|---|---|
| O1 | Live Market watch | Passed in part on the preview: 5 of 8 rows priced (BTC/THB moving, PTT.BK EOD, NVDA and AAPL from the SIP backfill). Live NVDA/AAPL change pending (US session); gold rows unverified (FU-4) at merge, then passed on the fix preview with all eight rows live, EOD or synthetic (see [[gold-feed-xaut-proxy]]). |
| O2 | Durable, gap-free history | Passed for migrations and on the preview: `candles_1h` matched the manual `GROUP BY` for 48 of 48 hours, and a 10 min 30 s outage left 0 missing minutes. Open: NVDA SIP part, owner-compose re-runs, FU-3. The XAUUSD part passed on the fix preview (12.6-minute gap, 0 missing minutes). |
| O3 | Correct CDC zones | Passed (fixture bar for bar, edge cases, `step` equals full series, preview label equals the strip's last cell). OI-1 licence open. |
| O4 | Instrument identity and universes | Passed at build time; the live `run list-refresh` transcript was not captured. |
| O5 | Watchlist control | Passed, including the Playwright journey on the preview. |
| O6 | Honest data status | Staleness, synthetics and calendars passed; the preview rendered only Live, EOD and Stale tags. The live Gold 96.5 check was unverified at merge and passed on the fix preview (deviation −0.021 %, not flagged). |
| O7 | Safe realtime | Passed: through the gateway `/api/ws` gave 401 without a cookie, 101 with a session, 403 for a foreign or missing Origin. Publish-to-client p99 4.99 ms on loopback. |
| O8 | Within free limits and terms | Passed by counters and tests, with terms in all four READMEs. FR-MD-DOC-002 pending. |

(source: raw/2026-10-07-market-data.md §Concept, Outcomes O1–O8; gold updates from raw/2026-10-07-fix-xau-feed-binance-th.md §Test plan, Preview acceptance)

## Decision map

| Decision | Topic | Where it lives |
|---|---|---|
| MD1, MD2 | Gold 96.5 premium (30-day median of `GTA mid − raw`); `GOLD9999USD@mts` as a synthetic of the XAU/USD mid | [[instrument-master]], [[market-data-worker]] |
| MD3, MD5–MD7 | MTS calendar; Thai stocks from Yahoo EOD with a SET close check; universe list sources; `top20_binance_th` | [[instrument-master]] |
| MD4, MD14 | Storage split (`candles` intraday with 180-day retention, `candles_eod` kept forever); backfill depth equals retention | [[market-timeseries]] |
| MD8, MD9 | Binance TH follows live behaviour, not its docs; US stocks from Alpaca IEX plus SIP | [[market-data-worker]] |
| MD10, MD11 | CoinMarketCap deferred to slice 6; TradingView is not a data source | this page |
| MD12 | CDC rules from piriya33's *CDC ActionZone V3 2020* | [[market-timeseries]] |
| MD13 | The owner's ten defaults (continuous worker, eight seeded rows, cap 50, priority, statuses, 24h change, `/ws` checks) | this page, [[market-data-worker]], [[realtime-websocket]] |
| ORCH-1 | Migrations folded into the service plan as MIG1–MIG4, shipped as their own PR | [[centralized-migrations]] |
| ORCH-7 (R1–R3) | Envelope keeps `requestID`; `details` added; `unsubscribed` ack on `/ws` | this page, [[realtime-websocket]] |
| ORCH-10, ORCH-30 | A row without `px:last` is stale; `last.ts` capped at `generated_at` | [[redis-market-contract]] |
| ORCH-11 (R8), ORCH-27 | 64 KiB frame closes with 1009; one batched existence query per subscribe | [[realtime-websocket]] |
| ORCH-12 | Indicator values are decimal strings on the wire; columns stay `double precision` | [[market-timeseries]] |
| ORCH-35, ORCH-36 | No `job:<name>` lock inside runners; `runner:serve` makes serving all-or-nothing | [[market-data-worker]] |
| ORCH-38, ORCH-39 | Binance TH 7-day fix and closed-cutoff fix | [[market-data-worker]] |
| OWNER-1, OWNER-2 / ORCH-21 | Dependency-gated parallel lanes; contract commands run once on the final tree | this page |
| OWNER-3 | Owner adds provider keys to the preview secrets; isolated DB, retained volumes; TimescaleDB telemetry off | [[forge-preview-gateway]] |
| OWNER-4 | OANDA unavailable for the owner's region; replacement deferred (FU-4), then closed the same day by the Binance TH XAUT proxy | [[market-data-worker]], [[gold-feed-xaut-proxy]] |
| ORCH-22/25 (OC-1), ORCH-26 (OC-2) | Add-dialog all-listed line; DEV-WEB-CAPTION | [[design-system-decisions]] |

(source: raw/2026-10-07-market-data.md §Concept, Product decisions and Build and owner decisions)

## REST API

Every market route sits behind `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles, 2026-10-29; see [[accounts-and-roles]]) (see [[auth-model]] and [[request-protection]]). The base URL is the service origin (`http://localhost:3000` on the owner compose, `/api` behind the preview gateway); the service has no `/api` prefix. Bodies are snake_case, prices, sizes and indicator values are decimal strings, times are RFC 3339 UTC, and responses carry `Cache-Control: no-store` (source: raw/2026-10-07-market-data.md §API).

| Method and path | Notes |
|---|---|
| `GET /instruments` | Search: `q` (1–64 chars; symbol or display-symbol prefix, or substring of name or any alias including `thai_name`), `asset_class`, `list`, `limit` 1–50 (default 20), opaque `cursor`. Ordered by exact symbol match, then list membership, then symbol. |
| `GET /instruments/{id}` | Instrument plus `aliases`, `lists`, `status` (`null` without `px:last`); `404 unknown_instrument` |
| `GET /instruments/{id}/candles` | `timeframe` `1m`/`15m`/`1h`/`1d` (required), `from`, `to`, `limit` 1–5000 (default 500); `last_is_partial`; `422 timeframe_unavailable` |
| `GET /instruments/{id}/indicators` | `timeframe` `15m`/`1h`/`1d`; items `{ts, close, ema12, ema26, cdc_zone, atr14}` |
| `GET /lists`, `GET /lists/{list_code}` | List status and members (optional `as_of`) |
| `GET /watchlist` | `{items, max_items: 50}`, lazily seeded |
| `POST /watchlist/items` | CSRF; `201`; `409 already_on_watchlist`, `422 instrument_inactive`, `422 watchlist_full` |
| `DELETE /watchlist/items/{id}` | CSRF; `204`, positions compacted |
| `PUT /watchlist` | CSRF; a subset of current items in the new order; `400` with `details.reason` `duplicate` or `not_on_watchlist` |
| `GET /market-watch` | `{generated_at, items:[Row]}` ordered by position |

(source: raw/2026-10-07-market-data.md §API, REST)

**Request rules.** Query strings are strict: an unknown, repeated or unparseable parameter is a 400. Ids are URL-encoded (`%40` for `@`); an encoded `/` is a 404. Checks run query (400), then instrument (404), then timeframe (422); a timeframe a route never serves (`5m`, or `1m` on indicators) is a 400. The error envelope stays `{"error","code","requestID"}` (the PRD's `request_id` is an erratum, R1), with an optional `details` (`field`, `reason`) on `400 invalid_request` (R2) (source: raw/2026-10-07-market-data.md §API; §Concept, ORCH-7).

**New error codes.** `unknown_instrument` 404, `timeframe_unavailable` 422, `already_on_watchlist` 409, `watchlist_full` 422, `instrument_inactive` 422, and for `/ws` `origin_rejected` 403, `realtime_unavailable` 503 and `too_many_connections` 429. All are in `AllCodes()` and the service README (source: raw/2026-10-07-market-data.md §API, New error codes).

**Two more instrument routes since charting (slice 5).** `GET /instruments/{id}/chart` (bars joined with indicators, plus overlays; see [[chart-read-api]]) and `GET /instruments/{id}/signals` (one instrument's signals over a span; see [[signals-read-api]]) sit on the same gated group. They follow the same query, instrument, timeframe check order, and reuse `unknown_instrument` and `timeframe_unavailable` with no new code. The slice-1 `candles` and `indicators` routes are unchanged (source: raw/2026-10-16-charting.md §API, Conventions; §Files touched, tidewatch-service, Unchanged; §Cross-cutting links).

## Watchlist and the Market watch row

- **Seeding.** The first `GET /watchlist`, `GET /market-watch` or mutation creates the watchlist with the default eight instruments, once even under concurrent first access. Emptying it never re-seeds it. The cap is 50 (MD13).
- **Notification.** Every committed change, seeding included, publishes `md:subscriptions` once, best effort; a failure logs `md_subscriptions_publish_failed` and never rolls back (see [[redis-market-contract]]). Watchlist edits write no audit event.
- **Storage.** `watchlists` (one per user, `ON DELETE CASCADE` from `users`) and `watchlist_items` with a `UNIQUE (watchlist_id, position) DEFERRABLE INITIALLY DEFERRED` constraint so a reorder is checked at commit.
- **Row shape.** `{instrument_id, display_symbol, name, asset_class, venue_label, quote_ccy, tick_size, last, change_24h, strip, current_zone, status, signals}`. `change_24h` is measured against the last `candles` close at or before 24 h ago (or the previous EOD session for a `1d` base), `pct` to 4 decimals. `strip` is up to 48 cells of `1h` or `1d` zones, oldest first, and `current_zone` equals the last cell. `signals` was always `null` until slice 3a (see below). How `last` and `status` are chosen is on [[redis-market-contract]].

(source: raw/2026-10-07-market-data.md §API, Watchlist and Market watch row; §Database, Migration A)

**`signals.today` (slice 3a, tidewatch-service PR #8, merge `2f9854f`).** `"signals": {"today": <int ≥ 0>}` replaces `"signals": null`, and the merged service never sends null.
- `today` counts the row's `signals` with `created_at` in `[D, D + 24h)`, where `D` is `BangkokDayStart(generated_at)`: local midnight in a fixed +07:00 zone, with no tz database.
- The upper bound is explicit (R6), so a row at 00:00:10 the next Bangkok day does not count.
- The count is **one batched query** per read (`instrument_id = ANY($1)`, grouped, served by `signals_instrument_created_idx`). An id missing from the result reads 0.
- A failed count fails the read, like the rows and strips (R10).
- The row ids are the watchlist's instrument ids, so **the count exists only for watchlist instruments**. Signals for other instruments are stored but appear on no screen until slice 4's Signals page.
- **Web.** `MarketWatchRow.signals` is `{ readonly today: number } | null`. The strict reader accepts `null` or an object whose `today` is a non-negative safe integer; anything else refuses the body (MW-22). Live `signal` frames raise the count once per `signal_id` without a reload, and the 5-minute reload resyncs it (see [[signal-message-contract]]). The cell's look is on [[design-system-decisions]].
- **Compatibility.** A new web with an old service accepts `null` and shows the dash. A new service with an old bot shows 0 everywhere.

(source: raw/2026-10-11-signals-ingest.md §API, `GET /market-watch` row and Compatibility; §Components, Row model; §Concept, What the user sees)

**Since signals context (2026-10-30), the count includes coverage signals.** The Market watch count counts both `signals.origin` values, so a coverage signal (`origin = 'context'`, impact `0.0000`, at most one per instrument per Bangkok day) adds 1 to `today` like any signal. It arrives as an ordinary C-SIG-1 frame. In production no coverage signals are written until `context` is in the bot's collectors value (see [[context-features-and-coverage-signals]]) (source: raw/2026-10-30-signals-context.md §Concept, How it runs, 6. Never a trigger; §API, 3. Signals routes, C-SIG-1).

## Market watch UI

The Overview route now loads `feat-overview/Overview`: a page header and the Market watch section (filter tabs All assets, Stocks, Crypto, Gold; *Add instrument* and *Edit list* dialogs; a six-column `table.tide` with Instrument, Last price, 24h change, Market tide · 48h, Current zone and Signals). Status tags are *Live*, *Delayed 15 min*, *EOD*, *Synthetic*, *Closed · opens EEE HH:mm* (Bangkok) and *Stale*, with Stale outranking the others. The other five screens keep their empty states. The store `MarketWatchService` is component-provided and reloads every 5 minutes, after a reconnect, after a `zone` message for a visible row, and after an add or save. The table is not a live region and prices change in place with no highlight (MW-23). Component and token details are on [[design-system-decisions]]; the socket client is on [[realtime-websocket]] (source: raw/2026-10-07-market-data.md §Components, tidewatch-web).

**Since slice 2 (2026-10-08).** Overview's `.content` now holds, in order: the portfolio hero (`app-portfolio-hero`), the KPI strip (`app-kpi-strip`), then the unchanged `app-market-watch` (SIM10). Two `.content section`s now exist, so `e2e/src/market-watch.spec.ts:103` was narrowed to Market watch's own section (ORCH-22). The Trade screen is no longer an empty state. Positions on Trade update *Last* from the same `/ws` stream, and nothing new was added to `/ws`. See [[simulation-engine]] (source: raw/2026-10-08-simulation-engine.md §Components; §Concept, ORCH-22; §API).

**Since charting (slice 5; tidewatch-web #14 and tidewatch-service #11, merged 2026-10-16, not deployed).** See [[charting]].
- **The symbol is a link.** `.asset-symbol` became `a.asset-symbol[routerLink]` to `["/chart", id]`, with the accessible name `aria-label="{symbol} chart"` (CH-W-29). The visible text stays exactly the symbol, and the row itself stays non-interactive (MW-10). `feat-overview/market-watch.spec.ts` gained `provideRouter([])` only; without it, 23 tests failed with NG0201.
- **The strip is unchanged here.** `app-tide-strip` gained a `slots` input whose default stays 48, so Market watch's output is byte-identical. The Chart passes 96 (see [[design-system-decisions]]).
- **The Chart agrees with this row.** The chart route's `right_now.last`, `change_24h` and `status` are built by Market watch's own row builder at the same `generated_at`, and its zone run follows the same rule over rows that exist (see [[chart-read-api]]). On the preview, 8 watchlist instruments were read four ways in the same minute (API `current_zone`, the chart's `right_now.zone`, the *Right now* DOM, the Market watch DOM), and all agreed (FR-CH-E2E-004).
- **The Chart reads `/market-watch` too,** for its *Instrument* select, its header identity and the strip timeframe.

(source: raw/2026-10-16-charting.md §Components, Market watch link and the 96-slot strip and `ChartService`; §API, `GET /instruments/{id}/chart`; §Concept, Review history (web plan r3); §Test plan, Acceptance status FR-CH-E2E-004)

## Gotchas worth remembering

- **Binance TH refuses klines spans over 7 days** (`400`, code `-4088`), a limit neither the PRD nor the venue docs state. It broke the first preview's 180-day backfill. Details and the fix are on [[market-data-worker]].
- **OANDA is unavailable for the owner's region, and keys can never exist.** At merge, `XAUUSD@oanda-demo`, `GOLD965THB@mts`, `GO@tfex` and `GOLD9999USD@mts` had no price source and read Stale while open (FU-4). Since the same-day fix, XAU/USD is priced from Binance TH `XAUTUSDT` and the USD/THB `USDTTHB` proxy is activated at `serve` start; `USDTHB@oanda-demo` still has no live source and the OANDA collector stays dormant. Leave the OANDA pair empty and never ask for keys. See [[gold-feed-xaut-proxy]] and [[market-data-worker]].
- **Never refresh a continuous aggregate with a NULL start or past the 180-day retention.** It silently deletes materialized buckets, and `candles_1d` is the only daily history for seven instruments past 180 days. See [[market-timeseries]].
- **Live US checks need the US regular session**: 20:30–03:00 Bangkok under EDT, 21:30–04:00 after 2026-11-01. Overnight rows read `stale` because the overnight session has no IEX trades.
- **First start is slow on purpose.** Each Binance TH pair takes 260 backfill windows and waits for its aggregate flush before going live; Alpaca `1Day` and the lists do not run at start.

(source: raw/2026-10-07-market-data.md §Concept, Preview findings; §Database, Writer rules; §Components, Rollout, operations and recovery; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, The correction)

## Operations

- **Bring-up on the owner compose (FR-MD-INFRA-001, not yet done).** Create `.env` from `.env.example` (the root `.env` does not exist yet), set `POSTGRES_PASSWORD` and, for the first start, `TIDEWATCH_ADMIN_PASSWORD` (retired since accounts and roles: the first start now needs `TIDEWATCH_OPERATOR_PASSWORD`, `TIDEWATCH_OPERATOR_PHONE` and a code sender; see [[operator-console]]), optionally set the Alpaca pair, leave the OANDA pair empty (OANDA is unusable for the owner; gold comes from Binance TH, see [[gold-feed-xaut-proxy]]), then `docker compose up -d --build` and `docker compose ps -a`. Expect `tidewatch-bot` healthy and `migrate` `Exited (0)`.
- **Compose changes.** The bot is now `restart: unless-stopped` with `stop_grace_period: 15s`, waits for `migrate` (completed) and `redis` (healthy), has a `wget` healthcheck on `127.0.0.1:9091/ready` and no published ports. `db` runs `postgres -c timescaledb.telemetry_level=off` (OWNER-3), which recreates the container on the next `up` while keeping the volume (untested). The compose header claims `up -d --build --wait` should now work; that is unconfirmed until a real start.
- **`.env.example`** gained empty `ALPACA_KEY_ID`, `ALPACA_SECRET_KEY`, `OANDA_DEMO_TOKEN`, `OANDA_DEMO_ACCOUNT_ID`, `GOLD965_PREMIUM_SEED_THB`, `TIDEWATCH_HTTP_CONTACT` and `MARKET_DATA_COLLECTORS`.
- **Migration order.** Migrations merge before or with the service and bot. Until migration C is applied, the service answers `503 not_ready` on `/ready`, `/auth/*`, every market route and `GET /ws`. `timescale/timescaledb-ha:pg18` is a floating tag; an image bump may need the migrations harness updated. Migration D (the XAU feed row) is later than C and not pinned; `/ready` tolerates it, and the bot should be restarted after `migrate` applies it so the proxy activation and the XAU backfill are logged (see [[centralized-migrations]], [[gold-feed-xaut-proxy]]).
- **Lost admin password.** The service CLI reset (`admin set-password`), never a down migration. Since accounts and roles (2026-10-29) the command is `user set-password`, with `admin set-password` as a deprecated alias for one release. Operators reset with `operator set-password` (source: raw/2026-10-29-accounts-roles.md §API, CLI).

Worker recovery notes (Redis outage, missing keys, restart gaps, interrupted backfill, two serves) are on [[market-data-worker]] (source: raw/2026-10-07-market-data.md §Components, Workspace root and Rollout, operations and recovery).

## Verification

| Project | Result |
|---|---|
| migrations | `make migrate-validate` and `make check-disposable-db` passed at `d77efa8`: 43/43 commands, 641 PASS, 0 FAIL, on PostgreSQL 18.6 and TimescaleDB 2.30.2 |
| service | `make ci` passed at `04dec78`; integration `ok 169.822s`, 2,091 PASS, 0 SKIP, 0 FAIL, 0 DATA RACE against throwaway TimescaleDB and loopback Redis; `make check-image` passed after an infrastructure retry |
| bot | `pnpm nx run-many -t lint test typecheck build` passed at `06a9ab8` (market-data 354, worker 39, shared 56, indicators 22); `sql-integration.sh` passed at `a289b26` and was not re-run for the two later fixes |
| web | 948 unit tests at `a0ac23a` (also under `TZ=America/New_York`); 949 after `a7cb23a`, build not re-run |
| web E2E | Playwright on the preview's isolated DB: 273 passed, 2 skipped (gated live specs), 0 failed; the 3 live specs passed with `E2E_LIVE_MARKET_DATA=1` |

Of 61 acceptance IDs, 44 passed, 14 passed with open parts, 3 are pending after merge (FR-MD-WEB-011, FR-MD-INFRA-001, FR-MD-DOC-002), and none failed. Reviews: migrations code and security r1; service code r3 and security r2 approved; bot code and security approved at r3, r4 and a code confirmation at `06a9ab8`; web 5/5 approved in round 2. A passing build command never marks a live, browser or SQL-on-live ID verified (source: raw/2026-10-07-market-data.md, summary block and §Test plan).

The preview was compose project `forge-0199b29a-mdata-d9d3e428` with an isolated database and retained volumes. Preview evidence spans three bot revisions (`9bf762d`, `99c8511`, `06a9ab8`); Alpaca keys were loaded from 11:44 Bangkok and OANDA never (source: raw/2026-10-07-market-data.md §Test plan, Stages; §Open questions, Bookkeeping drift).

## Open items

- **Pending, US regular session.** Live IEX bars and the 5-minute SIP reconciliation (FR-MD-BOT-003), a live NVDA/AAPL change (FR-MD-E2E-001), the NVDA part of FR-MD-BOT-008 and FR-MD-E2E-002.
- **Pending after merge.** FR-MD-INFRA-001 and the owner-compose re-runs of FR-MD-BOT-001, FR-MD-BOT-008, FR-MD-E2E-002 and FR-MD-E2E-003 (blocked until the owner creates the root `.env`); FR-MD-WEB-011 (`DESIGN.md`, see [[design-system-decisions]]); FR-MD-DOC-002 (the final report).
- **Owner decisions.** A9 (MTS hours 07:00–03:00), A16 (UTC-aligned US hourly strips), OC-1 (straight quotes in the all-listed line), OC-2 (DEV-WEB-CAPTION).
- **OI-1.** The licence statement for piriya33's *CDC ActionZone V3 2020* was not captured; the Pine source is not vendored.
- **Unverified.** Live `run list-refresh`, a 24 h Binance TH soak and real 429/418 (A5), live tick-to-browser timing, the preview axe run and the Closed, Delayed and Synthetic tag renders, and an ETH/THB price change. The XAU/USD-dependent checks (FU-4) passed on the fix preview on 2026-10-07; live weekend gating and the premium median path are still unobserved (see [[gold-feed-xaut-proxy]]).
- **Follow-ups.** FU-2 (`prom-client` deprecated), FU-3 (re-mark indicators after catch-up), FU-5 (log the concurrent-refresh transient at warn). FU-1 is resolved, and FU-4 (replace OANDA as the XAU/USD source) was resolved by the XAUT fix on 2026-10-07, which recorded one new pre-existing follow-up, FU-FIX-1 (Binance TH stream silence can leave Binance TH-fed rows Stale for up to ~3 min before the proactive reconnect; see [[market-data-worker]]). OpenAPI and Bruno for the REST routes were skipped because `tidewatch-apis` is not a git repo. Slice-0 carry-overs remain (see [[foundation-auth]]).
- **PRD §10 known gaps.** Thai stocks are end-of-day only; Webull's overnight session has no data; GO and GOLD9999USD carry no basis or dealer spread; US hourly bars are UTC-aligned; the signals column is a placeholder (closed by slice 3a on 2026-10-11, see [[signals-ingest]]); chart use of `packages/indicators` is deferred to slice 5. The `/ws` cap and fan-out are per process (SV15).

(source: raw/2026-10-07-market-data.md §Open questions)

## Out-of-date documents

Per D17 these were not edited:

- `documents/02-architecture.md` §3 says "1m/5m for US where available, 15m otherwise"; intraday US bars are now SIP 1m (MD9). §10's storage table lacks `candles_eod` (MD4).
- `documents/features/01-market-data-and-instruments.md` calls `top20_binance_th` "top 20", but it holds about 10 THB pairs today (MD7).
- The PRD's envelope field `request_id` is an erratum for `requestID` (R1).
- The specs' OANDA practice source (intent, PRD A3) does not hold for the owner's region. Since 2026-10-07 the deviation is recorded in `prd.md` §10 ("Deviations recorded after the build") with a decision-history row; the §4.1, §4.4 and A3 text is left as written by design (see [[gold-feed-xaut-proxy]]).

**Bookkeeping drift.** `verification.md` was last updated before the merge and still says no code PR is merged; `state.json` lanes and some result text predate the merge and the Alpaca keys. The merge facts come from `state.json` (`mergeCommit`, `mergedAt`) (source: raw/2026-10-07-market-data.md §Open questions). After the XAU fix the verification ledger gained a §10 post-fix close-out, and FU-4, OI-4 and GAP-GOLD-LIVE are marked resolved in the feature state (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Open questions).

## Related pages

- [[foundation-auth]] — Slice 0, which this slice builds on
- [[instrument-master]] — instrument ids, aliases, universe lists and calendars
- [[market-timeseries]] — candles, aggregates, retention and the CDC indicators
- [[market-data-worker]] — the bot's collectors, jobs, status publisher and venue gotchas
- [[redis-market-contract]] — the bot-to-service Redis keys and channels
- [[realtime-websocket]] — the service's `GET /ws` hub and the web socket client
- [[gold-feed-xaut-proxy]] — the 2026-10-07 fix that priced XAU/USD from Binance TH XAUT and closed FU-4
- [[centralized-migrations]] — migrations A–D and the required version `20261006131346`
- [[auth-model]] — the gate chain on every market route and the `/ws` session re-check
- [[request-protection]] — `/ws` exact-origin check and CSRF on watchlist mutations
- [[forge-preview-gateway]] — `/api/ws` through Caddy and the bot in the preview
- [[design-system-decisions]] — the new web components and the pending `DESIGN.md` refresh
- [[simulation-engine]] — Slice 2, which trades on these prices and adds the portfolio hero above Market watch
- [[signals-ingest]] — Slice 3a, which fills the Market watch Signals column with today's count
- [[signal-message-contract]] — the live `signal` frame that raises the count
- [[charting]] — slice 5, which links each symbol to its chart and copies this row into *Right now*
- [[chart-read-api]] — the chart route that reuses Market watch's row builder
- [[context-features-and-coverage-signals]] — coverage signals, which the `signals.today` count includes
