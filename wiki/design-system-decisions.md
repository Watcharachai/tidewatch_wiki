# Design system decisions

**Summary**: How the Aurora design system was implemented in `tidewatch-web`: variable-driven theming on Tailwind v4, recorded exceptions to the kit (D6), the account menu (D7), mockup breakpoints (D13), and the owner's light-theme and error-colour rulings (OWNER-4, OWNER-5, OWNER-6). The project's design reference is `tidewatch-web/DESIGN.md` (FR-WEB-019, merged 2026-10-06). Slice 1 added the Market watch building blocks (`TideStrip`, `ZoneLabel`, `.tag`, `Dialog`, `Toast`, the table pattern, `--backdrop`); documenting them in `DESIGN.md` is FR-MD-WEB-011, still pending. Slice 2 (2026-10-08) added the Trade screen, the portfolio hero, the equity chart, KPI cards, new role tokens and component classes; documenting them is FR-SIM-WEB-010, in progress. Slice 2b (2026-10-09) added the Bots screen with no new colour or token, plus reusable selected-row and selectable-row-button patterns; documenting them (FR-ZB-WEB-007) is closed, shipped as tidewatch-web PR #8 (merge `1689b0c`). The bot-activity feature (2026-10-10) added the Watch and Checks sections and the reusable **expandable row**, again with no new token, colour, type step or icon, and refreshed `DESIGN.md` inside its own web PR (FR-BA-WEB-011). Signals-ingest (slice 3a, 2026-10-11) filled the existing Market watch *Signals* cell with today's count. It added no component, route, stylesheet, token or icon, and no mockup (PD7). The cell stays quiet: no hue, badge, icon, motion or live region. The signals page (slice 4, 2026-10-12) replaced the `/signals` placeholder with the Signals screen. It added the pill filter chip, trust and impact bars, direction tones, a sticky detail wrap and `.nav-count`, the one rail badge. Again it added no token, colour, type step or icon. The expandable row moved into `table.css` as its second consumer, and `DESIGN.md` was refreshed inside the same web PR (FR-SP-WEB-011). The signals day control (tidewatch-web#13, merged 2026-10-14, not deployed) put a *Day* select first in the Signals filter row. It reuses `.chip-select` unchanged and adds no token, colour, type step, icon or motion, only one placement rule. It made no mockup (DC6), and `DESIGN.md` was refreshed inside the same PR (FR-SDC-WEB-013). Charting (slice 5, tidewatch-web #14, merged 2026-10-16 as `918d7b6`, not deployed) replaced the Chart placeholder with the Chart screen. It brought the first chart library, `lightweight-charts` 5.2.1, for the Chart only; Overview keeps its own "no chart library" decision. Canvas colours are read from the computed tokens, and zone hues appear only on candles and strip cells. It added a 96-slot mode of the shared tide strip and a recorded `role="img"` wrapper exception (S11). Again no token, colour, type step, icon, transition or animation was added. `DESIGN.md` was refreshed inside the same PR (PV4), and the rendered review approved with W5 and W6 left open. Bots (slice 6, tidewatch-web #15, merged 2026-10-21 as `acbd75d`, not deployed) added the Bots list sparkline and tags, *Create bot* and *Clone* dialogs, Loops with *Run now*, Candidates, the typed version editor with ORCH-7's allocation bar, Overview's *Your strategies* cards and the Trade recommendation card. Again no token, colour, type step or icon was added, and nothing animates; the pieces are feature-local. PV3 passed (keyboard, axe, contrast, overflow, clipping), but **the rendered design review (PV2) is CHANGES REQUESTED** (B1, the Clone dialog's `class="fixed"` colliding with Tailwind's `fixed` utility; S1–S3), and a follow-up web fix is in progress. Statistics (slice 7, tidewatch-web #20, merged 2026-10-27 as `74918fd` and deployed to production) replaced the `/stats` placeholder with the Stats screen: a KPI strip, an equity chart with a drawdown area, a calibration plot, an attribution table, *Why trades lost* with a labelling list, and a compare panel. Every rule sits in `stats.css` under `.stats-screen`. Again no token, colour, type step, icon, transition, animation or dependency was added, and Stats uses no chart library. One recorded colour exception: drawdown is drawn in `--down` at low opacity, never a zone colour (D13). Panel titles are `h2`s with the `h3` look (OD-5), Stats and the Bots editor share `SOURCE_NAMES` (OD-7), and `.chip` graduated to its own `chip.css`. The rendered review (PV2) approved at its re-check after PF2, with W8 fixed in PF3; the equity tooltip and focus-ring visuals were not captured. Accounts and roles (tidewatch-web #23, merged 2026-10-29 as `4725cb9` and deployed to production) added the **operator console** at `/admin`. It reuses the product frame under a `console` host class, and every rule sits in `console.css` under `.console`. The four icons `people`, `operators`, `audit` and `spend` are the one icon addition PRD §7.2 allows. No token, colour, type step or motion was added, and the console has no literal colour, `--up`, `--down` or `--z-*`. On the product side, the account menu now reads *Signed in as {display_name}*, and the Bots editor greys an unentitled tier with *Not in your plan*. The visual pass approved 0/3/13; VW1 and VW2 are fixed, and VW3 is open for the owner. The dialog-reopen-race fix (tidewatch-web #25, merged 2026-10-30 as `0fa0019`, deployment not verified) made the shared `Dialog` emit exactly one `closed` per opening, so a fast close-then-reopen no longer leaves an empty modal backdrop; it changed no style, template or public API. The learning loop (slice 8, tidewatch-web #21, merged 2026-10-30 as `de00a5f` and deployed to production) added the *Learning* section on the bot detail, the editor's locked learned block, the clone dialog's probation lock and the Stats proposal flow, with no mockup (D14) and existing patterns only. The new rules are `.learning-tables` and `.learning-actions` in `bots.css`, one `.status-line` per job, and the OD-PV2-1 wrap in `stats.css`. OD-PV2-2 amends PRD §7.4: the *Failure model* table has no 560px minimum. The rendered review (PV2) approved at round 2. Signals context (tidewatch-web #22, merged 2026-10-30 as `9dc59cf`; deploy triggered, not verified) added two discovery switch rows to the Bots version editor's Schedule group and a ≤ 600 px scroll margin under the sticky strip, with no new component, token, colour, icon or motion. A coverage signal renders on Signals with no product change.

**Sources**: `raw/2026-10-05-foundation-auth.md`; `raw/2026-10-07-market-data.md`; `raw/2026-10-08-simulation-engine.md`; `raw/2026-10-09-zone-transition-bot.md`; `raw/2026-10-10-bot-activity.md`; `raw/2026-10-11-signals-ingest.md`; `raw/2026-10-12-signals-page.md`; `raw/2026-10-14-signals-day-control.md`; `raw/2026-10-16-charting.md`; `raw/2026-10-21-bots.md`; `raw/2026-10-27-statistics.md`; orchestrator correction of 2026-10-21 (the PV2 verdict); `raw/2026-10-29-accounts-roles.md` (the console, the four icons and the account-menu change); `raw/2026-10-31-fix-dialog-reopen-race.md` (the `Dialog` close contract); `raw/2026-10-30-learning-loop.md` (the Learning section, the learned block, the Stats proposal flow, OD-PV2-1, OD-PV2-2 and the LL-W decisions); `raw/2026-10-30-signals-context.md` (the discovery rows and the coverage-signal rendering); `tidewatch-platform/tidewatch-web/DESIGN.md` at tidewatch-web `0b83213`; tidewatch-web PR 2 (https://github.com/tidewatch-labs/tidewatch-web/pull/2); tidewatch-web PR 8 (https://github.com/tidewatch-labs/tidewatch-web/pull/8, merge `1689b0c`)

**Last updated**: 2026-10-31

---

## Authority

The design authority is `documents/03-design-system.md` plus the Aurora block of `documents/mockups/tidewatch-redesigned.html` (token lines 216 to 233, layout lines 234 to 257). Where they disagree, the approved mockup and the owner rulings below won, and `03` was not edited (D17). The drift is listed under "Drift from 03" below (source: raw/2026-10-05-foundation-auth.md §Concept, Sources; §Open questions).

Since 2026-10-06 the project-level reference is `tidewatch-platform/tidewatch-web/DESIGN.md`. It records the same precedence (owner decisions, then the PRD, then the mockup over `03`), links both sources, and tabulates every place `03` differs; see "DESIGN.md (FR-WEB-019)" below (source: tidewatch-web `DESIGN.md` §Overview, Design authority).

## Styling (D6)

- Tailwind v4 through `setup-shared-styles` in single-app mode (`src/styles/`).
- Tokens are CSS custom properties defined once in `src/styles/base/tokens.css`: `:root` (dark, the default) and `:root[data-theme=light]`. `src/styles/tailwind/theme.css` maps them with `@theme inline` and removes Tailwind's palette (`--color-*: initial`).
- Token groups: surfaces, lines, text, brand, chrome (`--focus` `#b9e9de` dark / `#235f55` light, `--aurora-opacity` `1` / `.48`), zone and P&L tokens (reserved for later slices; the zone tokens and `--up`/`--down` are in use since slice 1, see "Slice 1: Market watch building blocks"), and radii `--r` 9 px and `--r-lg` 16 px.
- Recorded exceptions to the kit: no `dark:` variants (theming is variable-driven); no Angular Material (`@angular/aria` provides the menu); mockup inline SVG icons instead of lucide.
- DM Sans and Manrope are self-hosted through `@fontsource-variable` (OFL).
- The only literal colours outside the token file are the brand gradient tile's.
- The production build sets `inlineCritical: false` and `fonts: false`; otherwise the light-theme block went missing from the inlined CSS.
- Theme handling: `ThemeService` sets `data-theme` on `<html>`, dark by default, persisted in `localStorage['tw-theme']` with try/catch, and an inline script in `index.html` applies the stored theme before boot.

(source: raw/2026-10-05-foundation-auth.md §Concept, D6; §Components, Styles and ThemeService)

## Account menu (D7)

The account menu sits at the right of the top bar at every width: *Signed in as {username}*, then *Change password*, *Sign out* and *Sign out everywhere*. **Since accounts and roles (2026-10-29)** it reads *Signed in as {display_name}*, with the username under it in `--text-3` when the two differ. It reads `display_name` leniently and falls back to the username (`shell/account-menu.ts`) (source: raw/2026-10-29-accounts-roles.md §Components, Product-side changes). The mockup's help button and "Design preview" label are omitted. It is an `@angular/aria` menu with full keyboard behaviour (Enter, Space or ArrowDown opens and focuses the first item; arrows move; Escape closes and returns focus). A sign-out failure keeps the session, says so under the button and clears after 10 s (source: raw/2026-10-05-foundation-auth.md §Concept, D7; §Components, AccountMenu). The server-side effects of sign-out are in [[auth-model]].

## Breakpoints (D13)

Breakpoints follow the mockup, not `03`:

- Above 1250 px: 220 px rail.
- 1250 px and below: 190 px rail.
- 1080 px and below: 74 px icon rail.
- 820 px and below: single-column grids.
- 600 px and below: a sticky top strip with a 6-column nav and the theme switch at top-right.

(source: raw/2026-10-05-foundation-auth.md §Concept, Related decisions; §Components, Breakpoints)

## Owner ruling OWNER-4: light-theme AA fix

The mockup values measured below WCAG AA: the bar tint gave 4.3:1 for `--text-2` on the environment pill, and the leading crumb in `--text-3` gave 3.7:1. In the light theme only, `.global-bar` is transparent and the leading crumb uses `--text-2`. Dark keeps the mockup exactly (source: raw/2026-10-05-foundation-auth.md §Concept, Owner design decisions).

## Owner ruling OWNER-5: hue-less errors

Error text uses `--text`, led by the error glyph (`<app-icon name="close" />`, `aria-hidden`), in `p.error-message`. An invalid field gets a `--text-2` border. `--down` and the zone hues stay reserved for zones and P&L (`03` sections 2.3 and 10) (source: raw/2026-10-05-foundation-auth.md §Concept, Owner design decisions).

## Owner ruling OWNER-6: light breadcrumb hierarchy

In light, the current crumb uses `--text`, one step above the `--text-2` leading crumb. Dark is unchanged (`--text-3` leading, `--text-2` current) (source: raw/2026-10-05-foundation-auth.md §Concept, Owner design decisions).

## Shipped UI building blocks

- `Shell`, `Rail`, `TopBar`, `AccountMenu`; the rail holds the wordmark, workspace card, main nav (Overview, Signals, Chart, Bots, Trade, Stats), conviction note, mode line and theme switch (`aria-pressed`). The top bar shows a breadcrumb, the *Paper environment* pill and the 33 px *Account* button.
- Shared UI: `Icon` and `ICONS` (inline SVG, 24 viewBox, 1.6 stroke, `currentColor`), `Wordmark`, `PageHeader` (`h1` Manrope 700 at 29 px).
- `EmptyState` and `ScreenPlaceholder`: a panel with the route icon, an `h2` and one sentence, with no call to action, using the PRD section 7.3 copy per route.
- Sign-in is a glass panel (max width 380 px) with no links and no theme switch. The change-password screen has forced and voluntary modes.

(source: raw/2026-10-05-foundation-auth.md §Components, tidewatch-web)

## Verification

FR-WEB-001 to 016 passed. Screenshots in both themes at 390, 1080 and 1440 px were judged against the design review; axe reported 0 violations with a minimum text contrast of 4.65:1 (FR-WEB-015). Accepted UI limits: at 390 px the sign-out failure alert covers the `h1` for up to 10 s, the pre-hydration sign-in form looks dimmed, and axe reports needs-review items (not violations) on the open account menu (source: raw/2026-10-05-foundation-auth.md §Test plan; §Open questions, Known limits).

## Drift from 03

`documents/03-design-system.md` is out of date (not edited, per D17): breakpoints 1100/760 versus D13; body text 14px/1.45 versus the approved mockup's 13px/1.5 (PW-4); light `--text-3` measures 4.42:1 on `--bg`, below AA; and OWNER-4 and OWNER-6 are not reflected. OWNER-5 is consistent with sections 2.3 and 10. Updating 03 section 4 is deferred by the owner.

## DESIGN.md (FR-WEB-019)

FR-WEB-019 is closed. `tidewatch-platform/tidewatch-web/DESIGN.md` was written with `forge-setup-impeccable` on branch `codex/forge-fauth-69425a62-design` (base `f0d0a7f`), committed as `0b83213` and merged into `main` on 2026-10-06 as tidewatch-web PR 2, merge commit `4f8c4a2` (source: https://github.com/tidewatch-labs/tidewatch-web/pull/2; tidewatch-web git history). The raw source predates the merge and records the ID as open (source: raw/2026-10-05-foundation-auth.md §Open questions).

What the document covers (source: tidewatch-web `DESIGN.md` at `0b83213`):

- Status *established*: it describes the Slice 0 system as implemented and merged at `f0d0a7f`. It is not a redesign, and the token values it quotes are snapshots of the linked source files; values are changed in the sources, not in the tables.
- Sections: Overview (with a "Where things live" table and the fixed `styles.css` import order), Colors, Typography, Layout, Elevation & depth, Shapes, Motion, Focus/keyboard/accessibility, Components, Do's and don'ts, Decisions and exceptions, Known inconsistencies and follow-ups, Verification evidence, Source snapshot.
- Decisions recorded: D6, D7, D13, PW-2, PW-3, PW-4, PW-7, PW-12/13, PW-15, PW-18, OWNER-4, OWNER-5, OWNER-6, the contrast rule (lowest measured 4.65:1) and the build settings (`inlineCritical: false`, `fonts: false`).
- A "Reconciliation with 03" table listing each place `03` differs from the implementation and its resolution (PW-4, D13, D7, the mockup or the PRD). `documents/` is still not edited (D17), and updating `03 §4` remains deferred; see "Drift from 03" above.
- A source snapshot of 34 workspace-relative files with SHA-256 fingerprints (tokens, Tailwind theme, base and component CSS, shell and page components, `03`, the mockup and the PRD), inspected 2026-10-06 at `f0d0a7f`.

How Forge uses it: `forge-spec` and `forge-build` read `<project>/DESIGN.md`. Refresh it with `forge-setup-impeccable --project tidewatch-web`; add `--check` to report drift without writing. On 2026-10-06 the bundled drift check (`forge-design/scripts/source-snapshot.mjs check` against the embedded snapshot) reported all 34 sources unchanged (source: that check run on 2026-10-06, not a raw document).

**Now stale for slice 1 (FR-MD-WEB-011, pending after merge).** The slice-1 web PR did not change `DESIGN.md`, so it does not describe the new pieces below, and its source snapshot needs a refresh (`tokens.css`, `button.css` and `styles.css` changed). A separate docs PR is in progress through `forge-setup-impeccable` in the `web-design` worktree (branch `codex/forge-mdata-d9d3e428-design`, base `5611d79`). It must document `TideStrip`, `ZoneLabel`, `.tag`, `Dialog`, `Toast`, the table pattern, the neutral tile, `--backdrop` and the new icons; refresh the source snapshot; and record DEV-WEB-CAPTION with the owner's acknowledgement (OC-2) and the design reviewer's A9 items (source: raw/2026-10-07-market-data.md §Components, tidewatch-web; §Open questions, Pending by stage).

## Slice 1: Market watch building blocks

The visual target was the Market watch section of `documents/mockups/tidewatch-redesigned.html`, with the departures listed in PRD §7.2 (source: raw/2026-10-07-market-data.md §Concept, Sources).

**New shared components.**
- **`TideStrip`** (`shared/ui-tide-strip`): an inline SVG (`viewBox 0 0 1000 18`) with one `rect` per cell filled with `var(--z-*)`; a `null` cell gets a `--line-2` stroke. `role="img"` with an accessible name from `strip-label.ts`. Fewer than 48 cells are right-aligned.
- **`ZoneLabel` and `ZONES`** (`shared/ui-zone-label`). `zone.css` alone maps a zone to its token.
- **`Dialog`** (`shared/ui-dialog`, `app-dialog`): a native `<dialog>` opened with `showModal()`. The backdrop is the new **`--backdrop`** token, dark `rgba(4,10,19,.68)` and light `rgba(31,48,73,.14)`. Escape closes it through a capture-phase listener because the aria combobox cancels the key first (MW-16). Focus returns to the trigger, the body renders only while open, and a toast slot sits outside the glass panel (MW-3). Since 2026-10-30 it emits exactly one `closed` per opening, even after a fast close-then-reopen; see "The `Dialog` close contract" below.
- **`Toast`** (`shared/ui-toast`): a polite live region that clears after 4 s.
- Icons `plus`, `edit` and `arrow` were added to `ICONS`.
- New styles `tag.css`, `zone.css`, `dialog.css`, `toast.css`, `table.css` and `market-watch.css`; `button.css`, `tokens.css` and `styles.css` changed.

(source: raw/2026-10-07-market-data.md §Components, tidewatch-web Shared components and styles)

**Patterns.**
- **Table.** `table.tide` with a visually hidden caption and `min-width: 650px` inside a scroll region. Rows are 61 px and not clickable. The instrument cell is a neutral 29 px tile with a glyph (₿, Ξ, Au, G or the first letter), then `name · venue_label · status tag`.
- **Status tags.** A neutral `.tag` for every status (*Live*, *Delayed 15 min*, *EOD*, *Synthetic*, *Closed · opens EEE HH:mm*, *Stale*); Stale outranks the others (`util/status-tag.ts`).
- **Hue use.** 24h change uses `--up`/`--down`, U+2212 for minus, and `--text-2` for 0.0 % and "—". The error state ("Market watch couldn't load." plus *Try again*) is hue-less, consistent with OWNER-5.
- **Quiet table (MW-23).** The table is not a live region, and prices change in place with no highlight. A polite *Reconnecting live prices…* caption sits in the card header.
- **States.** "Loading market watch…" with no spinner; an empty state with a primary *Add instrument*; "No instruments in this view." for an empty filter; a row with no price shows "—" and the history-loading strip.

(source: raw/2026-10-07-market-data.md §Components, tidewatch-web Market watch card)

**Recorded deviations and open owner calls.**
- **DEV-WEB-CAPTION (ORCH-26, OC-2).** *History loading* is drawn in the empty strip slots only when the whole caption fits; otherwise a `title` carries it. The accessible name always ends ", history loading". The owner's acknowledgement is pending.
- **OC-1 (ORCH-22/25).** The Add instrument dialog's all-listed line (`Everything matching "<query>" is already on your list.`) uses straight quotes instead of the approved curly ones; pending the owner.

(source: raw/2026-10-07-market-data.md §Concept, ORCH-22/25/26 and Accepted PRD deviations; §Open questions)

**Verification.** FR-MD-WEB-001 passed on the mocked render, judged by the design reviewer at 1440 px in both themes; the preview captures were not re-judged against the mockup. FR-MD-WEB-009 passed on the mocked render with axe 0, overflow 56/56 and a minimum contrast of 4.66:1; the preview axe run and other-width contrast are unverified. The preview rendered only the Live, EOD and Stale tags. Web review round 2 approved 5/5 (angular, code, design, security, tailwind-curator) (source: raw/2026-10-07-market-data.md §Test plan, Per-ID results and Stages).

**Known web gaps.** Long names lose the venue first (design N1); phone rows hold three lines in 61 px (design N2); *Edit list* reopened during an in-flight save builds its draft from the pre-save rows; `prettier --check` fails on `README.md` and `CLAUDE.md`, as it already did at the base (GAP-WEB-PRETTIER) (source: raw/2026-10-07-market-data.md §Open questions, Known gaps).

## Slice 2: Trade and portfolio building blocks

tidewatch-web PR #5 (merge `cfed50e`, 2026-10-08) follows the existing `DESIGN.md` rules: no Material, no chart library, no `dark:`, tokens only in `tokens.css`, and native `<dialog>` and controls (source: raw/2026-10-08-simulation-engine.md §Components).

**Tokens and classes.**
- New role tokens in `src/styles/tailwind/theme.css`: `--text-metric` (22px), `--tracking-hero` (−0.055em), and the hero sizes `--text-hero-compact` (33px), `--text-hero-tablet` (39px) and `--text-hero-phone` (35px). **No new colour.**
- New reusable classes in `src/styles/components/`: `section.css` (`.section-head`), `metric-card.css`, `range-switch.css`, `portfolio.css` and `trade.css`.
- `.second` and `.status-line`, plus tweaks, in `table.css`.
- New icon: `trend` in `shared/ui-icon/icons.ts`, copied from the approved mockup.

**Patterns.**
- **Equity chart.** `app-equity-chart` is an inline SVG with `role="img"` and an accessible name.
  - The equity path is `--brand`. The benchmark is `--violet` at one named opacity token.
  - The tooltip is `aria-hidden`, with an sr-only status driven by the arrow keys.
  - A single-point series draws a flat line.
- **Range switch.** `1W/1M/3M` uses `aria-pressed` in a named group. Idle text in the light theme uses `--text-2` (4.41:1 → AA, ORCH-18).
- **Money.** Whole baht truncates toward zero (ORCH-19; the PRD won over plan SE-9). "—" placeholders carry sr-only words.
- **Trade layout.** A `300px minmax(0,1fr)` grid. It becomes one column at ≤ 1080 and stacks at ≤ 600.
- **Order ticket.**
  - The estimate is fingerprint-gated, in a polite live region with `aria-busy` while pending.
  - The busy *Placing…* button reaches ≥ 4.5:1 (5.51 light, 6.70 dark).
  - Manual-fill fields stack in containers ≤ 400px.
- **Open orders** has a sticky Cancel column.
- **Positions table** is not a live region.
- **Accessibility.** Heading order and landmark names are unique (ORCH-30).

(source: raw/2026-10-08-simulation-engine.md §Components; §Concept, Web deviations ORCH-18, ORCH-19, ORCH-23, ORCH-30)

**Verification.** Rendered evidence comes from a local build against a mocked API: axe 0 across 16 runs, minimum contrast 4.67 over 110 measurements, and no horizontal scroll at 390, 600, 1080, 1100 and 1440. The design reviewer approved in round 4. Fresh-account and populated states were mocked (ORCH-29). The design reviewer's rendered verdict gated the merge rather than the PR (ORCH-25) (source: raw/2026-10-08-simulation-engine.md §Test plan, Acceptance status; §Concept, ORCH-25).

**`DESIGN.md` is stale for slice 2 (FR-SIM-WEB-010, in progress).** `DESIGN.md` was unchanged at merge. Its refresh runs through `forge-setup-impeccable` on branch `codex/forge-sim-606762cb-design`, from `cfed50e` (source: raw/2026-10-08-simulation-engine.md §Files touched, Not changed).

**Open web follow-ups.**
- FU-5:
  - the range switch disappears when a period switch keeps failing;
  - trailing zeros count as decimals in the client check;
  - *Placed* is ambiguous about the weekday for orders older than 6 days;
  - a layout jump while Open orders loads.
- FU-6: radius literals (12/14/10/7/5/4px) sit beside the `--r` / `--r-lg` tokens.
- FU-13:
  - the MTS option text is truncated in the 300px select;
  - at 1440, the Status column sits partly under the pinned Cancel column.

(source: raw/2026-10-08-simulation-engine.md §Open questions)

## Slice 2b: Bots screen

tidewatch-web PR #7 (merge `db96bc9`, 2026-10-09) replaced the slice-0 `/bots` placeholder with a Bots screen in `feat-bots/`. It follows the `DESIGN.md` rules: no Material, CDK or chart library, no `dark:`, tokens only in `tokens.css`, **no new colour or token**, and native controls. The visual target is the spec's `mockup.html` (ZB11). Where it differs from the approved mockup's Bots screen, it wins. Where it differs from `DESIGN.md`, `DESIGN.md` wins (source: raw/2026-10-09-zone-transition-bot.md §Components; §Concept, ZB11).

**Screen structure.**
- Header "Bots", with the sub line "{n} bots · paper mode".
- A list section with the note "Paper money · a version never changes". Its `table.tide.bots` sits in a named scroll region. Columns: Bot (a native `<button aria-pressed>` name, the mono version label, a `.second` strategy line), Mode, Status (neutral `.tag`; "—" for the manual bot), 30 days (tone class), Max drawdown, Decisions, Equity (whole baht). Rows are quiet (MW-23).
- A detail for the selected bot (the first auto bot by default):
  - a head with the name, a mono version tag, a status tag and *Pause* / *Resume* (`.btn`, `aria-busy`, "Pausing…" / "Resuming…"); the manual bot shows a *Manual* tag and no button;
  - a strategy sentence derived from the version config, which falls back to "{strategy_label}. Rules as set in {label}." so no raw config value is ever shown;
  - a `.metric-strip` of four cards: *Equity*, *Return since start*, *Max drawdown*, *Last check*;
  - the reused positions table and the shared decision record (see [[decision-record]]).
- One polite status region ("Loading bots…" / "Bots couldn't load." plus *Try again*, which focuses the list heading). A keyboard selection focuses the detail heading after render; a pointer selection does not move focus.

**New reusable patterns.**
- **Selected row** `.tide tr.selected` in `table.css`: a `--surface` fill and an inset 3px `--brand` bar.
- **Selectable-row button** `.tide .name button[aria-pressed]`: reads as text, `--brand` on hover, `cursor: pointer`. The list's output is named `choose`, because `@angular-eslint/no-output-native` refuses `select`.
- **`.metric-strip`** moved verbatim from `portfolio.css` to `metric-card.css`. Overview renders identically: 0-pixel diffs at 1440, 820 and 600 in both themes (A7).
- **`bots.css`** (imported after `trade.css`, before `zone.css`): the mono version tag and strategy sentence; a head-button `min-width` of 88px so "Resuming…" never clips; the busy style `.bot-detail .btn[aria-busy="true"]`, which keeps AA instead of fading (ORCH-30); metric-strip margins, 28px section spacing and a head wrap at ≤ 600; and `--text-2` `.muted` / `.when` cells and centred load errors scoped to `.bots-screen`. That last item was design-review blocker **B1**: Trade's rules were scoped to `.trade` and did not reach Bots.
- **Tick-size digits.** Prices keep their tick-size digits (189.10, not 189.1) because the screen reads `GET /trade` once per open for `tradable_instruments` (ORCH-5). The mockup's "0.746 oz" never renders in production (pre-existing positions-table behaviour).

(source: raw/2026-10-09-zone-transition-bot.md §Components; §Concept, ORCH-3 → ORCH-5)

**Verification.** The mocked spec `e2e/src/bots.spec.ts` passed 142/142, locally and against the preview build: 80 captures (10 states × 2 themes × 390/600/1080/1440), no horizontal scroll 80/80, 600 contrast measurements with a minimum of 4.79:1, axe 0 violations in 20/20 runs, and 0 clipping. Design review r1 requested changes (blocking B1). r2 approved 5/5 on rendered evidence, with Overview and Trade at 0-pixel diffs (source: raw/2026-10-09-zone-transition-bot.md §Test plan, Acceptance status; §Concept, Stage).

**`DESIGN.md` for slice 2b (FR-ZB-WEB-007, closed).** `DESIGN.md` and `tokens.css` were unchanged at the slice-2b merge, and the raw source records the refresh as in progress in a separate web docs PR on branch `codex/forge-zbot-d1343f8c-design`, from `db96bc9` (source: raw/2026-10-09-zone-transition-bot.md §Components, Styles; §Files touched, Not changed; §Test plan, Acceptance status). It shipped as tidewatch-web PR #8: commit `7deaec3` ("docs(zone-transition-bot): DESIGN.md for the Bots screen and the selected-row pattern"), merged into `main` as `1689b0c` on 2026-10-09 (18:03Z) (source: https://github.com/tidewatch-labs/tidewatch-web/pull/8; tidewatch-web git history). `1689b0c` is the base that bot-activity's web PR #9 and its own `DESIGN.md` refresh (FR-BA-WEB-011) built on (source: raw/2026-10-10-bot-activity.md §Components; §Files touched).

**Open web follow-ups.**
- A 2xx non-JSON Pause/Resume body shows "Couldn't change" without reloading.
- Tailwind curator: a duplicate busy rule, and a redundant `display:block` on `.bot-detail app-decision-record`.
- Graduate `positions-table.ts`, `decision-record.ts` and `util/order-view.ts` to `pages/workspace/ui-*`. On that move, unscope the twice-scoped `.muted` / `.when` and centred-error rules. Promote the busy button to `button.css`. Graduate `number-format.ts` and `DISPLAY_TIME_ZONE`.
- Design notes:
  - the list's name cell has no whitespace between `.ver` and `.second`, so its accessible text reads "v1·687cCDC zone changes…" (the mockup does the same);
  - the 2px heading margin also applies to the Positions and Decision record headings inside `.bot-detail`;
  - in full-page captures the sidebar background ends at viewport height (pre-existing shell behaviour).
- The approved mockup's sparkline and probation tag were not built.

(source: raw/2026-10-09-zone-transition-bot.md §Open questions)

## Bot activity: Watch, Checks and the expandable row

tidewatch-web PR #9 (merge `31f9435`, 2026-10-10) added two sections to the bot detail (see [[bot-activity]]). The `DESIGN.md` rules apply: no Material, CDK or chart library; no `dark:`; native controls; nothing animates. **No token, colour, type step or icon was added:** `tokens.css`, `theme.css`, `icons.ts`, `table.css`, `section.css` and `button.css` are byte-identical to base `1689b0c`. All new styles live in `src/styles/components/bots.css` (source: raw/2026-10-10-bot-activity.md §Components).

**Visual target (BA5).** A one-direction mockup on the real tokens, in both themes and every state, with the Checks expansion working, browser-verified at 390/600/1080/1440. Where it differs from `DESIGN.md`, `DESIGN.md` wins, except the feature pieces PRD §7.6 names. Recorded copy rulings: PRD over mockup for *Decided* ("skip at 14:02", dropping "· insufficient cash"); mockup over PRD for the Checks head note, which the PRD does not name (source: raw/2026-10-10-bot-activity.md §Concept, Chosen design BA5; §Concept, Plan resolutions, Web).

**Placement (BAW-7).** Inside `app-bot-detail`: the `.metric-strip`, `app-bot-watch`, Positions, `app-decision-record`, `app-bot-checks`. Spacing is 24px under the strip, 28px after Watch and 28px before Checks. Both new hosts render only for `kind = auto` (source: raw/2026-10-10-bot-activity.md §Components, Placement).

**One table for now and then.** `app-bot-watch-table` is presentational, with inputs `rows`, `mode` (`now` | `then`) and `caption`. In *now* mode it is `table.tide.watch` with a *Next* column; in *then* mode it is `table.tide.nested` inside an expanded check, without *Next*. Rows are tracked by `instrumentId`, so a refresh updates them in place. It has a hidden caption and `th scope="col"`, and rows take no handler, role or `tabindex`. The web `CLAUDE.md` records the same convention (source: raw/2026-10-10-bot-activity.md §Components, `app-bot-watch-table` and DESIGN.md).

**The expandable row (new reusable pattern).**
- Each Checks row has a native `button.text-btn` *Details* / *Hide* with `aria-expanded` and `aria-controls="check-detail-{run_id}"`. `aria-controls` is always set, unlike the account menu, and the button is the same node in every state.
- Expanding sets `tr[data-expanded="true"]` and inserts `tr.check-detail#check-detail-{run_id}` with one `colspan="6"` cell. The cell holds a polite region that is empty in the inserting render and filled one task later (review-1 W5).
- Rows are tracked by `run_id`, so the 10 s merge keeps the same DOM nodes. Open rows survive refreshes; the open set resets on a bot change.
- Styles: `.tide tr[data-expanded="true"] td` and `.tide tr.check-detail > td` (`--surface`, `padding: 0 17px 17px`, `0 10px 14px` at ≤ 600); `.check-note` (10px `--text-3`; 5.46:1 dark, 4.84:1 light); `.tide.nested` (`min-width: 0`, 1px `--line` border, 12px radius, `border-collapse: separate`, 14px cells, hover `--surface-2`).
- The production nested table deliberately differs from the mockup's CSS: the mockup's selector leaked 17px padding into nested cells, and its `border-collapse: collapse` dropped the radius (design advisory A1).
- `DESIGN.md` records it under Bots pieces, with known inconsistency #19: move it to `table.css` when a second screen uses it. Slice 4's Signals detail row was that second screen, and the move is done (see "Slice 4: the Signals screen" below).

(source: raw/2026-10-10-bot-activity.md §Components, `app-bot-checks` and Styles; §Components, DESIGN.md)

**Focus and live regions.**
- Both sections keep their loading, error and empty states in one always-rendered polite wrapper. The section-level *Try again* focuses the section heading first (the Watch heading `h2#watch-title` carries `tabindex="-1"`).
- **ORCH-6 (accepted pending the owner's veto).** The detail-row *Try again* focuses that row's *Hide* button instead of the Checks heading, so a keyboard user stays at the row.
- **Stale line.** An always-present polite `role="status"` region above the Watch table holds the dashed `.status-line.watch-stale`.
- **Hidden-dash rule (ORCH-14 W1).** Two placeholder dashes were announced by screen readers. The Checks *Deferred* zero now renders `<span aria-hidden="true">—</span><span class="sr-only">0</span>`, and the Watch *Next* "—" is `aria-hidden` because its second line carries the words. No visual change.
- *Load more* reads *Loading…* and is `aria-busy` and disabled while busy; a failure raises the screen toast "Couldn't load more checks. Try again.". `.more-row` is left-aligned with 10px above, as the mockup renders it, while the Decision record's `.decision-more` is centred (design advisory A2).

(source: raw/2026-10-10-bot-activity.md §Components; §Concept, ORCH-6 and ORCH-14; §Concept, Plan resolutions, Web)

**`DESIGN.md` refresh (FR-BA-WEB-011, `d0f8408` + `098b0ef`).** +361/−51 at `d0f8408`. It adds the expandable-row pattern, the Bots screen placement and states, focus and live regions including the hidden-dash rule, ten decision rows (PRD §7.6 feature pieces, ORCH-5a, ORCH-6 pending veto, W4, W1, A1, A2, A3, A5 and copy rulings), the verification-evidence entry citing Phase C since `098b0ef`, and a 91-entry source snapshot (check: no drift). The design reviewer checked it (source: raw/2026-10-10-bot-activity.md §Components, DESIGN.md; §Concept, ORCH-14).

**Verification.** 8 new states (quiet, deferred, failed, stale, sections-loading, sections-error, check-expanded, check-error) × 2 themes × 390/600/1080/1440 = 64 captures, plus the 2b ten, with 0 horizontal page scroll. Contrast: 392 measurements, minimum 4.79:1. axe: 0 violations in 18 files. Clipping: 0/833 (Phase A) and 0/836 (Phase C). The light theme at four widths showed no page scroll in the owner-session validation. No screen-reader (VoiceOver) run was done (optional) (source: raw/2026-10-10-bot-activity.md §Test plan, Named acceptance tests, Acceptance status and Preview phases).

**Open web follow-ups.** Unused `WATCH_COPY.region` / `CHECKS_COPY.region`; the three-state `WatchCellView.hidden` (a named discriminant would be clearer); focus after *Load more* is unasserted (shared with the Decision record, design A4); e2e fixture realism (design A6); move the expandable-row styles to `table.css` when a second screen uses them; graduate `formatClockSeconds` into `bangkok-time.ts` (source: raw/2026-10-10-bot-activity.md §Open questions, Web).

## Slice 3a: the Market watch Signals cell

tidewatch-web PR #10 (merge `c2a1b26`, 2026-10-11) filled the existing *Signals* cell (see [[signals-ingest]]). **No new component, route, stylesheet, token or icon.** The cell uses the existing `table.css` classes, and there is no mockup, because the existing cell is filled (PD7) (source: raw/2026-10-11-signals-ingest.md §Components).

**States** (`feat-overview/market-watch-table.ts`, `util/row-view.ts`, SW-2). The `td` keeps `r num` in both states.
- **0 or `null`:** the existing `aria-hidden` dash. The `td` takes `.faint` (`--text-3`), and visually hidden words read *No signals today*.
- **n ≥ 1:** plain digits in `--text`, with hidden words completing "1 signal today" or "n signals today".
- The header stays *Signals*. There is no hue, badge, icon, motion or live region, keeping the Quiet table rule (MW-23): the count changes in place like prices do.

(source: raw/2026-10-11-signals-ingest.md §Components, Signals cell)

**Where it shows.** Only in the Market watch section of Overview, for the user's watchlist rows. The `/signals` page kept the slice-0 `app-screen-placeholder` ("No signals yet") until slice 4 replaced it (see below). How the count is loaded and raised live is on [[market-data]] and [[signal-message-contract]] (source: raw/2026-10-11-signals-ingest.md §Components, Where it shows).

**Docs.** In `DESIGN.md`, the §Table pattern *Columns* bullet and the accessibility "Market watch table" bullet now describe the cell (*No signals today*; "1 signal today" / "n signals today"). `README.md` no longer calls Signals a placeholder column. The web `CLAUDE.md` gained bullets for the Signals cell, the count, once-per-id counting, the reset, midnight and the Signals e2e, plus the `data/testdata/` pin. A `DESIGN.md` snapshot refresh at wrap-up (SW-11) is still open (source: raw/2026-10-11-signals-ingest.md §Components, Docs; §Open questions, Owner actions).

**Verification.** The unit specs cover 0, null, 1 and n. The mocked `e2e/src/market-watch.spec.ts` sends raw C-SIG-1 frames and captures `market-watch-signals-{dark,light}-{390,1080}.png`. P1 Playwright on the preview: 1+689+3 passed, 4 gated skips, 0 failed. The P3 design review approved with 0 blocking, 0 warnings and 5 advisories. Open advisories: the `table.css:110` comment still says "placeholder dash", and `DESIGN.md:638` and `:980` are long lines (source: raw/2026-10-11-signals-ingest.md §Test plan, Named acceptance tests, Reviews and Acceptance at merge; §Open questions, Follow-ups).

## Slice 4: the Signals screen

tidewatch-web PR #12 (merge `da6f4cb`, 2026-10-12) replaced the `/signals` placeholder with `app-signals` (see [[signals-page]]). It is built with Angular 22: signals, `httpResource`, signal forms and no `NgModule`. The `DESIGN.md` rules apply: no Material or chart library, no `dark:`, native controls, nothing animates. **No token, colour, type step or icon was added** (`tokens.css`, `theme.css` and `icons.ts` are unchanged). The approved mockup's soft-mint `.chip.on` and violet impact fill are not used (PW-3) (source: raw/2026-10-12-signals-page.md §Components).

**Visual target (D4).** A browser-verified mockup on the real tokens. Where it differs from `DESIGN.md`, `DESIGN.md` wins, except for the pieces PRD §7.6 names: the pill chip, trust bars, direction tones, the impact bar, the 860px table minimum with the ≤ 1250 density, the sticky `.detail-wrap`, `.nav-count` and the note-slot new-rows line (source: raw/2026-10-12-signals-page.md §Concept, Chosen design D4).

**New pieces** (`src/styles/components/signals.css`, imported after `bots.css` and before `zone.css`).
- **Pill chip.** `.chip` is a pill at 10px/500 with a `--line-2` border. Pressed, it takes a `--brand` border, `--surface-2` and `--text`, with a 0.18 s border and background transition. `.chip-select` wraps a native `<select>` (*Impact ≥*). The filter row wraps, and its `.sep` separators hide at ≤ 600. Filters are three named `role="group"`s of `button.chip[aria-pressed]`.
- **Trust bars.** Five 5×10px bars, with `TIER_BARS[tier]` filled and `aria-hidden`. The tier word sits in `.second`, and hidden text reads "{Tier}, trust {n} of 5".
- **Direction.** `.dir` uses the existing `.change-up/down/flat` tone classes, with ▲/▼/◆ (`aria-hidden`, plus a hidden word) and `p` to 3 dp.
- **Impact bar.** A 96px `.bar` (64px at ≤ 1250), with a `.hi` fill at ≥ 0.70, `aria-hidden`, and the number to 4 dp.
- **Table.** `table.tide.signals` has a hidden caption, eight columns and a minimum width of 860px. At ≤ 1250 it uses 12px cells, a 64px bar and a 220px headline. Rows are quiet and non-interactive (MW-10, MW-23). The headline wraps (min 260px, 220px at ≤ 1250).
- **Bots column (ORCH-16, design B1).** It is 126px above 1250, and its lines wrap at about 112–120px, so the table fits 862/862 at 1100 whatever the data. Rows with long bot lines grow taller, so `DESIGN.md`'s "61px rows" became "at least 61px".
- **Sticky detail wrap (ORCH-18).** `.detail-wrap` is `position: sticky`, with a steady inset (`left: 17px`, 10px at ≤ 600) and `max-width: calc(100cqw − 34px)` (`− 20px` at ≤ 600). The signals section's `.table-scroll` is an inline-size container for this section only, so the three detail columns stay in the visible region while the row's cells scroll. A6 (`container-type` does not disturb scrolling) held.
- **`.nav-count`** (in `shell.css`). The unseen badge on the Signals rail link. It is the one rail badge that `03` §10 allows, and `DESIGN.md`'s "no rail badges" was updated. Its behaviour is on [[user-settings]].
- **Light theme.** `.detail-note` and `.hint` lift to `--text-2`.

(source: raw/2026-10-12-signals-page.md §Components, `app-signals-filters`, `app-signals-table`, Expanded row, Rail badge and Styles; §Concept, ORCH-16 and ORCH-18; §Test plan, Assumption outcomes A6)

**The expandable row moved to `table.css`.** Signals is the expandable row's second consumer, so its rules moved out of `bots.css`, unscoped (SP-W-13/14). That is 11 rules:
- `.tide .details` and `tr[data-expanded="true"] td`;
- the detail cell and status-line rules, now selector lists for `tr.check-detail` and `tr.signal-detail`;
- `.check-note` and `.tide.nested`;
- `.bot-detail .more-row`, renamed to the shared `.more-row`.

The Bots captures stayed 0-pixel identical (144/144, twice).
- **Shared behaviour.** The Signals detail row follows the bot-activity pattern (see [[bot-activity]]):
  - *Details* / *Hide* is a `button.text-btn` with `aria-expanded` and `aria-controls="signal-detail-{id}"`.
  - The row inserts `tr.signal-detail` with one `colspan="8"` cell. Its polite region is inserted empty and filled one task later.
  - The detail is read once per id, and several rows may be open.
  - The detail-row *Try again* focuses that row's *Hide* first, as ORCH-6 did for Checks.

(source: raw/2026-10-12-signals-page.md §Components, Styles and Expanded row; §Concept, Plan resolutions, Web SP-W-13/14; §Test plan, Acceptance status FR-SP-WEB-010)

**States and focus.**
- "Loading signals…" shows in the dashed `.status-line`.
- The error state reads "Signals couldn't load." with *Try again*, which focuses the *Today* heading (`tabindex="-1"`) first.
- The empty day and the empty filter each have their own sentence.
- *Load more* reads *Loading…*, is `aria-busy` and disabled while busy, and a failure raises the toast "Couldn't load more signals. Try again."
- The `.more` note is a polite region. The table is not a live region.

(source: raw/2026-10-12-signals-page.md §Components, `app-signals` and SignalsService)

**`DESIGN.md` refresh (FR-SP-WEB-011; S12 plus P6 `0ebc5cc`).**
- It documents the chip, the moved expandable row, `.nav-count`, the trust and impact bars, direction tones, the Signals states and placement.
- It records the measured fit: 862/862 at 1100 (columns `[56,69,228,130,69,135,116,59]`), 958/958 at 1080, 1152/1152 at 1440, and 860 over 568 / 358 at 600 / 390.
- It adds a "Reconciliation with 03" row (left-aligned Direction and Impact; 5×10 trust bars), a contrast-opacity note (disabled and busy text are exempt) and a Verification evidence entry.
- The P6 check corrected 13 stale "pending" statements, and `forge-setup-impeccable --check` reports no drift (103 sources unchanged).
- The web `CLAUDE.md` gained the Signals conventions: structure, `SignalsApi`/`SignalsService`/badge, URL truth, counting, the Trade context, the quiet badge in specs, and follow-ups.

(source: raw/2026-10-12-signals-page.md §Components, DESIGN.md)

**Verification (FR-SP-WEB-010, passed).**
- Design r1 requested changes (B1: the table did not fit at 1100 once a bot name appeared in the Bots cell). After fix r4, r2 approved at `8dffcfb`.
- 232 captures and 226 overflow JSONs showed no horizontal page scroll. Every table state measures 862/862 at 1100 in both themes.
- axe found 0 violations in 48 runs. The minimum computed contrast is 4.85 (light `.dir.change-down`).
- With motion on, the only movement is the shell's 180 ms screen fade and the chip's 180 ms transition. *Show* and *Load more* motion were not exercised, because there was no data.
- On real data at 1100 (FR-SP-E2E-005), the page's `scrollWidth` equalled `innerWidth` at all five widths in both themes, and the detail wrap measured 828px with three columns.

(source: raw/2026-10-12-signals-page.md §Concept, Stage, Reviewed; §Test plan, Acceptance status)

**Open design and web follow-ups.**
- **A7.** The Bots column stays 126px above 1250, so "Slack Water bought 6.5" wraps even at 1440. A wider column there would keep the 1100 fit.
- **A8.** At ≤ 600, tall rows look half-empty with the Bots cell scrolled off.
- **A3.** Two controls are named "Account". During P1, a `viewport.spec` *Account* selector also collided with the Provenance chip (10 test failures, fixed in fix-r2).
- **A5.** Separators dangle when filter groups wrap.
- Move `.chip` to its own file when a second screen draws a filter chip.
- **Angular review r1:**
  - optional fields on `SignalMessage` (#3);
  - a hanging `GET /sources` keeps the opening on "Loading signals…" when stored filters name sources (#4);
  - a failed *Show* is silent (#5);
  - `feat-signals` imports `LoadMoreOutcome` and `bangkokInstant` from `feat-trade` and should graduate with `order-view.ts` (#8).
- The Trade pre-fill items are on [[signal-cited-orders]].

(source: raw/2026-10-12-signals-page.md §Open questions, Web follow-ups)

## Signals day control: the *Day* select (2026-10-14)

tidewatch-web PR #13 (head `e49c237`, merge `976233f`, 2026-10-14; not deployed) added a *Day* select to the Signals screen (see [[signals-day-control]]). It is built with Angular 22.1 standalone components, signals, `linkedSignal` and `httpResource`. **No token, colour, type step, icon, transition or animation was added.** `tokens.css`, `theme.css` and `icons.ts` are unchanged, and P3 confirmed the empty diff. The owner chose no mockup (DC6) (source: raw/2026-10-14-signals-day-control.md §Components; §Concept, Owner decisions DC6).

**The pieces.**
- **The Day chip (DC1, DC7).** `label.chip.chip-select` holds `span#signal-filter-day-label` "Day" and a native `<select aria-labelledby>`, built exactly like *Impact ≥*. It is first in the filter row, before *Asset class*, followed by an `aria-hidden` `.sep`. The separators still hide at ≤ 600. Options are tracked by `day`, so the `<select>` node survives an options change, and focus and value are kept at a rollover. The select is never disabled.
- **Day-named surfaces.** The section `h2`, the table's scroll-region `aria-label`, the hidden caption, the sub line and the empty sentences take the day phrase ("today", "yesterday", "on Sat 10 Oct"). Today's copy is byte-identical. The `h2` keeps `id="signals-today-title"` and `tabindex="-1"`.
- ***Show yesterday* (DC9).** A `button.text-btn` placed after a space inside the same dashed `p.status-line` as the empty-Today sentence.
- **The one new rule (SDC-W-8, placement only).** It is in `src/styles/components/signals.css` (+12/−1, including the header comment):

  ```css
  .signals-section .status-line .text-btn {
      padding: 0;
      line-height: inherit;
      vertical-align: baseline;
  }
  ```

(source: raw/2026-10-14-signals-day-control.md §Components, `app-signals-filters`, `app-signals`, `app-signals-table` and Styles)

**Design result (P3, rendered review approved).**
- The Day chip measures 117×26, against *Impact ≥* at 114×26, with identical borders, colours and focus ring.
- There was no horizontal page scroll in 60/60 captures, and the table measures 862/862 at 1100.
- The `h2` and count stay on one line in every state, width and theme. At 390 the Day chip takes its own row (+34px), which was accepted.
- axe found 0 violations in 32 files. The minimum contrast is unchanged at 4.85 (the existing light `.dir.change-down`).
- PRD A2 ("Wed 30 Sep" on one line) was judged by proxy, with "Sun 11 Oct" and "Sat 10 Oct" at about 105/358px at 390. The literal label was never rendered.

(source: raw/2026-10-14-signals-day-control.md §Components, Design result; §Test plan, Acceptance status FR-SDC-WEB-012)

**Accessibility.**
- The select is in the Tab order between *Add source* and *All assets*, with the accessible name "Day". The native control announces its value.
- Day changes announce through the existing polite state region ("Loading signals…", then rows or a sentence). Focus stays on the select during a day change (S4).
- *Show yesterday* is a native button with the `.text-btn` focus ring. Pressing it focuses the `h2` first. If it disappears while focused, for example at a rollover, focus moves to the `h2` (SDC-BD-1).
- Screen readers were not tested.

(source: raw/2026-10-14-signals-day-control.md §Components, Accessibility and `app-signals`; §Concept, Spec-level defaults S4 and SDC-BD-1; §Open questions)

**`DESIGN.md` refresh (FR-SDC-WEB-013, verified).** It now documents the filter row with *Day*, the day-named `h2`, the past-day states and copy, *Show yesterday*, the accessibility notes and the SDC-W-8 rule. The Source snapshot was refreshed: it adds the day-control PRD and intent and `bangkok-time.ts`, and repoints the drifted signals-page plan entry to `.forge/features/signals-page/artifacts/plans/tidewatch-web.md` (same SHA-256, SDC-W-10). A "Signals day control" Verification evidence entry cites P1–P3. The P4 commit `e49c237` changed `DESIGN.md` only, and `forge-setup-impeccable --check` then reported no drift (106/106). The design-review A8 and A6 wording advisories were folded in at P4 (source: raw/2026-10-14-signals-day-control.md §Components, Docs in the repo; §Concept, Stage and SDC-W-10; §Open questions, Follow-ups).

**Open design follow-ups.**
- **A10.** The *Show yesterday* focus ring touches the preceding period by 1px. The optional fix is a placement-only `margin-left` of 2–4px on `.signals-section .status-line .text-btn`.
- **A1.** A tighter SDC-W-8 selector.
- **A7 (design r3).** Focus falls to the document when a held pasted-day error ends by the out-of-window fallback to Today. This is rare.
- **Closed:** A2 (the 11px *Show yesterday* beside the 12px sentence) was closed at P3 with no change.

(source: raw/2026-10-14-signals-day-control.md §Open questions, Follow-ups)

## Slice 5: the Chart screen (2026-10-16)

tidewatch-web PR #14 (head `3ebce40`, merge `918d7b6`, 2026-10-16; not deployed) replaced the Chart placeholder with `app-chart` (see [[charting]]). It is built with Angular 22.1 standalone components, signals, `httpResource` and `linkedSignal`. The `DESIGN.md` rules hold:
- **No new token, colour, type step, icon, transition or animation.** `tokens.css`, `theme.css` and `icons.ts` have an empty diff against `976233f`, verified in PV3.
- **Zone hues appear only on candles and strip cells.**
- **Nothing animates.**

The visual target is a spec mockup on the real tokens (`mockup.html`, D6), browser-verified at five widths in both themes (source: raw/2026-10-16-charting.md §Components; §Concept, Owner decisions D6).

**The chart library (D1, S9).** `lightweight-charts` 5.2.1, pinned exactly, is the one chart library, and it is used by the Chart screen only. Overview's own "no chart library" decision still stands for Overview. The library loads lazily through one dynamic `import()` behind an engine seam, never on the server, and `/chart` keeps `RenderMode.Client` (CH-OD-3). `attributionLogo` stays on, as the licence requires. In dark, the library draws its light-variant mark; it measured 17.3 / 17.9:1 and was legible, so the text-link fallback was not needed (FR-CH-WEB-012) (source: raw/2026-10-16-charting.md §Concept, Owner decisions D1 and Operations; §Components, Routes and The engine seam; §Test plan, Acceptance status).

**Colour roles on the canvas.**
- **Palette from the tokens (S10, CH-W-6).** Each zone's computed `--zone` is read from a probe element carrying its `zone.css` class. Every other colour, and the type, come from `getComputedStyle(document.documentElement)`. All of it is re-read on a theme change, which re-sends the bars once and keeps the view. No TypeScript holds a colour literal or names a `--z-*` token.
- **Bars.** A zoned up bar is hollow (`--surface` fill, zone-coloured border and wick). A zoned down bar is filled with the zone colour. A no-zone bar (warm-up, a row not yet landed, or the forming bar) has no fill and a `--line-2` border (PD4). With CDC off, bars are neutral: `--text-2`, or `--surface` for an up bar.
- **EMAs.** EMA 12 in `--text` and EMA 26 in `--text-3`, at 1.2px.
- **Markers.** An up arrow in `--up` below the bar, a down arrow in `--down` above it, and a `--text-2` circle for neutral. There is no `--bg` outline, because the library offers none (CH-BUILD-3).
- **Elliott (PD12).** A `--brand` dashed (3 3) 1.2px polyline with 2.6px dots, and labels in `--font-display` at `--text-sm`, weight 600. Since PF2 each label is stroked 3px wide in `--surface` under its glyphs.
- **Levels.** The invalidation and the Fibonacci levels are library price lines. The 0.382 / 0.5 / 0.618 retracements are specified as dashed `--text-3` (PD11). Price lines are drawn sparse-dotted, because the library has no 2-4 dash (CH-BUILD-2). Level labels write in `--surface` on `--text-3`.
- **Last-value labels (CH-BUILD-9, CH-BD-2).** The candles' and EMA 26's labels sit on `--text-2`, and the candles' label is titled with the symbol (for example "NVDA 217.15").

(source: raw/2026-10-16-charting.md §Components, The engine seam and the canvas; §Concept, Accepted defaults PD4/PD11/PD12, Spec-level S10 and Build decisions CH-BD-2)

**The S11 accessibility exception.** The chart is one focusable `role="img"` wrapper, named by a summary sentence and described by the keys sentence, as an SE-17-style exception. It carries no description while it is named by a state (CH-BUILD-11). The library container is a sibling of the wrapper, not its child, because the attribution is a focusable link (CH-BUILD-1). The `.chart-tip` tooltip is `aria-hidden`, at most `min(360px, 100% − 16px)` wide, with its anchor clamped in the frame. A polite `sr-only` status speaks the tooltip words for keyboard moves only. Focus moves to the wrapper only when the instrument actually changes (CH-BUILD-9, CH-BUILD-11). On the error state, *Try again* focuses the *Timeframe* group first (SE-11) (source: raw/2026-10-16-charting.md §Components, The Chart screen and The engine seam; §Concept, Recorded build behaviours).

**Shared pieces reused or extended.**
- **`app-tide-strip` gained `slots`.** The default stays 48, so Market watch's output is byte-identical; the Chart passes `CHART_STRIP_SLOTS` 96 (PD6). It also accepts `15m`, which Market watch's parser still refuses. Strip words read "{symbol}, last 96 {15-minute|hourly|daily} zones, oldest to newest, ending in Buy for 11 bars", with a daily note "96 days · EOD". On the Chart the one-row strip table overrides `.tide`'s 650px minimum (CH-W-15) and takes no hover fill.
- **The Market watch symbol link.** `.asset-symbol` became `a.asset-symbol[routerLink]`, in `--text` with `--brand` on hover and the global focus ring. Its accessible name is `aria-label="{symbol} chart"` (CH-W-29), and the row stays non-interactive (MW-10). `market-watch.css` gained one rule.
- **`.switch[aria-checked="true"]::after`** joined the existing pressed rule in `shell.css` as a selector list (CH-W-14).
- **Reused as they are (S12):** `.range-switch`, `.switch`, the glass panel, `.side .row`, `app-zone-label`, `.tag`, the Bots verdict words, and `label.chip.chip-select` for the *Instrument* select.

(source: raw/2026-10-16-charting.md §Components, Market watch link and the 96-slot strip, Styles and docs, and The Chart screen; §Concept, Spec-level S12)

**The new stylesheet.** `src/styles/components/chart.css` scopes every rule under `.chart-screen` (CH-W-16) and is imported in `styles.css` before `zone.css`. It holds `.chart-tools`, `.chart`, `.chart-wrap`, `.side`, `.panel`, `.ew-alt`, `.feed`, the strip row, `.trade-links`, the breakpoints and the tooltip width. Literal radii (12px on `.chart-frame` and `.chart-focus`, 10px on `.chart-earlier`, 4px on `.feed .item`) are recorded as a known inconsistency, `DESIGN.md` item 25; no token was added (source: raw/2026-10-16-charting.md §Components, Styles and docs).

**Layout.** Above 1080, a two-column grid, `minmax(0,1fr) 290px` with a 20px gap. At ≤ 1080, the three right-column panels sit in a row under the chart; at ≤ 820 they stack; at ≤ 600 the toolbar wraps and the `.sep`s hide. The chart region is 440 / 360 / 300 px tall. PV3 measured frames of 824×440 at 1440, 534×440 at 1100, 940×360 at 1080, 550×300 at 600 and 340×300 at 390, matching PRD §7.8 (source: raw/2026-10-16-charting.md §Components, The Chart screen, Layout).

**Recorded build behaviours (`DESIGN.md` CH-BUILD-1…12).**
- CH-BUILD-1: the library container is the wrapper's sibling. CH-BUILD-2: sparse-dotted price lines. CH-BUILD-3: no marker outline.
- CH-BUILD-4: the header sub line is plain text, and the status `.tag` leads the right-hand actions.
- CH-BUILD-5: right-column panels are `section`s named by `h2`s drawn at the `h3` size.
- CH-BUILD-6: *Fibonacci* is independent of *Elliott count*; PageUp/PageDown move 10 bars.
- CH-BUILD-7: an off-watchlist instrument opens at 1h; a daily base then answers 422, and the chart falls back to 1D with two `replaceUrl` writes.
- CH-BUILD-8: a chosen candidate is kept across re-reads of the same chart while it is still offered.
- CH-BUILD-9 and CH-BUILD-11: the review r1 and r2 fixes (focus, engine error, label colours, touch, tooltip width; focus on `[`/`]`, the status reset, no description in states, "Loading chart…" during an engine restart).
- CH-BUILD-10: the signals re-read cancels an in-flight read rather than queueing one.
- CH-BUILD-12: the PF2 fixes (Fibonacci labels, the Elliott halo, the header sub line on error and unknown, the *Buy*/*Sell* pair).

(source: raw/2026-10-16-charting.md §Concept, Recorded build behaviours in `DESIGN.md`)

**Reviews.** Code review r1's design pass requested changes on the source (W1–W6): focus lost on `[`/`]`, axis label colours and contrast, `vertTouchDrag`, tooltip width, the header tone (became CH-BD-1) and the attribution logo (moved to PV3). Fix round 1 answered them. The **PV3 r1** rendered review viewed 130 captures, 130 overflow JSONs, and 26 contrast and 26 axe JSONs, and requested changes. Fix round PF2 answered:
- **B1 (blocking): the Fibonacci levels had no labels.** In 5.2.1, `axisLabelVisible: false` also hides a price line's title, so "fib 0.382" never drew; the mockup had the same defect. Every Fibonacci level now carries its axis label. PV3 r2 reads "fib 0.382 180.90", "fib 0.5 179.05" and "fib 0.618 177.20", at 5.17–5.46:1 dark and 4.55–4.84:1 light.
- **W1: Elliott labels were unreadable on a same-hue bar** (`--brand` on `--z-green`, 1.30:1 dark, 1.46:1 light). The 3px `--surface` stroke brings them to 12.98:1 dark and 7.40:1 light.
- **W2: the last-price and EMA 26 labels merged.** The symbol title (CH-BD-2) separates them, at 8.89:1 dark and 5.97:1 light.
- **W3:** the error and unknown states kept "Loading…" in the header; the header now says the state's sentence.
- **W4:** at 390 in the closed state, *Sell* wrapped alone; `.trade-links` now keeps the pair together.
- **C1:** the focus ring, the tooltip at the edge and the engine error were not captured. Three new hook-free capture tests show a 2px `--focus` ring at a 4px offset, a tooltip that stays inside the frame at 390 and 1440, and an engine-error region pixel-identical to the head-read error.

**PV3 r2 approved** at 2026-10-16T02:57:40Z, with W5 and W6 left open as follow-ups (CH-BD-4) (source: raw/2026-10-16-charting.md §Test plan, Defects found on the preview and their fixes; §Concept, Review history and Build decisions CH-BD-4).

**Verification (FR-CH-WEB-009, 010, 012).** 130/130 captures had no horizontal scroll. axe found 0 violations in 26 runs at 1440. The focus ring measured 13.01 / 7.40:1. **Touch scroll at ≤ 600 px is unverified**, and the 390/600/1080/1100 matrix captures were resizes of a chart opened at 1440 (source: raw/2026-10-16-charting.md §Test plan, Acceptance status; §Open questions).

**`DESIGN.md` and the other repo docs (S11, PV4 `3ebce40`).** `DESIGN.md` gained the chart pieces, a colour-role table, states and copy, accessibility, the S11 exception, CH-BUILD-1…12 and CH-BD-1/2, known inconsistencies 25–30 (W5 and W6 open), a refreshed source snapshot, and the "Charting" Verification evidence entry. Before PV4, `forge-setup-impeccable --check` found 8 hashes changed since S11, and all were refreshed. That entry was written before the merge, so it says "not merged". The web README gained the route, a "Signals on this chart" section and *Third-party notices*, which carries the upstream v5.2.1 NOTICE text. The web `CLAUDE.md` gained the `feat-chart` structure, the engine seam and lazy library, the chart reads and live rules, the test hook, `elliott.model.ts`, the two-key pre-fill and the e2e notes, with its managed blocks byte-identical (source: raw/2026-10-16-charting.md §Components, Styles and docs; §Concept, Operations; Sources (inputs to this document)).

**Open design follow-ups (CH-BD-4; `DESIGN.md` known inconsistencies 29–30).**
- **W5.** At 390, price-line titles ("count invalid below", the symbol title) cover the Elliott labels "4" and "(5)" and the newest bars, because the library draws titles after every primitive. Fix: anchor each label at its vertex bar's low or high instead of the close.
- **W6.** The crosshair paints over the tooltip, because the library's top canvas has `z-index: 2`. Fix: `.chart-screen .chart-engine { z-index: 0 }`, then re-capture the tooltip edge at 390.
- **PV3 r2 advisories.** The focus ring covers the region border at the bottom edge (6px of bottom padding would even it). The error and unknown header repeats the region's sentence, so a screen reader hears it twice. At 390, fib 0.5 and 0.618 can fall outside the auto-scaled price range (an `autoscaleInfoProvider` could include them). Edge time labels clip, and axis ticks peek under value labels (library behaviour).
- **CH-BD-1.** An optional projected sub line on `PageHeader`, so the Chart's 24h change can carry its up/down tone.
- **Item 25.** The literal radii in `chart.css`.

(source: raw/2026-10-16-charting.md §Open questions, Open design follow-ups and Web follow-ups)

## Slice 6: Bots additions, the version editor, *Your strategies* and the Trade card (2026-10-21)

tidewatch-web PR #15 (head `4ab65db`, merge `acbd75d`, 2026-10-21; not deployed) is described on [[bots]]. Angular standalone components with signals, `httpResource` and signal forms; Vitest (source: raw/2026-10-21-bots.md §Components).

**No new token, colour, type step or icon, and nothing animates.** The pieces are feature-local:
- `bots.css`: `.spark`, `.loop-row`, `.w`, the range, `.radio`, `.policy`, `.class-row`, `.alloc-bar`, `.editor-actions`;
- `portfolio.css`: `.bot-card`;
- `trade.css`: the `.reco` additions.

The visual target is one mockup on the real tokens at 390, 600, 1080 and 1440 in both themes (D13) (source: raw/2026-10-21-bots.md §Components; §Concept, Owner decisions D13).

**Patterns and recorded choices.**
- **`app-sparkline`** (`ui-sparkline/`): an inline SVG of 120×28, `aria-hidden`, with sr-only text "equity over 30 days, {first} to {last}". `Number` scales it for drawing only. Used in the Bots list's *Equity, 30 days* column and on Overview's cards.
- **A neutral *Champion* tag.** The design review accepted a neutral `.tag` rather than the mockup's `.champ` border. The detail head's missing *Champion* tag was GAP-W3, fixed in review.
- **Soft-disabled busy controls.** Busy primaries stay focusable with `aria-disabled` (and `aria-busy` where relevant): *Run now* → *Queued…*, *Creating…*, *Cloning…*, *Saving…*, *Declining…*. Playwright checks `toHaveJSProperty("disabled", false)` plus the ARIA states and focus, because `toBeEnabled` treats `aria-disabled` as disabled (PF1 F5).
- **Loops rows tracked by loop**, so each *Run now* stays one DOM node through the 10 s refresh; held 202s are dropped by the store, never from the announcing effect (the r2 angular blocker).
- **ORCH-7, the allocation bar.** Cash is the `--surface-3` track; US `--text-2`, TH `--text-3`, Crypto `--brand` at `--opacity-benchmark`, Gold `--brand`. This follows PRD §7.4 and the mockup and resolves a contradiction with §4.15.4. Beside it: "Allocation is a ceiling, never a target." and the sum check; Save is disabled while the sum is over 100 %.
- **Decision-model cards** are four `.radio` cards in a `radiogroup`, each with ≈ ฿/decision and "measured, 7 days" or "list price"; an unavailable card is greyed and not bound.
- **Editor layout.** The Universe and Schedule groups span the full width below Policy, because the 0.9fr column cannot fit the six-cell class row; the design review accepted this.
- **FU-1 cap messages** ("Use 10 or fewer." / "Use 20 or fewer.") render as the refused class row's next sibling, directly under it, with `aria-invalid` on the field (fix `f6eb8c0`, after FU-1 design r4 B1 found them in the Universe group's foot line; 90px cells would otherwise wrap). The active-bot sentence goes on the dialog's alert line, and the rate-limit sentence is a toast.
- **Overview cards.** `a.bot-card`, one per auto bot, newest first, between the KPI strip and Market watch; the 30-day return in its tone class; "{n} decisions" pluralised (GAP-W2). The manual bot is never a card.
- **The Trade card** keeps the `section.reco` place and styles, with a `label.chip.chip-select` *Follows* (see [[signal-cited-orders]]).
- **Watch words** for the nine C11' verdicts are on [[bot-watch-verdicts]].

(source: raw/2026-10-21-bots.md §Components, Bots screen, Overview and Trade; §Concept, ORCH-7; §Concept, Review history, Web code; §Test plan, Defects found on the preview)

**Verification.**
- **PV3, after PF1 (FR-BT-WEB-010):** keyboard journeys 12/12, axe 62/62, contrast ≥ 4.5:1 74/74, no horizontal scroll 592/592, clipping 8/8.
- **PV2 (FR-BT-WEB-011): CHANGES REQUESTED.** 280 captures (35 states × 2 themes × 4 widths) went to the rendered review, which returned changes after the web had merged. A follow-up web fix is in progress for:
  - **B1 (blocking):** the Clone dialog's `class="fixed"` collides with Tailwind's `fixed` utility, so the clone line overlaps the Strategy label;
  - **S1:** the cap-message divider placement;
  - **S2:** the Policy error placement at 390 px;
  - **S3:** the Overview error-line alignment.
- The code-level design review had approved (after B1 of FU-1 r4 was fixed). The source document, written before the verdict, says PV2 "was still running"; the orchestrator's correction of 2026-10-21 supersedes it.

(source: raw/2026-10-21-bots.md §Test plan, Acceptance status and Preview runs; PV2 verdict and findings from the orchestrator correction of 2026-10-21)

**`DESIGN.md`.** S15 updated `DESIGN.md`, and `f6eb8c0` added the BT-W mapping. The slice's *Verification evidence* entry was left for a follow-up web PR, and `DESIGN.md` may need a refresh once the PV2 fixes change visuals (source: raw/2026-10-21-bots.md §Files touched, tidewatch-web S15 and `f6eb8c0`; §Open questions).

**Open design and web follow-ups.**
- The PV2 fixes B1, S1, S2, S3 (in progress).
- Design advisories: an upgraded legacy bot reads "strip-timeframe manager"; "your watchlist" hides enabled classes; *Saving…* drops focus.
- `refusalCapClass` matches a path prefix only, and an over-cap value on a switched-off class focuses an empty alert line.
- `validateBotConfigV2`'s shape check runs twice on a refusal, and `sharesBeforeOff` survives a save.
- FU-6, the PF1 nits: assert *Upgrade*'s focus ring after a keyboard *Cancel*; tidy `FOLLOW_KEY` and a stale comment in `trade.spec.ts`; scope `app-bots .toast` in the contrast lists.
- The Decision record should word general-engine decisions in slice 7 (BT-W-9).

(source: raw/2026-10-21-bots.md §Open questions, Web review follow-ups and FU-6; PV2 items from the orchestrator correction of 2026-10-21)

## Slice 7: the Stats screen (2026-10-27)

tidewatch-web PR #20 (head `9a88771`, merge `74918fd`, merged 2026-10-27 and deployed to production the same day) replaced the `/stats` placeholder with `app-stats` (host class `stats-screen`); `feat-screen-placeholder/` was deleted, since Stats was its only user (see [[statistics]]). Angular 22 standalone components with signals and `httpResource`; Vitest. The visual target is `mockup.html` at 1440, 1100, 1080, 600 and 390 in both themes (D13) (source: raw/2026-10-27-statistics.md §Components; §Concept, Owner decisions D13; §Concept, Stage).

**No new token, colour, type step, icon, transition, animation or dependency, and no chart library on Stats.** Overview's chart and `util/chart-geometry.ts` are untouched; the Stats equity chart is a sibling on `portfolio.css`'s classes (source: raw/2026-10-27-statistics.md §Components; §Files touched, tidewatch-web, Unchanged by design).

**The pieces (`feat-stats/`).**
- **`stats-controls.ts`:** the *Bot* select ("· champion" on the champion), the *Version* select, and the `.range-switch` *30 d / 90 d / All / Custom* with native *From*/*To* date inputs bounded by the answer's window.
- **`kpi-row.ts`:** seven cells (Return, Max drawdown, Sharpe, Win rate, Decisions, Calibration error, Cost of decisions), each a label, a `.num` and a note. **Figures are never coloured.** The bordered strip has 7 columns, 4 at ≤ 1250 and 2 at ≤ 600. The win rate reads `57.00%` where the mockup shows `57%` (ST-W-3).
- **`stats-equity-chart.ts`:** inline SVG with three gridlines, the benchmark path in `--violet` at `--opacity-benchmark`, the equity path in `--brand` and the `.drawdown` area between the running peak and the equity. Date labels and right-hand value labels are HTML `.axis` spans over the stretched SVG, so the viewBox never squashes them. SE-17 keyboard keys (`role="img"`, `tabindex="0"`, arrows, Home/End, Escape) and nearest-point pointer picking; the tip is `aria-hidden`, and a polite status speaks keyboard moves only (see [[charting]]).
- **`calibration-plot.ts`:** a `role="img"` SVG with a dashed `.diagonal` and one `--violet` `.dot` per non-empty bin, radius `3 + √n / 1.4`, each with a `<title>`; the caption, the ECE line, and a visually hidden table of the ten bins (S10).
- **`attribution-table.ts`:** a named group of four `button.chip[aria-pressed]` (*Source*, *Event type*, *Asset class*, *Regime*; screen state, not URL state) and a `.table-scroll` region; returns in the change-tone classes; *Trust* on Source only.
- **`losses-panel.ts` and `losses-list.ts`:** one `.pm` row per label with an `aria-hidden` `--text-2` bar (`.pm-bar`), a template paragraph (PD6, no model call), and the labelling list with a native select per row.
- **`compare-panel.ts`:** a `.stats-panel.compare` with a `.compare-grid` (`role="table"`, `display: contents` rows), and verdict lines in `--text` when met and `--text-2` when unmet. *Promote to champion* is a `.btn.primary`, `aria-disabled` with `aria-describedby="compare-verdict"` unless the verdict passes.
- **`util/stats-view.ts`** holds every Stats word and S15's formatting: signed ratios with two digits and a U+2212 minus, ECE with 3 digits, Sharpe and Sortino with 2, THB through `formatThb`. It imports `TIER_WORDS` (feat-signals) and `TONE_CLASS` (feat-trade), cross-feature imports that FU-3 would graduate. There is no `Date.now()` in `feat-stats/`.

(source: raw/2026-10-27-statistics.md §Components, Data layer and The Stats screen, Pieces)

**Recorded choices.**
- **The `--down` drawdown exception (D13).** The equity chart's drawdown area is drawn in `--down` at low opacity (`.12`, legend swatch `.18`) through `stats.css`, never in a zone colour. The approved mockup in `documents/` shades drawdown with `--z-red`; D13 supersedes it, and `documents/` was not edited. **No zone hue anywhere on Stats:** `--z-*` never appears in `feat-stats/` or `stats.css`, specs included (the zone-token grep returns nothing).
- **`.stats-screen` scoping (ST-W-2).** Every rule (89 at PF3) sits under `.stats-screen` inside `@layer components`. The mockup's `.panel` became `.stats-panel` (S9), and there is a new scoped `.panel-status`.
- **OD-5: `h2` titles with the `h3` look.** `.stats-screen .panel-head h2` takes `--text-h3`, `--font-weight-title` and `--text`, so axe heading order passes. It amends PRD §7.6, in the same spirit as the Chart's CH-BUILD-5.
- **OD-7: shared source names.** Stats uses the Bots editor's `SOURCE_NAMES` (keyed by source code, falling back to the publisher) on attribution Source rows and the labelling list's *Signal* cell. PF2 moved it from `feat-bots/util/bot-draft.ts` to the shared `pages/workspace/util/source-names.ts`. It was found because three SEC EDGAR sources all read "SEC EDGAR · Filing" (PV2 B2). A loss row whose signal has a null publisher (XP-1) reads the editor's name for its code, else the code, else "—".
- **`.chip` graduated (ST-W-14).** `.chip` moved byte for byte from `signals.css` into a new `chip.css`, imported before `signals.css`; Signals renders unchanged (182/182 captures identical to the slice-6 baseline).
- **Busy buttons (ST-W-15).** `.stats-screen .btn[aria-busy="true"]` copies ORCH-30's rule. The labelling list's *Save* is soft-disabled with `aria-busy` while in flight.
- **Accepted deviations** (recorded in `DESIGN.md` "Stats words beyond PRD §4"): `57.00%`, HTML axis labels, the dropped mockup panel-head note, `.pm-bar` instead of `.bar`, the new `.panel-status`, the attribution cost note, the empty labelling list sentence, the OD-6 headings and "· champion" on the compare option.

(source: raw/2026-10-27-statistics.md §Components, Styles; §Concept, Owner decisions D13, OD-5 and OD-7; §Open questions, Accepted web deviations and `documents/` drift; §Test plan, Preview runs PV2)

**Bots editor and Trade.**
- **The editor's net figure (FR-ST-WEB-010).** `weightRow` reads `avg_r_5d_net` and writes it with two fraction digits and U+2212 (OD-4), worded "avg 5 d, net · n {n}" (it read "avg 5 d · n {n}"). *Fit weights* still reads gross. PF2 fixed the note breaking between "n" and its count (W5).
- **The follow-record sentence (FR-ST-WEB-011).** `p.reco-record` after `section.reco` on every loaded recommendation: not a live region, no tone class, `--text-2` (`trade.css`).

(source: raw/2026-10-27-statistics.md §Components, The Bots version editor and Trade)

**Layout.** `.stats-grid` is 1.8fr/1fr, 1.5fr/1fr at ≤ 1080, and one column at ≤ 820. After PF2 all eight attribution columns fit at ≥ 1251 px, and the table scrolls inside its region at 1100 and 1080. PF2 also fixed the hidden calibration table pushing the page 355 px wide at 1100 and 390 (W2). PF3 set the compare grid to `minmax(0,1fr) fit-content(32%) fit-content(32%)` so a long champion name wraps in its column at 390 (W8) (source: raw/2026-10-27-statistics.md §Components, Styles and Pieces; §Test plan, Defects found on the preview).

**Verification.**
- **PV2 (rendered design review, 230+ captures):** round 1 CHANGES REQUESTED (B1 focus lost after *Label losses*; B2 indistinguishable source names → OD-7; W1–W7 spacing, overflow, wrapping and long names). PF1 and PF2 fixed them; the re-check at `a7e4e56` **APPROVED**, and W8 was fixed in PF3.
- **PV3:** axe 0 violations and contrast ≥ 4.5:1 in 7 states × 2 themes at 1440; `a11y.spec` 22/22; keyboard reach passes after PF1 (it failed in PV1 as F-PV1-4).
- **FR-ST-WEB-012:** 160 state captures and 40 element captures at exact widths, no page scroll.
- **Not captured or not measured:** the equity tooltip and pointer pick (WEB-004), focus-ring visuals (WEB-014), contrast at widths other than 1440, nine states' contrast, and VoiceOver/Safari reading of the `display: contents` compare rows.
- **PV2 advisories left as they are:** the first-champion verdict wording under "Over its own window", the toast covering *Champion* at 390, the compare window note at 390, and the PRD's fresh-version wording.

(source: raw/2026-10-27-statistics.md §Test plan, Acceptance status, Preview runs and Defects found on the preview; §Open questions)

**`DESIGN.md`.** S14 and the fold added the Stats pieces, OD-3…OD-7, "Stats words beyond PRD §4" and the status names; PF2 updated it with OD-7; PV5 (`9a88771`) added the "Statistics (slice 7)" Verification evidence entry, with a snapshot of 165 sources and 0 drift; `forge-setup-impeccable --check` is clean (FR-ST-WEB-015). `prettier --check` fails on the base `DESIGN.md`, which was not reformatted by the project's scope rule (source: raw/2026-10-27-statistics.md §Files touched, tidewatch-web; §Test plan, Acceptance status; §Open questions).

**Open web follow-ups.** FU-3 (graduate `TIER_WORDS`, `TONE_CLASS`, `BOT_TRIGGER_WORDS`, `LoadMoreOutcome` and `number-format` to `pages/workspace/util/`; one shared `isUuid`), FU-4 (a `PageHeader` `focusHeading()` API; raise toasts from the screen), FU-5 (the 366-day custom-span UX; F13, a neutral disabled title when every challenger was refused) (source: raw/2026-10-27-statistics.md §Open questions, Follow-ups).

## Accounts and roles: the operator console (2026-10-29)

tidewatch-web PR #23 (head `ce420a7`, merge `4725cb9`, merged 2026-10-29 and deployed to production the same day) added the operator console, a lazy route tree under `src/app/pages/admin/` with its own shell, store, guards and API service (see [[operator-console]]). The product's `AuthService`, guards and `/sign-in` sources are byte-identical to the base (source: raw/2026-10-29-accounts-roles.md §Components).

**No new token, colour, type step or motion.**
- **`console.css`.** `src/styles/components/console.css` is one `@layer components`, imported after `stats.css`, with every selector scoped under `.console`. It has no literal colour, no `--up`, `--down` or `--z-*`, and no transition or animation. Greps gate `pages/admin/` and the file.
- **The pieces:** `.console-caption`, `.code-field`, `.resend`, `.phone-row`, `.secret-box`, `.row-actions`, and `table.tide.people`, `.operators`, `.audit` and `.spend`. It copies the ORCH-30 busy-button rule for the console's primaries; promoting that rule to `button.css` is a follow-up.
- **Four new icons** in `shared/ui-icon/icons.ts`: `people`, `operators`, `audit` and `spend`. These are the one icon addition PRD §7.2 allows.

(source: raw/2026-10-29-accounts-roles.md §Components, Styles and icons)

**The console shell (S19).**
- **The frame.** It reuses the product frame with a `console` host class. The workspace card reads *Operator console* / *{role}*, the rail label `CONSOLE`, and the nav *People*, *Operators* (owner only), *Audit* and *Spend*.
- **Labels.** The mode line reads *Operators only*, the environment pill *Operator console*, and the breadcrumb `Console / <Screen>`. The account menu reads *Signed in as {username} · {role}*.
- **Narrow widths.** At ≤ 600 px the rail becomes a 4-column strip, or 3 columns for staff.
- **Sign-in.** `/admin/sign-in` is a full-page glass panel captioned *Operator console*, with no links, theme switch or sign-up. The *Resend in {n} s* countdown number sits in `span.count` with tabular figures (VW1, `10851db`).
- **Temporary password.** It shows once in a `.secret-box`, and a 38-character password wraps only at its hyphens at 390 px (OQ-W4, VW2 `10851db`).
- **Tables.** The People table has an 860 px minimum. *Actions* are pinned right above 600 px and static at ≤ 600. Spend shows dollars with two decimals, or four under a cent.

(source: raw/2026-10-29-accounts-roles.md §Components, Screens; §Concept, Decisions during the build OQ-W2..W4)

**Product-side changes (§4.9.8).**
- **Account menu.** *Signed in as {display_name}*, with the username under it in `--text-3` when they differ (see "Account menu (D7)" above).
- **Bots editor** (`editor-tiers.ts`). An unentitled tier is greyed with the title *Not in your plan* and a visible "not in your plan" reason (H9).
- **Unchanged screens.** The create dialog's limit sentence reads `details.limit`. A `400 not_entitled` in Create or Clone shows the generic failure line, and `/sign-in` is unchanged.

(source: raw/2026-10-29-accounts-roles.md §Components, Product-side changes)

**Verification.**
- The final `operator` run (`10851db`) passed 527/527: 360 captures (36 states × 5 widths × 2 themes), 360 axe runs with 0 violations, and no horizontal page scroll.
- 424 contrast pairs were measured, the lowest 4.65 (`aside.rail .nav-label`, light).
- The visual pass approved 0/3/13. VW1 and VW2 were fixed in `10851db` and re-checked APPROVED.
- **VW3 is open for the owner.** The Edit dialog's country select (150 px) shows "United States and C" and hides `+1` above 600 px. Either put the dialling code first, which needs a copy sign-off, or widen the select.
- Code-level design review round 1 found that axe covered only part of the matrix, and the fix rounds closed it.

(source: raw/2026-10-29-accounts-roles.md §Test plan, Preview runs; §Concept, Review history, Web; §Open questions, Open owner decisions)

**`DESIGN.md`.** It gained "Console pieces", the states and captures, 16 decision rows (AR-W and OQ-W) and a refreshed source snapshot. `a7498cd` corrected it after the PR opened and had no reviewer re-read. COPY-SIGNOFF lists the copy beyond the PRD that the owner still has to sign off (source: raw/2026-10-29-accounts-roles.md §Components, Styles and icons; §Test plan, Not verified or partial; §Open questions, Open owner decisions).

## Signals context: discovery rows in the Schedule group (2026-10-30)

tidewatch-web #22 (merge `9dc59cf`, 2026-10-30; deploy triggered, not verified) is described on [[signals-context]]. **No new component, token, colour, icon or motion.** Design authority is `DESIGN.md`; there was no mockup.

- **Two full-width rows in `feat-bots/editor/editor-schedule.ts`,** after the wake times and before *Manager checks*. Each is a `.field` with a `.switch` (`button[role="switch"][aria-checked]`) named by its words. While a row is on, a native number input appears:
  - *Also propose on coverage anomalies*, with *Z-score at least* (`z_min`, 0.5–10, step 0.1);
  - *Also propose before earnings*, with *Within N sessions* (`sessions_ahead`, 1–20, step 1).
- **Layout.** The switch sits on the row-label line. The number appears on a second line, indented 46 px, at most 160 px wide. A switch-alignment issue was one of the r1 design findings.
- **Refusals.** A refusal under `…discovery.context` or `…discovery.calendar` is drawn under its row. `aria-invalid` and `aria-describedby` go to the number when the refusal names it, else to the switch. Focus follows `data-field`.
- **The draft model (`feat-bots/util/bot-draft.ts`, SC-W-2..4).** The words live here. `serialiseDraft` drops `discovery` when both rows are off. An off row saves its number as loaded (the contract default `"2.0"` or `"5"` when the version had none), so a hidden number is never refused and off-then-on leaves nothing to save. A stored both-off `discovery` reads as unchanged (`sameConfig`), so opening it offers no *Save*.
- **The vocabulary leaf (`data/bot-config.model.ts`).** It exports `DISCOVERY_KEYS`, `DISCOVERY_CONTEXT_KEYS`, `DISCOVERY_CALENDAR_KEYS`, `DISCOVERY_Z_MIN {min "0.5", max "10", default "2.0"}` and `DISCOVERY_SESSIONS_AHEAD {min "1", max "20", default "5"}`, plus the validator, reader and a faithful writer. `BOT_CONFIG_VOCABULARIES` is not extended. The service and bot implement the same key (see [[bot-versions-and-runs]]).
- **Scroll margin (PV2 finding B1, fix 2).** In `src/styles/components/bots.css`, a ≤ 600 px `scroll-margin-top: 124px` on `.bot-detail .editor [data-field]` keeps a focused field clear of the sticky strip.
- ***Sources and weights*** shows N's three rows by raw source code, because `SOURCE_NAMES` has no entry for them (owner ruling WEB-OQ-1).
- **Signals: no product change** (intent non-goal, SC-W-8; WEB-OQ-3 accepted the shipped rendering). A coverage signal renders through the existing row and detail, without the dashes the PRD text asked for. See [[signals-page]].
- **`DESIGN.md`.** `CLAUDE.md` and `DESIGN.md` record the rows, the sibling pin and SC-W-4..6. The *Verification evidence* entry is "Signals context (spec 3b)", and the snapshot refresh was kept (WEB-OQ-2). After the L update, the web kept both sides of `DESIGN.md`.
- **Verification.** FR-SC-WEB-001 was verified on Chromium only. WebKit/iOS Safari, contrast at 390/600/1080 and touch are unverified. FR-SC-WEB-002 was verified (PV3 on the real service, 0 console errors). `bots-editor.spec.ts` covers the save shapes, refusals beside the control, 390/600 clear-of-strip, the switch focus ring and 8 `bots__editor-discovery-…` captures. PV2 design was approved at the re-check. The e2e specs were not re-run on the merged tree.
- **Follow-ups:**
  - PV2 R1: a ~148 px scroll margin so the label shows at 390;
  - PV2 R2: a shared strip-height custom property instead of the hand-derived 124 px;
  - PV2 R3: verify the scroll margin on WebKit / iOS Safari;
  - PV2 R4: an app-wide `scroll-padding-top` at ≤ 600;
  - design A2 (a double announcement), A3 (a focus fallback for a hidden-number refusal) and A4 (the "Within N sessions" wording);
  - a whole-object discovery refusal focuses a switch with no `aria-describedby`;
  - the web testdata README has no C15 row;
  - the pre-existing flaky *Add source* focus test.

(source: raw/2026-10-30-signals-context.md §Components, Web; §Concept, Owner rulings; §Concept, Review history, Web; §Concept, Merge updates; §Test plan, Web and Recorded results; §Open questions, Smaller recorded follow-ups)

## The `Dialog` close contract (fix dialog-reopen-race, 2026-10-30)

A standalone `/forge-fix` in tidewatch-web only. tidewatch-web PR #25 (commit `6842b0a`) was merged on the owner's instruction on 2026-10-30 as `0fa0019`. The merge started `deploy-prod` and `release-please`, but **deployment was not verified**. Only `src/app/shared/ui-dialog/dialog.ts` and its spec changed; no style, token or template changed (source: raw/2026-10-31-fix-dialog-reopen-race.md, summary; §Components; §Files touched).

**The bug.** Reopening an `app-dialog` straight after closing it could leave the page dimmed by the blurred `::backdrop` with no panel and no buttons, because the empty `.dialog-panel` is `display:none`. It surfaced as the flaky Signals e2e "opens Add source and returns focus" (Enter on *Done*, then at once on *Add source*; see [[signals-page]]) (source: raw/2026-10-31-fix-dialog-reopen-race.md §Concept, The bug).

**Root cause.** `close()` calls the native `HTMLDialogElement.close()`, then `finish()` itself. The browser removes `open` at once but fires the `close` event later. If `open()` ran in between, the late event reached `onNativeClose()`, which checked only `openState()` and ran `finish()` a second time while the `<dialog>` stayed open and modal:
- the `@if (isOpen())` body was removed;
- the MW-16 Escape capture listener came off;
- focus went to a trigger made inert by the modal;
- a second `closed` landed in the new opening. Callers that reset on `(closed)` reset mid-opening: *Add instrument* cleared its query, *Add person* and *Reset password* cleared the temporary-password secret and their busy flag (see [[operator-console]]), and Operators dropped the new opening's results as stale.

(source: raw/2026-10-31-fix-dialog-reopen-race.md §Concept, Root cause)

**The fix.** `onNativeClose()` now finishes only when the element is really closed: `if (this.openState() && !this.dialog().nativeElement.open)`. In the HTML "close the dialog" steps the browser removes `open` before it fires `close`, so a genuine outside close (`form method=dialog`, `requestClose`, a foreign `.close()`) still finishes once, and a stale event arriving after a reopen is ignored. The guard adds no state and reads `openState()` first, so a late event never reads the `viewChild`. The diagnosis rejected an opening or pending-close counter (extra state that can drift) and letting only the native event call `finish()` (closing would become asynchronous and `closed` would fire later) (source: raw/2026-10-31-fix-dialog-reopen-race.md §Concept, The fix and Why the guard is safe).

**What callers can rely on.**
- Exactly one `closed` per opening, however many native `close` events are queued.
- A fast close-then-reopen keeps its body rendered, its Escape listener and its focus on the first field.
- Escape then closes the dialog once and returns focus to the trigger.
- `close()`, the Escape and `cancel` paths, the template and the public API (`open`, `close`, `isOpen`, `closed`) are unchanged.
- Every caller opens through `open()` and closes through `close()`: Signals *Add source*, Overview *Add instrument* and *Edit list*, the Bots dialog, the four People dialogs and Operators. None uses `method=dialog`, `requestClose()` or a native call, so `dialog.ts` is the only code that calls `showModal()` or `close()`.

(source: raw/2026-10-31-fix-dialog-reopen-race.md §Concept, What callers can rely on now; §Components)

**Verification (2026-10-30).**
- **Regression test.** "ignores the native close event of an earlier close() once it has opened again" in `dialog.spec.ts` failed before the fix (at `isOpen()`, with the element still `open`) and passes after (35/35). jsdom has no `showModal()` or `close()`, so the spec's stubs remove `open` and dispatch `close` asynchronously, as a browser does.
- **Suites and reviews.** The full unit suite passed (6489 tests), and lint, build and Prettier were clean. The code, security and angular reviewers approved with nits only; the security review found no genuine close path that now skips `finish()`.
- **On a preview.** The Signals e2e passed 5/5 with `--repeat-each=5` and 20/20 with `--repeat-each=20`. Eleven manual fast-reopen cycles each reopened with the body rendered and *Done* focused, and Escape returned focus to *Add source*.
- **Full Playwright run.** All 18 failures were Bots timeouts while the Mac slept, and they passed 131/131 on re-run. Every dialog-using spec passed.
- **Confidence.** The diagnosis came from reading the code (confidence `suspected`). The checks confirmed the behaviour in Chromium only.

(source: raw/2026-10-31-fix-dialog-reopen-race.md §Concept; §Test plan, Recorded results)

**Remaining limitations.**
- **Deployment.** Live since 2026-10-30: the production web build `de00a5f` (the learning loop, rolled out 2026-10-30) contains `0fa0019` by git ancestry. The fix's behaviour itself was not re-tested in production (source: raw/2026-10-30-learning-loop.md §Concept, Rollout to production).
- **An outside close before its event (existing gap, not a regression).** If something outside the component closes the element and `open()` runs before that `close` event arrives, `open()` is a no-op because `openState` is still true. The event then finishes the dialog normally. No caller does this.
- **Body reuse in the race window (not a regression).** When `close()` and `open()` run in one synchronous turn, Angular never renders the closed state, so the `@if (isOpen())` body view is reused rather than recreated. That bends "each opening starts fresh". In a browser the two key presses are separate tasks, and the zoneless scheduler usually renders between them. It has no visible effect today: the *Add source* body is static, and wrappers reset their state in `open()`. If it ever matters, the reviewers suggest keying the body on an opening counter (`@for (o of [opening()]; track o)`). The source tags this item MW-17 but also glosses MW-17 as the focus fallback in its cross-links [needs verification].
- **Spec nits not applied.** The regression test does not assert that focus returns to `trigger()` after the Escape close. The stub comment at `dialog.spec.ts:95-97` says "as a task", but the stub uses `queueMicrotask`.
- **No component-level copy** of the regression in `feat-signals/signals.spec.ts`. The shared component's test covers the contract.

(source: raw/2026-10-31-fix-dialog-reopen-race.md §Open questions)

## Learning loop (slice 8): the Learning section, the learned block and the Stats proposal flow (2026-10-30)

tidewatch-web PR #21 (head `568002f`, merge `de00a5f`, merged 2026-10-30 by Claude on the owner's instruction and deployed to production) added the learning loop's screens (see [[learning-loop]]). **D14: there is no mockup**, so the build used existing patterns only: no new token, colour, type step, icon or motion (PRD §7.2) (source: raw/2026-10-30-learning-loop.md §Components; §Concept, Owner decisions D14).

**The *Learning* section** (`feat-bots/bot-learning.ts`, selector `app-bot-learning`; every word in `feat-bots/util/learning-view.ts`).
- **Placement.** `bot-detail.ts:149` renders it between `app-bot-candidates` and `app-bot-version`, for auto bots only (none for Me), as a `.section` with its own `h2` "Learning".
- **The run row** is a `.loop-row`, reusing the Loops pattern: *Learning* · "Next run {EEE d MMM HH:mm}" (or "no schedule (paused)", "needs a v2 version"), and a second line "Last run {d MMM HH:mm} · {trigger} · {result}". *Run learning now* reuses the Loops' *Queued…*, the stale sentence and the 409 and 429 sentences.
- **Floors: one `.status-line` per job** (design SF-2 (a), the orchestrator's ruling that follows the PRD; `DESIGN.md` amended).
- **The draft.** A `.tag` "Draft from {d MMM}", then three tables in named `.table-scroll` regions inside `.learning-tables`:
  - *Proposed weights* (`source · current · proposed · likely range · n`), moved rows first and bold, with the existing tone classes on the change;
  - *Calibration* (`horizon · method · graded · raw ECE · calibrated ECE (out of sample)`);
  - *Failure model* (`fold · test rows · AUC`, then "mean out-of-sample AUC {x} · gate {open | closed}" and the importances as a `.second` list).
- **Actions** in `.learning-actions`: `.btn.primary` *Load into editor*, `.btn.ghost` *Dismiss draft* and the `.text-btn` *Download report*, a plain `<a download>` on the same origin.
- **Formats.** ECE and AUC show 3 digits on screen (the API sends 4), weights 2, dates in Bangkok. "AUC" and "ECE" are written out once in the section note.
- **Focus.** *Load into editor* moves focus to the editor heading; *Dismiss draft* toasts "Draft dismissed." and moves focus to the Learning heading.

(source: raw/2026-10-30-learning-loop.md §Components, The *Learning* section)

**LL-W decisions recorded in `DESIGN.md` (selected).**
- **LL-W-1.** A non-v2 version skips the learning read and shows the legacy sentence, with no button.
- **LL-W-21 (PF1).** With a pending draft whose gate is closed, the service sends `draft.diff.meta_gate: null`, so the *Failure model* table is drawn from `latest.summary.meta_model`, and "gate closed" stays readable (PRD §4.11.1). PV4 found the defect.
- **Undated dismissal (OQ-W2).** A dismissed draft reads "Dismissed", with no date, because M stores no dismissal time; a saved one reads "Saved as v{label} on {date}" from `saved_label` and `saved_at`.
- **XF-1.** The web's C15 features check walks per item, matching the service and the bot.

(source: raw/2026-10-30-learning-loop.md §Concept, Decisions during the build OQ-W2, XF-1; §Concept, Spec corrections, LL-W-1 and LL-W-21; §Components, Other states)

**The version editor and the clone dialog** (`feat-bots/bot-version.ts`, `bot-dialog.ts` and their utilities).
- **The learned block** shows as a `.status-line`: "Learned block from the run of {d MMM}: {n} calibration map(s) · failure model gate {open (AUC {x}) | none} · locked. A learning run proposes a new one." Beside it, a `.text-btn` *Remove the learned block* deletes the `learning` key (an undefined value is refused), which unlocks probation and enables *Save as vN*.
- **Probation.** With a learned block in the draft, *Start on probation (30 days)* is checked and disabled, with the title "A learned version always starts on probation." The clone dialog locks probation for a learned source (R12).
- **The serialiser** round-trips C15 to the same bytes and hash (`data/bot-config.model.ts`, which now imports `SIGNAL_EVENT_TYPES` from `./signals.model`).

(source: raw/2026-10-30-learning-loop.md §Components, The version editor and the clone dialog)

**Stats.**
- **The filter.** A native `button[aria-pressed]` `.chip`, *Proposed only*, in a group named "Filter the losing decisions"; an empty-under-filter sentence was added.
- **Proposal rows** show "Model: {rationale}" as a `.second` line inside **`<bdi>`** (web security N1: bidi characters in the model rationale). The button reads *Confirm* while the select equals the proposal and *Save* otherwise.
- **The counts line** keeps "waiting for you {n}" together with a non-breaking space.
- **The compare verdict** "Calibration not comparable yet (…)" with an `aria-disabled` *Promote to champion*, and "· learned version" in the sub line (`stats-view.ts:133`).
- **OD-PV2-1 (owner, 2026-10-29T01:58Z, "Fix with CSS").** In the unfiltered labelling list at 1100 and 1080, *Confirm* and *Save* were out of view (SF-PV2-1). Above 600px the losses table's Decision and Signal second lines and the saved tag may now wrap, a cell-wrap rule in `stats.css`.

(source: raw/2026-10-30-learning-loop.md §Components, Stats; §Concept, Decisions during the build OD-PV2-1; §Concept, Review history)

**Words elsewhere.** The Watch and Checks word `meta_veto` as "vetoed by the failure model" (`feat-bots/util/watch-view.ts:394`; see [[bot-watch-verdicts]]). The decision record's second line gains "size halved by the failure model" (`feat-trade/util/order-view.ts:377`). A learned strategy sentence gains "· learned" (`feat-bots/util/bot-view.ts:135`). The admin `AUDIT_TYPES` list reads `learning_draft_dismissed` as its 35th type, shown raw in the Audit *Type* filter (see [[operator-console]]) (source: raw/2026-10-30-learning-loop.md §Components, Words elsewhere and Data layer).

**Styles.**
- **`.learning-tables`** in `src/styles/components/bots.css`, scoped under `.bot-detail`: a column of three regions with a 12px gap, and a 560px table minimum **except `.failure-model`**.
- **OD-PV2-2 (owner, 2026-10-29T01:58Z, "Drop it for Failure model"). This amends PRD §7.4.** The 560px minimum applies to *Proposed weights* and *Calibration* only. The *Failure model* table has none and fits 358px at 390 (`bots.css:181-196`). It resolved SF-PV2-2 (the 560px minimum at 390).
- **`.learning-actions`**, also under `.bot-detail`: a wrapping flex row with a 10px gap.
- **`stats.css`** adds the chip wrap and the OD-PV2-1 cell wrap.

(source: raw/2026-10-30-learning-loop.md §Components, Styles; §Concept, Decisions during the build OD-PV2-2; §Concept, Spec corrections, OD-PV2-2)

**Verification.**
- **PV1** (`b84fd55`): 210 slice-8 captures with no overflow, axe 0 over 40 runs, contrast ≥ 4.79:1. Capture states include `bots__learning-{state}` (with `learned-realised` and `draft-gate-closed`), `bots__editor-learned`, `bots__editor-loaded-draft`, `bots__clone-learned` and six `stats__` states.
- **PV2 (rendered design review)** at `b84fd55`: CHANGES REQUESTED (SF-PV2-1 *Confirm* and *Save* out of view at 1100; SF-PV2-2 the *Failure model* minimum at 390; SF-PV2-3 the `DESIGN.md` refresh). PF1 `13d1267` fixed them with OD-PV2-1 and OD-PV2-2. **PV2 round 2 APPROVED** (0 blocking, 0 should-fix, 2 nits; `review/tidewatch-web/design-pv2-r2.md`).
- **PV3 and PV5:** keyboard, axe and contrast verified (slice-8 minimum 4.85); `forge-setup-impeccable --check` 173/173.
- **Not verified:** touch and real devices, screen readers, Safari and Firefox, widths 601–1079, *Confirm* by keyboard, and the "Remove → heading when unchanged" branch. FR-LL-WEB-007 is partial: no capture of the Checks' `meta_veto` words or a shrunk entry's second line. Playwright was not re-run on the merged head `568002f`.
- **e2e notes.** Playwright 1.63 does not route an `a[download]`, so the mock checks the link and the URL, and the real file was checked on the service (A5, byte-identical). The mocks of the §6.2 bodies fail closed.

(source: raw/2026-10-30-learning-loop.md §Components, e2e; §Concept, Review history, Preview design; §Test plan, Preview runs and Not verified or partial)

**`DESIGN.md`.** It gained "Learning (`.learning-tables`, `.learning-actions`)" at `:1972`, the "Learning loop (slice 8)" verification evidence at `:4726`, the LL-W decisions, OD-PV2-1 and OD-PV2-2, and a refreshed source snapshot (source: raw/2026-10-30-learning-loop.md §Components, `DESIGN.md`).

**The `Dialog` fix rides along.** The web PR merged `main` as `568002f` before it merged, bringing the favicon (#24) and the `app-dialog` reopen-race fix (#25, above), with no learning-loop change. So the production bundle rolled out from `de00a5f` contains #25. The source verifies that rollout by the learning routes in the live bundle, not by checking the dialog fix itself (source: raw/2026-10-30-learning-loop.md §Concept, Stage, Implemented; §Concept, Branch update onto L, Web again; §Concept, Rollout to production; §Files touched, tidewatch-web).

**Open web follow-ups.** F-PV1-4 (the Stats proposal-confirmed toast contrast test should measure the toast first or pin the clock); N-R2-2 (optional U+00A0 in "confirmed by you"); angular N1 (*Load into editor* silently no-ops while the editor is loading or failed), N2, N3; code N2 (the strategy reader refuses `learned: true` on a non-v2 config, stricter than the service) and N4; design advisories A-1, A-2 and A-6 (owner calls) and A-7 (source: raw/2026-10-30-learning-loop.md §Open questions, Recorded follow-ups, Web).

## Related pages

- [[foundation-auth]] — the slice that implemented this system
- [[auth-model]] — the server behaviour behind the account menu and sign-in states
- [[request-protection]] — web-side protections that share the shell (interceptor, `next` sanitising)
- [[market-data]] — slice 1, which added the Market watch card
- [[market-timeseries]] — the CDC zones the tide strip and zone label render
- [[simulation-engine]] — Slice 2, which added the Trade screen and portfolio hero
- [[zone-transition-bot]] — Slice 2b, which added the Bots screen
- [[decision-record]] — the decision record component now shared by Trade and Bots
- [[bot-activity]] — the Watch and Checks sections and the expandable row
- [[bot-watch-verdicts]] — the verdict copy the Watch and expanded checks render
- [[signals-ingest]] — slice 3a, which filled the Market watch Signals cell
- [[signal-message-contract]] — the live `signal` frame and the once-per-id count behind the cell
- [[signals-page]] — slice 4, which added the Signals screen and moved the expandable row to `table.css`
- [[signals-day-control]] — the *Day* `.chip-select` and the placement-only *Show yesterday* rule
- [[user-settings]] — the rail badge behind `.nav-count`
- [[signal-cited-orders]] — the Trade pre-fill hint and the *Quantity* layout change
- [[charting]] — slice 5, which added the Chart screen, the chart library and the 96-slot strip
- [[elliott-regime-labeller]] — the candidate counts the `--brand` Elliott primitive draws
- [[bots]] — slice 6, which added the Bots additions, the version editor, *Your strategies* and the Trade card
- [[statistics]] — slice 7, which added the Stats screen, the editor's net figure and the Trade follow-record sentence
- [[operator-console]] — the console screens styled by `console.css`
- [[accounts-and-roles]] — the feature that added the console, the four icons and the display-name account menu
- [[learning-loop]] — slice 8, which added the Learning section, the locked learned block and the Stats proposal flow
- [[signals-context]] — spec 3b, which added the discovery rows to the Schedule group
