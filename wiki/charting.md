# Charting (`charting`, slice 5)

**Summary**: Before slice 5, the Chart rail entry, the Signals page's instrument chips and its *Open chart* button all opened a slice-0 placeholder, and the Signals detail's *Elliott* and *Regime* lines read "Arrives with Charting". Slice 5 gave Tidewatch its chart. `/chart/:instrument_id` draws candles at 15m, 1h or 1D (no 4h), each coloured by the stored `indicators.cdc_zone` of its own bucket. It adds EMA 12/26, at most two Elliott candidate counts with a *fit* and an invalidation level, the instrument's signals as markers, Fibonacci levels when switched on, a 96-bar tide strip and the TradingView attribution. A right column (*Right now*, *Elliott, candidate counts*, *Signals on this chart*) repeats the facts as text. Closed 1m bars from `/ws` extend the forming bar without re-reading history, a new signal becomes a marker, and nothing moves the view the owner set. The service gained a pure, exact Go labeller (see [[elliott-regime-labeller]]), two gated read routes (see [[chart-read-api]] and [[signals-read-api]]), and `elliott` and `regime` on the signal detail's `context`. The web gained the Chart screen on `lightweight-charts` 5.2.1, a 96-slot strip mode, the Market watch symbol as a link, a two-key Trade pre-fill and filled Signals detail rows. There is no migration and no bot change. **Status:** implemented, verified locally and reviewed. On a preview every FR-CH ID passed except **FR-CH-E2E-003, which is partial** by owner decision CH-BD-3. Merged on 2026-10-16: tidewatch-service #11 as `1547a89` and tidewatch-web #14 as `918d7b6`. **Not deployed.**

**Sources**: `raw/2026-10-16-charting.md`; `raw/2026-10-27-statistics.md` (the deferred champion stance only)

**Last updated**: 2026-10-27

---

## Stage, stated precisely

This is the status in `state.json` as last updated at 2026-10-16T03:21:59Z (source: raw/2026-10-16-charting.md §Concept, Stage, stated precisely).

| Stage | Status |
|---|---|
| Implemented | **Service:** S1–S5, plus the review fix RF1 `51e40c2` (a one-line nil receiver). **Web:** S1–S11; review fixes r1 (`4f89b24`, `16807ba`) and r2 (`4caaacb`, `4d8de59`); preview fixes PF1 (`5476985`, plus the lint fix `6bc61c8`) and PF2 (`487bac1`, `91bdc07`); and the PV4 docs commit `3ebce40` (`DESIGN.md` only). |
| Verified locally | Every step's contract commands were re-run and exited 0. **Service:** `go vet` (both tags), `gofmt`, `go test ./... -race -count=1`, `make build`, and `make test-integration` with no `--- SKIP`. One S4 integration run failed on the unrelated `TestPassword_RateLimitAndLockout`, when a sessions lookup hit its deadline under host load; the re-run passed. **Web, final at `91bdc07`:** 3,932 unit tests in the host zone and again under `TZ=America/New_York`, lint with 0 problems, the build, e2e lint and type-check, the SSR smoke, `lib-imports`, and the colour, clock, motion, `HttpClient` and `innerHTML` guards. |
| Reviewed | **Plans:** service r1 changes requested, then r2 approved; web r1 changes requested, r2 approved, then a narrow r3 amendment approved. **Code:** service r1 and r2 approved; web r1 changes requested (code and design), then r2–r5 approved. |
| Verified on a preview | Yes, except **FR-CH-E2E-003, partial** (CH-BD-3). The final rounds ran on web `91bdc07` with service `51e40c2`: PV1 r3, PV2 r2, the PV3 r2 rendered design review (approved) and the A5 EXPLAIN. Touch scroll at ≤ 600 px was never checked. |
| Merged | **Yes**, 2026-10-16, as merge commits: tidewatch-service #11 (head `51e40c2` → `1547a89`, 03:21:39Z), then tidewatch-web #14 (head `3ebce40` → `918d7b6`, 03:21:47Z). The owner's instruction in chat at 2026-10-15T18:53:22Z: "if done please merge PR and continue". Neither repository has CI. |
| Deployed | **No.** No migration, environment or bot step is needed. Deploy the service before the web. |
| Documentation pass | The raw source and this wiki update. The API-collection regeneration was skipped, because the service README documents the routes. |

**Bookkeeping drift.** `verification.md` was written before the merge and reads "Merged: not yet". The Charting entry in the web `DESIGN.md` was written at PV4, also before the merge, and says "not merged". The merge facts come from `state.json` (`perProject.*.mergedAt`, `mergeCommit`) (source: raw/2026-10-16-charting.md, Sources (inputs to this document)).

## Merge record

| Repo | PR | Range (base..PR head) | Merge commit | Files |
|---|---|---|---|---|
| tidewatch-service | #11 | `8b18486..51e40c2` | `1547a89` | 43: the 42 planned, plus one recorded test-only S4 extra |
| tidewatch-web | #14 | `976233f..3ebce40` | `918d7b6` | 87 committed paths: 36 created, 51 modified |

**Not changed:** `tidewatch-migrations`; `tidewatch-bot` (its indicator job, contracts, fixtures and C-SIG-1 reader list); compose, workspace-root files and `.env.example`; and on the web `tokens.css`, `theme.css`, `icons.ts`, `zone.css`, `table.css`, `watch-view.ts`, `bangkok-time.ts`, `market-stream.service.ts` and `signals-api.service.ts` (source: raw/2026-10-16-charting.md §Files touched).

## Why the slice exists

The owner trades with CDC Action Zone and is learning Elliott Wave. Before this slice, zones appeared only as the 48-cell tide strip and a zone label on Market watch. A signal's market context appeared only as words in the Signals expanded row. No screen showed candles, zones, waves and signals together against the price. The roadmap's slice-5 exit test is: "the chart agrees with Market watch on zone and price; Elliott candidates never violate the three hard rules; markers link to signals."

The starting state, verified at `origin/main` on 2026-10-14 (web `976233f`, service `8b18486`, bot `ece175a`, migrations at I):
- **Bars.** `candles` (1m, 180-day retention), the aggregates `candles_15m`, `candles_1h` and `candles_1d`, and the `candles_daily` view. There was no 4h bar and no 4h indicator row (see [[market-timeseries]]).
- **Indicators.** One `indicators` row per closed 15m, 1h and 1d bucket within 60 s.
- **Realtime.** `/ws` already forwarded `tick`, `bar` (closed 1m bars, whose `o,h,l,c,v` the web tolerated but did not read), `zone` (strip timeframe only), `status` and `signal`.
- **Signals.** `GET /signals` was bound to one day and had no instrument filter.
- **Web.** The Chart placeholder was registered on `/chart` and `/chart/:instrument_id`. `app-tide-strip` always drew 48 slots. The Trade pre-fill needed all four keys.

(source: raw/2026-10-16-charting.md §Concept, Problem)

## Outcomes and their result

| # | Outcome | Result |
|---|---|---|
| O1 | Zone-true chart: every drawn bar's colour is its bucket's stored `cdc_zone`; on open, *Right now*, the strip's last cell and Market watch agree | **Met** (SVC-001/002, WEB-001/002/003, E2E-001, E2E-004) |
| O2 | Honest Elliott: at most two candidates, each with fit and invalidation, none breaking R1–R3, and *Candidate counts are not forecasts.* always shown | **Met** (SVC-003/004, WEB-005, E2E-005) |
| O3 | Signals in context: markers, the *Signals on this chart* list, highlight, links to the Signals day, filled detail rows | **Met at route, component and mocked-browser level.** The live drawing of a stored new signal (E2E-003) is partial |
| O4 | Live: a closed bar extends the chart without a history read, a new signal is a marker within 2 s, ticks move the last price, nothing moves the view | **Met except one leg.** WEB-008 and E2E-002 passed; E2E-003 is partial |
| O5 | Usable everywhere: both themes, no horizontal scroll at 390/600/1080/1100/1440, keyboard reach, 1,000 bars under 100 ms, the attribution | **Met** (WEB-009…014). Touch scroll is unverified, and design W5/W6 are open |

(source: raw/2026-10-16-charting.md §Concept, Outcomes (intent) and their result)

## Owner decisions (intent, 2026-10-14)

The interview ran in chat with the `grilling` skill, because the Forge Console Spec studio has no display in the desktop Code tab. The owner replied "confirmed" to the whole intent, and each decision is the recommended option.

- **D1. Chart engine: Lightweight Charts.** Pan, zoom, crosshair, per-bar colours, markers and plugin primitives come with it. Rejected: an in-house SVG chart, which would roughly double the web work. Costs accepted: a dependency, canvas accessibility work, runtime colours from the tokens, browser-only creation and the attribution link. Overview's own "no chart library" decision still stands for Overview.
- **D2. Timeframes 15m, 1h and 1D; 4h deferred.** A daily-base instrument offers 1D only. Computing 4h on read was rejected, because it would be a second CDC implementation whose zones are not stored rows. Doing 4h properly touches migrations, bot, service and web.
- **D3. The service computes Elliott and regime on read,** in one deterministic Go implementation that serves both the chart and the Signals detail. Slice 6's bot ports it against the same committed fixtures. A web-only labeller was rejected, because it would leave the Signals lines unfilled.
- **D4. Fixtures whose answers are known by construction:** three synthetic series built from chosen pivots, plus two real captured series checked only against the hard rules and the invalidation rule. Owner hand-labelling was rejected, because it would block planning or gate acceptance on owner work.
- **D5. Impulse and corrective candidates, the top two by fit.** The number is called *fit*, never probability.
- **D6. A spec mockup on the real tokens** (`mockup.html`), browser-verified at five widths in both themes, is the visual target.

**Accepted defaults (PD1–PD13), abridged.**
- The chart opens on the strip timeframe: 1h, or 1D for a daily base (PD1).
- `/chart` opens the first watchlist instrument. A native *Instrument* select sits in the title, and `[`/`]` step through it (PD2).
- The Market watch symbol links to its chart (PD3).
- The forming bar has no zone until its row lands. A daily EOD instrument has no live bar (PD4).
- The first read is the last 1,000 bars. Scrolling left loads earlier bars, up to the 180-day intraday retention (PD5).
- The shared strip runs at 96 slots (PD6).
- The zigzag thresholds (15m 1.2 %, 1h 2.5 %, 1D 6 %) and the regime constants are tunables (PD7).
- The stance line is Slack Water's latest watch verdict, in the Bots words (PD8).
- Markers come from an instrument-scoped read, and items link to the Signals page on their Bangkok day (PD9).
- *Buy* and *Sell* pre-fill the instrument and side only (PD10).
- Fibonacci is off by default (PD11).
- No new colour, and Elliott is drawn in `--brand` (PD12).
- Both themes, nothing animates, every width from 390 (PD13).

**Spec-level decisions (S1–S14), selected.**
- One chart route returns bars already LEFT JOINed with their indicator rows (S1).
- Pivots use closes only (S2).
- The regime is on the chart timeframe for the chart, and on the strip timeframe for a signal (S5).
- The stance comes from `bot_watch`, and the route never creates a bot (S7).
- The web re-reads the head with `limit=8` 65 s after a bucket closes, again at 180 s if there is still no zone, and at once on a `zone` frame (S8).
- `lightweight-charts` is pinned at exactly 5.2.1, with `attributionLogo` on (S9).
- Colours come from the computed tokens and are re-read on a theme change (S10).
- One focusable `role="img"` wrapper has its own keys (S11).
- The store is keyed on the route parameter (S13).
- A timeframe switch keeps the centre instant and the visible bar count (S14).

(source: raw/2026-10-16-charting.md §Concept, Owner decisions (intent, 2026-10-14; each the recommended option))

## Decisions taken during the build

**Owner decisions (`planning/owner-decisions.md`, each the recommended option).**

| ID | When (UTC) | Decision |
|---|---|---|
| CH-OD-1 | 2026-10-14T18:34:40Z | **The analysis window is always the newest 1,000 bars.** A head read computes `right_now`, `elliott` and the regime over the closed bars among the newest 1,000 it read, whatever `limit` is. So the web's `limit=8` re-read returns the same overlays as a full read (see [[chart-read-api]]). |
| CH-OD-2 | 2026-10-14T18:34:40Z | **The PRD gap fills are accepted as a set** and pinned by the fixtures. A later change is a fixture and contract change (see [[elliott-regime-labeller]]). |
| CH-OD-3 | 2026-10-15T02:09:17Z | **`/chart` keeps client rendering.** The screen is SSR-safe: the library loads and the chart is created only in `afterNextRender`. FR-CH-WEB-014's SSR clause is verified by a built-server smoke (200, the app shell, no `<canvas>`, no error). The intent's "SSR renders the page" is read as "SSR-safe" for authenticated routes. |
| CH-OD-4 | 2026-10-15T02:09:17Z | **Every price and indicator value goes through the shipped digit-wise `formatPrice(value, tick_size)`,** including EMA, ATR, the tooltip and the levels. `fit` is shown as sent. |
| CH-OD-5 | 2026-10-15T02:09:17Z | **Activating a *Signals on this chart* item is link navigation only.** Hover or focus highlights its marker. The chart moves the visible range on its own only on the S14 timeframe switch. This supersedes PRD §4.3's "item's activation" clause. |

**Build decisions (`planning/build-decisions.md`; CH-BD-4 is in `state.json`).**

| ID | When (UTC) | Decision |
|---|---|---|
| CH-BD-1 | 2026-10-15T12:47:33Z | The header's 24h change ships as plain text with no up/down tone, because the shared `PageHeader` `sub` is string-only and `page-header.ts` was a pinned, unchanged source. Follow-up: an optional projected sub line on `PageHeader`. |
| CH-BD-2 | 2026-10-16T01:59:28Z | The candle series' last-value label carries the instrument symbol as a title (for example "NVDA 217.15"), so it is told apart from EMA 26's label. No new colour or token. |
| CH-BD-3 | 2026-10-16T02:24:00Z | **FR-CH-E2E-003 is accepted as partial, and the merge goes ahead.** Proven: the live frame → signals re-read leg on the preview (+81 ms), and drawing within 2 s on the mocked `chart-live.spec.ts`. The real end-to-end is to be checked on the first real signal after merge. |
| CH-BD-4 | 2026-10-16T02:57:40Z | PV3 r2's non-blocking W5 and W6 are recorded as follow-ups rather than taking another fix and preview cycle. The orchestrator decided this under the owner's "if done please merge" and the reviewer's approval. |

**Other owner actions.** The orchestrator's first attempt to capture the two real fixture series was denied by the permission classifier. The owner then approved, in chat, a temporary read-only container for the capture (see [[forge-preview-gateway]]). The preview go-ahead for PV0–PV4 came at 2026-10-15T18:19:49Z, and the merge authorisation at 18:53:22Z.

(source: raw/2026-10-16-charting.md §Concept, Decisions taken during the build)

## What each project gained

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-service` | `internal/market/waves`: zigzag, Elliott and regime, one `Tunables` table and five byte-pinned fixtures. `GET /instruments/{id}/chart` and `GET /instruments/{id}/signals`. `elliott` and `regime` on the `context` of `GET /signals/{id}`. README routes, logs and error "When" text | [[elliott-regime-labeller]], [[chart-read-api]], [[signals-read-api]] |
| `tidewatch-web` | The Chart screen (`feat-chart/`) on `lightweight-charts` 5.2.1 behind an engine seam; the 96-slot strip; the Market watch symbol link; the two-key Trade pre-fill; filled Signals detail rows; `chart.css`; `DESIGN.md`, README and `CLAUDE.md` updates | [[design-system-decisions]], [[signal-cited-orders]], [[realtime-websocket]], [[market-data]] |
| `tidewatch-migrations`, `tidewatch-bot` | Nothing. `RequiredSchemaVersion` stays at I (`20261011182817`), and the bot harness is unaffected | [[centralized-migrations]] |

**Operations.**
- No migration, backfill, environment variable, secret, compose file, Redis key, metric or error code changed. The service `go.mod`/`go.sum` are unchanged.
- **The one new dependency is web-only:** `lightweight-charts` 5.2.1, pinned exactly and licensed Apache-2.0. It pulls in `fancy-canvas` 2.1.0, and both have sha512 integrity in the lockfile. It loads as its own chunk when the first chart opens, and never on the server.
- **Licence.** The licence requires the TradingView attribution and a link, so `attributionLogo` stays on and must never be turned off. The package ships no NOTICE file, so the web README's *Third-party notices* carries the upstream v5.2.1 NOTICE text, labelled as such.
- **Recovery.** Nothing is stored by either change, so each project rolls back on its own. Reverting the web removes the screen and brings back the Chart placeholder, the 48-only strip and the four-key-only pre-fill. Reverting the service removes both routes and the two context keys.
- **Owner's own stack.** Nothing to apply beyond deploying the two images; the merged service still needs only migration I.

(source: raw/2026-10-16-charting.md §Concept, Operations)

## What the user sees

**The Chart screen (`/chart/:instrument_id`, `app-chart`).**
- **Header.** The `h1` is the display symbol. The sub line reads "{name} · {venue_label} · {last price} · {change}" in plain text (CH-BD-1). It reads "Loading…" until the first head read answers, and after a failure it says "Chart couldn't load." or "No instrument called {id}.". On the right sit the status `.tag` (*Live*, *EOD*, *Closed · opens …*, *Stale*), the *Instrument* chip-select, and *Buy* / *Sell* links to `/trade?instrument=&side=`. The select lists the watchlist in order, with an off-watchlist current instrument first.
- **`/chart` without a parameter** reads `GET /market-watch` and goes to the first row with `replaceUrl`. With no rows it shows *No instrument to chart yet* and "Add an instrument on Market watch to chart it.".
- **Toolbar.** The *Timeframe* group offers 15m, 1h and 1D. On a `1d` base, 15m and 1h are disabled with the title *Daily bars only*. Five switches follow: *CDC Action Zone*, *EMA 12/26*, *Elliott count* and *Signals* are on, and *Fibonacci* is off and independent of the count. A switch turned off removes its drawing entirely. With *CDC Action Zone* off, bars take the neutral colours.
- **URL state.** `?tf=15m|1h|1d`, `?off=cdc,ema,elliott,signals` and `?on=fib` are written with `replaceUrl`, and only when they depart from the defaults. Nothing goes into `user_settings`. An instrument change keeps `off`/`on` and drops `tf`, so the next instrument opens on its strip timeframe.
- **Chart region.** It is 440 px tall above 1080, 360 px at ≤ 1080 and 300 px at ≤ 600. It holds the canvas, the state lines, "Couldn't load earlier bars." with *Try again* at the left edge, and the "Reconnecting live prices…" caption.
- **Strip row.** "Zone, last 96 bars", on the chart's timeframe. The cells are the last 96 closed bars that carry an indicator row.
- **Right column.** Three glass panels:
  - ***Right now*** (*Right now · 15m* on a 15m chart): the CDC zone and its age ("11 bars", or "No zone yet"), EMA 12 / 26, ATR 14, the regime ("Trend up, normal vol", or "Not enough history"), and Slack Water's verdict in the Bots words, or "Not in Slack Water's universe" (see [[bot-watch-verdicts]]).
  - ***Elliott, candidate counts***: the sentence "Candidate counts are not forecasts.", then at most two toggle buttons reading "{stage} … fit {fit}". The pressed one is drawn. Under them: "Invalidates if price closes below the wave 4 low, 183.40." (or "above … high"). With no candidate: "No candidate count on this timeframe yet."
  - ***Signals on this chart***: links to `/signals?day={Bangkok day of created_at}`, each with a time, the headline and "{Tier word} · {glyph} {p} · impact {impact}". Hover or focus enlarges the item's marker 1.5×. A marker click marks the item and moves focus to it, without scrolling the chart.
- **Layout.** Two columns above 1080 (`minmax(0,1fr) 290px`); the three panels in a row under the chart at ≤ 1080; stacked at ≤ 820; and a wrapping toolbar at ≤ 600.
- **States.** "Loading chart…"; "Chart couldn't load." with *Try again*; "No bars yet for {symbol}."; and "No instrument called {id}." with *Open the first chart*, only for a `404` whose code is `unknown_instrument`. A `422` falls back to 1D.
- **Keys.** On the focused chart, the arrow keys move ±1 bar, PageUp/PageDown ±10, Home/End go to the ends, `+`/`=` and `-` zoom ×2, and Escape clears. A polite status speaks the tooltip words for keyboard moves only. `[` and `]` work at page level and wrap through the watchlist.

(source: raw/2026-10-16-charting.md §Components, Routes and The Chart screen)

**Elsewhere.**
- **Market watch.** The symbol is a link to `/chart/{id}`, and the row stays non-interactive (see [[market-data]]).
- **Signals.** The instrument chips and *Open chart* now land on a real chart, and the detail's *Elliott* and *Regime* rows are filled (see [[signals-page]]).
- **Trade.** `/trade?instrument=&side=` pre-fills the instrument and side, and keeps the order type and quantity (see [[signal-cited-orders]]).

(source: raw/2026-10-16-charting.md §Components, Signals detail rows, Trade pre-fill, and Market watch link and the 96-slot strip)

## How the web builds it

- **`ChartService`** (`feat-chart/data/chart.service.ts`, component-provided) is keyed on the route parameter (S13) and on `tf`/`off`/`on`. It reads:
  - `GET /market-watch`, for the select, the header identity and the strip timeframe;
  - the head, at the default limit;
  - `GET /instruments/{id}` once, for an off-watchlist instrument (else the header names it by the part of the id before "@");
  - `GET /instruments/{id}/signals?from={first loaded bar ts}&limit=200`;
  - earlier pages, read imperatively.

  The first head read waits for `/market-watch` to learn the strip timeframe, unless the link asks for 1D.
- **Strict readers.** `data/chart.model.ts` refuses a whole body on a non-string decimal; an unknown zone, verdict, stage, kind, side, wave, trend or vol; a `fit` outside `["0.30","1.00"]` or without two decimals; more than two candidates; more than 5,000 bars; or a missing key. The Elliott and regime readers live in the leaf module `data/elliott.model.ts`, which both the chart model and the Signals model import, so neither imports the other.
- **Earlier bars.** Reaching the first loaded bar reads `to = first ts − 1 s, limit=1000` once, prepends the answer, and shifts the range so the same bars stay in view. It also re-reads the signals with the new `from`. It stops on an empty or short answer, or past 180 days of intraday history before the head's `generated_at`. A failure stops further reads until *Try again*.
- **Errors by code.** Only a `404 unknown_instrument` is the unknown state. A `404 not_found` and every other failure is the error state. A failed background reload keeps what is shown (MW-20).
- **`headLoads`** is a `linkedSignal` on the chart key (fix round 1, F1), so a later visit never opens on eight bars.
- **No browser clock.** "Now" for relative words is the newest `generated_at` the store has read. `feat-chart/` and `elliott-words.ts` contain no `Date.now()` and no argument-less `new Date()`.
- **The engine seam.** `CHART_ENGINE` is an `InjectionToken` over a small interface. `lightweight-engine.ts` is the one file that names `lightweight-charts`: it uses `import type` plus one dynamic `import()` after the first render, enforced by the `lib-imports` check. Vitest stubs the engine, because jsdom has no canvas. The library runs with kinetic scroll and last-price animation off, and with `vertTouchDrag: false` so that a vertical touch drag scrolls the page.
- **Bangkok axis.** Each instant is handed to the library shifted by +07:00. Every event and hook value maps back to the real instant.
- **Performance.** The first candlestick `setData` of a load is wrapped in the User Timing measure `tw-chart-setdata`. 1,000 bars took **1.7 ms** on the production build (authoritative) and 3.5 ms on the development build.
- **The dev-only test hook.** `CHART_TEST_HOOK` is true only when `isDevMode()`. The canvas then renders a hidden `<p data-testid="chart-hook">` whose text is JSON of what the engine drew: bar colours, EMA counts, markers with pixel positions, price lines, the Elliott points, the attached overlays, the visible range and the `setData` timing. Every Playwright test that reads it carries `@hook`. The production image has no hook: 0 on `/chart/NVDA@webull` on the production build, against 1 on the development control.

Colours, labels, markers and the accessibility wrapper are on [[design-system-decisions]]. The live fold is on [[realtime-websocket]] (source: raw/2026-10-16-charting.md §Components, `ChartService`, The engine seam and the canvas, and The dev-only test hook).

## Live behaviour

- A `tick` moves the header's last price and change, and the forming bar's `c`, `h` and `l`.
- A closed 1m `bar` folds into the UTC-aligned forming 15m, 1h or 1d bucket (`o` of the first, max `h`, min `l`, last `c`, summed `v`). The engine applies it as a single-bar update, with no history read. A bar past the boundary opens a new bucket, and the previous bar becomes closed without a zone.
- **S8.** After a bucket closes, one `limit=8` head re-read runs at 65 s, and one more at 180 s only if the newest closed bar still has no zone. A `zone` frame triggers it at once. The page merges the answer by `ts` and replaces `right_now`, `elliott` and `stance`.
- A `signal` frame with an unlisted id re-reads the instrument's signals, and the marker and item appear when it answers.
- A daily-base instrument folds nothing but still takes `status` and `signal`.
- Nothing in these updates moves the visible range, scrolls, animates or announces (MW-23).

(source: raw/2026-10-16-charting.md §Components, Realtime (S7))

## Test plan and acceptance

There is no CI, so every command runs locally.
- **Service.** `go vet ./... && go vet -tags integration ./...`, `gofmt -l`, `go test ./... -race -count=1`, `make build`, and `make test-integration TIDEWATCH_MIGRATIONS_DIR=<migrations checkout at 52deb26>` (about 395–480 s). Verification requires an `ok` line for `test/integration` and allows no `--- SKIP`.
- **Web.** Unit tests in the host zone and under `TZ=America/New_York` (3,932 at `91bdc07`), lint, the build, e2e lint, and the plan checks: `tsc-e2e`, the SSR smoke on `/chart` and `/chart/NVDA@webull`, `lib-imports`, the no-browser-clock and no-motion `lacks` checks, and the literal-colour greps.
- **Playwright runs on a preview only.** The `@hook` tests need the development build (PV0), and the production build runs `--grep-invert @hook`.

**New Playwright specs.** `e2e/src/chart.spec.ts` has 33 tests, 27 of them hook-free. They include a 13-state matrix at 390, 600, 1080, 1100 and 1440 in both themes, with overflow JSON and, at 1440, contrast and axe. `e2e/src/chart-live.spec.ts` has 6 tests. Chart is no longer a placeholder screen: `PLACEHOLDER_SCREENS` became `[STATS]`. The named service tests are listed on [[chart-read-api]], [[elliott-regime-labeller]] and [[signals-read-api]] (source: raw/2026-10-16-charting.md §Test plan, Commands and Named acceptance tests).

### Acceptance status (PRD §9)

| ID | Status | Evidence |
|---|---|---|
| FR-CH-SVC-001…007 | Passed | Named unit and integration tests, the A5 EXPLAIN, the hand re-derivation of a fixture, 45 gated routes and the README checks |
| FR-CH-WEB-001…005, 007…014 | Passed | Unit tests, PV1 r3 on the development and production builds, the PV3 r2 rendered review, and 1,000 bars in 1.7 ms |
| FR-CH-WEB-006 | Passed, after PF1 | Failed on the first preview run (the marker hit-test); passed in PV1 r2 and r3 |
| FR-CH-E2E-001 | Passed (r1 `6bc61c8`, r2 `91bdc07`) | NVDA and BTC/THB × 1h and 15m, dev hook against `indicators`. Head windows: 999 zoned bars plus the forming bar, 0 failures. Full histories (2,000–17,456 bars): the 14–25 warm-up rows with a NULL zone were drawn without a zone, 0 failures |
| FR-CH-E2E-002 | Passed (r1, r2) | An injected 1m bar raised the forming high in 171 ms (162 ms in r2) with no request. The bucket crossing made no head read. The `limit=8` re-read about 65 s later landed the zone equal to the SQL row |
| FR-CH-E2E-003 | **Partial** (CH-BD-3) | The injected C-SIG-1 frame triggered the signals re-read at +81 ms (r1) and +85 ms (r2). It answered 0 items, because an injected id has no database row and markers come only from the REST read. No real signal arrived during either run. Drawing within 2 s is proven only by the mocked `chart-live.spec` |
| FR-CH-E2E-004 | Passed (r1, r2) | 8 watchlist instruments, four reads each in the same minute (API `current_zone`, chart `right_now.zone`, the *Right now* DOM, the Market watch DOM): all agree |
| FR-CH-E2E-005 | Passed (r1, r2) | r1: 33 route reads, 28 candidates in 17 pairs, and an independent exact re-implementation identical on all 26 non-empty pairs. r2: 37 candidates in 21 pairs, with drawn points equal to the first candidate in all 21 |
| FR-CH-DOC-001 | Passed for the service and web docs; the wiki half was pending when the raw source was written | S5, S11, PV4 |

**Outcomes.** O1, O2 and O5 passed. O3 and O4 passed, except the real-row half of E2E-003.

(source: raw/2026-10-16-charting.md §Test plan, Acceptance status)

### Preview rounds and the defects they found

The preview run `chart-a69a3593` is described on [[forge-preview-gateway]].
- **PV1 at `4d8de59`** found three deterministic failures, each reproduced 2/2 in isolation. Fix round **PF1** corrected them:
  1. **A marker click did not mark its item.** In `lightweight-charts` 5.2.1, hover arbitration (`hitTestPane`) lets a series drawn above the candles win, so an EMA line within its 3 px hit tolerance took the pointer off a marker. Fix: when the library names no known marker, the engine hit-tests its own placed markers (`markerUnder`).
  2. **Earlier bars stopped loading.** The test "reached the first bar" was `range.from <= 0`, but after a prepend the library read a range set to 0 back as `1.1368683772161603e-13`. Fix: `FIRST_BAR_TOLERANCE = 1e-6` bar in `util/chart-range.ts`, shared by the canvas, the screen and the e2e helper.
  3. **A pasted out-of-window Signals day stayed on "Loading signals…" forever** on production builds. This race was pre-existing on `main` at `976233f`; see [[signals-day-control]].
- **PV1 r2 and r3** then passed. r3 on `91bdc07`: development 812 passed / 0 failed / 4 skipped (the 4 are live-gated specs), production 416 / 0.
- **PV3 r1** (130 captures) requested changes: B1, unlabelled Fibonacci levels, and W1–W4. Fix round **PF2** corrected them, and **PV3 r2 approved** with W5 and W6 left open (see [[design-system-decisions]]).
- **Found in code review, not on the preview:** `headLoads` kept `{limit: 8}` after an S8 re-read, so returning to the same chart opened it with 8 bars (F1); an S8 page that could not overlap replaced the chart (F2); an S8 merge undid a tick (F3); a store signal was written inside an effect (F5); a library-load failure left a blank chart (F6); a model import cycle (F7); focus was lost on `[`/`]` (F8, G1); and the service's nil-receiver hardening (RF1).

(source: raw/2026-10-16-charting.md §Test plan, Preview runs and Defects found on the preview and their fixes; §Concept, Review history)

### Manual reproduction

1. Open `/chart/NVDA@webull`. It opens on 1h, the strip timeframe. *Right now*'s zone, the strip's last cell and Market watch's current zone for NVDA match. Compare a few bars' colours with `SELECT ts, cdc_zone FROM indicators WHERE instrument_id = 'NVDA@webull' AND timeframe = '1h' ORDER BY ts DESC LIMIT 20`.
2. Switch to *15m*. The URL gains `?tf=15m`, the centre of the view is kept, and the panel title reads *Right now · 15m*. Turn *Elliott count* off: the polyline and its levels disappear, and the URL gains `?off=elliott`.
3. Read `GET /api/instruments/NVDA@webull/chart?timeframe=1h`. For each candidate, check that its points move in their own directions, that R1–R3 hold, and that a bullish invalidation is below the newest close. The panel shows at most two candidates and the sentence *Candidate counts are not forecasts.*
4. Keep the chart open through a bucket close. With no `GET …/chart` in the network log, the forming bar grows and a new bucket opens. About 65 s after the close, one `…&limit=8` read lands the zone.
5. On the first real signal for an open instrument, check that a marker and a *Signals on this chart* item appear within 2 s, and that clicking the marker marks and focuses the item. **This is the open half of FR-CH-E2E-003.**
6. Open a signal's detail on `/signals`: *Elliott* and *Regime* read values, or "No candidate count" / "Not enough history". Click a Market watch symbol: it opens `/chart/{id}`. Press *Buy* on the chart: Trade opens with the instrument and side set, and the order type and quantity unchanged.

(source: raw/2026-10-16-charting.md §Test plan, Manual reproduction)

## Open items

**Unverified or partial at merge (the owner knew).**
- **FR-CH-E2E-003, the real path** (CH-BD-3). Confirm that a marker and a feed item appear on an open chart within 2 s of the first real bot signal after merge.
- **Touch scroll at ≤ 600 px** (`vertTouchDrag: false`, F10). It was never run with touch emulation.
- Screen readers, the owner's own stack and production data were never checked.
- The 390/600/1080/1100 matrix captures were resizes of a chart opened at 1440, so they do not show "the last 96 bars on open" at narrow widths. The PF2 focus and tooltip captures did open at 390.

**Not deployed.** Both PRs are merged only. Deploy the service before the web; nothing else is needed.

**Web follow-ups.**
- `PageHeader`: an optional projected sub line, so the Chart's 24h change can carry its up/down tone (CH-BD-1).
- Security LOW (r1/r2): the route id is shown as written in the `h1` fallback, the unknown sentence and the wrapper `aria-label`. Add a shape check and a 64-character cap like `signal-prefill.ts` (text spoofing only).
- The invalidation sentence rounds the level to the tick through `formatPrice` (CH-OD-4): GOLD965THB 1D 71,975.88 reads "71,976", and GO 1h 4,199.52 reads "4,199.5". Consider the stored precision.
- Clear the `engineRestarting` flag once `engineReady()` is true after a restart (harmless today). Fix the `focusWrapper` doc comment and assert its off-watchlist return. Harden `chart.spec` (code r5).
- `journey.spec.ts`: fix round 1 (F4) restored a Chart visit, but the item stays in `state.followUps`.
- Design W5, W6, the PV3 r2 advisories and `DESIGN.md` item 25 are on [[design-system-decisions]]. Service follow-ups are on [[chart-read-api]]. The Signals items from PF1 are on [[signals-day-control]].

**Deferred by design (intent).**
- A 4h timeframe, as its own migration-plus-bot change.
- Tuning the zigzag thresholds and regime percentiles once the owner has seen the fixtures, and owner hand-labelled series as extra fixtures (see [[elliott-regime-labeller]]).
- **Slice 6:** the bot's port of the labeller against these fixtures, with bots reading the Elliott invalidation and the regime.
- **Slice 7:** a champion stance on the chart. Slack Water's watch verdict stands in until then.

(source: raw/2026-10-16-charting.md §Open questions)

**Update (slice 7, 2026-10-27).** Statistics did not add the champion stance: its owner decision D12 moved the champion stance on the Chart, the Tide brief and an Overview recommendation card to a follow-on spec. Slice 7's Stats equity chart reuses SE-17's keyboard pattern and, like Overview, uses no chart library (source: raw/2026-10-27-statistics.md §Concept, Owner decisions D12; §Components; see [[statistics]]).

## Related pages

- [[chart-read-api]]: `GET /instruments/{id}/chart`, the analysis window, `right_now`, the stance and the joined read
- [[elliott-regime-labeller]]: the `waves` package, its rules, tunables, regime and five fixtures
- [[signals-read-api]]: the instrument-scoped signal read and the detail's new `elliott` and `regime` keys
- [[market-timeseries]]: the `candles_*` relations and `indicators` rows the chart joins, and the 180-day retention behind earlier bars
- [[market-data]]: the Market watch row that `right_now` copies, and the symbol link
- [[realtime-websocket]]: the `tick`, `bar`, `zone`, `status` and `signal` frames the chart folds
- [[signal-message-contract]]: the C-SIG-1 frame, which carries no headline, so a new id triggers a REST re-read
- [[bot-watch-verdicts]]: the C11 verdict and `bot_watch` row behind the stance line
- [[zone-transition-bot]]: Slack Water, the stance source
- [[signals-page]]: the Signals detail rows now filled, and the chips and *Open chart* that land here
- [[signals-day-control]]: the pre-existing refused-day race fixed in PF1, and the `?day=` target of the feed items
- [[signal-cited-orders]]: the Trade pre-fill, which now also takes the two-key form
- [[instrument-master]]: `base_timeframe`, which limits a daily-base instrument to 1D
- [[design-system-decisions]]: the chart library, the colour roles, the 96-slot strip, CH-BUILD-1…12 and the rendered review
- [[centralized-migrations]]: no migration; the required schema version stays at I
- [[auth-model]]: both routes on the gated market group, and the owner-scoped stance
- [[forge-preview-gateway]]: the `chart-a69a3593` preview and its per-run development-build web (PV0)
