# Foundation and auth (Slice 0)

> Slice 0 put down the foundation every later Tidewatch slice depends on. Migrations moved from an MSSQL Node runner to goose on Postgres 18, and the first schema landed: the `timescaledb` and `vector` extensions plus `users`, `sessions`, `events` and `api_credentials`. `tidewatch-service` became a Go service with one seeded admin, cookie sessions, argon2id passwords, in-memory login limits and lockout, exact-origin CORS and CSRF, readiness that waits for the schema, a password-reset CLI and append-only audit events. `tidewatch-bot` gained `packages/shared` and a connect-and-exit `packages/worker`. `tidewatch-web` became the Aurora-styled Angular shell, with a prerendered sign-in page, a forced or voluntary password change and six titled empty-state screens. The untracked workspace root got a `docker-compose.yaml`, and Forge got a preview definition with a Caddy gateway. All four PRs merged on 2026-10-05T16:31:45Z: migrations `87ce578`, service `f9da2cd`, bot `fe17845`, web `f0d0a7f`. The full 156-test Playwright suite passed on two topologies: same-origin through the preview gateway, and cross-origin on a disposable copy of the owner's compose stack. Two items are still open. FR-INFRA-008 is the Forge run command, which the owner changes in Forge settings. FR-WEB-019 is `DESIGN.md`, whose PR is in progress.

## Concept

**Problem.** Every later slice needs three things first: a database, a service that knows who you are, and a web shell that already looks like Tidewatch. The owner signs in as a seeded `admin`; there is no sign-up (05 §1). Before this slice, `tidewatch-service` was an empty `main.go`, `tidewatch-web` was the Nx welcome app with every route prerendered, `tidewatch-bot` had an empty `packages/`, and `tidewatch-migrations` was an MSSQL `migrate.mjs` scaffold, the wrong engine according to 02 §10.

**Sources.** `tidewatch-specs/foundation-auth/intent.md` (confirmed 2026-10-04, decisions D1–D17), `prd.md` (§4 behaviour, §5 schema, §6 API, §7 design, §8 operations, §9 acceptance IDs, assumptions A1–A10) and `build-prompt.md`. The design authority is `documents/03-design-system.md` plus the Aurora block of `documents/mockups/tidewatch-redesigned.html` (token lines 216–233, layout lines 234–257). The auth authority is `documents/05-auth-and-access.md`, as adjusted by D1, D2, D7, D11 and D16.

### Outcomes O1–O7

| # | Outcome | Traced IDs (PRD §9) | Result |
|---|---|---|---|
| O1 | One command brings everything up | FR-INFRA-001/005, FR-MIG-* | Passed. The root compose was run on merged primaries under a disposable project with a fresh volume, and the isolated preview was healthy. |
| O2 | Health is truthful | FR-SVC-003/004 | Passed. `/health` is always 200; `/ready` went 503 → 503 → 200 as the schema and extensions appeared. |
| O3 | Sign in as the seeded admin, forced change, land on Overview | FR-AUTH-001/007, FR-WEB-009/013, FR-E2E-001 | Passed. |
| O4 | Approved shell on every route, dark default, light first-class, no horizontal scroll | FR-WEB-001…016 | Passed. |
| O5 | Sign out and sign out everywhere revoke sessions on the server | FR-AUTH-014/015, FR-WEB-011 | Passed. |
| O6 | Hostile use fails | FR-AUTH-008…018, FR-SVC-009 | Passed. |
| O7 | Later slices start small | FR-MIG-004, FR-BOT-*, FR-INFRA-005, FR-DOC-001, FR-WEB-019 | Partly open: everything has passed except FR-WEB-019 (`DESIGN.md`, in progress). |

### Architecture decisions

- **D1, cross-origin API with guardrails.** The browser calls the service origin (`http://localhost:3000` on the owner compose) directly, with credentials. Paths stay as 05 writes them (`/auth/login`, …), and there is no `/api` prefix in the service. The owner chose this once it was established that it is no less secure, given four guardrails:
  - exact single-origin CORS from `TIDEWATCH_APP_ORIGIN` with `Vary: Origin`, proven by table tests;
  - `/metrics` on its own `METRICS_PORT` listener (9090, never published; `404` on the main port);
  - in production, app and API share a registrable domain;
  - `SameSite=None` is never used.

  Rejected alternatives: a same-origin `/api` prefix (equally secure, owner preference) and Go serving the web app (breaks SSR).
- **D2, render modes.** `/sign-in` uses `RenderMode.Prerender`. Every other route, `**` included, uses `RenderMode.Client` (`src/app/app.routes.server.ts`). The SSR server never calls the API and never forwards or logs cookies.
  - Angular 22.1 SSR has no built-in host list (A4). The base list is `security.allowedHosts: ["localhost","127.0.0.1"]` in `project.json`, unioned with `NG_ALLOWED_HOSTS`.
  - A foreign `Host` gets `400`.
- **D6, styling.**
  - Tailwind v4 through `setup-shared-styles` in single-app mode (`src/styles/`).
  - Tokens are CSS custom properties, defined once in `src/styles/base/tokens.css`: `:root` (dark) and `:root[data-theme=light]`. `src/styles/tailwind/theme.css` maps them with `@theme inline` and removes Tailwind's palette (`--color-*: initial`).
  - Recorded exceptions to the kit: no `dark:` variants (theming is variable-driven); no Angular Material (`@angular/aria` provides the menu); mockup inline SVG icons instead of lucide.
  - DM Sans and Manrope are self-hosted (`@fontsource-variable`, OFL).
  - The only literal colours outside the token file are the brand gradient tile's.
  - The production build sets `inlineCritical: false` and `fonts: false`; otherwise the light-theme block went missing from the inlined CSS.
- **D7, account menu.** It sits at the right of the top bar at every width: *Signed in as {username}*, then *Change password*, *Sign out* and *Sign out everywhere*. The mockup's help button and "Design preview" label are omitted.
- **D11, server-side forced change.** While `must_change_password` is true, every authenticated route outside a fixed allowlist returns `403 password_change_required`. The allowlist is `GET /auth/me`, `POST /auth/password`, `POST /auth/logout` and `POST /auth/logout-all`. The gate fails closed, so new routes are gated by default. A new password must differ from the current one.
- **D16, Forge preview gateway.** The preview publishes one dynamic loopback port, so a `caddy:2-alpine` gateway (`.forge/docker/templates/preview-gateway/Caddyfile`) is the single browser entry, on `:8080`:
  - `GET /config.json` returns `{"apiBaseUrl":"/api"}` with `no-store`;
  - `/api/*` has the prefix stripped and goes to `tidewatch-service:3000`;
  - everything else goes to `tidewatch-web:4200` with `Host` preserved and `X-Forwarded-Host` dropped.

  On `/api/*` the gateway rewrites `Origin` to `http://localhost:4200` only when it exactly equals `http://<request host:port>` **and** the Host is loopback. Any other Origin passes through unchanged, so the service still rejects it.

  After the workspace-root security review warned about DNS rebinding, the gateway was changed to answer `421 Misdirected Request` for any non-loopback Host, before routing. Consequences:
  - the preview exercises the same-origin path, while the cross-origin path is verified by the service tests and FR-E2E-002;
  - no product code branches on "preview". The service's CLAUDE.md forbids the word in any Go source.
- **Related decisions.** D3 env naming (unprefixed infra settings, `TIDEWATCH_`-prefixed product settings). D9: a one-shot `migrate` container is the only place migrations apply automatically, and only to the local compose database. D10: the service starts without the schema and waits. D12: limits and lockout live in process memory. D13: breakpoints follow the mockup (1250/1080/820/600). D15: Playwright only against a fresh, separate database. D17: `documents/` is never edited.

### Owner design decisions

- **OWNER-4, light-theme AA fix.** The mockup values measured below WCAG AA: the bar tint gave 4.3:1 for `--text-2` on the environment pill, and the leading crumb in `--text-3` gave 3.7:1. In the light theme only, `.global-bar` is transparent and the leading crumb uses `--text-2`. Dark keeps the mockup exactly.
- **OWNER-5, hue-less errors.**
  - Error text uses `--text`, led by the error glyph (`<app-icon name="close" />`, `aria-hidden`), in `p.error-message`.
  - An invalid field gets a `--text-2` border.
  - `--down` and the zone hues stay reserved for zones and P&L (03 §2.3, §10).
- **OWNER-6, light breadcrumb hierarchy.** In light, the current crumb uses `--text`, one step above the `--text-2` leading crumb. Dark is unchanged (`--text-3` leading, `--text-2` current).

### Other recorded decisions (state.json)

- **OWNER-3 / ORCH-8.** Forge models migrations as a workspace resource (`migrationsPath` + `migrationsRepo`), not a project. The migrations steps were folded into the service plan as MIG1–MIG3 (`go-engineer`, an explicit override recorded as ORCH-1). They committed to the migrations worktree and shipped as their own PR, which had to merge before or with the service PR.
- **ORCH-5.** CORS preflight is answered only on registered routes. `OPTIONS` to `/auth/register`, to `/metrics` on the main port and to unknown paths returns `404`.
- **Service login order** (plan decision 6). The PRD lists rate limits before normalisation, but the per-username limit needs the normalised name. The implemented order is: CSRF → IP limit (checked and recorded) → parse the 8 KiB body → normalise → username limit → lockout state → exactly one argon2id verification → outcome.
- **`/ready` shape.** It keeps the go-health-checks shape, with the camelCase key `latencyMs`. The snake_case rule covers API bodies only.
- **OWNER-7.** Preview database `isolated`; preview volumes retained.
- **OWNER-8.** At the owner's request the orchestrator generated the preview secrets file. The owner then set `TIDEWATCH_ADMIN_PASSWORD` personally, and the generated admin value was removed.
- **OWNER-9.** After testing sign-in on the preview, the owner asked the orchestrator to merge. The merges were pinned to the reviewed heads, in the order migrations → service → bot → web.
- **OWNER-1.** `tidewatch-bot` stays in scope.

### Assumptions A1–A10

| ID | Assumption | Outcome |
|---|---|---|
| A1 | `timescaledb-ha:pg18` keeps data under `/home/postgres/pgdata/data` | Validated. `PGDATA=/home/postgres/pgdata/data` and the image declares no `VOLUME`. The named volume mounts on `/home/postgres/pgdata`, and FR-INFRA-004 proved persistence. |
| A2 | The superuser can create `timescaledb` and `vector` | Validated. The image already installs timescaledb 2.30.2 and `timescaledb_toolkit` in `POSTGRES_DB` at init. |
| A3 | `CREATE EXTENSION timescaledb` may need `NO TRANSACTION` | Validated as not needed: both run inside goose's default transaction. |
| A4 | Angular 22.1 SSR exposes an allowed-hosts setting | Partly invalidated. The mechanism exists (`security.allowedHosts` + `NG_ALLOWED_HOSTS`, unioned), but there is no built-in list: with nothing configured, every Host is rejected with 400, `localhost` included. |
| A5 | Forge can build the preview `migrate` from the run's migrations worktree | Holds for this run only. `{{project:tidewatch-migrations}}` resolves through this run's `worktrees.json`. Future runs will fail closed ("Unresolved setup token") because the helpers reject the resource slug. This is a Forge tooling gap. |
| A6 | The gateway can rewrite Origin only when it equals the request's own origin | Validated by curl (same-origin accepted, foreign Origin 403), and re-checked after the rebinding fix. `state.json` still lists A6 as pending; `verification.md` is authoritative. |
| A7 | Postgres 18 provides `uuidv7()` | Validated. |
| A8 | The engineer picks the common-password list | Resolved: SecLists `xato-net-10-million-passwords-1000000.txt` @ `56da8d99`, MIT, filtered to 46,146 entries. |
| A9 | `tidewatch-apis` is not a git repo, so API-collection generation skips | Holds; skipped. |
| A10 | `docker compose up --wait` may treat the exited one-shot bot as a failure | Validated. The documented command is `up -d --build`, then `ps -a`. |

## Database

All schema lives in `tidewatch-migrations`, a centralized workspace resource (`migrationsPath`): one flat goose sequence for the single `tidewatch` database. No service repo holds a `migrations/` directory.

### Migrations

| Version | File | Content |
|---|---|---|
| `20261004153020` | `migrations/20261004153020_enable_extensions.sql` | `CREATE EXTENSION IF NOT EXISTS timescaledb; CREATE EXTENSION IF NOT EXISTS vector;`. Down drops both with `IF EXISTS` in reverse order. Runs in a transaction (A3). |
| `20261004153023` | `migrations/20261004153023_auth_foundation.sql` | The four §5 tables, their indexes and the append-only trigger. Down is **destructive**: it drops `api_credentials`, `events`, `sessions`, `users`, then the trigger function, each `IF EXISTS`, never `CASCADE`. |

### Tables (exactly PRD §5; no extra CHECKs, by decision M6)

```sql
CREATE TABLE users (
    id                   uuid        PRIMARY KEY DEFAULT uuidv7(),
    username             text        NOT NULL UNIQUE CHECK (username = lower(username)),
    password_hash        text        NOT NULL,              -- PHC argon2id
    role                 text        NOT NULL DEFAULT 'admin',
    must_change_password boolean     NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    last_login_at        timestamptz
);

CREATE TABLE sessions (
    id           uuid        PRIMARY KEY DEFAULT uuidv7(),
    user_id      uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash   bytea       NOT NULL UNIQUE,               -- SHA-256 of the token
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,                      -- effective expiry
    ip           inet,
    user_agent   text,
    revoked_at   timestamptz
);
CREATE INDEX sessions_user_id_active_idx ON sessions (user_id) WHERE revoked_at IS NULL;

CREATE TABLE events (                                       -- plain table, not a hypertable
    id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at   timestamptz NOT NULL DEFAULT now(),
    type          text        NOT NULL,
    actor_user_id uuid        REFERENCES users (id),
    ip            inet,
    user_agent    text,
    request_id    text,
    detail        jsonb       NOT NULL DEFAULT '{}'
);
CREATE INDEX events_occurred_at_idx ON events (occurred_at DESC);
CREATE INDEX events_type_occurred_at_idx ON events (type, occurred_at DESC);
CREATE INDEX events_actor_user_id_occurred_at_idx ON events (actor_user_id, occurred_at DESC);
-- Triggers events_append_only (BEFORE UPDATE OR DELETE, per row) and
-- events_append_only_truncate (BEFORE TRUNCATE) call events_reject_mutation(),
-- which raises 'events is append-only: % is not allowed'.

CREATE TABLE api_credentials (                              -- table only in slice 0
    id           uuid        PRIMARY KEY DEFAULT uuidv7(),
    venue        text        NOT NULL,
    label        text        NOT NULL,
    enc_blob     bytea       NOT NULL,                      -- AES-256-GCM nonce||ciphertext||tag (later slice)
    last4        text        NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_used_at timestamptz,
    revoked_at   timestamptz
);
CREATE UNIQUE INDEX api_credentials_venue_label_active_key
    ON api_credentials (venue, label) WHERE revoked_at IS NULL;
```

The service enforces what the schema deliberately leaves out: allowed `role` values, the length of `token_hash`, `last4` and `user_agent` (truncated to 512), and the session lifetime. Lockout and rate-limit state are not stored (D12).

### Required-schema-version contract (`20261004153023`)

- The constant `RequiredSchemaVersion` in `tidewatch-service/internal/platform/postgres/schema.go` is `20261004153023`. It must equal the 14-digit prefix of `migrations/*_auth_foundation.sql`. The anchored lookup is `ls migrations | grep -E '^[0-9]{14}_auth_foundation[.]sql$' | cut -c1-14`, and the literal in both repos' docs is authoritative.
- The service's `/ready` `schema` check passes only when the newest `goose_db_version` row for that version has `is_applied = true`. The `extensions` check requires both extensions in `pg_extension`.
- **The constant and the migration move together.** When the service starts to depend on a later migration, the constant and that migration change in the same change. The migrations PR merges before or with the service PR. Both repos' `CLAUDE.md` and `README.md` document this.
- `TestContract_RequiredSchemaVersion` (service integration suite) fails if the constant and the migrations checkout drift apart.
- The tracking table is always `goose_db_version`. Every goose call passes `-env none -table goose_db_version`, and `GOOSE_DRIVER`, `GOOSE_DBSTRING`, `GOOSE_TABLE` and `GOOSE_MIGRATION_DIR` are unset. Without that, goose v3.27.3 merges a stray `GOOSE_DBSTRING` into its arguments and prints the full DSN, and `GOOSE_TABLE` silently moves tracking (decision M8).

### Tooling

- **goose `v3.27.3`**, pinned in both the `Makefile` (`GOOSE_VERSION`) and the `Dockerfile` (`ARG GOOSE_VERSION`) and run with `go run` (no global install). The `mssql` dependency, `migrate.mjs` and the `DB_*` variables are gone.
- **Make targets:** `migrate-up`, `migrate-status`, `migrate-validate` (no DB needed), `migrate-down` (one version; destructive, owner-only), `migrate-create NAME=<snake_case>`, `check-disposable-db`, `help`. The Makefile reads `DATABASE_URL` from `.env`.
- **npm aliases:** `migrate`, `migrate:status`, `migrate:validate`, `migrate:create -- <name>`. There are no npm dependencies.
- **Migrate image:**
  - goose is built in `golang:1.26-alpine` and runs on `alpine:3.22`, non-root (UID 10001), with no `.env*` in the image;
  - the entrypoint runs `up` through `scripts/dsn-guard.sh run`, which validates the DSN first (exit 1 naming only `DATABASE_URL` and a reason class) and masks goose output, the whole query string included;
  - `up` exits 0, and a rerun with nothing pending also exits 0.
- **`make check-disposable-db`** is the only sanctioned agent apply. It owns a throwaway `timescale/timescaledb-ha:pg18` container and always removes it. It never reads `.env`, the caller's `DATABASE_URL`, `GOOSE_*` or `PG*`.
- **DSN passwords** must be URL-safe or percent-encoded. In the root compose, `POSTGRES_PASSWORD` is restricted to `[A-Za-z0-9._~-]`, because one value both initialises Postgres and is embedded in `DATABASE_URL`.

## API

The base URL is the service origin (`http://localhost:3000` in compose). Behind the preview gateway the same routes appear under `/api`. Bodies are JSON with snake_case keys. The error envelope is `{"error": "<message>", "code": "<code>", "requestID": "<id>"}`, and the web app maps errors by `code`, never by message.

### Endpoints

| Method | Path | Auth | Request | Success | Errors |
|---|---|---|---|---|---|
| `POST` | `/auth/login` | none + CSRF | `{"username": ≤64 bytes, "password": ≤1024 bytes}` | `204` + `Set-Cookie: tw_session=…` | `400 invalid_request`, `401 invalid_credentials`, `403 csrf_rejected`, `429 rate_limited` (+`Retry-After`), `503 not_ready` |
| `POST` | `/auth/logout` | session + CSRF | — | `204` + clearing cookie | `401 unauthenticated`, `403 csrf_rejected` |
| `POST` | `/auth/logout-all` | session + CSRF | — | `204` + clearing cookie | `401 unauthenticated`, `403 csrf_rejected` |
| `GET` | `/auth/me` | session | — | `200 {"user":{"id","username","role","must_change_password"},"session":{"expires_at"}}` (RFC 3339 UTC) | `401 unauthenticated` |
| `POST` | `/auth/password` | session + CSRF | `{"current_password", "new_password"}` | `204` | `400 invalid_request`, `401 unauthenticated`, `403 csrf_rejected`, `422 current_password_incorrect \| password_too_short \| password_too_long \| password_too_common \| password_unchanged`, `429 rate_limited` |
| any | `/auth/register` | — | — | — | `404 not_found` for every method, `OPTIONS` included. There is no route, alias or redirect. |
| `GET` | `/health` | none | — | `200 {"status":"ok"}`; checks no dependency | — |
| `GET` | `/ready` | none | — | `200 {"ok":true,"checks":{database,schema,extensions,bootstrap}}` | `503 not_ready` (envelope + `checks`; fixed reasons, never driver text) |
| `GET` | `/info` | none | — | build metadata `{"service","version","commit","buildDate","env"}`. Not part of the §6 contract. | — |
| `GET` | `/metrics` | none (internal) | — | Prometheus text, on `METRICS_PORT` only | `404` on the main port |
| `OPTIONS` | registered paths | — | preflight | `204` + CORS headers (app origin) | `403 cors_rejected` (any other origin) |

Authenticated routes also return `403 password_change_required` (D11) and `403 forbidden` (role gate). `requireRole("admin")` wraps the whole authenticated group, `/auth/me` and the logout routes included; in slice 0 that is trivially satisfied.

### Error codes

| Code | Status | When |
|---|---|---|
| `invalid_request` | 400 | Malformed, oversized (>8 KiB), wrong-typed or incomplete body. On `/auth/password`, also an empty or >1024-byte `current_password`. |
| `invalid_credentials` | 401 | Wrong password, unknown user or locked account. The three responses are identical apart from `requestID`. |
| `unauthenticated` | 401 | Missing, unknown, expired or revoked session. Adds a clearing `Set-Cookie` if a cookie was sent. |
| `csrf_rejected` | 403 | A state-changing request failed the CSRF check. |
| `cors_rejected` | 403 | A preflight from an origin other than `TIDEWATCH_APP_ORIGIN`. |
| `password_change_required` | 403 | Forced-change gate. |
| `forbidden` | 403 | Role gate. |
| `not_found` | 404 | Unknown route or method; trailing-slash and case variants included. There are no redirects and no 405s. |
| `current_password_incorrect` | 422 | The current password didn't verify, or the account is locked. |
| `password_too_short` / `_too_long` / `_too_common` / `_unchanged` | 422 | New-password policy. |
| `rate_limited` | 429 | Login limits, the password-change username limit, or the throttle key cap. Always with an integer `Retry-After`. |
| `internal` | 500 | Unexpected failure; also a malformed stored hash on `/auth/password`. |
| `not_ready` | 503 | `/ready`, and every `/auth/*` route, until ready. |

### Request handling

- `X-Request-ID` is honoured when it is 1–128 characters from `[A-Za-z0-9._:-]`, otherwise generated. It is echoed on the response and appears in every log line and error body.
- Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`. Every `/auth/*` response also carries `Cache-Control: no-store`.
- `/auth/*` bodies are capped at 8 KiB.
- Metrics: the Go and process collectors, `http_requests_total{route,method,status}`, `http_request_duration_seconds{route,method}` (by route template) and `tidewatch_auth_login_attempts_total{result="success|failure|rate_limited"}`.

### Security model

**Sessions and cookie.**
- The token is 32 bytes from `crypto/rand`, base64url in the cookie. Only its SHA-256 is stored (`sessions.token_hash`).
- Cookie: `tw_session=<token>; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax`, plus `Secure` unless `ENVIRONMENT=local`. There is no `Domain`, so the cookie is host-only. No code path can set `SameSite=None`.
- Lifetime: 30 days absolute and 7 days idle, rolling. `expires_at = least(last_seen_at + 7d, created_at + 30d)`. `last_seen_at` is touched when it is at least 60 s old. A session is valid only when `revoked_at IS NULL` and `now() < expires_at`.
- A user may have several sessions:
  - `logout` revokes the current one;
  - `logout-all` revokes every one, the current one included;
  - a password change revokes the **other** sessions and keeps the current one;
  - the CLI reset revokes all of them.

**Passwords.**
- argon2id with 64 MiB of memory, 3 iterations, parallelism 1, a 16-byte salt and a 32-byte key, PHC-encoded, with constant-time verification. A successful login rehashes a hash with weaker parameters. Stored hashes above 256 MiB, 16 iterations or parallelism 16 are rejected as malformed.
- One shared hasher allows at most 4 concurrent argon2 operations (about 256 MiB); the rest wait. Hashing always happens before a DB transaction opens.
- Policy: at least 12 code points, at most 1024 bytes, not in the embedded common list (case-insensitive), and on `/auth/password` not equal to the current password. No composition rules; passwords are never trimmed. Usernames are trimmed and lowercased.
- The common list is SecLists `Passwords/Common-Credentials/xato-net-10-million-passwords-1000000.txt` @ `56da8d991239cc52b0da594db53457504a757670` (MIT, © 2018 Daniel Miessler), filtered to entries of at least 12 code points, lowercased and deduplicated: 46,146 entries (about 675 KB), embedded from `internal/auth/password/data/` together with `SOURCE.md` and `LICENSE`.
- Login performs exactly one argon2id verification: against the user's hash, or against a fixed dummy hash for unknown and locked users.

**Login limits, lockout and the atomic reserve/refund throttle** (`internal/auth/throttle`, in memory per D12).
- **Limits:** 5 login attempts per rolling minute per client IP, and 10 per rolling 15 minutes per normalised username, where every login attempt counts. On `/auth/password`, only a wrong current password counts toward the shared username limit and the lockout (FR-AUTH-023). A refused attempt returns `429` with `Retry-After`, verifies nothing and writes no event.
- **Lockout:** 20 consecutive failures within an hour lock the username for 15 minutes.
  - While locked, even the correct password gets the identical `401`. `/auth/password` answers `422 current_password_incorrect`.
  - A success after expiry resets the count, and so does a verified `current_password`.
  - After a lock ends, the next failure re-locks for as long as 20 failures remain inside the hour.
- **Atomic reserve/refund.** `Guard.BeginLogin` and `Guard.BeginPasswordChange` check the limit, count the attempt and mark it pending in the lockout in one step under `userMu`. Then comes exactly one verification and exactly one settle (`Attempt.Fail`, `Succeed` or `Abandon`, with `defer Close()`).
  - A login's attempt always stays counted.
  - A password change is refunded on `Succeed`, on `Abandon` (no verification ran, e.g. a cancelled argon2 wait or a failed lookup), and when a verified current password is paired with a new password the policy rejects. A user working through the forced change therefore can't lock themselves out with weak choices.
  - A refund removes only its own hit, is idempotent, and is a no-op once that hit has left the window.
  - Pending attempts count toward the lock: at most `max(1, 20 − failures)` in-flight attempts verify for real, and the rest run against the dummy hash.
- **Why.** Round-2 security review found a check-now/record-later race (`PeekUsername`): 200 parallel guesses all passed a limit of 10. Fix loop 2 (service `67047cd`) replaced it. Round 3 verified that 200 parallel `BeginPasswordChange` calls let exactly 10 through, each a real verification. It also verified that double-settles, cross-attempt refunds and 1,000 begin→Abandon cycles cannot widen the limit.
- **Client IP** is the TCP peer, unless the peer is in `TRUSTED_PROXIES`; then it is the rightmost untrusted `X-Forwarded-For` entry. IPv4 is keyed per address and IPv6 per /64 (changed from /128 in fix loop 1). IPv4-mapped IPv6 counts as IPv4.
- **Memory cap, fail closed.** Each tracker (IP window, username window, lockout) holds at most 100,000 keys, pruned only once expired and unlocked. At the cap, a new key gets `429` with a `Retry-After` of 1–900 s. Live counters are never evicted.

**CSRF and CORS (D1 guardrails).**
- **CSRF.** Every `POST`/`PUT`/`PATCH`/`DELETE` on a registered route, `/auth/login` included, needs `X-Tidewatch-Request: 1` and an `Origin` equal to `TIDEWATCH_APP_ORIGIN`.
  - `Referer` is consulted only when `Origin` is absent. A present-but-wrong or `null` Origin is never rescued.
  - The comparison is exact: scheme case is not folded, the host is lowercased, and default ports are normalised away. Repeated headers are rejected.
  - CSRF runs engine-wide but skips unmatched routes, so unknown paths still answer `404` and future routes are protected by default.
- **CORS.** A preflight from the app origin gets `204` with `Access-Control-Allow-Origin: <app origin>`, `Access-Control-Allow-Credentials: true`, `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE`, `Access-Control-Allow-Headers: Content-Type, X-Tidewatch-Request, X-Request-ID` and `Access-Control-Max-Age: 600`.
  - Any other origin (`null`, other ports, look-alike hosts, other schemes) gets `403 cors_rejected` with no `Access-Control-Allow-*` headers.
  - Every non-preflight response to the app origin carries ACAO, ACAC and `Access-Control-Expose-Headers: Retry-After, X-Request-ID`, even errors and 404s.
  - `Vary: Origin` is on every response. There is no wildcard and no echo.
- **Production constraint (documented, not built).** App and API on hosts of one registrable domain, a TLS terminator listed in `TRUSTED_PROXIES`, `METRICS_PORT` internal, and a single instance.

**Logging and redaction.**
- **Service** (zerolog JSON, plus a console writer when `ENVIRONMENT=local`). Redaction is an always-on writer (`logging.RedactWriter`) rather than a hook, because a zerolog hook can't remove fields already added. It masks:
  - sensitive keys at any depth;
  - configured secrets by value (8 bytes or more);
  - URL userinfo up to the last `@` on the line;
  - `password=` pairs;
  - the DSNs pgx echoes in backticks;
  - argon2 PHC hashes.

  Every rule is a linear forward scan. Both `http.Server.ErrorLog`s and the CLI's stdout and stderr go through the scrubber. The request logger reads no body or header except the user agent.
- **Bot.** pino with exact-key redaction and connection-string masking on every string, `child()`/`setBindings()` bindings and `msgPrefix`. `loadConfig` rejects a URL with a raw `#`, or a raw `@` after the host.
- **Migrate.** `dsn-guard.sh` validates the DSN and masks output.
- **Web.** The SSR server never logs cookies. Angular logs rejected Host values and URLs only.

**Audit events** (`events`, append-only; built only through the typed constructors in `internal/audit`).

| Type | Written when | `detail` |
|---|---|---|
| `user_bootstrapped` | Bootstrap creates the admin | `{"username"}` |
| `login_succeeded` | Login succeeds | `{}` |
| `login_failed` | A verification fails | `{"username": <normalised attempted name>, "reason": unknown_user\|wrong_password\|locked\|invalid_stored_hash\|password_changed}`; the reason is server-side only |
| `password_changed` | `POST /auth/password` succeeds | `{}` (revoking other sessions writes no separate event) |
| `password_reset` | CLI reset | `{"via":"cli"}` |
| `session_revoked` | logout / logout-all / CLI reset | `{"reason":"logout"}`, `{"reason":"logout_all","count":n}`, `{"reason":"password_reset","count":n}` |

A wrong `current_password` writes no event. Neither does a rate-limited login. CLI events carry `NULL` `ip`, `user_agent` and `request_id`. `credential_added`, `bot_version_created`, `order_placed` and `kill_switch` are reserved for later slices.

**Web-side protections.**
- **Interceptor scoping.** The interceptor adds `withCredentials` and `X-Tidewatch-Request: 1` only to URLs that start with `apiBaseUrl`.
- **`next` sanitising.** Only a single-`/` path is accepted: no scheme, no `//`, no `\`, no control characters, and not `/sign-in`. Anything else becomes `/`.
- **Storage.** Only `tw-theme` is ever stored.
- **Pre-hydration guard.** It was added after the round-1 web security review found that a password could reach the URL through a native submit before hydration. An inline script in `index.html` cancels every native `submit` in the capture phase, and the prerendered form stays in a disabled `<fieldset>` until `afterNextRender`.
- **`/auth/me` timeout.** `/auth/me` times out after 10 s (`ME_TIMEOUT_MS`) and takes the not-responding path; a hung check is never treated as signed in.

## Components

### tidewatch-service (Go 1.26, gin, zerolog, envconfig, pgx v5, Prometheus client, `x/crypto/argon2`)

- **One binary, three subcommands.**
  - `serve` (default).
  - `admin set-password --username <name>`: reads the first line of stdin, falling back to `TIDEWATCH_ADMIN_PASSWORD` only when stdin is empty or a terminal. Exits 2 for a usage error and 1 when not ready or the user is not found. On success it rehashes, sets `must_change_password`, revokes all sessions, writes events and prints `password updated for <username>; all sessions revoked`. It never creates users, never echoes arguments, and does not clear a running server's lockout.
  - `healthcheck`: `GET http://127.0.0.1:$PORT/ready` with a 3 s timeout; exit 0 only on 200. Distroless has no curl.

  `cmd/tidewatch-service/main.go` only sets up the signal context and calls `os.Exit(cli.Run(...))`. Wiring lives in `internal/cli` and `internal/app`.
- **Layout and dependency direction:** `cmd` → `internal/cli` → `internal/app` → `internal/handlers`, `internal/httpx/*` → `internal/services/{auth,bootstrap}` → `internal/repository/postgres` → `internal/platform/postgres`. Services also use `internal/auth/{password,session,throttle,username}`, `internal/audit`, `internal/clock` and `pkg/apperror`.
- **Middleware order.** Engine-wide: `requestid → recovery → securityheaders → logger → metrics → CORS → CSRF`. The `/auth` group adds `ReadyGate → BodyLimit`, and the authenticated subgroup adds `RequireSession → RequireRole("admin") → RequirePasswordChanged`. `RedirectTrailingSlash`, `RedirectFixedPath` and `HandleMethodNotAllowed` are off, because gin would write those answers before any middleware runs.
- **Startup and readiness.**
  1. Config is validated first; on failure the service exits 1 naming the variable, never its value.
  2. Both listeners bind immediately.
  3. A background waiter refreshes the database, schema and extensions snapshot every 2 s and logs `waiting for schema version <v>` at most every 30 s.
  4. Bootstrap runs once under `pg_advisory_xact_lock`. With an empty users table and a valid password it creates the admin with `must_change_password=true`. With no users and no password it exits 1 with `no users exist and TIDEWATCH_ADMIN_PASSWORD is not set`. When users exist it skips and logs, and warns if the password variable is still set.
  5. SIGINT and SIGTERM drain in-flight requests within `SHUTDOWN_GRACE_PERIOD` and close the pool.
- **Listener timeouts.**
  - API: ReadHeader 10 s, Read 30 s, no Write, Idle 120 s.
  - Metrics: 10 s / 10 s / 30 s / 60 s.
  - `ReadTimeout` bounds only receiving the body. It does not cancel a handler's context (pinned by `TestServer_ReadTimeoutDoesNotCancelRequestContext`).
- **Image contract.**
  - `deploy/Dockerfile`, context = project root.
  - Builder `golang:1.26-alpine`; final stage `runtime` is `gcr.io/distroless/static:nonroot` (UID 65532).
  - `ENTRYPOINT ["/tidewatch-service"]`, `CMD ["serve"]`, `EXPOSE 3000 9090`.
  - `HEALTHCHECK ["CMD","/tidewatch-service","healthcheck"]` (interval 10 s, timeout 5 s, start 20 s, 6 retries).
  - Build args are only `VERSION`, `COMMIT_HASH` and `BUILD_DATE`. `go.mod` carries `toolchain go1.26.8`.
- **Make targets:** `ci` (vet incl. `-tags integration`, test-race, build; Docker-free), `test-integration TIDEWATCH_MIGRATIONS_DIR=<checkout>`, `check-image`, `run`, `build`, `docker`.

### tidewatch-web (Angular 22.1 SSR, Nx 23, Tailwind v4, `@angular/aria`, signal forms)

**Route tree** (`src/app/app.routes.ts`):

```
/sign-in                 SignIn (lazy sign-in.routes.ts, guestGuard, Prerender, outside the shell)
''                       Shell (canActivateChild: authGuard, Client)
├── account/password     ChangePassword (lazy account.routes.ts; data.section 'Account'; allowed while forced)
└── '' (workspace.routes.ts)
    ├── ''               Overview  -> ScreenPlaceholder + EmptyState
    ├── signals          Signals   -> ScreenPlaceholder + EmptyState
    ├── chart            Chart     -> ScreenPlaceholder + EmptyState
    ├── bots             Bots      -> ScreenPlaceholder + EmptyState
    ├── trade            Trade     -> ScreenPlaceholder + EmptyState
    └── stats            Stats     -> ScreenPlaceholder + EmptyState
**                       redirect to ''
```

Document titles are `<Screen> · Tidewatch` (`TidewatchTitleStrategy`).

**Components** (standalone, signals-first, OnPush):
- `App` (`src/app/app.ts`): renders the full-page *Tidewatch can't start: its configuration is missing.* and *Tidewatch isn't responding.* (with *Try again*) states, or the router outlet.
- `Shell`, `Rail`, `TopBar`, `AccountMenu` (`src/app/shell/`):
  - **Rail.** 220 px with blur. It holds the wordmark and eyebrow `READ THE CURRENT`, the workspace card, `<nav aria-label="Main">` with Overview, Signals, Chart, Bots, Trade and Stats (`aria-current="page"`), the conviction note, the mode line and the theme switch (`button` with `aria-pressed`).
  - **TopBar.** Breadcrumb `Workspace / <Screen>` or `Account / Change password`, the *Paper environment* pill, and a 33 px *Account* button.
  - **AccountMenu.** An `@angular/aria` menu. Enter, Space or ArrowDown opens it and focuses the first item; arrows move; Escape closes it and returns focus; an outside click closes it. Sign-out outcomes (`204` or `401`) clear the store and go to `/sign-in` with a polite status (*You're signed out.* / *You're signed out on every device.*). A sign-out failure keeps the session, says so under the button, and clears after `FAILURE_DISMISS_MS` (10 s).
- `ThemeService` (`shell/data/`): `data-theme` on `<html>`, dark by default, persisted in `localStorage['tw-theme']` with try/catch. An inline script in `index.html` applies the stored theme before boot.
- Shared UI: `Icon` and `ICONS` (`shared/ui-icon/`: inline SVG for `i-wave`, `i-overview`, `i-signal`, `i-chart`, `i-bot`, `i-trade`, `i-stats`, `i-shield`, `i-layers`, a user glyph and `close`; 24 viewBox, 1.6 stroke, `currentColor`), `Wordmark`, `PageHeader` (`h1` Manrope 700 29 px plus a sub line).
- `EmptyState` (`pages/workspace/ui-empty-state/`): a panel with the route icon, an `h2` and one sentence, with no call to action. `ScreenPlaceholder` supplies the PRD §7.3 copy per route.
- `SignIn` (`pages/sign-in/feat-sign-in/`):
  - a glass panel with a max width of 380 px; *Username* (`autocomplete="username"`, `autocapitalize="none"`, `spellcheck="false"`, `maxlength=64`) and *Password* (`current-password`);
  - *Sign in* / *Signing in…*;
  - an error line with `role="alert"`;
  - no links and no theme switch;
  - error mapping: 401 → *Wrong username or password.*; 429 → *Too many attempts. Try again in {n} seconds.* (minutes from 120 s); network failure or 5xx → *Tidewatch isn't responding. Try again in a moment.*;
  - after a failure the username is kept, the password cleared and focused.
- `ChangePassword` (`pages/account/feat-change-password/`):
  - forced mode (*Choose a new password*) and voluntary mode (*Change password*);
  - fields *Current password*, *New password* (hint *At least 12 characters. Avoid common passwords.*) and *Confirm new password*;
  - *Save new password* / *Saving…*;
  - field-level mapping of the `422` codes and the mismatch error;
  - success: a forced change goes to `next` or `/`, and a voluntary change shows *Password changed. Your other devices were signed out.*

**Data and auth layer:**
- `RuntimeConfigService` (`shared/data/`): a browser-only `fetch('/config.json')` that runs in the app initializer and validates `apiBaseUrl`. An absolute http(s) URL without credentials, query or fragment is accepted, as is a root-relative path with at least one segment. A bare `/` is rejected, and a trailing `/` is trimmed.
- `AuthApiService` (`shared/auth/data/`): every `HttpClient` call to `{apiBaseUrl}/auth/*`, plus the `Retry-After` parsing and the `AuthError` mapping by `code`.
- `AuthService`: an `@Service()` signal store with `status` (`unknown` | `signed-in` | `signed-out`), `user` and `session`. `load()` calls `/auth/me` at most once per page load and shares the in-flight request. It also exposes `signIn`, `signOut`, `signOutEverywhere`, `changePassword` and `clear`.
- `authGuard`:
  - signed out → `/sign-in?next=<target>`;
  - change forced → `/account/password?next=<target>`;
  - any failure other than 401 → the not-responding page, without signing the user out.
- `guestGuard`: redirects a signed-in user to `next` or `/`.
- `authInterceptor`: on a 401 (except from login) it clears the store and redirects to `/sign-in?next=…`. On a 403 `password_change_required` it goes to `/account/password`, without `next`.
- `util/next-url.ts` (sanitiser) and `util/auth-error-message.ts` (code-to-message mapping).

**Styles** (`src/styles/`):
- `base/tokens.css`: surfaces, lines, text, brand, chrome (`--focus` `#b9e9de`/`#235f55`, `--aurora-opacity` `1`/`.48`), zone and P&L tokens (reserved), and `--r` 9 px / `--r-lg` 16 px.
- `base/base.css`: the aurora `body::before`, focus ring, 180 ms fade and reduced motion.
- `base/typography.css`.
- `tailwind/{theme,utilities,variants}.css`: role-named typography tokens.
- `components/{a,button,input,kbd,shell}.css` and `_mixins.scss`.

**Breakpoints (D13):**
- above 1250 px, the rail is 220 px;
- at 1250 px and below, it is 190 px;
- at 1080 px and below, a 74 px icon rail;
- at 820 px and below, single-column grids;
- at 600 px and below, a sticky top strip with a 6-column nav and the theme switch at top-right.

**SSR server and image.**
- `src/server.ts` serves `/config.json` with `Cache-Control: no-cache`, outside the 1-year static cache, and handles SIGTERM gracefully. A forced-stop fallback after 5 s exits 1.
- `Dockerfile`: final stage `runtime` on `node:24-slim`, `USER node` (UID 1000), `CMD node dist/tidewatch-web/server/server.mjs`, port 4200, optional `NG_ALLOWED_HOSTS`.
- The image ships the default `public/config.json` (`{"apiBaseUrl":"http://localhost:3000"}`); bind-mount a file over it to override.

**E2E** (`e2e/playwright.config.mts`):
- Projects, in order: `public`, `journey`, `authed-setup`, `authed`, `sign-out` (`sign-out` is the teardown of `authed-setup`).
- Chromium only by default; `E2E_ALL_BROWSERS=1` adds Firefox and WebKit. One worker, no retries; trace and video off.
- Passwords are typed only through `fillSecret` (`e2e/src/support/fixtures.ts`); a plain `fill()` leaks the value into the report zip.

### tidewatch-bot (Node 24, pnpm 11.5.2, Nx 23.2.1, TypeScript ~6.0.3, ESLint 10 flat config, Vitest 4)

- `@tidewatch-bot/shared` (`packages/shared`):
  - `loadConfig()`: `ENVIRONMENT` (default `local`), `LOG_LEVEL` (default `info`), `DATABASE_URL` (required) and `REDIS_URL` (optional, validated only). `ConfigError` names variables, never values.
  - `createLogger()`: pino with redaction.
  - `createPool()` / `closePool()`: `pg`; closing is idempotent.
  - `testing/no-network`: a Vitest `setupFiles` guard that throws on non-loopback `fetch`, `http(s)`, `net`/`tls` connect, `dgram` and DNS calls, and refuses every c-ares query.
- `@tidewatch-bot/worker` (`packages/worker`): `run()` loads the config, creates the logger and pool, runs `SELECT 1`, logs `worker: database reachable`, closes the pool and exits 0. Invalid config or an unreachable database exits 1 with a redacted error.
- Module-boundary tags: `type:shared` and `type:app`. Each package declares its own third-party dependencies, checked by `@nx/dependency-checks`.
- `Dockerfile` (repo root): multi-stage on `node:24-alpine`, a frozen pnpm install, a runtime stage with `--prod --filter "@tidewatch-bot/worker..."`, `USER node` (UID 1000) and `CMD ["node","packages/worker/dist/main.js"]`. Image size is 269 MB.

### Workspace root (not a git repo; files written in place)

- `docker-compose.yaml` (`name: tidewatch`):
  - `db`: `timescale/timescaledb-ha:pg18`, project-scoped named volume `tidewatch-pgdata` on `/home/postgres/pgdata`. Its healthcheck rejects a non-URL-safe `POSTGRES_PASSWORD`, then runs `pg_isready`.
  - `redis`: `redis:8-alpine`, no persistence.
  - `migrate`: one-shot built from `./tidewatch-migrations`, after `db` is healthy.
  - `tidewatch-service`: `deploy/Dockerfile`; starts after `migrate` completes successfully and `redis` is healthy; healthcheck is the `healthcheck` subcommand.
  - `tidewatch-web`: `NG_ALLOWED_HOSTS=localhost,127.0.0.1`; `config.json` is pinned through an inline compose `configs` entry; healthcheck is a Node fetch of `/sign-in`.
  - `tidewatch-bot`: one-shot, after `migrate`.
  - All host ports bind `127.0.0.1`; 9090 is never published.
  - The header documents start, logs, CLI reset, migration status, stop vs. fresh start (with a `down -v` data-loss warning), the password charset and A1.
- `.env.example`: `POSTGRES_PASSWORD` (placeholder; the stack won't start until it is replaced), `TIDEWATCH_ADMIN_USERNAME=admin`, `TIDEWATCH_ADMIN_PASSWORD=` (first start only), `TIDEWATCH_KEY_ENCRYPTION_KEY=`, `TIDEWATCH_PG_PORT=5433` and `TIDEWATCH_REDIS_PORT=6380`.
- `.forge/docker-compose.json`, synced with `forge-setup-docker-compose`:
  - projects: `tidewatch-web` → `[tidewatch-web]`; `tidewatch-service` → `[tidewatch-service]`; `tidewatch-bot` → `[]`, with the reason "slice 0 worker is a connect-and-exit check…";
  - base services: `tidewatch-service`, `tidewatch-web`, `redis`, `preview-gateway`;
  - `database.required: true`, with `isolated` mode adding `db` and `migrate` (built from `{{project:tidewatch-migrations}}`);
  - secrets come through `env_file` (`format: raw`) from `.forge/docker/secrets/tidewatch.env` (mode 0600, directory 0700; keys `POSTGRES_PASSWORD`, `TIDEWATCH_ADMIN_PASSWORD`, `DATABASE_URL`);
  - `preview: {service: preview-gateway, port: 8080, path: "/"}`;
  - `existing` database mode is not configured.
- `.forge/docker/templates/preview-gateway/Caddyfile`: see D16. `admin off`, `auto_https off`, no access log.

### Operations

| Task | Command (from the workspace root) |
|---|---|
| Start | `cp .env.example .env` (set `POSTGRES_PASSWORD` and, for the first start, `TIDEWATCH_ADMIN_PASSWORD`), then `docker compose up -d --build` and `docker compose ps -a`. Do not use `up --wait` (A10). |
| Expected state | `db`, `redis`, `tidewatch-service` and `tidewatch-web` healthy; `migrate` and `tidewatch-bot` `Exited (0)`. Sign in at `http://localhost:4200`. |
| Logs | `docker compose logs -f tidewatch-service`; `docker compose logs migrate tidewatch-bot` |
| CLI password reset | `read -rs TW_PW && printf '%s\n' "$TW_PW" \| docker compose exec -T tidewatch-service /tidewatch-service admin set-password --username admin; unset TW_PW`. Always pipe the password; without a pipe, `exec -T` echoes it. |
| Migration status | `docker compose run --rm --entrypoint sh migrate -c 'exec goose -env none -table goose_db_version -dir /migrations postgres "$DATABASE_URL" status'` |
| Stop, keep data | `docker compose down` |
| Fresh start | `docker compose down -v`. **Destroys** `tidewatch_tidewatch-pgdata` (all users, sessions and events); `TIDEWATCH_ADMIN_PASSWORD` must be set again. |
| After first start | Remove `TIDEWATCH_ADMIN_PASSWORD` from `.env`; bootstrap ignores it and warns while users exist. |
| Preview | `docker-compose-cli up --run <run> --database isolated --retention retain`; the browser entry is the gateway's dynamic loopback port. |

| Port | What | Owner compose |
|---|---|---|
| 4200 | web | `127.0.0.1:4200` |
| 3000 | API | `127.0.0.1:3000` |
| 9090 | metrics | never published |
| 5432 → `TIDEWATCH_PG_PORT` (5433) | Postgres | `127.0.0.1` |
| 6379 → `TIDEWATCH_REDIS_PORT` (6380) | Redis | `127.0.0.1` |
| dynamic | Forge preview | one loopback port → gateway `:8080` |

**Service environment** (README table):
- `ENVIRONMENT` (`local`|`development`|`staging`|`production`; anything but `local` requires an https app origin and sets `Secure`);
- `PORT` 3000 and `METRICS_PORT` 9090, which must differ;
- `LOG_LEVEL` `info`; `SHUTDOWN_GRACE_PERIOD` `15s`;
- `SERVICE_NAME`, `VERSION`, `COMMIT_HASH`, `BUILD_DATE`, `GIN_MODE`;
- `DATABASE_URL` (required);
- `REDIS_URL` (optional; validated, nothing connects);
- `TRUSTED_PROXIES` (empty = trust none);
- `TIDEWATCH_APP_ORIGIN` (required; exact `scheme://host[:port]`);
- `TIDEWATCH_ADMIN_USERNAME` (`admin`; `^[a-z0-9][a-z0-9._-]{2,63}$`);
- `TIDEWATCH_ADMIN_PASSWORD` (bootstrap and CLI fallback only; never stored or logged);
- `TIDEWATCH_KEY_ENCRYPTION_KEY` (optional; when set, base64 of exactly 32 bytes).

Recovery is the CLI reset, never a down migration.

## Files touched

Merged revisions: migrations `87ce578`, service `f9da2cd`, bot `fe17845`, web `f0d0a7f`. The worktrees under `.forge/docker/runs/fauth-69425a62/worktrees/` equal these merged trees.

**tidewatch-migrations** (tidewatch-labs/tidewatch-migrations#1; worktree `b7ddc75378`; base `dd7bcc8`)
- `migrate.mjs` (deleted)
- `package.json`, `.env.example`, `.gitignore` (adds `.mcp.json`), `README.md`, `CLAUDE.md` (modified; the `forge:start`/`forge:end` block is kept byte-identical)
- `Makefile`, `Dockerfile`, `.dockerignore` (created)
- `scripts/dsn-guard.sh`, `scripts/check-disposable-db.sh` (created)
- `migrations/20261004153020_enable_extensions.sql`, `migrations/20261004153023_auth_foundation.sql` (created)

**tidewatch-service** (tidewatch-labs/tidewatch-service#1; worktree `329891b601`; base `ddcfad7`; plan `.plans/foundation-auth.md`)
- `main.go` (deleted); `go.mod`, `.gitignore`, `CLAUDE.md` (modified); everything below is created
- `go.sum`, `Makefile`, `.env.example`, `.dockerignore`, `README.md`, `deploy/Dockerfile`, `scripts/check-image.sh`, `scripts/integration-test.sh`
- `cmd/tidewatch-service/main.go`
- `internal/cli/{cli,serve,setpassword,healthcheck}.go` + `{cli,setpassword,healthcheck}_test.go`
- `internal/app/{app,router,lifecycle}.go` + `{router,lifecycle,servers,clientip}_test.go`
- `internal/handlers/{auth,health}.go` + tests
- `internal/httpx/middleware/{bodylimit,cors,csrf,logger,readygate,recovery,securityheaders}.go` + `{bodylimit,cors,csrf,logger,readygate,securityheaders}_test.go`
- `internal/httpx/authn/{context,gates,session}.go` + `{gates,session}_test.go`; `internal/httpx/origin/origin.go` + test; `internal/httpx/requestid/requestid.go` + test; `internal/httpx/response/response.go` + test
- `internal/services/auth/{service,login,session,password}.go` + `{login,session,password,burst,fakes}_test.go`; `internal/services/bootstrap/service.go` + test
- `internal/auth/password/{argon2id,limiter,policy,common}.go` + tests; `internal/auth/password/data/{common-passwords.txt,SOURCE.md,LICENSE}`
- `internal/auth/session/{token,cookie,lifetime,principal}.go` + `{token,cookie,lifetime}_test.go`
- `internal/auth/throttle/{guard,keyset,lockout,window}.go` + `{guard,attempt,lockout,window}_test.go`
- `internal/auth/username/username.go` + test
- `internal/repository/postgres/{store,user,session,event}.go` + `{user,session,event}_test.go`
- `internal/platform/postgres/{postgres,schema}.go` + `schema_test.go`; `internal/platform/health/{health,readiness,waiter}.go` + tests
- `internal/audit/audit.go` + test; `internal/clock/clock.go` + test; `internal/clock/clocktest/fake.go`
- `internal/config/{config,validate,secrets}.go` + `{config,secrets}_test.go`
- `internal/observability/logging/{logger,redact,errorlog}.go` + `{redact,errorlog}_test.go`; `internal/observability/metrics/{metrics,handler,middleware}.go` + test
- `internal/pgtest/{pgtest,migrate}.go` (integration tag only)
- `pkg/apperror/{apperror,codes}.go` + `apperror_test.go`
- `test/integration/{main,harness,bootstrap,ready,login,session,password,cli,events,redaction}_test.go`

**tidewatch-bot** (tidewatch-labs/tidewatch-bot#1; worktree `6945fd5d6c`; base `92fec89`)
- `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `nx.json`, `tsconfig.base.json`, `tsconfig.json`, `.gitignore`, `README.md`, `CLAUDE.md` (modified)
- `eslint.config.mjs`, `.env.example`, `Dockerfile`, `.dockerignore` (created)
- `packages/shared/{package.json,tsconfig.json,tsconfig.lib.json,tsconfig.spec.json,vitest.config.mts}` (created)
- `packages/shared/src/{index,config,logger,db}.ts` + `{config,logger,db}.spec.ts`; `packages/shared/src/testing/no-network.ts` + spec (created)
- `packages/worker/{package.json,tsconfig.json,tsconfig.lib.json,tsconfig.spec.json,vitest.config.mts}` (created)
- `packages/worker/src/{main,run}.ts`, `run.spec.ts`, `no-network-guard.spec.ts` (created)

**tidewatch-web** (tidewatch-labs/tidewatch-web#1; worktree `5eb4e5c7ea`; base `7643522`)
- `src/app/app.html`, `src/app/app.css`, `src/app/nx-welcome.ts`, `e2e/src/example.spec.ts` (deleted)
- `package.json`, `pnpm-lock.yaml`, `project.json`, `.prettierrc`, `.prettierignore`, `.gitignore`, `README.md`, `CLAUDE.md` (modified)
- `src/index.html`, `src/styles.css`, `src/server.ts` (modified)
- `src/app/{app,app.spec,app.config,app.routes,app.routes.server}.ts` (modified)
- `e2e/playwright.config.mts`, `e2e/eslint.config.mjs` (modified)
- `.postcssrc.json`, `Dockerfile`, `.dockerignore`, `public/config.json` (created)
- `src/styles/base/{tokens,base,typography}.css`, `src/styles/tailwind/{theme,utilities,variants}.css`, `src/styles/components/{_mixins.scss,a.css,button.css,input.css,kbd.css,shell.css}` (created)
- `src/app/app.routes.spec.ts`, `src/app/tidewatch-title-strategy.ts` + spec (created)
- `src/app/shell/{shell,rail,top-bar,account-menu}.ts` + specs; `src/app/shell/data/theme.service.ts` + spec (created)
- `src/app/shared/ui-icon/{icon,icons}.ts` + `icon.spec.ts`; `src/app/shared/ui-wordmark/wordmark.ts` + spec; `src/app/shared/ui-page-header/page-header.ts` + spec (created)
- `src/app/shared/data/runtime-config.service.ts` + spec (created)
- `src/app/shared/auth/data/{auth.model,auth-api.service,auth.service}.ts` + `{auth-api.service,auth.service}.spec.ts` (created)
- `src/app/shared/auth/{auth.interceptor,auth.guard,guest.guard}.ts` + specs; `src/app/shared/auth/util/{next-url,auth-error-message}.ts` + specs (created)
- `src/app/pages/sign-in/sign-in.routes.ts`, `src/app/pages/sign-in/feat-sign-in/sign-in.ts` + spec (created)
- `src/app/pages/account/account.routes.ts`, `src/app/pages/account/feat-change-password/change-password.ts` + spec (created)
- `src/app/pages/workspace/workspace.routes.ts`, `feat-screen-placeholder/screen-placeholder.ts` + spec, `ui-empty-state/empty-state.ts` + spec (created)
- `e2e/src/{journey,sign-in,shell,password,sign-out,viewport,a11y,theme,fonts}.spec.ts`, `e2e/src/auth.setup.ts`, `e2e/src/support/{fixtures,screens}.ts` (created)

**Workspace root** (`/Users/maichinu/tidewatch`, not git; reported as workspace changes, not PRs)
- `docker-compose.yaml` (created)
- `.env.example` (created)
- `.forge/docker-compose.json` and its lock (created through the helper's `sync`)
- `.forge/docker/templates/preview-gateway/Caddyfile` (created; DNS-rebinding fix applied after the root review)
- `.forge/docker/secrets/tidewatch.env`: a local preview secrets file (0600) created at the owner's request (OWNER-8). It is not a deliverable, and its values are never printed.
- `.forge/workspace.json`: **not** changed by this build. FR-INFRA-008 is open.

## Test plan

### Commands (each from its project root)

| Project | Command | Result |
|---|---|---|
| service | `make ci` (vet, `go test -race`, build) | Passed at every step and on the reviewed head `67047cd`. |
| service | `make test-integration TIDEWATCH_MIGRATIONS_DIR=<tidewatch-migrations checkout>` | 1579 tests, 0 fail, 0 skip, run 6 times on fix-2. Log at `bin/integration-test.log`. |
| service | `make check-image` | Passed: nonroot, ports 3000/9090, no `.env`, healthcheck array present. |
| service | `govulncheck` | 9 reachable findings went to 0 after fix-1 (`x/text` v0.39.0, `quic-go` v0.59.1, toolchain go1.26.8). |
| migrations | `make migrate-validate`; `make help` | Passed. |
| migrations | `make check-disposable-db` | Passed: up → status → down → up → down-to 0 → up round trip, §5 catalog checks and `\d+` transcript; UPDATE, DELETE and TRUNCATE on `events` fail with "append-only"; plus malformed-DSN cases. |
| bot | `pnpm nx run-many -t lint test typecheck build` | Passed (fix-1 and fix-2). |
| web | `pnpm nx run-many -t lint test build` | Passed; 394 unit tests on `78b88af`. |
| web E2E | `BASE_URL=<url> E2E_ADMIN_PASSWORD=<from protected file> pnpm nx e2e e2e --skip-nx-cache --reporter=list,json,html` | 156/156 on the preview (twice) and 156/156 cross-origin on the owner compose. `--skip-nx-cache` is required because the Nx target cache ignores env. |

Key test files:
- **Service integration:** `test/integration/*_test.go` (`//go:build integration`).
- **Service named acceptance tests:** for example `TestContract_RequiredSchemaVersion`, `TestGuard_KeyCapFailsClosed`, `TestSessionRepo_HashOnlyAndRevokeCounts`, `TestServer_ReadTimeoutDoesNotCancelRequestContext`, and the concurrency test in `internal/services/auth/burst_test.go`.
- **Web:** `e2e/src/*.spec.ts`; unit specs beside each source file.
- **Bot:** `packages/*/src/*.spec.ts`; the no-network guard spec is `packages/shared/src/testing/no-network.spec.ts`.

### Stages (kept distinct)

- **Implemented.** Every planned step was completed and its contract verified on the build branches:
  - service MIG1–MIG3 and S1–S11;
  - bot S1–S5;
  - web S1–S3, M1 (S4+S5), S6–S8.

  Reviewed heads: migrations `b86b716`, service `67047cd`, bot `9c21124`, web `78b88af`. Code review loops: service and migrations took 2 fix loops before security and code approval in round 3; bot took 2 fix loops (round 3, security); web took 2 fix loops before all five reviewers approved (round 3 recheck: angular and security).
- **Verified (pre-merge, on the reviewed heads).** Per-step contracts and reviews, plus the isolated preview (Compose project `forge-0199b29a-fauth-69425a62`, `http://127.0.0.1:56376/` after the gateway fix):
  - FR-E2E-001: 156/156, run before and after the rebinding fix, with secret scans at 0 hits;
  - FR-INFRA-005 and FR-INFRA-006 (rebinding Host → 421; same-origin 401/400; CSRF 403; register 404; metrics 404);
  - the FR-AUTH-021 CLI transcript;
  - FR-MIG-005 rerun no-op, FR-SVC-011 healthy, and the FR-WEB-017 foreign Host → 400.
- **Merged.** 2026-10-05T16:31:45Z at the owner's explicit request (OWNER-9). Merge commits pinned to the reviewed heads, in order: migrations `87ce578` → service `f9da2cd` → bot `fe17845` → web `f0d0a7f`. No CI checks exist (D4).
- **Owner stack.** The post-merge checks ran on the merged primaries (fast-forwarded), using the root `docker-compose.yaml` under the **disposable project `tidewatch-fauth-verify`** with a fresh volume. That stack was removed afterwards with `down -v` (test data only). Results: FR-INFRA-001/002/004, FR-BOT-003/005, FR-MIG-005, FR-SVC-005, the cross-origin FR-AUTH-017/018 curls, and FR-E2E-002 at 156/156 cross-origin (localhost:4200 → localhost:3000, secret scan 0).
  - The build never started the owner's default `tidewatch` compose project, so nothing is confirmed running on it.
  - The preview is retained. Its admin was restored to the owner's password through the CLI, with the forced change pending, and the `e2e/.auth` credentials were deleted.

### Per-ID results (from `.forge/features/foundation-auth/verification.md`, authoritative)

No ID failed.

| Area | IDs | Result |
|---|---|---|
| Migrations | FR-MIG-001…005 | passed (005 also on the preview and the owner compose: first run exit 0, rerun "no migrations to run. current version: 20261004153023", exit 0) |
| Service | FR-SVC-001…011 | passed (005: `/metrics` 404 on 3000 and 9090 unpublished on the owner compose; `/api/metrics` 404 on the preview) |
| Auth | FR-AUTH-001…025 | passed (009/010/023 include the fix-2 atomic reservation; 017/018 by table tests plus preview and owner-compose curls; 021 by integration test plus the piped `docker compose exec -T` transcript) |
| Web | FR-WEB-001…018 | passed (008: the web server sends `no-cache`, and the gateway serves its own config with `no-store`; 010 judged from rendered screenshots in both themes at 390/1080/1440 plus design review r2; 015: axe 0 violations, min text contrast 4.65:1; 017: foreign Host → 400) |
| Web | FR-WEB-019 | **unverified**: post-merge `DESIGN.md` step, in progress |
| Bot | FR-BOT-001…005 | passed (003/005 at image level and on the owner compose: `worker: database reachable`, `Exited (0)`) |
| Infra | FR-INFRA-001…007 | passed (002: all published ports on 127.0.0.1; 003: images non-root (migrate UID 10001, service 65532, bot 1000, web 1000) with no `.env*`; 004: admin row and 8 events persisted across `down`/`up -d`) |
| Infra | FR-INFRA-008 | **unverified**: after merge; the owner changes it in Forge settings |
| E2E | FR-E2E-001, FR-E2E-002 | passed, 156/156 each |
| Docs | FR-DOC-001 | passed |
| Docs | FR-DOC-002 | pending the final report (the list is under Open questions below) |

### Manual reproduction

1. From the workspace root, follow *Start* in Operations against a fresh volume. Expect the state in that table and *Sign in* at `http://localhost:4200`.
2. Sign in as `admin` with the bootstrap password. Expect a redirect to `/account/password`. Change the password and land on Overview. Visit all six screens, then sign out. `/stats` should then redirect to `/sign-in?next=%2Fstats`.
3. Cross-origin checks against `http://localhost:3000`:
   - a preflight with `Origin: http://localhost:4200` returns `204` with exact ACAO and credentials;
   - a foreign or other-port Origin returns `403` with no ACAO;
   - a POST without `X-Tidewatch-Request`, or with a foreign Origin, returns `403`;
   - `/auth/register` returns `404` for GET, POST and OPTIONS;
   - `/metrics` returns `404`, and 9090 is unreachable.
4. Run the CLI reset (Operations). Expect `password updated for admin; all sessions revoked` and exit 0; the next sign-in forces a change.
5. `docker compose down`, then `docker compose up -d`. The admin and events persist, and `migrate` is a no-op.

## Open questions

### Open items

- **FR-INFRA-008 (owner action).** `.forge/workspace.json` still has `"runCommand": "go run ."` for `tidewatch-service`. The entrypoint moved, so the owner changes it in Forge's project settings to `go run ./cmd/tidewatch-service`. Unverified until then.
- **FR-WEB-019 (in progress).** `tidewatch-web/DESIGN.md` is being written with `forge-setup-impeccable` in the `web-design` worktree (branch `codex/forge-fauth-69425a62-design`, base `f0d0a7f`). It must document the implemented tokens and components, link 03 and the mockup, and record the D6, D7 and D13 exceptions plus OWNER-4/5/6 and PW-4. Its PR is not merged; the ID stays unverified.
- **Bookkeeping drift.** The stage-key line in `verification.md` still says "Merged = PR merged (none yet)" and "Running on the owner's stack … none yet", which contradicts its own status line. `state.json` still lists A6 as pending; `verification.md` records it validated.
- **A5 / Forge tooling.** `docker-compose-cli` and `execution-cli` accept only registered project IDs, so a future run can't resolve `{{project:tidewatch-migrations}}` for the preview `migrate` build, and the helpers reject the resource slug. Forge needs support for `migrationsPath` as a workspace resource.

### Out-of-date documents (FR-DOC-002; not edited, per D17)

- `documents/05-auth-and-access.md` §8: still describes the SSR server forwarding the session cookie (now D2: never) and the "rail's user area" (now D7: the account menu in the top bar). Deferred by the owner.
- `documents/03-design-system.md`:
  - §4 breakpoints 1100/760 vs. the mockup's 1250/1080/820/600 (D13); deferred by the owner.
  - §3 body text 14px/1.45 vs. the approved mockup's 13px/1.5 (PW-4).
  - The light `--text-3` measures 4.42:1 on `--bg`, below AA.
  - The light top-bar tint and leading crumb changes (OWNER-4) and the light current crumb in `--text` (OWNER-6).
  - Hue-less errors (OWNER-5) are consistent with §2.3 and §10.
- `documents/features/00-foundation-and-auth.md`: the "CI: lint + unit tests" line. CI is deferred (D4).
- `tidewatch-specs/foundation-auth/prd.md` A4 wording: Angular SSR has no built-in allowed-hosts list.

### Known limits (accepted and documented)

- **Single instance (D12).** Limits and lockout live in process memory, are cleared by a restart and are not shared across instances. The CLI reset does not clear a running server's lockout.
- **`TRUSTED_PROXIES` empty.** Neither the root compose nor the preview definition sets it. Clients arriving through a proxy, gateway or compose bridge share one IP, so the 5-per-minute per-IP login limit can act globally.
- **Argon2 wait queue unbounded.** Memory is capped at 4 operations. Waiters leave only when the client disconnects, and `ReadTimeout` does not cancel them. Bounding the queue needs a load-shedding error that PRD §6 doesn't define.
- **Throttle key cap.** At 100,000 keys per tracker, new clients or usernames get `429` until entries expire or the service restarts.
- **Lockout edge.** About 19 failures followed by a double-submitted correct password can produce a counted `401` and lock (code review r3; documented, accepted).
- **Service redaction.** It over-masks up to the last `@` on a line. A DSN password of 8 bytes or more that is an ordinary word is masked everywhere. Output through the stdlib `log` default logger bypasses the writer.
- **Bot redaction.** It is not a general secret scanner: other query parameters, JSON-escaped URLs and non-exact key names are not masked.
- **No-network guard residual limits.** Child processes, `worker_threads`, native addons and a custom `dgram` lookup are not guarded. Some refusals arrive asynchronously.
- **`gin` init.** An invalid `GIN_MODE` panics in gin's `init()` before the variable-naming validation runs.
- **`POSTGRES_PASSWORD`.** It is limited to `[A-Za-z0-9._~-]`, because percent-encoding can't work when one value is both the Postgres password and part of the URL.
- **Shared secrets file.** The preview passes one secrets file to `db`, `migrate` and `tidewatch-service`, so the admin password is visible in the `db` and `migrate` containers.
- **Internal endpoints.** `/info` serves build metadata on the main port. The metrics listener has no authentication.
- **Sessions.** They persist until expiry; there is no cleanup job in slice 0.
- **Web UI.**
  - A login password over 1024 bytes returns `invalid_request`, shown as the *isn't responding* copy.
  - At 390 px the sign-out failure alert covers the `h1` while it is visible; it auto-clears within 10 s.
  - The pre-hydration sign-in form looks dimmed (disabled).
  - axe reports needs-review items (not violations) on the open account menu.

### Follow-ups

- **web:**
  - Add client timeouts to login, logout and change-password. A hung sign-out leaves the session alive behind a busy state, a shared-device risk (security r3).
  - Move `@angular-devkit/build-angular` to `devDependencies`.
  - Add `frame-ancestors` / `X-Frame-Options` on HTML responses; the PRD is silent.
  - Optional: anchor the sign-out failure alert below the top bar on phones, and run a keyboard-focus check of the rail links and theme switch.
- **bot:** pin the base image by digest and add a `packageManager` hash (deferred with CI, D4). Fix the worker `main` field nit and the flake risk from a 100 ms timing assertion.
- **service:** consolidate `config.parseOrigin` with `origin.Normalise`. Pin `golang:1.26-alpine` and `distroless/static:nonroot` by digest (with CI). Bump `toolchain` with each patched Go release.
- **forge-tooling:** support `migrationsPath` as a workspace resource in the worktree, execution and preview helpers (A5).
- **Deferred by the owner:** CI (`forge-setup-cicd`), production topology and TLS, the AES-GCM credential helper (and making `TIDEWATCH_KEY_ENCRYPTION_KEY` required with the first credential-storing slice), Redis-backed rate limits, and updating 05 §8, 03 §4 and the brief's CI line.
- **When roles are added:** revisit the scope of `requireRole("admin")` over `/auth/*`, for example whether a non-admin may still reach `/auth/me` and logout.

## Cross-cutting links

The wiki had no pages at baseline `0a171c1`, so there are no existing slugs to link. This source supports these candidate concept pages, for the wiki-updater to decide: `auth-model` (sessions, argon2id, lockout, forced change), `request-protection` (CSRF and exact-origin CORS), `required-schema-version`, `centralized-migrations`, `forge-preview-gateway`, `local-compose-stack`, `audit-events`, `log-redaction`, `design-tokens-aurora`, `web-shell`.
