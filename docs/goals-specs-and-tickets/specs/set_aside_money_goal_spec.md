# Set Aside Money Goal Specification

**Goal type:** Set Aside Money / Reserve Fund
**Backend intent:** `RESERVE`
**Frontend labels:** `Set aside money`, `Reserve fund`
**Status:** Canonical merged spec for implementation
**Date:** July 14, 2026
**Merged from:**

- `set_aside_money_goal_spec_v1.md`
- `Set_Aside_Money_Payment_Specification_v1.md`

---

## Problem Statement

Sarflog needs one canonical specification for Set Aside Money goals so the
feature can be split into implementation tickets without losing the accounting
rules that make reserve goals different from planned purchases, debts, ordinary
expenses, and generic transfers.

A user may reserve money for an ongoing purpose such as emergency needs,
medical support, family support, car maintenance, home repairs, gifts, or annual
obligations. That money still physically exists inside specific wallets, but it
is protected from ordinary spending. When the user later pays an expense, the
app must distinguish between:

1. money that actually came from the reserve;
2. ordinary wallet money used for the same purpose;
3. real post-purchase reimbursement from reserve money;
4. the expense's category spending;
5. the portion that should affect the monthly category budget.

The risk is that implementation might treat a reserve as an abstract allowance.
That would let the app silently reduce reserve protection in one wallet merely
because another wallet paid a related expense. For a money-tracking product,
that would make wallet balances, reserve allocations, expense funding, and
budget reports drift away from what really happened.

---

## Solution

Set Aside Money is a persistent, wallet-bound reserve goal. It protects exact
money in exact wallets. Reaching the target means `Fully reserved`, not
completed. Using part of the reserve does not close the goal. The goal remains
active and may be refilled repeatedly.

The central product principle is:

> A reserve is consumed only when protected money actually leaves a wallet that
> currently holds that reserve, either through direct reserve expense use or a
> real reimbursement transfer.

The user records the real payment wallets. Sarflog proposes how much of each
payment leg can use reserve money from that same wallet, treats the rest as
ordinary spending, and shows every consequence before completion.

Set Aside Money also supports a post-purchase `Reimburse from Reserve` action.
That action transfers real money from reserve-holding wallets to the wallet or
wallets that already paid an ordinary-funded expense, consumes the corresponding
reserve allocations, and updates the original expense's reserve coverage and
monthly budget impact.

The model preserves four truths:

1. **Wallet truth:** which wallet physically lost or received money.
2. **Reserve truth:** which wallet currently protects how much for the reserve.
3. **Expense truth:** how much was actually spent and in which category.
4. **Budget truth:** how much of the expense consumed the ordinary monthly category plan.

---

## User Stories

1. As a user, I want to create a Set Aside Money goal, so that I can protect money for an ongoing purpose.
2. As a user, I want creating a reserve goal to avoid moving wallet money automatically, so that my balances remain truthful.
3. As a user, I want to reserve money from a specific wallet, so that I know where protected money physically exists.
4. As a user, I want to return reserved money without spending it, so that I can make it ordinary free money again.
5. As a user, I want a reserve to remain active after reaching its target, so that it behaves like a persistent fund rather than a completed purchase.
6. As a user, I want a reserve to remain active after I use it, so that I can refill it later.
7. As a user, I want to record an expense paid directly from a reserve-holding wallet, so that the same wallet's balance and reserve allocation decrease together.
8. As a user, I want to split one expense across multiple wallets, so that real-world payments are represented accurately.
9. As a user, I want one wallet to pay above its reserve allocation and have the excess treated as ordinary money, so that large same-wallet payments are supported truthfully.
10. As a user, I want a wallet with no reserve allocation to pay an expense as ordinary spending, so that related-purpose expenses do not falsely consume reserve money.
11. As a user, I want Sarflog to propose reserve use from eligible wallets, so that the common case is easy.
12. As a user, I want to reduce proposed reserve use to zero, so that I can preserve the reserve intentionally.
13. As a user, I want the app not to ask me to choose Direct, OffWallet, or Mixed, so that I record what happened instead of diagnosing accounting modes.
14. As a user, I want to see a preview before completing a reserve expense, so that I understand balance, reserve, and budget consequences.
15. As a user, I want full expense amount to remain visible in category spending, so that reports show what I actually spent.
16. As a user, I want only the ordinary-funded portion to affect the monthly category budget, so that reserve-covered emergencies do not consume ordinary budget capacity.
17. As a user, I want reimbursement to restore the budget capacity of the original expense period, so that a July reimbursement for a June expense fixes June's budget impact.
18. As a user, I want to prepare payment before a purchase, so that reserve money can be moved to the wallet the merchant accepts.
19. As a user, I want Prepare Payment to move both real money and reserve protection, so that the destination wallet can later use the reserve directly.
20. As a user, I want Prepare Payment not to count as an expense or income, so that budget and reports stay clean.
21. As a user, I want to reimburse an existing ordinary expense from reserve money, so that a reserve can truthfully cover something paid earlier.
22. As a user, I want reimbursement to transfer real money from reserve source wallets to original payment wallets, so that wallet history matches reality.
23. As a user, I want reimbursement not to be income or a second expense, so that reports do not double count.
24. As a user, I want partial reimbursement, so that I can cover only part of an ordinary-funded expense.
25. As a user, I want multiple reserve source wallets to reimburse one expense, so that reserves split across wallets can be used naturally.
26. As a user, I want multiple payment destination wallets to be reimbursed, so that split payments can be corrected fairly.
27. As a user, I want reimbursement to be blocked when it exceeds the remaining ordinary-funded portion, so that reserve coverage never exceeds the expense.
28. As a user, I want source wallets to be limited by their reserve allocations, so that one wallet cannot consume another wallet's protection.
29. As a user, I want reversals to restore wallets, allocations, expense coverage, and budget impact together, so that mistakes can be corrected safely.
30. As a product owner, I want Set Aside Money to scale to any number of wallets, so that implementation does not grow wallet-count-specific cases.
31. As an implementer, I want payment legs, allocation events, and reimbursement links to be source of truth, so that classifications and metrics can be derived reliably.

---

## Implementation Decisions

### 1. Locked v1 Decisions

1. A Set Aside Money goal is exact protected money located in specific wallets.
2. The backend intent is `RESERVE`.
3. Creating the goal does not move wallet money.
4. The goal starts and remains `ACTIVE`.
5. Reaching the target displays `Fully reserved`; it does not complete the goal.
6. Using reserve money decreases `ProtectedNow` but does not complete the goal.
7. The primary expense action is `Record reserve expense` or `Use reserve`.
8. Record Reserve Expense uses one shared two-step wizard.
9. The user never selects Direct, OffWallet, or Mixed.
10. Any wallet may appear as a real expense-payment wallet.
11. Each wallet payment is split into reserve-covered and ordinary portions.
12. Only an explicitly selected amount from a wallet may consume that same wallet's reserve allocation.
13. Reserve use from a wallet cannot exceed the reserve held in that wallet.
14. If a wallet pays more than its reserve allocation, the excess is ordinary spending rather than an error.
15. A wallet without reserve allocation contributes ordinary spending.
16. Unused allocations remain protected after expense settlement.
17. Full expense amount appears in category spending reports.
18. Only the ordinary-funded portion consumes the monthly category budget limit.
19. Prepare Payment is an optional real transfer before the purchase.
20. Reimburse from Reserve is a real transfer after an existing expense and is unique to Set Aside Money in v1.
21. Reimbursement is not a second expense and not income.
22. Reimbursement changes the original expense's reserve coverage and restores corresponding category-budget capacity.
23. Direct expense, reimbursement, edits, and reversals use linked atomic event bundles.
24. The model supports any number of wallets without brute-force cases.

### 2. Scope

Included:

- goal creation and lifecycle;
- reserve allocation and return;
- reserve-funded and ordinary-funded expense portions;
- one or multiple payment wallets;
- one wallet paying with both reserve and ordinary money;
- derived Direct, OffWallet, and Mixed descriptions;
- unified two-step reserve expense wizard;
- monthly category-budget interaction;
- Prepare Payment before purchase;
- post-purchase reimbursement;
- multi-source and partial reimbursement;
- reversals and edits;
- ledger events and audit data;
- validation, atomicity, idempotency, concurrency, and acceptance criteria.

Excluded:

- Planned Purchase terminal settlement;
- debt and installment payment logic;
- automatic inference that an expense should use a reserve;
- invisible cross-wallet reserve consumption;
- foreign-exchange conversion mechanics inside the reserve settlement engine;
- bank synchronization;
- automatic investment returns, target growth, or interest;
- completing the reserve merely because it reaches 100%.

### 3. Product Philosophy

**Persistent wallet-bound stock**

A reserve answers two questions at all times:

```text
How much protected reserve exists now?
In which wallets does that protected money exist?
```

Location is part of the financial truth. A reserve is not an abstract allowance
that can be silently consumed from any wallet.

**Purpose is not funding source**

An expense can match the reserve's purpose without using reserve money.

Example:

```text
Wallet A holds 500,000 Emergency Reserve.
Wallet B pays a 200,000 medical expense.
```

Immediately after payment:

```text
Wallet B balance: -200,000
Wallet A reserve: still 500,000
Reserve-covered amount: 0
```

The expense purpose is medical. The funding source is ordinary money.

**No invisible cross-wallet offset**

Sarflog must not reduce Wallet A's reserve merely because Wallet B paid. A later
reserve reimbursement must move real money from A to B if the user wants the
reserve to cover that expense.

**No automatic completion**

A reserve goal remains `ACTIVE` when:

- it reaches 100% of its target;
- money is used from it;
- it falls below its target;
- it is refilled after use.

`COMPLETED` is not a valid normal lifecycle state for this goal type.

### 4. Terminology

**Reserve goal**

A persistent goal with intent `RESERVE` that protects money for an ongoing
purpose.

**Target amount**

The desired current protection level of the reserve. It is a refill benchmark,
not a terminal completion threshold.

**Reserve-holding wallet**

A wallet with a positive current allocation to this reserve.

**Reserve allocation**

The amount inside one wallet currently protected for this reserve.

**Free money**

Wallet money not protected by any goal or obligation.

**Direct reserve use**

A real expense paid from a wallet that currently holds protection for this
reserve, where an explicitly selected amount from that same wallet consumes the
same wallet's reserve allocation.

**OffWallet expense**

A real expense paid from wallet money that does not consume protection from this
reserve. It is ordinary spending until a later reimbursement occurs.

**Mixed expense**

A single expense with both reserve-funded and ordinary-funded portions. This can
happen across multiple wallets or within one wallet that pays above the amount
selected from reserve.

**Prepare Payment**

A pre-purchase operation that transfers real money and relocates reserve
protection to the wallet expected to pay.

**Reimburse from Reserve**

A post-purchase operation that transfers real money from reserve-holding
wallets to wallets that already paid an expense, consumes the corresponding
reserve allocations, and changes the original expense's funding attribution.

**Reserve-covered amount**

The portion of an expense currently attributed to this reserve through direct
reserve use and/or linked reimbursements.

**Ordinary-funded amount**

The portion of an expense not covered by a reserve.

### 5. Mathematical Model

For each wallet `i`:

```text
B_i = real wallet balance before an operation
R_i = current amount protected for this reserve in wallet i
H_i = amount protected for all other goals and obligations in wallet i
P_i = real expense payment made from wallet i
U_i = portion of P_i explicitly funded from this reserve
O_i = ordinary portion of P_i
T_i = real transfer amount sent from reserve wallet i during reimbursement
A_i = amount newly allocated to this reserve in wallet i
```

For each payment leg:

```text
P_i = U_i + O_i
0 <= U_i <= min(P_i, R_i)
O_i >= 0
```

Global values:

```text
Target = reserve target amount
ProtectedNow = sum(R_i)
TotalExpense = sum(P_i)
DirectReserveCovered = sum(U_i)
ReimbursedReserveCovered = sum(active linked reimbursements)
ReserveCovered = DirectReserveCovered + ReimbursedReserveCovered
OrdinaryFunded = TotalExpense - ReserveCovered
RefillNeeded = max(Target - ProtectedNow, 0)
FullyReserved = ProtectedNow >= Target
```

Wallet free money before an allocation operation:

```text
Free_i = B_i - R_i - H_i
```

System-wide wallet safety invariant:

```text
For every wallet i:
B_i >= R_i + H_i
```

After all active operations, wallet balances must still preserve remaining
protections, subject to the application's treatment of current-transaction
consumption.

All amounts must use the same normalized settlement currency before these
formulas are applied.

### 6. Lifecycle and State Rules

**Creation**

Creating a reserve goal:

- creates the goal record;
- stores title, target amount, intent, currency, and optional template metadata;
- does not move wallet money;
- does not create a reserve allocation unless allocation is part of the same atomic workflow;
- starts with `ProtectedNow = 0` unless allocations are created in the same workflow;
- sets status to `ACTIVE`.

**Target date**

A reserve goal must not require or accept a terminal target date in v1.

**Fully reserved**

When:

```text
ProtectedNow >= Target
```

the UI may display `Fully reserved`, but the goal remains `ACTIVE`.

**After use**

After reserve use:

- the goal remains `ACTIVE`;
- only consumed allocations decrease;
- unrelated allocations remain protected;
- `RefillNeeded` is recomputed;
- cumulative consumed metrics may increase.

**Manual completion**

The backend must reject manually changing a reserve goal to `COMPLETED`.

**Deactivation, archive, or deletion**

If the product supports deactivation, archive, or deletion, remaining
allocations must first be explicitly returned to the original wallets'
free-money state. No protection may disappear silently.

### 7. Reserve Allocation Ledger

The reserve allocation ledger supports at least three contribution types.

**ALLOCATE**

Meaning: protect additional money in a wallet for this reserve.

Effect:

```text
R_i_after = R_i_before + amount
B_i_after = B_i_before
```

**RETURN**

Meaning: remove protection without spending the money.

Effect:

```text
R_i_after = R_i_before - amount
B_i_after = B_i_before
```

The money remains in the same wallet and becomes free.

**CONSUME**

Meaning: protected money actually leaves the reserve-holding wallet through
direct reserve expense use or reimbursement.

Effect for direct use or reimbursement source wallet:

```text
R_i_after = R_i_before - amount
B_i_after = B_i_before - amount
```

`CONSUME` must never exceed the wallet's current reserve allocation.

At any time:

```text
R_i = sum(ALLOCATE_i) - sum(RETURN_i) - sum(CONSUME_i)
```

Only active, non-reversed ledger rows participate in this calculation.

### 8. Reserve Money Operation

The user explicitly chooses a wallet and amount to protect.

Validation:

```text
amount > 0
wallet is eligible to fund goals
wallet currency matches or is normalized to goal currency
amount <= wallet free money
```

where:

```text
wallet free money = real balance - all existing protected amounts
```

Settlement:

- create an `ALLOCATE` ledger row;
- do not change the wallet's real balance;
- increase `ProtectedNow`;
- recompute `RefillNeeded` and `FullyReserved`.

The operation must be atomic and idempotent.

### 9. Return Reserved Money Operation

The user may explicitly unprotect part of the reserve without spending it.

Validation:

```text
0 < return amount <= R_i
```

Settlement:

- create a `RETURN` ledger row;
- keep the real wallet balance unchanged;
- reduce the wallet's reserve allocation;
- increase the wallet's free money by the same amount;
- keep the goal `ACTIVE`.

Returning money is not income, not an expense, and not a wallet transfer.

### 10. Unified Record Reserve Expense Wizard

Record Reserve Expense uses a two-step wizard.

**Step 1: Record what actually happened**

The user enters:

- expense date;
- category and optional subcategory;
- merchant/payee and note, if applicable;
- one or more wallets that actually paid;
- real amount paid from each wallet;
- amount from each paying wallet that should use this reserve.

Each payment row displays:

```text
Wallet name
Real balance
Protected for this reserve
Amount paid
Use from reserve
Ordinary portion (derived)
```

The user is never asked to select Direct, OffWallet, or Mixed.

**Smart default**

When launched from the reserve goal card:

```text
proposed_U_i = min(P_i, R_i)
```

The user may reduce `U_i`, including to zero, when they intentionally want to
preserve the reserve and use ordinary money.

For a wallet with no reserve allocation:

```text
R_i = 0
U_i = 0
O_i = P_i
```

**Same wallet above reserve**

Example:

```text
Cash reserve: 1,000,000
Cash paid:    1,400,000
```

Proposed split:

```text
Use from reserve: 1,000,000
Ordinary money:     400,000
```

The real expense is allowed if the wallet has sufficient usable balance. The
reserve-funded portion remains locally capped.

**Step 1 validation**

For each row:

```text
P_i > 0
P_i <= wallet valid real outflow capacity
0 <= U_i <= P_i
U_i <= R_i
```

Also validate category, date, currency, goal status, and duplicate submission
rules.

**Step 2: Review consequences**

The review must show:

- total expense;
- reserve-covered amount;
- ordinary-funded amount;
- monthly category-budget impact;
- real wallet balance changes;
- reserve-allocation changes per wallet;
- `ProtectedNow` after;
- `RefillNeeded` after;
- goal remains active;
- whether an ordinary portion remains eligible for later reimbursement.

Example:

```text
Total expense: 1,600,000 UZS
Covered by Family Support reserve: 1,000,000 UZS
Paid with ordinary money: 600,000 UZS
Monthly Health budget impact: 600,000 UZS

Cash balance: -1,000,000
Cash reserve: 3,000,000 -> 2,000,000
Humo balance: -600,000
Goal status: Active
```

The final action is `Complete expense`.

Step 2 must be produced by the same backend policy engine used for completion.
Completion revalidates all state and commits atomically.

### 11. Derived Payment Patterns

The labels are for audit and analytics, not user selection.

**Direct reserve-funded**

```text
ReserveCovered = TotalExpense
```

Every expense portion is explicitly covered by reserve held in the same payment
wallets.

**OffWallet or fully ordinary**

```text
ReserveCovered = 0
OrdinaryFunded = TotalExpense
```

No reserve allocation is consumed.

**Mixed reserve and ordinary**

```text
ReserveCovered > 0
OrdinaryFunded > 0
```

This may occur across multiple wallets or inside one wallet that pays above the
amount used from reserve.

All patterns use the same per-wallet equations:

```text
wallet balance decreases by P_i
reserve allocation decreases by U_i
ordinary portion equals P_i - U_i
```

### 12. Direct Reserve Use

The native reserve-use operation may use only explicitly selected amounts from
wallets that currently hold enough protection for this reserve.

For every reserve-funded payment leg:

```text
0 <= U_i <= P_i
U_i <= R_i
```

When a leg is fully reserve-funded:

```text
0 < P_i <= R_i
U_i = P_i
```

A wallet cannot use another wallet's reserve allocation.

Settlement for every payment wallet:

```text
B_i_after = B_i_before - P_i
R_i_after = R_i_before - U_i
```

Only the selected `U_i` amount creates a reserve `CONSUME` event.

Canonical multi-wallet example:

```text
Starting reserve:
A: 3,000,000 protected
B: 2,000,000 protected
C: 5,000,000 protected

Expense:
A pays 1,000,000; U_A = 1,000,000
B pays   500,000; U_B =   500,000
C pays 2,000,000; U_C = 2,000,000

Result:
A reserve: 2,000,000
B reserve: 1,500,000
C reserve: 3,000,000
Total reserve used: 3,500,000
Ordinary-funded: 0
Budget impact: 0
Goal remains active
```

Strict behavior for oversized same-wallet expense:

```text
Wallet A reserve: 300,000
Wallet A pays:    500,000
```

Valid v1 options:

1. record `U_A = 300,000` and `O_A = 200,000` through explicit split funding;
2. record the whole expense as ordinary and reimburse up to 300,000 afterward;
3. prepare additional reserve money before the purchase.

The engine must never silently consume more than `R_i`.

### 13. OffWallet Ordinary Expense

An OffWallet expense is paid from wallet money that is not consumed from this
reserve.

Example:

```text
Family Support reserve:
Wallet A: 500,000 protected

Actual expense:
Wallet B pays 200,000
U_B = 0
```

Immediate result:

```text
Wallet B balance: -200,000
Wallet A reserve: unchanged at 500,000
ReserveCovered: 0
OrdinaryFunded: 200,000
BudgetImpact: 200,000
```

The user may have spent on a family-support purpose, but the protected reserve
was not physically used.

The application must not:

- reduce Wallet A's reserve allocation invisibly;
- invent a historical transfer from Wallet A to Wallet B;
- classify the payment as reserve-funded merely because it was an emergency or reserve-related purpose;
- automatically infer a reserve goal from the expense category.

The expense may be reimbursed later through the dedicated `Reimburse from Reserve`
action.

### 14. Mixed Expense

A mixed expense has both reserve-funded and ordinary-funded portions.

Across-wallet example:

```text
Wallet A reserve: 500,000
A pays 200,000; U_A = 200,000
B pays 300,000; U_B = 0

Total expense: 500,000
Reserve-covered: 200,000
Ordinary-funded: 300,000
Budget impact: 300,000
A reserve becomes 300,000
B reserve unchanged at 0
```

Same-wallet example:

```text
Wallet A reserve: 300,000
Wallet A pays:    500,000
U_A:              300,000
O_A:              200,000
```

The same wallet loses 500,000 in real balance, but only 300,000 is reserve
consumption.

Any remaining ordinary portion may be reimbursed later, subject to source
reserve and destination limits.

### 15. Monthly Category-Budget Interaction

Every expense must preserve two reporting truths:

```text
CategoryActualSpending = TotalExpense
MonthlyBudgetImpact = OrdinaryFunded
```

Universal formula:

```text
MonthlyBudgetImpact = TotalExpense - ReserveCovered
0 <= ReserveCovered <= TotalExpense
```

The full expense always appears in category spending and reports. Only the
portion not covered by the reserve consumes the monthly category budget limit.

Direct reserve use example:

```text
Health expense: 1,200,000
ReserveCovered: 1,200,000
CategoryActualSpending: 1,200,000
MonthlyBudgetImpact: 0
```

OffWallet expense before reimbursement:

```text
Health expense: 1,200,000
ReserveCovered: 0
CategoryActualSpending: 1,200,000
MonthlyBudgetImpact: 1,200,000
```

Mixed expense:

```text
Expense: 600,000
ReserveCovered: 200,000
OrdinaryFunded: 400,000
CategoryActualSpending: 600,000
MonthlyBudgetImpact: 400,000
```

Reimbursement restores budget capacity:

```text
NewMonthlyBudgetImpact = OldMonthlyBudgetImpact - ReimbursementAmount
```

The result must never be negative.

Reimbursement changes the funding attribution of the original expense.
Therefore, budget impact must be recomputed for the original expense's budget
period, not the reimbursement transfer date.

Example:

- expense date: June 28;
- reimbursement date: July 3.

The June category budget impact is reduced. The reimbursement must not appear as
July income and must not consume or restore an unrelated July category budget.

If historical periods can be locked, the product must either reject
reimbursement against a locked period or create an explicit adjustment policy.
Silent divergence is prohibited.

### 16. Prepare Payment

Prepare Payment is used before the real purchase when the intended payment
wallet does not currently hold enough of the reserve.

For each preparation transfer leg from source wallet `s` to destination wallet
`d`:

```text
amount > 0
amount <= R_s
source balance decreases by amount
destination balance increases by amount
source reserve allocation decreases by amount
destination reserve allocation increases by amount
```

Ledger representation:

- real internal transfer `source -> destination`;
- `RETURN` or equivalent relocation-out row on the source allocation;
- `ALLOCATE` or equivalent relocation-in row on the destination allocation;
- common preparation/relocation identifier linking all records.

Conservation invariants:

```text
sum(source transfer amounts) = sum(destination received amounts)
sum(reserve allocation decreases) = sum(reserve allocation increases)
ProtectedNow after = ProtectedNow before
```

Prepare Payment:

- does not consume the reserve;
- does not change `RefillNeeded`;
- is not an expense;
- is not income;
- does not affect monthly budget;
- is a real internal wallet transfer plus reserve-location relocation.

After preparation, the destination wallet can perform direct reserve use.
Prepare Payment must not be automatically invented after the purchase occurred.

### 17. Reimburse from Reserve

Reimbursement is used after an ordinary or partially ordinary expense has
already happened.

It truthfully records:

1. the original payment wallet paid the merchant;
2. reserve-holding wallet or wallets later compensated that payment wallet;
3. protected reserve money actually left the source reserve wallet or wallets;
4. the original expense became partially or fully reserve-covered.

Reimbursement performs:

```text
real internal transfer
+ reserve allocation consumption
+ funding attribution update on original expense
+ category-budget impact restoration
```

It does not create another expense, income, or merchant payment.

**Entry points**

Primary:

```text
Expense details -> Reimburse from reserve
```

Secondary:

```text
Reserve goal card -> Reimburse an expense
```

The generic Wallet Transfer page must not be the primary creator of
reimbursement because reimbursement requires goal and expense context. The
resulting transfer may still appear in wallet histories.

**Eligible expense**

An expense is eligible when:

- it exists and is not deleted or reversed;
- it represents a real expense, not income or an internal transfer;
- it has an ordinary-funded amount greater than zero;
- its currency is compatible with the reserve reimbursement operation;
- it is not already fully reserve-covered;
- the selected destination wallet participated in paying the expense, unless a future policy explicitly supports reimbursement to an external person or account.

Remaining reimbursable amount:

```text
RemainingReimbursable = TotalExpense - ReserveCovered
```

Validation:

```text
0 < ReimbursementAmount <= RemainingReimbursable
```

For each destination payment wallet `d`:

```text
ReimbursementTo_d <= amount originally paid by d
                         - prior active reimbursements to d
                         - direct reserve coverage already attributed to d
```

For every reserve source wallet `s`:

```text
0 < SourceAmount_s <= R_s
```

The source wallet must have enough real balance after respecting all other
protected amounts. Because the reimbursement consumes this reserve allocation,
the post-operation invariant must hold:

```text
B_s - SourceAmount_s >= H_s + (R_s - SourceAmount_s)
```

Reimbursement conservation:

```text
sum(SourceAmount_s) = sum(ReimbursementTo_d) = ReimbursementAmount
```

Settlement for each source reserve wallet:

```text
B_s_after = B_s_before - SourceAmount_s
R_s_after = R_s_before - SourceAmount_s
```

Create a `CONSUME` row for each source amount.

Settlement for each destination payment wallet:

```text
B_d_after = B_d_before + ReimbursementTo_d
```

Create real internal transfer records linking sources and destinations.

For the original expense:

```text
ReserveCovered_after = ReserveCovered_before + ReimbursementAmount
OrdinaryFunded_after = TotalExpense - ReserveCovered_after
```

Partial reimbursement is valid. Further reimbursements may occur until:

```text
OrdinaryFunded = 0
```

The model supports any number of reserve source wallets and payment destination
wallets. Business correctness depends on aggregate conservation and per-wallet
limits, not wallet counts.

### 18. Canonical Family Support Example

Starting allocations:

```text
brandnewGoalWallet1 - CASH: 3,000,000 UZS protected
brandnewGoalWallet2 - CASH: 2,000,000 UZS protected
Cash - DEBIT:               5,000,000 UZS protected
Target:                    10,000,000 UZS
ProtectedNow:              10,000,000 UZS
RefillNeeded:                       0 UZS
Status: ACTIVE / Fully reserved
```

**Direct use**

`Cash - DEBIT` directly pays 1,200,000 UZS for medicine.

Result:

```text
Cash - DEBIT real balance:       -1,200,000
Cash - DEBIT reserve: 5,000,000 -> 3,800,000
Other reserve allocations: unchanged
ProtectedNow: 8,800,000
RefillNeeded: 1,200,000
Category actual spending: 1,200,000
Monthly category budget impact: 0
Goal status: ACTIVE
```

**OffWallet expense**

An Everyday Humo wallet that holds no Family Support reserve pays 1,200,000 UZS.

Immediate result:

```text
Everyday Humo real balance:      -1,200,000
Family Support ProtectedNow:     10,000,000
ReserveCovered:                           0
Monthly category budget impact:  1,200,000
Goal status: ACTIVE / Fully reserved
```

**Full reimbursement**

The user selects:

```text
Expense: medicine purchase paid by Everyday Humo
Reserve: Family Support
Source: Cash - DEBIT
Destination: Everyday Humo
Amount: 1,200,000 UZS
```

Settlement:

```text
Cash - DEBIT real balance:       -1,200,000
Cash - DEBIT reserve: 5,000,000 -> 3,800,000
Everyday Humo real balance:      +1,200,000
ProtectedNow: 8,800,000
RefillNeeded: 1,200,000
ReserveCovered on expense: 1,200,000
Monthly category budget impact: 0
Category actual spending: 1,200,000
```

Transaction history preserves both events:

1. Everyday Humo -> Pharmacy: 1,200,000 UZS expense.
2. Cash - DEBIT -> Everyday Humo: 1,200,000 UZS reserve reimbursement.

**Multi-source reimbursement**

The same 1,200,000 UZS expense may be reimbursed by:

```text
Cash - DEBIT:               700,000
brandnewGoalWallet2 - CASH: 500,000
```

Results:

```text
Cash - DEBIT balance and reserve:       -700,000
brandnewGoalWallet2 balance and reserve: -500,000
Everyday Humo receives:                1,200,000
Total reserve consumed:                1,200,000
```

The behavior is identical regardless of the number of source wallets.

### 19. UI and Interaction Specification

Recommended goal card actions:

- `Reserve money`
- `Unreserve` or `Return reserved money`
- `Prepare payment`
- `Record reserve expense` or `Use reserve`
- `Reimburse an expense`
- `View allocations and activity`
- `Archive` through an explicit release flow

Do not ask:

- paid from goal wallets;
- paid from another wallet;
- mixed.

Ask:

> Which wallets actually paid, and how much from each?

Then show adjustable `Use from reserve` amounts.

Plain-language summary labels:

```text
Covered by reserve
Paid with ordinary money
Monthly budget impact
```

Do not expose internal mode names in the main user flow.

When `ReserveCovered = 0`, Step 2 should state:

> This expense uses ordinary wallet money. The reserve remains unchanged. You
> can reimburse the paying wallet later.

Expense details should show `Reimburse from reserve` when:

```text
OrdinaryFunded > 0
```

The reimbursement flow asks for:

1. reserve goal;
2. reimbursement amount;
3. reserve source wallet or wallets;
4. destination payment wallet or wallets, prefilled from the expense;
5. confirmation summary.

Reimbursement confirmation must show:

- original expense;
- source reserve wallets and balance changes;
- destination wallet credits;
- reserve coverage before and after;
- monthly budget impact before and after;
- `ProtectedNow` after.

Wallet history may display reimbursement transactions with metadata:

```text
Reserve reimbursement
Cash - DEBIT -> Everyday Humo
1,200,000 UZS
Reserve: Family Support
Linked expense: Pharmacy
```

Eligible wallet filtering:

- `Use reserve` shows only wallets with `R_i > 0` for reserve-use portions, while ordinary payment rows may use any valid payment wallet.
- `Prepare payment` shows source wallets with `R_i > 0` and eligible destination wallets.
- `Reimburse from reserve` shows source wallets with `R_i > 0` and payment wallets linked to the selected expense that still have an unreimbursed ordinary portion.

Before mutation, confirmation summaries must show:

- real balance changes;
- reserve allocation changes;
- `ProtectedNow` after;
- `RefillNeeded` after;
- monthly budget impact before and after;
- linked expense and category.

### 20. Classification for Analytics and Audit

For a completed expense, classify current funding attribution using amounts,
not wallet names alone.

```text
ReserveCovered = direct coverage + active reimbursements
OrdinaryFunded = TotalExpense - ReserveCovered
```

Classification:

```text
If ReserveCovered = TotalExpense:
    DIRECT_RESERVE_FUNDED

If ReserveCovered = 0:
    ORDINARY_OFF_WALLET

If 0 < ReserveCovered < TotalExpense:
    MIXED_RESERVE_AND_ORDINARY
```

A later reimbursement may change the current classification over time:

```text
ORDINARY_OFF_WALLET -> MIXED_RESERVE_AND_ORDINARY -> DIRECT_RESERVE_FUNDED
```

The audit log must preserve that history even if the current derived
classification changes.

Classification must be reproducible from active funding attribution amounts. It
is not the sole source of truth.

### 21. Audit Data Requirements

**Reserve goal**

Store or derive:

- goal ID;
- intent `RESERVE`;
- title;
- target amount;
- currency;
- status;
- optional reserve template/type key;
- created and updated timestamps.

**Allocation ledger row**

Store:

- contribution ID;
- goal ID;
- wallet ID;
- type: `ALLOCATE`, `RETURN`, or `CONSUME`;
- amount;
- operation ID;
- linked expense ID when applicable;
- linked transfer ID when applicable;
- reversal reference when applicable;
- timestamp.

**Expense funding attribution**

For each expense, store or reliably derive:

- total expense amount;
- payment wallet legs;
- direct reserve coverage per wallet;
- reimbursement-covered amount;
- total reserve-covered amount;
- ordinary-funded amount;
- category actual spending;
- monthly budget impact;
- linked reserve goal ID;
- current derived funding classification.

**Reimbursement record**

Store:

- reimbursement bundle ID;
- original expense ID;
- reserve goal ID;
- total amount;
- source wallet transfer legs;
- destination wallet credit legs;
- reserve consumption per source;
- effective date and recorded date;
- original expense budget period;
- status: active or reversed;
- reversal link;
- idempotency key;
- timestamps.

### 22. Derived UI Metrics

Recommended formulas:

```text
ProtectedNow = sum(current R_i)
RefillNeeded = max(Target - ProtectedNow, 0)
FullyReserved = ProtectedNow >= Target
```

For `Used from reserve`, choose one clearly named metric.

Option A, cumulative lifetime consumption:

```text
UsedFromReserveLifetime = sum(active CONSUME amounts over goal lifetime)
```

Refilling does not reduce this historical usage number.

Option B, current target shortfall caused by use and returns:

```text
RefillNeeded = max(Target - ProtectedNow, 0)
```

Use the name `RefillNeeded`, not `Used from reserve`, for this metric. The UI
must not treat cumulative consumption and current refill need as the same value.

Reimbursement consumption is real reserve use and must be included in any
cumulative used-from-reserve metric.

### 23. Known Implementation Gap: Reserve Template Persistence

The reserve-type picker may offer choices such as Emergency Fund or Medical
Reserve. If the UI only uses the selection to set the title, the semantic
template is lost.

Recommended v1 correction:

- send an optional stable field such as `reserve_template_key` or `template_id` in the creation payload;
- persist it independently from the user-editable title;
- use it only for defaults, analytics, icons, education, and future automation;
- do not let the template key change settlement accounting rules unless explicitly specified later.

This gap is separate from reserve settlement and must not block the accounting
implementation.

### 24. Atomicity, Idempotency, and Concurrency

Each domain operation must commit all related records together or none of them.

Examples:

- Direct use: expense, wallet postings, `CONSUME` rows, funding attribution, budget impact.
- Prepare Payment: transfers, source relocation rows, destination allocation rows.
- Reimbursement: transfers, `CONSUME` rows, reimbursement links, expense funding update, budget recomputation.

Write endpoints must accept or derive idempotency keys so retries cannot
duplicate:

- expenses;
- transfers;
- contribution rows;
- reimbursements;
- budget adjustments.

The operation must re-read and lock or version-check:

- goal;
- wallet balances;
- affected reserve allocations;
- original expense;
- expense remaining reimbursable amount;
- affected budget period.

Concurrent operations must not allow reserve allocation or expense reimbursement
to go below zero or above valid limits.

Input wallet order must not change classification or final results.

### 25. Reversals and Edits

**Direct reserve-expense reversal**

Reversing a direct reserve-funded expense must atomically:

- restore real wallet balances;
- reverse matching `CONSUME` rows;
- restore reserve allocations;
- reduce cumulative reserve consumption as defined by reporting policy;
- remove category actual spending and budget impact from the original period.

If the expense has linked reimbursements, they must be reversed first or included
in a dependency-aware full reversal.

**Reimbursement reversal**

Reversing reimbursement must atomically:

- reverse the internal transfer;
- restore source reserve allocations;
- reverse source `CONSUME` rows;
- reduce reserve coverage on the original expense;
- increase the original expense's ordinary-funded amount;
- reapply monthly budget impact to the original period.

**Expense edits**

An expense amount must not be edited below its active reserve-covered amount.
Before reducing or deleting such an expense, linked reimbursements or reserve
coverage must be adjusted or reversed.

A financial edit should be represented as reverse-and-replace or a linked
adjustment bundle, not silent mutation that destroys audit history.

If destination funds are no longer available, or restored reserve protection
would violate wallet truth, block reversal and require an explicit corrective
operation.

Every reversal must succeed completely or not at all.

Prefer reversal records over destructive deletion for posted financial events.

### 26. Validation Errors

Block reserve expense completion when:

- goal is not active;
- payment is zero;
- a payment wallet lacks valid real balance;
- `U_i > P_i`;
- `U_i > R_i`;
- category or date is invalid;
- currency normalization fails;
- a stale preview no longer matches current balances or allocations;
- duplicate idempotency key conflicts.

Block reimbursement when:

- original expense is missing, deleted, reversed, or fully reimbursed;
- requested amount exceeds remaining ordinary portion;
- source wallet lacks reserve allocation;
- source wallet lacks valid real balance after preserving other protection;
- destination is not a valid original payment wallet;
- currency rules fail;
- historical period policy forbids the required budget adjustment.

Recommended domain error meanings:

```text
This wallet has only {available} protected for this reserve.
This wallet does not have enough free money to reserve {amount}.
This expense is already fully covered by reserve funds.
You can reimburse up to {remaining} for this expense.
The selected destination wallet did not pay the linked expense.
This expense belongs to a locked budget period and cannot be reimbursed without an adjustment workflow.
Convert or normalize the amounts before using this reserve.
The reserve changed while the wizard was open. Review the updated amounts.
```

All errors must leave state unchanged.

### 27. Prohibited Behaviors

The implementation must not:

1. auto-complete a reserve when it reaches its target;
2. release unrelated allocations after reserve use;
3. silently consume reserve from a wallet that did not lose real money;
4. invent a pre-purchase transfer after the expense already happened;
5. treat reimbursement as income;
6. treat reimbursement as a second expense;
7. double-count category spending;
8. restore the current month's budget when the original expense belongs to another month;
9. let reserve coverage exceed the expense amount;
10. let a source wallet consume more than its reserve allocation;
11. infer reimbursement semantics from an ordinary wallet transfer;
12. use proportional, FIFO, or arbitrary hidden source allocation;
13. implement wallet-count-specific `if/else` branches;
14. mutate only part of a multi-record operation after an error;
15. classify an expense as reserve-funded merely because its category matches a reserve purpose;
16. ask the user to choose internal Direct, OffWallet, or Mixed modes in the main expense flow.

### 28. Complexity and Scalability

The model works for any number of wallets.

Direct use validates each payment leg once:

```text
Time complexity: O(N)
```

Reimbursement validates source and destination legs:

```text
Time complexity: O(S + D)
```

Where:

- `N` = number of direct payment legs;
- `S` = number of reimbursement source wallets;
- `D` = number of reimbursement destination wallets.

No combinatorial search, brute-force case enumeration, or wallet-count-specific
branching is required.

### 29. Canonical Implementation Sequences

**Direct reserve expense**

1. Normalize currency and aggregate payment legs.
2. Load and lock the goal, wallet balances, reserve allocations, and affected budget period.
3. Verify goal intent is `RESERVE` and status is `ACTIVE`.
4. Verify each payment leg is positive and within wallet real outflow capacity.
5. Verify every reserve-use amount is non-negative, does not exceed the payment leg, and does not exceed that wallet's reserve allocation.
6. Verify wallet post-balances preserve all remaining protections.
7. Create the expense and payment postings.
8. Create matching `CONSUME` rows for `U_i` amounts.
9. Compute expense reserve coverage and monthly budget impact.
10. Recompute goal metrics.
11. Commit atomically.

**Prepare Payment**

1. Normalize source and destination transfer legs.
2. Load and lock wallets and reserve allocations.
3. Validate source allocations and balances.
4. Validate total source amount equals total destination amount.
5. Create real transfer postings.
6. Create source relocation-out and destination allocation-in rows.
7. Verify total `ProtectedNow` is unchanged.
8. Commit atomically.

**Reimburse from Reserve**

1. Load and lock the reserve goal, expense, payment legs, wallets, allocations, and original budget period.
2. Derive remaining reimbursable amount.
3. Validate source reserve amounts and destination outstanding payment amounts.
4. Verify source total equals destination total and does not exceed remaining reimbursable amount.
5. Create real internal transfer postings.
6. Create source `CONSUME` rows.
7. Create reimbursement and expense-link records.
8. Increase expense reserve coverage.
9. Recompute ordinary-funded amount and original-period monthly budget impact.
10. Recompute reserve metrics.
11. Commit atomically.

---

## Testing Decisions

### Highest-Value Test Seam

The highest-value seam is the backend reserve policy used by both preview and
completion. Tests should verify observable behavior: preview output, persisted
expense/reimbursement bundles, wallet balances, reserve allocations, funding
attribution, budget impact, status, validation failures, reversal behavior, and
idempotency.

Frontend tests should focus on whether the wizard sends payment rows and
`Use from reserve` amounts, renders backend preview data, avoids manual mode
selection, and displays reimbursement/budget consequences correctly.

### Goal Lifecycle Matrix

Test:

- creating a reserve does not move money;
- reaching target does not complete the goal;
- using money does not complete the goal;
- manual completion is rejected;
- remaining allocations stay protected after use;
- archive/delete requires explicit release policy.

### Allocation Truth Matrix

Test:

- `ALLOCATE` increases protection without changing balance;
- `RETURN` decreases protection without changing balance;
- `CONSUME` decreases both balance and protection by the same amount;
- current wallet allocation equals allocations minus returns and consumes;
- no wallet's total protection exceeds its real balance;
- returning reserved money is not income, expense, or transfer.

### Unified Expense Wizard Matrix

Test:

- one reserve wallet fully covers an expense;
- multiple reserve wallets cover an expense;
- entirely OffWallet expense;
- mixed reserve and ordinary wallets;
- one wallet pays above local reserve and excess is ordinary;
- user reduces proposed reserve use;
- user sets reserve use to zero;
- `U_i > P_i` is rejected;
- `U_i > R_i` is rejected;
- step 2 matches backend settlement;
- stale preview is rejected.

### Budget Interaction Matrix

Test:

- fully reserve-covered expense has zero budget impact;
- ordinary expense has full budget impact;
- mixed expense has partial budget impact;
- category actual spending always shows full amount;
- reimbursement restores original-period budget capacity;
- partial reimbursement leaves partial budget impact;
- budget impact never becomes negative;
- locked-period policy is enforced.

### Prepare Payment Matrix

Test:

- real transfer and allocation relocation;
- total reserve conserved;
- source reserve allocation decreases;
- destination reserve allocation increases;
- no expense, income, consumption, or budget effect is created;
- destination can later use reserve directly.

### Reimbursement Matrix

Test:

- single source and destination;
- multiple sources;
- multiple destinations;
- partial reimbursement;
- reimbursement cannot exceed ordinary portion;
- source reserve insufficient;
- destination validation;
- not counted as expense or income;
- original expense funding attribution updates;
- original-period budget impact updates;
- goal remains active.

### Reversal and Edit Matrix

Test:

- direct expense reversal restores wallet balances and reserve allocations;
- reimbursement reversal restores transfer, source allocations, funding attribution, and budget impact;
- linked reimbursement dependency is enforced;
- expense cannot be edited below active reserve-covered amount;
- impossible restoration is blocked;
- idempotent reversal.

### Reliability Matrix

Test:

- duplicate completion does not duplicate records;
- concurrent reserve change revalidates;
- concurrent wallet balance change revalidates;
- concurrent reimbursement cannot over-cover an expense;
- wallet input order does not change classification or final results;
- any failure leaves all linked state unchanged;
- audit history remains available after reversals.

---

## Out of Scope

- Planned Purchase final settlement.
- Debt and installment settlement.
- Automatically detecting that an ordinary expense should use a reserve.
- Reducing a reserve because an expense category matches the reserve purpose.
- Hidden cross-wallet reserve consumption.
- Generic wallet transfer creating reimbursement semantics.
- Foreign-exchange conversion policy inside reserve settlement.
- Interest, investment return, or automatic target growth.
- Terminal completion when a reserve reaches 100%.
- Merchant refunds after reimbursement, except through a separately designed correction/refund flow.

---

## Further Notes

### Final Normative Rules

1. Set Aside Money is a persistent, wallet-bound reserve.
2. Reserve money remains inside specific wallets and is protected there.
3. Creating a reserve goal does not move money.
4. Reaching the target means fully reserved, not completed.
5. The goal stays active after allocation, use, reimbursement, return, and refill.
6. Any wallet may record a real expense payment.
7. The user never chooses Direct, OffWallet, or Mixed.
8. Each wallet payment is split into reserve-covered and ordinary amounts.
9. Reserve-covered amount cannot exceed that same wallet's reserve allocation.
10. Payment above local reserve is allowed; the excess is ordinary money.
11. Only reserve-covered amounts consume protection.
12. Ordinary portions leave reserve allocations unchanged.
13. OffWallet spending is ordinary spending until reimbursed.
14. Prepare Payment moves reserve money before the expense.
15. Reimburse from Reserve moves reserve money after the expense.
16. Reimbursement changes the original expense's funding attribution, not its spending amount.
17. Reimbursement is not income, not a second expense, and not a merchant payment.
18. Full expense amount appears in category reports.
19. Only the ordinary-funded portion consumes the monthly category budget.
20. Reimbursement restores original-period budget capacity.
21. Payment legs, allocation events, and reimbursement links are source of truth.
22. Payment and reimbursement previews use the same backend rules as completion.
23. All operations and reversals are atomic, idempotent, and auditable.
24. The model scales linearly to any number of wallets and requires no brute-force cases.

These rules are the source of truth for v1 implementation.
