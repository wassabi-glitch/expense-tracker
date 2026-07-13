# Spec: UI1 Obligation Backend-Frontend Wiring

## Problem Statement

Epic 2 says the Debt and Payment Plan obligation architecture is implemented, but the current product surface is not fully wired end to end. The backend already exposes several truthful obligation contracts: derived state, schedule previews, component balances, append-only reversals, plan write-offs, archive metadata, and user-timezone urgency. The frontend still misses or bypasses some of those contracts, so users cannot reliably use the architecture that already exists.

From the user's perspective, this creates a confusing split: Sarflog knows the correct obligation facts, but the Obligations UI sometimes hides them, computes them locally, or falls back to legacy status/product assumptions.

## Solution

Wire the existing obligation backend contracts into the frontend so Debt and Payment Plan behavior is usable from the Obligations screen. The UI should stop treating backend-only functionality as done unless users can actually create, review, filter, archive, write off, reverse, and settle obligations through visible workflows.

The work should focus on the current Epic 2 contract from ADR 0026-0029:

- Debt uses derived lifecycle and time status, origin and counterparty language, principal and charge balances, component-aware payments, and append-only ledger actions.
- Payment Plan uses explicit schedule models, schedule preview, row settlement state, plan-level derived totals, archive metadata, first-class write-offs, and append-only reversals.
- Archive visibility must remain separate from lifecycle and urgency.
- User-facing date behavior must use the effective user timezone.

## User Stories

1. As an obligation user, I want the Payment Plan creation flow to preview the generated schedule before saving, so that I can confirm the plan matches the real agreement.
2. As an obligation user, I want flat-total plan rows to come from the backend preview, so that frontend rounding does not drift from backend accounting.
3. As an obligation user, I want to see the total principal, total charges, total to pay, final due date, and row list before creating a plan, so that I know what will be recorded.
4. As a borrower, I want bank loan, mortgage, and vehicle loan plans to support amortized schedules, so that interest and principal are represented truthfully.
5. As a borrower, I want to enter an annual interest rate for amortized plans, so that the generated rows match the loan structure.
6. As a borrower, I want amortized rows to appear grouped by installment, so that one real payment can still show its principal and charge parts.
7. As an obligation user, I want to create a manual contract schedule, so that Sarflog can match an exact provider or bank schedule.
8. As an obligation user, I want manual schedule rows to preserve my entered due dates and amounts, so that the app does not regenerate them into a different agreement.
9. As an obligation user, I want to switch between generated and manual schedule modes before saving, so that I can use the best model for the real contract.
10. As an obligation user, I want Payment Plan list cards to show derived open, closed, overdue, and on-track state, so that urgency is accurate.
11. As an obligation user, I want Payment Plan urgency to use my local timezone, so that a due date does not become overdue too early or too late.
12. As an obligation user, I want Payment Plan remaining principal and remaining charges to be visible, so that fees and original balance are not blended into one unclear number.
13. As an obligation user, I want row labels to distinguish unpaid, partial, paid, written off, and mixed settlement, so that waived money is not shown as paid money.
14. As an obligation user, I want to archive a Payment Plan without changing its balance or lifecycle, so that I can file it away without corrupting history.
15. As an obligation user, I want to restore an archived Payment Plan, so that a filed-away plan can return to the active view.
16. As an obligation user, I want Payment Plan filters to include active, archived, open, closed, and overdue views, so that I can find the right obligations quickly.
17. As an obligation user, I want to write off a custom amount across a whole Payment Plan, so that waived settlement discounts reduce the obligation without fake wallet movement.
18. As an obligation user, I want to write off a specific schedule row, so that a provider-waived row can be represented precisely.
19. As an obligation user, I want write-off UI copy to say forgiven or waived, so that I do not confuse it with a wallet payment.
20. As an obligation user, I want to undo the latest Payment Plan charge, so that accidental fees can be corrected through append-only history.
21. As an obligation user, I want to undo the latest Payment Plan payment, so that a mistaken payment entry can be reversed without deleting the original story.
22. As an obligation user, I want Payment Plan activity to show payments, charges, write-offs, and reversals distinctly, so that I can audit what happened.
23. As an obligation user, I want Debt creation to accept opening charges, so that fees or interest present on day one are not hidden inside principal.
24. As an obligation user, I want Debt creation to separate starting balance from wallet movement, so that borrowed cash, unpaid bills, and imported balances can be recorded truthfully.
25. As an obligation user, I want wallet movement during Debt creation to be allowed to differ from the starting Debt balance, so that upfront fees and unpaid-service flows are accurate.
26. As an obligation user, I want Debt payments to let me choose automatic, charges-first, principal-first, or custom allocation, so that the payment matches my agreement.
27. As an obligation user, I want custom Debt payment splits to validate against remaining principal and remaining charges, so that I cannot over-clear one component.
28. As an obligation user, I want Debt payment activity to show principal and charge effects separately, so that I can understand what the payment changed.
29. As an obligation user, I want Debt edit behavior to use derived lifecycle status instead of removed legacy status, so that open Debts can still be edited safely.
30. As an obligation user, I want Debt UI to avoid removed product-kind labels, so that standalone Debt stays separate from Payment Plan product language.
31. As an obligation user, I want archived Debt and archived Payment Plan behavior to feel consistent, so that filing away obligations is predictable.
32. As a developer, I want frontend API clients and hooks for every supported obligation action, so that UI components do not bypass backend contracts or duplicate accounting math.
33. As a developer, I want tests to prove backend responses and frontend workflows agree, so that future changes do not recreate these disconnects.

## Implementation Decisions

- Treat the existing Epic 2 obligation backend contract as the source of truth. Do not invent a second frontend accounting model.
- Keep Debt and Payment Plan separate. Debt remains an open-ended running-balance obligation. Payment Plan remains a scheduled obligation with product language and schedule rows.
- Use schedule preview as the creation review source for Payment Plans. The frontend should display backend preview rows and submit creation payloads that match the reviewed schedule.
- Keep flat-total, amortized loan, and manual contract schedule modes visible in creation. The UI can progressively disclose fields by plan type and schedule mode.
- Payment Plan creation should not rely on local frontend row-generation math except for lightweight provisional hints before preview. Saved rows must come from backend schedule generation or validated manual rows.
- Payment Plan list and detail responses should include user-timezone-derived plan and row urgency whenever those responses are used for user-facing views.
- Payment Plan archive and restore should use archive metadata, not stored lifecycle status, and should not mutate rows, allocations, ledger entries, or balances.
- Payment Plan list filtering should support archive visibility separately from open, closed, and overdue state.
- Payment Plan write-offs should expose row-level and plan-level flows. Plan-level write-off should allocate by the backend waterfall contract.
- Payment Plan charge reversal should be exposed as an undo action in the activity or details surface, following latest-first append-only behavior.
- Debt creation should expose original principal, opening charges, and wallet movement as separate concepts.
- Debt payment should expose allocation mode. Automatic defaults to the backend rule, while charges-first, principal-first, and custom modes send explicit allocation intent.
- Debt edit should use derived lifecycle status and remaining balance facts. It should not depend on a removed legacy status field.
- The frontend should remove dead assumptions about Payment Plan `ARCHIVED` status and standalone Debt `ACTIVE` status where the public contract now uses archive metadata and derived lifecycle.
- Error handling should localize existing backend error codes where possible rather than translating them into new frontend-only rules.

## Testing Decisions

- Use route-level backend tests for API contract behavior: schedule preview, archive visibility, derived plan time status, plan-level write-off, charge reversal, Debt opening charges, and Debt component payment allocation.
- Use frontend API client and hook tests to prove every exposed backend action has a callable frontend seam.
- Use component workflow tests around the Obligations UI where the user-facing behavior matters: create preview, archive and restore, write off, reverse, and component-aware Debt payment.
- Test external behavior rather than internal implementation details. Good tests should assert visible labels, submitted payloads, API calls, response handling, and cache invalidation effects.
- Reuse existing obligation route tests, frontend cache invalidation tests, date helper tests, and obligation schema tests as prior art.
- Timezone-sensitive tests should use explicit timezone headers or browser timezone helpers. User-facing due date and overdue logic must not use naive local date math.
- Regression tests should prove standalone Debt product-kind labels do not return and Payment Plan row settlement labels do not collapse written-off money into paid money.

## Out of Scope

- Rewriting the obligation domain model.
- Changing the immutable ledger architecture.
- Adding new financial products beyond the existing Debt and Payment Plan taxonomy.
- Reworking wallet accounting, budget interception, or expected inflow architecture except where existing obligation actions already touch them.
- Migrating old production data unless a specific wiring fix requires a small compatibility migration.
- Replacing the entire Obligations page design.

## Further Notes

This spec comes from a frontend-backend disconnect audit of the Epic 2 obligation architecture. The main pattern is not missing backend capability; it is missing product wiring. The safest implementation path is to work vertically through one user-visible obligation workflow at a time, keeping backend contracts and frontend controls in lockstep.
