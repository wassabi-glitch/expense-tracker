# ADR 0007: Goal Lifecycle, Date Boundaries, and Fulfillment Interception

## Status
Accepted

## Context
As we establish the rules for how users onboard and deploy their money in the Goals system (Epic 7), we must ensure that Goal mechanics do not violate the core "Reality-First" budgeting philosophy and the Wallet Epoch boundaries established in earlier ADRs.

Previously, the system struggled with:
1. Handling pre-existing "real world" goals for new users without generating fake historical ledger entries.
2. The distinction between a Goal (saving) and a Project (execution).
3. "Off-wallet purchases" where a user has Goal money locked in a Savings wallet but uses a Credit Card to make the actual purchase, leading to dangerous "auto-reimbursement" ghost transactions.

## Decision

We are formalizing three strict rules regarding the Goal lifecycle:

### 1. Goal Start Dates are Purely Decorative Metadata
If a user imports a pre-existing Goal (e.g., they started saving for a car 2 years ago), they may optionally assign a `historical_start_date` to the Goal.
- **Rule:** This date is 100% decorative. It is used strictly for UI gamification, nudges, and progress bars.
- **Why:** Generating historical "contributions" before the user's Wallet Epoch (Day 1) would mathematically corrupt the wallet's opening balance snapshot.

### 2. Strict Separation of Goal (Incubator) and Project (Execution)
A `FUND_PROJECT` Goal is purely an "incubator" for the saving phase. It digitally locks money inside a wallet over time.
- **Rule:** When the user is ready to begin the execution phase (e.g., remodeling the kitchen), the Goal is `GRADUATED` to a Project.
- **Why:** Goal Graduation is a one-way street. Once graduated, the Goal is permanently closed. If the project goes over budget, the user must allocate funds directly to the Project's budget pool, not to the dead Goal. This prevents ambiguous states where money is simultaneously being saved and spent in the same container.

### 3. Fulfillment Reality (The Rejection of Ghost Transfers)
When a user fulfills a Goal using an "off-wallet purchase" (e.g., money is locked in Wallet A, but they swipe Wallet B), the system will **not** generate "auto-reimbursement" ghost transfers between the wallets to cover the math.
- **Rule:** The system enforces strict physical reality. The expense is recorded against Wallet B (dropping its balance). The Goal is marked `COMPLETED`. The digitally locked funds in Wallet A are instantly "released" back into the user's *Free Money Now* pool.
- **Why:** Ghost transfers falsify banking reality. By simply releasing the funds in Wallet A, the user is mathematically whole, and they retain the agency to explicitly use that now-free money to pay off the Wallet B credit card bill whenever they choose. This ensures the app's ledger perfectly mirrors their real-world bank statements.

## Consequences
- The database schema for Goals will never require a functional `start_date` for ledger calculations.
- Any legacy `_settle_goal_funding_to_payment_wallets` auto-reimbursement logic is permanently deprecated.
- Users will experience slightly more friction (having to manually pay their credit card bills after an off-wallet goal purchase), but in exchange, they receive an absolute guarantee of ledger integrity.
