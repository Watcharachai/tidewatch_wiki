# Signal-cited orders: the recommendation, the Trade pre-fill and `decision_ctx`

**Summary**: Since slice 4 (the signals page, merged 2026-10-12), a user can act on a signal and leave a trace in the decision record. The Signals detail offers *Buy with recommendation* or *Sell with recommendation*, sized at 10% of equity, which is Slack Water's rule (owner decision D2). The link opens `/trade` pre-filled with the instrument, the side, the quantity and a Market order type. The order then carries a `decision_ctx` that cites exactly one signal. The service checks the citation inside `check()` and refuses a mismatch with `422 signal_not_applicable`. The decision row it writes fills `signal_ids`, `followed_recommendation`, `signal_snapshot` and `model`, the first writes of these columns. **No signal-cited order has been placed on any stack yet.** FR-SP-E2E-004 was unverified at merge, because no signal on the preview had a usable price. Since charting (slice 5; tidewatch-web #14, merged 2026-10-16 as `918d7b6`, not deployed), Trade also accepts a **two-key pre-fill**, `/trade?instrument=&side=`, which the Chart's *Buy* and *Sell* links use. It sets only the instrument and side, keeps the order type and quantity, and carries no signal context. The four-key form is unchanged. **Since slice 6 (bots; tidewatch-service #12 and tidewatch-web #15, merged 2026-10-21, not deployed),** Trade's recommendation card shows the followed bot's candidate instead of "Arrives with bots". *Use this order* opens a **third pre-fill form**, `/trade?instrument=&side=buy&qty=&candidate=`, and the order's `decision_ctx` cites the candidate (`candidate_id`), checked by the service with `422 candidate_not_applicable`. *Not this time* writes a skip citing the candidate. FR-BT-E2E-008 passed on the preview: the first candidate-cited `me` order and skip.

**Sources**: `raw/2026-10-12-signals-page.md`; `raw/2026-10-14-signals-day-control.md` (the actions on past days); `raw/2026-10-16-charting.md` (the two-key pre-fill and *Open chart*); `raw/2026-10-21-bots.md` (the recommendation card, the candidate pre-fill and candidate citations); `raw/2026-10-27-statistics.md` (`follow_record` and the champion only)

**Last updated**: 2026-10-27

---

## Why 10% of equity (D2)

*Buy with recommendation* pre-fills the instrument, the side and 10% of equity, and the label says this is Slack Water's rule (see [[zone-transition-bot]], ZB4). The number is a convention, not a forecast. The decision records the signal id, `followed_recommendation = true` and a snapshot holding the suggested quantity and the rule (`equity_pct_10`) (source: raw/2026-10-12-signals-page.md §Concept, Chosen design D2).

## The recommendation (service)

`GET /signals/{signal_id}` answers `recommendation: {side, qty_suggested, rule: "equity_pct_10", equity_pct: "0.10", equity, price, priced_at} | null`.

- **Sizing.** `qty_suggested = floor_to_lot(0.10 × equity_thb ÷ unit_value_thb)`.
- **Unit value (R7/R8).** `px:last` × the estimate's USD/THB rate (for USD-quoted spot) × the contract multiplier (for futures). `px:last` counts only when it is valid v1, not stale, and at most 120 s old (see [[redis-market-contract]]).
- **Null, never an error.** The recommendation is `null` for a neutral signal, a quantity that floors to zero, a missing rate or venue rule, an inactive instrument, or a user without a manual bot. The detail never creates a bot or an account.
- **Equity.** The recommendation reuses `GET /trade`'s valuation of the manual bot's paper account (A1 held in planning). `trade.go` changed only to share that valuation through `nowMarks`. `internal/trading/rules.go` gained `FloorQty`.
- **One price read.** Since review-fix r1, the detail reads `px:last` once and passes it to the recommender, so the context and the recommendation share one instant (`TestService_Detail_OnePxLastRead`).

(source: raw/2026-10-12-signals-page.md §API, `SignalDetail`; §Concept, Plan resolutions, Service R7/R8; §Test plan, Assumption outcomes A1; §Files touched, tidewatch-service)

## The hand-off from the Signals detail

The expanded row's actions (see [[signals-page]]):
- For an **up** signal, *Buy with recommendation*; for a **down** signal, *Sell with recommendation*. Each is an `a.btn.primary` with `routerLink`, because it navigates (SP-W-11). It links to `/trade?instrument=&side=&qty=&signal=`, with the hint "{qty} {symbol} · sized at 10% of equity, like Slack Water".
- For a **neutral** signal: "No directional call, so no trade is suggested."
- With **no recommendation**: "No price to size from right now." and no primary button.
- *Open chart* and *Source document* are always offered. Until slice 5, *Open chart* led to the Chart placeholder; since charting (merged 2026-10-16, not deployed) it opens the real chart for the signal's instrument (see [[charting]]).

(source: raw/2026-10-12-signals-page.md §Components, Expanded row, Actions; §Concept, Plan resolutions, Web SP-W-11; raw/2026-10-16-charting.md, summary block)

**On past days (signals day control, merged 2026-10-14, not deployed).** The owner kept *Buy / Sell with recommendation* on past days, unchanged (DC3). The rejected options were Yesterday only, or hiding it on past days. `signal-detail.ts` and Trade were not edited. The mocked Playwright test "shows the recommendation actions on a past day row" covers it (see [[signals-day-control]]) (source: raw/2026-10-14-signals-day-control.md §Concept, Owner decisions DC3; §Files touched, Not changed; §Test plan, Playwright).

## The Trade pre-fill (web)

- **Reading the query.** `feat-trade/util/signal-prefill.ts` parses `/trade?instrument=&side=&qty=&signal=` once, after the first successful `/trade` load. Whenever any of the four keys is present, the query is removed with `replaceUrl`.
- **A valid pre-fill** needs a tradable instrument, `buy` or `sell`, a decimal within `qty_decimals`, and a UUID. It then:
  - sets the instrument, the side and the quantity, using an exact BigInt floor to lot and decimals (a zero result is ignored);
  - sets the order type to **Market** (ORCH-15; before that it stayed Limit with an empty price);
  - shows the hint "Sized at 10% of equity, like Slack Water · from a signal" under *Quantity*;
  - keeps `signalContext = {signal_id, side, qty_suggested, rule: "equity_pct_10"}` in `TradeService`.
- **An instrument that is not on the watchlist (ORCH-14).** A well-formed query for such an instrument holds no context. It leaves only a polite hint: "{symbol} isn't on your watchlist, so this ticket can't trade it. Add it on Market watch." Choosing an instrument dismisses the hint. That was an engineer's call in fix-r3, which the owner may overrule.
- **Context lifecycle.**
  - The context is dropped when another instrument is chosen.
  - It is dropped after a definite answer: a 2xx, or any 4xx including `signal_not_applicable`.
  - It is kept after a 5xx or a network failure, so a retry re-sends a byte-identical body under the same `client_order_id` (ORCH-10). This departs from PRD §4.6's "whatever the outcome code".
  - Flipping the side keeps citing the signal with `followed_recommendation: false`, and flipping back restores `true` (ORCH-11). A quantity edit keeps `true`.
  - The attempt fingerprint includes the signal id and the followed flag, so a changed body never reuses a `client_order_id`.
- **Request and copy.** `PlaceOrderRequest` gains an optional `decision_ctx`; the estimate never carries it. `refusal-message.ts` adds "This signal no longer applies to the chosen instrument." for `signal_not_applicable`.
- **Layout (ORCH-18).** *Quantity* spans the row when *Limit price* is hidden, for market and manual-fill orders.

(source: raw/2026-10-12-signals-page.md §Components, Trade pre-fill and signal context; §Concept, ORCH-10, ORCH-11, ORCH-14, ORCH-15, ORCH-18)

**The two-key form (charting, slice 5; CH-W-12, PD10).** The Chart's header carries *Buy* (`a.btn.primary`) and *Sell* (`a.btn`) links to `/trade?instrument=&side=` (see [[charting]]). Before slice 5 the pre-fill needed all four keys.
- **Parsing.** `readSignalPrefill` accepts a second form: `instrument` and `side` alone, each exactly once.
- **Effect.** After the first successful `/trade` load, the ticket takes the instrument and side and **keeps its order type and quantity**. It holds no signal context and shows no signal hint. A different instrument clears the limit and fill prices; a manual-fill venue stays on market.
- **Untradable instrument.** A well-formed query for an instrument that `GET /trade` cannot trade shows the existing "isn't on your watchlist" hint (ORCH-14).
- **Mixed keys.** With `qty` or `signal` present, the query is the four-key form or nothing.
- **Cleanup.** The query is removed with `replaceUrl` whenever any key was present.
- **Unchanged.** The four-key form, which still sets a Market order and the signal context.
- **Code.** `feat-trade/util/signal-prefill.ts`, `trade.ts`, `trade.service.ts` and `order-ticket.ts` changed, each with its spec. The mocked `e2e/src/trade.spec.ts` covers the two-key form. Reverting the web PR returns Trade to the four-key form only.

(source: raw/2026-10-16-charting.md §Components, Trade pre-fill and The Chart screen; §Concept, Accepted defaults PD10 and Operations; §Files touched, tidewatch-web S8 and S10)

## `decision_ctx` on the order path (FR-SP-SVC-007)

```json
"decision_ctx": {"signal_ids": ["0199d1a2-7b10-7c3e-9a51-3f0c2e8b4d17"], "followed_recommendation": true}
```

**`checkDecisionCtx` accepts:**
- an absent or `null` context;
- the slice-2 form: `signal_ids` absent or `[]`, and the other two keys absent or null;
- exactly one hyphenated UUID, with `followed_recommendation` `true`, `false`, `null` or absent, and `candidate_id` absent or null.

**It refuses with `400 {field: decision_ctx, reason: invalid}`:**
- `signal_ids` that is null, not an array, holds two or more ids, or holds a non-UUID;
- a followed flag without exactly one id (R11);
- a non-null `candidate_id`.

*(Slice 4 rules. Since slice 6, `decision_ctx.candidate_id` is accepted on `POST /orders` and `POST /orders/estimate`, with `signal_ids` either `[]` or the candidate's ids as a set; see "Candidate citations" below.)*

Any other key is `unknown_field`.

**`checkSignal` (R12).** It runs inside `check()` right after the instrument checks (`404 unknown_instrument`, `422 instrument_inactive`, `422 instrument_not_tradable`). It comes before lot and tick, hours, side, money and any write, so placement and the estimate refuse identically (see [[paper-trading]] for the full intake order).
- If no such signal exists, the answer is `422 signal_not_applicable` with `details {"reason": "unknown"}`.
- If `signals.instrument_id` differs from the body's instrument, the reason is `instrument_mismatch`, with the message "The signal this order cites names another instrument."
- A refusal is counted in `orders_placed_total{result="rejected"}` and logged `order_rejected`.

**The new error code.** `signal_not_applicable` is 422, with `details.reason` `unknown` or `instrument_mismatch` and no `field`. It is appended last in `AllCodes` and in the README error table, which `TestCodes_Contract` reads.

(source: raw/2026-10-12-signals-page.md §API, Order path; §API, New error code; §Concept, Plan resolutions, Service R11/R12)

## What the decision row records

The decision row is written in the order's own transaction (see [[decision-record]]):
- `signal_ids = ARRAY[signal_id]`, in lower case.
- `followed_recommendation`, as sent.
- `signal_snapshot = {signal_id, document_id, source_code, tier, event_type, direction, p, p_up, p_down, p_neutral, impact, severity, horizon, created_at, recommendation}`. The recommendation is derived **at order time** from the same equity, price and rate that the order's checks used. It is `null` for a neutral signal, or when it cannot be sized (for example, with a stale `px:last`).
- `model = {tier: "system1", model_id: <scoring_model_id>, direction, p, prompt_version, extraction_model_id, rationale}`.

**Unchanged.**
- Without a cited signal, all four columns stay NULL, as before.
- Success bodies are unchanged.
- An idempotent replay answers the stored order, whatever `decision_ctx` says.
- `POST /decisions/skip` is unchanged.
- The estimate never writes.

(source: raw/2026-10-12-signals-page.md §API, Order path, Decision row written and Unchanged)

## How it reads back

- **Signals page, Bots column.** A user's citing decision reads "You bought 16.2" over "followed · HH:mm". It is **not** counted in "acted on by bots", which counts bot-actor decisions only (owner decision D1). The export's `bots` cell reads "You bought 16.2 (followed); Slack Water bought 16.2" (see [[signals-read-api]]).
- **Trade, Decision record.** This view already read "1 signal" and the followed flag, and it is unchanged.

(source: raw/2026-10-12-signals-page.md §Concept, Chosen design D1; §API, Export; §Components, Trade pre-fill, Unchanged)

## Compatibility

A new web against an old service still fills the ticket, but the old service refuses the placement as an invalid `decision_ctx`. An old web against the new service is unchanged (source: raw/2026-10-12-signals-page.md §API, Configuration and compatibility).

## Verification

- **Service.** `TestOrders_SignalDecisionCtx_WritesSnapshot` checks the exact JSON against hand-computed figures. `TestOrders_SignalNotApplicable_NothingWritten` checks that a refusal writes nothing.
- **Web.** The mocked e2e covers the trade hand-off, and Trade's spec passed 97/97 on the preview. FR-SP-WEB-005 is mocked only; its live half is E2E-004.
- **FR-SP-E2E-004 is unverified.** Both of the day's signals on the preview (AAPL, NVDA) had a stale `px:last`, because the US market was closed. So `recommendation` was `null`, and no primary button showed. No order or decision was created. The script `evidence/preview/P3/E2E-004/e2e-004.cjs` (`MODE=place`) is ready to run once a signal with a usable price exists. Step 4 of the manual reproduction on [[signals-page]] describes the check.

(source: raw/2026-10-12-signals-page.md §Test plan, Named acceptance tests and Acceptance status)

## Slice 6: the bot recommendation and candidate citations (2026-10-21)

Slice 6 (see [[bots]]) gives `me` recommendations from a bot the user follows (owner decisions D1, PD10). Merged 2026-10-21 (service `9f1f324`, web `acbd75d`); not deployed.

### Which bot, which candidate (S14, S21, ORCH-5c)

- **The follow setting.** `PUT /me/settings/recommendations.follow` checks the shape only: `{"mode": "champion"}` (the default) or `{"mode": "bot", "bot_id": "<uuid>"}`. Ownership is resolved at read time (see [[user-settings]]).
- **Resolution.** `bot` → that bot when it is the user's auto bot. Otherwise the champion rule: the user's `champion = true` auto bot, else the oldest `running` or `observing` auto bot whose current version is v2 with a scout, else none.
- **`GET /recommendation`** answers `{generated_at, follows, candidate, sized, reasons, declined, invalidated}` and creates no bot or account.
  - **The candidate shown:** the followed bot's newest `watching` candidate, then the newest `proposed`, long, not declined.
  - **`sized` (S21):** the followed bot's policy applied to `me`'s equity, floored to the lot; `null` with no usable price.
  - **`reasons`:** four strings (the thesis, the strongest signal, the CDC zone and age, the Elliott or regime line).
  - **`declined`:** true when no candidate is shown and the followed bot has a live candidate the user declined.
  - **`invalidated`:** set for 10 minutes after an invalidation expiry.

(source: raw/2026-10-21-bots.md §API, Behaviour worth knowing, Recommendation and follow; §Concept, Owner decisions D1)

### The Trade card (`feat-trade/recommendation-card.ts`)

- It keeps the `section.reco` place and styles. Head: "{Bot} suggests", with a `label.chip.chip-select` *Follows* listing the user's auto bots plus "Champion (auto)". A change writes the setting. Only the champion or one of the answer's `options` can be written (security L2).
- Body: "p {p} · impact {impact}" (a null `p` reads "p —"); "{symbol}, up to {pct} % of equity ({qty} {unit})"; four reasons; *Use this order* (`a.btn.primary`); *Not this time* (busy *Declining…*, toast "Declined. Recorded as a skip."). The decline reloads Trade's decision record (GAP-W4).
- States: no followed bot; no candidate ("{Bot} has no candidate right now. Its next wake is {EEE HH:mm}."); unsized ("No price to size from right now."); invalidated ("The last candidate was invalidated at {price}."); error with *Try again*.
- `RecommendationService` reads `GET /recommendation` every 10 s and after a follow write or a decline.

(source: raw/2026-10-21-bots.md §Components, Trade: the recommendation card; §Components, Data layer)

### The third pre-fill form (BT-W-16/17)

- `/trade?instrument=&side=buy&qty=&candidate=` sits beside the four-key signal form and the two-key Chart form, in `feat-trade/util/signal-prefill.ts`.
- The ticket holds `{candidate_id, signal_ids, followed_recommendation}`. The signal ids, the hint ("{qty} {symbol} · {Bot}'s candidate, sized by its policy") and `followed_recommendation: true` apply **only when the link matches the loaded candidate's id, instrument and `sized.qty`** (security L1). Otherwise the ticket carries `[]`, no hint and `false`.
- A 422 `candidate_not_applicable` reads the signal form's sentence. The estimate never carries the candidate.

(source: raw/2026-10-21-bots.md §Components, Trade, Third pre-fill form)

### Candidate citations on the service

- **Where.** `check()` reads a cited candidate right after the instrument check and before everything else, for placement, estimate and skip alike (see [[paper-trading]]).
- **Refusal.** `422 candidate_not_applicable {reason: unknown | instrument_mismatch | closed}`; nothing is written. `signal_ids` must be `[]` or the candidate's ids as a set.
- **On an order:** the decision records `candidate_id`, `followed_recommendation`, and the proposing decision's `signal_snapshot`/`model`. `candidates.followed_order_id` is set as the transaction's last write, when still null.
- **On a skip** (`POST /decisions/skip` with `candidate_id`): `loop user`, the candidate's `signal_ids`, `followed_recommendation false`. `candidates.declined_at` is set once, plus audit `recommendation_declined {decision_id, candidate_id}`. Neither action changes the candidate's `state` (see [[bots-engine]]).
- **Not compared:** the skip's direction against the candidate's (**FU-2**; it needs a contract refusal reason).
- Named tests: `TestRecommendation_Follow`, `TestRecommendation_NoCreate`, `TestOrders_CandidateCtx`, `TestSkip_Candidate`.

(source: raw/2026-10-21-bots.md §API, Behaviour worth knowing, Candidate citation; §API, Codes; §Test plan, Named acceptance tests; §Open questions, FU-2)

### On the preview (FR-BT-E2E-008, passed)

The follow was set to the probation bot C. The card showed C's watching BTC candidate: p 0.70, impact 0.50, "up to 1.31% of equity (0.00472 units)" and four reasons. *Use this order* opened Trade pre-filled, and the placed `me` buy (0.00472, pending at capture) has a decision citing the candidate, with `followed_recommendation` true and 1 signal. *Not this time* wrote a skip with `loop user` and the `candidate_id`, set `declined_at`, and the card read "Nothing else right now.". These rows remain on the shared preview database (source: raw/2026-10-21-bots.md §Test plan, The E2E checks and Preview database footprint).

## Slice 7: `follow_record` and a real champion (2026-10-27)

Slice 7 (see [[statistics]]; tidewatch-service #15 `f289b9f`, tidewatch-web #20 `74918fd`, merged and deployed to production on 2026-10-27) grades `followed_recommendation` for the first time and gives the champion rule a champion to find.

- **`follow_record` on `GET /recommendation` (S5, D11).** It is the answer's **last** key on every shape, the "no recommendation" shape included, rather than a sixth Stats route. Rows: the `me` bot's `buy|sell|add|trim|close` decisions with `ts ≥ now − 30 × 24 h` and `r_5d` not null, with no `actor` filter. `followed` is `followed_recommendation IS TRUE`; `own` is `IS NOT TRUE`. Each side has `n_graded` (always the count) and `avg_r_5d` (the gross mean, 6 digits, `null` under 5 graded). With no manual bot both sides are `{0, null}`. There is no counterfactual. Details on [[stats-read-api]].
- **The Trade sentence (FR-ST-WEB-011).** Under the recommendation card, `p.reco-record` reads "Over 30 days, decisions that followed a recommendation averaged {a}% after 5 days; your own ideas averaged {b}% ({n_f} and {n_o} graded)." When either average is null: "Not enough graded decisions yet to compare followed recommendations with your own ideas ({n_f} and {n_o} so far)." It is not a live region and carries no tone class. `parseRecommendation` now requires `follow_record`.
- **The champion rule can now find a champion.** Before slice 7 `bots.champion` was never set, so `{"mode": "champion"}` always fell back to the oldest auto bot with a scout. `POST /bots/{bot_id}/promote` now sets the flag (see [[bot-versions-and-runs]]). On the preview, `GET /recommendation` followed the newly promoted challenger (FR-ST-E2E-002). No production champion has been made yet.

(source: raw/2026-10-27-statistics.md, summary block; §Concept, Owner decisions D11 and Spec decisions S5; §Concept, How each figure is computed, `follow_record`; §Components, Data layer and Trade; §Test plan, The E2E checks)

## Follow-ups

- **Security L1.** The pre-fill hint shows for any URL `qty`. Optionally, show it only when the quantity and side match the recommendation from `GET /signals/{id}`.
- **Angular review #2.** The action hint hard-codes "sized at 10% of equity" whatever `recommendation.rule` says.
- **Security L2.** The shared strict body decoder accepts case-insensitive and repeated keys, on `POST /orders` too.
- The detail route's `uuid.Parse` accepts braced, URN and unhyphenated ids, while the order path accepts only hyphenated ones.
- `trading.Recommend` has no production caller after the review fix.
- The ORCH-14 dismissal call (the watchlist hint is dismissed when an instrument is chosen) stands unless the owner overrules it.

(source: raw/2026-10-12-signals-page.md §Open questions, Service and Web follow-ups)

## Related pages

- [[signals-page]]: the slice-4 overview, the Signals detail and the manual reproduction
- [[signals-day-control]]: the *Day* select, which keeps these actions on past days (DC3)
- [[decision-record]]: the four signal columns, now written for the first time
- [[paper-trading]]: the intake order that `checkSignal` joins, and the `me` bot's account
- [[signals-read-api]]: the detail route that answers the recommendation, and the Bots column
- [[zone-transition-bot]]: Slack Water's 10%-of-equity sizing rule (ZB4)
- [[redis-market-contract]]: the `px:last` usability rule the recommendation needs
- [[signals-pipeline]]: the scoring and extraction fields copied into `signal_snapshot` and `model`
- [[charting]]: slice 5, whose *Buy* and *Sell* links use the two-key pre-fill, and the chart *Open chart* now opens
- [[bots]]: slice 6, which added the bot recommendation card and the candidate pre-fill
- [[bots-engine]]: the candidates the card shows and their lifecycle
- [[user-settings]]: the `recommendations.follow` key behind *Follows*
- [[statistics]]: slice 7, which adds `follow_record` and the Trade follow-record sentence
- [[stats-read-api]]: the `follow_record` definition and the promote route
