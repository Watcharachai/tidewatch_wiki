# Redis market contract

**Summary**: The only channel between `tidewatch-bot` and `tidewatch-service`. The bot writes `px:last:<id>` and publishes `tick`, `bar`, `zone` and `status` messages on `px:<id>`, and since slice 3a (signals-ingest, 2026-10-11) one `signal` message per new `signals` row on `sig:<id>`. The service publishes `md:subscriptions` when a watchlist changes. Payloads are versioned with `v`, Redis DB 0 is ephemeral and never backed up, and there is no HTTP between the two. Slice 2 (paper trading) added no key, channel or env variable. It reuses `px:last` for trading hours and mark prices. Slice 2b (zone-transition bot) added nothing either; its runner reuses the same `px:last` freshness bound through the bot's in-memory price view. The bot-activity feature (2026-10-10) also added no key, channel or `/ws` message; its watch route reads `px:last` with one `MGET` to decorate each item with a session and next-open time, and degrades to `unknown` when Redis is absent. The signals page (slice 4, 2026-10-12) also added no key or channel. Its only new Redis operations are `PSUBSCRIBE` and `PUNSUBSCRIBE sig:*` on the service's one subscriber connection, and its signal detail reads a usable `px:last` once for the market context and the recommendation. Bots (slice 6, merged 2026-10-21, not deployed) added no key, channel or `/ws` message either: the Redis contract and `/ws` are unchanged, and the bot's guard reads the bot's own in-process recorded `px:last` view, not Redis.

**Sources**: `raw/2026-10-07-market-data.md`; `raw/2026-10-07-fix-xau-feed-binance-th.md`; `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-21-bots.md` (no change; the guard's price view only)

**Last updated**: 2026-10-21

---

## Keys and channels (PRD §6.3)

| Key or channel | Written by | Payload |
|---|---|---|
| `px:last:<instrument_id>` (string, TTL 7 days) | bot, status publisher only | `{"v":1,"price","ts","mode","stale","session","next_open_at","next_close_at","updated_at"}` |
| `px:<instrument_id>` (pub/sub) | bot | `tick` (at most 4 per second), `bar` (closed 1m bars only, after the upsert commits), `zone` (after a strip-timeframe indicator row persists; `ema12` and `ema26` as decimal strings), `status` (on change) |
| `md:subscriptions` (pub/sub) | service | `{"v":1,"type":"watchlist_changed"}` |
| `sig:<instrument_id>` (pub/sub, since slice 3a) | bot, `publishSignal` only | `signal`: the C-SIG-1 message, one per committed `signals` row, never throttled or coalesced (see [[signal-message-contract]]) |

(source: raw/2026-10-07-market-data.md §API, Redis contract; raw/2026-10-11-signals-ingest.md §API, C-SIG-1 and The signal transaction and the publish)

## Rules

- Consumers ignore unknown types and fields; a breaking change bumps `v`.
- The service never writes `px:*` or (since slice 3a) `sig:*`, and the bot reads no `md:*` channel except `md:subscriptions` (source: raw/2026-10-11-signals-ingest.md §API, Service).
- The status publisher is the single writer of `px:last` and `status`, guaranteed by the `runner:serve` lock (see [[market-data-worker]]).
- A `bar` is published only after its upsert commits (persist, then publish), and a `zone` only after its indicator row persists.
- DB 0 is ephemeral and never backed up. Redis holds nothing the service owns.

(source: raw/2026-10-07-market-data.md §API, Redis contract; §Components, Runtime pieces and Recovery notes)

## Service side

- **Redis is optional and never a readiness input.** An empty `REDIS_URL` gives a nil client: REST works, `/ws` answers `503 realtime_unavailable` and `redis_up` stays 0.
- The client (`github.com/redis/go-redis/v9`) uses a 1 s dial timeout, a pool of 4 for `MGET` and `PUBLISH`, and one pub/sub connection. `internal/platform/redis` owns the single subscriber, which owns `redis_up`. `internal/repository/redis/{lastprice,notify}.go` read `px:last` and publish `md:subscriptions`.
- Every committed watchlist change, seeding included, publishes `md:subscriptions` once, best effort. A failure, or Redis being down, logs `md_subscriptions_publish_failed` and never rolls the change back.
- Tests use `miniredis` for units and `internal/redistest`, an integration-only loopback Redis with a cuttable `Proxy`, for outages.

(source: raw/2026-10-07-market-data.md §Components, tidewatch-service; §API, Watchlist; §Concept, Libraries)

How the service fans `px:<id>` out to browsers is on [[realtime-websocket]].

## Bot side

- `REDIS_URL` is required by the bot, and its `/ready` checks Redis with `PING`.
- The subscription manager recomputes the live sets within about 1 s of an `md:subscriptions` message, and every 60 s regardless.
- For a Binance TH instrument on a non-crypto calendar (`XAUUSD@oanda-demo` on `gold-23-5`, since the XAU fix), ticks and bars outside the session are dropped before anything is published, so `px:last` carries no out-of-session prints, `stale` is `false` while the session is open, and outside it the row reads *Closed · opens …*, never *Stale*. The `ts` of a stored closed bar is the bar's close time. No key, channel or payload shape changed (see [[gold-feed-xaut-proxy]]).

(source: raw/2026-10-07-market-data.md §Components, packages/shared, Runtime pieces and Bot HTTP endpoints; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, The correction and Caller-visible implications; §API; §Test plan, Specs that pin the behaviour)

**The bots guard does not read Redis (slice 6).** The general engine's guard checks stops, invalidation and exposure from the recorded `px:last` view that `serve` shares with `sim` and the 2b pass, fresh within 120 s; a stale price is `deferred` with `["price_unavailable"]`. So a price published to Redis by hand never reaches the guard: on the preview, the stop check raised `stop_px` by SQL instead (FR-BT-E2E-004). *Run now* also needs no Redis: it travels through the `bot_run_requests` table (see [[bots-engine]]) (source: raw/2026-10-21-bots.md §The bot engine, Guard; §Concept, Spec decisions S10; §Test plan, The E2E checks; §Files touched, Not changed).

## How the Market watch row uses `px:last`

- **`last`.** `px:last` wins when its `ts` is after the latest stored bar's end; otherwise the stored close is used. `ts` is never after `generated_at` (ORCH-30).
- **`status`** `{mode, stale, session, next_open_at, delay_minutes}` is passed through from `px:last`. Without `px:last`, the row is `stale: true` with session `unknown` (ORCH-10), with mode `synthetic`, `eod` or `live` derived from the instrument, and the web shows *Stale*.

(source: raw/2026-10-07-market-data.md §API, Market watch row; §Concept, ORCH-10 and ORCH-30)

## How paper trading uses `px:last` (slice 2)

Slice 2 added no Redis key, channel or env variable, and nothing new on `/ws` (source: raw/2026-10-08-simulation-engine.md §API, Bot ↔ service).

- **Service, trading hours (SIM3).** The service has no calendar logic. It reads session state from `px:last`. A closed session refuses an order with `venue_closed` and `next_open_at`. An open session with a stale or missing price refuses it with `price_unavailable`. Manual MTS orders skip only the stale check, and a stale `px:last` also refuses a skip (R15).
- **Freshness bound (C6 rule 2).** `px:last` counts as a mark price when `ts ≤ t`, `stale` is false, and `updated_at ≥ T − 120 s`. The 120 s bound is pinned from the status publisher's 60 s rewrite interval. Without a usable `px:last`, the mark falls back to stored closes (see [[paper-trading]]).
- **Bot side.** The `sim` runner never reads Redis for marks. It reads the status publisher's in-memory `px:last` record through a price view that wraps `writeLast` (`packages/sim/src/price-view.ts`), with the same 120 s bound.
- `px:last` is not stored, so a benchmark valued at a fill mark is only indicative when re-checked later (FR-SIM-E2E-003 note).

(source: raw/2026-10-08-simulation-engine.md §Concept, Chosen design and C6; §API, Intake order and Bot runner `sim`; §Test plan, Acceptance status)

**Slice 2b (zone-transition bot)** also added nothing to Redis or `/ws`; the Bots screen polls REST every 10 s. The new `bots` runner reads the same recorded `px:last` view as `sim`, never Redis, with the same 120 s freshness bound. Because that view does not keep the session, the runner checks `inSession` on the instrument's calendar instead of the `px:last` session field (R22). A closed session or a stale price defers the bot's action and writes nothing (see [[zone-transition-bot]]) (source: raw/2026-10-09-zone-transition-bot.md §API, Bot runtime; §Concept, Plan resolutions, Bot R22; §Cross-cutting links).

## How the bot watch route uses `px:last` (bot-activity)

`GET /bots/{bot_id}/watch` (see [[bot-watch-verdicts]]) adds no Redis key, channel, `/ws` message or environment variable. The Bots screen keeps polling REST every 10 s.

- **One `MGET` after the database snapshot.** The service reads `px:last` for the items' instruments through the existing `ParseLastPrice` / `NormaliseSession`, after the snapshot closes (SA5, SA6).
- **Stricter than Market watch (R4, "stale or missing → unknown").** Market watch passes a present `px:last` session through even when it is stale. The watch route uses `px:last` only when it is valid, `stale = false` and `updated_at` ≥ `generated_at − 120 s` (`LivePriceMaxAge`). Then it supplies `session` and `next_open_at`; otherwise the item reads `session: "unknown"` and null.
- **A closed session still reads `closed`,** because the publisher rewrites `px:last` every 60 s and staleness is never true while a calendar is closed. A value left by a stopped publisher never claims a session.
- **`next_bar_at`** is the first UTC hour boundary after `generated_at`, set only for a `1h` item whose session is `open`.
- **Redis absent never fails the route.** Without `REDIS_URL`, with the subscriber down, or on an `MGET` error, the answer is 200 with every session `unknown` and every `next_*` null. Only the `MGET` error logs the existing warn `last_price_read_failed`. Redis stays out of readiness.
- **Observed on the preview.** While the whole bot worker was stopped, every Watch *Next* cell read "— no session state", because `px:last` comes from the stopped worker's status publisher. In the owner-session validation, *Next* equalled `px:last`.
- **Follow-up.** A usable `px:last` whose session normalises to `unknown` passes its `next_open_at` through (contract-literal; the web shows "—").

(source: raw/2026-10-10-bot-activity.md §API, Service routes; §Concept, Plan resolutions, Service SA5, R4; §Concept, Cross-project contracts, Unchanged; §Test plan, Preview phases; §Open questions, Service)

## The `sig:` channel (signals-ingest, slice 3a)

Slice 3a added the first new channel since slice 1. It added no Redis key, no new environment variable and no service-side Redis code (`internal/platform/redis` and `internal/repository/redis` are unchanged by design).

- **Bot side.** The signals runner publishes each `signals` row to `sig:<instrument_id>` **after its transaction commits**, with the byte-pinned C-SIG-1 bytes. The channel comes from the message's own `instrument_id`. A failed publish logs `signals_publish_failed` and rolls nothing back. Like `px:<id>`, nothing is replayed after a failure or an outage, and consumers resync from REST.
- **The service never writes `sig:*`.** Its hub subscribes to `sig:<id>` beside `px:<id>` for every instrument with a subscriber, accepts only `type: "signal"` there with an exact-key header check, and forwards the payload unchanged (see [[realtime-websocket]]).
- **Separation by prefix.** A `signal` on `px:` and a `tick` on `sig:` are both dropped silently by the service; both are listed in the fixture's `service_drops`.
- Signals are published for every instrument, watched or not. Only watched instruments have a `/ws` subscriber, so only they reach a browser.

(source: raw/2026-10-11-signals-ingest.md §API, Service; §API, `/ws` forwarding; §API, C-SIG-1; §API, The signal transaction and the publish; §Concept, What the user sees; §Files touched, tidewatch-service)

## Pattern subscription `sig:*` (signals page, slice 4)

The all-signals `/ws` feed (see [[realtime-websocket]]) needs every signal, watched or not. The service gets them with a pattern subscription instead of a new channel. Environment variables, secrets, compose, dependencies and Redis keys are unchanged.

- **Desired set.** The hub hands the subscriber `Channels.SetDesired(channels, patterns []string)`. The channels are the `px:<id>` channels of subscribed instruments, plus their `sig:<id>` channels **only while no connection is flagged**. The pattern `sig:*` is desired while any connection is flagged.
- **One connection.** The subscriber applies `PSUBSCRIBE`/`PUNSUBSCRIBE` on its one existing pub/sub connection (A2 held: go-redis v9.9.0 `PSubscribe`).
- **Add before drop.** The order is `SUBSCRIBE`, `PSUBSCRIBE`, then `UNSUBSCRIBE`, `PUNSUBSCRIBE`, with one command each. It never sends an argument-less unsubscribe, and it re-applies the whole set on a new connection.
- **Pattern messages.** A pattern message reaches `OnMessage` with its concrete channel and goes through the same header rules as a plain `sig:<id>` message.
- **At most once (R15).** A pattern copy passes only while its pattern is desired. A plain copy passes only while its channel is desired and no desired pattern matches it. A frame published inside one reconcile may be missed but is never duplicated, except across two flag flips within one hand-over (a follow-up; the web dedupes by `signal_id`).
- **Errors.** `redis_subscriber_reconcile_failed` now reads `redis: <cmd> N names: ...` and never names a channel.
- **Tests.** `TestRealtime_SignalsFeed_ResumesAfterOutage` covers re-applying the set after an outage.

(source: raw/2026-10-12-signals-page.md §API, `/ws`: the all-signals feed, Redis side and Metrics; §API, Configuration and compatibility; §Concept, Plan resolutions, Service R15; §Test plan, Assumption outcomes A2; §Open questions, Service follow-ups)

**`px:last` in the signal detail and the recommendation.** `GET /signals/{id}` reads `px:last` **once** (since review-fix r1) and shares the value between the market context and the recommendation. For the recommendation, `px:last` counts only when it is valid v1, not stale, and at most 120 s old, the same bound as the paper-trading checks. A stale price makes the recommendation `null` rather than an error. That is why FR-SP-E2E-004 could not run on the preview: both of the day's signals were US stocks with a stale `px:last` while the market was closed. The context's `latest_price` uses a usable `px:last`, else the latest strip close. See [[signal-cited-orders]] and [[signals-read-api]] (source: raw/2026-10-12-signals-page.md §API, `SignalDetail`; §Concept, Plan resolutions, Service R7/R8; §Test plan, Acceptance status FR-SP-E2E-004).

## Outage behaviour

While Redis is down, REST keeps working and rows read `stale` with session `unknown`. New `/ws` upgrades get `503 realtime_unavailable`; open sockets stay open and silent, and resume once the subscriber reconnects (backoff 100 ms to 5 s). Messages published during an outage are not replayed (source: raw/2026-10-07-market-data.md §Components, Recovery notes; §API, Fan-out).

## Related pages

- [[realtime-websocket]] — the `/ws` hub that forwards `px:<id>` messages byte for byte
- [[market-data-worker]] — the status publisher and bar sink that write these keys
- [[market-timeseries]] — the `bar` and `zone` data behind the messages
- [[gold-feed-xaut-proxy]] — why `px:last` for XAU/USD carries no out-of-session prints
- [[market-data]] — the slice overview and the watchlist routes that publish `md:subscriptions`
- [[paper-trading]] — the trading hours check and the C6 mark-price rule that read `px:last`
- [[zone-transition-bot]] — the `bots` runner's session and price check before each action
- [[bot-watch-verdicts]] — the watch route's session and `next_bar_at` decoration from `px:last`
- [[signal-message-contract]] — the C-SIG-1 message on `sig:<instrument_id>`
- [[signals-pipeline]] — the signal transaction that each `sig:` publish follows
- [[signals-page]] — slice 4, which added the `sig:*` pattern subscription
- [[signal-cited-orders]] — the recommendation that needs a usable `px:last`
- [[bots-engine]]: the guard that reads the recorded `px:last` view, not Redis
