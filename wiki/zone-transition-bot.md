# Zone-transition bot: Slack Water (Slice 2b)

**Summary**: Slice 2b added the first bot that trades paper money on its own. Each user now gets a second lazily created bot, **Slack Water** (`kind = auto`, `template = zone_transitions`, `mode = paper_auto`, ฿1,000,000), beside the slice-2 `me` bot. A new `bots` runner in tidewatch-bot checks it every 30 s. It buys at market when a CDC zone run on the strip timeframe turns Buy, and closes the whole position when the zone reads Sell. The four PRs merged on 2026-10-09. **The bot had not yet been seen placing an order** when the source was written: FR-ZB-E2E-001 and 002 are unverified, E2E-003 is partly verified, E2E-004 has not started, and FR-ZB-DOC-002 is deferred. The follow-on feature [[bot-activity]] (merged 2026-10-10) makes the bot record a per-instrument verdict on every pass and adds the Watch and Checks sections to the Bots screen; the first live bot entry was still unverified when it was written. **Since slice 6 ([[bots]], merged 2026-10-21, not deployed),** the runner dispatches each auto bot by the vocabulary of its current version: Slack Water's v1 still runs this unchanged 2b pass (its files are byte-identical to `ece175a`), while v2 bots run the new general engine (see [[bots-engine]]). A legacy bot can be moved to v2 with one explicit *Upgrade*.

**Sources**: `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md` (bot-activity changes only); `raw/2026-10-11-signals-ingest.md` (the ORCH-19 precedent note only); `raw/2026-10-12-signals-page.md` (the borrowed sizing rule only); `raw/2026-10-21-bots.md` (what slice 6 kept and added around the 2b pass)

**Last updated**: 2026-10-21

---

## Stage, stated precisely

This is the status in `state.json`, last updated 2026-10-09T17:45Z (source: raw/2026-10-09-zone-transition-bot.md §Concept, Stage, stated precisely).

| Stage | Status |
|---|---|
| Implemented | All planned steps are done: service MIG1, MIG2 and S1–S6 (the MIG steps land in the migrations repo, ORCH-1); bot S1–S10; web S1, S2, M1 (S3 and S4 bundled), S5–S9. Fix rounds after review: service 1 (cursor check order), bot 1 (the R2 memo order), web 2 (review fixes, then the preview test fixes ORCH-13/13a). |
| Verified locally | Every step's contract commands exited 0. The C10 fixture is byte-identical in the service and the bot (sha256 `7f43058a…2d24`). |
| Reviewed | Service and bot: code and security APPROVED in r1, delta APPROVED in r2. Web: all five reviewers requested changes in r1 (blocking design defect B1), APPROVED 5/5 in r2, and r3 delta-approved the preview test fixes. |
| Merged | Yes, on 2026-10-09 between 17:43:35Z and 17:43:59Z. The orchestrator merged on the owner's instruction "merge now and continue" (OWNER-2). There is no CI (D4). |
| Verified on a preview | **Partly.** The isolated Forge preview (compose project `forge-0199b29a-zbot-d1343f8c`, fresh database at F) ran exactly the PR heads. The mocked Bots suite, the secret scan, the runner state and the screen-against-SQL read passed. **No bot entry, restart replay or live Pause/Resume was observed.** |
| Running on the owner's own stack | **Not recorded.** The owner must apply migration F first (`make migrate-up` in tidewatch-migrations). Until then the service's `/ready` stays 503. |

## Merge record

| Repo | PR | Range (base..PR head) | Merge commit | Files |
|---|---|---|---|---|
| tidewatch-migrations | #5 | `6531508..bbf7a87` | `1e115c0` | 4 |
| tidewatch-service | #5 | `857d420..d87d098` | `594548f` | 50 |
| tidewatch-bot | #5 | `6902f4e..287818a` | `ac80b04` | 70 |
| tidewatch-web | #7 | `7c7b602..bfc9c48` | `db96bc9` | 43 (42 planned, plus `paper-orders.spec.ts` under ORCH-13) |

The merge order was migrations, then service and bot together (they share contract C4'), then web (source: raw/2026-10-09-zone-transition-bot.md §Concept, Stage and OWNER-2; §Files touched).

## Why the slice exists

Slice 2 ([[simulation-engine]]) delivered manual paper trading only. The owner's idea of "the sim" is a bot trading paper money in the background, but auto mode was not due until slice 6. The owner had accepted "manual first" on condition that a bot would follow soon. A rules-only bot on CDC Action Zone transitions needs no signals, because the `indicators` rows with `cdc_zone` already exist for every closed 15m, 1h and 1d bucket (see [[market-timeseries]]). The approved mockup already named this bot: Slack Water, "Zone transitions · v1" (source: raw/2026-10-09-zone-transition-bot.md §Concept, Problem).

## What each project gained

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-migrations` | Migration F (`20261009122143`): `bot_versions`, `bot_runs` and three `bots` columns | [[centralized-migrations]], [[bot-versions-and-runs]] |
| `tidewatch-service` | Lazy creation of both bots (`EnsureBots`), six `/bots` routes including Pause and Resume, the C10 version fixture, C4' `StampCloseReason`, error code `bot_status_conflict`, audit event `bot_status_changed` | [[bot-versions-and-runs]], [[paper-trading]] |
| `tidewatch-bot` | The new `packages/bots` library and the `bots` runner (the eleventh `COLLECTOR_NAMES` entry), the bot-side intake, and C4' in `packages/sim` | [[market-data-worker]], [[paper-trading]] |
| `tidewatch-web` | The Bots screen (list, detail, Pause / Resume), a shared `app-decision-record`, a bot branch in the order view | [[design-system-decisions]], [[decision-record]] |

(source: raw/2026-10-09-zone-transition-bot.md, summary block; §Database; §API; §Components)

## Trading rules (owner decisions ZB1–ZB4)

The owner accepted the recommended answers to Q1–Q10 as a block on 2026-10-09, then picked one mockup direction (ZB11) (source: raw/2026-10-09-zone-transition-bot.md §Concept, Chosen design).

- **ZB1 Rules.** Enter long on a transition into `buy`. Close on a transition into `sell`. Long only, market orders, one position per instrument. No adds, trims, stops or time limit. Rejected for now: a tighter exit on leaving `buy`, and GO shorts. Both could become later versions of the same bot.
- **ZB2 Timeframe.** The strip timeframe: `1h`, or `1d` for daily-only instruments such as PTT.BK. It is recorded in the version config. Rejected: `1d` for everything (a handful of trades a month) and `15m` (noise).
- **ZB3 Universe.** The owner's watchlist at evaluation time, tradable classes only. Manual-fill venues (Gold 96.5 at MTS) and futures (GO) are excluded through config flags. An instrument removed from the watchlist while a position is open is still managed to its exit. Default universe: NVDA, AAPL, PTT.BK, BTC/THB, ETH/THB, XAU/USD.
- **ZB4 Sizing.** 10% of current equity per entry, with the quantity rounded down. At most 6 open positions. A blocked entry writes a `skip` decision with reasons. Rejected: 20% with 4 positions, and 1/n of starting capital.
  - **Borrowed by the Signals page (slice 4, owner decision D2).** *Buy/Sell with recommendation* pre-fills 10% of the manual bot's equity and labels the number "like Slack Water". It is a convention, not a forecast. The rule is recorded as `equity_pct_10` in the decision's `signal_snapshot` (see [[signal-cited-orders]]). Slack Water itself is unchanged and cites no signal. Bots start citing signals in slice 6, so until then the Signals page reads "0 acted on by bots" (source: raw/2026-10-12-signals-page.md §Concept, Chosen design D1 and D2; §Cross-cutting links).

**Proposed defaults the build implemented** (PRD "PD"; not owner decisions):
- **Entries are transition-driven; exits are state-driven.** An entry needs a Buy zone run that started at or after `bots.status_since` and has no bot decision yet. The bot acts once per (instrument, zone run), with either an order or a `skip`. An exit fires whenever the bot holds a position and the latest strip row is `sell`. That includes right after a resume, and a Sell row that landed while the venue was closed.
- **The baseline resets on resume.** `status_since` marks the start of the current `running` stretch. Pausing cancels no pending order and closes no position.
- **Deferral is not a decision.** A closed venue or no live price writes nothing, and the next pass retries. Insufficient cash, the position or exposure limit, `max_open` and a zero quantity each write a `skip`, which closes that zone run.
- **Idempotent placement.** `client_order_id` is a UUIDv5 of (`bot_id`, `instrument_id`, entry plus the zone run start, or exit plus the position's `opened_at`). `UNIQUE (bot_id, client_order_id)` refuses a replay.

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Proposed defaults the build implemented)

### Zone-run details (bot plan)

- **R3, zone run window.** The run start is the earliest row of the trailing same-zone streak within the latest 49 strip rows. If the streak fills all 49 rows, the start is unknown and the run is never entered. Otherwise a sliding window would invent a new start every bar.
- **R4.** One count-based read of the latest 49 strip rows per instrument. It replaced a time-window read, which could not guarantee 48 rows for session-only US bars.
- **R13, baseline.** A Buy bucket that began before a creation or resume is baseline, even if it closed after it.
- **R20, pause race.** The bot never locks the `bots` row. It re-reads `status` inside the intake transaction, so at most one order from a pass that began before a pause can land.
- **R22.** `inSession` on the instrument's calendar stands in for "`px:last` session = open", because the recorded price view does not keep the session.
- **R6, observing.** An `observing` bot writes skip-shaped decisions with `reasons = ["observing"]`: no order, no reservation, no event. Nothing sets `observing` in 2b.

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Plan resolutions worth knowing, Bot)

## Other owner decisions (ZB5–ZB11)

- **ZB5 Bot-side intake.** The bot places its own orders with a `placeOrder` in tidewatch-bot that runs the service's check order, the shared arithmetic and the C4 lock order in one transaction. There is no HTTP, no credential and no service change for intake. Rejected: a service endpoint with a service token (it breaks "no HTTP between them" and adds a secret) and a Postgres function (a large refactor). Accepted cost: a second implementation of the money and limit checks, pinned by a scenario fixture. The mechanics are on [[paper-trading]].
- **ZB6 Creation.** The service creates Slack Water lazily beside `me`, one per user, inside the trust boundary. Rejected: creation at `serve` start, and a *Create bot* action (slice 6).
- **ZB7 Running from day one.** Status is `running` at creation. A 30-day probation was rejected, because the point of 2b is to watch it trade.
- **ZB8 Web.** A minimal Bots screen. Overview and Trade stay `me` only. Rejected: no web change (hides the bot) and a bot switcher on Trade (muddles the manual account).
- **ZB9 Schema.** Migration F; see [[bot-versions-and-runs]].
- **ZB10 Documents.** The spec session wrote `documents/features/02b-zone-transition-bot.md` and the roadmap and README rows. Builds never edit `documents/` (D17).
- **ZB11 Mockup.** The spec's `mockup.html` is the visual target. Where it differs from the approved mockup's Bots screen, it wins. Where it differs from `DESIGN.md`, `DESIGN.md` wins.

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Chosen design)

**During the build:**
- **OWNER-1.** The preview uses an isolated database, with volumes retained after merge. The live Pause/Resume check runs only after the first entry and the restart check are captured, because a resume moves `status_since` and would drop any Buy run that began earlier.
- **OWNER-2.** "Merge now and continue." E2E-001/002 and the live Pause/Resume part of E2E-003 are recorded as **unverified, not failed**: no Buy transition had occurred after the bot's baseline. The first-entry wait keeps running on the preview, and any entry it captures is added as evidence. Slice 3a's ORCH-19 ("merge it all and continue", 2026-10-11) followed this precedent: its 24 h soak IDs are recorded as unverified at merge, not failed (see [[signals-ingest]]; source: raw/2026-10-11-signals-ingest.md §Concept, ORCH-19).
- **ORCH-6.** An owner-visible revision of PRD §8.4 for an unsupported bot version, accepted pending the owner's veto. See [[bot-versions-and-runs]].

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Owner decisions during the build)

## Orchestrator rulings

- **ORCH-1.** Migration F was planned as MIG steps inside the service plan, but kept its own worktree, branch and PR (see [[centralized-migrations]]).
- **ORCH-2.** The service planner pinned C10's bytes and hash, the C4' text and the route shapes in `contracts.md`. The bot and web planners conformed.
- **ORCH-3 → ORCH-5.** Without a `/trade` read, the Bots screen lost tick-size digits (189.10 showed as 189.1). ORCH-5 lets the web read `GET /trade` **once per Bots screen open**, only for `tradable_instruments`, and never poll it.
- **ORCH-7.** Dependency-gated lanes with smelt bundling (owner choice).
- **ORCH-8.** `limits.max_open` is the string `"6"`: the PRD and C10 win over the intent's numeric `6`. Resume on an `observing` bot answers 409 `bot_status_conflict`.
- **ORCH-10.** Service fix round after an approved r1: the decisions cursor's syntax is decoded before ownership, and its bot binding is checked after the bot resolves. Three performance items became follow-ups.
- **ORCH-12.** Bot fix round after an approved r1: the R2 memo order, "more than 5 minutes" wording, `sqlStateOf` restricted to pg `DatabaseError`, and six zero counts on interrupted runs.
- **ORCH-11.** Preview evidence gates the **merge**, not the PR, following slice 2's ORCH-25 precedent.
- **ORCH-13 / 13a.** Two latent slice-2 test defects in `e2e/src/paper-orders.spec.ts` blocked the full Playwright suite on the fresh preview database. The fixes are test-only; see [[simulation-engine]].

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Orchestrator rulings)

## The `bots` runner (tidewatch-bot)

The runner lives in the new Nx library `packages/bots`. It talks to the database only. There is no HTTP to the service.

- **Placement.** `bots` is the last of the eleven `COLLECTOR_NAMES` (after `sim`), on by default, and holds lock `runner:bots`. It has no venue budget. It reads PostgreSQL, the reference cache and the recorded `px:last` view that `serve` shares with `sim`, never Redis (see [[market-data-worker]], [[redis-market-contract]]).
- **Dependencies.** Disabling `bots` leaves zone bots idle. With `sim` disabled, bot orders stay pending, because `sim` fills them. There is no new environment variable, and compose is unchanged.
- **Cadence.** One pass at start, then every 30 s (`BOTS_EVAL_INTERVAL_MS`) from the previous start. Passes never overlap. Before the first pass, stale `running` runs are swept (see [[bot-versions-and-runs]]).
- **Pass.**
  1. Read the zone bots (`kind = auto`, `template = zone_transitions`, `status` in `running` or `observing`, by `created_at`).
  2. Validate the version (see [[bot-versions-and-runs]]).
  3. Resolve the universe.
  4. Read the latest 49 strip rows per instrument (R4).
  5. Fire the rules.
  6. Check session and price outside any transaction: `inSession`, and a recorded `px:last` that is not stale, with `updated_at` within 120 s. A miss defers with `venue_closed` or `price_unavailable` and writes nothing.
  7. Run the intake (see [[paper-trading]]).
- **Failure isolation.** One bot's failure finishes its run `failed` with the error class (a constructor name, never a message), and the pass moves on. Isolation is per bot, not per instrument (a follow-up).
- **Concurrency.** The store serialises every method on one queue and connection, so `SERVE_POOL_MAX` stays 12. Integration evidence shows the account lock is taken first and that a bot entry and a sim fill serialise in both orders.

(source: raw/2026-10-09-zone-transition-bot.md §API, Bot runtime)

**Metrics** (closed label sets, exported at 0 from start): `bots_passes_total{result}` (`acted`, `noop`, `failed`, `nothing_new`), `bots_runs_total{status}`, `bots_decisions_total{action}` (`buy`, `close`, `skip`), `bots_deferred_total{reason}` (`venue_closed`, `price_unavailable`), `bots_pass_duration_seconds`, and the gauge `bots_running` (observing bots are not counted).

**Logs.** `bots_pass_started` (debug), `bots_run_finished`, `bots_order_placed`, `bots_decision_skipped`, `bots_action_deferred` (once per bot, instrument, rule, run start and reason), `bots_version_unsupported` (warn) and `bots_pass_failed` (error). They never carry a `key` field, a message, a body or a token (source: raw/2026-10-09-zone-transition-bot.md §API, Bot runtime, Metrics and Logs).

### What bot-activity changed in the runner (2026-10-10)

- **Verdicts.** `rules.ts` gained `evaluateRule`, which names why a rule did not fire (`no_rows`, `no_zone`, `run_start_unknown`, `baseline`, `holding` / `no_position` / `pending_order`, `decided`). `fireRule` is now a thin wrapper over it, with unchanged exports and specs. Together with the intake results, each evaluation yields one of fourteen verdicts per universe instrument (see [[bot-watch-verdicts]]).
- **A watch step after the pass.** The bot README now lists a step 8, *Watch*: after the run is finished with its outcomes, its metric and log are written and `lastSeen` advances, the bot overwrites one `bot_watch` row per instrument. A quiet pass with no run still writes the watch, which is the heartbeat. A thrown evaluation error writes no watch.
- **Outcomes on every finished run.** `finishRun` stores the entries in `bot_runs.outcomes` (see [[bot-versions-and-runs]]).
- **One new log event**, `bots_watch_write_failed` (error level). The six `bots_*` metric series and their label sets are unchanged.
- **Unchanged by contract.** `place.ts`, `intake.ts`, `strip.ts`, `universe.ts`, `engine.ts`, `metrics.ts`, `version.ts` and `client-order-id.ts` are byte-identical. For the same inputs, the pass writes the same decisions, orders, runs, counts, logs and metrics as 2b. The rules, cadence and order path did not move (outcome O5).

(source: raw/2026-10-10-bot-activity.md §API, Bot runtime; §Files touched, tidewatch-bot; §Concept, Outcomes)

### What slice 6 kept and added around the 2b pass (2026-10-21)

- **Dispatch by vocabulary (S1, D8).** Each pass reads the auto bots (`kind = auto`, `status IN (running, observing)`) and dispatches by the current version: exactly the C10 v1 config → this 2b evaluation; a `bot-config.v2` config → the general engine (scout, manager, guard; see [[bots-engine]]); anything else → `version_unsupported` as before. Without the worker's general dependencies, the 2b `runPass` runs alone.
- **Unbroken by contract (outcome O7).** Bot code review r3 found the 2b files byte-identical to `ece175a`, and the 2b named specs ("enters once on a buy transition", "baseline at status_since", "exits on sell", "replay after crash") stay green and unrenamed. On the preview the 2b pass kept running (`bots_run_finished` and `bots_order_placed` appeared in the bot log). Slack Water keeps its v1 hash and its decisions keep `rule entry/exit`; legacy bots have no guard.
- ***Upgrade* (D8, ORCH-5a, WEB-OQ-1).** A legacy bot's detail reads "This bot runs the original zone-transition rules (v1). Upgrade to edit it." with *Upgrade to the current vocabulary*. `GET /bots/{id}/upgrade` returns the PRD §4.2.5 translation (four classes at `0.25`, `max_symbols` and `max_candidates` 6 each), shown read-only and saved verbatim as v2 with `probation: false`. `TestBots_Upgrade` and FR-BT-SVC-005 verify it (v2 created, v1 intact). **No real *Upgrade* was saved on the preview**; the mocked editor spec covers the web half.
- **Direct entries reuse the 2b rules (S7).** A rules-only v2 config (`scout.kind = off`, `entry_condition = zone_turns_buy`) enters directly on a strip Buy run, keeping this pass's idempotency key and skip reasons.
- **Legacy reads.** For a v1 bot the new service routes answer: candidates an empty page; attribution weights `"0"`; schedule `scout.kind "off"`, `manager.timeframe "strip"`; universe the translation's.
- **One shared gauge (FU-7).** `bots_running` is now set by both this pass and the general pass, so it alternates between 1 and 2; it is to become one count or two gauges.
- **Mockup drift closed.** The sparkline and the probation tag that the 2b mockup showed but 2b did not build arrived in slice 6 (see [[design-system-decisions]]).

(source: raw/2026-10-21-bots.md §The bot engine, Pass order and Guard; §Concept, Spec decisions S1/S7, Owner decisions D8, Outcomes O7 and ORCH-5/6; §API, Conventions; §Components, Version editor; §Test plan, Defects found on the preview)

## Bots screen (tidewatch-web)

The slice-0 `/bots` placeholder became a Bots screen (`feat-bots/`):
- A list of both bots, with the mono version label `v1·687c`, mode, status, 30-day return, max drawdown, decisions and equity.
- A detail for the selected bot: a strategy sentence derived from the version config, four metric cards (*Equity*, *Return since start*, *Max drawdown*, *Last check*), positions and the decision record.
- *Pause* / *Resume* for Slack Water. The manual bot shows a *Manual* tag and no button.
- `BotsService` polls `GET /bots` and the selected bot's detail, portfolio and first decisions page every 10 s. It reads `GET /trade` once per screen open (ORCH-5).

Overview and Trade still show only `me` (ZB8). Patterns, styles and rendered verification are on [[design-system-decisions]]. The shared decision record and the bot-row copy are on [[decision-record]] (source: raw/2026-10-09-zone-transition-bot.md §Components).

**Since bot-activity (2026-10-10).** The detail of an auto bot gains a **Watch** table under the metric cards and a **Checks** history after the Decision record. The *Last check* card counts deferrals ("6 instruments · 2 deferred · no action") and names a failure class ("last check failed · DatabaseError"), so the 2b ORCH-6 failure is no longer unexplained. The 10 s tick now makes five detail reads plus the list. Details are on [[bot-activity]] (source: raw/2026-10-10-bot-activity.md §Components; §Concept, Problem).

## Test plan and acceptance

There is no CI (D4). All commands run locally.

| Project | Commands and last result |
|---|---|
| Migrations | `make migrate-validate`; `make check-disposable-db` PASS 1016/0, including F's transcript and 14 rolled-back probes |
| Service | `make ci`; `make test-integration` with no `--- SKIP` allowed |
| Bot | `pnpm nx run-many -t lint test typecheck build`; `scripts/sql-integration.sh` (market-data 16, worker 2, sim 17, bots 9, all passing on F) |
| Web | `pnpm nx run-many -t lint test build` (2,287 unit tests at fix-r1); mocked Chromium `e2e/src/bots.spec.ts` 142/142 |

The named acceptance tests are pinned and must not be renamed. Examples: `TestBots_ConcurrentFirstAccess`, `TestBots_ForeignBotIs404`, `TestCloseStampSQL_IsC4Prime`, `TestBotVersion_FixtureHash`, and the bot's Vitest titles `enters once on a buy transition`, `baseline at status_since`, `exits on sell` and `replay after crash` (source: raw/2026-10-09-zone-transition-bot.md §Test plan, Commands and Named acceptance tests).

### Acceptance status (PRD §9)

| ID | Status | Note |
|---|---|---|
| FR-ZB-MIG-001…003 | Passed | Harness PASS 1016/0 |
| FR-ZB-SVC-001…006 | Passed | v1 created as `v1·687c`; gated count 32; CSRF on both POSTs; no secret in logs over the six routes |
| FR-ZB-BOT-001…007, 009, 010 | Passed | Memory-store specs, 30 fixture scenarios and SQL integration on F |
| FR-ZB-BOT-008 | Passed (both repos) | `exit_reason = 'zone'` proven by unit, memory and SQL tests. **No live bot exit has happened yet.** |
| FR-ZB-WEB-001…006 | Passed | Mocked spec 142/142, locally and against the preview build |
| FR-ZB-WEB-007 | In progress at merge; **closed since** | `DESIGN.md` refresh in a separate web docs PR, which shipped as tidewatch-web PR #8 (merge `1689b0c`, 2026-10-09; see [[design-system-decisions]]) |
| FR-ZB-E2E-001 | **Unverified** | Prerequisites were ready. Slack Water's baseline was 15:00:56Z, so the earliest enterable Buy run started on the 16:00Z bar (entry about 17:00Z). By the merge at 17:43Z there were 4 `noop` runs, 0 decisions and a healthy bot. The first-entry wait (60 s poll, 10 h cap) kept running after merge. |
| FR-ZB-E2E-002 | **Unverified** | Depends on the first entry: restart/replay, and a Sell closing with `exit_reason = 'zone'` |
| FR-ZB-E2E-003 | **Partly verified** | The read-only screen equals SQL field by field for both bots. The account was fresh, so positions and decisions were compared as empty tables only. Live Pause/Resume was not run (OWNER-1, then OWNER-2). |
| FR-ZB-E2E-004 | **Not started** | The first week on the owner's stack: never a seventh position, never over the limits, never Gold 96.5 or GO; Trade and Overview for `me` unchanged |
| FR-ZB-DOC-001 | Passed | Per-project README and CLAUDE.md diffs, with fact-check files |
| FR-ZB-DOC-002 | **Deferred** | `tidewatch-apis` is not a Git repository |

(source: raw/2026-10-09-zone-transition-bot.md §Test plan, Acceptance status)

**Other preview results** (Phase A, 2026-10-09T15:16Z, fresh isolated database at F):
- Full Playwright suite: 571 passed, 2 failed, 1 skipped (the gated pause test). Both failures were test defects, fixed in web fix-r2 and ORCH-13/13a, and the fixed specs then passed on the preview. **The whole suite was not re-run end to end after fix-r2.**
- Secret scan of the HTML report, attachments and logs: 0 hits.
- Runner: both bots were created at 15:00:56Z. Passes ran every 30 s, and runs were written only when a strip row advanced (`noop`, `new_bars` 4 then 2), with 0 failed or interrupted runs.
- Both bots' benchmarks exclude NVDA and AAPL, because US `px:last` was absent when the accounts were created (the slice-2 `no_price` rule).

(source: raw/2026-10-09-zone-transition-bot.md §Test plan, Other preview results)

**Assumptions.** A1 (an entry within about 2 minutes of the bucket close) is unverified, because no entry occurred. A2: Alpaca US prices were live on the preview. A3: quantity rounding is covered by the intake fixture and was re-derived by hand in code review (NVDA 187.54 → 15.91700238 shares; PTT 34.28 → 2917 shares). A7: Overview 0-pixel diff. A8: Trade unchanged (source: raw/2026-10-09-zone-transition-bot.md §Test plan, Assumption outcomes).

### Manual reproduction for the open rows

1. **E2E-001.** On a stack with F applied, open Bots once (this creates both bots). Wait for a strip-timeframe Buy run that starts after Slack Water's `status_since` on an open-venue universe instrument. Capture the `indicators` row, the `bot_runs` row, the decision, the order and the fill with timestamps. A read-only capture script is at `.forge/features/zone-transition-bot/evidence/preview/e2e-001-capture.sh`.
2. **E2E-002.** Restart the bot container mid-pass and let it replay. Expect exactly one order per (instrument, zone run). On a Sell transition, expect `exit_reason = 'zone'` on the entry decision.
3. **E2E-003, pause part.** Only after steps 1 and 2: run `bots-live.spec.ts` with `E2E_BOTS_PAUSE=1` on Chromium against a fresh database. Confirm by SQL that Slack Water ends `running`, and that a Buy run that began during the pause is not entered after resume.

(source: raw/2026-10-09-zone-transition-bot.md §Test plan, Manual reproduction)

## Open items

- **Unverified behaviour.** The bot has not yet placed, filled or closed a real order on any stack (E2E-001/002), and the first-week check (E2E-004) has not started. ORCH-6 stands unless the owner vetoes it.
- **Owner action.** Apply migration F to the owner's own database before running the merged service.
- **Known gaps (bot README).**
  - A Buy run whose start falls outside the 49-row window is never entered (R3).
  - A run interrupted less than 5 minutes before a restart stays `running` until a later start (R12).
  - A Buy bucket that began before a creation or resume is baseline even if it closed after it (R13).
  - `exit_reason = 'zone'` applies only to bot exits (see [[decision-record]]).
- **Service follow-ups.**
  - `GET /bots` computes a full `1m` portfolio per bot on every 10 s poll. That is fine at 2 bots; revisit for slice 6. Slice 6 measured 5 bots at p50 17.7 ms / p95 21.1 ms on the preview (see [[bot-versions-and-runs]]).
  - The detail reads `CurrentVersion` twice.
  - If `SummarizeBot` fails after a committed pause or resume, the response is 500 and a retry gets 409. The audit trail stays consistent.
  - Pin a non-ASCII canonical-JSON case (U+2028/2029 escaping) in both repos before a C10 v2.
  - The service README says "any other cursor is 400". That is exact only for the caller's own bots; a binding mismatch on a foreign bot is 404.
- **Bot follow-ups.**
  - Keep intake errors off the pre-existing `runner_failed` path, which prints the message and stack.
  - Failure isolation is per bot, not per instrument.
  - The engine stops only between passes, so a slow-database pass may outlast `serve`'s 10 s shutdown guard.
  - On the unsupported-version path, a `finishRun` failure after `startRun` leaves an orphan `running` run until the next engine start.
- **Web follow-ups** are listed on [[design-system-decisions]].
- **Drift left in `documents/` (D17).** `02-architecture.md` §5.1 still lists three `bot_runs` statuses. `features/06-bots.md` still says auto mode arrives in slice 6, without the 2b exception. The approved mockup's sparkline and probation tag were not built.
- **Preview cleanup pending.** The preview keeps running with retained volumes for the first-entry wait. The `me` account there holds two pending BTC/THB limit buys and 0.0002 BTC from the slice-2 journey. The journey's git-ignored auth file in the web worktree is to be deleted at cleanup.

(source: raw/2026-10-09-zone-transition-bot.md §Open questions)

## Related pages

- [[bot-versions-and-runs]]: the bots, versions and runs model, Pause/Resume and the `/bots` routes
- [[paper-trading]]: the bot-side intake, contracts C4' and C10, and the `sim` runner that fills bot orders
- [[decision-record]]: the bot's decision rows, `policy_result` and `exit_reason = 'zone'`
- [[simulation-engine]]: slice 2, which built the `me` bot and the paper account this slice extends
- [[centralized-migrations]]: migration F and the new required schema version
- [[market-timeseries]]: the `indicators` rows (`cdc_zone`, strip timeframe) the bot reads
- [[market-data-worker]]: the worker that hosts the `bots` runner
- [[redis-market-contract]]: the `px:last` freshness bound the bot reuses through the recorded price view
- [[instrument-master]]: venues, calendars, `lot_size` and the `1d` base that shape universe and quantity
- [[design-system-decisions]]: the Bots screen patterns and the `DESIGN.md` refresh (tidewatch-web PR #8)
- [[forge-preview-gateway]]: the isolated preview where E2E verification runs
- [[gold-feed-xaut-proxy]]: XAU/USD, which is in the default universe
- [[bot-activity]]: the follow-on feature that shows what Slack Water checked and why it did not act
- [[bot-watch-verdicts]]: the fourteen verdicts that name the 2b rules (R3, R6, R13) per instrument
- [[signals-ingest]]: slice 3a, whose ORCH-19 merge followed the OWNER-2 "merge now" precedent
- [[signal-cited-orders]]: slice 4's *Buy with recommendation*, which borrows the ZB4 10%-of-equity rule
- [[bots]]: slice 6, which keeps this pass for v1 and adds the general engine and *Upgrade*
- [[bots-engine]]: the general engine that runs v2 configs beside the 2b pass
