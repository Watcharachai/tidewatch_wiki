# Realtime WebSocket (`GET /ws`)

**Summary**: The service's `GET /ws` hub forwards the bot's price messages from Redis to signed-in browsers, and since slice 3a (signals-ingest, 2026-10-11) also a `signal` frame for each new signal. An upgrade passes seven ordered checks, with an exact Origin match standing in for the CSRF header. The client protocol is small and strictly bounded; one `subscribe` covers both an instrument's prices and its signals. A 60 s session re-check that never extends the session closes sockets with 4401 or 4403, and the fan-out is per process. Since the signals page (slice 4, 2026-10-12), a connection may also opt into **every** `signal` frame with `subscribe_signals`. That per-connection flag is outside the 100-subscription limit, and the service backs it with one `PSUBSCRIBE sig:*`. Since charting (slice 5; tidewatch-web #14, merged 2026-10-16, not deployed), the Chart screen is a third web consumer. It folds closed 1m `bar` frames into the forming bar, so the web now reads their `o`, `h`, `l` and `v`, and it turns `zone` and `signal` frames into REST re-reads. **No `/ws` protocol, frame or service code changed.** **Since accounts and roles (merged and deployed 2026-10-29),** the role check and the re-check require role `user`, no longer `admin`. A person disabled in the operator console has their sockets closed with **4401** at the next 60 s re-check. An operator's `tw_admin` cookie is refused at the upgrade with `401` and no `101`.

**Sources**: `raw/2026-10-07-market-data.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-14-signals-day-control.md` (the reconnect across midnight); `raw/2026-10-16-charting.md` (the Chart as a consumer); `raw/2026-10-29-accounts-roles.md` (role `user`, the disabled-person close and the operator cookie only)

**Last updated**: 2026-10-29

---

## Pre-upgrade checks, in order

Plain HTTP answers with the standard error envelope, pinned by `TestRouter_WS_CheckOrder`:

1. ready (`503 not_ready`);
2. exact `Origin` (`403 origin_rejected`): missing, repeated, `null` or not the app origin all fail;
3. session (`401 unauthenticated`);
4. role `user` (`403 forbidden`). This read `admin` until accounts and roles (2026-10-29); `RoleAdmin` was deleted;
5. no forced password change pending (`403 password_change_required`);
6. Redis pub/sub answering (`503 realtime_unavailable`; also when `REDIS_URL` is empty or the service is shutting down);
7. fewer than 5 connections for this user (`429 too_many_connections`, per process).

Then the service's own handshake check runs. A non-upgrade `GET /ws` gets `400 invalid_request` with `details.reason` `upgrade_required` (source: raw/2026-10-07-market-data.md §API, WebSocket and New error codes).

**The operator cookie is not a session here.** `/ws` sits in the product group. An upgrade carrying only an operator's `tw_admin` gets `401` at step 3 with no `101` and no `Set-Cookie` (E2E-002, `TestCrossPrincipal_Cookies`) (source: raw/2026-10-29-accounts-roles.md §API, Gates and route groups; §Test plan, What each E2E check showed, E2E-002).

**Why no CSRF header.** There is no CSRF header on an upgrade, and the web client's socket carries no token, query or custom header. The exact Origin check plus the `SameSite=Lax` session cookie is the cross-site defence. See [[request-protection]] for the Origin rules and [[auth-model]] for the session and forced-change gates (source: raw/2026-10-07-market-data.md §API, WebSocket; §Components, tidewatch-web Data layer).

## Protocol

**Client to server.** `{"op":"subscribe"|"unsubscribe","instruments":[…]}`. Text JSON only, at most 4 KiB per message, 10 messages per second, 100 ids per message and 100 subscriptions per connection. One batched `InstrumentRepo.Existing` query checks a whole subscribe (ORCH-27). Since slice 4, also exactly `{"op":"subscribe_signals"}` and `{"op":"unsubscribe_signals"}` (see "The all-signals feed" below).

**Server to client.**
- `subscribed`, with `rejected[].code` one of `invalid_instrument_id`, `unknown_instrument` or `subscription_limit`;
- one `snapshot` per accepted id that has a valid `px:last`;
- `unsubscribed` (R3, added beyond the PRD);
- `signals_subscribed` and `signals_unsubscribed` (since slice 4);
- `tick`, `bar`, `zone` and `status`, forwarded byte for byte from Redis (shapes on [[redis-market-contract]]);
- `signal` (since slice 3a), forwarded byte for byte from `sig:<id>` (shape on [[signal-message-contract]]);
- `error` with code `bad_message`, `rate_limited` or `message_too_large`.

(source: raw/2026-10-07-market-data.md §API, WebSocket; §Concept, ORCH-7 and ORCH-27; raw/2026-10-11-signals-ingest.md §API, `/ws` forwarding)

## Signal forwarding (signals-ingest, slice 3a)

tidewatch-service PR #8 (merge `2f9854f`, 2026-10-11) added no route, error code, log event, environment variable or dependency. Client frames, limits and close codes are unchanged.

- **Dual-prefix desired set.** For every instrument with a subscriber, the hub's desired set holds both `px:<id>` and `sig:<id>`. One client `subscribe` covers both.
- **Header check.** On `sig:<id>` the only accepted type is `signal`. `market.ParseSignalHeader` must accept the header: `v` 1, `type` `"signal"`, and `instrument_id` equal to the channel's id. The payload is then forwarded **byte for byte** through the same `forward` path as prices, with the same ordering and the same 1013 eviction.
- **Silent drops.** A bad header, a mismatched id, a `signal` on `px:`, a header key in a case variant, and a payload that is not valid UTF-8 are all dropped. A drop counts nothing and leaves the socket open.
  - The exact-key rule came from security review M1 (`2fec95d`). The header used to be decoded case-insensitively with the last key winning, while the browser reads exact keys.
  - The UTF-8 rule came from L1. Before the fix, invalid UTF-8 was forwarded.
- **No snapshot and no replay for signals.** The REST count resyncs on the web's reload.
- **Metric.** `ws_messages_sent_total{type}` now has nine labels: `subscribed`, `unsubscribed`, `snapshot`, `tick`, `bar`, `zone`, `status`, `signal` and `error`.
- **Code.** `internal/market/feed.go` gained `SigChannel` and `ParseSignalHeader`; `internal/services/realtime/hub.go` and `ports.go` changed. `protocol.go` and `subscriber.go` are unchanged by design.
- **Web client.** `parseStreamFrame` accepts the `signal` frame. A signal raises the Market watch count without triggering a reload, unlike a `zone` message (see [[signal-message-contract]]).

(source: raw/2026-10-11-signals-ingest.md §API, `/ws` forwarding; §Files touched, tidewatch-service; §Test plan, Reviews; §Components, Stream frame and Counting)

**Follow-ups.** Apply exact-key decoding to `ParsePxHeader` too, a pre-existing weakness. Cap the forwarded `sig:` payload size, for example by dropping payloads over 4 KiB (security L2). Test that a `sig:` message triggers the 1013 slow-consumer eviction (L3) (source: raw/2026-10-11-signals-ingest.md §Open questions, Follow-ups).

## The all-signals feed (signals page, slice 4)

Before slice 4, `/ws` forwarded a `signal` frame only to connections subscribed to that instrument, at most 100 per connection. The Signals page needs every signal of the day, so tidewatch-service PR #10 (merge `8b18486`, 2026-10-12) added a per-connection flag (S2).

- **Client messages:** exactly `{"op":"subscribe_signals"}` and `{"op":"unsubscribe_signals"}`. Any other key is `{"type":"error","code":"bad_message"}`, and that includes an `instruments` key, even `[]` or `null`.
- **Acknowledgements:** `{"type":"signals_subscribed"}` and `{"type":"signals_unsubscribed"}`. Both are idempotent.
- **The flag.**
  - It is per connection, so a reconnect starts without it.
  - It is membership in `hub.allSignals`. It never counts toward the 100 subscriptions or `ws_subscriptions`, and the new gauge `ws_signal_feeds` counts it.
  - The 10-messages-per-second and 4 KiB limits count these messages.
  - The acknowledgement and the flag change happen in one write-locked section, and forwarding holds the read lock. So no frame arrives before `signals_subscribed` or after `signals_unsubscribed`.
- **Delivery.** A flagged connection receives every C-SIG-1 `signal` frame with its bytes unchanged, **once**, even when it also subscribed to that instrument. Eviction on a full queue is still 1013.
- **Redis side.** The hub hands the subscriber a desired set of channels and patterns: the subscribed instruments' `px:<id>` channels, plus the `sig:<id>` channels only while no connection is flagged, or the pattern `sig:*` while any connection is. How the subscriber applies `PSUBSCRIBE`, and the R15 at-most-once rule, are on [[redis-market-contract]].
- **Metrics.** `ws_messages_sent_total{type}` gains `signals_subscribed` and `signals_unsubscribed`, so it now has eleven types. `redis_subscriber_reconcile_failed` now reads `redis: <cmd> N names: ...` and never names a channel. No other limit, close code or frame changed.
- **Code.** `internal/services/realtime/{ports,hub,protocol,conn}.go` and `internal/platform/redis/subscriber.go` changed. `protocol.go` and `subscriber.go` had been left unchanged by design in slice 3a.

(source: raw/2026-10-12-signals-page.md §API, `/ws`: the all-signals feed; §Concept, Problem; §Files touched, tidewatch-service)

**Web client.**
- `MarketStream.acquireSignals()` is reference-counted, like instrument interest.
- Each new connection sends `subscribe_signals` first, then the instrument diff, within the 10-frames-per-second budget. A connection used only for the feed opens and recovers like any other.
- `parseStreamFrame` reads the two acknowledgements. The first `subscribed` **or** `signals_subscribed` counts as the connection's acknowledgement (SP-W-17).
- How the Signals page counts the frames is on [[signal-message-contract]].

(source: raw/2026-10-12-signals-page.md §Components, Data layer; §Concept, Plan resolutions, Web SP-W-16/17)

**The shown day and reconnects (signals day control, tidewatch-web#13, merged 2026-10-14, not deployed).** No `/ws` protocol, frame or service code changed.
- The Signals page keeps the all-signals feed held whatever day it shows. On a past day the frames are simply not counted (see [[signal-message-contract]]).
- **A reconnect reloads the shown day (PRD §4.7, owner decision SDC-OD-2).** A reconnect or a terminal-close reload of Today can cross Bangkok midnight before the 60 s summary tick. When its first page names the next day, the page drops that page and re-reads the kept day once with `GET /signals?day={kept day}`. That costs one extra list read in this case only. If the re-read fails, the rows are kept (MW-20), and seen-through does not move.
- After a rollover, every later reload of the kept list sends `day={kept day}`.
- This path was checked only in Vitest, never in a real browser.

See [[signals-day-control]] (source: raw/2026-10-14-signals-day-control.md §Concept, SDC-OD-2; §API, Requests as implemented; §Components, `SignalsService` store; §Open questions; §Cross-cutting links).

**Verification.** `TestRealtime_SignalsFeed` and `TestRealtime_SignalsFeed_ResumesAfterOutage` pass, and A2 (`PSubscribe` on the existing connection) held. On the preview, an injected publish reached the page's note 97 ms after the PUBLISH (FR-SP-E2E-001). No real bot publish arrived in 25 minutes, so only the service → web leg was observed (source: raw/2026-10-12-signals-page.md §Test plan, Named acceptance tests, Acceptance status and Assumption outcomes).

**Follow-ups.**
- **R15 double-flip window.** If the flag toggles twice within one hand-over, a publish may be delivered twice or missed. The web dedupes by `signal_id`.
- **Security L3.** A 0↔1 flag swap can drop frames for every user during the swap. Desired-set generations or a debounce are the suggested fixes.

(source: raw/2026-10-12-signals-page.md §Open questions, Service follow-ups)

## Lifecycle and close codes

- The server pings every 30 s and drops a socket after 60 s without a pong (recorded as 1006).
- Every 60 s one batched session re-check runs. It never touches the session, so an open socket alone does not extend the idle timeout (7 days, see [[auth-model]]).

| Code | Meaning |
|---|---|
| 4401 | The session ended (sign-out, sign-out everywhere, the CLI reset), or, since accounts and roles, it was revoked or its user is disabled. An operator's *Disable sign-in* and *Reset password* both revoke every session |
| 4403 | A forced change is pending, or the role is no longer `user` (it was `admin` until accounts and roles) |
| 1008 | The third protocol error within 60 s |
| 1009 | A message over 64 KiB, closed at once (ORCH-11 / R8, a DoS bound and recorded deviation) |
| 1011 | A server failure, such as two failed re-checks in a row |
| 1013 | More than 256 messages queued |
| 1001 | Shutdown |

(source: raw/2026-10-07-market-data.md §API, Lifecycle and close codes; §Concept, ORCH-11)

**Disable timing, measured (accounts and roles, E2E-003).** On the preview, a person's socket closed with 4401 **20,594 ms** after an operator disabled them, inside the 60,000 ms bound (ORCH-3 kept the PRD's 60 s). Their next REST call landed on `/sign-in`. `TestPeople_DisableClosesSockets4401` and `TestHub_RecheckUserRole` pin the behaviour (source: raw/2026-10-29-accounts-roles.md §API, Gates and route groups; §API, People, Writes; §Concept, Decisions during the build ORCH-3; §Test plan, What each E2E check showed, E2E-003 and Named acceptance tests).

## Fan-out

One Redis pub/sub connection per service instance holds `px:<id>` (and, since slice 3a, `sig:<id>`) for every id with at least one subscriber, reference-counted. Since slice 4, while any connection holds the all-signals flag, the same connection holds the pattern `sig:*` instead of the per-instrument `sig:<id>` channels. While Redis is down, sockets stay open and silent, and the subscriber reconnects with a backoff from 100 ms to 5 s. Messages published during an outage are not replayed. The per-user cap and the fan-out are per process (SV15); scaling out is not built (source: raw/2026-10-07-market-data.md §API, Fan-out; §Open questions, Known gaps).

## Implementation (tidewatch-service)

- Library: `github.com/coder/websocket v1.8.15`, chosen over gorilla and `x/net/websocket` for its close-code and ping control. gin's hijack works for the upgrade (A14, settled by integration tests with a real client).
- `internal/services/realtime` (`hub`, `conn`, `protocol`, `config`, `ports`) is transport-free. `internal/handlers/realtime.go` is the only place that knows both gin and coder/websocket.
- `internal/httpx/wsconn` holds the handshake check and `Peer`; `internal/httpx/middleware/upgradeorigin.go` holds the upgrade Origin check.
- The batched session check required changes to `internal/services/auth/{session,service}.go`.
- Metrics on the internal 9090 listener: `redis_up`, `ws_connections`, `ws_subscriptions`, `ws_messages_sent_total{type}`, `ws_closed_total{code}`, with closed label sets and no instrument or user label. Log events: `ws_connected`, `ws_closed`, `ws_panic`.

(source: raw/2026-10-07-market-data.md §Concept, Libraries and A14; §Components, tidewatch-service; §Files touched)

## Web client (`MarketStream`)

- One root WebSocket with reference-counted interest (`pages/workspace/data/market-stream.service.ts`).
- The URL is `apiBaseUrl` plus `/ws`, with `http`→`ws` and `https`→`wss`, and a relative base resolved against `location.origin` (so the preview's `/api` becomes `/api/ws`).
- Transient closes back off 1, 2, 5, 10, then 30 s. 4401 and 4403 are terminal: the page reloads once so the HTTP interceptor can redirect (MW-2, MW-26), and the socket recovers only after a successful REST reload.
- Message shapes are validated at runtime (`market-stream.model.ts`), and live 24h change is recomputed by `util/apply-stream-message.ts`. A `zone` message for a visible row, or a reconnect, triggers a REST reload of the Market watch.
- E2E specs mock the socket with `page.routeWebSocket`.

(source: raw/2026-10-07-market-data.md §Components, tidewatch-web Data layer and E2E; §Components, Recovery notes)

## The Chart screen as a consumer (charting, slice 5)

The Chart (see [[charting]]) reuses `MarketStream` with no protocol change. `market-stream.service.ts` itself was not edited.
- **Interest.** The Chart's store acquires one `MarketStream` interest for its instrument. It is released on destroy and replaced on an instrument change.
- **`tick`** moves the header's last price and change, by Market watch's `applyStreamMessage` rules. It also moves the forming bar's `c`, `h` and `l` when the tick's `ts` falls in the forming bucket.
- **`bar`** (a closed 1m bar). The web's `BarMessage.bar` gained optional `o`, `h`, `l` and `v` (CH-W-11), which the web had tolerated but not read before. Only a frame carrying all four is folded into the UTC-aligned forming 15m, 1h or 1d bucket, as a single-bar update with no history read. A bar past the boundary opens a new bucket. A 1m bar ending at or before the head's `right_now.last.ts`, or a minute already folded, only widens `h`/`l`.
- **`zone`** triggers the `limit=8` head re-read at once, on a daily base too. On a 15m chart, the 1h `zone` frame at the hour triggers it. Without a frame, the re-read runs 65 s after a bucket closes, and again at 180 s if there is still no zone (S8, see [[chart-read-api]]).
- **`signal`** with an unlisted `signal_id` re-reads `GET /instruments/{id}/signals`, cancelling a read in flight, one read per burst (CH-BUILD-10). The frame carries no headline, so the marker comes only from that REST read (see [[signal-message-contract]]).
- **`status`** updates the status tag. A `1d`-base instrument folds nothing and still takes `status` and `signal`.
- **Reconnects.** `reconnected` re-reads the head and the signals. `reloadRequested` and `reloadSucceeded(epoch)` behave as on Market watch (MW-2, MW-26), and `reconnecting` shows "Reconnecting live prices…".
- **Quiet.** Nothing in these updates moves the visible range, scrolls, animates or announces (MW-23).

**Verification on the preview.** FR-CH-E2E-002 passed: an injected 1m bar on `px:BTCTHB@binance-th` raised the forming high in 171 ms (162 ms in the second round) with no request, and the bucket crossing made no head read. **FR-CH-E2E-003 is partial** (owner decision CH-BD-3): an injected C-SIG-1 frame triggered the signals re-read at +81 ms (+85 ms in the second round), but no real signal arrived, so a marker drawn from a stored row was never seen live (source: raw/2026-10-16-charting.md §Components, Realtime (S7); §Concept, Problem; §Test plan, Acceptance status and Preview runs; §Files touched, Not changed).

## Verification

- Through the preview gateway, `/api/ws` gave 401 without a cookie, 101 with a session, and 403 for a foreign or missing Origin (O7, FR-MD-INFRA-003). See [[forge-preview-gateway]].
- Publish-to-client p99 was 4.99 ms on loopback (`TestRealtime_PublishToClient_P99Under2s`, FR-MD-WS-003). A live tick-to-browser timing was not captured.
- Other key tests: `TestRealtime_Upgrade_Refusals`, `TestRealtime_Protocol_Limits`, `TestRealtime_SessionRecheck_Closes4401And4403`, `TestRealtime_RedisOutage_RESTWorksAndResumes`, `TestRealtime_CurlTranscripts`, `TestServe_SIGTERM_ClosesSockets1001`.
- Manual check against the owner compose: an upgrade to `http://localhost:3000/ws` without a cookie and with the app Origin gives 401; with `Origin: http://evil.example` gives `403 origin_rejected`; a plain `GET /ws` with a valid session gives `400 upgrade_required`.

(source: raw/2026-10-07-market-data.md §Concept, O7; §Test plan)

## Related pages

- [[redis-market-contract]] — where the forwarded messages come from
- [[request-protection]] — the exact-origin rules `/ws` reuses as `origin_rejected`
- [[auth-model]] — session lifetime, the forced-change gate and the 4401/4403 triggers
- [[forge-preview-gateway]] — `/api/ws` upgrades through Caddy
- [[market-data]] — the slice overview
- [[signal-message-contract]] — the C-SIG-1 `signal` frame, its drops and how the web counts it
- [[signals-ingest]] — the slice-3a overview that added signal forwarding
- [[signals-page]] — the slice-4 overview that added the all-signals feed
- [[signals-day-control]] — the shown day, and the reconnect that re-reads it across midnight (SDC-OD-2)
- [[charting]] — slice 5, whose Chart folds `bar` frames and re-reads on `zone` and `signal` frames
- [[chart-read-api]] — the `limit=8` head re-read the Chart runs after a bucket closes or a `zone` frame
- [[accounts-and-roles]] — role `user`, and the person disable that closes sockets with 4401
- [[operator-console]] — the `tw_admin` cookie that `/ws` refuses, and *Disable sign-in*
