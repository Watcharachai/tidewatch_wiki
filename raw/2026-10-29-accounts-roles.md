# Accounts and roles, Phase A (`accounts-roles`): operators separate from users, the operator console, plans as data

> Before this feature Tidewatch had one account. The seeded `admin` row was bootstrapped from `TIDEWATCH_ADMIN_PASSWORD` and was both the only product user and the only administrator. All 64 gated product routes and `/ws` sat behind `RequireRole("admin")`. Phase A split the two:
> - **Operators** are a principal of their own. They have their own tables (`operators`, `operator_sessions`), cookie (`tw_admin`) and route group (`/admin/*`), and two roles, `owner` and `staff`. Every sign-in is a password and then a Twilio Verify SMS code.
> - **People** are users with role `user`. Each person has a display name, email, phone, status (`invited | active | disabled`) and plan.
>   - An operator creates a person in the console, which shows a temporary password once.
>   - The person must change it at first sign-in.
>   - An operator can edit a person, reset the password, disable sign-in (which pauses the person's auto bots) and enable sign-in again.
> - **Plans are data.** One `founder` row gives 10 active auto bots, $0.50 of model spend a day, all four decision tiers, no live trading and ฿1,000,000 starting capital. It replaces the constants in the service and the bot.
> - **Bot spend is bounded and attributed per person.** The bot holds each person to the plan's daily allowance, runs a tier the plan excludes as `none`, and stamps `bot_id` and `user_id` on every bot model call.
> - **No public sign-up exists in any phase (D19).** Phase B (the setup link with phone proof, the user code step, email verification, later `/sign-up`) is specified and pending by design. Its tables and columns already ship in migration L.
>
> **Status (2026-10-29).**
> - **Merged** on the owner's instruction, all four PRs:
>   - tidewatch-migrations #16 → `080979d` (07:00:39Z);
>   - tidewatch-service #18 → `35177e1` (07:11:46Z);
>   - tidewatch-bot #19 → `bd5e435` (07:11:51Z);
>   - tidewatch-web #23 → `4725cb9` (07:26:18Z).
> - **Deployed to production.**
>   - Migration L was applied at 07:25:10Z, and the service bootstrapped operator `owner` at 07:25:32Z.
>   - The new service rolled at 07:25:41Z and the bot at 07:19:12Z.
>   - The web rolled at 07:33:38Z, with `https://tidewatchtrade.com/admin/sign-in` answering 200.
> - **Verified.**
>   - 45 of the 51 acceptance IDs are verified: 44 outright and FR-AR-E2E-004 with the recorded deviation D-E2E004, which the owner kept as built.
>   - The other 6 are the Phase B rows, which are not in this build.
>   - 0 failed.
> - **Not done.** The owner's first production sign-in at `/admin/sign-in` has not happened. It will be the first live Twilio Verify send, because the Twilio sender has never run against the live API.

**Sources (inputs to this document).**
- **Spec.** In `/Users/maichinu/tidewatch/tidewatch-specs/accounts-roles/`:
  - `build-prompt.md`;
  - `intent.md` (O1–O8, D1–D19; confirmed 2026-10-27);
  - `prd.md` (S1–S22, §4–§11, `FR-AR-*`; the requirement source);
  - `mockup.html`.
  - The fingerprints matched at build start (2026-10-27T17:29:02Z): intent `c717e13a…6c24`, prd `3e8bba95…73fd`, mockup `9b48eebc…890d4`.
- **Build record.** In `/Users/maichinu/tidewatch/.forge/features/accounts-roles/`:
  - `state.json`: `decisions`, `specCorrections`, `ownerDecisions`, `ownerActions`, `deploy`, the `perProject` merge records and `log`;
  - `verification.md`: every PRD ID with its result and evidence;
  - `artifacts/pr/tidewatch-{migrations,service,bot,web}.pr.md`;
  - `planning/tidewatch-service/contracts.md` r3 (sha256 `976344e5…9829`), the binding wire contract.
- **Plans.** Each is the `.plans/accounts-roles.md` of its worktree under `/Users/maichinu/tidewatch/.forge/docker/runs/acct-c04f668a/worktrees/`:
  - migrations `b7ddc75378`: S1–S3;
  - service `329891b601`: S1–S11;
  - bot `6945fd5d6c`: S1–S5;
  - web `5eb4e5c7ea`: S1–S11.
- **Merged code, read in those worktrees at their merged heads.** The migration file; the service `README.md` and `CLAUDE.md` ("Accounts and roles invariants"); `internal/audit/audit.go`; `internal/config/config.go`; the bot and web `CLAUDE.md`.
- **Record notes.**
  - `verification.md`'s header still says "nothing is merged or deployed". It was written before the merges.
  - `state.json` (the `merge` records, `deploy`, and the `log` from 2026-10-29T06:59Z on) is authoritative for merge and deploy.
  - `verification.md` is authoritative for verified, failed and unverified.
  - The `artifacts/pr/*.pr.md` files are the pre-preview bodies. The preview and E2E-004 results were added to the published bodies separately (`state.runtime.prBodiesUpdated`).

## Concept

### Stage, stated precisely

| Stage | Status |
|---|---|
| Implemented | **Migrations:** S1–S3 (feat `b955a8c`, plan `0d1ada5`). **Service:** S1–S11 (feat `1eba43b`, plan `d4d5104`), then the owner-decided Twilio auth-token change `23d921f` and its review fixes `5c57438` (PR head). **Bot:** S1–S5 (feat `81e29b5`, plan `4e66579`). **Web:** S1–S11 (feat `5196393`, plan `0c99f26`); after the PR opened, e2e fixes `03d065c`, visual fixes `10851db`, DESIGN.md corrections `a7498cd` and the CI fix `ce420a7` (PR head). |
| Reviewed | Plans and code in all four repositories (see "Review history"). Plan-review fix loops: migrations 2, service 2, bot 1, web 2. Code-review fix loops: migrations 2, service 2, bot 1, web 2. |
| Verified locally | Every step's contract commands exited 0, and the orchestrator re-ran them independently (see "Test plan"). |
| Verified on a preview | **Yes.** A per-run isolated database at L, 2026-10-28 18:48Z–20:36Z; E2E-004 on 2026-10-29 02:00–02:08Z. The `dev` code sender was used, so Twilio never ran. |
| Merged | **Yes**, 2026-10-29, by Claude on the owner's instruction, in the order migrations → service and bot → web. |
| Deployed | **Yes, to production.** A merge to `main` is a production deploy: deploy-prod → GHCR → tidewatch-kubernetes GitOps bump → ArgoCD. See "Rollout to production". |
| First operator sign-in in production | **Not done.** It is the owner's action and the first live Twilio send. |
| Documentation pass | This document and the wiki update (worktree `docs-7ce006e44c`). `documents/` is untouched (slice-0 D17). The owner is to amend 05 §1, §2 and §11 and research brief §7 when the user phase is built (intent D17). |

### Problem

At `main` on 2026-10-27:
- **The one account.** `users(id, username, password_hash, role DEFAULT 'admin', must_change_password, created_at, last_login_at)` held one row, the seeded `admin`, created at first start from `TIDEWATCH_ADMIN_PASSWORD`.
- **Where `RequireRole("admin")` was read:** the router's gate chain, the bootstrap, and the websocket hub's 60-second re-check (4403 when the role was not `admin`).
- **The audit log.** `events.actor_user_id` was a foreign key to `users`, so an operator's action had nowhere to be recorded.
- **Ownership was already per user.** `bots.owner_user_id` was on every bot query. `EnsureBots` created `me` and Slack Water (฿1,000,000 each) for any user id. At most 10 active auto bots were allowed per account, and settings and watchlists were per user. Only account creation and the operator/user split were missing.
- **Model spend.** One $1.00 Bangkok-day ceiling was shared by ingest and every bot, with a 25 % per-bot share. `model_calls` had no `bot_id` or `user_id`.
- **What the owner asked for:** to invite other people who "can use the product but cannot create accounts or perform admin actions", and later to let people sign up and subscribe, so "admin and user should be separate".

### The model, as built

- **Two principals in two tables (D1).**
  - Operator: `operators` + `operator_sessions`, cookie `tw_admin`, `/admin/*` only.
  - User: `users` + `sessions`, cookie `tw_session`, the product only.
  - The service has one auth package parameterised by principal kind (`session.Principal` carries a `Kind`, and `KindNone` fails closed). It has two repositories, two cookies and two throttle keyspaces.
  - A cookie of the other kind is simply absent to a gate: `401 unauthenticated` with no `Set-Cookie` for the other cookie.
- **Operator roles.**
  - `owner` and `staff` may both do everything under People, Audit and Spend.
  - Only `owner` reaches `/admin/operators/*` (list, disable, enable).
  - Operators are created only by the CLI `operator create` (D3). The first one is bootstrapped from `TIDEWATCH_OPERATOR_*` when `operators` is empty (D2).
- **Operator sign-in (D10).**
  - The password step answers a challenge, never a cookie. Only a right SMS code (Twilio Verify) sets `tw_admin`.
  - Every sign-in needs a code; there is no trusted-device skip.
  - Sessions last 12 h idle and 7 d absolute (D12). TOTP is the recorded next hardening, not built.
- **People.**
  - Created only by `POST /admin/users` (console *Add person*): username, display name, email and phone are all required. Email and phone are stored but not verified (D9).
  - A new person is `invited`, with `must_change_password = true`, plan `founder` and a temporary password shown once.
  - The first successful sign-in flips `invited → active` and writes `user_activated`.
  - *Disable sign-in* revokes every session and pauses the person's running and observing auto bots through the user's own Pause path. *Enable* restores sign-in only; the bots stay paused.
  - Nothing is ever deleted (D13).
  - Operators see counts and spend only: no decisions, bot names, configs or impersonation (D6).
- **The owner's workspace survived (D2, O2).** Migration L backfilled the seeded `admin` row to a plain `user`:
  - `display_name = 'admin'`, `status = 'active'`, `plan_id = 'founder'`, NULL email and phone;
  - the same id, password hash, bots, decisions, watchlist and settings.
  - The owner's product sign-in needed no action.
- **Plans as data (D4, D5).**
  - One `founder` row; `users.plan_id` is NOT NULL.
  - The service's `Entitlements` is the only reader of the cap, the tiers and the starting capital.
  - The bot reads `daily_model_usd` and `decision_tiers` by join.
  - There is no plan write route and no *Change plan*. A second plan is a data migration.
- **No public sign-up (D19).** `/auth/register`, `/sign-up` and `/admin/register` answer `404` for every method, `OPTIONS` included. `TestRouter_NoSignup` admits `POST /admin/users` as the only user-creating route. The product's `/sign-in` keeps no links.
- **Phase B is pending by design (D11, D18; PRD §4.11, `FR-AR-B-001…006`).** It covers:
  - `POST /admin/users/{id}/setup-link`;
  - the prerendered `/set-password` with phone proof;
  - the user code step on `/sign-in`;
  - refusing a user with no phone;
  - email verification;
  - later, `/sign-up` with subscriptions in their own spec.

  Its data (`password_setup_tokens`, email, phone, status, plan) ships in L with no writer. Phase B waits on the owner's go, and on the owner's own row having email and phone set in *Edit person*.

### Owner decisions from the intent (selected; the full D1–D19 are in `intent.md`)

- **D1** Two principals in two tables, as above. One table with a `kind` column was rejected.
- **D2** The operator is bootstrapped from new variables, and `TIDEWATCH_ADMIN_*` is retired (read, ignored, warned about). No user is ever bootstrapped again.
- **D3** Roles `owner` and `staff`; operators are created by the CLI. The console's Operators page is read-only plus *Disable* / *Enable*.
- **D4, D5** `plans` ships with one row. The founder values are as above, and the allowance is enforced bot-side per user beside the 25 % per-bot budget and under the shared ceiling.
- **D7** `EnsureBots` is unchanged: every person gets `me` and a running, rules-only Slack Water at the plan's starting capital.
- **D8** `/admin/*` is on the same origin. `admin.tidewatchtrade.com` is reserved for later.
- **D10** A Twilio Verify SMS code on every operator sign-in; `TIDEWATCH_OTP_SENDER=twilio|dev`, with `dev` only when `ENVIRONMENT=local`.
- **D13** The lifecycle is `invited | active | disabled`; `pending_verification` and `suspended` are reserved; there is no delete.
- **D14** `events.actor_operator_id` sits beside `actor_user_id`; the two are never both set (S22).
- **D16** One timestamp-named migration. The siblings learning-loop and signals-context each also expected the letter after K, and the pin order was settled at build time: **L (this) → M (learning-loop) → N (signals-context)**.
- **D17** The founding rule changes from "no public sign-up, ever" to "invite-only until the subscription feature". `documents/` is not edited by this build.
- **D19** No public sign-up exists in any build until the subscription feature's own spec reopens it.

### Decisions during the build

| Id | When / by | Decision |
|---|---|---|
| PD-1 | 2026-10-27, parent | Spec correction to FR-AR-MIG-004: J (`20261020041046`) was the pin until L; K (`20261021082304`, index-only) was never pinned. The service pin moved J → L. |
| ORCH-3 | 2026-10-27, orchestrator | FR-AR-E2E-003 keeps the PRD's 60 s bound. |
| OQ-1 (a) | 2026-10-28, owner | The service reads `MODEL_SPEND_DAILY_CEILING_USD` (optional, default 1.00, parsed exactly as the bot parses it) for Spend's `ceiling_usd`. It is an owner-approved new service variable, an exception to PRD §8's list. |
| OQ-2 (accept) | 2026-10-28, owner | Temporary passwords keep the BIP-39 English list (2,048 words, MIT) and are **18–38 characters**: a spec correction to S2's "about 17 to 24". |
| B3 (A) | 2026-10-28, parent under owner delegation | The service's error-code log field was renamed `error_code` so it no longer collides with the masked `code` key. PRD §8's masked keys (`password`, `temporary_password`, `code`, `new_password`) are kept literally. |
| WAVE2-MODE | same | Dependency-gated lanes, each in its own worktree; nothing merges without the owner. |
| PB-1..3 | same | The bots package writes `bot_id` and `user_id`, and `packages/signals/src` is untouched. The S16 held reservations are the per-bot term summed over the person's bots. `bots_tier_not_entitled_total` is labelled with the three model tiers only. |
| OQ-W1 (a) | same | Contracts r3 added `totals {people, active}` to `GET /admin/users`, counted over all people and independent of `q`, `status` and `cursor`. |
| OQ-W2..W4 | same | Web copy not given by the PRD was accepted as planned (pending owner sign-off). `operator-live.spec.ts` makes the forced change in the UI. A 38-character temporary password wraps only at its hyphens at 390 px. |
| PREVIEW-DB | same | The preview used a per-run isolated, retained database, not the shared workspace volume, because L, M and N carry fixed goose versions from unmerged branches. |
| SPEC-2 (Down A) | 2026-10-28, parent under owner delegation | Spec correction to PRD §5's Down: `UPDATE users SET role = 'admin' WHERE status = 'active'` runs **before** the `ALTER` that drops `status`, so a rollback never re-admits a disabled or invited person. The Up block stays byte-identical to the PRD. |
| ORCH-4…8 | 2026-10-28, orchestrator | Bounded patches outside a step's file list, each recorded: test assertions for role `user` and `display_name`; the `operator_bootstrapped` audit type; the new codes in the contract list; the audit types list; the superseded web project-list check. |
| PREVIEW-E2E004 | 2026-10-29, owner ("Run E2E-004") | Run on a dedicated plan `e2e004`, never on `founder`. It spent $0.000032 of Jev credit. |
| D-E2E004 | 2026-10-29T03:17Z, owner | "Keep as built"; see SC-E2E004. |
| OWNER-TWILIO-AUTH-TOKEN | 2026-10-29T04:04Z, owner | Twilio Verify basic auth is `TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN`, the same pattern as sakuship-service; see SC-TWILIO-AUTH. |

### Spec corrections: the as-built truth that supersedes the PRD text

The build did not edit the spec repository. Where this list and `prd.md` or `intent.md` disagree, this list is the truth.

- **SC-E2E004 (from D-E2E004): Spend's *At allowance* means actual spend has reached the allowance.**
  - `Person.spend.reached` and `GET /admin/spend` `people[].reached` are `today_usd ≥ allowance_usd`, where `today_usd` is the actual attributed spend of the Bangkok day.
  - The bot stops a person earlier, on spend **plus the next survivor's estimate** (S16). So a person the bot has already stopped can show no tag.
  - PRD FR-AR-E2E-004 says "with the allowance set to `0.0001` … *Spend* shows them *At allowance*". It did not hold as written: at 0.0001 the person's actual spend was 0.000032, so `reached` was false and no tag showed.
  - With the allowance at 0.000032, `reached` was true and the tag rendered.
  - The owner kept both rules as built. There was no code change.
- **SC-TWILIO-AUTH (from OWNER-TWILIO-AUTH-TOKEN): Twilio Verify uses HTTP basic auth `TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN`.**
  - `TWILIO_API_KEY_SID` and `TWILIO_API_KEY_SECRET` are gone: no hit remains in the merged service tree.
  - This supersedes PRD §4.4 ("HTTP basic auth `TWILIO_API_KEY_SID:TWILIO_API_KEY_SECRET` … the account SID is sent as the `AccountSid` of the key"), the PRD §8 environment table, and intent's owner Vault list.
  - The owner decided it on 2026-10-29: the owner holds an account SID, an auth token and a Verify service SID, with no API key, and sakuship-service signs in to Verify v2 the same way.
  - `TWILIO_AUTH_TOKEN` is a Tier-1 secret. It is masked by value by the redaction writer and kept out of formatted output (`json:"-"` in `internal/config/config.go`). The sender stays on `net/http` (no twilio-go SDK).
  - Shipped in service commits `23d921f` and `5c57438`: `make ci` exit 0; integration `ok` 503.044s, 0 FAIL, 0 SKIP; code review APPROVED 0/0/3; security review APPROVED 0/1/1, fixed.
- **SPEC-2:** L's Down restores `role = 'admin'` only on active people (above). PRD §8's rollback text ("the Down restores `role = 'admin'`") is superseded.
- **PD-1:** FR-AR-MIG-004's "list K as the pin until this" is wrong. J was the pin until L, and K was never pinned.
- **OQ-2:** temporary passwords match `^[a-z]{3,8}(-[a-z]{3,8}){3}-[0-9]{2}$` and are 18–38 characters, not "about 17 to 24".
- **OQ-1:** the service gained `MODEL_SPEND_DAILY_CEILING_USD`, beyond PRD §8's variable list.
- **OQ-W1:** `GET /admin/users` also answers `totals {people, active}` (contracts r3 §4.2); the PRD's shape lacks it.
- **B3:** the service's error-code log field is `error_code`.
- **Resend `Retry-After`:** the service answers the wait until **both** resend rules allow (the later of the two waits). Contracts r3 §2.3 says "the earlier of the two". This was recorded as contract errata and is stricter.
- **Email rule:** the service accepts only printable-ASCII email addresses, a narrowing of PRD §4.5.1 documented in the service README. The web shows a non-ASCII email line.
- **Edit person:** the web validates only the fields that changed, so the backfilled owner row (NULL email and phone) can be renamed without inventing an email or phone. The web plan's AR-W-12 had said "all three".
- **Audit actors (F3):** `operator_login_failed` and `operator_password_reset` always have no actor (system), as PRD §4.8 lists them. The code first named the operator on a known username; review fix F3 aligned it.
- **E2E-005 method:** it ran on a copy of the retained preview database in a separate volume, not on the preview's own database. The per-run database starts fresh at L, so it could not hold a pre-L admin row.

### Rollout to production (2026-10-29)

| Time (UTC) | Event |
|---|---|
| 03:22 | The owner asked to merge. The orchestrator held first, for two reasons. Merging migrations #16 runs L in production through the migrate hook, after which the old service refuses product requests. And the new service exits at start without its Vault entries, while the Deployment strategy is Recreate, so the production API would go down. The orchestrator asked the owner to confirm Vault. |
| 04:04–04:52 | The owner chose the Twilio auth token. Service commits `23d921f` and `5c57438` were reviewed, pushed to #18 and passed CI. The preview was refreshed and operator sign-in passed on it. |
| 06:59:15 | The owner force-synced ExternalSecret `tidewatch-service-env`. Its keys were checked **by name only**, with formats checked pass/fail and no value printed. It held the five new values (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID`, `TIDEWATCH_OPERATOR_PASSWORD`, `TIDEWATCH_OPERATOR_PHONE`) beside `DATABASE_URL`, `TIDEWATCH_KEY_ENCRYPTION_KEY` and `TIDEWATCH_ADMIN_PASSWORD`. The owner kept the environment bootstrap as built. All four PRs were open, mergeable and clean, with checks passing. |
| 07:00:39 | Merged migrations #16 → `080979d`. deploy-prod run `40832687813` succeeded. The GitOps bump `988d34d` (`migrate.image 0.1.0-build-20261029.080979de`) landed on tidewatch-kubernetes `main` at 07:10:58. |
| 07:11:28 | ArgoCD `tidewatch-service` was still on `db77ef3`, so L was not applied. |
| 07:11:46 / 07:11:51 | Merged service #18 → `35177e1` (head `5c57438`) and bot #19 → `bd5e435` (head `4e66579`). They went in before ArgoCD applied L, so the migrate hook and the new service would roll in one sync. The migrate Job is the service chart's Sync-phase hook at wave −1 (`argocd.argoproj.io/hook: Sync`), and a failed migration blocks the Deployment. deploy-prod runs: service `40833869556` (GitOps `e832d20`, 07:19:14), bot `40833880511` (GitOps `37fcded`, 07:15:02); both succeeded. |
| 07:19:12 | The new bot `0.1.0-build-20261029.bd5e4356` rolled first, with `/ready` ready. Its evaluated-bots read joins `plans`, which did not exist yet. It logged **12 `bots_pass_failed` with Postgres error 42P01** (undefined table), one per 30 s pass, from 07:19:28 to 07:24:58. |
| 07:25:10 | **L applied**: `tidewatch-migrate 0.1.0-build-20261029.080979de` logged `OK 20261028120000_accounts_and_roles.sql`. This happened in the sync triggered by the **service** image bump `e832d20`. |
| 07:25:32 | The service bootstrapped operator `owner` (`bootstrap: created operator`) and logged the `TIDEWATCH_ADMIN_* is retired` warning. |
| 07:25:41 | The new service `0.1.0-build-20261029.35177e1a` rolled (Recreate; about 30 s after L). `/info` reported commit `35177e1`, and `/ready` was ok (bootstrap, database, extensions, schema). From then on the bot was clean (`bots_run_finished`, no 42P01). |
| 07:26:18 | Merged web #23 → `4725cb9` (head `ce420a7`). |
| 07:33:38 | deploy-prod `40835427469` succeeded, GitOps `b2a8611`, and web `0.1.0-build-20261029.4725cb93` rolled. `https://tidewatchtrade.com/admin/sign-in` answered 200 with the title "Sign in · Console · Tidewatch". It rendered *Operator console*, *Username*, *Password* and *Continue* in the in-app browser. `/sign-in` answered 200. |

**Lesson recorded (GitOps and hooks): a migrations-only GitOps bump does not trigger an ArgoCD sync.**
- The migrate Job is a hook of the `tidewatch-service` chart, and hooks are not part of ArgoCD's diff. So the bump of `migrate.image` alone (`988d34d`) left the app "in sync", and L did not run.
- L ran only in the sync that the service image bump (`e832d20`) triggered.
- A future migration needs either a service image bump in the same rollout or a manual sync.
- The bot rolled independently of that sync, so a bot that needs the new schema logs failed passes until the service sync applies the migration. That is the 42P01 window above.

### Review history

- **Migrations.**
  - Plan: r1 and r2 CHANGES REQUESTED, r3 APPROVED.
  - Code: r1 code APPROVED (S-1 username-check match). Security APPROVED, with two should-fix: S-1, the Down re-admitted disabled or invited people, resolved by SPEC-2; and S-2, the Down loses audit actors, documented with the export step.
  - Fix rounds 1 and 2, then r2 code and security APPROVED.
- **Service.**
  - Plan: r1 (7 blocking) and r2 CHANGES REQUESTED; r3 and r4 APPROVED.
  - Code round 1 was split by slice: five reviewers, all APPROVED, 0 blocking, 7 should-fix.
  - Fix round 1 (F1–F11):
    - F1: a double-submitted right code no longer loses its challenge;
    - F2: `services/auth` no longer imports metrics;
    - F3: `operator_login_failed` always has the system actor;
    - F4: one operator reset path;
    - F5: People writes re-check the acting operator under lock;
    - F8: the dev sender re-checks `ENVIRONMENT=local`;
    - F9: audit enum validation;
    - F10: `updated_at` on user writes;
    - F11: the audit and spend repositories scrub driver errors;
    - F6 and F7: docs.
  - Round 2 APPROVED. Fix round 2 (G1–G3): every People and Operators write locks the acting **session** row `FOR SHARE`, so a session revoked mid-request writes nothing and returns no temporary password.
  - Round 3 security APPROVED.
- **Bot.**
  - Plan: r1 CHANGES REQUESTED; r2 and r3 APPROVED.
  - Code APPROVED (notes). Security APPROVED, with SF-1: no spec pinned the allowance's two fail-closed paths. Fixed in fix round 1 with two mutation-checked specs.
- **Web.**
  - Plan: r1 and r2 CHANGES REQUESTED; r3 and r4 APPROVED.
  - Round 1: angular and code-app APPROVED. Code-e2e (4 blocking), security (SEC-W-1: Playwright's `error-context.md` could persist typed secrets) and code-level design (axe covered only part of the matrix) asked for changes.
  - Fix round 1 (H1–H16), round 2 APPROVED, fix round 2 (J1–J8), round 3 security APPROVED.
  - Visual pass APPROVED 0/3/13. VW1 and VW2 were fixed in `10851db` and re-checked APPROVED. VW3 is open for the owner.

## Database

### Migration L: `20261028120000_accounts_and_roles.sql`

`tidewatch-migrations` PR #16, merge `080979d`; file sha256 `1decf74c…03b7` (after SPEC-2).
- It runs in goose's default transaction and holds ACCESS EXCLUSIVE locks on `users`, `events` and `model_calls`, and SHARE ROW EXCLUSIVE on `bots`, until commit.
- It is the service's `RequiredSchemaVersion` from this build on (J → L; K never pinned).
- The bot's `scripts/sql-integration.sh` finds it by the anchored lookup `ls migrations | grep -E '^[0-9]{14}_accounts_and_roles[.]sql$' | cut -c1-14` and refuses to run without it.

The Up block is PRD §5 byte for byte:

```sql
CREATE TABLE operators (
    id                   uuid        PRIMARY KEY DEFAULT uuidv7(),
    username             text        NOT NULL UNIQUE CHECK (username = lower(username)),
    password_hash        text        NOT NULL,
    role                 text        NOT NULL CHECK (role IN ('owner', 'staff')),
    phone                text        NOT NULL UNIQUE CHECK (phone ~ '^\+[1-9][0-9]{6,14}$'),
    must_change_password boolean     NOT NULL DEFAULT true,
    created_at           timestamptz NOT NULL DEFAULT now(),
    last_login_at        timestamptz,
    disabled_at          timestamptz
);

CREATE TABLE operator_sessions (
    id           uuid        PRIMARY KEY DEFAULT uuidv7(),
    operator_id  uuid        NOT NULL REFERENCES operators (id) ON DELETE CASCADE,
    token_hash   bytea       NOT NULL UNIQUE,
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    ip           inet,
    user_agent   text,
    revoked_at   timestamptz
);
CREATE INDEX operator_sessions_operator_id_active_idx ON operator_sessions (operator_id) WHERE revoked_at IS NULL;

CREATE TABLE plans (
    plan_id              text        PRIMARY KEY CHECK (plan_id ~ '^[a-z][a-z0-9_]{1,31}$'),
    name                 text        NOT NULL,
    max_active_auto_bots integer     NOT NULL CHECK (max_active_auto_bots >= 0),
    daily_model_usd      numeric(10,6) NOT NULL CHECK (daily_model_usd >= 0),
    decision_tiers       text[]      NOT NULL CHECK (decision_tiers <@ ARRAY['none', 'jev', 'small_llm', 'large_llm']),
    live_trading         boolean     NOT NULL DEFAULT false,
    starting_capital_thb numeric     NOT NULL CHECK (starting_capital_thb >= 10000),
    created_at           timestamptz NOT NULL DEFAULT now()
);
INSERT INTO plans (plan_id, name, max_active_auto_bots, daily_model_usd, decision_tiers, live_trading, starting_capital_thb)
VALUES ('founder', 'Founder', 10, 0.500000, ARRAY['none', 'jev', 'small_llm', 'large_llm'], false, 1000000);

ALTER TABLE users
    ADD COLUMN display_name           text,
    ADD COLUMN email                  text,
    ADD COLUMN phone                  text,
    ADD COLUMN status                 text        NOT NULL DEFAULT 'active',
    ADD COLUMN plan_id                text,
    ADD COLUMN created_by_operator_id uuid        REFERENCES operators (id),
    ADD COLUMN disabled_at            timestamptz,
    ADD COLUMN updated_at             timestamptz NOT NULL DEFAULT now();

-- The seeded admin becomes a plain user and keeps everything it owns (intent D2).
UPDATE users SET role = 'user', display_name = username, plan_id = 'founder';

ALTER TABLE users
    ALTER COLUMN role SET DEFAULT 'user',
    ALTER COLUMN display_name SET NOT NULL,
    ALTER COLUMN plan_id SET NOT NULL,
    ADD CONSTRAINT users_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES plans (plan_id),
    ADD CONSTRAINT users_display_name_check CHECK (length(display_name) BETWEEN 1 AND 80),
    ADD CONSTRAINT users_email_check CHECK (email = lower(email)),
    ADD CONSTRAINT users_phone_check CHECK (phone ~ '^\+[1-9][0-9]{6,14}$'),
    ADD CONSTRAINT users_status_check CHECK (status IN ('invited', 'active', 'disabled', 'pending_verification', 'suspended')),
    ADD CONSTRAINT users_disabled_check CHECK ((status = 'disabled') = (disabled_at IS NOT NULL));
CREATE UNIQUE INDEX users_email_key ON users (email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX users_phone_key ON users (phone) WHERE phone IS NOT NULL;

ALTER TABLE events ADD COLUMN actor_operator_id uuid REFERENCES operators (id);
CREATE INDEX events_actor_operator_id_occurred_at_idx ON events (actor_operator_id, occurred_at DESC);

CREATE TABLE password_setup_tokens (
    token_hash             bytea       PRIMARY KEY,
    user_id                uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_by_operator_id uuid        NOT NULL REFERENCES operators (id),
    created_at             timestamptz NOT NULL DEFAULT now(),
    expires_at             timestamptz NOT NULL,
    used_at                timestamptz
);
CREATE INDEX password_setup_tokens_user_id_idx ON password_setup_tokens (user_id);

ALTER TABLE model_calls
    ADD COLUMN bot_id  uuid REFERENCES bots (bot_id),
    ADD COLUMN user_id uuid REFERENCES users (id);
CREATE INDEX model_calls_user_id_created_idx ON model_calls (user_id, created_at DESC) WHERE user_id IS NOT NULL;
```

**Notes on the schema.**
- **Roles.** `users.role` still has no CHECK; the service enforces role `user`. `users.updated_at` has no trigger; the service sets it on user writes (F10).
- **Uniqueness.** Email and phone are unique only when set (partial unique indexes). The service decides uniqueness under these indexes, never by a pre-read: two concurrent creates give one `201` and one `409`.
- **Only hashes are stored.** Operator sessions store the token's SHA-256 only. `password_setup_tokens` stores token hashes only, and nothing writes it in Phase A.
- **A3 held.** `ALTER TABLE events ADD COLUMN`, its foreign key and its index are DDL, which the append-only triggers (`events_append_only`, `events_append_only_truncate`) do not intercept. The harness proved it over an empty and a non-empty `events`.
- **Attribution columns.** `model_calls.bot_id` and `user_id` are nullable. Rows written before L and every signals-stage row read NULL in both, so the owner's pre-rollout bot spend is not attributed (S4).
- **New seeds.** None beyond the `founder` row. A changed founder value or a second plan is a data migration, never an edit of L.

### Backfill (FR-AR-MIG-002, FR-AR-E2E-005)

Every pre-L `users` row became role `user`, with `display_name = username`, `plan_id = 'founder'` and `status = 'active'` (the column default), and NULL email, phone, creator and `disabled_at`. It kept its id, password hash, sessions and everything it owns.
- **Harness proof.** On a planted pre-L admin row, after up the row reads user / admin / founder / active with NULL email and phone. After down it reads `admin`.
- **On a copy of the retained preview database (E2E-005).** The copy held two pre-L admin rows, `admin` and `pv4-stats`. The counts were identical before and after L: bots 5, decisions 32, watchlist items 8, settings 3, positions 14, orders 26, fills 26, paper accounts 5, bot versions 8, bot runs 281, candidates 4, sessions 42, events 79. md5 fingerprints were identical. `POST /auth/login` as `admin` answered 204 and `/auth/me` read role `user`.

### The Down (destructive, owner-only, local-only; never a recovery path)

Order:
1. Drop the `model_calls` attribution and its index.
2. Drop `password_setup_tokens`.
3. Drop `events.actor_operator_id` and its index.
4. Drop the email and phone unique indexes.
5. **`UPDATE users SET role = 'admin' WHERE status = 'active'`** (SPEC-2).
6. Drop the six `users` constraints and eight columns, and restore `role DEFAULT 'admin'`.
7. Drop `plans`, `operator_sessions` and `operators`.

Everything uses `IF EXISTS`, with no `CASCADE`.
- **Who can sign in afterwards.** Only active people get `admin` back, so the previous service accepts them. Invited, disabled, `pending_verification` and `suspended` people keep `user`, which the previous service refuses. The owner's pre-L row is active from the backfill, so it reads `admin` unless an operator changed its status.
- **What it destroys:** every operator and operator session, the plan, the setup tokens, every person's display name, email, phone, status, creator and disable time, the `model_calls` attribution, and **the operator actor of every audit event**. The `DROP COLUMN` on `events` is DDL that the append-only triggers do not stop, so operator actions lose their actor for good.

**Owner steps before any Down** (L header, migrations README runbook; security reviews S-2 and R2-N1…N3):
1. Export the operator-attributed events and the operators table, for example `SELECT e.id, e.type, e.occurred_at, e.detail, o.username FROM events e JOIN operators o ON o.id = e.actor_operator_id`, and `operators` without `password_hash`. Write the `\copy` output to an absolute path outside every repository, and delete it after the rollback settles.
2. Record the non-admin ids before re-applying L. Re-applying makes everyone `active` again (the column default), so the owner re-disables people right after `goose up`.
3. If the owner is locked out after a Down, run `UPDATE users SET role='admin' WHERE username='<owner>'`.
4. The rollback order is: revert the three images, then run `make migrate-down` locally against a copy first.

### Harness (`scripts/check-disposable-db.sh`)

- **Exact lists for L:** the catalog, the expected relations, columns, constraints and indexes, the founder seed, and the A3 probes. The slice-0 and H lists leave L's objects to L by name, only while L is applied. `users` fixtures go through `users_insert`, keyed on whether `users.plan_id` exists.
- **Probes and round trips:** 31 refusals over 29 constraints, each matched by constraint name, and 11 accepted controls (an `events` row with both actor columns set among them). All are rolled back, in each of 7 passes with L applied. Then down-to K and up twice, down-to the auth migration and up, down-to 0 and up, with every assertion re-run after each round trip (ten passes).
- **Summary lines:** with L newest, J's and K's down-proofs print "not run", never "passed".

### Who reads and writes what

| Object | Writer | Reader |
|---|---|---|
| `operators`, `operator_sessions` | service (bootstrap, CLI, sign-in, Operators routes) | service |
| `users` new columns | service (`POST/PATCH /admin/users`, reset, disable, enable, first login) | service; bot reads `plan_id` by join only, never `users.status` |
| `plans` | the migration seed only | service `Entitlements`; bot evaluated-bots join (`daily_model_usd`, `decision_tiers`) |
| `events.actor_operator_id` | service typed audit constructors (`audit.ActorOperator`) | service `GET /admin/audit` |
| `model_calls.bot_id`, `user_id` | bot (`bot_decide`, `bot_thesis` via `INSERT_BOT_CALL` / `recordBotCalls`) | service Spend and `Person.spend` |
| `password_setup_tokens` | nothing (Phase B) | nothing |

## API

### Conventions (contracts r3)

- **Envelope and errors.** The error envelope is `{"error","code","requestID"}` plus optional `details`. The web maps `code` and `details`, never the `error` text.
- **Money and time.** Money in `/admin/*` is a decimal string with exactly 6 fraction digits. Instants are RFC 3339 UTC; dates are Bangkok `YYYY-MM-DD`; absent values are `null`.
- **No caching.** Every `/admin/*` answer carries `Cache-Control: no-store`, refusals and unknown `/admin` paths included.
- **Strict bodies (S8).** Every `/admin/*` body is at most 8 KiB and must be one JSON object. An unknown key is `400 invalid_request {reason: "unknown_field"}` and the key is never named. An absent or `null` required field is `{field, reason: "missing"}`, and a bad value is `{field, reason: "invalid"}`.
- **Strict queries.** An unknown parameter is `invalid` (no field), a repeated one `duplicate`, and an out-of-range `limit` `out_of_range`.
- **CSRF and CORS** are engine-wide and unchanged. Every `POST`, `PATCH` and `DELETE`, including `/admin/auth/login*`, needs `X-Tidewatch-Request: 1` and the exact app `Origin`.
- **Rate limits.** `429 rate_limited` always carries an integer `Retry-After`.

### Operator auth (`/admin/auth/*`)

| Route | Auth | Request | Success | Errors |
|---|---|---|---|---|
| `POST /admin/auth/login` | none + CSRF | `{username ≤ 64 B, password ≤ 1024 B}` | `200 {challenge_id, phone_hint, expires_at, resend_after}`, **no cookie** | `400`, `401 invalid_credentials`, `403 csrf_rejected`, `429` (+`Retry-After`; `600` on Twilio's send limit), `503 not_ready`, `503 otp_unavailable` |
| `POST /admin/auth/login/verify` | none + CSRF | `{challenge_id, code ≤ 16 B}` | `204` + `Set-Cookie: tw_admin=…` | `400`, `401 otp_invalid`, `403`, `429`, `503 otp_unavailable` |
| `POST /admin/auth/login/resend` | none + CSRF | `{challenge_id}` | `204` | `400`, `401 otp_invalid`, `403`, `429` (+`Retry-After`), `503 otp_unavailable` |
| `POST /admin/auth/logout`, `/logout-all` | operator + CSRF | — | `204` + clearing `tw_admin` | `401`, `403` |
| `GET /admin/auth/me` | operator | — | `200 {operator: {id, username, role, must_change_password}, session: {expires_at}}` | `401` |
| `POST /admin/auth/password` | operator + CSRF | `{current_password, new_password}` | `204`; the other operator sessions revoked | `401`, `422 current_password_incorrect \| password_too_short \| password_too_long \| password_too_common \| password_unchanged`, `429` |

**The login step.**
- **Order:** CSRF; the operator login IP window (5 per rolling minute; IPv4 per address, IPv6 per /64); parse; normalise; the username limit (10 per 15 minutes); the lockout (20 consecutive failures, password or code together, lock 15 minutes); **exactly one argon2id verification** (the operator's hash, or the dummy hash for an unknown, disabled or locked operator); then the outcome.
- **A right password does not reset the lockout run.** Only the verify step's right code calls `Attempt.Succeed`.
- **Indistinguishable failures.** A wrong password and an unknown, disabled or locked operator all get the same `401 invalid_credentials`, "Wrong username or password.", identical apart from `requestID`.
- **`phone_hint`** is the country code and the last four digits, with the rest shown as bullets (`+66 •• ••• 1234`). Nothing else about the phone leaves the service through sign-in.

**The challenge store** (`internal/auth/challenge`, S1).
- **Where it lives.** In process memory, bound to the operator and never to the client IP (S10), with a 10-minute life.
- **Attempts.** Each challenge has 5 checks, reserved atomically before the sender is asked. Under 200 parallel verifies at most 5 reach the sender.
- **Consuming.** Only a right code consumes a challenge. Every failure only marks it used up, so a double-submitted right code still opens its session (F1).
- **Resend.** Allowed 30 s after the last send, and at most 3 sends per operator in 10 minutes (every send counts).
- **Capacity.** At most 100,000 challenges; a new one is refused at the cap, nothing is evicted. The store is swept every minute. A restart drops the challenges in flight.
- **Dead challenges.** A dead, consumed, unknown or wrong challenge is the one `401 otp_invalid`, "That code isn't right.". A dead one waits a fixed delay so it answers in the same timing envelope as a wrong code.
- **Separate IP windows.** Login, verify and resend each have their own window of 5 a minute.

**The forced change (S9).** Bootstrapped and CLI-created operators start with `must_change_password = true`. Until they change it, every gated `/admin/*` route except `GET /admin/auth/me`, `POST /admin/auth/password`, `/logout` and `/logout-all` answers `403 password_change_required`.

**The code sender** (`internal/auth/otp`, port `Send` / `Check`).
- **`twilio`** (the default) is Twilio Verify v2 over `net/http`: `POST https://verify.twilio.com/v2/Services/{TWILIO_VERIFY_SERVICE_SID}/Verifications` (`To`, `Channel=sms`) and `/VerificationCheck` (`To`, `Code`).
  - It uses HTTP basic auth `TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN` (SC-TWILIO-AUTH), with a 10 s timeout per call.
  - **Error mapping (A1, a total mapping).**
    - Send: `60203` (max send attempts) → `send_limited`, `429` + `Retry-After: 600`; any other 4xx, 5xx, timeout or transport failure → `503 otp_unavailable`.
    - Check: `60202`, `20404` or a bare `404` → a dead challenge; `60200` with `400` → a wrong code; anything it cannot decide → `503 otp_unavailable`, never a pass.
  - It has run only against fixtures transcribed from Twilio's docs (`internal/auth/otp/testdata/twilio/`; two of them, `send_ok` and `check_20003`, are assumptions). It has never run against the live API.
  - The check sends `To`, not `VerificationSid` (security L2, an open follow-up; not exploitable because phones are unique).
- **`dev`** sends nothing. It accepts only `TIDEWATCH_OTP_DEV_CODE` (exactly 6 digits, compared in constant time). It is refused at start unless `ENVIRONMENT=local` (`Validate`), and refused again in `app.newOTPSender` (F8).
- **Logs.** Nothing of a Twilio request or answer, a phone or a code reaches a log or an error text.

### People (`/admin/users`, owner and staff)

`Person`:

```
{id, username, display_name, email, phone, status, role,
 plan: {id, name},
 must_change_password, created_at,
 created_by: {operator_id, username} | null,
 last_login_at, disabled_at, sessions_active,
 bots: {active, total},
 spend: {today_usd, last_7d_usd, allowance_usd, reached}}
```

**Person fields.**
- **`bots`.** `active` counts `kind = 'auto'` bots in `running | observing`; `total` counts every bot, `me` included.
- **`spend` (S4).** `today_usd` is Σ `model_calls.cost_usd` for the person over the Bangkok day; `last_7d_usd` is the same over the 7 Bangkok days ending today; `allowance_usd` is `plans.daily_model_usd`; `reached` is `today_usd ≥ allowance_usd` (SC-E2E004).
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
- **List.** Newest first (`created_at DESC, id DESC`). The opaque cursor (kind byte `P`) is bound to `q` and `status`.
- **`q`** is 1–80 code points, case-insensitive. It matches a substring of `username` or `display_name`, a prefix of `email`, or a suffix of `phone` (at least 3 digits).
- **`totals`** count every row, and `active` rows separately, independent of the query, in the same snapshot as the page.
- **Field rules.**
  - `username`: trimmed and lowercased, `^[a-z0-9][a-z0-9._-]{2,63}$`.
  - `display_name`: 1–80 code points, no control characters.
  - `email`: lowercased, at most 254 bytes, one `@`, a dot in the domain part, printable ASCII only.
  - `phone`: E.164 `^\+[1-9][0-9]{6,14}$`.

**Writes.**
- **Create** stores `role user`, `status invited`, `must_change_password true`, `plan founder` and `created_by_operator_id`, and writes `user_created`. It creates no bot, account or watchlist; `EnsureBots` does that on the person's first product request, at the plan's starting capital.
- **Temporary password** (`internal/auth/password/temporary.go`): four words from the embedded BIP-39 English list (2,048 words, MIT; `data/WORDLIST-SOURCE.md` and `data/WORDLIST-LICENSE` beside it), generated with `crypto/rand`. It matches `^[a-z]{3,8}(-[a-z]{3,8}){3}-[0-9]{2}$` and is 18–38 characters. It is returned only in the create and reset answers and is never stored, logged or audited in clear.
- **Reset** sets a new temporary password and the forced change, and revokes every session (`session_revoked {reason: password_reset, count}` with the operator actor). It writes `user_password_reset {user_id, via: "console"}`.
- **Disable** is one locked transaction:
  - the acting operator's row `FOR SHARE`, then the acting session's row `FOR SHARE`;
  - then `MeBotLockKey(user)`, the users row `FOR NO KEY UPDATE`, and the bot rows in ascending `bot_id`;
  - then `status = disabled` and `disabled_at`;
  - every session is revoked (`session_revoked {reason: user_disabled}`);
  - each running or observing auto bot is paused through the trading Pause path (`bot_status_changed {bot_id, from, to: "paused", reason: "user_disabled"}`, operator actor);
  - finally `user_disabled {user_id, bots_paused}`.
- **After a disable.** REST answers `401`, and the hub's next 60 s re-check closes the person's sockets `4401`. A login gets the same `401 invalid_credentials` as a wrong password (`login_failed {reason: "disabled"}`). A create, clone, resume or `EnsureBots` already waiting on the lock gets `401 unauthenticated`.
- **Enable** sets `active`, or `invited` when the person never signed in, and clears `disabled_at`. The bots stay paused. It writes `user_enabled`.
- **Every People write checks the actor under lock** (F5, G1). A write by an operator disabled, gone, or whose session was revoked or expired mid-request is `401 unauthenticated`: nothing is written and no temporary password is returned.
- **Ignored bodies.** The reset, disable and enable POSTs ignore a body rather than refusing it (an open follow-up).

### Operators (`/admin/operators`, owner only)

`Operator`: `{id, username, role, must_change_password, created_at, last_login_at, disabled_at, sessions_active}`. The phone is never returned.

| Route | Success | Errors |
|---|---|---|
| `GET /admin/operators` | `200 {items: [Operator]}`, `created_at ASC, id ASC`, no paging | `403 forbidden` for staff |
| `POST /admin/operators/{operator_id}/disable` | `200 Operator`; that operator's sessions revoked | `400 invalid_request {reason: "self"}`, `403`, `404`, `409 status_conflict`, `409 last_owner` |
| `POST /admin/operators/{operator_id}/enable` | `200 Operator` | `403`, `404`, `409 status_conflict` |

- **Refusal order:** `403` → `404` → `self` → `status_conflict` → `last_owner`. These are decided under row locks, so two owners cannot disable each other concurrently.
- **No create route.** Operators are added only by the CLI.

### Audit (`GET /admin/audit`, owner and staff)

`GET /admin/audit?type=&actor=&limit=&cursor=` → `200 {items: [Event], next_cursor}`, newest first, 50 per page (1–100). The cursor's kind byte is `A` and it is bound to `type` and `actor`.

**Event fields.**
- `Event` is `{id, occurred_at, type, actor, ip, request_id, detail}`.
- `actor` is `{kind: "user" | "operator", id, username}`, or `{kind: "system", id: null, username: null}`.
- `detail` is shown as stored (S17).
- `actor=` matches a username of either kind.
- **Detail rule.** No detail ever carries a password, hash, code, token, email, phone or display name. Details are built only by the typed constructors in `internal/audit`, and `TestAudit_NoSecrets` builds every one of them.

**The closed list of 34 types** (`audit.Types()`). A `type=` outside it is `400 {field: "type", reason: "invalid"}`.
- Existing (17): `user_bootstrapped`, `login_succeeded`, `login_failed`, `password_changed`, `password_reset`, `session_revoked`, `order_placed`, `order_cancelled`, `decision_skipped`, `bot_status_changed`, `bot_created`, `bot_cloned`, `bot_version_created`, `bot_run_requested`, `recommendation_declined`, `bot_promoted`, `post_mortem_labelled`.
- New (17): `operator_bootstrapped`, `operator_created`, `operator_login_succeeded`, `operator_login_failed`, `operator_otp_sent`, `operator_otp_failed`, `operator_password_changed`, `operator_password_reset`, `operator_session_revoked`, `operator_disabled`, `operator_enabled`, `user_created`, `user_updated`, `user_password_reset`, `user_disabled`, `user_enabled`, `user_activated`.

**New detail shapes and actors (S22: never both actor columns).**

| Type | Actor | `detail` |
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
| `session_revoked` (operator form) | operator | `{reason: user_disabled \| password_reset, count}` |
| `bot_status_changed` (operator form) | operator | `{bot_id, from, to: "paused", reason: "user_disabled"}` |

`login_failed` gained the reason `disabled`.

**Failed sign-ins store the raw typed username.** `operator_login_failed` with reason `unknown_operator`, and the product's `login_failed` with reason `unknown_user`, keep the typed username in `detail`, and `/admin/audit` shows it as stored (contracts r3 §6). Whether to keep or omit it is an open owner decision (AUDIT-RAW-USERNAME).

**Rollout rule (web README).** The web's Audit page reads `type` from the same closed list (`AUDIT_TYPES`) and shows "Events couldn't load." on any other type. A new audit type must reach the web before, or in the same release as, the service that writes it.

### Spend (`GET /admin/spend`, owner and staff)

`GET /admin/spend?day=` → `200 {day_bkk, ceiling_usd, ingest_usd, bots_usd, people: [{user_id, username, display_name, allowance_usd, today_usd, last_7d_usd, reached}]}`.
- **`day`** is optional (`YYYY-MM-DD`, default today in Bangkok). A future day, or one before 2026-01-01, is `out_of_range`. The console shows today only.
- **The two totals.** `ingest_usd` is `model_calls` with `user_id IS NULL`; `bots_usd` is the rest. Their sum equals `model_spend_daily` for the day (checked by an integration test).
- **`ceiling_usd`** is `MODEL_SPEND_DAILY_CEILING_USD`, rendered once at start to 6 digits (OQ-1). If unset, the service uses 1.00, which must match the bot's value.
- **`people`** lists every `users` row, disabled ones included, ordered `today_usd DESC, username ASC`.
- **Two figures that agree up to known edges.** Stats' "cost of decisions" still reads `bot_runs.counts.cost_usd` (statistics D10). Spend reads `model_calls`. They agree up to a crashed wake and estimates.

### Product contract changes (additive)

- `GET /auth/me`: `user` becomes `{id, username, display_name, role, must_change_password}`. The backfilled row's `display_name` reads its username.
- `GET /model-tiers`: each tier gains `entitled: boolean` as its last key. The route still creates nothing.
- `409 bot_limit_reached {limit}` on `POST /bots`, `/clone` and `/resume`: `limit` is now the plan's `max_active_auto_bots`, counted under `MeBotLockKey`.
- `400 invalid_request {field: "config.decision_tier", reason: "not_entitled"}` on `POST /bots`, `POST /bots/{id}/versions` and `POST /bots/{id}/clone` when the plan excludes the tier. A legacy v1 config counts as `none`. Precedence: body and grammar refusals, then `not_entitled`, then the `limits.*` value rules, then `409 bot_limit_reached`.
- `POST /bots` without `starting_capital` uses the plan's `starting_capital_thb`; `EnsureBots` opens `me` and Slack Water at it. The literals 10 and 1,000,000 left `internal/services/trading`; the remaining grep hits (section numbers, bases, windows) were reviewed.
- Any `/auth/register`, `/sign-up`, `/admin/register` or other unregistered path: `404 not_found` for every method, `OPTIONS` included.

### Gates and route groups

- **Product group** (64 gated routes and `GET /ws`): `NoStore → ReadyGate → BodyLimit → RequireSession → RequireRole("user") → RequirePasswordChanged`.
  - `RoleAdmin` was deleted, and `grep -rn RoleAdmin internal test cmd pkg` is empty: nothing accepts `admin` any more.
  - The hub's 60 s re-check closes 4403 on a role other than `user` and 4401 on a session that is gone or revoked, or whose user is disabled.
- **`/admin` group:** `NoStore → ReadyGate → BodyLimit(8 KiB)`.
  - The three sign-in routes sit outside the gates; CSRF still applies.
  - The rest go through `RequireOperatorSession → RequireOperatorRole(owner, staff) → RequireOperatorPasswordChanged`, and `/admin/operators/*` adds `RequireOperatorRole(owner)`.
  - The route walks count 64 gated product routes and **16 gated `/admin` routes**: 4 auth, 7 people, 3 operators, audit and spend.
- **Cookies.**
  - `tw_session`: users, 30 d absolute / 7 d idle, unchanged.
  - `tw_admin`: operators, `Path=/; Max-Age=604800; HttpOnly; SameSite=Lax`, `Secure` unless `ENVIRONMENT=local`; 7 d absolute / 12 h idle (`expires_at = least(last_seen_at + 12h, created_at + 7d)`); touched when `last_seen_at` is 60 s old.
  - Neither cookie ever has `Domain` or `SameSite=None`, and only the SHA-256 of a 32-byte token is stored.
  - A refusal clears only its own kind's cookie.
- **Logging.** `http_request` carries `operator_id` for an authenticated operator, as it carries `user_id` for a user.

### Error codes

- **New:** `otp_invalid` (401), `otp_unavailable` (503), `username_taken`, `email_taken`, `phone_taken`, `status_conflict` (with `details: {status}`), `last_owner` (409).
- **New `invalid_request` reasons:** `self`, `not_entitled`.
- **`forbidden` (403)** gained its first real use, on `/admin/operators/*`.

### Bot: allowance, tier entitlement, attribution (`tidewatch-bot`)

- **Evaluated-bots join.** `EVALUATED_BOTS` joins `users` and `plans` (an inner join that drops no bot), so each row carries `ownerUserId`, `dailyModelUsd` (`numeric(10,6)` as text) and `decisionTiers` (a closed list, else `RangeError`). It never reads `users.status` or any other plan field. A wake keeps the row it started with, so a plan change acts at the next wake.
- **Per-person daily allowance (S16).**
  - Per survivor the order is: the per-bot 25 % budget, then `spent_user + estimate ≤ dailyModelUsd`, then the calls, where the global ceiling's reservation sits.
  - `spent_user` is `scoutCostForOwnerDay`: the per-bot statement joined by `owner_user_id`, read lazily once per wake per pass. It is added to the wake's tally, any held decide, and the owner's other open wakes of the same Bangkok day (each amount counted once).
  - Over the allowance, that survivor and every later one of the wake, carried passes included, take the template thesis with no call and nothing reserved.
  - It fires `bots_user_budget_reached_total{tier}` and the warn log `bots_user_budget_reached {user_id, bot_id, run_id}` once per wake.
  - Exempt: tier `none`, `NO_SPEND_BUDGET` models, and a wake that already hit the per-bot budget or the ceiling.
  - **Fails closed.** A missing allowance or a failed owner read fails the wake before any further call. Two mutation-checked specs pin this (SF-1).
- **Tier entitlement (S15).** Once per wake, a stored model tier outside `decisionTiers` runs the whole wake as `none`: no call, nothing reserved, neither budget consulted, a template thesis, and `p` from the signals. It logs `bots_tier_not_entitled {bot_id, run_id, tier}` and counts `bots_tier_not_entitled_total{tier}` once. The version and its hash are unchanged, and a carried wake keeps its tier.
- **Attribution.** The scout stamps `bot_id` and `user_id = ownerUserId` on every call it collects. So the survivor transaction, `recordBotCalls`, a settled held decide and an abandoned wake's held decide all write both columns (`INSERT_BOT_CALL`). `modelCallValid` refuses a non-UUID id, and nothing is written then. `packages/signals/src` never sets the columns, and `model_spend_daily` is unchanged.
- **Metrics.** `bots_user_budget_reached_total{tier}` and `bots_tier_not_entitled_total{tier}` use tiers `jev`, `small_llm` and `large_llm`, are exported at 0, and carry no `bot_id` or `user_id` label.
- **No new bot variable.**

### CLI (`tidewatch-service`, same binary, same redaction and readiness rules)

| Command | Behaviour |
|---|---|
| `operator create --username <u> --role owner\|staff --phone <E.164>` | Reads the password from the first stdin line, else `TIDEWATCH_OPERATOR_PASSWORD`, and validates it against the policy. Inserts with `must_change_password = true` and writes `operator_created {via: "cli"}`. Prints `operator created: <username> (<role>)`. A taken username or phone exits 1. |
| `operator set-password --username <u>` | The auth package's one reset path on the operator kind (`auth.NewOperatorReset`). Rehashes, sets the forced change and revokes every operator session. Writes `operator_password_reset {via: "cli"}` and `operator_session_revoked`. |
| `user set-password --username <u>` | The former `admin set-password`. `admin set-password` stays as a deprecated alias for one release; it prints a deprecation line and keeps the `TIDEWATCH_ADMIN_PASSWORD` fallback. |

- **Exit codes.** A flag value that fails its rule exits 2 naming the flag, never the value. No argument is ever echoed.
- **Known gap (follow-up):** a CLI-created `staff` operator on an empty `operators` table stops the owner bootstrap.

### Configuration (names only; values live in `.env` and Vault)

| Variable | Rule |
|---|---|
| `TIDEWATCH_OPERATOR_USERNAME` | default `owner`; `^[a-z0-9][a-z0-9._-]{2,63}$` |
| `TIDEWATCH_OPERATOR_PASSWORD` | Tier-1 secret. Required while `operators` is empty: without it the service exits 1 naming the variable. Ignored with a warning once operators exist. Masked by value. |
| `TIDEWATCH_OPERATOR_PHONE` | E.164, required with the password |
| `TIDEWATCH_OTP_SENDER` | `twilio` (default) or `dev`; `dev` only with `ENVIRONMENT=local` |
| `TIDEWATCH_OTP_DEV_CODE` | exactly 6 digits; required with `dev`, forbidden with `twilio` |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID` | Required with `twilio`. The account SID and auth token are the basic-auth pair. `TWILIO_AUTH_TOKEN` is Tier-1 and masked by value. |
| `MODEL_SPEND_DAILY_CEILING_USD` | owner-approved new service variable (OQ-1); optional, default 1.00, parsed like the bot; must carry the bot's value |
| `TIDEWATCH_ADMIN_USERNAME`, `TIDEWATCH_ADMIN_PASSWORD` | retired: read, ignored, one warning. The username lost its `admin` default so that "set" is detectable. |

- **Redaction.** The redaction writer masks `TWILIO_AUTH_TOKEN` and `TIDEWATCH_OPERATOR_PASSWORD` by value, and `code`, `tw_admin` and every `*password*` key at any depth.
- **The bot** gains no variable.
- **The web** gains no runtime variable. Its e2e uses `BASE_URL`, `E2E_OPERATOR_USERNAME` (default `owner`), `E2E_OPERATOR_PASSWORD` and `E2E_OTP_DEV_CODE`; `E2E_ADMIN_*` and `e2e/.auth/credentials.json` are retired.

### Metrics and logs

- **Service metrics**, with closed labels, at 0 from startup:
  - `tidewatch_otp_sends_total{principal="operator", result=sent|send_failed|send_limited}`;
  - `tidewatch_otp_checks_total{principal="operator", result=ok|wrong|dead}`;
  - `tidewatch_operator_login_attempts_total{result=success|failure|rate_limited|otp_pending}`.
  - `principal="user"` arrives with Phase B.
- **Service logs**, ids, enums and counts only:
  - `bootstrap: created operator` and `bootstrap: skipped, operators exist`;
  - `person_created`, `person_reset`, `person_disabled {user_id, bots_paused}`, `person_enabled`;
  - `operator_login`, `otp_send` (operator id, verification SID, status), `otp_check_failed`, `operator_disabled`, `operator_enabled`.
  - `TestLogs_NoPersonData` plants an email, phone, display name, passwords and codes and scans the logs.
- **Bot:** the two metric families above and the two warn events. The bot's closed event list is now 18.
- **After deploy, watch:** `tidewatch_operator_login_attempts_total`, `tidewatch_otp_sends_total{result="send_failed"}`, `bots_user_budget_reached_total` and `bots_tier_not_entitled_total`. Production logs keep about 5 h and are not in VictoriaLogs; metrics are on vmsingle.

## Components

All console code is in `tidewatch-web/src/app/pages/admin/`, a lazy route tree with its own shell, store, guards and API service. The product's `AuthService`, `authGuard`, `guestGuard` and `/sign-in` sources are byte-identical to the base.

### Routes (S18)

| Route | Screen | Render |
|---|---|---|
| `/admin/sign-in` | `feat-sign-in/operator-sign-in.ts` (both steps in one component), behind `operatorGuestGuard` | **prerendered** (`app.routes.server.ts`), with the disabled-`<fieldset>` guard until hydration and the capture-phase submit guard |
| `/admin` | People (`feat-people/`) | client |
| `/admin/operators` | Operators (`feat-operators/`); no client role guard | client |
| `/admin/audit` | Audit (`feat-audit/`) | client |
| `/admin/spend` | Spend (`feat-spend/`) | client |
| `/admin/account/password` | `feat-change-password/console-change-password.ts` | client |
| `/admin/**` unknown | redirects to `/admin` | — |

- **Titles** read `<Screen> · Console · Tidewatch`.
- **Guards.** `operatorGuard` (`canActivateChild`) sends a signed-out visitor to `/admin/sign-in?next=`, a forced change to `/admin/account/password?next=`, and any other failure to the full-page "Tidewatch isn't responding." state.
- **`next`.** `sanitizeAdminNext` keeps only targets under `/admin`, never `/admin/sign-in`, else `/admin`.

### Stores, API service, interceptor

- **`OperatorAuthService`** (`data/operator-auth.service.ts`) is a root store that mirrors `AuthService`.
  - State: `status`, `operator`, `loadError`, `heldUrl`, `mustChangePassword`.
  - Methods: `load()`, `signIn` (returns the challenge), `verify`, `resend`, `changePassword`, `signOut`, `signOutEverywhere`, `clear`.
  - It holds no password or code and touches no storage.
  - The product imports it in exactly two files: `app.ts` (the not-responding state) and `auth.interceptor.ts`.
- **`AdminApi`** (`data/admin-api.service.ts`) owns every `/admin/users`, `/admin/operators`, `/admin/audit` and `/admin/spend` call. No component injects `HttpClient`.
  - Strict readers in `data/admin.model.ts` require every key and refuse an unknown status, role, actor kind or audit type.
  - Money stays a 6-digit string, formatted digit by digit in `util/console-format.ts`.
  - An unreadable answer is a status-0 "isn't responding" error.
- **Interceptor branch (S12).** `auth.interceptor.ts` branches on the request's **API path**, never on the route.
  - A `401` on an `/admin` path (except the three login routes) clears only the operator store and goes to `/admin/sign-in?next=`.
  - A `403 password_change_required` goes to `/admin/account/password`.
  - A product `401` never touches the operator store.

### Screens

- **Shell** (`shell/console-shell.ts`, `console-rail.ts`, `console-top-bar.ts`, `console-account-menu.ts`, S19). It reuses the product frame with a `console` host class.
  - The workspace card reads *Operator console* / *{role}*, the rail label `CONSOLE`, and the nav *People*, *Operators* (owner only), *Audit* and *Spend*. The mode line reads *Operators only* and the environment pill *Operator console*.
  - The breadcrumb reads `Console / <Screen>`.
  - The account menu reads *Signed in as {username} · {role}*, with *Change password*, *Sign out* and *Sign out everywhere*.
  - At ≤ 600 px the rail becomes a 4-column strip (3 for staff).
- **Operator sign-in** (`/admin/sign-in`), a full-page glass panel with the caption *Operator console*.
  - **Step 1** (*Sign in*): *Username*, *Password*, *Continue* (busy *Checking…*). No links, no theme switch, no sign-up.
  - **Step 2** (*Enter your code*):
    - "We sent a code to {phone_hint}."; a *Code* field (`inputmode="numeric"`, `autocomplete="one-time-code"`); *Sign in* (busy *Signing in…*);
    - *Resend code*, which reads *Resend in {n} s* and is `aria-disabled` until `resend_after`; the countdown number sits in `span.count` with tabular figures (VW1, `10851db`);
    - *Use a different account*.
  - **Messages.** The PRD's copy, verbatim: wrong code, a 10-minute expiry back to step 1, 429 seconds or minutes, `otp_unavailable`, not responding.
  - **Focus** moves to the new `h1` on each step change.
- **People** (`/admin`).
  - **Header:** the sub line *{n} people · {m} active* from `totals`, and *Add person*. A filter row with the search *Find by name, username, email or phone* (300 ms) and a *Status* chip select.
  - **Table** (`table.tide.people`, 860 px minimum), columns:
    - *Person* (display name over username);
    - *Email* (220 px maximum, ellipsis, full address in `title`);
    - *Phone* (E.164 grouped for reading);
    - *Status* (a neutral tag);
    - *Plan*;
    - *Last sign-in* (Bangkok time);
    - *Bots* `{active} active · {total}`;
    - *Spend today* `$x / allowance`, plus the neutral tag *At allowance* when `reached`;
    - *Actions* (*Edit*, *Reset password*, *Disable sign-in* or *Enable*), pinned right above 600 px and static at ≤ 600.
  - **States:** loading, error with *Try again*, empty with *Add person*, filter-empty, *Load more* and its busy state, and a load-more error toast. The list reloads after every write, and the row is replaced from the answer first.
- **People dialogs** (`add-person-dialog.ts`, `edit-person-dialog.ts`, `reset-password-dialog.ts`, `disable-person-dialog.ts`, `temporary-password.ts`, `util/person-form.ts`).
  - **Add person.** Username, display name, email, and a phone row: a native country `<select>`, Thailand +66 first and default (`util/countries.ts`, S20), beside a national number.
    - On `201` the dialog switches to the temporary-password state. Its `.secret-box` shows the username and the temporary password, with *Copy password*: it reads *Copied* for 2 s and falls back to selecting the text without the clipboard API.
    - The password lives in one signal of the dialog and is discarded on close.
    - A 38-character password wraps only at its hyphens; the secret row was fixed in VW2 (`10851db`).
  - **Edit** sends only the changed fields, with the username read-only.
  - **Reset password** confirms first, then shows the new temporary password. A `409` reads *Enable sign-in first.*
  - **Disable sign-in** confirms first, then toasts "{name} can't sign in. {n} bots paused." or "No bots to pause.".
  - **Enable** runs in the row. A `409` on either reloads the list and toasts "That changed already.".
- **Operators** (`/admin/operators`).
  - Columns: *Operator*, *Role* (tag), *Last sign-in*, *Status*, *Actions*.
  - *Disable* has a confirm dialog.
  - Toasts: "You can't disable yourself." and "The last owner can't be disabled.".
  - The note reads "Add an operator with the service's operator create command."
  - **Staff.** The rail hides the link, and a typed URL shows *Owner only* after the service's `403`.
- **Audit** (`/admin/audit`): a *Type* chip select over the closed 34-type list, an *Actor username* search, and the columns *When* (Bangkok time to the second), *Type*, *Actor* (with the kind under it), *IP* and *Detail* (key: value pairs, ellipsis, full in `title`). *Load more*.
- **Spend** (`/admin/spend`): three metric cards (*Ceiling*, *Ingest today*, *Bots today*), then *People* with the columns *Person*, *Allowance*, *Today*, *7 days* and *Status* (*At allowance* or a dash). Dollars show two decimals, and four under a cent (so $0.000032 reads $0.0000).
- **Console change password** (`/admin/account/password`): the product's forced and voluntary pattern, bound to `POST /admin/auth/password`.

### Product-side changes (§4.9.8)

- **Account menu** (`shell/account-menu.ts`): *Signed in as {display_name}*, with the username under it in `--text-3` when the two differ. It reads `display_name` leniently, falling back to the username.
- **Bots editor** (`feat-bots/editor/editor-tiers.ts`): an unentitled tier is greyed with the title *Not in your plan* and a visible "not in your plan" reason (H9). `entitled` is read leniently (absent means `true`).
- **Limit sentence.** The create dialog's sentence reads "You have {n} active bots. Pause one to start another." from `details.limit`. At a cap of 1 it reads "1 active bots" (the PRD's text, verbatim).
- **`not_entitled` in create and clone.** A `400 not_entitled` in the Create or Clone dialog still shows the generic "Couldn't create the bot. Try again.".
- **`/sign-in`** is unchanged. A zero-anchor assertion was added (`sign-in.spec.ts`).

### Styles and icons

- **`src/styles/components/console.css`** is one `@layer components`, imported after `stats.css`. Every selector is scoped under `.console`.
  - It has no literal colour, no `--up`, `--down` or `--z-*`, and no transition or animation; greps gate `pages/admin/` and the file.
  - Console pieces: `.console-caption`, `.code-field`, `.resend`, `.phone-row`, `.secret-box`, `.row-actions`, and `table.tide.people`, `.operators`, `.audit` and `.spend`.
  - It copies the ORCH-30 busy-button rule for the console's primaries.
- **Four new icons** in `shared/ui-icon/icons.ts`: `people`, `operators`, `audit`, `spend`. These are the one icon addition PRD §7.2 allows. There is no new token, colour, type step or motion.
- **`DESIGN.md`** gained "Console pieces", the states and captures, 16 decision rows (AR-W and OQ-W) and a refreshed source snapshot.

### e2e (`tidewatch-web/e2e`)

- **Projects:** `public`, `operator` (five mocked console specs: `operator-sign-in`, `people`, `operators`, `audit`, `spend`, on the fail-closed `/admin/*` mock in `support/admin.ts`), `operator-live` (one real-service test), `journey`, `authed-setup`, `authed`, `sign-out`.
- **The operator helper** (`support/operator.ts`) holds a worker-scoped operator session. It signs in through the API with the dev code, keeps `tw_admin` in its own cookie jar, uses Node `fetch` and never Playwright's request context (SEC-W-5), and logs out at teardown.
- **People per run.** `createPerson(operator)` posts `e2e-{run}-{n}` and returns the temporary password in memory only. The journey, `authed-setup`, `password.spec`, `sign-out.spec` and `operator-live` each create their own people.
- **Secret hygiene.**
  - Passwords and codes are typed only through `fillSecret`.
  - `playwright.config.mts` sets `PLAYWRIGHT_NO_COPY_PROMPT=1`, and `fixtures.ts` refuses to load without it.
  - The auto fixture `failureSnapshotsOff` strips failure snapshots.
  - Lint bans `beforeAll` and `afterAll`.
  - `fixtures.ts` pins Playwright to 1.63.x at load.
- **Captures:** `console__{screen}-{state}-{theme}-{width}.png` at 1440, 1100, 1080, 600 and 390 in both themes, with axe on every capture (36 states × 5 widths × 2 themes = 360 runs).

## Files touched

Lists come from each plan's per-step **Files**, the recorded ORCH patches, the review-fix records and the merged worktrees. They were not re-derived from a `git diff`. Every project also committed `.plans/accounts-roles.md` (created).

### tidewatch-migrations (PR #16, https://github.com/tidewatch-labs/tidewatch-migrations/pull/16, merge `080979d`)

- `migrations/20261028120000_accounts_and_roles.sql` (created)
- `scripts/check-disposable-db.sh` (modified)
- `README.md`, `CLAUDE.md` (modified)

### tidewatch-service (PR #18, https://github.com/tidewatch-labs/tidewatch-service/pull/18, merge `35177e1`)

- **Created:**
  - `internal/auth/otp/{sender,dev,dev_test,twilio,twilio_test}.go`, plus `testdata/twilio/README.md` and 10 fixtures (`send_ok`, `send_60203`, `send_60200`, `check_approved`, `check_pending`, `check_60202`, `check_20404`, `check_60200`, `check_20003`, `check_canceled`);
  - `internal/auth/challenge/{store,store_test}.go`;
  - `internal/auth/phone/{phone,phone_test}.go`;
  - `internal/auth/password/{temporary,temporary_test}.go` and `data/{wordlist-english.txt,WORDLIST-SOURCE.md,WORDLIST-LICENSE}`;
  - `internal/services/auth/{kind,operator,operator_test,recorder}.go`;
  - `internal/services/admin/{store,people,people_test,cursor,cursor_test,operators,operators_test,audit,audit_test,spend,spend_test}.go`;
  - `internal/services/trading/{entitlements,entitlements_test}.go`;
  - `internal/repository/postgres/{operator,operatorsession,operator_test,people,people_test,plan,plan_test,adminaudit,spend}.go`;
  - `internal/handlers/{admin_auth,admin_people,admin_operators,admin_audit,admin_spend}.go` and their `_test.go`;
  - `internal/cli/{operator,operator_test}.go`;
  - `internal/observability/metrics/operator.go`;
  - `internal/app/otpsender_test.go`;
  - `test/integration/{users,operator_login,people,people_lifecycle,operators,entitlements,admin_reads}_test.go`.
- **Modified:**
  - `internal/platform/postgres/{schema,schema_test}.go` (the pin to L);
  - `internal/pgtest/migrate.go`;
  - `internal/repository/postgres/{user,user_test,session,session_test,event,event_test,trading_test,signal_test,bot}.go`;
  - `internal/auth/session/{principal,lifetime,lifetime_test,cookie,cookie_test}.go`;
  - `internal/auth/throttle/{guard,guard_test}.go`;
  - `internal/services/auth/{service,login,login_test,session,session_test,password,password_test,fakes_test}.go`;
  - `internal/services/trading/{store,account,botcreate,botcreate_test,botversions,bots,bots_test,modeltiers,modeltiers_test}.go`;
  - `internal/services/bootstrap/{service,service_test}.go`;
  - `internal/services/realtime/{hub,hub_test}.go`;
  - `internal/handlers/{auth,auth_test,bots,bots_test,orders,orders_test}.go`;
  - `internal/httpx/authn/{context,session,session_test,gates,gates_test}.go`;
  - `internal/httpx/middleware/{logger,logger_test,securityheaders,securityheaders_test,cors_test,csrf_test}.go`;
  - `internal/httpx/response/{response,response_test}.go`;
  - `internal/observability/logging/{redact,redact_test}.go`;
  - `internal/observability/metrics/{metrics,metrics_test}.go`;
  - `internal/audit/{audit,audit_test}.go`;
  - `internal/config/{config,validate,secrets,config_test,secrets_test}.go`;
  - `internal/app/{router,router_test,app,servers_test,lifecycle_test,redis_test}.go`;
  - `internal/cli/{cli,cli_test,setpassword,setpassword_test}.go`;
  - `pkg/apperror/{codes,codes_test,apperror,apperror_test}.go`;
  - `test/integration/{main,ready,signals_fixtures,trading_fixtures,harness,fixtures,bootstrap,watchlist,market,realtime,realtime_slo,login,events,redaction,session,cli,orders,bots_caps,bot_weights,observability}_test.go`;
  - `scripts/integration-test.sh`, `.env.example`, `README.md`, `CLAUDE.md`.
- **The post-PR Twilio commits** (file lists from `git show --stat`):
  - `23d921f` (20 files): `internal/auth/otp/{sender,twilio,twilio_test}.go`, `internal/auth/otp/testdata/twilio/README.md`, `internal/config/{config,config_test,secrets,secrets_test,validate}.go`, `internal/app/{app,router_test,servers_test}.go`, `test/integration/{bootstrap,harness,redaction,session}_test.go`, `.env.example`, `README.md`, `CLAUDE.md`, `.plans/accounts-roles.md`.
  - `5c57438` (6 files): `internal/auth/otp/{twilio,twilio_test}.go`, `internal/config/{config,config_test}.go`, `test/integration/redaction_test.go`, `.plans/accounts-roles.md`.

### tidewatch-bot (PR #19, https://github.com/tidewatch-labs/tidewatch-bot/pull/19, merge `bd5e435`)

- `scripts/sql-integration.sh` (modified)
- `packages/bots/vitest.int.config.mts` (modified)
- `packages/bots/src/{store,pg-store,metrics}.ts`, `general/{models,scout,pass}.ts`, `testing/memory-store.ts` (modified)
- `packages/bots/src/general/{scout,pass}.spec.ts`, `testing/memory-store.spec.ts`, `metrics.spec.ts`, `logs.spec.ts` (modified)
- `packages/bots/src/{pg-store,general,pass}.int.spec.ts`, `packages/sim/src/pg-store.int.spec.ts`, `packages/signals/src/pg-store.int.spec.ts` (modified; the last is the only change under `packages/signals`)
- `README.md`, `CLAUDE.md` (modified)

### tidewatch-web (PR #23, https://github.com/tidewatch-labs/tidewatch-web/pull/23, merge `4725cb9`)

- **Created under `src/app/pages/admin/`** (each with its `.spec.ts`):
  - `admin.routes.ts`, `operator.guard.ts`, `operator-guest.guard.ts`;
  - `data/{operator-auth.model,operator-auth-api.service,operator-auth.service,admin.model,admin-api.service}.ts`;
  - `util/{admin-next-url,operator-error-message,console-words,countries,console-format}.ts` (`console-words.ts` has no spec);
  - `feat-sign-in/operator-sign-in.ts`;
  - `shell/{console-shell,console-rail,console-top-bar,console-account-menu}.ts`;
  - `feat-change-password/console-change-password.ts`;
  - `feat-people/{people,people-table,add-person-dialog,edit-person-dialog,reset-password-dialog,disable-person-dialog,temporary-password}.ts`, `feat-people/data/people.service.ts`, `feat-people/util/person-form.ts`;
  - `feat-operators/operators.ts`;
  - `feat-audit/audit.ts`, `feat-audit/data/audit.service.ts`;
  - `feat-spend/spend.ts`.
- **Created elsewhere:** `src/styles/components/console.css`.
- **Modified (app):**
  - `src/app/app.ts`, `app.spec.ts`, `app.routes.ts`, `app.routes.spec.ts`, `app.routes.server.ts`, `src/styles.css`;
  - `src/app/shared/auth/auth.interceptor.ts` (+spec), `shared/auth/data/auth.model.ts`, `auth-api.service.spec.ts`;
  - `src/app/shell/account-menu.ts` (+spec);
  - `src/app/shared/ui-icon/icons.ts`, `icon.spec.ts`;
  - `src/app/pages/workspace/data/bots.model.ts` (+spec);
  - `feat-bots/util/{bot-draft,bot-view,bot-dialog-view}.ts` (+specs), `feat-bots/editor/editor-tiers.ts` (+spec), `feat-bots/data/bots.service.ts` (+spec), `feat-bots/bot-dialog.ts` (+spec).
- **Created (e2e):** `e2e/src/support/{operator,admin}.ts`, `e2e/src/{operator-live,operator-sign-in,people,operators,audit,spend}.spec.ts`.
- **Modified (e2e):**
  - `e2e/src/support/{fixtures,screens}.ts`, `e2e/playwright.config.mts`, `e2e/eslint.config.mjs`;
  - `e2e/src/{journey,auth.setup,password,sign-out,sign-in,shell}.spec.ts`;
  - a skip-rename in 18 specs: `a11y`, `watchlist`, `chart`, `chart-live`, `market-watch`, `market-watch-live`, `market-watch-dialogs`, `bots`, `bots-editor`, `bots-live`, `paper-orders`, `trade`, `overview-portfolio`, `signals`, `signals-live`, `theme`, `viewport`, `stats`.
- **Docs:** `DESIGN.md`, `README.md`, `CLAUDE.md` (modified).
- **After the PR opened:**
  - `03d065c`: e2e only (`support/admin.ts`, `support/screens.ts`, and the audit, operators, people, spend and operator-sign-in specs);
  - `10851db`: `operator-sign-in.ts` (+spec), `console-words.ts`, `console.css`, `DESIGN.md`;
  - `a7498cd`: `DESIGN.md`;
  - `ce420a7`: the CI fix in `operator-sign-in.spec.ts`, which restores its spies before the real timers.

## Test plan

### Commands (each project root; CI runs the first of each)

- **Migrations:** `make migrate-validate`; `make check-disposable-db` ends `check-disposable-db: PASS` with ten assertion passes.
- **Service:**
  - `make ci` (vet → test-race → build) and `go vet -tags integration ./...`;
  - `make test-integration TIDEWATCH_MIGRATIONS_DIR=<tidewatch-migrations checkout>`;
  - `! grep -rn RoleAdmin internal test cmd pkg`;
  - `go list -deps ./internal/services/auth` must show no Prometheus and no gin.
- **Bot:** `pnpm nx run-many -t lint test typecheck build`; `TIDEWATCH_MIGRATIONS_DIR=<checkout> bash scripts/sql-integration.sh`.
- **Web:**
  - `pnpm nx test tidewatch-web`, `pnpm nx lint tidewatch-web`, `pnpm nx build tidewatch-web` (the build reports `Prerendered 2 static routes`, `/admin/sign-in` among them);
  - the e2e lint and `tsc-e2e`;
  - the literal-colour grep, and the hue grep (`--up`, `--down`, `--z-*`) over `pages/admin/` and `console.css`;
  - on a stack, `pnpm exec playwright test --project operator` (Chromium, one worker, with `BASE_URL`), then `operator-live` and the product projects with `E2E_OPERATOR_PASSWORD` and `E2E_OTP_DEV_CODE` set in the shell.

### Named acceptance tests (do not rename)

- **Service:**
  - `TestRouter_NoSignup`, `TestRouter_AuthRegister_NotFound`;
  - `TestRouter_ForcedChangeGatesNewRoutes` (64), `TestRouter_OperatorForcedChangeGatesNewRoutes` (16);
  - `TestGates_CrossPrincipal`, `TestGates_OperatorForcedChangeAllowList`, `TestOperatorCookie_Attributes`, `TestSessionPolicy_Lifetimes`;
  - `TestOperatorLogin_ChallengeThenCookie`, `TestOperatorLogin_IndistinguishableFailures`, `TestOTP_DeadChallengeTiming`, `TestOperatorVerify_Burst`, `TestOperatorVerify_DoubleSubmitRightCode`;
  - `TestChallengeStore_CapAndSweep`, `TestDevSender_AcceptsOnlyConfiguredCode`, `TestNewOTPSender_DevOnlyLocal`, `TestTwilioSender_RequestShape`, `TestTwilioSender_LogsNoSecrets`;
  - `TestTemporaryPassword_Shape`, `TestAudit_NoSecrets`, `TestAudit_ActorForms`, `TestAudit_ReasonSetsClosed`;
  - `TestEntitlements_*`, `TestHub_RecheckUserRole`, `TestAuth_Me_DisplayName`, `TestLogin_InvitedBecomesActive`, `TestLogin_DisabledUserIndistinguishable`;
  - `TestMetrics_OperatorSeries_ClosedLabels`, `TestConfig_SpendCeiling`, `TestSpendCeiling_Render`.
  - Integration: `TestOperatorLogin_EndToEnd`, `TestCrossPrincipal_Cookies`, `TestBootstrap_CreatesOperator` and its siblings, `TestPeople_Create`, `TestPeople_CreateConcurrent`, `TestPeople_DisablePausesBots`, `TestPeople_DisableClosesSockets4401`, `TestPeople_EnableLeavesBotsPaused`, `TestOperators_ConcurrentOwnerDisable`, `TestCLI_OperatorCreate`, `TestEntitlements_PlanLimits`, `TestAdminAudit_List`, `TestAdminSpend_Sums`, `TestLogs_NoPersonData`, `TestMetrics_OperatorSeries_ScrapeAtZero`, `TestReady_AccountsSchema_NotReady`.
- **Bot (exact Vitest titles):** "holds a person's bots to the plan's daily allowance across bots"; "allowance and per-bot budget are independent"; "writes bot_id and user_id on every bot model call"; "runs a tier the plan excludes as none for the wake"; "a carried wake keeps its tier after the plan changes"; "registers bots_tier_not_entitled_total at zero for the three tiers"; "pg store on L: bot calls carry bot_id and user_id".
- **Web e2e:** test titles carry the `FR-AR-*` ids.

### Results (from `verification.md`; local, CI and preview)

- **Migrations.** Harness PASS: 31 refusals over 29 constraints, 11 controls, 7 passes with L applied, ten assertion passes; L sha `1decf74c…03b7`. CI validate SUCCESS.
- **Service.**
  - At the last S1–S11 fix round: unit 41 packages ok; integration `ok` 518.479s, 0 FAIL, 0 SKIP (990 top-level PASS per the PR body).
  - After the Twilio change: `make ci` exit 0; integration `ok` 503.044s, 0 FAIL, 0 SKIP. CI green on `5c57438`.
- **Bot.** Unit 381 of 381. Integration: bots 42, ingest 14, market-data 16, sim 18, signals 19, worker 2, all passed. `sql-integration: PASS` with `required schema version 20261028120000`. CI green.
- **Web.**
  - Unit 176 files, 6,487 tests (6,488 after `10851db`, and 6,488 three times after the CI fix); lint and build pass.
  - CI went green on `ce420a7`. The earlier failures were order-dependent `toast.spec` hook timeouts, caused by a spec restoring spies after the real timers.

**Acceptance status, 51 IDs, 0 failed:**

| Result | Count | IDs |
|---|---|---|
| verified (unit) | 4 | SVC-003, SVC-014, BOT-001, BOT-003 |
| verified (integration) | 18 | MIG-001…003; SVC-001, 002, 004–013, 015, 017; BOT-002 |
| verified (static) | 1 | WEB-014 |
| verified (review) | 3 | MIG-004, SVC-018, BOT-004 |
| verified (preview) | 18 | SVC-016; WEB-001…013; E2E-001, 002, 003, 005 |
| verified (preview), with deviation | 1 | E2E-004 (D-E2E004, kept as built) |
| not in this build (Phase B) | 6 | B-001…006 |

### Preview runs (2026-10-28 18:48Z → 2026-10-29 02:08Z; per-run database at L; `dev` sender)

| Run | Web build | Result |
|---|---|---|
| E2E-005 on a copy of the retained preview database | — | PASS; counts identical before and after L |
| `operator` run 1 | `0c99f26` | 507 passed, 20 failed: three test bugs (breadcrumb text, countdown regex, forced-change step), fixed in `03d065c` |
| `operator-live` | `0c99f26` | 1 of 1 passed (25 s), sign-in path `bootstrap-and-change` |
| product projects | `0c99f26` | 1,427 tests: 1,412 passed, 11 failed, 4 skipped. The 11 are pre-existing `@hook` chart tests that need the dev build; the 4 are gated by environment flags. |
| `operator` r2 | `0c99f26` + e2e `03d065c` | 527 of 527 |
| `operator` r3 (final) | `10851db` | 527 passed, 0 failed, 0 skipped. 360 captures; 360 axe runs, 0 violations; no horizontal page scroll in any capture; 424 contrast pairs, lowest 4.65 (`aside.rail .nav-label`, light). |
| E2E-002 transcript | `10851db` (service `d4d5104`) | PASS |
| E2E-004 | service `d4d5104` | PASS with deviation D-E2E004 |

**What each E2E check showed.**
- **E2E-001 (fresh stack).**
  - The operator bootstrapped and signed in with the dev code, made the forced change and added a person. The temporary password was shown once.
  - The person signed in at `/sign-in`, changed the password and landed on Overview. Bots showed Me and Slack Water at ฿1,000,000, and People showed the person *Active* with `1 active · 2`.
  - SQL: goose latest `20261028120000`; one operator (`owner`, owner); the person is user / active / founder with `created_by_operator_id` set. The expected event sequence was present.
- **E2E-002 (cross-principal).**
  - The person's `tw_session` on `GET /admin/users` → 401.
  - The operator's `tw_admin` on `GET /bots` → 401, and on the `/ws` upgrade → 401 with no 101.
  - No `Set-Cookie` on the refusals, and both cookies still worked afterwards.
- **E2E-003 (disable).**
  - The person's socket closed 4401 **20,594 ms** after the disable (bound 60,000 ms), and their next REST call landed on `/sign-in`.
  - SQL: `session_revoked {user_disabled}`, `user_disabled {bots_paused: 1}`, and `bot_status_changed {running → paused, user_disabled}` for Slack Water.
  - After *Enable*, the person signed in again and Slack Water stayed paused.
- **E2E-004 (allowance).**
  - At allowance 0.500000, bot B wrote `bot_decide` (Jev, $0.000032) and `bot_thesis` rows, both carrying `bot_id` and `user_id`.
  - At 0.0001, bot C's wake proposed with `thesis_source` template, 0 model calls and null `p`/`model_id`. `bots_user_budget_reached_total{tier="jev"}` went 0 → 1 with one warn line, while the per-bot budget and ceiling counters stayed 0.
  - The Spend leg was the deviation: no tag at 0.0001; *At allowance* at 0.000032 (SC-E2E004).
- **SVC-016 (metrics).** All 10 operator series were at 0 before the runs. After them they read failure 1, otp_pending 5 and success 5; checks ok 5; sends sent 5. These equal the audit events in the same database.

### Not verified or partial (stated separately)

- **The Twilio sender against the live API.** Never run, in preview or production. The owner's first production sign-in is the smoke test.
- **Screens against the real service.** Operators, Audit and Spend, and Edit and Reset password, ran only against the e2e mock. Their service routes have integration evidence.
- **The tier entitlement on a real wake.** `bots_tier_not_entitled_total` read 0 throughout.
- **The Down of L** ran only in the disposable harness.
- **Builds.** `operator-live`, the product projects and the metrics scrape ran on web `0c99f26`, not re-run on `10851db`. Between the two, the app changed only `operator-sign-in.ts`, `console-words.ts` and `console.css`.
- **The leak scan** (0 files with the operator password, the dev code or a `tw_admin` value across 4,781 evidence files) predates OP-R2, OP-R3 and the E2E-002 transcript.
- **`a7498cd`** (DESIGN.md only) had no reviewer re-read.
- **Production after deploy.** Verified only by `/info`, `/ready`, the bootstrap log line, the bot's logs and the rendered `/admin/sign-in`. No operator has signed in to production.

### Manual reproduction (production, the owner's first sign-in)

1. Open `https://tidewatchtrade.com/admin/sign-in`.
2. Sign in as `owner` with the bootstrap password from Vault (`TIDEWATCH_OPERATOR_PASSWORD`).
3. Expect an SMS code at `TIDEWATCH_OPERATOR_PHONE`. This is the first live Twilio Verify send; watch `tidewatch_otp_sends_total{result="send_failed"}` and the `otp_send` log line.
4. Enter the code. The console forces `/admin/account/password`; choose the new password.
5. People should list the backfilled owner row (`admin`, *Active*, *Founder*, no email or phone).
6. Then remove `TIDEWATCH_OPERATOR_PASSWORD` and `TIDEWATCH_ADMIN_PASSWORD` from Vault.

## Open questions

### Owner actions still open

- **The first production operator sign-in** (above). It is the live Twilio smoke test that OA-TWILIO-SMOKE asked for before rollout; that test was not run before the rollout.
- **After that sign-in,** delete `TIDEWATCH_OPERATOR_PASSWORD` and `TIDEWATCH_ADMIN_PASSWORD` from Vault (`apps/tidewatch-service/prod`). While they stay set, the service ignores both and logs a warning for each at start.
- **tidewatch-kubernetes.**
  - The service chart still sets `TIDEWATCH_ADMIN_USERNAME`. It only causes the retired-variable warning at start.
  - `scripts/seed-vault.sh` still prompts for `TIDEWATCH_ADMIN_*` and asks for no operator or Twilio values.
- **Optional (OA-SPEND-CHART, OA-SPEND-COMPOSE).** Add `MODEL_SPEND_DAILY_CEILING_USD` to the tidewatch-service chart, matching the bot chart's `modelSpendDailyCeilingUsd "1.00"`. Add it also to the root `docker-compose.yaml` service environment, where today it reaches only the bot. Unset, the service shows 1.00, which equals the bot's current value.
- **Root `.env.example` and compose** (owner-maintained) need the new service lines with `dev`; `TIDEWATCH_ADMIN_*` should be removed from the example.
- **Preview leftovers.**
  - Docker volume `acct-c04f668a-e2e005-pgdata` (OA-E2E005-VOLUME), kept for the owner to keep or remove.
  - The retained per-run volume `forge-0199b29a-acct-c04f668a_tidewatch-pgdata`. It holds the e2e people (there is no delete route), plan `e2e004` at 0.000032, person `e2e004-mvswcncud49f` and the observing bots E2E-004 A/B/C.
  - The preview stack, last recorded as running at `http://127.0.0.1:50850/`.

### Open owner decisions

- **VW3.** The Edit country select (150 px) shows "United States and C" and hides `+1` above 600 px (`console.css`, `countries.ts`). Either change the visible copy to put the dialling code first, which needs the owner's sign-off, or widen the select.
- **AUDIT-RAW-USERNAME.** `/admin/audit` shows the raw typed username stored in `operator_login_failed` (`unknown_operator`) and `login_failed` (`unknown_user`) details. Keep or omit.
- **COPY-SIGNOFF.** Copy the PRD did not give, accepted as written and listed in the web PR:
  - the unreadable-201 and unreadable-200 lines on *Add person* and *Reset password*;
  - the reused product failure lines for People actions;
  - the People-table accessibility names and the faint dash for a missing email or phone;
  - the Operators, Audit and Spend region labels, headings and the CLI note;
  - the generic "Couldn't create the bot" line for a `400 not_entitled`;
  - "1 active bots" at a cap of 1.
- **Bot security N-1 (needs a decision).** A crashed wake's committed spend drops out of the person's allowance sum, a PRD-accepted edge. The options are `max(today sum, attributed model_calls sum)` or a restart sweep.

### Sibling builds

- **learning-loop (migration M) and signals-context (migration N)** were built against `main` before L merged. The settled order is L → M → N. **Both must update their branches onto the new `main`** (with L) and re-pin their `RequiredSchemaVersion` and harness lists after L, before they merge.
- The local primary checkouts need `/forge-sync` to pick up the four merges.

### Recorded follow-ups (from the PR descriptions and review records)

- **Service:**
  - Security L1: code sends with an unknown outcome are refunded, which lets a password holder bypass the 30 s wait and the 3-per-10-minutes limit. Refund only on a definite 4xx.
  - Security L2: the Twilio check should send `VerificationSid`, not `To`.
  - The race `401` (a write by an operator disabled or revoked mid-request) sends no clearing cookie.
  - `resend_after` truncation; resends are not audited; the README names an unused reason.
  - The reset, disable and enable POSTs ignore a body.
  - The audit actor filter cannot use the actor indexes.
  - The `operator_id` log field is ambiguous between actor and target.
  - A CLI-created staff operator on an empty table blocks the owner bootstrap.
  - `admin.New` accepts nil dependencies while `NewOperators` panics.
  - The `PlanEntitlements` type assertion; the clamp class list; `EnsureBots` ignores the plan cap.
  - `metrics` imports `services/auth` (move the port to a small shared package if a cycle threatens).
  - Contracts r3 §7 and §11 still read "Source pending OQ-1" (stale).
- **Web:**
  - The Operators component is its own store; move it to `feat-operators/data/operators.service.ts`.
  - Graduate `NO_VALUE` and `DISPLAY_TIME_ZONE` out of `feat-overview/util`; `admin-next-url.ts` sits in the initial bundle.
  - `[0.00995, 0.01)` renders `$0.0100`, and sub-cent spend reads `$0.0000`.
  - There is no distinct line when the code is accepted but the follow-up `/admin/auth/me` fails.
  - The `fillSecret`-only guard belongs in the e2e lint, and the README shows a password inline on a command line (pre-existing).
  - A temporary password arriving after the user leaves the screen is lost.
  - Optional R3-A1 (`min-width: 2ch` on the countdown number) and R3-A2.
  - Promote the busy-button rule to `button.css`.
  - The 11 `@hook` chart tests fail on a production-build preview; use `--grep-invert @hook`.
- **Bot:**
  - Make `ScoutWake.bot` plan fields required.
  - Check both ids at wake start.
  - Take `user_id` from `bots.owner_user_id` in SQL.
  - A mid-pass disable leaves the bot running for the rest of that pass, as a user Pause does.
  - Put `MemoryPlan` and `FOUNDER_PLAN` on the testing barrel; make the memory store mirror L's foreign keys.
- **Migrations:** five pre-L harness summary claims overstate: FR-ZB-MIG-001, FR-BA-MIG-002, FR-SIG-MIG-001, FR-SIM-MIG-003 and FR-ZB-MIG-003.
- **Outside the build:**
  - `tidewatch-apis`: `/admin/*` may get an api-spec-generator pass.
  - `documents/` 05 §1, §2 and §11 and research brief §7 should be amended by the owner (D17).
  - Reserving the bots' share of the ceiling from ingest is still a separate open fix (an intent non-goal). Two people at $0.50 a day can still starve ingest.
  - Phase B (`FR-AR-B-001…006`) waits on the owner's go and on the owner's row having email and phone.

## Cross-cutting links

- [[auth-model]]: the operator principal, `tw_admin`, the code step, the challenge store, role `user` and the gate chains change this page's contract.
- [[request-protection]]: CSRF and CORS are unchanged and now cover `/admin/*`; `Cache-Control: no-store` on `/admin`.
- [[centralized-migrations]]: migration L, the pin moving J → L (K never pinned), the SPEC-2 Down, and the L → M → N order.
- [[foundation-auth]]: the seeded `admin` and `TIDEWATCH_ADMIN_*`, now retired and backfilled.
- [[model-routes-and-spend]]: `model_calls.bot_id` and `user_id`, the per-person allowance beside the 25 % per-bot budget, and Spend's ingest and bots split.
- [[bots-engine]]: the evaluated-bots join to `plans`, S16 and S15.
- [[bot-versions-and-runs]]: the plan's active-bot cap, the `not_entitled` tier refusal and the plan's starting capital.
- [[realtime-websocket]]: the hub re-check on role `user`; a disabled person closes with 4401.
- [[paper-trading]]: `EnsureBots` at the plan's starting capital; disable pauses through the Pause path.
- [[statistics]]: Stats' cost of decisions still reads `bot_runs.counts.cost_usd`.
- [[design-system-decisions]]: `console.css`, the four icons, the AR-W and OQ-W decisions, VW1–VW3.
- [[forge-preview-gateway]]: the preview ran with the `dev` sender and a per-run database.
- New pages the build prompt names for this pass: `accounts-and-roles` (overview) and `operator-console`.
