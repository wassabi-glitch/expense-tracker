# Epic 4: Expected Inflow Architecture

**Status:** Not Started  
**Depends On:** Epic 1 (Ledger Foundation — especially ADR 0011 Immutable Ledger)

## Goal
Build the complete architectural stack for tracking money the user expects to receive — salaries, client payments, debts being repaid, refunds. This epic defines how Expected Inflows are stored (two-layer database), displayed (progressive disclosure UI), and governed (domain logic constraints). These three ADRs form a strict sequential trilogy: database → frontend → business rules.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0012 — Expected Inflow Two-Layer Architecture & Derived State](../adr/0012-expected-inflow-two-layer-architecture.md)**
   - The database foundation. Separates the Agreement (Promise layer — `OPEN`/`CLOSED` only) from the Delivery (Schedule layer — detailed 8-state enum with `close_reason`). The backend derives display states (`EXPECTED`, `FULLY_RECEIVED`, `SETTLED`, `WRITTEN_OFF`) mathematically from the immutable ledger, never storing them. Smart forms hide the two-layer complexity from users during creation. Rescheduling operates strictly on the Schedule layer via `SUPERSEDED` chains.

2. [ ] **[ADR 0013 — Expected Inflow Progressive Disclosure UI](../adr/0013-expected-inflow-progressive-disclosure-ui.md)**
   - The frontend architecture. Built directly on 0012's two-layer split:
     - **Tab 1 (Agreements):** High-level contracts with the Tri-Color Progress Bar (green received / red written off / empty outstanding). No dates, no action buttons on rows.
     - **Tab 2 (Cashflow):** Calendar-based schedule chunks due in the selected month. Action buttons live here.
     - **Details Drawer:** Inline `Receive`, `Reschedule`, `Write off` buttons on each Schedule Card. A Unified Timeline replaces the raw database table dumps.
     - **No orphaned pages:** Clicking a Schedule row deep-links to the parent Promise drawer.

3. [ ] **[ADR 0014 — Expected Inflow Domain Logic & Ledger Reversals](../adr/0014-expected-inflow-domain-logic-and-reversals.md)**
   - The business rules that make the engine mathematically airtight:
     - **100% Promise Cap:** No over-receiving. Excess must be logged as separate income.
     - **Derived Lifecycle:** Promise auto-closes at `Outstanding == 0`, auto-reopens on reversal. No manual close/reopen.
     - **Reversal Rules:** Financial actions (receipts, write-offs) reversible in any order. Structural actions (reschedules) reversible only at the leaves of the tree.
     - **No Edit/Delete:** Schedule rows cannot be edited or hard-deleted. Users must use Reschedule, Write-off, Reverse, or Cancel — all of which preserve the audit trail.

## Why This Order
- ADR 0012 defines *where* data lives (Promise vs Schedule). Without this split, the UI and rules have no foundation.
- ADR 0013 defines *how* users see and interact with that data. It can only be designed once the two-layer database exists.
- ADR 0014 defines *what users can and cannot do*. The reversal rules (leaves-only for reschedules) and the 100% cap directly reference the Promise/Schedule architecture from 0012 and the Tri-Color bar from 0013.

## Execution Rules
- ADR 0012 requires a database migration to simplify `ExpectedInflowPromiseStatus` from the old 5-state enum to `OPEN`/`CLOSED`.
- ADR 0013's Tri-Color Progress Bar and Unified Timeline are new frontend components that will be reused in other features — build them as isolated, testable components.
- ADR 0014's "Leaves Only" reversal rule for reschedules is the highest-complexity validation in this epic. It requires tree traversal logic and must be covered by integration tests with multi-level reschedule chains.
