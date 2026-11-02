# Bot activity: Watch and Checks (`bot-activity`)

**Summary**: After slice 2b, the Bots screen showed Slack Water as *Running* with a *Last check* card ("6 instruments · no action"), but nothing said what the bot had looked at or why it did nothing. This feature makes the bot record its own per-instrument **verdict** on every pass and shows it in two new sections of the bot detail: a live **Watch** table and a **Checks** history whose rows expand to the outcomes stored at that check. Migration G (`20261010061500`) adds `bot_watch` and `bot_runs.outcomes`. The service gained three read-only routes and `error` on every run payload, and never computes a verdict. All 33 acceptance IDs passed (FR-BA-E2E-003 with a recorded method deviation). The four PRs merged on 2026-10-10. The owner must apply G to their own database; until then the merged service answers `/ready` 503. Since slice 6 ([[bots]], merged 2026-10-21, not deployed), Watch and Checks also word the general engine's nine new verdicts, Checks is loop-aware, and the bot detail gains Loops, Candidates and Version sections.

**Sources**: `raw/2026-10-10-bot-activity.md`; `raw/2026-10-12-signals-page.md` (the expandable-row move only); `raw/2026-10-21-bots.md` (the slice-6 follow-on only)

**Last updated**: 2026-10-21

---

## Stage, stated precisely

This is the status in `state.json`, last updated 2026-10-10T13:43:01Z (source: raw/2026-10-10-bot-activity.md §Concept, Stage, stated precisely).

| Stage | Status |
|---|---|
| Implemented | All planned steps are done: service MIG1, MIG2 (landing in the migrations repo, ORCH-1) and S1–S5; bot S1–S6; web S1–S8 plus the `DESIGN.md` refresh (FR-BA-WEB-011). Bounded rounds after review: service ORCH-12, bot ORCH-10 (docs), web ORCH-13 (docs and e2e), ORCH-14 and a docs-only W2 round. |
| Verified locally | Every step's contract commands exited 0 on the orchestrator's re-run. Migrations harness 1130 PASS / 0 FAIL; bot `bots:test` 132/132 and bots integration 16/16 on G; web 2,743 unit tests. The C11 fixture is byte-identical in the planning directory, the service and the bot. |
| Reviewed | Plans and code approved for all three projects after bounded rounds (bot plan r3, web plan r2 plus a delta r3; web angular review approved in r2 once the preview transcript was attached). The ORCH-14 deltas were approved by the angular, security, code and design reviewers. |
| Verified on a preview | **Yes**: 33/33, 0 failed, 0 unverified (FR-BA-E2E-003 with a method deviation), on an isolated preview at G, plus an owner-session read-only validation at about 13:37–13:42Z. |
| Merged | **Yes**, 2026-10-10, between 13:41:42Z and 13:42:10Z, on the owner's instruction "merge the PRs in order" (OWNER-1 of this build). Heads were verified equal to the reviewed heads and merged with `--match-head-commit`. No CI is configured on any repo (D4). |
| Running on the owner's own stack | **Not recorded.** The owner must apply G (`make migrate-up` in tidewatch-migrations). |

## Merge record

| Repo | PR | Range (base..PR head) | Merge commit | Files |
|---|---|---|---|---|
| tidewatch-migrations | #6 | `1e115c0..a474a77` | `3ec60a7` (13:41:42Z) | 4 |
| tidewatch-service | #7 | `594548f..14ce781` | `77d8ebf` (13:41:55Z) | 23 (the ORCH-12 fix touched the cursor parse, its tests and two docs) |
| tidewatch-bot | #6 | `ac80b04..b9d6d5e` | `6b8cdb0` (13:41:58Z) | 21 |
| tidewatch-web | #9 | `1689b0c..098b0ef` | `31f9435` (13:42:10Z) | 31 (30 in the S1–S8 lists, plus `DESIGN.md`) |

The merge order was migrations first, then service and bot, then web. Branches were kept for cleanup (source: raw/2026-10-10-bot-activity.md §Concept, Stage, Merged; §Files touched).

## Why the feature exists

The owner's follow-up after slice 2b was: "the Bots screen shows *Running* and a *Last check* card — 6 instruments · no action — but there is no visible log of what it checked or why it didn't act." The intent verified three gaps against the merged 2b code:

- **The bot recorded aggregates only.** A `bot_runs` row was written only when an instrument had a new strip row, at start, or on demand inside an intake that wrote a decision (2b R1), and it carried only `counts`. A quiet pass wrote nothing, deferrals wrote no row, and a rule that did not fire or was suppressed by an existing decision left no trace.
- **The reasons lived only in code.** `fireRule` returned null for five different reasons, and a decision-key hit was a sixth silent exit.
- **The service exposed one run.** `last_run` had no `error`, and no route listed `bot_runs`. A failed run read "last check failed" with no class, and 2b's ORCH-6 left *Last check* "stuck at the first failure" with no explanation.

(source: raw/2026-10-10-bot-activity.md §Concept, Problem)

## Owner decisions BA1–BA5 (confirmed 2026-10-10)

The owner answered five questions one at a time in the Forge Console Spec studio, accepting the recommended option each time, then confirmed the whole intent ("Yes, confirm all").

- **BA1 Both a live Watch and a Checks history; no raw per-pass log.** The Watch answers "why isn't it acting now", and the history reuses the run rows that already exist. Rejected: a per-pass log of about 2,880 near-identical entries per bot per day.
- **BA2 The bot records the verdicts; the service adds only "next bar" and session.** See [[bot-watch-verdicts]].
- **BA3 Placement.** Watch goes under the metric cards, Checks after the Decision record, and a check expands in place to the same per-instrument table as it stood then. Rejected: a separate Activity page, and one Activity block at the bottom (it hides the "now" answer).
- **BA4 Keep everything; no retention job.** About 1 KB per run, roughly 15 MB per bot per year; revisit at slice 6. Run rows must stay anyway, because decisions reference them.
- **BA5 A one-direction mockup** on the real tokens, both themes and every state, browser-verified at 390/600/1080/1440. Where it differs from `DESIGN.md`, `DESIGN.md` wins, except the feature pieces PRD §7.6 names.

**Outcomes O1–O5, all covered and passed:** O1 "why not" on screen within 40 s of the pass (30 s cadence + 10 s poll); O2 every recorded check opens to its outcomes; O3 the verdict is the bot's own and the rule specs are unchanged; O4 alive or broken is visible (heartbeat, stale line, failure class); O5 nothing else moves (rules, intake, order path, cadence and Decision record unchanged; `Me` gains no section; no retention job; `documents/` untouched).

(source: raw/2026-10-10-bot-activity.md §Concept, Chosen design)

**Proposed defaults the build implemented** (not owner decisions): the storage in migration G; a verdict vocabulary equal to the real code branches; the watch written once at the end of a successful evaluation, outside any transaction; the web copy; and the volume of six overwritten watch rows per bot plus one jsonb array per run. Details are on [[bot-watch-verdicts]] (source: raw/2026-10-10-bot-activity.md §Concept, Proposed defaults).

## What each project gained

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-migrations` | Migration G (`20261010061500`): `bot_watch` and `bot_runs.outcomes` | [[centralized-migrations]], [[bot-watch-verdicts]] |
| `tidewatch-service` | `GET /bots/{id}/watch`, `/runs` and `/runs/{run_id}`; `error` on every run payload; the runs cursor; the C11 fixture; `RequiredSchemaVersion` moved to G | [[bot-versions-and-runs]], [[bot-watch-verdicts]] |
| `tidewatch-bot` | `evaluateRule` and the fourteen verdicts, outcomes on every finished run, the `bot_watch` write, `HAS_DECISION` returning an id, the log event `bots_watch_write_failed` | [[bot-watch-verdicts]], [[market-data-worker]] |
| `tidewatch-web` | The Watch and Checks sections, the expandable-row pattern, the failure class and deferrals in the *Last check* note, and the `DESIGN.md` refresh | [[design-system-decisions]] |

(source: raw/2026-10-10-bot-activity.md, summary block; §Database; §API; §Components; §Files touched)

## Owner-visible revision and orchestrator rulings

- **ORCH-6 (owner-visible revision, accepted pending the owner's veto).** PRD §7.7 says *Try again* moves focus to the section heading. The section-level *Try again* does that. The **detail-row** *Try again* instead moves focus to that row's *Hide* button before calling `retryRun()`, which keeps a keyboard user at the row instead of jumping to the Checks heading many rows above. The design and angular reviewers agreed.
- **ORCH-1.** Migration G was planned as MIG steps inside the service plan, because the validators accept only registered projects. The migrations repo kept its own worktree, branch and PR, and merged first (see [[centralized-migrations]]).
- **ORCH-2 / ORCH-3.** The service planner pinned C11's bytes and hash, the §6.1 wire shapes and the writer semantics in `contracts.md`, and the bot and web planners conformed. G's version was an output of MIG1, appended to `contracts.md` as r3.
- **ORCH-4.** Path correction: the build prompt's `internal/repository/postgres/bots.go` is `bot.go`; `RequiredSchemaVersion` is in `internal/platform/postgres/schema.go`.
- **ORCH-5 / ORCH-5a.** Then-mode decoration reuses data already on the screen (see [[bot-watch-verdicts]]).
- **ORCH-7 / ORCH-9.** The approved service and web plans folded their should-fix items and were re-reviewed as deltas. ORCH-7 added the jsonb key-order note to the contract.
- **ORCH-8.** Dependency-gated lanes with bundle mode "smelt" (owner choice); no plan ended up bundling.
- **ORCH-10.** Bot doc-only round: the fixtures README had stated C11's direction backwards (the bot writes, the service reads).
- **ORCH-11.** `TestSubscriber_Restart_Resubscribes` is a pre-existing flake (5/120 failures at base). An integration failure caused only by it was re-run once. A separate session fixed it test-side in tidewatch-service#6 (`eeaf265`); the build branch was not rebased onto it.
- **ORCH-12.** Service fix round after approval: a forged cursor with `t` before PostgreSQL's minimum timestamp returned 500; `parseDecisionsCursor` now rejects `t < 0` as 400 (see [[bot-versions-and-runs]]).
- **ORCH-13 / ORCH-14.** Web fix rounds limited to docs, e2e and accessibility: two announced placeholder dashes were hidden (W1), two test defects fixed (D1/D2), and a suspected polling defect (D3) was diagnosed as **not a product defect** (Chromium DevTools labels fully read responses `ERR_ABORTED`).

(source: raw/2026-10-10-bot-activity.md §Concept, Owner-visible revision and Orchestrator rulings)

## Web: the Watch and Checks sections

Both sections live inside `app-bot-detail`, in this order: the `.metric-strip`, **`app-bot-watch`**, Positions, `app-decision-record`, **`app-bot-checks`**. Both render only for `kind = auto`. With *Me* selected neither renders and no watch or runs request is made (source: raw/2026-10-10-bot-activity.md §Components, Placement).

**Watch (`app-bot-watch`).**
- Head note: "Checked {time} · baseline since {d MMM HH:mm}"; when paused, "Paused since {…} · last checked {…}"; when observing, "Observing · checked {…} · baseline since {…}"; with no rows, "No check yet".
- **Stale line.** "No check since {HH:mm}. The bot runner may be off." It shows only while `bot.status = running` and `generated_at − checked_at > 120 s`, strictly (120 s is not stale, 121 s is), and clears when a newer `checked_at` arrives. For an observing bot it is not shown, as the PRD says, although an observing bot is evaluated every pass too (N3).
- States: "Loading watch…"; "Watch couldn't load." with *Try again*; "No check yet. Slack Water checks every 30 s once it runs."
- Columns: Instrument, Last bar, Zone, Verdict and Next. The verdict copy is on [[bot-watch-verdicts]]. *Next* reads, for example, "{HH:mm}" / "bar closes" or "{EEE HH:mm}" / "closed · opens", or "—" / "no session state".

**Checks (`app-bot-checks`).**
- One row per check that saw a new bar or wrote a decision, newest first, 20 at a time with *Load more*. Columns: When, Result ("No action", "1 entry", "2 entries · 1 skip", "Failed" with the error words, "Checking now"), Instruments, New bars, Deferred, and a *Details* / *Hide* button.
- A check expands in place to the per-instrument table as it stood at that check, fetched once per `run_id`; collapsing and re-expanding reads nothing. A check still running reads "Checking now" and is fetched once it finishes. Other detail outcomes: "The check failed before it evaluated an instrument · {error}", "No instrument was evaluated", and "This check couldn't load." with *Try again* (focus per ORCH-6).
- States: "Loading checks…"; "Checks couldn't load." with *Try again*; "No checks yet. A check is recorded when a new bar arrives or a decision is written."

**Last check card** (`util/bot-view.ts`). Deferrals come after the action parts and are omitted at zero ("6 instruments · 2 deferred · no action", "1 entry · 2 deferred"). A failed run reads "last check failed · {error words}", where `interrupted` reads "interrupted", `version_unsupported` reads "version unsupported", and any other class appears as is (for example `DatabaseError`).

**Store (`bots.service.ts`).** Two more `httpResource`s, the watch and the first runs page, reload with the detail trio on the 10 s tick: five reads plus the list. The tick skips while any of the five is loading. A selection change clears them and cancels a *Load more* in flight; a failed background reload keeps the last data. The watch and runs requests key on a primitive `selectedKind`, so the 10 s list reload does not re-issue and abort them (review-1 W3).

**Compatibility.** A web build against a service without these routes gets 404 and shows "Watch couldn't load." / "Checks couldn't load." while the rest of the detail renders.

(source: raw/2026-10-10-bot-activity.md §Components; §Concept, Proposed defaults, Web copy; §Concept, Plan resolutions, Web; §API, Compatibility)

The styles, the reusable expandable-row pattern and the `DESIGN.md` refresh are on [[design-system-decisions]].

## Test plan and acceptance

There is no CI (D4); all commands run locally. Migrations: `make migrate-validate` and `make check-disposable-db` (1130 PASS / 0 FAIL). Service: `make ci` and `make test-integration` with no `--- SKIP` allowed. Bot: `pnpm nx run-many -t lint test typecheck build` and `scripts/sql-integration.sh` (bots integration 16/16 on G). Web: `pnpm nx run-many -t lint test build` (2,743 tests), the mocked Chromium `e2e/src/bots.spec.ts` (260/260), and the full Playwright suite against a preview (source: raw/2026-10-10-bot-activity.md §Test plan, Commands).

The named acceptance tests must not be renamed. Examples: `TestWatchEntry_FixtureHash`, `TestRunsCursor_KindSeparation`, `TestDecisionsCursor_ChecksumGolden`, `TestBotWatch_RedisAbsent`, `TestRouter_ForcedChangeGatesNewRoutes` (35), and the bot's `writes the watch in one statement outside any transaction, after finishRun, without the account lock` (source: raw/2026-10-10-bot-activity.md §Test plan, Named acceptance tests).

### Acceptance status (PRD §9): 33/33 passed

| IDs | Status | Evidence / note |
|---|---|---|
| FR-BA-MIG-001…003 | Passed | Harness 1130/0; down to F and up restores G; `/ready` 503 on F only, 200 at G |
| FR-BA-BOT-001…008 | Passed | `evaluateRule` titles; 14 `records …` titles; C4 lock probes on G; outcomes full, partial and `[]`; specs +2,942/−0; C11 three-way `cmp` |
| FR-BA-SVC-001…006 | Passed | Named tests; 35 gated routes; golden decisions checksum; `error` value `DatabaseError` proven end to end |
| FR-BA-WEB-001…012 | Passed | 64 captures with 0 horizontal page scroll; minimum contrast 4.79:1 over 392 measurements; axe 0 violations; 0 clipping; `DESIGN.md` refresh checked. WEB-010: no screen-reader run (optional) |
| FR-BA-E2E-001 | Passed | Watch = `bot_watch` 6/6 rows, read 5.3 s (dark) and 6.5 s (light) after the pass |
| FR-BA-E2E-002 | Passed | Expanded checks = `bot_runs.outcomes` 6/6, both themes, one detail request per expansion |
| FR-BA-E2E-003 | Passed with deviation | Stale line at 120.6 s with the bot stopped; cleared on the first read after restart. The **whole bot container** was stopped for 148.5 s, because `MARKET_DATA_COLLECTORS` could not be changed without editing helper-managed compose files. Passes were shown by SQL and metrics, because `bots_pass_started` is debug-level. |
| FR-BA-E2E-004 | Passed | Pause froze the rows with the paused note; Resume rewrote all 6 rows with `baseline_at` = the new `status_since` |

(source: raw/2026-10-10-bot-activity.md §Test plan, Acceptance status)

**Preview.** An isolated preview (compose project `forge-0199b29a-bact-642f95ae`, fresh database at G) ran Phases A, B and C. Live verdicts seen were only `no_rows`, `no_zone`, `baseline` and `no_position`. The owner-session validation found 11 Checks rows equal to `bot_runs`, the Watch equal to `bot_watch` on the same pass, *Next* equal to `px:last`, and polling at 10.0 s with all five reads. The preview details and the admin-password restore are on [[forge-preview-gateway]] (source: raw/2026-10-10-bot-activity.md §Test plan, Preview phases).

**Assumptions A1–A6 all held.** A2 (`next_bar_at` = the next UTC hour) held for 24/7 crypto but was not exercised for US or SET, which were closed (weekend). A3 (the 120 s stale threshold): 48 passes averaged about 18 ms. A5: outcomes at most 637 B (source: raw/2026-10-10-bot-activity.md §Test plan, Assumption outcomes).

### Manual reproduction

1. With G applied and the bot running, open Bots and select Slack Water. Within 40 s of a pass, compare the Watch rows with `SELECT … FROM bot_watch WHERE bot_id = <id>`. Every row's `evaluated_at` should equal the head note's "Checked" time.
2. Expand the newest check and compare it with `SELECT outcomes FROM bot_runs WHERE run_id = <id>`. Expect one detail request, and none on collapse and re-expand.
3. Stop the bots runner (or the worker) for more than 2 minutes while Slack Water is `running`. The stale line appears once `generated_at − checked_at > 120 s` and clears after restart.
4. Pause: the rows freeze and the note reads "Paused since …". Resume: the next pass rewrites all rows with `baseline_at` = the new `status_since`. This moves the baseline, so a Buy run that began earlier is never entered (2b OWNER-1 caveat).

(source: raw/2026-10-10-bot-activity.md §Test plan, Manual reproduction)

## Open items

- **Owner veto pending:** ORCH-6 (the detail-row *Try again* focuses *Hide*).
- **Not observed on any stack:** ten of the fourteen verdicts (all but `no_rows`, `no_zone`, `baseline` and `no_position`) were exercised only by specs and mocks. A first bot entry, still unverified from 2b (FR-ZB-E2E-001/002, see [[zone-transition-bot]]), would be the first live `placed`. The "Checking now" and detail-loading states are DOM-verified only.
- **Web follow-ups:** security L1–L3 (`readNullable` for nullable watch keys and `checked_at`, an identifier-shape filter for `error`, a `run_id` UUID check); unused `WATCH_COPY.region` / `CHECKS_COPY.region`; the three-state `WatchCellView.hidden`; unasserted focus after *Load more*; e2e fixture realism; moving the expandable-row styles to `table.css`; graduating `formatClockSeconds`; making `e2e/tsconfig.json` type-check (20 errors at base); and, optionally, sending only `x-tidewatch-request` in the bots-live re-read.
- **Closed by slice 4 (2026-10-12):** the expandable-row styles moved to `table.css` when the Signals detail row became their second consumer. That was 11 rules, unscoped, and `.bot-detail .more-row` was renamed to the shared `.more-row`. The Bots captures stayed 0-pixel identical (144/144). The Signals detail row reuses the same behaviour: it is inserted empty and filled one task later, it is read once per id, and its *Try again* focuses that row's *Hide* (ORCH-6). See [[signals-page]] and [[design-system-decisions]] (source: raw/2026-10-12-signals-page.md §Components, Styles and Expanded row; §Test plan, Acceptance status FR-SP-WEB-010; §Cross-cutting links).
- **Service follow-ups:** a shared "That check doesn't exist." constant; the README's 2b route list omits portfolio (pre-existing); a usable `px:last` whose session normalises to `unknown` passes its `next_open_at` through.
- **Bot follow-ups:** `bots_watch_write_failed` has no once-only memo; formatting-only reflows near the intake in `pg-store.ts`; the intake-deferral sub-case of `records deferred …` stubs the intake.
- **Known gaps carried from 2b:** a Buy run missed for 49 strip rows is never entered (R3); an interrupted run under 5 minutes old stays `running` until a later start (R12); failure isolation is per bot, not per instrument.
- **Scale, to revisit at slice 6:** BA4 keeps every run's outcomes; `GET /bots` still computes a `1m` portfolio per bot on every poll. Slice 6's Scout/Guard loops and *Run now*, and slice 7's stats, are expected to reuse the watch and outcomes shapes.
- **What slice 6 did (2026-10-21).** The general engine reuses the watch and outcomes shapes, extended to 23 verdicts (C11') and a `15m` timeframe (see [[bot-watch-verdicts]]). `watch-view.ts` words the nine new verdicts ("Watching / waits for …", "Gated / …", "Entered", "Expired / TTL | invalidated", "Added", "Trimmed", "Exited", "Protected / stop {price} …", "No candidate"), and `checks-view.ts` is loop-aware. The detail's sections are now figures, Loops, Candidates, Version, Watch, Positions, Decision record and Checks; the manual bot shows none of Loops, Candidates and Version. `BotsService` reloads the selected auto bot's seven reads together (detail, portfolio, decisions, watch, checks, schedule, candidates) every 10 s. Retention is still deferred by design (no retention job), and `GET /bots` measured p50 17.7 ms with 5 bots on the preview. The runs cursor (`R`) now has a sibling, the candidates cursor (`C`) (source: raw/2026-10-21-bots.md §Components, Bots screen and Data layer; §API, Behaviour worth knowing; §Open questions, Deferred by design).
- **Drift left in `documents/` (D17):** the 2b brief has no line about bot activity.
- **Owner action and rollout.** Apply G to the owner's own database (`make migrate-up` with their `DATABASE_URL`) before running the merged service; `/ready` stays 503 until then. G is additive with no backfill. The rollout order was G, then service and bot (either order), then web. Rolling back the bot stops the watch writes, and after 120 s the stale line shows the honest state. Rolling back the service makes the web show the sections' error state.

(source: raw/2026-10-10-bot-activity.md §Open questions)

## Related pages

- [[bot-watch-verdicts]]: the fourteen verdicts, `bot_watch`, `bot_runs.outcomes`, contract C11 and the watch route
- [[zone-transition-bot]]: Slack Water and the 2b rules the verdicts name
- [[bot-versions-and-runs]]: `bot_runs` with `outcomes` and `error`, and the runs routes
- [[decision-record]]: the decisions the outcomes point to, and the then-mode decoration
- [[centralized-migrations]]: migration G and the new required schema version
- [[design-system-decisions]]: the expandable-row pattern and the `DESIGN.md` refresh
- [[market-data-worker]]: the `bots` runner that writes the watch
- [[redis-market-contract]]: `px:last` session decoration and Redis-absent degradation
- [[forge-preview-gateway]]: the isolated preview, Phases A–C and the admin-password restore
- [[paper-trading]]: the C4 lock order the watch write stays outside
- [[signals-page]]: slice 4, whose Signals detail row became the expandable row's second consumer
- [[bots]]: slice 6, whose general engine extends the verdicts and adds Loops, Candidates and Version
