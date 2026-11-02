# Per-user settings (`user_settings`) and the unseen-signals badge

**Summary**: Since slice 4 (the signals page, merged 2026-10-12), Tidewatch stores per-user preferences in the database. Migration I adds `user_settings`, which holds one jsonb value per (user, key). The service accepts exactly two keys. `signals.filters` holds the Signals page's stored filters. `signals.seen_through` holds the instant through which the user has seen signals, and it never moves backwards. Owner decision D3 put both in the database rather than in `localStorage`, because a "since last visit" count is only true when every device agrees on what has been seen. The rail's unseen-signals badge counts from that instant. The signals day control (merged 2026-10-14, not deployed) added no key and no migration. It changed only when the web writes the two keys: `signals.filters` never carries the shown day, and seen-through advances only on Today, never for a past day (SDC-OD-1). **Since slice 6 (bots, merged 2026-10-21, not deployed), the service accepts a third key, `recommendations.follow`**, which names the bot whose candidates Trade's recommendation card shows (owner decision D1). It also needed no migration. **Since accounts and roles (merged and deployed 2026-10-29),** every settings owner is a person with role `user`, created by an operator. Settings stay per person and are never shown in the operator console. Since no person is ever deleted, the `ON DELETE CASCADE` has no route that triggers it.

**Sources**: `raw/2026-10-12-signals-page.md`; `raw/2026-10-14-signals-day-control.md` (the day-control write rules); `raw/2026-10-21-bots.md` (the `recommendations.follow` key); `raw/2026-10-27-statistics.md` (the champion the key resolves to); `raw/2026-10-29-accounts-roles.md` (who owns settings, and the backfill only)

**Last updated**: 2026-10-29

---

## Why the database (D3)

The owner chose to keep filters and the badge's "seen through" instant in the database, with migration I's table, the settings routes and a badge route. The two rejected options were `localStorage`, and URL-only filters with no badge. Before slice 4, no table stored per-user settings, and the theme lived in `localStorage` only (source: raw/2026-10-12-signals-page.md §Concept, Chosen design D3; §Concept, Problem).

## The table (migration I)

```sql
CREATE TABLE user_settings (
    user_id    uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    key        text        NOT NULL CHECK (key ~ '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){0,3}$' AND length(key) <= 64),
    value      jsonb       NOT NULL CHECK (octet_length(value::text) <= 8192),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, key)
);
```

- There is one row per (user, key). A deleted user's rows go with the user (`ON DELETE CASCADE`). Since accounts and roles, nothing ever deletes a person (D13): an operator can only disable sign-in, which leaves the person's settings in place (source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built, and Owner decisions D13).
- **Size limits (ORCH-4).** The service caps a value at 4096 bytes and returns its own error. The 8192-octet CHECK is a database backstop.
- Constraint names are PostgreSQL's defaults: `user_settings_pkey`, `user_settings_user_id_fkey`, `user_settings_key_check` and `user_settings_value_check`.
- **The down migration destroys every stored setting.** Only the owner may run it, and only locally. How I ships and how the harness probes it are on [[centralized-migrations]].

(source: raw/2026-10-12-signals-page.md §Database; §Concept, Orchestrator rulings ORCH-4)

## Routes

| Method and path | Request | 2xx response | Errors |
|---|---|---|---|
| `GET /me/settings` | none | `{settings: {<key>: <value>}}`, stored keys only | — |
| `PUT /me/settings/{key}` | body exactly `{value}`, with the CSRF header `X-Tidewatch-Request: 1` and the app `Origin` | `{key, value, updated_at}` | 400 `invalid_request` with `details.field` `key` or `value` (`unknown_field` never names the key); 403 `csrf_rejected` |

- Both routes sit on the gated market group, like the signals routes (see [[signals-read-api]]). They are scoped to the session user, and no route takes a user id (see [[auth-model]]).
- **Validation order (S9):** the key, then a missing value, then 4096 bytes, then the value's shape.
- Settings writes are not audited, and they are never logged with their value.
- `TestRouter_NoDecisionMutation` now allows exactly `PUT /me/settings/:key` among its mutation routes (R16).

(source: raw/2026-10-12-signals-page.md §API, Service routes and Settings keys; §Concept, Plan resolutions, Service R16)

## The keys

| Key | Value |
|---|---|
| `signals.filters` | Exactly `{asset: "all"\|"us"\|"th"\|"crypto"\|"gold", tiers: [distinct tiers], sources: [distinct codes that exist in sources now, ≤ 64], min_impact: "0.00".."1.00"}`. A `min_impact` above 1.00 is `invalid` here but `out_of_range` in a query. |
| `signals.seen_through` | Exactly `{at: RFC 3339 instant ending in Z}`, at most 60 s past the service clock (`out_of_range`). **It never moves backwards:** the stored value is always the later instant, and a stale write gets the newer stored value back. |

**A third key since slice 6: `recommendations.follow`.**
- **Value.** Exactly `{"mode": "champion"}` (the default) or `{"mode": "bot", "bot_id": "<uuid>"}`; the stored follow setting is an object (ORCH-5d). `PUT /me/settings/recommendations.follow` checks the shape only; whether the bot is the user's own auto bot is resolved when `GET /recommendation` reads it.
- **Resolution.** A followed bot that is not the user's auto bot falls back to the champion rule: the user's `champion = true` auto bot, else the oldest `running` or `observing` auto bot whose current version is v2 with a scout, else none (ORCH-5c).
- **The web.** Trade's *Follows* select writes it; only the champion or one of the answer's `options` can be written (security L2). See [[signal-cited-orders]].
- **Since slice 7 (2026-10-27), `champion` can resolve to a promoted bot.** Until then `bots.champion` was never set, so the default always took the fallback. `POST /bots/{bot_id}/promote` now sets one champion per user, and `GET /recommendation` reads the flag on its next read; on the preview it followed the newly promoted bot (FR-ST-E2E-002). No production champion has been made yet (see [[statistics]]) (source: raw/2026-10-27-statistics.md, summary block; §API, Promotion semantics and locking; §Test plan, The E2E checks).
- **On the preview** the check left `recommendations.follow` = `{"mode": "bot", "bot_id": <bot C>}` on the shared retained database (see [[bots]]).

(source: raw/2026-10-21-bots.md §API, Changed routes and Behaviour worth knowing, Recommendation and follow; §Concept, Owner decisions D1 and ORCH-5/6; §Components, Trade; §Test plan, Preview database footprint)

**Writer.** Only the service's `SettingsRepo` writes `user_settings`. `PutLaterAt` keeps the later `seen_through` instant in one `INSERT … ON CONFLICT` statement and returns the stored row. `updated_at` moves only when the value changes (source: raw/2026-10-12-signals-page.md §API, Settings keys; §Database, Writers).

## The web: stored filters

- **The URL is the source of truth.** The Signals page writes `asset`, `tier`, `source` and `min_impact` with `replaceUrl` and `queryParamsHandling: "merge"`, and only non-default values (SP-W-7).
- **An empty URL takes the stored filters.** The store reads `GET /me/settings` first, applies the stored `signals.filters`, writes them into the URL, and then reads the list (SP-W-22). A URL that sets any of the four parameters wins over the stored filters.
- An emptied group is written as an empty value (`tier=`). For an empty set the list is not requested, and the filter-empty state shows at once.
- Malformed values fall back to that parameter's default. Unknown source codes are dropped once `/sources` answers, and a partly selected publisher is widened to all of its codes (ORCH-12).
- **Writes.** `PUT /me/settings/signals.filters` is debounced by 500 ms, sent one at a time, flushed at once on destroy, and silent on failure.

(source: raw/2026-10-12-signals-page.md §Components, URL and settings precedence; §Concept, Plan resolutions, Web SP-W-7/22; §Concept, ORCH-12)

**The shown day is not a filter (signals day control, 2026-10-14).**
- `signals.filters` never stores the day. Changing the day sends no `PUT /me/settings/signals.filters` (PD-C).
- `?day=` is not one of `FILTER_PARAMS` (`asset`, `tier`, `source`, `min_impact`), so the precedence above is unchanged. A URL that holds only `?day=` still takes the stored filters (DC5).
- An empty URL while the page is open, which is what the rail's *Signals* link gives, returns to Today and writes the stored filters back into the URL.

See [[signals-day-control]] (source: raw/2026-10-14-signals-day-control.md §Database; §API, The `day` URL parameter; §Concept, Owner decisions DC5 and PD-C).

## The web: seen-through and the rail badge

- **Who writes it.** `SignalsBadgeService` (`shell/data/signals-badge.service.ts`) is provided by `Shell`, which outlives the page (SP-W-5). `advanceSeenThrough(at)` writes `PUT /me/settings/signals.seen_through` only for a later instant, then re-reads the badge when the user is not on `/signals`.
- **When it advances (slice 4).** Seen-through moves to the newest listed `created_at` after the first successful list load and after *Show*. It never moves after *Load more* (SP-W-20).
- **When it advances (since the day control, SDC-W-11).** `advanceSeenThrough` itself is unchanged, and the stored value still never moves backwards. The Signals store now calls it:
  - after the first successful **Today** load of each service day (D0) the page shows. This includes the new Today after a midnight rollover (owner decision SDC-OD-1, 2026-10-13). A Today load with no rows still counts as that day's first;
  - after every *Show*, including the reveal of a count that was already waiting at the rollover;
  - **never** after a past day's load, another load of a Today already advanced for, *Load more*, or the kept-day re-read after a reconnect crosses midnight (SDC-OD-2).

  The accepted cost of SDC-OD-1: rows still waiting behind *Show* at a rollover are marked seen by the new Today's first load. Before the day control, opening the page cleared earlier days' unseen signals without ever showing them, although the badge counts 7 days back (source: raw/2026-10-14-signals-day-control.md §Database; §Concept, Problem and Decisions taken during the build; §Components, `SignalsService` store).
- **Reads.** The badge calls `GET /signals/badge` on shell load, on every `NavigationEnd` and every 5 minutes. While `/signals` is active the read is skipped and the count shows 0. An older answer never overwrites a newer one, and a failed read keeps the last count.
- **`.nav-count`.** It shows "99+" above 99 and is `aria-hidden`. The link's accessible name becomes "Signals, {n} unseen". It is hidden at ≤ 1080 (the icon rail) and in the ≤ 600 strip, where the name still carries the number. It is the one rail badge that `03` §10 allows, and `DESIGN.md`'s "no rail badges" was updated (see [[design-system-decisions]]).
- **In mocked specs.** The shell reads the badge on every screen, so every mocked spec's `failClosedApi` answers the route with `QUIET_BADGE` (`unseen: 0`) (SP-W-3).
- The count's server rules and defaults are on [[signals-read-api]].

(source: raw/2026-10-12-signals-page.md §Components, Rail badge and SignalsService; §Concept, Plan resolutions, Web SP-W-3/5/20)

## Verification

- **FR-SP-E2E-002 passed.** In two browser contexts, A changed the filters, and one `PUT` answered 200. After a reload, A's URL and chips were identical. B, opening `/signals` with an empty URL, received the stored filters. The `user_settings` rows were checked by SQL.
- **FR-SP-E2E-006 passed,** with a stored threshold of 0.00, because both real rows sat under 0.30. Overview showed the rail count 2 ("Signals, 2 unseen"), and the count was hidden on `/signals`. After A's reveal (seen-through 02:26:48.8928Z), B's next navigation answered `unseen 0`.
- **Harness.** Six probes are refused: an upper-case key, a 65-character key, a key with five segments, a value over 8192 octets, an unknown user and a duplicate (user, key). Controls accept a `signals.filters` row, a `signals.seen_through` row, and the cascade on user delete.
- **Named tests.** `TestSettings_RoundTripAndValidation`, `TestSettings_SeenThroughNeverBackwards` (20 concurrent writers), `TestSettingsKeys_Validate`, `TestSettingsHandler_Put_StrictBody`, `TestSettingsRepo_SeenThroughMax`, `TestService_Badge_Defaults` and `TestSignals_Badge`.

(source: raw/2026-10-12-signals-page.md §Test plan, Acceptance status and Named acceptance tests; §Database, Harness)

## Accounts and roles (2026-10-29)

- **Who owns a row.** `user_settings.user_id` now always names a person (role `user`). The seeded admin was backfilled to a plain person, keeping its id, so its rows needed no change. On a copy of the retained preview database the settings count (3) was identical before and after migration L (E2E-005).
- **Operators never see settings.** The console shows counts and spend only (D6). The `Person` shape and the other `/admin` answers carry no settings.
- **No new key.** The three keys are unchanged.

(source: raw/2026-10-29-accounts-roles.md §Concept, The model, as built; §Database, Backfill; §API, People and Product contract changes)

## Open items

- **Preview state.** The acceptance agent left the owner's `signals.filters` changed on the shared preview database (Wire and PR Newswire off, Impact ≥ 0.00). The owner has not yet been asked to reset them (see [[forge-preview-gateway]]).
- Only two keys were accepted at slice 4; slice 6 added `recommendations.follow`, the third. Any new preference needs its key and shape added to the service (`internal/services/settings/keys.go`) (source: raw/2026-10-21-bots.md §Files touched, tidewatch-service S9).

(source: raw/2026-10-12-signals-page.md §Test plan, Preview operational notes; §Open questions; §API, Settings keys)

## Related pages

- [[signals-page]]: the slice-4 overview and the Signals screen
- [[signals-day-control]]: the *Day* select, which never writes `signals.filters` and changes when seen-through advances
- [[signals-read-api]]: the badge route, its defaults, and the list the filters drive
- [[centralized-migrations]]: migration I and its destructive down
- [[auth-model]]: the session user that scopes every setting
- [[request-protection]]: the CSRF header and Origin check on `PUT /me/settings/{key}`
- [[design-system-decisions]]: `.nav-count`, the one rail badge
- [[source-registry-and-ingest]]: the source codes that `signals.filters` may name
- [[bots]]: slice 6, which added the `recommendations.follow` key
- [[signal-cited-orders]]: the Trade recommendation card that reads the follow setting
- [[statistics]]: slice 7, whose promote gives `{"mode": "champion"}` a champion to follow
- [[accounts-and-roles]]: people as the owners of settings, and the backfill that kept the owner's
