# Model routes, prices and the daily spend ceiling

**Summary**: Since slice 3a (merged 2026-10-11), the model behind every call is data, not code (D2). `model_routes` names the provider and model for each stage, plus a fallback. `model_prices` prices each model, and `prompt_versions` pins each prompt's hash. Every call writes a `model_calls` row and upserts `model_spend_daily` in the same transaction as the stage it serves. Before each call, a reservation-based check against `MODEL_SPEND_DAILY_CEILING_USD` (default $1.00, PD2) stops sending once the Bangkok day's budget would be exceeded. Over the ceiling, the document is **queued, never dropped**, and ingest keeps storing. This is outcome O3, "bounded cost that never drops work". The two providers are Jev, called directly, and OpenRouter, with one key. **Since slice 6 (bots, merged 2026-10-21, not deployed),** bots spend through the same ledger and ceiling. Migration J seeds two more routes, `bot_decide` (Jev, Haiku fallback) and `bot_thesis` (Haiku through OpenRouter), and a price row for the large tier, `anthropic/claude-sonnet-5.5`. A bot's decision tier (`none`, `jev`, `small_llm`, `large_llm`) picks the route, and the editor shows each tier's cost per decision, measured or list. The **FU-1 per-bot daily budget** holds each bot's two stages to 25 % of the shared ceiling per Bangkok day, under the global ceiling. Follow-up **FU-8**: a `bot_thesis` reply was rejected by the client's 240-code-point schema after the call had been paid. **Since slice 7 (statistics, merged and deployed 2026-10-27),** Stats shows each bot version's **cost of decisions**: Σ `bot_runs.counts.cost_usd` over the version's runs in the window, converted at the C6 USD/THB rate, with the USD figure alongside. When slice 7 shipped, it was per bot only through `bot_runs`, because `model_calls` had no `bot_id`. **Since accounts and roles (merged and deployed 2026-10-29),** `model_calls` carries `bot_id` and `user_id` on every bot call. Signals-stage rows and every row written before migration L read NULL in both. Spend is bounded **per person** too. The plan's `daily_model_usd` (the `founder` plan: $0.50) is a daily allowance, enforced bot-side beside the 25 % per-bot budget and under the shared ceiling. The operator console's Spend view splits the day into ingest (`user_id IS NULL`) and bots. The service now reads `MODEL_SPEND_DAILY_CEILING_USD` too, which must match the bot's value. Stats' cost of decisions still reads `bot_runs`. **Since the learning loop (slice 8, merged and deployed 2026-10-30),** a sixth stage, `post_mortem`, labels losing entries: migration M seeds its route (`openrouter`, `anthropic/claude-haiku-5.5`, no fallback), and the bot records `post_mortem.v1`. Labelling spends through the same ledger and ceiling. Under the owner's ruling OD-LEARN-SPEND ("Count it fully"), every `post_mortem` call carries `bot_id` and the owner's `user_id`, and the per-bot share and the per-person allowance both sum scout **and learn** runs. Production labelling depends on the OpenRouter key; the preview's key was refused on every call (see [[learning-loop]]).

**Sources**: `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-21-bots.md` (the bot stages, J's seeds and the per-bot budget); orchestrator note of 2026-10-21 (FU-8 only); `raw/2026-10-27-statistics.md` (the cost-of-decisions KPI only); `raw/2026-10-29-accounts-roles.md` (attribution, the per-person allowance, Spend and the service's ceiling variable); `raw/2026-10-30-learning-loop.md` (the `post_mortem` stage and OD-LEARN-SPEND only); `raw/2026-10-30-signals-context.md` (zero GDELT spend and `bot_thesis.v2` only)

**Last updated**: 2026-10-31

---

## Providers and model ids as data (D2, PD1, PD5)

- **D2. OpenRouter for the LLM, with one key and model ids as data.** The model behind every call is a database string, so A/B tests and tier changes are data changes, not deploys.
- **PD1. Jev direct** with `JEV_API_KEY`, at `https://api.typesafe.ai/v1/systemone`, its model pinned to `jev-1.13.0`, **never `jev-latest`**.
- **PD5. `anthropic/claude-haiku-5.5`** through OpenRouter for extraction, and as the small-LLM fallback for the Jev stages.
- `provider` is `jev|openrouter` throughout. A small-LLM fallback call is recorded as `openrouter` (R-SIG-34).
- OpenRouter requests carry **no `temperature`** (ORCH-16), a provider constraint found on the preview (PV-1; see [[signals-pipeline]]).

(source: raw/2026-10-11-signals-ingest.md §Concept, Chosen design D2 and Accepted defaults; §API, Triage and Extraction; §Database)

## Seeded routes and prices (migration H)

These are seed rows in H, so changing them is a data migration (see [[centralized-migrations]]).

| Table | Rows |
|---|---|
| `model_routes` | `triage (jev, jev-1.13.0, small_llm, anthropic/claude-haiku-5.5)`; `scoring` (the same); `extraction (openrouter, anthropic/claude-haiku-5.5, NULL, NULL)` |
| `model_prices` | `(jev, jev-1.13.0, 0.042, 0, 2026-10-11)`; `(openrouter, anthropic/claude-haiku-5.5, 0.10, 0.50, 2026-10-11)` |
| `prompt_versions` | No seed. The bot records `(version, stage, sha256)` at start. |

- **Start refusals.** A route or fallback without a valid `model_prices` row refuses the start (`RouteConfigError` `missing_price` / `missing_fallback_price`; code-signals W1). A prompt that changed under an old version fails the start (`PromptVersionConflictError`).
- ORCH-5 settled the table names: the PRD's `model_calls`, `model_spend_daily`, `model_routes` and `model_prices` win over the intent's `model_spend`.

(source: raw/2026-10-11-signals-ingest.md §Database, Seeds; §API, Start checks; §Concept, ORCH-5)

## The ledger

- **Every model call writes `model_calls`**, with `document_id`, `stage`, `provider`, `model_id`, `prompt_version`, tokens, `cost_usd`, `estimated` and `latency_ms`. It also upserts `model_spend_daily(day_bkk, provider, model_id)`, both in the stage's transaction.
- `cost_usd` is OpenRouter's `usage.cost` when present, else tokens × `model_prices`. Jev counts input tokens only.
- `day_bkk` uses a fixed +07:00 offset.
- `model_spend_daily` has the primary key `(day_bkk, provider, model_id)`. `model_calls.stage` also allows `eval`, so `signals-eval` spends through the same ledger and ceiling. `model_calls_created_idx` indexes the ledger.

(source: raw/2026-10-11-signals-ingest.md §API, Spend ledger and ceiling; §Database)

## The ceiling, with reservations (R-SIG-33)

- **Before each call:** today's recorded spend + the estimates of calls in flight + this call's estimate must be ≤ `MODEL_SPEND_DAILY_CEILING_USD`. The check and the reservation are one step, so two concurrent calls cannot overshoot together.
- **Over the ceiling,** nothing is sent. The document is marked `queued_reason = ceiling`, and `signals_spend_ceiling_reached` is logged once per Bangkok day. **Nothing is dropped, and ingest keeps storing.**
- **The variable.** The default is `1.00`. An empty or blank value means `1.00` (ORCH-5), and a non-decimal value exits 1 with `must be a decimal number`.

(source: raw/2026-10-11-signals-ingest.md §API, Ceiling with reservations; §API, Environment)

## Failed calls (ORCH-13)

- An HTTP error answer is recorded at the reported cost, usually `0` with `estimated = true`, and does not consume the ceiling.
- A timeout or connection loss after sending is recorded at the pre-call estimate and **counts** toward the ceiling.
- A failure before sending, a missing key and an abort are not recorded.
- A malformed 200 answer is recorded at 0, a small under-count noted in review.

(source: raw/2026-10-11-signals-ingest.md §API, Failed calls; §Concept, ORCH-13)

## Queue reasons survive restarts (R-SIG-32)

| Reason | Set when | Cleared |
|---|---|---|
| `ceiling` | The next call would pass the ceiling | At start, when today's spend is under the ceiling, so a same-day raise drains at once. At runtime, at the next Bangkok day, draining newest first. |
| `missing_key` | The provider's key is unset. `signals_model_disabled` is logged once with `provider` and `variable`. | At start only, so an added key needs a restart |
| `provider_unavailable` | 429 and 5xx are retried after 2, 4 and 8 s, then the document is marked | At start, or after 60 s at runtime |

A missing key disables its provider at start, and that provider's stages queue `missing_key`. `JEV_API_KEY` unset queues triage and scoring. `OPENROUTER_API_KEY` unset queues extraction and the small-LLM fallback. Neither stops `serve` (source: raw/2026-10-11-signals-ingest.md §API, Queue reasons and Environment).

## Route fallback

After 15 minutes of continuous Jev 5xx, triage and scoring use the route's `fallback_model_id` through the small-LLM adapter. `signals_route_fallback` is logged at most once an hour. One Jev attempt every 5 minutes ends the fallback, and every row records the model that answered (see [[signals-pipeline]]) (source: raw/2026-10-11-signals-ingest.md §API, Route fallback).

## Cost: expected and observed

- **PRD expectation:** about $0.18/day for triage and $0.35/day for extraction, at roughly 1,900 documents/day.
- **Preview, Bangkok day 2026-10-11:** $0.258474 by 09:54Z (Jev 436 calls, $0.038150; OpenRouter 364 calls, $0.220324), then $0.641961 by 10:49Z, under $1.00. 1,255 live Jev calls had been made by 10:47Z.
- **Eval run 3:** 199 calls for $0.116077. Extraction's worst-case output cost per call is $0.00125 at `max_tokens` 2500.

(source: raw/2026-10-11-signals-ingest.md §API, Cost expectation; §Test plan, Acceptance at merge and Eval; §Test plan, Reviews)

## Verification

- **FR-SIG-BRN-008** was verified by unit, integration and live tests, read with ORCH-13. Named bot tests include `reserves in-flight estimates so two concurrent calls cannot pass the ceiling together` and `drains ceiling-queued documents at start when today's spend is under the new ceiling`.
- **FR-SIG-E2E-005, live.** At 10:47:59Z the ceiling was set to `0.01`. Four documents queued `ceiling`, `signals_queue_depth{reason="ceiling"}` read 4, spend stayed at 0.634558, and exactly one `signals_spend_ceiling_reached` was logged. After the restore at 10:48:50Z, the queue drained by 10:49:27Z on the same Bangkok day (spend 0.641961). Only the same-day branch ran live; the next-day branch is covered by an integration spec.

(source: raw/2026-10-11-signals-ingest.md §Test plan, Named acceptance tests and Acceptance at merge)

## Operations

- **Keys.** The owner sets `JEV_API_KEY` and `OPENROUTER_API_KEY` in the root `.env`, optionally with `MODEL_SPEND_DAILY_CEILING_USD`, and restarts `tidewatch-bot`. `secretValues` masks the four provider keys and `TIDEWATCH_HTTP_CONTACT`. The root `docker-compose.yaml` passes the five new variables (the four keys and the ceiling) to the bot as `${VAR:-}`. Keys go only into owner-filled secrets and are never recorded here.
- **Watch** `signals_model_spend_usd_today` (a gauge reset at the Bangkok day) and `signals_queue_depth{reason}`.
- **Draining after a change.** Queued documents are re-evaluated at runner start, so a raised ceiling or an added key drains them after a restart.

(source: raw/2026-10-11-signals-ingest.md §API, Environment; §Open questions, Owner actions and Recovery)

## Bot stages (slice 6, 2026-10-21)

Slice 6 (see [[bots]]) merged on 2026-10-21 as tidewatch-migrations #10, tidewatch-service #12 and tidewatch-bot #10. It is not deployed.

### J's seeds and stage CHECKs

```sql
INSERT INTO model_routes (stage, provider, model_id, fallback_provider, fallback_model_id) VALUES
    ('bot_decide', 'jev', 'jev-1.13.0', 'small_llm', 'anthropic/claude-haiku-5.5'),
    ('bot_thesis', 'openrouter', 'anthropic/claude-haiku-5.5', NULL, NULL);
INSERT INTO model_prices (provider, model_id, input_usd_per_m, output_usd_per_m, valid_from) VALUES
    ('openrouter', 'anthropic/claude-sonnet-5.5', 2.00, 10.00, '2026-10-20');
```

- After J, `model_routes` has 5 rows and `model_prices` has 3. The Sonnet price was read from OpenRouter's models list at 2026-10-20T04:10:40Z and is cited in J's header (ORCH-3).
- J re-creates `model_routes_stage_check`, `model_calls_stage_check` and `prompt_versions_stage_check` to add `bot_decide` and `bot_thesis`. `prompt_versions` gets no seed; the bot records `bot_decide.v1` and `bot_thesis.v1` on first start.
- J's Down deletes only its own seed rows (the price row by `valid_from`) and fails loudly while a `model_calls` or `prompt_versions` row uses a bot stage (see [[centralized-migrations]]).

(source: raw/2026-10-21-bots.md §Database, Seeds and Altered objects; §Concept, Operations)

### Tiers and routing (D2, S3, ORCH-8)

| Tier | Route | Model call |
|---|---|---|
| `none` ("Rules only") | — | none, the thesis included (ORCH-8); the thesis is a template, `thesis_source = template`, nothing reserved |
| `jev` | `bot_decide` | `jev-1.13.0`, falling back to `anthropic/claude-haiku-5.5` |
| `small_llm` | the small-LLM adapter | the Haiku fallback model |
| `large_llm` | the same adapter (priced as `openrouter`) | `anthropic/claude-sonnet-5.5` |

- The thesis always uses `bot_thesis` (Haiku through OpenRouter), except for tier `none`.
- Both stages run on the signals router, ledger and ceiling (`openSignalsModels`), so they write `model_calls` and `model_spend_daily` like the signals stages and count against `MODEL_SPEND_DAILY_CEILING_USD`. There is no `custom` tier and never an OANDA key.
- **Bounded calls.** Each call has a 30 s deadline; a deadline-cut call is charged at its estimate as `lost_after_send` (signals-ingest's ORCH-13, applied to the bot in fix round 2). See [[bots-engine]] for the 15 s scout budget and carried wakes.
- A stage start refusal is logged once, and the runner goes on with failing stages, so the 2b zone pass never depends on these tables.
- `bots_model_calls_total{stage,tier}` has the closed label set `{bot_decide, bot_thesis} × {jev, small_llm, large_llm}`; `bots_model_cost_usd_today` is the bot's day gauge.

(source: raw/2026-10-21-bots.md §Concept, Owner decisions D2; §Concept, Rulings ORCH-8 and ORCH-13 note; §The bot engine, Model stages, Bounded model calls and Observability)

### Cost per decision shown to the owner (D3, `GET /model-tiers`)

- `measured`: the mean `cost_usd` over the last 7 Bangkok days when `calls_7d ≥ 20`.
- `list`: 1,500 input tokens for Jev and small; 2,500 input and 300 output for large, at `model_prices`.
- Then × `usd_thb`, to 4 dp. No price row or no rate → `unavailable: true`, and the editor greys that card.

(source: raw/2026-10-21-bots.md §API, Behaviour worth knowing, Model tiers; §Components, Version editor)

### The FU-1 per-bot daily budget (ORCH-10)

The service and bot security reviews found that one bot could exhaust the shared ceiling, which the signals pipeline also uses, because a signal-driven scout can wake every 5 minutes. At the owner's request (2026-10-21, 00:40Z) the build added:
- **`BOT_DAILY_CEILING_SHARE = 0.25`** × the ceiling per Bangkok day, on the two bot stages, bot-side only, with no schema or environment change. With the default USD 1.00 ceiling, that is about USD 0.25 per bot per day.
- **The budget day** is the Bangkok day of the wake's `started_at`.
- **Spend counted** = the day's other scout runs' `counts.cost_usd` + a carried survivor's held reservations + the wake's own tally. Before each survivor's calls its estimate is added; over the budget, that survivor and every later one take the template with no call and nothing reserved.
- **Signals:** `bots_bot_budget_reached_total{tier}` (exported at 0 for the three model tiers) and the warn log `bots_bot_budget_reached` (`bot_id` and `run_id` only, once per wake).
- Tier `none` is exempt; the global ceiling still applies on top, with its reservation check.
- The other FU-1 caps (per-class candidate and symbol bounds, at most 10 active auto bots, *Run now* at most 6 per bot and loop per hour) limit how many calls a wake or an account can make; see [[bot-versions-and-runs]].

**Known edges and follow-ups.**
- F2: a wake carried past midnight can let one bot use about 50 % of the new day's global ceiling. F4: one survivor can overshoot. A crashed wake's spend drops out of the sum until the next start's sweep. The 25 % is approximate, because it is based on estimates.
- **FU-4:** make `BotModels.budget` required, with a zero-estimate budget on `runner.ts`'s `unavailableModels`, so the budget cannot fail open by type.
- **FU-5 (owner decision):** 10 active bots × 25 % lets four running bots on one account exhaust the shared ceiling; the global ceiling still stops all calls. Consider a per-account cap or a lower share.
- **FU-8 (new):** a `bot_thesis` reply was rejected by the client's 240-code-point schema **after a paid call**, so the spend counts while the candidate gets the template thesis (S17). The fix is open.
- A failed `recordBotCalls` loses its calls, the same as in signals.

(source: raw/2026-10-21-bots.md §Concept, The FU-1 spend caps; §Open questions, Follow-ups and Budget edges; FU-8 from the orchestrator note of 2026-10-21)

### Observed on the preview

Bot B (tier `jev`) recorded `cost_usd` 0.000227 for its first signal-driven wake, and `/metrics` read `bots_model_cost_usd_today` 0.000227 and `bots_bot_budget_reached_total` 0 for all three tiers. B's thesis was nevertheless the template; the record does not say why [needs verification] (see [[bots]]). The 7-day spend soak FU-1 was meant to precede (FR-BT-E2E-002) was not run (source: raw/2026-10-21-bots.md §Test plan, Preview runs and The E2E checks; §Open questions).

## Cost of decisions on Stats (slice 7, 2026-10-27)

Slice 7 (see [[statistics]]) reads bot spend back per bot version. It adds no table, column or route here; it reads what the bot already writes (D10).

- **`cost_usd`** = Σ `bot_runs.counts->>'cost_usd'` over the version's runs (any loop) started in the window. Only a JSON string matching `^[0-9]{1,12}([.][0-9]{1,18})?$` counts, the bot's own guard. It carries 6 fraction digits.
- **`scout_wakes`** counts the runs with `loop = 'scout'`; the KPI note reads "{wakes} scout wakes · ${cost_usd}".
- **`usd_thb`** is the C6 rule-4 USD/THB rate resolved for the bot at the read's now, also for a past version's window; `null` without one. **`cost_thb`** is the exact `cost_usd` × that rate, rounded to 2 (S12). The USD figure travels too.
- **Why not `model_calls`.** At slice 7, `model_calls` had no `bot_id`, and adding one was explicitly out of that slice (D10), so cost per bot existed only through `bot_runs`. Migration L has since added `bot_id` and `user_id` (below). Stats still reads `bot_runs.counts.cost_usd` and was not changed.
- **A5: a crashed wake is undercounted,** because its spend never reaches `counts.cost_usd`; the KPI note says "scout wakes" for that reason. This matches the per-bot budget's edge above, where a crashed wake's spend drops out of the sum.
- **Not the same figure as the editor's ≈ ฿/decision.** `GET /model-tiers` estimates a tier's cost per decision (measured or list); Stats reports a version's actual recorded spend over a window.

(source: raw/2026-10-27-statistics.md §Concept, Problem, Owner decisions D10 and Spec decisions S12; §Concept, Assumptions A5; §Concept, How each figure is computed, KPIs; §Components, kpi-row; §Open questions, Other recorded residuals)

## Attribution and the per-person allowance (accounts and roles, 2026-10-29)

Accounts and roles ([[accounts-and-roles]]; migrations #16, service #18 and bot #19, merged and deployed to production on 2026-10-29) attributes bot spend to a bot and a person, and bounds it per person.

**Attribution (migration L).**
- **The columns.** `model_calls` gains nullable `bot_id` (→ `bots`) and `user_id` (→ `users`), and the index `model_calls_user_id_created_idx (user_id, created_at DESC) WHERE user_id IS NOT NULL`.
- **Every bot call carries both ids.** The scout stamps `bot_id` and `user_id = ownerUserId` on every call it collects. So the survivor transaction, `recordBotCalls`, a settled held decide and an abandoned wake's held decide all write both columns (`INSERT_BOT_CALL`). `modelCallValid` refuses a non-UUID id, and then nothing is written.
- **Signals rows stay NULL.** `packages/signals/src` never sets the columns, and `model_spend_daily` is unchanged. Rows written before L read NULL too, so the owner's bot spend before the rollout is not attributed (S4).

**The per-person daily allowance (S16, D4/D5).**
- **The limit.** It is the person's plan's `daily_model_usd`. The `founder` plan's is $0.50 a day.
- **The order, per survivor:**
  1. the per-bot 25 % budget (FU-1, above);
  2. `spent_user + estimate ≤ dailyModelUsd`;
  3. the calls, where the global ceiling's reservation sits.
- **`spent_user`** is `scoutCostForOwnerDay`: the per-bot statement joined by `owner_user_id`, read once per wake per pass. It is added to the wake's tally, any held decide, and the owner's other open wakes of the same Bangkok day, each amount counted once.
- **Over the allowance,** that survivor and every later one of the wake take the template thesis, with no call and nothing reserved.
- **Signals.** `bots_user_budget_reached_total{tier}` (exported at 0 for `jev`, `small_llm` and `large_llm`) and the warn log `bots_user_budget_reached {user_id, bot_id, run_id}`, once per wake.
- **Exempt.** Tier `none`, `NO_SPEND_BUDGET` models, and a wake that already hit the per-bot budget or the ceiling.
- **Fails closed.** A missing allowance or a failed owner read fails the wake before any further call (SF-1, two mutation-checked specs).
- **A tier the plan excludes** runs the whole wake as `none`, with nothing reserved and neither budget consulted (S15; see [[bots-engine]]).
- **Seen on the preview (E2E-004, plan `e2e004`).** At an allowance of 0.0001, bot C's wake proposed with a template thesis and 0 model calls. `bots_user_budget_reached_total{tier="jev"}` went 0 → 1, while the per-bot budget and ceiling counters stayed 0.

**Spend in the operator console (`GET /admin/spend`).**
- **The split.** `ingest_usd` is the `model_calls` rows with `user_id IS NULL`, and `bots_usd` is the rest. Their sum equals `model_spend_daily` for the day, which an integration test checks.
- **Per person.** Each row shows `today_usd` (Σ `cost_usd` for the Bangkok day), `last_7d_usd`, `allowance_usd` and `reached`.
- ***At allowance* is actual spend, not the bot's stop (SC-E2E004, as built over the PRD).** `reached` is `today_usd ≥ allowance_usd`. The bot stops a person earlier, on spend **plus the next survivor's estimate**, so a person the bot has already stopped can show no tag. On the preview, the allowance at 0.0001 with an actual spend of 0.000032 showed no tag; at 0.000032 the tag rendered. The owner kept both rules as built. Details are on [[operator-console]].
- **The ceiling on the service (OQ-1).** The service now reads `MODEL_SPEND_DAILY_CEILING_USD` (optional, default 1.00, parsed exactly as the bot parses it) for Spend's `ceiling_usd`. It must carry the bot's value. In production only the bot chart sets it (`"1.00"`), so the service shows its own default of 1.00. Adding it to the service chart and the root compose is optional owner action OA-SPEND-CHART / OA-SPEND-COMPOSE.
- **Two figures that agree up to known edges.** Stats' cost of decisions reads `bot_runs.counts.cost_usd`, while Spend reads `model_calls`. They agree except for a crashed wake and estimates.

**Open edges.**
- **Ingest can still starve.** Reserving the bots' share of the ceiling away from ingest is still a separate open fix, an intent non-goal. Two people at $0.50 a day can still starve ingest under the default $1.00 ceiling.
- **Bot security N-1 (needs an owner decision).** A crashed wake's committed spend drops out of the person's allowance sum, the same edge as the per-bot budget's. The options are `max(today sum, attributed model_calls sum)` or a restart sweep.
- **FU-5** (above) asked for a per-account cap or a lower share. The source does not say whether the per-person allowance closes it.

(source: raw/2026-10-29-accounts-roles.md §Database, Migration L and Notes on the schema; §API, Bot: allowance, tier entitlement, attribution; §API, Spend; §Concept, Decisions during the build OQ-1, PB-1..3; §Concept, Spec corrections SC-E2E004; §Test plan, What each E2E check showed, E2E-004; §Open questions)

## The `post_mortem` stage and learn spend (learning loop, 2026-10-30)

The learning loop ([[learning-loop]]; migrations #14, service #16 and bot #17, merged and deployed to production on 2026-10-30) adds a sixth model stage for its labelling job and counts its spend against both bot budgets.

**M's seed and stage CHECKs.**

```sql
INSERT INTO model_routes (stage, provider, model_id, fallback_provider, fallback_model_id) VALUES
    ('post_mortem', 'openrouter', 'anthropic/claude-haiku-5.5', NULL, NULL);
```

- M re-creates `model_routes_stage_check`, `model_calls_stage_check` and `prompt_versions_stage_check` to add `post_mortem` (`model_calls` keeps `eval`). After M there are **six routes**. The price row is Haiku's, already seeded by H, so M adds no price.
- The bot records `post_mortem.v1` in `prompt_versions` with its SHA-256, so **six prompt versions** exist now. A wording change is `post_mortem.v2`.
- M's Down deletes the route and narrows the CHECKs, but fails loudly while a `model_calls` or `prompt_versions` row has stage `post_mortem` (see [[centralized-migrations]]).
- **D9.** Proposals come from Haiku; moving to Sonnet would be a data change later.

**How a labelling call runs.**
- The labeller opens the stage through `openSignalsModels`, the same router, ledger, ceiling, reservations and deadline as the signals and bot stages. It reads `OPENROUTER_API_KEY`, the existing key name, through the signals router. There is no fallback.
- One call per candidate loss. The prompt carries the decision, the price path and up to 10 later signals, and no key, body or URL. The reply `{label, rationale}` is Ajv-checked.
- The `model_calls` row, the spend upsert, the `post_mortem` write and the `post_mortem_proposals` row commit in one READ COMMITTED transaction per proposal. If the proposal write fails after a paid call, the call is still recorded and charged before the reservation is released (bot security SF-1, fixed in round 2). A reply that fails its schema is charged and leaves the decision unlabelled ("charges a schema failure and leaves the decision unlabelled").
- **Start refusals stay local (SF-C2).** A bad `post_mortem` route row no longer stops the signals pipeline or the bot stages. The row is kept with its problem, `assertRoutePrices` prices J's five stages only, and only the labeller's stage start refuses it (`assertPostMortemRoute`), logging `learning_model_stage_failed` once with a closed `problem` (`missing_stage`, `post_mortem_provider`, `post_mortem_fallback`, `fallback_pair`, `missing_price`). A missing provider key likewise refuses only the labeller's stage start, and the losses wait (see [[signals-pipeline]]).

**OD-LEARN-SPEND: attributed, and counted under both budgets.**
- **Why.** The branch-update review found that `post_mortem` calls were unattributed, so the console's Spend counted them as ingest (`user_id IS NULL`), and that learn spend sat outside the per-person allowance. The owner ruled "Count it fully" on 2026-10-29T14:30Z.
- **Attribution.** `post_mortem` `model_calls` rows carry `bot_id` and the owner's `user_id`, so Spend counts them under `bots_usd` and the person. This supersedes PRD §5.3's "Not stored, by decision: … a `bot_id` on `model_calls`".
- **The two day sums (PRD S17, widened).** `BOT_COST_FOR_DAY` sums a bot's scout and learn runs for the Bangkok day; `OWNER_COST_FOR_DAY` (renamed from `SCOUT_COST_FOR_OWNER_DAY`) sums scout and learn runs across the owner's bots, so the scout's per-person allowance above now counts learn spend too. The scout's own per-bot check counts learn spend too: in the merged bot (`2a3a412`), `scoutCostForDay` is an alias of `botCostForDay`, which runs `BOT_COST_FOR_DAY` (`packages/bots/src/pg-store.ts:2530-2533`; checked by the orchestrator after the merge) (see [[bots-engine]]).
- **The labeller's checks, before every call:** first the bot's 25 % share (`BOT_COST_FOR_DAY` + the run's tally + the call's estimate), then `spent_user + tally + estimate ≤ plans.daily_model_usd`. Over either, or on a global ceiling refusal, labelling stops for the run, the remaining losses wait for the next run, and the bot logs `learning_budget_reached {budget: bot | user | ceiling}`.
- **Metrics.** `learning_model_calls_total{stage: post_mortem}` and `learning_model_cost_usd_today` (this process's Bangkok-day tally).
- **Verified.** Named titles "stops at the bot's daily share and leaves the rest waiting" and "sums scout and learn runs into the bot's day"; integration "stops at the bot's share" and "pg store on M: bot cost today". On PV6, `LEARNING_BOTS` read `daily_model_usd 0.500000` for 3 of 3 eligible bots, and `OWNER_COST_FOR_DAY` read 0.000029, the expected scout + learn sum. Learn inclusion itself is proven by the integration specs, because the preview's learn runs cost $0.

**Recorded residuals and open edges.**
- **Per runner.** The 25 % share and the per-person allowance each hold per runner, so a concurrent scout wake and learning run do not see each other's in-flight tally. The global ceiling holds.
- **Pre-fix rows** keep NULL attribution: 12 on the preview, none in production.
- **The report's budget line** shows the bot share only, and there is no labeller counter for an allowance stop.
- **A duplicate on reconnect.** The fallback call record may duplicate a `model_calls` row on a commit-then-connection error, which over-counts (a stricter ceiling).
- **A crashed learning run's** swept `cost_usd` counts only its proposals' costs.
- **Stats' cost of decisions** sums `bot_runs.counts.cost_usd` over runs of any loop, so it includes labelling spend (see [[stats-read-api]]).

**The OpenRouter key (owner action, open).** Production labelling uses the `post_mortem` route on OpenRouter Haiku, as does production `bot_thesis`. On the preview the OpenRouter key was refused on every call: all 12 `post_mortem` calls (4xx other than 429, 0 tokens, $0, `learning_model_stage_failed … DecideRejectedError` ×12), and every extraction call on that preview since 15:28. If production shares that key, labelling will not run there; each attempted loss logs `learning_model_stage_failed`, is charged $0 and waits for the next run. After checking the key, re-run one learning run on a bot with closed unlabelled losses to close FR-LL-E2E-003's model half and A6. The key is referred to by name only; its value is never recorded here.

(source: raw/2026-10-30-learning-loop.md §Concept, The four jobs, `labels.ts`; §Concept, Owner decisions D9; §Concept, Decisions during the build OD-LEARN-SPEND; §Concept, Spec corrections, OD-LEARN-SPEND, SF-C2 and A missing provider key; §Concept, Branch update onto L; §Concept, Review history; §Database, Migration M and Notes on the schema; §API, Bot side; §Test plan, Named acceptance tests, Preview runs and What each seeded E2E showed; §Open questions, Owner actions still open and Recorded follow-ups)

## Signals context: a context layer with no model spend (2026-10-30)

- **The owner's constraint.** Coverage and tone anomalies and upcoming earnings were to be noticed **without a model call per article, inside the $1/day ceiling**. Any model call per GDELT article is a non-goal.
- **Zero spend.** About 192 GDELT windows and 1.38 GB a day are streamed and discarded with **zero model spend**. The `context` runner makes no model call; the model ids `context.v1` on a coverage signal are a label, not a routed model. The integration spec "gdelt: a window adds nothing to the ledger" pins this. The 24 h soak (FR-SC-E2E-001, unverified) is to confirm `model_spend_daily` is unchanged by GDELT.
- **Where spend can rise.** The scout's context and calendar paths feed the unchanged rank-and-cap step **before** any model call. A survivor from them is a normal survivor for `bot_decide` and `bot_thesis`, under the per-bot budget, the per-person allowance and the ceiling. Their survivors take `impact_w = min_impact` and `p = null`, so a signal-driven survivor outranks them at equal allocation (see [[bots-engine]]).
- **A new prompt version.** `bot_thesis.v2` (PB8) is live beside `bot_thesis.v1`, because v1 described `market_state` as chart state only. After the merges the bot records 7 prompt versions.
- **Not model spend: the Finnhub budget.** The earnings refresh shares a 50-per-minute **request** budget with Finnhub company news (see [[event-calendar]]). It is a rate limit, not a ledger entry.
- **FR-SC-E2E-003 was not run** because a wake with both paths on would call the paid model router on the owner's key.

(source: raw/2026-10-30-signals-context.md §Concept, The problem; non-goals; §Database, Volume; §Concept, How it runs, 4 and 5; §Concept, Runtime counts; §Test plan, Ingest titles and Unverified end-to-end checks)

## Related pages

- [[signals-pipeline]]: the stages that spend through this ledger, and the fallback
- [[signals-ingest]]: the slice-3a overview and acceptance
- [[source-registry-and-ingest]]: the other key-gated providers (Finnhub, SET)
- [[centralized-migrations]]: migration H, which seeds the routes and prices
- [[market-data-worker]]: the bot `loadConfig` that reads the variables
- [[bots]]: slice 6, whose bots spend through this ledger
- [[bots-engine]]: the scout's bounded calls, carried wakes and the per-bot budget
- [[bot-versions-and-runs]]: the service-side FU-1 caps and `GET /model-tiers`
- [[statistics]]: slice 7, whose KPI strip shows each version's cost of decisions
- [[stats-read-api]]: the `cost_usd`, `cost_thb`, `usd_thb` and `scout_wakes` definitions
- [[accounts-and-roles]]: plans as data, the founder allowance and the attribution columns
- [[operator-console]]: the Spend view, its ingest/bots split and *At allowance*
- [[learning-loop]]: slice 8, whose `post_mortem` labeller spends through this ledger under OD-LEARN-SPEND
- [[signals-context]]: spec 3b, a context layer and calendar with no model call per article
