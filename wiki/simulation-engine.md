# Simulation engine and decision record (Slice 2)

**Summary**: Slice 2 added paper trading. Each user gets a lazily created `me` bot with a ฿1,000,000 THB paper account and a new Trade screen for market, limit and manual (MTS) orders. The service validates each order and writes it, plus exactly one append-only decision row, in one transaction. A new bot runner, `sim`, fills orders on stored bars, marks the ledger, values an equal-weight benchmark and back-fills each decision's outcome columns. Overview gained a portfolio hero and four KPI cards above Market watch. The four code PRs merged on 2026-10-08. Preview verification was still running when the source was written: FR-SIM-E2E-003 passed, and E2E-001, 002, 004 and 005 were not finished. Slice 2b (2026-10-09) added a second, automatic bot beside `me`; see [[zone-transition-bot]].

**Sources**: `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md` (later status and slice-2b changes only); `raw/2026-10-29-accounts-roles.md` (the gate's role only)

**Last updated**: 2026-10-29

---

## Stage, stated precisely

This is the status recorded in `state.json`, last updated 2026-10-08T17:42Z. Nothing newer is in the raw source (source: raw/2026-10-08-simulation-engine.md §Concept, Stage, stated precisely).

| Stage | Status |
|---|---|
| Implemented | All planned steps are done: service MIG1–MIG2 and S1–S8, bot S1–S10, web S1–S8. Fix rounds after review: service 2, bot 3, web 2, plus one web follow-up commit. |
| Verified locally | Every step's contract commands exited 0. The shared arithmetic fixture is byte-identical in the service and the bot (sha256 `ff3564c8…`). |
| Reviewed | Service: code and security APPROVED in round 2. Bot: code APPROVED in round 3, security in round 4. Web: angular, tailwind, security, code and design APPROVED, with design approved in round 4 on rendered evidence. |
| Merged | Yes, by the owner on 2026-10-08 between 17:41:28Z and 17:42:07Z (see the merge record below). |
| Verified on a preview | **Partly.** The isolated Forge preview runs exactly the merged heads on a database reset at 2026-10-08T14:57Z (OWNER-4). See [Preview acceptance](#preview-acceptance). |
| Running on the owner's own stack | **Not recorded.** The isolated Forge preview is the only running instance on record. Its volumes are retained, and CLEANUP waits until the scheduled task sets `verificationComplete` (ORCH-34). |

## Merge record

| Repo | PR | Reviewed head | Merge commit |
|---|---|---|---|
| tidewatch-migrations | #4 | `ffe6c27` | `6531508` |
| tidewatch-service | #4 | `8770fde` | `857d420` |
| tidewatch-bot | #4 | `c37d89a` | `6902f4e` |
| tidewatch-web | #5 | `a4c808b` | `cfed50e` |

The owner merged them by hand in this order. The orchestrator's own `gh pr merge` was denied by the session's auto-mode classifier (OWNER-6), and the orchestrator did not work around the denial. Diff sizes: migrations 4 files (+1,146 / −33), service 90 (+26,849 / −122), bot 65 (+24,060 / −111), web 79 (+18,756 / −133) (source: raw/2026-10-08-simulation-engine.md §Concept, Stage; §Files touched).

## Why the slice exists

Before this slice, nothing could be traded or recorded. The paper account is where every later strategy has to prove itself. The decision record is the dataset that later slices train on and are graded against: Signals (slice 3), Bots (slice 6), Stats (slice 7) and post-mortems (slice 8). Both were built before any signal exists, so they are designed around orders and outcomes rather than around one bot's needs (source: raw/2026-10-08-simulation-engine.md §Concept, Problem).

## What each project gained

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-migrations` | Migration E (`20261008050550`): nine tables, the `decisions` triggers, the `ledger` hypertable and six `venue_rules` seeds | [[centralized-migrations]], [[paper-trading]], [[decision-record]] |
| `tidewatch-service` | Seven gated trading routes, the intake checks, exact arithmetic (`internal/trading`), nine new error codes, three audit events, trading metrics and the 20-order verification driver | [[paper-trading]], [[decision-record]] |
| `tidewatch-bot` | `packages/sim` and the `sim` runner (the tenth `COLLECTOR_NAMES` entry), which runs fills, marks, outcomes and re-marks | [[paper-trading]], [[market-data-worker]] |
| `tidewatch-web` | The Trade screen (ticket, open orders, positions, decision record, recommendation placeholder), and on Overview the portfolio hero, the equity chart and the KPI strip | [[design-system-decisions]] |

(source: raw/2026-10-08-simulation-engine.md, summary block; §Database; §API; §Components)

## Owner decisions

The product decisions are SIM1–SIM13, confirmed 2026-10-08. The mechanics are on [[paper-trading]] and the outcome rules are on [[decision-record]]. Build-time owner decisions (source: raw/2026-10-08-simulation-engine.md §Concept, OWNER decisions during the build):

- **OWNER-1 (assumptions A1 and A2).** The orchestrator recommended these values and they were adopted. The owner may still veto them.
  - `webull/set` `commission_pct` is **0.00047**, replacing the PRD's 0.0015. It is the sum of Webull TH 0.04%, SET 0.005%, TSD 0.001% and SEC 0.001%, all ex-VAT, with 7% VAT on top. Source: webull.co.th, read 2026-10-08.
  - `tfex/tfex` `initial_margin_thb` is **137,550.00**, replacing the PRD's 150,000. It is 1.75 × the TCH GO margin of ฿78,600 (effective 11 June 2026). The value changes monthly, and each change needs a data migration.
- **OWNER-2.** Lanes were gated by dependency, with smelt bundling.
- **OWNER-3.** The preview uses an isolated database, and its volumes are retained after merge.
- **OWNER-4.** After the ORCH-31/33 bot fix, the preview database was reset and the 20-order run restarted. Only this run's volume was deleted. Attempt-1 evidence was archived.
- **OWNER-5 / OWNER-6.** The scheduled task `tidewatch-slice2-verify-merge` (cron `30 10,15,21 * * 1-5`, Bangkok) was first authorised to merge after full verification. The classifier denied the merge, so the task now only verifies and reports. The owner merged the four PRs by hand.

Rejected alternatives:
- Putting everything in the bot: the UI would wait on a worker for a fill the user typed in.
- Putting everything in the service: it would duplicate the bar pipeline.
- Filling daily-only orders at the last close: this is anachronistic.
- A notional limit for futures: one GO contract (about ฿1.2M) is larger than the account.
- An empty "Tide intelligence" panel: this was judged dishonest.

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design)

## API surface

All seven routes are on tidewatch-service. They mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles, 2026-10-29; see [[accounts-and-roles]]). CSRF covers the four POSTs (see [[auth-model]] and [[request-protection]]). Routes have no `/api` prefix and take no `bot_id`. The `me` bot comes from the session, so another user's order returns `404 not_found`. The gated-route count test now expects 26 routes: 23 production routes and 3 test probes (source: raw/2026-10-08-simulation-engine.md §API).

| Route | Purpose |
|---|---|
| `GET /trade` | Account, positions, open orders and tradable instruments |
| `POST /orders` | Place an order. Returns 201, or 200 on an idempotent replay of `(bot_id, client_order_id)` |
| `POST /orders/estimate` | Runs the same `check()` read-only, so it cannot disagree with a placement |
| `POST /orders/{order_id}/cancel` | Returns 200 `Order`, 404 `not_found` or 409 `order_not_pending` |
| `GET /decisions` | Keyset-paged decision list (see [[decision-record]]) |
| `POST /decisions/skip` | Records a `skip` decision. No UI calls it in this slice |
| `GET /portfolio` | `period` is `1w`, `1m` or `3m`. Returns the equity and benchmark series, returns and KPIs |

New error codes, appended to `AllCodes()`: `instrument_not_tradable`, `manual_fill_required`, `venue_closed`, `price_unavailable`, `insufficient_position`, `insufficient_cash`, `position_limit`, `exposure_limit` (all 422) and `order_not_pending` (409). New 400 reasons: `lot_size`, `tick_size`, `manual_fill_not_allowed` and `unknown_field`. The envelope is still `{error, code, requestID}` with an optional `details` (source: raw/2026-10-08-simulation-engine.md §API, New error codes). The intake order and the wire formats are on [[paper-trading]].

Audit events: `order_placed`, `order_cancelled` and `decision_skipped` (source: raw/2026-10-08-simulation-engine.md §API, Audit events).

## Web: Trade and Overview

- **Trade** (`feat-trade/`) replaces the slice-0 placeholder.
  - Layout: a 300px ticket column beside the content. It becomes one column at ≤ 1080 and stacks at ≤ 600.
  - The *Manual mode* tag sits in the header.
  - `TradeService` polls `GET /trade` every 10 s while the screen is open.
  - The order ticket debounces the estimate by 300 ms and gates it with a fingerprint. It picks refusal copy by `code` and reuses one `client_order_id` UUID across retries.
  - The other panels are open orders with a sticky *Cancel* column, a positions table updated in place from the existing `/ws` stream, and the decision record with *Load more*.
  - A recommendation placeholder reads "No recommendation yet…" and is tagged *Arrives with bots*.
- **Overview** (SIM10): the portfolio hero, then the KPI strip (SIM9: Today's return, Max drawdown, Open positions, Decisions), then the unchanged Market watch (see [[market-data]]).
  - The hero shows equity, a period-return pill and a `1W/1M/3M` range switch.
  - `app-equity-chart` is an inline SVG with `role="img"` and a tooltip driven by the arrow keys. Equity is drawn in `--brand` and the benchmark in `--violet` at a named opacity.
- Whole-baht display truncates toward zero (ORCH-19), so ฿1,018,934.52 shows as ฿1,018,934.

New tokens and styles are on [[design-system-decisions]] (source: raw/2026-10-08-simulation-engine.md §Components).

## Test plan and acceptance

There is no CI (D4). Every command runs locally.

| Project | Commands |
|---|---|
| Migrations | `make migrate-validate`, `make check-disposable-db` (PASS 848/0) |
| Service | `make ci`, `make test-integration` |
| Bot | `pnpm nx run-many -t lint test typecheck build`, `scripts/sql-integration.sh` |
| Web | `pnpm nx run-many -t lint test build` (about 1,835 unit tests at the last fix round). Mocked Chromium Playwright: 170/170 at `a4c808b` |

The named acceptance tests are pinned and must not be renamed. Examples: `TestOrders_Cancel_RacesFill` (22 rounds, one winner, no deadlock), `TestPortfolio_MatchesSQL`, `TestDecisions_DirectSQLMutationFails`, and the bot's `shared-fixture.spec.ts`. These IDs were verified by step contracts and reviews before merge: FR-SIM-MIG-001…003, SVC-001…013, BOT-001…009, WEB-001…009 and DOC-001. WEB-001/006/007/009 have rendered evidence from a mocked API: axe 0 across 16 runs, minimum contrast 4.67, and no horizontal scroll at five widths (source: raw/2026-10-08-simulation-engine.md §Test plan).

### Preview acceptance

These results are as recorded on 2026-10-08. The preview uses an isolated database reset at 2026-10-08T14:57Z and runs the merged heads.

| ID | Status | Detail |
|---|---|---|
| FR-SIM-E2E-001 | **In progress** | 20-order run on a fresh account. o01, o02 and o09 filled. o03 (PTT.BK) was refused with `venue_closed`, `next_open_at` 2026-10-09T03:00Z, and the other 16 rows wait behind it in sheet order. Next windows: SET on Fri 2026-10-09 (o03 and the rows behind it, including the MTS manual fills o07/o19), then Mon 2026-10-12 (o17). The PTT.BK chain spans about 4 SET trading days. |
| FR-SIM-E2E-002 | **Unverified (partial pass)** | 44/44 checks pass. No late or backdated fill occurred, so the ORCH-31/33 re-mark path was not exercised on the preview. Bot specs cover it. Re-run after the MTS fills with decimal equality (FU-12). |
| FR-SIM-E2E-003 | **Passed** | The 1w/1m/3m series equal the committed SQL. The benchmark is exact at the initial and 16:00 hour marks. Fill-mark benchmarks are only indicative. |
| FR-SIM-E2E-004 | **Partly passed** | Five refusals passed, with nothing written. Still unverified: US outside session, BTC/THB at 03:00 Bangkok, TFEX outside hours, and the driver's manual fills. |
| FR-SIM-E2E-005 | **Pending** | Needs `r_1h` / `r_1d` at +1 h and +1 session, then a second sweep that changes nothing. |
| FR-SIM-WEB-010 | **In progress** | `DESIGN.md` refresh (see [[design-system-decisions]]) |
| FR-SIM-DOC-002 | **Deferred** | `tidewatch-apis` is not a git repository (ORCH-3) |

The scheduled task `tidewatch-slice2-verify-merge` re-runs the driver and checkers in the next market windows. It only verifies and reports. It never merges and never cleans up (source: raw/2026-10-08-simulation-engine.md §Test plan, Acceptance status).

**Later status, as recorded by slice 2b (assumption A4).** At slice-2b plan time (2026-10-09), the slice-2 preview was recorded as 37/42, with E2E-001, 002 and 005 unverified, E2E-004 partial and no open fill defect. This differs from the 2026-10-08 table above (E2E-001 was then "in progress" and E2E-002 a "partial pass"). The 2b source does not give per-ID detail, so the table above is left as recorded (source: raw/2026-10-09-zone-transition-bot.md §Test plan, Assumption outcomes A4).

**Slice-2 test defects found by slice 2b (ORCH-13 / 13a).** The full Playwright suite on the fresh 2b preview database hit two latent defects in `e2e/src/paper-orders.spec.ts`. Both fixes are test-only, went into web PR #7 outside the plan's file list, and were delta-reviewed.
- ORCH-13: the regex `/^1,000$/` could never match the Open orders Limit cell (" 1,000 "). It is now `/^\s*1,000\s*$/`.
- ORCH-13a: `FILL_WITHIN_MS` rose from 120 s to 150 s, because it measures from placement to the UI showing the fill, which adds up to one 10 s screen refresh. On the preview a fill took about 110 s. The product's 2-minute claim is now measured in SQL instead (64.6 s and 113.5 s on the 2b preview). Under the next-bar rule a fill can take slightly over 2 minutes in the worst case; this is a slice-2 follow-up.

(source: raw/2026-10-09-zone-transition-bot.md §Concept, ORCH-13 and ORCH-13a; §Test plan, Other preview results; §Open questions, Slice 2 carry-overs)

Until E2E-001, 002, 004 and 005 finish, these paths have test evidence but no preview evidence:
- the futures open/close chain;
- the MTS manual fills and the bot's rewrite of their marks;
- limit fills on SET;
- BTC/THB fills at 03:00;
- outcome back-fill at real offsets.

(source: raw/2026-10-08-simulation-engine.md §Open questions)

**Manual reproduction.** Run `verification/sim-20-orders.sh` (tidewatch-service) on a fresh account only. It resumes from its `state.json` in each market window. Then run `verification/sim-20-fills.sql` with `psql -q`, then the script once more with `-fills` to compare the stored fills with `GET /trade`. Exit code 3 means the comparison failed. The driver reads the session cookie only from a file and never prints it (source: raw/2026-10-08-simulation-engine.md §Test plan, Manual reproduction).

## Open items

- **Follow-ups FU-1…FU-16.** The full list is in the source. The main ones:
  - FU-2: tighten the `venue_rules` CHECK.
  - FU-4: web refusal copy when `details` is missing.
  - FU-7: pin the 5m bar end.
  - FU-9: refuse backdated manual fills dated before the position opened.
  - FU-10: the strict JSON decoder accepts case-insensitive and duplicate keys.
  - FU-11: `EquityPath` reads the whole ledger.
  - FU-12: write the `fx` text as stored.
  - FU-15: re-mark scan indexes.
  - FU-16: add a dedicated re-mark metric.
- **Intent assumptions.** A1 and A2 were settled by OWNER-1, and the owner can still veto them. A3 is covered either way by the 5 s sweep. A4 (MTS hours 07:00–03:00 Bangkok) is still the PRD value until the owner confirms it.
- **Bot residuals (ORCH-31/33).**
  - The worker, service and database must share one clock.
  - A re-mark replays with the current futures margin rule.
  - A backdated reduce replays as recorded.
  - A long re-mark holds a gate slot.
- Three bot comments still say "nine" collectors. They were left as PRD-stable text.
- **Not changed.** `tidewatch-specs` and `tidewatch-apis` (neither is a git repo). `DESIGN.md` was unchanged at merge; its refresh is FR-SIM-WEB-010.

(source: raw/2026-10-08-simulation-engine.md §Open questions; §Files touched, Not changed)

## What slice 2b changed here

Slice 2b ([[zone-transition-bot]], merged 2026-10-09) built on this slice without changing its order path for users:
- **Two bots per user.** `EnsureAccount` became "`EnsureBots`, then return the manual bot", so every slice-2 route now also creates Slack Water. Overview and Trade still show only `me` (ZB8). `Position.opened_by` is the owning bot's name.
- **Routes.** The gated-route count went from 26 to **32** with six `/bots` routes. `TestRouter_NoDecisionMutation` was revised on purpose to allow the reviewed `:bot_id` routes (R4). `Decision` gained `bot_version`, `run_id` and `policy_result` (see [[decision-record]]).
- **Tests re-scoped.** Slice-2 tests that assumed one bot per user now target the manual bot (R8 / R15).
- **Contracts.** C4' parameterised the close stamp and C10 added the bot version fixture (see [[paper-trading]]).
- **Schema.** Migration F is the new required schema version (see [[centralized-migrations]]).
- **Web.** The decision record became a shared component with inputs; Trade's specs are byte-unchanged (A8). `.metric-strip` moved to `metric-card.css` with 0-pixel Overview diffs (A7).

(source: raw/2026-10-09-zone-transition-bot.md §API; §Concept, Plan resolutions; §Components; §Test plan, Assumption outcomes)

## Related pages

- [[paper-trading]]: the order path, fill model, ledger marks and the bot's `sim` runner
- [[decision-record]]: the append-only `decisions` table and its outcome back-fill
- [[market-data]]: Slice 1, whose Market watch now sits below the portfolio hero
- [[centralized-migrations]]: migration E and the new required schema version
- [[market-data-worker]]: the bot worker that now also runs `sim`
- [[redis-market-contract]]: `px:last` freshness used for hours and marks
- [[instrument-master]]: venues, calendars, tick and lot sizes that intake checks
- [[market-timeseries]]: the bars fills read, and the hypertable conventions the ledger follows
- [[design-system-decisions]]: new tokens and classes, and the pending `DESIGN.md` refresh
- [[forge-preview-gateway]]: the isolated preview where E2E verification runs
- [[gold-feed-xaut-proxy]]: XAU/USD and the USDTTHB rate that marks use
- [[zone-transition-bot]]: Slice 2b, the auto bot Slack Water that trades beside `me`
- [[bot-versions-and-runs]]: the bots, versions and runs model added by migration F
