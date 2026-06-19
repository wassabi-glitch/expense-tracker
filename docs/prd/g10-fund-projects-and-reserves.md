# G10: Fund Projects and Reserve Expenses

## Problem Statement

Users lack proper control and UI explainability for two key goal-related flows: Reserve Fund consumption and Fund Project graduation. 
1. When a user consumes money from a Reserve Fund (like an emergency fund), the expense currently hits the monthly budget automatically (or bypasses it silently), providing no agency to the user. Some reserve expenses are standard-sized and should impact the budget, while others are catastrophic and should bypass it.
2. The "Fund Project" goal type (`GoalIntent.FUND_PROJECT`) is completely absent from the goal creation UI, making it impossible for users to intentionally save up for a project.
3. Even if a `FUND_PROJECT` goal existed, the graduation flow is broken. The UI lacks the "Graduate" button to convert the goal into an isolated project.
4. The backend API (`/{goal_id}/graduate`) allows any goal type to graduate (e.g., Reserve or Planned Purchase), which is dangerous and conceptually flawed. It also fails to set the graduated goal's status to `GRADUATED`, leaving it active and prone to double-spending or confusion.
10. In the UI, goal-funded isolated projects render with filling progress bars (ticking up) instead of depleting progress bars (ticking down).
11. The backend currently allows expenses to be tagged to a project regardless of the expense's date, violating the core G7 time-boxing rule (`project.start_date <= expense_date <= project.target_end_date`).
12. Completed projects lack a "Reopen" action in the UI, leaving users permanently locked out of editing if they accidentally mark a project as complete.

## Solution

The system will provide explicit user control over Reserve Fund expense impacts and complete the missing Fund Project graduation lifecycle. 
- During a "Use Reserve" transaction, the user will explicitly toggle whether the expense should count against the monthly category budget.
- The UI will present "Project fund" as a primary choice during goal creation.
- A "Graduate to Project" action will be introduced for fully-funded `FUND_PROJECT` goals, which will invoke the graduation API and properly transition the goal into an isolated project.
- The backend API will be fortified to reject non-`FUND_PROJECT` graduation attempts and correctly update the goal's status to `GRADUATED`.
- Finally, the project UI will be corrected to ensure goal-funded isolated projects display a depleting progress bar, visually reinforcing that the user is spending down a pre-allocated stash.
- Enforce strict expense date validation against project date windows in the backend (`validate_session_item_links`).
- Add a "Reopen Project" action in the frontend UI for completed projects, allowing users to safely unlock historical records.
## User Stories

1. As a user, I want to explicitly choose whether a reserve fund expense counts against my monthly budget, so that I can keep my budget accurate whether the expense is a minor bump or a major catastrophe.
2. As a user, I want to see a "Project fund" option when creating a goal, so that I can save up money for a multi-expense mission (like a vacation or home renovation).
3. As a user, I want to click a "Graduate to Project" button on my completed project fund goal, so that I can officially convert my saved money into an isolated project.
4. As a system administrator, I want the backend to reject graduation attempts for Reserve or Planned Purchase goals, so that the ledger and goal states remain logically sound and conceptually pure.
5. As a system administrator, I want graduated goals to automatically change their status to `GRADUATED`, so that they are effectively locked and users cannot continue allocating money to a goal that has already spawned a project.
6. As a user, I want the progress bar on my goal-funded isolated project to start at 100% and tick down as I spend, so that I can visually see my remaining stash depleting.
7. As a user, I want the system to cleanly differentiate between direct isolated projects (which tick up against a cap) and goal-funded isolated projects (which tick down from a stash), so that the UI accurately reflects my financial reality.
8. As a project user, I want the backend to reject expenses that fall outside my project's date window, so my project reports remain historically accurate.
9. As a project user, I want a "Reopen" button on completed projects, so I can fix mistakes or add late receipts after finalizing a project.
## Implementation Decisions

- **Reserve Impact Toggle**: Add a boolean toggle to the "Use Reserve" form state (`useForm` in `Savings.jsx`) that asks "Count against monthly category budget?". 
- **Expense Posting Service**: Pass the reserve impact toggle value from the UI to the backend expense posting service. Update `post_expense_event` to respect the `enforce_monthly_budget_limits` parameter, which is currently dead code.
- **Goal Creation UI**: Update `GOAL_CREATE_CHOICES` in `Savings.jsx` to include a 4th choice mapping to `intent: "FUND_PROJECT"`. Ensure the wizard supports standard target amount and date inputs for this intent.
- **Graduation UI Hooking**: Import `useGraduateGoalMutation` into `Savings.jsx`. Render a "Graduate" action button conditionally for `FUND_PROJECT` goals that have a positive `unreleased_amount` and are not already completed/archived.
- **Backend Graduation Validation**: Modify `graduate_goal_to_project` in `app/routers/goals.py`. Add a check: `if goal.intent != models.GoalIntent.FUND_PROJECT: raise HTTPException(...)`.
- **The "Baton Pass" Graduation Architecture**: When a `FUND_PROJECT` goal graduates, the backend executes an atomic handoff. 
  1. Set `goal.status = models.GoalStatus.GRADUATED`.
  2. Create `GoalProjectRelease` rows to officially unlock the goal's claim on the wallets.
  3. Create `ProjectWalletAllocation` rows mapped to the new Isolated Project to re-lock the exact same funds into the project envelope.
  This ensures the Wallet's `Protected Balance` remains perfectly balanced, and the Project becomes entirely decoupled from the Goal, allowing the Goal to be frozen permanently.
- **Progress Bar Math**: In `Budgets.jsx`, identify `isGoalFundedIsolated`. For these projects, reverse the progress bar calculation (e.g., `(remainingFunding / releasedFunding) * 100`) and style it to reflect a depleting balance rather than a filling limit.
- **Backend Expense Date Validation**: Modify `validate_session_item_links` to accept `expense_date: date`. Add logic to enforce `expense_date >= project.start_date` and `expense_date <= project.target_end_date` (if the latter exists). Update all call sites in `expense_posting_service.py` and `session_draft_service.py` to pass the expense date.
- **Reopen Project UI**: In `Savings.jsx` (or the relevant project detail component), conditionally render a "Reopen" button for projects with `status == COMPLETED`. Wire this to a backend `PUT /projects/{id}/reopen` or `status` update endpoint.
## Testing Decisions

- Test the "Use Reserve" flow via unit/integration tests to ensure that toggling the budget impact flag correctly bypasses or hits the `CategoryBudget` and `MonthlyBudget` aggregates.
- Test the backend `/{goal_id}/graduate` endpoint:
  - Attempt to graduate a `RESERVE` goal (expect 400).
  - Attempt to graduate a `PLANNED_PURCHASE` goal (expect 400).
  - Successfully graduate a `FUND_PROJECT` goal and assert that `goal.status == "GRADUATED"`.
- UI Testing (Manual or Cypress): Verify the progress bar for goal-funded isolated projects ticks down. Verify direct isolated projects (no origin goal) still tick up.
- Test the backend expense posting validation to ensure out-of-bounds expense dates are rejected with a 400 when tagged to a project.
## Out of Scope

- Modifying the underlying Project ledger mathematics.
- Modifying how direct (non-goal-funded) isolated projects operate or render (they will continue to tick up against their limit).
- Changing the reimbursement strategy or auto-transfers for goal funding, which has already been explicitly rejected in favor of the "Prepare Payment" paradigm.

## Further Notes

These changes resolve architectural gaps discovered during the multi-currency deep dive and the evaluation of edge cases EC-146 through EC-150.
