# Event calendar (`event_calendar`, earnings and economic events)

**Summary**: Since signals context (spec 3b, merged 2026-10-30), one `event_calendar` table holds scheduled events of two kinds. **Earnings** rows come from Finnhub's earnings calendar for US instruments. The bot's `context` runner refreshes them once a day at 05:00 Bangkok, sharing one 50-per-minute Finnhub budget with company news. **Economic** rows are seeded in migrations: N seeds 10 FOMC decisions (2026-10-28 to 2027-12-08) and 1 BoT MPC decision (2026-12-23). **US CPI and payrolls are not seeded**, because BLS refused the scripted reads, so FR-SC-MIG-003 is partial. A renewal warning fires once per series per Bangkok day when that series' last seeded row is fewer than 60 days ahead, and BoT warns from the first start. The scout's calendar-driven discovery path and every `propose` decision's `market_state.calendar` read this table. In production the refresh does not run until `context` is in the bot's collectors value.

**Sources**: `raw/2026-10-30-signals-context.md`

**Last updated**: 2026-10-31

---

## Why this shape (intent D5)

Earnings come from Finnhub for US instruments, and economic events are seeded yearly rows, all in one table. 3b has **no manager gate on macro events**. Thai earnings and a paid economic calendar are non-goals (source: raw/2026-10-30-signals-context.md §Concept, The approach, D5; non-goals).

## The table (migration N)

```sql
CREATE TABLE event_calendar (event_id uuid PRIMARY KEY DEFAULT uuidv7(), kind text NOT NULL CHECK (kind IN ('earnings','economic')),
  instrument_id text REFERENCES instruments, title text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
  scheduled_date date NOT NULL, scheduled_at timestamptz, time_hint text CHECK (time_hint IN ('bmo','amc','dmh')),
  source_code text REFERENCES sources, external_ref text, detail jsonb NOT NULL DEFAULT '{}',
  first_seen_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((kind = 'earnings') = (instrument_id IS NOT NULL)), UNIQUE (kind, instrument_id, scheduled_date, title));
CREATE INDEX event_calendar_instrument_date_idx ON event_calendar (instrument_id, scheduled_date) WHERE kind = 'earnings';
CREATE INDEX event_calendar_kind_date_idx ON event_calendar (kind, scheduled_date);
```

An earnings row always names an instrument, and an economic row never does (`event_calendar_check`) (source: raw/2026-10-30-signals-context.md §Database).

## Earnings refresh (`calendar.ts`)

- **The call.** One Finnhub `GET /api/v1/calendar/earnings?from=<today−7>&to=<today+60>` runs daily at 05:00 Asia/Bangkok, and at start when the last successful refresh is more than a day old. It goes only to the pinned `finnhub.io` host, with `FINNHUB_API_KEY` passed by configuration name; the key value is never logged.
- **Filtering.** Results are filtered to master instruments by `ticker` alias on the `webull` venue (see [[instrument-master]]).
- **Write.** The range's `earnings` rows are replaced in one transaction, and a `source_runs` row is written on `finnhub-earnings-calendar`. That source row is owned by `context` (`config.owner`), not by the ingest runner (registry spec "registry: calendar source is owned by context"; see [[source-registry-and-ingest]]).
- **Shared budget.** The call shares one process-wide 50-per-minute Finnhub budget with company news (`collectors/finnhub-budget.ts`, keyed on the clock, using the `finnhub-company-news` row's `per_minute`).
- **Failures.** Only transient failures (429, 5xx, timeout) retry hourly. A 401/403 waits for the next slot. A missing `FINNHUB_API_KEY` writes a `missing_secret` noop run. A failed fetch keeps the existing rows.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 4. Context runner, Calendar; §API, Outbound calls; §Test plan, Calendar titles)

## Economic seeds (migration N)

One INSERT seeds only events after N's version instant (2026-10-28T12:02:00Z). `scheduled_at` is UTC, and `detail` holds `{source, local_time, tz, published_on}`.

| Series | Rows | Range | Source read |
|---|---|---|---|
| FOMC decision | 10 | 2026-10-28 to 2027-12-08 | federalreserve.gov, 2026-10-28 |
| BoT MPC decision | 1 | 2026-12-23 | bot.or.th, 2026-10-28; the 2027 schedule was unpublished |
| US CPI, US payrolls | **0** | — | **Not seeded.** BLS answered 403 to both scripted reads on the one pinned retry (owner ruling BOT-Q1, "Retry only") |

- **FR-SC-MIG-003 is partial** because of the missing BLS rows. The owner was to save the BLS pages to `inputs/`, but the folder stayed empty.
- **Seeds are data.** Next year's rows, and the BLS rows, ship as new data migrations, never as an edit of N (see [[centralized-migrations]]).

(source: raw/2026-10-30-signals-context.md §Database, Economic seeds and Seeds are data; §Concept, Owner rulings)

## Renewal warning (PB11; owner ruling BOT-Q2, "Per series")

- `context_calendar_expiring` fires once per **series** per Bangkok day when that series' last seeded row is fewer than 60 days ahead. This is an approved scope change to FR-SC-CAL-002.
- The `series` value is a closed code (`fomc`, `bot_mpc`, `us_cpi`, `us_payrolls`, `other`), never the title.
- **BoT is seeded only through 2026-12-23,** so its warning is active from the first start and repeats daily until a 2027 BoT migration ships. FOMC does not warn (spec "calendar: BoT warns from the first day while FOMC does not").
- Until the BLS migration ships, the `us_cpi` and `us_payrolls` series cannot warn.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 4. Context runner, Renewal warning; §Open questions, Owner actions)

## Who reads it

- **The read model** (`packages/context/src/read-model.ts`): `earningsBetween`, `nextEarnings` and `nextMacro` (see [[context-features-and-coverage-signals]]).
- **The scout's calendar-driven path.** A scope instrument qualifies with an `earnings` row within `sessions_ahead` sessions on its own calendar. Stocks only; crypto and gold never qualify (see [[bots-engine]]).
- **Decisions.** Every `propose` decision carries `market_state.calendar = {next_earnings: {scheduled_date, time_hint} | null, next_macro: {title, scheduled_at} | null}`, with earnings within 30 days and economic events within 7 days (see [[decision-record]]).
- **Metric:** `context_calendar_events{kind}`. **Events:** `context_calendar_refreshed`, `context_calendar_expiring`.

(source: raw/2026-10-30-signals-context.md §Concept, How it runs, 5. Scout discovery; §API, Bot-written jsonb; §Concept, Telemetry)

## Verification and open items

- **Named titles:** "calendar: refresh replaces the range", "calendar: missing key is a noop", "calendar: a failed fetch keeps rows", "calendar: a failed refresh retries hourly", "calendar: warns per series 60 days before its last seeded row", "calendar: BoT warns from the first day while FOMC does not", "finnhub: company news and the earnings refresh share one budget", "registry: calendar source is owned by context".
- **FR-SC-E2E-005 (live Finnhub, assumption A1), unverified.** One live earnings refresh with the owner's key: the `source_runs` row and `event_calendar` counts, or the recorded "unavailable on this plan" refusal. The preview's start-up refresh ran once on a fresh database, but the owner's acceptance is not recorded. If the endpoint is not on the owner's free tier, the refresh fails once a day for good, and the economic rows still load.
- **Owner actions:** a BLS seed data migration (US CPI and payrolls); a 2027 BoT MPC migration once the schedule is published; `context` in the production collectors value.
- **Follow-up:** assert `newsPerMinute` in the calendar integration spec, and fall back to `FINNHUB_CALLS_PER_MINUTE` on a broken news config.

(source: raw/2026-10-30-signals-context.md §Test plan; §Open questions)

## Related pages

- [[signals-context]]: the spec-3b overview and acceptance
- [[context-features-and-coverage-signals]]: the `context` runner that refreshes this table, and its read model
- [[bots-engine]]: the scout's calendar-driven discovery path
- [[decision-record]]: `market_state.calendar` on `propose` decisions
- [[source-registry-and-ingest]]: the `finnhub-earnings-calendar` source row and the shared Finnhub budget
- [[instrument-master]]: the `ticker` aliases on `webull` that earnings are matched by, and the session calendars
- [[centralized-migrations]]: migration N and its economic seeds
