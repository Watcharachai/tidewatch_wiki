# Instrument master, universes and calendars

**Summary**: The reference model every price, and later every signal, resolves to: `SYMBOL@venue` instrument ids with aliases, a per-instrument feed, base timeframe and daily source, synthetic gold instruments, weekly-refreshed universe lists, and trading calendars with yearly exception lists. Shipped in migrations A and C of slice 1. Migration D (2026-10-07) repointed `XAUUSD@oanda-demo` from OANDA to Binance TH `XAUTUSDT` without changing its id, venue, calendar or quote (see [[gold-feed-xaut-proxy]]). Since signals-ingest (slice 3a, 2026-10-11), `instrument_aliases` is read for the first time. CIKs, exchange tags, tickers and names resolve documents to `SYMBOL@venue` ids, and a daily SEC refresh upserts CIK aliases (see [[source-registry-and-ingest]]). Since charting (slice 5, merged 2026-10-16, not deployed), `base_timeframe` also decides which timeframes the Chart offers: a daily-base instrument gets 1D only. Since bots (slice 6, merged 2026-10-21, not deployed), bots read this model too: a bot's universe resolves from the universe lists and the watchlist into four asset classes, and the bot writes `realtime_requested_at` when its scout proposes an instrument off the watchlist.

**Sources**: `raw/2026-10-07-market-data.md`; `raw/2026-10-07-fix-xau-feed-binance-th.md`; `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-16-charting.md` (the chart's use of `base_timeframe` and the instrument errors); `raw/2026-10-21-bots.md` (bot classes, universes and realtime requests only); `raw/2026-10-30-signals-context.md` (GDELT name matching and earnings ticker matching only)

**Last updated**: 2026-10-31

---

## Instrument identity

- The id is `SYMBOL@venue`, enforced by a CHECK that `instrument_id = symbol || '@' || venue_id`. Examples: `NVDA@webull`, `BTCTHB@binance-th`, `GOLD965THB@mts`.
- `instruments` also carries `feed`, `feed_symbol`, `synthetic_formula`, `base_timeframe` (`1m`, `5m` or `1d`), `daily_source` (`aggregate` or `eod`), `realtime_requested_at` and `intraday_from`, plus an `active` flag.
- `instrument_aliases` holds `ticker`, `name`, `cik`, `isin` and `thai_name` aliases. Its index on `lower(alias)` is the only index in migration A beyond the keys.
- Clients URL-encode ids (`%40` for `@`). An encoded `/` is a 404, and a malformed or unknown path id is `404 unknown_instrument`.
- In the service, `internal/market` is a pure leaf package with ids, timeframes, zones, the venue label, the default eight, exact decimals and the `px:*` v1 shapes.

(source: raw/2026-10-07-market-data.md §Database, Migration A; §API, New error codes and Request rules; §Components, tidewatch-service)

Signals (slice 3) need this stable identity to resolve to, which is one reason the slice exists (source: raw/2026-10-07-market-data.md §Concept). Slice 3a uses it: see "How signals resolve to instruments" below.

## How signals resolve to instruments (slice 3a)

Before slice 3a, `instrument_aliases` was never read by alias, CIK or ISIN, and only S&P 500 members carried `cik` aliases. Signals-ingest reads it in two places (source: raw/2026-10-11-signals-ingest.md §Concept, Problem; §Cross-cutting links).

**At ingest, before any model call (§4.4)** (see [[source-registry-and-ingest]]):
1. the issuer CIK, with zero padding stripped, against `kind = 'cik'`;
2. exchange tags: `(SET: PTT)` resolves to `<SYM>.BK@webull`, and US tags such as `(NASDAQ: NVDA)` to `<SYM>@webull`;
3. `.BK` tokens, Binance pairs `…/THB` and `…/USDT` (to `@binance-th`), the SET `symbol` field and Finnhub `related`;
4. `name`/`thai_name` aliases of at least 4 characters, with word boundaries. Single-word aliases match only capitalised occurrences (R-SIG-5).

**After extraction (§4.9)** (see [[signals-pipeline]]): an extracted `ticker`, with its `exchange` deciding `.BK@webull`, `@webull` or `@binance-th`; else an exact case-insensitive `name`/`thai_name` match; else a row in `extraction_unresolved`, the SQL-only review list. A document with no resolved instrument is skipped `no_instrument`.

**Daily CIK refresh.** At 03:30 Bangkok, and at start when the last one is older than a day, the bot reads SEC's `company_tickers_exchange.json` and upserts `instrument_aliases(kind = 'cik', source = 'sec-company-tickers')` with `ON CONFLICT DO NOTHING`. Dual-class tickers map `-` to `.` (BRK-B → BRK.B). A forced refresh on the preview wrote 516 aliases.

**What this means for the master.**
- **Coverage limits resolution.** A company that is not an instrument cannot be resolved. In eval run 2, ten misses were labelled counterparties that are not Tidewatch instruments, so ORCH-18 scores resolution against the "tracked" labelled instruments.
- **A fresh database needs `run list-refresh` first.** On the preview, 109 documents were skipped `no_instrument` before it ran.
- **Thai stocks.** No SET notices are ingested, because the SET IR News API key is unavailable to an individual (spec assumption A1 was false). So slice 3a produces no Thai SET stock signals.
- **The universe limits signal volume (signals page, slice 4).** The instrument master holds 11 instruments, and 460 extraction mentions were unresolved. So filings and wires about other companies never become signals. (The preview's day held only two signals, both media rows.) Widening the instrument universe is a recorded follow-up for tidewatch-migrations and the bot's instrument master (source: raw/2026-10-12-signals-page.md §Open questions, Data and volume).
- **The Signals page's asset filter** (`us`, `th`, `crypto`, `gold`) splits signals by each instrument's `asset_class` and `calendar_id`. With the filter absent, every class is shown, fx included (source: raw/2026-10-12-signals-page.md §API, Service routes; §Cross-cutting links).

**Follow-ups.**
- `list-refresh` adding instruments does not trigger the CIK alias refresh, so new names wait up to 24 h.
- CIK aliases are stored in two forms: padded 10-digit from the lists source, and unpadded from the SEC refresh. The resolver normalises them, but the rows duplicate.
- A requeue path for `no_instrument` skips once the instrument master grows.

(source: raw/2026-10-11-signals-ingest.md §API, Named resolution, CIK alias refresh and Name resolution; §API, Jobs; §Test plan, Eval; §Concept, Spec assumption A1 and ORCH-18; §Open questions, Follow-ups)

## How GDELT mentions and earnings resolve to instruments (signals context, 2026-10-30)

Signals context (see [[signals-context]]) reads `instrument_aliases` in two more places.

- **GDELT keep gate** (see [[gdelt-gkg-ingest]]). GDELT organisation and name strings are normalised and corporate suffixes stripped. They are then matched **exactly** against `instrument_aliases` of kind `name` for **active** instruments.
  - Names under 4 characters never match.
  - Names in `context_versions.constants.ambiguous_names` never match: 35 names in v1, such as "apple", "visa" and "gas".
  - A row whose theme is a `class_tag` adds a class subject (`class:gold`, `class:crypto`) instead of an instrument.
  - The false-match rate is open (assumption A3, FR-SC-E2E-004). If more than 5 of 50 kept mentions name the wrong company, `ambiguous_names` or the gate themes are tightened as data.
- **Earnings calendar** (see [[event-calendar]]). Finnhub earnings results are filtered to master instruments by their `ticker` alias on the `webull` venue. Thai earnings are a non-goal.
- **Calendar-driven discovery** counts `sessions_ahead` on each instrument's **own** calendar. Stocks only (see [[bots-engine]]).
- **Universe size.** The GDELT figures were measured on 2026-10-27 against a **526-instrument universe with no SET names**, much wider than the 11 instruments recorded at slice 4.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 1. Keep gate, 4. Calendar and 5. Scout discovery; §Database, `context_versions`; §Measured GDELT figures; §Test plan, FR-SC-E2E-004)

## Seeded venues and instruments

Five venues: `webull`, `binance-th`, `oanda-demo`, `mts` and `tfex`. Seven calendars with 62 session rows, 10 instruments and 24 aliases (source: raw/2026-10-07-market-data.md §Database, Seeds).

| `instrument_id` | Class | Feed | Base | `daily_source` | Calendar | Default watchlist position |
|---|---|---|---|---|---|---|
| `NVDA@webull` | stock | alpaca | 1m | eod | `us-equities` | 0 |
| `AAPL@webull` | stock | alpaca | 1m | eod | `us-equities` | 1 |
| `PTT.BK@webull` | stock | yahoo | 1d | eod | `set` | 2 |
| `BTCTHB@binance-th` | crypto | binance-th | 1m | aggregate | `crypto` | 3 |
| `ETHTHB@binance-th` | crypto | binance-th | 1m | aggregate | `crypto` | 4 |
| `XAUUSD@oanda-demo` | gold | binance-th (`XAUTUSDT`) since migration D; seeded as oanda (`XAU_USD`) | 1m | aggregate | `gold-23-5` | 5 |
| `GOLD965THB@mts` | gold | synthetic (`gold965_thb`) | 1m | aggregate | `mts` | 6 |
| `GO@tfex` | gold | synthetic (`xau_usd_mid`) | 1m | aggregate | `tfex` | 7 |
| `USDTHB@oanda-demo` | fx | oanda | 1m | aggregate | `fx-24-5` | — |
| `GOLD9999USD@mts` | gold | synthetic (`xau_usd_mid`) | 1m | aggregate | `mts` | — |

(source: raw/2026-10-07-market-data.md §Database, Seeds)

At the slice-1 merge the four gold rows and `USDTHB@oanda-demo` had no price source, because OANDA is unavailable for the owner's region (FU-4; see [[market-data-worker]]) (source: raw/2026-10-07-market-data.md §Concept, Preview findings 2).

**Migration D (`20261007072235`) fixed that the same day** with a one-row UPDATE: `XAUUSD@oanda-demo` now has `feed='binance-th'`, `feed_symbol='XAUTUSDT'` and `name='Gold spot (XAUT proxy)'`. The id, `symbol`, `venue_id` `oanda-demo` (where the instrument would be paper-traded, which the PRD keeps separate from the feed, §3), `quote_ccy` `USD`, `tick_size` 0.01, calendar, base timeframe, daily source and watchlist position are unchanged; `lot_size` stays NULL in the seed and the Binance TH collector fills it with the venue's `0.00010`. The `name` alias "Gold spot" is kept, so search still matches. `USDTHB@oanda-demo` keeps `feed='oanda'` and stays inactive; USD/THB comes from an eleventh instrument, `USDTTHB@binance-th`, which the bot upserts at `serve` start (with a `ticker` alias) whenever OANDA is disabled, rather than seeding it in a migration. See [[gold-feed-xaut-proxy]] (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Database; §Concept, The correction).

## Trading rules per venue (slice 2)

Migration E added `venue_rules`, keyed `(venue_id, calendar_id)`, with six seeded rows: `webull/us-equities`, `webull/set`, `binance-th/crypto`, `oanda-demo/gold-23-5`, `tfex/tfex` (futures, multiplier 300) and `mts/mts` (manual). They hold fees, slippage, multiplier, margin and the manual flag. Values are on [[paper-trading]].

- **Intake checks against this master.** `POST /orders` checks:
  - the instrument: `unknown_instrument`, `instrument_inactive`, `instrument_not_tradable`;
  - `lot_size` and `tick_size`: 400 with those reasons;
  - whether the venue is manual (MTS).
- **Tradable list.** `GET /trade` lists `tradable_instruments`. The benchmark takes tradable classes only.
- **`XAUUSD@oanda-demo`** is paper-traded on the `oanda-demo` venue rule while priced from Binance TH `XAUTUSDT`, so no OANDA keys are needed.
- **`PTT.BK@webull`** has a `1d` base, so it is daily-only: it fills at the next SET session's open.
- **Calendars.** The service still evaluates no calendars; the bot evaluates them for fills and outcome horizons.
- **Assumption A4.** MTS hours 07:00–03:00 Bangkok are still the PRD value until the owner confirms them (same open item as A9 below).

(source: raw/2026-10-08-simulation-engine.md §Database, Seeds; §API, Intake order; §Concept, Chosen design, ORCH-11/24; §Open questions)

**Slice 2b: what the zone-transition bot reads from this master** (see [[zone-transition-bot]]):
- **Universe.** The owner's watchlist at evaluation time, tradable classes only. Manual-fill venues (MTS, such as Gold 96.5) and futures (`GO@tfex`) are excluded through config flags. Default universe: NVDA, AAPL, PTT.BK, BTC/THB, ETH/THB and XAU/USD (still labelled "OANDA demo", priced from Binance TH XAUT; see [[gold-feed-xaut-proxy]]).
- **Timeframe.** The `1d` base of PTT.BK puts it on the `1d` strip; other instruments use `1h`.
- **Quantity.** Rounded down to `lot_size`, else to the instrument's decimals (8 for US shares, 0 for SET, the lot digits for crypto).
- **Session.** The bot checks `inSession` on the instrument's calendar before acting; a closed venue defers the action.

(source: raw/2026-10-09-zone-transition-bot.md §Concept, ZB2 and ZB3; §API, Bot runtime; §Cross-cutting links)

## Base timeframe and daily source

Each instrument's `base_timeframe` is the finest timeframe it has; asking for a finer one (`1m`, `15m` or `1h` on a `1d` base) is `422 timeframe_unavailable`. `daily_source` decides whether its daily bars come from the `candles_1d` aggregate or from `candles_eod`, and no instrument gets both. Storage details are on [[market-timeseries]] (source: raw/2026-10-07-market-data.md §Concept, MD4; §Database, Migration B).

**The Chart and the base timeframe (charting, slice 5).** See [[charting]] and [[chart-read-api]].
- **The route.** `GET /instruments/{id}/chart` takes `15m`, `1h` or `1d`. `15m` or `1h` on a `1d` base is the reused `422 timeframe_unavailable`; `1m`, `5m` and `4h` are `400`. A malformed or unknown id is `404 unknown_instrument`, also on `GET /instruments/{id}/signals`. No error code was added; only the README's "When" text for the two reused codes changed.
- **The screen.** A daily-base instrument offers 1D only: *15m* and *1h* are disabled with the title *Daily bars only* (D2). The chart opens on the strip timeframe, `1h` or `1d` by base (PD1). An off-watchlist instrument opens at 1h; a daily base then answers 422, and the chart falls back to 1D with `replaceUrl` (CH-BUILD-7).
- **Identity.** The header names the instrument by its Market watch row's `display_symbol`. An off-watchlist instrument reads `GET /instruments/{id}` once, else is named by the part of the id before "@" (CH-W-2).

(source: raw/2026-10-16-charting.md §API, Conventions; §Concept, Owner decisions D2, Accepted defaults PD1, Planner reconciliations CH-W-2 and Recorded build behaviours CH-BUILD-7; §Components, The Chart screen)

## Synthetic gold instruments

- **MD2.** `GOLD9999USD@mts` is a synthetic of the XAU/USD mid. `GO@tfex` and `GOLD9999USD@mts` copy the XAU/USD bar inside their own sessions and carry no basis or dealer spread (a PRD §10 known gap).
- **Gold 96.5.** `GOLD965THB@mts` = `xau.{o,h,l,c} × usd_thb.c × 0.965 × 15.244 / 31.1035 + premium_applied(day)`.
- **MD1, the premium.** The 30-day median of `GTA mid − raw`, using earlier days only, with a seed (`GOLD965_PREMIUM_SEED_THB`) until 5 observations exist. The premium check runs at 17:45 against GTA prices and writes `gold_premium_checks`.
- Both legs are Binance TH proxies since the XAU fix: `xau_usd` is the `XAUTUSDT` 1m close (not an OANDA mid) and `usd_thb` the `USDTTHB` close, recorded in `gold_premium_checks` as `usd_thb_source='binance-th-usdt'` (there is no `xau_usd_source` column). The formula is unchanged. The first live premium row deviated −0.021 % from GTA (not flagged, `premium_basis 'seed'`); the 30-day median path still needs 5 prior observations. See [[gold-feed-xaut-proxy]].

(source: raw/2026-10-07-market-data.md §Concept, MD1, MD2 and Preview findings 2; §Components, Collectors; §Open questions, Known gaps; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Caller-visible implications; §Test plan, Preview acceptance)

## Universe lists

| `list_code` | Member bounds |
|---|---|
| `sp500` | 500–510 |
| `nasdaq100` | 100–103 |
| `set50` | 50 |
| `set100` | 100 |
| `top20_binance_th` | 5–20 |

- Tables: `instrument_list_defs`, `list_snapshots` (`accepted`, `rejected` or `failed`, with a reason; unique accepted per `(list_code, as_of)`), `instrument_lists` and `instrument_list_status`.
- Sources (MD6): Wikipedia, the Nasdaq API, SSGA and the SET site. `top20_binance_th` holds up to 20 THB pairs, but about 10 exist today (MD7).
- The bot refreshes lists weekly on Sunday 03:00 Bangkok, or on `run list-refresh`. Snapshots are validated (`count_out_of_bounds`, `source_too_old`, `churn_too_high`, `fetch_failed`, `parse_failed`), and list status is `ok`, `stale` (with `consecutive_failures` or `missed_rebalance`) or `never_fetched`.
- A US ticker grammar (`core/tickers.ts`, security F1) stops a list from creating `*.BK@webull` ids or re-homing an instrument.
- The service serves `GET /lists` and `GET /lists/{list_code}`, and `GET /instruments` can filter by `list`.
- The live `run list-refresh` transcript was not captured (O4).

(source: raw/2026-10-07-market-data.md §Database, Migration A and Seeds; §Concept, MD6 and MD7; §Components, Jobs)

**Bot universes and classes (slice 6, 2026-10-21).**
- **Classes (S2).** `stock` on the `set` calendar is `th_stock`; any other `stock` is `us_stock`; `crypto` is `crypto`; `gold` is `gold`. `fx` is never in a bot universe.
- **Resolution (PRD §4.11, service `universe.go` and bot `general/universe.ts`).** The bot version's lists and the watchlist, plus `include`, minus `exclude`; filtered to active instruments with a venue rule, not `fx`, not manual-fill and not futures; a liquidity floor over the newest 20 daily bars; plus held instruments. `GET /bots/{id}/universe` answers `{generated_at, by_class, total}`, and the editor reads "{n} instruments in the universe right now". The service's read runs a 20-bar volume subquery per member (about 570), a recorded nit.
- **Realtime requests (S12, PD8).** When the scout proposes a candidate on an instrument off the watchlist, it sets `instruments.realtime_requested_at` in the same transaction; each candidate close clears it. The subscription manager admits requested instruments after watchlist positions (see [[market-data-worker]]). FR-BT-E2E-006 (an off-watchlist US candidate made live within one manager cycle) was unverified, because the US market was closed and Binance TH subscribes every active pair anyway.

See [[bots-engine]] (source: raw/2026-10-21-bots.md §Concept, Spec decisions S2/S12 and Owner decisions PD8; §API, Behaviour worth knowing, Universe; §The bot engine, Scout and Manager; §Test plan, The E2E checks; §Open questions, Service code nits)

## Search

`GET /instruments` matches `q` (1–64 characters) as a prefix of the symbol or display symbol, or a substring of the name or any alias, `thai_name` included. Results are ordered by exact symbol match, then list membership, then symbol, and paged with an opaque `cursor`. The Add instrument dialog debounces it by 250 ms (source: raw/2026-10-07-market-data.md §API, REST; §Components, tidewatch-web Dialogs).

## Calendars

Only the bot evaluates calendars; they drive session status, staleness and the *Closed · opens …* tag. `calendar_sessions` use ISO weekdays, and `ends_at <= starts_at` means the session ends the next day (source: raw/2026-10-07-market-data.md §Database, Migration A). Since the XAU fix a venue collector also uses the instrument's calendar to decide which bars and ticks to store: the Binance TH collector gates through `calendar/in-session.ts` (`inSession(reference, instrument, at)`; an unknown calendar stores everything), the rule the synthetic engine already applied (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Components, tidewatch-bot).

| Calendar | Sessions (local time) |
|---|---|
| `us-equities` | Mon–Fri pre 04:00–09:30, regular 09:30–16:00, post 16:00–20:00; Sun–Thu overnight 20:00–04:00 (New York) |
| `set` | Mon–Fri 10:00–12:30 and 14:00–16:40 (Bangkok) |
| `tfex` | day 09:45–16:55 and night 18:50–03:00 (Bangkok) |
| `crypto` | every day 00:00–24:00 UTC |
| `gold-23-5` | Sun–Thu 18:00–17:00 (New York). Since the XAU fix also a gating rule: Binance TH XAU bars and ticks outside it are dropped, although XAUT itself trades continuously. `calendars.name` still reads `Gold spot 23/5 (OANDA XAU_USD)` (a rename would be its own migration) |
| `fx-24-5` | Sun–Thu 17:00–17:00 (New York) |
| `mts` | Mon–Fri 07:00–03:00 (Bangkok) (MD3) |

(source: raw/2026-10-07-market-data.md §Database, Calendars)

**Exceptions (migration C).** 99 rows: `us-equities` 10 closed days and 2 early closes (13:00 New York) in 2026 and 10 and 1 in 2027; `set` 20 and 18 closed days; `tfex` the same list as SET's. `valid_through` is `2027-12-31` for those three and NULL for `crypto`, `gold-23-5`, `fx-24-5` and `mts`, meaning no published list and so no coverage claim. Migration C's header cites 21 sources with SHA-256 hashes (A4) (source: raw/2026-10-07-market-data.md §Database, Migration C; §Concept, A4).

**Renewal rule.** The bot logs `calendar_exceptions_expiring` from 2027-11-02. Next year's list ships as a new migration, never as an edit of C, and a wrong calendar row is fixed forward the same way (see [[centralized-migrations]]) (source: raw/2026-10-07-market-data.md §Database, Migration C and Down migrations; §Components, Recovery notes).

**Deviations and open decisions.**
- DEV-A4-SET: the SET afternoon session is seeded from 14:00, not the PRD's 14:30, because SET opens at a random time between 13:55 and 14:00.
- A9 (MTS hours 07:00–03:00) is pending owner review; the official pages say only "24 hours".
- A10 (Webull overnight Sun–Thu 20:00–04:00 ET) is settled, but Webull's overnight session has no data, so the overnight session is always stale while open.

(source: raw/2026-10-07-market-data.md §Concept, Assumptions and Accepted PRD deviations; §Components, Status publisher)

**Known calendar gaps.** The NYSE early-close late session (to 17:00 ET) is not encoded, so post and overnight are dropped after a 13:00 early close. TFEX holiday-eve night sessions are not encoded. OANDA's daily 16:59–17:05 break is not modelled in `fx-24-5`, so FX rows can read stale for about 4 minutes a day (moot while the OANDA collector is dormant; XAU on `gold-23-5` instead shows up to ~60 s Stale at each session open, see [[gold-feed-xaut-proxy]]) (source: raw/2026-10-07-market-data.md §Open questions, Known gaps; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, Caller-visible implications).

## Related pages

- [[market-data]] — the slice overview, REST routes and watchlist
- [[market-timeseries]] — where each instrument's bars and indicators are stored
- [[market-data-worker]] — the collectors, list job and calendar-driven status
- [[gold-feed-xaut-proxy]] — why `XAUUSD@oanda-demo` is fed by Binance TH XAUT and how `gold-23-5` gates it
- [[centralized-migrations]] — migrations A, C and D and the fix-forward rule
- [[paper-trading]] — `venue_rules`, and the intake checks on tick, lot and tradability
- [[zone-transition-bot]] — the auto bot whose universe, timeframe and quantity come from this master
- [[source-registry-and-ingest]] — named resolution at ingest and the daily CIK refresh
- [[signals-pipeline]] — name resolution after extraction, and the `no_instrument` skip
- [[signals-page]] — slice 4, whose signal volume the 11-instrument universe limits
- [[charting]] — slice 5, which offers a daily-base instrument 1D only
- [[chart-read-api]] — the chart route's timeframe checks and reused instrument errors
- [[bots-engine]] — bot classes, universes and the scout's realtime requests
- [[gdelt-gkg-ingest]] — GDELT names matched against `name` aliases, and `ambiguous_names`
- [[event-calendar]] — earnings matched by `ticker` alias on `webull`
