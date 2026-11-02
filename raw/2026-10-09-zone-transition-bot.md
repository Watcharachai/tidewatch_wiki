# Zone-transition paper bot (Slice 2b, `zone-transition-bot`)

> Slice 2b added the first bot that trades paper money on its own. Each user now gets a second lazily created bot, **Slack Water** (`kind = auto`, `template = zone_transitions`, `mode = paper_auto`, ฿1,000,000), next to the slice-2 `me` bot. A new `bots` runner in tidewatch-bot evaluates every running zone bot every 30 s against the latest closed strip-timeframe `indicators` row (1h, or 1d for daily-only instruments) of each watchlist instrument. It enters long with a market order when a CDC zone run turns Buy after the bot's `status_since`, and closes the whole position when the strip row reads Sell. Orders go through a bot-side intake that mirrors the service's checks, arithmetic and lock order in one transaction. The existing `sim` runner fills them. A bot exit stamps `exit_reason = 'zone'` (contract C4'). Migration F adds `bot_versions` (the config as data, content-hash version, label `v1·687c`) and `bot_runs` (one row per pass that had something new). The service gained six `/bots` routes (four reads, Pause and Resume). The web `/bots` placeholder became a Bots screen with a list, a detail, Pause / Resume, and a Decision record shared with Trade. Four PRs were merged on 2026-10-09 by the orchestrator on the owner's instruction (OWNER-2): tidewatch-migrations #5 (merge `1e115c0`), tidewatch-service #5 (`594548f`), tidewatch-bot #5 (`ac80b04`) and tidewatch-web #7 (`db96bc9`). **The bot has not yet been seen placing an order on a preview:** FR-ZB-E2E-001 and 002 are unverified because no Buy transition occurred after Slack Water's baseline before the merge. E2E-003 is partly verified, and E2E-004 is the post-merge week. The `DESIGN.md` refresh (FR-ZB-WEB-007) is in a separate web docs PR. FR-ZB-DOC-002 (OpenAPI/Bruno) is deferred.

**Sources (inputs to this document).**
- Spec: `/Users/maichinu/tidewatch/tidewatch-specs/zone-transition-bot/build-prompt.md`, `intent.md` (ZB1–ZB11, O1–O7, proposed defaults), `prd.md` (§4–§10, A1–A8), `mockup.html` (the chosen visual target for the Bots screen, ZB11)
- Build state: `/Users/maichinu/tidewatch/.forge/features/zone-transition-bot/state.json` (decisions ORCH-1…13a, OWNER-1/2; per-project execution, deviations, reviews and follow-ups; `runtime.preview.acceptanceResults`; log)
- Cross-plan rulings: `/Users/maichinu/tidewatch/.forge/features/zone-transition-bot/planning/cross-plan-decisions.md`
- Plans: `…/worktrees/329891b601/.plans/zone-transition-bot.md` (service + migration F; MF1–MF8, SB1–SB9, R1–R15, contracts C4'/C10/§6.1), `…/worktrees/6945fd5d6c/.plans/zone-transition-bot.md` (bot; R1–R23), `…/worktrees/5eb4e5c7ea/.plans/zone-transition-bot.md` (web; BW-1…BW-13)
- Merged code (read-only, at the merged heads): migrations `…/worktrees/b7ddc75378`, service `…/worktrees/329891b601`, bot `…/worktrees/6945fd5d6c`, web `…/worktrees/5eb4e5c7ea` (all under `/Users/maichinu/tidewatch/.forge/docker/runs/zbot-d1343f8c/worktrees/`)
- Evidence: `/Users/maichinu/tidewatch/.forge/features/zone-transition-bot/evidence/` (per project and step; `preview/index.md` summarises the preview phase); reviews: `…/zone-transition-bot/review/<project>/r<n>/`

## Concept

### Stage, stated precisely

| Stage | Status (state.json, last update 2026-10-09T17:45Z) |
|---|---|
| Implemented | All planned steps are done: service MIG1, MIG2 and S1–S6 (MIG steps land in the migrations repo, ORCH-1); bot S1–S10; web S1, S2, M1 (S3+S4 bundled), S5–S9. After code review: one fix round on the service (cursor check order), one on the bot (the R2 memo order), and two on the web (review fixes, then preview test fixes ORCH-13/13a). |
| Verified locally | Every step's contract commands exited 0 (`make check-disposable-db` 1016 PASS / 0 FAIL; `make ci` and `make test-integration` with no skips; `pnpm nx run-many -t lint test typecheck build` and `scripts/sql-integration.sh` on F; web unit tests (2,287 at the last fix round) and mocked Chromium Playwright 142/142). The C10 fixture is byte-identical in the service and the bot (sha256 `7f43058a…2d24`). |
| Reviewed | Service: code and security reviews APPROVED in r1, delta APPROVED in r2. Bot: code and security APPROVED in r1, delta APPROVED in r2. Web: in r1 all five reviewers (angular, tailwind, design, security, code) requested changes, with a blocking design defect B1; r2 APPROVED 5/5; r3 delta APPROVED the preview test fixes. |
| Merged | Yes, 2026-10-09 between 17:43:35Z and 17:43:59Z, in order: migrations#5 at `bbf7a87` (merge `1e115c0`), service#5 at `d87d098` (`594548f`), bot#5 at `287818a` (`ac80b04`), web#7 at `bfc9c48` (`db96bc9`). The orchestrator merged on the owner's instruction "merge now and continue" (OWNER-2). No CI is configured (D4). |
| Verified on a preview | Partly. The isolated Forge preview (compose project `forge-0199b29a-zbot-d1343f8c`, fresh database at F) ran exactly the PR heads. The mocked Bots suite, the secret scan, the runner state and the screen-against-SQL read passed. **No bot entry, restart replay or live Pause/Resume was observed.** See Test plan. |
| Running on the owner's own stack | Not recorded. The owner must apply migration F to their own database (`make migrate-up` in tidewatch-migrations); until then the service's `/ready` stays 503. FR-ZB-E2E-004 is meant to run over the first week on the owner's stack. |

### Problem

Slice 2 (merged 2026-10-08) delivered paper trading by hand only: the `me` bot, the Trade ticket, fills, marks and the graded decision record. The owner's model of "the sim" is a bot trading paper money in the background, and auto mode was not due until slice 6, after signals (3), the Signals page (4) and charting (5). The owner had accepted "manual first" on condition that a bot follows soon. A rules-only bot on CDC Action Zone transitions needs no signals: the `indicators` rows with `cdc_zone` already exist for every closed 15m/1h/1d bucket, written within 60 s of the bucket's close. The approved mockup already names this bot: **Slack Water**, "Zone transitions · v1", "CDC zone changes as the only trigger" (intent "Problem and evidence").

### Chosen design (owner decisions ZB1–ZB11, confirmed 2026-10-09)

The owner accepted the recommended answer to Q1–Q10 as a block ("Agree all continue"), then chose one mockup direction (ZB11).

- **ZB1 Rules.** Enter long on a transition into `buy`; close on a transition into `sell`. Long only, market orders, one position per instrument, no adds, trims, stops or time limit. Rejected for now: a tighter exit on leaving `buy`, and GO shorts. Both can be later versions of the same bot.
- **ZB2 Timeframe.** The strip timeframe (1h; 1d for daily-only instruments such as PTT.BK), recorded in the version config. 1d for everything was rejected (a handful of trades a month), and so was 15m (noise).
- **ZB3 Universe.** The owner's watchlist at evaluation time, tradable classes only, excluding manual-fill venues (Gold 96.5 at MTS) and futures (GO), both via config flags. An instrument removed from the watchlist with an open position is still managed to its exit. Default universe: NVDA, AAPL, PTT.BK, BTC/THB, ETH/THB, XAU/USD.
- **ZB4 Sizing.** 10% of current equity per entry, quantity rounded down; at most 6 open positions; a blocked entry writes a `skip` decision with reasons. Rejected: 20% / 4, and 1/n of starting capital.
- **ZB5 Bot-side intake.** A `placeOrder` in tidewatch-bot runs the service's check order with the shared arithmetic and the C4 lock order in one transaction. No HTTP, no credential, no service change for intake. Rejected: a service endpoint with a service token (breaks "no HTTP between them", adds a secret) and a Postgres function (large refactor). Accepted cost: a second implementation of the money and limit checks, pinned by a scenario fixture.
- **ZB6 Creation.** The service creates Slack Water lazily beside `me`, one per user, inside the trust boundary. Rejected: creation at `serve` start (puts user-scoped creation in the worker), and *Create bot* (slice 6).
- **ZB7 Running from day one.** Status `running` at creation; Pause and Resume on the Bots screen; the runtime honours `observing` but nothing sets it in 2b. A 30-day probation was rejected because the point of 2b is to watch it trade.
- **ZB8 Web.** A minimal Bots screen: the list for `me` and Slack Water, a detail with figures, positions and the decision record, Pause / Resume. Overview and Trade stay `me` only. Rejected: no web change (hides the bot) and a bot switcher on Trade (muddles the manual account).
- **ZB9 Schema.** Migration F: `bot_versions`, `bot_runs` and three `bots` columns. Rejected: `bots.config` with no runs table (loses the difference between a quiet bot and a broken one), and the full slice-6 set (premature).
- **ZB10 Documents.** The spec session itself wrote `documents/features/02b-zone-transition-bot.md` and the 2b roadmap and README rows. Builds never edit `documents/` (D17).
- **ZB11 Mockup.** `mockup.html`: one direction, real tokens, both themes, every screen state. Where it differs from the approved mockup's Bots screen, it wins; where it differs from `DESIGN.md`, `DESIGN.md` wins.

### Proposed defaults the build implemented (PRD "PD"; not owner decisions)

- **Entries are transition-driven; exits are state-driven.** An entry needs a Buy zone run that started at or after `bots.status_since` and has no bot decision yet; the bot acts once per (instrument, zone run), with an order or a `skip`. An exit fires whenever the bot holds a position and the latest strip row is `sell`, including right after a resume and when the Sell row landed while the venue was closed.
- **The baseline resets on resume.** `status_since` marks the start of the current `running` stretch. Pausing cancels no pending order and closes no position.
- **Deferral is not a decision.** A closed venue or no live price writes nothing and is retried on the next pass. Insufficient cash, the position or exposure limit, `max_open` and a zero quantity each write a `skip`, which closes that run.
- **Version hash.** The SHA-256 of the canonical JSON config (keys sorted recursively, no whitespace, every number a decimal string). The label is `v{seq}·{first 4 hex}`. The real v1 label is **`v1·687c`**; the intent and mockup used `v1·c7e8` as an illustration (service R2, bot R14).
- **Idempotent placement.** `client_order_id` is a UUIDv5 of (`bot_id`, `instrument_id`, entry + zone run start, or exit + the position's `opened_at`), so `UNIQUE (bot_id, client_order_id)` refuses a replay.
- **Audit.** The bot writes `order_placed` / `decision_skipped` with a null actor; Pause/Resume write `bot_status_changed` with the session user as actor.

### Cross-project contracts (service plan; `planning/tidewatch-service/contracts.md` r2)

- **C10 `bot-version.v1.json`.**
  - Byte-identical copies, 1,437 bytes, file sha256 `7f43058aeb71930da9a5ecd0a57fa9caeaddadcb8e0af412032deef733762d24`:
    - service `internal/trading/testdata/bot-version.v1.json`, pinned by `TestBotVersion_FixtureHash`;
    - bot `packages/bots/fixtures/bot-version.v1.json`, pinned by `bot-version-fixture.spec.ts`.
  - v1 version `687c7ad37f7e7b531eab74efc79b24117d76360d70e5dd4cffa8f71bc4c47f68`, seq 1, label `v1·687c`.
  - Both sides hash `canonical(config)`, never the stored jsonb text. A raw JSON number in a config is refused.
  - Changing the fixture is a contract change in both repos at once, like C3.
- **C4' close stamp.** The only change from slice 2's C4 is that `'user'` became `$4`:

```sql
UPDATE decisions
   SET exit_reason = $4, closed_at = $3
 WHERE bot_id = $1 AND instrument_id = $2
   AND action IN ('buy', 'add', 'sell')
   AND exit_reason IS NULL AND closed_at IS NULL
   AND decision_id IN (SELECT decision_id FROM orders
                        WHERE bot_id = $1 AND instrument_id = $2 AND status = 'filled');
```

  - The bot's `CLOSE_STAMP` is the same text without the final `;`.
  - `$4 = 'zone'` only when the closing order's decision has `actor = 'bot'` and `policy_result->>'rule' = 'exit'`. The sim fill pass reads this under the account lock, after the fill guard and before the stamp.
  - The service's `StampClose` keeps its signature and always binds `'user'` (`ExitReasonUser`). `StampCloseReason` exists so an integration test can prove that `'zone'` binds.
  - The service and bot PRs had to merge together.
  - `decisions.exit_reason` already allowed `'zone'` (migration E), so C4' needed no schema change.
- **§6.1 wire shapes** (see API). **F's version** `20261009122143` was an execution output of MIG1 (ORCH-4/4a).
- **C3 (arithmetic), C5, C6 (mark price), C7 (wire formats)** are reused unchanged. The bot's intake calls `packages/sim`'s `marketPrice`, `divFloor`, `valueAccount` and `readMarkContext` (bot R16), so the bot never re-implements a price, fee or rounding rule.

### Owner decisions during the build

- **OWNER-1.** The preview uses an isolated database, with volumes retained after merge. The live Pause/Resume check (E2E-003, `E2E_BOTS_PAUSE=1`) runs only after the first entry and the restart check are captured, because a resume moves `status_since` and would drop any Buy run that began earlier.
- **OWNER-2.** "Merge now and continue." The orchestrator merged the four PRs in order: migrations, then service + bot, then web. E2E-001/002 and the live Pause/Resume part of E2E-003 are recorded as **unverified, not failed**: no Buy transition had occurred after the bot's baseline. The first-entry wait keeps running on the preview while docs and cleanup proceed, and any entry it captures is added as evidence.
- **ORCH-6: owner-visible revision of PRD §8.4, accepted pending the owner's veto.**
  - PRD §8.4's proposed default is that a failing pass leaves a failed run. For an **unsupported version** (another config, a `current_version` that is not the hash of its config, or none), the bot instead writes **one** `failed` run (`error = version_unsupported`, zero counts) per (bot, version) per runner run, then no new run until the version changes or the runner restarts. This avoids about 2,880 failed runs per bot per day.
  - Visible cost: the Bots screen's *Last check* stays at the first failure.
  - A null `current_version` cannot carry a run (`bot_runs.bot_version` is NOT NULL with an FK), so it is logged and counted without one.
  - Review fix (ORCH-12): the "already reported" memo is set only after the failed run is written, so a store outage retries it.
  - Every other failure class keeps PRD §8.4.
  - Listed in the bot README's Known gaps; asserted by the specs `version guard` and `version guard retries the failed run until the store has written it`.

### Orchestrator rulings (ORCH-1…13a)

- **ORCH-1.** Migration F was planned as MIG steps inside the service plan, because the validators accept only registered projects. The migrations repo kept its own worktree (`b7ddc75378`), branch and PR, and its billets live in the service namespace.
- **ORCH-2.** The service planner pinned C10's bytes and hash, the C4' text and the §6.1 shapes in `contracts.md`. The bot and web planners conformed to it before returning ready.
- **ORCH-3 → ORCH-5.** ORCH-3 had accepted no `/trade` call on the Bots screen. Web review B3 showed that prices then lose their tick-size digits (189.10 shows as 189.1), which breaks parity with the mockup (FR-ZB-WEB-001, P0). ORCH-5 superseded it: the web reads `GET /trade` **once per Bots screen open**, through the existing `TradeApi`, only for `tradable_instruments`, and never polls it. The design reviewer was told that the mockup's "0.746 oz" never renders in production (pre-existing `positions-table` behaviour). ORCH-5 also asked the web to render the `observing` reason.
- **ORCH-4 / 4a.** F's version is MIG1's output (`20261009122143`), recorded in cross-plan-decisions rather than `contracts.md`, whose r2 bytes the plans cite.
- **ORCH-7.** Dependency-gated lanes with smelt bundling (owner choice). Gates: bot S1 after service plan approval; bot S7 after service S1 (C10); bot S8 after MIG1 (F); web S8 after service S4+S5.
- **ORCH-8.** `limits.max_open` is the string `"6"`: the PRD and C10 win over the intent's numeric `6`. Resume on an `observing` bot answers 409 `bot_status_conflict`.
- **ORCH-9.** After web plan r2, a bounded polish round. Captures wait for the `/trade` read, requirement IDs were aligned with the matrix, and a README line covers a failed `/trade` read.
- **ORCH-10.** Service fix round after an approved r1: the decisions cursor's syntax is decoded before ownership (400 per contracts r2) and its bot binding is checked after the bot resolves; the migrations README probe count was corrected to 14. Three performance items became follow-ups.
- **ORCH-11.** Preview evidence (rendered WEB-001/005/006 on a fresh isolated DB, the design verdict, E2E-001…003) gates the **merge**, not the PR. This follows slice 2's ORCH-25 precedent.
- **ORCH-12.** Bot fix round after an approved r1:
  - the R2 memo order;
  - "more than 5 minutes" wording;
  - `sqlStateOf` restricted to pg `DatabaseError`;
  - six zero counts on interrupted runs.

  Per-instrument failure isolation and stopping mid-pass became follow-ups.
- **ORCH-13.** A latent slice-2 test defect blocked the full Playwright suite on the fresh preview DB, which the DoD requires. In `e2e/src/paper-orders.spec.ts:142`, the regex `/^1,000$/` can never match the Open orders Limit cell (" 1,000 "). The one-line, test-only fix `/^\s*1,000\s*$/` went into web PR #7 outside the plan's Files and was delta-reviewed.
- **ORCH-13a.** In the same spec, `FILL_WITHIN_MS` was raised from 120 s to 150 s. It measures from placement to the UI showing the fill, which adds up to one 10 s screen refresh; on the preview a fill took about 110 s. The product's 2-minute claim is now measured in SQL instead. Slice-2 follow-up: under the next-bar rule a fill can take slightly over 2 minutes in the worst case.

### Plan resolutions worth knowing (each recorded, none chosen silently)

**Service** (R1–R15, SB1–SB9)
- **SB2 / R5.** `EnsureAccount` remains, as "`EnsureBots`, then return the manual bot". Every slice-2 caller therefore creates both bots without editing the PRD-stable `place.go`. The cancel route creates them too (R6: a harmless superset of PRD §4.1's list).
- **R4.** `TestRouter_NoDecisionMutation`, which banned `:bot_id` routes, was revised on purpose:
  - only the reviewed `:bot_id` routes may exist;
  - no route may take `:decision_id`;
  - only GET is allowed under `/bots/:bot_id/decisions`.
- **R7.** The "30-day" maximum drawdown is the `1m` portfolio's `max_drawdown_pct`, which is the whole-ledger figure, so the detail card says "since start".
- **R8 / R15.** Slice-2 tests that assumed one bot per user were re-scoped to the manual bot on purpose. The unit fake now keys bots by owner and kind and filters ledger reads by bot.
- **SB5.** Pause/Resume lock `bots … FOR NO KEY UPDATE` and never the account row. This does not conflict with the `FOR KEY SHARE` that the bot's FK checks take.

**Bot** (R1–R23)
- **R1 On-demand run.** A deferred entry placed at the next open, or a skip, can land on a pass with no new strip row. In that case the run row is created inside the first intake transaction that writes a decision, so every bot decision carries a real `run_id`, and a rolled-back or decision-free intake leaves no run.
- **R3 Zone run window.** The start is the earliest row of the trailing same-zone streak within the latest 49 strip rows. If the streak fills all 49 rows, the start is unknown and the run is never entered. Otherwise a sliding window would invent a new start every bar.
- **R4.** One count-based read of the latest 49 strip rows per instrument, bounded like the service's `stripQuery`. It replaced `lastIndicator` + `indicatorsBetween`, whose time window cannot guarantee 48 rows for session-only US bars.
- **R5.** Universe, rule, session and price are read outside any transaction. The status re-read, idempotency, side, valuation, quantity and limits run after `paper_accounts … FOR UPDATE` on one connection. A missing USD/THB rate rolls back and counts as a `price_unavailable` deferral.
- **R6 Observing decisions.** Shaped like a skip, with `reasons = ["observing"]`: no order, no reservation, no event. An observing exit is recorded once per sell run.
- **R13.** `status_since` follows a bucket-start rule: a Buy bucket that began before a creation or resume is baseline, even if it closed after it.
- **R20 Pause race.** The bot never locks the `bots` row; it re-reads `status` inside the intake transaction. So at most one order from a pass that began before a pause can land.
- **R22.** `inSession` on the instrument's calendar stands for "`px:last` session = open", because the recorded price view does not keep the session. It is the same rule on the same data, at most about a minute more current.

**Web** (BW-1…BW-13)
- **BW-2.** The three new `Decision` fields are **optional** on the type and always set by the parser. This lets slice-2's typed fixtures, including the guarded `trade.spec.ts`, compile unchanged (A8).
- **BW-4.** `app-decision-record` takes function inputs (`loadMore`, `retry`) rather than outputs, so it can await the outcome as before.
- **BW-5.** A decision counts as a bot decision when `policy_result` is not null; every other row keeps the slice-2 path byte for byte.
- **BW-12.** The live Pause/Resume Playwright test is gated by `E2E_BOTS_PAUSE=1`, Chromium only, and always ends with Slack Water running.

## Database

Migration F, `migrations/20261009122143_bot_versions_and_runs.sql` in tidewatch-migrations, runs in goose's default transaction. Its version **`20261009122143`** is the new `RequiredSchemaVersion` (`internal/platform/postgres/schema.go`). A database migrated only through E is `/ready` 503 (`required version 20261009122143 not applied`). The bot has no schema constant; `scripts/sql-integration.sh` asserts F is applied. The previous pin was E `20261008050550`.

```sql
CREATE TABLE bot_versions (
    bot_id             uuid        NOT NULL REFERENCES bots (bot_id),
    version            text        NOT NULL CHECK (version ~ '^[0-9a-f]{64}$'),
    seq                integer     NOT NULL CHECK (seq > 0),
    config             jsonb       NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    created_by_user_id uuid        REFERENCES users (id),
    PRIMARY KEY (bot_id, version),
    UNIQUE (bot_id, seq)
);

CREATE TABLE bot_runs (
    run_id      uuid        PRIMARY KEY DEFAULT uuidv7(),
    bot_id      uuid        NOT NULL REFERENCES bots (bot_id),
    bot_version text        NOT NULL,
    loop        text        NOT NULL CHECK (loop IN ('scout', 'manager', 'guard')),
    trigger     text        NOT NULL CHECK (trigger IN ('scheduled', 'manual')),
    started_at  timestamptz NOT NULL,
    finished_at timestamptz,
    status      text        NOT NULL CHECK (status IN ('running', 'succeeded', 'noop', 'failed')),
    counts      jsonb       NOT NULL DEFAULT '{}',
    error       text,
    FOREIGN KEY (bot_id, bot_version) REFERENCES bot_versions (bot_id, version),
    CHECK ((status = 'running') = (finished_at IS NULL))
);

CREATE INDEX bot_runs_bot_started_idx ON bot_runs (bot_id, started_at DESC);

ALTER TABLE bots
    ADD COLUMN template text NOT NULL DEFAULT 'manual' CHECK (template IN ('manual', 'zone_transitions')),
    ADD COLUMN current_version text,
    ADD COLUMN status_since timestamptz NOT NULL DEFAULT now(),
    ADD CONSTRAINT bots_current_version_fkey FOREIGN KEY (bot_id, current_version) REFERENCES bot_versions (bot_id, version),
    ADD CONSTRAINT bots_kind_template_check CHECK ((kind = 'manual') = (template = 'manual'));

UPDATE bots SET status_since = created_at;   -- backfill; existing rows get template 'manual' from the default
```

- **Write order (MF3).** `bots_current_version_fkey` is MATCH SIMPLE, so a NULL `current_version` (the manual bot) goes unchecked. A writer must insert `bots` with NULL, then `bot_versions`, then `UPDATE bots SET current_version`.
- **Status values.** `bot_runs.status` adds `running` to the architecture document's three values (`succeeded|noop|failed`), so an interrupted pass stays visible. This drift is recorded in PRD §10; `documents/` was not edited (D17).
- **One zone bot per user** is enforced by the service under its advisory lock. No unique index enforces it, because slice 6 creates more bots per template.
- **Unchanged tables.** `decisions`, `orders`, `fills`, `positions` and `ledger` are untouched. `decisions` stays append-only, and `decisions.run_id` has no FK (service R10).
- **Down** drops the two named constraints, then the three columns, then `bot_runs` and `bot_versions`, each `IF EXISTS` and never `CASCADE`. It is destructive (every version and run) and owner-only.
- **Harness.** `scripts/check-disposable-db.sh` gained F's expected lists, catalog assertions, absent checks and transcripts, plus:
  - 14 rolled-back probes that must be refused: kind/template both ways, running with `finished_at`, succeeded without it, a dangling `current_version`, a non-hex version, `seq = 0`, a duplicate seq, a run naming no version, and others;
  - controls inserting a zone bot with the C10 v1 hash;
  - a backfill proof with a planted pre-F manual bot in the down/up window.

  E's exact `bots` checks became F-aware in the harness only; E's file is unchanged. Result: **1016 PASS / 0 FAIL** (MIG1).

## API

All six routes are on tidewatch-service, mounted by `mountBots` on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`. The engine-wide CSRF check covers the two POSTs. Every route runs `EnsureBots` first. The gated-route count test now counts **32** (29 production + 3 probes; it was 26).

| Method and path | Request | 2xx response | Errors |
|---|---|---|---|
| `GET /bots` | — | `{generated_at, items: [BotSummary]}`: manual bot first, then `created_at`, then `bot_id` | — |
| `GET /bots/{bot_id}` | — | `{generated_at, bot: BotSummary, version: {seq, hash, label, config, created_at} \| null, account, positions, open_orders}`: the exact `GET /trade` shapes for that bot | 404 |
| `GET /bots/{bot_id}/decisions` | `limit` 1–200 (default 50), opaque `cursor` bound to the bot | `{items: [Decision], next_cursor}` | 400, 404 |
| `GET /bots/{bot_id}/portfolio` | `period` ∈ `1w`/`1m`/`3m` (default `1m`) | the `GET /portfolio` body for that bot | 400, 404 |
| `POST /bots/{bot_id}/pause` | no body, no query | 200 bare `BotSummary` | 400 `manual_bot`, 404, 409 `bot_status_conflict` |
| `POST /bots/{bot_id}/resume` | no body, no query | 200 bare `BotSummary` | 400 `manual_bot`, 404, 409 `bot_status_conflict` |

**`BotSummary`** = `{bot_id, name, strategy_label, template, kind, mode, status, status_since, created_at, version: {seq, hash, label} | null, equity, return_30d: {abs, pct}, max_drawdown_pct, decisions_30d: {count, orders, skipped}, last_run: {run_id, loop, trigger, started_at, finished_at, status, counts} | null}`.
- The figures are the bot's `1m` portfolio at one instant: `equity_now`, `return_period`, `kpis.max_drawdown_pct` and `kpis.decisions`. So `GET /bots` and `GET /bots/{id}/portfolio?period=1m` agree.
- `last_run` is the newest `bot_runs` row by `started_at DESC, run_id DESC`, with `counts` as stored; it is null for `Me`.
- The list and the detail read in one `REPEATABLE READ READ ONLY` snapshot.

**Check order.**
1. CSRF (POSTs).
2. The gates.
3. The strict query parse: 400 `invalid_request` with `{field, reason}`; Pause/Resume accept no query parameter.
4. A malformed decisions cursor: 400.
5. A `bot_id` that is not a UUID, absent, or another user's: **one indistinguishable `404 not_found`** ("That bot doesn't exist."), never 403. Every repository query carries `owner_user_id`.
6. The route checks. A well-formed cursor bound to another bot is 400 on the caller's own bot and 404 on a foreign one.

**Pause / Resume (PRD §4.8).**
- Pause moves `running|observing → paused`; Resume moves `paused → running`.
- Each runs one transaction: lock the `bots` row `FOR NO KEY UPDATE`, refuse the manual bot, refuse a held status, set `status` and `status_since`, write the audit row.
- The metric and log come after the commit. The summary is read in a fresh snapshot.
- 409 messages: "That bot is already paused." / "That bot is already running." / "That bot isn't paused." (resume on `observing`).
- A paused bot is not evaluated; its pending orders still fill and its positions stay open.

**Changes to slice-2 routes.**
- `Decision` gains `bot_version` (string|null), `run_id` (uuid|null) and `policy_result` (object|null), always present, on `GET /decisions` and on the bots decisions route.
- `Position.opened_by` is the owning bot's name: "Me" on `/trade`, "Slack Water" on the bot detail.
- There is still no route that creates, updates or deletes a bot, a version or a decision.

**Lazy creation (`EnsureBots`, PRD §4.1).**
- Fast path: one lock-free read. Otherwise, under the existing `pg_advisory_xact_lock(MeBotLockKey(user))`, one transaction creates whichever of `Me` and Slack Water is missing.
- Slack Water's rows:
  - `bots`: "Slack Water", "Zone transitions", `auto`, `zone_transitions`, `paper_auto`, `running`, `status_since` = `created_at` = the service clock, limits 0.25 / 1.00;
  - its paper account with ฿1,000,000.00;
  - the slice-2 benchmark snapshot;
  - the initial `fill` ledger mark;
  - the C10 v1 `bot_versions` row (`created_by_user_id` NULL) and `current_version`.
- Ten concurrent first requests create exactly one of each.

**Error code.** `bot_status_conflict` (409) is appended to `AllCodes()`. `400 invalid_request` gains `details.reason = manual_bot`, with no `field`.

**Audit events (`events`).**
- `bot_status_changed {bot_id, from, to}`, with the session user as actor and request metadata.
- From the bot, with a null actor: `order_placed {order_id, instrument_id, side, type, qty, manual_fill, bot_id, run_id}` and `decision_skipped {decision_id, instrument_id, bot_id, run_id}`.

**Service metrics and logs.**
- `bot_status_changes_total{to}` (`paused`, `running`; exported at 0; an unknown value is ignored).
- Logs: `bot_status_changed`, and `paper_account_created` now carries `template`.

### Bot runtime (`tidewatch-bot` `packages/bots`; no HTTP to the service)

- **Runner.**
  - `bots` is the last of the eleven `COLLECTOR_NAMES` (after `sim`), on by default, and holds lock `runner:bots`. It has no venue budget and restarts with the usual backoff.
  - It reads PostgreSQL, the reference cache and the recorded `px:last` view that `serve` shares with `sim`, never Redis.
  - Disabling it leaves zone bots idle. With `sim` disabled, bot orders stay pending.
  - No new environment variable. `MARKET_DATA_COLLECTORS` accepts `bots`. Compose is unchanged.
- **Cadence.**
  - One pass at start, then every `BOTS_EVAL_INTERVAL_MS` = 30 s from the previous start. Passes never overlap.
  - Before the first pass, `running` runs older than `INTERRUPTED_RUN_AGE_MS` (5 min) are finished `failed`, `error = interrupted`, with six zero counts.
- **Pass.**
  1. Read the zone bots (`kind = auto`, `template = zone_transitions`, `status ∈ running|observing`, by `created_at`).
  2. Validate the version. It must be exactly v1 **and** `current_version` must equal the hash of the canonical config (R9).
  3. Resolve the universe.
  4. Read the strip rows (R4).
  5. Fire the rules.
  6. Check session and price outside any transaction: `inSession`, and a recorded `px:last` that is not stale with `updated_at` within 120 s. A miss defers `venue_closed` / `price_unavailable` and writes nothing.
  7. Run the intake.

  One bot's failure finishes its run `failed` with the error class (a constructor name, never a message) and the pass moves on.
- **Run records.**
  - A run row (`loop = manager`, `trigger = scheduled`) opens when an instrument has a newer strip row than the in-memory last-seen `ts`, or at start.
  - It finishes `succeeded` when a decision was written, else `noop`, with `counts = {instruments, new_bars, entries, exits, skips, deferred}`.
  - A pass with nothing new and nothing written writes no run.
- **Intake (`placeAction`), in one transaction with `SET LOCAL statement_timeout` 10 s.**
  1. `paper_accounts … FOR UPDATE` is the first statement.
  2. Re-read the status.
  3. Idempotency: `client_order_id`, then the decision key.
  4. Side.
  5. `equity_now` via `valueAccount` (R19), with the rule-4 USD/THB for USD spot.
  6. Quantity: `budget = round2(equity_now × 0.10)`. The estimate price is last + slippage against a buyer. `qty` is rounded **down** to `lot_size`, else to `QtyDecimals` (8 for US shares, 0 for SET, the lot digits for crypto).
  7. Limits, collected in order: `insufficient_cash`, `position_limit`, `exposure_limit`, `max_open`; `qty_below_minimum` when `qty ≤ 0`.
  8. Writes: the on-demand run (R1), the decision (`actor = bot`, `loop = manager`, `run_id`, `bot_version`, SV10 `market_state`, `policy_result`), the pending market order (`placed_by_user_id` NULL, `reserved_cash` = required for an entry, 0 for an exit), `reserved += required`, and the `order_placed` event.
  - A replay hits `ON CONFLICT (bot_id, client_order_id) DO NOTHING`, rolls back and reports `already_placed`.
- **`client_order_id`.** UUIDv5 in namespace `fef2c136-2402-56d4-a3a7-055c50a372d0` (= UUIDv5(URL, `urn:tidewatch:bots:client-order-id:v1`)) of `{bot_id}|{instrument_id}|entry|{zone_run_started_at}` or `{bot_id}|{instrument_id}|exit|{position.opened_at}`. Instants are RFC 3339 UTC with a millisecond fraction only when it is non-zero (R7).
- **`policy_result`.** `{passed, rule: entry|exit, trigger: zone_turns_buy|zone_is_sell, timeframe, bar_ts, zone_run_started_at, reasons: []}`. Decision `action` is `buy` / `close` / `skip`; `direction` follows the order side (`long` / `short`).
- **Metrics** (closed label sets, at 0 from start):
  - `bots_passes_total{result}` (`acted`, `noop`, `failed`, `nothing_new`)
  - `bots_runs_total{status}` (`succeeded`, `noop`, `failed`)
  - `bots_decisions_total{action}` (`buy`, `close`, `skip`)
  - `bots_deferred_total{reason}` (`venue_closed`, `price_unavailable`)
  - `bots_pass_duration_seconds`
  - `bots_running` (gauge; observing bots are not counted)
- **Logs.** `bots_pass_started` (debug), `bots_run_finished`, `bots_order_placed`, `bots_decision_skipped`, `bots_action_deferred` (once per memo key: bot, instrument, rule, run start, reason), `bots_version_unsupported` (warn), `bots_pass_failed` (error). They never carry a `key` field, a message, a body or a token.
- **Concurrency.** The store serialises every method on one queue and connection, so `SERVE_POOL_MAX` stays 12. The S8 integration evidence shows:
  - the account lock is held first;
  - a `NOWAIT` probe gets 55P03 while it is held;
  - the intake waits before reading bot status;
  - a bot entry and a sim fill serialise in both orders.

## Components

Angular, under `src/app/pages/workspace/`. `DESIGN.md` rules apply: no Material, CDK or chart library, no `dark:`, tokens only in `tokens.css`, no new colour or token, native controls.

**Bots screen (`feat-bots/`, replaces the slice-0 `/bots` placeholder; lazy route in `workspace.routes.ts`).**
- **`app-bots`** (`bots.ts`) provides the component-scoped `BotsService` (SE-5).
  - Header "Bots", sub line "{n} bots · paper mode" ("Loading…" before the first load).
  - The list `section.section`: heading with `.count`, the note "Paper money · a version never changes", and one polite status region with "Loading bots…" or "Bots couldn't load." plus *Try again*, which focuses the list heading.
  - Then `app-bot-detail` for the selected bot (the first auto bot by default), then one `app-toast`.
  - A keyboard selection focuses the detail heading after render; a pointer selection does not move focus.
- **`app-bots-list`** (`bots-list.ts`).
  - Inputs `bots`, `selectedId`. Output `choose` emits `{botId, keyboard}`. It is named `choose` because `@angular-eslint/no-output-native` refuses `select`.
  - A `table.tide.bots` in a named scroll region "Bots, scrollable table".
  - Columns: Bot (a native `<button aria-pressed>` name, mono version label `v1·687c`, `.second` strategy line), Mode, Status (neutral `.tag`; "—" for the manual bot), 30 days (tone class), Max drawdown, Decisions, Equity (whole baht).
  - The selected row has `.selected`. Rows are quiet (MW-23).
- **`app-bot-detail`** (`bot-detail.ts`) reads the store.
  - Head: the name, a mono version tag and a status tag. *Pause* / *Resume* is a `.btn` with `aria-busy` showing "Pausing…" / "Resuming…". The manual bot shows a *Manual* tag and no button.
  - The strategy sentence, derived from `version.config`: "Enters when the 1h zone turns Buy (1d for daily instruments), exits when it turns Sell. Long only, market orders, 10% of equity per entry, at most 6 positions. Universe: your watchlist, no manual venues, no futures." Config outside the v1 vocabulary falls back to "{strategy_label}. Rules as set in {label}.", so no raw config value is ever shown.
  - A `.metric-strip` of four cards: *Equity*, *Return since start*, *Max drawdown*, *Last check*. Last check notes: "{n} instruments · no action", "1 entry", "paused since 9 Oct 14:02", "observing · no orders", "checking now", "last check failed", "no check yet".
  - Positions (`app-positions-table`, reused unchanged; *Opened by* "Slack Water").
  - `app-decision-record` with the bots note and the empty sentence "No decisions yet. Slack Water acts when a zone turns Buy or Sell on a closed 1h bar."
  - Exposes `focusHeading()`.
- **`BotsService`** (`feat-bots/data/bots.service.ts`, `@Service({ autoProvided: false })`).
  - `GET /bots` every `BOTS_POLL_INTERVAL_MS` = 10 s.
  - The selected bot's detail, `portfolio?period=1m` and first decisions page every 10 s, as one reload point.
  - A selection change aborts the old bot's requests and never shows its data under the new name. Keep-last applies on a failed background refresh. *Load more* is aborted on select/destroy (review fix).
  - **One `GET /trade` per screen open** for `tradable_instruments` (ORCH-5). It is never polled; a failed read is retried only by *Try again*.
  - `toggleStatus()` returns `paused | resumed | already | failed`:
    - 200 applies the returned summary, then reloads;
    - 409 reloads with "Slack Water was already {paused|running}.";
    - 400/404/5xx leave the status and show "Couldn't change Slack Water. Try again.";
    - a 2xx body that cannot be parsed triggers a reload.

    The store never computes a status itself.
- **`util/bot-view.ts`**: `BOTS_COPY`, `botRowView`, `strategySentence`, `figuresView`, `lastCheckView`, `statusToast` (pure, table-tested).

**Shared with Trade.**
- **`app-decision-record`** (`feat-trade/decision-record.ts`) was refactored from `inject(TradeService)` to inputs. Required: `rows`, `state`, `loadMore` (function), `retry` (function). Optional: `hasMore`, `loadingMore`, `instruments` (default empty map), `note`, `emptyText` (defaults are Trade's copy). The `toast` output stays. `trade.ts` binds them from the same store members. Trade's specs (`trade.spec.ts`, `merge-decisions.ts` and their e2e) are byte-unchanged and green (A8).
- **`util/order-view.ts`** gains a bot branch, keyed on `policy_result != null`:
  - Line: "Buy NVDA 16.2", "Close NVDA 16.2", "Skip NVDA" (a skip never shows its quantity).
  - Second line: "zone turned Buy · market · filled 187.63" / "· pending"; "zone turned Sell · …"; for a skip, the first reason's words ("insufficient cash", "position limit", "exposure limit", "max open positions", "quantity below minimum", "observing"; an unknown code reads "skipped").
  - Signal: "CDC zone · 1h" / "· 1d". *Followed?*: "—".
- **`util/bangkok-time.ts`**: `formatClock` ("14:30") and `formatDayMonthTime` ("9 Oct 14:02").

**Data layer (`data/`).**
- `bots.model.ts`: `BotSummary`, `BotVersion`, `BotDetail`, `BotsList`, `BotRun` with tolerant parsers. The parser **requires `bot_id` to be a UUID**: security review L1 found that a `.`/`..` id escapes `/bots/` after URL encoding.
- `bots-api.service.ts`: `BotsApi`, the only place with `HttpClient` for these routes. Ids go through `encodeURIComponent`, the cursor through its own strict codec, and errors through `toTradeApiError`.
- `trade.model.ts`: `Decision` gains the three optional fields (BW-2).

**Styles.**
- `.metric-strip` moved verbatim from `portfolio.css` to `metric-card.css`. Overview renders identically: 0-pixel diffs at 1440/820/600 in both themes (A7).
- `table.css` gains the reusable selected row `.tide tr.selected` (`--surface` fill and an inset 3px `--brand` bar) and the selectable-row button `.tide .name button[aria-pressed]` (reads as text, `--brand` hover, `cursor: pointer`).
- New `bots.css` (imported after `trade.css`, before `zone.css`):
  - `.bots .ver`, the mono version tag and the strategy sentence;
  - a head button `min-width` of 88px, so "Resuming…" never clips;
  - the ORCH-30 busy style `.bot-detail .btn[aria-busy="true"]` (AA instead of fading);
  - the metric-strip margins, 28px section spacing and the head wrap at ≤ 600;
  - `--text-2` `.muted`/`.when` cells and centred load errors, scoped to `.bots-screen`. This was design-review blocker B1: Trade's rules were scoped to `.trade` and did not reach Bots.
- `DESIGN.md` and `tokens.css` were unchanged at merge. Documenting the selected-row pattern and the Bots screen is FR-ZB-WEB-007, in a separate web docs PR.

## Files touched

The file lists below come from each approved plan's Files lists. They are cross-checked against the orchestrator's per-step scope checks ("all changed files within plan Files") and the file counts of the reviewed diffs. No `git diff` was run for this document.

| Repo | Range (base..PR head) | Merge | Files |
|---|---|---|---|
| tidewatch-migrations | `6531508..bbf7a87` | `1e115c0` | 4 |
| tidewatch-service | `857d420..d87d098` | `594548f` | 50 |
| tidewatch-bot | `6902f4e..287818a` | `ac80b04` | 70 |
| tidewatch-web | `7c7b602..bfc9c48` | `db96bc9` | 43 (42 planned + `paper-orders.spec.ts`, ORCH-13) |

### tidewatch-migrations (PR #5)
- `migrations/20261009122143_bot_versions_and_runs.sql` (created): migration F.
- `scripts/check-disposable-db.sh` (modified): F's lists, assertions, probes, backfill proof; E's checks made F-aware.
- `README.md`, `CLAUDE.md` (modified): F's objects, write order, destructive down; required version moved from E to F with the anchored lookup.

### tidewatch-service (PR #5)

**Docs.** `README.md`, `CLAUDE.md` (modified): `/bots` routes and shapes, code and reason, audit event, metric, lazy creation of both bots, C4', C10, the 32 gated routes, named tests, required schema version F.

**Composition, platform, harness.**
- `internal/app/router.go` (modified): `mountBots`; `handlers.BotsService` in `tradingService`.
- `internal/platform/postgres/schema.go` (modified): `RequiredSchemaVersion = 20261009122143`.
- `internal/pgtest/migrate.go` (modified): anchored `_bot_versions_and_runs.sql` lookup.
- `scripts/integration-test.sh` (modified): exactly-one check for F.
- Tests: `internal/app/router_test.go` (gated count 32, R4 `TestRouter_NoDecisionMutation`, `TestCSRF_BotMutations`).

**Errors, audit, metrics.**
- `pkg/apperror/codes.go`, `pkg/apperror/apperror.go` (modified): `bot_status_conflict`, reason `manual_bot`.
- `internal/audit/audit.go` (modified): `TypeBotStatusChanged` with typed detail.
- `internal/observability/metrics/trading.go`, `metrics.go` (modified): `bot_status_changes_total{to}`, `BotStatusRecorder`.
- Tests: `pkg/apperror/codes_test.go`, `apperror_test.go`, `internal/audit/audit_test.go`, `internal/observability/metrics/metrics_test.go`.

**Handlers.**
- `internal/handlers/bots.go` (created): `BotsHandler`, six handler funcs, strict query parse, 404 rules.
- `internal/handlers/decisions.go` (modified): three new `Decision` fields.
- Tests: `internal/handlers/bots_test.go` (created), `decisions_test.go`.

**Repositories (`internal/repository/postgres/`).**
- `bot.go` (created): owner-scoped bot reads, `LockBot` (`FOR NO KEY UPDATE`), `SetStatus`, `CurrentVersion`, `LastRun`, `CreateZoneBot`.
- `account.go` (modified): `Bot` gains `Template`, `CurrentVersion`, `StatusSince`; the manual insert writes them.
- `order.go` (modified): C4' `CloseStampSQL`, `ExitReasonUser`, `StampCloseReason`.
- `decision.go` (modified): selects `bot_version`, `run_id`, `policy_result`.
- Tests: `closestamp_test.go` (created), `order_test.go`, `trading_test.go`.

**Trading service (`internal/services/trading/`).**
- `account.go` (modified): `EnsureBots`; `EnsureAccount` as a wrapper.
- `bots.go` (created): list, detail, decisions, portfolio, pause, resume.
- `decisions.go`, `portfolio.go` (modified): bot-scoped reuse.
- `trade.go` (modified): `opened_by` from the bot's name.
- `store.go` (modified).
- Tests: `bots_test.go` (created), `service_test.go`, `trade_test.go`, `place_test.go`, `portfolio_test.go`.

**Pure package (`internal/trading/`).**
- `botversion.go` (created): canonical JSON, hash, label, v1 config.
- `testdata/bot-version.v1.json` (created): C10.
- Tests: `botversion_test.go` (created).

**Integration tests (`test/integration/`).** `bots_test.go` (created); `decisions_test.go`, `events_test.go`, `main_test.go`, `orders_test.go`, `ready_test.go`, `redaction_test.go`, `trade_test.go`, `trading_fixtures_test.go` (modified).

Unchanged by design (verified per step): `place.go`, `manualfill.go`, `cancel.go`, `estimate.go`, `internal/trading/rules.go`, `arith.go`, `go.mod`/`go.sum`, and the Redis, `/ws` and realtime code.

### tidewatch-bot (PR #5)

**Repo root.**
- `README.md` (new "Bots" section, known gaps R2/R3/R12, schema dependency F), `CLAUDE.md`.
- `Dockerfile` (ships `bots` dist), `.env.example` (comment), `tsconfig.json` (reference), `pnpm-lock.yaml`.
- `scripts/sql-integration.sh` (runs the bots int specs, asserts F, counts leftovers).
- All modified.

**`packages/shared`.** `src/config.ts` (`bots` appended to `COLLECTOR_NAMES` and the reason text), `src/config.spec.ts` (modified).

**`packages/worker`.**
- `src/serve.ts` (wires the `bots` runner), `src/run.ts` (pool comment), `package.json` (depends on `bots`), `tsconfig.lib.json` (modified).
- Tests: `src/serve.spec.ts`, with collector counts raised by one on purpose.

**`packages/sim` (C4' and exports for the intake; no behaviour change otherwise).**
- `src/pg-store.ts`: `CLOSE_STAMP` with `$4`, the exit-reason read, `readMarkContext`.
- `src/store.ts`: `closeStampReason`, `FillOrderResult.exitReason`.
- `src/fill-pass.ts`: `valueAccount`; `sim_order_filled` gains `exit_reason`.
- `src/fill-rules.ts`: `marketPrice` factored out.
- `src/money.ts`: `divFloor`.
- `src/testing/memory-store.ts`: bot decision columns, `recordDecision`, `markContext`.
- `src/testing/index.ts`, `src/index.ts`.
- Tests: `pg-store.int.spec.ts`, `fill-pass.spec.ts`, `fill-rules.spec.ts`, `money.spec.ts`, `testing/memory-store.spec.ts` (`close stamp reason`).
- All modified.

**`packages/bots` (new Nx library `@tidewatch-bot/bots`, `type:shared`; depends on `shared`, `market-data`, `sim`, `indicators`, `prom-client`). All created.**
- Config: `package.json`, `tsconfig.json`, `tsconfig.lib.json`, `tsconfig.spec.json`, `vitest.config.mts`, `vitest.int.config.mts`.
- Fixtures:
  - `fixtures/bot-version.v1.json` (C10 copy);
  - `fixtures/bots-intake.v1.json` (30 hand-derived intake scenarios; sha `b92964f1…87d0`);
  - `fixtures/README.md`.
- Source (`src/`):
  - `index.ts`;
  - `version.ts` (v1 config, canonical JSON, hash, label, `validateVersion`);
  - `client-order-id.ts` (UUIDv5);
  - `strip.ts` (strip timeframe and bound, zone run, `market_state`);
  - `universe.ts`, `rules.ts` (`fireRule`, `checkSessionAndPrice`), `sizing.ts`, `intake.ts` (`evaluateIntake`, `limitReasons`);
  - `store.ts` (store interface), `place.ts` (`placeAction`), `pass.ts` (`runPass`), `engine.ts` (loop, interrupted sweep), `metrics.ts`, `pg-store.ts` (PostgreSQL store on F), `runner.ts`;
  - `testing/index.ts`, `testing/memory-store.ts`.
- Tests:
  - `version.spec.ts`, `client-order-id.spec.ts`, `strip.spec.ts`, `universe.spec.ts`, `rules.spec.ts`, `sizing.spec.ts`, `intake.spec.ts`;
  - `place.spec.ts`, `pass.spec.ts`, `engine.spec.ts`, `metrics.spec.ts`, `runner.spec.ts`;
  - `intake-fixture.spec.ts`, `bot-version-fixture.spec.ts`;
  - `pg-store.int.spec.ts`, `pass.int.spec.ts`;
  - `testing/memory-store.spec.ts`.

The bot plan listed 71 paths and the reviewed diff had 70 files. `packages/worker/tsconfig.spec.json` has no `bots` reference at the merged head and is presumed to be the one left unchanged.

### tidewatch-web (PR #7)

**Docs.** `README.md`, `CLAUDE.md` (modified): the Bots screen, the one `/trade` read, the record inputs, follow-ups.

**Routing.**
- `src/app/pages/workspace/workspace.routes.ts` (modified): `/bots` lazily loads `feat-bots/bots`.
- Tests: `src/app/app.routes.spec.ts`, `src/app/pages/workspace/feat-screen-placeholder/screen-placeholder.spec.ts`, `src/app/shell/shell.spec.ts` (moved off the Bots placeholder).

**Data (`src/app/pages/workspace/data/`).**
- `bots.model.ts`, `bots-api.service.ts` (created).
- `trade.model.ts` (modified).
- Tests: `bots.model.spec.ts`, `bots-api.service.spec.ts` (created), `trade.model.spec.ts`.

**Utilities.** `src/app/pages/workspace/util/bangkok-time.ts` (modified) and its spec.

**Trade (`feat-trade/`, modified).**
- `decision-record.ts` (inputs), `trade.ts` (binds them), `util/order-view.ts` (bot branch).
- Tests: `decision-record.spec.ts`, `util/order-view.spec.ts`. Every existing test title is kept.

**Bots (`feat-bots/`, created).**
- `bots.ts`, `bots-list.ts`, `bot-detail.ts`, `data/bots.service.ts`, `util/bot-view.ts`.
- Tests: `bots.spec.ts`, `bots-list.spec.ts`, `bot-detail.spec.ts`, `data/bots.service.spec.ts`, `util/bot-view.spec.ts`.

**Styles (`src/styles/`).** `styles.css` (import), `components/metric-card.css`, `components/portfolio.css`, `components/table.css` (modified); `components/bots.css` (created).

**End-to-end (`e2e/`).**
- `playwright.config.mts` (`bots`, `bots-live` in `AUTHED_SPECS`).
- `src/support/screens.ts` (`BOTS` becomes a real screen).
- `src/support/bots.ts` (created; §6.1 builders, the stateful `BotsApiMock`).
- `src/bots.spec.ts` (created; mocked, fail-closed).
- `src/bots-live.spec.ts` (created; real service; Pause/Resume gated by `E2E_BOTS_PAUSE=1`).
- `src/shell.spec.ts`, `src/journey.spec.ts`, `src/viewport.spec.ts` (modified).
- `src/paper-orders.spec.ts` (modified, ORCH-13/13a; test-only).

**Not changed:**
- `tidewatch-specs` and `documents/` are inputs only.
- `tidewatch-apis` is not a Git repo; FR-ZB-DOC-002 is deferred.
- Compose and workspace-root files.
- `DESIGN.md`: FR-ZB-WEB-007 runs on branch `codex/forge-zbot-d1343f8c-design` from `db96bc9`.

## Test plan

### Commands (all local; there is no CI, D4)

- **Migrations:** `make migrate-validate`; `make check-disposable-db` (PASS, 1016/0, including the F transcript and 14 rolled-back probes).
- **Service:** `make ci` (vet, test-race, build; Docker-free); `make test-integration TIDEWATCH_MIGRATIONS_DIR=<migrations checkout>` (no `--- SKIP` allowed; verification greps `--- PASS: <Name> (`).
- **Bot:**
  - `pnpm install --frozen-lockfile && pnpm nx run-many -t lint test typecheck build`.
  - `TIDEWATCH_MIGRATIONS_DIR=<checkout> bash scripts/sql-integration.sh`. Last run: market-data 16, worker 2, sim 17, bots 9, all passing on F. The bots int specs leave `zztest-bots-*` users and paused `ZZTEST bots *` bots behind (R17).
- **Web:** `pnpm nx run-many -t lint test build` (2,287 unit tests at fix-r1); mocked Chromium `e2e/src/bots.spec.ts` (142/142); the Playwright suite on a fresh isolated preview DB.

### Named acceptance tests (do not rename)

- **Service:** `TestBots_EnsureCreatesZoneBot`, `TestBots_ExistingMeGetsZoneBot`, `TestBots_ConcurrentFirstAccess`, `TestBots_List_MatchesSQL` (against `test/sql/portfolio_kpis.sql`, with SQL-planted `bot_runs`), `TestBots_Detail`, `TestBots_Decisions`, `TestBots_Portfolio`, `TestBots_ForeignBotIs404` (23 foreign, absent, upper-case and malformed reads), `TestBots_PauseResume`, `TestEvents_BotStatusChanged`, `TestService_PauseResume_Transitions`, `TestService_BotDecisions_BadCursorBeforeOwnership`, `TestCloseStampSQL_IsC4Prime`, `TestOrderRepo_StampClose_Reason`, `TestManualFill_CloseStampUser`, `TestBotVersion_FixtureHash`, `TestCSRF_BotMutations`, `TestRouter_ForcedChangeGatesNewRoutes` (32), `TestRouter_NoDecisionMutation`, `TestCodes_Contract`, `TestLogs_NoSecrets` (with a pass over all six `/bots` routes), `TestContract_RequiredSchemaVersion`, `TestService_Trade_OpenedByBotName`.
- **Bot (exact Vitest titles):**
  - `packages/bots/src/pass.spec.ts`: `enters once on a buy transition`, `baseline at status_since`, `exits on sell`, `defers while closed`, `skips with reasons`, `records runs`, `version guard`, `version guard retries the failed run until the store has written it`, `observing`.
  - `pass.int.spec.ts`: `replay after crash`.
  - `packages/sim/src/testing/memory-store.spec.ts`: `close stamp reason`.
  - `intake-fixture.spec.ts` (the 30 `bots-intake.v1.json` scenarios) and `bot-version-fixture.spec.ts` (C10 hash and 1,437-byte length).
- **Web:**
  - Vitest specs per component, parser and util.
  - `e2e/src/bots.spec.ts`: 10 states × 2 themes × 390/600/1080/1440 = 80 captures, measured contrast, axe, plus `reaches every Bots control by keyboard`, `reads /trade once per screen open and never polls it`, and `nothing in the Bots head, tags or figures is clipped at 390 and 600`.
  - `e2e/src/bots-live.spec.ts`: read-only; the Pause/Resume test is gated.

### Acceptance status (PRD §9)

| ID | Status | Evidence / note |
|---|---|---|
| FR-ZB-MIG-001…003 | Passed | Harness PASS 1016/0: F's objects and backfill proof; 14 probes refused and rolled back; F's objects absent after down, down-to slice 0 and down-to 0. |
| FR-ZB-SVC-001…006 | Passed | Named integration and unit tests above. v1 created as `v1·687c`; gated count 32; CSRF on both POSTs; no secret in logs over the six routes. |
| FR-ZB-BOT-001…007, 009, 010 | Passed | Memory-store specs, the 30 fixture scenarios, and SQL integration on F. Replay goes `ON CONFLICT` → `already_placed`. Runs `running` → `succeeded`/`noop`, the interrupted sweep, the version guard per ORCH-6, observing. Runner in `COLLECTOR_NAMES`, metrics with closed labels, README. |
| FR-ZB-BOT-008 | Passed (both repos) | Bot: unit, memory end-to-end (`exit_reason = 'zone'`) and SQL (zone and user). Service: `TestManualFill_CloseStampUser`, `TestOrderRepo_StampClose_Reason`, `TestCloseStampSQL_IsC4Prime`. **No live bot exit has happened yet.** |
| FR-ZB-WEB-001…006 | Passed | Mocked spec 142/142, both locally and **against the preview build**: 80 captures, no horizontal scroll 80/80, contrast 600 measurements with a minimum of 4.79:1, axe 0 violations in 20/20 runs, clipping 0. Design review r2 approved on rendered evidence (B1 resolved; Overview A7 and Trade WEB-004 at 0-pixel diffs). Trade specs unchanged and green (A8). |
| FR-ZB-WEB-007 | In progress | `DESIGN.md` refresh (selected-row pattern, Bots screen) in a separate web docs PR. |
| FR-ZB-E2E-001 | **Unverified** | Prerequisites were ready on the preview: universe of 6 with strip rows, Alpaca US prices live (A2), PTT.BK closed until 2026-10-12 03:00Z. Slack Water's baseline was 15:00:56Z, so the earliest enterable Buy run started on the 16:00Z bar (entry about 17:00Z). By the merge at 17:43Z there were 4 `noop` runs, 0 decisions and a healthy bot. The first-entry wait (60 s poll, 10 h cap) kept running after merge. |
| FR-ZB-E2E-002 | **Unverified** | Depends on the first entry (restart/replay and a Sell closing with `exit_reason = 'zone'`). |
| FR-ZB-E2E-003 | **Partly verified** | The read-only screen equals SQL and `portfolio_kpis.sql` field by field for both bots (Slack Water `v1·687c`, ฿1,000,000, 0.00%, 0.0%, 0 decisions, last check "6 instruments · no action"). This was a fresh account with no positions or decisions, so the positions/decisions comparison covered empty tables only. Live Pause/Resume was not run (OWNER-1, then OWNER-2). |
| FR-ZB-E2E-004 | Not started | The first week on the owner's stack: never a seventh position, never over the limits, never Gold 96.5 or GO; Trade and Overview for `me` unchanged. |
| FR-ZB-DOC-001 | Passed | Per-project README/CLAUDE.md diffs with fact-check files (migrations MIG2, service S6 ~28 statements, bot S10 161 path:line refs, web S9 135 rows). |
| FR-ZB-DOC-002 | Deferred | `tidewatch-apis` is not a Git repository. |

**Other preview results** (Phase A, 2026-10-09T15:16Z; web `f0619a2`, service `d87d098`, bot `287818a`, migrations `bbf7a87`; fresh isolated DB at F):
- Full Playwright suite: 571 passed, 2 failed, 1 skipped (the gated pause test).
  - Failure 1, `bots-live.spec.ts` test defects: D1, a `/\/bots$/` match that also caught the SPA page navigation; D2, padded button text. Both were fixed in web fix-r2, and the spec then passed read-only on the preview.
  - Failure 2, slice-2 `paper-orders.spec.ts`: fixed by ORCH-13/13a and passed on the preview. SQL fill latency was 64.6 s and 113.5 s.
  - The whole suite was not re-run end to end after fix-r2.
- Secret scan of the HTML report, attachments and logs (bootstrap password, journey password, session cookie, in plain, URL, JSON and base64 encodings): 0 hits.
- Runner: Me and Slack Water were created at 15:00:56Z. Passes ran every 30 s, and runs were written only when a strip row advanced (noop, `new_bars` 4 then 2), with 0 failed or interrupted. `bots_running 1`; `bot_status_changes_total` {paused 0, running 0}.
- Observations:
  - `bots_passes_total` counts no pass that had no zone bot.
  - Both bots' benchmarks exclude NVDA and AAPL, because US `px:last` was absent at creation (`no_price`, the slice-2 rule).
  - One slice-1 `aggregates_refresh_failed` was retried.

### Assumption outcomes (PRD A1–A8)

- **A1** (an entry within about 2 min of bucket close): unverified, because no entry occurred.
- **A2** (Alpaca keys): US prices were live on the preview.
- **A3** (`QtyDecimals`): covered by the intake fixture. Code review re-derived NVDA 187.54 → 15.91700238 shares → ฿100,107.00 and PTT 34.28 → 2917 shares → ฿100,045.05 by hand.
- **A4** (slice-2 preview): recorded at plan time as 37/42, with E2E-001/002/005 unverified, E2E-004 partial and no open fill defect. A fill problem on the preview would count as a slice-2 carry-over.
- **A5**: the first pass after a start writes one run per bot.
- **A6**: no separate timing evidence was recorded.
- **A7**: 0-pixel diff on Overview.
- **A8**: Trade unchanged.

### Manual reproduction (for the open E2E rows)

1. **E2E-001.** On a preview or owner stack with F applied, open Bots once (this creates both bots), then wait for a strip-timeframe Buy run that starts after Slack Water's `status_since` on an open-venue universe instrument. Capture the `indicators` row, the `bot_runs` row, the decision (`actor = bot`, `loop = manager`, `run_id`, `bot_version = 687c7ad3…`, `market_state`, `policy_result`), the order and the fill with timestamps. A read-only capture script exists at `/Users/maichinu/tidewatch/.forge/features/zone-transition-bot/evidence/preview/e2e-001-capture.sh`.
2. **E2E-002.** Restart the bot container mid-pass and let it replay. Expect exactly one order per (instrument, zone run). When a Sell transition occurs, expect `exit_reason = 'zone'` on the entry decision.
3. **E2E-003 pause part.** Only after 1 and 2: run `bots-live.spec.ts` with `E2E_BOTS_PAUSE=1` on Chromium against a fresh database. Confirm by SQL that Slack Water ends `running`, and that a Buy run that began during the pause is not entered after resume.

## Open questions

**Unverified behaviour (stated, not failed):**
- The bot has not yet placed, filled or closed a real order on any stack (E2E-001/002). The first-week check (E2E-004) has not started.
- **ORCH-6 / R2** is an owner-visible revision of PRD §8.4. It stands unless the owner vetoes it.

**Follow-ups recorded in state.json:**
- **Service:**
  - `GET /bots` computes a full `1m` portfolio per bot on every 10 s poll. This is fine at 2 bots; revisit for slice 6.
  - The detail reads `CurrentVersion` twice (`bots.go:175`, `:449`).
  - If `SummarizeBot` fails after a committed pause/resume, the response is 500 and a retry gets 409. The audit trail stays consistent.
  - Pin a non-ASCII canonical-JSON case (U+2028/2029 escaping) in both repos before a C10 v2.
  - The backfill proof becomes a note after a future migration G.
  - The decisions cursor checksum is unkeyed (slice 2; no impact, because ownership is checked by the owner-scoped query).
  - README:555 says "any other cursor is 400". That is exact only for the caller's own bots; a binding mismatch on a foreign bot is 404.
- **Bot:**
  - The pre-existing `runner_failed` log (`serve.ts:373-376`) prints the message and stack if `engine.run` rejects. Keep intake errors off that path.
  - Failure isolation is per bot, not per instrument (`pass.ts`).
  - The engine stops only between passes, so a slow-DB pass may outlast `serve`'s 10 s shutdown guard.
  - On the unsupported-version path, if `startRun` succeeds and `finishRun` throws, an orphan `running` run remains until the next engine start sweeps it.
- **Web:**
  - A 2xx non-JSON Pause/Resume body (with `withFetch`, an `HttpErrorResponse` with status 200) shows "Couldn't change" without reloading.
  - Tailwind curator: a duplicate busy rule, and a redundant `display:block` on `.bot-detail app-decision-record`.
  - CLAUDE.md follow-ups:
    - graduate `positions-table.ts`, `decision-record.ts` and `util/order-view.ts` to `pages/workspace/ui-*`;
    - on that move, unscope the twice-scoped `.muted`/`.when` and centred-error rules;
    - promote the busy button to `button.css`;
    - graduate `number-format.ts` and `DISPLAY_TIME_ZONE`.
  - Design notes:
    - The list's name cell has no whitespace between `.ver` and `.second`, so its accessible text reads "v1·687cCDC zone changes…" (the mockup does the same).
    - The 2px heading margin applies to the Positions and Decision record headings inside `.bot-detail` too.
    - In full-page captures the sidebar background ends at viewport height (pre-existing shell behaviour).
- **Slice 2 carry-overs:**
  - Under the next-bar rule, FR-SIM-E2E-004's "fills within 2 minutes" can be slightly exceeded in the worst case (about 110 s observed, plus UI refresh).
  - Add a log- or SQL-based fill-latency guard to the preview harness, because the UI cannot measure it (`filled_at` is the bar open).

**Known gaps (bot README):**
- A Buy run whose start falls outside the 49-row window is never entered (R3).
- A run interrupted less than 5 minutes before a restart stays `running` until a later start (R12).
- R13: a Buy bucket that began before a creation or resume is baseline even if it closed after it.
- `exit_reason = 'zone'` applies only to bot exits. A user closing a `me` position keeps `'user'` even when the zone is Sell, so slice-7 stats should read `policy_result`.

**Drift left in `documents/` (D17):**
- `02-architecture.md` §5.1 still lists three `bot_runs` statuses.
- `features/06-bots.md` still says auto mode arrives in slice 6, without the 2b exception.
- The approved mockup's sparkline and probation tag were not built.

**Preview cleanup pending:**
- The preview keeps running with retained volumes for the first-entry wait.
- On `Me` it holds two pending BTC/THB limit buys (0.0001 @ 1,000, ฿0.10 reserved each) and 0.0002 BTC from the paper-orders journey.
- The journey's credential file in the web worktree's git-ignored `e2e/.auth` is to be deleted at cleanup.

**Owner action:**
- Apply migration F to the owner's own database before running the merged service. `/ready` stays 503 until then.

## Cross-cutting links

- [[simulation-engine]]: slice 2's `me` bot, the `sim` runner that fills and marks bot orders, and the slice-2 preview carry-overs (A4).
- [[paper-trading]]: one order path, C3–C9. This slice adds C4' (the parameterised close stamp) and C10 (the version fixture), plus a second intake in the bot.
- [[decision-record]]: append-only `decisions`; bot rows now fill `actor = bot`, `loop = manager`, `run_id`, `bot_version` and `policy_result`.
- [[centralized-migrations]]: migration F, the required schema version `20261009122143` and the destructive down.
- [[market-timeseries]]: the `indicators` rows (`cdc_zone`, strip timeframe) the bot reads.
- [[market-data-worker]]: runners, `runner:<name>` locks and `COLLECTOR_NAMES`, where `bots` is the eleventh.
- [[redis-market-contract]]: `px:last` freshness (120 s bound), read by the bot through the recorded price view, not Redis.
- [[instrument-master]]: venues, calendars, `lot_size` and `base_timeframe = '1d'` (PTT.BK), which shape the universe and quantity.
- [[gold-feed-xaut-proxy]]: XAU/USD priced from Binance TH XAUT; in the universe, with `venue_label` still "OANDA demo".
- [[request-protection]]: CSRF and the gated group on the new routes.
- [[auth-model]]: the session user who owns both bots; ownership answers 404, never 403.
- [[design-system-decisions]]: the selected-row and selectable-row-button patterns, `.metric-strip` in `metric-card.css`, and the busy button, pending the `DESIGN.md` refresh.
- [[forge-preview-gateway]]: the isolated preview where E2E verification runs.
- [[realtime-websocket]]: nothing new on `/ws`; Bots polls REST every 10 s.
