# Signals read API (`GET /signals`, detail, summary, badge, export, `/sources`)

**Summary**: Since slice 4 (the signals page, tidewatch-service PR #10, merged 2026-10-12), the service reads the slice-3a signal tables through six routes. They return the day's list, with filters and a keyset cursor; one signal's detail, with provenance, model view, market context at the time and a sized recommendation; the day's summary counts; the unseen badge; a CSV export; and the source registry. Two settings routes make eight new routes in all (see [[user-settings]]). Every route mounts on the gated market group. Signals and sources are global. Citing decisions, the acted-on count, the recommendation and settings are scoped to the session user, and no route takes a user id. Every read is bound to a Bangkok day, and every read accepts `day`. At slice 4 the UI asked only for today. Since the signals day control (tidewatch-web#13, merged 2026-10-14, not deployed), the web also sends `day` for any of the last 7 Bangkok days. That needed no API change: the service and `SignalsApi` were not edited (see [[signals-day-control]]). Charting (slice 5; tidewatch-service #11, merged 2026-10-16 as `1547a89`, not deployed) added a seventh signals read, the instrument-scoped `GET /instruments/{id}/signals` over a `[from, to]` span, which the Chart's markers use. It also added `elliott` and `regime` to the detail's `context`, computed at the signal's `created_at` with no look-ahead (see [[elliott-regime-labeller]]). Since bots (slice 6, merged 2026-10-21, not deployed), bot decisions cite signals for the first time, so `acted_on_by_bots` and the Bots column can show bot actors; no signals route changed. **Since signals context (tidewatch-service #17, merged 2026-10-30, verified live),** coverage signals (`origin = 'context'`, impact `0.0000`) appear on the signals routes with no service code change, `GET /sources` lists 13 rows, and **`signals.origin` is stored but not exposed in any body** (owner ruling SVC-Q1).

**Sources**: `raw/2026-10-12-signals-page.md`; `raw/2026-10-14-signals-day-control.md` (the web's use of `day`); `raw/2026-10-16-charting.md` (the instrument-scoped read and the two new context keys); `raw/2026-10-21-bots.md` (bot decisions that cite signals only); `raw/2026-10-29-accounts-roles.md` (the gate's role only); `raw/2026-10-30-signals-context.md` (coverage signals, `origin` and the three new `/sources` rows only)

**Last updated**: 2026-10-31

---

## Gate chain and conventions

- All eight routes mount on the gated market group: `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles, 2026-10-29; see [[accounts-and-roles]]) (see [[auth-model]] and [[request-protection]]).
- Queries are parsed with `parseQuery`. An unknown, repeated or bad parameter gets `400 invalid_request {field, reason}`.
- Responses are snake_case JSON. Decimals are strings, and instants are RFC 3339 UTC.
- `/signals/summary`, `/signals/badge` and `/signals/export.csv` are static segments registered beside `/signals/:signal_id`, and they win over it.
- `TestRouter_ForcedChangeGatesNewRoutes` now counts 43 gated routes (40 production plus 3 test probes), up from 35 (R16). Since charting (slice 5) it counts 45 (42 production plus 3 test probes), with the chart route and the instrument-scoped signal read.

(source: raw/2026-10-12-signals-page.md §API, Service routes; §Concept, Plan resolutions, Service R16; raw/2026-10-16-charting.md §API, Conventions)

## Routes

| Method and path | Request | 2xx response | Errors |
|---|---|---|---|
| `GET /signals` | `day`, `asset`, `tier`, `source`, `min_impact`, `limit` 1–200 (default 50), `cursor`, `since` (not with `cursor`) | `{generated_at, day, items: SignalRow[], next_cursor, hidden_by_threshold}` | 400, including `{field: cursor, reason: invalid}` for a cursor from another query |
| `GET /signals/{signal_id}` | none | `SignalDetail` | 404 `not_found` (not a UUID, or not a signal) |
| `GET /signals/summary` | `day` | `{generated_at, day, today, acted_on_by_bots, contradicted_by_price}` | 400 |
| `GET /signals/badge` | none | `{generated_at, unseen, min_impact, seen_through}` | 400 for any parameter |
| `GET /signals/export.csv` | as the list, without `limit`, `cursor` or `since` | `text/csv; charset=utf-8`, attachment | 400 as the JSON envelope, before any CSV byte |
| `GET /sources` | none | `{items: [{source_code, publisher, kind, tier, enabled}]}` | 400 for any parameter |
| `GET /instruments/{instrument_id}/signals` (since slice 5) | `from` (required instant), `to` (optional, default `generated_at`), `limit` 1–200 (default 100) | `{instrument_id, generated_at, items}` | 400 query (`from` after `to` is `{field: from, reason: out_of_range}`); `404 unknown_instrument` |

`GET /me/settings` and `PUT /me/settings/{key}` are on [[user-settings]]. The order routes' new `decision_ctx` and `422 signal_not_applicable` are on [[signal-cited-orders]] (source: raw/2026-10-12-signals-page.md §API, Service routes). The instrument-scoped read is described below (source: raw/2026-10-16-charting.md §API, Conventions, route table).

## The Bangkok day

- A fixed UTC+07:00 zone: day D covers `[D−1 17:00Z, D 17:00Z)`. `day` is `YYYY-MM-DD`, and the default is the Bangkok day of `generated_at`.
- **Contracts r2 guidance (ORCH-8).** Clients send the response's `day` with every `cursor` and `since` read, so *Load more* and *Show* never cross Bangkok midnight. The web's export link carries the loaded `day` too (SP-W-21).

(source: raw/2026-10-12-signals-page.md §API, Bangkok day; §Concept, Cross-project contracts; §Components, SignalsService)

**What the day control relies on (2026-10-14).** The signals day control is web-only and uses these existing service rules:
- `GET /signals`, `GET /signals/summary` and `GET /signals/export.csv` accept `day=YYYY-MM-DD`. The parser has **no range check**, so an unknown, future or pre-history day answers an empty page with `hidden_by_threshold` 0. The web does its own window check (the last 7 days from the service's today) and never draws an out-of-window or future day.
- The cursor is bound to the day, and a `since` read stays within the day it names.
- The service answers `generated_at` at read time for any `day`. When a summary's `generated_at` falls on a later Bangkok day than the `day` it asked for, the web treats that as the midnight rollover (PRD A1, held in the store specs and the P1 clock test).
- History begins with slice 3a (2026-10-11), and `signals` has no retention policy.

At slice 4 the web sent `day` only on *Load more*, *Show*, the summary and the export, never on a first read. Now a past day's first page, summary and export all send `day={shown}`. On Today the first page still sends no `day`, and after a midnight rollover reloads send the kept day. The full per-read table is on [[signals-day-control]] (source: raw/2026-10-14-signals-day-control.md §Concept, Problem; §API, Requests as implemented and Service rules the web relies on).

## The list (`GET /signals`)

**Filters.**
- `asset`: `us`, `th`, `crypto` or `gold`. If it is absent, every class is included, fx too.
- `tier` and `source`: comma lists. **An empty value is the empty set (R4):** no row matches, and the export is header only. An absent parameter means all.
- `min_impact`: `^[01]\.[0-9]{2}$`, at most 1.00, default `0.00`. The screen's default is 0.30, so the web sends `min_impact` on every list, export and `since` request (SP-W-7).

**Cursor (S3).**
- It is opaque, with a checksum over the version, the kind, the day, the asset, both sets (sorted, with presence bytes) and the threshold, all length-prefixed.
- Decoding uses strict base64url and strict JSON, with a constant-time compare.
- It is bound to the query, not to the page size (`TestSignalsCursor_BoundToQuery`).
- The keyset order is `(created_at DESC, signal_id DESC)`.

**`since` reads (R5).**
- A `since` read returns the `limit` oldest rows after `since`, extended to every row that shares the last `created_at`, because a document's signals commit together.
- Rows come newest first, with `next_cursor` null.
- A capped reveal repeats `since` from the newest instant held, so no row is skipped.

**`hidden_by_threshold` (ORCH-8, R19).**
- On every paged read, it counts the response day's signals that match `asset`, `tier` and `source` but have `impact < min_impact`. It is computed in one statement over the whole day.
- It is `0` when `min_impact` is `0.00` or a set is empty, and it is the same on every page of one query.
- It is `null` on a `since` read.
- It is always present, as the envelope's last key.
- `TestSignals_List_HiddenByThreshold` includes a row at exactly 0.3000, which is listed but not counted (mutation-checked).

(source: raw/2026-10-12-signals-page.md §API, Service routes, Cursor and `hidden_by_threshold`; §Concept, Plan resolutions, Service R4, R5, R19; §Concept, Plan resolutions, Web SP-W-7; §Test plan, Named acceptance tests)

## `SignalRow`

```
{ signal_id, created_at, document_id, source_code, publisher, tier, headline, published_at, body_status,
  instrument: {instrument_id, display_symbol, asset_class, venue_id},
  siblings: [{instrument_id, display_symbol, direction, p}],
  event_type, severity, direction, p, p_up, p_down, p_neutral, applies_p, horizon, novelty, mention,
  conviction, impact,
  bots: [{decision_id, bot_id, bot_name, actor: "bot"|"user", action, qty | null, ts, followed_recommendation | null}] }
```

- **Decimal scales.** Probabilities have 3 dp (`"0.780"`), `severity` has 2, and `conviction` and `impact` have 4.
- **`siblings`** are the other signals of the same document. Filters do not apply to them.
- **`bots`** are decisions whose `signal_ids` overlap this id, on bots the session user owns (owner decision D1). See [[decision-record]].
- **Orderings (R6).** `bots` by `ts`, then `decision_id`. `siblings` by `display_symbol`, then `instrument_id`.
- **Closed vocabularies.** `tier`, `direction`, `horizon`, `novelty`, `mention`, `event_type`, `asset_class`, `body_status`, `kind`, `actor`, `action`, `role`, `cdc_zone` and the context timeframe are all closed vocabularies, listed in contracts §1. The web's strict parsers refuse unknown values. Since web fix-r1, decimals must be strings.

(source: raw/2026-10-12-signals-page.md §API, `SignalRow`; §Concept, Plan resolutions, Service R6; §Components, Data layer)

## `SignalDetail`

`SignalDetail` is `SignalRow` plus:
- **`canonical_url`**: an absolute `http`/`https` URL only, else `null` (R14).
- **`triage`**: `{is_material, event_type_probs (pass-through jsonb), model_id, prompt_version} | null`.
- **`extraction`**: `{key_facts[], rationale, role, why, prompt_version, model_id} | null`. It is the latest extraction whose `model_id` equals the signal's `extraction_model_id`. `role` and `why` come from `document_instruments`.
- **`structured`**: the source's `config.structured`, true for Binance TH listings. The web then reads "Structured source · no model".
- **`model`**: `{triage_model_id, extraction_model_id, scoring_model_id, prompt_version, scoring_version, constants: {novelty_w, mention_w, credibility}}`. The constants come from `scoring_versions.constants` and the current `sources.credibility`. How the web multiplies them out, including freshness at creation (ORCH-13), is on [[signals-pipeline]].
- **`context`**: `{timeframe, cdc_zone, zone_since, zone_age, close_at_signal, latest_price, latest_price_at, price_since_pct, atr14, contradicted}`, each nullable:
  - `timeframe` is the strip timeframe, `1h`, or `1d` for a daily base.
  - The zone run looks back over at most 48 strip rows at or before `created_at`.
  - `close_at_signal` is the latest strip close within the 7 days before `created_at`.
  - `atr14` comes from the latest `1d` row within the 30 days before `created_at`.
  - `latest_price` is a usable `px:last`, else the latest strip close (see [[redis-market-contract]]).
  - `price_since_pct` has 4 dp, rounded half away from zero.
  - `contradicted` is null when any input is missing.
  - The rows read are described on [[market-timeseries]].
  - **Since charting (slice 5), two more keys follow `contradicted`:** `elliott` and `regime`. See "The `elliott` and `regime` context keys" below.
- **`recommendation`**: `{side, qty_suggested, rule: "equity_pct_10", equity_pct: "0.10", equity, price, priced_at} | null`. How it is sized is on [[signal-cited-orders]]. Since review-fix r1, the detail reads `px:last` **once** and passes the value to the recommender, so the context and the recommendation share one instant (`TestService_Detail_OnePxLastRead`).

(source: raw/2026-10-12-signals-page.md §API, `SignalDetail`; §Concept, Plan resolutions, Service R14)

### Coverage signals in the list and the detail (signals context, 2026-10-30)

Signals context added a second kind of `signals` row, the coverage signal (see [[context-features-and-coverage-signals]]). The service has **no code change** for it.
- **List.** `GET /signals` lists coverage signals like any signal, with impact `0.0000`, so they appear only at `min_impact=0.00`.
- **Detail.** `GET /signals/:signal_id` answers 200 with exactly `SignalDetail`'s keys:
  - headline = the coverage title, publisher `GDELT Project`, tier `media`, `body_status headline_only`;
  - `triage` and `extraction` null;
  - `canonical_url` null, because the `tidewatch://` URL fails the http/https rule (R14);
  - `p 0.000`, `p_neutral 1.000`, `impact 0.0000`, every model id `context.v1`.
- **`origin` is stored but not exposed** in any body. The `document_instruments` subject row is joined but not rendered. This is owner ruling **SVC-Q1** (no API change for the coverage signal's detail body), and FR-SC-SVC-002 was verified under it (PS4). `TestSignals_Detail_ContextOrigin` asserts that the body holds no `"origin"`, no `tidewatch://` and no `coverage anomaly`. Exposing `origin` waits for the "what the bot sees" view.
- **The service reads no N table or column,** `signals.origin` included, so N is not pinned (see [[centralized-migrations]]).
- **Follow-up (optional):** more absent strings in `TestSignals_Detail_ContextOrigin` (service security L2).

(source: raw/2026-10-30-signals-context.md §API, 3. Signals routes; §Database, Pins; §Concept, Owner rulings SVC-Q1; §Test plan, Recorded results; §Open questions, Smaller recorded follow-ups)

### The `elliott` and `regime` context keys (charting, slice 5)

`context` keeps every slice-4 key and gains two keys after `contradicted` (contracts r2 §6):

```json
"elliott": {"stage": "Impulse, in wave 5", "direction": "up", "fit": "0.58", "invalidation": {"price": "183.4000", "side": "below", "wave": "4"}},
"regime":  {"trend": "up", "vol": "normal", "atr_pct": "0.83"}
```

- **What they are.** `elliott` is the first ranked candidate's `{stage, direction, fit, invalidation}`, or `null`. `regime` follows the regime rule, or is `null`. Both come from the shared labeller (see [[elliott-regime-labeller]]).
- **How they are computed.** On the strip timeframe (`context.timeframe`), with the same `waves` functions, over `ChartRepo.Bars(strip timeframe, created_at − timeframe, 500)`. Every bar must satisfy `ts + timeframe ≤ created_at`, eod bars included (CH-R6), so there is no look-ahead. For a daily-strip instrument, a session dated on or after `created_at`'s UTC day is never read.
- **Failure.** A failed bars read fails the detail, as a failed context read does. Code review r1 kept this, because `null` would misreport a database error as "no candidate".
- **Cost.** The detail now reads ≤ 500 bars and runs the `big.Rat` analysis per request. Security review r1 accepted this as a fixed, linear cost.
- **Unchanged.** Every other detail key, and the one `px:last` read.
- **Web.** The Signals detail's *Elliott* and *Regime* rows now show these values; "Arrives with Charting" is gone (see [[signals-page]]). The web reads both keys as optional-nullable, so it also parses an old service's body.

(source: raw/2026-10-16-charting.md §API, The signal detail's new context keys (contracts r2 §6); §Concept, Operations; §Components, Signals detail rows)

## Summary counts (PD7)

The summary is one SQL statement with lateral joins. Filters do not apply to it.
- **`today`**: the day's signals.
- **`acted_on_by_bots`**: distinct signals cited by a decision with `actor = 'bot'` on the user's bots. A user-actor citing decision never counts (owner decision D1).
- **`contradicted_by_price`**: signals that meet all of these conditions:
  - the direction is up or down;
  - `p ≥ 0.600`;
  - a daily ATR exists;
  - `latest_close − close_at_signal` goes against the call by more than that ATR.

  The latest stored close stands in for the current price (S7). Missing rows count as not contradicted.

(source: raw/2026-10-12-signals-page.md §API, Summary)

**Bots now cite signals (slice 6, 2026-10-21).** Until slice 6 no bot cited a signal, so `acted_on_by_bots` was 0 by design. Since slice 6, a general-engine bot's `propose` decision for a signal-driven candidate records `signal_ids` and `signal_snapshot`, and its entries copy them from the proposing decision (ORCH-9a). Those `actor = 'bot'` decisions overlap the signals' ids, so they appear in each row's `bots` field and count in `acted_on_by_bots`; setup-driven candidates and direct entries cite nothing. On the preview, the E2E bots' buys cited the two injected `binance-th-listings` signals. The routes, SQL and GIN index are unchanged (see [[bots-engine]] and [[decision-record]]) (source: raw/2026-10-21-bots.md §The bot engine, Decisions written by the loops and Manager; §Test plan, The E2E checks; §Cross-cutting links).

## Badge (S8)

- `unseen` counts signals with `created_at > seen_through`, `impact ≥ min_impact` and `created_at ≥ generated_at − 7 days`, capped at 999.
- With no stored setting, `min_impact` defaults to `"0.30"`, and `seen_through` defaults to the start of the current Bangkok day.
- A stored value that does not read back in its key's shape counts as not stored.
- What moves `seen_through`, and how the rail shows the count, is on [[user-settings]].

(source: raw/2026-10-12-signals-page.md §API, Badge)

## Export (`GET /signals/export.csv`, PD9)

- **Headers.** `Content-Disposition: attachment; filename="signals-<day>.csv"` and `Cache-Control: no-store`.
- **Body.** A UTF-8 BOM, RFC 4180 quoting and CRLF line ends, with at most 10,000 rows in list order. Every row is read before the first byte is written, so a refusal is still the JSON envelope.
- **Header row, exactly:** `signal_id,created_at_utc,created_at_bangkok,day,source_code,publisher,tier,event_type,headline,document_id,canonical_url,instrument_id,display_symbol,asset_class,direction,p,p_up,p_down,p_neutral,applies_p,horizon,novelty,mention,severity,conviction,impact,bots`.
- The `bots` cell reads like "You bought 16.2 (followed); Slack Water bought 16.2".
- **Formula guard (R13, a security default).** A `headline`, `publisher`, `canonical_url` or `bots` cell that starts with `=`, `+`, `-`, `@`, TAB, CR or LF (LF was added in review-fix r1) gets a leading `'`. `canonical_url` is passed only as an absolute `http`/`https` URL, else it is empty (R14).
- **A top-level GET.** It is read-only, so the session cookie travels and no CSRF header is needed (see [[request-protection]]). On the preview, three real downloads matched the API's row counts and sent the cookie. The development half of that check (A4) is unverified (ORCH-9).

(source: raw/2026-10-12-signals-page.md §API, Export; §Concept, Plan resolutions, Service R13/R14; §Test plan, Acceptance status FR-SP-WEB-007)

## Sources (`GET /sources`)

- The route returns `{source_code, publisher, kind, tier, enabled}` per row, and never a URL or `config` (`TestSources_List_NoURLOrConfig`).
- Rows are ordered by tier (filing, wire, exchange, media, account), then by code (R6).
- How the web turns the rows into publisher chips is on [[source-registry-and-ingest]].

- **Since signals context (migration N, 2026-10-30),** the route lists 13 rows. N's three come after `finnhub-company-news`, in the media group: `finnhub-earnings-calendar` (Finnhub), `gdelt-gkg-en` (GDELT Project) and `gdelt-gkg-translation` (GDELT Project). No URL, host, `config` key or key variable appears (`TestSources_ListsContextSources`) (source: raw/2026-10-30-signals-context.md §API, 2. `GET /sources`).

(source: raw/2026-10-12-signals-page.md §API, Service routes; §Concept, Plan resolutions, Service R6; §Test plan, Named acceptance tests)

## Instrument-scoped signals (`GET /instruments/{id}/signals`, slice 5)

Charting needed one instrument's signals over the span of its loaded bars, which `GET /signals` (one day, no instrument filter) cannot give (PRD S6). tidewatch-service #11 (merged 2026-10-16, not deployed) added this read beside the chart route, through the same `mountChart` mount and the conventions on [[chart-read-api]].

- **Span.** Inclusive: `from ≤ created_at ≤ to`. `to` defaults to `generated_at`.
- **Order and size.** Items come newest first by `(created_at, signal_id)`, at most `limit` (1–200, default 100), in one statement served by `signals_instrument_created_idx`. There are no citing decisions, no siblings and no cursor.
- **No maximum `from`–`to` distance.** The security review accepted the `limit ≤ 200` bound and the index range scan instead.
- **Body.**

  ```json
  {"instrument_id":"NVDA@webull","generated_at":"…",
   "items":[{"signal_id":"…","created_at":"2026-10-14T04:37:12.204511Z","tier":"filing","source_code":"sec-edgar","publisher":"NVIDIA Corp",
             "headline":"NVIDIA announces …","event_type":"guidance","direction":"up","p":"0.780","impact":"0.4224","horizon":"days","document_id":"…"}]}
  ```

  `headline` is `documents.title` and `publisher` comes from `documents`.
- **Code.** S3 added a separate `InstrumentSignalsService` port in `handlers/chart.go`, because `handlers.SignalsService` was a byte-identical contract file. `NewChartHandler` takes both services. S3 also created `internal/services/signals/instrument.go` and modified `internal/repository/postgres/signal.go`.
- **The web's use.** The Chart reads `?from={first loaded bar ts}&limit=200`, re-reads it with an earlier `from` when it loads earlier bars, and re-reads it when a `signal` frame names an unlisted id. Markers come from this read only, because the C-SIG-1 frame carries no headline (see [[signal-message-contract]]).

(source: raw/2026-10-16-charting.md §API, `GET /instruments/{id}/signals` (contracts r2 §5); §Database, Relations read; §Concept, Spec-level decisions S6; §Components, `ChartService` and Realtime; §Files touched, tidewatch-service)

## Compatibility

- An old web against the new service is unchanged.
- A new web against an old service shows the Signals error state and a hidden badge, because the routes answer 404.
- The bot is unaffected.
- Configuration, secrets, compose, `go.mod`/`go.sum` and Redis keys are unchanged.

(source: raw/2026-10-12-signals-page.md §API, Configuration and compatibility)

**Since charting (slice 5).** A new web on a service without slice 5 gets `404 not_found` on `GET /instruments/{id}/signals`, and the Chart shows its error state. An old web ignores the two new context keys (source: raw/2026-10-16-charting.md §API, Errors, compatibility and logs).

## Tests

- **Integration:** `TestSignals_List_FiltersAndPaging`, `TestSignals_List_SinceAndCitingDecisions`, `TestSignals_List_HiddenByThreshold`, `TestSources_List_NoURLOrConfig`, `TestSignals_Detail_ContextAndRecommendation`, `TestSignals_Summary_Counts`, `TestSignals_Badge`, `TestSignals_Export`, and `TestReady_SignalsIngestSchema_NotReady` (a database migrated only to H gives 503).
- **Unit:** `TestService_Badge_Defaults`, `TestSignalsCursor_BoundToQuery`, `TestExport_CSV_Format`, `TestExport_CSV_GuardCells` and `TestService_Detail_OnePxLastRead`.
- **Revised on purpose:** `TestRouter_ForcedChangeGatesNewRoutes` (43), `TestRouter_NoDecisionMutation`, `TestRouter_MarketMutations_CSRF`, `TestCodes_Contract` and the `TestReady_*` messages.
- **Code layout.** The new package `internal/services/signals/` holds `list`, `cursor`, `sources`, `detail`, `summary`, `badge` and `export`, each with tests. The repositories are `signal.go` and `source.go`, and the handler is `internal/handlers/signals.go`.

(source: raw/2026-10-12-signals-page.md §Test plan, Named acceptance tests; §Files touched, tidewatch-service)

**Added by charting (slice 5).**
- **Unit:** `TestService_InstrumentSignals_Span`, `TestChartHandler_Signals_Query`, `TestService_Detail_ElliottRegime` and `TestSignalsHandler_Detail_ElliottRegimeShape`.
- **Integration:** `TestInstrumentSignals_Span`; `TestSignals_Detail_ElliottRegime/intraday` and `/eod`, which seed look-ahead bars and check they are ignored, exclude the eod session on `created_at`'s day, and cover the midnight case.
- **Revised on purpose:** `TestRouter_ForcedChangeGatesNewRoutes` (43 → 45); `TestSignalsHandler_Detail_Shape`, which now expects `"elliott":null,"regime":null`; and `TestSignals_Detail_ContextAndRecommendation` through its exact-keys helper. `test/integration/signals_fixtures_test.go`, which adds the two keys to that helper, was an extra outside the S4 file list; code review r1 ruled it necessary and test-only.
- FR-CH-SVC-004 (the detail's keys) and FR-CH-SVC-005 (the instrument-scoped span) passed.

(source: raw/2026-10-16-charting.md §Test plan, Named acceptance tests and Acceptance status; §Files touched, tidewatch-service S4)

## Follow-ups

- The export caps silently at 10,000 rows. A truncation signal needs a contract change.
- The detail route's `uuid.Parse` accepts braced, URN and unhyphenated ids, while the order path accepts only hyphenated ones.
- Comments that promise "one read" overstate it: the equity valuation still MGETs the held instruments.
- Migration I's header and the migrations README say `@>`, but the list and the export use `&&`. This is wording only (see [[centralized-migrations]]).
- `encoding/csv` drops a bare CR inside a field (code-r1 nit 3).
- **A3 is unverified.** No explain-analyse of the lateral `indicators` lookups is recorded.
- The integration harness's `freePort` race ("address already in use") is pre-existing.

(source: raw/2026-10-12-signals-page.md §Open questions, Service follow-ups; §Test plan, Assumption outcomes)

## Related pages

- [[signals-page]]: the slice-4 overview, the screen and acceptance
- [[signals-day-control]]: the web's *Day* select, which sends `day` for the last 7 Bangkok days
- [[user-settings]]: the settings routes, `seen_through` and the rail badge
- [[signal-cited-orders]]: the recommendation in the detail and the order path that cites a signal
- [[signals-pipeline]]: the `signals`, `triage`, `extractions` and `document_instruments` rows these routes read
- [[source-registry-and-ingest]]: the `sources` rows behind `GET /sources`
- [[decision-record]]: the citing decisions behind `bots` and `acted_on_by_bots`
- [[market-timeseries]]: the strip rows and `atr14` behind `context`
- [[redis-market-contract]]: the `px:last` read behind `latest_price` and the recommendation
- [[auth-model]]: the gate chain and per-user scoping
- [[request-protection]]: the cookie-carrying export
- [[centralized-migrations]]: migration I's GIN index
- [[charting]]: slice 5, whose markers read the instrument-scoped route and which filled the Elliott and Regime rows
- [[chart-read-api]]: the sibling chart route and the conventions both slice-5 routes share
- [[elliott-regime-labeller]]: the labeller behind the detail's `elliott` and `regime`
- [[signal-message-contract]]: the C-SIG-1 frame, which carries no headline, so the Chart re-reads this route
- [[bots-engine]]: the bot decisions that now cite signals and count in `acted_on_by_bots`
- [[context-features-and-coverage-signals]]: coverage signals and the unexposed `origin` column
