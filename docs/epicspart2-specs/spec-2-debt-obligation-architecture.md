# Spec 2: Debt & Obligation Architecture

Source epic: Epic 2 Debt & Obligation Architecture

Source decisions: ADR 0026, ADR 0027, ADR 0028, ADR 0029

## Problem Statement

Sarflog's obligation domain needs to become clear enough that users can trust it and developers can extend it without reintroducing old coupling.

Debt and Payment Plans used to carry overlapping language. Debt absorbed formal loan and installment vocabulary even though standalone Debt is supposed to represent an open-ended obligation. Payment Plans carried schedule rows, transactions, charges, and ledger entries, but still mostly behaved like one flat installment engine. This made real-world cases hard to model:

- A simple IOU should not look like a mortgage.
- A bank loan should not be calculated like a store installment.
- A written-off row should not be shown as if it was fully paid with wallet money.
- A closed Debt should not continue to look overdue.
- A user action that reverses history should not delete the history it is reversing.
- A balance should be explainable from ledger entries, not from a magical mutable field.

The current architecture also risks confusing product states with accounting facts. Stored status enums try to describe lifecycle, urgency, archive visibility, payment outcome, forgiveness, and collection severity all at once. Payment Plan row status uses `PAID` as a terminal state even when a row may be settled by payment, write-off, or a mix of both. Write-off behavior can be hidden inside generic adjustment language, which weakens the user's understanding of what really happened.

Epic 2 must reset this area into a coherent obligation architecture:

- Debt is an open-ended balance with clear origin, counterparty, due date, and ledger history.
- Payment Plan is a scheduled contract with explicit schedule math and row-level settlement.
- Wallet money movement follows the Epic 1 immutable-ledger rules.
- Non-wallet obligation facts still get truthful domain ledger history where needed.
- Derived status is computed from facts, not stored as stale labels.

## Solution

Build the active Epic 2 obligation architecture from ADR 0026-0029.

From the user's perspective, Sarflog should make obligations feel honest and understandable:

- A Debt should say who owes whom, why it exists, what remains, and whether the due date has passed.
- A Payment Plan should say what contract schedule exists, what each row requires, what has been paid, what has been written off, and what remains.
- Payments, charges, write-offs, corrections, and reversals should be distinct actions with distinct history.
- Archive should change visibility only. It should not pretend a financial lifecycle changed.
- Bank loans, store installments, and manual contracts should be created through the schedule model that matches the real contract.

From the engineering perspective, the solution is a domain cleanup and architecture reset:

- Debt state becomes derived through `lifecycle_status` and `time_status`.
- Debt archive moves fully out of status and into archive metadata.
- Debt product vocabulary is removed from standalone Debt.
- Debt creation separates principal, opening charges, and wallet movement.
- Debt ledger actions become append-only facts with guarded reversals.
- Payment Plan creation branches by explicit `schedule_model`.
- Payment Plan generated schedules are previewed before creation.
- Payment Plan schedule rows use principal/charge components and settlement amounts.
- Payment Plan row state is settlement state, not time state.
- Payment Plan write-offs become first-class actions with their own ledger type and allocation history.
- Payment Plan totals and statuses are derived from rows, allocations, and ledger entries.

The highest-level testing seam should be API behavior at the Debt and Payment Plan route boundaries, supported by service-level tests only where schedule generation or allocation math is too dense to validate clearly through one route call.

## User Stories

1. As a user with a simple IOU, I want Debt to use plain obligation language, so that I do not have to classify a friend loan as a bank product.
2. As a user who owes someone money, I want the app to show whether the Debt is open or closed, so that I know whether any balance remains.
3. As a user who is owed money, I want the app to show whether the Debt is on track or overdue, so that I can follow up at the right time.
4. As a user with a paid-off Debt, I want the Debt to stop showing overdue urgency, so that closed history does not look like an active problem.
5. As a user, I want archived Debts to stay financially unchanged, so that filing something away does not rewrite its balance.
6. As a user, I want to restore an archived Debt without changing its lifecycle, so that archive behaves like visibility, not accounting.
7. As a user, I want Debt reason choices to use human wording, so that I can choose the right situation without understanding backend enums.
8. As a user with an unpaid bill, I want to record that I received work, service, or goods and need to pay later, so that no wallet movement is invented.
9. As a user who borrowed cash, I want to record the principal I received, so that the original debt amount is clear.
10. As a user who borrowed cash with upfront fees or interest, I want to record opening charges separately, so that the balance is more accurate than the cash received.
11. As a user who lent money with expected interest, I want to distinguish principal from charges, so that repayment history can explain both parts.
12. As a user, I want the starting Debt balance to equal principal plus opening charges, so that the total obligation is not confused with wallet movement.
13. As a user, I want wallet movement at Debt creation to be optional and explicit, so that imported or unpaid-service Debts do not touch cash.
14. As a user, I want imported Debts to record only the remaining balance that matters today, so that old pre-Sarflog history does not corrupt wallet math.
15. As a user, I want Debt charges to be added as their own action, so that interest, fees, penalties, and corrections are visible.
16. As a user, I want interest to be treated as a kind of charge, so that the app does not create competing balance systems.
17. As a user recording a Debt payment, I want to choose how the payment applies to principal and charges, so that the app matches the real agreement.
18. As a user, I want a visible default allocation rule, so that hidden principal-first or charge-first behavior does not surprise me.
19. As a user, I want to forgive part or all of a Debt without wallet money moving, so that waived obligations are truthful.
20. As a user, I want to correct a Debt balance with a guarded adjustment, so that mistakes can be fixed without pretending the correction was a payment.
21. As a user, I want to reverse the latest reversible Debt action, so that mistakes can be undone while preserving history.
22. As a user, I want the app to block reversing older Debt entries before newer ones, so that the activity story remains coherent.
23. As a user, I want original Debt ledger entries to remain visible after reversal, so that I can understand what happened and what was undone.
24. As a user, I want wallet-touching Debt reversals to also reverse wallet effects, so that my wallet balance returns to the right value.
25. As a user, I want Debt history to distinguish payments, charges, forgiveness, adjustments, and reversals, so that the activity feed tells the truth.
26. As a user, I want asset settlement to remain a planned Debt capability, so that future non-cash settlement can be modeled deliberately.
27. As a user, I do not want standalone Debt to expose formal loan actions like restructure terms unless a real feature needs them, so that the UI stays simple.
28. As a user creating a store installment, I want to enter the final total price, down payment, payment count, frequency, and first due date, so that the app can build the right flat schedule.
29. As a user creating a buy-now-pay-later plan, I want the plan to divide the unpaid total across scheduled rows, so that the schedule matches flat installment products.
30. As a user creating a bank loan, I want to enter principal, annual interest rate, term, frequency, and first due date, so that the schedule can model interest and principal separately.
31. As a user with a mortgage or auto loan, I want the plan to generate both charge and principal rows, so that each installment reflects the real loan components.
32. As a user with an unusual bank contract, I want manual schedule mode, so that Sarflog can match the contract instead of forcing a formula.
33. As a user, I want to preview generated schedules before creating a plan, so that I can catch differences from the contract early.
34. As a user, I want to edit a generated row before creation, so that small schedule differences can be corrected without starting over.
35. As a user, I want to add fees during schedule review, so that contract charges can be included from the start.
36. As a user, I want to switch from generated schedule to manual schedule, so that exact contract matching stays possible.
37. As a user, I want Sarflog to explain that generated bank schedules are planning tools, so that I know the bank contract remains the final source of truth.
38. As a user, I want product type and schedule math to be separate, so that a product label does not silently choose wrong accounting behavior.
39. As a user, I want `STORE_INSTALLMENT` style plans to default to flat total math, so that common Nasiya-like plans stay easy.
40. As a user, I want `BANK_LOAN`, mortgage, and auto loan plans to default to amortized math, so that formal loans behave like loans.
41. As a user, I want `OTHER` and ambiguous plans to let me choose the schedule model, so that edge cases are not mislabeled.
42. As a user, I want term to mean payment count plus frequency, so that weekly, biweekly, monthly, and quarterly plans all work.
43. As a user, I want Payment Plan rows to show principal and charges separately when needed, so that I understand what each installment covers.
44. As a user, I want multiple rows for one amortized installment to appear as one grouped installment, so that the UI does not look like duplicate payments.
45. As a user, I want Payment Plan payments to allocate across the whole unpaid schedule, so that early or oversized payments behave predictably.
46. As a user, I want the Payment Plan waterfall to pay oldest due dates first, so that the schedule story stays chronological.
47. As a user, I want charges on the same due date to be paid before principal, so that interest and fees are cleared before principal when the model requires it.
48. As a user, I want row status to mean unpaid, partial, or settled, so that status describes what remains instead of pretending all settlement was payment.
49. As a user, I want overdue to be computed from due date and local today, so that the app does not store stale time labels.
50. As a user, I want a row that is fully paid to say Paid, so that wallet payment is clear.
51. As a user, I want a row that is fully written off to say Written off, so that forgiveness is not misrepresented as payment.
52. As a user, I want a row settled by both payment and write-off to say Settled, so that mixed outcomes are truthful.
53. As a user, I want to write off the remaining amount on one row, so that waived scheduled obligations can be closed cleanly.
54. As a user, I want to write off a custom amount on one row, so that partial waivers are supported.
55. As a user, I want to write off part of the whole plan balance, so that settlement agreements can be recorded without touching wallet money.
56. As a user, I want plan-level write-offs to allocate predictably across remaining rows, so that the resulting schedule is explainable.
57. As a user, I want write-offs to have their own history type, so that forgiveness is not buried as a generic adjustment.
58. As a user, I want to reverse a Payment Plan write-off by appending reversal history, so that the original waiver remains auditable.
59. As a user, I want payment actions and write-off actions to be separate, so that the app never implies cash moved when it did not.
60. As a user, I want row history to show which payments and write-offs touched that row, so that I can explain its current state.
61. As a user, I want plan history to distinguish payment, added charge, write-off, adjustment, and reversal, so that the contract story is readable.
62. As a user, I want Payment Plan archive to be separate from lifecycle, so that hiding a plan does not change the amount owed.
63. As a user, I want pristine Payment Plans to be deletable, so that accidental empty setup can be removed.
64. As a user, I want active rows with real activity to be paid, written off, rescheduled, or reversed instead of deleted, so that history remains trustworthy.
65. As a user, I want remaining Payment Plan totals split into total, principal, and charges, so that I know what kind of balance remains.
66. As a user, I want Payment Plan closed/open state derived from remaining obligation, so that lifecycle follows the math.
67. As a developer, I want Debt and Payment Plan vocabulary to stay separate, so that one domain does not quietly recreate the old ghost-ledger coupling.
68. As a developer, I want current-state balances to be projections from ledger rows, so that repair and reconciliation are possible.
69. As a developer, I want every wallet-touching obligation operation to use the shared money-history rules, so that obligations do not become a separate mutable accounting system.
70. As a developer, I want tests at route boundaries for Debt and Payment Plan flows, so that behavior remains stable while internals are refactored.

## Implementation Decisions

- Treat ADR 0026-0029 as the canonical Epic 2 execution set.
- Keep older Debt epoch and Debt vs Payment Plan separation decisions as background constraints, but use ADR 0026-0029 when details conflict.
- Debt and Payment Plans remain separate domains. A standalone Debt must not own Payment Plan product vocabulary, and a Payment Plan must not require a shadow Debt to carry its balance.
- Debt should answer who owes whom, why the obligation exists, what kind of counterparty is involved, what remains, and when it is due.
- Payment Plan should answer what scheduled repayment structure exists, what type of plan it is, what rows are due, and how payments, charges, write-offs, and reversals touched those rows.
- Debt lifecycle must be derived from balance. Open means remaining amount is positive. Closed means remaining amount is zero or less.
- Debt time status must be derived from lifecycle, expected return date, and the user's local business date.
- Closed Debts must not expose `ON_TRACK` or `OVERDUE` time status.
- Archive is visibility only. Archive metadata must be separate from Debt lifecycle and time status.
- Restoring a Debt clears archive metadata and recomputes derived state instead of inventing a lifecycle transition.
- The legacy Debt status model should be removed from persistence rather than replaced by a different stored lifecycle enum.
- Debt route filters should expose derived lifecycle, derived time status, and archive filters rather than legacy status filters.
- Debt product kind should be removed from the Debt model, API payloads, route filters, UI labels, and tests.
- Formal loan and installment vocabulary belongs to Payment Plans, not standalone Debt.
- Debt origin kind should remain because it explains why the Debt exists.
- Debt counterparty kind should remain because it explains what kind of party is on the other side.
- The user-facing wording for unpaid work, service, goods, or bills should be broader than "someone paid for me".
- Debt creation should ask separately for principal amount, opening charges, and wallet movement.
- Opening Debt balance should equal opening principal plus opening charges.
- Wallet movement at Debt creation should represent actual cash that entered or left wallets today, not the total balance by assumption.
- Imported or pre-existing Debt balances should remain wallet-disconnected unless the user records current wallet money movement.
- Creating a Debt should append an initial Debt ledger entry for principal.
- Creating a Debt with opening charges should append a charge Debt ledger entry for the opening charge amount.
- Debt remaining amount should be treated as a projection or cache from posted Debt ledger entries.
- Debt ledger entry type is durable history, not UI status.
- Debt ledger source is audit provenance and should remain available for reversal safety.
- Debt reversals must append a new reversal ledger entry rather than deleting or mutating the original entry.
- Debt reversals must be latest-first for reversible posted entries.
- Debt reversal rules must block reversing initial entries, reversal entries, already-reversed entries, non-reversible entries, and older entries when newer reversible entries remain.
- If a reversed Debt entry touched wallet money, the reversal must also preserve the corresponding FinancialEvent reversal behavior so wallet history nets correctly.
- Debt action language should focus on real user actions: record payment, add charge, forgive, adjust balance, reverse entry, archive, restore or unarchive, and future asset settlement.
- Formal-loan actions such as set collateral and restructure terms should be removed or deferred unless a concrete standalone Debt feature needs them.
- Debt payment allocation should be explicit. The supported allocation choices should include automatic allocation, charges-first, principal-first, and custom split.
- The default Debt payment allocation rule must be visible to the user.
- Interest should be modeled as a charge. Do not create a competing interest-balance system during this epic.
- Automatic silent interest accrual is not part of this spec. If interest helpers are introduced later, they should propose charge entries that the user confirms.
- Payment Plans must store an explicit schedule model.
- Payment Plan type is product language. Schedule model is math behavior.
- The initial schedule models are flat total, amortized loan, and manual contract schedule.
- Flat total schedule generation should use final total price, down payment, payment count, frequency, and first due date.
- Flat total rows should be principal rows because seller markup is already included in the final total price.
- Amortized loan schedule generation should use principal, annual interest rate, payment count or term, frequency, first due date, and rounding rules.
- Amortized schedules should generate charge rows for interest and principal rows for principal.
- Manual contract schedule should let users enter exact rows from a bank contract or provider schedule.
- Generated schedules should have a review step before plan creation.
- Schedule preview should include total principal, total charges or interest, total to pay, final due date, and scheduled rows.
- During preview, users should be able to adjust rows, add fee rows, change due dates, or switch to manual schedule mode.
- Generated schedules are planning tools, not legal guarantees. Bank or provider contracts remain the source of truth when exactness matters.
- Default schedule model mapping should be explicit. Store installment, product financing, and many service contracts default to flat total. Bank loans, mortgages, and auto loans default to amortized loan. Education loan and other ambiguous plans should allow user choice.
- Payment Plan term should be represented as payment count plus frequency rather than months alone.
- Payment Plan rows need stable installment grouping so one amortized installment can contain both a charge row and a principal row.
- Payment Plan component type should remain small at the accounting level: principal and charge.
- More detailed charge kinds such as interest, late fee, service fee, penalty, and other can be added later without replacing the core component split.
- Payment Plan waterfall allocation applies to the whole unpaid schedule, not just the current month.
- Payment Plan waterfall ordering is oldest due date first, and within the same due date charge before principal.
- Payment Plan waterfall ordering applies to plan-level payment, plan-level write-off, bulk settlement, and early overpayment.
- Payment Plan row state should be settlement state, not time state.
- Payment Plan row settlement state should be derived or projected from amount, paid amount, and written-off amount.
- A row is unpaid when no amount has been paid or written off.
- A row is partial when some amount has been paid or written off but remaining amount is still positive.
- A row is settled when remaining amount is zero.
- Public row labels can be more specific than settlement state: paid, written off, settled, overdue, or on track.
- Overdue must be derived from due date, settlement state, and the user's local business date.
- Skipped should not exist as a stored settlement state. A missed row is unpaid, partial, overdue, rescheduled, deferred, or written off.
- Row write-off is a first-class action and must allow writing off the remaining amount or a custom amount.
- Plan-level write-off is a first-class action and should allocate across remaining rows with the same due-date and component ordering as the waterfall.
- Write-off must not imply wallet money moved.
- Payment Plan ledger entry type should include a dedicated write-off type.
- Write-off must not be encoded as a generic adjustment. Adjustment is for correction; write-off is for forgiveness, waiver, or settlement.
- Undoing a Payment Plan payment, charge, write-off, or adjustment should append reversal history rather than deleting the original ledger entry.
- Payment transactions should represent actual payment actions. They should not be reused as generic containers for write-offs or adjustments.
- Payment allocation history should explain how payment actions touched rows.
- Write-off allocation history should explain how write-off actions touched rows.
- Payment Plan rows should say what was scheduled.
- Payment Plan allocations should say how actions touched rows.
- Payment Plan ledger entries should say what happened historically.
- Payment Plan derived totals should say where the plan stands today.
- Payment Plan API responses should expose remaining total, remaining principal, remaining charges, lifecycle status, time status, and archive state when those concepts are implemented.
- Payment Plan archive should be separate from financial lifecycle.
- Payment Plan deletion should be allowed only while the plan is pristine and has no meaningful financial activity.
- Metadata-only edits to Debt or Payment Plan entities may remain mutable when they do not change wallet math or obligation ledger math.
- Schema cleanup may be destructive for stale development data if that is the cleanest way to remove legacy status and taxonomy concepts.
- Migration priority is clarity and long-term architecture, not preserving obsolete development rows.
- All wallet-touching operations in this spec must obey the Epic 1 wallet-legs test and immutable money-history rules.
- All user-facing "today" and overdue logic must use the user's effective timezone.
- Implementation should start by sharpening domain concepts rather than adding more statuses.

## Testing Decisions

- Tests should assert externally visible behavior rather than private implementation details.
- The preferred seam is Debt and Payment Plan API behavior, with database assertions used to verify ledger rows, allocations, and projections where user-visible responses alone are not enough.
- Service-level tests are appropriate for schedule generation math, amortized rounding, allocation helpers, and projection reconciliation when route tests would be too noisy.
- Debt derived-state tests should prove open, closed, on-track, overdue, and closed-with-null-time-status combinations.
- Debt timezone tests should prove overdue state uses the user's effective timezone, not server-local date.
- Debt archive tests should prove archive and restore do not change lifecycle or balance.
- Debt taxonomy tests should prove removed product-kind concepts no longer appear in creation payloads, update payloads, response payloads, filters, or UI-facing labels.
- Debt origin and counterparty tests should prove useful origin and counterparty values remain accepted.
- Debt creation tests should cover principal-only creation, principal plus opening charges, wallet-moving borrowed cash, wallet-moving lent cash, unpaid service bill, and imported balance.
- Debt creation tests should prove wallet movement does not have to equal starting Debt balance.
- Debt ledger tests should prove initial and charge entries are posted with correct principal and charge deltas.
- Debt payment tests should cover automatic allocation, charges-first allocation, principal-first allocation, and custom split.
- Debt payment tests should prove remaining amount, remaining principal, and remaining charges reconcile to ledger entries.
- Debt charge tests should prove manual charge entries increase the Debt without creating wallet movement.
- Debt forgiveness tests should prove forgiveness reduces the obligation without creating wallet movement.
- Debt adjustment tests should prove corrections are distinct from forgiveness and payments.
- Debt reversal tests should prove reversal appends a ledger entry and leaves the original entry queryable.
- Debt reversal tests should prove latest-first reversal rules reject out-of-order reversal.
- Debt wallet-touching reversal tests should prove wallet effects are reversed through immutable financial history.
- Debt metadata tests should prove title, description, note, due date, counterparty name, and archive edits do not create unnecessary money-history rows when they do not change financial math.
- Payment Plan schedule model tests should cover flat total, amortized loan, and manual contract schedule creation.
- Flat total tests should prove final total minus down payment is divided across the payment count and generated as principal rows.
- Flat total tests should include rounding behavior so the final row reconciles exactly.
- Amortized loan tests should prove annual interest rate is converted into the correct periodic rate for the selected frequency.
- Amortized loan tests should prove each installment contains charge and principal components and remaining principal reaches zero after final rounding.
- Manual schedule tests should prove user-provided principal and charge rows are preserved.
- Schedule preview tests should prove generated totals, final due date, and row list are visible before creation.
- Schedule preview tests should prove edited rows or manual rows are the rows persisted at creation.
- Schedule model mapping tests should prove plan types default to the intended schedule models while ambiguous types allow user choice.
- Term tests should prove weekly, biweekly, monthly, and quarterly frequencies do not depend on a months-only model.
- Installment grouping tests should prove charge and principal rows for the same amortized installment are grouped for response and UI use.
- Payment Plan waterfall tests should prove allocation walks oldest due date first.
- Payment Plan waterfall tests should prove charge rows are allocated before principal rows on the same due date.
- Payment Plan waterfall tests should cover early payment, oversized payment, partial payment, and payment spanning multiple installments.
- Payment Plan row settlement tests should prove unpaid, partial, and settled states derive from amount, paid amount, and written-off amount.
- Payment Plan row label tests should distinguish paid, written off, and mixed settled rows.
- Payment Plan overdue tests should prove overdue is derived from row due date, settlement state, and user timezone.
- Payment Plan tests should prove skipped is not stored as a settlement state.
- Row write-off tests should cover write off remaining amount and custom amount.
- Row write-off tests should prove written-off amount reduces remaining row obligation without creating wallet movement.
- Plan-level write-off tests should prove the write-off allocates across rows in the same order as waterfall payment allocation.
- Write-off ledger tests should prove write-offs use a dedicated write-off ledger entry type, not a generic adjustment.
- Write-off allocation tests should prove each touched row records how much was written off and which ledger entry caused it.
- Write-off reversal tests should prove reversing a write-off appends reversal history and restores row remaining amounts.
- Payment Plan payment tests should prove payment transactions are created for real payment actions only.
- Payment Plan non-payment action tests should prove write-offs and adjustments do not masquerade as payment transactions.
- Payment Plan charge tests should prove added charges create charge rows and charge ledger history.
- Payment Plan adjustment tests should prove correction remains distinct from write-off.
- Payment Plan reversal tests should prove payment, charge, write-off, and adjustment reversals preserve original ledger entries.
- Payment Plan projection tests should prove remaining total, remaining principal, and remaining charges reconcile from rows, allocations, and ledger entries.
- Payment Plan archive tests should prove archive does not change lifecycle, balance, rows, or history.
- Payment Plan pristine-delete tests should prove only untouched plans can be deleted directly.
- Payment Plan active-delete tests should prove plans with financial activity must be resolved through payment, write-off, reversal, archive, or correction flows.
- Cross-domain tests should prove Debt does not create Payment Plan ledger rows and Payment Plan does not create Debt ledger rows.
- Immutable ledger guardrail tests should remain part of the regression suite for wallet-touching Debt and Payment Plan flows.
- Wallet projection tests should verify balances after create, payment, reversal, correction, and void-style flows.
- Frontend tests should cover user-facing state labels, creation wizard branching, schedule preview behavior, row action availability, and truthful paid versus written-off copy.
- Existing debt action, debt charge ledger, payment plan route, payment plan ledger, payment plan accounting migration, immutable ledger guardrail, wallet projection, and timezone-boundary tests are prior art for this spec.

## Out of Scope

- Rebuilding the whole budget interceptor flow. Payment Plan payment budget errors remain governed by the budget epic.
- Auto-accruing interest in the background.
- Compound interest, grace periods, day-count conventions, holiday shifting, insurance logic, or lender-specific legal amortization parity.
- OCR, bank statement import, screenshot parsing, or automatic schedule import.
- Full asset settlement implementation beyond preserving the Debt ledger vocabulary needed for future work.
- Formal collateral management for standalone Debt.
- Formal loan restructuring actions for standalone Debt.
- A complete UI redesign outside the Debt and Payment Plan flows needed to express this architecture.
- Expected Inflow repayment scheduling changes beyond preserving the existing no-auto-trust separation.
- Production-grade historical compatibility for obsolete development-only Debt status and product-kind data.
- Full database-level immutability constraints for every domain ledger table.
- Reporting and analytics redesign for obligation history.
- Multi-currency obligation accounting beyond preserving existing currency behavior.

## Further Notes

This spec should be implemented as an architecture reset, not as another layer of statuses.

The practical execution order is:

1. Clean Debt status, archive, and taxonomy.
2. Clean Debt creation, ledger entries, payment allocation, and reversal rules.
3. Add explicit Payment Plan schedule models and reviewable schedule creation.
4. Clean Payment Plan row settlement, write-offs, allocation history, and reversal behavior.
5. Reconcile API responses, frontend labels, and tests with the new concepts.

The mental model should stay simple:

- Debt is an open-ended obligation.
- Payment Plan is a scheduled obligation.
- Rows say what is due.
- Allocations say how actions touched rows.
- Ledger entries say what happened.
- Derived fields say where things stand now.

Do not start by inventing more lifecycle states. Start by making the facts sharper.

