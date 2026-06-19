# Epic 2: Budget Intelligence & Backing

**Status:** Not Started  
**Depends On:** Epic 1 completion

## Goal
Answer the fundamental user question: *"How much money can I safely plan to spend this month?"* 
This epic transforms the budgeting system from a static envelope system into an intelligent, chronological cashflow simulator that understands debts, credits, expected incomes, and mandatory minimum floors.

## PRDs Included (Execution Sequence)

1. [ ] **[G17 - Expected Inflow Lifecycle](../prd/g17-expected-inflow-lifecycle.md)**
   - *Foundation:* Ensure the system accurately tracks incoming money (including debts owed to the user) with proper state machines (`PARTIALLY_RECEIVED`) and atomic wallet deposits.
2. [ ] **[G19 - Universal Inflow Wizards](../prd/g19-universal-inflow-wizards.md)**
   - *UI & Creation:* Build the guided wizard for logging expected and actual inflows to prevent accounting errors, and add `asset_id`/`refund_event_id` to the database.
3. [ ] **[G9 - Budget Explainability & Credit Survival](../prd/g9-budget-explainability-and-credit-survival.md)**
   - *Backend Math:* Introduce the massive architectural shift for credit card balance separation, "Category Floors" for obligations, and the final `plan_backing_remaining` formula.
4. [ ] **[G6 - Recurring Expenses Engine](../prd/g6-new-month-planner-and-recurring-floors.md) (Partial Extraction)**
   - *Floor Generation:* Extract the backend projection contract from G6 so that Expected Recurring Expenses automatically generate the Category Floors used by G9. (The full Month Setup Wizard UI will be deferred to a later epic).
5. [ ] **[G16 - Budget Backing UI Sync](../prd/g16-budget-backing-ui-sync.md)**
   - *Frontend Sync:* Swap legacy UI variables to consume the new math and display floor warnings natively on budget cards.
6. [ ] **[G20 - Future Timeline Simulator](../prd/g20-future-timeline-and-budget-cashflow-simulator.md)**
   - *Intelligence Layer:* Build the chronological 30-day timeline and 5-day Dashboard pulse widget using the unified Inflow and Obligation data.

## Execution Rules
- Execute strictly in sequence to maintain atomic Github commits and uncorrupted architecture.
