# PRD: G24 - Month-Scoped Overlay Project Architecture

Labels: `ready-for-agent`

## Problem Statement

Currently, Overlay Projects use a single, global "Total Limit" (fantasy money) that decouples from the strict monthly envelope system (G5). When a project spans multiple months, the system has no idea how much of that limit belongs to June vs. July, making it impossible to validate whether the user actually has the Global Budget capacity to fund the project. Furthermore, it creates a "Mountain of Confusion" regarding what happens when a project overspends in real life versus when the global parent budget overspends.

## Solution

Transform Overlay Projects into **Month-Scoped Slices**. A project limit is no longer a global number; it is a direct "Reservation" (Sub-Envelope) sliced out of the parent Global Monthly Budget. The mathematics strictly follow: `Global Limit = Project Reservation + General Bucket`. Overspending locally on a project steals from the General Bucket, preserving wallet reality while maintaining consequences.

## User Stories

1. As a budget user, I want project limits to be tied to specific months, so that my plan respects temporal boundaries.
2. As a budget user, I want project limits to act as reservations against my global monthly budget, so that I don't accidentally spend money twice.
3. As a budget user, I want my global parent category to remain green even if my project overspends, provided the global limit hasn't breached, so that my macro plan stays healthy.
4. As a budget user, I want my project overspending to steal capacity from my unreserved General Bucket, so that I face the natural consequence of having less free money.
5. As a budget user, I want the system to let reality happen (never blocking expenses), so that my wallet balance stays perfectly synced with reality.

## Implementation Decisions

- **Schema Changes:** Drop `ProjectCategoryLimit`. Create `ProjectCategoryMonthlyLimit(project_id, category, budget_year, budget_month, limit_amount)`.
- **Budget Materialization:** When the frontend requests a monthly budget, the backend aggregates all active `ProjectCategoryMonthlyLimit` rows for that month and exposes them as `Category Floors` (reserved limits).
- **The Golden Math Rule:** Project limits are strictly informational UI reservations. Expense posting logic does not hard-block when a project limit is exceeded. 
- **Temporal Alignment:** Changing a project's dates requires migrating the `ProjectCategoryMonthlyLimit` slices to the new months. Slices cannot be shrunk below their `actual_spent` amount during a date shift.

## Testing Decisions

- Test the `GET /budgets/{year}/{month}` endpoint to ensure it correctly aggregates and returns project reservations.
- Test expense posting to ensure overspending a project correctly reduces the available unreserved balance in the parent category without throwing a blocking exception.
- Prior art: G5 Month-Scoped Subcategories and G9 Category Floors.

## Out of Scope

- Subcategory inheritance (See G25).
- Project wrap-up and sweep logic (See G26).
- UI visualization of the reservations (See G27).

## Further Notes

By treating project limits as monthly reservations, we perfectly hook into the G12 "No Rollovers" rule. If a project slice is unspent at the end of a month, it is historically preserved, and the actual cash simply remains in `Free Money Now` for the next month.
