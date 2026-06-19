# Epic 6: Isolated Projects & YNAB Envelopes

**Status:** Not Started  
**Depends On:** Epic 5 (Overlay Projects) & Epic 3 (Taxonomy)

## Goal
Introduce **Isolated Projects**, a fundamentally different beast from Overlay Projects. While Overlays draw from monthly category limits, Isolated Projects require upfront wallet locks ("quarantine") to fully fund a massive project on day one. This system acts as a perfect zero-based "mini-YNAB" engine within Sarflog, decoupling liquidity from intent via the Pooled Vault architecture.

## PRDs Included

1. [ ] **Unified Project Creation Router (UI)**
   - *Routing:* Intercept the main "Create Project" button to display a 2-card splash screen asking the user to choose between "Track an Event (Overlay)" and "Fund a Massive Goal (Isolated)". This acts as the funnel into G27 or G28.
2. [ ] **[G28 - Isolated Project Wizard](../prd/g28-isolated-project-wizard.md)**
   - *Creation & Architecture:* Build the 4-step wizard (Identity -> Wallet Quarantine -> Internal Categories -> Micro Subcategories) that locks wallet funds into a Derived Total Stash, completely bypassing standard monthly budget limits.
3. [ ] **[G23 - Project Completion & Wrap-Up](../prd/g23-project-completion-and-wrap-up.md)**
   - *Lifecycle:* Implement the workflow to cleanly close out an isolated project when its dates have passed, sweeping any unused locked funds back to Free Money.

## Relevant Edge Cases
The internals of Isolated Projects are complex. The following edge cases, logged on June 18th, must be strictly observed to prevent architectural corruption:

- **EC-164: The Pooled Vault (Decoupling Liquidity from Intent)**
  - Wallets fund the total stash. Categories draw from the total stash. Wallets are never mapped directly to categories.
- **EC-165: Project Taxonomy Enforcement via G21 Hub**
  - Project subcategories (e.g., "Wedding DJ") must use the global Taxonomy Hub to prevent string tag fragmentation.
- **EC-166: Cascading Top-Ups & Wallet Hierarchy**
  - Injecting free money mid-project must cascade sequentially: Wallet -> Project Stash -> Parent Category -> Subcategory.
- **EC-167: Target End Dates as Sweep Triggers**
  - Isolated projects don't slice by month. The End Date is an alarm clock to trigger sweeping leftover funds back to Free Money.
- **EC-168: The Emergent Mini-YNAB Behavior**
  - If built correctly, a user can lock their whole paycheck into a "May 2026 Budget" isolated project, proving the structural integrity of the zero-based envelope engine.
- **EC-169: Derived Total Stash vs Abstract Target**
  - The UI must NOT ask for a "Target Amount". The stash is purely derived from whatever the user allocates in the wallet rows.
- **EC-170: The "Ghost Goal" Anti-Pattern for Direct Projects**
  - The backend must not create fake goals to lock wallets. It must use a dedicated `ProjectWalletAllocation` table.
- **EC-171: The Premature Graduation Double-Funding Trap**
  - When a Goal graduates into a Project, the Goal is frozen. Future top-ups must happen inside the Project, not the Goal.

## Execution Rules
- The database schema updates (`ProjectWalletAllocation`) from EC-170 and EC-171 must be built first.
- G28 execution will heavily rely on the UI patterns established in the Goal Funding wizard for Wallet locks.
