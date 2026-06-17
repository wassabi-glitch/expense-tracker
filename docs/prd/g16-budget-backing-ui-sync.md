# PRD: G16 - Budget Backing UI Sync

Labels: `ready-for-agent`

## Problem Statement

The backend has successfully implemented the G3 core budget backing math, which prevents false "Over-Planned" alerts after perfectly normal, in-limit spending. It also calculates required category floors for recurring bills and debts. However, the frontend never adopted these changes. The UI still blindly relies on the legacy `plan_free_money_remaining` variable instead of the new `plan_backing_remaining`. This causes the "Budget room after plan" card to panic and turn red when a user executes their plan correctly. Furthermore, the frontend entirely ignores the `category_floors` data sent by the backend, meaning users have no visibility into the minimum budget amounts they need to cover upcoming obligations like subscriptions or loan payments.

## Solution

Synchronize the frontend Budget Workspace UI with the existing backend G3 data. Specifically, swap out the legacy plan health variables for the new `plan_backing_remaining` and `backing_shortfall` fields so that plan health accurately reflects valid budget spent. Additionally, introduce a new UI component in the Budget detail or summary views that reads the `category_floors` array and displays required minimums and shortfalls for categories tied to obligations.

## User Stories

1. As a budget user, I want my "Budget room after plan" to remain stable after I spend within my category limits, so that the app doesn't punish me with red alerts for following my plan.
2. As a budget user, I want the UI's health status text to accurately reflect the smart backend math, so that I only see "Over-Planned" when I actually have a real backing shortfall.
3. As a budget planner, I want to see the required category floors visually on my budget cards, so that I know exactly how much I need to allocate to cover my upcoming Netflix bill or loan payment.
4. As a budget planner, I want to see a clear warning if I set my category limit below the required floor, so that I don't accidentally under-fund a strict obligation.
5. As a frontend maintainer, I want the UI to seamlessly consume the `BudgetMonthSummaryOut` schema fields provided by the G3 backend, so that the frontend and backend share the exact same source of truth for financial health.

## Implementation Decisions

- Modify the React components responsible for the "Budget room after plan" summary card to swap `plan_free_money_remaining` with `plan_backing_remaining`.
- Ensure the "Plan Health" string and color logic leverages the new backend math (e.g., checking `backing_shortfall` instead of cash gaps where appropriate).
- Map over the `category_floors` array returned from the `/budgets/month-summary` endpoint to render a new "Required Floors" subsection or badge on the relevant category budget cards.
- Add conditional styling to highlight a budget limit if its value is less than the `floor_amount` reported in the `category_floors` data.
- Remove leftover frontend calculations that try to manually derive plan health, defaulting fully to the backend's `plan_status`.

## Testing Decisions

- E2E or Component integration tests using a mocked `/budgets/month-summary` response that includes `plan_backing_remaining` and a populated `category_floors` array.
- Verify that when `plan_backing_remaining` is positive, the UI stays green (even if free money dropped due to valid spending).
- Verify that a budget card renders the required floor text/badge when that category exists in the `category_floors` array.
- Prior art for these tests can be found in existing frontend component tests for `Budgets.jsx` or similar data-driven UI components.

## Out of Scope

- Any backend changes. The G3 backend logic is already feature-complete, tested, and returning the correct data shapes.
- Changing the actual styling or design system of the budget cards; we are only dropping in new variables and a simple floor indicator.

## Further Notes

This PRD resolves the UI disconnects discovered after reviewing the G3 (Core Budget Backing Math) implementation. It bridges the gap between the smart backend accounting and the user-facing dashboard. Published locally under `docs/prd/` with the `ready-for-agent` label.

- **Macro vs. Micro Interactions (G6 vs. G16):** It is critical to preserve the UX distinction between G6's "Smart Auto-Fill" and G16's "1-Click Fix". G6 provides a **Macro-Interaction** designed for the "Month Setup Wizard" to globally initialize the budget. G16 provides a **Micro-Interaction** to be used mid-month. If a user adds a new subscription mid-month causing a floor warning, they use G16's targeted 1-Click Fix on that specific budget card to instantly resolve it, without being forced back into a heavy, global setup wizard.
