# PRD: G28 - Isolated Project Wizard and Mini-YNAB Mechanics

Labels: `ready-for-agent`

## Problem Statement

While Overlay projects act as month-scoped limit envelopes, Isolated Projects are physical cash vaults designed to protect massive, high-variance life events (Weddings, Renovations, PC Builds) from destroying the user's monthly budgeting habits. Currently, the creation flow for Isolated Projects lacks the physical "Quarantine" mechanics needed to explicitly lock funds at the wallet level. It also lacks internal categorical structuring, preventing accurate global analytics at the end of the year, and suffers from an unclear relationship between liquidity (wallets) and intent (categories).

## Solution

Implement a 3-Step Creation Wizard for Direct Isolated Projects that forces users to physically quarantine cash from specific wallets and distribute that stash into internal categorical sub-stashes, acting as a "Pooled Vault". This establishes a strict, zero-based "Mini-YNAB" micro-economy for the project.

## User Stories

1. As a project user, I want to create an Isolated Project directly on the Budgets page so that I can quarantine existing Free Money for a massive life event.
2. As a project user, I want the Total Project Stash amount to be dynamically derived from my wallet allocations rather than typed into an abstract input field, so that I cannot create a mathematical mismatch between my intent and my physical cash.
3. As a project user, I want the system to force me to allocate project funds from specific wallets during creation so that I physically lock my cash and avoid double-spending.
3. As a project user, I want the system to warn me or block me if my allocation exceeds my global Free Money Now, so that I don't accidentally force my monthly budget into an Over-Planned state.
4. As a project user, I want to break my total project stash down into Global Parent Categories (e.g., Food, Entertainment), so that my project spending perfectly rolls up into my end-of-year global analytics.
5. As a project user, I want to optionally create hyper-granular Subcategories using the Global Taxonomy Hub (G21 Combobox), so that my one-off tags (e.g., "Drywall") remain organized and can be archived later without polluting my daily budget dropdowns.
6. As a project user, I want to pay for a project expense from any linked project wallet without worrying about which wallet is tied to which category, so that I have total flexibility at the checkout counter (The Pooled Vault).
7. As a project user, I want the system to prevent me from overspending an internal project subcategory by forcing me to either rebalance internally or top-up externally, so that I maintain strict zero-based control.
8. As a project user, I want to execute a "Cascading Top-Up" when I add Free Money to a subcategory, so that the money mathematically flows through a specific wallet, the total project stash, the parent category, and into the subcategory simultaneously.
9. As a project user, I want to set a Target End Date for my isolated project so that the system can prompt me to sweep any leftover funds back into my Free Money once the date passes.

## Implementation Decisions

- **Step 1: The Identity**: The wizard begins by asking for Title, Target End Date, and Note. The Target End Date acts purely as a sweep trigger alarm clock, not a monthly slicing mechanism.
- **Step 2: The Quarantine (Wallet Allocation)**: The UI renders a Wallet Allocation list (identical to Goal Funding). It explicitly displays `Total Balance`, `Protected for Goals`, and `Free to Allocate` for each positive wallet. Crucially, the Total Project Stash is a purely *derived* sum of these allocations. There is no abstract "Target Amount" input field, preventing state-matching validation errors.
- **Step 3: The Internal Sub-Stashes (Taxonomy)**: The user allocates the total stash into Global Categories.
- **Step 4: Micro Structure**: The user uses the G21 Combobox to create or link Global Subcategories.
- **The Pooled Vault Architecture**: Wallets are NOT directly mapped to Categories. Wallets fund the total stash. Categories draw from the total stash.
- **The Cascading Top-Up**: When injecting new Free Money directly into a project subcategory, the system must prompt the user to select the funding wallet, and then execute the ledger updates sequentially: Wallet -> Project Stash -> Parent Category -> Subcategory.
- **Over-Planned Enforcement**: If a project expense forces the project stash below 0, the system must absorb the shock by draining global `Free Money Now`. If this drops below 0, the monthly plan state becomes `Over-Planned`.
- **Single Table Project Architecture**: Overlay and Isolated projects will share a single `projects` table using a `project_type` Enum (`OVERLAY`, `ISOLATED`). The differing mechanics are enforced by their relation tables: Overlay uses month-scoped reservation storage, while Isolated uses isolated project wallet allocation storage for physical cash quarantine.
- **The Isolated Project Wallet Allocation Table**: A database table mapping `project_id`, `wallet_id`, and `amount` acts as the single source of truth for an Isolated Project's total stash (which is mathematically derived as `SUM(amount)`). G36 supersedes the older generic `ProjectWalletAllocation` naming.

## Testing Decisions

- **Seams for Testing**:
  - The API endpoints for project creation: verify that the wallet allocations properly lock funds and deduct from Free Money Now.
  - The "Cascading Top-Up" endpoint: verify that injecting 500k into a subcategory successfully links to a selected wallet and increments all parent scopes appropriately.
  - The Project Expense routing: verify that a 5M expense recorded against a project category correctly checks the pooled wallet reserves, rather than demanding a 1:1 wallet-to-category map.
- Good tests will focus on the zero-based math: validating that moving cash into a project correctly impacts the global Budget Plan status when Free Money is exhausted.

## Out of Scope

- Native handling of recurring expected inflows specifically inside an isolated project (they remain globally managed).
- Linking an isolated project directly to an external bank API without going through the Wallet Ledger first.

## Further Notes

The Isolated Project architecture mathematically functions as a perfect Zero-Based Envelope Budget. While designed for massive, temporary life events, its structural integrity allows users to theoretically simulate the YNAB philosophy for their entire financial life.
