# Operator console (`/admin`)

**Summary**: Since accounts and roles (merged and deployed 2026-10-29), Tidewatch has an operator console. It is a lazy `/admin` route tree in tidewatch-web, on the same origin as the product (D8). tidewatch-service backs it with three sign-in routes and 16 gated `/admin` routes. An operator signs in in two steps. The password only answers a challenge, and only a correct Twilio Verify SMS code sets the `tw_admin` cookie (D10). The console has four screens. **People** lists, creates and edits people, resets their passwords, and disables or enables their sign-in. **Operators** is owner only: list, disable and enable. **Audit** reads a closed list of 34 event types. **Spend** shows the ceiling, today's ingest and bot spend, and each person's allowance. Operators are created only by the service CLI. The first operator is bootstrapped from `TIDEWATCH_OPERATOR_*` when `operators` is empty. In production the bootstrap created operator `owner` on 2026-10-29. No operator has signed in there yet, so the Twilio sender has never run against the live API. The account model the console administers is on [[accounts-and-roles]]. **Since the learning loop (merged and deployed 2026-10-30),** Audit's closed list has **35** types, with `learning_draft_dismissed` added, and Spend counts a learning run's `post_mortem` labelling calls as the owner's bot spend (see [[learning-loop]]).

**Sources**: `raw/2026-10-29-accounts-roles.md`; `raw/2026-10-31-fix-dialog-reopen-race.md` (the People dialogs' close behaviour only); `raw/2026-10-30-learning-loop.md` (the 35th audit type and labelling spend on Spend only)

**Last updated**: 2026-10-31

---

## Where it lives

- **Same origin (D8).** `/admin/*` is served from the product's origin, and `admin.tidewatchtrade.com` is reserved for later. In production the console is `https://tidewatchtrade.com/admin/sign-in`, and its title reads "Sign in · Console · Tidewatch".
- **Web.** All console code is in `tidewatch-web/src/app/pages/admin/`. This lazy route tree has its own shell, store, guards and API service. The product's `AuthService`, `authGuard`, `guestGuard` and `/sign-in` sources are byte-identical to the base.
- **Service.** `/admin` is its own route group with its own gates, described below. The product group is untouched apart from its role gate, which now requires `user` (see [[auth-model]]).

(source: raw/2026-10-29-accounts-roles.md §Concept, Owner decisions D8; §Components; §Concept, Rollout to production)

## Sign-in: a password, then an SMS code

### Routes (`/admin/auth/*`)

| Route | Auth | Request | Success | Errors |
|---|---|---|---|---|
| `POST /admin/auth/login` | none + CSRF | `{username ≤ 64 B, password ≤ 1024 B}` | `200 {challenge_id, phone_hint, expires_at, resend_after}`, **no cookie** | `400`, `401 invalid_credentials`, `403 csrf_rejected`, `429` (+`Retry-After`; `600` on Twilio's send limit), `503 not_ready`, `503 otp_unavailable` |
| `POST /admin/auth/login/verify` | none + CSRF | `{challenge_id, code ≤ 16 B}` | `204` + `Set-Cookie: tw_admin=…` | `400`, `401 otp_invalid`, `403`, `429`, `503 otp_unavailable` |
| `POST /admin/auth/login/resend` | none + CSRF | `{challenge_id}` | `204` | `400`, `401 otp_invalid`, `403`, `429` (+`Retry-After`), `503 otp_unavailable` |
| `POST /admin/auth/logout`, `/logout-all` | operator + CSRF | — | `204`, clearing `tw_admin` | `401`, `403` |
| `GET /admin/auth/me` | operator | — | `200 {operator: {id, username, role, must_change_password}, session: {expires_at}}` | `401` |
| `POST /admin/auth/password` | operator + CSRF | `{current_password, new_password}` | `204`; the operator's other sessions are revoked | `401`, `422` (the product's five password codes), `429` |

(source: raw/2026-10-29-accounts-roles.md §API, Operator auth)

### The password step

- **Order:**
  1. CSRF.
  2. The operator login IP window: 5 per rolling minute, IPv4 per address and IPv6 per /64.
  3. Parse, then normalise.
  4. The username limit: 10 per 15 minutes.
  5. The lockout: 20 consecutive failures, wrong passwords and wrong codes counted together, lock the username for 15 minutes.
  6. **Exactly one argon2id verification**, against the operator's hash, or against the dummy hash for an unknown, disabled or locked operator.
  7. The outcome.
- **A right password does not reset the lockout run.** Only the verify step's right code calls `Attempt.Succeed`.
- **Failures look the same.** A wrong password and an unknown, disabled or locked operator all get the same `401 invalid_credentials`, "Wrong username or password.". The answers are identical apart from `requestID`.
- **`phone_hint`** shows the country code and the last four digits, with bullets for the rest (`+66 •• ••• 1234`). Nothing else about the phone leaves the service through sign-in.

(source: raw/2026-10-29-accounts-roles.md §API, The login step)

### The challenge store (`internal/auth/challenge`, S1)

- **Where it lives.** In process memory, with a 10-minute life. A challenge is bound to the operator, never to the client IP (S10).
- **Five checks per challenge.** They are reserved atomically before the sender is asked. Under 200 parallel verifies, at most 5 reached the sender.
- **Only a right code consumes a challenge.** A failure only marks it used up, so a double-submitted right code still opens its session (F1).
- **Resend.** A resend is allowed 30 s after the last send, and at most 3 sends per operator in 10 minutes. Every send counts. The `Retry-After` is the wait until **both** rules allow it, which is stricter than contracts r3's "earlier of the two".
- **Capacity.** At most 100,000 challenges. At the cap a new challenge is refused and nothing is evicted. The store is swept every minute, and a restart drops the challenges in flight.
- **Dead challenges.** A dead, consumed, unknown or wrong challenge gets the one `401 otp_invalid`, "That code isn't right.". A dead one waits a fixed delay, so it answers in the same timing envelope as a wrong code.
- **IP windows.** Login, verify and resend each have their own window of 5 a minute.

(source: raw/2026-10-29-accounts-roles.md §API, The challenge store; §Concept, Spec corrections, Resend `Retry-After`)

### The code sender (`internal/auth/otp`, port `Send` / `Check`)

- **`twilio`** (the default) is Twilio Verify v2 over `net/http`, with no SDK.
  - **Calls.** `POST https://verify.twilio.com/v2/Services/{TWILIO_VERIFY_SERVICE_SID}/Verifications` (`To`, `Channel=sms`), and `/VerificationCheck` (`To`, `Code`).
  - **Auth (SC-TWILIO-AUTH).** HTTP basic auth `TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN`, with a 10 s timeout per call. There are **no API-key variables**. `TWILIO_API_KEY_SID` and `TWILIO_API_KEY_SECRET` from the PRD are gone. The owner decided this on 2026-10-29, matching how sakuship-service signs in to Verify v2.
  - **Send errors.** The mapping is total. `60203` (max send attempts) → `send_limited`, `429` + `Retry-After: 600`. Any other 4xx, 5xx, timeout or transport failure → `503 otp_unavailable`.
  - **Check errors.** `60202`, `20404` or a bare `404` → a dead challenge. `60200` with `400` → a wrong code. Anything the sender cannot decide → `503 otp_unavailable`, never a pass.
  - **Live status.** It has run only against fixtures transcribed from Twilio's docs (`internal/auth/otp/testdata/twilio/`). Two of them, `send_ok` and `check_20003`, are assumptions. **It has never run against the live API.**
- **`dev`** sends nothing.
  - It accepts only `TIDEWATCH_OTP_DEV_CODE`, exactly 6 digits, compared in constant time.
  - `Validate` refuses it at start unless `ENVIRONMENT=local`, and `app.newOTPSender` refuses it again (F8).
  - The preview and the e2e use it.
- **Logs.** No part of a Twilio request or answer, no phone and no code reaches a log or an error text.

(source: raw/2026-10-29-accounts-roles.md §API, The code sender; §Concept, Spec corrections, SC-TWILIO-AUTH)

### The forced change (S9) and the session

- **The forced change.** Operators created by the bootstrap or the CLI start with `must_change_password = true`. Until they change it, every gated `/admin/*` route answers `403 password_change_required`. The exceptions are `GET /admin/auth/me`, `POST /admin/auth/password`, `/logout` and `/logout-all`.
- **Cookie `tw_admin`.**
  - **Attributes:** `Path=/; Max-Age=604800; HttpOnly; SameSite=Lax`, plus `Secure` unless `ENVIRONMENT=local`. It never has `Domain` or `SameSite=None`.
  - **Lifetime.** 7 d absolute and 12 h idle (`expires_at = least(last_seen_at + 12h, created_at + 7d)`, D12). The session is touched when `last_seen_at` is 60 s old.
  - **Storage.** Only the SHA-256 of the 32-byte token is stored, in `operator_sessions.token_hash`.
- **Cross-principal.** A refusal clears only its own kind's cookie. To a product gate, `tw_admin` is simply absent, and to the console, `tw_session` is (see [[accounts-and-roles]]).
- **Not built.** TOTP is the recorded next hardening.

(source: raw/2026-10-29-accounts-roles.md §API, The forced change; §API, Gates and route groups, Cookies; §Concept, The model, as built)

### The sign-in screen (`/admin/sign-in`)

- **Rendering.** It is prerendered, a full-page glass panel with the caption *Operator console*. The form sits in a disabled `<fieldset>` until hydration, and a capture-phase submit guard runs, as on the product's `/sign-in` (see [[request-protection]]).
- **Step 1, *Sign in*.** *Username*, *Password* and *Continue*, which reads *Checking…* while busy. There are no links, no theme switch and no sign-up.
- **Step 2, *Enter your code*.**
  - The text "We sent a code to {phone_hint}.".
  - A *Code* field (`inputmode="numeric"`, `autocomplete="one-time-code"`).
  - *Sign in*, which reads *Signing in…* while busy.
  - *Resend code*, which reads *Resend in {n} s* and is `aria-disabled` until `resend_after`.
  - *Use a different account*.
- **Messages.** The PRD's copy, verbatim. A 10-minute expiry returns the operator to step 1. Focus moves to the new `h1` on each step change.

(source: raw/2026-10-29-accounts-roles.md §Components, Routes and Screens)

## Gates and the `/admin` route group

- **The group:** `NoStore → ReadyGate → BodyLimit(8 KiB)`.
  - The three sign-in routes sit outside the session gates, but CSRF still applies.
  - Every other route goes through `RequireOperatorSession → RequireOperatorRole(owner, staff) → RequireOperatorPasswordChanged`.
  - `/admin/operators/*` adds `RequireOperatorRole(owner)`.
- **Route count.** The route walk counts **16 gated `/admin` routes**: 4 auth, 7 people, 3 operators, audit and spend. `TestRouter_OperatorForcedChangeGatesNewRoutes` checks all 16.
- **Conventions (contracts r3).**
  - **Errors.** The error envelope is `{"error","code","requestID"}` plus optional `details`.
  - **Formats.** Money is a decimal string with exactly 6 fraction digits. Instants are RFC 3339 UTC, dates are Bangkok `YYYY-MM-DD`, and absent values are `null`.
  - **No caching.** Every `/admin/*` answer carries `Cache-Control: no-store`, refusals and unknown paths included.
  - **Strict bodies (S8).** A body is at most 8 KiB and must be one JSON object. An unknown key is `400 invalid_request {reason: "unknown_field"}`, and the key is never named.
  - **Strict queries.** An unknown parameter is `invalid`, a repeated one `duplicate`, and an out-of-range `limit` `out_of_range`.
  - **CSRF.** Every `POST`, `PATCH` and `DELETE`, `/admin/auth/login*` included, needs `X-Tidewatch-Request: 1` and the exact app `Origin`.
  - **Rate limits.** `429 rate_limited` always carries an integer `Retry-After`.
- **New codes.**
  - `otp_invalid` (401) and `otp_unavailable` (503);
  - `username_taken`, `email_taken`, `phone_taken`, `status_conflict` (with `details: {status}`) and `last_owner` (409);
  - the `invalid_request` reasons `self` and `not_entitled`.

  `forbidden` (403) gets its first real use, on `/admin/operators/*`.
- **Logging.** `http_request` carries `operator_id` for an authenticated operator, as it carries `user_id` for a user.

(source: raw/2026-10-29-accounts-roles.md §API, Conventions; Gates and route groups; Error codes)

## People (`/admin/users`, owner and staff)

`Person` is:

```
{id, username, display_name, email, phone, status, role,
 plan: {id, name},
 must_change_password, created_at,
 created_by: {operator_id, username} | null,
 last_login_at, disabled_at, sessions_active,
 bots: {active, total},
 spend: {today_usd, last_7d_usd, allowance_usd, reached}}
```

- **`bots.active`** counts `kind = 'auto'` bots in `running | observing`. `total` counts every bot, `me` included.
- **`spend` (S4).**
  - `today_usd` is Σ `model_calls.cost_usd` for the person over the Bangkok day.
  - `last_7d_usd` is the same over the 7 Bangkok days ending today.
  - `allowance_usd` is `plans.daily_model_usd`.
  - `reached` is `today_usd ≥ allowance_usd` (SC-E2E004, below under Spend).
- **`created_by`** is `null` for the backfilled row.

| Route | Request | Success | Errors |
|---|---|---|---|
| `GET /admin/users` | `q`, `status`, `limit` (1–100, default 50), `cursor` | `200 {items: [Person], next_cursor, totals: {people, active}}` | `400` |
| `POST /admin/users` | `{username, display_name, email, phone}` | `201 {user: Person, temporary_password}` | `400 {field, reason}`, `409 username_taken \| email_taken \| phone_taken` |
| `GET /admin/users/{user_id}` | — | `200 Person` | `404` |
| `PATCH /admin/users/{user_id}` | any of `display_name`, `email`, `phone` | `200 Person` | `400` (`username` or `plan_id` is `unknown_field`), `404`, `409 email_taken \| phone_taken` |
| `POST /admin/users/{user_id}/reset-password` | no body | `200 {user: Person, temporary_password}` | `404`, `409 status_conflict {status: "disabled"}` |
| `POST /admin/users/{user_id}/disable`, `/enable` | no body | `200 Person` | `404`, `409 status_conflict` |

**Listing and fields.**
- **Order.** Newest first (`created_at DESC, id DESC`). The opaque cursor (kind byte `P`) is bound to `q` and `status`.
- **`q`** is 1–80 code points, case-insensitive. It matches a substring of `username` or `display_name`, a prefix of `email`, or a suffix of at least 3 digits of `phone`.
- **`totals`** count every row, and the `active` rows separately. They do not depend on the query, and they come from the same snapshot as the page (OQ-W1).
- **Field rules.**
  - `username`: trimmed and lowercased, `^[a-z0-9][a-z0-9._-]{2,63}$`.
  - `display_name`: 1–80 code points, no control characters.
  - `email`: lowercased, at most 254 bytes, one `@`, a dot in the domain, printable ASCII only. That narrows PRD §4.5.1.
  - `phone`: E.164.

**Writes.**
- **Create.** Stores `role user`, `status invited`, `must_change_password true`, `plan founder` and `created_by_operator_id`, and writes `user_created`. It creates no bot, account or watchlist (see [[accounts-and-roles]]).
- **Temporary password** (`internal/auth/password/temporary.go`).
  - **Shape.** Four words from the embedded BIP-39 English list (2,048 words, MIT), generated with `crypto/rand`. It matches `^[a-z]{3,8}(-[a-z]{3,8}){3}-[0-9]{2}$` and is 18–38 characters (OQ-2).
  - **Handling.** It is returned only in the create and reset answers. It is never stored, logged or audited in clear.
- **Reset.** Sets a new temporary password and the forced change, and revokes every session (`session_revoked {reason: password_reset, count}`, operator actor). It writes `user_password_reset {user_id, via: "console"}`.
- **Disable** is one locked transaction:
  1. the acting operator's row `FOR SHARE`, then the acting session's row `FOR SHARE`;
  2. `MeBotLockKey(user)`, the users row `FOR NO KEY UPDATE`, and the bot rows in ascending `bot_id`;
  3. `status = disabled` and `disabled_at`;
  4. every session revoked (`session_revoked {reason: user_disabled}`);
  5. each running or observing auto bot paused through the trading Pause path (`bot_status_changed {…, to: "paused", reason: "user_disabled"}`, operator actor);
  6. `user_disabled {user_id, bots_paused}`.
- **After a disable.** REST answers `401`. The hub's next 60 s re-check closes the person's sockets with `4401` (see [[realtime-websocket]]). A login gets `401 invalid_credentials` (`login_failed {reason: "disabled"}`). A create, clone, resume or `EnsureBots` already waiting on the lock gets `401 unauthenticated`.
- **Enable.** Sets `active`, or `invited` when the person never signed in, and clears `disabled_at`. The bots stay paused. It writes `user_enabled`.
- **The actor is re-checked under lock (F5, G1–G3).** A write by an operator who is disabled, gone, or whose session was revoked or expired mid-request gets `401 unauthenticated`. Nothing is written, and no temporary password is returned.

**The People screen (`/admin`).**
- **Header.** The sub line reads *{n} people · {m} active*, beside *Add person*.
- **Filters.** A search box, *Find by name, username, email or phone* (300 ms), and a *Status* chip select.
- **Table** (`table.tide.people`, 860 px minimum). The columns:
  - *Person*: display name over username;
  - *Email*;
  - *Phone*: E.164, grouped for reading;
  - *Status*;
  - *Plan*;
  - *Last sign-in*: Bangkok time;
  - *Bots*: `{active} active · {total}`;
  - *Spend today*: `$x / allowance`, plus a neutral *At allowance* tag when `reached`;
  - *Actions*: *Edit*, *Reset password*, *Disable sign-in* or *Enable*.
- ***Add person*.** A country `<select>`, with Thailand +66 first and the default (S20), sits beside the national number.
  - On `201` the dialog shows the username and the temporary password once, with *Copy password*.
  - The password lives in one signal of the dialog and is discarded on close.
  - A 38-character password wraps only at its hyphens.
  - *Add person* and *Reset password* clear the secret and their busy flag on `(closed)`. Before tidewatch-web #25 (merged 2026-10-30; in production since the learning loop's web build `de00a5f` rolled out the same day), a stale native `close` event after a fast close-then-reopen could fire that reset inside the new opening. The shared `Dialog` now emits exactly one `closed` per opening, and the fix's security review found no retained temporary password. See [[design-system-decisions]] (source: raw/2026-10-31-fix-dialog-reopen-race.md §Concept, Root cause; §Test plan, Recorded results).
- ***Edit*** sends only the changed fields. The username is read-only.
- ***Reset password*** confirms, then shows the new temporary password. A `409` reads *Enable sign-in first.*
- ***Disable sign-in*** confirms, then shows the toast "{name} can't sign in. {n} bots paused.".

(source: raw/2026-10-29-accounts-roles.md §API, People; §Components, Screens and People dialogs; §Concept, Spec corrections)

## Operators (`/admin/operators`, owner only)

`Operator` is `{id, username, role, must_change_password, created_at, last_login_at, disabled_at, sessions_active}`. The phone is never returned.

| Route | Success | Errors |
|---|---|---|
| `GET /admin/operators` | `200 {items: [Operator]}`, `created_at ASC, id ASC`, no paging | `403 forbidden` for staff |
| `POST /admin/operators/{operator_id}/disable` | `200 Operator`; that operator's sessions are revoked | `400 invalid_request {reason: "self"}`, `403`, `404`, `409 status_conflict`, `409 last_owner` |
| `POST /admin/operators/{operator_id}/enable` | `200 Operator` | `403`, `404`, `409 status_conflict` |

- **Refusal order:** `403` → `404` → `self` → `status_conflict` → `last_owner`. The service decides these under row locks, so two owners cannot disable each other at the same time (`TestOperators_ConcurrentOwnerDisable`).
- **No create route.** An operator is added with the CLI.
- **Screen.** The columns are *Operator*, *Role*, *Last sign-in*, *Status* and *Actions*. *Disable* has a confirm dialog. The toasts read "You can't disable yourself." and "The last owner can't be disabled.". A note reads "Add an operator with the service's operator create command."
- **Staff.** The rail hides the Operators link. A typed URL shows *Owner only* after the service's `403`.

(source: raw/2026-10-29-accounts-roles.md §API, Operators; §Components, Screens)

## Audit (`/admin/audit`, owner and staff)

`GET /admin/audit?type=&actor=&limit=&cursor=` → `200 {items: [Event], next_cursor}`, newest first, 50 per page (1–100). The cursor's kind byte is `A`, and it is bound to `type` and `actor`.

- **Event shape.** `Event` is `{id, occurred_at, type, actor, ip, request_id, detail}`. `actor` is `{kind: "user" | "operator", id, username}`, or `{kind: "system", id: null, username: null}`.
- **Filters.** `actor=` matches a username of either kind.
- **No personal data in details.** No detail ever carries a password, hash, code, token, email, phone or display name. Details are built only by the typed constructors in `internal/audit`, and `TestAudit_NoSecrets` builds every one of them.
- **The two actor columns.** `events.actor_operator_id` sits beside `actor_user_id`, and the two are never both set (D14, S22).
- **The closed list of 34 types** (`audit.Types()`; 35 since the learning loop added `learning_draft_dismissed`, see "Audit and Spend since the learning loop" below). A `type=` outside it is `400 {field: "type", reason: "invalid"}`.
  - **Existing (17):** `user_bootstrapped`, `login_succeeded`, `login_failed`, `password_changed`, `password_reset`, `session_revoked`, `order_placed`, `order_cancelled`, `decision_skipped`, `bot_status_changed`, `bot_created`, `bot_cloned`, `bot_version_created`, `bot_run_requested`, `recommendation_declined`, `bot_promoted`, `post_mortem_labelled`.
  - **New (17):** `operator_bootstrapped`, `operator_created`, `operator_login_succeeded`, `operator_login_failed`, `operator_otp_sent`, `operator_otp_failed`, `operator_password_changed`, `operator_password_reset`, `operator_session_revoked`, `operator_disabled`, `operator_enabled`, `user_created`, `user_updated`, `user_password_reset`, `user_disabled`, `user_enabled`, `user_activated`.
  - `login_failed` gained the reason `disabled`.

| New type | Actor | `detail` |
|---|---|---|
| `operator_bootstrapped` | none | `{operator_id, username}` |
| `operator_created` | none (CLI) | `{operator_id, username, role, via: "cli"}` |
| `operator_login_succeeded` | operator | `{}` |
| `operator_login_failed` | none, always (F3) | `{username, reason: unknown_operator \| wrong_password \| locked \| disabled \| invalid_stored_hash}` |
| `operator_otp_sent` | operator | `{channel: "sms", sends}` |
| `operator_otp_failed` | operator or none | `{reason: wrong \| dead \| send_failed \| send_limited}` |
| `operator_password_changed` / `operator_password_reset` | operator / none | `{}` / `{via: "cli"}` |
| `operator_session_revoked` | operator | `{reason: logout \| logout_all \| password_reset \| operator_disabled, count}` |
| `operator_disabled`, `operator_enabled` | operator | `{operator_id}` |
| `user_created` | operator | `{user_id, username, plan_id}` |
| `user_updated` | operator | `{user_id, fields: [names only]}` |
| `user_password_reset` | operator | `{user_id, via: "console"}` |
| `user_disabled` / `user_enabled` | operator | `{user_id, bots_paused}` / `{user_id}` |
| `user_activated` | user | `{}` |

- **Failed sign-ins store the raw typed username.** `operator_login_failed` with `unknown_operator`, and the product's `login_failed` with `unknown_user`, keep the typed username in `detail`, and `/admin/audit` shows it as stored. Whether to keep or omit it is open owner decision AUDIT-RAW-USERNAME.
- **Rollout rule (web README).** The web's Audit page reads `type` from the same closed list (`AUDIT_TYPES`) and shows "Events couldn't load." on any other type. So a new audit type must reach the web before, or in the same release as, the service that writes it.
- **Screen.**
  - **Filters.** A *Type* chip select over the 34 types, and an *Actor username* search.
  - **Columns.** *When* (Bangkok time, to the second), *Type*, *Actor* (with the kind under it), *IP* and *Detail* (key: value pairs).
  - *Load more*.

(source: raw/2026-10-29-accounts-roles.md §API, Audit; §Concept, Owner decisions D14; §Components, Screens; §Open questions, Open owner decisions)

## Spend (`/admin/spend`, owner and staff)

`GET /admin/spend?day=` → `200 {day_bkk, ceiling_usd, ingest_usd, bots_usd, people: [{user_id, username, display_name, allowance_usd, today_usd, last_7d_usd, reached}]}`.

- **`day`** is optional (`YYYY-MM-DD`, default today in Bangkok). A future day, or one before 2026-01-01, is `out_of_range`. The console shows today only.
- **The two totals.** `ingest_usd` is the `model_calls` rows with `user_id IS NULL`, and `bots_usd` is the rest. Their sum equals `model_spend_daily` for the day, which an integration test checks (see [[model-routes-and-spend]]).
- **`ceiling_usd`** is `MODEL_SPEND_DAILY_CEILING_USD`, rendered once at start to 6 digits (OQ-1). If the variable is unset, the service uses 1.00, which must match the bot's value.
- **`people`** lists every `users` row, disabled ones included, ordered `today_usd DESC, username ASC`.
- ***At allowance* means actual spend has reached the allowance (SC-E2E004, as built over the PRD).** `reached` is `today_usd ≥ allowance_usd`. The bot can stop a person earlier, on spend **plus the next survivor's estimate**, so a person the bot has already stopped can show no tag. On the preview, an allowance of 0.0001 with an actual spend of 0.000032 showed no tag. At 0.000032 the tag rendered. The owner kept both rules (D-E2E004).
- **Two figures that agree up to known edges.** Stats' cost of decisions reads `bot_runs.counts.cost_usd` (statistics D10), while Spend reads `model_calls`. They agree except for a crashed wake and estimates (see [[statistics]]).
- **Screen.** Three metric cards come first: *Ceiling*, *Ingest today* and *Bots today*. Then *People*, with the columns *Person*, *Allowance*, *Today*, *7 days* and *Status* (*At allowance* or a dash). Dollars show two decimals, or four under a cent, so $0.000032 reads $0.0000.

(source: raw/2026-10-29-accounts-roles.md §API, Spend; §Concept, Spec corrections, SC-E2E004; §Components, Screens)

## Audit and Spend since the learning loop (2026-10-30)

The learning loop (service #16 and web #21, merged and deployed to production on 2026-10-30; see [[learning-loop]]) touched two console screens without changing their routes.

- **A 35th audit type.** `learning_draft_dismissed {bot_id, learning_run_id}` is written by the product's *Dismiss draft* (`POST /bots/{bot_id}/learning/draft/dismiss`), with the person as actor. The service's `audit.Types()` gained it, and the web's closed `AUDIT_TYPES` list (34) gained it as the 35th (`src/app/pages/admin/data/admin.model.ts:184`, branch-update commit `f2ee96c`). It shows raw in the *Type* filter, like the other 34.
- **The rollout rule was applied.** Because the web's Audit reader refuses an unknown type, the web went out straight after the service (migrations → service → bot → web), so no older web met the new type.
- **Other audit details changed, not new types.** `bot_version_created` gains `learned_from_run` and `draft_modified` on a draft save, `post_mortem_labelled` always carries `confirmed_proposal`, and `bot_run_requested` can carry `{loop: learn}`.
- **Seen on the preview (PV6).** One `learning_draft_dismissed` event with `actor_user_id` was returned by `GET /admin/audit?type=learning_draft_dismissed` and shown on `/admin/audit` in both themes.
- **Spend counts labelling as the owner's (OD-LEARN-SPEND).** A learning run's `post_mortem` `model_calls` rows carry the bot's `bot_id` and the owner's `user_id`, so Spend counts them in `bots_usd` and in the person's `today_usd`, not in `ingest_usd`. Before the fix (found in the branch-update review) they were unattributed and would have shown as ingest. Pre-fix rows keep NULL attribution: 12 on the preview database, none in production. `GET /admin/spend` answered 200 on PV6.
- ***At allowance* includes labelling.** The tag still reads `today_usd ≥ allowance_usd`, and `today_usd` now includes the person's labelling calls. The bot's own allowance check sums scout and learn runs (`OWNER_COST_FOR_DAY`). The learning report's budget line shows the bot share only (see [[model-routes-and-spend]]).

(source: raw/2026-10-30-learning-loop.md §Concept, Branch update onto L; §Concept, Decisions during the build OD-LEARN-SPEND; §Concept, Rollout to production, Why this order; §API, Codes, audit, metrics and logs; §Components, Data layer; §Test plan, Preview runs; §Open questions, Recorded residuals)

## The CLI (`tidewatch-service`, same binary)

| Command | Behaviour |
|---|---|
| `operator create --username <u> --role owner\|staff --phone <E.164>` | Reads the password from the first stdin line, else from `TIDEWATCH_OPERATOR_PASSWORD`, and validates it against the policy. Inserts the operator with `must_change_password = true` and writes `operator_created {via: "cli"}`. Prints `operator created: <username> (<role>)`. A taken username or phone exits 1 |
| `operator set-password --username <u>` | The auth package's one reset path for the operator kind (`auth.NewOperatorReset`). Rehashes, sets the forced change and revokes every operator session. Writes `operator_password_reset {via: "cli"}` and `operator_session_revoked` |
| `user set-password --username <u>` | The former `admin set-password`. `admin set-password` stays as a deprecated alias for one release: it prints a deprecation line and keeps the `TIDEWATCH_ADMIN_PASSWORD` fallback |

- **Exit codes.** A flag value that fails its rule exits 2, naming the flag but never the value. No argument is ever echoed.
- **Known gap (follow-up).** A `staff` operator created with the CLI on an empty `operators` table stops the owner bootstrap.

(source: raw/2026-10-29-accounts-roles.md §API, CLI)

## Configuration and the environment bootstrap

Variable names only. The values live in `.env` and Vault and are never recorded here.

| Variable | Rule |
|---|---|
| `TIDEWATCH_OPERATOR_USERNAME` | Default `owner`; `^[a-z0-9][a-z0-9._-]{2,63}$` |
| `TIDEWATCH_OPERATOR_PASSWORD` | Tier-1 secret, masked by value. Required while `operators` is empty: without it the service exits 1, naming the variable. Ignored with a warning once operators exist |
| `TIDEWATCH_OPERATOR_PHONE` | E.164. Required with the password |
| `TIDEWATCH_OTP_SENDER` | `twilio` (default) or `dev`. `dev` is allowed only with `ENVIRONMENT=local` |
| `TIDEWATCH_OTP_DEV_CODE` | Exactly 6 digits. Required with `dev` and forbidden with `twilio` |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID` | Required with `twilio`. The account SID and auth token are the basic-auth pair (SC-TWILIO-AUTH). `TWILIO_AUTH_TOKEN` is Tier-1 and masked by value |
| `MODEL_SPEND_DAILY_CEILING_USD` | An owner-approved new service variable (OQ-1). Optional, default 1.00, parsed like the bot parses it. It must carry the bot's value |
| `TIDEWATCH_ADMIN_USERNAME`, `TIDEWATCH_ADMIN_PASSWORD` | **Retired.** Read, ignored, with one warning. The username lost its `admin` default so that "set" is detectable |

- **The bootstrap (D2).** When `operators` is empty, the service creates the first operator from `TIDEWATCH_OPERATOR_*`. That operator has `must_change_password = true` and writes `operator_bootstrapped` with no actor. The service logs `bootstrap: created operator`, or `bootstrap: skipped, operators exist` once operators exist. No user is ever bootstrapped again. In production this ran at 2026-10-29 07:25:32Z and created operator `owner`.
- **Redaction.** The redaction writer masks `TWILIO_AUTH_TOKEN` and `TIDEWATCH_OPERATOR_PASSWORD` by value, and the keys `code`, `tw_admin` and every `*password*` key at any depth.
- **The bot and the web.** The bot gains no variable, and the web gains no runtime variable. The web e2e uses `BASE_URL`, `E2E_OPERATOR_USERNAME` (default `owner`), `E2E_OPERATOR_PASSWORD` and `E2E_OTP_DEV_CODE`. `E2E_ADMIN_*` and `e2e/.auth/credentials.json` are retired.
- **Production Vault.** Before the rollout, the owner force-synced ExternalSecret `tidewatch-service-env`, which was checked by key name only. It held the five new names (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID`, `TIDEWATCH_OPERATOR_PASSWORD`, `TIDEWATCH_OPERATOR_PHONE`) beside `DATABASE_URL`, `TIDEWATCH_KEY_ENCRYPTION_KEY` and `TIDEWATCH_ADMIN_PASSWORD`.

(source: raw/2026-10-29-accounts-roles.md §API, Configuration; §Concept, Owner decisions D2; §Concept, Rollout to production)

## The owner's first sign-in, and what to do after it

The first production sign-in is the owner's action. It is also the first live Twilio Verify send.

1. Open `https://tidewatchtrade.com/admin/sign-in`.
2. Sign in as `owner` with the bootstrap password from Vault (`TIDEWATCH_OPERATOR_PASSWORD`).
3. Expect an SMS code at `TIDEWATCH_OPERATOR_PHONE`. Watch `tidewatch_otp_sends_total{result="send_failed"}` and the `otp_send` log line.
4. Enter the code. The console forces `/admin/account/password`, where the owner chooses a new password.
5. People should list the backfilled owner row: `admin`, *Active*, *Founder*, with no email or phone.
6. **Then delete `TIDEWATCH_OPERATOR_PASSWORD` and `TIDEWATCH_ADMIN_PASSWORD` from Vault** (`apps/tidewatch-service/prod`). While they stay set, the service ignores both and logs a warning for each at start.

**Related clean-up the source lists as open:**
- **The service chart** in tidewatch-kubernetes still sets `TIDEWATCH_ADMIN_USERNAME`, which only causes the retired-variable warning.
- **`scripts/seed-vault.sh`** still prompts for `TIDEWATCH_ADMIN_*` and asks for no operator or Twilio values.
- **The root files.** The owner-maintained root `.env.example` and compose need the new service lines with `dev`, and `TIDEWATCH_ADMIN_*` should be removed from the example.
- **Optional:** `MODEL_SPEND_DAILY_CEILING_USD` in the service chart and the root compose.
- **Phase B** also waits for the owner's own row to have an email and phone set in *Edit person* (see [[accounts-and-roles]]).

(source: raw/2026-10-29-accounts-roles.md §Test plan, Manual reproduction; §Open questions, Owner actions still open)

## Metrics and logs

- **Service metrics.** The labels are closed, and the series sit at 0 from startup:
  - `tidewatch_otp_sends_total{principal="operator", result=sent|send_failed|send_limited}`;
  - `tidewatch_otp_checks_total{principal="operator", result=ok|wrong|dead}`;
  - `tidewatch_operator_login_attempts_total{result=success|failure|rate_limited|otp_pending}`.

  `principal="user"` arrives with Phase B.
- **Service logs** carry ids, enums and counts only:
  - `bootstrap: created operator`, `bootstrap: skipped, operators exist`;
  - `person_created`, `person_reset`, `person_disabled {user_id, bots_paused}`, `person_enabled`;
  - `operator_login`, `otp_send` (operator id, verification SID, status), `otp_check_failed`, `operator_disabled`, `operator_enabled`.

  `TestLogs_NoPersonData` plants an email, a phone, a display name, passwords and codes, then scans the logs for them.
- **After deploy, watch** `tidewatch_operator_login_attempts_total`, `tidewatch_otp_sends_total{result="send_failed"}`, `bots_user_budget_reached_total` and `bots_tier_not_entitled_total`. Production logs keep about 5 h and are not in VictoriaLogs. Metrics are on vmsingle.

(source: raw/2026-10-29-accounts-roles.md §API, Metrics and logs)

## Web implementation

- **Routes (S18).**
  - `/admin/sign-in` is prerendered, behind `operatorGuestGuard`.
  - `/admin` (People), `/admin/operators`, `/admin/audit`, `/admin/spend` and `/admin/account/password` are client-rendered. The Operators route has no client role guard.
  - An unknown `/admin/**` path redirects to `/admin`.
  - Titles read `<Screen> · Console · Tidewatch`.
- **Guards.** `operatorGuard` (`canActivateChild`) sends three cases elsewhere:
  - a signed-out visitor goes to `/admin/sign-in?next=`;
  - a pending forced change goes to `/admin/account/password?next=`;
  - any other failure gets the full-page "Tidewatch isn't responding." state.

  `sanitizeAdminNext` keeps only targets under `/admin`, never `/admin/sign-in`, and otherwise falls back to `/admin`.
- **`OperatorAuthService`.** A root store that mirrors `AuthService`. It holds no password or code and touches no storage. The product imports it in exactly two files: `app.ts` and `auth.interceptor.ts`.
- **`AdminApi`.** It owns every `/admin` data call, and no component injects `HttpClient`.
  - Its strict readers refuse an unknown status, role, actor kind or audit type.
  - Money stays a 6-digit string, formatted digit by digit.
- **Interceptor branch (S12).** `auth.interceptor.ts` branches on the request's **API path**, never on the route.
  - A `401` on an `/admin` path clears only the operator store and goes to `/admin/sign-in?next=`. The three login routes are the exception.
  - A `403 password_change_required` goes to `/admin/account/password`.
  - A product `401` never touches the operator store.
- **Shell (S19).** The console reuses the product frame with a `console` host class.
  - The workspace card reads *Operator console* / *{role}*, and the rail label reads `CONSOLE`.
  - The nav is *People*, *Operators* (owner only), *Audit* and *Spend*.
  - The breadcrumb reads `Console / <Screen>`, and the account menu reads *Signed in as {username} · {role}*.
  - At ≤ 600 px the rail becomes a 4-column strip, or 3 columns for staff.
- **Styles and icons.** `console.css` and four icons; see [[design-system-decisions]].
- **e2e.**
  - **The operator helper** (`support/operator.ts`) holds a worker-scoped operator session. It signs in through the API with the dev code, keeps `tw_admin` in its own cookie jar, and uses Node `fetch`, never Playwright's request context (SEC-W-5).
  - **Projects.** Five mocked console specs run on the fail-closed `/admin/*` mock, and `operator-live` runs one test against the real service.
  - **People.** The journey and the product setup create their own people per run (`e2e-{run}-{n}`).
  - **Secret hygiene.** Secrets are typed only through `fillSecret`, `PLAYWRIGHT_NO_COPY_PROMPT=1` is required, and failure snapshots are stripped.

(source: raw/2026-10-29-accounts-roles.md §Components, Routes, Stores, Screens and e2e)

## Open items for the console

- **Service security L1.** Code sends with an unknown outcome are refunded. That lets a password holder bypass the 30 s wait and the 3-per-10-minutes limit. The fix is to refund only on a definite 4xx.
- **Service security L2.** The Twilio check should send `VerificationSid`, not `To`. This is not exploitable, because phones are unique.
- **Other service follow-ups:**
  - the race `401` (a write by an operator disabled or revoked mid-request) sends no clearing cookie;
  - `resend_after` is truncated, resends are not audited, and the README names an unused reason;
  - the reset, disable and enable POSTs ignore a body rather than refusing it;
  - the audit actor filter cannot use the actor indexes;
  - the `operator_id` log field is ambiguous between actor and target;
  - a CLI-created staff operator on an empty table blocks the owner bootstrap;
  - `admin.New` accepts nil dependencies, while `NewOperators` panics;
  - contracts r3 §7 and §11 still read "Source pending OQ-1".
- **Web follow-ups:**
  - move the Operators component's store to `feat-operators/data/operators.service.ts`;
  - sub-cent spend reads `$0.0000`, and `[0.00995, 0.01)` renders `$0.0100`;
  - there is no distinct line when the code is accepted but the follow-up `/admin/auth/me` fails;
  - a temporary password that arrives after the user has left the screen is lost;
  - promote the busy-button rule to `button.css`.
- **Open owner decisions:** VW3 (the Edit country select), AUDIT-RAW-USERNAME and COPY-SIGNOFF (see [[accounts-and-roles]]).

(source: raw/2026-10-29-accounts-roles.md §Open questions, Recorded follow-ups and Open owner decisions)

## Related pages

- [[accounts-and-roles]]: the feature overview, the account model, plans, the spec corrections and acceptance
- [[auth-model]]: the product sessions, argon2id, throttle and forced change the operator kind reuses
- [[request-protection]]: CSRF, CORS, `no-store` and the pre-hydration guard on `/admin`
- [[model-routes-and-spend]]: the ledger behind Spend, `model_calls.user_id` and the ceiling
- [[bots-engine]]: the bot-side allowance that Spend's *At allowance* tag trails
- [[realtime-websocket]]: the 4401 close a disable triggers
- [[centralized-migrations]]: migration L's `operators`, `operator_sessions` and `events.actor_operator_id`
- [[design-system-decisions]]: `console.css`, the four icons, the visual review and the shared `Dialog` close contract
- [[forge-preview-gateway]]: the preview that ran the console with the `dev` sender
- [[statistics]]: the other spend figure, cost of decisions from `bot_runs`
- [[learning-loop]]: the 35th audit type and the labelling spend Spend now attributes to the owner
