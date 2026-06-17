## Problem Statement

The backend currently supports two powerful "Reallocation" features:
1. Shifting monthly limits between parent categories (e.g., from Groceries to Entertainment).
2. Shifting limits between subcategories within the same parent (e.g., from Transport Buffer to Fuel).

While the backend logic and API endpoints for both are fully implemented and wired into the frontend's API client (`frontend/src/lib/api/budgets.js`), there is a significant UI disconnect on the frontend.

Currently, **parent category reallocation** can only be triggered *reactively* through a "repair prompt" on the Expenses page (when a user overspends and is forced to cover it from another category). There is absolutely no UI on the main Budgets dashboard (`Budgets.jsx`) to *proactively* reallocate money between parent categories. Users can proactively reallocate subcategories from the dashboard, but not parent categories.

## Solution

We need to close the gap between the frontend and backend by introducing a proactive "Reallocate Limits" feature on the main Budgets dashboard. This will allow users to shift funds between top-level category budgets directly, mirroring the existing UI for subcategory reallocation.

## User Stories

1. As a user reviewing my monthly budgets, I want to proactively shift 500k from my "Dining" limit to my "Groceries" limit, so that I can adjust my plan before I overspend.
2. As a user on the Budgets dashboard, I want a clear "Reallocate" button on my parent category cards, so that I don't have to wait until I log a transaction to shift my limits.
3. As a developer, I want the `Budgets.jsx` dashboard to consume the existing `reallocateBudget` API client method, so that the frontend fully utilizes the backend's capabilities.

## Implementation Decisions

- **Frontend (`frontend/src/features/budgets/Budgets.jsx`)**:
  - Introduce a new state or dialog for "Parent Reallocation".
  - Add a "Reallocate" action to the top-level Budget cards (similar to how it currently exists for subcategories).
  - The dialog should allow the user to select:
    - **Source Category** (from a list of active parent budgets with remaining capacity).
    - **Target Category** (from a list of active parent budgets).
    - **Amount** (validating that it does not exceed the source's remaining limit).
  - Consume the `reallocateBudget` API function (which takes `from_category`, `to_category`, `amount`, `budget_year`, `budget_month`) to execute the shift.
  - Call the React Query mutation to invalidate and refetch the budgets upon success.

## Testing Decisions

We will test the feature at the following seams:

- **Frontend UI Layer**: 
  - Render the Budgets dashboard and verify the new "Reallocate" button appears on parent categories.
  - Verify that the target/source dropdowns correctly prevent the user from selecting the same category for both.
  - Verify that the amount input validates against the source category's available `remaining` balance.
- **Integration Seam**: 
  - Ensure the form submission successfully maps to the `POST /budgets/reallocate` payload and triggers a UI refresh upon receiving the updated `reallocated_in` and `reallocated_out` properties from the backend.

## Out of Scope

- Modifying the backend logic. The backend `reallocate_budget` endpoint is already robust and handles cross-parent logic perfectly.
- Changing the "repair" prompts in `Expenses.jsx`—those are reactive and will remain as they are.

## Further Notes

This is purely a missing-UI issue. The domain model, schemas, and API functions are fully prepared to handle proactive parent-category reallocations. Bringing this to the Budgets dashboard will make the planning experience much more dynamic.
