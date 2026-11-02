# Simulation engine and decision record (Slice 2, `simulation-engine`)

> Slice 2 added paper trading to Tidewatch. Each user gets a lazily created `me` bot with a ฿1,000,000 THB paper account. The user places market, limit and manual (MTS) orders from a new Trade screen. The service validates each order and writes it, together with exactly one append-only decision row, in one transaction. A new `sim` runner in the bot then fills the order on stored bars, marks the ledger hourly, after every fill and at the Bangkok day end, values an equal-weight benchmark and back-fills the outcome columns of each decision. Overview gained a portfolio hero (equity, period return, equity-versus-benchmark chart) and four KPI cards above Market watch. Four code PRs merged on 2026-10-08, all by the owner: tidewatch-migrations #4 (merge `6531508`), tidewatch-service #4 (`857d420`), tidewatch-bot #4 (`6902f4e`) and tidewatch-web #5 (`cfed50e`). Preview verification was still running when this was written. FR-SIM-E2E-001 is in progress, E2E-002 is unverified (partial pass), E2E-003 passed, E2E-004 partly passed and E2E-005 is pending. A scheduled task runs these checks and only reports. The FR-SIM-WEB-010 `DESIGN.md` refresh is in progress, and FR-SIM-DOC-002 (API collection) is deferred.

**Sources (inputs to this document).**
- Spec: `/Users/maichinu/tidewatch/tidewatch-specs/simulation-engine/build-prompt.md`, `intent.md` (SIM1–SIM13, A1–A4), `prd.md` (§4–§9)
- Build state: `/Users/maichinu/tidewatch/.forge/features/simulation-engine/state.json` (decisions OWNER-1…6, ORCH-1…34; perProject execution, deviations and reviews; `runtime.preview.acceptanceResults`; `followUps` FU-1…16; log)
- Cross-plan rulings: `/Users/maichinu/tidewatch/.forge/features/simulation-engine/planning/cross-plan-decisions.md` (ORCH-6, ORCH-8, ORCH-9, ORCH-10)
- Plans: `…/worktrees/329891b601/.plans/simulation-engine.md` (service + migration E, contracts C1–C9, SV1–SV14, R1–R19), `…/worktrees/6945fd5d6c/.plans/simulation-engine.md` (bot), `…/worktrees/5eb4e5c7ea/.plans/simulation-engine.md` (web)
- Merged code (read-only): migrations `…/worktrees/b7ddc75378` (`migrations/20261008050550_simulation_engine.sql`, `CLAUDE.md`), service `…/worktrees/329891b601` (`CLAUDE.md`, `README.md`), bot `…/worktrees/6945fd5d6c` (`README.md` "Simulation", `CLAUDE.md`), web `…/worktrees/5eb4e5c7ea`
- Evidence: `/Users/maichinu/tidewatch/.forge/features/simulation-engine/evidence/` (per project and step; `root/preview/e2e/`, `root/preview/web/`)

## Concept

### Stage, stated precisely

| Stage | Status (as recorded in state.json, last update 2026-10-08T17:42Z) |
|---|---|
| Implemented | All planned steps are done: service MIG1–MIG2 and S1–S8, bot S1–S10 (S2+S3 bundled as M1), web S1–S8 (S1+S2 bundled as M1). After review the service had 2 fix rounds, the bot 3 and the web 2, plus one web follow-up commit. |
| Verified locally | Every step's contract commands exited 0 (`make ci`, `make test-integration`, `make check-disposable-db`, `pnpm nx run-many -t lint test typecheck build`, `scripts/sql-integration.sh`, mocked Playwright). The shared arithmetic fixture is byte-identical in the service and the bot (sha256 `ff3564c8…`). |
| Reviewed | Service: code and security reviews APPROVED in round 2. Bot: code APPROVED in round 3 and security APPROVED in round 4. Web: angular, tailwind, security, code and design reviews all APPROVED, design in round 4 on rendered evidence. |
| Merged | Yes. On 2026-10-08 between 17:41:28Z and 17:42:07Z the owner merged, in order: migrations#4 at `ffe6c27` (merge `6531508`), service#4 at `8770fde` (`857d420`), bot#4 at `c37d89a` (`6902f4e`) and web#5 at `a4c808b` (`cfed50e`). The orchestrator's own `gh pr merge` was denied by the session's auto-mode classifier (OWNER-6) and was not worked around. |
| Verified on a preview | Partly. The isolated Forge preview runs exactly the merged heads on a database reset on 2026-10-08T14:57Z (OWNER-4). For per-ID results see Test plan. |
| Running on the owner's own stack | Not recorded. The only running instance in the record is the isolated Forge preview. Its volumes are retained, and CLEANUP is deferred until the scheduled task sets `verificationComplete` (ORCH-34). |

### Problem

Before this slice nothing could be traded or recorded. The paper account is where every later strategy has to prove itself, and the decision record is the dataset that later slices train on and are graded against: Signals (slice 3), Bots (slice 6), Stats (slice 7) and post-mortems (slice 8). Both were built before any signal exists, so they are designed around orders and outcomes rather than one bot's needs (intent "Problem and evidence").

### Chosen design (owner decisions SIM1–SIM13, confirmed 2026-10-08)

- **One order path, split ownership (SIM1).** The Go service is the trust boundary. It validates, then writes the `pending` order and its decision row in one transaction. The bot's `sim` runner fills pending orders on bars. Manual MTS orders are filled synchronously by the service at the entered price and time (`tag = 'manual_fill'`). The service and the bot share only the schema and Redis; there is no HTTP between them.
- **Hours (SIM3).** The service reads session state from `px:last` and has no calendar logic. A closed session gives `venue_closed` with `next_open_at`. An open session with a stale or missing price gives `price_unavailable`. Crypto is always open. Manual orders skip only the stale check.
- **Fill model (SIM2, SIM13.3).** A market order fills at the open of the first closed 1-minute bar after placement, plus slippage. A limit order fills on the first later bar that trades through, at `min(open, limit)` for a buy and `max(open, limit)` for a sell. There are no partial fills. Daily-only instruments (`PTT.BK@webull`) fill at the next session's open once that session's EOD row lands.
- **Futures (SIM5).** GO@tfex uses a margin model: the initial margin is reserved from cash, P&L is Δprice × 300 × contracts in THB, and sell-to-open is allowed. There is no variation settlement and no maintenance call.
- **Limit orders (SIM6)** are good till cancelled, reserve their estimated cost plus fees (or the margin) against available cash, and can be cancelled while pending.
- **Ledger (SIM4).** Marks are written at every UTC hour, after every fill and at 00:00 Bangkok (`kind` = `hour` / `fill` / `day_end`).
- **Outcomes (SIM7).** `r_1h` uses wall time (null for daily-only instruments). `r_1d`, `r_5d` and `r_20d` use calendar sessions. MAE/MFE run up to the earlier of session 20 and the position close. Each column is written once.
- **Fees and slippage (SIM8)** are seeded data in `venue_rules`, read by both the service estimate and the bot fill.
- **KPI cards (SIM9):** Today's return, Max drawdown, Open positions, Decisions. **Overview layout (SIM10):** hero, then KPI strip, then Market watch.
- **`me` bot (SIM12).** Created lazily on first Trade or Overview access, with ฿1,000,000, a 25% per-instrument limit and 100% total exposure. There is no reset endpoint; a fresh database is the reset.
- **Benchmark (SIM13.10).** The user's watchlist at account creation, tradable classes only, equal weight, never rebalanced, in THB.

Rejected alternatives recorded in intent:
- Everything in the bot was rejected because the UI would wait on a worker for a fill the user typed in.
- Everything in the service was rejected because it would duplicate the bar pipeline.
- Filling daily-only orders at the last close was rejected as anachronistic.
- A notional limit for futures was rejected because one GO contract (about ฿1.2M) exceeds the account.
- An empty "Tide intelligence" panel was rejected as dishonest.

### Cross-project contracts (service plan C1–C9; the source of truth for bot and web)

- **C3 shared fixture.** `internal/trading/testdata/sim-arithmetic.v1.json` is the canonical copy in the service. The bot keeps a byte-identical copy at `packages/sim/fixtures/sim-arithmetic.v1.json`. Both test suites pin sha256 `ff3564c898741e48dea08ee11eaf33873c01d2d08cef655242015d7f7b208283`, and changing it is a contract change in both repos at once. It holds a 20-order sequence (o01–o20, marks m1/m2) with anchors computed independently in Python. Two of them: m2 cash ฿568,272.57, equity ฿1,031,518.97.
- **C4 pinned SQL and locking.** Both sides take the account row first (`paper_accounts … FOR UPDATE`), then the order, then positions/fills/ledger/decisions. The fill guard, cancel guard and close stamp are pinned text (`FillGuardSQL`, `CancelGuardSQL`, `CloseStampSQL`). `orders.reserved_cash` never changes after placement. The invariant `paper_accounts.reserved = Σ holds of pending orders + Σ margin_reserved of open positions` holds after every commit. Hour and day_end marks take the account row `FOR SHARE`. Service "now" reads run in one `REPEATABLE READ READ ONLY` snapshot.
- **C5 exact arithmetic.** Both implementations use exact rationals (Go `math/big`, TS decimal strings) and round half away from zero only where a value is stored or sent on the wire. THB amounts are `round2`. `avg_px` has 8 fraction digits. A futures reduce releases `round2(margin_reserved × q / qty)` (B3/R17), not the PRD's `initial_margin × q`. The identity `equity = starting_capital + Σ fills.realized_thb + unrealized` holds exactly.
- **C6 mark price rule (ORCH-8).**
  1. A stored close counts at its bar end: for 1-minute bars, `ts + 60 s ≤ t`; for daily-only bars, the session end `≤ t`. The 24-hour window is measured on bar end.
  2. `px:last` counts when `ts ≤ t`, it is not stale, and `updated_at ≥ T − 120 s`. The 120 s bound is pinned from the status publisher's 60 s rewrite interval.
  3. A position with no price falls back to its last known mark, else its latest fill price.
  4. USD/THB comes from `USDTTHB@binance-th`, then `USDTHB@oanda-demo`, then the last ledger row's rate.
  5. A benchmark member with no price uses its latest close with no window, else its start price. With no members the benchmark is null.
  6. `ledger.marks` is `{instrument_id: {px, fx, value_thb}}` with decimal strings.
- **C7 wire formats.** THB amounts are 2-dp strings and percentages are 4-dp in percent units. Outcome ratios (`r_*`, `mae`, `mfe`) travel as the stored ratio with 6 dp, never as percent (ORCH-6). The plan added `kpis.today_base_equity` and `kpis.peak_equity` (ORCH-6/R18).
- **C8:** nine new error codes and typed details. **C9:** decision action/direction, and a side check that stays correct across pending orders.

### OWNER decisions during the build

- **OWNER-1 (A1/A2), adopted on the orchestrator's recommendation; the owner may veto.**
  - `webull/set` `commission_pct` is **0.00047**: Webull TH 0.04% + SET 0.005% + TSD 0.001% + SEC 0.001%, all ex-VAT, with VAT 7%. Source: webull.co.th pricing, read 2026-10-08. It replaces the PRD's 0.0015.
  - `tfex/tfex` `initial_margin_thb` is **137,550.00**: 1.75 × the TCH GO margin of ฿78,600 effective 11 June 2026. It replaces the PRD's 150,000. This number changes monthly, and an update is a data migration.
- **OWNER-2.** Dependency-gated lanes with smelt bundling.
- **OWNER-3.** Isolated preview database; volumes retained after merge.
- **OWNER-4.** After the ORCH-31/33 bot fix, the preview database was reset and the 20-order run restarted. Only this run's volume was deleted, and attempt-1 evidence was archived.
- **OWNER-5 / OWNER-6.** A scheduled task (`tidewatch-slice2-verify-merge`, cron `30 10,15,21 * * 1-5` Bangkok) was first authorised to merge after full verification. When the merge was denied by the classifier, the task became verify-and-report only, and the owner merged the four PRs by hand.

### Recorded deviations and rulings (all within PRD latitude unless noted)

**Migrations / service**

- **FU-2.** The PRD's `venue_rules` CHECK lets a spot rule with a margin but no multiplier pass. The migration keeps the PRD CHECK exactly as written; tightening it is deferred.
- **ORCH-11 / ORCH-24 (R13).** The service never evaluates calendars. For a backdated manual fill's mark on an account holding a daily-only instrument whose `px:last` is unusable, it uses the latest `candles_eod` row with `session_date + 1 day 00:00 UTC ≤ t`. For `set` this never looks ahead but can lag by up to 14 h 20 min. The same calendar-free end bounds the C6 24 h window, so for about 14 h the service shows the stored close where the bot uses its last mark. The price is the same, but `Position.last` is non-null on the service and null on the bot.
- **R14.** `manual_fill.filled_at` may not be before the account's `started_at`.
- **R15.** A stale `px:last` refuses a skip.
- **R16.** Ledger readers order rows by `(ts, kind)` with `fill < hour < day_end`.
- **ORCH-21.** `test/integration/events_test.go` was changed so the slice-0 completeness loop iterates an explicit list. The three trading events got their own positive assertions in S4/S5.
- **ORCH-27.** `internal/simverify/seed.go`, `actual.go` and `report.go` were added as scoped files. The plan's "six USD / two manual" counts were wrong; the C3 sequence has 7 USD fills and 3 manual orders.
- **S3/S4/S6 notes:**
  - A missed venue-rule reload happens at most once per second.
  - A USD position with no C6 rate uses its latest fill's `usd_thb`.
  - A manual price is stored as entered, not tick-rounded.
  - Bangkok is a fixed UTC+7.
  - `max_drawdown_pct` / `peak_equity` are computed over ledger marks only, not the live "now" point.
- **ORCH-28 fix round:**
  - `unrealized_pct` is `"0.0000"` (not null) when the base is zero.
  - Negative `insufficient_cash.available` can reach the client.
  - `ledger.marks.px` is written as used, not rounded.
  - A concurrent duplicate `client_order_id` integration test was added.

**Bot**

- **ORCH-20.** `@tidewatch-bot/shared` became a runtime dependency only when S6 first imported it.
- **S4/S6 notes:**
  - A 5m bar's end would be `ts + 5 min` (FU-7; no 5m instrument is seeded).
  - New error events: `sim_mark_failed`, `sim_outcome_failed`.
  - `sim_mark_lag_seconds` is a gauge.
- **ORCH-26 fix round (security r1):**
  - Mark reads use the fill transaction's own connection, so there is no nested pool checkout under a row lock.
  - A global concurrency gate of 3 is shared by fill passes, outcome tasks and re-marks.
  - Bar windows per pass are bounded.
  - Pending reads are paged at 500.
  - `position_changed` / `usd_thb_unavailable` back off until a newer bar is stored.
  - The outcome sweep keeps an in-memory `(ts, decision_id)` cursor.
  - Any null outcome column is retried.
  - Rule 3 "most recent fill" is ordered by `filled_at DESC, created_at DESC`.
  - The USD fallback to the last fill's rate matches the service.
- **ORCH-31 (found on the preview by FR-SIM-E2E-002).** Fills can commit out of `filled_at` order: US bars arrive about 15–17 min late, and manual fills can be backdated. The ruling makes the bot the single re-marker.
  - Every mark is computed from the account state *as of* its `ts` (`as-of.ts`).
  - A durable `staleLedger` query flags rows computed before a fill that precedes them. Its insert instant is `GREATEST(created_at, uuidv7 ts of fill_id)` with 1 ms tolerance, plus a 30 s window for manual fills.
  - A re-mark pass every 15 s rewrites those rows in `(ts, kind)` order (`remark.ts`).
  - The service is unchanged; its manual-fill `fill` row is rewritten by the bot 30–45 s later.
- **ORCH-33 hardening (security r3):**
  - At most 500 rows per account per sweep, resuming from the earliest stale row.
  - Accounts rotate between sweeps.
  - The stale scan is bounded to fills inserted within 7 days, as a range on the `fill_id` uuidv7 key.
  - Rules 3/4 history reads are strictly before `(t, kind)`.
  - The worker/DB same-clock assumption is documented, not changed.
- **Accepted residuals:**
  - The bot, service and database must share a clock.
  - Each stale check scans fills within the horizon.
  - A replay uses the *current* futures margin rule.
  - A backdated reduce replays as recorded.

**Web**

- **ORCH-18.** Idle range-switch text in the light theme uses `--text-2` (4.41:1 → AA).
- **ORCH-19.** Whole-baht display truncates toward zero, so ฿1,018,934.52 shows as ฿1,018,934, matching the hero's integer part. The PRD wins over plan SE-9.
- **ORCH-22.** `e2e/src/market-watch.spec.ts:103` was narrowed to Market watch's own section, because Overview now has two `.content section`s.
- **ORCH-23 fix round:**
  - The estimate is fingerprint-gated, so stale numbers are not shown.
  - The chart tooltip is `aria-hidden`, with an sr-only status driven by the keyboard.
  - A single-point series draws a flat line.
  - "—" placeholders carry sr-only words.
  - Benchmark opacity is one named token.
- **ORCH-30 fix round:**
  - Heading order and unique landmark names.
  - The busy *Placing…* button reaches ≥ 4.5:1 (5.51 light / 6.70 dark).
  - "Market, next bar" fits the 300px ticket.
  - `aria-busy` is set on the pending estimate.
  - Follow-up `a4c808b`: the manual-fill fields stack in containers ≤ 400px, and the Open orders Cancel column is sticky.
- **Smaller deviations:**
  - Short futures show the unit "contracts · short".
  - The futures margin line uses the position's `margin_reserved`.
  - A refusal without `details` falls back to generic copy (FU-4).

**Orchestration**

- **ORCH-1.** Migration E was folded into the service plan as MIG steps, with its own worktree, branch and PR.
- **ORCH-3.** `tidewatch-apis` was excluded because it is not a git repo, so FR-SIM-DOC-002 is deferred.
- **ORCH-9 / ORCH-14.** The 20-order script and spreadsheet are service code under `verification/` and `internal/simverify`. The orchestrator only runs them.
- **ORCH-25.** The design reviewer's rendered verdict gated the merge rather than the PR.
- **ORCH-29.** On the preview, E2E-001 owns the admin account and runs first on a fresh account. Only non-order work runs in parallel.

## Database

Migration E, `migrations/20261008050550_simulation_engine.sql` in tidewatch-migrations, adds nine tables. It runs in goose's default transaction. Its version **`20261008050550`** is the new `RequiredSchemaVersion` in `internal/platform/postgres/schema.go`. `/ready` stays 503 until it is applied. The bot has no schema constant; its harness asserts E is applied. The previous pin was C `20261006131346`; D `20261007072235` was never pinned.

| Table | Key / notable constraints | Purpose |
|---|---|---|
| `venue_rules` | PK `(venue_id, calendar_id)`; CHECK `(settlement='futures') = (contract_multiplier IS NOT NULL AND initial_margin_thb IS NOT NULL)`; `source` NOT NULL | Fees, slippage, multiplier, margin and manual flag. Read by the service estimate/intake and the bot fill. |
| `bots` | uuidv7 PK; `kind` manual/auto; `mode` paper_manual/paper_auto/live; `max_position_pct` (0,1], `max_total_exposure` > 0; unique partial index `bots_owner_manual_key (owner_user_id) WHERE kind='manual'` | One manual `me` bot per user. |
| `paper_accounts` | PK `bot_id`; `quote_ccy = 'THB'`; `reserved ≥ 0` | Cash, reserved and starting capital. |
| `benchmark_members` | PK `(bot_id, instrument_id)`; `weight`, `start_px`, `start_usd_thb` | Benchmark snapshot taken at account creation. |
| `decisions` | uuidv7 PK; indexes `decisions_bot_ts_idx (bot_id, ts DESC)`, `decisions_pending_outcomes_idx (ts) WHERE r_20d IS NULL OR mae IS NULL`; three triggers | The append-only decision record (architecture §7). |
| `orders` | uuidv7 PK; `UNIQUE (bot_id, client_order_id)`; `decision_id` UNIQUE FK; CHECK `(type='limit') = (limit_px IS NOT NULL)`; `orders_pending_idx (instrument_id, placed_at) WHERE status='pending'` | Orders; `reserved_cash` is the placement hold. |
| `fills` | uuidv7 PK; `order_id` UNIQUE; `tag` simulated/manual_fill; `usd_thb`, `fee_detail` jsonb, `cash_delta`, `realized_thb` | One fill per order (no partial fills). |
| `positions` | uuidv7 PK; unique partial `positions_open_key (bot_id, instrument_id) WHERE closed_at IS NULL`; `opened_by_decision_id` FK | Open/closed positions; a reopen is a new row. |
| `ledger` | PK `(bot_id, ts, kind)`, `kind` hour/fill/day_end; TimescaleDB hypertable on `ts`, 28-day chunks, `create_default_indexes => false`, no columnstore, no retention | Marks: cash, reserved, equity, realized, unrealized, positions_value, usd_thb, benchmark, marks jsonb, computed_at. |

The `decisions` row also carries columns for later slices, all nullable: `bot_version`, `loop` (`user` now), `run_id`, `candidate_id`, `signal_ids uuid[]`, `signal_snapshot`, `model`, `policy_result`, `followed_recommendation`, `user_override_reason`. Slice 6 therefore needs no migration (O7).

**Append-only triggers** (every message starts `decisions is append-only`):

```sql
CREATE TRIGGER decisions_append_only          BEFORE DELETE   ON decisions FOR EACH ROW       EXECUTE FUNCTION decisions_reject_mutation();
CREATE TRIGGER decisions_append_only_truncate BEFORE TRUNCATE ON decisions FOR EACH STATEMENT EXECUTE FUNCTION decisions_reject_mutation();
CREATE TRIGGER decisions_backfill_only        BEFORE UPDATE   ON decisions FOR EACH ROW       EXECUTE FUNCTION decisions_backfill_only();
```

`decisions_backfill_only` compares the `to_jsonb` row images with the outcome columns, `outcomes_detail` and `post_mortem` removed. Any column added later is therefore protected by default. The rules:
- `r_1h`, `r_1d`, `r_5d`, `r_20d`, `mae`, `mfe`, `mae_mfe_through`, `exit_reason` and `closed_at` are write-once (null → value).
- `outcomes_detail` (NOT NULL DEFAULT `'{}'`) stays an object and may only gain keys. The bot writes one top-level key per outcome column (C1).
- `post_mortem` can never return to null and is frozen once it carries `"confirmed_by_user": true`.

**Seeds:** six `venue_rules` rows, each with a `source` citation. Nothing else is seeded; the `me` bot is lazy because the admin user is created at service bootstrap.

| venue / calendar | settlement | manual | commission_pct | vat | sell per unit / cap (quote) | per contract ฿ | slippage | multiplier | initial margin ฿ |
|---|---|---|---|---|---|---|---|---|---|
| `webull` / `us-equities` | spot | no | 0.0010 | 0.07 | 0.000195 / 9.79 | — | 2 bp | — | — |
| `webull` / `set` | spot | no | **0.00047** (OWNER-1) | 0.07 | — | — | 10 bp | — | — |
| `binance-th` / `crypto` | spot | no | 0.0025 | 0 | — | — | 5 bp | — | — |
| `oanda-demo` / `gold-23-5` | spot | no | 0 | 0 | — | — | 3 bp | — | — |
| `tfex` / `tfex` | futures | no | 0 | 0 | — | 210.00 | 1 tick | 300 | **137,550.00** (OWNER-1) |
| `mts` / `mts` | spot | yes | 0 | 0 | — | — | 0 | — | — |

The `oanda-demo` rule models the OANDA paper venue. `XAUUSD@oanda-demo` has been priced from Binance TH `XAUTUSDT` since migration D, so OANDA keys are never needed. A changed number is a data migration; fills keep the numbers they used (`fee_detail`).

**Down** drops the nine tables in reverse order, `IF EXISTS`, no `CASCADE`, then the two functions. It is destructive (every order, fill, mark and decision) and owner-only. `scripts/check-disposable-db.sh` gained E's relations, triggers, hypertable and seed assertions. The harness reported PASS 848/0.

## API

All routes are on tidewatch-service. They mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`. CSRF covers the four POSTs. There is no `/api` prefix and no `bot_id` parameter; the `me` bot comes from the session, so another user's order is `404 not_found`. The gated-route count test now counts 26 (23 production + 3 test probes). There is no update or delete route for decisions (`TestRouter_NoDecisionMutation`).

| Method and path | Request | 2xx response |
|---|---|---|
| `GET /trade` | — | `{generated_at, bot, account: {quote_ccy, starting_capital, cash, reserved, available, equity, realized, unrealized, started_at, days_on_paper, limits: {max_position_pct "25.0000", max_total_exposure "100.0000"}, usd_thb: {rate, ts, source} \| null}, positions: [Position], open_orders: [Order], tradable_instruments: [TradableInstrument]}` |
| `POST /orders` | `{client_order_id (uuid), instrument_id, side, type, qty, limit_px?, manual_fill?: {px, filled_at}, decision_ctx?}` | 201, or 200 on an idempotent replay: `{order, fill \| null, decision_id}` |
| `POST /orders/estimate` | the same minus `client_order_id` | 200 `{estimate_px, gross_thb, fee_thb, fee_detail, slippage_thb, required_thb, usd_thb, portfolio_after: {position_pct, exposure_pct}, fill_note}`, or the same 4xx a placement would get |
| `POST /orders/{order_id}/cancel` | — | 200 `Order`; 404 `not_found`; 409 `order_not_pending` |
| `GET /decisions` | `limit` 1–200 (default 50), opaque `cursor` (keyset `(ts DESC, decision_id DESC)`) | `{items: [Decision], next_cursor}` |
| `POST /decisions/skip` | `{instrument_id, direction, qty?, candidate_id: null, reason?}` (`reason` ≤ 500 runes, never logged) | 201 `Decision` (`action = 'skip'`); no UI calls it in this slice |
| `GET /portfolio` | `period` ∈ `1w`/`1m`/`3m` (default `1m`) | `{generated_at, period, since, equity_now, benchmark_now, return_period, return_total, starting_capital, started_at, days_on_paper, series: [{ts, equity, benchmark}], kpis: {today_return_pct, today_base_equity, max_drawdown_pct, peak_equity, open_positions: {count, deployed_pct}, decisions: {count, orders, skipped}}}` |

**Intake order (`POST /orders`, PRD §4.3 / SV4).** The first failure answers and nothing is written. The steps are:
1. Strict body decode (400 `invalid_request`; unknown field → `details.reason unknown_field`, never naming the key).
2. Lazy account creation, in its own committed transaction under an advisory lock.
3. Account row `FOR UPDATE`.
4. Idempotency on `(bot_id, client_order_id)`.
5. Instrument (404 `unknown_instrument`, 422 `instrument_inactive` / `instrument_not_tradable`).
6. Lot and tick (400, reasons `lot_size` / `tick_size`).
7. Manual venue (422 `manual_fill_required` with `field` `manual_fill_px` / `manual_fill_filled_at`; 400 `manual_fill_not_allowed`; a manual limit is 400).
8. Hours and price from `px:last` with the 120 s bound (`venue_closed` with `next_open_at`, `price_unavailable`).
9. Side check (`insufficient_position` with `held`).
10. Money (`insufficient_cash` {required, available}, `position_limit` / `exposure_limit` {after_pct, limit_pct}).
11. Write the decision (`loop`/`actor` `user`, `px_at_decision`, `market_state` from the latest strip-timeframe `indicators` row), the order, `reserved += required` and the audit event `order_placed`. A manual order is then filled in the same transaction, with its own `fill` ledger mark.

The estimate runs the same `check()` read-only, so it cannot disagree with a placement.

**New error codes**, appended to `AllCodes()` in this order:

| Code | Status |
|---|---|
| `instrument_not_tradable` | 422 |
| `manual_fill_required` | 422 |
| `venue_closed` | 422 |
| `price_unavailable` | 422 |
| `insufficient_position` | 422 |
| `insufficient_cash` | 422 |
| `position_limit` | 422 |
| `exposure_limit` | 422 |
| `order_not_pending` | 409 |

New 400 reasons: `lot_size`, `tick_size`, `manual_fill_not_allowed`, `unknown_field`. The envelope stays `{error, code, requestID}` with optional `details`.

**Wire formats (C7):**
- THB amounts are 2-dp strings; percentages are 4-dp in percent units.
- Outcome fields `r_1h…r_20d`, `mae` and `mfe` are stored ratios with 6 dp (the web multiplies by 100).
- `fill_note` ∈ `next_bar` / `next_session_open` / `manual` / `futures_margin`.
- `qty_unit` ∈ `shares` / `units` / `baht` / `oz` / `contracts`.
- `today_base_equity` is null with no prior `day_end` mark. `peak_equity` is null with no mark after the initial one. The benchmark is null when the account has no members.

**Audit events (`events`):** `order_placed {order_id, instrument_id, side, type, qty, manual_fill}`, `order_cancelled {order_id}`, `decision_skipped {decision_id, instrument_id}`.

**Service metrics/logs:**
- `orders_placed_total{result}` ∈ `filled_manual` / `pending` / `rejected`. A replay or an estimate counts nothing.
- `orders_cancelled_total{result}` ∈ `cancelled` / `not_pending` / `not_found`.
- Logs: `order_placed`, `order_rejected`, `order_cancelled`, `paper_account_created`, `benchmark_member_excluded`, `mark_price_missing`. They carry ids, codes and amounts only.

**Bot ↔ service.** No new Redis key, channel or env variable, and nothing new on `/ws`. The bot reads the status publisher's in-memory `px:last` record (a price view wrapping `writeLast`), never Redis, for marks.

**Bot runner `sim`** (`packages/sim`, the tenth `COLLECTOR_NAMES` entry, on by default, lock `runner:sim`, no venue budget). It runs four loops:
- A fill sweep every 5 s, plus a fill pass on each bar-sink `persisted` event.
- Hour/day_end marks 10 s after each boundary. Missed boundaries are never back-filled.
- An outcome sweep every 1 min, at most 500 decisions per sweep with an in-memory cursor.
- A re-mark sweep every 15 s.

Passes for one instrument never overlap (one queue per instrument), and a global gate of 3 (`SIM_CONCURRENCY`) limits concurrent work. Metrics: `sim_orders_pending`, `sim_fills_total{venue_id,tag}`, `sim_fill_latency_seconds`, `sim_marks_total{kind}`, `sim_mark_lag_seconds{kind}` (gauge), `sim_outcomes_written_total{column}`, `sim_outcome_lag_seconds`. Logs: `sim_order_filled`, `sim_fill_skipped`, `sim_fill_failed`, `sim_mark_written` (`remark: true` on rewrites), `sim_mark_failed`, `sim_mark_price_missing`, `sim_benchmark_member_excluded`, `sim_outcome_written`, `sim_outcome_failed`. There is no dedicated re-mark metric (FU-16).

## Components

Angular, under `src/app/pages/workspace/`. Per `DESIGN.md` rules: no Material, no chart library, no `dark:`, tokens only in `tokens.css`, native `<dialog>`/controls.

**Trade (`feat-trade/`, replaces the slice-0 placeholder route in `workspace.routes.ts`)**
- `app-trade` (`trade.ts`) owns the layout: a `300px minmax(0,1fr)` grid, one column at ≤ 1080 (ticket and recommendation side by side) and stacked at ≤ 600. The header sub line reads `Paper account · ฿… · available ฿…`, with a *Manual mode* tag. It provides `TradeService` (`feat-trade/data/trade.service.ts`), which polls `GET /trade` every 10 s while the screen is open, reloads after a place or cancel, and pages `GET /decisions` with *Load more* (`util/merge-decisions.ts`).
- `app-order-ticket` (`order-ticket.ts`) is a signal form with these fields:
  - Instrument (native select from `tradable_instruments`), Side, Type, Quantity (hint from `venue_rule`) and Limit price.
  - For MTS, a manual block with Fill price and Fill time (Bangkok `datetime-local`).
  - Estimate rows from `POST /orders/estimate`, debounced 300 ms and fingerprint-gated, in a polite live region with `aria-busy` while pending.
  - The fill note (`util/fill-note.ts`); futures margin copy comes from `venue_rule.initial_margin_thb`.
  - A `role="alert"` refusal line, chosen by `code` (`util/refusal-message.ts`, PRD §7.5).
  - *Place paper order* / *Placing…*.

  A `client_order_id` UUID is generated per submission and reused on retry (`util/client-order-id.ts`).
- `app-open-orders` (`open-orders.ts`): a table with Placed / Instrument / Side / Type / Qty / Limit / Reserved / Status and a sticky *Cancel* column. Toasts read "Order cancelled." and, on 409, "That order was already filled or cancelled." followed by a reload.
- `app-positions-table` (`positions-table.ts`): Instrument / Size / Entry / Last / P&L (percent plus THB on a second line) / Zone (`app-zone-label`) / Opened by "Me". *Last* and P&L update in place from the existing `/ws` price stream (`util/live-position.ts`); the table is not a live region.
- `app-decision-record` (`decision-record.ts`): When / Decision / Signal ("Own idea, no signal") / Followed? / After 1 d / After 5 d ("Not yet" while null) / Post-mortem ("Not graded yet"). It shows 50 rows plus *Load more*.
- A recommendation placeholder panel reads "No recommendation yet…" with the tag *Arrives with bots* and no buttons.

**Overview (`feat-overview/`)**: `app-overview`'s `.content` holds, in order:
1. `app-portfolio-hero`: equity with role tokens per breakpoint, the period-return pill, "since …", a `1W/1M/3M` range switch (`aria-pressed`, named group), the chart, a legend and a footer (Starting capital, Total return, Days on paper).
2. `app-kpi-strip`: four `.metric-card`s (Today's return, Max drawdown, Open positions, Decisions).
3. The unchanged `app-market-watch`.

`app-equity-chart` (feature-local) is an inline SVG with `role="img"` and an accessible name. The equity path is `--brand`; the benchmark path is `--violet` at a named opacity. It has a keyboard tooltip driven by the arrow keys, and helpers in `util/chart-geometry.ts` and `util/portfolio-view.ts`. `PortfolioService` (`feat-overview/data/portfolio.service.ts`) is component-provided and calls `GET /portfolio?period=`.

**Data layer.**
- `data/trade.model.ts` and `data/portfolio.model.ts` hold strict parsers.
- `data/trade-api.service.ts` and `data/portfolio-api.service.ts` each have their own query codec.
- `util/money-format.ts` truncates whole baht (ORCH-19); `util/bangkok-time.ts` formats Bangkok times.

**Styles and tokens.**
- New role tokens in `src/styles/tailwind/theme.css`: `--text-metric` (22px), `--tracking-hero` (−0.055em), and the hero sizes `--text-hero-compact` (33px), `--text-hero-tablet` (39px) and `--text-hero-phone` (35px).
- No new colour.
- New reusable classes in `src/styles/components/`: `section.css` (`.section-head`), `metric-card.css`, `range-switch.css`, `portfolio.css`, `trade.css`, plus `.second` / `.status-line` and table tweaks in `table.css`.
- New icon: `trend` in `shared/ui-icon/icons.ts`, copied from the approved mockup.
- Documenting the new pieces in `DESIGN.md` is FR-SIM-WEB-010, in progress in a separate design worktree.

## Files touched

From `git diff --stat` base..merge commit for each repo (`/Users/maichinu/tidewatch/.forge/features/simulation-engine/artifacts/files-touched/`). Each non-test file has a one-line purpose note; tests are grouped by folder.

| Repo | Range | Files | Lines |
|---|---|---|---|
| tidewatch-migrations | `a2e7f81..6531508` | 4 | +1,146 / −33 |
| tidewatch-service | `734ce35..857d420` | 90 | +26,849 / −122 |
| tidewatch-bot | `a420767..6902f4e` | 65 | +24,060 / −111 |
| tidewatch-web | `a9459e0..cfed50e` | 79 | +18,756 / −133 |

### tidewatch-migrations (PR #4) — 4 files, +1,146 / −33

- `migrations/20261008050550_simulation_engine.sql`: migration E. Nine tables, the `decisions` triggers, the `ledger` hypertable and the six venue-rule seeds.
- `scripts/check-disposable-db.sh`: harness expectations for E (relations, triggers, hypertable, seeds, the append-only transcript and the down).
- `README.md`, `CLAUDE.md`: migration E conventions and the new required schema version.

### tidewatch-service (PR #4) — 90 files, +26,849 / −122

**Docs**
- `README.md`: trading routes, codes, events, metrics, verification script and schema version.
- `CLAUDE.md`: paper-trading invariants, named trading tests and the required schema version.

**Composition and platform**
- `internal/app/app.go`: wires the trading handlers and services into `newApp`.
- `internal/app/router.go`: `mountTrading`, the seven gated trading routes.
- `internal/platform/postgres/schema.go`: `RequiredSchemaVersion` = `20261008050550`.
- `internal/pgtest/migrate.go`: per-test databases migrated through E (integration-tag helper).
- `scripts/integration-test.sh`: integration harness updates for migration E.
- Tests: `internal/app/router_test.go`.

**Errors, audit, metrics**
- `pkg/apperror/codes.go`: the nine new codes and the new 400 reasons.
- `pkg/apperror/apperror.go`: typed trading details and `NewTrade`.
- `internal/audit/audit.go`: typed `order_placed`, `order_cancelled` and `decision_skipped` constructors.
- `internal/observability/metrics/trading.go`: `orders_placed_total` and `orders_cancelled_total`.
- `internal/observability/metrics/metrics.go`: registers the trading series.
- Tests: `pkg/apperror/` (`apperror_test.go`, `codes_test.go`), `internal/audit/audit_test.go`, `internal/observability/metrics/metrics_test.go`, `internal/httpx/response/response_test.go`.

**Handlers (`internal/handlers/`)**
- `strictjson.go`: strict body decoder (unknown fields give `unknown_field`).
- `trade.go`: `GET /trade`.
- `orders.go`: `POST /orders`, `POST /orders/estimate` and cancel, with their metrics and logs.
- `decisions.go`: `GET /decisions` and `POST /decisions/skip`.
- `portfolio.go`: `GET /portfolio`.
- Tests: `decisions_test.go`, `orders_test.go`, `portfolio_test.go`, `strictjson_test.go`, `trade_test.go`.

**Repositories (`internal/repository/postgres/`)**
- `account.go`: bots, paper accounts, benchmark members, the account lock, and position and pending-order reads.
- `order.go`: orders, fills, positions and the C4 pinned statements.
- `decision.go`: decision inserts and the keyset list.
- `ledger.go`: ledger upsert and reads, equity path and decision counts.
- `price.go`: C6 stored closes and USD/THB lookups.
- `venuerule.go`: `venue_rules` reads.
- `indicator.go`: latest strip-timeframe indicator row (for `market_state` and the zone).
- Tests: `order_test.go`, `trading_test.go`.

**Trading service (`internal/services/trading/`)**
- `service.go`: service construction and dependencies.
- `store.go`: base `Store` / `Ledger` interfaces and the snapshot runner.
- `account.go`: the lazy `me` bot, account, benchmark snapshot and initial mark.
- `venuerules.go`: venue-rule cache (60 s TTL, reload on a miss).
- `marks.go`: C6 marks and "now" equity.
- `trade.go`: the `GET /trade` read model.
- `place.go`: intake checks in order, `InOrderTx`, the writes, Bangkok as fixed UTC+7.
- `estimate.go`: the read-only estimate on the same `check()`.
- `manualfill.go`: synchronous MTS fill and its `fill` mark.
- `cancel.go`: cancel under the account lock (`CancelStore`).
- `decisions.go`: skip and decision list (`DecisionStore`).
- `cursor.go`: the opaque, checksummed decisions cursor.
- `portfolio.go`: series, returns and KPIs (`PortfolioLedger`).
- Tests: `decisions_test.go`, `place_test.go`, `portfolio_test.go`, `service_test.go`, `trade_test.go`.

**Exact arithmetic (`internal/trading/`, new pure package)**
- `decimal.go`: exact decimals on `math/big`.
- `arith.go`: C5 fill, fee, margin, equity and benchmark arithmetic, and the C9 side check.
- `marks.go`: the C6 price-selection rules.
- `rules.go`: the venue-rule type and C7 derivations (`qty_unit`, decimals, `fill_note`).
- `testdata/sim-arithmetic.v1.json`: the shared C3 fixture (sha256 `ff3564c8…`).
- Tests: `arith_test.go`, `decimal_test.go`, `fixture_test.go`, `rules_test.go`.

**FR-SIM-E2E-001 driver (`internal/simverify/`, new; `verification/`, new)**
- `internal/simverify/sheet.go`: spreadsheet reader and C5 recompute.
- `internal/simverify/driver.go`: HTTP driver for the 20-order run, resumable and with a freshness check.
- `internal/simverify/seed.go`: run seeding and initial state.
- `internal/simverify/actual.go`: actual values from the stored fills.
- `internal/simverify/report.go`: comparison report against `GET /trade`.
- `verification/sim-20-orders.sh`: bash 3.2 entry point.
- `verification/sim20.go`: `//go:build ignore` main that runs the driver.
- `verification/sim-20-orders.csv`: the 20-order spreadsheet.
- `verification/sim-20-fills.sql`: read-only fills query for psql.
- Tests: `internal/simverify/` (`driver_test.go`, `fakeservice_test.go`, `sheet_test.go`).

**Committed SQL and integration tests**
- `test/sql/portfolio_series.sql`, `test/sql/portfolio_kpis.sql`: committed series and KPI SQL that `GET /portfolio` must equal.
- Tests in `test/integration/`: `cancel_test.go`, `decisions_test.go`, `events_test.go` (ORCH-21), `main_test.go`, `observability_test.go`, `orders_test.go`, `portfolio_test.go`, `ready_test.go`, `redaction_test.go`, `trade_test.go`, `trading_fixtures_test.go`, `verification_test.go`.

### tidewatch-bot (PR #4) — 65 files, +24,060 / −111

**Repo root**
- `README.md`: Simulation section (runner, tables, fills, marks, re-mark, outcomes, metrics, events).
- `CLAUDE.md`: sim runner patterns, dependency shape and gotchas.
- `Dockerfile`: builds and ships the `sim` dist.
- `.env.example`: `sim` in the `MARKET_DATA_COLLECTORS` notes.
- `tsconfig.json`: project reference for `packages/sim`.
- `pnpm-lock.yaml`: lockfile entries for the new package.
- `scripts/sql-integration.sh`: runs the sim integration specs, asserts migration E and counts leftover rows.

**`packages/market-data`**
- `src/calendar/calendar.ts`: trading-session helpers used by the fill rules and outcomes.
- `src/index.ts`: exports them.
- Tests: `src/calendar/calendar.spec.ts`.

**`packages/shared`**
- `src/config.ts`: `sim` added to `COLLECTOR_NAMES`.
- Tests: `src/config.spec.ts`.

**`packages/worker`**
- `src/serve.ts`: starts the `sim` runner and wraps `writeLast` in the price-view recorder.
- `src/run.ts`: pool-size comment for the sim runner (`SERVE_POOL_MAX` stays 12).
- `package.json`: depends on `@tidewatch-bot/sim`.
- `tsconfig.lib.json`: reference to `sim`.
- Tests: `src/serve.spec.ts`.

**`packages/sim` (new Nx package, `type:shared`)**
- Config:
  - `package.json`: package manifest (`market-data`, `shared` and `prom-client` as dependencies).
  - `tsconfig.json`, `tsconfig.lib.json`, `tsconfig.spec.json`: TypeScript project config.
  - `vitest.config.mts`: unit test config with the no-network guard.
  - `vitest.int.config.mts`: integration spec config.
- Fixtures:
  - `fixtures/sim-arithmetic.v1.json`: byte-identical copy of the service's C3 fixture.
  - `fixtures/btcthb-1m.csv`: BTC/THB 1-minute bar fixture.
  - `fixtures/ptt-bk-eod.csv`: PTT.BK daily-only bar fixture.
  - `fixtures/README.md`: fixture provenance (including constructed bars).
- Source:
  - `src/index.ts`: package exports.
  - `src/money.ts`: exact decimal-string money.
  - `src/venue-rule.ts`: venue-rule reader and type.
  - `src/arithmetic.ts`: the §4.6 / C5 fill, fee, margin and equity arithmetic.
  - `src/fill-rules.ts`: market, limit, futures and daily-only fill rules over candidate bars.
  - `src/marks.ts`: C6 mark prices, account marks and the benchmark.
  - `src/as-of.ts`: account state as of a mark instant (ORCH-31).
  - `src/remark.ts`: stale-ledger detection and the re-mark pass (ORCH-31/33).
  - `src/schedule.ts`: hour and Bangkok day-end boundaries.
  - `src/outcomes.ts`: outcome horizons, MAE/MFE and `outcomes_detail`.
  - `src/store.ts`: the sim store interface.
  - `src/pg-store.ts`: PostgreSQL store on migration E (C4 SQL, lock order, one connection per transaction).
  - `src/fill-pass.ts`: per-instrument fill pass (guard, position check, back-off, bounded reads).
  - `src/engine.ts`: triggers, per-instrument queues and the fill, mark, outcome and re-mark loops.
  - `src/gate.ts`: shared concurrency gate (`SIM_CONCURRENCY` = 3).
  - `src/metrics.ts`: the seven `sim_*` metrics.
  - `src/price-view.ts`: recorded `px:last` view with the 120 s bound.
  - `src/runner.ts`: the `sim` `Runner` (lock `runner:sim`).
  - `src/testing/index.ts`: the testing export.
  - `src/testing/fixtures.ts`: bar and account fixture builders.
  - `src/testing/memory-store.ts`: in-memory store for specs.
- Tests in `src/`: `arithmetic.spec.ts`, `engine.spec.ts`, `fill-pass.spec.ts`, `fill-rules.spec.ts`, `gate.spec.ts`, `marks.spec.ts`, `metrics.spec.ts`, `money.spec.ts`, `outcomes.spec.ts`, `pg-store.int.spec.ts`, `price-view.spec.ts`, `remark.spec.ts`, `runner.spec.ts`, `schedule.spec.ts`, `shared-fixture.spec.ts`, `venue-rule.spec.ts`.
- Tests in `src/testing/`: `memory-store.spec.ts`.

### tidewatch-web (PR #5) — 79 files, +18,756 / −133

**Docs**
- `README.md`: Trade screen, portfolio hero, data flow and states.
- `CLAUDE.md`: Trade and Overview conventions.

**Routing, shell, icons**
- `src/app/pages/workspace/workspace.routes.ts`: Trade route now loads `app-trade`.
- `src/app/shared/ui-icon/icons.ts`: new `trend` icon.
- Tests: `src/app/app.routes.spec.ts`, `src/app/pages/workspace/feat-screen-placeholder/screen-placeholder.spec.ts`, `src/app/shell/shell.spec.ts`, `src/app/shared/ui-icon/icon.spec.ts`.

**Data layer (`src/app/pages/workspace/data/`)**
- `trade.model.ts`: Trade, order, decision and estimate types with strict parsers.
- `trade-api.service.ts`: HTTP client for the trade, order, estimate, cancel and decision routes.
- `portfolio.model.ts`: portfolio types and parser.
- `portfolio-api.service.ts`: HTTP client for `GET /portfolio`.
- Tests: `trade.model.spec.ts`, `trade-api.service.spec.ts`, `portfolio.model.spec.ts`, `portfolio-api.service.spec.ts`.

**Shared utilities (`src/app/pages/workspace/util/`)**
- `money-format.ts`: THB, amount and percent formatting (whole baht truncated, ORCH-19).
- `bangkok-time.ts`: Asia/Bangkok date and time formatting.
- Tests: `money-format.spec.ts`, `bangkok-time.spec.ts`.

**Trade (`src/app/pages/workspace/feat-trade/`, new)**
- `trade.ts`: `app-trade` screen layout and states.
- `order-ticket.ts`: `app-order-ticket` signal form, estimate, manual fill and placement.
- `open-orders.ts`: `app-open-orders` table with cancel.
- `positions-table.ts`: `app-positions-table` with live Last and P&L.
- `decision-record.ts`: `app-decision-record` with Load more.
- `data/trade.service.ts`: component-provided store (10 s poll, reloads, decisions paging).
- `util/client-order-id.ts`: per-submission UUID, reused on retry.
- `util/live-position.ts`: applies stream prices to positions.
- `util/merge-decisions.ts`: merges decision pages.
- `util/refusal-message.ts`: §7.5 refusal copy by code.
- `util/ticket-copy.ts`: ticket hints and labels from `venue_rule`.
- `util/fill-note.ts`: fill-note copy.
- `util/order-view.ts`: order and decision row view models.
- Tests: `decision-record.spec.ts`, `open-orders.spec.ts`, `order-ticket.spec.ts`, `positions-table.spec.ts`, `trade.spec.ts`, `data/trade.service.spec.ts`, and in `util/`: `client-order-id.spec.ts`, `fill-note.spec.ts`, `live-position.spec.ts`, `merge-decisions.spec.ts`, `order-view.spec.ts`, `refusal-message.spec.ts`, `ticket-copy.spec.ts`.

**Overview (`src/app/pages/workspace/feat-overview/`)**
- `overview.ts`: places the hero and KPI strip above Market watch.
- `portfolio-hero.ts`: `app-portfolio-hero`.
- `equity-chart.ts`: `app-equity-chart` inline SVG with a keyboard tooltip.
- `kpi-strip.ts`: `app-kpi-strip`.
- `data/portfolio.service.ts`: component-provided `GET /portfolio?period=` store.
- `util/chart-geometry.ts`: chart scaling and paths.
- `util/portfolio-view.ts`: hero and KPI view model.
- Tests: `overview.spec.ts`, `portfolio-hero.spec.ts`, `equity-chart.spec.ts`, `kpi-strip.spec.ts`, `data/portfolio.service.spec.ts`, `util/chart-geometry.spec.ts`, `util/portfolio-view.spec.ts`.

**Styles**
- `src/styles/tailwind/theme.css`: `--text-metric`, `--tracking-hero` and the three hero size tokens.
- `src/styles.css`: imports the new component styles.
- `src/styles/components/section.css`: `.section-head`.
- `src/styles/components/metric-card.css`: KPI cards.
- `src/styles/components/range-switch.css`: the period toggle (light-theme contrast fix, ORCH-18).
- `src/styles/components/portfolio.css`: the hero and chart.
- `src/styles/components/trade.css`: the Trade layout, ticket and tables.
- `src/styles/components/table.css`: `.second` / `.status-line` and table tweaks.

**End-to-end (`e2e/`)**
- `e2e/playwright.config.mts`: new specs and the live-data gate.
- `e2e/src/support/trade.ts`: mocked trade/portfolio API and page helpers.
- `e2e/src/support/screens.ts`: capture, contrast and axe helpers extended to Trade and Overview.
- `e2e/src/support/market-watch.ts`: market-watch mocks updated for the portfolio routes.
- Tests in `e2e/src/`: `trade.spec.ts`, `overview-portfolio.spec.ts`, `paper-orders.spec.ts` (gated live journey), `journey.spec.ts`, `market-watch.spec.ts` (ORCH-22), `shell.spec.ts`, `viewport.spec.ts`.

**Not changed:**
- `tidewatch-specs` (not a git repo; no spec edits).
- `tidewatch-apis` (not a git repo; FR-SIM-DOC-002 deferred).
- `DESIGN.md` (unchanged at merge; its refresh is FR-SIM-WEB-010, running on branch `codex/forge-sim-606762cb-design` from `cfed50e`).

## Test plan

### Commands (all local; there is no CI, D4)

- **Migrations:** `make migrate-validate`; `make check-disposable-db` (throwaway TimescaleDB, PASS 848/0).
- **Service:** `make ci` (vet, test-race, build; Docker-free); `make test-integration TIDEWATCH_MIGRATIONS_DIR=<migrations checkout>`.
- **Bot:**
  - `pnpm nx run-many -t lint test typecheck build`.
  - `TIDEWATCH_MIGRATIONS_DIR=<checkout> bash scripts/sql-integration.sh`. Sim integration specs run last. They leave `zztest-sim-*` users and `ZZTEST sim *` bots behind, because decisions are append-only (R28).
- **Web:** `pnpm nx run-many -t lint test build` (about 1,835 unit tests at the last fix round); mocked Chromium Playwright (170/170 at `a4c808b`); capture/contrast/axe specs.

### Named acceptance tests (do not rename; verification greps for them)

- **Service:**
  - `TestCodes_Contract`, `TestError_TradeDetails_InBody`
  - `TestFixture_PinnedHash`, `TestFixture_Sequence_TwentyOrders`
  - `TestOrders_Place_Validation`, `TestOrders_Place_Idempotent`, `TestOrders_Place_Hours`, `TestOrders_ManualFill`, `TestOrders_Cancel_RacesFill` (22 rounds, one winner, no deadlock), `TestOrders_Estimate_SameRefusals`
  - `TestRouter_NoDecisionMutation`, `TestDecisions_DirectSQLMutationFails`
  - `TestPortfolio_MatchesSQL` (against `test/sql/portfolio_*.sql`)
  - `TestLogs_NoSecrets`, `TestMetrics_TradingSeries_ScrapeAfterOrders`
  - `TestDriver_FakeService_TwentyOrders`, `TestVerification_FillsSQL`
  - `TestTrade_FirstAccessCreatesOneBot`, `TestTrade_ConcurrentFirstAccess`
  - `TestContract_RequiredSchemaVersion`, `TestReady_SchemaWait`
- **Bot (Vitest titles, exact strings):**
  - `fills a market order on the next bar once`, `fills a limit order when a bar trades through`
  - the PTT.BK daily-only spec
  - `futures margin and settlement`, `account invariants after each fill`
  - `marks hourly, on fill and at day end`, `back-fills outcomes once`
  - `shared-fixture.spec.ts` (the full C3 sequence against the pinned fixture)
  - `pg-store.int.spec.ts`: the FOR SHARE in-flight-fill wait, more concurrent fills than the pool size, and re-mark replay of the attempt-1 backdated case
  - `remark.spec.ts`
- **Web:**
  - Vitest specs per component, parser and util.
  - Mocked Playwright `trade.spec.ts` and `overview-portfolio.spec.ts`.
  - `paper-orders.spec.ts`, gated by `E2E_LIVE_MARKET_DATA`, which must run only after E2E-001 completes (ORCH-29).

### Acceptance status (PRD §9)

**Merge-gating IDs:**
- FR-SIM-MIG-001…003, SVC-001…013, BOT-001…009, WEB-001…009 and DOC-001 were verified by step contracts and reviews.
- WEB-001/006/007/009 have rendered evidence from a local build against a mocked API: axe 0 across 16 runs, minimum contrast 4.67 over 110 measurements, no horizontal scroll at 390/600/1080/1100/1440. The design reviewer approved in round 4. Fresh-account and populated states were mocked (ORCH-29). Evidence: `evidence/root/preview/web/r2/`, `r3/`.

**Preview runs** (isolated DB, reset 2026-10-08T14:57Z; revisions migrations `ffe6c27`, service `8770fde`, bot `c37d89a`, web `a4c808b`, which are the merged heads):

| ID | Status | Detail / evidence |
|---|---|---|
| FR-SIM-E2E-001 | **In progress** | Fresh account; watchlist default eight, benchmark 8 × 0.125. Run 1 filled o01 (NVDA buy 10 @236.51), o02 (AAPL buy limit 5 @337.52) and o09 (NVDA sell 4 @236.08). o03 (PTT.BK) was refused with `venue_closed`, `next_open_at` 2026-10-09T03:00Z, and the other 16 rows wait behind it in sheet order. Next windows: SET Fri 2026-10-09 10:00–16:40 Bangkok (o03, then the rows behind it including the MTS manual fills o07/o19) and Mon 2026-10-12 (o17). The PTT.BK chain spans about 4 SET trading days. Evidence: `evidence/root/preview/e2e/e2e-001-status.txt`, `sim20-run/RERUN.md`, `sim20-run/transcript.txt`. Attempt 1 on bot `2ff79c4` is archived (`e2e-attempt1-old-bot/`). |
| FR-SIM-E2E-002 | **Unverified (partial pass)** | 44/44 checks pass: `GET /trade` against SQL, and every ledger row recomputed as of its `ts`. No late or backdated fill occurred that night (US fills came about 60 s after the bar), so the ORCH-31/33 re-mark path was not exercised on the preview (0 re-mark logs). It is covered by bot unit and integration specs that reproduce the attempt-1 case. Re-run the checker after the driver's MTS fills, comparing against the bot-rewritten manual-fill row with decimal equality (marks `fx` `33.5` vs `33.50`, FU-12). Attempt 1 failed on bot `2ff79c4`; that defect was fixed by ORCH-31/33. Evidence: `e2e-002-marks-vs-trade.txt`. |
| FR-SIM-E2E-003 | **Passed** | 1w/1m/3m series equal the committed SQL (decimal). The benchmark is exact at the initial and 16:00 hour marks. Fill-mark benchmarks are indicative only, because `px:last` is not stored. Evidence: `e2e-003-portfolio-benchmark.txt`. |
| FR-SIM-E2E-004 | **Partly passed** | Five refusals with nothing written: `manual_fill_required` ×2, `manual_fill_not_allowed`, an MTS limit, and SET `venue_closed` + `next_open_at`. Unverified: US outside session (the Webull overnight session reads open), BTC/THB at 03:00 Bangkok, TFEX outside hours, and the driver's manual fills. Evidence: `e2e-004-hours-manual-fill.txt`. |
| FR-SIM-E2E-005 | **Pending** | Needs `r_1h` / `r_1d` at +1 h and +1 session on preview decisions, then a second sweep that changes nothing. |
| FR-SIM-WEB-010 | **In progress** | `DESIGN.md` refresh (forge-setup-impeccable) after visual verification. |
| FR-SIM-DOC-002 | **Deferred** | `tidewatch-apis` is not a git repository (ORCH-3). |

Metrics excerpts: `evidence/root/preview/e2e/metrics-excerpts.txt`. There is no dedicated re-mark metric; log counts were used. The scheduled task `tidewatch-slice2-verify-merge` re-runs the driver and checkers in the next market windows. It only verifies and reports: it never merges and never cleans up.

### Manual reproduction

1. Run the 20-order sheet on a fresh account only; the driver refuses an account that already has orders: `verification/sim-20-orders.sh`, which resumes from its `state.json` when re-run in each market window.
2. Run `verification/sim-20-fills.sql` with `psql -q` against the isolated database.
3. Run the script once more with `-fills`, which re-fills the output columns from the stored fills with the C5 code and compares them with `GET /trade`. Exit 3 means the comparison failed. A 401/403/429 response stops the run.

The driver reads the session cookie only from a file and never prints it.

## Open questions

Follow-ups recorded in state.json:
- **FU-1:** The service's calendar-free daily close rule could look ahead up to 1 h for a US-hours daily-only instrument. None is seeded today.
- **FU-2:** Tighten the `venue_rules` CHECK so a spot rule cannot carry margin without a multiplier (later migration).
- **FU-3:** Give the web `paper-orders.spec.ts` a separate opt-in beyond `E2E_LIVE_MARKET_DATA`.
- **FU-4:** Per-code web refusal copy when `insufficient_cash` / `position_limit` / `exposure_limit` / `insufficient_position` arrive without `details`. This needs PRD §7.5 copy.
- **FU-5:** Web:
  - keep the range switch visible when a period switch keeps failing;
  - trailing zeros count as decimals in the client check;
  - weekday ambiguity in *Placed* for orders older than 6 days;
  - the Open orders section is absent while loading (layout jump).
- **FU-6:** Web radius literals (12/14/10/7/5/4px) beside the `--r` / `--r-lg` tokens.
- **FU-7:** C6 should pin the 5m bar end (the bot uses `ts+5min`, the service would use +1 min). No 5m instrument is seeded.
- **FU-8:** A partial index matching the bot's wider outcome-pending predicate. Today it is a per-minute scan of `decisions`, trivial at current volume.
- **FU-9:** The service should refuse a backdated manual fill dated before the open position's `opened_at` or the latest fill on the instrument.
- **FU-10:** The service's strict JSON decoder accepts case-insensitive and duplicate keys.
- **FU-11:** `GET /portfolio` `EquityPath` reads the whole ledger; aggregate in SQL later.
- **FU-12:** The service should write `ledger.marks` `fx` as the stored rate text, to match the fixture form (`33.5` vs `33.50`, decimal-equal today).
- **FU-13:** Web: MTS option text is truncated in the 300px instrument select (A7), and Open orders Status text sits partly under the pinned Cancel column at 1440 (A8).
- **FU-14:** Bot: a flaky `market-data` `http.spec` timing test (pre-existing).
- **FU-15:** An index on `fills(created_at)` for the re-mark horizon scan, and collapsing fills per bot (or a lateral `LIMIT 1`) in `STALE_LEDGER` (security R4-1).
- **FU-16:** A dedicated bot re-mark metric instead of log lines.

Other unresolved items:
- **Intent assumptions.**
  - A1 (SET commission) and A2 (GO margin) were settled by OWNER-1. The margin changes monthly and needs a data migration each time.
  - A3 (synthetic bars reach the sink's `persisted` event) is covered either way by the 5 s sweep.
  - A4: MTS hours 07:00–03:00 Bangkok are still the PRD value until the owner confirms them.
- **Owner veto window on OWNER-1.** The values were adopted on the orchestrator's recommendation, with the owner able to veto.
- **Bot residuals (ORCH-31/33):**
  - The worker, service and database must share one clock.
  - A re-mark replay uses the current futures margin rule.
  - A backdated reduce is replayed as recorded.
  - A long re-mark holds a gate slot.
- **Preview-only coverage gaps.** Until E2E-001/002/004/005 finish, these paths have test evidence but no preview evidence:
  - the futures open/close chain;
  - the MTS manual fills and the bot's rewrite of their marks;
  - limit fills on SET;
  - BTC/THB fills at 03:00;
  - outcome back-fill at real offsets.
- **Three bot comments still say "nine" collectors** (`market-data/src/runtime/types.ts:76`, `metrics.ts:7`, `status/status-publisher.ts:115`). They were left as PRD-stable text.

## Cross-cutting links

- [[centralized-migrations]]: migration E, the required schema version and the destructive down.
- [[market-timeseries]]: `candles`, `candles_eod` and the hypertable conventions the ledger follows.
- [[instrument-master]]: venues, calendars, `tick_size` / `lot_size` and `base_timeframe = '1d'` for PTT.BK.
- [[market-data-worker]]: runners, advisory locks and the bar sink `persisted` event that triggers fills.
- [[redis-market-contract]]: `px:last` freshness (60 s rewrite, 120 s bound) used for hours and marks.
- [[gold-feed-xaut-proxy]]: XAU/USD priced from Binance TH XAUT and the USDTTHB proxy for USD/THB.
- [[request-protection]]: CSRF, the gated group and the strict body limits on the new POSTs.
- [[auth-model]]: the session user who owns the `me` bot, and the admin and forced-change gates.
- [[realtime-websocket]]: the price stream that updates Positions' *Last* (nothing new on `/ws`).
- [[design-system-decisions]]: new tokens and reusable classes pending the `DESIGN.md` refresh.
- [[forge-preview-gateway]]: the isolated preview where E2E verification runs.
- [[market-data]]: the slice-1 Market watch that Overview now places below the portfolio hero.
