# PRD: G23 - Project Completion Wrap-Up and Typology

Labels: `ready-for-agent`

## Problem Statement

1. **The Receipt Lag:** In real life, project expenses (hotel incidentals, contractor invoices) often trickle in days after the official end date. If the system silently auto-completes projects exactly on the `target_end_date`, users are locked out and forced into a high-friction loop (Reopen -> Guess new date -> Log expense -> Re-complete).
2. **Lack of Closure:** Completing a major financial project (like a wedding or renovation) is stressful. Currently, completing a project is an anticlimactic database state-change with no psychological closure or performance feedback.
3. **Trapped Liquidity:** When an Isolated project finishes under budget, the remaining reserved funds sit trapped in limbo unless the user manually hunts down the origin goal to release them.
4. **Typology Blurring:** Overlay (Constraint-based) and Isolated (Fund Accounting) projects currently share confusing terminology and mechanics. Overlay projects risk breaking the global taxonomy (G21) if allowed to have custom subcategories, and Isolated projects confusingly use the term "Limit" instead of "Funding."

## Solution

1. **Prompted Wrap-Up (Agency > Automation):** The system treats `target_end_date` as an inclusive boundary (spending allowed *through* 11:59 PM on that day). When the date passes, the system does not auto-lock the project. Instead, it surfaces a "Ready to Wrap Up?" prompt, allowing a grace period for lagging receipts.
2. **The "Project Wrapped" Report:** Clicking "Wrap Up" triggers a beautiful summary modal before locking the project. It shows Hero Metrics (Planned vs Actual), Top Spending Heavy Hitters, and a Velocity sparkline.
3. **The Sweep Action:** The final step of the Wrap-Up modal for Isolated projects prompts the user to sweep any remaining funding back to `Ready to Assign` or `Emergency Fund`.
4. **Strict Typology Enforcement:** 
   - **Overlay Projects:** UI uses "Limit". Progress ticks UP. No custom subcategories allowed; they inherit and report on global `UserSubcategory` tags to preserve G21 taxonomy.
   - **Isolated Projects:** UI uses "Funding" or "Allocation". Progress ticks DOWN. Allowed to have custom `ProjectSubcategory` tags for siloed tracking (e.g., "Drywall").

## User Stories

1. As a user, I want the system to treat my project's target end date as an inclusive boundary, so that I can log expenses incurred on the final day without being blocked.
2. As a user, I want the system to prompt me to wrap up a project when the target date passes rather than locking it silently, so that I have a grace period to log lagging receipts (The Receipt Lag).
3. As a user, I want to see a "Project Wrapped" summary when I finalize a project, so that I gain psychological closure and understand my financial performance (e.g., "$200 under budget!").
4. As a user, I want to be prompted to sweep unused money from an Isolated project during wrap-up, so that my liquidity is immediately returned to my main budget.
5. As a user, I want Overlay projects to use terms like "Limit" and show progress filling up, so that it matches my mental model of a constraint.
6. As a user, I want Isolated projects to use terms like "Funding" and show progress ticking down, so that it matches my mental model of draining a dedicated pile of cash.
7. As a user, I want my Overlay projects to automatically group my spending by my global subcategories (from G21), so that my global taxonomy stays clean and I don't have to recreate tags.

## Implementation Decisions

- **Wrap-Up Status:** The backend does not need a new `status` enum. The "Ready to Wrap Up" state is a derived frontend UI state (`today() > target_end_date` AND `status == ACTIVE`).
- **Analytics Payload:** Add a new endpoint `GET /projects/{project_id}/wrap-up-summary` that calculates the "Spotify Wrapped" metrics (Hero metric, Top Expense, burn-down data points).
- **Sweep Integration:** The `POST /projects/{project_id}/complete` payload will be expanded to accept an optional `sweep_destination` enum/ID for Isolated projects, which triggers a funding release ledger entry before marking `COMPLETED`.
- **Subcategory Enforcement:** Ensure `validate_project_subcategory_rules` strictly prevents `ProjectSubcategory` creation for Overlay projects. Frontend UI for Overlay projects should render global subcategory reporting instead of a custom subcategory setup tab.

## Testing Decisions

- **Seams for Testing:** 
  - Service-level tests for the analytics generation logic (`get_project_wrap_up_summary`).
  - API integration tests for the `/complete` flow ensuring the `sweep_destination` properly generates the un-reservation ledger entries.
  - Unit tests verifying that inclusive date boundaries (`<= target_end_date`) allow expense posting at exactly 11:59 PM on the target date.
- Good tests will focus on the ledger math being perfectly balanced after a sweep-and-complete action, ensuring no double-counting.

## Out of Scope

- Retroactively generating "Wrapped" reports for already completed projects.
- Animating the "Wrapped" report with complex canvas graphics (keep it to clean CSS/HTML charts and basic CSS micro-animations).

## Further Notes

By prioritizing user agency and providing a delightful wrap-up experience, we transform a rigid database state-change into a rewarding product feature that aligns perfectly with human psychology and real-world receipt lags.
