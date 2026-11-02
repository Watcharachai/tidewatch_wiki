# Signals day control (`signals-day-control`, ORCH-19)

**Summary**: Slice 4's Signals screen showed only the service's current Bangkok day. After Bangkok midnight it was empty, and a page left open kept calling the old day "Today". This web-only feature adds a *Day* select, first in the Signals filter row, listing the service's today and the six days before it: *Today*, *Yesterday*, then dates such as "Sat 10 Oct". The shown day lives only in `?day=YYYY-MM-DD`, written with `replaceUrl` and never stored. A past day names itself in the heading, the sub line, the table's name and caption, the empty sentences and the export. It never counts live frames and never advances seen-through. At Bangkok midnight, a page open on Today keeps its rows and relabels them *Yesterday* within one 60 s summary tick, without reading the list again. An empty Today offers *Show yesterday*. "Today" always comes from the service's `generated_at`, never from the browser clock. The service, migrations and bot did not change, because the API already accepted `day`. tidewatch-web PR #13 merged on 2026-10-14 at 06:58:59Z (head `e49c237`, merge commit `976233f`) on the owner's instruction. 14 of 15 acceptance IDs were verified, and **FR-SDC-E2E-001 is partial**. The change is merged but **not deployed**. **Update (2026-10-16):** charting's preview found that a pasted out-of-window day could stay on "Loading signals…" forever on production builds, a race already on `main` at `976233f`. Charting's fix round PF1 corrected it in `signals.service.ts`, merged with tidewatch-web #14 (`918d7b6`) on 2026-10-16 and **not deployed** (see "After merge" below).

**Sources**: `raw/2026-10-14-signals-day-control.md`; `raw/2026-10-16-charting.md` (the PF1 race fix only)

**Last updated**: 2026-10-16

---

## Stage, stated precisely

This is the status in `state.json` as last updated at 2026-10-14T06:59:24Z (source: raw/2026-10-14-signals-day-control.md §Concept, Stage, stated precisely).

| Stage | Status |
|---|---|
| Implemented | Steps S1 `19a6364`, S2 `481556e`, S3 `ee9c9cf`, S4 `560e54c` and S5 `9cc3fd3`. Review-fix rounds r1 `7cf44dc`, r2 `3c11b88`, r3 `6e0d938` and r4 `cef0be9`. P4 design refresh `e49c237` (`DESIGN.md` only). |
| Verified locally | Every step's and every fix round's contract commands exited 0. At `cef0be9`, `pnpm nx test tidewatch-web` ran 3,138 tests in 94 files, in the host zone and again under `TZ=America/New_York`. Lint, build, e2e lint, the e2e type-check, Prettier on the owned files and the plan checks also passed. |
| Reviewed | **Plan:** r1 changes requested, then r2 approved. **Code:** five rounds, each by four reviewers (angular, design, code, security). Round 5 at `cef0be9` was all approved, with no blocking or should-fix finding. |
| Verified on a preview | P1 Playwright 770 passed / 0 failed / 4 live-gated skips. P2: FR-SDC-E2E-001 **partial**. P3: rendered design review approved. P4: `forge-setup-impeccable --check` reported no drift (106/106). Result: 14 of 15 IDs verified, none failed. |
| Merged | Yes, 2026-10-14T06:58:59Z. tidewatch-web#13 merged as a merge commit with `--match-head-commit e49c237`, giving `976233f`. The orchestrator merged on the owner's instruction "merge it and continue". No other repository merged. |
| Deployed | **No.** No migration, environment or service step is needed; the web deploys alone. |
| Documentation pass | The raw document and this wiki update. `tidewatch-specs` and `tidewatch-apis` are not Git repositories and were not changed. |

`verification.md` was written at the merge pause, so its closing line still reads "Merged: no (awaiting the owner)". The merge itself is recorded in `state.json` (`perProject.tidewatch-web.merged`) (source: raw/2026-10-14-signals-day-control.md §Concept, Stage, stated precisely).

## Why it exists

On 2026-10-13 the owner opened Signals just after Bangkok midnight, found it empty, and asked for a way to read earlier days. This is ORCH-19 of the signals-page build. It was recorded at 2026-10-12T18:24Z as "keep today-only for this build, add a day control after the merge" (see [[signals-page]]). The intent checked these facts on 2026-10-13, at web `da6f4cb`, service `8b18486` and migrations `52deb26`:
- **The API already accepted `day`.** `GET /signals`, `GET /signals/summary` and `GET /signals/export.csv` take `day=YYYY-MM-DD` (see [[signals-read-api]]).
- **History.** `signals` has no retention policy, and history begins with slice 3a on 2026-10-11 (see [[signals-ingest]]).
- **The web never sent `day` on a first read.** It carried the answered `day` only on *Load more*, *Show*, the summary and the export.
- **Midnight with the page open.** The page stayed on the day it had loaded and still called it *Today*. Frames for the new day were not counted. A filter change or a reconnect then reloaded into the new, empty day.
- **The badge counts 7 days back,** but the page could show only today. Opening the page advanced seen-through to today's newest row, which cleared earlier days' unseen signals without ever showing them (see [[user-settings]]).

The interview ran in chat with the `grilling` skill, because the Forge Console Spec studio reported no attached display. The owner took every recommended option in both rounds (source: raw/2026-10-14-signals-day-control.md §Concept, Problem).

**Outcomes (intent).** O1: any of the last 7 Bangkok days can be read from the screen. O2: midnight never blanks or mislabels the page. O3: a past day reads honestly as the past. O4: links and reloads reproduce the view (source: raw/2026-10-14-signals-day-control.md §Concept, Outcomes).

## Terms (PRD §3)

| Term | Meaning |
|---|---|
| D0 (service today) | The Bangkok day (fixed UTC+07:00) of the latest `generated_at` the page has read from any first page, *Load more*, *Show* or summary answer. It never moves backwards and never comes from the browser clock. It is unknown until the first answer. Bangkok day D covers `[D−1 17:00Z, D 17:00Z)`. |
| Window | D0 and D0−1 … D0−6. |
| Shown day | The URL's `day` when present, else D0. A *past day* is a shown day before D0. |
| Day label | *Today* (D0), *Yesterday* (D0−1), else "{Ddd} {d} {Mon}" in en-US short forms with no leading zero, e.g. "Sat 10 Oct". |
| Day phrase | "today", "yesterday" or "on {Day label}" ("on Sat 10 Oct"), used inside sentences. |
| Rollover | D0 moving forward while the page is open. |

(source: raw/2026-10-14-signals-day-control.md §Concept, Terms)

## Owner decisions (intent, 2026-10-13)

The owner chose the recommended option for each decision.

| ID | Decision | Rejected |
|---|---|---|
| DC1 | A last-7-days *Day* select, built as `label.chip.chip-select` like *Impact ≥*. Its options are *Today*, *Yesterday*, then five dates, matching the badge's 7-day window. | Today/Yesterday chips (reaching Friday from Monday would need a hand-edited URL). Chips plus an *Earlier* select (three controls, and the most wrapping at 390). |
| DC2 | At Bangkok midnight on Today, stay on the day being read. Within about 60 s it relabels as *Yesterday*, and the URL gains `?day=` with `replaceUrl`. No reload, no row change. | Switching to the new, empty day. Leaving the mislabel. |
| DC3 | *Buy / Sell with recommendation* stays on past days, unchanged (see [[signal-cited-orders]]). | Yesterday only. Hidden on past days. |
| DC4 | Past-day rules: no live counting and no *Show*; the note is unchanged; a past day's load never advances seen-through; the heading, table name and caption name the day; the sub line shows that day's counts, refreshed every 60 s; *Export* carries the day. | — |
| DC5 | `?day=YYYY-MM-DD` is the day's only home. Absent means Today, and today's own date is written as absent. A malformed, future or out-of-window day falls back to Today. Writes use `replaceUrl`. `signals.filters` never stores the day. A `?day=`-only URL still takes the stored filters. The rail's *Signals* link returns to Today and keeps the filters. | — |
| DC6 | No mockup. | A small mockup on the real tokens. |
| DC7 | The select is first in the filter row, before *Asset class*, labelled "Day", followed by the row's `.sep`. | Last, beside *Impact ≥*. In the section head. |
| DC8 | Past-day sentences: "No signals yesterday." / "No signals on Sat 10 Oct."; "No signals match these filters yesterday." / "… on Sat 10 Oct.". | — |
| DC9 | An empty Today offers *Show yesterday*: a `.text-btn` after the empty sentence. | The sentence only. |

**Accepted defaults.**
- **PD-A.** The options come from the service's day. Until the first answer, the select shows *Today* only.
- **PD-B.** A viewed day that rolls past the window stays as an extra option until another day is chosen. Only a pasted out-of-window link falls back to Today.
- **PD-C.** Changing the day never writes `signals.filters`.

**Spec-level defaults (PRD).**
- **S1.** A new-rows count already waiting at the rollover keeps *Show* until the rows are revealed.
- **S2.** A pasted out-of-window or future day is checked once D0 is known. It is never drawn, the URL drops it with `replaceUrl`, and Today loads. The section stays loading throughout.
- **S3.** *Export*'s `day` is the shown day from the moment it is chosen.
- **S4.** A day change behaves like a filter change: the rows drop to loading, the list and summary are read again, the count restarts, focus stays on the select, and open rows are kept by `signal_id`.
- **S5.** Seen-through advances after the first successful Today load and after *Show*, never after a past day's load or *Load more*.
- **S6.** Day words come from `YYYY-MM-DD` strings by calendar arithmetic in the Bangkok helpers.

(source: raw/2026-10-14-signals-day-control.md §Concept, Owner decisions, Accepted defaults and Spec-level defaults)

## Decisions taken during the build

- **SDC-OD-1 (owner, 2026-10-13T02:31:15Z; plan review r1, blocker 2).** The first successful load of each new D0 shown as Today advances seen-through, including the new Today after a midnight rollover. The accepted cost: old-day rows still waiting behind *Show* at the rollover are marked seen too. The plan records this as SDC-W-11. See [[user-settings]].
- **SDC-OD-2 (owner, 2026-10-13T05:15:28Z; code review r2).** A reconnect or terminal-close reload of Today can cross midnight before the summary tick. When it answers with the next day, the page does not take that page. It re-reads the kept day once by date (`day=X`), so that "a reconnect reloads the shown day" (PRD §4.7). This costs one extra list read in that case only. The plain midnight relabel still makes no list read. It is recorded in `owner-decisions-review.md`, because the approved plan fingerprints `owner-decisions.md`, which had to stay byte-identical. See [[realtime-websocket]].
- **SDC-BD-1 (build; design review r1 W1 / r2 A5; fix round 1).** If *Show yesterday* has keyboard focus when a rollover on an empty Today removes it, focus moves to the day's `h2` (the SE-11 rule). Focus cannot stay on a removed button. All other focus is left alone.
- **Fix-round cap override (owner, 2026-10-14T00:57:25Z).** The owner authorised a fourth review-fix round past the cap of 3.

**Plan reconciliations within the PRD's latitude (SDC-W-1…10).**
- **SDC-W-1.** `new-signals.ts` stays byte-identical. The store passes it the list's `generated_at` only while the list is Today. On a past day, including after a rollover, it passes `null`, so no new frame counts. Ids already counted stay with *Show* (see [[signal-message-contract]]).
- **SDC-W-2.** A list's identity is its query plus its resolved day. None of these make a `GET /signals` or change the view: learning D0; the rollover's switch from an absent `day` to `day={loaded}`; rewriting `?day={D0}` to absent. Choosing *Today* after a rollover starts a new list.
- **SDC-W-3.** On Today the summary and export send the loaded Today list's `day`, or none. They never send a past day's.
- **SDC-W-4.** The day lives beside the filters in the store, outside `FILTER_PARAMS`. It is written in one merge navigation with `replaceUrl`.
- **SDC-W-5.** `signal-filters.ts` only parses `day`. The window check needs D0, so the store does it.
- **SDC-W-6.** The sub line shows a summary only when the summary's `day` is the shown day.
- **SDC-W-7.** The store computes the options, and the filters component stays presentational. The `<select>` node is kept when its options change.
- **SDC-W-8.** CSS is limited to placement.
- **SDC-W-9.** The Playwright second day is opt-in, and the mock reads the page's faked clock.
- **SDC-W-10.** The drifted signals-page plan entry in `DESIGN.md`'s Source snapshot was repointed to `.forge/features/signals-page/artifacts/plans/tidewatch-web.md` (same SHA-256 `910c45ff…`).

(source: raw/2026-10-14-signals-day-control.md §Concept, Decisions taken during the build)

## Review history

| Round | Head | Verdicts | What followed |
|---|---|---|---|
| Plan r1 | `b58c375b…` | Changes requested. Blocking: S5's checks did not prove the doc edits, and seen-through after a rollover needed the owner. Should-fix: E2E-001 was in no step, and no spec covered focus staying on the select or open rows being kept. | SDC-OD-1; planner r2. |
| Plan r2 | `2df746c9…` | Approved (0/0). | Approved 2026-10-13T02:45:36Z. |
| Code r1 | `9cc3fd3` | All four approved. Should-fix: a pasted day's failed opening showed Loading, and a Today reload crossing midnight replaced the kept rows. Design W1–W4. | Fix r1 `7cf44dc` (6 new specs). |
| Code r2 | `7cf44dc` | All four approved. Remaining: the pasted-day error flickered with the 60 s tick (a11y), and a reconnect after midnight missed rows (an owner question). | SDC-OD-2; fix r2 `3c11b88` (error latch plus the kept-day re-read). |
| Code r3 | `3c11b88` | Angular changes requested: an effect wrote a store signal through `onFirstPage`/`reloadList`, against angular-signals. Code, design and security approved. | Fix r3 `6e0d938`: the re-read trigger moved into the page resource's `parse` callback, and the latch resets on a new list read. |
| Code r4 | `6e0d938` | All four approved. Non-gating: a stale hold on an A→B→A filter revert, an unpinned tick-guard spec, an optional `pickedDay` guard. | Cap reached; the owner authorised fix r4 `cef0be9`. |
| Code r5 | `cef0be9` | All four approved, nothing blocking. | Review gate passed 2026-10-14T01:11:46Z; PR opened 01:12:51Z. |

(source: raw/2026-10-14-signals-day-control.md §Concept, Review history)

## What the user sees

**The Day select** is `label.chip.chip-select`, holding `span#signal-filter-day-label` "Day" and a native `<select aria-labelledby>`. It is built exactly like *Impact ≥*, sits first in the filter row and is followed by an `aria-hidden` `.sep`. It is never disabled.
- **With D0 known**, the options are D0 (*Today*), D0−1 (*Yesterday*), then D0−2 … D0−6 by date label. A shown day outside that window is added as an extra last option (PD-B).
- **Before D0 is known**, the select shows *Today* alone (value `""`), or the URL's day alone by its date label.
- On the preview, with D0 on Wed 14 Oct, it read *Today*, *Yesterday*, "Mon 12 Oct" … "Thu 8 Oct".

**Copy by day (PRD §4.4–§4.6, verbatim in `util/signal-view.ts`).**

| Piece | Today | Past day |
|---|---|---|
| Sub line | "{n} today · {n} acted on by bots · {n} contradicted by price" (unchanged) | "142 yesterday · 0 acted on by bots · 3 contradicted by price", "88 on Sat 10 Oct · …" |
| Section `h2` | *Today* | *Yesterday*, *Sat 10 Oct* |
| Region name / caption | "Signals today, scrollable table" / "Signals today" | "Signals yesterday, …" / "Signals on Sat 10 Oct" |
| Empty day | "No signals yet today. Signals appear within seconds of a filing, release or exchange notice becoming a scored event." plus *Show yesterday* | "No signals yesterday." / "No signals on Sat 10 Oct." |
| Filters show nothing | "No signals match these filters today." | "No signals match these filters yesterday." / "… on Sat 10 Oct." |
| Loading, error | "Loading signals…", "Signals couldn't load." plus *Try again* | Same |
| Note | "Newest first · Asia/Bangkok", plus "· {n} more under Impact ≥ {t}" | Same, with no new-rows count except S1 |

A day before signal history began reads as an empty past day. The empty-day test is unchanged: the shown day's summary answers 0, or, without a summary, the unfiltered query has nothing hidden.

**Other behaviour.**
- The `h2` keeps `id="signals-today-title"` and `tabindex="-1"`, and a rollover relabels it in place.
- ***Show yesterday*** is a `button.text-btn` after a space inside the same dashed `p.status-line`. It renders only while the page is on Today, the state is `empty`, and D0 is known. Pressing it first focuses the `h2` (the button disappears while the day before loads), then selects the day before. If it disappears while focused without a press, focus moves to the `h2` (SDC-BD-1).
- Open rows (`openRows`, by `signal_id`) survive day changes and the rollover. Details already read stay in the store, so reopening reads nothing.
- Rows, cells, the expanded row, its actions (DC3) and *When*'s `HH:mm` are unchanged.

(source: raw/2026-10-14-signals-day-control.md §Components, `app-signals-filters`, Option list, `app-signals`, `app-signals-table` and Copy)

## How the store works

The `SignalsService` store (`feat-signals/data/signals.service.ts`, provided by the component) gained `serviceToday` (D0), `shownDay`, `isPastDay`, `shownLabel`, `shownPhrase`, `dayOptions`, `canShowYesterday`, `chooseDay(day)` and `showYesterday()`. Existing signals such as `rows`, `state`, `subLine`, `newCount` and `exportUrl` now describe the shown day.

- **Day state.** `pickedDay` holds the URL's or the reader's day, and is null for Today. `_serviceToday` holds D0. `acceptedDay` is a `linkedSignal`: a day accepted once stays accepted while it is picked, which implements PD-B. `dayStatus` is `today`, `shown`, `pending` (a pasted day waiting for D0, with nothing drawn) or `rejected` (out of window or future; the URL drops it).
- **D0 and the rollover.** `noteAnswer(generated_at)` runs inside the `httpResource` `parse` callbacks of the first page and the summary, not in an effect. It also runs for *Load more* and *Show*. It only moves D0 forward. On Today, when the list's day is now before D0, it sets `pickedDay` to the list's day. The URL effect then writes `?day=` with `replaceUrl`. The list is not read again, because the list identity (`listRef`) is unchanged and `lastPage` accepts pages by ref, query and picked day.
- **Reload across midnight (SDC-OD-2).** `keptDayFor` detects a Today reload whose page names a later day. Its `parse` drops that page and starts one `reloadList()`, which sends `day`. After fix r4 this also requires `pickedDay !== null`.
- **Seen-through.** `onListLoaded` advances it when the page is Today's and its day is not yet `seenThroughDay`. A Today load with no rows still counts as that D0's first (see [[user-settings]]).
- **Pasted-day error latch.** `heldOpening` and `openingFailed` (fix rounds r2–r4) hold a pasted day's failed opening as `error` with *Try again*, when both the list and the summary failed before D0 was known. This stops the 60 s tick from flickering it back to loading. Every intentional new list read clears the hold.
- **Sub line.** It shows a summary only when its `day` is the shown day (SDC-W-6). After a day change it reads "Loading…" until that day's summary answers.
- **Unchanged.** SE-5 (destroy releases the feed, timers and reads), MW-20 (a failed background reload keeps rows and day) and ORCH-17 (counts stay after the first list load).

**Pure helpers.**
- `pages/workspace/util/bangkok-time.ts` gained `bangkokDay(iso)`, `shiftDay(day, n)`, `daysBefore(day, ref)` and `formatDayLabel(day)`. They do calendar arithmetic on `YYYY-MM-DD` strings: dates are built at noon UTC and read back in UTC, with no zone maths and no browser clock.
- `feat-signals/util/signal-filters.ts` gained `DAY_PARAM`, `DAY_WINDOW = 7`, `parseDay`, `toDayParam`, `dayOptions` and `DayOption`. `FILTER_PARAMS` and `hasAnyFilter` are unchanged.
- `feat-signals/util/signal-view.ts` gained `dayLabel`, `dayPhrase`, `TODAY_PHRASE`, `emptyDayText`, `filterEmptyText`, `tableRegionName`, `tableCaption` and `SIGNAL_COPY.showYesterday`. `subLine` takes a phrase, and Today's output is byte-identical.

(source: raw/2026-10-14-signals-day-control.md §Components, `SignalsService` store and Pure helpers)

## Requests and the `day` URL parameter

There was **no service contract change**. `SignalsApi` (`data/signals-api.service.ts`) and `signals.model.ts` were not edited; the plan's scope check failed the build if either changed. `listRequest(query, day)`, `summaryRequest(day)` and `exportUrl(query, day)` already covered every form (source: raw/2026-10-14-signals-day-control.md §API).

| Read | Today | Past day |
|---|---|---|
| `GET /signals` first page | No `day` on the opening, a filter change, or a reload before any rollover. | `day={shown}`. After a rollover, every reload of the kept list (*Try again*, reconnect, terminal close) sends `day={kept day}`. |
| *Load more* (`cursor`) | The loaded list's `day` (unchanged). | The loaded list's `day`. |
| *Show* (`since`) | The loaded list's `day` (unchanged). | Only for a count already waiting at the rollover (S1), with the loaded day. |
| `GET /signals/summary` | The loaded Today list's `day` once there is one, else none. Read every 60 s, after *Show*, and at once on a day change. | `day={shown}` from the first read, every 60 s. |
| *Export* `href` | The loaded Today list's `day`, else none; never a past day's. | `day={shown}` from the moment it is chosen (S3). |
| Reconnect or terminal close across midnight | The next-day page is dropped, and one `GET /signals?day={kept day}` follows (SDC-OD-2). A failure keeps the rows (MW-20), and seen-through does not move. | — |

**The `day` URL parameter (client contract).**
- `?day=YYYY-MM-DD` is read only when it appears once and is a real calendar date. A repeated, malformed or impossible value such as `2026-02-30` is dropped at once, and Today loads.
- It is written with `router.navigate([], { relativeTo, queryParams, queryParamsHandling: "merge", replaceUrl: true })`. History length does not change, and the four filter parameters are kept.
- *Today* removes it. A URL whose `day` equals D0 is rewritten without it, with no extra list read.
- It is not one of `FILTER_PARAMS` (`asset`, `tier`, `source`, `min_impact`), so stored-filter precedence is unchanged (see [[user-settings]]).
- A pasted day outside the window or in the future is never drawn. Once D0 is known, the URL drops it and Today loads (S2).
- An empty URL while the page is open (the rail's *Signals* link) returns to Today and writes the filters back.

The service rules the web relies on (a day-bound cursor, `since` staying within its day, an empty page for an unknown or future day, and `generated_at` at read time as the rollover signal) are on [[signals-read-api]] (source: raw/2026-10-14-signals-day-control.md §API, Requests as implemented, Service rules and The `day` URL parameter).

## Database

There is no schema change, no migration and no new settings key. The feature changes only when the web writes the existing `user_settings` keys: `signals.filters` never carries a day, and `signals.seen_through` follows SDC-W-11. Both are described on [[user-settings]]. Rollback is a revert of the PR. No data is written beyond the existing seen-through setting (source: raw/2026-10-14-signals-day-control.md §Database).

## Design and accessibility

No token, colour, type step, icon, transition or animation was added. `tokens.css`, `theme.css` and `icons.ts` are unchanged. One placement-only rule was added for *Show yesterday*, and P3 approved the rendered result. Measurements, the rule itself, accessibility and the `DESIGN.md` refresh are on [[design-system-decisions]] (source: raw/2026-10-14-signals-day-control.md §Components, Styles, Design result and Accessibility).

## Files touched

All 21 paths are in tidewatch-web, all modified (none created), in the range `da6f4cb..e49c237`. The plan's scope check reported 22 changed paths, all planned. The 22nd is the untracked plan file `.plans/signals-day-control.md`, which was not committed. The list comes from the step reports and the scope checks, not from a `git diff`.
- **S1 (day words and forms):** `bangkok-time.ts`, `signal-filters.ts`, `signal-view.ts` and their specs.
- **S2 (store):** `signals.service.ts` and its spec, also edited in fix rounds r1–r4.
- **S3 (screen, filter row, table):** `signals-filters.ts`, `signals.ts`, `signals-table.ts` and their specs, plus `src/styles/components/signals.css`.
- **S4 (Playwright):** `e2e/src/support/signals.ts`, `e2e/src/support/screens.ts` and `e2e/src/signals.spec.ts`.
- **S5 and P4 (docs):** `DESIGN.md`, `README.md` and `CLAUDE.md`.

**Not changed:** `signals-api.service.ts`, `signals.model.ts`, `new-signals.ts`, `signals-badge.service.ts`, the shell and rail, `signal-detail.ts`, Trade, `tokens.css`, `theme.css`, `icons.ts`, `section.css`, `button.css` and `e2e/src/signals-live.spec.ts`. tidewatch-service, tidewatch-migrations, tidewatch-bot, `tidewatch-apis` and `documents/` were not changed either.

**Docs in the repo.** The README's "Signals" section covers the day control, `?day=`, past-day reading, the rollover, *Show yesterday* and the seen-through rule in "The rail count". The web `CLAUDE.md` (outside the managed blocks, which stayed byte-identical) covers the shown day, D0, the rollover, the reload across midnight, past-day counting, seen-through, the export's day and the e2e mock notes.

(source: raw/2026-10-14-signals-day-control.md §Files touched; §Components, Docs in the repo)

## Test plan and acceptance

There is no CI. Commands run in `tidewatch-platform/tidewatch-web`:
- `pnpm nx test tidewatch-web`, and `TZ=America/New_York pnpm nx test tidewatch-web --skip-nx-cache` (3,138 tests at `cef0be9`).
- `pnpm nx lint tidewatch-web`, `pnpm nx build tidewatch-web` and `pnpm nx run e2e:lint`.
- The plan checks (`.forge/features/signals-day-control/planning/tidewatch-web/checks/plan-checks.mjs`). They check that there is no browser clock (`Date.now()` or `new Date()`) in `feat-signals/` and `bangkok-time.ts`. They also check for no new colour or motion in `signals.css`, that no existing test title was lost, the e2e type-check, and that the Playwright titles exist.
- **Playwright runs on a preview only.** The `authed` project needs a real sign-in, so in the worktree the specs are only listed, linted and type-checked.

**Unit specs (Vitest).**
- The helper specs cover the 17:00Z boundary on both sides; month and year ends (31 Oct → 1 Nov, 31 Dec → 1 Jan, 29 Feb); "Sat 10 Oct" with no leading zero; malformed, repeated or impossible days; `FILTER_PARAMS` still exactly four names; and every Today sentence unchanged.
- The store spec covers every request in the table above, the `replaceUrl` merge, the D0 rewrite with no second read, S1, S2, PD-B, seen-through per SDC-W-11, SDC-OD-2 and the error latch. One named example is "relabels Today as Yesterday at the rollover without reading the list again".
- Each fix round showed its new specs failing against the previous source: r1 6, r2 6, r3 5, r4 3.

**Playwright (`e2e/src/signals.spec.ts`, mocked, fail-closed, `@authed`).** Twelve new tests were added, among them "relabels Today as Yesterday at Bangkok midnight without reading the list again" and "writes seen-through after the first Today load and Show but never after a past day". Two existing tests were extended: the Export link and keyboard reach. `SIGNALS_STATES` gained `yesterday`, `dated-day`, `past-empty` and `past-filter-empty`. The mock's opt-in second day (`SUNDAY_FIXTURES`) reads `generated_at` from the page's faked clock (SDC-W-9). The rollover tests install `page.clock` at `BEFORE_MIDNIGHT` (`2026-10-11T16:59:30Z`) and advance 65 s.

(source: raw/2026-10-14-signals-day-control.md §Test plan, Commands, Unit specs and Playwright)

### Acceptance status (PRD §9)

| IDs | Status | Evidence / note |
|---|---|---|
| FR-SDC-WEB-001, 002, 003, 004, 005, 009, 010, 011 | Verified | Vitest plus P1, with request-log, URL, `history.length` and DOM attachments. 003, 008 and 010 were also seen on real data in P2. |
| FR-SDC-WEB-006 | Verified | P1 `page.clock` across 17:00Z. **SDC-OD-2's reconnect re-read and SDC-BD-1's focused-button path are Vitest only.** |
| FR-SDC-WEB-007 | Verified | Vitest; the PRD names no browser check. |
| FR-SDC-WEB-008 | Verified | Vitest, P1, and P2's real "No signals yesterday.". |
| FR-SDC-WEB-012 | Verified | P3 approved. PRD A2 ("Wed 30 Sep" on one line) was judged by proxy, using "Sun 11 Oct"/"Sat 10 Oct" at 390. Advisory A10 is open. |
| FR-SDC-WEB-013 | Verified | S5 doc checks, then P4 `impeccable --check` (no drift, 106/106) and the Verification evidence entry. |
| FR-SDC-WEB-014 | Verified | 3,138 unit tests in both zones; P1 full suite with 0 failures. |
| FR-SDC-E2E-001 | **Partial** | The literal Yesterday-with-rows case is **unverified**: the preview's Yesterday (13 Oct) had no signals. The real-data comparison ran on Mon 12 Oct instead and matched SQL in full. |

**Outcomes.** O1–O4 were implemented and verified on the preview through the IDs above. The owner signed off at the outcome level when instructing the merge (source: raw/2026-10-14-signals-day-control.md §Test plan, Acceptance status).

**P2 detail (FR-SDC-E2E-001), about 08:35 Bangkok on 14 Oct.**
- SQL counts by Bangkok day: 14 Oct 10 (2 at ≥ 0.30), 13 Oct 0, 12 Oct 6 (1 at ≥ 0.30).
- On Mon 12 Oct, at `min_impact` 0.30 and 0.00, everything matched SQL: API ids and order (1/1, 6/6), rendered rows and times, the summary `today` (6 = 6), and the data rows of `signals-2026-10-12.csv` (1 = 1, 6 = 6).
- Yesterday (13 Oct) rendered correctly as empty ("No signals yesterday.", with `day=2026-10-13` on the list and the export), but there were no rows to compare.
- Today sent no `day` on the list.

The preview run itself is described on [[forge-preview-gateway]] (source: raw/2026-10-14-signals-day-control.md §Test plan, Preview).

### Manual reproduction

1. With signals on earlier Bangkok days, open `/signals` and choose *Yesterday* in the *Day* select. The URL gains `?day=` and history length does not change. The heading reads *Yesterday* and the sub line "{n} yesterday · …". *Export* links `…/signals/export.csv?…&day={that day}`, and no `PUT /me/settings/signals.filters` is sent.
2. Compare the rows and the sub line's count with a SQL count of `signals` whose `created_at`, shifted to UTC+07:00, falls on that day, using the default filters and `min_impact=0.00`. Count the export's data rows too. This is FR-SDC-E2E-001; it still needs doing on a day whose Yesterday has signals.
3. Paste `?day=` for a date 8 days back, or one in the future. Nothing of that day is drawn, the URL drops `day`, and Today loads.
4. Keep the page open on Today across 17:00Z. Within one 60 s summary interval, the heading, select, region and caption read *Yesterday*, the URL gains `?day=`, and the network log shows no `GET /signals`.
5. On an empty Today, *Show yesterday* follows the empty sentence. Pressing it moves focus to the heading and selects the day before.

(source: raw/2026-10-14-signals-day-control.md §Test plan, Manual reproduction)

## Open items

**Unverified at merge (the owner knew).**
- FR-SDC-E2E-001 with *Yesterday* holding real signals; the preview's 13 Oct had none.
- These ran only in Vitest or were checked by proxy, never in a real browser: SDC-OD-2's reconnect re-read; SDC-BD-1 (a focused *Show yesterday* removed at a rollover); the held pasted-day error and a filter undo; and the literal "Wed 30 Sep" label (PRD A2).
- Screen readers, and the owner's own or production data.

**Not deployed.** The web change is only merged. No database or service step is needed to deploy it.

**Accepted trade-offs.** SDC-OD-1: rows still waiting behind *Show* at a rollover are marked seen by the new Today's first load. SDC-OD-2: one extra list read after a reconnect that crosses midnight.

**Follow-ups (`state.json` `followUps`).**
- The *Export* `href` carries an unchecked pasted out-of-window or future day while it waits for D0 (code r1 nit).
- The sub line can read "Loading…" for up to 60 s when a Today list's day passes the last summary's day before the tick (code r1 nit).
- A pasted `?day=` with an emptied filter group whose summary fails still shows Loading, not the error (fix r1 residual).
- Focus falls to the document when a held pasted-day error ends by the out-of-window fallback to Today (design r3 A7; rare).
- Pre-existing, not from this feature: `firstLoadSeen.set(true)` runs inside the list-loaded effect (angular r3).
- An optional spec for the `sameAttempt` second guard (code r5).
- A tighter SDC-W-8 selector (design A1), and A10, the *Show yesterday* focus ring (see [[design-system-decisions]]).

(source: raw/2026-10-14-signals-day-control.md §Open questions)

## After merge: the refused-day race (fixed by charting's PF1, 2026-10-16)

The charting build's first preview suite (see [[charting]]) failed the Signals test "never draws an out-of-window or future day and ends on Today" on the production build. The same test **failed 2/2 on `main` at `976233f`**, the day control's merge commit, so the defect was already present when this feature merged. It is a timing race, not a date dependence.
- **Symptom.** A pasted out-of-window `?day=` stayed on "Loading signals…" forever, instead of ending on Today as S2 requires.
- **Cause.** A refused pasted day's late list page was taken as a midnight rollover (`signals.service.ts` around lines 463, 482 and 1074). So the store picked the refused day again after the URL had dropped it.
- **Fix (PF1, `5476985`).** A first page whose `day` does not answer the request that sent it (`answersDay`: `page.day === (sentDay ?? bangkokDay(generated_at))`) now only updates D0 (`noteAnswer`). It starts no rollover and no re-read, and the resource drops it. The new case in `signals.service.spec.ts` fails 1 of 67 with the guard off. It is a recorded scope extension of the charting build, included because it blocked the production-build preview run.
- **Status.** Merged with tidewatch-web #14 (`918d7b6`) on 2026-10-16; **not deployed**. The test passed in charting's later preview rounds.
- **Follow-ups (code r4, angular r4).** Also check `loaded.ref === untracked(listRef)`, and restrict the rollover pick to pages with `sentDay === null`.
- **Also seen, pre-existing and flaky.** "opens Add source and returns focus" in `signals.spec` fails intermittently on production builds (the base head failed 6 of 12 runs). It passed in charting's second production run and is a follow-up.

**The Chart links here.** Each *Signals on this chart* item links to `/signals?day={Bangkok day of created_at}`. Under DC5 above, a day inside the last-7-days window opens on that day, and an older one falls back to Today.

(source: raw/2026-10-16-charting.md §Test plan, Defects found on the preview and their fixes, PF1 item 3; §Files touched, tidewatch-web PF1; §Components, The Chart screen; §Cross-cutting links; raw/2026-10-14-signals-day-control.md §Concept, Owner decisions DC5)

## Related pages

- [[signals-page]]: the slice-4 screen this extends, and where ORCH-19 was recorded
- [[signals-read-api]]: the existing `day` parameter, the Bangkok day, the day-bound cursor and `generated_at` at read time
- [[user-settings]]: `signals.filters` never carries the day, and the seen-through rules (SDC-OD-1, SDC-W-11)
- [[design-system-decisions]]: the *Day* `.chip-select`, the placement-only rule, P3 and the `DESIGN.md` refresh
- [[signal-message-contract]]: how live frames are counted only while the list is Today (SDC-W-1)
- [[realtime-websocket]]: the all-signals feed and the reconnect that reloads the shown day (SDC-OD-2)
- [[signals-ingest]]: where signal history begins; `signals` has no retention
- [[signal-cited-orders]]: the recommendation actions kept on past days (DC3)
- [[forge-preview-gateway]]: the `sdc-1aa0b0c9` preview and the run-mapping extension
- [[charting]]: slice 5, whose PF1 fixed the refused-day race and whose feed items link to `?day=`
