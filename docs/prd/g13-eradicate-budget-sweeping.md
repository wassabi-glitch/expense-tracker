## Problem Statement

The "Budget Sweeping" feature (the ability to automatically sweep unspent budget money into a designated goal) was previously deprecated at the product level because budgets in this system serve as pure planning limits, not real-money envelopes. Although the API currently blocks users from setting a `sweep_target_goal_id` (returning a 400 error), the ghost of this feature still haunts the codebase. The database retains the columns, the API schemas still declare the fields, and the computation engine still parses `"SWEEP"` ledger effects. The user wants to eradicate all traces of this feature from the entire ecosystem to simplify the codebase.

## Solution

We will permanently delete all sweep-related fields from the database, API schemas, backend computation engines, and the frontend error handling. This is a pure cleanup operation that fully aligns the codebase with the actual product model.

## User Stories

1. As a developer, I want the `BudgetService` computation engine to be unburdened by `sweep_amount` logic, so that the code is easier to read, maintain, and test.
2. As a database administrator, I want the `Budget` table to drop the unused `sweep_target_goal_id` column, so that the schema perfectly reflects the active features.
3. As an API consumer, I want the Budget API schemas to completely omit `sweep_target_goal_id` and `sweep_amount`, so that the API documentation is accurate and I am not tempted to use deprecated fields.
4. As a frontend developer, I want to remove legacy error messages (`budgets.sweep_removed`), so that the frontend code doesn't carry dead translations.

## Implementation Decisions

- **Database (`app/models.py`)**: 
  - Drop the `sweep_target_goal_id` column from the `Budget` model via an Alembic migration.
  - Remove the `"SWEEP"` constant/enum from `BudgetLedgerType` (or equivalent).
- **API Schemas (`app/schemas.py`)**: 
  - Remove `sweep_target_goal_id` and `sweep_amount` from all Budget Pydantic models (inbound and outbound).
- **Backend Logic (`app/services/budget_service.py`)**:
  - Remove the extraction of `"SWEEP"` from ledger effects.
  - Remove `sweep_amount` from the `effective_limit` calculations. (Assuming the rollover eradication PRD is also implemented, the formula will simply become `effective_limit = monthly_limit - cap_trim_amount`).
- **API Endpoints (`app/routers/budget.py`)**:
  - Remove the explicit check that raises `HTTP 400` with the detail `"budgets.sweep_removed"`. Rely on Pydantic's schema validation to reject or ignore the field entirely.
- **Frontend / Translations (`frontend/src/lib/errorMessages.js`)**:
  - Delete the frontend translation mapping for `"budgets.sweep_removed"` as the backend will no longer emit it.

## Testing Decisions

We will test the removal of the feature at the following seams:

- **Backend API Layer**: We will write tests to ensure that providing `sweep_target_goal_id` in a budget creation or update payload is either ignored or throws a standard `422 Unprocessable Entity` (depending on Pydantic configuration), rather than the custom `400` legacy error.
- **Service Layer (Computation Seam)**: We will test `BudgetService` to verify that `effective_limit` calculations completely ignore any historical `"SWEEP"` effects that might still exist in the database for older users.
- **Frontend tests**: Ensure that no components fail due to the missing error message mapping.

## Out of Scope

- Deleting historical `"SWEEP"` ledger entries from the database. Existing records for old months will remain untouched in the ledger for historical integrity, but the computation engine will no longer parse or act on them.
- Any changes to standard Goal features (depositing/withdrawing). This PRD strictly targets the *budget-to-goal sweep* mechanic.

## Further Notes

This eradication pairs perfectly with the Rollover Eradication (g12). Together, they drastically simplify the End-of-Month Engine, turning budgets back into simple, stateless month-to-month planning rails.
