# PRD: G7 - Projects and Goal Deployment

Labels: `ready-for-agent`

## Problem Statement

Sarflog can now protect wallet reality, monthly budget backing math, expected inflows, month-scoped subcategory limits, and recurring/category floors. The remaining project weakness is lifecycle trust.

Users need projects to behave like real reporting windows and real deployments of goal money. A late-entered receipt should be taggable when the receipt's expense date belongs to the project. A completed project should not be silently edited after its final report. A Fund Project goal should be deployable when life starts the project before the goal reaches 100 percent.

## Solution

Harden project and goal deployment rules around explicit dates and lifecycle state. Project tagging validates the expense's date against the project's start and end dates. Project date edits allow expansion but block shrinking that would strand existing tagged expenses. Completed projects become protected reports until the user explicitly reopens them.

Fund Project goals can graduate before full funding. The resulting isolated project starts with the funded amount as its released stash, and any shortfall is handled by existing G3 backing math as normal free-money pressure. Project reporting distinguishes overlay projects that tick up against a limit from isolated projects that tick down against a stash.

## User Stories

1. As a project user, I want to tag a late-entered receipt when the receipt date belongs inside the project window, so that reporting matches real life instead of entry timing.
2. As a project user, I want expenses outside the project window to be rejected, so that project reports do not include unrelated spending.
3. As a project user, I want project start dates to move backward freely, so that I can account for work that started earlier than I first planned.
4. As a project user, I want project end dates to move forward freely, so that delays do not force me to create a fake second project.
5. As a project user, I want start-date shrinking to be blocked when existing tagged expenses would fall before the new start date, so that no expense is orphaned by metadata edits.
6. As a project user, I want end-date shrinking to be blocked when existing tagged expenses would fall after the new end date, so that no expense is orphaned by metadata edits.
7. As a project user, I want completed projects to be read-only, so that final reports stay trustworthy.
8. As a project user, I want an explicit Reopen Project action, so that edits to completed history are intentional.
9. As a goal user, I want to graduate a Fund Project goal before it reaches 100 percent, so that real-life deadlines do not trap protected money.
10. As a goal user, I want the initial project stash to equal the funded amount released from the goal, so that the project starts with real protected money.
11. As a budget user, I want unfunded isolated-project overspending to reduce free money through existing backing math, so that shortfalls are honest.
12. As a project user, I want overlay project visuals to tick up toward a limit, so that analytical tracking is easy to scan.
13. As a project user, I want isolated project visuals to tick down from the released stash, so that protected project money feels like a spendable balance.
14. As a maintainer, I want project-date rules centralized behind existing expense/project validation seams, so that quick expenses, session expenses, and goal-funded expenses share the same invariants.
15. As a tester, I want API-level tests for project date and graduation rules, so that behavior is verified through public interfaces.

## Implementation Decisions

- Preserve wallet reality over plan metadata.
- Keep G3 backing math as the source of truth for over-planned status and project shortfalls.
- Keep goals as protected real money until explicitly released, consumed, returned, or graduated into a project.
- Validate project tagging by `expense_date`, never by server date or request time.
- Enforce `project.start_date <= expense_date <= project.target_end_date` when `target_end_date` exists.
- Allow project date expansion without extra friction.
- Block date shrinking when existing tagged expenses would fall outside the proposed window.
- Treat completed projects as protected reports. Edits and new expense tagging require explicit reopen.
- Do not require a Fund Project goal to be fully funded before graduation.
- Use released goal funding, not goal target amount, as the isolated project stash.
- Overlay projects are analytical trackers and should visually tick up.
- Isolated projects are stash deployments and should visually tick down.

## Testing Decisions

- Prefer public API tests through expense creation, project updates, project lifecycle routes, and goal graduation routes.
- The first tracer bullet verifies expense creation with a project link uses the expense's own date.
- The second tracer bullet verifies date expansion and date shrink blocking through project update endpoints.
- Goal/project graduation tests should live near existing goal tests and assert released funding, linked project state, and no full-funding prerequisite.
- Frontend project display work should be verified by production build and, where browser tooling is available, a project dashboard smoke test.
- Docker-backed backend tests are the verification source because the app runs backend, API, Redis, DB, and frontend through Docker.

## Out of Scope

- Reworking the project data model beyond the current date/lifecycle fields.
- Replacing G3 backing math.
- Detailed final-report rendering beyond protecting completed project history.
- New forecasting claims about goal delays or opportunity cost.
- Full mobile-specific project UI behavior.

## Further Notes

This PRD implements G7 from `docs/EC_IMPLEMENTATION_PLAN.md` and is grounded in EC-112, EC-113, EC-114, EC-117, EC-118, and EC-127.

No external issue tracker tool is available in this environment, so the PRD is published locally under `docs/prd/` with the `ready-for-agent` label.
