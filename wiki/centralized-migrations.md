# Centralized migrations and the required-schema-version contract

**Summary**: All Tidewatch schema lives in one flat goose sequence in the `tidewatch-migrations` workspace resource, and the service declares the one migration version it needs (`RequiredSchemaVersion`) so that readiness stays truthful. The constant and the migration must change together, and a later migration the service does not depend on (such as the corrective migration D) leaves the constant alone. **Since the learning loop (merged and deployed to production 2026-10-30) the constant is migration M's `20261028120100`** (`learning_loop`). M adds `learning_runs`, `calibration_maps` and `post_mortem_proposals`, widens five CHECKs for the `learn` loop and the `post_mortem` stage, and seeds one route. The pin moved L → M. **Migration N `20261028120200` (`signals_context`, the PRD's "L") merged after it on 2026-10-30, completing the settled order L → M → N, and is never pinned.** The service reads no N table or column, and only the bot's SQL harness requires N. Goose order is K, L, M, N. M and N each reached production through the service sync, which confirmed the deploy lesson a second time. From accounts and roles (merged and deployed 2026-10-29) until M, the constant was migration L's `20261028120000` (`accounts_and_roles`). L adds operators, plans, person columns, `events.actor_operator_id` and `model_calls` attribution, and backfills the seeded admin to a plain user. The pin moved J → L, and K was never pinned. **Deploy lesson (2026-10-29, confirmed 2026-10-30):** a migrations-only GitOps bump does not trigger an ArgoCD sync, because the migrate Job is a Sync hook. L, M and N each ran only in the sync that a service image bump triggered. From bots (slice 6, merged 2026-10-21) until L, the constant was migration J's `20261020041046`; statistics (slice 7, merged and deployed 2026-10-27) needed no migration and left it at J, while the migrations head had moved on to K (`20261021082304`, an index). Before that it was I's `20261011182817` (the signals page), H's `20261011020408` (signals-ingest), G's `20261010061500` (bot-activity), F's `20261009122143` (slice 2b) and E's `20261008050550` (slice 2).

**Sources**: `raw/2026-10-05-foundation-auth.md`; `raw/2026-10-07-market-data.md`; `raw/2026-10-07-fix-xau-feed-binance-th.md`; `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-21-bots.md`; `raw/2026-10-27-statistics.md`; `raw/2026-10-29-accounts-roles.md`; `raw/2026-10-30-learning-loop.md`; `raw/2026-10-30-signals-context.md`

**Last updated**: 2026-10-31

---

## Workspace resource, not a project

All schema lives in `tidewatch-migrations`, a centralized workspace resource (`migrationsPath`): one flat goose sequence for the single `tidewatch` database. No service repo holds a `migrations/` directory. Forge models this as a workspace resource (`migrationsPath` plus `migrationsRepo`), not a project (OWNER-3 / ORCH-8). The migration steps were folded into the service plan as MIG1 to MIG3 with an explicit engineer override (ORCH-1), committed to a migrations worktree and shipped as their own PR, which had to merge before or with the service PR (source: raw/2026-10-05-foundation-auth.md §Database; §Concept, Other recorded decisions). Slice 1 repeated the pattern: the steps were folded into the service plan as MIG1–MIG4 (ORCH-1) and shipped as tidewatch-migrations PR #2, merged first on 2026-10-07 (source: raw/2026-10-07-market-data.md §Concept, ORCH-1; §Components, Rollout).

Forge tooling gap (A5): `{{project:tidewatch-migrations}}` resolved for the preview `migrate` build only because of this run's `worktrees.json`. Future runs will fail closed ("Unresolved setup token"), because the helpers accept only registered project IDs and reject the resource slug. Forge needs `migrationsPath` support in its worktree, execution and preview helpers (source: raw/2026-10-05-foundation-auth.md §Concept, A5; §Open questions). See [[forge-preview-gateway]].

## Migrations shipped in slice 0

| Version | Content |
|---|---|
| `20261004153020` (`enable_extensions`) | `CREATE EXTENSION IF NOT EXISTS timescaledb; ... vector;`. Down drops both in reverse order. Runs inside goose's default transaction (assumption A3 validated as not needing `NO TRANSACTION`). |
| `20261004153023` (`auth_foundation`) | The four tables below, their indexes and the append-only trigger. Down is **destructive** (drops the tables and trigger function, each `IF EXISTS`, never `CASCADE`). |

(source: raw/2026-10-05-foundation-auth.md §Database, Migrations)

## Migrations shipped in slice 1 (market data)

| Order | Version | File | Content |
|---|---|---|---|
| A | `20261006100927` | `market_reference.sql` | 16 reference tables and their seeds (venues, calendars, instruments, aliases, universe lists, watchlists, collector cursors and checks) |
| B | `20261006113158` | `market_timeseries.sql` | 3 hypertables (`candles`, `candles_eod`, `indicators`), 3 continuous aggregates, 7 policy jobs and the `candles_daily` view |
| C | `20261006131346` | `market_calendar_exceptions.sql` | 99 calendar exceptions for 2026–2027, and `valid_through` |
| D | `20261007072235` | `market_xau_feed_binance_th.sql` | Corrective, 2026-10-07: one-row `UPDATE instruments` repointing `XAUUSD@oanda-demo` to `feed='binance-th'`, `feed_symbol='XAUTUSDT'`, `name='Gold spot (XAUT proxy)'`; Down restores `oanda` / `XAU_USD` / `Gold spot`. Data only, no CHECK, view or alias change (see [[gold-feed-xaut-proxy]]) |

All four run in goose's default transaction; because `WITH DATA` is refused inside a transaction, B creates its aggregates `WITH NO DATA` (A1). The harness checks migration A's table list for exactness, so a stray table fails the run. What the tables mean is on [[instrument-master]] and [[market-timeseries]] (source: raw/2026-10-07-market-data.md §Database, Migrations and Migration A; §Concept, A1; raw/2026-10-07-fix-xau-feed-binance-th.md §Database).

**Fix forward, never edit.** Next year's calendar exceptions ship as a new migration, never as an edit of C, and a wrong calendar row is fixed forward with a new migration. Never rename, regenerate or edit C (source: raw/2026-10-07-market-data.md §Database, Migration C, Required-schema-version contract and Down migrations). A seed correction is a new migration too: D changes one slice-1 seed row and leaves A's seed file untouched; the migrations README and CLAUDE.md now state the rule (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Database).

**Down migrations are owner-only, local-only and never a recovery path.** D restores the XAU row only; XAU candles and the `binance-th` collector cursor written meanwhile stay (the cursor key includes the collector, so there is no clash with an OANDA cursor). C deletes its exception rows and resets `valid_through`. B drops the view, policies, aggregates and hypertables and **destroys every stored bar and indicator row**. A drops its 16 tables and **destroys every watchlist**, which is user data. `down-to 20261004153023` keeps the auth tables (source: raw/2026-10-07-market-data.md §Database, Down migrations; raw/2026-10-07-fix-xau-feed-binance-th.md §Database, Down caveat).

**Harness changes.** `scripts/check-disposable-db.sh` was generalised: A/B/C assertions, aggregate equality across a refresh boundary, the A1/A2/A11 probes, a fork-and-kill `bounded` helper, and TimescaleDB telemetry off. Review fix `d77efa8` changed only the harness and docs; the SQL is byte-identical to `8a158f1` (source: raw/2026-10-07-market-data.md §Database; §Files touched). For D the harness became phase-gated: `expected_migrations` gained `market_xau_feed_binance_th`, the 18-column instrument projection moved into `instrument_row`, `ref_expected_instruments` holds A's nine untouched rows with the seed and post-D XAU rows beside it, and `assert_market_reference` appends whichever XAU row the phase expects (D's once D is applied, else the seed), so A's exact dump stays valid in every pass; the `absent_` check for D passes when `instruments` is gone (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Database, Harness).

## Migration shipped in slice 2 (simulation engine)

| Order | Version | File | Content |
|---|---|---|---|
| E | `20261008050550` | `simulation_engine.sql` | Nine tables: `venue_rules`, `bots`, `paper_accounts`, `benchmark_members`, `decisions`, `orders`, `fills`, `positions` and `ledger`. Also the three `decisions` triggers, the `ledger` hypertable (28-day chunks, no columnstore, no retention) and six `venue_rules` seeds, each citing a `source` |

- E runs in goose's default transaction.
- Like the earlier slices, it was folded into the service plan as MIG steps (ORCH-1), with its own worktree, branch and PR. It shipped as tidewatch-migrations PR #4: reviewed head `ffe6c27`, merged by the owner as `6531508` on 2026-10-08, first of the four slice-2 PRs.
- What the tables mean is on [[paper-trading]] and [[decision-record]].

(source: raw/2026-10-08-simulation-engine.md §Database; §Concept, Stage and Orchestration)

**Fix forward applies to venue rules too.** A changed fee, slippage or margin number is a data migration. Existing fills keep the numbers they used (`fee_detail`). The TFEX GO initial margin (฿137,550.00, OWNER-1) changes monthly, so expect a data migration each time. FU-2 proposes a later migration to tighten the `venue_rules` CHECK; E keeps the PRD's CHECK as written (source: raw/2026-10-08-simulation-engine.md §Database, Seeds; §Concept, OWNER-1 and FU-2).

**E's down is destructive.** It drops the nine tables in reverse order (`IF EXISTS`, no `CASCADE`), then the two trigger functions. That destroys every order, fill, mark and decision. Only the owner may run it. `scripts/check-disposable-db.sh` gained E's relations, triggers, hypertable, seed assertions, the append-only transcript and the down. It reported PASS 848/0 (source: raw/2026-10-08-simulation-engine.md §Database; §Files touched).

## Migration shipped in slice 2b (zone-transition bot)

| Order | Version | File | Content |
|---|---|---|---|
| F | `20261009122143` | `bot_versions_and_runs.sql` | Two tables, `bot_versions` and `bot_runs` (with index `bot_runs_bot_started_idx`), and three `bots` columns: `template`, `current_version` and `status_since`. Two named constraints: `bots_current_version_fkey` and `bots_kind_template_check`. A backfill sets `status_since = created_at` |

- F runs in goose's default transaction. Its version was an output of MIG1 (ORCH-4/4a).
- As before, it was planned as MIG steps inside the service plan (ORCH-1) but kept its own worktree (`b7ddc75378`), branch and PR. It shipped as tidewatch-migrations PR #5: head `bbf7a87`, merge `1e115c0`, merged by the orchestrator on the owner's instruction on 2026-10-09, first of the four slice-2b PRs.
- `decisions`, `orders`, `fills`, `positions` and `ledger` are unchanged.
- **Write order (MF3).** `bots_current_version_fkey` is MATCH SIMPLE, so a writer inserts `bots` with a NULL `current_version`, then `bot_versions`, then sets `current_version`.
- **Status drift.** `bot_runs.status` adds `running` to the architecture document's three values. This is recorded in PRD §10; `documents/` was not edited (D17).
- What the tables mean is on [[bot-versions-and-runs]].

**F's down is destructive.** It drops the two named constraints, then the three columns, then `bot_runs` and `bot_versions`, each `IF EXISTS` and never `CASCADE`. That destroys every version and run. Only the owner may run it.

**Harness.** `scripts/check-disposable-db.sh` gained F's expected lists, catalog assertions, absent checks and transcripts, plus:
- 14 rolled-back probes that must be refused, among them kind/template mismatches both ways, `running` with `finished_at`, `succeeded` without it, a dangling `current_version`, a non-hex version, `seq = 0`, a duplicate seq and a run naming no version;
- controls that insert a zone bot with the C10 v1 hash;
- a backfill proof with a planted pre-F manual bot in the down/up window. After a future migration G this proof becomes a note.

E's exact `bots` checks became F-aware in the harness only; E's file is unchanged. Result: **PASS 1016/0** (MIG1).

(source: raw/2026-10-09-zone-transition-bot.md §Database; §Concept, ORCH-1 and ORCH-4; §Files touched, tidewatch-migrations; §Open questions)

## Migration shipped in bot-activity (2026-10-10)

| Order | Version | File | Content |
|---|---|---|---|
| G | `20261010061500` | `bot_watch_and_run_outcomes.sql` | One table, `bot_watch`, and one column, `bot_runs.outcomes jsonb NOT NULL DEFAULT '[]'` |

```sql
CREATE TABLE bot_watch (
    bot_id              uuid        NOT NULL REFERENCES bots (bot_id),
    instrument_id       text        NOT NULL REFERENCES instruments (instrument_id),
    evaluated_at        timestamptz NOT NULL,
    run_id              uuid,
    timeframe           text        NOT NULL CHECK (timeframe IN ('1h', '1d')),
    bar_ts              timestamptz,
    zone                text        CHECK (zone IN ('buy', 'pre_buy_2', 'pre_buy_1', 'pre_sell_1', 'pre_sell_2', 'sell')),
    zone_run_started_at timestamptz,
    zone_age            integer     NOT NULL DEFAULT 0 CHECK (zone_age >= 0),
    baseline_at         timestamptz NOT NULL,
    held                boolean     NOT NULL,
    pending_order       boolean     NOT NULL,
    rule                text        CHECK (rule IN ('entry', 'exit')),
    verdict             text        NOT NULL CHECK (verdict IN ('no_rows', 'no_zone', 'run_start_unknown', 'baseline',
                                        'holding', 'no_position', 'pending_order', 'decided', 'deferred', 'placed',
                                        'skipped', 'observed', 'already_placed', 'nothing')),
    reasons             text[]      NOT NULL DEFAULT '{}',
    decision_id         uuid,
    order_id            uuid,
    PRIMARY KEY (bot_id, instrument_id)
);

ALTER TABLE bot_runs ADD COLUMN outcomes jsonb NOT NULL DEFAULT '[]';
```

- G runs in goose's default transaction after F. It was created with `make migrate-create NAME=bot_watch_and_run_outcomes`, and its version was an output of MIG1 (ORCH-3). The code reviewer diffed the CREATE TABLE and ALTER body against PRD §5.1: identical.
- As before, it was planned as MIG steps inside the service plan, because the validators accept only registered projects (ORCH-1). It kept its own worktree (`b7ddc75378`), branch and PR, and shipped as tidewatch-migrations PR #6: range `1e115c0..a474a77`, merge `3ec60a7`, merged first of the four bot-activity PRs on 2026-10-10 on the owner's instruction.
- **No other object.** No index beyond the primary key, no seed, no grant, no change to any other table. `run_id`, `decision_id` and `order_id` have no FK (like `decisions.run_id`). Constraint names are PostgreSQL's defaults (`bot_watch_pkey`, `bot_watch_bot_id_fkey`, `bot_watch_instrument_id_fkey`, `bot_watch_{timeframe,zone,zone_age,rule,verdict}_check`).
- G is additive with no backfill. What the objects mean is on [[bot-watch-verdicts]] and [[bot-versions-and-runs]].

**G's down is destructive.** `ALTER TABLE bot_runs DROP COLUMN IF EXISTS outcomes; DROP TABLE IF EXISTS bot_watch;`, with no `CASCADE`. It destroys every watch row and every run's outcomes; A–F are unaffected. Only the owner may run it, and only locally.

**Harness** (`scripts/check-disposable-db.sh`, +261/−11 together with the G file):
- G joins `expected_migrations`, and `required_migration = bot_watch_and_run_outcomes`.
- `relations_` / `assert_` / `absent_` functions check the exact columns, the primary key, both FKs, the five CHECKs, the single index and the `outcomes` column with its default. "G seeds nothing" is asserted.
- Probes, each in a rolled-back transaction with its own probe user: the PRD's unknown-verdict probe plus 7 more are refused (bad timeframe, zone, negative `zone_age`, bad rule, unknown instrument, unknown bot, duplicate key). 4 controls are accepted: a row with every nullable column null, the bot's `ON CONFLICT … DO UPDATE` upsert, pointers naming nothing, and a `bot_runs` row reading `outcomes = []`.
- F's checks were made G-aware in the harness only: F's exact `bot_runs` column list excludes `outcomes`, and "F is newest" became "F or later". F's file is unchanged.
- Once G is newest, the harness's make down/up window rolls back G, and its existing branch skips F's backfill proof with a note (R10, accepted).
- Result: **1130 PASS / 0 FAIL**. A make down to F then up restores G, and two down-to round trips pass (FR-BA-MIG-001/002).

**Follow-up (harmless).** G's version lands on :00 seconds, and no `make migrate-create` transcript was kept.

(source: raw/2026-10-10-bot-activity.md §Database; §Concept, ORCH-1, ORCH-3 and Plan resolutions, Service R10; §Files touched, tidewatch-migrations; §Open questions)

## Migration shipped in signals-ingest (slice 3a, 2026-10-11)

| Order | Version | File | Content |
|---|---|---|---|
| H | `20261011020408` | `signals_ingest.sql` | 18 tables, 8 indexes and the seeds for sources, the scoring version, model routes and model prices |

- H is one file in goose's default transaction after G, created with `make migrate-create NAME=signals_ingest`. Its version was MIG1's output (ORCH-3). H's content last changed in `8d00dd4`.
- As before, it was planned as MIG steps inside the service plan (ORCH-1) and shipped in its own worktree, branch and PR: tidewatch-migrations PR #7, range `3ec60a7..dd7e150`, merge `e015a3a` (14:59:06Z). **The bot PR merged about one minute earlier**, against the planned "migrations first" order. Nothing deploys automatically.
- The bot harness pins H's sha256 `a77fcf10fd6cd481af3ee347306cc998b3e5ebe53438b65a35a8dcffdbb0520d`.

**Objects: exactly PRD §5.1, with one owner-approved substitution (ORCH-8).** MIG1 verified that the DDL block's sha256 equals the PRD block after that one-line swap.
- **18 tables, in this order:**
  - sources and runs: `sources`, `source_cursors`, `source_files`, `source_runs`;
  - documents: `documents`, `document_versions`, `document_instruments`, `document_quarantine`;
  - model stages: `triage`, `extractions`, `extraction_unresolved`;
  - versions and spend: `scoring_versions`, `prompt_versions`, `model_routes`, `model_prices`, `model_calls`, `model_spend_daily`;
  - output: `signals`.
- **8 indexes:** `source_runs_source_started_idx`, `documents_title_hash_published_idx`, `documents_stage_published_idx`, `document_versions_document_idx`, `document_quarantine_created_idx`, `model_calls_created_idx`, `signals_instrument_created_idx` and `signals_created_idx`.
- **Nothing else:** no other index, trigger or function, and no `ALTER` of an earlier table. `uuidv7()` defaults as in A–G, and PostgreSQL's default constraint names.
- **Closed vocabularies.** `event_type` on `triage` and `signals` is a CHECK of 15 values, so a new event type needs a migration (PRD S12).

**The ORCH-8 deviation.** PRD §4.3 keeps a quarantined document at `stage = 'quarantined'`, with `skip_reason` naming the stage (`triage`, `extraction`, `scoring`). But §5.1's CHECK would refuse that row. H writes instead:

```sql
-- on documents (constraint documents_check), in place of
-- CHECK ((stage = 'skipped') = (skip_reason IS NOT NULL))
CHECK ((stage IN ('skipped', 'quarantined')) = (skip_reason IS NOT NULL))
```

There is no `ingest` value for `skip_reason`. An ingest-time quarantine writes only `document_quarantine` and creates no `documents` row.

**Seeds are data.** H seeds 10 `sources` rows (8 enabled), `scoring_versions` row 1, three `model_routes` and two `model_prices`. It seeds no `prompt_versions`; the bot records those at start. Like A's and E's seeds, a later change is a data migration. Enabling Business Wire, though, is an owner `UPDATE` of its row. What the objects mean is on [[source-registry-and-ingest]], [[signals-pipeline]] and [[model-routes-and-spend]].

**H's down is destructive.** It runs `DROP TABLE IF EXISTS` for the 18 tables in reverse order, never `CASCADE`. That deletes every source, run, document, extraction and signal, and the spend ledger. Only the owner may run it, and only locally. A–G are unaffected.

**Harness** (`scripts/check-disposable-db.sh`, MIG2): **1330 PASS / 0 FAIL**.
- H's lists, `relations_/assert_/absent_signals_ingest`, and the exact catalog of the 18 tables.
- `H seeds: sources …`, which compares the ten rows as jsonb.
- More than 20 refusal probes matched on constraint names, such as `documents_canonical_url_key`, `triage_event_type_check`, `signals_direction_check` and the ORCH-8 probe `a quarantined document without skip_reason`.
- Accepted controls, including `quarantined|extraction`.
- Make down/up and round trips that now roll back H.

**Follow-up.** An index on `documents (source_code, external_id)` for withdraw and external-id lookups.

(source: raw/2026-10-11-signals-ingest.md §Database; §Concept, ORCH-1, ORCH-3 and ORCH-8; §Concept, Stage, Merged; §Files touched, tidewatch-migrations; §Open questions)

## Migration shipped in the signals page (slice 4, 2026-10-12)

| Order | Version | File | Content |
|---|---|---|---|
| I | `20261011182817` | `user_settings.sql` | One table, `user_settings`, and one index, `decisions_signal_ids_gin_idx` on `decisions` |

```sql
-- +goose Up
CREATE TABLE user_settings (
    user_id    uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    key        text        NOT NULL CHECK (key ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){0,3}$' AND length(key) <= 64),
    value      jsonb       NOT NULL CHECK (octet_length(value::text) <= 8192),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, key)
);

CREATE INDEX decisions_signal_ids_gin_idx ON decisions USING gin (signal_ids);

-- +goose Down
DROP INDEX IF EXISTS decisions_signal_ids_gin_idx;
DROP TABLE IF EXISTS user_settings;
```

- I runs in goose's default transaction after H. Its SQL is PRD §5.1 byte for byte, and its version was MIG1's output, not a guessed timestamp (ORCH-3).
- **Shipping.** As before, I was planned as MIG steps inside the service plan, because `workspace.json` registers only web, service and bot (ORCH-1). The MIG billets live in the service namespace (TS-75…77). I kept its own worktree (`b7ddc75378`, a manual helper mirror added to `worktrees.json`), branch and PR. It shipped as tidewatch-migrations PR #9, range `4d05646..090e809`, merge `52deb26` at 18:29:07Z on 2026-10-12, first of the three code PRs.
- **No other object.** I adds no trigger, function, view or seed, and changes no earlier table. Constraint names are PostgreSQL's defaults (`user_settings_pkey`, `user_settings_user_id_fkey`, `user_settings_key_check`, `user_settings_value_check`). `CREATE INDEX` on the append-only `decisions` is DDL, which its triggers do not intercept (see [[decision-record]]).
- **What the objects serve.** `user_settings` holds one row per (user, key); see [[user-settings]]. The GIN index serves the Signals page's lookups of citing decisions. The list and the export use `&&`, and the summary uses `@>`; GIN `array_ops` serves both (see [[signals-read-api]]).
- **Docs.** The migrations README and `CLAUDE.md` move the pin to I, list H as "the pin until I", and note the destructive down past I.

**I's down is destructive for settings only.** It drops the index and `user_settings`, which deletes every stored preference. No decision data is touched. Only the owner may run it, and only locally.

**Harness** (`scripts/check-disposable-db.sh`):
- I joins `expected_migrations`, and `required_migration=user_settings`.
- `relations_user_settings` prints `user_settings|r`. `assert_user_settings` checks the index by name, definition and access method `gin` (R2).
- Six probes are refused, each in a rolled-back transaction: an upper-case key, a 65-character key, a key with five segments, a value over 8192 octets, an unknown user, and a duplicate (user, key).
- Four controls are accepted: a `signals.filters` row with `updated_at` defaulted; a `signals.seen_through` row; `ON DELETE CASCADE` removing a deleted user's rows; and an `EXPLAIN` of `signal_ids @> ARRAY[...]` under `enable_seqscan = off` that names the index.
- E's exact `decisions` index list leaves out `decisions_signal_ids_gin_idx` by name, and only while I is applied (MI5).
- The make down/up window and the down-to round trips run `absent_user_settings`.
- Result: **1,436 PASS / 0 FAIL** on the orchestrator's re-run (the engineer's run gave 1,434).

**Follow-up (wording only).** I's header and the migrations README say `@>`, but the list and the export use `&&`.

(source: raw/2026-10-12-signals-page.md §Database; §Concept, Orchestrator rulings ORCH-1 and ORCH-3; §Concept, Stage, Merged; §Files touched, tidewatch-migrations; §Open questions, Service follow-ups)

## Migration shipped in bots (slice 6, 2026-10-21)

| Order | Version | File | Content |
|---|---|---|---|
| J | `20261020041046` | `bots_candidates_and_requests.sql` | Three tables (`candidates`, `bot_version_events`, `bot_run_requests`), `bots.probation_until` with `bots_probation_check`, six re-created CHECKs, two `model_routes` seeds and one `model_prices` row |

- J runs in goose's default transaction, with no trigger, function or view. The PRD §5.1 block appears verbatim (74 lines, byte-identical); the price row and the timeframe statement follow it, so the block stays unedited.
- Its header cites the A5 constraint names (verified on the disposable database at base `52deb26`), the price row's URL and read time, and the ORCH-6 deviation. J's version, the large-tier price row and the CHECK names were outputs of the MIG step (ORCH-3), and the version is recorded in `planning/tidewatch-service/j-version.txt` (OQ-3).
- **Shipping.** As for G, H and I, J was planned as MIG steps inside the service plan (ORCH-1), with its own worktree (`b7ddc75378`), branch and PR. It shipped as tidewatch-migrations PR #10, range `52deb26..7a2cc41`, merge `cd378a3` at 04:08:15Z on 2026-10-21, first of the four slice-6 PRs. File sha256 `89d1ea84…a476`.
- **New tables.** `candidates` (described on [[bots-engine]]): two indexes including the partial `candidates_live_instrument_idx`, and CHECKs on direction, `p`/`impact` in [0, 1], `thesis_source`, horizon, the four entry conditions, positive prices, `state`, `state_reason` and the state/reason pairing. `bot_version_events` and `bot_run_requests` (described on [[bot-versions-and-runs]]), the latter with the partial unique key `bot_run_requests_pending_key (bot_id, loop) WHERE taken_at IS NULL`.
- **The six re-created CHECKs**, each dropped and re-created by its verified existing name:

| Constraint | Before J | After J |
|---|---|---|
| `bots_template_check` | `manual, zone_transitions` | `manual, news_drift, filings_only, zone_transitions, blank` |
| `bot_watch_verdict_check` | G's fourteen verdicts | the fourteen plus `watching, gated, entered, expired, added, trimmed, exited, protected, no_candidate` (23, = C11') |
| `bot_watch_timeframe_check` (ORCH-6 OQ-1 deviation) | `1h, 1d` | `15m, 1h, 1d` |
| `model_routes_stage_check` | `triage, extraction, scoring` | plus `bot_decide, bot_thesis` |
| `model_calls_stage_check` | `triage, extraction, scoring, eval` | plus `bot_decide, bot_thesis` |
| `prompt_versions_stage_check` | `triage, extraction, scoring` | plus `bot_decide, bot_thesis` |

- **Seeds.** `bot_decide (jev, jev-1.13.0, small_llm, anthropic/claude-haiku-5.5)`, `bot_thesis (openrouter, anthropic/claude-haiku-5.5, NULL, NULL)` and the price `(openrouter, anthropic/claude-sonnet-5.5, 2.00, 10.00, 2026-10-20)`. After J, `model_routes` has 5 rows and `model_prices` 3; `prompt_versions` gets no seed (see [[model-routes-and-spend]]).
- `decisions` is unchanged; `candidates` holds foreign keys into it (see [[decision-record]]).

**J's Down is DESTRUCTIVE, owner-only and local-only, never a recovery path.** It runs in reverse order with `IF EXISTS` and no `CASCADE`: it deletes only J's own seed rows (the price row by its `valid_from`), narrows the six CHECKs back, drops `probation_until` and its CHECK, and drops the three tables with every row. It fails loudly while a bot uses a new template, a watch row uses a new verdict or `15m`, or a `model_calls`/`prompt_versions` row uses a bot stage. J has no grants, so "owner-only" is a procedure, not an enforced permission.

**Harness** (`scripts/check-disposable-db.sh`, +642/−17):
- J joined the exact lists with its catalog (3 tables, 3 PKs, 13 FKs, 14 CHECKs, 7 indexes), the re-created CHECKs and the seed counts (5 and 3). The E–H checks were made J-aware.
- **FR-BT-MIG-002 refusal probes, rolled back:** a closed candidate without a reason, a second pending request, probation while running, stage `bot_foo`, and `4h` refused after `15m`/`1h`/`1d` were accepted; 13 refusals and 6 controls.
- **FR-BT-MIG-003 round trips:** a down to I fails loudly while a `news_drift` bot exists, then a clean down and back.
- **Caveat** (MIG3 fact check): only the `news_drift` case of the loud Down failure is round-tripped; the other narrowed-CHECK refusals follow from J's Down but are not tested separately.
- **Follow-up FU-3:** the next migration should add `bot_run_requests (bot_id, loop, requested_at DESC)` for the *Run now* rate-limit window.

(source: raw/2026-10-21-bots.md §Database; §Concept, ORCH-1, ORCH-3, ORCH-5/6 OQ-1 and OQ-3; §Concept, Stage, Merged; §Files touched, tidewatch-migrations; §Open questions, FU-3 and Service security notes)

## No migration in statistics (slice 7, 2026-10-27)

- **No schema change.** Slice 7 added no table, column, index or environment variable, and tidewatch-migrations was not changed (PD10). `RequiredSchemaVersion` stays J (`20261020041046`). Everything it writes already existed: `decisions.post_mortem` (migration E, under the `decisions_backfill_only` trigger), `bots.champion`, and the `promoted`/`demoted` kinds of `bot_version_events` that J reserved for this slice.
- **The migrations head is K** (`20261021082304`, an index), later than J and not pinned, the same pattern as D. Production was at J or later, and the slice-7 preview was migrated to K (goose `20261021082304`).
- **Explicitly out (D10):** an `attribution_snapshots` table (until its trigger: a Stats read over 500 ms on the preview, or 50,000 decisions) and a `bot_id` on `model_calls`.
- **An index needs the owner first (A7).** On the preview, `period=all` sequence-scans `decisions` at a 99.7 % single-bot skew, while `30d` and the losses read use `decisions_bot_ts_idx`. Timing stayed under 500 ms, and no index was proposed or added (see [[stats-read-api]]).
- **`documents/` drift** (never edited): `02-architecture.md` §11 lists `post_mortems` and `attribution_snapshots` tables, and `07-statistics.md` lists `attribution_snapshots`; post-mortems live in `decisions.post_mortem`.
- **Rollback** is a revert of the merge commits; there is no schema to roll back.

(source: raw/2026-10-27-statistics.md §Database; §Concept, Owner decisions D10 and PD10; §Concept, Assumptions A7; §Test plan, Preview runs; §Open questions, Rollout and production and `documents/` drift)

## Migration shipped in accounts and roles (2026-10-29)

| Order | Version | File | Content |
|---|---|---|---|
| L | `20261028120000` | `accounts_and_roles.sql` | `operators`, `operator_sessions`, `plans` (one `founder` seed row) and `password_setup_tokens`. Eight new `users` columns with the backfill and six constraints, `events.actor_operator_id` with an index, and `model_calls.bot_id`/`user_id` with an index |

- **Shipping.** tidewatch-migrations PR #16, merge `080979d` (2026-10-29 07:00:39Z), file sha256 `1decf74c…03b7` after SPEC-2. It was planned as MIG steps S1–S3 in its own worktree (`b7ddc75378`).
- **Locks.** L runs in goose's default transaction. Until commit it holds ACCESS EXCLUSIVE locks on `users`, `events` and `model_calls`, and SHARE ROW EXCLUSIVE on `bots`.
- **The Up is PRD §5 byte for byte.** The objects:
  - **`operators`:** a lowercase unique `username`; `role IN ('owner','staff')`; an E.164 unique `phone`; `must_change_password DEFAULT true`; and `disabled_at`.
  - **`operator_sessions`:** a SHA-256 `token_hash` and a partial index on active sessions per operator.
  - **`plans`:** `plan_id` matching `^[a-z][a-z0-9_]{1,31}$`, `max_active_auto_bots`, `daily_model_usd numeric(10,6)`, `decision_tiers` restricted to `none`/`jev`/`small_llm`/`large_llm`, `live_trading DEFAULT false`, and `starting_capital_thb >= 10000`.
  - **The `users` columns:** `display_name`, `email`, `phone`, `status DEFAULT 'active'`, `plan_id`, `created_by_operator_id`, `disabled_at` and `updated_at`.
  - **The `users` constraints and indexes:** `users_plan_id_fkey`, `users_display_name_check` (1–80), `users_email_check` (lowercase), `users_phone_check` (E.164), `users_status_check` (`invited`, `active`, `disabled`, `pending_verification`, `suspended`) and `users_disabled_check` (`status = 'disabled'` exactly when `disabled_at` is set), plus the partial unique indexes `users_email_key` and `users_phone_key`.
  - **`role` default.** `users.role` now defaults to `'user'` and still has no CHECK; the service enforces it. `updated_at` has no trigger; the service sets it (F10).
- **The backfill (FR-AR-MIG-002).** `UPDATE users SET role = 'user', display_name = username, plan_id = 'founder'` runs before `display_name` and `plan_id` become NOT NULL. Every pre-L row keeps its id, hash, sessions and everything it owns, and reads `status = 'active'` from the default. On a copy of the retained preview database every table count and md5 fingerprint was identical before and after L (E2E-005, see [[accounts-and-roles]]).
- **A3 held.** `ALTER TABLE events ADD COLUMN`, its foreign key and its index are DDL, which the append-only triggers (`events_append_only`, `events_append_only_truncate`) do not intercept. The harness proved it over an empty and a non-empty `events`.
- **Only hashes are stored.** Operator sessions store the token's SHA-256 only. `password_setup_tokens` stores token hashes only and has no writer in Phase A.
- **Attribution columns.** `model_calls.bot_id` and `user_id` are nullable. Rows written before L and every signals-stage row read NULL, so pre-rollout bot spend is not attributed (see [[model-routes-and-spend]]).
- **Seeds are data.** The only seed is the `founder` row. A changed founder value or a second plan is a data migration, never an edit of L.
- **Who writes what.**
  - The service writes `operators`, `operator_sessions`, the new `users` columns and `events.actor_operator_id`.
  - The bot writes `model_calls.bot_id` and `user_id`.
  - Only the seed writes `plans`. The service's `Entitlements` and the bot's evaluated-bots join read it.
  - Nothing writes `password_setup_tokens`.

**L's Down is destructive, owner-only, local-only, and never a recovery path.**
- **Order:**
  1. Drop the `model_calls` attribution.
  2. Drop `password_setup_tokens`.
  3. Drop `events.actor_operator_id`.
  4. Drop the email and phone indexes.
  5. **`UPDATE users SET role = 'admin' WHERE status = 'active'`** (SPEC-2).
  6. Drop the six `users` constraints and eight columns, restoring `role DEFAULT 'admin'`.
  7. Drop `plans`, `operator_sessions` and `operators`.

  Everything uses `IF EXISTS`, with no `CASCADE`.
- **SPEC-2 (as built over PRD §8).** Only active people get `admin` back, so a rollback never re-admits a disabled or invited person. PRD §8's "the Down restores `role = 'admin'`" is superseded.
- **What it destroys:**
  - every operator and operator session;
  - the plan and the setup tokens;
  - every person's display name, email, phone, status, creator and disable time;
  - the `model_calls` attribution;
  - **the operator actor of every audit event.** The `DROP COLUMN` on `events` is DDL that the append-only triggers do not stop.
- **Owner steps before any Down** (L header, migrations README runbook; security S-2 and R2-N1…N3):
  1. Export the operator-attributed events and the `operators` table without `password_hash`, to an absolute path outside every repository. Delete the export once the rollback settles.
  2. Record the non-admin ids before re-applying L. Re-applying makes everyone `active` again, so the owner re-disables people right after `goose up`.
  3. If the owner is locked out after a Down, run `UPDATE users SET role='admin' WHERE username='<owner>'`.
  4. Roll back in this order: revert the three images, then run `make migrate-down` locally against a copy first.

**Harness** (`scripts/check-disposable-db.sh`):
- **Exact lists for L:** the catalog, relations, columns, constraints and indexes, the founder seed, and the A3 probes. The slice-0 and H lists leave L's objects to L by name, only while L is applied. `users` fixtures go through `users_insert`, keyed on whether `users.plan_id` exists.
- **Probes.** 31 refusals over 29 constraints, each matched by constraint name, and 11 accepted controls, among them an `events` row with both actor columns set. All are rolled back, in each of 7 passes with L applied.
- **Round trips.** Then down-to K and up twice, down-to the auth migration and up, and down-to 0 and up, re-running every assertion after each round trip (ten assertion passes): `check-disposable-db: PASS`.
- **Summary lines.** With L newest, J's and K's down-proofs print "not run", never "passed".
- **Follow-up.** Five pre-L harness summary claims overstate: FR-ZB-MIG-001, FR-BA-MIG-002, FR-SIG-MIG-001, FR-SIM-MIG-003 and FR-ZB-MIG-003.

(source: raw/2026-10-29-accounts-roles.md §Database; §Concept, Spec corrections SPEC-2 and PD-1; §Concept, Owner decisions D16; §Concept, Stage; §Open questions, Recorded follow-ups, Migrations)

## Migration shipped in the learning loop (slice 8, 2026-10-30)

| Order | Version | File | Content |
|---|---|---|---|
| M | `20261028120100` | `learning_loop.sql` | `learning_runs`, `calibration_maps` and `post_mortem_proposals`; five re-created CHECKs (`learn` on two loop columns, `post_mortem` on three stage columns); one `model_routes` seed row |

- **Shipping.** tidewatch-migrations PR #14, merge `8feeae3` (head `d28de68`), file sha256 `3b68d1be…ba51d`. MIG1–MIG3 were planned in the bot plan and committed in one commit, `6f776c0`, in the migrations worktree `b7ddc75378`. The feature's overview is on [[learning-loop]].
- **The letter.** The PRD (S21) and intent D3 called it "L". The parent coordination settled it as **M** on 2026-10-27, because accounts-roles took L and signals-context takes N. **Every "L" in the learning-loop spec reads M.** M was first written on K, with J as the pin, and was merged onto `main` + L in the branch update (below).
- **The Up is PRD §5.1 verbatim** from `-- +goose Up` through the last Down statement; the header (lines 1–38) is the only addition. It runs in goose's default transaction, with no trigger, function or view.
- **The objects:**
  - **`learning_runs`:** `learning_run_id uuid PK DEFAULT uuidv7()`; `bot_id` → `bots`; `bot_version` and `saved_version`, each with `bot_id` a composite foreign key to `bot_versions`; `run_id` with no foreign key (like `decisions.run_id`); `trigger IN ('scheduled','manual')`; `started_at`, `finished_at`; `status IN ('running','succeeded','failed')` and `error`; `window_from`, `window_to`; `seed` matching `^[0-9a-f]{16}$`; `floors`, `summary`, `counts` (`jsonb NOT NULL DEFAULT '{}'`); `draft_config`, `draft_status IN ('proposed','saved','dismissed')`, `dismissed_reason IN ('user','superseded')`; `report text CHECK (octet_length(report) <= 65536)`. Four table-level CHECKs tie `status = 'running'` to a null `finished_at`, `draft_config` to `draft_status`, `saved` to `saved_version` and `dismissed` to `dismissed_reason`. PostgreSQL named them `learning_runs_check` and `learning_runs_check1`…`check3`, and the harness matches them by those names. Indexes: `learning_runs_bot_started_idx (bot_id, started_at DESC)` and the partial unique `learning_runs_pending_draft_key (bot_id) WHERE draft_status = 'proposed'`, one pending draft per bot.
  - **`calibration_maps`:** `map_id` PK; `bot_id`, `(bot_id, bot_version)` → `bot_versions`; `learning_run_id` → `learning_runs`; `tier IN ('jev','small_llm','large_llm')`; `horizon IN ('intraday','days','weeks')`; `method IN ('isotonic','platt')`; `points jsonb` (`[["p","y"], …]` for isotonic, `{"a","b"}` for Platt, as decimal strings); `n_fit`, `n_test ≥ 0`; `ece_raw_oos`, `ece_map_oos numeric(6,4) ≥ 0`; `proposed boolean`; `UNIQUE (learning_run_id, horizon, method)`.
  - **`post_mortem_proposals`:** `decision_id uuid PK` → `decisions`; `bot_id` → `bots`; `learning_run_id` → `learning_runs`; `label` in the seven post-mortem labels; `rationale` of 1–240 characters; `model_id`; `prompt_version`; `cost_usd numeric(10,6) ≥ 0`; `proposed_at`. Index `(bot_id, proposed_at DESC)`. Append-only by convention: one row per decision, never updated or deleted. Bot security N-5 notes there is no composite foreign key from a proposal to its bot.
  - **Five CHECKs dropped and re-created:** `bot_runs_loop_check` and `bot_run_requests_loop_check` as `loop IN ('scout','manager','guard','learn')`; `model_routes_stage_check` and `prompt_versions_stage_check` with `post_mortem` added; `model_calls_stage_check` with `post_mortem` added beside `eval`. The five names were verified on the disposable database (A2).
  - **The seed:** `('post_mortem', 'openrouter', 'anthropic/claude-haiku-5.5', NULL, NULL)`. Six routes exist after M; Haiku's price row was already seeded, so M adds no price (see [[model-routes-and-spend]]).
- **What M did not add.** No `learned` column (S1: learned is derived from `config.learning`) and no change to any existing table's columns. The `bot_id` and `user_id` on `model_calls` came from L.
- **Who writes what.** The bot writes `learning_runs` (except the draft's saved or user-dismissed end state), `calibration_maps`, `post_mortem_proposals` and the superseding dismissal in a run's final transaction. The service writes a draft's `saved` or `dismissed (user)` state and `saved_version`. Details are on [[learning-loop]].

**M's Down is destructive, owner-only, local-only, and never a recovery path.**
1. Delete the `post_mortem` route.
2. Narrow the five CHECKs back.
3. Drop `post_mortem_proposals`, `calibration_maps` and `learning_runs`, with `IF EXISTS` and no `CASCADE`.

It **fails loudly** (goose exit 1, M kept whole) while a `bot_runs` or `bot_run_requests` row has loop `learn`, or a `model_calls` or `prompt_versions` row has stage `post_mortem`. In production both kinds of row exist once a learning run has happened. It leaves `decisions.post_mortem` proposals in place, because they are decision data. It ran only in the disposable harness.

**Harness** (`scripts/check-disposable-db.sh`, +736/−40 at MIG2):
- **FR-LL-MIG-001:** the catalog, the three tables, the five re-created CHECKs by name, the seed count of 6 routes, and the pin summary moved to M (224 PASS lines at MIG2).
- **FR-LL-MIG-002:** 82 PASS lines of rolled-back refusal probes, each matched by constraint name: a second `proposed` draft, an eighth label, a 241-code-point rationale, `saved` without `saved_version`, `dismissed` without a reason, `running` with `finished_at`, a `learn` request or run before M, and a `post_mortem` call and prompt row accepted after M (including a `model_calls` row with a NULL `document_id`, A1).
- **FR-LL-MIG-003** (37 PASS lines): four committed probes make the Down fail while M stays whole; then the down and up round trip. The Down leaves L applied, and every A–L assertion passes there.
- **Exact lists.** F's and J's exact assertions defer to M by constraint name while M is applied.
- **After the branch update onto L** (`49f06b9` + `d28de68`): M and L round trips with L between K and M; `make migrate-validate` 15 files; `check-disposable-db: PASS` with 4,153 PASS and 0 FAIL. J's down-to-I round trip is reported "not run", because with L between it would run L's destructive Down. **M's header still says it applies on K with J as the pin**; it was left unedited because the file is reviewed and its SHA recorded.

**Preview note.** The learning-loop preview applied M on a clean K-level database without L, then applied L out of order with `goose -allow-missing` for PV6 (see [[forge-preview-gateway]]).

(source: raw/2026-10-30-learning-loop.md §Database, Migration M, Notes on the schema, The Down, Harness and Who reads and writes what; §Concept, Decisions during the build, Letter M and Preview DB; §Concept, Spec corrections, The migration is M; §Concept, Branch update onto L; §Concept, Stage, Implemented; §Files touched, tidewatch-migrations; §Test plan, Results and Not verified or partial; §Open questions, Recorded follow-ups, Bot)

## Production rollout: migrations ride the service sync (lesson, 2026-10-29)

Production deploys run through GitOps: a merge to `main` runs deploy-prod, which pushes to GHCR and bumps tidewatch-kubernetes, and ArgoCD syncs the bump. **The migrate Job is a hook of the `tidewatch-service` chart: a Sync-phase hook at wave −1 (`argocd.argoproj.io/hook: Sync`).** A failed migration blocks the service Deployment.

**What happened with L.**
- At 07:00:39Z migrations #16 merged, and at 07:10:58 its GitOps bump `988d34d` changed only `migrate.image`.
- Hooks are not part of ArgoCD's diff, so that bump left the app "in sync", and **L did not run**. At 07:11:28 ArgoCD `tidewatch-service` was still on `db77ef3`.
- The service #18 and bot #19 merges followed at 07:11:46 and 07:11:51.
- L ran at 07:25:10, in the sync triggered by the **service** image bump `e832d20`. The new service rolled about 30 s later (Recreate).
- **The bot rolled independently of that sync,** at 07:19:12. Its evaluated-bots read joins `plans`, which did not exist yet, so it logged 12 `bots_pass_failed` with Postgres 42P01 (undefined table), one per 30 s pass, until L applied. From 07:25:41 on, the bot ran clean.

**The rule for the next schema change:**
- A migrations-only GitOps bump does not apply a migration.
- A migration needs either a service image bump in the same rollout or a manual ArgoCD sync.
- Merge a schema change's service PR right after its migration PR, so the hook and the new service roll in one sync.
- A bot that needs the new schema logs failed passes until the service sync applies the migration. Expect that window, or hold the bot until after the sync.

**Related production cautions recorded for L.** Once L is applied, the old service refuses product requests. The new service exits at start without its Vault entries, and the Deployment strategy is Recreate. So confirm Vault before merging the migration.

(source: raw/2026-10-29-accounts-roles.md §Concept, Rollout to production; Lesson recorded (GitOps and hooks))

**Confirmed a second time with M (2026-10-30).**
- Migrations #14 merged as `8feeae3`, and deploy-prod ran. GitOps commit `c376f6e` bumped `migrate.image` only, and **no ArgoCD sync followed**.
- Service #16 merged as `3f8627a`. ArgoCD synced the service's GitOps commit `166610b`, and the migrate Job (Sync hook, wave −1) **applied M in that sync**. `/info` then reported `3f8627a`, and `/ready` answered 200 with the schema ok.
- **This time the service went before the bot, on purpose.** The bot has no schema-version check, so a bot rolled before M would have failed its learning queries against an L-only database, the same class as L's 42P01 window. The order was migrations → service → bot → web, and the bot rolled clean with its `learning` collector started.
- **The web went straight after the service,** because the admin audit list is closed and an older web's strict reader would refuse the new `learning_draft_dismissed` type (see [[operator-console]]).
- **The rule stands:** a migrations-only GitOps bump does not apply a migration. A rollout needs a service image bump in the same rollout, or a manual sync, and the service must sync before any consumer that needs the new schema rolls.

(source: raw/2026-10-30-learning-loop.md §Concept, Rollout to production; Why this order; Lesson recorded (GitOps and hooks), confirmed a second time)

## Migration shipped in signals context (spec 3b, 2026-10-30)

| Order | Version | File | Content |
|---|---|---|---|
| K | `20261021082304` | (an index) | never pinned |
| L | `20261028120000` | `accounts_and_roles.sql` | see above |
| M | `20261028120100` | `learning_loop` | the learning-loop build (see [[learning-loop]]); **the required schema version** |
| N | `20261028120200` | `signals_context.sql` | three `sources` rows, `context_versions`, `theme_rules`, `domain_rules`, `gkg_mentions`, `context_features`, `event_calendar`, and `signals.origin`; **never pinned** |

- **The letter (ORCH-2).** The PRD calls this migration "L". Two sibling builds started at the same time and own L ([[accounts-and-roles]]) and M ([[learning-loop]]), so this build's letter is N, and it merged after them (ORCH-5). Shipped as tidewatch-migrations #15, merge `89669e8` (2026-10-30 19:40:46Z).
- **Planned inside the bot plan (ORCH-1),** in a companion worktree with its own PR, because the bot is N's only writer and its harness pin is the one that moves.
- **Pins.**
  - **The required schema version is M (`20261028120100`), set by learning-loop.** The service's `RequiredSchemaVersion` and the migrations harness `required_migration` are both `learning_loop`.
  - **N is never pinned.** The service reads no N table or column, `signals.origin` included. This build never moved a pin (intent D7: the migration is additive, and the service pin does not move for it).
  - Only the bot's `scripts/sql-integration.sh` requires N: anchored lookup `^[0-9]{14}_signals_context[.]sql$`, applied and not newer than the newest applied version, with its SHA-256 recorded. After the M update it keeps L's and M's checks and records the SHA-256 of H, J, L, M and N.
  - The service's `scripts/integration-test.sh` also requires N in the checkout, for its data only.
- **Shape.** Additive on K, in goose's default transaction, with no trigger, function, view or extension. `signals.origin` (`NOT NULL DEFAULT 'document'`, CHECK `document`/`context`) is the only change to an earlier table. Constraint names are PostgreSQL's defaults (`gkg_mentions_check`, `context_features_check`, `context_features_check1`, `theme_rules_check`, `event_calendar_check`, `signals_origin_check`).
- **Hypertables and policies.** `gkg_mentions`: 7-day chunks, columnstore after 30 days, **90-day retention (N's one retention policy)**. `context_features`: 28-day chunks, columnstore after 90 days, no retention.
- **Seeds:** three `sources` rows (`gdelt-gkg-en`, `gdelt-gkg-translation`, `finnhub-earnings-calendar`), `context_versions` v1, 37 `theme_rules`, 9 deny `domain_rules`, and 11 economic `event_calendar` rows (10 FOMC, 1 BoT MPC). US CPI and payrolls are not seeded (FR-SC-MIG-003 partial). **Seeds are data:** a change to a rule, constant, source row or calendar row is a new data migration, never an edit of N, and next year's calendar rows ship as a new migration.
- **Down** is destructive and owner-only. It removes policies before hypertables, then the rules and constants, then the three sources' signals, document rows, quarantine rows, documents, runs, files, cursors and rows, in dependency order. Every statement uses `IF EXISTS`, never `CASCADE`.
- **Harness** (`scripts/check-disposable-db.sh`). It appends `signals_context` to `expected_migrations` and adds `relations_`, `assert_`, `absent_` and `hypertables_signals_context`. H's exact `signals` lists and B's job list leave N's objects to N by name. **Merge-M resolution:** while N is the newest migration, J's and M's down tests (steps 10d and 10e) report "not run", never "passed". N's down is proven wherever a down crosses N (`down-to 20261021082304`, `down-to 20261004153023`, `down-to 0`). `check-disposable-db` PASS (10 passes, 0 FAIL).
- **A new script,** `scripts/check-gkg-themes.sh`, checks each seeded theme against GDELT's theme lookup (FR-SC-MIG-002).
- **Release note for API clients.** After N, re-posting a pre-N bot config without the three new `source_weights` entries is `400 config.source_weights missing`, not `409 version_unchanged` (see [[bot-versions-and-runs]]).
- **Production rollout.** N reached production through the **service's** sync, following the lesson above. The migrations deploy bumped `migrate.image` 8 s before the service bump, so the sync that rolled service `ef9e93e` ran N. The record infers this from the bump order; it holds no production `goose_db_version` read.

What N's objects hold is on [[gdelt-gkg-ingest]], [[context-features-and-coverage-signals]] and [[event-calendar]] (source: raw/2026-10-30-signals-context.md §Database; §Concept, Build-time decisions worth keeping; §Concept, Merge updates (ORCH-5))

## Auth tables (slice 0)

The tables follow PRD section 5 exactly, with no extra CHECKs (decision M6). The service enforces what the schema leaves out: allowed `role` values, the length of `token_hash`, `last4` and `user_agent` (truncated to 512), and the session lifetime. Lockout and rate-limit state are not stored (D12).

- **`users`**: `uuidv7()` primary key (Postgres 18 provides it, A7), unique lowercase `username`, PHC argon2id `password_hash`, `role` default `admin`, `must_change_password` default true, `created_at`, `last_login_at`.
- **`sessions`**: primary key, `user_id` with `ON DELETE CASCADE`, unique SHA-256 `token_hash` (bytea), `created_at`, `last_seen_at`, effective `expires_at`, `ip`, `user_agent`, `revoked_at`; a partial index on active sessions per user.
- **`events`**: a plain table, not a hypertable. Identity primary key, `occurred_at`, `type`, nullable `actor_user_id`, `ip`, `user_agent`, `request_id`, `detail jsonb`; three indexes on time, type and actor. Triggers `events_append_only` (BEFORE UPDATE OR DELETE, per row) and `events_append_only_truncate` (BEFORE TRUNCATE) call `events_reject_mutation()`, which raises "events is append-only".
- **`api_credentials`**: table only in slice 0. `venue`, `label`, `enc_blob` (AES-256-GCM nonce, ciphertext and tag, written in a later slice), `last4`, timestamps, and a unique index on `(venue, label)` where not revoked.

(source: raw/2026-10-05-foundation-auth.md §Database, Tables)

**Changed by migration L (2026-10-29).**
- **`users`:** `role` now defaults to `user`. The table gained `display_name`, `email`, `phone`, `status`, `plan_id`, `created_by_operator_id`, `disabled_at` and `updated_at`.
- **`events`:** gained `actor_operator_id`, never set together with `actor_user_id`.
- **New tables:** operators have their own `operators` and `operator_sessions` (see above) (source: raw/2026-10-29-accounts-roles.md §Database, Migration L).

How these tables are used is described on [[auth-model]] and [[operator-console]].

## The required-schema-version contract

- The constant `RequiredSchemaVersion` in `tidewatch-service/internal/platform/postgres/schema.go` is **`20261028120100`** since the learning loop (migration M, `learning_loop`, merged and deployed 2026-10-30; `schema.go:33`).
  - **The pin moved L → M.** M applies on L. `TestReady_LearningSchema_NotReady` migrates a database to L and expects `/ready` 503; `TestContract_RequiredSchemaVersion` checks the constant against the checkout.
  - **The bot.** Still no compiled constant. Its `scripts/sql-integration.sh` pins M by the anchored lookup `learning_loop`, keeps L, J and H asserted, refuses to run without L and M applied, and logs `required schema version: 20261028120100 (learning_loop) applied`.
  - **The service's integration runs** take `TIDEWATCH_MIGRATIONS_DIR=<checkout at M>`.
  - **Rollout order:** migrations → service → bot → web, so the service sync applies M before the bot rolls (see the lesson above).
  - **The last sibling.** signals-context (N, `20261028120200`) merged after M on 2026-10-30, once its branches were updated onto `main` with M (source: raw/2026-10-30-learning-loop.md §Open questions, Sibling builds). **N is newer and never pinned**, the same pattern as D and K: the service reads no N table or column. The bot's `scripts/sql-integration.sh` also requires N. `TestContract_RequiredSchemaVersion` is one of signals context's named service tests, and the service integration run after the M update passed 5,531 with 0 FAIL (source: raw/2026-10-30-signals-context.md §Database, Pins; §Test plan, Executable checks and Recorded results).
- From accounts and roles until M the constant was **`20261028120000`** (migration L, `accounts_and_roles`, merged 2026-10-29).
  - **The pin moved J → L.** K (`20261021082304`, index-only) was never pinned; PD-1 corrects FR-AR-MIG-004's "list K as the pin until this".
  - **Readiness.** A database below L answers `/ready` 503 (`TestReady_AccountsSchema_NotReady`).
  - **The bot.** It has no compiled constant. Its `scripts/sql-integration.sh` finds L by the anchored lookup `ls migrations | grep -E '^[0-9]{14}_accounts_and_roles[.]sql$' | cut -c1-14` and refuses to run without it (`required schema version 20261028120000`).
  - **Rollout order:** migrations → service and bot → web. In production, apply it through the service sync (see the lesson above).
  - **The siblings.** learning-loop (M) and signals-context (N) were built before L merged. They must update their branches onto the new `main` and re-pin their `RequiredSchemaVersion` and harness lists after L, before they merge. learning-loop did so on 2026-10-29 and merged on 2026-10-30 (above) (source: raw/2026-10-29-accounts-roles.md §Database, Migration L; §Concept, Decisions during the build PD-1; §Test plan, Named acceptance tests and Results; §Open questions, Sibling builds).
- From bots until L the constant was **`20261020041046`** (migration J, `bots_candidates_and_requests`, merged 2026-10-21). The service answers `/ready` 503 on a database below J (`TestReady_BotsSchema_NotReady`). The bot has no compiled schema check; its `scripts/sql-integration.sh` refuses to run unless J is applied. **Owner action:** apply J to the owner's own database before running the merged service and bot, then the web. Rollout order: J first, then the service and the bot together (they share J's seeds, C4'', C11', C12 and C13), then the web (source: raw/2026-10-21-bots.md §Concept, Operations; §Concept, Stage, Deployed).
- The signals page pinned **`20261011182817`** (migration I, `user_settings`, merged 2026-10-12). A database migrated only through H answers `/ready` 503 (`required version 20261011182817 not applied`), and `TestReady_SignalsIngestSchema_NotReady` proves it. `TestContract_RequiredSchemaVersion` was revised on purpose. The anchored lookup is `ls migrations | grep -E '^[0-9]{14}_user_settings[.]sql$' | cut -c1-14`. **The bot is not built for this change (ORCH-5).** Its harness requires H applied and the newest applied version not older than H, which I satisfies. The stale bot sentence "it equals the service's RequiredSchemaVersion" (`tidewatch-bot/CLAUDE.md` and README) was corrected by the docs-only tidewatch-bot PR #9, merged as `ece175a` (ORCH-5a). **Owner action:** apply I to the owner's own database (`make migrate-up` in tidewatch-migrations) before running the merged service. I is additive with no backfill. Rollback is `make migrate-down`, which drops `user_settings` and the GIN index. Rollout order: migrations, then service, then web (source: raw/2026-10-12-signals-page.md §Database; §Concept, ORCH-5 and ORCH-5a; §Test plan, Named acceptance tests; §Open questions, Documentation and owner actions).
- Signals-ingest pinned **`20261011020408`** (migration H, `signals_ingest`, merged 2026-10-11). A database migrated only through G answers `/ready` 503 (`required version 20261011020408 not applied`), and the new `TestReady_BotWatchSchema_NotReady` proves it. `pgtest` has the anchored lookup `^([0-9]{14})_signals_ingest\.sql$` (`SignalsIngestVersion`), and `scripts/integration-test.sh` checks that exactly one H file exists. The bot's `scripts/sql-integration.sh` asserts H and pins its SHA-256. The intent's F pin was stale, and ORCH-5 moved the pin G → H. **Owner action:** apply H to the owner's own database (`make migrate-up` with their `DATABASE_URL`, or the compose `migrate` container). H is additive with no backfill. Rollback is `make migrate-down`, which drops all 18 tables (source: raw/2026-10-11-signals-ingest.md §Database; §API, Schema pin; §Concept, ORCH-5; §Open questions, Owner actions).
- Bot-activity pinned **`20261010061500`** (migration G, `bot_watch_and_run_outcomes`, merged 2026-10-10). A database migrated only through F answers `/ready` 503 (`required version 20261010061500 not applied`); `TestReady_BotVersionsSchema_NotReady` (F only → 503 with G's message) proves "503 before G" (R11). The migrations README and CLAUDE.md moved the required version from F to G with the anchored lookup. The bot still has no schema constant; `scripts/sql-integration.sh` asserts G is applied. **Owner action:** apply G to the owner's own database (`make migrate-up` with their `DATABASE_URL`) before running the merged service. Rollback is `make migrate-down`, which drops both G objects (source: raw/2026-10-10-bot-activity.md §Database; §Concept, Plan resolutions, Service R11; §Files touched; §Open questions, Owner action).
- Slice 2b pinned **`20261009122143`** (migration F, `bot_versions_and_runs`, merged 2026-10-09). A database migrated only through E answers `/ready` 503 (`required version 20261009122143 not applied`). In the service, `internal/pgtest/migrate.go` uses an anchored lookup on `_bot_versions_and_runs.sql`, and `scripts/integration-test.sh` checks that exactly one F file exists. The bot still has no schema constant; its `scripts/sql-integration.sh` asserts that F is applied. **Owner action:** apply F to the owner's own database (`make migrate-up`) before running the merged service (source: raw/2026-10-09-zone-transition-bot.md §Database; §Files touched; §Open questions, Owner action).
- Slice 2 pinned **`20261008050550`** (migration E, `simulation_engine`, merged 2026-10-08). D (`20261007072235`) was never pinned, so the pin moved straight from C to E (source: raw/2026-10-08-simulation-engine.md §Database).
- Slice 1 pinned **`20261006131346`** (migration C, `market_calendar_exceptions`). The anchored lookup is `ls migrations | grep -E '^[0-9]{14}_market_calendar_exceptions[.]sql$' | cut -c1-14`, and the literal in both repos' docs is authoritative (source: raw/2026-10-07-market-data.md §Database, Required-schema-version contract).
- History: in slice 0 the constant was `20261004153023`, the prefix of `migrations/*_auth_foundation.sql`, found with the same anchored lookup on `_auth_foundation` (source: raw/2026-10-05-foundation-auth.md §Database, Required-schema-version contract).
- Until C is applied, the service answers `503 not_ready` on `/ready`, `/auth/*`, every market route and `GET /ws`; `TestReady_SchemaWait` walks 503, 503, 503, 200 (source: raw/2026-10-07-market-data.md §Database; §Components, Rollout).
- **Migration D (`20261007072235`) is later than C and not pinned.** The service does not depend on it, so the constant stays at C and `/ready`, which checks C's `is_applied` by version, tolerates the newer row (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Database; §Concept, Caller-visible implications).
- The bot has no compiled constant. Its `/ready` checks only the database and Redis. Its SQL harness (`scripts/sql-integration.sh`) used to assert that the applied maximum equals C's version; since the XAU fix it enumerates D as optional (so it still runs against a migrations checkout without D), requires C `is_applied`, requires D applied when present, accepts a newer maximum, hashes A–D and records both the required and the newest applied version (source: raw/2026-10-07-market-data.md §Database, Required-schema-version contract; raw/2026-10-07-fix-xau-feed-binance-th.md §Database).
- The service's `/ready` `schema` check passes only when the newest `goose_db_version` row for that version has `is_applied = true`. The `extensions` check requires both extensions in `pg_extension`.
- **The constant and the migration move together.** When the service starts to depend on a later migration, the constant and that migration change in the same change, and the migrations PR merges before or with the service PR. Both repos' `CLAUDE.md` and `README.md` document this.
- `TestContract_RequiredSchemaVersion` in the service integration suite fails if the constant and the migrations checkout drift apart.
- D10: the service starts without the schema and waits. Both listeners bind immediately, a background waiter refreshes the database, schema and extensions snapshot every 2 s, and `/ready` returns 503 until the schema is present. `/ready` went 503, 503, 200 as the schema and extensions appeared (outcome O2).

(source: raw/2026-10-05-foundation-auth.md §Database, Required-schema-version contract; §Components, Startup and readiness; §Concept, O2)

## Tooling and safety rules

- goose `v3.27.3`, pinned in both the `Makefile` (`GOOSE_VERSION`) and the `Dockerfile`, run with `go run` (no global install). The `mssql` dependency, `migrate.mjs` and the `DB_*` variables are gone.
- Make targets: `migrate-up`, `migrate-status`, `migrate-validate` (no DB needed), `migrate-down` (one version; destructive, owner-only), `migrate-create NAME=<snake_case>`, `check-disposable-db`, `help`. The Makefile reads `DATABASE_URL` from `.env`. npm aliases wrap the same commands and add no npm dependencies.
- **Tracking table and env hygiene.** The tracking table is always `goose_db_version`. Every goose call passes `-env none -table goose_db_version`, and `GOOSE_DRIVER`, `GOOSE_DBSTRING`, `GOOSE_TABLE` and `GOOSE_MIGRATION_DIR` are unset. Without that, goose v3.27.3 merges a stray `GOOSE_DBSTRING` into its arguments and prints the full DSN, and `GOOSE_TABLE` silently moves tracking (decision M8).
- **Migrate image.** goose is built in `golang:1.26-alpine` and runs on `alpine:3.22`, non-root (UID 10001), with no `.env*` in the image. The entrypoint runs `up` through `scripts/dsn-guard.sh`, which validates the DSN first (naming only `DATABASE_URL` and a reason class) and masks goose output. A rerun with nothing pending exits 0.
- **D9.** A one-shot `migrate` container is the only place migrations apply automatically, and only to the local compose database.
- **`make check-disposable-db`** is the only sanctioned agent apply. It owns a throwaway `timescale/timescaledb-ha:pg18` container, always removes it, and never reads `.env`, the caller's `DATABASE_URL`, `GOOSE_*` or `PG*`.
- **DSN passwords** must be URL-safe or percent-encoded; in the root compose `POSTGRES_PASSWORD` is restricted to `[A-Za-z0-9._~-]`.
- **Recovery** from a lost password is the CLI reset, never a down migration.

(source: raw/2026-10-05-foundation-auth.md §Database, Tooling; §Concept, Related decisions; §Components, Operations)

## Verified behaviour

The disposable-database round trip (up, status, down, up, down-to 0, up) passed with catalog checks, and UPDATE, DELETE and TRUNCATE on `events` fail with "append-only". FR-MIG-005 passed on the preview and the owner compose (first run exit 0; rerun reports "no migrations to run. current version: 20261004153023"). Merged as `87ce578` on 2026-10-05 (source: raw/2026-10-05-foundation-auth.md §Test plan).

Slice 1: `make migrate-validate` and `make check-disposable-db` passed at `d77efa8` with 43/43 commands exiting 0, 641 PASS lines and 0 FAIL over seven passes, covering up, `down-to 20261004153023`, up, `down-to 0` and up, on PostgreSQL 18.6 and TimescaleDB 2.30.2. Merged as `cb93cd5` on 2026-10-07. `timescale/timescaledb-ha:pg18` is a floating tag, so an image bump may need the harness updated (source: raw/2026-10-07-market-data.md §Test plan; §Files touched; §Components, Rollout).

Migration D: `make migrate-validate` parsed 6 files (D in a transaction, Up 1 / Down 1) and `make check-disposable-db` printed `check-disposable-db: PASS` with 649 PASS / 0 FAIL in 3m03s, covering D's exact row and `updated_at >= created_at`, the seed row back after `make migrate-down`, the `down-to 20261004153023` and `down-to 0` round trips, and A's named-constraint probes and alias dump with the new row; the pin summary reads `market_calendar_exceptions version: 20261006131346 <- RequiredSchemaVersion` beside `market_xau_feed_binance_th version: 20261007072235`. Shipped as tidewatch-migrations PR #3 and merged as `a2e7f81` on 2026-10-07 (source: raw/2026-10-07-fix-xau-feed-binance-th.md §Test plan, Results recorded).

## Related pages

- [[foundation-auth]] — the slice-0 overview
- [[market-data]] — the slice-1 overview that added migrations A–C
- [[gold-feed-xaut-proxy]] — the corrective fix that added migration D
- [[simulation-engine]] — the slice-2 overview that added migration E
- [[paper-trading]] — what E's trading tables and `venue_rules` hold
- [[decision-record]] — E's append-only `decisions` table and its triggers
- [[zone-transition-bot]] — the slice-2b overview that added migration F
- [[bot-versions-and-runs]] — what F's `bot_versions`, `bot_runs` and new `bots` columns hold, and G's `outcomes`
- [[bot-activity]] — the feature overview that added migration G
- [[bot-watch-verdicts]] — what G's `bot_watch` rows and verdict values mean
- [[signals-ingest]] — the slice-3a overview that added migration H
- [[source-registry-and-ingest]] — what H's source, run and document tables hold
- [[signals-pipeline]] — what H's model-stage and `signals` tables hold, and the ORCH-8 stages
- [[model-routes-and-spend]] — H's seeded routes and prices, and the spend ledger
- [[signals-page]] — the slice-4 overview that added migration I
- [[user-settings]] — what I's `user_settings` holds, and its keys
- [[instrument-master]] — what migrations A, C and D hold
- [[market-timeseries]] — what migration B holds, and the aggregate refresh rules
- [[auth-model]] — how the `users`, `sessions` and `events` tables are used
- [[forge-preview-gateway]] — the preview that builds `migrate` from this resource
- [[bots]] — the slice-6 overview that added migration J
- [[bots-engine]] — what J's `candidates` table holds
- [[statistics]] — slice 7, which needed no migration and left the pin at J
- [[accounts-and-roles]] — the feature that added migration L and moved the pin J → L
- [[operator-console]] — what L's `operators`, `operator_sessions` and `events.actor_operator_id` serve
- [[learning-loop]] — the feature that added migration M and moved the pin L → M
- [[signals-context]] — spec 3b, which added migration N (never pinned)
- [[gdelt-gkg-ingest]] — what N's `theme_rules`, `domain_rules` and `gkg_mentions` hold
- [[context-features-and-coverage-signals]] — what N's `context_versions`, `context_features` and `signals.origin` hold
- [[event-calendar]] — what N's `event_calendar` and its economic seeds hold
