# Decision record

**Summary**: The `decisions` table is Tidewatch's append-only record of every trading decision: the order, or the skip, together with the price and market state at the time. The bot writes the outcome columns later, once each. Database triggers enforce this: no delete, no truncate, and updates only by back-fill. Since slice 2b (2026-10-09) the zone-transition bot writes its own rows, filling `actor = bot`, `run_id`, `bot_version` and `policy_result`, and its exits are stamped `exit_reason = 'zone'`. Later slices (Signals, Bots, Stats, post-mortems) train on this dataset and are graded against it. Since the bot-activity feature (2026-10-10), the bot's per-instrument verdicts in `bot_watch` and `bot_runs.outcomes` point into this table without a foreign key, and `HAS_DECISION` returns the suppressing decision's id instead of a boolean. Since the signals page (slice 4, merged 2026-10-12), a user order placed from a signal writes the four signal columns for the first time: `signal_ids`, `followed_recommendation`, `signal_snapshot` and `model`. Migration I adds a GIN index on `signal_ids`, which the Signals page's Bots column reads. No such order had been placed on any stack at merge. **Since slice 6 (bots, merged 2026-10-21, not deployed),** the general engine's three loops write their own decisions: the scout `propose`, the manager `buy | add | trim | close | skip` and the guard `close | trim`, each with `loop`, `candidate_id`, `market_state.elliott`/`regime` and, for signal-driven candidates, `signal_ids` and `signal_snapshot`. Bots now cite signals. The close stamp's `exit_reason` comes from the closing decision's `policy_result.exit_reason` (C4''), so `stop`, `invalidation`, `horizon` and `protect` appear beside `zone` and `user`. User orders and skips can cite a bot's candidate. `decisions` itself is unchanged; migration J's `candidates` rows point into it. **Since slice 7 (statistics, merged and deployed 2026-10-27),** Stats grades this record: per-version KPIs, calibration of the scout's stated `p`, attribution and losses all read it, and `post_mortem` has its first writer. `PUT /decisions/{decision_id}/post-mortem` is the one user write to a decision that the service admits; it sets a confirmed label on a losing bot `buy`/`add`, and the trigger freezes it once confirmed. No column, index or trigger changed. **Since the learning loop (slice 8, merged and deployed 2026-10-30),** the bot is the first writer of `post_mortem` with `labelled_by: "model"`: a learning run proposes a label for a closed losing entry where `post_mortem` is null, unconfirmed, and the rationale goes to the new `post_mortem_proposals` table. Confirming the model's label keeps `labelled_by: "model"`. On a learned version, the scout's `propose` rows carry the calibrated `p` with `p_raw` and `calibration` in `model`, and entries carry `policy_result.meta`. `decisions` itself is again unchanged (see [[learning-loop]]). **Since signals context (merged 2026-10-30),** every scout `propose` decision also carries `market_state.context` (the instrument's newest coverage features) and `market_state.calendar` (next earnings and next macro event), and `policy_result.discovery` names the paths that qualified the candidate. These are additive jsonb keys; the table is unchanged.

**Sources**: `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-21-bots.md`; `raw/2026-10-27-statistics.md`; `raw/2026-10-29-accounts-roles.md` (the backfill and operator visibility only); `raw/2026-10-30-learning-loop.md` (the model labeller, the provenance rule, the learned `model` and `policy_result.meta`, and the export only); `raw/2026-10-30-signals-context.md` (the additive `market_state` and `policy_result` keys only)

**Last updated**: 2026-10-31

---

## Why it exists

Before slice 2, nothing could be recorded. The decision record was built before any signal exists, so it is designed around orders and outcomes rather than one bot's needs. It also carries nullable columns for later slices, so slice 6 needs no migration (O7) (source: raw/2026-10-08-simulation-engine.md §Concept, Problem; §Database). That held: slice 6's migration J added `candidates`, `bot_version_events` and `bot_run_requests` but altered no `decisions` column (source: raw/2026-10-21-bots.md §Database).

## When a row is written

- **Orders.** `POST /orders` writes exactly one decision row in the same transaction as the order (see [[paper-trading]]). The row records:
  - `loop` and `actor`, both `user` for orders placed through the service (bot rows differ; see below);
  - `px_at_decision`;
  - `market_state`, taken from the latest strip-timeframe `indicators` row (see [[market-timeseries]]).
- **Order link.** `orders.decision_id` is a UNIQUE foreign key, so each order has exactly one decision. A position records `opened_by_decision_id`.
- **Skips.** `POST /decisions/skip` writes a decision with `action = 'skip'`. It takes `{instrument_id, direction, qty?, candidate_id: null, reason?}`, where `reason` is at most 500 runes and never logged. A stale `px:last` refuses a skip (R15). No UI calls this route in slice 2. Audit event: `decision_skipped`.

(source: raw/2026-10-08-simulation-engine.md §API)

### Bot rows (slice 2b)

The zone-transition bot writes decisions through its own intake (see [[paper-trading]] and [[zone-transition-bot]]):

- `actor = bot`, `loop = manager`, `run_id` (a real `bot_runs` row, see [[bot-versions-and-runs]]), `bot_version` (the 64-hex version hash) and `market_state`.
- `action` is `buy`, `close` or `skip`. `direction` follows the order side (`long` or `short`).
- **`policy_result`** = `{passed, rule: entry|exit, trigger: zone_turns_buy|zone_is_sell, timeframe, bar_ts, zone_run_started_at, reasons: []}`.
- A blocked entry is a `skip` with reasons (`insufficient_cash`, `position_limit`, `exposure_limit`, `max_open`, `qty_below_minimum`). An `observing` bot writes skip-shaped rows with `reasons = ["observing"]` (R6). A closed venue or missing price writes nothing, because deferral is not a decision.
- The bot acts at most once per (instrument, zone run).
- Audit: `order_placed` and `decision_skipped` with a null actor.
- **Not yet seen live.** No bot decision had been written on any stack when the source was written; the preview had 0 decisions at merge (FR-ZB-E2E-001 unverified).

(source: raw/2026-10-09-zone-transition-bot.md §API, Bot runtime and Audit events; §Concept, Proposed defaults; §Test plan, Acceptance status)

### Pointers from the bot's verdicts (bot-activity)

Since bot-activity, each evaluation records one verdict per universe instrument (see [[bot-watch-verdicts]]). Four verdicts point at a decision through `decision_id`: `decided` (a decision with the key already exists), `placed`, `skipped` and `observed`.

- **No foreign key.** `bot_watch.decision_id` and the `decision_id` inside `bot_runs.outcomes` have no FK, like `decisions.run_id`. The bot fills them only from bot-scoped reads.
- **Scoped decoration.** The service's watch route left-joins decisions scoped to the same bot (`d.bot_id = w.bot_id`) and owner, and returns `decision: {decision_id, action, ts}`. A pointer to another bot's or user's decision renders `null`, with the raw id kept as stored.
- **`HAS_DECISION` returns the id (R-BA1).** The bot's SQL changed from `SELECT EXISTS (…)` to `SELECT decision_id … ORDER BY ts, decision_id LIMIT 1`. It is still a lock-free read bound to the bot's own decisions through `decisions_bot_ts_idx`. `hasDecision` stays the boolean over that read, and a new `decisionId` returns the id; the pass calls it only on a hit. The intake's SQL text therefore moved, although `intake.ts` is byte-identical.
- **Decisions themselves are unchanged.** The pass writes the same decisions as in 2b for the same inputs, and the Decision record section on the Bots screen is unchanged (outcome O5).

(source: raw/2026-10-10-bot-activity.md §Database; §API, Service routes, Pointer decoration; §API, Bot runtime, `HAS_DECISION` and Unchanged by contract; §Concept, Plan resolutions, Bot R-BA1; §Concept, Outcomes)

### Orders that cite a signal (signals page, slice 4)

Before slice 4, `signal_ids`, `signal_snapshot`, `model` and `followed_recommendation` existed but had never been written. `POST /orders` accepted only an empty `decision_ctx`. Since tidewatch-service PR #10 (merge `8b18486`), an order may cite **exactly one** signal (see [[signal-cited-orders]]). Its decision row, written in the order's own transaction, records:

- `signal_ids = ARRAY[signal_id]`, in lower case;
- `followed_recommendation`, as sent: `true` from *Buy/Sell with recommendation*, and `false` once the user flips the side (ORCH-11);
- `signal_snapshot = {signal_id, document_id, source_code, tier, event_type, direction, p, p_up, p_down, p_neutral, impact, severity, horizon, created_at, recommendation}`. The recommendation is derived at order time from the same equity, price and rate the checks used, and it is `null` when the signal is neutral or the order cannot be sized;
- `model = {tier: "system1", model_id: <scoring_model_id>, direction, p, prompt_version, extraction_model_id, rationale}`.

**Writers.** Only the order path writes these four columns, inside the decision's own transaction. Without a cited signal they stay NULL, as before. A citation whose signal is unknown or names another instrument is refused with `422 signal_not_applicable` before any write. **Not yet seen live.** No signal-cited order had been placed on any stack at merge (FR-SP-E2E-004 unverified).

**Bots still cite nothing.** No bot cites a signal until slice 6, so the Signals page's "acted on by bots" count is 0 by design (owner decision D1). **Since slice 6 (merged 2026-10-21),** bot entries copy the proposing decision's `signal_ids`, so a bot's signal-driven trades now count in "acted on by bots" (see below).

(source: raw/2026-10-12-signals-page.md §Concept, Problem and Chosen design D1; §API, Order path; §Database, Writers; §Test plan, Acceptance status)

### Bot loop decisions (slice 6)

Since slice 6 (tidewatch-bot #10, merge `81133bf`, 2026-10-21; not deployed), the general engine writes decisions from three loops (see [[bots-engine]]). Every bot decision carries:
- `actor bot`, `bot_version`, `loop` (`scout`, `manager` or `guard`) and `run_id`;
- `candidate_id` wherever one exists (every propose, entry, add, trim, exit and guard close);
- `signal_ids` and `signal_snapshot`, null for setup-driven candidates and direct entries;
- `model` (`{tier: "none"}` for tier `none`), `market_state` **with `elliott` and `regime` filled** from `packages/waves` (the slots were empty before), and `policy_result`.

| Loop | Actions |
|---|---|
| scout | `propose`. A `down` signal over the threshold writes a `propose` with `direction = short`, reason `long_only`, and no candidate (D12, long only) |
| manager | `buy`, `add`, `trim`, `close`, `skip`. Entries copy `signal_ids`, `signal_snapshot` and `model` from the proposing decision (ORCH-9a). A skip or observed decision is written once per candidate and reason, not once per bar (ORCH-9b). A failed gate is a watch verdict, not a decision (S6) |
| guard | `close`, `trim`, with `policy_result {rule: "protect", exit_reason, level, last}` |

- **Probation.** An `observing` bot writes a skip-shaped decision with `reasons ["observing"]` once per candidate and places no order. On the preview, bot C wrote the scout `propose` and the manager's `skip` with `["observing"]`, and 0 orders.
- **Seen live.** On the preview (2026-10-21), bot decisions were written for real for the first time: buys by bots A and B carrying the candidate id, the cited signal (source `binance-th-listings`), the snapshot and the version, and guard closes with `exit_reason stop`.
- **User decisions that cite a candidate.** A `me` order placed with *Use this order* records `candidate_id`, `followed_recommendation` and the proposing decision's `signal_snapshot`/`model`. *Not this time* writes a skip with `loop user`, the candidate's `signal_ids` and `followed_recommendation false`. `POST /decisions/skip` now takes `candidate_id` (it was always null before). See [[signal-cited-orders]].
- **Append-only footprint.** The preview's E2E decisions stay on the shared retained volume and cannot be deleted (see [[bots]]).

(source: raw/2026-10-21-bots.md §The bot engine, Decisions written by the loops, Scout and Manager; §API, Behaviour worth knowing, Candidate citation; §Test plan, The E2E checks and Preview database footprint; §Concept, ORCH-9)

### Context and calendar on `propose` decisions (signals context, 2026-10-30)

Signals context (tidewatch-bot #18, merged 2026-10-30; see [[signals-context]]) adds bot-written jsonb keys. They are additive, for later consumers:
- **`market_state.context`** = `{ts, articles_24h, articles_z, tone_mean_24h, tone_z, countries_24h, publishers_24h, context_version}`, or null. It is the instrument's newest context feature row (see [[context-features-and-coverage-signals]]).
- **`market_state.calendar`** = `{next_earnings: {scheduled_date, time_hint} | null, next_macro: {title, scheduled_at} | null}`. Earnings within 30 days and economic events within 7 days count (see [[event-calendar]]).
- **`policy_result.discovery`** lists the paths that qualified the candidate, in the order `signal`, `setup`, `context`, `calendar`, with `context_z` for context (see [[bots-engine]]).
- **Every `propose` decision now carries `market_state.context` and `market_state.calendar`** (the context value is null when there is no feature row).
- **Coverage signals never enter the trigger path.** A context-driven candidate attaches the day's coverage signal, but `origin = 'context'` signals never qualify, never write a `long_only` refusal and never drive an add or trim. The learning loop's post-mortem `LATER_SIGNALS` query also reads `origin = 'document'` only.
- **Readers.** The web ignores these keys (its readers drop unknown keys). Slice 8's use of `market_state.context` and `.calendar`, and the "what the bot sees" view, are the expected next consumers.

(source: raw/2026-10-30-signals-context.md, summary block; §API, Bot-written jsonb; §Concept, How it runs, 5. Scout discovery and 6. Never a trigger; §Open questions, Assumptions still open)

### Post-mortem labels (slice 7)

Until slice 7 the `post_mortem jsonb` column existed, and the `decisions_backfill_only` trigger let a writer set it once and froze it once `"confirmed_by_user": true`, but nothing wrote it (source: raw/2026-10-27-statistics.md §Concept, Problem). Slice 7 (tidewatch-service #15, merge `f289b9f`, merged and deployed 2026-10-27) adds its first writer, `PUT /decisions/{decision_id}/post-mortem` (see [[stats-read-api]]).

- **The one decision mutation.** It is the only user write to a decision the service admits. `TestRouter_NoDecisionMutation` allows exactly this one `/decisions` write, with the comment "the post-mortem label is the one user write to a decision; the trigger limits it to post_mortem". The trigger still rejects any other column (`TestPostMortem_Refusals` checks a direct update).
- **What may be labelled.** A **losing decision**: an `actor bot` `buy` or `add` of one of the user's bots whose horizon column is graded and is not a hit. The horizon column comes from the decision's candidate (`intraday → r_1d`, `days → r_5d`, `weeks → r_20d`; anything else or no candidate → `r_5d`); a hit is a return `> 0` for `long` and `< 0` for `short`, and zero is a miss. A winner, an ungraded row, a skip or a manual decision is `400 not_a_loss`. The decision need not be of the bot's current version.
- **What is stored.** Exactly `{label, labelled_by: "user", confirmed_by_user: true, labelled_at}`, with `label` one of `signal_late`, `already_priced`, `regime_shift`, `stopped_by_noise`, `signal_wrong`, `sizing`, `execution` (D5). The write is a conditional `UPDATE … WHERE post_mortem IS NULL OR post_mortem->'confirmed_by_user' IS DISTINCT FROM 'true'::jsonb`, so an unconfirmed model proposal is replaced by the user's label.
- **Frozen once confirmed.** A second label on a confirmed row, a lost race and an identical repeat all answer `409 post_mortem_frozen`; the trigger would refuse the change anyway. Audit event: `post_mortem_labelled {decision_id, label}`.
- **Slice 8** will write model proposals into the same shape with `labelled_by: "model", confirmed_by_user: false`. Stats counts only labels whose `confirmed_by_user` is JSON `true` (the string `"true"` does not count). Slice 8 shipped this on 2026-10-30; see "Model-proposed labels and learned versions" below.
- **On the preview** (FR-ST-E2E-003, passed), *Regime shift* saved on screen was stored with `confirmed_by_user true`; a second save and a direct PUT got 409.
- **`documents/` drift.** `02-architecture.md` §11 lists a `post_mortems` table; post-mortems live in `decisions.post_mortem`.

(source: raw/2026-10-27-statistics.md §Database, What slice 7 writes; §API, Conventions and `PUT /decisions/{decision_id}/post-mortem`; §Concept, Owner decisions D5 and D8; §Concept, How each figure is computed, Post-mortem counts; §Test plan, The E2E checks; §Open questions, `documents/` drift)

## Schema

- uuidv7 primary key.
- Indexes:
  - `decisions_bot_ts_idx (bot_id, ts DESC)`;
  - `decisions_pending_outcomes_idx (ts) WHERE r_20d IS NULL OR mae IS NULL`.
- Columns for later slices, all nullable: `bot_version`, `loop`, `run_id`, `candidate_id`, `signal_ids uuid[]`, `signal_snapshot`, `model`, `policy_result`, `followed_recommendation`, `user_override_reason`.
- FU-8: the bot's outcome-pending predicate is wider than the partial index, so today it is a per-minute scan. That is trivial at current volume.
- Slice 2b's migration F left `decisions` untouched. The zone bot fills `bot_version`, `loop`, `run_id` and `policy_result`. `decisions.run_id` has no foreign key (service R10).
- **Signals exist since slice 3a (2026-10-11), but `decisions` is unchanged.** Migration H added the `signals` table and altered no earlier table. `decisions.signal_ids[]` is expected to reference `signals.signal_id` from slice 6, when the scout reads `signals`. Slice 3a changed no screen other than the Market watch cell, so the Decision record's *Signal* column is unchanged. See [[signals-pipeline]].
- **Since slice 4, migration I adds `decisions_signal_ids_gin_idx`** (`USING gin (signal_ids)`). It serves the Signals page's lookups of citing decisions: the list and export use `&&`, and the summary uses `@>`. `CREATE INDEX` is DDL, which the append-only triggers do not intercept. I's down drops the index and touches no decision data. User orders now write `signal_ids` (see above), and bot decisions are still expected to cite signals from slice 6 (see [[centralized-migrations]]). Since slice 6, bot decisions do write `signal_ids`, and `candidates.proposed_decision_id`, `entered_decision_id` and `declined_decision_id` are foreign keys into `decisions` (source: raw/2026-10-21-bots.md §Database, New tables).

(source: raw/2026-10-08-simulation-engine.md §Database; §Open questions; raw/2026-10-09-zone-transition-bot.md §Database; raw/2026-10-11-signals-ingest.md §Database; §Cross-cutting links; §Open questions, Other open items; raw/2026-10-12-signals-page.md §Database)

## Append-only enforcement

Migration E adds three triggers. Every error message starts with `decisions is append-only` (see [[centralized-migrations]]):

```sql
CREATE TRIGGER decisions_append_only          BEFORE DELETE   ON decisions FOR EACH ROW       EXECUTE FUNCTION decisions_reject_mutation();
CREATE TRIGGER decisions_append_only_truncate BEFORE TRUNCATE ON decisions FOR EACH STATEMENT EXECUTE FUNCTION decisions_reject_mutation();
CREATE TRIGGER decisions_backfill_only        BEFORE UPDATE   ON decisions FOR EACH ROW       EXECUTE FUNCTION decisions_backfill_only();
```

`decisions_backfill_only` compares the `to_jsonb` images of the old and new rows, with the outcome columns, `outcomes_detail` and `post_mortem` removed. Any column added later is therefore protected by default. The rules:

- `r_1h`, `r_1d`, `r_5d`, `r_20d`, `mae`, `mfe`, `mae_mfe_through`, `exit_reason` and `closed_at` are write-once: null → value.
- `outcomes_detail` (NOT NULL DEFAULT `'{}'`) stays an object and may only gain keys. The bot writes one top-level key per outcome column (C1).
- `post_mortem` can never return to null. It is frozen once it carries `"confirmed_by_user": true`.

The service has no update or delete route for decisions (`TestRouter_NoDecisionMutation`). `TestDecisions_DirectSQLMutationFails` proves the triggers reject direct SQL. The `events` table from slice 0 uses the same append-only pattern (see [[auth-model]]).

Because decisions cannot be deleted, the bot's sim integration specs leave `zztest-sim-*` users and `ZZTEST sim *` bots behind (R28). The migration's down step drops the table and every decision, and only the owner may run it (source: raw/2026-10-08-simulation-engine.md §Database; §Test plan). Slice 2b's bots integration specs likewise leave `zztest-bots-*` users and paused `ZZTEST bots *` bots behind (R17) (source: raw/2026-10-09-zone-transition-bot.md §Test plan, Commands).

**R4, the no-mutation route test was revised on purpose in slice 2b.** `TestRouter_NoDecisionMutation` used to ban `:bot_id` routes. Now only the reviewed `:bot_id` routes may exist, no route may take `:decision_id`, and only GET is allowed under `/bots/:bot_id/decisions`. There is still no route that creates, updates or deletes a decision (source: raw/2026-10-09-zone-transition-bot.md §Concept, Plan resolutions, Service R4; §API, Changes to slice-2 routes). Since bot-activity the test admits eight reviewed `:bot_id` routes, still with no `:decision_id` route and no mutation under `/bots` except Pause and Resume (source: raw/2026-10-10-bot-activity.md §API, Route inventory). Since slice 4 it also allows exactly `PUT /me/settings/:key` as a mutation route (R16), a settings write that never touches `decisions` (see [[user-settings]]) (source: raw/2026-10-12-signals-page.md §Concept, Plan resolutions, Service R16). **Since slice 7** it admits exactly one decision write, `PUT /decisions/{decision_id}/post-mortem` (above), and its reviewed `:bot_id` routes grow from nineteen to twenty with `POST /bots/{bot_id}/promote` (source: raw/2026-10-27-statistics.md §API, Conventions).

### `exit_reason = 'zone'` (contract C4')

The close stamp that sets `exit_reason` and `closed_at` on a position's opening decisions is now parameterised (C4', see [[paper-trading]]). It binds `'zone'` only when the closing order's decision has `actor = 'bot'` and `policy_result->>'rule' = 'exit'`. Every user close still binds `'user'`. Migration E already allowed `'zone'`, so no schema change was needed.

- **Known gap for slice 7.** A user closing a `me` position keeps `'user'` even when the zone is Sell. Stats should therefore read `policy_result`, not `exit_reason`, to tell rule-driven exits apart. As built, slice 7 grades only bot decisions (`me` appears only in Trade's follow-record sentence) and defines a loss by the horizon return, not by `exit_reason`; the losses list shows `exit_reason` as stored, worded "closed by stop", "closed by you" and so on (source: raw/2026-10-27-statistics.md §Concept, Owner decisions D1; §API, `GET /stats/losses`; §Components, losses-list).
- **Status.** Proven by unit, memory and SQL tests in both repos (FR-ZB-BOT-008). **No live bot exit has happened yet** (FR-ZB-E2E-002 unverified).

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Cross-project contracts; §Test plan, Acceptance status; §Open questions, Known gaps)

### C4'': exit reasons from `policy_result` (slice 6)

Since slice 6, `packages/sim`'s `closeStampReason` binds `policy_result->>'exit_reason'` from the closing decision: `stop`, `invalidation`, `zone`, `horizon` or `protect`. Without it, `rule = 'exit'` binds `zone` (legacy 2b exits), and anything else binds `user`. The `CloseStampSQL` text is unchanged; only the bound value changes. An unknown value throws `RangeError`. On the preview, two guard stops stamped `stop` (see [[paper-trading]] and [[bots-engine]]). The slice-7 gap above still holds for `me` closes (source: raw/2026-10-21-bots.md §The bot engine, C4''; §Test plan, The E2E checks).

## Outcomes (SIM7)

The bot's `sim` runner back-fills outcomes in a sweep every minute, at most 500 decisions per sweep. Any null outcome column is retried.

- `r_1h` uses wall time. It is null for daily-only instruments.
- `r_1d`, `r_5d` and `r_20d` use calendar sessions.
- MAE and MFE run up to the earlier of session 20 and the position close.
- Each column is written once.
- On the wire, `r_*`, `mae` and `mfe` are the stored ratio with 6 dp, never percent (ORCH-6). The web multiplies by 100.

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design and Bot deviations; §API, Wire formats)

**Preview status.** As of 2026-10-08, FR-SIM-E2E-005 (outcomes at +1 h and +1 session, then a second sweep that changes nothing) was **pending**. Outcome back-fill at real offsets has test evidence only (source: raw/2026-10-08-simulation-engine.md §Test plan, Acceptance status).

## Reading it back

- `GET /decisions?limit=1–200&cursor=` (default 50) uses keyset paging on `(ts DESC, decision_id DESC)` with an opaque, checksummed cursor. It returns `{items, next_cursor}`.
- The Trade screen's `app-decision-record` shows these columns: When, Decision, Signal ("Own idea, no signal"), Followed?, After 1 d, After 5 d ("Not yet" while null) and Post-mortem ("Not graded yet"). It shows 50 rows with *Load more*.
- The Overview KPI *Decisions* shows `{count, orders, skipped}`.

(source: raw/2026-10-08-simulation-engine.md §API; §Components)

**Slice 2b changes.**
- The wire `Decision` gains `bot_version` (string or null), `run_id` (uuid or null) and `policy_result` (object or null). They are always present, on `GET /decisions` and on the new `GET /bots/{bot_id}/decisions`, which pages the same way with a cursor bound to the bot (see [[bot-versions-and-runs]]).
- The web's `app-decision-record` is now shared by Trade and the Bots screen. It was refactored from injecting `TradeService` to inputs (`rows`, `state`, `loadMore`, `retry`, plus optional `note` and `emptyText`). Trade's specs are byte-unchanged and green (A8).
- On the web, a row counts as a bot decision when `policy_result` is not null (BW-5). Bot rows read "Buy NVDA 16.2", "Close NVDA 16.2" or "Skip NVDA" (a skip never shows its quantity). The second line reads "zone turned Buy · market · filled 187.63" or "· pending", or the first skip reason in words. The signal column reads "CDC zone · 1h" or "· 1d", and *Followed?* reads "—". Every other row keeps the slice-2 path byte for byte.
- The three new fields are optional on the web's `Decision` type and always set by the parser, so slice-2 typed fixtures compile unchanged (BW-2).

(source: raw/2026-10-09-zone-transition-bot.md §API, Changes to slice-2 routes; §Components, Shared with Trade and Data layer; §Concept, Plan resolutions, Web)

**Bot-activity changes.**
- **Cursor separation.** A runs cursor is refused on `GET /decisions` and `GET /bots/{id}/decisions`, and a decisions cursor is refused on `/runs`. The decisions cursor's bytes are untouched, pinned by the golden test `TestDecisionsCursor_ChecksumGolden` (checksum `f49e775ce4fa3e51f891f12ad89f2c5b`), so no issued decisions cursor breaks. Since ORCH-12, `parseDecisionsCursor` rejects a forged `t < 0` as 400 instead of reaching the query and returning 500 (see [[bot-versions-and-runs]]).
- **Placement on the Bots screen.** The new Checks section sits after the Decision record (BA3).
- **Then-mode decoration reuses the record (ORCH-5a).** In an expanded check, a `decided` or `placed` row is decorated like the live Watch only when its pointer matches a decision already loaded in the Decision record (or the current watch item). No request is made to decorate; otherwise the row reads "a decision exists for this bar" or "{buy | close} order placed".

(source: raw/2026-10-10-bot-activity.md §API, Runs cursor; §Concept, Plan resolutions, Service SA3/R6; §Concept, ORCH-12, BA3 and ORCH-5/5a)

**Signals page (slice 4).**
- **The Bots column reads citing decisions (owner decision D1).** Each signal row's `bots` lists the decisions whose `signal_ids` overlap the signal's id, on bots the session user owns, ordered by `ts` and then `decision_id`. Each entry is `{decision_id, bot_id, bot_name, actor, action, qty, ts, followed_recommendation}`. The web reads "No bot acted", or up to three lines such as "You bought 16.2" over "followed · HH:mm". Beside the PRD's three verbs ("bought", "sold", "skipped"), the web also words "proposed" and "protected" (SP-W-23).
- **"Acted on by bots" counts bot actors only.** The summary counts distinct signals cited by a decision with `actor = 'bot'`. A user's own citing decision is shown but never counted, because counting any bot trade on the instrument would attribute zone trades to news and corrupt slice 7's attribution.
- **Trade's Decision record is unchanged.** It already read "1 signal" and the followed flag.
- **Slice 6 makes the count real.** Bot entries now cite signals, so "acted on by bots" can be non-zero. Trade's Decision record still reads general-engine decisions through the existing closed maps (BT-W-9); wording them is a slice-7 follow-up (source: raw/2026-10-21-bots.md §Components, Trade; §Open questions, Web review follow-ups; §Cross-cutting links).

(source: raw/2026-10-12-signals-page.md §Concept, Chosen design D1; §API, `SignalRow` and Summary; §Concept, Plan resolutions, Service R6 and Web SP-W-23; §Components, Trade pre-fill, Unchanged)

**Graded by Stats (slice 7).** The Stats routes read this table in one `REPEATABLE READ READ ONLY` snapshot and compute every figure from it (see [[statistics]] and [[stats-read-api]]):
- **Counts:** a version's decisions in the window; skips are `action = 'skip'` except rows whose `policy_result->'reasons'` is `["observing"]`; orders are `buy, sell, add, trim, close`.
- **Calibration:** the version's `propose` rows whose `model->>'p'` is a decimal in [0, 1], graded at the candidate's horizon column.
- **Attribution:** bot `buy`/`add` rows by `signal_snapshot.source_code`, `event_type`, the instrument's asset class and `market_state->'regime'`, net of the modelled round-trip cost.
- **`follow_record`:** the `me` bot's order decisions of the last 30 days with `r_5d`, split by `followed_recommendation IS TRUE`.
- **Index use.** `period=30d` and the losses read use `decisions_bot_ts_idx`; `period=all` sequence-scans `decisions` at the preview's 99.7 % single-bot skew. No index was added (A7, the owner decides).

(source: raw/2026-10-27-statistics.md §Database, What the reads use and Index use; §Concept, How each figure is computed)

## Accounts and roles (2026-10-29)

- **Decisions survived the split unchanged.** Migration L touched `users`, `events` and `model_calls` but not `decisions`. On a copy of the retained preview database, decisions (32), positions, orders and fills were identical before and after L, with identical md5 fingerprints (E2E-005). The owner's decisions keep pointing at the same user id, now a plain person with role `user`.
- **Operators never read decisions.** The operator console shows counts and spend only, with no decisions, bot names, configs or impersonation (D6). The Decision record stays a per-person view.
- **A disable is audited in `events`, not here.** *Disable sign-in* pauses the person's auto bots through Pause and writes the audit events `session_revoked`, `bot_status_changed {to: "paused", reason: "user_disabled"}` and `user_disabled`, with the operator as actor (see [[operator-console]]).
- **The other append-only table changed.** `events` gained `actor_operator_id` through DDL, which the `events` append-only triggers do not intercept (A3). L's Down would drop that column and lose every operator actor, so the owner exports operator-attributed events before any Down (see [[centralized-migrations]]).

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built; §Database, Backfill, Notes on the schema and The Down; §API, People, Writes)

## Model-proposed labels and learned versions (learning loop, 2026-10-30)

The learning loop (migration M, tidewatch-service #16, tidewatch-bot #17; merged and deployed 2026-10-30; see [[learning-loop]]) reads this record as its training data and writes back into it in two narrow ways. Migration M altered no `decisions` column, index or trigger.

**The model labeller: the first `labelled_by: "model"` writer.**
- **Candidates.** A learning run's labelling job takes the bot's closed losses of any version in the last 90 days whose `post_mortem` is null, newest first, at most 100 per run.
- **The write.** One `post_mortem` model call per loss (Haiku through OpenRouter, `post_mortem.v1`). One READ COMMITTED transaction then sets `post_mortem = {label, labelled_by: "model", confirmed_by_user: false, labelled_at}` **only where it is still null**, inserts a `post_mortem_proposals` row, and writes the `model_calls` row and the spend upsert. If the owner labelled the decision meanwhile, the 0-row update skips the proposal row, and the call stays charged. The bot title is "writes post_mortem only where null".
- **`post_mortem_proposals`** (migration M) holds one row per decision (`decision_id` is its primary key and a foreign key to `decisions`): the label, the rationale (1–240 code points), `model_id`, `prompt_version` and `cost_usd`. It is append-only by convention, never updated or deleted. The rationale lives only here, never in `decisions.post_mortem`.
- **The trigger rules are unchanged.** An unconfirmed model proposal is not frozen, so the owner's PUT can replace it; a confirmed one is frozen.

**The PUT provenance rule (D10).** `PUT /decisions/{decision_id}/post-mortem` still writes only `post_mortem`:
- confirming the model's proposed label stores `labelled_by: "model"`, `confirmed_by_user: true`;
- a different label stores `labelled_by: "user"`, `confirmed_by_user: true`;
- the audit `post_mortem_labelled` always carries `confirmed_proposal`;
- a confirmed label is still frozen (`409 post_mortem_frozen`). On the preview (E2E-003), *Confirm* on a seeded proposal stored `{labelled_by: model, confirmed_by_user: true}`, and a second PUT got 409.

So Stats now has three labeller counts: user, model confirmed by the user, and proposed (see [[stats-read-api]]).

**What a learned version writes.**
- **`model` on the scout's `propose` rows.** With a calibration map for the candidate's horizon, `model.p` is the calibrated `p` (3 digits), and `model` also carries `p_raw` and `calibration {method, horizon, learning_run_id}`. Without a map, `p` is unchanged, `p_raw` is written and `calibration` is null. An unlearned version's `model` object is byte-identical to slice 6. D5: the calibrated `p` is what the bot states and what Stats grades, and refits always read `p_raw` (`model.p_raw ?? model.p`), so maps never compound.
- **`policy_result.meta {p_loss, effect: none|shrink}`** on a gated version's candidate-entry intake decisions, skips and observing decisions included. A veto writes no decision at all; it is a `gated` watch verdict (see [[bot-watch-verdicts]]). Trade's decision record words a shrunk entry's second line "size halved by the failure model" (`feat-trade/util/order-view.ts:377`).
- On the preview (E2E-001), the next scout wake on a learned v3 wrote `model.p 0.597`, `p_raw 0.730` and `calibration {isotonic, days, run}`.

**The extraction-error export reads this record (D11).** `GET /learning/extraction-errors` streams, on demand, the user's `actor bot` `buy | add` decisions whose label is a **confirmed** `signal_wrong`, joined to their signal, document and newest extraction. It writes nothing, and nothing is trained on it (see [[learning-loop]]).

**`documents/` drift, again.** `02-architecture.md` §11 lists a `post_mortems` table. Post-mortems live in `decisions.post_mortem`, and `post_mortem_proposals` holds only the model's rationale.

(source: raw/2026-10-30-learning-loop.md §Concept, Problem; §Concept, The four jobs, `labels.ts`; §Concept, A learned version in the engine; §Concept, Service rules; §Database, Migration M and Notes on the schema; §API, Routes, The export line and Codes, audit, metrics and logs; §Components, Words elsewhere; §Test plan, What each seeded E2E showed; §Open questions, `documents/` drift)

## Related pages

- [[simulation-engine]]: the slice-2 overview
- [[paper-trading]]: the order path that writes each decision, and the `sim` runner that back-fills it
- [[centralized-migrations]]: migration E and its destructive down
- [[market-timeseries]]: the `indicators` row behind `market_state`
- [[auth-model]]: the append-only `events` table, the same pattern from slice 0
- [[zone-transition-bot]]: slice 2b, the first bot that writes its own decisions
- [[bot-versions-and-runs]]: the `bot_versions` and `bot_runs` rows that bot decisions point to
- [[bot-watch-verdicts]]: the verdicts whose `decision_id` pointers lead into this table
- [[signals-pipeline]]: the `signals` rows that `signal_ids[]` references
- [[bot-activity]]: the feature that added the Checks section after the Decision record
- [[signal-cited-orders]]: the order path that writes the four signal columns, and the recommendation it snapshots
- [[signals-page]]: the slice-4 overview, whose Bots column reads citing decisions
- [[signals-read-api]]: the `bots` field and the `acted_on_by_bots` count
- [[bots]]: slice 6, whose loops write propose, entry, add, trim, exit and guard decisions
- [[bots-engine]]: the scout, manager and guard, and the C4'' close stamp
- [[statistics]]: slice 7, which grades this record and adds the post-mortem label
- [[stats-read-api]]: the post-mortem PUT and the Stats reads of this table
- [[accounts-and-roles]]: the person model; decisions survived the backfill and stay hidden from operators
- [[learning-loop]]: slice 8, which learns from this record and writes model-proposed labels into it
- [[signals-context]]: spec 3b, which adds `market_state.context`, `market_state.calendar` and `policy_result.discovery`
