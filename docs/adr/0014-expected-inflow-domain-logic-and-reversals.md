# 0014. Expected Inflow Domain Logic and Ledger Reversals

## Context

Following the architectural updates in ADR-0012 and ADR-0013, we needed to establish strict domain logic rules for the Expected Inflows engine to prevent accounting discrepancies ("leaky buckets") and ensure the immutable ledger remains robust. 

Specifically, we needed to address four edge cases:
1. What happens when a user receives more money than the contract states?
2. When does a Promise officially close, and how does it reopen?
3. In an immutable ledger, can a user reverse any action at any time?
4. Should users be allowed to directly edit or delete financial schedule rows?

## Decision

We are adopting strict mathematical and ledger-based constraints for the Expected Inflows domain logic.

### 1. The 100% Promise Cap (No Over-receiving)
A Promise represents a strict contract. It cannot be over-fulfilled.
- **Rule:** The system will reject any receipt payload where `(Total Received + Total Written Off + New Receipt) > Original Amount`.
- **Handling Excess:** If a user receives a bonus, tip, or overpayment that exceeds the original contract, the system will instruct them to record the excess as a separate standard income entry. 
- **Schedule-Level Exception:** A user *can* over-receive on a specific Schedule chunk (which automatically applies the excess to other active schedules), provided it does not breach the total Promise cap.

### 2. Derived Promise Lifecycle (Auto-Closing)
There is no manual "Close" or "Reopen" action for a Promise.
- **Auto-Close:** A Promise automatically transitions to `CLOSED` the exact millisecond its `Outstanding Amount == 0`. Once closed, all financial action buttons (`Receive`, `Reschedule`, `Write-off`) are locked.
- **Auto-Reopen:** A Promise automatically transitions back to `OPEN` if a past ledger action (like a receipt or write-off) is reversed, pushing the `Outstanding Amount` above zero again.

### 3. Immutable Ledger Reversals
To provide good UX without breaking the ledger, we split reversal rules into two categories based on the action type:
- **Financial Actions (Receipts, Write-offs): ANY ORDER.** These can be reversed at any time, chronologically or randomly. Reversing them simply appends a negative compensating row to the ledger and recalculates the Promise math.
- **Structural Actions (Reschedules): LEAVES ONLY.** Rescheduling creates a "tree" (a superseded parent spawns child schedules). A reschedule action can *only* be reversed if the resulting child schedules are completely untouched (still `EXPECTED` with 0 received/written-off). If cash has already been applied to a child, the tree is locked.

### 4. Forbidding Schedule Edit and Delete
We explicitly forbid raw `Edit` and `Delete` actions on Schedule rows (`expected_incomes` table) to protect the ledger's integrity.
- **No Edit:** Changing a date or amount is a historical financial event. Users must use the **`Reschedule`** action, which properly supersedes the old schedule and creates a new one, preserving the audit trail. *(Note: Text notes can be edited as they do not affect math).*
- **No Delete:** A Schedule is mathematically chained to the Promise (`sum(active_schedules) == outstanding_promise`). Hard-deleting a schedule breaks this math. Users must use mathematically sound actions to remove a schedule:
  - **`Reverse`** (if created by mistake).
  - **`Write-off`** (if the money is lost forever).
  - **`Cancel`** (if the entire parent Promise contract is voided).

## Consequences

- **Integrity:** It is mathematically impossible for money to "vanish" from the Expected Inflows system. Every dollar is strictly accounted for.
- **Predictability:** The Tri-Color Progress Bar (ADR-0013) is guaranteed to never exceed 100%, keeping the UI clean and the mental model intact.
- **Development Complexity:** The backend must implement robust validation logic for the "Leaves Only" rule on reschedule reversals and enforce the 100% receipt cap.
