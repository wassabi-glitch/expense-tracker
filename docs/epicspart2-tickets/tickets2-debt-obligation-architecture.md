# Tickets: Debt & Obligation Architecture

Source spec: `docs/epicspart2-specs/spec-2-debt-obligation-architecture.md`

These tickets implement the active Epic 2 obligation architecture from ADR 0026-0029. They reset Debt and Payment Plan behavior around derived state, clear taxonomy, explicit schedule models, truthful row settlement, first-class write-offs, and append-only obligation history.

Assumption: the Epicspart2 ledger foundation and money-history definition of done are already in force. Work the frontier: any ticket whose blockers are complete can start.

## Proposed Breakdown

1. **Introduce derived Debt state and archive visibility**
   - Blocked by: None
   - What it delivers: Debt responses and filters expose lifecycle, time status, and archive visibility from facts instead of relying on overloaded stored statuses.

2. **Remove standalone Debt product taxonomy from public flows**
   - Blocked by: None
   - What it delivers: users create and view standalone Debts through origin and counterparty language, without Payment Plan product labels leaking into Debt.

3. **Split Debt creation into principal, opening charges, and wallet movement**
   - Blocked by: Tickets 1, 2
   - What it delivers: Debt creation records what is owed separately from what cash moved today, while preserving imported and unpaid-service flows.

4. **Make Debt payments component-aware**
   - Blocked by: Ticket 3
   - What it delivers: users can apply Debt payments to charges, principal, or a custom split with ledger-backed projections.

5. **Harden Debt reversal and action rules**
   - Blocked by: Tickets 3, 4
   - What it delivers: Debt undo behavior becomes append-only, latest-first, wallet-safe, and free of obsolete formal-loan action language.

6. **Contract legacy Debt status, product-kind, and policy machinery**
   - Blocked by: Tickets 1, 2, 3, 4, 5
   - What it delivers: the transitional Debt cleanup is completed by deleting obsolete stored status/product concepts and aligning UI/tests with the new contract.

7. **Add Payment Plan schedule model foundation with flat-total preview**
   - Blocked by: None
   - What it delivers: Payment Plans store schedule math explicitly and flat installment creation becomes previewable before the plan is created.

8. **Add amortized loan schedules with installment grouping**
   - Blocked by: Ticket 7
   - What it delivers: bank-style plans generate principal and charge rows grouped into understandable installments.

9. **Add manual contract schedule creation**
   - Blocked by: Ticket 7
   - What it delivers: users can enter exact contract rows when generated schedules do not match the provider's schedule.

10. **Convert Payment Plan rows to settlement state and derived overdue**
    - Blocked by: Ticket 7
    - What it delivers: rows distinguish unpaid, partial, paid, written off, and mixed settlement without storing stale time status.

11. **Apply plan-wide waterfall allocation by due date and component**
    - Blocked by: Tickets 8, 10
    - What it delivers: payments allocate across the whole unpaid schedule, oldest due date first and charge before principal within the same due date.

12. **Make Payment Plan write-offs first-class with allocation history**
    - Blocked by: Tickets 10, 11
    - What it delivers: row and plan-level write-offs reduce obligations without pretending wallet money moved.

13. **Make Payment Plan reversals append-only across all financial actions**
    - Blocked by: Tickets 11, 12
    - What it delivers: undoing payments, charges, write-offs, and adjustments preserves the original history and appends reversal facts.

14. **Expose Payment Plan derived totals, archive, and pristine delete behavior**
    - Blocked by: Tickets 10, 13
    - What it delivers: Payment Plans expose current totals and visibility from facts, while only untouched plans can be deleted directly.

15. **Finish cross-domain obligation cleanup and regression coverage**
    - Blocked by: Tickets 6, 8, 9, 14
    - What it delivers: Debt and Payment Plan stay separated end to end, with tests proving projection, timezone, immutability, and UI language contracts.

## Ticket 1: Introduce Derived Debt State And Archive Visibility

**What to build:** Debt should expose its current lifecycle, time urgency, and archive visibility from balance, due date, archive metadata, and the user's timezone. From the user's perspective, open Debts can be on track or overdue, closed Debts stop looking urgent, and archived Debts are simply filed away.

**Blocked by:** None - can start immediately.

- [x] Debt responses expose `lifecycle_status` as open when remaining balance is positive and closed when remaining balance is zero or less.
- [x] Debt responses expose `time_status` only for open Debts.
- [x] Open Debts due today or later in the user's timezone are on track.
- [x] Open Debts due before the user's local today are overdue.
- [x] Closed Debts expose no time urgency.
- [x] Archive state is represented separately from lifecycle and time status.
- [x] Restoring an archived Debt clears archive metadata without changing balance or lifecycle.
- [x] Debt list filtering supports lifecycle, time status, archived-only, and include-archived views.
- [x] User-facing date logic uses the effective user timezone.
- [x] Tests cover open/on-track, open/overdue, closed/no-time-status, archived open, archived closed, and timezone-boundary behavior.

## Ticket 2: Remove Standalone Debt Product Taxonomy From Public Flows

**What to build:** Standalone Debt should stop asking users to classify open-ended obligations as mortgages, store installments, bank loans, or other Payment Plan products. From the user's perspective, Debt creation and display use clear reason and counterparty language.

**Blocked by:** None - can start immediately.

- [x] Debt create and update flows no longer require or display standalone Debt product kind.
- [x] Debt list, detail, activity, and summary responses no longer expose Payment Plan product labels for standalone Debts.
- [x] Debt filters no longer depend on product-kind values.
- [x] Debt creation still accepts useful origin values that explain why the Debt exists.
- [x] Debt creation still accepts useful counterparty kinds that explain who is on the other side.
- [x] User-facing wording for unpaid work, service, goods, or bills covers the deferred-expense case without inventing wallet movement.
- [x] Product labels such as mortgage, car loan, store installment, service pay-later, and bank loan are reserved for Payment Plans.
- [x] Frontend Debt cards, forms, dialogs, filters, and badges stop showing raw product-kind labels.
- [x] Tests prove removed product-kind concepts cannot leak through public Debt create/update/response/filter behavior.
- [x] Existing non-product Debt origin and counterparty behavior remains covered by regression tests.

## Ticket 3: Split Debt Creation Into Principal, Opening Charges, And Wallet Movement

**What to build:** Debt creation should record the obligation amount and any actual cash movement as separate facts. From the user's perspective, borrowed cash with fees, lent money with expected interest, unpaid service bills, and imported balances can all be created without lying about what happened in the wallet.

**Blocked by:**

- Ticket 1: Introduce derived Debt state and archive visibility.
- Ticket 2: Remove standalone Debt product taxonomy from public flows.

- [x] Debt creation accepts an original principal amount.
- [x] Debt creation accepts optional opening charges defaulting to zero.
- [x] Starting Debt balance equals principal plus opening charges.
- [x] Debt creation can record wallet movement when cash actually enters or leaves a wallet.
- [x] Debt creation does not require wallet movement for unpaid service bills or imported balances.
- [x] Wallet movement amount is allowed to differ from the starting Debt balance.
- [x] Principal creation appends an initial Debt ledger entry with principal delta.
- [x] Opening charges append a charge Debt ledger entry with charge delta.
- [x] Remaining Debt balance reconciles from posted Debt ledger entries.
- [x] Wallet-touching creation follows wallet epoch, user timezone, and immutable money-history rules.
- [x] Tests cover principal-only, principal-plus-charge, borrowed cash with upfront fee, lent cash with expected charge, unpaid service bill, and imported balance.

## Ticket 4: Make Debt Payments Component-Aware

**What to build:** Recording a Debt payment should let the user choose how the payment reduces charges and principal. From the user's perspective, the app can match agreements where fees or interest are cleared first, principal is cleared first, or the split is custom.

**Blocked by:** Ticket 3: Split Debt creation into principal, opening charges, and wallet movement.

- [x] Debt payment creation supports automatic allocation.
- [x] Debt payment creation supports charges-first allocation.
- [x] Debt payment creation supports principal-first allocation.
- [x] Debt payment creation supports custom principal and charge splits.
- [x] The default allocation rule is visible in API/UI behavior.
- [x] Payment ledger entries record principal and charge deltas accurately.
- [x] Payments cannot allocate more than the remaining eligible principal or charges.
- [x] Wallet movement created by payment follows the shared money-history seams.
- [x] Remaining amount, remaining principal, and remaining charges reconcile after payment.
- [x] Debt activity clearly distinguishes principal payment and charge payment effects.
- [x] Tests cover all allocation modes, over-allocation rejection, wallet effects, and projection reconciliation.

## Ticket 5: Harden Debt Reversal And Action Rules

**What to build:** Debt actions should preserve history and offer only actions that make sense for standalone Debt. From the user's perspective, reverse means "undo this latest action while keeping the story," not "delete the old row."

**Blocked by:**

- Ticket 3: Split Debt creation into principal, opening charges, and wallet movement.
- Ticket 4: Make Debt payments component-aware.

- [x] Debt reversal appends a reversal ledger entry instead of deleting or mutating the original entry.
- [x] Original Debt ledger entries remain queryable after reversal.
- [x] Reversal is blocked for initial entries.
- [x] Reversal is blocked for reversal entries.
- [x] Reversal is blocked for already-reversed entries.
- [x] Reversal is blocked for entries marked non-reversible.
- [x] Reversal is blocked for older entries while newer unreversed reversible entries remain.
- [x] Wallet-touching Debt reversals also reverse wallet effects through immutable financial history.
- [x] Debt action availability focuses on record payment, add charge, forgive, adjust balance, reverse, archive, restore or unarchive, and future asset settlement.
- [x] Obsolete standalone Debt action language for collateral setup and formal loan restructuring is removed or hidden unless backed by a concrete feature.
- [x] Tests prove latest-first reversal behavior, wallet-safe reversal, original-history preservation, and action availability.

## Ticket 6: Contract Legacy Debt Status, Product-Kind, And Policy Machinery

**What to build:** After the new Debt contract is active, remove the old stored status, product-kind, and generalized policy machinery that only existed to support the previous mixed model. From the user's perspective, Debt becomes simpler and more consistent everywhere.

**Blocked by:**

- Ticket 1: Introduce derived Debt state and archive visibility.
- Ticket 2: Remove standalone Debt product taxonomy from public flows.
- Ticket 3: Split Debt creation into principal, opening charges, and wallet movement.
- Ticket 4: Make Debt payments component-aware.
- Ticket 5: Harden Debt reversal and action rules.

- [x] Legacy Debt lifecycle statuses are no longer used as the source of truth for public behavior.
- [x] Obsolete Debt product-kind persistence is removed or safely migrated out.
- [x] Public Debt schemas no longer expose removed product-kind or legacy status fields.
- [x] Debt action restriction behavior no longer depends on obsolete status/product combinations.
- [x] Debt UI no longer hardcodes legacy statuses or product kinds.
- [x] Tests and fixtures are migrated to derived lifecycle/time status and origin/counterparty language.
- [x] Migration behavior is explicit about development-data cleanup where old values cannot be meaningfully preserved.
- [x] Cross-flow behavior still proves Debt does not depend on Payment Plan records or ledgers.
- [x] Regression tests prove legacy product vocabulary cannot return to standalone Debt.

## Ticket 7: Add Payment Plan Schedule Model Foundation With Flat-Total Preview

**What to build:** Payment Plan creation should store explicit schedule math and preview generated flat installment rows before creation. From the user's perspective, store installments and buy-now-pay-later plans can be reviewed before becoming real obligations.

**Blocked by:** None - can start immediately.

- [x] Payment Plan creation accepts an explicit schedule model.
- [x] Payment Plan type remains product language while schedule model controls math behavior.
- [x] Store installment and product-financing plans default to flat-total schedule behavior.
- [x] Flat-total creation asks for final total price, down payment, payment count, frequency, and first due date.
- [x] Flat-total schedule generation computes unpaid total as final total minus down payment.
- [x] Flat-total generated rows are principal rows.
- [x] Flat-total rounding ensures the generated rows reconcile exactly to the unpaid total.
- [x] Schedule preview returns total principal, total charges, total to pay, final due date, and rows.
- [x] The user can create the plan from the reviewed preview.
- [x] Existing Payment Plan payment and budget-boundary behavior remains intact for flat plans.
- [x] Tests cover default mapping, preview totals, generated row amounts, rounding, creation from preview, and regression for existing flat plan behavior.

## Ticket 8: Add Amortized Loan Schedules With Installment Grouping

**What to build:** Payment Plans should support bank-style loan schedules where each installment can include interest/charge and principal rows. From the user's perspective, a loan payment appears as one installment even when the accounting has multiple components.

**Blocked by:** Ticket 7: Add Payment Plan schedule model foundation with flat-total preview.

- [x] Bank loan, mortgage, and auto loan plan types default to amortized schedule behavior.
- [x] Amortized creation accepts principal, annual interest rate, payment count or term, frequency, first due date, and required generation metadata.
- [x] Annual interest rate is converted into a periodic rate based on frequency.
- [x] Generated amortized schedules include charge rows for interest and principal rows for principal.
- [x] Final rounding ensures remaining principal reaches zero.
- [x] Rows that belong to the same installment share stable grouping data.
- [x] API responses can present grouped installments without hiding row-level accounting.
- [x] Schedule preview shows total principal, total interest/charges, total to pay, final due date, installment rows, and remaining principal progression.
- [x] The UI explains generated schedules as planning tools rather than legal guarantees.
- [x] Tests cover monthly and at least one non-monthly frequency, component rows, grouping, rounding, preview, and creation from preview.

## Ticket 9: Add Manual Contract Schedule Creation

**What to build:** Users should be able to enter exact contract rows when generated schedules are not precise enough. From the user's perspective, Sarflog can match the bank app or provider contract instead of forcing an approximation.

**Blocked by:** Ticket 7: Add Payment Plan schedule model foundation with flat-total preview.

- [x] Manual schedule model accepts user-entered due dates, principal amounts, charge amounts, and totals.
- [x] Manual rows preserve user-entered amounts instead of regenerating them.
- [x] Manual schedule creation validates that rows are internally consistent.
- [x] Manual schedule creation supports multiple rows per installment when principal and charges are both present.
- [x] Manual schedule preview shows entered rows and aggregate totals before creation.
- [x] Users can switch from generated preview to manual schedule mode before creation.
- [x] Manual schedules store enough metadata to explain that the contract schedule came from user-entered rows.
- [x] Payment Plan responses treat manual rows the same as generated rows after creation.
- [x] Tests cover exact-row preservation, validation failures, mixed principal/charge rows, switching to manual mode, and creation from preview.

## Ticket 10: Convert Payment Plan Rows To Settlement State And Derived Overdue

**What to build:** Payment Plan rows should describe whether the scheduled obligation is unpaid, partial, or settled, and display overdue as a derived time label. From the user's perspective, paid and written-off rows no longer collapse into the same false "paid" meaning.

**Blocked by:** Ticket 7: Add Payment Plan schedule model foundation with flat-total preview.

- [x] Row settlement state derives from amount, paid amount, and written-off amount.
- [x] A row with no paid or written-off amount is unpaid.
- [x] A row with partial paid or written-off amount and remaining balance is partial.
- [x] A row with zero remaining amount is settled.
- [x] Public labels distinguish paid, written off, mixed settled, unpaid, partial, and overdue cases.
- [x] Overdue is derived from due date, unsettled state, and the user's local today.
- [x] Closed or settled rows do not show stale overdue urgency.
- [x] Stored skipped status is removed or ignored as a current settlement state.
- [x] Row responses expose enough paid, written-off, remaining, settlement, and time information for the UI to render truthful labels.
- [x] Tests cover unpaid, partial-paid, partial-written-off, fully paid, fully written-off, mixed settled, overdue, and timezone-boundary cases.

## Ticket 11: Apply Plan-Wide Waterfall Allocation By Due Date And Component

**What to build:** Payment Plan payments should allocate across the whole unpaid schedule in a predictable order. From the user's perspective, early payments, large payments, and partial payments reduce rows chronologically and clear charges before principal on the same due date.

**Blocked by:**

- Ticket 8: Add amortized loan schedules with installment grouping.
- Ticket 10: Convert Payment Plan rows to settlement state and derived overdue.

- [ ] Plan-level payment allocation scans the whole unpaid schedule.
- [ ] Allocation visits older due dates before newer due dates.
- [ ] Allocation pays charge rows before principal rows within the same due date.
- [ ] Allocation supports payments that partially settle one row.
- [ ] Allocation supports payments that spill across multiple rows and installments.
- [ ] Allocation supports oversized payments up to the remaining obligation and rejects invalid excess according to product rules.
- [ ] Payment allocation records explain which rows were touched and by how much.
- [ ] Ledger entries distinguish principal and charge deltas for the payment.
- [ ] Grouped installment responses reflect updated paid, remaining, and settlement values after allocation.
- [ ] Tests cover partial payment, exact installment payment, early overpayment, charge-before-principal ordering, multiple due dates, and projection reconciliation.

## Ticket 12: Make Payment Plan Write-Offs First-Class With Allocation History

**What to build:** Payment Plan write-offs should be real obligation actions, separate from payments and adjustments. From the user's perspective, waived rows or settlement discounts reduce what is owed without pretending cash moved.

**Blocked by:**

- Ticket 10: Convert Payment Plan rows to settlement state and derived overdue.
- Ticket 11: Apply plan-wide waterfall allocation by due date and component.

- [ ] Row-level write-off can write off the remaining row amount.
- [ ] Row-level write-off can write off a custom valid amount.
- [ ] Plan-level write-off can reduce the remaining plan obligation.
- [ ] Plan-level write-off allocates across rows using the same due-date and component ordering as payment waterfall.
- [ ] Write-off updates written-off amounts without creating wallet movement.
- [ ] Write-off creates a dedicated write-off ledger entry rather than a generic adjustment.
- [ ] Write-off allocation history records which rows were touched, how much was written off, and which ledger entry caused it.
- [ ] Row and plan activity distinguish write-off from payment and adjustment.
- [ ] UI copy makes clear that written-off amounts were forgiven or waived, not paid.
- [ ] Tests cover row remaining write-off, row custom write-off, plan-level write-off, allocation history, no-wallet-effect behavior, labels, and projection reconciliation.

## Ticket 13: Make Payment Plan Reversals Append-Only Across All Financial Actions

**What to build:** Undoing Payment Plan financial actions should preserve the original action and append reversal history. From the user's perspective, the app can undo mistakes while still showing what was originally recorded.

**Blocked by:**

- Ticket 11: Apply plan-wide waterfall allocation by due date and component.
- Ticket 12: Make Payment Plan write-offs first-class with allocation history.

- [ ] Payment reversal preserves the original payment action and appends reversal history.
- [ ] Charge reversal preserves the original charge action and appends reversal history.
- [ ] Write-off reversal preserves the original write-off action and appends reversal history.
- [ ] Adjustment reversal preserves the original adjustment action and appends reversal history.
- [ ] Reversals restore paid and written-off row amounts through counter-balancing allocation effects.
- [ ] Wallet-touching reversals preserve immutable FinancialEvent history.
- [ ] Non-wallet write-off and adjustment reversals do not create fake wallet movement.
- [ ] Activity timelines show original actions and reversal actions distinctly.
- [ ] Reversal validation blocks already-reversed or non-reversible actions.
- [ ] Tests cover payment, charge, write-off, and adjustment reversal; original-history preservation; no double-application; and projection reconciliation.

## Ticket 14: Expose Payment Plan Derived Totals, Archive, And Pristine Delete Behavior

**What to build:** Payment Plan current state should be derived from the schedule, allocations, ledger entries, and archive metadata. From the user's perspective, a plan shows what remains, whether it is urgent, whether it is filed away, and whether it can be safely deleted.

**Blocked by:**

- Ticket 10: Convert Payment Plan rows to settlement state and derived overdue.
- Ticket 13: Make Payment Plan reversals append-only across all financial actions.

- [ ] Payment Plan responses expose remaining total.
- [ ] Payment Plan responses expose remaining principal.
- [ ] Payment Plan responses expose remaining charges.
- [ ] Payment Plan lifecycle derives open or closed from remaining obligation.
- [ ] Payment Plan time status derives on-track or overdue from unsettled rows and user-local date.
- [ ] Closed Payment Plans do not expose stale overdue urgency.
- [ ] Archive is represented separately from lifecycle and time status.
- [ ] Archive and unarchive do not change rows, allocations, ledger entries, or balances.
- [ ] Direct delete is allowed only for pristine untouched plans.
- [ ] Plans with meaningful activity must be resolved through payment, write-off, reversal, correction, or archive flows.
- [ ] Tests cover derived totals, derived lifecycle, derived time status, archive/unarchive, pristine delete, active delete rejection, and timezone behavior.

## Ticket 15: Finish Cross-Domain Obligation Cleanup And Regression Coverage

**What to build:** The final slice proves Epic 2 is coherent end to end. From the user's perspective, Debt and Payment Plans behave like separate, truthful obligation tools with consistent state, history, and language.

**Blocked by:**

- Ticket 6: Contract legacy Debt status, product-kind, and policy machinery.
- Ticket 8: Add amortized loan schedules with installment grouping.
- Ticket 9: Add manual contract schedule creation.
- Ticket 14: Expose Payment Plan derived totals, archive, and pristine delete behavior.

- [ ] Debt does not create or depend on Payment Plan ledger rows.
- [ ] Payment Plan does not create or depend on Debt ledger rows.
- [ ] Debt UI uses Debt origin, counterparty, balance, due date, lifecycle, time status, and archive language.
- [ ] Payment Plan UI uses plan type, schedule model, rows, allocations, settlement, lifecycle, time status, and archive language.
- [ ] Shared obligation lists and dashboards do not rely on removed Debt statuses, removed Debt product kinds, or old Payment Plan row statuses.
- [ ] Cross-domain summaries reconcile Debt and Payment Plan balances from their own ledgers or row/allocation facts.
- [ ] Expected-inflow receivable behavior remains explicit and does not auto-trust open receivable Debts.
- [ ] Budget interceptor behavior for Payment Plan payments still returns the existing budget-required contract when needed.
- [ ] Regression tests cover timezone-derived urgency, immutable wallet history, projection reconciliation, no cross-domain leakage, and truthful labels.
- [ ] The Epic 2 documentation, spec, and tickets agree on ADR 0026-0029 as the active execution set.

