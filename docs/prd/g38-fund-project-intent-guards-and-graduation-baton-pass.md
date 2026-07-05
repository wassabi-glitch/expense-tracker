# PRD: G38 - Fund Project Intent Guards and Graduation Baton Pass

Labels: `ready-for-agent`

## Problem Statement

Sarflog has accepted ADR008's rule that goal lifecycle states are intent-specific, but the most important high-risk slice is still only partially enforced in product behavior: `FUND_PROJECT` goals are supposed to behave like project incubators, not like ordinary purchase or debt goals.

Without a dedicated implementation slice, a Fund Project goal can drift into ambiguous states. It may expose the wrong action language, allow invalid completion semantics, or stay partially active after graduation in a way that creates two parallel funding paths: keep contributing to the old goal and also top up the new project. That ambiguity is exactly the kind of domain leak that makes protected-money systems hard to trust.

Epic 6 Issue 6 already covers the isolated-project funding handoff. What is still needed is a focused PRD that applies the `FUND_PROJECT` part of ADR008 and ADR007 end to end, so the graduation path is protected by the right lifecycle guards rather than just implemented as a happy-path transfer.

## Solution

Implement the `FUND_PROJECT` subset of ADR008 as a focused lifecycle slice that supports Epic 6 Issue 6.

The user-facing behavior should be:

- A Fund Project goal remains an active saving incubator until the user explicitly graduates it or archives it.
- A passed target date never completes or invalidates the goal. It may only inform UI warning copy.
- A Fund Project goal cannot be completed like a planned purchase or debt payoff goal.
- Graduation is the one-way baton pass from goal saving phase to isolated project execution phase.
- Once graduated, the goal becomes read-only as a historical saving record and all future funding increases belong to the project top-up flow.

This slice should not redesign the lifecycle of every goal intent. It should make the Fund Project path correct now, while staying compatible with future full ADR008 rollout for the other intents.

## User Stories

1. As a goal user, I want a Fund Project goal to stay active until I deliberately graduate it or archive it, so that the app does not pretend my project started just because I reached a number.
2. As a goal user, I want a Fund Project goal to remain usable even after its target date passes, so that real-life project timing does not trap my money.
3. As a goal user, I want a passed target date on a Fund Project goal to show only warning language, so that I am informed without the system mutating my goal behind my back.
4. As a goal user, I want Fund Project goals to reject completion behavior, so that the app does not confuse project incubation with purchase fulfillment.
5. As a goal user, I want the primary close action for a Fund Project goal to be graduation rather than completion, so that the UI matches the domain.
6. As a goal user, I want to graduate a Fund Project goal before it reaches 100 percent, so that I can start the real project when life requires it.
7. As a goal user, I want the graduated project to begin with only the real funded amount, so that my project stash stays honest.
8. As a goal user, I want the original Fund Project goal to become read-only after graduation, so that I do not accidentally keep funding the wrong container.
9. As a goal user, I want future money additions after graduation to route into project top-up, so that I have one clear place to continue funding.
10. As a goal user, I want the relationship between the graduated goal and the active project to be obvious, so that I can understand what happened to my protected money.
11. As a goal user, I want goal detail and project detail to explain the baton pass in plain language, so that the history feels coherent.
12. As a goal user, I want invalid actions on a graduated Fund Project goal to fail with stable messages, so that I know the project is now the live funding surface.
13. As a goal user, I want archived Fund Project goals to stay archived and non-operational, so that history remains trustworthy.
14. As a goal user, I want non-Fund goals to be blocked from the graduation route, so that the project system cannot be entered through the wrong intent.
15. As a project user, I want a graduated Fund Project to behave like any other isolated project for top-ups and internal allocation, so that the execution phase is consistent.
16. As a budget user, I want time-derived goal warnings to stay derived rather than stored, so that goal state does not depend on background jobs.
17. As a developer, I want one durable goal status enum with intent-specific lifecycle guards, so that the schema stays stable while domain rules remain strict.
18. As a developer, I want graduation, allocation, return, consume, and update routes all to respect the Fund Project matrix, so that no write seam can bypass the intent rules.
19. As a tester, I want public API tests for invalid Fund Project completion and post-graduation read-only behavior, so that the lifecycle contract is verified externally.
20. As a product owner, I want this narrow slice separated from the full all-intents ADR008 rollout, so that Epic 6 Issue 6 can proceed without reopening every goal flow at once.

## Implementation Decisions

- Keep the existing global `GoalStatus` enum as the durable database lifecycle storage for goals.
- Keep time-derived warning states out of database status storage. Fund Project deadlines may influence UI warning copy, but not stored lifecycle state.
- Treat `FUND_PROJECT` as having only three valid persisted lifecycle states: `ACTIVE`, `GRADUATED`, and `ARCHIVED`.
- Treat `COMPLETED` as invalid for `FUND_PROJECT` across all write seams, not just a generic status update endpoint.
- Preserve ADR007's one-way separation between goal incubation and project execution: graduation is the baton pass into the isolated project model.
- Require the graduation route to reject non-`FUND_PROJECT` intents.
- Require the graduation route to create or continue only the isolated-project path for Fund Project goals.
- Require successful graduation to move the origin goal into a terminal graduated state before commit completes.
- Treat a graduated Fund Project goal as read-only for contribution allocation, return, consume, funding edits, and other saving-phase mutations.
- Route all future post-graduation funding increases through the isolated project top-up contract introduced for active isolated projects.
- Expose explicit relationship data in goal and project read models so clients can render "this goal became this project" without inferring from nullable fields.
- Use UI copy that distinguishes saving-phase goal language from execution-phase project language.
- Do not expand this PRD into Reserve, Planned Purchase, or Pay Obligation lifecycle redesign. Those remain future ADR008 rollout work.
- Treat target-date behavior for this slice as optional and non-blocking: target dates may support warnings or nudges, but they must not block graduation or auto-close the goal.
- Keep the feature compatible with Epic 6 Issue 6's wallet-backed funding handoff into isolated project wallet-allocation truth.

## Testing Decisions

- Good tests should verify externally visible behavior at the highest seam available: goal routes, project routes, and list/detail responses.
- Add API tests proving a `FUND_PROJECT` goal cannot be completed through any public completion-capable path available to goals.
- Add API tests proving non-Fund goals cannot use the graduation route.
- Add API tests proving a Fund Project goal remains `ACTIVE` after passing its target date and can still graduate successfully.
- Add API tests proving successful graduation flips the goal to `GRADUATED` and blocks later allocation, return, consume, and edit attempts.
- Add API tests proving list/detail responses expose the linked goal/project relationship after graduation.
- Add API tests proving project top-up remains the live funding path after graduation.
- Add API tests proving no background or read-path logic mutates stored goal status based on date passage alone.
- Add frontend tests for Fund Project action copy, visible graduation action, read-only graduated state, and project-routing language after graduation.
- Prior art includes existing goal graduation tests, goal funding mutation tests, and isolated project top-up tests already present in the codebase.
- Docker-backed backend tests and frontend build remain the verification source for the completed slice.

## Out of Scope

- Full ADR008 rollout for `RESERVE`, `PLANNED_PURCHASE`, and `PAY_OBLIGATION`.
- Debt-engine redesign for obligation goals.
- Planned purchase completion redesign.
- Reserve goal UX redesign.
- New database lifecycle enums beyond the existing goal status enum.
- A generalized goal state machine framework for all intents.
- Broader project reporting work outside the Fund Project graduation path.

## Further Notes

This PRD is intentionally narrow.

The point is not to finish every implication of ADR008 in one pass. The point is to make Epic 6 Issue 6 safe by ensuring the Fund Project lifecycle truth matches the project-funding handoff truth:

- Fund Project goal = saving incubator
- Graduated isolated project = execution stash
- Project top-up = future funding path

That baton pass is the part most likely to create double-funding confusion if the lifecycle rules remain soft.
