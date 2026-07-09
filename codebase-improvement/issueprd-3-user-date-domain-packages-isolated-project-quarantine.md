# Issue Breakdown For PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

Parent PRD: `prd-3-user-date-domain-packages-isolated-project-quarantine.md`

Triage: ready-for-agent

## Proposed Breakdown For Approval

1. **Introduce the Required User-Date seam through normal expense posting**
   - Type: AFK
   - Blocked by: PRD 1 Issue 1
   - User stories covered: 1, 2, 3, 11, 16, 17, 19, 20, 30

2. **Route session draft and recurring expense dates through the Required User-Date seam**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 2, 3, 6, 10, 16, 17, 18, 19, 30

3. **Route Debt and Payment Plan due-date and posting flows through the Required User-Date seam**
   - Type: AFK
   - Blocked by: 1, PRD 2 Issues 6 and 7
   - User stories covered: 2, 4, 10, 16, 17, 18, 19, 25, 30

4. **Route income, expected inflow, refund, transfer, and reversal dates through the Required User-Date seam**
   - Type: AFK
   - Blocked by: 1
   - User stories covered: 5, 8, 9, 10, 16, 17, 18, 19, 20, 30

5. **Add cross-flow timezone boundary regression coverage**
   - Type: AFK
   - Blocked by: 2, 3, 4
   - User stories covered: 1, 2, 3, 4, 5, 6, 7, 19, 30

6. **Define the post-deepening domain package split map**
   - Type: HITL
   - Blocked by: PRD 1 and PRD 2 core posting and permission seams
   - User stories covered: 21, 22, 23, 24, 25, 30

7. **Split the first stable ledger and posting domain package with compatibility exports**
   - Type: AFK
   - Blocked by: 6
   - User stories covered: 21, 22, 23, 24, 30

8. **Split Budget Permission and Budget Reporting domain packages with behavior-preserving tests**
   - Type: AFK
   - Blocked by: 6, PRD 2 Issues 1 through 4
   - User stories covered: 21, 22, 23, 24, 30

9. **Split Debt and Payment Plan domain packages without merging obligation rules**
   - Type: AFK
   - Blocked by: 6, PRD 2 Issues 5 through 8
   - User stories covered: 21, 22, 23, 25, 30

10. **Define the Frozen Isolated Project quarantine contract**
    - Type: AFK
    - Blocked by: None - can start immediately
    - User stories covered: 12, 13, 14, 15, 26, 27, 28, 30

11. **Route core Budget, Project, and Expense Posting isolated checks through the quarantine contract**
    - Type: AFK
    - Blocked by: 10, PRD 2 Issue 2
    - User stories covered: 12, 13, 14, 15, 24, 26, 27, 28, 29, 30

12. **Add isolated quarantine regression coverage and guardrails**
    - Type: AFK
    - Blocked by: 11
    - User stories covered: 12, 13, 14, 15, 26, 27, 28, 29, 30

Review questions before implementation:

- Should issue 6 be HITL, or do you want agents to choose the package split map without review?
- Should the first package split target ledger/posting as written, or should Budget be first after PRD 2 settles?
- Does the isolated quarantine wording feel strict enough that agents will preserve old compatibility without reviving the frozen feature?
- Are any date-sensitive flows missing from issues 1 through 5?

---

## Issue 1: Introduce The Required User-Date Seam Through Normal Expense Posting

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Introduce a Required User-Date seam through the normal expense posting path. Normal expense creation should resolve the user's effective timezone at the route or job boundary and pass an explicit user-local business date into posting behavior whenever the caller omits an expense date or asks for "today".

This issue should prove the seam on the safest and most common money-posting path before broader flows are migrated.

## Acceptance criteria

- [x] Normal expense creation with an explicit date preserves the provided date.
- [x] Normal expense creation without an explicit date uses the user's effective local date.
- [x] Budget month selection for a posted expense uses the user-local business date.
- [x] A timezone boundary test proves the expense lands on the user's local day when UTC and the user's date differ.
- [x] Technical audit timestamps remain timezone-aware UTC.
- [x] Normal expense route contracts remain stable.
- [x] Existing normal expense, Budget, Wallet, and ledger tests pass.
- [x] New regression coverage proves normal expense posting cannot silently fall back to server-local "today".

## Blocked by

- PRD 1 Issue 1: Create The Financial Event Ledger Seam Through Normal Expense Posting

---

## Issue 2: Route Session Draft And Recurring Expense Dates Through The Required User-Date Seam

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Route session draft finalization and recurring expense confirmation through the Required User-Date seam. Draft finalization and recurring confirmation should use explicit user-local business dates for default posting dates, Budget month impact, and any "today" validation.

Interactive flows should resolve dates from the request/user timezone. Background recurring flows should resolve dates from the stored user timezone.

## Acceptance criteria

- [x] Session draft finalization with explicit item dates preserves those dates.
- [x] Session draft finalization without explicit item dates uses the user's effective local date.
- [x] Recurring expense confirmation uses the correct user-local occurrence or confirmation date.
- [x] Background recurring behavior resolves user-facing dates from the stored user timezone.
- [x] Budget month impact remains correct for session drafts and recurring expenses.
- [x] Existing session draft and recurring tests pass.
- [x] New timezone boundary coverage proves these flows do not use server-local "today".

## Blocked by

- Issue 1: Introduce The Required User-Date Seam Through Normal Expense Posting

---

## Issue 3: Route Debt And Payment Plan Due-Date And Posting Flows Through The Required User-Date Seam

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Route Debt and Payment Plan due-date status and posting flows through the Required User-Date seam. Debt and Payment Plan domains must remain separate, but both should use explicit user-local dates for due status, charge posting, payment posting, schedule behavior, and Budget month impact.

This issue should build on the shared posting work from PRD 2 without merging Debt and Payment Plan domain rules.

## Acceptance criteria

- [x] Debt due, overdue, and warning status uses the user's local business date.
- [x] Payment Plan due, overdue, and schedule status uses the user's local business date.
- [x] Debt charge and payment posting uses explicit user-local dates.
- [x] Payment Plan charge and payment posting uses explicit user-local dates.
- [x] Budget month impact remains correct for obligation-related spending.
- [x] Background or scheduled obligation behavior resolves from stored user timezone where relevant.
- [x] Debt and Payment Plan domain separation remains unchanged.
- [x] Existing Debt and Payment Plan tests pass.
- [x] New timezone boundary coverage proves due-date status does not shift because of server-local date.

## Blocked by

- Issue 1: Introduce The Required User-Date Seam Through Normal Expense Posting
- PRD 2 Issue 6: Route Debt Charge Money Events Through Shared Posting Seams
- PRD 2 Issue 7: Route Payment Plan Charge And Payment Money Events Through Shared Posting Seams

---

## Issue 4: Route Income, Expected Inflow, Refund, Transfer, And Reversal Dates Through The Required User-Date Seam

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Route non-expense money flows through the Required User-Date seam where user-facing dates matter. Income receipt, expected inflow receipt, refunds, wallet transfers, reconciliation adjustments, voids, and reversals should use explicit business dates for user-visible ledger behavior while keeping technical audit timestamps in UTC.

## Acceptance criteria

- [x] Income posting uses an explicit user-local business date when the user does not provide one.
- [x] Expected inflow receipt posting uses an explicit user-local business date.
- [x] Refund posting preserves intended refund and original-expense date behavior.
- [x] Wallet transfer and reconciliation date behavior is explicit and user-local where user-facing.
- [x] Voids and reversals preserve immutable ledger behavior while using correct business dates for user-visible entries.
- [x] Technical timestamps remain timezone-aware UTC.
- [x] Existing income, expected inflow, refund, transfer, reconciliation, void, and reversal tests pass where present.
- [x] New timezone boundary coverage proves these flows do not fall back to server-local user-facing dates.

## Blocked by

- Issue 1: Introduce The Required User-Date Seam Through Normal Expense Posting

---

## Issue 5: Add Cross-Flow Timezone Boundary Regression Coverage

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Add cross-flow timezone boundary coverage proving the Required User-Date seam protects the stable core. The tests should cover representative flows where UTC and the user's timezone produce different local dates or months.

This issue is a verification slice after the main migrations, not a new product behavior slice.

## Acceptance criteria

- [x] Normal expense posting is covered at a timezone boundary.
- [x] Session draft finalization is covered at a timezone boundary.
- [x] Recurring confirmation or scheduler behavior is covered at a timezone boundary.
- [x] Debt due-date status is covered at a timezone boundary.
- [x] Payment Plan due-date or schedule behavior is covered at a timezone boundary.
- [x] Income or expected inflow receipt is covered at a timezone boundary.
- [x] At least one refund, transfer, reversal, or reconciliation path is covered where user-facing dates matter.
- [x] Tests use timezone-aware project helpers rather than generic system date helpers.
- [x] Relevant backend tests pass in Docker.

## Blocked by

- Issue 2: Route Session Draft And Recurring Expense Dates Through The Required User-Date Seam
- Issue 3: Route Debt And Payment Plan Due-Date And Posting Flows Through The Required User-Date Seam
- Issue 4: Route Income, Expected Inflow, Refund, Transfer, And Reversal Dates Through The Required User-Date Seam

---

## Issue 6: Define The Post-Deepening Domain Package Split Map

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Define the package split map for backend domains after the deeper posting and permission seams have settled. The map should identify the domain package boundaries, compatibility strategy, migration order, import rules, and rollback-safe approach before any large file movement happens.

This is marked HITL because package boundaries affect long-term architecture. The agent can draft the map, but a human should approve the final package plan before file moves begin.

## Acceptance criteria

- [x] The package map follows stable domain seams rather than file size alone.
- [x] Expense Posting, Financial Event Ledger, Budget Permission, Budget Reporting, Wallets, Goals, Projects, Debt, Payment Plans, Income, Expected Inflows, Recurring, and Reports each have clear ownership.
- [x] Debt and Payment Plan remain separate domains.
- [x] Frozen Isolated Project behavior is not promoted into the active core package map.
- [x] The plan includes a compatibility export or transition strategy.
- [x] The plan includes a dependency order for package moves.
- [x] The plan identifies tests that must pass after each package move.
- [ ] Human approval is captured before implementation issues begin. *(See `codebase-improvement/domain-package-split-map.md` Section 8)*

## Blocked by

- PRD 1 core posting seams
- PRD 2 core Budget Permission and obligation posting seams

---

## Issue 7: Split The First Stable Ledger And Posting Domain Package With Compatibility Exports

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Move the first stable ledger and posting domain definitions behind the approved package split map. This should be a behavior-preserving package split that keeps existing routes, services, serialization, database mappings, and tests working through compatibility exports while the codebase transitions.

The target should be narrow enough to complete and verify independently.

## Acceptance criteria

- [x] The moved ledger/posting domain definitions follow the approved package map.
- [x] Compatibility exports preserve existing behavior during the transition.
- [x] Routes and services continue returning the same responses.
- [x] Database mappings remain stable.
- [x] No historical ledger data is rewritten.
- [x] No new product behavior is introduced.
- [x] Existing ledger, expense posting, wallet, and related tests pass.
- [x] New smoke coverage or import coverage proves the compatibility surface works.

## Blocked by

- Issue 6: Define The Post-Deepening Domain Package Split Map

---

## Issue 8: Split Budget Permission And Budget Reporting Domain Packages With Behavior-Preserving Tests

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Move Budget Permission and Budget Reporting into separate domain package surfaces according to the approved package map. The split should preserve the PRD 2 decision that write-time permission and display-time reporting are different interfaces.

## Acceptance criteria

- [x] Budget Permission remains the write-time spending permission interface.
- [x] Budget Reporting remains the display-time read interface.
- [x] Money-posting callers do not depend on Budget reporting output.
- [x] Budget Month Summary output remains unchanged.
- [x] Project Budget View output remains unchanged where relevant.
- [x] Compatibility exports preserve existing route and service behavior during the transition.
- [x] Existing Budget Permission, Budget reporting, project budget, and expense tests pass.
- [x] New regression coverage proves the package split did not reconnect permission and reporting.

## Blocked by

- Issue 6: Define The Post-Deepening Domain Package Split Map
- PRD 2 Issue 1: Introduce Budget Permission Through Normal Expense Posting
- PRD 2 Issue 2: Move Subcategory And Project Spend Checks Behind Budget Permission
- PRD 2 Issue 3: Separate Budget Month Summary From Budget Permission
- PRD 2 Issue 4: Separate Project Budget View From Budget Permission

---

## Issue 9: Split Debt And Payment Plan Domain Packages Without Merging Obligation Rules

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Move Debt and Payment Plan domain definitions into package surfaces according to the approved package map while preserving their intentional separation. Shared money-posting mechanics may remain shared through posting seams, but Debt and Payment Plan models, schemas, rules, status logic, and lifecycle behavior must not be merged.

## Acceptance criteria

- [x] Debt remains an open-ended running-balance obligation domain.
- [x] Payment Plan remains a scheduled obligation domain with rows and waterfall behavior.
- [x] Shared posting mechanics stay behind Expense Posting, Financial Event Ledger, Budget Permission, and related money seams.
- [x] No generic shared obligation table, lifecycle, schema, or package replaces the two domains.
- [x] Compatibility exports preserve existing route and service behavior during the transition.
- [x] Existing Debt tests pass.
- [x] Existing Payment Plan tests pass.
- [x] New regression coverage proves the package split did not merge Debt and Payment Plan concepts.

## Blocked by

- Issue 6: Define The Post-Deepening Domain Package Split Map
- PRD 2 Issue 5: Define The Obligation Money Posting Seam Without Merging Domains
- PRD 2 Issue 6: Route Debt Charge Money Events Through Shared Posting Seams
- PRD 2 Issue 7: Route Payment Plan Charge And Payment Money Events Through Shared Posting Seams
- PRD 2 Issue 8: Add Cross-Flow Budget Interceptor And Decoupling Regression Coverage

---

## Issue 10: Define The Frozen Isolated Project Quarantine Contract

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Define a Frozen Isolated Project quarantine contract that represents the small set of compatibility questions stable core modules are still allowed to ask while ADR-0022 remains active. The contract should preserve existing compatibility behavior without starting new Isolated Project or Fund Project work.

This issue should make the freeze visible in code organization and documentation so future agents do not treat older isolated project PRDs as active execution targets.

## Acceptance criteria

- [x] The contract clearly states that Isolated Projects and Fund Project work remain frozen under ADR-0022.
- [x] The contract exposes only compatibility behavior needed by stable core modules.
- [x] The contract does not add top-ups, rebalancing, stash release, sweep, Fund Project graduation, project-protection breach resolution, or new isolated micro-subcategory behavior.
- [x] Overlay Project behavior remains outside the frozen quarantine.
- [x] Existing isolated project records remain readable where currently supported.
- [x] Documentation or inline guidance warns agents not to expand isolated mechanics.
- [x] Existing Project, Budget, and Expense tests still pass before broader routing changes.

## Blocked by

None - can start immediately

---

## Issue 11: Route Core Budget, Project, And Expense Posting Isolated Checks Through The Quarantine Contract

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Route existing isolated project compatibility checks in core Budget, Project, and Expense Posting behavior through the Frozen Isolated Project quarantine contract. Stable core modules should stop carrying scattered isolated project special cases directly.

This issue preserves current behavior. It must not deepen isolated stash mechanics or activate new Isolated Project features.

## Acceptance criteria

- [x] Existing monthly-budget bypass compatibility for isolated project spending is preserved where currently supported.
- [x] Existing project reporting compatibility remains readable where currently supported.
- [x] Overlay Project Budget behavior remains unchanged.
- [x] Expense Posting no longer needs scattered direct knowledge of frozen isolated project internals beyond the quarantine result.
- [x] Budget Permission no longer needs scattered direct knowledge of frozen isolated project internals beyond the quarantine result.
- [x] Project reporting no longer needs scattered direct knowledge of frozen isolated project internals beyond the quarantine result.
- [x] No new Isolated Project or Fund Project workflow is introduced.
- [x] Existing Budget, Project, and Expense tests pass.
- [x] New regression coverage proves the quarantine preserves behavior without expanding the feature.

## Blocked by

- Issue 10: Define The Frozen Isolated Project Quarantine Contract
- PRD 2 Issue 2: Move Subcategory And Project Spend Checks Behind Budget Permission

---

## Issue 12: Add Isolated Quarantine Regression Coverage And Guardrails

## Parent

PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

## What to build

Add regression coverage and guardrails proving ADR-0022 remains respected after isolated project code is quarantined. The stable core should preserve old compatibility behavior but should not expose, deepen, or depend on new Isolated Project or Fund Project mechanics.

## Acceptance criteria

- [x] Tests prove existing isolated project compatibility behavior remains stable where currently supported.
- [x] Tests prove Overlay Project behavior remains active and unchanged.
- [x] Tests or static checks catch accidental new dependencies from stable core modules into frozen isolated internals where practical.
- [x] Tests or documentation checks make clear that older Isolated Project PRDs are not active execution targets.
- [x] No new direct Isolated Project creation, Fund Project graduation, top-up, rebalance, sweep, stash release, or project-protection breach behavior is introduced.
- [x] Relevant Budget, Project, Expense Posting, and reporting tests pass.
- [x] Any remaining isolated project leakage that cannot be safely moved is documented as a follow-up with a reason.

## Blocked by

- Issue 11: Route Core Budget, Project, And Expense Posting Isolated Checks Through The Quarantine Contract
