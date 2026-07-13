# Spec: UI1 Ledger Foundation Disconnects

## Problem Statement

Sarflog's Ledger Foundation ticket pack is marked complete, but the audit found several user-facing money paths that do not yet enforce the same chronology and ledger rules as the main expense and income flows.

From the user's perspective, this creates inconsistent trust boundaries:

- The same wallet date can be rejected in one flow and accepted in another.
- A session expense can become posted money through a weaker date gate than a normal expense.
- Expected Inflow receipts can post money into a wallet before that wallet's tracking start.
- Debt and Payment Plan wallet movements can bypass the wallet epoch rule in some obligation paths.
- When the backend does reject a pre-epoch date, the frontend may lose the human explanation and show only an internal error code.

This weakens the Epicspart2 Ledger Foundation promise: posted money should obey wallet epochs, user-local dates, closed-period guardrails, and clear correction guidance no matter which UI path records it.

## Solution

Wire the Ledger Foundation rules through every posted-money path discovered in the UI1 audit.

From the user's perspective:

- Any wallet-touching money movement refuses dates before the touched wallet's tracking start.
- Session expenses follow the same normal logging and closed-period rules as normal expenses.
- Expected Inflow receipts are allowed only when the receipt date is valid for every destination wallet.
- Debt and Payment Plan money movements follow the same wallet epoch rule as ordinary expenses, income, transfers, and reconciliation.
- Error messages clearly explain what happened, including which wallet caused the boundary failure and what date is allowed.

From the engineering perspective, the existing ledger foundation remains the source of truth. The work is wiring and guardrail coverage, not a new ledger model.

## User Stories

1. As a user, I want every wallet-touching receipt to respect the wallet's tracking start, so that old money cannot sneak into a new wallet.
2. As a user, I want Expected Inflow receipts to reject pre-epoch wallet dates, so that planned income cannot become invalid posted money.
3. As a user, I want Expected Inflow receipt errors to name the affected wallet, so that I know which destination caused the problem.
4. As a user, I want session expenses to follow the same date rules as normal expenses, so that receipt scanning does not bypass money-history rules.
5. As a user, I want session expenses in closed months to be rejected through the same current-correction guidance, so that old reports stay stable.
6. As a user, I want session expenses to reject wallet allocations before the wallet tracking start, so that multi-wallet receipt sessions stay honest.
7. As a user, I want debt payments from wallets to respect wallet epochs, so that obligations do not rewrite pre-onboarding wallet history.
8. As a user, I want debt initial wallet movements to respect wallet epochs, so that borrowed or lent money cannot be posted before a wallet exists.
9. As a user, I want payment-plan setup money to respect wallet epochs, so that loan or installment setup cannot corrupt wallet history.
10. As a user, I want payment-plan payments to respect wallet epochs, so that installment activity uses the same chronology rules as expenses.
11. As a user, I want obligation-related errors to use user-facing language, so that I understand whether to change the date, wallet, or use a correction path.
12. As a user, I want valid same-day wallet activity to keep working, so that I can create a wallet and immediately record current money.
13. As a user, I want multi-wallet receipts and payments to validate every touched wallet, so that one invalid allocation cannot slip through.
14. As a user, I want valid current-month activity to continue working after these guardrails, so that normal logging remains fast.
15. As a user, I want grace-window behavior to stay consistent, so that recent cleanup is possible when the product rule allows it.
16. As a user, I want future-date rejection and pre-epoch rejection to remain distinct, so that I know which rule I hit.
17. As a user, I want closed-period rejection and wallet-epoch rejection to remain distinct, so that I can choose the right correction path.
18. As a user, I want cancelled or reversed money to remain mathematically correct after these checks, so that validation changes do not break ledger reversal behavior.
19. As a user, I want wallet balances to remain accurate after accepted Expected Inflow, session, debt, and payment-plan activity, so that the displayed balance remains trustworthy.
20. As a developer, I want every wallet-touching command to use the existing wallet epoch seam, so that chronology rules stay centralized.
21. As a developer, I want session finalization to use the same normal logging date rule as expense creation, so that receipt-session behavior does not drift.
22. As a developer, I want obligation wallet movements to validate before posting financial events or adjusting balances, so that rejected commands leave no partial history.
23. As a developer, I want Expected Inflow realization to validate destination wallets before posting any events, so that one failed allocation cannot leave partial receipt history.
24. As a developer, I want frontend error handling to preserve structured backend details, so that domain errors can become useful product copy.
25. As a developer, I want regression tests at route/service seams, so that internal refactors do not weaken ledger foundation behavior.
26. As a developer, I want guardrail tests to cover accepted and rejected cases, so that same-day and valid current-period behavior remains protected.

## Implementation Decisions

- Keep the existing Ledger Foundation domain seam as canonical for wallet epoch validation.
- Apply wallet epoch validation before any wallet balance adjustment, Financial Event posting, or domain ledger row creation in the audited wallet-touching paths.
- Treat Expected Inflow creation as planning intent when it does not touch a wallet. Validate wallet epochs when an Expected Inflow is realized into posted money.
- Validate every destination wallet allocation in Expected Inflow realization against the realization date.
- Keep Expected Inflow write-offs and reschedules out of wallet epoch validation unless they create wallet-touching posted money.
- Session draft creation and editing may remain planning state, but session finalization creates posted expense money and must use the same normal logging date rule as normal expense creation.
- Session finalization must validate every wallet allocation against the finalized expense date before posting.
- Debt and Payment Plan flows that move wallet money must validate the transaction date against every touched wallet.
- Obligation flows that are planning-only or metadata-only should not be forced into the global Financial Event ledger.
- Rejected commands must fail before any partial wallet balance, Financial Event, domain ledger, or allocation side effect is committed.
- Use the effective user timezone for "today" and closed-period decisions.
- Preserve existing same-day epoch behavior: activity on the wallet creation date remains allowed.
- Preserve existing closed-period behavior: current month remains open, the grace window remains allowed, and sealed months route users toward current correction.
- Preserve existing reversal and correction semantics. This work does not change void, reversal, or correction repost behavior except where validations prevent invalid posting.
- Frontend error handling should preserve structured backend details and render a clear wallet epoch message when the backend supplies wallet name, requested date, and tracking start date.
- The frontend should continue sending the browser timezone automatically.
- Frontend date inputs should continue using timezone-aware local date helpers for default and max values.
- Error translation should not expose internal codes when structured user-facing detail is available.
- No broad schema redesign is required unless a specific flow lacks enough request data to validate the touched wallets before posting.

## Testing Decisions

- Test behavior at route or service seams where users trigger posted money, not private helper internals.
- Tests should prove rejected pre-epoch commands create no Financial Event, Wallet Ledger, Entity Ledger, domain ledger, payment allocation, or wallet balance side effect.
- Expected Inflow tests should cover a valid same-day receipt, a rejected receipt before the destination wallet epoch, and multi-wallet receipt validation where one wallet is invalid.
- Session finalization tests should cover current-period success, closed-period rejection, pre-epoch wallet rejection, and preservation of existing future-date rejection.
- Debt tests should cover initial wallet movement and debt payment wallet movement before and on the wallet epoch.
- Payment Plan tests should cover setup or disbursement wallet movement and payment wallet movement before and on the wallet epoch.
- Frontend tests should cover structured wallet epoch error localization and should not rely on raw backend code strings in user-visible assertions.
- Projection tests should verify accepted flows still reconcile wallet balances from ledger history where the existing projection seam applies.
- Tests should use project timezone helpers rather than server-local date math.
- Tests should preserve the distinction between posted money, mutable metadata, planning intent, and drafts.

## Out of Scope

- Rewriting the full immutable ledger architecture.
- Building a new audit-history UI for voided and reversal Financial Events.
- Full database-level immutability constraints for every ledger table.
- Historical data migration for already-posted invalid legacy rows.
- Changing budget permission rules except where session finalization already uses them.
- Rebuilding Expected Inflow, Debt, or Payment Plan domain models.
- Changing the product rule for current month, grace window, or closed-period correction behavior.
- Replacing all direct wallet balance adjustments in the codebase if they are outside the audited posted-money paths.

## Further Notes

The audit found the Ledger Foundation core is mostly present: shared void/reversal behavior exists, frontend requests send the browser timezone, normal expense and income creation use user-local date helpers, and wallet projection verification has dedicated tests.

The remaining disconnects are wiring gaps. The implementation should make the existing foundation apply consistently to the UI paths that create posted money.
