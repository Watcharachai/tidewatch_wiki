# Bots engine: the general engine (scout, manager, guard)

**Summary**: Since slice 6 (tidewatch-bot #10, merged 2026-10-21 as `81133bf`, not deployed), the bot's `bots` runner runs two engines. A config that is exactly the C10 v1 config runs the unchanged 2b zone pass (see [[zone-transition-bot]]). A `bot-config.v2` config runs the **general engine** in `packages/bots/src/general/`, with three loops per bot: the **scout** proposes candidates and never orders, the **manager** enters and manages positions on closed bars through the bot-side intake, and the **guard** checks stops, invalidation, daily loss and exposure on every 30 s pass. Each bot is evaluated under its own advisory lock. *Run now* reaches the bot through the `bot_run_requests` table, never HTTP. Candidates live in migration J's `candidates` table and follow one lifecycle: `proposed → watching → entered → closed`, or `expired`. Model calls (`bot_decide`, `bot_thesis`) run on the signals router, ledger and ceiling, are bounded so the guard is never starved, and since FU-1 are also held to a **per-bot daily budget** of 25 % of the shared ceiling. The engine's Elliott and regime facts come from `packages/waves`, a byte-identical TypeScript port of the service's labeller. **Slice 7 (statistics, merged and deployed 2026-10-27) changed nothing in the bot.** Stats grades what the engine writes: the scout's stated `p` on `propose` decisions, graded at the candidate's horizon; entries and adds for attribution and losses; and each wake's `bot_runs.counts.cost_usd` as the cost of decisions. **Since accounts and roles (tidewatch-bot #19, merged as `bd5e435` and deployed 2026-10-29),** the evaluated-bots read joins `users` and `plans`. Each wake holds the owner to the plan's **daily allowance** (S16), after the per-bot budget and before the global ceiling. A stored tier the plan excludes runs the whole wake as `none` (S15). The engine stamps `bot_id` and `user_id` on every model call it records. **Since the learning loop (slice 8; tidewatch-bot #17, merged as `2a3a412` and deployed 2026-10-30),** a separate `learning` runner sits beside the bots runner, and the bots runner never takes a `learn` request. On a **learned** version (a config with a `learning` block) the scout states the calibrated `p` and keeps `p_raw`, and the manager's failure gate can veto an entry (`gated`, `meta_veto`) or halve its size, never raise it. The per-bot and per-person day spends now sum scout **and learn** runs (`BOT_COST_FOR_DAY`, `OWNER_COST_FOR_DAY`). See [[learning-loop]]. **Since signals context (tidewatch-bot #18, merged 2026-10-30 as `b083697`; deploy triggered, not verified),** the scout has two optional discovery paths beside signal and setup: **context-driven** (an instrument's coverage z ≥ `z_min`) and **calendar-driven** (earnings within `sessions_ahead` sessions). They are off unless a version sets `schedule.scout.discovery`. Both enter the unchanged rank-and-cap step before any model call. Every `propose` decision now carries `market_state.context` and `market_state.calendar`, and **coverage signals (`origin = 'context'`) are never read as triggers**.

**Sources**: `raw/2026-10-21-bots.md`; `raw/2026-10-27-statistics.md` (what Stats reads from the engine only); orchestrator note of 2026-10-21 (FU-8 only); `raw/2026-10-29-accounts-roles.md` (the plan join, S15, S16 and attribution only); `raw/2026-10-30-learning-loop.md` (the `learn` filter, the learned scout and manager, and the day-spend reads only); `raw/2026-10-30-signals-context.md` (the discovery paths, the origin filter and `bot_thesis.v2` only)

**Last updated**: 2026-10-31

---

## Why a second engine beside the 2b pass (S1, D8)

Slack Water's v1 must keep working byte for byte (outcome O7), and the new vocabulary needs loops the 2b pass does not have (a scheduler, a per-bot lock, candidates, a guard). So the runner dispatches each bot by the vocabulary of its current version. The 2b files are byte-identical to `ece175a` (bot code review r3), and the 2b named specs ("enters once on a buy transition", "baseline at status_since", "exits on sell", "replay after crash") stay green and unrenamed. Without the worker's general dependencies, the 2b `runPass` runs alone (source: raw/2026-10-21-bots.md §Concept, Spec decisions S1; §Concept, Owner decisions D8; §The bot engine; §Test plan, Named acceptance tests).

## Pass order (`runEnginePass`)

Every `BOTS_EVAL_INTERVAL_MS` (30 s) under `runner:bots`; passes never overlap.

1. **Take the run requests** in one statement (`takeRunRequests`).
2. **End due probations** (`endProbations`), in its own statement: `observing` bots whose `probation_until <= now()` become `running` with `status_since = now()` and `probation_until = NULL`. It writes `probation_ended` and `bot_status_changed {observing → running}` with a null actor.
3. **Read the bots to evaluate:** `kind = auto`, `status IN (running, observing)`. Since accounts and roles, the read (`EVALUATED_BOTS`) inner-joins `users` and `plans`, which drops no bot, so each row also carries `ownerUserId`, `dailyModelUsd` and `decisionTiers` (see below).
4. **Evaluate each bot under its own lock** (S19). The lock is `bot:<bot_id>`, taken with `tryLock` on the `LockSession` that holds `runner:bots`, outside any transaction, and released in a `finally`. It uses no pooled connection, so `SERVE_POOL_MAX` stays 12. A bot whose lock is held elsewhere logs `bots_lock_busy` and is skipped; its taken requests wait in memory.
5. **Dispatch by vocabulary** (`dispatchVersion`, reading `current_version` once per bot per pass):
   - `legacy` (exactly the v1 config): the unchanged 2b evaluation;
   - `general` (accepted by `readConfigV2` and hashing to `current_version`): guard, then manager, then scout (when due or requested);
   - anything else is `unsupported`: one `failed` run per (bot, version) per runner run, as in 2b (see [[bot-versions-and-runs]]), and a run request gets one `failed` manual run.

**Start-up.** Before the first pass, runs left `running` for more than 5 minutes are finished `failed`, `error = interrupted`, with **their own loop's** zero counts (GAP-B3, fixed in review), and every request taken before this start without a run is released (`releaseRunRequests(now)`) (source: raw/2026-10-21-bots.md §The bot engine, Pass order and Start-up).

## Scheduler (PD7, S23)

- **`times`:** `next_wake` is the next configured `HH:MM` in Bangkok strictly after the newest scout run's `started_at` (else `status_since`). Missed wakes collapse into one.
- **`signal_driven`:** a wake is due when a qualifying signal arrived after the last scout start and that start was at least 5 minutes ago.
- **`off`:** never.
- A paused bot is not evaluated, so it never wakes.
- The default (PD7) is wakes at 06:00 and 20:00 Bangkok with `min_impact` 0.45, and a 1h manager with events on.

(source: raw/2026-10-21-bots.md §The bot engine, Scheduler; §Concept, Owner decisions PD7)

## Run requests (*Run now*, S10)

The service inserts a `bot_run_requests` row (`loop` scout, manager or guard); a partial unique key allows one pending request per bot and loop. The bot takes pending requests at the start of each pass, writes `taken_at` and `run_id`, and runs that loop once as a `trigger = manual` run. A request is `stale` to the service when untaken for 10 minutes or more. There is no HTTP between the service and the bot. The service-side checks and the FU-1 rate limit (6 per bot and loop per rolling hour) are on [[bot-versions-and-runs]] (source: raw/2026-10-21-bots.md §Concept, Spec decisions S10; §Database, New tables and Who writes what; §API, Behaviour worth knowing, Schedule).

## Scout (PRD §4.4; `scout.ts`, `models.ts`)

1. **Universe.** The resolved universe for the class, minus instruments the bot holds or has a live candidate on, resolved once per evaluation. Classes (S2): `stock` on the `set` calendar is `th_stock`, any other `stock` is `us_stock`, `crypto` and `gold` are themselves, and `fx` is never in a universe (see [[instrument-master]]).
2. **Signal-driven candidates.** `up` signals in the window (since the previous scout run's `started_at`) with a weighted impact ≥ `scout.min_impact` and a horizon in `policy.horizons`, grouped per instrument (at most 20 signal ids). A `down` signal over the threshold writes a `propose` decision with `direction = short`, reason `long_only` and no candidate (D12).
3. **Setup-driven candidates.** Universe instruments whose strip zone run began after the previous wake and reads `buy` or `pre_buy_2`.
4. **Rank and cap before any model call (S4).** Score `impact_w × allocation[class]`. Instruments with no venue rule or price feed, or whose class has reached `max_symbols` (held and live-candidate instruments counted once each), are dropped, as are instruments with a null `ttl_until`. Then `max_candidates[class]` survivors are kept per class. Since FU-1 the caps are bounded at 10 candidates and 20 symbols per class.
5. **Decide**, unless the tier is `none`: one `bot_decide` call per survivor; the candidate's `p` is the tier's answer.
6. **Thesis**, unless the tier is `none`: one `bot_thesis` call (strict JSON, at most 240 characters, prompt `bot_thesis.v1`). On any failure, a ceiling refusal or a budget refusal, the thesis is a template sentence with `thesis_source = template` (S17). Tier `none` makes no call at all, the thesis included (ORCH-8).
7. **Market state and levels.** `market_state` carries `elliott` and `regime` from `packages/waves` on the manager timeframe. `invalidation_px` is the first ranked bullish candidate's invalidation, else `close − stop_atr × atr14`. `ttl_until` is `ttl_sessions[class]` sessions ahead on the instrument's calendar (default 5 sessions for stock and gold, 3 days for crypto, D5).
8. **Write, one transaction per survivor:** the `propose` decision, the candidate (`proposed`), and `instruments.realtime_requested_at` for an instrument off the watchlist (S12).

The scout never reads money and never places an order (source: raw/2026-10-21-bots.md §The bot engine, Scout; §Concept, Spec decisions S2, S4, S17, S23; ORCH-8).

**Since signals context (2026-10-30)**, steps 2 and 3 have two optional siblings, the context and calendar paths, and the signal reads in step 2 count only `origin = 'document'` signals. See "Discovery paths" below.

## Discovery paths: context and calendar (signals context, 2026-10-30)

Slice 6 kept two of the scout's four discovery paths reserved "until spec 3b" (D10). Signals context (tidewatch-bot #18, merge `b083697`) built them in `packages/bots/src/general/scout.ts` (PRD §4.10). They run only when the version sets `schedule.scout.discovery` (see [[bot-versions-and-runs]]).

- **Context-driven** (`discovery.context {enabled, z_min}`). A scope instrument qualifies when its newest feature row in `(startedAt − 24 h, startedAt]` has a non-null `articles_z ≥ z_min`. It attaches the day's coverage signal through `CONTEXT_SIGNALS_ON`. That read is keyed on the canonical URL of the wake's Bangkok day (S17), not on `created_at`. Features and coverage signals are on [[context-features-and-coverage-signals]]. Class rows are never used.
- **Calendar-driven** (`discovery.calendar {enabled, sessions_ahead}`). A scope instrument qualifies with an `earnings` row within `sessions_ahead` sessions on its own calendar. **Stocks only;** crypto and gold never qualify. See [[event-calendar]].
- **Ranking.** Both paths enter the unchanged rank-and-cap step (S4) with `impact_w = min_impact`, `p = null` and `horizon = days`. So a signal-driven survivor outranks them at equal allocation. An instrument qualified by several paths is one candidate. `policy_result.discovery` lists its paths in the order `signal`, `setup`, `context`, `calendar`, with `context_z` for context.
- **Theses.** Survivors without a signal get template theses: `Coverage {z:.1f}σ above its 30-day baseline (...)` and `Earnings {EEE d MMM} (...)`.
- **Decision context.** Every `propose` decision carries `market_state.context` (`{ts, articles_24h, articles_z, tone_mean_24h, tone_z, countries_24h, publishers_24h, context_version}` or null) and `market_state.calendar` (`{next_earnings, next_macro}`). See [[decision-record]].
- **Run counts.** `bot_runs.counts.by_discovery {signal, setup, context, calendar}`.
- **Manual runs.** A manual scout request on `scout.kind = off` runs setup plus the enabled discovery paths.
- **The read model is required.** `worker/serve.ts` wires `BotsRunnerGeneralDeps.createContextReadModel` as a required dependency (PB17), so the paths cannot silently never run.
- **Never a trigger (PRD §4.7, PD11).** The trigger reads `SIGNALS_SINCE`, `SIGNALS_SINCE_ON` and `QUALIFYING_SIGNAL` (the scout window, the `signal_driven` due check, and the manager's events, adds and trims) filter `origin = 'document'`, and the memory store mirrors them. So does `LATEST_SIGNAL`, the signals novelty read, since S17. With any `min_impact`, including 0, a coverage signal never qualifies, never writes a `long_only` refusal, never wakes a bot and never triggers an add or trim.
- **Production.** The paths stay off for every bot until a version sets the key. The context path also needs the `context` runner, which is not yet in the production bot chart's collectors value. The bot deploy was triggered but not verified.
- **Verification.** Titles: "scout: context-driven qualification", "scout: calendar-driven qualification", "scout: context signals never qualify", "scheduler: context signals never wake", "manager: context signals are not events", "scout: caps discovery paths before model calls", "scout: decision context carries context and calendar" and "scout: manual run on off runs non-signal paths". Integration: "scout: discovery paths on the database". FR-SC-BOT-007 kept 336 base titles in 39 files (`check-base-titles.mjs`). **FR-SC-E2E-003, a preview wake with both paths on, was not run,** because it would call the paid model router on the owner's key.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 5. Scout discovery and 6. Never a trigger; §API, Bot-written jsonb; §Test plan, Bots and Unverified end-to-end checks)

## Bounded model calls and carried wakes (fix rounds 2 and 3)

- Each call has a deadline (`MODEL_CALL_TIMEOUT_MS`, 30 s in the bound's arithmetic). A call cut by it is charged at its estimate (`CallDeadlineError` → `lost_after_send`, signals-ingest's ORCH-13).
- The pass's `SCOUT_MODEL_BUDGET_MS` (15 s) never cuts a call. Once spent, no new call starts, and a model-tier wake is **carried**: the run stays `running`, and the next evaluation continues it before any new wake. A survivor can be carried half-done, at its thesis, with its paid decide held.
- **The guard's worst-case delay** is 2 × (15 + 30) s + W = **90 s + W**, where W is the non-model pass work. A spec proves it with W = 0 (every call hanging 30 s, 3 bots, 16 passes). Before the r3 fold the budget was 20 s and a hanging provider could push a guard stop to about 160 s (R3-W2).
- A carried wake that ends (pause, new version, the runner stopping) finishes `failed`/`interrupted`.
- A survivor that throws after a call still records its calls (`recordBotCalls`) and counts them in the run and the per-bot budget (FU-1 fix F1). Its reservations are always released.

(source: raw/2026-10-21-bots.md §The bot engine, Bounded model calls and carried wakes; §Concept, Review history, Bot code)

## Per-bot daily model budget (FU-1 item 4)

- `BOT_DAILY_CEILING_SHARE = 0.25` × `MODEL_SPEND_DAILY_CEILING_USD`, per Bangkok day, on the two bot stages. No schema or environment change.
- **The budget day** is the Bangkok day of the wake's `started_at` (the plan-review r7 ruling against an unbounded midnight carry-over).
- **Spend** = `scoutCostForDay` (the sum of the day's other scout runs' `counts.cost_usd`) + a carried half-done survivor's held reservations + the wake's own tally.
- Before each survivor's calls its estimate is added. Over the budget, that survivor and every later one take the template with no call and nothing reserved.
- Visible as `bots_bot_budget_reached_total{tier}` (exported at 0 for `jev`, `small_llm` and `large_llm`) and the warn log `bots_bot_budget_reached` (`bot_id` and `run_id` only, once per wake).
- Tier `none` is exempt. The global ceiling still applies on top (see [[model-routes-and-spend]]).
- **Since accounts and roles (2026-10-29)** a second, per-person limit follows this one: the plan's daily allowance (see "Plan allowance, tier entitlement and attribution" below).

**Budget edges (bot security r6, info).** F2: a wake carried past midnight can let one bot use about 50 % of the new day's global ceiling. F4: one survivor can overshoot the budget. A crashed wake's spend drops out of the sum until the next start's sweep writes zero counts (the global ceiling still holds). The 25 % is approximate, because it is based on estimates. **FU-4:** make `BotModels.budget` required, with a zero-estimate budget on `runner.ts`'s `unavailableModels`, so the budget cannot fail open by type; production `models.ts` always sets it. **FU-5 (owner decision):** 10 active bots × 25 % lets four running bots on one account exhaust the shared ceiling. Since accounts and roles the per-person allowance also bounds one account ($0.50 a day on `founder`). The source does not say whether that closes FU-5.

(source: raw/2026-10-21-bots.md §Concept, The FU-1 spend caps, item 4; §Open questions, Follow-ups and Budget edges)

## Manager (PRD §4.5; `manager.ts`, `positions.ts`, `direct-entry.ts`, `intake.ts`)

- **Triggers.** It acts on an instrument only on a new closed bar of `schedule.manager.timeframe` (`strip` means the strip timeframe), or, with `on_events`, on a new strong signal, a strip zone change, or `px:last` crossing a level. It reads the universe's newest bars once per pass (`latestIndicatorRows`, P27). It makes no model call in this slice (S18).
- **Candidates.**
  - `proposed → watching` (reason `seen`) on the first evaluation.
  - Expiry at TTL: `expired`, reason `ttl`. A close at or below `invalidation_px` before entry: `expired`, reason `invalidated`.
  - The entry condition (`immediately`, `zone_turns_buy`, `pullback_ema12` or `elliott_wave2_holding`, D4) is checked on the closed bar.
  - Gates in order: `cdc_filter`, `elliott_filter`, `impact_below_min`, `p_below_min`, `max_open`, `max_symbols`, `allocation`. A failed gate is a `gated` watch verdict, not a decision (S6). Only a hard limit that blocks an otherwise-met entry writes a `skip`.
  - Sizing by `p` within the allocation (PD4), capped by the fee-net allocation room `room / (1 + allocation × fee rate)` with pending buys counted (ORCH-9c).
  - The entry goes through the intake with `client_order_id = UUIDv5("{bot_id}|{instrument_id}|candidate|{candidate_id}")`, copying the proposing decision's `signal_ids`, `signal_snapshot` and `model` (ORCH-9a). On `placed` the candidate becomes `entered`, with `stop_px = entry − stop_atr × atr14`.
  - An observing bot writes a skip-shaped decision with `reasons ["observing"]` once per candidate (ORCH-9b), and the candidate stays `watching`.
- **Positions.** Exit on zone, horizon (`hold_max_sessions`) or invalidation; *Add* at most once per signal; *Trim* of half on a `down` signal. Each close moves the candidate to `closed` with its reason and clears `realtime_requested_at`. An `entered` candidate with no position and no pending order (a cancelled entry, a user close) is closed as `closed (user)`.
- **Direct entries (S7).** With `scout.kind = off` and `entry_condition = zone_turns_buy`, a strip Buy run creates the candidate `proposed → entered` and the order in one intake transaction, keeping the 2b idempotency key and skip reasons.
- **Version change.** The service never touches candidates on a save. The bot expires the previous version's live candidates with reason `version` on its next pass. A later version's manager never enters an earlier version's candidate.

The intake itself (account lock first, the C4 lock order) is on [[paper-trading]] (source: raw/2026-10-21-bots.md §The bot engine, Manager; §Concept, Spec decisions S6, S7, S18; ORCH-9).

## Guard (PRD §4.6; `guard.ts`)

On every pass, for each general bot that is `running` or `observing`, with rules only, from the recorded `px:last` (fresh within 120 s; a stale price is `deferred` with `["price_unavailable"]`, ORCH-5d). The bot reads its own in-process recorded prices, not Redis (see [[redis-market-contract]]).

- **Stop** (`last ≤ stop_px`) or **invalidation** (`last ≤ invalidation_px`): a protective market close with `loop guard`, `action close` and `policy_result {rule: "protect", exit_reason, level, last}`.
- **Daily loss** (`equity ≤ day-start equity × (1 − daily_loss_pct)`): close every position. The pause waits until every open position has a close placed; then `bots.status = paused`, with event `guard_paused {day_pnl_pct}`.
- **Total exposure and class ceiling** (× 1.10): close the newest positions, `exit_reason protect`, counted as `trimmed`.

The guard writes a run only when it acted, or on a manual run. Its `protected` entries are written even when a pause skips the manager (GAP-B2, fixed in review). A guard pause skips the manager and the scout for that pass. The pause (`pauseFromGuard`) and the probation flip are short transactions of their own, never under an account lock; they are the only bot writes to `bots.status` (S8/S11). Legacy bots have no guard.

On the preview, a stop raised above the live price produced the guard's close 14.8 s after the breach and a closed position 60.1 s after it (FR-BT-E2E-004) (source: raw/2026-10-21-bots.md §The bot engine, Guard; §Test plan, The E2E checks).

## Candidates (migration J, PRD §4.7)

**Lifecycle.** `proposed` (scout) → `watching` (manager) → `entered` (order) → `closed` (`zone | horizon | invalidation | stop | protect | user`). A `proposed` or `watching` candidate can also become `expired` (`ttl | invalidated | version`). For `me`, *Not this time* sets `declined_at`/`declined_decision_id`, and *Use this order* sets `followed_order_id`; neither changes `state` (see [[signal-cited-orders]]).

**The table** (full DDL notes on [[centralized-migrations]]):
- Keys: `candidate_id uuid PK DEFAULT uuidv7()`; `bot_id` → `bots`; `(bot_id, bot_version)` → `bot_versions`; `run_id`; `instrument_id` → `instruments`; `proposed_decision_id NOT NULL`, `entered_decision_id`, `declined_decision_id` → `decisions`; `order_id`, `followed_order_id` → `orders`.
- Fields: `direction`, `p numeric(4,3)`, `impact numeric(5,4)`, `thesis` (≤ 240), `thesis_source` (`model` or `template`), `horizon`, `entry_condition`, `invalidation_px`, `stop_px`, `ttl_until`, `state`, `state_reason`, `signal_ids uuid[] DEFAULT '{}'`, `declined_at`, `created_at`, `state_changed_at`.
- Indexes: `candidates_bot_state_idx (bot_id, state, created_at DESC)` and the partial `candidates_live_instrument_idx (bot_id, instrument_id) WHERE state IN ('proposed','watching','entered')`.
- CHECKs: the closed sets above, `p` and `impact` in [0, 1], prices > 0, and `(state IN ('closed','expired')) = (state_reason IS NOT NULL) OR state = 'watching'`.

**Who writes.** The service writes only `declined_at`, `declined_decision_id` and `followed_order_id`. The bot writes every other column (source: raw/2026-10-21-bots.md §The bot engine, Candidate lifecycle; §Database, New tables and Who writes what).

## Decisions the loops write (PRD §4.8)

Every bot decision carries `actor bot`, `bot_version`, `loop` and `run_id`; `candidate_id` wherever one exists (every propose, entry, add, trim, exit and guard close); `signal_ids` and `signal_snapshot` (null for setup-driven candidates and direct entries); `model` (`{tier: "none"}` for tier `none`); `market_state` with `elliott` and `regime`; and `policy_result`. Actions: the scout writes `propose`; the manager `buy | add | trim | close | skip`; the guard `close | trim`. See [[decision-record]] (source: raw/2026-10-21-bots.md §The bot engine, Decisions written by the loops).

**C4'' (`packages/sim`, S9).** `closeStampReason` binds `policy_result->>'exit_reason'` (`stop`, `invalidation`, `zone`, `horizon`, `protect`). Without it, `rule = 'exit'` binds `zone` (legacy), and anything else binds `user`. The `CloseStampSQL` text is unchanged; only the bound value changes. An unknown value throws `RangeError`. See [[paper-trading]] (source: raw/2026-10-21-bots.md §The bot engine, C4'').

## Watch verdicts from the general engine

The general engine writes the same `bot_watch` rows and `bot_runs.outcomes` as the 2b pass, with nine more verdicts (C11': `watching`, `gated`, `entered`, `expired`, `added`, `trimmed`, `exited`, `protected`, `no_candidate`) and a `15m` timeframe. `rule` names the evaluation kind (`entry` or `exit`) on general-engine `deferred`, `skipped` and `observed` entries (ORCH-9d). See [[bot-watch-verdicts]] (source: raw/2026-10-21-bots.md §Database, Altered objects; ORCH-9).

## Model stages (`bot_decide`, `bot_thesis`)

- Both run on the signals router, ledger and ceiling (`openSignalsModels`), so they share `model_calls`, `model_spend_daily` and `MODEL_SPEND_DAILY_CEILING_USD` with the signals pipeline (see [[signals-pipeline]] and [[model-routes-and-spend]]).
- **Tier routing.** `jev` uses the `bot_decide` route (`jev-1.13.0`, falling back to Haiku); `small_llm` uses the small-LLM adapter with the Haiku fallback model; `large_llm` uses the adapter with `anthropic/claude-sonnet-5.5`. `none` calls nothing.
- Prompts `bot_decide.v1` and `bot_thesis.v1` are recorded in `prompt_versions` on first start. **Since signals context, `bot_thesis.v2` (PB8) is live,** because v1's text described `market_state` as chart state only. It is recorded beside v1, which stays untouched (source: raw/2026-10-30-signals-context.md §Concept, How it runs, 5. Scout discovery).
- A stage start refusal is logged once, and the runner goes on with failing stages, so the 2b pass never depends on the model tables.
- **FU-8 (new, recorded after the source document).** A `bot_thesis` reply was rejected by the client's 240-code-point schema **after a paid call**: the call is charged, and the candidate falls back to the template thesis under S17. The fix is open. Whether this explains the preview's template thesis on bot B (a paid `jev` wake with `thesis_source template`) is not stated in the record [needs verification].

(source: raw/2026-10-21-bots.md §The bot engine, Model stages; §Open questions, B's template thesis; FU-8 from the orchestrator note of 2026-10-21)

## `packages/waves` (D7, FR-BT-BOT-012)

- A pure Nx library (`@tidewatch-bot/waves`) with a `BigInt` rational type, zigzag, `analyze`, `computeRegime` and `TUNABLES`. No I/O and no runtime dependency.
- The five C13 fixtures and `waves-tunables.v1.json` were copied with `cp` and are hash-pinned.
- `waves:test` passed 84/84. An extra Go cross-check found the JSON output byte-identical to the service's on all five fixtures; this A1 gate was green before any engine step.

See [[elliott-regime-labeller]] (source: raw/2026-10-21-bots.md §The bot engine, `packages/waves`).

## Observability

- **Thirteen `bots_*` series.** Six from `createBotsMetrics` (including `bots_running`), seven from `createGeneralBotsMetrics`: `bots_scout_wakes_total{result}`, `bots_candidates_total{state}`, `bots_guard_actions_total{kind}`, `bots_run_requests_total{loop}`, `bots_model_calls_total{stage,tier}`, `bots_model_cost_usd_today` and `bots_bot_budget_reached_total{tier}`. Label sets are closed.
- **Fifteen log events**, closed by a source scan. Slice 6 adds `bots_scout_finished`, `bots_candidate_state`, `bots_guard_acted`, `bots_run_request_taken`, `bots_probation_ended`, `bots_lock_busy` and `bots_bot_budget_reached`.
- No log line carries a thesis, headline, message, body, URL or key.
- **FU-7 (defect).** `bots_running` is set by both the 2b pass and the general pass, so it alternates between 1 and 2 instead of counting all running auto bots; bot README lines 586 and 765 disagree about it. On the preview it read 2.

(source: raw/2026-10-21-bots.md §The bot engine, Observability; §Test plan, Defects found on the preview)

## Verification (bot)

- Local: `pnpm nx run-many -t lint test typecheck build`, and `scripts/sql-integration.sh` on J (it refuses to run below J). Titles are asserted exactly with `scripts/assert-vitest-titles.mjs`. The harness's bots specs went 30/30 at S13, 36/36 after fix 1 and 37/37 after fix 2.
- Named titles include "dispatches by vocabulary", "enters on {condition}", "gate is a verdict not a decision", "expires at ttl", "replay after crash (general)", "decision context is complete (sql)", "takes run requests", "skips a locked bot", "observing proposes but never orders", "ends probation", "allocation is a ceiling", "requests realtime at proposal", "direct entry on zone turn", "routes by tier", "ceiling keeps candidates", "tier none makes no model call", and the FU-1 titles "keeps the bot budget for a wake carried over midnight", "registers bots_bot_budget_reached_total at zero for the three tiers", "a failed survivor's calls count toward the bot's budget" and "pg store on J: scout cost today".
- FR-BT-BOT-001…014 are verified by unit tests and the harness. The real-time halves: BOT-004 by E2E-004 (passed); BOT-009 by E2E-005 and BOT-010 by E2E-006 (both unverified). See [[bots]].

(source: raw/2026-10-21-bots.md §Concept, Stage, Verified locally; §Test plan, Commands, Named acceptance tests and Acceptance status)

## Open bot items

FU-4, FU-5, FU-7 and FU-8 (above); bot security L1 (an untrusted-content instruction in the prompts, needing new prompt versions) and L3 (bot-scope `CANDIDATE_FOR_CHANGE`); a failed `recordBotCalls` loses its calls, as in signals. Deferred by design: a per-tick guard, manager judgement (S18), shorts, 4h, and GDELT and calendar discovery (source: raw/2026-10-21-bots.md §Open questions). GDELT and calendar discovery shipped with signals context on 2026-10-30 as opt-in paths (see "Discovery paths" above).

## Read by Stats (slice 7, 2026-10-27)

Slice 7 (see [[statistics]]) made **no bot change**: the bot still writes outcomes, runs and `cost_usd` as before, and the 2b pass and the general engine are untouched. Stats reads what the engine writes (source: raw/2026-10-27-statistics.md, summary block; §Database, What slice 7 writes).

- **The scout's stated `p`.** Calibration's population is a version's `propose` decisions whose `model->>'p'` is a decimal in [0, 1]. Tier `none` writes `{tier: "none"}` and states no probability, so a rules-only version reads "This version states no probabilities" and its ECE is `null`. Before slice 7 no decision on any stack had a graded stated `p`; the calibration plot and `calibration_no_worse` were exercised only on synthetic fixtures and seeded data (A4).
- **The candidate horizon picks the outcome column:** `intraday → r_1d`, `days → r_5d`, `weeks → r_20d`; anything else, or no candidate, uses `r_5d` (A3).
- **Entries and adds** (`actor bot`, `action IN (buy, add)`) are the attribution base rows and the only decisions that can be losing decisions to label. Their copied `signal_snapshot.source_code` and `market_state.regime` give the source and regime dimensions.
- **Cost of decisions** is Σ `bot_runs.counts.cost_usd` over the version's runs in the window, any loop, counting only a JSON string that matches the bot's own decimal guard. Scout wakes are runs with `loop = 'scout'`. A crashed wake's spend is undercounted (A5). At slice 7 `model_calls` had no `bot_id`, so per-bot cost existed only through `bot_runs`. Since migration L the engine writes `bot_id` and `user_id` on its calls, but Stats still reads `bot_runs` (see [[model-routes-and-spend]]).
- **Probation skips.** An `observing` bot's skip-shaped decisions with `reasons ["observing"]` are not counted as deliberate skips (PD3). A version's window is not moved by probation (D2).
- **The guard pause met the E2E seeding.** During FR-ST-E2E-002 the guard paused the seeded PV4 Challenger twice, because its seeded ledger ended at 1,080,000 while the engine values a fill-less account at its starting capital, which read as a −7.4 % day. The source calls that correct product behaviour on inconsistent seed data; the seed's ledger was rescaled, leaving the ratios unchanged, and the two `guard_paused` events remain on the shared preview database.
- **FU-1 (slice 7, service).** A NaN or Inf `r_5d` or `px_at_decision` now makes the attribution and stats reads answer 500 (slice 6 answered 200 with "NaN"). The follow-up is to confirm the bot cannot write non-finite values, or to count such rows as ungraded.

(source: raw/2026-10-27-statistics.md §Concept, Problem, Owner decisions D2/D8 and PD3, Assumptions A3–A5; §Concept, How each figure is computed; §Test plan, The E2E checks and Preview database footprint; §Open questions, Follow-ups FU-1)

## Plan allowance, tier entitlement and attribution (accounts and roles, 2026-10-29)

tidewatch-bot #19 (merge `bd5e435`, head `4e66579`; bot S1–S5) shipped with migration L and was deployed to production on 2026-10-29. See [[accounts-and-roles]] for the plans.

- **The evaluated-bots join.** `EVALUATED_BOTS` joins `users` and `plans` (an inner join that drops no bot). Each row carries:
  - `ownerUserId`;
  - `dailyModelUsd` (`numeric(10,6)` as text);
  - `decisionTiers`, a closed list; anything else throws `RangeError`.

  It never reads `users.status` or any other plan field. A wake keeps the row it started with, so a plan change takes effect at the next wake.
- **Per-person daily allowance (S16).**
  - **The order, per survivor:**
    1. the per-bot 25 % budget;
    2. `spent_user + estimate ≤ dailyModelUsd`;
    3. the calls, where the global ceiling's reservation sits.
  - **`spent_user`** is `scoutCostForOwnerDay`: the per-bot statement joined by `owner_user_id`, read lazily once per wake per pass. It is added to the wake's tally, any held decide, and the owner's other open wakes of the same Bangkok day, each amount counted once.
  - **Over the allowance,** that survivor and every later one of the wake, carried passes included, take the template thesis with no call and nothing reserved.
  - **Signals.** It fires `bots_user_budget_reached_total{tier}` and the warn log `bots_user_budget_reached {user_id, bot_id, run_id}`, once per wake.
  - **Exempt.** Tier `none`, `NO_SPEND_BUDGET` models, and a wake that already hit the per-bot budget or the ceiling.
  - **Fails closed.** A missing allowance or a failed owner read fails the wake before any further call. Two mutation-checked specs pin this (security SF-1).
- **Tier entitlement (S15).** Once per wake, a stored model tier outside `decisionTiers` runs the whole wake as `none`:
  - no call, nothing reserved, and neither budget consulted;
  - a template thesis, and `p` taken from the signals;
  - one log `bots_tier_not_entitled {bot_id, run_id, tier}` and one count of `bots_tier_not_entitled_total{tier}`.

  The version and its hash are unchanged, and a carried wake keeps its tier. On the service side, a save or create with an unentitled tier is refused `not_entitled` (see [[bot-versions-and-runs]]).
- **Attribution.** The scout stamps `bot_id` and `user_id = ownerUserId` on every call it collects. So the survivor transaction, `recordBotCalls`, a settled held decide and an abandoned wake's held decide all write both columns (`INSERT_BOT_CALL`). `modelCallValid` refuses a non-UUID id, and nothing is written then. `packages/signals/src` never sets the columns.
- **Observability.** Two new metric families, `bots_user_budget_reached_total{tier}` and `bots_tier_not_entitled_total{tier}`, use the tiers `jev`, `small_llm` and `large_llm`, are exported at 0, and carry no `bot_id` or `user_id` label. The source gives the bot's closed event list as 18 after this build. No new bot variable.
- **Disable and the engine.** Disabling a person in the operator console pauses their running and observing auto bots through the user's Pause path, so the engine stops evaluating them. A disable in the middle of a pass leaves the bot running for the rest of that pass, as a user Pause does (follow-up).
- **Verified.** Unit 381/381. Integration bots 42, all passed. `sql-integration: PASS` at `required schema version 20261028120000`. The Vitest titles include:
  - "holds a person's bots to the plan's daily allowance across bots";
  - "allowance and per-bot budget are independent";
  - "writes bot_id and user_id on every bot model call";
  - "runs a tier the plan excludes as none for the wake";
  - "a carried wake keeps its tier after the plan changes";
  - "pg store on L: bot calls carry bot_id and user_id".

  On the preview, E2E-004 tripped the allowance once. The tier entitlement never fired on a real wake (`bots_tier_not_entitled_total` read 0 throughout).
- **In production,** the new bot rolled at 07:19:12Z, before L was applied. It logged 12 `bots_pass_failed` with Postgres 42P01 (no `plans` table) until L ran in the service sync at 07:25:10Z (see [[centralized-migrations]]).
- **Follow-ups:**
  - make the `ScoutWake.bot` plan fields required;
  - check both ids at wake start;
  - take `user_id` from `bots.owner_user_id` in SQL;
  - put `MemoryPlan` and `FOUNDER_PLAN` on the testing barrel, and make the memory store mirror L's foreign keys;
  - security N-1 (a crashed wake's spend drops out of the allowance sum) needs an owner decision.

(source: raw/2026-10-29-accounts-roles.md §API, Bot: allowance, tier entitlement, attribution; §API, Metrics and logs; §Test plan, Named acceptance tests, Results and Not verified or partial; §Concept, Rollout to production; §Open questions, Recorded follow-ups, Bot and Open owner decisions)

## The learning loop and the engine (slice 8, 2026-10-30)

tidewatch-bot #17 (merge `2a3a412`, head `435feb4`) shipped with migration M and was deployed to production on 2026-10-30. The loop itself is on [[learning-loop]].

- **A separate runner, not a fourth loop (D4).** Learning runs in its own `learning` runner (the fourteenth collector, `runner:learning`), because a fourth loop inside the bots pass would break the guard's 90 s bound. It never writes `bots`, `candidates`, `orders`, `ledger` or `bot_watch`, and never places an order (see [[market-data-worker]]).
- **The bots runner ignores `learn` (review B1).** M adds `learn` as a fourth value of `bot_runs.loop` and `bot_run_requests.loop`. The bots runner's take adds `AND r.loop <> 'learn'`. Its start-up sweeps (`INTERRUPT_RUNS`, `RELEASE_RUN_REQUESTS`) skip `learn` rows too, because a learning run outlives the bots runner's 5-minute cutoff. Named titles: "takes learn requests only" (learning runner), "bots runner ignores learn" and "bots runner never takes a learn request (sql)".
- **The scout on a learned version (D5, S8).** After a survivor's `p` is settled, if `learning.calibration` has a map for the candidate's horizon, `p_cal = apply(map, p)` (3 digits). The candidate gets `p = p_cal`, and the `propose` decision's `model` carries `p: p_cal`, `p_raw` and `calibration {method, horizon, learning_run_id}`.
  - Without a map, `p` is unchanged, `p_raw` is written and `calibration` is null.
  - Tier `none` is untouched, and an unlearned version's `model` object is byte-identical to slice 6 ("unlearned version is byte-identical").
  - Refits always use `p_raw`, so maps never compound.
  - On the preview (E2E-001), the next scout wake on a learned v3 wrote `model.p 0.597`, `p_raw 0.730` and `candidates.p 0.597`.
- **The manager's failure gate (D8, S11; `learning/meta-gate.ts`).** After the `allocation` gate, with a non-null `meta_gate`, the manager computes `p_loss = sigmoid(intercept + Σ coef·(x − mean)/scale)` over the closed feature list:
  - `p_loss ≥ 0.70`: a `gated` watch verdict with reasons `["meta_veto"]` and **no decision** (`META_VETO`; see [[bot-watch-verdicts]]);
  - `0.55 ≤ p_loss < 0.70`: `sizedBudget × 0.5`, before the fee-net room and the cap;
  - below 0.55: unchanged.

  Entries record `policy_result.meta {p_loss, effect: none|shrink}`; as built, every candidate-entry intake decision of a gated version carries it, skips and observing decisions included. **Direct entries** (zone turns with `scout.kind = off`) are exempt. The gate never raises size. Named titles: "meta veto is a verdict not a decision", "shrinks the budget", "never increases size", "direct entry is exempt".
- **The day-spend reads now include learn runs (OD-LEARN-SPEND).**
  - `BOT_COST_FOR_DAY` (`pg-store.ts:1271`) sums the bot's scout **and learn** runs of the Bangkok day, the per-bot 25 % share's spend. The scout's own per-bot check reads it too: in the merged bot (`2a3a412`), `scoutCostForDay` is an alias of `botCostForDay`, which runs `BOT_COST_FOR_DAY` (`packages/bots/src/pg-store.ts:2107-2114, 2530-2533`; checked by the orchestrator after the merge), so a learning run's spend reduces the same day's scout share.
  - `OWNER_COST_FOR_DAY` (`pg-store.ts:1291`), renamed from `SCOUT_COST_FOR_OWNER_DAY` (the accounts-and-roles section above names the owner's read `scoutCostForOwnerDay`, from that source), sums scout and learn runs across all the owner's bots, so the per-person allowance now counts learn spend.
  - The labeller checks both before every `post_mortem` call. Each holds per runner, so a concurrent scout wake and learning run do not see each other's in-flight tally; the global ceiling holds. Named titles: "sums scout and learn runs into the bot's day", "pg store on M: bot cost today". See [[model-routes-and-spend]].
- **Observability.** `bots_run_requests_total{loop}` gains `learn` through the shared counter. The learning runner's own five metric families and ten log events are on [[learning-loop]].
- **The C14 port.** `learning/net.ts` ports the service's modelled round-trip rate for the weights job, pinned by `attribution-net.v1.json` in both repositories ("agrees with every C14 net-return case").
- **Harness.** `scripts/sql-integration.sh` pins M by the anchored lookup `learning_loop` and keeps L, J and H asserted; it refuses to run without L and M. Final: bots 536 unit tests, bots int 61.

(source: raw/2026-10-30-learning-loop.md §Concept, The runner and A learned version in the engine; §Concept, Owner decisions D4, D5, D8; §Concept, Decisions during the build OD-LEARN-SPEND; §Concept, Spec corrections, OD-LEARN-SPEND; §API, Bot side; §Test plan, Commands and Named acceptance tests; §Test plan, What each seeded E2E showed)

## Related pages

- [[bots]]: the slice-6 overview, acceptance, preview results and follow-ups
- [[bot-versions-and-runs]]: v2 configs, the service routes, run requests and the FU-1 service caps
- [[bot-watch-verdicts]]: C11' and the nine new verdicts
- [[zone-transition-bot]]: the 2b pass that still runs v1 configs
- [[decision-record]]: the decisions each loop writes, and C4'' exit reasons
- [[paper-trading]]: the bot-side intake and the close stamp in `packages/sim`
- [[model-routes-and-spend]]: the routes, ledger, global ceiling and per-bot budget
- [[signals-pipeline]]: the router and `decide()` port the bot stages reuse
- [[elliott-regime-labeller]]: the service labeller `packages/waves` ports
- [[market-data-worker]]: the worker hosting `runner:bots`
- [[redis-market-contract]]: the recorded `px:last` view the guard reads, not Redis
- [[instrument-master]]: classes, universe lists and `realtime_requested_at`
- [[signal-cited-orders]]: `me`'s use and decline of a candidate on Trade
- [[statistics]]: slice 7, which grades the engine's decisions, `p` and spend per version
- [[stats-read-api]]: the calibration, attribution and cost definitions over these rows
- [[accounts-and-roles]]: plans as data, the founder allowance and tiers the engine now reads
- [[learning-loop]]: slice 8, whose runner proposes the calibration maps and the failure gate a learned version runs
- [[signals-context]]: spec 3b, which added the context and calendar discovery paths
- [[context-features-and-coverage-signals]]: the features the context path reads, and why coverage signals never trigger
- [[event-calendar]]: the earnings rows the calendar path reads
