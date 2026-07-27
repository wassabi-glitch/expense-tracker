# Planned Purchase Goal Specification v1

**Goal type:** Planned Purchase
**Status:** Canonical merged spec for implementation
**Date:** July 14, 2026
**Merged from:**

- `Planned_Purchase_Payment_Specification_v1.md`
- `goals-plannedpurchase-specs.md`

---

## Problem Statement

Sarflog needs a single, precise specification for how a `Planned Purchase`
goal records the final real-world purchase when the protected goal money may
be located in one wallet, many wallets, the same wallet used at checkout, a
different wallet used at checkout, or a mix of both.

Without one canonical spec, implementation tickets could split the feature
along the wrong seams: UI might ask users to choose accounting modes, backend
logic might silently move money between wallets, or settlement might release
protected funds without preserving a reliable audit trail.

The user problem is simple:

> I saved or reserved money for one specific purchase. When I actually buy it,
> I want to record which wallets really paid, have Sarflog close the goal
> correctly, and trust that balances, protections, unused money, and history are
> all accurate.

---

## Solution

Planned Purchase is a terminal goal for one specific final purchase event. The
user records the real checkout through one shared `Record purchase` flow. The
user does not choose `DIRECT`, `OFF_WALLET`, or `MIXED`; Sarflog derives the
settlement mode from the relationship between funding wallets and payment
wallets.

The implementation must preserve two truths at the same time:

1. **Real payment truth:** which wallets actually lost real money, and how much.
2. **Goal protection truth:** all protection for the completed goal is removed
   because the planned outcome happened.

After a successful final purchase settlement:

```text
ACTIVE -> COMPLETED
```

All remaining goal allocations become zero. Any unused protected amount becomes
free money in the wallet where it already exists. No hidden real wallet transfer
is created.

---

## User Stories

1. As a user, I want to reserve money for a planned purchase, so that I can keep that money separate from ordinary spending.
2. As a user, I want to record the final purchase from the wallet that actually paid, so that my real wallet balance stays accurate.
3. As a user, I want to pay from the same wallet that held the goal money, so that a straightforward purchase is easy to record.
4. As a user, I want to pay from a different wallet than the one holding the goal money, so that real-life checkout constraints are supported.
5. As a user, I want to pay from multiple wallets, so that split payments can be recorded accurately.
6. As a user, I want Sarflog to derive whether the purchase is Direct, OffWallet, or Mixed, so that I do not need to understand internal accounting categories.
7. As a user, I want to see a preview before completing the purchase, so that I understand which balances will change and which protections will be released.
8. As a user, I want the final purchase amount to be allowed below the funded amount, so that discounts or cheaper purchases can close the goal correctly.
9. As a user, I want unused protected money to become free after completion, so that the app no longer treats it as reserved.
10. As a user, I want the goal to complete after the final purchase, so that finished purchase goals do not remain active.
11. As a user, I want a funding wallet to be limited by its own protected amount, so that one wallet does not silently consume another wallet's reserved money.
12. As a user, I want non-funding wallets to pay only if they have enough spendable balance, so that the purchase cannot consume money protected for other obligations.
13. As a user, I want every payment wallet checked for sufficient spendable balance, so that settlement never makes a wallet lie about available money.
14. As a user, I want Sarflog to reject purchases above the funded capacity, so that a Planned Purchase does not become an ordinary overspending shortcut.
15. As a user, I want Sarflog to avoid hidden transfers, so that my wallet history matches what really happened.
16. As a user, I want to prepare payment before checkout when needed, so that I can move real money and protection to the wallet the merchant accepts.
17. As a user, I want Prepare Payment to be explicit and pre-purchase only, so that the app does not invent transfers after the fact.
18. As a user, I want the purchase completion to be atomic, so that failed validation cannot leave half-updated balances or protections.
19. As a user, I want duplicate completion attempts to be idempotent, so that retries do not create duplicate purchases.
20. As a user, I want stale previews to be revalidated, so that changes made while the wizard is open are not overwritten.
21. As a user, I want an audit record of the settlement, so that I can later understand what happened.
22. As a user, I want reversal to restore the whole linked settlement if possible, so that mistakes can be corrected safely.
23. As a user, I want reversal blocked when exact restoration is unsafe, so that corrections do not create false wallet state.
24. As a product owner, I want one model that works for any number of funding and payment wallets, so that the implementation does not grow wallet-count-specific cases.
25. As an implementer, I want one backend settlement policy used by preview and completion, so that frontend and backend behavior cannot drift.

---

## Implementation Decisions

### 1. Locked v1 Decisions

1. A Planned Purchase represents one final purchase event.
2. The primary action is `Record purchase`.
3. Record Purchase uses one shared two-step wizard.
4. Step 1 asks only which wallets actually paid, how much, purchase date, and optional merchant/category/note data.
5. The UI does not ask the user to choose Direct, OffWallet, or Mixed.
6. Sarflog derives the settlement mode from funding-wallet and payment-wallet relationships.
7. Any number of funding and payment wallets is supported.
8. Total purchase payment cannot exceed total remaining goal funding.
9. A funding wallet cannot pay more than the amount protected for this goal in that same wallet.
10. Wallets do not silently cover another funding wallet's local limit.
11. A non-funding wallet may participate as an OffWallet payment source if it has enough real spendable balance.
12. Every payment wallet, including a funding wallet that pays, must have enough real spendable balance for its payment leg.
13. Purchase amount may be lower than the total funded amount.
14. After successful payment, the goal becomes completed.
15. Every remaining goal allocation becomes zero and unused protection is released to free money.
16. No hidden real wallet transfer is created.
17. Prepare Payment remains an optional pre-purchase flow.
18. Planned Purchase has no post-payment reimbursement action.
19. Settlement and reversal operate as atomic linked event bundles.

### 2. Scope

Included:

- final purchase recording;
- one or multiple payment wallets;
- Direct, OffWallet, and Mixed derivation;
- wallet-local and global funding limits;
- payment-wallet spendable-balance validation;
- purchase price below the funded amount;
- release of unused protection;
- optional Prepare Payment before purchase;
- two-step wizard and review preview;
- audit data, idempotency, concurrency, and reversal.

Excluded:

- deposits or staged seller payments;
- installment purchases and payment plans;
- keeping the Planned Purchase active after a partial purchase;
- post-purchase reimbursement;
- automatically borrowing from ordinary money above funded capacity;
- automatically converting purchase excess into an ordinary expense;
- merchant refund handling after completion, except through a separately designed refund/correction flow;
- FX conversion mechanics inside the settlement engine.

A purchase paid over time belongs in the debts, installments, or payment-plan model, not in this final-settlement model.

### 3. Core Concepts

**Funding wallet**

A wallet that contains protected money assigned to the Planned Purchase goal.
Example:

```text
Wallet A: 500,000 protected
```

The protected amount is not free money and cannot be used for unrelated
spending.

**Payment wallet**

A wallet from which real money actually leaves when the purchase is made.
Example:

```text
Wallet B: 500,000 payment
```

Wallet B's real balance decreases by 500,000.

**Protected amount**

The amount inside a specific wallet reserved for the current goal.

**Free amount**

Money inside a wallet that is not protected by any goal or obligation.

**Payment leg**

The portion of a purchase paid from one wallet. A single purchase may have many
payment legs:

```text
Wallet A: 200,000
Wallet B: 300,000
Wallet C: 100,000
```

This is one 600,000 purchase with three payment legs.

### 4. Notation

For each wallet `i`:

```text
B_i = real wallet balance before settlement
F_i = remaining amount protected for this Planned Purchase in wallet i
H_i = money protected for other goals or obligations in wallet i
P_i = real amount paid from wallet i at checkout
```

Spendable balance for this transaction:

```text
Spendable_i = B_i - H_i
```

The current Planned Purchase allocation is not included in `H_i`.

Global values:

```text
G = sum(F_i) = total remaining goal funding
Q = sum(P_i) = total final purchase payment
```

Wallet sets:

```text
FundingSet = { i | F_i > 0 }
PaymentSet = { i | P_i > 0 }
DirectSet = FundingSet intersect PaymentSet
OffWalletSet = PaymentSet minus FundingSet
```

Short notation:

```text
F = FundingSet
P = PaymentSet
D = DirectSet
O = OffWalletSet
```

Where:

- `D` represents Direct payment wallets.
- `O` represents OffWallet payment wallets.

### 5. Universal Invariants

These rules apply to all settlement modes.

**Goal must have funds**

```text
G > 0
```

A goal with no protected funds cannot be settled.

**Payment must be positive**

```text
Q > 0
```

A goal cannot be completed with a zero-value payment.

**Payment cannot exceed total funded amount**

```text
Q <= G
```

Example:

```text
Total funded: 1,000,000
Total payment: 1,200,000
```

This is invalid. The Planned Purchase can only be settled within its funded
capacity.

**Funding wallet local Direct limit**

For every wallet that both funded the goal and paid:

```text
P_i <= F_i
```

A funding wallet cannot use ordinary money above its own goal allocation inside
this Planned Purchase settlement. Another wallet's unused allocation does not
increase this wallet's limit.

Example:

```text
A funded 500,000
B funded 500,000
A paid 400,000
B paid 600,000
```

This is invalid because `600,000 > 500,000` for Wallet B, even though total
payment equals total funding.

**Every payment wallet must have sufficient spendable balance**

For every payment wallet:

```text
P_i <= Spendable_i
```

The transaction must not consume money protected for other goals or
obligations. This applies to Direct, OffWallet, and Mixed payment wallets.

**Amounts cannot be negative**

```text
F_i >= 0
P_i >= 0
B_i >= 0
H_i >= 0
```

**Atomicity**

All validation occurs before mutation. If one invariant fails:

- no wallet balance is changed;
- no protection is released;
- the goal is not completed;
- no purchase, settlement, or reversal transaction is created.

**Ordering independence**

Reordering wallet rows must not change classification, totals, or settlement
outcome.

**Wallet count is unlimited**

The model must support any wallet count combination:

```text
1 funding wallet + 1 payment wallet
2 funding wallets + 7 payment wallets
10 funding wallets + 3 payment wallets
N funding wallets + M payment wallets
```

No business rule may depend on a specific wallet count.

### 6. Derived Settlement Modes

Settlement mode is derived from the relationship between funding wallets and
payment wallets. The modes are mutually exclusive.

**Direct**

```text
PaymentSet is a subset of FundingSet
```

Equivalent:

```text
O is empty
D is not empty
```

Every payment wallet previously funded the goal. Some funding wallets may
remain unused during payment.

**OffWallet**

```text
FundingSet intersect PaymentSet is empty
```

Equivalent:

```text
D is empty
O is not empty
```

None of the payment wallets funded the goal.

**Mixed**

```text
D is not empty
O is not empty
```

At least one funding wallet pays and at least one non-funding wallet pays.

Every valid settlement belongs to exactly one mode. A settlement cannot be both
Direct and Mixed, or both OffWallet and Mixed.

### 7. Direct Settlement

Direct settlement occurs when every payment wallet belongs to the funding set.

Canonical example:

```text
Funding:
A: 500,000
B: 400,000
C: 300,000

Payment:
A: 450,000
B: 300,000

Validation:
A payment <= A funding
B payment <= B funding
Q = 750,000 <= G = 1,200,000
```

Wallet C does not need to participate in the payment even though it funded the
goal.

Invalid local-limit example:

```text
Funding:
A: 500,000
B: 400,000

Payment:
A: 400,000
B: 500,000

Total:
Q = 900,000
G = 900,000
```

The total is valid, but Wallet B violates its local Direct limit:

```text
500,000 > 400,000
```

Therefore, settlement is invalid.

Direct settlement behavior:

```text
B_i_after = B_i_before - P_i
F_i_after = 0
Unused = G - Q
```

Funds remaining in unused funding wallets, and unused protected amounts inside
payment wallets, become free money. No real transfer is created.

### 8. OffWallet Settlement

OffWallet settlement occurs when none of the payment wallets funded the goal.

Canonical example:

```text
Funding:
A: 500,000
B: 500,000

Payment:
C: 600,000
D: 200,000

Classification:
{A, B} intersect {C, D} = empty
```

Settlement:

- C real balance decreases by 600,000.
- D real balance decreases by 200,000.
- A and B real balances do not change.
- A and B goal protections become zero.
- The goal completes.
- 200,000 is the net unused goal amount released to free money.

OffWallet supports N-to-M wallet combinations. The number of funding wallets
does not need to equal the number of payment wallets.

N-to-M example:

```text
Funding:
A: 400,000
B: 300,000
C: 300,000

Payment:
D: 600,000
E: 400,000

Classification:
{A, B, C} intersect {D, E} = empty
```

Payment wallets must not be paired one-to-one with funding wallets. Funding
wallets represent one aggregate goal capacity for the OffWallet portion.

### 9. Mixed Settlement

Mixed settlement occurs when at least one funding wallet pays and at least one
non-funding wallet pays.

Simplest example:

```text
Funding:
A: 500,000

Payment:
A: 200,000
B: 300,000

Direct portion: 200,000
OffWallet portion: 300,000
Total payment: 500,000
```

Definitions:

```text
DirectPaid = sum(P_i where i is in D)
OffWalletPaid = sum(P_i where i is in O)
RemainingFundPool = G - DirectPaid
```

The OffWallet portion must not exceed the remaining funded pool:

```text
OffWalletPaid <= RemainingFundPool
```

This is equivalent to the global invariant:

```text
DirectPaid + OffWalletPaid <= G
```

Canonical example:

```text
Funding:
A: 400,000
B: 300,000

Payment:
A: 200,000
B: 100,000
C: 400,000

Validation:
A: 200,000 <= 400,000
B: 100,000 <= 300,000
Q = 700,000 <= G = 700,000
```

Settlement:

- A balance decreases by 200,000.
- B balance decreases by 100,000.
- C balance decreases by 400,000.
- All A and B goal protection becomes zero.
- The goal completes.
- Unused amount is zero.

Lower-price Mixed example:

```text
Funding:
A: 800,000

Payment:
A: 200,000
B: 300,000
C: 100,000

G = 800,000
DirectPaid = 200,000
OffWalletPaid = 400,000
Q = 600,000
Unused = 200,000
```

A's real balance falls only by 200,000. The remaining protection is removed
because the goal closes. System-wide net free-money increase equals 200,000.

Invalid Mixed example:

```text
Funding:
A: 400,000
B: 300,000

Payment:
A: 200,000
B: 100,000
C: 500,000

DirectPaid = 300,000
RemainingFundPool = 400,000
OffWalletPaid = 500,000
```

The invariant fails:

```text
500,000 > 400,000
```

The total payment also exceeds total funding:

```text
Q = 800,000
G = 700,000
```

Therefore, settlement is invalid.

### 10. Unified Settlement Mathematics

All modes use the same final-state formulas.

For every wallet:

```text
real_balance_after_i = real_balance_before_i - P_i
```

For wallets that did not participate in payment:

```text
P_i = 0
```

Therefore, their real balances remain unchanged.

For every funding wallet after completion:

```text
goal_protection_after_i = 0
```

Unused amount:

```text
Unused = G - Q
Unused >= 0
```

Considering only this goal's settlement, free-money change per wallet is:

```text
DeltaFree_i = F_i - P_i
```

For a funding wallet that participated in payment:

```text
F_i > 0
P_i > 0
P_i <= F_i
DeltaFree_i >= 0
```

For a funding wallet that did not participate in payment:

```text
F_i > 0
P_i = 0
DeltaFree_i = F_i
```

Its entire current goal allocation becomes free money.

For an OffWallet payment wallet:

```text
F_i = 0
P_i > 0
DeltaFree_i = -P_i
```

Its free money decreases by the amount it actually paid.

System-wide:

```text
sum(DeltaFree_i) = sum(F_i) - sum(P_i)
sum(DeltaFree_i) = G - Q
sum(DeltaFree_i) = Unused
```

In OffWallet and Mixed settlements, a large amount of protection may be
released inside funding wallets while free balances decrease inside payment
wallets. The system-wide net increase in free money is only:

```text
funded amount - actual purchase payment
```

### 11. Source Attribution Rules

**Direct attribution**

A Direct payment is explicitly linked to the same wallet's goal allocation:

```text
Wallet A payment -> Wallet A current goal fund
```

**OffWallet attribution**

An OffWallet payment must not be artificially paired with individual funding
wallets.

Example:

```text
Funding:
A: 500,000
B: 500,000

Payment:
C: 800,000
```

The system must not invent mappings such as:

```text
A covered 500,000
B covered 300,000
```

or:

```text
A covered 400,000
B covered 400,000
```

The system only needs aggregate settlement information:

```text
Total funded: 1,000,000
OffWallet payment: 800,000
Unused: 200,000
```

Because the Planned Purchase is completed, all funding allocations become zero
regardless.

**Mixed attribution**

In Mixed mode:

- the Direct portion is attributable to specific funding wallets;
- the OffWallet portion is covered only by the aggregate remaining goal pool.

The OffWallet portion must not be distributed across individual funding wallets.

### 12. Prohibited Hidden Behaviors

The implementation must not perform any of these behaviors.

**Hidden wallet transfers**

The application must not create an automatic real transfer from a funding wallet
to a payment wallet.

**Automatic rebalancing**

A funding wallet must not pay more than its local current goal fund, even when
another funding wallet has unused protection.

Example:

```text
A funded: 500,000
B funded: 500,000
A paid: 400,000
B paid: 600,000
```

This is invalid. The unused 100,000 inside Wallet A must not increase Wallet B's
local Direct payment limit.

**Treating one wallet as both Direct and OffWallet**

When a wallet has current goal funds and participates in payment:

```text
F_i > 0
P_i > 0
```

it is a Direct wallet. The wallet must not use an amount above its goal fund as
an OffWallet portion.

Example:

```text
A funded: 200,000
A payment: 300,000
```

This is invalid even when Wallet A has additional free money.

**Allowing payment above funded amount**

When the purchase cost exceeds the goal's funded amount, settlement must be
rejected. The excess must not automatically become an ordinary expense.

**Keeping the goal active after settlement**

The payment described in this spec is final. After successful settlement, the
goal must become `COMPLETED`.

### 13. Unified Record Purchase Wizard

Record Purchase uses a two-step wizard.

**Step 1: Record the real checkout**

The user enters:

- purchase date;
- one or more wallets or cash sources that actually paid;
- amount from each wallet;
- optional category;
- optional merchant;
- optional note.

Each wallet row should display:

```text
Wallet name
Real balance
Protected for this goal, if any
Maximum valid amount for this row
Amount paid
```

Do not display mode-selection cards such as:

- I paid from goal wallets;
- I paid from another wallet;
- Mixed.

The payment rows fully determine the mode.

**Real-time guidance**

For a funding wallet:

```text
row maximum = min(F_i, wallet usable real balance)
```

For a non-funding wallet:

```text
row maximum = wallet ordinary spendable balance
```

The wizard must also show:

```text
Final price = sum(payment rows)
Available goal funding = G
Remaining capacity = G - current final price
```

**Step 2: Review consequences**

The review must show:

- final purchase amount;
- wallets that actually pay and their balance changes;
- plain-language grouped consequences;
- internally derived Direct, OffWallet, or Mixed relationship in audit data;
- goal status transition;
- each funding wallet's protection before and after;
- unused amount released;
- warning if any invariant fails.

Plain-language headings should be:

```text
Paid from wallets holding goal money
Paid from other wallets
Unused goal money released
```

The user clicks `Complete purchase` only after reviewing the full state
transition.

**Backend preview authority**

Step 2 must come from a backend preview endpoint or the same authoritative
policy engine used by completion. The frontend must not independently guess
settlement effects.

**Final revalidation**

On Complete Purchase, the backend rechecks:

- goal status;
- current allocations;
- wallet balances;
- payment totals;
- currency normalization;
- optimistic-lock versions.

### 14. Goal Card and UI Copy

Active Planned Purchase actions:

- `Reserve money`
- `Unreserve`
- `Prepare payment`
- `Record purchase`
- `View activity`
- `Archive/Cancel` through an explicit release flow

Step 1 copy should use:

> Which wallets actually paid at checkout?

Do not use:

> Select Direct, OffWallet, or Mixed.

Canonical preview example:

```text
Final purchase: 3,000,000 UZS

Paid from a goal wallet
Cash: 2,000,000 UZS

Paid from another wallet
Humo: 1,000,000 UZS

After completion
Cash balance: -2,000,000
Humo balance: -1,000,000
Remaining goal protection released: 1,000,000
Goal status: Completed
```

Invalid funding-wallet local-limit message:

> Cash has only 500,000 UZS protected for this purchase. Reduce this wallet's
> payment or use another valid payment wallet.

Completed cards should show actual purchase amount and completion date. They
must not continue showing money as reserved.

### 15. Prepare Payment

Prepare Payment is optional and occurs before checkout.

Example:

```text
Savings holds 5M protected.
The merchant must be paid from Humo.
The user prepares 3M.
```

Operation:

```text
real transfer: Savings -> Humo = 3M
protection relocation: Savings -= 3M
protection relocation: Humo += 3M
goal total funding unchanged
goal status unchanged
```

After preparation, Humo can participate as a Direct payment wallet.

Prepare Payment must not be automatically invented after the purchase occurred.
It is not a reimbursement action.

### 16. Completion and Lifecycle

On successful completion:

```text
ACTIVE -> COMPLETED
```

Store:

- actual purchase amount `Q`;
- purchase date;
- payment legs;
- derived mode;
- unused amount;
- completion timestamp.

All remaining goal allocations become zero. This is a protection-state change
only; it is not a real wallet inflow or transfer.

The goal must not remain active after the final purchase merely because the
purchase cost was lower than target or funding.

If only a deposit or first installment occurred, do not use this settlement.
Use the appropriate staged-payment model.

### 17. Currency Rules

All `F_i` and `P_i` values must be normalized to one settlement currency before
validation.

When wallets use different currencies, the currency layer must resolve:

- exchange rate;
- exchange-rate locking;
- rounding;
- source and destination amounts;
- conversion fees;
- conversion gains or losses.

The settlement engine must not compare raw amounts from incompatible currencies.

### 18. Unified Settlement Sequence

The backend should process settlement in this conceptual order.

**Phase 1: Input normalization**

1. Aggregate multiple payment legs from the same wallet into one `P_i` value.
2. Ignore zero-value payment legs.
3. Normalize all amounts into the settlement currency.

**Phase 2: Set construction**

1. Construct `FundingSet`.
2. Construct `PaymentSet`.
3. Construct `DirectSet = FundingSet intersect PaymentSet`.
4. Construct `OffWalletSet = PaymentSet minus FundingSet`.

**Phase 3: Mode classification**

```text
O is empty -> DIRECT
D is empty -> OFF_WALLET
D is not empty and O is not empty -> MIXED
```

**Phase 4: Validation**

1. `G > 0`
2. `Q > 0`
3. `Q <= G`
4. For every Direct wallet: `P_i <= F_i`
5. For every payment wallet: `P_i <= Spendable_i`
6. Goal status is `ACTIVE`
7. Amounts are non-negative
8. Currency normalization is valid
9. Preview and completion state versions are still current
10. Completion is not a duplicate

**Phase 5: Settlement**

1. Subtract `P_i` from each payment wallet's real balance.
2. Set all current goal allocations to zero.
3. Calculate `Unused = G - Q`.
4. Store `Q` as the actual purchase cost.
5. Store the derived settlement mode.
6. Change goal status to `COMPLETED`.

**Phase 6: Audit data**

The settlement record must logically preserve at least:

```text
Total funded amount at settlement
Total payment amount
Direct paid amount
OffWallet paid amount
Unused amount
Settlement mode
Funding wallet IDs
Payment wallet IDs
Payment amount per wallet
Funding allocation per wallet before settlement
Wallet balances before and after
Goal status before and after
Goal completion timestamp
Idempotency key
```

The OffWallet portion must not be artificially attributed to individual funding
wallets.

### 19. Audit and Event Bundle

One purchase bundle should contain:

1. purchase or expense record;
2. wallet outflow legs;
3. goal-allocation consumption and release events;
4. goal completion;
5. budget/category effects, if applicable;
6. derived settlement mode.

Required fields:

- bundle id;
- goal id;
- payment date;
- total funded before settlement;
- total purchase payment;
- Direct paid amount;
- OffWallet paid amount;
- unused amount;
- derived mode;
- payment wallet ids and amounts;
- funding wallet ids and allocations before settlement;
- wallet balances before and after;
- goal status before and after;
- completion timestamp;
- idempotency key.

Payment legs and allocation events are the source of truth. The mode is derived
data. It can be recalculated and must not be the sole accounting foundation.

### 20. Reversal

A purchase reversal must reverse the whole linked bundle, not only the visible
expense row.

Correct inverse:

```text
restore each payment wallet by P_i
restore each original goal allocation F_i
change goal COMPLETED -> ACTIVE
remove or void the active purchase completion record
restore category/budget effects, if applicable
link the reversal to the original bundle
```

If money released on completion has since been spent or protected elsewhere and
the original allocations cannot be restored without violating wallet truth,
block the reversal and require an explicit correction/refund workflow.

Reversal is atomic: either the complete inverse succeeds or nothing changes.

### 21. Validation Errors

Block settlement when:

- goal is not active;
- no funding remains;
- payment total is zero;
- payment total exceeds total remaining goal funding;
- a funding wallet's payment exceeds its local allocation;
- any payment wallet lacks real spendable balance;
- any amount is negative;
- currency normalization fails;
- goal or wallet state changed after preview;
- the payment would create a duplicate completion.

Recommended messages:

```text
This purchase goal has only X UZS available.
This wallet can use up to X UZS for this goal.
Wallet balance changed while the wizard was open. Review the updated preview.
This goal has already been completed.
```

### 22. Atomicity, Idempotency, and Concurrency

Wallet outflows, purchase record, allocation releases, audit records, and goal
completion must commit in one transaction.

Complete Purchase uses an idempotency key. Retrying the same request returns
the existing bundle.

Lock or version-check:

- goal;
- all funding allocations;
- all payment wallets.

Recompute `G`, `Q`, local limits, spendable balances, and mode at commit time.

### 23. Complexity and Scalability

The algorithm processes each relevant wallet once:

```text
O(N + M)
```

where `N` is funding-wallet count and `M` is payment-wallet count.

Do not enumerate wallet-count combinations or write separate business rules for
one, two, three, or more wallets.

---

## Testing Decisions

### Highest-Value Test Seam

The highest-value seam is the backend settlement policy used by both preview
and completion. Tests should verify externally observable behavior: returned
preview, persisted bundle, wallet balances, goal allocations, goal status,
validation failures, and idempotency.

Frontend tests should focus on whether the wizard sends payment rows, renders
backend preview data, blocks invalid progression, and avoids exposing manual
mode selection.

### Classification Matrix

Test:

- one funding wallet pays: Direct;
- multiple funding wallets pay: Direct;
- no funding wallet pays: OffWallet;
- funding and non-funding wallets pay: Mixed;
- row order does not change classification;
- duplicate wallet rows aggregate before classification;
- zero-value payment rows are ignored.

### Validation Matrix

Test:

- payment equals total funding;
- payment below total funding;
- payment above total funding is rejected;
- funding wallet above local allocation is rejected;
- one wallet cannot be partly Direct and partly OffWallet above its allocation;
- Direct payment wallet with insufficient spendable balance is rejected;
- OffWallet payment wallet with insufficient spendable balance is rejected;
- Mixed payment wallet with insufficient spendable balance is rejected;
- zero payment is rejected;
- negative amount is rejected;
- completed goal is rejected;
- stale preview is rejected at completion;
- currency normalization failure is rejected.

### Settlement Matrix

Test:

- Direct settlement decreases only payment-wallet real balances;
- Direct settlement releases unused allocation;
- Direct settlement leaves unused funding wallets' real balances unchanged;
- OffWallet settlement decreases payment wallets only;
- OffWallet settlement leaves funding-wallet real balances unchanged;
- Mixed settlement applies correct real outflows for every payment wallet;
- all protection is zero after completion;
- goal status becomes `COMPLETED`;
- no hidden transfer is created;
- unused formula equals `G - Q`;
- global free-money change equals `G - Q`.

### Prepare Payment Matrix

Test:

- real balance transfer occurs;
- protection relocates from source wallet to destination wallet;
- total goal protection is conserved;
- goal remains active;
- no purchase, debt, expense, or final settlement is created;
- prepared destination wallet can later participate as Direct.

### Audit and Reliability Matrix

Test:

- purchase bundle stores required totals, legs, allocations, balances, mode, status changes, and idempotency key;
- mode is recalculable from source payment legs and allocations;
- concurrent allocation change invalidates stale preview;
- concurrent wallet-balance change invalidates stale preview;
- duplicate Complete does not duplicate purchase;
- any failure leaves all state unchanged.

### Reversal Matrix

Test:

- reversal restores payment wallet balances;
- reversal restores exact original allocations;
- reversal changes goal back to `ACTIVE`;
- reversal restores budget/category effects, if applicable;
- reversal links to the original bundle;
- impossible restoration is blocked;
- repeated reversal request is idempotent;
- failed reversal leaves all state unchanged.

---

## Out of Scope

- Partial purchase completion that keeps the Planned Purchase active.
- Deposits and staged seller payments.
- Installment schedules.
- Debt repayment.
- Post-purchase reimbursement as part of Planned Purchase.
- Merchant refund workflows after a completed purchase.
- Hidden wallet transfers.
- Automatic rebalancing across funding wallets.
- FX conversion policy inside the settlement engine.
- Allowing ordinary overspend above the funded Planned Purchase capacity.

---

## Further Notes

### Settlement-Mode Summary

| Mode | Classification | Local funding-wallet limit | Global limit |
| --- | --- | --- | --- |
| Direct | `PaymentSet is a subset of FundingSet` | For every Direct wallet: `P_i <= F_i` | `Q <= G` |
| OffWallet | `FundingSet intersect PaymentSet is empty` | No Direct wallet exists | `Q <= G` |
| Mixed | `D is not empty and O is not empty` | For every Direct wallet: `P_i <= F_i` | `Q <= G` |

### Final Normative Rules

1. Planned Purchase is a terminal goal for one final purchase.
2. The user records actual payment wallets in a two-step wizard.
3. The user never selects Direct, OffWallet, or Mixed.
4. Sarflog derives the relationship from wallet allocations and payment rows.
5. Total purchase payment cannot exceed total remaining goal funding.
6. A funding wallet cannot pay more than its own remaining goal allocation.
7. Every payment wallet must have enough real spendable balance.
8. Direct, OffWallet, and Mixed support any number of wallets.
9. Only actual payment wallets lose real balance.
10. No hidden wallet transfer is created.
11. No automatic funding-wallet rebalancing is created.
12. No one wallet can be both Direct and OffWallet in the same settlement.
13. The goal completes after successful final settlement.
14. All remaining goal protection is released.
15. Unused amount equals total funding minus actual purchase payment.
16. Global free-money change equals total funding minus actual purchase payment.
17. Prepare Payment is optional and pre-purchase only.
18. Planned Purchase has no post-payment reimbursement.
19. Payment legs and allocation events are source of truth; mode is derived.
20. Preview and completion use the same backend policy.
21. Settlement and reversal are atomic linked bundles.
22. A reversal restores payment wallets, allocations, status, and related effects together.
23. The model scales without brute-force wallet combinations.

### Final Fundamental Model

Planned Purchase settlement manages:

```text
Real payment truth
+
Goal protection truth
```

Real payment truth answers:

```text
Which wallets actually lost money, and how much?
```

Goal protection truth answers:

```text
What happened to the protected goal funds after the purchase was completed?
```

Universal final-state formulas:

```text
Real balance after settlement:
B_i_after = B_i_before - P_i

Current goal protection after settlement:
F_i_after = 0

Unused amount:
G - Q

Free-money change per wallet:
DeltaFree_i = F_i - P_i

Global free-money change:
sum(DeltaFree_i) = G - Q
```

These formulas allow Planned Purchase to support all valid N-wallet
combinations through one unified accounting model.
