# Issues: G8 - Expense Entry and Post-Save Repair UX

Parent PRD: `docs/prd/g8-expense-entry-post-save-ux.md`

Publish label: `ready-for-agent`

Execution scope: EC-109, EC-110, and EC-123 only.

Progress: Issues 1-4 are implemented/verified for the available environment. Browser smoke was attempted, but the in-app browser target was unavailable.

## Proposed Breakdown

1. **Show Non-Blocking Over-Budget Warnings**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-4, 14-16
   - Status: Completed

2. **Show Parent Category Post-Save Repair Actions**
   - Type: HITL
   - Blocked by: Issue 1
   - User stories covered: 5-8, 15-16
   - Status: Completed

3. **Show Subcategory Overspend Repair Actions**
   - Type: HITL
   - Blocked by: Issue 1
   - User stories covered: 9-13, 15-16
   - Status: Completed

4. **Verify End-to-End Expense Save and Repair States**
   - Type: AFK
   - Blocked by: Issues 1-3
   - User stories covered: 1-16
   - Status: Completed

## Issue 1: Show Non-Blocking Over-Budget Warnings

## What to build

Expense entry should warn when the current amount/category/date/subcategory would exceed the plan, but it must not disable save.

## Acceptance criteria

- [x] A parent-category overage warning appears before save when the entered expense would exceed remaining category budget.
- [x] A subcategory overage warning appears before save when the entered expense would exceed remaining subcategory limit.
- [x] Warnings update when amount, category, date, or subcategory changes.
- [x] Save remains enabled while over-budget warnings are visible.
- [x] Saving the expense records the real transaction successfully.

## Progress

- GREEN: Quick Add now computes advisory parent-category and subcategory warnings from existing budget/subcategory state.
- GREEN: Save remains available because warnings are not part of validation.
- Verification: Docker frontend build passed.

## Blocked by

None.

## Issue 2: Show Parent Category Post-Save Repair Actions

## What to build

After an expense pushes a parent category into the red, show the updated red state and repair actions.

## Acceptance criteria

- [x] The affected category shows negative remaining after save.
- [x] The post-save UI offers reallocation from another parent category.
- [x] The post-save UI offers increasing the affected category limit.
- [x] The post-save UI offers leaving the category red.
- [x] Leaving red does not mutate budgets.
- [x] Repair actions refresh the budget detail and month summary state.

## Progress

- RED/GREEN: Added `tests/test_budget.py::test_parent_category_overspend_can_be_repaired_by_reallocation`.
- GREEN: Quick Add opens a parent-category repair dialog after a saved over-budget expense.
- GREEN: Repair dialog supports parent reallocation, parent limit increase, and leave-red.
- Verification: Docker budget and expense suites passed; Docker frontend build passed.

## Blocked by

- Issue 1: Show Non-Blocking Over-Budget Warnings

## Issue 3: Show Subcategory Overspend Repair Actions

## What to build

After an expense pushes a subcategory into the red, show the red subcategory state and same-parent repair actions.

## Acceptance criteria

- [x] The affected subcategory shows negative remaining after save.
- [x] The post-save UI offers reallocation from parent buffer.
- [x] The post-save UI offers reallocation from sibling subcategories.
- [x] The post-save UI offers increasing the parent category limit when micro repair is insufficient.
- [x] The post-save UI offers leaving the subcategory red.
- [x] Subcategory repair does not silently mutate another parent category.

## Progress

- GREEN: Quick Add opens a subcategory repair dialog after a saved subcategory overage.
- GREEN: Repair dialog supports parent-buffer reallocation, sibling-subcategory reallocation, parent limit increase, and leave-red.
- GREEN: Subcategory reallocation uses `POST /budgets/{budget_id}/subcategories/reallocate`, so repair stays inside the parent category unless the user explicitly increases the parent limit.
- Verification: Docker budget and expense suites passed; Docker frontend build passed.

## Blocked by

- Issue 1: Show Non-Blocking Over-Budget Warnings

## Issue 4: Verify End-to-End Expense Save and Repair States

## What to build

Add focused regression coverage for the user-visible over-budget and subcategory repair workflow.

## Acceptance criteria

- [x] Backend tests prove parent-category over-budget expense save succeeds and reports red state.
- [x] Backend tests prove subcategory over-limit expense save succeeds and reports red state.
- [x] Frontend build passes after UI changes.
- [x] Browser smoke check verifies warning, save, red state, and at least one repair path if browser tooling is available.
- [x] No test or doc in this G8 pass expands scope beyond EC-109, EC-110, and EC-123.

## Progress

- Verification: `docker compose exec api pytest -q tests/test_budget.py -q` passed on rerun. First run had a non-reproducible failure in `test_budget_write_rate_limit_blocks_burst`.
- Verification: `docker compose exec api pytest -q tests/test_expenses.py -q` passed.
- Verification: `docker compose exec frontend npm run build` passed with the existing Vite large chunk warning.
- Browser smoke: attempted through the Browser skill on 2026-06-15, but the in-app browser target returned `Browser is not available: iab`; no browser smoke was possible in this environment.

## Blocked by

- Issue 1: Show Non-Blocking Over-Budget Warnings
- Issue 2: Show Parent Category Post-Save Repair Actions
- Issue 3: Show Subcategory Overspend Repair Actions
