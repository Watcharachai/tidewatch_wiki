# Statistics (`statistics`, slice 7)

**Summary**: Before slice 7, every bot decision was recorded and its outcomes were back-filled, but nothing read that record back as a judgement. `/stats` was still the slice-0 placeholder, and `bots.champion` was never set, so `recommendations.follow = "champion"` always fell back to the oldest auto bot with a scout. Slice 7 built the read side. The **Stats screen** grades one version of one of the owner's auto bots over a window: seven KPIs, equity against benchmark with a drawdown area, a calibration plot of stated `p` against the realised hit rate, attribution by source, event type, asset class and regime, *Why trades lost* with a labelling list, and *Compare bots* with *Promote to champion*. The service gained five gated, owner-scoped routes (64 gated in all; see [[stats-read-api]]), one attribution module serving two scopes, `follow_record` on `GET /recommendation`, two error codes, two audit events and two metrics. There was **no migration and no bot change**. Assumption A1 was false: `positions.realized_thb` is already net of both fees. **Status (2026-10-27):** verified on a preview, apart from FR-ST-SVC-013's index criterion (failed as written) and two uncaptured visual details. **Merged** on the owner's instruction (tidewatch-service #15 → `f289b9f`, tidewatch-web #20 → `74918fd`). **Deployed to production** separately, after each merge. **No production champion has been made**; that is the owner's action. **Since accounts and roles (2026-10-29),** `model_calls` carries `bot_id` and `user_id`. Stats was not changed, though: its cost of decisions still reads `bot_runs.counts.cost_usd` (D10), while the operator console's Spend reads `model_calls`. The two agree up to a crashed wake and estimates. **Since the learning loop (slice 8, merged and deployed 2026-10-30; see [[learning-loop]]),** the model proposes post-mortem labels, as D5 planned. *Why trades lost* gains a *Proposed only* filter, each proposal shows the model's rationale with a *Confirm* button, and the counts line splits labels into yours, the model's confirmed by you, and proposed. A confirmed model label keeps `labelled_by: "model"`. A **learned** challenger can no longer be promoted on a skipped calibration test: the verdict reads "Calibration not comparable yet", and promote refuses `calibration_not_comparable`. A learned version's calibration grades its calibrated `p`.

**Sources**: `raw/2026-10-27-statistics.md`; `raw/2026-10-29-accounts-roles.md` (the attribution columns and the Spend comparison only); `raw/2026-10-30-learning-loop.md` (the learning-loop section only)

**Last updated**: 2026-10-31

---

## Stage, stated precisely

Merged and deployed are separate stages, recorded separately in the source. The source takes `state.json` as authoritative for merge and deploy, and `verification.md` for verified, failed and unverified; `verification.md`'s header still reads "not merged, not deployed" because it was written earlier.

| Stage | Status (2026-10-27) |
|---|---|
| Implemented | **Service** (base `db281db`): S1–S9 in `6821b65`, the post-approval fold `b81c2ab`, the plan commit `5ab46d3` (PR head). **Web** (base `9e7b8e0`): S1–S14 and XP1 in `e99dce9`, review fix `b815cb4`, fold `aec5308`, plan commit `cbdb17f`, preview fixes PF1 `f7be11c`, PF2 `a7e4e56`, PF3 `5c68125`, docs `9a88771` (PR head) |
| Verified locally | Service `make ci` and the integration suite (4,115 PASS, 0 SKIP at the fold); the fixture generators reproduce their JSON byte for byte; `gofmt` clean. Web: 5,240 unit tests at S3 and 5,457 at PF2/PF3, lint, build, e2e lint and type-check, the zone-token and literal-colour greps |
| Reviewed | Plans and code in both repositories. Fix loops: plan review service 1, web 1; code review web 1. The service had no code fix loop and one post-approval fold |
| Verified on a preview | **Yes.** PV1 → PF1 → PV1b → PF2 → PV1c/PV1d → PF3 → PV1e; PV2 (rendered design review), PV3 (keyboard, axe, contrast), PV4 (FR-ST-E2E-001…004 against SQL), SVC-013 (timing and `EXPLAIN`), PV5 (docs) |
| **Merged** | **Yes**, 2026-10-27, on the owner's instruction "merge everything for me an continue" (quoted as written). Service #15 head `5ab46d3` → merge `f289b9f` at 08:02:48Z. Web #20 head `9a88771` → merge `74918fd` at 08:10:33Z. The web merged only after the service was deployed |
| **Deployed** | **Yes, both to production**, because a merge to `main` is a production deploy (deploy-prod → GHCR → tidewatch-kubernetes → ArgoCD). Service: run `40470855019`; `https://api.tidewatchtrade.com/info` reported commit `f289b9f`, build `0.1.0-build-20261027.f289b9fc`, at 08:10:11Z; `/stats` and `/stats/compare` answered 401 (registered and gated). Web: run `40471697694`; the `tidewatchtrade.com` bundle carried the Stats chunk ("Compare bots") and `/stats` answered 200, recorded at 08:21:25Z |
| **First production champion** | **Not made.** Promoting it is the owner's action after deploy (build prompt, PRD §8), and the record shows no promotion on production |
| Documentation pass | The raw source and this wiki update (wiki base `01a0d8a`). FR-ST-DOC-002 (OpenAPI and Bruno) is deferred, because `tidewatch-apis` is empty and not a Git repository |

(source: raw/2026-10-27-statistics.md, summary block; §Concept, Stage, stated precisely; Sources, Record notes)

## Why the slice exists

The brief calls Stats the gate between paper and live, and "the only honest answer to 'is the bot getting smarter'". At `main` on 2026-10-25 the inputs already existed:
- **The decision record** carried `bot_version`, `loop`, `action`, `direction`, `candidate_id`, `signal_snapshot`, the scout's `model.p`, `market_state.regime`, `policy_result` and the write-once outcomes. Its `post_mortem jsonb` could be set once by a writer and froze once confirmed, but nothing wrote it (see [[decision-record]]).
- **Per-bot money:** `ledger` `day_end` marks with `equity` and an equal-weight buy-and-hold `benchmark`; `positions` with `realized_thb`, `fees_thb`, `opened_by_decision_id` and `closed_at` (see [[paper-trading]]).
- **Versions:** `bot_versions` existed, `bots.champion` was never set, and `bot_version_events.kind` already allowed `promoted` and `demoted`, reserved for slice 7 by migration J (see [[bot-versions-and-runs]]).
- **Slice-6 attribution** was gross only. **Cost** was stored per scout wake in `bot_runs.counts.cost_usd`; `model_calls` has no `bot_id`.
- **No graded stated `p` existed on any stack**, so calibration had no real data.

The roadmap's exit test, "calibration plot and attribution computed from decisions only; a challenger cannot be promoted without an out-of-sample window", maps to FR-ST-SVC-001, 004, 005 and 009 together (source: raw/2026-10-27-statistics.md §Concept, Problem).

## Outcomes and their result

| # | Outcome | Result |
|---|---|---|
| O1 | Every number is reproducible from the record | **Met.** `TestStats_MatchesSQL` checks every `GET /stats` field against five committed SQL files. FR-ST-E2E-001 matched screen to SQL in three windows (22/22 screen, 34/34 raw values each) |
| O2 | Confidence is graded honestly | **Met by fixtures.** Synthetic ECE 0.0000 (calibrated) and 0.1500 (over-confident). There is still no real graded stated `p` (A4) |
| O3 | Per-version KPIs with reference arithmetic | **Met.** 11 scenarios computed independently in Python; A1's correction is in the fixture |
| O4 | One attribution, two screens | **Met.** `TestBots_Attribution_Compat` passes at HEAD and at base against the slice-6 golden. FR-ST-E2E-004: the editor's net figure equalled the Stats Source row character for character for all 10 sources |
| O5 | Losses get a reason | **Met.** FR-ST-E2E-003: a label saved on screen was stored confirmed; a second save got `409 post_mortem_frozen` |
| O6 | A champion exists only when earned | **Met.** FR-ST-E2E-002: an 11-day shared window was refused; after 46 days the promotion succeeded on screen, and the *Champion* tag and `GET /recommendation` followed it |
| O7 | Light theme, no zone colour | **Met.** Zone and literal-colour greps clean; no zone hue in the captures |

(source: raw/2026-10-27-statistics.md §Concept, Outcomes (intent) and their result)

## Owner decisions (intent, 2026-10-25)

The owner replied "Take all and continue" to one interview round: Q1–Q13 became D1–D13 and PD1–PD10 were adopted. It ran in chat, because the Forge Console Spec studio has no display in the desktop Code tab.

- **D1 Auto bots only.** `me` has no version and no `p`; it appears only in the Trade sentence.
- **D2 The version window** is `[created_at, next version's created_at or now)`. Equity and benchmark are rebased to the window's first mark. Probation does not move the start.
- **D3 One champion bot per user** (`bots.champion`). *Promote* flips the flag, writes `promoted` on the challenger's current version and `demoted` on the previous champion's, plus one audit event. A later version of the champion keeps the flag, and its out-of-sample record restarts.
- **D4 The promotion check** over the shared window: the challenger's return is higher, its max drawdown no deeper, its ECE no worse (only when both sides have ≥ 30 graded stated-`p` decisions; otherwise skipped), and it is an active auto bot. **The first champion** needs only its own window of ≥ 30 days and the active condition. A refusal names each failed condition; there is no tolerance band.
- **D5 The owner labels losses now; the model proposes labels in slice 8.** Seven labels: `signal_late`, `already_priced`, `regime_shift`, `stopped_by_noise`, `signal_wrong`, `sizing`, `execution`.
- **D6 Two levels of win rate:** per closed position in the KPI row; per decision at 5 days, net of modelled costs, in attribution.
- **D7 Net of modelled costs, one module, both screens.** The fit keeps its gross label.
- **D8 Calibration:** stated `p` from `propose` decisions; horizon from the candidate (`intraday → r_1d`, `days → r_5d`, `weeks → r_20d`); ten equal-width bins; dots sized by √n in violet; tier `none` reads "This version states no probabilities".
- **D9 Sharpe and Sortino** on daily returns between `day_end` marks, risk-free 0, annualised by √365; under 10 returns they read "not yet".
- **D10 Computed live, no snapshot table.** The trigger for an `attribution_snapshots` table is a Stats read over 500 ms on the preview, or 50,000 decisions. Cost of decisions = Σ `bot_runs.counts.cost_usd` at the C6 USD/THB rate (see [[model-routes-and-spend]]).
- **D11 The Trade sentence** compares followed and own decisions of the last 30 days by mean `r_5d`, with no counterfactual.
- **D12** The champion stance on the Chart, the Tide brief and an Overview recommendation card move to a follow-on spec.
- **D13 Presentation:** `mockup.html` at 1440, 1100, 1080, 600 and 390 in both themes. Drawdown is drawn in `--down` at low opacity, never a zone colour (see [[design-system-decisions]]).
- **PD1–PD10 (abridged):** the five routes and two codes; URL state on `/stats`; deliberate skips exclude `["observing"]`; days to recover; four attribution dimensions with *No signal* and *Unknown* rows never dropped; a template paragraph under *Why trades lost* with no model call; the audit events and metric; an SQL counterpart for every number; the web data layer on `httpResource`; build order service → web, no bot change, no migration.

(source: raw/2026-10-27-statistics.md §Concept, Owner decisions from the intent)

## Spec decisions that shaped the build (PRD S1–S16, selected)

- **S1** one attribution module, two signatures: the Bots scope (all versions, no window, slice-6 S20 unchanged) and the Stats scope (one version, one window).
- **S2** calibration shows at 30 graded; `n_stated` and `n_graded` are always returned.
- **S5** the Trade sentence rides on `GET /recommendation` as `follow_record`, not a sixth route.
- **S6** the losses list pages like `/decisions`, with cursor kind `L`.
- **S7** promote re-runs the check inside the lock and refuses the current champion.
- **S8** custom dates are inclusive Bangkok dates, at most 366 of them.
- **S11** the series is every `day_end` mark in the window plus the now point, with no downsampling.
- **S13** every read is one `REPEATABLE READ READ ONLY` snapshot; promote and the post-mortem write are `READ WRITE`, and promote runs under `MeBotLockKey`.
- **S15** the web formats and never computes.
- **S16** `GET /stats` without `bot_id` reads the champion, else the oldest auto bot with a current version.

The detail of each is on [[stats-read-api]] (source: raw/2026-10-27-statistics.md §Concept, Spec decisions that shaped the build).

## Owner decisions during the build (OD-1…OD-7)

| Id | Decision |
|---|---|
| OD-1 | The series benchmark is **rescaled** to start at the equity of the point that holds the benchmark base (contracts r2 §2.4). `benchmark_return_pct` is unchanged |
| OD-2 | `GET /stats/compare` with the current champion as challenger is `400 invalid_request {field: "challenger", reason: "invalid"}`. `same_bot` stays documented and is never sent |
| OD-3 | *Compare bots* is disabled only when no challenger exists, and hidden on the empty state. With no champion and one auto bot, the panel opens on the first-champion rule |
| OD-4 | The editor's net figure uses two fraction digits, so the editor and the Stats Source row read identically |
| OD-5 | Stats panel titles are `h2`s with the `h3` look, for axe heading order; amends PRD §7.6 |
| OD-6 | The first-champion grid headings "Over its own window" / "Challenger over its own window" are accepted |
| OD-7 | Stats uses the Bots editor's source names (`SOURCE_NAMES`, falling back to the publisher) on attribution Source rows and the labelling list's *Signal* cell. Web-only; amends PRD §4.6. Found because three SEC EDGAR sources all read "SEC EDGAR · Filing" |

`state.json` uses the ids OQ1, OQ2, ST-W-10 and WEB-B3 for OD-1…OD-4. A recorded reconciliation: intent PD1 lists `GET /stats/compare?champion&challenger`, while PRD §6.5 reads the champion from the flag and refuses a `champion` parameter; the contracts follow the PRD (source: raw/2026-10-27-statistics.md §Concept, Owner decisions during the build; Sources, Record notes).

## Assumptions A1–A7, as checked

- **A1: false.** `positions.realized_thb` is already net of both fees. The C5 arithmetic books a spot buy as `realized = −fee`, a spot sell as `gross − fee − cost_removed`, a futures open as `−fee` and a futures reduce as `pnl − fee`, and the bot's `packages/sim` agrees. So per-position net is `realized_thb`, PRD §11's own fallback; D6 and PRD §4.3's `realized_thb − fees_thb` would take the fees twice. The fixture records `"a1": "realized_thb is net of fees; no subtraction"`, and the finding was reported to the owner (see [[paper-trading]]).
- **A2:** the modelled cost rate omits the US sell-side per-unit fee, and VAT applies to commission only. The README and the attribution table say so.
- **A3:** a decision with no candidate grades at `r_5d`.
- **A4:** real calibration data waits for live bots, so synthetic fixtures carry the acceptance.
- **A5:** `bot_runs.counts.cost_usd` undercounts a crashed wake; the KPI note says "scout wakes".
- **A6: held.** `app-page-header` projects actions, so *Compare bots* sits there.
- **A7: did not hold literally at the preview's data skew** (FR-ST-SVC-013). No index was added; the owner is asked before any index is proposed.

(source: raw/2026-10-27-statistics.md §Concept, Assumptions A1–A7, as checked)

## Rulings during the build

- **XP-1 (2026-10-26).** A loss row's `signal` is non-null whenever `signal_snapshot` exists. Its `publisher` and `tier` come from a LEFT JOIN to `sources` by the snapshot's `source_code`, so **both are `null` when the code is absent or is not a `sources` row**; `source_code` is `null` when the snapshot has no such key. The service keeps this and contracts stay r2. The web reader accepts the nulls: the *Signal* cell shows the editor's source name for the code (OD-7), else the publisher, else the code, else "—", and a null tier shows no tier tag (ST-W-18 and the web review's refinement).
- **Code order.** `AllCodes()` ends `… run_rate_limited, promotion_refused, post_mortem_frozen`: 20 trade codes.

(source: raw/2026-10-27-statistics.md §Concept, Rulings during the build; §Components, attribution-table and losses-list)

## What each project gained

| Project | Gained |
|---|---|
| `tidewatch-service` | Five gated routes (59 → 64), the shared attribution module (`GET /bots/{bot_id}/attribution` gains four additive keys), `follow_record` on `GET /recommendation`, `promotion_refused` and `post_mortem_frozen`, reason `not_a_loss`, audit `bot_promoted` and `post_mortem_labelled`, metrics `stats_reads_total{kind}` and `stats_read_seconds{kind}`. Pure, float-free `internal/trading/stats.go`, `calibration.go`, `costrate.go`. See [[stats-read-api]] |
| `tidewatch-web` | `feat-stats` replaces the placeholder (`feat-screen-placeholder/` deleted); the Bots version editor's attribution figure switches from gross to net; Trade gains the follow-record sentence; `SOURCE_NAMES` moved to a shared `util/source-names.ts`; `.chip` moved to `chip.css`. See [[design-system-decisions]] |
| `tidewatch-migrations` | Nothing. `RequiredSchemaVersion` stays J (`20261020041046`); the migrations head is K (`20261021082304`, an index) (see [[centralized-migrations]]) |
| `tidewatch-bot` | Nothing. It still writes outcomes, runs and `cost_usd` as before (see [[bots-engine]]) |

Nothing writes `bot_versions`, `candidates`, `orders`, `fills` or `ledger`. The only writes are `decisions.post_mortem`, `bots.champion`, `bot_version_events` `promoted`/`demoted` and two audit events (source: raw/2026-10-27-statistics.md, summary block; §Database; §Files touched).

## What the user sees

- **`/stats`.** `h1` *Stats* with a sub line ("{bot} {label} · out-of-sample since {start date} · {window words} · benchmark is equal-weight buy and hold of the bot's watchlist") and *Compare bots* in the header actions. Then the controls (*Bot*, *Version*, *30 d / 90 d / All / Custom*), the KPI strip, *Equity against benchmark* beside *Does confidence mean what it says?*, *What each source earned* beside *Why trades lost*, the labelling list when open, and the compare panel when open.
- **Seven KPIs:** Return, Max drawdown, Sharpe, Win rate, Decisions, Calibration error, Cost of decisions, each with a note; figures are never coloured.
- **URL state:** `bot`, `v`, `period`, `from`/`to`, `compare` and `losses=1`; malformed keys are dropped with one `replaceUrl`. There is no timer.
- **Sixteen states** form the capture matrix: populated, loading, error, empty ("Nothing to grade yet"), fresh, rules-only, few-graded, switching, fallback, compare-passing, compare-refused, compare-first, compare-disabled, promoted, losses-open and labelled.
- **Labelling.** *Label losses* opens losing decisions of the version without a label, newest first, each with a native select of the seven reasons and *Save*. A saved row reads "Labelled by you · {word}" and *Frozen*.
- **Compare and promote.** The panel shows the champion (or "No champion yet"), a challenger select, the shared window, a grid and one verdict line per condition. *Promote to champion* is enabled only when the verdict passes; success toasts "{name} is the champion." (+ " {old} was demoted.").
- **Bots editor:** "avg 5 d, net · n {n}" instead of the gross figure (see [[bots]]).
- **Trade:** under the recommendation card, "Over 30 days, decisions that followed a recommendation averaged {a}% after 5 days; your own ideas averaged {b}% ({n_f} and {n_o} graded)." or "Not enough graded decisions yet…" (see [[signal-cited-orders]]).

Component and style details are on [[design-system-decisions]] (source: raw/2026-10-27-statistics.md §Components).

## Test plan and acceptance

Service and web commands are local; CI runs `make ci` and lint-test-build. Playwright runs only on a preview (`authed-setup`, then `public` + `authed` with `--no-deps --grep-invert @hook`; `journey` and `sign-out` skipped). The named service tests are listed on [[stats-read-api]] (source: raw/2026-10-27-statistics.md §Test plan, Commands).

| ID | Status |
|---|---|
| FR-ST-SVC-001…012 | Verified |
| FR-ST-SVC-013 (P2) | **Timing verified; the index criterion failed as written.** `period=all` p50 134 / p95 161 / max 206 ms; `30d` p50 37 / max 40 ms; all under 500 ms, so the D10 trigger was not reached. The expectation "`decisions_bot_ts_idx` range, no sequential scan" does not hold for `period=all` at the preview's data skew. **No index was added** (A7; the owner decides) |
| FR-ST-WEB-001…015 | Verified. WEB-004: the equity tooltip and pointer pick were **not captured**. WEB-014: focus-ring visuals were **not captured**; keyboard reach failed in PV1 (F-PV1-4) and passed after PF1 |
| FR-ST-E2E-001…004 | **Passed** on the preview |
| FR-ST-DOC-001 | Verified |
| FR-ST-DOC-002 | **Unverified: recorded deferral** (`tidewatch-apis` is not a Git repository) |

**Unverified in PV3, outside any single ID:** focus-ring visuals, contrast at widths other than 1440, nine states whose contrast was not measured, and VoiceOver/Safari reading of the `display: contents` compare-grid rows (source: raw/2026-10-27-statistics.md §Test plan, Acceptance status).

### Preview runs

- **The run.** `stats-285d3631`, compose project `forge-0199b29a-stats-285d3631`, isolated with retain on the shared volume `forge-preview-0199b29a_tidewatch-pgdata`, migrated to K. Service `5ab46d3` (equal to the merged code), web `cbdb17f` refreshed to `f7be11c`, `a7e4e56` and `5c68125`, bot `a22e399`, migrations `7b41800`. The owner's preview credentials were copied to `e2e/.auth` (mode 600) and never read or echoed (see [[forge-preview-gateway]]).
- **PV1 (`cbdb17f`):** 1402 passed, 4 failed, 4 skipped. F-PV1-1 (environment, still open): `bots-live.spec.ts` expects "2 bots · paper mode" and reads 5, because the shared database holds admin's slice-6 E2E bots. F-PV1-2/3: tests clicked soft-disabled buttons (fixed in PF1). F-PV1-4: a product a11y defect, focus lost after *Label losses* (fixed in PF1).
- **PV1b, PV1c, PV1d, PV1e:** stats.spec 258/258 after PF1; the full suite at `a7e4e56` passed except `bots-live` and host-slowness timeouts that passed 191/191 when re-run alone. Final: every spec passes except the one `bots-live.spec.ts` environment failure.
- **PV2:** rendered review of 230+ captures; round 1 CHANGES REQUESTED (B1 focus = F-PV1-4; B2 indistinguishable source names → OD-7; W1–W7), re-check at `a7e4e56` APPROVED, W8 fixed in PF3.
- **PV3:** axe 0 violations and contrast ≥ 4.5:1 in 7 states × 2 themes at 1440.
- **PV5:** the `DESIGN.md` evidence entry; `impeccable --check` clean.

(source: raw/2026-10-27-statistics.md §Test plan, Preview runs; Defects found on the preview and their fixes)

### The E2E checks (PV4, 2026-10-27, service `5ab46d3`)

A dedicated admin user `pv4-stats` was inserted by SQL; its password was set with the CLI and never printed. Bots were created through `POST /bots`, then backdated by hash-recorded seed scripts.
- **FR-ST-E2E-001: passed.** Every KPI, note, ECE line, post-mortem figure and the four attribution tables on screen equalled `test/sql/stats_*.sql` run against the preview database, in three windows (custom 10 Aug–15 Oct, `all`, `30d`). Earlier captures taken while the back-fill was still filling rows are kept as superseded.
- **FR-ST-E2E-002: passed.** PV4 Champion was promoted by API (first-champion branch, 61 days). PV4 Challenger with an 11-day shared window was refused `409 promotion_refused ["window_too_short"]`; a forced press sent no POST. After a seed script moved it to a 46-day shared window, it was promoted **on screen**, with the toast and the *Champion* tag on Bots, and `GET /recommendation` followed it. **Deviation:** the engine's guard paused the Challenger twice, because its seeded ledger ended at 1,080,000 while a fill-less account is valued at its starting capital (a −7.4 % day); that is correct product behaviour on inconsistent seed data, and the ledger was rescaled (see [[bots-engine]]).
- **FR-ST-E2E-003: passed.** *Regime shift* saved on screen; the row reads `confirmed_by_user true`; a second save and a direct PUT got `409 post_mortem_frozen`.
- **FR-ST-E2E-004: passed.** The editor's net figure equalled the Stats Source row for all 10 sources (at web `cbdb17f`; OD-7 later changed names, not figures).

(source: raw/2026-10-27-statistics.md §Test plan, The E2E checks and SVC-013)

### Preview database footprint

This persists on the shared retained volume, because `decisions`, `events` and `bot_version_events` are append-only.
- **`pv4-stats`'s bots:** PV4 Perf (paused), PV4 Champion (paused, `champion = false`, promoted then demoted), PV4 Challenger (paused, **`champion = true`**), plus `Me` and Slack Water created by `EnsureBots`. All auto bots were left paused.
- **Rows:** PV4 Perf holds 10,000 decisions (57 with a `post_mortem` at insert, 58 after E2E-003), 2,500 candidates, 400 closed positions, 1,288 `bot_runs` and 93 ledger rows; Champion and Challenger 12 decisions each.
- **Written by the product:** `promoted` × 2 and `demoted` × 1, `guard_paused` × 2, audit `bot_promoted` × 2 (114, 121) and `post_mortem_labelled` × 1 (123). The outcome back-fill rewrote allowed columns on PV4 Perf's rows from the preview's real bars, so its figures can still move.
- **Not touched:** `admin` still has 5 bots and no champion. No schema, index or container changed. No `pv4-stats` bot placed an order.

(source: raw/2026-10-27-statistics.md §Test plan, Preview database footprint)

## Operations

- **Merge order.** Service first, then the web only after the service deploy, because the web's strict readers refuse pre-slice-7 bodies; the web must never run ahead of the service.
- **Recovery.** Revert the merge commit on `main`; that redeploys the previous image, and there is no schema to roll back. A champion flag set by a promotion stays in `bots.champion`; clear it by SQL only on the owner's instruction.
- **Monitoring.** Watch `stats_read_seconds{kind}` against the 500 ms D10 trigger, and `stats_reads_total{kind}`.
- **First production champion.** A candidate must be an auto bot that is `running`, with probation over and its own window of at least 30 days.

(source: raw/2026-10-27-statistics.md §Open questions, Rollout and production)

## Open items

**Failed as written, or unverified, at merge (the owner merged knowing this):**
- FR-ST-SVC-013's index criterion (above). The record shows no index proposal and no owner answer on one.
- The equity chart's tooltip and pointer pick, and focus-ring visuals, not captured; contrast at other widths, nine states' contrast and VoiceOver/Safari on the compare rows, not measured.
- FR-ST-DOC-002 (OpenAPI and Bruno), deferred.
- `bots-live.spec.ts` (F-PV1-1) fails on any shared preview database holding more than `Me` and Slack Water.
- **No real calibration data.** The calibration plot, the ECE KPI and `calibration_no_worse` were exercised only on synthetic fixtures and seeded data (A4).

**Follow-ups (`state.followUps`):**
- **FU-1 (service):** a NaN or Inf `r_5d` or `px_at_decision` now makes the attribution and stats reads answer 500 (slice 6 answered 200 with "NaN"). Confirm the bot cannot write non-finite values, or count such rows as ungraded.
- **FU-2 (service):** Bots-scope attribution is now aggregated in Go; watch it beside the D10 trigger.
- **FU-3 (web):** graduate `TIER_WORDS`, `TONE_CLASS`, `BOT_TRIGGER_WORDS`, `LoadMoreOutcome` and `number-format` to `pages/workspace/util/`, and keep one `isUuid`.
- **FU-4 (web):** a `PageHeader` `focusHeading()` API; raise toasts from the screen, not from outputs emitted after `await`.
- **FU-5 (web):** the 366-day custom-span UX; optionally write `bot` into the URL before promoting; F13, a neutral disabled title when every challenger was refused this session.
- **FU-6 (service):** promote holds one pool connection and the advisory lock while it acquires a second for the snapshot (fails closed through `queryTimeout`); optional hardening.

**Other residuals.** A champion without a current version answers 500 on compare and promote (unreachable). `cost_usd` undercounts a crashed wake (A5). At slice 7 `model_calls` had no `bot_id`; migration L has since added it (see below). Accepted web deviations (`57.00%` against the mockup's `57%`, HTML axis labels, `.pm-bar`, the new `.panel-status`, copy beyond PRD §4 recorded in `DESIGN.md`). The e2e mock's `seriesInstants` falls back to the first `day_end` where the contract says the first mark of any kind. Billet was unavailable (`POST /billets` answered 500). **`documents/` drift** (never edited): `07-statistics.md` lists `attribution_snapshots` and a generated reading; `02-architecture.md` §11 lists `post_mortems` and `attribution_snapshots` tables (post-mortems live in `decisions.post_mortem`); the approved mockup shades drawdown with `--z-red` (D13 uses `--down`).

**Deferred by design:** factor models, regression dashboards and PDF reports; the model-proposed post-mortem labeller, recalibration maps, Thompson weights and the meta-model (slice 8); live mode for the champion only (slice 9); account sources (slice 10); the champion stance on the Chart, the Tide brief and an Overview recommendation card (the D12 follow-on spec); `attribution_snapshots` until its trigger; `me` in the Stats selector; a counterfactual Trade sentence.

(source: raw/2026-10-27-statistics.md §Open questions)

## Since accounts and roles (2026-10-29)

- **Spend is attributed, but Stats still reads `bot_runs`.** Migration L added `model_calls.bot_id` and `user_id`, and the bot stamps both on every bot call. Stats' cost of decisions is unchanged: Σ `bot_runs.counts.cost_usd` (D10). The operator console's Spend view reads `model_calls`. The source says the two agree up to a crashed wake and estimates (see [[model-routes-and-spend]] and [[operator-console]]).
- **The Stats routes' gate** is the product group's `RequireRole("user")` (it was `admin`). The routes are still owner-scoped by the session user (see [[auth-model]]).
- **The preview's `pv4-stats` user** was one of the two pre-L admin rows on the copy of the retained preview database that E2E-005 migrated to L. Its counts were unchanged (see [[accounts-and-roles]]).

(source: raw/2026-10-29-accounts-roles.md §API, Spend; §Database, Notes on the schema and Backfill; §API, Gates and route groups)

## Since the learning loop (slice 8, 2026-10-30)

The learning loop (tidewatch-service #16 `3f8627a`, tidewatch-web #21 `de00a5f`, with migration M and tidewatch-bot #17; merged and deployed to production on 2026-10-30) built the four items this page deferred to slice 8: the model-proposed post-mortem labeller, recalibration maps, Thompson weights and the meta-model. See [[learning-loop]]. Route detail is on [[stats-read-api]].

**Model-proposed labels (D9, D10).**
- **Where proposals come from.** A learning run proposes one label per closed losing entry whose `post_mortem` is null (Haiku through OpenRouter). It is stored unconfirmed with `labelled_by: "model"`, and its rationale goes to `post_mortem_proposals` (see [[decision-record]]).
- **Counted only once confirmed.** `labelled` and `by_label` still count only confirmed labels. `post_mortems.by_labeller` now has real values for all three keys: `user`, `model` (confirmed by the owner) and `proposed` (0 in slice 7).
- **The labelling list.** A native `button[aria-pressed]` chip *Proposed only* (in a group named "Filter the losing decisions") adds `proposed=1`. A proposal row shows "Model: {rationale}" as a second line inside `<bdi>`. The button reads *Confirm* while the select equals the proposal and *Save* otherwise. The saved tag reads "Proposed by the model · confirmed by you · {word}" with the toast "Label confirmed.", or "Labelled by you · {word}" with "Label saved.".
- **The counts line** reads "Labels: you {user} · model, confirmed by you {model} · proposed, waiting for you {proposed}".
- **Provenance (D10).** Confirming the model's label stores `labelled_by: "model"`, `confirmed_by_user: true`; choosing another label stores `labelled_by: "user"`. A confirmed label is still frozen.
- **OD-PV2-1 (owner, "Fix with CSS").** Above 600px the losses table's Decision and Signal second lines and the saved tag may wrap, so *Confirm* and *Save* stay fully in view at 1100 and 1080 (see [[design-system-decisions]]).
- **Not yet seen for real.** No model-written proposal has been produced in any environment: on the preview all 12 `post_mortem` calls were refused by OpenRouter. The downstream flow was verified on three SQL-seeded proposals (FR-LL-E2E-003, partial).

**The learned-challenger gate (D13).**
- **What changed.** In the compare verdict, a skipped `calibration_no_worse` on a **learned** challenger is `met: false` with `detail {not_comparable: <reason>}`, not `met: null`. Promote refuses it with `409 promotion_refused` and the new reason `calibration_not_comparable`.
- **The first-champion branch is unchanged,** and there is still no automatic promotion. An unlearned challenger keeps the slice-7 skip.
- **The words.** "Calibration not comparable yet ({reason words}); a learned version must show its calibration before promotion", with *Promote to champion* `aria-disabled`.
- **On the preview (E2E-004).** With 10 graded proposals, promote answered `409 [return_not_higher, calibration_not_comparable, not_active]` and the panel worded it. With 35 graded, the challenger was judged on ECE (0.1685 against 0.1015, `calibration_worse`). `bots.champion` did not change.

**Calibration of a learned version.**
- **D5.** The calibrated `p` is what the bot states and what Stats grades, so a learned version's calibration plot and ECE read the calibrated `p`. `p_raw` is kept in `model` for the next refit.
- **The realised line.** A learning run on a learned version with ≥ 30 graded records `calibration.realised {ece_calibrated, ece_raw, n}` and the report words it "helped", "did not help" or "made it worse". The bot's *Learning* section shows the line above its tables. This is the roadmap's exit-test record, and it was proven only on seeded data.
- **The sub line** adds "· learned version" (`stats-view.ts:133`), from `version.learned`.

**Cost of decisions** still sums `bot_runs.counts.cost_usd` over the version's runs of any loop, so it now also includes a learning run's labelling spend.

**Brief acceptance (from the learning-loop source).** BA-4 (labels counted only once confirmed) is verified for the counting and the list, and BA-6 (the API refuses an unproven learned challenger) is verified. A model-written proposal is still unverified.

(source: raw/2026-10-30-learning-loop.md, summary block; §Concept, Owner decisions D5, D9, D10, D13; §Concept, The four jobs, `calibrate.ts` and `labels.ts`; §Concept, Service rules; §Concept, Decisions during the build OD-PV2-1; §Concept, Spec corrections, `learn` rows; §API, Routes; §Components, Stats; §Test plan, Results and What each seeded E2E showed)

## Related pages

- [[stats-read-api]]: the five routes, query grammar, bodies, figure definitions, codes, audit and metrics (contracts r2)
- [[decision-record]]: the dataset Stats grades, and `post_mortem`, its one user write
- [[bot-versions-and-runs]]: version windows, `bots.champion` and the `promoted`/`demoted` events
- [[bots]]: slice 6, the *Champion* tag, the editor's net figure and the attribution route
- [[bots-engine]]: `cost_usd` per wake, the scout's stated `p`, the candidate horizon and the guard pause
- [[paper-trading]]: `realized_thb` (A1), the ledger marks and the now point
- [[model-routes-and-spend]]: cost of decisions
- [[design-system-decisions]]: the Stats pieces, the `--down` drawdown exception, OD-5 and OD-7
- [[signal-cited-orders]] and [[user-settings]]: `follow_record` and the champion the follow setting resolves to
- [[simulation-engine]]: ledger `day_end` marks and the equal-weight benchmark
- [[source-registry-and-ingest]]: the `sources` rows behind the Source dimension
- [[elliott-regime-labeller]]: the regime words behind the regime dimension
- [[centralized-migrations]]: no migration; `RequiredSchemaVersion` stays J
- [[auth-model]]: the 64 gated routes and owner-scoped 404s
- [[forge-preview-gateway]]: the isolated retained preview and the dedicated `pv4-stats` user
- [[accounts-and-roles]]: `model_calls` attribution and the person model behind the session user
- [[learning-loop]]: slice 8, which proposes labels, calibrates `p` and adds the learned-challenger gate
