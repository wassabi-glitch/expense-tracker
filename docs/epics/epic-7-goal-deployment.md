# Epic 7: Goal Deployment & Protection

**Status:** Not Started  
**Depends On:** Epic 6 (for Project intersections)

## Goal
Establish strict lifecycle rules and safety guardrails for the moment a user actually *uses* the money they saved. This epic rips out dangerous "auto-reimbursement" ghost transactions, implements the unified Goal Fulfillment Interceptor pattern for off-wallet purchases, and enforces strict date boundaries and read-only protections for completed projects.

## PRDs Included

1. [ ] **[G11 - Goal Payment Philosophy & Auto-Reimbursement Deprecation](../prd/g11-goal-payment-philosophy.md)**
   - *Payment Workarounds:* Remove `_settle_goal_funding_to_payment_wallets` logic. Build the UI and backend logic to correctly release goal funds without hitting the monthly budget (or providing a toggle for Reserve funds) when a user pays from a non-funding wallet.
2. [ ] **[G7 - Projects and Goal Deployment](../prd/g7-projects-and-goal-deployment.md)**
   - *Project Protections:* Enforce `project.start_date <= expense_date <= project.target_end_date` for expense tagging. Build the "Reopen Project" action to keep completed projects as immutable reports.

## Relevant Edge Cases
These critical edge cases define the Goal Fulfillment Interceptor pattern:

- **EC-162: Wallet Goal Collision & Protection Breaches**
  - Triggers a warning if generic expenses mathematically drop the wallet balance below its reserved goal allocations.
- **EC-163: Goal Fulfillment Interceptor vs. Protection Breach**
  - A smart filter that intercepts the EC-162 warning and asks the user: "Did you mean to use your reserved Goal funds for this purchase?" to cleanly convert a generic expense into a Goal Fulfillment.

## Execution Rules
- Execute G11 first to remove the ghost-transaction technical debt before adding new interceptor UI flows.
- Make sure G7 validations are added centrally to the expense posting service so they apply to Quick Adds, Session drafts, and Goal fulfillments equally.
