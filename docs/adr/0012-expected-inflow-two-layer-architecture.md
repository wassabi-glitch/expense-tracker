# 0012. Expected Inflow Two-Layer Architecture & Derived State

## Context

The Expected Inflows feature handles money the user expects to receive in the future (e.g., salaries, debts being repaid, refunds). The previous implementation suffered from several architectural and UX issues:

1. **State Mutation Bugs:** The Promise-level status was calculated using a flawed decision tree (e.g., a 99% received and 1% written-off inflow would be permanently branded as `WRITTEN_OFF`).
2. **Redundant Status Storage:** We were storing derived states (`PARTIALLY_RECEIVED`, `RESOLVED`, etc.) at the Promise layer, violating the immutable ledger pattern established in ADR-0011.
3. **UI/DB Mismatch:** The frontend attempted to display the Promise (the "What") and filter it by the Schedule (the "When") simultaneously. This resulted in confusing displays, such as a $60k yearly salary contract appearing under a specific month's tab, rather than just the specific $5k monthly paycheck.

## Decision

We are explicitly embracing a **Two-Layer Architecture** for Expected Inflows, separating the Agreement (Promise) from the Delivery (Schedule), both in the database and the UI.

### 1. Database Storage: Two Distinct Layers
- **The Promise Layer (`expected_inflow_promises`):** Represents the initial agreement/contract. 
  - The `status` column is simplified to represent pure human intent: **`OPEN`** (active, tracking) and **`CLOSED`** (terminal, done). 
  - The `original_amount` is strictly immutable. It never changes, even if the payment is rescheduled or split.
  - **No `close_reason` column:** The Promise table does not store a `close_reason`. The previous architecture "faked" a `close_reason` in the API output based on the 5-state enum. Under OPEN/CLOSED, the backend dynamically derives this detail from the immutable ledger.
- **The Schedule Layer (`expected_incomes`):** Represents the reality of the calendar (cashflow).
  - The `status` column retains its detailed 8-state enum (e.g., `EXPECTED`, `SUPERSEDED`, `RESOLVED`, `WRITTEN_OFF`) and relies on `close_reason`. This acts as an immutable audit trail of what specifically happened to that chunk of money on that specific date.

### 2. Backend Derivation (The Math)
- The backend API will no longer send the raw database Promise status to the frontend.
- Instead, it dynamically derives a **Display State** based strictly on the immutable ledger (Realizations and Write-Offs) against the `original_amount`. 
- **Examples:**
  - `OPEN` + Outstanding = `"EXPECTED"`
  - `CLOSED` + 100% Received = `"FULLY_RECEIVED"`
  - `CLOSED` + 99% Received + 1% Written Off = `"SETTLED"`
  - `CLOSED` + 0% Received + 100% Written Off = `"WRITTEN_OFF"`

### 3. UI Architecture: The Two-Tab Pattern
To fix the cognitive dissonance in the UI, we split the presentation to match the database:
- **Tab 1: "Agreements / Promises" (The "What")**
  - A master list of all contracts. No month/date filtering. Driven by search. Clicking a Promise opens the detailed drawer showing its history.
- **Tab 2: "Cashflow / Schedules" (The "When")**
  - A calendar-based view showing the specific child schedules due in the currently selected month.

### 4. Smart Forms for Creation
Despite the two-layer database architecture, the UI will *not* force the user to create a Promise and Schedule separately. The "Add expected inflow" modal acts as a smart form: it captures the Total Contract Amount and the Initial Delivery Date simultaneously. The backend immediately splits this into one Promise row and one Schedule row upon save.

### 5. Rescheduling Logic
Rescheduling operates strictly on the Schedule layer. When a payment is delayed or split:
- The original Schedule is marked `SUPERSEDED` (close_reason: "RESCHEDULED").
- New child Schedules are created with the new dates and amounts.
- The Promise `original_amount` remains completely untouched, preserving the history of the original contract.

## Consequences

- **Correctness:** The "1% write-off" bug is eliminated because status is derived mathematically from the immutable ledger. "Settled" accurately describes a mostly-fulfilled contract.
- **Clarity:** The user's mental model now perfectly matches the database architecture. They can see their high-level agreements separate from their monthly cashflow.
- **Auditability:** The Schedule layer retains a perfect, immutable history of all date changes, splits, and cancellations without polluting the high-level Promise state.
- **Migration Required:** A database migration is required to alter `ExpectedInflowPromiseStatus`. Existing `EXPECTED`/`PARTIALLY_RECEIVED` values migrate to `OPEN`, and `RESOLVED`/`CANCELLED`/`WRITTEN_OFF` migrate to `CLOSED`.
