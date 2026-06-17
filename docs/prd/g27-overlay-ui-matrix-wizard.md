# PRD: G27 - Overlay UI Matrix & Creation Wizard

Labels: `ready-for-agent`

## Problem Statement

Displaying the complexity of multiple overlapping month-scoped Overlay projects on the main Budgets dashboard creates a visual "Rainbow Bar of Death" that overwhelms the user. Furthermore, the current "Create Project" UI is architecturally incompatible with Month-Scoped Slicing (G24). Initially, forcing users to predict and budget for future unbaked months creates a "Pandora's Box" that violates the G9 Realism Check and tricks users into budgeting money they don't currently have.

## Solution

Build a **Two-Tier Matrix UI** and a **Just-In-Time (JIT) Project Allocation flow**. 
1. The main Budgets dashboard abstracts complexity away, showing only "Total Reserved" math. The Budget Details page lists overlapping projects as individual mini-bars. 
2. The Project Creation Wizard only asks for current-month allocations, preventing future-month fantasy budgeting.
3. When new months arrive, the standard EC-155 Month Setup Wizard detects active cross-month projects and prompts the user to slice their newly minted limits into the project dynamically.

## User Stories

1. As a budget user, I want the main Budgets dashboard to only show macro math (Total Limit, Total Reserved, Free Limit), so my workspace stays clean.
2. As a budget user, I want the Budget Details page to list all overlapping projects as individual mini-bars, so I can see micro complexity only when needed.
3. As a budget user, I want the project creation wizard to only ask for current-month allocations, so I don't have to invent fake money for future unbudgeted months.
4. As a budget user, I want the wizard to prompt me to optionally add subcategories in the final step, so I can plan micro-tracking natively.
5. As a budget user, I want the system to prompt me to add new project slices when I set up my budget for a new month, so my cross-month projects grow dynamically over time using real cash flow.

## Implementation Decisions

- **Frontend `Budgets.jsx`:** Update Budget Cards. Do not stack progress bars. Add a textual `Project Reservations` deduction line, yielding `Free Limit`. The progress bar stays green/red based solely on `Total Spent` vs `Total Parent Limit`.
- **Frontend `BudgetDetails.jsx`:** Add an "Active Project Reservations" section. Render a list of `ProjectMiniBar` components for any project that has a reservation in the current month.
- **Frontend `CreateProjectWizard.jsx`:**
  - **Step 1:** Identity & Time (Title, Dates).
  - **Step 2:** Macro Slices (Checkboxes for Parent Categories).
  - **Step 3:** Current Month Allocation (Dynamically renders input fields ONLY for the current active month, fetching global budget headroom to validate inputs live).
  - **Step 4:** Micro Structure (Optional subcategories. Prompts global creation if missing).
- **Frontend `MonthSetupWizard.jsx` (EC-155 Integration):**
  - Upon completion of a new month's setup, check for active cross-month projects. If found, trigger a `Project Allocation Prompt` allowing the user to slice the newly minted month's budget into their active project.
- **Frontend Project Card:** Update the project card to display aggregated "Total Reserved Scope" instead of a flat input limit.

## Testing Decisions

- UI component testing for `CreateProjectWizard`: Verify the grid *only* renders inputs for the current active month, ignoring future months spanned by the project dates.
- UI component testing for `MonthSetupWizard`: Verify the `Project Allocation Prompt` successfully fires if an active project exists and spans into the newly setup month.
- Test the validation hook to ensure inputs exceeding current global headroom trigger a red warning state.
- Test `BudgetDetails` to ensure multiple projects correctly list themselves without mutating the parent progress bar.

## Out of Scope

- Backend schema changes (covered in G24, G25).
- Isolated project wizard paths (Isolated projects skip the monthly grid and use a simple stash limit).

## Further Notes

This dual-axis design perfectly matches the mental model: "Which projects are eating my Transport money?" (Budget UI) versus "What categories of money does this trip need?" (Project UI). The wizard ensures the database receives perfectly structured `ProjectCategoryMonthlyLimit` rows.
