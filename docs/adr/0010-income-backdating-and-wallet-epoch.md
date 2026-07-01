# 10. Income Backdating and the Wallet Epoch Boundary

Date: 2026-06-30

## Status

Accepted

## Context

When a user creates a Wallet in Sarflog, they establish a starting balance (e.g., 5,000,000 UZS) at a specific point in time (the "Wallet Epoch"). This starting balance mathematically represents the net sum of all historical income and expenses up to that exact second. 

If a user were allowed to log a historical Income (e.g., a past salary payment) with a date *prior* to the Wallet Epoch, the system would add those funds to the current wallet balance. This would break the integrity of the ledger, because that historical income is *already mathematically baked into* the starting balance they declared.

Additionally, Expected Inflows (promises of future money) must conceptually occur in the future or present, not in the past.

## Decision

We enforce a strict chronological boundary around the Wallet Epoch for all incoming money:

1. **No Income Backdating:** The system will strictly reject any `Income` transaction with a date earlier than the user's Wallet Epoch date.
2. **No Past Expected Inflows:** The system will reject the creation of any `Expected Inflow` (promise) with a date earlier than the user's Wallet Epoch date.
3. **Historical Data:** If users wish to track their financial history prior to using Sarflog, they must rely on external tools (e.g., Excel). Our ledger's source of truth begins strictly at the Epoch.

## Consequences

- **Guaranteed Mathematical Integrity:** The Opening Balance remains an uncorrupted snapshot of the user's wealth at the time of onboarding.
- **Clear UX Boundaries:** Users learn quickly that Sarflog is a forward-looking and present-focused tool, avoiding confusing double-counting of historical funds.
