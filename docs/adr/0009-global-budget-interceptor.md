# ADR 0009: The Global Budget Interceptor Pattern (In-Context Resolution)

## Status
Accepted

## Context
Sarflog enforces strict limit-based budgeting (ADR 0006). A transaction cannot be posted against a budget category if that category has no defined limit for the current month. 

When a user (or an automated engine) attempts to log an expense, settle a debt, or process a payment plan charge against an unbudgeted category, the backend will reject it to protect the mathematical integrity of the plan.

If the frontend handles this rejection by simply throwing an error and forcing the user to navigate away to the Budgets page to fix the issue, we create severe friction. Users lose their context (the drafted transaction) and are highly likely to abandon the workflow or the app entirely.

## Decision

We are establishing the **Global Budget Interceptor Pattern** across the entire application to provide "In-Context Resolution" (Just-in-Time Setup).

1. **The Backend Contract:** When any transaction attempts to hit an unbudgeted category, the backend MUST instantly halt and return a structured `400 Bad Request` (e.g., `expenses.budget_required`). This payload must include the missing category ID and the transaction's proposed amount.
2. **The Frontend Universal Component:** The frontend must implement a universal "Budget Interceptor" modal. This component listens for the structured 400 error across all transaction flows (Quick Add, Debt Settlement, Payment Plans, CSV Import).
3. **In-Context Resolution:** Instead of crashing or navigating away, the frontend freezes the user's current transaction draft and overlays the Interceptor modal right on the current screen.
4. **The Resolution Flow:**
   - The modal informs the user of the missing category.
   - It pre-fills a recommended budget limit (equal to or greater than the attempted transaction amount).
   - It displays the user's current available "Plan Backing" (Free Money Now).
   - Upon the user confirming the new limit, the frontend smoothly chains two API calls under the hood: (1) Create/Update the Budget Limit, and (2) Re-submit the original transaction draft.

## Consequences
- **Zero Context Loss:** Users never have to abandon a workflow to satisfy a system prerequisite. 
- **Unified Engineering:** The frontend team builds the Interceptor component once and mounts it globally, rather than writing custom error handling for every single form in the app.
- **Empowered Discipline:** We maintain our strict reality-first budgeting rules without sacrificing user experience. The system remains mathematically strict, but feels incredibly forgiving, smooth, and helpful to the user.
