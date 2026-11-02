# Accounts and roles (`accounts-roles`, Phase A)

**Summary**: Before this feature Tidewatch had one account. The seeded `admin` row, bootstrapped from `TIDEWATCH_ADMIN_PASSWORD`, was both the only product user and the only administrator, and all 64 gated product routes and `/ws` sat behind `RequireRole("admin")`. Phase A separated the two. **Operators** are now their own principal, with their own tables (`operators`, `operator_sessions`), cookie (`tw_admin`), route group (`/admin/*`) and two roles, `owner` and `staff`. Every operator sign-in takes a password and then a Twilio Verify SMS code. Operators work in the [[operator-console]]. **People** are users with role `user`. Each has a display name, email, phone, status (`invited | active | disabled`) and plan. Only an operator can create a person, and the console shows the temporary password once. **Plans are data.** One `founder` row allows 10 active auto bots, $0.50 of model spend a day, all four decision tiers, no live trading and ฿1,000,000 of starting capital. It replaces the constants that the service and the bot used to hold. The bot holds each person to the plan's daily allowance, runs a tier the plan excludes as `none`, and stamps `bot_id` and `user_id` on every bot model call. **No phase has public sign-up (D19).** Phase B covers the setup link with phone proof, a user code step and email verification. It is specified and waits by design, and migration L already ships its columns. **Status (2026-10-29):** all four PRs are merged (migrations #16, service #18, bot #19, web #23) and deployed to production. 45 of the 51 acceptance IDs are verified, E2E-004 among them with deviation D-E2E004, which the owner kept as built. The other 6 IDs are Phase B, and none failed. The owner has not yet made the first operator sign-in in production. That sign-in will also be the first live Twilio Verify send. **Since the learning loop (merged and deployed 2026-10-30; see [[learning-loop]]),** migration M follows L as planned, the six learning routes sit behind the same `RequireRole("user")` gate, the closed audit list has a 35th type (`learning_draft_dismissed`), and the per-person daily allowance also counts a person's learning-run labelling spend (OD-LEARN-SPEND).

**Sources**: `raw/2026-10-29-accounts-roles.md`; `raw/2026-10-30-learning-loop.md` (the learning-loop section only); `raw/2026-10-30-signals-context.md` (the sibling update and merge order only)

**Last updated**: 2026-10-31

---

## Stage, stated precisely

| Stage | Status (2026-10-29) |
|---|---|
| Implemented | **Migrations:** S1–S3 (feat `b955a8c`, plan `0d1ada5`). **Service:** S1–S11 (feat `1eba43b`, plan `d4d5104`), then the owner-decided Twilio auth-token change `23d921f` and its review fixes `5c57438` (PR head). **Bot:** S1–S5 (feat `81e29b5`, plan `4e66579`). **Web:** S1–S11 (feat `5196393`, plan `0c99f26`). After the PR opened, the web added e2e fixes `03d065c`, visual fixes `10851db`, DESIGN.md corrections `a7498cd` and the CI fix `ce420a7` (PR head) |
| Reviewed | Plans and code in all four repositories. Plan-review fix loops: migrations 2, service 2, bot 1, web 2. Code-review fix loops: the same counts |
| Verified on a preview | **Yes.** A per-run isolated database at L, 2026-10-28 18:48Z–20:36Z, and E2E-004 on 2026-10-29 02:00–02:08Z. The preview used the `dev` code sender, so Twilio never ran |
| Merged | **Yes**, 2026-10-29, by Claude on the owner's instruction, in the order migrations → service and bot → web: migrations #16 → `080979d` (07:00:39Z), service #18 → `35177e1` (07:11:46Z), bot #19 → `bd5e435` (07:11:51Z), web #23 → `4725cb9` (07:26:18Z) |
| Deployed | **Yes, to production.** A merge to `main` is a production deploy (deploy-prod → GHCR → tidewatch-kubernetes GitOps bump → ArgoCD). L was applied at 07:25:10Z, and the service bootstrapped operator `owner` at 07:25:32Z. The new service rolled at 07:25:41Z, the bot at 07:19:12Z and the web at 07:33:38Z. `https://tidewatchtrade.com/admin/sign-in` answered 200 |
| First operator sign-in in production | **Not done.** It is the owner's action and the first live Twilio send |
| Documentation | The raw source and this wiki update. `documents/` is untouched (slice-0 D17). The owner is to amend 05 §1, §2 and §11 and research brief §7 when the user phase is built |

The source treats `state.json` as authoritative for merge and deploy, and `verification.md` for verified, failed and unverified. `verification.md`'s header still says "nothing is merged or deployed", because it was written before the merges (source: raw/2026-10-29-accounts-roles.md, summary block; Sources, Record notes; §Concept, Stage, stated precisely).

## Why the feature exists

At `main` on 2026-10-27:
- **One account.** `users(id, username, password_hash, role DEFAULT 'admin', must_change_password, created_at, last_login_at)` held one row, the seeded `admin`, created at first start from `TIDEWATCH_ADMIN_PASSWORD` (see [[foundation-auth]]).
- **Where `RequireRole("admin")` was read:** the router's gate chain, the bootstrap, and the websocket hub's 60-second re-check, which closed 4403 when the role was not `admin`.
- **The audit log** had nowhere to record an operator's action, because `events.actor_user_id` was a foreign key to `users`.
- **Ownership was already per user.** `bots.owner_user_id` was on every bot query, and `EnsureBots` created `me` and Slack Water (฿1,000,000 each) for any user id. Each account was limited to 10 active auto bots, and settings and watchlists were per user. Only account creation and the operator/user split were missing.
- **Model spend.** Ingest and every bot shared one $1.00 Bangkok-day ceiling, with a 25 % per-bot share. `model_calls` had no `bot_id` or `user_id`.
- **The owner's ask:** invite other people who "can use the product but cannot create accounts or perform admin actions", and later let people sign up and subscribe, so "admin and user should be separate".

(source: raw/2026-10-29-accounts-roles.md §Concept, Problem)

## The model, as built

### Two principals in two tables (D1)

| | Operator | User (a "person") |
|---|---|---|
| Tables | `operators`, `operator_sessions` | `users`, `sessions` |
| Cookie | `tw_admin`: 7 d absolute, 12 h idle | `tw_session`: 30 d absolute, 7 d idle (unchanged) |
| Routes | `/admin/*` only (16 gated routes plus the three sign-in steps) | The product: 64 gated routes and `GET /ws` |
| Roles | `owner`, `staff` | `user` |
| Sign-in | A password, then a Twilio Verify SMS code, on every sign-in. There is no trusted-device skip (D10) | A password at `/sign-in`, unchanged. Phase B adds a code step |
| Created by | The CLI `operator create` (D3). The first operator comes from the environment bootstrap (D2) | `POST /admin/users` (console *Add person*) only |

- **One auth package for both kinds.** It is parameterised by principal kind: `session.Principal` carries a `Kind`, and `KindNone` fails closed. There are two repositories, two cookies and two throttle keyspaces.
- **A cookie of the other kind does not exist for a gate.** The gate answers `401 unauthenticated` and sends no `Set-Cookie` for the other cookie. In E2E-002, the person's `tw_session` on `GET /admin/users` got 401. The operator's `tw_admin` got 401 on `GET /bots` and on the `/ws` upgrade, with no 101. Both cookies still worked afterwards.
- **Rejected:** one table with a `kind` column (D1).
- The sign-in steps, the challenge store, the code sender and the cookie are on [[operator-console]]. The product's sessions and throttle are on [[auth-model]].

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D1, D10; §API, Gates and route groups; §Test plan, What each E2E check showed, E2E-002)

### Operator roles (D3)

- `owner` and `staff` may both do everything under People, Audit and Spend.
- Only `owner` reaches `/admin/operators/*` (list, disable, enable). Staff get `403 forbidden`, the code's first real use.
- No route creates an operator. Operators come only from the CLI, so the console's Operators page is read-only apart from *Disable* and *Enable*.
- Nobody can disable themselves, and nobody can disable the last owner (`409 last_owner`).

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D3; §API, Operators; §API, Error codes)

### People

- **Fields.** Each person has a username, a display name (1–80 code points), an email and a phone. All four are required at creation. Email and phone are stored but not verified (D9). Email and phone are unique only when set; the service decides that under partial unique indexes, never by a pre-read, so two concurrent creates give one `201` and one `409`. Each person also has a status, a plan, the creating operator, `disabled_at` and `updated_at`.
- **Lifecycle (D13).** The statuses are `invited | active | disabled`. `pending_verification` and `suspended` are reserved. Nothing is ever deleted.
  - **Create.** A new person is `invited`, with `must_change_password = true`, plan `founder` and a temporary password shown once. Creating a person makes no bot, account or watchlist. `EnsureBots` makes those on the person's first product request, at the plan's starting capital. Every person gets `me` and a running, rules-only Slack Water (D7).
  - **First sign-in.** The first successful sign-in flips `invited → active` and writes `user_activated`.
  - **Disable sign-in.** This revokes every session and pauses the person's running and observing auto bots through the user's own Pause path. REST then answers `401`, the hub's next 60 s re-check closes the person's sockets with `4401`, and a login gets the same `401 invalid_credentials` as a wrong password.
  - **Enable.** Sign-in comes back as `active`, or as `invited` if the person never signed in. The bots stay paused.
  - **Reset password.** This sets a new temporary password and the forced change, and revokes every session. For a disabled person it is refused with `409 status_conflict`.
- **What operators see (D6).** Counts and spend only: no decisions, bot names or configs, and no impersonation.
- The routes, field rules and locking are on [[operator-console]].

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D7, D13; §API, People; §Database, Notes on the schema)

### The owner's workspace survived (D2, O2)

- **The backfill.** Migration L turned every pre-L `users` row into a plain `user`. Each row got `display_name = username`, `plan_id = 'founder'`, `status = 'active'` (the column default), and NULL email, phone, creator and `disabled_at`. It kept its id, password hash, sessions, bots, decisions, watchlist and settings. The owner's product sign-in needed no action.
- **E2E-005**, run on a copy of the retained preview database. The copy held two pre-L admin rows, `admin` and `pv4-stats`. The counts were identical before and after L: bots 5, decisions 32, watchlist items 8, settings 3, positions 14, orders 26, fills 26, paper accounts 5, bot versions 8, bot runs 281, candidates 4, sessions 42 and events 79. The md5 fingerprints were identical too. `POST /auth/login` as `admin` answered 204, and `/auth/me` read role `user`.
- **What the owner's row looks like now.** In People it reads `admin`, *Active*, *Founder*, with no email or phone, and `created_by` is `null`.
- **D2.** No user is ever bootstrapped again.

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D2; §Database, Backfill; §Test plan, Manual reproduction)

### Plans as data (D4, D5)

`plans` ships with one row:

| `plan_id` | `name` | `max_active_auto_bots` | `daily_model_usd` | `decision_tiers` | `live_trading` | `starting_capital_thb` |
|---|---|---|---|---|---|---|
| `founder` | Founder | 10 | 0.500000 | `none`, `jev`, `small_llm`, `large_llm` | false | 1000000 |

- `users.plan_id` is NOT NULL, with a foreign key to `plans`.
- **Who reads the plan.** On the service, `Entitlements` is the only reader of the bot cap, the tiers and the starting capital. The bot reads `daily_model_usd` and `decision_tiers` by join.
- **Changing a plan.** There is no plan write route and no *Change plan*. A second plan, or a changed founder value, is a data migration, never an edit of L (see [[centralized-migrations]]).
- **Product contract changes, all additive:**
  - **The active-bot cap.** `409 bot_limit_reached {limit}` on `POST /bots`, `/clone` and `/resume` now takes `limit` from the plan's `max_active_auto_bots`, counted under `MeBotLockKey`.
  - **Unentitled tiers.** `400 invalid_request {field: "config.decision_tier", reason: "not_entitled"}` answers `POST /bots`, `POST /bots/{id}/versions` and `POST /bots/{id}/clone` when the plan excludes the tier. A legacy v1 config counts as `none`.
  - **Starting capital.** `POST /bots` without `starting_capital` uses the plan's `starting_capital_thb`, and `EnsureBots` opens `me` and Slack Water at it. The literals 10 and 1,000,000 are gone from `internal/services/trading`.
  - **`GET /model-tiers`.** Each tier gains `entitled: boolean` as its last key.
  - **`GET /auth/me`.** `user` gains `display_name`.
- **On the web.** The Bots editor greys an unentitled tier with *Not in your plan*, and the account menu reads *Signed in as {display_name}* (see [[design-system-decisions]]).

Route-level detail is on [[bot-versions-and-runs]] (source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D4, D5; §Database, Migration L; §API, Product contract changes; §Components, Product-side changes).

### The bot-side daily allowance, tier entitlement and attribution (S15, S16)

- **The evaluated-bots read joins `users` and `plans`.** Each bot row carries `ownerUserId`, `dailyModelUsd` and `decisionTiers`. The bot never reads `users.status`. A wake keeps the row it started with, so a plan change takes effect at the next wake.
- **Per-person daily allowance (S16).** For each survivor, the bot checks three limits in order:
  1. the per-bot 25 % budget;
  2. `spent_user + estimate ≤ dailyModelUsd`, summed over all the person's bots for the Bangkok day;
  3. the global ceiling's reservation, checked at the calls.

  Once a survivor goes over the allowance, it and every later survivor of the wake take the template thesis, with no call and nothing reserved. Tier `none` is exempt. A missing allowance or a failed owner read fails the wake (fail closed).
- **Tier entitlement (S15).** A stored tier that is not in `decisionTiers` runs the whole wake as `none`. The version and its hash do not change.
- **Attribution.** The bot stamps `bot_id` and `user_id` on every bot model call. Signals-stage rows and every row written before L read NULL in both, so the owner's bot spend before the rollout is not attributed.
- **What it does not fix.** Reserving the bots' share of the ceiling away from ingest is still a separate open fix, an intent non-goal. Two people at $0.50 a day can still starve ingest.

Details are on [[bots-engine]] and [[model-routes-and-spend]] (source: raw/2026-10-29-accounts-roles.md §API, Bot: allowance, tier entitlement, attribution; §Database, Notes on the schema; §Open questions, Outside the build).

### No public sign-up, in any phase (D19, D17)

- `/auth/register`, `/sign-up` and `/admin/register` answer `404` for every method, `OPTIONS` included.
- `TestRouter_NoSignup` allows `POST /admin/users` as the only route that creates a user.
- The product's `/sign-in` page has no links. A zero-anchor assertion in `sign-in.spec.ts` checks this.
- **D17** changes the founding rule from "no public sign-up, ever" to "invite-only until the subscription feature". **D19:** no build may add public sign-up until the subscription feature's own spec reopens it. `documents/` is not edited.

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D17, D19; §Components, Product-side changes)

### Phase B: pending by design (D11, D18; `FR-AR-B-001…006`)

- **What it covers:**
  - `POST /admin/users/{id}/setup-link`;
  - a prerendered `/set-password` page with phone proof;
  - a user code step on `/sign-in`;
  - refusing a user who has no phone;
  - email verification;
  - later, `/sign-up` with subscriptions, in their own spec.
- **Its data already ships in L, with no writer:** `password_setup_tokens` (token hashes only), email, phone, status and plan. The `principal="user"` metric labels arrive with Phase B.
- **What it waits on.** The owner's go, and the owner's own row having email and phone set in *Edit person*.

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built; §Database, Notes on the schema; §API, Metrics and logs; §Open questions, Outside the build)

## Owner decisions from the intent (selected)

The full D1–D19 are in `tidewatch-specs/accounts-roles/intent.md` (confirmed 2026-10-27).
- **D1** Two principals in two tables. One table with a `kind` column was rejected.
- **D2** The operator is bootstrapped from new variables. `TIDEWATCH_ADMIN_*` is retired: it is read, ignored and warned about. No user is ever bootstrapped again.
- **D3** Roles `owner` and `staff`. Operators are created by the CLI.
- **D4, D5** `plans` ships with one row. The allowance is enforced bot-side per user, beside the 25 % per-bot budget and under the shared ceiling.
- **D7** `EnsureBots` is unchanged: every person gets `me` and a running, rules-only Slack Water at the plan's starting capital.
- **D8** `/admin/*` is on the same origin. `admin.tidewatchtrade.com` is reserved for later.
- **D10** Every operator sign-in needs a Twilio Verify SMS code. `TIDEWATCH_OTP_SENDER` is `twilio` or `dev`, and `dev` is allowed only when `ENVIRONMENT=local`.
- **D13** The lifecycle is `invited | active | disabled`. `pending_verification` and `suspended` are reserved, and there is no delete.
- **D14** `events.actor_operator_id` sits beside `actor_user_id`. The two are never both set (S22).
- **D16** One timestamp-named migration. The sibling builds learning-loop and signals-context also each expected the letter after K. The pin order was settled at build time: **L (this) → M (learning-loop) → N (signals-context)**.
- **D17, D19** As above.

(source: raw/2026-10-29-accounts-roles.md §Concept, Owner decisions from the intent)

## Decisions during the build (selected)

| Id | When / by | Decision |
|---|---|---|
| PD-1 | 2026-10-27, parent | J was the pin until L. K was never pinned, so the service pin moved J → L |
| ORCH-3 | 2026-10-27, orchestrator | FR-AR-E2E-003 keeps the PRD's 60 s bound |
| OQ-1 (a) | 2026-10-28, owner | The service reads `MODEL_SPEND_DAILY_CEILING_USD` for Spend's `ceiling_usd`. This owner-approved new service variable is an exception to PRD §8's list |
| OQ-2 | 2026-10-28, owner | Temporary passwords keep the BIP-39 English list and are 18–38 characters |
| B3 (A) | 2026-10-28, under owner delegation | The service's error-code log field is named `error_code`, so it no longer collides with the masked `code` key |
| PB-1..3 | same | The bots package writes `bot_id` and `user_id`, and `packages/signals/src` is untouched. The held reservations are summed over the person's bots. `bots_tier_not_entitled_total` is labelled with the three model tiers only |
| OQ-W1 (a) | same | Contracts r3 added `totals {people, active}` to `GET /admin/users` |
| OQ-W2..W4 | same | Web copy that the PRD did not give was accepted as planned, pending owner sign-off |
| PREVIEW-DB | same | The preview used a per-run isolated, retained database, because L, M and N carry fixed goose versions from unmerged branches (see [[forge-preview-gateway]]) |
| SPEC-2 (Down A) | 2026-10-28, under owner delegation | L's Down restores `role = 'admin'` only on active people |
| PREVIEW-E2E004 | 2026-10-29, owner | E2E-004 ran on a dedicated plan, `e2e004`, never on `founder`. It spent $0.000032 of Jev credit |
| D-E2E004 | 2026-10-29T03:17Z, owner | "Keep as built"; see SC-E2E004 below |
| OWNER-TWILIO-AUTH-TOKEN | 2026-10-29T04:04Z, owner | Twilio Verify basic auth is `TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN`; see SC-TWILIO-AUTH below |

(source: raw/2026-10-29-accounts-roles.md §Concept, Decisions during the build)

## Spec corrections: the as-built truth over the PRD

The build did not edit the spec repository. Where this list disagrees with `prd.md` or `intent.md`, this list is the truth.

- **SC-E2E004 (from D-E2E004): Spend's *At allowance* tag means actual spend has reached the allowance.**
  - `Person.spend.reached` and `GET /admin/spend` `people[].reached` are `today_usd ≥ allowance_usd`. Here `today_usd` is the person's actual attributed spend for the Bangkok day.
  - The bot stops a person earlier, as soon as spend **plus the next survivor's estimate** would pass the allowance (S16). So the bot can already have stopped a person who shows no tag.
  - PRD FR-AR-E2E-004 says that "with the allowance set to `0.0001` … *Spend* shows them *At allowance*". That did not hold as written. At 0.0001 the person's actual spend was 0.000032, so `reached` was false and no tag showed. With the allowance at 0.000032, `reached` was true and the tag rendered.
  - The owner kept both rules as built. There was no code change.
- **SC-TWILIO-AUTH (from OWNER-TWILIO-AUTH-TOKEN): Twilio Verify uses HTTP basic auth `TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN`.**
  - `TWILIO_API_KEY_SID` and `TWILIO_API_KEY_SECRET` are gone. No hit remains in the merged service tree.
  - This supersedes three spec texts: PRD §4.4 ("HTTP basic auth `TWILIO_API_KEY_SID:TWILIO_API_KEY_SECRET` … the account SID is sent as the `AccountSid` of the key"), the PRD §8 environment table, and the intent's owner Vault list.
  - The owner decided it on 2026-10-29. The owner holds an account SID, an auth token and a Verify service SID, with no API key, and sakuship-service signs in to Verify v2 the same way.
  - `TWILIO_AUTH_TOKEN` is a Tier-1 secret. The redaction writer masks it by value, and `json:"-"` in `internal/config/config.go` keeps it out of formatted output. The sender stays on `net/http`, with no twilio-go SDK.
  - It shipped in service commits `23d921f` and `5c57438`, with `make ci` exit 0 and integration `ok` 503.044s (0 FAIL, 0 SKIP). Code review APPROVED it 0/0/3. Security review APPROVED it 0/1/1, and the finding was fixed.
- **SPEC-2:** L's Down restores `role = 'admin'` only on active people. This supersedes PRD §8's rollback text ("the Down restores `role = 'admin'`") (see [[centralized-migrations]]).
- **PD-1:** FR-AR-MIG-004's "list K as the pin until this" is wrong. J was the pin until L, and K was never pinned.
- **OQ-2:** temporary passwords match `^[a-z]{3,8}(-[a-z]{3,8}){3}-[0-9]{2}$` and are 18–38 characters, not "about 17 to 24".
- **OQ-1:** the service gained `MODEL_SPEND_DAILY_CEILING_USD`, which is not in PRD §8's variable list.
- **OQ-W1:** `GET /admin/users` also answers `totals {people, active}` (contracts r3 §4.2). The PRD's shape lacks it.
- **B3:** the service's error-code log field is `error_code`.
- **Resend `Retry-After`:** the service waits until **both** resend rules allow, the later of the two waits. Contracts r3 §2.3 says "the earlier of the two". This is recorded as contract errata, and the as-built rule is stricter.
- **Email rule:** the service accepts only printable-ASCII email addresses. This narrows PRD §4.5.1 and is documented in the service README.
- **Edit person:** the web validates only the fields that changed. So the backfilled owner row, which has NULL email and phone, can be renamed without inventing an email or phone. The web plan's AR-W-12 had said "all three".
- **Audit actors (F3):** `operator_login_failed` and `operator_password_reset` always have no actor (system), as PRD §4.8 lists them.
- **E2E-005 method:** it ran on a copy of the retained preview database in a separate volume. The per-run database starts fresh at L, so it could not hold a pre-L admin row.

(source: raw/2026-10-29-accounts-roles.md §Concept, Spec corrections)

## What each project gained

| Project | Change |
|---|---|
| `tidewatch-migrations` | Migration L `20261028120000_accounts_and_roles.sql`: `operators`, `operator_sessions`, `plans` with the founder seed, `password_setup_tokens`, eight new `users` columns and the backfill, `events.actor_operator_id`, and `model_calls.bot_id`/`user_id`. The harness gained exact lists, probes and round trips (see [[centralized-migrations]]) |
| `tidewatch-service` | The operator principal, the challenge store and the code sender. 16 gated `/admin` routes (auth 4, people 7, operators 3, audit, spend), the CLI `operator create`/`set-password` and `user set-password`, and `Entitlements`. The product role gate moved to `user` (`RoleAdmin` deleted). There are 34 closed audit types, and the pin moved J → L (see [[operator-console]], [[auth-model]]) |
| `tidewatch-bot` | The evaluated-bots join to `plans`, the per-person allowance (S16), tier entitlement (S15), and `bot_id`/`user_id` on every bot call. Two metric families and two warn events were added, with no new variable (see [[bots-engine]]) |
| `tidewatch-web` | The lazy `/admin` console with its own shell, store, guards and API service, and a prerendered `/admin/sign-in`. `console.css` and four icons were added. On the product side, the account menu shows the display name and the editor marks unentitled tiers. The e2e moved to an operator helper and per-run people (see [[operator-console]], [[design-system-decisions]]) |

(source: raw/2026-10-29-accounts-roles.md §Database; §API; §Components; §Files touched)

## Rollout to production (2026-10-29)

| Time (UTC) | Event |
|---|---|
| 03:22 | The owner asked to merge, and the orchestrator held first. Merging migrations #16 runs L in production through the migrate hook, after which the old service refuses product requests. The new service exits at start without its Vault entries, and the Deployment strategy is Recreate. So the orchestrator asked the owner to confirm Vault |
| 04:04–04:52 | The owner chose the Twilio auth token. Commits `23d921f` and `5c57438` were reviewed, pushed to #18 and passed CI. Operator sign-in passed on the refreshed preview |
| 06:59:15 | The owner force-synced ExternalSecret `tidewatch-service-env`. Its keys were checked **by name only**: formats got a pass/fail check, and no value was printed. The five new names were present: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID`, `TIDEWATCH_OPERATOR_PASSWORD` and `TIDEWATCH_OPERATOR_PHONE`. The owner kept the environment bootstrap as built |
| 07:00:39 | Migrations #16 merged. GitOps bump `988d34d` (`migrate.image`) landed at 07:10:58 |
| 07:11:28 | ArgoCD `tidewatch-service` was still on `db77ef3`. **L had not been applied** |
| 07:11:46 / 07:11:51 | Service #18 and bot #19 merged before ArgoCD applied L, so the migrate hook and the new service would roll in one sync |
| 07:19:12 | The new bot rolled first. Its evaluated-bots read joins `plans`, which did not exist yet, so it logged 12 `bots_pass_failed` with Postgres 42P01 (undefined table), one per 30 s pass, 07:19:28–07:24:58 |
| 07:25:10 | **L applied**, in the sync triggered by the **service** image bump `e832d20` |
| 07:25:32 | The service bootstrapped operator `owner` and logged the `TIDEWATCH_ADMIN_* is retired` warning |
| 07:25:41 | The new service rolled (Recreate), about 30 s after L. `/info` reported `35177e1`, and `/ready` was ok. From then on the bot ran clean |
| 07:26:18 / 07:33:38 | Web #23 merged, then rolled. `/admin/sign-in` answered 200 with the title "Sign in · Console · Tidewatch", and `/sign-in` answered 200 |

**Lesson:** a migrations-only GitOps bump does not trigger an ArgoCD sync. The migrate Job is a Sync hook at wave −1, and hooks are not diffed. The full lesson is on [[centralized-migrations]] (source: raw/2026-10-29-accounts-roles.md §Concept, Rollout to production; Lesson recorded).

## Test plan and acceptance

**Acceptance status: 51 IDs, 0 failed.**

| Result | Count | IDs |
|---|---|---|
| verified (unit) | 4 | SVC-003, SVC-014, BOT-001, BOT-003 |
| verified (integration) | 18 | MIG-001…003; SVC-001, 002, 004–013, 015, 017; BOT-002 |
| verified (static) | 1 | WEB-014 |
| verified (review) | 3 | MIG-004, SVC-018, BOT-004 |
| verified (preview) | 18 | SVC-016; WEB-001…013; E2E-001, 002, 003, 005 |
| verified (preview), with deviation | 1 | E2E-004 (D-E2E004, kept as built) |
| not in this build (Phase B) | 6 | B-001…006 |

**What the E2E checks showed** (preview, per-run database at L, `dev` sender):
- **E2E-001 (fresh stack).** The operator bootstrapped, signed in with the dev code, made the forced change and added a person, whose temporary password was shown once. The person signed in at `/sign-in`, changed the password and landed on Overview. Bots showed Me and Slack Water at ฿1,000,000, and People showed the person *Active* with `1 active · 2`. In SQL the person reads user / active / founder, with `created_by_operator_id` set.
- **E2E-002 (cross-principal).** Each cookie was refused on the other side with 401 and no `Set-Cookie` (above).
- **E2E-003 (disable).** The person's socket closed 4401 **20,594 ms** after the disable, inside the 60,000 ms bound. Their next REST call landed on `/sign-in`. SQL showed `session_revoked {user_disabled}`, `user_disabled {bots_paused: 1}` and `bot_status_changed {running → paused, user_disabled}` for Slack Water. After *Enable* the person signed in again, and Slack Water stayed paused.
- **E2E-004 (allowance).** At allowance 0.500000, bot B wrote `bot_decide` (Jev, $0.000032) and `bot_thesis` rows, both carrying `bot_id` and `user_id`. At 0.0001, bot C's wake proposed with a template thesis and 0 model calls. `bots_user_budget_reached_total{tier="jev"}` went 0 → 1, while the per-bot budget and ceiling counters stayed 0. The Spend leg was the deviation (SC-E2E004 above).
- **E2E-005 (backfill).** Counts identical before and after L (above).
- **SVC-016 (metrics).** All 10 operator series read 0 before the runs. After them they equalled the audit events in the same database.

**Final web run.** The final `operator` run passed 527 of 527, with 360 captures and 360 axe runs at 0 violations. No capture scrolled horizontally, and the lowest of 424 contrast pairs was 4.65 (source: raw/2026-10-29-accounts-roles.md §Test plan, Results, Acceptance status, Preview runs and What each E2E check showed).

**Not verified or partial:**
- **Twilio.** The sender has never run against the live API, in preview or production. The owner's first production sign-in is the smoke test. OA-TWILIO-SMOKE had asked for it before the rollout, and it was not run.
- **Mock-only screens.** Operators, Audit and Spend, and Edit and Reset password, ran only against the e2e mock. Their service routes have integration evidence.
- **Tier entitlement on a real wake.** `bots_tier_not_entitled_total` read 0 throughout.
- **L's Down** ran only in the disposable harness.
- **Web builds.** `operator-live`, the product projects and the metrics scrape ran on web `0c99f26`, not on `10851db`.
- **Production after deploy** is verified only by `/info`, `/ready`, the bootstrap log line, the bot's logs and the rendered `/admin/sign-in`.

(source: raw/2026-10-29-accounts-roles.md §Test plan, Not verified or partial)

## Review history (abridged)

- **Migrations.** Plan approved at r3. Security had two should-fix items. S-1: the Down re-admitted disabled or invited people, which SPEC-2 resolved. S-2: the Down loses audit actors, documented with an export step.
- **Service.** Plan approved at r3. Code round 1 had five reviewers and 7 should-fix items, fixed as F1–F11. Fix round 2, G1–G3, made every People and Operators write lock the acting **session** row `FOR SHARE`, so a session revoked mid-request writes nothing and returns no temporary password.
- **Bot.** Security SF-1: no spec pinned the allowance's two fail-closed paths. Two mutation-checked specs fixed it.
- **Web.**
  - Round 1 asked for changes: code-e2e found 4 blocking items, security found SEC-W-1 (Playwright's `error-context.md` could persist typed secrets), and the design review found that axe covered only part of the matrix.
  - Fix rounds H1–H16 and J1–J8 followed, and round 3 security approved.
  - The visual pass approved 0/3/13. VW1 and VW2 were fixed in `10851db`, and VW3 is open for the owner.

(source: raw/2026-10-29-accounts-roles.md §Concept, Review history)

## Open items

**Owner actions still open.**
- **The first production operator sign-in.** This is the live Twilio smoke test. The steps, and the Vault clean-up that follows, are on [[operator-console]].
- **tidewatch-kubernetes.** The service chart still sets `TIDEWATCH_ADMIN_USERNAME`, which only causes the retired-variable warning. `scripts/seed-vault.sh` still prompts for `TIDEWATCH_ADMIN_*` and asks for no operator or Twilio values.
- **Optional (OA-SPEND-CHART, OA-SPEND-COMPOSE).** Add `MODEL_SPEND_DAILY_CEILING_USD` to the service chart, matching the bot chart's `"1.00"`, and to the root `docker-compose.yaml` service environment.
- **Root files.** The root `.env.example` and compose need the new service lines with `dev`, and `TIDEWATCH_ADMIN_*` should be removed from the example.
- **Preview leftovers.** The source lists these (see [[forge-preview-gateway]]).

**Open owner decisions.**
- **VW3.** The Edit dialog's country select (150 px) shows "United States and C" and hides `+1` above 600 px. Either put the dialling code first, which needs a copy sign-off, or widen the select.
- **AUDIT-RAW-USERNAME.** `/admin/audit` shows the raw typed username stored by failed sign-ins for unknown accounts. The owner decides whether to keep it or omit it.
- **COPY-SIGNOFF.** The web copy that the PRD did not give, listed in the web PR.
- **Bot security N-1.** A crashed wake's committed spend drops out of the person's allowance sum, an edge the PRD accepted. The options are `max(today sum, attributed model_calls sum)` or a restart sweep.

**Sibling builds.** learning-loop (migration M) and signals-context (migration N) were built against `main` before L merged. The settled order is L → M → N. Both must update their branches onto the new `main` and re-pin their `RequiredSchemaVersion` and harness lists after L, before they merge. Local primary checkouts need `/forge-sync` to pick up the four merges.

**Update (2026-10-30): both siblings merged after L.** Signals context merged `main` into its four branches after L (2026-10-30T04:12Z) and again after M. In the L update, its service saves in `entitlements_test.go` and `bots_caps_test.go` were wrapped in `withLiveSources`, and the web kept both sides of `DESIGN.md`. It merged on 2026-10-30 in the order migrations → service → bot and web, after learning-loop's service#16, bot#17 and web#21. **The required schema version is now M (`20261028120100`), set by learning-loop.** Signals context's N (`20261028120200`) is never pinned. Goose order is K, L, M, N (see [[signals-context]] and [[centralized-migrations]]) (source: raw/2026-10-30-signals-context.md §Concept, Merge updates (ORCH-5); §Database, Pins).

**Follow-ups.** The service, web and bot follow-ups that concern the console are on [[operator-console]]. The bot follow-ups:
- make the `ScoutWake.bot` plan fields required;
- check both ids at wake start;
- take `user_id` from `bots.owner_user_id` in SQL;
- put `MemoryPlan` and `FOUNDER_PLAN` on the testing barrel, and make the memory store mirror L's foreign keys.

A disable in the middle of a pass leaves the bot running for the rest of that pass, as a user Pause does. The migrations follow-up: five pre-L harness summary claims overstate (FR-ZB-MIG-001, FR-BA-MIG-002, FR-SIG-MIG-001, FR-SIM-MIG-003 and FR-ZB-MIG-003). Outside the build:
- `tidewatch-apis` may get an api-spec-generator pass for `/admin/*`;
- the `documents/` amendments (D17);
- Phase B.

(source: raw/2026-10-29-accounts-roles.md §Open questions)

## Since the learning loop (2026-10-30)

The learning loop (migrations #14, service #16, bot #17, web #21; merged and deployed to production on 2026-10-30) was the first sibling to land after L. See [[learning-loop]].

- **The sibling order held.** learning-loop merged `origin/main` with L into all four branches on 2026-10-29, re-pinned onto L + M, and merged as M. The pin moved L → M (see [[centralized-migrations]]). signals-context (N) is the last sibling and still has to update onto `main` with M.
- **Role `user` on the learning routes.** PRD §6.1 mounted the six new routes behind `RequireRole("admin")`. Since L every product route is behind `RequireRole("user")`, and nothing accepts `admin`, so the learning routes use `user`. The learning handler tests sign in as role `user` (`98211ab`), and a learned *Save as vN* still gets the plan's tier check (`c29d0f0`).
- **The allowance counts learn spend (OD-LEARN-SPEND, "Count it fully").** A learning run's `post_mortem` calls carry the bot's `bot_id` and the owner's `user_id`. The owner's day spend now sums scout **and** learn runs (`OWNER_COST_FOR_DAY`), and the labeller checks `spent_user + tally + estimate ≤ plans.daily_model_usd` after the per-bot share. So a person's $0.50 founder allowance now covers both their bots' scout wakes and their learning runs (see [[model-routes-and-spend]]). The allowance holds per runner, so a concurrent scout wake and learning run do not see each other's in-flight tally.
- **Spend shows labelling as the owner's.** Because the calls are attributed, the console's Spend counts them under `bots_usd` and the person, not `ingest_usd`. Before the fix they would have shown as ingest; 12 such pre-fix rows remain on the preview database, none in production (see [[operator-console]]).
- **The 35th audit type.** `learning_draft_dismissed {bot_id, learning_run_id}` joins the closed `audit.Types()` list, and the web's `AUDIT_TYPES` (closed at 34) gained it as the 35th (`f2ee96c`).
- **On the preview (PV6),** the seeded `pv4-learning` user read role `user` after L was applied. It dismissed a draft (200, then `409 draft_not_pending`), the event showed on `/admin/audit` with `actor_user_id`, and `GET /admin/spend` answered 200.

(source: raw/2026-10-30-learning-loop.md §Concept, Branch update onto L; §Concept, Decisions during the build, Letter M and OD-LEARN-SPEND; §Concept, Spec corrections, Gate chain and OD-LEARN-SPEND; §Components, Data layer; §Test plan, Preview runs; §Open questions, Sibling builds and Recorded residuals)

## Related pages

- [[operator-console]]: the `/admin` console, its sign-in, routes, CLI, configuration and the owner's first sign-in
- [[auth-model]]: the product sessions and throttle, now for role `user`, beside the operator principal
- [[foundation-auth]]: the slice-0 seeded `admin` and `TIDEWATCH_ADMIN_*`, now retired and backfilled
- [[centralized-migrations]]: migration L, the J → L pin, the SPEC-2 Down, the L → M → N order and the GitOps-hook lesson
- [[model-routes-and-spend]]: `model_calls.bot_id`/`user_id`, the per-person allowance and Spend's ingest/bots split
- [[bots-engine]]: the evaluated-bots join to `plans`, S16 and S15
- [[bot-versions-and-runs]]: the plan's active-bot cap, the `not_entitled` refusal and the plan's starting capital
- [[realtime-websocket]]: the hub re-check on role `user`, and the 4401 close for a disabled person
- [[paper-trading]]: `EnsureBots` at the plan's starting capital, and disable pausing through the Pause path
- [[request-protection]]: CSRF, CORS and `no-store` over `/admin/*`
- [[statistics]]: Stats' cost of decisions still reads `bot_runs.counts.cost_usd`
- [[design-system-decisions]]: `console.css`, the four icons, the AR-W and OQ-W decisions and VW1–VW3
- [[forge-preview-gateway]]: the per-run preview database and the `dev` sender
- [[user-settings]] and [[decision-record]]: per-person data that survived the backfill and stays hidden from operators
- [[learning-loop]]: migration M after L, role `user` on its routes, and learn spend under the allowance
- [[signals-context]]: the sibling build that owns migration N and merged after L and M
