# Epic 6: Goal Lifecycle & Intent Protection

**Status:** Not Started  
**Depends On:** Epic 1 (Ledger Foundation) & Epic 2 (Debt Architecture — for PAY_OBLIGATION goals)

## Goal
Define the complete lifecycle rules and intent-driven state machine for Goals — Sarflog's "protected real money" containers. This epic formalizes when goals can be created, what statuses are valid per intent, how fulfillment works without ghost transactions, and the strict separation between saving (Goal) and spending (Project). These two ADRs are inseparable: one defines *what happens* in a goal's life, the other encodes *which of those things are allowed* based on intent.

## ADRs Included (Execution Sequence)

1. [ ] **[ADR 0007 — Goal Lifecycle, Date Boundaries & Fulfillment Interception](../adr/0007-goal-lifecycle-and-fulfillment.md)**
   - Three strict lifecycle rules:
     - **Decorative Start Dates:** Imported pre-existing goals may carry a `historical_start_date`, but it is 100% decorative (gamification, nudges, progress bars). No fake historical contributions — that would corrupt the wallet's opening balance snapshot.
     - **Goal → Project Graduation:** `FUND_PROJECT` goals are incubators for saving. When the user begins execution, the Goal is `GRADUATED` to a Project — one-way, permanently closed. Future top-ups happen inside the Project, never the dead Goal.
     - **Rejection of Ghost Transfers:** Off-wallet purchases (money locked in Wallet A, swiped on Wallet B) do NOT trigger auto-reimbursement ghost transfers. The expense hits Wallet B, the Goal completes, and locked funds in Wallet A are released back to Free Money. The user manually pays their credit card bill. The ledger mirrors banking reality.

2. [ ] **[ADR 0008 — Goal Intent Status Matrix & Overdue Rejection](../adr/0008-goal-intent-status-matrix.md)**
   - Maps each `GoalIntent` to its precise allowed behaviors:

   | Intent | Target Date | Valid DB Statuses | Overdue Handling |
   |--------|------------|-------------------|------------------|
   | `RESERVE` (Emergency Fund) | Disabled/Hidden | `ACTIVE`, `ARCHIVED` | Impossible — perpetual fund |
   | `PLANNED_PURCHASE` (Buy a Laptop) | Optional | `ACTIVE`, `COMPLETED`, `ARCHIVED` | UI badge only — soft warning |
   | `FUND_PROJECT` (Kitchen Remodel) | Optional | `ACTIVE`, `GRADUATED`, `ARCHIVED` | UI badge only — never `COMPLETED` directly |
   | `PAY_OBLIGATION` (Save for Mom's Loan) | Mandatory (from Debt) | `ACTIVE`, `COMPLETED`, `ARCHIVED` | Handled by Debt Engine |

   - **Golden Rule:** No `OVERDUE` in the database. It is always derived on the fly (`status in [ACTIVE] and target_date < today`). Storing it would require midnight cron jobs and create synchronization failures.

## Why These Two Together
- ADR 0007 says: "FUND_PROJECT goals graduate to Projects." ADR 0008 encodes that by giving `FUND_PROJECT` the status set `{ACTIVE, GRADUATED, ARCHIVED}` — notice `COMPLETED` is explicitly absent.
- ADR 0007 says: "No ghost transfers on fulfillment." ADR 0008 ensures the status transitions (`ACTIVE` → `COMPLETED`) only happen via explicit human action, not automated wallet reconciliation.
- You cannot implement one without the other.

## Execution Rules
- The `GoalStatus` enum must explicitly omit `OVERDUE`. Any existing `OVERDUE` values in the database must be migrated to `ACTIVE`.
- The frontend must dynamically toggle UI elements based on `GoalIntent`: hide target date for `RESERVE`, show "Graduate" instead of "Complete" for `FUND_PROJECT`, disable target date editing for `PAY_OBLIGATION`.
- Legacy `_settle_goal_funding_to_payment_wallets` auto-reimbursement logic (referenced in ADR 0007) is permanently deprecated and must be deleted.
