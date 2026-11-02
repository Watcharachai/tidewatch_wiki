# Learning loop, slice 8 (`learning-loop`): recalibration, source weights, the failure meta-model, model-proposed post-mortems, the extraction-error export and the learned-challenger gate

> Before this feature nothing fed a bot's graded decisions back into the bot. Stats plotted a bot's stated `p` against reality but never corrected it. Source weights were set by hand or by a one-off fit. No model predicted which signals fail. A losing trade got a reason only when the owner typed one. A challenger was judged by the slice-7 promotion check, which *skips* `calibration_no_worse` when a side has fewer than 30 graded proposals. Slice 8 added a monthly learning loop that proposes changes and never applies them:
> - **A `learning` runner in the bot.** It is the fourteenth collector and holds `runner:learning`. Each eligible auto bot (v2 version, `running` or `observing`) gets one learning run on the 1st of the month at 03:00 Bangkok, or when the owner presses *Run learning now*. A run reads the bot's current version over the last 90 days and runs four jobs:
>   - **recalibration**: isotonic or Platt per horizon, proposed only when it cuts the out-of-sample ECE by at least 20 %;
>   - **source weights**: seeded Thompson posteriors over source × event type, collapsed to per-source weights, at most ±0.25 a run;
>   - **a failure meta-model**: walk-forward L2 logistic regression with purge and embargo; its gate opens above a mean out-of-sample AUC of 0.58 over at least two folds;
>   - **post-mortem labels**: one proposal per closed losing entry from the new `post_mortem` model stage (Haiku through OpenRouter).
> - **Nothing changes a running bot.** A run that proposes something writes a *draft*: the current v2 config with new `source_weights` and a `learning` block holding the maps and the gate. The owner loads the draft into the editor and saves it as vN. A learned version always starts on probation.
> - **A learned version in the engine.** The scout states the calibrated `p` and keeps `p_raw`. The manager's meta gate can veto an entry (a `gated` watch verdict `meta_veto`) or halve its size. It can never increase size.
> - **Post-mortems.** Stats counts a model proposal under *proposed* until the owner confirms it. A confirmed proposal keeps `labelled_by: "model"`.
> - **Export.** An API-only JSONL export lists the confirmed `signal_wrong` losses. Nothing is trained on it.
> - **Promotion.** Promote refuses a learned challenger whose calibration test would be skipped, with the reason `calibration_not_comparable`.
> - **The report.** Each run renders a markdown report. It is stored on `learning_runs.report` and served by the API. The loop never writes `tidewatch-wiki` (intent D12, the Q12 ruling).
>
> **Status (2026-10-30).**
> - **Merged** by Claude on the owner's explicit instruction (OD-MERGE-1, "Merge them for me"), in the order migrations → service → bot → web:
>   - tidewatch-migrations #14 → `8feeae3` (head `d28de68`);
>   - tidewatch-service #16 → `3f8627a` (head `48f179d`);
>   - tidewatch-bot #17 → `2a3a412` (head `435feb4`);
>   - tidewatch-web #21 → `de00a5f` (head `568002f`).
> - **Deployed to production.** M was applied by the service's ArgoCD sync, through the migrate Sync hook at wave −1.
>   - `/info` reports commit `3f8627a`, and `/ready` answers 200 with the schema ok.
>   - The bot is ready, with the `learning` collector started and a first learning pass done.
>   - The web bundle serves the learning routes.
>   - An unauthenticated `GET /bots/{id}/learning/runs` answers 401.
> - **Verified.** 43 PRD acceptance IDs: 40 verified, 2 partial (FR-LL-WEB-007, FR-LL-E2E-003), 1 unverified (FR-LL-DOC-002, a recorded deferral), 0 failed. Assumption A8 (the ten-bot timing) was not timed.
> - **Not observed yet.**
>   - No scheduled production run has happened. The first is due on 2026-11-01 at 03:00 Bangkok (PRD §8.4).
>   - A model-written post-mortem proposal has never been produced in any environment: the preview's OpenRouter key was refused on every call.

**Sources (inputs to this document).**
- **Spec.** In `/Users/maichinu/tidewatch/tidewatch-specs/learning-loop/`:
  - `build-prompt.md`;
  - `intent.md` (O1–O7, D1–D15 with D12 revised, PD1–PD8; confirmed 2026-10-27);
  - `prd.md` (S1–S21, §4–§11, `FR-LL-*`; the requirement source).
  - There is no mockup (D14). The fingerprints matched at build start (2026-10-27T17:30:06Z): intent `40527760…6ff6fe`, prd `fbc12b9a…981908`.
- **Build record.** In `/Users/maichinu/tidewatch/.forge/features/learning-loop/`:
  - `state.json`: `perProject` (steps, PR heads, merge commits), `ownerAnswers`, `ownerDecisions`, `branchUpdate` (with OD-LEARN-SPEND), `runtime.preview`, `review`, `deploy`, `docRepositories` and `log`;
  - `verification.md`: every `FR-LL-*` ID with its result and evidence, plus "Rollout and recovery";
  - `planning/coordination.md`: the migration letter M and the L → M → N order;
  - `planning/owner-answers.md`;
  - `planning/spec-corrections.md`: OQ-G1, A3 and the weeks-horizon limitation;
  - `planning/tidewatch-bot/contracts.md` r1 (sha256 `687cbb45…3986`), the cross-plan contract for C14, C15, the summary shape and the §6.2 bodies;
  - `evidence/preview/results.md` and `seeded.md` (PV4);
  - `evidence/tidewatch-web/PV1-findings.md`;
  - `review/` (round 1, round 2, polish, and `tidewatch-web/design-pv2-r2.md`, the final design verdict).
- **Plans.** Each is the `.plans/learning-loop.md` of its worktree under `/Users/maichinu/tidewatch/.forge/docker/runs/ll-f3bdc8b0/worktrees/`:
  - bot `6945fd5d6c`: Steps 1–14, recorded in `state.json` as MIG1, MIG2, MIG3, S1–S9, SM1 (S10 and S11) and FIX-G1. The migration steps live in the bot plan; their files are in the migrations worktree `b7ddc75378`.
  - service `329891b601`: SVC1–SVC11;
  - web `5eb4e5c7ea`: S1–S11.
- **Merged code, read in those worktrees at the PR heads:**
  - `migrations/20261028120100_learning_loop.sql` and the migrations `CLAUDE.md`;
  - the bot `CLAUDE.md` ("Architecture patterns — learning runner"), `README.md:736-754`, `packages/bots/src/learning/meta.ts`, `pg-store.ts`, `learning/labels.ts` and `packages/shared/src/config.ts`;
  - the service `CLAUDE.md` ("Learning invariants (slice 8)"), `README.md:1435-1484`, `internal/app/router.go` and `internal/platform/postgres/schema.go`;
  - the web `bot-detail.ts`, `bots.css`, the view utilities and `admin.model.ts`.
- **Record notes.**
  - `verification.md`'s header says "NOT merged; NOT deployed". It was written on 2026-10-29, before the branch update and the merges.
  - `state.json` (`branchUpdate`, `deploy`, `perProject.*.mergeCommit` and the `log` from 2026-10-29T09:38Z on) is authoritative for the branch update, merge and deploy.
  - `verification.md` is authoritative for the verified, partial, unverified and failed counts.
  - `state.json` still says `perProject.*.phase: AWAITING_MERGE` beside `prState: MERGED`. The phase field was not advanced per project.
- **Not changed by this build.**
  - `tidewatch-specs` and `tidewatch-apis` are not git repositories, so the spec text and the API collection were not edited.
  - The spec corrections below are carried in this document and the wiki.
  - `documents/` is untouched (slice-0 D17).

## Concept

### Stage, stated precisely

| Stage | Status |
|---|---|
| Implemented | **Migrations:** MIG1–MIG3 in one commit, `6f776c0`. Branch update: merge `49f06b9`, then `d28de68` (harness round trips with L between K and M; PR head). **Bot:** MIG1–S9, SM1 and FIX-G1, plus XF-2, review fix round 1 and the round-2 polish. Code `ab68c93`, plan `de9ff78`. Branch update: merge `119acd5`, then `857cac3`, `c82da43`, `f753cf3`. OD-LEARN-SPEND: `1c3317b`, `7b9e724`, `04c8fe5`, `1e8d8ec`, `435feb4` (PR head). **Service:** SVC1–SVC11, plus review fix round 1 and the polish. Code `20e9697`, plan `0c140c4`. Branch update: merge `b59bcc5`, then `5400c5e`, `98211ab`, `c29d0f0`, `48f179d` (PR head). **Web:** S1–S11, plus XF-1, review fix round 1 and the polish. Code `d5671e0`, plan `b84fd55`. Preview rounds: `3cb3fb4` (e2e: the report download checked by URL), `13d1267` (PF1), `864714c` (DESIGN.md preview evidence and a wait in a Stats keyboard test). Branch update: merge `6eff940`, then `f2ee96c` (`learning_draft_dismissed` as the 35th audit type). Merge of `main` `568002f` (favicon #24 and the app-dialog fix #25; PR head). |
| Reviewed | Plans and code in all four repositories (see "Review history"). Plan-review fix loops: bot 2, service 2, web 3. Code-review fix loops: one round each in bot, service and web. Then a polish round, the preview design re-check, and two reviews of the branch update. |
| Verified locally | Every step's contract commands exited 0, and the orchestrator re-ran them. The long integration suites were checked from the engineers' logs per step, then re-run in full by the orchestrator on the final trees (see "Test plan"). |
| Verified on a preview | **Yes.** It used a per-run isolated, retained database at M (no L) from 2026-10-28 15:29Z to 2026-10-29 03:33Z (PV1–PV5). After the merges with L it was refreshed: L was applied out of order and PV6 ran on 2026-10-30, 03:16Z–09:24Z. |
| Merged | **Yes**, 2026-10-30, by Claude on the owner's instruction, in the order migrations → service → bot → web. |
| Deployed | **Yes, to production.** A merge to `main` is a production deploy: deploy-prod → GHCR → tidewatch-kubernetes GitOps bump → ArgoCD. See "Rollout to production". |
| First scheduled production run | **Not yet.** It is due 2026-11-01 03:00 Bangkok (2026-10-31T20:00Z) for each eligible bot whose current version predates it (S3). |
| Documentation pass | This document and the wiki update (worktree `docs-7ce006e44c`). `tidewatch-specs` and `tidewatch-apis` are unchanged (non-git). `documents/` is untouched. |

### Problem

As found at `main` on 2026-10-27 (intent "Problem and evidence"):
- **The decision record already held every input.**
  - A scout `propose` carries `model {tier, model_id, direction, p, rationale, prompt_version}`, `signal_snapshot`, `market_state` (regime, Elliott, zone) and `candidate_id`.
  - Outcomes `r_1h…r_20d`, `mae`, `mfe`, `exit_reason` and `closed_at` are back-filled once.
  - `post_mortem` is writable once and frozen once confirmed.
- **Slice 7 fixed the shapes this slice extends:** `post_mortem {label, labelled_by: user|model, confirmed_by_user, labelled_at}`, the losses list with a slot for a model proposal, and `GET /stats/compare` plus `POST /bots/{id}/promote` with five conditions. `calibration_no_worse` was *skipped* when a side stated no `p` or had fewer than 30 graded.
- **A version never changes, and the v2 vocabulary is closed**, so learned behaviour can only reach a bot through a new version.
- **The runtime hooks.** `bot_run_requests` is the only path from the service to the bot. `bot_runs.loop` and `bot_run_requests.loop` were CHECKed to `scout | manager | guard`, and the model stages to five values.
- **Spend.** One $1/day Bangkok-day ceiling and a 25 % per-bot share. Accounts-roles (L) later added a per-person `daily_model_usd` of $0.50.
- **Thin data.** Driftline (News drift, tier `jev`) is observing until about 2026-11-26. It writes proposals with a stated `p` but no entries. So calibration can reach its 150 floor within weeks, while weights, the meta-model and labels need graded entries.

### The model, as built

**The runner** (`packages/bots/src/learning/runner.ts`; bot `README.md:740-742`):
- **Name, lock and switch.**
  - `learning` is the fourteenth and last of the `COLLECTOR_NAMES` (`packages/shared/src/config.ts:48`) and holds `runner:learning`. It has no per-bot lock, no account lock and no venue budget. `serve` starts it; it is never a one-shot job.
  - There is **no `LEARNING_ENABLED`** (owner OQ-1). An empty `MARKET_DATA_COLLECTORS` runs it, and an explicit list must name `learning`.
  - `LEARNING_EVAL_INTERVAL_MS` (default 60 000; integer 1 000–86 400 000; `config.ts:151-156`) is the only new variable.
- **A pass, in order:**
  1. Sweep learning runs `running` for over 30 minutes (`failed`, `interrupted`).
  2. Take the `learn` requests in one statement (`TAKE_LEARN_REQUESTS`, `learning/pg-store.ts:205`).
  3. Read the learning bots (`LEARNING_BOTS`, `learning/pg-store.ts:250`, which joins `users` and `plans` as the evaluated-bots read does).
  4. Run each requested bot as `manual`, then each due bot as `scheduled`.
  - At start the runner releases `learn` requests taken without a run.
- **The due rule (S3).** A bot is due at the first 1st of the month, 03:00 Bangkok, strictly after the later of its newest learning run and its current version's `created_at`.
  - Missed slots collapse into one, and a paused bot is never due.
  - A failed scheduled run waits for next month (owner OQ-3). *Run learning now* is the retry.
  - A legacy (v1) version is skipped silently when scheduled; when requested it gets one `failed` manual run.
- **The bots runner never takes a `learn` request.** Its take adds `AND r.loop <> 'learn'`. Its start-up sweeps (`INTERRUPT_RUNS`, `RELEASE_RUN_REQUESTS`) skip `learn` rows too, because a learning run outlives the bots runner's 5-minute cutoff (review B1).
- **What it never writes:** `bots`, `candidates`, `orders`, `ledger` or `bot_watch`. It never places an order. Runs are sequential, so a pass holds at most one pooled connection and no transaction spans a model call.
- **`learning_lock_busy`:** a requested bot whose learning run is still `running` and not yet swept is left alone, and its request waits.

**Populations and floors** (PRD §4.2; window `[max(now − 90 d, version.created_at), now)` over the current version):

| Job | Population | Floor |
|---|---|---|
| Calibration | graded proposal rows (stated `p`) | 150; a horizon under 50 rows gets no map (`too_few`) |
| Weights | graded entry rows with a cited signal | 100; a source moves only with ≥ 10 graded rows |
| Meta-model | graded entry rows | 150, of which ≥ 30 losses |
| Labelling | the bot's closed losses of any version in the last 90 days with `post_mortem` null, newest first | none; at most 100 per run |

Below its floor a job proposes nothing. The run still succeeds, writes its floors and report, and on a learned version writes the realised calibration line (D15).

**The four jobs** (pure TypeScript, no new dependency; floats inside, decimal strings out, a seeded PRNG recorded on the run):
- **`calibrate.ts` (D5, S7).**
  - Rows are sorted by `ts`; the first ⌊2n/3⌋ fit and the rest test.
  - It fits isotonic (pool-adjacent violators, at most 64 points) and Platt (Newton, L2 0.01, `p` clipped to [0.001, 0.999]) on `p_raw` (`model.p_raw ?? model.p`).
  - The method with the lower out-of-sample ECE is chosen (ten bins, 4 digits; ties go to Platt). It is **proposed** when `ece_map_oos ≤ 0.8 × ece_raw_oos`.
  - The proposed points come from a refit on the whole window. Both methods' rows are written to `calibration_maps`.
  - `n_fallback` counts rows whose `p` fell back to the signal scorer.
  - On a learned version with ≥ 30 graded, the summary carries `calibration.realised {ece_calibrated, ece_raw, n}`. The report words it "helped", "did not help" or "made it worse" (the roadmap exit-test record).
- **`weights.ts` (D6, S9, S20).**
  - Each arm (source × event type) gets `Beta(1 + wins, 1 + losses)`. A win is a net `r_5d > 0` after the modelled round-trip rate (the C14 port of the service's `ModelledCostRate`).
  - Per source, the weight is the count-weighted posterior mean over its arms, scaled so the largest is 1.00, clamped to [0.05, 1.00] and moved at most ±0.25 from the current weight (2 digits).
  - 1,000 seeded draws give the 10th–90th percentile "likely range".
  - Event-type arms and return-weighted means are reported, never applied.
- **`meta.ts` (D7, D8, S10).**
  - The features are a closed list in a fixed order: `impact`, `p_raw`, `severity`, `atr_pct`, then one-hots for tier, source, event type, horizon, regime trend and volatility, zone, asset class, entry condition and weekday, plus `elliott_candidate`. They are standardised on the training rows; a zero-variance feature is dropped and recorded.
  - Folds test `[T0 + k·30 d, T0 + (k+1)·30 d)` for k ≥ 1. A fold's training rows have `ts + purge(horizon) < fold start − 5 d`.
  - Purge margins are **7 / 14 / 39** calendar days for intraday / days / weeks (A3). A fold needs ≥ 20 test rows and ≥ 5 rows of each class.
  - Each fold fits L2 logistic regression by Newton (λ = 1, at most 50 iterations) and reports its AUC.
  - The gate opens when the mean out-of-sample AUC is above 0.58 over **at least two folds** (`MIN_FOLDS = 2`, OQ-G1). The constants are at `meta.ts:63-95`.
  - When open, the refit on all rows is written as `meta_gate` with `veto_above "0.70"`, `shrink_above "0.55"` and `shrink_factor "0.5"`.
- **`labels.ts` (D9, S12).**
  - It makes one `post_mortem` call per candidate loss (`post_mortem.v1`; `openrouter`, `anthropic/claude-haiku-5.5`, no fallback) through `openSignalsModels` (ledger, ceiling, reservations, deadline).
  - The prompt carries the decision, the price path and up to 10 later signals of the instrument in the five sessions after entry. It carries no key, body or URL.
  - The reply `{label, rationale}` is Ajv-checked, and the rationale is fitted to 240 code points.
  - The write is one READ COMMITTED transaction per proposal: `post_mortem` only where null (`labelled_by: "model"`, `confirmed_by_user: false`), a `post_mortem_proposals` row, the `model_calls` row (with `bot_id` and the owner's `user_id`) and the spend upsert.
  - A 0-row update (the owner labelled meanwhile) skips the proposal row and keeps the charged call.
  - **Two checks before every call** (`labels.ts:685-699`): the bot's 25 % share (`BOT_COST_FOR_DAY`, the bot's scout and learn runs of the day), then the owner's `plans.daily_model_usd` (`OWNER_COST_FOR_DAY`, scout and learn runs across all the owner's bots). Each check adds the run's tally and the call's estimate.
  - Over either check, or on a global ceiling refusal, labelling stops for the run (`budget_stopped`, `learning_budget_reached {budget: bot|user|ceiling}`) and the rest wait.

**The draft and the report** (D1, D12, S13, S14):
- **When a draft is written.** Only when weights, calibration or the gate proposes something. The draft is `canonical(current config with source_weights replaced and learning = {learning_run_id, fitted_at, fitted_from: current hash, calibration, meta_gate})`.
- **One pending draft per bot.** A partial unique index enforces it. A new draft supersedes the old one (`dismissed`, reason `superseded`) in the run's final transaction. A run that proposes nothing leaves the pending draft in place (owner OQ-2).
- **The report.** It is a pure render of `summary`, at most 64 KiB, stored on `learning_runs.report`. It covers the floors, calibration per horizon, the weights table and the arms "shown, not applied", the folds, AUC and importances, the post-mortems, the draft's change list and the cost.
- **The seed.** It is the first 16 hex characters of `sha256(bot_id ‖ started_at)`. The same rows and seed give the same bytes.

**A learned version in the engine** (D5, D8, S8, S11):
- **The scout.** After a survivor's `p` is settled, if `learning.calibration` has a map for its horizon, `p_cal = apply(map, p)` (3 digits). The candidate gets `p = p_cal`, and the `propose` decision's `model` carries `p: p_cal`, `p_raw` and `calibration {method, horizon, learning_run_id}`.
  - Without a map: `p` is unchanged, `p_raw` is written and `calibration` is null.
  - Tier `none` is untouched.
  - An unlearned version's `model` object is byte-identical to slice 6.
  - Refits always use `p_raw`, so maps never compound.
- **The manager.** After `allocation`, with a non-null `meta_gate`, it computes `p_loss = sigmoid(intercept + Σ coef·(x − mean)/scale)`:
  - `p_loss ≥ 0.70` is a `gated` watch verdict with reasons `["meta_veto"]` and no decision (`META_VETO`, `learning/meta-gate.ts:54`);
  - `0.55 ≤ p_loss < 0.70` multiplies `sizedBudget` by 0.5 before the room and cap;
  - below that, the entry is unchanged.
  - Entries record `policy_result.meta {p_loss, effect: none|shrink}`. As built this is on every candidate-entry intake decision of a gated version, skips and observing decisions included.
  - Direct entries (zone turns, `scout.kind = off`) are exempt. The gate never raises size.

**Service rules** (service `CLAUDE.md` "Learning invariants (slice 8)"):
- **Learned is derived from the config.** `learned := config.learning != null` (S1); there is no column.
- **Save as vN of a draft.** `POST /bots/{id}/versions` with `learning_run_id` locks the bot row, then the run row. It refuses a foreign or unknown run (`404`), a draft no longer `proposed` (`409 draft_not_pending`), and a `learning` block that differs from the draft's byte for byte (`400 {config, draft_mismatch}`). It flips the draft to `saved` with `saved_version` in the same transaction.
- **Probation is forced.** A learned config with `probation: false` is `400 {probation, invalid}`, whether or not `learning_run_id` was sent. A clone of a learned source cannot skip probation either (R12, owner OQ-S2).
- **Dismiss** is one conditional statement plus the audit row `learning_draft_dismissed`.
- **The PUT provenance rule (D10).** Confirming the model's label stores `labelled_by: "model"`, `confirmed_by_user: true`. A different label stores `labelled_by: "user"`.
- **The learned-challenger gate (D13).** A skipped `calibration_no_worse` on a learned challenger becomes `met: false`, `detail {not_comparable}`, and promote refuses with `calibration_not_comparable`. The first-champion branch is unchanged. There is no automatic promotion.
- **The export (D11)** is generated on demand from existing tables and writes nothing.

**Web** (D14, no mockup): see "Components". In short:
- the *Learning* section on the bot detail between Candidates and Version;
- the editor's locked learned block with *Remove the learned block* and the locked probation checkbox;
- the clone dialog's lock;
- on Stats, *Proposed only*, the rationale line and *Confirm*;
- the not-comparable verdict line;
- the words for `meta_veto`, a halved size and "· learned".

### Owner decisions from the intent (selected; the full D1–D15 and PD1–PD8 are in `intent.md`)

- **D1** Learned results live only in a draft version. Maps or models read by reference from a running version were rejected.
- **D2** Floors per job, over the current version's last 90 days.
- **D3** One migration with three tables. The letter was settled at build time as **M** (see "Decisions during the build").
- **D4** A separate `learning` runner. A fourth loop inside the bots pass was rejected because it would break the guard's 90 s bound.
- **D5** The calibrated `p` is what the bot states and what Stats grades; `p_raw` is kept.
- **D6** Thompson weights collapsed to the per-source vocabulary. Event-type weights are shown, not applied.
- **D7** The meta-model is `logistic_v1`. `family` is recorded so `gbdt_v1` can follow later.
- **D8** A walk-forward protocol. The gate only vetoes or shrinks.
- **D9** Post-mortem proposals come from Haiku. Sonnet would be a data change later.
- **D10** Confirmation keeps provenance.
- **D11** The export is on demand, with no table, file or training.
- **D12 (revised in the Q12 discussion, 2026-10-27).**
  - The report is a system artefact: rendered from the run's summary, stored on `learning_runs.report` and served by the service.
  - `tidewatch-wiki` is the project's knowledge base, not the system's memory, and the bot in Kubernetes could not write to it anyway.
  - So the brief's "written to the wiki `raw/` folder" is recorded drift and is not followed.
  - `documents/` is separately governed by slice-0 D17 and was not edited.
- **D13** The learned-challenger gate; a learned draft always starts on probation; there is no automatic promotion.
- **D14** No mockup; existing patterns only.
- **D15** Runs happen on observing bots and on empty data, and write a report even when nothing is proposed.
- **PD1–PD8.** The defaults covered the route list, the optional `learning` key (absent everywhere before, so no stored hash changed), the arithmetic, the fixtures, the run record, observability, the build order and the recorded non-goals: RL, fine-tuning, automatic promotion, event-type weights, hand-corrected extractions, GDELT features and the Tiingo versus EODHD question.

### Decisions during the build

| Id | When / by | Decision |
|---|---|---|
| Letter M | 2026-10-27, parent coordination | The migration is **M**, `20261028120100_learning_loop.sql`, overriding PRD S21's "L". Siblings: accounts-roles = L, signals-context = N; the merge order is **L → M → N**. M was first written on K, with J as the pin. |
| OQ-1 | 2026-10-28, owner ("Recommended for all + lanes") | No `LEARNING_ENABLED`; `learning` is a `MARKET_DATA_COLLECTORS` member. The production chart sets `collectors: ""`, so it runs with no owner action. |
| OQ-2 | same | A run that proposes nothing leaves the pending draft. |
| OQ-3 | same | A failed scheduled run waits until next month; *Run learning now* is the retry. |
| OQ-W2 (a) | same | `LearningRun` gains `saved_label` and `saved_at` (P11), from a join to `bot_versions`. A dismissal is undated. |
| OQ-W5 | same | The extraction-error export is API-only (no on-screen control). |
| OQ-W6 | same | *Load into editor* on a draft whose `fitted_from` is no longer current loads onto the current version and applies only the `moved: true` weight rows. |
| OQ-S1 | same | Audit keys `learned_from_run` and `draft_modified` on draft saves. |
| OQ-S2 (R12) | same | A clone of a learned source refuses `probation: false`; the web locks the clone dialog's probation control. |
| Wave 2 | same | `executionMode = lanes`: dependency-gated lanes, each in its own worktree. |
| Preview DB | 2026-10-28, parent | A per-run isolated, retained preview database (not the shared `forge-preview-0199b29a_tidewatch-pgdata`). M was applied on a clean K-level database without L. |
| OQ-G1 (a) | 2026-10-28T08:28Z, owner via parent | At least **two** folds, not three (PRD §4.5.2 step 2). A 90-day window can hold at most two 30-day folds, so with three the gate could never open. The bot plan went to r3; FIX-G1 applied it. |
| A3 | 2026-10-28, owner | Purge margins 7 / 14 / 39 days, not the PRD's 2 / 8 / 30 (the worst case is Songkran, 38.278 days). |
| Weeks-horizon limitation | 2026-10-28, owner accepted | A mostly weeks-horizon bot cannot open the gate under these rules. A longer meta window is a follow-up spec. |
| XF-1, XF-2 | 2026-10-28, orchestrator | XF-1: the web's C15 features walk was switched to per-item checking, to match the service and the bot. XF-2: the bot accepts `fitted_at` years 0000–0099. |
| Design SF-2 (a) | 2026-10-28, orchestrator | One `.status-line` per job, as the PRD says; DESIGN.md amended. |
| OD-PV2-1 | 2026-10-29T01:58Z, owner | "Fix with CSS": in the unfiltered Stats labelling list at 1100 and 1080, *Confirm* and *Save* must be fully in view. |
| OD-PV2-2 | same, owner | "Drop it for Failure model": the Failure model table has no 560px minimum. **This amends PRD §7.4.** |
| OD-PV4-1 | 2026-10-29T06:35Z, owner | "Keep them separate": the seeded learning bots stay under `pv4-learning` on the preview database. |
| OD-LEARN-SPEND | 2026-10-29T14:30Z, owner | "Count it fully": `post_mortem` `model_calls` rows carry `bot_id` and the owner's `user_id`. The owner's day spend reads scout **and learn** runs (`OWNER_COST_FOR_DAY`, renamed from `SCOUT_COST_FOR_OWNER_DAY`). The labeller checks `spent_user + tally + estimate ≤ plans.daily_model_usd` after the per-bot share. |
| OD-MERGE-1 | 2026-10-30 (recorded 18:45:41Z), owner | "Merge them for me": merge the four PRs now, in order. |

### Spec corrections: the as-built truth that supersedes the PRD and intent text

The build did not edit the spec folder, which is not a git repository. Where this list and `prd.md` or `intent.md` disagree, this list is the truth.

- **The migration is M, `20261028120100`, and it applies on L.**
  - Every "L" in the spec for this feature reads M.
  - The service's `RequiredSchemaVersion` moved L → M (`internal/platform/postgres/schema.go:33`). The bot's `scripts/sql-integration.sh` pins M by the anchored lookup `learning_loop` and keeps L, J and H asserted.
  - L (`20261028120000`) was the pin until M. J was the pin until L, and K was never pinned.
- **OQ-G1:** PRD §4.5.2 step 2's "at least three folds" is **at least two**. FR-LL-E2E-002's open-gate case was run on a seeded window of at most 90 days (88 days).
- **A3:** PRD S10's purge margins of 2 / 8 / 30 days are **7 / 14 / 39**. The holidays in the covering test are hard-coded through 2027.
- **OQ-1:** there is no `LEARNING_ENABLED` (PRD §4.1, §8.1, intent "Constraints"). Learning is switched off only by an explicit `MARKET_DATA_COLLECTORS` list that omits `learning`.
- **OQ-W2:** `LearningRun` ends with `saved_label` and `saved_at` (P11). PRD §4.12's "Dismissed on {date}" reads "Dismissed", with no date (M has no dismissal timestamp).
- **OQ-S1:** `bot_version_created` gains `learned_from_run` and `draft_modified` on a draft save only. PRD §4.10.1's "The audit `bot_version_created` is unchanged" is superseded; §8.3's detail list was right.
- **OQ-S2 / R12:** a clone of a learned source refuses `probation: false`. The PRD names no clone rule.
- **OD-PV2-2:** PRD §7.4's 560px minimum applies to *Proposed weights* and *Calibration* only. The *Failure model* table has none and fits 358px at 390 (`src/styles/components/bots.css:181-196`).
- **OD-PV2-1:** above 600px the Stats labelling list's Decision and Signal second lines and the saved tag may wrap, so *Confirm* and *Save* are in view at 1100 and 1080.
- **OD-LEARN-SPEND, together with L:**
  - PRD §5.3's "Not stored, by decision: … a `bot_id` on `model_calls`" is superseded: after L and this ruling, `post_mortem` rows carry `bot_id` and `user_id`.
  - PRD S17 is widened. `BOT_COST_FOR_DAY` (scout + learn, per bot; `packages/bots/src/pg-store.ts:1271`) sits beside `OWNER_COST_FOR_DAY` (scout + learn, per owner; `pg-store.ts:1291`). The labeller checks both.
- **Gate chain:** PRD §6.1 mounts the routes behind `RequireRole("admin")`. Since L every product route is behind `RequireRole("user")`, and nothing accepts `admin`.
- **`learn` rows are invisible to the existing bot reads.** This is the service plan's R4; the PRD is silent. `BotRepo.LastRun`, `Runs`, `RunByID` and `LatestRunRequests` filter `loop <> 'learn'`. `GET /stats` `kpis.cost_usd` still includes a learning run's labelling spend.
- **SF-C1 (a known limitation, documented, not fixed):**
  - A draft carries only this run's proposals.
  - Within about 60 days of saving a gated or mapped version, a new draft has `meta_gate: null` (`too_few_folds`) and lacks unproposed maps. Saving it switches that gate or map off.
  - The change list shows it (`learning.meta_gate: logistic_v1, AUC x → none`).
- **SF-C2:** a bad `post_mortem` route row does not stop the signals pipeline or the bot stages. Only the labeller's stage start refuses it (`assertPostMortemRoute`) and logs `learning_model_stage_failed` once.
- **A missing provider key** refuses only the labeller's stage start, logged once. The losses wait.
- **FR-LL-BOT-003's 120-row Platt case:**
  - PRD §4.3 item 5 does not say which sample is out of sample.
  - The test runs the job on the oldest 120 rows and scores the stored refit on the other 1,880; 191 of 200 seeds pass.
  - Accepted by the code reviewer.
- **The weights interval** is collapsed, scaled and clamped but not stepped. A report can show a proposal outside its own likely range; on the preview, finnhub was proposed at 0.35 with a range of 0.05–0.17.
- **The report** prints 4-digit ECE; the PRD example shows 3.
- **LL-W-1:** the web skips the learning read for a non-v2 version and shows the legacy sentence.
- **LL-W-21 (PF1):** with a pending draft whose gate is closed, the service sends `draft.diff.meta_gate: null`. The web then draws the Failure model table from `latest.summary.meta_model`, so "gate closed" is readable (PRD §4.11.1).
- **The cut export stream:** after the 200 has started, a failure aborts the connection, so the client sees a cut, not a clean end. This holds over HTTP/1.1 (the main listener).
- **Q12 / D12:** the brief's report-in-the-wiki is not followed; the report lives on `learning_runs.report`.
- **A3, A6, A8 and A5:** see "Test plan".

### Branch update onto L (2026-10-29, session `e80c96e2`)

L (accounts-roles: migrations #16, service #18, bot #19, web #23) merged to `main` on 2026-10-29, and all four learning-loop PRs then conflicted.
- **Method.** Merge `origin/main` into each branch (merge commits, no force-push), resolve, re-run the checks and push. Pushed at 10:22:47Z.
- **Migrations** `49f06b9` + `d28de68`: `make migrate-validate` exit 0 (15 files); `make check-disposable-db` PASS (4,153 PASS, 0 FAIL). J's down-to-I round trip is reported "not run", because with L between it would run L's destructive down. M's header still says it applies on K with J as the pin; it was left unedited because the file is reviewed and its SHA recorded.
- **Bot** `119acd5` + `857cac3` (`LearningModelCall` based on the unattributed `BotStageCall`), `c82da43`, `f753cf3`: nx run-many exit 0 (bots 527 tests). sql-integration PASS on L+M.
- **Service** `b59bcc5` + `5400c5e`, `98211ab` (the learning handler tests sign in as role `user`), `c29d0f0` (a learned save still gets the plan tier check), `48f179d`. `go test ./... -race`: 41 packages, 790 PASS. `make ci` exit 0. `make test-integration` on L+M ok, recorded as "229 functions PASS". `TestReady_LearningSchema_NotReady` now migrates to L.
- **Web** `6eff940` + `f2ee96c`: the admin `AUDIT_TYPES` list is closed (34), so `learning_draft_dismissed` was added as the 35th (`src/app/pages/admin/data/admin.model.ts:184`). Unit tests: 178 files, 6,994 pass. Lint, build and e2e lint pass.
- **Review.** The code-reviewer approved every conflict resolution and raised one finding. `post_mortem` `model_calls` were unattributed (they showed as ingest on Spend), and learn spend sat outside the per-person allowance. The owner ruled OD-LEARN-SPEND.
- **The fix**: `1c3317b`, `7b9e724`, `04c8fe5`, `1e8d8ec` and `435feb4`.
  - Reviewed APPROVED with one should-fix, a runner-level spec, resolved by `1e8d8ec`.
  - Final checks: nx exit 0 (bots 536); sql-integration PASS (bots int 61).
  - Recorded residuals: pre-fix `post_mortem` rows keep NULL attribution (12 on the preview, none in production); the allowance holds per runner; the report's budget line shows the bot share only; `.plans/accounts-roles.md` still names `SCOUT_COST_FOR_OWNER_DAY`.
- **Web again, 2026-10-30T17:41Z (2026-10-31 local).** The web was three commits behind `main` (the favicon #24 and the app-dialog reopen-race fix #25). It merged `main` as `568002f`: lint, 6,995 unit tests and build green, e2e tsc clean. It was pushed with the PR body updated. **Playwright was not re-run on `568002f`.**

### Rollout to production (2026-10-30)

| When (UTC) | Event |
|---|---|
| recorded 18:45:41 | OD-MERGE-1. All four PRs were MERGEABLE, CLEAN and validated (PV6_ci); migrations, bot and service were current with `main`, and the web had just been updated. |
| ″ | Merged migrations #14 → `8feeae3`; deploy-prod ok. GitOps `c376f6e` bumped `migrate.image` only. **No ArgoCD sync followed**: the migrate Job is a hook of the `tidewatch-service` chart, and hooks are not diffed. |
| ″ | Merged service #16 → `3f8627a`. ArgoCD synced the service's GitOps deploy commit `166610b` (tidewatch-kubernetes) and the sync succeeded, and the migrate Job (Sync hook, wave −1) **applied M** in that sync. `/info` reported commit `3f8627a`, and `/ready` answered 200 with the schema ok. |
| ″ | Merged bot #17 → `2a3a412`. Rollout ok and `/ready` ok; the `learning` collector started, with a first learning pass. |
| 18:45:09 (re-auth) | During the bot rollout, the production bot's Alpaca stream looped on 406. The local preview bot (`forge-0199b29a-ll-f3bdc8b0-tidewatch-bot-1`) held the same Alpaca key and had taken Alpaca's single stream connection. Production re-authenticated at 18:45:09Z after the preview container was stopped. |
| ″ | Merged web #21 → `de00a5f`. Rollout ok; the live bundle serves the learning routes (`/learning/runs` in the bundle). An unauthenticated `GET /bots/{id}/learning/runs` answers 401. |

**Why this order.** The build prompt allowed bot and service in either order, both before the web. The rollout went migrations → **service** → bot → web for two reasons:
- **M had to be applied before the bot rolled.** A migrate-image-only bump does not apply M; only the service sync does. The bot has no schema-version check, so a bot rolled before M would have failed its learning queries against an L-only database. That is the same class as accounts-roles' 42P01 window.
- **The web went straight after the service.** The admin audit list is closed: a `learning_draft_dismissed` event shown to an older web would fail its strict reader.

**Lesson recorded (GitOps and hooks), confirmed a second time.** A migrations-only GitOps bump does not trigger an ArgoCD sync. A rollout needs a service image bump in the same rollout, or a manual sync. The service must sync before any consumer that needs the new schema rolls.

**Lesson recorded (one Alpaca stream per key).** Alpaca allows a single stream connection per key. A preview or local bot that holds the production Alpaca key takes the stream from production whenever production restarts, and production then loops on 406. Stop preview bots, or give them another key, before a production bot rollout.

### Review history

- **Plans.**
  - Bot: r1 CHANGES REQUESTED (4 blocking: learn filters on `INTERRUPT_RUNS` and `RELEASE_RUN_REQUESTS`, missing Files, unchecked files, a smelt mismatch); r2 APPROVED; r3 APPROVED after OQ-G1, re-running only the S5 and S11 contracts.
  - Service: r1 CHANGES REQUESTED (2 blocking); r2 APPROVED (3 should-fix); r3 APPROVED.
  - Web: r1 CHANGES REQUESTED (3 blocking); r2 APPROVED; r3 APPROVED (P11 and the R12 lock); r4 APPROVED (the S3 scope needed `stats-view.ts`).
- **Code round 1** (eight reviewers, 2026-10-28 10:52–11:01Z):
  - **Web:** security APPROVED (N1: bidi characters in the model rationale); angular APPROVED (3 nits); code APPROVED (4 nits).
  - **Service:** security APPROVED (3 nits: the cut export ends as a clean 200; no deadline when the writer refuses one; no concurrent-export limit); code APPROVED with one should-fix (a mid-stream export failure looks complete).
  - **Bot:** security APPROVED with SF-1 (a paid `post_mortem` call was lost from the ledger when the proposal write failed) and SF-2 (the log scan lacked rationale, report, name and config keys); code APPROVED with SF-C1 (document that a draft drops gate and maps) and SF-C2 (a bad `post_mortem` route row stopped the whole signals pipeline).
  - **Web design:** CHANGES REQUESTED (SF-1…SF-6, no rendered evidence).
- **Fix round 1.** Dispatched at 11:00Z. The orchestrating session ended before the hand-backs arrived. The evidence shows the edits done and every suite green.
- **Round 2** (14:45–14:51Z), all APPROVED:
  - bot security (SF-1: `labels.ts` records the lost call and charges it before release; SF-2: the forbidden keys and a `runLearning` sentinel case);
  - service code (the export cut aborts the connection; the deadline fails closed; a compile-time assertion in `router.go`);
  - bot code (SF-C1 by documentation; SF-C2 in code: the bad row is kept with its problem, `assertRoutePrices` prices J's five only, and the labeller asserts its route);
  - web code (`<bdi>` around the rationale);
  - web design at source level.
- **Polish r2** (cheap nits), with a code-reviewer over the three deltas: APPROVED with S-1. The bot's `problem` field mislabelled J-stage refusals. It was fixed and confirmed at 15:18:36Z.
- **Preview design.** PV2 CHANGES REQUESTED (SF-PV2-1 Confirm and Save out of view at 1100, SF-PV2-2 the Failure model 560px minimum at 390, SF-PV2-3 the DESIGN.md refresh). Resolved by PF1 with OD-PV2-1 and OD-PV2-2. PV2 round 2 **APPROVED** (0 blocking, 0 should-fix, 2 nits; `review/tidewatch-web/design-pv2-r2.md`).
- **Branch update.** The code-reviewer approved every conflict resolution. Finding 1 was resolved by OD-LEARN-SPEND, whose fix was reviewed APPROVED.

## Database

### Migration M: `20261028120100_learning_loop.sql`

`tidewatch-migrations` PR #14, merge `8feeae3`; file sha256 `3b68d1be…ba51d`.
- The PRD §5.1 block runs verbatim from `-- +goose Up` through the last Down statement. The header (lines 1–38) is the only addition.
- It runs in goose's default transaction, with no trigger, function or view.
- It is the service's `RequiredSchemaVersion` from this build on.
- The five constraint names were verified on the disposable database (A2): `bot_runs_loop_check`, `bot_run_requests_loop_check`, `model_routes_stage_check`, `model_calls_stage_check`, `prompt_versions_stage_check`.

```sql
-- +goose Up
CREATE TABLE learning_runs (
    learning_run_id  uuid        PRIMARY KEY DEFAULT uuidv7(),
    bot_id           uuid        NOT NULL REFERENCES bots (bot_id),
    bot_version      text        NOT NULL,
    run_id           uuid        NOT NULL,
    trigger          text        NOT NULL CHECK (trigger IN ('scheduled', 'manual')),
    started_at       timestamptz NOT NULL,
    finished_at      timestamptz,
    status           text        NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    error            text,
    window_from      timestamptz NOT NULL,
    window_to        timestamptz NOT NULL,
    seed             text        NOT NULL CHECK (seed ~ '^[0-9a-f]{16}$'),
    floors           jsonb       NOT NULL DEFAULT '{}',
    summary          jsonb       NOT NULL DEFAULT '{}',
    counts           jsonb       NOT NULL DEFAULT '{}',
    draft_config     jsonb,
    draft_status     text        CHECK (draft_status IN ('proposed', 'saved', 'dismissed')),
    dismissed_reason text        CHECK (dismissed_reason IN ('user', 'superseded')),
    saved_version    text,
    report           text        CHECK (octet_length(report) <= 65536),
    FOREIGN KEY (bot_id, bot_version)   REFERENCES bot_versions (bot_id, version),
    FOREIGN KEY (bot_id, saved_version) REFERENCES bot_versions (bot_id, version),
    CHECK ((status = 'running') = (finished_at IS NULL)),
    CHECK ((draft_config IS NULL) = (draft_status IS NULL)),
    CHECK ((draft_status = 'saved') = (saved_version IS NOT NULL)),
    CHECK ((draft_status = 'dismissed') = (dismissed_reason IS NOT NULL))
);
CREATE INDEX learning_runs_bot_started_idx ON learning_runs (bot_id, started_at DESC);
CREATE UNIQUE INDEX learning_runs_pending_draft_key ON learning_runs (bot_id) WHERE draft_status = 'proposed';

CREATE TABLE calibration_maps (
    map_id          uuid         PRIMARY KEY DEFAULT uuidv7(),
    bot_id          uuid         NOT NULL REFERENCES bots (bot_id),
    bot_version     text         NOT NULL,
    learning_run_id uuid         NOT NULL REFERENCES learning_runs (learning_run_id),
    tier            text         NOT NULL CHECK (tier IN ('jev', 'small_llm', 'large_llm')),
    horizon         text         NOT NULL CHECK (horizon IN ('intraday', 'days', 'weeks')),
    method          text         NOT NULL CHECK (method IN ('isotonic', 'platt')),
    points          jsonb        NOT NULL,
    n_fit           integer      NOT NULL CHECK (n_fit >= 0),
    n_test          integer      NOT NULL CHECK (n_test >= 0),
    ece_raw_oos     numeric(6,4) NOT NULL CHECK (ece_raw_oos >= 0),
    ece_map_oos     numeric(6,4) NOT NULL CHECK (ece_map_oos >= 0),
    proposed        boolean      NOT NULL,
    created_at      timestamptz  NOT NULL DEFAULT now(),
    FOREIGN KEY (bot_id, bot_version) REFERENCES bot_versions (bot_id, version),
    UNIQUE (learning_run_id, horizon, method)
);

CREATE TABLE post_mortem_proposals (
    decision_id     uuid          PRIMARY KEY REFERENCES decisions (decision_id),
    bot_id          uuid          NOT NULL REFERENCES bots (bot_id),
    learning_run_id uuid          NOT NULL REFERENCES learning_runs (learning_run_id),
    label           text          NOT NULL CHECK (label IN ('signal_late', 'already_priced', 'regime_shift', 'stopped_by_noise', 'signal_wrong', 'sizing', 'execution')),
    rationale       text          NOT NULL CHECK (length(rationale) BETWEEN 1 AND 240),
    model_id        text          NOT NULL,
    prompt_version  text          NOT NULL,
    cost_usd        numeric(10,6) NOT NULL CHECK (cost_usd >= 0),
    proposed_at     timestamptz   NOT NULL DEFAULT now()
);
CREATE INDEX post_mortem_proposals_bot_proposed_idx ON post_mortem_proposals (bot_id, proposed_at DESC);

ALTER TABLE bot_runs         DROP CONSTRAINT bot_runs_loop_check,         ADD CONSTRAINT bot_runs_loop_check         CHECK (loop IN ('scout', 'manager', 'guard', 'learn'));
ALTER TABLE bot_run_requests DROP CONSTRAINT bot_run_requests_loop_check, ADD CONSTRAINT bot_run_requests_loop_check CHECK (loop IN ('scout', 'manager', 'guard', 'learn'));
ALTER TABLE model_routes     DROP CONSTRAINT model_routes_stage_check,    ADD CONSTRAINT model_routes_stage_check    CHECK (stage IN ('triage', 'extraction', 'scoring', 'bot_decide', 'bot_thesis', 'post_mortem'));
ALTER TABLE model_calls      DROP CONSTRAINT model_calls_stage_check,     ADD CONSTRAINT model_calls_stage_check     CHECK (stage IN ('triage', 'extraction', 'scoring', 'eval', 'bot_decide', 'bot_thesis', 'post_mortem'));
ALTER TABLE prompt_versions  DROP CONSTRAINT prompt_versions_stage_check, ADD CONSTRAINT prompt_versions_stage_check CHECK (stage IN ('triage', 'extraction', 'scoring', 'bot_decide', 'bot_thesis', 'post_mortem'));

INSERT INTO model_routes (stage, provider, model_id, fallback_provider, fallback_model_id) VALUES
    ('post_mortem', 'openrouter', 'anthropic/claude-haiku-5.5', NULL, NULL);
```

**Notes on the schema.**
- **Unlinked and append-only by convention.** `learning_runs.run_id` has no foreign key, like `decisions.run_id`. `post_mortem_proposals` is append-only by convention: one row per decision, never updated or deleted.
- **Stored shapes.** `calibration_maps.points` is `[["p","y"], …]` for isotonic and `{"a","b"}` for Platt, as decimal strings.
- **Generated names.** PostgreSQL named the four table-level `learning_runs` CHECKs `learning_runs_check` and `learning_runs_check1`…`check3`. The harness matches them by these names.
- **Seeds.** Six routes exist after M; the `post_mortem` price row is Haiku's, already seeded.
- **What M did not add.** No `learned` column (S1) and no change to any table's columns. The `bot_id` and `user_id` on `model_calls` come from L, not M.
- **One draft per bot.** The partial unique index `learning_runs_pending_draft_key` keeps one `proposed` draft per bot. A new draft's supersession and its insert happen in the same final transaction.

### The Down (destructive, owner-only, local-only; never a recovery path)

In order:
1. Delete the `post_mortem` route.
2. Narrow the five CHECKs back.
3. Drop `post_mortem_proposals`, `calibration_maps` and `learning_runs`, using `IF EXISTS` and no `CASCADE`.

It **fails loudly** (goose exit 1, M kept whole) while a `bot_runs` or `bot_run_requests` row has loop `learn`, or a `model_calls` or `prompt_versions` row has stage `post_mortem`. In production both kinds of row exist once a learning run has happened. It leaves `decisions.post_mortem` proposals in place, because they are decision data.

### Harness (`scripts/check-disposable-db.sh`)

- **FR-LL-MIG-001:** the catalog, the three tables, the five re-created CHECKs by name, the seed count of 6 routes, and the pin summary moved to M (224 PASS lines at MIG2).
- **FR-LL-MIG-002:** rolled-back refusal probes, each matched by constraint name (82 PASS lines):
  - a second `proposed` draft;
  - an eighth label;
  - a 241-code-point rationale;
  - `saved` without `saved_version`;
  - `dismissed` without a reason;
  - `running` with `finished_at`;
  - a `learn` request or run before M;
  - a `post_mortem` call and prompt row accepted after M (including a `model_calls` row with a NULL `document_id`, A1).
- **FR-LL-MIG-003** (step 10e; 37 PASS lines): four committed probes make the down fail while M stays whole. Then come the down and up round trip; the down leaves L applied, and every A–L assertion passes there.
- **Exact lists and filters.** F's and J's exact assertions defer to M by constraint name while M is applied.
- **After the branch update** (`d28de68`): M and L round trips with L between K and M; 4,153 PASS, 0 FAIL.

### Who reads and writes what

| Object | Writer | Reader |
|---|---|---|
| `learning_runs` | bot: every column except the three below | service: all of them |
| `learning_runs.draft_status` → `saved` / `dismissed (user)`, `dismissed_reason = 'user'`, `saved_version` | service: Save as vN of a draft, dismiss | bot (supersession checks), service |
| `learning_runs.draft_status` → `dismissed (superseded)` | bot: the run's final transaction | service |
| `calibration_maps`, `post_mortem_proposals` | bot | service (`LossRow.proposal` joins `post_mortem_proposals`) |
| `bot_runs` (loop `learn`), `bot_run_requests.taken_at` / `run_id` for `learn` | bot (learning runner) | service: learning routes only; hidden from the other bot reads (R4) |
| `bot_run_requests` (loop `learn`) insert | service (`POST /bots/{id}/run`) | bot (learning runner) |
| `decisions.post_mortem` | bot: where null, `labelled_by: model`; service PUT: user or confirmed model | service Stats, export |
| `model_calls` (stage `post_mortem`, `bot_id`, `user_id`), `model_spend_daily`, `prompt_versions` (`post_mortem.v1`) | bot | the bot's ceiling; the service's console Spend |
| `bot_versions.config->'learning'` | service (Save as vN) | bot (`readConfigV2`), service (`learned`), web |

## API

### Conventions

- **Routes and gates.** All six new routes mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("user") → RequirePasswordChanged` (`internal/app/router.go:518-523`). The gated product count goes 64 → **70** (`TestRouter_ForcedChangeGatesNewRoutes`).
- **Ownership.** Routes are owner-scoped. An id that is not a UUID, is absent, or is another user's is the one `404 not_found`, never `403`. Queries and bodies are parsed strictly, and the POSTs need CSRF.
- **EnsureBots.** The five `/bots/{bot_id}/learning…` routes run `EnsureBots`. The export does not, because it creates nothing (P10).
- **Reads.** Each learning read is one `REPEATABLE READ READ ONLY` snapshot (S15). Stored `{}` for `floors`, `summary` or `counts` is served as `null`; `draft.config` is in C10 canonical form.
- **Formats.** Decimals are strings: ECE and AUC 4 digits, weights 2, `cost_usd` 6. Instants are RFC 3339 UTC; Bangkok is a fixed UTC+07:00.
- **What the service adds:** no environment variable, Redis key, `/ws` frame or model call (service `README.md:1437-1443`).

### Routes

| Method and path | Request | 2xx | Refusals |
|---|---|---|---|
| `POST /bots/{bot_id}/run` (changed) | `{loop: scout\|manager\|guard\|learn}` | `202 {request_id, requested_at}` | as before; `learn` on a version that is not v2 is `400 {field: loop, reason: invalid}`, "Learning needs a v2 version. Upgrade the bot first." (P8, after the manual and paused refusals, before `run_pending`); 6 per hour per bot and loop |
| `GET /bots/{bot_id}/learning` | — | `200 {generated_at, next_run, request, latest, draft}` | `400` (any parameter), `404` |
| `GET /bots/{bot_id}/learning/runs` | `limit` 1–100 (20), `cursor` (kind `E`) | `200 {items: [LearningRun], next_cursor}`, newest first | `400`, `404` |
| `GET /bots/{bot_id}/learning/runs/{learning_run_id}` | — | `200 LearningRun` | `400`, `404` ("That learning run doesn't exist.") |
| `GET /bots/{bot_id}/learning/runs/{learning_run_id}/report` | — | `200 text/markdown; charset=utf-8`, `Content-Disposition: attachment; filename="learning-{bot-slug}-{YYYY-MM}.md"` | `400`, `404` (also for a run without a report) |
| `POST /bots/{bot_id}/learning/draft/dismiss` | no body | `200 {learning_run_id, draft_status: "dismissed"}` | `400 manual_bot`, `404`, `409 draft_not_pending` |
| `POST /bots/{bot_id}/versions` (changed; 64 KiB config group) | `{config, probation?, learning_run_id?}` | `201 {version, bot}` | as before, plus P2's order (below) |
| `POST /bots/{bot_id}/clone` (changed) | as before | as before | a learned source with `probation: false` is `400 {probation, invalid}` (R12) |
| `GET /learning/extraction-errors` | `bot_id?`, `from?`, `to?` (Bangkok dates on `decisions.ts`, `from ≤ to`, at most 366 days) | `200 application/x-ndjson; charset=utf-8`, `attachment; filename="extraction-errors-{YYYYMMDD}.jsonl"` | `400` (grammar, ranges), `404` (a foreign `bot_id`) |
| `GET /stats/losses` (changed) | `+ proposed=1` | `LossRow` ends with `proposal: {rationale, model_id, proposed_at} \| null` | `400 {field: proposed, reason: invalid}`; the filtered list's cursor is kind `M` and is refused on the unfiltered list, and the reverse |
| `PUT /decisions/{decision_id}/post-mortem` (changed) | as slice 7 | `labelled_by` per the provenance rule | as slice 7 (`409 post_mortem_frozen` once confirmed) |
| `GET /stats/compare`, `POST /bots/{bot_id}/promote` (changed) | as slice 7 | for a learned challenger, a skipped `calibration_no_worse` is `met: false, detail {not_comparable: <reason>}` | promote's `409 promotion_refused` gains the reason `calibration_not_comparable` (nine documented reasons) |
| `GET /bots`, `GET /bots/{bot_id}`, `GET /stats`, `GET /bots/{bot_id}/versions[/{seq}]` (changed) | as before | `learned` as the last key of `strategy`, of the stats and compare `version`, of each versions item and of the version detail (P7) | as before |

**The status body** (`GET /bots/{bot_id}/learning`, PRD §6.2):

```json
{
  "generated_at": "…",
  "next_run": "2026-12-01T03:00:00+07:00",
  "request": {"request_id": "…", "requested_at": "…", "taken_at": null, "run_id": null, "stale": false},
  "latest": { "…LearningRun" },
  "draft": {
    "learning_run_id": "…", "proposed_at": "…",
    "config": { "…the full draft config" },
    "diff": {
      "weights": [{"source_code": "sec-8k", "current": "1.00", "proposed": "0.85", "lo": "0.62", "hi": "0.97", "n": 41, "moved": true}],
      "calibration": [{"horizon": "days", "method": "isotonic", "n_fit": 141, "n_test": 71, "ece_raw_oos": "0.0910", "ece_map_oos": "0.0410"}],
      "meta_gate": {"auc_oos": "0.6120", "gate": true, "folds": [{"from": "…", "to": "…", "n_train": 90, "n_test": 31, "auc": "0.6300"}], "importances": [{"feature": "p_raw", "coef": "-0.5400"}]}
    }
  }
}
```

**Fields of the status body.**
- **`next_run`** is the first `YYYY-MM-01T03:00:00+07:00` after the later of the newest learning run and the current version (P3). It is `null` for the manual bot, a paused bot and a version that is not v2.
- **The manual bot** gets `200` with only `generated_at` set.
- **`request`** is the newest `learn` request, `stale` after 10 minutes.
- **`draft`** is the pending draft or `null`. `draft.proposed_at` is the run's `finished_at` (P4).
- **`diff.meta_gate`** is `null` when the draft proposes no gate, even if the run fitted a closed one (the web then reads `latest.summary.meta_model`; see LL-W-21).
- **A due bot's past slot.** A due bot's `next_run` can be a past slot for up to one pass (≤ 60 s) until the runner runs it. This was observed on the preview and is cosmetic.

**`LearningRun`** (every key always present; undefined is `null`):

```json
{
  "learning_run_id": "…", "run_id": "…", "trigger": "scheduled", "started_at": "…", "finished_at": "…", "status": "succeeded", "error": null,
  "version": {"seq": 7, "hash": "…", "label": "v7·9ad1", "learned": false},
  "window": {"from": "…", "to": "…", "days": 90},
  "seed": "3f9a1c2b4d5e6f70",
  "floors": {"calibration": {"needed": 150, "have": 212, "met": true}, "weights": {"needed": 100, "have": 0, "met": false}, "meta_model": {"needed": 150, "have": 0, "losses_needed": 30, "losses_have": 0, "met": false}, "post_mortems": {"candidates": 0}},
  "summary": {"calibration": {…}, "weights": {…}, "meta_model": {…}, "post_mortems": {…}, "draft": {"changes": [{"path": "learning.calibration", "from": null, "to": "1 map"}]}},
  "counts": {"graded_proposals": 212, "graded_entries": 0, "losses": 0, "maps_proposed": 1, "arms_moved": 0, "auc_oos": null, "labels_proposed": 0, "cost_usd": "0.000000"},
  "has_report": true,
  "draft_status": "proposed", "saved_version": null, "dismissed_reason": null,
  "saved_label": null, "saved_at": null
}
```

The runs list omits `summary.weights.arms` and `summary.meta_model.folds`; the detail has them. `saved_label` and `saved_at` (P11, OQ-W2) are `null` unless `draft_status` is `saved`.

**Save as vN of a draft (P2).** The save locks the `bots` row `FOR NO KEY UPDATE`, then the run row `FOR UPDATE`, and refuses in this order:
1. bot `404`;
2. manual `400`;
3. a run that is not this bot's or user's: `404`;
4. `409 draft_not_pending`, "That draft was already saved or dismissed.";
5. `400 {field: config, reason: draft_mismatch}`, "The learned block can't be edited. Load the draft again.";
6. `probation: false` on a learned config: `400 {field: probation, reason: invalid}`, "A learned version starts on probation.";
7. the validator;
8. `409 version_unchanged`;
9. the insert.

After the insert:
- The draft flips by a conditional `UPDATE … AND draft_status = 'proposed'` that must touch exactly one row.
- The `version_created` event and the audit `bot_version_created` gain `learned_from_run` and `draft_modified`. `draft_modified` is true when the saved config differs from `draft_config` outside `learning`.
- A learned config posted without `learning_run_id` is accepted with probation forced, and no draft changes.
- An unlearned save keeps the slice-6 order and messages byte for byte.
- `learning_run_id` must be absent, `null` or a UUID string, else `400 {learning_run_id, invalid}` (P1).
- After the branch update, a learned save still gets the plan tier check (`c29d0f0`).

**The export line** (keys in this order; PRD §4.10.5):

```json
{"decision_id":"…","bot_id":"…","version_label":"v7·9ad1","ts":"…","instrument_id":"NVDA@webull","direction":"long",
 "document":{"document_id":"…","source_code":"sec-8k","tier":"filing","publisher":"SEC 8-K","title":"…","canonical_url":"…","published_at":"…","language":"en","body_status":"full","body":"…","body_truncated":false},
 "extraction":{"extraction_id":"…","prompt_version":"extraction.v1","schema_version":"…","model_id":"…","output":{…},"key_facts":["…"],"rationale":"…"},
 "signal":{"signal_id":"…","event_type":"guidance","direction":"up","p":"0.740","impact":"0.8200","severity":"3.00","horizon":"days","scoring_version":1},
 "outcome":{"horizon_column":"r_5d","r":"-0.031200","hit":false,"exit_reason":"stop"},
 "post_mortem":{"label":"signal_wrong","labelled_by":"model","labelled_at":"…"},
 "correction":{"direction_realised":"down"}}
```

**Which rows are exported.**
- **Rows:** the user's `actor bot` `buy | add` decisions with a **confirmed** `signal_wrong` label. `signals` and `documents` are inner joins, and the newest extraction of the document is taken.
- **Bodies:** `body` only for `body_status = 'full'`, cut at 65,536 bytes on a UTF-8 boundary with `body_truncated: true`. `version_label` may be `null` (LEFT JOIN).
- **Order and empty results:** `decisions.ts, decision_id` order; an empty result is an empty `200`.
- **Deadline.** The snapshot and the stream run under one 60 s deadline (`extractionExportTimeout`, a code constant).
- **Failures.** A writer that cannot take the write deadline is refused with `500` before any byte. A failure after the 200 has started logs `extraction_export_failed` and aborts the connection.

**Codes, audit, metrics and logs (service).**
- **Codes.** `draft_not_pending` (409) is in `AllCodes()`. New `invalid_request` reasons: `draft_mismatch`, and `invalid` on `learning_run_id` and `probation`. New `promotion_refused` reason: `calibration_not_comparable`.
- **Audit.** `learning_draft_dismissed {bot_id, learning_run_id}`. `bot_version_created` gains `learned_from_run` and `draft_modified` on a draft save only. `post_mortem_labelled` always carries `confirmed_proposal`. `bot_run_requested` carries `{loop: learn}`.
- **Metrics.** `learning_drafts_total{outcome: saved|dismissed}` and `bot_run_requests_total{loop="learn"}`, both at 0 from start.
- **Logs.** `learning_draft_dismissed`, `extraction_export_failed` and `bot_version_created` (with `learning_run_id` on a draft save). They carry ids and enums only, never a rationale, report line, document body or config (`TestLogs_NoBotTextOrConfig` uses sentinels).
- **Cursors.** Learning runs use kind `E` (0x45) over `(started_at, learning_run_id)`, bound to the bot. Filtered losses use kind `M` (0x4D). Each is refused on every other list.

### The `learning` block in the v2 config (PRD §5.2; C15)

```json
"learning": {
  "learning_run_id": "<uuid>", "fitted_at": "2026-12-01T03:00:12Z", "fitted_from": "<64 hex>",
  "calibration": {"maps": [
    {"horizon": "days", "method": "isotonic", "points": [["0.1200", "0.0830"], ["0.4550", "0.3100"]], "params": null},
    {"horizon": "weeks", "method": "platt", "points": null, "params": {"a": "0.8120", "b": "-0.4100"}}]},
  "meta_gate": {"family": "logistic_v1", "features": ["impact", "p_raw", "…"], "means": ["…"], "scales": ["…"], "coef": ["…"],
                "intercept": "-0.4100", "auc_oos": "0.6120", "veto_above": "0.70", "shrink_above": "0.55", "shrink_factor": "0.5"}
}
```

**The block's rules.**
- **Presence.** It is one optional top-level key, absent on every earlier version, so no stored hash changed. When present every key is required and unknown keys are refused.
- **Refusal order.** Rules are refused in order, with the dotted `details.field`:
  - calibration has 1–3 maps in horizon order;
  - isotonic maps have 2–64 points with `p` strictly increasing and `y` non-decreasing, at 4 digits;
  - Platt maps have `a > 0`;
  - `family` is exactly `logistic_v1`;
  - `features` is a subset of the closed list, in its order, checked per item (XF-1);
  - `means`, `scales` and `coef` have the same length, with `scales > 0`;
  - `shrink_above ≤ veto_above`;
  - `shrink_factor` is in (0, 1).
- **Fixtures.**
  - `bot-version.v2-learned.json` (C15, sha256 `977068bf…`) is byte-identical in the bot (`packages/bots/fixtures/`), the service (`internal/trading/testdata/`) and the web (`src/app/pages/workspace/data/testdata/`). Each copy is pinned by its hash, with 10 accepted and 59 refusal cases.
  - C12 `bot-version.v2.json` (`44161eb0…`) is unchanged.
  - C14 `attribution-net.v1.json` (`a42edbfc…`) pins the net-return rule in the bot and the service (A7).

### Bot side (`tidewatch-bot`)

**Configuration.**
- `LEARNING_EVAL_INTERVAL_MS` is the only new variable.
- `MARKET_DATA_COLLECTORS` accepts `learning`; an empty or unset value includes it.
- The route `post_mortem` is data (M's seed).
- The labeller reads `OPENROUTER_API_KEY`, the existing key name, through the signals router.
- No dependency, lockfile, Dockerfile or Redis change.

**Metrics** (all registered at 0 with closed label sets):
- `learning_runs_total{result: proposed|noop|floor|failed}`;
- `learning_proposals_total{kind: calibration|weights|meta_gate|post_mortem}`;
- `learning_model_calls_total{stage: post_mortem}`;
- `learning_model_cost_usd_today` (this process's Bangkok-day tally);
- `learning_pass_duration_seconds`;
- `bots_run_requests_total{loop}`, which gains `learn` through the shared counter.

**Logs**: exactly ten events, closed by a source scan:
- `learning_run_started`, `learning_run_finished`;
- `learning_floor_not_met`;
- `learning_draft_proposed`, `learning_draft_superseded`;
- `learning_label_proposed`;
- `learning_model_stage_failed`, with the closed-set `problem` field (`missing_stage`, `post_mortem_provider`, `post_mortem_fallback`, `fallback_pair`, `missing_price`) only for a `post_mortem` `RouteConfigError`;
- `learning_budget_reached` (`budget` is `bot`, `user` with `user_id`, or `ceiling`);
- `learning_run_interrupted`;
- `learning_lock_busy`.

They carry ids, trigger, counts and `error_class` only, never a rationale, thesis, title, body or key.

**Prompt.** `post_mortem.v1` is recorded in `prompt_versions` with its SHA-256; six prompt versions exist now. A wording change is `post_mortem.v2`.

## Components

All of these are in `tidewatch-web`. They use the existing tokens and patterns only: no new token, colour, type step, icon or motion (D14, PRD §7.2).

**The *Learning* section** (`src/app/pages/workspace/feat-bots/bot-learning.ts`, selector `app-bot-learning`; words in `feat-bots/util/learning-view.ts`):
- **Placement.** It is rendered by `bot-detail.ts:149` between `app-bot-candidates` and `app-bot-version`, for auto bots only (none for Me). It is a `.section` with its own `h2` "Learning".
- **The run row.** A `.loop-row` reads *Learning* · "Next run {EEE d MMM HH:mm}", "no schedule (paused)" or "needs a v2 version". The second line is "Last run {d MMM HH:mm} · {trigger} · {result}"; the results are "draft proposed", "nothing to propose", "floors not met", "failed ({error})" and "never run".
- ***Run learning now*** shows the Loops' *Queued…*, the stale sentence ("Queued since {HH:mm}. The learning runner may be off.") and the 409 and 429 sentences. When a run lands, a toast reads "Learning ran at {HH:mm}: {result}".
- **Floors.** One `.status-line` per job (design SF-2 (a)).
- **The draft.** A `.tag` "Draft from {d MMM}", then three tables in named `.table-scroll` regions inside `.learning-tables`:
  - *Proposed weights*: `source · current · proposed · likely range · n`, moved rows first and bold, with tone classes on the change;
  - *Calibration*: `horizon · method · graded · raw ECE · calibrated ECE (out of sample)`;
  - *Failure model*: `fold · test rows · AUC`, the line "mean out-of-sample AUC {x} · gate {open | closed}", and the importances as a `.second` list.
  - The actions sit in `.learning-actions`: `.btn.primary` *Load into editor*, `.btn.ghost` *Dismiss draft* and the `.text-btn` *Download report*.
  - With no draft, the summary tables still render with *Download report*. With a pending draft but a closed gate, the Failure model table comes from `latest.summary.meta_model` (LL-W-21, PF1).
- **Other states.**
  - The realised line shows above the tables on a learned version.
  - "Saved as v{label} on {date}" for a saved draft, and "Dismissed" (undated) for a dismissed one.
  - Legacy: "Learning needs the current vocabulary. Upgrade this bot to enable it.", with no button and no read (LL-W-1).
  - Loading and error: "Loading…" and "Learning couldn't load." with *Try again*.
- **Formats.** ECE and AUC show 3 digits on screen and weights 2; dates are in Bangkok. "AUC" and "ECE" are written out once in the section note.
- ***Load into editor***:
  - emits `loadRequested`, and `bot-detail` calls `loadLearned`;
  - applies the weights through the existing `applyFitted` path (only `moved: true` rows on a stale draft, OQ-W6);
  - attaches the learned block, checks and locks probation, and moves focus to the editor heading;
  - shows the note "Loaded from the learning run of {d MMM}. Review, then save as v{seq+1}; it starts on probation."
- ***Save as vN*** posts `learning_run_id` only when the config's block belongs to the held run. A `409` reads "That draft was already saved or dismissed. Reload the bot."; a `400 draft_mismatch` reads "The learned block can't be edited. Load the draft again."
- ***Dismiss draft*** re-reads the section, toasts "Draft dismissed." and moves focus to the Learning heading.
- ***Download report*** is `<a download class="text-btn" href="{apiBase}/bots/…/learning/runs/…/report">`. The session cookie applies on the same origin (A5), and the service names the file `learning-{bot-slug}-{YYYY-MM}.md`.

**The version editor and the clone dialog** (`feat-bots/bot-version.ts`, `feat-bots/data/bot-editor.service.ts`, `feat-bots/util/bot-draft.ts`, `feat-bots/bot-dialog.ts`, `feat-bots/util/bot-dialog-view.ts`):
- **The learned block.** A loaded learned version shows the `.status-line` "Learned block from the run of {d MMM}: {n} calibration map(s) · failure model gate {open (AUC {x}) | none} · locked. A learning run proposes a new one."
  - Beside it is a `.text-btn`, *Remove the learned block*. It deletes the `learning` key, because an undefined value is refused. Probation then unlocks and *Save as vN* enables.
- **Probation.** With a learned block in the draft, *Start on probation (30 days)* is checked and disabled, with the title "A learned version always starts on probation."
- **The clone dialog** locks probation for a learned source (R12).
- **The serialiser** round-trips C15 to the same bytes and hash (`data/bot-config.model.ts`, which now imports `SIGNAL_EVENT_TYPES` from `./signals.model`).

**Stats** (`feat-stats/losses-list.ts`, `feat-stats/util/stats-view.ts`, `feat-stats/data/stats.service.ts`, `src/styles/components/stats.css`):
- **The filter.** A native `button[aria-pressed]` `.chip`, *Proposed only*, adds `proposed=1`; its group is named "Filter the losing decisions". An empty-under-filter sentence was added.
- **Proposal rows** show "Model: {rationale}" as a `.second` line inside `<bdi>`. The button reads *Confirm* while the select equals the proposal and *Save* otherwise.
- **Tags and toasts.** "Proposed by the model · confirmed by you · {word}" with the toast "Label confirmed.", or "Labelled by you · {word}" with "Label saved."
- **The counts line** reads "Labels: you {user} · model, confirmed by you {model} · proposed, waiting for you {proposed}". A non-breaking space keeps "waiting for you {n}" together.
- **The compare verdict.** "Calibration not comparable yet ({reason words}); a learned version must show its calibration before promotion". The refused *Promote to champion* is `aria-disabled`.
- **The sub line** adds "· learned version" (`stats-view.ts:133`).
- **Wrapping (OD-PV2-1).** Above 600px the losses table's second lines and the saved tag may wrap.

**Words elsewhere:**
- The Watch and Checks word `meta_veto` as "vetoed by the failure model" (`feat-bots/util/watch-view.ts:394`).
- The decision record's second line gains "size halved by the failure model" (`feat-trade/util/order-view.ts:377`).
- A learned strategy sentence gains "· learned" (`feat-bots/util/bot-view.ts:135`).

**Data layer.**
- `data/bots.model.ts` gains strict readers for `LearningStatus`, `LearningRun` (with P11) and `LearningDraft`, and requires `strategy.learned` and the versions' `learned`.
- `data/bots-api.service.ts` gains the five reads, the dismiss, the report and export URLs, and `learning_run_id` on save.
- `data/stats.model.ts` gains `LossRow.proposal`, `version.learned` and the not-comparable reason; `stats-api.service.ts` gains `proposed`.
- `data/trade.model.ts` gains `policy_result.meta`.
- The Stats `POST_MORTEM_LABELS` must equal `LEARNING_LABELS`.
- `src/app/pages/admin/data/admin.model.ts` reads `learning_draft_dismissed` as the 35th audit type. It is shown raw in the Audit Type filter, like the other 34.

**Styles.**
- `src/styles/components/bots.css` scopes `.learning-tables` (a column of three regions with a 12px gap; 560px table minimum except `.failure-model`) and `.learning-actions` (a wrapping flex row, 10px gap). Both sit under `.bot-detail`.
- `stats.css` adds the chip wrap and the OD-PV2-1 cell wrap.

**e2e.**
- `e2e/src/bots-learning.spec.ts` covers the run, draft, load-and-save, dismiss, download link, editor, clone and keyboard flows.
- `e2e/src/support/bots.ts` and `stats.ts` mock the §6.2 bodies and fail closed. Learning, runs, run detail and export are unmocked unless a spec mocks them.
- `support/screens.ts` adds the capture states: `bots__learning-{state}` including `learned-realised` and `draft-gate-closed`, plus `bots__editor-learned`, `bots__editor-loaded-draft`, `bots__clone-learned` and `stats__{six states}`.
- Playwright 1.63 does not route an `a[download]`, so the mock checks the link and the download URL. The file itself is checked on the real service (F-PV1-2, A5).

**`DESIGN.md`.**
- "Learning (`.learning-tables`, `.learning-actions`)" at `:1972`.
- The "Learning loop (slice 8)" verification evidence at `:4726`.
- The LL-W decisions, OD-PV2-1 and OD-PV2-2, and the source snapshot.
- `forge-setup-impeccable --check` is clean at 173/173.

## Files touched

Lists come from the pre-polish file snapshots (`review/pre-polish/<project>.files`), the polish and preview-fix records, and the branch-update records in `state.json`. They were not re-derived from a `git diff` of the merge commits. The created/modified split follows git's ordering in the snapshots (untracked after tracked) for the bot and the web. For the service it follows the step records, because the service's new files were intent-to-add. Every project except migrations also committed `.plans/learning-loop.md` (created).

### tidewatch-migrations (PR #14, https://github.com/tidewatch-labs/tidewatch-migrations/pull/14, merge `8feeae3`)

- `migrations/20261028120100_learning_loop.sql` (created)
- `scripts/check-disposable-db.sh` (modified: +736/−40 at MIG2, then the L-between round trips in `d28de68`)
- `README.md`, `CLAUDE.md` (modified: the pin M, with L, K and J as history)

### tidewatch-bot (PR #17, https://github.com/tidewatch-labs/tidewatch-bot/pull/17, merge `2a3a412`)

- **Created:**
  - `packages/bots/src/learning/` sources, each with its `.spec.ts`: `calibrate`, `weights`, `meta`, `meta-gate`, `features`, `logistic`, `numeric`, `prng`, `draft`, `report`, `summary`, `store`, `metrics`; plus `ece.ts`, `feature-names.ts`, `net.ts`, `run.ts`, `runner.ts` (+spec), `schedule.ts`, `labels.ts` (+spec), `pg-store.ts`, `floors.spec.ts`, `logs.spec.ts` and `learning.int.spec.ts`;
  - `packages/bots/src/attribution-net-fixture.spec.ts`, `bot-version-v2-learned-fixture.spec.ts`, `testing/learning-memory-store.ts`;
  - `packages/bots/fixtures/attribution-net.v1.json` (C14) and `bot-version.v2-learned.json` (C15);
  - `packages/bots/fixtures/learning/`: `calibration-synthetic.v1.json`, `leakage.v1.json` and `thompson-seeded.v1.json`, with their `gen-*.mjs` generators; `service-calibration.json`; and `report-{draft,floors,realised}.golden.md`;
  - `packages/signals/src/post-mortem.ts` (+spec) and `prompts/post-mortem.v1.ts`.
- **Modified:**
  - `packages/bots/src/{index,metrics,pg-store,sizing,store,vocabulary,watch}.ts` and their specs (`metrics`, `sizing`, `vocabulary`, `logs`);
  - `packages/bots/src/general/{intake,manager,scout}.ts` (+specs), `general.int.spec.ts`, `testing/{index,memory-store}.ts`, `vitest.int.config.mts`, `fixtures/README.md`;
  - `packages/bots/src/pg-store.int.spec.ts` (branch update: the owner day sums learn runs);
  - `packages/shared/src/config.ts` (+spec);
  - `packages/signals/src/{index,prompt-versions,routes,store}.ts`, `prompts/versions.ts`, `testing/{index,memory-store}.ts`, and the specs `metrics`, `pg-store.int`, `pipeline.int`, `prompt-versions`, `prompts`, `routes`, `runner`, `memory-store`;
  - `packages/worker/src/serve.ts` (+spec) and `run.ts` (a polish comment on the pool size);
  - `scripts/sql-integration.sh` (pin M), `.env.example`, `README.md`, `CLAUDE.md`.

### tidewatch-service (PR #16, https://github.com/tidewatch-labs/tidewatch-service/pull/16, merge `3f8627a`)

- **New in this slice** (by the step records):
  - `internal/handlers/learning.go` (+test);
  - `internal/services/trading/{learning,extraction_export}.go` (+tests);
  - `internal/repository/postgres/learning.go`;
  - `internal/observability/metrics/learning.go`;
  - `internal/trading/{botconfig_learning,botversion_v2_learned,costrate_fixture}_test.go`;
  - `internal/trading/testdata/{attribution-net.v1,bot-version.v2-learned}.json`;
  - `test/integration/{learning,learning_save,learning_scope,learning_requests,learning_fixtures,learned_keys,extraction_export,compat_slice7}_test.go`;
  - `test/integration/testdata/{bots_summary,stats,stats_compare,stats_losses}_slice7.golden.json`.
- **Modified:**
  - `internal/platform/postgres/schema.go` (the pin M), `internal/pgtest/migrate.go`, `scripts/integration-test.sh`;
  - `internal/app/{router,router_test}.go`;
  - `internal/audit/{audit,audit_test}.go`;
  - `internal/handlers/{bots,bots_test,stats,stats_test}.go`;
  - `internal/observability/metrics/{metrics,metrics_test,trading}.go`;
  - `internal/repository/postgres/{bot,decision,stats}.go`;
  - `internal/services/trading/{botcreate,botcreate_test,bots,botversions,botversions_test,cursor,cursor_test,postmortem,postmortem_test,promote_test,promotion,promotion_test,schedule,schedule_test,stats}.go`;
  - `internal/trading/botconfig.go`;
  - `pkg/apperror/{apperror,apperror_test,codes,codes_test}.go`;
  - `test/integration/{main,ready,bots,bot_versions,events,post_mortem,promote,redaction,stats_fixtures,stats_losses}_test.go`;
  - `README.md`, `CLAUDE.md`.
- **Branch-update follow-ups** (`5400c5e`, `98211ab`, `c29d0f0`, `48f179d`): test and doc changes within the files above. They cover the audit order, the dismiss CSRF test, the learning handler tests signing in as role `user`, the learned-save tier check test, the M lookup and the merged route counts.

### tidewatch-web (PR #21, https://github.com/tidewatch-labs/tidewatch-web/pull/21, merge `de00a5f`)

- **Created:**
  - `src/app/pages/workspace/feat-bots/bot-learning.ts` (+spec);
  - `feat-bots/util/learning-view.ts` (+spec);
  - `src/app/pages/workspace/data/testdata/bot-version.v2-learned.json` (C15);
  - `e2e/src/bots-learning.spec.ts`.
- **Modified (app):**
  - `src/app/pages/workspace/data/{bot-config.model,bots-api.service,bots.model,stats-api.service,stats.model,trade.model}.ts` (+specs);
  - `feat-bots/{bot-detail,bot-dialog,bot-version}.ts` (+specs), and the specs `bot-candidates`, `bots-list`, `bots`;
  - `feat-bots/data/{bot-editor.service,bots.service}.ts` (+specs);
  - `feat-bots/util/{bot-dialog-view,bot-draft,bot-view,watch-view}.ts` (+specs);
  - `feat-stats/losses-list.ts`, `feat-stats/util/stats-view.ts` and `feat-stats/data/stats.service.ts` (+specs), and the specs `calibration-plot`, `compare-panel`, `kpi-row`, `losses-panel`, `stats-equity-chart`, `stats`;
  - `feat-trade/util/order-view.ts` (+spec);
  - `src/styles/components/{bots,stats}.css`;
  - branch update `f2ee96c`: `src/app/pages/admin/data/admin.model.ts` (+spec) and `src/app/pages/admin/feat-audit/audit.spec.ts`.
- **Modified (e2e):** `e2e/playwright.config.mts`, `e2e/src/support/{bots,screens,stats}.ts`, `e2e/src/{a11y,bots,bots-editor,stats}.spec.ts`.
- **Docs:** `DESIGN.md`, `README.md`, `CLAUDE.md`.
- **After the PR opened:**
  - `3cb3fb4`: e2e only (`bots-learning.spec.ts`);
  - `13d1267` (PF1): `bot-learning.ts`, `learning-view.ts`, `stats-view.ts`, `losses-list.ts` (+specs), `bots.css`, `stats.css`, the e2e mocks and specs (`draft-gate-closed`, the Stats scroll-to-top, the `dialog p.clone-strategy` selector), `DESIGN.md`, `CLAUDE.md`;
  - `864714c`: `DESIGN.md` and a wait in a Stats keyboard test;
  - `568002f`: a merge of `main`, bringing #24 (favicon) and #25 (the `app-dialog` reopen race), with no learning-loop change.

## Test plan

### Commands (each project root; CI runs the first of each)

- **Migrations:** `make migrate-validate` (15 files); `make check-disposable-db` ends `check-disposable-db: PASS` (4,153 PASS, 0 FAIL after the branch update).
- **Bot:**
  - `pnpm nx run-many -t lint test typecheck build` (9 projects; bots 536 unit tests at the final head);
  - `TIDEWATCH_MIGRATIONS_DIR=<tidewatch-migrations checkout at M> bash scripts/sql-integration.sh`. It refuses to run without L and M applied, logs `required schema version: 20261028120100 (learning_loop) applied`, and its int specs include bots 61 (learning among them);
  - the titles are asserted with `node scripts/assert-vitest-titles.mjs`.
- **Service:**
  - `make ci` (vet, both tags → test-race → build);
  - `make test-integration TIDEWATCH_MIGRATIONS_DIR=<checkout at M>`. Its known flake is the `freePort` bind race under host load; re-run it.
- **Web:**
  - `pnpm nx test tidewatch-web` (6,995 tests at `568002f`), `pnpm nx lint tidewatch-web`, `pnpm nx build tidewatch-web`;
  - the e2e lint and `tsc -p e2e/tsconfig.json --noEmit` (29 known errors, none new);
  - the literal-colour and zone-token greps;
  - on a stack: `pnpm exec playwright test -c e2e/playwright.config.mts --grep-invert @hook`, one worker.

### Named acceptance tests (do not rename)

- **Bot (exact Vitest titles, selected):**
  - "takes learn requests only", "bots runner ignores learn", "due on the first of the month 03:00 Bangkok", "a new version resets the clock", "collapses missed slots into one run", "runs a requested bot as manual before due bots";
  - "a bot under every floor still succeeds with a report and no draft";
  - "halves the out-of-sample ECE on the synthetic over-confident set", "keeps the Platt fallback within 60 % on 120 rows";
  - "applies the calibration map", "unlearned version is byte-identical";
  - "reproduces the seeded interval byte for byte";
  - "never sees a future bar", "opens the gate on two folds within a 90-day window", "closes the gate with fewer than two folds", "stays within 0.40 to 0.60 on the leakage set with the guards", "exceeds 0.90 on the leakage set without the guards", "purge margins cover every calendar's horizon";
  - "meta veto is a verdict not a decision", "shrinks the budget", "never increases size", "direct entry is exempt";
  - "writes post_mortem only where null", "stops at the bot's daily share and leaves the rest waiting", "charges a schema failure and leaves the decision unlabelled", "sends no key, body or URL in the prompt";
  - "round-trips a draft against C15";
  - "words helped, did not help and made it worse";
  - "never logs a sentinel rationale";
  - "pins the C15 fixture's SHA-256", "agrees with every C14 net-return case";
  - "sums scout and learn runs into the bot's day";
  - Integration: "floor not met writes a report and no draft", "supersedes the pending draft", "proposes where null, skips where the owner labelled", "stops at the bot's share", "bots runner never takes a learn request (sql)", "pg store on M: bot cost today", "sweeps an interrupted learning run".
- **Service:**
  - `TestLearning_ScopeAndNotFound`, `TestLearning_Status`, `TestLearning_RunsPaging`, `TestLearning_Report`, `TestLearning_SavedLabel`, `TestLearning_Dismiss`, `TestLearning_ReadsInSnapshot`;
  - `TestVersions_SaveDraft`, `TestVersions_SaveDraft_Refusals`, `TestVersions_SaveDraft_Races`, `TestVersions_LearnedForcesProbation`, `TestBots_CloneLearnedForcesProbation`;
  - `TestPostMortem_ConfirmProposal`, `TestPostMortem_ChangeProposal`, `TestStatsLosses_ProposedFilter`, `TestStats_PostMortemCounts_Proposals`;
  - `TestPromote_LearnedNotComparable`;
  - `TestExport_ExtractionErrors_OnlyConfirmed`, `TestExport_Shape`, `TestExport_Scope`, `TestLearningHandler_ExportCutFailsTheRead`, `TestLearningHandler_ExportCutThroughWrappedWriter`;
  - `TestLearned_AdditiveKeys`, `TestBots_Summary_Compat`, `TestStats_Version_Compat`, `TestStats_Compare_Compat`, `TestStatsLosses_Compat`;
  - `TestBots_LearnRowsInvisible`, `TestBots_RunLearn`, `TestBots_RunLearn_Legacy`;
  - `TestValidateConfigV2_Learning`, `TestBotVersion_V2LearnedFixtureHash`, `TestBotVersion_V2FixtureHash`, `TestAttributionNet_Fixture`;
  - `TestReady_LearningSchema_NotReady`, `TestContract_RequiredSchemaVersion`;
  - `TestCodes_Contract`, `TestRouter_ForcedChangeGatesNewRoutes` (70), `TestRouter_NoDecisionMutation`, `TestAudit_LearningEvents`, `TestMetrics_LearningDraftsSeries`, `TestMetrics_RunRequestLoops`, `TestLogs_NoBotTextOrConfig`.
- **Web:** Vitest `bot-learning.spec.ts`, `learning-view.spec.ts`, `bot-config.model.spec.ts` (C15 sha256 `977068bf…`), `losses-list.spec.ts`. The e2e titles carry the `FR-LL-*` ids, for example "FR-LL-WEB-001 requests a learning run".

### Results (from `verification.md` and the `state.json` branch-update and preview records)

**Acceptance status: 43 IDs; 40 verified, 2 partial, 1 unverified, 0 failed.**

| Area | Result |
|---|---|
| FR-LL-MIG-001…003 | verified (harness; M as PRD §5.1; probes by constraint name; loud-failure down) |
| FR-LL-BOT-001…013 | verified (unit and SQL-integration titles). BOT-003 carries the recorded 120-row reading; BOT-006 is verified against the corrected spec (two folds, 7/14/39) |
| FR-LL-SVC-001…011 | verified (integration on the post-polish tree: 897 PASS, 0 FAIL, 0 SKIP; after the branch update `make ci` and integration on L+M were green) |
| FR-LL-WEB-001…006, 008 | verified (Vitest, the Playwright runs on the preview, rendered captures, axe, contrast and keyboard) |
| FR-LL-WEB-007 | **partial**: there is no capture of the Checks' `meta_veto` words or of a shrunk entry's second line. Verified: the not-comparable line, the aria-disabled Promote, "· learned version", "· learned", the real refusal wording (E2E-004) and the Watch's "vetoed by the failure model" on the real service (E2E-002) |
| FR-LL-E2E-001, 002, 004, 005, 006 | verified on the preview (below) |
| FR-LL-E2E-003 | **partial**: the model half is unverified, because the preview's OpenRouter key was refused on every call. The downstream half is verified on three SQL-seeded proposals |
| FR-LL-DOC-001 | verified (READMEs, `CLAUDE.md`s, `DESIGN.md`, PR diffs) |
| FR-LL-DOC-002 | **unverified, recorded deferral**: `tidewatch-apis` is not a git repository; the collection was not regenerated (as in slices 6 and 7). The service README documents the shapes |

**Brief acceptance.**
- BA-1 (≥ 50 % ECE cut): verified on synthetic data (0.1371 → 0.0444) and on the preview (0.1465 → 0.0292).
- BA-2 (no future bar; AUC per fold): verified on the leakage set, 0.5000 with the guards and 0.9574 without.
- BA-3 (weights always a draft; diff plus Save as vN): verified.
- BA-4 (labels counted only once confirmed): verified for the counting and the list. A model-written proposal was unverified.
- BA-5 (the export holds only confirmed labels): verified.
- BA-6 (the API refuses an unproven learned challenger): verified.

**Assumptions (PRD §11).**
- A1: holds; `model_calls.document_id` is nullable.
- A2: holds; the five constraint names are as listed.
- A3: **failed as written**; corrected to 7/14/39 with the owner's acceptance.
- A4: holds; Newton converged in 6–7 iterations.
- A5: verified; the real `a[download]` saved the service-named file byte-identical.
- A6: **partial**; the mocked schema-failure case is verified, but 0 real Haiku replies came back.
- A7: verified; C14 agrees.
- A8: **unverified**; no ten-bot pass was timed.
- A9: verified (`TestVersions_SaveDraft`).

### Preview runs (per-run isolated database `forge-0199b29a-ll-f3bdc8b0`)

| Run | Build | Result |
|---|---|---|
| PV1 (Playwright, `--grep-invert @hook`, journey and sign-out skipped) | web `b84fd55` at M | 1,706 passed, 4 failed (e2e test defects F-PV1-1 relative href and F-PV1-2 un-routed `a[download]`, fixed in `3cb3fb4`), 4 skipped (live gates). Slice-8 measures: 210 captures, no overflow, axe 0 over 40 runs, contrast ≥ 4.79:1 |
| PV1b | `3cb3fb4` | `bots-learning.spec.ts` 198/198 |
| PV4 (seeded E2E-001…006, user `pv4-learning`) | bot `de9ff78`, service `0c140c4`, web `b84fd55` | 5 passed; E2E-003 model half unverified. Found the closed-gate draft display defect, fixed in PF1 |
| PV2 (rendered design review) | `b84fd55` | CHANGES REQUESTED (SF-PV2-1…3) → PF1 `13d1267` with OD-PV2-1 and OD-PV2-2 |
| PV1c | `13d1267` | 1,173 passed, 2 intermittent: F-PV1-3, a test race fixed by waiting for Promote (PV1e: FR-ST-WEB-014 30/30); F-PV1-4, toast timing (follow-up) |
| PV1d | `13d1267` | `stats.spec.ts` 346/346 |
| PV2 round 2, PV3, PV5 | `13d1267` | APPROVED (0 blocking, 0 should-fix, 2 nits). Keyboard, axe and contrast verified (slice-8 minimum 4.85). `forge-setup-impeccable --check` 173/173 |
| PV6 (whole suite, all projects, one worker) | web `f2ee96c`, bot `435feb4`, service `48f179d`, migrations `d28de68`; L applied out of order with `goose -allow-missing` | 2,260 passed, 3 failed, 4 skipped in 37.5 min. Two failures were slice-6 `bots__stale-*-1440` toast captures under load, which passed 6/6 in isolation. The third was `signals.spec` "opens Add source and returns focus": a pre-existing race in the shared `app-dialog`, identical on `main`, later fixed by web #25 (now in the PR head `568002f`) |
| PV6 real stack | same | `pv4-learning` (role `user` after L) read the learning status and runs. Dismiss → 200, then 409 `draft_not_pending`. One `learning_draft_dismissed` event with `actor_user_id`, shown by `GET /admin/audit?type=learning_draft_dismissed` and on `/admin/audit` in both themes. `GET /admin/spend` 200 |
| PV6 database | same | The learning runner made 4 passes with no failure. `LEARNING_BOTS` read 3 of 3 eligible bots with `daily_model_usd 0.500000`. `OWNER_COST_FOR_DAY` = 0.000029, the expected scout + learn sum. Learn inclusion is proven by the int specs, because the preview's learn runs cost $0 |

**What each seeded E2E showed (PV4, 2026-10-28 17:04–18:03Z).**
- **E2E-001.**
  - Setup: PV4 Calib, tier `jev`, 2,000 graded over-confident proposals.
  - *Run learning now* on screen → manual run `01a18381…`. The days isotonic map cut the out-of-sample ECE 0.1465 → 0.0292 (0.199 × raw); Platt reached 0.0431 and was not chosen. The draft diff showed on screen.
  - *Load into editor* → *Save as v3* gave v3·1a2c learned and observing, with probation to 27 Nov. Its `learning` equals the draft's byte for byte, with `bot_version_created {seq 3, learned_from_run, draft_modified false}`.
  - The next scout wake on a real BTCTHB setup wrote `model.p 0.597`, `p_raw 0.730`, `calibration {isotonic, days, run}` and `candidates.p 0.597` (the map's interpolation is 0.596632).
- **E2E-002.**
  - Weights stayed within [0.05, 1.00] and ±0.25.
  - Gate open on two separable sets (AUC 0.8624, 0.8396) and closed on the noise set (0.5481, reason `auc`). Both sets had two folds in an 88-day window.
  - An entry on the learned version recorded `policy_result.meta {effect none, p_loss 0.0232}`. The high-`p_loss` candidate was `gated ["meta_veto"]` with no decision, and the Watch read "Gated · vetoed by the failure model".
  - A first attempt seeded `atr_pct` on the wrong scale; the engine writes it in percent. That was a seed error, not a product defect.
- **E2E-003.**
  - 12 candidate losses produced 12 `post_mortem` calls, all refused by OpenRouter (4xx other than 429, 0 tokens, $0). `learning_model_stage_failed … DecideRejectedError` was logged ×12. The same route had failed every `extraction` call on that preview since 15:28.
  - Downstream, on 3 SQL-seeded proposals (`model_id 'pv4-seed-no-model-call'`):
    - `by_labeller {user 2, model 0, proposed 3}`;
    - *Proposed only* showed the rationale;
    - *Confirm* → `{labelled_by: model, confirmed_by_user: true}`, the counts moved 0 → 1 and 3 → 2, with audit `confirmed_proposal: true`;
    - a second PUT → `409 post_mortem_frozen`.
- **E2E-004.**
  - With 10 graded proposals, promote → `409 promotion_refused [return_not_higher, calibration_not_comparable, not_active]` and the panel worded it.
  - With 35 graded it was judged on ECE (0.1685 vs 0.1015 → `calibration_worse`).
  - `bots.champion` was unchanged.
- **E2E-005.** The export had 4 lines, equal to the SQL count of confirmed `signal_wrong` entries with a joinable signal. Excluded as specified: 2 unconfirmed proposals, 1 `signal_late`, and 1 confirmed entry without a snapshot. `jq` showed the §4.10.5 key order on every line.
- **E2E-006.**
  - PV4 Scheduled (observing; version from 2026-09-20) got a `scheduled` run that succeeded. Calibration floor met (300/150); weights 0/100 and meta 0/150 not met.
  - Days isotonic 0.0585 → 0.0548 was not proposed (not ≤ 80 %), so there was no draft. The report was 1,110 bytes.
  - *Download report* in Chromium saved `learning-pv4-scheduled-2026-10.md`, byte-identical to `learning_runs.report`.
- **Paid calls.** Jev `bot_decide` 1 call, $0.000029. OpenRouter 13 refused calls, $0.

### Not verified or partial (stated separately)

- **A model-proposed post-mortem**, in any environment (E2E-003 model half, A6).
- **FR-LL-WEB-007:** no capture of the Checks' `meta_veto` words or a shrunk entry's second line.
- **A8:** no ten-bot pass was timed.
- **FR-LL-DOC-002:** deferred.
- **The realised calibration line on real data.** It needs a learned version to run for a month; it was proven only on seeded data (O1's realised half is unverified by design).
- **Playwright on the merged web head `568002f`.** Not re-run. Unit, lint and build were green; the head adds only `main`'s #24 and #25.
- **PV3 gaps:** touch and real devices, screen readers, Safari and Firefox, widths 601–1079, Confirm by keyboard, and the "Remove → heading when unchanged" branch.
- **Production after deploy.** Verified only by `/info`, `/ready`, the bot's ready state and its learning collector log, the live bundle, and the unauthenticated 401. No learning run has been requested in production, and no scheduled run has happened yet.
- **M's Down** ran only in the disposable harness.

### Manual reproduction (production)

1. Sign in at `https://tidewatchtrade.com/sign-in` and open a v2 auto bot's detail. A legacy v1 bot (Slack Water) shows the legacy sentence and no button.
2. Expect the *Learning* section between Candidates and Version, with "Next run Sun 1 Nov, 03:00" (or the bot's next slot) and *Run learning now*.
3. Press *Run learning now*. Expect *Queued…*, then within about one pass (60 s) the toast "Learning ran at {HH:mm}: {result}". On today's thin data the result is likely "floors not met" or "nothing to propose".
4. *Download report* should save `learning-{bot-slug}-{YYYY-MM}.md`.
5. On the bot's metrics, watch `learning_runs_total{result}`, `learning_pass_duration_seconds` and, if the bot has closed losses, `learning_model_calls_total{stage="post_mortem"}` and `learning_model_cost_usd_today`.
6. A `learning_model_stage_failed` with `error_class DecideRejectedError` means OpenRouter refused the call (see Open questions).
7. After 2026-11-01 03:00 Bangkok, expect one `scheduled` run per eligible bot.

## Open questions

### Owner actions still open

- **Check the OpenRouter key.**
  - Production labelling uses the `post_mortem` route on OpenRouter Haiku, as does production `bot_thesis`.
  - The preview's OpenRouter key was refused on every call (extraction, `post_mortem`, `bot_thesis`).
  - If production shares that key, labelling will not run there. Each attempted loss logs `learning_model_stage_failed`, is charged $0, and waits for the next run.
  - After the key is checked, re-run one learning run on a bot with closed unlabelled losses to close FR-LL-E2E-003's model half and A6.
- **Watch the first scheduled production run,** due 2026-11-01 03:00 Bangkok. PRD §8.4 expects Driftline, which is observing on probation, to report floors and at most a calibration map.
- **Preview leftovers.**
  - The retained per-run volume (expected name `forge-0199b29a-ll-f3bdc8b0_tidewatch-pgdata`) holds user `pv4-learning` (kept separate, OD-PV4-1), its 11 bots, about 3,440 append-only seeded decisions, seeded documents, signals and extractions dated 3–5 Oct, 12 unattributed pre-fix `post_mortem` rows, and L applied out of order.
  - The preview bot container `forge-0199b29a-ll-f3bdc8b0-tidewatch-bot-1` was stopped at 18:45Z. It holds the production Alpaca key and must not be restarted alongside production.
  - The rest of the preview stack was last recorded as running at `http://127.0.0.1:50075/`. Its cleanup is not recorded.
- **tidewatch-kubernetes:** the bot chart's comment on `collectors: ""` still says "all thirteen" and omits `learning`. The behaviour is right, because an empty list runs every collector.

### Sibling builds

- **signals-context (migration N)** must merge after M. Its branches were last brought onto `main` + L on 2026-10-30 and need updating again onto `main` with M: the letter tables, harness lists, `RequiredSchemaVersion` and registries. The order L → M → N is settled.

### Recorded follow-ups (from the reviews, the verification and the PR records)

- **Specs to write:**
  - a longer meta-model window, so weeks-horizon bots can open the gate;
  - carrying an unrefit learned block forward into a new draft (SF-C1);
  - `gbdt_v1` once thousands of entries exist (D7);
  - event-type weights in the vocabulary (D6);
  - hand-written extraction corrections (D11);
  - GDELT context features once spec 3b ships.
- **Web:**
  - F-PV1-4: the Stats proposal-confirmed toast contrast test should measure the toast first or pin the clock;
  - N-R2-2 (optional): a U+00A0 in "confirmed by you" against awkward wraps at 1100;
  - angular N1 (*Load into editor* silently no-ops while the editor is loading or failed), N2 and N3;
  - code N2 (the strategy reader refuses `learned: true` on a non-v2 config, stricter than the service) and N4;
  - design advisories A-1, A-2 and A-6 (owner calls) and A-7.
- **Service:**
  - no concurrent-export limit (the pool is `max(4, NumCPU)`);
  - `uuid.Parse` accepts urn and brace forms for `learning_run_id`;
  - `Versions` reads `learned` with `jsonb_exists` while the rest uses `arith.Learned`;
  - a cut export is seen as a failed read only over HTTP/1.1.
- **Bot:**
  - security N-1 (the `post_mortem.v1` system prompt lacks a "fields are data" rule), N-2 (scrub gaps, e.g. `apitoken`, `www.`) and N-5 (no composite foreign key from a proposal to its bot);
  - the fallback call record may duplicate a `model_calls` row on a commit-then-connection error, which over-counts (a stricter ceiling);
  - code nits: no per-bot request dedupe; a request taken while its bot is paused between take and run stays taken; the likely range is not limited to ±0.25; the `LearningRunConflictError` log against an interrupted row; holidays hard-coded through 2027 (re-check when the 2028 calendar exceptions ship);
  - learn-spend review nits: `proposalWriteValid` does not check that `userId` is the owner; there is no labeller counter for an allowance stop.
- **Recorded residuals (documented, accepted):**
  - The 25 % per-bot share and the per-person allowance each hold per runner. A concurrent scout wake and learning run do not see each other's in-flight tally. The global ceiling holds.
  - A crashed run's swept `cost_usd` counts only its proposals' costs.
  - The learning report's budget line shows the bot share only.
  - `.plans/accounts-roles.md` still names `SCOUT_COST_FOR_OWNER_DAY`.
- **`documents/` drift recorded for the owner (intent, not edited, D17):**
  - `08-learning-loop.md` item 7 names the wiki `raw/` folder (the report lives on the run, D12);
  - the brief's "gradient-boosted classifier" (D7 starts with logistic);
  - `02-architecture.md` §11 lists a `post_mortems` table (post-mortems live in `decisions.post_mortem`; `post_mortem_proposals` holds only the rationale).
- **`tidewatch-apis`:** the six routes and changed bodies may get an api-spec-generator pass (FR-LL-DOC-002).

## Cross-cutting links

- [[bots]]: the slice overview this feature extends. The Learning section on the bot detail, the editor's learned block and the clone lock.
- [[bots-engine]]: the fourteenth collector `learning`, the scout's calibrated `p` with `p_raw`, the manager's `meta_veto` and shrink, the bots runner's `learn` filter, `BOT_COST_FOR_DAY` and `OWNER_COST_FOR_DAY`.
- [[bot-versions-and-runs]]: Save as vN of a draft, forced probation (also on clone, R12), the optional `learning` key and C15, `learned` on versions, and `learn` as the fourth loop on `bot_runs` and `bot_run_requests`.
- [[bot-watch-verdicts]]: `meta_veto` as a `gated` reason (C11' unchanged).
- [[decision-record]]: `model.p_raw` and `model.calibration` on learned versions, `policy_result.meta`, and the first `labelled_by: "model"` writer of `post_mortem`.
- [[statistics]] and [[stats-read-api]]: the provenance rule on the PUT, `LossRow.proposal`, `proposed=1` with cursor `M`, `calibration_not_comparable`, and `version.learned`.
- [[model-routes-and-spend]]: the `post_mortem` stage and route, `post_mortem.v1`, attribution of labelling calls to bot and owner, and learn spend under the 25 % share and the person's allowance (OD-LEARN-SPEND).
- [[signals-pipeline]]: the optional `post_mortem` route in the signals readers; a bad row no longer stops the pipeline (SF-C2).
- [[centralized-migrations]]: migration M (`20261028120100`), the pin L → M, and the L → M → N order. A migrate-image-only GitOps bump does not sync, a lesson confirmed a second time.
- [[accounts-and-roles]] and [[operator-console]]: role `user` on the learning routes, `learning_draft_dismissed` as the 35th audit type, and labelling spend shown as the owner's on Spend.
- [[market-data-worker]]: one Alpaca stream connection per key; a preview bot on the production key took production's stream (operational lesson).
- [[design-system-decisions]]: `.learning-tables`, `.learning-actions`, OD-PV2-1, OD-PV2-2 (amends PRD §7.4) and the LL-W decisions.
- [[forge-preview-gateway]]: the per-run isolated, retained preview database; L applied out of order on it; preview containers must not share production keys.
- New page the build prompt names for this pass: `learning-loop` (the overview, replacing the planned `learning-loop-plan` page).
