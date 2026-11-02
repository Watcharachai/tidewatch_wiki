# Signal message contract (C-SIG-1, `sig:<instrument_id>`)

**Summary**: C-SIG-1 is the message one new signal travels in, from the bot through Redis and the service to the browser. Since slice 3a (merged 2026-10-11), the bot publishes one compact JSON object per `signals` row to the Redis channel `sig:<instrument_id>`, only after the row commits. The service checks the header and forwards the bytes unchanged on `/ws` as a `signal` frame. The web counts each `signal_id` once per row on the loaded Bangkok day. The canonical file `signals-message.v1.json` is byte-identical in the service, the bot and the web, and a test in each repo pins it. It follows the shared-fixture pattern of contract C11 (see [[bot-watch-verdicts]]), extended to three repositories. The signals page (slice 4, merged 2026-10-12) left the bytes unchanged. It added a second delivery path: an all-signals `/ws` feed that sends every frame once to a flagged connection. The Signals page counts those frames into a quiet "N new signals" note and never inserts them. Charting (slice 5, merged 2026-10-16, not deployed) also left the bytes unchanged. Because the frame carries no headline, the Chart treats a new `signal_id` only as a cue to re-read the instrument's signals over REST. Signals context (spec 3b, merged 2026-10-30) also left the bytes unchanged. Its **coverage signals** are ordinary C-SIG-1 messages on `sig:<instrument_id>`, with `impact "0.0000"` and `p "0.000"`, so every consumer counts them like any signal.

**Sources**: `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-14-signals-day-control.md` (Today-only counting); `raw/2026-10-16-charting.md` (the Chart's markers); `raw/2026-10-30-signals-context.md` (coverage signals only)

**Last updated**: 2026-10-31

---

## Canonical bytes and copies

- **Canonical file:** `.forge/features/signals-ingest/planning/tidewatch-service/signals-message.v1.json`. It is 9,137 bytes, ASCII, LF, with a 2-space indent. **sha256 `a0829396c81494f81c19f4506afd613e6bc2b66f0b0f45d335d6aca09c96e7d1`**.
- **Byte-identical copies, each pinned by a test:**
  - service `internal/market/testdata/signals-message.v1.json`, pinned by `TestSignalMessage_FixtureHash`; the hub tests read the same file;
  - bot `packages/signals/fixtures/signals-message.v1.json`, pinned by `signals-message-fixture.spec.ts`;
  - web `src/app/pages/workspace/data/testdata/signals-message.v1.json`, whose SHA-256 `market-stream.model.spec.ts` checks with `crypto.subtle`; `.prettierignore` skips the folder.
- **Copy with `cp`, never re-serialise.** A change is a contract change in all three repositories at once. The three-way `cmp` (canonical = service = bot = web) passed at 2026-10-11T08:14Z.
- ORCH-2 pinned the shared contracts in the service plan's `contracts.md`. ORCH-10 let the copies land before service S1, provided `cmp` checks them.

(source: raw/2026-10-11-signals-ingest.md §API, C-SIG-1; §Concept, Stage, Verified locally; §Concept, ORCH-2 and ORCH-10)

## The message

One JSON object with no whitespace and every key present, in this order:

`v, type, instrument_id, signal_id, document_id, source_code, tier, event_type, direction, p, impact, severity, created_at`

- `p`, `impact` and `severity` are **decimal strings** with 3, 4 and 2 fraction digits, never numbers.
- `created_at` is the `signals` row's own `created_at` (from `RETURNING`), in RFC 3339 UTC with `Z`, with a millisecond fraction only when it is non-zero.
- **Readers.** The service reads `v`, `type` and `instrument_id`. The web reads `v`, `type`, `instrument_id`, `signal_id` and `created_at`, and since slice 4 also `tier`, `source_code` and `impact`, read leniently (see below). The rest is there for later consumers.

```json
{"v":1,"type":"signal","instrument_id":"NVDA@webull","signal_id":"019a…","document_id":"019a…",
 "source_code":"sec-edgar-8k","tier":"filing","event_type":"earnings","direction":"up","p":"0.867",
 "impact":"0.4224","severity":"3.20","created_at":"2026-10-11T20:06:12.345Z"}
```

**The file also holds:**
- the vocabularies `tiers`, `event_types` and `directions`;
- four `examples`: an NVDA 8-K up, an AAPL wire down in the last half-second of a Bangkok day, a PTT.BK SET neutral at exactly Bangkok midnight, and an NVDA media up;
- eight `service_drops`: a `tick` on `sig:`, a `signal` on `px:`, `v` 2, no `v`, an instrument mismatch, a wrong JSON type, invalid JSON and two JSON values.

(source: raw/2026-10-11-signals-ingest.md §API, C-SIG-1)

## Bot: publish after commit

- The C-SIG-1 builder and `publishSignal` live in `packages/market-data/src/redis/contract.ts` and `publisher.ts`.
- Only after the signal transaction commits is each row logged `signals_emitted`, counted, and published to `sig:<instrument_id>`. The channel comes from the message's own `instrument_id`.
- A signal is **never throttled or coalesced**, unlike `tick` on `px:<id>`.
- A failed publish logs `signals_publish_failed` (`error_class`, under its own 30 s interval) and rolls nothing back. Nothing is replayed; consumers resync from REST.
- The service never writes `sig:*`. Where the channel sits beside `px:*` is on [[redis-market-contract]].

(source: raw/2026-10-11-signals-ingest.md §API, The signal transaction and the publish; §Files touched, tidewatch-bot; §API, Service)

## Service: forward on `/ws`

- For every instrument with a subscriber, the hub's desired set holds both `px:<id>` and `sig:<id>`. One client `subscribe` covers both.
- On `sig:<id>`, the only accepted type is `signal`. `market.ParseSignalHeader` must accept the header: `v` 1, `type` `"signal"`, and `instrument_id` equal to the channel's id. The payload is then forwarded **byte for byte** through the same `forward` path as prices, with the same ordering and the same 1013 eviction.
- **Everything else is dropped silently:** a bad header, a mismatched id, a `signal` on `px:`, a header key in a case variant (exact keys only, security M1, `2fec95d`) and a payload that is not valid UTF-8 (L1). A drop counts nothing and leaves the socket open.
- There is **no snapshot and no replay** for signals.
- `ws_messages_sent_total{type}` gained the label `signal`. The details are on [[realtime-websocket]].

(source: raw/2026-10-11-signals-ingest.md §API, `/ws` forwarding; §Test plan, Reviews)

## Web: counting a signal once

- **Frame.** `parseStreamFrame` (`data/market-stream.model.ts`) accepts `{"type":"signal","v":1,…}` as `SignalMessage {type:'signal', instrument_id, signal_id, created_at}`. `signal_id` must be a non-empty string of at most 64 characters, and `created_at` must be an instant. Anything else returns null.
- **Counting** (`feat-overview/util/apply-stream-message.ts`, `market-watch.service.ts`). A `signal` raises a row's `signals.today` by one when all of these hold:
  - the row is listed and its `signals` is not `null`;
  - `created_at` falls on the **Bangkok day of the loaded body's `generated_at`**. The browser clock plays no part: there is no `Date.now()` in the counting path;
  - the `signal_id` has not been counted on that row since the last successful load.
- **Rules around it.**
  - Each row remembers at most 200 ids, and the oldest is forgotten.
  - Only a successful load empties the ids and moves the counting day. A failed reload keeps both (MW-20).
  - A signal triggers no reload, timer or request. The 5-minute reload (MW-12) resyncs the count from REST (`GET /market-watch`, see [[market-data]]).
  - After Bangkok midnight, the cell keeps day D's count until the next successful load brings D+1: at most 5 minutes while reloads succeed. There is no midnight reload.
  - The signal path is pure.
- How the cell renders the count is on [[design-system-decisions]].

(source: raw/2026-10-11-signals-ingest.md §Components, Stream frame and Counting)

## Slice 4: the all-signals feed and the Signals page

**The contract is unchanged.** The fixture `signals-message.v1.json` (sha256 `a0829396…e7d1`) is still byte-identical in the bot, the service and the web (source: raw/2026-10-12-signals-page.md §Concept, Cross-project contracts).

- **A second delivery path.** A `/ws` connection that sends `{"op":"subscribe_signals"}` receives every C-SIG-1 `signal` frame, bytes unchanged, **once**, even when it also subscribed to that instrument. The service backs it with `PSUBSCRIBE sig:*`. Details are on [[realtime-websocket]] and [[redis-market-contract]].
- **The web reads three more fields, leniently (SP-W-16).** `SignalMessage` gains `tier`, `source_code` and `impact`. Because they are read leniently, Market watch's count is unchanged.
- **Counting on the Signals page (SP-W-18, S10).** A `signal` frame counts as new only when all of these hold:
  - its `created_at` falls on the loaded Bangkok day, taken from `generated_at` and never from the browser clock;
  - its tier and source are pressed in the filters;
  - its impact is at or above the threshold;
  - its id is neither listed nor already counted. At most 500 ids are remembered, and they are cleared on each successful list load.

  The asset class is not applied.
- **The note, not the table.** Waiting rows read "{n} new signals" (or "1 new signal") with *Show*. Nothing is inserted and nothing scrolls, and the table is not a live region. *Show* reads the list with `since` set to the newest listed `created_at` and `limit=200`, then prepends the rows (see [[signals-read-api]]).
- **Midnight (as merged in slice 4).** The page counted only frames on its loaded Bangkok day, and the UI had no day control. After Bangkok midnight it showed an empty day until new signals arrived. A day control was the owner-requested follow-up ORCH-19 (see [[signals-page]]).

(source: raw/2026-10-12-signals-page.md §API, `/ws`: the all-signals feed; §Components, SignalsService and Data layer; §Concept, Plan resolutions, Web SP-W-16; §Concept, ORCH-19)

**Counting since the day control (tidewatch-web#13, merged 2026-10-14, not deployed).** The C-SIG-1 bytes, the fixture and `new-signals.ts` are unchanged; `new-signals.ts` stayed byte-identical. What changed is what the Signals store passes in (SDC-W-1):
- **Only Today counts.** The store passes the list's `generated_at` only while the shown day is Today. On a past day it passes `null`, so no frame counts and *Show* is not offered.
- **At the midnight rollover** the page keeps Today's rows and relabels them *Yesterday*. From then on it passes `null`, so frames for the new day are not counted on that page. Ids already counted before the rollover stay with *Show* until revealed (S1).
- **The feed stays held** whatever day is shown; only the counting stops (see [[realtime-websocket]]).
- The service's "today" is the Bangkok day of `generated_at`, never the browser clock, as before.

See [[signals-day-control]] (source: raw/2026-10-14-signals-day-control.md §Concept, SDC-W-1 and Spec-level defaults S1; §Components, `SignalsService` store; §Files touched, Not changed; §Cross-cutting links).

**Verification (FR-SP-E2E-001, passed with an injected publish).** A C-SIG-1 copy was published on `sig:AAPL@webull` while the page was on `/signals?asset=crypto&min_impact=0.00`. AAPL is not crypto, and the frame still counted, because the asset class is not applied. The note changed to "1 new signal Show" **97 ms** after the PUBLISH. `scrollY` stayed at 17, and there was no request, navigation or DOM change outside the note. **No real bot publish arrived in 25 minutes** of watching `PSUBSCRIBE sig:*`, so only the service → web leg was observed, not bot → Redis (source: raw/2026-10-12-signals-page.md §Test plan, Acceptance status).

## Slice 5: the Chart's markers

Charting (tidewatch-web #14, merged 2026-10-16, not deployed) made the Chart a third web consumer of the `signal` frame. **The contract is unchanged:** the bot (including its C-SIG-1 reader list) was not changed, and the service forwards the frame as before.
- **The frame only triggers a read.** C-SIG-1 carries no headline, so the Chart draws signal markers only from the REST read `GET /instruments/{id}/signals` (CH-W-9; see [[signals-read-api]]).
- **When it re-reads.** A `signal` frame whose `signal_id` is not already listed bumps that re-read, even while one is in flight; the resource aborts the older read, and there is one read per burst tick (CH-BUILD-10). The marker and the *Signals on this chart* item appear when the read answers.
- **"Within 2 s"** holds unless more than about 20 new ids arrive per second for more than 2 s.
- **Verification.** FR-CH-E2E-003 is **partial** (owner decision CH-BD-3). On the preview, an injected C-SIG-1 frame (`sig:ETHTHB@binance-th`, "PV2 injected test signal") reached the page and triggered the re-read at +81 ms, and +85 ms in the second round. The read answered 0 items, because an injected id has no database row. No real signal arrived during either run, so the drawing within 2 s is proven only on the mocked `chart-live.spec.ts`. The real check waits for the first real signal after merge.

(source: raw/2026-10-16-charting.md §Components, Realtime (S7); §Concept, Planner reconciliations CH-W-9, Recorded build behaviours CH-BUILD-10 and Build decisions CH-BD-3; §Test plan, Acceptance status and Preview runs; §Files touched, Not changed; §Cross-cutting links)

## Signals context: coverage signals are ordinary messages (2026-10-30)

- **C-SIG-1 is unchanged** (`signals-message.v1.json`). No new Redis key and no new `/ws` frame.
- **Who publishes.** Besides `runner:signals`, the bot's `context` runner now publishes a coverage signal on `sig:<instrument_id>` after its own commit. A failed publish rolls nothing back, the same rule as the pipeline's (see [[context-features-and-coverage-signals]]).
- **What it carries.** `impact "0.0000"` and `p "0.000"`. The key list is unchanged, so the frame has no `origin` field.
- **Consumers.** The Market watch count and the Signals page count both origins. The bot's own trigger reads use the database and filter `origin = 'document'`, not this channel (see [[bots-engine]]).
- **Verified.** "context: publishes C-SIG-1 after commit"; on the preview a coverage signal reached Redis through the bot's own code. **In production the `context` runner is not running yet,** so no coverage signal is published there.

(source: raw/2026-10-30-signals-context.md §API, 3. Signals routes, C-SIG-1; §API, No new route; §Concept, How it runs, 4. Coverage signals and 6. Never a trigger; §Test plan, Unverified end-to-end checks)

## Compatibility (PRD §6.6)

- An old service ignores `sig:` and keeps `signals: null`.
- A new service with an old bot shows 0 everywhere.
- A new web with an old service accepts `null` and shows the dash.

(source: raw/2026-10-11-signals-ingest.md §API, Compatibility)

## Verification

- **Bot → Redis.** 43 real C-SIG-1 publishes between 10:01:00Z and 10:04:41Z, equal to the 43 `signals` rows committed in that window, none for a watched row (FR-SIG-BRN-007).
- **Service → web.** An orchestrator-injected C-SIG-1 on `sig:NVDA@webull` was published at 10:37:30.630Z, and the frame arrived at 10:37:30.682Z. NVDA went from 2 to 3 ("3 signals today") with no reload or navigation, and the scroll position did not change (FR-SIG-E2E-004, the web plan's P2 fallback).
- **Not observed.** A full bot → web update on a watched row was never seen in the 43-minute window.
- Named tests: service `TestHub_Dispatch_SignalForwardedUnchanged`, `TestHub_Dispatch_SigDropsFromFixture`, `TestRealtime_SignalForwarded`; bot `publishes the C-SIG-1 message after commit and never rolls back on a failed publish`; web `market-stream.model.spec.ts` (the pin, the example payloads and the five frame-level drops) and `apply-stream-message.spec.ts`, run under two host time zones including `TZ=America/New_York`.

(source: raw/2026-10-11-signals-ingest.md §Test plan, Acceptance at merge and Named acceptance tests)

## Follow-ups

- **Service:** apply exact-key decoding to `ParsePxHeader` too, a pre-existing weakness; cap the forwarded `sig:` payload size, for example by dropping payloads over 4 KiB (security L2); test that a `sig:` message triggers the 1013 slow-consumer eviction (security L3).
- **Web:** validate `generated_at` with `isTimestamp` and require a `Z` or an offset on the signal's `created_at`; the midnight gap (SW-10).

(source: raw/2026-10-11-signals-ingest.md §Open questions, Follow-ups)

## Related pages

- [[signals-pipeline]]: the signal transaction that the publish follows
- [[redis-market-contract]]: the `sig:` channel beside `px:*` and `md:subscriptions`
- [[realtime-websocket]]: the `/ws` hub that forwards the `signal` frame
- [[market-data]]: the REST `signals.today` count that the live count resyncs to
- [[design-system-decisions]]: the Signals cell
- [[bot-watch-verdicts]]: contract C11, the byte-pinned shared-fixture pattern this follows
- [[signals-ingest]]: the slice-3a overview
- [[signals-page]]: the slice-4 overview, whose live note counts these frames
- [[signals-day-control]]: the *Day* select, which counts frames only while the shown day is Today
- [[charting]]: slice 5, whose Chart turns a new `signal_id` into a REST re-read and a marker
- [[context-features-and-coverage-signals]]: the coverage signals that ride this message unchanged
