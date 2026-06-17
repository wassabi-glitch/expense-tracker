## Problem Statement

The application currently supports complex "budget rollover" logic that allows unspent money to carry forward to the next month, either partially, fully, or as a percentage. This feature introduces unnecessary complexity into the financial domain model, complicates the codebase (touching the database, backend computations, and frontend UI), and deviates from the core, simplified vision of the product. The user wants to completely eradicate the concept of budget rollovers from the entire ecosystem to simplify the budget experience.

## Solution

We will remove all rollover-related logic from the backend services, API schemas, database models, and the frontend application. Budgets will be strictly month-to-month, meaning any unspent limits simply disappear at the end of the period, without being carried forward.

## User Stories

1. As a user, I want my monthly budget limits to reset cleanly every month, so that I have a predictable and clear understanding of my allowance.
2. As a user, I do not want to see any confusing "Rollover" settings or labels in the Budget UI, so that the interface remains simple and clean.
3. As a premium user, I no longer want to see the "Budget Rollover" toggle in the settings, so that I am not distracted by unsupported features.
4. As a developer, I want the `BudgetService` to compute effective limits without complex rollover mathematics, so that the system is easier to maintain and test.
5. As an API consumer, I want the budget creation and update endpoints to be streamlined, so that I don't have to provide rollover-related parameters.

## Implementation Decisions

- **Database (`app/models.py`)**: 
  - Drop the `max_rollover_amount` and `rollover_mode` columns from the `Budget` model via an Alembic migration.
  - Drop the `budget_rollover_enabled` column from the User profile model via migration.
  - Remove the `ROLLOVER` constant/enum.
- **API Schemas (`app/schemas.py`)**: 
  - Remove all rollover fields (`max_rollover_amount`, `rollover_mode`, `rollover_amount`) from Budget inbound/outbound schemas.
  - Remove `budget_rollover_enabled` from User profile schemas and delete the `UserBudgetRolloverPreferenceUpdate` model.
- **Backend Logic (`app/services/budget_service.py`)**:
  - Delete `_rollover_policy_amount` and any associated calculation logic.
  - Remove rollover additions from `effective_limit` calculations.
- **API Endpoints (`app/routers/budget.py`, `app/routers/users.py`)**:
  - Remove `_validate_rollover_fields`.
  - Delete the `PATCH /me/preferences/budget-rollover` endpoint entirely.
- **Frontend Components**:
  - Remove the Budget Rollover section from `Settings.jsx` and its related React Query mutations.
  - Remove "Rollover" labels and values from `Budgets.jsx` and `BudgetDetails.jsx`.
  - Remove `"featureRollover"` from the Premium features list in `Premium.jsx`.
- **Translations (`i18n/locales/*.json`)**:
  - Delete all rollover-related strings (e.g., `budgetRolloverTitle`, `rolloverAmount`) across all supported languages.

## Testing Decisions

We will test the removal of the feature at the following seams:

- **Backend API Layer (Highest Seam)**: We will write tests to ensure that `PATCH /users/me/preferences/budget-rollover` returns a `404 Not Found`. We will also ensure that creating or updating a budget with rollover fields simply ignores them or throws a 422 Unprocessable Entity (depending on Pydantic's `extra` config).
- **Service Layer (Computation Seam)**: We will test `BudgetService` computation functions to verify that when calculating a budget's `effective_limit`, it strictly follows the formula `monthly_limit - sweep_amount - cap_trim_amount` without any rollover additions.
- **Frontend UI Tests**: Ensure that the `Settings` component renders correctly without the rollover toggle and that the `Budgets` dashboard does not attempt to render rollover data.

## Out of Scope

- We will not be restructuring how `sweep_target_goal_id` works; sweeping unspent money to goals is conceptually distinct from rolling over budget limits, though they are related. Sweeping will remain intact unless otherwise specified.
- Re-calculating historical financial periods. Old budget calculations that already occurred will remain as they are in the ledger (if they were materialized as physical transactions), though the UI will no longer display rollover breakdowns.

## Further Notes

By removing rollovers, the "End-of-Month Engine" described in `architecture_blueprint.md` will become significantly simpler. We should also update the documentation to reflect this structural change.
