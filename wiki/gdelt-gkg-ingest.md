# GDELT GKG ingest and the keep gate (`gkg_mentions`, `theme_rules`, `domain_rules`)

**Summary**: Since signals context (spec 3b, merged 2026-10-30), the bot's `packages/ingest` reads GDELT's Global Knowledge Graph 2.1. It reads two file streams, `gdelt-gkg-en` and `gdelt-gkg-translation`, every 5 minutes under `runner:ingest`, and makes no model call. A **keep gate whose rules are database rows** (`theme_rules`, `domain_rules`, re-read every run and never written by the bot) keeps a row only when it carries a gate theme and names an active instrument or a class tag, and its publisher domain is not denied. Only kept rows are stored, as `gkg_mentions`, with 90-day retention. Each window commits in one transaction with its cursor. Every bound from the security reviews is a refusal or a drop, never a truncated mention. On 2026-10-27 about 2.18 % (`en`) and 0.62 % (`translation`) of rows were kept, from about 1.38 GB a day streamed and discarded, at zero model spend. What the kept mentions feed is on [[context-features-and-coverage-signals]].

**Sources**: `raw/2026-10-30-signals-context.md`

**Last updated**: 2026-10-31

---

## Why a keep gate, and why rules as data (intent D4, D6, D7)

- **D4.** A row is kept on a **gate theme AND an active instrument (or a class tag)**, unless its publisher domain is **denied**. Only matched rows are kept. Storing rejected rows would cost about a million rows a day, and a window can be re-ingested from GDELT's archive under new rules.
- **Rules are rows.** The owner wanted every rule and threshold to change without a deploy. `theme_rules` and `domain_rules` are re-read on every run. A change takes effect on the next run, with no restart (int spec "gdelt: a rule change changes the next run"; the live check is FR-SC-E2E-002, unverified).
- **D6.** Both streams run from day one, with **no automatic backfill**. A bounded owner-run backfill exists.
- **No model call per article**, and never the GDELT DOC 2.0 API (non-goals).

(source: raw/2026-10-30-signals-context.md §Concept, The approach, D4, D6, D7 and non-goals)

## The collector (`packages/ingest/src/collectors/gdelt/`)

GDELT is its own registry family (plan PB3–PB5). See [[source-registry-and-ingest]] for the registry.

- **Sources.** `gdelt-gkg-en` and `gdelt-gkg-translation`, each on a 300 s timer under `runner:ingest`. One pass writes one `source_runs` row and commits **one transaction per window**: mentions, `source_files`, quarantine rows and the cursor together.
- **Cursor per stream:** `{stream, last_settled_stamp, pending:[{stamp, attempts, first_missing_at}]}`.
  - The first run settles the newest `lastupdate` stamp without fetching (no backfill).
  - A pass handles at most 8 due stamps, oldest first, and never steps past an unsettled stamp.
  - A 404 becomes `missing_retryable`. After `missing_retry_hours` (6) the collector reads the stream's own manifest tail (`Range: bytes=-2097152`; on a 206 the first line is discarded). The stamp then becomes `gap_confirmed`, or the run fails after 12 attempts. A stamp the manifest does not list is filed `unlisted`.
- **Download and integrity.** Windows are streamed by market-data's new `transport/stream-zip.ts` (`streamZipEntry`, `fflate`; see [[market-data-worker]]).
  - Caps come from `sources.config`: 64 MiB zipped, 256 MiB inflated.
  - SHA-256 and MD5 are computed while streaming. The MD5 is checked against the **same stream's** manifest.
  - Limits: 2 streamed requests per second, a 120 s window deadline.
  - `fetch.ts` keeps its 4 MiB cap and was not edited.
  - Only GDELT's own `http://` origin is rewritten to `https://data.gdeltproject.org`. Any other host fails the run with `SourceConfigError`.
- **Parse.** 27 tab-separated columns, quote processing off, HTML entities decoded in `PAGE_TITLE`.
- **Tripwire.** More than 5 % quarantined rows in a file of at least 100 rows quarantines the window: its kept rows roll back, the run fails with `QuarantineRatioExceeded`, and the stamp settles.
- **Window notifier.** After each window commit, a notifier shared with the `context` runner triggers feature computation (PB7).
- **Outbound.** Files only, on `https://data.gdeltproject.org` only, with User-Agent `Tidewatch/<version>` and no contact.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 1. GDELT collector; §API, Outbound calls)

## The keep gate (`gate.ts`, `match.ts`)

The order is:
1. **Denied domain** (`domain_rules.action = 'deny'`): rejected.
2. **Gate-theme hit.** A `theme_rules` row in bucket `gate` must match. A zero weight still gates.
3. **Subjects.** Organisation and name strings are normalised and corporate suffixes stripped, then matched exactly against `instrument_aliases` of kind `name` for active instruments (see [[instrument-master]]). Names under 4 characters, and any listed in `context_versions.constants.ambiguous_names`, never match. A `class_tag` theme adds the subject `class:<asset_class>`.

The bot never writes `theme_rules` or `domain_rules`.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 1. GDELT collector, Keep gate)

## Real-data fix: rows split by raw newlines (S15, finding GDELT-NL)

- **What happened.** On the live 2026-10-27 backfill, the tripwire quarantined translated window `20261027181500`: 143 of 2,731 lines (5.24 %), `missing_fields`. The cause was raw newlines in `V2ExtrasXML`, inside a `mailto:` footer, on 27 `berliner-zeitung.de` rows and 2 `tyzden.sk` rows.
- **Fix.** The parser fix was chosen, under the owner's delegation, not a deny-list entry. **A row starts only on `^\d{14}-T?\d+\t`;** any other line is joined to the previous row with one space.
- **Live re-measure.** 96 of 96 windows parsed, and the stream's `missing_fields` fell from 463 to 0.
- **Side effect (soak watch item).** Since S15, a URL that GDELT splits with a raw newline is quarantined (field `url`) instead of stored with a space. None of 4,737 real URLs had one.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 2. Real-data fix; §Open questions, Soak watch items)

## Bounds from the security reviews (S17–S19)

Every bound is a refusal or a drop, never a truncated mention.

- **Streaming:** received chunks are coalesced into 4 KiB parts; an entry over 1,000,000 lines is refused (`line_count`); a row over 1,000 continuation lines is `body_too_large`.
- **Per row, before decoding:**
  - record id at most 32 characters;
  - URL at most 2,048 characters, with no control character or space;
  - domain at most 253 characters, matching `^[a-z0-9.-]+$`;
  - list fields read to at most 4,096 entries, names at most 256 characters;
  - themes must match `^[A-Z0-9_]{1,128}$`;
  - tone is read up to its first comma;
  - the title is decoded from at most 10,010 raw units (surrogate-safe), with control characters turned into spaces.
- **Per mention and per window:** 128 subjects per row; 64 themes and 64 countries per mention; 10,000 mentions per window; a 16 MiB charge per window (refused `mention_bytes`). `gkgMentionRowsJson` (`commit-rows.ts`) is the single row mapping for the commit, so the commit payload stays inside the charge.
- **Memory.** About 66 MiB per window at commit, 132 MiB for both streams, against the 576 MiB production heap. Review r4 measured the round-3 attack zip refused at 817 mentions, with 9.8 MiB retained and a 24.2 MiB commit peak (before S19: 289.7 / 552.5 MiB).

Why these exist: r1 found a newline-dense zip could exhaust the heap, r2 found a tiny-chunk partial-line rope, mention fan-out and row pinning, and r3 found per-mention size unbounded (see [[signals-context]]) (source: raw/2026-10-30-signals-context.md §Concept, How it runs, 3. Bounds; §Concept, Review history).

## Backfill

`source-backfill --source gdelt-gkg-en|gdelt-gkg-translation --from --to` covers at most one UTC day per call. It writes mentions, files and quarantine rows, and **no feature rows**. A one-day call measured 61.4 s (`en`) and 65.2 s (`translation`) (source: raw/2026-10-30-signals-context.md §Concept, How it runs, 1. GDELT collector, Backfill; §Measured GDELT figures).

## Tables and seeds (migration N)

```sql
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
  PRIMARY KEY (subject, ts, gkg_record_id), CHECK (subject rule));
```

- **`gkg_mentions`** is a hypertable on `ts` with 7-day chunks and no default index. It moves to the columnstore (segment by `subject`, order by `ts DESC`) after 30 days. Its **90-day retention is N's one retention policy**. The subject rule: an instrument row has `subject = instrument_id`; a class row has no instrument and `subject = 'class:' || asset_class`.
- **`theme_rules` seeds: 37, all `exact`, weight 1.** Each was checked against GDELT's `LOOKUP-GKGTHEMES.TXT` (read 2026-10-28, 59,315 lines) by `scripts/check-gkg-themes.sh` (FR-SC-MIG-002).
  - 25 `gate` rows: the PRD's 22 `ECON_*` plus the build's `ECON_CUTOUTLOOK`, `ECON_NATIONALIZE` and `ECON_PRICECONTROL`.
  - 2 `class_tag` rows: `ECON_GOLDPRICE → gold`, `ECON_BITCOIN → crypto`.
  - 10 `score` rows: the `WB_*` finance families.
  - Ten candidate themes are absent from the lookup and were never seeded (for example `ECON_MERGER`, `ECON_CRYPTOCURRENCY`).
- **`domain_rules` seeds: 9 deny rows, no trust rows,** each with a note naming the window it was observed in: `pr-inside.com`, `prokerala.com`, `prnewswire.com`, `zazoom.it`, `sanantoniopost.com`, `tucsonpost.com`, `californiatelegraph.com`, `themarketsdaily.com` and `dailypolitical.com`. The last three came from the build's own windows.
- **Seeds are data.** A change to a rule is a new data migration, never an edit of N (see [[centralized-migrations]]). The live rule-flip check (FR-SC-E2E-002) uses a direct `UPDATE theme_rules SET is_active = …`, which the next run reads with no restart.

(source: raw/2026-10-30-signals-context.md §Database)

## Measured figures (2026-10-27, `packages/ingest/docs/gdelt-gkg-layout.md`)

These were measured over 96 windows per stream, against a 526-instrument universe with no SET names.

| Figure | `en` | `translation` |
| --- | --- | --- |
| Rows read | 117,445 | 222,965 |
| Kept-row ratio (committed) | 2.18 % (2,561) | 0.62 % (1,387) |
| `rejected_theme` | 85.48 % | 84.63 % |
| `rejected_match` | 10.48 % | 13.03 % |
| `rejected_domain` | 1.87 % | 1.51 % |
| Inflate ratio | 3.07–3.11× | 3.15–3.29× |
| One-day backfill call | 61.4 s, 503,846,895 bytes | 65.2 s, 870,231,067 bytes |

- **Mentions.** The 3,948 kept rows wrote 7,000 `gkg_mentions` (1.77 subjects per kept row).
- **Volume.** About 1.38 GB a day for both streams (the PRD estimated 1.8 GB), about 192 windows, streamed and discarded with zero model spend. The largest window was 21,054,631 bytes zipped.
- **Request tolerance.** 392 requests over two runs: no 429, 403 or 5xx, and at most 2 streamed requests in any rolling second. This is an observed floor, not a published limit (assumption A2 stays open until the soak).
- **Real maxima against the caps:** subjects per row 25 of 128; mentions per window 164 of 10,000; list entries 680 of 4,096; names 62 of 256; themes 61 of 128; countries 36 of 64; busiest window 0.70 of 16 MiB.

(source: raw/2026-10-30-signals-context.md §Measured GDELT figures; §Database, Volume)

## Observability (ingest side)

The PRD's 8 events and 6 metrics are closed sets, split between the two runners (PB6); `telemetry-union.spec.ts` checks the union. The ingest side owns:
- **events:** `context_window_finished`, `context_window_quarantined`, `context_gap_confirmed`;
- **metrics:** `context_gkg_rows_total{source,outcome}`, `context_windows_total{source,status}`, `context_window_lag_seconds{source}`.

The context side is on [[context-features-and-coverage-signals]] (source: raw/2026-10-30-signals-context.md §Concept, Telemetry).

## Verification and open items

- **Named titles** include "gdelt: two streams advance their own cursors", "gdelt: digest is the stream's own", "gdelt: quarantine ratio has a 100-row floor", "gdelt: confirms a gap from the manifest tail", "gdelt: first run settles without fetching", "gdelt: keep gate reads rules as data", "stream-zip: refuses past the caps", "no-direct-network: only fetch.ts and stream-zip read bodies" and "source-backfill: gdelt is bounded to a day". Integration: "gdelt: a rule change changes the next run" and "gdelt: a window adds nothing to the ledger".
- **Unverified:** the 24 h soak (FR-SC-E2E-001), the live rule flip (E2E-002) and the owner's false-match spot check (E2E-004: at most 5 wrong companies in 50 kept mentions; if over, tighten `ambiguous_names` or the gate themes as data).
- **In production,** ingest stores GDELT mentions if the collectors value lists `ingest`, even while `context` is not running.
- **Follow-ups:**
  - `md5_ok` on `mention_count` / `mention_bytes` refusal notes (review r3 nit 2, extended at r4);
  - a `theme_rules` shape check where rules are written: a row off `^[A-Z0-9_]{1,128}$` can never match, and nothing warns (every N seed matches);
  - export `STREAM_ZIP_PART_BYTES` / `STREAM_MAX_LINES` and drop the `STREAM_ZIP_CHUNK_BYTES` alias;
  - fix the `gdelt-gkg-layout.md:178` wording; GC before the baseline in `retain-bound.mjs`; reflow a 91-column doc comment in `collector.ts`.
- **Soak watch items:** the URL quarantine count (above), `mention_bytes` and `mention_count` refusals, and the sweep gap described on [[context-features-and-coverage-signals]].

(source: raw/2026-10-30-signals-context.md §Test plan; §Open questions)

## Related pages

- [[signals-context]]: the spec-3b overview, acceptance and owner actions
- [[context-features-and-coverage-signals]]: what kept mentions feed: features, coverage signals and the read model
- [[source-registry-and-ingest]]: the `sources` registry, `runner:ingest`, runs and quarantine
- [[instrument-master]]: the `name` aliases the gate matches against
- [[market-data-worker]]: the `stream-zip` transport and the runners in `serve`
- [[centralized-migrations]]: migration N and its seeds
- [[model-routes-and-spend]]: why GDELT adds nothing to the spend ledger
