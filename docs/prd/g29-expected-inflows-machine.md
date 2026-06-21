# PRD: G29 - Expected Inflows Machine

Status: Implemented contract - focused Docker regression rerun pending after final compatibility hardening

This PRD is the current Expected Inflows contract. It consolidates the useful ideas from the earlier planning, lifecycle, universal-inflow, budget-backing, and Epic 2 documents. Where those documents conflict, this contract takes precedence for G29.

## Implemented Contract

- One `expected_inflow_promises` row represents the user's original promise and original amount.
- One or more dated `expected_incomes` rows represent the promise's schedule. The legacy table name remains temporarily, but its role is now schedule persistence.
- Receipts and write-offs allocate to schedule rows. Promise totals and lifecycle are derived from those auditable facts.
- A promise remains `EXPECTED` or `PARTIALLY_RECEIVED` while any active scheduled amount remains. It becomes `RESOLVED` only when its original expected amount has been received, `WRITTEN_OFF` when a terminal shortfall exists, or `CANCELLED` when a zero-receipt promise is explicitly cancelled.
- Rescheduling supersedes only the selected schedule row and creates linked replacements. It does not close the overall promise, move wallet money, or automatically merge sibling schedules.
- Partial rescheduling is explicit: the moved amount creates replacement schedules and any unmoved amount is retained as a replacement on the original date.
- Parent-level receipt can satisfy one or more sibling schedules in one wallet event. Wallet allocations equal the actual receipt; schedule allocations equal the expected portion satisfied. An overpayment may therefore post more actual wallet value than the outstanding expected amount.
- Partial write-off is an amount fact, not a separate lifecycle status. The UI derives a `Partially written off` label while outstanding money remains.
- Amount, date, and note are editable only while the promise is pristine. Title remains editable afterward. Source identity, received totals, event links, and lifecycle cannot be patched directly.
- The canonical UI is `/money-in/expected-inflow`, with promise details at `/money-in/expected-inflow/:id`. Budgets links to this flow and no longer owns a duplicate form.

## Problem Statement

Sarflog currently has a narrow Expected Income feature that lets users create monthly planning rows for earned income. The backend also supports expectations linked to receivable debts, while the frontend largely understands only earned income sources. The frontend can manually change an expectation to `RECEIVED`, `MISSED`, or `CANCELLED`, but that status change is not a complete realization workflow and can be disconnected from actual wallet, debt, refund, or asset ledger truth.

The product direction is broader than earned income. Users may reasonably expect salary, freelance income, debt repayments, debt-related charges, expense refunds, asset-sale proceeds, or other incoming value. These inflows do not share one accounting treatment. A debt payment may contain principal and charges and may produce more than one financial event. A refund must remain linked to the original expense and may repair budget spending. An asset sale is not earned income. Borrowed cash is incoming wallet value but is not wealth and must not create false budget backing.

Earlier requirements attempted to solve these concerns by adding a generic realization modal, one linked transaction, automatic record splitting when dates move between months, and additional foreign keys for refunds and assets. That approach is incomplete. It conflates planning, scheduling, accounting classification, actual wallet movement, and source-specific domain behavior.

The Expected Inflows machine uses one model from database persistence through domain services, public APIs, budget backing, and frontend workflows. The model remains faithful to Sarflog's reality-first permission-budgeting philosophy:

- Wallets and ledgers record reality.
- Expected inflows record planning assumptions.
- Budgets are monthly spending permission.
- Only valid active expectations may support plan backing.
- Borrowing capacity and borrowed money must not be presented as wealth.
- Actual accounting behavior remains owned by the relevant income, debt, refund, asset, and wallet domains.

## Solution

Build an Expected Inflows machine that represents explicit, dated expectations of future incoming wallet value without pretending that every inflow is earned income or that every inflow has the same accounting route.

The expected-inflow layer will own planning facts: expected amount, source kind and source reference, expected date and planning period, lifecycle, active remaining amount, rescheduling lineage, and audit history. It will not independently classify or post actual financial events.

When money arrives, a realization workflow will delegate to the existing domain that owns the source:

- Earned income delegates to income posting.
- Receivable repayment delegates to debt payment and reconciliation.
- Refund delegates to the expense-refund workflow.
- Asset-sale proceeds delegate to asset liquidation.
- Other future inflow kinds require an explicit domain policy before being enabled.

The result of that delegated posting is linked back to the expectation through realization and allocation records. This relationship must support the real cardinalities discovered in the codebase: one actual realization can affect one or more expected rows, and one delegated posting can produce one or more financial events. The first frontend release may intentionally expose a narrower interaction, but the database must not encode a false one-expectation-to-one-event rule.

The canonical frontend home will be the Money In workspace under an Expected Inflows view. The Budgets workspace may provide a shortcut into the same creation flow, but it will not maintain a second contradictory expected-inflow form. The workspace will separate active expectations from history and expose explicit actions for realization, rescheduling, cancellation, write-off, and permitted corrections.

The decisions in this document are now the implementation baseline. Remaining follow-ups are listed in Further Notes and do not change the core promise/schedule contract.

## User Stories

1. As a budget user, I want Expected Inflows clearly separated from actual Money In, so that I do not mistake planned money for cash already in my wallets.
2. As a budget user, I want the product to use the term Expected Inflow rather than Expected Income, so that debt repayments, refunds, and asset-sale proceeds are not mislabeled as earned income.
3. As a budget user, I want every expectation to identify where the future value is expected to come from, so that the plan remains explainable.
4. As a budget user, I want creating an expectation to be an explicit decision, so that uncertain debts and possible refunds do not automatically inflate my plan.
5. As a budget user, I want the system to show whether an expectation counts toward plan backing, so that I understand why it does or does not support my monthly budget.
6. As a budget user, I want borrowed money distinguished from owned or returned value, so that loans do not appear as wealth.
7. As a budget user, I want to create an expected earned-income row from an active income source, so that salary or freelance income can support planning.
8. As a budget user, I want to create an explicit expected payment from an active receivable debt, so that only reliable debt repayments enter my plan.
9. As a budget user, I want receivable debts excluded from expected backing until I create an expectation, so that uncertain counterparties do not create fake budget room.
10. As a budget user, I want to plan an expected refund against the original expense when that behavior is enabled, so that the future refund retains its accounting context.
11. As a budget user, I want to plan expected asset-sale proceeds against the relevant asset when that behavior is enabled, so that a sale is not recorded as ordinary earned income.
12. As a budget user, I want source-specific creation steps instead of one form containing unrelated foreign-key selectors, so that adding an expectation remains understandable.
13. As a budget user, I want to enter an expected amount, expected date, and optional note, so that the planned promise has enough context.
14. As a budget user, I want the system to validate that the selected source belongs to me and is eligible for an expectation, so that cross-user or invalid links cannot be created.
15. As a budget user, I want an active expectation to show expected, received, and remaining amounts separately, so that partial fulfillment is understandable.
16. As a budget user, I want an untouched expectation to be `EXPECTED`, so that its complete eligible amount remains visibly pending.
17. As a budget user, I want an expectation with some but not all value realized to be `PARTIALLY_RECEIVED`, so that the unpaid remainder stays visible.
18. As a budget user, I want a fully satisfied expectation to become `RESOLVED`, so that completed plans move out of the active workspace.
19. As a budget user, I want an expectation that will produce no money to become `CANCELLED`, so that it stops supporting the plan without being deleted.
20. As a budget user, I want a terminal record to explain whether it was fully received, cancelled, written off, or rescheduled, so that history remains meaningful.
21. As a budget user, I want overdue expectations to show a warning without silently changing lifecycle state, so that lateness does not invent a business decision.
22. As a budget user, I want stale expectations never to roll into another month automatically, so that the system does not manufacture future promises.
23. As a budget user, I want only active eligible remaining amounts to contribute to plan backing, so that completed, cancelled, written-off, or rescheduled amounts do not remain trusted.
24. As a budget user, I want receiving money to ask for the actual received amount and date, so that expected and actual values remain distinct.
25. As a budget user, I want a realization to support one or more destination wallets, so that split deposits match reality.
26. As a budget user, I want destination-wallet allocations to equal the actual incoming wallet amount, so that wallet balances cannot diverge from the recorded realization.
27. As a budget user, I want early receipts accepted against a later expectation, so that money received before its expected date can be recorded honestly.
28. As a budget user, I want late receipts accepted without rewriting the original expected date, so that planned and actual timing remain comparable.
29. As a budget user, I want a partial receipt to reduce only the remaining expected amount, so that the unpaid balance continues to support planning only when still valid.
30. As a budget user, I want an earned-income realization posted through the income domain, so that income sources and income reporting remain correct.
31. As a budget user, I want a receivable realization posted through the debt domain, so that principal, charges, debt balance, and debt reconciliation remain correct.
32. As a budget user, I want debt principal distinguished from debt-related income or charges, so that returned assets are not mislabeled as earned income.
33. As a budget user, I want an expected refund realized through the refund domain, so that the original expense and budget effect remain linked.
34. As a budget user, I want expected asset-sale proceeds realized through the asset domain, so that the asset lifecycle and sale classification remain correct.
35. As a budget user, I want one actual incoming payment to be recorded only once in wallet reality, so that allocating it to expectations cannot duplicate cash.
36. As a budget user, I want actual posting and expected-inflow updates to succeed or fail together, so that planning history cannot claim money arrived when ledger posting failed.
37. As a budget user, I want to explicitly reschedule an outstanding expectation, so that changing a date does not trigger hidden record creation.
38. As a budget user, I want to divide an outstanding amount across multiple future dates, so that revised payer promises can be represented accurately.
39. As a budget user, I want reschedule allocations to account for the complete outstanding amount, so that no unexplained remainder disappears.
40. As a budget user, I want to include the current period as a reschedule destination when some amount remains expected there, so that the complete revised schedule is explicit.
41. As a budget user, I want the original expectation preserved after rescheduling, so that the system retains what I originally expected and what was already received.
42. As a budget user, I want rescheduled child rows linked to their origin, so that I can follow the promise through later revisions.
43. As a budget user, I want separately created future schedule rows kept distinct even when they land in the same month, so that lineage and notes are not destroyed by automatic merging.
44. As a budget user, I want the UI to aggregate a month's expected total without physically merging its rows, so that planning remains scannable and auditable.
45. As a budget user, I want same-period date corrections handled separately from cross-period rescheduling, so that simple corrections do not cause surprising lifecycle effects.
46. As a budget user, I want normal edits constrained after receipts or rescheduling exist, so that historical planning facts cannot be rewritten casually.
47. As a budget user, I want deletion permitted only while an expectation has no realization or lineage history, so that linked truth cannot be orphaned.
48. As a budget user, I want write-off to close an unpaid remainder without pretending it was received, so that counterparty default remains visible.
49. As a budget user, I want reversal of actual money handled by the domain that posted it, so that wallet, debt, refund, and asset truth are repaired correctly.
50. As a budget user, I want lifecycle state recalculated after a valid reversal, so that Expected Inflows reflects repaired ledger truth.
51. As a Money In user, I want one canonical Expected Inflows workspace, so that I do not encounter contradictory forms on Money In and Budgets.
52. As a Money In user, I want Active and History views, so that open planning work is separated from completed audit history.
53. As a Money In user, I want each row to show source kind, source label, expected date, expected amount, realized amount, remaining amount, lifecycle, and backing effect, so that I can understand it without opening the record.
54. As a Money In user, I want source-specific realization actions, so that salary, debt repayment, refund, and asset sale do not use misleading generic forms.
55. As a budget user, I want the Budgets page to open the canonical Add Expected flow with the selected month prefilled, so that budget repair remains convenient without creating a second implementation.
56. As a maintainer, I want Expected Inflows to delegate accounting behavior to existing domain services, so that it does not become a competing ledger engine.
57. As a maintainer, I want realization capable of linking to more than one financial event, so that debt principal and charge postings can be represented honestly.
58. As a maintainer, I want financial events capable of satisfying expectation allocations without a singular linked-transaction column, so that the database does not encode false cardinality.
59. As a maintainer, I want stored statuses and totals protected from arbitrary client updates, so that lifecycle follows domain commands and verified math.
60. As a maintainer, I want concurrent receipt and reschedule operations serialized, so that the same outstanding amount cannot be realized or rescheduled twice.
61. As a maintainer, I want idempotent realization commands, so that retries do not duplicate wallet or debt effects.
62. As a tester, I want public API and end-to-end tests to assert observable financial behavior, so that refactors can change internals without weakening correctness.
63. As a future timeline user, I want active expectations exposed as dated timeline items, so that expected inflows can participate in later cash-flow simulation.

## Implementation Decisions

- This is the approved G29 implementation contract. Later changes must preserve the promise/schedule/realization/write-off invariants or revise this PRD explicitly.
- Use `Expected Inflow` as the user-facing canonical term. `Expected Income` remains legacy terminology to be migrated.
- Preserve the reality/planning boundary. Expected-inflow records never alter wallet balances, debt balances, expense totals, assets, or financial events merely because they are created, edited, cancelled, or rescheduled.
- Keep expected inflows explicit. Receivable debts, refunds, assets, and possible earnings do not automatically create plan backing.
- Treat source kind and backing eligibility as separate concerns. Being incoming wallet value does not automatically make a source earned income or valid plan backing.
- The expected-inflow layer owns planning and scheduling facts. Actual accounting classification and posting remain delegated to the income, debt, refund, asset, wallet, and related domain services.
- The realization coordinator may orchestrate domain services and persist expectation links, but it must not duplicate their classification, principal/charge, reversal, budget-restoration, or reconciliation rules.
- Do not assume one realization produces one financial event. Existing debt behavior can split a payment between principal and charges and produce separate classified events.
- Do not retain a single `linked_transaction_id` as the long-term realization model.
- Keep multi-wallet realization as a first-class requirement. Wallet allocation amounts must equal the actual wallet amount recorded by the realization.
- Preserve expected amount separately from actual realization allocations. Received and remaining totals should be derived from valid allocations or maintained only as protected projections with reconciliation checks.
- Use a math-driven promise lifecycle with active values `EXPECTED` and `PARTIALLY_RECEIVED`, plus terminal values `RESOLVED`, `CANCELLED`, and `WRITTEN_OFF`.
- Keep `RESCHEDULED`/`SUPERSEDED` on schedule history, not as a terminal state of the overall promise.
- Treat overdue as a calculated presentation condition based on date, current lifecycle, and remaining amount. Do not introduce an overdue database lifecycle state merely because time passed.
- Replace automatic cross-month date splitting with an explicit rescheduling command.
- Rescheduling creates no wallet, entity, debt, refund, asset, or financial-event entries.
- A reschedule command replaces a selected schedule's complete outstanding amount. The UI accepts the amount to move and automatically retains any unmoved amount on the source date so conservation remains explicit.
- Preserve the promise's original expected amount and existing realizations when rescheduling. Supersede the source schedule row and link every replacement schedule to it.
- Do not automatically merge replacement rows that share a month or date. Aggregate them in read models when a monthly total is useful.
- Permit actual receipt dates before or after expected dates. Realization timing does not rewrite expected timing.
- Prevent generic clients from directly setting received totals, linked-event identifiers, or lifecycle statuses. Use explicit realization, cancel, write-off, reschedule, reversal-reconciliation, and approved edit commands.
- Make Money In -> Expected Inflows the canonical management workspace.
- Keep the Budgets expected-inflow entry point as a shortcut into the canonical creation flow with the budget month preselected.
- Replace the current single-source add form with progressive source-kind routing. Each source kind shows only its relevant selector and fields.
- Replace the current manual Received/Missed/Cancelled status buttons with domain actions. The final action set depends on lifecycle and source kind.
- Split the workspace into Active and History views. Active contains expectations with a valid remaining amount; History contains terminal expectations while retaining source, schedule, realization, and lineage evidence.
- Continue using the month-summary public contract as the highest seam for observing backing effects.
- Use the Money In Expected Inflows workspace as the highest frontend seam for creation, lifecycle, realization, rescheduling, and history behavior.
- Use the existing domain posting seams as the highest accounting seams for earned income, debt payments, refunds, and asset sales.
- Introduce a dedicated expected-inflow lifecycle API rather than expanding a generic patch endpoint with hidden multi-record side effects.
- Persistence boundaries are `expected_inflow_promises`, legacy-named `expected_incomes` schedule rows, `expected_inflow_realizations`, realization-to-schedule allocations, realization-to-financial-event links, and `expected_inflow_write_offs`.
- `expected_inflow_promises` contains planning identity, owner, source kind/reference, title, original amount, aggregate lifecycle, note, and timestamps. Schedule rows contain dated amounts, synchronized budget year/month, lifecycle/close metadata, and rescheduling lineage.
- A realization record should represent one user-observed incoming-money action and retain its actual date and amount independently of expected schedule rows.
- A realization allocation should state how much of that actual action satisfies a particular expected row.
- A realization-event link should permit a delegated domain posting to return one or more financial events without forcing a polymorphic accounting implementation into the expected-inflow table.
- Enforce ownership, positive amounts, source eligibility, allocation totals, lifecycle compatibility, planning horizon, and source-reference integrity at the backend boundary. Add database constraints where the database can express the invariant reliably.
- Lock affected expectation rows in a deterministic order during realization and rescheduling. Commit domain posting, realization links, lifecycle recalculation, and backing-visible changes atomically.
- Design migration from the legacy expected-income table only after the target schema is approved. Do not create a permanent duplicate model without a migration and compatibility plan.
- Preserve legacy data and existing G4 behavior during migration, including explicit receivable expectations and month-summary visibility, until equivalent behavior is proven through the new public contract.

## Testing Decisions

- Prefer tests of externally observable behavior over assertions about helper functions or ORM implementation details.
- Use the Money In Expected Inflows workspace as the end-to-end seam for user-visible creation, active/history navigation, source-specific actions, early and partial realization, rescheduling, cancellation, and validation errors.
- Use the expected-inflow lifecycle API as the integration seam for creation, approved editing, realization coordination, cancellation, write-off, rescheduling, and history queries.
- Use month summary as the integration seam for plan-backing effects. Tests must prove that only eligible active remaining amounts contribute and that partial realization reduces expected backing by the applied amount.
- Use existing income posting tests as prior art for earned-income wallet and entity-ledger behavior.
- Use existing debt-payment and debt-reconciliation tests as prior art for receivable principal, charges, wallet allocations, debt-ledger entries, classifications, and balance reconciliation.
- Use existing expense-refund tests as prior art for links to original expenses, partial refund limits, wallet restoration, and budget-spending repair.
- Use existing asset-liquidation tests as prior art for asset-sale proceeds and asset lifecycle changes.
- Test that creating, editing, cancelling, or rescheduling an expectation never creates actual wallet or financial-event effects.
- Test that realization creates or delegates actual posting exactly once and links every resulting event without duplicating wallet value.
- Test multi-wallet realization totals and reject missing, duplicate, inactive, foreign-owned, or mismatched wallet allocations.
- Test full, partial, early, late, under-, and over-realization policies once their decision gates are resolved.
- Test debt realizations containing principal only, charges only, and both principal and charges.
- Test that receivable principal is not falsely reported as earned income and that eligible charges retain their correct income classification.
- Test refund realization against original expense limits and budget effects.
- Test explicit rescheduling into one, two, and multiple dates, including keeping part of the outstanding amount in the current period.
- Test that reschedule allocation totals must equal the source outstanding amount and that the entire transaction rolls back on failure.
- Test that rescheduled rows preserve parent history and are not automatically merged.
- Test concurrent realization/reschedule attempts and idempotent command retries.
- Test lifecycle state after actual-event reversal once reversal semantics are approved.
- Test deletion and edit restrictions after realizations or rescheduling lineage exist.
- Test overdue presentation without database lifecycle mutation.
- Test the Budgets shortcut opens the canonical flow and produces the same result as creation from Money In.
- Preserve focused regression coverage for legacy expected-income creation, explicit debt-linked expectations, and month-summary behavior throughout migration.

## Out of Scope

- Cleanup or renaming of unrelated legacy tables outside the migration required for G29.
- Automatically creating expected inflows from every income source, debt, expense, refund possibility, asset, recurring item, or loan application.
- Automatically rolling expectations into later months because they became overdue.
- Treating credit limits, overdraft capacity, or borrowed funds as owned wealth.
- Reimplementing debt principal/charge classification, refund accounting, asset liquidation, or income posting inside the expected-inflow module.
- Full accounts-receivable invoicing, statements, collections, or aging reports.
- Tax reporting or legal classification of taxable income.
- Bank synchronization, bank-statement matching, or external payment-provider reconciliation.
- Automatic matching of imported deposits to expected inflows.
- Foreign-exchange realization policy beyond the application's approved currency model.
- Recurring automatic generation of salary or other expected inflows.
- The complete future cash-flow simulator; this feature will expose reliable dated data for that later work.
- Legacy-table cleanup unrelated to the migration required for Expected Inflows.

## Further Notes

### Current Product Baseline

Money In now exposes separate Money In and Expected Inflows tabs. Expected Inflows uses the aggregate API and TanStack Query hooks for earned income, receivable repayments, refunds, and asset-sale expectations. The Budgets page links to the same creation flow. Legacy budget endpoints remain only as compatibility adapters and cannot directly mutate lifecycle or received truth.

### Reference Scenario: Earned Income With Rescheduling

The user expects 10m salary in June. They receive 6m into one or more wallets. The promise becomes partially received with 4m remaining. The employer then promises 1m in July and 3m in August. The user reschedules the June schedule into those two allocations. The June schedule becomes `SUPERSEDED`; the overall 10m promise remains `PARTIALLY_RECEIVED` and exposes the July/August children. It becomes `RESOLVED` only after the remaining 4m is received. No wallet money moves during rescheduling.

### Reference Scenario: Receivable Principal And Charges

A counterparty owes principal plus a posted charge. One payment may be split by the debt domain between principal and charge balances. Principal may be classified as returned value or debt settlement, while a receivable charge may be classified as income. The expected-inflow realization links to the complete delegated result and does not choose either classification itself.

### Reference Scenario: Early Receipt

An August expectation is paid in July. The actual wallet and financial-event date is in July. The August expectation is satisfied or partially satisfied according to the allocation. The system does not rewrite the August expected date merely because reality happened early.

### Reference Scenario: Expected Refund

The user expects a refund linked to a prior expense. When it arrives, the refund domain creates a refund event linked to that expense and applies the approved wallet and budget-spending effects. The expectation records satisfaction by that result. Whether the pending refund contributes to generic plan backing before realization is a separate decision gate.

### Conflicts With Earlier Documents

- A generic date edit must not automatically split or carry forward an expectation.
- The original expected amount must not be lowered to the received amount merely to make status math convenient.
- A single linked transaction is insufficient for debt payments that produce principal and charge events.
- Adding `asset_id` or `refund_event_id` alone does not define source-specific realization behavior.
- A universal frontend wizard can route actions but must not become a universal accounting implementation.
- `MISSED` as a stored lifecycle conflicts with the newer proposal to use overdue presentation plus explicit cancellation, write-off, or rescheduling.
- Existing `ready-for-agent` labels on older Expected Inflows documents do not mean this consolidated machine is ready to implement.

### Closed Decisions

1. G29 tracks explicit promises for earned income, receivable repayment, refunds, and asset sales. It does not automatically create expectations from possible sources.
2. Promise and dated schedule are separate entities. Schedule date, budget year, and budget month are one synchronized planning fact.
3. Pristine promises allow amount/date/note correction. After receipt, write-off, cancellation, or lineage exists, only title remains generally editable.
4. Rescheduling is an explicit command, replaces exactly one selected schedule's outstanding amount, allows multiple target dates, and rejects newly backdated targets. An already overdue retained portion may keep its original date.
5. Receipt is a promise-level command. It may satisfy multiple sibling schedules and deposit into multiple wallets atomically. Future schedules may be satisfied early.
6. Actual receipts may be below or above the expectation. Wallet legs equal the complete actual receipt; schedule allocations cannot exceed the outstanding expected amount.
7. Partial write-off is supported. Write-off amount is stored and audited; `Partially written off` is derived presentation while the promise remains open.
8. Cancellation is allowed only before receipt or write-off. Full receipt resolves; a terminal shortfall writes off; rescheduling does not resolve the promise.
9. Overdue is derived presentation, never an automatic lifecycle transition or carry-forward.
10. The promise/schedule/allocation/event-link migration is approved and applied as Alembic revision `8d9e0f1a2b34`.
11. The canonical lifecycle/read API and Money In workspace are approved. Legacy budget endpoints are compatibility adapters and cannot directly patch lifecycle truth.

### Remaining Follow-ups

1. Extract earned-income, refund, and asset-sale posting logic from routers/coordinators into dedicated domain services; receivable realization already delegates to the debt service.
2. Define bounced-payment and owning-domain event reversal orchestration beyond the existing expected-inflow reconciliation command.
3. Decide whether future non-backing source kinds such as borrowed money belong in the timeline.
4. Add dedicated concurrency/rollback, timeline-contract, and authenticated browser end-to-end coverage beyond the focused integration suite.
5. Rename the legacy `expected_incomes` schedule table only in the separate legacy cleanup effort.

### Publication Note

This local PRD records the implemented G29 contract. The final focused Docker rerun after compatibility hardening was blocked by the execution service usage limit on 2026-06-21 and must be rerun before release sign-off.
