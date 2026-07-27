# Tickets: Set Aside Money Goal

Build persistent Set Aside Money reserve goals with wallet-bound protection, reserve expense attribution, Prepare Payment, reimbursement, budget impact, and reversal. Source spec: `../specs/set_aside_money_goal_spec.md`.

Work the **frontier**: any ticket whose blockers are all done. For a purely linear chain that means top to bottom.

## Proposed Breakdown

1. **Establish Reserve Goal lifecycle and metrics**
   - Blocked by: None
   - What it delivers: Set Aside Money behaves as a persistent active reserve with clear protected, refill, and fully-reserved metrics.

2. **Allocate and return reserve money**
   - Blocked by: Ticket 1
   - What it delivers: users can protect and unprotect exact wallet money without changing real wallet balances.

3. **Record a Direct Reserve Expense**
   - Blocked by: Ticket 2
   - What it delivers: users can spend from reserve-holding wallets and consume matching reserve allocations.

4. **Support OffWallet and Mixed Reserve Expenses**
   - Blocked by: Ticket 3
   - What it delivers: users can record reserve-related expenses that are partly or fully ordinary-funded.

5. **Add Set Aside Prepare Payment**
   - Blocked by: Ticket 2
   - What it delivers: users can move reserve money and matching protection before the expense.

6. **Reimburse an ordinary expense from reserve**
   - Blocked by: Ticket 4
   - What it delivers: users can transfer real reserve money after an expense and update the original expense's funding attribution.

7. **Apply reimbursement to original-period budgets**
   - Blocked by: Ticket 6
   - What it delivers: reimbursement restores budget capacity in the original expense period while category actual spending remains truthful.

8. **Add Reserve audit bundles, classifications, and metrics**
   - Blocked by: Tickets 5, 7
   - What it delivers: reserve operations store source facts for audit, classification, idempotency, and derived metrics.

9. **Reverse and edit Reserve expense bundles**
   - Blocked by: Ticket 8
   - What it delivers: reserve expenses and reimbursements can be reversed safely without destructive history edits.

10. **Harden Set Aside Money acceptance coverage**
    - Blocked by: Ticket 9
    - What it delivers: tests prove lifecycle, allocation, expenses, Prepare Payment, reimbursement, budgets, reversal, reliability, and UI behavior.

## Ticket 1: Establish Reserve Goal Lifecycle and Metrics

**What to build:** Users can create Set Aside Money goals that behave as persistent wallet-bound reserves, stay active when fully reserved or used, and expose clear reserve metrics.

**Blocked by:** None - can start immediately.

- [ ] Creating a reserve goal stores the reserve intent, title, target, currency, status, and optional template key without moving wallet money.
- [ ] Reserve goals start and remain `ACTIVE` through allocation, use, reimbursement, return, and refill.
- [ ] Reaching the target displays `Fully reserved` without completing the goal.
- [ ] Terminal target dates are not required or accepted for reserve goals.
- [ ] Manual completion of a reserve goal is rejected.
- [ ] The UI exposes `ProtectedNow`, `RefillNeeded`, and `FullyReserved` without confusing current refill need with lifetime usage.

## Ticket 2: Allocate and Return Reserve Money

**What to build:** Users can protect free money in specific wallets for a reserve and explicitly return protected money to free money without spending it.

**Blocked by:** Ticket 1: Establish Reserve Goal Lifecycle and Metrics.

- [ ] Reserve Money validates positive amount, eligible wallet, compatible currency, and sufficient free money.
- [ ] Allocation creates protected reserve in the selected wallet without changing real wallet balance.
- [ ] Return Reserved Money validates the amount does not exceed that wallet's current reserve allocation.
- [ ] Returning reserve decreases protection and increases free money without creating income, expense, or transfer.
- [ ] Current wallet allocation can be derived from active allocation, return, and consume events.
- [ ] Allocation and return operations are atomic and idempotent.

## Ticket 3: Record a Direct Reserve Expense

**What to build:** Users can record an expense paid from reserve-holding wallets where selected reserve-covered amounts consume protection from the same wallets and update budget impact.

**Blocked by:** Ticket 2: Allocate and Return Reserve Money.

- [ ] The wizard asks which wallets actually paid, how much each paid, and how much from each wallet should use this reserve.
- [ ] A reserve-funded amount cannot exceed the payment amount or that same wallet's reserve allocation.
- [ ] Direct reserve use decreases the same wallet's real balance and reserve allocation by the selected reserve-covered amount.
- [ ] Full category actual spending equals the full expense amount.
- [ ] Monthly budget impact equals the ordinary-funded portion.
- [ ] The goal remains active after reserve use.
- [ ] Step 2 preview and completion use the same backend policy.

## Ticket 4: Support OffWallet and Mixed Reserve Expenses

**What to build:** Users can record reserve-related expenses paid partly or entirely with ordinary wallet money, including one wallet paying above its reserve allocation.

**Blocked by:** Ticket 3: Record a Direct Reserve Expense.

- [ ] A wallet with no reserve allocation can pay an ordinary-funded expense without changing reserve allocations.
- [ ] A wallet paying above its reserve allocation can split the leg into reserve-covered and ordinary portions.
- [ ] The user can reduce proposed reserve use, including to zero.
- [ ] OffWallet expenses leave the reserve unchanged and remain eligible for later reimbursement.
- [ ] Mixed expenses consume reserve only for explicitly selected reserve-covered portions.
- [ ] The UI never asks the user to choose Direct, OffWallet, or Mixed.
- [ ] Step 2 explains ordinary payment and later reimbursement eligibility in plain language.

## Ticket 5: Add Set Aside Prepare Payment

**What to build:** Before an expense, users can move reserve money and matching reserve protection to the wallet expected to pay, without creating expense, income, consumption, or budget effects.

**Blocked by:** Ticket 2: Allocate and Return Reserve Money.

- [ ] Prepare Payment transfers real money from reserve source wallets to destination wallets.
- [ ] Matching reserve allocation relocates from source wallets to destination wallets in the same operation.
- [ ] Total reserve protection is conserved.
- [ ] Source and destination balances reflect the real transfer.
- [ ] `ProtectedNow` and `RefillNeeded` remain unchanged.
- [ ] The destination wallet can later use the relocated reserve directly.
- [ ] Prepare Payment cannot rewrite history after an expense has already occurred.

## Ticket 6: Reimburse an Ordinary Expense From Reserve

**What to build:** Users can reimburse an existing ordinary or partially ordinary expense by transferring real money from reserve source wallets to original payment wallets and updating the original expense's reserve coverage.

**Blocked by:** Ticket 4: Support OffWallet and Mixed Reserve Expenses.

- [ ] Reimbursement is launched from expense details or the reserve goal card with the original expense context.
- [ ] Only active real expenses with ordinary-funded amount remaining are eligible.
- [ ] Source wallets must hold enough reserve allocation and preserve other protected money after transfer.
- [ ] Destination wallets must be original payment wallets with unreimbursed ordinary-funded portions.
- [ ] Source totals equal destination totals and the reimbursement amount does not exceed remaining ordinary-funded amount.
- [ ] Source wallet balances and reserve allocations decrease; destination wallet balances increase.
- [ ] The original expense's reserve-covered amount increases and ordinary-funded amount decreases.
- [ ] Reimbursement is not income, not a second expense, and not a merchant payment.

## Ticket 7: Apply Reimbursement to Original-Period Budgets

**What to build:** Reserve reimbursement restores monthly budget capacity in the original expense period while preserving full category actual spending.

**Blocked by:** Ticket 6: Reimburse an Ordinary Expense From Reserve.

- [ ] Category actual spending remains the full original expense amount after reimbursement.
- [ ] Monthly budget impact becomes total expense minus active reserve coverage.
- [ ] Partial reimbursement leaves the remaining ordinary-funded amount as budget impact.
- [ ] Budget capacity is restored in the original expense month, not the reimbursement month.
- [ ] Budget impact never becomes negative.
- [ ] Locked historical periods are rejected or routed through an explicit adjustment policy.

## Ticket 8: Add Reserve Audit Bundles, Classifications, and Metrics

**What to build:** Reserve expenses and reimbursements persist auditable source data so current coverage, classification, budget impact, protected amount, refill need, and lifetime use can be derived.

**Blocked by:**

- Ticket 5: Add Set Aside Prepare Payment.
- Ticket 7: Apply Reimbursement to Original-Period Budgets.

- [ ] Reserve goal records include intent, target, currency, status, optional template key, and timestamps.
- [ ] Allocation ledger rows store type, wallet, amount, operation, linked expense or transfer, reversal reference, and timestamp.
- [ ] Expense funding attribution stores total amount, payment legs, direct reserve coverage, reimbursement coverage, ordinary amount, budget impact, and linked reserve.
- [ ] Reimbursement records store source legs, destination legs, original expense, budget period, status, reversal link, and idempotency key.
- [ ] Current classification is derived from reserve-covered and ordinary-funded amounts.
- [ ] Lifetime reserve use includes both direct consumption and reimbursement consumption when that metric is enabled.

## Ticket 9: Reverse and Edit Reserve Expense Bundles

**What to build:** Users can safely reverse reserve expenses and reimbursements, and edits cannot destroy audit history or make reserve coverage exceed the expense.

**Blocked by:** Ticket 8: Add Reserve Audit Bundles, Classifications, and Metrics.

- [ ] Direct reserve-expense reversal restores payment wallet balances, reserve allocations, category actual spending, and original-period budget impact.
- [ ] Reimbursement reversal reverses the internal transfer, restores source allocations, reduces original expense reserve coverage, and reapplies original-period budget impact.
- [ ] An expense with active reserve coverage cannot be reduced below the covered amount without reversing or adjusting coverage first.
- [ ] Linked reimbursement dependencies are enforced during direct expense reversal.
- [ ] Impossible restoration is blocked with an explicit correction path.
- [ ] Reversal records preserve audit history instead of destructively deleting posted financial events.

## Ticket 10: Harden Set Aside Money Acceptance Coverage

**What to build:** Set Aside Money behavior is covered across lifecycle, allocation, direct use, OffWallet use, mixed use, Prepare Payment, reimbursement, budgets, reversal, reliability, and UI behavior.

**Blocked by:** Ticket 9: Reverse and Edit Reserve Expense Bundles.

- [ ] Tests cover reserve creation, no automatic completion, manual completion rejection, and archive/delete release policy.
- [ ] Tests cover allocation, return, consumption derivation, insufficient free money, and wallet protection invariants.
- [ ] Tests cover direct reserve expense, OffWallet ordinary expense, mixed multi-wallet expense, same-wallet above reserve, user-reduced reserve use, and stale preview rejection.
- [ ] Tests cover category actual spending, budget impact, original-period reimbursement, partial reimbursement, locked-period policy, and non-negative budget impact.
- [ ] Tests cover Prepare Payment conservation and destination direct-use readiness.
- [ ] Tests cover reimbursement single source, multiple sources, multiple destinations, partial reimbursement, source insufficiency, destination validation, and not income/not expense classification.
- [ ] Tests cover reversal, edit guards, idempotency, concurrency revalidation, wallet-order independence, and full rollback on failure.
