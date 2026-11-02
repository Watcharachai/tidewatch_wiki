# Signals page (`signals-page`, slice 4): today's signals with provenance, a quiet live feed, and acting on a signal through the decision record

> Since slice 3a, signals existed only as a count cell on Market watch. Slice 4 gives them a screen. `/signals` now lists today's signals (the Bangkok day), newest first, with trust bars by tier, the headline, the instrument, direction and probability, an impact bar, and a Bots column that reads the decisions citing each signal. The title line reads "N today · N acted on by bots · N contradicted by price". Filters are pill chips held in the URL and stored per user. A row expands in place to three columns (Extracted, Model view, Context at the time) and up to three actions. *Buy/Sell with recommendation* opens `/trade` pre-filled at 10% of equity (the Slack Water rule), and the resulting order's decision now records the signal id, `followed_recommendation`, a `signal_snapshot` and `model`. A signal published while the page is open is counted in a quiet "N new signals · Show" note and is never inserted on its own. The rail shows an unseen count that agrees across devices. Migration I (`20261011182817`) adds `user_settings` and a GIN index on `decisions.signal_ids`. The service gained eight gated routes, an all-signals `/ws` feed backed by `PSUBSCRIBE sig:*`, the signal-citing `decision_ctx`, and the error code `signal_not_applicable`. The bot is unchanged. All code PRs merged on 2026-10-12 at 18:29Z on the owner's instruction: tidewatch-migrations #9 (`52deb26`), tidewatch-service #10 (`8b18486`) and tidewatch-web #12 (`da6f4cb`). Two P0 preview checks were **unverified** at merge because the preview had no suitable data: FR-SP-E2E-003 (no filing, wire or structured-source signal existed) and FR-SP-E2E-004 (no signal had a usable price, so no recommendation was offered). The owner knew this when they gave the instruction.

**Sources (inputs to this document).**
- Spec: `/Users/maichinu/tidewatch/tidewatch-specs/signals-page/build-prompt.md`, `intent.md` (D1–D4, PD1–PD13, O1–O5), `prd.md` (§4–§11, S1–S12, A1–A6, FR-SP-*), `mockup.html` (the chosen visual target, D4). Fingerprints matched at build start: intent `b83ab24f…f3bb`, prd `2d3acb27…7748`, mockup `25f7f536…1908`.
- Build record: `/Users/maichinu/tidewatch/.forge/features/signals-page/state.json` (log, `ownerDecisions`, `followUps`, `runtime.acceptance`, previews), `planning/cross-plan-decisions.md` (ORCH-1…19, ORCH-5a), `verification.md`, `planning/tidewatch-service/contracts.md` (r2 plus the §12 revision note), `review/tidewatch-{service,web}/*.md`, `evidence/preview/P3/index.md`.
- Plans: service and migrations `/Users/maichinu/tidewatch/.forge/docker/runs/sigp-4081ec46/worktrees/329891b601/.plans/signals-page.md` (MIG1–MIG3, S1–S8, MI1–MI6, R1–R21); web `/Users/maichinu/tidewatch/.forge/docker/runs/sigp-4081ec46/worktrees/5eb4e5c7ea/.plans/signals-page.md` (approved r3; S1–S12, SP-W-1…24, D-1…D-10).
- Merged code, read in the run's worktrees: migrations `…/worktrees/b7ddc75378`, service `…/329891b601`, web `…/5eb4e5c7ea`, together with each project's `CLAUDE.md`.

## Concept

### Stage, stated precisely

| Stage | Status (state.json, last update 2026-10-12T18:30:01Z) |
|---|---|
| Implemented | Migrations MIG1–MIG3; service S1–S8 plus review-fix r1 (`539a07e`); web S1–S12 plus fix rounds r1 (`ff3a6c1`), r2 (`031d40e`, e2e only), r3 (`f2e5b01`), r4 (`8dffcfb`) and the P6 docs commit (`0ebc5cc`, `DESIGN.md` only). |
| Verified locally | Every step's contract commands exited 0 on the orchestrator's re-run. Migrations harness: 1,436 PASS / 0 FAIL. Service: `make ci` and `make test-integration` passed on every step; one run hit the pre-existing harness port-collision flake and passed on re-run. Web: 3,001 unit tests in both time zones (default and `TZ=America/New_York`), lint, build and e2e lint/tsc, all at `8dffcfb`. |
| Reviewed | **Plans:** service r1 CHANGES REQUESTED (1 blocking / 4 should-fix / 8 notes), then r2 APPROVED (0/1/3). Web r1 CHANGES REQUESTED (4/11/10), r2 APPROVED (0/2/4), then r3 APPROVED (0/1/2) after an S8 scope gap. **Code:** service code r1 APPROVED (0/1 should-fix/8 nits), security r1 APPROVED (3 low), code r2 delta APPROVED. Web angular r1 APPROVED (8 follow-ups), security r1 APPROVED (1 low), code r1 APPROVED (2 should-fix), code r2 delta APPROVED. Web design r1 CHANGES REQUESTED (B1: the table did not fit at 1100 once a bot name appeared in the Bots cell); r2 APPROVED at `8dffcfb`. |
| Verified on a preview | Partly. FR-SP-E2E-001 (injected publish), 002, 005 and 006 passed. **003 and 004 are unverified** (data). FR-SP-WEB-010 (rendered design review) passed. The P1 mocked Playwright suite passed: 749 / 0 failed / 4 skipped on the final image. Bots 0-pixel diff: 144/144 identical. See Test plan. |
| Merged | Yes, 2026-10-12, with merge commits and remote branch deletion, in order: migrations#9 head `090e809` → `52deb26` (18:29:07Z), service#10 head `539a07e` → `8b18486` (18:29:14Z), web#12 head `0ebc5cc` → `da6f4cb` (18:29:21Z). Owner instruction in chat: "merge it all for me and continue". No CI is configured on any repo. |
| Deployed / owner's own stack | Not deployed beyond the local preview. Whether I has been applied to the owner's own database is not recorded. The merged service answers `/ready` 503 until I is applied. |
| Documentation pass | The ORCH-5a docs-only bot PR tidewatch-bot#9 (the pin sentence in `tidewatch-bot/CLAUDE.md` and README) merged 2026-10-12T18:31Z as `ece175a`; this wiki update. |

### Problem

Signals had existed since slice 3a (merged 2026-10-11), but the only place they appeared was a count cell on Market watch. The owner had nowhere to read a signal together with its provenance, the model's view and the market context at the time. There was also no way to act on a signal that left a trace in the decision record. The brief lists this as the owner's second feature: "a place to check news, its impact, and the instruments it touches, with the provenance and the model's view visible, so trust is earned row by row." The roadmap's slice-4 exit test is: new signals appear without a reload; the expanded row shows extracted / model / context; *Buy with recommendation* opens the ticket pre-filled.

The starting state, verified at `origin/main` on 2026-10-11:
- **Decision columns.** `decisions.signal_ids`, `signal_snapshot`, `model` and `followed_recommendation` existed but had never been written.
- **Order path.** `POST /orders` accepted only `decision_ctx` `{followed_recommendation: null, candidate_id: null, signal_ids: []}`.
- **`/ws`.** It forwarded `signal` frames only to connections subscribed to that instrument, and a connection may hold at most 100 subscriptions.
- **Settings.** No table stored per-user settings; the theme lived in `localStorage` only.
- **Route.** `/signals` rendered the slice-0 placeholder.

### Chosen design (owner decisions D1–D4, Spec studio 2026-10-11, each the recommended option)

- **D1 The Bots column reads the decisions that cite the signal, else "No bot acted".** "Acted on by bots" counts bot-actor decisions only. The owner's own signal-cited orders read "You bought 16.2 · followed" and are not counted. Rejected alternatives: leaving the column out until slice 6; showing any bot trade on the instrument after the signal, which would attribute zone trades to news and corrupt slice 7's attribution. No bot cites signals until slice 6, so the count is 0 today by design.
- **D2 *Buy with recommendation* pre-fills instrument, side and 10% of equity, labelled as Slack Water's rule.** The decision records the signal id, `followed_recommendation = true` and a snapshot holding the suggested quantity and the rule (`equity_pct_10`). The number is a convention, not a forecast, and the label says so.
- **D3 Filters and the badge's "seen through" live in the database** (migration I `user_settings`, settings routes, a badge route). Rejected: `localStorage`, and URL-only with no badge. A "since last visit" count is only true when every device agrees on what has been seen.
- **D4 A browser-verified mockup on the real tokens is the visual target.** Where it differs from `DESIGN.md`, `DESIGN.md` wins, except the pieces named in PRD §7.6: the pill chip, trust bars, direction tones, impact bar, the 860px table minimum with the ≤ 1250 density, the sticky `.detail-wrap`, `.nav-count` and the note-slot new-rows line.

**Accepted defaults the build implemented (PD1–PD13, S1–S12).**
- One row per `signals` row (document × instrument). The instrument cell names its siblings.
- 50 rows per page, with a keyset cursor bound to the day and filters.
- The UI shows today only; the API takes `day` for export and later use.
- Trust bars come from a closed map by tier: filing 5, exchange 4, wire 4, media 3, account 2.
- Direction uses the `.change-up/down/flat` tone classes.
- "Contradicted" means p ≥ 0.600, a directional call, and a move against the call larger than one daily ATR.
- The export is a CSV of at most 10,000 rows.
- The badge refreshes on navigation and every 5 minutes and is hidden on `/signals`.
- No live badge elsewhere, no day control, no "Not this time" skip, no Elliott or regime values ("Arrives with Charting"), no decay recomputation, and no bot change.

### Cross-project contracts (`planning/tidewatch-service/contracts.md`, owned by the service planner, ORCH-2)

- **r1:** the first pin of `SignalRow`, `SignalDetail` (with `context` and `recommendation`), the summary, badge, sources, settings keys, the `/ws` operations and acknowledgements, the export columns, the `decision_ctx` body, the `signal_snapshot` / `model` shapes and the new error code.
- **r2 (ORCH-8):**
  - The list envelope gains `hidden_by_threshold`.
  - Guidance: clients send the response's `day` with every `cursor` and `since` read, so *Load more* and *Show* never cross Bangkok midnight.
- **§12 revision note (ORCH-3):** I = `20261011182817`, MIG1's output, read from `evidence/tidewatch-service/MIG1/required-schema-version.txt`.
- The web froze r2 as `planning/tidewatch-web/contracts-r2.md`. Its parsers and mocks follow it byte-for-byte where the contract gives example bodies.
- **Unchanged:** the C-SIG-1 `signal` frame bytes (fixture `signals-message.v1.json`, sha256 `a0829396…e7d1`, byte-identical in bot, service and web).

### Owner decisions taken during the build (ORCH-5a, 8–11, 13–19)

| ID | When (UTC) | Decision |
|---|---|---|
| ORCH-5a | 2026-10-11T17:53Z | The stale bot pin sentence (`tidewatch-bot/CLAUDE.md` line ~249, "it equals the service's RequiredSchemaVersion", and the README note) is corrected by a **docs-only bot PR in the documentation pass**: no code, harness or image change, and not a build target. |
| ORCH-8 | 2026-10-11T18:09Z | The service adds a hidden-by-threshold count to `GET /signals`: the day's signals matching asset/tier/source with `impact < min_impact`. The web shows "· {n} more under Impact ≥ {t}" only when it is > 0. |
| ORCH-9 | 2026-10-11T18:09Z | A4 (the export link's cookie) is checked on the preview only. The development half is reported unverified, and the shared dev database is never migrated by the build. |
| ORCH-10 | 2026-10-11T18:26Z | The signal context **survives a 5xx or network failure** (unknown outcome), so a retry re-sends a byte-identical body under the same `client_order_id`. It is dropped after any definite answer (2xx, or any 4xx including `signal_not_applicable`). This departs from PRD §4.6's "whatever the outcome code". |
| ORCH-11 | 2026-10-11T18:26Z | Flipping the ticket's side away from the recommendation keeps citing the signal, with `followed_recommendation: false`; flipping back restores `true`. An instrument change still drops the context; a quantity edit keeps `true`. |
| ORCH-13 | 2026-10-12T03:32Z | Preview finding F1: the Model view's Impact line now shows the **real freshness at creation**, `exp(−ln2 · (created_at − published_at) / half_life)` with half-lives intraday 2 h, days 24 h, weeks 120 h, computed in the web. The factors then multiply to the stored impact. PRD §4.5's "freshness 1.00" premise was wrong against 3a §4.11 (NVDA: the factors gave 0.2753, but the stored impact was 0.1568 because freshness was 0.5697). Web only. |
| ORCH-14 | 2026-10-12T03:32Z | Code review SF2 / preview F2: a well-formed pre-fill for an instrument that is not on the watchlist shows a hint on Trade, "{symbol} isn't on your watchlist, so this ticket can't trade it. Add it on Market watch.", instead of being ignored silently. No context is held. |
| ORCH-15 | 2026-10-12T03:32Z | Preview F3: a signal pre-fill sets the order type to **Market**. Before, it stayed Limit with an empty price. |
| ORCH-16 | 2026-10-12T07:30Z | Design B1: the Bots cell's lines **wrap** (max about 112–120px), so the table fits 862/862 at 1100 whatever the data. Rows with long bot lines grow taller; `DESIGN.md`'s "61px rows" became "at least 61px". |
| ORCH-17 | 2026-10-12T07:30Z | Design W1: the sub line reads "Loading…" only until the first successful list load. After that, a failed filter change or reload keeps the day's counts, since they ignore filters. This supersedes review-fix r1's literal reading of §4.13. |
| ORCH-18 | 2026-10-12T07:30Z | The owner authorised a fourth web fix round past the cap of 3. It covered ORCH-16/17 plus polish: *Quantity* spans the row when *Limit price* is hidden (market and manual-fill venues), a steady sticky-detail inset (`left: 17px`, 10px at ≤ 600), and `DESIGN.md` wording. |
| ORCH-19 | 2026-10-12T18:24Z (01:24 on 10-13 Bangkok) | After the owner saw an empty page after Bangkok midnight: **keep today-only for this build**, and add a day control (Today/Yesterday or a last-7-days picker, `?day=`) as a follow-up after the merge. The API already takes `day`. |

### Orchestrator rulings (ORCH-1…7, 12)

- **ORCH-1.** Migration I is planned as MIG steps inside the service plan, because `workspace.json` registers only web, service and bot. The migrations repo keeps its own worktree (`b7ddc75378`, a manual helper mirror added to `worktrees.json`), branch and PR, and merges first. MIG billets live in the service namespace (TS-75…77).
- **ORCH-2.** The service plan pins the shared contracts. The web planner conformed to them before returning ready.
- **ORCH-3.** I's version is an execution output (MIG1), not a guessed timestamp.
- **ORCH-4.** The settings value limit follows the PRD: 4 KiB (4096 bytes) in the service with its error, and a CHECK of 8192 octets in the database as a backstop.
- **ORCH-5.** The bot is not built (PRD §8.2). Its harness requires H applied and the newest applied version not older than H, which I satisfies.
- **ORCH-6.** Lanes: service MIG1 → MIG2 → MIG3 → S1…S8; web S1… on mocks once the service plan was approved (contracts r2 final apart from §12); live checks on the preview. Merge order: migrations, service, web. No workspace-root, compose or `.env.example` edits; `documents/` is never edited.
- **ORCH-7.** Models were chosen per step by workload (opus/high for the heavier service and web steps, sonnet for the rest). Execution mode was dependency-gated lanes, sequential bundles, no smelts.
- **ORCH-12 (code review r1 SF1; the owner may overrule).** A partly selected publisher (a hand-edited URL, or a stored list that predates a newly registered code) is widened to all of that publisher's current codes once `GET /sources` answers. The chip then reads pressed honestly. The alternative was `aria-pressed="mixed"` with a new style.

### Plan resolutions worth knowing (each recorded, none chosen silently)

**Service (R1–R21).**
- **R4.** `tier=` or `source=` with an empty value is the **empty set**: no row matches, and the export is header only. An absent parameter means all.
- **R5.** A `since` read returns the `limit` oldest rows after `since`, extended to every row sharing the last `created_at` (a document's signals commit together), newest first, with `next_cursor` null. A capped reveal repeats `since` from the newest instant held, so no row is skipped.
- **R6.** Orderings: `bots` by `ts` then `decision_id`; `siblings` by `display_symbol` then `instrument_id`; `GET /sources` by tier (filing, wire, exchange, media, account) then code.
- **R7/R8.** The recommendation's unit value is `px:last` × the estimate's USD/THB rate (USD-quoted spot) × the contract multiplier (futures). `px:last` counts only when valid v1, not stale, and at most 120 s old. The result is `null` for neutral signals, zero floored quantities, a missing rate or venue rule, inactive instruments, or a user without a manual bot. The detail never creates a bot or an account.
- **R11.** A non-null `followed_recommendation` requires exactly one signal id. **R12:** the signal check runs right after the instrument checks and before lot/tick, hours, side and money, inside `check()`, so placement and estimate refuse identically and before any write.
- **R13 (security default).** CSV formula guard: a `headline`, `publisher`, `canonical_url` or `bots` cell starting with `=`, `+`, `-`, `@`, TAB, CR (and LF, added in review-fix r1) gets a leading `'`. **R14:** `canonical_url` is passed only as an absolute `http`/`https` URL, else `null` or empty.
- **R15.** Pattern hand-over is at most once per publish. A frame published inside one reconcile may be missed but is never duplicated, except across two flag flips within one hand-over (a follow-up).
- **R16.** Deliberate test revisions: `TestRouter_ForcedChangeGatesNewRoutes` 35 → 43; `TestRouter_NoDecisionMutation` now allows exactly `PUT /me/settings/:key`; the closed-labels metrics test; the `SetDesired` fakes; `TestCodes_Contract`; the `TestReady_*` messages.
- **R19 (ORCH-8).** `hidden_by_threshold` is the envelope's last key and always present: an integer on paged reads, `null` on `since` reads, computed in one statement over the whole day.

**Web (SP-W-1…24).**
- **SP-W-3.** The shell now reads `GET /signals/badge` on every screen, so `failClosedApi` answers that route with `QUIET_BADGE` (`unseen: 0`) in every mocked spec.
- **SP-W-5.** Seen-through writes live in `SignalsBadgeService` (provided by `Shell`, which outlives the page).
- **SP-W-7.** Only non-default parameters are written to the URL. Every list, export and `since` request still sends `min_impact`, because the service's default (0.00) is not the screen's (0.30).
- **SP-W-8.** One source chip per `publisher`; the label is the registry text, so it reads "Stock Exchange of Thailand" where the mockup said "SET". Disabled sources stay toggleable, with the title "Not reading yet".
- **SP-W-11.** *Buy/Sell with recommendation* is an `a.btn.primary` with `routerLink`, because it navigates.
- **SP-W-13/14.** `.bot-detail .more-row` becomes the shared `.more-row`. The moved detail rules become selector lists for `tr.check-detail` and `tr.signal-detail`.
- **SP-W-15.** `signals-live.spec.ts` is mocked and not gated, unlike `market-watch-live` and `bots-live`.
- **SP-W-16/17.** `SignalMessage` gains `tier`, `source_code` and `impact`, read leniently so Market watch's count is unchanged. The first `subscribed` **or** `signals_subscribed` counts as a connection's acknowledgement.
- **SP-W-22.** With an empty URL the store reads `GET /me/settings` first, applies the stored filters, writes them into the URL, and then reads the list.
- **SP-W-23.** Bots words beyond the PRD's three verbs: "proposed" and "protected". A null `qty` drops the quantity.
- **Revision r3.** `feat-screen-placeholder/screen-placeholder.spec.ts` was added to S8's scope. It expected `/signals` to be the placeholder; this was a planning gap, not a product decision.

## Database

Migration I lives in tidewatch-migrations as `migrations/20261011182817_user_settings.sql` and runs in goose's default transaction after H (`20261011020408`). Its version is the new `RequiredSchemaVersion` (`internal/platform/postgres/schema.go`). A database migrated only through H answers `/ready` 503 (`required version 20261011182817 not applied`). The anchored lookup is `ls migrations | grep -E '^[0-9]{14}_user_settings[.]sql$' | cut -c1-14`. The SQL is PRD §5.1 byte for byte:

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

- **No other object.** No trigger, function, view or seed, and no change to an earlier table. Constraint names are PostgreSQL's defaults: `user_settings_pkey`, `user_settings_user_id_fkey`, `user_settings_key_check`, `user_settings_value_check`. `CREATE INDEX` on the append-only `decisions` is DDL, which its triggers do not intercept.
- **Semantics.** One row per (user, key). Only two keys are accepted by the service (`signals.filters`, `signals.seen_through`; see API). The service caps a value at 4096 bytes; the 8192-octet CHECK is a backstop (ORCH-4). The GIN index serves the Bots column's citing-decision lookups. The list and export use `&&`, the summary `@>`; GIN `array_ops` serves both.
- **Down** drops only preferences and the index; no decision data is touched. It is destructive for per-user settings, owner-only and local-only.
- **Harness** (`scripts/check-disposable-db.sh`):
  - I joins `expected_migrations`, and `required_migration=user_settings`.
  - `relations_user_settings` prints `user_settings|r`; the index is asserted by name, definition and access method `gin` in `assert_user_settings` (R2).
  - Six probes are refused, each in a rolled-back transaction: an upper-case key, a 65-character key, a key with five segments, a value over 8192 octets, an unknown user, and a duplicate (user, key).
  - Four controls are accepted:
    - a `signals.filters` row with `updated_at` defaulted;
    - a `signals.seen_through` row;
    - `ON DELETE CASCADE` removing a deleted user's rows;
    - an `EXPLAIN` of `signal_ids @> ARRAY[...]` under `enable_seqscan = off` that names the index.
  - E's exact `decisions` index list leaves out `decisions_signal_ids_gin_idx` by name, and only while I is applied (MI5).
  - The make down/up window and the down-to round trips run `absent_user_settings`.
  - Result: **1,436 PASS / 0 FAIL** (orchestrator re-run; the engineer's run gave 1,434).
- **Writers.**
  - `user_settings`: only the service's `SettingsRepo`. `PutLaterAt` keeps the later `seen_through` instant in one `INSERT … ON CONFLICT` statement and answers the stored row; `updated_at` moves only when the value changes.
  - The four decision signal columns: only the order path, in the decision's own transaction.

## API

### Service routes (tidewatch-service)

All eight routes mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`. They parse queries with `parseQuery` (unknown, repeated or bad → `400 invalid_request {field, reason}`) and return snake_case JSON with decimals as strings and instants as RFC 3339 UTC. `/signals/summary`, `/badge` and `/export.csv` are static segments registered beside `/signals/:signal_id` and win over it. `TestRouter_ForcedChangeGatesNewRoutes` now counts 43 gated routes (40 production + 3 test probes). Signals and sources are global; citing decisions, the acted-on count, the recommendation and settings are scoped to the session user. No route takes a user id.

| Method and path | Request | 2xx response | Errors |
|---|---|---|---|
| `GET /signals` | `day` (YYYY-MM-DD Bangkok; default the Bangkok day of `generated_at`), `asset` (`us`\|`th`\|`crypto`\|`gold`; absent = every class, fx included), `tier`, `source` (comma lists; empty value = empty set), `min_impact` (`^[01]\.[0-9]{2}$`, ≤ 1.00, default `0.00`), `limit` 1–200 (50), `cursor`, `since` (not with `cursor`) | `{generated_at, day, items: SignalRow[], next_cursor, hidden_by_threshold}` | 400 (incl. `{field: cursor, reason: invalid}` for a cursor from another query) |
| `GET /signals/{signal_id}` | none | `SignalDetail` | 404 `not_found` (not a UUID or not a signal) |
| `GET /signals/summary` | `day` | `{generated_at, day, today, acted_on_by_bots, contradicted_by_price}` | 400 |
| `GET /signals/badge` | none | `{generated_at, unseen, min_impact, seen_through}` | 400 (any parameter) |
| `GET /signals/export.csv` | as the list without `limit`, `cursor`, `since` | `text/csv; charset=utf-8`, attachment | 400 as the JSON envelope, before any CSV byte |
| `GET /sources` | none | `{items: [{source_code, publisher, kind, tier, enabled}]}` | 400 (any parameter) |
| `GET /me/settings` | none | `{settings: {<key>: <value>}}`, stored keys only | — |
| `PUT /me/settings/{key}` | body exactly `{value}`; CSRF header `X-Tidewatch-Request: 1` and app `Origin` | `{key, value, updated_at}` | 400 `invalid_request` (`details.field` `key` or `value`; `unknown_field` never names the key); 403 `csrf_rejected` |
| `POST /orders`, `POST /orders/estimate` | `decision_ctx` may cite one signal (below) | unchanged | new 422 `signal_not_applicable` |

**Bangkok day.** A fixed UTC+07:00 zone: day D covers `[D−1 17:00Z, D 17:00Z)`.

**Cursor (S3).** It is opaque and checksummed over version, kind, day, asset, both sets (sorted, with presence bytes) and threshold, with length prefixes. Decoding is strict base64url and strict JSON with a constant-time compare. It is bound to the query, not to the page size (`TestSignalsCursor_BoundToQuery`). Keyset order is `(created_at DESC, signal_id DESC)`.

**`hidden_by_threshold` (ORCH-8).** On every paged read: the number of the response day's signals matching `asset`, `tier` and `source` with `impact < min_impact`. It is `0` when `min_impact` is `0.00` or a set is empty, the same value on every page of one query, and `null` on a `since` read. The key is always present.

**`SignalRow`.**

```
{ signal_id, created_at, document_id, source_code, publisher, tier, headline, published_at, body_status,
  instrument: {instrument_id, display_symbol, asset_class, venue_id},
  siblings: [{instrument_id, display_symbol, direction, p}],
  event_type, severity, direction, p, p_up, p_down, p_neutral, applies_p, horizon, novelty, mention,
  conviction, impact,
  bots: [{decision_id, bot_id, bot_name, actor: "bot"|"user", action, qty | null, ts, followed_recommendation | null}] }
```

- **Decimal scales.** Probabilities have 3 dp (`"0.780"`), `severity` 2, `conviction` and `impact` 4.
- **`siblings`** are the other signals of the same document, ignoring filters.
- **`bots`** are decisions with `signal_ids` overlapping the id, on bots the session user owns (D1).
- **Closed vocabularies** for `tier`, `direction`, `horizon`, `novelty`, `mention`, `event_type`, `asset_class`, `body_status`, `kind`, `actor`, `action`, `role`, `cdc_zone` and the context timeframe are listed in contracts §1. The web's strict parsers refuse unknown values.

**`SignalDetail`** is `SignalRow` plus:
- `canonical_url` (http/https only, else `null`; R14).
- `triage` `{is_material, event_type_probs (pass-through jsonb), model_id, prompt_version} | null`.
- `extraction` `{key_facts[], rationale, role, why, prompt_version, model_id} | null`: the latest extraction whose `model_id` equals the signal's `extraction_model_id`; `role` and `why` come from `document_instruments`.
- `structured` (the source's `config.structured`, true for Binance TH listings).
- `model` `{triage_model_id, extraction_model_id, scoring_model_id, prompt_version, scoring_version, constants: {novelty_w, mention_w, credibility}}`, from `scoring_versions.constants` and the current `sources.credibility`.
- `context` `{timeframe, cdc_zone, zone_since, zone_age, close_at_signal, latest_price, latest_price_at, price_since_pct, atr14, contradicted}` (each nullable):
  - `timeframe` is the strip timeframe, `1h` (or `1d` for a daily base).
  - The zone run looks back over at most 48 strip rows at or before `created_at`.
  - `close_at_signal` is the latest strip close within the 7 days before `created_at`.
  - `atr14` comes from the latest `1d` row within the 30 days before `created_at`.
  - `latest_price` is a usable `px:last`, else the latest strip close.
  - `price_since_pct` has 4 dp, half away from zero.
  - `contradicted` is null when any input is missing.
  - Since review-fix r1 the detail reads `px:last` **once** and passes the value to the recommender, so context and recommendation share one instant (`TestService_Detail_OnePxLastRead`).
- `recommendation` `{side, qty_suggested, rule: "equity_pct_10", equity_pct: "0.10", equity, price, priced_at} | null`, where `qty_suggested = floor_to_lot(0.10 × equity_thb ÷ unit_value_thb)`. The recommendation is read-only and answers `null`, never an error, when it cannot be sized.

**Summary (PD7, §4.4).** One SQL statement with lateral joins, ignoring filters.
- `acted_on_by_bots` counts distinct signals cited by a decision with `actor = 'bot'` on the user's bots; a user-actor citing decision never counts.
- `contradicted_by_price` counts signals with direction up or down, `p ≥ 0.600`, a daily ATR, and `latest_close − close_at_signal` against the call by more than that ATR. The latest stored close stands in for the current price (S7); missing rows count as not contradicted.

**Badge (S8).**
- `unseen` counts signals with `created_at > seen_through`, `impact ≥ min_impact` and `created_at ≥ generated_at − 7 days`, capped at 999.
- Defaults when no setting is stored: `min_impact` `"0.30"`, `seen_through` the start of the current Bangkok day.
- A stored value that does not read back as its key's shape counts as not stored.

**Settings keys (S9; checked in order: key, missing, 4096 bytes, shape).**

| Key | Value |
|---|---|
| `signals.filters` | exactly `{asset: "all"\|"us"\|"th"\|"crypto"\|"gold", tiers: [distinct tiers], sources: [distinct codes that exist in sources now, ≤ 64], min_impact: "0.00".."1.00"}`. A `min_impact` above 1.00 is `invalid` here but `out_of_range` in a query. |
| `signals.seen_through` | exactly `{at: RFC 3339 instant ending in Z}`, not more than 60 s past the service clock (`out_of_range`). **Never moves backwards:** the stored value is the later instant, and a stale write answers the newer stored value. |

Settings writes are not audited and never logged with their value.

**Export (PD9).**
- Headers: `Content-Disposition: attachment; filename="signals-<day>.csv"`, `Cache-Control: no-store`.
- Body: UTF-8 BOM, RFC 4180 quoting, CRLF, at most 10,000 rows in list order. Every row is read before the first byte is written, so a refusal is still the JSON envelope.
- Header row, exactly: `signal_id,created_at_utc,created_at_bangkok,day,source_code,publisher,tier,event_type,headline,document_id,canonical_url,instrument_id,display_symbol,asset_class,direction,p,p_up,p_down,p_neutral,applies_p,horizon,novelty,mention,severity,conviction,impact,bots`.
- `bots` reads like "You bought 16.2 (followed); Slack Water bought 16.2".
- It is a read-only top-level GET: the session cookie travels and no CSRF header is needed.

### `/ws`: the all-signals feed (S2)

- **Client messages:** exactly `{"op":"subscribe_signals"}` and `{"op":"unsubscribe_signals"}`. Any other key, an `instruments` key included (even `[]` or `null`), is `{"type":"error","code":"bad_message"}`. **Server acknowledgements:** `{"type":"signals_subscribed"}` and `{"type":"signals_unsubscribed"}`, both idempotent.
- **The flag.** It is per connection, so a reconnect starts without it. It is membership in `hub.allSignals`, never counts toward the 100 subscriptions or `ws_subscriptions`, and is counted by the new gauge `ws_signal_feeds`. The 10-messages-per-second and 4 KiB limits count these messages. The acknowledgement and the flag change happen in one write-locked section, and forwarding holds the read lock, so no frame precedes `signals_subscribed` or follows `signals_unsubscribed`.
- **Delivery.** A flagged connection receives every C-SIG-1 `signal` frame, bytes unchanged, **once**, even when it also subscribed to that instrument. Eviction on a full queue is still 1013.
- **Redis side.**
  - The hub hands the subscriber `Channels.SetDesired(channels, patterns []string)`: the `px:<id>` channels of subscribed instruments, plus the `sig:<id>` channels only while no connection is flagged, and the pattern `sig:*` while any is.
  - The subscriber applies `PSUBSCRIBE`/`PUNSUBSCRIBE` on its one existing connection (A2 held: go-redis v9.9.0 `PSubscribe`). It adds before it drops (`SUBSCRIBE`, `PSUBSCRIBE`, then `UNSUBSCRIBE`, `PUNSUBSCRIBE`), sends one command each, never sends an argument-less unsubscribe, and re-applies the whole set on a new connection.
  - A pattern message reaches `OnMessage` with its concrete channel and the same header rules.
  - R15 rule: a pattern copy passes only while its pattern is desired; a plain copy only while its channel is desired and no desired pattern matches it.
- **Metrics.** `ws_messages_sent_total{type}` gains `signals_subscribed` and `signals_unsubscribed` (eleven types now). `redis_subscriber_reconcile_failed` now reads `redis: <cmd> N names: ...` and never names a channel. No other limit, close code or frame changed.

### Order path: `decision_ctx` cites a signal (FR-SP-SVC-007, D2, S4, S6)

```json
"decision_ctx": {"signal_ids": ["0199d1a2-7b10-7c3e-9a51-3f0c2e8b4d17"], "followed_recommendation": true}
```

- **Accepted** (`checkDecisionCtx`):
  - absent or `null`;
  - the slice-2 form (`signal_ids` absent or `[]`, the other two absent or null);
  - exactly one hyphenated UUID with `followed_recommendation` `true`, `false`, `null` or absent, and `candidate_id` absent or null.
- **Refused `400 {field: decision_ctx, reason: invalid}`:** `signal_ids` null, not an array, two or more ids, or a non-UUID; a followed flag without exactly one id (R11); a non-null `candidate_id`. Another key is `unknown_field`.
- **`checkSignal`** runs inside `check()` right after the instrument checks (`404 unknown_instrument`, `422 instrument_inactive`, `422 instrument_not_tradable`) and before every other check and any write, for placement and estimate alike:
  - no such signal → `422 signal_not_applicable` with `details {"reason": "unknown"}`;
  - `signals.instrument_id` ≠ the body's instrument → `details {"reason": "instrument_mismatch"}`, message "The signal this order cites names another instrument.";
  - a refusal is counted `orders_placed_total{result="rejected"}` and logged `order_rejected`.
- **Decision row written** in the order's transaction: `signal_ids = ARRAY[signal_id]` (lower-case), `followed_recommendation` as sent, and:
  - `signal_snapshot` = `{signal_id, document_id, source_code, tier, event_type, direction, p, p_up, p_down, p_neutral, impact, severity, horizon, created_at, recommendation}`. The recommendation is derived **at order time** from the same equity, price and rate the order checks used; it is `null` for a neutral signal or when it cannot be sized (for example a stale `px:last`).
  - `model` = `{tier: "system1", model_id: <scoring_model_id>, direction, p, prompt_version, extraction_model_id, rationale}`.
- **Unchanged:** without a cited signal all four columns stay NULL as before; success bodies; an idempotent replay answers the stored order whatever `decision_ctx` says; `POST /decisions/skip`. The estimate never writes.

**New error code.** `signal_not_applicable`, 422, `details.reason` `unknown` | `instrument_mismatch`, no `field`. It is appended last in `AllCodes` and in the README error table, and `TestCodes_Contract` reads that table.

**Configuration and compatibility.**
- **Unchanged:** environment variables, secrets, compose, dependencies (`go.mod`/`go.sum`) and Redis keys. The new Redis operations are `PSUBSCRIBE`/`PUNSUBSCRIBE sig:*` only.
- **Compatibility:**
  - An old web against the new service is unchanged.
  - A new web against an old service shows the Signals error state and a hidden badge (404s). Its pre-fill still fills the ticket, but placement is refused as an invalid `decision_ctx`.
  - The bot is unaffected.

## Components

Angular 22 (signals, `httpResource`, signal forms, no `NgModule`). `DESIGN.md` rules apply: no Material or chart library, no `dark:`, native controls, nothing animates. **No token, colour, type step or icon was added** (`tokens.css`, `theme.css`, `icons.ts` unchanged). The approved mockup's soft-mint `.chip.on` and violet impact fill are not used (PW-3).

**Routes (`pages/workspace/workspace.routes.ts`).**
- `/signals` lazy-loads `Signals` (`app-signals`) in place of the placeholder.
- `chart/:instrument_id` shows the existing Chart placeholder; the parameter is unused until Charting. `/chart` is unchanged.

**`app-signals` (`feat-signals/signals.ts`, `providers: [SignalsService]`).**
- **Header.** `app-page-header` "Signals" with the sub line "{n} today · {n} acted on by bots · {n} contradicted by price".
  - It reads "Loading…" until the summary and the first list load answer; after that the counts stay through later failures (ORCH-17).
  - Right side: *Export* (`a.btn.ghost[download]`) and *Add source* (`.btn`).
- **`.content`, in order:** `app-signals-filters`; one `.section` with `h2` *Today* (`tabindex="-1"`), a `.count` (hidden noun "signals shown") and the `.more` note as a polite region; one polite state region; the scroll region (`role="region"`, focusable, "Signals today, scrollable table") holding `app-signals-table`; *Load more* in `.more-row`.
- **States.**
  - Loading: "Loading signals…" in the dashed `.status-line`.
  - Error: "Signals couldn't load." with *Try again*, which focuses *Today* first.
  - Empty day: "No signals yet today. Signals appear within seconds of a filing, release or exchange notice becoming a scored event."
  - Filter-empty: "No signals match these filters today."
  - *Load more* busy: *Loading…*, `aria-busy`, disabled. Its failure raises the toast "Couldn't load more signals. Try again."
- **Add source** opens an `app-dialog` titled *Add source* with the description "Arrives with user sources.", the body naming the seeded primary sources, and *Done*. Nothing is written.

**`app-signals-filters` (`signals-filters.ts`; inputs `filters`, `chips`, `accountSourceExists`; output `filtersChange`).**
- Three named `role="group"`s of native `button.chip[aria-pressed]`:
  - **Asset class** (single choice): *All assets*, *US stocks*, *Thai stocks*, *Crypto*, *Gold*.
  - **Provenance:** *Filing*, *Wire*, *Exchange*, *Media*, *Account*. *Account* is `disabled` with the title "No account sources yet" while no account source exists.
  - **Source:** one chip per publisher from `GET /sources`; the three EDGAR rows fold into *SEC EDGAR*, and disabled rows carry the title "Not reading yet".
- *Impact ≥* is a `<label class="chip chip-select">` around a native `<select>` with 0.00/0.10/0.30/0.50/0.70 (default 0.30).
- The row wraps; its `.sep` separators hide at ≤ 600.

**URL and settings precedence (FR-SP-WEB-002, SP-W-7/22).**
- The URL is the source of truth: `asset`, `tier`, `source`, `min_impact`, written with `replaceUrl` and `queryParamsHandling: "merge"`. Only non-default values are written.
- An emptied group is written as an empty value (`tier=`); for an empty set the list is not requested and the filter-empty state shows at once.
- Malformed values fall back to that parameter's default. Unknown source codes are dropped once `/sources` answers, and a partial publisher is widened (ORCH-12).
- An empty URL takes the stored `signals.filters` after `GET /me/settings`; a URL with any of the four wins.
- `PUT /me/settings/signals.filters` is debounced 500 ms, sent one at a time, flushed at once on destroy, and silent on failure.

**`app-signals-table` (`signals-table.ts`; inputs `rows`, `openIds`, `details`, `generatedAt`; outputs `toggleDetail`, `retry`).** `table.tide.signals` with a hidden caption, eight columns, a minimum width of 860px, and quiet non-interactive rows (MW-10, MW-23).

| Column | Cell |
|---|---|
| When | `HH:mm` Bangkok in `<time datetime>` with the full instant as `title` |
| Trust | five 5×10px bars, `TIER_BARS[tier]` filled, `aria-hidden`; tier word in `.second`; hidden "{Tier}, trust {n} of 5" |
| What happened | `.headline`, wrapping (min 260px, 220px at ≤ 1250), linked to the row's own detail anchor |
| Instrument | `a.chip` to `/chart/{instrument_id}` ("Open {symbol} on the chart"); `.second` "also {symbol} {glyph} {p}" per sibling (max 3, then "+n"), clipped in 130px |
| Direction | `.dir` in `.change-up/down/flat`: ▲/▼/◆ (`aria-hidden`, hidden word) and `p` with 3 dp (`p_neutral` for neutral) |
| Impact | 96px `.bar` (64px at ≤ 1250), `.hi` fill at ≥ 0.70, `aria-hidden`; number with 4 dp |
| Bots | `.faint` "No bot acted", or up to 3 lines "{You \| bot name} {bought \| sold \| skipped \| proposed \| protected} {qty}" over "followed · HH:mm" or "HH:mm"; lines wrap (ORCH-16) |
| Details | `button.text-btn` *Details* / *Hide*, `aria-expanded`, `aria-controls="signal-detail-{id}"` |

**Expanded row (`signal-detail.ts`, `app-signal-detail`; input `entry`, output `retry`).**
- Opening inserts `tr.signal-detail#signal-detail-{id}` with one `colspan="8"` cell. Its `.detail-wrap` is a polite region, inserted empty and filled one task later.
- The wrap is `position: sticky` with a steady inset (`left: 17px`, 10px at ≤ 600; ORCH-18) and `max-width: calc(100cqw − 34px)` (`− 20px` at ≤ 600). The signals section's `.table-scroll` is an inline-size container for this section only, so the three columns stay inside the visible region while the row's cells scroll.
- The detail is read once per id, and collapsing and reopening reads nothing. "Loading this signal…" shows while it loads. "This signal couldn't load." comes with *Try again*, which focuses that row's *Hide* first. Several rows may be open.
- **Extracted.**
  - *Event*: "{event words} · severity {s} / 5".
  - *Novelty*: "First for {symbol} · …" or "Repeat within 5 days".
  - *Publisher*: "{publisher} · HH:mm:ss · {full text | feed text | headline only}".
  - *Instrument*: "Named in the document · {role}" or "Implied by the model · {role}".
  - Key facts and the rationale.
- **Model view.**
  - *Direction*: "▲ Up 0.780" over the full distribution.
  - *Applies*, and *Horizon* ("Intraday · 2 h half-life" / "Days · 24 h" / "Weeks · 120 h").
  - *Decision tier*: "System 1 · {scoring_model_id}".
  - *Extraction*: "{model} · {prompt_version}".
  - *Impact*: "{conviction} conviction × {severity/5} severity × {novelty_w} novelty × {freshness} freshness × {credibility} credibility × {mention_w} mention = {impact}". Freshness is computed by `freshnessAtCreation` (ORCH-13; `HALF_LIFE_HOURS` intraday 2, days 24, weeks 120).
  - A structured source reads "Structured source · no model".
- **Context at the time.**
  - *CDC zone*: `app-zone-label` with "· {timeframe} · since … · {n} bars", or "No zone yet".
  - *Price at signal* over "latest {price}".
  - *Price since*: a signed percent in its tone, over "Within 1 ATR ({atr})", "More than 1 ATR ({atr}) against the call" or "No daily ATR for this instrument".
  - *Elliott* and *Regime*: "Arrives with Charting".
- **Actions.**
  - up: `a.btn.primary` *Buy with recommendation*; down: *Sell with recommendation*. Each links to `/trade?instrument=&side=&qty=&signal=` and has the hint "{qty} {symbol} · sized at 10% of equity, like Slack Water".
  - neutral: "No directional call, so no trade is suggested."
  - no recommendation: "No price to size from right now." and no primary button.
  - *Open chart* (`.btn`) and *Source document* (`.btn.ghost`, `target="_blank" rel="noopener noreferrer"`).

**`SignalsService` (`feat-signals/data/signals.service.ts`, component-provided; SE-5).**
- **Reads.** The first page, the summary and the sources are `httpResource`s; *Load more*, *Show*, a detail and the settings are imperative. Leaving the screen releases the feed, timers and reads.
- **Reload rules.** The summary reloads every 60 s and after a reveal. The list reloads only on *Try again*, a filter change, a reveal, a reconnect and a terminal close. A failed background reload keeps the rows (MW-20).
- **Continued reads.** Every *Load more* and *Show* carries the loaded `day` (contracts r2). *Load more* and *Show* answers are dropped when the list changed meanwhile.
- **Live count (SP-W-18, S10).** A `signal` frame counts as new when:
  - its `created_at` is on the loaded Bangkok day (from `generated_at`, never the browser clock);
  - its tier and source are pressed;
  - its impact is at or above the threshold;
  - its id is neither listed nor counted (at most 500 ids, cleared on each successful list load).

  Asset class is not applied.
- **The note.**
  - With rows waiting: "{n} new signals" (singular "1 new signal") with a `.text-btn` *Show*.
  - Otherwise: "Newest first · Asia/Bangkok", plus "· {n} more under Impact ≥ {t}" when `hidden_by_threshold` > 0.
  - Nothing is inserted and nothing scrolls; the table is not a live region.
- ***Show*** reads `since` = the newest listed `created_at` with `limit=200`, prepends the rows, clears the count, focuses *Today*, advances seen-through and reloads the summary. A capped answer leaves the remainder counted.
- **Seen-through** advances to the newest listed `created_at` after the first successful list load and after *Show*, never after *Load more* (SP-W-20).
- **Export link (SP-W-21)** = `apiBaseUrl` + `/signals/export.csv?` + the URL filters + the loaded `day`.

**Data layer (`pages/workspace/data/`).**
- `signals.model.ts` has strict parsers that refuse unknown vocabulary values; since fix-r1, decimals must be strings.
- `signals-api.service.ts` (`SignalsApi`) owns the eight routes and the export URL.
- `market-stream.model.ts` / `market-stream.service.ts`:
  - `MarketStream.acquireSignals()` is reference-counted like instrument interest.
  - Each new connection sends `subscribe_signals` first, then the instrument diff, within the 10-frames-per-second budget. A feed-only connection opens and recovers like any other.
  - `parseStreamFrame` reads the two acknowledgements.
  - `SignalMessage` gains lenient `tier`, `source_code` and `impact`; Market watch's count is unchanged.

**Rail badge (`shell/data/signals-badge.service.ts`, `SignalsBadgeService` provided by `Shell`; `rail.ts`, `shell.ts`, `shell.css`).**
- **Reads.** `GET /signals/badge` on shell load, on every `NavigationEnd` and every 5 minutes. While `/signals` is active the read is skipped and the count shows 0. An older answer never overwrites a newer one, and a failed read keeps the last count.
- **Seen-through writes.** `advanceSeenThrough(at)` writes `PUT /me/settings/signals.seen_through` only for a later instant, then re-reads the badge when not on `/signals`.
- **`.nav-count`** shows "99+" above 99 and is `aria-hidden`; the link's name becomes "Signals, {n} unseen". It is hidden at ≤ 1080 (icon rail) and in the ≤ 600 strip, where the name still carries the number. It is the one rail badge 03 §10 allows; `DESIGN.md`'s "no rail badges" was updated.

**Trade pre-fill and signal context (`feat-trade/`).**
- **Reading the query.** `util/signal-prefill.ts` parses `/trade?instrument=&side=&qty=&signal=` once, after the first successful `/trade` load. The query is removed with `replaceUrl` whenever any of the four keys was present.
- **A valid pre-fill:**
  - needs a tradable instrument, `buy`/`sell`, a decimal within `qty_decimals`, and a UUID;
  - sets instrument, side, quantity (exact BigInt floor to lot and decimals; a zero result is ignored) and order type Market (ORCH-15);
  - shows the hint "Sized at 10% of equity, like Slack Water · from a signal" under *Quantity*;
  - keeps `signalContext = {signal_id, side, qty_suggested, rule: "equity_pct_10"}` in `TradeService`.
- **Unwatched instrument (ORCH-14).** A well-formed query for an instrument that is not on the watchlist leaves only `untradableSignal` for the ticket's polite hint. Choosing an instrument dismisses it (an engineer's call in fix-r3 that the owner may overrule).
- **Context lifecycle.** The context is dropped on another instrument and after a definite answer, kept on a 5xx or network failure (ORCH-10), and the side flip sets `followed_recommendation` (ORCH-11). The attempt fingerprint includes the signal id and followed flag, so a changed body never reuses a `client_order_id`.
- **Request and copy.** `PlaceOrderRequest` (`trade.model.ts`) gains an optional `decision_ctx`; the estimate never carries it. `refusal-message.ts` adds "This signal no longer applies to the chosen instrument." for `signal_not_applicable`.
- **Layout (ORCH-18).** *Quantity* spans the row (`col-span-2`) when *Limit price* is hidden, for market and manual-fill orders.
- **Unchanged:** the decision record already reads "1 signal" and the followed flag.

**Styles.**
- New `src/styles/components/signals.css`, imported after `bots.css` and before `zone.css`. It holds:
  - the filter pieces: `.signal-filters`, `.chip` (pill, 10px/500, `--line-2` border; pressed: `--brand` border, `--surface-2`, `--text`; a 0.18 s border/background transition), `.chip-select`;
  - the row pieces: `.trust`, `.bar`, `.dir`, the `table.tide.signals` column rules (≤ 1250: 12px cells, 64px bar, 220px headline; Bots column 126px above 1250, wrapping);
  - the detail pieces: `.signal-detail`, `.detail-wrap`, `.detail-note` and `.hint`, with light-theme lifts to `--text-2`.
- `.nav-count` is in `shell.css`.
- **Expandable-row rules moved** from `bots.css` to `table.css`, unscoped, as the second consumer. That is 11 rules: `.tide .details`, `tr[data-expanded="true"] td`, the detail cell and status-line rules as selector lists for `tr.check-detail` and `tr.signal-detail`, `.check-note`, `.tide.nested`, and `.bot-detail .more-row` renamed `.more-row`. Bots captures stayed 0-pixel identical (P2).

**`DESIGN.md` (FR-SP-WEB-011; S12 plus P6 `0ebc5cc`).**
- **Documents** the chip, the moved expandable row, `.nav-count`, trust and impact bars, direction tones, the Signals states and placement, and the measured fit:
  - 862/862 at 1100 (columns `[56,69,228,130,69,135,116,59]`);
  - 958/958 at 1080 and 1152/1152 at 1440;
  - 860 over 568 / 358 at 600 / 390.
- **Records:** a "Reconciliation with 03" row (left-aligned Direction/Impact; 5×10 trust bars), the contrast-opacity note (disabled and busy text exempt), and a Verification evidence entry.
- **P6 check:** 13 stale "pending" statements corrected. `forge-setup-impeccable --check` reports no drift (103 sources unchanged).
- **Web `CLAUDE.md`** gained the Signals conventions: structure, `SignalsApi`/`SignalsService`/badge, URL truth, counting, the Trade context, quiet badge in specs, and follow-ups.

## Files touched

The lists come from each approved plan's Files lists, cross-checked against the reviewed diff counts and the final scope check. No `git diff` was run for this document.

| Repo | Range (base..PR head) | Merge | Files |
|---|---|---|---|
| tidewatch-migrations | `4d05646..090e809` | `52deb26` | 4 |
| tidewatch-service | `c570c99..539a07e` | `8b18486` | 73 at `b4ad4d1` (code reviewer's count: 70 planned plus 3 extras); review-fix r1 stayed inside that set |
| tidewatch-web | `63c7f29..0ebc5cc` | `da6f4cb` | 68 (angular reviewer at `f76104f`: +17,916/−353). Final `scope S12` check at `0ebc5cc`: 69 changed paths including `.plans/signals-page.md`, all planned. |
| tidewatch-bot | unchanged by code | https://github.com/tidewatch-labs/tidewatch-bot/pull/9 (docs only, ORCH-5a) | merged `ece175a` |

### tidewatch-migrations (PR #9, https://github.com/tidewatch-labs/tidewatch-migrations/pull/9)
- `migrations/20261011182817_user_settings.sql` (created)
- `scripts/check-disposable-db.sh` (modified)
- `README.md`, `CLAUDE.md` (modified: the pin moves to I, H is listed as "the pin until I", the destructive down past I is noted)

### tidewatch-service (PR #10, https://github.com/tidewatch-labs/tidewatch-service/pull/10)
- **Schema pin (S1):** `internal/platform/postgres/schema.go`, `internal/pgtest/migrate.go`, `scripts/integration-test.sh`, `test/integration/main_test.go`, `test/integration/ready_test.go` (modified).
- **Repository:** `internal/repository/postgres/signal.go`, `signal_test.go`, `source.go`, `settings.go`, `settings_test.go` (created); `decision.go`, `trading_test.go` (modified).
- **Signals service (new package `internal/services/signals/`):** `service.go`, `list.go`, `list_test.go`, `cursor.go`, `cursor_test.go`, `sources.go`, `detail.go`, `detail_test.go`, `summary.go`, `badge.go`, `badge_test.go`, `export.go`, `export_test.go` (created).
- **Settings service (new package `internal/services/settings/`):** `service.go`, `keys.go`, `keys_test.go`, `service_test.go` (created; `service_test.go` is an extra).
- **Trading:** `internal/services/trading/recommend.go`, `recommend_test.go` (created); `place.go`, `place_test.go`, `store.go`, `trade.go` (modified; `trade.go` only to share the equity valuation via `nowMarks`); `internal/trading/rules.go`, `rules_test.go` (modified: `FloorQty`).
- **Handlers:** `internal/handlers/signals.go`, `signals_test.go`, `settings.go`, `settings_test.go` (created); `orders.go`, `orders_test.go`, `realtime_test.go` (modified).
- **Realtime and Redis (S6):** `internal/services/realtime/{ports,hub,hub_test,protocol,protocol_test,conn,conn_test}.go`, `internal/platform/redis/{subscriber,subscriber_test,redis_test}.go`, `internal/httpx/wsconn/peer_test.go` (modified).
- **Metrics:** `internal/observability/metrics/realtime.go`, `metrics_test.go`, `metrics.go` (modified; `metrics.go` is an extra, +3 lines registering `ws_signal_feeds`).
- **Errors:** `pkg/apperror/codes.go`, `apperror.go`, `apperror_test.go`, `codes_test.go` (modified; `codes_test.go` is an extra, the `TestCodes_Contract` row).
- **Wiring:** `internal/app/app.go`, `router.go`, `router_test.go` (modified).
- **Integration:** `test/integration/signals_test.go`, `signals_fixtures_test.go`, `settings_test.go` (created); `orders_test.go`, `realtime_test.go`, `redis_test.go` (modified).
- **Docs:** `README.md` (routes, error table, `/ws` operations, Redis table, observability), `CLAUDE.md` (Signals and settings invariants, Redis rules, required schema version I, named tests) (modified).

### tidewatch-web (PR #12, https://github.com/tidewatch-labs/tidewatch-web/pull/12)
- **Data:** `src/app/pages/workspace/data/signals.model.ts`, `signals.model.spec.ts`, `signals-api.service.ts`, `signals-api.service.spec.ts` (created); `market-stream.model.ts`, `market-stream.model.spec.ts`, `market-stream.service.ts`, `market-stream.service.spec.ts`, `trade.model.ts`, `trade-api.service.spec.ts` (modified).
- **Shell:** `src/app/shell/data/signals-badge.service.ts`, `signals-badge.service.spec.ts` (created); `rail.ts`, `rail.spec.ts`, `shell.ts`, `shell.spec.ts` (modified).
- **Signals (`src/app/pages/workspace/feat-signals/`, all created):** `signals.ts`, `signals-filters.ts`, `signals-table.ts`, `signal-detail.ts`, `data/signals.service.ts`, `util/signal-view.ts`, `util/signal-filters.ts`, `util/new-signals.ts`, each with its `.spec.ts`.
- **Trade (`feat-trade/`):** `util/signal-prefill.ts`, `util/signal-prefill.spec.ts` (created); `trade.ts`, `trade.spec.ts`, `order-ticket.ts`, `order-ticket.spec.ts`, `data/trade.service.ts`, `data/trade.service.spec.ts`, `util/refusal-message.ts`, `util/refusal-message.spec.ts`, `util/ticket-copy.ts`, `util/ticket-copy.spec.ts` (modified).
- **Routes:** `src/app/pages/workspace/workspace.routes.ts`, `src/app/app.routes.spec.ts`, `src/app/pages/workspace/feat-screen-placeholder/screen-placeholder.spec.ts` (modified).
- **Styles:** `src/styles/components/signals.css` (created); `table.css`, `bots.css`, `shell.css`, `src/styles.css` (modified).
- **End-to-end:** `e2e/src/signals.spec.ts`, `e2e/src/signals-live.spec.ts`, `e2e/src/support/signals.ts` (created); `e2e/playwright.config.mts`, `e2e/src/support/{screens,market-watch,trade}.ts`, `e2e/src/{shell,theme,journey,viewport,a11y,bots}.spec.ts` (modified).
- **Docs:** `DESIGN.md`, `README.md`, `CLAUDE.md` (modified).

**Not changed:**
- `tidewatch-bot` code, harness and image;
- `documents/` and `tidewatch-specs` (inputs only);
- `tidewatch-apis` (not a git repo; collection regeneration skipped);
- compose, workspace-root files and `.env.example`;
- tokens, theme and icons.

## Test plan

### Commands (all local; there is no CI)

- **Migrations:** `make migrate-validate`; `make check-disposable-db` (1,436 PASS / 0 FAIL).
- **Service:** `make ci` (vet, test-race, build; Docker-free); `make test-integration TIDEWATCH_MIGRATIONS_DIR=<migrations checkout>` (about 285 s). Verification greps `--- PASS: <Name> (`, and no `--- SKIP` is allowed. If the only integration failure is "address already in use" on a metrics port, re-run: this is the pre-existing `freePort` race.
- **Web:** `pnpm nx run-many -t lint test build` (3,001 tests at `8dffcfb`, also run with `TZ=America/New_York`); e2e lint and `tsc`.
- **Web against a preview:** the full Playwright suite (`authed-setup`, then `public` + `authed` with `--no-deps`, then `sign-out`; the first-sign-in journey excluded on a kept database). Credentials are read from the owner's file and never printed.
- **No headless run in the worktree.** The mocked specs need a real sign-in for `authed`, so in the worktree they are only listed, linted and type-checked.

### Named acceptance tests (do not rename)

- **Service integration:** `TestSignals_List_FiltersAndPaging`, `TestSignals_List_SinceAndCitingDecisions`, `TestSignals_List_HiddenByThreshold` (including an exact-threshold row at 0.3000 that is listed but not counted, mutation-checked), `TestSources_List_NoURLOrConfig`, `TestSignals_Detail_ContextAndRecommendation`, `TestSignals_Summary_Counts`, `TestSignals_Badge`, `TestSignals_Export`, `TestSettings_RoundTripAndValidation`, `TestSettings_SeenThroughNeverBackwards` (20 concurrent writers), `TestRealtime_SignalsFeed`, `TestRealtime_SignalsFeed_ResumesAfterOutage`, `TestOrders_SignalDecisionCtx_WritesSnapshot` (exact JSON against hand-computed figures), `TestOrders_SignalNotApplicable_NothingWritten`, `TestReady_SignalsIngestSchema_NotReady` (a database migrated only to H gives 503).
- **Service unit:** `TestSettingsKeys_Validate`, `TestSettingsHandler_Put_StrictBody`, `TestService_Badge_Defaults`, `TestSignalsCursor_BoundToQuery`, `TestExport_CSV_Format`, `TestExport_CSV_GuardCells`, `TestSettingsRepo_SeenThroughMax`, `TestService_Detail_OnePxLastRead`.
- **Service, existing tests revised on purpose:** `TestContract_RequiredSchemaVersion`, `TestRouter_ForcedChangeGatesNewRoutes` (43), `TestRouter_NoDecisionMutation`, `TestRouter_MarketMutations_CSRF`, `TestCodes_Contract`, `TestMetrics_RealtimeSeries_ClosedLabels`.
- **Web e2e (mocked, fail-closed):**
  - `e2e/src/signals.spec.ts` (47 tests): states, filters and URL/settings precedence, the expanded row and its single read, the trade hand-off, export `href`, *Add source*, `/chart/{id}`, the 1100 fit with a bot named in the Bots cell, and keyboard.
  - `e2e/src/signals-live.spec.ts` (13 tests): socket acknowledgements, counting three frames into the note with `scrollY` unchanged, *Show*, and the badge across navigation and the 5-minute refresh.
  - `e2e/src/support/signals.ts` mocks the eight routes, the two acknowledgements and a C-SIG-1 frame publisher (`frameOf`).

### Acceptance status (PRD §9; passed / failed / unverified stated separately)

| IDs | Status | Evidence / note |
|---|---|---|
| FR-SP-MIG-001 | Passed | Harness 1,436/0; MIG1 SQL equality with §5.1. |
| FR-SP-MIG-002 | Passed | `TestContract_RequiredSchemaVersion`, `TestReady_SignalsIngestSchema_NotReady`; preview `/api/ready` 200 at I. |
| FR-SP-SVC-001…010 | Passed | Named tests above, plus the review-fix r1 re-runs. SVC-008 hit one harness port-collision flake and passed on re-run. SVC-010 doc checks 9/9. |
| FR-SP-WEB-001…006, 008, 009, 011 | Passed | Unit tests plus P1-final2 (749 passed / 0 failed / 4 skipped on web `8dffcfb`; signals 47/47, signals-live 13/13, trade 97/97, bots 260/260). WEB-005 is mocked only; its live half is E2E-004. |
| FR-SP-WEB-007 | Passed (preview half) | P4: three real downloads, each `signals-2026-10-12.csv`, starting with a BOM and the exact header, row counts equal to the API, the session cookie sent. **Development half unverified** (not run, ORCH-9). |
| FR-SP-WEB-010 | Passed | Design r1 CHANGES REQUESTED, then fix r4, then r2 APPROVED. 232 captures and 226 overflow JSONs with no horizontal page scroll. Every table state measures 862/862 at 1100 in both themes. axe found 0 violations in 48 runs. Minimum computed contrast 4.85 (light `.dir.change-down`). Bots 0-pixel diff 144/144, twice. Motion check (P6, motion on): only the shell's 180 ms screen fade and the chip's 180 ms transition. *Show* and *Load more* motion were not exercised (no data). |
| FR-SP-WEB-012 | Passed on the preview | P1 at `ff3a6c1`: 723 passed, 21 failed, all test defects: 10 a `viewport.spec` *Account* selector colliding with the Provenance chip, 9 an anchored note regex in `signals-live`, 2 `settingsPut` counting the seen-through PUT. These were fixed in fix-r2 and re-run 149/149; then P1-final 745/0 and P1-final2 749/0. **"Locally" half unverified** (not run). |
| FR-SP-E2E-001 | Passed (injected) | A C-SIG-1 copy was published on `sig:AAPL@webull` with the page on `/signals?asset=crypto&min_impact=0.00`. The note changed to "1 new signal Show" **97 ms** after the PUBLISH; `scrollY` stayed 17 → 17; no request, navigation or DOM change outside the note. No real bot publish arrived in 25 minutes of watching `PSUBSCRIBE sig:*`, so only the service → web leg was observed, not bot → Redis. |
| FR-SP-E2E-002 | Passed | Two browser contexts. A changed the filters; one `PUT` answered 200; after a reload the URL and chips were identical. B with an empty URL received the stored filters. The `user_settings` rows were checked by SQL. |
| FR-SP-E2E-003 | **Unverified** | Partial: the two media (Finnhub) rows of the day passed 133/133 checks each (API vs SQL 81, DOM vs PRD words built from SQL 52). No filing, wire or structured-source signal existed: EDGAR returned `nothing_new` on a Sunday night in New York, the wires were not material or named no instrument, Binance TH had `nothing_new`, and `set-notices` was disabled. |
| FR-SP-E2E-004 | **Unverified** | Both of the day's signals (AAPL, NVDA) had a stale `px:last` (US market closed), so `recommendation: null` and no primary button. No order or decision was created. The script `evidence/preview/P3/E2E-004/e2e-004.cjs` (`MODE=place`) is ready to run once a signal with a usable price exists. |
| FR-SP-E2E-005 | Passed | Real data at 1100: page `scrollWidth == innerWidth` at all five widths in both themes; region 862/862; headlines on 2 lines; detail wrap 828px with three columns. After ORCH-16, mocked rows with bot names also measured 862/862. |
| FR-SP-E2E-006 | Passed | Tested with a stored threshold of 0.00, because both real rows sat under 0.30. Overview showed the rail count 2 ("Signals, 2 unseen"); it was hidden on `/signals`. After A's reveal (seen-through 02:26:48.8928Z), B's next navigation answered `unseen 0`. |

**Outcomes (intent O1–O5).** O1 passed. O2 is passed at component level, with E2E-003 unverified. O3 is passed in unit and mocked tests, with E2E-004 unverified. O4 passed, with an injected publish. O5 passed.

**Which revisions the live checks ran on.** P3/P4 ran against web `ff3a6c1` and service `539a07e`. The later web rounds (r3 ORCH-13/14/15, r4 ORCH-16/17/18) were verified by the mocked suite on the preview (P1-final, P1-final2) and the delta design review. P3 was not re-run after them.

### Preview and the database change (shared retained workspace volume)

- **First preview.** `sigp-4081ec46` (compose project `forge-0199b29a-sigp-4081ec46`, `http://127.0.0.1:54375/`) came up at 22:46Z on 2026-10-11: isolated, fresh, migrated to I, 6 containers healthy. The worktree mapping was extended to the bot at base `a6e39e0`. Ingest was live (90 documents in the first minutes), but there were 0 signals.
- **Owner sign-in failed there,** as expected on a fresh database: the admin is bootstrapped from `TIDEWATCH_ADMIN_PASSWORD` with `must_change_password = t`.
- **Move to the shared volume (owner request, 2026-10-12T01:55Z).** The owner asked to use Forge's updated isolated+retain behaviour so builds share one preview database. That behaviour gives new runs a stable workspace volume (`forge-preview-<hash>_tidewatch-pgdata`); existing runs keep their per-run volume.
  - The orchestrator stopped the `sigp` preview. Its per-run volume `forge-0199b29a-sigp-4081ec46_tidewatch-pgdata` was retained, holding only the admin bootstrap.
  - It then created a related owned run **`sigpws-8add0389`** with a copy of the worktree mapping (the same PR branches). Its database mounts the shared **`forge-preview-0199b29a_tidewatch-pgdata`**, which was new and empty at first.
  - The owner signed in and set the password there (`must_change_password = f`). The first signal appeared at 02:26Z.
- **Later previews on the shared volume, one at a time:**
  - refreshes for web `f2e5b01` (`:53989`) and `8dffcfb` (`:65256`);
  - a related run **`sigpbase-653372cf`** with the web image at base `63c7f29` for the P2 Bots baseline (`:60270`), while `sigpws` was stopped.
- **At merge** the active preview was `sigpws-8add0389` at `http://127.0.0.1:65256/`: running, 2 signals, admin signed in.
- **Operational notes.**
  - The acceptance agent's repeated sign-ins hit the login throttle (`429` at 02:56:55Z). There was no lockout and no wrong password.
  - The acceptance agent left the owner's `signals.filters` changed on the shared preview database (Wire and PR Newswire off, Impact ≥ 0.00). The owner has not yet been asked to reset them.

### Assumption outcomes (PRD A1–A6)

- **A1** (the manual bot's `paper_accounts` equity is reachable from the order path): held in planning; the recommendation reuses `GET /trade`'s valuation.
- **A2** (`PSubscribe` on the existing connection): held, as go-redis v9.9.0 supports it; covered by the integration tests including the outage resume.
- **A3** (lateral `indicators` lookups fast by primary key): **no explain-analyse is recorded**; unverified.
- **A4** (the download cookie): held on the preview; the development half is unverified.
- **A5** (most media rows under 0.30): consistent with the preview's two media rows (0.0002 and 0.1568), but the sample is very small.
- **A6** (`container-type` does not disturb scrolling): held; the sticky wrap measured a steady 10px inset at 390 and 600.

### Manual reproduction

1. Apply I, open `/signals` with the bot pipeline running, and expand a row. Compare it with `SELECT … FROM signals JOIN documents …`, the `triage`, `extractions` and `document_instruments` rows, and `indicators` at or before `created_at`. The impact factors should multiply to `signals.impact` within display rounding.
2. With the page open, wait for a real publish or inject one with `PUBLISH sig:<instrument_id> '<C-SIG-1 JSON>'`. Within 2 s the note reads "1 new signal Show" and the page does not scroll. *Show* prepends the row, focuses *Today*, and `user_settings.signals.seen_through` advances.
3. Change chips, reload, and open the same URL-less `/signals` in a second browser: the same filters appear.
4. For a signal whose instrument has a fresh `px:last` and is on the watchlist, use *Buy with recommendation*. On `/trade`, check the instrument, side, quantity, Market and the hint, then place the order. Check `decisions.signal_ids`, `followed_recommendation = true`, and the `signal_snapshot.recommendation.rule = 'equity_pct_10'`. The Signals row should then read "You bought {qty}" over "followed · HH:mm". This is FR-SP-E2E-004, not yet done.
5. Run `curl` with a session cookie against `/signals/export.csv?day=YYYY-MM-DD&min_impact=0.00`: you get an attachment with a BOM, the exact header and CRLF line ends.

## Open questions

**Unverified at merge (the owner knew):**
- FR-SP-E2E-003 for a filing, a wire and a structured-source row.
- FR-SP-E2E-004: the buy flow, the decision row and the "You bought … · followed" row. No signal-cited order has been placed on any stack yet.
- A real bot → Redis → service → web publish observed live (E2E-001 passed only with an injected publish).
- The development half of A4 and of FR-SP-WEB-012.
- A3 (no explain-analyse recorded).
- Rendered motion for *Show* and *Load more* (no data).

**Owner-requested follow-up:**
- **Day control (ORCH-19).** Today/Yesterday or a last-7-days picker with `?day=` in the URL. On past days: no live note, no *Show*, no seen-through, and the counts for that day. Web only; the API already takes `day`. It came up when the owner saw an empty page after Bangkok midnight.

**Data and volume:**
- **Few signals.** The instrument master holds 11 instruments, and 460 extraction mentions were unresolved, so filings and wires about other companies never become signals. Widening the instrument universe is a follow-up (tidewatch-migrations and bot instrument master).
- **Default threshold.** Whether 0.30 is the right default (intent's watched assumption, A5) needs more days of data.
- **Bots column.** It will read "No bot acted" and "0 acted on by bots" until slice 6 bots cite signals.

**Service follow-ups (reviews and state):**
- The export silently caps at 10,000 rows; a truncation signal needs a contract change.
- R15 double-flip window: a publish may be delivered twice or missed if the flag toggles twice within one hand-over (the web dedupes by `signal_id`). Security L3: a 0↔1 flag swap can drop frames for every user during the swap. Consider desired-set generations or a debounce.
- Security L2: the shared strict body decoder accepts case-insensitive and repeated keys (also on `POST /orders`).
- The detail route's `uuid.Parse` accepts braced, URN and unhyphenated ids, while the order path accepts only hyphenated ones.
- "One read" comments overstate (equity valuation still MGETs held instruments); R15 comments lack the double-flip qualification; `trading.Recommend` has no production caller after the review fix.
- Migration I's header and the migrations README say `@>`; the list and export use `&&` (wording only).
- `encoding/csv` drops a bare CR inside a field (code-r1 nit 3).
- The integration harness's `freePort` race ("address already in use", pre-existing).

**Web follow-ups (reviews and state):**
- Security L1: the pre-fill hint shows for any URL `qty`. Optionally show it only when qty and side match `GET /signals/{id}`'s recommendation.
- Angular review r1:
  - the action hint hard-codes "sized at 10% of equity" whatever `recommendation.rule` says (#2);
  - `SignalMessage` optional fields (#3);
  - a hanging `GET /sources` keeps the opening on "Loading signals…" when stored filters name sources (#4);
  - a failed *Show* is silent (#5);
  - `feat-signals` imports `LoadMoreOutcome` and `bangkokInstant` from `feat-trade` and should graduate with `order-view.ts` (#8).
- Design:
  - A7: the Bots column stays 126px above 1250, so "Slack Water bought 6.5" wraps even at 1440; a wider column there would keep the 1100 fit.
  - A8: at ≤ 600, tall rows look half-empty with the Bots cell scrolled off.
  - A3: two controls are named "Account".
  - A5: separators dangle when filter groups wrap.
- Move `.chip` to its own file when a second screen draws a filter chip.
- ORCH-12 (widening a partial publisher) and the fix-r3 call (the watchlist hint dismissed when an instrument is chosen) stand unless the owner overrules them.

**Documentation and owner actions:**
- Apply migration I to the owner's own database (`make migrate-up` in tidewatch-migrations) before running the merged service; `/ready` stays 503 until then. I is additive with no backfill. Rollback is `make migrate-down`, which drops `user_settings` and the GIN index (destructive for settings only). Merge and rollout order: migrations → service → web.
- Reset the preview's `signals.filters` if wanted.
- Out of scope by design: decay after creation is still not recomputed (the shown freshness is the value at creation).

## Cross-cutting links

- [[signals-pipeline]]: the 3a pipeline whose `signals`, `documents`, `triage`, `extractions` and `document_instruments` rows this page reads; impact and the freshness formula behind ORCH-13.
- [[signals-ingest]]: slice 3a, which made the C-SIG-1 publish and the Market watch count that this slice builds on.
- [[signal-message-contract]]: the C-SIG-1 `signal` frame, forwarded unchanged on the new all-signals feed; `SignalMessage`'s lenient `tier`, `source_code`, `impact`.
- [[source-registry-and-ingest]]: `GET /sources` (no URL or config), the publisher-grouped Source chips, `config.structured`.
- [[decision-record]]: the first writes of `signal_ids`, `followed_recommendation`, `signal_snapshot` and `model`; the GIN index; the Bots column reading citing decisions.
- [[paper-trading]]: the order path's `decision_ctx`, the `check()` order with `checkSignal`, the new 422 code, the recommendation reusing `GET /trade`'s equity and the estimate's pricing, the Trade pre-fill.
- [[realtime-websocket]]: `subscribe_signals`/`unsubscribe_signals`, the per-connection flag, `ws_signal_feeds`, the closed message-type labels.
- [[redis-market-contract]]: `PSUBSCRIBE sig:*` on the one subscriber connection, the add-before-drop rule, R15 at-most-once; `px:last` usability (120 s) for context and recommendation.
- [[centralized-migrations]]: migration I, `RequiredSchemaVersion` `20261011182817`, the harness, and the bot's "not older than H" rule.
- [[market-timeseries]]: the `indicators` strip rows, zone runs and `atr14` behind Context at the time and "contradicted by price".
- [[instrument-master]]: `asset_class` and `calendar_id` behind the US/Thai split; the 11-instrument universe limiting signal volume.
- [[zone-transition-bot]]: Slack Water's 10%-of-equity rule that D2 borrows; slice 6 will let bots cite signals.
- [[bot-activity]]: the expandable-row pattern, now moved to `table.css` as the second consumer, with the Bots captures 0-pixel identical.
- [[bot-watch-verdicts]]: the shared expandable-row behaviour (insert empty, fill one task later, *Try again* focuses *Hide*).
- [[design-system-decisions]]: the pill chip, trust and impact bars, direction tones, `.nav-count` (the one rail badge), the sticky `.detail-wrap`, and the 1100 fit with wrapping Bots lines.
- [[auth-model]]: settings are scoped per user id; signals are global; citing decisions are scoped by `owner_user_id`.
- [[request-protection]]: the gated market group, CSRF on `PUT /me/settings/:key`, and the export as a cookie-carrying top-level GET.
- [[forge-preview-gateway]]: the isolated preview, the move to the shared retained workspace volume, related runs `sigpws`/`sigpbase`, and the same-origin export.
