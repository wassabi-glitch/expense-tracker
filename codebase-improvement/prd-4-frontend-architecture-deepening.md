# PRD 4: Frontend Architecture Deepening For Expected Inflows, Projects, Cache, Budget Recovery, And Calendar Safety

Triage: ready-for-agent

## Problem Statement

Sarflog's frontend already has useful feature folders, reusable UI primitives, request timezone headers, and several focused hooks. The remaining pain is not that the frontend is unstructured. The pain is that several important product rules still leak through shallow modules, so each screen has to remember backend payload shapes, cache side effects, user-local calendar rules, and money-flow recovery behavior.

From the user's perspective, this can show up as Expected Inflow source choices being wrong, Refund choices showing the wrong item, Budget-required errors stopping a money movement instead of helping repair the plan, Project actions crowding the Budgets screen, stale dashboard or wallet data after a ledger change, or dates shifting around the user's real calendar.

From the developer's perspective, the risky knowledge is spread across callers. The deletion test is clear: if the local helper or screen code is removed, the complexity reappears in multiple other callers. This PRD turns the five frontend architecture candidates from the review into deeper modules with smaller interfaces, better locality, and higher leverage.

## Solution

Create a frontend architecture deepening program with five coordinated improvements:

1. **Expected Inflow Source Picker Read Model**: Expected Inflow creation and editing should receive normalized source options for Earned income, Receivable Debt repayment, Refund, and Asset Sale. The implementation should absorb backend payload unwrapping, Debt lifecycle status rules, and source-kind filtering.
2. **Project Details Seam**: The Budgets screen should remain the monthly attention surface for Budget permission. Heavy Project execution flows should move behind a dedicated Project details seam, matching ADR-0020's two-layer UX architecture.
3. **Ledger Side-Effect Cache Module**: Money mutations should stop hand-writing scattered query invalidations. A deeper cache module should own canonical query keys and the side effects of ledger-adjacent mutations.
4. **Global Budget Interceptor Module**: Budget-required errors should become an in-context repair flow. The frontend should freeze the user's draft, help create or update the missing Budget permission, then replay the original money movement.
5. **User-Local Calendar Module**: User-facing date-only behavior should be centralized. Date-only parsing, comparison, month arithmetic, schedule preview, analytics ranges, and display labels should use one tested user-local calendar implementation.

These improvements should be implemented incrementally. Each slice should be narrow, demoable, and independently verifiable.

## User Stories

1. As a Sarflog user, I want Expected Inflow Debt repayment choices to include open Receivables, so that I can plan money I realistically expect to receive.
2. As a Sarflog user, I want Expected Inflow Debt repayment choices to exclude closed Debts, so that old obligations do not clutter planning.
3. As a Sarflog user, I want Refund source choices to show the actual expense title and date, so that I can link the correct original expense.
4. As a Sarflog user, I want Refund source choices to exclude refund rows, so that I do not link a refund to another refund by mistake.
5. As a Sarflog user, I want Expected Inflow source options to behave consistently when I create and edit a promise of future money, so that planning support is reliable.
6. As a Sarflog user, I want the Budgets screen to focus on what needs my attention this month, so that monthly Budget permission remains easy to scan.
7. As a Sarflog user, I want Project cards on the Budgets screen to be concise status summaries, so that active Budget work is not buried under Project configuration.
8. As a Sarflog user, I want to open a Project details view when I need to manage Project structure, so that heavy Project work has enough space.
9. As a Sarflog user, I want Project lifecycle actions to live where I can see the Project context, so that pause, resume, complete, restore, and deletion decisions are less confusing.
10. As a Sarflog user, I want Project deletion resolution to show affected expenses clearly, so that I understand what detach or delete means.
11. As a Sarflog user, I want archived Project actions to be state-aware, so that I am not offered actions that already happened.
12. As a Sarflog user, I want Project copy to use user language, so that ledger-safe behavior does not sound intimidating.
13. As a Sarflog user, I want wallet balances, Budget summaries, dashboards, analytics, Debts, Goals, and Expected Income to refresh after money movement, so that the app reflects ledger truth.
14. As a Sarflog user, I want changes such as refunds, splits, wallet fees, Debt payments, Payment Plan payments, and Goal contributions to refresh related views consistently, so that I do not distrust stale numbers.
15. As a Sarflog user, I want Budget-required errors to keep me in the same workflow, so that I do not lose the money movement I was recording.
16. As a Sarflog user, I want the app to tell me which Budget permission is missing, so that repair is concrete.
17. As a Sarflog user, I want the repair flow to suggest a useful Budget limit, so that I can fix the plan quickly.
18. As a Sarflog user, I want the original money movement to retry after Budget permission is added, so that strict rules still feel forgiving.
19. As a Sarflog user, I want Budget-required handling to work for one-time expenses, recurring templates, session drafts, Debt settlement, and Payment Plan charges, so that all money flows behave consistently.
20. As a Sarflog user, I want today's date to mean my local today, so that dates do not shift when I use the app near midnight.
21. As a Sarflog user, I want Payment Plan schedule previews to stay on the intended due dates, so that installments do not drift by timezone.
22. As a Sarflog user, I want analytics date ranges to use my selected dates, so that reports match my real calendar.
23. As a Sarflog user, I want dashboard due labels to use the same calendar math everywhere, so that "today", "tomorrow", and "overdue" are trustworthy.
24. As a Sarflog user, I want forms with max dates and default dates to use the same local-date behavior, so that validation does not contradict display.
25. As a developer, I want Expected Inflow source selection behind one read model, so that backend payload shape changes are handled in one place.
26. As a developer, I want ADR-0018 enforced by tests at the source picker seam, so that feed unwrapping and status matching do not regress.
27. As a developer, I want Budgets to stop owning Project execution state, so that Budget permission and Project lifecycle logic have better locality.
28. As a developer, I want the Project details seam to absorb Project structure, deletion resolution, and lifecycle workflows, so that Project tests target the right surface.
29. As a developer, I want query-key naming centralized, so that spelling differences cannot silently skip invalidations.
30. As a developer, I want ledger side-effect invalidations centralized, so that money-flow modules do not each carry a private map of the whole app.
31. As a developer, I want Budget-required recovery behind one module, so that transaction flows share repair-and-replay behavior.
32. As a developer, I want the Budget Interceptor to use structured backend errors, so that localization and recovery do not depend on fragile message text.
33. As a developer, I want user-local calendar operations behind one module, so that screens do not decide individually when raw JavaScript dates are safe.
34. As a developer, I want frontend date tests at timezone boundaries, so that bugs are caught when UTC and the user's local date differ.
35. As a developer, I want each deepened module to be tested through its public seam, so that tests verify behavior rather than implementation details.
36. As a developer, I want the changes to be incremental, so that each issue can be implemented and reviewed without a giant frontend rewrite.
37. As a developer, I want existing route contracts and backend endpoints preserved where possible, so that frontend deepening does not trigger unnecessary backend scope.
38. As a developer, I want ADR-0009, ADR-0018, ADR-0020, and the frontend timezone rules to be reflected in code organization, so that future agents stop rediscovering the same decisions.
39. As a developer, I want old compatibility behavior to remain stable while callers migrate, so that users do not see regressions during refactors.
40. As a developer, I want final guardrails that make shallow reintroductions obvious, so that this architecture work stays durable.

## Implementation Decisions

- Treat this PRD as a frontend architecture program, not a visual redesign.
- Preserve the existing browser timezone header behavior.
- Preserve the existing core domain vocabulary: Wallets are reality, Budgets are permission, Expected Income is planning support, Goals are protected real money, and Credit is payment capacity.
- Respect ADR-0009 for in-context Budget-required recovery.
- Respect ADR-0018 for frontend payload unwrapping and status matching.
- Respect ADR-0020 for Project two-layer disclosure.
- Respect the frontend date rule that user-facing date-only behavior must use user-local dates.
- Implement the Expected Inflow source picker as a deeper read model that returns source options for each source kind.
- The Expected Inflow source read model owns backend payload unwrapping for feed-oriented expense data.
- The Expected Inflow source read model owns Debt receivable eligibility and must not rely on legacy `ACTIVE` status when lifecycle state is the real rule.
- The Expected Inflow source read model should not merge Expected Inflow Agreement and Schedule concepts; ADR-0012 remains intact.
- The Expected Inflow editor should consume normalized options rather than raw backend payloads where practical.
- The Project details seam should be introduced incrementally while the Budgets screen keeps existing summary behavior.
- The Budgets screen should remain the Layer 1 monthly attention surface.
- The Project details seam should absorb heavy Project execution flows: structure editing, lifecycle actions, deletion resolution, affected expense context, and future Project-only analysis.
- Project details work should preserve existing Overlay Project behavior.
- Frozen Isolated Project behavior remains governed by ADR-0022 and should not be expanded by this PRD.
- The existing Budget details view remains separate from Project details; Budget details explain one Budget permission category, while Project details explain one Project lifecycle.
- The ledger side-effect cache module owns canonical query-key naming for frontend data that reflects ledger truth or plan health.
- Query-key compatibility may be transitional where existing screens already use old key spellings.
- Money mutation hooks should call named invalidation behavior instead of duplicating broad query lists.
- Cache invalidation migration should start with the safest common flows, then move through Wallets, Expenses, Income, Expected Inflows, Debts, Payment Plans, Goals, Assets, Budgets, Dashboard, Analytics, and Notifications.
- The Budget Interceptor should capture structured Budget-required errors and avoid depending on localized text parsing.
- The Budget Interceptor should preserve the user's original draft or mutation payload until the repair flow succeeds, fails, or is cancelled.
- The Budget Interceptor should create or update the missing Budget permission and then replay the original money movement.
- The first Budget Interceptor slice should prove the behavior on one-time expense creation before broader flows migrate.
- Later Budget Interceptor slices should cover recurring templates, session drafts, Debt settlement, Payment Plan charges, and other money flows that can hit strict Budget permission.
- The user-local calendar module should own date-only parsing, formatting, comparison, month arithmetic, and schedule preview behavior.
- Raw JavaScript date operations can remain for technical timestamps, auth token expiry, or purely technical timing where user-facing date-only behavior is not involved.
- Payment Plan schedule preview is the first high-value calendar migration because date-only `toISOString` behavior can shift intended due dates.
- Dashboard, analytics, forms, and validation should migrate after the Payment Plan calendar seam is proven.
- All work should be delivered as thin vertical slices with tests in each slice.
- Avoid broad file movement unless a slice creates a real deeper module and migrates one user-visible path to it.
- Avoid introducing TypeScript or a new form framework as part of this PRD.
- Avoid replacing React Query; the work is to deepen how the app uses it.
- Avoid backend migrations unless a narrow Budget Interceptor contract gap is discovered and documented.

## Testing Decisions

- Test external behavior at the highest useful seam, not private helper call order.
- Expected Inflow source tests should verify user-visible source options for Earned income, Receivable Debt repayment, Refund, and Asset Sale.
- Expected Inflow source tests should cover open versus closed Debt eligibility and expense feed unwrapping.
- Project details tests should verify that Budgets remains a monthly attention surface and that Project detail flows remain reachable.
- Project deletion resolution tests should verify user-language actions and affected expense context where the data is available.
- Cache tests should verify that a completed money mutation invalidates or refreshes the correct user-visible views through the shared cache module.
- Cache tests should include at least one regression for query-key spelling compatibility.
- Budget Interceptor tests should verify that a Budget-required error freezes the draft, opens repair, submits Budget permission, and replays the original money movement.
- Budget Interceptor tests should cover cancellation, repair failure, and replay failure.
- Date tests should use fixed dates and explicit browser/user timezones.
- Payment Plan date tests should cover a timezone where local midnight and UTC date differ.
- Dashboard and analytics date tests should verify sorting, range validation, and display labels without date shifting.
- Tests should prefer existing frontend test style where present.
- Existing Node-based module tests can be used for pure read models, payload builders, cache rules, and calendar helpers.
- React behavior tests should be added only where the behavior cannot be proven through pure module tests.
- Frontend build verification should run in Docker when practical, following project Docker-first rules.
- If Docker is unavailable, local frontend build or targeted Node tests may be used and the verification limitation should be noted.

## Out of Scope

- Backend architecture refactors beyond a narrow Budget Interceptor contract gap.
- Database migrations.
- New money domain behavior.
- Multicurrency.
- Shared spaces or household collaboration.
- Premium plan redesign.
- Full visual redesign of the Budgets, Project, Income, Dashboard, or Analytics screens.
- Replacing React Query.
- Introducing TypeScript.
- Replacing the current UI primitive library.
- Rewriting every frontend feature folder.
- Removing all legacy query keys in one slice.
- Solving every timezone display issue in the whole app in the first calendar slice.
- New Isolated Project or Fund Project work.
- Changing the core philosophy that Budgets are permission, not physical envelopes.
- Changing immutable ledger behavior.
- Changing route URLs unless a Project details route is introduced as part of ADR-0020 execution.

## Further Notes

- The top recommendation from the architecture review is to start with the Expected Inflow source picker because it has the clearest deletion test and directly enforces ADR-0018.
- The second safest foundation is the ledger side-effect cache module because later Budget Interceptor and Project flows will benefit from consistent refresh behavior.
- The Project details seam should stay disciplined: Budgets should route to Project depth, not absorb it.
- The calendar work is high leverage because user-local dates are product behavior in Sarflog, not formatting.
- This PRD intentionally groups five candidates because they share one architectural theme: risky product knowledge should live behind deep modules instead of being reimplemented by callers.
