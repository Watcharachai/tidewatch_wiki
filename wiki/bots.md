# Bots (`bots`, slice 6)

**Summary**: Before slice 6, each user had one fixed, rules-only auto bot, Slack Water, with a single v1 version and Pause/Resume. Nothing created or edited a bot, no bot had acted on a signal, and Trade's recommendation card read "Arrives with bots". Slice 6 made bots versioned configs that the owner creates and tunes. A bot is created from one of four templates or cloned, and every change saves a new version in a new **v2 vocabulary** (`"schema": "bot-config.v2"`). The bot runner runs a **general engine** for v2 configs beside the unchanged 2b pass, which still runs v1 configs. Each general bot has three loops: the **scout** (wakes on a schedule or on signals, ranks and caps before any model call, and writes **candidates** with a thesis and no order), the **manager** (enters, adds, trims and exits on closed bars) and the **guard** (stops, invalidation, daily loss and exposure on every 30 s pass). New bots and new versions start on a 30-day **probation** that records decisions and places no order. *Run now* runs one loop on demand, and the Trade card shows the followed bot's candidate with *Use this order* and *Not this time*. Migration J adds `candidates`, `bot_version_events`, `bot_run_requests` and `bots.probation_until`. The service gained 14 gated routes (59 in all) and seven error codes. The bot gained `packages/waves`, a byte-identical TypeScript port of the Elliott/regime labeller. At the owner's request the build also added the **FU-1 spend caps** (ORCH-10). **Status:** all four PRs merged on 2026-10-21 on the owner's instruction. FR-BT-E2E-001, 003, 004 and 008 passed on the preview; 002 and 007 are partial; 005 and 006 are unverified. The rendered design review (PV2) is **CHANGES REQUESTED**, and a follow-up web fix is in progress. **Not deployed.** **Since slice 7 (statistics, merged and deployed 2026-10-27; see [[statistics]]),** the *Champion* tag has a writer (`POST /bots/{bot_id}/promote`), so `recommendations.follow = "champion"` can resolve to a promoted bot; the attribution route gains four additive net keys, and the version editor's figure beside each weight now reads net of modelled costs. No production champion has been made. **Since accounts and roles (merged and deployed 2026-10-29; see [[accounts-and-roles]]),** the FU-1 active-bot cap, the starting capital and the allowed decision tiers come from the person's plan. The `founder` plan keeps 10, ฿1,000,000 and all four tiers. A tier the plan excludes is refused `not_entitled` and runs as `none` in the bot. Bot spend is attributed per bot and person and held to the plan's $0.50 daily allowance. **Since the learning loop (slice 8, merged and deployed 2026-10-30; see [[learning-loop]]),** each v2 auto bot's detail has a *Learning* section between Candidates and Version, *Run now*'s route takes `learn`, and a monthly learning run can propose a draft that the owner loads into the editor and saves as vN. A learned version always starts on probation, and its learned block is locked in the editor and the clone dialog. **Since signals context (spec 3b, merged 2026-10-30; see [[signals-context]]),** the two discovery paths D10 left out exist as optional, off-by-default config: `schedule.scout.discovery.context` (coverage anomalies) and `.calendar` (upcoming earnings), with two switch rows in the version editor's Schedule group. A version without the key hashes and behaves exactly as before.

**Sources**: `raw/2026-10-21-bots.md`; `raw/2026-10-27-statistics.md` (the slice-7 section only); `raw/2026-10-29-accounts-roles.md` (the accounts-and-roles section only); `raw/2026-10-30-learning-loop.md` (the learning-loop section only); `raw/2026-10-30-signals-context.md` (the signals-context section only); orchestrator corrections of 2026-10-21 (the PV2 verdict and the web FU-1 status, which supersede the source on those two points; see "Corrections to the source")

**Last updated**: 2026-10-31

---

## Stage, stated precisely

| Stage | Status |
|---|---|
| Implemented | **Migrations:** `7a2cc41` (MIG1–MIG3). **Service:** S1–S10, the review fold `65b6670`, FU-1 S11 `1fba53f`, S12 `fa32357` and the doc fix `0ea611b`. **Bot:** S1–S14, review fixes `5705a3e`, `cb21d74`, `b8dc2f4`, `a30b998`, FU-1 S15 `8d1cd37`, S16 `e95c7d7` and the fix `1502f07`. **Web:** S1–S15, review fixes `b4bc039`, `ed37420`, FU-1 S16 `ba8bda4`, S17 `7f0c6d9`, the fix `f6eb8c0`, and the preview fix PF1 `4ab65db` (e2e only). |
| Verified locally | Every step's contract commands were re-run by the orchestrator and exited 0. **Service:** `go vet` (both tags), `go test ./... -race`, `make test-integration` with no `--- SKIP`. A first S2 re-check hit timeouts in untouched code at load averages of 25–45; the low-load re-run passed. **Bot:** `pnpm nx run-many -t lint test typecheck build` and `scripts/sql-integration.sh` on J. **Web:** 4,875 unit tests in 131 files at S16, lint, build, e2e lint and type-check, and the literal-colour grep. |
| Reviewed | Plans and code in every repository. Fix loops: plan review web 1, bot 3, service 1; code review web 2, bot 3 (the cap). |
| Verified on a preview | **Partly.** PV1, PF1, then the Bots, editor and Trade specs at 633/633. PV3: keyboard 12/12, axe 62/62, contrast 74/74, no horizontal scroll 592/592, clipping 8/8. PV5: C12 byte-identical in three repositories. **PV2 (rendered design review): CHANGES REQUESTED** (B1, S1–S3; fix in progress). E2E: 001, 003, 004, 008 passed; 002, 007 partial; 005, 006 unverified. |
| Merged | **Yes**, 2026-10-21, merge commits in plan order (see "Merge record"). Owner instruction: "If done please merge all and continue". |
| Deployed | **No.** The owner applies J (`20261020041046`) to their own database before running the merged service and bot. |
| Documentation pass | The raw source and this wiki update. FR-BT-DOC-002 (OpenAPI and Bruno) is deferred, because `tidewatch-apis` is not a Git repository. |

(source: raw/2026-10-21-bots.md §Concept, Stage, stated precisely; PV2 verdict from the orchestrator correction of 2026-10-21)

## Merge record

| Repo | PR | Range (base..PR head) | Merge commit | Merged at (UTC) |
|---|---|---|---|---|
| tidewatch-migrations | #10 | `52deb26..7a2cc41` | `cd378a3` | 04:08:15Z |
| tidewatch-service | #12 | `1547a89..0ea611b` | `9f1f324` | 04:08:25Z |
| tidewatch-bot | #10 | `ece175a..1502f07` | `81133bf` | 04:08:30Z |
| tidewatch-web | #15 | `918d7b6..4ab65db` | `acbd75d` | 04:49:39Z |

- The web merge waited for PF1. The preview served web `f6eb8c0`; PF1 changed only e2e files.
- The E2E checks continued on the preview after the J, service and bot merges, on the same code.
- `state.json` records `pushedAt` times for the service (04:55Z) and the bot (05:15Z) later than their `mergedAt` (04:08Z). The source takes the merge commits and `mergedAt` as authoritative.
- **Not changed:** `documents/`, `tidewatch-specs`, `tidewatch-apis`, the 2b pass (byte-identical to `ece175a` per bot code review r3), the C10 fixture, the C4 lock order, `/ws`, the Redis contract, the fill model and the indicator job.

(source: raw/2026-10-21-bots.md §Concept, Stage, Merged; §Files touched; Sources, Record notes)

## Corrections to the source

The source document is stale on two points. The orchestrator's corrections of 2026-10-21 are used on this page and on the pages it links:
- **Web FU-1 items: verified**, after the PF1 re-run on the preview. The source (and `verification.md`'s FU-1 table) still read "partial".
- **The rendered design review (PV2) is CHANGES REQUESTED.** The source says it "was still running". A follow-up web fix is in progress for B1, S1, S2 and S3 (see "Design review (PV2)" below and [[design-system-decisions]]).

(source: orchestrator correction of 2026-10-21, superseding raw/2026-10-21-bots.md §Concept, Stage; §Test plan, Acceptance status and Preview runs; Sources, Record notes)

## Why the slice exists

The product's core idea is bots the owner creates and tunes against evidence: pick the sources and tune their weights beside each source's results, pick a decision tier, set a policy, a universe, an allocation and a schedule, save that as a version, and watch it scout, enter and manage positions on paper.

At `main` on 2026-10-16 (service `1547a89`, web `918d7b6`, bot `ece175a`, migrations at I), the runner evaluated only v1 zone bots every 30 s. It had no scheduler, no per-bot lock and no candidates. `decisions` already carried `loop`, `run_id`, `candidate_id`, `signal_ids`, `signal_snapshot`, `model`, `market_state` (with empty `elliott` and `regime` slots) and `exit_reason`, but no `candidates` table existed. The labeller lived only in the service, and the bot cannot call the service.

The roadmap's slice-6 exit test: two auto bots run 7 days on paper without intervention; scout wakes produce candidates and never orders; a guard stop is honoured within 2 minutes whatever the manager's cadence; any config change creates a new version; attribution numbers reconcile with the decision record.

(source: raw/2026-10-21-bots.md §Concept, Problem)

## Outcomes and their result

| # | Outcome | Result |
|---|---|---|
| O1 | A version is the only way to change a bot | **Met.** SVC-003/004 verified. E2E-001 saved v3 on screen and left v2's decisions, runs and orders md5-identical |
| O2 | Three loops on paper, honestly separated | **Met except the week.** BOT-001…008 verified. E2E-003 and E2E-004 passed. E2E-002 partial: the 7-day run was not done (A7) |
| O3 | Allocation is a ceiling, never a target | **Unit-level only.** BOT-009 (scripted week), BOT-002 (40 signals → 5 candidates), BOT-010/011. E2E-005 and E2E-006 **unverified** |
| O4 | Evidence beside every weight | **Met at route level; partial on the preview.** SVC-007/008 verified. E2E-007 partial: attribution agreed for all 10 sources, but with 0 graded decisions the fit could only be refused |
| O5 | Honest cost and probation | **Met.** SVC-009, WEB-006. The probation bot read "Observing · day 1 of 30", wrote a skip with `["observing"]` and placed 0 orders |
| O6 | Recommendations for `me` | **Met.** SVC-010/011, WEB-009, E2E-008 passed |
| O7 | Slack Water unbroken | **Met by tests.** BOT-001/013 with the 2b named specs green; 2b files byte-identical to `ece175a`. SVC-005 (upgrade then save) verified. No real *Upgrade* was saved on the preview |
| O8 | The bot explains itself | **Met.** SVC-006, WEB-004/005; the *Run now* half of E2E-004 passed |

(source: raw/2026-10-21-bots.md §Concept, Outcomes (intent) and their result)

## Owner decisions (intent, 2026-10-16)

The owner took the recommended answer for all thirteen questions and adopted PD1–PD12 in one round, in chat, because the Forge Console Spec studio has no display in the desktop Code tab.

- **D1.** `me` follows a selectable bot: setting `recommendations.follow`, default "champion", falling back to an auto bot with a scout (see [[user-settings]]).
- **D2.** Decision tiers: `bot_decide` on Jev (`jev-1.13.0`, Haiku fallback); `bot_thesis` on Haiku through OpenRouter; `large_llm` on `anthropic/claude-sonnet-5.5`. No `custom` tier and never an OANDA key (see [[model-routes-and-spend]]).
- **D3.** Cost per decision is measured from the ledger's last 7 Bangkok days at 20 calls or more, else list price × a fixed typical request.
- **D4.** Four entry conditions: `immediately`, `zone_turns_buy`, `pullback_ema12`, `elliott_wave2_holding`.
- **D5.** Default TTL: 5 sessions (stock, gold), 3 days (crypto).
- **D6.** 4h is reserved in the vocabulary and refused by validation.
- **D7.** The bot ports the labeller against the five committed fixtures (see [[elliott-regime-labeller]]).
- **D8.** Slack Water's v1 stays executable under the unchanged 2b pass; a legacy bot gets one explicit *Upgrade*; rules-only templates enter directly on a zone event (see [[zone-transition-bot]]).
- **D9.** Probation lasts 30 days and can be overridden; unchecking it writes a `probation_skipped` event.
- **D10.** Discovery is signal-driven and setup-driven; GDELT and calendar discovery are out. Ranking is impact × source weight × class weight, with a per-class cap.
- **D11.** Overview gets *Your strategies*; the Tide brief and an Overview recommendation move to slice 7. (Slice 7 moved them again, with the champion stance on the Chart, to a follow-on spec: its D12.)
- **D12.** Long only. A `down` candidate is recorded as a `propose` with `direction = short` and never entered.
- **D13.** One mockup on the real tokens, at 390, 600, 1080 and 1440 in both themes.
- **PD1–PD12 (abridged):** J's tables; weight defaults 1.0 for filing, exchange and wire sources and 0.6 for media, with attribution beside each weight; a logistic fit, preview only; sizing by `p` within the allocation; exit reasons; the guard on the 30 s pass from the recorded `px:last`; scout wakes at 06:00 and 20:00 Bangkok with `min_impact` 0.45 and a 1h manager with events on; realtime on demand through `realtime_requested_at`; Create and Clone, each bot with its own paper account; `me` uses or declines a candidate; the Bots screen additions; run rows as in 2b.

(source: raw/2026-10-21-bots.md §Concept, Owner decisions and adopted defaults)

## Spec decisions that shaped the build (selected)

- **S1** dispatch by vocabulary; **S3** a fourth tier `none` ("Rules only") with no model call; **S4** caps before calls; **S6** an unmet entry gate is a watch verdict, not a decision; **S7** rules-only configs enter directly on a zone turn; **S8/S11** the bot writes `bots.status` only for the guard pause and the probation flip; **S9** C4''; **S10** *Run now* through a table, never HTTP; **S12** the bot writes `instruments.realtime_requested_at`; **S15** the sparkline from the existing 1m portfolio; **S17** a failed thesis never blocks a candidate; **S18** no manager model call in this slice; **S19** a per-bot advisory lock; **S20** attribution's SQL; **S21** `me`'s sized quantity; **S23** the scout's signal window and the 5-minute signal-wake floor; **S24** closed `counts` keys per loop.

How they work is on [[bots-engine]] (bot side) and [[bot-versions-and-runs]] (service side) (source: raw/2026-10-21-bots.md §Concept, Spec decisions that shaped the build).

## Orchestrator rulings (ORCH-1…10)

| Ruling | Decision |
|---|---|
| ORCH-1 | J planned as MIG steps inside the service plan, as G, H and I were; the migrations repository kept its own worktree, branch and PR and merged first |
| ORCH-2 | The service planner pins the shared contracts in `contracts.md`: J's objects, the §4.2.1 vocabulary, C12, C13, C4'', C11' and the §6.1 bodies |
| ORCH-3 | J's version, the large-tier price row and the CHECK names are outputs of the MIG step |
| ORCH-4 | Dependency-gated lanes (MIG first; `packages/waves` after the bot plan; engine steps after the contracts; web on mocks after the service plan) |
| ORCH-5 / ORCH-6 | Adopted as recommended on 2026-10-20 after the owner declined the question form twice and replied "Continue"; each stays open to an owner override. 5a the Upgrade per PRD §4.2.5 (four classes at 0.25, `max_symbols`/`max_candidates` 6 each); 5b the probation status rules; 5c the `me` fallback is "running or observing"; 5d housekeeping (follow setting is an object; two bot-side `bots.status` writes; stale guard price → `deferred`; expiry reason `version`; 14 new routes → 59 gated; guard exposure closes counted as `trimmed`). OQ-1 J also re-creates `bot_watch_timeframe_check` with `15m` (a sixth CHECK). OQ-2 `probation: false` on an observing bot → `running`. WEB-OQ-1 the Upgrade saves with `probation: false`. WEB-OQ-2 E2E-005's on-screen half has no element, so it is reported unverified |
| ORCH-7 | Allocation-bar colours per PRD §7.4 and the mockup (see [[design-system-decisions]]) |
| ORCH-8 | Tier `none` makes no model call, the thesis included; `bots_model_calls_total` labels are `{bot_decide, bot_thesis} × {jev, small_llm, large_llm}` |
| ORCH-9 | 9a entries copy `signal_ids`, `signal_snapshot` and `model` from the proposing decision; 9b a skip or observed decision once per candidate and reason, not per bar; 9c the allocation room net of the entry's own fee, pending buys counted; 9d `rule` names the evaluation kind on general-engine `deferred`/`skipped`/`observed` entries |
| ORCH-10 | The FU-1 spend caps added to this build at the owner's request, before the preview checks |

Planner precision P27 (`latestIndicatorRows`, a set-based indicators read) was accepted by bot code review r3. Signals-ingest's ORCH-13 (a call cut after sending is charged at its estimate) was applied to the bot stages in bot fix round 2 (source: raw/2026-10-21-bots.md §Concept, Rulings during the build).

## The FU-1 spend caps (ORCH-10, contracts r2)

Both security reviews raised the same risk: one bot could exhaust the shared daily model-spend ceiling (`MODEL_SPEND_DAILY_CEILING_USD`, default USD 1.00, also used by the signals pipeline), and a signal-driven scout can wake every 5 minutes. On 2026-10-21 at 00:40Z the owner asked for FU-1 in this build. Each plan gained steps after its completed ones (service S11–S12, bot S15–S16, web S16–S17), and the completed steps' evidence carried over. Contracts r2 is a changelog over r1; C12, C11', C13, C4'', J's schema and the route list are unchanged.

1. **Per-class caps.** `limits.max_candidates.<class>` 0–10 and `limits.max_symbols.<class>` 0–20. The service refuses `400 invalid_request {field, reason: out_of_range}`; the bot's v2 reader refuses a stored out-of-range config as `version_unsupported`; the editor shows "Use 10 or fewer." / "Use 20 or fewer.". The templates (5 and 4) and the Upgrade (6 and 6) stay valid.
2. **At most 10 active auto bots per account** (`kind = 'auto'`, `status IN ('running','observing')`). Create, clone and resume refuse an 11th with `409 bot_limit_reached {limit: 10}`. Since accounts and roles, `limit` is the plan's `max_active_auto_bots`, which is 10 on `founder`.
3. ***Run now*: at most 6 per bot and loop in a rolling 60 minutes.** The 7th is `429 run_rate_limited {retry_after_s}` with an integer `Retry-After`.
4. **A per-bot daily model budget** of 25 % of the shared ceiling per Bangkok day, on the two bot stages, bot-side only.

Items 1–3 are detailed on [[bot-versions-and-runs]]; item 4 on [[bots-engine]] and [[model-routes-and-spend]].

**FU-1 verification.** Service bounds, the active-bot cap and the rate limit: verified (S11 unit and integration). The bot reader's bounds and the per-bot budget: verified by unit tests and the harness. **The web parts: verified**, by unit tests and, after PF1, by the preview re-run of `bots.spec.ts`, `bots-editor.spec.ts` and `trade.spec.ts` (633/633), which hold the FU-1 e2e titles; the 429 toast and the editor cap were also exercised by hand on the preview. **The 11th active bot** was not tried on the preview, because it would have left permanent bots on the shared database; it is verified only by `TestBots_ActiveBotCap` and `TestBots_ActiveBotCap_Concurrent`.

(source: raw/2026-10-21-bots.md §Concept, The FU-1 spend caps; §Test plan, Acceptance status, FU-1 items; web status from the orchestrator correction of 2026-10-21)

## What each project gained

| Project | Gained |
|---|---|
| `tidewatch-migrations` | Migration J (`20261020041046_bots_candidates_and_requests`): three tables, `bots.probation_until`, six re-created CHECKs, two model routes and one price row; harness +642/−17. See [[centralized-migrations]] |
| `tidewatch-service` | 14 gated owner-scoped routes (59 gated in all), the v2 validator refusing by dotted field, the four templates as pinned data, the `recommendations.follow` setting, `candidate_id` on orders and skips, seven error codes (five from contracts r1, two from FU-1), `RequiredSchemaVersion` → J. See [[bot-versions-and-runs]] |
| `tidewatch-bot` | `packages/waves`; dispatch by vocabulary, the scheduler, a per-bot lock, run requests, scout, manager, guard, the candidate lifecycle, the probation end, realtime requests, the `bot_decide`/`bot_thesis` stages and the C4'' close stamp. See [[bots-engine]] |
| `tidewatch-web` | Bots list sparkline and tags, *Create bot* and *Clone*, Loops with *Run now*, Candidates, the typed version editor (with *Upgrade*), Overview's *Your strategies*, and the Trade recommendation card with *Follows* and a third pre-fill form. See [[design-system-decisions]] and [[signal-cited-orders]] |

(source: raw/2026-10-21-bots.md, summary block; §Database; §API; §Components)

## What the user sees

- **Bots list.** "{n} bots · paper mode" (plus "· {name} is the champion"), *Create bot*, an *Equity, 30 days* sparkline column, status tags (*Running*, *Paused*, *Observing · day {d} of 30*, a neutral *Champion*), and a v2 strategy line "{template label} · {n} sources · {tier word}".
- **Bot detail.** Head with version tag, status, *Pause/Resume* and *Clone*; the v2 strategy sentence; sections figures, **Loops**, **Candidates**, **Version**, Watch, Positions, Decision record, Checks. The manual bot shows none of Loops, Candidates and Version.
- **Loops.** Scout, Manager and Guard rows, each with *Run now* (*Queued…* until the run appears, then a "{Loop} ran at {HH:mm}: {summary}" toast; refusals and the FU-1 rate-limit toast in words).
- **Candidates.** Instrument, state and reason, "p · impact", the thesis (marked "{tier} · template" when templated), invalidation and TTL; *Show all* and *Load more*.
- ***Create bot* / *Clone*.** Name, four strategy cards (News drift, Filings only, Zone transitions, Blank), starting capital (default 1,000,000, at least 10,000) and *Start on probation (30 days)*, checked.
- **Version editor.** Sources and weights with attribution and *Fit weights from the last 90 days*; four decision-model cards with ≈ ฿/decision; policy and overlays; universe and allocation per class (with the FU-1 cap messages); schedule; *Save as v{seq+1}*. A legacy bot shows *Upgrade to the current vocabulary*.
- **Overview.** *Your strategies* cards between the KPI strip and Market watch, one per auto bot, linking to `/bots?bot={id}`.
- **Trade.** The recommendation card: "{Bot} suggests", a *Follows* select, "p · impact", sized quantity, four reasons, *Use this order* and *Not this time*.

Details of components and copy: [[design-system-decisions]]; the Trade card and pre-fill: [[signal-cited-orders]] (source: raw/2026-10-21-bots.md §Components).

## Review history (abridged)

- **Service:** plan r1 changes requested, then approved through r6 (FU-1). Code r1 approved with three should-fix (a clone race, a status-changing save neither counted nor logged, a README contradiction), folded in `65b6670`; FU-1 r3 code and security approved.
- **Bot:** plan r1 → r9 (ORCH-9 revision r5/r6; FU-1 r7 changes requested for an unbounded midnight carry-over, r8 approved). Code r1–r6: GAP-B2, GAP-B3, W1–W9 (including W4, scout calls blocking the 30 s pass), M1, R1 (deadline-cut calls uncharged), R2-B1, R3-W2 (a hanging provider could push a guard stop to about 160 s; budget cut 20 → 15 s, bound 90 s + W), R4-1, and FU-1 F1. Code-review fix loops reached the cap of 3.
- **Web:** plan r1 changes requested (the allocation-bar colours → ORCH-7), then approved. Code r1: GAP-W1…W4 and a `pendingRuns` leak; r2: `announceRun` wrote a signal inside an effect; FU-1 r4 design B1 (cap messages in the wrong place), fixed in `f6eb8c0`. PF1 code review approved. The rendered review was left to the preview (PV2).

(source: raw/2026-10-21-bots.md §Concept, Review history)

## Test plan and acceptance

All commands are local; there is no CI. Playwright runs only on a preview (`authed-setup`, then `public` + `authed` with `--no-deps`; production build with `--grep-invert @hook`; `sign-out` skipped). The named acceptance tests are listed on [[bot-versions-and-runs]] (service) and [[bots-engine]] (bot) (source: raw/2026-10-21-bots.md §Test plan, Commands).

### Acceptance status (PRD §9)

| ID | Status | Evidence |
|---|---|---|
| FR-BT-MIG-001…003 | Verified | disposable-DB re-checks; bot harness on J |
| FR-BT-SVC-001…012 | Verified (unit and integration, no SKIP) | service S3–S11 re-checks |
| FR-BT-BOT-001…014 | Verified (unit and harness on J) | BOT-004's real-time half is E2E-004 (passed); BOT-009's is E2E-005 and BOT-010's is E2E-006 (both unverified) |
| FR-BT-WEB-001…009 | Verified on the preview | PV1 1053/69/4, then the PF1 re-run 633/633 |
| FR-BT-WEB-010 | Verified on the preview | keyboard 12/12, axe 62/62, contrast ≥ 4.5:1 74/74 |
| FR-BT-WEB-011 | **Not passed: PV2 CHANGES REQUESTED** | code-level design review approved; 280 captures, no horizontal scroll 592/592, clipping 8/8; the rendered review requested changes (B1, S1–S3), fix in progress |
| FR-BT-WEB-012 | Verified | the orchestrator's re-runs |
| FR-BT-E2E-001 | **Passed** | on-screen save of v3, v2 rows md5-identical |
| FR-BT-E2E-002 | **Partial** | two auto bots, complete context, no duplicate on restart; the 7-day run was not done |
| FR-BT-E2E-003 | **Passed** (TTL by a method deviation) | wake at its time, no order, entry on a closed bar, TTL expiry |
| FR-BT-E2E-004 | **Passed** (stop by a method deviation) | *Run now* per loop; guard close 14.8 s after the breach |
| FR-BT-E2E-005 | **Unverified** | not run |
| FR-BT-E2E-006 | **Unverified** | not run |
| FR-BT-E2E-007 | **Partial** | attribution agreed; fit refused at 0 graded decisions |
| FR-BT-E2E-008 | **Passed** | card, *Use this order*, *Not this time* |
| FR-BT-DOC-001 | Verified | doc greps and reviewers' doc checks |
| FR-BT-DOC-002 | Deferred | `tidewatch-apis` is not a Git repository |

(source: raw/2026-10-21-bots.md §Test plan, Acceptance status; FR-BT-WEB-011 from the orchestrator correction of 2026-10-21)

### Preview runs

- **The run.** `bots-1c6ff8ae`, compose project `forge-0199b29a-bots-1c6ff8ae`, isolated with retain on the shared volume `forge-preview-0199b29a_tidewatch-pgdata` at J; 6/6 services healthy. Revisions: migrations `7a2cc41`, service `0ea611b`, bot `1502f07`, web `f6eb8c0`. First up at `http://127.0.0.1:61518/` (2026-10-21T00:15Z), refreshed for FU-1 at `http://127.0.0.1:59343/`. The image check found the FU-1 copy in the web chunks, both new codes in the service binary and `bots_bot_budget_reached_total` in the bot dist. The owner gave the go-ahead for PV1–PV5 and E2E-001…008 on the refreshed preview. See [[forge-preview-gateway]].
- **Database before the checks:** Me and Slack Water only, 0 candidates, at J.
- **PV1 (web `f6eb8c0`, production build).** Credentials were copied to `e2e/.auth` (mode 600) and never read or echoed. 1,131 tests listed. **1053 passed, 69 failed, 4 skipped (live-gated), in 23.5 min.** 11 failures were `@hook` tests, expected on a production build; 58 were real (bots 52, bots-editor 4, trade 1, signals 1), and all were test defects.
- **PF1 (`4ab65db`, test-only).** Re-run of `bots`, `bots-editor` and `trade` with `--grep-invert @hook`: **633 passed, 0 failed**. The Signals focus test passed 3/3 on repeat. PF1 code review approved; its three nits became FU-6.
- **PV3, after PF1:** keyboard 12/12, axe 62/62, contrast 74/74, no horizontal scroll 592/592, clipping 8/8.
- **PV2:** 280 captures (35 states × 2 themes × 4 widths). The rendered review was dispatched while the web merged and returned **CHANGES REQUESTED** (next section).
- **PV5:** C12 is byte-identical in web, service and bot (`44161eb0…`).
- **A3:** `GET /bots` × 30 with 5 bots: p50 17.7 ms, p95 21.1 ms, max 29.6 ms (27.3 ms in integration).
- **`/metrics`:** `bots_bot_budget_reached_total` 0 for all three tiers; `bots_model_cost_usd_today` 0.000227; `bots_running` 2 (the FU-7 defect).

(source: raw/2026-10-21-bots.md §Test plan, Preview runs; PV2 verdict from the orchestrator correction of 2026-10-21)

### Design review (PV2): CHANGES REQUESTED

The rendered review of the 280 captures requested changes after the web had merged. A follow-up web fix is in progress for:
- **B1 (blocking).** The Clone dialog's `class="fixed"` collides with Tailwind's `fixed` utility, so the clone line overlaps the Strategy label.
- **S1.** The cap-message divider placement.
- **S2.** The Policy error placement at 390 px.
- **S3.** The Overview error-line alignment.

`DESIGN.md`'s *Verification evidence* entry for this slice was already planned for a follow-up web PR, and `DESIGN.md` may need a refresh if visuals change (source: orchestrator correction of 2026-10-21; raw/2026-10-21-bots.md §Open questions).

### The E2E checks (2026-10-21, about 04:12–04:50Z)

**Setup.** Three bots were created at 04:12:47Z through `POST /bots` (`news_drift`, v1 `v1·ef8d`), then saved to v2:

| Bot | Tier | Scout | Manager | Status | v2 |
|---|---|---|---|---|---|
| E2E A · none · BTC | `none` | times `["11:22"]` Bangkok | 15m | running | `v2·eb37` |
| E2E B · jev · ETH | `jev` | `signal_driven` | 15m | running | `v2·5589` |
| E2E C · probation | `none` | `signal_driven` | 15m | observing until 2026-11-20 | `v2·43f4` |

At 04:12:53Z two up signals (BTCTHB, ETHTHB) were inserted into the preview database as `documents` plus `signals` rows of source `binance-th-listings`, impact 0.5, p 0.7, horizon `days`.

- **E2E-001 passed.** A's editor save toasted "Saved as v3·417e"; v1 and v2 were unchanged (md5 of v2's 2 decisions, 13 runs and 1 order identical). A raw portfolio comparison differed only in `generated_at` and the now-point's `ts`, as the orchestrator read it. In the same session, 11 Crypto candidates showed "Use 10 or fewer." with `aria-invalid`, no version was written, and the API answered `400 out_of_range` at `config.limits.max_candidates.crypto`.
- **E2E-002 partial.** B's scout woke at 04:13:14Z: 1 candidate, `cost_usd` 0.000227, `p` 0.670, `thesis_source template`. B's manager bought 0.139 ETH at 04:15:14Z (filled 04:16:00); A bought BTC at 04:30:14Z. Every buy carried the full decision context. **Restart:** after B's `stop_px` was raised, the guard wrote a close and placed a sell at 04:46:14.84Z, and the bot restarted at 04:46:15.3Z; afterwards there was one close, one sell, two distinct `client_order_id`s and no duplicate. The 7-day (or 72 h) run was **not done** (A7).
- **E2E-003 passed.** A's scout woke at 04:22:14Z (11:22:14 Bangkok): one run, one candidate, no order. The manager entered only at 04:30:14Z, after the 04:15 bar closed. **TTL (method deviation):** C's `ttl_until` was moved by SQL to now + 90 s; it expired (`ttl`) 20.8 s after `ttl_until`.
- **E2E-004 passed.** *Run now* for scout, manager and guard each showed *Queued…* and was taken within one pass with one `trigger = manual` run. **Stop (method deviation):** with live `px:last` 2,780,999 THB, A's `stop_px` was raised by SQL to 2,920,000; the guard's close came **14.8 s** after the breach, and the position closed **60.1 s** after it. An injected Redis price would not have reached the guard, because the bot reads its own in-process recorded prices.
- **E2E-005 unverified.** The scripted allocation week was not run, the US market was closed, and its on-screen half has no element (ORCH-6 item 5).
- **E2E-006 unverified.** It needs a US stock off the watchlist during US hours.
- **E2E-007 partial.** Attribution on screen, the S20 SQL and the route agreed for all 10 sources (`binance-th-listings` n 1, the rest n 0). *Fit weights* showed "Fitting needs 30 graded decisions. 0 so far." (`409 too_few_decisions`), and the version stayed at seq 2.
- **E2E-008 passed.** Follow set to C; the card showed C's watching BTC candidate (p 0.70, impact 0.50, "up to 1.31% of equity (0.00472 units)", four reasons). *Use this order* placed a `me` buy citing the candidate; *Not this time* wrote a `loop user` skip and set `declined_at`. C read "Observing · day 1 of 30" with 0 orders.
- **FU-1 on the preview.** Six manager requests in the window; the 7th press toasted "Run now is limited to 6 runs an hour. Try again in 57 min." (`retry_after_s` 3398), wrote nothing and left the button idle and focused. An 8th API call answered `429 run_rate_limited`.

(source: raw/2026-10-21-bots.md §Test plan, The E2E checks)

### Defects found on the preview

- **PF1 (test defects, F1–F11).** A page-toast locator matching two `[role=status]` regions; a stale contrast selector after the sparkline column; head buttons moved into `.acts`; `toBeEnabled` treating `aria-disabled` as disabled; focus-ring asserts after a mouse click; the Gold slider restoring 10 %; a selection race; the macOS keyboard *Follows* choice; the `run_pending` mock; a Signals focus flake (F11); and the expected `@hook` failures (F9).
- **Product defect FU-7.** `bots_running` is set by both the 2b pass and the general pass, so it alternates between 1 and 2. Not fixed in this build (see [[bots-engine]]).
- **Found in review, all fixed before merge:** bot GAP-B2, GAP-B3, W1–W9, M1, R1, R2-B1, R2-W1…W4, R3-W1/W2, R4-1/R4-2, FU-1 F1; service the clone race, the uncounted status-changing save, a README contradiction; web GAP-W1…W4, the `pendingRuns` leak, `announceRun`'s effect write, FU-1 B1.

(source: raw/2026-10-21-bots.md §Test plan, Defects found on the preview and their fixes)

### Preview database footprint

The checks left this on the shared retained volume `forge-preview-0199b29a_tidewatch-pgdata`:
- **Three E2E bots**, each with its own paper account, benchmark and marks: A `running` at v3·417e (manager 1D), B `running` at v2·5589 (tier `jev`), C `observing` until 2026-11-20. A preview started on this volume evaluates them like any auto bot.
- **Two injected `documents` and `signals` rows** (source `binance-th-listings`, titles starting "E2E bots preview").
- **Paper orders:** A's and B's buys and guard sells (positions closed); one `me` buy of 0.00472 BTC citing C's candidate (pending at capture).
- **`decisions`** for all of the above, append-only and not deletable.
- **`candidates`:** A's and B's `closed (stop)`; C's `expired (ttl)` with `declined_at` set.
- **Eight `bot_run_requests`** (scout 1, manager 6, guard 1).
- **`user_settings`:** `recommendations.follow` = `{"mode": "bot", "bot_id": <C>}`.

(source: raw/2026-10-21-bots.md §Test plan, Preview database footprint)

### Manual reproduction

1. **Create and save.** *Create bot* (News drift, on probation): the list shows "Observing · day 1 of 30". Change one weight and *Save as v2*: `bot_versions` gains a row while v1 stays.
2. **Run now.** Press it on Scout: *Queued…*, then the toast; `bot_run_requests` holds `taken_at` and `run_id`. Six more presses within an hour give the 429 toast.
3. **A wake.** On a `times` scout, wait for a wake: one scout `bot_runs` row, `proposed` candidates, `propose` decisions and no order.
4. **The guard.** A breach of `px:last` below a held candidate's `stop_px` closes the position within 90 s + W, with `loop guard` and `exit_reason = 'stop'`.
5. **Trade.** Set *Follows* to a bot with a watching candidate; *Use this order* places an order whose decision has `candidate_id`; *Not this time* writes `loop user` with `candidate_id`.
6. **Slack Water.** It keeps its v1 hash and `rule entry/exit` under the 2b pass, and its detail shows *Upgrade to the current vocabulary*.

(source: raw/2026-10-21-bots.md §Test plan, Manual reproduction)

## Operations

- **Order:** J first; then the service and the bot together (they share J's seeds, C4'', C11', C12 and C13); then the web. The service answers `/ready` 503 below J. The bot has no compiled schema check; its SQL harness refuses to run below J.
- **Environment:** no new variables. The large-tier price row was read from OpenRouter's models list at 2026-10-20T04:10:40Z and is cited in J's header.
- **Rollback:** rolling back the bot stops the loops and leaves candidates; the service hides the new routes (the web shows the sections' error states); the web returns the 2b screen. J's Down is destructive and owner-only.
- **Compatibility:** an old web on the new service ignores the new summary keys; a new web on an old service shows the new sections' error states (404) and renders the rest.

(source: raw/2026-10-21-bots.md §Concept, Operations)

## Open items

**Unverified or partial at merge (the owner merged knowing this):**
- **FR-BT-E2E-002:** the 7-day or 72 h run of two auto bots (A7), which is also the spend soak FU-1 was meant to precede.
- **FR-BT-E2E-005:** the scripted allocation week against `positions` and `ledger`.
- **FR-BT-E2E-006:** an off-watchlist US candidate made live within one manager cycle, during US hours.
- **FR-BT-E2E-007:** a real fit preview, after 30 graded decisions.
- **FR-BT-WEB-011:** PV2 requested changes (B1, S1–S3); the web fix is in progress.
- **The 11th active bot** was never tried on a real stack; integration tests only.
- **No real *Upgrade*** of a legacy bot was saved on the preview.
- **B's template thesis.** B (tier `jev`) recorded `cost_usd` 0.000227 and `p` 0.670, but its thesis was the template. The source does not record why the thesis call fell back. FU-8 (below) describes a failure of this shape, but the record does not say it is the same event [needs verification].

**Not deployed.** The owner applies J (`20261020041046`) to their own database, then runs the merged service and bot, then the web.

**Follow-ups (`state.followUps`).**
- **FU-2:** compare a skip's direction with its candidate's; needs a contract refusal reason (service S9).
- **FU-3:** an index `bot_run_requests (bot_id, loop, requested_at DESC)` for the *Run now* window, in the next migration; the window count has no usable index today (service security r3 L1).
- **FU-4:** make `BotModels.budget` required, with a zero-estimate budget on `runner.ts`'s `unavailableModels`, so the per-bot budget cannot fail open by type (bot code r6).
- **FU-5 (owner decision):** 10 bots × 25 % lets four running bots on one account exhaust the shared ceiling (the global ceiling still stops all calls). Consider a per-account cap or a lower share.
- **FU-6:** the PF1 review nits (assert *Upgrade*'s focus ring after a keyboard *Cancel*; move `FOLLOW_KEY` above the describe's doc comment and fix a stale comment in `trade.spec.ts`; scope `app-bots .toast` in the contrast lists).
- **FU-7:** the `bots_running` gauge is overwritten by both passes and flips between 1 and 2; make it one count or two gauges, and align the bot README.
- **FU-8 (new):** a `bot_thesis` reply was rejected by the client's 240-code-point schema **after a paid call**. The spend is incurred, and under S17 the thesis becomes the template. See [[bots-engine]] and [[model-routes-and-spend]].

**Other recorded residuals.** An ORCH-10 note for the web `CLAUDE.md`; requiring the six `BotSummary` keys in `readBotSummary` once old fixtures are refreshed; bot security L1 (an untrusted-content instruction in the prompts, needing new prompt versions) and L3 (bot-scope `CANDIDATE_FOR_CHANGE`); a failed `recordBotCalls` loses its calls; the budget edges listed on [[bots-engine]]; service notes (J has no grants, so the owner-only Down is a procedure; bot names accept Unicode format characters; a clone copies a pre-cap over-cap config, which the bot reader then refuses); service nits (a 20-bar volume subquery per universe member, fit-weights running the full attribution, a README audit row); web review follow-ups and design advisories on [[design-system-decisions]]; load-sensitive flaky tests; and `documents/` drift (`02-architecture.md` §5.1 lists `4h`; `06-bots.md` lists GDELT and calendar discovery as in scope).

**Deferred by design.** 4h, the `custom` tier, shorts, GDELT and calendar discovery; a per-tick guard, an alert channel, retention jobs, account sources; manager judgement (S18); the promotion check, per-version KPIs and the champion stance (slice 7); learning jobs (slice 8); live mode (slice 9). Slice 7 shipped the promotion check and per-version KPIs; the champion stance moved to a follow-on spec (see [[statistics]]).

(source: raw/2026-10-21-bots.md §Open questions; FU-8 and the PV2 verdict from the orchestrator correction of 2026-10-21)

## Since slice 7 (statistics, 2026-10-27)

Slice 7 (tidewatch-service #15 `f289b9f`, tidewatch-web #20 `74918fd`; merged and deployed to production on 2026-10-27) changed these slice-6 surfaces. See [[statistics]] for the slice and [[stats-read-api]] for the routes.

- **The *Champion* tag now has a writer.** `POST /bots/{bot_id}/promote` sets `bots.champion` on one auto bot per user when the promotion check passes, and clears it on the previous champion. The Bots *Champion* tag reads the flag on its next read; on the preview it appeared on screen after the E2E-002 promotion. Before slice 7 nothing set it (see [[bot-versions-and-runs]]).
- **`recommendations.follow = "champion"` now resolves to a promoted bot.** The champion rule takes the user's `champion = true` auto bot first; until a promotion, it falls back to the oldest running or observing v2 auto bot with a scout, as before. On the preview, `GET /recommendation` followed the newly promoted bot (FR-ST-E2E-002) (see [[user-settings]] and [[signal-cited-orders]]).
- **Attribution, now additive and net.** `GET /bots/{bot_id}/attribution` is served by the shared attribution module's Bots scope (all versions, no window). Each item gains `win_rate`, `avg_r_5d_net`, `best` and `worst` after `graded`; every slice-6 key, value, item and order is byte-identical (`TestBots_Attribution_Compat`).
- **The editor's net figure (FR-ST-WEB-010, OD-4).** The version editor's figure beside each source weight reads `avg_r_5d_net` with two fraction digits and a U+2212 minus, worded "avg 5 d, net · n {n}" (it read "avg 5 d · n {n}", gross). It equals the Stats Source row under `period=all` for a single-version bot: FR-ST-E2E-004 matched it character for character for all 10 sources. *Fit weights* still reads gross. The editor's `SOURCE_NAMES` moved to a shared `util/source-names.ts` so Stats uses the same names (OD-7).
- **`GET /bots/{bot_id}/versions`** has its first web reader, the Stats *Version* select.
- **The slice-6 E2E bots on the shared preview database** (E2E A, B and C) make `bots-live.spec.ts` read "5 bots · paper mode" where it expects 2 (F-PV1-1, environmental, still open).
- **Production state.** `verification.md` records production at J or later before the slice-7 deploy, and no promotion on production. The first production champion is the owner's action: an auto bot that is `running`, with probation over and its own window of at least 30 days.

(source: raw/2026-10-27-statistics.md §API, Changed routes; §Database, What slice 7 writes; §Components, The Bots version editor and Data layer; §Concept, Owner decisions OD-4 and OD-7; §Test plan, The E2E checks and Preview runs; §Database, No migration; §Open questions, Rollout and production)

## Since accounts and roles (2026-10-29)

Accounts and roles (migrations #16, service #18, bot #19, web #23; merged and deployed to production on 2026-10-29) changed these slice-6 surfaces. See [[accounts-and-roles]] for the model.

- **FU-1 caps from the plan.** `bot_limit_reached {limit}` reads the plan's `max_active_auto_bots`. `POST /bots` without `starting_capital` and `EnsureBots` use the plan's `starting_capital_thb`. The `founder` values equal the slice-6 constants (see [[bot-versions-and-runs]]).
- **Tier entitlement.** A tier the plan excludes is refused on create, save and clone with `400 invalid_request {field: "config.decision_tier", reason: "not_entitled"}`. `GET /model-tiers` marks each tier `entitled`, and the editor greys an unentitled tier *Not in your plan*. In the bot, a stored unentitled tier runs the whole wake as `none` (S15; see [[bots-engine]]).
- **Per-person allowance beside the per-bot budget.** The FU-1 per-bot 25 % budget is now followed by the plan's daily allowance per person ($0.50 on `founder`), under the shared ceiling. Every bot model call carries `bot_id` and `user_id` (see [[model-routes-and-spend]]). FU-5 asked for a per-account cap or a lower share. The source does not say whether the allowance closes it.
- **Disable pauses bots.** An operator's *Disable sign-in* pauses the person's running and observing auto bots through Pause (`bot_status_changed {reason: user_disabled}`), and *Enable* leaves them paused (see [[operator-console]]).
- **Gates.** The product group's role gate is `RequireRole("user")`, and the count stays 64 gated routes.

(source: raw/2026-10-29-accounts-roles.md §API, Product contract changes; §API, Bot: allowance, tier entitlement, attribution; §API, People, Writes; §Components, Product-side changes; §API, Gates and route groups)

## Since the learning loop (slice 8, 2026-10-30)

The learning loop (migrations #14, service #16, bot #17, web #21; merged and deployed to production on 2026-10-30) shipped the "learning jobs (slice 8)" that slice 6 deferred. See [[learning-loop]] for the loop.

- **The *Learning* section** (`feat-bots/bot-learning.ts`) sits on the bot detail between Candidates and Version, for auto bots only. It shows the next and last run, *Run learning now*, the floors, and a pending draft's *Proposed weights*, *Calibration* and *Failure model* tables with *Load into editor*, *Dismiss draft* and *Download report*. A legacy (v1) bot reads "Learning needs the current vocabulary. Upgrade this bot to enable it." with no button (LL-W-1).
- ***Run now*'s route takes a fourth loop.** `POST /bots/{bot_id}/run` accepts `{loop: learn}`. It keeps slice 6's 6-per-hour rate limit per bot and loop, and refuses a non-v2 version with "Learning needs a v2 version. Upgrade the bot first." `learn` runs and requests are hidden from the existing run reads (`LastRun`, `Runs`, `RunByID`, `LatestRunRequests`; R4), so they surface only through the learning routes (see [[bot-versions-and-runs]]).
- **The version editor's learned block.** *Load into editor* applies the draft's weights through the existing `applyFitted` path, attaches the locked learned block and checks and locks *Start on probation (30 days)*. *Remove the learned block* deletes the `learning` key and unlocks probation. *Save as vN* posts `learning_run_id` only when the block belongs to the held run. On a stale draft only the `moved: true` weight rows are applied (OQ-W6).
- **The clone dialog** locks probation for a learned source (R12), and the service refuses `probation: false` on such a clone.
- **"· learned".** A learned bot's strategy sentence gains "· learned" (`feat-bots/util/bot-view.ts:135`); `BotSummary.strategy` ends with `learned` (P7).
- **The Watch and Checks** word `meta_veto` as "vetoed by the failure model"; the decision record's second line gains "size halved by the failure model" (see [[bot-watch-verdicts]] and [[decision-record]]).
- **On the preview (E2E-001)**, *Run learning now* on PV4 Calib proposed a days isotonic map, and *Load into editor* → *Save as v3* gave a learned, observing v3·1a2c on probation whose `learning` equalled the draft byte for byte.
- **The `pv4-learning` bots** (11, kept separate by OD-PV4-1) stay on the learning-loop run's own retained preview database, not on the shared volume (see [[forge-preview-gateway]]).

(source: raw/2026-10-30-learning-loop.md §Components; §API, Routes; §Concept, Decisions during the build OQ-W6, OQ-S2, OD-PV4-1; §Concept, Spec corrections, LL-W-1 and `learn` rows; §Test plan, What each seeded E2E showed; §Open questions, Owner actions still open)

## Since signals context (spec 3b, 2026-10-30)

Signals context (migrations #15, service #17, bot #18, web #22; merged 2026-10-30) built what D10 deferred: "GDELT and calendar discovery are out". See [[signals-context]] for the feature.

- **Two optional discovery paths in the scout.** `schedule.scout.discovery.context {enabled, z_min}` proposes on coverage anomalies, and `.calendar {enabled, sessions_ahead}` proposes before earnings. Both feed the unchanged rank-and-cap step before any model call. **The key is optional and absent means off:** a version without it canonicalises and hashes exactly as before. See [[bots-engine]] for the scout and [[bot-versions-and-runs]] for the vocabulary.
- **The version editor.** Two switch rows in the Schedule group: *Also propose on coverage anomalies* (*Z-score at least*, default 2.0) and *Also propose before earnings* (*Within N sessions*, default 5). See [[design-system-decisions]].
- ***Sources and weights*** shows three more rows by raw code after N (`finnhub-earnings-calendar`, `gdelt-gkg-en`, `gdelt-gkg-translation`), because `SOURCE_NAMES` has no entry for them (owner ruling WEB-OQ-1).
- **Coverage signals never act.** They are `media` signals with `origin = 'context'` and `impact 0.0000`, filtered out of every trigger read, so they never wake a bot, qualify a candidate or trigger an add or trim (see [[context-features-and-coverage-signals]]).
- **Production.** The discovery paths stay off for every bot until a version sets `schedule.scout.discovery`. Even then, the context path finds no features until the owner adds `context` to the production bot chart's collectors value. The bot and web deploys were triggered but not verified. FR-SC-E2E-003, a preview wake with both paths on, was not run, because it would call the paid model router.
- **`documents/`.** The drift noted above (`06-bots.md` lists GDELT and calendar discovery as in scope) is narrower now that both exist as opt-in paths. `documents/` itself was not touched (D17).

(source: raw/2026-10-30-signals-context.md, summary block; §Components, Web; §Concept, How it runs, 5. Scout discovery and 6. Never a trigger; §Test plan, Unverified end-to-end checks)

## Related pages

- [[bots-engine]]: the general engine (scout, manager, guard), candidates, run requests, the per-bot budget and `packages/waves`
- [[bot-versions-and-runs]]: v2 configs, create, clone, save as vN, events, probation, the 14 new routes and the FU-1 service caps
- [[bot-watch-verdicts]]: C11', now 23 verdicts, and the `15m` watch timeframe
- [[decision-record]]: the loop decisions, `candidate_id`, `market_state.elliott`/`regime` and C4'' exit reasons
- [[paper-trading]]: the bot-side intake, the C4'' close stamp and per-bot paper accounts
- [[model-routes-and-spend]]: the `bot_decide`/`bot_thesis` routes, the Sonnet price row and the per-bot 25 % budget
- [[signal-cited-orders]]: `decision_ctx.candidate_id`, the Trade recommendation card and the third pre-fill form
- [[elliott-regime-labeller]]: the labeller now ported to `packages/waves`
- [[design-system-decisions]]: the slice-6 components, ORCH-7's allocation bar and the PV2 findings
- [[zone-transition-bot]]: Slack Water and the 2b pass, kept byte-for-byte for v1
- [[bot-activity]]: Watch and Checks, now worded for the general engine
- [[centralized-migrations]]: migration J and the required schema version
- [[user-settings]]: the new `recommendations.follow` key
- [[signals-page]] and [[signals-read-api]]: the "acted on by bots" count, made real by bot decisions citing signals
- [[forge-preview-gateway]]: the `bots-1c6ff8ae` preview on the shared retained volume
- [[auth-model]]: the 59 gated routes and owner-scoped 404s
- [[statistics]]: slice 7, which promotes a champion and grades each version
- [[stats-read-api]]: promote, compare and the shared attribution module
- [[accounts-and-roles]]: the plan behind the FU-1 cap, the tiers and the starting capital
- [[learning-loop]]: slice 8, which adds the Learning section, drafts saved as vN and the locked learned block
- [[signals-context]]: spec 3b, which adds the context and calendar discovery paths D10 deferred
