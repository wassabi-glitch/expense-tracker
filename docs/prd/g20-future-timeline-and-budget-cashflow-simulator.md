## Problem Statement

Users struggle to plan their monthly budgets because they lack a consolidated view of their future cashflow. They plan fantasy budgets based on their current wallet balance, forgetting that they have significant obligations (installments, debts, recurring bills) due later in the month. Conversely, they may feel artificially constrained because they forget about expected income arriving soon. The UI separates Expected Incomes (Money In), Debts/Installments (Obligations), and Budgets (Planning) into disconnected silos, preventing users from seeing the true "Financial Truth Status" of their month.

## Solution

Introduce a "Commitment Intelligence" layer (EC-052) that merges Expected Incomes and Expected Expenses into a unified chronological story. 
1. **The Budget Cashflow Simulator:** Embed the full 30-day "Future Timeline Engine" (EC-054) directly into the Budgets page. This transforms static budgeting into a dynamic cashflow simulation, where users can see exactly when obligations hit versus when income arrives, allowing them to adjust category limits safely.
2. **Category Floors Validation & 1-Click Fix:** Enforce "Category Floors" on the budget cards so users are visually warned if they plan a budget lower than their required obligations for that category. Provide a 1-click quick action button (e.g., "Set limit to required floor") to instantly resolve the warning or auto-create the budget.
3. **The Dashboard Pulse Check:** Introduce a compressed "Next 5 Days" widget on the Dashboard to give users a fast, actionable pulse check of immediate cashflow hits without overwhelming them with a 30-day view.
4. **Financial Truth Status:** Display a clear, deterministic status (EC-053) such as "Covered now," "Waiting on income," or "At risk" based on the balance of free money, expected income, and known obligations.

## User Stories

1. As a budget planner, I want to see a 30-day chronological timeline of my expected incomes and obligations on the Budgets page, so that I can visualize my cashflow and avoid planning a budget that will bounce a payment.
2. As a budget planner, I want my budget category cards to display a "Required Floor" if I have a debt or recurring expense tied to it, so that I don't accidentally set a limit lower than my legal obligations.
3. As a budget planner, I want a 1-click button to auto-fill my budget limits to perfectly match my minimum required floors, so that I do not have to manually type out my obligations.
3. As a mobile app user checking my finances on the go, I want to see a "Next 5 Days" timeline on my Dashboard, so that I can instantly know what money is coming in or going out before the weekend.
4. As a user reviewing my monthly plan, I want to see a clear "Financial Truth Status" (e.g., "Waiting on income"), so that I don't have to manually calculate if my plan is realistic.
5. As an advanced planner, I want the system to warn me if my planned spending threatens an upcoming obligation, so that I can reduce discretionary spending before I run out of cash.

## Implementation Decisions

- **Budgets Workspace:** 
  - Do NOT create a standalone "Expected Expenses" tab. Expected expenses will be visualized exclusively through the new Timeline UI and Category Floors.
  - The Budgets page will render the `category_floors` array returned from the backend, highlighting the minimum required amount for affected categories.
  - A new `FutureTimeline` component will be added to the Budgets page, plotting events chronologically (Expected Incomes, Debt payments, Installment payments, Recurring bills).
- **Dashboard:**
  - Introduce a `NextFiveDaysTimeline` widget. This will use the same data source as the 30-day timeline but filter for `date <= today + 5 days`.
  - Introduce a `FinancialTruthStatus` banner at the top of the Dashboard.
- **Backend Data Source:**
  - Create or extend an endpoint (e.g., `/timeline/future`) that aggregates and sorts `ExpectedIncome`, `InstallmentPayment`, `Debt` (payable), and `RecurringExpense` records by date.
  - The Financial Truth calculation will be a deterministic formula: `Planning capacity = free money now + expected income - known promises - desired cushion`.

## Testing Decisions

- **Good Tests:** We will test the external behavior of the timeline aggregation and budget floor validations. Tests will simulate complex months with interleaved incomes and obligations.
- **Modules Tested:**
  - `TimelineService`: Unit tests verifying that different database models (Debts, Expected Incomes, Recurring) are properly unified, sorted, and returned with the correct positive/negative cashflow impact.
  - `BudgetService` (Floors): Verify that `get_budget_category_floors()` accurately calculates minimums.
  - Integration tests for the Dashboard and Budgets API endpoints.
- **Prior Art:** Existing budget math tests and expense feed tests.

## Out of Scope

- A separate "Expected Expenses" creation wizard or tab. Expected expenses must be derived organically from actual Contracts (Debts, Installments, Recurring Expenses).
- AI-assisted explanations or probabilistic stress forecasting. The V1 timeline and opportunity cost warnings must remain strictly deterministic (EC-054).
- Modifying the core budgeting model or replacing categories. The new features act purely as an intelligence layer above the strict accounting ledgers (EC-052).

## Further Notes

This PRD formalizes the UX strategy discovered in EC-052, EC-053, and EC-054. It prevents the app from becoming bloated with duplicated tabs and focuses on placing the right information in the right mental context: deep 30-day simulation during Planning (Budgets page), and fast 5-day pulse checks during Execution (Dashboard). Published locally under `docs/prd/` with the `ready-for-agent` label.
