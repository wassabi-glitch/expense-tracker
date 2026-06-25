# PRD: G21 - Subcategory Taxonomy Hub and UI Alignment

Labels: `ready-for-agent`

## Problem Statement

The current subcategory architecture cleanly separates global tags (`UserSubcategory`) from monthly budget limits (`BudgetSubcategoryLimit`). However, the API and UI are misaligned with this architecture:
1. **The Orphaned Intent Trap:** The "Add Subcategory" UI uses a raw text input. If a user types "Meat" in June and "MeatJune" in July, the system blindly creates duplicate global tags, fracturing historical reporting.
2. **The Deletion Danger:** Clicking "Delete" on a subcategory in the monthly budget UI triggers a backend route that attempts to delete the global tag entirely, rather than just removing the monthly limit. This risks catastrophic data loss for past expenses.
3. **Tag Bloat:** Over years of tracking, users accumulate dozens of subcategories. Without a centralized place to manage them, the ontology becomes a messy "junk drawer" of active, abandoned, and duplicate tags.

## Solution

1. **API Alignment:** Fix the backend budget routes so that deleting a subcategory from a month only removes the `BudgetSubcategoryLimit`, preserving the global tag and its history.
2. **The Combobox Upgrade:** Replace the raw text input for adding subcategories with a "Search & Create" Combobox. Users can pick from their inactive historical tags (preventing duplicates) or explicitly create a new one.
3. **The Taxonomy Hub:** Introduce a dedicated settings page where users can view all their tags grouped by parent category. The Hub provides a "Lifetime Scorecard" for each tag and grants users three superpowers: Renaming, Archiving (toggling `is_active` to hide them from budget dropdowns), and Merging (consolidating duplicate tags and rewriting historical expenses to the winner).

## User Stories

1. As a budget user, I want the "Add Subcategory" input to be a searchable dropdown, so that I can easily reuse my historical tags without accidentally creating duplicates.
2. As a budget user, I want to delete a subcategory from my current month's plan, so that it disappears from the active budget without destroying the tag's historical data.
3. As a budget user, I want a centralized Taxonomy Hub, so that I can view all the subcategories I have ever created, grouped by parent category.
4. As a budget user, I want to see a "Lifetime Scorecard" for each subcategory in the Hub (first used, total transactions, lifetime spent), so that I can decide if the tag is still useful.
5. As a budget user, I want to toggle a subcategory as "Inactive", so that it stops cluttering my active budget dropdowns but keeps my historical charts intact.
6. As a budget user, I want to select multiple duplicate subcategories and "Merge" them into one, so that all their historical expenses are consolidated under a single clean tag.
7. As a budget user, I want to rename a subcategory in the Hub, so that the new name ripples across all my past and future reports.

## Implementation Decisions

- **Backend API Fixes**:
  - `DELETE /budgets/subcategories/{subcategoryId}`: Change behavior to only delete the `BudgetSubcategoryLimit` for the current budget context (requires taking `budget_id` as a query param). If the global `UserSubcategory` needs deletion, it will be handled by a new dedicated endpoint in the Taxonomy Hub.
  - `POST /budgets/{budget_id}/subcategories`: Update to accept an optional existing `subcategory_id` to reuse a global tag. If a raw `name` is provided and it matches an existing tag for that user/category, gracefully reuse the existing `UserSubcategory` instead of crashing with an `IntegrityError`.
- **Taxonomy Hub Endpoints**:
  - `GET /subcategories/taxonomy`: Returns all `UserSubcategory` tags with aggregated lifetime stats (first_used, last_used, tx_count, lifetime_spent), grouped by parent category.
  - `PATCH /subcategories/{id}`: Expose updating the `is_active` flag and `name`.
  - `POST /subcategories/merge`: Accepts a list of `source_ids` and a `target_id`. It will update all `EntityLedger` rows pointing to the source IDs to point to the target ID, then delete the source `UserSubcategory` rows.
- **Frontend Changes**:
  - Replace the `<Input>` in `Budgets.jsx` with a Combobox component.
  - Create a new tab/view inside the Budgets page for the Subcategory Taxonomy Hub, keeping it tightly integrated with the user's budgeting workflow rather than burying it in Settings.

## Testing Decisions

- **Testing Seams**:
  - **Backend Integration Tests (`tests/api/`)**:
    - Test the `/subcategories/merge` endpoint: Verify that `EntityLedger` rows are correctly reassigned and old tags are deleted.
    - Test the `/budgets/subcategories` endpoints: Verify that global tags are NOT deleted when a monthly limit is removed, and that providing an existing name to the create route reuses the tag.
  - **Frontend Component Tests (`frontend/src/tests/`)**:
    - Test the Combobox component to ensure "Create New" triggers the correct payload vs "Select Existing".
    - Test the Taxonomy Hub rendering the lifetime stats and the Merge modal flow.
- **Prior Art**: Follow the existing patterns for financial event ledger manipulation in the backend, and standard React component testing in the frontend.

## Out of Scope

- Month-by-month historical limit charting (e.g., "Meat limit trend over 12 months"). This belongs in the future Analytics/Cashflow Simulator (G20), not the Taxonomy Hub.
- Automatically purging unused subcategories without user consent.

## Further Notes

- The `UserSubcategory` table already has an `is_active` boolean, which makes implementing the Archive feature straightforward.
- Merging subcategories must be executed in a single database transaction to prevent data corruption.
