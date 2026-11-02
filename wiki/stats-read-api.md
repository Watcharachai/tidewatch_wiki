# Stats read API: `/stats`, losses, compare, promote and the post-mortem label

**Summary**: The five owner-scoped, gated routes that slice 7 added to tidewatch-service (PR #15, merge `f289b9f`, merged and deployed to production on 2026-10-27): `GET /stats`, `GET /stats/losses`, `GET /stats/compare`, `PUT /decisions/{decision_id}/post-mortem` and `POST /bots/{bot_id}/promote`. Three read the decision record and the ledger in one `REPEATABLE READ READ ONLY` snapshot; two write, the post-mortem label being the one user write to a decision. Every figure has a committed SQL counterpart, and decimals travel as strings. Two existing routes changed additively: `GET /bots/{bot_id}/attribution` gains four net keys, and `GET /recommendation` gains `follow_record`. The shapes, figure definitions and refusal order are pinned by the service's `contracts.md` **r2** (sha256 `7b01f95c…b0fc`; r1 `66fe3e64…2f0f`), as recorded in the source. The screen that reads these routes is on [[statistics]]. **Since the learning loop (tidewatch-service #16, merge `3f8627a`, merged and deployed 2026-10-30),** four of the five routes changed additively. `GET /stats/losses` takes `proposed=1` (cursor kind `M`), and each `LossRow` ends with the model's `proposal`. The post-mortem PUT keeps provenance: confirming the model's label stores `labelled_by: "model"`. For a **learned** challenger, a skipped `calibration_no_worse` is `met: false` with `not_comparable`, and promote refuses `calibration_not_comparable` (nine documented reasons). `GET /stats` and compare carry `version.learned`. The gated count is 70 (see [[learning-loop]]).

**Sources**: `raw/2026-10-27-statistics.md` (§API and §Database, which follow contracts r2 §2–§7, the open-contract choices in `M1-choices.md`, the service README "Stats routes" and the service `CLAUDE.md` "Stats invariants (slice 7)"); `raw/2026-10-29-accounts-roles.md` (the gate's role only); `raw/2026-10-30-learning-loop.md` (the changed Stats routes only)

**Last updated**: 2026-10-31

---

## Conventions

- **Gating.** All five routes mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles, 2026-10-29; see [[accounts-and-roles]]). CSRF is engine-wide on the PUT and the POST (`X-Tidewatch-Request: 1` plus the app `Origin`; see [[request-protection]]).
- **Gated count.** `TestRouter_ForcedChangeGatesNewRoutes` counts **64**: 61 production routes and 3 test probes. It went 59 → 60 (S4) → 62 (S5) → 63 (S6) → 64 (S7).
- **No decision mutation, with one exception.** `TestRouter_NoDecisionMutation` admits exactly one new `/decisions` write, the post-mortem PUT ("the post-mortem label is the one user write to a decision; the trigger limits it to post_mortem"). Its reviewed `:bot_id` routes grow from nineteen to twenty with promote (see [[decision-record]]).
- **Owner scope.** A bot, version or decision that is unknown or another user's is one indistinguishable `404 not_found`, never 403 (see [[auth-model]]).
- **The manual bot.** On `GET /stats` and `/stats/losses` it is the same 404 as an unknown bot. Compare answers `400 {field: "challenger", reason: "manual_bot"}`; promote answers `400 {reason: "manual_bot"}`. It is never the default bot.
- **Strict query.** An unknown parameter is `400 invalid_request {reason: "invalid"}` with no field; a repeated one `{field, reason: "duplicate"}`; a malformed one `{field, reason: "invalid"}`.
- **Shapes.** Every key is always present; undefined is `null`.
- **Nothing is created.** No route calls `EnsureBots`. Promote is the one `/bots/{bot_id}` route that does not, recorded as an exception in the service `CLAUDE.md` (fold P3).
- **Snapshots (S13).** Every read is one `REPEATABLE READ READ ONLY` snapshot. Promote and the post-mortem write are `READ WRITE`.

(source: raw/2026-10-27-statistics.md §API, Conventions; §Concept, Spec decisions S13)

## Routes

| Method and path | Request | 2xx | Refusals |
|---|---|---|---|
| `GET /stats` | `bot_id?`, `version?` (a `seq`), `period?` = `30d\|90d\|all\|custom`, `from?`, `to?` | `200 {generated_at, bot, version, window, kpis, series, calibration, attribution, post_mortems}` | `400` (grammar, S8 ranges), `404` |
| `GET /stats/losses` | `bot_id` (required), `version?`, `limit?` 1–200 (default 50), `cursor?` | `200 {items: [LossRow], next_cursor}` | `400` (grammar, cursor), `404` |
| `GET /stats/compare` | `challenger` (required); a `champion` parameter is unknown | `200 {generated_at, champion \| null, challenger, shared_window \| null, verdict}` | `400` (grammar, `manual_bot`, champion as challenger), `404`, `500` for a flagged champion without a current version (fails closed; unreachable) |
| `POST /bots/{bot_id}/promote` | no query, no body (ignored, as Pause/Resume) | `200 {bot: BotSummary, previous_champion: uuid \| null}` | `400 {reason: manual_bot}`, `404`, `409 promotion_refused {reasons}` |
| `PUT /decisions/{decision_id}/post-mortem` | `{"label": "<one of seven>"}` (strict) | `200 {decision_id, post_mortem}` | `400` (body, `not_a_loss`), `404`, `409 post_mortem_frozen` |

**Changed routes (additive).**
- `GET /bots/{bot_id}/attribution`: each item gains `win_rate`, `avg_r_5d_net`, `best` and `worst` after `graded`, in that order. Every existing key, value, item and order is byte-identical to slice 6 (`TestBots_Attribution_Compat`, at HEAD and at base `db281db`). See [[bot-versions-and-runs]].
- `GET /recommendation`: gains `follow_record` as its **last** key on every shape, the "no recommendation" shape included. See [[signal-cited-orders]].

(source: raw/2026-10-27-statistics.md §API, Routes and Changed routes)

## `GET /stats`

### Query grammar and check order

1. **`parseQuery`:** an unknown parameter, then a duplicate, by name.
2. **Each parameter's grammar,** in the order `bot_id`, `version`, `period`, `from`, `to`:
   - `bot_id`: a hyphenated 8-4-4-4-12 UUID in either case; braced, URN and unhyphenated forms are `invalid`;
   - `version`: plain ASCII digits, 1 to 2147483647, no sign and no leading zero (`01` is `invalid`);
   - `from` and `to`: `YYYY-MM-DD` dates that exist.
3. **Cross-field rules,** in order: `version` without `bot_id` → `{field: "bot_id", reason: "missing"}`; `from` or `to` with a non-custom period (an absent period is `all`) → `{field, reason: "invalid"}`; `custom` without `from` → `{field: "from", reason: "missing"}`.
4. **Bot and version,** so a foreign bot is `404` before any range check: an unknown, foreign or manual bot, or an auto bot without a version → "That bot doesn't exist."; an unknown version → "That version doesn't exist."; no `bot_id` and no gradable bot → "No bot to grade yet.".
5. **S8 ranges,** each `out_of_range`: `from > to` → `from`; a `to` ending at or before the version start → `to`; a `from` at or after the window end → `from`; more than 366 dates → `to`.

An empty window is never an error: a version made a minute ago answers zeros, `null`s and the ten source rows. Without `bot_id`, the route reads the champion, else the oldest auto bot with a current version (S16) (source: raw/2026-10-27-statistics.md §API, `GET /stats` query grammar and check order; §Concept, Spec decisions S16).

### The body (contracts §2.4, PRD §6.1; key order as shown)

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

- `bot.status` is `running`, `observing` or `paused`.
- `version.hash` is the full 64-hex hash, and `label` is `v{seq}·{hash[0:4]}`; `version.current` means `bots.current_version` is this version.
- `version.tier` is the v2 `decision_tier` (`none | jev | small_llm | large_llm`), or `none` for a legacy v1 config.

(source: raw/2026-10-27-statistics.md §API, `GET /stats` body and notes)

## How each figure is computed (contracts r2 §2)

### Rounding and units

- Decimals travel as strings, rounded half away from zero. Ratios carry 6 fraction digits (the web multiplies by 100); THB carries 2; Sharpe, Sortino, the profit factor and the ECE carry 4; `cost_usd` carries 6.
- Instants are RFC 3339 UTC; Bangkok dates are `YYYY-MM-DD`; Bangkok is a fixed UTC+07:00.
- `internal/trading/stats.go`, `calibration.go` and `costrate.go` are pure and float-free; square roots go through `math/big`.

### The window

- **Version window (D2).** `start` is the version's `created_at`. `end` is the `created_at` of the next `seq`, or `null` for the current version (the read's now closes it). See [[bot-versions-and-runs]].
- **Periods.** `all` → `[start, E]` where `E = end or now`; `30d` / `90d` → `[max(start, E − N × 24 h), E]`; `custom` → `[from 00:00 Bangkok, to 24:00 Bangkok]`, clipped to `[start, E]`.
- **Membership.** Decisions, runs and position closes count when `from ≤ ts < to`. Ledger marks join the series when `from < ts ≤ to`; a `day_end` mark at 00:00 Bangkok closes the previous day. The **rebase mark** is the last `day_end` with `ts ≤ from`, else the first mark of any kind with `ts ≥ from`.
- **Days.** `window.days = floor((to − from) / 24 h)`. `to_day` is the Bangkok date of the last instant before `to`.
- **The now point.** When `to` is now, it is `GET /portfolio`'s `equity_now` and `benchmark_now`, through the unchanged `portfolioAt(bot, 1m, now)` in the same snapshot (see [[paper-trading]]).

### KPIs

| Field | Definition |
|---|---|
| `return_pct` | last series equity / first series equity − 1; `"0.000000"` with one point or a zero base |
| `benchmark_return_pct` | last non-null benchmark / benchmark base − 1, where the base is the first point with a non-null benchmark; `null` when none has one or the base is zero |
| `series[].benchmark` (OD-1) | `stored × (E_b / B_b)`, where `B_b` is the benchmark base and `E_b` is that same point's equity, computed exactly then rounded. When the rebase mark has a benchmark, both lines start at the rebase equity |
| `series[].drawdown`, `max_drawdown_pct` | `equity / running peak − 1` (≤ 0); the KPI is its minimum |
| `days_to_recover` (PD4) | Bangkok-date difference from the trough to the first later point with equity ≥ the peak at the trough; `null` when not recovered; `0` when there was no drawdown. **Fold P2:** a point can be the trough only when its drawdown rounded to 6 digits is negative; the trough is the earliest exact minimum among those |
| `sharpe`, `sortino`, `daily_returns` | `r_t = e_t / e_{t−1} − 1` over the rebase mark and the `day_end` marks, without the now point. Sharpe = mean / sample st. dev. (N − 1) × √365. Sortino = mean / √(Σ min(r_t, 0)² / N) × √365. `null` when N < 10 or the denominator is 0 |
| `win_rate_pct`, `positions_closed`, `positions_won` | positions opened by a decision of this version and closed in the window. **Net = `realized_thb`** (A1: already net of both fees). Won / closed |
| `profit_factor` | Σ positive net / \|Σ negative net\|; `null` when no position lost |
| `decisions`, `skips`, `orders` | rows of this version in the window. Skips are `action = 'skip'` except `policy_result->'reasons' = ["observing"]` (PD3). Orders are `buy, sell, add, trim, close` |
| `cost_usd`, `scout_wakes` | Σ `bot_runs.counts->>'cost_usd'` over the version's runs (any loop) started in the window. Only a JSON string matching `^[0-9]{1,12}([.][0-9]{1,18})?$` counts (the bot's own guard). Scout wakes are runs with `loop = 'scout'` |
| `usd_thb`, `cost_thb` | `usd_thb` is the C6 rule-4 rate at the read's now (also for a past version's window), `null` without one; `cost_thb` = exact `cost_usd` × that rate, rounded to 2 (see [[model-routes-and-spend]]) |

### Calibration (D8, S2)

- **Population.** The version's `propose` rows in the window whose `model->>'p'` is a decimal in [0, 1] (`n_stated`). The grammar is `-?[0-9]+(\.[0-9]+)?`, so `.5`, `1e-1` and `true` state nothing, and `-0` is 0.
- **Horizon column** from the candidate: `intraday → r_1d`, `days → r_5d`, `weeks → r_20d`; anything else, or no candidate, uses `r_5d` (A3). `n_graded` counts rows whose horizon column is not null.
- **Hit.** The horizon return is `> 0` for `long` and `< 0` for `short`; zero is a miss.
- **Bins.** Always ten, `lo` `"0.0"`…`"0.9"`; a bin holds `lo ≤ p < hi`, and the last holds `0.9 ≤ p ≤ 1`. `mean_p` and `hit_rate` carry 3 digits and are `null` when `n = 0`.
- **ECE** = `Σ (n_b / n_graded) × |hit_rate_b − mean_p_b|`, from the exact bin values, 4 digits. `null` under 30 graded, or when `states_p` is false (tier `none`, or a legacy v1 config).

### Attribution (D7, PD5, S1)

- **Base rows.** `actor = 'bot' AND action IN ('buy','add')`. The Bots scope takes every version; the Stats scope takes this version, in the window.
- **Modelled round-trip rate** from the instrument's `venue_rules` row: `2 × commission_pct × (1 + vat_pct) + 2 × slippage_bps / 10000`; for futures, plus `2 × per_contract_fee_thb / (px_at_decision × contract_multiplier)` when the price is positive; no rule row means rate 0. A2: it omits the US sell-side per-unit fee.
- **Net return.** `r_5d` oriented by direction (`−r_5d` for short), minus that rate.
- **Per group:** `n`; `n_graded`; `win_rate` (graded rows with net > 0, over `n_graded`); `avg_r_5d` (the gross stored average, unoriented, as slice 6's S20); `avg_r_5d_net`; `best` and `worst` (max and min net). All 6 digits, `null` when `n_graded = 0`. Key order: `key, label, tier, n, n_graded, win_rate, avg_r_5d, avg_r_5d_net, best, worst`.
- **Groups.**
  - `source`: every `sources` row in `GET /sources` order (tier `filing, wire, exchange, media, account`, then code), always present, then `{key: "none", label: "No signal"}` for rows without a snapshot, without a code, or with a code that is not a `sources` row (see [[source-registry-and-ingest]] and [[signals-read-api]]);
  - `event_type`: by `n` descending, then key; then *No signal*;
  - `asset_class`: `us` "US stock" (stock on `us-equities`), `th` "Thai stock" (stock on `set`), `crypto`, `gold`, then `unknown` (see [[instrument-master]]);
  - `regime`: the six `trend × vol` cells ("Up · normal volatility" …), then `unknown` (see [[elliott-regime-labeller]]).
  - Groups with `n = 0` are omitted, except the source rows.

### Post-mortem counts (D5)

- **A losing decision** is a base row (Stats scope, in the window) whose horizon column is graded and is not a hit.
- **`labelled` and `by_label`** count losing decisions whose `post_mortem->'label'` is a JSON string naming one of the seven labels, with `confirmed_by_user` JSON `true` (the string `"true"` does not count). `by_label` always has the seven keys in fixed order.
- **`by_labeller`:** `user` and `model` count confirmed known labels by `labelled_by`; `proposed` counts a known label that is not confirmed (0 in this slice).

### `follow_record` on `GET /recommendation` (D11, S5)

- **Rows.** The `me` bot's `buy|sell|add|trim|close` decisions with `ts ≥ now − 30 × 24 h` and `r_5d` not null, with no `actor` filter.
- **Split.** `followed` is `followed_recommendation IS TRUE`; `own` is `IS NOT TRUE`.
- **Values.** `avg_r_5d` is the gross average, 6 digits, `null` under 5 graded on that side; `n_graded` is always the count. With no manual bot, both sides are `{0, null}`.

(source: raw/2026-10-27-statistics.md §Concept, How each figure is computed; Assumptions A1–A3)

## `GET /stats/losses`

- **Check order.** `parseQuery`; `bot_id` absent → `missing`, not hyphenated → `invalid`; `version` per S4's grammar; `limit` non-digits `invalid`, outside 1–200 `out_of_range`; `cursor` empty → `invalid`. Then the service: cursor syntax (before the bot), bot and version (as for `/stats`), then the cursor binding.
- **Items.** Losing decisions of the version over the **whole version window** (not a period) whose `post_mortem` is `null` or not confirmed, ordered `ts DESC, decision_id DESC`, 50 per page by default. Membership: `bot_version = hash`, `created_at ≤ ts < next version's created_at (else now)`, `actor = 'bot'`, `action IN (buy, add)`, horizon column graded and not a hit.
- **`LossRow`**, keys in order:

```json
{"decision_id": "…", "ts": "…", "loop": "scout", "version_label": "v7·9ad1", "action": "buy",
 "instrument_id": "NVDA@webull", "display_symbol": "NVDA", "qty": "16.2", "fill_px": "131.40",
 "exit_reason": "stop",
 "signal": {"source_code": "sec-8k", "publisher": "SEC 8-K", "tier": "filing", "p": "0.68", "horizon": "days"},
 "trigger": null, "horizon_column": "r_5d", "outcome_net": "-0.024000", "post_mortem": null}
```

- **Field rules.** `qty` and `fill_px` read as `GET /decisions` answers them; `fill_px` is `null` without a fill. `trigger` is `policy_result->>'trigger'`. `outcome_net` is the stored, unrounded horizon return oriented by direction, minus the modelled rate at `px_at_decision`, computed exactly and rounded to 6 digits.
- **`signal` (XP-1).** Non-null whenever `signal_snapshot` exists. `publisher` and `tier` come from a LEFT JOIN to `sources` by the snapshot's `source_code`, so **a loss row's signal may carry a null `publisher` and `tier`** when the code is absent or is not a `sources` row; `source_code` is `null` when the snapshot has no such key. Contracts stay r2. The web shows the editor's name for the code, else the publisher, else the code, else "—", with no tier tag for a null tier.
- **Cursor.** On the decisions wire, kind byte `L` (0x4C). The checksum input is `version(8) ‖ 'L' ‖ bot_id(16) ‖ seq(8) ‖ ts µs(8) ‖ decision_id(16)`, 57 bytes, bound to the bot and version. A decisions, runs or candidates cursor is `400 {field: "cursor", reason: "invalid"}`, as is a losses cursor of another bot or version, or an edited one; a losses cursor sent to `GET /decisions` or `GET /bots/{bot_id}/decisions` is refused the same way. The candidates cursor's state byte `L` sits at another offset of a 50-byte input, so the two cannot collide. The checksum is unkeyed (existing design, security L-3).

(source: raw/2026-10-27-statistics.md §API, `GET /stats/losses`; §Concept, Rulings XP-1; §Concept, Review history, Service code)

## `PUT /decisions/{decision_id}/post-mortem`

Checks, in order (contracts §5):
1. Any query parameter → `400` (no field).
2. A path id that is not a UUID → `404`.
3. The body: an extra key is `unknown_field` (never named); `label` absent or `null` → `{field: "label", reason: "missing"}`; outside the seven → `{field: "label", reason: "invalid"}`. The body is checked before ownership, so a bad body on a foreign decision is `400`.
4. Not the user's decision → `404` "That decision doesn't exist.".
5. Not a losing `buy | add` with `actor bot` of any of the user's bots → `400 {field: "decision_id", reason: "not_a_loss"}` "Only a losing buy or add of a bot can be labelled.". This covers a winner, an ungraded row, a skip and a manual decision. The decision need not be of the current version.
6. Already confirmed → `409 post_mortem_frozen` "That decision was already labelled.", with no details. A conditional `UPDATE` that matches no row (a lost race) is `409` too, and so is a second identical PUT.

**The write.** One READ COMMITTED READ WRITE transaction (`PostMortemStore.InPostMortemTx`), with no lock beyond the UPDATE's own. It stores exactly `{label, labelled_by: "user", confirmed_by_user: true, labelled_at}` by `UPDATE … WHERE post_mortem IS NULL OR post_mortem->'confirmed_by_user' IS DISTINCT FROM 'true'::jsonb`, so an unconfirmed model proposal is replaced by the user's label. `labelled_at` comes from the service clock at full precision, so the stored object and the answer share one value. The audit row is written in the same transaction, and the handler logs `post_mortem_labelled` after the commit. The existing `decisions_backfill_only` trigger still rejects any other column and freezes a confirmed label (see [[decision-record]]).

(source: raw/2026-10-27-statistics.md §API, `PUT /decisions/{decision_id}/post-mortem`; §Database, What slice 7 writes)

## `GET /stats/compare` and the verdict

- **Check order.** `parseQuery` (`champion` is an unknown parameter here); `challenger` absent → `missing`, malformed → `invalid`; in one snapshot, an unknown or foreign bot → `404`; the manual bot → `400 {challenger, manual_bot}` "The manual bot can't be compared."; an auto bot without a version → `404`; the champion itself → `400 {challenger, invalid}` "That bot is the champion." (OD-2).
- **The champion** is the user's `kind = 'auto'` bot with `champion = true`. A flagged champion without a current version is an internal error (`ErrChampionWithoutVersion`, 500), not the first-champion branch, because promote must see the same champion.
- **The shared window** is `[max(both current versions' created_at), now]`, under `all`'s rules. Both sides' `kpis` come from the same `statsFigures` function `GET /stats` uses.
- **Comparisons use the answered (rounded) figures** (returns and drawdowns at 6 digits, ECE at 4), so the verdict never contradicts its own detail. An equal return is not higher; an equal |drawdown| or ECE passes.

| Code | Met when | `detail` |
|---|---|---|
| `window_30d` | `days ≥ 30` | `{days}` |
| `return_higher` | challenger `return_pct` > champion's, strictly | `{challenger, champion}` |
| `drawdown_no_deeper` | \|challenger `max_drawdown_pct`\| ≤ \|champion's\| | `{challenger, champion}` |
| `calibration_no_worse` | challenger `ece` ≤ champion's, when both state `p` and both have `n_graded ≥ 30`; else `met: null` | `{challenger, champion}`, or `{skipped}`: the first of `champion_states_no_p`, `challenger_states_no_p`, `too_few_graded` |
| `active` | `kind = 'auto'`, `status = 'running'`, `probation_until` null or ≤ now | `{status, probation_until}` |
| `first_champion` | always | `{}` |

- **With a champion,** the conditions are `window_30d, return_higher, drawdown_no_deeper, calibration_no_worse, active`, in that order.
- **With none,** `champion` and `shared_window` are `null`; the challenger is read over its own current-version window to now, and the conditions are `first_champion`, `window_30d` (its own days) and `active`.
- **`passes`** is true when every `met` is `true` or `null`.

(source: raw/2026-10-27-statistics.md §API, `GET /stats/compare` and the verdict)

## `POST /bots/{bot_id}/promote`: semantics and locking

1. **Transaction and lock.** `Store.InLockedTx(MeBotLockKey(user))`: READ COMMITTED, advisory lock first. A REPEATABLE READ snapshot would have been taken before the lock wait and missed a concurrent promote. It is the same lock that create, clone and resume hold.
2. **Load the bot, owner-scoped** (one `404` for another user's, unknown or malformed). No `EnsureBots`.
3. **Refuse the manual bot:** `400 {reason: "manual_bot"}` "The manual bot can't be promoted.".
4. **Find the current champion.**
5. **Lock the rows.** `BotRepo.LockBot` locks the challenger and the champion (when another bot) `FOR NO KEY UPDATE`, in ascending `bot_id` byte order, the lock Pause, Resume and Save as vN take. No Pause, Save or promote can change the flag, status or `current_version` between the check and the flip, and no lock cycle is possible (contracts r2 §7).
6. **Refusals from the locked rows:** the champion itself (including a lost race) → `409 promotion_refused {reasons: ["already_champion"]}` "That bot is already the champion."; no current version → `["no_current_version"]`.
7. **Re-run the verdict in a snapshot.** Since fold P1 it runs in `Store.InSnapshot` (REPEATABLE READ READ ONLY), begun **after** the row locks, on a second pool connection, bounded by `queryTimeout` (pool exhaustion fails closed: 500, rollback). It takes no lock and commits before the first write, so cash and open positions come from one snapshot and the verdict never sees a half-applied fill. `TestPromoteBot_VerdictReadsInSnapshot` pins the call order.
8. **A failing verdict** → `409 promotion_refused` "That bot can't be promoted yet.", listing unmet conditions in order: `window_too_short`, `return_not_higher`, `drawdown_deeper`, `calibration_worse`, `not_active`. `same_bot` is documented and never sent.
9. **On a pass,** at one `now` with the session user as actor: the previous champion `champion = false`, then the challenger `true`; `promoted` on the challenger's current version with `detail {previous_champion}`; `demoted` on the previous champion's current version with `detail {succeeded_by}`, only when there was one; the audit `bot_promoted`.
10. **After the commit,** the handler logs `bot_promoted` and answers the `GET /bots` item read after the commit.

A refusal writes nothing. Two concurrent promotes end with exactly one champion (`TestPromote_Concurrent`). A Pause holding the challenger's row lock commits while promote waits; promote then answers `409 [not_active]` (`TestPromote_PauseRace`). The flag is read by the Bots *Champion* tag and by `recommendations.follow = "champion"` on their next read. A later version of the champion keeps the flag, and its compare window restarts (D3). See [[bot-versions-and-runs]].

(source: raw/2026-10-27-statistics.md §API, Promotion semantics and locking; §Database, What slice 7 writes)

## Codes, audit, metrics and logs

| Code | HTTP | Where | `details` |
|---|---|---|---|
| `promotion_refused` | 409 | promote | `{reasons: [string]}` (typed `PromotionDetail`; `PublicDetails` keeps only the eight documented reasons, in order, and always sends an array) |
| `post_mortem_frozen` | 409 | post-mortem PUT | none |
| `invalid_request` | 400 | all five | `{field?, reason}`; new reason `not_a_loss` |

- **Codes.** Both new codes follow `run_rate_limited` in `AllCodes()`, giving 20 trade codes; the README error table has two new rows (`TestCodes_Contract`, `TestAllCodes_MatchContract`, `TestReason_ClosedSet`).
- **Audit.** `bot_promoted {bot_id, version, previous_champion}`, where `version` is the integer seq and `previous_champion` is always present (JSON `null` for the first champion); `post_mortem_labelled {decision_id, label}`. Typed constructors only; `audit.Types()` orders `bot_promoted` first (`TestAudit_StatsEvents`).
- **Metrics.** `stats_reads_total{kind}` and `stats_read_seconds{kind}` (a histogram on Prometheus' default buckets, which include 0.5 s), with `kind` in `stats | compare | losses`, all at 0 from startup (`TestMetrics_StatsSeries`). Each request that reaches the service counts once; a query refused in the handler does not. They make the D10 500 ms trigger observable.
- **Logs** (info, ids and enums only, after the commit): `bot_promoted` and `post_mortem_labelled`. `TestLogs_NoBotTextOrConfig` checks that a sentinel bot name and a sentinel rationale never reach the log.

(source: raw/2026-10-27-statistics.md §API, Codes, audit, metrics and logs)

## Performance and index use (FR-ST-SVC-013, A7)

- **Timing passed.** On the preview (92 `day_end` marks, 10,000 decisions; 20 timed runs after one warm-up), `period=all` took p50 133.5 / p95 161.1 / max 206.0 ms and `30d` p50 37.2 / max 40.1 ms. All are under 500 ms, so the D10 snapshot-table trigger was not reached.
- **The index criterion failed as written.** `EXPLAIN (ANALYZE, BUFFERS)` on PostgreSQL 18.6: `period=30d` and the losses read used `decisions_bot_ts_idx`; for `period=all` the planner chose a sequential scan on `decisions` for the counts, calibration, entry-outcomes and version-attribution statements, because the seeded bot owns 10,000 of 10,032 rows (99.7 %). With `enable_seqscan = off` (session only) the index plan exists and costs about the same.
- **No index was added.** A7 says the owner is asked first; the record shows no index proposal and no owner answer.

(source: raw/2026-10-27-statistics.md §Database, Index use; §Test plan, The E2E checks and SVC-013; §Open questions)

## Named service tests (do not rename)

- **Unit:** `TestStatsWindow_Rules`, `TestStatsArithmetic_Fixtures`, `TestStatsArithmetic_SqrtExact`, `TestCalibration_Synthetic`, `TestCalibration_Bins`, `TestAttribution_Net`, `TestAttribution_Dimensions`, `TestModelledCostRate`, `TestPromotionCheck_Conditions`, `TestPromoteBot_VerdictReadsInSnapshot`, `TestLossesCursor_KindAndBinding`; the handler, contract and router tests, including `TestRouter_NoDecisionMutation` and `TestRouter_ForcedChangeGatesNewRoutes` (64).
- **Integration:** `TestStats_MatchesSQL`, `TestStats_Window`, `TestStats_Calibration`, `TestStats_DefaultBot`, `TestStats_Compare`, `TestStats_ScopeAndNotFound`, `TestStatsLosses_Paging`, `TestCursor_Kinds`, `TestPostMortem_Write`, `TestPostMortem_Refusals`, `TestDecisions_DirectSQLMutationFails`, `TestPromote_Pass`, `TestPromote_Refused`, `TestPromote_Concurrent`, `TestPromote_PauseRace`, `TestBots_Attribution_Compat`, `TestBots_Attribution_MatchesSQL`, `TestRecommendation_FollowRecord`, `TestRecommendation_NoCreate`, `TestLogs_NoBotTextOrConfig`.
- **Fixtures.** `internal/trading/testdata/stats/gen_arithmetic.py` and `gen_calibration.py` reproduce their JSON byte for byte using only the Python standard library; `test/sql/stats_{series,kpis,calibration,attribution,post_mortems}.sql` run with `psql -v`.

(source: raw/2026-10-27-statistics.md §Test plan, Commands and Named acceptance tests)

## Changes from the learning loop (slice 8, 2026-10-30)

tidewatch-service #16 (merge `3f8627a`) changed these routes additively. The loop is on [[learning-loop]]; the screen changes are on [[statistics]].

**Gates and count.** The six new learning routes take the gated count from 64 to **70** (`TestRouter_ForcedChangeGatesNewRoutes`). The Stats routes keep their gate, `RequireRole("user")` since accounts and roles; PRD §6.1's `RequireRole("admin")` for the new routes is superseded the same way.

**`GET /stats/losses`: `proposed=1` and `LossRow.proposal`.**
- **The filter.** `proposed=1` narrows the list to losses with a model proposal (the screen's *Proposed only*). Any other value is `400 {field: proposed, reason: invalid}`.
- **The cursor.** The filtered list's cursor is kind `M` (0x4D). It is refused on the unfiltered list, and the unfiltered list's kind `L` cursor is refused on the filtered list. Each is refused on every other list (`TestStatsLosses_ProposedFilter`).
- **`LossRow`** ends with `proposal: {rationale, model_id, proposed_at} | null`, from a join to `post_mortem_proposals`. The rest of the row is unchanged (`TestStatsLosses_Compat` against a slice-7 golden).

**`PUT /decisions/{decision_id}/post-mortem`: the provenance rule (D10).**
- Checks and refusals are as slice 7, including `409 post_mortem_frozen` once confirmed.
- **What is stored.** When the label equals the model's unconfirmed proposal, `{label, labelled_by: "model", confirmed_by_user: true, labelled_at}`. A different label stores `labelled_by: "user"`, as before. The conditional `UPDATE` still replaces only an unconfirmed label.
- **Audit.** `post_mortem_labelled` always carries `confirmed_proposal` (`TestPostMortem_ConfirmProposal`, `TestPostMortem_ChangeProposal`).

**`GET /stats` post-mortem counts.** `by_labeller.model` counts confirmed labels with `labelled_by: "model"`, and `by_labeller.proposed` counts known labels that are not confirmed. Both were 0 in slice 7 (`TestStats_PostMortemCounts_Proposals`). **`kpis.cost_usd`** sums `bot_runs.counts.cost_usd` over runs of any loop, so it includes a learning run's labelling spend, while the other bot reads hide `learn` rows (R4).

**`GET /stats/compare` and `POST /bots/{bot_id}/promote`: the learned-challenger gate (D13).**
- **The verdict.** For a **learned** challenger (`config.learning != null`), a `calibration_no_worse` that slice 7 would skip is `met: false, detail {not_comparable: <reason>}`, so `passes` is false. The source does not list the reason values; the web words them as "({reason words})". An unlearned challenger keeps `met: null` with `{skipped}`.
- **Promote** refuses with `409 promotion_refused` and the new reason `calibration_not_comparable`, giving **nine** documented reasons (`TestPromote_LearnedNotComparable`).
- **The first-champion branch is unchanged,** and there is no automatic promotion.
- **On the preview (E2E-004),** a learned challenger with 10 graded proposals got `409 [return_not_higher, calibration_not_comparable, not_active]`. With 35 graded it was judged on ECE (0.1685 against 0.1015 → `calibration_worse`).

**`version.learned`.** The Stats and compare `version` objects end with `learned` (P7), as do `strategy` on the bots routes and the versions items (see [[bot-versions-and-runs]]). The additive keys are checked against slice-7 goldens (`TestLearned_AdditiveKeys`, `TestStats_Version_Compat`, `TestStats_Compare_Compat`).

**The modelled cost rate, shared with the bot (C14).** The learning job's weights count a win as a net `r_5d > 0` after the same modelled round-trip rate as attribution. `attribution-net.v1.json` (`a42edbfc…`) pins the rule in the service and the bot (`TestAttributionNet_Fixture`; A7 verified).

(source: raw/2026-10-30-learning-loop.md §Concept, Service rules; §Concept, Owner decisions D10, D13; §Concept, Spec corrections, Gate chain and `learn` rows; §API, Conventions, Routes and Codes, audit, metrics and logs; §API, The `learning` block, Fixtures; §Test plan, Named acceptance tests, Results and What each seeded E2E showed)

## Related pages

- [[statistics]]: the slice-7 overview, the screen, acceptance and open items
- [[decision-record]]: the rows these routes read, and the post-mortem trigger rules
- [[bot-versions-and-runs]]: version windows, `bots.champion`, `bot_version_events` and the slice-6 attribution route
- [[paper-trading]]: `realized_thb`, ledger marks, `portfolioAt` and the C6 USD/THB rate
- [[model-routes-and-spend]]: the cost-of-decisions figure
- [[signal-cited-orders]]: `GET /recommendation`, now with `follow_record`
- [[auth-model]] and [[request-protection]]: the gated group, CSRF and owner-scoped 404s
- [[source-registry-and-ingest]], [[instrument-master]] and [[elliott-regime-labeller]]: the attribution dimensions
- [[learning-loop]]: slice 8, which adds `proposed=1`, `LossRow.proposal`, the provenance rule and `calibration_not_comparable`
