# Signals page day control (`signals-day-control`, ORCH-19): a last-7-days *Day* select, `?day=` in the URL, past days that read as the past, and the midnight relabel

> Slice 4 shipped a Signals screen that showed only the service's current Bangkok day. After Bangkok midnight it was empty, and a page left open kept calling the old day "Today" (ORCH-19). This web-only feature added a *Day* select, first in the Signals filter row. It lists the service's today and the six days before it: *Today*, *Yesterday*, then dates such as "Sat 10 Oct". The shown day lives only in `?day=YYYY-MM-DD`, which is written with `replaceUrl` and never stored. A past day names itself in the heading, the sub line, the table's name and caption, the empty sentences and the export. It never counts live frames, never offers *Show* (except for a count already waiting at midnight) and never advances seen-through. At Bangkok midnight, a page open on Today keeps its rows and relabels them *Yesterday* within one 60 s summary tick, without reading the list again. An empty Today offers *Show yesterday*. "Today" always comes from the service's `generated_at`, never from the browser clock. The service, migrations and bot were not changed, because the API already took `day`. tidewatch-web PR #13 merged on 2026-10-14 at 06:58:59Z (head `e49c237`, merge commit `976233f`) on the owner's instruction. 14 of the 15 acceptance IDs were verified. FR-SDC-E2E-001 is **partial**: the preview had no real signals on its Yesterday, so the real-data comparison ran on an earlier dated day instead, where it matched SQL in full. The change is merged but **not deployed**.

**Sources (inputs to this document).**
- Spec: `/Users/maichinu/tidewatch/tidewatch-specs/signals-day-control/build-prompt.md`, `intent.md` (O1–O4, DC1–DC9, PD-A…PD-C) and `prd.md` (§3 terms and S1–S6, §4 behaviour, §7 design, §9 `FR-SDC-*`, §11 A1–A3). Both fingerprints matched at build start: intent `a5ee8194…ba66`, prd `3201e699…a697`.
- Plan: `/Users/maichinu/tidewatch/.forge/features/signals-day-control/artifacts/plans/tidewatch-web.md` (approved at r2, sha256 `2df746c9…`; steps S1–S5, decisions SDC-W-1…11, preview checks P1–P4).
- Build record: `/Users/maichinu/tidewatch/.forge/features/signals-day-control/state.json` (log, `ownerDecisions`, `buildDecisions`, `followUps`, `runtime.acceptance`, `merged`), `verification.md`, `planning/owner-decisions.md` (SDC-OD-1), `planning/owner-decisions-review.md` (SDC-OD-2), `review/tidewatch-web/` (r1–r5 and `P3/design-rendered.md`), `evidence/tidewatch-web/{S1…S5,R1…R4,P1,P4}/` and `evidence/preview/P2/SUMMARY.md`.
- Merged code, read in the build worktree `/Users/maichinu/tidewatch/.forge/docker/runs/sdc-1aa0b0c9/worktrees/5eb4e5c7ea` at `e49c237`, together with its `CLAUDE.md`, the README "Signals" section and `DESIGN.md`.

## Concept

### Stage, stated precisely

| Stage | Status (state.json, last update 2026-10-14T06:59:24Z) |
|---|---|
| Implemented | Steps S1 `19a6364`, S2 `481556e`, S3 `ee9c9cf`, S4 `560e54c` and S5 `9cc3fd3`. Review-fix rounds r1 `7cf44dc`, r2 `3c11b88`, r3 `6e0d938` and r4 `cef0be9`. P4 design refresh `e49c237` (`DESIGN.md` only). |
| Verified locally | Every step's and every fix round's contract commands exited 0. At `cef0be9`: `pnpm nx test tidewatch-web` ran 3,138 tests in 94 files, in the host zone and again under `TZ=America/New_York`. Lint, build, e2e lint, the e2e type-check, Prettier on the owned files and the plan checks (scope, titles, no browser clock, no new colour or motion, doc checks, managed blocks) also passed. |
| Reviewed | **Plan:** r1 CHANGES REQUESTED, then r2 APPROVED. **Code:** five rounds, each by four reviewers (angular, design, code, security). Round 5 at `cef0be9` was all APPROVED, with no blocking or should-fix finding. See "Review history". |
| Verified on a preview | **P1:** Playwright 770 passed / 0 failed / 4 live-gated skips. **P2:** FR-SDC-E2E-001 partial. **P3:** rendered design review APPROVED. **P4:** `forge-setup-impeccable --check` reported no drift (106/106). Result: 14 of 15 IDs verified, none failed. |
| Merged | Yes, 2026-10-14T06:58:59Z: tidewatch-web#13 as a merge commit with `--match-head-commit e49c237`, giving `976233f`. The orchestrator merged on the owner's instruction "merge it and continue". No other repository merged. |
| Deployed | No. No migration, environment or service step is needed; the web deploys alone. |
| Documentation pass | This document and the wiki update (worktree `docs-7ce006e44c` at wiki `b3b3ed1`). `tidewatch-specs` and `tidewatch-apis` are not Git repositories and were not changed. |

`verification.md` was written at the merge pause, so its closing line still reads "Merged: no (awaiting the owner)". The merge itself is recorded in `state.json` (`perProject.tidewatch-web.merged`).

### Problem

On 2026-10-13 the owner opened Signals just after Bangkok midnight, found it empty, and asked for a way to read earlier days. This was ORCH-19, recorded in the signals-page build at 2026-10-12T18:24Z (01:24 on 10-13 Bangkok) as "keep today-only for this build, add a day control after the merge".

The intent verified these facts on 2026-10-13, at web `da6f4cb`, service `8b18486` and migrations `52deb26`:
- **The API already took `day`.** `GET /signals`, `GET /signals/summary` and `GET /signals/export.csv` accept `day=YYYY-MM-DD`: a Bangkok day, defaulting to the service's today. The parser has no range check, so a future or pre-history day answers an empty page.
- **History.** `signals` has no retention policy. History begins with slice 3a (2026-10-11).
- **The web never sent `day` on a first read.** It carried the answered `day` only on *Load more*, *Show*, the summary and the export.
- **Midnight with the page open.** The page stayed on the day it had loaded and still called it *Today*. The new day's frames were not counted. A filter change or a reconnect then reloaded into the new, empty day.
- **The badge counts 7 days back,** but the page could show only today. Opening the page advanced seen-through to today's newest row, which cleared earlier days' unseen signals without ever showing them.

The interview ran in chat (the `grilling` skill) because the Forge Console Spec studio reported no attached display. The owner took every recommended option in both rounds.

### Outcomes (intent)

- **O1.** Any of the last 7 Bangkok days can be read from the screen.
- **O2.** Midnight never blanks or mislabels the page.
- **O3.** A past day reads honestly as the past.
- **O4.** Links and reloads reproduce the view.

### Terms (PRD §3)

| Term | Meaning |
|---|---|
| D0 (service today) | The Bangkok day (fixed UTC+07:00) of the latest `generated_at` the page has read from any first page, *Load more*, *Show* or summary answer. It never moves backwards, never comes from the browser clock, and is unknown until the first answer. Bangkok day D covers `[D−1 17:00Z, D 17:00Z)`. |
| Window | D0 and D0−1 … D0−6. |
| Shown day | The URL's `day` when present, else D0. A *past day* is a shown day before D0. |
| Day label | *Today* (D0), *Yesterday* (D0−1), else "{Ddd} {d} {Mon}" in en-US short forms with no leading zero, e.g. "Sat 10 Oct". |
| Day phrase | "today", "yesterday" or "on {Day label}" ("on Sat 10 Oct"), used inside sentences. |
| Rollover | D0 advancing while the page is open. |

### Owner decisions (intent, 2026-10-13; each the recommended option)

| ID | Decision | Rejected |
|---|---|---|
| DC1 | A last-7-days *Day* select, built as `label.chip.chip-select` like *Impact ≥*. Its options are *Today*, *Yesterday*, then five dates. This matches the badge's 7-day window. | Today/Yesterday chips (Friday from Monday would need a hand-edited URL). Chips plus an *Earlier* select (three controls, the most wrapping at 390). |
| DC2 | At Bangkok midnight on Today, stay on the day being read. Within about 60 s it relabels as *Yesterday*, and the URL gains `?day=` with `replaceUrl`. No reload, no row change. | Switching to the new, empty day. Leaving the mislabel. |
| DC3 | *Buy / Sell with recommendation* stays on past days, unchanged. | Yesterday only. Hidden on past days. |
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
- **S1.** A new-rows count already waiting at the rollover keeps *Show* until revealed.
- **S2.** A pasted out-of-window or future day is checked once D0 is known. It is never drawn, the URL drops it with `replaceUrl`, Today loads, and the section stays loading throughout.
- **S3.** *Export*'s `day` is the shown day from the moment it is chosen.
- **S4.** A day change behaves like a filter change: the rows drop to loading, the list and summary are read again, the count restarts, focus stays on the select, and open rows are kept by `signal_id`.
- **S5.** Seen-through advances after the first successful Today load and after *Show*, never after a past day's load or *Load more*.
- **S6.** Day words come from `YYYY-MM-DD` strings by calendar arithmetic in the Bangkok helpers.

### Decisions taken during the build

- **SDC-OD-1 (owner, 2026-10-13T02:31:15Z; plan review r1, blocker 2).** The first successful load of each new D0 shown as Today advances seen-through, including the new Today after a midnight rollover. Accepted cost: old-day rows still waiting behind *Show* at the rollover are marked seen too. Recorded in the plan as SDC-W-11.
- **SDC-OD-2 (owner, 2026-10-13T05:15:28Z; code review r2).** A reconnect or terminal-close reload of Today can cross midnight before the summary tick. When it answers the next day, the page does not take that page. Instead it re-reads the kept day once by date (`day=X`), so "a reconnect reloads the shown day" (PRD §4.7). This costs one extra list read in that case only; the plain midnight relabel still makes no list read. It is recorded in `owner-decisions-review.md`, because the approved plan fingerprints `owner-decisions.md`, which had to stay byte-identical.
- **SDC-BD-1 (build, design review r1 W1 / r2 A5; fix round 1).** If *Show yesterday* has keyboard focus when a rollover on an empty Today removes it, focus moves to the day's `h2` (the SE-11 rule). Focus cannot stay on a removed button; all other focus is left alone.
- **Fix-round cap override (owner, 2026-10-14T00:57:25Z).** The owner authorised a fourth review-fix round past the cap of 3.

**Plan reconciliations within the PRD's latitude (SDC-W-1…10).**
- **SDC-W-1.** `new-signals.ts` stays byte-identical. The store passes it the list's `generated_at` only while the list is Today. On a past day, including after a rollover, it passes `null`, so no new frame counts, while ids already counted stay with *Show*.
- **SDC-W-2.** A list's identity is its query plus its resolved day. Learning D0, the rollover's switch from an absent `day` to `day={loaded}`, and rewriting `?day={D0}` to absent all make no `GET /signals` and keep the view. Choosing *Today* after a rollover starts a new list.
- **SDC-W-3.** On Today the summary and export send the loaded Today list's `day`, or none. They never send a past day's.
- **SDC-W-4.** The day lives beside the filters in the store, outside `FILTER_PARAMS`, and is written in one merge navigation with `replaceUrl`.
- **SDC-W-5.** `signal-filters.ts` only parses `day`; the window check, which needs D0, is the store's.
- **SDC-W-6.** The sub line shows a summary only when the summary's `day` is the shown day.
- **SDC-W-7.** The store computes the options; the filters component stays presentational. The `<select>` node is kept when its options change.
- **SDC-W-8.** CSS is limited to placement.
- **SDC-W-9.** The Playwright second day is opt-in, and the mock reads the page's faked clock.
- **SDC-W-10.** The drifted signals-page plan entry in `DESIGN.md`'s Source snapshot was repointed to `.forge/features/signals-page/artifacts/plans/tidewatch-web.md` (same SHA-256 `910c45ff…`).

### Review history

| Round | Head | Verdicts | What followed |
|---|---|---|---|
| Plan r1 | `b58c375b…` | CHANGES REQUESTED. Blocking: S5's checks did not prove the doc edits; seen-through after a rollover needed the owner. Should-fix: E2E-001 was in no step; no spec for focus staying on the select or for open rows being kept. | SDC-OD-1; planner r2. |
| Plan r2 | `2df746c9…` | APPROVED (0/0). | Approved 2026-10-13T02:45:36Z. |
| Code r1 | `9cc3fd3` | All four APPROVED. Should-fix: a pasted day's failed opening showed Loading; a Today reload crossing midnight replaced the kept rows. Design W1–W4. | The orchestrator chose a should-fix round; fix r1 `7cf44dc` (6 new specs). |
| Code r2 | `7cf44dc` | All four APPROVED. Remaining: the pasted-day error flickered with the 60 s tick (a11y), and a reconnect after midnight missed rows (an owner question). | SDC-OD-2; fix r2 `3c11b88` (error latch plus the kept-day re-read). |
| Code r3 | `3c11b88` | Angular CHANGES REQUESTED: an effect wrote a store signal through `onFirstPage`/`reloadList`, contrary to angular-signals. Code, design and security APPROVED. | Fix r3 `6e0d938`: the re-read trigger moved into the page resource's `parse` callback; the latch resets on a new list read. |
| Code r4 | `6e0d938` | All four APPROVED. Non-gating: a stale hold on an A→B→A filter revert, an unpinned tick-guard spec, an optional `pickedDay` guard. | Cap reached; the owner authorised fix r4 `cef0be9`. |
| Code r5 | `cef0be9` | All four APPROVED, nothing blocking. | Review gate passed 2026-10-14T01:11:46Z; PR opened 01:12:51Z. |

## Database

No schema change, no migration and no new settings key. The feature changes only when the web writes the existing keys of `user_settings` (see [[user-settings]]):
- **`signals.filters`** never carries a day. Changing the day sends no `PUT /me/settings/signals.filters` (PD-C).
- **`signals.seen_through`** is written through `SignalsBadgeService.advanceSeenThrough` (unchanged; the stored value never moves backwards). Writes follow SDC-W-11:
  - **written** after the first successful Today load of each D0 the page shows, and after every *Show* (including S1's reveal after a rollover);
  - **never written** after a past day's load, another load of a Today already advanced for, *Load more*, or the SDC-OD-2 re-read.

Rollback is a revert of the PR. No data is written beyond the existing seen-through setting.

## API

**No service contract change.** The web uses the `day` parameter that `GET /signals`, `GET /signals/summary` and `GET /signals/export.csv` already accepted (see [[signals-read-api]]). `SignalsApi` (`data/signals-api.service.ts`) was not edited: `listRequest(query, day)`, `summaryRequest(day)` and `exportUrl(query, day)` already covered every form, and `isSignalDay` in `signals.model.ts` validates a day. The plan's scope check failed the build if either file changed.

**Requests as implemented (PRD §4.3, SDC-W-3, SDC-OD-2).**

| Read | Today | Past day |
|---|---|---|
| `GET /signals` first page | No `day` (the service's today) on the opening, a filter change, or a reload before any rollover. | `day={shown}`. After a rollover, every reload of the kept list (*Try again*, reconnect, terminal close) sends `day={kept day}`. |
| *Load more* (`cursor`) | The loaded list's `day` (unchanged). | The loaded list's `day`. |
| *Show* (`since`) | The loaded list's `day` (unchanged). | Only for a count already waiting at the rollover (S1), with the loaded day. |
| `GET /signals/summary` | The loaded Today list's `day` once there is one, else none. Read every 60 s, after *Show*, and at once on a day change. | `day={shown}` from the first read, every 60 s. |
| *Export* `href` | The loaded Today list's `day`, else none; never a past day's. | `day={shown}` from the moment it is chosen (S3). |
| Reconnect or terminal close across midnight | The next-day page is dropped; one `GET /signals?day={kept day}` follows (SDC-OD-2). A failure keeps the rows (MW-20); seen-through does not move. | — |

**Service rules the web relies on.** The cursor is bound to the day. A `since` read stays within the day it names. An unknown or future day answers an empty page with `hidden_by_threshold` 0. The service answers `generated_at` at read time for any `day`, so a summary whose `generated_at` is on a later Bangkok day than the `day` it asked for signals the rollover (A1; held in the store specs and the P1 clock test).

**The `day` URL parameter (client contract).**
- `?day=YYYY-MM-DD`, read only when it appears once and is a real calendar date. A repeated, malformed or impossible value such as `2026-02-30` is dropped at once, and Today loads.
- It is written with `router.navigate([], { relativeTo, queryParams, queryParamsHandling: "merge", replaceUrl: true })`, so history length does not change and the four filter parameters are kept.
- *Today* removes it, and a URL whose `day` equals D0 is rewritten without it, with no extra list read.
- It is not one of `FILTER_PARAMS` (`asset`, `tier`, `source`, `min_impact`), so the stored-filter precedence is unchanged.
- A pasted day outside the window or in the future is never drawn. Once D0 is known, the URL drops it and Today loads (S2).
- An empty URL while the page is open (the rail's *Signals* link) returns to Today and writes the filters back.

## Components

Angular 22.1 standalone components, signals, `linkedSignal` and `httpResource`. No token, colour, type step, icon, transition or animation was added. `tokens.css`, `theme.css` and `icons.ts` are unchanged (P3 confirmed the empty diff). See [[design-system-decisions]].

**`app-signals-filters` (`feat-signals/signals-filters.ts`).**
- New inputs `dayOptions: readonly DayOption[]` and `shownDay: string | null`, and a new output `dayChange: string | null`.
- It draws, first in the row, `label.chip.chip-select` > `span#signal-filter-day-label` "Day" + native `<select aria-labelledby>`, built exactly like *Impact ≥*, followed by an `aria-hidden` `.sep`. The separators still hide at ≤ 600.
- Options are tracked by `day`, so the `<select>` node survives an options change (focus and value are kept at a rollover). Before D0 is known, the dateless *Today* option has the value `""`.
- The select is never disabled. It stays presentational: it emits the option's `day`, and the store does the rest.

**Option list (`dayOptions` in `util/signal-filters.ts`, SDC-W-7, PD-A, PD-B).**
- With D0 known: D0 (*Today*), D0−1 (*Yesterday*), then D0−2 … D0−6 by date label, plus a shown day outside that window as an extra last option.
- Before D0: *Today* alone, or the URL's day alone by its date label.
- On the preview, with D0 Wed 14 Oct, it read *Today*, *Yesterday*, "Mon 12 Oct" … "Thu 8 Oct".

**`app-signals` (`feat-signals/signals.ts`).**
- It passes `store.dayOptions()` and `store.shownDay()` to the filters, and binds `(dayChange)` to `store.chooseDay($event)`.
- The section `h2` reads `store.shownLabel()` (*Today*, *Yesterday*, "Sat 10 Oct"). It keeps `id="signals-today-title"` and `tabindex="-1"`, and a rollover relabels it in place.
- The empty and filter-empty sentences come from `emptyDayText` / `filterEmptyText` of the shown phrase.
- ***Show yesterday*** is a `button.text-btn` placed after a space inside the same dashed `p.status-line`. It renders only while `store.canShowYesterday()`: Today, state `empty`, and D0 known. Pressing it first focuses the `h2` (the button goes while the day before loads), then calls `store.showYesterday()`. If the button disappears while focused without a press (a rollover, or a reload bringing rows), focus moves to the `h2` (SDC-BD-1).
- The open-row set (`openRows` by `signal_id`) survives day changes and the rollover. Details already read are kept in the store, so reopening reads nothing.

**`app-signals-table` (`feat-signals/signals-table.ts`).**
- New required input `phrase`. The scroll region's `aria-label` is `tableRegionName(phrase)` and the hidden caption is `tableCaption(phrase)`.
- Rows, cells, the expanded row, its actions (DC3; `signal-detail.ts` not edited) and *When*'s `HH:mm` are unchanged.

**Copy (PRD §4.4–§4.6, verbatim in `util/signal-view.ts`).**

| Piece | Today | Past day |
|---|---|---|
| Sub line | "{n} today · {n} acted on by bots · {n} contradicted by price" (unchanged) | "142 yesterday · 0 acted on by bots · 3 contradicted by price", "88 on Sat 10 Oct · …" |
| Section `h2` | *Today* | *Yesterday*, *Sat 10 Oct* |
| Region name / caption | "Signals today, scrollable table" / "Signals today" | "Signals yesterday, …" / "Signals on Sat 10 Oct" |
| Empty day | "No signals yet today. Signals appear within seconds of a filing, release or exchange notice becoming a scored event." + *Show yesterday* | "No signals yesterday." / "No signals on Sat 10 Oct." |
| Filters show nothing | "No signals match these filters today." | "No signals match these filters yesterday." / "No signals match these filters on Sat 10 Oct." |
| Loading, error | "Loading signals…", "Signals couldn't load." + *Try again* | Same |
| Note | "Newest first · Asia/Bangkok", plus "· {n} more under Impact ≥ {t}" | Same; never a new-rows count except S1 |

A day before signal history began reads as an empty past day. The empty-day test is unchanged: the shown day's summary answers 0; without it, the unfiltered query with nothing hidden.

**`SignalsService` store (`feat-signals/data/signals.service.ts`, component-provided).**
- **Public additions.** `serviceToday` (D0), `shownDay`, `isPastDay`, `shownLabel`, `shownPhrase`, `dayOptions`, `canShowYesterday`, `chooseDay(day)` and `showYesterday()`. Existing signals (`rows`, `state`, `subLine`, `newCount`, `exportUrl`, …) now describe the shown day.
- **Day state.**
  - `pickedDay` holds the URL's or the reader's day (null for Today).
  - `_serviceToday` holds D0.
  - `acceptedDay` is a `linkedSignal`. A day accepted once stays accepted while it is picked, which implements PD-B.
  - `dayStatus` is one of `today`, `shown`, `pending` (a pasted day waiting for D0, nothing drawn) or `rejected` (out of window or future; the URL drops it).
- **D0 and the rollover.** `noteAnswer(generated_at)` runs inside the `httpResource` `parse` callbacks of the first page and the summary (not in an effect), and also for *Load more* and *Show*. It moves D0 forward only. On Today, when the list's day is now before D0, it sets `pickedDay` to the list's day. The URL effect then writes `?day=` with `replaceUrl`, and the list is not read again: the list identity (`listRef`) is unchanged, and `lastPage` accepts pages by ref, query and picked day.
- **Reload across midnight.** `keptDayFor` detects a Today reload whose page names a later day. Its `parse` drops that page and starts one `reloadList()`, which sends `day` (SDC-OD-2). After fix r4 this also requires `pickedDay !== null`.
- **Seen-through.** `onListLoaded` advances it when the page is Today's and its day is not yet `seenThroughDay`. A Today load with no rows still counts as that D0's first.
- **Pasted-day error latch.** `heldOpening`/`openingFailed` (fix rounds r2–r4) hold a pasted day's failed opening (list and summary both failed before D0) as `error` with *Try again*. This stops the 60 s tick from flickering it back to loading. Every intentional new list read clears the hold.
- **Sub line.** It shows a summary only when its `day` is the shown day (SDC-W-6); after a day change it reads "Loading…" until that day's summary answers.
- **Unchanged.** SE-5 (destroy releases the feed, timers and reads), MW-20 (a failed background reload keeps rows and day) and ORCH-17 (counts stay after the first list load) are unchanged.

**Pure helpers.**
- `pages/workspace/util/bangkok-time.ts` gained `bangkokDay(iso)`, `shiftDay(day, n)`, `daysBefore(day, ref)` and `formatDayLabel(day)` ("Sat 10 Oct"). These are calendar arithmetic on `YYYY-MM-DD` strings: dates are built at noon UTC and read back in UTC, with no zone maths and no browser clock.
- `feat-signals/util/signal-filters.ts` gained `DAY_PARAM`, `DAY_WINDOW = 7`, `parseDay`, `toDayParam`, `dayOptions` and `DayOption`. `FILTER_PARAMS` and `hasAnyFilter` are unchanged.
- `feat-signals/util/signal-view.ts` gained `dayLabel`, `dayPhrase`, `TODAY_PHRASE`, `emptyDayText`, `filterEmptyText`, `tableRegionName`, `tableCaption` and `SIGNAL_COPY.showYesterday`. `subLine` takes a phrase; Today's output is byte-identical.

**Styles.** One placement-only rule (SDC-W-8) in `src/styles/components/signals.css` (+12/−1, including the header comment):

```css
.signals-section .status-line .text-btn {
    padding: 0;
    line-height: inherit;
    vertical-align: baseline;
}
```

**Design result (P3).**
- The Day chip measures 117×26, against *Impact ≥* at 114×26, with identical borders, colours and focus ring.
- No horizontal page scroll in 60/60 captures; the table is 862/862 at 1100.
- The `h2` and count stay on one line in every state, width and theme. At 390 the Day chip takes its own row (+34px), which was accepted.
- axe found 0 violations in 32 files. Minimum contrast is unchanged at 4.85 (the existing light `.dir.change-down`).

**Accessibility.**
- The select is in the Tab order between *Add source* and *All assets*, with the accessible name "Day"; the native control announces its value.
- Day changes announce through the existing polite state region ("Loading signals…", then rows or a sentence).
- *Show yesterday* is a native button with the `.text-btn` focus ring.

**Docs in the repo.**
- `DESIGN.md`: the filter row with *Day*, the day-named `h2`, the past-day states and copy, *Show yesterday*, the accessibility notes, the SDC-W-8 rule, a refreshed Source snapshot (adds the day-control PRD and intent and `bangkok-time.ts`; SDC-W-10), and a "Signals day control" Verification evidence entry citing P1–P3 (P4).
- README "Signals": the day control, `?day=`, past-day reading, the rollover, *Show yesterday*, and the seen-through rule in "The rail count".
- `CLAUDE.md` (outside the managed blocks, which stayed byte-identical): the shown day, D0, the rollover, the reload across midnight, past-day counting, seen-through, the export's day, and the e2e mock notes.

## Files touched

All 21 paths are in tidewatch-web, all **modified** (none created), range `da6f4cb..e49c237`. The plan's scope check reported 22 changed paths, all planned; the 22nd is the untracked plan file `.plans/signals-day-control.md`, which was not committed. No `git diff` was run for this document. The list comes from the step reports and the scope checks.

- **S1 (day words and forms):**
  - `src/app/pages/workspace/util/bangkok-time.ts`, `bangkok-time.spec.ts`
  - `src/app/pages/workspace/feat-signals/util/signal-filters.ts`, `signal-filters.spec.ts`
  - `src/app/pages/workspace/feat-signals/util/signal-view.ts`, `signal-view.spec.ts`
- **S2 (store):** `src/app/pages/workspace/feat-signals/data/signals.service.ts`, `signals.service.spec.ts`. Also edited in fix rounds r1–r4.
- **S3 (screen, filter row, table):**
  - `src/app/pages/workspace/feat-signals/signals-filters.ts`, `signals-filters.spec.ts`
  - `src/app/pages/workspace/feat-signals/signals.ts`, `signals.spec.ts` (also r1)
  - `src/app/pages/workspace/feat-signals/signals-table.ts`, `signals-table.spec.ts`
  - `src/styles/components/signals.css`
- **S4 (Playwright):** `e2e/src/support/signals.ts`, `e2e/src/support/screens.ts`, `e2e/src/signals.spec.ts` (also r1).
- **S5 and P4 (docs):** `DESIGN.md` (also r1–r3 and P4), `README.md`, `CLAUDE.md` (also r1–r3).

**Not changed:**
- `signals-api.service.ts`, `signals.model.ts`, `new-signals.ts`, `signals-badge.service.ts`, the shell and rail, `signal-detail.ts`, Trade;
- `tokens.css`, `theme.css`, `icons.ts`, `section.css`, `button.css`;
- `e2e/src/signals-live.spec.ts`;
- tidewatch-service, tidewatch-migrations, tidewatch-bot, `tidewatch-apis`, `documents/`.

## Test plan

### Commands (run in `tidewatch-platform/tidewatch-web`; no CI)

- `pnpm nx test tidewatch-web`, and `TZ=America/New_York pnpm nx test tidewatch-web --skip-nx-cache`: 3,138 tests at `cef0be9`.
- `pnpm nx lint tidewatch-web`, `pnpm nx build tidewatch-web`, `pnpm nx run e2e:lint`.
- The plan checks (`.forge/features/signals-day-control/planning/tidewatch-web/checks/plan-checks.mjs`):
  - `lacks 'Date[.]now[(]|new Date[(][)]'` over `feat-signals/` and `bangkok-time.ts` (no browser clock);
  - `no-new` for colours and motion in `signals.css`;
  - `titles` (no existing test title lost);
  - `tsc-e2e --all`;
  - `listed` (the Playwright titles exist).
- **Playwright on a preview only.** The `authed` project needs a real sign-in, so in the worktree the specs are only listed, linted and type-checked. On the preview: `authed-setup`, then `public` + `authed` with `--no-deps`, then `sign-out`. Credentials are read from the owner's file in-process and never printed.

### Unit specs (Vitest)

- **`bangkok-time.spec.ts`, `signal-filters.spec.ts`, `signal-view.spec.ts`:**
  - the 17:00Z boundary on both sides;
  - month and year ends (31 Oct → 1 Nov, 31 Dec → 1 Jan, 29 Feb);
  - "Sat 10 Oct" with no leading zero;
  - labels and phrases for D0 … D0−6 and an older day;
  - the PD-B extra option and the pre-D0 forms;
  - a malformed, repeated or impossible (`2026-02-30`) `day` read as absent;
  - `FILTER_PARAMS` still exactly four names;
  - every Today sentence unchanged.
- **`signals.service.spec.ts`** (fake timers, `HttpTestingController`, router testing setup): every §4.3 request; `replaceUrl` merge; the D0 rewrite with no second read; S2; the `?day=`-only stored filters; no filters `PUT`; the rollover with no `GET /signals`; S1; PD-B; seen-through per SDC-W-11; SDC-OD-2; the error latch. Named examples:
  - "relabels Today as Yesterday at the rollover without reading the list again"
  - "shifts the labels of a past day at a rollover without reading the list"
  - "keeps the list when a {reconnect, terminal close} reload answers the next Bangkok day before the summary tick and reads its day again"
  - "keeps the rows when the kept day's re-read fails after a reconnect crossed midnight"
  - "reports a reload that answers the next day after the rollover as succeeded and keeps the list"
  - "holds a pasted day's failed opening while the summary is read again until D0 is known"
  - "reads no list again after a reload whose page names a later day than its own generated_at"
- **Component specs** (`signals-filters.spec.ts`, `signals.spec.ts`, `signals-table.spec.ts`):
  - the select first, before *All assets*, named "Day";
  - the `<select>` node kept across option changes;
  - focus kept on the select during a day change;
  - the open set kept;
  - *Show yesterday* rules and focus to the `h2`;
  - verbatim copy;
  - "relabels the heading, the select and the table as Yesterday at the rollover without a list read";
  - "keeps Try again and its focus while a pasted day's summary is read again in the background".
- **Mutation and without-the-fix checks.** Each fix round showed its new specs failing against the previous source: r1 6, r2 6, r3 5, r4 3. Removing the tick guard fails exactly the 2 tick specs.

### Playwright (`e2e/src/signals.spec.ts`, mocked, fail-closed, `@authed`)

- **New tests (titles verbatim):**
  - "draws the Day select first in the filter row with Today, Yesterday and five dates"
  - "writes the chosen day with replaceUrl and reproduces it on reload"
  - "rewrites the date of today and a malformed day to Today without another list read"
  - "never draws an out-of-window or future day and ends on Today"
  - "sends the shown day on the list, Load more, summary and export routes"
  - "names a past day in the heading, sub line, region and caption and keeps the note quiet"
  - "writes seen-through after the first Today load and Show but never after a past day"
  - "relabels Today as Yesterday at Bangkok midnight without reading the list again"
  - "offers Show yesterday on an empty Today and words the past empty states"
  - "keeps the stored filters across day changes and returns to Today from the rail"
  - "shows the recommendation actions on a past day row"
  - "captures the focus rings of Day, Impact and Show yesterday at 1440" (dark and light, added in fix r1)
- **Existing tests extended** (titles kept): "links Export with the filters and the day" (a past day, then back to Today); "reaches every control with the keyboard" (Day between *Add source* and *All assets*).
- **State matrix.** `SIGNALS_STATES` gained `yesterday`, `dated-day` ("Sun 11 Oct", page clock on Tue 13 Oct), `past-empty` ("No signals on Sat 10 Oct.") and `past-filter-empty`. `empty` now shows *Show yesterday*. Each state is captured at 390, 600, 1080, 1100 and 1440 in both themes, with overflow JSON, and contrast and axe at 1440.
- **Mock (`e2e/src/support/signals.ts`, SDC-W-9).**
  - The opt-in second day is `SUNDAY_FIXTURES`: `NVDA_KEYNOTE` with a recommendation, `DOGE_HALT` and `GOLD_WEEKEND` under 0.30. Supporting exports: `TWO_DAYS` and `SUNDAY_SUMMARY`.
  - `generated_at` is read from the page's faked clock with `page.evaluate(() => Date.now())` as each answer is built, because route handlers run in Node. An explicit override wins. An absent `day` answers that instant's Bangkok day.
  - Per-route `ALLOWED` checks are unchanged.
  - Constants `SIGNALS_NOW` (`2026-10-12T04:58:00Z`), `SIGNALS_YESTERDAY`, `SIGNALS_TUESDAY_NOW` and `BEFORE_MIDNIGHT` (`2026-10-11T16:59:30Z`). The rollover tests install `page.clock` there and advance 65 s.
  - `signals-live.spec.ts` and its 7-day badge count see the same answers as before.

### Acceptance status (PRD §9; passed, failed and unverified stated separately)

| IDs | Status | Evidence / note |
|---|---|---|
| FR-SDC-WEB-001, 002, 003, 004, 005, 009, 010, 011 | Verified | Vitest plus P1, with request-log, URL, `history.length` and DOM attachments (`evidence/tidewatch-web/P1/attachments/`). 003, 008 and 010 were also seen on real data in P2. |
| FR-SDC-WEB-006 | Verified | P1 `page.clock` across 17:00Z: request log, DOM, `scrollY`, history. **SDC-OD-2's reconnect re-read and SDC-BD-1's focused-button path are Vitest only.** |
| FR-SDC-WEB-007 | Verified | Vitest (the PRD names no browser check). |
| FR-SDC-WEB-008 | Verified | Vitest, P1, and P2's real "No signals yesterday.". |
| FR-SDC-WEB-012 | Verified | P3 APPROVED. PRD A2 ("Wed 30 Sep" on one line) was judged by proxy: "Sun 11 Oct"/"Sat 10 Oct" at about 105/358px at 390. Advisory A10 is open. |
| FR-SDC-WEB-013 | Verified | S5 doc checks, then P4 `impeccable --check` (no drift, 106/106) and the Verification evidence entry. |
| FR-SDC-WEB-014 | Verified | 3,138 unit tests in both zones; P1 full suite with 0 failures. |
| FR-SDC-E2E-001 | **Partial** | See "Preview" below. The literal Yesterday-with-rows case is unverified. |

**Outcomes.** O1–O4 were implemented and verified on the preview through the IDs above. Sign-off at the outcome level was the owner's, at merge.

### Preview

- **Run.** `sdc-1aa0b0c9`, compose project `forge-0199b29a-sdc-1aa0b0c9`, `http://127.0.0.1:55694/`.
  - Isolated with retain, on the shared volume `forge-preview-0199b29a_tidewatch-pgdata`; 6/6 healthy from 2026-10-14T01:20:23Z.
  - Revisions: web `cef0be9`, service `8b18486`, bot `ece175a`, migrations `52deb26`.
  - The first `up` failed with "Unresolved setup token: project:tidewatch-migrations". The run mapping was then extended to the service, bot and migrations worktrees (migrations as a manual mirror, as in signals-page).
  - The preview was left running at the merge pause.
- **P1.** setup 1/1; main 770 passed / 0 failed / 4 skipped (live-gated: bots-live 1, market-watch-live 2, paper-orders 1); sign-out 3/3. `signals.spec.ts` 68/68, `signals-live.spec.ts` 13/13. 60/60 matrix captures plus 6 focus captures.
- **P2 (FR-SDC-E2E-001), about 08:35 Bangkok on 14 Oct.**
  - SQL counts by Bangkok day: 14 Oct 10 (2 at ≥ 0.30), 13 Oct 0, 12 Oct 6 (1 at ≥ 0.30). At 08:21 only 12 Oct had signals; ingest produced the 14 Oct rows during P1.
  - On **Mon 12 Oct**, at both `min_impact` 0.30 and 0.00, everything matched SQL: API ids and order (1/1, 6/6), rendered rows and times, the summary `today` (6 = 6), and `signals-2026-10-12.csv` data rows (1 = 1, 6 = 6).
  - **Yesterday (13 Oct)** rendered correctly as empty ("No signals yesterday.", `day=2026-10-13` on the list and the export), but it had no rows to compare.
  - **Today** sent no `day` on the list.
- **P3.** `review/tidewatch-web/P3/design-rendered.md`.

### Manual reproduction

1. With signals on earlier Bangkok days, open `/signals`. The *Day* select is the first control and lists *Today*, *Yesterday* and five dates. Choose *Yesterday*:
   - the URL gains `?day=` and history length is unchanged;
   - the heading reads *Yesterday*, and the sub line "{n} yesterday · …";
   - *Export* links `…/signals/export.csv?…&day={that day}`;
   - no `PUT /me/settings/signals.filters` is sent.
2. Compare the rows and the sub line's count with a SQL count of `signals` whose `created_at`, shifted to UTC+07:00, falls on that day. Use the default filters and `min_impact=0.00`. Download the export and count its data rows. This is FR-SDC-E2E-001; repeat it on a day whose Yesterday has signals.
3. Paste `?day=` for a date 8 days back, or one in the future. Nothing of that day is drawn, the URL drops `day`, and Today loads.
4. Keep the page open on Today across 17:00Z. Within one summary interval (60 s) the heading, select, region and caption read *Yesterday*, the URL gains `?day=`, and the network log shows no `GET /signals`.
5. On an empty Today, *Show yesterday* follows the empty sentence. Pressing it moves focus to the heading and selects the day before.

## Open questions

**Unverified at merge (the owner knew):**
- FR-SDC-E2E-001 with *Yesterday* holding real signals: the preview's 13 Oct had none.
- These ran only in Vitest or were checked by proxy, never in a real browser: SDC-OD-2's reconnect re-read; SDC-BD-1 (a focused *Show yesterday* removed at a rollover); the held pasted-day error and a filter undo; the literal "Wed 30 Sep" label (PRD A2).
- Screen readers, and the owner's own or production data.

**Not deployed.** The web change is merged only. No database or service step is needed.

**Accepted trade-offs:**
- SDC-OD-1: rows still waiting behind *Show* at a rollover are marked seen by the new Today's first load.
- SDC-OD-2: one extra list read after a reconnect that crosses midnight.

**Follow-ups (state.json `followUps`):**
- The *Export* `href` carries an unchecked pasted out-of-window or future day while it waits for D0 (code r1 nit).
- The sub line can read "Loading…" for up to 60 s when a Today list's day passes the last summary's day before the tick (code r1 nit).
- A pasted `?day=` with an emptied filter group whose summary fails still shows Loading, not the error (fix r1 residual).
- Focus falls to the document when a held pasted-day error ends by the out-of-window fallback to Today (design r3 A7; rare).
- Pre-existing, not from this feature: `firstLoadSeen.set(true)` runs inside the list-loaded effect (angular r3).
- An optional spec for the `sameAttempt` second guard (code r5).
- A tighter SDC-W-8 selector (design A1).
- **A10:** the *Show yesterday* focus ring touches the preceding period by 1px. Optional fix: a placement-only `margin-left` of 2–4px on `.signals-section .status-line .text-btn`.
- Already closed: the design-review A2 item (11px *Show yesterday* beside the 12px sentence) was closed at P3 with no change, and the A8 and A6 wording advisories were folded into `DESIGN.md` at P4.

## Cross-cutting links

- [[signals-page]]: the slice-4 screen this extends. Its "today only" statement, the ORCH-19 follow-up, the sub line, states, focus targets, seen-through and export now follow the shown day.
- [[signals-read-api]]: the existing `day` parameter on the list, summary and export, the Bangkok day boundary, the day-bound cursor, and `generated_at` at read time (the rollover signal).
- [[user-settings]]: `signals.filters` never carries the day; the new `signals.seen_through` rules (SDC-OD-1).
- [[design-system-decisions]]: the *Day* `.chip-select` reused unchanged, first in the filter row, and the one placement-only rule for *Show yesterday*.
- [[realtime-websocket]]: the all-signals feed held whatever the day, and the reconnect that reloads the shown day (SDC-OD-2).
- [[signals-ingest]]: history begins at slice 3a (2026-10-11); `signals` has no retention.
- [[forge-preview-gateway]]: the isolated preview on the shared retained volume, and the run mapping extension after the unresolved-token failure.
