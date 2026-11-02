# Signals pipeline (`packages/signals`: triage, extraction, scoring)

**Summary**: Since slice 3a (merged 2026-10-11), the bot's `runner:signals` moves each stored document through three model stages. **Triage** is Jev: is the document material, what kind of event is it, and how severe? **Extraction** is OpenRouter with `anthropic/claude-haiku-5.5`, which returns strict JSON naming the companies involved, including implied ones. **Scoring** is Jev again: per candidate instrument, does the document apply, and in which direction and over what horizon? The principle is D3, "the LLM names, Jev scores": the language model never forecasts, and every probability comes from Jev. Both providers sit behind one `decide()` port. Each stage commits in one transaction, so a crash resumes from the last stage. Each surviving (document, instrument) pair becomes a `signals` row with an impact score, published after commit as the C-SIG-1 message. Every call is charged to the spend ledger described on [[model-routes-and-spend]]. Since the signals page (slice 4, 2026-10-12), the service reads these rows back, and the expanded Signals row shows them as Extracted and Model view (see [[signals-read-api]]). Since bots (slice 6, merged 2026-10-21, not deployed), the bot's general engine reuses the same router, ledger and ceiling for two more stages, `bot_decide` and `bot_thesis`, and its scout reads `signals` to propose candidates (see [[bots-engine]]). Since the learning loop (slice 8, merged and deployed 2026-10-30), a sixth stage on the same router, `post_mortem`, labels losing bot entries, and a bad `post_mortem` route row no longer stops this pipeline (SF-C2; see [[learning-loop]]). **Since signals context (merged 2026-10-30),** a second writer adds `signals` rows without this pipeline: the `context` runner's **coverage signals**. Each is born on a synthetic document already at `stage = signalled`, so `runner:signals` never triages it, and it makes no model call. `signals.origin` tells the two apart (`document` here, `context` there). Every trigger read filters `origin = 'document'` (see [[context-features-and-coverage-signals]]).

**Sources**: `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-21-bots.md` (the bot stages and the scout's signal reads only); `raw/2026-10-29-accounts-roles.md` (unattributed signals spend and the ingest share only); `raw/2026-10-30-learning-loop.md` (the `post_mortem` stage in the signals package and SF-C2 only); `raw/2026-10-30-signals-context.md` (coverage signals, `signals.origin`, the novelty filter and prompt versions only)

**Last updated**: 2026-10-31

---

## Principle

The research brief's strategy is primary source, good extraction and a drift horizon. The language model extracts and never forecasts, and **a calibrated probability is the only thing passed between components**. Under D3 the LLM reads and names instruments, and Jev supplies every probability. In the owner's probe, Jev reported a genuine 40/37/23 direction split where an LLM would have asserted a direction. The full distribution is stored (`p_up`, `p_down`, `p_neutral`), so outcome O2, "calibrated probability, honestly", can be audited (source: raw/2026-10-11-signals-ingest.md §Concept, Problem, Chosen design D3 and Outcomes).

## The stage machine

```
stored ──triage──► triaged ──(material)──► extracted ──► scored ──► signalled
   │                  │ not material / routine            │ no candidate applies / no_instrument
   └─ duplicate       └─► skipped                         └─► skipped
quarantined ◄── any model stage on a contract failure (skip_reason = the stage)
```

- `documents.stage` is one of `stored`, `triaged`, `extracted`, `scored`, `signalled`, `skipped` or `quarantined`.
- `skip_reason` is one of `duplicate`, `not_material`, `routine`, `no_instrument`, `not_relevant`, `withdrawn`, `triage`, `extraction` or `scoring`. The last three name the stage of a quarantine (ORCH-8).
- `queued_reason` is one of `ceiling`, `missing_key` or `provider_unavailable`. A queued document waits without being dropped (see [[model-routes-and-spend]]).

(source: raw/2026-10-11-signals-ingest.md §API, Signals pipeline; §Database, Key shapes and ORCH-8)

## Sweeps and transactions

- `runner:signals` sweeps every 10 s from the previous start. Each sweep takes at most 20 unqueued documents, newest first (`published_at DESC`), with at most 2 in flight.
- Each stage commits its rows, its `model_calls` row, the `model_spend_daily` upsert and the new `stage` in **one transaction**. No store call spans a model call, so a crash resumes from the last committed stage.
- Failure backoff runs from 5 minutes to 1 hour and is kept in memory (code-signals W2, `2b908c6`).
- **Stage reuse.** A stage result stored for `(document, stage, prompt version)` is reused at no charge, whichever model answered. BOT-D1, a stall found at S13 and fixed in `2b908c6`, came from scoring reading the extraction by the route's model id while the row was stored under the provider-reported id. The read is now `readExtraction(documentId, promptVersion)`, newest row.

(source: raw/2026-10-11-signals-ingest.md §API, Signals pipeline, Sweeps and Stage reuse)

## The `decide()` port

- `decide/types.ts` defines one interface with two adapters: Jev (`decide/jev.ts`) and the small LLM (`decide/small-llm.ts`, an OpenRouter chat completion).
- `decide.contract.spec.ts` runs both adapters against recorded fixtures. Those fixtures are constructed from the documented shapes and the owner's probe answers (R-SIG-13, ORCH-7); they are not live captures.
- The Jev question texts are asserted **byte-equal** to `tidewatch-specs/signals-ingest/jev-probe/*.questions.json` (FR-SIG-BRN-001). A one-character change fails three tests.

(source: raw/2026-10-11-signals-ingest.md §API, `decide()` port; §Open questions, Other open items)

## Triage (Jev)

- `POST https://api.typesafe.ai/v1/systemone`, model `jev-1.13.0`, with a bearer key.
- The state sent is `{source, published_at, title, body: excerpt}`, where the excerpt is the first 32,000 characters (R-SIG-25).
- Three questions: `is_material` (Noul), `event_type` (a Choice over the 15 types) and `severity` (a Score).
- **Gates.** Below the kind's `material_threshold` (filing 0.50, exchange 0.50, wire 0.60, media 0.70; PD3), the document becomes `skipped`/`not_material`. An `other` event with severity under 1 becomes `skipped`/`routine`.
- Structured documents (Binance TH listings) skip extraction.

`event_type` is a closed CHECK of 15 values on `triage` and `signals`: `earnings`, `guidance`, `m_and_a`, `financing`, `insider`, `regulatory`, `product`, `legal`, `macro_rate`, `macro_data`, `listing`, `halt`, `hack`, `supply` and `other`. A new type needs a migration (PRD S12). `severity` is `numeric(4,2)`, Jev's Score expected value (S11) (source: raw/2026-10-11-signals-ingest.md §API, Triage; §Database).

## Extraction (OpenRouter)

- `POST https://openrouter.ai/api/v1/chat/completions`, model `anthropic/claude-haiku-5.5` (from `model_routes`).
- System prompt `extraction.v1` with `cache_control: {type: 'ephemeral'}`. The user turn is `{title, published_at, source, body ≤ 12k tokens, alias_candidates}`.
- `response_format: {type: 'json_schema', json_schema: {name: 'extraction_v1', strict: true, schema}}`, with `provider: {require_parameters: true}`.
- **`max_tokens` is 2500** (`EXTRACTION_MAX_TOKENS`, ORCH-17). At 1200, 51 of 58 failed calls on the preview had stopped with truncated JSON. The worst-case output cost per call is $0.00125.
- **No `temperature`** (ORCH-16, also removed from the small-LLM adapter). OpenRouter answered 404 "No endpoints found…" for this model with `temperature: 0` plus `require_parameters` (PV-1). Determinism rests on strict structured output plus Ajv.
- **Ajv on every reply.** Strict structured outputs refuse `maxLength`/`maxItems`, so the request schema moves them into descriptions. Ajv (strict mode, `allErrors`) enforces the full limits client-side: `why` ≤ 200, `key_facts` ≤ 8 of ≤ 160, `rationale` ≤ 900, `additionalProperties: false`.
- An invalid reply is retried once with the error appended (`signals_extraction_invalid`, attempts 1 and 2), then quarantined `schema_invalid`. A 4xx other than 429 is `provider_rejected`.
- The prompt asks for named companies and up to five implied ones, each with a one-sentence `why`. **It never asks for a direction or a probability.**
- The prompt hash covers `{system, schema}` and did not change with ORCH-17 (`652f70db…`). `extractions` is `UNIQUE (document_id, prompt_version, model_id)`.

(source: raw/2026-10-11-signals-ingest.md §API, Extraction; §Concept, ORCH-16, ORCH-17 and PV-1; §Test plan, Reviews; §Database)

## Name resolution (§4.9)

An extracted `ticker` resolves first: its `exchange` decides `.BK@webull`, `@webull` or `@binance-th`. Otherwise an exact case-insensitive `name`/`thai_name` match is tried. Otherwise a row goes into `extraction_unresolved`, the review list, which has no UI and is read by SQL. A document with no resolved candidate becomes `skipped`/`no_instrument`, and its facts are kept. The aliases are on [[instrument-master]], and the earlier alias pass at ingest is on [[source-registry-and-ingest]] (source: raw/2026-10-11-signals-ingest.md §API, Name resolution; §Concept, What the user sees).

## Scoring (Jev)

- At most 12 candidates, alias-named first.
- **Request 1** asks `<slug>_applies` for every candidate. Under 0.6 (`applies_threshold`), the candidate's outcome is `not_relevant`.
- **Request 2** asks direction `{up, down, neutral}` and horizon `{intraday, days, weeks}` for the survivors only (PRD S5).
- **Direction (R-SIG-7).** `neutral` if and only if `p_neutral ≥ 0.5`; else `up` if `p_up ≥ p_down`; else `down`. `p` is the probability of the stored direction.

(source: raw/2026-10-11-signals-ingest.md §API, Scoring)

## Impact (`scoring_versions` v1)

Scoring version 1 is a seed row in migration H, so a change is a data migration:

```json
{"material_threshold": {"filing": 0.50, "exchange": 0.50, "wire": 0.60, "media": 0.70},
 "applies_threshold": 0.60, "novelty_window_days": 5,
 "half_life_hours": {"intraday": 2, "days": 24, "weeks": 120},
 "novelty_w": {"first": 1.0, "repeat": 0.6}, "mention_w": {"named": 1.0, "implied": 0.8},
 "neutral_min_p": 0.5}
```

- `p_dir = p_up / (p_up + p_down)`.
- `conviction = max(0, 2·p_dir − 1)·(1 − p_neutral)` for up, `max(0, 1 − 2·p_dir)·(1 − p_neutral)` for down, and 0 for neutral.
- `impact = conviction × severity/5 × novelty_w × freshness × credibility × mention_w`, rounded to 4 decimals.
- `freshness = exp(−ln2·Δt / half_life(horizon))`, at scoring time.
- `novelty` is `first` unless a signal exists for the same `(instrument_id, event_type)` within 5 days.
- `credibility` comes from the source tier (filing 1.00, exchange 0.95, wire 0.85, media 0.60; see [[source-registry-and-ingest]]).
- `scoring.spec.ts` reproduces the PRD's worked values exactly: 0.0124 (an NVDA supply wire), 0.0907 (AMD) and 0.4224 (an NVDA 8-K).

(source: raw/2026-10-11-signals-ingest.md §Database, Seeds; §API, Impact)

## Route fallback and start checks

- **Fallback.** After 15 minutes of continuous Jev 5xx, triage and scoring use the small LLM with the route's `fallback_model_id`. `signals_route_fallback` is logged at most once an hour. One Jev attempt every 5 minutes ends the fallback. Every row records the model that actually answered.
- **Prompt versions.** `recordPromptVersions` records `(version, stage, sha256)` at start and fails the start if a prompt changed under an old version (`PromptVersionConflictError`). A database that ran a pre-`2b908c6` image needs `DELETE FROM prompt_versions WHERE prompt_version='extraction.v1'`, because the old hash was `88d3faa7`. The owner's database never ran one. **After signals context and learning-loop merged (2026-10-30), the bot records 7 prompt versions:** `triage.v1`, `extraction.v1`, `scoring.v1`, `bot_decide.v1`, `bot_thesis.v1`, `bot_thesis.v2` (new, recorded beside v1) and `post_mortem.v1` (source: raw/2026-10-30-signals-context.md §Concept, Runtime counts after the merges).
- **Prices.** A route or fallback without a valid `model_prices` row refuses the start (`RouteConfigError` `missing_price` / `missing_fallback_price`; code-signals W1). See [[model-routes-and-spend]].

(source: raw/2026-10-11-signals-ingest.md §API, Route fallback and Start checks)

## The signal transaction and the publish

- **One transaction per document.** Every surviving candidate becomes a `signals` row, the candidate's `outcome` becomes `signal`, and the document becomes `stage = signalled`. `UNIQUE (document_id, instrument_id)` holds.
- **Row contents.** `tier` is copied from the source and `scoring_version` is 1. The three model ids (`triage_model_id`, `extraction_model_id`, `scoring_model_id`) are stored, and `prompt_version` is the extraction prompt version. For structured sources, `extraction_model_id` and `prompt_version` read `structured` (R-SIG-8).
- **Publish after commit.** Only after commit is each row logged `signals_emitted`, counted, and published by `publishSignal` to `sig:<instrument_id>` with the C-SIG-1 bytes. A signal is never throttled or coalesced. A failed publish logs `signals_publish_failed` and rolls nothing back; nothing is replayed, and consumers resync from REST. The message is on [[signal-message-contract]].

```sql
-- signals (excerpt): one row per surviving (document, instrument)
direction text NOT NULL CHECK (direction IN ('up', 'down', 'neutral')),
p, p_up, p_down, p_neutral, applies_p numeric(4,3), horizon text CHECK (horizon IN ('intraday', 'days', 'weeks')),
novelty text CHECK (novelty IN ('first', 'repeat')), mention text CHECK (mention IN ('named', 'implied')),
conviction numeric(5,4), impact numeric(5,4), scoring_version integer REFERENCES scoring_versions,
triage_model_id, extraction_model_id, scoring_model_id, prompt_version text NOT NULL,
UNIQUE (document_id, instrument_id)
```

Indexes: `signals_instrument_created_idx` (which serves the Market watch count) and `signals_created_idx` (source: raw/2026-10-11-signals-ingest.md §API, The signal transaction and the publish; §Database).

### A second writer: coverage signals (signals context, 2026-10-30)

- **`signals.origin`** (migration N): `text NOT NULL DEFAULT 'document' CHECK (origin IN ('document', 'context'))`, with the partial index `signals_origin_created_idx (origin, created_at DESC) WHERE origin = 'context'`. Rows this pipeline writes read `document`.
- **Coverage signals** come from the bot's `context` runner, not from `runner:signals`. Each one writes a synthetic `documents` row with `stage = signalled` (so it is never triaged), a `document_versions` row, a `document_instruments` subject row and a `signals` row with `origin = 'context'`, `p 0.000`, `p_neutral 1.000`, `impact 0.0000`, `event_type other`, and model ids and `prompt_version` `context.v1`. It makes no model call and adds nothing to the spend ledger. The canonical URL `tidewatch://context/<instrument_id>/<bkk_day>` makes it one per instrument per Bangkok day.
- **Novelty ignores them.** `LATEST_SIGNAL`, the signals novelty read, filters `origin = 'document'` since S17 (bot review r1 found it unfiltered). Spec "signals: novelty ignores coverage signals".
- **Publish.** Coverage signals go out as ordinary C-SIG-1 messages after their commit, like this pipeline's rows.

The full mechanism is on [[context-features-and-coverage-signals]] (source: raw/2026-10-30-signals-context.md §Concept, How it runs, 4. Context runner, Coverage signals and 6. Never a trigger; §Database; §Concept, Review history)

## Jobs

| Job | Lock | Behaviour |
|---|---|---|
| `signals-requeue --reason <schema_invalid\|contract_violation\|provider_rejected>` | `job:signals-requeue` | Moves quarantined documents with that reason back to `stored` in one transaction, clearing `skip_reason` and `queued_reason`. Finished stages are reused without a second charge. The CLI accepts six reasons, but the job refuses the ingest-time ones with exit 1. |
| `signals-eval [--set labelled-filings-v1]` | `job:signals-eval` | Rebuilds each labelled filing into the entry the collector would store, then runs ingest resolution, triage, extraction and §4.9 resolution through the live routes, prices and ceiling, recording calls as `stage = eval`. It write-tests its output directory before any paid call. If the ceiling or a provider stops it, it writes `complete: false` and exits 1. It spends money and is never part of `test`. The labelled set is not in the image, so on a container it is copied in (`VERIFICATION.md`). |

On the preview, `signals-requeue` moved 138 `provider_rejected` and 30 `schema_invalid` documents back to `stored` after the fixes. Of the 30, 28 passed extraction. One still hit the 2500 cap, and one failed `maxLength` on a key fact (source: raw/2026-10-11-signals-ingest.md §API, Jobs; §Test plan, Preview pre-soak captures).

## Measured quality (FR-SIG-BRN-011)

| Run | Bot | Instrument resolution | `event_type` | Wires (feed-only) | Calls / cost |
|---|---|---|---|---|---|
| 1 | before ORCH-18 | 85% (85/100) | 94% | materiality 95%, `event_type` 60% | 196 / $0.108 |
| 2 (after a forced CIK refresh) | before ORCH-18 | 89% (89/100) | 95% | as run 1 | $0.109 |
| **3** | `53cb76d` | **tracked 100% (100/100)**; all-labelled 89% | **94%** | materiality 95% (19/20), `event_type` 60% (12/20) | 199 / $0.116077 |

- Run 2's ten misses were labelled counterparties that are not Tidewatch instruments, which led to ORCH-18: resolution is scored against the "tracked" labelled instruments, and the 90% bar applies to that figure.
- **The labelled set** (`packages/signals/fixtures/labelled-filings-v1`) holds 100 EDGAR 8-K/6-K filings and 20 PR Newswire feed items, fetched once. They were labelled by claude-opus-5-5, and **every entry is `review_status: "unreviewed"`** (A5). The owner's review is planned after the soak, starting with the low-confidence entries in `review-note.txt`.
- 10 of the 20 wire items are not in English, and only 1 is labelled material, so the wire materiality figure says little about recall (A8).

(source: raw/2026-10-11-signals-ingest.md §Test plan, Eval; §Concept, ORCH-18)

**Reused by the bot stages (slice 6, 2026-10-21).** The general bot engine opens `bot_decide` and `bot_thesis` on the signals router, ledger and ceiling (`openSignalsModels`). Tier `jev` uses the `bot_decide` route (`jev-1.13.0`, Haiku fallback); `small_llm` and `large_llm` use the small-LLM adapter with Haiku or `anthropic/claude-sonnet-5.5`. Prompts `bot_decide.v1` and `bot_thesis.v1` are recorded in `prompt_versions` on first start, and bot S4 added `thesis.ts` and the two prompt files to `packages/signals/src/`. J widens the three stage CHECKs, and the signals harness specs were updated for J's two route rows and five prompt versions. Signals-ingest's ORCH-13 charge for deadline-cut calls applies to the bot stages too. Details on [[bots-engine]] and [[model-routes-and-spend]] (source: raw/2026-10-21-bots.md §The bot engine, Model stages; §Files touched, tidewatch-bot S4 and S13; §Concept, Rulings, ORCH-13 note).

**Signals spend stays unattributed (accounts and roles, 2026-10-29).** Migration L added nullable `model_calls.bot_id` and `user_id`. `packages/signals/src` never sets them, so every triage, extraction, scoring and eval row reads NULL in both, and `model_spend_daily` is unchanged. The bot stages, which run on this router and ledger, now stamp both ids. The operator console's Spend view counts the NULL-`user_id` rows as `ingest_usd`, beside `bots_usd`, and the two sum to `model_spend_daily`. **Open:** the bots' share of the shared ceiling is still not reserved away from ingest. Each person's bots may spend up to the plan's $0.50 a day, so two people can still starve ingest under the default $1.00 ceiling (see [[model-routes-and-spend]] and [[accounts-and-roles]]) (source: raw/2026-10-29-accounts-roles.md §Database, Notes on the schema; §API, Bot: allowance, tier entitlement, attribution and Spend; §Open questions, Outside the build).

**The `post_mortem` stage and SF-C2 (learning loop, 2026-10-30).** tidewatch-bot #17 (merge `2a3a412`) added `post-mortem.ts` and `prompts/post-mortem.v1.ts` to `packages/signals/src/`, and the learning runner's labeller opens the `post_mortem` stage on this router, ledger and ceiling (`openSignalsModels`), on the route M seeds (`openrouter`, `anthropic/claude-haiku-5.5`, no fallback). The signals readers treat that route as optional. Code review round 1 found that a bad `post_mortem` route row stopped the whole signals pipeline (SF-C2). In round 2 the bad row is kept with its problem, `assertRoutePrices` prices only J's five stages, and only the labeller's stage start refuses the row (`assertPostMortemRoute`), logging `learning_model_stage_failed` once. Triage, extraction, scoring and the bot stages carry on. A missing provider key likewise refuses only the labeller's stage start. The same PR modified `packages/signals/src/{index,prompt-versions,routes,store}.ts` and the specs `metrics`, `pg-store.int`, `pipeline.int`, `prompt-versions`, `prompts`, `routes`, `runner` and `memory-store`; after M there are six routes and six prompt versions. **The preview's OpenRouter key** was refused on every call, extraction included, from 15:28 on 2026-10-28; whether production shares that key is an open owner check (see [[model-routes-and-spend]] and [[learning-loop]]) (source: raw/2026-10-30-learning-loop.md §Concept, The four jobs, `labels.ts`; §Concept, Spec corrections, SF-C2 and A missing provider key; §Concept, Review history; §Files touched, tidewatch-bot; §Test plan, What each seeded E2E showed; §Open questions, Owner actions still open).

**The scout reads `signals` (slice 6).** A general bot's scout takes `up` signals since its previous wake with a weighted impact (impact × source weight × class weight) at or above `scout.min_impact` and a horizon in its policy, groups them per instrument (at most 20 signal ids), and caps per class before any model call. A `down` signal over the threshold is recorded as a short `propose` and never entered (long only, D12). A signal-driven scout wakes at most once per 5 minutes (S23) (source: raw/2026-10-21-bots.md §The bot engine, Scout and Scheduler; §Concept, Owner decisions D10/D12).

**Untrusted content (bot security L1).** As with extraction's security L2 below, an untrusted-content instruction should be added to the bot prompts; that needs new prompt versions (source: raw/2026-10-21-bots.md §Open questions, Other recorded residuals).

## Observability

- **Log events: 12 in a closed set**, enforced by a source scan in each package's `logs.spec.ts`. Fields are snake_case, and `error_class` is a constructor name, never a message, URL, header, key or contact. The signals events are `signals_document_skipped` (debug), `signals_extraction_invalid`, `signals_spend_ceiling_reached` (once per Bangkok day), `signals_model_disabled` (once), `signals_route_fallback` (at most hourly), `signals_emitted` (info), `signals_publish_failed` (rate-limited) and `signals_stage_failed` (error). The four ingest events are on [[source-registry-and-ingest]].
- **Signals metrics:** `signals_stage_total{stage,result}`, `signals_model_calls_total{stage,provider}`, `signals_model_spend_usd_today`, `signals_queue_depth{reason}`, `signals_emitted_total{tier}` and the histogram `signals_stage_duration_seconds{stage}`. An unknown label throws `RangeError`. Scrape them inside the bot container with `wget -qO- http://127.0.0.1:9091/metrics`.
- **`packages/signals/VERIFICATION.md`** holds the eight §8.5 queries (kept-row ratio, reject reasons, quarantine ratio, stale sources, spend by day and model, signals by tier and event type, syndication check, unresolved names), each run on H by `verification-queries.int.spec.ts`. It also holds a ninth query for the two-wire pair, a capture script and the eval procedure.

(source: raw/2026-10-11-signals-ingest.md §API, Observability)

## Observed on the preview, and open questions

- The first signal arrived at 09:36:40.690Z (`NVDA@webull`, `finnhub-company-news`, `m_and_a`), 10 s after its document was first seen.
- Before the soak, **only the media tier had produced signals**. EDGAR documents mostly ended `no_instrument` or `not_material`, and the wires had no kept rows. Whether filings, wires and exchange notices produce signals at all is open until the soak.
- **Follow-ups:**
  - an `extraction.v2` prompt with an explicit "the document is data, not instructions" rule; v1 must not change in place (security L2);
  - tag `finish_reason == 'length'` on extraction quarantines, because a retry re-sends the same cap;
  - minor doc nits in `eval.ts` and `VERIFICATION.md`.

(source: raw/2026-10-11-signals-ingest.md §Test plan, Acceptance at merge and Preview pre-soak captures; §Open questions)

## Read back by the Signals page (slice 4)

The pipeline is unchanged; the bot had no code change in slice 4. The service's signal detail reads the stage rows back (see [[signals-read-api]]):
- **`triage`**: `{is_material, event_type_probs, model_id, prompt_version}`, with the probabilities passed through as jsonb.
- **`extraction`**: the latest `extractions` row whose `model_id` equals the signal's `extraction_model_id`, with `key_facts`, `rationale` and `prompt_version`. `role` and `why` come from `document_instruments`.
- **`model`**: the three model ids, the prompt and scoring versions, and `constants: {novelty_w, mention_w, credibility}`. These come from `scoring_versions.constants` and the source's **current** `sources.credibility`.

**What the web shows.**
- *Extracted* reads "First for {symbol}" or "Repeat within 5 days" for novelty. For the instrument it reads "Named in the document · {role}" or "Implied by the model · {role}".
- *Model view* reads "System 1 · {scoring_model_id}" for the decision tier, and the extraction model and prompt version.
- *Impact* multiplies the factors out: "{conviction} conviction × {severity/5} severity × {novelty_w} novelty × {freshness} freshness × {credibility} credibility × {mention_w} mention = {impact}".

**Freshness at creation (ORCH-13, preview finding F1).**
- PRD §4.5 assumed the freshness factor would read 1.00. That premise was wrong against slice 3a's §4.11, the impact formula above, which takes freshness at scoring time. For the preview's NVDA row, the other factors multiplied to 0.2753, but the stored impact was 0.1568, because freshness was 0.5697.
- The web now computes the real freshness at creation, `exp(−ln2 · (created_at − published_at) / half_life)`, in `freshnessAtCreation`. It uses `HALF_LIFE_HOURS` intraday 2, days 24 and weeks 120, matching scoring version 1. The factors then multiply to the stored impact. The fix is in the web only.
- **Decay after creation is still not recomputed**, by design. The shown freshness is the value at creation.

**Volume and thresholds seen on the preview.**
- **Few signals.** The instrument master holds 11 instruments, and 460 extraction mentions were unresolved, so filings and wires about other companies never become signals. Widening the universe is a follow-up (see [[instrument-master]]).
- **The Signals page's default threshold is Impact ≥ 0.30.** Assumption A5 holds that most media rows fall under it. That is consistent with the preview's two media rows (impact 0.0002 and 0.1568), but the sample is very small. Whether 0.30 is the right default needs more days of data.
- **Only media produced rows on 2026-10-12.** No filing, wire or structured-source signal existed, so FR-SP-E2E-003 is unverified (see [[signals-page]]).

(source: raw/2026-10-12-signals-page.md §API, `SignalDetail`; §Components, Expanded row; §Concept, ORCH-13; §Test plan, Acceptance status and Assumption outcomes; §Open questions, Data and volume and Documentation and owner actions)

## Related pages

- [[signals-ingest]]: the slice-3a overview and acceptance
- [[source-registry-and-ingest]]: where documents, tiers and credibility come from
- [[model-routes-and-spend]]: routes, prices, the spend ledger, the ceiling and queue reasons
- [[signal-message-contract]]: the C-SIG-1 message published after commit
- [[instrument-master]]: the aliases that name resolution reads
- [[centralized-migrations]]: migration H's tables, CHECKs and seeds
- [[market-data-worker]]: the `serve` process that runs `runner:signals`
- [[decision-record]]: `decisions.signal_ids[]`, filled by signal-cited user orders since slice 4 and by bots since slice 6
- [[signals-read-api]]: the detail route that reads `triage`, `extractions` and `document_instruments` back
- [[signals-page]]: the slice-4 screen that shows Extracted and Model view
- [[signal-cited-orders]]: the order path that copies scoring fields into `signal_snapshot` and `model`
- [[bots-engine]]: the bot stages that reuse this router, ledger and ceiling, and the scout that reads `signals`
- [[accounts-and-roles]]: the per-person allowance and attribution beside this pipeline's unattributed spend
- [[learning-loop]]: slice 8, whose `post_mortem` labeller runs on this router
- [[context-features-and-coverage-signals]]: the second `signals` writer (`origin = 'context'`), which bypasses these stages
