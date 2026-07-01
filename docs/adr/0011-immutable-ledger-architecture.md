# 11. Immutable Ledger Architecture

Date: 2026-06-30

## Status

Accepted

## Context

A robust financial application requires absolute trust. If a user deletes an expense or changes an income amount, and the database simply overwrites or hard-deletes the row (`db.delete()`), the system suffers from "amnesia." The history of what originally happened—and what the balances *used to be*—is permanently destroyed.

To prepare for enterprise-level scale, auditability, and absolute mathematical integrity, we must treat the system's ledger (e.g., `FinancialEvent`, `WalletLedger`, `EntityLedger`) as an immutable append-only log.

## Decision

We adopt a strict **Immutable Ledger Architecture** across the entire platform:

1. **No Hard Deletes for Financial Events:** Once a `FinancialEvent` is `POSTED`, it can never be hard-deleted (`db.delete()`). 
2. **The Reversal Pattern:** To "delete" an event, the system must update its status to `VOIDED`, and append a brand new `FinancialEvent` with `status = REVERSAL`. This reversal event inserts counter-balancing (negative) ledger legs to mathematically zero out the original transaction.
3. **No Amount Mutations:** Users are not allowed to update the amount, wallet, or category of a `POSTED` event. If the math needs to change, the user must Void the original event (triggering a reversal) and post a new corrected event. Metadata (like `title` and `description`) is the only mutable data on a posted event.
4. **Universal Application:** This architecture must be strictly applied across all modules, including Expenses (already implemented), Income, Expected Inflows, Debt Payments, and Goal Contributions.

## Consequences

- **Flawless Audit Trails:** Every penny's movement, including mistakes and corrections, is permanently recorded. The system can reconstruct the exact state of a user's wallet at any millisecond in the past.
- **Increased Engineering Complexity:** Backend deletion and update routers must be carefully written to generate and link Reversal events rather than relying on simple SQL `DELETE` or `UPDATE` statements.
- **Database Growth:** The database will grow faster due to retained voided rows and reversal events. In the future, a "Hard Delete Sweeper" cron job may be introduced to physically delete voided records that are older than statutory data retention limits (e.g., 7 years).
