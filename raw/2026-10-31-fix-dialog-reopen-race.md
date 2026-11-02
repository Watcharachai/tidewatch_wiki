# Fix: app-dialog empty modal on fast reopen (dialog-reopen-race)

> A standalone `/forge-fix` (run `fix-dialog-reopen-race-98309091`, console run `fix:dialog-reopen-race:20261030T121318`) in tidewatch-web only. Reopening an `app-dialog` straight after closing it could leave the page dimmed and blocked by an empty modal backdrop, with no panel and no buttons. The cause was a stale native `close` event: it arrived after the reopen and ended the new opening. One guard in `Dialog.onNativeClose()` now ignores that event, and a regression test reproduces the race. PR tidewatch-labs/tidewatch-web#25 (commit `6842b0a`, base `0462c4c`) was merged on the owner's instruction ("Merge #25") at 2026-10-30T17:29:38Z as merge commit `0fa0019`. The merge started the `deploy-prod` and `release-please` workflows (in progress when read once at about 17:30Z). Deployment was **not verified**. tidewatch-service, tidewatch-bot and tidewatch-migrations are unchanged.

**Sources:** `.forge/fixes/dialog-reopen-race/` (`state.json`, `diagnosis/brief.json`, `engineer-report.md`, `review/code-reviewer.md`, `review/security-reviewer.md`, `review/angular-reviewer.md`, `pr-body.md`, `evidence/`).

## Concept

**The bug.** The Playwright test "opens Add source and returns focus" (`e2e/src/signals.spec.ts`) presses Enter on *Done* to close the Add source dialog, then presses Enter on *Add source* straight away to reopen it. Under load, *Done* never appeared again. The test failed 2 of 3 attempts in the learning-loop PV6 preview run, and the PV6b baseline on the same unfixed dialog code passed 1 of 3, failing at `signals.spec.ts:1290` (`toBeFocused` on *Done*, element not found). On screen the page was dimmed by the blurred `::backdrop` with no panel, because the empty `.dialog-panel` is `display:none` (`src/styles/components/dialog.css`).

**Root cause.** `close()` (`src/app/shared/ui-dialog/dialog.ts`) calls the native `HTMLDialogElement.close()`, then calls `finish()` itself. The native call removes `open` immediately but fires the `close` event later, asynchronously. If `open()` ran before that event arrived, `showModal()` reopened the element and `openState` went back to true. The late event then reached `onNativeClose()`. That method checked only `openState()`, so it ran `finish()` a second time, which:

- set `openState` false and removed the `@if (isOpen())` body;
- took the Escape capture listener off (MW-16);
- sent focus to a trigger made inert by the modal;
- emitted `closed` again.

All of this happened while the `<dialog>` stayed open and modal. The extra `closed` also landed in the new opening, so callers that reset state on `(closed)` reset it mid-opening:

- *Add instrument* cleared its query.
- *Add person* and *Reset password* cleared the temporary-password secret and set busy to false.
- Operators dropped the new opening's results as stale.

**The fix.** `onNativeClose()` now finishes only when the element is really closed:

```ts
protected onNativeClose(): void {
    if (this.openState() && !this.dialog().nativeElement.open) {   // was: if (this.openState())
        this.finish();
    }
}
```

**Why the guard is safe.** In the HTML "close the dialog" steps, the browser removes `open` (and leaves the top layer) before it fires `close`. So:

- A genuine outside close (`form method=dialog`, `requestClose`, a foreign `.close()`) still has `open` gone when its event arrives, and it still finishes once.
- A stale event arriving after a reopen sees `open` set and is ignored.

The guard adds no state, reads the DOM as `close()` already does, and handles several queued events: no sequence emits `closed` twice for one opening. The guard evaluates `openState()` first, so a late event never reads the `viewChild`. `close()`, the Escape and `cancel` paths, the template and the public API (`open`, `close`, `isOpen`, `closed`) are unchanged. The diagnosis rejected two alternatives:

- An opening or pending-close counter. It adds state, and the count can drift if an event is never delivered.
- Letting only the native event call `finish()`. That makes closing asynchronous and changes when `closed` fires.

**What callers can rely on now.**

- Exactly one `closed` per opening.
- A fast close-then-reopen keeps its body rendered, its Escape listener and its focus on the first field.
- Escape then closes the dialog once and returns focus to the trigger.

The diagnosis was made by reading the code (confidence `suspected`). The e2e and manual checks below confirmed the behaviour in Chromium.

## Database

_n/a_

## API

_n/a_ (frontend-only, no request or contract change).

## Components

- **`Dialog` (`app-dialog`, `src/app/shared/ui-dialog/dialog.ts`).** Only the `onNativeClose()` guard (line 193) and its doc comment (lines 186-191) changed. The comment says the event can arrive after a fast reopen ("Done, then Add source"), must not end that opening, and that only a closed element finishes.
- **Callers, all unchanged:**
  - `feat-signals/signals.ts` (Add source)
  - `feat-overview/add-instrument-dialog.ts` and `edit-list-dialog.ts`
  - `feat-bots/bot-dialog.ts`
  - `admin/feat-people/` (`add-person-dialog.ts`, `reset-password-dialog.ts`, `disable-person-dialog.ts`, `edit-person-dialog.ts`)
  - `admin/feat-operators/operators.ts`

  All of them open through `open()` and close through `close()`. None uses `method=dialog`, `requestClose()` or direct native calls, so `dialog.ts` is the only code that calls `showModal()` or `close()`.

## Files touched

**tidewatch-web** (2 modified, +30/-2)

- `src/app/shared/ui-dialog/dialog.ts` (modified, +7/-2)
- `src/app/shared/ui-dialog/dialog.spec.ts` (modified, +23)

## Test plan

**Regression test.** It is in `src/app/shared/ui-dialog/dialog.spec.ts`, under "closing", lines 396-417: "ignores the native close event of an earlier close() once it has opened again".

1. Run `await open()`, then `close()` and `open(trigger(), fallback())` with no await between them, then `await settle()`.
2. Expect the element to be `open`, `isOpen()` true, the `h2` and `.cancel` rendered, focus on `.first`, and `closes === 1`.
3. Press Escape on `.first`. Expect the dialog closed and `closes === 2`.

jsdom has no `showModal()` or `close()`, so the spec's `beforeEach` stubs them like a browser: `close()` removes `open`, returns focus, and dispatches `close` via `queueMicrotask` (Chromium uses a task; both are asynchronous). The existing outside-close test (lines 365-375) removes `open` before dispatching and still passes.

```sh
pnpm nx test tidewatch-web --include=src/app/shared/ui-dialog
pnpm nx test tidewatch-web && pnpm nx lint tidewatch-web && pnpm nx build tidewatch-web
pnpm exec prettier --check src/app/shared/ui-dialog/dialog.ts src/app/shared/ui-dialog/dialog.spec.ts
# on a preview, with the usual e2e env (BASE_URL, E2E_OPERATOR_PASSWORD, E2E_OTP_DEV_CODE; values never written down)
playwright test -c e2e/playwright.config.mts --grep-invert @hook --grep "opens Add source and returns focus" --repeat-each=5
```

**Manual check.** Open Signals, then *Add source*. Press Enter on *Done* and then Enter again at once. The dialog must come back with its text and *Done* focused. Escape must close it and return focus to *Add source*. The race depends on timing, and CPU throttling makes it more likely.

**Recorded results (2026-10-30).**

| Check | Result |
|---|---|
| Dialog unit spec, before fix | 1 failed / 34 passed: the new test failed at `isOpen()` (line 405) right after `dialogEl().open === true` passed, which is the stuck-modal state |
| Dialog unit spec, after fix | 35/35 |
| Full unit suite | 176 files, 6489 tests passed |
| Lint, build, Prettier on the two files | clean |
| Reviews (fingerprint `300415d9`) | code-reviewer, security-reviewer and angular-reviewer all APPROVED with nits only and 0 fix loops. The security review found no genuine close path that now skips `finish()`, and no retained temporary password |
| CI on `6842b0a` | 1 check passing (validate SUCCESS) at merge |
| Signals e2e on a preview (web `6842b0a`; service `35177e1`, bot `bd5e435`, migrations `080979d` on main) | 5/5 with `--repeat-each=5` (requested); 20/20 with `--repeat-each=20` |
| Manual, in the browser pane on the owner's signed-in preview session | 11 fast-reopen cycles (1, then 10): each time the dialog was open, the body rendered and *Done* focused; Escape closed it and returned focus to *Add source*; no writes |
| Full Playwright suite, one worker, `--grep-invert @hook` | 1922 passed, 4 skipped, 18 failed. All 18 were Bots timeouts while the Mac was asleep with the lid closed (the `pmset` log confirms; wall times of 7-17 min against a 60 s timeout). Re-running the 8 affected locations with the Mac awake gave 131/131 (1.8 min). Every dialog-using spec passed |

## Open questions

- **Deployment not verified.** The merge started `deploy-prod`, but nobody checked that the fix is live on tidewatchtrade.com.
- **Existing gap, not a regression.** If something outside the component closes the element and `open()` runs before that `close` event arrives, `open()` is a no-op because `openState` is still true. The event then finishes the dialog normally. No caller does this.
- **Body reuse in the race window (MW-17), not a regression.** When `close()` and `open()` run in one synchronous turn (as in the test), Angular never renders the closed state, so the `@if (isOpen())` body view is reused rather than recreated. That bends "each opening starts fresh". In a browser, two key presses are separate tasks and the zoneless scheduler usually renders between them. This has no visible effect today: the Add source body is static, and wrappers reset their state in `open()`. The reviewers suggested keying the body on an opening counter (e.g. `@for (o of [opening()]; track o)`) if it ever matters.
- **Spec nits not applied.**
  1. The regression test could also assert that focus returns to `trigger()` after the Escape close.
  2. The existing stub comment at `dialog.spec.ts:95-97` says the `close` event fires "as a task", but the stub uses `queueMicrotask`.
- **Optional test not added.** The diagnosis suggested a component-level copy of the regression in `feat-signals/signals.spec.ts` (click Done, then Add source, with no settle between). It was not added; the shared component's test covers the contract.

## Cross-cutting links

- [[design-system-decisions]]: dialog conventions (bodies render only while open, MW-16 Escape capture, MW-17 focus fallback)
- [[signals-page]]: the Add source dialog and the `signals.spec.ts` e2e that exposed the race
- [[operator-console]]: the temporary-password dialogs that clear their secret on `(closed)`
- [[forge-preview-gateway]]: the preview the browser checks ran on
