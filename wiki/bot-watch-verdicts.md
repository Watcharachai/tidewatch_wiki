# Bot watch and verdicts (`bot_watch`, `bot_runs.outcomes`, contract C11)

**Summary**: Since the bot-activity feature (merged 2026-10-10), the zone-transition bot names one of fourteen **verdicts** for every universe instrument on every evaluation: what it did, or why it did not act. `evaluateRule` computes the verdict. After each successful evaluation the bot overwrites one `bot_watch` row per (bot, instrument), which also serves as the heartbeat. When a run finishes, the bot stores the same entries in `bot_runs.outcomes`. The entry shape is the **WatchEntry**, pinned by contract C11 (`bots-watch-entry.v1.json`), a fixture that is byte-identical in the service and the bot. The service reads and decorates these rows but never computes a verdict (BA2). **Since slice 6 (bots, merged 2026-10-21, not deployed),** the general engine writes the same rows with **nine more verdicts** (`watching`, `gated`, `entered`, `expired`, `added`, `trimmed`, `exited`, `protected`, `no_candidate`), pinned as contract **C11'** (`bots-watch-entry.v2.json`, 23 verdicts), and the watch timeframe gains `15m` (see [[bots-engine]]). **Since the learning loop (slice 8, merged and deployed 2026-10-30),** a learned version's failure gate can veto an entry. The veto is a `gated` verdict with the reason `meta_veto` and no decision, so C11' and its 23 verdicts are unchanged (see [[learning-loop]]).

**Sources**: `raw/2026-10-10-bot-activity.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md` (the shared expandable row only); `raw/2026-10-16-charting.md` (the chart's stance only); `raw/2026-10-21-bots.md` (C11' and the general engine's verdicts); `raw/2026-10-27-statistics.md` (the deferred champion stance only); `raw/2026-10-30-learning-loop.md` (`meta_veto` only)

**Last updated**: 2026-10-31

---

## Why the bot records the verdict (BA2)

Before this feature, `fireRule` returned null for five different reasons, and a decision-key hit (2b R6) was a sixth silent exit, so the pass could not tell them apart. The screen exists to explain the bot, so it must show what the bot computed. A second implementation in the service would get rules such as R13's bucket-start baseline subtly wrong, and slice 2b had already paid for one second implementation (ZB5, the intake). So the bot records the verdicts, and the service adds only "next bar" and session (source: raw/2026-10-10-bot-activity.md §Concept, Problem and Chosen design BA2).

The verdict vocabulary is the set of real code branches, and the rule specs are unchanged (outcome O3) (source: raw/2026-10-10-bot-activity.md §Concept, Proposed defaults and Outcomes).

## `evaluateRule` (tidewatch-bot `rules.ts`)

`evaluateRule` returns `{kind: 'fired', fired}` or `{kind: 'blocked', reason}`. The blocked reasons are tested in the order `fireRule` always used:

1. no strip rows → `no_rows`;
2. a null zone or a pre-zone → `no_zone`;
3. Buy with an unknown run start → `run_start_unknown`;
4. Buy whose run began before `statusSince` → `baseline`;
5. the side is not allowed → `pending_order` when a pending bot order exists, else `holding` (entry) or `no_position` (exit);
6. a decision-key hit → `decided`.

- `fireRule` is now `evaluateRule(...).kind === 'fired' ? fired : null`, a wrapper of at most 4 lines. Its exports and specs are unchanged. `rules.ts` changed by +62/−10, and `rules.spec.ts` gained 368 lines and lost none.
- **S3 interpretation.** `evaluateRule`'s own `decided` branch is unreachable in the pass. The pass passes `hasDecision: () => false` and checks the store itself, and the result maps to the zone's implied rule.
- A `RangeError` from `zoneRun` (unknown zone text) is not a verdict. It throws as before, and the evaluation fails.

(source: raw/2026-10-10-bot-activity.md §API, Bot runtime; §Concept, Plan resolutions, Bot)

## The fourteen verdicts (C11 table)

Each evaluation yields exactly one entry per universe instrument. The unreachable `market === null` guard records `no_rows`, so no instrument is skipped (R-BA5).

| Verdict | When | `rule` | `reasons` | Pointers |
|---|---|---|---|---|
| `no_rows` | no strip rows | null | `[]` | — |
| `no_zone` | zone null or a pre-zone | null | `[]` | — |
| `run_start_unknown` | the Buy streak fills the 49-row window (2b R3) | `entry` | `[]` | — |
| `baseline` | the Buy run began before `status_since` (2b R13) | `entry` | `[]` | — |
| `holding` | Buy while an open position exists | `entry` | `[]` | — |
| `no_position` | Sell with no open position | `exit` | `[]` | — |
| `pending_order` | a pending bot order blocks the side | the rule the zone implies | `[]` | `order_id` |
| `decided` | a decision with the key exists (2b R6) | the rule | `[]` | `decision_id` |
| `deferred` | the session/price gate is not ok, or the intake deferred (including a USD-quoted spot instrument without a USD/THB rate) | the rule | `['venue_closed']` or `['price_unavailable']` | — |
| `placed` | the intake placed an order | the rule | `[]` | `decision_id`, `order_id` |
| `skipped` | the intake skipped | the rule | `['qty_below_minimum']` alone, or a non-empty ordered subsequence of `insufficient_cash`, `position_limit`, `exposure_limit`, `max_open` | `decision_id` |
| `observed` | the intake observed | the rule | `['observing']` | `decision_id` |
| `already_placed` | the intake found the order already placed | the rule | `[]` | `order_id` |
| `nothing` | the intake found the locked state no longer allows the action (paused, a decision appeared, the side changed) | the rule | `[]` | — |

`baseline` is the verdict the owner is most likely to ask about: a Buy bucket that began before a creation or resume is never entered (source: raw/2026-10-10-bot-activity.md §API, Bot runtime, The fourteen verdicts; §Concept, Problem; §Concept, Plan resolutions, Bot R-BA5).

**Seen live so far.** The preview showed only `no_rows` (NVDA and AAPL before US bars), `no_zone` (pre-zones), `baseline` (BTC/THB and XAU/USD Buy runs older than the baseline) and `no_position` (NVDA and PTT.BK on Sell). The other ten verdicts were exercised only by specs and mocks. A first bot entry, still unverified from 2b (FR-ZB-E2E-001/002), would be the first live `placed` (source: raw/2026-10-10-bot-activity.md §Test plan, Preview phases; §Open questions).

## The WatchEntry

```
WatchEntry = { instrument_id, timeframe ('1h'|'1d'), bar_ts | null, zone | null, zone_run_started_at | null,
               zone_age (int >= 0), baseline_at, held, pending_order, rule ('entry'|'exit'|null),
               verdict, reasons: string[], decision_id | null, order_id | null }
```

- `bar_ts`, `zone`, `zone_run_started_at` and `zone_age` come from `zoneRun(rows)`. `zone_age` is the streak over the latest 48 rows; with no rows the four read null, null, null and 0 (see [[market-timeseries]]).
- `held` and `pending_order` are the values the rule was given. `baseline_at` is `bots.status_since` as the pass read it.
- `pending_order` points to the first pending bot order on the instrument, by `(placed_at, order_id)` (R-BA6).
- The new module `watch.ts` holds `WATCH_VERDICTS`, `WATCH_ENTRY_FIELDS`, `WATCH_REASON_SETS`, the `WatchEntry` type, `watchEntryJson` (keys in C11 order, so every C11 example re-renders to identical bytes), `impliedRule` and `checkWatchEntry`.
- **No write-time validation (R-BA9).** `checkWatchEntry` encodes the C11 per-verdict table, but only specs use it. Production does not validate outcomes at write time, because a throwing `finishRun` would strand a run `running`. Migration G's CHECKs guard the `bot_watch` columns.

A constructed C11 example (`baseline`):

```json
{"instrument_id": "AAPL@webull", "timeframe": "1h", "bar_ts": "2026-10-09T19:00:00Z", "zone": "buy",
 "zone_run_started_at": "2026-10-08T15:00:00Z", "zone_age": 18, "baseline_at": "2026-10-09T07:02:13.250Z",
 "held": false, "pending_order": false, "rule": "entry", "verdict": "baseline", "reasons": [],
 "decision_id": null, "order_id": null}
```

(source: raw/2026-10-10-bot-activity.md §API, Shapes and Bot runtime, Entry facts; §Database, Semantics; §Concept, Plan resolutions, Bot)

## Storage (migration G)

Migration G (`20261010061500`, `bot_watch_and_run_outcomes`) adds both objects. The full DDL, harness and down are on [[centralized-migrations]].

- **`bot_watch`**: primary key `(bot_id, instrument_id)`, one row per (bot, universe instrument), overwritten on each evaluation. The columns are the WatchEntry fields plus `evaluated_at` and `run_id`. CHECKs cover `timeframe` (`1h`, `1d`), `zone` (the six CDC zones), `zone_age >= 0`, `rule` (`entry`, `exit`) and `verdict` (the fourteen values). `bot_id` and `instrument_id` have foreign keys. `run_id`, `decision_id` and `order_id` have none, like `decisions.run_id`. The bot fills them only from bot-scoped reads, and the service's joins are scoped to the same bot.
- **`bot_runs.outcomes jsonb NOT NULL DEFAULT '[]'`**: the entries gathered by the evaluation that finished the run (see [[bot-versions-and-runs]]). It is `[]` for rows from before G, for a `running` run, for the version-unsupported run and for the R12 interrupted sweep.
- **Volume.** Six watch rows per bot, overwritten, and one jsonb array of about six entries per run. There is no index beyond the primary key and F's `(bot_id, started_at DESC)`. BA4 keeps everything with no retention job: about 1 KB per run, roughly 15 MB per bot per year, to be revisited at slice 6. On the preview, `pg_column_size(outcomes)` was at most 637 B (average 631 B) over 7 runs of 6 entries (assumption A5 held).

(source: raw/2026-10-10-bot-activity.md §Database; §Concept, Chosen design BA4 and Proposed defaults; §Test plan, Assumption outcomes)

## When the bot writes

**Write order in one evaluation (PRD §4.4–4.5).**
1. The run, if any, is finished by `finishRun` with its status, counts and **outcomes**.
2. Its existing metric and `bots_run_finished` log.
3. `lastSeen` advances.
4. **The watch write**, the evaluation's last I/O. It is stamped `evaluated_at` = the `now` read once at the start of `evaluateBot`. `run_id` is the run this evaluation opened, the on-demand run its first decision-writing intake created (2b R1), or null for a quiet pass.

A quiet pass with no run still writes the watch; that write is the heartbeat. `bots_passes_total{nothing_new}` counts such passes (source: raw/2026-10-10-bot-activity.md §API, Bot runtime, Write order).

**Failure paths.**
- A thrown evaluation error finishes the run `failed` with the error class and **the entries gathered so far**, logs `bots_pass_failed` as before, and writes **no** watch. The rows stay as they were; the failed run and the heartbeat explain the gap.
- The version-unsupported path (2b ORCH-6, including a null `current_version`) is not an evaluation. Its failed run carries `outcomes = []`, and it makes no watch write, because an empty write would delete the rows.
- A failed watch write logs `bots_watch_write_failed` at error level, with exactly `bot_id`, `error_class` (a constructor name) and `code` when a SQLSTATE exists. It does not fail the evaluation, and the next pass retries. There is no once-only memo, so a persistent failure logs every 30 s per bot (a follow-up; the stale line surfaces it).
- An empty universe deletes the bot's rows. Paused bots are not evaluated, so their rows stay as of the last pass.

(source: raw/2026-10-10-bot-activity.md §API, Bot runtime, Failure paths; §Concept, Proposed defaults; §Open questions, Follow-ups)

**The watch statement (`WRITE_WATCH`, `pg-store.ts`).** One statement through the plain query path. A data-modifying CTE deletes the bot's rows whose instrument is not in `jsonb_to_recordset($3)`, then runs `INSERT … ON CONFLICT (bot_id, instrument_id) DO UPDATE`. It never runs inside `transaction()` or the intake, and never takes a lock statement. An instrument listed twice fails it (21000), as does a column check (23514). The memory store mirrors those constraints (`MemoryCardinalityError` carries 21000) (source: raw/2026-10-10-bot-activity.md §API, Bot runtime, The watch statement).

**C4 untouched (R-BA7 / R-BA8).** The watch write comes after the finished run's metric and log and after `lastSeen` advances, in its own catch. Its FK checks take `KEY SHARE` on the `bots` and `instruments` rows only, which does not conflict with Pause's `FOR NO KEY UPDATE`, and it never touches `paper_accounts`. The integration title `writes the watch in one statement outside any transaction, after finishRun, without the account lock` proves three things: the statement runs alone in its checkout after `FINISH_RUN`; it completes while another session holds `paper_accounts … FOR UPDATE`; and the backend holds no `paper_accounts` lock while waiting (see [[paper-trading]] for the C4 lock order) (source: raw/2026-10-10-bot-activity.md §API, Bot runtime, C4 untouched; §Concept, Plan resolutions, Bot).

**`HAS_DECISION` now returns an id (R-BA1).** The SQL changed from `SELECT EXISTS (…)` to `SELECT decision_id … ORDER BY ts, decision_id LIMIT 1`: the suppressing decision, earliest by `ts`, then `decision_id`. `hasDecision` stays the boolean over that read, because existing specs assert booleans, and a new `decisionId` returns the id. The pass calls `decisionId` only on a hit. The read is still lock-free and bound to the bot's own decisions through `decisions_bot_ts_idx`. The intake's SQL text therefore moved, although `intake.ts` is byte-identical (security ℹ️-1) (see [[decision-record]]) (source: raw/2026-10-10-bot-activity.md §API, Bot runtime; §Concept, Plan resolutions, Bot R-BA1).

**Unchanged by contract.** For the same inputs, the pass writes the same decisions, orders, runs, counts, logs and metrics as 2b. Cost: one extra statement per evaluated bot per pass, plus one extra read per suppressed instrument (source: raw/2026-10-10-bot-activity.md §API, Bot runtime, Unchanged by contract).

## Contract C11: `bots-watch-entry.v1.json`

C11 is new in bot-activity and follows the C10 pattern (see [[bot-versions-and-runs]]).

- **Canonical bytes.** 11,941 bytes, ASCII, LF, 2-space indent. File sha256 `9bec3bd8ad5e5aaa1855f29b0d261c475b47795fd2706fe812639699bd94cbc6`.
- **Byte-identical copies.**
  - service `internal/trading/testdata/bots-watch-entry.v1.json`, pinned by `TestWatchEntry_FixtureHash`;
  - bot `packages/bots/fixtures/bots-watch-entry.v1.json`, pinned by `bots-watch-entry-fixture.spec.ts` (4 titles, including the `watchEntryJson` re-render).
  - Copy with `cp`; never re-serialise. A change is a contract change in both repos at once. The fixture is also byte-identical in the planning directory.
- **Direction.** The bot writes and the service reads. The bot's fixtures README had stated this backwards and was fixed in ORCH-10.
- **Keys.** `contract`, `fixture`, `spec`, `instant_format`, `fields` (the 14 WatchEntry names in order), `types`, `timeframes`, `zones`, `rules`, `verdicts` (the per-verdict table), `reasons` (`empty`, `deferred`, `skipped`, `observed`), `reason_rules` and `examples` (16 constructed entries covering every verdict, both deferral reasons and both skip shapes).
- **Instant format.** Inside `bot_runs.outcomes`, instants are RFC 3339 UTC with `Z`, with a millisecond fraction only when non-zero (the bot's `formatTs`, 2b R7). Instants the service renders from `timestamptz` columns use Go's RFC 3339 with up to 9 trimmed fraction digits. Consumers compare instants, never text.
- **jsonb key order (r2 clarification, ORCH-7).** The run detail returns `outcomes::text`, so each entry's keys arrive in jsonb's normalised order (shorter keys first, then bytewise), not in C11 `fields` order. Consumers parse and compare values.
- **Unchanged.** C3–C10, the C4 lock order, the error envelope and snake_case bodies. There is no new Redis key, channel, `/ws` message, environment variable, error code or metric.

(source: raw/2026-10-10-bot-activity.md §Concept, Cross-project contracts; §Concept, Stage, Verified locally; §Concept, ORCH-10)

**The pattern spreads.** Signals-ingest (slice 3a, 2026-10-11) follows the same byte-pinned shared-fixture pattern for C-SIG-1 (`signals-message.v1.json`). It extends the pattern to three repositories: the service, the bot and the web, where the web checks the SHA-256 with `crypto.subtle`. See [[signal-message-contract]] (source: raw/2026-10-11-signals-ingest.md §API, C-SIG-1; §Cross-cutting links).

## The watch route: `GET /bots/{bot_id}/watch`

The route takes no query parameter and answers `{generated_at, checked_at, items: [WatchItem]}`. Errors: 400 for any parameter, 404 for an absent or foreign bot. It mounts on the gated market group with the other `/bots` routes (see [[bot-versions-and-runs]]).

```
WatchItem = WatchEntry & { evaluated_at, run_id | null, display_symbol,
                           decision: {decision_id, action, ts} | null, order: {order_id, status} | null,
                           session: 'open'|'closed'|'unknown', next_open_at | null, next_bar_at | null }
```

- **`checked_at`** = `max(evaluated_at)` over the bot's rows, or null with none. It is the heartbeat.
- **One snapshot (SA5).** The read is one owner-scoped query, with the pointer joins scoped to the same bot. `generated_at` is read once at the start. The `px:last` read runs after the snapshot closes.
- **Universe order.** `watchlist_items.position` ascending, then rows whose instrument has left the watchlist, by `instrument_id COLLATE "C"`.
- **Pointer decoration.** `decision` and `order` come from left joins scoped to the same bot (`d.bot_id = w.bot_id`, `o.bot_id = w.bot_id`) and owner. A pointer to another bot's or user's object renders `null`, and the raw id is kept as stored. Integration plants such pointers and asserts `null`.
- **Session decoration (SA6, R4).** After the database snapshot, one `MGET` of `px:last` for the items' instruments, through the existing `ParseLastPrice` / `NormaliseSession`. A usable record (valid, `stale = false`, `updated_at` within 120 s of `generated_at`, `LivePriceMaxAge`) supplies `session` and `next_open_at`. Otherwise the item reads `unknown` / null. This applies "stale or missing → unknown" literally, unlike Market watch, which passes a present but stale session through (see [[redis-market-contract]]).
- **`next_bar_at` (R5).** The first UTC hour boundary strictly after `generated_at` (08:10:30Z → 09:00Z; exactly 08:00:00Z → 09:00Z). It is set only for `timeframe = '1h'` with `session = 'open'`, and is null for every 1d item and every closed or unknown session. It keys on `bot_watch.timeframe`, not on a separate `instruments.base_timeframe` read.
- **Redis absent never fails the route.** Without `REDIS_URL`, with the subscriber down, or on an `MGET` error, the answer is 200 with every `session: "unknown"` and every `next_*` null. Only the `MGET` error logs the existing warn `last_price_read_failed`. Redis is not a readiness input.
- **Manual bot.** The watch answers `{generated_at, checked_at: null, items: []}` without reading `bot_watch` or Redis.
- **Paused or observing bot.** Rows are answered as last written, with no special case. The web words the head note from `bot.status`.
- The service never computes a verdict, never reads `indicators` for this route and never writes anything.

(source: raw/2026-10-10-bot-activity.md §API, Service routes; §Concept, Plan resolutions, Service SA5, R4, R5)

## How the web words each verdict

The Watch and the expanded Checks rows share one table (see [[bot-activity]]). The copy is sentence case with no hue (`util/watch-view.ts`):

| Verdict | Line | Second line |
|---|---|---|
| `no_rows` | No bars yet | nothing to evaluate |
| `no_zone` | Nothing to do | "{Zone label} is not Buy or Sell" / "no zone yet" |
| `run_start_unknown` | Run start unknown | Buy for 49+ bars — never entered |
| `baseline` | Baseline | Buy run began before the baseline, {d MMM HH:mm} |
| `holding` | Holding | waits for Sell |
| `no_position` | Nothing to do | Sell, no position |
| `pending_order` | Order pending | waits for the fill |
| `decided` | Already decided | "{skip \| buy \| close} at {time}" (then-mode fallback "a decision exists for this bar") |
| `deferred` | Entry waits / Exit waits | venue closed / no live price |
| `placed` | Entered / Exited | "{buy \| close} at {HH:mm} · {order status}" (then-mode fallback "{buy \| close} order placed") |
| `skipped` | Skipped | the reasons through `BOT_REASON_WORDS`, joined " · " |
| `observed` | Observed | observing · no orders |
| `already_placed` | Order already placed | from an earlier pass |
| `nothing` | No action | state changed during intake |

- **Then mode (ORCH-5, amended by ORCH-5a).** Outcomes carry only the `decision_id` / `order_id` pointers. In an expanded check, `decided` and `placed` are decorated exactly like now mode **when the pointer matches data already on the screen** (the Decision record's loaded decisions, or the current watch item's decoration). No request is made to decorate. With no match they use the fallbacks above.
- **PRD over mockup.** *Decided* reads "skip at 14:02"; the mockup's "· insufficient cash" is dropped in both modes.
- **Strict parsing.** An unknown `verdict`, `session`, `rule`, `timeframe` or `zone` value refuses the whole body, so the section shows its error rather than a wrong verdict. `action` and order `status` stay strings and render only through closed maps.

(source: raw/2026-10-10-bot-activity.md §Components, Verdict copy and Data layer; §Concept, ORCH-5 / ORCH-5a; §Concept, Plan resolutions, Web)

**The expanded check's row is now shared (slice 4).** The expandable row that holds a check's then-mode verdicts is now shared with the Signals page's detail rows. Its styles moved from `bots.css` to `table.css` as selector lists for `tr.check-detail` and `tr.signal-detail`. The behaviour is the same in both places: the row is inserted empty and filled one task later, and *Try again* focuses that row's *Hide*. The verdict copy and the rendering are unchanged, and the Bots captures stayed 0-pixel identical (144/144). See [[design-system-decisions]] (source: raw/2026-10-12-signals-page.md §Components, Styles and Expanded row; §Test plan, Acceptance status FR-SP-WEB-010; §Cross-cutting links).

## A second reader: the Chart's stance (charting, slice 5)

Since charting (tidewatch-service #11 and tidewatch-web #14, merged 2026-10-16, not deployed), `bot_watch` has a second reader besides the watch route: the `stance` of a chart head read (see [[chart-read-api]] and [[charting]]).
- **Which row.** One statement selects the session user's oldest `kind = 'auto' AND template = 'zone_transitions'` bot (by `created_at`, then `bot_id`), the bot `systemBots` picks (CH-R10). It `CROSS JOIN LATERAL`s that bot's `bot_watch` row for the instrument. `owner_user_id = $1` is in the bots filter, so another user's bot or rows are never read.
- **What it returns.** `{bot_id, bot_name, bot_status (running|observing|paused), verdict (one of the fourteen C11 values), rule (entry|exit|null), reasons[], timeframe, zone, zone_age, zone_run_started_at, held, pending_order, baseline_at, evaluated_at, decision_id, order_id}`, or `null` when there is no zone bot or no row for the instrument. It never creates a bot (S7).
- **How the web words it (PD8).** The *Right now* panel's *Slack Water* row shows the verdict line and its second line through `watch-view.ts`'s `watchRows`, so the words match the Bots Watch. A null stance reads "Not in Slack Water's universe", and a paused bot shows a *Paused* tag. `watch-view.ts` itself was not changed.
- **Strict reading.** The Chart's readers refuse a whole body with an unknown verdict, as the Bots screen does.
- **Next.** Slice 7 plans a champion stance on the chart; Slack Water's watch verdict stands in until then. Slice 7 (statistics, 2026-10-27) did not build it: its D12 moved the champion stance on the Chart to a follow-on spec, so the Slack Water verdict still stands in (source: raw/2026-10-27-statistics.md §Concept, Owner decisions D12; see [[statistics]]).

(source: raw/2026-10-16-charting.md §API, `GET /instruments/{id}/chart`; §Database, The stance read; §Concept, Accepted defaults PD8, Spec-level S7 and Planner reconciliations CH-R10; §Components, The Chart screen and `ChartService`; §Files touched, Not changed; §Open questions, Deferred by design)

## C11': the general engine's verdicts (slice 6, 2026-10-21)

Since slice 6 (tidewatch-migrations #10, tidewatch-service #12, tidewatch-bot #10 and tidewatch-web #15, merged 2026-10-21, not deployed), v2 bots run the general engine (see [[bots-engine]]). It writes `bot_watch` and `bot_runs.outcomes` the same way, with an extended vocabulary.

- **Nine new verdicts.** `watching`, `gated`, `entered`, `expired`, `added`, `trimmed`, `exited`, `protected` and `no_candidate`. With G's fourteen that makes **23**, which is C11'. Migration J re-creates `bot_watch_verdict_check` with all 23 (see [[centralized-migrations]]).
- **`15m`.** J also re-creates `bot_watch_timeframe_check` as `('15m','1h','1d')`, a recorded sixth CHECK (ORCH-6 OQ-1), because a v2 manager can run on 15m. `4h` stays refused. The web keeps `WATCH_TIMEFRAMES` and adds `WATCH_ENTRY_TIMEFRAMES` (`15m`, `1h`, `1d`).
- **Gates are verdicts (S6).** An unmet entry condition or a failed gate (`cdc_filter`, `elliott_filter`, `impact_below_min`, `p_below_min`, `max_open`, `max_symbols`, `allocation`) is a `gated` verdict, not a decision. Only a hard limit that blocks an otherwise-met entry writes a `skip`.
- **`rule` on general-engine entries (ORCH-9d).** On `deferred`, `skipped` and `observed` entries written by the general engine, `rule` names the evaluation kind (`entry` or `exit`).
- **Guard.** A stale recorded price is `deferred` with `["price_unavailable"]` (ORCH-5d). Guard exposure closes are counted as `trimmed`; stop and invalidation closes appear as `protected`.
- **The fixture.** `bots-watch-entry.v2.json`, byte-identical in the service (`internal/trading/testdata/`, pinned by `TestWatchEntryV2_FixtureHash`) and the bot (`packages/bots/fixtures/`, pinned by `bots-watch-entry-v2-fixture.spec.ts`). In bot S11, `checkWatchEntryV2` was aligned with planner precision P26 as an authorised deviation.
- **Legacy bots.** The 2b pass and its fourteen verdicts are unchanged for v1 configs.

**How the web words the nine (PRD §4.16, `watch-view.ts`).** "Watching / waits for …", "Gated / …", "Entered", "Expired / TTL | invalidated", "Added", "Trimmed", "Exited", "Protected / stop {price} …" and "No candidate". `checks-view.ts` is loop-aware, so a check row names its loop. The readers still refuse an unknown verdict (see [[bot-activity]]).

(source: raw/2026-10-21-bots.md §Database, Altered objects and the six re-created CHECKs; §Concept, Spec decisions S6; §Concept, Rulings ORCH-5/6 and ORCH-9; §Components, Data layer and Bots screen, Watch and Checks; §Files touched, tidewatch-service S1 and tidewatch-bot S3, S11)

## `meta_veto`: the failure gate's veto (learning loop, 2026-10-30)

Since the learning loop (tidewatch-bot #17 and tidewatch-web #21, merged and deployed 2026-10-30; see [[learning-loop]]), a learned version may carry a `meta_gate`, the `logistic_v1` failure model.
- **The veto is a verdict, not a decision.** After the `allocation` gate, a candidate whose `p_loss` is at or above 0.70 gets a `gated` watch verdict with reasons `["meta_veto"]`, and no decision is written (`META_VETO`, `learning/meta-gate.ts:54`). This follows S6 above: a failed gate is a verdict. The bot title is "meta veto is a verdict not a decision".
- **No new verdict and no contract change.** `meta_veto` is a reason on the existing `gated` verdict, so C11' (23 verdicts, `bots-watch-entry.v2.json`) is unchanged, and so is `bot_watch_verdict_check`.
- **A halved size is not a verdict.** For `0.55 ≤ p_loss < 0.70` the manager halves the sized budget and enters as usual; the entry decision records `policy_result.meta {p_loss, effect: "shrink"}` (see [[decision-record]] and [[bots-engine]]).
- **How the web words it.** `watch-view.ts:394` words the reason as "vetoed by the failure model", so the Watch reads "Gated · vetoed by the failure model". The Checks use the same words.
- **Seen on the preview (FR-LL-E2E-002).** On a seeded learned version with an open gate, the high-`p_loss` candidate was `gated ["meta_veto"]` with no decision, and the Watch read "Gated · vetoed by the failure model" on the real service. A capture of the Checks' `meta_veto` words was not taken, which leaves FR-LL-WEB-007 partial.

(source: raw/2026-10-30-learning-loop.md §Concept, A learned version in the engine; §Components, Words elsewhere; §Test plan, Named acceptance tests, Results and What each seeded E2E showed; §Cross-cutting links)

## Related pages

- [[bot-activity]]: the feature overview, the Watch and Checks sections, and acceptance
- [[zone-transition-bot]]: Slack Water and the 2b rules (R3, R6, R13) the verdicts name
- [[bot-versions-and-runs]]: `bot_runs`, now with `outcomes` and `error`, and the runs routes
- [[centralized-migrations]]: migration G and its destructive down
- [[decision-record]]: the decisions that `decided`, `placed`, `skipped` and `observed` point to
- [[paper-trading]]: the C4 lock order the watch write stays outside, and contracts C3 and C10
- [[redis-market-contract]]: the `px:last` record behind `session`, `next_open_at` and the 120 s bound
- [[market-timeseries]]: the strip `indicators` rows behind `bar_ts`, `zone` and `zone_age`
- [[market-data-worker]]: the `bots` runner and its new `bots_watch_write_failed` event
- [[signal-message-contract]]: C-SIG-1, which follows the C11 shared-fixture pattern across three repos
- [[signals-page]]: slice 4, whose Signals detail row shares the expandable row with Checks
- [[chart-read-api]]: the chart route's `stance`, the second reader of `bot_watch`
- [[charting]]: slice 5, whose *Right now* panel words Slack Water's verdict
- [[elliott-regime-labeller]]: slice 5's fixtures, byte-pinned in the C11 pattern
- [[bots-engine]]: the general engine that writes the nine C11' verdicts
- [[bots]]: slice 6, which added C11' and the `15m` watch timeframe
- [[learning-loop]]: slice 8, whose failure gate adds the `meta_veto` reason on `gated`
