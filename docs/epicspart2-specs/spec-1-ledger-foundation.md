# Spec 1: Ledger Foundation & Chronological Integrity

## Problem Statement

Sarflog is a ledger-first, cash-aware spending-permission system. Users need to trust that once money is recorded, the app will not quietly rewrite history, double-count pre-onboarding money, or let old transactions corrupt the live budget.

Right now, the next wave of debt, payment-plan, income, and planning work depends on four foundation rules being true everywhere:

- Wallet opening balances are sealed epoch snapshots.
- Income and expected inflows cannot sneak before the wallet epoch.
- Normal money logging is today-focused, with reconciliation handling missed past reality.
- Posted financial events are immutable and corrected through void-and-reversal, not hard delete or amount mutation.

If these boundaries are not made explicit before the rest of Epicspart2 work proceeds, new features may accidentally build on mutable history. That would make later debt, payment-plan, expected-inflow, and reconciliation work harder to trust and harder to refactor.

## Solution

Build a small but firm ledger foundation before deeper Epicspart2 feature execution.

From the user's perspective, Sarflog should behave like a trustworthy financial notebook:

- When they create a wallet, the starting balance becomes the beginning of tracked financial truth for that wallet.
- They cannot create expenses, income, transfers, settlements, or expected inflows before the relevant wallet exists.
- Normal daily logging stays fast and current-day focused.
- Missed past activity goes through reconciliation, not casual backdating.
- When they delete or correct posted money, Sarflog keeps the original fact, appends the mathematical correction, and shows the corrected current state.
- Metadata can be cleaned up without changing money history.

From the engineering perspective, this spec creates the minimum immutable-ledger foundation needed before building more debt and payment-plan behavior:

- A shared financial-event reversal pattern.
- Consistent wallet-epoch and user-timezone date validation.
- A clear rule that posted financial math is append-only.
- Focused regression tests at route/service seams.
- A first concrete conversion slice for standalone income update/delete, because it is a small, high-confidence example of the architecture.

## User Stories

1. As a user, I want my wallet opening balance to be treated as the start of tracked truth, so that old pre-Sarflog history is not double-counted.
2. As a user, I want Sarflog to block expenses before a wallet's creation date, so that my wallet balance stays mathematically honest.
3. As a user, I want Sarflog to block income before a wallet's creation date, so that past salary or gifts do not inflate my current balance twice.
4. As a user, I want expected inflows to respect the wallet epoch, so that planning promises do not pretend to exist before my tracked financial life began.
5. As a user, I want same-day wallet setup and same-day logging to be allowed, so that I can start using the app immediately after onboarding.
6. As a user, I want each wallet to have its own epoch boundary, so that a newer wallet does not restrict older wallets or vice versa.
7. As a user, I want normal expense entry to be fast for today's spending, so that everyday tracking stays low-friction.
8. As a user, I want normal income entry to be fast for today's received money, so that current cash is easy to record.
9. As a user, I want missed past activity to go through reconciliation, so that I am forced to compare app reality with wallet reality instead of casually rewriting history.
10. As a user, I want a grace window for month-end cleanup, so that I can correct recent missed activity without corrupting long-closed months.
11. As a user, I want closed months to stay sealed, so that old reports do not keep changing after I have moved on.
12. As a user, I want missed closed-period activity to become a current correction, so that today's plan absorbs the correction honestly.
13. As a user, I want deleting a posted expense to void it rather than erase it, so that I can still understand what happened before.
14. As a user, I want deleting a posted income entry to reverse it rather than erase it, so that money-in history stays explainable.
15. As a user, I want correcting a posted income amount to preserve the original and add the correction, so that my financial journal tells the truth.
16. As a user, I want correcting a posted wallet allocation to preserve the original movement, so that wallet history remains reconstructable.
17. As a user, I want correcting a posted category allocation to preserve the original allocation, so that budget history remains explainable.
18. As a user, I want metadata-only edits to remain simple, so that fixing a title or note does not create noisy correction history.
19. As a user, I want the app to prevent accidental hard deletes of posted financial events, so that my audit trail cannot disappear.
20. As a user, I want reversal events to be linked to the original events, so that I can see why a balance changed.
21. As a user, I want wallet balances to remain correct after a void, reversal, or correction, so that the current app state matches real life.
22. As a user, I want debt and payment-plan work to follow the same money-history rules, so that obligations do not become a separate inconsistent system.
23. As a user, I want the app to preserve the difference between real money movement and planning intent, so that expected inflows and budgets do not masquerade as cash.
24. As a user, I want the app to use my timezone for today and date boundaries, so that a transaction is not rejected or accepted because of the server's clock.
25. As a user, I want clear error messages when a date violates an epoch or closed-period rule, so that I understand what action is allowed instead.
26. As a user, I want corrections to affect the right month according to the app's rules, so that budget reports remain stable.
27. As a user, I want historical data before Sarflog to stay outside the active ledger, so that onboarding remains simple and mathematically clean.
28. As a user, I want the app to protect both cash wallets and credit wallets with the same epoch principle, so that all account types remain consistent.
29. As a user, I want transfers to respect both wallet epochs, so that money cannot move through a wallet before that wallet exists.
30. As a user, I want reconciliation adjustments to be ledger-backed, so that balance repairs are visible rather than hidden.
31. As a developer, I want one shared reversal pattern, so that future modules do not invent incompatible void/delete behavior.
32. As a developer, I want one clear date-validation path for user-facing money rules, so that timezone and epoch behavior is consistent.
33. As a developer, I want tests to cover behavior at route/service seams, so that refactors can change internals without weakening the product contract.
34. As a developer, I want new Epicspart2 work to use the foundation immediately, so that we do not create new mutable history that must be rewritten later.
35. As a developer, I want legacy violations to be identified and fixed in focused slices, so that the foundation improves without turning into a giant blocking rewrite.

## Implementation Decisions

- Treat this spec as the first Epicspart2 execution dependency. It should be completed before deeper debt, payment-plan, expected-inflow, or goal money-history features are built.
- Do not attempt a full platform-wide immutable-ledger rewrite in one pass. The first slice should establish the shared foundation and convert the most obvious high-value violation.
- The foundation should enforce the accepted wallet epoch rule at date granularity. Same-day activity is allowed; earlier dates are blocked.
- Wallet epoch validation must be per wallet, not global per user.
- Income and expected inflow creation must honor the same epoch boundary as expenses and wallet-touching flows.
- Normal money logging should remain today-focused. Past or missed activity belongs to reconciliation.
- Closed-period behavior should preserve the distinction between open month, closing window, closed month, and current correction.
- User-facing date calculations must use the effective user timezone, not server-local dates.
- Posted financial-event math should be append-only. Amount, wallet, category, source, date, and allocation changes should not mutate the posted event in place.
- Metadata-only edits may remain mutable when they do not change money math.
- Deleting a posted financial event means voiding the original and appending a reversal event with counter-balancing ledger legs.
- Reversal events must preserve enough links to explain the relationship between original event, reversal event, domain object, wallet legs, and entity legs.
- A shared financial-event reversal service should be the main seam for voiding posted money events.
- New debt and payment-plan work should use the shared immutable pattern immediately, even if older debt/payment-plan escape hatches are converted gradually.
- Standalone income update/delete should be the first concrete conversion slice because it is small, visible, and exercises the same invariants needed by later modules.
- Existing expense delete behavior can be used as prior art for the void-and-reversal pattern.
- Existing financial-event posting behavior can be used as the primary posting seam for new money movement.
- Current-state fields such as wallet balance, debt remaining amount, and payment-plan status may remain as projections, but the underlying money facts should be reconstructable from ledger history.
- Budget limits, recurring templates, and drafts should not be forced into the global financial ledger. They are permission, intent, or pre-finalization state unless real money is posted.
- The spec should not introduce import tooling, bank parsing, or broad feature work. It is a foundation for chronological and mutation integrity.
- The implementation should prefer focused route/service behavior changes over broad schema churn unless a schema change is necessary to preserve reversal links.

## Testing Decisions

- Tests should assert externally visible behavior, not private implementation details.
- Date-boundary tests should use explicit user timezones and the project's timezone helpers.
- Wallet epoch tests should cover expenses, income, transfers, reconciliation, and any wallet-touching obligation flow that creates money movement.
- Income backdating tests should cover both direct income and expected inflow promises.
- Strict logging tests should cover today-only normal entry, reconciliation-based past entry, closing-window behavior, closed-period correction behavior, and pre-epoch rejection.
- Immutable-ledger tests should prove that deleting a posted event leaves the original event available, marks it voided, appends a reversal event, and restores wallet math.
- Income update/delete tests should prove that financial-field changes do not rewrite the original posted event or delete its ledger legs.
- Metadata-only edit tests should prove that title/note changes remain possible without creating unnecessary reversal rows.
- Reversal tests should verify link integrity between original event and reversal event.
- Projection tests should verify wallet balance after create, void, reversal, and corrected repost.
- Regression tests should be added for any known legacy route that previously hard-deleted posted money.
- Existing expense void tests, financial-event ledger seam tests, income ledger tests, transfer/reconciliation ledger tests, debt ledger tests, and payment-plan ledger tests should be used as prior art.
- Tests should preserve the distinction between immutable financial facts and mutable projections.
- Tests should avoid asserting exact internal helper names unless those helpers are public service seams.

## Out of Scope

- Full conversion of every historical debt and payment-plan edge case.
- Full database-level immutability constraints for every ledger table.
- Importing bank schedules, parsing statements, OCR, CSV import, or screenshot processing.
- Rebuilding the entire budget engine.
- Rewriting recurring templates, session drafts, or budget permission models into financial ledger events.
- Full asset lifecycle event-sourcing.
- Isolated Projects and Fund Project expansion.
- Historical data migration for pre-Sarflog user history.
- Reporting UI redesign for audit trails.
- Long-term retention or hard-delete sweeper policy for old voided data.

## Further Notes

This spec is intentionally a foundation slice, not a giant refactor. The goal is to stop new Epicspart2 work from adding more mutable money history while proving the immutable pattern on one concrete existing area.

The most practical execution order is:

1. Standardize shared reversal behavior for posted financial events.
2. Enforce wallet epoch and user-timezone date boundaries consistently.
3. Convert standalone income update/delete to void, reversal, and corrected repost behavior.
4. Make new debt and payment-plan work use the same append-only pattern.
5. Convert older escape hatches as they are touched by later specs.

The important product principle is: Sarflog should save truth first and repair plans second. The app can help users recover from mistakes, but it should not pretend the original money history never happened.
