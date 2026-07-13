# Set Aside Money (Reserve Fund) Goal

## Domain, Settlement, Reimbursement, and Monthly Budget Specification

**Version:** 1.0 - Implementation Ready  
**Backend intent:** `RESERVE`  
**Frontend labels:** `Set aside money`, `Reserve fund`  
**Status:** Normative product and accounting specification

---

## 1. Purpose

This document defines the complete v1 behavior of the **Set Aside Money** goal type, represented by the backend intent `RESERVE`.

A Set Aside Money goal is a **persistent, wallet-bound protection bucket**. It represents real money that still exists inside specific wallets but is protected from ordinary spending for an ongoing purpose such as:

- emergency fund;
- medical reserve;
- family support;
- car maintenance;
- home repairs;
- gifts or annual obligations;
- another irregular but recurring need.

A reserve is not a terminal purchase goal. Reaching the target means **fully reserved**, not completed. Using part of the reserve does not close the goal. The goal stays active and may be refilled repeatedly.

The central product principle is:

> A reserve is consumed only when protected money actually leaves a wallet that currently holds that reserve, either through a direct expense or a real reimbursement transfer.

This specification keeps four truths consistent:

1. **Wallet truth:** which wallet physically lost or received money.
2. **Reserve truth:** which wallet currently protects how much for the reserve.
3. **Expense truth:** how much was actually spent and in which category.
4. **Budget truth:** how much of the expense consumed the ordinary monthly category plan.

---

## 2. Scope

This specification covers:

- goal creation and lifecycle;
- reserving and returning money;
- direct reserve use;
- ordinary OffWallet expenses;
- mixed reserve and ordinary payment;
- Prepare Payment before a purchase;
- Reimburse from Reserve after a purchase;
- multiple source and payment wallets;
- monthly category budget impact;
- goal ledger events and audit data;
- validation, atomicity, reversals, and acceptance criteria.

This specification does not define:

- Planned Purchase settlement;
- debt or installment settlement;
- automatic investment returns or interest;
- foreign-exchange conversion mechanics;
- bank synchronization;
- automatic detection that an ordinary expense “should have” used a reserve.

---

## 3. Product philosophy

### 3.1 Persistent protected stock

A reserve answers two questions at all times:

- **How much protected reserve exists now?**
- **In which wallets does that protected money exist?**

The location is part of the financial truth. A reserve is not an abstract allowance that can be silently consumed from any wallet.

### 3.2 Purpose is not the same as funding source

An expense can have an emergency purpose without having used emergency-reserve money.

Example:

- Wallet A holds 500,000 UZS of Emergency Reserve.
- Wallet B pays a 200,000 UZS medical expense using ordinary free money.

The expense purpose is medical or emergency-related, but the reserve remains 500,000 UZS because no protected money left Wallet A.

### 3.3 No invisible cross-wallet accounting

The application must not silently reduce reserve protection in Wallet A merely because Wallet B paid an eligible expense.

To use Wallet A's reserve after Wallet B has already paid, the system must record a real reimbursement transfer from Wallet A to Wallet B.

### 3.4 No automatic completion

A reserve goal remains `ACTIVE` when:

- it reaches 100% of its target;
- money is used from it;
- it falls below its target;
- it is refilled after use.

`COMPLETED` is not a valid normal lifecycle state for this goal type.

---

## 4. Terminology

### 4.1 Reserve goal

A persistent goal with intent `RESERVE` that protects money for an ongoing purpose.

### 4.2 Target amount

The desired current protection level of the reserve. It is a refill benchmark, not a terminal completion threshold.

### 4.3 Reserve-holding wallet

A wallet with a positive current allocation to this reserve.

### 4.4 Reserve allocation

The amount inside one wallet currently protected for this reserve.

### 4.5 Free money

Wallet money not protected by any goal or obligation.

### 4.6 Direct reserve use

A real expense paid from a wallet that currently holds enough protection for this reserve, with the same amount consumed from that wallet's reserve allocation.

### 4.7 OffWallet expense

A real expense paid from a wallet that does not use protection from this reserve. It is ordinary spending until a later reimbursement occurs.

### 4.8 Mixed expense

A single expense whose payment is partly reserve-funded and partly ordinary-funded.

### 4.9 Prepare Payment

A pre-purchase operation that transfers real money and relocates reserve protection to the wallet that is expected to pay.

### 4.10 Reimburse from Reserve

A post-purchase operation that transfers real money from reserve-holding wallet(s) to wallet(s) that already paid an expense, consumes the corresponding reserve allocations, and changes the original expense's funding attribution.

### 4.11 Reserve-covered amount

The portion of an expense currently attributed to this reserve through direct reserve use and/or linked reimbursements.

### 4.12 Ordinary-funded amount

The portion of an expense not covered by a reserve.

---

## 5. Mathematical model

For each wallet `i`:

```text
B_i = real wallet balance before an operation
R_i = current amount protected for this reserve in wallet i
H_i = amount protected for all other goals and obligations in wallet i
P_i = real expense payment made from wallet i
U_i = amount of P_i directly consumed from this reserve
T_i = real transfer amount sent from reserve wallet i during reimbursement
A_i = amount newly allocated to this reserve in wallet i
```

Global values:

```text
Target = reserve target amount
ProtectedNow = sum(R_i)
TotalExpense = sum(P_i)
DirectReserveCovered = sum(U_i)
ReimbursedReserveCovered = sum(all active reimbursements linked to the expense)
ReserveCovered = DirectReserveCovered + ReimbursedReserveCovered
OrdinaryFunded = TotalExpense - ReserveCovered
RefillNeeded = max(Target - ProtectedNow, 0)
FullyReserved = ProtectedNow >= Target
```

Wallet free money before an operation:

```text
Free_i = B_i - R_i - H_i
```

System-wide invariant:

```text
For every wallet i:
B_i >= R_i + H_i
```

All amounts must use the same normalized settlement currency before these formulas are applied.

---

## 6. Lifecycle and state rules

### 6.1 Creation

Creating a reserve goal:

- creates the goal record;
- stores its title, target amount, intent, and optional template metadata;
- does not move wallet money;
- does not create a reserve allocation;
- starts with `ProtectedNow = 0` unless allocations are created in the same atomic workflow;
- sets status to `ACTIVE`.

### 6.2 Target date

A reserve goal must not require or accept a terminal target date in v1.

### 6.3 Fully reserved

When:

```text
ProtectedNow >= Target
```

The UI may display `Fully reserved`, but the goal remains `ACTIVE`.

### 6.4 After use

After reserve use:

- the goal remains `ACTIVE`;
- only consumed allocations decrease;
- unrelated allocations remain protected;
- `RefillNeeded` is recomputed;
- cumulative consumed statistics may increase.

### 6.5 Manual completion

The backend must reject manually changing a reserve goal to `COMPLETED`.

### 6.6 Deactivation or deletion

If the product supports deactivation or deletion, all remaining allocations must first be explicitly returned to their original wallets' free-money state. No protection may disappear silently.

---

## 7. Goal contribution ledger

The reserve funding ledger uses three contribution types.

### 7.1 `ALLOCATE`

Meaning: protect additional money in a wallet for this reserve.

Effect:

```text
R_i' = R_i + amount
B_i' = B_i
```

### 7.2 `RETURN`

Meaning: remove protection without spending the money.

Effect:

```text
R_i' = R_i - amount
B_i' = B_i
```

The money remains in the same wallet and becomes free.

### 7.3 `CONSUME`

Meaning: protected money actually leaves the reserve-holding wallet through direct expense or reimbursement.

Effect for direct use or reimbursement source wallet:

```text
R_i' = R_i - amount
B_i' = B_i - amount
```

`CONSUME` must never exceed the wallet's current reserve allocation.

### 7.4 Ledger truth

At any time:

```text
R_i = sum(ALLOCATE_i) - sum(RETURN_i) - sum(CONSUME_i)
```

Only active, non-reversed ledger rows participate in this calculation.

---

## 8. Reserve allocation: “Reserve money”

The user explicitly chooses a wallet and amount to protect.

Validation:

```text
amount > 0
wallet is eligible to fund goals
wallet currency matches or is normalized to goal currency
amount <= wallet free money
```

Where:

```text
wallet free money = real balance - all existing protected amounts
```

Settlement:

- create an `ALLOCATE` ledger row;
- do not change the wallet's real balance;
- increase `ProtectedNow`;
- recompute `RefillNeeded` and `FullyReserved`.

The operation must be atomic and idempotent.

---

## 9. Returning reserved money

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

---

## 10. Native settlement model: strict direct reserve use

### 10.1 Core invariant

The native `Use reserve` operation may use only wallets that currently hold enough protection for this reserve.

For every reserve-funded payment leg:

```text
0 < P_i <= R_i
U_i = P_i
```

A wallet cannot use another wallet's reserve allocation.

### 10.2 Direct-use settlement

For every reserve-funded payment wallet:

```text
B_i' = B_i - P_i
R_i' = R_i - P_i
```

The application records:

- the real expense;
- the category and expense date;
- payment legs per wallet;
- matching `CONSUME` rows per reserve-funded wallet;
- `ReserveCovered += P_i` for each direct leg.

The goal remains `ACTIVE`.

### 10.3 Multi-wallet direct use

The model supports any number of wallets.

For `N` direct payment wallets:

```text
For each i from 1 to N:
P_i <= R_i
B_i' = B_i - P_i
R_i' = R_i - P_i
```

No wallet-count-specific business rules are allowed.

### 10.4 Strict v1 behavior for an oversized same-wallet expense

If one wallet holds 300,000 UZS for the reserve but pays a 500,000 UZS expense, the entire 500,000 UZS must not be submitted as one direct reserve-use leg.

Valid v1 options are:

1. record 300,000 UZS as reserve-funded and 200,000 UZS as an ordinary funding portion using explicit split funding; or
2. record the whole expense as ordinary and reimburse up to 300,000 UZS afterward; or
3. prepare additional reserve money before the purchase.

The engine must never silently consume more than `R_i`.

---

## 11. OffWallet expenses

### 11.1 Definition

An OffWallet expense is paid from wallet money that is not consumed from this reserve.

Example:

```text
Wallet A reserve allocation: 500,000
Wallet B pays expense:       200,000
Direct reserve use:                0
```

### 11.2 Immediate result

```text
Wallet B balance decreases by 200,000
Wallet A reserve remains 500,000
ReserveCovered = 0
OrdinaryFunded = 200,000
```

The full expense initially affects the monthly category budget.

### 11.3 Philosophical rule

The fact that an expense's purpose matches the reserve does not mean reserve money was used.

The reserve remains unchanged until a real reimbursement occurs.

### 11.4 Prohibited behavior

The application must not:

- reduce Wallet A's reserve allocation invisibly;
- invent a historical transfer from Wallet A to Wallet B;
- classify the payment as reserve-funded merely because it was an emergency;
- automatically infer a reserve goal from the expense category.

---

## 12. Mixed expenses

### 12.1 Definition

A mixed expense has both:

- one or more reserve-funded payment portions; and
- one or more ordinary-funded payment portions.

Example:

```text
Wallet A holds reserve and pays: 200,000 reserve-funded
Wallet B pays:                   400,000 ordinary-funded
Total expense:                  600,000
```

### 12.2 Settlement

For reserve-funded portions:

```text
wallet balance decreases
same wallet reserve allocation decreases
```

For ordinary-funded portions:

```text
wallet balance decreases
reserve allocations remain unchanged
```

Result:

```text
ReserveCovered = 200,000
OrdinaryFunded = 400,000
```

### 12.3 Descriptive modes, not separate engines

For Set Aside Money, `DIRECT`, `OFF_WALLET`, and `MIXED` are useful descriptions of an expense's funding attribution. They do not require three unrelated settlement engines.

The unified rule is:

```text
Only explicitly reserve-funded portions consume reserve allocations.
All other portions are ordinary-funded.
```

---

## 13. Prepare Payment: pre-purchase flow

### 13.1 Purpose

Prepare Payment is used before the real purchase when the intended payment wallet does not currently hold enough of the reserve.

It changes real wallet state before the expense occurs.

### 13.2 Operation

For each preparation transfer leg from source wallet `s` to destination wallet `d`:

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
- a common preparation/relocation identifier linking all records.

### 13.3 Conservation invariants

For a preparation operation:

```text
sum(source transfer amounts) = sum(destination received amounts)
sum(reserve allocation decreases) = sum(reserve allocation increases)
ProtectedNow after = ProtectedNow before
```

Prepare Payment does not consume the reserve and does not change `RefillNeeded`.

### 13.4 Classification

Prepare Payment is:

- not an expense;
- not income;
- not reserve consumption;
- a real internal wallet transfer plus reserve-location relocation.

After preparation, the destination wallet can perform native direct reserve use.

---

## 14. Reimburse from Reserve: post-purchase flow

### 14.1 Purpose

Reimbursement is used after an ordinary or partially ordinary expense has already happened.

It truthfully records:

1. the original payment wallet paid the merchant;
2. reserve-holding wallet(s) later compensated that payment wallet;
3. protected reserve money actually left the source reserve wallet(s);
4. the original expense became partially or fully reserve-covered.

### 14.2 Primary UI entry points

Recommended entry points:

- **Primary:** Expense details -> `Reimburse from reserve`
- **Secondary:** Reserve goal card -> `Reimburse an expense`

The generic Wallet Transfer page must not be the primary creator of reimbursement because a reimbursement requires goal and expense context.

The resulting transfer may still appear in wallet histories.

### 14.3 Eligible expense

An expense is eligible when:

- it exists and is not deleted or reversed;
- it represents a real expense, not income or an internal transfer;
- it has an ordinary-funded amount greater than zero;
- its currency is compatible with the reserve reimbursement operation;
- it is not already fully reserve-covered;
- the selected destination wallet participated in paying the expense, unless the product explicitly supports reimbursement to an external person or account in a later version.

### 14.4 Remaining reimbursable amount

For an expense:

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

### 14.5 Source validation

For every reserve source wallet `s`:

```text
0 < SourceAmount_s <= R_s
```

The source wallet must have enough real balance after respecting all other protected amounts. Because the reimbursement consumes this reserve allocation, the post-operation invariant must hold:

```text
B_s - SourceAmount_s >= H_s + (R_s - SourceAmount_s)
```

### 14.6 Reimbursement conservation

```text
sum(SourceAmount_s) = sum(ReimbursementTo_d) = ReimbursementAmount
```

### 14.7 Reimbursement settlement

For each source reserve wallet `s`:

```text
B_s' = B_s - SourceAmount_s
R_s' = R_s - SourceAmount_s
```

Create a `CONSUME` row for each source amount.

For each destination payment wallet `d`:

```text
B_d' = B_d + ReimbursementTo_d
```

Create real internal transfer records linking sources and destinations.

For the original expense:

```text
ReserveCovered' = ReserveCovered + ReimbursementAmount
OrdinaryFunded' = TotalExpense - ReserveCovered'
```

The reimbursement itself is:

- not a second expense;
- not income;
- not a category-spending event;
- a real internal transfer plus reserve consumption plus funding-attribution update.

### 14.8 Multiple sources and destinations

The model supports any number of reserve source wallets and payment destination wallets.

It is represented by transfer legs, not brute-force cases.

For `S` sources and `D` destinations:

```text
sum over S source amounts = sum over D destination amounts
```

The agent may construct explicit source-to-destination transfer legs, but business correctness depends on the aggregate conservation and per-wallet limits, not on wallet counts.

### 14.9 Partial reimbursement

Partial reimbursement is valid.

Example:

```text
Expense:               1,200,000
Already reserve-covered: 200,000
Remaining ordinary:    1,000,000
New reimbursement:       300,000
```

After reimbursement:

```text
ReserveCovered = 500,000
OrdinaryFunded = 700,000
```

Further reimbursements may occur until `OrdinaryFunded = 0`.

---

## 15. Monthly category budget interaction

### 15.1 Two separate reporting truths

Every expense must preserve both:

```text
CategoryActualSpending = TotalExpense
MonthlyBudgetImpact = OrdinaryFunded
```

The full expense always appears in category spending and reports.

Only the portion not covered by the reserve consumes the monthly category budget limit.

### 15.2 Universal formula

```text
MonthlyBudgetImpact = TotalExpense - ReserveCovered
```

With invariant:

```text
0 <= ReserveCovered <= TotalExpense
```

### 15.3 Direct reserve use

If a 1,200,000 UZS medical expense is fully paid from reserve-holding wallets:

```text
CategoryActualSpending = 1,200,000
ReserveCovered =         1,200,000
MonthlyBudgetImpact =            0
```

### 15.4 OffWallet expense before reimbursement

If the same expense is paid entirely from an ordinary wallet:

```text
CategoryActualSpending = 1,200,000
ReserveCovered =                 0
MonthlyBudgetImpact =    1,200,000
```

### 15.5 Mixed expense

If 200,000 is reserve-funded and 400,000 is ordinary-funded:

```text
CategoryActualSpending = 600,000
ReserveCovered =        200,000
MonthlyBudgetImpact =   400,000
```

### 15.6 Reimbursement restores budget capacity

When an ordinary-funded portion is later reimbursed:

```text
NewMonthlyBudgetImpact
= OldMonthlyBudgetImpact - ReimbursementAmount
```

The result must never be negative.

The original category spending remains unchanged.

### 15.7 Original expense month

A reimbursement changes the funding attribution of the original expense. Therefore, budget impact must be recomputed for the **original expense's budget period**, not the reimbursement transfer date.

Example:

- expense date: June 28;
- reimbursement date: July 3.

The June category budget impact is reduced. The reimbursement must not appear as July income and must not consume or restore an unrelated July category budget.

### 15.8 Closed or historical periods

If the application allows historical edits, it must recompute historical actuals and preserve an audit event. If periods can be locked, the product must either reject reimbursement against a locked period or create an explicit adjustment policy. Silent divergence is prohibited.

---

## 16. Screenshot-based canonical example: Family Support reserve

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

### 16.1 Direct use example

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

### 16.2 OffWallet example

An Everyday Humo wallet that holds no Family Support reserve pays 1,200,000 UZS.

Immediate result:

```text
Everyday Humo real balance:      -1,200,000
Family Support ProtectedNow:     10,000,000
ReserveCovered:                           0
Monthly category budget impact:  1,200,000
Goal status: ACTIVE / Fully reserved
```

### 16.3 Full reimbursement example

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

### 16.4 Multi-source reimbursement example

The same 1,200,000 UZS expense may be reimbursed by:

```text
Cash - DEBIT:               700,000
brandnewGoalWallet2 - CASH: 500,000
```

Results:

```text
Cash - DEBIT balance and reserve:               -700,000
brandnewGoalWallet2 balance and reserve:         -500,000
Everyday Humo receives:                         1,200,000
Total reserve consumed:                         1,200,000
```

The behavior is identical regardless of the number of source wallets.

---

## 17. UI and interaction specification

### 17.1 Goal card actions

Recommended actions:

- `Reserve money`
- `Use reserve`
- `Prepare payment`
- `Reimburse an expense`
- `Return reserved money`
- `View allocations and activity`

### 17.2 Expense details action

When `OrdinaryFunded > 0`, show:

```text
Reimburse from reserve
```

The flow asks for:

1. reserve goal;
2. reimbursement amount;
3. reserve source wallet(s);
4. destination payment wallet(s), prefilled from the expense;
5. confirmation summary.

### 17.3 Wallet page

The generic wallet transfer flow must remain generic. It must not silently create reimbursement semantics.

Wallet history may display reimbursement transactions with metadata such as:

```text
Reserve reimbursement
Cash - DEBIT -> Everyday Humo
1,200,000 UZS
Reserve: Family Support
Linked expense: Pharmacy
```

### 17.4 Eligible wallet filtering

`Use reserve` shows only wallets with `R_i > 0` for this reserve.

`Prepare payment` shows:

- source wallets with `R_i > 0`;
- eligible destination wallets.

`Reimburse from reserve` shows:

- source wallets with `R_i > 0`;
- payment wallets linked to the selected expense that still have an unreimbursed ordinary portion.

### 17.5 Confirmation summaries

Before mutation, show all consequences:

- real balance changes;
- reserve allocation changes;
- ProtectedNow after;
- RefillNeeded after;
- monthly budget impact before and after;
- linked expense and category.

---

## 18. Classification for analytics and audit

For a completed expense, classify its current funding attribution using amounts, not wallet names alone.

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

A later reimbursement may change the classification over time, for example:

```text
ORDINARY_OFF_WALLET -> MIXED_RESERVE_AND_ORDINARY -> DIRECT_RESERVE_FUNDED
```

The audit log must preserve that history even if the current derived classification changes.

---

## 19. Atomicity, idempotency, and concurrency

### 19.1 Atomicity

Each domain operation must commit all related records together or none of them.

Examples:

- Direct use: expense + wallet postings + `CONSUME` rows + budget attribution.
- Prepare Payment: transfers + source relocation rows + destination allocation rows.
- Reimbursement: transfers + `CONSUME` rows + reimbursement links + expense funding update + budget recomputation.

### 19.2 Idempotency

Write endpoints must accept or derive an idempotency key so retries cannot duplicate:

- expenses;
- transfers;
- contribution rows;
- reimbursements;
- budget adjustments.

### 19.3 Concurrency

The operation must re-read and lock or version-check:

- wallet balances;
- reserve allocations;
- expense remaining reimbursable amount;
- budget state.

Concurrent operations must not allow reserve allocation or expense reimbursement to go below zero or above valid limits.

### 19.4 Ordering independence

Input wallet order must not change classification or final results.

---

## 20. Reversals and edits

### 20.1 Direct reserve-use reversal

Reversing a direct reserve-funded expense must atomically:

- restore real wallet balances;
- reverse matching `CONSUME` rows;
- restore reserve allocations;
- reduce cumulative reserve consumption as defined by reporting policy;
- remove category actual spending and budget impact from the original period.

### 20.2 Reimbursement reversal

Reversing a reimbursement must atomically:

- reverse the internal transfer;
- restore source reserve allocations;
- reverse source `CONSUME` rows;
- reduce the expense's `ReserveCovered` amount;
- increase the original period's monthly budget impact by the reversed amount.

### 20.3 Expense edits

An expense amount must not be edited below its active reserve-covered amount.

Before reducing or deleting such an expense, linked reimbursements or reserve coverage must be adjusted or reversed.

### 20.4 Immutable audit

Prefer reversal records over destructive deletion for posted financial events.

---

## 21. Validation errors

Recommended domain error meanings:

### Insufficient reserve in source wallet

```text
This wallet has only {available} protected for this reserve.
```

### Insufficient free money for allocation

```text
This wallet does not have enough free money to reserve {amount}.
```

### Expense fully reimbursed

```text
This expense is already fully covered by reserve funds.
```

### Reimbursement exceeds ordinary-funded portion

```text
You can reimburse up to {remaining} for this expense.
```

### Invalid destination

```text
The selected destination wallet did not pay the linked expense.
```

### Locked historical period

```text
This expense belongs to a locked budget period and cannot be reimbursed without an adjustment workflow.
```

### Currency mismatch

```text
Convert or normalize the amounts before using this reserve.
```

All errors must leave state unchanged.

---

## 22. Audit data requirements

### 22.1 Reserve goal

Store or derive:

- goal ID;
- intent `RESERVE`;
- title;
- target amount;
- currency;
- status;
- optional reserve template/type key;
- created and updated timestamps.

### 22.2 Allocation ledger row

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

### 22.3 Reimbursement record

Store:

- reimbursement ID;
- reserve goal ID;
- linked expense ID;
- total amount;
- source transfer legs;
- destination transfer legs;
- operation date;
- original expense budget period;
- status: active or reversed;
- idempotency key;
- timestamps.

### 22.4 Expense funding attribution

Store or reliably derive:

- total expense amount;
- direct reserve-covered amount;
- reimbursement-covered amount;
- total reserve-covered amount;
- ordinary-funded amount;
- category actual spending;
- monthly budget impact;
- current derived funding classification.

---

## 23. Derived UI metrics

Recommended formulas:

```text
ProtectedNow = sum(current R_i)
RefillNeeded = max(Target - ProtectedNow, 0)
FullyReserved = ProtectedNow >= Target
```

For `Used from reserve`, choose one clearly named metric:

### Option A: cumulative lifetime consumption

```text
UsedFromReserveLifetime = sum(active CONSUME amounts over goal lifetime)
```

Refilling does not reduce this historical usage number.

### Option B: current target shortfall caused by use and returns

Use the name `RefillNeeded`, not `Used from reserve`:

```text
RefillNeeded = max(Target - ProtectedNow, 0)
```

The UI should not treat cumulative consumption and current refill need as the same value.

---

## 24. Known implementation gap: reserve template persistence

The reserve-type picker may offer choices such as Emergency Fund or Medical Reserve. If the UI only uses the selection to set the title, the semantic template is lost.

Recommended v1 correction:

- send an optional stable field such as `reserve_template_key` or `template_id` in the creation payload;
- persist it independently from the user-editable title;
- use it only for defaults, analytics, icons, education, and future automation;
- do not let the template key change settlement accounting rules unless explicitly specified later.

This gap is separate from reserve settlement and must not block the accounting implementation.

---

## 25. Prohibited behaviors

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
14. mutate only part of a multi-record operation after an error.

---

## 26. Complexity and scalability

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

No combinatorial search or brute-force case enumeration is required.

---

## 27. Acceptance criteria

The implementation is correct only if all of the following hold.

### Goal lifecycle

1. Creating a reserve does not move money.
2. Reaching the target does not complete the goal.
3. Using money does not complete the goal.
4. Manual completion is rejected.
5. Remaining allocations stay protected after use.

### Allocation truth

6. `ALLOCATE` increases protection without changing balance.
7. `RETURN` decreases protection without changing balance.
8. `CONSUME` decreases both balance and protection by the same amount.
9. Current wallet allocation equals allocations minus returns and consumes.
10. No wallet's total protection exceeds its real balance.

### Direct use

11. Only wallets holding enough reserve may fund native reserve-use legs.
12. Every direct reserve-funded amount is less than or equal to that wallet's allocation.
13. Direct use decreases the same wallet's balance and allocation equally.
14. Any number of direct wallets is supported.

### OffWallet and mixed expenses

15. An OffWallet expense leaves the reserve unchanged.
16. Its ordinary-funded amount initially equals the full expense.
17. In a mixed expense, only reserve-funded portions consume allocations.
18. Ordinary portions remain eligible for later reimbursement.

### Prepare Payment

19. Prepare Payment happens before purchase.
20. It records real transfers.
21. It relocates equal reserve protection.
22. It does not consume reserve or change ProtectedNow.
23. It is not an expense or income.

### Reimbursement

24. Reimbursement links to a real existing expense.
25. It transfers real money from reserve source wallet(s) to original payment wallet(s).
26. Source balances and reserve allocations decrease equally.
27. Destination balances increase.
28. Reserve-covered amount increases by the reimbursement amount.
29. Reimbursement cannot exceed the remaining ordinary-funded amount.
30. Multiple partial reimbursements are supported.
31. Multiple source and destination wallets are supported without brute force.
32. Reimbursement is not income or a second expense.

### Monthly budgets

33. Category actual spending always equals the full expense amount.
34. Monthly budget impact equals ordinary-funded amount.
35. Direct reserve coverage does not consume the monthly category budget.
36. Reimbursement restores budget capacity by the reimbursed amount.
37. Budget impact is adjusted in the original expense's period.
38. Budget impact never becomes negative.

### Reliability

39. Every operation is atomic.
40. Retries are idempotent.
41. Concurrent operations cannot over-consume reserve or over-reimburse an expense.
42. Wallet input order does not change results.
43. Reversals restore all corresponding wallet, reserve, expense, and budget states.
44. Audit history remains available after reversals.

---

## 28. Canonical implementation sequence

### 28.1 Direct reserve use

1. Normalize currency and aggregate payment legs.
2. Load and lock the goal, wallet balances, and reserve allocations.
3. Verify goal intent is `RESERVE` and status is `ACTIVE`.
4. Verify every reserve-funded payment leg is positive and does not exceed that wallet's reserve allocation.
5. Verify wallet post-balances preserve all remaining protections.
6. Create the expense and payment postings.
7. Create matching `CONSUME` rows.
8. Compute expense reserve coverage and monthly budget impact.
9. Recompute goal metrics.
10. Commit atomically.

### 28.2 Prepare Payment

1. Normalize source and destination transfer legs.
2. Load and lock wallets and reserve allocations.
3. Validate source allocations and balances.
4. Validate total source amount equals total destination amount.
5. Create real transfer postings.
6. Create source relocation-out and destination allocation-in rows.
7. Verify total `ProtectedNow` is unchanged.
8. Commit atomically.

### 28.3 Reimburse from Reserve

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

## 29. Final normative rules

The Set Aside Money goal is governed by the following final rules:

```text
1. Reserve money remains inside specific wallets and is protected there.
2. A reserve is consumed only when protected money actually leaves its holder wallet.
3. Native use is wallet-local and strict.
4. OffWallet spending is ordinary spending until reimbursed.
5. Mixed spending consumes reserve only for explicitly reserve-funded portions.
6. Prepare Payment moves reserve money before the expense.
7. Reimburse from Reserve moves reserve money after the expense.
8. Reimbursement changes the original expense's funding attribution, not its spending amount.
9. Full expense amount appears in category reports.
10. Only the ordinary-funded portion consumes the monthly category budget.
11. The goal stays active and unreleased allocations remain protected.
12. The model scales linearly to any number of wallets and requires no brute-force cases.
```

These rules are the source of truth for v1 implementation.
