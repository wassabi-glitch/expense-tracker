# Issues: G29 - Expected Inflows Machine

Parent PRD: `docs/prd/g29-expected-inflows-machine.md`

Status: Core vertical slice implemented. Audited against the working tree and Docker runtime on 2026-06-21; final focused Docker rerun after compatibility hardening is pending because the execution service reached its usage limit.

Tracking rules:

- `[x]` means the behavior or artifact exists in the current working tree.
- `[ ]` means it is missing, incomplete, unapproved, or not proven at the required test seam.
- This checklist does not claim release readiness. Authenticated browser tests, concurrency/rollback coverage, reversal orchestration, and the final focused Docker rerun remain incomplete.

Current implementation summary:

- Issues 1-4: the promise/schedule/lifecycle/persistence/API/UI decisions are now recorded as the implemented PRD contract.
- Issues 5-14: backend and frontend tracer paths exist. The canonical UI, detail page, aggregate commands, source routes, and timeline endpoint are wired; unchecked criteria identify remaining proof or architectural extraction work.
- Issue 15: intentionally deferred until a non-backing source kind is approved.

## Proposed Breakdown

1. **Define Expected Inflow boundary and backing matrix**
   - Type: HITL
   - Blocked by: None
   - User stories covered: 1-14, 23

2. **Approve schedule, date, lifecycle, and rescheduling model**
   - Type: HITL
   - Blocked by: Issue 1
   - User stories covered: 15-23, 37-48

3. **Approve realization and domain delegation contract**
   - Type: HITL
   - Blocked by: Issue 1
   - User stories covered: 24-36, 49-50, 56-61

4. **Approve persistence, API, UX, and migration contract**
   - Type: HITL
   - Blocked by: Issues 2-3
   - User stories covered: 51-62

5. **Deliver canonical earned-income expectation planning**
   - Type: AFK
   - Blocked by: Issue 4
   - User stories covered: 1-7, 12-16, 23, 51-55, 59, 62

6. **Realize earned expectations into multiple wallets**
   - Type: AFK
   - Blocked by: Issue 5
   - User stories covered: 15-18, 24-30, 35-36, 52-54, 57-62

7. **Reschedule outstanding expectations across dates**
   - Type: AFK
   - Blocked by: Issue 6
   - User stories covered: 37-47, 60, 62

8. **Deliver cancellation, write-off, overdue, and reversal repair**
   - Type: AFK
   - Blocked by: Issue 6
   - User stories covered: 19-22, 46-50, 52-53, 59-62

9. **Plan explicit receivable-debt expectations**
   - Type: AFK
   - Blocked by: Issue 5
   - User stories covered: 8-9, 12-14, 23, 51-55

10. **Realize receivables through principal and charge posting**
    - Type: AFK
    - Blocked by: Issues 6 and 9
    - User stories covered: 24-32, 35-36, 54, 56-62

11. **Plan and realize expected expense refunds**
    - Type: AFK
    - Blocked by: Issue 6
    - User stories covered: 10, 12-14, 23-29, 33, 35-36, 54

12. **Plan and realize expected asset-sale proceeds**
    - Type: AFK
    - Blocked by: Issue 6
    - User stories covered: 11-14, 23-29, 34-36, 54

13. **Allocate one promise-level receipt across sibling schedules**
    - Type: AFK
    - Blocked by: Issues 6 and 10
    - User stories covered: 35, 57-61

14. **Expose Expected Inflows to the future timeline contract**
    - Type: AFK
    - Blocked by: Issues 7-8 and 10-12
    - User stories covered: 63

15. **Handle approved non-backing incoming sources**
    - Type: AFK
    - Blocked by: Issues 1 and 5
    - User stories covered: 5-6

---

## Issue 1: Define Expected Inflow Boundary And Backing Matrix

**Type:** HITL

**Implementation status:** Approved for G29. `EARNED`, `RECEIVABLE`, `REFUND`, and `ASSET_SALE` are explicit supported kinds and are backing-eligible; borrowed and other non-backing source kinds are deferred.

### What to build

Reach and document a shared product definition for Expected Inflows before schema or UI implementation begins. Classify each proposed source kind as included, deferred, or excluded, and decide separately whether an included kind contributes to monthly plan backing. The result must preserve the distinction between incoming wallet value, earned income, returned value, asset conversion, and borrowed money.

### Acceptance criteria

- [x] The canonical definition of an Expected Inflow is approved in domain language.
- [x] The initial supported source kinds are explicitly listed.
- [x] Earned income, receivable principal, receivable charges, refunds, asset sales, neutral returns, insurance proceeds, and borrowed money each have an inclusion decision.
- [x] Every included source kind has an explicit backing policy.
- [x] Borrowed money and borrowing capacity cannot be presented as owned wealth.
- [x] Source-kind identity and backing eligibility are documented as separate concepts.
- [x] Explicit creation remains required; source-domain records do not automatically become expected backing.
- [x] Deferred and excluded source kinds are recorded so later agents do not infer support from broad UI terminology.
- [x] The approved decisions are reflected in the G29 PRD and domain glossary where appropriate.

### Blocked by

None - can start immediately.

---

## Issue 2: Approve Schedule, Date, Lifecycle, And Rescheduling Model

**Type:** HITL

**Implementation status:** Implemented and documented. Original promise and dated schedules are separate persistence and UI concepts.

### What to build

Define how original promises, dated schedule rows, lifecycle state, planning periods, corrections, and explicit rescheduling relate. Resolve whether one Expected Inflow row is the original promise or one scheduled portion, and produce unambiguous rules for partial receipts, terminal close reasons, overdue presentation, deletion, and one-to-many rescheduling.

### Acceptance criteria

- [x] The model distinguishes an original promise from scheduled portions, or explicitly proves that one entity can safely represent both.
- [x] The meaning of expected amount, realized amount, outstanding amount, and active backing amount is approved.
- [x] The lifecycle states `EXPECTED`, `PARTIALLY_RECEIVED`, `RESOLVED`, `CANCELLED`, and `WRITTEN_OFF` are approved.
- [x] Fully received, written-off, rescheduled, and cancelled close reasons are defined independently from lifecycle where necessary.
- [x] Overdue behavior is defined without an automatic calendar-driven business decision.
- [x] Expected date and budget-period synchronization or independence is decided.
- [x] Same-period date-correction rules are defined before and after realization history exists.
- [x] Cross-period changes use an explicit reschedule action rather than a hidden date-edit side effect.
- [x] Rescheduling allocation totals, allowed target periods, lineage, and no-auto-merge behavior are approved.
- [x] Edit and deletion permissions are defined for every lifecycle and history condition.
- [x] The approved decisions are reflected in the G29 PRD and domain glossary where appropriate.

### Blocked by

- Issue 1: Define Expected Inflow boundary and backing matrix

---

## Issue 3: Approve Realization And Domain Delegation Contract

**Type:** HITL

**Implementation status:** Core realization contract implemented. Owning-domain bounced-payment reversal and service extraction for earned/refund/asset posting remain follow-ups.

### What to build

Define realization as the bridge between an expectation and actual domain-owned ledger truth. Resolve the cardinality between realizations, expected rows, wallet legs, financial events, and source-domain records. Specify how earned income, receivable principal and charges, refunds, asset sales, early or late receipts, over-realization, and reversals delegate to their owning domains.

### Acceptance criteria

- [x] A realization has an approved business definition independent of a financial-event wrapper.
- [x] The relationship between one realization, wallet allocations, schedule allocations, and generated financial events is approved.
- [x] The model supports debt posting that can produce separate principal and charge events.
- [x] Earned-income, debt, refund, and asset-sale delegation boundaries are documented.
- [x] Multi-wallet totals and expectation-allocation totals have explicit invariants.
- [x] Early, on-time, and late receipt behavior is defined without rewriting expected dates.
- [x] Under-realization and over-realization behavior is approved.
- [x] The first release allocates one receipt across sibling schedules of one promise, not unrelated promises.
- [ ] Reversal and bounced-payment behavior is defined through the owning domain.
- [x] Cancellation, write-off, and reopening semantics do not contradict actual reversal behavior.
- [x] Atomicity, concurrency locking, and idempotency expectations are documented.
- [x] The approved decisions are reflected in the G29 PRD; no separate ADR is required for this feature-local model.

### Blocked by

- Issue 1: Define Expected Inflow boundary and backing matrix

---

## Issue 4: Approve Persistence, API, UX, And Migration Contract

**Type:** HITL

**Implementation status:** Implemented contract. Migration, aggregate API, canonical list/detail UI, source-kind creation, lifecycle actions, and legacy compatibility adapters exist.

### What to build

Turn the approved domain and realization models into one reviewed implementation contract. Define target persistence boundaries, lifecycle commands, read models, source-specific frontend journeys, responsive behavior, legacy migration, compatibility, and the public seams used for acceptance testing.

### Acceptance criteria

- [x] The target tables, relationships, ownership keys, constraints, and indexes are approved.
- [x] Derived values and protected stored projections are identified.
- [x] The lifecycle command API is approved for creation, permitted edits, realization, rescheduling, cancellation, write-off, and reversal reconciliation.
- [x] Generic clients cannot directly mutate protected lifecycle or realization fields.
- [x] Active, History, row-detail, Add Expected, Realize, and Reschedule UI flows are approved for desktop and mobile.
- [x] Money In is confirmed as the canonical Expected Inflows workspace.
- [x] The Budgets entry point is defined as a shortcut into the canonical flow.
- [x] Source-specific earned, debt, refund, and asset UI routing is documented.
- [x] Legacy expected-income data migration and API compatibility are approved.
- [x] Month summary, lifecycle API, source-domain posting APIs, and Money In UI are approved as the highest testing seams.
- [x] The G29 PRD is updated from draft to an approved implementation contract.

### Blocked by

- Issue 2: Approve schedule, date, lifecycle, and rescheduling model
- Issue 3: Approve realization and domain delegation contract

---

## Issue 5: Deliver Canonical Earned-Income Expectation Planning

**Type:** AFK

**Implementation status:** Implemented. The canonical visible path is wired and dormant Money In/Budgets legacy forms and API calls are removed; browser-level frontend tests remain.

### What to build

Deliver the first complete Expected Inflows path for earned income. A user can create, inspect, correct, and delete an eligible untouched earned-income expectation from the canonical Money In workspace; the selected month's summary reflects its valid backing; the Budgets shortcut opens the same flow; and compatible legacy earned expectations remain visible through the approved migration strategy.

### Acceptance criteria

- [x] An active income source can be selected through the canonical Add Expected flow.
- [x] The user can enter an approved expected amount, date or period, and optional note.
- [x] Ownership, source eligibility, positive amount, date, period, and planning-horizon rules are enforced.
- [x] New earned expectations appear in the Active view with source, expected amount, date, remaining amount, lifecycle, and backing effect.
- [x] Eligible active earned expectations contribute the correct amount to month summary.
- [x] Creating or editing an expectation creates no wallet, entity, or financial-event entries.
- [x] Permitted corrections and untouched-record deletion follow the approved mutability rules.
- [x] The Budgets shortcut opens the same creation flow with the selected month prefilled.
- [x] The duplicate earned-only Budgets form does not remain as a separate implementation.
- [x] Legacy earned expectations remain readable or are migrated according to the approved contract.
- [ ] API integration and frontend tests prove the complete user-visible path.

### Blocked by

- Issue 4: Approve persistence, API, UX, and migration contract

---

## Issue 6: Realize Earned Expectations Into Multiple Wallets

**Type:** AFK

**Implementation status:** Partial. API, database, multi-wallet UI, lifecycle math, locking, and idempotency exist; exhaustive API and frontend coverage does not.

### What to build

Let a user realize all or part of an earned-income expectation through a source-specific action. The user records the actual date and amount, allocates the amount across one or more wallets, and receives one atomic result that posts earned-income truth, records realization history, recalculates lifecycle and remaining backing, and updates Active or History presentation.

### Acceptance criteria

- [x] Realize is available only for lifecycle states allowed by the approved contract.
- [x] The flow requires a positive actual amount, actual date, and valid destination-wallet allocations.
- [x] Wallet allocations must sum to the approved actual wallet amount.
- [x] Duplicate, missing, inactive, or foreign-owned wallets are rejected.
- [ ] Earned-income posting delegates to the existing income domain and preserves income-source classification.
- [x] Full realization moves the expectation to its approved resolved history state.
- [x] Partial realization leaves the correct outstanding amount active and reduces expected backing by only the applied amount.
- [x] Early and late receipt dates are accepted without rewriting the expected date.
- [x] Actual posting, realization links, lifecycle recalculation, and backing changes commit atomically.
- [x] Idempotent retries cannot duplicate income or wallet value.
- [x] Active and History UI totals refresh from backend truth.
- [ ] API integration and frontend tests cover single-wallet, multi-wallet, partial, full, early, late, invalid, and retry behavior.

### Blocked by

- Issue 5: Deliver canonical earned-income expectation planning

---

## Issue 7: Reschedule Outstanding Expectations Across Dates

**Type:** AFK

**Implementation status:** Implemented. The selected source schedule is superseded and replacement schedules conserve its full outstanding amount; the full rollback/concurrency/browser test matrix remains.

### What to build

Let a user explicitly replace an active outstanding schedule with one or more dated replacement rows. The complete outstanding amount must be accounted for, the original expectation and its realizations remain historical truth, replacement rows retain lineage, monthly summaries move only the rescheduled backing, and no actual ledger movement occurs.

### Acceptance criteria

- [x] Reschedule is available only when an approved positive outstanding amount exists.
- [x] The flow accepts one or more positive dated allocations under the approved period rules.
- [x] Allocation amounts must equal the complete outstanding amount.
- [x] An allowed allocation can remain in the current period when the approved model permits it.
- [x] The original expected and realized amounts remain unchanged.
- [x] The selected source schedule becomes `SUPERSEDED`; the overall promise remains open until all expected money is received or otherwise resolved.
- [x] Replacement rows link to their source lineage and begin with the approved active lifecycle.
- [x] Rows sharing a date or month remain distinct in persistence.
- [x] Monthly read models may aggregate rows without merging their identity.
- [x] Rescheduling creates no wallet, entity, debt, refund, asset, or financial-event entries.
- [x] All replacements and source-row changes commit or roll back together.
- [x] Concurrent realization and rescheduling cannot consume the same outstanding amount.
- [ ] UI and API tests cover one target, multiple targets, a current-period target, invalid totals, rollback, lineage, and monthly backing changes.

### Blocked by

- Issue 6: Realize earned expectations into multiple wallets

---

## Issue 8: Deliver Cancellation, Write-Off, Overdue, And Reversal Repair

**Type:** AFK

**Implementation status:** Partial. Cancellation, partial/full write-off, write-off reversal, overdue presentation, reconciliation API, and lifecycle-aware UI actions exist; owning-domain payment reversal and full acceptance coverage remain open.

### What to build

Complete the lifecycle controls around active and realized expectations. Users can cancel eligible zero-receipt expectations, write off approved unpaid remainders, see overdue warnings without automatic state mutation, and have lifecycle and backing repaired after the owning domain reverses actual money.

### Acceptance criteria

- [x] Cancellation eligibility and resulting close reason follow the approved contract.
- [x] Write-off eligibility and resulting close reason follow the approved contract.
- [x] Neither cancellation nor write-off creates actual wallet movement.
- [x] Terminal records contribute no active expected backing.
- [x] Overdue is calculated for eligible active rows and appears as a warning without changing stored lifecycle.
- [x] The system never automatically reschedules or cancels a row because time passed.
- [ ] Actual-event reversal remains owned by the domain that posted the money.
- [x] Reversal reconciliation repairs realization totals, lifecycle, remaining amount, and backing atomically.
- [x] Direct arbitrary status changes are rejected.
- [x] Active and History actions reflect lifecycle and source-specific permissions.
- [ ] Tests cover zero-receipt cancellation, partial write-off, overdue presentation, reversal repair, forbidden actions, and backing effects.

### Blocked by

- Issue 6: Realize earned expectations into multiple wallets

---

## Issue 9: Plan Explicit Receivable-Debt Expectations

**Type:** AFK

**Implementation status:** Partial. Planning and display are wired through the canonical UI and API; the required frontend and full API test matrix is incomplete.

### What to build

Extend the canonical Expected Inflows creation and read experience to active receivable debts. A user explicitly selects a receivable and creates a planning expectation; uncertain debt balances remain excluded until that action; debt-linked rows display counterparty and source context correctly; and backing follows the approved receivable policy.

### Acceptance criteria

- [x] The Add Expected flow exposes the approved receivable-debt source kind.
- [x] Only active user-owned eligible receivables can be selected.
- [x] Creating a receivable debt alone does not create an expectation or backing.
- [x] A debt-linked expectation retains its debt identity and approved source metadata.
- [x] Debt-linked rows display the counterparty rather than a missing income-source fallback.
- [x] Expected amount is validated against the approved receivable and charge policy.
- [x] Eligible active receivable expectations affect month summary according to the backing matrix.
- [x] Creating, editing, or deleting an untouched debt expectation does not change the debt ledger or wallet reality.
- [x] Legacy explicit debt-linked expectations remain readable or are migrated according to the approved contract.
- [ ] API and frontend tests prove creation, ownership rejection, source display, no automatic backing, and month-summary behavior.

### Blocked by

- Issue 5: Deliver canonical earned-income expectation planning

---

## Issue 10: Realize Receivables Through Principal And Charge Posting

**Type:** AFK

**Implementation status:** Partial. This is the strongest delegated vertical slice: it calls the debt-payment service and links principal and charge events, but comprehensive acceptance coverage is absent.

### What to build

Let a user realize a receivable-linked expectation while delegating the actual payment completely to the debt domain. The resulting principal and charge components update debt truth, wallet truth, classifications, reconciliation, realization links, expected lifecycle, and backing without presenting returned principal as earned income.

### Acceptance criteria

- [x] Realization validates the expectation, receivable, amount, actual date, and destination wallets under the approved contract.
- [x] Actual posting delegates to the existing debt-payment service.
- [x] Principal reduces the correct receivable balance and receives the approved returned-value or settlement classification.
- [x] Charges reduce posted charge balance and receive the approved income classification.
- [x] A mixed payment can produce and link every principal and charge financial event.
- [x] Wallet value is recorded exactly once across all generated components.
- [x] Debt transaction, debt-ledger entries, financial events, realization links, lifecycle, and backing commit atomically.
- [x] Debt reconciliation and dependent projections run after posting.
- [x] Partial, full, early, and late payments update the expectation correctly.
- [x] Realized principal does not inflate earned-income reporting.
- [x] Idempotent retries and concurrent operations cannot duplicate payment or consume outstanding amounts twice.
- [ ] Tests cover principal-only, charge-only, mixed, multi-wallet, partial, full, invalid, rollback, and classification behavior.

### Blocked by

- Issue 6: Realize earned expectations into multiple wallets
- Issue 9: Plan explicit receivable-debt expectations

---

## Issue 11: Plan And Realize Expected Expense Refunds

**Type:** AFK

**Implementation status:** Partial. Planning, validation, posting effects, and linkage exist, but refund posting is currently reimplemented inside the coordinator instead of delegated to the existing refund workflow.

### What to build

Deliver a complete expected-refund path after its backing policy is approved. A user selects an eligible original expense, creates a dated expectation, and later realizes all or part of it through the refund domain so wallet restoration, original-expense linkage, budget-spending repair, expectation lifecycle, and backing remain coherent.

### Acceptance criteria

- [x] The Add Expected flow exposes the approved refund source kind.
- [x] Only eligible user-owned posted expenses can be selected.
- [x] The expected amount respects the approved remaining-refundable limit.
- [x] Creating an expected refund does not create a refund event or alter budget spending.
- [x] Pending refund backing follows the approved backing matrix.
- [ ] Realization delegates to the existing refund workflow and links to the original expense.
- [x] Actual refund amount cannot exceed the approved refundable balance unless an approved surplus policy applies.
- [x] Wallet restoration and budget-spending repair occur exactly once.
- [x] Partial and full refunds update both refund eligibility and expected lifecycle correctly.
- [x] Actual posting, realization links, lifecycle, and backing changes commit atomically.
- [ ] UI and API tests cover creation, source eligibility, partial/full realization, budget effects, invalid amounts, and rollback.

### Blocked by

- Issue 6: Realize earned expectations into multiple wallets

---

## Issue 12: Plan And Realize Expected Asset-Sale Proceeds

**Type:** AFK

**Implementation status:** Partial. Planning and posting effects exist, but asset-sale posting is currently reimplemented inside the coordinator instead of delegated to the asset domain.

### What to build

Deliver a complete expected asset-sale path after its backing and variance policies are approved. A user selects an eligible owned asset, creates a dated expected-sale row, and later realizes proceeds through asset liquidation so the asset lifecycle, sale classification, wallet truth, expectation lifecycle, and backing remain coherent.

### Acceptance criteria

- [x] The Add Expected flow exposes the approved asset-sale source kind.
- [x] Only eligible user-owned assets can be selected.
- [x] Creating the expectation does not liquidate or mutate the asset.
- [x] Pending asset-sale backing follows the approved backing matrix.
- [ ] Realization delegates to the existing asset-sale or liquidation domain.
- [x] Sale proceeds retain asset-sale classification rather than ordinary earned-income classification.
- [x] Under- and over-sale variance follows the approved policy.
- [x] Wallet value is recorded exactly once.
- [x] Asset lifecycle, financial events, realization links, expectation lifecycle, and backing commit atomically.
- [x] Partial sale behavior is either supported according to an approved policy or rejected clearly.
- [ ] UI and API tests cover creation, eligibility, exact/under/over realization, classification, rollback, and lifecycle effects.

### Blocked by

- Issue 6: Realize earned expectations into multiple wallets

---

## Issue 13: Allocate One Promise-Level Receipt Across Sibling Schedules

**Type:** AFK

**Implementation status:** Implemented for sibling schedules of one promise. Independent promises are intentionally not combined into one receipt command; comprehensive concurrency, rollback, and browser tests remain.

### What to build

Allow one user-observed receipt to satisfy one or more dated schedules belonging to the same original promise without duplicating wallet value. The promise-level Receive action defaults to oldest-due allocation, permits explicit sibling allocation when needed, posts actual incoming value once, and recalculates every affected schedule plus the parent promise.

### Acceptance criteria

- [x] The UI begins at the selected promise and exposes sibling schedule allocations only when multiple active schedules exist.
- [x] Every selected schedule is active, user-owned through the promise, and belongs to the same delegated settlement context.
- [x] Schedule allocation amounts are positive and do not exceed approved outstanding limits.
- [x] Schedule allocations equal the expected portion satisfied; an actual overpayment may exceed that amount.
- [x] Wallet allocation totals satisfy the approved relationship to the same actual receipt amount.
- [x] Actual wallet value and source-domain posting occur exactly once.
- [x] Each affected schedule receives its own realization allocation and lifecycle recalculation, followed by parent-promise recalculation.
- [x] The promise and all affected schedules are locked in deterministic order.
- [x] The complete operation commits or rolls back atomically.
- [x] Idempotent retries cannot duplicate any source-domain, wallet, or expectation effect.
- [ ] Tests cover sibling schedules, partial allocations, invalid totals, overpayment, concurrency, rollback, and aggregate lifecycle results.

### Blocked by

- Issue 6: Realize earned expectations into multiple wallets
- Issue 10: Realize receivables through principal and charge posting

---

## Issue 14: Expose Expected Inflows To The Future Timeline Contract

**Type:** AFK

**Implementation status:** Partial. A dated owner-scoped timeline endpoint exists; dedicated timeline-contract tests are missing.

### What to build

Expose reliable dated Expected Inflow projections for later timeline and simulator work. The read contract must distinguish source kind, backing eligibility, expected date, active remaining amount, lifecycle, overdue presentation, and terminal history without duplicating lifecycle or backing math in timeline consumers.

### Acceptance criteria

- [x] Timeline output includes stable identity, source kind, source label, expected date, expected amount, realized amount, remaining amount, lifecycle, and backing eligibility.
- [x] Active and terminal rows are distinguishable without consumers recreating lifecycle rules.
- [x] Overdue presentation is exposed without mutating stored lifecycle.
- [x] Rescheduled lineage and replacement rows do not cause double-counted projected inflows.
- [x] Source-specific accounting details are represented only where required for display or routing.
- [x] Timeline consumers do not calculate expected-inflow backing independently.
- [x] The contract can be filtered by date range and owner.
- [ ] Tests cover interleaved source kinds, partial receipts, rescheduling, overdue rows, terminal rows, and chronological ordering.
- [x] This issue does not build the complete cash-flow simulator UI.

### Blocked by

- Issue 7: Reschedule outstanding expectations across dates
- Issue 8: Deliver cancellation, write-off, overdue, and reversal repair
- Issue 10: Realize receivables through principal and charge posting
- Issue 11: Plan and realize expected expense refunds
- Issue 12: Plan and realize expected asset-sale proceeds

---

## Issue 15: Handle Approved Non-Backing Incoming Sources

**Type:** AFK

**Implementation status:** Not implemented. The schema has a backing-eligibility field, but no approved non-backing source kind or end-to-end flow exists.

### What to build

Implement any incoming source kinds that Issue 1 approves for Expected Inflows visibility but excludes from plan backing, such as borrowed money or neutral returned value. The complete path must make the non-backing treatment obvious, delegate actual posting to the correct domain, and prevent the source from improving plan health while still supporting dated tracking when approved.

### Acceptance criteria

- [ ] Only source kinds explicitly approved by Issue 1 are implemented.
- [ ] The Add Expected flow identifies that the source does not count toward plan backing.
- [ ] Active rows display zero backing contribution while retaining their dated expected amount.
- [ ] Month summary and budget-create/update validation do not gain capacity from these rows.
- [ ] Realization delegates to the correct source domain and never misclassifies borrowed money as earned income.
- [ ] Actual wallet value and corresponding liability or neutral context are recorded according to the owning domain.
- [ ] Lifecycle, realization history, early/late behavior, and terminal actions follow the approved common contract.
- [ ] UI and API tests prove clear labeling, zero backing, correct realization routing, and no earned-income inflation.

### Blocked by

- Issue 1: Define Expected Inflow boundary and backing matrix
- Issue 5: Deliver canonical earned-income expectation planning
