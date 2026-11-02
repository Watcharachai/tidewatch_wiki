# Market data and instruments (Slice 1)

> Slice 1 gave Tidewatch its market data. Three goose migrations added the instrument master and its seeds (A), the TimescaleDB time series (B) and the 2026–2027 calendar exceptions (C). The service's `RequiredSchemaVersion` moved to C's version, `20261006131346`. `tidewatch-bot` became a long-running worker with two new packages: `packages/indicators` (CDC ActionZone, EMA, ATR14) and `packages/market-data` (collectors, the indicator job, list refresh, subscriptions, staleness and status, the Redis publisher and metrics). It serves `/health`, `/ready` and `/metrics` on port 9091. `tidewatch-service` gained 11 gated market REST routes, the `GET /ws` hub fed from Redis, eight new error codes and realtime metrics. `tidewatch-web` replaced the Overview placeholder with the Market watch card. All four PRs were merged by merge commit on 2026-10-07 at 13:00:54 Bangkok (06:00:54Z): migrations `cb93cd5`, service `734ce35`, bot `5a60477` and web `5611d79`. Nothing is deployed beyond the local Forge preview, and the owner's compose stack has not been started. On the preview, the first-start Binance TH backfill failed against an undocumented 7-day klines limit. That P0 was fixed in bot `99c8511` and `06a9ab8`. Alpaca ran live with the owner's keys. OANDA turned out to be unavailable for the owner's region, so the four gold rows have no price source (FU-4, deferred). The acceptance ledger covers 61 IDs: 44 passed, 14 passed with open parts, 3 pending after merge and 0 failed.

## Concept

**Problem.** Prices are what every later slice is graded against. The simulation (slice 2) cannot fill an order without a bar. Signals (slice 3) need a stable instrument identity to resolve to. The tide strip is the product's signature. Before this slice, Overview was an empty state ("Nothing to watch yet"). The service had no market routes, Redis client or WebSocket library, and its router tests expected `/ws` to answer 404. The bot was a one-shot database check, and the migrations held only the extensions and the auth tables.

**Sources.**
- `tidewatch-specs/market-data/intent.md`: confirmed on 2026-10-06, with decisions MD1–MD14 and outcomes O1–O8.
- `prd.md`: behaviour (§4), schema (§5), REST, `/ws` and Redis contracts (§6), design (§7), operations (§8), acceptance IDs `FR-MD-*` (§9), known gaps (§10) and assumptions A1–A16.
- `build-prompt.md`.
- The visual target is the Market watch section of `documents/mockups/tidewatch-redesigned.html`, with the departures listed in PRD §7.2.
- The acceptance ledger is `.forge/features/market-data/verification.md`. It is the source of truth for passed, unverified and pending.

### Outcomes O1–O8

The status column follows the ledger (§5). "Preview" means the Forge preview with an isolated database. It is never the owner's stack.

| # | Outcome | Status |
|---|---|---|
| O1 | Live Market watch | Passed in part, on the preview. The eight rows render. BTC/THB changed without a reload, PTT.BK shows its EOD close, and NVDA and AAPL are priced from the Alpaca SIP backfill, so 5 of 8 rows have a price. A live NVDA/AAPL change is pending (US regular session). The gold rows are unverified (FU-4). FR-MD-WEB-011 and FR-MD-INFRA-001 are pending after merge. |
| O2 | Durable, gap-free history | Passed for the migrations and on the preview: `candles_1h` equals the manual `GROUP BY` for 48 of 48 hours, and a restart left 0 missing minutes after 10 min 30 s down (BTCTHB and ETHTHB). Open: the NVDA SIP part (US session), the XAUUSD part (FU-4), the owner-compose re-runs and GAP-BOT-CATCHUP-IND (FU-3). |
| O3 | Correct CDC zones | Passed. The fixture matches bar for bar, the edge cases pass, `step` equals the full series, and on the preview the label equals the strip's last cell. OI-1 (the CDC script's licence statement) is open. |
| O4 | Instrument identity and universes | Passed at build time. The live `run list-refresh` transcript was not captured. |
| O5 | Watchlist control | Passed, including the Playwright journey on the preview. |
| O6 | Honest data status | Staleness, synthetics and calendars passed. The preview rendered the Live, EOD and Stale tags only. The live half of the Gold 96.5 within-1 % check is unverified: there is no XAU/USD source, and it also needs a GTA publishing day. |
| O7 | Safe realtime | Passed. Through the preview gateway, `/api/ws` gave 401 without a cookie, 101 with a session, and 403 for a foreign or missing Origin. Publish-to-client p99 was 4.99 ms on loopback. A live tick-to-browser timing was not captured. |
| O8 | Within free limits and terms | Passed by counters and tests, with terms recorded in all four READMEs. FR-MD-DOC-002 is pending. Live runs under the limits are evidenced only by the preview's Binance TH and Alpaca backfills. |

### Product decisions (intent, MD1–MD14)

- **MD4, storage split.**
  - `candles` holds intraday bars only: 7-day chunks, columnstore after 30 days, retention 180 days.
  - The new `candles_eod` hypertable holds daily-native bars with no retention, so retention can never delete daily history.
  - Each instrument carries `base_timeframe` (`1m`, `5m`, `1d`) and `daily_source` (`aggregate` or `eod`).
  - `candles_daily` picks the daily source per instrument.
  - A timeframe finer than an instrument's base is refused with `422 timeframe_unavailable`.
- **MD8, Binance TH follows live behaviour, not its docs.**
  - The stream uses the bare endpoint with `SUBSCRIBE` frames.
  - Klines are budgeted at weight 5, with a 4,800 per minute cap.
  - The collector reconnects before 24 h.
  - The first start backfills 180 days of 1m bars.
  - The preview then found a limit the docs do not state (see "Preview findings" below).
- **MD9, US stocks.**
  - Live minutes come from the Alpaca IEX websocket (`b` and `u` bars, at most 30 symbols).
  - Every 5 minutes, SIP 1m bars replace every window older than 15 minutes.
  - Backfill uses SIP 1m.
  - Watchlist names beyond 30 are polled with a 15-minute delay.
  - One limiter allows 180 requests per 60 s.
- **MD12, CDC rules.** They follow piriya33's *CDC ActionZone V3 2020*: close source, EMA 12/26, and `null` on ties and during warm-up. The fixture has 500 BTCTHB 1h bars: 200 warm-up bars, then 300 compared bar for bar against an independent Python reference.
- **MD13, the owner's ten defaults.**
  - The worker runs continuously, and a missing secret disables only its collector.
  - The watchlist is seeded with eight instruments on first access and holds at most 50.
  - Realtime priority is watchlist position, then `realtime_requested_at`.
  - The row statuses are Live, Delayed 15 min, EOD, Synthetic, Closed · opens … (Bangkok) and Stale.
  - 24h change is measured against the price 24 h ago.
  - `/ws` checks the cookie and Origin, then re-checks the session every 60 s.
- **MD14.** The intraday backfill depth equals the 180-day retention. Longer daily history comes from `candles_eod` or `candles_1d`.
- **Other product decisions:**
  - MD1: the Gold 96.5 premium is the 30-day median of `GTA mid − raw`, using earlier days only, with a seed until 5 observations exist.
  - MD2: `GOLD9999USD@mts` is a synthetic of the XAU/USD mid.
  - MD3: the `mts` calendar is Mon–Fri 07:00–03:00 Bangkok.
  - MD5: Thai stocks come from Yahoo EOD, with a SET-website close check.
  - MD6: the universe lists come from Wikipedia, the Nasdaq API, SSGA and the SET site.
  - MD7: `top20_binance_th` holds up to 20 THB pairs (about 10 exist today).
  - MD10: CoinMarketCap is deferred to slice 6.
  - MD11: TradingView is not a data source.

### Build and owner decisions (state.json)

- **ORCH-1.** The migrations repo is a workspace resource, not a registered project. Its steps were folded into the service plan as MIG1–MIG4 and shipped as their own PR, merging before or with the service and bot PRs.
- **OWNER-1.** Dependency-gated parallel lanes:
  - service: MIG steps, then S steps;
  - bot: S1–S5 at once, S6 onwards after MIG4 verified;
  - web: at once, against mocks.
- **ORCH-7, the envelope (R1).** The envelope keeps slice 0's `requestID`; the PRD's `request_id` is an erratum. A `details` object was added (R2), and an `unsubscribed` acknowledgement was added to `/ws` (R3).
- **ORCH-10.** A row without `px:last` is `stale: true` with session `unknown`, and the web shows *Stale*.
- **ORCH-11 (R8).** A `/ws` frame over 64 KiB closes the socket with 1009 at once. This is a DoS bound and a recorded deviation.
- **ORCH-12.** Indicator values (`close`, `ema12`, `ema26`, `atr14`) are decimal strings on REST and in the forwarded `zone` message. The database columns stay `double precision`.
- **ORCH-22 and ORCH-25.** The Add instrument dialog gained a polite status line: `Everything matching "<query>" is already on your list.`. It uses straight quotes, which is OC-1.
- **ORCH-26.** DEV-WEB-CAPTION, which is OC-2.
- **ORCH-27.** One batched `InstrumentRepo.Existing` query checks a whole `/ws` subscribe.
- **ORCH-30.** A row's `last.ts` is capped at `generated_at`.
- **ORCH-35.** Scheduled runs inside runners take no `job:<name>` lock.
- **ORCH-36.** The process-level advisory lock `runner:serve` makes serving all-or-nothing, so `px:last` and `status` keep a single writer.
- **ORCH-37.** A docs-only bot polish (`9bf762d`). The catch-up/indicator gap became FU-3.
- **ORCH-38 and ORCH-39.** The preview P0 fix round and the closed-cutoff fix (see below).
- **OWNER-2 and ORCH-21.** At the owner's request for speed, each contract command runs once on the final tree, and reviews start as soon as a lane's last step verifies.
- **OWNER-3, preview decisions.**
  - The owner adds the provider keys to the preview secrets file personally; Claude never handles them.
  - Volumes are retained, and the database mode is isolated.
  - TimescaleDB telemetry is off (`timescaledb.telemetry_level=off`) on both the preview and the owner-compose `db`.
- **OWNER-4.** OANDA is unavailable for the owner's region. A replacement XAU/USD source is deferred (FU-4), and the build proceeded with the Alpaca keys only.
- **OWNER-5.** "The only real remaining gap is the gold price (FU-4); merge the four PRs." The orchestrator merged with `--match-head-commit` at the reviewed and tested heads, in the order migrations → service → bot → web.
- **Libraries.**
  - Service: `github.com/coder/websocket v1.8.15`, chosen over gorilla and `x/net/websocket` for its close-code and ping control. `github.com/redis/go-redis/v9 v9.9.0`. The test-only `github.com/alicebob/miniredis/v2 v2.37.0` (SV1).
  - Bot: `ws` 8 instead of Node's global WebSocket (A12), because the global one exposes no ping event and sends `User-Agent: node`. Also `redis` 6, `prom-client` 15 (deprecated upstream, FU-2), `luxon` 3, `node-html-parser` 9 and `fflate` 0.8.

### Preview findings

**1. P0: Binance TH rejects klines spans over 7 days.**
- **What failed.** On the first preview (bot `9bf762d`, `http://127.0.0.1:54736/`), the first-start backfill sent 180-day spans. The venue answered `400` with code `-4088`, "Maximum time interval is 7 days.", and `binance_th_backfill_failed` was logged 8 times.
  - The backfill never completed, so BTC/THB and ETH/THB never went live, and FR-MD-INFRA-002 failed.
  - Neither the PRD nor the venue docs name this limit. A probe confirmed it (`evidence/root/preview/04-binance-th-7day-probe.txt`); 7 days plus 1 minute still passed live.
- **Fix in `99c8511` (ORCH-38).** The backfill pages in back-to-back 1,000-minute windows (`BACKFILL_WINDOW_MS`, one full `limit=1000` page):
  - Each window ends at `min(now, start + 60,000,000 ms − 1)`.
  - A 180-day first start is 260 calls per instrument, 1,300 weight of the 4,800 per minute.
  - The backfill ends only when a window reaches now. An empty or short window moves on and leaves the cursor where it was.
  - `fetchKlines` throws a `RangeError` for a span over 7 days, before charging the limiter or sending anything.
  - The fake transport answers any span over 7 days with the captured 400 (`packages/market-data/fixtures/binance-th/klines-error-4088.json`), so specs cannot pass on a request the venue refuses.
  - Tests were red before the fix (`evidence/tidewatch-bot/review-fix-r3/00-red-before-fix.log`). Code and security round 4 approved it at `99c8511`.
- **Follow-up fix in `06a9ab8` (ORCH-39, code r4 Minor 1).**
  - The "closed" cutoff used to be read after the response arrived, so a minute that closed while the request was in flight could be stored as final with partial OHLCV.
  - The filter is now `row.closeTime < now`, where `now` is read before the request.
  - The README's `binance_th_metadata_failed` row gained `venue_code`.
  - The code reviewer's confirmation approved it (market-data 354/354).
- **Result on `06a9ab8`.** FR-MD-INFRA-002 passed at 09:38 Bangkok.
  - BTCTHB held 259,210 bars and ETHTHB 259,158, from 2026-04-10, with no `binance_th_backfill_failed`.
  - `px:last` was live, and the BTC price changed within 20 s.

**2. OANDA is unavailable.**
- The owner's Thai-region account is with OANDA Global Markets, which offers MT5 only. OANDA's v20 docs exclude that division, so `OANDA_DEMO_TOKEN` and `OANDA_DEMO_ACCOUNT_ID` can never be obtained.
- The OANDA lines in the preview secrets file were cleared before the preview restarted, and the OANDA collector stays disabled (`collector_disabled`).
- **Consequences.**
  - `XAUUSD@oanda-demo` (XAU/USD), `GOLD965THB@mts` (Gold 96.5), `GO@tfex` and `GOLD9999USD@mts` (Gold 99.99) have no price source and read Stale while open. `USDTHB@oanda-demo` has no live source either.
  - For the Gold 96.5 formula and premium check, USD/THB falls back to the Binance TH `USDTTHB` proxy (A3). The proxy is unit-tested only.
- **FU-4, deferred by the owner on 2026-10-07.** Choosing a replacement XAU/USD source is a scope change for a new `/forge-spec` run. It needs to weigh free-tier 1m availability, spot against futures, terms and the effect on the premium check. An MT5 Python bridge is Windows-only.

**3. Alpaca is live with the owner's keys.**
- The preview was restarted at 11:44 Bangkok (`http://127.0.0.1:62244/`).
- The IEX stream authenticated (`alpaca_stream_authenticated`, recorded in `state.json`).
- The SIP 1m backfill covered 180 days: NVDA 117,181 bars and AAPL 104,196, from 2026-04-10 to 2026-10-06 23:59Z.
- `/market-watch` showed NVDA 239.86 and AAPL 333.99. Both read `stale` in the US overnight session, which has no IEX trades.
- The indicator job then wrote NVDA 7,872 15m and 1,968 1h rows, and AAPL 7,871 15m and 1,968 1h rows.
- A6 is confirmed for SIP history and IEX auth.
- Live IEX bars and the 5-minute SIP reconciliation need the US regular session: 20:30–03:00 Bangkok under EDT, 21:30–04:00 after 2026-11-01.
- The `1Day` rows in `candles_eod` wait for the 05:30–08:00 Bangkok slot. That is documented first-start behaviour.

**4. A concurrent aggregate refresh failed, then recovered.**
- After the Alpaca backfill, the bot's deferred flush collided with TimescaleDB's own refresh policy on `candles_15m` ("concurrent refresh") at 04:43:14Z. It logged `aggregates_refresh_failed` at level 50 and carried the range.
- The 5-minute aggregate maintenance retry refreshed it at 04:47:50Z (5 slices, 2 instruments). The indicator rows followed.
- This is an expected transient that needs no action. It logs at error level, though, so FU-5 proposes logging it at warn with its own reason, or retrying sooner.
- Evidence: `evidence/root/preview/alpaca/02-after-retry.txt`.

### Assumptions A1–A16

| ID | Assumption | Outcome |
|---|---|---|
| A1 | Aggregate creation may need `NO TRANSACTION` | Settled: B runs in goose's default transaction. `WITH DATA` is refused inside a transaction, so the aggregates are created `WITH NO DATA` with their policies. `refresh_continuous_aggregate` cannot run in a transaction. |
| A2 | FKs and CHECKs on hypertables, compressed-chunk upserts, current policy names | Settled. The columnstore names are used, constraints are enforced on chunks, and `ON CONFLICT DO UPDATE` into a compressed chunk works. |
| A3 | The owner's OANDA practice division offers XAU_USD and USD_THB | Moot and unverified: no v20 account can be obtained (FU-4). USD/THB uses the `USDTTHB` proxy (unit-tested only). |
| A4 | Official session hours and holidays | Settled for the build. Migration C's header cites 21 sources with SHA-256 hashes. DEV-A4-SET applies. |
| A5 | Binance TH pings, 24 h lifetime and limits | Partial. The stream and the 180-day backfill ran live, and the 7-day klines rule was found. No 24 h soak was run, and real 429/418 were never exercised. |
| A6 | Alpaca free-plan SIP and IEX behave as documented | Confirmed on the preview for SIP history and IEX auth. Live IEX bars are pending (US session). |
| A7 | Yahoo answers `Mozilla/5.0` without a crumb | Settled. The first live load on the preview loaded 1 of 1, and PTT.BK shows 41.50. The SET close check was not inspected. |
| A8 | The Nasdaq API needs a browser User-Agent | Partial: one build-time capture answered 200, but no live bot run has happened. |
| A9 | MTS hours are 07:00–03:00 | **Pending owner review.** The official pages say only "24 hours". |
| A10 | Webull overnight is Sun–Thu 20:00–04:00 ET | Settled. |
| A11 | Real-time aggregation must be set explicitly | Settled: `materialized_only = f` on all three aggregates. |
| A12 | Node's global WebSocket is usable | Rejected; the `ws` package is used. |
| A13 | GTA JSON stays available, with the classic page as fallback | Partial: build-time captures only, with no live poll. |
| A14 | gin's hijack works for the upgrade | Settled by integration tests with a real client. |
| A15 | The formula plus a premium near 0 tracks GTA within 1 % | Unverified (FU-4; also needs a GTA day). |
| A16 | UTC-aligned US hourly strips are acceptable | **Pending owner review** on the preview. NVDA and AAPL now have 1h rows to judge from. |

**Accepted PRD deviations.**
- **DEV-A4-SET.** The SET afternoon session is seeded 14:00–16:40, not the PRD's 14:30. SET opens at a random time between 13:55 and 14:00, so 14:00 is the latest possible open.
- **DEV-WEB-CAPTION.** *History loading* is drawn in the empty strip slots only when the whole caption fits. Otherwise a `title` carries it. The accessible name always ends ", history loading". The owner's acknowledgement is pending (OC-2).

## Database

All schema lives in `tidewatch-migrations`, the centralized goose resource with one flat sequence for the single `tidewatch` database. Its base commit was `87ce578`. Review-fix commit `d77efa8` changed only the harness and docs (FU-1 folded in). The migration SQL is byte-identical to `8a158f1` (`evidence/tidewatch-service/MIG-fix-r1/sql-hashes.txt`).

### Migrations

| Order | Version | File | Content |
|---|---|---|---|
| A | `20261006100927` | `migrations/20261006100927_market_reference.sql` | 16 reference tables and their seeds |
| B | `20261006113158` | `migrations/20261006113158_market_timeseries.sql` | 3 hypertables, 3 continuous aggregates, 7 policy jobs and the `candles_daily` view |
| C | `20261006131346` | `migrations/20261006131346_market_calendar_exceptions.sql` | 99 calendar exceptions for 2026–2027, and `valid_through` |

All three run in goose's default transaction.

### Migration A: reference tables (exactly PRD §5.1)

The harness checks the table list for exactness, so a stray table fails the run. The only index beyond the keys is `instrument_aliases` on `lower(alias)`.

| Group | Tables |
|---|---|
| Venues and calendars | `venues`, `calendars` (with `valid_through`), `calendar_sessions` (ISO weekday; `ends_at <= starts_at` means the next day), `calendar_exceptions` (`closed` or `early_close`) |
| Instruments | `instruments`: the id `SYMBOL@venue` with a CHECK that `instrument_id = symbol \|\| '@' \|\| venue_id`, plus `feed`, `feed_symbol`, `synthetic_formula`, `base_timeframe`, `daily_source`, `realtime_requested_at` and `intraday_from`. Also `instrument_aliases` (`ticker`, `name`, `cik`, `isin`, `thai_name`). |
| Universe lists | `instrument_list_defs`, `list_snapshots` (`accepted`, `rejected` or `failed`, with a reason; unique accepted per `(list_code, as_of)`), `instrument_lists`, `instrument_list_status` |
| User data | `watchlists`, `watchlist_items` |
| Collectors and checks | `collector_cursors` (`bars`, `sip_reconciled`, `eod`), `gta_prices`, `gold_premium_checks`, `eod_close_checks` |

```sql
CREATE TABLE watchlists (
    watchlist_id uuid        PRIMARY KEY DEFAULT uuidv7(),
    user_id      uuid        NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE watchlist_items (
    watchlist_id  uuid        REFERENCES watchlists (watchlist_id) ON DELETE CASCADE,
    instrument_id text        REFERENCES instruments (instrument_id),
    position      int         NOT NULL CHECK (position >= 0),
    added_at      timestamptz NOT NULL,
    PRIMARY KEY (watchlist_id, instrument_id),
    CONSTRAINT watchlist_items_watchlist_id_position_key
        UNIQUE (watchlist_id, position) DEFERRABLE INITIALLY DEFERRED   -- a reorder is checked at commit
);
```

**Seeds.**
- 5 venues: `webull`, `binance-th`, `oanda-demo`, `mts` and `tfex`.
- 7 calendars with 62 session rows.
- 10 instruments and 24 aliases.
- 5 list definitions, with member bounds: `sp500` 500–510, `nasdaq100` 100–103, `set50` 50, `set100` 100, `top20_binance_th` 5–20.

| `instrument_id` | Class | Feed | Base | `daily_source` | Calendar | On the default watchlist |
|---|---|---|---|---|---|---|
| `NVDA@webull` | stock | alpaca | 1m | eod | `us-equities` | 0 |
| `AAPL@webull` | stock | alpaca | 1m | eod | `us-equities` | 1 |
| `PTT.BK@webull` | stock | yahoo | 1d | eod | `set` | 2 |
| `BTCTHB@binance-th` | crypto | binance-th | 1m | aggregate | `crypto` | 3 |
| `ETHTHB@binance-th` | crypto | binance-th | 1m | aggregate | `crypto` | 4 |
| `XAUUSD@oanda-demo` | gold | oanda | 1m | aggregate | `gold-23-5` | 5 |
| `GOLD965THB@mts` | gold | synthetic (`gold965_thb`) | 1m | aggregate | `mts` | 6 |
| `GO@tfex` | gold | synthetic (`xau_usd_mid`) | 1m | aggregate | `tfex` | 7 |
| `USDTHB@oanda-demo` | fx | oanda | 1m | aggregate | `fx-24-5` | — |
| `GOLD9999USD@mts` | gold | synthetic (`xau_usd_mid`) | 1m | aggregate | `mts` | — |

**Calendars** (local times; only the bot evaluates them):
- `us-equities`: Mon–Fri pre 04:00–09:30, regular 09:30–16:00 and post 16:00–20:00; Sun–Thu overnight 20:00–04:00 (New York).
- `set`: Mon–Fri 10:00–12:30 and 14:00–16:40 (Bangkok).
- `tfex`: day 09:45–16:55 and night 18:50–03:00 (Bangkok).
- `crypto`: every day 00:00–24:00 UTC.
- `gold-23-5`: Sun–Thu 18:00–17:00 (New York).
- `fx-24-5`: Sun–Thu 17:00–17:00 (New York).
- `mts`: Mon–Fri 07:00–03:00 (Bangkok).

### Migration B: time series (excerpt of the shipped SQL)

```sql
CREATE TABLE candles (
    instrument_id text        NOT NULL REFERENCES instruments (instrument_id),
    ts            timestamptz NOT NULL,
    o numeric NOT NULL, h numeric NOT NULL, l numeric NOT NULL, c numeric NOT NULL,
    v             numeric     NOT NULL DEFAULT 0,
    PRIMARY KEY (instrument_id, ts),
    CONSTRAINT candles_ohlc_check
        CHECK (l > 0 AND l <= least(o, c) AND h >= greatest(o, c) AND v >= 0)
);
SELECT create_hypertable('candles', by_range('ts', INTERVAL '7 days'), create_default_indexes => false);
ALTER TABLE candles SET (timescaledb.enable_columnstore = true,
    timescaledb.segmentby = 'instrument_id', timescaledb.orderby = 'ts DESC');
CALL add_columnstore_policy('candles', after => INTERVAL '30 days');
SELECT add_retention_policy('candles', drop_after => INTERVAL '180 days');

CREATE MATERIALIZED VIEW candles_1h
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT instrument_id, time_bucket(INTERVAL '1 hour', ts) AS ts,
       first(o, ts) AS o, max(h) AS h, min(l) AS l, last(c, ts) AS c,
       sum(v) AS v, count(*) AS bars
FROM candles
GROUP BY instrument_id, time_bucket(INTERVAL '1 hour', ts)   -- never GROUP BY ts
WITH NO DATA;
SELECT add_continuous_aggregate_policy('candles_1h',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
```

| Object | Settings |
|---|---|
| `candles` (on `ts`) | 7-day chunks; columnstore after 30 days (segment `instrument_id`); retention 180 days |
| `candles_eod` (on `session_date`) | `source` is `yahoo` or `alpaca-1day`, plus `fetched_at` and the same OHLC check; 365-day chunks; columnstore after 365 days; no retention |
| `indicators` (on `ts`) | `timeframe` is `15m`, `1h` or `1d`; `close`, `ema12`, `ema26` and `atr14` are `double precision`; `cdc_zone` is one of the six zones or NULL; `computed_at`; PK `(instrument_id, timeframe, ts)`; 28-day chunks; columnstore after 90 days (segment `instrument_id, timeframe`); no retention |
| `candles_15m`, `candles_1h`, `candles_1d` | UTC `time_bucket` with no origin or offset (A16); real-time aggregation on; refresh the last 3 days up to one bucket ago, every 5 minutes, 15 minutes and 1 hour |
| `candles_daily` (view) | `candles_eod` rows (`ts` = `session_date` at 00:00 UTC) for `daily_source = 'eod'`, `UNION ALL` `candles_1d` rows (`source = 'aggregate'`) for `aggregate`. No instrument gets both. |

**Writer rules** (stated in both the migrations and the bot docs):
- A writer that stores bars older than 3 days must call `refresh_continuous_aggregate` for the touched range on all three aggregates, outside a transaction.
- Never refresh over a range whose raw chunks retention has already dropped, and never with a NULL start. That silently deletes the materialized buckets, and past 180 days `candles_1d` is the only daily history for the seven `aggregate` instruments.

### Migration C: calendar exceptions

There are 99 rows in total:
- `us-equities`: 10 closed days and 2 early closes in 2026; 10 closed days and 1 early close in 2027. An early close ends at 13:00 New York.
- `set`: 20 closed days in 2026 and 18 in 2027.
- `tfex`: 20 and 18, the same list as SET's.

`valid_through` is `2027-12-31` for those three calendars. It is NULL for `crypto`, `gold-23-5`, `fx-24-5` and `mts`, which means no published list and so no coverage claim. Next year's exceptions ship as a new migration, never as an edit of C.

### Required-schema-version contract (`20261006131346`)

- `RequiredSchemaVersion` in `tidewatch-service/internal/platform/postgres/schema.go` is `20261006131346`. The anchored lookup is `ls migrations | grep -E '^[0-9]{14}_market_calendar_exceptions[.]sql$' | cut -c1-14`. The earlier `auth_foundation` lookup (`20261004153023`) is history.
- `/ready` stays `503` until C is applied. `TestReady_SchemaWait` walks 503 → 503 → 503 → 200, and `TestContract_RequiredSchemaVersion` enforces the equality.
- The bot has no compiled constant. Its `/ready` checks only the database and Redis. Its SQL harness asserts that the applied maximum equals C's version.
- Never rename, regenerate or edit C. The constant and any later dependent migration move together, and the migrations PR merges first.

### Down migrations (owner-only, local-only, never a recovery path)

- **C** deletes its exception rows and resets `valid_through`.
- **B** drops the view, policies, aggregates and hypertables. It **destroys every stored bar and indicator row**.
- **A** drops its 16 tables. It **destroys every watchlist**, which is user data.
- `down-to 20261004153023` keeps the auth tables. A wrong calendar row is fixed forward with a new migration.

## API

The base URL is the service origin (`http://localhost:3000` on the owner compose, `/api` behind the preview gateway). There is no `/api` prefix in the service.

Conventions:
- Bodies are snake_case.
- Prices, sizes and indicator values are decimal strings.
- Times are RFC 3339 UTC.
- The error envelope is `{"error","code","requestID"}`, with an optional `details` (`field`, `reason`) on `400 invalid_request`.
- Responses on the market group carry `Cache-Control: no-store`.

### REST (`tidewatch-service`; every route behind `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`)

| Method and path | Request | 2xx | Errors (besides the gate answers) |
|---|---|---|---|
| `GET /instruments` | `q` (1–64 characters: a prefix of symbol or display symbol, or a substring of name or any alias, `thai_name` included), `asset_class`, `list`, `limit` 1–50 (default 20), opaque `cursor` | `{items:[Instrument], next_cursor}`. Ordered by exact symbol match, then list membership, then symbol. | `400 invalid_request` |
| `GET /instruments/{id}` | — | `Instrument` plus `aliases`, `lists` and `status` (`null` without `px:last`) | `404 unknown_instrument` |
| `GET /instruments/{id}/candles` | `timeframe` ∈ `1m`/`15m`/`1h`/`1d` (required), `from`, `to`, `limit` 1–5000 (default 500) | `{instrument_id, timeframe, items:[{ts,o,h,l,c,v}], last_is_partial}`. `1m` reads `candles`, `15m`/`1h` the aggregates, `1d` `candles_daily`. | 400, 404, `422 timeframe_unavailable` |
| `GET /instruments/{id}/indicators` | `timeframe` ∈ `15m`/`1h`/`1d`, `from`, `to`, `limit` | `{instrument_id, timeframe, items:[{ts, close, ema12, ema26, cdc_zone, atr14}]}` | 400, 404, 422 |
| `GET /lists` | — | `{items:[{list_code, name, asset_class, status, reason, current_as_of, member_count, last_attempt_at}]}` | — |
| `GET /lists/{list_code}` | `as_of` (optional) | `{list_code, as_of, members:[{instrument_id, display_symbol, name, rank}]}` | `404 not_found` |
| `GET /watchlist` | — | `{items:[{instrument_id, position, added_at}], max_items: 50}`, lazily seeded | — |
| `POST /watchlist/items` | `{instrument_id}` + CSRF | `201 {instrument_id, position, added_at}` | 400, `404 unknown_instrument`, `409 already_on_watchlist`, `422 instrument_inactive`, `422 watchlist_full` |
| `DELETE /watchlist/items/{id}` | CSRF | `204`; positions are compacted | `404 not_found` |
| `PUT /watchlist` | `{instrument_ids:[…]}` + CSRF: a subset of the current items in the new order | `200`, same body as `GET` | `400 invalid_request` (`details.reason` `duplicate` or `not_on_watchlist`) |
| `GET /market-watch` | — | `{generated_at, items:[Row]}` ordered by position | — |

**Request rules.**
- Query strings are strict: an unknown, repeated or unparseable parameter is a 400.
- Ids are URL-encoded by clients (`%40` for `@`). An encoded `/` is a 404.
- Checks run in the order query (400), then instrument (404), then timeframe (422). A timeframe a route never serves (`5m`, or `1m` on indicators) is a 400.
- A NaN or infinite stored indicator is `null` and logs the warn event `indicator_value_not_finite`.

**Watchlist.**
- The first `GET /watchlist`, `GET /market-watch` or mutation creates the watchlist with the default eight, once even under concurrent first access (`TestWatchlist_ConcurrentFirstAccess_SeedsOnce`). Emptying it never re-seeds it.
- Every committed change, the seeding included, publishes `md:subscriptions` once, best effort. A failure, or Redis being down, logs the warn event `md_subscriptions_publish_failed` and never rolls the change back.
- Watchlist edits write no audit event.

**Market watch row.** `{instrument_id, display_symbol, name, asset_class, venue_label, quote_ccy, tick_size, last, change_24h, strip, current_zone, status, signals}`.
- **`last`.** `px:last` wins when its `ts` is after the latest stored bar's end; otherwise the stored close is used. `ts` is never after `generated_at` (ORCH-30).
- **`change_24h`.** `{reference_price, reference_ts, abs, pct}`, with `pct` to 4 decimals. The reference is the last `candles` close at or before 24 h ago, or the previous EOD session for a `1d` base.
- **`strip`.** `{timeframe: "1h"|"1d", cells:[{ts, zone|null}] (≤ 48, oldest first), complete}`, and `current_zone` equals the last cell's zone.
- **`status`.** `{mode, stale, session, next_open_at, delay_minutes}`, passed through from `px:last`. Without `px:last` it is `stale: true`, `session: "unknown"` (ORCH-10), with mode `synthetic`, `eod` or `live` derived from the instrument.
- **`signals`.** Always `null`.

### New error codes (in `AllCodes()` and the service README)

| Code | Status | When |
|---|---|---|
| `unknown_instrument` | 404 | A path id that is malformed or not in `instruments`. On `POST /watchlist/items`, a well-formed unknown id. |
| `timeframe_unavailable` | 422 | A timeframe finer than the instrument's base (`1m`/`15m`/`1h` on a `1d` base) |
| `already_on_watchlist` | 409 | Adding an instrument that is already on the list |
| `watchlist_full` | 422 | Adding a 51st instrument |
| `instrument_inactive` | 422 | Adding an instrument whose `active` is false |
| `origin_rejected` | 403 | A `/ws` upgrade whose `Origin` is missing, repeated, `null` or not the app origin |
| `realtime_unavailable` | 503 | A `/ws` upgrade while Redis pub/sub is not answering, `REDIS_URL` is empty, or the service is shutting down |
| `too_many_connections` | 429 | A `/ws` upgrade when the user already holds 5 connections (per process) |

### WebSocket `GET /ws`

**Pre-upgrade checks, in order** (plain HTTP answers with the envelope; pinned by `TestRouter_WS_CheckOrder`):
1. ready (`503 not_ready`);
2. exact `Origin` (`403 origin_rejected`);
3. session (`401 unauthenticated`);
4. `admin` (`403 forbidden`);
5. no forced change pending (`403 password_change_required`);
6. Redis (`503 realtime_unavailable`);
7. fewer than 5 connections (`429 too_many_connections`).

Then comes the service's own handshake check. A non-upgrade `GET /ws` gets `400 invalid_request` with `details.reason` `upgrade_required`. There is no CSRF header on an upgrade: the exact Origin check plus the `SameSite=Lax` cookie is the cross-site defence.

**Client to server.**
- `{"op":"subscribe"|"unsubscribe","instruments":[…]}`.
- Text JSON only, at most 4 KiB, 10 per second, 100 ids per message and 100 subscriptions per connection.

**Server to client.**
- `subscribed`, with `rejected[].code` one of `invalid_instrument_id`, `unknown_instrument` or `subscription_limit`.
- One `snapshot` per accepted id that has a valid `px:last`.
- `unsubscribed` (R3).
- `tick`, `bar`, `zone` and `status`, forwarded byte for byte.
- `error` with code `bad_message`, `rate_limited` or `message_too_large`.

**Lifecycle and close codes.**
- The server pings every 30 s and drops a socket after 60 s without a pong (recorded as 1006).
- Every 60 s, one batched session re-check runs. It never touches the session, so an open socket alone does not extend the idle timeout.
  - 4401: the session ended (sign-out, sign-out everywhere, the CLI reset).
  - 4403: a forced change is pending, or the role is no longer `admin`.
- 1008: the third protocol error within 60 s.
- 1009: a message over 64 KiB (R8).
- 1011: a server failure, such as two failed re-checks in a row.
- 1013: more than 256 messages queued.
- 1001: shutdown.

**Fan-out.** One Redis pub/sub connection per instance holds `px:<id>` for every id with at least one subscriber, reference-counted. While Redis is down, sockets stay open and silent, and the subscriber reconnects with a backoff from 100 ms to 5 s. Messages published during an outage are not replayed. The per-user cap and the fan-out are per process (SV15).

### Redis contract (§6.3; DB 0 is ephemeral and never backed up)

| Key or channel | Written by | Payload |
|---|---|---|
| `px:last:<instrument_id>` (string, TTL 7 days) | bot (status publisher only) | `{"v":1,"price","ts","mode","stale","session","next_open_at","next_close_at","updated_at"}` |
| `px:<instrument_id>` (pub/sub) | bot | `tick` (at most 4 per second), `bar` (closed 1m bars only, after the upsert commits), `zone` (after a strip-timeframe indicator row persists; `ema12` and `ema26` are decimal strings), `status` (on change) |
| `md:subscriptions` (pub/sub) | service | `{"v":1,"type":"watchlist_changed"}` |

Consumers ignore unknown types and fields, and a breaking change bumps `v`. The service never writes `px:*`, and the bot reads no `md:*` channel except `md:subscriptions`. There is no HTTP between the bot and the service.

### Bot HTTP endpoints (`0.0.0.0:9091` inside the container, never published)

- `GET /health`: always `200 {"status":"ok"}`.
- `GET /ready`: checks the database (`SELECT 1`) and Redis (`PING`), 2 s each, single-flight and cached for 1 s. It answers `200 {"status":"ready"}` or `503 {"status":"not_ready","failing":[…]}`. It does not check the schema version.
- `GET /metrics`: the Prometheus text of the 13 series.
- Any other method gets 405; any other path gets 404.

## Components

### tidewatch-bot (Node 24, pnpm 11.5.2, Nx 23.2.1, TypeScript ~6.0.3, Vitest 4; base `fe17845`)

**`packages/indicators`** (`type:shared`, zero runtime dependencies, no I/O).
- EMA(n) is SMA-seeded and `null` before n closes. ATR14 uses Wilder's method with an SMA seed.
- The CDC zone is computed from the close, EMA12 and EMA26: `buy`, `pre_buy_2`, `pre_buy_1`, `sell`, `pre_sell_2`, `pre_sell_1`, or `null` on ties and warm-up.
- A full-series function and an incremental `step(state, bar)` give identical results.
- Fixtures:
  - `fixtures/cdc-reference-1h.csv` holds 500 BTCTHB 1h bars captured once from Binance TH public REST.
  - `fixtures/cdc_reference.py` is the independent oracle.
  - `fixtures/README.md` records the capture. Its licence statement is open (OI-1).

**`packages/market-data`** (`type:shared`).
- **Collectors:**
  - **`binance-th`.** The bare-endpoint stream with `<symbol>@kline_1m`. A closed kline is upserted, and every kline publishes a tick. REST klines page in 1,000-minute windows. A weight limiter allows 4,800 per 60 s and adopts `x-mbx-used-weight-1m`. It honours 429 `Retry-After`, and a 418 stops REST and logs `collector_banned`. It reconnects after 3 min of silence or at 23 h. The realtime set holds at most 20 instruments.
  - **`alpaca`.** The IEX stream (`bars`, `updatedBars`, at most 30 symbols). SIP `1Min` REST for backfill, 5-minute reconciliation and 1-minute delayed polling, always with `end ≤ now − 15 min`. `1Day` SIP bars go to `candles_eod` on Tue–Sat 05:30–08:00 Bangkok. One sliding window of 180 requests per 60 s covers every caller.
  - **`oanda`.** The pricing stream at the mid, at most 4 per second. M1 candles every minute. A startup instrument check, and the `USDTTHB` proxy when `USD_THB` is missing. Disabled on the owner's setup (FU-4).
  - **`yahoo`.** SET end-of-day at 18:00 Mon–Fri with retries to 20:00, then 07:30 Tue–Sat. A 400-day first load. One request per second.
  - **`set-check`.** It compares the Yahoo close with the SET site's `historical-trading` and writes `eod_close_checks`. It never changes `candles_eod`.
  - **`gta`.** It polls every 2 minutes, 08:30–18:00. The Gold 96.5 premium check runs at 17:45.
  - **`synthetic`.** `GO@tfex` and `GOLD9999USD@mts` copy the XAU/USD bar inside their own sessions. `GOLD965THB@mts` = `xau.{o,h,l,c} × usd_thb.c × 0.965 × 15.244 / 31.1035 + premium_applied(day)`.
- **Jobs:**
  - **Indicators.** One row per closed 15m, 1h or 1d bucket within 60 s. Rows are recomputed forward after corrections. `zone` is published only for strip-timeframe rows inside the 3-day correction window.
  - **Weekly lists.** Sunday 03:00 Bangkok, or `run list-refresh`. Snapshots are validated (`count_out_of_bounds`, `source_too_old`, `churn_too_high`, `fetch_failed`, `parse_failed`), and list status is tracked (`ok`, `stale` with `consecutive_failures` or `missed_rebalance`, `never_fetched`). A US ticker grammar (`core/tickers.ts`, security F1) stops a list from creating `*.BK@webull` ids or re-homing an instrument.
- **Runtime pieces:**
  - **Subscription manager.** It recomputes within about 1 s of `md:subscriptions` and every 60 s. An instrument entering a set is backfilled before it goes live. Alpaca names evicted from the live set move to delayed polling.
  - **Status publisher.** It is the only writer of `px:last` and `status`, with a pass every 250 ms. Staleness rules live in `status/staleness.ts`. A disabled collector makes its instruments stale while open. The overnight session is always stale while open.
  - **Bar sink.** Persist, then publish. Aggregate refreshes are deferred, flushed once per backfill run in calls of at most 7 days, clamped to the retention horizon, and carried on failure. The aggregate maintenance retries every 5 minutes and runs a daily catch-up.
  - **Transport.** `transport/http.ts` is the only `fetch` and `transport/ws.ts` the only WebSocket. Redirects are followed by hand: at most 3, `https` and same-origin only, and none for credentialed sources. One User-Agent table governs every request.

**`packages/shared`.**
- `loadConfig` now requires `REDIS_URL`. The pairs `ALPACA_KEY_ID`/`ALPACA_SECRET_KEY` and `OANDA_DEMO_TOKEN`/`OANDA_DEMO_ACCOUNT_ID` are both-or-neither: half a pair exits 1 naming the missing member.
- New optional variables: `GOLD965_PREMIUM_SEED_THB`, `TIDEWATCH_HTTP_CONTACT`, `MARKET_DATA_COLLECTORS` (default: all nine) and `METRICS_PORT` (default 9091).
- The redaction list gains `key`, `apca-api-key-id` and `apca-api-secret-key`. Configured key values of 8 or more characters are masked in every string.

**`packages/worker`** (`type:app`).
- **`serve`** is the default `CMD`. It takes `runner:serve` first; only the holder starts runners, the status layer and the aggregate maintenance. A second serve stays in full standby.
- **`run <job> [--list <code>]`** runs one of `list-refresh`, `indicators`, `yahoo-eod`, `alpaca-daily` or `gold-premium-check`. Exit codes are 0, 1 (a failure or a lock held elsewhere) and 2 (usage).
- **Shutdown.** On SIGTERM the shutdown is ordered, with a 10 s guard that logs `shutdown_timeout` and exits 1.
- **Image.** The same `Dockerfile` CMD, `node packages/worker/dist/main.js`, running as non-root `node` (UID 1000). It has no `EXPOSE` or `HEALTHCHECK`; compose owns the healthcheck.

### tidewatch-service (Go 1.26; base `f04ae0a`)

- **New packages.**
  - `internal/market`: a pure leaf with ids, timeframes, zones, the venue label, the default eight, exact decimals and the `px:*` v1 shapes.
  - `internal/services/{market,watchlist,realtime}`.
  - `internal/handlers/{instruments,lists,watchlist,marketwatch,realtime,query}.go`.
  - `internal/httpx/wsconn`: handshake check and `Peer`.
  - `internal/httpx/middleware/{nostore,upgradeorigin}.go`.
  - `internal/repository/postgres/{instrument,list,candle,indicator,watchlist,marketwatch}.go`. Every call runs under a query timeout.
  - `internal/repository/redis/{lastprice,notify}.go`.
  - `internal/platform/redis`: the go-redis client, a zerolog adapter, and the one subscriber, which owns `redis_up`.
  - `internal/redistest`: an integration-only loopback Redis with a cuttable `Proxy`.
- **The realtime hub** (`internal/services/realtime`) is transport-free. `internal/handlers/realtime.go` is the only place that knows both gin and coder/websocket.
- **Redis is optional and never a readiness input.** An empty `REDIS_URL` gives a nil client: REST works, `/ws` answers 503 and `redis_up` stays 0. The client uses a 1 s dial timeout, a pool of 4 for `MGET` and `PUBLISH`, and one pub/sub connection.
- **Gate coverage.** `TestRouter_ForcedChangeGatesNewRoutes` counts 19 gated routes: 16 production routes and 3 test-only probes. The forced-change allowlist still has its four slice-0 entries.
- **Metrics.**
  - New series on the internal 9090 listener: `redis_up`, `ws_connections`, `ws_subscriptions`, `ws_messages_sent_total{type}` and `ws_closed_total{code}`. They have closed label sets, with no instrument or user label.
  - New log events: `ws_connected`, `ws_closed`, `ws_panic`, `md_subscriptions_publish_failed` and `indicator_value_not_finite`.

### tidewatch-web (Angular 22.1, Tailwind v4, `@angular/aria`; base `4f8c4a2`)

**Route tree.** The Overview child of `workspace.routes.ts` now loads `feat-overview/Overview` instead of `ScreenPlaceholder`. The other five screens keep their empty states.

```
''  Shell
└── ''  Overview (feat-overview/overview.ts): page header + MarketWatch section
        MarketWatch (provides the MarketWatchService store)
        ├── MarketWatchTable (table.tide, six columns, legend)
        ├── AddInstrumentDialog (app-dialog + aria combobox/listbox + app-toast)
        └── EditListDialog (app-dialog + signal form over the ordered draft)
```

**Market watch card** (PRD §7.2).
- **Header.** `h2` "Market watch" with a count. Filter tabs *All assets · Stocks · Crypto · Gold* (`aria-pressed`; `fx` rows appear only under All). *Add instrument* and *Edit list* buttons (`plus` and `edit` icons). A polite *Reconnecting live prices…* caption.
- **Table.** `table.tide` with a visually hidden caption and `min-width: 650px` in a scroll region. Columns:
  - Instrument: a neutral 29 px tile with a glyph (₿, Ξ, Au, G or the first letter), then `name · venue_label · status tag`;
  - Last price, with decimals from `tick_size`;
  - 24h change: `--up`/`--down`, U+2212 for minus, `--text-2` for 0.0 % and "—";
  - Market tide · 48h;
  - Current zone;
  - Signals: "—".
- **Rows.** 61 px tall and not clickable.
- **Status tags.** Neutral `.tag` for *Live*, *Delayed 15 min*, *EOD*, *Synthetic*, *Closed · opens EEE HH:mm* (Bangkok) and *Stale*. Stale outranks the others (`util/status-tag.ts`).
- **States:**
  - "Loading market watch…" (no spinner);
  - "Market watch couldn't load." plus *Try again*, hue-less;
  - empty: "Your market watch is empty. Add an instrument to follow its price and tide." plus a primary *Add instrument*;
  - filter-empty: "No instruments in this view.";
  - a row with no price yet shows "—" and the History loading strip.

**Shared components and styles.**
- `TideStrip` (`shared/ui-tide-strip`). An inline SVG with `viewBox 0 0 1000 18` and one `rect` per cell filled with `var(--z-*)`; a `null` cell gets a `--line-2` stroke. It has `role="img"` and an accessible name built by `strip-label.ts`. Cells are right-aligned when there are fewer than 48.
- `ZoneLabel` + `ZONES` (`shared/ui-zone-label`). `zone.css` alone maps a zone to its token.
- `Dialog` (`shared/ui-dialog`, `app-dialog`). A native `<dialog>` opened with `showModal()`.
  - The backdrop is the new `--backdrop` token: dark `rgba(4,10,19,.68)`, light `rgba(31,48,73,.14)`.
  - Escape closes it through a capture-phase listener (MW-16), because the aria combobox cancels the key first.
  - Focus returns to the trigger on close, and the body renders only while open.
  - A toast slot sits outside the glass panel (MW-3).
- `Toast` (`shared/ui-toast`). A polite live region that clears after 4 s.
- Icons `plus`, `edit` and `arrow` were added to `ICONS`.
- Styles: `tag.css`, `zone.css`, `dialog.css`, `toast.css`, `table.css` and `market-watch.css` are new; `button.css`, `tokens.css` and `styles.css` changed.

**Dialogs.**
- **Add instrument.**
  - Search is debounced 250 ms (`GET /instruments?q=&limit=`). The active option is the first unlisted one.
  - Enter or a click adds the instrument and shows a toast such as "Added NVDA to Market watch."; the option becomes *On your list*.
  - "No instrument matches "xyz"." and the all-listed line (OC-1).
  - On `watchlist_full`: "Market watch holds up to 50 instruments. Remove one first.". Any other failure: "Couldn't add that instrument. Try again.".
- **Edit list** ("Your market watch").
  - Keep checkboxes, plus *Move up* and *Move down* buttons whose names include the symbol.
  - *Save list* sends `PUT /watchlist` and shows the toast "Market watch saved.". *Cancel* discards.

**Data layer** (`pages/workspace/data/`; `HttpClient` only lives here).
- **Models.** `market-data.model.ts` and `market-stream.model.ts` define the §6 types with runtime shape checks. Decimal strings are capped at 40 characters and formatted digit by digit.
- **`MarketWatchApi`** (`market-watch-api.service.ts`). REST calls, with a strict `HttpParameterCodec`.
- **`MarketStream`** (`market-stream.service.ts`). One root WebSocket with reference-counted interest.
  - The URL comes from `apiBaseUrl` (`http`→`ws`, `https`→`wss`, a relative base after `location.origin`) plus `/ws`. The socket has no token, query or custom header.
  - Transient closes back off 1, 2, 5, 10 and then 30 s. 4401 and 4403 are terminal: they reload once, so the interceptor can redirect (MW-2, MW-26).
- **Store.** `MarketWatchService` (`feat-overview/data/`) is component-provided (MW-13). It uses `httpResource()` and a single `reload()` (MW-12): every 5 minutes, after a reconnect, after a `zone` message for a visible row, and after an add or save. Live 24h change is recomputed by `util/apply-stream-message.ts`.
- **Quiet table.** The table is not a live region, and prices change in place with no highlight (MW-23).

**E2E** (all in the existing `authed` Playwright project, MW-18):
- `market-watch.spec.ts` and `market-watch-dialogs.spec.ts` are fail-closed mocked specs: REST through `page.route`, and the socket through `page.routeWebSocket`.
- `market-watch-live.spec.ts` is skipped unless `E2E_LIVE_MARKET_DATA=1`.
- `watchlist.spec.ts` is the FR-MD-E2E-004 journey. It restores the eight seeded rows at the end.

`DESIGN.md` was not changed in this PR; that is FR-MD-WEB-011.

### Workspace root (not a git repo; edited in place) and the Forge preview

- **`docker-compose.yaml`** (SHA-256 `afe5da80…` → `c967a35e…`).
  - `tidewatch-bot` is now long-running:
    - `restart: unless-stopped` and `stop_grace_period: 15s`;
    - `depends_on`: `migrate` (`service_completed_successfully`) and `redis` (`service_healthy`);
    - healthcheck `wget -qO- http://127.0.0.1:9091/ready` (interval 10 s, timeout 5 s, 12 retries, start 30 s);
    - `METRICS_PORT: "9091"` and the optional keys as `${VAR:-}`;
    - no `ports`.
  - `db` gained `command: ["postgres", "-c", "timescaledb.telemetry_level=off"]` (OWNER-3).
  - The header now expects the bot to be "healthy" (only `migrate` exits 0). It also documents `run list-refresh`, the in-container metrics read, and that 9090 and 9091 are never published.
  - It claims `up -d --build --wait` is expected to work. That is unconfirmed until a real start.
- **`.env.example`** (`be2c84a1…` → `e0dbe7d6…`) gained these keys, all empty, with comments: `ALPACA_KEY_ID`, `ALPACA_SECRET_KEY`, `OANDA_DEMO_TOKEN`, `OANDA_DEMO_ACCOUNT_ID`, `GOLD965_PREMIUM_SEED_THB`, `TIDEWATCH_HTTP_CONTACT` and `MARKET_DATA_COLLECTORS`.
- **`.forge/docker-compose.json`** was synced through `forge-setup-docker-compose` (discover → candidate → sync → status `current`; setup SHA-256 `8d5d59c8…`).
  - `tidewatch-bot` is a preview service: built from `{{project:tidewatch-bot}}`, with `ENVIRONMENT=local`, `REDIS_URL`, `METRICS_PORT 9091`, the `/ready` healthcheck, `restart: unless-stopped` and `stop_grace_period 15s`.
  - The isolated overlay adds the secrets `env_file` and `depends_on` migrate completed.
  - The isolated `db` also runs with telemetry off.
- The preview secrets file `.forge/docker/secrets/tidewatch.env` is owner-filled and never printed. It now holds the Alpaca keys; the OANDA lines are empty.

### Rollout, operations and recovery

**Migration order.**
1. `tidewatch-migrations` (PR #2) merges before or with the service and bot PRs. That order was followed on 2026-10-07.
2. Compose applies A, B and C through the one-shot `migrate` container. The service and the bot both wait for `migrate` to complete. The bot also waits for Redis to be healthy.
3. Until C is applied, the service answers `503 not_ready` on `/ready`, `/auth/*`, every market route and `GET /ws`.
4. The web has no schema dependency of its own; it needs the service's REST and `/ws`.
5. Downs are not a recovery path (see Database). Ask before `down -v` on any stack that holds the owner's data.
6. `timescale/timescaledb-ha:pg18` is a floating tag; an image bump may need the migrations harness updated.

**Environment changes.**
- New bot variables are listed under Components. `REDIS_URL` is now required by the bot and stays optional for the service.
- Bring-up on the owner compose (FR-MD-INFRA-001, not yet done):
  1. Create `.env` from `.env.example`. The root `.env` does not exist yet.
  2. Set `POSTGRES_PASSWORD`, and `TIDEWATCH_ADMIN_PASSWORD` for the first start.
  3. Optionally set the Alpaca pair. Leave the OANDA pair empty (FU-4).
  4. Run `docker compose up -d --build`, then `docker compose ps -a`. Expect `tidewatch-bot` healthy and `migrate` `Exited (0)`.
- The `db` command change recreates the container on the next `up` while keeping the volume. That is standard Compose behaviour and was not tested here.

**Observability.**
- **Bot.**
  - `/health`, `/ready` and `/metrics` listen on 9091 inside the container and are never published. Read them with `docker compose exec tidewatch-bot wget -qO- http://127.0.0.1:9091/metrics`.
  - 13 series:
    - `market_data_stale{instrument_id}` and `market_data_last_update_age_seconds{instrument_id}`;
    - `collector_enabled`, `collector_connected`, `collector_reconnects_total` and `backfill_bars_total` (by collector);
    - `alpaca_requests_total{endpoint}`, `alpaca_rate_limited_total` and `binance_th_weight_used`;
    - `indicator_job_lag_seconds{timeframe}`;
    - `instrument_list_age_days{list_code}` and `instrument_list_status{list_code,status}`;
    - `gold_premium_deviation_pct`.
  - Logs are structured snake_case events, 169 of them, which equal the README rows.
- **Service.** The realtime series above, on 9090 (never published).
- **Preview-only excerpts.** `evidence/root/preview/07-bot-metrics.txt` and `10-bot-log-06a9ab8.jsonl`.

**Recovery notes (from the READMEs).**
- **Redis outage.** REST keeps working, and rows read `stale` with session `unknown`. `/ws` answers `503 realtime_unavailable` and `redis_up` is 0. Open sockets stay open and resume once the subscriber reconnects. Redis holds nothing the service owns.
- **Missing keys.** The affected collector is disabled (`collector_disabled`), and its instruments show `stale` while their session is open. Nothing crashes. Half a pair is a configuration error, and the bot exits 1.
- **Restart gaps.** The bot backfills from `collector_cursors` on start and on reconnect. On the preview, a 10 min 30 s kill left 0 missing minutes in the last hour for BTCTHB and ETHTHB.
- **First start.** Each Binance TH pair takes 260 windows. Instruments are backfilled one after another, and each waits for its aggregate flush before subscribing, so prices take minutes to go live. Alpaca `1Day` and the lists do not run at start: use `run alpaca-daily` (only while `serve` does not hold `runner:alpaca`) or `run list-refresh`.
- **Concurrent aggregate refresh.** `aggregates_refresh_failed` with a carried range is retried every 5 minutes. No action is needed (FU-5).
- **Interrupted deep backfill (GAP-BOT-CATCHUP-IND, FU-3).** Delete the affected instrument's `indicators` rows from the start of the gap, for each affected timeframe. The next pass recomputes from there. `run indicators` alone does not repair it.
- **Aggregate refresh.** Never refresh a continuous aggregate older than the 180-day retention, or with a NULL start.
- **Shutdown.** The worker's guard is 10 s, so compose uses `stop_grace_period: 15s`. A catch-up slice still running at SIGTERM can make the exit code 1 with nothing lost.
- **Two serves.** The second stands by under `runner:serve`. Up to about 25 s of overlap is possible if a lock loss goes undetected (security r3 I-2, accepted).
- **Calendars.** Exceptions run to 2027-12-31. The bot logs `calendar_exceptions_expiring` from 2027-11-02; ship the next list as a new migration before then.
- **Web sockets.** 4401 and 4403 are terminal and recover only after a successful REST reload (MW-26).
- **Lost admin password.** Use the service CLI reset (`admin set-password`), never a down migration.

## Files touched

Merged revisions:

| Repo | PR | Reviewed head | Merge commit |
|---|---|---|---|
| tidewatch-migrations | tidewatch-labs/tidewatch-migrations#2 | `d77efa8` | `cb93cd5` |
| tidewatch-service | tidewatch-labs/tidewatch-service#3 | `04dec78` | `734ce35` |
| tidewatch-bot | tidewatch-labs/tidewatch-bot#2 | `06a9ab8` | `5a60477` |
| tidewatch-web | tidewatch-labs/tidewatch-web#3 | `a7cb23a` | `5611d79` |

All four merged at 2026-10-07T13:00:54+07:00. The lists below come from the plans' step file lists, cross-checked against the run worktrees (which equal the reviewed heads) and the review-fix status logs.

**tidewatch-migrations** (worktree `b7ddc75378`; commits `8a158f1` MIG1–MIG4, `d77efa8` review fix)
- `migrations/20261006100927_market_reference.sql`, `migrations/20261006113158_market_timeseries.sql`, `migrations/20261006131346_market_calendar_exceptions.sql` (created)
- `scripts/check-disposable-db.sh` (modified: harness generalised, A/B/C assertions, aggregate equality, fork-and-kill `bounded`, telemetry off)
- `README.md`, `CLAUDE.md`, `.dockerignore` (modified)

**tidewatch-service** (worktree `329891b601`; plan `.plans/market-data.md`; commits `842f944` S1–S9, `426fa79` review-fix r1, `04dec78` review-fix r2)
- `internal/platform/postgres/schema.go`, `internal/pgtest/migrate.go`, `scripts/integration-test.sh`, `pkg/apperror/{codes,apperror}.go` + `apperror_test.go`, `internal/httpx/response/response.go` + test (modified)
- `internal/market/{feed,id,timeframe,zone,venue,defaults,decimal}.go` + `{feed,id,timeframe,venue,decimal}_test.go` (created)
- `internal/platform/redis/{redis,logger,subscriber}.go` + tests; `internal/repository/redis/{lastprice,notify}.go` + tests; `internal/redistest/{redistest,proxy}.go` (created)
- `internal/repository/postgres/{instrument,list,candle,indicator,watchlist,marketwatch}.go` + tests (created; `instrument.go` includes `Existing`, ORCH-27); `internal/repository/postgres/session.go` + test (modified)
- `internal/services/market/{service,instruments,cursor,candles,indicators,lists,errors,marketwatch}.go` + tests; `internal/services/watchlist/{service,store}.go` + test; `internal/services/realtime/{hub,conn,protocol,config,ports}.go` + tests (created)
- `internal/services/auth/{session,service}.go`, `{fakes,session}_test.go` (modified, for the batched session check)
- `internal/handlers/{instruments,lists,query,watchlist,marketwatch,realtime}.go` + tests (created)
- `internal/httpx/middleware/{nostore,upgradeorigin}.go` + tests; `internal/httpx/wsconn/{handshake,peer}.go` + tests (created); `internal/httpx/middleware/bodylimit.go` (modified)
- `internal/observability/metrics/realtime.go` (created); `metrics.go`, `metrics_test.go`, `internal/observability/logging/redact_test.go` (modified)
- `internal/config/validate.go`, `config_test.go` (modified)
- `internal/app/{app,router}.go`, `{router,observability,lifecycle,servers}_test.go` (modified); `internal/app/redis_test.go` (created)
- `test/integration/{redis,market,fixtures,watchlist,marketwatch,realtime,realtime_slo}_test.go` (created); `test/integration/{main,ready,harness,session}_test.go` (modified)
- `.env.example`, `go.mod`, `go.sum`, `README.md`, `CLAUDE.md` (modified)

**tidewatch-bot** (worktree `6945fd5d6c`; commits `ec1e19f` S1–S14, `5febc81` review-fix r1, `577a719` S15, `c1570d3` S16, `a289b26` review-fix r2, `9bf762d` docs polish, `99c8511` fix r3, `06a9ab8` fix r4)
- `packages/indicators/` (created): `package.json`, `tsconfig{,.lib,.spec}.json`, `vitest.config.mts`, `src/{index,indicators,zone}.ts`, `src/{fixture,edge-cases,step,no-network-guard}.spec.ts`, `fixtures/{cdc-reference-1h.csv,cdc_reference.py,README.md}`
- `packages/market-data/` (created):
  - `package.json`, `tsconfig{,.lib,.spec}.json`, `vitest.config.mts`, `vitest.int.config.mts`
  - `src/{index,metrics,sink}.ts` + specs; `src/sink.int.spec.ts`; `src/{no-network-guard,no-direct-network,fixtures-format}.spec.ts`
  - `src/core/{clock,decimal,zoned-time,usd-thb-source,tickers}.ts`; `src/calendar/calendar.ts`; `src/limits/{sliding-window-limiter,weight-limiter}.ts`
  - `src/transport/{http,ws,user-agents}.ts`; `src/redis/{client,contract,publisher,subscriptions-listener}.ts`
  - `src/db/{types,repositories,pg-repositories,reference-cache,locks}.ts` + `pg-repositories.int.spec.ts`, `locks.int.spec.ts`
  - `src/runtime/types.ts`
  - `src/collectors/binance-th/{collector,rest,stream,parse}.ts`; `src/collectors/alpaca/{collector,rest-client,stream,reconcile,daily}.ts` + `limiter-coverage.spec.ts`; `src/collectors/oanda/{collector,rest,stream}.ts`; `src/collectors/yahoo/{collector,parse}.ts`; `src/collectors/set-site/session.ts`; `src/collectors/set-check/collector.ts`; `src/collectors/gta/{collector,parse,premium}.ts`
  - `src/synthetic/{formulas,engine}.ts`
  - `src/jobs/indicators/job.ts` (+ `job.int.spec.ts`); `src/jobs/lists/{job,validate,rebalance,instruments}.ts` (+ `job.int.spec.ts`, `sources.spec.ts`); `src/jobs/lists/sources/{wikipedia-sp500,ssga-spy,nasdaq100,wikipedia-nasdaq100,set-composition,binance-th-top20}.ts`
  - `src/subscriptions/manager.ts`; `src/status/{freshness,staleness,status-publisher}.ts`
  - `src/testing/{index,fake-clock,fake-http,fake-ws,fake-redis,memory-repositories}.ts`
  - Unit specs beside each module.
  - `fixtures/README.md` and `fixtures/{binance-th,alpaca,oanda,yahoo,set,gta,lists}/…`, including `fixtures/binance-th/klines-error-4088.json` (added in `99c8511`)
- `packages/shared/src/{config,logger,index}.ts` + `{config,logger}.spec.ts` (modified)
- `packages/worker/` (modified: `package.json`, `tsconfig.lib.json`, `tsconfig.spec.json`, `vitest.config.mts`, `src/{main,run}.ts`, `src/run.spec.ts`; created: `vitest.int.config.mts`, `src/{cli,serve,http-server,jobs}.ts` + specs, `src/serve.int.spec.ts`)
- `scripts/sql-integration.sh` (created)
- `Dockerfile`, `.dockerignore`, `.env.example`, `tsconfig.json`, `pnpm-lock.yaml`, `README.md`, `CLAUDE.md` (modified)

**tidewatch-web** (worktree `5eb4e5c7ea`; plan steps M1 (S1+S2) and S3–S7; commits `d015ab2`, `a0ac23a` (approved in round 2), `a7cb23a` (docs and spec polish))
- `src/styles/base/tokens.css` (`--backdrop`), `src/styles.css`, `src/styles/components/button.css`, `src/app/shared/ui-icon/{icons.ts,icon.spec.ts}` (modified)
- `src/styles/components/{tag,zone,dialog,toast,table,market-watch}.css` (created)
- `src/app/shared/ui-tide-strip/{tide-strip,strip-label}.ts` + specs; `src/app/shared/ui-zone-label/{zones,zone-label}.ts` + spec; `src/app/shared/ui-dialog/dialog.ts` + spec; `src/app/shared/ui-toast/toast.ts` + spec (created)
- `src/app/pages/workspace/data/{market-data.model,market-stream.model,market-watch-api.service,market-stream.service}.ts` + specs (created)
- `src/app/pages/workspace/feat-overview/{overview,market-watch,market-watch-table,add-instrument-dialog,edit-list-dialog}.ts` + specs; `feat-overview/data/market-watch.service.ts` + spec; `feat-overview/util/{apply-stream-message,row-view,number-format,status-tag,asset-glyph,watchlist-error-message}.ts` + specs (created)
- `src/app/pages/workspace/workspace.routes.ts`, `feat-screen-placeholder/screen-placeholder.spec.ts`, `src/app/app.routes.spec.ts` (modified)
- `e2e/src/{market-watch,market-watch-dialogs,market-watch-live,watchlist}.spec.ts`, `e2e/src/support/market-watch.ts` (created); `e2e/playwright.config.mts`, `e2e/src/support/{fixtures,screens}.ts`, `e2e/src/{shell,journey,a11y,viewport}.spec.ts` (modified)
- `README.md`, `CLAUDE.md` (modified). `DESIGN.md` was not changed.

**Workspace root** (`/Users/maichinu/tidewatch`, not git)
- `docker-compose.yaml`, `.env.example`, `.forge/docker-compose.json` (modified in place)
- `.forge/docker/secrets/tidewatch.env`: owner-edited (Alpaca keys added, OANDA lines cleared). Not a deliverable; values never printed.

## Test plan

### Commands (each from its project root)

| Project | Command | Result |
|---|---|---|
| migrations | `make migrate-validate`; `make check-disposable-db` | Passed at `d77efa8`: 43/43 commands exit 0, 641 PASS lines and 0 FAIL, seven passes. The harness covers up, `down-to 20261004153023`, up, `down-to 0` and up, the catalog, aggregate equality across a refresh boundary, and the A1/A2/A11 probes. Ran on PostgreSQL 18.6 and TimescaleDB 2.30.2. |
| service | `make ci` | Passed at `04dec78`: vet including `-tags integration`, `-race` unit tests and build. |
| service | `make test-integration TIDEWATCH_MIGRATIONS_DIR=<checkout>` | Passed: `ok test/integration 169.822s`, 2,091 PASS lines, 0 SKIP, 0 FAIL, 0 DATA RACE. It runs against throwaway TimescaleDB and loopback Redis. |
| service | `make check-image` | Passed at S7, after an infrastructure retry (ORCH-28). |
| bot | `pnpm nx run-many -t lint test typecheck build` | Passed at `06a9ab8` with `--skip-nx-cache`: market-data 354, worker 39, shared 56, indicators 22. |
| bot | `TIDEWATCH_MIGRATIONS_DIR=<checkout> bash scripts/sql-integration.sh` | `sql-integration: PASS` at `a289b26` (market-data int 16/16, worker int 2/2). Not re-run for `99c8511` or `06a9ab8`. |
| web | `pnpm nx run-many -t lint test build` | Passed at `a0ac23a`: 948 unit tests, also under `TZ=America/New_York`. After `a7cb23a`, lint and 949 tests passed; `build` was not re-run (spec and docs changes only). |
| web E2E | Playwright against the preview's fresh isolated database | Full suite: 273 passed, 2 skipped (the gated live specs), 0 failed. Live specs with `E2E_LIVE_MARKET_DATA=1` on the final preview: 3 passed. |

**Key tests.**
- **Service:** `TestContract_RequiredSchemaVersion`, `TestReady_SchemaWait`, `TestMarket_RoutesGated`, `TestInstruments_Search_ThaiAliasFiltersPaging`, `TestCandles_SourcesLimitsPartial`, `TestWatchlist_ConcurrentFirstAccess_SeedsOnce`, `TestMarketWatch_Rows_FromFixtures`, `TestRealtime_Upgrade_Refusals`, `TestRealtime_Protocol_Limits`, `TestRealtime_PublishToClient_P99Under2s`, `TestRealtime_SessionRecheck_Closes4401And4403`, `TestRealtime_RedisOutage_RESTWorksAndResumes`, `TestRealtime_CurlTranscripts` and `TestServe_SIGTERM_ClosesSockets1001`.
- **Bot:**
  - The indicators titles "matches the CDC reference fixture bar for bar" and the edge-case and step specs;
  - the Binance TH title "backfills 180 days of 1m bars on first start" (260 windows), "does not store the bar that was forming at request time…" and the 7-day REST guard;
  - the Alpaca 1,000-request limiter spec (window maximum 180);
  - the integration specs `*.int.spec.ts`.
- **Web:** `e2e/src/market-watch*.spec.ts`, `e2e/src/watchlist.spec.ts`, and the unit specs beside each source file.

### Stages (kept distinct)

- **Implemented.** Every planned step, with contracts verified on the build branches:
  - service MIG1–MIG4 and S1–S9;
  - bot S1–S16 plus review fixes r1 and r2, the docs polish, and fixes r3 and r4;
  - web M1 (S1+S2) and S3–S7, plus review fix r1 and the polish.
- **Reviewed.**
  - Migrations: code and security r1.
  - Service: code r3 APPROVED at `04dec78`; security r2 APPROVED at `426fa79`, with LOW-R2-1 confirmed fixed by code r3.
  - Bot: code and security r3 APPROVED at `a289b26`; r4 code and security APPROVED at `99c8511`; code confirmation APPROVED at `06a9ab8`.
  - Web: round 2, 5/5 APPROVED at `a0ac23a` (angular, code, design, security, tailwind-curator). `a7cb23a` was orchestrator-checked and not re-reviewed.
  - Reports: `.forge/features/market-data/review/<project>/r*/`.
- **Verified (build-time).** Fixtures, mocks, disposable databases and loopback Redis. A passing build command never marks a live, browser or SQL-on-live ID verified.
- **Verified (preview).** Forge preview compose project `forge-0199b29a-mdata-d9d3e428`, isolated database, retained volumes, running the reviewed heads. The current URL is `http://127.0.0.1:62244/`; earlier previews ran at `:54736` (bot `9bf762d`), `:64925` (bot `99c8511`) and `:51406` (final heads, no keys).
  - The Alpaca keys were loaded from 11:44 Bangkok. OANDA was never loaded.
  - FR-MD-INFRA-003 and FR-MD-E2E-004 ran on the first preview. Neither path involves the bot.
  - The Playwright journey spends the forced password change. At the owner's request, the preview admin was later set back to the original bootstrap password through `POST /auth/password`.
- **Merged.** 2026-10-07T13:00:54+07:00, at the owner's explicit request (OWNER-5), pinned to the reviewed heads. No CI exists (D4).
- **Deployed / running on the owner's stack.** Nothing. The owner's compose has not been started (the root `.env` does not exist), so every owner-compose re-run is pending.

### Per-ID results (from `verification.md`; no ID failed)

| Area | IDs | Result |
|---|---|---|
| Migrations | FR-MD-MIG-001…006 | passed (disposable DB) |
| Indicators | FR-MD-IND-001…004 | passed. IND-001's fixture README licence clause is open (OI-1). IND-003 has the FU-3 residual. |
| Bot | FR-MD-BOT-001 | passed (unit and image; preview healthy with keys absent). Owner-compose `ps` pending-after-merge. |
| Bot | FR-MD-BOT-002 | passed (fixtures; preview 180-day backfill and live stream on `06a9ab8`, after the `9bf762d` failure). 24 h lifetime and real 429/418 unverified (A5). |
| Bot | FR-MD-BOT-003 | passed (unit; preview SIP 180-day backfill, A6). Live IEX bars and SIP reconciliation pending-preview (US regular session). |
| Bot | FR-MD-BOT-004 | passed (fixtures built from the v20 docs). Live part unverified (FU-4). |
| Bot | FR-MD-BOT-005, 006, 007, 009, 010, 011, 012 | passed (009 also from the preview `/metrics` excerpt) |
| Bot | FR-MD-BOT-008 / FR-MD-E2E-002 | passed (preview: BTCTHB and ETHTHB, 0 missing minutes). NVDA SIP part pending-preview. XAUUSD part unverified (FU-4). Owner compose pending-after-merge. |
| Gold | FR-MD-GOLD-001 | passed (unit). Live part unverified (FU-4, and it needs a GTA publishing day). |
| Lists | FR-MD-LIST-001…003 | passed (fixtures and migrated-DB integration). The live `run list-refresh` transcript is unverified. |
| API | FR-MD-API-001…008 | passed |
| Realtime | FR-MD-WS-001, 002, 004, 005 | passed |
| Realtime | FR-MD-WS-003 | passed (integration p99 4.99 ms). Live tick-to-browser timing unverified. |
| Service | FR-MD-SVC-001, 002 | passed |
| Web | FR-MD-WEB-001 | passed (mocked render; design reviewer at 1440 px, both themes). The preview captures were not re-judged against the mockup. |
| Web | FR-MD-WEB-002, 003, 005, 006, 007 | passed, including the preview live specs and journey |
| Web | FR-MD-WEB-004, 010 | passed (unit and mocked) |
| Web | FR-MD-WEB-008 | passed. The preview rendered only the Live, EOD and Stale tags. |
| Web | FR-MD-WEB-009 | passed on the mocked render (axe 0, overflow 56/56, minimum contrast 4.66:1). Preview axe and other-width contrast unverified. |
| Web | FR-MD-WEB-011 | pending-after-merge (`DESIGN.md`) |
| Infra | FR-MD-INFRA-001 | pending-after-merge (static `docker compose config` only) |
| Infra | FR-MD-INFRA-002, 003 | passed (preview). 002 failed first on `9bf762d`. |
| E2E | FR-MD-E2E-001 | passed for BTC/THB moving, PTT.BK EOD 41.50, and NVDA and AAPL priced. NVDA/AAPL live change pending-preview. ETH/THB change unverified (the market was flat). Gold rows unverified (FU-4). |
| E2E | FR-MD-E2E-003 | passed (preview: 48/48 hours, `EXCEPT` 0 rows both ways, BTCTHB and ETHTHB). Not re-run over NVDA/AAPL. Owner compose pending. |
| E2E | FR-MD-E2E-004 | passed (preview) |
| Docs | FR-MD-DOC-001 | passed |
| Docs | FR-MD-DOC-002 | pending-after-merge (the final report) |

### Manual reproduction

1. **Bring up.** Follow the owner-compose bring-up under Rollout. Expect `tidewatch-bot` healthy, and after a few minutes BTC/THB and ETH/THB live on Overview.
2. **Bot health.** `docker compose exec tidewatch-bot wget -qO- http://127.0.0.1:9091/ready` returns `{"status":"ready"}`. In `/metrics`, `collector_enabled{collector="oanda"}` is 0 while its pair is empty.
3. **`/ws` refusals.** Send an upgrade to `http://localhost:3000/ws`:
   - without a cookie and with the app Origin: `401`;
   - with `Origin: http://evil.example`: `403 origin_rejected` (the README `curl` recipe);
   - a plain `GET /ws` with a valid session: `400` `upgrade_required`.
4. **Restart gap.**
   1. Stop or kill the bot for at least 10 minutes, then start it.
   2. Once it is healthy, run `generate_series` over the last 60 closed minutes `EXCEPT` the stored `ts` for `BTCTHB@binance-th`. Expect 0 rows.
5. **Aggregate equality.** Compare `candles_1h` with `SELECT instrument_id, time_bucket('1 hour', ts), first(o,ts), max(h), min(l), last(c,ts), sum(v), count(*) FROM candles … GROUP BY 1,2` over the last 48 whole hours, both ways with `EXCEPT`. Expect 0 rows.
6. **Watchlist.** Add, remove and reorder through the dialogs, reload, and the order persists. Remove all to see the empty state. Each change publishes `md:subscriptions`.

## Open questions

### Pending, by stage

- **pending-preview (needs the US regular session: 20:30–03:00 Bangkok under EDT, 21:30–04:00 after 2026-11-01).**
  - Live IEX bars and the 5-minute SIP reconciliation (FR-MD-BOT-003).
  - A live NVDA/AAPL price change (FR-MD-E2E-001).
  - The NVDA SIP part of FR-MD-BOT-008 and FR-MD-E2E-002.
- **pending-after-merge, owner compose.**
  - FR-MD-INFRA-001: the bot runs healthy in the root compose. Blocked until the owner creates the root `.env`, which does not exist yet.
  - The owner-compose re-runs of FR-MD-BOT-001 (`ps` healthy), FR-MD-BOT-008, FR-MD-E2E-002 and FR-MD-E2E-003.
- **pending-after-merge, `DESIGN.md` (FR-MD-WEB-011).** In progress as a separate docs PR through `forge-setup-impeccable`, in the `web-design` worktree (branch `codex/forge-mdata-d9d3e428-design`, base `5611d79`). It must:
  - document `TideStrip`, `ZoneLabel`, `.tag`, `Dialog`, `Toast`, the table pattern, the neutral tile, `--backdrop` and the new icons;
  - refresh its source snapshot;
  - record DEV-WEB-CAPTION with the owner's acknowledgement (OC-2) and the design reviewer's A9 items.
- **pending-after-merge, final report (FR-MD-DOC-002).** Not yet written. The out-of-date documents to list are below.
- **Owner decisions.**
  - **A9.** MTS hours 07:00–03:00. Only the calendar can be judged on the preview, because the gold rows have no price.
  - **A16.** UTC-aligned US hourly strips, including extended hours.
  - **OC-1.** The all-listed line uses straight quotes instead of the approved curly ones.
  - **OC-2.** The DEV-WEB-CAPTION acknowledgement.
- **OI-1, the CDC licence.** The licence statement for piriya33's *CDC ActionZone V3 2020* (`th.tradingview.com/v/rGpAOoLi/`) was not captured. The fixture README says "not determinable on 2026-10-06". The Pine source is not vendored.
- **Unverified, no stage assigned.**
  - The live `run list-refresh` transcript (FR-MD-LIST-001).
  - A 24 h Binance TH soak and real 429/418 (A5).
  - The live tick-timestamp timing (FR-MD-WS-003).
  - The preview axe run, the non-populated preview captures, and the Closed, Delayed and Synthetic tag renders (FR-MD-WEB-008, FR-MD-WEB-009).
  - The design reviewer's look at the preview captures (FR-MD-WEB-001).
  - An ETH/THB price change.
- **Unverified, no XAU/USD source (FU-4).**
  - The XAU/USD, Gold 96.5 and GO rows of FR-MD-E2E-001.
  - The XAUUSD parts of FR-MD-BOT-004, FR-MD-BOT-008 and FR-MD-E2E-002.
  - The live half of FR-MD-GOLD-001 (A15, GAP-GOLD-LIVE).

### Known gaps (accepted and documented)

- **GAP-BOT-CATCHUP-IND (FU-3).**
  - After a restart, the clamped catch-up refresh rebuilds the aggregates but never re-marks indicators: `sink.ts` passes it an empty instrument map.
  - So after an interrupted backfill of bars older than 3 days, the 15m, 1h and 1d `indicators` rows over the gap can stay missing, and later EMA and ATR values are computed across the gap.
  - Manual recovery is in the bot README (above).
  - The proposed fix: at serve start, mark each intraday instrument dirty from the earliest bucket that has an aggregate but no indicator row, or persist the carried ranges.
- **GAP-GOLD-LIVE.** The live gold check needs an XAU/USD source and a GTA publishing day. Its `state.json` text still names OANDA keys and predates FU-4.
- **Calendars.**
  - The NYSE early-close late session (to 17:00 ET) is not encoded; post and overnight are dropped after a 13:00 early close.
  - TFEX holiday-eve night sessions are not encoded; only full-day closures are.
  - OANDA's daily 16:59–17:05 break is not modelled in `fx-24-5`, so FX rows can read stale for about 4 minutes a day.
- **PRD §10.**
  - Thai stocks are end-of-day only.
  - Webull's overnight session has no data.
  - GO and GOLD9999USD carry no basis or dealer spread.
  - US hourly bars are UTC-aligned (A16).
  - The signals column is a placeholder.
  - Chart consumption of `packages/indicators` is deferred to slice 5.
- **Web.**
  - Long names lose the venue first (design N1).
  - Phone rows hold three lines in 61 px (design N2).
  - *Edit list* reopened during an in-flight save builds its draft from the pre-save rows (a narrow race).
  - GAP-WEB-PRETTIER: `prettier --check` fails on README.md and CLAUDE.md, as it already did at the base.
- **Service.** The `/ws` cap, subscription counts and fan-out are per process (SV15); scaling out is not built.
- **Bot round-4 info notes (not registered as follow-ups).**
  - Time to live on a first start is bound by latency and the per-instrument aggregate flush.
  - A Binance TH pair with no history re-scans 260 windows per connect.
  - A persistent failure after empty windows re-fetches them on each 30 s retry, up to 1,300 weight (security r4 I-1).
  - Error bodies of up to 32 MiB are JSON-parsed, 1.6 s in the worst case (security r4 I-2).
- **Accepted security info items.**
  - Bot I-1: the fallback logger in `exitCodeOf`.
  - Bot I-2: a lock-loss detection window of about 25 s.
  - Service INFO-1: CSRF/CORS refusals and 404s carry no `no-store` (ORCH-29).

### Follow-ups

- **FU-2 (bot).** `prom-client` is deprecated upstream (replaced by `@prometheus-io/client`). The owner decides on a later migration. Only `metrics.ts` imports it.
- **FU-3 (bot).** Re-mark indicators after the catch-up refresh (see above).
- **FU-4 (tidewatch-specs and bot).** Replace OANDA practice as the XAU/USD source through a new `/forge-spec` run. Deferred by the owner on 2026-10-07 (OWNER-4).
- **FU-5 (bot).** Log the expected "concurrent refresh" transient at warn with a distinct reason, or retry sooner. Today it logs `aggregates_refresh_failed` at level 50.
- **FU-1** is resolved (folded into the migrations review fix `d77efa8`).
- **API collection (P2).** OpenAPI and Bruno for §6.1 in `tidewatch-apis` were skipped, because that folder is not a git repo.
- **Carried from slice 0.** Pin base images by digest (with CI, D4); merge `config.parseOrigin` with `origin.Normalise`; move `@angular-devkit/build-angular` to `devDependencies`; decide a framing policy for HTML responses.

### Out-of-date documents (FR-MD-DOC-002; not edited, per D17)

- `documents/02-architecture.md` §3 says "1m/5m for US where available, 15m otherwise". Intraday US bars are now SIP 1m (MD9).
- `documents/02-architecture.md` §10's storage table lacks `candles_eod` (MD4).
- `documents/features/01-market-data-and-instruments.md` calls `top20_binance_th` "top 20", but it holds at most about 10 THB pairs today (MD7).
- **PRD erratum (R1).** The error envelope field is `requestID`, not `request_id`.
- **The specs' OANDA practice source** (intent "OANDA practice serves XAU/USD", PRD A3) does not hold for the owner's region (FU-4).

### Bookkeeping drift

- `verification.md` was last updated at 11:54 Bangkok, before the merge at 13:00:54. Its section 1 still says "No code PR is merged" and lists bot PR #2 as "(open)". `state.json` `lanes` still say "waiting for the PR phase". The merge facts above come from `state.json` (`mergeCommit`, `mergedAt`, the `all-prs-merged` log entry).
- The `state.json` execution entries stop at service S6, bot S9 and web S7, while `completedSteps` and the evidence show every step done. The ledger relies on the evidence.
- The `state.json` FR-MD-E2E-001, FR-MD-E2E-002 and FR-MD-BOT-008 results still say "owner keys absent". The ledger rows supersede them: Alpaca was loaded, and OANDA is unavailable.
- Preview evidence spans three bot revisions:
  - FR-MD-BOT-009's `/metrics` excerpt and FR-MD-E2E-003's data come from `99c8511`;
  - FR-MD-INFRA-003 and FR-MD-E2E-004 ran on `9bf762d`;
  - everything else ran on `06a9ab8`.
  - The excerpts and the populated captures predate the Alpaca keys.

## Cross-cutting links

Existing wiki pages this feature extends:
- `[[foundation-auth]]`: Slice 0, which this slice builds on.
- `[[centralized-migrations]]`: migrations A–C and the required version moving to `20261006131346`.
- `[[request-protection]]`: `/ws` reuses exact-origin matching as `origin_rejected`, and CSRF covers the watchlist mutations.
- `[[auth-model]]`: the gate chain on every market route, the 60 s non-touching session re-check, and the 4401/4403 closes.
- `[[forge-preview-gateway]]`: `/api/ws` upgrades through Caddy with the Origin rewrite (FR-MD-INFRA-003).
- `[[design-system-decisions]]`: the new `.tag`, `--backdrop`, `TideStrip`, `ZoneLabel`, `Dialog` and `Toast`, and the pending DESIGN.md refresh.

Candidate new pages for the wiki-updater to decide on:
- `market-data` (slice overview)
- `instrument-master` (ids, aliases, lists)
- `market-calendars`
- `timeseries-storage` (candles, candles_eod, aggregates, retention and refresh rules)
- `redis-market-contract`
- `realtime-websocket`
- `market-data-worker` (runner locks, jobs, collectors)
- `binance-th-collector` (the 7-day klines rule)
- `alpaca-collector`
- `xau-usd-source` (FU-4)
- `cdc-indicators`
- `market-watch-ui`
