# Request protection (CSRF and CORS)

**Summary**: The D1 decision: the browser calls the service origin directly with credentials, made safe by exact-origin CORS, a mandatory CSRF header plus Origin check, an unpublished metrics listener, `SameSite=Lax` cookies and a shared registrable domain in production. Includes the web-side and SSR host protections that complement it, and how the slice-1 market routes and `GET /ws` reuse the same rules. **Since accounts and roles (2026-10-29)** the same CSRF and CORS rules cover the operator console's `/admin/*` routes, sign-in included, unchanged. Every `/admin` answer is `no-store`, and the second cookie, `tw_admin`, follows the same never-`Domain`, never-`SameSite=None` rule. The web interceptor now branches on the API path, so an operator `401` and a product `401` never touch each other's state.

**Sources**: `raw/2026-10-05-foundation-auth.md`; `raw/2026-10-07-market-data.md`; `raw/2026-10-12-signals-page.md` (signals and settings routes only); `raw/2026-10-29-accounts-roles.md` (the `/admin` routes, `tw_admin` and the interceptor branch only)

**Last updated**: 2026-10-29

---

## The D1 decision

The browser calls the service origin (`http://localhost:3000` on the owner compose) directly, with credentials. Paths stay as `documents/05-auth-and-access.md` writes them (`/auth/login`, ...), with no `/api` prefix in the service. The owner chose this once it was established that it is no less secure, given four guardrails:

1. Exact single-origin CORS from `TIDEWATCH_APP_ORIGIN` with `Vary: Origin`, proven by table tests.
2. `/metrics` on its own `METRICS_PORT` listener (9090, never published; `404` on the main port).
3. In production, app and API share a registrable domain.
4. `SameSite=None` is never used.

Rejected alternatives: a same-origin `/api` prefix (equally secure, an owner preference) and Go serving the web app (breaks SSR) (source: raw/2026-10-05-foundation-auth.md §Concept, D1).

The Forge preview is the one place that uses a same-origin `/api` prefix, through a gateway (see [[forge-preview-gateway]]); the service itself has no such prefix.

## CSRF

- Every `POST`, `PUT`, `PATCH` and `DELETE` on a registered route, `/auth/login` included, needs the header `X-Tidewatch-Request: 1` and an `Origin` equal to `TIDEWATCH_APP_ORIGIN`.
- `Referer` is consulted only when `Origin` is absent. A present-but-wrong or `null` Origin is never rescued.
- The comparison is exact: scheme case is not folded, the host is lowercased, default ports are normalised away, and repeated headers are rejected.
- CSRF runs engine-wide but skips unmatched routes, so unknown paths still answer `404` and future routes are protected by default.
- Failure is `403 csrf_rejected`.

(source: raw/2026-10-05-foundation-auth.md §API, CSRF and CORS)

## CORS

- A preflight from the app origin gets `204` with `Access-Control-Allow-Origin: <app origin>`, `Access-Control-Allow-Credentials: true`, allowed methods `GET, POST, PUT, PATCH, DELETE`, allowed headers `Content-Type, X-Tidewatch-Request, X-Request-ID` and `Access-Control-Max-Age: 600`.
- Any other origin (`null`, other ports, look-alike hosts, other schemes) gets `403 cors_rejected` with no `Access-Control-Allow-*` headers.
- Every non-preflight response to the app origin carries ACAO, ACAC and `Access-Control-Expose-Headers: Retry-After, X-Request-ID`, even errors and 404s.
- `Vary: Origin` is on every response. There is no wildcard and no echo.
- ORCH-5: a preflight is answered only on registered routes. `OPTIONS` to `/auth/register`, to `/metrics` on the main port and to unknown paths returns `404`.

(source: raw/2026-10-05-foundation-auth.md §API, CSRF and CORS; §Concept, Other recorded decisions)

## The market routes and `/ws` (slice 1)

- **Gate chain.** Every market REST route runs `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged` (role `user` since accounts and roles), so the 8 KiB body cap and `Cache-Control: no-store` now cover the market group as well as `/auth/*` (source: raw/2026-10-07-market-data.md §API, REST).
- **CSRF on watchlist mutations.** `POST /watchlist/items`, `DELETE /watchlist/items/{id}` and `PUT /watchlist` need the CSRF header and Origin like every other mutation (source: raw/2026-10-07-market-data.md §API, REST).
- **`/ws` uses the exact-origin rule instead of the CSRF header.** An upgrade whose `Origin` is missing, repeated, `null` or not the app origin gets `403 origin_rejected`, checked right after readiness and before the session. There is no CSRF header on an upgrade: the exact Origin check plus the `SameSite=Lax` cookie is the cross-site defence. The check lives in `internal/httpx/middleware/upgradeorigin.go`. The full check order is on [[realtime-websocket]] (source: raw/2026-10-07-market-data.md §API, WebSocket and New error codes; §Components, tidewatch-service).
- **Strict query strings.** On the market routes an unknown, repeated or unparseable query parameter is a 400, and an encoded `/` in an id is a 404 (source: raw/2026-10-07-market-data.md §API, Request rules).
- **Envelope.** It stays `{"error","code","requestID"}`, now with an optional `details` (`field`, `reason`) on `400 invalid_request` (ORCH-7, R1/R2) (source: raw/2026-10-07-market-data.md §API; §Concept, ORCH-7).
- **Accepted info item (ORCH-29).** CSRF and CORS refusals and 404s carry no `no-store` (source: raw/2026-10-07-market-data.md §Open questions, Accepted security info items).

## Signals and settings routes (slice 4)

- **Same gate chain.** The eight signals-page routes sit on the gated market group, with the 8 KiB body cap and `no-store` (see [[signals-read-api]]).
- **CSRF on the settings write.** `PUT /me/settings/{key}` needs the CSRF header `X-Tidewatch-Request: 1` and the app `Origin`, like every other mutation. A refusal is `403 csrf_rejected`. `TestRouter_MarketMutations_CSRF` is among the existing tests revised on purpose in this slice (see [[user-settings]]).
- **The export is a top-level GET.** `GET /signals/export.csv` is read-only, so the session cookie travels and no CSRF header is needed. The web builds the link as `apiBaseUrl` + `/signals/export.csv?` + the filters + the loaded `day`. On the preview, three real downloads through the same-origin gateway sent the cookie. The development half of that check (A4) is unverified. Under ORCH-9 it was checked on the preview only, and the build never migrates the shared dev database.
- **CSV formula guard (R13, a security default).** Export cells that start with `=`, `+`, `-`, `@`, TAB, CR or LF get a leading `'`. Only absolute `http`/`https` URLs pass as `canonical_url` (R14).
- **Strict bodies.** `PUT /me/settings/{key}` takes exactly `{value}`; `unknown_field` never names the key. **Security L2 (follow-up):** the shared strict body decoder accepts case-insensitive and repeated keys, on `POST /orders` too.

(source: raw/2026-10-12-signals-page.md §API, Service routes and Export; §Components, SignalsService; §Concept, ORCH-9; §Concept, Plan resolutions, Service R13/R14; §Test plan, Named acceptance tests and Acceptance status; §Open questions, Service follow-ups)

## The operator console's `/admin/*` routes (accounts and roles, 2026-10-29)

- **CSRF and CORS are engine-wide and unchanged.** Every `POST`, `PATCH` and `DELETE` under `/admin`, including the three sign-in steps (`/admin/auth/login`, `/login/verify`, `/login/resend`), needs `X-Tidewatch-Request: 1` and the exact app `Origin`. `/admin/*` is on the product's origin (D8), so no new CORS origin was added.
- **No caching.** Every `/admin/*` answer carries `Cache-Control: no-store`, refusals and unknown `/admin` paths included.
- **Strict bodies and queries.** The group's gates are `NoStore → ReadyGate → BodyLimit(8 KiB)`. A body must be one JSON object. An unknown key is `unknown_field`, and the key is never named. An unknown query parameter is `invalid`, a repeated one `duplicate`.
- **No sign-up surface.** `/auth/register`, `/sign-up`, `/admin/register` and any other unregistered path answer `404 not_found` for every method, `OPTIONS` included.
- **The second cookie.** `tw_admin` is `Path=/; Max-Age=604800; HttpOnly; SameSite=Lax`, plus `Secure` unless `ENVIRONMENT=local`. Like `tw_session`, it never has `Domain` or `SameSite=None`. A refusal clears only its own kind's cookie.
- **Web-side.**
  - **Interceptor (S12).** `auth.interceptor.ts` branches on the request's API path, never on the route. A `401` on an `/admin` path, other than the three login routes, clears only the operator store and goes to `/admin/sign-in?next=`. A product `401` never touches the operator store.
  - **`next`.** `sanitizeAdminNext` keeps only targets under `/admin`, never `/admin/sign-in`, and otherwise falls back to `/admin`.
  - **Pre-hydration guard.** `/admin/sign-in` is prerendered with the same disabled-`<fieldset>` guard until hydration and the capture-phase submit guard as `/sign-in`.
- **Secrets in e2e artefacts.** Security finding SEC-W-1 was that Playwright's `error-context.md` could persist typed secrets. The fix: `PLAYWRIGHT_NO_COPY_PROMPT=1` is required and failure snapshots are stripped.

Details are on [[operator-console]] (source: raw/2026-10-29-accounts-roles.md §API, Conventions, Product contract changes and Gates and route groups; §Components, Routes and Stores, API service, interceptor; §Components, e2e; §Concept, Review history, Web).

## Response and request hygiene

- Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`; every `/auth/*` response also carries `Cache-Control: no-store`.
- `/auth/*` bodies are capped at 8 KiB.
- `X-Request-ID` is honoured when it is 1 to 128 characters from `[A-Za-z0-9._:-]`, otherwise generated, and is echoed on the response and in every log line and error body.
- Middleware order, engine-wide: `requestid`, `recovery`, `securityheaders`, `logger`, `metrics`, `CORS`, `CSRF`. gin's trailing-slash redirects and 405 handling are turned off, because gin would write those answers before any middleware runs.
- Metrics are served on a separate listener and are unauthenticated (an accepted limit). `/info` serves build metadata on the main port.

(source: raw/2026-10-05-foundation-auth.md §API, Request handling; §Components, Middleware order; §Open questions, Known limits)

## Production constraint (documented, not built)

App and API on hosts of one registrable domain, a TLS terminator listed in `TRUSTED_PROXIES`, `METRICS_PORT` internal, and a single instance. Any environment other than `local` requires an https app origin and sets the `Secure` cookie flag. Production topology and TLS are deferred by the owner (source: raw/2026-10-05-foundation-auth.md §API, Production constraint; §Components, Service environment; §Open questions, Follow-ups).

## Web-side and SSR protections

- **Interceptor scoping.** The interceptor adds `withCredentials` and `X-Tidewatch-Request: 1` only to URLs that start with `apiBaseUrl`.
- **`next` sanitising.** Only a single-`/` path is accepted: no scheme, no `//`, no `\`, no control characters, and not `/sign-in`. Anything else becomes `/`.
- **Storage.** Only `tw-theme` is ever stored.
- **Pre-hydration guard.** Added after a round-1 web security review found a password could reach the URL through a native submit before hydration. An inline script in `index.html` cancels every native `submit` in the capture phase, and the prerendered form stays in a disabled `<fieldset>` until `afterNextRender`.
- **`/auth/me` timeout.** `/auth/me` times out after 10 s and takes the not-responding path; a hung check is never treated as signed in.
- **SSR host allow-list (D2).** `/sign-in` is prerendered; every other route is client-rendered. The SSR server never calls the API and never forwards or logs cookies. Angular 22.1 SSR has no built-in host list (assumption A4, partly invalidated), so the base list `["localhost","127.0.0.1"]` lives in `project.json`, unioned with `NG_ALLOWED_HOSTS`. With nothing configured, every Host is rejected with `400`, `localhost` included. A foreign `Host` gets `400`.
- **Open follow-up.** Add `frame-ancestors` / `X-Frame-Options` on HTML responses; the PRD is silent. Client timeouts on login, logout and change-password are also outstanding.

(source: raw/2026-10-05-foundation-auth.md §API, Web-side protections; §Concept, D2 and A4; §Open questions, Follow-ups)

## Related pages

- [[auth-model]] — the sessions, throttle and forced-change rules these protections front
- [[forge-preview-gateway]] — the same-origin preview path and its Origin rewrite
- [[foundation-auth]] — the slice overview and verification results
- [[realtime-websocket]] — the `/ws` pre-upgrade checks that reuse the exact-origin rule
- [[market-data]] — the market routes behind the same gate chain
- [[signals-read-api]] — the signals routes and the cookie-carrying CSV export
- [[user-settings]] — the CSRF-protected settings write
- [[operator-console]] — the `/admin/*` routes, the `tw_admin` cookie and the interceptor branch
