# Fix: XAU/USD priced from Binance TH XAUTUSDT (xau-feed-binance-th)

> A standalone `/forge-fix` (run `fix-xau-feed-649e2a7a`, Billet `bl-tY1CZC1Dn86G` / TB-24) for the slice-1 market-data gap FU-4: the four gold rows had no price because `XAUUSD@oanda-demo` was fed by OANDA practice v20, which the owner can never use (Thai-region OANDA Global Markets is MT5-only and excluded from v20). The fix repoints that one instrument row to the Binance TH `XAUTUSDT` pair (Tether Gold, 1 token = 1 troy ounce) through the Binance TH collector that already shipped, keeps the instrument id, venue, `gold-23-5` calendar and `quote_ccy`, gates Binance TH bars and ticks by the instrument's own calendar, and activates the `USDTTHB` USD/THB proxy at `serve` start whenever OANDA is disabled (an extension the diagnosis found necessary). Two PRs merged on 2026-10-07: tidewatch-migrations #3 (migration D, merge `a2e7f81`, 16:51:17Z) and tidewatch-bot #3 (merge `a420767`, 16:51:22Z). tidewatch-service and tidewatch-web are unchanged. On the Forge preview, XAU/USD went Live, the three synthetics rebuilt, a 12.6-minute restart left 0 missing XAU minutes, and the first live `gold_premium_checks` row deviated −0.021 % from GTA (not flagged). The market-data feature state records FU-4, OI-4 and GAP-GOLD-LIVE as resolved by this fix. One pre-existing follow-up was recorded (FU-FIX-1) and the PRD deviation record is still to be written into `prd.md`.

**Sources (inputs to this document).**
- Owner's fix report: `/Users/maichinu/tidewatch/tidewatch-specs/market-data/fix-xau-usd-feed.md`
- Diagnosis: `/Users/maichinu/tidewatch/.forge/fixes/xau-feed-binance-th/diagnosis/brief.json`, `…/diagnosis/evidence.md`
- Engineer reports: `…/reports/migrations-engineer-r1.md`, `…/reports/bot-engineer-r1.md`
- Reviews: `…/review/code-reviewer-r1.md`, `…/review/security-reviewer-r1.md`
- Preview acceptance: `…/reports/preview-acceptance.md`
- Fix state: `…/state.json` (log, `followUps`, merge records)
- Market-data PRD the fix deviates from: `/Users/maichinu/tidewatch/tidewatch-specs/market-data/prd.md` (§3, §4.1, §4.2, §4.4, §4.5, §4.10, A3)

## Concept

### The bug

- Documented behaviour (PRD): FR-MD-E2E-001 says all eight watchlist rows show a price, and `XAUUSD@oanda-demo`, `GOLD965THB@mts` and `GO@tfex` are three of them. FR-MD-BOT-006 says `GO` and `GOLD9999USD` equal the XAU/USD bars and `GOLD965THB` equals the formula plus `premium_applied`. FR-MD-GOLD-001 says the daily GTA check writes a `gold_premium_checks` row with `|deviation_pct| ≤ 1`. FR-MD-BOT-008 says a restart of ≥ 10 min leaves no missing 1m bars for `XAUUSD` while its session is open.
- Actual behaviour at the end of slice 1: the four gold rows (`XAUUSD@oanda-demo`, `GOLD965THB@mts`, `GO@tfex`, `GOLD9999USD@mts`) read *Stale* with no price, and every XAU/USD-dependent acceptance ID was "unverified (no source)". The PRD's XAU/USD feed is the OANDA practice v20 API (`XAU_USD`). The owner's OANDA account is in the Thai region, served by OANDA Global Markets (MT5 only), which OANDA's v20 docs exclude, so `OANDA_DEMO_TOKEN` / `OANDA_DEMO_ACCOUNT_ID` can never exist (OWNER-4 in the market-data feature). The owner deferred the replacement as FU-4 on 2026-10-07 and then chose Binance TH tokenized gold, XAUT first, the same day (fix report).

### Confirmed root cause (diagnosis, confidence `confirmed`, scope `corrective`)

The chain, with the lines inspected at bot `5a60477` and migrations `cb93cd5`:

1. Seed: `migrations/20261006100927_market_reference.sql:327` seeds `XAUUSD@oanda-demo` with `feed='oanda'`, `feed_symbol='XAU_USD'`, `tick_size 0.01`, `lot_size NULL`, calendar `gold-23-5`.
2. The OANDA collector is disabled without keys (`packages/worker/src/serve.ts:147-170`, `:198-200`: `missing_secrets`, no runner), so XAU gets neither backfill nor live bars.
3. The synthetic engine keys on the instrument id and starves (`synthetic/engine.ts:248-254`, `:415-419`); the premium check logs `gold_premium_check_skipped` with `missing: ['xau_usd']` (`collectors/gta/premium.ts:188-224`); staleness marks XAU `collector_disabled` and the synthetics `component_stale` (`status/staleness.ts:139-141`, `:183-195`).
4. Repointing the row to Binance TH was blocked: `refreshMetadata` in `collectors/binance-th/collector.ts` kept only `quoteAsset === 'THB'` symbols (`:277`, `:290-296`, `:302-305`), so a USDT-quoted feed symbol was never TRADING in `symbolStatus`, `wantedStreams` logged `binance_th_symbol_not_trading` with `status: 'unlisted'` and never subscribed (`:370-377`), and `fillInstrumentSizes` never filled its sizes.
5. A second link the owner's report assumed away: the `USDTTHB@binance-th` proxy instrument was created, and the process-wide USD/THB holder switched, only inside the OANDA collector's `useProxy()` (`collectors/oanda/collector.ts:399-416`), which runs after a successful OANDA startup check and so never runs without keys. With the holder left at OANDA, `GOLD965THB` stays `component_stale` (judged on `USDTHB@oanda-demo`), USDTTHB writes trigger no `GOLD965THB` build (`engine.ts:505-512`), and USDTTHB is not tier 0 in the Binance TH set. The preview DB state for that row was suspected, not observed, at diagnosis time.

### The correction (owner-approved defaults plus one extension)

1. **Feed symbol `XAUTUSDT`** on Binance TH (`PAXGUSDT` is the documented alternative; both are listed `TRADING` on `api.binance.th` with tick 0.01 and lot 0.0001, and share Binance global's order book).
2. **Instrument id stays `XAUUSD@oanda-demo`.** Venue is where the instrument would be paper-traded (the owner's OANDA MT5 demo); feed is where the price comes from, and the PRD separates the two (§3 "Feed … is separate from the venue"). The service's default watchlist, the web, the Redis keys and every id-keyed consumer therefore need no change. `name` becomes `Gold spot (XAUT proxy)`; `quote_ccy` stays `USD` (USDT ≈ USD, the same convention as the USDTTHB proxy).
3. **Keep the `gold-23-5` calendar and gate XAU bars by it.** XAUT trades on Saturday and Sunday almost flat (1m-return sd 0.005 % against 0.03 % on weekdays). Without gating, every Monday's 48-bar tide strip would carry about 48 flat weekend bars and the CDC zone would stop matching a gold chart. Live and backfill paths skip bars whose `ts` is outside the instrument's calendar session, the rule the synthetic engine already applied; ticks are gated with the bars so `px:last` carries no out-of-session prints. Status outside the session is *Closed · opens …*, never *Stale*; the status layer already derived that from the instrument's own calendar, so no status rule changed.
4. **USD/THB unchanged in intent:** `USDTHB@oanda-demo` keeps `feed='oanda'` (inactive without keys); the premium check records `usd_thb_source='binance-th-usdt'`. **Extension (brief `decisionsAssumed[0]`):** because of root-cause link 5, the bot now activates the USDTTHB proxy at `serve` start whenever `'oanda'` is not in the enabled collector set. A code route was chosen over seeding `USDTTHB@binance-th` in the migration so the proxy's creation stays in one place.
5. **The OANDA collector stays in the tree, dormant.** It still works if a v20 account ever appears, and still calls the same proxy helper with reason `usd_thb_unavailable`. Both OANDA lines in the secrets file stay empty (a half-filled pair exits the bot). The owner is never asked for OANDA keys.

### Why XAUT, and what was rejected (evidence gathered 2026-10-07 from the owner's network, fix report)

- Binance TH `exchangeInfo` lists `XAUTUSDT` and `PAXGUSDT` as `TRADING` (quote `USDT`); `nbstream.binance.th` streams `xautusdt@kline_1m`; REST 1m klines over the last 120 minutes had 0 gaps (2–3 zero-volume bars).
- Tracking over 7 days of 1m closes (7,002 overlapping minutes): XAUT / COMEX `GC=F` ratio sd **0.057 %** (PAXG 0.058 %; the −0.66 % mean is the futures basis). Against GTA's own `goldSpot` (4,146.0 at 09:06 Bangkok): XAUT −0.085 %, PAXG +0.037 %, inside the 1 % GTA tolerance; the 30-day premium median absorbs any steady offset.
- Liquidity (24 h): XAUT 48k trades / $20.6M, PAXG 26k / $12.2M on the shared book.
- Rejected: Deriv (HTTP 520 from this network), Finnhub (forex candles 403 on free), Massive/Polygon (EOD only), Twelve Data (REST-only free tier; noted as a viable fallback), Yahoo `GC=F` (futures, unofficial), goldapi.io / API Ninjas / supapongai (quotes only or paid).

### Caller-visible implications

- **Market watch:** the XAU/USD row is *Live* (feed `binance-th` → mode `live`), named "Gold spot (XAUT proxy)" with the venue label still "OANDA demo". `GO`, `GOLD9999USD` and `GOLD965THB` are *Synthetic* inside their own sessions and *Closed · opens …* outside. Outside `gold-23-5` (Sun–Thu 18:00–17:00 New York) XAU reads *Closed*, never *Stale*.
- **Expected blips:** up to ~60 s *Stale* at each `gold-23-5` open, because Binance TH staleness is judged on closed bars and the first in-session kline closes a minute after the open (same class as the OANDA daily-break note; confined to XAU since the synthetics on `mts`/`tfex` are closed at 05:00 Bangkok). After a fresh-DB first start, XAU showed *Stale* for ~3 min on the preview because the Binance TH collector opens its stream only after every instrument's backfill (pre-existing first-start behaviour, not the open blip).
- **Stored data:** no XAU bars on Saturday New York, after the Friday 17:00 close or in the weekday 17:00–18:00 break; the cursor still advances across gated minutes, so a restart during a gap resumes after it. `px:last` for XAU carries no out-of-session prints. Lot size for XAU is stored as the venue's text `0.00010` (numeric 0.0001); tick stays the seeded `0.01`.
- **Premium check:** `xau_usd` in `gold_premium_checks` is now an XAUT/USDT 1m close rather than an OANDA mid; `usd_thb_source` is `binance-th-usdt`. The table has no `xau_usd_source` column (an optional later follow-up, out of scope here).
- **Subscriptions:** XAU/USD joins the Binance TH realtime set as a tier-0 component (and USDTTHB once the holder names the proxy), so the 20-instrument cap holds one fewer low-ranked `top20_binance_th` member (by design, asserted in the manager specs).
- **Operators:** every `serve` start without OANDA logs `usd_thb_proxy_in_use` with `reason: 'oanda_disabled'` (at `warn`, the steady state; see Open questions). New events `binance_th_bar_outside_session` (info; `dropped` count per backfill window, `ts` once per live gap) and `usd_thb_proxy_failed` (retried after each 60 s reference refresh). `binance_th_metadata_refreshed` gains `symbols` (every `exchangeInfo` symbol; 520 at capture, 11 THB, 383 USDT). The README logs table went from 169 to 171 rows.
- **Compatibility:** a running bot picks the migrated row up within 60 s through the reference cache, but a restart after `migrate` is recommended so the proxy activation and the 180-day XAU and USDTTHB backfills are logged. Old bot + new row only logs `binance_th_symbol_not_trading`; new bot + old row is a no-op. tidewatch-service keeps `XAUUSD@oanda-demo` as the default watchlist id (`internal/market/defaults.go:16`) and `/ready` checks C `is_applied` by version (`schema.go:97`), tolerant of a newer D. tidewatch-web keys the status tag on mode/stale/session/next_open_at only. Neither changed.

### Deviations from the market-data PRD (recorded here and, since 2026-10-07 16:55Z, in `prd.md` §10 "Deviations recorded after the build" plus a decision-history row)

| PRD location | PRD text | After this fix |
|---|---|---|
| §3 Feed vs venue | Feed is separate from the venue | Unchanged principle; it is the reason the id and venue `oanda-demo` stay while the feed moves |
| §4.1 seed row (line 88) | `XAUUSD@oanda-demo` · Gold spot · OANDA demo · feed `oanda (XAU_USD)` | feed `binance-th (XAUTUSDT)`, name `Gold spot (XAUT proxy)`; venue, class `gold`, quote `USD`, calendar `gold-23-5`, base `1m`, daily `aggregate`, watchlist position 5 unchanged |
| §4.1 (line 79) | Collectors may refresh sizes from `exchangeInfo` (Binance TH) | Now applies to XAU: `lot_size` filled `0.00010`, `tick_size` kept |
| §4.2 (line 132) | `gold-23-5` "OANDA XAU_USD hours" | Calendar kept as the XAU session definition even though XAUT itself trades continuously; Binance TH bars and ticks outside it are dropped |
| §4.4 Binance TH row | "subscribes every active THB instrument (≤ 20)"; symbol metadata from `exchangeInfo` | Subscribes every active `feed='binance-th'` instrument regardless of quote asset; metadata indexes every `exchangeInfo` symbol (the THB subset remains for the "no THB symbols listed" guard and the `top20_binance_th` list job); bars and ticks are written only inside the instrument's calendar (the Synthetic row's rule, now applied by a venue collector) |
| §4.4 OANDA row | Proxy `usd_thb_proxy_in_use` when USD_THB is unavailable (A3) | Collector dormant; the proxy is also activated at `serve` start when OANDA is disabled (`reason: oanda_disabled`); the OANDA path keeps `reason: usd_thb_unavailable` |
| §4.4 (line 197) | Binance TH keeps "all THB pairs (at most 20) and the two OANDA instruments" | The Binance TH set also carries XAU (tier 0) and USDTTHB; the OANDA set is empty without keys |
| §4.5 premium | `raw = xau_usd × usd_thb × …` from the 1m closes at the round's minute | Same formula; `xau_usd` is the XAUT/USDT close, `usd_thb` the USDTTHB close (`usd_thb_source='binance-th-usdt'`) |
| §4.10 thresholds (line 315) | `oanda`: no `PRICE` for 2 min | XAU is judged by the Binance TH closed-bar rule on its own calendar; the OANDA rule now applies only to `USDTHB@oanda-demo` |
| A3 | The owner's OANDA practice division offers XAU_USD and USD_THB | False for the owner. Both legs are Binance TH proxies: USDTTHB for USD/THB, XAUT for XAU/USD |
| §9 / Readiness | OANDA live evidence needs the owner's keys; otherwise unverified | The XAU parts of FR-MD-E2E-001, FR-MD-BOT-008 and the live half of FR-MD-GOLD-001 now have preview evidence without OANDA keys (Test plan) |

## Database

**Migration D** — `tidewatch-migrations/migrations/20261007072235_market_xau_feed_binance_th.sql` (goose version `20261007072235`, generated with `make migrate-create NAME=market_xau_feed_binance_th`, goose default transaction). Data only; no CHECK or view change, no alias change, slice-1 seed file untouched.

```sql
-- +goose Up
UPDATE instruments
   SET feed = 'binance-th',
       feed_symbol = 'XAUTUSDT',
       name = 'Gold spot (XAUT proxy)',
       updated_at = now()
 WHERE instrument_id = 'XAUUSD@oanda-demo';

-- +goose Down
UPDATE instruments
   SET feed = 'oanda',
       feed_symbol = 'XAU_USD',
       name = 'Gold spot',
       updated_at = now()
 WHERE instrument_id = 'XAUUSD@oanda-demo';
```

(Shape as described in the engineer report; the committed file carries a header citing the fix report and the PRD deviation.)

- Row after D, as asserted by the harness: `XAUUSD@oanda-demo|XAUUSD|XAU/USD|Gold spot (XAUT proxy)|gold|oanda-demo|USD|0.01|NULL|gold-23-5|true|binance-th|XAUTUSDT|NULL|1m|aggregate|NULL|NULL`, with `updated_at >= created_at` and no other instrument row touched.
- CHECKs already allowed the new values: `feed IN (… 'binance-th' …)`, `instruments_feed_synthetic_formula_check` (feed ≠ synthetic, formula NULL), `instruments_instrument_id_check` (id/symbol/venue unchanged); `feed_symbol` has no CHECK. No view or function reads `feed` (`candles_daily` switches on `daily_source`).
- `tick_size` stays `0.01` (equals XAUTUSDT's tick), `lot_size` stays `NULL` so the collector's NULL-only size fill writes `0.00010`. The seeded `name` alias "Gold spot" is kept (search still matches; alias dump and count unchanged).
- **Required schema version unchanged:** the service still pins C (`20261006131346`, `market_calendar_exceptions`); D is "later and not pinned".
- **Down caveat:** Down restores the row only. XAU candles and the `binance-th` collector cursor written meanwhile stay (the cursor key includes the collector, so there is no clash with an OANDA cursor).
- **Harness `scripts/check-disposable-db.sh`:** `expected_migrations` += `market_xau_feed_binance_th`; `xf_index` via `mig_index` (0-based); the 18-column instrument projection extracted to `instrument_row`; `ref_expected_instruments` holds A's nine untouched rows with `xau_seed_row` / `xau_binance_th_row` beside it; `assert_market_reference` appends the XAU row per phase (`applied_n > xf_index` → D's row, else the seed row) so A's exact dump stays valid in every pass; new `relations_` (no-op), `assert_` and `absent_` functions for D (`absent_` passes when `instruments` is gone); D transcript and two summary lines. README and CLAUDE.md (outside the Forge block) document D, the phase gate and "a seed correction is a new migration".
- **Bot `scripts/sql-integration.sh`** (previously pinned `max(version_id) == C`): enumerates D as optional (at most one file) so it still runs against a migrations checkout without D; requires C `is_applied`, requires D applied when present, accepts a newer maximum; hashes A–D; records the required and the newest applied version.

## API

_n/a_ — no REST route, `/ws` message, error code or Redis key changed. tidewatch-service and tidewatch-web were not modified (see Caller-visible implications for why they tolerate D and the new feed).

## Components

### tidewatch-bot (`codex/forge-fix-xau-feed-649e2a7a-6945fd5d6c`, delivered `989214d`, PR #3)

- **`packages/market-data/src/collectors/binance-th/collector.ts`.** `refreshMetadata` indexes every `exchangeInfo` symbol into `symbolStatus` and fills NULL sizes by `feedSymbol` through a `bySymbol` map; keeps the THB subset for the "no THB symbols listed" guard and the `thb_symbols` log field; adds `symbols`. `wantedStreams` is unchanged and feed-based, so widening the index cannot subscribe a symbol that has no `feed='binance-th'` row. Calendar gating via `inSession`: the REST backfill filters after `closed` (`row.closeTime < now`) is computed and keeps `lastClosed`/`resume` from the unfiltered rows, so a window wholly inside a weekend still advances the cursor and is never re-fetched; the live path drops the tick, the `price` observation and the bar outside the session but still `advanceCursor`s a closed minute. An `outsideSession` set logs `binance_th_bar_outside_session` once per gap on the stream.
- **`packages/market-data/src/calendar/in-session.ts` (new).** `inSession(reference, instrument, at)`: the instrument's own calendar through the existing `isOpen` (DST via luxon, exceptions applied, compiled calendars WeakMap-cached); unknown calendar → `true` so nothing is dropped. Exports `CalendarLookup`.
- **`packages/market-data/src/core/usd-thb-source.ts`.** `PROXY_INSTRUMENT` (`USDTTHB@binance-th`, moved from the OANDA collector, same row), `UsdThbProxyReason` (`'oanda_disabled' | 'usd_thb_unavailable'`), `activateUsdThbProxy({ repos, reference, holder, logger, reason })`: upsert the instrument and its `ticker` alias, `reference.refresh()`, `holder.set(PROXY_USD_THB)`, log `usd_thb_proxy_in_use` with `reason`. The upsert is idempotent (`WHERE … IS DISTINCT FROM`, `active` coalesced, sizes coalesced), so it cannot wipe collector-filled sizes or reactivate an owner-deactivated row.
- **`packages/market-data/src/collectors/oanda/collector.ts`.** `useProxy()` delegates to the helper with `reason: 'usd_thb_unavailable'`; local proxy constants removed; otherwise untouched.
- **`packages/worker/src/serve.ts`.** `ServeOptions.usdThbSource?` (defaults to the process-wide holder, a test seam). `ensureUsdThbProxy()` runs when `'oanda'` is not in `selection.enabled`, after the first `refreshReference()` and before the standby/runner loops start, so the synthetic engine initialises with the proxy as its USD/THB source. A failure logs `usd_thb_proxy_failed` and is retried on each 60 s reference refresh until it succeeds; silenced when stopping.
- **`packages/market-data/src/index.ts`.** Exports `inSession`, `CalendarLookup`, `PROXY_INSTRUMENT`, `activateUsdThbProxy`, `UsdThbProxyReason`, `ActivateUsdThbProxyOptions`.
- **Test doubles.** `testing/memory-repositories.ts` seeds XAU in the post-migration state (`binance-th`, `XAUTUSDT`, `Gold spot (XAUT proxy)`, `lotSize` NULL; the `name` alias stays `Gold spot`). The OANDA collector spec upserts the migration-A XAU row in its own `setup()` so its 14 specs keep their meaning.
- **Fixtures (`packages/market-data/fixtures/binance-th/`, captured 2026-10-07 from the owner's network, no key, `User-Agent: Tidewatch/0.0.1`, hashes in the fixtures README):** `exchange-info-xautusdt.json` (excerpt keeping `BTCTHB`, `ETHTHB`, `PAXGUSDT`, `USDTTHB`, `XAUTUSDT` verbatim), `klines-xautusdt-1m.json` (Friday 2026-10-02 20:50–21:09Z around the 17:00 New York close), `klines-xautusdt-1m-sunday-open.json` (Sunday 2026-10-04 21:50–22:09Z around the 18:00 open), `ws-session-xautusdt.ndjson` (bare endpoint, `SUBSCRIBE xautusdt@kline_1m`, ack, one closed kline, four forming klines, close 1000; 29.7 s). The captures show the regime change plainly (minute volume 15.97 → 1.79 at the Friday close; 0.756 → 63.26 at the Sunday open). A full-page weekend span is not committed by convention, so the whole-weekend spec uses constructed rows shaped like the capture.
- **Docs.** README (collector rows, "XAU/USD from Binance TH" paragraph with the gating rule, Closed-not-Stale and the ≤ 60 s blip; logs table; schema dependency), CLAUDE.md outside the managed block (managed block byte-identical, sha256 `848d7342…a507`), `.env.example` (OANDA pair optional in practice; XAU/USD and USD/THB no longer depend on it; leave both empty), fixtures README capture record.

### tidewatch-migrations (`codex/forge-fix-xau-feed-649e2a7a-b7ddc75378`, delivered `5831a72`, PR #3)

See Database. The CLAUDE.md Forge block is byte-identical to HEAD (`cmp`).

### tidewatch-service, tidewatch-web

Unchanged (read-only compatibility lookups only; both extended into the preview at `origin/main`: service `734ce35`, web `a9459e0`).

## Files touched

**tidewatch-migrations** (3 modified, 1 created)

- `migrations/20261007072235_market_xau_feed_binance_th.sql` (created)
- `scripts/check-disposable-db.sh` (modified)
- `README.md` (modified)
- `CLAUDE.md` (modified, outside the Forge block)

**tidewatch-bot** (18 modified, 6 created)

- `packages/market-data/src/collectors/binance-th/collector.ts` (modified)
- `packages/market-data/src/calendar/in-session.ts` (created)
- `packages/market-data/src/calendar/in-session.spec.ts` (created)
- `packages/market-data/src/core/usd-thb-source.ts` (modified)
- `packages/market-data/src/collectors/oanda/collector.ts` (modified)
- `packages/market-data/src/index.ts` (modified)
- `packages/worker/src/serve.ts` (modified)
- `packages/market-data/src/testing/memory-repositories.ts` (modified)
- `packages/market-data/src/collectors/binance-th/collector.spec.ts` (modified)
- `packages/market-data/src/collectors/binance-th/rest.spec.ts` (modified)
- `packages/market-data/src/collectors/oanda/collector.spec.ts` (modified)
- `packages/market-data/src/status/staleness.spec.ts` (modified)
- `packages/market-data/src/status/status-publisher.spec.ts` (modified)
- `packages/market-data/src/subscriptions/manager.spec.ts` (modified)
- `packages/worker/src/serve.spec.ts` (modified)
- `packages/market-data/fixtures/binance-th/exchange-info-xautusdt.json` (created)
- `packages/market-data/fixtures/binance-th/klines-xautusdt-1m.json` (created)
- `packages/market-data/fixtures/binance-th/klines-xautusdt-1m-sunday-open.json` (created)
- `packages/market-data/fixtures/binance-th/ws-session-xautusdt.ndjson` (created)
- `packages/market-data/fixtures/README.md` (modified)
- `scripts/sql-integration.sh` (modified)
- `README.md` (modified)
- `CLAUDE.md` (modified, outside the managed block)
- `.env.example` (modified)

Not touched, deliberately: `jobs/lists/sources/binance-th-top20.ts` (keeps its THB filter), `status/*.ts` rules, `synthetic/*`, `collectors/gta/*`, `packages/shared/src/config.ts`, `transport/*`, `package.json` / lockfile (no new dependency), tidewatch-service, tidewatch-web, `tidewatch-specs/market-data/prd.md`.

## Test plan

### Commands

tidewatch-bot (from the project root):

```sh
pnpm install --frozen-lockfile
pnpm nx test @tidewatch-bot/market-data
pnpm nx run-many -t lint test typecheck build
# Docker, optional: migrate image built from a migrations checkout, goose A–D, *.int.spec.ts
TIDEWATCH_MIGRATIONS_DIR=<migrations checkout> bash scripts/sql-integration.sh
```

Docs cross-check (not a committed script): distinct `event: '<name>'` literals in non-spec `packages/*/src` must equal the README `### Logs` rows; the method is `.forge/features/market-data/evidence/tidewatch-bot/review-fix-r2/06-docs-crosscheck.sh`. Expected after this fix: 171 = 171, and the CLAUDE.md managed block sha256 unchanged.

tidewatch-migrations:

```sh
make migrate-validate            # 6 files parse; D Txn ✔, Up 1 / Down 1
bash -n scripts/check-disposable-db.sh
make check-disposable-db         # Docker; must print `check-disposable-db: PASS`
```

### Specs that pin the behaviour

- `collectors/binance-th/collector.spec.ts` (20 → 25): `admits a USDT-quoted feed symbol: XAUTUSDT is subscribed and its NULL lot size is filled`; `replays the captured xautusdt@kline_1m session…`; `drops backfilled bars outside the instrument calendar…`; `pages across a gated weekend…` (stored set asserted against `isOpen(gold-23-5)` itself); `drops live klines and ticks outside the session…` (placed at the Sunday 21:58 → 22:01Z boundary so the first in-session kline after the gap is shown being published again).
- `collectors/binance-th/rest.spec.ts` (9 → 10): `parses the captured XAUTUSDT fixtures: …`.
- `calendar/in-session.spec.ts` (new): truth table on `gold-23-5` (Friday close, Sunday open, weekday break), `crypto`, unknown calendar. Session edges: the 16:59 NY bar (open 20:59Z) is stored, the 17:00 bar dropped, the 18:00 bar stored.
- `status/status-publisher.spec.ts`: `reports a Binance TH instrument on gold-23-5 as closed, not stale, outside its session` (`px:last.ts` of a stored closed bar is the bar's close time, 21:00Z).
- `status/staleness.spec.ts`: XAU judged by the Binance TH closed-bar rule; OANDA-threshold assertions moved to `USDTHB@oanda-demo`; Saturday → XAU closed, `reason: null`, `nextOpenAt` Sunday 22:00Z.
- `subscriptions/manager.spec.ts`: XAU leads the Binance TH set; the 20-cap keeps `USDT, XAU, …` and truncates `C16`; the real-collector spec uses 16 filler pairs instead of 17.
- `worker/src/serve.spec.ts` (+3): proxy activated at start when OANDA is disabled (before `collector_started`, instrument and alias written, holder switched); untouched when OANDA is enabled; retried with the reference refresh after a failed first attempt.
- `collectors/oanda/collector.spec.ts`: unchanged meaning through a local XAU override.

Red-before evidence (unchanged collector, 07:47:14Z): all five new collector specs failed; the first failure is the symptom itself — `Expected "0:SUBSCRIBE:xautusdt@kline_1m,btcthb@kline_1m|2"`, `Received "0:SUBSCRIBE:btcthb@kline_1m|1"`. With the metadata fix alone (07:48:55Z) the admission spec passed and the gating specs failed on stored weekend bars (all 20 Friday minutes stored; 5,484 minutes stored instead of 2,484 on the weekend walk). With `inSession` gating: 25/25.

### Results recorded (engineer, orchestrator and reviewer runs, 2026-10-07)

| Check | Result |
|---|---|
| Migrations baseline harness on untouched HEAD (scratchpad copy) | PASS, 641 PASS lines, 2m06s |
| `make check-disposable-db` with D | `check-disposable-db: PASS`, 649 PASS / 0 FAIL, 3m03s (07:28:03Z–07:31:06Z): D's exact row, `updated_at >= created_at`, seed row back after `make migrate-down`, `down-to 20261004153023` and `down-to 0` round trips, A's named-constraint probes and alias dump green with the new row; pin summary `market_calendar_exceptions version: 20261006131346 <- RequiredSchemaVersion`, `market_xau_feed_binance_th version: 20261007072235` |
| `make migrate-validate`, `bash -n`, CLAUDE.md block `cmp` | ok / ok / byte-identical |
| Bot touched specs (10 files, default timeouts, JSON report `tmp/vitest-fix-xau-market-data.json`) | 92/92 |
| `pnpm nx run-many -t lint test typecheck build --skip-nx-cache` (final, load ≈ 9) | all four packages green: shared 56/56, indicators 22/22, worker 42/42, market-data 362/362 |
| Earlier runs at host load 24–32 | timeouts only in untouched timing-sensitive specs (`calendar.spec`, `http.spec` real-timer probe, `sources.spec` SSGA < 500 ms, `decimal`, `logger`, `yahoo`, `indicators`); each passes alone; no timeout or config was changed. Orchestrator rerun: 360/362 under load, the two untouched files 29/29 alone |
| Docs cross-check | code events 171 = README events 171; managed block sha256 `848d7342…a507` = HEAD |
| `scripts/sql-integration.sh` against the migrations worktree | `sql-integration: PASS` (engineer 08:29:20Z, 16 s; orchestrator rerun 08:57:12Z): goose to `20261007072235`, `schema version: 20261006131346 (market_calendar_exceptions) applied; newest applied: 20261007072235`, int specs market-data 16/16 and worker 2/2, every labelled resource cleaned. A first attempt at 08:11Z was killed after Docker Desktop's VM hung; Docker was restarted with the owner's approval at 08:53Z |
| code-reviewer r1 | APPROVED on snapshot fingerprint `1160e11dafde…`; 0 blocking, 0 major, 2 minor (PRD/wiki not in snapshot; harness PASS log narrated, not attached), nits below. Reviewer re-ran touched specs 84/84, worker 42/42, full market-data 361/362 (the one failure the untouched `http.spec` probe, 17/17 alone), the docs cross-check and the fixture secret grep |
| security-reviewer r1 | APPROVED; 2 nits (below); fixtures and `.env.example` free of keys/headers/cookies; outbound hosts unchanged; migration and harness SQL constant; backfill and live cursors always advance |
| Publication | migrations `5831a72` → PR #3, bot `989214d` → PR #3, cross-linked; committed snapshot bound to the approved fingerprint (09:14:38Z); merged 16:51:17Z / 16:51:22Z |

### Preview acceptance (`http://127.0.0.1:51212/`, compose `forge-0199b29a-fix-xau-feed-649e2a7a`, isolated DB with retained volumes; migrations `5831a72`, bot `989214d`, service `734ce35`, web `a9459e0`; owner's Alpaca keys, OANDA pair empty)

| Check | Result | Evidence |
|---|---|---|
| Startup | passed | `collector_disabled` oanda (`missing_secrets`) → `usd_thb_proxy_in_use` reason `oanda_disabled`; `binance_th_metadata_refreshed` symbols 520, thb_symbols 11, instruments_filled 4; `instruments` row = binance-th / XAUTUSDT / "Gold spot (XAUT proxy)" / lot 0.00010; no level ≥ 50 bot events (10:04:09Z) |
| FR-MD-E2E-001 gold rows | passed | XAU/USD · Live 4,120.94 → 4,119.32; Gold 96.5 · Synthetic 66,005 → 65,682 → 65,636 without reload; GO · Closed · opens 18:50 at 4,121.3; zones and 48-bar strips present. XAU `px:last` `stale=false`, moving tick-level 4120.37 (10:07:09Z) → 4119.04 (10:08:25Z) with closed 1m bars 10:05/10:06/10:07 stored. All eight rows live/EOD at 10:09Z. (XAU read *Stale* for ~3 min after the first start: the stream opens after the last Binance TH backfill on a fresh DB.) |
| Calendar gating | passed | 180-day XAU backfill 176,641 bars; `binance_th_bar_outside_session` dropped 920 (weekend page) and 60 (daily 17:00 NY break); DB: 0 Saturday-NY bars, 0 Friday ≥ 17:00 NY bars, 0 weekday 17:00-break bars for `XAUUSD@oanda-demo` |
| Synthetics | passed | GOLD965THB 153,601 / GOLD9999USD 153,601 / GO 108,560 (TFEX sessions only) bars rebuilt to the current minute from XAU + USDTTHB |
| FR-MD-BOT-008 XAU restart gap | passed | bot killed 10:09:02Z (restart policy off), container `StartedAt` 10:21:39Z, downtime 757 s ≈ 12.6 min (the state log's earlier "47 min" was corrected at 12:55:56Z from the container timestamp); 90 s after restart, the last 60 min have 0 missing minutes for XAUUSD (session open), BTCTHB and ETHTHB; `usd_thb_proxy_in_use` and `binance_th_metadata_refreshed` logged again on restart |
| FR-MD-GOLD-001 premium row | passed | one-shot `run gold-premium-check` at 10:59Z (the scheduled 17:45 Bangkok run fell inside the kill window): GTA round 87844 (17:08 Bangkok, bar 65,550/65,750, gold_spot 4119), gta_mid 65,650.0, xau_usd 4,119.32 (XAUT), usd_thb 33.69 (binance-th-usdt), raw 65,636.22, premium_observed 13.78, premium_applied 0 (`seed`, 0 observations), synthetic 65,636.22, deviation_pct −0.0210 %, flagged false |

Logs beside the acceptance report: `preview-up.log`, `preview-live-readings.log`, `preview-restart-gap.log`, `preview-gold-premium-check.log`.

### Manual reproduction (a future preview or the owner stack)

1. Apply migrations (goose `up` reaches `20261007072235`), then restart `tidewatch-bot` with the OANDA pair empty.
2. Within a minute expect `usd_thb_proxy_in_use` (`reason: oanda_disabled`), `binance_th_metadata_refreshed` with `symbols` ≈ 520, XAU and USDTTHB 180-day backfills (260 klines calls each, under the 4,800/min limiter), `synthetic_rebuild` for GO, GOLD9999USD and GOLD965THB, and the four gold rows priced on Market watch / `/market-watch`.
3. Gating: `SELECT count(*) FROM candles WHERE instrument_id='XAUUSD@oanda-demo' AND extract(isodow FROM ts AT TIME ZONE 'America/New_York') = 6` must be 0 (Saturday New York is always outside `gold-23-5`).
4. Restart gap: stop the bot ≥ 10 min while `gold-23-5` is open, restart, and query the last 60 minutes of XAU bars for missing minutes (expect 0).
5. Premium: on a GTA publishing day, the 17:45 Bangkok check (or `run gold-premium-check`) writes a `gold_premium_checks` row with `usd_thb_source='binance-th-usdt'` and `|deviation_pct| ≤ 1`.
6. Never ask for OANDA keys; a half-filled pair exits the bot.

## Open questions

- **FU-FIX-1 (tidewatch-bot, pre-existing, recorded 12:55:56Z).** Binance TH WebSocket sessions end every ~20–60 min (reason `closed`) and sometimes go silent; the collector reconnects only after 3 min without a message, so every Binance TH-fed row (BTC, ETH, XAU and the gold synthetics) can show *Stale* for up to ~3 min before recovery (observed 12:54:46Z on the preview; the gap was backfilled, no missing bars). Consider ping/pong dead-connection detection or a shorter silence threshold. Not introduced by this fix.
- **PRD deviation record** (code-reviewer Minor 1): resolved — `prd.md` §10 now carries a dated "Deviations recorded after the build" entry and the decision history a 2026-10-07 row; the §4.1 / §4.4 / A3 text is left as written (lines 88, 132, 174, 197, 315, 897 still describe OANDA, by design). The wiki pages `market-data`, `market-data-worker` and `instrument-master` still say the gold rows have no source and FU-4 is deferred; this document is the input for that update. The market-data verification ledger gained a §10 post-fix close-out and FU-4 / OI-4 / GAP-GOLD-LIVE are marked resolved in the feature state.
- **Migrations harness PASS log** (code-reviewer Minor 2): resolved — `make check-disposable-db` was rerun in the migrations worktree before publishing and its captured log (`check-disposable-db: PASS`, 09:09–09:12Z) is at `.forge/fixes/xau-feed-binance-th/reports/migrations-check-disposable-db-rerun.log`; the bot's `sql-integration` rerun log independently proves A–D apply.
- **`usd_thb_proxy_in_use` at `warn`** is now the steady state on every start (`reason: oanda_disabled`); `info` for that reason would keep `warn` for the anomaly case. README documents `warn`; left for a follow-up.
- **Cosmetic OANDA wording left in place:** `calendars.name` for `gold-23-5` is still `Gold spot 23/5 (OANDA XAU_USD)` and the migrations README "Known gaps / OANDA hours" note still reads OANDA-sourced. The brief said the calendar is unchanged; a rename would be its own migration.
- **Public API surface** (nit): `packages/market-data/src/index.ts` now exports `inSession`, `CalendarLookup`, `PROXY_INSTRUMENT`, `UsdThbProxyReason`, `ActivateUsdThbProxyOptions` though only `activateUsdThbProxy`/`usdThbSource` are consumed by the worker; consistent with the package convention.
- **`proxyPending` ignores whether `binance-th` is enabled** (nit): with both collectors off, the proxy row is upserted and the holder switched to a source nobody feeds. Harmless (readers fall back).
- **Standby `serve` also runs the proxy upsert** before holding `runner:serve` (security nit 1): idempotent constant-row write; at most a doc note in the "One active serve" paragraph.
- **`outsideSession` entries are never pruned** when an instrument leaves `live` (security nit 2): bounded by ≤ 20 ids; at most one missing `binance_th_bar_outside_session` line later.
- **One-shot `run gold-premium-check` does not activate the proxy** (nit): `gta/premium.ts` falls back through `otherUsdThb` and still records `binance-th-usdt`; no change needed.
- **Down of D leaves data:** XAU candles and the `binance-th` cursor stay after a rollback (documented in the migration header and README).
- **Realtime cap:** with XAU (and USDTTHB) as tier-0 members, a full 20-member `top20_binance_th` list truncates its lowest-ranked members (by design, brief risk 3).
- **Session-open blip:** up to ~60 s *Stale* at each `gold-23-5` open (Sun and Mon–Thu 18:00 New York), confined to XAU.
- **Live weekend gating not yet observed on a real weekend.** The fix ran on a Wednesday; the evidence is the 180-day backfilled history (0 Saturday-NY bars, 920 + 60 dropped), the captured Friday-close and Sunday-open fixtures and the unit specs. The fix report's "after the next weekend" DB query remains a later check.
- **Premium median path not yet exercised live:** the preview row used `premium_basis 'seed'` with 0 observations; the 30-day median needs 5 prior observations.
- **`gold_premium_checks.xau_usd_source`** column: optional later follow-up (out of scope per the fix report). PAXG and any new collector are also out of scope.
- **Deployment:** verified on the Forge preview (isolated DB) only; the owner compose bring-up (FR-MD-INFRA-001) remains open from slice 1.
- **Lot size text:** stored as the venue's `0.00010`; PostgreSQL normalises it, the memory repositories keep the string.

## Cross-cutting links

- [[market-data]] — the slice-1 overview this fix amends (O1/O2/O6 gold parts, OWNER-4, FU-4, the "OANDA unavailable" known gap, the unverified XAU/USD-dependent IDs).
- [[market-data-worker]] — collectors (Binance TH metadata and gating, OANDA dormant, the USD/THB proxy at `serve` start), the "OANDA is unavailable for the owner's region" gotcha, status and staleness, recovery notes, follow-ups (FU-4 closed; FU-FIX-1 new).
- [[instrument-master]] — the `XAUUSD@oanda-demo` seed row (feed, name), the gold synthetics and premium formula, the `gold-23-5` calendar now applied as a gating rule to a venue collector.
- [[market-timeseries]] — `candles` content for XAU (no out-of-session bars), the synthetic rebuilds, `gold_premium_checks`.
- [[centralized-migrations]] — migration D after A–C, the required-schema-version contract staying at C, the phase-gated harness pattern for seed corrections.
- [[redis-market-contract]] — `px:last` for XAU (`stale`, `session`, no out-of-session prints).
- [[forge-preview-gateway]] — the preview the acceptance ran through.
