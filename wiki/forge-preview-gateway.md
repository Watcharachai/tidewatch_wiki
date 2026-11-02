# Forge preview gateway

**Summary**: The preview publishes one dynamic loopback port, so a Caddy gateway is the single browser entry. It serves runtime config, proxies `/api/*` to the service and everything else to the web app, rewrites Origin only for exact same-origin loopback requests, and answers 421 to any non-loopback Host (DNS-rebinding defence). The bot-activity feature (2026-10-10) ran its end-to-end checks on an isolated preview in three phases and records two durable operating notes: the e2e journey spends the admin's one-time forced password change once per database, and the admin password is restored through the service CLI. Signals-ingest (slice 3a, 2026-10-11) ran on an isolated preview with the owner's Jev, OpenRouter and Finnhub keys in the Forge secrets file. Its notes: a key change needs a full `up --refresh`, every refresh changes the port, and the owner now signs in first with their own admin password. **Since the signals page (slice 4, 2026-10-12), previews share one retained workspace database volume.** At the owner's request, the build moved to Forge's updated isolated+retain behaviour. New runs mount a stable `forge-preview-<hash>_tidewatch-pgdata` volume, while existing runs keep their per-run volume. The signals day control (2026-10-14) ran on that shared volume. Its first `up` failed on an unresolved migrations setup token, and passed once the run mapping was extended to the service, bot and migrations worktrees. Charting (2026-10-15 to 2026-10-16) ran on the same shared volume and added a per-run development-build web and gateway (PV0) beside the production preview, because its dev-only test hook is absent from the production image. Bots (slice 6, 2026-10-21) ran on the same shared volume (`bots-1c6ff8ae`), refreshed once for FU-1, and left three E2E bots running or observing there, so any later preview on that volume evaluates them. **Accounts and roles (2026-10-28 to 2026-10-29) did not use the shared volume.** It ran on a per-run isolated, retained database (PREVIEW-DB), because migrations L, M and N carry fixed goose versions from unmerged branches. It used the `dev` code sender, so Twilio never ran. It also retired the admin-password operating notes above for the e2e: the suite now signs in as an operator with the dev code and creates its own people per run, so no run spends a shared user's forced change. **The learning loop (2026-10-28 to 2026-10-30) also ran on a per-run isolated, retained database**, `forge-0199b29a-ll-f3bdc8b0`, at M without L. After the merges with L it was refreshed with L applied out of order (`goose -allow-missing`) for the whole-suite PV6 run. Its seeded `pv4-learning` user and 11 bots stay there (OD-PV4-1). Its preview bot held the production Alpaca key and took production's single Alpaca stream during the production rollout, so that container must stay stopped while production runs.

**Sources**: `raw/2026-10-05-foundation-auth.md`; `raw/2026-10-07-market-data.md`; `raw/2026-10-07-fix-xau-feed-binance-th.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-14-signals-day-control.md`; `raw/2026-10-16-charting.md`; `raw/2026-10-21-bots.md`; `raw/2026-10-29-accounts-roles.md` (the accounts-and-roles preview and the e2e credential change only); `raw/2026-10-30-learning-loop.md` (the learning-loop preview and its production-key lesson only)

**Last updated**: 2026-10-31

---

## Why a gateway (D16)

The Forge preview publishes one dynamic loopback port, so a `caddy:2-alpine` gateway (`.forge/docker/templates/preview-gateway/Caddyfile`) is the single browser entry, on `:8080`. It lets the preview run the app same-origin even though the owner compose runs web and API on separate origins (see [[request-protection]]) (source: raw/2026-10-05-foundation-auth.md §Concept, D16).

## Routing

- `GET /config.json` returns `{"apiBaseUrl":"/api"}` with `Cache-Control: no-store`.
- `/api/*` has the prefix stripped and goes to `tidewatch-service:3000`.
- Everything else goes to `tidewatch-web:4200` with `Host` preserved and `X-Forwarded-Host` dropped.
- The Caddyfile sets `admin off`, `auto_https off` and no access log.

(source: raw/2026-10-05-foundation-auth.md §Concept, D16; §Components, Workspace root)

## Origin rewrite

On `/api/*` the gateway rewrites `Origin` to `http://localhost:4200` only when the Origin exactly equals `http://<request host:port>` **and** the Host is loopback. Any other Origin passes through unchanged, so the service still rejects it. This was assumption A6, validated by curl (same-origin accepted, foreign Origin 403) and re-checked after the rebinding fix. `state.json` still lists A6 as pending, but `verification.md` is authoritative (source: raw/2026-10-05-foundation-auth.md §Concept, D16 and A6; §Open questions).

## DNS-rebinding fix

After the workspace-root security review warned about DNS rebinding, the gateway was changed to answer `421 Misdirected Request` for any non-loopback Host, before routing. Consequences:

- The preview exercises only the same-origin path. The cross-origin path is verified by the service tests and FR-E2E-002 on a disposable copy of the owner compose.
- No product code branches on "preview". The service's `CLAUDE.md` forbids the word in any Go source.

The 156-test E2E suite was run before and after the fix with secret scans at 0 hits, and FR-INFRA-006 confirmed rebinding Host gives 421, same-origin gives 401/400, CSRF gives 403, register gives 404 and metrics gives 404 (source: raw/2026-10-05-foundation-auth.md §Concept, D16; §Test plan, Stages).

## WebSocket upgrades through the gateway (slice 1)

The web client derives its socket URL from `apiBaseUrl`, so on the preview it connects to `/api/ws`, which the gateway strips to `/ws` on the service with the same Origin rewrite. FR-MD-INFRA-003 verified it through the gateway: `/api/ws` gave `401` without a cookie, `101` with a session, and `403` for a foreign or missing Origin, so the rewrite does not weaken the service's `origin_rejected` check. See [[realtime-websocket]] (source: raw/2026-10-07-market-data.md §Concept, O7; §Components, tidewatch-web Data layer; §Cross-cutting links).

## Forge definition

`.forge/docker-compose.json`, synced with `forge-setup-docker-compose`:

- Projects: `tidewatch-web` and `tidewatch-service` map to their own services. In slice 0 `tidewatch-bot` mapped to none because the worker was a connect-and-exit check; since slice 1 it is a preview service (see "Slice 1 changes" below).
- Base services: `tidewatch-service`, `tidewatch-web`, `redis`, `preview-gateway`.
- `database.required: true`; `isolated` mode adds `db` and `migrate`, with `migrate` built from `{{project:tidewatch-migrations}}` (see [[centralized-migrations]] for why this will fail in future runs).
- Secrets come through `env_file` (raw format) from `.forge/docker/secrets/tidewatch.env` (file mode 0600, directory 0700), with keys `POSTGRES_PASSWORD`, `TIDEWATCH_ADMIN_PASSWORD` and `DATABASE_URL`. The values are never recorded in the wiki or printed.
- `preview: {service: preview-gateway, port: 8080, path: "/"}`. `existing` database mode is not configured.
- Start: `docker-compose-cli up --run <run> --database isolated --retention retain`; the browser entry is the gateway's dynamic loopback port.

(source: raw/2026-10-05-foundation-auth.md §Components, Workspace root and Operations)

### Slice 1 changes

`.forge/docker-compose.json` was re-synced through `forge-setup-docker-compose` (discover, candidate, sync, status `current`):

- `tidewatch-bot` is a preview service, built from `{{project:tidewatch-bot}}`, with `ENVIRONMENT=local`, `REDIS_URL`, `METRICS_PORT 9091`, the `/ready` healthcheck, `restart: unless-stopped` and `stop_grace_period 15s`.
- The isolated overlay gives the bot the secrets `env_file` and a `depends_on` on `migrate` completing. The isolated `db` runs with TimescaleDB telemetry off.
- The secrets file now also holds the owner's Alpaca keys; the OANDA lines are empty and stay empty, because OANDA is unavailable for the owner's region and gold is priced from Binance TH since the XAU fix (see [[market-data-worker]], [[gold-feed-xaut-proxy]]). The owner adds provider keys personally and Claude never handles them (OWNER-3).
- The XAU fix acceptance ran on its own preview, compose project `forge-0199b29a-fix-xau-feed-649e2a7a` (isolated DB, retained volumes; migrations `5831a72`, bot `989214d`, service `734ce35`, web `a9459e0`, Alpaca keys, OANDA pair empty).

(source: raw/2026-10-07-market-data.md §Components, Workspace root; §Concept, OWNER-3 and Preview findings 2; raw/2026-10-07-fix-xau-feed-binance-th.md §Concept, The correction; §Test plan, Preview acceptance)

## Owner decisions about the preview

- OWNER-7: preview database `isolated`; preview volumes retained.
- OWNER-8: at the owner's request the orchestrator generated the preview secrets file; the owner then set `TIDEWATCH_ADMIN_PASSWORD` personally and the generated admin value was removed.
- OWNER-9: after testing sign-in on the preview, the owner asked for the merge.
- The preview is retained. Its admin was restored to the owner's password through the CLI with the forced change pending, and the `e2e/.auth` credentials were deleted.

(source: raw/2026-10-05-foundation-auth.md §Concept, Other recorded decisions; §Test plan, Stages)

Slice 1 (OWNER-3): isolated database, retained volumes, telemetry off. The preview ran as compose project `forge-0199b29a-mdata-d9d3e428` and was restarted several times on new dynamic ports as bot fixes and keys landed. The Playwright journey spends the forced password change, so at the owner's request the preview admin was set back to the original bootstrap password through `POST /auth/password` (source: raw/2026-10-07-market-data.md §Concept, OWNER-3; §Test plan, Stages).

## Bot-activity preview (2026-10-10)

The bot-activity feature (see [[bot-activity]]) verified its four end-to-end IDs on an isolated preview: compose project `forge-0199b29a-bact-642f95ae`, a fresh database at migration G, volumes retained.

- **Phase A** (08:29–08:49Z, preview `:50245`; web image `de44595`, suite from `d44f655`, service `14ce781`, bot `b9d6d5e`, migrations `a474a77`). Full suite 691 passed / 0 failed / 1 skipped (the gated pause). The first-sign-in journey ran here and spent the admin's one-time forced change. A secret scan of 1,440 files found 0 hits (positive control 2). `EnsureBots` created both bots at 08:30:15Z.
- **Phase B** (independent E2E-003/004). The gated journeys failed on two test defects (D1, D2). While the whole worker was down, every Watch *Next* read "— no session state", because `px:last` comes from the stopped worker's status publisher.
- **Phase C** (after ORCH-14; preview `:49257`, web `5b8cb7c`, database kept). Suite 690 / 0 / 1, with the journey left out because the forced change was already spent. `bots.spec.ts` 260/260, captures byte- and pixel-identical to Phase A, and the gated Pause/Resume passed once. End state: 7 runs, 0 failed, `/api/ready` 200.
- **Owner-session live validation** (about 13:37–13:42Z, read-only, as the owner), then the owner's "merge the PRs in order".
- **E2E-003 method deviation.** The whole bot container was stopped for 148.5 s, because `MARKET_DATA_COLLECTORS` could not be changed without editing helper-managed compose files.

(source: raw/2026-10-10-bot-activity.md §Test plan, Preview phases and Acceptance status; §Concept, Stage)

**Operating notes.**
- **The e2e journey spends the admin password.** The first-sign-in journey performs the admin's one-time forced password change to a random journey password, kept in the git-ignored `e2e/.auth` plus a 0600 copy for later phases. Afterwards the owner's `TIDEWATCH_ADMIN_PASSWORD` (from `.forge/docker/secrets/tidewatch.env`) no longer signs in.
- **Restoring it.** At the owner's request (11:45Z) the orchestrator ran the service CLI `admin set-password --username admin`, which reads `TIDEWATCH_ADMIN_PASSWORD` from the environment and never prints it. The reset revoked all sessions, so `e2e/.auth` became stale, and it leaves `must_change_password = true` by app design. The owner typed the password personally; the permission classifier blocked materialising it.
- **The journey runs once per database.** On a kept database it cannot run again. Later phases ran the suite with `--no-deps` and re-ran `authed-setup` (journey password) before each step, because `sign-out` ends the saved session.
- **Left running.** At AWAITING_MERGE the preview was kept running for manual testing at `http://127.0.0.1:49257/`. Its teardown and the removal of the e2e credential files are not recorded in `state.json`.

(source: raw/2026-10-10-bot-activity.md §Test plan, Preview operational notes; §Open questions, Preview state)

## Signals-ingest preview (2026-10-11)

The signals-ingest feature (see [[signals-ingest]]) was verified on an isolated preview: compose project `forge-0199b29a-sig-d1c18e46`, a fresh database migrated to H, and 10 sources with 8 enabled. It ran with the owner's Jev, OpenRouter and Finnhub keys and no SET key.

| Result | Preview | Bot |
|---|---|---|
| First signal, P1 | refresh 2, `:52646` | `8ee0b71` |
| P2 | refresh 3, `:58693` | `f786102` |
| BRN-011 eval run 3 | refresh 4, `:60014` | `53cb76d` |
| E2E-005 | refreshes 5 and 6, `:60210` (ceiling 0.01) and `:60236` (restored) | `53cb76d` |

At merge, the preview ran migrations `dd7e150`, service `b9de179`, bot `53cb76d` and web `534e140` at `http://127.0.0.1:60236/`. Its teardown is not recorded.

**Operating notes.**
- **Each refresh changed the port.** The preview was refreshed several times as bot fixes landed; the table above maps each result to its refresh.
- **Provider keys.** The owner added the Jev, OpenRouter and Finnhub keys to the Forge secrets file and left SET empty. A bot-only recreate kept a stale secrets snapshot, so a **full `up --refresh`** was needed for the new keys to reach the bot. The key values are never recorded in the wiki or printed.
- **Owner-first admin sign-in (PV-3).** This time the owner signed in first with their own new admin password, then shared it for e2e through a file. The orchestrator copied the file into `e2e/.auth/credentials.json` without reading or printing it. The forced-change journey was excluded, because the owner had already spent it.
- **Preview-only data changes.** PR Newswire was polled every 900 s on the preview only (PV-2); the merged seed keeps 120 s. The spend ceiling was lowered to `0.01` and restored for E2E-005.
- **Timestamps.** Some `state.json` log entries stamped 13:20Z–17:30Z that sort before 09:50Z are Bangkok local times mislabelled Z. They are left as written; the acceptance times come from evidence files.

(source: raw/2026-10-11-signals-ingest.md §Test plan, Preview operational notes; §Concept, Stage, Verified on a preview; §Concept, PV-2 and PV-3; §Test plan, Acceptance at merge)

## Signals-page preview and the shared retained workspace volume (2026-10-11 to 2026-10-12)

The signals page (see [[signals-page]]) started on an isolated, fresh preview and moved to a shared database volume mid-run.

- **First preview.** Run `sigp-4081ec46` (compose project `forge-0199b29a-sigp-4081ec46`, `http://127.0.0.1:54375/`) came up at 22:46Z on 2026-10-11. It was isolated and fresh, migrated to I, with 6 containers healthy. The worktree mapping was extended to the bot at base `a6e39e0`. Ingest was live (90 documents in the first minutes), but there were 0 signals.
- **Owner sign-in failed there,** as expected on a fresh database: the admin is bootstrapped from `TIDEWATCH_ADMIN_PASSWORD` with `must_change_password = t`.
- **The move to the shared volume (owner request, 2026-10-12T01:55Z).** The owner asked to use Forge's updated isolated+retain behaviour, so that builds share one preview database. New runs get a stable workspace volume, `forge-preview-<hash>_tidewatch-pgdata`, while existing runs keep their per-run volume.
  - The orchestrator stopped the `sigp` preview. Its per-run volume `forge-0199b29a-sigp-4081ec46_tidewatch-pgdata` was retained; it held only the admin bootstrap.
  - It then created a related owned run, **`sigpws-8add0389`**, with a copy of the worktree mapping (the same PR branches). Its database mounts the shared **`forge-preview-0199b29a_tidewatch-pgdata`**, which was new and empty at first.
  - The owner signed in there and set the password (`must_change_password = f`). The first signal appeared at 02:26Z.
- **Later previews on the shared volume ran one at a time:**
  - refreshes for web `f2e5b01` (`:53989`) and `8dffcfb` (`:65256`);
  - a related run, **`sigpbase-653372cf`**, with the web image at base `63c7f29` for the P2 Bots baseline (`:60270`), while `sigpws` was stopped.
- **At merge** the active preview was `sigpws-8add0389` at `http://127.0.0.1:65256/`: running, with 2 signals and the admin signed in.

(source: raw/2026-10-12-signals-page.md §Test plan, Preview and the database change)

**Operating notes.**
- **Shared state carries across builds.** Because later builds mount the same workspace volume, anything a run leaves in the database stays. The acceptance agent left the owner's `signals.filters` changed on the shared preview database (Wire and PR Newswire off, Impact ≥ 0.00), and the owner has not yet been asked to reset them (see [[user-settings]]).
- **Login throttle.** The acceptance agent's repeated sign-ins hit the login throttle (`429` at 02:56:55Z). There was no lockout and no wrong password (see [[auth-model]]).
- **A kept database excludes the first-sign-in journey.** The full Playwright suite ran as `authed-setup`, then `public` + `authed` with `--no-deps`, then `sign-out`. Credentials were read from the owner's file and never printed.
- **The export works same-origin.** Three real CSV downloads through the gateway sent the session cookie (FR-SP-WEB-007, preview half).

(source: raw/2026-10-12-signals-page.md §Test plan, Preview operational notes, Commands and Acceptance status)

## Signals-day-control preview (2026-10-14)

The signals day control (see [[signals-day-control]]) was verified on an isolated preview with retain, mounted on the shared workspace volume.
- **Run.** `sdc-1aa0b0c9`, compose project `forge-0199b29a-sdc-1aa0b0c9`, `http://127.0.0.1:55694/`. It used the shared volume `forge-preview-0199b29a_tidewatch-pgdata`, and 6/6 containers were healthy from 2026-10-14T01:20:23Z.
- **Revisions.** Web `cef0be9` (the review-approved head), service `8b18486`, bot `ece175a`, migrations `52deb26`.
- **Unresolved setup token.** The first `up` failed with "Unresolved setup token: project:tidewatch-migrations". The run mapping was then extended to the service, bot and migrations worktrees, with migrations as a manual mirror as in the signals-page build. The build changed only the web, but the preview still needed the other projects mapped.
- **Playwright.** Because the database is kept, the suite ran as `authed-setup`, then `public` + `authed` with `--no-deps`, then `sign-out`. Credentials were read from the owner's file in-process and never printed.
- **Shared data limited the real-data check.** On 14 Oct the shared database held signals on 12 Oct and 14 Oct but none on 13 Oct. So FR-SDC-E2E-001's Yesterday case had no rows to compare, and the comparison ran on Mon 12 Oct instead. That ID is partial.
- **At the merge pause** the preview was left running.

(source: raw/2026-10-14-signals-day-control.md §Test plan, Preview and Commands; §Cross-cutting links)

## Charting preview and the development-build web (2026-10-15 to 2026-10-16)

Charting (see [[charting]]) was verified on an isolated preview with retain, on the shared workspace volume.
- **Run.** `chart-a69a3593`, compose project `forge-0199b29a-chart-a69a3593`, on the shared volume `forge-preview-0199b29a_tidewatch-pgdata`, with 6/6 containers healthy.
- **Revisions.** Service `51e40c2`, bot `ece175a`, migrations `52deb26` (a manual mirror). The web moved `4d8de59` → `6bc61c8` → `91bdc07`. The checks cite `91bdc07`, because the final head `3ebce40` only changes `DESIGN.md`.
- **Origins.** Production `:50682`, then `:52543`, then `:55796`. Development (PV0) `:58231`, then `:52705`, then `:55924`.
- **PV0, a per-run development-build web.** The Chart's test hook exists only in development builds, so the production preview image could not run the `@hook` Playwright tests (web plan r1 blocking item). PV0 added `tidewatch-web-dev` and `preview-gateway-dev` through a compose override kept in the feature's `planning/tidewatch-web/preview-dev/`, never in a product repository. They ran in the same compose project, against the same service, database and Redis. PV0 was re-applied on every web commit the preview served (CF-3). The production build ran the hook-free tests with `--grep-invert @hook`, and the PV2 absence check found 0 hook elements on the production build against 1 on the development control.
- **Injected publishes (PV2).** Each round made exactly two PUBLISHes on the preview Redis: a 1m bar on `px:BTCTHB@binance-th` with `pv2_note` "PV2 injected test bar", and a C-SIG-1 signal on `sig:ETHTHB@binance-th` (`ffffffff-0000-4000-8000-000000000002`, "PV2 injected test signal"). SQL was read-only, and nothing was signed in or out.
- **Read-only database access.** The A5 EXPLAIN ANALYZE ran read-only (`BEGIN READ ONLY`, `default_transaction_read_only`). For the CH-R8 capture of the two real fixture series, the orchestrator's first attempt was denied by the permission classifier. The owner then approved, in chat, a temporary read-only container (`timescaledb-ha:pg18`, `--network none`) on the retained preview volume. The container was removed afterwards and the volume kept. No credentials were handled. Engineers have no database access.
- **Sign-out incident (2026-10-15T18:42Z).** The Playwright `sign-out` project's "Sign out everywhere" ended the owner's preview sessions twice. It was deferred and not run in the later rounds. Credentials for the authed suite were read from the owner's file and never printed.

(source: raw/2026-10-16-charting.md §Test plan, Preview runs, Commands and Acceptance status; §Components, The dev-only test hook; §Concept, Other owner actions recorded in the run and Planner reconciliations CH-R8; §Database, A5; §Concept, Review history (web plan r1))

## Bots preview (2026-10-21)

Bots (see [[bots]]) was checked on an isolated preview with retain, on the shared workspace volume.
- **Run.** `bots-1c6ff8ae`, compose project `forge-0199b29a-bots-1c6ff8ae`, on `forge-preview-0199b29a_tidewatch-pgdata` at migration J, with 6/6 services healthy. Revisions: migrations `7a2cc41`, service `0ea611b`, bot `1502f07`, web `f6eb8c0`.
- **Origins.** First up at `http://127.0.0.1:61518/` (2026-10-21T00:15Z), then refreshed for FU-1 at `http://127.0.0.1:59343/`. An image check confirmed the FU-1 copy in the web chunks, both new error codes in the service binary and the new bot metric in the bot dist before the checks.
- **Owner go-ahead.** "Go ahead and run the plan's preview checks (PV1-PV5 and FR-BT-E2E-001...008) on the refreshed preview."
- **Credentials-copy method.** The owner's preview credentials were copied to `e2e/.auth` (mode 600) and never read or echoed. The run did `authed-setup`, then `public` + `authed` with `--no-deps`; journey and `sign-out` were skipped (sign-out would end the owner's sessions), and live gates were unset. The production build ran with `--grep-invert @hook`.
- **Checks continued after merge.** The E2E checks ran about 04:12–04:50Z, after the J, service and bot merges, on the same code; the preview served web `f6eb8c0` while the merged web head `4ab65db` differs only in e2e files (PF1).
- **Database writes.** The checks created three E2E bots (A and B `running`, C `observing` until 2026-11-20), injected two `documents`/`signals` rows (source `binance-th-listings`, titles starting "E2E bots preview"), moved a candidate's `ttl_until` and two `stop_px` values by SQL for the TTL and stop checks, and set the owner's `recommendations.follow` to bot C. Decisions are append-only and cannot be removed. **A and B were left `running` and C `observing`; a preview started on this volume evaluates them like any auto bot.** The 11th-active-bot check was deliberately not run, because it would have left permanent bots on the shared database.
- **The guard reads in-process prices.** For the stop check the orchestrator raised `stop_px` by SQL rather than injecting a Redis price, because the bot reads its own recorded `px:last` view, not Redis.

(source: raw/2026-10-21-bots.md §Test plan, Commands, Preview runs, The E2E checks and Preview database footprint; §Test plan, Acceptance status, FU-1 items)

## Accounts-and-roles preview (2026-10-28 to 2026-10-29)

Accounts and roles (see [[accounts-and-roles]]) was checked on an isolated preview with retain, but **not on the shared workspace volume**.
- **PREVIEW-DB.** The run used a per-run isolated, retained database, because L, M and N carry fixed goose versions from unmerged branches. The volume is `forge-0199b29a-acct-c04f668a_tidewatch-pgdata`, at L.
- **When.** 2026-10-28 18:48Z–20:36Z, then E2E-004 on 2026-10-29 02:00–02:08Z. The preview stack was last recorded as running at `http://127.0.0.1:50850/`.
- **The code sender was `dev`** (`TIDEWATCH_OTP_SENDER=dev` with `ENVIRONMENT=local`), so Twilio never ran on the preview. The operator was bootstrapped from the environment on the fresh database (E2E-001).
- **E2E-005 ran on a copy.** The per-run database starts fresh at L, so it could not hold a pre-L admin row. E2E-005 ran instead on a copy of the retained preview database, which held the two pre-L rows `admin` and `pv4-stats`. The copy sat in a separate volume, `acct-c04f668a-e2e005-pgdata` (OA-E2E005-VOLUME), which is kept for the owner to keep or remove.
- **E2E-004 ran on a dedicated plan, `e2e004`, never on `founder`** (PREVIEW-E2E004). It spent $0.000032 of Jev credit.
- **What the per-run volume still holds.** The e2e people, because there is no delete route. Also plan `e2e004` at 0.000032, person `e2e004-mvswcncud49f` and the observing bots E2E-004 A, B and C.
- **The e2e no longer uses a shared admin password.**
  - **Variables.** The web e2e uses `BASE_URL`, `E2E_OPERATOR_USERNAME` (default `owner`), `E2E_OPERATOR_PASSWORD` and `E2E_OTP_DEV_CODE`. `E2E_ADMIN_*` and `e2e/.auth/credentials.json` are retired.
  - **The operator helper.** It signs in through the API with the dev code and keeps `tw_admin` in its own cookie jar.
  - **People per run.** The journey, `authed-setup`, `password.spec`, `sign-out.spec` and `operator-live` each create their own people (`e2e-{run}-{n}`). So the slice-0 to slice-6 notes about the journey spending the admin's forced change, and about restoring the admin password through the CLI, no longer describe the current suite.
- **Results.** The final `operator` run (`10851db`) passed 527/527. `operator-live` passed 1/1 (sign-in path `bootstrap-and-change`). The product projects ran 1,427 tests: 1,412 passed, 11 failed and 4 skipped. The 11 are pre-existing `@hook` chart tests that need the dev build, and the 4 are gated by environment flags.

(source: raw/2026-10-29-accounts-roles.md §Concept, Stage and Decisions during the build PREVIEW-DB, PREVIEW-E2E004; §Concept, Spec corrections, E2E-005 method; §Database, Backfill; §Test plan, Preview runs; §Components, e2e; §API, Configuration; §Open questions, Owner actions still open)

## Learning-loop preview (2026-10-28 to 2026-10-30)

The learning loop (see [[learning-loop]]) was checked on an isolated preview with retain, **not on the shared workspace volume**.
- **A per-run database (parent decision, 2026-10-28).** The database is `forge-0199b29a-ll-f3bdc8b0`, not the shared `forge-preview-0199b29a_tidewatch-pgdata`. M was applied on a clean K-level database **without L**. PV1–PV5 ran from 2026-10-28 15:29Z to 2026-10-29 03:33Z.
- **Refreshed for PV6 with L out of order.** After the branch update onto L, the same database was refreshed and L was applied out of order with `goose -allow-missing`. PV6 ran the whole Playwright suite, all projects, one worker, on 2026-10-30 03:16Z–09:24Z (web `f2ee96c`, bot `435feb4`, service `48f179d`, migrations `d28de68`): 2,260 passed, 3 failed, 4 skipped in 37.5 min. One failure was the shared `app-dialog` reopen race, later fixed by web #25 (see [[design-system-decisions]]).
- **A dedicated seeded user.** The seeded learning bots belong to user `pv4-learning`, kept separate from the owner's bots at the owner's ruling OD-PV4-1 ("Keep them separate"). After L it reads role `user`.
- **The database still holds** `pv4-learning` and its 11 bots, about 3,440 append-only seeded decisions, seeded documents, signals and extractions dated 3–5 Oct, 12 unattributed pre-fix `post_mortem` `model_calls` rows, and L applied out of order. The retained volume's expected name is `forge-0199b29a-ll-f3bdc8b0_tidewatch-pgdata`.
- **The preview's OpenRouter key was refused on every call** (extraction, `post_mortem`, `bot_thesis`), so no model-written post-mortem was produced (FR-LL-E2E-003's model half and A6 stay open). Paid calls on PV4: Jev `bot_decide` 1 call, $0.000029; OpenRouter 13 refused calls, $0.
- **Preview containers must not share production keys (lesson, 2026-10-30).** The preview bot container `forge-0199b29a-ll-f3bdc8b0-tidewatch-bot-1` holds the **production Alpaca key**. During the production bot rollout it held Alpaca's single stream connection, and the production bot looped on 406 until the container was stopped at 18:45Z. It must not be restarted alongside production. Stop preview bots, or give them another key, before a production bot rollout (see [[market-data-worker]]).
- **The rest of the stack** was last recorded as running at `http://127.0.0.1:50075/`. Its cleanup is not recorded.
- **e2e method.** The report download was checked by URL in the mock, because Playwright 1.63 does not route an `a[download]`, and the real file was checked on the service (A5).

(source: raw/2026-10-30-learning-loop.md §Concept, Stage, Verified on a preview; §Concept, Decisions during the build, Preview DB and OD-PV4-1; §Concept, Rollout to production and Lesson recorded (one Alpaca stream per key); §Test plan, Preview runs and What each seeded E2E showed; §Components, e2e; §Open questions, Owner actions still open)

## Known limits

- The preview shares one secrets file between `db`, `migrate` and `tidewatch-service`, so the admin password is visible in the `db` and `migrate` containers.
- `TRUSTED_PROXIES` is empty in the preview definition, so everything arriving through the gateway shares one client IP and the 5-per-minute per-IP login limit can act globally (see [[auth-model]]).
- FR-INFRA-008 (the Forge run command for `tidewatch-service`) is an open owner action; see [[foundation-auth]].

(source: raw/2026-10-05-foundation-auth.md §Open questions)

## Related pages

- [[request-protection]] — the CSRF and CORS rules the gateway rewrite must not weaken
- [[centralized-migrations]] — the migrations resource the preview `migrate` builds from
- [[foundation-auth]] — the slice overview
- [[realtime-websocket]] — the `/ws` hub reached as `/api/ws` through the gateway
- [[market-data]] — slice 1, which added the bot to the preview
- [[bot-activity]] — the feature verified on the Phase A–C preview described above
- [[auth-model]] — the forced password change the e2e journey spends, and the CLI reset
- [[signals-ingest]] — the feature verified on the refreshed preview with provider keys described above
- [[signals-page]] — the feature that moved to the shared retained workspace volume described above
- [[user-settings]] — the stored filters left changed on the shared preview database
- [[signals-day-control]] — the web-only feature verified on the `sdc-1aa0b0c9` preview described above
- [[charting]] — slice 5, verified on the `chart-a69a3593` preview with its PV0 development-build web
- [[elliott-regime-labeller]] — the two real fixture series captured read-only from the retained preview volume
- [[bots]] — slice 6, checked on the `bots-1c6ff8ae` preview on the shared volume
- [[accounts-and-roles]] — checked on a per-run database at L with the `dev` code sender
- [[operator-console]] — the operator helper and dev code the e2e now signs in with
- [[learning-loop]] — checked on a per-run database at M, refreshed with L out of order for PV6
- [[market-data-worker]] — the one-Alpaca-stream-per-key lesson the preview bot caused
