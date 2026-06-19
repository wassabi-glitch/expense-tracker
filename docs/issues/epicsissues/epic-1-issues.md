# Epic 1 Issues: Core Cleanup

## Issue 1: Eradicate Budget Sweeping

### What to build
Completely strip the deprecated "Budget Sweeping" feature from the system end-to-end. This feature was previously deprecated at the product level, but dead code still haunts the database schema, API, and computation engines. Removing this will guarantee the End-of-Month Engine acts purely as a stateless planner. 

### Acceptance criteria
- [x] `sweep_target_goal_id` column is dropped from the `Budget` database table via Alembic migration.
- [x] `"SWEEP"` constant is removed from `BudgetLedgerType`.
- [x] `sweep_target_goal_id` and `sweep_amount` are removed from all inbound/outbound Pydantic schemas.
- [x] `BudgetService.effective_limit` calculations completely ignore any historical `"SWEEP"` ledger effects.
- [x] Frontend legacy translation mapping for `"budgets.sweep_removed"` is deleted.
- [x] Creating/updating a budget with sweep fields either ignores them or returns `422 Unprocessable Entity`, not a custom legacy `400`.

### Blocked by
None - can start immediately.

---

## Issue 2: Eradicate Budget Rollovers

### What to build
Completely remove the complex "budget rollover" mechanism from the entire ecosystem. Budgets will now be strictly month-to-month planning limits with no automatic carry-forward capabilities. This vertical slice rips the feature out of the database, the backend math, and the user-facing React settings.

### Acceptance criteria
- [ ] `max_rollover_amount` and `rollover_mode` columns are dropped from the `Budget` table via Alembic migration.
- [ ] `budget_rollover_enabled` is dropped from the User profile table via Alembic migration.
- [ ] All rollover fields are removed from the API Pydantic schemas.
- [ ] The `PATCH /me/preferences/budget-rollover` endpoint is deleted entirely and returns `404 Not Found`.
- [ ] `BudgetService` computation ignores rollovers; `effective_limit` relies strictly on `monthly_limit` minus cap trims.
- [ ] "Budget Rollover" settings toggle is removed from the `Settings.jsx` React component.
- [ ] "Rollover" visual labels are removed from `Budgets.jsx` and `BudgetDetails.jsx`.
- [ ] All rollover-related i18n translation strings are deleted.

### Blocked by
- Issue 1: Eradicate Budget Sweeping (To prevent Alembic database migration merge conflicts).
