# Issues: G7 - Projects and Goal Deployment

Parent PRD: `docs/prd/g7-projects-and-goal-deployment.md`

Publish label: `ready-for-agent`

Execution scope for this pass: Issues 1-4 are now implemented.

## Proposed Breakdown

1. **Validate project expense tagging by expense date**
   - Type: AFK
   - Blocked by: None
   - User stories covered: 1-2, 14-15

2. **Protect project date edits from orphaning tagged expenses**
   - Type: AFK
   - Blocked by: Issue 1
   - User stories covered: 3-6, 14-15

3. **Lock completed projects until explicit reopen**
   - Type: AFK
   - Blocked by: Issues 1-2
   - User stories covered: 7-8, 14-15

4. **Graduate Fund Project goals into stash-backed project reporting**
   - Type: HITL
   - Blocked by: Issues 1-3
   - User stories covered: 9-13, 15

## Issue 1: Validate Project Expense Tagging By Expense Date

## What to build

Project expense tagging should validate the expense's own date against the project window. Late entry is allowed when the entered expense date is inside the project, and rejected when the expense date falls outside the project start/end boundaries.

## Acceptance criteria

- [x] An expense entered after a project's end date can still be tagged when its `date` is on or before the project end date.
- [x] An expense dated before the project start is rejected.
- [x] An expense dated after the project end is rejected when `target_end_date` exists.
- [x] Validation uses the shared project expense validation seam used by normal expense posting.

## Blocked by

None - can start immediately.

## Progress

- RED: Added `tests/test_expenses.py::test_project_expense_tagging_uses_expense_date_not_current_date`.
- GREEN: Project expense validation now rejects expenses after `project.target_end_date` using the expense date.
- Verification blocked: Docker test execution could not run because the sandbox cannot access Docker and escalation was rejected by the approval system.

## Issue 2: Protect Project Date Edits From Orphaning Tagged Expenses

## What to build

Project date updates should allow window expansion but block shrinking when any existing tagged expense would fall outside the proposed project dates.

## Acceptance criteria

- [x] Moving the project start date earlier is allowed.
- [x] Moving the project end date later is allowed.
- [x] Moving the project start date after the earliest tagged expense is rejected.
- [x] Moving the project end date before the latest tagged expense is rejected.
- [x] Removing an end date remains allowed because it expands the valid window.

## Blocked by

- Issue 1: Validate project expense tagging by expense date

## Progress

- RED: Added `tests/test_expenses.py::test_project_date_update_allows_expansion_and_blocks_orphaning_tagged_expenses`.
- GREEN: Project update validation now checks the proposed end date against the latest linked expense date.
- Verification blocked: Docker test execution could not run because the sandbox cannot access Docker and escalation was rejected by the approval system.

## Issue 3: Lock Completed Projects Until Explicit Reopen

## What to build

Completed projects should become protected reports. Dates, limits, subcategories, and expense tagging are blocked while completed. The existing reopen action is the only path back to editable `ACTIVE` state.

## Acceptance criteria

- [x] Completed project update attempts are rejected.
- [x] Completed project category-limit and subcategory edits are rejected.
- [x] New expense tagging to a completed project is rejected until reopen.
- [x] Reopen transitions the project back to editable active state.
- [x] Re-completing after edits preserves the latest valid report window.

## Blocked by

- Issue 1: Validate project expense tagging by expense date
- Issue 2: Protect project date edits from orphaning tagged expenses

## Progress

- RED: Added `tests/test_expenses.py::test_completed_project_rejects_edits_and_expense_tagging_until_reopen`.
- GREEN: Added completed/archived project editability validation and wired it through project metadata, category-limit, and subcategory mutation routes.
- Existing shared project expense validation rejects new tagging while the project is completed.
- Docker-backed verification passed for the new Issue 3 test, the G7 narrow slice, and `tests/test_expenses.py`.

## Issue 4: Graduate Fund Project Goals Into Stash-Backed Project Reporting

## What to build

Fund Project goals should graduate before 100 percent completion. The isolated project starts with a released stash equal to the funded amount, not the target amount. Overlay project reporting ticks up toward limits; isolated project reporting ticks down from released stash and exposes shortfalls through existing backing math.

## Acceptance criteria

- [x] A Fund Project goal can graduate when funded amount is less than target amount.
- [x] The graduation response exposes a linked isolated project.
- [x] Initial released project funding equals the funded goal amount selected for release.
- [x] Spending within the released stash reduces remaining funding.
- [x] Spending beyond released funding is not hidden; G3 backing math reflects the free-money pressure.
- [x] Project UI distinguishes overlay tick-up from isolated tick-down reporting.

## Blocked by

- Issue 1: Validate project expense tagging by expense date
- Issue 2: Protect project date edits from orphaning tagged expenses
- Issue 3: Lock completed projects until explicit reopen

## Progress

- RED: Added `tests/test_goals.py::test_fund_project_goal_graduates_early_with_funded_stash_and_reports_shortfall`.
- GREEN: Fund Project graduation now releases currently funded/unreleased money into the isolated project by default.
- Project summaries now expose `progress_direction` and `funding_shortfall`; isolated goal-funded projects can report negative remaining funding instead of blocking the real spend.
- Existing G3 budget summary math reflects wallet/free-money pressure after isolated project spending.
- Docker-backed verification passed for the new Issue 4 test, the G7 narrow slice, and `tests/test_goals.py`.
