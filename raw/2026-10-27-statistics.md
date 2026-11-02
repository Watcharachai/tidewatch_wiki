# Statistics (`statistics`, slice 7): per-version KPIs, calibration, attribution, post-mortems and the promotion check

> Before this slice, every bot decision was recorded and its outcomes were back-filled, but nothing read that record back as a judgement. `/stats` was still the slice-0 placeholder ("Does confidence mean what it says?" / "Nothing to grade yet"). `bots.champion` was never set, so `recommendations.follow = "champion"` always fell back to the oldest auto bot with a scout. Slice 7 built the read side: the screen and routes that grade a bot version, and the promotion check between paper and live.
> - **The Stats screen.** `/stats` grades one version of one of the owner's auto bots over a window. It shows:
>   - seven KPIs;
>   - equity against benchmark, with a drawdown area;
>   - a calibration plot of stated `p` against the realised hit rate;
>   - attribution by source, event type, asset class and regime;
>   - *Why trades lost*, with a labelling list for losing decisions;
>   - *Compare bots*, with *Promote to champion*.
> - **Service.** It adds:
>   - five gated, owner-scoped routes: `GET /stats`, `GET /stats/losses`, `GET /stats/compare`, `PUT /decisions/{decision_id}/post-mortem` and `POST /bots/{bot_id}/promote`. The gated count goes from 59 to 64;
>   - one attribution module with two scopes, so `GET /bots/{bot_id}/attribution` gains four additive keys;
>   - `follow_record` on `GET /recommendation`;
>   - the codes `promotion_refused` and `post_mortem_frozen`, and the reason `not_a_loss`;
>   - the audit events `bot_promoted` and `post_mortem_labelled`;
>   - the metrics `stats_reads_total{kind}` and `stats_read_seconds{kind}`.
> - **Web.**
>   - `feat-stats` replaces the placeholder.
>   - The Bots version editor's attribution figure switches from gross to net.
>   - Trade gains a "followed recommendations against your own ideas" sentence.
> - **No migration and no bot change.** `RequiredSchemaVersion` stays J (`20261020041046`). Nothing writes `bot_versions`, `candidates`, `orders`, `fills` or `ledger`.
> - **A1 was false.** `positions.realized_thb` is already net of both fees, so per-position net is `realized_thb`, not `realized_thb − fees_thb` as the PRD wrote.
>
> **Status (2026-10-27).**
> - **Verified.**
>   - Every service requirement FR-ST-SVC-001…012 is verified.
>   - FR-ST-SVC-013: the timing passed. Its index criterion **failed as written**: `period=all` sequence-scans `decisions` on the skewed preview data.
>   - FR-ST-WEB-001…015 are verified. Two visual details were never captured: the equity tooltip and pointer pick, and focus rings.
>   - FR-ST-E2E-001…004 passed on the preview.
>   - FR-ST-DOC-001 is verified. FR-ST-DOC-002 is a recorded deferral.
>   - One Playwright failure remains, and it is environmental: `bots-live.spec.ts` counts the shared preview database's slice-6 bots.
> - **Merged**, on the owner's instruction:
>   - tidewatch-service #15 → `f289b9f` at 2026-10-27T08:02:48Z;
>   - tidewatch-web #20 → `74918fd` at 08:10:33Z.
> - **Deployed to production.**
>   - Service: `https://api.tidewatchtrade.com/info` reported commit `f289b9f` at 08:10:11Z.
>   - Web: the `tidewatchtrade.com` bundle carried the Stats chunk at 08:21:25Z.
> - **Not done.** Promoting the first production champion is the owner's action, and it has not happened.

**Sources (inputs to this document).**
- **Spec.** In `/Users/maichinu/tidewatch/tidewatch-specs/statistics/`:
  - `build-prompt.md`;
  - `intent.md` (O1–O7, D1–D13, PD1–PD10; confirmed 2026-10-25);
  - `prd.md` (S1–S16, A1–A7, §4–§11, `FR-ST-*`);
  - fingerprints, which matched at build start (2026-10-25T10:27:02Z): intent `2d4d5c5d…22f9`, prd `8aae8d44…5f9a`, mockup `9e640980…9c3d`.
- **Build record.** `/Users/maichinu/tidewatch/.forge/features/statistics/state.json` (`perProject`, `ownerDecisions`, `crossProjectChecks`, `followUps` FU-1…FU-6, `previewChecks`, `runtime`, `log`) and `verification.md`.
- **Rulings.** `planning/cross-plan-decisions.md` (XP-1 and the code order).
- **Contracts.** `planning/tidewatch-service/contracts.md` r2 (sha256 `7b01f95c…b0fc`; r1 `66fe3e64…2f0f`).
- **Open-contract choices.** `evidence/tidewatch-service/M1-choices.md` (M1, S4…S9 and FOLD).
- **Plans.** Each is the `.plans/statistics.md` of its worktree under `/Users/maichinu/tidewatch/.forge/docker/runs/stats-285d3631/worktrees/`:
  - service `329891b601`: approved r2, plan `9f25c0b5…c603`, handoff `06400836…6ee2d`; steps S1–S9;
  - web `5eb4e5c7ea`: approved r2, plan `423fbca0…5a9c`, handoff `e29f94b0…0d75`; steps S1–S14.
- **Reviews.** `review/tidewatch-service/` and `review/tidewatch-web/`.
- **Preview evidence.**
  - `evidence/tidewatch-web/PV1-findings.md` and `PV2-design-review.md`;
  - `evidence/preview/seeded.md`;
  - `evidence/service/stats-explain.txt`.
- **Merged code, read in the run's worktrees.** The service `README.md` ("Stats routes") and `CLAUDE.md` ("Stats invariants (slice 7)"), and the web `CLAUDE.md`.
- **Record notes.**
  - `verification.md`'s header still reads "not merged, not deployed" and gives the PR heads. `state.json` records both merges and both deploys after that header was written. This document takes `state.json` as authoritative for merge and deploy, and `verification.md` for verified, failed and unverified.
  - `state.json`'s `ownerDecisions` uses the ids OQ1, OQ2, ST-W-10 and WEB-B3 for the decisions that `verification.md` and the plans number OD-1…OD-4. This document uses OD-1…OD-7.
  - `state.json`'s `previewChecks.previewUrl` is the first preview URL. The final one is `runtime.previewUrl`.

## Concept

### Stage, stated precisely

| Stage | Status (`state.json` and `verification.md`, 2026-10-27) |
|---|---|
| Implemented | **Service** (base `db281db`): S1–S9 in `6821b65`; the post-approval fold `b81c2ab`; the plan commit `5ab46d3` (PR head). **Web** (base `9e7b8e0`): S1–S14 and XP1 in `e99dce9`; review fix round 1 `b815cb4`; the post-approval fold `aec5308`; the plan commit `cbdb17f`; preview fixes PF1 `f7be11c`, PF2 `a7e4e56` and PF3 `5c68125`; the PV5 docs commit `9a88771` (PR head). |
| Verified locally | Every step's contract commands exited 0, with the parent re-checks recorded per step. **Service:** `make ci` and the integration suite. At the fold it ran 4,115 PASS, 0 SKIP, including `TestPromote_*`, `TestStats_MatchesSQL` and `TestStats_Compare`. The fixture generators reproduced their JSON byte for byte, and `gofmt` was clean. **Web:** `pnpm nx test tidewatch-web` (5,240 tests at S3, 5,457 at PF2/PF3), lint, build, the e2e lint and type-check, the zone-token and literal-colour greps, and the plan's `plan-checks.mjs` checks. |
| Reviewed | Plans and code in both repositories; see "Review history". Fix loops: plan review service 1 and web 1; code review web 1. The service had no code fix loop and one post-approval fold. |
| Verified on a preview | **Yes.** PV1 (Playwright) → PF1 → PV1b → PF2 → PV1c and PV1d → PF3 → PV1e; then PV2 (rendered design review), PV3 (keyboard, axe and contrast), PV4 (FR-ST-E2E-001…004 against SQL), SVC-013 (timing and `EXPLAIN`) and PV5 (docs). See "Test plan". |
| Merged | **Yes**, on 2026-10-27, on the owner's instruction "merge everything for me an continue" (quoted as written). The service went first; the web followed only after the service was deployed. Service #15 head `5ab46d3` → merge `f289b9f` (08:02:48Z). Web #20 head `9a88771` → merge `74918fd` (08:10:33Z). |
| Deployed | **Yes, both to production**, because a merge to `main` is a production deploy (deploy-prod → GHCR → tidewatch-kubernetes → ArgoCD). **Service:** deploy-prod run `40470855019`. `/info` reported commit `f289b9f…`, build `0.1.0-build-20261027.f289b9fc`, at 08:10:11Z. `/ready` answered 200; `/stats` and `/stats/compare` answered 401, so they are registered and gated; an unknown route answered 404. **Web:** deploy-prod run `40471697694`. The main bundle changed to `main-JNXZ2XZ4.js` at about 08:20Z, the lazy chunk `chunk-pniIVq0-.js` contains "Compare bots", and `/stats` answered 200. Recorded at 08:21:25Z. |
| First production champion | **Not made.** That is the owner's action after deploy (build prompt, PRD §8), and the record shows no promotion on production. |
| Documentation pass | This document and the wiki update (worktree `docs-7ce006e44c`, wiki base `01a0d8a`). FR-ST-DOC-002 (OpenAPI and Bruno) is deferred, because `tidewatch-apis` is empty and not a Git repository. |

### Problem

The brief calls Stats the gate between paper and live, and "the only honest answer to 'is the bot getting smarter'". At `main` on 2026-10-25 (service `9f1f324`, web `38512c2`, bot `650e5ba`, migrations at K) the inputs already existed:
- **The decision record.** `decisions` carried `bot_version`, `loop`, `action`, `direction`, `candidate_id`, `signal_ids` and `signal_snapshot {source_code, tier, event_type, …}`.
  - `model {tier, …, p, …}` is set on a scout `propose`, and entries copy it.
  - `market_state.regime {trend, vol, atr_pct}` and `policy_result` are recorded.
  - The back-filled outcomes `r_1h`, `r_1d`, `r_5d`, `r_20d`, `mae`, `mfe`, `exit_reason` and `closed_at` are write-once.
  - There is a `post_mortem jsonb` that the `decisions_backfill_only` trigger lets a writer set once, and freezes once `"confirmed_by_user": true`. Nothing wrote it yet.
- **Per-bot money.** `ledger` holds a `day_end` mark at 00:00 Bangkok every day, with `equity` and an equal-weight buy-and-hold `benchmark`. `positions` holds `realized_thb`, `fees_thb`, `opened_by_decision_id` and `closed_at`.
- **Versions.** `bot_versions` existed. `bots.champion` was never set. `bot_version_events.kind` already allowed `promoted` and `demoted`, which migration J reserved for slice 7.
- **Slice-6 attribution.** The S20 SQL behind `GET /bots/{bot_id}/attribution` was gross only.
- **Cost.** Each scout wake stores its spend as `bot_runs.counts.cost_usd`. `model_calls` has no `bot_id`.
- **No graded `p` anywhere.** No decision on any stack had a graded stated `p`, so calibration and the fit had no real data yet.

The roadmap's exit test is "calibration plot and attribution computed from decisions only; a challenger cannot be promoted without an out-of-sample window". It maps to FR-ST-SVC-001, 004, 005 and 009 together.

### Outcomes (intent) and their result

| # | Outcome | Result |
|---|---|---|
| O1 | Every number is reproducible from the record | **Met.** `TestStats_MatchesSQL` compares every `kpis`, `series`, `calibration`, `attribution` and `post_mortems` field of `GET /stats` with five committed SQL files (3 bots, 2 versions, past and custom windows). On the preview, FR-ST-E2E-001 matched the screen to SQL for three windows (22/22 screen values and 34/34 raw values per window). |
| O2 | Confidence is graded honestly | **Met by fixtures.** On the synthetic sets, `TestCalibration_Synthetic` gives ECE 0.0000 (calibrated) and 0.1500 (over-confident, every dot below the diagonal). The integration test is `TestStats_Calibration`. PV2 checked the rendered plot, caption, rules-only and few-graded states. There is still no real graded stated `p`, which is A4's expectation. |
| O3 | Per-version KPIs with reference arithmetic | **Met.** `TestStatsArithmetic_Fixtures` passes over 11 scenarios computed independently in Python (standard library only, byte-reproducible). `TestStatsWindow_Rules` and `TestStats_Window` also pass. A1's correction is recorded in the fixture. |
| O4 | One attribution, two screens | **Met.** One module serves two scopes. `TestBots_Attribution_Compat` passes at HEAD and at base `db281db` against the slice-6 golden. FR-ST-E2E-004: the editor's net figure equalled the Stats Source row character for character for all 10 sources. |
| O5 | Losses get a reason | **Met.** `TestPostMortem_Write` and `TestPostMortem_Refusals` pass. FR-ST-E2E-003: a label saved on screen was stored with `confirmed_by_user true`, a second save got `409 post_mortem_frozen`, and the counts moved by 1. |
| O6 | A champion exists only when earned | **Met.** `TestPromote_Pass`, `Refused`, `Concurrent` and `PauseRace` pass, and so does `TestPromoteBot_VerdictReadsInSnapshot`. FR-ST-E2E-002: an 11-day shared window was refused (`window_too_short`) and the screen said so; after 46 days the promotion succeeded on screen, and the *Champion* tag and `GET /recommendation` followed it. |
| O7 | Light theme, no zone colour | **Met.** The zone and literal-colour greps are clean. PV1c "draws every chart from classes in both themes" read the computed colours. PV2 found no zone hue in the captures. |

### Owner decisions from the intent (round 1, 2026-10-25)

The owner replied "Take all and continue" to one interview round: Q1–Q13 became D1–D13 and the defaults PD1–PD10 were adopted. It ran in chat, because the Forge Console Spec studio has no display in the desktop Code tab.
- **D1 Auto bots only.** `me` has no version and no `p`, so it appears only in the Trade sentence.
- **D2 The version window** is `[created_at, next version's created_at or now)`. Equity and benchmark are rebased to the window's first mark. Probation does not move the start.
- **D3 One champion bot per user** (`bots.champion`).
  - *Promote* flips the flag and writes `promoted` on the challenger's current version and `demoted` on the previous champion's, plus one audit event.
  - A later version of the champion keeps the flag, and its out-of-sample record restarts.
- **D4 The promotion check.** It runs over the shared window (the overlap of the two current versions' windows, in calendar days). It passes when:
  - the challenger's return is higher;
  - its max drawdown is no deeper;
  - its ECE is no worse (only when both sides have ≥ 30 graded stated-`p` decisions; otherwise the condition is skipped);
  - it is an active auto bot (`running`, probation over).

  **The first champion** needs only its own window of ≥ 30 days and the active condition. A refusal names each failed condition. There is no tolerance band.
- **D5 The owner labels losses now; the model proposes labels in slice 8.** The seven labels are `signal_late`, `already_priced`, `regime_shift`, `stopped_by_noise`, `signal_wrong`, `sizing` and `execution`. Slice 8 will write `labelled_by: "model", confirmed_by_user: false` into the same shape.
- **D6 Two levels of win rate.** The KPI row's is per closed position; the attribution table's is per decision, at the 5-day horizon, net of modelled costs.
- **D7 Net of modelled costs, one module, both screens.** The fit keeps its gross label.
- **D8 Calibration.**
  - The stated `p` comes from `propose` decisions.
  - The horizon comes from the candidate: `intraday → r_1d`, `days → r_5d`, `weeks → r_20d`.
  - Ten equal-width bins, with dots sized by √n in violet.
  - Tier `none` reads "This version states no probabilities".
- **D9 Sharpe and Sortino** use daily returns between consecutive `day_end` marks, risk-free 0, annualised by √365 (not √252). Under 10 returns they read "not yet".
- **D10 Computed live, no snapshot table.** The PRD records the trigger for `attribution_snapshots`: a Stats read over 500 ms on the preview, or 50,000 decisions. Cost of decisions = Σ `bot_runs.counts.cost_usd`, converted at the C6 USD/THB rate.
- **D11 The Trade sentence.** It compares followed and own decisions of the last 30 days, mean `r_5d`, with no counterfactual.
- **D12** The champion stance on the Chart, the Tide intelligence brief and an Overview recommendation card move to a follow-on spec.
- **D13 Presentation.** `mockup.html` is the chosen visual target, at 1440, 1100, 1080, 600 and 390 in both themes. Drawdown is drawn in `--down` at low opacity, never a zone colour.
- **PD1–PD10:**
  - PD1: the five routes and two codes;
  - PD2: URL state on `/stats`;
  - PD3: deliberate skips exclude `["observing"]`;
  - PD4: days to recover;
  - PD5: the four attribution dimensions, with *No signal* and *Unknown* rows that are never dropped;
  - PD6: a template paragraph under *Why trades lost*, with no model call;
  - PD7: the audit events and metric;
  - PD8: an SQL counterpart for every number, and pure-function fixtures;
  - PD9: the web data layer (`httpResource`, a screen-provided `StatsService`);
  - PD10: build order service → web, no bot change, no migration.

### Spec decisions that shaped the build (PRD S1–S16, selected)

- **S1 One attribution module, two signatures.** The Bots scope covers all versions with no window (slice-6 S20 unchanged); the Stats scope covers one version and one window.
- **S2 Calibration shows at 30 graded.** `n_stated` and `n_graded` are always returned.
- **S3 Daily returns and the two ratios.** Sharpe = mean / sample st. dev. × √365. Sortino = mean / √(Σ min(r, 0)² / N) × √365.
- **S4 Entries are long only**, but the code orients by `direction`.
- **S5** The Trade sentence rides on `GET /recommendation` as `follow_record`, not a sixth route.
- **S6** The losses list pages like `/decisions`: keyset `(ts DESC, decision_id DESC)` and cursor kind `L`.
- **S7** Promote re-runs the check inside the lock and refuses the current champion (`already_champion`).
- **S8** Custom dates are inclusive Bangkok dates, with a span of at most 366 dates.
- **S9** The mockup's `.panel` is `.stats-panel`.
- **S10** The calibration plot carries a visually hidden table of its bins.
- **S11** The series is every `day_end` mark in the window plus the now point, with no downsampling.
- **S12** Cost of decisions is converted at the C6 rule-4 USD/THB rate, and the USD figure travels too.
- **S13** Every read is one `REPEATABLE READ READ ONLY` snapshot. Promote and the post-mortem write are `READ WRITE`, and promote runs under `MeBotLockKey`.
- **S14** There are two metrics, so the D10 trigger can be observed.
- **S15 The web formats and never computes.** Ratios × 100 with two digits and a U+2212 minus, ECE with three digits, Sharpe and Sortino with two.
- **S16** `GET /stats` without `bot_id` reads the champion, else the oldest auto bot with a current version.

### Owner decisions during the build (OD-1…OD-7)

| Id | When | Decision |
|---|---|---|
| OD-1 | 2026-10-25 (service OQ1) | The series benchmark is **rescaled** to start at the rebase equity. Precisely, it starts at the equity of the series point that holds the benchmark base (contracts r2 §2.4). `benchmark_return_pct` is unchanged. |
| OD-2 | 2026-10-25 (service OQ2) | `GET /stats/compare` with the current champion as challenger is `400 invalid_request {field: "challenger", reason: "invalid"}`. `same_bot` stays in the documented reason set and is never emitted in this slice. |
| OD-3 | 2026-10-26 (web ST-W-10) | *Compare bots* is disabled only when no challenger exists, and hidden on the empty state. With no champion and one auto bot, the panel opens on the first-champion rule, so the first promotion stays reachable. |
| OD-4 | 2026-10-26 (web plan review B3) | The editor's net figure uses S15's two fraction digits, so the editor and the Stats Source row read identically and FR-ST-E2E-004 is a straight equality. |
| OD-5 | 2026-10-26 (web review r1) | The Stats panel titles are `h2`s with the `h3` look, to satisfy axe heading order. This amends PRD §7.6. |
| OD-6 | 2026-10-26 (web review r1) | The first-champion grid headings "Over its own window" / "Challenger over its own window" are accepted. |
| OD-7 | 2026-10-27 (PV2 B2) | Stats uses the Bots editor's source names (`SOURCE_NAMES` keyed by source code, falling back to the publisher) on the attribution Source rows and the labelling list's *Signal* cell. It is web-only and amends PRD §4.6. It was found because three SEC EDGAR sources all read "SEC EDGAR · Filing"; this also folded the PV4 observation (called FU-7 in the log). |

Recorded reconciliation (not a question): intent PD1 lists `GET /stats/compare?champion&challenger`, while PRD §6.5 reads the champion from the flag and refuses a `champion` parameter. The contracts follow the PRD.

### Assumptions A1–A7, as checked

- **A1: false.** `positions.realized_thb` is already net of both fees.
  - The service's C5 arithmetic (`internal/trading/arith.go`, `ApplyFill`) books:
    - a spot buy as `realized = −fee`;
    - a spot sell as `gross − fee − cost_removed`;
    - a futures open as `−fee`;
    - a futures reduce as `pnl − fee`.
  - `RealizedTHB` and `FeesTHB` both accumulate on every fill. The bot's `packages/sim/src/arithmetic.ts` agrees.
  - So per-position net is `realized_thb`, PRD §11's own fallback. Subtracting `fees_thb` again would take the fees twice.
  - D6 and PRD §4.3 literally say `realized_thb − fees_thb`. The arithmetic fixture records `"a1": "realized_thb is net of fees; no subtraction"`, and the finding was reported to the owner.
- **A2:** the modelled cost rate omits the US sell-side per-unit fee, and VAT applies to commission only. The words "modelled costs: commission, VAT, slippage, futures fees" are in the README and under the attribution table.
- **A3:** a decision with no candidate grades at `r_5d`.
- **A4:** real calibration data waits for live bots, so the synthetic fixtures carry acceptance 2.
- **A5:** `bot_runs.counts.cost_usd` undercounts a crashed wake. The KPI note says "scout wakes".
- **A6: held.** `app-page-header` projects actions, so *Compare bots* sits there as Signals' *Export* does.
- **A7: did not hold literally at the preview's data skew** (see FR-ST-SVC-013). No index was added.

### Rulings during the build

- **XP-1 (2026-10-26).** `LossRow.signal` is non-null whenever `signal_snapshot` exists.
  - Its `publisher` and `tier` come from a LEFT JOIN to `sources` by the snapshot's `source_code`, so both are `null` when the code is absent or is not a `sources` row. `source_code` is `null` when the snapshot has no such key.
  - The service keeps this, and contracts stay r2. The web reader accepts the nulls and words them with ST-W-18's rule: a dash, and no tier tag.
  - The web review recorded a refinement: a null publisher falls back to `source_code`, then "—".
- **Code order.** `AllCodes()` reads `… run_rate_limited, promotion_refused, post_mortem_frozen`, 20 trade codes. S5 appended `post_mortem_frozen` first, and S7 inserted `promotion_refused` before it.

### How each figure is computed (contracts r2 §2, with the open-contract choices)

**Rounding and units.**
- Decimals travel as strings, rounded half away from zero.
- Ratios carry 6 fraction digits (the web × 100). THB carries 2.
- Sharpe, Sortino, the profit factor and the ECE carry 4. `cost_usd` carries 6.
- Instants are RFC 3339 UTC, and Bangkok dates are `YYYY-MM-DD`; Bangkok is a fixed UTC+07:00.
- `internal/trading/stats.go`, `calibration.go` and `costrate.go` are pure and float-free. Square roots go through `math/big`.

**The window.**
- **Version window.** `start` is the version's `created_at`. `end` is the `created_at` of the smallest `seq` above it, or `null` for the current version (the read's now closes it).
- **Periods.**
  - `all` → `[start, E]`, where `E = end or now`.
  - `30d` / `90d` → `[max(start, E − N × 24 h), E]`.
  - `custom` → `[from 00:00 Bangkok, to 24:00 Bangkok]`, clipped to `[start, E]`.
- **Membership.**
  - Decisions, runs and position closes count when `from ≤ ts < to`.
  - Ledger marks join the series when `from < ts ≤ to`; a `day_end` mark at 00:00 Bangkok closes the previous day.
  - The **rebase mark** is the last `day_end` with `ts ≤ from`, else the first mark of any kind with `ts ≥ from`.
- **Days.** `window.days = floor((to − from) / 24 h)`. `from_day` is the Bangkok date of `from`; `to_day` is the Bangkok date of the last instant before `to`, and equals `from_day` for an empty window.
- **The now point.** When `to` is now, it is `GET /portfolio`'s `equity_now` and `benchmark_now`, through the unchanged `portfolioAt(bot, 1m, now)` in the same snapshot.

**KPIs.**

| Field | Definition |
|---|---|
| `return_pct` | last series equity / first series equity − 1; `"0.000000"` with one point or a zero base |
| `benchmark_return_pct` | last non-null benchmark / benchmark base − 1. The base is the first point with a non-null benchmark. `null` when no point has one, or when the base is zero |
| `series[].benchmark` (OD-1) | `stored × (E_b / B_b)`, where `B_b` is the benchmark base and `E_b` is **that same point's** equity, computed exactly and then rounded. When the rebase mark has a benchmark, both lines start at the rebase equity |
| `series[].drawdown`, `max_drawdown_pct` | `equity / running peak − 1` (≤ 0), with the peak taken from the first point. The KPI is its minimum, `"0.000000"` when never below a peak |
| `days_to_recover` (PD4) | Bangkok-date difference from the trough to the first later point with equity ≥ the peak at the trough. `null` when not recovered. `0` when `max_drawdown_pct` is `"0.000000"`. Each point is dated by the Bangkok day it closes (`ts − 1 µs`). **Fold P2:** a point can be the trough only when its drawdown, rounded to 6 digits, is negative; among those, the trough is the earliest exact minimum |
| `sharpe`, `sortino`, `daily_returns` | `r_t = e_t / e_{t−1} − 1` over the rebase mark and the `day_end` marks, without the now point. A return whose previous equity is 0 is skipped. Sharpe = mean / sample st. dev. (N − 1) × √365. Sortino = mean / √(Σ min(r_t, 0)² / N) × √365. `null` when N < 10 or the denominator is 0 |
| `win_rate_pct`, `positions_closed`, `positions_won` | positions whose `opened_by_decision_id` is a decision of this version and that closed in the window. Net = `realized_thb` (A1). Won / closed; `"0.000000"` when none closed |
| `profit_factor` | Σ positive net / \|Σ negative net\|; `null` when no position lost |
| `decisions`, `skips`, `orders` | Rows of this version in the window. Skips are `action = 'skip'`, except rows whose `policy_result->'reasons'` equals `["observing"]`. Orders are `action IN ('buy','sell','add','trim','close')` |
| `cost_usd`, `scout_wakes` | Σ `bot_runs.counts->>'cost_usd'` over the version's runs (any loop) started in the window. Only a JSON string matching `^[0-9]{1,12}([.][0-9]{1,18})?$` counts (the bot's own guard). Scout wakes are runs with `loop = 'scout'` |
| `usd_thb`, `cost_thb` | `usd_thb` is the C6 rule-4 rate resolved for the bot at the read's now (also for a past version's window); `null` without one. `cost_thb` = the exact `cost_usd` × that rate, rounded to 2 |

**Calibration (D8, S2).**
- **Population.** The version's `propose` rows in the window whose `model->>'p'` is a decimal in [0, 1]; `n_stated` counts them.
  - The grammar is `-?[0-9]+(\.[0-9]+)?`, then 0 ≤ p ≤ 1. So `.5`, `1e-1` and `true` state nothing, and `-0` is 0.
- **Horizon column.** It comes from the candidate: `intraday → r_1d`, `days → r_5d`, `weeks → r_20d`. Anything else, or no candidate, uses `r_5d`. `n_graded` counts rows whose horizon column is not null.
- **Hit.** The horizon return is `> 0` for `long` and `< 0` for `short`. A zero return is a miss.
- **Bins.** Always ten, `lo` `"0.0"`…`"0.9"` and `hi` `"0.1"`…`"1.0"`. A bin holds `lo ≤ p < hi`; the last holds `0.9 ≤ p ≤ 1`.
  - Each bin has `n`, `mean_p` and `hit_rate`. The last two carry 3 digits and are `null` when `n = 0`.
  - Comparisons are exact.
- **ECE.** `Σ (n_b / n_graded) × |hit_rate_b − mean_p_b|`, computed from the exact bin values, 4 digits.
  - It is `null` under 30 graded, or when `states_p` is false.
  - `states_p` is false when `version.tier` is `none`; a legacy v1 config counts as `none`.

**Attribution (D7, PD5, S1).**
- **Base rows.** `actor = 'bot' AND action IN ('buy','add')`. The Bots scope takes every version; the Stats scope takes this version, in the window.
- **Modelled round-trip rate.** From the instrument's `venue_rules` row (by `venue_id` and `calendar_id`):
  - `2 × commission_pct × (1 + vat_pct) + 2 × slippage_bps / 10000`;
  - for futures, plus `2 × per_contract_fee_thb / (px_at_decision × contract_multiplier)` when `px_at_decision > 0`;
  - no rule row means rate 0.
- **Net return.** `r_5d` oriented by direction (`−r_5d` for short), minus that rate.
- **Per group.**
  - `n`;
  - `n_graded` (`r_5d` not null);
  - `win_rate`: graded rows with net > 0, over `n_graded`;
  - `avg_r_5d`: the gross stored average, unoriented, as S20;
  - `avg_r_5d_net`;
  - `best` and `worst`: the maximum and minimum net.

  All are 6 digits, and `null` when `n_graded = 0`. Key order: `key, label, tier, n, n_graded, win_rate, avg_r_5d, avg_r_5d_net, best, worst`.
- **Groups.**
  - **`source`:** every `sources` row in `GET /sources` order (tier `filing, wire, exchange, media, account`, then code), always present, then `{key: "none", label: "No signal"}` for rows without a snapshot, without a code, or with a code that is not a `sources` row.
  - **`event_type`:** by `n` descending, then key; then *No signal*.
  - **`asset_class`:** `us` "US stock" (stock on `us-equities`), `th` "Thai stock" (stock on `set`), `crypto`, `gold`, then `unknown`.
  - **`regime`:** the six `trend × vol` cells ("Up · normal volatility" …), then `unknown`.
  - Groups with `n = 0` are omitted, except the source rows.

**Post-mortem counts (D5).**
- **Losing decision.** A base row (Stats scope, in the window) whose horizon column is graded and is not a hit.
- **`labelled` and `by_label`.** They count losing decisions whose `post_mortem->'label'` is a JSON string naming one of the seven labels, with `confirmed_by_user` JSON `true`. The string `"true"` does not count.
- **`by_label`.** It always has the seven keys in the fixed order.
- **`by_labeller`.**
  - `user` and `model`: confirmed known labels whose `labelled_by` is that JSON string;
  - `proposed`: a known label that is not confirmed (0 in this slice).

**`follow_record` (D11).**
- **Rows.** The `me` bot's `buy|sell|add|trim|close` decisions with `ts ≥ now − 30 × 24 h` and `r_5d` not null, with no `actor` filter.
- **Split.** `followed` is `followed_recommendation IS TRUE`; `own` is `IS NOT TRUE`.
- **Values.** `avg_r_5d` is the gross average, 6 digits, `null` under 5 graded on that side. `n_graded` is always the count. With no manual bot, both sides are `{0, null}`.

### Review history

| Repository and round | Verdicts | What followed |
|---|---|---|
| Service plan r1 → r2 | **r1** CHANGES REQUESTED (3 blocking, 8 should-fix). Blocking: `codes_test.go` missing from the S5 and S7 Files; the M2 smelt's S6 gated-count check broken by S7; the S3 README content unchecked. Should-fix included the promote vs pause/save row-lock race and the golden's provenance. **r2** APPROVED (2026-10-26T02:19:24Z) with 2 should-fix: R2-W1, the preview seeding rule (a dedicated user), and R2-W2, carried in S1's prompt. | r2 added promote's row locks to contracts and dropped the M2 smelt. Contracts went to r2 with no shape change. |
| Web plan r1 → r2 | **r1** CHANGES REQUESTED (3 blocking, 9 should-fix). B1: a compare re-read after a promote vs OD-2. B2: per-step `stats-view.ts` gates. B3: the editor's digits (→ OD-4). ST-W-10 → OD-3. **r2** APPROVED (2026-10-26T04:32:02Z) with should-fix N1–N3. | N1: a loop guard on refused challengers. N2: a named test for compare 5xx. N3: the chip-before-signals import order. All went into the S7, S9 and S13 prompts. |
| Service code r1 → r2 (`db281db..6821b65`, then `..b81c2ab`) | **r1** code APPROVED (0/1/5). W1: `days_to_recover` broke the "0 when no drawdown" pin at the rounding edge. Security APPROVED (0/1/3). M-1: promote's re-run verdict read cash and open positions in separate READ COMMITTED statements, so a fill committing between them could flip `return_higher` / `drawdown_no_deeper`. L-1: a flagged champion without a version → 500. L-2: the losses join could not duplicate, since `orders.decision_id` and `fills.order_id` are UNIQUE. L-3: the losses cursor checksum is unkeyed (existing design). **Fold `b81c2ab`:** P1 verdict in `InSnapshot` after the locks; P2 trough by the rounded drawdown, plus fixture `sub_rounding_dip`; P3 the `CLAUDE.md` EnsureBots exception. **r2** code and security APPROVED. | FU-6 recorded the two-connection pattern. |
| Web code r1 → r3 (`9e7b8e0..e99dce9`, `..b815cb4`, `..aec5308`) | **r1:** angular CHANGES REQUESTED (2/2/6), code CHANGES REQUESTED (1/2/8), design CHANGES REQUESTED at code level (1/3/advisories). Security was code-level APPROVED (0/0/1); its formal verdict was CHANGES REQUESTED only by the W6 evidence rule, while E2E was pending. Must-fix: F1, an effect wrote `fallbackRead` (CLAUDE.md "no effect writes a store signal"); F2, *Compare bots* was live while loading or on error but its panel rendered only with figures; F3, real-service "settled" checks matched the panel status line; F4, heading order (→ OD-5). Should-fix F5–F14, including a nullable `LossRow.qty`, "no marks yet" keyed on `daily_returns === 0`, copy beyond the PRD recorded in `DESIGN.md`, long-name overflow, sticky `keepPrevious` and an `isUuid` check in `versionsRequest`. **Fix `b815cb4`** (F1–F12, F14; F13 left, since it needs new copy). **r2:** all four APPROVED. **Fold `aec5308`:** a long-name e2e test, the `CLAUDE.md` StatsService line, the words entry, and the `DESIGN.md` status names. **r3:** design and code APPROVED. | Rendered checks were left to PV1–PV3. |
| PV2 rendered design review | **r1** CHANGES REQUESTED. B1: focus lost after *Label losses* (= F-PV1-4). B2: indistinguishable source names (→ OD-7). W1–W7: spacing, the hidden calibration table overflowing by 355px, the one-label summary sentence, title wrapping, the editor note breaking, attribution cells cut at the region edge, the long-name capture. **Re-check at `a7e4e56`** APPROVED. W8: the compare grid squeezed by a long champion name at 390 → PF3. | — |

## Database

**No migration.** `RequiredSchemaVersion` stays J (`20261020041046`). The migrations head is K (`20261021082304`, an index). Production was at J or later (`verification.md`), and the preview at K. No table, column, index or environment variable was added. `attribution_snapshots` and a `bot_id` on `model_calls` were explicitly out (D10). An index needs the owner first (A7).

### What the reads use

| Table | Columns read | By |
|---|---|---|
| `bots` | `owner_user_id`, `kind`, `status`, `probation_until`, `champion`, `current_version`, `created_at` | every route (owner scope, S16's default, the `active` condition) |
| `bot_versions` | `seq`, `version` (hash), `config` (the v2 `decision_tier`), `created_at` | windows, `version.tier`, labels |
| `decisions` | `bot_version`, `ts`, `actor`, `action`, `direction`, `loop`, `candidate_id`, `instrument_id`, `qty`, `px_at_decision`, `signal_snapshot` (`source_code`, `event_type`), `model->>'p'`, `market_state->'regime'`, `policy_result` (`reasons`, `trigger`), `r_1d`, `r_5d`, `r_20d`, `exit_reason`, `followed_recommendation`, `post_mortem` | counts, calibration, attribution, losses, `follow_record` |
| `candidates` | `horizon` (via `decisions.candidate_id`) | the horizon column |
| `ledger` | `bot_id`, `ts`, `kind` (`day_end`, plus the first mark of any kind for a fresh window), `equity`, `benchmark` | series, return, drawdown, Sharpe, Sortino |
| `positions` | `realized_thb` (net, A1), `opened_by_decision_id`, `closed_at` | win rate, profit factor |
| `orders`, `fills` | `orders.decision_id`, `fills.order_id`, `fills.px` (both UNIQUE, so one row per decision) | `LossRow.fill_px` |
| `bot_runs` | `bot_version`, `loop`, `started_at`, `counts->>'cost_usd'` | cost and scout wakes |
| `venue_rules` | `commission_pct`, `vat_pct`, `slippage_bps`, `per_contract_fee_thb`, `contract_multiplier` | the modelled cost rate |
| `instruments`, `sources` | `asset_class`, calendar; `publisher`, `tier` | dimensions, labels |
| `paper_accounts` and open positions | through the unchanged `portfolioAt` | the now point |

### What slice 7 writes (first writer of each)

| Object | Written by | Rule |
|---|---|---|
| `decisions.post_mortem` | `PUT /decisions/{decision_id}/post-mortem` | Exactly `{label, labelled_by: "user", confirmed_by_user: true, labelled_at}`, by a conditional `UPDATE … WHERE post_mortem IS NULL OR post_mortem->'confirmed_by_user' IS DISTINCT FROM 'true'::jsonb`. The existing `decisions_backfill_only` trigger still rejects any other column (`TestPostMortem_Refusals` checks a direct update) and freezes a confirmed label. An unconfirmed model proposal is replaced by the user's label. |
| `bots.champion` | `POST /bots/{bot_id}/promote` | `false` on the previous champion, `true` on the challenger (`BotRepo.SetChampion`, owner-scoped), in one transaction. |
| `bot_version_events` `promoted` / `demoted` | promote | `promoted` on the challenger's current version with `detail {previous_champion: uuid \| null}`; `demoted` on the previous champion's current version with `detail {succeeded_by}`, only when there was one. The actor is the session user. |
| `events` (audit) | both writes | `bot_promoted {bot_id, version (seq), previous_champion}` and `post_mortem_labelled {decision_id, label}`. |

The bot is unchanged. It still writes outcomes, runs and `cost_usd` as before.

### Index use (FR-ST-SVC-013, A7)

`EXPLAIN (ANALYZE, BUFFERS)` on the preview (PostgreSQL 18.6) of the statements, taken verbatim from `internal/repository/postgres/{stats,attribution}.go`:
- **`period=30d`** (3,255 rows, 32 % of the table): every version-window read used `decisions_bot_ts_idx` (Index Scan Backward).
- **`statsLossesSQL`** used `decisions_bot_ts_idx` in both windows.
- **`period=all`:** the planner chose a Seq Scan on `decisions` for `statsDecisionCountsSQL`, `statsCalibrationSQL`, `statsEntryOutcomesSQL` and `attributionVersionSQL`. On that database the seeded bot owns 10,000 of 10,032 rows (99.7 %), so a full scan is cheaper.
- **Diagnostic:** with `enable_seqscan = off` (session only), the index range plan exists and costs about the same.
- No index was added.

The preview database's footprint from this build is under "Test plan".

## API

### Conventions

- **Gating.** All five routes mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`. CSRF is engine-wide on the PUT and the POST (`X-Tidewatch-Request: 1` plus the app `Origin`).
- **Gated count.** `TestRouter_ForcedChangeGatesNewRoutes` counts **64**: 61 production routes and 3 test probes. It went 59 → 60 (S4) → 62 (S5) → 63 (S6) → 64 (S7).
- **Reviewed `:bot_id` routes.** `TestRouter_NoDecisionMutation` admits exactly one new `/decisions` write, the post-mortem PUT, with the comment "the post-mortem label is the one user write to a decision; the trigger limits it to post_mortem". Its reviewed `:bot_id` routes grow from nineteen to twenty with promote.
- **Owner scope.** A bot, version or decision that is unknown or another user's is one indistinguishable `404 not_found`, never 403.
- **The manual bot.**
  - On `GET /stats` and `/stats/losses` it is the same 404 as an unknown bot.
  - Compare answers `400 {field: "challenger", reason: "manual_bot"}`.
  - Promote answers `400 {reason: "manual_bot"}`.
  - It is never S16's default.
- **Strict query.**
  - An unknown parameter is `400 invalid_request {reason: "invalid"}`, with no field.
  - A repeated one is `{field, reason: "duplicate"}`; a malformed one `{field, reason: "invalid"}`.
- **Shapes.** Every key is always present, and undefined is `null`.
- **Nothing is created.** No route calls `EnsureBots`. Promote is the one `/bots/{bot_id}` route that does not, recorded as an exception in `CLAUDE.md` (fold P3).

### Routes

| Method and path | Request | 2xx | Refusals |
|---|---|---|---|
| `GET /stats` | `bot_id?`, `version?` (a `seq`), `period?` = `30d\|90d\|all\|custom`, `from?`, `to?` | `200 {generated_at, bot, version, window, kpis, series, calibration, attribution, post_mortems}` | `400` (grammar, S8 ranges), `404` |
| `GET /stats/losses` | `bot_id` (required), `version?`, `limit?` 1–200 (default 50), `cursor?` | `200 {items: [LossRow], next_cursor}` | `400` (grammar, cursor), `404` |
| `GET /stats/compare` | `challenger` (required); a `champion` parameter is unknown | `200 {generated_at, champion \| null, challenger, shared_window \| null, verdict}` | `400` (grammar, `manual_bot`, champion as challenger), `404`, `500` for a flagged champion without a current version (fails closed; unreachable) |
| `POST /bots/{bot_id}/promote` | no query, no body (ignored, as Pause/Resume) | `200 {bot: BotSummary, previous_champion: uuid \| null}` | `400 {reason: manual_bot}`, `404`, `409 promotion_refused {reasons}` |
| `PUT /decisions/{decision_id}/post-mortem` | `{"label": "<one of seven>"}` (strict) | `200 {decision_id, post_mortem}` | `400` (body, `not_a_loss`), `404`, `409 post_mortem_frozen` |

**Changed routes (additive).**
- `GET /bots/{bot_id}/attribution`: each item gains `win_rate`, `avg_r_5d_net`, `best` and `worst` after `graded`, in that order. Every existing key, value, item and order is byte-identical to slice 6.
- `GET /recommendation`: gains `follow_record` as its **last** key on every shape, the "no recommendation" shape included.

### `GET /stats` query grammar and check order

1. **`parseQuery`:** an unknown parameter, then a duplicate, by name.
2. **Each parameter's grammar,** in the order `bot_id`, `version`, `period`, `from`, `to`:
   - `bot_id`: a hyphenated 8-4-4-4-12 UUID in either case. Braced, URN and unhyphenated forms are `invalid`.
   - `version`: plain ASCII digits, 1 to 2147483647, with no sign and no leading zero (`01` is `invalid`).
   - `from` and `to`: `YYYY-MM-DD` dates that exist.
3. **Cross-field rules,** in order:
   - `version` without `bot_id` → `{field: "bot_id", reason: "missing"}`;
   - `from` or `to` with a non-custom period (an absent period is `all`) → `{field, reason: "invalid"}`;
   - `custom` without `from` → `{field: "from", reason: "missing"}`.
4. **Bot and version** (so a foreign bot is `404` before any range check):
   - an unknown, foreign or manual bot, or an auto bot without a version → "That bot doesn't exist.";
   - an unknown version → "That version doesn't exist.";
   - with no `bot_id` and no gradable bot → "No bot to grade yet.".
5. **S8 ranges,** each `out_of_range`:
   - `from > to` → `field: "from"`;
   - a `to` ending at or before the version start → `to`;
   - a `from` at or after the window end → `from`;
   - more than 366 dates → `to`.

An empty window is never an error: a version made a minute ago answers zeros, `null`s and the ten source rows.

The body, exactly as the contract shows (PRD §6.1, contracts §2.4; key order as shown):

```json
{
  "generated_at": "2026-10-25T07:00:00Z",
  "bot": {"bot_id": "…", "name": "Driftline", "champion": false, "status": "running"},
  "version": {"seq": 7, "hash": "9ad1…", "label": "v7·9ad1", "created_at": "…", "current": true, "tier": "jev"},
  "window": {"period": "all", "from": "…", "to": "…", "from_day": "2026-07-04", "to_day": "2026-10-04", "start": "…", "end": null, "days": 92},
  "kpis": {
    "return_pct": "0.084100", "benchmark_return_pct": "0.031200",
    "max_drawdown_pct": "-0.030800", "days_to_recover": 11,
    "sharpe": "1.6100", "sortino": "2.2400", "daily_returns": 91,
    "win_rate_pct": "0.570000", "profit_factor": "1.8200", "positions_closed": 44, "positions_won": 25,
    "decisions": 212, "skips": 31, "orders": 97,
    "ece": "0.0410", "n_stated": 190, "n_graded": 184,
    "cost_usd": "2.710000", "cost_thb": "96.40", "scout_wakes": 38, "usd_thb": "35.57"
  },
  "series": [{"ts": "…", "equity": "1000000.00", "benchmark": "1000000.00", "drawdown": "0.000000"}],
  "calibration": {"bins": [{"lo": "0.6", "hi": "0.7", "n": 42, "mean_p": "0.652", "hit_rate": "0.667"}], "ece": "0.0410", "n_stated": 190, "n_graded": 184, "states_p": true},
  "attribution": {
    "source": [{"key": "sec-8k", "label": "SEC 8-K", "tier": "filing", "n": 61, "n_graded": 58, "win_rate": "0.640000", "avg_r_5d": "0.009800", "avg_r_5d_net": "0.008400", "best": "0.062000", "worst": "-0.038000"}],
    "event_type": [], "asset_class": [], "regime": []
  },
  "post_mortems": {"losing": 87, "labelled": 61, "by_label": {"signal_late": 21, "already_priced": 17, "regime_shift": 9, "stopped_by_noise": 7, "signal_wrong": 4, "sizing": 2, "execution": 1}, "by_labeller": {"user": 61, "model": 0, "proposed": 0}}
}
```

Notes on the `bot` and `version` objects:
- `bot.status` is `running`, `observing` or `paused`.
- `version.hash` is the full 64-hex hash, and `label` is `v{seq}·{hash[0:4]}`.
- `version.current` means `bots.current_version` is this version.
- `version.tier` is the v2 `decision_tier` (`none | jev | small_llm | large_llm`), or `none` for a legacy v1 config.

### `GET /stats/losses`

- **Check order.**
  1. `parseQuery`.
  2. `bot_id`: absent → `missing`, else not hyphenated → `invalid`.
  3. `version`: S4's grammar.
  4. `limit`: non-digits `invalid`; outside 1–200 `out_of_range`.
  5. `cursor`: empty → `invalid`.
  6. The service: cursor syntax (before the bot), then bot and version (as for `/stats`), then the cursor binding.
- **Items.**
  - Losing decisions of the version over the **whole version window** (not a period), whose `post_mortem` is `null` or not confirmed.
  - Ordered `ts DESC, decision_id DESC`; 50 per page by default.
  - Membership: `d.bot_version = hash AND created_at ≤ ts < (next version's created_at, else now)`, `actor = 'bot'`, `action IN (buy, add)`, horizon column graded and not a hit.
- **`LossRow`**, keys in order:

```json
{"decision_id": "…", "ts": "…", "loop": "scout", "version_label": "v7·9ad1", "action": "buy",
 "instrument_id": "NVDA@webull", "display_symbol": "NVDA", "qty": "16.2", "fill_px": "131.40",
 "exit_reason": "stop",
 "signal": {"source_code": "sec-8k", "publisher": "SEC 8-K", "tier": "filing", "p": "0.68", "horizon": "days"},
 "trigger": null, "horizon_column": "r_5d", "outcome_net": "-0.024000", "post_mortem": null}
```

  Field rules:
  - `qty` and `fill_px` read as `GET /decisions` answers them; `fill_px` is `null` without a fill.
  - `signal` follows XP-1's null rules.
  - `trigger` is `policy_result->>'trigger'`.
  - `outcome_net` is the stored, unrounded horizon return oriented by direction, minus the modelled rate at `px_at_decision`, computed exactly and then rounded to 6 digits.
- **Cursor.** On the decisions wire, kind byte `L` (0x4C). The checksum input is `version(8) ‖ 'L' ‖ bot_id(16) ‖ seq(8) ‖ ts µs(8) ‖ decision_id(16)`, 57 bytes, bound to the bot and the version by `seq`.
  - A decisions, runs or candidates cursor is `400 {field: "cursor", reason: "invalid"}`; so is a losses cursor of another bot or version, or an edited one.
  - A losses cursor sent to `GET /decisions` or `GET /bots/{bot_id}/decisions` is refused the same way.
  - The candidates cursor's state byte `L` sits at another offset of a 50-byte input, so the two cannot collide.

### `PUT /decisions/{decision_id}/post-mortem`

Checks, in order (contracts §5, the README):
1. Any query parameter → `400` (no field).
2. A path id that is not a UUID (`uuid.Parse`) → `404`.
3. The body: an extra key is `unknown_field` (never named); `label` absent or `null` is `{field: "label", reason: "missing"}`; outside the seven is `{field: "label", reason: "invalid"}`. Because the body is checked before ownership, a bad body on a foreign decision is `400`.
4. Not the user's decision → `404` "That decision doesn't exist.".
5. Not a losing `buy | add` with `actor bot` of any of the user's bots → `400 {field: "decision_id", reason: "not_a_loss"}` "Only a losing buy or add of a bot can be labelled.". This covers a winner, an ungraded row, a skip and a manual decision. The decision need not be of the current version.
6. Already confirmed → `409 post_mortem_frozen` "That decision was already labelled.", with no details. A conditional `UPDATE` that matches no row (a race lost) is `409` too, and so is a second identical PUT.

The write runs in one READ COMMITTED READ WRITE transaction (`PostMortemStore.InPostMortemTx`), with no advisory or row lock beyond the UPDATE's own. It sets `labelled_at` from the service clock at full precision, so the stored object and the answer share one value. The audit row is written in the same transaction. The handler logs `post_mortem_labelled` (`decision_id`, `label`) after the commit.

### `GET /stats/compare` and the verdict

- **Check order.**
  1. `parseQuery` (`champion` is an unknown parameter here).
  2. `challenger` absent → `missing`, or malformed → `invalid`.
  3. In one snapshot: an unknown or foreign bot → `404` "That bot doesn't exist.".
  4. The manual bot → `400 {challenger, manual_bot}` "The manual bot can't be compared.".
  5. An auto bot without a version → `404`.
  6. The champion itself → `400 {challenger, invalid}` "That bot is the champion." (OD-2).
- **The champion** is the user's `kind = 'auto'` bot with `champion = true`. A flagged champion without a current version is an internal error (`ErrChampionWithoutVersion`, 500), not the first-champion branch, because promote must see the same champion.
- **The shared window** is `[max(both current versions' created_at), now]`, under `all`'s rules. Both sides' `kpis` come from the same `statsFigures` function `GET /stats` uses. A side whose version started later reads exactly as its `GET /stats` answer.
- **Comparisons use the answered (rounded) figures:** returns and drawdowns at 6 digits, ECE at 4. So the verdict never contradicts its own detail. An equal return is not higher; an equal |drawdown| or ECE passes.

| Code | Met when | `detail` |
|---|---|---|
| `window_30d` | `days ≥ 30` | `{days}` |
| `return_higher` | challenger `return_pct` > champion's, strictly | `{challenger, champion}` |
| `drawdown_no_deeper` | \|challenger `max_drawdown_pct`\| ≤ \|champion's\| | `{challenger, champion}` |
| `calibration_no_worse` | challenger `ece` ≤ champion's, when both versions state p and both have `n_graded ≥ 30`; else `met: null` | `{challenger, champion}`, or `{skipped}`: the first of `champion_states_no_p`, `challenger_states_no_p`, `too_few_graded` |
| `active` | `kind = 'auto'`, `status = 'running'`, `probation_until` null or ≤ now | `{status, probation_until}` |
| `first_champion` | always | `{}` |

- **With a champion,** the conditions are `window_30d, return_higher, drawdown_no_deeper, calibration_no_worse, active`, in that order.
- **With none,** `champion` and `shared_window` are `null`. The challenger is read over its own current-version window to now, and the conditions are `first_champion`, `window_30d` (its own days) and `active`.
- **`passes`** is true when every `met` is `true` or `null`.

### Promotion semantics and locking (`POST /bots/{bot_id}/promote`)

1. **The transaction and lock.** `Store.InLockedTx(MeBotLockKey(user))`: READ COMMITTED, with the advisory lock taken first. A REPEATABLE READ snapshot would have been taken before the lock wait and missed a concurrent promote. It is the same lock that create, clone and resume hold.
2. **Load the bot, owner-scoped.** Another user's, an unknown one and a malformed id are the one `404`. There is no `EnsureBots`.
3. **Refuse the manual bot:** `400 {reason: "manual_bot"}` "The manual bot can't be promoted.".
4. **Find the current champion** (`userChampion`).
5. **Lock the rows.** `BotRepo.LockBot` locks the challenger and the champion (when it is another bot) `FOR NO KEY UPDATE`, in **ascending `bot_id` byte order**. That is the lock Pause, Resume and Save as vN take. No Pause, Save or promote can change the flag, the status or `current_version` between the check and the flip, and no lock cycle is possible (contracts r2 §7). The champion found before the locks must still be flagged on its locked row; otherwise the internal error `errChampionMoved` is raised, which is unreachable under the advisory lock.
6. **Refusals from the locked rows:**
   - the champion itself, including a lost race → `409 promotion_refused {reasons: ["already_champion"]}` "That bot is already the champion.";
   - no current version → `["no_current_version"]`.
7. **Re-run the verdict (`compareBots`) in a snapshot.** Since fold P1, it runs in a `Store.InSnapshot` (REPEATABLE READ READ ONLY) begun **after** the row locks are held, on a second pool connection.
   - Its `BEGIN`, pool acquisition included, is bounded by `queryTimeout`. If the pool is exhausted it fails closed: 500, and the locked transaction rolls back.
   - It takes no lock, none on `paper_accounts` included, and commits before the first write.
   - Cash and open positions therefore come from one snapshot, and the verdict never sees a fill half-applied.
   - `TestPromoteBot_VerdictReadsInSnapshot` pins the call order: locked begin → `BotByID` → `UserBots` → `LockBot` (ascending) → snapshot begin → `StatsVersion` → snapshot end → locked end.
8. **A failing verdict** → `409 promotion_refused` "That bot can't be promoted yet.". The unmet conditions are listed in condition order: `window_30d → window_too_short`, `return_higher → return_not_higher`, `drawdown_no_deeper → drawdown_deeper`, `calibration_no_worse → calibration_worse`, `active → not_active`. `same_bot` is documented and never sent.
9. **On a pass,** all at one `now`, with the session user as actor:
   - previous champion `champion = false`, then challenger `true`;
   - `promoted` (with `previous_champion`);
   - `demoted` (with `succeeded_by`), only when there was a champion;
   - the audit `bot_promoted`.
10. **After the commit,** the handler logs `bot_promoted` (`bot_id`, and `previous_champion` only when there was one; no seq, no name). It answers the `GET /bots` item read after the commit, whose `champion` is true.

A refusal writes nothing. Two concurrent promotes end with exactly one champion (`TestPromote_Concurrent`). A Pause holding the challenger's row lock commits while promote waits; promote then answers `409 [not_active]` and writes nothing (`TestPromote_PauseRace`). The flag is read by the Bots *Champion* tag and by `recommendations.follow = "champion"` on their next read. A later version of the champion keeps the flag (D3), and its compare window restarts.

### Codes, audit, metrics and logs

| Code | HTTP | Where | `details` |
|---|---|---|---|
| `promotion_refused` | 409 | promote | `{reasons: [string]}` (typed `PromotionDetail`; `PublicDetails` keeps only the eight documented reasons, in order, and always sends an array) |
| `post_mortem_frozen` | 409 | post-mortem PUT | none |
| `invalid_request` | 400 | all five | `{field?, reason}`; new reason `not_a_loss` |

- **Codes.** Both new codes come after `run_rate_limited` in `AllCodes()`, giving 20 trade codes, and the README error table has two new rows (`TestCodes_Contract`, `TestAllCodes_MatchContract`, `TestReason_ClosedSet`). The `PromotionReason*` strings are duplicated in `apperror`, and an equality test checks them (`TestBotsHandler_Promote`).
- **Audit.** `bot_promoted {bot_id, version, previous_champion}`. `version` is the integer seq, and `previous_champion` is always present (JSON `null` for the first champion). `post_mortem_labelled {decision_id, label}`. Both use typed constructors only. `audit.Types()` orders `bot_promoted` before `post_mortem_labelled` (`TestAudit_StatsEvents`). `test/integration/events_test.go` was edited twice, outside the step Files, to pin these types.
- **Metrics.** `stats_reads_total{kind}` and `stats_read_seconds{kind}` (a histogram with Prometheus' default buckets, which include 0.5 s), with `kind` in `stats | compare | losses`, all at 0 from startup (`TestMetrics_StatsSeries`). Each request that reaches the service counts once; a query refused in the handler does not.
- **Logs** (info, ids and enums only, after the commit): `bot_promoted` and `post_mortem_labelled`. `TestLogs_NoBotTextOrConfig` promotes a sentinel-named champion and labels a sentinel-rationale loss, then checks that neither text reaches the log.

## Components

Angular 22 standalone components with signals and `httpResource`, tested with Vitest. Paths are under `src/app/pages/workspace/` unless shown otherwise. No chart library is used on Stats, and no token, colour, type step, icon, transition, animation or dependency was added.

### Data layer

- **`data/stats.model.ts`.** Strict readers for `GET /stats`, `/stats/losses` and `/stats/compare`.
  - Every key is required and unknown keys are ignored. An unknown vocabulary value, or a malformed body, is a `StatsParseError`.
  - Extra cross-field checks: ten bins, `drawdown ≤ 0`, `passes` consistent with the conditions.
  - `LossRow.qty` is nullable (F5). `signal.source_code`, `publisher` and `tier` may be null (XP-1).
  - `PROMOTION_REFUSAL_REASONS` lives in `trade.model.ts` and is re-exported here.
- **`data/stats-api.service.ts` (`StatsApi`, ST-W-5).** The five calls. It always sends `period`, and errors go through `toTradeApiError`. CSRF is added by `authInterceptor`.
- **`data/bots.model.ts` and `bots-api.service.ts`.**
  - `SourceAttribution` requires the four new keys.
  - `parseRecommendation` requires `follow_record`.
  - `parseBotVersions` and `BotsApi.versionsRequest` are the first web reader of the slice-6 `GET /bots/{bot_id}/versions`; it feeds the *Version* select (ST-W-4).
  - Every older unit and e2e fixture was refreshed, with no lenient reads.
- **`feat-stats/data/stats.service.ts` (`StatsService`, SE-5).** Provided by `app-stats`.
  - **URL truth (ST-W-6).** `util/stats-url.ts` parses `bot` (a UUID), `v` (a whole number, only with `bot`), `period` (`30d|90d|all`), `from`/`to` (`from` means custom), `compare` (a UUID) and `losses=1`. Malformed, repeated or orphaned keys are dropped with one merging `replaceUrl`.
  - **Reads.** `GET /stats`, the labelling list's first page and `GET /stats/compare` are `httpResource`s keyed on the URL. `GET /bots` and the versions read feed the selects. A per-bot read without `bot` in the URL uses the answer's `bot.bot_id`.
  - **No timer (ST-W-8).** It reads on open, on a control change, on *Try again*, after a saved label and after a promotion.
  - **`keepFigures` (F10).** The last answer stays while another query loads, unless the last settled read failed.
  - **`fallbackRead` (F1).** A `linkedSignal`, because no effect writes a store signal.
  - **Fallbacks (ST-W-7).**
    - A `404` on a query that named `bot` or `v` drops them, reads the default, and shows "That bot or version doesn't exist. Showing {bot} {label}." for one load.
    - A `404` without `bot` is the empty state.
    - A `400` on the period keys drops them and reads `all`.

### The Stats screen (`feat-stats/`)

The `/stats` route loads `Stats` (`app-stats`, host class `stats-screen`). `feat-screen-placeholder/` was deleted, since Stats was its only user.

**Order on the page:**
1. `app-page-header`: `h1` *Stats*, a sub line, and *Compare bots* in the actions slot.
2. The controls row.
3. The KPI strip.
4. Grid 1: *Equity against benchmark* and *Does confidence mean what it says?*.
5. Grid 2: *What each source earned* and *Why trades lost*.
6. The labelling list, when open.
7. The compare panel, when open.
8. The screen's `app-toast`.

**The sub line, populated:** "{bot} {label} · out-of-sample since {start date} · {window words} · benchmark is equal-weight buy and hold of the bot's watchlist". The window words are "{days} days on paper", "last 30 days", "last 90 days" or "{from} – {to}".

**States (PRD §4.10).**

| State | What shows |
|---|---|
| Loading | Sub line "Loading…"; a polite `.status-line` "Loading stats…"; the controls stay |
| Error | "Stats couldn't load." as a centred `.error-message`, with *Try again*; focus goes to the `h1` |
| Empty | `app-empty-state` "Nothing to grade yet" / "Stats appear once an auto bot has a version. Create one on Bots."; the controls and *Compare bots* are hidden |
| Populated | the full screen |
| Fresh | `0.00%`, "—", `0`; a flat line; ten source rows at `n 0`; "0 losing decisions". "no marks yet" is keyed on `daily_returns === 0` (F6) and sits on the Max drawdown note |
| Rules-only | "This version states no probabilities. A rules-only bot has nothing to calibrate."; ECE KPI "—" with "states no probabilities" |
| Few graded | "Not graded yet. The plot needs 30 graded decisions with a stated probability; {n_graded} so far." |
| Switching | old figures kept, strip `aria-busy` |
| Fallback | the one-load fallback sentence |
| Compare: passing, refused, first, disabled; promoted | see the compare panel |
| Losses open, labelled | see the labelling list |

These sixteen states are the capture matrix: populated, loading, error, empty, fresh, rules-only, few-graded, switching, fallback, compare-passing, compare-refused, compare-first, compare-disabled, promoted, losses-open and labelled.

**Pieces.**
- **`stats-controls.ts`** has three controls:
  - the labelled *Bot* select: auto bots with a current version, in `GET /bots` order, "· champion" on the champion;
  - the *Version* select: newest first, the service's label, "(current)";
  - the `.range-switch` *30 d* / *90 d* / *All* / *Custom* (`button[aria-pressed]` in a named group). *Custom* reveals native *From* / *To* date inputs bounded by the answer's window. For a past version the upper bound is the Bangkok day of the last instant before `end` (F12).
- **`kpi-row.ts`.** Seven cells: Return, Max drawdown, Sharpe, Win rate, Decisions, Calibration error, Cost of decisions.
  - Each cell has a label, a `.num` and a note, with §4.3's notes:
    - "benchmark {x}";
    - "{n} days to recover" / "not yet recovered";
    - "Sortino {s} · daily, ×√365";
    - "profit factor {pf} · per closed position" / "no losses yet";
    - "{skips} skipped on purpose";
    - "{n_graded} graded · 10 bins" / "states no probabilities" / "{n} graded · needs 30";
    - "{wakes} scout wakes · ${cost_usd}".
  - The figures are never coloured. The win rate reads `57.00%` (ST-W-3), where the mockup shows `57%`.
  - The bordered strip has 7 columns, 4 at ≤ 1250 and 2 at ≤ 600.
- **`stats-equity-chart.ts` (`app-stats-equity-chart`, ST-W-1).** A sibling of Overview's chart on `portfolio.css`'s classes; `feat-overview/` and `util/chart-geometry.ts` are untouched.
  - Inline SVG with three gridlines: the benchmark path (`--violet` at `--opacity-benchmark`), the equity path (`--brand`) and the `.drawdown` area between the running peak and the equity (`--down` at .12, swatch .18).
  - Four Bangkok date labels ("4 Jul") and right-hand value labels in millions of baht, as HTML `.axis` spans over the stretched SVG, so the viewBox never squashes them.
  - SE-17 keys: `role="img"`, `tabindex="0"`, ArrowLeft/Right, Home/End, Escape and blur, and nearest-point pointer picking. The tip is `aria-hidden`, and a polite status speaks keyboard moves only.
  - The legend has the bot's label, *Buy & hold benchmark*, *Drawdown from peak*, and "THB · marked daily" (hidden at ≤ 820).
  - `util/stats-chart-geometry.ts` does drawing arithmetic only.
- **`calibration-plot.ts`.**
  - A `role="img"` SVG: gridlines at 0/25/50/75/100, a dashed `.diagonal`, and one `--violet` `.dot` per non-empty bin of radius `3 + √n / 1.4`, each with a `<title>`.
  - The caption, verbatim; the line "Expected calibration error {ece} · {n_graded} graded"; S10's hidden table of the ten bins.
  - PF2 fixed that hidden table pushing the page 355px wide at 1100 and 390 (W2).
- **`attribution-table.ts`.** A bare `.section` *What each source earned*:
  - the `h2`, a `.count` of groups, and the note "average 5-day return after acting, net of modelled costs";
  - a named group "Attribution dimension" of four `button.chip[aria-pressed]`: *Source*, *Event type*, *Asset class*, *Regime*. The choice is screen state, not URL state;
  - a `.table-scroll` region "Attribution, scrollable table" holding *Decisions*, *Graded*, *Win rate*, *Avg 5 d, net*, *Best*, *Worst*, plus *Trust* on Source only;
  - returns in the change-tone classes, and "—" while ungraded;
  - A2's words under the table;
  - Source rows named through `SOURCE_NAMES` (OD-7).

  After PF2, all eight columns fit at ≥ 1251px, and the table scrolls in its region at 1100 and 1080. `.chip` moved byte for byte from `signals.css` to a new `chip.css`, imported before `signals.css` (ST-W-14); Signals renders unchanged.
- **`losses-panel.ts`.** *Why trades lost*, with the note "{losing} losing decisions · {labelled} labelled".
  - One `.pm` row per label, in fixed order: *Signal was late*, *Already priced in*, *Regime shift*, *Stopped by noise*, *Signal was wrong*, *Sizing*, *Execution*. Each has an `aria-hidden` `--text-2` bar (`.pm-bar`) and its count, followed by a fainter *Not labelled yet* row.
  - PD6's template paragraph, with the share of labelled losses as a whole percent from counts. That share is the web's one derived figure. W3 added a one-label sentence for when the second count is 0.
  - The line "Labels: user {u} · model {m} (model proposals arrive with slice 8)".
  - *Label losses* (`aria-expanded`, `aria-controls`) sets `losses=1` and moves focus to the list's `h2`.
- **`losses-list.ts`.** A bare `.section.losses` *Label why trades lost*, with a `.count` and the note "losing decisions of this version without a label · newest first", and a region "Losing decisions, scrollable table".
  - **Columns:**
    - *When* ("Thu 1 Oct, 14:00" over "{loop} · v{seq}");
    - *Decision* ("Buy NVDA 16.2" over "filled {px} · closed by {word}");
    - *Signal* ("{source name} · {Tier}" over "p {p} · {horizon}", or *No signal* with the trigger);
    - *Outcome* (net, tone class, "{h} d, net");
    - *Label* (a native select "Choose a reason…" plus the seven words; a model proposal preselects it and says "proposed by the model");
    - *Save*.
  - **ST-W-18 words.** Exit words read "closed by stop", "closed on horizon", "closed by invalidation", "closed on zone change", "closed by the protect rule" and "closed by you"; an unknown value reads as stored. `fill_px` null reads "not filled". The other null fields drop their phrase.
  - **Save outcomes (ST-W-13):**
    - `200`: the tag "Labelled by you · {word}", *Frozen*, `GET /stats` re-read, and the toast "Label saved.";
    - `409`: the list re-reads, and the toast "That decision was already labelled.";
    - `404`/`400`: the list re-reads, and the toast "Couldn't save the label. Try again.";
    - network or 5xx: the select keeps its value, with the same toast.
  - *Save* is soft-disabled with `aria-busy` while in flight. Empty list: "No losing decision of this version is waiting for a label.".
  - **PF1.** The named region is the list body in every state, and `.table-scroll` is applied only with rows. Before this, focus was lost while the list loaded (F-PV1-4).
- **`compare-panel.ts`.** A `.stats-panel.compare`.
  - **Selects.** *Champion* (read-only, or "No champion yet") and *Challenger* (other auto bots with a version, never the champion).
  - **Note.** "shared out-of-sample window {from} – {to} · {days} days", omitted when `shared_window` is null.
  - **Grid.** A `.compare-grid` with `role="table"`: Return, Max drawdown, Sharpe · Sortino, Calibration error, Decisions · graded with p, Status.
    - With no champion, the heading reads "Over its own window" (OD-6).
    - PF3 set the columns to `minmax(0,1fr) fit-content(32%) fit-content(32%)` (W8).
  - **Verdict.** A headline and one line per condition, worded from `code`, `met` and `detail` (PRD §4.8 words; the skip reasons and `no_current_version` per ST-W-18). Met lines are `--text`, unmet `--text-2`. Reasons never come from the web.
  - **Opening.** *Compare bots* opens the panel with `aria-expanded`/`aria-controls` and moves focus to the panel's title.
    - It is soft-disabled with the title "Create a second auto bot to compare" only when no challenger exists (OD-3), and only once `GET /bots` has loaded.
    - It is also soft-disabled while the screen loads or failed (F2).
  - **Default challenger (ST-W-11).** The shown bot when it is not the champion, else the first listed.
    - A compare `404`, or a `400` on `challenger`, drops `compare` and falls back. Refused ids are kept for the screen's life and never read again (N1); the panel closes when none is left.
    - A compare 5xx shows "Stats couldn't load." with *Try again* inside the panel (N2).
  - ***Promote to champion*** is a `.btn.primary`, enabled only on `passes`; otherwise it is `aria-disabled` with `aria-describedby="compare-verdict"`. Outcomes (ST-W-12):
    - **`200`, or `409 ["already_champion"]`:** the promoted state.
      - The toast "{name} is the champion." (+ " {old} was demoted.").
      - *Champion* soft-disabled; grid and verdict kept as answered.
      - `GET /bots` and `GET /stats` re-read.
      - **No compare read for the new champion** (OD-2). The *Challenger* select then offers "Choose a challenger…".
    - **Any other `409`:** re-renders the verdict from the reasons, then re-reads compare and the bots.
    - **Network or 5xx:** the toast "Couldn't promote {name}. Try again.".
- **Formatting (ST-W-3).** `util/stats-view.ts` holds every Stats word and S15's formatting:
  - signed ratios with two digits and U+2212 through `formatRatioPercent(…, 2)`;
  - ECE with 3 digits; Sharpe and Sortino with 2;
  - THB through `formatThb`;
  - dates as "4 Jul 2026" and "Thu 1 Oct, 14:00".

  It imports `TIER_WORDS` (feat-signals) and `TONE_CLASS` (feat-trade), which are cross-feature imports. There is no `Date.now()` or argument-less `new Date()` in `feat-stats/`.

### Styles (`src/styles/components/stats.css`)

- Every rule (89 at PF3) sits under `.stats-screen`, inside `@layer components` (ST-W-2).
- The pieces: `.stats-controls`, `.kpis`/`.kpi`, `.stats-grid` (1.8fr/1fr, 1.5fr/1fr at ≤ 1080, one column at ≤ 820), `.stats-panel` with `.panel-head`, `.drawdown`, `.calibration` (`.diagonal`, `.dot`, `.caption`, `.ece`), `.pm`, `.losses`, `.compare-grid` with `display: contents` rows, `.verdict`, and a new scoped `.panel-status`.
- **OD-5.** `.stats-screen .panel-head h2` takes `--text-h3`, `--font-weight-title` and `--text`.
- **Busy buttons (ST-W-15).** `.stats-screen .btn[aria-busy="true"]` copies ORCH-30's rule.
- **No zone hues.** `--z-*` never appears in `feat-stats/` or `stats.css`, specs included.

### The Bots version editor (FR-ST-WEB-010)

`weightRow` in `feat-bots/util/bot-draft.ts` reads `avg_r_5d_net`.
- It writes the figure with two fraction digits and U+2212 (OD-4), worded "avg 5 d, net · n {n}". Before this it read "avg 5 d · n {n}".
- The ungraded "n {n}" and *Fit weights*, which still reads gross, are unchanged.
- PF2 moved `SOURCE_NAMES` out of `bot-draft.ts` into the shared `pages/workspace/util/source-names.ts` (OD-7), and fixed the note breaking between "n" and its count (W5).

### Trade: the follow-record sentence (FR-ST-WEB-011)

`followRecordSentence` (`feat-trade/util/recommendation-view.ts`) words PRD §4.9:
- "Over 30 days, decisions that followed a recommendation averaged {a}% after 5 days; your own ideas averaged {b}% ({n_f} and {n_o} graded)."
- When either average is null: "Not enough graded decisions yet to compare followed recommendations with your own ideas ({n_f} and {n_o} so far)."

The figures go through the signed ratio format, which already carries "%", so no second "%" is printed. `recommendation-card.ts` draws it as `p.reco-record` after `section.reco` on every loaded answer: not a live region, no tone class, `--text-2` (`trade.css`).

### Playwright

- **Mock.** `e2e/src/support/stats.ts` serves contracts r2's exact bodies. It fails closed on a wrong query, a wrong body, a missing `X-Tidewatch-Request: 1`, or a compare read the screen must never make (repeat reads of refused ids, a compare read after a promotion, an unpasted champion).
- **Spec and matrix.** `e2e/src/stats.spec.ts` (258 tests under `[authed]`) covers:
  - the URL state, period, attribution dimension, labelling and promote/refuse flows;
  - the N1 loop scenario and the N2 compare-5xx test;
  - a 40-character long-name test outside the matrix;
  - 160 state captures (`stats__{state}-{theme}-{width}.png` at 1440, 1100, 1080, 600 and 390 in both themes) and 40 element captures (`stats__kpis-…`, `stats__calibration-{populated|rules-only|few-graded}-…`);
  - 14 axe and 14 contrast titles (7 states × 2 themes).
- **Quiet default.** `QUIET_STATS` (`support/market-watch.ts`) answers `GET /stats` with a 404, so mocked hops land on the empty state. On the real service, Stats can be in any state, because the zone bot that `EnsureBots` creates makes it populated.
- **Captures elsewhere.** `trade__follow-record-{graded|few}-…` and `bots__editor-net-…`.
- **Known mock simplification.** The mock's `seriesInstants` falls back to the first `day_end` before the opening mark, where the contract says the first mark of any kind. So PV2's v1-window captures show one fewer equity point than real data.

## Files touched

No `git diff` was run for this document. The lists come from each plan's per-step Files, the recorded deviations and the fix-round and preview-fix records (PF2's from its `git status` capture).

| Repository | Range (base..PR head) | Merge |
|---|---|---|
| tidewatch-service | `db281db..5ab46d3` | `f289b9f` |
| tidewatch-web | `9e7b8e0..9a88771` | `74918fd` |

### tidewatch-service (PR #15, https://github.com/tidewatch-labs/tidewatch-service/pull/15)

- **S1 (the attribution module).**
  - Created: `internal/trading/costrate.go`, `costrate_test.go`, `internal/services/trading/attribution_test.go`, `test/integration/attribution_compat_test.go`, `test/integration/testdata/bots_attribution_slice6.golden.json`.
  - Modified: `internal/services/trading/attribution.go`, `internal/repository/postgres/attribution.go`, `internal/handlers/bots.go`, `bots_test.go`, `test/integration/bot_weights_test.go`, `README.md`.
- **S2 (window and arithmetic).** Created: `internal/trading/stats.go`, `stats_test.go`, `internal/trading/testdata/stats/{arithmetic.json,gen_arithmetic.py,README.md}`, `internal/services/trading/statswindow.go`, `statswindow_test.go`.
- **S3 (calibration).**
  - Created: `internal/trading/calibration.go`, `calibration_test.go`, `testdata/stats/{calibration.json,gen_calibration.py}`.
  - Modified: `testdata/stats/README.md`.
- **S4 (`GET /stats`).**
  - Created: `internal/repository/postgres/stats.go`, `internal/services/trading/stats.go`, `internal/handlers/stats.go`, `stats_test.go`, `internal/observability/metrics/stats.go`, `test/sql/stats_{series,kpis,calibration,attribution,post_mortems}.sql`, `test/integration/stats_fixtures_test.go`, `stats_test.go`.
  - Modified: `internal/observability/metrics/metrics.go`, `metrics_test.go`, `internal/app/router.go`, `router_test.go`, `README.md`.
- **S5 (losses, post-mortem).**
  - Created: `internal/services/trading/postmortem.go`, `test/integration/stats_losses_test.go`, `post_mortem_test.go`.
  - Modified: `postgres/stats.go`, `postgres/decision.go`, `services/trading/cursor.go`, `cursor_test.go`, `services/trading/stats.go`, `handlers/stats.go`, `stats_test.go`, `handlers/decisions.go`, `decisions_test.go`, `pkg/apperror/codes.go`, `codes_test.go`, `apperror.go`, `apperror_test.go`, `internal/audit/audit.go`, `audit_test.go`, `router.go`, `router_test.go`, `README.md`.
  - Outside the list: `test/integration/events_test.go` (the `audit.Types()` pin).
- **S6 (compare).**
  - Created: `internal/services/trading/promotion.go`, `promotion_test.go`, `test/integration/stats_compare_test.go`.
  - Modified: `services/trading/stats.go` (`statsFigures` factored out, output unchanged), `handlers/stats.go`, `stats_test.go`, `router.go`, `router_test.go`, `README.md`.
- **S7 (promote).**
  - Created: `internal/services/trading/promote.go`, `test/integration/promote_test.go`.
  - Modified: `postgres/bot.go`, `handlers/bots.go`, `bots_test.go`, the four `pkg/apperror` files, `audit.go`, `audit_test.go`, `router.go`, `router_test.go`, `README.md`.
  - Outside the list: `test/integration/events_test.go` again.
- **S8 (`follow_record`).** Modified: `postgres/stats.go`, `services/trading/recommendation.go`, `recommendation_test.go`, `handlers/recommendation.go`, `recommendation_test.go`, `test/integration/recommendation_test.go`, `README.md`.
- **S9 (scope and docs).**
  - Created: `test/integration/stats_scope_test.go`.
  - Modified: `test/integration/redaction_test.go`, `README.md`, `CLAUDE.md` (59 → 64 everywhere, and a new "Stats invariants (slice 7)" section).
- **Fold `b81c2ab`.**
  - `services/trading/promote.go` and a new unit test file, `internal/services/trading/promote_test.go`.
  - `internal/trading/stats.go`, `test/sql/stats_kpis.sql`, `gen_arithmetic.py` and the regenerated `arithmetic.json` (scenario `sub_rounding_dip`; the ten earlier scenarios byte-unchanged).
  - The testdata `README.md`, `README.md` and `CLAUDE.md`.
- **Unchanged by design:** `fitweights.go`, `portfolio.go`, `recommend.go`, `internal/trading/arith.go`, the C3/C10/C11 fixtures, `internal/market/waves`, `internal/config`, `.env.example` and `schema.go`. There is no `migrations/` directory, and no source contains "preview".

### tidewatch-web (PR #20, https://github.com/tidewatch-labs/tidewatch-web/pull/20)

Paths under `src/app/pages/workspace/` unless shown otherwise.

- **S1.**
  - Created: `data/stats.model.ts`, `stats.model.spec.ts`, `data/stats-api.service.ts`, `stats-api.service.spec.ts`.
  - Modified: `data/trade.model.ts` and its spec.
- **S2.** Modified: `data/bots.model.ts`, `bots-api.service.ts` and their specs; the fixtures in `feat-bots/bot-version.spec.ts`, `feat-bots/data/bot-editor.service.spec.ts`, `feat-bots/editor/editor-weights.spec.ts`, `feat-bots/util/bot-draft.spec.ts`, `feat-trade/data/recommendation.service.spec.ts`, `feat-trade/recommendation-card.spec.ts`, `feat-trade/trade.spec.ts` and `feat-trade/util/recommendation-view.spec.ts`.
- **S3.**
  - Created: `feat-stats/stats.ts`, `stats.spec.ts`, `stats-controls.ts` and spec, `feat-stats/data/stats.service.ts` and spec, `feat-stats/util/stats-url.ts` and spec, `feat-stats/util/stats-view.ts` and spec, `src/styles/components/stats.css`.
  - Modified: `workspace.routes.ts`, `src/app/app.routes.spec.ts`, `src/app/shell/shell.spec.ts`, `src/styles.css`.
  - Deleted: `feat-screen-placeholder/screen-placeholder.ts` and its spec.
- **S4.** Created: `feat-stats/kpi-row.ts` and spec. Modified: `stats-view.ts`, `stats.ts`, `stats.css`.
- **S5.** Created: `feat-stats/stats-equity-chart.ts` and spec, `feat-stats/util/stats-chart-geometry.ts` and spec. Modified: `stats-view.ts`, `stats.ts`, `stats.css`.
- **S6.** Created: `feat-stats/calibration-plot.ts` and spec. Modified: `stats-chart-geometry.ts`, `stats-view.ts`, `stats.ts`, `stats.css`.
- **S7.**
  - Created: `feat-stats/attribution-table.ts` and spec, `src/styles/components/chip.css`.
  - Modified: `stats-view.ts`, `stats.ts`, `stats.css`, `src/styles/components/signals.css`, `src/styles.css`.
- **S8.**
  - Created: `feat-stats/losses-panel.ts`, `losses-list.ts` and specs.
  - Modified: `stats.service.ts`, `stats-view.ts`, `stats.ts`, `stats.css` and two store test edits.
- **S9.** Created: `feat-stats/compare-panel.ts` and spec. Modified: `stats.service.ts`, `stats-view.ts`, `stats.ts`, `stats.spec.ts`, `stats.css`.
- **S10.** Modified: `feat-bots/util/bot-draft.ts`, `feat-bots/editor/editor-weights.ts` and their specs.
- **S11.** Modified: `feat-trade/util/recommendation-view.ts`, `feat-trade/recommendation-card.ts` and their specs, `src/styles/components/trade.css`.
- **S12.** Modified: `e2e/src/support/{screens,market-watch,bots,trade}.ts`, `e2e/src/{a11y,viewport,shell,journey,signals-live,bots,bots-editor,trade}.spec.ts`.
- **S13.** Created: `e2e/src/support/stats.ts`, `e2e/src/stats.spec.ts`. Modified: `e2e/playwright.config.mts`.
- **S14.** `DESIGN.md`, `README.md` (the Stats route), `CLAUDE.md`.
- **XP1.** `data/stats.model.ts` and spec, `feat-stats/util/stats-view.ts` and spec.
- **Fix `b815cb4` (F1–F12, F14).** Files already listed: the store, the screen, the four panel components, the readers (`isUuid` in `versionsRequest`), the e2e real-service checks, `stats.css` and `DESIGN.md`.
- **Fold `aec5308`.** The e2e long-name test, `CLAUDE.md` and `DESIGN.md`.
- **PF1 `f7be11c`.** `feat-stats/losses-list.ts` and its spec (focus), and `e2e/src/stats.spec.ts` (F-PV1-2/3: the soft-disabled buttons are activated as a user can).
- **PF2 `a7e4e56`.**
  - Created: `pages/workspace/util/source-names.ts`, an OD-7 scope extension.
  - Modified: `feat-bots/util/bot-draft.ts` and spec, `feat-stats/{attribution-table.spec,calibration-plot,calibration-plot.spec,stats-equity-chart,stats-equity-chart.spec}.ts`, `feat-stats/util/stats-view.ts` and spec, `src/styles/components/stats.css`, `e2e/src/stats.spec.ts`, `e2e/src/support/market-watch.ts`, `DESIGN.md`, `CLAUDE.md` (14 files, +318/−94).
- **PF3 `5c68125`.** `src/styles/components/stats.css` (the compare grid's columns).
- **PV5 `9a88771`.** `DESIGN.md`: the "Statistics (slice 7)" Verification evidence entry.
- **Unchanged by design:** `feat-overview/` (including `equity-chart.ts` and `util/chart-geometry.ts`), the shared styles (`portfolio.css`, `metric-card.css`, `range-switch.css`, `section.css`, `table.css`, `button.css`, `tag.css`, `toast.css`, `zone.css`), `tokens.css`, `theme.css`, `icons.ts`, `package.json` and the lockfile. `feat-bots/data/bot-editor.service.ts` was planned as *to change* and did not change: the figure is drawn by `bot-draft.ts`.

**Not changed:** tidewatch-migrations (no schema change), tidewatch-bot, `documents/`, `tidewatch-specs` (inputs only) and `tidewatch-apis` (empty, not a Git repository).

## Test plan

### Commands (all local; CI runs `make ci` / lint-test-build)

- **Service:**
  - `make ci` (vet with and without the integration tag, the race suite, build);
  - `make test-integration TIDEWATCH_MIGRATIONS_DIR=/Users/maichinu/tidewatch/tidewatch-migrations` (throwaway containers);
  - `gofmt -l` empty.
  - Verification greps `--- PASS: <Name> (` in `go test -v` output and in `bin/integration-test.log`, and requires an `ok` line with no `--- SKIP`.
  - The fixture generators must reproduce their JSON byte for byte, importing only the Python standard library: `python3 internal/trading/testdata/stats/gen_arithmetic.py` and `gen_calibration.py`.
  - The committed SQL runs with `psql -v` (`bot_id`, `seq`, `from`, `to`, plus `now_equity`, `now_benchmark` and `usd_thb`).
- **Web:**
  - `pnpm nx test tidewatch-web`, `pnpm nx lint tidewatch-web`, `pnpm nx build tidewatch-web`, `pnpm nx run e2e:lint` and the e2e type check;
  - the literal-colour grep;
  - the zone-token grep `grep -rn -E "z-(green|blue|lblue|yellow|orange|red)" src/app/pages/workspace/feat-stats src/styles/components/stats.css`, which must return nothing;
  - `forge-setup-impeccable --project tidewatch-web --check`.
- **Playwright runs only on a preview.** Run `authed-setup`, then `public` + `authed` with `--no-deps --grep-invert @hook`. `journey` and `sign-out` are skipped, because sign-out ends the owner's sessions.

### Named acceptance tests (do not rename)

- **Service, unit:**
  - `TestStatsWindow_Rules`, `TestStatsArithmetic_Fixtures`, `TestStatsArithmetic_SqrtExact`;
  - `TestCalibration_Synthetic`, `TestCalibration_Bins`;
  - `TestAttribution_Net`, `TestAttribution_Dimensions`, `TestModelledCostRate`;
  - `TestPromotionCheck_Conditions`, `TestPromoteBot_VerdictReadsInSnapshot`;
  - `TestLossesCursor_KindAndBinding`;
  - the handler tests `TestStatsHandler_Query`, `TestStatsHandler_Losses_Query`, `TestStatsHandler_Compare_Query`, `TestDecisionsHandler_PostMortem_Body`, `TestBotsHandler_Promote`, `TestBotsHandler_Attribution_Additive`, `TestRecommendationHandler_Body`, `TestRecommendationHandler_FollowRecord`;
  - the contract and router tests `TestCodes_Contract`, `TestAllCodes_MatchContract`, `TestReason_ClosedSet`, `TestPromotionDetail_PublicDetails`, `TestAudit_StatsEvents`, `TestMetrics_StatsSeries`, `TestCSRF_PostMortem`, `TestCSRF_BotMutations`, `TestRouter_NoDecisionMutation`, `TestRouter_ForcedChangeGatesNewRoutes` (64).
- **Service, integration:**
  - `TestStats_MatchesSQL`, `TestStats_Window`, `TestStats_Calibration`, `TestStats_DefaultBot`, `TestStats_Compare`, `TestStats_ScopeAndNotFound`, `TestStatsLosses_Paging`, `TestCursor_Kinds`;
  - `TestPostMortem_Write`, `TestPostMortem_Refusals`, `TestDecisions_DirectSQLMutationFails`;
  - `TestPromote_Pass`, `TestPromote_Refused`, `TestPromote_Concurrent`, `TestPromote_PauseRace`;
  - `TestBots_Attribution_Compat` (at HEAD and at base `db281db`), `TestBots_Attribution_MatchesSQL`;
  - `TestRecommendation_FollowRecord`, `TestRecommendation_NoCreate`, `TestLogs_NoBotTextOrConfig`.
  - S4's mutation check: breaking two computations was caught by `TestStats_MatchesSQL`, then restored.
- **Service, added by S1 beyond the plan:** `TestAttribution_Scope` and `TestAttribution_VersionRows`.
- **Web, unit:** the specs of `stats.model`, `stats-api.service`, `stats.service`, `stats-url`, `stats-view`, `stats`, `stats-controls`, `kpi-row`, `stats-equity-chart`, `stats-chart-geometry`, `calibration-plot`, `attribution-table` (13 tests), `losses-panel`, `losses-list`, `compare-panel`, `bot-draft`, `editor-weights`, `recommendation-view` and `recommendation-card`.
- **Web, e2e (`stats.spec.ts`):**
  - "keeps its URL state", "switches period without losing the strip", "switches attribution dimension";
  - "opens the labelling list", "labels a loss";
  - "promotes a challenger", "shows why promotion is refused", "FR-ST-WEB-009 shows an error line in the panel when compare fails", "a refused default is never read again (N1)";
  - "draws every chart from classes in both themes", "reaches every control with the keyboard";
  - the axe and contrast matrices and the capture matrices;
  - `bots-editor.spec.ts`, `trade.spec.ts` and `a11y.spec.ts`, updated.

### Acceptance status (PRD §9; passed, failed, unverified and deferred stated separately)

| ID | P | Status | Evidence |
|---|---|---|---|
| FR-ST-SVC-001 | P0 | Verified | `TestStats_MatchesSQL` (S4, M3 re-check, FOLD1) |
| FR-ST-SVC-002 | P0 | Verified | `TestStatsWindow_Rules`, `TestStats_Window`, `TestStatsHandler_Query` |
| FR-ST-SVC-003 | P0 | Verified | `TestStatsArithmetic_Fixtures` (11 scenarios incl. `sub_rounding_dip`), generator reproducible, A1 recorded |
| FR-ST-SVC-004 | P0 | Verified | `TestCalibration_Synthetic` (ECE 0.0000 / 0.1500), `TestCalibration_Bins`, `TestStats_Calibration` |
| FR-ST-SVC-005 | P0 | Verified | `TestBots_Attribution_Compat` (HEAD and `db281db`), `TestBots_Attribution_MatchesSQL`, `TestAttribution_Net/Dimensions`, `TestModelledCostRate` |
| FR-ST-SVC-006 | P0 | Verified | `TestPostMortem_Write/Refusals`, `TestRouter_NoDecisionMutation`, `TestCSRF_PostMortem` |
| FR-ST-SVC-007 | P1 | Verified | `TestStatsLosses_Paging`, `TestCursor_Kinds`, `TestLossesCursor_KindAndBinding`, `TestStatsHandler_Losses_Query` |
| FR-ST-SVC-008 | P0 | Verified | `TestPromotionCheck_Conditions`, `TestStats_Compare` |
| FR-ST-SVC-009 | P0 | Verified | `TestPromote_Pass/Refused/Concurrent/PauseRace`, `TestPromoteBot_VerdictReadsInSnapshot` |
| FR-ST-SVC-010 | P1 | Verified | `TestRecommendation_FollowRecord/NoCreate/Follow`, `TestRecommendationHandler_Body/FollowRecord` |
| FR-ST-SVC-011 | P1 | Verified | `TestCodes_Contract`, `TestAllCodes_MatchContract`, `TestAudit_StatsEvents`, `TestMetrics_StatsSeries`, `TestRouter_ForcedChangeGatesNewRoutes` (64), README |
| FR-ST-SVC-012 | P1 | Verified | `TestStats_DefaultBot`, `TestStats_ScopeAndNotFound`, `TestLogs_NoBotTextOrConfig` |
| FR-ST-SVC-013 | P2 | **Timing verified; the index criterion failed as written** | `period=all`: p50 134 / p95 161 / max 206 ms; `30d`: p50 37 / max 40 ms; all < 500 ms, so the D10 trigger was not reached. The `EXPLAIN` expectation "`decisions_bot_ts_idx` range, no sequential scan" does not hold for `all` at the preview's skew (see Database). No index was added (A7). `evidence/preview/perf/`, `evidence/service/stats-explain.txt` |
| FR-ST-WEB-001 | P0 | Verified | unit (store, URL, screen); PV1c URL, fallback and empty titles |
| FR-ST-WEB-002 | P0 | Verified | unit (controls, store, versions reader); PV1c period and custom-range titles |
| FR-ST-WEB-003 | P0 | Verified | `kpi-row`/`stats-view` specs; PV2 `stats__kpis-*` (7/4/2 columns, notes, U+2212, ฿) |
| FR-ST-WEB-004 | P0 | Verified (**visual tooltip and pointer pick not captured**) | chart and geometry specs; PV1 keyboard point; PV2 drawdown in `--down`, violet benchmark, a single fresh axis date |
| FR-ST-WEB-005 | P0 | Verified | `calibration-plot` spec; PV2 `stats__calibration-*` (W2, W4 fixed) |
| FR-ST-WEB-006 | P0 | Verified | `attribution-table` spec; PV2 OD-7 names, 8 columns fit at ≥ 1251, region scroll at ≤ 1250 |
| FR-ST-WEB-007 | P0 | Verified | `losses-panel` spec; PV1c "opens the labelling list"; W3 one-label sentence |
| FR-ST-WEB-008 | P0 | Verified | `losses-list`/store/reader specs; PV1c three titles; E2E-003 |
| FR-ST-WEB-009 | P0 | Verified | `compare-panel`/store/screen specs; PV1c compare titles (after the F-PV1-2/3 test fixes); E2E-002 |
| FR-ST-WEB-010 | P0 | Verified | `bot-draft`/`editor-weights` specs; PV1c bots-editor 87/87; PV2 `bots__editor-net-*` (W5 fixed); E2E-004 |
| FR-ST-WEB-011 | P1 | Verified | recommendation specs; PV1c trade 190/190; PV2 `trade__follow-record-*` |
| FR-ST-WEB-012 | P0 | Verified | 160 state captures and 40 element captures at exact viewport widths; no page scroll (document, CDP and body checks); tables scroll in their regions; long-name capture after PF3 |
| FR-ST-WEB-013 | P0 | Verified | zone and colour greps; PV1c computed colours; no zone hue in captures |
| FR-ST-WEB-014 | P0 | Verified (**focus-ring visuals not captured**) | axe 0 violations and contrast ≥ 4.5:1 in 7 states × 2 themes at 1440; `a11y.spec` 22/22; keyboard reach passes after PF1 (it **failed** in PV1 as F-PV1-4) |
| FR-ST-WEB-015 | P1 | Verified | `DESIGN.md` (Stats pieces, OD-3…OD-7, "Stats words beyond PRD §4", the "Statistics (slice 7)" evidence entry, snapshot 165 sources, 0 drift); `forge-setup-impeccable --check` clean |
| FR-ST-E2E-001 | P0 | **Passed** | `evidence/preview/e2e-001/` |
| FR-ST-E2E-002 | P0 | **Passed** | `evidence/preview/e2e-002/` |
| FR-ST-E2E-003 | P1 | **Passed** | `evidence/preview/e2e-003/` |
| FR-ST-E2E-004 | P2 | **Passed** | `evidence/preview/e2e-004/` |
| FR-ST-DOC-001 | P1 | Verified | service README and `CLAUDE.md` (S9, FOLD1); web README, `DESIGN.md` and `CLAUDE.md` (S14, PF2, PV5); the wiki pages follow in this pass |
| FR-ST-DOC-002 | P2 | **Unverified: recorded deferral** | `tidewatch-apis` is empty and not a Git repository |

**Unverified in PV3, outside any single ID's pass:**
- focus-ring visuals;
- contrast at widths other than 1440;
- nine states whose contrast was not measured;
- VoiceOver and Safari reading of the `display: contents` compare-grid rows.

### Preview runs

**The run.**
- Run `stats-285d3631`, compose project `forge-0199b29a-stats-285d3631`, isolated with retain on the shared volume `forge-preview-0199b29a_tidewatch-pgdata`, migrated to K (goose `20261021082304`). 6/6 services were healthy and `/api/ready` was ok.
- **Revisions:** service `5ab46d3` (the PR head, equal to the merged code); web `cbdb17f`, refreshed to `f7be11c`, `a7e4e56` and `5c68125`; bot `a22e399` (main, unchanged); migrations `7b41800` (main).
- **Image check:** `GET /api/stats`, `/stats/compare` and `/stats/losses` answered 401 (registered and gated), against 404 for an unknown route. The web chunk contains "Compare bots".
- **Owner go-ahead (2026-10-27):** "Yes, run the preview verification matrix (PV1–PV5 and the SVC-013 timing), using a dedicated preview user and bot for the seeded data."
- **Method.** The owner's preview credentials were copied to `e2e/.auth` (mode 600) and never read or echoed. The run did `authed-setup`, then `public` + `authed` with `--no-deps --grep-invert @hook`; `journey` and `sign-out` were skipped.

**Playwright, in order:**
- **PV1 (web `cbdb17f`):** 1402 passed, 4 failed, 4 skipped, in 21.6 min. By spec: a11y 22/22, bots-editor 87, bots 391, chart 27, overview-portfolio 92, shell 9, signals 69, signals-live 13, trade 190, viewport 94, watchlist 1. stats had 255 passed, 2 timed out and 1 failed.
  - **F-PV1-1 (environment, still open).** `bots-live.spec.ts:598` "lists Me then Slack Water …" expects "2 bots · paper mode" and read "5 bots · paper mode". The shared retained database holds admin's slice-6 E2E bots (E2E A · none · BTC, E2E B · jev · ETH, E2E C · probation). The live spec assumes a fresh database. This is not a slice-7 defect, and no code changed for it.
  - **F-PV1-2 and F-PV1-3 (e2e test defects).** "shows why promotion is refused" and "disables Compare bots without a challenger" clicked soft-disabled (`aria-disabled`) buttons, which Playwright refuses. The product behaviour was correct. Fixed in PF1.
  - **F-PV1-4 (product a11y defect, FR-ST-WEB-014).** After *Label losses*, focus left the list's `h2`: two Tabs later it was on the rail's "Signals" link. The named region rendered only with rows. Fixed in PF1.
- **PV1b (`f7be11c`):** stats.spec 258/258.
- **PV1c (`a7e4e56`, full suite):** 1387 passed, 19 failed, 4 skipped, in 3.9 h. stats 258, trade 190, bots-editor 87, a11y 22, viewport 94, signals 69, bots 391 and chart 27 all passed. The failures:
  - market-watch: 7 timed out and 1 failed;
  - overview-portfolio: 10 timed out;
  - bots-live: 1 (F-PV1-1).
- **PV1d (`a7e4e56`):** market-watch + overview-portfolio re-run alone, 191/191 in 2.7 min. The PV1c timeouts were host slowness, not regressions.
- **PV1e (`5c68125`):** stats.spec 258/258. The long-name capture was viewed: the champion's name wraps in its column, and the labels sit at normal width.
- **Final at `a7e4e56`/`5c68125`:** every spec passes except the one `bots-live.spec.ts` environment failure.
  - Skipped live gates: market-watch-live 2, paper-orders 1, bots-live pause 1.
  - The full suite was not re-run at `5c68125` (PF3 is CSS only) or at `9a88771` (PV5 is docs only).

**The other preview checks:**
- **PV2.** Rendered design review on 230+ captures. Round 1 CHANGES REQUESTED, then PF1 and PF2; the re-check at `a7e4e56` APPROVED; W8 was fixed in PF3. Signals captures were 182/182 and Market watch 82/82 identical to the slice-6 baseline; Overview was unaffected.
- **PV3.** See the table above.
- **PV5.** The `DESIGN.md` evidence entry; `impeccable --check` clean; S14 13/13; snapshot 165 entries, 0 drift.

### The E2E checks and SVC-013 (2026-10-27, 02:26–02:57Z, PV4, service `5ab46d3`)

**Seeding.**
- **The user.** A dedicated admin user, `pv4-stats` (`01a17b2d-eca6-7a41-8422-2b169356ee91`), was inserted by SQL. Its password was set with `tidewatch-service admin set-password --username pv4-stats` and the forced change was completed; the passwords were never printed (R2-W1).
- **The bots.** Created through `POST /bots`, so the v1 config, hash, account and benchmark are the service's own, then backdated by SQL.
- **The data.** Seed scripts `seed/00_user.sql`, `10_perf.sql` (deterministic generator, seed 20261027), `15_fix_creation_marks.sql`, `16_rescale_challenger.sql`, `20_e2e002_phase1.sql` and `21_e2e002_phase2.sql`, each hash-recorded in `evidence/preview/seeded.md`.

**Results.**
- **FR-ST-SVC-013.** PV4 Perf: 92 `day_end` marks and 10,000 decisions. 20 timed runs after one warm-up through the gateway:
  - `period=all`: min 110.6, p50 133.5, p95 161.1, max 206.0 ms;
  - `30d`: min 34.7, p50 37.2, p95 38.9, max 40.1 ms.
- **FR-ST-E2E-001: passed.**
  - Every KPI, note, ECE line, post-mortem panel figure and the four attribution tables on screen equalled `test/sql/stats_*.sql` run against the preview database. The SQL results were formatted independently.
  - Three windows: custom 10 Aug–15 Oct, `all` and `30d`. Each scored 22/22 on screen and 34/34 raw.
  - The first captures ran while the bot's outcome back-fill was still filling seeded ungraded rows. They are kept in `e2e-001/superseded-backfill-in-progress/`. The final captures are bracketed by an unchanged data fingerprint.
- **FR-ST-E2E-002: passed.**
  - **Setup.** PV4 Champion was promoted by API at 02:34:52 (first-champion branch, 61 days; audit event 114).
  - **The refusal.** PV4 Challenger with an 11-day shared window was refused: `409 promotion_refused ["window_too_short"]`. The screen worded it, the button was `aria-disabled`, and a forced press sent no POST.
  - **The promotion.** After `21_e2e002_phase2.sql` moved the Challenger's v1 to a 46-day shared window, it was promoted **on screen** at 02:42:57, with the toast and the *Champion* tag on Bots. `GET /recommendation` followed the new champion.
  - **SQL.** One champion; `promoted` (`previous_champion` = Champion) and `demoted` (`succeeded_by` = Challenger); audit event 121.
  - **Deviation.** The engine's guard paused the Challenger twice (02:35:29, 02:37:59). Its seeded ledger ended at 1,080,000 while the engine values a fill-less account at its starting capital, which read as a −7.4 % day. That is correct product behaviour on inconsistent seed data. `16_rescale_challenger.sql` scaled the ledger by 1,000,000/1,080,000, leaving the ratios unchanged. The first refused capture, showing "Paused", is kept in `e2e-002/first-attempt-guard-paused/`.
- **FR-ST-E2E-003: passed.**
  - *Regime shift* was saved on screen (200) on decision `66458d2d-486f-48b3-b33d-09087b191355`. The row reads `confirmed_by_user true`, with audit event 123.
  - A second save got `409 post_mortem_frozen` and the toast; a direct PUT got 409 too. The counts moved by 1.
- **FR-ST-E2E-004: passed.** The editor's net figure equalled the Stats Source row character for character for all 10 sources, and the API answers agreed. It ran at web `cbdb17f`; OD-7 changed the source names afterwards, but not the figures.

### Defects found on the preview and their fixes

- **PF1 `f7be11c`:**
  - F-PV1-4 (focus);
  - F-PV1-2/3 (tests).
- **PF2 `a7e4e56`:**
  - **B2 / OD-7:** indistinguishable source names, now shared with the editor;
  - **W1:** no space above the labelling list;
  - **W2:** the hidden calibration table pushed the page 355px wide at 1100 and 390, and the page-overflow check gained a body measurement;
  - **W3:** the few-graded summary named a zero-count second label; it now has a one-label sentence;
  - **W4:** panel titles and the ECE line wrapped awkwardly;
  - **W5:** the editor note broke between "n" and its count;
  - **W6:** the attribution table was cut at its region edge on desktop; all eight columns now fit at ≥ 1251px;
  - **W7:** long names were only partly verified; the long-name capture was saved;
  - **Advisories applied:** `align-self: start` on *Why trades lost*, and a single "25 Oct" on the fresh chart's axis.
- **PF3 `5c68125`:** W8 (the compare grid's columns).
- **Found in review, not on the preview** (all fixed before merge):
  - service: M-1 and W1;
  - web: F1–F12 and F14.

### Preview database footprint (shared retained volume `forge-preview-0199b29a_tidewatch-pgdata`)

This persists: `decisions`, `events` and `bot_version_events` are append-only.

**Bots of `pv4-stats`:**

| Bot | Id | Template / tier | Final state |
|---|---|---|---|
| PV4 Perf | `01a17b2e-84b2-7b0b-a477-8fac4024c6b4` | news_drift / jev, v1 `ef8d1f8c…` | paused |
| PV4 Champion | `01a17b2e-855a-7e55-afcb-0b5c2b9983cd` | blank / none, v1 `28cfecd1…` | paused, `champion = false` (promoted, then demoted) |
| PV4 Challenger | `01a17b2e-85a3-7a84-aeba-c30cba628023` | blank / none, v1 `28cfecd1…` | paused, **`champion = true`** |
| Me | `01a17b2e-846f-7ea5-8dff-e5fc2cbe4b41` | manual | running (created by `EnsureBots` on the first `POST /bots`, not asked for) |
| Slack Water | `01a17b2e-8473-74b2-b573-519baac8d761` | zone_transitions | paused (created by `EnsureBots`) |

**Rows inserted:**
- **PV4 Perf:**
  - 10,000 decisions: 2,500 propose, 3,300 buy, 500 add, 800 sell, 300 trim, 600 close, 1,800 skip (600 of them `["observing"]`) and 200 protect;
  - 57 decisions carried a `post_mortem` at insert (44 user, 9 model confirmed, 4 model proposed), and 58 after E2E-003;
  - 2,500 candidates (expired, ttl);
  - 400 closed positions;
  - 1,288 `bot_runs` (184 scout, 1,104 manager);
  - 93 ledger rows.
- **Champion:** 12 decisions, 62 ledger rows.
- **Challenger:** 12 decisions, 47 ledger rows.
- **The rest:** one creation fill mark per bot from the service, the user, and a default 8-item watchlist.

**Written by the product during the checks:**
- `bot_version_events`:
  - `created` + `probation_skipped` × 3;
  - `promoted` × 2 and `demoted` × 1;
  - `guard_paused` × 2 on the Challenger.
- `events`: `bot_created` × 3, `bot_status_changed` × 12, `bot_promoted` × 2 (114, 121), `post_mortem_labelled` × 1 (123), and the login and password events.
- The outcome back-fill rewrote allowed columns on PV4 Perf's rows: `r_1h` and `outcomes_detail` on 9,776 rows, and `r_1d`/`r_5d` on most of the 246 rows seeded ungraded.
  - It computed them from the preview's real bars against the seeded `px_at_decision`, hence some large best and worst figures.
  - It skips the 224 `USDTHB@oanda-demo` rows.
  - 23 recent rows stay ungraded until their horizon passes, so PV4 Perf's `all` and `30d` figures can still move.

**Not touched:** `admin` still has 5 bots and no champion. No schema, index or container changed. Two live sessions of `pv4-stats` remain (one API, one browser). No `pv4-stats` bot ever placed an order. All its auto bots were left paused, so a preview started on this volume does not run them.

### Manual reproduction

1. **The screen and the SQL.** Open `/stats?bot={id}&period=all`. Run `psql -v bot_id=… -v seq=… -v from=… -v to=… -v now_equity=… -v now_benchmark=… -v usd_thb=… -f test/sql/stats_kpis.sql`, with `from` and `to` taken from the answer's `window`. Each KPI should equal the screen once S15's formatting is applied.
2. **Calibration states.** A tier-`none` version reads "This version states no probabilities…". A version with fewer than 30 graded `propose` rows reads "Not graded yet…" with its count.
3. **Label a loss.** Choose *Label losses*, pick a reason, then *Save*. The row turns into "Labelled by you · {word}" and *Frozen*. `SELECT post_mortem FROM decisions WHERE decision_id = …` holds the four keys. Saving again gives the toast "That decision was already labelled.".
4. **Compare and promote.** Open *Compare bots* with a challenger whose shared window is under 30 days. The verdict reads "Shared window is {n} days; the check needs at least 30" and *Promote* is `aria-disabled`. With ≥ 30 days and the other conditions met, *Promote* succeeds:
   - `bots.champion` flips;
   - `bot_version_events` gains `promoted` (and `demoted`);
   - `events` gains `bot_promoted`;
   - Bots shows the *Champion* tag.
5. **The editor and Stats agree.** On a single-version bot, the editor's "avg 5 d, net · n {n}" figure equals the Stats Source row under `period=all`.
6. **Trade.** Under the recommendation card, the follow-record sentence reads either its averages or "Not enough graded decisions yet…".
7. **Metrics.** After a read, `/metrics` shows `stats_reads_total{kind="stats"}` incremented and `stats_read_seconds` observed.

## Open questions

**Failed as written, or unverified, at merge (the owner merged knowing this):**
- **FR-ST-SVC-013's index criterion.** `period=all` sequence-scans `decisions` on the preview, because of the 99.7 % single-bot skew. The 30d window and the losses read use `decisions_bot_ts_idx`. A7 says the owner is asked before any index is proposed. The record shows no index proposal and no owner answer on one.
- **Not captured visually:**
  - the equity chart's tooltip and pointer pick (WEB-004);
  - focus-ring visuals (WEB-014).
- **Not measured:**
  - contrast at widths other than 1440;
  - nine states' contrast;
  - VoiceOver/Safari on the `display: contents` compare rows.
- **FR-ST-DOC-002:** the OpenAPI and Bruno collection, deferred because `tidewatch-apis` is not a Git repository.
- **`bots-live.spec.ts` (F-PV1-1).** It fails on any shared preview database that holds more than `Me` and Slack Water. It was not changed in this build.
- **No real calibration data.** No graded stated `p` existed anywhere at build time (A4). The calibration plot, the ECE KPI and `calibration_no_worse` were exercised only on synthetic fixtures and seeded data.

**Rollout and production:**
- **First production champion.** Not made. It is the owner's action. A candidate must be an auto bot that is `running`, with probation over and its own window of ≥ 30 days (first-champion branch).
- **Recovery.** Revert the merge commit on `main`; that redeploys the previous image, and there is no schema to roll back.
  - A champion flag set by a promotion stays in `bots.champion`. Clear it by SQL only on the owner's instruction.
  - The web's strict readers refuse pre-slice-7 bodies, so the web must never run ahead of the service. The merge order was service first, then web only after the service deploy.
- **Monitoring.** Watch `stats_read_seconds{kind}` against the 500 ms D10 trigger, and `stats_reads_total{kind}`.

**Follow-ups (`state.followUps`):**
- **FU-1 (service).** A NaN or Inf `r_5d` or `px_at_decision` now makes the attribution and stats reads answer 500 (`ErrAttributionValue`/`ErrStatsValue`). Slice 6 answered 200 with "NaN". Confirm the bot cannot write non-finite values, or count such rows as ungraded.
- **FU-2 (service).** Bots-scope attribution is now aggregated in Go, so rows cross the wire on each request. Watch it beside the D10 `attribution_snapshots` trigger (500 ms or 50,000 decisions).
- **FU-3 (web).** Graduate `TIER_WORDS`, `TONE_CLASS`, `BOT_TRIGGER_WORDS`, `LoadMoreOutcome` and `number-format` to `pages/workspace/util/`, and keep one shared `isUuid` (two exported copies exist, in `bots.model.ts` and `stats.model.ts`).
- **FU-4 (web).** Add a `PageHeader` `focusHeading()` API instead of `tabindex` from outside. Have the screen raise toasts from outcomes: `compare-panel` and `losses-list` emit after `await`, on a possibly destroyed output.
- **FU-5 (web).**
  - The UX of the 366-day custom span.
  - Optionally, write `bot` into the URL before promoting.
  - F13: a neutral disabled title when every challenger was refused this session (the current title, "Create a second auto bot to compare", is then inaccurate).
- **FU-6 (service).** Promote holds one pool connection and the advisory lock while it acquires a second for the snapshot. It fails closed through `queryTimeout`. Optional hardening: begin the read-only transaction before `InLockedTx` and run its first statement after the locks, or document this in `CLAUDE.md`.

**Other recorded residuals and notes:**
- **Champion without a current version.** It answers 500 on compare and promote (L-1). It is unreachable, because slice 6 never leaves a bot without v1.
- **Cost.** `cost_usd` undercounts a crashed wake (A5), and cost is per bot only through `bot_runs`; `model_calls` has no `bot_id`.
- **A2's omissions.** The modelled cost omits the US sell-side per-unit fee, and VAT applies to commission only.
- **Accepted web deviations:**
  - `57.00%` against the mockup's `57%`;
  - HTML axis labels over the SVG;
  - the dropped mockup panel-head note;
  - `.pm-bar` instead of `.bar`;
  - the new `.panel-status`;
  - copy beyond PRD §4, recorded in `DESIGN.md` "Stats words beyond PRD §4":
    - the attribution cost note;
    - the empty labelling list sentence;
    - the OD-6 headings;
    - "· champion" on the compare option;
    - the transient "Calibration error is worse" / "Still observing" verdict lines until the re-read;
    - the reused Decision record wording, including "Couldn't load more decisions. Try again.".
- **PV2 advisories left as they are:**
  - the first-champion verdict "Shared window 92 days…" under "Over its own window" (owner's wording call);
  - the toast covers *Champion* at 390 (shared toast placement);
  - the compare window note leaves "days" alone at 390;
  - the PRD wording "0.00% · 0 days to recover" and "Win rate 0.00% · no losses yet" on a fresh version.
- **The e2e mock's `seriesInstants` fallback** differs from contracts §2.3 (see "Playwright").
- **`prettier --check`** fails on the base `DESIGN.md`, `README.md` and `CLAUDE.md`. They were not reformatted, by the project's scope rule.
- **The S10/S11 engineer's loading gap.** That engineer did not open `contracts.md`, `CLAUDE.md` or `DESIGN.md`. The checks passed and the reviewers covered conventions.
- **Billet was unavailable.** `POST /billets` answered HTTP 500 twice on 2026-10-26, so every project has `stepBillets []`.
- **`documents/` drift for the owner** (never edited, D17):
  - `07-statistics.md` lists `attribution_snapshots` and a "generated reading" (now template text, PD6);
  - `02-architecture.md` §11 lists `post_mortems` and `attribution_snapshots` tables (post-mortems live in `decisions.post_mortem`);
  - the approved mockup shades drawdown with `--z-red` (D13 uses `--down`).

**Deferred by design (intent):**
- factor models, regression dashboards and PDF reports;
- the model-proposed post-mortem labeller (it writes `labelled_by: "model", confirmed_by_user: false` into the same shape), recalibration maps, Thompson weights, the meta-model and the extraction-error export (slice 8);
- live mode for the champion only (slice 9);
- account sources (slice 10);
- the champion stance on the Chart, the Tide brief and an Overview recommendation card (the D12 follow-on spec);
- `attribution_snapshots` until its trigger;
- `me` in the Stats selector;
- a counterfactual Trade sentence.

## Cross-cutting links

The build prompt names a new `statistics` overview page and a `stats-read-api` page for this slice. It also names updates to the pages below marked "(build prompt)".
- [[decision-record]] (build prompt): `post_mortem` now has its first writer (`PUT /decisions/{decision_id}/post-mortem`), the one admitted decision mutation. The losses definition and horizon mapping read `r_1d`/`r_5d`/`r_20d` and the candidate horizon. `TestRouter_NoDecisionMutation` admits one route.
- [[bot-versions-and-runs]] (build prompt): the version window; `bot_version_events` `promoted`/`demoted` (first writer); `bots.champion` (first writer); the reviewed `:bot_id` routes at twenty; the gated count at 64; `GET /bots/{bot_id}/versions` gains its first web reader.
- [[bots-engine]]: `bot_runs.counts.cost_usd`, the `propose` decision's `model.p`, the candidate horizon and the guard pause the E2E seeding met. The engine was unchanged.
- [[bots]]: the slice-6 attribution route, now additive, and the editor's net figure; the *Champion* tag now has a writer; `recommendations.follow = "champion"` now resolves to a promoted bot.
- [[paper-trading]] (build prompt): A1, so `positions.realized_thb` is already net of both fees; the now point reuses `portfolioAt`; the `REPEATABLE READ READ ONLY` snapshot pattern.
- [[model-routes-and-spend]] (build prompt): cost of decisions from `bot_runs.counts.cost_usd` at the C6 USD/THB rate; no `bot_id` on `model_calls`.
- [[design-system-decisions]] (build prompt): the drawdown exception (`--down` through `stats.css`); `.chip` graduating to `chip.css`; `.stats-screen` scoping; OD-5 heading levels; OD-7 shared `SOURCE_NAMES`; the busy-button copy; no zone hue on Stats.
- [[simulation-engine]]: ledger `day_end` marks, the equal-weight benchmark and C5 fill arithmetic behind the KPIs.
- [[signal-cited-orders]] and [[user-settings]]: `followed_recommendation` feeding `follow_record`; the `recommendations.follow` setting reading the champion flag.
- [[source-registry-and-ingest]] and [[signals-read-api]]: the `sources` rows (publisher, tier, `GET /sources` order) behind the Source dimension.
- [[instrument-master]]: `asset_class` and calendars behind the asset-class dimension; `venue_rules` behind the modelled cost rate.
- [[elliott-regime-labeller]]: the `market_state.regime` trend and volatility words behind the regime dimension.
- [[signals-page]]: the URL-state pattern (`?day=`) that Stats' `?bot=&v=&period=` follows, and the `.chip` it now shares.
- [[charting]]: SE-17's keyboard pattern on the new equity chart; Stats uses no chart library.
- [[centralized-migrations]]: no migration; `RequiredSchemaVersion` stays J; migrations head K.
- [[auth-model]] and [[request-protection]]: the 64 gated routes, CSRF on the PUT and the POST, owner-scoped 404s.
- [[forge-preview-gateway]]: the isolated retained preview, the dedicated `pv4-stats` user and the credentials-copy Playwright method.
