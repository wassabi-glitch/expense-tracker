# 0024. Immutable Ledger Boundary — When the Void/Reversal Pattern Applies

Date: 2026-07-10

## Status

Accepted

## Context

Epicspart2 Tickets 1–6 established an append-only financial ledger in Sarflog:

- `post_financial_event` is the single write seam for all money movement.
- `void_financial_event` replaces hard-deletes with a compensating reversal.
- Correction reposts (Ticket 5) replace in-place mutation of posted events.
- Closed-period guardrails (Ticket 6) enforce a 5-day grace window for month-end cleanup.

During review, a fundamental design question came up: **which actions in the system actually need immutable-ledger treatment, and which do not?**

The answer was not obvious from the tickets alone. The concern was that some unknown future operation might silently require immutability, and the system would fail in production because nobody had named the boundary.

## Decision

**The immutable-ledger pattern applies if and only if a FinancialEvent has wallet legs with non-zero amounts — i.e., money left or entered a wallet.**

If an operation produced wallet movement, it must never be deleted or mutated in place. It must use the shared void/reversal seam (`void_financial_event`) or correction repost pattern.

If an operation did not produce wallet movement, immutability is unnecessary. The row is metadata, planning intent, or a projection — it can be updated or deleted directly.

### The one-line test

> **Did this operation produce wallet legs?** If yes → immutable. If no → mutable.

### Concrete examples

| Action | Wallet legs? | Immutable ledger? |
|--------|-------------|-------------------|
| Delete posted expense | ✅ Wallet outflow | ✅ Void, don't hard-delete |
| Delete posted income | ✅ Wallet inflow | ✅ Void, don't hard-delete |
| Edit income amount | ✅ Wallet inflow amount changed | ✅ Correction repost |
| Edit income note (metadata only) | ❌ Same wallet legs | ❌ Update in place |
| Delete debt (IOU, no cash transferred) | ❌ No money moved | ❌ Delete Debt row directly |
| Delete debt (cash borrowed, wallet received money) | ✅ Wallet inflow | ✅ Void the inflow event first |
| Cancel debt payment | ✅ Wallet outflow at payment time | ✅ Void the payment event |
| Reverse asset sale | ✅ Wallet inflow at sale time | ✅ Void the sale event |
| Undo wallet transfer | ✅ Both wallets touched | ✅ Void the transfer event |
| Delete budget | ❌ Spending permission, not money | ❌ Delete directly |
| Delete recurring template | ❌ Draft/intent, not posted money | ❌ Delete directly |
| Delete goal | ❌ Reservation of funds, not movement | ❌ Delete directly |
| Payment plan settlement | ✅ Wallet outflow | ✅ Void the settlement event |

### Why wallet legs are the boundary

Every money-touching action in Sarflog normalizes to the same shape:

```
FinancialEvent → WalletLedger (signed amounts per wallet)
              → EntityLedger (why the money moved)
```

`void_financial_event` works on any event regardless of `event_type` or `reference_type` — it negates every wallet leg, negates every entity leg, and links the reversal to the original. The math is universal because signed amounts are universal.

### What varies: side-effect cleanup

The void function handles the ledger. The caller handles domain-specific cleanup:

| Domain | After void, also call... |
|--------|--------------------------|
| Expenses | `check_budget_alerts(db, budget)` |
| Income | `reconcile_debt(db, debt_id)` |
| Debts | `reconcile_debt(db, debt_id)`, `sync_debt_goal_targets(...)` |
| Assets | Recalculate asset status |
| Payment plans | Recalculate plan schedule |

The caller pattern never changes — only the `reconcile_*` / `check_*` / `sync_*` calls after the void change.

### What this means for remaining tickets

Tickets 7 and 8 exist because debt, payment-plan, asset, and expected-inflow paths have not yet been converted to the shared seam. The conversion follows the same pattern for every module:

1. Replace `db.delete(event)` with `void_financial_event(db, event=event, ...)`.
2. Replace direct `WalletService.adjust_balance(...)` calls with a new `post_financial_event(...)`.
3. Add the domain-specific side-effect cleanup after the void.

No new patterns are needed. The seam already handles every case.

## Consequences

- Developers have a clear, one-question test for whether an operation needs immutable treatment.
- The shared `void_financial_event` seam is confirmed as the single correction mechanism for all money-touching actions.
- Non-money metadata (budgets, templates, drafts, goals without allocations) stays simple — no unnecessary reversal rows.
- Remaining hard-delete and direct-balance-mutation paths in debts, payment plans, assets, expected inflows, and projects are identified as conversion work (Tickets 7, 8), not as design unknowns.
