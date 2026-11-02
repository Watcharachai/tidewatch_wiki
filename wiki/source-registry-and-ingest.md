# Source registry and ingest (`sources`, `documents`, `packages/ingest`)

**Summary**: Since slice 3a (merged 2026-10-11), the `sources` table is the registry of every feed Tidewatch reads. Each row records the feed's kind and tier, its fetch method, schedule, enabled flag and `config`, so enabling, disabling or rescheduling a source is a data change, not a code change. Migration H seeds ten rows: SEC EDGAR 8-K, 6-K and Form 4; PR Newswire and GlobeNewswire feed text; Binance TH listings; key-gated SET notices and Finnhub news; and Business Wire and AccessWire, both seeded disabled. Eight are enabled. The bot's `runner:ingest` polls each enabled row and records a `source_runs` row per pass. It stores deduplicated `documents` with their raw payloads, and resolves named instrument candidates from `instrument_aliases` before any model call. An entry it cannot store is quarantined, never dropped silently. What happens to a stored document next is on [[signals-pipeline]]. Since the signals page (slice 4, 2026-10-12), the service exposes the registry read-only as `GET /sources`, without URLs or `config`, and the Signals page draws one filter chip per publisher from it. **Since signals context (migration N, merged 2026-10-30), the registry has 13 rows.** N adds two GDELT GKG streams (`gdelt-gkg-en`, `gdelt-gkg-translation`) as their own collector family under `runner:ingest`, with a keep gate whose rules are database rows (see [[gdelt-gkg-ingest]]). It also adds `finnhub-earnings-calendar`, which the `context` runner owns, not ingest (see [[event-calendar]]). Company news and the earnings refresh now share one process-wide 50-per-minute Finnhub budget.

**Sources**: `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-30-signals-context.md` (the three N rows, the GDELT family and the shared Finnhub budget only)

**Last updated**: 2026-10-31

---

## Why primary sources, and why feed text for wires

- **D1. Primary sources now.** Filings, wires and exchange notices come first. GDELT is spec 3b, a context layer for the slice-6 scout, and will be added to the same registry. (It was: see "The three context sources" below.)
- **D4. Full text for primary sources, headline-only for media.**
- **D5. Feed text only for every wire** (`config.body_fetch = false`, a seed value). PR Newswire's terms prohibit automated retrieval and data mining of its site. Business Wire's site refuses non-browser clients, and its terms prohibit storing or copying content. A browser User-Agent to get past a refusal was rejected outright. The page-fetch path exists, gated by that seed value. Whether to enable `body_fetch` for any wire is the owner's call after reading that publisher's terms. Feed-text `event_type` accuracy was only 60% (12/20) in the eval.

(source: raw/2026-10-11-signals-ingest.md §Concept, Chosen design; §Open questions, Other open items)

## The ten seeded sources

| `source_code` | Kind / tier, fetch | Schedule | Enabled | Body | Gate and terms |
|---|---|---|---|---|---|
| `sec-edgar-8k`, `sec-edgar-6k`, `sec-edgar-form4` | filing / filing, `atom` (`browse-edgar?action=getcurrent&type=<8-K\|6-K\|4>&output=atom&count=100`) | 60 s | yes | `full`: the primary document plus `EX-99*` from the complete submission `.txt`; over 4 MiB, `headline_only` from the Atom entry (ORCH-14) | Needs an e-mail-form `TIDEWATCH_HTTP_CONTACT`, else `collector_disabled` `missing_contact`. SEC fair access: `Tidewatch/<version> <contact>`, gzip, at most 10 req/s and 4 in flight across the process, and a 10-minute pause on 403/429. Filings are public domain. |
| `globenewswire` | wire / wire, `rss` ("News about Public Companies") | 120 s | **yes** (ORCH-6) | `feed_only` | `www.globenewswire.com` refuses non-browser clients, so no page is fetched. The RSS host's robots.txt does not disallow `/RssFeed/`. |
| `prnewswire` | wire / wire, `rss` ("All News Releases") | 120 s seeded | yes | `feed_only` | Its terms prohibit automated retrieval of the site; robots.txt allows `/rss/`. Cloudflare refused the Node client after the first request on the preview (PV-2). |
| `businesswire` | wire / wire, `rss` (one request per URL-encoded `?rss=<token>`) | 120 s | **no**, `tokens []` | `feed_only` | Disabled **pending category tokens**. The all-news token answers "deactivated by the administrator", and the token list is on a site that refuses the product client. Its fixtures are constructed. |
| `accesswire` | wire / wire, `rss` | 300 s | **no** | none | No public feed (`/rss` is the company blog, `/rss2` is key-gated, robots.txt disallows both). No collector (`collector_disabled` `no_collector`). |
| `set-notices` | exchange / exchange, `json` (SET Smart Marketplace IR news) | 300 s | yes, key-gated | `headline_only` until `config.download_url_template` is set (R-SIG-10). PDFs via `unpdf`, bounded to 10 s, 100 pages and 1,000,000 characters. | `SET_MARKETPLACE_API_KEY` in the `api-key` header, sent only to the pinned host. **An individual cannot obtain the key (A1 false)**, so the source writes `missing_secret` noop runs. `deletedNews` withdraws a stored notice (`skip_reason = withdrawn`). |
| `binance-th-listings` | exchange / exchange, `poll` (`api.binance.th/api/v1/exchangeInfo`) | 300 s | yes | structured and synthesised; no LLM | A new symbol is a listing. `TRADING` → `BREAK`/`HALT` is a halt, and back is a resumption. The first run stores a baseline only. |
| `finnhub-company-news` | media / media, `json` (`finnhub.io/api/v1/company-news`) | 900 s | yes, key-gated | `feed_only` (the summary), else `headline_only`; the article `url` is stored, never fetched | `FINNHUB_API_KEY` in `X-Finnhub-Token`, sent only to the pinned `finnhub.io`. Personal-use plan. At most 700 symbols per run at no more than 50 calls/min: watchlist US tickers first, then US list members. |

- **Credibility by tier:** filing 1.00, exchange 0.95, wire 0.85 and media 0.60. These feed the impact formula (see [[signals-pipeline]]).
- **Pinned hosts (security M1, `8235f31`).** Keys go only to `finnhub.io` and `marketplace.set.or.th`, pinned in `packages/ingest/src/collectors/api.ts`. A `sources.url` pointing elsewhere fails the run with `SourceConfigError`.
- **User-Agents.** Every new source uses the product User-Agent `Tidewatch/<version>`; none uses `browser`.
- **Seeds are data.** The rows are in migration H, so a later change to a seed is a data migration (see [[centralized-migrations]]). Enabling Business Wire is an `UPDATE` of its row (`enabled`, `config.tokens`). On the owner stack, polling PR Newswire every 900 s, as on the preview, would be an owner data change (`schedule_seconds`).

(source: raw/2026-10-11-signals-ingest.md §API, Source registry: the ten seeded rows; §Database, Seeds; §Concept, ORCH-6 and Spec assumption A1; §Open questions, Owner actions)

## The three context sources (migration N, signals context, 2026-10-30)

| `source_code` | Kind / tier, fetch | Schedule | Config | Owner |
|---|---|---|---|---|
| `gdelt-gkg-en` | media / media, `gdelt`, publisher 'GDELT Project', `https://data.gdeltproject.org/gdeltv2/lastupdate.txt` | 300 s | `stream`, `missing_retry_hours` 6, `max_zip_bytes` 64 MiB, `max_inflated_bytes` 256 MiB, `quarantine_ratio_pct` 5, `quarantine_min_rows` 100 | `runner:ingest` |
| `gdelt-gkg-translation` | the same, on `lastupdate-translation.txt` | 300 s | the same | `runner:ingest` |
| `finnhub-earnings-calendar` | media / media, `json`, publisher 'Finnhub', `https://finnhub.io/api/v1/calendar/earnings` | 86,400 s | `key_variable` `FINNHUB_API_KEY`, `days_back` 7, `days_ahead` 60, `owner` `context` | the `context` runner |

- **Credibility** 0.60 for both GDELT rows (the media tier). No GDELT article gets a model call (a spec non-goal).
- **The GDELT family** is its own registry family in `packages/ingest/src/collectors/gdelt/`. Per window it commits mentions (`gkg_mentions`), `source_files`, quarantine rows and its cursor in one transaction. The coverage signals' synthetic documents come from the `context` runner instead (see [[context-features-and-coverage-signals]]). The collector, keep gate, bounds and measured volumes are on [[gdelt-gkg-ingest]].
- **The calendar source is owned by `context`** ("registry: calendar source is owned by context"). Its runs land in `source_runs` like any other (see [[event-calendar]]).
- **The shared Finnhub budget.** `collectors/finnhub-budget.ts` holds one process-wide 50-per-minute budget, keyed on the clock and using the `finnhub-company-news` row's `per_minute`. Company news and the earnings refresh both draw from it ("finnhub: company news and the earnings refresh share one budget"). Follow-up: fall back to `FINNHUB_CALLS_PER_MINUTE` on a broken news config.
- **Thirteen `SOURCE_CODES`.** The stale gauge now covers thirteen sources ("ingest: stale gauge covers thirteen sources").
- **`GET /sources`** lists N's three rows after `finnhub-company-news`, in the media group, with no URL, host, `config` key or key variable (see [[signals-read-api]]). On the Signals page they add one *GDELT Project* chip; the calendar row reuses *Finnhub*.
- **Bot versions must weigh them.** After N, a config's `source_weights` must list all 13 sources. Re-posting a pre-N config without them is `400 config.source_weights missing` (see [[bot-versions-and-runs]]).
- **Seeds are data.** A change to these rows is a new data migration, never an edit of N (see [[centralized-migrations]]).

(source: raw/2026-10-30-signals-context.md §Database, Three sources rows; §Concept, How it runs, 1. GDELT collector and 4. Calendar; §API, 2. `GET /sources`; §Components, Signals page; §Test plan, Ingest and Calendar titles; §Concept, Runtime counts; §Open questions, Smaller recorded follow-ups)

## Tables (migration H)

Eight of H's 18 tables belong to ingest. They are listed in H's order:
- **Sources and runs:** `sources`, `source_cursors`, `source_files` and `source_runs`.
- **Documents:** `documents`, `document_versions`, `document_instruments` and `document_quarantine`.

```sql
-- documents (excerpt)
canonical_url text NOT NULL, title_hash text NOT NULL CHECK (title_hash ~ '^[0-9a-f]{64}$'),
body_status text NOT NULL CHECK (body_status IN ('full', 'feed_only', 'headline_only')),
issuer_cik text CHECK (issuer_cik ~ '^[0-9]{1,10}$'), duplicate_of uuid REFERENCES documents (document_id),
stage text NOT NULL DEFAULT 'stored'
  CHECK (stage IN ('stored', 'triaged', 'extracted', 'scored', 'signalled', 'skipped', 'quarantined')),
UNIQUE (canonical_url)
```

- The `stage`, `skip_reason` and `queued_reason` columns drive the signals pipeline. The ORCH-8 CHECK that lets a quarantined document name its stage is on [[centralized-migrations]].
- An **ingest-time** quarantine (unparseable, missing fields, oversized body) writes only `document_quarantine` (`stage = 'ingest'`, `document_id` NULL) and creates no `documents` row. There is no `ingest` value for `skip_reason`.
- Indexes serving ingest: `source_runs_source_started_idx`, `documents_title_hash_published_idx`, `documents_stage_published_idx`, `document_versions_document_idx` and `document_quarantine_created_idx`.
- **Growth (PRD §5.3, no retention this slice).** About 1,900 documents/day at about 10 KB each is roughly 40 MB/day for `documents` plus `document_versions`, about 15 GB/year before TOAST. None of this was measured on the preview.

(source: raw/2026-10-11-signals-ingest.md §Database)

## The ingest runner

- **Start.** `runner:ingest` first finishes runs left `running` for more than 10 minutes as `failed`/`interrupted`. It then gates each enabled row: a missing key or contact writes one `missing_secret` noop run and logs `collector_disabled`. Finally it starts one timer per active source.
- **Live registry.** `sources` is re-read every 60 s, so disabling a row stops its timer within one refresh.
- **Runs.** Each pass writes a `source_runs` row (`running` → `succeeded` | `noop` | `failed`) with `counts {fetched, new, duplicate, quarantined, bodies_fetched, bodies_fallback}`. `error` is a class name, never a message or URL. A 429 ends the run `noop`/`rate_limited`.
- **Bounded fetch.** One fetcher per process uses `ctx.http` only. Bodies are capped at 4 MiB, and a request has a 30 s deadline on the injected clock. Every host other than sec.gov gets 2 req/s, and a paused host fails fast. For robots.txt, a 4xx means allow all, a 5xx or no answer means disallow all, and 401/403 counts as a refusal.

(source: raw/2026-10-11-signals-ingest.md §API, Ingest runner and write path)

## Write path

A batch and its cursor commit in **one transaction**, so a restart produces duplicates, never new rows. Each entry writes:
- one `documents` row, with the title on one line, control characters removed and the length cut to 1,000 characters at a code-point boundary, and NFC text with NUL removed;
- one `document_versions` row holding the raw payload as an envelope `{content_type, encoding: json|utf8|base64, data}` with its SHA-256;
- the named-resolution candidates (`document_instruments`, `origin = alias`).

(source: raw/2026-10-11-signals-ingest.md §API, Write path)

## Dedup (ORCH-12)

There are two gates:

1. **`UNIQUE (canonical_url)`.** The canonical URL lower-cases the scheme and host, removes the default port, the fragment and tracking parameters (`utm_*`, `fbclid`, `gclid`), and normalises the trailing slash.
2. **Syndication by title.** This gate applies only to a new **wire or media** document. If its `title_hash` matches a document from **another** source published within 72 h **either side** of its own publication time, it is stored `skipped`/`duplicate` with `duplicate_of` set to the earliest original. It is never triaged, extracted or scored. The `title_hash` is SHA-256 over the lower-cased title with whitespace collapsed and datelines and wire prefixes removed.

- ORCH-12 narrows PRD §4.3: same-source repeats are kept, and **filings and exchange notices never dedupe by title**.
- The first code review found the window one-sided (B1); it is two-sided since `8235f31`.
- A live two-wire pair was never seen on the preview, so FR-SIG-E2E-003 is unverified at merge. An injected pair passed in the integration spec.

(source: raw/2026-10-11-signals-ingest.md §API, Dedup; §Concept, ORCH-12; §Test plan, Acceptance at merge)

## Named resolution (§4.4), before any model call

1. The issuer CIK, with zero padding stripped, against `kind = 'cik'`.
2. Exchange tags such as `(NASDAQ: NVDA)` and `(SET: PTT)`. `SET:` resolves to `<SYM>.BK@webull`, and US tags to `<SYM>@webull`.
3. `.BK` tokens, Binance pairs `…/THB` and `…/USDT` (to `@binance-th`), the SET `symbol` field and Finnhub `related`.
4. `name`/`thai_name` aliases of at least 4 characters, with word boundaries. Single-word aliases match only capitalised occurrences (R-SIG-5).

A document with no hit still goes to triage. Extraction may name more instruments later (see [[signals-pipeline]]). This was the first time `instrument_aliases` was read by alias or CIK; the alias model is on [[instrument-master]] (source: raw/2026-10-11-signals-ingest.md §API, Named resolution; §Concept, Problem).

## CIK alias refresh

- The refresh runs daily at 03:30 Bangkok, and at start when the last one is older than a day.
- It reads SEC's `company_tickers_exchange.json` and upserts `instrument_aliases(kind = 'cik', source = 'sec-company-tickers')` with `ON CONFLICT DO NOTHING`. The refresh instant lives in the `sec-edgar-8k` cursor (R-SIG-3).
- Dual-class tickers map `-` to `.` (BRK-B → BRK.B).
- A forced refresh on the preview wrote 516 aliases. At first start it had run with only 11 instruments, which caused four of eval run 1's misses.

(source: raw/2026-10-11-signals-ingest.md §API, CIK alias refresh; §Test plan, Eval)

## Quarantine

An unstorable entry writes only `document_quarantine` and never aborts the run. The ORCH-14 exception: a **live** EDGAR submission over 4 MiB is stored `headline_only` from its Atom entry, counted in `bodies_fallback` and logged `ingest_fetch_failed` (`BodyTooLargeError`). An oversized **backfill** filing has no Atom entry, so it is still quarantined (source: raw/2026-10-11-signals-ingest.md §API, Quarantine; §Concept, ORCH-14).

## Jobs

| Job | Lock | Behaviour |
|---|---|---|
| `source-run --source <code>` | `job:source-run`, budget `runner:ingest` | One collector pass for one source, with a run row. It refuses (exit 1) while `runner:ingest` is held elsewhere, and first finishes runs left `running` for more than 10 minutes. |
| `source-backfill --source <sec-edgar-*> --from <date> --to <date>` | `job:source-backfill`, budget `runner:ingest` | Lists filings through EDGAR full-text search (`efts.sec.gov`), one day per query, and stores them like live entries. EDGAR only in this slice. |
| `list-refresh` (existing) | `job:list-refresh` | A fresh database needs it before resolution works: on the preview, 109 documents were skipped `no_instrument` before it ran. It does not trigger the CIK refresh. |

(source: raw/2026-10-11-signals-ingest.md §API, Jobs)

## Observability

- **Ingest log events** (part of the closed set of 12): `ingest_run_finished` (info), `ingest_fetch_failed` (warn), `ingest_body_fallback` (warn, once per host per Bangkok day) and `ingest_document_quarantined` (warn). The existing `collector_disabled` gains the reasons `missing_contact` and `no_collector`.
- **Ingest metrics:** `ingest_source_runs_total{source,status}`, `ingest_documents_total{source,outcome}` and `signals_ingest_stale{source}` (1 for `stale` and `failing`). The `source` label is limited to the ten `SOURCE_CODES`.
- **Stale-source taxonomy.** A source is `disabled`, `missing_secret`, or `failing` (the latest finished run failed). It is `fresh` when a `succeeded` or `noop` run, other than a `missing_secret` one, finished within 2 × `schedule_seconds`. Otherwise it is `stale`. The "Stale sources" query in `packages/signals/VERIFICATION.md` reads it.

(source: raw/2026-10-11-signals-ingest.md §API, Observability)

## Environment

- **`FINNHUB_API_KEY`** unset: `finnhub-company-news` runs `missing_secret` noops.
- **`SET_MARKETPLACE_API_KEY`** unset: `set-notices` is off (`missing_secret`). The key cannot be obtained by an individual.
- **`TIDEWATCH_HTTP_CONTACT`** (existing) must be e-mail-shaped for EDGAR: printable ASCII, at most 200 characters, one `@`. It is sent to sec.gov only (ORCH-11), and `secretValues` masks it (ORCH-9). Wikipedia now gets `Tidewatch/<version> (personal research)` unless the contact is URL-form (R-SIG-39).
- None of these stops `serve`. The model keys are on [[model-routes-and-spend]].

(source: raw/2026-10-11-signals-ingest.md §API, Environment; §Concept, ORCH-9 and ORCH-11)

## Observed on the preview

- EDGAR ×3, GlobeNewswire and PR Newswire succeeded on their first run (08:54:32–33Z). Finnhub succeeded 20.5 minutes after its key became active and stored 124 documents.
- `binance-th-listings` was healthy but ran only `noop` (no listing occurred). `set-notices` read `missing_secret`, and `businesswire` and `accesswire` had 0 runs.
- PR Newswire's Cloudflare front refused the Node client after the first request (10 failed runs), so its schedule was moved to 900 s on the preview only (PV-2).
- `finnhub-company-news` runs `noop rate_limited` right after each restart, and fails when a restart interrupts a run (2 failed and 7 noop runs). This is on the soak watch list.

(source: raw/2026-10-11-signals-ingest.md §Test plan, Acceptance at merge and Preview pre-soak captures; §Concept, PV-2; §Open questions, Follow-ups)

## Read back by the Signals page (slice 4)

- **`GET /sources`** (tidewatch-service PR #10) answers `{items: [{source_code, publisher, kind, tier, enabled}]}`. It never returns `url` or `config` (`TestSources_List_NoURLOrConfig`). Rows are ordered by tier (filing, wire, exchange, media, account), then code (R6). Any query parameter is a 400. See [[signals-read-api]].
- **`config.structured`** is exposed in a signal's detail as `structured`, true for Binance TH listings. The detail's Model view then reads "Structured source · no model".
- **Source chips (SP-W-8).**
  - There is one chip per `publisher`, labelled with the registry text. So it reads "Stock Exchange of Thailand" where the mockup said "SET", and the three EDGAR rows fold into *SEC EDGAR*.
  - Disabled sources stay toggleable, with the title "Not reading yet".
  - The *Account* provenance chip is disabled ("No account sources yet") while no account source exists.
  - Unknown codes in a URL or stored filter are dropped once `/sources` answers.
  - A partly selected publisher, for example from a stored list that predates a newly registered code, is widened to all of its current codes (ORCH-12; the owner may overrule).
- **Trust bars are not credibility.** The Signals page draws trust bars from a closed display map by tier (filing 5, exchange 4, wire 4, media 3, account 2). The impact formula's credibility (filing 1.00, exchange 0.95, wire 0.85, media 0.60) is unchanged.
- **Add source.** The page's *Add source* dialog reads "Arrives with user sources." and names the seeded primary sources. Nothing is written.
- **What the preview produced (FR-SP-E2E-003, unverified).** On 2026-10-12, the preview's two signals were both media (Finnhub) rows. No filing, wire or structured-source signal existed. EDGAR returned `nothing_new` on a Sunday night in New York. The wires were not material or named no instrument. Binance TH had `nothing_new`, and `set-notices` was disabled.

(source: raw/2026-10-12-signals-page.md §API, Service routes and `SignalDetail`; §Components, `app-signals-filters`; §Concept, Plan resolutions, Service R6 and Web SP-W-8; §Concept, ORCH-12; §Concept, Accepted defaults; §Test plan, Acceptance status)

## Follow-ups

- An index on `documents (source_code, external_id)` for withdraw and external-id lookups (migrations).
- Backfill: build `headline_only` documents for oversized filings from efts metadata. ORCH-14 covers live Atom entries only.
- A requeue path for `no_instrument` skips once the instrument master grows.
- `list-refresh` adding instruments does not trigger the CIK alias refresh, so new names wait up to 24 h.
- CIK aliases are stored in two forms: padded 10-digit from the lists source, and unpadded from the SEC refresh. The resolver normalises them, but the rows duplicate.
- Isolate PDF extraction in a worker thread with `resourceLimits`; the current bound is cooperative. Thai PDFs (A6) and the SET download endpoint stay unverified, because no key exists.
- A follow-up spec for a licensed Thai-stock news source for personal use, because the SET IR News API is listed-company-only.

(source: raw/2026-10-11-signals-ingest.md §Open questions, Follow-ups and Other open items)

## Related pages

- [[signals-ingest]]: the slice-3a overview and acceptance
- [[signals-pipeline]]: what happens to a stored document: triage, extraction, scoring
- [[instrument-master]]: the aliases, CIKs and `SYMBOL@venue` ids that resolution targets
- [[centralized-migrations]]: migration H, its seeds and the ORCH-8 CHECK
- [[market-data-worker]]: the `serve` process that runs `runner:ingest`, and the User-Agent table
- [[model-routes-and-spend]]: the provider keys and the spend ledger
- [[signals-read-api]]: `GET /sources` and the `structured` flag in a signal's detail
- [[signals-page]]: the slice-4 screen whose Source and Provenance chips come from this registry
- [[user-settings]]: the stored `signals.filters`, whose `sources` must exist in this registry
- [[gdelt-gkg-ingest]]: the GDELT collector family, its keep gate and its bounds
- [[event-calendar]]: the `finnhub-earnings-calendar` source, owned by the `context` runner
- [[signals-context]]: spec 3b, which added the three context sources
