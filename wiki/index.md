# tidewatch — Wiki index

Maintained by Claude using the `wiki-llm` skill. See that skill for
folder structure, page format, citation rules, ingest workflow, and
lint procedure. Categories are top-level H2 headings so the wiki's
knowledge graph (`/understand-knowledge`) can detect topic clusters.
Rename or add categories as the workspace's knowledge grows.

## Overviews

- [[foundation-auth]] — Slice 0: Postgres migrations, Go auth service, Aurora web shell, preview
- [[market-data]] — Slice 1: instruments, time series, bot collectors, REST and /ws, Market watch
- [[simulation-engine]] — Slice 2: paper trading, Trade screen, portfolio hero; preview checks partial
- [[zone-transition-bot]] — Slice 2b: Slack Water auto paper bot on CDC zone runs; no live entry yet
- [[bot-activity]] — Bot Watch and Checks: per-instrument verdicts, migration G, 33/33 passed
- [[signals-ingest]] — Slice 3a: feeds to `signals` via Jev and OpenRouter, migration H; soak pending
- [[signals-page]] — Slice 4: /signals, live note, rail badge, migration I; E2E-003/004 unverified
- [[signals-day-control]] — ORCH-19: 7-day Day select, `?day=`, midnight relabel; merged, not deployed
- [[charting]] — Slice 5: zone-coloured Chart, Elliott counts, signal markers; merged, not deployed
- [[bots]] — Slice 6: v2 bots, scout/manager/guard, Run now, Trade card, FU-1 caps; PV2 changes requested
- [[statistics]] — Slice 7: /stats KPIs, calibration, attribution, post-mortems, promote; merged, deployed
- [[accounts-and-roles]] — Phase A: operators apart from users, people, plans as data, no sign-up; deployed
- [[learning-loop]] — Slice 8: monthly learning runs, drafts saved as vN, failure gate, model post-mortems; deployed
- [[signals-context]] — Spec 3b: GDELT context, coverage signals, event calendar, scout discovery; N unpinned

## Architecture

- [[auth-model]] — Cookie sessions, argon2id, login throttle, forced change, audit events; role `user`
- [[operator-console]] — `/admin`: password then Twilio SMS code, People, Operators, Audit, Spend, CLI
- [[request-protection]] — D1 guardrails: exact-origin CORS, CSRF header plus Origin, SSR hosts
- [[centralized-migrations]] — goose resource, migrations A–N (pin M, N never pinned), schema-version contract, GitOps hook lesson
- [[forge-preview-gateway]] — Caddy preview gateway: /api proxy, Origin rewrite, 421 on rebinding
- [[design-system-decisions]] — Aurora tokens, D6/D7/D13, OWNER-4/5/6, DESIGN.md, Market watch to the Learning section (slice 8)
- [[market-timeseries]] — candles, candles_eod, aggregates, refresh rules, CDC indicators, the chart's joined read
- [[market-data-worker]] — Bot serve/collectors/status, sim/bots/ingest/signals/learning/context runners; Binance TH 7-day rule; OANDA dormant; one Alpaca stream per key
- [[redis-market-contract]] — px:last, px:<id>, sig:<id> and md:subscriptions between bot and service
- [[paper-trading]] — Order path and bot-side intake, fill model, venue rules, ledger marks, `sim` runner
- [[bot-versions-and-runs]] — Bots, v1/v2 versions, windows, probation, runs, /bots routes, champion, FU-1 caps, learned drafts
- [[bot-watch-verdicts]] — Bot verdicts (C11's 14, C11' 23), bot_watch, bot_runs.outcomes, watch route
- [[bots-engine]] — General bot engine: scout, manager, guard, candidates, run requests, per-bot budget, learned p and meta gate, discovery paths
- [[realtime-websocket]] — GET /ws: check order, limits, 4401/4403, fan-out, signal frame, all-signals feed
- [[signals-pipeline]] — decide() port, Jev triage and scoring, OpenRouter extraction, impact, publish
- [[model-routes-and-spend]] — Routes, prices, ledger, $1.00 ceiling, 25 % bot budget, per-person allowance, `post_mortem` stage
- [[signal-message-contract]] — C-SIG-1 on `sig:<id>`: three-repo byte pin, `/ws` signal frame, web count
- [[signals-read-api]] — Signal list, detail (with Elliott, regime), summary, badge, export, `/sources`, per-instrument read
- [[chart-read-api]] — `GET /instruments/{id}/chart`: joined bars, analysis window, `right_now`, stance
- [[stats-read-api]] — Five Stats routes (contracts r2): figures, losses, compare verdict, promote, post-mortem
- [[gdelt-gkg-ingest]] — GDELT GKG streams, keep gate as data (`theme_rules`, `domain_rules`), bounds, volumes
- [[context-features-and-coverage-signals]] — `context` runner, 24 h coverage z, coverage signals (`origin = 'context'`, never a trigger)
- [[user-settings]] — `user_settings` (migration I), stored filters, seen-through, badge, follow setting

## Domain

- [[gold-feed-xaut-proxy]] — XAU/USD priced from Binance TH XAUT: migration D, calendar gating, USD/THB proxy
- [[decision-record]] — Append-only decisions, back-fill, outcomes, bot loop and cited rows, C4'', post-mortem
- [[signal-cited-orders]] — Signal and candidate citations, three Trade pre-fills, the bot recommendation card
- [[elliott-regime-labeller]] — `waves`: zigzag, Elliott candidates with fit, regime, C13 fixtures, bot port
- [[instrument-master]] — SYMBOL@venue ids, aliases, synthetic gold, universe lists, calendars, signal resolution
- [[source-registry-and-ingest]] — Thirteen sources (ten from H, three from N), ingest runner, dedup, named resolution, CIK refresh
- [[event-calendar]] — `event_calendar`: Finnhub US earnings, seeded FOMC and BoT MPC, per-series renewal warning
