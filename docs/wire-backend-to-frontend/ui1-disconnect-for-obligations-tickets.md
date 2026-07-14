# Tickets: UI1 Obligation Backend-Frontend Wiring

These tickets wire the existing Debt and Payment Plan obligation backend contracts into the frontend. Source spec: `ui1-disconnect-for-obligations.md`.

Work the frontier: any ticket whose blockers are all done can start.

## Ticket 1: Show Payment Plan Derived State And Archive Visibility

**What to build:** Payment Plans should show user-timezone-derived open, closed, overdue, and on-track state in list and detail views, and users should be able to archive and restore plans without changing financial history.

**Blocked by:** None - can start immediately.

- [x] Payment Plan list and detail views receive derived lifecycle, urgency, remaining principal, and remaining charges from backend responses.
- [x] User-facing urgency uses the effective user timezone.
- [x] Archive and restore actions are available from the Payment Plan UI.
- [x] Archived Payment Plans are visually filed away without changing balances, rows, allocations, or ledger entries.
- [x] Payment Plan filters support archive visibility separately from lifecycle and urgency.
- [x] The frontend no longer treats stored `ARCHIVED` status as the source of archive truth.
- [ ] Tests cover list urgency, detail urgency, archive, restore, and active versus archived filtering.

## Ticket 2: Use Backend Preview For Flat-Total Payment Plan Creation

**What to build:** Creating a flat-total Payment Plan should call the backend preview contract before saving, show the generated rows and totals, and create the plan from the reviewed schedule.

**Blocked by:** None - can start immediately.

- [x] The creation wizard calls schedule preview before the final create action.
- [x] The review step shows total principal, total charges, total to pay, final due date, frequency, and generated rows.
- [x] Flat-total rows shown to the user match the backend preview.
- [x] Creation submits payload values that match the reviewed preview.
- [x] Local frontend row math is only a provisional hint, not the persisted schedule source of truth.
- [ ] Tests cover successful preview, preview validation errors, creation after preview, and rounding display.

## Ticket 3: Wire Amortized Loan Schedule Creation

**What to build:** Bank loan, mortgage, and vehicle loan plans should support amortized schedule preview and creation, including interest/charge rows grouped with principal rows into installments.

**Blocked by:** Ticket 2: Use Backend Preview For Flat-Total Payment Plan Creation.

- [x] Amortized-eligible plan types expose annual interest rate and schedule inputs.
- [x] Preview shows principal rows, charge rows, installment grouping, totals, and final due date.
- [x] The UI explains generated schedules as planning tools, not legal guarantees.
- [x] Creation preserves the selected amortized schedule model and generation metadata.
- [x] Payment and detail views display grouped installment meaning without hiding row-level accounting.
- [ ] Tests cover amortized preview, missing-rate validation, creation, non-monthly frequency, and grouped display.

## Ticket 4: Wire Manual Contract Schedule Creation

**What to build:** Users should be able to create Payment Plans from exact manually entered contract rows when generated schedules do not match the provider agreement.

**Blocked by:** Ticket 2: Use Backend Preview For Flat-Total Payment Plan Creation.

- [x] The creation wizard supports a manual schedule mode.
- [x] Users can enter due dates, principal amounts, charge amounts, and optional installment grouping.
- [x] Preview validates and returns the exact manual rows before creation.
- [x] Users can switch from generated preview to manual mode before saving.
- [x] Saved plans preserve manually entered rows and metadata.
- [ ] Tests cover valid manual rows, invalid row validation, mixed principal and charge rows, mode switching, and creation.

## Ticket 5: Wire Payment Plan Write-Off And Charge Reversal Actions

**What to build:** Payment Plan details should expose row-level write-off, plan-level write-off, write-off undo, and latest charge reversal as first-class append-only actions.

**Blocked by:** Ticket 1: Show Payment Plan Derived State And Archive Visibility.

- [x] Row-level write-off supports full remaining and custom valid amount flows.
- [x] Plan-level write-off allocates across rows using backend waterfall behavior.
- [x] Write-off UI copy distinguishes waived or forgiven money from paid money.
- [x] Latest charge reversal is available when backend policy allows it.
- [x] Activity shows payments, charges, write-offs, and reversals distinctly.
- [x] Cache invalidation keeps list, detail, summary, and row state synchronized after each action.
- [ ] Tests cover row write-off, plan write-off, write-off undo, charge reversal, and no-wallet-effect behavior.

## Ticket 6: Wire Debt Creation Principal, Opening Charges, And Wallet Movement

**What to build:** Debt creation should let users separately record original principal, opening charges, and any real wallet movement, including cases where wallet movement differs from starting balance.

**Blocked by:** None - can start immediately.

- [x] Debt creation exposes original principal separately from opening charges.
- [x] Starting Debt balance is previewed as principal plus opening charges.
- [x] Wallet movement remains optional for unpaid bills and imported balances.
- [x] Wallet movement can differ from the starting Debt balance when the real-world event requires it.
- [x] Creation review explains what balance is created and what wallet money moves today.
- [ ] Tests cover principal-only, principal-plus-charge, borrowed cash with fee, lent money with expected charge, unpaid service bill, and imported balance.

## Ticket 7: Wire Debt Component-Aware Payment Allocation

**What to build:** Recording a Debt payment should let users choose automatic, charges-first, principal-first, or custom principal and charge splits, and the resulting activity should show component effects.

**Blocked by:** None - can start immediately.

- [x] Debt payment UI exposes allocation mode when the Debt has principal and charge balances.
- [x] Automatic mode uses the backend default allocation rule.
- [x] Charges-first and principal-first modes send explicit allocation intent.
- [x] Custom mode validates that principal and charge amounts add up to the payment amount.
- [x] Custom mode prevents allocating more than the remaining eligible principal or charges.
- [x] Activity and balance cards update principal, charge, and total remaining values after payment.
- [ ] Tests cover all allocation modes, validation errors, successful payment, and refreshed detail state.

## Ticket 8: Replace Legacy Debt Status Assumptions In Edit Flow

**What to build:** Debt editing should use derived lifecycle status and balance facts, not removed legacy status fields, so open Debts can still be edited safely.

**Blocked by:** None - can start immediately.

- [x] Debt edit amount visibility is based on derived lifecycle and archive state.
- [x] Open, unarchived Debts can submit valid initial amount changes.
- [x] Closed or archived Debts cannot change financial setup through generic edit.
- [x] The frontend no longer checks removed standalone Debt status fields.
- [x] Existing origin, counterparty, date, category, and income-source editing remains intact.
- [ ] Tests cover open edit, closed edit lockout, archived edit lockout, and no legacy status dependency.

## Ticket 9: Finish Obligation UI Contract Regression Coverage

**What to build:** The final regression slice should prove the Obligations UI is wired to the active Debt and Payment Plan contracts and no longer depends on removed vocabulary or stale local models.

**Blocked by:** Ticket 1: Show Payment Plan Derived State And Archive Visibility; Ticket 2: Use Backend Preview For Flat-Total Payment Plan Creation; Ticket 3: Wire Amortized Loan Schedule Creation; Ticket 4: Wire Manual Contract Schedule Creation; Ticket 5: Wire Payment Plan Write-Off And Charge Reversal Actions; Ticket 6: Wire Debt Creation Principal, Opening Charges, And Wallet Movement; Ticket 7: Wire Debt Component-Aware Payment Allocation; Ticket 8: Replace Legacy Debt Status Assumptions In Edit Flow.

- [x] Standalone Debt UI does not expose removed product-kind labels.
- [x] Standalone Debt UI uses origin and counterparty language.
- [x] Payment Plan UI reserves product labels for scheduled plans.
- [x] Payment Plan rows use settlement labels rather than stale skipped or paid-only status meaning.
- [x] Debt and Payment Plan summaries reconcile from their own facts without cross-domain ledger leakage.
- [x] User-timezone overdue behavior is covered across list and detail surfaces.
- [x] Tests cover the primary create, pay, write-off, archive, restore, and reverse paths from the user's perspective.
