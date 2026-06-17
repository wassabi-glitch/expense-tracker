# PRD: G4 - Expected Inflows and Debt Obligation Workflows

Labels: `ready-for-agent`

## Problem Statement

Sarflog can now explain whether a monthly budget plan is backed by real free money, valid spent, explicit expected income, and cash-only obligation reserves. The next weak spot is the quality of the expected inflow and obligation records feeding that math.

Debts owed to the user can look like future money, but open-ended receivables are not reliable cash until the user explicitly decides to plan against them. At the same time, debts the user owes need clearer workflow signals: dated or overdue obligations should be hard warnings, while open-ended debts should produce softer paydown suggestions. Expected inflows also need lifecycle truth. Receiving money should preserve the expectation as `RECEIVED`, with the actual received amount or linked wallet event recorded, instead of deleting or silently mutating the planning row.

## Solution

Treat expected inflows as honest lifecycle records. Debt receivables do not become budget backing automatically. A debt owed to the user can prompt the user to create an explicit expected-payment record, and only that expected-payment record contributes to `/budgets/month-summary` while it remains `EXPECTED`.

Debt payments, income realization, and missed expectations should move records through explicit statuses. The first vertical slice adds the receivable expected-payment seam; later slices complete received/missed lifecycle actions and hard/soft obligation warnings for debts owed by the user.

## User Stories

1. As a budget user, I want open-ended debts owed to me excluded from expected inflows, so that my plan does not trust uncertain paybacks.
2. As a budget user, I want to explicitly add an expected payment for a receivable, so that I can choose when a payback is reliable enough for planning.
3. As a budget user, I want only explicit expected-payment records to increase expected inflow backing, so that debt rows do not create fake budget room.
4. As a budget user, I want a receivable debt to prompt me to add an expected payment, so that I do not forget to decide whether it belongs in the plan.
5. As a budget user, I want expected-payment records linked to the debt they came from, so that the expected inflow explains its source.
6. As a budget user, I want expected payments to keep source income separate from debt payback, so that salary and receivables remain distinguishable.
7. As a budget user, I want receiving an expected inflow to mark the row `RECEIVED`, so that planning history stays auditable.
8. As a budget user, I want received amount stored separately from expected amount, so that over-realization and under-realization are visible.
9. As a budget user, I want a received expected inflow linked to the wallet transaction when possible, so that the plan ties back to ledger truth.
10. As a budget user, I want missed expected inflows to stop contributing to plan backing, so that stale promises do not silently roll forward.
11. As a budget user, I want cancelled expected inflows to remain visible but inactive, so that old assumptions are explainable.
12. As a budget user who owes dated debt, I want a hard warning before the due date, so that required cash obligations are visible.
13. As a budget user with overdue debt, I want stronger overdue warnings, so that obligations do not look optional.
14. As a budget user with open-ended debt, I want soft paydown suggestions, so that optional debt cleanup is encouraged without blocking the plan.
15. As a maintainer, I want G4 to preserve G3 plan backing math, so that expected inflow improvements do not weaken budget correctness.
16. As a maintainer, I want G4 to preserve G2 wallet-backed obligation rules, so that credit cards and overdrafts remain wallet transfer workflows.
17. As a frontend user, I want the same `/budgets/month-summary` contract to explain expected inflow totals, so that dashboards do not need duplicate math.
18. As a tester, I want route-level tests for receivable expected payments, so that future refactors preserve the public behavior.

## Implementation Decisions

- Keep `/budgets/month-summary` as the highest public seam for plan backing.
- Keep `/budgets/expected-incomes` as the expected inflow lifecycle seam and extend it to support debt-linked expected payments.
- Keep `/debts` as the seam that prompts users to explicitly plan receivables instead of auto-trusting debt rows.
- Add debt-linked expected-income fields rather than creating a separate receivable-planning table in the first slice.
- Allow an expected inflow to be linked to either an active income source or an active debt owed to the user.
- Do not auto-create expected-income rows when receivable debts are created.
- Count only `EXPECTED` expected-income rows in plan backing.
- Preserve `RECEIVED`, `MISSED`, and `CANCELLED` rows as lifecycle history.
- Store received amount and linked wallet/financial transaction fields for later realization actions.
- Keep credit-card and overdraft payoff as wallet transfers, not debt-table rows.

## Testing Decisions

- Prefer API-level integration tests through `/debts`, `/budgets/expected-incomes`, and `/budgets/month-summary`.
- Tests should assert behavior the user can observe: workflow warning codes, expected inflow totals, linked expected-payment rows, and plan backing.
- The first tracer bullet should prove a receivable debt does not affect month-summary until an explicit expected-payment row is created.
- Follow-up tests should prove expected inflow realization preserves rows as `RECEIVED` with received amount and linked transaction data.
- Follow-up tests should prove debt obligation warnings differ for dated/overdue debts and open-ended debts.
- Existing budget and debt route tests are the prior art.

## Out of Scope

- Frontend UI for the expected-payment prompt.
- Full timeline/reporting projection work.
- Automatic rollover of missed expected inflows.
- Automatic creation of expected-income rows from debts.
- Credit-card statement reserve UX.
- Payment-plan schedule redesign.
- Month-scoped subcategory architecture.

## Further Notes

This PRD implements G4 from `docs/EC_IMPLEMENTATION_PLAN.md` and is grounded in EC-129, EC-130, EC-131, and EC-132. It builds on completed G3 budget backing math and preserves the G2 decision that wallet-backed obligations are not duplicated as debt rows.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
