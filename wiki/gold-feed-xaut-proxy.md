# Gold feed: the Binance TH XAUT proxy

**Summary**: Since 2026-10-07, `XAUUSD@oanda-demo` is priced from the Binance TH `XAUTUSDT` pair (Tether Gold, 1 token = 1 troy ounce) through the Binance TH collector, because the owner's OANDA account can never reach the v20 API. The instrument id, venue, `gold-23-5` calendar, USD quote and 0.01 tick are unchanged; Binance TH bars and ticks are gated by the instrument's own calendar, and the `USDTTHB` USD/THB proxy is activated at `serve` start whenever OANDA is disabled. This closed the slice-1 gap FU-4 (with OI-4 and GAP-GOLD-LIVE) through migration D and tidewatch-bot PR #3.

**Sources**: `raw/2026-10-07-fix-xau-feed-binance-th.md`

**Last updated**: 2026-10-08

---

## Why the gold rows had no price

At the end of slice 1 the four gold rows (`XAUUSD@oanda-demo`, `GOLD965THB@mts`, `GO@tfex`, `GOLD9999USD@mts`) read *Stale* with no price. The PRD's XAU/USD feed was the OANDA practice v20 API, but the owner's account is Thai-region OANDA Global Markets (MT5 only), which OANDA's v20 docs exclude, so `OANDA_DEMO_TOKEN` and `OANDA_DEMO_ACCOUNT_ID` can never exist (OWNER-4 on [[market-data]]). The owner deferred the replacement as FU-4 on 2026-10-07 and chose Binance TH tokenized gold, XAUT first, the same day (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, The bug).

The diagnosis (confidence `confirmed`, scope `corrective`) traced the chain: the seed row had `feed='oanda'`; without keys the OANDA collector is disabled, so XAU got neither backfill nor live bars; the synthetic engine starved, the premium check skipped with `missing: ['xau_usd']`, and staleness marked the synthetics `component_stale`. Two things blocked a simple repoint. The Binance TH collector's `refreshMetadata` kept only THB-quoted symbols, so a USDT-quoted feed symbol was never `TRADING` in `symbolStatus` and was never subscribed (`binance_th_symbol_not_trading`). And the `USDTTHB@binance-th` USD/THB proxy was created, and the process-wide USD/THB holder switched, only inside the OANDA collector's `useProxy()`, which runs after a successful OANDA startup check and so never runs without keys, leaving `GOLD965THB` judged on the dead `USDTHB@oanda-demo` (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Confirmed root cause).

## The correction

1. **Feed symbol `XAUTUSDT`** on Binance TH. `PAXGUSDT` is the documented alternative; both are listed `TRADING` on `api.binance.th` with tick 0.01 and lot 0.0001, and share Binance global's order book.
2. **Instrument id stays `XAUUSD@oanda-demo`.** Venue is where the instrument would be paper-traded (the owner's OANDA MT5 demo); feed is where the price comes from, and the PRD separates the two (§3). The service's default watchlist, the web, the Redis keys and every id-keyed consumer therefore needed no change. `name` becomes `Gold spot (XAUT proxy)`; `quote_ccy` stays `USD` (USDT ≈ USD, the same convention as the USDTTHB proxy).
3. **The `gold-23-5` calendar is kept and applied as a gate.** XAUT trades through Saturday and Sunday almost flat (1m-return sd 0.005 % against 0.03 % on weekdays). Without gating, every Monday's 48-bar tide strip would carry about 48 flat weekend bars and the CDC zone would stop matching a gold chart. Live and backfill paths skip bars whose `ts` is outside the instrument's calendar session, the rule the synthetic engine already applied; ticks are gated with the bars so `px:last` carries no out-of-session prints. Outside the session XAU reads *Closed · opens …*, never *Stale*; no status rule changed.
4. **USD/THB proxy at `serve` start.** `USDTHB@oanda-demo` keeps `feed='oanda'` and stays inactive. Because of the second root-cause link, the bot now activates the `USDTTHB@binance-th` proxy at `serve` start whenever `'oanda'` is not in the enabled collector set, logging `usd_thb_proxy_in_use` with `reason: 'oanda_disabled'`. The helper lives in `core/usd-thb-source.ts` and the OANDA collector calls the same helper with `reason: 'usd_thb_unavailable'`. A code route was chosen over seeding the proxy row in the migration so the proxy's creation stays in one place.
5. **The OANDA collector stays in the tree, dormant.** It still works if a v20 account ever appears. Both OANDA lines in the secrets file stay empty (a half-filled pair exits the bot); the owner is never asked for OANDA keys.

(source: raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, The correction)

## Why XAUT

Evidence gathered on 2026-10-07 from the owner's network: `XAUTUSDT` and `PAXGUSDT` are `TRADING` in Binance TH `exchangeInfo`, `nbstream.binance.th` streams `xautusdt@kline_1m`, and 120 minutes of REST 1m klines had 0 gaps. Over 7 days of 1m closes (7,002 overlapping minutes) the XAUT / COMEX `GC=F` ratio had sd 0.057 % (PAXG 0.058 %; the −0.66 % mean is the futures basis). Against GTA's own `goldSpot` XAUT was −0.085 % and PAXG +0.037 %, inside the 1 % GTA tolerance; the 30-day premium median absorbs any steady offset. Liquidity over 24 h: XAUT 48k trades / $20.6M, PAXG 26k / $12.2M. Rejected: Deriv (HTTP 520 from this network), Finnhub (forex candles 403 on free), Massive/Polygon (EOD only), Twelve Data (REST-only free tier; noted as a viable fallback), Yahoo `GC=F` (futures, unofficial), goldapi.io / API Ninjas / supapongai (quotes only or paid) (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Why XAUT).

## What shipped

- **Migration D**, `20261007072235_market_xau_feed_binance_th.sql`: a one-row `UPDATE instruments SET feed='binance-th', feed_symbol='XAUTUSDT', name='Gold spot (XAUT proxy)', updated_at=now()` for `XAUUSD@oanda-demo`, with a Down that restores `oanda` / `XAU_USD` / `Gold spot`. Data only; existing CHECKs already allowed the values; the required schema version stays C. Details on [[centralized-migrations]].
- **Binance TH collector.** `refreshMetadata` indexes every `exchangeInfo` symbol (the THB subset is kept for the "no THB symbols listed" guard and the `top20_binance_th` list job) and fills NULL sizes by feed symbol, so XAU's `lot_size` becomes the venue's `0.00010`. `wantedStreams` stays feed-based, so widening the index cannot subscribe a symbol that has no `feed='binance-th'` row. Backfill and live paths gate through the new `calendar/in-session.ts` (`inSession(reference, instrument, at)` over the existing `isOpen`; unknown calendar → `true`). The backfill filters after `closed` is computed and keeps the cursor from the unfiltered rows, so a window wholly inside a weekend still advances the cursor and is never re-fetched; the live path drops the tick, the price observation and the bar but still advances the cursor. `binance_th_bar_outside_session` is logged once per gap on the stream and with a `dropped` count per backfill window.
- **`core/usd-thb-source.ts`** holds `PROXY_INSTRUMENT` (`USDTTHB@binance-th`, moved from the OANDA collector) and `activateUsdThbProxy(...)`: an idempotent upsert of the instrument and its `ticker` alias (`WHERE … IS DISTINCT FROM`, sizes and `active` coalesced, so it cannot wipe collector-filled sizes or reactivate an owner-deactivated row), a reference refresh, the holder switch and the log line. `serve.ts` runs `ensureUsdThbProxy()` after the first `refreshReference()` and before the standby and runner loops start, so the synthetic engine initialises with the proxy as its USD/THB source; a failure logs `usd_thb_proxy_failed` and is retried on each 60 s reference refresh.
- **Fixtures** captured from the owner's network without a key: `exchange-info-xautusdt.json`, `klines-xautusdt-1m.json` (around the Friday 17:00 New York close), `klines-xautusdt-1m-sunday-open.json` and `ws-session-xautusdt.ndjson`. The captures show the regime change plainly (minute volume 15.97 → 1.79 at the Friday close, 0.756 → 63.26 at the Sunday open).
- **tidewatch-service and tidewatch-web are unchanged.** The service keeps `XAUUSD@oanda-demo` as a default watchlist id and `/ready` checks C's `is_applied` by version, tolerant of a newer D; the web keys the status tag on mode, stale, session and `next_open_at` only.

Merged on 2026-10-07: tidewatch-migrations #3 (merge `a2e7f81`, 16:51:17Z) and tidewatch-bot #3 (merge `a420767`, 16:51:22Z) (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Database; §Components; §Test plan, Results recorded).

## Caller-visible behaviour

- **Market watch.** The XAU/USD row is *Live* (feed `binance-th` → mode `live`), named "Gold spot (XAUT proxy)" with the venue label still "OANDA demo". `GO`, `GOLD9999USD` and `GOLD965THB` are *Synthetic* inside their own sessions and *Closed · opens …* outside.
- **Expected blips.** Up to ~60 s *Stale* at each `gold-23-5` open (Sun and Mon–Thu 18:00 New York), because Binance TH staleness is judged on closed bars and the first in-session kline closes a minute after the open; confined to XAU, since the synthetics on `mts` and `tfex` are closed at 05:00 Bangkok. After a fresh-DB first start XAU showed *Stale* for ~3 min because the Binance TH collector opens its stream only after every instrument's backfill (pre-existing first-start behaviour).
- **Stored data.** No XAU bars on Saturday New York, after the Friday 17:00 close or in the weekday 17:00–18:00 break; the cursor still advances across gated minutes, so a restart during a gap resumes after it (see [[market-timeseries]]). `px:last` for XAU carries no out-of-session prints (see [[redis-market-contract]]).
- **Premium check.** `xau_usd` in `gold_premium_checks` is now an XAUT/USDT 1m close rather than an OANDA mid; `usd_thb_source` is `binance-th-usdt`. The table has no `xau_usd_source` column (an optional later follow-up). The formula on [[instrument-master]] is unchanged.
- **Subscriptions.** XAU/USD joins the Binance TH realtime set as a tier-0 component (and USDTTHB once the holder names the proxy), so the 20-instrument cap holds one fewer low-ranked `top20_binance_th` member, by design.
- **Operators.** Every `serve` start without OANDA logs `usd_thb_proxy_in_use` (`reason: 'oanda_disabled'`, at `warn`). New events `binance_th_bar_outside_session` (info) and `usd_thb_proxy_failed`; `binance_th_metadata_refreshed` gains `symbols` (520 at capture, 11 THB, 383 USDT). The bot README logs table went from 169 to 171 rows.
- **Compatibility.** A running bot picks the migrated row up within 60 s through the reference cache, but a restart after `migrate` is recommended so the proxy activation and the 180-day XAU and USDTTHB backfills are logged. Old bot + new row only logs `binance_th_symbol_not_trading`; new bot + old row is a no-op.

(source: raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Caller-visible implications)

## Verified on the Forge preview (2026-10-07)

| Check | Result |
|---|---|
| Startup | `collector_disabled` oanda (`missing_secrets`) → `usd_thb_proxy_in_use` reason `oanda_disabled`; `binance_th_metadata_refreshed` symbols 520, thb_symbols 11, instruments_filled 4; `instruments` row = binance-th / XAUTUSDT / "Gold spot (XAUT proxy)" / lot 0.00010 |
| FR-MD-E2E-001 gold rows | XAU/USD *Live* 4,120.94 → 4,119.32; Gold 96.5 *Synthetic* 66,005 → 65,636 without reload; GO *Closed · opens 18:50*; all eight rows live, EOD or synthetic |
| Calendar gating | 180-day XAU backfill 176,641 bars; `binance_th_bar_outside_session` dropped 920 (weekend page) and 60 (daily 17:00 New York break); 0 Saturday-NY, 0 Friday ≥ 17:00 NY and 0 weekday-break XAU bars in the DB |
| Synthetics | GOLD965THB 153,601 / GOLD9999USD 153,601 / GO 108,560 (TFEX sessions only) bars rebuilt to the current minute from XAU + USDTTHB |
| FR-MD-BOT-008 restart gap | 12.6 min (757 s) downtime → 0 missing minutes in the last 60 for XAUUSD, BTCTHB and ETHTHB; proxy activation and metadata refresh logged again on restart |
| FR-MD-GOLD-001 premium row | one-shot `run gold-premium-check`: GTA round 87844, gta_mid 65,650.0, `xau_usd` 4,119.32 (XAUT), `usd_thb` 33.69 (binance-th-usdt), raw 65,636.22, premium_applied 0 (`seed`, 0 observations), deviation −0.021 %, flagged false |

Build checks: `make check-disposable-db` printed `check-disposable-db: PASS` (649 PASS / 0 FAIL); bot `pnpm nx run-many -t lint test typecheck build` green (market-data 362/362, worker 42/42, shared 56/56, indicators 22/22); `scripts/sql-integration.sh` PASS against A–D; docs cross-check 171 code events = 171 README rows; code-reviewer and security-reviewer approved at r1 with nits only (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Test plan, Results recorded and Preview acceptance).

## Open items after the fix

- **FU-FIX-1 (tidewatch-bot, pre-existing).** Binance TH WebSocket sessions end every ~20–60 min and sometimes go silent; the collector reconnects only after 3 min without a message, so every Binance TH-fed row (BTC, ETH, XAU and the gold synthetics) can show *Stale* for up to ~3 min before recovery (observed on the preview; the gap was backfilled, no bars missing). Consider ping/pong dead-connection detection or a shorter silence threshold. Not introduced by this fix.
- **Nits deferred.** `usd_thb_proxy_in_use` is logged at `warn` though `reason: 'oanda_disabled'` is now the steady state (`info` for that reason would keep `warn` for the anomaly case); `calendars.name` for `gold-23-5` still reads `Gold spot 23/5 (OANDA XAU_USD)` and the migrations README's OANDA-hours note still reads OANDA-sourced (a rename would be its own migration).
- **Not yet observed live.** Weekend gating on a real weekend (the fix ran on a Wednesday; the evidence is the 180-day backfilled history, the captured Friday-close and Sunday-open fixtures and the unit specs) and the 30-day premium median path (the preview row used `premium_basis 'seed'`; the median needs 5 prior observations).
- **Down of D leaves data.** XAU candles and the `binance-th` cursor stay after a rollback.
- **Scope left out.** PAXG, any new collector and a `gold_premium_checks.xau_usd_source` column. The owner compose bring-up (FR-MD-INFRA-001) remains open from slice 1.
- **Already recorded elsewhere.** The PRD deviation is in `tidewatch-specs/market-data/prd.md` §10 ("Deviations recorded after the build", with a decision-history row; the §4.1, §4.4 and A3 text is left as written by design), and the market-data verification ledger has a §10 post-fix close-out. FU-4, OI-4 and GAP-GOLD-LIVE are marked resolved in the feature state.

(source: raw/2026-10-07-fix-xau-feed-binance-th.md §Open questions)

## Related pages

- [[market-data]] — the slice-1 overview this fix amends (O1/O2/O6 gold parts, OWNER-4, FU-4)
- [[market-data-worker]] — the Binance TH and OANDA collectors, status and staleness, recovery notes and follow-ups
- [[instrument-master]] — the `XAUUSD@oanda-demo` row, the gold synthetics and the `gold-23-5` calendar now used as a gate
- [[market-timeseries]] — XAU bars in `candles`, the synthetic rebuilds and `gold_premium_checks`
- [[centralized-migrations]] — migration D and the required-schema-version contract staying at C
- [[redis-market-contract]] — `px:last` for XAU: no out-of-session prints
- [[forge-preview-gateway]] — the preview the acceptance ran through
