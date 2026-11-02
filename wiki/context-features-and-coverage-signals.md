# Context features and coverage signals (`packages/context`, `signals.origin`)

**Summary**: Since signals context (spec 3b, merged 2026-10-30), the bot's `context` runner turns kept GDELT mentions into **context features**. For each instrument (and the class rows `class:gold`, `class:crypto`) and each 15-minute window, it computes the trailing-24 h article count, tone, countries and publishers against a 30-UTC-day baseline with a Poisson floor. When an instrument's coverage z crosses its threshold, the runner writes one **coverage signal** per instrument per Bangkok day. This is a `media` signal on a synthetic document, with `origin = 'context'`, `impact 0.0000`, `p_neutral 1.000` and model ids `context.v1`, published as an ordinary C-SIG-1 message. **A coverage signal never triggers anything.** Every trigger read filters `origin = 'document'`, so with any `min_impact`, including 0, it never qualifies, wakes a bot, or adds or trims; `impact = 0` is only a second line of defence. `origin` is stored but **not exposed by the API** (owner ruling SVC-Q1). The runner also refreshes the [[event-calendar]] and serves a read model to the scout. It makes no model call. **In production the runner is not running yet**, because the bot chart's collectors value does not list `context`.

**Sources**: `raw/2026-10-30-signals-context.md`

**Last updated**: 2026-10-31

---

## Why a signal, and why never a trigger (intent D1, PRD §4.7, PD11)

The owner wanted coverage anomalies surfaced as media signals, but never acting as a trigger. A coverage anomaly is therefore a `media` signal with a synthetic document: `origin = 'context'`, `impact = 0`, `conviction = 0`, `p_neutral = 1`, `event_type = other`, and direction `neutral` unless the tone z also crosses. Two alternatives were rejected: no `signals` row until the "what the bot sees" view, and a real impact so the signal path could act. The title carries the summary, so the web needed no change. A `coverage` event type is a non-goal (source: raw/2026-10-30-signals-context.md §Concept, The approach, D1; non-goals).

## The runner (`packages/context`)

- The `context` Runner holds `runner:context`. It makes no model call and uses at most one pooled connection, so `SERVE_POOL_MAX` stays 12. It is the 15th of `COLLECTOR_NAMES` (`learning` is the 14th) and enabled by default when `MARKET_DATA_COLLECTORS` is empty (see [[market-data-worker]]).
- **Notifications.** A window notifier, shared by `ingest` and `context` (PB7), triggers feature computation after each window commit. A 60 s sweep of `source_files` recovers lost notices. The queue holds at most 64 pending notices; a notice past that is **dropped silently**, and the sweep computes its window.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 4. Context runner; Runtime counts)

## Features (`features.ts`, intent D3)

- One row per subject per 15-minute window in which the subject was mentioned. It is written at `ts = stamp + 15 min` and upserted on `(subject, ts)`, so the second stream's arrival recomputes the same row.
- **Columns:** `articles_24h`, `countries_24h`, `publishers_24h`, `tone_mean_24h` and up to five `top_themes`.
- **Baseline:** the trailing 30 complete UTC days.
- **`sd_eff = max(baseline_sd, sqrt(max(baseline_mean, 1)))`** (the Poisson floor).
- **z is null under 7 baseline days** (`min_baseline_days`): no anomaly before 7 days, full strength at 30 (D6). There is no automatic backfill, and `source-backfill` writes no feature rows.
- **Class rows** (`class:gold`, `class:crypto`) are recorded but never used for discovery, and never get a signal.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 4. Context runner, Features; §Concept, D3, D6)

## Constants as data (`context_versions`, intent D7)

```sql
CREATE TABLE context_versions (context_version integer PRIMARY KEY CHECK (context_version > 0),
                               constants jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
-- v1: {"z_articles": 2.0, "z_tone": 2.0, "min_articles_24h": 5, "min_baseline_days": 7, "baseline_days": 30,
--      "novelty_window_days": 5, "sd_floor": "poisson", "ambiguous_names": [35 names: "apple", "visa", ... "gas"]}
```

Thresholds and constants are stamped on outputs (`context_features.context_version`). A change is a new data migration with a new version, never an edit of N (source: raw/2026-10-30-signals-context.md §Database; §Concept, D7).

## `context_features` (migration N)

- Columns: `ts`, `subject`, `instrument_id`, `asset_class`, `context_version`, `articles_24h`, `baseline_days`, `baseline_mean`, `baseline_sd`, `articles_z`, `tone_mean_24h`, `tone_baseline_mean`, `tone_baseline_sd`, `tone_z`, `countries_24h`, `publishers_24h`, `top_themes jsonb`, `computed_at`. Primary key `(subject, ts)`.
- CHECKs: the same subject rule as `gkg_mentions` (`context_features_check`), and `baseline_days >= 7 OR articles_z IS NULL` (`context_features_check1`).
- A hypertable on `ts` with 28-day chunks, compressed to the columnstore after 90 days, with **no retention**. Index `context_features_instrument_ts_idx (instrument_id, ts DESC) WHERE instrument_id IS NOT NULL`.

(source: raw/2026-10-30-signals-context.md §Database)

## Coverage signals (`coverage.ts`)

**Trigger.** An instrument subject with `articles_z ≥ z_articles` (2.0) and `articles_24h ≥ min_articles_24h` (5).

**One transaction writes:**
- a synthetic `documents` row with `stage = signalled`, so `runner:signals` never triages it (see [[signals-pipeline]]). Its `canonical_url` is `tidewatch://context/<instrument_id>/<bkk_day>`, inserted `ON CONFLICT DO NOTHING`, which gives **one per instrument per Bangkok day**. Publisher "GDELT Project", `body_status headline_only`;
- its `document_versions` row (the feature row and constants as JSON);
- a `document_instruments` subject row;
- the `signals` row: `origin = 'context'`, `p 0.000`, `p_neutral 1.000`, `impact 0.0000`, `severity = min(5, |z|)`, model ids and `prompt_version` `context.v1`.

**After the commit,** C-SIG-1 goes out on `sig:<instrument_id>`. A failed publish rolls nothing back (see [[signal-message-contract]]).

**Title format:** `Coverage: {symbol} {z:.1f}σ above its 30-day baseline · {n} articles · {countries} countries · tone {tone:+.1f}`. Decimals are rounded half away from zero from their exact decimal strings, and tone is always signed (PB18).

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 4. Context runner, Coverage signals)

## `signals.origin` and the never-a-trigger rule

```sql
ALTER TABLE signals ADD COLUMN origin text NOT NULL DEFAULT 'document' CHECK (origin IN ('document', 'context'));
CREATE INDEX signals_origin_created_idx ON signals (origin, created_at DESC) WHERE origin = 'context';
```

`signals.origin` is the only change N makes to an earlier table. Every pre-N signal reads `document`.

**The trigger reads filter `origin = 'document'`:**
- `SIGNALS_SINCE`, `SIGNALS_SINCE_ON` and `QUALIFYING_SIGNAL`: the scout window, the `signal_driven` due check, and the manager's events, adds and trims. The memory store mirrors them;
- `LATEST_SIGNAL`, the signals novelty read (added in S17, after bot review r1 found it unfiltered);
- after the M update, the learning loop's post-mortem `LATER_SIGNALS` query (`packages/bots/src/learning/pg-store.ts`).

So with any `min_impact`, including 0, **a coverage signal never qualifies, never writes a `long_only` refusal, never wakes a bot and never triggers an add or trim.** `impact = 0` is only a second line of defence. The Market watch count and the Signals page still count both origins.

A context path in the scout reads the **features**, not the signal. It attaches the day's coverage signal by its canonical URL, through `CONTEXT_SIGNALS_ON` (see [[bots-engine]]).

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 6. Never a trigger; §Database)

## How a coverage signal reads back

- **`origin` is stored but not exposed** in any API body (owner ruling **SVC-Q1**: no API change for the coverage signal's detail body). `TestSignals_Detail_ContextOrigin` asserts that the detail body holds no `"origin"`, no `tidewatch://` and no `coverage anomaly`. The `document_instruments` subject row is joined but not rendered.
- **List:** `GET /signals` lists coverage signals like any signal, with impact `0.0000`, so they appear only at `min_impact=0.00`.
- **Detail:** `SignalDetail`'s exact keys. Headline = the coverage title, publisher `GDELT Project`, tier `media`, `body_status headline_only`; `triage` and `extraction` null; `canonical_url` null, because the `tidewatch://` URL fails the http/https rule; every model id `context.v1`. See [[signals-read-api]].
- **Web:** rendered through the existing table and detail with no product change. See [[signals-page]].
- **C-SIG-1** is unchanged: coverage signals are ordinary messages with `impact "0.0000"` and `p "0.000"`.
- Exposing `origin` waits for the "what the bot sees" view.

(source: raw/2026-10-30-signals-context.md §API, 3. Signals routes; §Components, Signals page)

## Read model (`read-model.ts`)

`latestFeatures`, `earningsBetween`, `nextEarnings` and `nextMacro`. `worker/serve.ts` wires it as the **required** `BotsRunnerGeneralDeps.createContextReadModel` (PB17), so the discovery paths cannot silently never run. The scout uses it for discovery and for `market_state.context` / `.calendar` on every `propose` decision (see [[bots-engine]] and [[decision-record]]) (source: raw/2026-10-30-signals-context.md §Concept, How it runs, 4. Context runner, Read model).

## Observability (context side)

PRD §4.13's closed sets are split between the runners (PB6), and `telemetry-union.spec.ts` checks the union. The context side owns:
- **events:** `context_features_written`, `context_signal_emitted`, `context_calendar_refreshed`, `context_calendar_expiring`, `context_stage_failed`;
- **metrics:** `context_features_written_total`, `context_signals_total`, `context_calendar_events{kind}`.

The ingest side is on [[gdelt-gkg-ingest]] (source: raw/2026-10-30-signals-context.md §Concept, Telemetry).

## Verification and open items

- **Named titles** include "context: computes features against the fixture baseline", "context: writes a coverage signal with the context values", "context: publishes C-SIG-1 after commit", "context: class rows have no signal", "context: keeps at most 64 pending window notices", "scout: context signals never qualify", "scheduler: context signals never wake", "manager: context signals are not events" and "signals: novelty ignores coverage signals". Integration: "context: one coverage signal per instrument per Bangkok day", "context: features upsert on the database" and "pg-store: context signals are not read as triggers".
- **On the preview,** a coverage signal reached the database and Redis through the bot's own code (partial support for FR-SC-E2E-003).
- **Not running in production** until the owner adds `context` to the bot chart's collectors value: no features, coverage signals or calendar refresh.
- **Follow-ups:**
  - a metric for dropped context notices. Visibility needs a label on an existing context metric through a PRD change, because the event set is closed at five;
  - export the coverage URL prefix from `packages/context` and drop the duplicate in `bots`.
- **Soak watch item: the sweep gap.** A window inserted earlier but committed after the sweep moved past a later uuidv7 `file_id` is skipped until a restart's 24 h lookback. Since S19 this also needs a dropped notice. It affects data completeness only.

(source: raw/2026-10-30-signals-context.md §Test plan; §Open questions)

## Related pages

- [[signals-context]]: the spec-3b overview and acceptance
- [[gdelt-gkg-ingest]]: the kept mentions these features are computed from
- [[event-calendar]]: the calendar the same runner refreshes
- [[bots-engine]]: the scout's context-driven discovery path, which reads these features
- [[signals-pipeline]]: the document stages; a coverage document is born `signalled`
- [[signals-read-api]]: how a coverage signal reads, with `origin` hidden
- [[signals-page]]: how a coverage signal renders
- [[signal-message-contract]]: C-SIG-1, unchanged for coverage signals
- [[decision-record]]: `market_state.context` on `propose` decisions
- [[market-data-worker]]: the fifteenth runner
- [[centralized-migrations]]: migration N
