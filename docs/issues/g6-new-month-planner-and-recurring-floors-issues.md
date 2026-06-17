# Issues: G6 - New Month Planner and Recurring Floors

Parent PRD: `docs/prd/g6-new-month-planner-and-recurring-floors.md`

Publish label: `ready-for-agent`

## Proposed Breakdown

1. **Stop automatic rollover effects in v1**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1, 4, 15-16

2. **Preview explicit month setup modes**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 2-9, 15-16

3. **Apply copy and smart auto-fill setup**
   - Type: AFK
   - Blocked by: Issues 1-2
   - User stories covered: 3-11, 15-16

4. **Complete payable-debt and recurring floor coverage**
   - Type: AFK
   - Blocked by: Issue 2
   - User stories covered: 5-8, 15-16

5. **Expose recurring default cost projections**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 12-13, 15-16

6. **Save custom recurring projection horizons and wire UI**
   - Type: HITL
   - Blocked by: Issue 5
   - User stories covered: 12-16

## Issue 1: Stop Automatic Rollover Effects In V1

## What to build

Unused budget room should not automatically carry into a later month. Recomputing a budget chain should leave next-month effective limits equal to explicit monthly limits, so savings return to unallocated capacity until the user makes a new intentional plan.

## Acceptance criteria

- [x] A prior month with unspent budget room does not create rollover/cap-trim/sweep effects in the next month.
- [x] Month summary for the next month reports effective limits equal to explicit monthly limits.
- [x] Existing budget backing math still reports over-planned states through G3 calculations.
- [x] The behavior does not depend on premium status or the legacy rollover preference.

## Blocked by

None - can start immediately.

## Progress

- RED: `tests/test_budget.py::test_get_budgets_does_not_auto_rollover_unused_room_in_v1` failed because a premium user still received a 100-unit automatic rollover.
- GREEN: budget chain recomputation now clears legacy budget ledger effects and does not create new rollover/cap-trim/sweep effects in v1.
- GREEN: Focused Docker test passed.

## Issue 2: Preview Explicit Month Setup Modes

## What to build

Budget setup should expose a read-only pre-flight preview for `PLAN_FROM_SCRATCH`, `COPY_PREVIOUS_MONTH`, and `SMART_AUTO_FILL`. The preview should use the user's effective timezone, G3 month backing math, G4 expected inflows and cash reserves, and G3/G6 category floors.

## Acceptance criteria

- [x] Plan-from-scratch preview proposes zero category limits and does not create budget rows.
- [x] Copy-previous preview proposes previous-month parent limits and copied month-scoped subcategory limits.
- [x] Smart auto-fill preview proposes copied parent limits raised to at least category floor amounts.
- [x] Preview includes pre-flight totals and status from existing month-summary math.
- [x] Preview distinguishes category floors from cash-only reserve pressure.

## Blocked by

- Issue 1: Stop automatic rollover effects in v1

## Progress

- RED: `tests/test_budget.py::test_month_setup_preview_modes_are_read_only_and_show_floor_repair` failed because `/budgets/month-setup/preview` did not exist.
- GREEN: month setup preview now returns read-only category proposals for plan from scratch, copy previous month, and smart auto-fill.
- GREEN: Preview reuses existing G3/G4/G5 math through month summary and category floor builders.
- GREEN: Focused Docker test passed.

## Issue 3: Apply Copy And Smart Auto-Fill Setup

## What to build

Budget setup should apply explicit setup choices. Copy previous month creates the selected month's parent budgets and copied subcategory limits. Smart auto-fill does the same, but raises parent category limits to satisfy category floors before saving.

## Acceptance criteria

- [x] Applying copy previous creates budget rows only for missing selected-month categories.
- [x] Applying copy previous copies budget-month subcategory limit rows without linking history.
- [x] Applying smart auto-fill raises parent limits to at least computed floor amounts.
- [x] Applying setup returns the same pre-flight status fields used by month-summary.
- [x] Re-applying setup is idempotent for existing selected-month budgets.

## Blocked by

- Issue 1: Stop automatic rollover effects in v1
- Issue 2: Preview explicit month setup modes

## Progress

- RED: `tests/test_budget.py::test_month_setup_apply_copies_previous_month_and_smart_fills_floors` failed because `/budgets/month-setup/apply` did not exist.
- GREEN: month setup apply now creates missing copied budgets, copies month-scoped subcategory limit rows, and raises smart auto-fill parent limits to floor amounts.
- GREEN: Reapplying setup does not duplicate existing selected-month budgets.
- GREEN: Focused Docker test passed.

## Issue 4: Complete Payable-Debt And Recurring Floor Coverage

## What to build

Category floors should cover every payable obligation whose repayment posts as a categorized expense, including category-linked debt rows, installment/payment-plan due rows, and recurring expenses due in the month. Cash-only debt remains global reserve pressure.

## Acceptance criteria

- [x] A payable debt with an expense category appears as a category floor even when its product label is not enough by itself.
- [x] Installment/payment-plan due rows continue to appear as category floors.
- [x] Recurring expenses due in the selected month continue to appear as category floors.
- [x] Cash-only debt remains cash obligation reserve pressure, not a category floor.
- [x] Month setup smart auto-fill uses the same floor list as month-summary.

## Blocked by

- Issue 2: Preview explicit month setup modes

## Progress

- RED: `tests/test_budget.py::test_budget_month_summary_classifies_payable_debt_floor_by_expense_route` failed because a payable debt with an expense category but non-deferred origin was missing from category floors.
- GREEN: category floors now include active payable debts with an expense category unless the debt is explicitly cash-only.
- GREEN: Focused Docker test passed.

## Verification For Completed First Half

- `docker compose exec api pytest -q tests/test_budget.py::test_get_budgets_does_not_auto_rollover_unused_room_in_v1 tests/test_budget.py::test_month_setup_preview_modes_are_read_only_and_show_floor_repair tests/test_budget.py::test_month_setup_apply_copies_previous_month_and_smart_fills_floors -q` passed with 3 tests.
- `docker compose exec api pytest -q tests/test_budget.py -q` passed with 45 tests.
- Frontend was not touched for the completed first half, so no frontend build was run.

## Final G6 Verification

- `docker compose exec api pytest -q tests/test_budget.py -q` passed with 46 tests.
- `docker compose exec api pytest -q tests/test_recurring_expenses.py -q` passed with 10 active tests and 1 intentionally skipped scheduler-deadlock test.
- `npm.cmd run build` passed.

## Issue 5: Expose Recurring Default Cost Projections

## What to build

Recurring expense details should expose backend-calculated default cost projection rows. The backend counts scheduled occurrences over frequency-appropriate horizons and multiplies by recurring amount.

## Acceptance criteria

- [x] Daily recurring expenses return 7-day, 14-day, 1-month, 3-month, 6-month, and 12-month projections.
- [x] Weekly and biweekly recurring expenses return 1-month, 3-month, 6-month, and 12-month projections.
- [x] Monthly recurring expenses return 3-month, 6-month, and 12-month projections.
- [x] Longer recurring frequencies return the documented default horizons.
- [x] Projection rows do not mutate recurring due dates, budgets, wallets, debts, or expenses.

## Blocked by

None - can start immediately.

## Progress

- RED: `tests/test_recurring_expenses.py::test_recurring_default_projections_match_frequency_horizons` failed because `/recurring/{id}/projections` did not exist.
- GREEN: recurring projection service and endpoint now return backend-calculated default projection rows from scheduler-compatible date advancement.
- GREEN: Focused Docker projection tests passed.

## Issue 6: Save Custom Recurring Projection Horizons And Wire UI

## What to build

Users should be able to save custom projection horizons per recurring expense and see them on the recurring detail UI alongside defaults.

## Acceptance criteria

- [x] Users can save custom projection horizons allowed for the recurring frequency.
- [x] Saved custom horizons are returned with recurring projection output.
- [x] Ad hoc projection preview can be requested without persistence.
- [x] Validation caps extreme horizons while allowing practical values like 299 days and 50 weeks.
- [x] UI renders default and custom projection rows without implying they alter the plan.

## Blocked by

- Issue 5: Expose recurring default cost projections

## Progress

- RED: custom projection tests failed because save/preview endpoints did not exist.
- GREEN: saved custom horizons are stored on recurring templates as preference metadata and returned alongside default projections.
- GREEN: ad hoc projection preview returns `ad_hoc` rows without changing saved custom horizons.
- GREEN: recurring UI opens a cost projection dialog, renders backend default/custom/preview rows, and saves custom horizons.
- GREEN: `docker compose exec api pytest -q tests/test_recurring_expenses.py -q` passed with 10 active tests and 1 pre-existing scheduler-deadlock skip.
- GREEN: `npm.cmd run build` passed.
