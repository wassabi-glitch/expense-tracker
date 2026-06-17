# Issues: G5 - Month-Scoped Subcategory Architecture

Parent PRD: `docs/prd/g5-month-scoped-subcategory-architecture.md`

Publish label: `ready-for-agent`

## Proposed Breakdown

1. **Store subcategory limits per budget month**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-4, 10-11

2. **Copy subcategory limits during lazy month materialization**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 2-4, 10

3. **Expose subcategory overspend without blocking expense save**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 5-7, 9-10

4. **Constrain subcategory reallocation inside the parent category**
   - Type: AFK
   - Blocked by: Issues 1 and 3
   - User stories covered: 4, 6, 8-10

5. **Wire month-scoped subcategory state into budget UI**
   - Type: HITL
   - Blocked by: Issues 1-4
   - User stories covered: 2-8, 10

## Issue 1: Store Subcategory Limits Per Budget Month

## What to build

Subcategory tags should stop owning financial limits globally. A parent budget month should own each subcategory's limit for that month, while budget detail and subcategory routes keep exposing the existing `monthly_limit` API field from the selected budget's limit row.

## Acceptance criteria

- [x] `UserSubcategory` represents reusable tag identity without a global monthly limit.
- [x] A budget-specific subcategory limit record links a parent budget to a user subcategory and a monthly limit.
- [x] Creating a budget subcategory with a limit creates the tag and the selected budget month's limit.
- [x] Updating a subcategory limit changes the selected/latest budget month's limit without mutating prior budget detail.
- [x] Budget detail returns the correct `monthly_limit`, `spent`, `remaining`, and `is_over_limit` for the requested month.
- [x] The sum of budget-month subcategory limits cannot exceed that parent budget's monthly limit.

## Blocked by

None - can start immediately.

## Suggested verification

- `docker compose exec api pytest -q tests/test_budget.py::test_budget_subcategory_limit_changes_do_not_mutate_prior_month_detail -q`
- `docker compose exec api pytest -q tests/test_budget.py::test_lazy_month_materialization_copies_subcategory_limits_without_linking_history -q`
- `docker compose exec api pytest -q tests/test_budget.py -q`

## Progress

- RED: `tests/test_budget.py::test_budget_subcategory_limit_changes_do_not_mutate_prior_month_detail` failed because the prior budget detail returned the later patched global limit.
- GREEN: `UserSubcategory` is now tag identity, budget-month limits live in `BudgetSubcategoryLimit`, budget detail reads limit rows for the requested budget, and later-month limit updates no longer mutate prior budget detail.
- GREEN: Docker focused G5 tests, full budget suite, narrow expense subcategory tests, and Alembic upgrade passed.

## Issue 2: Copy Subcategory Limits During Lazy Month Materialization

## What to build

When a missing budget month is lazily created from the prior month, copy the prior budget's subcategory limit rows into the new budget. The copy should be a new set of rows so later edits remain month-scoped.

## Acceptance criteria

- [x] Lazy materialization creates new budget-specific subcategory limit rows from the source month.
- [x] Editing the new month's copied limit does not mutate the source month.
- [x] Subcategories without explicit limits remain unbounded in the new month.
- [x] Parent category capacity validation still runs after lazy materialization.

## Blocked by

- Issue 1: Store subcategory limits per budget month

## Progress

- GREEN: `tests/test_budget.py::test_lazy_month_materialization_copies_subcategory_limits_without_linking_history` verifies that a current-month expense lazily materializes a copied subcategory limit from the previous budget and that later edits do not mutate the source month.
- GREEN: `tests/test_budget.py::test_lazy_month_materialization_keeps_unlimited_subcategories_unbounded` verifies unbounded subcategories remain unbounded after lazy materialization.

## Issue 3: Expose Subcategory Overspend Without Blocking Expense Save

## What to build

Budget detail should make subcategory overspend visible through negative remaining and `is_over_limit`, while ordinary expense save continues to record wallet reality even when a subcategory or parent category goes red.

## Acceptance criteria

- [x] Expense save with no subcategory remains valid for a parent category budget.
- [x] Expense save with an over-limit subcategory remains valid.
- [x] Budget detail shows overspent subcategories as negative remaining and over limit.
- [x] Parent category overspend still leaks to global plan backing through existing G3 math.

## Blocked by

- Issue 1: Store subcategory limits per budget month

## Progress

- GREEN: `tests/test_budget.py::test_parent_category_spending_without_subcategory_remains_valid` verifies parent-only spending stays valid and appears as untagged budget activity.
- GREEN: `tests/test_budget.py::test_subcategory_overspend_saves_and_budget_detail_reports_red_state` verifies over-limit subcategory spending saves and budget detail reports negative remaining.
- GREEN: `tests/test_budget.py::test_parent_category_overspend_leaks_to_global_plan_backing` verifies G3 backing math still turns the plan `over_planned` when parent overspend consumes global backing.

## Issue 4: Constrain Subcategory Reallocation Inside The Parent Category

## What to build

Subcategory reallocation should move limit between sibling subcategories or unallocated parent-category buffer only. It must not directly pull from another parent category or silently mutate parent budgets.

## Acceptance criteria

- [x] Reallocation within the same parent budget month succeeds when sibling/buffer capacity exists.
- [x] Reallocation across parent categories is rejected.
- [x] Reallocation cannot make the sum of subcategory limits exceed the parent budget limit.
- [x] Parent budget reallocation remains the explicit macro action for moving money between categories.

## Blocked by

- Issue 1: Store subcategory limits per budget month
- Issue 3: Expose subcategory overspend without blocking expense save

## Progress

- RED: Reallocation tests initially failed with `404 Not Found` because no subcategory reallocation route existed.
- GREEN: Added budget-scoped subcategory reallocation from parent buffer or sibling subcategory only.
- GREEN: `tests/test_budget.py::test_subcategory_reallocation_from_buffer_and_sibling_stays_inside_parent` verifies successful same-parent buffer and sibling moves.
- GREEN: `tests/test_budget.py::test_subcategory_reallocation_rejects_cross_parent_and_overcommitted_moves` verifies cross-parent moves, missing buffer, and spent-source overcommit are rejected.

## Issue 5: Wire Month-Scoped Subcategory State Into Budget UI

## What to build

Budget UI should display month-scoped subcategory limits, negative remaining states, parent-category buffer, and repair actions without implying that subcategory overspend blocks transaction save.

## Acceptance criteria

- [x] Budget detail UI reads subcategory limits from the selected month.
- [x] Historical months do not visually change after later-month subcategory edits.
- [x] Overspent subcategories show actionable repair options.
- [x] Parent-only spending is shown as unspecified category spending.
- [x] UX copy keeps micro subcategory decisions separate from macro parent budget decisions.

## Blocked by

- Issue 1: Store subcategory limits per budget month
- Issue 2: Copy subcategory limits during lazy month materialization
- Issue 3: Expose subcategory overspend without blocking expense save
- Issue 4: Constrain subcategory reallocation inside the parent category

## Progress

- Budget detail and Manage Subcategories surfaces now show parent buffer, month-scoped subcategory limits, red subcategory states, and unspecified parent spending.
- Manage Subcategories now exposes a same-parent reallocation tool for buffer or sibling moves.
- Subcategory updates can target a specific budget month while preserving the old latest-month route behavior for compatibility.
- Frontend production build passed with `npm.cmd run build`.

## Final verification

- `docker compose exec api pytest -q tests/test_budget.py -q` passed with 43 tests.
- `docker compose exec api pytest -q tests/test_expenses.py::test_split_expense_can_add_subcategories_when_parent_had_none tests/test_expenses.py::test_split_expense_can_clear_parent_subcategory -q` passed with 2 tests.
- `npm.cmd run build` passed. Vite reported the existing large chunk warning.
- The in-app browser remained unavailable for a UI smoke check (`iab` could not be acquired).
