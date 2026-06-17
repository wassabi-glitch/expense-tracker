# G11: Goal Payment Philosophy & Auto-Reimbursement Deprecation

## Problem Statement

When a user has saved money for a goal in specific wallets, but pays for the goal's objective using a *different* wallet (one that didn't fund the goal), the system currently lacks a clean architectural philosophy. Historically, there was an attempt to use auto-generated "reimbursement" transfers (e.g., `_settle_goal_funding_to_payment_wallets`). 

This approach creates a messy, confusing ledger state filled with system-generated transfers that the user didn't explicitly authorize, making their financial history difficult to parse. Furthermore, the handling of budget limits for these "off-wallet" payments is inconsistent. While `enforce_monthly_budget_limits` exists in the expense posting service, it is effectively dead code, meaning expenses always hit the budget unless they are from an isolated project.

## Solution

The system will completely deprecate and remove all automatic reimbursement and auto-transfer logic from the codebase. Instead, the application will enforce a strict two-pronged approach for goal payments:

1. **Pre-Purchase (Prepare Payment):** The primary and recommended flow. Users must use the "Prepare Payment" UI *before* making the real-world purchase to explicitly move goal funds into the desired payment wallet.
2. **Post-Purchase (The Unified Workaround Pattern):** If the user bypasses preparation and pays from a non-funding wallet, they use the "Already paid from wrong wallet" UI flow. The system will record the expense, apply the correct budget rule based on the goal intent (including providing a toggle for Reserve funds), and explicitly release the equivalent funds from the goal's funding wallet(s) back to the user's free balance. 

## User Stories

1. As a user, I want my ledger to perfectly reflect my real-world actions, so that I don't see confusing, system-generated wallet-to-wallet transfers that I never actually made.
2. As a user who forgot to use "Prepare Payment" for a **Planned Purchase**, I want to record my purchase as "Achieved outside reserved funds." The system should release my reserved funds and **NOT** hit my monthly budget, because the financial impact was already absorbed when I saved the money (CapEx).
3. As a user who paid for a **Reserve Fund** need from a regular checking account, I want to record the expense and **I MUST see a toggle to choose whether it hits my monthly category budget or not**. The system should release my reserved funds back to me, and by default it should hit the budget for visibility, but I need the toggle to opt out if the emergency is catastrophic.
4. As a user who made a purchase for a **Fund Project** (Isolated) from a non-funding wallet, I want to record the expense. The system should release the equivalent project stash back to my free balance and **NOT** hit my monthly budget, because it is isolated by design.

## Implementation Decisions

### The Unified Pattern

| Intent | Record Expense | Release Goal Funds | Hit Monthly Budget | Reasoning |
| :--- | :--- | :--- | :--- | :--- |
| **Planned Purchase** | ✅ | ✅ | ❌ | Pre-planned CapEx, already absorbed during saving. |
| **Reserve Fund** | ✅ | ✅ | 🔘 (Toggle) | Real unexpected OpEx, budget needs visibility, but user must have a toggle to opt out if catastrophic. |
| **Fund Project** | ✅ | ✅ | ❌ | Isolated by design, money was graduated. |

- **Remove Auto-Reimbursements**: Rip out `_settle_goal_funding_to_payment_wallets` and any ghost transaction generation logic.
- **Fix Budget Enforcement**: Fix the dead `enforce_monthly_budget_limits` flag in `post_expense_event` so it actually works.
- **Planned Purchase Flow**: When using `ACHIEVED_OUTSIDE_RESERVED_FUNDS`, release the goal funds and pass `enforce_monthly_budget_limits=False` to the expense posting service.
- **Reserve Fund Flow**: Build an "already paid" UI flow for Reserve Fund goals. Release the matching amount from the goal-funded wallet(s) and provide the user with a UI toggle for `enforce_monthly_budget_limits` (default to True for visibility, but allow opt-out).
- **Fund Project Flow**: Build an "already paid" UI flow for Fund Project goals. Release the equivalent funds from the project stash and ensure the expense does not hit the monthly budget.

## Testing Decisions

- Test the `post_expense_event` logic to guarantee that `enforce_monthly_budget_limits=False` truly bypasses `CategoryBudget` and `MonthlyBudget` aggregates.
- Assert that for all three workaround flows, 0 wallet-to-wallet transfer ledger entries are generated.
- Verify that the goal funds are properly unreserved/released in the backend for each flow.

## Out of Scope

- Retroactively cleaning up old auto-transfers from the database for existing users.
- Generating reporting lines differently—all expenses will still appear in spending reports regardless of whether they hit the budget or not.

## Further Notes

Budget pressure is about "Am I overspending my monthly lifestyle allowance?", while the Spending report is about "Where did my money go this month?". Bypassing the budget for Planned Purchases and Isolated Projects keeps the budget pressure accurate without hiding the actual spending from reports. The Reserve toggle ensures users maintain control over catastrophic events.
