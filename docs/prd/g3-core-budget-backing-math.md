# PRD: G3 - Core Budget Backing Math

Labels: `ready-for-agent`

## Problem Statement

Sarflog already separates wallet reality from budget plans, but the core budget backing math still compares total monthly limits directly against current free money plus expected income. That creates false `Over-Planned` alerts after normal spending: when a user spends within a category limit, cash leaves the wallet, but the remaining plan should not become less covered simply because expected spending happened.

The plan also needs a stable foundation for later debt floors, cash-only obligation reserves, recurring floors, and project shortfalls. Without a centralized backing calculation, future agents will keep patching plan status in separate places and risk counting credit-card float, protected goal money, or financing mechanisms as real budget capacity.

## Solution

Centralize budget plan-capacity math around effective backing.

For each budgeted category, only spending up to that category's effective limit counts as valid budget spent. Valid spent is added back to free money because it represents already-executed spending that was covered by the monthly plan. Spending past the limit, or spending without budget room, does not get added back and therefore reduces backing for the rest of the plan.

The core formula is:

```text
valid_budget_spent = min(category_spent, category_limit)
effective_backing = free_money_now + expected_inflows + total_valid_budget_spent - applicable_cash_obligation_reserves
plan_status = Covered unless total_limits > effective_backing
```

The first implementation pass keeps current expected-income records as the expected inflow source, keeps cash-obligation reserves at zero until the debt-reserve workflow exists, and preserves G2's rule that credit cards and overdrafts are wallet-backed liabilities rather than budget capacity.

## User Stories

1. As a budget user, I want normal in-limit spending to keep my monthly plan status stable, so that Sarflog does not panic after I follow my plan.
2. As a budget user, I want overspending to reduce plan backing, so that the app shows when one category has stolen cash from the rest of the month.
3. As a budget user, I want unbudgeted spending to reduce plan backing, so that unplanned purchases make the plan visibly tighter.
4. As a salary-timing user, I want expected income to help classify whether the plan can work later, so that plans can say `Waiting on income` without pretending money is spendable today.
5. As a goal user, I want protected goal money excluded from free money, so that funding a goal reduces the cash available for monthly budgets.
6. As a credit-card user, I want credit limit and negative card balances excluded from free money, so that borrowed payment capacity does not become fake wealth.
7. As an overdraft user, I want overdraft capacity excluded from free money, so that borrowed cash access does not make the budget healthier.
8. As a maintainer, I want budget create and update validation to use the same backing calculation as month summary, so that route behavior and dashboard status cannot disagree.
9. As a planner, I want category-linked debts to become minimum category limits later, so that required installment/debt spending is visible in the relevant category.
10. As a cash-debt user, I want future cash-only debts to warn or reserve cash explicitly, so that obligations do not silently reduce every category.
11. As a recurring-expense user, I want recurring bills to become category floors later, so that budget setup knows about required monthly spending.
12. As a frontend user, I want plan-health numbers to keep their current language, so that `Over-Planned`, `Waiting on income`, and covered statuses stay understandable.
13. As a future G4 implementer, I want expected inflow handling to have a clear seam, so that receivables and liquidity loans can be added without rewriting budget status.
14. As a future G5 implementer, I want parent category leakage to be correct before month-scoped subcategory limits arrive, so that subcategory overspend can roll up predictably.
15. As a future G8 implementer, I want expense save to record reality even when plans break, so that warnings and repair actions can happen after ledger truth is saved.
16. As a tester, I want route-level tests around plan backing behavior, so that future refactors preserve observable budget semantics.

## Implementation Decisions

- Keep `/budgets/month-summary` as the highest public seam for plan-health behavior.
- Keep budget create, budget update, and lazy budget materialization using the shared capacity check.
- Introduce a shared plan-capacity computation in the budget service rather than duplicating formulas in route handlers.
- Compute valid budget spent per budget computation as `min(max(spent, 0), max(effective_limit, 0))`.
- Use effective monthly limits, not raw base monthly limits, for plan-capacity comparisons.
- Keep current expected-income rows as the only expected inflow source in this slice.
- Keep applicable cash-obligation reserves at zero until explicit reserve workflows exist.
- Preserve the existing free-money rule: positive owned asset wallets only, after protected goal money, excluding credit wallets, negative balances, and available credit or overdraft limits.
- Preserve G2 source-of-truth rules: credit-card and overdraft payoff is a wallet transfer, not a debt-table payment or expense category.
- Do not block expense save as part of the first G3 slice; existing hard budget-limit guards are tracked as a later G3/G8 behavior change.

## Testing Decisions

- Prefer API-level integration tests through `/budgets/month-summary`, `/budgets/`, and budget update endpoints.
- Tests should assert user-observable behavior: plan status, backing totals, remaining/gap fields, and rejection payloads.
- The first tracer bullet should prove normal in-limit spending keeps plan status stable.
- Follow-up tests should prove overspending and unbudgeted spending reduce effective backing.
- Existing `tests/test_budget.py` month-summary and capacity tests are the prior art.
- Focused tests should avoid full `tests/test_expenses.py` because local Redis-only rate-limit coverage is known to be environment-sensitive.

## Out of Scope

- Building the full expected inflow model for receivables, refunds, loans, or asset sales.
- Adding debt-funded-plan flags.
- Adding explicit cash-obligation reserve workflows.
- Adding category-linked debt or recurring-expense floors.
- Implementing month-scoped subcategory limit tables.
- Changing budget UI repair actions after an over-budget expense.
- Implementing credit-card statement reserve UX.
- Removing rollover infrastructure.
- Adding 50/30/20 reporting.

## Further Notes

This PRD implements G3 from `docs/EC_IMPLEMENTATION_PLAN.md` and is grounded in EC-109, EC-115, EC-127, EC-128, EC-131, and EC-135. It preserves the completed G2 decisions: financing mechanism is not an expense category, and credit-card or overdraft obligations are wallet-backed liabilities.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
