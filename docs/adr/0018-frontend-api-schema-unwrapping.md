# 0018. Frontend API Schema Unwrapping and Status Matching

## Context

During a deep-dive into the Expected Inflows creation workflow, we discovered two critical frontend bugs in the "Add Expected Inflow" modal (`ExpectedInflowDialogs.jsx`) that were preventing users from linking Debts and Refunds:
1. **The Debt Dropdown Bug:** The frontend was silently filtering out valid open Debts because it was strictly matching against a legacy string (`debt.status === "ACTIVE"`). Our backend architecture had previously shifted to mathematically derived statuses (`"OPEN"` vs `"CLOSED"`) per ADR-0005.
2. **The Refund Dropdown Bug:** The frontend dropdown displayed `"Expense #undefined"` for all Refund options. This occurred because the frontend was querying the `/expenses` endpoint, which returns a polymorphic feed payload (`ExpenseFeedItemOut`). The frontend attempted to parse domain fields (`title`, `id`, `event_type`) directly from the outer wrapper, rather than unwrapping the inner `ExpenseOut` object.

## Decision

We are formalizing the rules for how the React frontend consumes and processes backend data schemas to prevent these synchronization bugs.

### 1. Strict Payload Unwrapping
When the frontend fetches data from feed-oriented endpoints (like `/expenses`), it must explicitly unwrap the polymorphic wrapper to access the core domain entity.
- Components must map `item => item.expense` (or `item.merge_group`) before running filter logic.
- Filtering must rely on the correct inner schema properties (e.g., checking `expense.transaction_type` instead of incorrectly guessing `item.event_type`).

### 2. Elimination of Legacy Status Strings
Frontend components must aggressively deprecate hardcoded status string checks (like `"ACTIVE"`) that violate recent backend Architectural Decision Records.
- If a domain model transitions to mathematically derived states (like Debts in ADR-0005), the frontend must immediately update its filter criteria to match the new strict boundaries (e.g., `status === "OPEN"`).

## Consequences

- **Immediate Fixes:** The `ExpectedInflowDialogs.jsx` component will be refactored to change the Debt filter to `"OPEN"`, and to properly `map` and unwrap the `ExpenseFeedItemOut` array for Refunds.
- **Robustness:** By enforcing strict schema unwrapping, the frontend will accurately display titles, counterparties, and IDs for all complex nested objects.
