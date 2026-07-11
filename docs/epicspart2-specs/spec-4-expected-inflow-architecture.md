# Spec 4: Expected Inflow Architecture

Source epic: Epic 4 Expected Inflow Architecture

Source decisions: ADR 0012, ADR 0013, ADR 0014

## Problem Statement

Sarflog already has the beginnings of an Expected Inflow engine, but it is not yet the final accounting-grade architecture described by Epic 4.

Users need to track money they expect to receive: salaries, client invoices, refunds, asset-sale proceeds, and debts being repaid. The current model has useful pieces, including Promise records, Schedule records, realization records, allocation records, and write-off records. But the current behavior still mixes stored lifecycle labels, monthly cashflow filtering, payment actions, manual reopen/delete paths, and partial ledger reversal behavior in ways that can confuse users and weaken auditability.

The product problem is simple: users need to know both "what money am I owed overall?" and "what money should arrive this month?" without those two questions fighting each other.

The architecture problem is sharper:

- A high-level agreement should not be filtered and acted on as if it were one due-date row.
- A due-date chunk should be rescheduled, received, written off, or reversed without rewriting the agreement.
- Promise-level state should not store derived labels that can go stale or misclassify mixed outcomes.
- Over-receiving should not silently inflate a contract beyond 100 percent.
- Financial reversals should preserve the original fact and append compensating history.
- Reschedule reversal must protect the schedule tree once child schedules have real activity.
- The UI should guide the user through agreements, cashflow, and schedule actions without exposing raw database mechanics.

If this epic is not completed, Expected Inflows will remain a partly modernized feature: useful for simple cases, but risky for long-lived contracts, disputed payments, delayed client work, debt repayment tracking, and future audit/reporting features.

## Solution

Build the complete Expected Inflow architecture from ADR 0012, ADR 0013, and ADR 0014.

From the user's perspective, Sarflog should behave like a clear incoming-money cockpit:

- The Agreements view shows what people, clients, institutions, or sources are expected to pay overall.
- The Cashflow view shows which exact chunks are due in the selected month.
- The details drawer explains the story of one agreement without dumping raw tables.
- Action buttons appear next to the specific schedule chunk they affect.
- The progress bar never exceeds 100 percent.
- A partly received and partly written-off agreement is shown as settled, not wrongly branded as fully written off.
- If extra money arrives beyond the agreement, Sarflog asks the user to record the excess as separate income.
- If a receipt or write-off was recorded by mistake, the user can reverse it while preserving history.
- If a payment was rescheduled and the replacement schedules are still untouched, the user can reverse the reschedule.
- Once replacement schedules have receipts, write-offs, or further reschedules, the tree is protected from unsafe reversal.

From the engineering perspective, the solution is a cleanup and hardening pass over the existing two-layer foundation:

- Promise remains the Agreement layer.
- Schedule remains the Delivery/Cashflow layer.
- Promise persistence stores only open or closed lifecycle intent.
- Promise display state is derived from immutable realization and write-off facts.
- Schedule state remains detailed because it records what happened to a specific due-date chunk.
- Rescheduling operates only on schedules by superseding one schedule and creating child schedules.
- Financial actions create append-only or compensating history.
- Structural actions preserve schedule tree integrity.
- The frontend follows the same mental split as the data model.

The highest-level testing seam should be Expected Inflow API behavior, with service-level tests for dense derived-state math and reschedule tree traversal, and focused frontend tests for the two-tab model, tri-color progress bar, schedule-card actions, and timeline rendering.

## User Stories

1. As a user, I want to see all expected inflow agreements in one place, so that I know who or what is expected to pay me.
2. As a user, I want agreements to be separate from monthly cashflow, so that a yearly salary does not look like one monthly paycheck.
3. As a user, I want each agreement to show original amount, received amount, written-off amount, and outstanding amount, so that I understand where it stands.
4. As a user, I want a progress bar that separates received, written-off, and outstanding money, so that contract completion is visually obvious.
5. As a user, I want the progress bar to stop at 100 percent, so that overpayment does not make the agreement look mathematically broken.
6. As a user, I want partly received and partly written-off agreements to be described honestly, so that settlement does not look like total loss.
7. As a user, I want fully received agreements to close automatically, so that I do not have to manually mark them done.
8. As a user, I want fully written-off agreements to close automatically, so that lost money stops showing as active cashflow.
9. As a user, I want mixed received/write-off agreements to close automatically when nothing is outstanding, so that settled contracts no longer demand action.
10. As a user, I want an agreement to reopen automatically if a receipt or write-off is reversed, so that the outstanding amount becomes actionable again.
11. As a user, I do not want manual close and reopen buttons, so that lifecycle follows the money math instead of a fragile user toggle.
12. As a user, I want to create an expected inflow with one simple form, so that I do not have to understand Promise and Schedule tables.
13. As a user, I want the creation form to capture total agreement amount and first due date together, so that setup feels natural.
14. As a user, I want Sarflog to create the agreement and first schedule behind the scenes, so that the architecture stays strong without burdening me.
15. As a user expecting salary, I want the agreement to show my salary contract and the cashflow tab to show the next paycheck, so that long-term agreement and monthly planning stay separate.
16. As a user expecting a client invoice, I want to reschedule a delayed payment without changing the original invoice amount, so that history remains honest.
17. As a user, I want to split one delayed payment into multiple future due dates, so that partial payment promises can be tracked.
18. As a user, I want old rescheduled rows to remain visible in the history, so that I can see what changed.
19. As a user, I want the Cashflow view to show only schedule chunks due in the selected month, so that monthly planning is easy.
20. As a user, I want schedule rows to include agreement context, so that a due chunk is not orphaned from its parent agreement.
21. As a user, I want clicking a cashflow row to open the parent agreement drawer, so that I stay in one coherent story.
22. As a user, I want the clicked schedule card to be highlighted in the drawer, so that I know which chunk I was looking at.
23. As a user, I want Receive, Reschedule, and Write off actions beside the active schedule card, so that I know exactly what the action will affect.
24. As a user, I do not want action buttons on high-level agreement rows, so that I do not accidentally act on the wrong due-date chunk.
25. As a user, I want schedule cards to hide actions when the agreement is fully closed, so that finished agreements are protected.
26. As a user, I want to receive more than one schedule chunk in one payment when the total does not exceed the agreement, so that one client transfer can settle multiple due dates.
27. As a user, I want Sarflog to reject receipt amounts above the agreement cap, so that the original contract stays mathematically true.
28. As a user, I want excess money to be recorded as separate income, so that bonuses, tips, or overpayments do not corrupt the agreement.
29. As a user, I want to write off some expected money, so that disputed or lost amounts are no longer treated as collectible cash.
30. As a user, I want write-offs to reduce outstanding amount without touching wallet cash, so that forgiveness or loss is not treated as payment.
31. As a user, I want to reverse a write-off if the customer later pays, so that the money can become outstanding or received again.
32. As a user, I want to reverse a receipt if I logged it by mistake, so that wallet and agreement history are corrected without erasing the original fact.
33. As a user, I want receipt and write-off reversals to work in any order, so that I can correct whichever financial action was wrong.
34. As a user, I want reversal history to remain visible, so that I can explain why the current state changed.
35. As a user, I want reschedule reversal to be allowed only when replacement schedules are untouched, so that real payment history is never scrambled.
36. As a user, I want Sarflog to block reschedule reversal after a child schedule has been received, written off, or rescheduled again, so that the tree remains trustworthy.
37. As a user, I want schedule date and amount changes to go through rescheduling, so that historical due-date changes are recorded.
38. As a user, I want schedule delete to be replaced by safe actions, so that expected money cannot silently vanish.
39. As a user, I want pristine setup mistakes to have a safe correction path, so that simple data entry errors do not require heavy accounting language.
40. As a user, I want non-pristine agreements to preserve original amount and schedule history, so that real financial history cannot be rewritten.
41. As a user, I want the details drawer to show a unified timeline, so that receipts, write-offs, reversals, and reschedules read like one story.
42. As a user, I do not want raw internal IDs in the timeline, so that the UI feels like a financial tool rather than a database view.
43. As a user, I want formatted amounts and dates in the timeline, so that the history is easy to read.
44. As a user, I want overdue schedule chunks to use my local timezone, so that due status matches my real day.
45. As a user, I want expected inflows to continue helping budget backing only for active collectible outstanding amounts, so that my plan is not backed by closed or written-off money.
46. As a user, I want expected debt repayments, refunds, earned income, and asset-sale proceeds to follow the same Promise/Schedule rules, so that incoming-money behavior is consistent.
47. As a developer, I want Promise state to be derived from ledger facts, so that status bugs cannot return.
48. As a developer, I want Schedule state to preserve close reasons and parent-child history, so that reschedule chains are auditable.
49. As a developer, I want financial reversals and structural reversals to have different validation rules, so that correction UX stays flexible without breaking history.
50. As a developer, I want tests at route and service seams, so that frontend and backend refactors do not weaken money invariants.
51. As a developer, I want reusable progress and timeline components, so that other money-history surfaces can use the same visual language later.
52. As a developer, I want legacy expected-inflow paths contracted or hidden, so that old edit/delete/reopen behavior cannot bypass the new domain rules.

## Implementation Decisions

- Treat ADR 0012, ADR 0013, and ADR 0014 as the canonical Epic 4 execution set.
- Reuse the existing Promise, Schedule, realization, allocation, and write-off foundation rather than rebuilding the domain from scratch.
- Treat the current 5-state Promise status model as transitional. The target stored Promise lifecycle is `OPEN` or `CLOSED`.
- This project is still in development, so prefer a clean destructive migration over preserving obsolete expected-inflow data shapes.
- Do not keep legacy columns, enum values, payload fields, route behavior, fixtures, or UI branches solely to avoid losing development data.
- Migration may either map old development rows into the new `OPEN`/`CLOSED` shape or discard/reseed incompatible development rows, whichever leaves the cleaner long-term architecture.
- No old Promise status values should survive in persistence after the migration.
- Do not store derived Promise display states as the source of truth.
- Expose derived display state separately from stored lifecycle. The expected display states are `EXPECTED`, `FULLY_RECEIVED`, `SETTLED`, and `WRITTEN_OFF`.
- Derive display state from original amount, valid received amount, active written-off amount, and outstanding amount.
- Promise `original_amount` represents the agreement amount and must remain stable after meaningful activity exists.
- Pristine setup mistakes may have a narrow safe correction path, but real financial or schedule history must not be rewritten.
- Promise does not own `close_reason` as stored truth. API close details should be derived from the facts that closed the agreement.
- Schedule remains the cashflow layer and keeps detailed lifecycle, close reason, due date, amount, and parent-child history.
- Rescheduling marks the source schedule as superseded and creates replacement child schedules.
- Rescheduling must never mutate the Promise original amount.
- The sum of active schedule remaining amounts should reconcile to Promise outstanding amount.
- Receipt allocation may span multiple active schedules under the same Promise.
- A receipt may exceed one schedule's remaining amount only if the excess can be allocated to other active schedules in the same Promise.
- A receipt must be rejected if received plus written off plus new receipt would exceed the Promise original amount.
- Excess money outside the Promise contract belongs in standalone income, not the expected inflow.
- Write-offs are financial actions that reduce collectible outstanding amount without creating wallet movement.
- Write-offs must be reversible in any order.
- Receipt reversals must be supported as Expected Inflow domain actions, not only as generic income deletion.
- Financial reversals must preserve the original action and append compensating history or an equivalent immutable reversal fact.
- Receipt reversal must also preserve wallet/entity ledger correctness by using the shared financial-event reversal behavior.
- Write-off reversal should not simply erase the historical write-off. The final architecture should preserve both original write-off and reversal history.
- Promise lifecycle auto-closes when outstanding amount reaches zero.
- Promise lifecycle auto-reopens when reversal makes outstanding amount positive again.
- Closed Promises must not expose Receive, Reschedule, or Write off actions.
- Manual Promise close and manual Promise reopen are not part of the target user workflow.
- Cancel remains a contract-voiding action only where it is mathematically safe and clearly distinct from write-off.
- Raw schedule edit and raw schedule delete are not normal actions after creation.
- Schedule date or amount changes should be represented by reschedule, reverse, write-off, or cancel flows.
- Reschedule reversal is structural, not financial. It must follow a leaves-only rule.
- A reschedule can be reversed only if the child schedules created by that reschedule are untouched.
- Untouched child schedules means no receipt allocation, no write-off, no child reschedule, and still in the expected state.
- If a child schedule has real activity, the reschedule tree is locked and the user must use new financial/structural actions rather than reversing the old split.
- The Agreements UI is the "what" view. It should not be month-filtered by due schedule date.
- Agreement rows should not show schedule-level action buttons.
- Agreement rows should use a reusable tri-color progress bar.
- The Cashflow UI is the "when" view. It should be filtered by selected month and show schedule chunks due in that month.
- Cashflow rows should carry enough parent Promise context for the user to understand the due chunk.
- Schedule rows should not have standalone details pages.
- Clicking a schedule row should open the parent Promise drawer and anchor the schedule card.
- The details drawer should contain summary metrics, schedule cards, inline actions, and a unified timeline.
- The unified timeline should merge creation, receipt, write-off, reversal, reschedule, cancel, and close events into one user-readable story.
- Raw database IDs should not be primary UI content in the timeline.
- Existing expected-inflow budget backing behavior must continue to use active collectible schedule amounts, not closed or written-off amounts.
- Expected inflow date behavior must use the effective user timezone for "today", overdue, future-date validation, and default action dates.
- API responses should not keep legacy status or lifecycle fields solely for backwards compatibility with development-era callers.
- Short-lived expand-contract code is acceptable only inside a single implementation slice to keep tests green; each slice should remove obsolete legacy fields and branches before it is considered complete.
- The final public contract should not require frontend code to infer Promise status from raw stored database lifecycle.

## Testing Decisions

- Tests should assert externally visible behavior and financial invariants rather than private helper implementation.
- The preferred backend seam is Expected Inflow API behavior because it exercises auth, timezone, schemas, service rules, persistence, wallet effects, and response contracts together.
- Service-level tests are appropriate for derived Promise display state, Promise outstanding math, allocation math, and leaves-only reschedule traversal.
- Migration tests should prove no legacy Promise status values survive. If old rows are kept, they must map cleanly to `OPEN` or `CLOSED`; if keeping them makes the migration messy, development data may be discarded/reseeded.
- API tests should prove derived display states for expected, fully received, settled mixed outcome, and fully written-off agreements.
- API tests should prove Promise status is not used as stale display truth.
- Receipt tests should cover partial receipt, exact full receipt, receipt spanning multiple active schedules, and rejected over-receipt above the Promise cap.
- Receipt tests should prove a schedule-level over-receipt can spill into sibling active schedules only up to the Promise cap.
- Receipt reversal tests should prove wallet/entity ledger effects are reversed, original realization history remains visible, and Promise math recalculates.
- Write-off tests should cover partial write-off, full write-off, mixed settlement, write-off reversal, and reversal after other financial actions.
- Write-off reversal tests should prove the original write-off remains auditable.
- Auto-close tests should prove Promise lifecycle closes exactly when outstanding reaches zero through receipt, write-off, or mixed settlement.
- Auto-reopen tests should prove Promise lifecycle reopens when reversal makes outstanding positive.
- Action-lock tests should prove closed Promises hide or reject Receive, Reschedule, and Write off commands.
- Reschedule tests should prove original schedules become superseded, replacement schedules become children, and Promise original amount does not change.
- Reschedule reversal tests should cover simple leaf reversal, multi-child reversal, multi-level untouched tree reversal, and blocked reversal after child receipt, write-off, or child reschedule.
- No-edit/delete tests should prove non-pristine schedule rows cannot be updated or hard-deleted through public APIs.
- Cancel tests should prove contract cancellation is allowed only when mathematically safe.
- Budget backing tests should prove active expected inflow backing excludes superseded, closed, written-off, and reversed amounts.
- Timezone tests should use explicit request timezones and project timezone helpers for due status and action-date validation.
- Frontend tests should cover Agreements tab behavior, Cashflow tab behavior, action placement, disabled closed-state actions, and schedule deep-link anchoring.
- Component tests should cover tri-color progress rendering for received, written-off, outstanding, zero outstanding, and mixed settlement cases.
- Timeline tests should cover chronological rendering of creation, receipt, write-off, reversal, reschedule, and close events.
- Existing expected-inflow route tests, budget month summary tests, financial-event ledger tests, wallet projection tests, debt repayment tests, and frontend income feature tests are prior art.
- Tests should distinguish immutable financial facts from mutable metadata.
- Tests should preserve compatibility for source kinds: earned income, receivable debt repayment, refund, and asset sale.

## Out of Scope

- Bank import, OCR, statement parsing, or automatic invoice ingestion.
- Automatic recurring expected inflow generation beyond preserving existing behavior.
- Full standalone Income redesign outside excess-payment guidance.
- Full Debt architecture redesign beyond expected repayments using the receivable source.
- Full Asset lifecycle redesign beyond existing asset-sale expected inflow behavior.
- Multi-currency expected inflow accounting.
- Legal invoice management, tax treatment, or accounts-receivable aging reports.
- Full reporting dashboard redesign outside the Expected Inflow surfaces needed for this epic.
- Database-level immutability constraints for every expected-inflow table beyond the constraints needed for this feature.
- Preserving obsolete development-only Expected Inflow data, fields, statuses, or compatibility behavior.
- A generic event-sourcing framework for all domains.

## Further Notes

The current implementation already has useful structural pieces. The important work is not inventing the idea from zero; it is contracting the current partial implementation into the stricter ADR contract.

Known current gaps to close during this spec:

- Promise persistence still uses the older multi-state lifecycle.
- Promise display status is derived and then stored back as status, instead of separating stored lifecycle from display state.
- Legacy expected-inflow data shapes should be removed from the database and codebase rather than carried forward for development-data compatibility.
- Earned over-receipt is currently allowed at the wallet event level even when it exceeds the Promise cap.
- Write-off reversal currently relies on reversal metadata rather than a fully append-only reversal history.
- Receipt reversal is not yet exposed as a first-class Expected Inflow workflow.
- Manual reopen and delete paths still exist around expected inflows.
- The current UI still resembles a single-list/action-button flow more than the final Agreements/Cashflow/Drawer model.

The mental model should stay simple:

- Promise says what was agreed.
- Schedule says when pieces should arrive.
- Realizations say what actually arrived.
- Write-offs say what is no longer collectible.
- Reversals say what was corrected.
- Derived fields say where the agreement stands now.

Do not start by adding more statuses. Start by making the stored facts sharper and deriving the rest.
