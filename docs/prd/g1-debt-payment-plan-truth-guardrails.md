# PRD: G1 - Debt and Payment-Plan Truth Guardrails

Labels: `ready-for-agent`

## Problem Statement

Sarflog already has a serious debt, payment-plan, wallet, and ledger model, but some generic CRUD paths can still mutate obligation truth too broadly.

For regular debts, generic update and delete operations can bypass the explicit debt action model after real activity exists. For payment plans, setup fields and delete behavior need lifecycle-aware boundaries because a plan owns a linked debt, payment schedule, wallet events, and possible goal dependencies. For payment-plan payments, regular debt reversal is correctly blocked, but the replacement plan-owned undo path is missing.

If these guardrails are incomplete, users can accidentally destroy the story of a debt or payment plan while the app still displays clean-looking balances.

## Solution

Harden debt and payment-plan workflows so finalized obligation history evolves through explicit domain actions, not silent row mutation.

Regular debt generic update should be limited to safe metadata. Opening amount and setup correction should only be allowed while pristine. Status changes should use explicit actions such as payment, forgiveness, settlement, archive, and restore. Deletion should be available only for pristine records created by mistake.

Payment plans should allow safe details edits, but financial setup and schedule shape should be editable only before real activity. After activity, changes must use payment, charge, write-off, undo, correction, reschedule, settlement, or archive actions. Payment-plan payment reversal should be owned by the payment-plan layer so schedule rows, debt ledger, wallet ledger, financial events, and dependencies stay reconciled.

Debt and payment-plan detail views should present audit history as oldest-to-newest storylines, with reversal/undo actions shown only where the owning domain can safely perform them.

## User Stories

1. As a debt user, I want regular debt balances to change through explicit actions, so that I understand why the balance changed.
2. As a debt user, I want generic debt edits to be limited after history exists, so that I do not erase payment or correction history by accident.
3. As a debt user, I want to correct an opening amount only before real activity exists, so that setup mistakes can still be fixed safely.
4. As a debt user, I want paid, forgiven, settled, archived, and restored states to use explicit actions, so that status changes tell a clear financial story.
5. As a debt user, I want non-pristine debt deletion blocked, so that recorded obligations do not disappear silently.
6. As a debt user, I want pristine debt deletion to remain possible, so that mistaken setup records can be removed before they become financial history.
7. As a debt user, I want payment-plan-managed debts protected from regular debt mutation routes, so that the plan schedule and linked debt do not drift apart.
8. As a payment-plan user, I want to edit safe display details without rewriting financial history, so that I can fix names or labels without changing balances.
9. As a payment-plan user, I want setup fields to lock after payments, fees, write-offs, or goal dependencies exist, so that schedule truth remains stable.
10. As a payment-plan user, I want delete to be available only before real activity exists, so that deleting a plan does not erase wallet or schedule history.
11. As a payment-plan user, I want closed plans to be archived instead of deleted, so that old obligations remain available for audit.
12. As a payment-plan user, I want an Undo payment action owned by the payment plan, so that schedule rows and debt balance are restored together.
13. As a payment-plan user, I want payment undo to update wallet balances only when that matches real life, so that app wallet reality stays honest.
14. As a payment-plan user, I want older payment undo blocked until newer dependent payments are undone, so that schedule order remains coherent.
15. As a debt user, I want reversal warnings to explain real-wallet consequences, so that I choose the correct action when money really moved.
16. As a debt user, I want forgiveness, settlement, charge, and correction actions instead of misusing reverse, so that each real-world event is represented honestly.
17. As a goal user, I want debt/payment-plan reversals to respect linked goal funding, so that protected goal money is not corrupted.
18. As a wallet user, I want every reversal that affects wallet money to be audit-preserving, so that balances can be traced.
19. As a tester, I want pristine and non-pristine paths covered through public API routes, so that guardrails cannot regress.
20. As a maintainer, I want debt and payment-plan details to use one storyline model, so that future UI work does not reintroduce inconsistent audit ordering.
21. As a support/debugging user, I want business date and recorded timestamp kept distinct in activity views, so that I can reconstruct what happened.
22. As a future agent, I want G1 to stop at guardrails and reversal safety, so that later budget math, category cleanup, and dashboard intelligence remain separate.

## Implementation Decisions

- Treat regular debt as an obligation timeline, not a freely editable row.
- Generic regular debt update may change safe metadata such as counterparty name, description, date, expected return date, and safe display/planning labels when policy permits.
- Generic regular debt update must not set debt status. Paid status remains automatic. Forgiven, settled, archived, and restored states use explicit action routes.
- Opening amount correction is allowed only while the debt is pristine.
- A pristine debt has only its original creation state and no payments, charges, forgiveness, settlement, balance correction, reversals, linked funded goal dependency, or payment-plan manager.
- Regular debt delete is allowed only while pristine. Non-pristine debt should be reversed, corrected, settled, forgiven, or archived.
- Payment-plan-managed debts remain blocked from regular mutating debt routes unless the payment-plan route explicitly owns the operation.
- Payment plan setup fields are lifecycle-locked after real activity. Safe metadata remains editable while the plan is not archived.
- Payment-plan delete is allowed only while pristine. Non-pristine plans use archive or future restructure actions.
- Payment-plan payment reversal is a plan-owned action, not generic debt ledger reversal.
- Payment-plan payment reversal v1 should operate on the latest payment operation only.
- Payment-plan payment reversal must restore schedule rows, debt ledger state, financial event/wallet effects, and plan/debt remaining balances together, or block with a clear reason.
- Reversal copy must say that undo changes app wallet balance and is only appropriate when the real payment failed, was cancelled, refunded, or was recorded by mistake.
- Debt and payment-plan detail activity should render oldest-to-newest as a storyline. Feed/list previews may remain newest-first.
- G1 does not change category taxonomy, budget backing math, debt expected-inflow planning, credit-card source of truth, or expense-save behavior.

## Testing Decisions

- Tests should use public API routes and existing integration-style route tests where possible.
- Regular debt CRUD guardrails should be covered in debt route tests by creating debts, recording activity, then attempting generic update/delete.
- Debt policy unit tests can cover reusable pristine/non-pristine decision helpers when route tests would be too broad.
- Payment-plan lifecycle guardrails should be covered in installment route tests by creating a plan, recording payment/charge/write-off activity, then attempting setup update/delete.
- Payment-plan reversal should be covered through the payment-plan route, not regular debt reversal.
- Reversal tests should assert observable effects: wallet balance, payment row status/amount, debt remaining amount, plan remaining amount, ledger reversal, and blocked older reversal.
- UI/storyline tests should focus on externally visible ordering/copy where the frontend test harness exists; otherwise build/check plus targeted component-level assertions can be added later.

## Out of Scope

- Reworking budget backing math.
- Deprecating or migrating `INSTALLMENTS_DEBT`.
- Combining credit-card negative wallets into the Debts UI.
- Adding expected inflow prompts for debts owed to the user.
- Implementing full payment-plan restructure/reschedule workflows.
- Supporting arbitrary older payment-plan reversal with complex reallocation.
- Reworking all debt/payment-plan visual design beyond storyline ordering and action visibility.
- Changing ordinary expense save behavior.

## Further Notes

This PRD implements EC-047 through EC-051 from the edge-case log. It should land before category cleanup and budget math work because later slices depend on debt/payment-plan history being trustworthy.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
