# Learning loop (`learning-loop`, slice 8)

**Summary**: Before slice 8 nothing fed a bot's graded decisions back into the bot. Stats graded a version's stated `p` but never corrected it. Source weights were set by hand or by a one-off fit. No model predicted which entries fail. A losing trade got a reason only when the owner typed one. The slice-7 promotion check *skipped* `calibration_no_worse` when a side had fewer than 30 graded proposals. Slice 8 added a monthly **learning loop that proposes changes and never applies them**. A new `learning` runner in the bot (the fourteenth collector, lock `runner:learning`) gives each eligible auto bot (a v2 version, `running` or `observing`) one **learning run** on the 1st of the month at 03:00 Bangkok, or when the owner presses *Run learning now*. A run reads the bot's current version over the last 90 days and runs four jobs: **recalibration** (isotonic or Platt per horizon, proposed only when it cuts the out-of-sample ECE by at least 20 %); **source weights** (seeded Thompson posteriors collapsed to per-source weights, moved at most ±0.25 a run); a **failure meta-model**, `logistic_v1` (walk-forward with purge and embargo; its gate opens above a mean out-of-sample AUC of 0.58 over at least two folds); and **post-mortem labels** (one proposal per closed losing entry, from the new `post_mortem` model stage, Haiku through OpenRouter). A run that proposes something writes a **draft**. The owner loads it into the editor and saves it as vN, and a learned version always starts on probation. On a learned version the scout states the calibrated `p` and keeps `p_raw`. The manager's gate can only **veto** an entry (a `gated` verdict, `meta_veto`) or **halve** its size; it never raises size. Stats counts a model label only once the owner confirms it. Promote refuses a learned challenger whose calibration test would be skipped (`calibration_not_comparable`). An API-only JSONL export lists the confirmed `signal_wrong` losses, and nothing is trained on it. Each run's markdown report is stored on `learning_runs.report` and served by the API; the loop never writes this wiki (D12, the Q12 ruling). Migration **M** (`20261028120100`) is the new required schema version. Labelling spend is attributed to the bot and its owner, and counts against the per-bot share and the person's allowance (OD-LEARN-SPEND). **Status (2026-10-30):** merged by Claude on the owner's instruction (migrations #14, service #16, bot #17, web #21) and **deployed to production**. Of 43 acceptance IDs, 40 are verified, 2 partial (FR-LL-WEB-007, FR-LL-E2E-003) and 1 unverified (FR-LL-DOC-002, a recorded deferral); none failed. **No scheduled production run has happened yet**; the first is due 2026-11-01 at 03:00 Bangkok. **No model-written post-mortem has been produced in any environment**, because the preview's OpenRouter key was refused on every call.

**Sources**: `raw/2026-10-30-learning-loop.md`

**Last updated**: 2026-10-31

---

## Stage, stated precisely

| Stage | Status (2026-10-30) |
|---|---|
| Implemented | **Migrations:** MIG1–MIG3 in `6f776c0`; the branch update merge `49f06b9`, then `d28de68` (PR head). **Bot:** MIG1–S9, SM1 and FIX-G1, plus XF-2, review fix round 1 and the round-2 polish (code `ab68c93`, plan `de9ff78`); branch update `119acd5`, `857cac3`, `c82da43`, `f753cf3`; OD-LEARN-SPEND `1c3317b`, `7b9e724`, `04c8fe5`, `1e8d8ec`, `435feb4` (PR head). **Service:** SVC1–SVC11, review fix round 1 and the polish (code `20e9697`, plan `0c140c4`); branch update `b59bcc5`, `5400c5e`, `98211ab`, `c29d0f0`, `48f179d` (PR head). **Web:** S1–S11, XF-1, review fix round 1 and the polish (code `d5671e0`, plan `b84fd55`); preview rounds `3cb3fb4`, `13d1267` (PF1), `864714c`; branch update `6eff940`, `f2ee96c`; a merge of `main`, `568002f` (PR head) |
| Reviewed | Plans and code in all four repositories. Plan-review fix loops: bot 2, service 2, web 3. Code-review fix loops: one round each in bot, service and web. Then a polish round, the preview design re-check, and two reviews of the branch update |
| Verified locally | Every step's contract commands exited 0, and the orchestrator re-ran them. The long integration suites were re-run in full on the final trees |
| Verified on a preview | **Yes.** A per-run isolated, retained database at M without L, 2026-10-28 15:29Z to 2026-10-29 03:33Z (PV1–PV5). After the merges with L it was refreshed with L applied out of order, and PV6 ran on 2026-10-30, 03:16Z–09:24Z (see [[forge-preview-gateway]]) |
| Merged | **Yes**, 2026-10-30, by Claude on the owner's instruction (OD-MERGE-1, "Merge them for me"), in the order migrations → service → bot → web: migrations #14 → `8feeae3` (head `d28de68`), service #16 → `3f8627a` (head `48f179d`), bot #17 → `2a3a412` (head `435feb4`), web #21 → `de00a5f` (head `568002f`) |
| Deployed | **Yes, to production.** A merge to `main` is a production deploy (deploy-prod → GHCR → tidewatch-kubernetes GitOps bump → ArgoCD). M was applied by the service's ArgoCD sync, through the migrate Sync hook at wave −1 |
| First scheduled production run | **Not yet.** Due 2026-11-01 03:00 Bangkok (2026-10-31T20:00Z) for each eligible bot whose current version predates it (S3) |
| Documentation pass | The raw source and this wiki update. `tidewatch-specs` and `tidewatch-apis` are not git repositories and were not edited, so the spec corrections below are carried only here. `documents/` is untouched (slice-0 D17) |

The source takes `state.json` as authoritative for the branch update, merge and deploy, and `verification.md` for the verified, partial, unverified and failed counts. `verification.md`'s header still says "NOT merged; NOT deployed", because it was written on 2026-10-29. `state.json` still says `perProject.*.phase: AWAITING_MERGE` beside `prState: MERGED`, because the phase field was not advanced (source: raw/2026-10-30-learning-loop.md, summary block; Sources, Record notes and Not changed by this build; §Concept, Stage, stated precisely).

## Why the slice exists

As found at `main` on 2026-10-27 (intent "Problem and evidence"):
- **The decision record already held every input.** A scout `propose` carries `model {tier, model_id, direction, p, rationale, prompt_version}`, `signal_snapshot`, `market_state` (regime, Elliott, zone) and `candidate_id`. Outcomes `r_1h…r_20d`, `mae`, `mfe`, `exit_reason` and `closed_at` are back-filled once. `post_mortem` is writable once and frozen once confirmed (see [[decision-record]]).
- **Slice 7 fixed the shapes this slice extends:** `post_mortem {label, labelled_by: user|model, confirmed_by_user, labelled_at}`, the losses list with a slot for a model proposal, and `GET /stats/compare` plus promote with five conditions, where `calibration_no_worse` was skipped when a side stated no `p` or had fewer than 30 graded (see [[statistics]]).
- **A version never changes, and the v2 vocabulary is closed,** so learned behaviour can reach a bot only through a new version (see [[bot-versions-and-runs]]).
- **The runtime hooks.** `bot_run_requests` is the only path from the service to the bot. `bot_runs.loop` and `bot_run_requests.loop` were CHECKed to `scout | manager | guard`, and the model stages to five values.
- **Spend.** One $1/day Bangkok-day ceiling, a 25 % per-bot share, and since accounts and roles a per-person `daily_model_usd` of $0.50 (see [[model-routes-and-spend]]).
- **Thin data.** Driftline (News drift, tier `jev`) is observing until about 2026-11-26. It writes proposals with a stated `p` but no entries. So calibration can reach its 150 floor within weeks, while weights, the meta-model and labels need graded entries.

(source: raw/2026-10-30-learning-loop.md §Concept, Problem)

## The model, as built

### The `learning` runner (`packages/bots/src/learning/runner.ts`)

- **Name, lock and switch.**
  - `learning` is the fourteenth and last of the `COLLECTOR_NAMES` and holds `runner:learning`. It has no per-bot lock, no account lock and no venue budget. `serve` starts it; it is never a one-shot job.
  - There is **no `LEARNING_ENABLED`** (owner OQ-1). An empty `MARKET_DATA_COLLECTORS` runs it, and an explicit list must name `learning`. The production chart sets `collectors: ""`, so it runs with no owner action.
  - `LEARNING_EVAL_INTERVAL_MS` (default 60 000; an integer from 1 000 to 86 400 000) is the only new variable (see [[market-data-worker]]).
- **A pass, in order:**
  1. Sweep learning runs left `running` for over 30 minutes (`failed`, `interrupted`).
  2. Take the `learn` requests in one statement (`TAKE_LEARN_REQUESTS`).
  3. Read the learning bots (`LEARNING_BOTS`, which joins `users` and `plans` as the evaluated-bots read does).
  4. Run each requested bot as `manual`, then each due bot as `scheduled`.

  At start the runner releases `learn` requests taken without a run.
- **The due rule (S3).** A bot is due at the first 1st of the month, 03:00 Bangkok, strictly after the later of its newest learning run and its current version's `created_at`.
  - Missed slots collapse into one, and a paused bot is never due.
  - A failed scheduled run waits for next month (owner OQ-3); *Run learning now* is the retry.
  - A legacy (v1) version is skipped silently when scheduled. When requested, it gets one `failed` manual run.
- **The bots runner never takes a `learn` request.** Its take adds `AND r.loop <> 'learn'`, and its start-up sweeps skip `learn` rows too, because a learning run outlives the bots runner's 5-minute cutoff (review B1; see [[bots-engine]]).
- **D4: a separate runner,** not a fourth loop inside the bots pass, which would break the guard's 90 s bound.
- **What it never writes:** `bots`, `candidates`, `orders`, `ledger` or `bot_watch`, and it never places an order. Runs are sequential, so a pass holds at most one pooled connection, and no transaction spans a model call.
- **`learning_lock_busy`:** a requested bot whose learning run is still `running` and not yet swept is left alone, and its request waits.

(source: raw/2026-10-30-learning-loop.md §Concept, The model, as built, The runner; §Concept, Owner decisions D4; §Concept, Decisions during the build OQ-1, OQ-3)

### Populations and floors (PRD §4.2, D2)

The window is `[max(now − 90 d, version.created_at), now)` over the current version.

| Job | Population | Floor |
|---|---|---|
| Calibration | graded proposal rows (stated `p`) | 150; a horizon under 50 rows gets no map (`too_few`) |
| Weights | graded entry rows with a cited signal | 100; a source moves only with ≥ 10 graded rows |
| Meta-model | graded entry rows | 150, of which ≥ 30 losses |
| Labelling | the bot's closed losses of any version in the last 90 days with `post_mortem` null, newest first | none; at most 100 per run |

Below its floor a job proposes nothing. The run still succeeds, writes its floors and report, and on a learned version writes the realised calibration line (D15: runs happen on observing bots and on empty data) (source: raw/2026-10-30-learning-loop.md §Concept, Populations and floors; Owner decisions D2, D15).

### The four jobs

All four are pure TypeScript with no new dependency: floats inside, decimal strings out, and a seeded PRNG recorded on the run.

- **Calibration (`calibrate.ts`, D5, S7).**
  - Rows are sorted by `ts`; the first ⌊2n/3⌋ fit and the rest test.
  - It fits isotonic (pool-adjacent violators, at most 64 points) and Platt (Newton, L2 0.01, `p` clipped to [0.001, 0.999]) on `p_raw` (`model.p_raw ?? model.p`), so maps never compound.
  - The method with the lower out-of-sample ECE wins (ten bins, 4 digits; ties go to Platt). It is **proposed** when `ece_map_oos ≤ 0.8 × ece_raw_oos`. The proposed points come from a refit on the whole window, and both methods' rows are written to `calibration_maps`.
  - On a learned version with ≥ 30 graded, the summary carries `calibration.realised {ece_calibrated, ece_raw, n}`, and the report words it "helped", "did not help" or "made it worse" (the roadmap exit-test record).
- **Source weights (`weights.ts`, D6, S9, S20).**
  - Each arm (source × event type) gets `Beta(1 + wins, 1 + losses)`. A win is a net `r_5d > 0` after the modelled round-trip rate (the C14 port of the service's `ModelledCostRate`; see [[stats-read-api]]).
  - Per source, the weight is the count-weighted posterior mean over its arms, scaled so the largest is 1.00, clamped to [0.05, 1.00] and moved at most ±0.25 from the current weight (2 digits). 1,000 seeded draws give the 10th–90th percentile "likely range".
  - Event-type arms and return-weighted means are **reported, never applied** (D6).
- **The failure meta-model (`meta.ts`, D7, D8, S10).**
  - **Features**, a closed list in a fixed order: `impact`, `p_raw`, `severity`, `atr_pct`, then one-hots for tier, source, event type, horizon, regime trend and volatility, zone, asset class, entry condition and weekday, plus `elliott_candidate`. They are standardised on the training rows; a zero-variance feature is dropped and recorded.
  - **Folds** test `[T0 + k·30 d, T0 + (k+1)·30 d)` for k ≥ 1. A fold's training rows need `ts + purge(horizon) < fold start − 5 d` (a 5-day embargo). Purge margins are **7 / 14 / 39** calendar days for intraday / days / weeks (A3). A fold needs ≥ 20 test rows and ≥ 5 rows of each class.
  - Each fold fits L2 logistic regression by Newton (λ = 1, at most 50 iterations) and reports its AUC.
  - **The gate opens** when the mean out-of-sample AUC is above 0.58 over **at least two folds** (`MIN_FOLDS = 2`, OQ-G1). When open, the refit on all rows is written as `meta_gate` with `veto_above "0.70"`, `shrink_above "0.55"` and `shrink_factor "0.5"`.
  - `family` is recorded so `gbdt_v1` can follow later (D7).
- **Post-mortem labels (`labels.ts`, D9, S12).**
  - One `post_mortem` call per candidate loss (`post_mortem.v1`; `openrouter`, `anthropic/claude-haiku-5.5`, no fallback) through `openSignalsModels`, with its ledger, ceiling, reservations and deadline (see [[model-routes-and-spend]]).
  - The prompt carries the decision, the price path and up to 10 later signals of the instrument in the five sessions after entry. It carries no key, body or URL.
  - The reply `{label, rationale}` is Ajv-checked, and the rationale is fitted to 240 code points.
  - **One READ COMMITTED transaction per proposal:** `post_mortem` only where null (`labelled_by: "model"`, `confirmed_by_user: false`), a `post_mortem_proposals` row, the `model_calls` row (with `bot_id` and the owner's `user_id`) and the spend upsert. A 0-row update (the owner labelled meanwhile) skips the proposal row and keeps the charged call.
  - **Two budget checks before every call:** the bot's 25 % share (`BOT_COST_FOR_DAY`, the bot's scout and learn runs of the day), then the owner's `plans.daily_model_usd` (`OWNER_COST_FOR_DAY`, scout and learn runs across all the owner's bots). Each adds the run's tally and the call's estimate. Over either check, or on a global ceiling refusal, labelling stops for the run (`budget_stopped`, `learning_budget_reached {budget: bot|user|ceiling}`) and the rest wait.

(source: raw/2026-10-30-learning-loop.md §Concept, The four jobs; Owner decisions D5–D9; Decisions during the build OQ-G1, A3)

### The draft and the report (D1, D12, S13, S14)

- **A draft is written** only when weights, calibration or the gate propose something. It is `canonical(current config with source_weights replaced and learning = {learning_run_id, fitted_at, fitted_from: current hash, calibration, meta_gate})`.
- **D1: learned results live only in a draft version.** Maps or models read by reference from a running version were rejected. Nothing changes a running bot.
- **One pending draft per bot.** A partial unique index enforces it. A new draft supersedes the old one (`dismissed`, reason `superseded`) in the run's final transaction. A run that proposes nothing leaves the pending draft in place (owner OQ-2).
- **SF-C1, a documented limitation.** A draft carries only this run's proposals. Within about 60 days of saving a gated or mapped version, a new draft has `meta_gate: null` (`too_few_folds`) and lacks unproposed maps, so saving it switches that gate or map off. The change list shows it (`learning.meta_gate: logistic_v1, AUC x → none`).
- **The report** is a pure render of `summary`, at most 64 KiB, stored on `learning_runs.report`. It covers the floors, calibration per horizon, the weights table and the arms "shown, not applied", the folds, AUC and importances, the post-mortems, the draft's change list and the cost. It prints 4-digit ECE (the PRD example shows 3). Its budget line shows the bot share only.
- **The seed** is the first 16 hex characters of `sha256(bot_id ‖ started_at)`. The same rows and seed give the same bytes.
- **D12, revised in the Q12 discussion (2026-10-27): the report never goes to the wiki.** The report is a system artefact, rendered from the run's summary, stored on the run and served by the service. `tidewatch-wiki` is the project's knowledge base, not the system's memory, and the bot in Kubernetes could not write to it anyway. So the brief's "written to the wiki `raw/` folder" is recorded drift and is not followed.

(source: raw/2026-10-30-learning-loop.md §Concept, The draft and the report; Owner decisions D1, D12; Spec corrections SF-C1, Q12 / D12)

### A learned version in the engine (D5, D8, S8, S11)

- **The scout.** After a survivor's `p` is settled, if `learning.calibration` has a map for its horizon, `p_cal = apply(map, p)` (3 digits). The candidate gets `p = p_cal`, and the `propose` decision's `model` carries `p: p_cal`, `p_raw` and `calibration {method, horizon, learning_run_id}`. Without a map, `p` is unchanged, `p_raw` is written and `calibration` is null. Tier `none` is untouched, and an unlearned version's `model` object is byte-identical to slice 6.
- **D5.** The calibrated `p` is what the bot states and what Stats grades; `p_raw` is kept.
- **The manager.** After `allocation`, with a non-null `meta_gate`, it computes `p_loss = sigmoid(intercept + Σ coef·(x − mean)/scale)`:
  - `p_loss ≥ 0.70` is a `gated` watch verdict with reasons `["meta_veto"]` and no decision;
  - `0.55 ≤ p_loss < 0.70` multiplies `sizedBudget` by 0.5 before the room and cap;
  - below that the entry is unchanged.
- Entries record `policy_result.meta {p_loss, effect: none|shrink}`. Direct entries (zone turns, `scout.kind = off`) are exempt. **D8: the gate only vetoes or shrinks; it never raises size.**

Details are on [[bots-engine]], [[decision-record]] and [[bot-watch-verdicts]] (source: raw/2026-10-30-learning-loop.md §Concept, A learned version in the engine; Owner decisions D5, D8).

### Service rules (service `CLAUDE.md` "Learning invariants (slice 8)")

- **Learned is derived from the config.** `learned := config.learning != null` (S1); there is no column.
- **Save as vN of a draft.** `POST /bots/{id}/versions` with `learning_run_id` locks the bot row, then the run row. It refuses a foreign or unknown run (`404`), a draft no longer `proposed` (`409 draft_not_pending`) and a `learning` block that differs from the draft's byte for byte (`400 {config, draft_mismatch}`). It flips the draft to `saved` with `saved_version` in the same transaction.
- **Probation is forced (D13).** A learned config with `probation: false` is `400 {probation, invalid}`, whether or not `learning_run_id` was sent. A clone of a learned source cannot skip probation either (R12, owner OQ-S2).
- **Dismiss** is one conditional statement plus the audit row `learning_draft_dismissed`.
- **The PUT provenance rule (D10).** Confirming the model's label stores `labelled_by: "model"`, `confirmed_by_user: true`. A different label stores `labelled_by: "user"`.
- **The learned-challenger gate (D13).** A skipped `calibration_no_worse` on a learned challenger becomes `met: false`, `detail {not_comparable}`, and promote refuses with `calibration_not_comparable`. The first-champion branch is unchanged, and there is no automatic promotion.
- **The export (D11)** is generated on demand from existing tables and writes nothing: no table, no file, no training.

Route-level detail is on [[bot-versions-and-runs]] and [[stats-read-api]] (source: raw/2026-10-30-learning-loop.md §Concept, Service rules; Owner decisions D10, D11, D13; Decisions during the build OQ-S2).

### Spend attribution (OD-LEARN-SPEND)

The branch-update review found that `post_mortem` `model_calls` were unattributed, so they showed as ingest on the console's Spend view, and that learn spend sat outside the per-person allowance. The owner ruled on 2026-10-29T14:30Z: **"Count it fully".**
- `post_mortem` `model_calls` rows carry `bot_id` and the owner's `user_id`.
- The owner's day spend reads scout **and learn** runs (`OWNER_COST_FOR_DAY`, renamed from `SCOUT_COST_FOR_OWNER_DAY`). `BOT_COST_FOR_DAY` sums scout and learn runs per bot.
- The labeller checks `spent_user + tally + estimate ≤ plans.daily_model_usd` after the per-bot share.
- **Recorded residuals.** Pre-fix `post_mortem` rows keep NULL attribution (12 on the preview, none in production). The share and the allowance each hold per runner, so a concurrent scout wake and learning run do not see each other's in-flight tally; the global ceiling holds. The report's budget line shows the bot share only. `.plans/accounts-roles.md` still names `SCOUT_COST_FOR_OWNER_DAY`.

Details are on [[model-routes-and-spend]] and [[accounts-and-roles]] (source: raw/2026-10-30-learning-loop.md §Concept, Decisions during the build OD-LEARN-SPEND; Branch update onto L; §Open questions, Recorded residuals).

## Data: migration M

M is `20261028120100_learning_loop.sql` (tidewatch-migrations #14, merge `8feeae3`). It adds three tables and widens five CHECKs:
- **`learning_runs`**: one row per run, with `trigger` (`scheduled | manual`), `status` (`running | succeeded | failed`), the window, `seed`, `floors`, `summary`, `counts`, the draft (`draft_config`, `draft_status` `proposed | saved | dismissed`, `dismissed_reason` `user | superseded`, `saved_version`) and `report` (≤ 65,536 bytes). The partial unique index `learning_runs_pending_draft_key` keeps one `proposed` draft per bot.
- **`calibration_maps`**: one row per run, horizon and method, with `points`, `n_fit`, `n_test`, `ece_raw_oos`, `ece_map_oos` and `proposed`.
- **`post_mortem_proposals`**: one row per decision (append-only by convention), holding the label, the rationale (1–240), the model and prompt version and `cost_usd`.
- **CHECKs widened:** `loop` gains `learn` on `bot_runs` and `bot_run_requests`; `stage` gains `post_mortem` on `model_routes`, `model_calls` and `prompt_versions`. One route row is seeded: `post_mortem` on `openrouter`, `anthropic/claude-haiku-5.5`, no fallback.
- **No `learned` column** and no other column change. The `bot_id` and `user_id` on `model_calls` came from L.

**Who reads and writes what.**

| Object | Writer | Reader |
|---|---|---|
| `learning_runs` | bot: every column except the draft's end state | service: all of them |
| `learning_runs.draft_status` → `saved`, or `dismissed` with reason `user`, plus `saved_version` | service: Save as vN of a draft, dismiss | bot (supersession checks), service |
| `learning_runs.draft_status` → `dismissed (superseded)` | bot: the run's final transaction | service |
| `calibration_maps`, `post_mortem_proposals` | bot | service (`LossRow.proposal` joins `post_mortem_proposals`) |
| `bot_runs` and `bot_run_requests` with loop `learn` | bot (learning runner) takes and runs; service inserts the request | service: learning routes only; hidden from the other bot reads (R4) |
| `decisions.post_mortem` | bot: where null, `labelled_by: model`; service PUT: user or confirmed model | service Stats, export |
| `model_calls` (stage `post_mortem`), `model_spend_daily`, `prompt_versions` (`post_mortem.v1`) | bot | the bot's ceiling; the console's Spend |
| `bot_versions.config->'learning'` | service (Save as vN) | bot (`readConfigV2`), service (`learned`), web |

The DDL, the Down and the harness are on [[centralized-migrations]] (source: raw/2026-10-30-learning-loop.md §Database).

## Owner decisions from the intent (selected)

The full D1–D15 and PD1–PD8 are in `tidewatch-specs/learning-loop/intent.md` (confirmed 2026-10-27).
- **D1** Learned results live only in a draft version.
- **D2** Floors per job, over the current version's last 90 days.
- **D3** One migration with three tables. The letter was settled at build time as **M**.
- **D4** A separate `learning` runner.
- **D5** The calibrated `p` is what the bot states and what Stats grades; `p_raw` is kept.
- **D6** Thompson weights collapsed to the per-source vocabulary. Event-type weights are shown, not applied.
- **D7** The meta-model is `logistic_v1`; `gbdt_v1` can follow.
- **D8** A walk-forward protocol. The gate only vetoes or shrinks.
- **D9** Post-mortem proposals come from Haiku. Sonnet would be a data change later.
- **D10** Confirmation keeps provenance.
- **D11** The export is on demand, with no table, file or training.
- **D12 (revised)** The report lives on the run, never in the wiki (above).
- **D13** The learned-challenger gate; a learned draft always starts on probation; no automatic promotion.
- **D14** No mockup; existing patterns only (see [[design-system-decisions]]).
- **D15** Runs happen on observing bots and on empty data, and always write a report.
- **PD1–PD8** covered the route list, the optional `learning` key (absent everywhere before, so no stored hash changed), the arithmetic, the fixtures, the run record, observability, the build order and the recorded non-goals: RL, fine-tuning, automatic promotion, event-type weights, hand-corrected extractions, GDELT features and the Tiingo versus EODHD question.

(source: raw/2026-10-30-learning-loop.md §Concept, Owner decisions from the intent)

## Decisions during the build

| Id | When / by | Decision |
|---|---|---|
| Letter M | 2026-10-27, parent coordination | The migration is **M**, overriding PRD S21's "L". Siblings: accounts-roles = L, signals-context = N; the merge order is **L → M → N** |
| OQ-1 | 2026-10-28, owner | No `LEARNING_ENABLED`; `learning` is a `MARKET_DATA_COLLECTORS` member |
| OQ-2 | same | A run that proposes nothing leaves the pending draft |
| OQ-3 | same | A failed scheduled run waits until next month; *Run learning now* is the retry |
| OQ-W2 (a) | same | `LearningRun` gains `saved_label` and `saved_at` (P11). A dismissal is undated |
| OQ-W5 | same | The extraction-error export is API-only, with no on-screen control |
| OQ-W6 | same | *Load into editor* on a stale draft loads onto the current version and applies only the `moved: true` weight rows |
| OQ-S1 | same | Audit keys `learned_from_run` and `draft_modified` on draft saves |
| OQ-S2 (R12) | same | A clone of a learned source refuses `probation: false`; the web locks the clone dialog's probation control |
| Preview DB | 2026-10-28, parent | A per-run isolated, retained preview database, not the shared volume; M applied on a clean K-level database without L |
| OQ-G1 (a) | 2026-10-28T08:28Z, owner | At least **two** folds, not three. A 90-day window holds at most two 30-day folds, so with three the gate could never open |
| A3 | 2026-10-28, owner | Purge margins 7 / 14 / 39 days, not 2 / 8 / 30 (the worst case is Songkran, 38.278 days) |
| Weeks-horizon limitation | 2026-10-28, owner accepted | A mostly weeks-horizon bot cannot open the gate under these rules. A longer meta window is a follow-up spec |
| XF-1, XF-2 | 2026-10-28, orchestrator | XF-1: the web checks C15's features per item, matching the service and the bot. XF-2: the bot accepts `fitted_at` years 0000–0099 |
| Design SF-2 (a) | 2026-10-28, orchestrator | One `.status-line` per job, as the PRD says; DESIGN.md amended |
| OD-PV2-1 | 2026-10-29T01:58Z, owner | "Fix with CSS": in the unfiltered Stats labelling list at 1100 and 1080, *Confirm* and *Save* must be fully in view |
| OD-PV2-2 | same, owner | "Drop it for Failure model": the *Failure model* table has no 560px minimum. **This amends PRD §7.4** |
| OD-PV4-1 | 2026-10-29T06:35Z, owner | "Keep them separate": the seeded learning bots stay under `pv4-learning` on the preview database |
| OD-LEARN-SPEND | 2026-10-29T14:30Z, owner | "Count it fully" (above) |
| OD-MERGE-1 | 2026-10-30, owner | "Merge them for me": merge the four PRs now, in order |

(source: raw/2026-10-30-learning-loop.md §Concept, Decisions during the build)

## Spec corrections: the as-built truth over the PRD and intent

The build did not edit the spec folder, which is not a git repository. Where this list disagrees with `prd.md` or `intent.md`, this list is the truth.

- **The migration is M, `20261028120100`, and it applies on L.** Every "L" in this feature's spec reads M. The service's `RequiredSchemaVersion` moved L → M. L was the pin until M, J until L, and K was never pinned (see [[centralized-migrations]]).
- **OQ-G1:** PRD §4.5.2 step 2's "at least three folds" is **at least two**. FR-LL-E2E-002's open-gate case ran on a seeded window of 88 days.
- **A3:** PRD S10's purge margins of 2 / 8 / 30 days are **7 / 14 / 39**. The holidays in the covering test are hard-coded through 2027.
- **OQ-1:** there is no `LEARNING_ENABLED` (PRD §4.1, §8.1, intent "Constraints"). Learning is off only when an explicit `MARKET_DATA_COLLECTORS` list omits `learning`.
- **OQ-W2:** `LearningRun` ends with `saved_label` and `saved_at` (P11). PRD §4.12's "Dismissed on {date}" reads "Dismissed", with no date, because M has no dismissal timestamp.
- **OQ-S1:** `bot_version_created` gains `learned_from_run` and `draft_modified` on a draft save only. PRD §4.10.1's "The audit `bot_version_created` is unchanged" is superseded; §8.3's detail list was right.
- **OQ-S2 / R12:** a clone of a learned source refuses `probation: false`. The PRD names no clone rule.
- **OD-PV2-2 (amends PRD §7.4):** the 560px table minimum applies to *Proposed weights* and *Calibration* only. The *Failure model* table has none and fits 358px at 390 (`src/styles/components/bots.css:181-196`; see [[design-system-decisions]]).
- **OD-PV2-1:** above 600px the Stats labelling list's Decision and Signal second lines and the saved tag may wrap, so *Confirm* and *Save* are in view at 1100 and 1080.
- **OD-LEARN-SPEND, together with L:** PRD §5.3's "Not stored, by decision: … a `bot_id` on `model_calls`" is superseded; `post_mortem` rows carry `bot_id` and `user_id`. PRD S17 is widened: `BOT_COST_FOR_DAY` (scout + learn, per bot) sits beside `OWNER_COST_FOR_DAY` (scout + learn, per owner), and the labeller checks both.
- **Gate chain:** PRD §6.1 mounts the routes behind `RequireRole("admin")`. Since L every product route is behind `RequireRole("user")`, and nothing accepts `admin` (see [[auth-model]]).
- **`learn` rows are invisible to the existing bot reads** (service plan R4; the PRD is silent). `BotRepo.LastRun`, `Runs`, `RunByID` and `LatestRunRequests` filter `loop <> 'learn'`. `GET /stats` `kpis.cost_usd` still includes a learning run's labelling spend.
- **SF-C1** (a known limitation, documented, not fixed): above.
- **SF-C2:** a bad `post_mortem` route row does not stop the signals pipeline or the bot stages. Only the labeller's stage start refuses it (`assertPostMortemRoute`) and logs `learning_model_stage_failed` once (see [[signals-pipeline]]).
- **A missing provider key** refuses only the labeller's stage start, logged once. The losses wait.
- **FR-LL-BOT-003's 120-row Platt case:** PRD §4.3 item 5 does not say which sample is out of sample. The test runs the job on the oldest 120 rows and scores the stored refit on the other 1,880; 191 of 200 seeds pass. Accepted by the code reviewer.
- **The weights interval** is collapsed, scaled and clamped but not stepped, so a report can show a proposal outside its own likely range. On the preview, finnhub was proposed at 0.35 with a range of 0.05–0.17.
- **The report** prints 4-digit ECE; the PRD example shows 3.
- **LL-W-1:** the web skips the learning read for a non-v2 version and shows the legacy sentence.
- **LL-W-21 (PF1):** with a pending draft whose gate is closed, the service sends `draft.diff.meta_gate: null`, and the web draws the *Failure model* table from `latest.summary.meta_model`, so "gate closed" is readable (PRD §4.11.1).
- **The cut export stream:** after the 200 has started, a failure aborts the connection, so the client sees a cut, not a clean end. This holds over HTTP/1.1 (the main listener).
- **Q12 / D12:** the brief's report-in-the-wiki is not followed; the report lives on `learning_runs.report`.

(source: raw/2026-10-30-learning-loop.md §Concept, Spec corrections)

## API

### Conventions

- **Gates.** All six new routes mount on the gated market group `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("user") → RequirePasswordChanged`. The gated product count goes **64 → 70** (`TestRouter_ForcedChangeGatesNewRoutes`).
- **Ownership.** An id that is not a UUID, is absent, or is another user's is one `404 not_found`, never `403`. Queries and bodies are strict, and the POSTs need CSRF. The five `/bots/{bot_id}/learning…` routes run `EnsureBots`; the export does not (P10).
- **Reads.** Each learning read is one `REPEATABLE READ READ ONLY` snapshot (S15). Stored `{}` for `floors`, `summary` or `counts` is served as `null`; `draft.config` is in C10 canonical form.
- **Formats.** Decimals are strings: ECE and AUC 4 digits, weights 2, `cost_usd` 6. Instants are RFC 3339 UTC; Bangkok is a fixed UTC+07:00.
- **The service adds** no environment variable, Redis key, `/ws` frame or model call.

(source: raw/2026-10-30-learning-loop.md §API, Conventions)

### Routes

| Method and path | Request | 2xx | Refusals |
|---|---|---|---|
| `POST /bots/{bot_id}/run` (changed) | `{loop: scout\|manager\|guard\|learn}` | `202 {request_id, requested_at}` | as before; `learn` on a version that is not v2 is `400 {field: loop, reason: invalid}`, "Learning needs a v2 version. Upgrade the bot first."; 6 per hour per bot and loop |
| `GET /bots/{bot_id}/learning` | — | `200 {generated_at, next_run, request, latest, draft}` | `400` (any parameter), `404` |
| `GET /bots/{bot_id}/learning/runs` | `limit` 1–100 (20), `cursor` (kind `E`) | `200 {items: [LearningRun], next_cursor}`, newest first | `400`, `404` |
| `GET /bots/{bot_id}/learning/runs/{learning_run_id}` | — | `200 LearningRun` | `400`, `404` |
| `GET /bots/{bot_id}/learning/runs/{learning_run_id}/report` | — | `200 text/markdown`, attachment `learning-{bot-slug}-{YYYY-MM}.md` | `400`, `404` (also for a run without a report) |
| `POST /bots/{bot_id}/learning/draft/dismiss` | no body | `200 {learning_run_id, draft_status: "dismissed"}` | `400 manual_bot`, `404`, `409 draft_not_pending` |
| `POST /bots/{bot_id}/versions` (changed) | `{config, probation?, learning_run_id?}` | `201 {version, bot}` | as before, plus P2's order (see [[bot-versions-and-runs]]) |
| `POST /bots/{bot_id}/clone` (changed) | as before | as before | a learned source with `probation: false` is `400 {probation, invalid}` (R12) |
| `GET /learning/extraction-errors` | `bot_id?`, `from?`, `to?` (Bangkok dates, at most 366 days) | `200 application/x-ndjson`, attachment `extraction-errors-{YYYYMMDD}.jsonl` | `400`, `404` (a foreign `bot_id`) |
| `GET /stats/losses` (changed) | `+ proposed=1` | `LossRow` ends with `proposal` | see [[stats-read-api]] |
| `PUT /decisions/{decision_id}/post-mortem` (changed) | as slice 7 | `labelled_by` per the provenance rule | as slice 7 |
| `GET /stats/compare`, `POST /bots/{bot_id}/promote` (changed) | as slice 7 | `not_comparable` for a learned challenger | `calibration_not_comparable` |
| `GET /bots`, `GET /bots/{bot_id}`, `GET /stats`, `GET /bots/{bot_id}/versions[/{seq}]` (changed) | as before | `learned` as the last key of `strategy`, of the stats and compare `version`, of each versions item and of the version detail (P7) | as before |

(source: raw/2026-10-30-learning-loop.md §API, Routes)

### The status body and `LearningRun`

- **`next_run`** is the first `YYYY-MM-01T03:00:00+07:00` after the later of the newest learning run and the current version (P3). It is `null` for the manual bot, a paused bot and a version that is not v2. A due bot's `next_run` can show a past slot for up to one pass (≤ 60 s), which is cosmetic.
- **The manual bot** gets `200` with only `generated_at` set.
- **`request`** is the newest `learn` request, `stale` after 10 minutes.
- **`draft`** is the pending draft or `null`, with `config` and a `diff` of `weights` (`source_code, current, proposed, lo, hi, n, moved`), `calibration` (`horizon, method, n_fit, n_test, ece_raw_oos, ece_map_oos`) and `meta_gate` (`auc_oos, gate, folds, importances`). `diff.meta_gate` is `null` when the draft proposes no gate, even if the run fitted a closed one (LL-W-21). `draft.proposed_at` is the run's `finished_at` (P4).
- **`LearningRun`** always has every key (undefined is `null`): ids, `trigger`, times, `status`, `error`, `version {seq, hash, label, learned}`, `window {from, to, days}`, `seed`, `floors` (per job `needed`, `have`, `met`; post-mortems `candidates`), `summary` (calibration, weights, meta_model, post_mortems, `draft.changes`), `counts` (`graded_proposals, graded_entries, losses, maps_proposed, arms_moved, auc_oos, labels_proposed, cost_usd`), `has_report`, the draft state, and `saved_label`/`saved_at`. The runs list omits `summary.weights.arms` and `summary.meta_model.folds`.

(source: raw/2026-10-30-learning-loop.md §API, The status body, Fields of the status body and `LearningRun`)

### The extraction-error export (D11)

- **Rows:** the user's `actor bot` `buy | add` decisions with a **confirmed** `signal_wrong` label. `signals` and `documents` are inner joins, and the newest extraction of the document is taken.
- **Each line**, keys in order: `decision_id, bot_id, version_label, ts, instrument_id, direction, document {…, body, body_truncated}, extraction {…}, signal {…}, outcome {horizon_column, r, hit, exit_reason}, post_mortem {label, labelled_by, labelled_at}, correction {direction_realised}`.
- **Bodies:** `body` only for `body_status = 'full'`, cut at 65,536 bytes on a UTF-8 boundary with `body_truncated: true`.
- **Order and empty results:** `decisions.ts, decision_id`; an empty result is an empty `200`.
- **Deadline and failures.** One 60 s deadline covers the snapshot and the stream. A writer that cannot take the write deadline is refused with `500` before any byte. A failure after the 200 has started logs `extraction_export_failed` and aborts the connection.

(source: raw/2026-10-30-learning-loop.md §API, The export line and Which rows are exported)

### Codes, audit, metrics and logs

- **Service codes.** `draft_not_pending` (409) is in `AllCodes()`. New `invalid_request` reasons: `draft_mismatch`, and `invalid` on `learning_run_id` and `probation`. New `promotion_refused` reason: `calibration_not_comparable`.
- **Audit.** `learning_draft_dismissed {bot_id, learning_run_id}`, the 35th type (see [[operator-console]]). `bot_version_created` gains `learned_from_run` and `draft_modified` on a draft save only. `post_mortem_labelled` always carries `confirmed_proposal`. `bot_run_requested` carries `{loop: learn}`.
- **Service metrics.** `learning_drafts_total{outcome: saved|dismissed}` and `bot_run_requests_total{loop="learn"}`, both at 0 from start.
- **Cursors.** Learning runs use kind `E` (0x45) over `(started_at, learning_run_id)`, bound to the bot; filtered losses use kind `M` (0x4D). Each is refused on every other list.
- **Bot metrics** (all at 0, closed label sets): `learning_runs_total{result: proposed|noop|floor|failed}`, `learning_proposals_total{kind}`, `learning_model_calls_total{stage: post_mortem}`, `learning_model_cost_usd_today`, `learning_pass_duration_seconds`, and `bots_run_requests_total{loop}` gains `learn`.
- **Bot logs:** exactly ten events, closed by a source scan: `learning_run_started`, `learning_run_finished`, `learning_floor_not_met`, `learning_draft_proposed`, `learning_draft_superseded`, `learning_label_proposed`, `learning_model_stage_failed` (with a closed `problem` field for a `post_mortem` `RouteConfigError`), `learning_budget_reached` (`budget` `bot`, `user` with `user_id`, or `ceiling`), `learning_run_interrupted` and `learning_lock_busy`.
- **No text in logs.** Service and bot logs carry ids, enums, counts and `error_class` only, never a rationale, report line, thesis, document body, config or key (`TestLogs_NoBotTextOrConfig`, the bot's sentinel scan).

(source: raw/2026-10-30-learning-loop.md §API, Codes, audit, metrics and logs; Bot side)

### The `learning` block in the v2 config (PRD §5.2, C15)

- **Shape.** `learning {learning_run_id, fitted_at, fitted_from, calibration {maps: [{horizon, method, points, params}]}, meta_gate {family: "logistic_v1", features, means, scales, coef, intercept, auc_oos, veto_above, shrink_above, shrink_factor}}`.
- **Presence.** One optional top-level key, absent on every earlier version, so no stored hash changed. When present every key is required and unknown keys are refused.
- **Refusal order** (dotted `details.field`): 1–3 maps in horizon order; isotonic maps of 2–64 points with `p` strictly increasing and `y` non-decreasing at 4 digits; Platt `a > 0`; `family` exactly `logistic_v1`; `features` a subset of the closed list in order, checked per item (XF-1); `means`, `scales` and `coef` of equal length with `scales > 0`; `shrink_above ≤ veto_above`; `shrink_factor` in (0, 1).
- **Fixtures.** `bot-version.v2-learned.json` (C15, sha256 `977068bf…`) is byte-identical in the bot, the service and the web, each copy pinned by its hash with 10 accepted and 59 refusal cases. C12 `bot-version.v2.json` (`44161eb0…`) is unchanged. C14 `attribution-net.v1.json` (`a42edbfc…`) pins the net-return rule in the bot and the service (A7).

(source: raw/2026-10-30-learning-loop.md §API, The `learning` block in the v2 config)

## What the user sees

All in `tidewatch-web`, with existing tokens and patterns only (D14, no mockup). Component and style detail is on [[design-system-decisions]].
- **The *Learning* section** on an auto bot's detail, between Candidates and Version. Its run row reads "Next run {EEE d MMM HH:mm}", "no schedule (paused)" or "needs a v2 version", with the last run's trigger and result ("draft proposed", "nothing to propose", "floors not met", "failed ({error})", "never run"). *Run learning now* shows *Queued…*, a stale sentence, and the toast "Learning ran at {HH:mm}: {result}".
- **Floors**, one status line per job, then the draft: a "Draft from {d MMM}" tag and three tables, *Proposed weights*, *Calibration* and *Failure model*, with *Load into editor*, *Dismiss draft* and *Download report*. A saved draft reads "Saved as v{label} on {date}"; a dismissed one "Dismissed". A legacy bot reads "Learning needs the current vocabulary. Upgrade this bot to enable it.", with no button.
- ***Load into editor*** applies the weights, attaches the locked learned block, checks and locks probation, and notes "Loaded from the learning run of {d MMM}. Review, then save as v{seq+1}; it starts on probation." *Remove the learned block* unlocks probation. The clone dialog locks probation for a learned source.
- **Stats:** a *Proposed only* filter, "Model: {rationale}" on proposal rows, *Confirm* while the select equals the proposal, the counts line "Labels: you {user} · model, confirmed by you {model} · proposed, waiting for you {proposed}", the not-comparable verdict line, and "· learned version" in the sub line (see [[statistics]]).
- **Elsewhere:** the Watch and Checks word `meta_veto` as "vetoed by the failure model"; the decision record's second line gains "size halved by the failure model"; a learned strategy sentence gains "· learned".

(source: raw/2026-10-30-learning-loop.md §Components)

## What each project gained

| Project | Gained |
|---|---|
| `tidewatch-migrations` | Migration M and its harness (M and L round trips with L between K and M; 4,153 PASS, 0 FAIL) (see [[centralized-migrations]]) |
| `tidewatch-bot` | `packages/bots/src/learning/` (runner, schedule, calibrate, weights, meta, meta-gate, labels, draft, report, summary, the pg store, metrics), the scout's calibrated `p` and the manager's meta gate, `post_mortem.ts` and `prompts/post-mortem.v1.ts` in `packages/signals`, the C14 and C15 fixtures, `BOT_COST_FOR_DAY` and `OWNER_COST_FOR_DAY` (see [[bots-engine]]) |
| `tidewatch-service` | Six routes (64 → 70), Save as vN of a draft, forced probation, the dismiss, the PUT provenance rule, the learned-challenger gate, the export, `learned` on the bot, version, Stats and compare bodies (P7), `draft_not_pending`, the pin M (see [[bot-versions-and-runs]] and [[stats-read-api]]) |
| `tidewatch-web` | `bot-learning.ts` and `learning-view.ts`, the editor's learned block, the clone lock, the Stats proposal flow, the words for `meta_veto` and a halved size, `learning_draft_dismissed` as the 35th admin audit type, `.learning-tables` and `.learning-actions` (see [[design-system-decisions]]) |

(source: raw/2026-10-30-learning-loop.md §Files touched)

## Branch update onto L (2026-10-29)

L (accounts and roles) merged to `main` on 2026-10-29, and all four learning-loop PRs then conflicted.
- **Method.** Merge `origin/main` into each branch (merge commits, no force-push), resolve, re-run the checks and push.
- **Migrations** `49f06b9` + `d28de68`: `make migrate-validate` exit 0 (15 files), `make check-disposable-db` PASS (4,153 PASS, 0 FAIL). J's down-to-I round trip is reported "not run", because with L between it would run L's destructive Down. M's header still says it applies on K with J as the pin; it was left unedited because the file is reviewed and its SHA recorded.
- **Bot**: nx exit 0 (bots 527 tests); sql-integration PASS on L+M.
- **Service**: `go test ./... -race` 790 PASS in 41 packages, `make ci` exit 0, integration on L+M ok. The learning handler tests sign in as role `user`, and a learned save still gets the plan tier check (`c29d0f0`).
- **Web**: the admin `AUDIT_TYPES` list is closed (34), so `learning_draft_dismissed` was added as the 35th (`f2ee96c`). Unit tests 6,994 pass.
- **Review.** The code-reviewer approved every conflict resolution and raised one finding, which the owner ruled as OD-LEARN-SPEND (above). The fix (`1c3317b`…`435feb4`) was reviewed APPROVED; final bots 536 unit tests, sql-integration PASS (bots int 61).
- **Web again, 2026-10-30T17:41Z.** The web was three commits behind `main` (favicon #24 and the app-dialog reopen-race fix #25). It merged `main` as `568002f`: lint, 6,995 unit tests and build green, e2e tsc clean. **Playwright was not re-run on `568002f`.**

(source: raw/2026-10-30-learning-loop.md §Concept, Branch update onto L)

## Rollout to production (2026-10-30)

| When (UTC) | Event |
|---|---|
| recorded 18:45:41 | OD-MERGE-1. All four PRs were MERGEABLE, CLEAN and validated |
| ″ | Migrations #14 merged → `8feeae3`; deploy-prod ok. GitOps `c376f6e` bumped `migrate.image` only. **No ArgoCD sync followed**, because the migrate Job is a hook of the `tidewatch-service` chart and hooks are not diffed |
| ″ | Service #16 merged → `3f8627a`. ArgoCD synced the service's GitOps commit `166610b`, and the migrate Job (Sync hook, wave −1) **applied M** in that sync. `/info` reported `3f8627a`, and `/ready` answered 200 with the schema ok |
| ″ | Bot #17 merged → `2a3a412`. Rollout ok and `/ready` ok; the `learning` collector started, with a first learning pass |
| 18:45:09 (re-auth) | During the bot rollout the production bot's Alpaca stream looped on 406. The local preview bot held the same Alpaca key and had taken Alpaca's single stream connection. Production re-authenticated after the preview container was stopped |
| ″ | Web #21 merged → `de00a5f`. Rollout ok; the live bundle serves the learning routes. An unauthenticated `GET /bots/{id}/learning/runs` answers 401 |

**Why this order.** The build prompt allowed bot and service in either order, both before the web. The rollout went migrations → **service** → bot → web:
- **M had to be applied before the bot rolled.** A migrate-image-only bump does not apply M; only the service sync does. The bot has no schema-version check, so a bot rolled before M would have failed its learning queries against an L-only database, the same class as accounts-roles' 42P01 window.
- **The web went straight after the service.** The admin audit list is closed, so a `learning_draft_dismissed` event shown to an older web would fail its strict reader.

**Lesson recorded, confirmed a second time (GitOps and hooks).** A migrations-only GitOps bump does not trigger an ArgoCD sync. A rollout needs a service image bump in the same rollout, or a manual sync, and the service must sync before any consumer that needs the new schema rolls (see [[centralized-migrations]]).

**Lesson recorded (one Alpaca stream per key).** Alpaca allows a single stream connection per key. A preview or local bot that holds the production Alpaca key takes the stream from production whenever production restarts, and production then loops on 406. Stop preview bots, or give them another key, before a production bot rollout (see [[market-data-worker]] and [[forge-preview-gateway]]).

(source: raw/2026-10-30-learning-loop.md §Concept, Rollout to production; Lesson recorded (GitOps and hooks); Lesson recorded (one Alpaca stream per key))

## Review history (abridged)

- **Plans.** Bot r1 CHANGES REQUESTED (4 blocking, among them the missing learn filters on `INTERRUPT_RUNS` and `RELEASE_RUN_REQUESTS`), r2 APPROVED, r3 APPROVED after OQ-G1. Service r1 CHANGES REQUESTED (2 blocking), r2 and r3 APPROVED. Web r1 CHANGES REQUESTED (3 blocking), then r2–r4 APPROVED.
- **Code round 1** (eight reviewers, 2026-10-28). Web security N1: bidi characters in the model rationale. Service: a mid-stream export failure looked complete. Bot security SF-1: a paid `post_mortem` call was lost from the ledger when the proposal write failed; SF-2: the log scan lacked rationale, report, name and config keys. Bot code SF-C1 (document that a draft drops gate and maps) and SF-C2 (a bad `post_mortem` route row stopped the whole signals pipeline). Web design CHANGES REQUESTED (SF-1…SF-6, no rendered evidence).
- **Round 2, all APPROVED.** `labels.ts` records and charges the lost call before release; the export cut aborts the connection and the deadline fails closed; SF-C1 by documentation, SF-C2 in code (the bad row is kept with its problem, `assertRoutePrices` prices J's five only, the labeller asserts its route); `<bdi>` around the rationale.
- **Polish** (code-reviewer over three deltas): APPROVED with S-1, the bot's `problem` field mislabelling J-stage refusals, fixed and confirmed.
- **Preview design.** PV2 CHANGES REQUESTED (SF-PV2-1 *Confirm* and *Save* out of view at 1100; SF-PV2-2 the *Failure model* 560px minimum at 390; SF-PV2-3 the DESIGN.md refresh), resolved by PF1 with OD-PV2-1 and OD-PV2-2. PV2 round 2 **APPROVED** (0 blocking, 0 should-fix, 2 nits).
- **Branch update.** Every conflict resolution approved; finding 1 resolved by OD-LEARN-SPEND, reviewed APPROVED.

(source: raw/2026-10-30-learning-loop.md §Concept, Review history)

## Test plan and acceptance

**Acceptance status: 43 IDs; 40 verified, 2 partial, 1 unverified, 0 failed.**

| Area | Result |
|---|---|
| FR-LL-MIG-001…003 | verified (harness; M as PRD §5.1; probes by constraint name; the loud-failure Down) |
| FR-LL-BOT-001…013 | verified. BOT-003 carries the recorded 120-row reading; BOT-006 is verified against the corrected spec (two folds, 7/14/39) |
| FR-LL-SVC-001…011 | verified (integration on the post-polish tree 897 PASS, 0 FAIL, 0 SKIP; after the branch update `make ci` and integration on L+M green) |
| FR-LL-WEB-001…006, 008 | verified (Vitest, Playwright on the preview, captures, axe, contrast, keyboard) |
| FR-LL-WEB-007 | **partial**: no capture of the Checks' `meta_veto` words or of a shrunk entry's second line. The not-comparable line, the aria-disabled Promote, "· learned version", "· learned", the real refusal wording (E2E-004) and the Watch's "vetoed by the failure model" (E2E-002) are verified |
| FR-LL-E2E-001, 002, 004, 005, 006 | verified on the preview |
| FR-LL-E2E-003 | **partial**: the model half is unverified, because the preview's OpenRouter key was refused on every call; the downstream half is verified on three SQL-seeded proposals |
| FR-LL-DOC-001 | verified |
| FR-LL-DOC-002 | **unverified, recorded deferral**: `tidewatch-apis` is not a git repository, so the collection was not regenerated (as in slices 6 and 7). The service README documents the shapes |

**Brief acceptance.** BA-1 (≥ 50 % ECE cut): verified on synthetic data (0.1371 → 0.0444) and on the preview (0.1465 → 0.0292). BA-2 (no future bar; AUC per fold): 0.5000 on the leakage set with the guards and 0.9574 without. BA-3 (weights always a draft; diff plus Save as vN) and BA-5 (the export holds only confirmed labels) and BA-6 (the API refuses an unproven learned challenger): verified. BA-4 (labels counted only once confirmed): verified for the counting and the list; a model-written proposal was not.

**Assumptions (PRD §11).** A1 holds (`model_calls.document_id` is nullable). A2 holds (the five constraint names). A3 **failed as written**, corrected to 7/14/39. A4 holds (Newton converged in 6–7 iterations). A5 verified (the real `a[download]` saved the service-named file byte-identical). A6 **partial** (the mocked schema-failure case only; 0 real Haiku replies). A7 verified (C14 agrees). A8 **unverified** (no ten-bot pass was timed). A9 verified.

(source: raw/2026-10-30-learning-loop.md §Test plan, Results)

### Preview runs (per-run isolated database `forge-0199b29a-ll-f3bdc8b0`)

- **PV1** (web `b84fd55` at M): 1,706 passed, 4 failed (two e2e defects fixed in `3cb3fb4`), 4 skipped; 210 slice-8 captures, no overflow, axe 0 over 40 runs, contrast ≥ 4.79:1. PV1b: `bots-learning.spec.ts` 198/198.
- **PV4** (seeded E2E-001…006, user `pv4-learning`): 5 passed; E2E-003's model half unverified. It found the closed-gate draft display defect, fixed in PF1.
- **PV2 → PF1 → PV2 round 2, PV3, PV5** (`13d1267`): APPROVED; keyboard, axe and contrast verified (slice-8 minimum 4.85); `forge-setup-impeccable --check` 173/173. PV1c had two intermittents, one a test race fixed by waiting for Promote, one a toast-timing follow-up (F-PV1-4).
- **PV6** (whole suite on the final heads, L applied out of order with `goose -allow-missing`): 2,260 passed, 3 failed, 4 skipped in 37.5 min. Two failures were slice-6 toast captures under load that passed 6/6 alone; the third was the pre-existing `app-dialog` race later fixed by web #25. On the real stack, `pv4-learning` (role `user` after L) read the learning status and runs, dismissed a draft (200, then 409), and one `learning_draft_dismissed` event showed on `/admin/audit`. The learning runner made 4 passes with no failure, and `OWNER_COST_FOR_DAY` read the expected scout + learn sum.

**What each seeded E2E showed (PV4, 2026-10-28).**
- **E2E-001.** PV4 Calib (tier `jev`, 2,000 graded over-confident proposals): *Run learning now* on screen gave a manual run whose days isotonic map cut the out-of-sample ECE 0.1465 → 0.0292; Platt reached 0.0431 and was not chosen. *Load into editor* → *Save as v3* gave v3·1a2c, learned and observing on probation, its `learning` equal to the draft's byte for byte. The next scout wake on a real BTCTHB setup wrote `model.p 0.597`, `p_raw 0.730` and `candidates.p 0.597`.
- **E2E-002.** Weights stayed within [0.05, 1.00] and ±0.25. The gate opened on two separable sets (AUC 0.8624, 0.8396) and stayed closed on the noise set (0.5481), each with two folds in an 88-day window. An entry recorded `policy_result.meta {effect none, p_loss 0.0232}`; the high-`p_loss` candidate was `gated ["meta_veto"]` with no decision, and the Watch read "Gated · vetoed by the failure model".
- **E2E-003.** 12 candidate losses produced 12 `post_mortem` calls, all refused by OpenRouter (4xx other than 429, 0 tokens, $0); the same route had failed every extraction on that preview. Downstream, on 3 SQL-seeded proposals, *Proposed only* showed the rationale, *Confirm* stored `{labelled_by: model, confirmed_by_user: true}` and moved the counts, and a second PUT got `409 post_mortem_frozen`.
- **E2E-004.** With 10 graded proposals, promote answered `409 promotion_refused [return_not_higher, calibration_not_comparable, not_active]`; with 35 graded it was judged on ECE (`calibration_worse`). `bots.champion` was unchanged.
- **E2E-005.** The export had 4 lines, equal to the SQL count of confirmed `signal_wrong` entries with a joinable signal, in the documented key order.
- **E2E-006.** PV4 Scheduled (observing) got a `scheduled` run: calibration floor met (300/150), weights and meta not met; the days map (0.0585 → 0.0548) was not proposed, so no draft. *Download report* saved `learning-pv4-scheduled-2026-10.md`, byte-identical to `learning_runs.report`.
- **Paid calls.** Jev `bot_decide` 1 call, $0.000029; OpenRouter 13 refused calls, $0.

(source: raw/2026-10-30-learning-loop.md §Test plan, Preview runs; What each seeded E2E showed)

### Not verified or partial

- **A model-proposed post-mortem**, in any environment (E2E-003 model half, A6).
- **FR-LL-WEB-007:** no capture of the Checks' `meta_veto` words or a shrunk entry's second line.
- **A8:** no ten-bot pass was timed.
- **FR-LL-DOC-002:** deferred.
- **The realised calibration line on real data.** It needs a learned version to run for a month; proven only on seeded data.
- **Playwright on the merged web head `568002f`:** not re-run.
- **PV3 gaps:** touch and real devices, screen readers, Safari and Firefox, widths 601–1079, *Confirm* by keyboard, and the "Remove → heading when unchanged" branch.
- **Production after deploy** is verified only by `/info`, `/ready`, the bot's ready state and learning collector log, the live bundle and the unauthenticated 401. No learning run has been requested in production, and no scheduled run has happened yet.
- **M's Down** ran only in the disposable harness.

(source: raw/2026-10-30-learning-loop.md §Test plan, Not verified or partial)

## Manual reproduction (production)

1. Sign in at `https://tidewatchtrade.com/sign-in` and open a v2 auto bot's detail. A legacy v1 bot (Slack Water) shows the legacy sentence and no button.
2. Expect the *Learning* section between Candidates and Version, with "Next run Sun 1 Nov, 03:00" (or the bot's next slot) and *Run learning now*.
3. Press *Run learning now*. Expect *Queued…*, then within about one pass (60 s) the toast "Learning ran at {HH:mm}: {result}". On today's thin data the result is likely "floors not met" or "nothing to propose".
4. *Download report* should save `learning-{bot-slug}-{YYYY-MM}.md`.
5. On the bot's metrics, watch `learning_runs_total{result}`, `learning_pass_duration_seconds` and, if the bot has closed losses, `learning_model_calls_total{stage="post_mortem"}` and `learning_model_cost_usd_today`.
6. A `learning_model_stage_failed` with `error_class DecideRejectedError` means OpenRouter refused the call (see "Open items").
7. After 2026-11-01 03:00 Bangkok, expect one `scheduled` run per eligible bot.

(source: raw/2026-10-30-learning-loop.md §Test plan, Manual reproduction (production))

## Open items

**Owner actions still open.**
- **Check the OpenRouter key.** Production labelling uses the `post_mortem` route on OpenRouter Haiku, as does production `bot_thesis`. The preview's OpenRouter key was refused on every call (extraction, `post_mortem`, `bot_thesis`). If production shares that key, labelling will not run there: each attempted loss logs `learning_model_stage_failed`, is charged $0 and waits for the next run. After the key is checked, re-run one learning run on a bot with closed unlabelled losses to close FR-LL-E2E-003's model half and A6.
- **Watch the first scheduled production run,** due 2026-11-01 03:00 Bangkok. PRD §8.4 expects Driftline, observing on probation, to report floors and at most a calibration map.
- **Preview leftovers** (see [[forge-preview-gateway]]): the retained per-run volume holds user `pv4-learning` and its 11 bots, about 3,440 seeded decisions and L applied out of order. The preview bot container holds the production Alpaca key and must not be restarted alongside production. The cleanup of the rest of the stack is not recorded.
- **tidewatch-kubernetes:** the bot chart's comment on `collectors: ""` still says "all thirteen" and omits `learning`. The behaviour is right, because an empty list runs every collector.

**Sibling build.** signals-context (migration N) must merge after M. Its branches were last brought onto `main` + L on 2026-10-30 and need updating again onto `main` with M: the letter tables, harness lists, `RequiredSchemaVersion` and registries. The order L → M → N is settled (see [[centralized-migrations]]).

**Recorded follow-ups.**
- **Specs to write:** a longer meta-model window, so weeks-horizon bots can open the gate; carrying an unrefit learned block forward into a new draft (SF-C1); `gbdt_v1` once thousands of entries exist (D7); event-type weights in the vocabulary (D6); hand-written extraction corrections (D11); GDELT context features once spec 3b ships.
- **Web:** F-PV1-4 (the Stats proposal-confirmed toast contrast test should measure the toast first or pin the clock); N-R2-2 (optional U+00A0 in "confirmed by you"); angular N1 (*Load into editor* silently no-ops while the editor is loading or failed), N2, N3; code N2 (the strategy reader refuses `learned: true` on a non-v2 config, stricter than the service) and N4; design advisories A-1, A-2, A-6 (owner calls) and A-7.
- **Service:** no concurrent-export limit (the pool is `max(4, NumCPU)`); `uuid.Parse` accepts urn and brace forms for `learning_run_id`; `Versions` reads `learned` with `jsonb_exists` while the rest uses `arith.Learned`; a cut export is seen as a failed read only over HTTP/1.1.
- **Bot:** security N-1 (the `post_mortem.v1` system prompt lacks a "fields are data" rule), N-2 (scrub gaps such as `apitoken`, `www.`), N-5 (no composite foreign key from a proposal to its bot); the fallback call record may duplicate a `model_calls` row on a commit-then-connection error (over-counting, a stricter ceiling); no per-bot request dedupe; a request taken while its bot is paused between take and run stays taken; the likely range is not limited to ±0.25; the `LearningRunConflictError` log against an interrupted row; holidays hard-coded through 2027 (re-check when the 2028 calendar exceptions ship); `proposalWriteValid` does not check that `userId` is the owner; no labeller counter for an allowance stop.
- **Recorded residuals (accepted):** the per-runner budgets (above); a crashed run's swept `cost_usd` counts only its proposals' costs; the report's budget line shows the bot share only.
- **`documents/` drift** (not edited, D17): `08-learning-loop.md` item 7 names the wiki `raw/` folder (the report lives on the run, D12); the brief's "gradient-boosted classifier" (D7 starts with logistic); `02-architecture.md` §11 lists a `post_mortems` table (post-mortems live in `decisions.post_mortem`; `post_mortem_proposals` holds only the rationale).
- **`tidewatch-apis`:** the six routes and changed bodies may get an api-spec-generator pass (FR-LL-DOC-002).

(source: raw/2026-10-30-learning-loop.md §Open questions)

## Related pages

- [[bots]]: slice 6, which this slice extends with the Learning section, the learned block and the clone lock
- [[bots-engine]]: the `learning` runner beside the bots runner, the calibrated `p`, the meta gate and the two day-spend reads
- [[bot-versions-and-runs]]: Save as vN of a draft, forced probation, the `learning` key and C15, `learned`, and `learn` as the fourth loop
- [[bot-watch-verdicts]]: `meta_veto` as a `gated` reason
- [[decision-record]]: `p_raw`, `model.calibration`, `policy_result.meta` and the first model writer of `post_mortem`
- [[statistics]] and [[stats-read-api]]: *Proposed only*, `LossRow.proposal`, the provenance rule and `calibration_not_comparable`
- [[model-routes-and-spend]]: the `post_mortem` stage and route, attribution and OD-LEARN-SPEND
- [[signals-pipeline]]: the optional `post_mortem` route in the signals readers (SF-C2)
- [[centralized-migrations]]: migration M, the pin L → M and the L → M → N order
- [[accounts-and-roles]] and [[operator-console]]: role `user` on the learning routes, the 35th audit type and labelling spend on Spend
- [[auth-model]]: the 70 gated product routes
- [[market-data-worker]]: the fourteenth collector and the one-Alpaca-stream-per-key lesson
- [[design-system-decisions]]: `.learning-tables`, `.learning-actions`, OD-PV2-1, OD-PV2-2 and the LL-W decisions
- [[forge-preview-gateway]]: the per-run preview database, L applied out of order, and the preview bot on the production Alpaca key
