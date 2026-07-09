# PRD 1: Deepen Expense Posting And Centralize Ledger Posting

Triage: ready-for-agent

## Problem Statement

Sarflog is a ledger-first, cash-aware spending-permission system. The backend already has an Expense Posting module and several ledger-aware money flows, but the rules for posting financial truth are still scattered across multiple routes and modules.

From the user's perspective, this creates risk in the most important part of the app: when they record spending, receive money, settle obligations, reverse mistakes, or finalize session drafts, Sarflog must save truth first, protect Wallet balances, respect Budget permission, preserve ledger history, and apply the user's local date consistently.

Today, similar posting behavior is repeated in separate flows. Normal expenses, session drafts, Payment Plans, Debt charges, expected inflow receipts, refunds, asset sales, wallet transfers, and reversals can each construct Financial Events, Wallet Ledger entries, and Entity Ledger entries directly. That makes the posting interface too wide: each caller must know too many invariants to avoid corrupting money truth.

This PRD covers the first codebase-improvement slice: deepen Expense Posting and introduce a central Financial Event Ledger module so money posting has higher locality and more leverage.

## Solution

Create a deeper backend posting architecture with two cooperating modules:

1. Expense Posting becomes the one high-level interface for expense-shaped financial truth.
2. Financial Event Ledger becomes the lower-level interface for constructing, linking, voiding, and reversing immutable money events.

The user-facing behavior should not change. Users should still be able to add expenses, finalize session drafts, confirm recurring expenses, pay Debt charges, record Payment Plan payments, receive expected inflows, record refunds, sell assets, transfer wallet funds, and reverse mistakes. The difference is that the backend will route these flows through fewer, deeper seams.

The goal is not a broad folder reshuffle. The goal is to make it structurally hard to bypass Wallet Epoch, Budget permission, immutable ledger rules, title preservation, wallet-balance rules, and user-local date rules.

## User Stories

1. As a Sarflog user, I want a normal expense to be posted reliably, so that my Wallet, Budget, and ledger history stay in sync.
2. As a Sarflog user, I want a session draft to finalize through the same posting rules as a normal expense, so that receipt-based spending cannot bypass Budget permission or wallet protection.
3. As a Sarflog user, I want recurring expense confirmation to use the same posting rules as manual expense entry, so that repeated expenses behave predictably.
4. As a Sarflog user, I want Payment Plan payments that create expenses to use the same Budget permission rules as normal expenses, so that hidden charges or scheduled payments cannot silently corrupt my monthly plan.
5. As a Sarflog user, I want Debt charge payments to use the same expense posting rules as normal category spending, so that charges hit the right Budget and ledger history.
6. As a Sarflog user, I want Debt principal settlements to preserve the right obligation ledger links, so that my Debt balance and Wallet balance agree.
7. As a Sarflog user, I want expected inflow receipts to post money into Wallets consistently, so that received money becomes real cash without duplicate ledger logic.
8. As a Sarflog user, I want refunds to preserve the original expense title and category effect, so that refund duality remains clear in Money In and Expenses.
9. As a Sarflog user, I want asset sales to post income without robotic title pollution, so that my General Ledger remains human-readable.
10. As a Sarflog user, I want wallet transfers to be ledgered consistently, so that money movement between Wallets is auditable.
11. As a Sarflog user, I want voiding a posted expense to create a reversal instead of erasing history, so that my ledger remains trustworthy.
12. As a Sarflog user, I want reversing a linked event to update Wallet balances and related ledgers consistently, so that fixing mistakes does not create hidden drift.
13. As a Sarflog user, I want Budget-required errors to remain structured, so that the frontend Budget Interceptor can repair missing Budget permission in context.
14. As a Sarflog user, I want project-linked expenses to respect Overlay Project and frozen Isolated Project rules, so that project spending does not break core Budget math.
15. As a Sarflog user, I want protected Goal money to remain protected during outflows, so that spending cannot accidentally consume locked savings.
16. As a Sarflog user, I want expense dates to be interpreted in my timezone, so that "today" means my today.
17. As a Sarflog user, I want Wallet Epoch rules to be enforced consistently, so that transactions before a wallet's sealed starting snapshot cannot double-count money.
18. As a Sarflog user, I want existing reports and analytics to keep working after this refactor, so that architecture improvements do not change financial meaning.
19. As a Sarflog user, I want old posted ledger history to remain intact, so that refactoring does not rewrite my past.
20. As a developer, I want one deep Expense Posting interface, so that new expense-shaped flows do not copy wallet, Budget, project, and ledger code.
21. As a developer, I want one Financial Event Ledger interface, so that posting, voiding, reversing, and linking Financial Events are testable at one seam.
22. As a developer, I want routes to stop constructing money ledger rows directly, so that HTTP code does not own financial truth.
23. As a developer, I want Payment Plan and Debt flows to delegate money event construction, so that obligation modules own obligation math but not low-level ledger mechanics.
24. As a developer, I want expected inflow source adapters to delegate posting mechanics, so that Expected Inflows own Promise and Schedule logic without reimplementing ledger posting.
25. As a developer, I want tests to assert user-visible financial behavior, so that implementation details can change without brittle test churn.

## Implementation Decisions

- Deepen Expense Posting before reorganizing folders.
- Treat Expense Posting as the highest seam for expense-shaped Financial Events.
- Treat Financial Event Ledger as the lower seam for immutable event construction, Wallet Ledger entries, Entity Ledger entries, event links, voids, and reversals.
- Keep routes focused on HTTP concerns: authentication, request parsing, response shaping, and rate-limit headers.
- Keep domain modules responsible for product decisions: Budget permission, Wallet protection, project eligibility, obligation math, expected inflow lifecycle, and recurring schedule intent.
- Do not make Payment Plans and Debts the same domain concept. Debt remains an open-ended obligation. Payment Plan remains a scheduled obligation. Only their money posting mechanics should converge behind shared ledger seams.
- Expense Posting must support single-line expenses and multi-line session finalization.
- Expense Posting must support caller-supplied wallet allocations.
- Expense Posting must support category, subcategory, Overlay Project, and legacy isolated project links without exposing those rules to every caller.
- Expense Posting must preserve structured Budget-required failures for the Global Budget Interceptor pattern.
- Expense Posting must continue validating Budget permission and project spending permission before money is posted.
- Expense Posting must continue validating Wallet goal protection for outflows unless a caller has already performed an equivalent domain-specific validation.
- Financial Event Ledger must support immutable append-only posting for Financial Events.
- Financial Event Ledger must support event status transitions for voiding without hard-deleting posted financial truth.
- Financial Event Ledger must support reversal Financial Events with counter-balancing Wallet Ledger and Entity Ledger entries.
- Financial Event Ledger must preserve strict title inheritance rules from the General Ledger naming decision.
- Financial Event Ledger must avoid server-local date defaults for user-facing money events. Money modules must receive an explicit user-local effective date.
- Technical timestamps such as created, updated, voided, archived, token expiry, and security events may continue using timezone-aware UTC.
- Wallet balance adjustment should remain protected by the wallet rules module, but callers should not separately construct wallet legs after balance mutation.
- Existing direct event construction should be migrated incrementally from lowest-risk flows to highest-risk flows.
- The first migration target should be session draft finalization because it currently duplicates expense posting behavior and belongs naturally behind the Expense Posting seam.
- The second migration target should be Payment Plan expense posting because it repeats Budget permission and wallet allocation behavior.
- The third migration target should be direct income, refund, asset-sale, and transfer posting paths behind Financial Event Ledger adapters.
- The refactor should preserve existing route contracts unless tests reveal an existing inconsistency that must be fixed to uphold accepted ADRs.
- Schema changes are not expected for this PRD.
- Database migrations are not expected for this PRD.
- Existing ledger rows should not be rewritten.
- Existing ADRs remain authoritative, especially Wallet Epoch, strict logging and reconciliation, Global Budget Interceptor, Immutable Ledger Architecture, Global Ledger Naming, Debt dual path, Payment Plan engine, Expected Inflow two-layer architecture, and the Isolated Project freeze.

## Testing Decisions

- Tests should verify external financial behavior, not internal helper calls.
- The primary test seam for expense-shaped flows is the Expense Posting interface as exercised through existing route workflows.
- The primary test seam for low-level immutable money events is the Financial Event Ledger interface.
- Existing expense tests are prior art for posted expense creation, wallet debits, Budget links, immutable void/reversal behavior, split expenses, and session drafts.
- Existing Payment Plan tests are prior art for scheduled payment posting, charges, write-offs, reversals, and Budget-required failures.
- Existing Debt tests are prior art for Debt transaction creation, Debt Ledger entries, principal and charge splits, wallet effects, and reversals.
- Existing Expected Inflow tests are prior art for receipts, refunds, receivable payments, Promise cap rules, and source-specific posting.
- Add regression coverage proving session draft finalization produces the same Financial Event, Wallet Ledger, Entity Ledger, Budget, project, and Debt split behavior after moving through Expense Posting.
- Add regression coverage proving Payment Plan expense posting still raises structured Budget-required failures when a category has no Budget permission.
- Add regression coverage proving Payment Plan expense posting still writes the correct payment-plan links into the Entity Ledger.
- Add regression coverage proving Debt charge payments still post category expense impact and obligation ledger impact consistently.
- Add regression coverage proving refunds preserve the user-facing title rule and category contra-expense behavior.
- Add regression coverage proving voiding an expense appends a reversal and does not hard-delete posted financial truth.
- Add regression coverage proving wallet transfer behavior remains balanced across two Wallet Ledger entries.
- Add regression coverage proving user-local dates are explicit in money posting paths and do not fall back to server-local date defaults.
- Use timezone-aware test helpers when test data depends on "today".
- Keep route-level tests for user-visible behavior and add focused module tests only where the new seam has meaningful leverage.
- Avoid tests that assert private helper names, internal call order, or exact implementation decomposition.

## Out of Scope

- Frontend structure and organization.
- New user-facing features.
- New Budget behavior.
- New Debt behavior.
- New Payment Plan behavior.
- New Expected Inflow behavior.
- New Recurring Template or Recurring Occurrence behavior.
- Reopening the Isolated Project or Fund Project freeze.
- Rewriting historical ledger rows.
- Broad splitting of model and schema modules.
- Broad folder reshuffling without a deeper module seam.
- Changing route URLs or frontend request contracts.
- Changing authentication, rate limiting, or notification behavior.
- Changing Docker, deployment, or migration infrastructure.

## Further Notes

- This PRD intentionally combines the first two backend architecture candidates because Expense Posting should sit above Financial Event Ledger. Expense Posting owns expense-shaped product rules; Financial Event Ledger owns immutable money event mechanics.
- The first implementation issue should be small: route session draft finalization through the deepened Expense Posting seam while preserving behavior.
- The second implementation issue should migrate Payment Plan expense posting through the same seam.
- The Financial Event Ledger seam should be introduced conservatively. One adapter is hypothetical; two real migrated flows justify the seam.
- The deletion test should guide each extraction. If deleting a helper merely moves the same caller knowledge elsewhere, it is shallow. If deleting a module would scatter Budget, Wallet, ledger, date, and reversal rules across many callers, it is earning its depth.
- The expected end state is higher locality and leverage, not a prettier file tree.
