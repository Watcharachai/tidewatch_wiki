# Paper trading: order path, fill model and ledger

**Summary**: How Tidewatch simulates trading on paper. The Go service is the trust boundary for user orders: it validates each order, then writes the `pending` order and its decision row in one transaction. Since slice 2b (2026-10-09) there is a second intake: the zone-transition bot places its own orders inside tidewatch-bot with the same checks, arithmetic and lock order (ZB5). The bot's `sim` runner fills every pending order on stored bars, marks the ledger, values the benchmark and back-fills outcomes. The two sides share only the schema and Redis, plus pinned fixtures, pinned SQL and one mark-price rule, so they compute the same numbers. Since the signals page (slice 4, 2026-10-12), a user order may cite one signal through `decision_ctx`. The service checks the citation right after the instrument checks and refuses a mismatch with `422 signal_not_applicable` (see [[signal-cited-orders]]). Since slice 6 (bots, merged 2026-10-21, not deployed), every created or cloned bot gets its own paper account, the general engine's manager and guard place orders through the same bot-side intake (the C4 lock order is unchanged), the close stamp binds the closing decision's own exit reason (C4''), and a user order or skip may cite a bot's candidate, checked by the service right after the instrument checks (`422 candidate_not_applicable`). **Since slice 7 (statistics, merged and deployed 2026-10-27),** Stats reads these tables to grade each bot version and changes none of them. Its check of assumption A1 found that `positions.realized_thb` is **already net of both fees**, so a closed position's net result is `realized_thb`, never `realized_thb − fees_thb`. **Since accounts and roles (merged and deployed 2026-10-29),** every account belongs to a person created by an operator. `EnsureBots` and `POST /bots` take the starting capital from the person's plan (`founder`: ฿1,000,000), and disabling a person pauses their auto bots through the Pause path. The order path, fill model and ledger are unchanged.

**Sources**: `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md` (contract C11 and the watch write only); `raw/2026-10-12-signals-page.md` (the signal check and the recommendation only); `raw/2026-10-21-bots.md` (the general engine's intake, C4'', per-bot accounts and the candidate check only); `raw/2026-10-27-statistics.md` (A1, the Stats reads of positions, ledger and `portfolioAt` only); `raw/2026-10-29-accounts-roles.md` (who owns an account, the plan's starting capital and the disable pause only)

**Last updated**: 2026-10-29

---

## One order path, split ownership (SIM1)

- **Service.** Validates the order. Writes the `pending` order, its [[decision-record]] row, `reserved += required` and the `order_placed` audit event in one transaction.
- **Bot.** The `sim` runner fills pending orders on bars.
- **Manual MTS orders** are filled synchronously by the service at the price and time the user entered (`tag = 'manual_fill'`), in the same transaction, with their own `fill` ledger mark.
- There is no HTTP between service and bot (see [[redis-market-contract]]).
- **Since slice 2b**, the bot also places orders for its zone-transition bot through a second intake that mirrors the service's (see below). User orders still go only through the service.

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design; raw/2026-10-09-zone-transition-bot.md §Concept, ZB5)

## The `me` bot and account (SIM12, SIM13.10)

- Each user gets one manual bot (unique partial index `bots_owner_manual_key`). It is created lazily on the first Trade or Overview access, in its own committed transaction under an advisory lock.
- Starting values: ฿1,000,000 THB, a 25% per-instrument limit and 100% total exposure. Since accounts and roles the starting capital is the person's plan's `starting_capital_thb` (฿1,000,000 on `founder`). The literal left `internal/services/trading` (source: raw/2026-10-29-accounts-roles.md §API, Product contract changes).
- There is no reset endpoint. A fresh database is the reset.
- Nothing is seeded for it. In slice 2 that was because the admin user was created at service bootstrap. **Since accounts and roles (2026-10-29) no user is bootstrapped.** The seeded admin was backfilled to a plain person and kept its `me` account, and every new person is created by an operator in the [[operator-console]]. Creating a person makes no bot, account or watchlist; `EnsureBots` makes them on the person's first product request (source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built; §API, People, Writes).
- **Benchmark.** The user's watchlist at account creation, tradable classes only, equal weight, never rebalanced, valued in THB. It is snapshotted into `benchmark_members` (`weight`, `start_px`, `start_usd_thb`). With the default eight watchlist instruments, that gives 8 × 0.125.

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design; §Database; §Test plan, E2E-001)

**Since slice 2b, `me` is one of two bots.** The service now creates Slack Water, the zone-transition bot, beside `me` in the same lazy step (`EnsureBots`). Slack Water has its own ฿1,000,000.00 paper account, benchmark snapshot and initial `fill` mark. `EnsureAccount` is now "`EnsureBots`, then return the manual bot", so the slice-2 routes are unchanged. Overview and Trade still show only `me`. `Position.opened_by` is the owning bot's name: "Me" on `/trade`, "Slack Water" on the bot detail. Slice-2 tests that assumed one bot per user were re-scoped to the manual bot (R8 / R15). See [[bot-versions-and-runs]] and [[zone-transition-bot]] (source: raw/2026-10-09-zone-transition-bot.md §API, Lazy creation and Changes to slice-2 routes; §Concept, Plan resolutions, Service).

## Trading hours (SIM3)

- The service has no calendar logic. It reads session state from `px:last` (see [[redis-market-contract]]).
- A closed session returns `venue_closed` with `next_open_at`.
- An open session with a stale or missing price returns `price_unavailable`. "Fresh" means `px:last` is not stale and `updated_at ≥ T − 120 s`.
- Crypto is always open. Manual orders skip only the stale check.

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design; §API, Intake order)

## Intake order (`POST /orders`)

The first failed check answers the request, and nothing is written:

1. Strict body decode (400 `invalid_request`; an unknown field gives `unknown_field` without naming the key).
2. Lazy account creation.
3. Account row `FOR UPDATE`.
4. Idempotency on `(bot_id, client_order_id)`.
5. Instrument checks: `unknown_instrument`, `instrument_inactive`, `instrument_not_tradable`.
6. Lot and tick size (400) (see [[instrument-master]]).
7. Manual venue: `manual_fill_required`, `manual_fill_not_allowed`. A manual limit order is a 400.
8. Hours and price from `px:last`.
9. Side check: `insufficient_position` with `held`.
10. Money: `insufficient_cash`, `position_limit` / `exposure_limit`.
11. Write the decision (with `px_at_decision` and `market_state` from the latest strip-timeframe `indicators` row), the order, the reservation and the audit event.

`POST /orders/estimate` runs the same `check()` read-only (source: raw/2026-10-08-simulation-engine.md §API, Intake order).

**The signal check (slice 4, FR-SP-SVC-007).**
- Since tidewatch-service PR #10 (merge `8b18486`), step 1's strict decode also validates `decision_ctx`. It may cite exactly one hyphenated signal UUID, with a `followed_recommendation` flag. Anything else is `400 {field: decision_ctx, reason: invalid}`.
- `checkSignal` runs inside `check()` right after step 5's instrument checks, and before lot and tick, hours, side, money and any write (R12). Placement and the estimate therefore refuse identically.
- An unknown signal, or one that names another instrument, gets `422 signal_not_applicable` (`details.reason` `unknown` or `instrument_mismatch`). The refusal counts as `orders_placed_total{result="rejected"}` and is logged `order_rejected`.
- The estimate never carries `decision_ctx` from the web and never writes. An idempotent replay answers the stored order, whatever `decision_ctx` says.
- **The read-only recommendation** in a signal's detail sizes 10% of the manual bot's equity. It reuses `GET /trade`'s valuation (A1 held in planning; `trade.go` shares it through `nowMarks`), and `internal/trading/rules.go` gained `FloorQty`.
- What the decision row records is on [[signal-cited-orders]] and [[decision-record]].

(source: raw/2026-10-12-signals-page.md §API, Order path; §Concept, Plan resolutions, Service R11/R12; §Test plan, Assumption outcomes A1; §Files touched, tidewatch-service)

## Second intake: the bot's `placeAction` (slice 2b, ZB5)

The zone-transition bot does not call the service. Its intake in `packages/bots` runs the service's check order, with the shared arithmetic and the C4 lock order, in one transaction with `SET LOCAL statement_timeout` 10 s. Rejected alternatives were a service endpoint with a service token (it breaks "no HTTP between them" and adds a secret) and a Postgres function (a large refactor). The accepted cost is a second implementation of the money and limit checks, pinned by a scenario fixture (`fixtures/bots-intake.v1.json`, 30 hand-derived scenarios).

Session and price are checked first, outside any transaction (see [[zone-transition-bot]]). Then:

1. `paper_accounts … FOR UPDATE` is the first statement.
2. Re-read the bot's status.
3. Idempotency: `client_order_id`, then the decision key.
4. Side.
5. `equity_now` via `valueAccount`, with the rule-4 USD/THB for USD spot. A missing USD/THB rate rolls back and counts as a `price_unavailable` deferral.
6. Quantity: `budget = round2(equity_now × 0.10)`. The estimate price is last plus slippage against a buyer. `qty` is rounded **down** to `lot_size`, else to `QtyDecimals` (8 for US shares, 0 for SET, the lot digits for crypto).
7. Limits, collected in order: `insufficient_cash`, `position_limit`, `exposure_limit`, `max_open`; `qty_below_minimum` when `qty ≤ 0`. If any applies, the intake writes a `skip` decision with those reasons and a `decision_skipped` event instead of an order.
8. Writes: the on-demand run, the decision (`actor = bot`, `loop = manager`, `run_id`, `bot_version`, `market_state`, `policy_result`), the pending market order (`placed_by_user_id` NULL, `reserved_cash` = required for an entry and 0 for an exit), `reserved += required`, and the `order_placed` event.

- A replay hits `ON CONFLICT (bot_id, client_order_id) DO NOTHING`, rolls back and reports `already_placed`.
- **`client_order_id`.** A UUIDv5 in namespace `fef2c136-2402-56d4-a3a7-055c50a372d0` of `{bot_id}|{instrument_id}|entry|{zone_run_started_at}` or `{bot_id}|{instrument_id}|exit|{position.opened_at}`. Instants are RFC 3339 UTC, with a millisecond fraction only when it is non-zero (R7).
- **No re-implemented price rules.** The intake calls `packages/sim`'s `marketPrice`, `divFloor`, `valueAccount` and `readMarkContext` (bot R16). C3, C5, C6 and C7 are reused unchanged.
- **Evidence.** Integration tests show the account lock is taken first, a `NOWAIT` probe gets 55P03 while it is held, and a bot entry and a sim fill serialise in both orders. Code review re-derived NVDA 187.54 → 15.91700238 shares and PTT 34.28 → 2917 shares by hand.
- **Not yet seen live.** No bot order had been placed or filled on any stack when the source was written (FR-ZB-E2E-001/002 unverified).

(source: raw/2026-10-09-zone-transition-bot.md §Concept, Chosen design ZB5, Cross-project contracts and Plan resolutions, Bot R5; §API, Bot runtime, Intake; §Test plan, Assumption outcomes and Acceptance status)

## Slice 6: the general engine's orders, per-bot accounts and the candidate check

Slice 6 merged on 2026-10-21 (tidewatch-service #12 `9f1f324`, tidewatch-bot #10 `81133bf`); it is not deployed (see [[bots]]).

- **One paper account per bot (PD9).** `POST /bots` and `POST …/clone` create the bot, its own paper account, a benchmark snapshot and the initial mark in one transaction. Starting capital defaults to ฿1,000,000 (since accounts and roles, to the plan's `starting_capital_thb`, whose CHECK also requires ≥ 10,000) and must be at least ฿10,000.00. Each bot's figures and 30-day sparkline come from its own account's `1m` portfolio and `day_end` marks (see [[bot-versions-and-runs]]).
- **Manager entries through the intake.** The general engine's manager enters through the existing bot-side intake (above) with `client_order_id = UUIDv5("{bot_id}|{instrument_id}|candidate|{candidate_id}")`, copying the proposing decision's `signal_ids`, `signal_snapshot` and `model` (ORCH-9a). Sizing is by `p` within the allocation (PD4), capped by the allocation room net of the entry's own fee, `room / (1 + allocation × fee rate)`, with pending buys counted (ORCH-9c). *Add*, *trim* and exits go through the same path.
- **Direct entries (S7)** for rules-only configs keep the 2b idempotency key and skip reasons, creating the candidate `proposed → entered` and the order in one intake transaction.
- **Guard closes** are protective market orders placed through the intake with `loop guard`. The guard's pause and the probation flip are short transactions of their own, never under an account lock.
- **Restart safety (FR-BT-E2E-002).** On the preview, a guard close was written and its sell placed at 04:46:14.84Z, and the bot restarted at 04:46:15.3Z; afterwards there was one close decision, one sell and two distinct `client_order_id`s, with no duplicate.
- **C4'' in `packages/sim` (S9).** `closeStampReason` binds `policy_result->>'exit_reason'` (`stop`, `invalidation`, `zone`, `horizon`, `protect`); without it `rule = 'exit'` binds `zone` and anything else `user`. `CloseStampSQL` is unchanged; only the bound value changes, and an unknown value throws `RangeError`. Bot S8 changed `packages/sim`'s store, pg-store and fill pass for it (see [[decision-record]]).
- **The candidate check on the service (S9).** `check()` reads a cited candidate right after the instrument check and before everything else, for placement, estimate and skip alike. A refusal is `422 candidate_not_applicable {reason: unknown | instrument_mismatch | closed}` and writes nothing; `signal_ids` must be `[]` or the candidate's ids as a set. On an order, `followed_order_id` is set as the transaction's last write, when still null. Details on [[signal-cited-orders]].
- **Unchanged:** the fill model, the C4 lock order, C3 and the indicator job.

(source: raw/2026-10-21-bots.md §API, Behaviour worth knowing, Create and clone and Candidate citation; §The bot engine, Manager, Guard and C4''; §Concept, Owner decisions PD4/PD9 and ORCH-9; §Test plan, The E2E checks; §Files touched, Not changed)

## Fill model (SIM2, SIM5, SIM6, SIM13.3)

- **Market orders** fill at the open of the first closed 1-minute bar after placement, plus slippage.
- **Limit orders** fill on the first later bar that trades through: at `min(open, limit)` for a buy and `max(open, limit)` for a sell. They are good till cancelled. They reserve their estimated cost plus fees (or the margin) against available cash, and they can be cancelled while pending.
- No partial fills: `fills.order_id` is UNIQUE.
- **Daily-only instruments** (`PTT.BK@webull`, base `1d`) fill at the next session's open, once that session's `candles_eod` row lands (see [[market-timeseries]]).
- **Futures** (`GO@tfex`) use a margin model:
  - the initial margin is reserved from cash;
  - P&L is Δprice × 300 × contracts, in THB;
  - sell-to-open is allowed;
  - there is no variation settlement and no maintenance call.

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design)

## Fees, slippage and margin: `venue_rules` (SIM8)

The service estimate and the bot fill both read seeded `venue_rules` rows. Each row cites a `source`. If a number changes, that is a data migration, and existing fills keep the numbers they used (in `fee_detail`).

| venue / calendar | settlement | commission | slippage | other |
|---|---|---|---|---|
| `webull` / `us-equities` | spot | 0.0010 + 7% VAT | 2 bp | sell fee 0.000195 per unit, cap 9.79 |
| `webull` / `set` | spot | **0.00047** + 7% VAT (OWNER-1) | 10 bp | — |
| `binance-th` / `crypto` | spot | 0.0025 | 5 bp | — |
| `oanda-demo` / `gold-23-5` | spot | 0 | 3 bp | the OANDA paper venue. Priced from Binance TH `XAUTUSDT`, so no OANDA keys are needed (see [[gold-feed-xaut-proxy]]) |
| `tfex` / `tfex` | futures | ฿210 per contract | 1 tick | multiplier 300, initial margin **฿137,550.00** (OWNER-1, changes monthly) |
| `mts` / `mts` | spot, manual | 0 | 0 | — |

(source: raw/2026-10-08-simulation-engine.md §Database, Seeds; §Concept, OWNER-1)

## Cross-project contracts (C3–C9)

These contracts are the source of truth for both the bot and the web (source: raw/2026-10-08-simulation-engine.md §Concept, Cross-project contracts).

- **C3, shared fixture.**
  - The canonical copy is the service's `internal/trading/testdata/sim-arithmetic.v1.json`. The bot holds a byte-identical copy at `packages/sim/fixtures/sim-arithmetic.v1.json`.
  - Both test suites pin sha256 `ff3564c898741e48dea08ee11eaf33873c01d2d08cef655242015d7f7b208283`. Changing the fixture is a contract change in both repos at once.
  - It holds 20 orders, with anchors computed independently in Python. For example, at mark m2: cash ฿568,272.57, equity ฿1,031,518.97.
- **C4, locking and pinned SQL.**
  - Lock order: account row first (`paper_accounts … FOR UPDATE`), then the order, then positions, fills, ledger and decisions.
  - The fill guard, cancel guard and close stamp are pinned text: `FillGuardSQL`, `CancelGuardSQL`, `CloseStampSQL`.
  - `orders.reserved_cash` never changes after placement.
  - Invariant after every commit: `paper_accounts.reserved = Σ holds of pending orders + Σ margin_reserved of open positions`.
  - Hour and day_end marks take the account `FOR SHARE`. Service "now" reads run in one `REPEATABLE READ READ ONLY` snapshot.
- **C5, exact arithmetic.**
  - Go uses `math/big` rationals and TypeScript uses decimal strings.
  - Values are rounded half away from zero, only where they are stored or sent. THB amounts use `round2`, and `avg_px` keeps 8 fraction digits.
  - A futures reduce releases `round2(margin_reserved × q / qty)`, not the PRD's `initial_margin × q`.
  - `equity = starting_capital + Σ fills.realized_thb + unrealized` holds exactly.
  - **Fees are inside `realized_thb` (checked by slice 7's A1).** Every fill subtracts its fee from realized P&L, so `positions.realized_thb` is already net of both the opening and the closing fee; see "Read by Stats" below.
- **C6, mark-price rule (ORCH-8).**
  1. A stored close counts once its bar has ended: `ts + 60 s ≤ t` for 1-minute bars, the session end `≤ t` for daily-only bars. The 24 h window is measured on bar end.
  2. `px:last` counts when `ts ≤ t`, it is not stale, and `updated_at ≥ T − 120 s`. The 120 s bound comes from the status publisher's 60 s rewrite interval.
  3. A position with no price falls back to its last known mark, then to its latest fill price.
  4. USD/THB comes from `USDTTHB@binance-th`, then `USDTHB@oanda-demo`, then the last ledger row's rate.
  5. A benchmark member with no price uses its latest close with no window, then its start price.
  6. `ledger.marks` is `{instrument_id: {px, fx, value_thb}}`, stored as decimal strings.
- **C7, wire formats.**
  - THB amounts are 2-dp strings. Percentages are 4-dp, in percent units.
  - Outcome ratios travel as 6-dp ratios, never as percent (ORCH-6).
  - `fill_note` is one of `next_bar`, `next_session_open`, `manual`, `futures_margin`.
  - `qty_unit` is one of `shares`, `units`, `baht`, `oz`, `contracts`.
- **C8, C9.** C8 adds nine error codes with typed details. C9 covers the decision action and direction, and a side check that stays correct across pending orders.
- **C4', parameterised close stamp (slice 2b).** The only change from C4 is that the literal `'user'` became `$4`:

  ```sql
  UPDATE decisions
     SET exit_reason = $4, closed_at = $3
   WHERE bot_id = $1 AND instrument_id = $2
     AND action IN ('buy', 'add', 'sell')
     AND exit_reason IS NULL AND closed_at IS NULL
     AND decision_id IN (SELECT decision_id FROM orders
                          WHERE bot_id = $1 AND instrument_id = $2 AND status = 'filled');
  ```

  - The bot's `CLOSE_STAMP` is the same text without the final `;`.
  - `$4 = 'zone'` only when the closing order's decision has `actor = 'bot'` and `policy_result->>'rule' = 'exit'`. The sim fill pass reads this under the account lock, after the fill guard and before the stamp.
  - The service's `StampClose` keeps its signature and always binds `'user'`. `StampCloseReason` exists so an integration test can prove that `'zone'` binds.
  - `decisions.exit_reason` already allowed `'zone'` (migration E), so C4' needed no schema change. The service and bot PRs had to merge together.
- **C10, bot version fixture (slice 2b).** A byte-identical `bot-version.v1.json` in the service and the bot, pinning the canonical-JSON hash of the v1 config. Details on [[bot-versions-and-runs]].

(source for C4' and C10: raw/2026-10-09-zone-transition-bot.md §Concept, Cross-project contracts)

- **C11, bot watch-entry fixture (bot-activity, 2026-10-10).** C11 joins C3 and C10 as a byte-pinned shared fixture: `bots-watch-entry.v1.json`, byte-identical in the service and the bot, pins the per-instrument WatchEntry shape and the fourteen-verdict table. Details on [[bot-watch-verdicts]].
- **The watch write stays outside C4.** The bot's `bot_watch` write runs after the run is finished, as one statement outside any transaction and outside the intake. Its FK checks take `KEY SHARE` on the `bots` and `instruments` rows only, and it never touches `paper_accounts`. An integration test proves it completes while another session holds `paper_accounts … FOR UPDATE`. C3–C10 and the C4 lock order are unchanged, and `place.ts` and `intake.ts` are byte-identical.

(source: raw/2026-10-10-bot-activity.md §Concept, Cross-project contracts; §API, Bot runtime, C4 untouched and Unchanged by contract; §Concept, Plan resolutions, Bot R-BA7/R-BA8; §Cross-cutting links)

- **Slice-6 contracts (2026-10-21).** **C4''** (the close stamp binds the closing decision's `policy_result.exit_reason`; above). **C11'** (`bots-watch-entry.v2.json`, 23 verdicts; see [[bot-watch-verdicts]]). **C12** (`bot-version.v2.json`, byte-identical in web, service and bot; see [[bot-versions-and-runs]]). **C13** (the five Elliott fixtures and `waves-tunables.v1.json`, byte-identical in service and bot; see [[elliott-regime-labeller]]). C3, C10 and the C4 lock order are unchanged (source: raw/2026-10-21-bots.md §Concept, ORCH-2; §Operations; §Files touched, Not changed).

## Ledger and marks (SIM4)

- `ledger` is a TimescaleDB hypertable on `ts`: 28-day chunks, `create_default_indexes => false`, no columnstore and no retention.
- Primary key `(bot_id, ts, kind)`. `kind` is `hour`, `fill` or `day_end`, written at every UTC hour, after every fill, and at 00:00 Bangkok.
- Readers order rows by `(ts, kind)`, with `fill < hour < day_end` (R16).
- Bangkok is a fixed UTC+7.
- `max_drawdown_pct` and `peak_equity` cover ledger marks only, not the live "now" point.

(source: raw/2026-10-08-simulation-engine.md §Database; §Concept, Recorded deviations)

**Re-marking (ORCH-31, found on the preview by FR-SIM-E2E-002).** Fills can commit out of `filled_at` order: US bars arrive about 15–17 min late, and manual fills can be backdated. The ruling makes the bot the only re-marker:
- Every mark is computed from the account state as of its `ts` (`as-of.ts`).
- A durable `staleLedger` query flags rows that were computed before an earlier fill had committed.
- A pass every 15 s rewrites the flagged rows in `(ts, kind)` order (`remark.ts`).
- The service is unchanged. The bot rewrites the service's manual-fill `fill` row 30–45 s later.

ORCH-33 hardening:
- At most 500 rows per account per sweep, and accounts rotate between sweeps.
- The stale scan is bounded to fills inserted within the last 7 days, as a range on the `fill_id` uuidv7 key.
- Rules 3 and 4 read history strictly before `(t, kind)`.

(source: raw/2026-10-08-simulation-engine.md §Concept, Bot deviations ORCH-31 and ORCH-33)

**Accepted residuals.**
- The bot, service and database must share a clock.
- A replay uses the current futures margin rule.
- A backdated reduce replays as recorded.

(source: raw/2026-10-08-simulation-engine.md §Concept, Accepted residuals)

## The bot's `sim` runner

The runner lives in `packages/sim`. It is the tenth `COLLECTOR_NAMES` entry, on by default, holds the lock `runner:sim` and has no venue budget (see [[market-data-worker]]). It runs four loops:

| Loop | Cadence |
|---|---|
| Fill sweep | Every 5 s, plus a pass on each bar-sink `persisted` event |
| Hour and day_end marks | 10 s after each boundary. Missed boundaries are never back-filled |
| Outcome sweep | Every 1 min, at most 500 decisions per sweep, with an in-memory `(ts, decision_id)` cursor |
| Re-mark sweep | Every 15 s |

- Passes for one instrument never overlap (one queue per instrument).
- A global gate of 3 (`SIM_CONCURRENCY`) is shared by fill passes, outcome tasks and re-marks.
- Mark reads use the fill transaction's own connection, so the pool is never checked out twice under a row lock. Pending reads are paged at 500.
- For marks, the bot reads the status publisher's in-memory `px:last` record (a price view that wraps `writeLast`), never Redis.

Metrics:
- `sim_orders_pending`
- `sim_fills_total{venue_id,tag}`
- `sim_fill_latency_seconds`
- `sim_marks_total{kind}`
- `sim_mark_lag_seconds{kind}` (a gauge)
- `sim_outcomes_written_total{column}`
- `sim_outcome_lag_seconds`

There is no dedicated re-mark metric (FU-16). Rewrites log `sim_mark_written` with `remark: true` (source: raw/2026-10-08-simulation-engine.md §API, Bot runner `sim`; §Concept, ORCH-26).

**Slice 2b changes to `packages/sim`.** No fill behaviour changed. The `sim` runner fills the zone bot's market orders exactly as it fills user orders, so with `sim` disabled, bot orders stay pending. `CLOSE_STAMP` takes `$4` (C4'), the fill pass reads the exit reason, and `sim_order_filled` gains `exit_reason`. `marketPrice`, `divFloor`, `valueAccount` and `readMarkContext` are exported for the bot's intake (source: raw/2026-10-09-zone-transition-bot.md §Files touched, tidewatch-bot; §API, Bot runtime).

**Fill latency (slice-2 carry-over).** Under the next-bar rule, FR-SIM-E2E-004's "fills within 2 minutes" can be slightly exceeded in the worst case. The 2b preview measured SQL fill latencies of 64.6 s and 113.5 s. The UI cannot measure it, because `filled_at` is the bar open, so a log- or SQL-based latency guard for the preview harness is a follow-up (source: raw/2026-10-09-zone-transition-bot.md §Concept, ORCH-13a; §Test plan, Other preview results; §Open questions, Slice 2 carry-overs).

## Read by Stats (slice 7, 2026-10-27)

Slice 7 (see [[statistics]]) reads the paper-trading tables and writes none of them: nothing writes `orders`, `fills` or `ledger`, and there was no migration (source: raw/2026-10-27-statistics.md, summary block; §Database).

**A1 was false: `realized_thb` is already net of both fees.** The PRD (D6, §4.3) defined a closed position's net result as `realized_thb − fees_thb`. The service's C5 arithmetic (`internal/trading/arith.go`, `ApplyFill`) books:
- a spot buy as `realized = −fee`;
- a spot sell as `gross − fee − cost_removed`;
- a futures open as `−fee`;
- a futures reduce as `pnl − fee`.

`RealizedTHB` and `FeesTHB` both accumulate on every fill, and the bot's `packages/sim/src/arithmetic.ts` agrees. So per-position net is `realized_thb` (PRD §11's own fallback); subtracting `fees_thb` again would take the fees twice. The arithmetic fixture records `"a1": "realized_thb is net of fees; no subtraction"`, and the finding was reported to the owner. Stats' win rate and profit factor use `realized_thb` as net (source: raw/2026-10-27-statistics.md §Concept, Assumptions A1; §Concept, How each figure is computed, KPIs).

**What Stats reads.**
- **`positions`:** `realized_thb`, `opened_by_decision_id` and `closed_at`, for positions opened by a decision of the graded version and closed in the window.
- **`ledger`:** every `day_end` mark in the window (equity and the equal-weight buy-and-hold benchmark), plus the first mark of any kind for a fresh window. A `day_end` mark at 00:00 Bangkok closes the previous day. Daily returns for Sharpe and Sortino run between consecutive `day_end` marks, annualised by √365.
- **The now point** reuses the unchanged `portfolioAt(bot, 1m, now)` in the same snapshot, so it equals `GET /portfolio`'s `equity_now` and `benchmark_now`.
- **The C6 rule-4 USD/THB rate** at the read's now converts the cost of decisions to THB.
- **`venue_rules`:** commission, VAT, slippage and the futures per-contract fee give the modelled round-trip cost rate that attribution subtracts. It omits the US sell-side per-unit fee, and VAT applies to commission only (A2).
- **Snapshot pattern.** Every Stats read runs in one `REPEATABLE READ READ ONLY` snapshot, the C4 "now" read pattern. Promote's verdict re-run takes no lock, `paper_accounts` included, and reads cash and open positions from one snapshot begun after its bot-row locks, so it never sees a half-applied fill (see [[stats-read-api]]).

(source: raw/2026-10-27-statistics.md §Database, What the reads use; §Concept, How each figure is computed, The window and KPIs; §Concept, Assumptions A2; §API, Promotion semantics and locking)

**A seeded-ledger caution from the preview.** The engine values a fill-less account at its starting capital. A seeded ledger that ended at 1,080,000 therefore read as a −7.4 % day, and the guard paused the seeded challenger twice; the seed was rescaled (see [[bots-engine]]) (source: raw/2026-10-27-statistics.md §Test plan, The E2E checks, FR-ST-E2E-002).

## Service-side notes and known gaps

- **ORCH-11 / ORCH-24 (R13), calendar-free close rule.** The service never evaluates calendars. A backdated manual fill on an account that holds a daily-only instrument, whose `px:last` is unusable, is marked from the latest `candles_eod` row with `session_date + 1 day 00:00 UTC ≤ t`.
  - For `set`, this never looks ahead, but it can lag by up to 14 h 20 min.
  - For about 14 h, the service can show `Position.last` non-null where the bot shows null. The price is the same.
  - FU-1: the same rule could look up to 1 h ahead for a US-hours daily-only instrument. None is seeded.
- **Manual fills.**
  - R14: `filled_at` may not be earlier than the account's `started_at`.
  - The manual price is stored as entered, not rounded to the tick.
  - FU-9: refuse fills dated before the position opened.
- R15: a stale `px:last` refuses a skip.
- Negative `insufficient_cash.available` can reach the client.
- FU-2: the `venue_rules` CHECK still lets a spot rule carry a margin without a multiplier.
- FU-12: the `ledger.marks` `fx` value is written as `33.50` where the fixture has `33.5`. The two are decimal-equal.

(source: raw/2026-10-08-simulation-engine.md §Concept, Recorded deviations; §Open questions)

## Accounts and roles: who owns an account (2026-10-29)

- **Every account belongs to a person** with role `user`, created only by an operator (see [[accounts-and-roles]]). The backfill kept the owner's accounts, orders, fills, positions and ledger intact: on a copy of the retained preview database, paper accounts 5, orders 26, fills 26 and positions 14 were identical before and after L (E2E-005).
- **Starting capital is plan data.** `EnsureBots` opens `me` and Slack Water at the plan's `starting_capital_thb`, and `POST /bots` without `starting_capital` uses it too.
- **Disable pauses through the Pause path.** An operator's *Disable sign-in* pauses each running or observing auto bot through the trading Pause path, inside one locked transaction that takes `MeBotLockKey(user)` and the bot rows in ascending `bot_id`. The source says nothing more about pending orders or open positions on a disable than that the bots are paused [needs verification] (see [[bot-versions-and-runs]] for Pause).
- **Operators never see trading data.** The console shows counts and spend only, with no decisions, bot names, configs or impersonation (D6).

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built; §Database, Backfill; §API, People, Writes; §API, Product contract changes)

## Related pages

- [[simulation-engine]]: the slice-2 overview, stage and preview acceptance
- [[decision-record]]: the decision row written with every order, and its outcomes
- [[redis-market-contract]]: `px:last` session state and the 120 s freshness bound
- [[market-data-worker]]: the worker that hosts the `sim` runner and the bar sink `persisted` event
- [[market-timeseries]]: `candles` and `candles_eod`, the bars fills and marks read
- [[instrument-master]]: venues, calendars, tick and lot sizes
- [[gold-feed-xaut-proxy]]: XAU/USD pricing and the USDTTHB rate
- [[centralized-migrations]]: migration E, which created these tables
- [[zone-transition-bot]]: slice 2b, the auto bot that uses the second intake
- [[bot-versions-and-runs]]: the bots, versions and runs model, and the C10 fixture
- [[bot-watch-verdicts]]: contract C11 and the bot's watch write, which stays outside the C4 lock order
- [[signal-cited-orders]]: `decision_ctx`, `checkSignal`, the recommendation and the Trade pre-fill
- [[bots]]: slice 6, with per-bot paper accounts and candidate-cited orders
- [[statistics]]: slice 7, which grades bots from positions and ledger marks (A1)
- [[stats-read-api]]: the KPI definitions that read `realized_thb`, `day_end` marks and `portfolioAt`
- [[bots-engine]]: the manager and guard that place orders through the bot-side intake
- [[accounts-and-roles]]: the person who owns each account, and the plan's starting capital
