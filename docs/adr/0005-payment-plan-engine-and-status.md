# ADR 0005: Payment Plan Engine, Statuses, and Budget Boundary

## Status
Accepted

## Context
Payment Plans (e.g., Mortgages, Auto Loans, Store Installments) are formal, strictly scheduled contracts. Previously, the architecture attempted to mirror real-world complexities by introducing numerous statuses (e.g., `SKIPPED`, `DEFAULTED`, `CANCELLED`) and struggled with how to handle hidden charges and budget limits when payments were made. This led to state-machine complexity and silent backend failures when a payment triggered a budget limit violation mid-month.

## Decision

We are brutally simplifying the state machine to protect mathematical truth, while establishing a strict intercept pattern for Budget interactions.

### 1. Parent Plan Statuses
A Payment Plan will now have only two states:
- **`OPEN`**: The plan is active and requires the user's attention.
- **`CLOSED`**: The plan is finalized and dead (whether successfully paid off, forgiven, or defaulted). 
*Why:* The Parent Status only dictates UI visibility. The true story of *why* it closed is strictly told by the Ledger Entries (e.g., closed by a Payment vs closed by a Write-Off).

### 2. Schedule Row Statuses
Rows (`PaymentPlanPaymentStatus`) will be strictly limited to:
- **`PENDING`**: The payment is scheduled.
- **`PARTIAL`**: The payment is partially fulfilled.
- **`PAID`**: The payment is completely fulfilled.
*Why:* `SKIPPED` breaks the total balance math. `OVERDUE` is a computed property (`status in [PENDING, PARTIAL] and due_date < today`) and will not be stored in the database.

### 3. The Waterfall Spillover Engine
The current backend Waterfall Engine is architecturally correct and is officially preserved:
- Payments are made to the Parent Plan, not the Row.
- The engine sweeps the schedule, paying off `CHARGE` rows first, then spilling over into the oldest `PRINCIPAL` rows.
- Charges/Late Fees are explicitly injected into the schedule as rows with `component_type=CHARGE`.

### 4. The Strict Limit-Based Budget Boundary (The Intercept Modal)
Sarflog enforces Strict Limit-Based Budgeting. If the Waterfall Engine attempts to process a payment (e.g., a hidden 10,000 UZS `DEBT_CHARGES` fee) and the user has no Budget Limit established for that category in the current month:
- **Backend Rule:** The backend MUST NOT auto-materialize the budget mid-month. It must instantly halt and throw a structured `400 Bad Request` (`expenses.budget_required`), including the missing category and required amount.
- **Frontend Rule (The Intercept Modal):** The frontend catches this error and prevents the UI from crashing. It overlays a context-aware modal prompting the user to explicitly set up the missing Budget Limit, funding it from available "Plan Backing" (reallocating if necessary), before resuming the payment flow.

## Consequences
- Massive reduction in UI and Backend state-filtering logic (everything is just `is_open`).
- Schedule rows mathematically sum up to the total remaining balance flawlessly.
- Users are never confused by silent payment failures; they are gently guided to fix their budget limits without losing their context.

### 5. Row Actions & Forgiveness Architecture
To guarantee flexibility for all real-world contract scenarios, actions are divided between the Row level and the Parent level.

**Row Actions:**
1. **Pay (Full or Partial):** Standard wallet-touching payment.
2. **Edit Due Date:** Extending the grace period for a specific row without breaking the overall schedule.
3. **Defer / Push to End:** Removing a row and appending a new one to the end of the loan (e.g., Payment Holidays).
4. **Row-Based Forgiveness (Write-Off):** Wiping out a specific row (e.g., "12th payment is on us"). This automatically propagates up as an `ADJUSTMENT` ledger entry that reduces the Parent Plan's `remaining_amount`.

**Parent Actions:**
1. **Plan-Based Forgiveness (Principal Reduction):** A bulk write-off (e.g., settling a defaulted loan for less, or a 20% principal discount). This requires recalculating the schedule, or simply letting the Waterfall Engine void the final rows because the balance hits zero early.
2. **Add Charge:** Injecting a Late Fee as a new `CHARGE` row into the schedule.
3. **Close:** Force-closing a defaulted plan.

### 6. The Imported Path (Historical Pre-Existing Plans)
Payment Plans must follow the same strict Wallet Epoch decoupling as Debts (ADR 0003). If a user imports a 36-month loan that started 12 months ago:
- **The Math (Reality):** The system strictly enforces `IMPORTED_BALANCE`. It asks only for the *remaining balance today* and the *remaining schedule*. This guarantees zero historical money leaves the current Wallet, preserving the Wallet Epoch snapshot.
- **The Psychology (Decorative UI):** The system optionally accepts `historical_start_date` and `historical_original_amount`. These are stored purely as decorative metadata to draw progress bars in the UI, and never touch the system's strict financial ledger.
