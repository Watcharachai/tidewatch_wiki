# Bots, versions and runs

**Summary**: The data model that lets one user own more than one bot. A `bots` row carries a `template`, a lifecycle `status` and `status_since`. `bot_versions` stores each bot's config as data under a content hash, and a version never changes. `bot_runs` holds one row per bot pass that had something new, so a quiet bot can be told apart from a broken one. Migration F added the versions and runs in slice 2b (2026-10-09). The service's six `/bots` routes read this model, and Pause / Resume change a bot's status. Since the bot-activity feature (merged 2026-10-10), migration G adds `bot_runs.outcomes` (the per-instrument verdicts of the evaluation that finished the run), every run payload carries `error`, and three more read-only routes list a bot's runs, return one run with its outcomes, and return its live watch: nine `/bots` routes in all. **Since slice 6 (bots; tidewatch-service #12 and migration J, merged 2026-10-21, not deployed),** the owner creates bots from four templates or clones them, and every change saves a new version in the v2 vocabulary (`"schema": "bot-config.v2"`). Migration J adds `bot_version_events`, `bot_run_requests` and `bots.probation_until`, and new bots and versions start on a 30-day probation (`observing`). The service gained 14 gated routes (create, clone, versions, upgrade, candidates, schedule, universe, *Run now*, attribution, fit-weights, model tiers and the recommendation), an extended `BotSummary`, and the FU-1 caps: per-class bounds, at most 10 active auto bots and *Run now* at most 6 times per bot and loop per hour. How the bot runs v2 configs is on [[bots-engine]]. **Since slice 7 (statistics; tidewatch-service #15, merged and deployed 2026-10-27),** each version has a **window**, `[created_at, next version's created_at or now)`, over which Stats grades it. `bots.champion` and the `promoted`/`demoted` version events have their first writer, `POST /bots/{bot_id}/promote`, which flips the flag only when the promotion check passes; a later version of the champion keeps the flag. `GET /bots/{bot_id}/attribution` gains four additive net keys, `GET /bots/{bot_id}/versions` gains its first web reader, and the gated count is 64. No production champion has been made yet. **Since accounts and roles (tidewatch-service #18, merged and deployed 2026-10-29),** the active-bot cap, the starting capital and the allowed decision tiers come from the owner's **plan** (`founder`: 10 active auto bots, ฿1,000,000, all four tiers). A save, create or clone with a tier the plan excludes is refused `not_entitled`. `GET /model-tiers` marks each tier `entitled`. Disabling a person in the operator console pauses their running and observing auto bots through Pause. **Since the learning loop (slice 8; migration M and tidewatch-service #16, merged and deployed 2026-10-30),** `learn` is a fourth loop on `bot_runs` and `bot_run_requests`, and `POST /bots/{bot_id}/run` accepts it for v2 versions. A v2 config may carry one optional `learning` block (contract C15), and a version is **learned** exactly when it has one. *Save as vN* can save a learning run's draft (`learning_run_id`), and a learned version always starts on probation, on save and on clone. `learned` is the last key of `strategy` and of each version item. The service gained six gated routes (70 in all). `learn` rows are hidden from the existing run reads. **Since signals context (tidewatch-service #17, merged 2026-10-30),** `bot-config.v2` has an optional `schedule.scout.discovery` key with `context {enabled, z_min}` and `calendar {enabled, sessions_ahead}`. Absent means off, and a config without it hashes exactly as before. A second shared fixture, `bot-version.v2-discovery.json`, pins the key's accepted cases and refusals in all three repos.

**Sources**: `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-21-bots.md`; `raw/2026-10-27-statistics.md`; `raw/2026-10-29-accounts-roles.md` (plan limits, `not_entitled`, `entitled` and the disable pause only); `raw/2026-10-30-learning-loop.md` (the `learn` loop, the `learning` block, Save as vN of a draft, forced probation and `learned` only); `raw/2026-10-30-signals-context.md` (the discovery key, its fixture, `by_discovery` and the `source_weights` release note only)

**Last updated**: 2026-10-31

---

## Why this shape (ZB9)

Migration F adds `bot_versions`, `bot_runs` and three `bots` columns. Two alternatives were rejected:
- A `bots.config` column with no runs table. It loses the difference between a quiet bot and a broken one.
- The full slice-6 table set. It was judged premature.

The tables `decisions`, `orders`, `fills`, `positions` and `ledger` are untouched by F (source: raw/2026-10-09-zone-transition-bot.md §Concept, Chosen design ZB9; §Database).

## Bots

- **Two bots per user since slice 2b.** The manual `me` bot (slice 2, see [[paper-trading]]) and **Slack Water**, the zone-transition bot (see [[zone-transition-bot]]).
- **New `bots` columns.**
  - `template`: `manual` or `zone_transitions`. The constraint `bots_kind_template_check` ties it to `kind`: `kind = 'manual'` exactly when `template = 'manual'`.
  - `current_version`: a foreign key to `bot_versions`. It is NULL for the manual bot.
  - `status_since`: when the current status began. F back-filled it from `created_at`.
- **One zone bot per user** is enforced by the service under its advisory lock. No unique index enforces it, because slice 6 will create more bots per template. Since slice 6, `template` also allows `news_drift`, `filings_only` and `blank` (J re-creates `bots_template_check`), and *Create bot* and *Clone* add auto bots under the same `MeBotLockKey` lock, at most 10 active per account (see below).

(source: raw/2026-10-09-zone-transition-bot.md §Database)

### Lazy creation (`EnsureBots`, PRD §4.1)

- Every `/bots` route runs `EnsureBots` first. `EnsureAccount` remains as "`EnsureBots`, then return the manual bot", so every slice-2 caller creates both bots without edits to the PRD-stable `place.go` (SB2 / R5). The cancel route creates them too (R6).
- Fast path: one lock-free read. Otherwise, under the existing `pg_advisory_xact_lock(MeBotLockKey(user))`, one transaction creates whichever of `Me` and Slack Water is missing.
- Slack Water is created with:
  - name "Slack Water", strategy label "Zone transitions", `kind = auto`, `template = zone_transitions`, `mode = paper_auto`, status `running`, `status_since` = `created_at` = the service clock, limits 0.25 / 1.00;
  - its own paper account with ฿1,000,000.00 (since accounts and roles, the plan's `starting_capital_thb`, ฿1,000,000 on `founder`), the slice-2 benchmark snapshot and the initial `fill` ledger mark;
  - the C10 v1 `bot_versions` row (`created_by_user_id` NULL), then `current_version`.
- Ten concurrent first requests create exactly one of each (`TestBots_ConcurrentFirstAccess`).

(source: raw/2026-10-09-zone-transition-bot.md §API, Lazy creation; §Concept, Plan resolutions, Service)

## Status lifecycle

| Status | Meaning in 2b |
|---|---|
| `running` | The `bots` runner evaluates the bot and may place orders. The status at creation (ZB7). |
| `paused` | Not evaluated. Its pending orders still fill and its positions stay open. |
| `observing` | The runtime honours it: it writes skip-shaped decisions with `reasons = ["observing"]` and places no orders. **Nothing sets it in 2b.** |

- **Pause** moves `running` or `observing` to `paused`. **Resume** moves `paused` to `running`. Resume on an `observing` bot is a 409 (ORCH-8). Since slice 6, **Resume** goes to `observing` while `probation_until > now()`, else to `running`, and refuses an 11th active auto bot with `409 bot_limit_reached` (see "Status and probation" below).
- Each runs one transaction: lock the `bots` row `FOR NO KEY UPDATE`, refuse the manual bot, refuse a status the bot already holds, set `status` and `status_since`, and write the audit row. The metric and log come after the commit. The lock never touches the account row and does not conflict with the `FOR KEY SHARE` that the bot's foreign-key checks take (SB5).
- **`status_since` is the strategy's baseline.** A resume moves it, so a Buy zone run that began before the resume is never entered. Bucket-start rule (R13): a bucket that began before a creation or resume is baseline even if it closed after it.
- **Pause race (R20).** The bot runner never locks the `bots` row. It re-reads `status` inside its intake transaction, so at most one order from a pass that began before a pause can land.

(source: raw/2026-10-09-zone-transition-bot.md §API, Pause / Resume; §Concept, Chosen design ZB7, Proposed defaults, ORCH-8 and Plan resolutions)

**Watch rows across Pause and Resume (bot-activity).** A paused bot is not evaluated, so its `bot_watch` rows stay as of the last pass and the Watch reads "Paused since … · last checked …". After a resume, the next pass rewrites every row with `baseline_at` = the new `status_since`. Both were verified on the preview (FR-BA-E2E-004). The watch write's FK checks take `KEY SHARE` only, which does not conflict with Pause's `FOR NO KEY UPDATE` (see [[bot-watch-verdicts]]) (source: raw/2026-10-10-bot-activity.md §Test plan, Acceptance status and Manual reproduction; §Concept, Plan resolutions, Bot R-BA7/R-BA8).

## Versions: config as data

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
```

- **Hash.** The version is the SHA-256 of the canonical JSON config: keys sorted recursively, no whitespace, and every number a decimal string. A raw JSON number in a config is refused. Both sides hash `canonical(config)`, never the stored jsonb text.
- **Label.** `v{seq}·{first 4 hex}`. The real v1 label is **`v1·687c`**. The intent and mockup used `v1·c7e8` only as an illustration.
- **v1 config.** It encodes the zone-transition rules: the strip timeframe (`1h`, `1d` for daily instruments), long only, market orders, 10% of equity per entry, `limits.max_open` as the string `"6"` (ORCH-8), and a universe of the watchlist with no manual venues and no futures. The web derives its strategy sentence from it.
- **Write order (MF3).** `bots_current_version_fkey` is MATCH SIMPLE, so a NULL `current_version` goes unchecked. A writer must insert `bots` with NULL, then `bot_versions`, then `UPDATE bots SET current_version`.
- **A version never changes.** In 2b there was no route that creates, updates or deletes a bot, a version or a decision. The Bots screen says "Paper money · a version never changes". Since slice 6, `POST /bots`, `POST …/clone` and `POST …/versions` create bots and versions; a version is still never updated or deleted, and there is still no decision mutation.

(source: raw/2026-10-09-zone-transition-bot.md §Database; §Concept, Proposed defaults; §Components)

### C10: the shared version fixture

- Byte-identical copies, 1,437 bytes, file sha256 `7f43058aeb71930da9a5ecd0a57fa9caeaddadcb8e0af412032deef733762d24`:
  - service `internal/trading/testdata/bot-version.v1.json`, pinned by `TestBotVersion_FixtureHash`;
  - bot `packages/bots/fixtures/bot-version.v1.json`, pinned by `bot-version-fixture.spec.ts`.
- v1 version `687c7ad37f7e7b531eab74efc79b24117d76360d70e5dd4cffa8f71bc4c47f68`, seq 1, label `v1·687c`.
- Changing the fixture is a contract change in both repos at once, like C3 (see [[paper-trading]]).
- Follow-up: pin a non-ASCII canonical-JSON case (U+2028/2029 escaping) in both repos before a C10 v2.

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Cross-project contracts; §Open questions)

### Version guard (ORCH-6)

The runner evaluates a bot only if its version is exactly v1 **and** `current_version` equals the hash of the canonical config (R9). For an unsupported version, the bot writes **one** `failed` run (`error = version_unsupported`, zero counts) per bot and version per runner run, then no new run until the version changes or the runner restarts.

- Why: PRD §8.4 would leave a failed run on every pass, about 2,880 failed runs per bot per day.
- Visible cost: the Bots screen's *Last check* stays at the first failure.
- A null `current_version` cannot carry a run, because `bot_runs.bot_version` is NOT NULL with a foreign key. It is logged and counted without one.
- The "already reported" memo is set only after the failed run is written, so a store outage retries it (ORCH-12).
- This is an owner-visible revision of PRD §8.4, **accepted pending the owner's veto**. Every other failure class keeps PRD §8.4.

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Owner decisions during the build, ORCH-6)

**Since bot-activity.** The version-unsupported path (including a null `current_version`) is not an evaluation: its failed run carries `outcomes = []`, and it writes no watch row, because an empty write would delete the rows. *Last check* now names the class: "last check failed · version unsupported" (source: raw/2026-10-10-bot-activity.md §API, Bot runtime, Failure paths; §Components, Last check card).

## Runs

```sql
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
```

Index: `bot_runs_bot_started_idx (bot_id, started_at DESC)`.

- **Status drift.** `running` is added to the architecture document's three values (`succeeded`, `noop`, `failed`), so an interrupted pass stays visible. The drift is recorded in PRD §10; `documents/` was not edited (D17).
- **When a run is written (zone bot).** A run (`loop = manager`, `trigger = scheduled`) opens when an instrument has a newer strip row than the runner's last-seen `ts`, or at start. It finishes `succeeded` when a decision was written, else `noop`. `counts` = `{instruments, new_bars, entries, exits, skips, deferred}`. A pass with nothing new and nothing written writes no run.
- **On-demand run (R1).** A deferred entry placed at the next open, or a skip, can land on a pass with no new strip row. Then the run row is created inside the first intake transaction that writes a decision. Every bot decision therefore carries a real `run_id` (see [[decision-record]]), and a rolled-back or decision-free intake leaves no run.
- **Failures.** One bot's failure finishes its run `failed` with the error class, never a message.
- **Interrupted sweep.** Before the first pass, `running` runs older than 5 minutes (`INTERRUPTED_RUN_AGE_MS`) are finished `failed`, `error = interrupted`, with six zero counts. Known gap (R12): a run interrupted less than 5 minutes before a restart stays `running` until a later start.

(source: raw/2026-10-09-zone-transition-bot.md §Database; §API, Bot runtime; §Concept, Plan resolutions, Bot; §Open questions)

### Outcomes (migration G, bot-activity)

Migration G adds one column: `ALTER TABLE bot_runs ADD COLUMN outcomes jsonb NOT NULL DEFAULT '[]'` (see [[centralized-migrations]]).

- **What it holds.** One WatchEntry per universe instrument, as the evaluation that finished the run saw it: the verdict, the rule, the reasons, the zone facts and the `decision_id` / `order_id` pointers. The shape is pinned by contract C11 (see [[bot-watch-verdicts]]).
- **When it is written.** `finishRun` stores it with the run's status and counts (`RunFinish.outcomes` is optional and means `[]` when absent; the pass always passes it, R-BA2). A thrown evaluation error finishes the run `failed` with the class and the entries gathered so far.
- **When it stays `[]`.** For rows from before G, for a `running` run, for the version-unsupported run and for the R12 interrupted sweep.
- **When a run is written did not change.** The bot still writes a run only for a new strip row, at start, or on demand inside a decision-writing intake. A quiet pass still writes no run, but it now writes the `bot_watch` heartbeat (see [[bot-watch-verdicts]]).
- **Retention (BA4).** Everything is kept, with no retention job: about 1 KB per run, roughly 15 MB per bot per year, to be revisited at slice 6. Run rows must stay anyway, because decisions reference them. On the preview the stored outcomes were at most 637 B.
- **No new shape on existing bot types (R-BA3).** `BotRunRow`, `PassSummary` and similar shapes gained no field, because specs assert `toEqual` on them. Entries are observed through new memory-store accessors (`runOutcomes`, `watchRows`) and SQL.

(source: raw/2026-10-10-bot-activity.md §Database; §Concept, Chosen design BA4, Proposed defaults and Plan resolutions, Bot; §API, Bot runtime)

## The `/bots` routes (tidewatch-service)

All six routes mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles; see [[accounts-and-roles]]). The engine-wide CSRF check covers the two POSTs (see [[request-protection]]). The gated-route count test now counts **32** (29 production routes plus 3 probes; it was 26).

| Method and path | Request | 2xx response | Errors |
|---|---|---|---|
| `GET /bots` | — | `{generated_at, items: [BotSummary]}`: the manual bot first, then by `created_at`, then `bot_id` | — |
| `GET /bots/{bot_id}` | — | `{generated_at, bot, version \| null, account, positions, open_orders}`, with the `GET /trade` shapes for that bot | 404 |
| `GET /bots/{bot_id}/decisions` | `limit` 1–200 (default 50), opaque `cursor` bound to the bot | `{items: [Decision], next_cursor}` | 400, 404 |
| `GET /bots/{bot_id}/portfolio` | `period` `1w`, `1m` or `3m` (default `1m`) | the `GET /portfolio` body for that bot | 400, 404 |
| `POST /bots/{bot_id}/pause` | no body, no query | 200 bare `BotSummary` | 400 `manual_bot`, 404, 409 `bot_status_conflict` |
| `POST /bots/{bot_id}/resume` | no body, no query | 200 bare `BotSummary` | 400 `manual_bot`, 404, 409 `bot_status_conflict` |

- **`BotSummary`** carries identity (`bot_id`, `name`, `strategy_label`, `template`, `kind`, `mode`), `status` and `status_since`, the version `{seq, hash, label}` or null, and the figures `equity`, `return_30d`, `max_drawdown_pct`, `decisions_30d` and `last_run` (null for `Me`).
  - The figures are the bot's `1m` portfolio at one instant, so `GET /bots` and `GET /bots/{id}/portfolio?period=1m` agree.
  - The "30-day" maximum drawdown is the whole-ledger figure, so the web labels it "since start" (R7).
  - The list and the detail read in one `REPEATABLE READ READ ONLY` snapshot.
- **Check order.** CSRF (POSTs), the gates, a strict query parse (400 `invalid_request`), a malformed decisions cursor (400), then ownership. A `bot_id` that is not a UUID, is absent, or belongs to another user gets **one indistinguishable `404 not_found`**, never 403. Every repository query carries `owner_user_id` (see [[auth-model]]). A well-formed cursor bound to another bot is 400 on the caller's own bot and 404 on a foreign one.
- **409 messages.** "That bot is already paused." / "That bot is already running." / "That bot isn't paused."
- **Error codes.** `bot_status_conflict` (409) is appended to `AllCodes()`. `400 invalid_request` gains `details.reason = manual_bot`.
- **Audit events.** `bot_status_changed {bot_id, from, to}` with the session user as actor. The bot runner writes `order_placed` and `decision_skipped` with a null actor.
- **Metric.** `bot_status_changes_total{to}` (`paused`, `running`; exported at 0).
- **Cost note.** `GET /bots` computes a full `1m` portfolio per bot on every 10 s web poll. That is fine at 2 bots; revisit for slice 6. Slice 6 measured it: with 5 bots, 27.3 ms in integration (A3) and p50 17.7 ms / p95 21.1 ms on the preview (source: raw/2026-10-21-bots.md §API, `BotSummary` additions).

(source: raw/2026-10-09-zone-transition-bot.md §API; §Open questions)

### Three read-only routes added by bot-activity

The service docs now count the `/bots` routes as "six in 2b, three in bot-activity" (ORCH-12). The three new routes are `GET`s on the same gated group, mounted by `mountBots`. They need no CSRF and read no body. Each runs `EnsureBots` first. The service never computes a verdict and never writes anything on these routes.

| Method and path | Request | 2xx response | Errors |
|---|---|---|---|
| `GET /bots/{bot_id}/watch` | no query parameter | `{generated_at, checked_at, items: [WatchItem]}` (see [[bot-watch-verdicts]]) | 400 (any parameter), 404 |
| `GET /bots/{bot_id}/runs` | `limit` 1–100 (default 20), opaque `cursor` | `{items: [BotRun], next_cursor}`, newest first by `started_at DESC, run_id DESC`, without `outcomes` | 400, 404 |
| `GET /bots/{bot_id}/runs/{run_id}` | no query parameter | `BotRun & {outcomes: [WatchEntry]}`, outcomes exactly as stored | 400 (any parameter), 404 |
| `GET /bots`, `GET /bots/{bot_id}`, `POST …/pause`, `POST …/resume` | as in 2b | `last_run` gains `error` | as in 2b |

```
BotRun = { run_id, loop, trigger, started_at, finished_at | null, status, counts, error: string | null }
```

- **`error`** is `bot_runs.error` as stored: a class name such as `DatabaseError`, or `interrupted`, or `version_unsupported`. It is always present: on `last_run` (list, detail, pause and resume answers), on every runs item and on the detail. One run type and one renderer (`toBotRunJSON`) serve all three (SA1).
- **Run detail.** It returns `outcomes::text`, so each entry's keys arrive in jsonb's normalised order, not the contract's field order; consumers parse and compare values (ORCH-7). A run that is not this bot's answers `404 not_found` "That check doesn't exist." (the screen calls a run a check, R9).
- **Manual bot.** Runs answer `{items: [], next_cursor: null}`.

**Runs cursor (SA3 / R6).** Base64url without padding of `{"v":1,"t":<started_at µs>,"i":"<run_id>","h":"<32 hex>"}`. `h` is the first 16 bytes of SHA-256 over `version (u64 BE) ‖ 0x52 ‖ bot_id ‖ started_at µs ‖ run_id`.
- The decisions cursor's wire is reused, with a kind byte `0x52` ('R') in the runs checksum input only (49 bytes against the decisions' 48). The decisions bytes are untouched, so no issued decisions cursor breaks. A golden test (`TestDecisionsCursor_ChecksumGolden`, checksum `f49e775ce4fa3e51f891f12ad89f2c5b`) was written and run against the unmodified functions before `cursor.go` was edited.
- A decisions cursor is refused on `/runs`, and a runs cursor is refused on `GET /decisions` and `GET /bots/{id}/decisions`. A runs cursor for one bot is refused for another.
- The checksum is unkeyed: it is an integrity check, not an anti-forgery control. Authorization never depends on it, because ownership is resolved first and every row is re-scoped by owner.
- **ORCH-12.** A forged cursor with `t` before PostgreSQL's minimum timestamp reached the query and returned 500. `parseDecisionsCursor`, which the runs cursor shares, now rejects `t < 0` as 400. Checksum bytes and every issued cursor are unchanged.

**Check order on the new routes.**
1. The gate chain, ready gate and no-store.
2. The strict query parse: `runs` accepts only `limit` and `cursor`; the other two accept none. Unknown, repeated or bad parameters → `400 invalid_request {field, reason}`.
3. A `bot_id` (or `run_id`) that is not a UUID → 404.
4. `runs` only: cursor syntax → `400 {field: cursor, reason: invalid}`, before ownership (including `t < 0` since ORCH-12).
5. `EnsureBots`, then ownership. An absent or foreign bot → `404 not_found` "That bot doesn't exist.", never 403 (see [[auth-model]]).
6. `runs`: the cursor's binding to this bot and kind → 400. Detail: a run that is not this bot's → 404 "That check doesn't exist.".

No message distinguishes a foreign bot or run from an absent one.

**Route inventory.** `TestRouter_ForcedChangeGatesNewRoutes` now counts **35** gated routes (32 production + 3 test probes; it was 32). `TestRouter_NoDecisionMutation` admits eight reviewed `:bot_id` routes, still with no `:decision_id` route and no mutation under `/bots` except Pause and Resume (see [[decision-record]]). There is no new error code, reason, audit event, metric, log event or environment variable; the routes are counted by the existing request metrics.

**Compatibility.** A web build against a service without these routes gets 404 and shows the sections' error state while the rest of the bot detail renders. A service at G against a database without G answers 503 on `/ready`.

(source: raw/2026-10-10-bot-activity.md §API, Service routes; §Concept, Cross-project contracts, ORCH-12 and Plan resolutions, Service SA1, SA3/R6, R9)

## Slice 6: v2 configs, create, clone, save as vN (2026-10-21)

Slice 6 (see [[bots]]) merged on 2026-10-21 as tidewatch-migrations #10 (`cd378a3`) and tidewatch-service #12 (`9f1f324`). It is not deployed: the owner applies J first (source: raw/2026-10-21-bots.md §Concept, Stage, Merged and Deployed).

### The v2 vocabulary and dispatch (S1, C12)

- **Dispatch.** A config whose canonical form equals the C10 v1 canonical runs the 2b pass. One with `"schema": "bot-config.v2"` runs the general engine (see [[bots-engine]]). Anything else is `version_unsupported`, handled as the 2b version guard above.
- **Contents.** Sources and their weights (`source_weights`), the decision tier (`none`, `jev`, `small_llm`, `large_llm`), policy (entry condition, sizing, `max_open`, hold, exit on zone, `stop_atr`, horizons, per-class TTL, CDC and Elliott overlays, `daily_loss_pct`), the universe per class (lists, `include`, `exclude`, `allocation`, `limits.max_symbols` and `limits.max_candidates`), and the schedule (scout `times` / `signal_driven` / `off`, `min_impact`, the manager timeframe `15m`, `1h`, `1d` or `strip`, `on_events`). `4h` is reserved and refused (`timeframe_unavailable`, D6). `fx` is never in a universe.
- **C12.** The pinned `bot-version.v2.json` fixture is byte-identical in the service, the bot and the web (`44161eb0…`, PV5). The service pins it with `TestBotVersion_V2FixtureHash`; the web's Vitest checks its SHA-256, its closed sets and a read/write round trip to the same canonical bytes and hash.
- **Templates as pinned data.** `internal/trading/templates/{news_drift,filings_only,zone_transitions,blank}.json`, pinned by `TestTemplates_Pinned`. The templates carry 5 candidates and 4 symbols per class. `news_drift` v1 is `v1·ef8d`.
- **Hash and label.** Unchanged from C10: SHA-256 of the canonical JSON, label `v{seq}·{hash[0:4]}`. A set-like array out of canonical order (`source_weights`, `include`, `exclude`, `horizons`, `schedule.scout.times`) is **refused, never reordered**, because array order is part of the hash.

(source: raw/2026-10-21-bots.md §Concept, Spec decisions S1; §API, Behaviour worth knowing; §Components, Data layer; §Files touched, tidewatch-service S1; §Test plan, Preview runs PV5)

### New tables (migration J)

- **`bot_version_events`**: `event_id` PK, `bot_id`, `version` (`(bot_id, version)` → `bot_versions`), `kind`, `actor_user_id`, `detail jsonb DEFAULT '{}'`, `created_at`; index `(bot_id, created_at DESC)`. `kind IN (created, cloned, version_created, probation_skipped, probation_ended, guard_paused, promoted, demoted)`; `promoted`/`demoted` belong to slice 7. The service writes `created`, `cloned`, `version_created` and `probation_skipped`; the bot writes `probation_ended` and `guard_paused`. Since slice 7, promote writes `promoted` and `demoted` (see "Slice 7" below).
- **`bot_run_requests`**: `request_id` PK, `bot_id`, `loop` (scout, manager, guard), `requested_by_user_id NOT NULL`, `requested_at`, `taken_at`, `run_id`. The partial unique key `bot_run_requests_pending_key (bot_id, loop) WHERE taken_at IS NULL` allows one pending request per bot and loop. The service inserts; the bot writes `taken_at` and `run_id`.
- **`bots.probation_until timestamptz`**, with `bots_probation_check CHECK (probation_until IS NULL OR status = 'observing' OR status = 'paused')`.
- `candidates` is described on [[bots-engine]]. The full J DDL, CHECKs and down are on [[centralized-migrations]].

(source: raw/2026-10-21-bots.md §Database, New tables, Altered objects and Who writes what)

### Status and probation (ORCH-5b, OQ-2)

`observing`, which nothing set in 2b, is now set by probation (D9).

| Action | Result |
|---|---|
| Create or clone, `probation` true (default) | `observing`, `probation_until = now + 30 d` |
| Create or clone, `probation` false | `running`, plus a `probation_skipped` event |
| Save as vN, `probation` true | `running`/`observing` → `observing` with a new 30 days; `paused` stays `paused` with `probation_until` set |
| Save as vN, `probation` false | `observing` → `running` with `probation_until NULL`; any other status keeps it and clears `probation_until` |
| Pause | keeps `probation_until` |
| Resume | `observing` while `probation_until > now`, else `running` |
| The runner's flip (bot) | `observing` → `running` when due, clearing `probation_until` |

The guard's pause and the probation flip are the only bot writes to `bots.status` (S8/S11; see [[bots-engine]]) (source: raw/2026-10-21-bots.md §Database, Status and probation; §Concept, ORCH-5/6).

### Conventions on the new routes

- **Gating.** Every new route mounts on the gated market group (`NoStore → ReadyGate → BodyLimit → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles; see [[accounts-and-roles]])); CSRF is engine-wide on POST and PUT. `POST /bots` and `POST /bots/{bot_id}/versions` use a separate config group with a **64 KiB** body limit; every other route keeps 8 KiB.
- **Scope.** Every query is scoped by `owner_user_id`. A foreign or absent bot is one indistinguishable `404 not_found` (`TestBots_NewRoutes_ScopeAndNotFound`, 11 `:bot_id` routes). Queries and bodies are strict (`400 unknown_field`, never named).
- **Gated count.** `TestRouter_ForcedChangeGatesNewRoutes` counts **59** gated routes: 45 + 14, of which 56 are production and 3 test probes. The build prompt's "+13" was a count slip (ORCH-5d). Since slice 7 it counts **64** (61 production, 3 probes) (source: raw/2026-10-27-statistics.md §API, Conventions).
- **The manual bot.** Clone, versions POST, run and fit-weights answer `400 invalid_request {reason: manual_bot}`; `GET …/versions` answers `{"items": []}` and candidates an empty page; version detail, upgrade, attribution, schedule and universe answer 404.
- **A legacy (v1) bot.** Candidates: an empty page. Upgrade: answers. Attribution weights read `"0"`. Schedule: `scout.kind "off"`, `manager.timeframe "strip"`. Universe: the translation's.

(source: raw/2026-10-21-bots.md §API, Conventions)

### The 14 new routes

| Method and path | Request | 2xx | Refusals |
|---|---|---|---|
| `POST /bots` (64 KiB) | `{name, template: news_drift\|filings_only\|zone_transitions\|blank, starting_capital?, probation?}` | `201 {bot, version: {seq, hash, label, created_at}}` | `400` (body, `name`, `template`, `starting_capital` below `10000.00`), `409 bot_limit_reached`, `409 bot_name_taken` |
| `POST /bots/{bot_id}/clone` | `{name, probation?}` | `201`, as `POST /bots` | `400 manual_bot`, `404`, `409 bot_limit_reached`, `409 bot_name_taken` |
| `GET /bots/{bot_id}/versions` | — | `{items}`, newest first, at most 100, each with its `events` | `404` |
| `GET /bots/{bot_id}/versions/{seq}` | `seq` 1–2147483647 | the item plus `config` and `vocabulary` (`v1\|v2\|unsupported`) | `404` |
| `POST /bots/{bot_id}/versions` (64 KiB) | `{config, probation?}` | `201 {version, bot}` | `400 {field, reason}`, `400 manual_bot`, `404`, `409 version_unchanged` (current **or any earlier** hash) |
| `GET /bots/{bot_id}/upgrade` | — | `{config}`, the §4.2.5 translation | `404` (general or manual bot) |
| `GET /bots/{bot_id}/candidates` | `state=live\|all`, `limit` 1–100, `cursor` | `{items: [Candidate], next_cursor}` | `400 cursor`, `404` |
| `GET /bots/{bot_id}/schedule` | — | `{generated_at, scout, manager, guard, requests}` | `404` |
| `GET /bots/{bot_id}/universe` | — | `{generated_at, by_class, total}` | `404` |
| `POST /bots/{bot_id}/run` | `{loop: scout\|manager\|guard}` | `202 {request_id, requested_at}` | `400 loop`/`manual_bot`, `404`, `409 bot_status_conflict` (paused), `409 run_pending`, `429 run_rate_limited` |
| `GET /bots/{bot_id}/attribution` | — | `{generated_at, version, items}` | `404` |
| `POST /bots/{bot_id}/fit-weights` | `{days}` 30–365, default 90 | `{fitted, n, n_graded, method: "logistic_v1", warnings}`; writes nothing | `400 days`, `400 manual_bot`, `404`, `409 too_few_decisions {n_graded, needed: 30}` |
| `GET /model-tiers` | — | `{generated_at, usd_thb, items}` for `none`, `jev`, `small_llm`, `large_llm`; creates no bot | `400 invalid_request` |
| `GET /recommendation` | — | `{generated_at, follows, candidate, sized, reasons, declined, invalidated}`; creates no bot or account | `400 invalid_request` |

**Changed routes.** `POST /bots/{bot_id}/resume` gains `409 bot_limit_reached`. `PUT /me/settings/recommendations.follow` is a new settings key (see [[user-settings]]). `POST /decisions/skip` gains `candidate_id`, and `POST /orders` and `POST /orders/estimate` gain `decision_ctx.candidate_id` (see [[signal-cited-orders]]). Every `BotSummary` answer carries the extension below (source: raw/2026-10-21-bots.md §API, Routes).

### Behaviour worth knowing

- **Create and clone.** One transaction under the user's `MeBotLockKey`: the active count (`bot_limit_reached`), the name (1–40 runes after trimming, no control character, unique case-insensitively), then the writes: the bot, its own paper account, a benchmark snapshot, the initial mark, v1 from the template's embedded JSON, the `created`/`cloned` and `probation_skipped` events, audit `bot_created`/`bot_cloned` and the log `paper_account_created`. A clone copies the source's **current** config as v1, with its template, label, starting capital and limit columns. The review fold closed a race in which the clone read the bot row and then the version unlocked (`TestService_CloneBot_SaveInterleaved`).
- **Save as vN.** The validator refuses in r1 §2.3 order; the first failure wins, by dotted field and a reason from `missing`, `unknown_field`, `invalid`, `out_of_range`, `duplicate`, `unknown`, `timeframe_unavailable` (`4h` only). One transaction locks the bot row `FOR NO KEY UPDATE`, inserts `seq = max + 1`, moves `current_version`, writes `max_position_pct`/`max_total_exposure` from `limits`, applies the status rules, writes the events and audit `bot_version_created`, and (after the review fold) counts and logs a status change. `ValidateConfigV2`'s table has 175 cases.
- **Schedule.** Service text the web prints as sent: "{when}: {n} signal(s) → {n} candidate(s)", "every {tf} · last {HH:mm} · {action}", "no breach · checked {HH:mm}". A request is `stale` when untaken for at least 10 minutes. `next_wake` is computed in Bangkok (fixed UTC+07:00).
- **Candidates cursor.** Its own kind byte `C` and a state byte go into the checksum, bound to the bot (`TestCandidatesCursor_KindAndState`), beside the runs cursor's `R`.
- **Universe (PRD §4.11).** Lists and watchlist, plus `include`, minus `exclude`; filtered to active instruments with a venue rule, not `fx`, not manual-fill and not futures; a liquidity floor over the newest 20 daily bars; plus held instruments.
- **Attribution (S20).** `n`, `n_graded` and `avg_r_5d` (6 dp) from one statement over every version's bot `buy`/`add` decisions per `signal_snapshot.source_code`; `graded` means `n_graded ≥ 20` (`TestBots_Attribution_MatchesSQL`). Since slice 7 the route is served by the shared attribution module's Bots scope and each item gains `win_rate`, `avg_r_5d_net`, `best` and `worst` after `graded`; every slice-6 key, value, item and order is byte-identical (`TestBots_Attribution_Compat`, at HEAD and at base `db281db`). The aggregation now runs in Go (FU-2) (source: raw/2026-10-27-statistics.md §API, Changed routes; §Concept, Outcomes O4; §Open questions, FU-2).
- **Fit weights.** A logistic fit by Newton's method, L2 λ = 1, at most 50 iterations, fitted values clamped to `[0.05, 1.00]`; it writes nothing (`TestBots_FitWeights_WritesNothing`).
- **Model tiers (D3).** `measured`: the mean `cost_usd` over the last 7 Bangkok days when `calls_7d ≥ 20`. `list`: 1,500 input tokens for Jev and small; 2,500 input and 300 output for large. Then × `usd_thb` to 4 dp. No price row or no rate → `unavailable: true` (see [[model-routes-and-spend]]).
- **Recommendation and follow.** On [[signal-cited-orders]].

(source: raw/2026-10-21-bots.md §API, Behaviour worth knowing)

### `BotSummary` additions (contracts §8.1)

Six keys follow `last_run`: `probation {until, day, of: 30}` or `null`; `champion` (written only by slice 7's promote); `candidates_open` (the live count, any version); `next_wake` (`null` for `signal_driven`, `off`, legacy, manual and paused bots); `strategy {vocabulary, sources_weighted, decision_tier}` or `null` for the manual bot; and `sparkline`, at most 30 `day_end` marks `{day, equity}`, oldest first, from the 1m portfolio the summary already computes (S15). The web still reads the six keys leniently, because pre-slice-6 fixtures omit them (a follow-up) (source: raw/2026-10-21-bots.md §API, `BotSummary` additions; §Components, Data layer).

### FU-1 caps on the service (ORCH-10, contracts r2)

- **Per-class bounds.** `limits.max_candidates.<class>` is a whole number in 0–10, `limits.max_symbols.<class>` in 0–20. Over the cap: `400 invalid_request {field: "config.limits.max_candidates.<class>" | "config.limits.max_symbols.<class>", reason: "out_of_range"}`. It is a value rule after the grammar's `invalid`, checked `max_symbols` before `max_candidates`, classes in order. The templates (5 and 4) and the Upgrade (6 and 6) stay valid. `apperror.Detail.Field` now accepts dotted snake_case paths of at most 64 bytes.
- **At most 10 active auto bots.** Active means `kind = 'auto'` and `status IN ('running','observing')`; the manual bot and paused bots do not count. `POST /bots`, `POST …/clone` and `POST …/resume` refuse an 11th with `409 bot_limit_reached {limit: 10}` and write nothing. The count is taken under `pg_advisory_xact_lock(MeBotLockKey(user))`; Resume now takes that lock before its `FOR NO KEY UPDATE` row lock. Web copy: "You have 10 active bots. Pause one to start another."
- ***Run now*: 6 per bot and loop in a rolling 60 minutes.** The window counts `bot_run_requests.requested_at`, taken or not, and is checked after `run_pending`. The 7th is `429 run_rate_limited {retry_after_s}`: the whole seconds until the oldest of the six leaves the window, rounded up and at least 1, also sent as an integer `Retry-After` header. Nothing is written and no audit event fires. **FU-3:** the window count has no usable index; add `bot_run_requests (bot_id, loop, requested_at DESC)` in the next migration.
- Typed details are sanitised: `limit < 0` is sent as 0, `retry_after_s < 1` as 1.
- **Verified** by S11 unit and integration tests, including `TestBots_ActiveBotCap_Concurrent` (8 parallel creates at 9 active: exactly one 201) and `TestRunRateLimit_RetryAfter` (the oldest exactly 60 min old accepted, 1 s before the edge, sub-second rounding). On the preview the 7th *Run now* press answered 429 with `retry_after_s` 3398; the 11th active bot was not tried there.

(source: raw/2026-10-21-bots.md §Concept, The FU-1 spend caps; §API, Codes; §Test plan, Named acceptance tests and The E2E checks)

### Codes, audit, metrics and logs

| Code | HTTP | Where | `details` |
|---|---|---|---|
| `bot_name_taken` | 409 | create, clone | — |
| `version_unchanged` | 409 | save | — |
| `run_pending` | 409 | run | — |
| `too_few_decisions` | 409 | fit-weights | `{n_graded, needed}` |
| `candidate_not_applicable` | 422 | orders, estimate, skip | `{reason}` |
| `bot_limit_reached` (FU-1) | 409 | create, clone, resume | `{limit: 10}` |
| `run_rate_limited` (FU-1) | 429 | run | `{retry_after_s}` and `Retry-After` |

- Appended to `AllCodes()` in this order and to the README table (`TestCodes_Contract`).
- **Audit:** `bot_created {bot_id, template}`, `bot_cloned {bot_id, from_bot_id}`, `bot_version_created {bot_id, seq}`, `bot_run_requested {bot_id, loop}`, `recommendation_declined {decision_id, candidate_id}`; `bot_status_changed` gains `observing`. None carries a name, config, thesis or key (`TestAudit_BotEvents`, `TestLogs_NoBotTextOrConfig`).
- **Metrics:** `bots_created_total{template}`, `bot_versions_created_total`, `bot_run_requests_total{loop}`, all at 0 from startup; `bot_status_changes_total{to}` gains `observing` and counts saves too.
- **Logs** (ids only): `bot_created`, `bot_version_created`, `bot_run_requested`.

(source: raw/2026-10-21-bots.md §API, Codes, audit, metrics and logs)

### Service follow-ups

FU-2 (compare a skip's direction with its candidate's), FU-3 (the run-window index), and notes: J has no grants, so the owner-only Down is a procedure; bot names accept Unicode format characters (owner-only visibility); a clone copies a pre-cap over-cap config, which the bot reader then refuses, so it cannot spend; the universe read runs a 20-bar volume subquery per member (about 570); fit-weights runs the full attribution; README line 1878's audit row names only pause and resume (source: raw/2026-10-21-bots.md §Open questions).

## Slice 7: version windows, the champion and promotion (2026-10-27)

Slice 7 (see [[statistics]]) merged on 2026-10-27 as tidewatch-service #15 (`f289b9f`) and was deployed to production the same day. It added no migration: `bot_versions`, `bots.champion` and the `promoted`/`demoted` kinds already existed (J reserved the kinds for this slice). Route details are on [[stats-read-api]] (source: raw/2026-10-27-statistics.md §Concept, Stage, stated precisely; §Database).

### The version window (D2)

- A version's window is `[created_at, next version's created_at or now)`: `start` is the version's `created_at`, and `end` is the `created_at` of the next `seq`, or `null` for the current version, which the read's now closes.
- Stats grades one version over its window, or over `30d`, `90d` or a custom range of Bangkok dates clipped to it. Equity and benchmark are rebased to the window's first mark. **Probation does not move the start.**
- `GET /bots/{bot_id}/versions` (slice 6) gains its first web reader: it feeds the Stats *Version* select, newest first, with the service's label and "(current)".

(source: raw/2026-10-27-statistics.md §Concept, Owner decisions D2; How each figure is computed, The window; §Components, Data layer and stats-controls)

### The champion flag (D3)

- **One champion bot per user** (`bots.champion`), an auto bot. Before slice 7 nothing set it, so `recommendations.follow = "champion"` always fell back to the oldest auto bot with a scout (see [[user-settings]]).
- **First writer: `POST /bots/{bot_id}/promote`.** In one transaction it sets `champion = false` on the previous champion, then `true` on the challenger (`BotRepo.SetChampion`, owner-scoped). The flag is read by the Bots *Champion* tag and by the follow setting on their next read.
- **A later version of the champion keeps the flag,** and its out-of-sample record (the compare window) restarts.
- **The promotion check** runs over the shared window of the two current versions: the challenger's return is higher, its max drawdown no deeper, its ECE no worse (only when both sides state `p` with ≥ 30 graded), and it is active (`kind = 'auto'`, `status = 'running'`, probation over); the window must be at least 30 days. **The first champion** needs only its own window of ≥ 30 days and the active condition. There is no tolerance band.
- **Locking.** Promote holds `MeBotLockKey(user)` (the lock of create, clone and resume) and locks both bot rows `FOR NO KEY UPDATE` in ascending `bot_id` order (the lock of Pause, Resume and Save as vN), so no Pause, Save or promote can change the flag, status or `current_version` between the check and the flip. A Pause that wins the row lock makes promote answer `409 [not_active]` (`TestPromote_PauseRace`).
- **No production champion yet.** Promoting the first production champion is the owner's action, and the record shows none. A champion set by a promotion stays after a revert of the merge; clear it by SQL only on the owner's instruction.

(source: raw/2026-10-27-statistics.md §Concept, Owner decisions D3 and D4; §Database, What slice 7 writes; §API, Promotion semantics and locking; §Open questions, Rollout and production)

### `promoted` and `demoted` events

| Kind | Written on | `detail` | When |
|---|---|---|---|
| `promoted` | the challenger's current version | `{previous_champion: uuid \| null}` | every successful promote |
| `demoted` | the previous champion's current version | `{succeeded_by}` | only when there was a champion |

The actor is the session user. The same transaction writes the audit event `bot_promoted {bot_id, version (seq), previous_champion}`. A refused promote writes nothing. On the preview, E2E-002 left `promoted` × 2 and `demoted` × 1 on the `pv4-stats` bots, with PV4 Challenger holding `champion = true` (see [[statistics]]) (source: raw/2026-10-27-statistics.md §Database, What slice 7 writes; §Test plan, Preview database footprint).

### Route inventory after slice 7

- **Gated count 64** (61 production, 3 probes): 59 → 60 (S4) → 62 (S5) → 63 (S6) → 64 (S7).
- `TestRouter_NoDecisionMutation`'s reviewed `:bot_id` routes grow from nineteen to twenty with promote.
- **Promote does not call `EnsureBots`**, the one `/bots/{bot_id}` route that does not; it is recorded as an exception in the service `CLAUDE.md` (fold P3).
- **A champion without a current version** answers 500 on compare and promote (`ErrChampionWithoutVersion`, review L-1). It is unreachable, because slice 6 never leaves a bot without v1.

(source: raw/2026-10-27-statistics.md §API, Conventions; §API, `GET /stats/compare`; §Open questions, Other recorded residuals)

## Accounts and roles: plan limits on the bot routes (2026-10-29)

Accounts and roles (see [[accounts-and-roles]]) moved the slice-6 constants into the person's plan. The service's `Entitlements` is the only reader of the cap, the tiers and the starting capital. The founder plan keeps the slice-6 values (10, all four tiers, ฿1,000,000), so the observable limits did not change for the owner.

- **The active-bot cap.** `409 bot_limit_reached {limit}` on `POST /bots`, `/clone` and `/resume` now takes `limit` from the plan's `max_active_auto_bots`, counted under `MeBotLockKey`. The literals 10 and 1,000,000 left `internal/services/trading`. The web sentence reads "You have {n} active bots. Pause one to start another." from `details.limit`; at a cap of 1 it reads "1 active bots", the PRD's text verbatim.
- **Tier entitlement.** When the plan excludes the tier, `POST /bots`, `POST /bots/{id}/versions` and `POST /bots/{id}/clone` answer `400 invalid_request {field: "config.decision_tier", reason: "not_entitled"}`. A legacy v1 config counts as `none`.
  - **Precedence:** body and grammar refusals, then `not_entitled`, then the `limits.*` value rules, then `409 bot_limit_reached`.
  - **Web.** In the Create or Clone dialog this still shows the generic "Couldn't create the bot. Try again.". The editor greys an unentitled tier with *Not in your plan*.
- **`GET /model-tiers`.** Each tier gains `entitled: boolean` as its last key. The route still creates nothing, and the web reads `entitled` leniently (absent means `true`).
- **Starting capital.** `POST /bots` without `starting_capital` uses the plan's `starting_capital_thb`, and `EnsureBots` opens `me` and Slack Water at it.
- **Disable pauses through Pause.** An operator's *Disable sign-in* runs one locked transaction: `MeBotLockKey(user)`, then the users row, then the bot rows in ascending `bot_id`. Each running or observing auto bot is paused through the trading Pause path, writing `bot_status_changed {bot_id, from, to: "paused", reason: "user_disabled"}` with the operator as actor. *Enable* restores sign-in only, and the bots stay paused. A create, clone, resume or `EnsureBots` already waiting on the lock gets `401 unauthenticated`. On the preview (E2E-003), Slack Water went `running → paused` and stayed paused after *Enable*.
- **Gates.** The product group's role gate is `RequireRole("user")`, and the gated product count stays 64.
- **Service follow-ups:** the `PlanEntitlements` type assertion, the clamp class list, and `EnsureBots` ignoring the plan cap.

(source: raw/2026-10-29-accounts-roles.md §API, Product contract changes; §API, People, Writes; §Components, Product-side changes; §Test plan, What each E2E check showed, E2E-003; §Open questions, Recorded follow-ups, Service)

## Learning loop: learned versions, drafts and the `learn` loop (2026-10-30)

The learning loop (see [[learning-loop]]) merged on 2026-10-30 as tidewatch-migrations #14 (`8feeae3`) and tidewatch-service #16 (`3f8627a`), and was deployed to production. A version still never changes: learned behaviour reaches a bot only as a new version saved from a draft (D1).

### `learn`, the fourth loop

- **Migration M** re-creates `bot_runs_loop_check` and `bot_run_requests_loop_check` as `loop IN ('scout', 'manager', 'guard', 'learn')` (see [[centralized-migrations]]).
- **`POST /bots/{bot_id}/run`** accepts `{loop: learn}` and inserts a `bot_run_requests` row for the bot's `learning` runner (see [[bots-engine]]). `learn` on a version that is not v2 is `400 {field: loop, reason: invalid}`, "Learning needs a v2 version. Upgrade the bot first." (P8). It is checked after the manual and paused refusals and before `run_pending`. The slice-6 limit of 6 per hour per bot and loop applies. Audit `bot_run_requested` carries `{loop: learn}`, and `bot_run_requests_total{loop="learn"}` starts at 0.
- **`learn` rows are invisible to the existing bot reads (R4).** `BotRepo.LastRun`, `Runs`, `RunByID` and `LatestRunRequests` filter `loop <> 'learn'` (`TestBots_LearnRowsInvisible`), so `learn` rows never reach the slice-6 run reads; only the learning routes read them. `GET /stats` `kpis.cost_usd` still includes a learning run's labelling spend.

### The `learning` block and `learned` (S1, C15, P7)

- **One optional top-level key** of the v2 config, absent on every earlier version, so no stored hash changed. When present, every key is required and unknown keys are refused. It holds `learning_run_id`, `fitted_at`, `fitted_from`, `calibration.maps` (1–3, isotonic or Platt) and `meta_gate` (`family: "logistic_v1"` and its coefficients and thresholds). The validator's refusal order is on [[learning-loop]].
- **`learned := config.learning != null`.** There is no column.
- **`learned` on the wire.** It is the last key of `strategy` (on `GET /bots` and `GET /bots/{bot_id}`), of each `GET /bots/{bot_id}/versions` item and of the version detail. It is also on the Stats and compare `version` (see [[stats-read-api]]).
- **C15.** `bot-version.v2-learned.json` (sha256 `977068bf…`) is byte-identical in the service (`internal/trading/testdata/`), the bot and the web, pinned by `TestBotVersion_V2LearnedFixtureHash` with 10 accepted and 59 refusal cases (`TestValidateConfigV2_Learning`). C12 is unchanged.

### Save as vN of a draft (P2)

`POST /bots/{bot_id}/versions` takes `{config, probation?, learning_run_id?}`, still in the 64 KiB config group. With `learning_run_id`, the save locks the `bots` row `FOR NO KEY UPDATE`, then the run row `FOR UPDATE`, and refuses in this order:
1. bot `404`;
2. manual `400`;
3. a run that is not this bot's or user's: `404`;
4. `409 draft_not_pending`, "That draft was already saved or dismissed.";
5. `400 {field: config, reason: draft_mismatch}`, "The learned block can't be edited. Load the draft again." (the `learning` block must equal the draft's byte for byte);
6. `probation: false` on a learned config: `400 {field: probation, reason: invalid}`, "A learned version starts on probation.";
7. the validator;
8. `409 version_unchanged`;
9. the insert.

After the insert:
- The draft flips by a conditional `UPDATE … AND draft_status = 'proposed'` that must touch exactly one row, setting `saved` and `saved_version` in the same transaction.
- The `version_created` event and the audit `bot_version_created` gain `learned_from_run` and `draft_modified`, on a draft save only (OQ-S1). `draft_modified` is true when the saved config differs from `draft_config` outside `learning`.
- A learned config posted without `learning_run_id` is accepted with probation forced, and no draft changes.
- An unlearned save keeps the slice-6 order and messages byte for byte.
- `learning_run_id` must be absent, `null` or a UUID string, else `400 {learning_run_id, invalid}` (P1). A follow-up notes that `uuid.Parse` also accepts urn and brace forms.
- Since the branch update onto L, a learned save still gets the plan's tier check (`c29d0f0`; see "Accounts and roles" above).
- `learning_drafts_total{outcome: saved|dismissed}` counts saves and dismissals.

### Probation is forced for learned configs (D13, R12)

- **Save.** A learned config with `probation: false` is refused (step 6 above), whether or not `learning_run_id` was sent (`TestVersions_LearnedForcesProbation`). So a learned version is always saved with probation, with the status effects in "Status and probation" above. On the preview, E2E-001's learned v3 was observing with probation to 27 Nov.
- **Clone (R12, owner OQ-S2).** `POST /bots/{bot_id}/clone` of a learned source with `probation: false` is `400 {probation, invalid}` (`TestBots_CloneLearnedForcesProbation`). The PRD named no clone rule.
- **No automatic promotion.** A learned challenger reaches champion only through promote, which now refuses an unproven one (`calibration_not_comparable`; see [[stats-read-api]]).

### Route inventory after the learning loop

- **Gated count 70**: six new routes (the learning status, runs list, run detail, report, draft dismiss and the extraction-error export), 64 → 70 (`TestRouter_ForcedChangeGatesNewRoutes`). The five `/bots/{bot_id}/learning…` routes run `EnsureBots`; the export does not (P10). They are listed on [[learning-loop]].
- **New code.** `draft_not_pending` (409) is in `AllCodes()`.

(source: raw/2026-10-30-learning-loop.md §Concept, Problem; §Concept, Service rules; §Concept, Owner decisions D1, D13; §Concept, Decisions during the build OQ-S1, OQ-S2; §Concept, Spec corrections, OQ-S1, OQ-S2 / R12 and `learn` rows; §Database, Migration M and Who reads and writes what; §API, Conventions, Routes, Save as vN of a draft, Codes, audit, metrics and logs, and The `learning` block; §Test plan, Named acceptance tests; §Open questions, Recorded follow-ups, Service)

## Signals context: the optional `schedule.scout.discovery` key (2026-10-30)

Signals context (see [[signals-context]]; tidewatch-service #17, merge `ef9e93e`, verified live in production) added one optional key to the v2 vocabulary. The bot's `readConfigV2`, the service's `internal/trading/botconfig.go` and the web's `bot-config.model.ts` implement it identically (contracts r1 §2, ORCH-3). What the scout does with it is on [[bots-engine]].

```json
"scout": {
  "discovery": {
    "calendar": { "enabled": true, "sessions_ahead": "5" },
    "context":  { "enabled": true, "z_min": "2.0" }
  },
  "kind": "times",
  "min_impact": "0.45",
  "times": ["..."]
}
```

- **Absent means off (intent D2).** A config without `discovery` canonicalises and hashes exactly as before, so every existing version keeps its hash. `bot-version.v2.json` (C12) is unchanged (`44161eb0…8790`). A `bot-config.v3` was rejected.
- **When present,** both sub-objects are required, with closed key sets.
- **Values.** `z_min` is a decimal string in [0.5, 10] (web default `"2.0"`). `sessions_ahead` is a whole-number string in [1, 20] (default `"5"`). Both are checked whatever `enabled` is.
- **Refusals.** `400 invalid_request` with `details {field, reason}` and a dotted field such as `config.schedule.scout.discovery.context.z_min`. Reasons: `out_of_range`, `invalid`, `unknown_field` and `missing`. `"discovery": null` is `invalid`.
- **The sibling fixture.** `bot-version.v2-discovery.json` (28,847 bytes, SHA-256 `ce6242a9…5132`) is byte-identical in the bot (`packages/bots/fixtures/`), the service (`internal/trading/testdata/`) and the web (`src/app/pages/workspace/data/testdata/`). It holds 8 accepted cases and 33 refusals, each with its field and reason, and every reader runs them all.
- **Where it applies.** `POST /bots` and `POST /bots/:bot_id/versions` accept it. The service reads no discovery value. `GET /bots/:bot_id/upgrade` (the legacy translation) emits no `discovery`.
- **Release note: a behaviour change for API clients.** After migration N, re-posting a pre-N config without the three new `source_weights` entries (`finnhub-earnings-calendar`, `gdelt-gkg-en`, `gdelt-gkg-translation`) is `400 config.source_weights missing`, not `409 version_unchanged`. The web's forward rule (weight `"0"` for unlisted sources) is unaffected.
- **Run counts.** Scout runs carry `bot_runs.counts.by_discovery {signal, setup, context, calendar}`. The web ignores it (its readers drop unknown keys).
- **Merge with learning-loop.** After the M update, `botconfig.go` keeps both `discovery` and `learning`, with the shared optional-key helper renamed to `main`'s `objectWith`. The `learnedConfig` test fixture lists all 13 sources.
- **Tests:** `TestBotConfig_Discovery` (41 subtests), `TestBotVersion_V2DiscoveryFixtureHash`, `TestBotConfig_UpgradeTranslation_NoDiscovery`, `TestBots_Upgrade_NoDiscovery`, `TestBotVersions_Discovery`.
- **Open follow-up: `draft_modified` on an unedited learned draft.** It reads true for a learned draft fitted from a pre-N version, because the draft lists 10 sources and the web saves 13. Either the bot's draft writer should list all live sources at weight 0, or the service should ignore added zero-weight rows.
- **Service follow-ups (optional):** a full wrong-type matrix subtest (security L1) and the `wholeIn` / `wholeAtMost` duplication.

(source: raw/2026-10-30-signals-context.md §API, 1. Bot version vocabulary; §API, Bot-written jsonb; §Concept, Build-time decisions, Service release note; §Concept, Merge updates; §Test plan, Service; §Open questions)

## Related pages

- [[zone-transition-bot]]: slice 2b, the first auto bot built on this model
- [[paper-trading]]: the paper account each bot owns, and the order path both bots use
- [[decision-record]]: decisions now carry `bot_version`, `run_id` and `policy_result`
- [[centralized-migrations]]: migration F and its destructive down
- [[simulation-engine]]: slice 2, which created the `bots` table and the `me` bot
- [[auth-model]]: the session user who owns both bots
- [[request-protection]]: CSRF on the Pause and Resume POSTs
- [[bot-activity]]: the feature that added `outcomes`, `error` on the wire and the runs and watch routes
- [[bot-watch-verdicts]]: the WatchEntry stored in `outcomes`, contract C11 and the watch route
- [[bots]]: slice 6, which added v2 configs, create, clone, save as vN, probation and 14 routes
- [[bots-engine]]: the general engine that runs v2 configs, run requests and candidates
- [[user-settings]]: the `recommendations.follow` key
- [[signal-cited-orders]]: the recommendation route and `candidate_id` on orders and skips
- [[statistics]]: slice 7, which grades a version over its window and promotes a champion
- [[stats-read-api]]: the compare verdict, promote's locking and the attribution module
- [[accounts-and-roles]]: the plan that sets the active-bot cap, tiers and starting capital
- [[operator-console]]: *Disable sign-in*, which pauses a person's auto bots
- [[learning-loop]]: slice 8, whose drafts are saved as learned versions, and the `learn` loop
- [[signals-context]]: spec 3b, which added the optional `schedule.scout.discovery` key
