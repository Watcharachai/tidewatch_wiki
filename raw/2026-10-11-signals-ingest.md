# Signals ingest and extract (`signals-ingest`, slice 3a)

> Before this slice nothing in Tidewatch read a filing, a press wire or an exchange notice, and the Market watch *Signals* column was a hard-coded dash. Slice 3a builds the pipeline from feed to `signals` row. The bot gained two packages and two runners. `packages/ingest` reads ten seeded `sources` rows (SEC EDGAR 8-K, 6-K and Form 4; PR Newswire and GlobeNewswire feed text; Binance TH listings; key-gated SET notices and Finnhub news; Business Wire and AccessWire seeded disabled) and stores deduplicated `documents`. `packages/signals` runs Jev triage, OpenRouter extraction with `anthropic/claude-haiku-5.5` (strict `json_schema` plus client-side Ajv), and Jev scoring per instrument. Every call goes through a daily spend ledger with a ceiling. Each surviving (document, instrument) is committed as a `signals` row and then published to `sig:<instrument_id>` with the byte-pinned C-SIG-1 message. Migration H (`20261011020408`) adds 18 tables, 8 indexes and the seeds. The service forwards `sig:` on `/ws` as a new `signal` frame and adds `signals.today` (Bangkok day) to every Market watch row. The web Signals cell now shows today's count and raises it live. The four PRs were merged on 2026-10-11 between 14:58:10Z and 14:59:23Z on the owner's instruction (ORCH-19): tidewatch-migrations #7 (merge `e015a3a`), tidewatch-service #8 (`2f9854f`), tidewatch-bot #7 (`0d7be6d`) and tidewatch-web #10 (`c2a1b26`). At merge, 30 of the 36 acceptance IDs were verified, 3 were verified with qualifications, and 3 were unverified (the 24-hour soak IDs FR-SIG-E2E-002, FR-SIG-E2E-003 and FR-SIG-BRN-012) because the soak had not run. The `/signals` page is still the slice-0 placeholder (slice 4). Counts appear only in the Market watch table on Overview, for instruments on the user's watchlist. The owner must apply H to their own database; the merged service answers `/ready` 503 until then.

**Sources (inputs to this document).**
- Spec: `/Users/maichinu/tidewatch/tidewatch-specs/signals-ingest/build-prompt.md`, `intent.md` (O1–O7, D1–D5, PD1–PD10; sha256 `7ca20e02…ce58`), `prd.md` (§3–§11, S1–S12, A1–A8; sha256 `6d14fb96…b436`). Fingerprints verified at build start (2026-10-10T18:30:41Z).
- Build record: `/Users/maichinu/tidewatch/.forge/features/signals-ingest/state.json` (log, per-project execution, reviews, `runtime.preview`, `ownerDecisions`, `previewFindings`, `specAssumptionFindings`, `followUps`, `merged`), `verification.md` (acceptance ledger, updated about 10:55Z, before the merge), `planning/cross-plan-decisions.md` (ORCH-1…19), `planning/tidewatch-service/contracts.md` (r1–r4: C-SIG-1, the `/ws` frame, the row field, H's version, the seeds and the live feed checks).
- Preview evidence under `/Users/maichinu/tidewatch/.forge/features/signals-ingest/evidence/preview/`: `P2/P2-summary.md`, `E2E-005/E2E-005-summary.md`, `E2E-001-note.md`, `BRN-011/signals-eval-run3.log`, `BRN-011/signals-eval-labelled-filings-v1.run3.json`, `BRN-011/review-note.txt`, and `BRN-012-pre-soak/*.tsv`.
- Plans (under `/Users/maichinu/tidewatch/.forge/docker/runs/sig-d1c18e46/worktrees/`):
  - `329891b601/.plans/signals-ingest.md`: service, plus migration H as MIG1–MIG3; MH1–MH8, SS1–SS7, R1–R12.
  - `6945fd5d6c/.plans/signals-ingest.md`: bot S1–S24, R-SIG-1…39, amended by ORCH-16/17/18.
  - `5eb4e5c7ea/.plans/signals-ingest.md`: web S1–S4, SW-1…SW-11.
- Merged code, read at the PR heads: service `329891b601` (`CLAUDE.md`), bot `6945fd5d6c` (`CLAUDE.md`, `README.md`, `packages/signals/VERIFICATION.md`, `packages/{ingest,signals}/src`), web `5eb4e5c7ea` (`CLAUDE.md`, `DESIGN.md`, `workspace.routes.ts`).

## Concept

### Stage, stated precisely

| Stage | Status (state.json, last update 2026-10-11T14:59:52Z, phase `SOURCING`) |
|---|---|
| Implemented | All 36 plan steps are committed: service 8 (MIG1–MIG3, S1–S5), bot 24 (S1–S24) and web 4 (S1–S4) (`perProject.<p>.completedSteps`). Later commits from review and preview fixes: service `2fec95d` and `b9de179`; migrations `dd7e150`; bot `2b908c6`, `8235f31`, `d64e732`, `8ee0b71` (ORCH-16), `f786102` (ORCH-17) and `53cb76d` (ORCH-18); web `534e140`. The workspace-root `docker-compose.yaml` and `.env.example` were edited in place and are in no PR (ORCH-4). |
| Verified locally | Every step's contract commands exited 0 on the orchestrator's re-run, except four superseded step-time checks: bot S9 c16, S11 c09 and S14 c08 (the `fixtures-readme.mjs` form that S20 replaced) and S23 c03 (comment-only lines removed, which ORCH-15 allows). Migrations harness: 1330 PASS / 0 FAIL. Bot unit tests at `53cb76d`: signals 120, ingest 153, worker 54. C-SIG-1 three-way `cmp` (canonical = service = bot = web, sha256 `a0829396…e7d1`) at 2026-10-11T08:14Z. |
| Reviewed | **Plans:** service r1 APPROVED (0/5/6), then deltas r2 and r3 after ORCH-8 (both APPROVED). Bot r1, r2 and r3 CHANGES REQUESTED (5/11/9, then 2/3/5, then 1/0/3); r4 APPROVED. Web r1 CHANGES REQUESTED (1/2); r2 APPROVED. **Code:** see Test plan → Reviews. |
| Verified on a preview | 30 IDs verified, 3 verified with qualifications, 3 pending the 24 h soak. 0 failed. Isolated preview (compose project `forge-0199b29a-sig-d1c18e46`, fresh database migrated to H, 10 sources with 8 enabled), with the owner's Jev, OpenRouter and Finnhub keys and no SET key. See Test plan. |
| Merged | Yes, 2026-10-11, by the owner by hand: the session's permission policy blocked the orchestrator's `gh pr merge`. Order recorded: bot#7 at `53cb76d` (merge `0d7be6d`, 14:58:10Z); migrations#7 at `dd7e150` (`e015a3a`, 14:59:06Z); service#8 at `b9de179` (`2f9854f`, 14:59:11Z); web#10 at `534e140` (`c2a1b26`, 14:59:23Z). The bot merged about one minute before the migrations, against the planned order (migrations first); nothing deploys automatically. Before the merge, all four PRs were checked OPEN, MERGEABLE and CLEAN at those heads. No CI is configured (D4). |
| Running on the owner's own stack | Not recorded. H is not applied to the owner's database; the merged service answers `/ready` 503 until it is. |

### Problem

The intent verified the gap against `origin/main` on 2026-10-11:

- **No `sources`, `documents` or `signals` table existed.** Nothing read SEC filings, wires or exchange notices.
- **The Signals column was a hard-coded dash on both sides.** The service always sent `Signals *struct{}` as null (`internal/handlers/marketwatch.go`). The web hard-coded `signals: null` (`data/market-data.model.ts`).
- **The `/ws` hub forwarded only `px:<id>`.** `PxType` was a closed set (`tick|bar|zone|status`), and `sig:` appeared nowhere in the service, the bot or the web.
- **`instrument_aliases` was never read by alias, CIK or ISIN.** Only S&P 500 members carried `cik` aliases.

The research brief's strategy (§2.1) is primary source, good extraction and a drift horizon: read 8-Ks, releases and exchange notices within seconds, extract them well, and trade the window of hours to days. The language model extracts and never forecasts. A calibrated probability is the only thing passed between components.

### Chosen design (intent decisions, confirmed 2026-10-11)

- **D1 Primary sources now; GDELT is spec 3b.** GDELT is a context layer whose only consumer is the slice-6 scout.
- **D2 OpenRouter for the LLM, one key, model ids as data.** The model behind every call is a database string, so A/B tests and tier changes are data changes.
- **D3 Hybrid: the LLM names, Jev scores.** The LLM reads and names instruments, including implied suppliers, customers and peers. Jev supplies every probability. The owner's probe showed Jev reporting a genuine 40/37/23 direction split where an LLM would assert a direction.
- **D4 Full text for primary sources, headline-only for media.**
- **D5 Feed text only for every wire** (`config.body_fetch = false`, a seed value). PR Newswire's terms prohibit automated retrieval and data mining of its site. Business Wire's site refuses non-browser clients, and its terms prohibit storing or copying content. A browser User-Agent to get past a refusal was rejected outright. The page-fetch path exists and is gated by that seed value.
- **Accepted defaults** (proposed defaults the owner confirmed, not separate decisions):
  - PD1: Jev direct with `JEV_API_KEY`, its model pinned to `jev-1.13.0`, never `jev-latest`.
  - PD2: a ceiling of $1.00 per day.
  - PD3: materiality thresholds filing 0.50, exchange 0.50, wire 0.60, media 0.70; `applies` threshold 0.6.
  - PD4: the impact formula.
  - PD5: `anthropic/claude-haiku-5.5` for extraction.
  - PD6: CIK and alias resolution with a daily CIK refresh.
  - PD7: no mockup; the existing cell is filled.
  - PD8: two new bot packages.
  - PD9: a labelled set of 100 filings.
  - PD10: a pure-JS PDF extractor.

### Outcomes (intent O1–O7) at merge

| # | Outcome | State at merge |
|---|---|---|
| O1 | The brain has input, unattended | Ingest ran on the preview. EDGAR ×3, GlobeNewswire and PR Newswire succeeded on their first run. The 24 h soak criterion (FR-SIG-E2E-002) is **unverified**. |
| O2 | Calibrated probability, honestly | Every probability comes from Jev answers. The full direction distribution is stored (`p_up`, `p_down`, `p_neutral`). Model ids and prompt versions are on every row. |
| O3 | Bounded cost that never drops work | Ledger and ceiling verified (FR-SIG-BRN-008, FR-SIG-E2E-005). Pre-soak spend was $0.641961 by 10:49Z, under $1.00. |
| O4 | Provenance and dedup | Unit and integration specs on H pass. A live two-wire pair (FR-SIG-E2E-003) is **unverified**. |
| O5 | Operator-readable health | `VERIFICATION.md` holds the eight queries, captured once before the soak. The re-capture after the soak (FR-SIG-BRN-012) is **pending**. |
| O6 | Realtime and the count | Service → web was verified live with an injected message. Bot → Redis was shown by 43 real publishes. A full bot → web update on a watched row was not observed. |
| O7 | Measured quality | Eval run 3: tracked resolution 100%, `event_type` 94%, against **unreviewed** labels. The `decide()` contract test passes for both adapters. |

### Owner and orchestrator decisions during the build

**Owner decisions:**
- **ORCH-5:** six PRD/intent inconsistencies settled.
  - Ten source rows, where the PRD says "nine".
  - Mask all four keys.
  - Five root variables; an empty ceiling means `1.00`.
  - The intent's F pin was stale; the pin moves G → H.
  - The PRD's table names win (`model_calls`, `model_spend_daily`, `model_routes`, `model_prices`, not the intent's `model_spend`).
  - New testdata folders.
- **ORCH-6** (O1/O2/O3):
  - GlobeNewswire **enabled**, feed text only, 120 s. A non-keyword RSS feed was verified, so A3 was false. This is an owner-approved deviation from D5's "registered but disabled".
  - Business Wire **disabled**, `tokens []`, until the owner supplies category tokens.
  - The SEC contact is an e-mail address (the owner's), used for sec.gov only. sec.gov answered 403 to a URL-form contact.
  - SET stays `headline_only` until its download endpoint is verified with a key.
- **ORCH-7:** provider fixtures are constructed. The closed 12-event log set is kept, with no start-up `GET /v1/models` call.
- **ORCH-8:** the `documents` CHECK is widened so a quarantined document can name its stage (see Database).
- **ORCH-9:** `secretValues` also masks `TIDEWATCH_HTTP_CONTACT` (five masked values).
- **ORCH-11:** the contact e-mail goes to sec.gov only, at runtime too. The Wikipedia `research` User-Agent no longer carries an e-mail-form contact.
- **ORCH-12:** title-hash dedup applies only to a **wire or media** document against **another** source within 72 h. This narrows PRD §4.3; same-source repeats and filings or notices are kept.
- **ORCH-13:** an HTTP error answer is recorded at the reported cost, usually 0 with `estimated = true`, and does not consume the ceiling. A timeout or connection loss after sending is recorded at the pre-call estimate and counts.
- **ORCH-14:** a live EDGAR filing whose complete submission exceeds 4 MiB is stored `headline_only` from its Atom entry, with no quarantine row. This amends PRD §4.2's `body_too_large` quarantine for `sec-edgar-*`.
- **ORCH-15:** comment-only corrections to the root `.env.example` were allowed.
- **ORCH-17:** extraction `max_tokens` goes from 1200 to 2500. On the preview, 51 of 58 failed extraction calls had stopped at 1200 with truncated JSON, and 29 of about 180 filings were quarantined (about 16%).
- **ORCH-18:** `signals-eval` scores resolution against the labelled instruments that exist in the instrument master ("tracked"). The all-labelled figure is still reported, and the 90% bar applies to the tracked figure.
- **ORCH-19** (owner: "Ok got it then merge it all and continue"): merge every code PR before the 24 h soak. FR-SIG-E2E-002, FR-SIG-E2E-003 and the FR-SIG-BRN-012 re-capture are recorded as **unverified at merge, not failed** (the pattern of slice 2b's "merge now"). The `/signals` placeholder copy is unchanged. The owner asked to continue with slice 4.

**Orchestrator rulings:**
- **ORCH-1:** migration H is planned as service MIG steps, in its own migrations worktree, branch and PR.
- **ORCH-2:** the service plan pins the shared contracts in `contracts.md`.
- **ORCH-3:** H's version is MIG1's output.
- **ORCH-4:** the root files belong to the bot plan, outside any PR.
- **ORCH-10:** bot S16–S18 wait for MIG2 verified. C-SIG-1 copies may precede service S1, checked with `cmp`.
- **ORCH-16:** OpenRouter requests carry no `temperature`. A provider constraint; the owner was informed.

**Preview findings:**
- **PV-1 (blocking):** OpenRouter answered 404 "No endpoints found that can handle the requested parameters" for `anthropic/claude-haiku-5.5` with `temperature: 0` plus `require_parameters`, and 200 without `temperature`. Fixed by ORCH-16 (`8ee0b71`). The 138 `provider_rejected` documents were requeued.
- **PV-2:** PR Newswire's Cloudflare front answers 404 HTML to the bot's Node client after the first request, while a host `curl` gets 200. The owner chose to poll every 900 s and observe. This was a preview-only data change (`schedule_seconds = 900`); the merged seed keeps 120 s. The owner asked about Puppeteer, which was declined on terms and refusal grounds.
- **PV-3:** the owner signed in with their own new admin password and shared it for e2e through a file, never printed.

**Spec assumption A1 was false.** The SET Smart Marketplace "IR Website" news API (`marketplace.set.or.th/api/public/news/IR`) is a service for listed companies to show their own news on their IR website. A subscription needs a company application, the authorised signatory's contract and company registration documents, so an individual cannot obtain it. `set-notices` stays key-gated (`missing_secret`), and slice 3a has no Thai SET stock signals.
- Alternatives were researched, and none replaces SET disclosures:
  - the PRD/NBT Open API: government and regional news, a fit for the 3b context layer;
  - newsdata.io: media tier, a 12 h delayed free tier, US$199.99/month for real time.
- A follow-up spec for a licensed Thai-stock news source is recorded.

### What the user sees, and what they don't

- **Overview → Market watch:** the *Signals* column shows today's count (Bangkok day) for each watchlist row and goes up live when a `signal` frame arrives. 0 or no count is the existing dash.
- **No other screen changed.** The `/signals` route still renders the slice-0 empty state (`workspace.routes.ts`: `screen("signals", "Signals", { emptyTitle: "No signals yet", … })`). The Signals page is slice 4. Signals of instruments that are not on the watchlist are stored and published, but no screen shows them yet.
- **Unresolved names are SQL-only.** The review list (`extraction_unresolved`) has no UI.

## Database

Migration H is `migrations/20261011020408_signals_ingest.sql` in tidewatch-migrations (PR #7, head `dd7e150`; H's content last changed in `8d00dd4`; merge `e015a3a`). It is one file in goose's default transaction, created with `make migrate-create NAME=signals_ingest`, after G (`20261010061500`). Its version is the service's new `RequiredSchemaVersion` (`internal/platform/postgres/schema.go`). The bot harness asserts it and pins its sha256 `a77fcf10fd6cd481af3ee347306cc998b3e5ebe53438b65a35a8dcffdbb0520d`. A database migrated only to G answers `/ready` 503 (`required version 20261011020408 not applied`).

**Objects: exactly PRD §5.1, with one owner-approved substitution (ORCH-8).** MIG1 verified that the DDL block's sha256 equals the PRD block after that one-line swap.
- **18 tables**, in this order:
  - sources and runs: `sources`, `source_cursors`, `source_files`, `source_runs`;
  - documents: `documents`, `document_versions`, `document_instruments`, `document_quarantine`;
  - model stages: `triage`, `extractions`, `extraction_unresolved`;
  - versions and spend: `scoring_versions`, `prompt_versions`, `model_routes`, `model_prices`, `model_calls`, `model_spend_daily`;
  - output: `signals`.
- **8 indexes:** `source_runs_source_started_idx`, `documents_title_hash_published_idx`, `documents_stage_published_idx`, `document_versions_document_idx`, `document_quarantine_created_idx`, `model_calls_created_idx`, `signals_instrument_created_idx`, `signals_created_idx`.
- **Nothing else:** no other index, trigger, function or `ALTER` of an earlier table; `uuidv7()` defaults as in A–G; PostgreSQL's default constraint names.

**The ORCH-8 deviation.** PRD §4.3 keeps a quarantined document at `stage = 'quarantined'` with `skip_reason` naming the stage (`triage`, `extraction`, `scoring`), but §5.1's CHECK would refuse that row. H writes instead:

```sql
-- on documents (constraint documents_check), in place of
-- CHECK ((stage = 'skipped') = (skip_reason IS NOT NULL))
CHECK ((stage IN ('skipped', 'quarantined')) = (skip_reason IS NOT NULL))
```

There is no `ingest` value for `skip_reason`. An ingest-time quarantine (unparseable, missing fields, oversized body) writes only `document_quarantine` (`stage = 'ingest'`, `document_id` NULL) and creates no `documents` row. `signals-requeue` clears `skip_reason` and `queued_reason` when it moves rows back to `stored`.

**Key shapes** (full DDL in PRD §5.1):

```sql
-- documents (excerpt)
canonical_url text NOT NULL, title_hash text NOT NULL CHECK (title_hash ~ '^[0-9a-f]{64}$'),
body_status text NOT NULL CHECK (body_status IN ('full', 'feed_only', 'headline_only')),
issuer_cik text CHECK (issuer_cik ~ '^[0-9]{1,10}$'), duplicate_of uuid REFERENCES documents (document_id),
stage text NOT NULL DEFAULT 'stored'
  CHECK (stage IN ('stored', 'triaged', 'extracted', 'scored', 'signalled', 'skipped', 'quarantined')),
skip_reason text CHECK (skip_reason IN ('duplicate', 'not_material', 'routine', 'no_instrument', 'not_relevant',
                                         'withdrawn', 'triage', 'extraction', 'scoring')),
queued_reason text CHECK (queued_reason IN ('ceiling', 'missing_key', 'provider_unavailable')),
UNIQUE (canonical_url)

-- signals (excerpt): one row per surviving (document, instrument)
direction text NOT NULL CHECK (direction IN ('up', 'down', 'neutral')),
p, p_up, p_down, p_neutral, applies_p numeric(4,3), horizon text CHECK (horizon IN ('intraday', 'days', 'weeks')),
novelty text CHECK (novelty IN ('first', 'repeat')), mention text CHECK (mention IN ('named', 'implied')),
conviction numeric(5,4), impact numeric(5,4), scoring_version integer REFERENCES scoring_versions,
triage_model_id, extraction_model_id, scoring_model_id, prompt_version text NOT NULL,
UNIQUE (document_id, instrument_id)
```

- `event_type` (on `triage` and `signals`) is a closed CHECK of 15 values: `earnings, guidance, m_and_a, financing, insider, regulatory, product, legal, macro_rate, macro_data, listing, halt, hack, supply, other`. A new type needs a migration (PRD S12).
- `severity` is `numeric(4,2)`, Jev's Score expected value (S11).
- `extractions` is `UNIQUE (document_id, prompt_version, model_id)`.
- `model_calls.stage` also allows `eval`.
- `model_spend_daily` has the primary key `(day_bkk, provider, model_id)`.
- `provider` is `jev|openrouter` throughout. A small-LLM fallback call is recorded as `openrouter` (R-SIG-34).

**Seeds (same file; data, so a later change is a data migration):**
- `sources`: 10 rows, 8 enabled (see API → Source registry).
- `scoring_versions` row 1:

  ```json
  {"material_threshold": {"filing": 0.50, "exchange": 0.50, "wire": 0.60, "media": 0.70},
   "applies_threshold": 0.60, "novelty_window_days": 5,
   "half_life_hours": {"intraday": 2, "days": 24, "weeks": 120},
   "novelty_w": {"first": 1.0, "repeat": 0.6}, "mention_w": {"named": 1.0, "implied": 0.8},
   "neutral_min_p": 0.5}
  ```

- `model_routes`:
  - `triage (jev, jev-1.13.0, small_llm, anthropic/claude-haiku-5.5)`;
  - `scoring` (the same);
  - `extraction (openrouter, anthropic/claude-haiku-5.5, NULL, NULL)`.
- `model_prices`:
  - `(jev, jev-1.13.0, 0.042, 0, 2026-10-11)`;
  - `(openrouter, anthropic/claude-haiku-5.5, 0.10, 0.50, 2026-10-11)`.
- No `prompt_versions` seed: the bot records `(version, stage, sha256)` at start.

**Down.** `DROP TABLE IF EXISTS` for the 18 tables in reverse order, never `CASCADE`. It deletes every source, run, document, extraction and signal, and the spend ledger. Owner-only and local-only.

**Harness** (`scripts/check-disposable-db.sh`, MIG2): **1330 PASS / 0 FAIL**.
- H lists, `relations_/assert_/absent_signals_ingest`, and the exact catalog of the 18 tables.
- A check named `H seeds: sources …`, which compares the ten rows as jsonb.
- More than 20 refusal probes matched on constraint names (for example `documents_canonical_url_key`, `triage_event_type_check`, `signals_direction_check`, and the ORCH-8 probe `a quarantined document without skip_reason`).
- Accepted controls, including `quarantined|extraction`.
- Make down/up and round trips that now roll back H.

**Growth (PRD §5.3, no retention this slice).** About 1,900 documents/day at about 10 KB each, roughly 40 MB/day for `documents` + `document_versions` (about 15 GB/year before TOAST), a few hundred `signals` and about 3,000 `model_calls` per day. None of this was measured on the preview.

## API

### Service (tidewatch-service, PR #8, head `b9de179`, merge `2f9854f`)

No new route, error code, log event, environment variable, Redis key or dependency. The service never writes `sig:*`.

**`/ws` forwarding (S3, SS2/SS3).**
- For every instrument with a subscriber, the hub's desired set holds both `px:<id>` and `sig:<id>`. One client `subscribe` covers both; client frames, limits and close codes are unchanged.
- On `sig:<id>` the only accepted type is `signal`. `market.ParseSignalHeader` must accept the header (`v` 1, `type` `"signal"`, `instrument_id` equal to the channel's id), and then the payload is forwarded **byte for byte** through the same `forward` path (same ordering and same 1013 eviction).
- Everything else is dropped silently: a bad header, a mismatched id, a `signal` on `px:`, and, after security M1 (`2fec95d`), a header key in a case variant (exact keys `v`, `type`, `instrument_id` only) or a payload that is not valid UTF-8. A drop counts nothing and leaves the socket open.
- `ws_messages_sent_total{type}` now has nine labels: `subscribed, unsubscribed, snapshot, tick, bar, zone, status, signal, error`.
- There is no snapshot and no replay for signals. The REST count resyncs on the web's reload.

**`GET /market-watch` row (S4, SS4/SS5).** `"signals": {"today": <int ≥ 0>}` replaces `"signals": null`, and this build never sends null.
- `today` counts the row's `signals` with `created_at` in `[D, D + 24h)`, where `D` is `BangkokDayStart(generated_at)`: local midnight in `time.FixedZone("Asia/Bangkok", 7*3600)`, with no tz database.
- The count is **one batched query** per read (`instrument_id = ANY($1)`, grouped, served by `signals_instrument_created_idx`); an id missing from the result reads 0.
- The upper bound is explicit (R6), so a row at 00:00:10 the next Bangkok day does not count.
- A failed count fails the read like `Rows`/`Strips` (R10).
- The row ids are the watchlist's instrument ids (S4 flag), so the count exists only for watchlist instruments.

**Schema pin (S2).** `RequiredSchemaVersion = 20261011020408`. `pgtest` has the anchored lookup `^([0-9]{14})_signals_ingest\.sql$` (`SignalsIngestVersion`), and `scripts/integration-test.sh` has an exactly-one check for it. The new test `TestReady_BotWatchSchema_NotReady` proves that a G-only database is 503.

**Compatibility (PRD §6.6).**
- An old service ignores `sig:` and keeps `signals: null`.
- A new service with an old bot shows 0 everywhere.
- A new web with an old service accepts `null` and shows the dash.

### C-SIG-1: the `sig:<instrument_id>` message (bot → Redis → service → web)

- **Canonical bytes:** `/Users/maichinu/tidewatch/.forge/features/signals-ingest/planning/tidewatch-service/signals-message.v1.json`. 9,137 bytes, ASCII, LF, 2-space indent, **sha256 `a0829396c81494f81c19f4506afd613e6bc2b66f0b0f45d335d6aca09c96e7d1`**.
- **Byte-identical copies, each pinned by a test:**
  - service `internal/market/testdata/signals-message.v1.json` (`TestSignalMessage_FixtureHash`; the hub tests read the same file);
  - bot `packages/signals/fixtures/signals-message.v1.json` (`signals-message-fixture.spec.ts`);
  - web `src/app/pages/workspace/data/testdata/signals-message.v1.json` (`market-stream.model.spec.ts` checks its SHA-256 with `crypto.subtle`; `.prettierignore` skips the folder).
- Copy with `cp` and never re-serialise. A change is a contract change in all three repositories at once.
- **Message:** one JSON object, no whitespace, every key present, keys in this order: `v, type, instrument_id, signal_id, document_id, source_code, tier, event_type, direction, p, impact, severity, created_at`.
  - `p`, `impact` and `severity` are decimal strings with 3, 4 and 2 fraction digits, never numbers.
  - `created_at` is the `signals` row's own `created_at` (from `RETURNING`), RFC 3339 UTC with `Z`, and a millisecond fraction only when non-zero.
- **Readers:** the service reads `v`, `type` and `instrument_id`; the web reads `v`, `type`, `instrument_id`, `signal_id` and `created_at`.
- **The file also holds:** vocabularies (`tiers`, `event_types`, `directions`), four `examples`, and eight `service_drops`.
  - The examples are an NVDA 8-K up, an AAPL wire down (the last half-second of a Bangkok day), a PTT.BK SET neutral (exactly Bangkok midnight) and an NVDA media up.
  - The service drops are: a `tick` on `sig:`, a `signal` on `px:`, `v` 2, no `v`, an instrument mismatch, a wrong JSON type, invalid JSON and two JSON values.

```json
{"v":1,"type":"signal","instrument_id":"NVDA@webull","signal_id":"019a…","document_id":"019a…",
 "source_code":"sec-edgar-8k","tier":"filing","event_type":"earnings","direction":"up","p":"0.867",
 "impact":"0.4224","severity":"3.20","created_at":"2026-10-11T20:06:12.345Z"}
```

### Bot runtime (tidewatch-bot, PR #7, head `53cb76d`, merge `0d7be6d`)

Two new `type:shared` Nx libraries:
- `@tidewatch-bot/ingest` depends on `shared` and `market-data`.
- `@tidewatch-bot/signals` depends on `shared`, `market-data` and `ingest`.
- New third-party dependencies, none with an install script (`allowBuilds` stays `nx`): `fast-xml-parser` ^5.11.2 (DOCTYPE and entity declarations refused), `node-html-parser` ^9, `unpdf` ^1.8.1, `ajv` ^8.20.0 and `prom-client` ^15.1.3.
- `COLLECTOR_NAMES` grows to thirteen (`ingest` is twelfth, `signals` thirteenth), both enabled by default.
- The Dockerfile ships eight `dist` trees. `SERVE_POOL_MAX` stays 12: the A7 probe measured an ingest peak of 1, a signals peak of 1 and a combined 2/12, and both runners stopped in 2.8 ms and 1.0 ms.

#### Source registry: the ten seeded rows (contracts.md §5.1)

| `source_code` | Kind / tier, fetch | Schedule | Enabled | Body | Gate and terms |
|---|---|---|---|---|---|
| `sec-edgar-8k`, `sec-edgar-6k`, `sec-edgar-form4` | filing / filing, `atom` (`browse-edgar?action=getcurrent&type=<8-K\|6-K\|4>&output=atom&count=100`) | 60 s | yes | `full`: the primary document plus `EX-99*` from the complete submission `.txt`. Over 4 MiB: `headline_only` from the Atom entry (ORCH-14) | Needs an e-mail-form `TIDEWATCH_HTTP_CONTACT`, else `collector_disabled` `missing_contact`. SEC fair access: `Tidewatch/<version> <contact>`, `Accept-Encoding: gzip, deflate`, ≤ 10 req/s and 4 in flight across the process, a 10-minute pause on 403/429. Filings are public domain. |
| `globenewswire` | wire / wire, `rss` (`rss.globenewswire.com/RssFeed/orgclass/1/…` "News about Public Companies") | 120 s | **yes** (ORCH-6 O2) | `feed_only` | `www.globenewswire.com` refuses non-browser clients, so no page is fetched; `rss.globenewswire.com/robots.txt` does not disallow `/RssFeed/` |
| `prnewswire` | wire / wire, `rss` ("All News Releases") | 120 s seeded; **900 s on the preview only** (PV-2) | yes | `feed_only` | Its Terms of Use prohibit automated retrieval of the site; robots.txt allows `/rss/`. Cloudflare refused the Node client after the first request on the preview (10 failed runs) |
| `businesswire` | wire / wire, `rss` (`feed.businesswire.com/rss/home/`; one request per token, `?rss=<token>`, URL-encoded) | 120 s | **no**, `tokens []` | `feed_only` | Disabled **pending category tokens**. The all-news token answers "deactivated by the administrator", and the token list is on `businesswire.com`, which refuses the product client. Its terms prohibit storing or copying content, so its fixtures are constructed. |
| `accesswire` | wire / wire, `rss` (`accessnewswire.com/newsroom`) | 300 s | **no** | none | No public feed: `/rss` is the company blog, `/rss2` is key-gated, and robots.txt disallows `/rss`, `/rss2` and `/api`. No collector (`collector_disabled` `no_collector`). |
| `set-notices` | exchange / exchange, `json` (`marketplace.set.or.th/api/public/news/IR`) | 300 s | yes, key-gated | `headline_only` until `config.download_url_template` is set (R-SIG-10). PDFs via `unpdf`, bounded to 10 s, 100 pages and 1,000,000 characters | `SET_MARKETPLACE_API_KEY` in the `api-key` header, sent only to the pinned host. **The key is unavailable to an individual (A1 false)**, so the source writes `missing_secret` noop runs. `deletedNews` withdraws a stored notice (`skip_reason = withdrawn`). |
| `binance-th-listings` | exchange / exchange, `poll` (`api.binance.th/api/v1/exchangeInfo`) | 300 s | yes | structured, synthesised; no LLM | A new symbol is a listing; `TRADING` → `BREAK`/`HALT` is a halt, and back is a resumption. The first run stores a baseline only. |
| `finnhub-company-news` | media / media, `json` (`finnhub.io/api/v1/company-news`) | 900 s | yes, key-gated | `feed_only` (the summary), else `headline_only`; the article `url` is stored, never fetched | `FINNHUB_API_KEY` in `X-Finnhub-Token`, sent only to the pinned `finnhub.io`. Personal-use plan. At most 700 symbols per run at ≤ 50 calls/min: watchlist US tickers first, then US list members. |

- **Credibility:** filing 1.00, exchange 0.95, wire 0.85, media 0.60.
- **Pinned hosts (security M1, `8235f31`):** keys go only to `finnhub.io` and `marketplace.set.or.th`, pinned in `packages/ingest/src/collectors/api.ts`. A `sources.url` pointing elsewhere fails the run with `SourceConfigError`.
- **User-Agents:** every new source uses the product User-Agent `Tidewatch/<version>`; none uses `browser`.
- **Enabling Business Wire** is a data change: an `UPDATE` of its `sources` row (`enabled`, `config.tokens`), not code.

#### Ingest runner and write path (`packages/ingest`)

- **Runner.** `runner:ingest`.
  - At start: runs left `running` more than 10 minutes are finished `failed`/`interrupted`; each enabled row is gated (a missing key or contact writes one `missing_secret` noop run and logs `collector_disabled`); then one timer per active source.
  - `sources` is re-read every 60 s, so disabling a row stops its timer within one refresh.
  - A run writes `source_runs` (`running` → `succeeded` | `noop` | `failed`, with `counts {fetched, new, duplicate, quarantined, bodies_fetched, bodies_fallback}`). `error` is a class name, never a message or URL. A 429 ends the run `noop`/`rate_limited`.
- **Bounded fetch.** One fetcher per process, using `ctx.http` only. Bodies are capped at 4 MiB, and a request has a 30 s deadline on the injected clock. Every non-sec.gov host gets 2 req/s, and a paused host fails fast. robots.txt: a 4xx means allow all; a 5xx or no answer means disallow all; 401/403 counts as a refusal.
- **Write path.** A batch and its cursor commit in one transaction, so a restart produces duplicates, never new rows. Per entry:
  - one `documents` row: title on one line with control characters removed, cut to 1,000 characters at a code-point boundary; NFC text with NUL removed;
  - one `document_versions` row holding the raw payload as an envelope `{content_type, encoding: json|utf8|base64, data}` with its SHA-256;
  - the §4.4 named-resolution candidates (`document_instruments`, `origin = alias`).
- **Dedup (ORCH-12, ingest review B1 fix `8235f31`).** Two gates:
  - The first is the `UNIQUE (canonical_url)`. The canonical URL has the scheme and host lower-cased, the default port, fragment and tracking parameters (`utm_*`, `fbclid`, `gclid`) removed, and the trailing slash normalised.
  - The second applies to a new **wire or media** document whose `title_hash` matches a document from **another** source published within 72 h **either side** of its own publication time. Such a document is stored `skipped`/`duplicate` with `duplicate_of` set to the earliest original, and is never triaged, extracted or scored. The `title_hash` is SHA-256 over the lower-cased title with whitespace collapsed and datelines and wire prefixes removed. The original review found the window one-sided from the new document's `published_at`.
  - Filings and exchange notices never dedupe by title.
- **Named resolution (§4.4), before any model call:**
  1. The issuer CIK (zero padding stripped) against `kind = 'cik'`.
  2. Exchange tags such as `(NASDAQ: NVDA)` and `(SET: PTT)`: `SET:` resolves to `<SYM>.BK@webull`, US tags to `<SYM>@webull`.
  3. `.BK` tokens, Binance pairs `…/THB` and `…/USDT` (to `@binance-th`), the SET `symbol` field and Finnhub `related`.
  4. `name`/`thai_name` aliases of at least 4 characters with word boundaries. Single-word aliases match only capitalised occurrences (R-SIG-5).

  A document with no hit still goes to triage.
- **CIK alias refresh.** Daily at 03:30 Bangkok, and at start when older than a day. It reads `company_tickers_exchange.json` and upserts `instrument_aliases(kind = 'cik', source = 'sec-company-tickers')` with `ON CONFLICT DO NOTHING`. The refresh instant lives in the `sec-edgar-8k` cursor (R-SIG-3). Dual-class tickers map `-` to `.` (BRK-B → BRK.B; ingest review item 4).
- **Quarantine.** An unstorable entry writes only `document_quarantine` and never aborts the run. A live EDGAR submission over 4 MiB is the ORCH-14 exception: it is stored `headline_only`, counted in `bodies_fallback`, and logged `ingest_fetch_failed` (`BodyTooLargeError`). An oversized **backfill** filing has no Atom entry and is still quarantined.

#### Signals pipeline (`packages/signals`)

```
stored ──triage──► triaged ──(material)──► extracted ──► scored ──► signalled
   │                  │ not material / routine            │ no candidate applies / no_instrument
   └─ duplicate       └─► skipped                         └─► skipped
quarantined ◄── any model stage on a contract failure (skip_reason = the stage)
```

- **Sweeps.** `runner:signals` sweeps every 10 s from the previous start.
  - Each sweep takes at most 20 unqueued documents newest-first (`published_at DESC`), with at most 2 in flight.
  - Each stage commits its rows, its `model_calls` row, the `model_spend_daily` upsert and the new `stage` in **one transaction**. No store call spans a model call, so a crash resumes from the last committed stage.
  - Failure backoff is 5 minutes to 1 hour, in memory (code-signals W2, `2b908c6`).
- **Stage reuse.** A stage result stored for `(document, stage, prompt version)` is reused at no charge, whichever model answered. BOT-D1 (found at S13 and fixed in `2b908c6`) was a stall: scoring read the extraction by the route's model id while the row was stored under the provider-reported model id. The read is now `readExtraction(documentId, promptVersion)`, newest row.
- **`decide()` port** (`decide/types.ts`) with two adapters behind one interface: Jev (`decide/jev.ts`) and the small LLM (`decide/small-llm.ts`, an OpenRouter chat completion).
  - `decide.contract.spec.ts` runs both adapters against recorded fixtures. Those fixtures are constructed from the documented shapes and the owner's probe answers (R-SIG-13).
  - The Jev question texts are asserted **byte-equal** to `tidewatch-specs/signals-ingest/jev-probe/*.questions.json` (FR-SIG-BRN-001). A one-character change fails three tests.
- **Triage (Jev).** `POST https://api.typesafe.ai/v1/systemone`, model `jev-1.13.0`, bearer key.
  - State: `{source, published_at, title, body: excerpt}`, where the excerpt is the first 32,000 characters (R-SIG-25).
  - Three questions: `is_material` (Noul), `event_type` (Choice over the 15 types) and `severity` (Score).
  - Gates: below the kind's `material_threshold` → `skipped`/`not_material`; `other` with severity under 1 → `skipped`/`routine`.
  - Structured (Binance TH) documents skip extraction.
- **Extraction (OpenRouter).** `POST https://openrouter.ai/api/v1/chat/completions`, model `anthropic/claude-haiku-5.5` (from `model_routes`).
  - System prompt `extraction.v1` with `cache_control: {type: 'ephemeral'}`.
  - User turn: `{title, published_at, source, body ≤ 12k tokens, alias_candidates}`.
  - `response_format: {type: 'json_schema', json_schema: {name: 'extraction_v1', strict: true, schema}}` with `provider: {require_parameters: true}`.
  - **`max_tokens` 2500 (`EXTRACTION_MAX_TOKENS`, ORCH-17).**
  - **No `temperature` (ORCH-16; also removed from the small-LLM adapter).** Determinism rests on strict structured output plus Ajv.
  - The request schema moves `maxLength`/`maxItems` into descriptions, because strict structured outputs refuse them. **Ajv** (strict mode, `allErrors`) enforces the full limits client-side on every reply: `why` ≤ 200, `key_facts` ≤ 8 of ≤ 160, `rationale` ≤ 900, `additionalProperties: false`.
  - An invalid reply is retried once with the error appended (`signals_extraction_invalid`, attempts 1 and 2), then quarantined `schema_invalid`. A 4xx other than 429 → `provider_rejected`.
  - The prompt asks for named companies and up to five implied ones, each with a one-sentence `why`. It never asks for a direction or a probability.
  - The prompt hash covers `{system, schema}` and did not change with ORCH-17 (`652f70db…`).
- **Name resolution (§4.9).** `ticker` (the `exchange` decides `.BK@webull`, `@webull` or `@binance-th`), else an exact case-insensitive `name`/`thai_name` match, else a row in `extraction_unresolved` (the SQL review list). No resolved candidate → `skipped`/`no_instrument`, with the facts kept.
- **Scoring (Jev), at most 12 candidates, alias-named first.**
  - Request 1 asks `<slug>_applies` for every candidate; under 0.6 → `outcome = not_relevant`.
  - Request 2 asks direction `{up, down, neutral}` and horizon `{intraday, days, weeks}` for the survivors only (PRD S5).
  - Direction (R-SIG-7): `neutral` iff `p_neutral ≥ 0.5`; else `up` iff `p_up ≥ p_down`, else `down`. `p` is the probability of the stored direction.
- **Impact (`scoring_versions` v1).**
  - `p_dir = p_up/(p_up+p_down)`.
  - `conviction = max(0, 2·p_dir − 1)·(1 − p_neutral)` for up, `max(0, 1 − 2·p_dir)·(1 − p_neutral)` for down, 0 for neutral.
  - `impact = conviction × severity/5 × novelty_w × freshness × credibility × mention_w`, rounded to 4 decimals.
  - `freshness = exp(−ln2·Δt/half_life(horizon))` at scoring time.
  - `novelty` is `first` unless a signal exists for the same `(instrument_id, event_type)` within 5 days.
  - `scoring.spec.ts` reproduces the PRD worked values exactly: 0.0124 (NVDA supply wire), 0.0907 (AMD) and 0.4224 (NVDA 8-K).
- **Route fallback.** After 15 minutes of continuous Jev 5xx, triage and scoring use the small LLM with `fallback_model_id` (`signals_route_fallback` at most once an hour). One Jev attempt every 5 minutes ends the fallback. Every row records the model that answered.
- **Start checks.**
  - `recordPromptVersions` fails the start if a prompt changed under an old version (`PromptVersionConflictError`).
  - A route or fallback without a valid `model_prices` row refuses the start (`RouteConfigError` `missing_price`/`missing_fallback_price`; code-signals W1).
  - A database that ran a pre-`2b908c6` image needs `DELETE FROM prompt_versions WHERE prompt_version='extraction.v1'`, because the old hash was `88d3faa7`. The owner's database never ran one.

#### Spend ledger and ceiling

- **Every model call writes `model_calls`** (`document_id`, `stage`, `provider`, `model_id`, `prompt_version`, tokens, `cost_usd`, `estimated`, `latency_ms`) and upserts `model_spend_daily(day_bkk, provider, model_id)` in the stage's transaction.
  - `cost_usd` is OpenRouter's `usage.cost` when present, else tokens × `model_prices` (Jev counts input tokens only).
  - `day_bkk` uses a fixed +07:00 offset.
- **Ceiling with reservations (R-SIG-33).** Before each call: today's recorded spend + the estimates of calls in flight + this call's estimate ≤ `MODEL_SPEND_DAILY_CEILING_USD` (default `1.00`). Check and reservation are one step, so two concurrent calls cannot overshoot together.
  - Over the ceiling, nothing is sent, the document is marked `queued_reason = ceiling`, and `signals_spend_ceiling_reached` is logged once per Bangkok day.
  - Nothing is dropped, and ingest keeps storing.
- **Failed calls (ORCH-13).**
  - An HTTP error answer is recorded at the reported cost, usually `0` with `estimated = true`.
  - A timeout or connection loss after sending is recorded at the estimate and counts toward the ceiling.
  - A failure before sending, a missing key and an abort are not recorded.
  - A malformed 200 answer is recorded at 0, a small under-count noted in review.
- **Queue reasons survive restarts (R-SIG-32).**
  - At start: `ceiling` marks clear when today's spend is under the ceiling (a same-day raise drains at once), and `missing_key` and `provider_unavailable` marks clear.
  - At runtime: `ceiling` clears at the next Bangkok day and drains newest-first; `provider_unavailable` clears after 60 s; `missing_key` waits for the next start.
  - 429 and 5xx are retried after 2, 4 and 8 s, then the document is marked `provider_unavailable`.
- **A missing key disables the provider at start** (`signals_model_disabled` once with `provider`, `variable`), and its stages queue `missing_key`.
- **Cost expectation (PRD):** about $0.18/day for triage and $0.35/day for extraction at roughly 1,900 documents/day. Observed on the preview: Bangkok day 2026-10-11 reached $0.258474 by 09:54Z (Jev 436 calls, $0.038150; OpenRouter 364 calls, $0.220324) and $0.641961 by 10:49Z.

#### The signal transaction and the publish

- **One transaction per document:** every surviving candidate becomes a `signals` row, the candidate's `outcome` becomes `signal`, and the document becomes `stage = signalled`. `UNIQUE (document_id, instrument_id)` holds.
- **Row contents:** `tier` is copied from the source; `scoring_version` is 1; the three model ids are stored; `prompt_version` is the extraction prompt version. For structured sources, `extraction_model_id` and `prompt_version` are `structured` (R-SIG-8).
- **Publish after commit.** Only after commit is each row logged `signals_emitted`, counted, and published by `publishSignal` to `sig:<instrument_id>` with the C-SIG-1 bytes. The channel comes from the message's own `instrument_id`, and a signal is never throttled or coalesced.
- **A failed publish** logs `signals_publish_failed` (`error_class`, under its own 30 s interval) and rolls nothing back. Nothing is replayed; consumers resync from REST.

#### Jobs (`run <job>`)

| Job | Lock | Behaviour |
|---|---|---|
| `source-run --source <code>` | `job:source-run`, budget `runner:ingest` | One collector pass for one source with a run row. It refuses (exit 1) while `runner:ingest` is held elsewhere, and finishes runs left `running` for more than 10 minutes first. |
| `source-backfill --source <sec-edgar-*> --from <date> --to <date>` | `job:source-backfill`, budget `runner:ingest` | Lists filings through EDGAR full-text search (`efts.sec.gov`), one day per query, and stores them like live entries. EDGAR only in this slice. |
| `signals-requeue --reason <schema_invalid\|contract_violation\|provider_rejected>` | `job:signals-requeue` | Moves quarantined documents with that reason back to `stored` in one transaction, clearing `skip_reason` and `queued_reason`. Finished stages are reused without a second charge. The CLI accepts six reasons, but the job refuses the ingest-time ones with exit 1. |
| `signals-eval [--set labelled-filings-v1]` | `job:signals-eval` | Rebuilds each labelled filing into the entry the collector would store and runs §4.4 resolution, triage, extraction and §4.9 resolution through the live routes, prices and ceiling, recording calls as `stage = eval`. It write-tests its output directory (`os.tmpdir()`, `/tmp` in the image) before any paid call. Stopped by the ceiling or a provider, it writes `complete: false` and exits 1. It spends money and is never part of `test`. The labelled set is not in the image (`**/fixtures` is excluded), so on a container it is copied in (`VERIFICATION.md` → "Running the evaluation on the preview"). |
| `list-refresh` (existing, slice 1) | `job:list-refresh` | Fills the S&P 500, Nasdaq-100 and SET lists. A fresh database needs it before resolution and the eval work. On the preview, 109 documents were skipped `no_instrument` before it ran, and it does not trigger the CIK alias refresh (both are follow-ups). |

#### Observability

- **Log events: 12, a closed set.** A source scan in each package's `logs.spec.ts` enforces it. Fields are snake_case, and `error_class` is a constructor name, never a message, URL, header, key or contact.

  | Event | Level |
  |---|---|
  | `ingest_run_finished` | info |
  | `ingest_fetch_failed` | warn |
  | `ingest_body_fallback` | warn, once per host per Bangkok day |
  | `ingest_document_quarantined` | warn |
  | `signals_document_skipped` | debug |
  | `signals_extraction_invalid` | warn |
  | `signals_spend_ceiling_reached` | warn, once per Bangkok day |
  | `signals_model_disabled` | warn, once |
  | `signals_route_fallback` | warn, at most hourly |
  | `signals_emitted` | info |
  | `signals_publish_failed` | warn, rate-limited |
  | `signals_stage_failed` | error |

  The existing `collector_disabled` gains the reasons `missing_contact` and `no_collector`.
- **Bot metrics: 9 series, closed label sets.** An unknown label throws `RangeError`.
  - Ingest:
    - `ingest_source_runs_total{source,status}`;
    - `ingest_documents_total{source,outcome}`;
    - `signals_ingest_stale{source}`, which is 1 for `stale` and `failing`.
  - Signals:
    - `signals_stage_total{stage,result}`;
    - `signals_model_calls_total{stage,provider}`;
    - `signals_model_spend_usd_today`, a gauge reset at the Bangkok day;
    - `signals_queue_depth{reason}`;
    - `signals_emitted_total{tier}`;
    - `signals_stage_duration_seconds{stage}`, a histogram.
  - The `source` label is limited to the ten `SOURCE_CODES`.
  - Scrape them inside the bot container with `wget -qO- http://127.0.0.1:9091/metrics`.
- **Stale-source taxonomy:**
  - `disabled`;
  - `missing_secret`;
  - `failing`: the latest finished run failed;
  - `fresh`: a `succeeded` or `noop` run, other than a `missing_secret` one, within 2 × `schedule_seconds`;
  - else `stale`.
- **Service:** `ws_messages_sent_total{type="signal"}`. No new log event.
- **`packages/signals/VERIFICATION.md`** holds the eight §8.5 queries, each under a fixed heading with one `sql` block, run on H by `verification-queries.int.spec.ts`:

  | Query | Answers |
  |---|---|
  | Kept-row ratio | BRN-012 |
  | Reject reasons | BRN-012 |
  | Quarantine ratio | E2E-002 (< 5%), BRN-012 |
  | Stale sources | E2E-002, BRN-012 |
  | Spend by day and model | E2E-002, E2E-005, BRN-012 |
  | Signals by tier and event type | E2E-002, BRN-012 |
  | Syndication check | E2E-003, BRN-012 |
  | Unresolved names | BRN-012 |

  It also holds a ninth query (the two-wire pair, for E2E-003), a capture script, and the eval procedure.

#### Environment (bot `loadConfig`; root files pass them as `${VAR:-}`)

| Variable | Default | When unset or empty |
|---|---|---|
| `JEV_API_KEY` | unset | Triage and scoring queue `missing_key`; `signals_model_disabled` once |
| `OPENROUTER_API_KEY` | unset | Extraction and the small-LLM fallback queue |
| `FINNHUB_API_KEY` | unset | `finnhub-company-news` runs `missing_secret` noops |
| `SET_MARKETPLACE_API_KEY` | unset | `set-notices` off (`missing_secret`) |
| `MODEL_SPEND_DAILY_CEILING_USD` | `1.00` | Empty or blank means `1.00`; a non-decimal value exits 1 with `must be a decimal number` |

- **The four keys are optional and gate quietly.** None stops `serve`.
- **`secretValues` masks five values:** the four keys and `TIDEWATCH_HTTP_CONTACT`.
- **`TIDEWATCH_HTTP_CONTACT`** (existing) must be e-mail-shaped for EDGAR: printable ASCII, ≤ 200 characters, one `@`. It is sent to sec.gov only. Wikipedia gets `Tidewatch/<version> (personal research)` unless the contact is URL-form (R-SIG-39).
- **`MARKET_DATA_COLLECTORS`** defaults to all thirteen names.

## Components

Angular (tidewatch-web, PR #10, head `534e140`, merge `c2a1b26`). No new component, route, stylesheet, token or icon; the cell uses the existing `table.css` classes. No mockup (PD7).

- **Row model** (`data/market-data.model.ts`, SW-1). `MarketWatchRow.signals` is `{ readonly today: number } | null`. The strict reader accepts `null` or an object whose `today` is a non-negative safe integer (other keys dropped). A missing key, or a negative, fractional, non-finite or string `today`, refuses the body, like every other field (MW-22).
- **Signals cell** (`feat-overview/market-watch-table.ts`, `util/row-view.ts`, SW-2). The `td` keeps `r num` in both states:
  - **0 or `null`:** the existing `aria-hidden` dash, the `td` takes `.faint` (`--text-3`), and the visually hidden words read *No signals today*.
  - **n ≥ 1:** plain digits in `--text` with hidden words completing "1 signal today" or "n signals today".
  - The header stays *Signals*. No hue, badge, icon, motion or live region (Quiet table, MW-23).
- **Stream frame** (`data/market-stream.model.ts`, SW-3). `parseStreamFrame` accepts `{"type":"signal","v":1,…}` as `SignalMessage {type:'signal', instrument_id, signal_id, created_at}`. `signal_id` must be a non-empty string of at most 64 characters, and `created_at` an instant. Anything else returns null.
- **Counting** (`feat-overview/util/apply-stream-message.ts`, `feat-overview/data/market-watch.service.ts`, SW-4…SW-7, SW-10). A `signal` raises a row's `signals.today` by one when all of these hold:
  - the row is listed and its `signals` is not `null`;
  - `created_at` falls on the **Bangkok day of the loaded body's `generated_at`**. The browser clock plays no part: no `Date.now()` in the counting path.
  - the `signal_id` has not been counted on that row since the last successful load.

  The rules around it:
  - Each row remembers at most 200 ids, and the oldest is forgotten.
  - Only a successful load empties the ids and moves the counting day. A failed reload keeps both (MW-20).
  - A signal triggers no reload, timer or request; the 5-minute reload (MW-12) resyncs.
  - After Bangkok midnight the cell keeps day D's count until the next successful load brings D+1: at most 5 minutes while reloads succeed. There is no midnight reload.
  - The signal path is pure.
- **Where it shows.** Only the Market watch section of Overview, for the user's watchlist rows. The Signals **page** (`/signals`) keeps the slice-0 `app-screen-placeholder` with "No signals yet" (slice 4).
- **Docs.** `DESIGN.md` §Table pattern *Columns* bullet and the accessibility "Market watch table" bullet (*No signals today*; "1 signal today" / "n signals today"). `README.md` no longer calls Signals a placeholder column. `CLAUDE.md` gains the Signals cell, Signals count, Once per id, Reset, Midnight and Signals e2e bullets, and the `data/testdata/` pin.

## Files touched

From the approved plans' Files lists, `state.json` step billets, review-fix scopes, and a listing of the merged bot packages' `src/`. No `git diff` was run for this document.

| Repo | Range (base..PR head) | Merge |
|---|---|---|
| tidewatch-migrations | `3ec60a7..dd7e150` | `e015a3a` |
| tidewatch-service | `77d8ebf..b9de179` | `2f9854f` |
| tidewatch-bot | `6b8cdb0..53cb76d` | `0d7be6d` |
| tidewatch-web | `31f9435..534e140` | `c2a1b26` |

### tidewatch-migrations (PR #7, https://github.com/tidewatch-labs/tidewatch-migrations/pull/7)
- `migrations/20261011020408_signals_ingest.sql` (created): migration H.
- `scripts/check-disposable-db.sh` (modified): H's lists, catalog, seeds, probes and round trips.
- `README.md`, `CLAUDE.md` (modified): H's objects, the ORCH-8 CHECK, seeds as data, the destructive down, the required version moved G → H with the anchored lookup.

### tidewatch-service (PR #8, https://github.com/tidewatch-labs/tidewatch-service/pull/8)
- **`internal/market`:**
  - `testdata/signals-message.v1.json` (created);
  - `signal_fixture_test.go` (created);
  - `bangkok.go`, `bangkok_test.go` (created);
  - `feed.go`, `feed_test.go` (modified: `SigChannel`, `ParseSignalHeader`, the exact-key and UTF-8 drops).
- **Schema pin:** `internal/platform/postgres/schema.go`, `internal/pgtest/migrate.go`, `scripts/integration-test.sh`, `test/integration/main_test.go`, `test/integration/ready_test.go` (modified).
- **Realtime:** `internal/services/realtime/hub.go`, `hub_test.go`, `ports.go`, `internal/observability/metrics/realtime.go`, `metrics_test.go`, `test/integration/realtime_test.go` (modified).
- **Market watch:** `internal/repository/postgres/marketwatch.go`, `marketwatch_test.go`; `internal/services/market/marketwatch.go`, `marketwatch_test.go`; `internal/handlers/marketwatch.go`, `marketwatch_test.go`; `test/integration/marketwatch_test.go` (modified).
- **Docs:** `README.md`, `CLAUDE.md` (modified).
- **Unchanged by design:** `router.go`, `pkg/apperror`, `internal/trading`, `internal/services/trading`, `internal/platform/redis`, `internal/repository/redis`, `protocol.go`, `subscriber.go`, `go.mod`/`go.sum`.

### tidewatch-bot (PR #7, https://github.com/tidewatch-labs/tidewatch-bot/pull/7)
- **`packages/ingest` (created).**
  - Scaffold: `package.json`, the tsconfigs, `vitest.config.mts`, `vitest.int.config.mts`.
  - Text primitives: `src/sources.ts`, `canonical-url.ts`, `title-hash.ts`, `text.ts`, `pdf.ts`.
  - Fetching: `robots.ts`, `fetch.ts`.
  - Collectors: `collectors/{types,api,binance-th-listings,set-notices,finnhub}.ts`, `collectors/edgar/{atom,submission,efts,company-tickers,collector}.ts`, `collectors/wire/{rss,page-fetch,collector}.ts`.
  - Store and write path: `store.ts`, `pg-store.ts`, `testing/memory-store.ts`, `runs.ts`, `documents.ts`, `resolution.ts`.
  - Runner and jobs: `registry.ts`, `runner.ts`, `metrics.ts`, `logs.ts`, `cik-refresh.ts`, `jobs.ts`, `index.ts`, `testing/index.ts`.
  - Unit specs beside the sources, and `pg-store.int.spec.ts`, `runner.int.spec.ts`.
  - Fixtures with a README: `sec-edgar`, `wire`, `binance-th`, `set-notices`, `finnhub`, `robots`, `pdf`.
- **`packages/signals` (created).**
  - `decide/{types,provider,jev,small-llm}.ts`.
  - Prompts: `prompts/{triage.v1,scoring.v1,extraction.v1,extraction-schema.v1,versions}.ts`.
  - Stages: `constants.ts`, `triage.ts`, `scoring.ts`, `impact.ts`, `openrouter.ts`, `extraction.ts`, `resolve-names.ts`.
  - Store, ledger and routes: `store.ts`, `pg-store.ts`, `testing/memory-store.ts`, `ledger.ts`, `routes.ts`, `prompt-versions.ts`.
  - Pipeline and runner: `pipeline.ts`, `publish.ts`, `metrics.ts`, `logs.ts`, `runner.ts`, `jobs.ts`, `eval.ts`, `index.ts`, `testing/index.ts`.
  - Specs, including `decide.contract.spec.ts`, `signals-message-fixture.spec.ts`, `labelled-set.spec.ts`, and the integration specs `pg-store.int.spec.ts`, `pipeline.int.spec.ts`, `verification-queries.int.spec.ts` and `runners.int.spec.ts`.
  - `VERIFICATION.md`.
  - Fixtures: `signals-message.v1.json`, `jev-probe`, `jev`, `openrouter`, `eval-mini`, and `labelled-filings-v1/{labels.json, filings, wires, review-note.txt}` (100 EDGAR filings and 20 PR Newswire items).
- **Existing packages (modified):**
  - `packages/shared/src/config.ts` and spec: five variables, thirteen collectors, five masked values.
  - `packages/market-data/src/transport/user-agents.ts`: new `SOURCE_NAMES`; the Wikipedia policy withholds an e-mail contact.
  - `packages/market-data/src/redis/contract.ts`, `publisher.ts`: the C-SIG-1 builder and `publishSignal`.
  - `packages/market-data/src/runtime/types.ts`, `index.ts`, `fixtures-format.spec.ts`.
  - Spec edits named by R-SIG-15: `transport/http.spec.ts`, `jobs/lists/sources.spec.ts`.
  - `packages/worker/src/{serve,jobs,cli,run}.ts` and their specs, `worker/package.json`, `worker/tsconfig.lib.json`.
- **Repo root (modified):** `Dockerfile` (eight dists; `/app/tmp` owned by `node`), `.env.example`, `tsconfig.json`, `pnpm-lock.yaml`, `scripts/sql-integration.sh` (asserts H and pins its SHA-256), `README.md`, `CLAUDE.md`.
- **Unchanged (stable-path guard):** `bots`, `sim`, `indicators`, the market-data transport `http.ts`, collectors, limits, core, db, status and the shared logger, pool and guard.

### tidewatch-web (PR #10, https://github.com/tidewatch-labs/tidewatch-web/pull/10)
- **Data:** `src/app/pages/workspace/data/market-data.model.ts`, `market-data.model.spec.ts`, `market-stream.model.ts`, `market-stream.model.spec.ts` (modified); `data/testdata/signals-message.v1.json` (created).
- **Overview:** `feat-overview/util/row-view.ts`, `row-view.spec.ts`, `market-watch-table.ts`, `market-watch-table.spec.ts`, `util/apply-stream-message.ts`, `apply-stream-message.spec.ts`, `data/market-watch.service.ts`, `market-watch.service.spec.ts` (modified).
- **End-to-end:** `e2e/src/support/market-watch.ts`, `e2e/src/market-watch.spec.ts`, `e2e/src/support/screens.ts` (modified).
- **Repo files:** `.prettierignore`, `DESIGN.md`, `README.md`, `CLAUDE.md` (modified).

### Workspace root (applied in place, not in any PR; ORCH-4)
- `/Users/maichinu/tidewatch/docker-compose.yaml`: five additive `${VAR:-}` lines for `tidewatch-bot`.
- `/Users/maichinu/tidewatch/.env.example`: five `KEY=` lines and comments, plus the ORCH-15 comment corrections.
- Hashes before and after are in `evidence/tidewatch-bot/S23/` and `evidence/tidewatch-bot/review-fix-r1-B/root-after-sha256.txt`.

**Not changed:**
- `documents/` (forbidden by the build prompt);
- `tidewatch-apis` (no route change);
- `tidewatch-specs` (input);
- `.forge/` preview definitions: no planner edited them; the orchestrator resynced the preview setup.

## Test plan

### Commands (all local; there is no CI, D4)

- **Migrations:** `make migrate-validate`; `make check-disposable-db` (1330 PASS / 0 FAIL).
- **Service:** `make ci` (vet, test-race, build; Docker-free) and `make test-integration TIDEWATCH_MIGRATIONS_DIR=<migrations checkout>`. No `--- SKIP` is allowed; verification greps `--- PASS: <Name> (`.
- **Bot:**
  - `pnpm install --frozen-lockfile && pnpm nx run-many -t lint test typecheck build`;
  - `TIDEWATCH_MIGRATIONS_DIR=<checkout> bash scripts/sql-integration.sh` (asserts H and its SHA-256; runs the ingest and signals integration specs);
  - `run signals-eval` only on a preview with keys.
- **Web:**
  - `pnpm nx run-many -t lint test build` (the web has no `typecheck` target);
  - the full Playwright suite against a preview (`pnpm nx e2e e2e` with `BASE_URL`; the live and pause gates off for P1).

### Named acceptance tests (do not rename)

- **Service:**
  - fixture and parsing: `TestSignalMessage_FixtureHash`, `TestParseSignalHeader`, `TestBangkokDayStart`, `TestKeys_ContractNames`;
  - hub and realtime: `TestHub_RefCount_SubscribesOncePerInstrument` (revised), `TestHub_Dispatch_SignalForwardedUnchanged`, `TestHub_Dispatch_SigDropsFromFixture`, `TestMetrics_RealtimeSeries_ClosedLabels` (9 labels), `TestRealtime_SignalForwarded`;
  - Market watch: `TestService_MarketWatch_SignalsToday`, `TestMarketWatchHandler_Get_Shape` (revised), `TestMarketWatchRepo_SignalsToday`, `TestMarketWatch_SignalsToday_BangkokDay`;
  - schema: `TestContract_RequiredSchemaVersion`, `TestReady_BotWatchSchema_NotReady` and the four existing `TestReady_*` schema tests on H's message.
- **Bot:** the exact Vitest titles of each plan step, asserted from the JSON report, for example:
  - `decide.contract.spec.ts`;
  - `scoring.spec.ts` (0.0124 / 0.0907 / 0.4224);
  - `inserts a document's signals with the candidate outcomes and stage signalled in one transaction`;
  - `publishes the C-SIG-1 message after commit and never rolls back on a failed publish`;
  - `reserves in-flight estimates so two concurrent calls cannot pass the ceiling together`;
  - `drains ceiling-queued documents at start when today's spend is under the new ceiling`;
  - `moves quarantined documents with the given reason back to stored, clearing skip_reason, as signals-requeue`;
  - the ingest and signals `logs.spec.ts` closed-set scans;
  - the no-network guard and `no-direct-network` scans in both packages.
- **Web:**
  - `market-data.model.spec.ts`, `row-view.spec.ts`, `market-watch-table.spec.ts` (0, null, 1, n);
  - `market-stream.model.spec.ts` (the C-SIG-1 pin, the example payloads, the five frame-level drops);
  - `apply-stream-message.spec.ts`, run under two host time zones including `TZ=America/New_York`;
  - `market-watch.service.spec.ts` (no reload, no browser clock, reset only on a successful load);
  - mocked `e2e/src/market-watch.spec.ts`, which sends the raw C-SIG-1 frames, plus the captures `market-watch-signals-{dark,light}-{390,1080}.png`.

### Reviews (code)

- **Service:**
  - code r1 APPROVED with 3 docs should-fix;
  - security r1 CHANGES REQUESTED (0 critical, 1 medium, 3 low). M1: `ParseSignalHeader` decoded keys case-insensitively, last key winning, while the browser reads exact keys. L1: invalid UTF-8 was forwarded.
  - fixed in `2fec95d` (migrations docs `dd7e150`);
  - security r2 and code r2 APPROVED;
  - doc nits in `b9de179`.
- **Bot:**
  - Round 1, split three ways:
    - code-signals CHANGES REQUESTED (1 blocking, 5 should-fix, 7 nits): BOT-D1, W1 missing price, W2 failure backoff, W3 failed-call accounting (ORCH-13), W4 eval output directory, W5 a live schema call;
    - code-ingest CHANGES REQUESTED (1 blocking, 7 should-fix, 5 nits): B1 the one-sided syndication window, unencoded Business Wire tokens, the publish log message, the CIK dual-class mapping, the stale-gauge query, docs, root comments, and EDGAR 4 MiB (ORCH-14);
    - security APPROVED (0 critical, 1 medium, 3 low): M1 pin the key hosts, L1 PDF bounds, L2 extraction.v2 data rule (a follow-up), L3 `/app/tmp` ownership.
  - Fix A `2b908c6` (signals package and Dockerfile) and fix B `8235f31` (ingest, market-data, docs, root comments).
  - All three r2 APPROVED; final doc nits in `d64e732`.
  - Deltas APPROVED: r3 `8ee0b71` (ORCH-16), r4 `f786102` (ORCH-17; worst-case output cost per call $0.00125), r5 `53cb76d` (ORCH-18; `eval.spec` 9/9).
- **Web:**
  - angular, security (0/0/0) and code r1 APPROVED at `3c4f3b2`;
  - a docs should-fix in `534e140`, code r2 APPROVED;
  - P3 design review APPROVED (0 blocking, 0 warnings, 5 advisories).

### Acceptance at merge (PRD §9; `verification.md`, read with ORCH-19)

| IDs | Status | Evidence / note |
|---|---|---|
| FR-SIG-MIG-001, MIG-002 | Verified | Harness 1330/0, with the ORCH-8 CHECK as the only deviation. Service pin and `TestReady_*`; bot harness on H (sha `a77fcf10…`); preview `/api/ready` 200 on H. |
| FR-SIG-ING-001…004, 006…011 | Verified | Unit and integration specs on H. On the preview, businesswire and accesswire had 0 runs. EDGAR ×3 succeeded on the first run. A forced CIK refresh wrote 516 aliases. Binance TH: 29 `noop` runs, unit spec only for a listing. Finnhub succeeded once its key was active (124 documents). ING-008 is read with ORCH-12 and is two-sided since `8235f31`. |
| FR-SIG-ING-005 | Verified (mocked) | Constructed fixtures only. A live check is impossible because the SET key is listed-company-only (A1 false). The preview row reads `missing_secret`. |
| FR-SIG-BRN-001…010 | Verified | Jev bodies byte-equal to the probes; 1,255 live Jev calls by 10:47Z. BRN-003 is read with ORCH-16/17; W5's live extraction call returned 200 twice ($0.00147). BRN-007: the 43 real C-SIG-1 publishes in the P2 capture. BRN-008: unit, integration and live E2E-005, read with ORCH-13. BRN-010: 12 events and 9 series. |
| FR-SIG-BRN-011 | Verified against **unreviewed** labels (A5) | Run 3 (bot `53cb76d`, `complete: true`): tracked 100% (100/100), all-labelled 89%, `event_type` 94%. See Eval below. |
| FR-SIG-SVC-001…003 | Verified | Named tests; the M1 exact-key decode in `2fec95d`; live forwarding seen in P2; NVDA 2 / AAPL 1 → 1 / 0 across 17:00Z in the fixed-clock test. |
| FR-SIG-WEB-001…003 | Verified | Unit specs. P1 Playwright: 1+689+3 passed, 4 gated skips, 0 failed; secret scan 0/328; tests 356, 357 and 414–417 passed. P3 design APPROVED. |
| FR-SIG-E2E-001 | Verified with exceptions | EDGAR ×3, GlobeNewswire and PR Newswire succeeded on their first run (08:54:32–33Z). Finnhub succeeded at 09:36:29Z, 20.5 min after its key became active. The first signal (09:36:40.690Z, NVDA@webull, `finnhub-company-news`, `m_and_a`) came 10 s after its document was first seen. **Exceptions:** binance-th-listings is healthy but only `noop` (no listing occurred); set-notices is `missing_secret` (A1). |
| FR-SIG-E2E-004 | Verified (fallback, web plan P2) | Service → web live with an orchestrator-injected C-SIG-1 on `sig:NVDA@webull`: published 10:37:30.630Z, frame received 10:37:30.682Z, NVDA 2 → 3 ("3 signals today"), no reload or navigation, `scrollY` 653 unchanged, `scrollLeft` 0. The bot → Redis leg is shown by 43 real publishes (10:01:00–10:04:41Z, equal to the 43 `signals` rows committed in the window), none for a watched row. **A full bot → web update on a watched row was not observed** in the 43-minute window. |
| FR-SIG-E2E-005 | Verified | Ceiling set to `0.01` at 10:47:59Z: 4 documents queued `ceiling`, `signals_queue_depth{reason="ceiling"} 4`, spend unchanged at 0.634558, exactly one `signals_spend_ceiling_reached`. Restored at 10:48:50Z: drained by 10:49:27Z on the same Bangkok day, spend 0.641961. Only the same-day branch ran live; the next-day branch is covered by the S17 integration spec. |
| FR-SIG-E2E-002 | **Unverified at merge** (ORCH-19) | 24 h soak not run. Pre-soak at 09:54Z: 7/7 enabled sources with secrets `fresh`; spend under $1.00; `within_bar` false for GlobeNewswire, 6-K, 8-K and Form 4 (see below); only the media tier had produced signals. |
| FR-SIG-E2E-003 | **Unverified at merge** (ORCH-19) | `syndication-check.tsv` had 0 rows, but no real two-wire pair was seen. An injected pair passed in the S17 integration spec on the harness database only. |
| FR-SIG-BRN-012 | **Unverified at merge** (ORCH-19) | All eight queries were captured once before the soak (about 09:54Z, `BRN-012-pre-soak/`). The post-soak re-capture is outstanding. |

Totals: **30 verified, 3 qualified (ING-005, E2E-001, E2E-004), 3 unverified at merge (E2E-002, E2E-003, BRN-012), 0 failed** out of 36 IDs.

### Eval (FR-SIG-BRN-011, `signals-eval-labelled-filings-v1.run3.json`)

| Run | Bot | Instrument resolution | `event_type` | Wires (feed-only) | Calls / cost |
|---|---|---|---|---|---|
| 1 | before ORCH-18 | 85% (85/100) | 94% | materiality 95%, `event_type` 60% | 196 / $0.108 |
| 2 (after a forced CIK refresh, 516 aliases) | before ORCH-18 | 89% (89/100) | 95% | as run 1 | $0.109 |
| **3** | `53cb76d` | **tracked 100% (100/100)**; all-labelled 89% (89/100; 11 filings name an untracked company) | **94% (94/100)** | materiality 95% (19/20), `event_type` 60% (12/20) | 199 / $0.116077 |

- **Run 1's misses.** Four came from missing CIK aliases on Nasdaq-100-only instruments: at first start the CIK refresh had run with only 11 instruments.
- **Run 2's misses.** Ten were labelled counterparties that are not Tidewatch instruments (CTVA, QRVO ×2, NFG, CRGY, UNF, OPCH, HESM, SNY, STRC), which led to ORCH-18. One was a real error: the FOXA filing also resolved MS. Under the containment rule extras are allowed, so it is not a miss.
- **The labelled set** (`packages/signals/fixtures/labelled-filings-v1`) holds 100 EDGAR 8-K/6-K filings and 20 PR Newswire feed items, fetched once in S20.
  - Labelled by claude-opus-5-5 in S21 and S22. Every entry is `review_status: "unreviewed"`, and the review is planned after the soak.
  - Reading basis: header, title, the first 6,000 characters of the primary document and of EX-99.1.
  - 10 of the 20 wire items are not in English, and only 1 wire item is labelled material, so the wire materiality figure says little about recall (A8).
  - `review-note.txt` lists the low-confidence labels.

### Preview pre-soak captures (`BRN-012-pre-soak/`, about 09:54Z)

- **Stale sources:**
  - `fresh`: binance-th-listings, finnhub-company-news, globenewswire, prnewswire (900 s on the preview), sec-edgar-6k/8k/form4;
  - `missing_secret`: set-notices;
  - `disabled`: accesswire, businesswire.
- **Quarantine ratio** (`document_quarantine` rows over 24 h; history rows stay after a requeue):

  | Source | Quarantined / stored |
  |---|---|
  | sec-edgar-6k | 78/100 |
  | sec-edgar-8k | 86/98 |
  | sec-edgar-form4 | 3/50 |
  | globenewswire | 2/21 |
  | finnhub-company-news | 2/124 |
  | prnewswire | 0/20 |

  - These rows are mostly the 138 PV-1 `provider_rejected` rows and the pre-ORCH-17 `schema_invalid` rows.
  - After the fixes, `signals-requeue` moved 138 `provider_rejected` and 30 `schema_invalid` documents back to `stored`. Of the 30, 28 passed extraction and 2 stayed quarantined: one still hit the 2500 cap, and one failed `maxLength` on a key fact.
  - The soak capture was therefore scheduled for **2026-10-12 ~10:00Z or later**, so the rolling 24 h window excludes the pre-fix rows.
- **Kept-row ratio** (current stages):
  - EDGAR documents were mostly `skipped` `no_instrument` (6-K 64, 8-K 65, Form 4 3) or `not_material`;
  - finnhub signalled 8 documents (kept ratio 0.065);
  - prnewswire and globenewswire had no kept rows.
- **Signals by tier and event type:** all media tier at that point (earnings 1, legal 2, m_and_a 2, product 2, supply 2).
- **Syndication check:** 0 rows.
- **Spend:** $0.258474 for the Bangkok day.

### Preview operational notes

- **Refreshes.** The preview was refreshed several times; each refresh changed the port.

  | Result | Preview | Bot |
  |---|---|---|
  | First signal, P1 | refresh 2, `:52646` | `8ee0b71` |
  | P2 | refresh 3, `:58693` | `f786102` |
  | BRN-011 run 3 | refresh 4, `:60014` | `53cb76d` |
  | E2E-005 | refreshes 5 and 6, `:60210` (ceiling 0.01) and `:60236` (restored) | `53cb76d` |

  At merge it ran migrations `dd7e150`, service `b9de179`, bot `53cb76d` and web `534e140` at `http://127.0.0.1:60236/`. Its teardown is not recorded.
- **Keys.** The owner added the Jev, OpenRouter and Finnhub keys to the Forge secrets file and left SET empty. A bot-only recreate kept a stale secrets snapshot, so a full `up --refresh` was needed.
- **Admin sign-in.** The owner signed in first with their own new admin password and shared it through a file that the orchestrator copied into `e2e/.auth/credentials.json` without reading or printing it. The forced-change journey was excluded, because the owner had spent it.
- **Timestamps.** `state.json` log entries stamped 13:20Z–17:30Z that sort before 09:50Z are Bangkok local times mislabelled Z. They are left as written. The preview acceptance times above come from evidence files.

### Manual reproduction (preview or owner stack with H and keys)

1. **Sources.** Run the "Stale sources" query in `packages/signals/VERIFICATION.md`. Every enabled source with its secret should read `fresh`.
2. **Count.** Open Overview. For a watchlist instrument with a signal today (Bangkok), the Signals cell reads "n signals today" and equals `SELECT count(*) FROM signals WHERE instrument_id = '<id>' AND created_at >= <Bangkok midnight>`.
3. **Live increment.** Publish a C-SIG-1 payload copied from the fixture's `examples[]`, with a fresh `signal_id` and `created_at` on the page's Bangkok day, to `sig:<visible id>`. The count goes up by one within 2 s with no reload. Re-publishing the same `signal_id` changes nothing.
4. **Ceiling.** Set `MODEL_SPEND_DAILY_CEILING_USD=0.01` and restart `tidewatch-bot`. Documents queue `ceiling` and one `signals_spend_ceiling_reached` appears. Restore the variable and restart: the queue drains the same Bangkok day while spend is under the ceiling.

## Open questions

### Unverified at merge (ORCH-19)

- **The 24 h soak** (FR-SIG-E2E-002, FR-SIG-E2E-003, FR-SIG-BRN-012): capture after 2026-10-12 ~10:00Z, with the eight queries and the pair query.
  - Open: whether the quarantine ratio falls under 5% once the pre-fix rows leave the window.
  - Open: whether filings, wires and exchange notices produce signals at all. Pre-soak, only the media tier had; most EDGAR documents ended `no_instrument` or `not_material`.
  - Open: whether a real two-wire pair occurs.
- **Full bot → web on a watched row** was never observed live. Only service → web (injected) and bot → Redis (real) were.
- **Labels are unreviewed** (A5). BRN-011 stands against model-written labels until the owner spot-checks them, starting with the low-confidence entries in `review-note.txt`.

### Owner actions and operations

- **Apply migration H** to the owner's own database, through the compose `migrate` container or `make migrate-up` in tidewatch-migrations with their `DATABASE_URL`. The merged service answers `/ready` 503 until then.
  - H is additive with no backfill.
  - Rollback is `make migrate-down`, which drops all 18 tables, including every document, signal and the spend ledger: destructive, owner-only.
- **Run `/forge-sync`** so local checkouts of the four repos reach the merge commits.
- **Five new bot variables:** set `JEV_API_KEY` and `OPENROUTER_API_KEY` (optionally `FINNHUB_API_KEY`; `SET_MARKETPLACE_API_KEY` is unobtainable) in `.env`, optionally `MODEL_SPEND_DAILY_CEILING_USD` (default `1.00`), then restart `tidewatch-bot`.
  - `TIDEWATCH_HTTP_CONTACT` must be an e-mail address, or EDGAR stays disabled.
  - Watch `signals_ingest_stale` and `signals_model_spend_usd_today`.
- **Rollout and rollback.** The planned order was H → service and bot (either order) → web.
  - Bot rollback: list the other eleven names in `MARKET_DATA_COLLECTORS` (drop `ingest` and `signals`) and restart. The tables stay.
  - Service rollback restores `signals: null`; web rollback restores the dash.
- **Recovery.**
  - Quarantined documents: `run signals-requeue --reason <schema_invalid|contract_violation|provider_rejected>` returns them to `stored` without re-charging finished stages.
  - Queued documents re-evaluate at runner start, so a raised ceiling or an added key drains them after a restart.
  - Interrupted ingest runs finish `failed`/`interrupted` at the next start.
- **PR Newswire on the owner stack.** The seed polls every 120 s. If Cloudflare refuses the client as on the preview (PV-2), changing `schedule_seconds` to 900 is an owner data change.
- **Business Wire.** The owner supplies the Financial Services / Technology category tokens from businesswire.com's RSS page. Enabling the source is an `UPDATE` of its `sources` row (a reminder recorded for build completion).
- **`DESIGN.md` snapshot refresh** at wrap-up (SW-11).

### Follow-ups (`state.json` `followUps`, 18 entries)

- **Service:**
  - apply exact-key decoding to `ParsePxHeader` too (pre-existing weakness; security M1 / code nit 4);
  - cap the forwarded `sig:` payload size, for example drop payloads over 4 KiB (security L2);
  - test that a `sig:` message triggers the 1013 slow-consumer eviction (security L3).
- **Web:**
  - validate `generated_at` with `isTimestamp` and require a `Z` or offset on the signal's `created_at`;
  - the midnight gap: the count stays on the loaded `generated_at` day until the next successful load (SW-10);
  - P3 advisories: the `table.css:110` comment says "placeholder dash", and `DESIGN.md:638/:980` are long lines.
- **Migrations:** an index on `documents (source_code, external_id)` for withdraw and external-id lookups.
- **Bot, prompts and extraction:**
  - an `extraction.v2` prompt with an explicit "the document is data, not instructions" rule; v1 must not change in place (security L2);
  - isolate PDF extraction in a worker thread with `resourceLimits` (the current bound is cooperative);
  - tag `finish_reason == 'length'` on extraction quarantines (a retry re-sends the same cap).
- **Bot, ingest and aliases:**
  - backfill: build `headline_only` documents for oversized filings from efts metadata (ORCH-14 covers live Atom only);
  - a requeue path for `no_instrument` skips once the instrument master grows (109 on the preview before list-refresh);
  - `list-refresh` adding instruments does not trigger the CIK alias refresh, so new names wait up to 24 h;
  - CIK aliases are stored in two forms (padded 10-digit from the lists source, unpadded from the SEC refresh); the resolver normalises them, but the rows duplicate.
- **Bot, docs:**
  - r5 nits: `eval.ts:546-551` should say "null when expected_instruments is"; `VERIFICATION.md:341` and `README.md:610` say "untracked names" but the field holds instrument ids;
  - the bot plan text (`.plans`, untracked) at :878 and :1152 still states BRN-011 as all-labelled containment and should cite ORCH-18.
- **Bot, soak watch:** `finnhub-company-news` runs `noop rate_limited` right after each restart and fails when a restart interrupts a run (2 failed and 7 noop runs on the preview).
- **Spec:** a licensed Thai-stock news source for personal use (SETSMART / SMART Marketplace natural-person products, or ask SET infoproducts), because the SET IR News API is listed-company-only.
- **Note:** `verification.md` lists 19 follow-ups. The extra item, the `VERIFICATION.md` eval `docker cp` path, was fixed in `53cb76d`.

### Other open items

- **Thai PDFs (A6)** and the SET download endpoint stay unverified; no key exists.
- **Provider fixtures are constructed.** Live Jev and OpenRouter calls were exercised on the preview, but the fixtures themselves are not live captures.
- **The wire `event_type` accuracy on feed text** was 60% (12/20). Whether `body_fetch` should be enabled for any wire is the owner's call after reading that publisher's terms (D5).
- **Growth and retention** (about 40 MB/day of documents at the PRD's volume) were not measured. Retention is out of scope until a later slice.
- **Next consumers:** slice 4 (the Signals page) reads `signals`, `documents` and `extractions`; slice 6's scout reads `signals`; spec 3b adds GDELT sources and the context layer to the same registry.

## Cross-cutting links

- [[centralized-migrations]]: migration H `20261011020408`, the required-schema-version contract moved G → H, the ORCH-8 CHECK and the destructive down.
- [[instrument-master]]: `instrument_aliases` read for the first time (CIK, tickers, names, `thai_name`), the daily CIK refresh, and `SYMBOL@venue` candidates.
- [[market-data-worker]]: the `ingest` and `signals` runners (12th and 13th `COLLECTOR_NAMES`), new jobs, the `SERVE_POOL_MAX` 12 check, User-Agents and the sec.gov contact rule.
- [[redis-market-contract]]: the new `sig:<instrument_id>` channel and the C-SIG-1 message beside `px:*`.
- [[realtime-websocket]]: the `signal` frame on `/ws`, the dual-prefix desired set, the exact-key header drops and `ws_messages_sent_total{type="signal"}`.
- [[market-data]]: the Market watch row's `signals.today` and the web Signals cell.
- [[design-system-decisions]]: the Signals cell dash/count states, Quiet table (MW-23) and the hidden-words rule.
- [[bot-watch-verdicts]]: the byte-pinned shared-fixture pattern (C11) that C-SIG-1 follows.
- [[decision-record]]: `decisions.signal_ids[]` will reference `signals.signal_id` from slice 6; unchanged here.
- [[forge-preview-gateway]]: the isolated preview, its refreshes, keys in the Forge secrets file and the owner-first admin sign-in.
- [[zone-transition-bot]] and [[bot-activity]]: the earlier "merge before verification" precedent (slice 2b) that ORCH-19 follows.
