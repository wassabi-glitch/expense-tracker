# Tickets: Expected Inflow Architecture

Source spec: `docs/epicspart2-specs/spec-4-expected-inflow-architecture.md`

These tickets implement the active Epic 4 expected-inflow architecture from ADR 0012-0014. They contract the current partial two-layer implementation into a stricter Promise/Schedule model with derived display state, progressive disclosure UI, 100 percent Promise caps, append-only financial reversals, and leaves-only structural reversal.

Assumption: the Epicspart2 ledger foundation and money-history definition of done are already in force. Work the frontier: any ticket whose blockers are complete can start.

## Proposed Breakdown

1. **Contract Promise lifecycle to OPEN/CLOSED with derived display state**
   - Blocked by: None
   - What it delivers: Expected Inflow Promises stop storing stale display labels and expose status from ledger-backed math.

2. **Enforce Promise cap, auto-close, and auto-reopen**
   - Blocked by: Ticket 1
   - What it delivers: agreements cannot be over-received, close when outstanding reaches zero, and reopen when reversal creates outstanding amount.

3. **Expose Agreements and Cashflow views from the two-layer model**
   - Blocked by: Ticket 1
   - What it delivers: users can separately browse high-level agreements and selected-month schedule chunks.

4. **Build Agreement rows with tri-color progress**
   - Blocked by: Tickets 1, 3
   - What it delivers: agreement rows become simple, action-free summaries of received, written-off, and outstanding money.

5. **Build Schedule cards, inline actions, and drawer anchoring**
   - Blocked by: Tickets 2, 3
   - What it delivers: Receive, Reschedule, and Write off actions live beside the specific active schedule they affect.

6. **Replace raw expected-inflow history with a unified timeline**
   - Blocked by: Tickets 3, 5
   - What it delivers: agreement details read as one chronological money story instead of separate raw tables.

7. **Add first-class receipt reversal**
   - Blocked by: Tickets 1, 2, 5
   - What it delivers: mistaken receipts can be reversed through expected-inflow history while preserving wallet/entity ledger correctness.

8. **Make write-off reversal preserve append-only history**
   - Blocked by: Tickets 1, 2, 6
   - What it delivers: mistaken write-offs can be reversed in any order without erasing the original write-off fact.

9. **Add leaves-only reschedule reversal**
   - Blocked by: Tickets 5, 6
   - What it delivers: untouched reschedule branches can be reversed, while branches with real child activity are protected.

10. **Remove legacy data, edit, delete, and manual lifecycle paths**
    - Blocked by: Tickets 2, 7, 8, 9
    - What it delivers: old data shapes and edit/delete/reopen paths no longer bypass or burden the Promise/Schedule and immutable-history rules.

11. **Harden budget backing, timezone behavior, and source-kind coverage**
    - Blocked by: Tickets 2, 7, 8, 9, 10
    - What it delivers: expected inflows stay correct across budgeting, user-local dates, and earned, receivable, refund, and asset-sale sources.

12. **Finish end-to-end Expected Inflow regression and documentation alignment**
    - Blocked by: Tickets 4, 6, 10, 11
    - What it delivers: Epic 4 is verified as one coherent architecture across backend, frontend, tests, and docs.

## Ticket 1: Contract Promise Lifecycle To OPEN/CLOSED With Derived Display State

**What to build:** Expected Inflow Promises should store only whether the agreement is open or closed, while API responses derive the user-facing display state from received, written-off, and outstanding amounts. From the user's perspective, an agreement can be expected, fully received, settled, or written off without stale stored labels causing wrong wording.

**Blocked by:** None - can start immediately.

- [x] Promise lifecycle persistence supports only open and closed values.
- [x] Legacy Promise status values are removed from persistence.
- [x] Development rows using obsolete status or data shapes are either cleanly migrated to open/closed or discarded/reseeded if that produces a cleaner architecture.
- [x] Promise response exposes derived display state separately from stored lifecycle.
- [x] Derived display state covers expected, fully received, settled mixed outcome, and fully written-off agreements.
- [x] Promise close details are derived from facts rather than stored as Promise close reason.
- [x] Promise original amount remains the target for all derived math.
- [x] No legacy status fields, enum values, or compatibility storage remain solely to preserve development-era callers.
- [x] Frontend status labels use the derived display state instead of raw stored lifecycle.
- [x] Tests prove a 99 percent received and 1 percent written-off agreement displays as settled, not written off.
- [x] Tests prove raw Promise lifecycle cannot drift from derived display math.

## Ticket 2: Enforce Promise Cap, Auto-Close, And Auto-Reopen

**What to build:** The Promise should behave like a strict agreement. From the user's perspective, the app should reject receipts above the original agreement, close finished agreements automatically, and reopen agreements automatically when reversal makes money outstanding again.

**Blocked by:** Ticket 1: Contract Promise lifecycle to OPEN/CLOSED with derived display state.

- [x] Receipt creation rejects any payload where received plus written off plus new receipt would exceed original amount.
- [x] A receipt can spill across active sibling schedules only up to the Promise cap.
- [x] Overpayment guidance tells the user to record excess as separate income.
- [x] Promise lifecycle changes to closed when outstanding reaches zero through receipt, write-off, or mixed settlement.
- [x] Promise lifecycle changes back to open when reversal makes outstanding positive.
- [x] Closed Promises reject Receive, Reschedule, and Write off commands.
- [x] Closed Promises hide or disable financial action buttons in the UI.
- [x] The tri-color progress contract can never exceed 100 percent.
- [x] Tests cover partial receipt, exact receipt, sibling-schedule spillover, rejected over-receipt, auto-close, and auto-reopen.
- [x] Existing overpayment tests are updated to the new contract.

## Ticket 3: Expose Agreements And Cashflow Views From The Two-Layer Model

**What to build:** Expected Inflows should have two explicit views: Agreements for the high-level "what" and Cashflow for the selected-month "when." From the user's perspective, a yearly salary agreement no longer appears as if the whole contract belongs to one month.

**Blocked by:** Ticket 1: Contract Promise lifecycle to OPEN/CLOSED with derived display state.

- [x] Agreement listing is not filtered out merely because no schedule is due in the selected month.
- [x] Agreement listing supports search and high-level lifecycle/display filters.
- [x] Cashflow listing returns schedule chunks due in the selected month.
- [x] Cashflow rows include parent Promise title, source label, amount, due date, status, and action availability.
- [x] Cashflow rows omit deep reschedule tree history to keep the month view scannable.
- [x] Schedule rows do not expose their own orphaned details page.
- [x] Clicking a Cashflow row can identify the parent Promise and target schedule.
- [x] Budget month integration continues to consume active schedule backing amounts.
- [x] Tests prove Agreement and Cashflow filters answer different questions.
- [x] Frontend renders Agreements and Cashflow as separate tabs or equivalent primary views.

## Ticket 4: Build Agreement Rows With Tri-Color Progress

**What to build:** Agreement rows should become simple summaries of contract completion. From the user's perspective, each row answers "how close is this agreement to done?" without dates or action buttons competing for attention.

**Blocked by:**

- Ticket 1: Contract Promise lifecycle to OPEN/CLOSED with derived display state.
- Ticket 3: Expose Agreements and Cashflow views from the two-layer model.

- [x] Agreement rows show title, source, original amount, derived display state, and completion math.
- [x] Agreement rows do not show Receive, Reschedule, or Write off buttons.
- [x] Agreement rows do not lead with schedule due dates as if the Promise were a monthly row.
- [x] A reusable tri-color progress component renders received, written-off, and outstanding portions.
- [x] Progress bar segments use original amount as the 100 percent target.
- [x] Progress bar handles zero outstanding, full write-off, mixed settlement, and active partial states.
- [x] Progress bar remains visually stable on mobile and desktop.
- [ ] Component tests cover segment math and labels.
- [ ] Frontend tests prove row action buttons are absent from Agreements.
- [x] Agreement rows open the parent details drawer.

## Ticket 5: Build Schedule Cards, Inline Actions, And Drawer Anchoring

**What to build:** The details drawer should make schedule-level actions obvious. From the user's perspective, Receive, Reschedule, and Write off buttons appear inside the active schedule card they will affect.

**Blocked by:**

- Ticket 2: Enforce Promise cap, auto-close, and auto-reopen.
- Ticket 3: Expose Agreements and Cashflow views from the two-layer model.

- [x] Details drawer includes summary metrics for expected, received, written off, and outstanding amounts.
- [x] Details drawer renders schedule cards for current and historical schedules.
- [x] Active schedule cards expose Receive, Reschedule, and Write off actions when the Promise is open.
- [x] Inactive, superseded, written-off, cancelled, or resolved schedule cards do not expose invalid actions.
- [x] Action payloads target a specific schedule where required.
- [x] Cashflow row navigation opens the parent Promise drawer.
- [x] The target schedule card is anchored or highlighted after Cashflow row navigation.
- [x] The UI does not expose standalone schedule details pages.
- [ ] Tests prove action availability matches Promise lifecycle and schedule state.
- [ ] Tests prove schedule action payloads cannot accidentally act on the wrong chunk.

## Ticket 6: Replace Raw Expected-Inflow History With A Unified Timeline

**What to build:** Expected Inflow details should present one readable history of the agreement. From the user's perspective, creation, receipts, write-offs, reversals, reschedules, cancellations, and closure read as one chronological story.

**Blocked by:**

- Ticket 3: Expose Agreements and Cashflow views from the two-layer model.
- Ticket 5: Build Schedule cards, inline actions, and drawer anchoring.

- [x] Details drawer removes separate raw table-style sections for schedule history, activity, and write-offs.
- [x] Unified timeline includes agreement creation.
- [x] Unified timeline includes receipts with received date and amount.
- [x] Unified timeline includes write-offs with reason and amount.
- [x] Unified timeline includes write-off reversals distinctly from original write-offs.
- [x] Unified timeline includes receipt reversals once receipt reversal exists.
- [x] Unified timeline includes reschedules with source and replacement schedule context.
- [x] Unified timeline includes cancel or close events when applicable.
- [x] Timeline copy uses user-facing language rather than raw internal IDs.
- [x] Amounts and dates use existing formatting helpers.
- [ ] Tests cover timeline ordering and event types.

## Ticket 7: Add First-Class Receipt Reversal

**What to build:** Users should be able to reverse an expected-inflow receipt without deleting the original history. From the user's perspective, a mistaken receipt correction restores wallet math and agreement outstanding amount while keeping the original receipt visible.

**Blocked by:**

- Ticket 1: Contract Promise lifecycle to OPEN/CLOSED with derived display state.
- Ticket 2: Enforce Promise cap, auto-close, and auto-reopen.
- Ticket 5: Build Schedule cards, inline actions, and drawer anchoring.

- [x] Expected Inflow exposes a receipt reversal command.
- [x] Receipt reversal preserves the original realization record as history.
- [x] Receipt reversal appends compensating expected-inflow allocation history or equivalent immutable reversal facts.
- [x] Receipt reversal reverses linked wallet/entity ledger effects through the shared financial-event reversal behavior.
- [x] Receipt reversal recalculates schedule received amounts.
- [x] Receipt reversal recalculates Promise received, outstanding, lifecycle, and display state.
- [x] Receipt reversal works after later write-offs when the math remains valid.
- [x] Receipt reversal blocks already-reversed or invalid realization targets.
- [x] UI exposes receipt reversal from the timeline or receipt history context.
- [x] Tests cover full receipt reversal, partial receipt reversal, reversal after closure, auto-reopen, wallet projection, and original-history visibility.

## Ticket 8: Make Write-Off Reversal Preserve Append-Only History

**What to build:** Write-off reversal should correct the current state without erasing the original write-off. From the user's perspective, if a client later pays a disputed amount, Sarflog can restore the outstanding amount while still showing that the amount was once written off.

**Blocked by:**

- Ticket 1: Contract Promise lifecycle to OPEN/CLOSED with derived display state.
- Ticket 2: Enforce Promise cap, auto-close, and auto-reopen.
- Ticket 6: Replace raw expected-inflow history with a unified timeline.

- [x] Write-off reversal preserves the original write-off as a visible historical fact.
- [x] Write-off reversal appends reversal history instead of relying on silent deletion.
- [x] Write-off reversal works in any order relative to other financial action reversals.
- [x] Write-off reversal recalculates schedule written-off amount.
- [x] Write-off reversal recalculates Promise written-off, outstanding, lifecycle, and display state.
- [x] Write-off reversal can reopen a closed Promise when outstanding becomes positive.
- [x] Timeline shows original write-off and reversal distinctly.
- [x] UI prevents reversing the same write-off twice.
- [x] Tests cover partial write-off reversal, full write-off reversal, mixed settlement reversal, reversal after closure, and original-history visibility.
- [x] Existing write-off reversal behavior is migrated without losing audit readability.

## Ticket 9: Add Leaves-Only Reschedule Reversal

**What to build:** Users should be able to reverse a reschedule only while the replacement branch is untouched. From the user's perspective, correcting a mistaken date split is easy before money activity happens, but protected after child schedules have real history.

**Blocked by:**

- Ticket 5: Build Schedule cards, inline actions, and drawer anchoring.
- Ticket 6: Replace raw expected-inflow history with a unified timeline.

- [x] Reschedule history records enough identity to know which child schedules came from one reschedule action.
- [x] A reschedule reversal command restores the superseded source schedule when all replacement children are untouched.
- [x] Reversal removes or closes untouched replacement children through an auditable structural correction.
- [x] Reversal is allowed for a simple one-child untouched replacement.
- [x] Reversal is allowed for a multi-child untouched replacement.
- [x] Reversal is blocked if any child has received amount.
- [x] Reversal is blocked if any child has written-off amount.
- [x] Reversal is blocked if any child has been rescheduled into its own children.
- [x] Reversal is blocked if any child is no longer expected for another reason.
- [x] Timeline shows reschedule reversal distinctly.
- [x] Tests cover multi-level schedule trees and the blocked child-activity cases.

## Ticket 10: Remove Legacy Data, Edit, Delete, And Manual Lifecycle Paths

**What to build:** Legacy data shapes and actions should stop bypassing or burdening the new Expected Inflow contract. From the user's perspective, active money history is changed through Receive, Reschedule, Write off, Reverse, or safe Cancel actions, not raw edit/delete/reopen controls. From the developer's perspective, this is a development-stage cleanup: remove obsolete database values, code paths, schemas, fixtures, and UI branches instead of preserving them for old dev data.

**Blocked by:**

- Ticket 2: Enforce Promise cap, auto-close, and auto-reopen.
- Ticket 7: Add first-class receipt reversal.
- Ticket 8: Make write-off reversal preserve append-only history.
- Ticket 9: Add leaves-only reschedule reversal.

- [x] Obsolete Expected Inflow enum values, columns, payload fields, and response fields are removed when they no longer match the new contract.
- [x] Obsolete development rows are migrated only when the mapping is clean; otherwise they may be discarded or reseeded.
- [x] No database table or column is kept solely to preserve stale development data.
- [x] No backend branch is kept solely to support the old 5-state Promise lifecycle.
- [x] No frontend branch is kept solely to render old expected-inflow status values.
- [x] Manual Promise reopen is removed or hidden from public user workflows.
- [x] Manual lifecycle changes are replaced by auto-close and auto-reopen math.
- [x] Raw schedule edit is unavailable after meaningful activity exists.
- [x] Raw schedule delete is unavailable after meaningful activity exists.
- [x] Promise delete is allowed only for pristine setup records with no meaningful history.
- [x] Non-pristine deletion attempts return clear guidance to use reverse, write-off, cancel, or archive-like visibility behavior if available.
- [x] Pristine setup correction remains possible without weakening history rules.
- [x] Frontend removes legacy edit/delete/reopen buttons where they violate the target contract.
- [x] API tests prove lifecycle commands cannot bypass expected-inflow invariants.
- [x] Regression tests prove legacy budget expected-income routes cannot bypass lifecycle commands.
- [x] Migration and cleanup tests prove the final schema/code path has no dependency on obsolete expected-inflow development data.

## Ticket 11: Harden Budget Backing, Timezone Behavior, And Source-Kind Coverage

**What to build:** Expected Inflows should remain trustworthy across budget backing, local dates, and every supported incoming-money source. From the user's perspective, plans are backed only by collectible money, dates match their local day, and earned income, receivables, refunds, and asset sales follow the same rules.

**Blocked by:**

- Ticket 2: Enforce Promise cap, auto-close, and auto-reopen.
- Ticket 7: Add first-class receipt reversal.
- Ticket 8: Make write-off reversal preserve append-only history.
- Ticket 9: Add leaves-only reschedule reversal.
- Ticket 10: Remove legacy data, edit, delete, and manual lifecycle paths.

- [ ] Budget backing includes only active collectible outstanding schedule amounts.
- [ ] Budget backing excludes superseded schedules.
- [ ] Budget backing excludes closed, written-off, cancelled, and reversed amounts.
- [ ] Budget month summaries remain schedule-based rather than Promise-date based.
- [ ] Due status and overdue behavior use the user's effective timezone.
- [ ] Receipt, write-off, reschedule, and cancel date validation use the user's effective timezone.
- [ ] Earned income expected inflows follow the Promise cap and reversal rules.
- [ ] Receivable debt repayment expected inflows follow the Promise cap and reversal rules while preserving debt repayment effects.
- [ ] Refund expected inflows follow the Promise cap and reversal rules while preserving refund links.
- [ ] Asset-sale expected inflows follow the Promise cap and write-off behavior for lower actual sale proceeds.
- [ ] Tests cover timezone boundaries and every supported source kind.
- [ ] Wallet projection tests prove reversals do not double-apply wallet effects.

## Ticket 12: Finish End-To-End Expected Inflow Regression And Documentation Alignment

**What to build:** The final slice proves Expected Inflows now match Epic 4 end to end. From the user's perspective, Agreements, Cashflow, details, actions, reversals, and budget backing behave like one coherent incoming-money system.

**Blocked by:**

- Ticket 4: Build Agreement rows with tri-color progress.
- Ticket 6: Replace raw expected-inflow history with a unified timeline.
- Ticket 10: Remove legacy data, edit, delete, and manual lifecycle paths.
- Ticket 11: Harden budget backing, timezone behavior, and source-kind coverage.

- [ ] End-to-end tests cover create, receive, reschedule, write off, reverse receipt, reverse write-off, reverse untouched reschedule, and blocked unsafe reschedule reversal.
- [ ] End-to-end tests cover active, fully received, settled mixed outcome, and written-off display states.
- [ ] Frontend tests cover Agreements tab, Cashflow tab, details drawer, schedule anchor, inline actions, progress bar, and timeline.
- [ ] No public Expected Inflow workflow depends on the old 5-state Promise status model.
- [ ] No public Expected Inflow workflow can over-receive above original amount.
- [ ] No public Expected Inflow workflow can hard-delete non-pristine schedule history.
- [ ] Existing docs agree that Promise is agreement, Schedule is cashflow, and ledger facts drive display state.
- [ ] The spec, tickets, and ADRs use consistent terminology for Promise, Schedule, realization, write-off, reversal, outstanding, and settlement.
- [ ] Remaining known gaps are documented if any are intentionally deferred.
- [ ] Docker-first verification instructions are clear for migrations, backend tests, and frontend build.
