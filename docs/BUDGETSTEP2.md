# Budget Step 2 Plan

Date: 2026-06-07

This plan starts Step 2 as a domain/product pass before implementation. It is based on `docs/PRODUCT.md` and the current backend/frontend audit.

## Product Position

Budgets in Sarflog are monthly spending limits.

They are not wallet-backed. They are not envelopes. They do not reserve cash. They do not create spendable money.

The Step 2 budget work should make the product answer:

```text
Can I pay?       Wallets, credit, overdraft
Should I spend? Monthly budget limits and subcategory limits
What changed?   Goals, debts, projects, refunds, wallet reality
```

## Current Audit

Current backend strengths:

- `app/services/budget_service.py` already treats expenses and refunds as signed budget impact.
- `get_budget_spent_by_id`, `get_budget_detail`, and subcategory spend calculations already exclude isolated project spending.
- Goal planned purchases and goal purchases achieved outside reserved funds are already excluded from normal monthly budget usage.
- Tests already protect goal-funded planned purchase exclusion in `tests/test_goals.py`.
- Session finalization already skips normal monthly budget resolution for isolated project items.

Current backend gaps:

- Quick expense posting still resolves a normal monthly budget before project context can exempt isolated projects.
- `app/routers/analytics.py` still computes this-month stats with older category-threshold logic and does not use the same budget impact filters as `budget_service`.
- `app/utils.py::check_budget_alerts` also uses older spend calculation and can disagree with budget service rules.
- Budget health is currently per-category usage status: `On Track`, `Warning`, `High Risk`, `Over Limit`.
- There is no month-level budget plan health status based on free money now.
- Schema/model fields still expose envelope-era concepts: `max_envelope_balance`, `sweep_target_goal_id`, `sweep_amount`.
- `sweep_target_goal_id` is already rejected on create/update, but the compatibility fields still exist.

Current frontend strengths:

- `frontend/src/features/budgets/Budgets.jsx` already shows current month vs history, filters, category cards, subcategories, and project signals.
- It already distinguishes isolated projects from overlay projects in several places.
- It already uses URL filters for category/status/month/sort.

Current frontend gaps:

- The page still uses envelope language in copy.
- The top summary is based on visible rows, not a true month-level plan health model.
- Project management is mixed into the Budgets page. This can stay for now, but it must not drive the Step 2 budget rules.
- UI statuses still describe category usage risk only; they do not explain whether the whole monthly plan is covered by free money now.

## Step 2 Decisions

1. Budgets remain category/month rows.

   A budget row means: "The user permits up to this amount of monthly spending in this category."

2. Normal expenses hit monthly budgets.

   A normal expense must resolve a monthly category budget and consume that category's monthly limit.

3. Refunds reduce budget usage.

   A refund linked to a budgeted expense reduces the signed usage for that same budget.

4. Goal-funded spending does not hit normal monthly budgets.

   Goal planned purchases, reserve use, and goal-funded project spending should stay categorized for analytics, but should not consume normal monthly category room.

5. Overlay project expenses hit monthly budgets.

   Overlay projects are reporting/planning lenses on top of monthly categories.

6. Isolated project expenses do not hit monthly budgets.

   Isolated project expenses should not require a normal monthly category budget just to be recorded.

7. Credit and overdraft do not create budget room.

   Spending paid by borrowed capacity can still hit the category budget, but credit limit and overdraft limit must not increase plan capacity.

8. Expected income is deferred.

   Do not use expected income in Step 2 implementation. Do not allocate future salary into budgets.

9. Known promises are deferred unless already implemented.

   Do not subtract debt due, installment due, required bills, or scheduled goal contributions in the first Step 2 slice.

10. Rollover remains permission, not cash.

   Existing rollover behavior may stay, but UI copy must describe it as carried spending permission. It must not read as money or envelope balance.

11. Subcategories remain budget lanes, not envelopes.

   Subcategory limits split a parent category's monthly permission. Subcategory leftover is not money and cannot fund goals.

12. Project behavior is mostly deferred.

   Preserve existing overlay/isolated/project-funded behavior. Do not redesign Fund Project goals during Step 2.

## First Implementation Slice

### Slice 2.1: Centralize Budget Impact Rules

Goal: every backend budget view, alert, and stats endpoint should agree on what counts against normal monthly budgets.

Implement one shared budget-impact query layer in `app/services/budget_service.py` and reuse it from:

- `get_budget_spent_by_id`
- `get_budget_detail`
- `get_subcategory_spent_for_month`
- `validate_budget_limit`
- `validate_subcategory_limit`
- `app/routers/analytics.py::get_this_month_stats`
- `app/utils.py::check_budget_alerts`

Rules for this shared layer:

- Include posted `EXPENSE` as positive spend.
- Include posted `REFUND` as negative spend.
- Include normal expenses.
- Include overlay project expenses.
- Exclude isolated project expenses.
- Exclude goal-funded / goal-completion references that are already excluded by `budget_service`.
- Do not include credit repayments as category spend.
- Do not include asset sale income, debt inflows, wallet corrections, or transfers.

Expected tests:

- Normal expense increases budget spent.
- Refund decreases budget spent and alerts/stats follow the same number.
- Planned purchase stays categorized but does not change budget spent.
- Isolated project expense does not change monthly budget spent.
- Overlay project expense does change monthly budget spent.
- Analytics this-month stats match `/budgets/item` for the same category.
- Budget alerts use the same signed, filtered spend as `/budgets/item`.

### Slice 2.2: Fix Isolated Project Budget Requirement

Goal: isolated project expenses should not require a normal monthly budget.

Current issue:

- `post_expense_event` resolves a monthly budget before the isolated project exemption is applied.
- Session finalization already handles isolated projects better by allowing `budget_id = null`.

Change:

- Validate project/subcategory links before resolving a monthly budget.
- If `project.is_isolated` is true:
  - do not call `resolve_expense_budget`
  - do not call `validate_budget_limit`
  - do not call `validate_subcategory_limit` for monthly subcategories
  - store `EntityLedger.budget_id = null`
  - still validate project total/category/subcategory limits
- If project is missing or overlay:
  - keep existing monthly budget requirement
  - keep monthly category/subcategory validation

Expected tests:

- Isolated project expense can be created without a monthly budget.
- Overlay project expense still requires a monthly budget.
- Normal expense still requires a monthly budget.
- Isolated project expense appears in project budget summaries.
- Isolated project expense does not appear in monthly budget detail activity.

### Slice 2.3: Add Month-Level Budget Plan Summary

Goal: the Budgets page needs a true plan health layer, not only category progress cards.

Add a backend endpoint, proposed:

```text
GET /budgets/month-summary?budget_year=YYYY&budget_month=M
```

Response shape should include:

```text
budget_year
budget_month
owned_money_now
protected_goal_money
free_money_now
monthly_budget_limit_total
monthly_effective_limit_total
normal_budget_spent
normal_budget_remaining
plan_free_money_remaining
plan_status
categories_over_limit
categories_close_to_limit
borrowing_pressure
```

Initial status rules, with expected income deferred:

```text
if monthly_effective_limit_total < free_money_now:
    plan_status = "covered_with_cushion"
elif monthly_effective_limit_total == free_money_now:
    plan_status = "covered_no_cushion"
else:
    plan_status = "over_planned"
```

Borrowing pressure is a separate signal, not budget room:

```text
borrowing_pressure = true
```

when current-month budgeted spending was paid by credit/liability wallets or pushed an overdraft-backed wallet below zero.

Free money now calculation:

```text
owned_money_now =
sum positive active wallet balances for owned asset wallets

protected_goal_money =
active unreleased goal allocations

free_money_now =
max(owned_money_now - protected_goal_money, 0)
```

Do not include:

- credit limit
- overdraft limit
- liability wallet balances as positive capacity
- expected income
- future debt receivables

Expected tests:

- Positive asset wallet balance contributes to owned money.
- Credit limit does not contribute to free money now.
- Overdraft limit does not contribute to free money now.
- Protected goal money reduces free money now.
- Plan status becomes `covered_with_cushion`, `covered_no_cushion`, or `over_planned`.

### Slice 2.4: Budgets UI Language Pass

Goal: remove envelope mental model from the Budgets page.

Replace language:

```text
Envelope cards -> Budget cards
Effective envelope space -> Effective monthly permission
Available space -> Available budget room
Monthly envelopes -> Monthly budgets
```

Preferred page language:

```text
Monthly spending limits
Budget room
Free money now
Protected for goals
Covered with cushion
Covered, no cushion
Over-Planned
Borrowing pressure
Rollover permission
```

Avoid:

```text
Envelope balance
Budget cash
Budget money
Transfer budget money
Allocate salary
Credit-backed budget
```

UI changes:

- Add top summary cards for month-level plan health:
  - Free money now
  - Monthly budget total
  - Budget room after plan
  - Plan status
- Keep category cards focused on category usage:
  - limit
  - spent
  - remaining permission
  - over/close-to-limit status
- Keep Projects section for now, but make it secondary and avoid making Step 2 depend on project redesign.
- Keep current filters unless they conflict with the new status model.

### Slice 2.5: Subcategory Rule Cleanup

Goal: make subcategories clearly behave as lanes inside parent category limits.

First pass decision:

- Do not add a new per-month subcategory limit table yet.
- Keep `UserSubcategory` as the reusable category lane.
- Treat `monthly_limit` as the active monthly lane limit for that category.
- Ensure create/update validates total active subcategory limits against the relevant parent monthly budget.
- UI should say "subcategory lane" or "monthly lane limit", not envelope.

Later migration option:

- If monthly-varying subcategory limits become necessary, add a `budget_subcategory_limits` table keyed by budget/month/subcategory.
- Do not do that in the first Step 2 implementation slice.

Expected tests:

- Subcategory total cannot exceed parent category limit.
- Expense with subcategory hits parent category and subcategory.
- Expense without subcategory hits parent category only.
- Goal-funded purchase with subcategory does not consume subcategory monthly usage.
- Isolated project local subcategories remain project-local and do not affect monthly subcategories.

## Deferred Work

Expected income:

- Do not include in Step 2 first implementation.
- Later, it can classify a plan as `waiting_on_income`, but it must not allocate future salary.

Known promises:

- Do not subtract debt payments, installments, bills, or scheduled goal contributions until those commitments are explicit and stable.

Fund Project goals:

- Keep for Step 3.
- Step 2 only preserves the rule that goal-funded/isolated project spending does not double-hit normal monthly budgets.

Rollover redesign:

- Do not remove rollover.
- Do not treat rollover as money.
- Rename UI copy first; deeper rollover health checks can come later.

Schema cleanup:

- Do not break existing API fields immediately.
- Hide or stop using envelope/sweep fields in UI.
- Later migration can rename or deprecate `max_envelope_balance`, `sweep_target_goal_id`, and `sweep_amount`.

## Recommended Execution Order

1. Add shared backend budget-impact helpers and align alerts/stats with budget service.
2. Fix isolated project quick expense behavior.
3. Add `/budgets/month-summary`.
4. Add backend tests for every invariant above.
5. Update Budgets frontend to consume month summary.
6. Replace envelope language in Budgets UI and `en.json`.
7. Run Docker verification:

```text
docker compose exec -T api pytest -q tests/test_budget.py tests/test_budget_alerts.py
docker compose exec -T api pytest -q tests/test_goals.py::test_planned_purchase_is_categorized_but_excluded_from_normal_monthly_budget
docker compose exec -T api pytest -q tests/test_goals.py::test_planned_purchase_achieved_outside_reserved_funds_is_excluded_from_normal_monthly_budget
docker compose exec -T frontend npm run build
```

## Acceptance Criteria

Step 2 is done when:

- Budgets page no longer presents budgets as envelopes or money.
- Normal expenses, refunds, goal-funded purchases, overlay projects, and isolated projects all have clear budget impact rules.
- `/budgets/`, `/budgets/item`, `/budgets/item/detail`, analytics this-month stats, and budget alerts agree on spending numbers.
- The Budgets page shows month-level plan health based on free money now.
- Credit/overdraft does not increase budget room.
- Expected income remains out of the implementation.
- Fund Project goals are not redesigned during this step.
