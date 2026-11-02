# Signals context (`signals-context`, spec 3b)

**Summary**: Slice 3a shipped primary sources only. Spec 3b builds the deferred context layer and the event calendar, and fills the two scout discovery paths slice 6 kept reserved (bots D10). It has five parts:
- **GDELT GKG 2.1 ingest.** Two streams every 5 minutes, with no model call per article. A keep gate whose rules are database rows decides what is stored.
- **Context features.** Per instrument and 15-minute window, trailing-24 h coverage is compared against a 30-day baseline.
- **Coverage signals.** `media` signals with `origin = 'context'` and `impact 0.0000`. They **never trigger** anything.
- **An event calendar.** US earnings from Finnhub, plus seeded FOMC and BoT MPC rows.
- **Two optional scout discovery paths** under `schedule.scout.discovery`. They are off when the key is absent.

Migration N (`20261028120200`, which the PRD calls "L") is additive. Goose order is K, L, M, N. **The required schema version is M, and N is never pinned.** All four PRs merged on 2026-10-30 (migrations#15, service#17, bot#18, web#22). In production the service is verified live on `ef9e93e`. The bot and web deploys were triggered but not verified, and the production bot chart does not yet list `context` in its collectors value, so **the context runner is not running in production**. Of 39 acceptance IDs, 33 are verified, FR-SC-MIG-003 is partial (no BLS seeds) and FR-SC-E2E-001..005 are unverified.

**Sources**: `raw/2026-10-30-signals-context.md`

**Last updated**: 2026-10-31

---

## Stage, stated precisely

| Stage | Status |
|---|---|
| Planned | Bot S1–S19 plus a wrap-up docs step, approved at plan revision r17. Bot S1–S2 also edited the companion migrations worktree (ORCH-1). Service S1–S3 (r4). Web S1–S6 (r3). Migrations had no plan of its own; N and its harness were planned and verified as bot S1–S2. |
| Reviewed | Bot code and security approved at r4, after three rounds of changes. Service r1 approved. Web approved at r2, after all four reviewers asked for changes at r1. See "Review history" below. |
| Updated onto `main` | `main` was merged into every branch twice, after L and after M, with no rebase or force-push (ORCH-5). |
| Merged | **Yes**, 2026-10-30, all four PRs, by Claude on the owner's instruction, in the order migrations → service → bot and web. |
| Deployed | **Service: verified live.** It runs `ef9e93e`; `/info` was confirmed and `/ready` answered 200 at about 19:56Z. N reached production through the service's sync. **Bot and web: deploy triggered, not verified.** |
| Running in production | **The context runner is not running.** The production bot chart's collectors value does not list `context`. Until the owner adds it, there are no context features, coverage signals or calendar refreshes. The discovery paths stay off for every bot until a version sets `schedule.scout.discovery`. |
| Verified | 33 of 39 PRD acceptance IDs verified, FR-SC-MIG-003 partial, FR-SC-E2E-001..005 unverified. The preview was not refreshed onto L and M after the `main` updates, and the web e2e specs were not re-run on the merged tree. |

(source: raw/2026-10-30-signals-context.md, summary block; §Sources; §Test plan, Recorded results)

## Merge record

| Repo | PR | Merge commit |
|---|---|---|
| tidewatch-migrations | #15 | `89669e8` (19:40:46Z) |
| tidewatch-service | #17 | `ef9e93e` (19:42:58Z) |
| tidewatch-bot | #18 | `b083697` (19:57:23Z) |
| tidewatch-web | #22 | `9dc59cf` (19:57:29Z) |

The bot PR is a single squashed commit (`2de076b` on base `87495d5`), plus the CI timeout fix `5a75c1d` and the two main-merge commits. An earlier local commit held unredacted fixture blobs (personal email addresses in GKG excerpts, finding SEC-I2). The fixtures were redacted in S17, and the branch was squashed before its first push. So that commit was never pushed, and no remote ref contains it (source: raw/2026-10-30-signals-context.md, summary block; §Concept, Review history).

## Why the feature exists

The brain read filings, wires, exchange notices, Binance TH listings and Finnhub headlines, but it had **no media context and no calendar**:
- the scout could propose only on signals and chart setups;
- slice 8's meta-model had no context inputs;
- the owner wanted coverage and tone anomalies and upcoming earnings noticed, without a model call per article and inside the $1/day ceiling, with every rule and threshold a row that changes without a deploy.

Slice 3a's D1 had already named GDELT as a context layer for spec 3b, with the slice-6 scout as its consumer (see [[signals-ingest]]) (source: raw/2026-10-30-signals-context.md §Concept, The problem).

## Chosen design (intent D1–D7)

- **D1. A coverage anomaly is a `media` signal with a synthetic document.** It has `origin = 'context'`, `impact = 0`, `conviction = 0`, `p_neutral = 1`, `event_type = other` and model ids `context.v1`. Its direction is `neutral` unless the tone z also crosses. Two alternatives were rejected: no `signals` row until the "what the bot sees" view, and a real impact so the signal path could act. This choice is both "surfaced as media signals" and "not a trigger". The title carries the summary, so the web needs no change. See [[context-features-and-coverage-signals]].
- **D2. Two optional keys in `bot-config.v2`, absent means off, with web toggles.** A `bot-config.v3`, or running the paths for every scout, were rejected, so existing versions keep their hash and behaviour. See [[bots-engine]] and [[bot-versions-and-runs]].
- **D3. Grain.** One `context_features` row per subject per 15-minute window in which the subject was mentioned: trailing-24 h counts against a 30-UTC-day baseline. Class rows (`class:gold`, `class:crypto`) are recorded but never used for discovery.
- **D4. Keep gate.** A row is kept on a gate theme AND an active instrument (or a class tag), unless its publisher domain is denied. Only matched rows are kept: rejected rows would cost about a million rows a day, and a window can be re-ingested from GDELT's archive under new rules. See [[gdelt-gkg-ingest]].
- **D5. Earnings from Finnhub for US instruments; economic events as seeded yearly rows**, in one `event_calendar` table. No manager gate on macro events in 3b. See [[event-calendar]].
- **D6. Both streams from day one, no automatic backfill.** No anomaly before 7 baseline days (`min_baseline_days`), full strength at 30. A bounded owner-run backfill exists.
- **D7. Thresholds and constants live in `context_versions`, stamped on outputs.** The migration is additive, and the service pin does not move for it.

**Non-goals kept:** any model call per GDELT article, the GDELT DOC 2.0 API, a `coverage` event type, any Signals page change, a sector column, class-level discovery, Thai earnings, and a paid economic calendar.

(source: raw/2026-10-30-signals-context.md §Concept, The approach, by owner decision (intent D1–D7))

## What each project gained

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-migrations` | Migration N `20261028120200` (`signals_context`): three `sources` rows, `context_versions`, `theme_rules`, `domain_rules`, `gkg_mentions`, `context_features`, `event_calendar`, and `signals.origin`. Seeds: 37 themes, 9 deny domains, 11 economic rows. Harness lists and `scripts/check-gkg-themes.sh` | [[centralized-migrations]] |
| `tidewatch-bot` | The GDELT collector family in `packages/ingest`, the new `packages/context` and its `context` runner (the 15th collector), the scout's context and calendar paths, `bot_thesis.v2`, the streaming zip reader `transport/stream-zip.ts`, and the shared Finnhub budget. 158 files, 74 new | [[gdelt-gkg-ingest]], [[context-features-and-coverage-signals]], [[event-calendar]], [[bots-engine]], [[market-data-worker]] |
| `tidewatch-service` | Validation of the optional `schedule.scout.discovery` key in `botconfig.go` and the shared contract fixture. No handler, repository or route changed, and no pin moved | [[bot-versions-and-runs]], [[signals-read-api]] |
| `tidewatch-web` | Two discovery rows in the Bots version editor's Schedule group, the draft and vocabulary model, and a ≤ 600 px scroll margin. No Signals page change | [[design-system-decisions]], [[bots]] |

**Not changed.** `tidewatch-kubernetes` was not touched: adding `context` to the production bot chart's collectors value is an owner action. `tidewatch-specs` and `tidewatch-apis` are not git repositories; API-collection regeneration was skipped. `documents/` was not touched (D17) (source: raw/2026-10-30-signals-context.md §Files touched; §Components).

## What the user sees

- **Bots → version editor → Schedule.** Two new switch rows: *Also propose on coverage anomalies* (with *Z-score at least*) and *Also propose before earnings* (with *Within N sessions*). See [[design-system-decisions]].
- **Bots → *Sources and weights*.** Three more rows, shown by raw code (`finnhub-earnings-calendar`, `gdelt-gkg-en`, `gdelt-gkg-translation`), because `SOURCE_NAMES` has no entry for them (owner ruling WEB-OQ-1).
- **Signals.** A coverage signal renders through the existing table and detail, with no product change. It is listed only at *Impact ≥ 0.00*, and the Source chips gain one *GDELT Project* chip. See [[signals-page]].
- **Nothing shows `origin`.** Exposing it waits for the "what the bot sees" view.

(source: raw/2026-10-30-signals-context.md §Components)

## Decisions during the build

- **Migration letter N (ORCH-2).** Two sibling builds started at the same time and own L ([[accounts-and-roles]]) and M ([[learning-loop]]). So this feature's migration is N, and it merged after them (ORCH-5). The PRD calls it "L".
- **Pins.** This build never moved a pin. At build time the service's `RequiredSchemaVersion` and the migrations harness `required_migration` were J; the sibling builds moved them to L and then M. Only the bot's SQL harness requires N.
- **The migration was planned inside the bot plan (ORCH-1),** in a companion worktree with its own PR, because the bot is N's only writer and its harness pin is the one that moves.
- **Cross-project vocabulary (ORCH-3).** The bot plan's `contracts.md` r1 pinned the `discovery` key set, bounds and defaults, every refusal's field and reason, and the bytes of `bot-version.v2-discovery.json`. The service and web planned against that revision.
- **Service release note** (accepted 2026-10-28). After N, an API client re-posting a pre-N bot config gets `400 config.source_weights missing` instead of `409`, because N adds three `sources` rows the config must weigh. The web's forward rule (weight `"0"` for unlisted sources) is unaffected.
- **Owner rulings (2026-10-28):**
  - BOT-Q1, "Retry only": one pinned BLS retry, then FOMC and BoT only;
  - BOT-Q2, "Per series" (the calendar renewal warning; see [[event-calendar]]);
  - **SVC-Q1: no API change for the coverage signal's detail body**, so `origin` is stored but not exposed;
  - WEB-OQ-1: raw source codes stay in *Sources and weights*;
  - WEB-OQ-2: keep the `DESIGN.md` snapshot refresh;
  - WEB-OQ-3: accept the shipped Signals rendering;
  - execution in lanes.
- **BLS pages.** The parent relayed that the owner would save the BLS pages to `inputs/`. The folder stayed empty, so FR-SC-MIG-003 stays partial.
- **Real-data fix S15 (finding GDELT-NL).** Rows split by raw newlines were fixed in the parser, not with a deny-list entry. See [[gdelt-gkg-ingest]].

(source: raw/2026-10-30-signals-context.md §Concept, Build-time decisions worth keeping)

## Review history (abridged)

- **Plans.** Bot: 17 revisions (r1, r6, r11 and r16 had CHANGES REQUESTED), approved at r17. Service: approved at r4. Web: approved at r3.
- **Bot code and security.**
  - r1 CHANGES REQUESTED: the `LATEST_SIGNAL` novelty read lacked the origin filter, and a newline-dense zip could exhaust the heap. Fixed in S17.
  - r2 security CHANGES REQUESTED: a tiny-chunk partial-line rope, mention fan-out and row pinning, and record-id length. Fixed in S18.
  - r3 security CHANGES REQUESTED: per-mention size was unbounded (290 MiB retained, 552 MiB commit peak from a 516 KB zip). Fixed in S19.
  - r4: code APPROVED (4 nits), security APPROVED (4 low follow-ups).
- **Service.** r1 code and security APPROVED.
- **Web.** At r1 all four reviewers asked for changes, on the preview-evidence gate and a switch-alignment design issue. At r2 all approved, after fix 1 and fix 2 (390 px focus under the sticky strip), with design approved at the PV2 re-check.

The bounds the security rounds added are on [[gdelt-gkg-ingest]] (source: raw/2026-10-30-signals-context.md §Concept, Review history).

## Merge updates (ORCH-5)

The branches waited until the sibling builds merged. Then `main` was merged into each branch twice:
- **After L merged** (2026-10-30T04:12Z): migrations `988a334`, service `78c449a`, bot `a4eb5f8`, web `97a0f8a`. Service saves in `entitlements_test.go` and `bots_caps_test.go` were wrapped in `withLiveSources`, and the web kept both sides of `DESIGN.md`.
- **After M merged:** migrations `59f57ae` (18:02Z); service `59a2bdb`, bot `c228874` and web `3ebd65d` (19:40Z, after learning-loop service#16, bot#17 and web#21 merged).
- **Conflict resolutions with [[learning-loop]].**
  - Bot: 15 collectors (`learning` 14th, `context` 15th) and 7 prompt versions. The post-mortem query `LATER_SIGNALS` reads `origin = 'document'` only. `sql-integration.sh` requires N, keeps L's and M's checks, and records the SHA-256 of H, J, L, M and N.
  - Service: `botconfig.go` keeps both `discovery` and `learning`. The `learnedConfig` fixture lists all 13 sources. The stats compat normaliser sets N's three source rows aside (`nRows`), so the slice-7 goldens stay byte-unchanged.
  - Web: the `discovery` and `learning` key sets are both intact, and 5 snapshot hashes were recomputed.
  - Migrations harness: see [[centralized-migrations]].

(source: raw/2026-10-30-signals-context.md §Concept, Merge updates (ORCH-5))

## Test plan and acceptance

**Commands.**
- Migrations: `make migrate-validate` and `make check-disposable-db`.
- Bot: `pnpm nx run-many -t lint test typecheck build`, then `scripts/sql-integration.sh` with L, M and N applied. Spec titles are exact strings checked by `scripts/assert-vitest-titles.mjs`, for example "scout: context signals never qualify", "scheduler: context signals never wake", "context: one coverage signal per instrument per Bangkok day" and "calendar: BoT warns from the first day while FOMC does not". FR-SC-BOT-007 is checked by `check-base-titles.mjs`: 336 base titles in 39 files kept.
- Service: `make ci`, then `make test-integration`. Named tests: `TestBotConfig_Discovery` (41 subtests), `TestBotVersion_V2DiscoveryFixtureHash`, `TestBotConfig_UpgradeTranslation_NoDiscovery`, `TestSources_ListsContextSources`, `TestSignals_Detail_ContextOrigin`, `TestBots_Upgrade_NoDiscovery`, `TestBotVersions_Discovery` and `TestContract_RequiredSchemaVersion`.
- Web: unit, lint, build and `e2e:lint`. The Playwright suites `bots-editor.spec.ts` and `signals.spec.ts` run only on a preview.

(source: raw/2026-10-30-signals-context.md §Test plan, Executable checks)

### Acceptance (`verification.md`)

| IDs | Status | Note |
|---|---|---|
| FR-SC-MIG-001, -002 | Verified | MIG-002 includes each seeded theme checked against GDELT's lookup (`scripts/check-gkg-themes.sh`) |
| FR-SC-MIG-003 | **Partial** | US CPI and payrolls not seeded: BLS refused the scripted reads |
| FR-SC-ING-001..011 | Verified | |
| FR-SC-CTX-001..005 | Verified | |
| FR-SC-CAL-001..003 | Verified | CAL-002 under the owner's "Per series" scope change |
| FR-SC-BOT-001..008 | Verified | BOT-007 by `check-base-titles.mjs` |
| FR-SC-SVC-001, -002 | Verified | SVC-002 under PS4: no `origin`, subject row not rendered |
| FR-SC-WEB-001 | Verified (Chromium only) | WebKit/iOS Safari, contrast at 390/600/1080 and touch unverified |
| FR-SC-WEB-002 | Verified | PV3 on the real service, 0 console errors |
| FR-SC-E2E-001..005 | **Unverified** | See below |

**Web preview runs** (at `a1f2ed1`, before the merge updates): 1,419 passed, 1 failed (the pre-existing flaky `Signals, mocked › opens Add source and returns focus`), 4 skipped. PV2 design review approved. PV4 is unverified, because it needs a paid-model wake.

**After the `main` updates:** bot run-many green (1,709 tests) and `sql-integration` PASS with L, M and N; service integration 5,531 PASS, 0 FAIL; web 7,028 unit tests and a production build OK; migrations `check-disposable-db` PASS. **The e2e specs were not re-run on the merged tree, and the preview was not refreshed onto L/M.**

(source: raw/2026-10-30-signals-context.md §Test plan, Recorded results)

### The unverified end-to-end checks and the evidence each needs

`packages/context/VERIFICATION.md` holds the read-only queries for these.
- **FR-SC-E2E-001 (24 h soak).** Both GDELT sources fresh throughout, every stamp settled or pending with a reason. Quarantine ratio under 5 % on files of 100 rows or more. `model_spend_daily` unchanged by GDELT. Feature rows written. `context_window_lag_seconds` under 1,200 s at the end. Exactly one `bot_mpc` renewal warning per Bangkok day. In production this needs `context` in the collectors value first.
- **FR-SC-E2E-002 (live rule flip).** Two consecutive `source_runs` rows' `counts.kept`, before and after one `UPDATE theme_rules SET is_active = …`, with no restart. Only the integration spec covers it today.
- **FR-SC-E2E-003 (preview wake).** A version with both paths on should get one context and one calendar candidate with `discovery` recorded, and no order. Not run, because it would call the paid model router on the owner's key. Partial support: a coverage signal reached the preview database and Redis through the bot's own code, and the editor saves and reads both rows.
- **FR-SC-E2E-004 (owner spot check, A3).** Of 50 kept mentions from one real window, at most 5 name the wrong company. If over, tighten `ambiguous_names` or the gate themes, as data.
- **FR-SC-E2E-005 (live Finnhub, A1).** One live earnings refresh with the owner's key, or the recorded "unavailable on this plan" refusal. The preview's start-up refresh ran once on a fresh database, but the owner's acceptance is not recorded.

(source: raw/2026-10-30-signals-context.md §Test plan, Unverified end-to-end checks)

## Open items

**Owner actions.**
- **Production collectors.** Add `context` to the production bot chart's collectors value in `tidewatch-kubernetes` (owner-only). Until then, no features, coverage signals or calendar refresh run in production. Per the bot docs, ingest still stores GDELT mentions while `context` is disabled, if the collectors value lists `ingest`.
- **BLS seed data migration** for US CPI and payrolls, which completes FR-SC-MIG-003.
- **2027 BoT MPC schedule**, in a new migration once it is published.
- **Refresh the preview onto L/M and re-run the e2e specs on the merged tree,** then FR-SC-E2E-001..005.

**Open assumptions.** A1, whether Finnhub `/calendar/earnings` is on the owner's free tier. A2, GDELT's tolerance for two streams every 5 minutes plus backfills. A3, the false-match rate.

**Next consumers.** Exposing `origin` and rendering context rows wait for the "what the bot sees" view. Slice 8 is expected to use `market_state.context` and `.calendar`.

**Follow-ups** are listed on the concept pages:
- the collector's on [[gdelt-gkg-ingest]];
- the runner's on [[context-features-and-coverage-signals]];
- the calendar's on [[event-calendar]];
- the web's on [[design-system-decisions]];
- the learned-draft `draft_modified` issue on [[bot-versions-and-runs]].

(source: raw/2026-10-30-signals-context.md §Open questions)

## Related pages

- [[gdelt-gkg-ingest]]: the GDELT collector, the keep gate as data, the bounds and the measured figures
- [[context-features-and-coverage-signals]]: the `context` runner, features, coverage signals and `signals.origin`
- [[event-calendar]]: `event_calendar`, the Finnhub earnings refresh, seeded economic rows and the renewal warning
- [[bots-engine]]: the scout's context and calendar discovery paths
- [[bot-versions-and-runs]]: the optional `schedule.scout.discovery` key and its contract fixture
- [[decision-record]]: `market_state.context`, `market_state.calendar` and `policy_result.discovery`
- [[centralized-migrations]]: migration N, goose order K, L, M, N, and the M pin
- [[source-registry-and-ingest]]: the thirteen `sources` rows
- [[signals-ingest]]: slice 3a, which deferred this context layer to spec 3b
- [[signals-pipeline]]: the synthetic document at `stage = signalled`
- [[signals-read-api]] and [[signals-page]]: how a coverage signal reads and renders, `origin` not exposed
- [[signal-message-contract]]: C-SIG-1 unchanged; coverage signals are ordinary messages
- [[market-data-worker]]: the fifteenth runner and the streaming zip reader
- [[instrument-master]]: `name` aliases for matching, `ticker` aliases for earnings
- [[model-routes-and-spend]]: zero model spend from GDELT; `bot_thesis.v2`
- [[design-system-decisions]]: the discovery rows in the Schedule group
- [[bots]]: slice 6, which reserved these discovery paths
- [[accounts-and-roles]]: the sibling build that owns migration L
- [[learning-loop]]: slice 8, the sibling build that owns migration M and the pin; its post-mortem reads document signals only
