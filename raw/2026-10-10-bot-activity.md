# Bot activity: what Slack Water checked and why it didn't act (`bot-activity`, Watch + Checks)

> After slice 2b the Bots screen showed Slack Water as *Running* with a *Last check* card ("6 instruments · no action"), but nothing said what the bot had looked at or why it did nothing. This feature makes the bot record its own per-instrument **verdict** on every pass and shows it in two new sections of the bot detail. The bot evaluates each universe instrument through a new `evaluateRule` that names one of fourteen verdicts (for example `baseline`: the Buy run began before the bot's `status_since`). It overwrites one `bot_watch` row per (bot, instrument) after each successful evaluation and stores the same entries in `bot_runs.outcomes` when a run finishes. Migration G (`20261010061500`) adds both objects. The service gained three read-only routes (`GET /bots/{id}/watch`, `/runs`, `/runs/{run_id}`), `error` on every run payload, and session / next-bar decoration taken from `px:last`; it never computes a verdict. The web gained a **Watch** table under the metric cards (with a heartbeat note and a stale line after 120 s without a pass) and a **Checks** history after the Decision record, where a check expands in place to its stored outcomes. The *Last check* note now counts deferrals and names a failure class. `DESIGN.md` gained the reusable expandable-row pattern. All 33 acceptance IDs passed: the component IDs through each project's tests and the mocked suite run against the preview build, the four end-to-end IDs on an isolated preview (FR-BA-E2E-003 with a recorded method deviation). The four PRs were merged on 2026-10-10 between 13:41:42Z and 13:42:10Z on the owner's instruction: tidewatch-migrations #6 (merge `3ec60a7`), tidewatch-service #7 (`77d8ebf`), tidewatch-bot #6 (`6b8cdb0`) and tidewatch-web #9 (`31f9435`). The owner must apply G to their own database; the merged service answers `/ready` 503 until then.

**Sources (inputs to this document).**
- Spec: `/Users/maichinu/tidewatch/tidewatch-specs/bot-activity/build-prompt.md`, `intent.md` (BA1–BA5, O1–O5, proposed defaults), `prd.md` (§4–§9, A1–A6), `mockup.html` (the chosen visual target, BA5). Fingerprints verified at build start: intent `d54d6769…73fb`, prd `1c72a561…3ab2`, mockup `76c4a91c…4c44`.
- Build record: `/Users/maichinu/tidewatch/.forge/features/bot-activity/state.json` (log, per-project execution, reviews, `runtime.preview`, follow-ups), `verification.md` (33/33 matrix, A1–A6, follow-ups, rollout), `planning/cross-plan-decisions.md` (ORCH-1…14, ORCH-5a), `planning/tidewatch-service/contracts.md` (r1–r3: C11, §6.1, G's version), `review/<project>/*.md`, `evidence/preview/phase-a|b|c/index.md`.
- Plans (under `/Users/maichinu/tidewatch/.forge/docker/runs/bact-642f95ae/worktrees/`): `329891b601/.plans/bot-activity.md` (service + migration G: MG1–MG7, SA1–SA9, R1–R11), `6945fd5d6c/.plans/bot-activity.md` (bot: R-BA1…R-BA13), `5eb4e5c7ea/.plans/bot-activity.md` (web: BAW-1…BAW-10, WC-1…WC-8, drift rulings).
- Merged code, read at the PR heads: migrations `…/worktrees/b7ddc75378`, service `…/329891b601`, bot `…/6945fd5d6c`, web `…/5eb4e5c7ea` (each project's `CLAUDE.md` was also read).

## Concept

### Stage, stated precisely

| Stage | Status (state.json, last update 2026-10-10T13:43:01Z) |
|---|---|
| Implemented | All planned steps are done. Service: MIG1, MIG2 (landing in the migrations repo, ORCH-1) and S1–S5. Bot: S1–S6. Web: S1–S8, plus the `DESIGN.md` refresh (FR-BA-WEB-011, `d0f8408`). Bounded rounds after review: service ORCH-12 (`14ce781`); bot ORCH-10 docs (`b9d6d5e`); web ORCH-13 docs and e2e (`d44f655`), ORCH-14 (`5b8cb7c`) and a docs-only W2 round (`098b0ef`). |
| Verified locally | Every step's contract commands exited 0 on the orchestrator's re-run. Migrations harness: 1130 PASS / 0 FAIL. Bot: `bots:test` 132/132 at `a9502c6`; `sql-integration.sh` 16/16 bots integration specs on G. Web: 2,743 unit tests (82 files) at `5b8cb7c`. The C11 fixture is byte-identical in the planning directory, the service and the bot (sha256 `9bec3bd8…cbc6`). |
| Reviewed | **Plans:** service APPROVED r1 (0/5/12), with a delta r2 after ORCH-7. Bot: r1 and r2 CHANGES REQUESTED, r3 APPROVED. Web: r1 CHANGES REQUESTED (3/8/8), r2 APPROVED (0/3/5), r3 delta APPROVED after ORCH-9. **Code:** service code and security APPROVED in r1; delta r2 on `14ce781` APPROVED. Bot code and security APPROVED in r1; doc delta r2 APPROVED. Web: security r1 APPROVED (3 low); code r1 APPROVED with 2 should-fix; angular r1 CHANGES REQUESTED on its evidence gate only, then r2 APPROVED with the preview transcript; design r1 APPROVED (0/1/6, W1). ORCH-14 deltas APPROVED: angular r3, security r2, code r3, design r2. |
| Verified on a preview | Yes: 33/33 (FR-BA-E2E-003 with a method deviation), 0 failed, 0 unverified. Isolated preview (compose project `forge-0199b29a-bact-642f95ae`, fresh database at G), Phases A, B and C, plus an owner-session read-only validation at about 13:37–13:42Z. See Test plan. |
| Merged | Yes, 2026-10-10, in order: migrations#6 at `a474a77` (merge `3ec60a7`, 13:41:42Z); then service#7 at `14ce781` (`77d8ebf`, 13:41:55Z) and bot#6 at `b9d6d5e` (`6b8cdb0`, 13:41:58Z); then web#9 at `098b0ef` (`31f9435`, 13:42:10Z). The owner gave the instruction in chat ("merge the PRs in order", recorded as OWNER-1 of this build). Heads were verified equal to the reviewed heads and merged with `--match-head-commit`. Merge commits; branches kept for cleanup. No CI is configured on any repo (D4). |
| Running on the owner's own stack | Not recorded. The owner must apply G (`make migrate-up` in tidewatch-migrations). |

### Problem

The owner's follow-up after slice 2b was: "the Bots screen shows *Running* and a *Last check* card — 6 instruments · no action — but there is no visible log of what it checked or why it didn't act." The intent verified this against the merged 2b code:

- **The bot recorded aggregates only.** A `bot_runs` row was written only when an instrument had a strip row newer than the runner's in-memory last-seen `ts` (about hourly for 1h instruments, daily for PTT.BK), at start, or on demand inside an intake that wrote a decision (2b R1). It carried `counts = {instruments, new_bars, entries, exits, skips, deferred}`. A quiet pass wrote nothing. Deferrals wrote no row. A rule that did not fire, or was suppressed by an existing decision, left no trace. `bots_pass_started` is a debug log.
- **The reasons lived only in code.** `fireRule` returned null for five different reasons, and a decision-key hit (R6) was a sixth silent exit. The pass could not tell them apart. The baseline rule (R13: a Buy bucket that began before a creation or resume is never entered) is the most common reason the owner would ask about.
- **The service exposed one run.** `last_run` on `GET /bots` and `GET /bots/{id}` had no `error`, and no route listed `bot_runs`. A failed run read "last check failed" with no class. 2b's ORCH-6 (one failed run per unsupported version) left *Last check* "stuck at the first failure" with no explanation.

### Chosen design (owner decisions BA1–BA5, confirmed 2026-10-10)

The owner answered five questions one at a time in the Forge Console Spec studio, accepting the recommended option each time, then confirmed the whole intent ("Yes, confirm all").

- **BA1 Both a live Watch and a Checks history; no raw per-pass log.** The Watch answers "why isn't it acting now"; the history reuses the run rows that already exist. Rejected: a per-pass log, about 2,880 near-identical entries per bot per day.
- **BA2 The bot records the verdicts; the service adds only "next bar" and session.** The screen exists to explain the bot, so it must show what the bot computed. A second implementation would get rules such as R13's bucket-start baseline subtly wrong. 2b had already paid for one second implementation (ZB5, the intake).
- **BA3 Placement.** Watch goes under the metric cards, Checks after the Decision record, and a check expands in place to the same per-instrument table as it stood then. Rejected: a separate Activity page (a route, polling and states for no gain at two bots), and one Activity block at the bottom (hides the "now" answer).
- **BA4 Keep everything; no retention job.** About 1 KB per run, roughly 15 MB per bot per year; revisit at slice 6. Run rows must stay anyway, because decisions reference them.
- **BA5 A one-direction mockup** on the real tokens, both themes, every state, with the Checks expansion working, browser-verified at 390/600/1080/1440. Where it differs from `DESIGN.md`, `DESIGN.md` wins, except the feature pieces PRD §7.6 names.

**Outcomes (intent O1–O5), all covered and passed (verification.md):** O1 "why not" on screen within 40 s of the pass (30 s cadence + 10 s poll); O2 every recorded check opens to its outcomes; O3 the verdict is the bot's own and the rule specs are unchanged; O4 alive or broken is visible (heartbeat, stale line, failure class); O5 nothing else moves (rules, intake, order path, cadence and Decision record unchanged; `Me` gains no section; no retention job; `documents/` untouched).

### Proposed defaults the build implemented (confirmed as defaults, not owner decisions)

- **Storage.** Migration G `bot_watch_and_run_outcomes`: `bot_watch` with primary key `(bot_id, instrument_id)` and pointer columns without FKs, plus `bot_runs.outcomes jsonb NOT NULL DEFAULT '[]'`.
- **Verdict vocabulary = the real branches** (fourteen; see API → Bot runtime). `rules.ts` gains `evaluateRule`, and `fireRule` becomes a thin wrapper so its specs stay.
- **When the bot writes.** The watch is written once at the end of a successful evaluation, outside any transaction, after the run is finished. A thrown error finishes the run `failed` with the outcomes gathered so far and leaves the watch as it was. A version-unsupported run carries `outcomes = []`. Paused bots are not evaluated, so their rows stay as of the last pass.
- **Web copy.** Head note "Checked 15:10:30 · baseline since 14:02". Stale line "No check since 15:08. The bot runner may be off." Checks are listed 20 at a time with *Load more*. The *Last check* note reads "6 instruments · 2 deferred · no action" and "last check failed · DatabaseError" (`interrupted` and `version_unsupported` read "interrupted" and "version unsupported"). Both sections are absent for `Me`.
- **Volume.** Six watch rows per bot, overwritten; one jsonb array of about six entries per run; no index beyond the primary key and F's `(bot_id, started_at DESC)`.

### Cross-project contracts (`planning/tidewatch-service/contracts.md`, r1–r3)

- **C11 `bots-watch-entry.v1.json`** (new; the C10 pattern).
  - Canonical bytes: 11,941 bytes, ASCII, LF, 2-space indent, file sha256 `9bec3bd8ad5e5aaa1855f29b0d261c475b47795fd2706fe812639699bd94cbc6`.
  - Byte-identical copies: service `internal/trading/testdata/bots-watch-entry.v1.json` (pinned by `TestWatchEntry_FixtureHash`) and bot `packages/bots/fixtures/bots-watch-entry.v1.json` (pinned by `bots-watch-entry-fixture.spec.ts`, 4 titles). Copy with `cp`, never re-serialise. A change is a contract change in both repos at once.
  - Keys: `contract`, `fixture`, `spec`, `instant_format`, `fields` (the 14 WatchEntry names in order), `types`, `timeframes`, `zones`, `rules`, `verdicts` (the per-verdict table), `reasons` (`empty`, `deferred`, `skipped`, `observed`), `reason_rules`, `examples` (16 constructed entries covering every verdict, both deferral reasons and both skip shapes).
  - **Instant format.** Inside `bot_runs.outcomes`: RFC 3339 UTC with `Z`, a millisecond fraction only when non-zero (the bot's `formatTs`, 2b R7). Instants the service renders from `timestamptz` columns use Go's RFC 3339 with up to 9 trimmed fraction digits. Consumers compare instants, never text.
  - **r2 clarification (ORCH-7).** The run detail returns `outcomes::text`, so each entry's keys arrive in jsonb's normalised order (shorter keys first, then bytewise), not C11 `fields` order. Consumers parse and compare values.
- **§6.1 wire shapes** (see API).
- **G's version** `20261010061500` was an execution output of MIG1 (ORCH-3), appended to `contracts.md` as r3.
- **Unchanged:** C3–C10, the C4 lock order, the error envelope, snake_case bodies, the gated route chain, ownership as one indistinguishable 404. No new Redis key, channel, `/ws` message, environment variable, error code or metric.

### Owner-visible revision and owner decisions during the build

- **ORCH-6 (owner-visible revision, accepted pending the owner's veto).** PRD §7.7 says *Try again* moves focus to the section heading. The section-level *Try again* does exactly that. The **detail-row** *Try again* instead moves focus to that row's *Hide* button, which stays in the DOM, before calling `retryRun()`. This keeps the keyboard user at the row instead of jumping to the Checks heading many rows above. The design and angular reviewers agreed; the design review recorded the keyboard walk for both cases.
- **OWNER-1 (this build).** "Merge the PRs in order", given after the owner-session live validation.
- **Preview admin password (owner request, 11:45Z).** See Test plan → Preview operational notes.

### Orchestrator rulings (ORCH-1…14)

- **ORCH-1.** Migration G was planned as MIG steps inside the service plan, because the validators accept only registered projects (`workspace.json` registers web, service and bot). The migrations repo kept its own worktree (`b7ddc75378`), branch and PR, and merged first. MIG billets live in the service namespace.
- **ORCH-2.** The service planner pinned C11's bytes and hash, the §6.1 shapes and the `bot_watch` / `outcomes` writer semantics in `contracts.md`; the bot and web planners conformed before returning ready.
- **ORCH-3.** G's version is MIG1's output (`evidence/tidewatch-service/MIG1/required-schema-version.txt`); service S2 and the bot harness read it at execution.
- **ORCH-4.** Path correction: the build prompt's `internal/repository/postgres/bots.go` is `bot.go`; `RequiredSchemaVersion` is in `internal/platform/postgres/schema.go`.
- **ORCH-5, amended by ORCH-5a (web review-1 B3).** PRD §7.3 specifies only *now*-mode copy, and outcomes carry only the `decision_id` / `order_id` pointers. In *then* mode (an expanded check), `decided` and `placed` are decorated exactly like *now* mode **when the pointer matches data already loaded on the screen** (the Decision record's loaded decisions, or the current watch item's decoration). No request is made to decorate. With no match they read "a decision exists for this bar" and "{buy | close} order placed". The mockup's expanded 15:00 check had shown a decorated ETH row, which triggered the amendment.
- **ORCH-6.** Detail-row focus (above).
- **ORCH-7.** The service plan (approved r1) folded five should-fix verification gaps and added the jsonb key-order note to contracts r2. It was re-reviewed as a delta, not a fix loop.
- **ORCH-8.** Execution mode: dependency-gated lanes. Service MIG1 → MIG2 → S1…S5. Bot S1–S3 after service plan approval, S4 after MIG1, S5 after service S1, S6 after S4 + S5. Web S1–S6 on mocks after service plan approval, S7 after service S2–S4, S8 last. Bundle mode "smelt" (owner choice); no plan ended up bundling (bot R-BA13: no compliant bundle).
- **ORCH-9.** The web plan (approved r2) folded three should-fix items, including the expected change to the `bot-view.spec.ts:474` row ("4 instruments · 2 deferred · no action") and the corrected count of 20 pre-existing e2e type errors at base.
- **ORCH-10.** Bot doc-only round after APPROVED reviews: the fixtures README stated C11's direction backwards (the bot writes, the service reads); the README's `nothing` row, merge-order line and "not successful evaluations" wording were fixed.
- **ORCH-11.** `TestSubscriber_Restart_Resubscribes` (`internal/platform/redis`, byte-identical to base) is a pre-existing flake: it failed 5/120 at base and 8/120 in the build worktree (miniredis Up-after-resubscribe race). An integration failure caused only by it was re-run once. A separate session fixed it test-side and merged tidewatch-service#6 (`eeaf265`; `waitUntil` Up; 6/120 failures at base, 0/360 after). The build branch was not rebased onto it (no file overlap). A metrics-port "address in use" bind failure under concurrent container load (service S2 run 1) was treated the same way.
- **ORCH-12.** Service bounded fix round after APPROVED reviews. Security L1: a forged cursor with `t` before PostgreSQL's minimum timestamp reached the query and returned 500. `parseDecisionsCursor` (shared by the runs cursor) now rejects `t < 0` as 400; checksum bytes and every issued cursor are unchanged (`TestParseDecisionsCursor_NegativeT`, `TestService_BotCursors_NegativeT`). Two doc fixes: "the nine `/bots` routes" is now "six in 2b, three in bot-activity", and only a read error logs `last_price_read_failed`.
- **ORCH-13.** Web review round 1 fix, docs and e2e only, so the reviewed app code and the preview's web image did not change:
  - the README observing-note form;
  - the bots-live empty-Checks branch now asserts against the newest `/runs` body, because it would race on a fresh database;
  - clock slack in the gated Pause step.
- **ORCH-14.** Web fix round 2:
  - **W1:** two placeholder dashes were announced. The Checks *Deferred* zero now renders `<span aria-hidden="true">—</span><span class="sr-only">0</span>`, and the Watch *Next* "—" is `aria-hidden` because its second line carries the words. No visual change.
  - **D1/D2:** test defects in `bots-live.spec.ts`: an anchored caption regex against untrimmed text, and an unguarded `json()` on a dropped body.
  - **D3:** a candidate polling defect (the Watch refreshing after 10/20/30 s) was diagnosed as **not a product defect**. Chromium DevTools labels fully-read responses `ERR_ABORTED`; the page aborts nothing and every tick issues all five reads. Regression specs were added.
  - Then the `DESIGN.md` refresh, checked by the design reviewer.

### Plan resolutions worth knowing (each recorded, none chosen silently)

**Service** (MG1–MG7, SA1–SA9, R1–R11)
- **SA1.** One run type: `repopg.BotRun`, `trading.BotRun` and `botRunJSON` gain `Error`. One renderer (`toBotRunJSON`) serves `last_run`, the runs items and the detail.
- **SA3 / R6 Runs cursor.** The decisions cursor's wire is reused, with a kind byte `0x52` ('R') in the runs checksum input only (49 bytes against the decisions' 48). The decisions bytes are untouched, so no issued decisions cursor breaks. A golden test (`TestDecisionsCursor_ChecksumGolden`: checksum `f49e775ce4fa3e51f891f12ad89f2c5b`) was written and run against the unmodified functions before `cursor.go` was edited. The orchestrator and the code reviewer each recomputed it independently in Python.
- **SA5.** The watch read is one owner-scoped query with the pointer joins scoped to the same bot. `generated_at` is read once at the start. The `px:last` read runs after the snapshot closes.
- **R4 "Stale or missing → unknown".** Market watch passes a present `px:last` session through even when stale; this route applies the PRD literally. `px:last` is usable only when valid, `stale = false` and `updated_at` ≥ `generated_at − 120 s` (`LivePriceMaxAge`). A closed session still reads `closed`, because the publisher rewrites `px:last` every 60 s and staleness is never true while a calendar is closed. A value left by a stopped publisher never claims a session.
- **R5.** `next_bar_at` keys on `bot_watch.timeframe` (the strip timeframe the bot evaluated), not a separate `instruments.base_timeframe` read.
- **R9.** A run 404 reads "That check doesn't exist." (the screen calls a run a check).
- **R10.** Once G is newest, the harness's make down/up window rolls back G, and its existing branch skips F's backfill proof with a note. Accepted.
- **R11.** `TestReady_BotVersionsSchema_NotReady` (F only → 503 with G's message) proves "503 before G".

**Bot** (R-BA1…R-BA13)
- **R-BA1.** PRD §4.2 says "`hasDecision` now returns its id", but existing specs assert booleans on it and FR-BA-BOT-006 forbids editing them. So the SQL `HAS_DECISION` returns the suppressing decision's id (earliest by `ts`, then `decision_id`), `hasDecision` stays the boolean over that read, and a new `decisionId` returns the id. The pass calls `decisionId` only on a hit.
- **R-BA2.** `RunFinish.outcomes` is optional; absent means `[]`. The pass always passes it.
- **R-BA3.** No new field on existing shapes (`BotRunRow`, `PassSummary`, …), because specs assert `toEqual` on them. Entries are observed through new memory-store accessors (`runOutcomes`, `watchRows`) and SQL.
- **R-BA4.** The bots integration specs' cleanup lists gain `'bot_watch'`; the harness leftover gate counts `bot_watch` rows of spec bots (must be 0).
- **R-BA5.** The unreachable `market === null` guard records `no_rows`, so every universe instrument yields exactly one entry.
- **R-BA6.** The `pending_order` pointer is the first pending bot order on the instrument, by `(placed_at, order_id)`.
- **R-BA7 / R-BA8.** The watch write comes after the finished run's metric and log and after `lastSeen` advances, in its own catch. Its FK checks take `KEY SHARE` on the `bots` and `instruments` rows only, which does not conflict with Pause's `FOR NO KEY UPDATE`. It never touches `paper_accounts`.
- **R-BA9.** `checkWatchEntry` encodes the C11 per-verdict table and is used by specs only; production does not validate outcomes at write time, because a throwing `finishRun` would strand a run `running`. G's CHECKs guard the `bot_watch` columns.
- **S3 interpretation.** `evaluateRule`'s own `decided` branch is unreachable in the pass (the pass passes `hasDecision: () => false` and checks the store itself); it maps to the zone's implied rule.

**Web** (BAW-1…BAW-10 and drift rulings)
- **PRD over mockup copy.** *Decided* reads "skip at 14:02" (the mockup's "· insufficient cash" is dropped in both modes).
- **Mockup over PRD.** The Checks head note comes from the mockup ("One row per check that saw a new bar or wrote a decision · newest first"), because the PRD names none. `.more-row` is left-aligned with 10px above, as the mockup renders it, while the record's `.decision-more` is centred (design advisory A2).
- **A check still running when expanded (review-1 W4).** It fetches nothing and reads "Checking now". When the 10 s refresh shows it finished, an open row fetches once. A detail that still answers `running` is not cached, so it is never frozen as "No instrument was evaluated".
- **No reads for `Me`.** The watch and runs request functions read a primitive `selectedKind` computed and return `undefined` for the manual bot. A 10 s list reload rebuilds the summary objects, so a non-primitive dependency would re-issue (and abort) the reads (review-1 W3). The ORCH-14 mutation check proved the new tick specs catch this.
- **E2E type check (W8 / ORCH-9).** `tsc -p e2e/tsconfig.json` fails at base with 20 pre-existing errors (missing Node types, `import.meta` under commonjs). S6/S7 require no new error class in their own files; fixing the e2e tsconfig is a follow-up.
- **Stale line for an observing bot (N3).** It is shown only while `running`, as the PRD says, although an observing bot is evaluated every pass too.

## Database

Migration G, `migrations/20261010061500_bot_watch_and_run_outcomes.sql` in tidewatch-migrations, runs in goose's default transaction after F (`20261009122143`). It was created with `make migrate-create NAME=bot_watch_and_run_outcomes`. Its version **`20261010061500`** is the new `RequiredSchemaVersion` (`internal/platform/postgres/schema.go`). A database migrated only through F answers `/ready` 503 (`required version 20261010061500 not applied`). The bot has no schema constant; `scripts/sql-integration.sh` asserts G is applied. The code reviewer diffed the CREATE TABLE and ALTER body against PRD §5.1: identical.

```sql
CREATE TABLE bot_watch (
    bot_id              uuid        NOT NULL REFERENCES bots (bot_id),
    instrument_id       text        NOT NULL REFERENCES instruments (instrument_id),
    evaluated_at        timestamptz NOT NULL,
    run_id              uuid,
    timeframe           text        NOT NULL CHECK (timeframe IN ('1h', '1d')),
    bar_ts              timestamptz,
    zone                text        CHECK (zone IN ('buy', 'pre_buy_2', 'pre_buy_1', 'pre_sell_1', 'pre_sell_2', 'sell')),
    zone_run_started_at timestamptz,
    zone_age            integer     NOT NULL DEFAULT 0 CHECK (zone_age >= 0),
    baseline_at         timestamptz NOT NULL,
    held                boolean     NOT NULL,
    pending_order       boolean     NOT NULL,
    rule                text        CHECK (rule IN ('entry', 'exit')),
    verdict             text        NOT NULL CHECK (verdict IN ('no_rows', 'no_zone', 'run_start_unknown', 'baseline',
                                        'holding', 'no_position', 'pending_order', 'decided', 'deferred', 'placed',
                                        'skipped', 'observed', 'already_placed', 'nothing')),
    reasons             text[]      NOT NULL DEFAULT '{}',
    decision_id         uuid,
    order_id            uuid,
    PRIMARY KEY (bot_id, instrument_id)
);

ALTER TABLE bot_runs ADD COLUMN outcomes jsonb NOT NULL DEFAULT '[]';
```

- **No other object.** No index beyond the primary key, no seed, no grant, no change to any other table. `run_id`, `decision_id` and `order_id` have no FK (like `decisions.run_id`). The bot fills them only from bot-scoped reads, and the service's joins are scoped to the same bot. Constraint names are PostgreSQL's defaults (`bot_watch_pkey`, `bot_watch_bot_id_fkey`, `bot_watch_instrument_id_fkey`, `bot_watch_{timeframe,zone,zone_age,rule,verdict}_check`).
- **Semantics.** One `bot_watch` row per (bot, universe instrument), overwritten each evaluation. `baseline_at` is `bots.status_since` as the pass read it. `outcomes` is `[]` for rows from before G, for a `running` run, for the version-unsupported run and for the R12 interrupted sweep.
- **Down.** `ALTER TABLE bot_runs DROP COLUMN IF EXISTS outcomes; DROP TABLE IF EXISTS bot_watch;`. No `CASCADE`. It is destructive (every watch row and every run's outcomes), owner-only and local-only.
- **Harness** (`scripts/check-disposable-db.sh`, +261/−11 together with the G file):
  - G joins `expected_migrations`; `required_migration = bot_watch_and_run_outcomes`.
  - `relations_` / `assert_` / `absent_` functions check the exact columns, the primary key, both FKs, the five CHECKs, the single index and the `outcomes` column with its default. "G seeds nothing" is asserted.
  - Probes, each in a rolled-back transaction with its own probe user: the PRD's unknown-verdict probe plus 7 more are refused (bad timeframe, zone, negative `zone_age`, bad rule, unknown instrument, unknown bot, duplicate key). 4 controls are accepted: a row with every nullable column null, the bot's `ON CONFLICT … DO UPDATE` upsert, pointers naming nothing, and a `bot_runs` row reading `outcomes = []`.
  - F's checks were made G-aware in the harness only: F's exact `bot_runs` column list excludes `outcomes`, and "F is newest" became "F or later". F's file is unchanged.
  - Result: **1130 PASS / 0 FAIL**. A make down to F then up restores G, and two down-to round trips pass (FR-BA-MIG-001/002).
- **Size (A5).** On the preview, `pg_column_size(outcomes)` was at most 637 B (average 631 B) over 7 runs with 6 entries each.

## API

### Service routes (tidewatch-service)

The three new routes are `GET`s on the gated market group (`NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`), mounted by `mountBots`. They need no CSRF and read no body. Each runs `EnsureBots` first. The service never computes a verdict, never reads `indicators` for these routes and never writes anything.

| Method and path | Request | 2xx response | Errors |
|---|---|---|---|
| `GET /bots/{bot_id}/watch` | no query parameter | `{generated_at, checked_at, items: [WatchItem]}` | 400 (any parameter), 404 |
| `GET /bots/{bot_id}/runs` | `limit` 1–100 (default 20), opaque `cursor` | `{items: [BotRun], next_cursor}`, newest first by `started_at DESC, run_id DESC`, no `outcomes` | 400, 404 |
| `GET /bots/{bot_id}/runs/{run_id}` | no query parameter | `BotRun & {outcomes: [WatchEntry]}`, outcomes exactly as stored | 400 (any parameter), 404 |
| `GET /bots`, `GET /bots/{bot_id}`, `POST …/pause`, `POST …/resume` | as 2b | `last_run` gains `error` | as 2b |

**Shapes.**

```
BotRun = { run_id, loop, trigger, started_at, finished_at | null, status, counts, error: string | null }
WatchEntry = { instrument_id, timeframe ('1h'|'1d'), bar_ts | null, zone | null, zone_run_started_at | null,
               zone_age (int >= 0), baseline_at, held, pending_order, rule ('entry'|'exit'|null),
               verdict, reasons: string[], decision_id | null, order_id | null }
WatchItem = WatchEntry & { evaluated_at, run_id | null, display_symbol,
                           decision: {decision_id, action, ts} | null, order: {order_id, status} | null,
                           session: 'open'|'closed'|'unknown', next_open_at | null, next_bar_at | null }
```

- **`error`** is `bot_runs.error` as stored: a class name such as `DatabaseError`, or `interrupted`, or `version_unsupported`. It is always present: on `last_run` (list, detail, pause and resume answers), on every runs item and on the detail.
- **`checked_at`** = `max(evaluated_at)` over the bot's rows, null with none. It is the heartbeat.
- **Universe order.** `watchlist_items.position` ascending, then rows whose instrument left the watchlist, by `instrument_id COLLATE "C"`.
- **Pointer decoration.** `decision` and `order` come from left joins scoped to the same bot (`d.bot_id = w.bot_id`, `o.bot_id = w.bot_id`) and owner. A pointer to another bot's or user's object renders `null`, with the raw id kept as stored. Integration plants such pointers and asserts `null`.
- **Session decoration (SA6).** After the database snapshot, one `MGET` of `px:last` for the items' instruments, through the existing `ParseLastPrice` / `NormaliseSession`. Usable (valid, `stale = false`, `updated_at` within 120 s of `generated_at`) → `session` and `next_open_at` from it. Otherwise `unknown` / null.
- **`next_bar_at`** is the first UTC hour boundary strictly after `generated_at` (08:10:30Z → 09:00Z; exactly 08:00:00Z → 09:00Z), only for `timeframe = '1h'` with `session = 'open'`. It is null for every 1d item and every closed or unknown session.
- **Redis absent never fails the route.** Without `REDIS_URL`, with the subscriber down, or on an `MGET` error (only that logs the existing warn `last_price_read_failed`), the answer is 200 with every `session: "unknown"` and every `next_*` null. Redis is not a readiness input.
- **Manual bot.** The watch answers `{generated_at, checked_at: null, items: []}` without reading `bot_watch` or Redis. Runs answer `{items: [], next_cursor: null}`.
- **Paused or observing bot.** Rows are answered as last written, with no special case; the web words the head note from `bot.status`.

**Runs cursor.** Base64url without padding of `{"v":1,"t":<started_at µs>,"i":"<run_id>","h":"<32 hex>"}`. `h` is the first 16 bytes of SHA-256 over `version (u64 BE) ‖ 0x52 ‖ bot_id ‖ started_at µs ‖ run_id`. A decisions cursor is refused on `/runs`, and a runs cursor is refused on `GET /decisions` and `GET /bots/{id}/decisions`. A runs cursor for one bot is refused for another. The checksum is unkeyed: it is an integrity check, not an anti-forgery control (security ℹ️-2). Authorization never depends on it, because ownership is resolved first and every row is re-scoped by owner.

**Check order on the new routes.**
1. The gate chain, ready gate and no-store.
2. The strict query parse: `runs` accepts only `limit` and `cursor`; the other two accept none. Unknown, repeated or bad → `400 invalid_request {field, reason}`.
3. `bot_id` (and `run_id`) not a UUID → 404.
4. `runs` only: cursor syntax → `400 {field: cursor, reason: invalid}`, before ownership. Since ORCH-12 this includes `t < 0`.
5. `EnsureBots`, then ownership. Absent or another user's bot → `404 not_found` "That bot doesn't exist.", never 403.
6. `runs`: cursor binding to this bot and kind → 400. Detail: a run that is not this bot's → `404 not_found` "That check doesn't exist.".

No message distinguishes a foreign bot or run from an absent one.

**Route inventory.** `TestRouter_ForcedChangeGatesNewRoutes` now counts 35 gated routes (32 production + 3 test probes; it was 32). `TestRouter_NoDecisionMutation` admits eight reviewed `:bot_id` routes: still no `:decision_id` route and no mutation under `/bots` except pause and resume. No new error code, reason, audit event, metric, log event or env var; the routes are counted by the existing request metrics.

**Compatibility (PRD §6.3).** A web build against a service without these routes gets 404 and shows "Watch couldn't load." / "Checks couldn't load." while the rest of the detail renders. A service at G against a database without G is 503 on `/ready`.

### Bot runtime: verdicts, the watch write and outcomes (tidewatch-bot `packages/bots`)

**`evaluateRule` (S1, `rules.ts`).** It returns `{kind: 'fired', fired}` or `{kind: 'blocked', reason}`. `BLOCKED_REASONS` are tested in the order `fireRule` always used:
1. no strip rows → `no_rows`;
2. a null zone or a pre-zone → `no_zone`;
3. Buy with an unknown run start → `run_start_unknown`;
4. Buy whose run began before `statusSince` → `baseline`;
5. the side is not allowed → `pending_order` when a pending bot order exists, else `holding` (entry) or `no_position` (exit);
6. a decision-key hit → `decided`.

`fireRule` is now `evaluateRule(...).kind === 'fired' ? fired : null`, a wrapper of at most 4 lines with unchanged exports and specs. `rules.ts` changed +62/−10; `rules.spec.ts` gained 368 lines and lost none.

**The fourteen verdicts (one per universe instrument per evaluation; C11 table).**

| Verdict | When | `rule` | `reasons` | Pointers |
|---|---|---|---|---|
| `no_rows` | no strip rows | null | `[]` | — |
| `no_zone` | zone null or a pre-zone | null | `[]` | — |
| `run_start_unknown` | Buy streak fills the 49-row window (2b R3) | `entry` | `[]` | — |
| `baseline` | Buy run began before `status_since` (2b R13) | `entry` | `[]` | — |
| `holding` | Buy while an open position exists | `entry` | `[]` | — |
| `no_position` | Sell with no open position | `exit` | `[]` | — |
| `pending_order` | a pending bot order blocks the side | the rule the zone implies | `[]` | `order_id` |
| `decided` | a decision with the key exists (2b R6) | the rule | `[]` | `decision_id` |
| `deferred` | session/price gate not ok, or the intake deferred (including a USD-quoted spot instrument without a USD/THB rate) | the rule | `['venue_closed']` or `['price_unavailable']` | — |
| `placed` | intake placed | the rule | `[]` | `decision_id`, `order_id` |
| `skipped` | intake skipped | the rule | `['qty_below_minimum']` alone, or a non-empty ordered subsequence of `insufficient_cash`, `position_limit`, `exposure_limit`, `max_open` | `decision_id` |
| `observed` | intake observed | the rule | `['observing']` | `decision_id` |
| `already_placed` | intake found the order already placed | the rule | `[]` | `order_id` |
| `nothing` | intake found the locked state no longer allows the action (paused, decision appeared, side changed) | the rule | `[]` | — |

A `RangeError` from `zoneRun` (unknown zone text) is not a verdict: it throws as before and the evaluation fails.

A constructed C11 example (`baseline`):

```json
{"instrument_id": "AAPL@webull", "timeframe": "1h", "bar_ts": "2026-10-09T19:00:00Z", "zone": "buy",
 "zone_run_started_at": "2026-10-08T15:00:00Z", "zone_age": 18, "baseline_at": "2026-10-09T07:02:13.250Z",
 "held": false, "pending_order": false, "rule": "entry", "verdict": "baseline", "reasons": [],
 "decision_id": null, "order_id": null}
```

**Entry facts.** `bar_ts`, `zone`, `zone_run_started_at` and `zone_age` come from `zoneRun(rows)`; `zone_age` is the streak over the latest 48 rows (null/null/null/0 with no rows). `held` and `pending_order` are the values the rule was given. `watch.ts` (new) holds `WATCH_VERDICTS`, `WATCH_ENTRY_FIELDS`, `WATCH_REASON_SETS`, the `WatchEntry` type, `watchEntryJson` (keys in C11 order, so every C11 example re-renders to identical bytes), `impliedRule` and `checkWatchEntry`.

**Write order in one evaluation (PRD §4.4–4.5).**
1. The run, if any, is finished by `finishRun` with its status, counts and **outcomes**.
2. Its existing metric and `bots_run_finished` log.
3. `lastSeen` advances.
4. **The watch write**, the evaluation's last I/O, stamped `evaluated_at` = the `now` read once at the start of `evaluateBot`. `run_id` is the run this evaluation opened, the on-demand run its first decision-writing intake created (2b R1), or null for a quiet pass.

A quiet pass (no run) still writes the watch, which is the heartbeat. `bots_passes_total{nothing_new}` counts such passes.

**Failure paths.**
- A thrown evaluation error finishes the run `failed` with the class and **the entries gathered so far**, logs `bots_pass_failed` as before, and writes **no** watch. The rows stay as they were; the failed run and the heartbeat explain it.
- The version-unsupported path (2b ORCH-6, including a null `current_version`) is not an evaluation. Its failed run carries `outcomes = []` and it makes no watch write, because an empty write would delete the rows. The R12 interrupted sweep leaves the default `[]`.
- A failed watch write logs `bots_watch_write_failed` (error level; exactly `bot_id`, `error_class` (a constructor name) and `code` when a SQLSTATE exists) and does not fail the evaluation. The next pass retries. There is no once-only memo (follow-up).
- An empty universe deletes the bot's rows. Paused bots are not evaluated, so their rows stay.

**The watch statement (`WRITE_WATCH`, `pg-store.ts`).** One statement through the plain query path: a data-modifying CTE deletes the bot's rows whose instrument is not in `jsonb_to_recordset($3)`, then `INSERT … ON CONFLICT (bot_id, instrument_id) DO UPDATE`. It is never inside `transaction()` or the intake and never takes a lock statement. An instrument listed twice fails it (21000), as does a column check (23514). The memory store mirrors those constraints (`MemoryCardinalityError` carries 21000).

**C4 untouched.** The integration title `writes the watch in one statement outside any transaction, after finishRun, without the account lock` proves three things: the statement runs alone in its checkout after `FINISH_RUN`; it completes while another session holds `paper_accounts … FOR UPDATE`; and the backend holds no `paper_accounts` lock while waiting.

**`HAS_DECISION`** changed from `SELECT EXISTS (…)` to `SELECT decision_id … ORDER BY ts, decision_id LIMIT 1`. It is still a lock-free read bound to the bot's own decisions through `decisions_bot_ts_idx`. The intake's SQL text therefore moved although `intake.ts` is byte-identical (security ℹ️-1).

**Unchanged by contract.** `place.ts`, `intake.ts`, `strip.ts`, `universe.ts`, `engine.ts`, `metrics.ts`, `version.ts` and `client-order-id.ts` are byte-identical. So are the other packages, the Dockerfile, `.env.example`, `pnpm-lock.yaml` and `packages/bots/package.json`. The pass writes the same decisions, orders, runs, counts, logs and metrics as 2b for the same inputs. The six `bots_*` metric series and their label sets are unchanged; the only new log event is `bots_watch_write_failed`. Every existing `*.spec.ts` changed by addition only (+2,942/−0 across the bot's specs). Cost: one extra statement per evaluated bot per pass, plus one extra read per suppressed instrument.

## Components

Angular, under `src/app/pages/workspace/`. `DESIGN.md` rules apply: no Material, CDK or chart library; no `dark:`; no token, colour, type step or icon added (`tokens.css`, `theme.css`, `icons.ts`, `table.css`, `section.css` and `button.css` are byte-identical to base `1689b0c`); native controls; nothing animates.

**Placement (BAW-7).** Inside `app-bot-detail`'s section, in order: the `.metric-strip`, **`app-bot-watch`**, Positions, `app-decision-record`, **`app-bot-checks`**. Both new hosts render only for `kind = auto`. With *Me* selected neither renders and no watch or runs request is made. Spacing: 24px under the strip, 28px after Watch, 28px before Checks.

**`app-bot-watch`** (`feat-bots/bot-watch.ts`, injects `BotsService`).
- `section.section#watch` with `h2#watch-title` *Watch* (`tabindex="-1"`) and a `.count` with the hidden noun "instruments".
- The `.more` head note:
  - "Checked {HH:mm:ss | d MMM HH:mm:ss} · baseline since {d MMM HH:mm}";
  - paused: "Paused since {…} · last checked {…}";
  - observing: "Observing · checked {…} · baseline since {…}";
  - no rows: "No check yet".
- **Stale line.** An always-present polite `role="status"` region above the table holds the dashed `.status-line.watch-stale` "No check since {HH:mm}. The bot runner may be off.". It shows only while `bot.status = running` and `generated_at − checked_at > 120 s`, strictly (120 s is not stale, 121 s is), and clears when a newer `checked_at` arrives.
- **States**, in one always-rendered polite wrapper: "Loading watch…"; "Watch couldn't load." with *Try again*, which focuses the Watch heading first; "No check yet. Slack Water checks every 30 s once it runs."
- The table sits in a `.table-scroll` `role="region"` (`tabindex="0"`) named "Watch, scrollable table".

**`app-bot-watch-table`** (`bot-watch-table.ts`, presentational). Inputs `rows`, `mode` (`now` | `then`), `caption`. It is one table for both uses: *now* (`table.tide.watch`, with *Next*) and *then* (`table.tide.nested` inside an expanded check, without *Next*). Rows are tracked by `instrumentId`, so a refresh updates them in place. A hidden caption, `th scope="col"`, and rows that take no handler, role or `tabindex`.

Columns:
- **Instrument:** the symbol, with `.second` "{venue} · {timeframe}".
- **Last bar:** `HH:mm` today, else `d MMM HH:mm`, a 1d bar as `d MMM`; `.second` "closed bar". No bar: an `aria-hidden` "—" plus the hidden text "No bar yet".
- **Zone:** `app-zone-label` with "since {…} · {n} bars", or "start unknown · 48+ bars".
- **Verdict:** the line and a reason.
- **Next:** "{HH:mm}" / "bar closes"; "{EEE HH:mm}" / "closed · opens"; "—" / "closed"; "—" / "daily · after close"; "—" / "no session state". Since W1 the dashes are `aria-hidden`.

**Verdict copy** (sentence case, no hue; `util/watch-view.ts`):

| Verdict | Line | Second line |
|---|---|---|
| `no_rows` | No bars yet | nothing to evaluate |
| `no_zone` | Nothing to do | "{Zone label} is not Buy or Sell" / "no zone yet" |
| `run_start_unknown` | Run start unknown | Buy for 49+ bars — never entered |
| `baseline` | Baseline | Buy run began before the baseline, {d MMM HH:mm} |
| `holding` | Holding | waits for Sell |
| `no_position` | Nothing to do | Sell, no position |
| `pending_order` | Order pending | waits for the fill |
| `decided` | Already decided | "{skip \| buy \| close} at {time}" (then-mode fallback "a decision exists for this bar") |
| `deferred` | Entry waits / Exit waits | venue closed / no live price |
| `placed` | Entered / Exited | "{buy \| close} at {HH:mm} · {order status}" (then-mode fallback "{buy \| close} order placed") |
| `skipped` | Skipped | the reasons through `BOT_REASON_WORDS`, joined " · " |
| `observed` | Observed | observing · no orders |
| `already_placed` | Order already placed | from an earlier pass |
| `nothing` | No action | state changed during intake |

**`app-bot-checks`** (`bot-checks.ts`) and the **expandable row**.
- `section.section` with `h2#checks-title` *Checks*, a count with "+" while `next_cursor` exists, and the mockup's head note. The same state pattern as Watch: "Loading checks…"; "Checks couldn't load." with *Try again*; "No checks yet. A check is recorded when a new bar arrives or a decision is written."
- `table.tide.checks` in the region "Checks, scrollable table". Columns:
  - **When:** a `<time>`, `EEE HH:mm` within six Bangkok days, else `d MMM HH:mm`.
  - **Result:** "No action" / "1 entry" / "2 entries · 1 skip" with "finished at {HH:mm:ss}"; "Failed" with "{error words} · at {HH:mm:ss}"; "Checking now" with "started {…}".
  - **Instruments**, **New bars**, **Deferred:** a zero reads `aria-hidden` "—" plus sr-only "0".
  - A last `.details` cell (`width: 1%`; header text visually hidden).
- Rows are tracked by `run_id`, so the 10 s merge keeps the same DOM nodes. Open rows survive refreshes; the open set resets on a bot change.
- Each row's native `button.text-btn` *Details* / *Hide* has `aria-expanded` and `aria-controls="check-detail-{run_id}"`. `aria-controls` is always set, unlike the account menu. It is the same node in every state.
- Expanding sets `tr[data-expanded="true"]` and inserts `tr.check-detail#check-detail-{run_id}` with one `colspan="6"` cell. The cell holds a polite region that is empty in the inserting render and filled one task later (review-1 W5): "Loading this check…", then the `.check-note` "What each instrument evaluated to at this check" and an `app-bot-watch-table` in *then* mode, decorated per ORCH-5a. Other outcomes of the detail:
  - "The check failed before it evaluated an instrument · {error}";
  - "No instrument was evaluated";
  - "This check couldn't load." with *Try again*, which focuses *Hide* first (ORCH-6).
- The detail is fetched once per `run_id`; collapsing and re-expanding reads nothing.
- *Load more* sits in `.more-row`. It reads *Loading…* and is `aria-busy` and disabled while busy. A failure raises the screen toast "Couldn't load more checks. Try again." through the section's `toast` output, which `app-bot-detail` relays.

**Last check card** (`util/bot-view.ts`). Deferrals come after the action parts and are omitted at zero ("6 instruments · 2 deferred · no action", "1 entry · 2 deferred"). A failed run reads "last check failed · {error words}", where `interrupted` → "interrupted", `version_unsupported` → "version unsupported", and any other class appears as is.

**Store (`feat-bots/data/bots.service.ts`, BAW-3).**
- Two more `httpResource`s, the watch and the first runs page, keyed on the selected bot and `detailLoads`. They reload with the detail trio on the 10 s tick: five reads plus the list.
- `onDetailTick` skips while any of the five is loading.
- A selection change clears them and cancels a runs *Load more* in flight. A failed background reload keeps the last data (MW-20). No new `GET /trade` read. Leaving the screen aborts everything (SE-5).
- Runs paging: `mergeRunsFirstPage` (merge by `run_id`, the `merge-decisions.ts` semantics) and `appendRunsPage` in `util/merge-runs.ts`; `loadMoreRuns()` has its own busy flag `loadingMoreRuns`.
- Details: `runDetails` maps `run_id` → `loading | error | ready`. `openRun` fetches only when there is no entry; `retryRun` re-fetches after an error. A detail whose `run_id` differs from the request is an error; a `running` answer is not kept.

**Data layer (`data/`).**
- `bots.model.ts`: `BotRun.error` is optional on the type and always set by the parser (`null` when absent), so 2b fixtures compile (BW-2).
- New `parseBotWatch`, `parseBotRunsPage`, `parseBotRunDetail`. Unknown `verdict`, `session`, `rule`, `timeframe` or `zone` values refuse the body, so the section shows its error rather than a wrong verdict. `action` and order `status` are kept as strings and rendered only through closed maps.
- `bots-api.service.ts`: `watchRequest`, `runsRequest` (`RUNS_PAGE_SIZE = 20`), `runs(botId, cursor)`, `runDetail(botId, runId)`. Ids go through `encodeURIComponent` and the cursor through the strict codec; failures go through `toTradeApiError`.
- S7 reconciled 41 rows / 36 wire keys against the service's `json` tags at `5208c2a`, plus the service's C11 hash and vocabulary: no drift.

**Styles (`src/styles/components/bots.css` only).** `app-bot-watch` / `app-bot-checks` blocks and `.watch-stale`. `.tide .details`. `.tide tr[data-expanded="true"] td` and `.tide tr.check-detail > td` (`--surface`, `padding: 0 17px 17px`, `0 10px 14px` at ≤ 600). `.check-note` (10px `--text-3`; 5.46:1 dark, 4.84:1 light). `.tide.nested` (`min-width: 0`, 1px `--line` border, 12px radius, `border-collapse: separate`, 14px cells, hover `--surface-2`). `.more-row`. The production nested table deliberately differs from the mockup's CSS: the mockup's selector leaked 17px padding into nested cells and its `border-collapse: collapse` dropped the radius (design advisory A1).

**`DESIGN.md` (FR-BA-WEB-011, `d0f8408` + `098b0ef`).** +361/−51 at `d0f8408`. It adds:
- the **Expandable row** pattern under Bots pieces (markup, look, behaviour, the always-set `aria-controls`), with known inconsistency #19: move it to `table.css` when a second screen uses it;
- the Bots screen placement and states;
- focus and live regions, including the hidden-dash rule;
- ten decision rows (PRD §7.6 feature pieces, ORCH-5a, ORCH-6 pending veto, W4, W1, A1, A2, A3, A5, copy rulings);
- the verification-evidence entry, citing Phase C since `098b0ef`;
- a 91-entry source snapshot (check: no drift).

The web `CLAUDE.md` gained the same conventions ("One table for now and then", the Watch and Checks store bullets, follow-ups).

## Files touched

The lists below come from each approved plan's Files lists. They are cross-checked against the orchestrator's per-step scope checks and the file counts of the reviewed diffs. No `git diff` was run for this document.

| Repo | Range (base..PR head) | Merge | Files |
|---|---|---|---|
| tidewatch-migrations | `1e115c0..a474a77` | `3ec60a7` | 4 |
| tidewatch-service | `594548f..14ce781` | `77d8ebf` | 23 (at `5208c2a`; the ORCH-12 fix, +78/−7, touched the cursor parse, its tests and the two docs) |
| tidewatch-bot | `ac80b04..b9d6d5e` | `6b8cdb0` | 21 (+5,068/−93 at `a9502c6`; ORCH-10 +4/−4 in docs) |
| tidewatch-web | `1689b0c..098b0ef` | `31f9435` | 31 (30 in the S1–S8 lists at `de44595`, plus `DESIGN.md`; ORCH-13 and ORCH-14 (11 files, +243/−32) stayed inside that set) |

### tidewatch-migrations (PR #6, https://github.com/tidewatch-labs/tidewatch-migrations/pull/6)
- `migrations/20261010061500_bot_watch_and_run_outcomes.sql` (created): migration G, with a header citing PRD §5.1, BA1, BA2, BA4 and the FK-less pointers.
- `scripts/check-disposable-db.sh` (modified): G's lists, assertions, probes, transcript; F's checks made G-aware.
- `README.md`, `CLAUDE.md` (modified): G's objects, destructive down, required version moved from F to G with the anchored lookup.

### tidewatch-service (PR #7, https://github.com/tidewatch-labs/tidewatch-service/pull/7)
- **Docs:** `README.md`, `CLAUDE.md` (modified): the three routes and shapes, `error`, C11, the runs cursor, the watch invariants, 35 gated routes, named tests, required schema version G.
- **Schema contract:** `internal/platform/postgres/schema.go` (`RequiredSchemaVersion = 20261010061500`), `internal/pgtest/migrate.go` (anchored lookup), `scripts/integration-test.sh` (modified).
- **C11:** `internal/trading/testdata/bots-watch-entry.v1.json` (created), `internal/trading/watchentry_test.go` (created).
- **Repository:** `internal/repository/postgres/bot.go` (modified): `BotRun.Error`; `LastRun` selects it; `RunKey`, `Runs`, `RunByID` (with `outcomes::text`, `ErrRunNotFound`), `Watch`.
- **Services (`internal/services/trading/`):** `botruns.go` (created: `BotRuns`, `BotRun`, the `BotRunReads` port), `botwatch.go` (created: `BotWatch`, `watchSession`, `nextBarAt`), `cursor.go` (modified, append-only, plus the `t < 0` check), `bots.go` (modified: `BotRun.Error`). Tests: `cursor_test.go` (created), `bots_test.go` (modified).
- **Handlers:** `internal/handlers/bots.go` (modified: `Runs()`, `Run()`, `Watch()`, one `toBotRunJSON`), `internal/handlers/bots_test.go` (modified).
- **Router:** `internal/app/router.go` (modified: three GETs in `mountBots`), `internal/app/router_test.go` (modified: 35 gated, 8 reviewed routes).
- **Integration (`test/integration/`):** `bot_runs_test.go`, `bot_watch_test.go` (created); `bots_test.go`, `main_test.go`, `ready_test.go` (modified).
- **Unchanged by design (verified):** `decisions.go`, `marks.go`, `marketwatch.go`, `feed.go`, place/manualfill/cancel/estimate, `internal/trading` rules and arithmetic, `internal/config`, `internal/observability`, `pkg/apperror`, `internal/platform/redis`, `go.mod`/`go.sum`. No Go source contains "preview".

### tidewatch-bot (PR #6, https://github.com/tidewatch-labs/tidewatch-bot/pull/6)
- **Repo root:** `README.md` (pass step 8 *Watch*, outcomes on *Finish*, the fourteen-verdict table, C11 beside C10, `bot_watch` in *Rows written*, the new log event, schema dependency G), `CLAUDE.md`, `scripts/sql-integration.sh` (asserts G, `bot_watch` leftover gate) (modified).
- **`packages/bots`:** `vitest.int.config.mts` (modified, names G); `fixtures/bots-watch-entry.v1.json` (created, C11 copy); `fixtures/README.md` (modified).
- **`packages/bots/src`:**
  - `rules.ts`, `index.ts` (modified);
  - `watch.ts` (created);
  - `store.ts` (modified: `RunFinish.outcomes`, `decisionId`, `writeWatch`);
  - `pg-store.ts` (modified: `HAS_DECISION`, `FINISH_RUN` with `outcomes`, `WRITE_WATCH`);
  - `pass.ts` (modified: gathers entries, writes outcomes and the watch);
  - `testing/memory-store.ts`, `testing/index.ts` (modified: `MemoryWatchRow`, `watchEntry` builder, `runOutcomes`, `watchRows`).
- **Tests:** `rules.spec.ts`, `testing/memory-store.spec.ts`, `pass.spec.ts`, `pg-store.int.spec.ts`, `pass.int.spec.ts` (modified, additions only); `watch.spec.ts`, `bots-watch-entry-fixture.spec.ts` (created).

### tidewatch-web (PR #9, https://github.com/tidewatch-labs/tidewatch-web/pull/9)
- **Docs:** `README.md`, `CLAUDE.md`, `DESIGN.md` (modified).
- **Data (`src/app/pages/workspace/data/`):** `bots.model.ts`, `bots-api.service.ts` and their specs (modified).
- **Bots (`src/app/pages/workspace/feat-bots/`), created:** `bot-watch.ts`, `bot-watch-table.ts`, `bot-checks.ts`, `util/watch-view.ts`, `util/checks-view.ts`, `util/merge-runs.ts`, each with its `.spec.ts`.
- **Bots, modified:** `bot-detail.ts`, `bot-detail.spec.ts`, `bots.spec.ts`, `data/bots.service.ts`, `data/bots.service.spec.ts`, `util/bot-view.ts`, `util/bot-view.spec.ts`.
- **Styles:** `src/styles/components/bots.css` (modified).
- **End-to-end:** `e2e/src/support/bots.ts` (three mocked routes, builders, counts), `e2e/src/bots.spec.ts` (named tests and the 8-state matrix), `e2e/src/support/screens.ts` (§7.5 copy), `e2e/src/bots-live.spec.ts` (read-only Watch/Checks checks and the gated Pause/Resume extension) (modified).

**Not changed:** `tidewatch-specs` and `documents/` (inputs only, D17); `tidewatch-apis` (not a Git repo; routes documented in the service README only); compose and workspace-root files; no new environment variable.

## Test plan

### Commands (all local; there is no CI, D4)

- **Migrations:** `make migrate-validate`; `make check-disposable-db` (1130 PASS / 0 FAIL).
- **Service:** `make ci` (vet, test-race, build; Docker-free); `make test-integration TIDEWATCH_MIGRATIONS_DIR=<migrations checkout>`. No `--- SKIP` allowed; verification greps `--- PASS: <Name> (`. If an integration failure comes only from `TestSubscriber_Restart_Resubscribes`, re-run (ORCH-11; fixed on main by service#6).
- **Bot:** `pnpm install --frozen-lockfile && pnpm nx run-many -t lint test typecheck build`; `TIDEWATCH_MIGRATIONS_DIR=<checkout> bash scripts/sql-integration.sh` (asserts G; bots integration 16/16 on G).
- **Web:** `pnpm nx run-many -t lint test build` (2,743 tests); mocked Chromium `e2e/src/bots.spec.ts` (260/260); the full Playwright suite against a preview (`pnpm nx e2e e2e --skip-nx-cache` with `BASE_URL`, `E2E_LIVE_MARKET_DATA=1`); `bots-live.spec.ts`, with the Pause/Resume test gated by `E2E_BOTS_PAUSE=1` (Chromium, fresh database).

### Named acceptance tests (do not rename)

- **Service:** `TestWatchEntry_FixtureHash`, `TestRunsCursor_RoundTrip`, `TestRunsCursor_KindSeparation`, `TestRunsCursor_BoundToBot`, `TestDecisionsCursor_ChecksumGolden`, `TestParseDecisionsCursor_NegativeT`, `TestService_BotCursors_NegativeT`, `TestBotsHandler_Runs_Query`, `TestBotsHandler_Run_NotFound`, `TestBotsHandler_Watch_Shape`, `TestNextBarAt`, `TestService_BotWatch_Decorations`, `TestBotRuns_List`, `TestBotRuns_CursorBinding`, `TestBotRuns_Detail` (outcomes JSON-equal to the C11 examples), `TestBotRuns_ForeignRunIs404`, `TestBotWatch_UniverseOrderAndDecorations`, `TestBotWatch_RedisAbsent`, `TestBotWatch_ManualBotEmpty`, `TestBotWatch_ForeignBotIs404`, `TestContract_RequiredSchemaVersion`, `TestReady_BotVersionsSchema_NotReady`, `TestReady_SchemaWait`, `TestRouter_ForcedChangeGatesNewRoutes` (35), `TestRouter_NoDecisionMutation`. The 2b named tests stay.
- **Bot (exact Vitest titles):**
  - 12 `evaluateRule` titles (`rules.spec.ts`);
  - the fourteen `records …` titles and `gathers exactly one entry …` (`pass.spec.ts`);
  - `stamps every watch row with the evaluation's now and the run it opened or finished`;
  - `stores empty outcomes and writes no watch on a version-unsupported run`;
  - `returns the suppressing decision's id` (memory and integration);
  - `writes the watch in one statement outside any transaction, after finishRun, without the account lock` (`pg-store.int.spec.ts`);
  - 4 C11 fixture titles (`bots-watch-entry-fixture.spec.ts`, including the `watchEntryJson` re-render).
- **Web (`e2e/src/bots.spec.ts`, mocked, fail-closed):**
  - behaviour: "renders the Watch section's verdicts and next words", "shows the stale line and clears it on a newer check" (`page.clock`), "lists checks newest first and appends with Load more", "raises the toast when Load more fails", "expands a check in place and fetches it once", "shows a check's error and retries it", "keeps an open check across the 10 s refresh" (focused *Hide* survives);
  - sections and focus: "shows neither section for Me and requests neither", "moves focus to the heading on Try again", "decorates an expanded check from the data already loaded" (ORCH-5a);
  - keyboard, copy and layout: "reaches every Watch and Checks control by keyboard", "names the failure class in the Last check note", "nothing in the Watch and Checks heads is clipped at 390 and 600".
  - Matrix: 8 new states (quiet, deferred, failed, stale, sections-loading, sections-error, check-expanded, check-error) × 2 themes × 390/600/1080/1440 = 64 captures, plus the 2b ten.
  - Store specs (`bots.service.spec.ts`): the five exact titles from BAW-3, plus the ORCH-14 "10 s detail tick" specs. A mutation reading `selected()?.kind` makes all six fail.
  - Real-store tests (`bots.spec.ts`): "expands a check against the real store and fetches its detail once", "retries a check's detail once after an error", "shows both section errors when the service lacks the routes".

### Acceptance status (PRD §9, verification.md): 33/33 passed

| IDs | Status | Evidence / note |
|---|---|---|
| FR-BA-MIG-001…003 | Passed | Harness 1130/0; down to F + up restores G; `/ready` 503 on F only, 200 at G (also on the preview). |
| FR-BA-BOT-001…008 | Passed | `evaluateRule` titles; 14 `records …` titles; C4 lock probes on G; outcomes full / partial / `[]`; `decisionId`; specs +2,942/−0; C11 three-way `cmp`; docs fact-check (19 refs). |
| FR-BA-SVC-001…006 | Passed | Named tests above; 35 gated routes; golden decisions checksum; `error` value `DatabaseError` proven end to end. |
| FR-BA-WEB-001…012 | Passed | Unit and mocked Playwright on the preview; 64 captures, 0 horizontal page scroll; contrast 392 measurements, minimum 4.79:1; axe 0 violations in 18 files; clipping 0/833 (Phase A) and 0/836 (Phase C); `DESIGN.md` refresh checked (91/91 hashes). WEB-010: no screen-reader run (optional). |
| FR-BA-E2E-001 | Passed | Watch = `bot_watch` 6/6 rows, read 5.3 s (dark) and 6.5 s (light) after the pass. |
| FR-BA-E2E-002 | Passed | Expanded checks = `bot_runs.outcomes` 6/6, both themes, one detail request per expansion. |
| FR-BA-E2E-003 | Passed with deviation | Stale line at 120.6 s with the bot stopped; cleared on the first read after restart. The **whole bot container** was stopped for 148.5 s, because `MARKET_DATA_COLLECTORS` could not be changed without editing helper-managed compose files. Passes were shown by SQL and metrics, because `bots_pass_started` is debug-level. |
| FR-BA-E2E-004 | Passed | Pause froze rows with the paused note (`max(evaluated_at)` stayed before the pause through the next pass slot); Resume rewrote all 6 rows with `baseline_at` = the new `status_since`. Independent captures (Phase B) and the gated journey (Phase C, 1/1). |

### Preview phases (isolated database at G; `runtime.preview`)

- **Phase A** (08:29–08:49Z; preview `:50245`; web image `de44595`, suite from `d44f655`, service `14ce781`, bot `b9d6d5e`, migrations `a474a77`).
  - Full suite 691 passed / 0 failed / 1 skipped (the gated pause).
  - The first-sign-in journey ran here, spending the admin's one-time forced change.
  - Secret scan of 1,440 files: 0 hits (positive control 2).
  - `EnsureBots` created both bots at 08:30:15Z. Passes ran at :10/:40. `bot_watch` held 6 rows; two noop runs had 6 outcomes each.
  - Live verdicts seen: `no_rows` (NVDA/AAPL in the first run, before US bars), `no_zone` (pre-zones), `baseline` (BTC/THB and XAU/USD Buy runs older than the baseline) and `no_position` (NVDA and PTT.BK Sell).
- **Phase B** (independent E2E-003/004).
  - The gated journeys failed on test defects D1 and D2.
  - D3 was observed (Watch refresh intervals of 10 s ×10, 20 s ×7, 30 s ×3).
  - While the whole worker was down, every *Next* read "— no session state", because `px:last` comes from the stopped worker's status publisher.
  - Pause/Resume moved Slack Water's `status_since` several times; the final Phase B baseline was 08:54:55.00Z.
- **Phase C** (after ORCH-14; preview `:49257`, web `5b8cb7c`, database kept).
  - Suite 690 / 0 / 1 (journey left out, because the forced change was already spent).
  - `bots.spec.ts` 260/260; captures byte- and pixel-identical to Phase A; W1 verified in the accessibility tree.
  - `bots-live` populated branch passed; the gated Pause/Resume passed once.
  - Tick probe: 12 ticks 10.0 s apart, all five reads each, 0/80 page aborts. 4 CDP `ERR_ABORTED` labels appeared on fully received reads.
  - End state: 7 runs, 0 failed; `/api/ready` 200.
- **Owner-session live validation** (2026-10-10, about 13:37–13:42Z, read-only, as the owner). Checks: 11 rows equal to `bot_runs`. No 20:00 check, because that bar arrived late and was recorded at 20:20 (correct). An expanded check equalled `outcomes` with one request and no refetch on reopen. Enter and Space toggled with the focus ring kept. Watch equalled `bot_watch` on the same pass; *Next* equalled `px:last`. Polling was 10.0 s with all five reads. Light theme at four widths showed no page scroll.

### Assumption outcomes (PRD A1–A6)

- **A1** (2b's MIG pattern): held (ORCH-1).
- **A2** (`next_bar_at` = next UTC hour): held for 24/7 crypto. The 09:00Z bar's run was recorded at 09:00:11Z. US and SET were closed (weekend), so it was not exercised there.
- **A3** (120 s stale threshold): held. 48 passes averaged about 18 ms (all under 1 s).
- **A4** (`px:last` for six instruments within the poll budget): held.
- **A5** (outcomes under 2 KB): held, at most 637 B.
- **A6** (2b carry-overs don't block): held.

### Preview operational notes

- **Admin password after the e2e suite.** The e2e first-sign-in journey performs the admin's one-time forced password change to a random journey password. That password is kept in the git-ignored `e2e/.auth`, plus a 0600 copy for later phases. Afterwards the owner's `TIDEWATCH_ADMIN_PASSWORD` (`.forge/docker/secrets/tidewatch.env`) no longer signs in.
  - At the owner's request (11:45Z), the orchestrator restored it with the service CLI `admin set-password --username admin`. The CLI reads `TIDEWATCH_ADMIN_PASSWORD` from the environment and never prints it.
  - The reset revoked all sessions, so `e2e/.auth` became stale, and it leaves `must_change_password = true` by app design.
  - The owner typed the password themselves; the permission classifier blocked materialising it.
- **Journey runs once per database.** On a kept database the journey cannot run again. Later phases ran the suite with `--no-deps` and re-ran `authed-setup` (journey password) before each step, because `sign-out` ends the saved session.

### Manual reproduction

1. With G applied and the bot running, open Bots and select Slack Water. Within 40 s of a pass, compare the Watch rows with `SELECT … FROM bot_watch WHERE bot_id = <id>` (verdict, rule, reasons, zone, age, `bar_ts`, `baseline_at`). Every row's `evaluated_at` should equal the head note's "Checked" time.
2. Expand the newest check and compare it with `SELECT outcomes FROM bot_runs WHERE run_id = <id>`. Expect one detail request, and none on collapse and re-expand.
3. Stop the bots runner (or the worker) for more than 2 minutes while Slack Water is `running`: the stale line appears once `generated_at − checked_at > 120 s` and clears after restart.
4. Pause: rows freeze and the note reads "Paused since …". Resume: the next pass rewrites all rows with `baseline_at` = the new `status_since`. This moves the baseline, so a Buy run that began earlier is never entered (2b OWNER-1 caveat).

## Open questions

**Owner veto pending:** ORCH-6 (the detail-row *Try again* focuses *Hide* rather than the Checks heading).

**Not observed on any stack:** the `placed`, `skipped`, `observed`, `deferred`, `decided`, `pending_order`, `holding`, `already_placed`, `nothing` and `run_start_unknown` verdicts were exercised only by specs and mocks. The preview showed only `no_rows`, `no_zone`, `baseline` and `no_position`. A first bot entry (still unverified from 2b: E2E-001/002) would be the first live `placed`. No screen-reader (VoiceOver) run was done (optional). The "Checking now" and detail-loading states are DOM-verified only, with no rendered capture.

**Follow-ups recorded (not done in this build):**
- **Web:**
  - Security L1–L3: `readNullable` for the nullable watch keys and `checked_at` (the parser reads absent nullable keys as null); an identifier-shape filter for `error`; a `run_id` UUID check.
  - Unused `WATCH_COPY.region` / `CHECKS_COPY.region`.
  - `WatchCellView.hidden` is a three-state field (`null` / `""` / words); a named discriminant would be clearer.
  - Focus after *Load more* is unasserted (shared with the Decision record, design A4).
  - E2E fixture realism: NVDA is held but "Entry waits", a state the bot cannot produce; zone ages beyond the 48-row window (design A6).
  - Move the expandable-row styles to `table.css` when a second screen uses them (`DESIGN.md` inconsistency #19).
  - Graduate `formatClockSeconds` into `bangkok-time.ts`.
  - Make `e2e/tsconfig.json` type-check (20 errors at base).
  - Optional: the bots-live re-read copies the page's request headers (cookie included) into a same-origin `page.request.get`; send only `x-tidewatch-request` (security r2 L4).
- **Service:** a shared "That check doesn't exist." constant (it duplicates `msgRunNotFound`); the README's 2b route list omits portfolio (pre-existing). A usable `px:last` whose session normalises to `unknown` passes its `next_open_at` through (contract-literal; the web shows "—"). G's version lands on :00 seconds, and no `make migrate-create` transcript was kept (harmless).
- **Bot:** `bots_watch_write_failed` has no once-only memo, so a persistent failure logs every 30 s per bot (the stale line surfaces it). `pg-store.ts` has formatting-only reflows near the intake. The intake-deferral sub-case of `records deferred …` stubs the intake instead of using a real USD instrument without a rate.
- **From the D3 review:** the claim that base `1689b0c` behaves the same is unit-level only, and the probe's zero page-abort count is partly by construction (it filtered Angular's `abortInProgressLoad`).

**Known gaps carried (bot README / 2b):** a Buy run missed for 49 strip rows is never entered (R3); an interrupted run under 5 minutes old stays `running` until a later start (R12); failure isolation is per bot, not per instrument.

**Scale assumptions to revisit at slice 6:** BA4 keeps every run's outcomes (about 15 MB per bot per year); `GET /bots` still computes a `1m` portfolio per bot on every poll (2b follow-up). Slice 6's Scout/Guard loops and *Run now*, and slice 7's stats, are expected to reuse the watch and outcomes shapes.

**Drift left in `documents/` (D17):** the 2b brief has no line about bot activity; it can follow with the next documents pass.

**Preview state:** at AWAITING_MERGE the preview was kept running for manual testing at `http://127.0.0.1:49257/` (compose project `forge-0199b29a-bact-642f95ae`, isolated database at G, volumes retained). Its teardown and the removal of the e2e credential files are not recorded in state.json.

**Owner action:** apply migration G to the owner's own database (`make migrate-up` in tidewatch-migrations with their `DATABASE_URL`) before running the merged service; `/ready` stays 503 until then. G is additive with no backfill. Rollback is `make migrate-down`, which drops both objects (destructive; A–F unaffected). Rollout order was G → service and bot (either order) → web. Rolling back the bot stops the watch writes, and after 120 s the stale line shows the honest state. Rolling back the service makes the web show the sections' error state.

## Cross-cutting links

- [[zone-transition-bot]]: Slack Water, the 2b rules (R3, R6, R13, ORCH-6) that the fourteen verdicts name, and the 2b E2E rows still unverified.
- [[bot-versions-and-runs]]: `bot_runs` gains `outcomes` and `error` on the wire; runs are now listed and paged.
- [[decision-record]]: pointers from `bot_watch` and outcomes into append-only `decisions`; *then*-mode decoration reuses the record's loaded rows (ORCH-5a).
- [[paper-trading]]: the C4 lock order the watch write stays outside; C11 joins C3 and C10 as a byte-pinned shared fixture.
- [[centralized-migrations]]: migration G, `RequiredSchemaVersion` `20261010061500`, the destructive down and the harness.
- [[redis-market-contract]]: `px:last` session and `next_open_at`, the 120 s usability bound, and Redis-absent degradation.
- [[market-timeseries]]: the strip `indicators` rows and zone runs behind `bar_ts`, `zone` and `zone_age`.
- [[market-data-worker]]: the `bots` runner, 30 s cadence, `bots_*` metrics and the new `bots_watch_write_failed` event.
- [[instrument-master]]: venues, calendars and base timeframes behind `timeframe` and *Next*.
- [[gold-feed-xaut-proxy]]: XAU/USD in the universe, labelled "OANDA demo" on the Watch.
- [[design-system-decisions]]: the expandable-row pattern, one table for *now* and *then*, and the hidden-dash rule.
- [[auth-model]]: ownership answers one indistinguishable 404 for bots and runs.
- [[request-protection]]: the gated group and no-store on the three new GETs.
- [[forge-preview-gateway]]: the isolated preview, Phases A–C, the one-time journey and the admin-password restore.
- [[simulation-engine]]: the `sim` runner that fills bot orders (`placed` → `order.status`).
- [[realtime-websocket]]: nothing new on `/ws`; Bots keeps polling REST every 10 s.
