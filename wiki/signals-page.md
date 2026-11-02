# Signals page (`signals-page`, slice 4)

**Summary**: After slice 3a, signals appeared only as a count cell on Market watch. Slice 4 gives them a screen. `/signals` lists the Bangkok day's signals, newest first. Each row shows trust bars by tier, the headline, the instrument, direction and probability, an impact bar, and a Bots column that reads the decisions citing the signal. Pill-chip filters are held in the URL and stored per user. A row expands in place to three columns (Extracted, Model view, Context at the time) and up to three actions. *Buy/Sell with recommendation* opens `/trade` pre-filled at 10% of equity, which is Slack Water's sizing rule, and the resulting decision records the signal. A signal published while the page is open is counted in a quiet "N new signals · Show" note and is never inserted automatically. The rail shows an unseen count that is the same on every device. Migration I (`20261011182817`) adds `user_settings` and a GIN index on `decisions.signal_ids`. The service gained eight gated routes, an all-signals `/ws` feed backed by `PSUBSCRIBE sig:*`, a `decision_ctx` that can cite a signal, and the error code `signal_not_applicable`. The bot code is unchanged. The three code PRs merged on 2026-10-12 at 18:29Z on the owner's instruction, and a docs-only bot PR followed. **FR-SP-E2E-003 and FR-SP-E2E-004 were unverified at merge** because the preview had no suitable data. The owner knew this when they gave the instruction. As merged, the UI showed today only, and the owner asked for a day control as a follow-up (ORCH-19). The owner must apply I to their own database; until then the merged service answers `/ready` 503. **Update (2026-10-14):** ORCH-19 has been built as [[signals-day-control]]. A *Day* select shows any of the last 7 Bangkok days, and `?day=` holds the choice in the URL. At Bangkok midnight a page left open on Today relabels its rows *Yesterday*. tidewatch-web PR #13 merged on 2026-10-14 (merge `976233f`). It is **not deployed**, and its FR-SDC-E2E-001 is partial. **Update (2026-10-16):** [[charting]] (slice 5) merged on 2026-10-16 (web #14 `918d7b6`, service #11 `1547a89`) and is **not deployed**. The detail's *Elliott* and *Regime* rows now show values instead of "Arrives with Charting", and the instrument chips and *Open chart* land on a real chart. Its preview fix PF1 also corrected a pre-existing Signals race (see [[signals-day-control]]). **Update (2026-10-30):** signals context (spec 3b) adds **coverage signals**, `media` rows from GDELT with impact `0.0000`. They render through the existing table and detail **with no product change** (owner ruling WEB-OQ-3). They are listed only at *Impact ≥ 0.00*, and the Source chips gain one *GDELT Project* chip (see [[signals-context]]).

**Sources**: `raw/2026-10-12-signals-page.md`; `raw/2026-10-11-signals-ingest.md` (the ORCH-19 disambiguation only); `raw/2026-10-14-signals-day-control.md` (the day-control updates only); `raw/2026-10-16-charting.md` (the Elliott and Regime rows and the chart links only); `raw/2026-10-21-bots.md` (bots citing signals only); `raw/2026-10-31-fix-dialog-reopen-race.md` (the *Add source* fast-reopen fix only); `raw/2026-10-30-signals-context.md` (the coverage-signal rendering only)

**Last updated**: 2026-10-31

---

## Stage, stated precisely

This is the status in `state.json` as last updated at 2026-10-12T18:30:01Z (source: raw/2026-10-12-signals-page.md §Concept, Stage, stated precisely).

| Stage | Status |
|---|---|
| Implemented | Migrations MIG1–MIG3. Service S1–S8 plus review-fix r1 (`539a07e`). Web S1–S12 plus fix rounds r1 (`ff3a6c1`), r2 (`031d40e`, e2e only), r3 (`f2e5b01`) and r4 (`8dffcfb`), and the P6 docs commit (`0ebc5cc`, `DESIGN.md` only). |
| Verified locally | Every step's contract commands exited 0 on the orchestrator's re-run. Migrations harness: 1,436 PASS / 0 FAIL. Service: `make ci` and `make test-integration` passed on every step; one run hit the pre-existing port-collision flake and passed on re-run. Web: 3,001 unit tests in two time zones (default and `TZ=America/New_York`), lint, build and e2e lint/tsc, all at `8dffcfb`. |
| Reviewed | **Plans:** service r1 changes requested (1 blocking), then r2 approved. Web r1 changes requested (4 blocking), r2 approved, then r3 approved after an S8 scope gap. **Code:** service code r1, security r1 and the code r2 delta approved. Web angular r1, security r1, code r1 and the code r2 delta approved. Web design r1 requested changes (B1: the table did not fit at 1100 once a bot name appeared in the Bots cell); r2 approved at `8dffcfb`. |
| Verified on a preview | Partly. FR-SP-E2E-001 (with an injected publish), 002, 005 and 006 passed. **003 and 004 are unverified** (no suitable data). FR-SP-WEB-010 (rendered design review) passed. The mocked Playwright suite passed 749 / 0 failed / 4 skipped on the final image. The Bots screen's 0-pixel diff was 144/144 identical. |
| Merged | **Yes**, 2026-10-12, with merge commits and remote branch deletion, in the order migrations, service, web. The owner's instruction in chat: "merge it all for me and continue". No CI is configured on any repo. |
| Deployed / owner's own stack | Not deployed beyond the local preview. Whether I has been applied to the owner's own database is not recorded. |
| Documentation pass | The ORCH-5a docs-only bot PR and this wiki update. |

## Merge record

| Repo | PR | Range (base..PR head) | Merge commit |
|---|---|---|---|
| tidewatch-migrations | #9 | `4d05646..090e809` | `52deb26` (18:29:07Z) |
| tidewatch-service | #10 | `c570c99..539a07e` | `8b18486` (18:29:14Z) |
| tidewatch-web | #12 | `63c7f29..0ebc5cc` | `da6f4cb` (18:29:21Z) |
| tidewatch-bot | #9, docs only (ORCH-5a) | unchanged by code | `ece175a` (18:31Z) |

- **Size.** Migrations 4 files. Service 73 files at `b4ad4d1` (70 planned plus 3 extras); review-fix r1 stayed inside that set. Web 68 files; the final scope check at `0ebc5cc` counted 69 changed paths including `.plans/signals-page.md`, all planned.
- **The bot PR** corrects the stale pin sentence in `tidewatch-bot/CLAUDE.md` (line ~249, "it equals the service's RequiredSchemaVersion") and the README note. It has no code, harness or image change, and it was not a build target.
- **Rollout order:** migrations, then service, then web.

(source: raw/2026-10-12-signals-page.md §Concept, Stage; §Concept, ORCH-5a; §Files touched; §Open questions, Documentation and owner actions)

## Why the slice exists

Signals had existed since slice 3a (merged 2026-10-11), but the only place they appeared was a count cell on Market watch (see [[signals-ingest]]). The owner had nowhere to read a signal together with its provenance, the model's view and the market context at the time, and no way to act on a signal that left a trace in the decision record. The brief lists this as the owner's second feature: "a place to check news, its impact, and the instruments it touches, with the provenance and the model's view visible, so trust is earned row by row." The roadmap's exit test for slice 4: new signals appear without a reload; the expanded row shows extracted / model / context; *Buy with recommendation* opens the ticket pre-filled (source: raw/2026-10-12-signals-page.md §Concept, Problem).

The starting state, verified at `origin/main` on 2026-10-11:
- `decisions.signal_ids`, `signal_snapshot`, `model` and `followed_recommendation` existed but had never been written (see [[decision-record]]).
- `POST /orders` accepted only the empty `decision_ctx` (`{followed_recommendation: null, candidate_id: null, signal_ids: []}`).
- `/ws` forwarded `signal` frames only to connections subscribed to that instrument, and a connection may hold at most 100 subscriptions.
- No table stored per-user settings; the theme lived in `localStorage` only.
- `/signals` rendered the slice-0 placeholder.

(source: raw/2026-10-12-signals-page.md §Concept, Problem)

## Chosen design (owner decisions D1–D4, Spec studio 2026-10-11)

The owner took the recommended option each time.

- **D1. The Bots column reads the decisions that cite the signal, else "No bot acted".** "Acted on by bots" counts bot-actor decisions only. The owner's own signal-cited orders read "You bought 16.2 · followed" and are not counted. Two alternatives were rejected: leaving the column out until slice 6, and showing any bot trade on the instrument after the signal, which would attribute zone trades to news and corrupt slice 7's attribution. No bot cites signals until slice 6, so the count is 0 today by design.
- **D2. *Buy with recommendation* pre-fills the instrument, the side and 10% of equity, labelled as Slack Water's rule.** The decision records the signal id, `followed_recommendation = true` and a snapshot holding the suggested quantity and the rule (`equity_pct_10`). The number is a convention, not a forecast, and the label says so. See [[signal-cited-orders]].
- **D3. Filters and the badge's "seen through" instant live in the database:** migration I's `user_settings`, the settings routes and a badge route. Rejected: `localStorage`, and URL-only with no badge. A "since last visit" count is only true when every device agrees on what has been seen. See [[user-settings]].
- **D4. A browser-verified mockup on the real tokens is the visual target.** Where it differs from `DESIGN.md`, `DESIGN.md` wins, except for the pieces named in PRD §7.6. See [[design-system-decisions]].

**Accepted defaults (PD1–PD13, S1–S12).**
- One row per `signals` row (document × instrument). The instrument cell names its siblings.
- 50 rows per page, with a keyset cursor bound to the day and the filters.
- The UI shows today only; the API takes `day` for export and later use. (Superseded on 2026-10-14 by [[signals-day-control]], which uses that `day` with no API change.)
- Trust bars come from a closed map by tier: filing 5, exchange 4, wire 4, media 3, account 2.
- "Contradicted" means p ≥ 0.600, a directional call, and a move against the call larger than one daily ATR.
- The export is a CSV of at most 10,000 rows.
- The badge refreshes on navigation and every 5 minutes, and is hidden on `/signals`.
- **Not built:** a live badge elsewhere, a day control, a "Not this time" skip, Elliott or regime values ("Arrives with Charting"), recomputed decay, and any bot change. (The day control followed as [[signals-day-control]], merged 2026-10-14. Elliott and regime values followed with [[charting]], merged 2026-10-16.)

(source: raw/2026-10-12-signals-page.md §Concept, Chosen design and Accepted defaults; raw/2026-10-14-signals-day-control.md §Concept, Stage)

## What each project gained

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-migrations` | Migration I (`20261011182817`): `user_settings` and `decisions_signal_ids_gin_idx`. Harness 1,436 PASS / 0 FAIL | [[centralized-migrations]], [[user-settings]] |
| `tidewatch-service` | Eight gated routes: the signal list, detail, summary, badge and CSV export, `GET /sources`, and the settings read and write. Also the all-signals `/ws` feed on `PSUBSCRIBE sig:*`, a `decision_ctx` that cites one signal, the read-only recommendation, `signal_not_applicable`, and `RequiredSchemaVersion` moved to I | [[signals-read-api]], [[user-settings]], [[realtime-websocket]], [[redis-market-contract]], [[signal-cited-orders]] |
| `tidewatch-web` | The Signals screen (`feat-signals/`), the rail badge, the Trade pre-fill and signal context, `signals.css`, the expandable row moved into `table.css`, and a `DESIGN.md` refresh | [[design-system-decisions]], [[signal-cited-orders]], [[user-settings]] |
| `tidewatch-bot` | No code, harness or image change. Docs-only PR #9 fixes the schema-pin sentence | [[centralized-migrations]] |

**Unchanged:** environment variables, secrets, compose, the workspace root, `.env.example`, Go dependencies, Redis keys, tokens, theme and icons. The C-SIG-1 `signal` frame bytes are unchanged (see [[signal-message-contract]]) (source: raw/2026-10-12-signals-page.md §API, Configuration and compatibility; §Files touched, Not changed; §Concept, Cross-project contracts).

## What the user sees

**The Signals screen (`/signals`, `app-signals`).**
- **Header.** "Signals", with the sub line "{n} today · {n} acted on by bots · {n} contradicted by price". It reads "Loading…" until the first successful load; after that the counts stay through later failures (ORCH-17). On the right are *Export* and *Add source*. *Add source* opens a dialog ("Arrives with user sources.") that names the seeded primary sources and writes nothing. Pressing *Done* and then *Add source* at once could leave an empty, dimmed modal backdrop with no panel. The e2e "opens Add source and returns focus" failed 2 of 3 attempts in the learning-loop PV6 preview run. Since tidewatch-web #25 (merged 2026-10-30, deployment not verified), the dialog comes back with its text and *Done* focused, and Escape returns focus to *Add source*. The cause and the shared `Dialog` contract are on [[design-system-decisions]] (source: raw/2026-10-31-fix-dialog-reopen-race.md §Concept, The bug; §Test plan).
- **Filters.** These are three groups of pill chips plus a select:
  - *Asset class* (single choice): *All assets*, *US stocks*, *Thai stocks*, *Crypto*, *Gold*.
  - *Provenance*: *Filing*, *Wire*, *Exchange*, *Media*, *Account*. *Account* is disabled while no account source exists.
  - *Source*: one chip per publisher from `GET /sources`.
  - *Impact ≥*: 0.00 / 0.10 / 0.30 / 0.50 / 0.70, default 0.30.

  The URL holds the filters, and the stored filters apply when the URL has none (see [[user-settings]]).
- **Table.** Eight columns: When, Trust, What happened, Instrument (a chip to `/chart/{instrument_id}` plus up to three siblings), Direction, Impact, Bots and Details. The page shows 50 rows, with *Load more*.
- **States.** "Loading signals…". "Signals couldn't load." with *Try again*. An empty day reads "No signals yet today. Signals appear within seconds of a filing, release or exchange notice becoming a scored event." An empty filter reads "No signals match these filters today."
- **Expanded row.** Three columns:
  - *Extracted*: event and severity, novelty, publisher and body status, how the instrument was named, key facts and rationale;
  - *Model view*: the direction distribution, horizon, decision tier, extraction model, and the impact factors multiplied out;
  - *Context at the time*: the CDC zone, the price at the signal and now, and "price since" against one ATR. *Elliott* and *Regime* read "Arrives with Charting" (filled since slice 5; see "Since charting" below).

  The actions are *Buy/Sell with recommendation*, *Open chart* and *Source document*.
- **Live note.** While rows are waiting, the note reads "{n} new signals" with *Show*. Otherwise it reads "Newest first · Asia/Bangkok", plus "· {n} more under Impact ≥ {t}" when signals are hidden by the threshold. Nothing is inserted and nothing scrolls. *Show* prepends the rows, focuses *Today*, advances seen-through and reloads the summary.
- **Today only (as merged on 2026-10-12).** The page always showed the current Bangkok day. After Bangkok midnight it was empty until new signals arrived, and a page left open kept calling the old day *Today*. This is why the owner asked for a day control as a follow-up (ORCH-19).

(source: raw/2026-10-12-signals-page.md §Components; §Concept, ORCH-17 and ORCH-19; raw/2026-10-14-signals-day-control.md §Concept, Problem)

**Since the day control (merged 2026-10-14, not deployed).** The descriptions above are the slice-4 Today. The page now shows a *shown day*:
- A *Day* select (`label.chip.chip-select`, labelled "Day") is first in the filter row, before *Asset class*. It lists *Today*, *Yesterday* and five dates such as "Sat 10 Oct". "Today" is the Bangkok day of the service's latest `generated_at`, never the browser clock.
- The day lives only in `?day=YYYY-MM-DD`, written with `replaceUrl`. Absent means Today. `signals.filters` never stores it.
- On a past day, the sub line, the section `h2`, the table's region name and caption, the empty sentences and the *Export* link name that day, for example "142 yesterday · …" or "No signals on Sat 10 Oct.". A past day counts no live frames, offers no *Show* (except for a count already waiting at midnight), and never advances seen-through.
- At Bangkok midnight a page open on Today keeps its rows. Within one 60 s summary tick it relabels them *Yesterday* and writes `?day=`, without reading the list again.
- An empty Today offers *Show yesterday* after the empty sentence.
- The section `h2` keeps its id and `tabindex="-1"`, so the focus targets are unchanged; the heading now reads the shown day's label.

The full behaviour, decisions and acceptance are on [[signals-day-control]] (source: raw/2026-10-14-signals-day-control.md, summary block; §Components; §Concept, Owner decisions; §Cross-cutting links).

**Elsewhere.**
- **Rail.** An unseen count on the Signals link (`.nav-count`, "99+" above 99), hidden while on `/signals` (see [[user-settings]]).
- **Trade.** `/trade?instrument=&side=&qty=&signal=` pre-fills a Market order and carries the signal into the decision (see [[signal-cited-orders]]).
- **Chart.** `/chart/:instrument_id` shows the existing Chart placeholder; the parameter is unused until Charting.

(source: raw/2026-10-12-signals-page.md §Components; §Concept, ORCH-17 and ORCH-19)

**Since charting (slice 5, merged 2026-10-16, not deployed).** See [[charting]].
- **Chart links.** The instrument chips and *Open chart* now open the real Chart at `/chart/{instrument_id}`.
- **The detail's *Elliott* row** reads "{stage} · fit {fit} · invalidates {below|above} {price}", with the price through `formatPrice(price, null)` as `atr14` is. ***Regime*** reads the regime words, such as "Trend up, normal vol". A null or absent key reads "No candidate count" or "Not enough history", still `.faint`. Filled values are plain `.v` text.
- **The values** come from the detail's new `context.elliott` and `context.regime`, computed on the strip timeframe from bars that had closed by the signal's `created_at` (`ts + timeframe ≤ created_at`) (see [[signals-read-api]] and [[elliott-regime-labeller]]).
- **Copy.** "Arrives with Charting" is removed, and `SIGNAL_COPY.arrivesWithCharting` is gone. `pages/workspace/util/elliott-words.ts` holds the words both the chart and the detail use, so they cannot drift. The e2e Signals mock's detail fixtures gained `elliott` and `regime`, and `signals.spec.ts` gained "shows Elliott and regime in the context column".
- **The way back.** A *Signals on this chart* item links to `/signals?day={Bangkok day of created_at}`, so the Chart opens the Signals page on the signal's day (see [[signals-day-control]]).

(source: raw/2026-10-16-charting.md §Components, Signals detail rows and The Chart screen; §API, The signal detail's new context keys; §Test plan, Named acceptance tests, S10 updates; §Cross-cutting links)

How the routes answer is on [[signals-read-api]]. Styles, measured fit and `DESIGN.md` are on [[design-system-decisions]].

## Owner decisions during the build

| ID | When (UTC) | Decision |
|---|---|---|
| ORCH-5a | 2026-10-11T17:53Z | The stale bot pin sentence is corrected by a **docs-only bot PR in the documentation pass**, which is not a build target. |
| ORCH-8 | 2026-10-11T18:09Z | `GET /signals` adds a hidden-by-threshold count; the web shows "· {n} more under Impact ≥ {t}" only when it is above 0. |
| ORCH-9 | 2026-10-11T18:09Z | A4 (the export link's cookie) is checked on the preview only. The development half is reported unverified, and the build never migrates the shared dev database. |
| ORCH-10 | 2026-10-11T18:26Z | The signal context **survives a 5xx or network failure** (unknown outcome), so a retry re-sends a byte-identical body under the same `client_order_id`. It is dropped after any definite answer. This departs from PRD §4.6's "whatever the outcome code". |
| ORCH-11 | 2026-10-11T18:26Z | Flipping the ticket's side keeps citing the signal with `followed_recommendation: false`; flipping back restores `true`. |
| ORCH-13 | 2026-10-12T03:32Z | Preview finding F1: the Model view's impact line shows the **real freshness at creation**, computed in the web. PRD §4.5's "freshness 1.00" premise was wrong (see [[signals-pipeline]]). |
| ORCH-14 | 2026-10-12T03:32Z | A pre-fill for an instrument that is not on the watchlist shows a hint on Trade instead of being ignored silently. |
| ORCH-15 | 2026-10-12T03:32Z | Preview F3: a signal pre-fill sets the order type to **Market**. Before, it stayed Limit with an empty price. |
| ORCH-16 | 2026-10-12T07:30Z | Design B1: the Bots cell's lines **wrap**, so the table fits 862/862 at 1100 whatever the data. |
| ORCH-17 | 2026-10-12T07:30Z | Design W1: the sub line reads "Loading…" only until the first successful list load. |
| ORCH-18 | 2026-10-12T07:30Z | The owner authorised a fourth web fix round past the cap of 3, covering ORCH-16/17 and polish. |
| ORCH-19 | 2026-10-12T18:24Z (01:24 on 10-13 Bangkok) | After seeing an empty page after Bangkok midnight, the owner chose to **keep today-only for this build** and add a day control as a follow-up after the merge. *Since closed:* built as [[signals-day-control]], merged 2026-10-14 as tidewatch-web#13 (`976233f`), not deployed. |

ORCH numbers are per feature. Slice 3a's ORCH-19 (merge before the soak, on [[signals-ingest]]) is a different decision (source: raw/2026-10-12-signals-page.md §Concept, Owner decisions taken during the build; raw/2026-10-11-signals-ingest.md §Concept, Owner and orchestrator decisions during the build). The "since closed" note on ORCH-19 comes from raw/2026-10-14-signals-day-control.md §Concept, Problem and Stage.

**Orchestrator rulings (ORCH-1…7, 12).**
- **ORCH-1.** Migration I was planned as MIG steps inside the service plan, because `workspace.json` registers only web, service and bot. The migrations repo kept its own worktree (`b7ddc75378`), branch and PR, and merged first. The MIG billets live in the service namespace (TS-75…77).
- **ORCH-2 / ORCH-3.** The service plan pins the shared contracts, and the web planner conformed to them. I's version is MIG1's output, not a guessed timestamp.
- **ORCH-4.** The settings value limit is 4 KiB in the service, with an 8192-octet CHECK in the database as a backstop.
- **ORCH-5.** The bot is not built. Its harness requires H applied and the newest applied version not older than H, which I satisfies.
- **ORCH-6.** Lanes: service MIG1 → MIG3 → S1…S8, and web S1… on mocks once the service plan was approved. Merge order migrations, service, web. No workspace-root, compose or `.env.example` edits, and `documents/` is never edited.
- **ORCH-7.** Models were chosen per step by workload (opus/high for the heavier service and web steps, sonnet for the rest). Execution used dependency-gated lanes and sequential bundles.
- **ORCH-12** (code review r1 SF1; the owner may overrule). A partly selected publisher is widened to all of that publisher's current codes once `GET /sources` answers, so the chip reads pressed honestly. The rejected alternative was `aria-pressed="mixed"` with a new style.

(source: raw/2026-10-12-signals-page.md §Concept, Orchestrator rulings)

**Web plan resolutions worth knowing.**
- **SP-W-3.** The shell reads `GET /signals/badge` on every screen, so every mocked spec's `failClosedApi` answers that route with `QUIET_BADGE` (`unseen: 0`).
- **SP-W-15.** `signals-live.spec.ts` is mocked and not gated, unlike `market-watch-live` and `bots-live`.
- **SP-W-23.** The Bots column uses two words beyond the PRD's three verbs: "proposed" and "protected". A null `qty` drops the quantity.
- **Revision r3.** `screen-placeholder.spec.ts` still expected `/signals` to be the placeholder. Adding it to S8's scope fixed a planning gap, not a product decision.

(source: raw/2026-10-12-signals-page.md §Concept, Plan resolutions, Web)

## Test plan and acceptance

There is no CI, so every command runs locally.
- **Migrations.** `make migrate-validate` and `make check-disposable-db`.
- **Service.** `make ci`, then `make test-integration TIDEWATCH_MIGRATIONS_DIR=<migrations checkout>` (about 285 s). No `--- SKIP` is allowed. If the only integration failure is "address already in use" on a metrics port, re-run: that is the pre-existing `freePort` race.
- **Web.** `pnpm nx run-many -t lint test build`, also under `TZ=America/New_York`, plus the full Playwright suite against a preview. The mocked specs need a real sign-in for `authed`, so in the worktree they are only listed, linted and type-checked.

The named acceptance tests (do not rename) are listed on [[signals-read-api]], [[user-settings]], [[signal-cited-orders]] and [[realtime-websocket]]. The web e2e specs are `e2e/src/signals.spec.ts` (47 tests) and `e2e/src/signals-live.spec.ts` (13 tests), with mocks in `e2e/src/support/signals.ts` (source: raw/2026-10-12-signals-page.md §Test plan, Commands and Named acceptance tests).

### Acceptance status (PRD §9)

| IDs | Status | Evidence / note |
|---|---|---|
| FR-SP-MIG-001, 002 | Passed | Harness 1,436/0; MIG1 SQL equal to §5.1; preview `/api/ready` 200 at I |
| FR-SP-SVC-001…010 | Passed | Named tests and the review-fix r1 re-runs. SVC-008 passed on re-run after a harness port-collision flake |
| FR-SP-WEB-001…006, 008, 009, 011 | Passed | Unit tests plus P1-final2 (749 / 0 / 4 skipped on web `8dffcfb`; signals 47/47, signals-live 13/13, trade 97/97, bots 260/260). WEB-005 is mocked only; its live half is E2E-004 |
| FR-SP-WEB-007 | Passed (preview half) | Three real downloads of `signals-2026-10-12.csv` with a BOM, the exact header, row counts equal to the API, and the session cookie sent. **The development half is unverified** (not run, ORCH-9) |
| FR-SP-WEB-010 | Passed | Design r1 requested changes; after fix r4, r2 approved. See [[design-system-decisions]] |
| FR-SP-WEB-012 | Passed on the preview | P1 at `ff3a6c1` had 21 failures, all test defects, fixed in fix-r2; then P1-final 745/0 and P1-final2 749/0. **The "locally" half is unverified** (not run) |
| FR-SP-E2E-001 | Passed (injected) | The note changed 97 ms after an injected PUBLISH, with no scroll. No real bot publish arrived in 25 minutes (see [[signal-message-contract]]) |
| FR-SP-E2E-002 | Passed | Filters stored in one browser came back in a second one (see [[user-settings]]) |
| FR-SP-E2E-003 | **Unverified** | Partial: the day's two media (Finnhub) rows passed 133/133 checks each (API vs SQL 81, DOM vs PRD words built from SQL 52). No filing, wire or structured-source signal existed: EDGAR returned `nothing_new` on a Sunday night in New York, the wires were not material or named no instrument, Binance TH had `nothing_new`, and `set-notices` was disabled |
| FR-SP-E2E-004 | **Unverified** | Both of the day's signals (AAPL, NVDA) had a stale `px:last` because the US market was closed, so `recommendation` was null and no primary button showed. No order or decision was created (see [[signal-cited-orders]]) |
| FR-SP-E2E-005 | Passed | Real data at 1100: `scrollWidth == innerWidth` at all five widths in both themes; region 862/862; detail wrap 828px with three columns |
| FR-SP-E2E-006 | Passed | Tested with a stored threshold of 0.00, because both real rows sat under 0.30. The rail read "Signals, 2 unseen" and dropped to 0 in a second browser after the first one's reveal (see [[user-settings]]) |

**Outcomes (intent O1–O5).** O1 passed. O2 passed at component level, with E2E-003 unverified. O3 passed in unit and mocked tests, with E2E-004 unverified. O4 passed, with an injected publish. O5 passed.

**Which revisions the live checks ran on.** P3/P4 ran against web `ff3a6c1` and service `539a07e`. The later web rounds (r3 for ORCH-13/14/15, r4 for ORCH-16/17/18) were verified by the mocked suite on the preview and the delta design review. P3 was not re-run after them.

**Assumptions (PRD A1–A6).** A1 (the manual bot's equity is reachable from the order path) held in planning; the recommendation reuses `GET /trade`'s valuation. A2 (`PSubscribe` on the existing connection) held. **A3 (lateral `indicators` lookups are fast by primary key) is unverified, because no explain-analyse is recorded.** A4 (the download cookie) held on the preview; the development half is unverified. A5 (most media rows sit under 0.30) is consistent with the preview's two media rows (0.0002 and 0.1568), but that sample is very small. A6 (`container-type` does not disturb scrolling) held.

(source: raw/2026-10-12-signals-page.md §Test plan, Acceptance status, Outcomes, Which revisions and Assumption outcomes)

**Preview.** The build moved mid-run to Forge's shared, retained workspace database volume at the owner's request. At merge, the active preview was the related run `sigpws-8add0389` with 2 signals. Details and operating notes are on [[forge-preview-gateway]] (source: raw/2026-10-12-signals-page.md §Test plan, Preview and the database change).

### Manual reproduction

1. Apply I, open `/signals` with the bot pipeline running, and expand a row. Compare it with `SELECT … FROM signals JOIN documents …`, the `triage`, `extractions` and `document_instruments` rows, and `indicators` at or before `created_at`. The impact factors should multiply to `signals.impact` within display rounding.
2. With the page open, wait for a real publish, or inject one with `PUBLISH sig:<instrument_id> '<C-SIG-1 JSON>'`. Within 2 s the note reads "1 new signal Show", and the page does not scroll. *Show* prepends the row, focuses *Today*, and `user_settings.signals.seen_through` advances.
3. Change chips, reload, and open the same `/signals` with no query in a second browser: the same filters appear.
4. For a signal whose instrument has a fresh `px:last` and is on the watchlist, use *Buy with recommendation*. On `/trade`, check the instrument, side, quantity, Market and the hint, then place the order. Check `decisions.signal_ids`, `followed_recommendation = true` and `signal_snapshot.recommendation.rule = 'equity_pct_10'`. The Signals row should then read "You bought {qty}" over "followed · HH:mm". This is FR-SP-E2E-004, not yet done.
5. `curl` with a session cookie against `/signals/export.csv?day=YYYY-MM-DD&min_impact=0.00`: the answer is an attachment with a BOM, the exact header and CRLF line ends.

(source: raw/2026-10-12-signals-page.md §Test plan, Manual reproduction)

## Open items

**Unverified at merge (the owner knew).**
- FR-SP-E2E-003 for a filing, a wire and a structured-source row.
- FR-SP-E2E-004: the buy flow, the decision row and the "You bought … · followed" row. **No signal-cited order has been placed on any stack yet.**
- A real bot → Redis → service → web publish observed live. E2E-001 passed only with an injected publish.
- The development half of A4 and of FR-SP-WEB-012.
- A3, because no explain-analyse is recorded.
- Rendered motion for *Show* and *Load more*, because there was no data.

**Owner-requested follow-up: the day control (ORCH-19), now merged.** At slice-4 merge this was an open follow-up: a Today/Yesterday control or a last-7-days picker, with `?day=` in the URL. Past days would get no live note, no *Show* and no seen-through update, and would show that day's counts. It was web only, because the API already took `day`. It came up when the owner saw an empty page after Bangkok midnight (source: raw/2026-10-12-signals-page.md §Open questions).

The owner chose the last-7-days *Day* select (DC1). It was built as [[signals-day-control]]: implemented and reviewed (five code rounds, round 5 all approved), and verified on a preview for 14 of 15 IDs. **FR-SDC-E2E-001 is partial**, because the preview's Yesterday had no real signals. It merged on 2026-10-14 at 06:58:59Z as tidewatch-web#13 (head `e49c237`, merge `976233f`). It is **not deployed**, and no database or service step is needed (source: raw/2026-10-14-signals-day-control.md §Concept, Stage; §Concept, Owner decisions; §Test plan, Acceptance status).

**Data and volume.**
- **Few signals.** The instrument master holds 11 instruments, and 460 extraction mentions were unresolved, so filings and wires about other companies never become signals. Widening the instrument universe is a follow-up in tidewatch-migrations and the bot's instrument master (see [[instrument-master]]).
- **Default threshold.** Whether 0.30 is the right default (A5, the intent's watched assumption) needs more days of data.
- **Bots column.** It will read "No bot acted" and "0 acted on by bots" until slice 6 bots cite signals. **Since slice 6 (bots, merged 2026-10-21, not deployed), bots do cite signals:** a signal-driven candidate's decisions carry its `signal_ids`, so the Bots column and the count can show bot actors (see [[signals-read-api]] and [[bots]]) (source: raw/2026-10-21-bots.md §The bot engine, Decisions written by the loops; §Cross-cutting links).

**Owner actions.**
- Apply migration I to the owner's own database (`make migrate-up` in tidewatch-migrations) before running the merged service; `/ready` stays 503 until then. I is additive with no backfill. Rollback is `make migrate-down`, which drops `user_settings` and the GIN index (destructive for settings only). Rollout order: migrations → service → web.
- Reset the shared preview database's `signals.filters` if wanted. The acceptance agent left Wire and PR Newswire off and Impact ≥ 0.00.

**Out of scope by design.** Decay after creation is still not recomputed; the shown freshness is the value at creation.

**Follow-ups** from the reviews and `state.json` are listed on the concept pages: service routes and export on [[signals-read-api]]; the feed's R15 double-flip window and security L3 on [[realtime-websocket]]; the pre-fill and order path on [[signal-cited-orders]]; design and Angular items on [[design-system-decisions]].

(source: raw/2026-10-12-signals-page.md §Open questions)

## Coverage signals on the page (signals context, 2026-10-30)

Signals context (tidewatch-web #22, merge `9dc59cf`, merged 2026-10-30; deploy triggered, not verified) made **no Signals page product change** (intent non-goal, SC-W-8). A coverage signal (see [[context-features-and-coverage-signals]]) renders through the existing table and detail:
- **Row:** the headline (the coverage title, `Coverage: {symbol} {z}σ above its 30-day baseline · …`), *Media trust*, ◆ Neutral 1.000, and an impact bar at 0.0000.
- **Detail:** *Other · severity x.xx / 5*, *GDELT Project · headline only*, *Named in the document*; no *Key facts*, no rationale and no source link; *System 1 · context.v1*, Extraction *context.v1*.
- **No dashes** are drawn for the absent triage and extraction. The PRD text said "dashes"; the owner accepted the shipped rendering (WEB-OQ-3).
- **Threshold.** The row is listed only at *Impact ≥ 0.00*. At the default 0.30 it is counted in the "N more under Impact ≥ 0.30" note.
- **Source chips.** One new *GDELT Project* chip; the calendar source reuses *Finnhub*.
- **Counts.** The Market watch count and the Signals page count both origins. `origin` is not exposed, so the page cannot tell a coverage signal apart except by its content.
- **Tests.** `signals.spec.ts` covers the render with `SIGNAL_FIXTURES_WITH_COVERAGE` and `SOURCES_WITH_CONTEXT`. It ran on the preview before the `main` updates and was not re-run on the merged tree.
- **Next.** Rendering context rows differently waits for the "what the bot sees" view.

(source: raw/2026-10-30-signals-context.md §Components, Signals page; §Concept, How it runs, 6. Never a trigger; §Test plan, Web and Recorded results; §Open questions, Assumptions still open)

## Related pages

- [[signals-day-control]]: the ORCH-19 follow-up, a last-7-days *Day* select, `?day=` and the midnight relabel (merged 2026-10-14)
- [[charting]]: slice 5, which filled the *Elliott* and *Regime* rows and gave the chips and *Open chart* a real chart (merged 2026-10-16)
- [[elliott-regime-labeller]]: the labeller behind the detail's *Elliott* and *Regime* values
- [[signals-read-api]]: the list, detail, summary, badge, export and sources routes
- [[user-settings]]: `user_settings`, the stored filters, seen-through and the rail badge
- [[signal-cited-orders]]: the recommendation, the Trade pre-fill, `decision_ctx` and `signal_not_applicable`
- [[signals-ingest]]: slice 3a, which made the signals, the C-SIG-1 publish and the Market watch count
- [[signals-pipeline]]: the rows the detail reads, and the impact formula behind ORCH-13
- [[signal-message-contract]]: the unchanged `signal` frame and how the page counts new rows
- [[realtime-websocket]]: `subscribe_signals` and the per-connection all-signals flag
- [[redis-market-contract]]: `PSUBSCRIBE sig:*` and the `px:last` usability rule
- [[decision-record]]: the first writes of the four signal columns and the GIN index
- [[paper-trading]]: the order path that checks a cited signal
- [[source-registry-and-ingest]]: `GET /sources` and the publisher chips
- [[centralized-migrations]]: migration I and the required schema version
- [[market-timeseries]]: the strip rows and `atr14` behind Context at the time
- [[instrument-master]]: the 11-instrument universe that limits signal volume
- [[zone-transition-bot]]: Slack Water's 10%-of-equity rule that D2 borrows
- [[bot-activity]]: the expandable-row pattern, now shared through `table.css`
- [[design-system-decisions]]: the shared `Dialog` behind *Add source* and its one-`closed`-per-opening contract
- [[design-system-decisions]]: the chip, bars, tones, rail badge and the 1100 fit
- [[forge-preview-gateway]]: the shared retained preview volume and the related runs
- [[auth-model]]: per-user scoping and the login throttle hit on the preview
- [[request-protection]]: CSRF on the settings write and the cookie-carrying export
- [[bots]]: slice 6, whose bot decisions now cite signals in the Bots column
- [[signals-context]]: spec 3b, whose coverage signals render here unchanged
