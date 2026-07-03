# 0019. Overlay Project Deletion Resolution UX

Date: 2026-07-03

## Status

Accepted

## Context

Epic 5 Issue 8 added ledger-safe deletion and resolution paths for overlay projects. The first implementation protected financial history, but product review surfaced three important UX and state-semantics problems:

1. **Archived projects can still be archived again.** The backend resolution path and archive endpoint currently set `status = ARCHIVED` without first checking whether the project is already archived. The database result is harmless, but the product behavior is confusing because the UI presents a meaningful action that has already happened.
2. **Deletion decisions need concrete expense context.** The deletion resolution modal currently shows only linked expense count and total amount. For high-consequence actions such as detaching expenses or deleting linked expenses, users need to see which expenses are affected.
3. **UI copy exposes implementation language.** Terms such as "Void", "Cascade Void", and "reversal ledger entries" correctly describe the backend's immutable ledger mechanics, but they are not user-facing budgeting language. Users are trying to decide whether to hide a project, detach expenses, or delete linked expenses from their working budget view.

This ADR clarifies how overlay project deletion should behave at the product boundary while preserving ADR-0011 immutable ledger architecture internally.

## Decision

### 1. Archived Project Actions Must Be State-Aware

Archived overlay projects must not present "Archive" as an available resolution action.

- Backend archive endpoints should reject repeated archive requests with a stable error such as `projects.already_archived`, or explicitly treat the operation as idempotent and return a clear unchanged response.
- UI controls must hide or disable archive actions for projects already in `ARCHIVED` status.
- Archived project cards should expose only actions that still make product sense, such as restore/reopen where allowed, detach-and-delete, or delete-linked-expenses-and-delete when appropriate.

### 2. Deletion Preview Must Show Affected Expenses

The overlay project deletion preview should include concrete linked expense rows in addition to aggregate count and total.

Minimum useful fields:

- expense id
- title
- date
- amount
- category
- subcategory name when available

The modal should show a compact list of affected expenses before the user chooses Detach or Delete. If the list is large, the UI may show the first reasonable number of rows plus a "View all linked expenses" path.

### 3. UI Must Use User Language, Not Ledger Language

The frontend should describe user outcomes rather than internal ledger implementation.

Preferred user-facing language:

- "Archive project"
- "Detach expenses"
- "Delete linked expenses and project"
- "These expenses will no longer count in your budgets or wallet balances."
- "Accounting history is preserved for accuracy."

Avoid as primary UI copy:

- "Void"
- "Cascade void"
- "Reversal"
- "Ledger entries"

The backend, tests, and internal documentation may continue using precise ledger terms such as void, reversal, and immutable ledger, because those terms describe the implementation required by ADR-0011.

## Consequences

- The next overlay deletion polish pass should update backend validation, frontend copy, and modal layout together.
- Tests should cover already-archived project behavior, expense-list preview payloads, and user-facing action labels.
- API contracts may need to expand `ProjectDeletionPreviewOut` with a list of linked expenses.
- The product remains ledger-safe internally while becoming clearer and less intimidating to users.

