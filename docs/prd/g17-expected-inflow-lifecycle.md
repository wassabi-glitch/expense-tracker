# PRD: G17 - Expected Inflow Lifecycle & Realization

Labels: `ready-for-agent`

## Problem Statement

Sarflog's current "Expected Income" system suffers from three major flaws that cause confusion and corrupt financial history. First, the UI terminology ("Expected Income") implies only salary or earned income, even though the G4 backend supports debt receivables. Second, clicking "Receive" merely changes a text status without actually depositing any real money into a wallet, failing to bridge the gap between planning and reality. Third, the system lacks a proper accounting lifecycle: there is no safe way to handle partial payments, write-offs, or delays without manually overriding statuses or deleting rows (which permanently destroys the user's historical audit trail of what they originally planned versus what they actually received).

## Solution

Rebuild the expected inflow system around a mathematically driven state machine and an atomic "Realization" workflow. 

First, rename the UI to "Expected Inflows" to accurately reflect that it tracks any incoming money (salary, debt paybacks, etc.). 
Second, replace the simple "Receive" button with a Realization Modal that asks the user exactly how much money arrived and which wallet or wallets it went to, atomically creating the real ledger transaction and linking it to the expectation.
Third, implement a strict 4-state lifecycle (`EXPECTED`, `PARTIALLY_RECEIVED`, `RESOLVED`, `CANCELLED`) where the active state is automatically computed based on how much money has been linked (`received_amount`), rather than relying on manual status dropdowns.

## User Stories

1. As a budget user, I want the UI to say "Expected Inflows" instead of "Expected Income," so that I know I can plan for debt paybacks and refunds here as well.
2. As a budget user, I want clicking "Receive" to prompt me for an amount and a wallet, so that real money is deposited into my ledger at the exact same time the expectation is marked as received.
3. As a budget user, I want partial receipts to automatically shift the inflow to `PARTIALLY_RECEIVED`, so that I can track that I am still owed the remaining balance without manual math.
4. As a budget user, I want the remaining expectation to automatically update my budget backing, so that my plan tightens or loosens based on exact partial receipts.
5. As a budget user, I want a "Force Resolve" (write-off) button for partial payments, so that if the counterparty defaults on the remaining balance, I can close the record without deleting history.
6. As a budget user, I want a "Cancel" button for expectations that yield 0 UZS, so that I can close cancelled contracts without deleting the audit trail.
7. As a budget user, I want terminal expectations (`RESOLVED` and `CANCELLED`) moved to a separate History tab, so that my active planning workspace remains uncluttered.
26. As a budget user, I want overdue expected inflows to show a visual warning badge rather than changing database states, so that I know the money is late but still technically expected.
27. As a budget user, I want changing the month of a partially received inflow to automatically split the record, so that my past month's history is perfectly preserved while the remaining balance safely rolls forward into the new month.
10. As a budget user, I want the "Delete" button hidden once real money is attached, so that I don't accidentally corrupt my ledger by deleting partially received history.
11. As a budget user, I want a "Re-Open" button on resolved records, so that if a bounced transfer is reversed or zombie debt arrives months later, I can wake the record up and recalculate its status based on the current cash truth.

## Implementation Decisions

- **Terminology:** Rename all frontend UI references from "Expected Income" to "Expected Inflows".
- **Realization Modal:** Introduce a modal for the "Receive" action that accepts `actual_amount` and `wallet_allocations`, where allocation amounts must sum to the actual amount. A single `wallet_id` can remain as a compatibility shortcut, but the primary contract should support more than one destination wallet.
- **Atomic Processing:** The backend `receive` endpoint must perform a database transaction that creates a `LedgerEntry` (Income or Debt Payment) AND updates the `ExpectedIncome` row (`received_amount` += amount, and link the transaction ID).
- **Math-Driven State Machine:** 
  - `EXPECTED`: `received_amount == 0`
  - `PARTIALLY_RECEIVED`: `0 < received_amount < expected_amount`
  - `RESOLVED`: Terminal state. Hit automatically if `received_amount >= expected_amount`, or manually forced.
  - `CANCELLED`: Terminal state. Manually forced if `received_amount == 0`.
- **UI Architecture:** Split the Expected Inflows view into two tabs: "Active Inflows" (EXPECTED, PARTIALLY_RECEIVED) and "History" (RESOLVED, CANCELLED).
- **Mutability Rules:**
  - `EXPECTED`: All fields editable. Delete allowed.
  - `PARTIALLY_RECEIVED`: `expected_amount` becomes read-only. Delete forbidden.
  - `RESOLVED` / `CANCELLED`: All fields read-only. Delete forbidden. Re-Open allowed.
- **Re-Open Logic:** Does not hardcode a destination state. Removes the terminal flag and lets the math (`received_amount` vs `expected_amount`) determine if it lands in `EXPECTED` or `PARTIALLY_RECEIVED`.
- **Auto-Split on Month Shift:** When a user changes the month of a `PARTIALLY_RECEIVED` record, the backend automatically splits it into two rows:
  - Row 1 (Original Month): `expected_amount` is lowered to equal `received_amount`, automatically forcing the status to `RESOLVED` and locking the past month's history.
  - Row 2 (New Month): A brand new row is created with `expected_amount` equal to the remaining balance, `received_amount` = 0, starting its life as `EXPECTED`. A `parent_id` is added to track its origin.

## Testing Decisions

- E2E or Integration tests using the new `/expected-incomes/{id}/receive` API seam to ensure the wallet `LedgerEntry` and the `ExpectedIncome` update happen atomically.
- Verify state transitions: 0 UZS receipt leaves it `EXPECTED` (if allowed), partial receipt moves it to `PARTIALLY_RECEIVED`, and full receipt moves it to `RESOLVED`.
- Verify that editing `expected_amount` is rejected by the backend if `received_amount > 0`.
- Verify the Auto-Split logic: Changing the month of a `PARTIALLY_RECEIVED` record correctly closes the original row and creates a new `EXPECTED` row in the target month with the remaining balance.
- Verify that Re-Open on a 0 UZS resolved record yields `EXPECTED`, while Re-Open on a partial record yields `PARTIALLY_RECEIVED`.
- Prior art for atomic ledger + domain updates exists in `app/routers/installments.py` (e.g., mark-paid routes).

## Out of Scope

- Building a full accounts-receivable aging report.
- Automatically creating Expected Inflows from every new debt (users still manually choose which debts to plan against).
- Automatically rolling over expected inflows to the next month if they are overdue (users must manually edit the date).

## Further Notes

This PRD formalizes the enterprise-grade accounting practices for accrual vs. cash lifecycle management. It bridges the gap discovered during G4 review by ensuring expectation history is never destroyed, partial payments are safely tracked, and real wallet money is successfully minted when an expectation is realized. Published locally under `docs/prd/` with the `ready-for-agent` label.
