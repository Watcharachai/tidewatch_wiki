# Auth model

**Summary**: How Tidewatch authenticates the people who use the product: opaque cookie sessions stored hashed, argon2id passwords with a common-password list, an atomic in-memory login throttle with lockout, a server-enforced forced password change, and append-only audit events. Since slice 6 (bots, merged 2026-10-21, not deployed), the gated market group carries **59** gated routes, every new bot route is owner-scoped with an indistinguishable 404, and the new bot audit events carry no name, config, thesis or key. Since statistics (slice 7, merged and deployed 2026-10-27), the group carries **64** gated routes; the five Stats routes are owner-scoped with the same indistinguishable 404, and CSRF covers the post-mortem PUT and the promote POST. **Since accounts and roles (merged and deployed 2026-10-29), there are two principals.** The product's sessions, throttle and forced change on this page now serve **users with role `user`**. Product sign-in did not change, and the product gate chain reads `RequireRole("user")`, because `RoleAdmin` was deleted. **Operators** are a separate kind, with their own tables, the `tw_admin` cookie, the `/admin/*` routes and a password-then-SMS-code sign-in (see [[operator-console]]). The seeded `admin` row is now a plain user, and `TIDEWATCH_ADMIN_*` is retired (see [[accounts-and-roles]]). Since the learning loop (merged and deployed 2026-10-30), the product group carries **70** gated routes; the six learning routes are owner-scoped with the same indistinguishable 404, and the audit list has a 35th type, `learning_draft_dismissed` (see [[learning-loop]]).

**Sources**: `raw/2026-10-05-foundation-auth.md`; `raw/2026-10-07-market-data.md`; `raw/2026-10-12-signals-page.md` (signals and settings scoping only); `raw/2026-10-16-charting.md` (the chart routes' gating and the owner-scoped stance only); `raw/2026-10-21-bots.md` (the bot routes' gating, scoping and audit events only); `raw/2026-10-27-statistics.md` (the Stats routes' gating, scoping and audit events only); `raw/2026-10-29-accounts-roles.md` (the two principals, role `user`, the bootstrap, the CLI and the audit list); `raw/2026-10-30-learning-loop.md` (the learning routes' gating, scoping and audit events only)

**Last updated**: 2026-10-31

---

## Scope

There is no sign-up, in any phase (D19 of accounts and roles). **Since accounts and roles (2026-10-29), product accounts are people with role `user`. Only an operator creates one, through `POST /admin/users` in the [[operator-console]]. A new person starts `invited`, with a temporary password and `must_change_password=true`.** Operators are a second principal with their own tables, cookie and routes, and their own sign-in with an SMS code. This page describes the product (user) side, which the operator kind reuses: one auth package parameterised by principal kind, with two repositories, two cookies and two throttle keyspaces (source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built). *History:* until migration L, the only account was the seeded `admin`, created by bootstrap with `must_change_password=true`. L backfilled that row to a plain `user` (see [[accounts-and-roles]]). The auth authority is `documents/05-auth-and-access.md` as adjusted by D1, D2, D7, D11 and D16; its section 8 is out of date (see [[foundation-auth]]). Cross-origin guardrails (CSRF, CORS) are on [[request-protection]], and the tables are on [[centralized-migrations]] (source: raw/2026-10-05-foundation-auth.md §Concept, §Components).

## Sessions and cookie

- The token is 32 bytes from `crypto/rand`, base64url in the cookie. Only its SHA-256 is stored in `sessions.token_hash`.
- Cookie: `tw_session=<token>; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax`, plus `Secure` unless `ENVIRONMENT=local`. There is no `Domain` (host-only), and no code path can set `SameSite=None`.
- Lifetime is 30 days absolute and 7 days idle, rolling: `expires_at = least(last_seen_at + 7d, created_at + 30d)`. `last_seen_at` is touched when at least 60 s old. A session is valid only when `revoked_at IS NULL` and `now() < expires_at`.
- Several sessions per user are allowed. `logout` revokes the current one, `logout-all` revokes all (current included), a password change revokes the **other** sessions and keeps the current one, and the CLI reset revokes all.
- Sessions persist until expiry; there is no cleanup job in slice 0.

(source: raw/2026-10-05-foundation-auth.md §API, Security model; §Open questions, Known limits)

## Passwords

- argon2id with 64 MiB memory, 3 iterations, parallelism 1, a 16-byte salt and a 32-byte key, PHC-encoded, constant-time verification. A successful login rehashes a weaker hash. Stored hashes above 256 MiB, 16 iterations or parallelism 16 are rejected as malformed.
- One shared hasher allows at most 4 concurrent operations (about 256 MiB); the rest wait, and hashing always happens before a DB transaction opens. The wait queue is unbounded because bounding it needs a load-shedding error the PRD does not define.
- Policy: at least 12 code points, at most 1024 bytes, not in the embedded common list (case-insensitive), and on `/auth/password` not equal to the current password. No composition rules, and passwords are never trimmed. Usernames are trimmed and lowercased.
- The common list is SecLists `xato-net-10-million-passwords-1000000.txt` at commit `56da8d99` (MIT), filtered to entries of 12 or more code points: 46,146 entries (about 675 KB), embedded with `SOURCE.md` and `LICENSE` (assumption A8).
- Login performs exactly one argon2id verification, against the user's hash or a fixed dummy hash for unknown and locked users, so the three failure modes look identical.

(source: raw/2026-10-05-foundation-auth.md §API, Security model; §Concept, A8; §Open questions)

## Login order

CSRF, then IP limit (checked and recorded), then parse the 8 KiB body, normalise the username, username limit, lockout state, exactly one argon2id verification, outcome. This differs from the PRD, which lists rate limits before normalisation, because the per-username limit needs the normalised name (plan decision 6) (source: raw/2026-10-05-foundation-auth.md §Concept, Other recorded decisions).

## Throttle, lockout and the atomic reserve/refund

Implemented in `internal/auth/throttle`, in process memory (D12).

- **Limits.** 5 login attempts per rolling minute per client IP, and 10 per rolling 15 minutes per normalised username (every login attempt counts). On `/auth/password`, only a wrong current password counts toward the shared username limit and lockout. A refused attempt returns `429` with `Retry-After`, verifies nothing and writes no event.
- **Lockout.** 20 consecutive failures within an hour lock the username for 15 minutes. While locked, even the correct password gets the identical `401` (and `/auth/password` answers `422 current_password_incorrect`). A success after expiry, or a verified `current_password`, resets the count.
- **Atomic reserve/refund.** `Guard.BeginLogin` and `Guard.BeginPasswordChange` check the limit, count the attempt and mark it pending in one step, then exactly one verification and exactly one settle (`Fail`, `Succeed` or `Abandon`). A login attempt always stays counted. A password-change attempt is refunded on success, on abandon, and when a verified current password is paired with a new password the policy rejects, so a user in the forced change cannot lock themselves out with weak choices. Pending attempts count toward the lock, so only `max(1, 20 - failures)` in-flight attempts verify for real.
- **Why it exists.** A round-2 security review found a check-now/record-later race: 200 parallel guesses all passed a limit of 10. The fix replaced it, and round 3 verified that 200 parallel `BeginPasswordChange` calls let exactly 10 through.
- **Client IP.** The TCP peer, unless the peer is in `TRUSTED_PROXIES`, in which case the rightmost untrusted `X-Forwarded-For` entry. IPv4 is keyed per address, IPv6 per /64, IPv4-mapped IPv6 as IPv4.
- **Memory cap, fail closed.** Each tracker holds at most 100,000 keys; at the cap a new key gets `429` with a `Retry-After` of 1 to 900 s, and live counters are never evicted.
- **Known limits.** Single instance only; state is cleared on restart, and the CLI reset does not clear a running server's lockout. `TRUSTED_PROXIES` is empty in the compose and preview definitions, so clients behind a proxy, gateway or compose bridge share one IP and the per-IP limit can act globally. About 19 failures followed by a double-submitted correct password can produce a counted `401` and lock (accepted).

(source: raw/2026-10-05-foundation-auth.md §API, Security model; §Open questions, Known limits)

## Forced password change (D11)

While `must_change_password` is true, every authenticated route outside a fixed allowlist returns `403 password_change_required`. The allowlist is `GET /auth/me`, `POST /auth/password`, `POST /auth/logout` and `POST /auth/logout-all`. The gate fails closed, so new routes are gated by default. On the web side, `authGuard` sends a forced user to `/account/password?next=<target>`, and the interceptor does the same (without `next`) on a `403 password_change_required` (source: raw/2026-10-05-foundation-auth.md §Concept, D11; §Components, Data and auth layer).

## Endpoints

| Method and path | Auth | Notes |
|---|---|---|
| `POST /auth/login` | none + CSRF | `204` and `Set-Cookie`; `401 invalid_credentials`, `429 rate_limited`, `503 not_ready` |
| `POST /auth/logout`, `/auth/logout-all` | session + CSRF | `204` with a clearing cookie |
| `GET /auth/me` | session | user (`id`, `username`, `display_name` since accounts and roles, `role`, `must_change_password`) and session `expires_at` |
| `POST /auth/password` | session + CSRF | `204`; `422` codes `current_password_incorrect`, `password_too_short`, `password_too_long`, `password_too_common`, `password_unchanged` |
| any `/auth/register` | none | `404 not_found` for every method; no route, alias or redirect. Since accounts and roles, `/sign-up` and `/admin/register` answer the same, `OPTIONS` included (`TestRouter_NoSignup`) |
| `GET /health`, `/ready`, `/info` | none | `/health` is always 200; `/ready` reports database, schema, extensions, bootstrap |

Errors use the envelope `{"error","code","requestID"}` and the web app maps by `code`, never by message. Bodies are snake_case JSON. `/auth/*` is `503 not_ready` until ready, and `requireRole("admin")` wraps the whole authenticated group (trivially satisfied in slice 0) (source: raw/2026-10-05-foundation-auth.md §API). **Since accounts and roles that role is `user`**, and the slice-0 follow-up to revisit it once roles exist is settled. See "Accounts and roles" below.

## Market routes and `/ws` (slice 1)

- **Same gates on every market route.** `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`. New routes were gated by default: `TestRouter_ForcedChangeGatesNewRoutes` counts 19 gated routes (16 production routes and 3 test-only probes), and the allowlist still has its four slice-0 entries (source: raw/2026-10-07-market-data.md §API, REST; §Components, tidewatch-service).
- **`/ws` checks before the upgrade.** Session (`401 unauthenticated`), then `admin` (`403 forbidden`; role `user` since accounts and roles), then no forced change pending (`403 password_change_required`), after readiness and the exact Origin check (source: raw/2026-10-07-market-data.md §API, WebSocket).
- **Non-touching re-check on open sockets.** Every 60 s one batched session re-check runs. It never touches the session, so an open socket alone does not extend the 7-day idle timeout. It closes with **4401** when the session ended (sign-out, sign-out everywhere, the CLI reset) and **4403** when a forced change is pending or the role is no longer `admin` (since accounts and roles: no longer `user`, and a disabled person's sockets close **4401**); two failed re-checks in a row close with 1011. The batched check required changes to `internal/services/auth/{session,service}.go` and `internal/repository/postgres/session.go` (source: raw/2026-10-07-market-data.md §API, Lifecycle and close codes; §Files touched).
- **Web side.** 4401 and 4403 are terminal for the socket client: it reloads once so the interceptor can redirect, and recovers only after a successful REST reload (MW-2, MW-26) (source: raw/2026-10-07-market-data.md §Components, tidewatch-web Data layer and Recovery notes).
- **No audit events for watchlist edits** (source: raw/2026-10-07-market-data.md §API, Watchlist).

Details of the socket are on [[realtime-websocket]].

## Signals and settings scoping (slice 4)

- **Same gates.** The signals page's eight new routes mount on the same gated market group (`NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("admin") → RequirePasswordChanged`). `TestRouter_ForcedChangeGatesNewRoutes` now counts 43 gated routes: 40 production routes and 3 test probes.
- **What is global and what is per user.** Signals and sources are global. Citing decisions (scoped by the bots' `owner_user_id`), the acted-on count, the recommendation and settings are scoped to the session user. No route takes a user id. See [[signals-read-api]] and [[user-settings]].
- **Settings belong to the user row.** `user_settings.user_id` references `users (id)` with `ON DELETE CASCADE`. Settings writes are not audited and never logged with their value.
- **Login throttle seen on the preview.** The acceptance agent's repeated sign-ins hit the login throttle (`429` at 02:56:55Z on 2026-10-12). There was no lockout and no wrong password (see [[forge-preview-gateway]]).

(source: raw/2026-10-12-signals-page.md §API, Service routes and Settings keys; §Database; §Concept, Plan resolutions, Service R16; §Test plan, Preview operational notes; §Cross-cutting links)

## Chart routes (slice 5)

- **Same gates.** `GET /instruments/{id}/chart` and `GET /instruments/{id}/signals` mount on the same gated market group through `mountChart`. They are GETs, so no CSRF header is needed. `TestRouter_ForcedChangeGatesNewRoutes` now counts **45** gated routes: 42 production routes and 3 test probes.
- **The stance is scoped to the session user.** The chart's `stance` read filters bots by `owner_user_id = $1` and takes the user's oldest `auto`/`zone_transitions` bot, so another user's bot or watch rows are never read. The route never creates a bot, account or watchlist. `TestChart_Stance_ScopedAndNoCreate` checks both, and security review r1 approved it (FR-CH-SVC-006).
- **Global data.** Bars, indicators, Elliott counts and instrument signals are not per user.
- **Security LOW (web, open).** The route id is shown as written in the Chart's `h1` fallback, its unknown-instrument sentence and the wrapper `aria-label`. The suggested fix is a shape check and a 64-character cap, like `signal-prefill.ts`. The risk is text spoofing only.

Details are on [[chart-read-api]] (source: raw/2026-10-16-charting.md §API, Conventions; §Database, The stance read; §Test plan, Acceptance status FR-CH-SVC-006; §Open questions, Web follow-ups).

## Bot routes (slice 6)

- **Same gates.** The 14 new routes mount on the gated market group (`NoStore → ReadyGate → BodyLimit → RequireSession → RequireRole("admin") → RequirePasswordChanged`). CSRF is engine-wide on POST and PUT (`TestCSRF_BotMutations`). `POST /bots` and `POST /bots/{bot_id}/versions` take a 64 KiB body limit; every other route keeps 8 KiB.
- **Gated count.** `TestRouter_ForcedChangeGatesNewRoutes` now counts **59** gated routes: 45 + 14, of which 56 are production and 3 test probes. The build prompt's "+13" was a count slip (ORCH-5d).
- **Owner scope.** Every repository query is scoped by `owner_user_id`. A foreign or absent bot is one indistinguishable `404 not_found` on all 11 `:bot_id` routes (`TestBots_NewRoutes_ScopeAndNotFound`, `bot_scope_test.go`). `GET /recommendation` and `GET /model-tiers` create no bot or account; a followed bot that is not the user's own falls back to the champion rule.
- **Audit events.** `bot_created`, `bot_cloned`, `bot_version_created`, `bot_run_requested` and `recommendation_declined`; `bot_status_changed` gains `observing`. None carries a name, config, thesis or key (`TestAudit_BotEvents`, `TestLogs_NoBotTextOrConfig`). The two FU-1 refusals (`bot_limit_reached`, `run_rate_limited`) write nothing and fire no audit event.
- **Security notes.** Bot names accept Unicode format characters (owner-only visibility). Trade's *Follows* writes only the champion or one of the answer's options (web security L2), and the candidate pre-fill applies its context only when the link matches the loaded candidate (web security L1).

Details are on [[bot-versions-and-runs]] and [[signal-cited-orders]] (source: raw/2026-10-21-bots.md §API, Conventions, Codes, audit, metrics and logs; §Concept, The FU-1 spend caps; §Components, Trade; §Open questions, Service security notes).

## Stats routes (slice 7)

- **Same gates.** The five Stats routes (`GET /stats`, `/stats/losses`, `/stats/compare`, `PUT /decisions/{decision_id}/post-mortem`, `POST /bots/{bot_id}/promote`) mount on the gated market group with an 8 KiB body limit. CSRF is engine-wide on the PUT and the POST (`TestCSRF_PostMortem`, `TestCSRF_BotMutations`).
- **Gated count.** `TestRouter_ForcedChangeGatesNewRoutes` counts **64**: 61 production routes and 3 test probes (59 → 64).
- **Owner scope.** A bot, version or decision that is unknown or another user's is one indistinguishable `404 not_found`, never 403 (`TestStats_ScopeAndNotFound`). The post-mortem PUT checks its body before ownership, so a bad body on a foreign decision is `400`. No Stats route creates a bot; promote is the one `/bots/{bot_id}` route without `EnsureBots`.
- **Audit events.** `bot_promoted {bot_id, version, previous_champion}` and `post_mortem_labelled {decision_id, label}`, typed constructors only. Logs carry ids and enums only; `TestLogs_NoBotTextOrConfig` checks that a sentinel bot name and rationale never reach the log.

Details are on [[stats-read-api]] (source: raw/2026-10-27-statistics.md §API, Conventions, `PUT /decisions/{decision_id}/post-mortem` and Codes, audit, metrics and logs; §Test plan, Named acceptance tests).

## Accounts and roles: role `user`, and a second principal (2026-10-29)

Accounts and roles (tidewatch-service #18, merge `35177e1`, merged and deployed to production on 2026-10-29) split the operator from the user. The model is on [[accounts-and-roles]], and the operator side on [[operator-console]].

- **The product gate chain is now** `NoStore → ReadyGate → BodyLimit → RequireSession → RequireRole("user") → RequirePasswordChanged`, over the 64 gated product routes and `GET /ws`.
  - Every earlier section on this page, and every route page, that reads `RequireRole("admin")` reads `RequireRole("user")` from migration L on.
  - `RoleAdmin` was deleted, and `grep -rn RoleAdmin internal test cmd pkg` is empty, so nothing accepts `admin` any more.
  - `users.role` still has no CHECK; the service enforces `user`.
- **Two principals, one auth package.** `session.Principal` carries a `Kind`, and `KindNone` fails closed. There are two repositories, two cookies (`tw_session` for users, unchanged; `tw_admin` for operators) and two throttle keyspaces.
  - A cookie of the other kind is simply absent to a gate: `401 unauthenticated`, with no `Set-Cookie` for the other cookie.
  - A refusal clears only its own kind's cookie.
  - Neither cookie ever has `Domain` or `SameSite=None`.
- **The person lifecycle at sign-in.**
  - The first successful product sign-in of an `invited` person flips the status to `active` and writes `user_activated` (`TestLogin_InvitedBecomesActive`).
  - A disabled person's login gets the same `401 invalid_credentials` as a wrong password, and writes `login_failed {reason: "disabled"}` (`TestLogin_DisabledUserIndistinguishable`).
  - Disabling a person revokes every session, so REST answers `401` and the hub's re-check closes sockets with `4401` (see [[realtime-websocket]]).
  - An operator's reset sets a temporary password and the forced change, and revokes every session.
- **The hub re-check** closes `4403` on a role other than `user` (it was "not `admin`"), and `4401` on a session that is gone, revoked or whose user is disabled (`TestHub_RecheckUserRole`).
- **Logging.** `http_request` carries `operator_id` for an authenticated operator, as it carries `user_id` for a user.

(source: raw/2026-10-29-accounts-roles.md §API, Gates and route groups; §Concept, The model, as built; §API, People, Writes; §Test plan, Named acceptance tests; §Database, Notes on the schema)

## Learning routes (slice 8, 2026-10-30)

- **Same gates, role `user`.** The six new routes (the learning status, runs list, run detail, report download, draft dismiss and the extraction-error export) mount on the gated market group `NoStore → ReadyGate → BodyLimit(8 KiB) → RequireSession → RequireRole("user") → RequirePasswordChanged` (`internal/app/router.go:518-523`). PRD §6.1's `RequireRole("admin")` is superseded by L. The dismiss POST needs CSRF.
- **Gated count.** `TestRouter_ForcedChangeGatesNewRoutes` counts **70** (64 → 70).
- **Owner scope.** An id that is not a UUID, is absent, or is another user's is one `404 not_found`, never 403 (`TestLearning_ScopeAndNotFound`). The export's foreign `bot_id` is the same 404.
- **The report download** is a plain `<a download>` on the same origin, so the session cookie applies (A5, verified on the real service).
- **Audit and logs.** `learning_draft_dismissed {bot_id, learning_run_id}` is the 35th closed type (`TestAudit_LearningEvents`). Logs carry ids and enums only, never a rationale, report line, document body or config (`TestLogs_NoBotTextOrConfig`, with sentinels).

Details are on [[learning-loop]] and [[bot-versions-and-runs]] (source: raw/2026-10-30-learning-loop.md §API, Conventions, Routes and Codes, audit, metrics and logs; §Concept, Spec corrections, Gate chain; §Components, *Download report*; §Test plan, Named acceptance tests and Results, A5).

## Bootstrap and CLI reset

**As built since accounts and roles (2026-10-29).**
- **The bootstrap creates an operator, never a user (D2).** When `operators` is empty, it creates the first operator from `TIDEWATCH_OPERATOR_USERNAME` (default `owner`), `TIDEWATCH_OPERATOR_PASSWORD` and `TIDEWATCH_OPERATOR_PHONE`, with `must_change_password=true`, and writes `operator_bootstrapped`.
  - Without the password while `operators` is empty, the service exits 1, naming the variable.
  - Once operators exist, the bootstrap skips and ignores the password with a warning.
- **`TIDEWATCH_ADMIN_USERNAME` and `TIDEWATCH_ADMIN_PASSWORD` are retired.** They are read, ignored and warned about once. No user is ever bootstrapped again.
- **The CLI.**
  - `user set-password --username <name>` is the former `admin set-password`, which stays as a deprecated alias for one release (it prints a deprecation line and keeps the `TIDEWATCH_ADMIN_PASSWORD` fallback).
  - `operator create` and `operator set-password` manage operators.
  - Details are on [[operator-console]].

(source: raw/2026-10-29-accounts-roles.md §Concept, Owner decisions D2; §API, CLI and Configuration)

**History (slice 0).** Bootstrap ran once under `pg_advisory_xact_lock`:
- with no users and a valid `TIDEWATCH_ADMIN_PASSWORD`, it created the admin with `must_change_password=true`;
- with no users and no password, it exited 1;
- when users existed, it skipped, and warned if the password variable was still set.

The CLI `admin set-password --username <name>` reads the first stdin line, falling back to the env variable only when stdin is empty or a terminal. It rehashes, sets `must_change_password`, revokes all sessions and writes events, and it never creates users. The stdin rule and the reset effects carry over to `user set-password`. See [[foundation-auth]] for the reset command (source: raw/2026-10-05-foundation-auth.md §Components).

## Audit events

The `events` table is append-only (database triggers reject UPDATE, DELETE and TRUNCATE; see [[centralized-migrations]]). Rows are built only through typed constructors in `internal/audit`.

| Type | Written when |
|---|---|
| `user_bootstrapped` | Bootstrap creates the admin |
| `login_succeeded` | Login succeeds |
| `login_failed` | A verification fails; `detail.reason` (`unknown_user`, `wrong_password`, `locked`, `invalid_stored_hash`, `password_changed`) is server-side only |
| `password_changed` | `POST /auth/password` succeeds |
| `password_reset` | CLI reset |
| `session_revoked` | logout, logout-all or CLI reset, with a reason and count |

A wrong `current_password` and a rate-limited login write no event. CLI events carry NULL `ip`, `user_agent` and `request_id`. `credential_added`, `bot_version_created`, `order_placed` and `kill_switch` are reserved for later slices (source: raw/2026-10-05-foundation-auth.md §API, Audit events).

**Since accounts and roles (2026-10-29)**, `audit.Types()` is a closed list of **34 types**: 17 existing and 17 new operator and person types. Since the learning loop (2026-10-30) it has 35, with `learning_draft_dismissed` (see "Learning routes" above).
- **Actor columns.** `events.actor_operator_id` (migration L) sits beside `actor_user_id`, and the two are never both set (D14, S22).
- **Failed sign-ins.** `login_failed` gained the reason `disabled`. Its `unknown_user` form keeps the raw typed username in `detail`; keeping or omitting it is open owner decision AUDIT-RAW-USERNAME.
- **No personal data in details.** No detail carries a password, hash, code, token, email, phone or display name (`TestAudit_NoSecrets`).

The full list, the new detail shapes and the `GET /admin/audit` reader are on [[operator-console]] (source: raw/2026-10-29-accounts-roles.md §API, Audit; §Concept, Owner decisions D14).

## Logging and redaction

- **Service.** zerolog JSON; redaction is an always-on writer (`logging.RedactWriter`) rather than a hook, because a hook cannot remove fields already added. It masks sensitive keys at any depth, configured secrets by value (8 bytes or more), URL userinfo, `password=` pairs, DSNs echoed by pgx and argon2 PHC hashes. Both `http.Server.ErrorLog`s and the CLI's stdout and stderr go through it. The request logger reads no body or header except the user agent.
- **Bot.** pino with exact-key redaction and connection-string masking.
- **Migrate.** `dsn-guard.sh` validates the DSN and masks output.
- **Web.** The SSR server never logs cookies.
- **Limits.** The service writer over-masks up to the last `@` on a line, an ordinary-word DSN password of 8 bytes or more is masked everywhere, and output through the stdlib default `log` logger bypasses it. The bot redactor is not a general secret scanner.

(source: raw/2026-10-05-foundation-auth.md §API, Logging and redaction; §Open questions, Known limits)

## Related pages

- [[foundation-auth]] — the slice that built this model
- [[request-protection]] — CSRF, CORS and web-side protections that front these routes
- [[centralized-migrations]] — `users`, `sessions`, `events` tables and the append-only trigger
- [[realtime-websocket]] — the `/ws` session re-check and its 4401/4403 closes
- [[market-data]] — the market routes behind the same gates
- [[user-settings]] — per-user settings keyed by the user row
- [[signals-read-api]] — the signals routes and what they scope to the session user
- [[chart-read-api]] — the chart route, the 45 gated routes and the owner-scoped stance read
- [[bots]] — slice 6, with 14 more gated, owner-scoped routes (59 in all)
- [[bot-versions-and-runs]] — the bot routes, their scope and audit events
- [[stats-read-api]] — slice 7's five gated, owner-scoped routes (64 in all) and their audit events
- [[accounts-and-roles]] — the operator/user split, people, plans and role `user` (2026-10-29)
- [[learning-loop]] — slice 8's six gated, owner-scoped routes (70 in all) and the 35th audit type
- [[operator-console]] — the operator principal: password then SMS code, `tw_admin`, the CLI and the audit reader
