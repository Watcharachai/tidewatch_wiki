# Signals context (spec 3b, `signals-context`): GDELT as a context layer, rules as data, an event calendar, and the scout's context- and calendar-driven discovery paths

> Slice 3 shipped as 3a (primary sources only). Its media context layer and the event calendar were deferred, and slice 6's scout kept two of its four discovery paths reserved "until spec 3b" (bots D10). This feature built them:
> - **GDELT GKG 2.1 ingest.** Two file streams, `en` and `translation`, are read every 5 minutes with no model call per article. A keep gate whose rules are database rows (`theme_rules`, `domain_rules`) decides what is stored. Only matched rows are stored, as `gkg_mentions`, with 90-day retention.
> - **Context features.** Per instrument (and the class rows `class:gold`, `class:crypto`) and per 15-minute window: trailing-24 h article count, tone, countries and publishers, against a 30-UTC-day baseline with a Poisson floor.
> - **Coverage signals.** A z crossing writes one `media` signal per instrument per Bangkok day with `origin = 'context'` and `impact 0.0000`. It is visible on the Signals page and published as C-SIG-1, and nothing ever treats it as a trigger.
> - **Event calendar.** US earnings come from Finnhub (one call a day). The economic rows (FOMC, BoT MPC) are seeded in the migration.
> - **Two optional discovery paths in the scout.** `schedule.scout.discovery.context {enabled, z_min}` and `.calendar {enabled, sessions_ahead}` feed the existing rank-and-cap step before any model call. A version without the key hashes and behaves exactly as before.
> - Every `propose` decision now carries `market_state.context` and `market_state.calendar`.
>
> **Status (2026-10-30).**
> - **Merged** on 2026-10-30, all four PRs, by Claude on the owner's instruction, in the order migrations → service → bot and web:
>   - tidewatch-migrations #15 (https://github.com/tidewatch-labs/tidewatch-migrations/pull/15) → `89669e8` (19:40:46Z);
>   - tidewatch-service #17 (https://github.com/tidewatch-labs/tidewatch-service/pull/17) → `ef9e93e` (19:42:58Z);
>   - tidewatch-bot #18 (https://github.com/tidewatch-labs/tidewatch-bot/pull/18) → `b083697` (19:57:23Z);
>   - tidewatch-web #22 (https://github.com/tidewatch-labs/tidewatch-web/pull/22) → `9dc59cf` (19:57:29Z).
> - **Production.** The service runs `ef9e93e`: `/info` was confirmed and `/ready` answered 200 at about 19:56Z. Migration N reached production through the service's sync (see Database). Bot and web: deploy triggered, not verified here. Production's bot chart does not yet list `context` in its collectors value, so **the context runner is not running in production** until the owner adds it. The discovery paths stay off for every bot until a version sets `schedule.scout.discovery`.
> - **Verified.** Of the 39 PRD acceptance IDs, 33 are verified, FR-SC-MIG-003 is partial (US CPI and payrolls not seeded) and FR-SC-E2E-001..005 are unverified. The preview was not refreshed onto L and M after the main updates, and the web e2e specs were not re-run on the merged tree.

**Sources (inputs to this document).**
- **Spec.** `/Users/maichinu/tidewatch/tidewatch-specs/signals-context/`: `intent.md` (O1–O7, D1–D7, PD1–PD14, A1–A3; confirmed 2026-10-27), `prd.md` (PRD-S1–S14, §4–§11, 39 `FR-SC-*` IDs), `build-prompt.md`. No mockup. The PRD calls the migration "L"; this build's letter is N (ORCH-2).
- **Build record.** `/Users/maichinu/tidewatch/.forge/features/signals-context/`: `state.json` (`perProject`, `mainUpdates`, `merge`, `log`, `ownerQuestions`, `followUps`), `verification.md`, `planning/cross-plan-decisions.md` (ORCH-1..7), `planning/tidewatch-bot/contracts.md` r1 (sha256 `60aa27b0…38f3`, the cross-project vocabulary), `reviews/` (bot r1–r4 code and security, service r1, web r1–r2). Evidence paths below are relative to this folder.
- **Plans** (merged state, `.plans/signals-context.md` in each worktree under `/Users/maichinu/tidewatch/.forge/docker/runs/sctx-57acb7d1/worktrees/`):
  - bot `6945fd5d6c`: S1–S19 plus the wrap-up docs step. S1–S2 edited the companion migrations worktree (ORCH-1). Approved at plan revision r17.
  - service `329891b601`: S1–S3 (r4).
  - web `5eb4e5c7ea`: S1–S6 (r3).
  - migrations `b7ddc75378`: no plan of its own; migration N and its harness were planned and verified as bot S1–S2.
- **Code** read from those worktrees at their merged heads, including `migrations/20261028120200_signals_context.sql` (its header records the decisions and seeds), `packages/ingest/docs/gdelt-gkg-layout.md` (the measured operating figures) and each repo's `CLAUDE.md`.

## Concept

### The problem

The brain read filings, wires, exchange notices, Binance TH listings and Finnhub headlines, but it had no media context and no calendar.
- The scout could only propose on signals and chart setups.
- Slice 8's meta-model had no context inputs.
- The owner wanted coverage and tone anomalies and upcoming earnings noticed:
  - without a model call per article, inside the $1/day ceiling;
  - with every rule and threshold a row that changes without a deploy.

### The approach, by owner decision (intent D1–D7)

- **D1. A coverage anomaly is a `media` signal with a synthetic document.** It has `origin = 'context'`, `impact = 0`, `conviction = 0`, `p_neutral = 1`, `event_type = other`, model ids `context.v1`, and direction `neutral` unless tone z also crosses. Rejected alternatives: no `signals` row until the "what the bot sees" view, or a real impact so the signal path could act. Reason: it satisfies both "surfaced as media signals" and "not a trigger", and the title carries the summary, so no web change is needed.
- **D2. Two optional keys in `bot-config.v2`, absent means off, with web toggles.** Rejected: a `bot-config.v3`, or running the paths for every scout. Reason: existing versions keep their hash and behaviour.
- **D3. Grain.** One `context_features` row per subject per 15-minute window in which the subject was mentioned, trailing-24 h counts against a 30-UTC-day baseline. Class rows (`class:gold`, `class:crypto`) are recorded but never used for discovery.
- **D4. Keep gate.** A row is kept on a gate theme AND an active instrument (or a class tag), unless its publisher domain is denied. Only matched rows are kept. Rejected rows would cost about a million rows a day, and a window can be re-ingested from GDELT's archive under new rules.
- **D5. Earnings from Finnhub for US instruments; economic events as seeded yearly rows.** One `event_calendar` table. No manager gate on macro events in 3b.
- **D6. Both streams from day one, no automatic backfill.** No anomaly before 7 baseline days (`min_baseline_days`), full strength at 30. A bounded owner-run backfill exists.
- **D7. Thresholds and constants live in `context_versions`, stamped on outputs.** The migration is additive, and the service pin does not move for it.

Non-goals kept: any model call per GDELT article, the DOC 2.0 API, a `coverage` event type, any Signals page change, a sector column, class-level discovery, Thai earnings, and a paid economic calendar.

### How it runs (bot, `tidewatch-bot`)

**1. GDELT collector** (`packages/ingest/src/collectors/gdelt/`, its own registry family; plan PB3–PB5):
- **Sources.** `gdelt-gkg-en` and `gdelt-gkg-translation`, each on a 300 s timer under `runner:ingest`. One pass writes one `source_runs` row and commits **one transaction per window**: mentions, `source_files`, quarantine rows and the cursor together.
- **Cursor and stamps.** The cursor is per stream: `{stream, last_settled_stamp, pending:[{stamp, attempts, first_missing_at}]}`.
  - The first run settles the newest `lastupdate` stamp without fetching (no backfill).
  - A pass handles at most 8 due stamps, oldest first, and never steps past an unsettled stamp.
  - A 404 becomes `missing_retryable`. After `missing_retry_hours` (6) the collector reads the stream's own manifest tail (`Range: bytes=-2097152`; on a 206 the first line is discarded). The stamp then becomes `gap_confirmed`, or the run fails after 12 attempts. A stamp the manifest line does not list is filed `unlisted`.
- **Download and integrity.** Windows are streamed by market-data's new `transport/stream-zip.ts` (`streamZipEntry`, `fflate`). Caps from `sources.config`: 64 MiB zipped, 256 MiB inflated. SHA-256 and MD5 are computed while streaming, and the MD5 is checked against the **same stream's** manifest. Limits: 2 streamed requests per second, a 120 s window deadline. `fetch.ts` keeps its 4 MiB cap and was not edited. Only GDELT's own `http://` origin is rewritten to `https://data.gdeltproject.org`; any other host fails the run with `SourceConfigError`.
- **Parse.** 27 tab-separated columns, quote processing off, HTML entities decoded in `PAGE_TITLE`.
- **Tripwire.** More than 5 % quarantined rows in a file of at least 100 rows quarantines the window: its kept rows roll back, the run fails with `QuarantineRatioExceeded`, and the stamp settles.
- **Keep gate** (`gate.ts`, `match.ts`). `theme_rules` and `domain_rules` are re-read every run, and the bot never writes them. The order is: denied domain, then a gate-theme hit (a zero weight still gates), then subjects. Organisation and name strings are normalised and corporate suffixes stripped, then matched exactly against `instrument_aliases` of kind `name` for active instruments. Names under 4 characters and `ambiguous_names` never match. A class-tag theme adds `class:<asset_class>`.
- **Backfill.** `source-backfill --source gdelt-gkg-en|gdelt-gkg-translation --from --to`, at most one UTC day per call. It writes mentions, files and quarantine rows, and no feature rows.

**2. Real-data fix: rows split by raw newlines (S15, finding GDELT-NL).**
- **What happened.** On the live 2026-10-27 backfill, the tripwire quarantined translated window `20261027181500` (143 of 2,731 lines, 5.24 %, `missing_fields`). The cause was raw newlines in `V2ExtrasXML`: 27 `berliner-zeitung.de` rows and 2 `tyzden.sk` rows, inside a `mailto:` footer.
- **Fix.** The parent session, under the owner's delegation, chose the parser fix, not a deny-list entry. A row starts only on `^\d{14}-T?\d+\t`; any other line is joined to the previous row with one space.
- **Live re-measure.** 96 of 96 windows parsed, and the stream's `missing_fields` fell from 463 to 0 (`evidence/tidewatch-bot/S15/backfill-2026-10-27-translation.json`).

**3. Bounds from the security reviews (S17–S19).** Every bound is a refusal or a drop, never a truncated mention.
- **Streaming:**
  - received chunks are coalesced into 4 KiB parts;
  - an entry over 1,000,000 lines is refused (`line_count`);
  - a row over 1,000 continuation lines is `body_too_large`.
- **Per row, before decoding:**
  - record id at most 32 characters;
  - URL at most 2,048, with no control character or space;
  - domain at most 253, matching `^[a-z0-9.-]+$`;
  - list fields read to at most 4,096 entries, names at most 256;
  - themes must match `^[A-Z0-9_]{1,128}$`;
  - tone is read up to its first comma;
  - the title is decoded from at most 10,010 raw units (surrogate-safe), with control characters turned into spaces.
- **Per mention and per window:**
  - 128 subjects per row;
  - 64 themes and 64 countries per mention;
  - 10,000 mentions per window;
  - a 16 MiB charge per window (refused `mention_bytes`);
  - `gkgMentionRowsJson` (`commit-rows.ts`) is the single row mapping for the commit, so the commit payload stays inside the charge.
- **Memory.** About 66 MiB per window at commit, 132 MiB for both streams, against the 576 MiB production heap. Review r4 measured the round-3 attack zip refused at 817 mentions, with 9.8 MiB retained and a 24.2 MiB commit peak (it was 289.7 / 552.5 MiB).

**4. Context runner** (`packages/context`, the `context` Runner holding `runner:context`; no model call, at most one pooled connection, `SERVE_POOL_MAX` stays 12):
- **Notifications.** A window notifier, shared by `ingest` and `context` (PB7), triggers feature computation after each window commit. A 60 s sweep of `source_files` recovers lost notices. The queue holds at most 64 pending notices; a notice past that is dropped silently and the sweep computes its window.
- **Features** (`features.ts`), written at `ts = stamp + 15 min` and upserted on `(subject, ts)`, so the second stream's arrival recomputes the same row:
  - `articles_24h`, `countries_24h`, `publishers_24h`, `tone_mean_24h` and up to five `top_themes`;
  - the baseline is the trailing 30 complete UTC days;
  - `sd_eff = max(baseline_sd, sqrt(max(baseline_mean, 1)))`;
  - z is null under 7 baseline days.
- **Coverage signals** (`coverage.ts`). The trigger is an instrument subject with `articles_z ≥ z_articles` (2.0) and `articles_24h ≥ min_articles_24h` (5). One transaction writes:
  - a synthetic `documents` row: `stage = signalled`, so `runner:signals` never triages it; `canonical_url = tidewatch://context/<instrument_id>/<bkk_day>`, `ON CONFLICT DO NOTHING`, so one per instrument per Bangkok day; publisher "GDELT Project"; `body_status headline_only`;
  - its `document_versions` row (the feature row and constants as JSON);
  - a `document_instruments` subject row;
  - the `signals` row: `origin = 'context'`, `p 0.000`, `p_neutral 1.000`, `impact 0.0000`, `severity = min(5, |z|)`, model ids and `prompt_version` `context.v1`.
  - After the commit, C-SIG-1 goes out on `sig:<instrument_id>`. A failed publish rolls nothing back.
  - The title format is `Coverage: {symbol} {z:.1f}σ above its 30-day baseline · {n} articles · {countries} countries · tone {tone:+.1f}`. Decimals are rounded half away from zero from their exact decimal strings, and tone is always signed (PB18).
- **Calendar** (`calendar.ts`):
  - One Finnhub `GET /api/v1/calendar/earnings?from=<today−7>&to=<today+60>` runs daily at 05:00 Asia/Bangkok, and at start when the last successful refresh is more than a day old.
  - Results are filtered to master instruments by `ticker` alias on the `webull` venue. The range's `earnings` rows are replaced in one transaction, and a `source_runs` row is written on `finnhub-earnings-calendar`.
  - The call shares one process-wide 50-per-minute Finnhub budget with company news (`collectors/finnhub-budget.ts`, keyed on the clock, using the `finnhub-company-news` row's `per_minute`).
  - Only transient failures (429, 5xx, timeout) retry hourly. A 401/403 waits for the next slot. A missing `FINNHUB_API_KEY` writes a `missing_secret` noop run.
- **Renewal warning** (PB11; owner ruling "Per series", an approved scope change to FR-SC-CAL-002):
  - `context_calendar_expiring` fires once per **series** per Bangkok day when that series' last seeded row is fewer than 60 days ahead.
  - The `series` value is a closed code (`fomc`, `bot_mpc`, `us_cpi`, `us_payrolls`, `other`), never the title.
  - BoT is seeded only through 2026-12-23, so its warning is active from the first start and repeats daily until a 2027 BoT migration ships.
- **Read model** (`read-model.ts`, used by `bots`): `latestFeatures`, `earningsBetween`, `nextEarnings`, `nextMacro`. It is wired by `worker/serve.ts` as the **required** `BotsRunnerGeneralDeps.createContextReadModel` (PB17), so the paths cannot silently never run.

**5. Scout discovery** (`packages/bots/src/general/scout.ts`; PRD §4.10):
- **Context-driven.** A scope instrument qualifies when its newest feature row in `(startedAt − 24 h, startedAt]` has a non-null `articles_z ≥ z_min`. It attaches the day's coverage signal through `CONTEXT_SIGNALS_ON`, which is keyed on the canonical URL of the wake's Bangkok day (S17), not on `created_at`.
- **Calendar-driven.** A scope instrument qualifies with an `earnings` row within `sessions_ahead` sessions on its own calendar. Stocks only; crypto and gold never qualify.
- **Ranking.** Both paths enter the unchanged rank-and-cap step (S4) with `impact_w = min_impact`, `p = null` and `horizon = days`, so a signal-driven survivor outranks them at equal allocation. An instrument qualified by several paths is one candidate, and `policy_result.discovery` lists the paths in the order `signal`, `setup`, `context`, `calendar` (with `context_z` for context).
- **Theses.** Template theses for survivors without a signal: `Coverage {z:.1f}σ above its 30-day baseline (...)` and `Earnings {EEE d MMM} (...)`.
- **`bot_thesis.v2`** (PB8) is live, because v1's text described `market_state` as chart state only. It is recorded beside v1, which stays untouched.
- **Run counts.** `bot_runs.counts.by_discovery {signal, setup, context, calendar}`.
- **Manual runs.** A manual scout request on `scout.kind = off` runs setup plus the enabled discovery paths.

**6. Never a trigger** (PRD §4.7, PD11). The trigger reads filter `origin = 'document'`:
- `SIGNALS_SINCE`, `SIGNALS_SINCE_ON` and `QUALIFYING_SIGNAL` (the scout window, the `signal_driven` due check, the manager's events, adds and trims), with the memory store mirroring them;
- `LATEST_SIGNAL` (signals novelty, S17);
- after the M update, the learning loop's post-mortem `LATER_SIGNALS` query too.

So with any `min_impact`, including 0, a coverage signal never qualifies, never writes a `long_only` refusal, never wakes a bot and never triggers an add or trim. `impact = 0` is only a second line of defence. The Market watch count and the Signals page still count both origins.

**Telemetry.** PRD §4.13's 8 events and 6 metrics, as closed sets split by owner (PB6), with `telemetry-union.spec.ts` checking the union:
- **Ingest side:** events `context_window_finished`, `context_window_quarantined`, `context_gap_confirmed`; metrics `context_gkg_rows_total{source,outcome}`, `context_windows_total{source,status}`, `context_window_lag_seconds{source}`.
- **Context side:** events `context_features_written`, `context_signal_emitted`, `context_calendar_refreshed`, `context_calendar_expiring`, `context_stage_failed`; metrics `context_features_written_total`, `context_signals_total`, `context_calendar_events{kind}`.

**Runtime counts after the merges:**
- 15 `COLLECTOR_NAMES` (`learning` 14th, `context` 15th, enabled by default when `MARKET_DATA_COLLECTORS` is empty);
- 13 `SOURCE_CODES`;
- 7 recorded prompt versions (`triage.v1`, `extraction.v1`, `scoring.v1`, `bot_decide.v1`, `bot_thesis.v1`, `bot_thesis.v2`, `post_mortem.v1`);
- 10 packages in the image.

### Measured GDELT figures (`packages/ingest/docs/gdelt-gkg-layout.md`)

Measured on 2026-10-27 (96 windows per stream) against a 526-instrument universe with no SET names:

| Figure | `en` | `translation` |
| --- | --- | --- |
| Rows read | 117,445 | 222,965 |
| Kept-row ratio (committed) | 2.18 % (2,561) | 0.62 % (1,387) |
| `rejected_theme` | 85.48 % | 84.63 % |
| `rejected_match` | 10.48 % | 13.03 % |
| `rejected_domain` | 1.87 % | 1.51 % |
| Inflate ratio | 3.07–3.11× | 3.15–3.29× |
| One-day backfill call | 61.4 s, 503,846,895 bytes | 65.2 s, 870,231,067 bytes |

- **Mentions.** The 3,948 kept rows wrote 7,000 `gkg_mentions` (1.77 subjects per kept row). The PRD's nexus comparison was 12.4 % and 8.7 % for a logistics vocabulary.
- **Volume.** About 1.38 GB a day for both streams (the PRD estimated 1.8 GB). The largest window was 21,054,631 bytes zipped.
- **Request tolerance.** 392 requests over two runs: no 429, 403 or 5xx, and at most 2 streamed requests in any rolling second. This is an observed floor, not a published limit.
- **Real maxima against the caps.**
  - subjects per row: 25 of 128;
  - mentions per window: 164 of 10,000;
  - list entries: 680 of 4,096;
  - names: 62 of 256;
  - themes: 61 of 128;
  - countries: 36 of 64;
  - busiest window: 0.70 of 16 MiB.

### Build-time decisions worth keeping

- **Migration letter N (ORCH-2).** Two sibling builds started at the same time and own L (accounts-roles) and M (learning-loop), so this feature's migration is N and merged after them (ORCH-5).
- **Pins.** This build never moved a pin. The service's `RequiredSchemaVersion` and the migrations harness `required_migration` were J at build time; the sibling builds moved them to L and then M. Only the bot's SQL harness requires N.
- **The migration was planned inside the bot plan (ORCH-1)**, in a companion worktree with its own PR, because the bot is N's only writer and its harness pin is the one that moves.
- **Cross-project vocabulary (ORCH-3).** The bot plan's `contracts.md` r1 pinned the `discovery` key set, bounds and defaults, every refusal's field and reason, and the bytes of `bot-version.v2-discovery.json`. The service and web planned against that revision.
- **Service release note** (accepted by the parent, 2026-10-28). After N, an API client re-posting a pre-N bot config gets `400 config.source_weights missing` instead of `409`, because N adds three `sources` rows that the config must weigh. The web's forward rule (weight `"0"` for unlisted sources) is unaffected.
- **Owner rulings** (2026-10-28):
  - BOT-Q1, "Retry only": one pinned BLS retry, then FOMC and BoT only;
  - BOT-Q2, "Per series";
  - SVC-Q1: no API change for the coverage signal's detail body;
  - WEB-OQ-1: raw source codes stay in *Sources and weights*;
  - WEB-OQ-2: keep the DESIGN.md snapshot refresh;
  - WEB-OQ-3: accept the shipped Signals rendering;
  - execution in lanes.
  - The parent also relayed that the owner would save the BLS pages to `inputs/`; the folder stayed empty, so FR-SC-MIG-003 stays partial.

### Review history

- **Plans.** Bot: 17 revisions (r1, r6, r11 and r16 had CHANGES REQUESTED), approved at r17. Service: approved at r4. Web: approved at r3.
- **Bot code and security.**
  - r1 CHANGES REQUESTED: the `LATEST_SIGNAL` novelty read lacked the origin filter; a newline-dense zip could exhaust the heap; plus informational findings on stored-string bounds, personal data in fixtures, the BLS scanner path and the Finnhub budget. Fixed in S17.
  - r2 security CHANGES REQUESTED: a tiny-chunk partial-line rope, mention fan-out and row pinning, record-id length. Fixed in S18.
  - r3 security CHANGES REQUESTED: per-mention size was unbounded (290 MiB retained, 552 MiB commit peak from a 516 KB zip). Fixed in S19.
  - r4: code APPROVED (4 nits), security APPROVED (4 low follow-ups).
- **Service.** r1 code and security APPROVED.
- **Web.** r1: all four reviewers CHANGES REQUESTED, on the preview-evidence gate plus a switch-alignment design issue. r2: all APPROVED, after fix 1 and fix 2 (390 px focus under the sticky strip), with design approved at the PV2 re-check.
- **Bot PR history.** The bot PR is a single squashed commit (`2de076b` on base `87495d5`), plus the CI timeout fix `5a75c1d` and the two main-merge commits. An earlier local commit held unredacted fixture blobs (personal email addresses in GKG excerpts, review finding SEC-I2). The fixtures were redacted in S17 (allowlist of role mailboxes, scanner spec), and the branch was squashed before its first push, so that commit was never pushed. No remote ref contains it (`state.json` `perProject.tidewatch-bot.secI2`).

### Merge updates (ORCH-5)

The branches stayed on `main` until the sibling builds merged. Then `main` was merged into every branch twice, with no rebase or force-push (`state.json` `mainUpdates`):
- **After L merged** (2026-10-30T04:12Z):
  - migrations `988a334`, service `78c449a`, bot `a4eb5f8`, web `97a0f8a`;
  - service saves in `entitlements_test.go` and `bots_caps_test.go` were wrapped in `withLiveSources`;
  - the web kept both sides of `DESIGN.md`.
- **After M merged:**
  - migrations `59f57ae` (18:02Z);
  - service `59a2bdb`, bot `c228874`, web `3ebd65d` (19:40Z, after learning-loop service#16, bot#17 and web#21 merged).
- **Main conflict resolutions:**
  - **Migrations harness.** While N is the newest migration, J's down test and M's down test (steps 10d and 10e) report "not run", never "passed". N's down is proven wherever a down crosses N (`down-to 20261021082304`, `down-to 20261004153023`, `down-to 0`). `check-disposable-db` PASS (10 passes, 0 FAIL; `evidence/tidewatch-migrations/merge-M/`).
  - **Bot:**
    - 15 collectors (learning 14th, context 15th) and 7 prompt versions;
    - the post-mortem query `LATER_SIGNALS` (`packages/bots/src/learning/pg-store.ts`) reads `origin = 'document'` only;
    - `sql-integration.sh` requires N while keeping L's and M's checks and records the SHA-256 of H, J, L, M and N;
    - run-many green (1,709 tests), `sql-integration` PASS with L, M and N (`evidence/tidewatch-bot/merge-M/`).
  - **Service:**
    - `botconfig.go` keeps both `discovery` and `learning`, with the shared optional-key helper renamed to main's `objectWith`;
    - the `learnedConfig` test fixture lists all 13 sources;
    - the stats compat normaliser sets N's three source rows aside (`nRows`) so the slice-7 goldens stay byte-unchanged;
    - integration 5,531 PASS, 0 FAIL (`evidence/tidewatch-service/merge-M/`).
  - **Web.** `discovery` and `learning` key sets both intact, discovery fixture unchanged, 5 snapshot hashes recomputed, 7,028 unit tests and a production build OK (`evidence/tidewatch-web/merge-M/`).

## Database

**Migration N:** `tidewatch-migrations/migrations/20261028120200_signals_context.sql` (`signals_context`, goose version `20261028120200`).
- **Order.** Goose order is K (`20261021082304`), L (`20261028120000`, accounts_and_roles), M (`20261028120100`, learning_loop), N.
- **Pins.**
  - **The required schema version is M (`20261028120100`), set by learning-loop.** The service's `RequiredSchemaVersion` and the migrations harness `required_migration` are both `learning_loop`.
  - **N is never pinned.** The service reads no N table or column, `signals.origin` included.
  - Only the bot's `scripts/sql-integration.sh` requires N: anchored lookup `^[0-9]{14}_signals_context[.]sql$`, applied and not newer than the newest applied version, SHA-256 recorded (`ba22ec97…6052` in `verification.md`).
  - The service's `scripts/integration-test.sh` also requires N in the checkout, for its data only.
- **Shape.** Additive on K, in goose's default transaction, with no trigger, function, view or extension. `signals.origin` is the only change to an earlier table.

```sql
-- Three sources rows (PRD 4.1)
-- gdelt-gkg-en / gdelt-gkg-translation: media/media, fetch_kind gdelt, 'GDELT Project',
--   https://data.gdeltproject.org/gdeltv2/lastupdate(-translation).txt, schedule 300 s, credibility 0.60,
--   config {"stream", "missing_retry_hours": 6, "max_zip_bytes": 67108864, "max_inflated_bytes": 268435456,
--           "quarantine_ratio_pct": 5, "quarantine_min_rows": 100}
-- finnhub-earnings-calendar: media/media, fetch_kind json, 'Finnhub', https://finnhub.io/api/v1/calendar/earnings,
--   schedule 86400 s, config {"key_variable": "FINNHUB_API_KEY", "days_back": 7, "days_ahead": 60, "owner": "context"}

CREATE TABLE context_versions (context_version integer PRIMARY KEY CHECK (context_version > 0),
                               constants jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
-- v1: {"z_articles": 2.0, "z_tone": 2.0, "min_articles_24h": 5, "min_baseline_days": 7, "baseline_days": 30,
--      "novelty_window_days": 5, "sd_floor": "poisson", "ambiguous_names": [35 names: "apple", "visa", ... "gas"]}

CREATE TABLE theme_rules (theme text PRIMARY KEY CHECK (theme ~ '^[A-Z0-9_]+$'),
  bucket text NOT NULL CHECK (bucket IN ('gate','score','class_tag')),
  match_kind text NOT NULL DEFAULT 'exact' CHECK (match_kind IN ('exact','prefix')),
  weight smallint NOT NULL DEFAULT 1 CHECK (weight >= 0), asset_class text CHECK (asset_class IN ('stock','crypto','gold','fx')),
  is_active boolean NOT NULL DEFAULT true, note text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((bucket = 'class_tag') = (asset_class IS NOT NULL)));
CREATE TABLE domain_rules (domain text PRIMARY KEY CHECK (domain = lower(domain) AND domain ~ '^[a-z0-9.-]+$'),
  action text NOT NULL CHECK (action IN ('deny','trust')), is_active boolean NOT NULL DEFAULT true,
  note text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE gkg_mentions (ts timestamptz NOT NULL, gkg_record_id text NOT NULL,
  source_code text NOT NULL REFERENCES sources, subject text NOT NULL, instrument_id text REFERENCES instruments,
  asset_class text, publisher_domain text NOT NULL, url text NOT NULL, title text, tone numeric(6,2),
  themes text[] NOT NULL, countries text[] NOT NULL, language text, is_translated boolean NOT NULL,
  PRIMARY KEY (subject, ts, gkg_record_id),
  CHECK ((instrument_id IS NOT NULL AND subject = instrument_id)
      OR (instrument_id IS NULL AND asset_class IS NOT NULL AND subject = 'class:' || asset_class)));
-- hypertable on ts, 7-day chunks, no default index; columnstore (segmentby subject, orderby ts DESC) after 30 days;
-- retention 90 days (the one retention policy)

CREATE TABLE context_features (ts, subject, instrument_id, asset_class, context_version REFERENCES context_versions,
  articles_24h, baseline_days, baseline_mean numeric(10,3), baseline_sd numeric(10,3), articles_z numeric(8,3),
  tone_mean_24h, tone_baseline_mean, tone_baseline_sd numeric(6,2), tone_z numeric(8,3), countries_24h, publishers_24h,
  top_themes jsonb NOT NULL DEFAULT '[]', computed_at, PRIMARY KEY (subject, ts),
  CHECK (same subject rule), CHECK (baseline_days >= 7 OR articles_z IS NULL));
-- hypertable on ts, 28-day chunks; columnstore after 90 days; no retention
CREATE INDEX context_features_instrument_ts_idx ON context_features (instrument_id, ts DESC) WHERE instrument_id IS NOT NULL;

CREATE TABLE event_calendar (event_id uuid PRIMARY KEY DEFAULT uuidv7(), kind text NOT NULL CHECK (kind IN ('earnings','economic')),
  instrument_id text REFERENCES instruments, title text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
  scheduled_date date NOT NULL, scheduled_at timestamptz, time_hint text CHECK (time_hint IN ('bmo','amc','dmh')),
  source_code text REFERENCES sources, external_ref text, detail jsonb NOT NULL DEFAULT '{}',
  first_seen_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((kind = 'earnings') = (instrument_id IS NOT NULL)), UNIQUE (kind, instrument_id, scheduled_date, title));
CREATE INDEX event_calendar_instrument_date_idx ON event_calendar (instrument_id, scheduled_date) WHERE kind = 'earnings';
CREATE INDEX event_calendar_kind_date_idx ON event_calendar (kind, scheduled_date);

ALTER TABLE signals ADD COLUMN origin text NOT NULL DEFAULT 'document' CHECK (origin IN ('document', 'context'));
CREATE INDEX signals_origin_created_idx ON signals (origin, created_at DESC) WHERE origin = 'context';
```

- **Constraint names** are PostgreSQL's defaults: `gkg_mentions_check`, `context_features_check` (the subject rule), `context_features_check1` (the baseline rule), `theme_rules_check`, `event_calendar_check`, `signals_origin_check`.
- **`theme_rules` seeds (37, all `exact`, weight 1).** Each theme was checked against GDELT's `LOOKUP-GKGTHEMES.TXT`, read 2026-10-28T02:20:22Z (lookup sha256 `9cfd2554…99cf`, 59,315 lines). Each theme's document count is recorded in N's header, with the output of `scripts/check-gkg-themes.sh` (FR-SC-MIG-002).
  - 25 `gate` rows: the PRD's 22 `ECON_*` plus the build's `ECON_CUTOUTLOOK`, `ECON_NATIONALIZE`, `ECON_PRICECONTROL`.
  - 2 `class_tag` rows: `ECON_GOLDPRICE → gold`, `ECON_BITCOIN → crypto`.
  - 10 `score` rows: the `WB_*` finance families.
  - Ten candidate themes are absent from the lookup and were never seeded (for example `ECON_MERGER`, `ECON_CRYPTOCURRENCY`).
- **`domain_rules` seeds (9 deny rows, no trust rows),** each with a note naming the window it was observed in: `pr-inside.com`, `prokerala.com`, `prnewswire.com`, `zazoom.it`, `sanantoniopost.com`, `tucsonpost.com`, `californiatelegraph.com`, `themarketsdaily.com`, `dailypolitical.com`. The last three came from the build's own windows, beyond the plan's six.
- **Economic seeds** (one INSERT, only events after N's version instant 2026-10-28T12:02:00Z). `scheduled_at` is UTC; `detail` holds `{source, local_time, tz, published_on}`:
  - **FOMC decision:** 10 rows, 2026-10-28 to 2027-12-08 (federalreserve.gov, read 2026-10-28T02:22:04Z).
  - **BoT MPC decision:** 1 row, 2026-12-23 (bot.or.th, read 02:22:05Z). The 2027 schedule was unpublished.
  - **US CPI and US payrolls: not seeded.** BLS answered 403 to both scripted reads on the one pinned retry (2026-10-28T02:22:42Z, `seed_set=fomc,bot`; `planning/tidewatch-bot/measurements/bls-retry.txt`, `bls-capture.txt`). They follow in a later data migration.
- **Seeds are data.** A change to a rule, constant, source row or calendar row is a new data migration, never an edit of N. Next year's calendar rows ship as a new migration.
- **Down** is destructive and owner-only. It removes policies before hypertables, then the rules and constants, then the three sources' signals, document rows, quarantine rows, documents, runs, files, cursors and rows, in dependency order. Every statement uses `IF EXISTS`, never `CASCADE`.
- **Harness.** `scripts/check-disposable-db.sh` appends `signals_context` to `expected_migrations` and adds `relations_`, `assert_`, `absent_` and `hypertables_signals_context`. H's exact `signals` lists and B's job list leave N's objects to N by name.
- **Production rollout.** N reached production through the service's sync. The migrate job is an ArgoCD sync hook in the service chart (the service CLAUDE.md calls it the migrate PreSync hook), so it runs only when the service syncs. The migrations deploy bumped `migrate.image` 8 s before the service bump, so the sync that rolled `ef9e93e` ran N (`state.json` `merge.prodChecks`). The record infers this from the bump order; it holds no production `goose_db_version` read.

**Volume (PRD §5.3, measured above).** About 192 windows and 1.38 GB a day are streamed and discarded, with zero model spend. `gkg_mentions` is bounded by its 90-day retention. `context_features` has no retention and is compressed after 90 days.

## API

**No new route.** No pin move, no environment variable, no Redis key, no `/ws` frame.

**The API surface did change in three ways:**
1. the optional `schedule.scout.discovery` config key;
2. three new rows on `GET /sources`;
3. coverage signals, which now appear on the signals routes.

**1. Bot version vocabulary: optional `schedule.scout.discovery`** (contracts r1 §2; bot `readConfigV2`, service `internal/trading/botconfig.go`, web `bot-config.model.ts`, identical in all three).

```json
"scout": {
  "discovery": {
    "calendar": { "enabled": true, "sessions_ahead": "5" },
    "context":  { "enabled": true, "z_min": "2.0" }
  },
  "kind": "times",
  "min_impact": "0.45",
  "times": ["..."]
}
```
(excerpt of `bot-version.v2-discovery.json` as stored)

- **Absent means off.** A config without `discovery` canonicalises and hashes exactly as before, so every existing version keeps its hash. `bot-version.v2.json` is unchanged (`44161eb0…8790`).
- When `discovery` is present, both sub-objects are required, with closed key sets.
- **Values:** `z_min` is a decimal string in [0.5, 10] (web default `"2.0"`); `sessions_ahead` is a whole-number string in [1, 20] (default `"5"`). Both are checked whatever `enabled` is.
- **Refusals:** `400 invalid_request` with `details {field, reason}` and a dotted field such as `config.schedule.scout.discovery.context.z_min`. Reasons are `out_of_range`, `invalid`, `unknown_field` and `missing`. `"discovery": null` is `invalid`.
- **Contract fixture.** `bot-version.v2-discovery.json` (28,847 bytes, SHA-256 `ce6242a961c2d47620f4b816281c71697cd9f3bbfa720138fd3a48090d675132`) is byte-identical in the bot (`packages/bots/fixtures/`), the service (`internal/trading/testdata/`) and the web (`src/app/pages/workspace/data/testdata/`). It holds 8 accepted cases and 33 refusals, each with its field and reason, and every reader runs them all.
- **Where it applies.** `POST /bots` and `POST /bots/:bot_id/versions` accept it. The service reads no discovery value. `GET /bots/:bot_id/upgrade` (legacy translation) emits no `discovery`.
- **Behaviour change (service release note).** After N, re-posting a pre-N config without the three new `source_weights` entries is `400 config.source_weights missing`, not `409 version_unchanged`.

**2. `GET /sources`.** It lists N's three rows (13 in all) after `finnhub-company-news`, in the media group: `finnhub-earnings-calendar` (Finnhub), `gdelt-gkg-en` (GDELT Project), `gdelt-gkg-translation` (GDELT Project). No URL, host, `config` key or key variable appears (`TestSources_ListsContextSources`).

**3. Signals routes: coverage signals.** No code change in the service.
- **List.** `GET /signals` lists them like any signal (impact `0.0000`), so they appear only at `min_impact=0.00`.
- **Detail.** `GET /signals/:signal_id` answers 200 with exactly `SignalDetail`'s keys:
  - headline = the coverage title, publisher `GDELT Project`, tier `media`, `body_status headline_only`;
  - `triage` and `extraction` null;
  - `canonical_url` null, because the `tidewatch://` URL fails the http/https rule;
  - `p 0.000`, `p_neutral 1.000`, `impact 0.0000`, every model id `context.v1`.
- **`origin` is stored but not exposed** in any body. The `document_instruments` subject row is joined but not rendered (SVC-Q1; `TestSignals_Detail_ContextOrigin` asserts that the body holds no `"origin"`, no `tidewatch://` and no `coverage anomaly`). Exposing `origin` waits for the "what the bot sees" view.
- **C-SIG-1** is unchanged (`signals-message.v1.json`). Coverage signals are ordinary messages on `sig:<instrument_id>` with `impact "0.0000"` and `p "0.000"`.

**Bot-written jsonb (additive keys, read by later consumers):**
- `decisions.market_state.context` = `{ts, articles_24h, articles_z, tone_mean_24h, tone_z, countries_24h, publishers_24h, context_version}` or null;
- `decisions.market_state.calendar` = `{next_earnings: {scheduled_date, time_hint} | null, next_macro: {title, scheduled_at} | null}` (earnings within 30 days, economic events within 7 days);
- `decisions.policy_result.discovery` (and `context_z`);
- `bot_runs.counts.by_discovery`.

The web ignores these keys (its readers drop unknown keys).

**Outbound calls (bot):**
- **GDELT:** files only, never the DOC API, on `https://data.gdeltproject.org` only. User-Agent `Tidewatch/<version>`, no contact.
- **Finnhub:** `GET https://finnhub.io/api/v1/calendar/earnings` to the pinned host, with `FINNHUB_API_KEY` passed by configuration name (the key value is never logged).

## Components

**Web (`tidewatch-web`; Angular 22).** No new component, token, colour, icon or motion. Design authority is `DESIGN.md`; there was no mockup.
- **`feat-bots/editor/editor-schedule.ts` (the Bots version editor's Schedule group).**
  - Two full-width rows sit after the wake times and before *Manager checks*. Each is a `.field` with a `.switch` (`button[role="switch"][aria-checked]`) named by its words, and, while on, a native number input:
    - *Also propose on coverage anomalies*, with *Z-score at least* (`z_min`, 0.5–10, step 0.1);
    - *Also propose before earnings*, with *Within N sessions* (`sessions_ahead`, 1–20, step 1).
  - The switch sits on the row-label line; the number appears on a second line, indented 46 px, max 160 px.
  - A refusal under `…discovery.context` or `…discovery.calendar` is drawn under its row. `aria-invalid` and `aria-describedby` go to the number when the refusal names it, else to the switch. Focus follows `data-field`.
  - The words live in `feat-bots/util/bot-draft.ts`.
- **`feat-bots/util/bot-draft.ts` (the draft model, SC-W-2..4).**
  - `serialiseDraft` drops `discovery` when both rows are off.
  - An off row saves its number as loaded (the contract default `"2.0"` or `"5"` when the version had none), so a hidden number is never refused and off-then-on leaves nothing to save.
  - A stored both-off `discovery` reads as unchanged (`sameConfig`), so opening it offers no *Save*.
- **`data/bot-config.model.ts` (the v2 vocabulary leaf).**
  - It exports `DISCOVERY_KEYS`, `DISCOVERY_CONTEXT_KEYS`, `DISCOVERY_CALENDAR_KEYS`, `DISCOVERY_Z_MIN {min "0.5", max "10", default "2.0"}` and `DISCOVERY_SESSIONS_AHEAD {min "1", max "20", default "5"}`, plus the validator, reader and faithful writer (`writeBotConfigV2` emits `discovery` exactly when the typed config holds it).
  - `BOT_CONFIG_VOCABULARIES` is not extended.
- **`src/styles/components/bots.css`.** A ≤ 600 px `scroll-margin-top: 124px` on `.bot-detail .editor [data-field]` keeps a focused field clear of the sticky strip (PV2 finding B1, fix 2).
- **Signals page: no product change** (intent non-goal; SC-W-8, OQ-3 accepted as shipped).
  - A coverage signal renders through the existing table and detail:
    - headline, *Media trust*, ◆ Neutral 1.000, an impact bar at 0.0000;
    - detail *Other · severity x.xx / 5*, *GDELT Project · headline only*, *Named in the document*;
    - no *Key facts*, no rationale and no source link;
    - *System 1 · context.v1*, Extraction *context.v1*.
  - No dashes are drawn for the absent triage and extraction (the PRD text said "dashes"; the owner accepted the shipped rendering).
  - The row is listed only at *Impact ≥ 0.00*. At the default 0.30 it is counted in the "N more under Impact ≥ 0.30" note.
  - The Source chips gain one *GDELT Project* chip and reuse *Finnhub*.
- **Bots *Sources and weights*.** After N the editor shows three more rows by raw code (`SOURCE_NAMES` has no entry for them; OQ-1).
- **Docs.** `CLAUDE.md` and `DESIGN.md` record the rows, the sibling pin and SC-W-4..6. The DESIGN.md "Verification evidence" entry is "Signals context (spec 3b)".

**Service (`tidewatch-service`).** `botconfig.go` gained the optional key's validation only. No handler, repository or route changed.

**Bot.** No UI. The runtime pieces are in Concept: the GDELT collector, the `context` package and runner, and the scout paths.

## Files touched

> **Provenance.** Each list is `git diff --name-status <merge>^1 <merge>` of the PR's merge commit on `main`: exactly what the PR changed against `main` as it stood at merge time (so after L and M). (new) marks an added file; everything else was modified. No file was deleted.

**tidewatch-migrations** (migrations#15, merge `89669e8`, worktree `b7ddc75378`): 5 files, 2 new.
- (root): `CLAUDE.md`, `README.md`
- `migrations/`: `20261028120200_signals_context.sql` (new)
- `scripts/`: `check-disposable-db.sh`, `check-gkg-themes.sh` (new)

**tidewatch-service** (service#17, merge `ef9e93e`, worktree `329891b601`): 18 files, 3 new.
- `.plans/`: `signals-context.md` (new)
- (root): `CLAUDE.md`, `README.md`
- `internal/repository/postgres/`: `settings_test.go`
- `internal/trading/`: `botconfig.go`, `botconfig_discovery_test.go` (new)
- `internal/trading/testdata/`: `bot-version.v2-discovery.json` (new)
- `scripts/`: `integration-test.sh`
- `test/integration/`: `attribution_compat_test.go`, `bot_versions_test.go`, `bots_caps_test.go`, `compat_slice7_test.go`, `entitlements_test.go`, `learning_fixtures_test.go`, `redaction_test.go`, `signals_fixtures_test.go`, `signals_test.go`, `stats_test.go`

**tidewatch-bot** (bot#18, merge `b083697`, worktree `6945fd5d6c`): 158 files, 74 new.
- (root): `.env.example`, `CLAUDE.md`, `Dockerfile`, `README.md`, `pnpm-lock.yaml`, `tsconfig.json`
- `.plans/`: `signals-context.md` (new)
- `packages/bots/fixtures/`: `README.md`, `bot-version.v2-discovery.json` (new)
- `packages/bots/`: `package.json`, `tsconfig.lib.json`
- `packages/bots/src/`: `bot-version-v2-discovery-fixture.spec.ts` (new), `general.int.spec.ts`, `pg-store.int.spec.ts`, `pg-store.spec.ts` (new), `pg-store.ts`, `runner.spec.ts`, `runner.ts`, `store.ts`, `vocabulary.spec.ts`, `vocabulary.ts`
- `packages/bots/src/general/`: `manager.spec.ts`, `models.spec.ts`, `models.ts`, `pass.spec.ts`, `pass.ts`, `scheduler.spec.ts`, `scout.spec.ts`, `scout.ts`, `sessions.spec.ts`, `sessions.ts`
- `packages/bots/src/learning/`: `learning.int.spec.ts`, `pg-store.ts`
- `packages/bots/src/testing/`: `memory-store.spec.ts`, `memory-store.ts`
- `packages/context/`: `README.md` (new), `VERIFICATION.md` (new), `package.json` (new), `tsconfig.json` (new), `tsconfig.lib.json` (new), `tsconfig.spec.json` (new), `vitest.config.mts` (new), `vitest.int.config.mts` (new)
- `packages/context/fixtures/`: `README.md` (new)
- `packages/context/fixtures/finnhub/`: `earnings-calendar.json` (new)
- `packages/context/src/`: `calendar.spec.ts` (new), `calendar.ts` (new), `constants.ts` (new), `context.int.spec.ts` (new), `coverage.spec.ts` (new), `coverage.ts` (new), `features.spec.ts` (new), `features.ts` (new), `index.ts` (new), `logs.spec.ts` (new), `logs.ts` (new), `metrics.spec.ts` (new), `metrics.ts` (new), `no-network-guard.spec.ts` (new), `pg-store.ts` (new), `publish.spec.ts` (new), `read-model.spec.ts` (new), `read-model.ts` (new), `runner.spec.ts` (new), `runner.ts` (new), `scans.spec.ts` (new), `store.ts` (new), `telemetry-union.spec.ts` (new)
- `packages/context/src/testing/`: `index.ts` (new), `memory-store.ts` (new)
- `packages/ingest/docs/`: `gdelt-gkg-layout.md` (new)
- `packages/ingest/fixtures/`: `README.md`
- `packages/ingest/fixtures/gdelt/`: `20261027181500.translation.split-rows.excerpt.txt` (new), `20261028030000.translation.gkg.csv.zip.b64` (new), `20261028031500.gkg.csv.zip.b64` (new), `20261028031500.translation.gkg.csv.zip.b64` (new), `20261028033000.gkg.csv.zip.b64` (new), `LOOKUP-GKGTHEMES.excerpt.txt` (new), `lastupdate-translation.txt` (new), `lastupdate.txt` (new), `masterfilelist-short.txt` (new), `masterfilelist-tail.txt` (new), `masterfilelist-translation-tail.txt` (new)
- `packages/ingest/src/`: `cik-refresh.ts`, `gdelt.int.spec.ts` (new), `index.ts`, `jobs.spec.ts`, `jobs.ts`, `logs.spec.ts`, `logs.ts`, `metrics.spec.ts`, `metrics.ts`, `no-direct-network.spec.ts`, `pg-store.int.spec.ts`, `pg-store.ts`, `registry.spec.ts`, `registry.ts`, `runner.int.spec.ts`, `runner.spec.ts`, `runner.ts`, `sources.spec.ts`, `sources.ts`, `store.ts`
- `packages/ingest/src/collectors/`: `api.ts`, `finnhub-budget.ts` (new), `finnhub.spec.ts`, `finnhub.ts`
- `packages/ingest/src/collectors/gdelt/`: `collector.spec.ts` (new), `collector.ts` (new), `commit-rows.spec.ts` (new), `commit-rows.ts` (new), `fixtures.spec.ts` (new), `gate.spec.ts` (new), `gate.ts` (new), `manifest.spec.ts` (new), `manifest.ts` (new), `match.spec.ts` (new), `match.ts` (new), `notifier.ts` (new), `parse.spec.ts` (new), `parse.ts` (new), `stamps.spec.ts` (new), `stamps.ts` (new), `telemetry.ts` (new), `types.ts` (new)
- `packages/ingest/src/testing/`: `index.ts`, `memory-store.spec.ts`, `memory-store.ts`
- `packages/market-data/src/`: `index.ts`
- `packages/market-data/src/transport/`: `http.spec.ts`, `stream-zip.spec.ts` (new), `stream-zip.ts` (new), `user-agents.spec.ts`, `user-agents.ts`
- `packages/shared/src/`: `config.spec.ts`, `config.ts`
- `packages/signals/src/`: `index.ts`, `pg-store.int.spec.ts`, `pg-store.ts`, `pipeline.int.spec.ts`, `pipeline.spec.ts`, `prompt-versions.spec.ts`, `prompt-versions.ts`, `runner.spec.ts`, `runners.int.spec.ts`, `thesis.spec.ts`, `thesis.ts`, `verification-queries.int.spec.ts`
- `packages/signals/src/prompts/`: `bot-thesis.v2.ts` (new), `prompts.spec.ts`, `versions.ts`
- `packages/signals/src/testing/`: `memory-store.ts`
- `packages/worker/`: `package.json`, `tsconfig.lib.json`
- `packages/worker/src/`: `run.ts`, `serve.spec.ts`, `serve.ts`
- `scripts/`: `sql-integration.sh`

**tidewatch-web** (web#22, merge `9dc59cf`, worktree `5eb4e5c7ea`): 19 files, 3 new.
- `.plans/`: `signals-context.md` (new)
- (root): `CLAUDE.md`, `DESIGN.md`
- `e2e/src/`: `bots-editor.spec.ts`, `signals.spec.ts`
- `e2e/src/support/`: `bots.ts`, `signals.ts`
- `src/app/pages/workspace/data/`: `bot-config.model.spec.ts`, `bot-config.model.ts`, `signals.model.spec.ts`
- `src/app/pages/workspace/data/testdata/`: `README.md` (new), `bot-version.v2-discovery.json` (new)
- `src/app/pages/workspace/feat-bots/editor/`: `editor-schedule.spec.ts`, `editor-schedule.ts`
- `src/app/pages/workspace/feat-bots/util/`: `bot-draft.spec.ts`, `bot-draft.ts`
- `src/app/pages/workspace/feat-signals/`: `signal-detail.spec.ts`, `signals-table.spec.ts`
- `src/styles/components/`: `bots.css`

**Not changed (dispositions).**
- **`tidewatch-specs` and `tidewatch-apis` are not git repositories.** The specs are unchanged, and API-collection regeneration was skipped (`includeApiCollections: false`). The API surface did change: the optional `schedule.scout.discovery` config key, the three `/sources` rows, and coverage signals on the signals routes. Their `origin` is not exposed (see API).
- **`tidewatch-kubernetes`** was not touched: adding `context` to the production bot chart's collectors value is an owner action.
- **`documents/`** was not touched (D17).

## Test plan

**Executable checks** (each repo's convention; integration specs only through the harnesses):
- **Migrations:** `make migrate-validate`; `make check-disposable-db` (exact lists, N's assert/absent functions, down round trips).
- **Bot:** `pnpm nx run-many -t lint test typecheck build`, then `TIDEWATCH_MIGRATIONS_DIR=<migrations checkout> bash scripts/sql-integration.sh` (needs L, M and N applied; writes `tmp/vitest-int-context.json` beside the others). Spec titles are exact strings checked by `scripts/assert-vitest-titles.mjs`. Key titles:
  - **Ingest:** `gdelt: two streams advance their own cursors`, `gdelt: digest is the stream's own`, `gdelt: quarantine ratio has a 100-row floor`, `gdelt: confirms a gap from the manifest tail`, `gdelt: first run settles without fetching`, `gdelt: resolves organisations to subjects`, `gdelt: keep gate reads rules as data`, `stream-zip: inflates one entry under the caps`, `stream-zip: refuses past the caps`, `no-direct-network: only fetch.ts and stream-zip read bodies`, `http: keeps Range across redirects`, `ingest: stale gauge covers thirteen sources`, `source-backfill: gdelt is bounded to a day`; int `gdelt: a rule change changes the next run`, `gdelt: a window adds nothing to the ledger`.
  - **Context:** `context: computes features against the fixture baseline`, `context: writes a coverage signal with the context values`, `context: publishes C-SIG-1 after commit`, `context: class rows have no signal`, `context: keeps at most 64 pending window notices`, `context: window and context telemetry are the eight events and six metrics`; int `context: one coverage signal per instrument per Bangkok day`, `context: features upsert on the database`.
  - **Calendar:** `calendar: refresh replaces the range`, `calendar: missing key is a noop`, `calendar: a failed fetch keeps rows`, `calendar: a failed refresh retries hourly`, `calendar: warns per series 60 days before its last seeded row`, `calendar: BoT warns from the first day while FOMC does not`, `finnhub: company news and the earnings refresh share one budget`, `registry: calendar source is owned by context`.
  - **Bots:** `vocabulary: discovery is optional and hashed when present`, `scout: context-driven qualification`, `scout: calendar-driven qualification`, `scout: context signals never qualify`, `scheduler: context signals never wake`, `manager: context signals are not events`, `scout: caps discovery paths before model calls`, `scout: decision context carries context and calendar`, `scout: manual run on off runs non-signal paths`, `prompt versions: bot_thesis.v2 is recorded beside v1`, `signals: novelty ignores coverage signals`; int `pg-store: context signals are not read as triggers`, `scout: discovery paths on the database`. FR-SC-BOT-007 is checked by `check-base-titles.mjs`: 336 base titles in 39 files kept.
  - **Hardening evidence:** `evidence/tidewatch-bot/S17/bomb-*.json`, `S18/rope-*.json`, `S18/retain-*.json`, `S19/window-*.json`, `S19/row-bound.json`.
- **Service:** `make ci`, then `make test-integration TIDEWATCH_MIGRATIONS_DIR=<checkout>`. Named evidence tests (do not rename):
  - unit: `TestBotConfig_Discovery` (41 subtests), `TestBotVersion_V2DiscoveryFixtureHash`, `TestBotConfig_UpgradeTranslation_NoDiscovery`;
  - integration: `TestSources_ListsContextSources`, `TestSignals_Detail_ContextOrigin`, `TestBots_Upgrade_NoDiscovery`, `TestBotVersions_Discovery`, `TestContract_RequiredSchemaVersion`.
- **Web:** `pnpm nx test tidewatch-web`, `nx lint`, `nx build`, `nx run e2e:lint`. The Playwright suites run only on a preview (no headless authed run in the worktree):
  - `bots-editor.spec.ts`: the save shapes (both off omits `discovery`; either on sends both sub-objects), refusals beside the control, 390/600 clear-of-strip, the switch focus ring, and the 8 `bots__editor-discovery-…` captures;
  - `signals.spec.ts`: the coverage-signal render with `SIGNAL_FIXTURES_WITH_COVERAGE` and `SOURCES_WITH_CONTEXT`.

**Recorded results (`verification.md`; per-ID evidence under `evidence/`).**
- **Verified (33):** FR-SC-MIG-001, -002; FR-SC-ING-001..011; FR-SC-CTX-001..005; FR-SC-CAL-001..003; FR-SC-BOT-001..008; FR-SC-SVC-001, -002 (the latter under PS4: no `origin`, subject row not rendered); FR-SC-WEB-001 (Chromium only; WebKit/iOS Safari, contrast at 390/600/1080 and touch unverified); FR-SC-WEB-002 (PV3 on the real service, console 0 errors, `evidence/preview/web-002/`).
- **Partial (1):** FR-SC-MIG-003. US CPI and payrolls are not seeded: BLS refused scripted reads.
- **Unverified (5):** FR-SC-E2E-001..005 (see below).
- **Web preview runs** (at `a1f2ed1`, before the merge updates): 1,419 passed, 1 failed, 4 skipped. The one failure is the pre-existing flaky `Signals, mocked › opens Add source and returns focus`, which this build did not touch. PV2 design review APPROVED. PV4 unverified (it needs a paid-model wake).
- **After the main updates:**
  - bot run-many green (1,709 tests) and `sql-integration` PASS with L, M and N;
  - service integration 5,531 PASS, 0 FAIL;
  - web 7,028 unit tests and a production build OK;
  - migrations `check-disposable-db` PASS.
- **Not done after the merge updates:** **the e2e specs were not re-run on the merged tree, and the preview was not refreshed onto L/M.**

**Unverified end-to-end checks and the evidence each needs** (`packages/context/VERIFICATION.md` holds the read-only queries: kept-row ratio, reject reasons, quarantine ratio with its floor, stamp completeness, oldest unsettled stamp, run taxonomy, coverage signals per day, mention spot-check, calendar next events):
- **FR-SC-E2E-001 (24 h soak).**
  - Both GDELT sources fresh throughout; every stamp settled or pending with a reason.
  - Quarantine ratio under 5 % on files of 100 rows or more; `model_spend_daily` unchanged by GDELT; feature rows written.
  - `context_window_lag_seconds` under 1,200 s at the end.
  - Exactly one `context_calendar_expiring` `bot_mpc` warning per Bangkok day.
  - In production this needs `context` in the collectors value first.
- **FR-SC-E2E-002 (live rule flip).** Two consecutive `source_runs` rows' `counts.kept`, before and after one `UPDATE theme_rules SET is_active = …`, with no restart in the logs. Only the int spec covers it today.
- **FR-SC-E2E-003 (preview wake).** A version with both paths on, a seeded feature row above `z_min` and an earnings row in range. The next wake's `bot_runs`, `candidates` and `decisions` rows should show one context and one calendar candidate with `discovery` recorded, and no order. Not run, because it would call the paid model router on the owner's key. Partial support: a coverage signal reached the preview DB and Redis through the bot's own code, and the editor saves and reads both rows.
- **FR-SC-E2E-004 (owner spot check, A3).** Of 50 kept mentions from one real window, at most 5 name the wrong company. If over, tighten `ambiguous_names` or the gate themes as data.
- **FR-SC-E2E-005 (live Finnhub, A1).** One live earnings refresh with the owner's key: the `source_runs` row and `event_calendar` counts, or the recorded "unavailable on this plan" refusal. The preview's start-up refresh ran once on a fresh DB, but the owner's acceptance is not recorded.

## Open questions

**Owner actions and follow-ups (from `verification.md` and `state.json`):**
- **Production collectors.** Add `context` to the production bot chart's collectors value (`tidewatch-kubernetes`, owner-only). Until then the context runner does not run in production: no features, coverage signals or calendar refresh. Per the bot docs, ingest still stores GDELT mentions while `context` is disabled, if the collectors value lists `ingest`.
- **BLS seed data migration.** US CPI and US payrolls rows, which completes FR-SC-MIG-003. Until then the `us_cpi` and `us_payrolls` series cannot warn.
- **2027 BoT MPC schedule.** A new migration once it is published. Until then BoT warns once per Bangkok day.
- **`md5_ok` on mention-cap refusals.** A `mention_count` or `mention_bytes` refusal note could compute `md5_ok` (review r3 nit 2, extended at r4).
- **A metric for dropped context notices.** A notice past 64 pending is dropped silently, and the 60 s sweep computes its window. Visibility needs a label on an existing context metric through a PRD change, because the event set is closed at five.
- **A `theme_rules` shape check where rules are written.** A future row off `^[A-Z0-9_]{1,128}$` can never match, and nothing warns. Every N seed matches.
- **`draft_modified` on an unedited learned draft.** It reads true for a learned draft fitted from a pre-N version: the draft lists 10 sources and the web saves 13. Either the bot's draft writer should list all live sources at weight 0, or the service should ignore added zero-weight rows.
- **The web testdata README has no C15 row** (`src/app/pages/workspace/data/testdata/README.md`).
- **Refresh the preview onto L/M and re-run the e2e specs on the merged tree.**
- Then FR-SC-E2E-001..005 as listed in the Test plan.

**Soak watch items (review r4):**
- **URL quarantine count.** Since S15 a URL that GDELT splits with a raw newline is quarantined (field `url`) instead of stored with a space. None of 4,737 real URLs had one.
- **`mention_bytes` and `mention_count` refusals.** The real busiest window was 0.70 of 16 MiB.
- **Sweep gap.** A window inserted earlier but committed after the sweep moved past a later uuidv7 `file_id` is skipped until a restart's 24 h lookback. Since S19 this also needs a dropped notice. It affects data completeness only.

**Smaller recorded follow-ups (`state.json` `followUps`, review nits):**
- **Web:**
  - PV2 R1: a ~148 px scroll margin so the label shows at 390;
  - PV2 R2: a shared strip-height custom property instead of the hand-derived 124 px;
  - PV2 R3: verify the scroll margin on WebKit / iOS Safari;
  - PV2 R4: an app-wide `scroll-padding-top` at ≤ 600;
  - design A2 (double announcement), A3 (focus fallback for a hidden-number refusal), A4 ("Within N sessions" wording);
  - a whole-object discovery refusal focuses a switch with no `aria-describedby`;
  - the pre-existing flaky *Add source* focus test.
- **Bot:**
  - assert `newsPerMinute` in the calendar int spec, and fall back to `FINNHUB_CALLS_PER_MINUTE` on a broken news config;
  - export `STREAM_ZIP_PART_BYTES` / `STREAM_MAX_LINES` and drop the `STREAM_ZIP_CHUNK_BYTES` alias;
  - export the coverage URL prefix from `packages/context` and drop the duplicate in `bots`;
  - fix the `gdelt-gkg-layout.md:178` wording;
  - GC before the baseline in `retain-bound.mjs`;
  - reflow the 91-column doc comment in `collector.ts`.
- **Service** (optional): a full wrong-type matrix subtest (security L1); more absent strings in `TestSignals_Detail_ContextOrigin` (L2); the `wholeIn` / `wholeAtMost` duplication.

**Assumptions still open (intent A1–A3, PRD A4–A5):**
- **A1:** whether Finnhub `/calendar/earnings` is on the owner's free tier (E2E-005). If it is not, the refresh fails permanently once a day and the economic rows still load.
- **A2:** GDELT tolerance for two streams every 5 minutes plus backfills. One 392-request floor was observed with no refusals; the soak should confirm it.
- **A3:** the false-match rate (E2E-004).
- **Coverage-signal display.** Exposing `origin` and rendering context rows wait for the "what the bot sees" view, which is the next consumer, along with slice 8's use of `market_state.context` / `.calendar`.

## Cross-cutting links

- [[source-registry-and-ingest]]: thirteen `sources` rows, the GDELT registry family, the calendar source owned by `context`.
- [[signals-ingest]] and [[signals-pipeline]]: the synthetic document at `stage = signalled`, `LATEST_SIGNAL` origin filter, C-SIG-1 publish after commit.
- [[signal-message-contract]]: C-SIG-1 unchanged; coverage signals are ordinary messages.
- [[signals-read-api]] and [[signals-page]]: `GET /sources` rows, the coverage signal's detail and its rendering, `origin` not exposed.
- [[bots-engine]], [[bots]] and [[bot-versions-and-runs]]: optional `schedule.scout.discovery`, the C12 sibling fixture, `by_discovery`, `bot_thesis.v2`.
- [[decision-record]]: `market_state.context`, `market_state.calendar`, `policy_result.discovery`.
- [[instrument-master]]: `name` aliases for matching, `ticker` aliases on `webull` for earnings.
- [[centralized-migrations]] and [[market-timeseries]]: migration N, goose order K, L, M, N, hypertable and policy conventions.
- [[model-routes-and-spend]]: zero spend from GDELT; the shared Finnhub budget.
- [[market-data-worker]]: the fifteenth runner, the streaming zip reader in the transport.
- [[design-system-decisions]]: SC-W-4..6, the discovery rows in the Schedule group.
- [[accounts-and-roles]]: the sibling migration L and the merge order.
