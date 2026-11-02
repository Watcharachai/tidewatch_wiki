# Signals ingest and extract (`signals-ingest`, slice 3a)

**Summary**: Before slice 3a, nothing in Tidewatch read a filing, a press wire or an exchange notice, and the Market watch *Signals* column was a hard-coded dash. Slice 3a builds the pipeline from feed to `signals` row. The bot's new `packages/ingest` reads ten seeded `sources` rows and stores deduplicated `documents`. The new `packages/signals` runs Jev triage, OpenRouter extraction with `anthropic/claude-haiku-5.5`, and Jev scoring per instrument, all under a daily spend ceiling. It commits each surviving (document, instrument) pair as a `signals` row, then publishes it to `sig:<instrument_id>` as the byte-pinned C-SIG-1 message. Migration H (`20261011020408`) adds 18 tables. The service forwards `sig:` on `/ws` as a `signal` frame and adds `signals.today` (the Bangkok day's count) to every Market watch row. The web Signals cell shows that count and raises it live. The four PRs merged on 2026-10-11 on the owner's instruction (ORCH-19). At merge, 30 of the 36 acceptance IDs were verified, 3 were verified with qualifications and 3 were unverified because the 24 h soak had not run. The owner must apply H to their own database; until then the merged service answers `/ready` 503. **Update (2026-10-30):** spec 3b, the GDELT context layer this slice deferred (D1), merged as [[signals-context]].

**Sources**: `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md` (the slice-4 pointers only); `raw/2026-10-14-signals-day-control.md` (history and retention only); `raw/2026-10-30-signals-context.md` (the spec-3b pointer only)

**Last updated**: 2026-10-31

---

## Stage, stated precisely

This is the status in `state.json`, last updated 2026-10-11T14:59:52Z in phase `SOURCING` (source: raw/2026-10-11-signals-ingest.md §Concept, Stage, stated precisely).

| Stage | Status |
|---|---|
| Implemented | All 36 plan steps are committed: service 8 (MIG1–MIG3, S1–S5), bot 24 (S1–S24) and web 4 (S1–S4). Later commits came from review and preview fixes: service `2fec95d`, `b9de179`; migrations `dd7e150`; bot `2b908c6`, `8235f31`, `d64e732`, `8ee0b71` (ORCH-16), `f786102` (ORCH-17), `53cb76d` (ORCH-18); web `534e140`. The workspace-root `docker-compose.yaml` and `.env.example` were edited in place and are in no PR (ORCH-4). |
| Verified locally | Every step's contract commands exited 0 on the orchestrator's re-run, except four superseded step-time checks. Migrations harness 1330 PASS / 0 FAIL. Bot unit tests at `53cb76d`: signals 120, ingest 153, worker 54. The C-SIG-1 three-way `cmp` passed at 2026-10-11T08:14Z. |
| Reviewed | Plans: service r1 approved, plus deltas r2 and r3 after ORCH-8; bot approved at r4 after three rounds of changes; web approved at r2. Code reviews: see Test plan. |
| Verified on a preview | 30 IDs verified, 3 verified with qualifications, 3 pending the 24 h soak, 0 failed. The preview was isolated, with a fresh database at H and 10 sources (8 enabled). It ran with the owner's Jev, OpenRouter and Finnhub keys and no SET key. |
| Merged | **Yes**, 2026-10-11, by the owner by hand, because the session's permission policy blocked the orchestrator's `gh pr merge`. All four PRs were checked OPEN, MERGEABLE and CLEAN at the reviewed heads. The bot merged about one minute before the migrations, against the planned order; nothing deploys automatically. No CI is configured (D4). |
| Running on the owner's own stack | **Not recorded.** H is not applied to the owner's database, so the merged service answers `/ready` 503 until it is. |

## Merge record

| Repo | PR | Range (base..PR head) | Merge commit |
|---|---|---|---|
| tidewatch-bot | #7 | `6b8cdb0..53cb76d` | `0d7be6d` (14:58:10Z) |
| tidewatch-migrations | #7 | `3ec60a7..dd7e150` | `e015a3a` (14:59:06Z) |
| tidewatch-service | #8 | `77d8ebf..b9de179` | `2f9854f` (14:59:11Z) |
| tidewatch-web | #10 | `31f9435..534e140` | `c2a1b26` (14:59:23Z) |

The planned rollout order was H, then service and bot in either order, then web (source: raw/2026-10-11-signals-ingest.md §Concept, Stage, Merged; §Files touched; §Open questions, Rollout and rollback).

## Why the slice exists

The intent checked the gap against `origin/main` on 2026-10-11:

- **No `sources`, `documents` or `signals` table existed.** Nothing read SEC filings, wires or exchange notices.
- **The Signals column was a hard-coded dash on both sides.** The service always sent `signals` as null, and the web hard-coded `signals: null`.
- **The `/ws` hub forwarded only `px:<id>`.** `sig:` appeared nowhere in the service, the bot or the web.
- **`instrument_aliases` was never read** by alias, CIK or ISIN. Only S&P 500 members carried `cik` aliases.

The research brief's strategy (§2.1) has three parts: primary sources, good extraction and a drift horizon. Tidewatch reads 8-Ks, releases and exchange notices within seconds, extracts them well, and trades the window of hours to days. **The language model extracts and never forecasts.** A calibrated probability is the only thing passed between components (source: raw/2026-10-11-signals-ingest.md §Concept, Problem).

## Chosen design (intent D1–D5, confirmed 2026-10-11)

- **D1. Primary sources now; GDELT is spec 3b.** GDELT is a context layer, and its only consumer is the slice-6 scout.
- **D2. OpenRouter for the LLM, with one key and model ids as data.** The model behind every call is a database string, so A/B tests and tier changes are data changes. See [[model-routes-and-spend]].
- **D3. Hybrid: the LLM names, Jev scores.** The LLM reads the document and names instruments, including implied suppliers, customers and peers. Jev supplies every probability. In the owner's probe, Jev reported a genuine 40/37/23 direction split where an LLM would assert a direction. See [[signals-pipeline]].
- **D4. Full text for primary sources, headline-only for media.**
- **D5. Feed text only for every wire** (`config.body_fetch = false`, a seed value). PR Newswire's terms prohibit automated retrieval of its site. Business Wire refuses non-browser clients, and its terms prohibit storing content. A browser User-Agent to get past a refusal was rejected outright. See [[source-registry-and-ingest]].

**Accepted defaults** (proposed defaults the owner confirmed): PD1 Jev direct with `JEV_API_KEY`, pinned to `jev-1.13.0` and never `jev-latest`; PD2 a $1.00 daily ceiling; PD3 materiality thresholds of filing 0.50, exchange 0.50, wire 0.60 and media 0.70, with an `applies` threshold of 0.6; PD4 the impact formula; PD5 `anthropic/claude-haiku-5.5` for extraction; PD6 CIK and alias resolution with a daily CIK refresh; PD7 no mockup, because the existing cell is filled; PD8 two new bot packages; PD9 a labelled set of 100 filings; PD10 a pure-JS PDF extractor.

(source: raw/2026-10-11-signals-ingest.md §Concept, Chosen design)

## What each project gained

| Project | What it gained | Concept page |
|---|---|---|
| `tidewatch-migrations` | Migration H (`20261011020408`): 18 tables, 8 indexes and the seeds (10 sources, scoring version 1, model routes and prices) | [[centralized-migrations]] |
| `tidewatch-bot` | `packages/ingest` and `packages/signals`, the `ingest` and `signals` runners (12th and 13th collectors), four jobs, five new environment variables, the C-SIG-1 builder and `publishSignal` | [[source-registry-and-ingest]], [[signals-pipeline]], [[model-routes-and-spend]], [[market-data-worker]] |
| `tidewatch-service` | `sig:<id>` forwarded on `/ws` as a `signal` frame; `signals.today` on every Market watch row; `RequiredSchemaVersion` moved to H. No new route, error code, log event, environment variable, Redis key or dependency. | [[realtime-websocket]], [[signal-message-contract]], [[market-data]] |
| `tidewatch-web` | The Signals cell shows today's count and counts `signal` frames live. No new component, route, token or icon. | [[design-system-decisions]], [[signal-message-contract]] |
| Workspace root | Five additive `${VAR:-}` lines for `tidewatch-bot` in `docker-compose.yaml` and five `KEY=` lines in `.env.example`, applied in place and in no PR (ORCH-4) | [[market-data-worker]] |

(source: raw/2026-10-11-signals-ingest.md, summary block; §API; §Components; §Files touched)

## What the user sees, and what they don't

- **Overview → Market watch.** The *Signals* column shows today's count (Bangkok day) for each watchlist row and goes up live when a `signal` frame arrives. A count of 0, or no count, keeps the existing dash.
- **No other screen changed.** The `/signals` route still renders the slice-0 empty state ("No signals yet"). The Signals page is slice 4. Signals for instruments that are not on the watchlist are stored and published, but no screen shows them yet. (Slice 4 shipped on 2026-10-12 and shows every signal of the day, watched or not; see [[signals-page]].)
- **Unresolved names are SQL-only.** The review list (`extraction_unresolved`) has no UI.

(source: raw/2026-10-11-signals-ingest.md §Concept, What the user sees)

## Outcomes O1–O7 at merge

| # | Outcome | State at merge |
|---|---|---|
| O1 | The brain has input, unattended | Ingest ran on the preview. EDGAR ×3, GlobeNewswire and PR Newswire succeeded on their first run. The 24 h soak (FR-SIG-E2E-002) is **unverified**. |
| O2 | Calibrated probability, honestly | Every probability comes from Jev. The full direction distribution is stored (`p_up`, `p_down`, `p_neutral`), and model ids and prompt versions are on every row. |
| O3 | Bounded cost that never drops work | The ledger and ceiling were verified (FR-SIG-BRN-008, FR-SIG-E2E-005). Pre-soak spend was $0.641961 by 10:49Z, under $1.00. |
| O4 | Provenance and dedup | Unit and integration specs on H pass. A live two-wire pair (FR-SIG-E2E-003) is **unverified**. |
| O5 | Operator-readable health | `VERIFICATION.md` holds the eight queries, captured once before the soak. The post-soak re-capture (FR-SIG-BRN-012) is **pending**. |
| O6 | Realtime and the count | Service → web was verified live with an injected message. Bot → Redis was shown by 43 real publishes. A full bot → web update on a watched row was not observed. |
| O7 | Measured quality | Eval run 3 scored tracked resolution 100% and `event_type` 94%, against **unreviewed** labels. The `decide()` contract test passes for both adapters. |

(source: raw/2026-10-11-signals-ingest.md §Concept, Outcomes)

## Owner and orchestrator decisions during the build

**Owner decisions.**
- **ORCH-5.** Settled six PRD/intent inconsistencies: ten source rows (the PRD says "nine"); mask all four keys; five root variables, where an empty ceiling means `1.00`; the pin moves G → H (the intent's F pin was stale); the PRD's table names win (`model_calls`, `model_spend_daily`, `model_routes`, `model_prices`); new testdata folders.
- **ORCH-6.** GlobeNewswire is **enabled** with feed text only every 120 s, an owner-approved deviation from D5's "registered but disabled". Business Wire is **disabled** with `tokens []` until the owner supplies category tokens. The SEC contact is an e-mail address used for sec.gov only, because sec.gov answered 403 to a URL-form contact. SET stays `headline_only` until its download endpoint is verified with a key.
- **ORCH-7.** Provider fixtures are constructed. The closed 12-event log set is kept, with no start-up `GET /v1/models` call.
- **ORCH-8.** The `documents` CHECK is widened so a quarantined document can name its stage (see [[centralized-migrations]]).
- **ORCH-9 / ORCH-11.** `secretValues` also masks `TIDEWATCH_HTTP_CONTACT`, and the contact goes to sec.gov only, at runtime too.
- **ORCH-12.** Title-hash dedup applies only to a wire or media document against another source within 72 h (see [[source-registry-and-ingest]]).
- **ORCH-13.** Failed-call accounting (see [[model-routes-and-spend]]).
- **ORCH-14.** A live EDGAR filing over 4 MiB is stored `headline_only` from its Atom entry, with no quarantine row.
- **ORCH-15.** Comment-only corrections to the root `.env.example` were allowed.
- **ORCH-17.** Extraction `max_tokens` goes from 1200 to 2500. On the preview, 51 of 58 failed extraction calls had stopped at 1200 with truncated JSON, and about 16% of filings were quarantined.
- **ORCH-18.** `signals-eval` scores resolution against the labelled instruments that exist in the instrument master ("tracked"). The 90% bar applies to the tracked figure.
- **ORCH-19** (owner: "Ok got it then merge it all and continue"). Every code PR merges before the 24 h soak. FR-SIG-E2E-002, FR-SIG-E2E-003 and FR-SIG-BRN-012 are recorded as **unverified at merge, not failed**. This follows the slice-2b "merge now" precedent (OWNER-2 on [[zone-transition-bot]]). The owner asked to continue with slice 4.

**Orchestrator rulings.** ORCH-1: migration H is planned as service MIG steps but ships in its own migrations worktree, branch and PR. ORCH-2/3: the service plan pins the shared contracts in `contracts.md`, and H's version is MIG1's output. ORCH-4: the root files belong to the bot plan, outside any PR. ORCH-10: bot S16–S18 wait for MIG2, and C-SIG-1 copies may come first if checked with `cmp`. ORCH-16: OpenRouter requests carry no `temperature`, a provider constraint (see PV-1).

(source: raw/2026-10-11-signals-ingest.md §Concept, Owner and orchestrator decisions during the build)

## Preview findings and a false spec assumption

- **PV-1 (blocking).** OpenRouter answered 404 "No endpoints found that can handle the requested parameters" for `anthropic/claude-haiku-5.5` with `temperature: 0` plus `require_parameters`. Without `temperature`, it answered 200. ORCH-16 (`8ee0b71`) fixed it, and the 138 `provider_rejected` documents were requeued.
- **PV-2.** After the first request, PR Newswire's Cloudflare front answers 404 HTML to the bot's Node client, while a host `curl` gets 200. The owner chose to poll every 900 s and observe. That was a preview-only data change; the merged seed keeps 120 s. The owner asked about Puppeteer, which was declined on terms and refusal grounds.
- **PV-3.** The owner signed in first with their own new admin password and shared it for e2e through a file. It was never printed (see [[forge-preview-gateway]]).
- **Spec assumption A1 was false.** The SET Smart Marketplace "IR Website" news API is for listed companies to show their own news. A subscription needs a company application, so an individual cannot obtain it. `set-notices` stays key-gated (`missing_secret`), and **slice 3a has no Thai SET stock signals**. The alternatives researched (the PRD/NBT Open API, newsdata.io) do not replace SET disclosures. A follow-up spec for a licensed Thai-stock news source is recorded.

(source: raw/2026-10-11-signals-ingest.md §Concept, Preview findings and Spec assumption A1)

## Test plan and acceptance

There is no CI (D4), so all commands run locally. Migrations: `make migrate-validate` and `make check-disposable-db` (1330 PASS / 0 FAIL). Service: `make ci` and `make test-integration`, with no `--- SKIP` allowed. Bot: `pnpm nx run-many -t lint test typecheck build` and `scripts/sql-integration.sh`, which asserts H and its SHA-256. `run signals-eval` runs only on a preview with keys. Web: `pnpm nx run-many -t lint test build` and the full Playwright suite against a preview (source: raw/2026-10-11-signals-ingest.md §Test plan, Commands).

The named acceptance tests must not be renamed. Examples: `TestSignalMessage_FixtureHash`, `TestParseSignalHeader`, `TestBangkokDayStart`, `TestHub_Dispatch_SignalForwardedUnchanged`, `TestMarketWatch_SignalsToday_BangkokDay`, the bot's `decide.contract.spec.ts` and `scoring.spec.ts` (0.0124 / 0.0907 / 0.4224), and the web's `apply-stream-message.spec.ts`, run under two host time zones (source: raw/2026-10-11-signals-ingest.md §Test plan, Named acceptance tests).

**Code reviews.** Service: security r1 found M1, case-insensitive header decoding where the browser reads exact keys, and L1, invalid UTF-8 forwarded. Both were fixed in `2fec95d`. Bot round 1 split three ways: code-signals (BOT-D1 and W1–W5), code-ingest (B1, the one-sided syndication window, and EDGAR over 4 MiB) and security (M1, pin the key hosts). Fixes A `2b908c6` and B `8235f31` followed, and all three r2 reviews approved. The ORCH-16/17/18 deltas were each approved. Web: angular, security and code reviews approved, and the P3 design review approved with 5 advisories (source: raw/2026-10-11-signals-ingest.md §Test plan, Reviews).

### Acceptance at merge (PRD §9, read with ORCH-19)

| IDs | Status | Evidence / note |
|---|---|---|
| FR-SIG-MIG-001, 002 | Verified | Harness 1330/0, with the ORCH-8 CHECK as the only deviation; preview `/api/ready` 200 on H |
| FR-SIG-ING-001…004, 006…011 | Verified | Specs on H. EDGAR ×3 succeeded on the first run; a forced CIK refresh wrote 516 aliases; Finnhub stored 124 documents once its key was active |
| FR-SIG-ING-005 | Verified (mocked) | Constructed fixtures only, because the SET key is listed-company-only (A1 false) |
| FR-SIG-BRN-001…010 | Verified | Jev bodies byte-equal to the probes; 1,255 live Jev calls by 10:47Z; 43 real C-SIG-1 publishes (BRN-007); 12 events and 9 series (BRN-010) |
| FR-SIG-BRN-011 | Verified against **unreviewed** labels | Eval run 3: tracked 100%, all-labelled 89%, `event_type` 94% |
| FR-SIG-SVC-001…003 | Verified | Named tests; exact-key decoding since `2fec95d`; live forwarding seen in P2 |
| FR-SIG-WEB-001…003 | Verified | Unit specs; P1 Playwright 1+689+3 passed, 4 gated skips, 0 failed; P3 design approved |
| FR-SIG-E2E-001 | Verified with exceptions | The first signal (09:36:40.690Z, `NVDA@webull`, `finnhub-company-news`, `m_and_a`) came 10 s after its document was first seen. Binance TH listings only ran `noop`; `set-notices` is `missing_secret` |
| FR-SIG-E2E-004 | Verified (fallback) | An orchestrator-injected C-SIG-1 on `sig:NVDA@webull` reached the browser 52 ms after publishing, and NVDA went from 2 to 3 with no reload. No real bot → web update on a watched row was seen |
| FR-SIG-E2E-005 | Verified | The ceiling set to `0.01` queued 4 documents and logged one `signals_spend_ceiling_reached`; on restore, the queue drained the same Bangkok day |
| FR-SIG-E2E-002, E2E-003, BRN-012 | **Unverified at merge** (ORCH-19) | The 24 h soak, a real two-wire pair and the post-soak query re-capture are outstanding |

Totals: **30 verified, 3 qualified (ING-005, E2E-001, E2E-004), 3 unverified at merge, 0 failed** out of 36 (source: raw/2026-10-11-signals-ingest.md §Test plan, Acceptance at merge).

**Pre-soak picture (about 09:54Z).** Every enabled source that had its secret read `fresh`. The quarantine ratios were high for EDGAR 6-K (78/100) and 8-K (86/98). These were mostly the 138 PV-1 rows and the pre-ORCH-17 `schema_invalid` rows; after the fixes, `signals-requeue` moved them back. EDGAR documents mostly ended `no_instrument` or `not_material`, and **only the media tier had produced signals** (Finnhub: 8 documents signalled). The soak capture was therefore scheduled for 2026-10-12 ~10:00Z or later, so that the rolling 24 h window excludes the pre-fix rows (source: raw/2026-10-11-signals-ingest.md §Test plan, Preview pre-soak captures).

### Manual reproduction

1. **Sources.** Run the "Stale sources" query in `packages/signals/VERIFICATION.md`. Every enabled source with its secret should read `fresh`.
2. **Count.** Open Overview. For a watchlist instrument with a signal today (Bangkok), the Signals cell reads "n signals today", which equals the `signals` count since Bangkok midnight.
3. **Live increment.** Publish a C-SIG-1 payload copied from the fixture's `examples[]` to `sig:<visible id>`, with a fresh `signal_id` and a `created_at` on the page's Bangkok day. The count goes up by one within 2 s with no reload. Re-publishing the same `signal_id` changes nothing.
4. **Ceiling.** Set `MODEL_SPEND_DAILY_CEILING_USD=0.01` and restart `tidewatch-bot`. Documents queue as `ceiling`, and one `signals_spend_ceiling_reached` appears. Restore the variable and restart: the queue drains the same Bangkok day while spend is under the ceiling.

(source: raw/2026-10-11-signals-ingest.md §Test plan, Manual reproduction)

## Open items

- **Unverified at merge (ORCH-19).** The 24 h soak (FR-SIG-E2E-002, E2E-003, BRN-012) should be captured after 2026-10-12 ~10:00Z. It is open whether the quarantine ratio falls under 5%, whether filings, wires and exchange notices produce signals at all, and whether a real two-wire pair occurs. A full bot → web update on a watched row was never observed. The eval labels are model-written and unreviewed (A5).
- **Owner actions.**
  - Apply migration H to the owner's own database (`make migrate-up` with their `DATABASE_URL`). H is additive with no backfill; its down is destructive.
  - Run `/forge-sync` so the local checkouts of the four repos reach the merge commits.
  - Set `JEV_API_KEY` and `OPENROUTER_API_KEY` (optionally `FINNHUB_API_KEY` and `MODEL_SPEND_DAILY_CEILING_USD`) in `.env`, and restart `tidewatch-bot`. `TIDEWATCH_HTTP_CONTACT` must be an e-mail address, or EDGAR stays disabled.
  - Supply the Business Wire category tokens. Enabling the source is an `UPDATE` of its `sources` row.
  - Refresh the `DESIGN.md` snapshot at wrap-up (SW-11).
- **Rollback.** For the bot, list the other eleven names in `MARKET_DATA_COLLECTORS` and restart; the tables stay. A service rollback restores `signals: null`, and a web rollback restores the dash.
- **Follow-ups.** `state.json` records 18 follow-ups. They are listed on the concept pages: service and web on [[signal-message-contract]]; prompts and extraction on [[signals-pipeline]]; ingest, aliases and the `documents (source_code, external_id)` index on [[source-registry-and-ingest]]; aliases on [[instrument-master]]. One more is a spec for a licensed Thai-stock news source.
- **Not measured.** The growth of about 40 MB/day of documents at the PRD's volume was not measured. Retention is out of scope until a later slice.
- **Next consumers.** Slice 4 (the Signals page) reads `signals`, `documents` and `extractions`. Slice 6's scout reads `signals`, and `decisions.signal_ids[]` will reference `signals.signal_id` (see [[decision-record]]). Spec 3b adds GDELT sources and the context layer to the same registry.
- **Update: spec 3b merged on 2026-10-30** (migrations#15, service#17, bot#18, web#22) as [[signals-context]]. Migration N adds three sources (13 in all): two GDELT GKG streams with a keep gate and `finnhub-earnings-calendar`. It adds coverage signals, `media` rows with `origin = 'context'` and impact 0 that never trigger. It adds an event calendar and two optional scout discovery paths. The `context` runner is not yet running in production (source: raw/2026-10-30-signals-context.md, summary block).
- **Update: slice 4 merged on 2026-10-12** (migrations#9, service#10, web#12). It reads these tables through eight new routes, and user orders placed from a signal now fill `decisions.signal_ids` (see [[signals-page]] and [[signal-cited-orders]]) (source: raw/2026-10-12-signals-page.md, summary block; §Concept, Stage).
- **Update: history and retention, checked on 2026-10-13.** `signals` still has no retention policy, and signal history begins with this slice (2026-10-11). The Signals page's *Day* select reads any of the last 7 Bangkok days. A day before history began reads as an empty past day. The select merged on 2026-10-14 as tidewatch-web#13 and is not deployed (see [[signals-day-control]]) (source: raw/2026-10-14-signals-day-control.md §Concept, Problem; §Components, Copy).
- The slice-3a ORCH-19 above (merge before the soak) is a different decision from the signals page's ORCH-19, which asked for the day control (source: raw/2026-10-12-signals-page.md §Concept, Owner decisions taken during the build).

(source: raw/2026-10-11-signals-ingest.md §Open questions)

## Related pages

- [[source-registry-and-ingest]]: the ten sources, the ingest runner, dedup and named resolution
- [[signals-pipeline]]: triage, extraction, scoring, impact and the signal transaction
- [[model-routes-and-spend]]: model ids as data, the spend ledger and the daily ceiling
- [[signal-message-contract]]: C-SIG-1 on `sig:<instrument_id>`, its forwarding and the web count
- [[centralized-migrations]]: migration H and the required version moved G → H
- [[instrument-master]]: the aliases and CIKs that signals resolve to
- [[market-data-worker]]: the `ingest` and `signals` runners in `serve`
- [[redis-market-contract]]: the `sig:` channel beside `px:*`
- [[realtime-websocket]]: the `signal` frame on `/ws`
- [[market-data]]: the Market watch row's `signals.today`
- [[design-system-decisions]]: the Signals cell states
- [[forge-preview-gateway]]: the isolated preview, its refreshes and the provider keys
- [[zone-transition-bot]]: the "merge now" precedent that ORCH-19 follows
- [[bot-activity]]: the preceding feature, whose migration G H follows
- [[signals-page]]: slice 4, the next feature, which gives these signals a screen
- [[signals-day-control]]: the *Day* select that reads the last 7 days of this history
- [[signals-context]]: spec 3b, the GDELT context layer and event calendar this slice deferred
