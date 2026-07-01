# ADR 0006: Strict Limit Balancing & The Cancellation of Permissive UX

## Status
Accepted

## Context
During the design of the Month Setup Wizard, we initially proposed a "Permissive UX" model. This model would allow users to save a monthly budget plan even if it exceeded their available funds ("Overplanned" state), relying entirely on passive warnings to prompt them to fix it later. 

However, allowing users to budget money they do not actually possess fundamentally breaks zero-based budgeting principles and erodes user trust in the system's mathematics.

## Decision

We are explicitly canceling the "Permissive UX" model and instituting **Strict Limit Balancing** for all Month Setup modes (Plan from Scratch, Copy Last Month, Smart Auto-Fill).

1. **The Intercept Rule:** If a user attempts to finalize a budget setup that exceeds their current available "Plan Backing", the system MUST block the save and display an intercept screen.
2. **Mandatory Resolution:** The user is required to manually trim their category limits (or log expected inflows) until the budget is mathematically balanced (Overplanned <= 0) before they can proceed.
3. **Forward-Looking Only:** Budgeting must only account for money currently in the wallet at the exact moment of setup, regardless of what day of the month it is. Past behavior and external mental accounting are ignored to preserve ledger truth.

## Consequences

- **Increased Trust:** Users will never be implicitly guided to overdraft their accounts. A successfully saved budget mathematically guarantees that the user has the funds to back it.
- **Friction as a Feature:** "Copy Last Month" is no longer a blind, single-click action if the user's income has dropped. The friction forces active, healthy financial decision-making.
- **UI Requirements:** The frontend must provide a clear, real-time "Amount Remaining to Balance" indicator during the setup flow so the user knows exactly how much they need to trim.
