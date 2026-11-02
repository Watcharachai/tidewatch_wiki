# Foundation and auth (Slice 0)

**Summary**: Slice 0 built the base every later Tidewatch slice depends on: goose migrations on Postgres 18, a Go service with cookie-session auth for one seeded admin, an Aurora-styled Angular shell, a connect-and-exit bot worker, a root compose stack and a Forge preview gateway. All four PRs merged on 2026-10-05. FR-WEB-019 (`DESIGN.md`) closed on 2026-10-06 when its PR merged; FR-INFRA-008 remains open. Slice 1 changed the bot, Overview and schema version. **Accounts and roles (2026-10-29) retired the seeded-admin model.** The seeded `admin` is now a plain user with role `user`. `TIDEWATCH_ADMIN_*` is retired, and the bootstrap now creates the first *operator* from `TIDEWATCH_OPERATOR_*`. `admin set-password` became `user set-password`. See "Changed by later slices" and [[accounts-and-roles]].

**Sources**: `raw/2026-10-05-foundation-auth.md`; tidewatch-web PR 2 (https://github.com/tidewatch-labs/tidewatch-web/pull/2) for the FR-WEB-019 closure; `raw/2026-10-07-market-data.md` for what slice 1 changed; `raw/2026-10-29-accounts-roles.md` for what accounts and roles retired or replaced

**Last updated**: 2026-10-29

---

## What this slice delivered

Every later slice needs a database, a service that knows who you are, and a web shell that already looks like Tidewatch. The owner signs in as a seeded `admin`, and there is no sign-up (source: raw/2026-10-05-foundation-auth.md §Concept). Before the slice, `tidewatch-service` was an empty `main.go`, `tidewatch-web` was the Nx welcome app, `tidewatch-bot` had an empty `packages/`, and `tidewatch-migrations` was an MSSQL scaffold, the wrong engine (source: raw/2026-10-05-foundation-auth.md §Concept).

| Project | What it became | Concept page |
|---|---|---|
| `tidewatch-migrations` | goose on Postgres 18; the `timescaledb` and `vector` extensions plus `users`, `sessions`, `events`, `api_credentials` | [[centralized-migrations]] |
| `tidewatch-service` | Go 1.26 service: cookie sessions, argon2id, in-memory limits and lockout, exact-origin CORS and CSRF, readiness that waits for the schema, a password-reset CLI, append-only audit events | [[auth-model]], [[request-protection]] |
| `tidewatch-web` | Angular 22.1 SSR shell in the Aurora design: prerendered sign-in, forced or voluntary password change, six titled empty-state screens | [[design-system-decisions]] |
| `tidewatch-bot` | `packages/shared` and a connect-and-exit `packages/worker` | see Components below |
| Workspace root | `docker-compose.yaml`, `.env.example`, Forge preview definition with a Caddy gateway | [[forge-preview-gateway]] |

(source: raw/2026-10-05-foundation-auth.md, summary block and §Components)

The authority documents were `tidewatch-specs/foundation-auth/{intent,prd,build-prompt}.md`, `documents/03-design-system.md` (design) and `documents/05-auth-and-access.md` (auth, as adjusted by D1, D2, D7, D11 and D16). The `documents/` folder is never edited (D17) (source: raw/2026-10-05-foundation-auth.md §Concept).

## Outcomes O1 to O7

| # | Outcome | Result |
|---|---|---|
| O1 | One command brings everything up | Passed (disposable compose project, fresh volume, healthy isolated preview) |
| O2 | Health is truthful | Passed: `/health` is always 200; `/ready` went 503, 503, 200 as the schema and extensions appeared |
| O3 | Sign in as the seeded admin, forced change, land on Overview | Passed |
| O4 | Approved shell on every route, dark default, light first-class, no horizontal scroll | Passed |
| O5 | Sign out and sign out everywhere revoke sessions on the server | Passed |
| O6 | Hostile use fails | Passed |
| O7 | Later slices start small | Passed since 2026-10-06. The source recorded it partly open pending FR-WEB-019, whose `DESIGN.md` has since merged (see [[design-system-decisions]]) |

(source: raw/2026-10-05-foundation-auth.md §Concept, Outcomes O1-O7)

## Decision map

| Decision | Topic | Where it lives |
|---|---|---|
| D1 | Cross-origin API with four guardrails | [[request-protection]] |
| D2 | Render modes: `/sign-in` prerendered, everything else client-rendered; SSR never calls the API | [[request-protection]] (host allow-list), this page (Web shell) |
| D3 | Env naming: unprefixed infra settings, `TIDEWATCH_`-prefixed product settings | this page (Operations) |
| D6, D7, D13 | Styling, account menu, breakpoints | [[design-system-decisions]] |
| D9, D10 | Only a one-shot `migrate` container applies migrations automatically (local compose database only); the service starts without the schema and waits | [[centralized-migrations]] |
| D11 | Server-side forced password change | [[auth-model]] |
| D12 | Limits and lockout in process memory | [[auth-model]] |
| D15 | Playwright only against a fresh, separate database | this page (Verification) |
| D16 | Forge preview gateway | [[forge-preview-gateway]] |
| D17 | `documents/` is never edited | this page (Out-of-date documents) |

(source: raw/2026-10-05-foundation-auth.md §Concept, Architecture decisions and Related decisions)

## Components in brief

### Service

One binary with three subcommands: `serve` (default), `admin set-password --username <name>` and `healthcheck` (distroless has no curl, so the healthcheck is a subcommand). `main.go` only sets up the signal context; wiring lives in `internal/cli` and `internal/app`. The final image is `gcr.io/distroless/static:nonroot` (UID 65532), exposing 3000 and 9090. Startup validates config first (naming the variable, never the value), binds both listeners immediately, then waits in the background for the schema (see [[centralized-migrations]]), and bootstraps the admin once under an advisory lock (source: raw/2026-10-05-foundation-auth.md §Components).

### Web shell

- Route tree: `/sign-in` (lazy, guest guard, prerendered, outside the shell), then a `Shell` under `authGuard` with `account/password`, and the six workspace routes (Overview, Signals, Chart, Bots, Trade, Stats), each a `ScreenPlaceholder` with an `EmptyState`. Unknown paths redirect to `/`. Titles read `<Screen> · Tidewatch`.
- Runtime config: the browser fetches `/config.json` at app initialization and validates `apiBaseUrl`. The shipped default is the service origin on `localhost:3000`; the preview gateway serves `/api` instead.
- Auth layer: a signal store (`AuthService`), `authGuard`, `guestGuard` and an interceptor. Details are in [[auth-model]] and [[request-protection]].
- Playwright suite: projects `public`, `journey`, `authed-setup`, `authed`, `sign-out`; Chromium by default, one worker, no retries. Passwords are typed only through `fillSecret`, because a plain `fill()` leaks the value into the report zip.

(source: raw/2026-10-05-foundation-auth.md §Components, tidewatch-web)

### Bot

`@tidewatch-bot/shared` provides `loadConfig()` (`ENVIRONMENT`, `LOG_LEVEL`, required `DATABASE_URL`, optional `REDIS_URL`; errors name variables, never values), a pino logger with redaction, `createPool()`/`closePool()` and a Vitest no-network guard that throws on non-loopback network access. `@tidewatch-bot/worker` runs `SELECT 1`, logs `worker: database reachable`, closes the pool and exits 0; bad config or an unreachable database exits 1 with a redacted error. The runtime image is `node:24-alpine` and non-root. The slice-0 worker is deliberately a connect-and-exit check, so it is listed with no preview project in the Forge compose definition (source: raw/2026-10-05-foundation-auth.md §Components, tidewatch-bot and Workspace root).

## Operations

Run from the workspace root (not a git repo; files were written in place).

| Task | Command or note |
|---|---|
| Start | `cp .env.example .env`, set `POSTGRES_PASSWORD` and, on first start, `TIDEWATCH_ADMIN_PASSWORD` (**retired since accounts and roles**: the first start now needs `TIDEWATCH_OPERATOR_PASSWORD` and `TIDEWATCH_OPERATOR_PHONE` while `operators` is empty, plus a code sender, `dev` with `TIDEWATCH_OTP_DEV_CODE` only under `ENVIRONMENT=local`; see [[operator-console]]); then `docker compose up -d --build` and `docker compose ps -a`. Do not use `up --wait`, because the one-shot bot exits (A10). |
| Expected state | `db`, `redis`, `tidewatch-service`, `tidewatch-web` healthy; `migrate` and `tidewatch-bot` `Exited (0)`. Sign in at `http://localhost:4200`. |
| CLI password reset | Always pipe the password in, for example `read -rs TW_PW && printf '%s\n' "$TW_PW" \| docker compose exec -T tidewatch-service /tidewatch-service admin set-password --username admin; unset TW_PW`. Without a pipe, `exec -T` echoes it. **Since accounts and roles the command is `user set-password`**, and `admin set-password` is a deprecated alias for one release. The backfilled owner row keeps the username `admin`. Operators reset with `operator set-password`. |
| Stop, keep data | `docker compose down` |
| Fresh start | `docker compose down -v` destroys the `tidewatch-pgdata` volume (all users, sessions and events). |
| After first start | Remove `TIDEWATCH_ADMIN_PASSWORD` from `.env`; bootstrap ignores it and warns while users exist. **Since accounts and roles:** remove `TIDEWATCH_OPERATOR_PASSWORD` once the first operator has signed in (it is ignored with a warning once operators exist), and remove the retired `TIDEWATCH_ADMIN_*`. |

Ports: web `127.0.0.1:4200`, API `127.0.0.1:3000`, metrics 9090 never published, Postgres `TIDEWATCH_PG_PORT` (5433) and Redis `TIDEWATCH_REDIS_PORT` (6380), both on `127.0.0.1`. All published ports bind loopback. `POSTGRES_PASSWORD` is limited to `[A-Za-z0-9._~-]` because one value both initializes Postgres and is embedded in `DATABASE_URL`. Recovery from a lost password is the CLI reset, never a down migration (source: raw/2026-10-05-foundation-auth.md §Components, Operations).

The compose stack: `db` (`timescale/timescaledb-ha:pg18`, named volume on `/home/postgres/pgdata`, assumption A1 validated), `redis` (`redis:8-alpine`, no persistence), one-shot `migrate`, `tidewatch-service` (starts after `migrate` succeeds and `redis` is healthy), `tidewatch-web` and one-shot `tidewatch-bot` (after `migrate`) (source: raw/2026-10-05-foundation-auth.md §Components, Workspace root).

## Verification

- Unit and integration: service `make ci`, and 1579 integration tests with 0 failures, run six times on the second fix loop; `govulncheck` went from 9 reachable findings to 0; web had 394 unit tests; migrations passed a disposable-database round trip.
- E2E (FR-E2E-001 and FR-E2E-002): 156 of 156 Playwright tests passed on two topologies, same-origin through the preview gateway and cross-origin on a disposable copy of the owner's compose stack (`localhost:4200` to `localhost:3000`). `--skip-nx-cache` is required because the Nx cache ignores env.
- Per-ID results: no ID failed. At the time of the source, FR-WEB-019 and FR-INFRA-008 were unverified and FR-DOC-002 was pending the final report. FR-WEB-019 has since closed: `tidewatch-web/DESIGN.md` merged on 2026-10-06 as tidewatch-web PR 2 (source: https://github.com/tidewatch-labs/tidewatch-web/pull/2).
- The build never started the owner's default `tidewatch` compose project, so nothing is confirmed running there.
- Review: service and migrations took two fix loops, bot two, web two, each approved in round 3.
- Merge: 2026-10-05T16:31:45Z at the owner's request (OWNER-9), pinned to reviewed heads in the order migrations `87ce578`, service `f9da2cd`, bot `fe17845`, web `f0d0a7f`. No CI checks exist (D4).

(source: raw/2026-10-05-foundation-auth.md §Test plan)

## Open items

- **FR-INFRA-008 (owner action).** `.forge/workspace.json` still has `"runCommand": "go run ."` for `tidewatch-service`. The entrypoint moved, so the owner changes it in Forge settings to `go run ./cmd/tidewatch-service`.
- **Forge tooling gap (A5).** A future run cannot resolve `{{project:tidewatch-migrations}}` for the preview `migrate` build (see [[forge-preview-gateway]] and [[centralized-migrations]]).
- **Bookkeeping drift.** The stage-key line in `verification.md` still says "none yet" for merged and running, contradicting its own status line, and `state.json` lists A6 as pending where `verification.md` records it validated. `verification.md` is authoritative.

(source: raw/2026-10-05-foundation-auth.md §Open questions)

Closed since the source was written:

- **FR-WEB-019 (closed 2026-10-06).** `tidewatch-web/DESIGN.md` merged into `main` as tidewatch-web PR 2 (commit `0b83213`, merge `4f8c4a2`). What it contains is on [[design-system-decisions]] (source: https://github.com/tidewatch-labs/tidewatch-web/pull/2).

## Out-of-date documents

Per D17 these were not edited; they are recorded for the owner:

- `documents/05-auth-and-access.md` §8 still describes the SSR server forwarding the session cookie (now never, D2) and the rail's user area (now the top-bar account menu, D7). Deferred by the owner.
- `documents/03-design-system.md` has breakpoints 1100/760 versus the shipped 1250/1080/820/600 (D13), body text 14px/1.45 versus the approved 13px/1.5, a light `--text-3` below AA (4.42:1), and no mention of the OWNER-4/6 light-theme changes.
- `documents/features/00-foundation-and-auth.md` mentions "CI: lint + unit tests", but CI is deferred (D4).
- The PRD's A4 wording is wrong: Angular SSR has no built-in allowed-hosts list.

(source: raw/2026-10-05-foundation-auth.md §Open questions)

## Known limits and follow-ups

Accepted limits (single-instance in-memory limits, empty `TRUSTED_PROXIES`, unbounded argon2 wait queue, throttle key cap, redaction over-masking, shared preview secrets file, unauthenticated internal endpoints, no session cleanup job) are listed on the concept pages where they apply: [[auth-model]], [[request-protection]], [[forge-preview-gateway]].

Follow-ups:
- web: client timeouts on login, logout and change-password (a hung sign-out leaves a live session behind a busy state); move `@angular-devkit/build-angular` to `devDependencies`; add `frame-ancestors` / `X-Frame-Options` to HTML responses.
- bot: pin the base image by digest and add a `packageManager` hash (deferred with CI).
- service: consolidate `config.parseOrigin` with `origin.Normalise`; pin base images by digest; bump `toolchain` with each patched Go release.
- Forge tooling: support `migrationsPath` as a workspace resource in the worktree, execution and preview helpers.
- Deferred by the owner: CI, production topology and TLS, the AES-GCM credential helper (and making `TIDEWATCH_KEY_ENCRYPTION_KEY` required with the first credential-storing slice), Redis-backed rate limits, and updating 05 §8, 03 §4 and the brief's CI line.
- When roles are added, revisit the scope of `requireRole("admin")` over `/auth/*`. **Settled by accounts and roles (2026-10-29):** the product group requires role `user`, and operators have their own `/admin` group (see [[accounts-and-roles]]).

(source: raw/2026-10-05-foundation-auth.md §Open questions)

Still open after slice 1: pin base images by digest (with CI, D4), merge `config.parseOrigin` with `origin.Normalise`, move `@angular-devkit/build-angular` to `devDependencies`, and decide a framing policy for HTML responses (source: raw/2026-10-07-market-data.md §Open questions, Follow-ups).

## Changed by later slices

Slice 1 ([[market-data]], merged 2026-10-07) superseded parts of this page. The slice-0 description above is kept as history.

- **Bot.** `tidewatch-bot` is no longer a connect-and-exit check. `serve` is a long-running worker with `/health`, `/ready` and `/metrics` on 9091 (see [[market-data-worker]]). In compose it is `restart: unless-stopped` with a `/ready` healthcheck, so the expected state is `tidewatch-bot` healthy, not `Exited (0)`; only `migrate` exits 0. The compose header now claims `up -d --build --wait` should work, which replaces the A10 advice above but is unconfirmed until a real start.
- **Overview.** The Overview route loads the Market watch card instead of `ScreenPlaceholder`; the other five screens keep their empty states.
- **Schema.** `RequiredSchemaVersion` moved from `20261004153023` to `20261006131346` (see [[centralized-migrations]]).
- **Preview.** The bot is now a preview service in `.forge/docker-compose.json` (see [[forge-preview-gateway]]).

(source: raw/2026-10-07-market-data.md §Components, Workspace root, tidewatch-web Route tree and tidewatch-bot; §Database, Required-schema-version contract)

Accounts and roles ([[accounts-and-roles]], merged and deployed to production on 2026-10-29) replaced the slice-0 account model:
- **The seeded `admin` is a plain user.** Migration L backfilled it to role `user`, `display_name = 'admin'`, `status = 'active'` and plan `founder`. It kept its id, password hash, bots, decisions, watchlist and settings, so the owner's product sign-in needed no action. "The owner signs in as a seeded `admin`" (above) now means signing in as that backfilled person.
- **No user is bootstrapped any more (D2).** The bootstrap creates the first **operator** from `TIDEWATCH_OPERATOR_*` when `operators` is empty. `TIDEWATCH_ADMIN_USERNAME` and `TIDEWATCH_ADMIN_PASSWORD` are retired: read, ignored and warned about once.
- **People are created only by an operator,** in the [[operator-console]]. Public sign-up stays absent in every phase (D19).
- **The service CLI** gained `operator create`, `operator set-password` and `user set-password`, the renamed `admin set-password`, which is kept as a deprecated alias for one release.
- **The product gate chain** reads `RequireRole("user")`, and `RoleAdmin` was deleted (see [[auth-model]]).
- **Schema.** `RequiredSchemaVersion` is L, `20261028120000` (see [[centralized-migrations]]).

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D2; §Database, Backfill; §API, CLI and Configuration)

## Related pages

- [[auth-model]] — sessions, passwords, throttling, forced change, audit events
- [[request-protection]] — CSRF, exact-origin CORS and the D1 guardrails
- [[centralized-migrations]] — schema, goose tooling and the required-schema-version contract
- [[forge-preview-gateway]] — the Caddy preview gateway (D16)
- [[design-system-decisions]] — Aurora tokens, D6/D7/D13 and OWNER-4/5/6
- [[market-data]] — Slice 1, built on this foundation
- [[accounts-and-roles]] — the operator/user split that retired the seeded-admin model
- [[operator-console]] — the operator bootstrap, CLI and `/admin` console
