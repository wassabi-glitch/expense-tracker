# Issues: G3 - Core Budget Backing Math

Parent PRD: `docs/prd/g3-core-budget-backing-math.md`

Publish label: `ready-for-agent`

## Proposed Breakdown

1. **Stabilize plan status with valid budget spent**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-4, 8, 12, 16

2. **Let overspending leak out to global plan backing**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 2-3, 14-16

3. **Preserve goal funding as protected money in plan capacity**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 5, 8, 16

4. **Keep credit-card float out of planning wealth**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 6-8, 16

5. **Introduce category floors for linked obligations**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 9, 11, 14

6. **Add explicit reserve seam for cash-only obligations**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 10, 13

7. **Relax expense save into warn-after-ledger behavior**
   - Type: AFK
   - Blocked by: Issue 2
   - User stories covered: 15-16

## Issue 1: Stabilize Plan Status With Valid Budget Spent

## What to build

Make budget month plan health use valid budget spent when deciding whether the plan is covered, waiting on income, or over-planned. Normal spending that stays within a category's effective limit should not make the global plan status worse just because the user's wallet balance went down.

This slice should centralize the capacity calculation used by month summary and budget create/update validation, while keeping expected income, goal protection, and credit-card exclusion behavior intact.

## Acceptance criteria

- [x] `/budgets/month-summary` computes effective backing as free money now plus expected income plus total valid budget spent.
- [x] Valid budget spent is capped per category at that category's effective monthly limit.
- [x] In-limit spending keeps a previously covered plan covered.
- [x] Budget create/update validation uses the same effective backing calculation.
- [x] Existing expected-income statuses remain distinct: covered, covered with no cushion, waiting on income, and over-planned.
- [x] Existing G2 debt/wallet source-of-truth tests still pass.

## Blocked by

None - can start immediately.

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_budget_month_summary_valid_budget_spent_keeps_in_limit_plan_covered -q`
- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_budget_month_summary_uses_free_money_not_credit_or_overdraft tests\\test_budget.py::test_create_budget_rejects_plan_above_free_money_without_expected_income tests\\test_budget.py::test_expected_income_allows_waiting_on_income_status tests\\test_budget.py::test_expected_income_status_change_can_make_existing_plan_over_planned -q`
- `.\\venv\\Scripts\\pytest -q tests\\test_debts.py::test_debt_list_projects_negative_wallet_obligations_without_debt_rows tests\\test_debts.py::test_credit_wallet_obligation_payoff_uses_transfer_with_fee_not_debt_payment tests\\test_debts.py::test_overdraft_wallet_obligation_payoff_uses_transfer_not_expense -q`

## Progress

- RED: `tests/test_budget.py::test_budget_month_summary_valid_budget_spent_keeps_in_limit_plan_covered` failed because month summary did not expose or apply `valid_budget_spent`.
- GREEN: budget plan capacity now centralizes effective backing as cash-backed valid budget spent plus free money plus expected income, and month summary exposes `valid_budget_spent`.
- GREEN: budget create validation accepts new limits that fit after cash-backed valid spending is counted.
- GREEN: pure credit-card spend still does not become valid backing; it remains borrowing pressure and does not create fake wealth.

## Issue 2: Let Overspending Leak Out To Global Plan Backing

## What to build

Make category overspending reduce global plan backing instead of pretending every spent som is still valid budget usage. Spending up to the category's effective limit remains valid spent; spending above that limit leaks out and reduces the backing available for the rest of the monthly plan.

This slice focuses on the centralized month-summary/capacity math. Relaxing normal expense entry so users can intentionally save over-budget expenses remains Issue 7.

## Acceptance criteria

- [x] Valid budget spent is capped at each category's effective monthly limit.
- [x] Category spending beyond the effective limit is excluded from valid budget spent.
- [x] Overspending can make the global plan `over_planned`.
- [x] Month summary reports the resulting `backing_shortfall`, cash gap, and over-limit category count.
- [x] Existing create/update backing checks still use the centralized capacity calculation.

## Blocked by

- Issue 1: Stabilize plan status with valid budget spent

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_budget_month_summary_overspending_leaks_out_of_global_backing -q`

## Progress

- GREEN: seeded over-limit ledger reality shows only the in-limit portion as `valid_budget_spent`; the excess reduces `backing_total` and turns the month `over_planned`.

## Issue 3: Preserve Goal Funding As Protected Money In Plan Capacity

## What to build

Ensure protected goal money remains excluded from budget plan capacity even after normal valid budget spending is added back. Goal funding locks real money away from monthly spending; valid spent must not accidentally re-open that protected cash as budget room.

## Acceptance criteria

- [x] Protected goal allocations continue to reduce `free_money_now`.
- [x] Valid budget spent adds back only executed monthly spending, not protected goal money.
- [x] A plan that exactly fits after goal protection remains `covered_no_cushion`.
- [x] Creating extra budget room beyond protected backing is rejected.

## Blocked by

- Issue 1: Stabilize plan status with valid budget spent

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_budget_plan_capacity_keeps_goal_money_protected_after_valid_spend -q`

## Progress

- GREEN: month summary keeps goal money protected after cash-backed budget spending, and budget creation rejects limits that would rely on protected goal funds.

## Issue 4: Keep Credit-Card Float Out Of Planning Wealth

## What to build

Prevent credit-card float from becoming fake plan backing. Credit-card spending should still hit category spending and borrowing pressure, but only the cash-backed portion of a mixed payment should be added back as valid budget spent.

## Acceptance criteria

- [x] Pure credit-card budget spending does not add valid backing.
- [x] Mixed cash/credit spending is prorated so only the cash-backed share becomes valid budget spent.
- [x] Borrowed card portions cannot justify additional budget creation.
- [x] Borrowing pressure remains visible when budgeted spending uses credit.
- [x] G2 wallet-backed obligation invariants remain green.

## Blocked by

- Issue 1: Stabilize plan status with valid budget spent

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_budget_plan_capacity_prorates_mixed_cash_and_credit_spending tests\\test_budget.py::test_budget_month_summary_reports_over_planned_and_borrowing_pressure -q`
- `.\\venv\\Scripts\\pytest -q tests\\test_debts.py::test_debt_list_projects_negative_wallet_obligations_without_debt_rows tests\\test_debts.py::test_credit_wallet_obligation_payoff_uses_transfer_with_fee_not_debt_payment tests\\test_debts.py::test_overdraft_wallet_obligation_payoff_uses_transfer_not_expense -q`

## Progress

- RED: mixed cash/credit spending counted the full expense as `valid_budget_spent` because the service only checked whether an event had any cash wallet leg.
- GREEN: cash-backed budget spend is prorated by event wallet allocation, so card-funded portions remain borrowing pressure without increasing plan backing.

## Issue 5: Introduce Category Floors For Linked Obligations

## What to build

Expose required category floors in the budget month summary without subtracting them globally from plan capacity. Recurring expenses, pending payment-plan/installment principal, and dated category-linked debts should show the minimum category room the planner needs for the month. If the category budget is below that floor, the summary reports a category-level shortfall.

## Acceptance criteria

- [x] Active recurring expenses due in the month contribute to the matching category floor.
- [x] Pending/partial installment principal due in the month contributes to the plan's real purchase category floor.
- [x] Pending/partial installment charges due in the month contribute to `Debt Charges`.
- [x] Dated category-linked debts owed by the user contribute to their real expense category floor.
- [x] Category floors report floor amount, effective limit, shortfall, and source labels.
- [x] Category floors do not blindly subtract from global backing.

## Blocked by

- Issue 1: Stabilize plan status with valid budget spent

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_budget_month_summary_reports_category_obligation_floors_without_global_subtraction -q`

## Progress

- GREEN: `/budgets/month-summary` now returns `category_floors`, `category_floor_total`, and `category_floor_shortfall` for recurring, installment, and category-linked debt floors.

## Issue 6: Add Explicit Reserve Seam For Cash-Only Obligations

## What to build

Add a computed reserve seam for dated cash-only debts owed by the user. Cash-only debts are wallet drainers rather than category spending, so they reduce plan backing directly through `cash_obligation_reserve_total`.

## Acceptance criteria

- [x] Dated cash-borrowed debts owed by the user contribute to `cash_obligation_reserve_total`.
- [x] Informal cash debt products due in the month contribute to `cash_obligation_reserve_total`.
- [x] Cash obligation reserves reduce cash backing and total backing.
- [x] Existing budget plans can become `over_planned` when a cash-only obligation appears.
- [x] Budget create/update validation includes the reserve amount in rejection details.

## Blocked by

- Issue 1: Stabilize plan status with valid budget spent

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_budget_month_summary_reserves_cash_only_debt_from_plan_backing -q`

## Progress

- GREEN: cash-only debt reserves now reduce effective backing and surface in month-summary plus capacity rejection payloads.

## Issue 7: Relax Expense Save Into Warn-After-Ledger Behavior

## What to build

Stop hard-blocking ordinary expense save when category or subcategory limits would go red. Ledger truth should be recorded first; budget state should then show over-limit and global backing effects. Project budget validation remains separate and still applies.

## Acceptance criteria

- [x] Ordinary over-budget expense creation succeeds.
- [x] The affected budget records actual spend and becomes over-limit.
- [x] Month summary reflects only in-limit spending as valid budget spent.
- [x] Overspending can turn a fully allocated plan `over_planned`.
- [x] Session draft finalization and split editing no longer call monthly category/subcategory hard-stop validators.
- [x] Existing goal-funded planned purchase behavior still distinguishes goal-funded spending from normal monthly budget spending.

## Blocked by

- Issue 2: Let overspending leak out to global plan backing

## Suggested verification

- `.\\venv\\Scripts\\pytest -q tests\\test_budget.py::test_over_budget_expense_save_records_reality_and_turns_plan_over_planned tests\\test_goals.py::test_unplanned_purchase_still_counts_against_monthly_budget_without_blocking_save -q`

## Progress

- RED: legacy goal test expected `budgets.limit_exceeded` for an ordinary over-budget purchase.
- GREEN: ordinary over-budget expense save now returns `201`, updates budget spend/over-limit state, and month summary turns `over_planned` when the rest of the plan was fully backed.
