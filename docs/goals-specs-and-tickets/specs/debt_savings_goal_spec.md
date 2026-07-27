# Debt Savings Goal Specification

## Domain, Payment, Progress, Completion, and Reversal Rules

**Version:** 1.0 - Implementation Ready  
**Goal family:** Save toward a debt  
**Scope:** Debts the user owes; installment/payment-plan branch excluded  
**Status:** Normative product, accounting, and UX specification  
**Date:** July 13, 2026

---

## 1. Purpose

This document defines the complete v1 behavior of a **Debt Savings** goal: a goal linked to an existing debt the user owes, used to protect wallet money for future debt payments and later attribute part of a real debt payment to that protected money.

A Debt Savings goal has two jobs:

1. Protect exact wallet money so it does not appear freely spendable.
2. Convert selected protected amounts into real payments that reduce the linked debt.

The goal does not own the debt balance. The debt ledger remains the sole source of truth for how much is owed.

The locked product principle is:

> The user records the real debt payment from the wallets that actually paid. Sarflog then separates that payment into a debt-savings-funded portion and an ordinary-money portion. The full real payment reduces the debt exactly once; only the debt-savings-funded portion consumes goal reservations.

This specification intentionally excludes post-payment reimbursement for Debt Savings in v1.

---

## 2. Locked v1 decisions

The following decisions are normative:

1. Only open debts the user owes may have a Debt Savings goal.
2. Only one active Debt Savings goal may exist for the same debt.
3. The goal supports two modes: **Save everything left** and **Save a smaller amount**.
4. Creating the goal does not move money.
5. Reservations remain physically inside their original wallets.
6. `Reserve money`, `Unreserve`, and `Prepare payment` never alter the debt balance.
7. The primary action is **Record debt payment**, not a narrow “goal-only payment” action.
8. Record debt payment accepts any wallet or combination of wallets.
9. The user never chooses Direct, OffWallet, or Mixed.
10. Sarflog derives the relationship and displays consequences in step 2 of a two-step wizard.
11. A paying wallet may use debt savings only up to its own reservation for this goal.
12. A payment amount above a wallet's reservation is allowed; the excess is ordinary payment money.
13. A partial goal may fund no more than its remaining goal target. Any excess payment remains ordinary.
14. The full real payment reduces the debt once, even when only part is funded through the goal.
15. There is no Debt Savings reimbursement action in v1.
16. A partial goal may be finished early so the user cannot become trapped below the target.
17. If the debt closes, the linked goal completes even when its partial target was not fully paid through the goal.
18. Reversing a linked debt payment must reverse every linked wallet, reservation, progress, release, and goal-status effect.
19. All settlement and reversal operations must be atomic.

---

## 3. Scope and non-scope

### 3.1 Included

This specification covers:

- goal eligibility and creation;
- full and partial saving modes;
- wallet reservations and unreserving;
- Prepare Payment before the creditor is paid;
- the unified two-step Record Debt Payment wizard;
- payments from reserved wallets, unrelated wallets, and mixed sources;
- payments greater than the partial goal target;
- progress and readiness metrics;
- early completion of partial goals;
- debt charges, forgiveness, corrections, and reversals;
- event bundles, atomicity, concurrency, and audit requirements.

### 3.2 Excluded

This specification does not define:

- installment or payment-plan schedules;
- incoming debts where someone owes the user;
- debt refinancing or consolidation;
- automatic interest accrual engines;
- post-payment reimbursement from Debt Savings;
- foreign-exchange conversion rules;
- bank synchronization.

---

## 4. Fundamental financial truths

### 4.1 Debt truth

The debt ledger answers:

> How much does the user currently owe?

Only debt-ledger events may change this value.

### 4.2 Wallet truth

Wallet balances answer:

> Which wallets actually lost or received real money?

### 4.3 Goal-protection truth

Goal allocations answer:

> How much money is currently protected in each wallet for this debt?

### 4.4 Funding-attribution truth

A debt payment record answers:

> How much of this real debt payment was funded through the Debt Savings goal, and how much came from ordinary wallet money?

These truths must remain separate. A goal must never secretly manipulate the debt balance, and a debt payment must never silently consume a reservation from a different wallet.

---

## 5. Terminology

### 5.1 Linked debt

The open debt that the user owes and that the goal prepares money to pay.

### 5.2 Reservation

Money still inside a wallet but protected for this Debt Savings goal.

### 5.3 Goal-funded payment amount

The portion of a real debt payment explicitly funded by this goal and consumed from reservations in the same paying wallets.

### 5.4 Ordinary payment amount

The portion of a real debt payment funded by ordinary wallet money rather than this goal.

### 5.5 Paid through goal

The cumulative active amount of debt payments funded by this goal. Reversed payments do not remain in this value.

### 5.6 Save everything left

A mode whose purpose is to prepare for the debt's entire remaining balance. Its readiness requirement follows the live debt balance.

### 5.7 Save a smaller amount

A mode whose purpose is to prepare one partial payment up to a fixed user-selected amount.

### 5.8 Prepare Payment

A pre-payment operation that transfers real money and relocates the matching reservation to the wallet expected to pay the creditor.

### 5.9 Payment bundle

One causal operation containing the debt-ledger payment, wallet outflows, reservation consumption, progress changes, completion, and any release of leftover reservations.

---

## 6. Eligibility and creation rules

A Debt Savings goal may be created only when all of the following are true:

- the debt exists;
- the debt direction is **I owe**;
- the debt is open;
- the remaining debt balance is positive;
- no other active Debt Savings goal exists for the same debt.

A closed, fully paid, reversed, deleted, or incoming debt is ineligible.

Creating the goal:

- links the goal to the debt;
- stores the selected mode;
- stores a target amount for partial mode;
- optionally stores a target date;
- creates no wallet transfer;
- creates no reservation unless the user performs Reserve Money;
- does not change the debt balance.

### 6.1 Save everything left creation

The user selects the debt. No independent fixed target is required. The UI may display the debt balance at creation as an initial reference, but the live debt balance remains authoritative.

### 6.2 Save a smaller amount creation

The user selects a target satisfying:

```text
0 < original_partial_target <= current_debt_balance
```

The partial target does not grow when the debt grows. It may become effectively smaller when the remaining debt becomes too small to justify the original target.

---

## 7. Mathematical model

For the linked debt and goal:

```text
D = current remaining debt balance
Y = cumulative active amount paid through this goal
R_i = current reservation for this goal in wallet i
R = sum(R_i) = total reserved now
P_i = real debt-payment amount paid from wallet i
U_i = portion of P_i funded through this goal
O_i = ordinary portion of P_i
Q = sum(P_i) = total real debt payment
U = sum(U_i) = total goal-funded portion
O = sum(O_i) = total ordinary portion
```

For every payment wallet:

```text
P_i = U_i + O_i
0 <= U_i <= P_i
O_i >= 0
```

Local reservation invariant:

```text
U_i <= R_i
```

Global payment invariant:

```text
0 < Q <= D
```

Settlement:

```text
D_after = D - Q
wallet_balance_i_after = wallet_balance_i_before - P_i
R_i_after = R_i - U_i
Y_after = Y + U
```

No ordinary portion consumes a goal reservation.

---

## 8. Goal modes and effective targets

### 8.1 Save everything left

This mode prepares for the entire live debt balance.

The goal does not need a single historical progress bar combining old payments and current reservations. The UI must show separate truths:

```text
Debt remaining = D
Reserved now = R
Paid through this goal = Y
Ready for remaining debt = min(R, D) / D
```

When `D = 0`, readiness is complete and the goal completes.

The maximum goal-funded amount in a new payment is limited by:

```text
U <= min(R, Q, D)
```

There is no independent partial-target cap.

### 8.2 Save a smaller amount

Let:

```text
T0 = original user-selected partial target
```

The effective total target is:

```text
T = min(T0, Y + D)
```

This prevents the goal from demanding more than the amount already paid through the goal plus the debt that still exists.

Remaining goal-funded capacity:

```text
GoalCapacityRemaining = max(0, T - Y)
```

A new payment must satisfy:

```text
U <= GoalCapacityRemaining
```

Current progress amount:

```text
ProgressAmount = min(T, Y + R)
```

Still needed to prepare:

```text
StillNeeded = max(0, T - Y - R)
```

Still payable through the goal:

```text
StillPayableThroughGoal = max(0, T - Y)
```

### 8.3 Why paid and reserved are shown separately

`Y` is historical debt reduction funded through the goal. `R` is money still available for a future payment. They are different states and must be displayed separately even when a preparation progress indicator uses `Y + R`.

---

## 9. Reserve Money

Reserve Money protects free money in one or more eligible wallets.

For each allocation in wallet `i`:

```text
0 < allocation_i <= wallet_free_to_reserve_i
```

Result:

- wallet real balance is unchanged;
- `R_i` increases;
- wallet free-to-spend decreases by the same amount;
- debt balance is unchanged;
- goal status remains active.

Reserve Money must not reserve funds already protected for another goal or obligation.

---

## 10. Unreserve Money

The user may return protected money to free wallet money while the goal is active.

For each wallet:

```text
0 < unreserve_i <= R_i
```

Result:

- wallet real balance is unchanged;
- `R_i` decreases;
- free money increases;
- debt balance is unchanged;
- paid-through-goal remains unchanged.

If a partial goal is already complete, remaining reservations are handled by completion release rather than ordinary Unreserve.

---

## 11. Prepare Payment

Prepare Payment is optional and occurs before the real creditor payment.

Example:

```text
Wallet A holds 500,000 reserved.
The creditor must be paid from Wallet C.
The user prepares 300,000 from A to C.
```

The operation performs:

```text
Real transfer: A -> C = 300,000
Reservation relocation: R_A -= 300,000; R_C += 300,000
Debt change: 0
Paid-through-goal change: 0
```

Conservation invariants:

```text
sum(reservations_before) = sum(reservations_after)
source balance decreases by transfer amount
destination balance increases by transfer amount
```

Prepare Payment must never be used to invent a transfer after the debt payment already occurred.

---

## 12. Unified two-step Record Debt Payment wizard

The user must never choose Direct, OffWallet, or Mixed.

### 12.1 Step 1 - Record what actually happened

The user enters:

- payment date;
- one or more wallets that actually paid the creditor;
- real amount paid from each wallet;
- optional note;
- the amount from each paying wallet that should use this goal's reservation.

For each row, show:

```text
Wallet name
Current balance
Reserved for this debt goal
Amount paid
Use from debt savings
Ordinary portion (derived)
```

The per-wallet calculation is:

```text
O_i = P_i - U_i
```

The user does not choose a settlement mode.

### 12.2 Smart defaults

When launched from the Debt Savings goal card, Sarflog should propose the maximum eligible goal-funded amount.

For each payment row in visible order:

```text
proposed_U_i = min(P_i, R_i, remaining_goal_capacity_after_prior_rows)
```

The user may reduce `U_i`, including reducing it to zero.

When launched from the general Debt page, the product may default goal use to zero and offer a clear one-click action such as **Use available debt savings**. Regardless of entry point, step 2 must display the exact final attribution before confirmation.

### 12.3 Step 1 validation

Validate:

```text
P_i > 0
P_i <= wallet spendable balance for real outflow
U_i >= 0
U_i <= P_i
U_i <= R_i
sum(P_i) <= D
```

For partial mode also validate:

```text
sum(U_i) <= GoalCapacityRemaining
```

The total payment is not capped by the goal target. Only the goal-funded portion is capped by the goal.

### 12.4 Step 2 - Review consequences

Step 2 must be generated from the same backend policy used for final settlement.

It must show:

- total received by the creditor;
- amount funded through debt savings;
- amount paid with ordinary money;
- debt balance before and after;
- wallet balance changes per wallet;
- reservation changes per wallet;
- paid-through-goal before and after;
- goal status after;
- completion reason, if any;
- leftover reservations that will be released;
- warnings or blocked conditions.

The final action is **Complete payment**.

### 12.5 Atomic completion

On Complete, the backend must revalidate all balances, reservations, debt state, target capacity, and version numbers. It then applies the complete payment bundle atomically.

---

## 13. Derived payment patterns

Patterns are derived for audit and analytics only.

Let:

```text
F = wallets with R_i > 0 before payment
P = wallets with P_i > 0
```

Descriptive classification:

```text
DIRECT: every payment amount is goal-funded and every paying wallet has reservation
OFF_WALLET: U = 0
MIXED: U > 0 and O > 0
```

For Debt Savings, amount attribution is more useful than set membership. A single wallet may pay both a goal-funded and ordinary portion when `P_i > U_i`.

The user must not see or select these technical labels.

---

## 14. Canonical payment examples

### 14.1 Fully goal-funded payment

Starting state:

```text
Debt remaining: 1,000,000
Wallet A reserved: 400,000
Wallet B reserved: 300,000
```

Payment:

```text
Wallet A pays 200,000; U_A = 200,000
Wallet B pays 100,000; U_B = 100,000
```

Result:

```text
Debt remaining: 700,000
A reservation: 200,000
B reservation: 200,000
Paid through goal: +300,000
Ordinary payment: 0
Goal remains active
```

### 14.2 Entirely ordinary OffWallet payment

Starting state:

```text
Debt remaining: 1,000,000
Wallet A reserved: 600,000
Wallet C reserved: 0
```

Payment:

```text
Wallet C pays 300,000; U_C = 0
```

Result:

```text
Debt remaining: 700,000
Wallet C balance: -300,000
Wallet A reservation: unchanged at 600,000
Paid through goal: unchanged
Ordinary payment: 300,000
```

There is no reimbursement action in v1.

### 14.3 Same wallet pays more than its reservation

Starting state:

```text
Wallet A reserved: 2,000,000
Wallet A pays: 2,400,000
```

Valid attribution:

```text
U_A = 2,000,000
O_A = 400,000
```

The payment is allowed if Wallet A has enough real balance. The app must not reject the real debt payment merely because it exceeds the reservation.

### 14.4 Mixed multi-wallet payment

Starting state:

```text
Wallet A reserved: 2,000,000
Wallet B reserved: 1,000,000
Wallet C reserved: 0
```

Payment:

```text
A pays 2,400,000; U_A = 2,000,000; O_A = 400,000
C pays   600,000; U_C = 0;         O_C = 600,000
```

Result:

```text
Total debt payment: 3,000,000
Goal-funded: 2,000,000
Ordinary: 1,000,000
A reservation becomes 0
B reservation remains 1,000,000
```

### 14.5 A 2M partial goal inside a 10M debt payoff

Starting state:

```text
Debt remaining: 10,000,000
Partial target: 2,000,000
A reserved: 1,200,000
B reserved:   800,000
C reserved:         0
```

Real payment:

```text
A pays 1,200,000; U_A = 1,200,000
B pays   800,000; U_B =   800,000
C pays 8,000,000; U_C =         0
```

Preview:

```text
Creditor receives: 10,000,000
From debt savings: 2,000,000
From ordinary money: 8,000,000
Debt: 10,000,000 -> 0
```

Result:

- the debt closes;
- the partial goal records 2M paid through goal;
- the 8M remains ordinary payment;
- the goal completes;
- no amount above 2M is falsely attributed to the goal.

### 14.6 Debt closes before partial target is achieved

Starting state:

```text
Debt remaining: 10,000,000
Partial target: 2,000,000
Only 1,000,000 is used from the goal
9,000,000 is ordinary money
```

The debt closes. The goal completes with reason `DEBT_CLOSED`, not `TARGET_PAID`. Any unused reservation is released.

---

## 15. Completion rules

### 15.1 Completion reasons

Store an explicit reason:

```text
TARGET_PAID
DEBT_CLOSED
FINISHED_EARLY
```

### 15.2 Partial goal target paid

A partial goal completes with `TARGET_PAID` when:

```text
Y >= T
```

The debt may still remain open. After completion, the user may create another Debt Savings goal for the same debt.

### 15.3 Debt closed

Any active goal linked to a debt that becomes zero completes with `DEBT_CLOSED`.

This applies whether the debt was closed by:

- a goal-funded payment;
- ordinary payment money;
- a mixed payment;
- forgiveness;
- a balance correction.

### 15.4 Finish partial goal early

A partial goal must offer **Finish goal early**.

Example:

```text
Target: 3,000,000
Paid through goal: 2,900,000
Reserved now: 0
```

The user may finish at 2.9M rather than remain trapped for 100k.

On finish early:

- status becomes completed;
- reason becomes `FINISHED_EARLY`;
- achieved amount is stored;
- any remaining reservations are released;
- another active goal for the debt may then be created.

### 15.5 Release on completion

When the goal completes, all remaining reservations for that goal are released to free money.

No real wallet balance changes during release.

The release must be part of the completion bundle for reversible audit.

---

## 16. Progress and card display

### 16.1 Shared metrics

Always show:

```text
Debt remaining
Reserved now
Paid through this goal
```

Do not hide these behind one ambiguous percentage.

### 16.2 Save everything left card

Recommended display:

```text
Debt remaining: D
Reserved now: R
Ready for remaining debt: min(R, D) / D
Paid through this goal: Y
```

The progress bar represents current readiness for the remaining debt, not lifetime historical progress.

### 16.3 Save a smaller amount card

Recommended display:

```text
Payment target: T
Paid through this goal: Y
Still reserved: R
Still needed: max(0, T - Y - R)
```

A preparation bar may show:

```text
min(T, Y + R) / T
```

Completion must not be inferred solely from the bar. Completion requires target payment, debt closure, or explicit early finish.

### 16.4 Excess reserved after debt changes

For partial mode:

```text
ExcessReserved = max(0, R - max(0, T - Y))
```

When positive and the goal is still active, display an **Excess reserved** warning and let the user choose which wallet allocations to unreserve. Do not silently choose wallet-level releases unless the goal completes.

---

## 17. Debt actions and their goal effects

### 17.1 Record payment

May change:

- debt balance;
- payment-wallet balances;
- selected goal reservations;
- paid-through-goal;
- goal completion;
- release of leftover reservations.

### 17.2 Add charge

Changes the debt balance upward.

- Full mode readiness requirement grows automatically.
- Partial mode does not grow beyond its original target.
- No reservation is consumed.
- Paid-through-goal does not change.

### 17.3 Forgive balance

Reduces the debt without a wallet payment.

- It is not paid through the goal.
- It may shrink partial effective target.
- If it closes the debt, the goal completes with `DEBT_CLOSED` and releases reservations.

### 17.4 Correct balance

Applies a positive or negative debt-ledger adjustment.

The goal recomputes from the new debt truth. A correction is never treated as a goal-funded payment.

### 17.5 Edit debt metadata

Changing title, note, due date, or non-balance metadata must not alter goal reservations or progress.

### 17.6 Archive debt

An open debt with an active Debt Savings goal must not be archived without an explicit resolution flow. The user must close/correct the debt or cancel/archive the goal and release reservations first.

---

## 18. Reversal model

### 18.1 Core rule

A debt action must not be reversed in isolation when it created linked goal or wallet effects.

> Reverse the causal event bundle, not a single visible ledger row.

### 18.2 Goal-funded payment bundle

A payment bundle may contain:

1. debt-ledger payment;
2. one or more wallet outflows;
3. one or more goal `CONSUME` events;
4. paid-through-goal increase;
5. goal completion;
6. leftover reservation releases.

All rows share a causal bundle identifier.

### 18.3 Reversing a payment

The inverse operation must:

```text
restore debt balance by Q
restore each payment wallet by P_i
restore each consumed reservation by U_i
decrease paid-through-goal by U
reopen the goal if this bundle caused completion
restore reservations released by this bundle
```

Example:

```text
Before payment: debt 500k, wallet reservation 500k, goal ACTIVE
After payment: debt 0, reservation 0, goal COMPLETED
After reversal: debt 500k, reservation 500k, goal ACTIVE
```

The screenshot behavior where the debt reopens but the goal remains completed is invalid.

### 18.4 Reversing ordinary portions

If a mixed payment contained ordinary money, reversal restores those wallet outflows and the debt balance as part of the same bundle. Only the goal-funded portion restores reservations and goal progress.

### 18.5 Reversing charges, forgiveness, and corrections

These events normally have only a debt-ledger inverse. However, when the original event caused automatic goal completion or release, those lifecycle effects must belong to the same bundle and must also reverse.

Example: forgiveness closes the debt and releases reservations. Reversing forgiveness must reopen the debt and reopen/restore the goal state if restoration is feasible.

### 18.6 Reversal feasibility

A reversal is allowed only when all linked effects can be restored without violating current wallet balances, currency rules, or reservation constraints.

If released money has since been spent or reallocated and the prior protection cannot be restored, block the reversal and explain:

> This action cannot be reversed because money released by it has since been used or reallocated. Use Correct balance or another explicit adjustment.

### 18.7 Reversal atomicity

Either the entire inverse bundle succeeds, or no state changes.

---

## 19. UI specification

### 19.1 Goal card actions

Active goal:

- `Reserve money`
- `Unreserve`
- `Prepare payment`
- `Record debt payment`
- `View activity`
- `Finish goal early` for partial mode where applicable
- `Archive/Cancel` through an explicit release flow

### 19.2 No mode-selection buttons

Do not ask:

- “Did you pay from goal wallets?”
- “Did you pay from another wallet?”
- “Was it mixed?”

Ask only:

> Which wallets actually paid, and how much from each?

### 19.3 Plain-language attribution

Use:

```text
From debt savings
From ordinary money
```

Do not expose Direct, OffWallet, Mixed, local invariant, or settlement-mode terminology.

### 19.4 Step 2 confirmation language

The preview must explicitly say:

```text
Creditor receives: X
Debt: before -> after
From debt savings: Y
From ordinary money: Z
Reservations after: ...
Goal status after: ...
```

### 19.5 Completed card

A completed goal must show its reason accurately. Do not display `100% funded` when the debt closed mainly through ordinary money.

Examples:

```text
Completed - Target paid
Completed - Debt closed
Completed early
```

---

## 20. Validation and error behavior

Block completion when:

- debt is closed or non-positive before payment;
- payment total is zero;
- payment total exceeds current debt balance;
- a wallet lacks real spendable balance;
- `U_i > P_i`;
- `U_i > R_i`;
- partial total goal use exceeds remaining goal capacity;
- currency normalization fails;
- goal is inactive, completed, or linked to a different debt;
- state changed after preview and revalidation fails.

Never partially apply a failed payment.

Recommended messages:

```text
This wallet has only X reserved for this debt goal.
The debt has only X remaining.
This partial goal can use only X more from debt savings.
Wallet balance changed while this payment was open. Review the updated amounts.
```

---

## 21. Audit data requirements

### 21.1 Goal record

Store at least:

- goal id;
- linked debt id;
- mode;
- original partial target, if applicable;
- status;
- completion reason;
- achieved amount for early finish;
- created and completed timestamps.

### 21.2 Payment bundle

Store at least:

- bundle id;
- debt id;
- goal id, if used;
- payment date;
- total payment `Q`;
- total goal-funded `U`;
- total ordinary `O`;
- debt before and after;
- note;
- actor and idempotency key.

### 21.3 Payment leg

For each wallet:

- wallet id;
- real payment `P_i`;
- goal-funded `U_i`;
- ordinary `O_i`;
- wallet balance before and after;
- reservation before and after.

### 21.4 Lifecycle effects

Store explicit linked events for:

- reservation consumption;
- reservation release;
- completion;
- reopening;
- reversal relationships.

Derived totals must be reproducible from active, non-reversed ledger events.

---

## 22. Atomicity, idempotency, and concurrency

### 22.1 Atomicity

Payment, completion, release, and reversal must occur in one database transaction.

### 22.2 Idempotency

The Complete button must submit an idempotency key. A retry must return the existing bundle rather than record a duplicate payment.

### 22.3 Concurrency

Lock or version-check:

- linked debt;
- active goal;
- all payment wallets;
- all affected goal allocations.

Recalculate `D`, `R_i`, and remaining target capacity immediately before commit.

### 22.4 Ordering

Wallet input order must not affect final totals. It may affect the proposed distribution of `U_i`, but the exact distribution is visible and user-adjustable before confirmation.

---

## 23. Scalability

The model supports any number of payment and reservation wallets.

For `N` payment rows, validation and settlement are linear:

```text
O(N)
```

Do not implement wallet-count-specific branches. The engine processes payment legs using the same per-wallet equations.

---

## 24. Minimum acceptance-test matrix

### Creation

- open debt owed by user is accepted;
- incoming debt is rejected;
- closed debt is rejected;
- second active goal for same debt is rejected;
- partial target above debt balance is rejected.

### Reservation

- one-wallet reserve;
- multi-wallet reserve;
- insufficient free money;
- unreserve partial and full;
- no debt balance change.

### Payment

- one reserved wallet, fully goal-funded;
- multiple reserved wallets;
- entirely ordinary OffWallet payment;
- same wallet payment above reservation;
- mixed multi-wallet payment;
- payment equal to debt balance;
- payment above debt balance rejected;
- partial target cap enforced only on `U`, not `Q`;
- 2M partial goal inside 10M debt payoff;
- user reduces smart default goal use to zero.

### Completion

- partial target paid while debt remains;
- debt closes before target paid;
- finish partial goal early at 2.9M of 3M;
- leftover reservations released;
- new goal allowed after completion.

### Debt changes

- charge increases full-mode readiness requirement;
- charge does not grow partial target;
- forgiveness shrinks debt without increasing paid-through-goal;
- correction can close debt and complete goal;
- metadata edit has no financial effect.

### Reversal

- fully goal-funded payment reversal;
- mixed payment reversal;
- reversal reopens goal;
- release restoration;
- impossible restoration blocks reversal;
- forgiveness reversal reopens debt and linked goal when feasible.

### Reliability

- duplicate Complete request is idempotent;
- concurrent wallet change causes revalidation;
- no partial mutation after any failure.

---

## 25. Final normative rules

1. A Debt Savings goal protects exact money in exact wallets for a linked debt the user owes.
2. The debt ledger alone owns the debt balance.
3. The payment wizard records reality from any wallet or wallet combination.
4. The user never selects Direct, OffWallet, or Mixed.
5. Each payment leg is split into goal-funded and ordinary amounts.
6. Goal-funded amount cannot exceed the same wallet's reservation.
7. A partial goal caps goal-funded amount, not the total real payment.
8. The full real payment reduces the debt exactly once.
9. Only goal-funded amounts consume reservations and increase paid-through-goal.
10. Ordinary debt payments never consume reservations.
11. Debt Savings has no post-payment reimbursement in v1.
12. Prepare Payment is optional and only occurs before the creditor payment.
13. Full mode completes when the debt closes.
14. Partial mode completes when its effective target is paid, the debt closes, or the user finishes early.
15. Completion releases all remaining reservations.
16. Progress displays debt remaining, reserved now, and paid through goal as separate truths.
17. Any debt event that causes goal lifecycle effects must bundle those effects for reversal.
18. Reversing a payment must restore debt, wallets, reservations, progress, and goal status together.
19. Every mutation is atomic, idempotent, auditable, and revalidated at commit time.
20. The model scales to any number of wallets without brute-force cases.
