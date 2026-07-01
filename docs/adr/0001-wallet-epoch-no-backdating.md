# Wallet Epoch: No Backdating Before Wallet Creation

A wallet's initial balance is a sealed snapshot of reality — the net result of every prior financial event. Allowing transactions dated before the wallet's creation date would double-count money that is already reflected in that opening balance.

**Decision:** No transaction (expense, inflow, transfer, debt settlement) may be dated before the wallet's `created_at` date. The enforcement is at **date granularity**: `transaction_date >= wallet.created_at.date()`. Same-day transactions are allowed; the implicit contract is that the user's entered balance reflects reality as of the start of that day.

**Why date-level, not stricter (next-day only):** Blocking the entire creation day punishes users who set up the app and immediately want to log a purchase. The small same-day honesty gap is the user's responsibility, and the app will display an onboarding message explaining the contract.

**Applies uniformly:** Cash wallets snapshot owned money. Credit wallets snapshot outstanding balance owed. The no-backdating rule applies identically to both — the initial balance already accounts for all prior activity regardless of accounting type.

**Per-wallet, not global:** Each wallet has its own epoch (its own `created_at`). Wallet A created June 1st and Wallet B created June 15th have independent boundaries.
