# PRD 3: User-Date Seam, Domain Package Split, And Isolated Project Quarantine

Triage: ready-for-agent

## Problem Statement

Sarflog's backend is moving toward deeper money-posting seams, but three architecture risks still remain after the Expense Posting, Financial Event Ledger, Budget Permission, and obligation posting cleanups.

First, user-facing date behavior is not yet strict enough as an architectural rule. Sarflog already has timezone helpers and request timezone handling, but some money-posting and lifecycle flows can still fall back to caller-omitted dates, server-local dates, or generic "today" behavior. From the user's perspective, this can create wrong expense dates, wrong budget months, wrong due-date status, or wrong recurring behavior when the user's local day differs from the server day.

Second, the backend's model and schema surfaces are large. Splitting them too early would only move complexity into more files. The split should happen after deeper domain seams become stable, so the file tree expresses real boundaries instead of aspirational boundaries.

Third, ADR-0022 freezes Isolated Projects and Fund Project work, but some existing isolated project behavior still leaks into core Budget, Project, and Expense Posting logic. From the user's perspective, frozen experimental behavior should not distort the stable core app. From the developer's perspective, future agents should not accidentally continue Isolated Project work just because older code and issue files still exist.

## Solution

Create three backend architecture improvements:

1. **Required User-Date Seam**: money-posting, due-date, budget-month, recurring, project, income, expected inflow, Debt, and Payment Plan flows must receive or resolve an explicit user-local business date when user-facing behavior depends on "today", a posting date, a selected month, or a due-date status.
2. **Domain Package Split After Deepening**: split large model and schema surfaces only after stable seams exist. The split should follow real domain boundaries created by Expense Posting, Financial Event Ledger, Budget Permission, obligation flows, Wallets, Goals, Projects, Income, Expected Inflows, Recurring, and reporting.
3. **Frozen Isolated Project Quarantine**: preserve existing frozen isolated project behavior where needed, but route it behind a small quarantine contract so stable core modules do not learn or expand isolated project mechanics.

The goal is not to add new product behavior. The goal is to make Sarflog safer to change before larger work such as immutable architecture, multicurrency, shared spaces, and launch-readiness hardening.

## User Stories

1. As a Sarflog user, I want "today" to mean my local today, so that my expense dates are not shifted by the server timezone.
2. As a Sarflog user, I want posting dates to be consistent across normal expenses, session drafts, recurring expenses, Debt charges, and Payment Plan payments, so that the same real-world action lands on the same business day.
3. As a Sarflog user, I want Budget month selection to use my timezone, so that spending near midnight is assigned to the correct month.
4. As a Sarflog user, I want due-date status for Debts and Payment Plans to use my local date, so that something is not overdue too early or too late.
5. As a Sarflog user, I want expected inflow receipt and income dates to use my local date, so that money received today appears in the correct day and month.
6. As a Sarflog user, I want recurring confirmations to use my local calendar, so that repeated bills do not drift around timezone boundaries.
7. As a Sarflog user, I want project effective dates and completion checks to use my local date, so that project workflows match my real calendar.
8. As a Sarflog user, I want refunds and reversals to preserve correct business dates, so that ledger history remains understandable.
9. As a Sarflog user, I want wallet transfers and reconciliation adjustments to use intentional dates, so that cash movement history is auditable.
10. As a Sarflog user, I want background jobs to use my stored timezone, so that scheduled behavior stays correct even when I am not actively sending requests.
11. As a Sarflog user, I want invalid or missing request timezone data to fall back predictably, so that the app still works without corrupting dates.
12. As a Sarflog user, I want stable core features to remain free from frozen Isolated Project complexity, so that normal budgeting and spending stay simple.
13. As a Sarflog user, I want Overlay Projects to keep working while Isolated Projects remain frozen, so that current project planning is not blocked.
14. As a Sarflog user, I want existing isolated project records to remain readable if they already exist, so that old data is not broken by cleanup.
15. As a Sarflog user, I do not want new Isolated Project or Fund Project behavior to appear accidentally, so that frozen product decisions stay frozen.
16. As a developer, I want money-posting seams to require a user-local business date, so that no caller can accidentally use server-local "today".
17. As a developer, I want route code to resolve user timezone once and pass an explicit date context into domain flows, so that services do not guess.
18. As a developer, I want background services to resolve dates from stored user timezone, so that scheduled flows are deterministic.
19. As a developer, I want tests to cover timezone boundary behavior, so that bugs are caught when UTC and the user's local date differ.
20. As a developer, I want technical audit timestamps to remain timezone-aware UTC, so that operational history remains standard.
21. As a developer, I want domain packages to be split after stable seams exist, so that folders reflect real ownership.
22. As a developer, I want model and schema splits to preserve compatibility while migration is in progress, so that agents can move one domain at a time.
23. As a developer, I want import paths and domain ownership to become easier to navigate, so that future changes are faster and safer.
24. As a developer, I want Budget Permission, Expense Posting, and Financial Event Ledger boundaries to survive package splitting, so that folder work does not flatten the architecture again.
25. As a developer, I want Debt and Payment Plan packages to remain separate, so that their domain rules do not merge during organization cleanup.
26. As a developer, I want frozen isolated project logic behind one small contract, so that core modules do not accumulate scattered special cases.
27. As a developer, I want ADR-0022 to be enforced by code organization, so that old Isolated Project PRDs are not accidentally treated as active roadmap work.
28. As a developer, I want legacy isolated behavior to be labeled clearly, so that future agents understand it is preserved but not deepened.
29. As a developer, I want regression tests around isolated quarantine, so that cleanup does not delete old compatibility or expand frozen behavior.
30. As a developer, I want each architecture slice to be independently verifiable, so that agents can execute this PRD safely one issue at a time.

## Implementation Decisions

- The backend timezone helper layer remains the source of truth for resolving request timezone, user timezone, app default timezone, and UTC fallback.
- A user-facing business date is required whenever behavior depends on an expense date, budget month, due-date status, recurring occurrence date, project effective date, income date, expected inflow date, refund date, transfer date, or reconciliation date.
- Money-posting seams should receive an explicit user-local date or date context. They should not call generic "today" behavior for user-facing dates.
- Interactive routes should resolve effective timezone from request timezone first, then persisted user timezone, then app default, then UTC.
- Background services should resolve effective timezone from the stored user timezone, then app default, then UTC.
- Technical timestamps such as created, updated, voided, archived, token expiry, and security events remain timezone-aware UTC.
- Existing route contracts should remain stable unless a route is already returning incorrect user-facing dates.
- Existing persisted dates should not be rewritten as part of this PRD.
- Date cleanup should happen through high-value posting and lifecycle seams first, then lower-risk reporting and read flows.
- Domain package splitting should happen after deep posting and permission seams exist, not before.
- Package boundaries should follow domain ownership, not table count or file size alone.
- Compatibility exports or transitional import surfaces are acceptable during package splitting to keep vertical slices small.
- Each package split should include behavior-preserving tests before and after the move.
- Do not perform a broad one-shot model or schema rewrite.
- Do not combine Debt and Payment Plan packages into a generic obligation package.
- Do not move frozen Isolated Project work into the active core domain during package splitting.
- Frozen Isolated Project behavior should be routed behind a quarantine contract that can answer only the compatibility questions stable core modules still need.
- The quarantine contract may preserve old reads, eligibility checks, bypass checks, or display data, but it must not add top-ups, rebalancing, stash release, project-protection resolution, Fund Project graduation, or new isolated micro-subcategory behavior.
- Overlay Project behavior remains part of the active stable core.
- Existing Isolated Project records may remain readable and may preserve current compatibility behavior.
- ADR-0022 is authoritative until superseded by a later decision.
- This PRD depends conceptually on PRD 1 and PRD 2 because user-date strictness, package splitting, and isolated quarantine are safer after posting and permission seams are deeper.

## Testing Decisions

- Tests should verify external business behavior, not private helper call order.
- Add timezone boundary tests where UTC and the user's local date differ.
- Use existing timezone-aware test helpers when test data depends on "today".
- Route-level tests should cover interactive flows that resolve timezone from request context.
- Service or job-boundary tests should cover background flows that resolve timezone from stored user settings.
- Add regression coverage proving normal expense, session draft, recurring, Debt, Payment Plan, income, expected inflow, refund, transfer, and reversal paths do not fall back to server-local user-facing dates.
- Add focused tests for due-date and budget-month behavior where a one-day timezone difference changes the result.
- Add package-split tests that prove imports, serialization, route responses, and database behavior remain stable after each domain move.
- Add regression coverage proving frozen isolated project compatibility remains preserved without activating new Isolated Project work.
- Add tests or static checks where practical to catch new user-facing date logic that bypasses the required user-date seam.
- Use Docker-first verification for backend tests unless explicitly running locally.

## Out of Scope

- New frontend structure or frontend organization.
- New user-facing product features.
- Multicurrency.
- Shared household spaces.
- Premium gating.
- Caching.
- Rate-limit redesign.
- Idempotency redesign, except where date context naturally touches money-posting safety.
- Rewriting historical ledger rows.
- Changing existing route URLs.
- New Isolated Project product work.
- Fund Project goal creation or graduation UX.
- Isolated project top-ups, rebalancing, wrap-up, sweep, stash release, or project-protection breach resolution.
- Deleting all existing isolated project code.
- One-shot broad model and schema rewrites.
- Database migrations unless a narrow package split reveals a necessary compatibility constraint.

## Further Notes

- "Required User-Date Seam" means user-facing calendar behavior must be explicit. It does not mean every technical timestamp becomes local time.
- The package split should be boring and incremental. First deepen behavior, then move code.
- The isolated project quarantine is a safety boundary, not a revival of the feature.
- A good deletion test for the user-date seam: if deleting it allows money posting to silently use server-local "today", the seam is doing real work.
- A good deletion test for domain package splitting: if moving files changes behavior, the split is too risky or too broad.
- A good deletion test for isolated quarantine: if deleting the quarantine scatters isolated project conditionals across Budget, Project, and Expense Posting again, the quarantine is earning its place.
