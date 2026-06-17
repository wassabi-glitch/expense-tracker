# Edge Cases and Bugs Log

Purpose:
This file tracks bugs, edge cases, confusing flows, broken assumptions, and stabilization tasks for Sarflog.

Historical vocabulary note:
Entries are chronological source material. Older budget-health references to `Underfunded` / `underfunded`
are provenance only; EC-111 and G0 supersede them with `Over-Planned` / `over_planned`.

Rule:
Do not keep scary edge cases in memory. Capture them here, classify them, then decide whether to fix now, defer, or reject.

---

## Status Labels

- `NEW` — captured but not reviewed
- `INVESTIGATING` — currently being understood
- `FIX_NOW` — must be fixed before next milestone
- `DEFERRED` — valid but not needed yet
- `REJECTED` — intentionally not supported
- `FIXED` — resolved
- `NEEDS_TEST` — fix exists but needs verification

---

## Severity Labels

- `S0` — data corruption / financial truth broken
- `S1` — core flow blocked
- `S2` — confusing UX or incorrect behavior
- `S3` — rare edge case / polish issue
- `S4` — idea, not bug

---

## Core Invariants

These must never silently break:

1. Wallet balances must follow wallet rules.
2. Debit/cash/prepaid wallets must not spend unavailable money unless explicitly designed otherwise.
3. Credit wallets may represent liability.
4. Drafts are not final financial truth.
5. Finalized expenses affect real financial records.
6. Allocations/goals do not physically move wallet money unless a real transfer exists.
7. Project planned amount and funded amount are different.
8. Asset tracking is optional unless user chooses it.
9. Loan received is borrowed inflow, not earned income.
10. Original currency must never be overwritten by reporting currency.

---

# Entry Template

## EC-000: Short title

**Status:** NEW  
**Severity:** S2  
**Area:** Wallets / Expenses / Budgets / Sessions / Assets / Debts / Goals / Projects / Multicurrency / UI / API  
**Discovered on:** YYYY-MM-DD  
**Reported by:** Me / User / AI Agent / Test  

### Scenario

Describe the real-world situation.

Example:
User has 99k in debit wallet and tries to add a backdated expense that causes the wallet to become negative on an earlier date.

### Steps to Reproduce

1. 
2. 
3. 

### Expected Behavior

What should happen?

### Actual Behavior

What currently happens?

### Why This Matters

Explain what financial truth, UX, or system rule is affected.

### Affected Modules

- Wallets
- Expenses
- Budgets
- Details Page
- API Validation

### Related Invariants

Example:
- Wallet balances must follow wallet rules.
- Historical transaction order matters.

### Decision

Choose one:

- Fix now
- Defer
- Reject / not supported
- Needs more research

### Proposed Fix

Describe the simplest fix.

### UX Copy / Error Message

If user-facing, write the exact message.

Example:
“This transaction cannot be saved because your Debit wallet would become negative on May 3. Add missing income, change wallet, change date, or reduce amount.”

### Test Cases Needed

- [ ] Backend unit test
- [ ] API integration test
- [ ] UI flow test
- [ ] Regression test

### Final Resolution

Write what was actually changed.

### Notes

Extra context, tradeoffs, or future ideas.

---

## EC-001: Quick Add multi-wallet incorrectly uses Session Draft pipeline

**Status:** FIXED  
**Severity:** S1  
**Area:** Expenses / Sessions / API / UI  
**Discovered on:** 2026-05-20  
**Reported by:** User  

### Scenario

User creates one normal expense from Quick Add and pays it from 2+ wallets.

### Expected Behavior

Quick Add should create one non-session `FinancialEvent` with one `EntityLedger` allocation and one or more `WalletLedger` legs.

### Actual Behavior

Frontend routed multi-wallet Quick Add through Session Draft/Basket routes, creating session semantics for a single quick expense.

### Why This Matters

Quick Add and Basket mode have different purposes. Multi-wallet payment is a wallet-leg detail, not proof that the expense is a basket/session.

### Decision

Fix now.

### Proposed Fix

Make `POST /expenses/` accept `wallet_allocations` for both single-wallet and multi-wallet Quick Add. Keep `wallet_id` as temporary backend compatibility only. Update frontend Quick Add to always send `wallet_allocations` and never create session drafts.

### Test Cases Needed

- [ ] API integration test: one wallet allocation creates one non-session event.
- [ ] API integration test: multiple wallet allocations create one non-session event with multiple wallet legs.
- [ ] API integration test: allocation sum mismatch is rejected.
- [ ] API integration test: duplicate wallet allocations are rejected.

---

## EC-002: Expense update should not silently mutate financial truth

**Status:** FIX_NOW  
**Severity:** S1  
**Area:** Expenses / Wallets / Budgets / Projects / API / UI  
**Discovered on:** 2026-05-20  
**Reported by:** User  

### Scenario

User edits an already-created expense.

### Expected Behavior

Only metadata fields should be editable from normal Edit: `title` and `description`.

### Actual Behavior

Current update route allows changing amount, wallet, date, subcategory, and project links for simple one-wallet expenses, causing wallet/budget/project ripple effects.

### Why This Matters

Financial fields are ledger truth. Silent mutation can corrupt wallet history, budget usage, project reporting, refunds, assets, debts, and analytics.

### Decision

Fix now: make normal expense update metadata-only. Financial correction can become a separate explicit future flow with audit trail.

### Proposed Fix

Change `PUT /expenses/{id}` to accept only `title` and `description`. Lock updates for refunded/deleted-incompatible events as before. Frontend should show financial details as locked and explain that wrong financial details require delete/recreate for now.

### Test Cases Needed

- [ ] API integration test: title/description update succeeds for one-wallet Quick Add.
- [ ] API integration test: amount/date/wallet/category/project fields are rejected.
- [ ] API integration test: metadata update works for multi-wallet Quick Add without touching wallet legs.

---

## EC-003: Expense delete should void/reverse instead of hard-delete

**Status:** FIX_NOW  
**Severity:** S1  
**Area:** Expenses / Wallets / Budgets / Projects / API / UI  
**Discovered on:** 2026-05-20  
**Reported by:** User  

### Scenario

User deletes a finalized Quick Add expense.

### Expected Behavior

The original financial event should remain for audit/history and be marked `VOIDED`. A reversal event should undo the exact wallet/entity effects.

### Actual Behavior

Current delete reverses wallet balances and deletes the `FinancialEvent`, erasing historical truth.

### Why This Matters

Hard-delete contradicts immutable ledger semantics. It makes financial history harder to audit and hides why balances/budgets changed.

### Decision

Fix now for normal Quick Add expenses: frontend can still say Delete, but backend implements void/reversal.

### Proposed Fix

Add event status/void metadata to `FinancialEvent`. Change `DELETE /expenses/{id}` to mark the original as `VOIDED`, create a `REVERSAL` event with opposite wallet/entity legs, and exclude voided/reversal events from normal expense lists/reports. Block voiding for refunded, asset-linked, debt/installment-linked, already-voided, or reversal events.

### Test Cases Needed

- [ ] API integration test: one-wallet Quick Add void creates reversal and restores wallet balance.
- [ ] API integration test: multi-wallet Quick Add void reverses every wallet leg exactly.
- [ ] API integration test: voided expense disappears from normal list/get but remains in DB.
- [ ] API integration test: already-voided expense cannot be voided again.

---

## EC-004: Expenses GET route needs feed-aware filtering and precise grouping language

**Status:** PARTIALLY_FIXED  
**Severity:** S2  
**Area:** Expenses / API / UI  
**Discovered on:** 2026-05-21  
**Reported by:** User  

### Scenario

Expenses page now contains different event shapes: Quick Add expenses, multi-wallet expenses, session items, refunds, linked expenses, and merge groups.

### Expected Behavior

`GET /expenses/` should return a production-ready feed that supports primary views: `all`, `quick`, `sessions`, `groups`, `refunds`, and `linked`. Merge groups should appear as folder-like parent rows instead of repeating every child row in the main feed.

### Actual Behavior

The route has been upgraded to return feed items and fold merge groups, but wording and grouping semantics still need cleanup. A multi-wallet expense must not be called a grouped expense. Split expenses should not be treated as `Groups` if the product definition is "one quick expense with internal allocation."

### Why This Matters

Bad grouping language makes users think a two-wallet payment is a grouped/merged expense. This confuses filtering, action availability, refunds, and details navigation.

### Decision

Keep primary feed tabs for now. Delay secondary filter chips until all expense actions are reviewed one by one. Use exact UI language: `multi-wallet`, `session`, `refund`, `linked`, `merged folder`; avoid vague `grouped expense` copy.

### Proposed Fix

Keep the feed-aware route, but later remove split expenses from the `Groups` tab unless the Split feature is redefined as a true group. Update frontend copy/tooltips so multi-wallet expenses are labeled as multi-wallet, not grouped.

### Test Cases Needed

- [ ] API integration test: `view=quick` includes normal one-wallet and multi-wallet Quick Add expenses.
- [ ] API integration test: `view=groups` includes merge folders only unless Split is explicitly redesigned.
- [ ] UI test/manual check: multi-wallet rows show `2 wallets` and never say `grouped expense`.
- [ ] UI test/manual check: merge folders expand to child expenses without duplicating children in the main `all` feed.

---

## EC-005: Split Expense must model one payment with multiple allocation lines

**Status:** IMPLEMENTED_FOR_STABILIZATION  
**Severity:** S1  
**Area:** Expenses / Split Action / Budgets / Wallets / UI  
**Discovered on:** 2026-05-22  
**Reported by:** User  

### Scenario

User Quick Adds one expense, then uses Split Expense to break the payment into multiple line items.

Example:

```text
Parent payment:
Korzinka shopping - 500k

Breakdown:
Groceries - 300k
Household cleaning - 150k
Pet food - 50k
```

### Expected Behavior

Split should mean one real wallet payment with multiple internal budget allocation lines. The parent event remains as the payment container. Split lines become the category/budget truth once they exist.

### Actual Behavior

Current Split implementation has gaps:

- New split form prefills line item 1 with the parent title and full parent amount, which teaches the wrong mental model.
- Split rows only allow subcategory selection under the parent category.
- Split rows do not allow choosing a category per line, so mixed-purpose receipts like Korzinka/Amazon cannot be modeled correctly.
- UI language does not clearly explain that split lines are a breakdown/allocation, not separate wallet payments.
- Split rows do not have a clear action model yet; they should not be treated exactly like full independent expenses.
- Already-split expenses can still open the Split action again, creating ambiguity between "split for the first time" and "edit existing breakdown."

### Why This Matters

Real-world payments often have one wallet charge but multiple budgeting purposes. If split rows inherit only the parent category, budget reporting becomes inaccurate for supermarket, marketplace, mall, receipt scanning, and mixed shopping cases.

### Decision

Keep the parent event. Do not replace it with independent expenses.

Use this model:

```text
FinancialEvent = one real payment
WalletLedger = how the payment was funded
EntityLedger = where the money should be allocated
```

Once split lines exist, budget/category reports should use the split lines as authoritative allocation truth. The parent category is only a default/fallback.

For stabilization, make Split a one-time action:

```text
Unsplitted Quick Add expense -> allow Split Expense once
Already split expense -> block Split Expense
```

Do not implement Edit Breakdown yet. If the saved split is wrong, the supported correction path is delete/void and recreate the expense.

### Proposed Fix

- Remove parent title/amount prefill when creating a new split.
- Add `category` to each split row in schema/backend/frontend.
- Default each split row category to the parent category for speed.
- Make each row's subcategory selector depend on that row's selected category.
- Recalculate/validate each split row against the correct category budget and subcategory budget.
- Keep wallet allocations only at parent event level for now; do not build per-line wallet-to-category mapping yet.
- Do not expose full normal expense actions on split lines yet. Treat line-level actions as a future dedicated design: edit allocation, refund line, mark line as asset, move line to project.
- Backend should reject Split when the event already has multiple entity allocation lines.
- Frontend should hide/disable Split Expense for already-split expenses and explain that breakdown editing is not available yet.

### Action Rules For Split Parents

An expense with split items is still one real parent payment. Its split items are allocation lines, not full independent expense rows. Action availability should follow this rule.

Allowed actions:

- `View`: keep enabled because details page is where the breakdown belongs.
- `Note`: keep enabled because notes are metadata.
- `Edit`: keep enabled only for metadata fields such as `title` and `description`.
- `Merge`: keep enabled at parent-payment level only. Merge folders group real payments, not split lines.
- `Delete`: keep enabled as whole-parent void/delete. Copy must say it voids the entire payment and split breakdown.

Blocked actions:

- `Correct financial details`: block because amount/date/wallet/category corrections would require recalculating split allocations.
- `Split Expense`: block if already split. No Edit Breakdown flow for now.
- `Mark as Asset`: block because only one split line may be an asset, not necessarily the full parent payment.
- `Mark as Recurring`: block until recurring can clone split allocation lines safely.
- `Issue Refund`: block until line-level refund behavior is designed.

Future dedicated actions:

- `Edit Breakdown`: intentionally deferred.
- `Refund split line`: intentionally deferred.
- `Mark split line as asset`: intentionally deferred.
- `Move split line to project`: intentionally deferred.

### Test Cases Needed

- [x] API integration test: one-wallet Quick Add can be split into two lines with total exactly equal to parent amount.
- [x] API integration test: multi-wallet Quick Add can be split without changing wallet legs.
- [x] API integration test: split total mismatch is rejected.
- [x] API integration test: split line can use a different category from parent category.
- [x] API integration test: each split line binds to the correct monthly budget for its own category.
- [ ] API integration test: each split line validates the correct subcategory limit for its own category.
- [x] API integration test: refunded/split-complex expenses cannot use normal refund behavior until line-level refund behavior is designed.
- [x] API integration test: already-split expense cannot be split again.
- [ ] UI manual check: new split form starts with empty line labels/amounts.
- [ ] UI manual check: category selector exists per split row and subcategories change per selected category.
- [ ] UI manual check: already-split expense hides/disables Split Expense with clear explanation.
- [ ] UI manual check: split parent allows View, Note, metadata Edit, Merge, and Delete.
- [ ] UI manual check: split parent blocks Correct financial details, Split again, Mark as Asset, Mark as Recurring, and Issue Refund.
- [ ] UI manual check: split parent delete dialog says it voids the entire payment and split breakdown.

---

## EC-006: Mark as Asset needs Quick Add guardrails

**Status:** NEEDS_FIX  
**Severity:** S1  
**Area:** Expenses / Assets / Refunds / Delete / API / UI  
**Discovered on:** 2026-05-22  
**Reported by:** User  

### Scenario

User Quick Adds an expense and chooses `Mark as Asset`.

Example:

```text
Laptop - 10.2M
Paid from Card + Cash
Current value: 9M
```

### Expected Behavior

Mark as Asset should track a purchased thing the user still owns or controls. Payment method does not matter, so one-wallet and multi-wallet Quick Add expenses can both become assets.

### Actual Behavior

Current backend mostly allows any posted expense to become an asset unless it is already linked or is a split parent. It does not yet fully enforce refund and dependency guardrails.

### Why This Matters

An asset-linked expense becomes lineage for asset lifecycle. If normal refund/delete/correction flows still mutate that expense, asset history can become false.

### Decisions

- Do not hard-block by category. Categories are purpose/life-area envelopes, so `Business/Work -> Chair` can be a valid asset.
- Use soft UX guidance for "good assets" vs "usually not assets".
- Allow multi-wallet Quick Add expenses to become assets.
- Block refunded expenses from Mark as Asset for now.
- Block normal Issue Refund on asset-linked expenses for now.
- Block delete/void of asset-linked expenses while the asset exists.
- Keep `current_value >= 0`; do not force it to be less than or equal to purchase value.
- Defer refund-aware asset acquisition.

### Refund-Aware Asset Ideas Deferred

Real example:

```text
Laptop expense: 10.2M
Store refund: 200k overcharge
User still owns laptop
Net acquisition cost: 10M
```

This is valid in real life, but needs explicit asset-aware flow later:

- `Create asset from net purchase`
- `Asset purchase adjustment`
- `Return asset`
- `Asset-linked partial refund`

Until then, refunded expenses should not become assets and asset-linked expenses should not use normal refund.

### Implemented Fix

- Backend Mark as Asset route should reject refunded expenses.
- Backend Mark as Asset route should reject split parents, session events, and debt/installment-linked expenses.
- Backend direct asset creation with `origin_event_id` should use the same eligibility rules.
- Backend refund route should reject asset-linked expenses.
- Backend delete/void route should continue rejecting asset-linked expenses.
- Frontend should disable Mark as Asset for refunded/split/session/already-linked expenses and show clear reason.
- Frontend Mark as Asset modal should explain that assets are items still owned/controlled, with examples.

### Test Cases

- [x] API integration test: one-wallet Quick Add can be marked as asset.
- [x] API integration test: multi-wallet Quick Add can be marked as asset.
- [x] API integration test: already-refunded expense cannot be marked as asset.
- [x] API integration test: asset-linked expense cannot be refunded through normal expense refund.
- [x] API integration test: asset-linked expense cannot be deleted/voided while asset exists.
- [x] API integration test: direct `/assets` creation with refunded `origin_event_id` is rejected.
- [x] API integration test: direct `/assets` creation with split `origin_event_id` is rejected.
- [ ] UI manual check: Mark as Asset disabled for refunded/split/session/already-linked expenses.
- [ ] UI manual check: modal copy explains assets vs normal consumable/service expenses.

---

## 2026-05-23 Goal Funding Architecture Notes

**Status:** DECIDED  
**Severity:** S0 if violated  
**Area:** Goals / Savings / Wallets / Expenses / Assets / Projects  
**Discovered on:** 2026-05-23  
**Reported by:** User / AI Agent  

### Architectural Changes Made Today

Sarflog's Savings/Goals model has moved away from the old virtual savings-pool flow:

```text
Old:
Wallet -> virtual Savings pool -> Goal
```

The agreed model is now:

```text
Wallet = real money location
Goal = intention
Goal allocation = virtual label/reservation on wallet money
```

The new correct flow:

```text
Wallet -> Goal Allocation -> Goal
```

Important rules:

- Goal allocations do not change wallet balance.
- Goal allocations must never be counted as extra money.
- Goal allocations reduce a wallet's available-for-goals amount.
- A wallet can become over-allocated if real wallet balance later drops below reserved goal allocations.
- Savings Account is a real wallet type, not the same thing as a virtual savings pool.
- Credit/liability wallets cannot fund goals.
- Budgets do not sweep into goals. Budgets remain planning limits.

### Intent Taxonomy Direction

Goal intent should mean:

```text
What workflow happens when the goal money is used?
```

Intent should not mean:

```text
What label, icon, emotion, or template does the goal have?
```

Current direction:

```text
RESERVE
PLANNED_PURCHASE
PAY_OBLIGATION
FUND_PROJECT
```

This section documents edge cases for the first two:

```text
RESERVE
PLANNED_PURCHASE
```

---

## EC-007: Reserve intent must not behave like a completed purchase goal

**Status:** IMPLEMENTED  
**Severity:** S1  
**Area:** Goals / Wallets / UI  
**Discovered on:** 2026-05-23  
**Reported by:** User / AI Agent  

### Scenario

User creates an emergency fund, rainy day fund, family support buffer, or general savings cushion.

Example:

```text
SavingsWallet balance: 20M
Emergency Fund target: 15M
Reserved from SavingsWallet: 15M
```

### Expected Behavior

Reserve goals are protection/storage goals. Reaching the target should not mean the goal is "done" in the same way as buying a laptop.

The UI should communicate:

```text
Target reached
Protected amount: 15M
```

not:

```text
Completed, now spend it
```

### Why This Matters

Reserve goals can stay active for months or years. They are not naturally converted into one final purchase/payment.

### Rules

- `RESERVE` money can stay reserved indefinitely.
- Target reached means "protected target reached", not "ready to complete".
- Unreserving reserve money does not create a wallet transaction.
- Using reserve money requires a real expense/payment event.
- If the real wallet balance drops below reserve allocations, show over-allocation.
- Reserve goals can be funded from multiple eligible wallets.

### Real-World Examples

```text
Emergency fund
Rainy day fund
Medical backup
Job-loss cushion
Family support buffer
Cash safety reserve
General savings cushion
```

### Edge Cases

#### Reserve used for an emergency expense from same wallet

```text
Emergency reserve from SavingsWallet: 15M
Hospital bill paid from SavingsWallet: 3M
```

Expected:

```text
SavingsWallet -3M
Emergency reserve allocation -3M
Emergency reserve remaining: 12M
```

#### Reserve used for an emergency expense from different wallet

```text
Emergency reserve from SavingsWallet: 15M
Hospital bill paid from DebitWallet: 3M
```

Expected:

Do not silently guess. Ask settlement question:

```text
This reserve is saved in SavingsWallet, but you paid from DebitWallet.
What happened?

1. Use reserve funds to cover this payment
2. I paid without using the reserve
3. Change payment wallet
```

#### Paid without using reserve

If user chooses "I paid without using the reserve":

```text
DebitWallet -3M
SavingsWallet unchanged
Emergency reserve allocation unchanged
```

The reserve stays protected.

#### Use reserve funds to cover payment

If user chooses "Use reserve funds to cover this payment":

```text
DebitWallet -3M hospital expense
SavingsWallet -3M transfer
DebitWallet +3M transfer
Emergency reserve allocation -3M
```

Meaning:

```text
Debit was the checkout/payment wallet.
Savings reserve was the real funding source.
```

#### User changes mind

User can unreserve money:

```text
Emergency reserve allocation -2M
SavingsWallet balance unchanged
SavingsWallet available-for-goals +2M
```

No wallet transaction should be created.

#### Wallet over-allocation

```text
SavingsWallet balance: 10M
Emergency reserve allocation: 15M
```

Expected:

```text
Wallet is over-allocated by 5M.
Add money back or reduce reserve allocations.
```

### UX Copy / Error Message

```text
This reserve protects money in SavingsWallet. If you paid from another wallet, choose whether the reserve should cover that payment or stay untouched.
```

### Test Cases Needed

- [x] Reserve allocation does not change wallet balance.
- [x] Reserve can stay active after reaching target.
- [x] Reserve usage from same wallet consumes allocation and creates real expense/payment.
- [x] Reserve usage from different wallet requires settlement choice.
- [x] Paid-outside-reserve leaves reserve allocation unchanged.
- [x] Reserve-funded reimbursement creates real transfer and consumes allocation.
- [x] Wallet over-allocation is detected and displayed.

---

## EC-008: Planned Purchase intent must complete through a real purchase event

**Status:** IMPLEMENTED  
**Severity:** S1  
**Area:** Goals / Expenses / Assets / Wallets / UI  
**Discovered on:** 2026-05-23  
**Reported by:** User / AI Agent  

### Scenario

User saves for one specific purchase.

Examples:

```text
Laptop
Phone
Furniture
Gold
Car
Course payment
Vacation ticket
Medical procedure
```

### Expected Behavior

Planned purchase goals should complete only when a real purchase/payment is recorded.

The action should not be generic:

```text
Mark used
```

The action should be specific:

```text
Record purchase
Buy item
Use for purchase
```

### Why This Matters

The wallet balance changes only when the purchase happens. Goal completion alone is not a financial event.

### Asset Taxonomy Rule

Buying an asset is still a wallet outflow first.

Correct model:

```text
Financial event: asset_purchase or purchase
Wallet -amount
Optional asset record created from the purchase
```

Do not model asset creation as if it magically appears without a payment event.

Completion flow should ask:

```text
Result of purchase:
- Expense only
- Create asset from this purchase
- Create asset plus extra fees/costs
```

### Edge Cases

#### Purchase price equals target/funded amount

```text
Laptop target: 10M
Reserved: 10M
Actual purchase: 10M
```

Expected:

```text
Wallet -10M
Goal allocation -10M
Purchase event created
Goal completed
Optional asset created
```

#### Purchase price lower than reserved amount

```text
Laptop target/reserved: 10M
Actual purchase: 8M
```

Expected:

```text
Wallet -8M
Goal allocation -8M
Leftover reserved: 2M
```

Ask what to do with leftover:

```text
1. Keep remaining 2M reserved
2. Unreserve remaining 2M
3. Move remaining 2M to another goal
```

Do not silently release leftover funds.

#### Purchase price higher than reserved amount

```text
Laptop reserved: 10M
Actual purchase: 12M
```

Expected:

Allow only if payment wallet has enough real money or if user provides another funding source.

```text
Reserved goal coverage: 10M
Extra payment required: 2M
```

Extra 2M is normal spending unless explicitly allocated from another goal/source.

#### User buys before fully funded

```text
Laptop target: 10M
Reserved: 6M
Actual purchase: 10M
```

Expected:

Allow if real wallet rules allow the payment.

```text
Consume 6M reserved goal allocation
Record remaining 4M as normal payment outside goal funds
```

But the UI must state that the goal was only partially funded.

#### User cancels purchase

Expected options:

```text
Unreserve money
Change goal target/title
Convert to RESERVE
Move allocation to another goal
Archive goal
```

#### Purchase refund/return after completion

Deferred design required.

Potential future behavior:

```text
Refund restores wallet money.
Asset may be returned/removed/adjusted.
Goal allocation should not automatically reappear unless user chooses to recreate/reserve it.
```

### Test Cases Needed

- [x] Purchase completion creates real wallet outflow.
- [x] Purchase completion consumes matching goal allocation.
- [x] Expense-only purchase works.
- [x] Asset purchase creates asset linked to purchase event.
- [x] Lower actual price leaves leftover allocation unless user explicitly releases it.
- [x] Generic allocation consume is blocked for planned purchase goals.
- [ ] Higher actual price requires extra real funding source.
- [ ] Partial-funded purchase clearly separates goal-funded and outside-goal amounts.
- [ ] Purchase refund/return behavior remains blocked or explicitly designed.

---

## EC-009: Goal payment wallet differs from funding wallet

**Status:** IMPLEMENTED  
**Severity:** S0  
**Area:** Goals / Wallets / Expenses / Assets / UI / API  
**Discovered on:** 2026-05-23  
**Reported by:** User / AI Agent  

### Scenario

User reserves goal money in one wallet but pays from another wallet.

Example:

```text
SavingsWallet: 10M
DebitWallet: 10M

Laptop Goal:
Reserved from SavingsWallet: 10M

At store:
DebitWallet pays 10M
```

### Problem

There are two different truths:

```text
Funding wallet = where saved/reserved money lives
Payment wallet = wallet/card/cash that actually paid
```

If these differ, the app must not silently guess what happened.

### Rejected Behaviors

Do not silently pretend payment came from the funding wallet:

```text
SavingsWallet -10M
```

if user actually paid from DebitWallet.

Do not silently release goal allocation:

```text
DebitWallet -10M
SavingsWallet unchanged
Goal allocation removed
```

without asking whether saved money should cover the payment.

Do not silently create reimbursement transfer:

```text
SavingsWallet -10M
DebitWallet +10M
```

unless user explicitly chooses that settlement.

### Decision

Use a settlement step when payment wallet differs from goal funding wallet.

Mental model:

```text
Goal funding = money reserved in a drawer
Payment wallet = card/cash used at checkout
Settlement = whether money from the drawer covers the payment
```

### Settlement Options

When payment wallet differs, show:

```text
This goal was funded from SavingsWallet, but you paid from DebitWallet.
What happened?

1. Use goal funds to cover this payment
   Move reserved money from SavingsWallet to DebitWallet.

2. I paid without using goal funds
   Keep SavingsWallet untouched and release/keep allocation depending on intent.

3. Change payment wallet
   Record this payment from the funding wallet instead.
```

### Settlement Mode: DIRECT

Payment wallet is the same as funding wallet.

```text
SavingsWallet -10M purchase
Goal allocation -10M
```

### Settlement Mode: REIMBURSE_PAYMENT_WALLET

Payment wallet differs, but goal funds should cover it.

```text
DebitWallet -10M purchase
SavingsWallet -10M transfer
DebitWallet +10M transfer
Goal allocation -10M
```

Meaning:

```text
Debit was payment instrument.
Savings was real funding source.
```

### Settlement Mode: PAID_OUTSIDE_GOAL_FUNDS

Payment wallet differs and goal funds should not cover it.

For `PLANNED_PURCHASE`:

```text
DebitWallet -10M purchase
SavingsWallet unchanged
Goal allocation released
Goal completed as paid outside goal funds
```

For `RESERVE`:

```text
DebitWallet -3M emergency expense
SavingsWallet unchanged
Reserve allocation unchanged by default
```

Reserve should usually stay protected unless user explicitly unreserves or uses it.

### Multi-Wallet Funding

Goal funded by:

```text
SavingsWallet: 7M
CashWallet: 3M
Total: 10M
```

User pays from DebitWallet and chooses "Use goal funds".

Default reimbursement:

```text
SavingsWallet -7M -> DebitWallet +7M
CashWallet -3M -> DebitWallet +3M
DebitWallet -10M purchase
Goal allocations -10M total
```

Future UX may allow custom settlement split. Default should be proportional or exact-source based.

### Senior Rule

```text
Default: use the wallets that funded the goal.
If payment wallet differs: require explicit settlement choice.
Never silently guess.
```

### UX Copy / Error Message

```text
This payment uses a different wallet than the one funding this goal. Choose whether the saved goal money should cover this payment or stay untouched.
```

### Test Cases Needed

- [x] Same funding/payment wallet uses DIRECT settlement.
- [x] Different payment wallet requires settlement choice.
- [x] Reimbursement settlement creates real transfer legs.
- [x] Paid-outside-goal-funds does not mutate funding wallet.
- [x] Planned purchase paid outside goal funds releases or resolves purchase allocation with explicit user choice.
- [x] Reserve paid outside goal funds leaves reserve intact by default.
- [x] Multi-wallet reimbursement uses deterministic split.
- [x] Reimbursement transfer is created only when user submits explicit reimbursement settlement.

---

## EC-010: Strict goal protection vs reality reconciliation

**Status:** PARTIALLY_FIXED  
**Severity:** S0  
**Area:** Goals / Wallets / Expenses / Transfers / UI / API  
**Discovered on:** 2026-05-24  
**Reported by:** User / AI Agent  

### Core Discovery

Goal allocations should act as protected money.

They do not reduce wallet balance, but they should reduce the wallet's normal free-to-spend amount.

```text
wallet_balance = real money
protected_for_goals = active unreleased goal allocations from wallet
free_to_spend = wallet_balance - protected_for_goals
```

This is a deliberate strictness decision for goals only.

Do not apply this to budgets.

```text
Goals = protected real-money reservations
Budgets = planning limits
```

### Normal In-App Spending Mode

This is the normal expense/transfer creation flow.

Rule:

```text
Normal spending cannot silently consume protected goal money.
```

Example:

```text
Debit Wallet balance: 10M
Camera Goal allocation from Debit: 8M
Free to spend: 2M

User tries to create:
Restaurant expense: 5M from Debit
```

Expected:

```text
Blocked.
Only 2M is free to spend.
8M is protected for goals.
```

Allowed next actions:

```text
Release goal money first
Rebalance goal funding from another wallet
Choose another wallet
Cancel
```

### Strict Spending Validation Diagram

```text
  +----------------------------+
  | User creates normal spend  |
  | wallet: Debit              |
  | amount: 5M                 |
  +-------------+--------------+
                |
                v
  +----------------------------+
  | Check free_to_spend        |
  | balance: 10M               |
  | protected: 8M              |
  | free: 2M                   |
  +-------------+--------------+
                |
      +---------+---------+
      |                   |
      v                   v
 amount <= free      amount > free
      |                   |
      v                   v
  +---------+       +----------------------+
  | POST    |       | BLOCK normal spend   |
  | expense |       | ask for resolution   |
  +---------+       +----------------------+
```

### Reality Reconciliation Mode

This is not the same as normal spending.

It exists only when real life already happened outside Sarflog.

Example:

```text
Debit Wallet in Sarflog: 10M
Camera Goal protected from Debit: 8M
Free to spend: 2M

Real world:
User already paid 4M restaurant expense from Debit card.
```

Sarflog cannot pretend this did not happen.

But Sarflog also should not silently weaken goal protection.

So the expense should enter a reconciliation flow.

Correct wording:

```text
Normal spending is blocked if it violates protected goal money.

If the user already spent money outside Sarflog, they enter Reconciliation Mode.
Sarflog records reality only after the user resolves the damaged goal allocation.
```

### Important Correction: Remove "Temporary Over-Allocation" as a Resolution

Previous candidate option:

```text
Mark wallet over-allocated
Fix later
```

Decision:

```text
Do not offer this as a normal user-facing resolution.
```

Reason:

```text
Over-allocation is a problem state, not a solution.
Letting the user choose it weakens the strict protection model.
```

Over-allocation can still exist as a detected warning state if the system discovers inconsistency, but it should not be presented as a clean resolution button.

Better options:

```text
1. Reduce goal allocation
2. Rebalance goal funding from another wallet
3. Cancel
```

### Reconciliation Example

Initial:

```text
Debit Wallet: 10M
Camera Goal allocation from Debit: 8M
Free to spend: 2M
```

Real-world overspend:

```text
Restaurant expense: 4M from Debit
Conflict amount: 2M
```

Reconciliation dialog:

```text
This real expense uses 2M protected for Camera Goal.

Choose how to resolve it:

1. Reduce Camera Goal allocation by 2M
   Debit balance becomes 6M
   Camera allocation from Debit becomes 6M
   Camera Goal becomes 2M short

2. Move 2M Camera funding to another wallet
   Debit balance becomes 6M
   Debit Camera allocation becomes 6M
   Another wallet adds 2M Camera allocation
   Camera Goal stays funded

3. Cancel
   Do not record the expense
```

### Reconciliation Diagram

```text
REAL-WORLD OVERSPEND ALREADY HAPPENED

  +----------------------------+
  | User logs real expense     |
  | Debit -4M                  |
  +-------------+--------------+
                |
                v
  +----------------------------+
  | Sarflog checks free spend  |
  | free_to_spend: 2M          |
  | conflict: 2M               |
  +-------------+--------------+
                |
                v
  +----------------------------+
  | Reconciliation required    |
  +-------------+--------------+
                |
     +----------+----------+----------+
     |                     |          |
     v                     v          v
 Reduce allocation    Rebalance    Cancel
 Camera -2M           from wallet   no post
     |                     |
     v                     v
 Goal short by 2M    Goal stays
                    funded
```

### Conditional UI Rule

Do not add a permanent parallel "Add reconciliation expense" button next to normal quick add.

Better:

```text
User uses normal Add Expense.
Sarflog detects goal-protection conflict.
Sarflog opens reconciliation dialog conditionally.
```

This keeps the common flow simple and prevents users from treating reconciliation as a normal expense mode.

### API Direction

Normal endpoint:

```text
POST /expenses
```

Default behavior:

```text
Strictly enforce wallet.free_to_spend.
```

If conflict:

```json
{
  "detail": "expenses.goal_protection_conflict",
  "wallet_id": 1,
  "free_to_spend": 2000000,
  "expense_amount": 4000000,
  "conflict_amount": 2000000,
  "affected_goal_allocations": []
}
```

Then frontend opens reconciliation dialog.

Possible follow-up endpoint:

```text
POST /expenses/reconcile
```

Payload should include:

```text
original expense payload
resolution: REDUCE_GOAL | REBALANCE_GOAL
affected goal allocation details
```

Alternative:

```text
POST /expenses with mode = RECONCILIATION
```

But a separate endpoint is cleaner because it prevents accidental bypass of strict spending validation.

### Rejected Option: Pending Reconciliation

Previous candidate:

```text
Save pending reconciliation
Decide later
```

Decision:

```text
Do not offer pending reconciliation for this flow.
```

Reason:

```text
It creates too much freedom and complexity.
It lets the user delay the core decision.
It requires unresolved expense states, reminders, and cleanup rules.
It weakens the strict goal protection model.
```

If the user wants to record a real-world overspend, they must decide now:

```text
Reduce the affected goal allocation
or
Rebalance the affected goal allocation
or
Cancel
```

### Settlement Amendment

This strict protection model also affects EC-009.

If payment wallet differs from goal funding wallet and user chooses to use goal funds, do not automatically record a completed reimbursement transfer unless the user confirms the real-world transfer happened.

Preferred flow:

```text
Debit paid purchase.
Savings funded goal.
User chooses "use goal funds".
Sarflog creates pending reimbursement instruction.
User physically transfers Savings -> Debit.
User confirms.
Sarflog records transfer and consumes goal allocation.
```

This avoids fake wallet balances.

### What To Implement

- [x] Add wallet `free_to_spend` calculation: balance minus active unreleased goal allocations.
- [x] Enforce `free_to_spend` for normal Quick Add expense creation.
- [x] Enforce `free_to_spend` for normal session-draft finalization.
- [ ] Enforce `free_to_spend` for normal wallet transfers.
- [x] Return structured `expenses.goal_protection_conflict` when normal spending violates protected goal money.
- [ ] Add conditional reconciliation dialog in expense UI.
- [ ] Support `REDUCE_GOAL` reconciliation.
- [ ] Support `REBALANCE_GOAL` reconciliation.
- [ ] Remove "temporary over-allocation" as a normal resolution option.
- [ ] Do not offer pending reconciliation as a normal resolution option.
- [x] Add tests that normal spending is blocked when it exceeds free-to-spend.
- [ ] Add tests that reconciliation can reduce affected goal allocation.
- [ ] Add tests that reconciliation can rebalance goal allocation to another eligible wallet.
- [ ] Add tests that reconciliation requires an immediate reduce/rebalance decision.

Checkpoint 4 implementation note:

```text
Normal expense paths now respect goal protection:
- Quick Add expense
- Session draft finalize

Goal-specific use paths intentionally bypass this normal-spending guard because they consume/settle protected goal funding as part of the goal workflow.
```

### Final Rule

```text
Strict protection by default.
Conditional reconciliation when reality already happened.
Over-allocation is a warning/problem state, not a resolution.
Pending reconciliation is rejected for this flow.
```

---

## EC-011: Goal purchase paid from multiple wallets while funded from different wallet(s)

**Status:** IMPLEMENTED
**Severity:** S0
**Area:** Goals / Expenses / Wallet Ledger / Entity Ledger / Settlement / API
**Discovered on:** 2026-05-24
**Reported by:** User / AI Agent

### Scenario

User funds a planned purchase goal from one wallet, but buys the item using multiple payment wallets.

Example:

```text
Cash Wallet: 10M
Debit Wallet: 10M

Fridge Goal:
funded from Cash Wallet: 10M
```

Purchase day:

```text
Fridge price: 10M

Paid:
Cash: 5M
Debit: 5M
```

### Core Discovery

A single payment-wallet field is rejected for goal completion.

Goal purchase completion should use:

```text
payment_allocations[]
```

Even a one-wallet purchase should be represented as one item in `payment_allocations[]`.

Example API shape:

```json
{
  "amount": 10000000,
  "payment_allocations": [
    { "wallet_id": 1, "amount": 5000000 },
    { "wallet_id": 2, "amount": 5000000 }
  ],
  "settlement_mode": "REIMBURSE_PAYMENT_WALLET"
}
```

Invariant:

```text
sum(payment_allocations.amount) == purchase_amount
```

### Why This Fits The Three-Pillar Ledger

This is a natural fit for the 3-pillar architecture.

```text
FinancialEvent = what happened
WalletLedger = where money moved
EntityLedger = what category/object absorbed the value
GoalContributions = how protected goal allocation was consumed/released
```

Purchase event:

```text
FinancialEvent
- type: EXPENSE
- title: Fridge
- reference_type: goal_purchase
```

Wallet truth:

```text
WalletLedger
- event_id: purchase, wallet_id: Cash,  amount: -5M
- event_id: purchase, wallet_id: Debit, amount: -5M
```

Category/object meaning:

```text
EntityLedger
- event_id: purchase
- category: Electronics or Housing
- amount: 10M
- budget_id: ...
```

Goal allocation:

```text
GoalContributions
- goal_id: Fridge
- wallet_id: Cash
- type: CONSUME or RETURN
- linked_event_id: purchase
```

If reimbursement is needed, that should be a separate transfer event:

```text
FinancialEvent
- type: TRANSFER
- reference_type: goal_reimbursement

WalletLedger
- Cash:  -5M
- Debit: +5M
```

### Interpretation 1: Full Goal Funds The Purchase

This should be the recommended/default interpretation for a completed planned purchase.

Meaning:

```text
The protected Cash goal money should ultimately pay for the whole fridge.
Debit was only a payment instrument for 5M.
```

Records:

```text
Purchase:
Cash -5M
Debit -5M

Settlement:
Cash -5M
Debit +5M

Goal:
Cash allocation consumed: 10M
Goal completed
```

Final state:

```text
Cash: 0
Debit: 10M
Fridge Goal: completed
```

Important:

```text
The settlement transfer must only be marked complete if the real-world transfer happened.
```

If the user still needs to physically move cash/deposit money/reimburse Debit, a future pending reimbursement workflow can handle that.

### Interpretation 2: Only The Direct Goal-Wallet Payment Uses Goal Funds

Alternative meaning:

```text
The user used 5M of the Cash goal fund and 5M of normal Debit money.
```

Records:

```text
Purchase:
Cash -5M
Debit -5M

Goal:
Cash allocation consumed: 5M
remaining Cash allocation resolved explicitly
outside-goal amount: 5M
```

For a completed purchase, do not leave stale money allocated to the already-bought item unless there is a clear related purpose.

Recommended result:

```text
Consume 5M from goal allocation.
Release remaining 5M from goal allocation.
Complete goal.
```

Final state:

```text
Cash: 5M
Debit: 5M
Fridge Goal: completed
Outside-goal amount: 5M
```

Exception:

```text
If the remaining 5M is intentionally for delivery, installation, warranty, or accessories,
the app should ask user to keep/convert it as a related goal/project allocation.
```

### UX Rule

When purchase payment wallets differ from goal funding wallets, compare:

```text
goal funding sources
payment allocations
```

Example:

```text
Goal funded by:
Cash 10M

Purchase paid by:
Cash 5M
Debit 5M
```

Show:

```text
Fridge Goal was funded from Cash, but 5M was paid from Debit.

How should Sarflog handle the Debit-paid part?
```

Recommended options:

```text
1. Use Fridge goal funds
   Cash goal funds cover the full purchase.
   Create/confirm Cash -> Debit reimbursement for 5M.

2. Pay 5M outside goal funds
   Consume 5M Cash goal allocation.
   Release or redirect the remaining 5M.

3. Cancel
```

Avoid:

```text
Silently pretending the Debit payment came from Cash.
Silently leaving unused goal money allocated to a completed purchase.
Silently creating reimbursement transfers that did not happen in real life.
```

### Implementation Direction

Implementation target:

```text
Goal use payload should accept payment_allocations[] only.
```

Required validations:

```text
sum(payment_allocations) == purchase amount
each payment wallet belongs to user
each payment wallet has sufficient real balance/allowed limit
goal settlement cannot consume more unreleased allocation than exists
reimbursement transfer is posted only for explicit REIMBURSE_PAYMENT_WALLET settlement
```

Implementation note:

```text
Current checkpoint posts reimbursement transfers when the user explicitly chooses reimbursement settlement.
A separate pending-reimbursement confirmation workflow is still deferred.
```

### What To Implement

- [x] Add `payment_allocations[]` support to planned purchase goal completion.
- [x] Create one purchase `FinancialEvent` with multiple `WalletLedger` legs.
- [x] Create one `EntityLedger` category allocation for total purchase amount.
- [x] Add settlement planning when payment wallets differ from goal funding wallets.
- [x] Support full-goal-funded settlement with reimbursement.
- [x] Support partial-goal-funded / outside-goal amount settlement.
- [x] Require explicit user choice for leftover completed-goal allocation.
- [x] Add tests for one funding wallet + two payment wallets.
- [x] Add tests for multi-funding wallets + multi-payment wallets.
- [x] Add tests that reimbursement transfer is not silently posted without explicit settlement.

### Final Rule

```text
Payment allocations describe how checkout was paid.
Goal funding sources describe which protected money should bear the cost.
Settlement reconciles the difference.
The three-pillar ledger can represent this cleanly.
```

---

## EC-012: Wallet outflows, transfers, archive, credit repayment, and overdraft can break goal allocations

**Status:** PARTIALLY_FIXED
**Severity:** S0
**Area:** Goals / Wallets / Transfers / Archive / Credit / Overdraft / Assets / API
**Discovered on:** 2026-05-24
**Reported by:** User / AI Agent

### Problem

The strict goal-protection model cannot apply only to expenses.

Any operation that reduces a wallet balance can make that wallet unable to support its active goal allocations.

Affected operations:

```text
expense
transfer out
credit card repayment
loan repayment
bank deposit funding
asset purchase
currency exchange
wallet replacement
wallet archive preparation
```

### Core Invariant

For every wallet that can hold owned money:

```text
owned_positive_balance = max(wallet.balance, 0)
protected_for_goals = sum(active unreleased goal allocations from wallet)
free_owned_outflow = owned_positive_balance - protected_for_goals
```

Normal wallet outflow is allowed only if:

```text
outflow_amount <= free_owned_outflow
```

If this is false, the action touches protected goal money.

Goal allocations can only remain attached to a wallet while:

```text
owned_positive_balance >= protected_for_goals
```

### Archive Rule

Wallet archive must require:

```text
wallet.balance == 0
active_goal_allocations == 0
pending_goal_settlements == 0
```

For credit/overdraft-style wallets, also require:

```text
outstanding_debt == 0
overdraft_used == 0
pending_repayments == 0
```

### Flow Diagram

```text
WALLET OUTFLOW REQUESTED
expense, transfer, repayment, deposit, asset buy, archive prep

  +-------------------------------+
  | Compute wallet availability   |
  | balance                       |
  | protected_for_goals           |
  | free_owned_outflow            |
  | overdraft/credit capacity     |
  +---------------+---------------+
                  |
                  v
  +-------------------------------+
  | amount <= free_owned_outflow? |
  +---------------+---------------+
          | yes                  | no
          v                      v
  +-------------------+   +------------------------------+
  | Allow normally    |   | Goal protection conflict     |
  +-------------------+   +---------------+--------------+
                                           |
        +----------------------+-----------+-----------+----------------------+
        |                      |                       |                      |
        v                      v                       v                      v
 Intended goal use     Transfer/replacement     Real-life reconcile     Borrowed/credit
 consume allocation    move allocation          reduce/rebalance        explicit debt use
```

### Case 1: Archive Wallet With Goal Allocations

Example:

```text
Old Debit balance: 10M
Camera Goal allocation from Old Debit: 8M
Free: 2M
```

If user tries to archive this wallet, Sarflog must block.

Reason:

```text
The wallet still backs 8M of protected goal money.
Archiving would leave Camera Goal pointing to a closed/empty wallet.
```

Allowed resolutions:

```text
1. Move Camera allocation to another eligible wallet.
2. Release/reduce Camera allocation.
3. Cancel archive.
```

If user is replacing the wallet:

```text
Transfer Old Debit -> New Debit: 10M
Move Camera allocation Old Debit -> New Debit: 8M
Old Debit balance becomes 0
Old Debit goal allocations become 0
Archive Old Debit
```

### Case 2: Transfer Only Free Money

Example:

```text
Old Debit balance: 10M
Camera protected: 8M
Free: 2M

Transfer Old Debit -> Cash: 2M
```

Allowed.

Final:

```text
Old Debit balance: 8M
Camera protected: 8M
Free: 0
```

### Case 3: Transfer More Than Free Money

Example:

```text
Old Debit balance: 10M
Camera protected: 8M
Free: 2M

Transfer Old Debit -> New Debit: 5M
```

This touches:

```text
2M free money
3M protected Camera money
```

Normal transfer should be blocked.

Resolution options:

```text
1. Move 3M Camera allocation to New Debit.
2. Reduce/release 3M Camera allocation.
3. Transfer only the 2M free amount.
4. Cancel.
```

If moving allocation:

```text
Old Debit balance: 5M
New Debit balance: 5M

Camera allocation:
Old Debit: 5M
New Debit: 3M
Total: 8M
```

### Case 4: Credit Card Repayment From Protected Wallet

Example:

```text
Debit balance: 10M
Camera protected: 8M
Free: 2M
Credit card debt: 5M

Pay credit card from Debit: 5M
```

This is not a normal wallet-to-wallet transfer.

It is a repayment from owned money to a liability.

Sarflog should block normal repayment:

```text
Only 2M is free.
3M is protected for Camera Goal.
```

Options:

```text
1. Pay only 2M.
2. Release/reduce 3M from Camera Goal.
3. Move 3M Camera funding to another eligible wallet.
4. Choose another payment wallet.
5. Cancel.
```

Credit wallet rule:

```text
Credit wallets cannot fund goals.
Credit wallets cannot hold goal allocations.
Credit repayments must respect protected money in the source wallet.
```

### Case 5: Debit Wallet With Overdraft

Example:

```text
Debit1 balance: 3M
Overdraft limit: 10M
Camera Goal allocation from Debit1: 3M
Free owned money: 0

Transfer Debit1 -> Debit2: 10M
```

In the bank, this may be allowed if overdraft transfers are allowed.

In Sarflog, this is not a normal transfer.

It means:

```text
3M protected owned money is affected
7M overdraft/borrowed money is used
```

Valid resolutions:

```text
1. Move the 3M Camera allocation to Debit2.
   Debit1 becomes -7M.
   Debit2 receives 10M.
   Camera Goal stays funded from Debit2.

2. Reduce/release the 3M Camera allocation.
   Debit1 becomes -7M.
   Debit2 receives 10M.
   Camera Goal becomes short by 3M.

3. Cancel.
```

Invalid:

```text
Keep Camera allocation on Debit1 after Debit1 becomes -7M.
```

Reason:

```text
Overdraft is borrowed capacity.
Borrowed capacity cannot back goal funding.
Goal allocations are backed only by owned positive wallet balance.
```

### Case 6: Bank Deposit Or Asset Purchase From Protected Wallet

Example:

```text
Debit balance: 20M
Wedding Goal protected: 15M
Free: 5M

Open bank deposit from Debit: 10M
```

This touches 5M protected Wedding money.

Until goal allocations can point to assets, Sarflog should not move goal funding into the bank deposit asset automatically.

Valid resolutions:

```text
1. Open deposit with only free 5M.
2. Move 5M Wedding funding to another eligible wallet.
3. Reduce/release 5M Wedding funding.
4. Cancel.
```

### Implementation Direction

Add or centralize:

```text
WalletAvailabilityService
```

It should return:

```text
wallet_balance
owned_positive_balance
protected_for_goals
free_owned_outflow
overdraft_remaining
credit_capacity
affected_goal_allocations_if_outflow(amount)
```

Every route that creates wallet outflow should call this service:

```text
expenses
transfers
wallet archive
credit repayment
loan repayment
bank deposit creation
asset purchase
currency exchange
project-funded spending
goal completion spending
```

Goal-linked spending can intentionally consume protected money, but normal spending and normal transfers cannot.

### What To Implement

- [x] Add `WalletAvailabilityService` or equivalent shared domain service.
- [x] Enforce free-owned-outflow checks for transfer-out flows.
- [x] Enforce active allocation check before wallet archive.
- [x] Block archive unless `balance = 0`, `active_goal_allocations = 0`, and no pending settlements.
- [x] Add wallet replacement flow that moves balance and allocations together.
- [x] Add transfer resolution: move allocation, reduce/release allocation, transfer free amount only, cancel.
- [x] Ensure credit wallets cannot fund goals or hold allocations.
- [x] Treat credit-card destination transfers as repayments.
- [x] Treat overdraft usage as explicit borrowed/debt usage when protected allocations are affected.
- [x] Ensure goal allocations only use positive owned balance, not overdraft or credit capacity.
- [x] Add tests for archiving a zero-balance wallet with active goal allocations.
- [x] Add tests for full balance transfer from wallet with goal allocations.
- [x] Add tests for partial transfer that touches protected money.
- [x] Add tests for credit repayment from protected wallet.
- [x] Add tests for overdraft transfer where allocation must move or shrink.
- [x] Add tests that allocation cannot remain on a negative-balance wallet.
- [x] Enforce goal protection for wallet fee/interest/reconciliation outflows.
- [x] Enforce goal protection for debt and installment outflows.
- [ ] Add richer dedicated UI for full wallet replacement/archive-assisted migration.
- [ ] Add pending settlement model if later required.

Checkpoint implementation note:

```text
Transfer API now supports explicit goal-resolution modes:
- MOVE_TO_DESTINATION: move the required affected goal allocation to the destination wallet.
- RELEASE: release/reduce the required affected goal allocation from the source wallet.

No resolution:
- transfer is blocked if it would make the source wallet unable to back its goal allocations.

Wallet archive:
- blocked when active goal allocations remain, even if balance is already 0.

Overdraft:
- overdraft may move money only if any affected protected allocation is moved or released immediately.
- goal allocation is never allowed to remain backed by negative balance/borrowed capacity.
```

### Final Rule

```text
Goal allocations are protected claims on owned wallet money.
Any wallet outflow must respect those claims.
If money moves to another eligible wallet, the allocation may move with it.
If money leaves owned wallets or becomes borrowed/asset money, the allocation must be reduced, released, or rebalanced.
Credit and overdraft capacity cannot fund goals.
Wallet archive requires zero balance, zero allocations, zero pending settlement, and zero debt.
```

---

## EC-013: Goal Funding Can Exceed Target Amount

**Status:** FIXED
**Severity:** S1
**Area:** Goals / Goal Allocations / Savings Page / API Validation
**Discovered on:** 2026-05-24
**Reported by:** User

### Problem

Current code allows a user to allocate more money to a goal than the goal's target amount.

Example:

```text
Camera Goal target: 10M
Already funded: 8M

User allocates: 5M

Result:
Funded amount: 13M
Target amount: 10M
```

This should not happen for the current goal model.

### Why This Is Wrong

Goal allocation means:

```text
This much real wallet money is protected for this specific goal.
```

If the target is 10M, the app should not protect 13M for that goal unless we deliberately add an overfunding feature later.

Overfunding causes confusing states:

```text
progress > 100%
remaining amount = 0 but extra money still reserved
completion actions become ambiguous
unused allocation has to be released manually
wallet free-to-spend becomes lower than necessary
```

### Correct Invariant

For active goals:

```text
goal_funded_amount <= goal.target_amount
```

Allocation must satisfy:

```text
new_allocation_amount <= goal.target_amount - current_funded_amount
```

If not:

```text
Reject with goals.allocation_exceeds_target
```

### Expected UX

If user tries to overfund:

```text
This goal only needs 2M more.
You cannot allocate 5M.
```

Possible UI helper:

```text
[Fund remaining 2M]
```

### Related Rules

Target edits must also respect existing funding:

```text
target_amount >= current_funded_amount
```

This rule already exists conceptually as:

```text
goals.target_below_funded_amount
```

But allocation creation must enforce the other side too:

```text
funded_amount must not grow above target_amount
```

### What To Implement

- [x] Add backend validation in goal allocation endpoint.
- [x] Reject allocation when `current_funded_amount + amount > target_amount`.
- [x] Return `goals.allocation_exceeds_target`.
- [x] Update frontend error localization.
- [x] In the funding UI, cap suggested/default amount to remaining goal amount.
- [x] Add tests for overfunding blocked from one wallet.
- [x] Add tests for overfunding blocked across multiple allocations.
- [x] Add tests that exact remaining allocation succeeds.

### Final Rule

```text
Goals can be fully funded, not overfunded.
Extra wallet money should remain unallocated/free unless the user creates or funds another goal.
```

---

## EC-014: Completed Goal Allows Second Purchase

**Status:** FIX_NOW
**Severity:** S0
**Area:** Goals / Planned Purchase / Expense Creation / Frontend Actions / API Validation
**Discovered on:** 2026-05-24
**Reported by:** User

### Problem

Current UI still shows `Record purchase` for a goal that has already completed a purchase.

Current backend may allow calling the planned purchase endpoint again for the same goal.

Example:

```text
Goal: Laptop
Intent: PLANNED_PURCHASE
Status: COMPLETED
linked_expense_event_id: 123

User clicks Record purchase again.
```

This must be rejected.

### Why This Is Wrong

A planned-purchase goal represents one purchase lifecycle:

```text
Reserve money -> record the real purchase -> consume/release goal allocation -> complete goal
```

After that purchase is recorded, the goal has already resolved into a real financial event.

Allowing a second purchase causes:

```text
duplicate expenses
duplicate asset creation possibility
incorrect consumed/outside-goal amounts
confusing completed goal history
ambiguous "what did this goal buy?" relationship
```

### Correct Invariant

For a planned-purchase goal:

```text
linked_expense_event_id can be set only once.
```

If:

```text
goal.status == COMPLETED
AND goal.linked_expense_event_id IS NOT NULL
```

then:

```text
POST /goals/{goal_id}/record-purchase must reject.
```

Expected backend error:

```text
goals.purchase_already_recorded
```

### Expected Frontend Behavior

For a completed planned-purchase goal with `linked_expense_event_id`:

```text
Disable or hide Record purchase button.
```

Preferred UI:

```text
[Purchase recorded]
```

or:

```text
View purchase
```

if expense detail navigation exists.

Do not show an active `Record purchase` button.

### Edge Cases

If a purchase was recorded incorrectly:

```text
User should void/correct the linked expense first.
```

Do not solve this by allowing a second purchase on the same goal.

If user wants to buy accessories later:

```text
Create a new related goal
or convert remaining money into a project/reserve
```

Do not attach a second primary purchase to the original completed planned-purchase goal.

### What To Implement

- [x] Add backend guard in planned purchase endpoint.
- [x] Reject if `goal.linked_expense_event_id` is already set.
- [x] Reject if `goal.status == COMPLETED` and goal already has a real-world completion event.
- [x] Return `goals.purchase_already_recorded`.
- [x] Add frontend error localization.
- [x] Disable/hide `Record purchase` button for already purchased goals.
- [ ] Optionally show `View purchase` if linked expense details are routable.
- [x] Add tests that a second planned purchase is rejected.
- [ ] Add tests that frontend action state is derived from `linked_expense_event_id` / completed status.

### Final Rule

```text
One planned-purchase goal can resolve into one purchase event only.
After purchase completion, the goal is read-only for purchase recording.
```

---

## EC-015: Goal Purchase Allows Future-Dated Expense

**Status:** FIX_NOW
**Severity:** S0
**Area:** Goals / Planned Purchase / Reserve Use / Expense Date Validation / Frontend Calendar
**Discovered on:** 2026-05-24
**Reported by:** User

### Problem

The current goal purchase flow can create a real expense with a future date.

This is wrong because goal purchase completion creates a posted `FinancialEvent` of type `EXPENSE`.
Posted real expenses must not be future-dated.

### Current Findings

Quick Add expense creation is protected correctly.

Backend:

```text
app/routers/expenses.py
create_expense()

local_today = today_in_tz(user_tz)
if expense.date > local_today:
    reject with expenses.date_in_future
```

This uses request/user timezone through:

```text
get_effective_user_timezone
today_in_tz(user_tz)
```

Frontend Quick Add is also protected.

Frontend:

```text
frontend/src/features/expenses/Expenses.jsx
Quick Add date input:
max={todayISO}
```

Schema:

```text
frontend/src/features/expenses/expenseSchemas.js
dateSchema:
v <= toISODateInTimeZone()
```

So normal Quick Add blocks future dates both in the UI and backend.

Goal purchase is not protected correctly.

Backend:

```text
app/routers/goals.py
record_planned_purchase_goal()

effective_date = payload.date or today_in_tz(user_tz)
```

But there is currently no:

```text
if effective_date > today_in_tz(user_tz):
    reject
```

Then `_create_goal_expense_event()` creates the expense event with:

```text
date=expense_date
```

So a future `payload.date` can become a posted expense.

Frontend:

```text
frontend/src/features/savings/Savings.jsx
Goal use / Record purchase date input
```

Current input has:

```text
type="date"
value={useForm.date || ""}
```

But it does not set:

```text
max={todayISO}
```

Schema:

```text
frontend/src/features/savings/savingsSchemas.js
goalUseFormSchema.date
```

Currently accepts optional string and does not reject future dates.

### Why This Is Severe

Goal purchase creates real financial truth:

```text
wallet balances decrease
expense event is posted
budget/category spending is updated
goal allocation is consumed/released
optional asset can be created
```

If the date is in the future, the app can produce impossible financial state:

```text
wallet balance reduced today by an expense dated tomorrow
future budget can be materialized through goal purchase
analytics and dashboards may disagree by date
goal marked completed before the real purchase day
```

### Correct Invariant

Any route that creates a posted expense must enforce:

```text
expense_date <= today_in_user_timezone
```

This includes:

```text
POST /expenses/
POST /expenses/session-drafts
POST /expenses/session-drafts/{id}/finalize
POST /goals/{goal_id}/use-reserve
POST /goals/{goal_id}/record-purchase
```

### Expected Backend Behavior

For goal purchase:

```text
effective_date = payload.date or today_in_tz(user_tz)

if effective_date > today_in_tz(user_tz):
    raise HTTPException(400, "expenses.date_in_future")
```

Use the same error as Quick Add:

```text
expenses.date_in_future
```

Do not invent a goal-specific error, because the rejected object is a real expense date.

### Expected Frontend Behavior

Goal use / Record purchase dialog must:

```text
set date max to today in browser timezone
validate date <= today before submit
show expenses.dateFuture localization
```

Example:

```text
<Input type="date" max={todayISO} ... />
```

Schema should mirror Quick Add:

```text
date <= toISODateInTimeZone()
```

### What To Implement

- [x] Add backend future-date guard in `record_planned_purchase_goal`.
- [x] Add backend future-date guard in `use_reserve_goal` because it uses the same posted-expense creation path.
- [x] Consider moving the guard into `_create_goal_expense_event()` so all goal-created expenses are protected centrally.
- [x] Reuse `expenses.date_in_future`.
- [x] Add frontend `max={todayISO}` to the goal use / record purchase date input.
- [x] Add future-date validation to `goalUseFormSchema`.
- [x] Add backend test that future-dated goal purchase is rejected.
- [x] Add backend test that future-dated reserve use is rejected.
- [ ] Add frontend/unit/schema test if frontend validation tests exist.

### Final Rule

```text
Goal purchase is still expense creation.
Any posted expense created from goals must obey the same timezone-aware future-date rules as Quick Add.
```

---

## EC-016: Goal-Created Expenses Can Drift From Quick Add Expense Rules

**Status:** FIX_NOW
**Severity:** S1
**Area:** Expenses / Goals / FinancialEvent / WalletLedger / EntityLedger
**Discovered on:** 2026-05-24
**Reported by:** User

### Problem

Goal purchase currently creates a real expense using the same accounting tables as Quick Add, but it does not go through the same expense posting code path.

Quick Add:

```text
POST /expenses/
-> create_expense()
-> FinancialEvent
-> WalletLedger
-> EntityLedger
-> budget validation
-> wallet balance update
```

Goal purchase:

```text
POST /goals/{goal_id}/record-purchase
-> record_planned_purchase_goal()
-> _create_goal_expense_event()
-> FinancialEvent
-> WalletLedger
-> EntityLedger
-> goal_contributions
-> goal lifecycle updates
```

This is directionally correct because goal purchases are real expenses. The bug is that the expense posting logic is duplicated, so validation rules can drift.

### Concrete Example

Quick Add blocks a future-dated expense:

```text
if expense.date > today_in_tz(user_tz):
    reject expenses.date_in_future
```

Goal purchase currently has its own helper:

```text
_create_goal_expense_event(...)
```

If that helper misses the same date guard, goal purchase can create a future-dated posted expense even though Quick Add rejects it.

This is exactly the class of bug caused by two expense posting paths.

### Correct Mental Model

There should be one shared expense-posting core:

```text
ExpensePostingService
```

Both flows should use it:

```text
Quick Add Expense
-> ExpensePostingService

Goal Purchase
-> ExpensePostingService
-> goal consume / return / settlement lifecycle
```

Goal purchase should add goal-specific side effects, not reimplement the base expense rules.

### Same Tables, Different Orchestration

Both Quick Add and goal purchase should write the same core accounting truth:

```text
financial_events
wallet_ledger
entity_ledger
wallet balance adjustment
budget/category impact
```

Goal purchase additionally writes:

```text
goal_contributions with CONSUME / RETURN
goals.linked_expense_event_id
goals.status = COMPLETED for planned purchases
optional asset row
optional reimbursement transfer events
```

So the desired architecture is not:

```text
separate fake goal expense system
```

It is:

```text
shared real expense posting + goal lifecycle wrapper
```

### Rules That Must Not Drift

The shared posting service should own:

```text
future-date validation
wallet allocation total validation
wallet ownership and active-state validation
goal-protected free-to-spend validation where applicable
budget materialization/resolution
budget limit validation
subcategory/project validation where supported
WalletLedger creation
EntityLedger creation
FinancialEvent creation
wallet balance adjustment
```

Goal purchase should own only:

```text
goal intent validation
settlement mode handling
goal funding consumption
goal funding return/release
goal completion status
linked expense/asset pointers
reimbursement transfer orchestration
```

### What To Implement

- [x] Extract an `ExpensePostingService` or equivalent shared backend helper.
- [x] Move common expense creation validation and ledger writes into that service.
- [x] Make `POST /expenses/` use the shared service.
- [x] Make `_create_goal_expense_event()` use the shared service instead of manually duplicating the write path.
- [x] Keep goal-specific lifecycle logic in `goals.py` after the expense event is posted.
- [x] Add tests proving Quick Add and goal purchase reject the same invalid expense date.
- [x] Add tests proving both paths write `FinancialEvent`, `WalletLedger`, and `EntityLedger` consistently.
- [x] Add tests proving goal purchase still writes `GoalContributions` and links `goals.linked_expense_event_id`.

### Final Rule

```text
Goal purchase is a real expense with extra goal lifecycle behavior.
It must share the same base expense-posting rules as Quick Add.
Do not let goal-created expenses become a second accounting path.
```

---

## EC-017: Goal Funding Must Support Multiple Wallets

**Status:** FIXED
**Severity:** S2
**Area:** Goals / Savings Page / Wallet Funding / UI
**Discovered on:** 2026-05-24
**Reported by:** User

### Problem

The current Reserve Money modal is shaped like a one-wallet funding action:

```text
Goal
Wallet selector
Amount
Reserve
```

That is fine for a simple first interaction, but it is not the full domain model. Real users often save toward one goal across several money locations.

Example:

```text
Laptop Goal target: 10M

Reserved from:
- Savings Account: 6M
- Cash at home: 2M
- Debit card reserve: 2M
```

If the product only allows one wallet per goal, the app forces fake behavior:

```text
User already has the full 10M spread across wallets,
but Sarflog cannot represent that truth cleanly.
```

### Correct Domain Model

Goals and wallets are many-to-many:

```text
One wallet can fund many goals.
One goal can be funded by many wallets.
```

Examples:

```text
Savings Account: 20M
  -> Emergency Goal: 10M
  -> Laptop Goal: 5M
  -> Travel Goal: 5M
```

```text
Wedding Goal: 50M
  <- Savings Account: 30M
  <- Cash Wallet: 10M
  <- Debit Reserve: 10M
```

Architecture sentence:

```text
Goals and wallets have a many-to-many relationship through goal funding records.
Goal funding does not move money.
It protects portions of wallet balances for specific goals and reduces each wallet's free-to-spend amount.
```

### Data Shape

The conceptual join table / ledger shape is:

```text
goal_allocations / goal_contributions
- id
- goal_id
- wallet_id
- amount
- currency
- contribution_type: ALLOCATE / RETURN / CONSUME
- linked_event_id
- created_at
```

Per goal:

```text
funded_amount = sum(active allocations to this goal)
remaining_to_fund = target_amount - funded_amount
```

Per wallet:

```text
protected_for_goals = sum(active allocations from this wallet)
free_to_spend = wallet_balance - protected_for_goals
```

### Core Invariants

For each wallet:

```text
sum(active goal allocations from wallet) <= wallet.owned_positive_balance
```

For each active goal:

```text
sum(active goal allocations to goal) <= goal.target_amount
```

Goal allocations must not be backed by:

```text
credit capacity
overdraft capacity
archived wallets
wrong-currency wallets
ineligible wallets
```

### UX Direction

Keep the default Reserve Money interaction simple, but add multi-wallet support deliberately.

Recommended modal shape:

```text
Reserve Money

Goal: Laptop
Target: 10M
Remaining: 10M

Sources:
1. Savings Account
   Balance: 8M
   Already reserved: 2M
   Free to reserve: 6M
   Reserve amount: 6M

2. Cash Wallet
   Balance: 3M
   Already reserved: 0
   Free to reserve: 3M
   Reserve amount: 2M

[+ Add another wallet]

Total selected: 8M
Remaining after reserve: 2M
```

The basic flow can still start with one wallet row. The important UI addition is:

```text
+ Add another wallet
```

Do not force users through multi-wallet complexity if they only need one wallet.

### Purchase-Day Impact

Multi-wallet goal funding naturally connects to `payment_allocations[]`.

Example:

```text
Camera Goal target: 10M

Funded by:
- Savings: 6M
- Cash: 2M
- Debit reserve: 2M

Paid by:
- Debit: 10M
```

If user chooses to use reserved goal funds, the settlement layer must compare:

```text
funding wallets
payment wallets
```

Then it can create required settlements:

```text
Savings -> Debit: 6M
Cash -> Debit: 2M
Debit allocation consumed directly: 2M
```

This is why goal purchase completion must use:

```text
payment_allocations[]
```

not a single `payment_wallet_id`.

### What To Implement

- [x] Keep backend goal funding as many-to-many through wallet-backed goal contribution/allocation records.
- [x] Change the existing plural allocate endpoint to accept multiple wallet allocation rows in one request:
  `POST /goals/{goal_id}/allocations` with `{ allocations: [{ wallet_id, amount }] }`.
- [x] Keep single-wallet reserve as a valid simple case of the multi-wallet model.
- [x] Update the Reserve Money modal to support `+ Add wallet`.
- [x] Show each wallet row with balance, already reserved, and free-to-reserve.
- [x] Validate total selected amount does not exceed goal remaining amount.
- [x] Validate each wallet row does not exceed that wallet's free-to-reserve amount.
- [x] Prevent duplicate wallet rows in the same reserve action.
- [x] Show goal funding sources grouped by wallet on each goal card/detail view.
- [x] Add tests for reserving one goal from multiple wallets.
- [x] Add tests for one wallet funding multiple goals.
- [x] Add tests that protected/free-to-spend math stays correct across both directions.

### Final Rule

```text
One goal can be funded by multiple eligible wallets.
One wallet can fund multiple goals.
Each allocation protects only its source wallet's real owned money.
Multi-wallet funding is not a special case; it is the correct domain model.
```

---

## EC-018: Planned Purchase Settlement UX Is Too Confusing And Too Permissive

**Status:** DESIGN_CONFIRMED
**Severity:** S2
**Area:** Goals / Planned Purchase / Settlement UX / Expense Form
**Discovered on:** 2026-05-24
**Reported by:** User

### Problem

The planned purchase dialog currently exposes settlement language that is too abstract:

```text
Pay from goal funding wallet
Use goal funds to cover payment
Pay outside goal funds
```

This is hard for a normal user to understand.

The `Pay outside goal funds` option is especially weak for the product model. If the user does not want the purchase to consume goal money, then it should not be recorded through the goal purchase flow at all.

Correct user expectation:

```text
If I click Record purchase on a goal,
I am using the goal's reserved money for that purchase.
```

If the purchase has no real goal relationship:

```text
User should go to Expenses and create a normal expense.
```

### Why `Pay Outside Goal Funds` Should Be Removed

`Pay outside goal funds` means:

```text
Create an expense related to this goal,
but do not consume the goal's reserved money.
```

That creates unnecessary ambiguity:

```text
Goal says money was reserved for Laptop.
User records Laptop purchase from the goal.
But goal money is not used.
```

This weakens the mental model.

Better rule:

```text
Goal purchase flow always uses reserved goal funds.
Normal expense flow is for expenses that should not use goal funds.
```

### Correct Settlement Choices

The flow should only keep the two settlement meanings that match real goal usage:

```text
1. I paid directly from the reserved goal wallet.
2. I paid with another wallet/card, but the reserved goal money should cover it.
```

Backend mapping:

```text
I paid directly from the reserved goal wallet
-> settlement_mode = DIRECT

I paid with another wallet/card, but goal money should cover it
-> settlement_mode = REIMBURSE_PAYMENT_WALLET
```

Remove/deprecate from planned purchase UI:

```text
PAID_OUTSIDE_GOAL_FUNDS
```

If backend keeps it temporarily for compatibility, frontend should stop offering it.

### Human-Focused UI Question

Replace the raw `Settlement` dropdown with a question.

Recommended wording:

```text
How should the reserved goal money be used for this purchase?
```

If payment wallet is one of the goal funding wallets:

```text
You paid from money already reserved for this goal.

[Use this reserved wallet money]
No extra transfer is needed.
```

If payment wallet differs from funding wallet:

```text
You paid with Debit Card, but this goal is reserved in Savings.

Should Sarflog use the reserved Savings money to cover this purchase?
```

Options:

```text
Use reserved goal money
Record the purchase from Debit Card and settle it from the goal funding wallet.

Change payment wallet
Record the purchase directly from one of the reserved goal wallets.
```

Optional helper action:

```text
This is not a goal purchase
Cancel and create a normal expense instead.
```

This should be a navigation/cancel helper, not a settlement mode.

### Real-World Example

Goal:

```text
Laptop Goal target: 10M
Reserved from Savings: 10M
```

Case A:

```text
User pays from Savings.
```

Meaning:

```text
The reserved wallet paid directly.
No reimbursement/settlement transfer is needed.
Goal funding is consumed.
```

Case B:

```text
User pays with Debit Card at the store.
```

Meaning:

```text
Debit Card was the payment instrument.
Savings was the goal funding source.
Sarflog should use the reserved Savings money to cover the Debit payment.
```

This requires settlement/reimbursement behavior, not `pay outside goal funds`.

### Subcategory Gap

Goal-created expense currently behaves like a simpler category-level expense. The planned purchase form should support subcategories too.

Reason:

```text
If Quick Add expense can be categorized as Electronics -> Laptop,
then goal purchase should be able to create the same kind of expense.
```

Otherwise analytics and category breakdowns become less accurate for goal-created expenses.

Required fields:

```text
category
subcategory_id
```

Expected validation:

```text
subcategory belongs to user
subcategory belongs to selected category
subcategory limit validation runs if applicable
```

Longer-term, this should be handled by the shared expense posting service from EC-016.

### What To Implement

- [x] Remove `Pay outside goal funds` from the planned purchase frontend UI.
- [x] Consider rejecting `PAID_OUTSIDE_GOAL_FUNDS` for planned purchase on the backend after compatibility cleanup.
- [x] Replace the settlement dropdown with a human-focused question and explanatory choices.
- [x] Show context-aware text comparing payment wallets vs goal funding wallets.
- [ ] Add a cancel/helper action for users who actually want a normal expense instead.
- [x] Add `subcategory_id` to the goal purchase form payload.
- [x] Add subcategory selector to the Record Purchase modal.
- [x] Validate subcategory on the backend for goal-created expenses.
- [x] Ensure goal-created expense writes `EntityLedger.subcategory_id`.
- [x] Add tests for planned purchase with subcategory.
- [x] Add tests proving planned purchase consumes goal funds and does not support a silent outside-goal purchase path.

### Final Rule

```text
Record Purchase on a goal means: use this goal's reserved money.
If user does not want to use goal money, they should create a normal expense.
Settlement UI should explain real-life payment behavior, not expose accounting jargon.
```

---

## EC-019: Goal Templates Are Design Debt

**Status:** DESIGN_CONFIRMED
**Severity:** S3
**Area:** Goals / Intent Taxonomy / UI Simplicity
**Discovered on:** 2026-05-24
**Reported by:** User

### Problem

Goal templates are currently not pulling real weight in the domain model.

The important field is:

```text
goal.intent
```

because intent changes behavior:

```text
RESERVE
PLANNED_PURCHASE
PAY_OBLIGATION
FUND_PROJECT
```

But template values like:

```text
Laptop / Phone
Emergency Fund
Travel
General Savings
```

mostly change wording, labels, or icon psychology. They do not change ledger behavior, wallet protection rules, settlement rules, or completion flow.

### Why This Is Bad

Templates create extra UI and schema complexity without giving the system more financial truth.

They can make users ask:

```text
What is the difference between a template and an intent?
Why do I need to pick this?
What happens if I choose the wrong one?
```

This is especially bad because the goal model is already conceptually heavy:

```text
wallet-backed funding
protected free-to-spend
goal settlement
planned purchase completion
multi-wallet funding
```

The UI should not add optional classification unless it changes behavior.

### Correct Rule

Use intent for workflow.

Use plain user-entered fields for identity:

```text
title
description
optional cover image
optional tags later
```

Do not keep templates as a core domain concept unless they become true presets that create behavior, validation, or default settings.

### Better Replacement

Instead of:

```text
Intent: PLANNED_PURCHASE
Template: Laptop / Phone
Title: Laptop 4
```

Use:

```text
Intent: PLANNED_PURCHASE
Title: Laptop 4
Optional cover image: laptop photo
Optional description: MacBook for work
```

Instead of:

```text
Intent: RESERVE
Template: Emergency Fund
Title: Emergency Fund
```

Use:

```text
Intent: RESERVE
Title: Emergency Fund
Optional cover image: symbolic image
```

### What To Implement

- [x] Remove template selection from goal creation UI.
- [x] Remove template badges from goal cards/detail views.
- [x] Keep intent visible only where it helps explain behavior.
- [x] Stop requiring or encouraging template values in frontend schemas.
- [ ] Consider deprecating `goals.template` in backend after existing data is handled.
- [x] If keeping the DB column temporarily, treat it as ignored legacy metadata.
- [x] Do not add new behavior based on templates.

### Final Rule

```text
Intent is behavior.
Template is decoration.
If decoration does not meaningfully help users, remove it.
```

---

## EC-020: Planned Purchase Completion Uses Explicit Target Adjustment

**Status:** FIXED
**Severity:** S2
**Area:** Goals / Planned Purchase / Purchase Completion / UX Rules
**Discovered on:** 2026-05-24
**Reported by:** User

### Context

We have been deciding how strict `PLANNED_PURCHASE` goals should be when the user records the final purchase.

The core question:

```text
Can a planned purchase goal be completed before it reaches 100% of its original target?
```

This is not fully decided yet.

### Model A: Original Target Must Be Fully Funded

Rule:

```text
Record purchase only when:
reserved/unreleased goal funding >= goal.target_amount
```

Example:

```text
Laptop target: 10M
Reserved: 8M
Actual store price: 7.13M
```

Under this model:

```text
Block purchase until user updates target manually to 7.13M.
Then purchase can be recorded.
```

Pros:

```text
Very strict and clear.
Target means the planned purchase amount.
Goal cannot be completed at 70% or 80% by accident.
Keeps the progress bar meaning simple.
```

Cons:

```text
Extra friction when real price changes.
User must edit target before recording purchase.
Can feel annoying at checkout time.
```

### Model B: Actual Purchase Amount Becomes Final Target At Completion

Rule:

```text
Record purchase only when:
actual_purchase_amount <= reserved/unreleased goal funding
```

If the actual price is lower than original target, Sarflog adjusts completion around the actual price.

Example:

```text
Laptop target: 10M
Reserved: 8M
Actual store price: 7.13M
```

Under this model:

```text
Allow purchase.
Record expense: 7.13M
Consume goal funding: 7.13M
Return/unreserve extra: 870k
Complete goal at actual purchase price.
```

Pros:

```text
Matches real checkout behavior.
Allows price drops without manual target editing.
Still prevents underfunded purchase because actual price must be covered.
```

Cons:

```text
Target becomes less rigid.
Progress can jump from 80% to completed because final price changed.
Needs very clear UI explanation.
```

### Model C: Quick Target Adjustment Inside Record Purchase

Rule:

```text
If actual price differs from target, ask user to update target inside the Record Purchase flow.
```

Example:

```text
Laptop target: 10M
Reserved: 8M
Actual price entered: 7.13M
```

UI says:

```text
This purchase is below your goal target.
Update target from 10M to 7.13M and record purchase?
```

If user confirms:

```text
goal.target_amount = 7.13M
expense = 7.13M
consume = 7.13M
return extra reserved funding = 870k
goal completed
```

Pros:

```text
Keeps target semantically correct.
Avoids separate manual edit flow.
Makes price-change decision explicit.
```

Cons:

```text
More UI states.
More backend transaction logic.
Still needs careful wording.
```

### Shared Invariant Across All Reasonable Models

We do not want this:

```text
Goal target: 10M
Reserved: 7M
Actual purchase: 10M
System allows goal completion anyway.
```

That would reintroduce the rejected `pay outside goal funds` ambiguity.

Minimum invariant:

```text
actual_purchase_amount <= reserved/unreleased goal funding
```

If not:

```text
Reject.
Ask user to reserve more money first or create a normal expense outside the goal flow.
```

### Final Decision

Use Model C:

```text
Quick target adjustment inside Record Purchase.
```

Reason:

```text
Planned Purchase remains one final purchase event.
If the real checkout price differs from the original target, the user must explicitly update the target inside Record Purchase.
Any leftover reserved money is unreserved/released.
The goal is completed and cannot be used for a second purchase.
```

### Intent Coverage Status

So far, detailed modeling has focused on:

```text
RESERVE
PLANNED_PURCHASE
```

Still not deeply modeled:

```text
PAY_OBLIGATION
FUND_PROJECT
```

These two intents need their own senior-level pass before implementation rules are finalized.

### What To Implement

- [x] Choose Model C for planned purchase completion.
- [x] Allow `goal.target_amount` to be changed during purchase completion only with explicit confirmation.
- [x] Reject purchase completion when actual amount differs from target and confirmation is missing.
- [x] Release unused reserved money automatically after planned purchase completion.
- [x] Keep one planned purchase goal limited to one purchase event.
- [ ] Model `PAY_OBLIGATION` edge cases.
- [ ] Model `FUND_PROJECT` edge cases.

### Final Rule

```text
Planned Purchase = one final purchase event.
If actual price differs from target, user must update the target inside Record Purchase.
Actual purchase amount must be covered by unreleased goal funding.
Leftover reserved money is returned.
Continue treating RESERVE and PLANNED_PURCHASE as the only deeply reviewed intents so far.
```

---

## EC-021: Debt Lending From Credit Or Overdraft Must Be Explicit Borrowed-Money Lending

**Status:** DESIGN_CONFIRMED
**Severity:** S2
**Area:** Debts / Wallets / Credit / Overdraft / Multi-Wallet Debt Allocations
**Discovered on:** 2026-05-25
**Reported by:** User

### Context

Debts currently support:

```text
DebtType.OWING = I owe someone
DebtType.OWED = someone owes me
is_money_transferred = whether wallet money actually moved at creation
```

For `is_money_transferred=true`, current debt creation uses one wallet:

```text
initial_wallet_id
```

Current debt payment also uses one wallet:

```text
DebtTransaction.wallet_id
```

This needs to catch up to the newer architecture:

```text
initial_wallet_allocations[]
payment_allocations[]
```

### Core Problem

Normal lending should use owned money.

But credit cards and debit overdraft capacity are borrowed money.

If the app lets users lend from them as if they are normal owned-money wallets, Sarflog lies about the financial nature of the transaction.

Example:

```text
Credit card cash advance: 5M
User lends that 5M to friend
```

This is not normal lending from owned cash.

It creates two linked truths:

```text
Credit liability: -5M
Receivable from friend: +5M
```

Net worth is not improved.

### Rejected Solution: Global Settings Toggle

Do not add a broad setting like:

```text
Allow lending from credit cards: on/off
Allow lending from overdraft: on/off
```

Reason:

```text
Settings are mutable.
History is immutable.
```

If user turns the setting off later, old debt records should not become invalid or change meaning.

This creates bad questions:

```text
Do old borrowed-money lending records become illegal?
Do reports change retroactively?
Does the UI hide actions for existing debts?
What happens if user turns it back on?
```

Avoid this.

### Rejected Solution: Permanent Wallet-Creation Rule

Do not ask at wallet creation:

```text
Can this credit/overdraft wallet be used for lending forever?
```

Reason:

```text
Wallet nature is stable.
User behavior is situational.
```

A credit card is always borrowed-money capacity. A debit overdraft is always borrowed-money capacity when balance goes below zero.

The user may normally avoid lending from borrowed money, but one day they may actually do it in real life. Sarflog must be able to record reality without changing the permanent wallet definition.

### Correct Rule

Wallet type defines the nature of money.

Transaction flow decides whether borrowed money is being used.

Normal debt/lending flow:

```text
Can lend only from owned free money.
```

Eligible normal lending sources:

```text
Cash
Savings
Debit positive free-to-spend balance
Prepaid positive free-to-spend balance
```

Not eligible for normal lending:

```text
Credit card borrowed capacity
Debit overdraft borrowed portion
Protected goal money
```

### Explicit Advanced Flow

If user chooses a credit card or tries to use overdraft capacity, do not silently allow it.

Show an explicit borrowed-money lending flow:

```text
You are lending borrowed money.

This means:
- your card/overdraft debt increases
- someone now owes you money
- this is not normal lending from owned cash

Continue?
```

If confirmed, classify the transaction as:

```text
borrowed_money_lending
```

This is not a global setting. It is a transaction-level decision.

### Real-World Example: Credit Card Lending

User uses a credit card cash advance to lend a friend 5M.

Sarflog records:

```text
Credit wallet: -5M
Debt owed to me: +5M
```

Meaning:

```text
I borrowed 5M from the card/bank.
My friend owes me 5M.
```

If fees or interest exist:

```text
Debt charge / bank fee / interest expense should be recorded separately.
```

### Real-World Example: Debit Overdraft Lending

Wallet:

```text
Debit balance: 3M
Overdraft limit: 10M
Protected for goals: 0
```

User lends:

```text
8M to friend
```

This is mixed:

```text
3M owned money
5M overdraft borrowed money
```

Normal lending should block and explain:

```text
Only 3M is owned money.
The remaining 5M uses overdraft.
Use borrowed-money lending flow?
```

If confirmed:

```text
Debit wallet becomes -5M
Debt owed to me increases by 8M
Transaction marked as partially borrowed-money lending
```

### Real-World Example: Overlimit Credit

If credit card is already over limit:

```text
Credit balance: -12M
Credit limit: 10M
allow_overlimit: true
```

Normal lending should still be blocked.

If user really did it in real life and Sarflog must record reality, allow only through explicit advanced/reconciliation flow.

The app should show:

```text
This uses overlimit borrowed money.
Your card is already beyond its normal limit.
```

### Receiving Money Into Credit Or Overdraft Is Different

Receiving money into a credit/overdraft wallet can be valid because it reduces debt.

Example:

```text
Credit card balance: -8M
Friend repays 3M directly to card
Credit card balance: -5M
```

This is allowed as repayment destination.

Rule:

```text
Borrowed wallets cannot normally be lending sources.
Borrowed wallets can be repayment destinations if money is coming in.
```

### Multi-Wallet Debt Allocation Direction

Debt creation with real money transfer should eventually support:

```text
initial_wallet_allocations[]
```

This applies to both real-transfer debt creation directions:

```text
I OWE + money_transferred=true
They OWE ME + money_transferred=true
```

Current single-wallet field:

```text
initial_wallet_id
```

is not enough long-term.

Replace the creation model with:

```text
initial_wallet_allocations[]
- wallet_id
- amount
- source_kind: OWNED_MONEY / BORROWED_MONEY if needed
```

For `I OWE + money_transferred=true`, the allocations are destination wallets where borrowed money entered.

Example:

```text
I borrowed 10M.
Received:
- Debit: 6M
- Cash: 4M

Debt:
I owe lender 10M.
```

Wallet effects:

```text
Debit +6M
Cash +4M
Debt remaining +10M
```

For `They OWE ME + money_transferred=true`, the allocations are source wallets where lent money left.

Example:

```text
Friend borrowed 10M from me.
I gave:
- Cash: 3M
- Savings: 7M

Debt:
Friend owes me 10M.
```

Wallet effects:

```text
Cash -3M
Savings -7M
Receivable remaining +10M
```

The total allocation must equal the debt initial amount:

```text
sum(initial_wallet_allocations.amount) == debt.initial_amount
```

Example:

```text
They owe me 10M.
I lent:
- Cash: 4M owned money
- Debit: 3M owned money
- Debit overdraft: 3M borrowed money
```

The allocation rows should classify the source:

```text
OWNED_MONEY
BORROWED_MONEY
```

or derive it from wallet state:

```text
owned_part = available positive free-to-spend
borrowed_part = amount - owned_part
```

### Final Rule

```text
Owned positive free money can be lent normally.
Borrowed capacity cannot be lent through the normal debt flow.
Credit/overdraft lending is allowed only as explicit transaction-level borrowed-money lending.
Do not model this as a global setting.
Do not model this as a permanent wallet-creation rule.
```

---

## EC-022: Debt Payments And Receipts Must Support Multiple Wallets

**Status:** DESIGN_CONFIRMED
**Severity:** S2
**Area:** Debts / Debt Transactions / WalletLedger / Multi-Wallet Payments
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

Debt payment currently uses a single wallet:

```text
DebtTransaction.wallet_id
```

This is too narrow. Real debt payments and receipts can be split across multiple wallets.

The debt transaction model should eventually use:

```text
payment_allocations[]
- wallet_id
- amount
```

The total must match the debt payment amount:

```text
sum(payment_allocations.amount) == debt_transaction.amount
```

### Applies To All Four Debt Cases

Debt direction and money-transfer mode change the meaning, but multi-wallet payments still make sense in all four cases.

### Case 1: I Owe + Money Transferred

Example:

```text
I borrowed 10M from Ali.
Repayment today:
- Debit: 6M
- Cash: 4M
```

Meaning:

```text
Money leaves my wallets.
My payable debt decreases by 10M.
```

Rules:

```text
payment_allocations[] are source wallets.
Each source must have enough free owned money unless explicit borrowed-money repayment is used.
Goal-protected money cannot be touched silently.
Principal repayment is not an expense.
Charges/interest portion is an expense.
```

### Case 2: I Owe + No Money Transferred

Example:

```text
Ali paid my restaurant bill for 300k.
No money entered my wallet.
I owe Ali 300k.

Later I repay:
- Cash: 100k
- Debit: 200k
```

Meaning:

```text
Money leaves my wallets.
The deferred expense/payable decreases.
```

Rules:

```text
payment_allocations[] are source wallets.
The payment may map to the stored expense_category.
Goal-protected money cannot be touched silently.
Credit/overdraft repayment must be explicit borrowed-money use.
```

### Case 3: They Owe Me + Money Transferred

Example:

```text
I lent Ali 10M.
He repays:
- Cash: 3M
- Debit transfer: 7M
```

Meaning:

```text
Money enters my wallets.
My receivable debt decreases by 10M.
```

Rules:

```text
payment_allocations[] are destination wallets.
Principal repayment is not income.
Charges/interest/profit portion may be income.
Receiving into credit/overdraft wallet can be valid if it reduces debt.
```

Example receiving into credit:

```text
Credit wallet balance: -8M
Friend repays 3M directly to credit card
Credit wallet balance: -5M
```

### Case 4: They Owe Me + No Money Transferred

Example:

```text
Client owes me 5M for work.
No wallet money left me at creation.

Client pays:
- Cash: 2M
- Debit transfer: 3M
```

Meaning:

```text
Money enters my wallets.
Receivable decreases.
If business income, it may also count under income_source_id.
If personal payback, it should not inflate income reports.
```

Rules:

```text
payment_allocations[] are destination wallets.
Income classification depends on the debt's income_source_id / personal-payback choice.
```

### Correct Architecture

Debt transactions should follow the same allocation-array direction as expenses and goal purchases:

```text
DebtTransaction
  amount
  date
  note

DebtTransactionWalletAllocation
  debt_transaction_id
  wallet_id
  amount
```

Or equivalent ledger-first implementation:

```text
FinancialEvent
WalletLedger rows, one per wallet
EntityLedger rows for debt principal / charges / income / expense meaning
```

### What To Implement

- [ ] Add `payment_allocations[]` to debt payment request schema.
- [ ] Keep single-wallet payment as UI shorthand only if desired, but backend should support allocation arrays.
- [ ] Validate `sum(payment_allocations.amount) == payment.amount`.
- [ ] For `OWING`, treat allocations as wallet outflows.
- [ ] For `OWED`, treat allocations as wallet inflows.
- [ ] Split principal vs charges correctly.
- [ ] Ensure goal-protected outflow checks run per source wallet.
- [ ] Add tests for all four debt cases with multi-wallet payment/receipt.

### Final Rule

```text
Every debt payment/receipt can be represented as one debt transaction with multiple wallet legs.
Direction decides whether those wallet legs are outflows or inflows.
```

---

## EC-023: Goal-Protected Wallet Money Affects Debt Actions

**Status:** DESIGN_CONFIRMED
**Severity:** S1
**Area:** Debts / Goals / Wallet Availability / Protected Outflows
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

Wallet-funded goal money changes how much of a wallet is free for debt actions.

Goal allocations do not reduce wallet balance, but they do reduce free-to-use owned money:

```text
wallet balance = real money
goal allocation = protected claim on wallet money
free-to-use = wallet balance - protected goal allocations
```

Debt actions that take money out of a wallet must respect this.

### Real-World Example

Wallet:

```text
Debit balance: 10M
PS5 Goal protected from Debit: 8M
Free-to-use: 2M
```

User tries to repay a debt:

```text
Pay Ali 5M from Debit
```

Normal flow must block:

```text
Only 2M is free.
3M would touch money reserved for PS5.
Release or move goal funding first.
```

### Affected Debt Actions

These actions reduce wallet balance and must run wallet availability checks:

```text
I OWE repayment
They OWE ME initial lending
Debt edit that increases money sent out
Debt transaction deletion/reversal that removes an inflow from a wallet
Debt delete/void that reverses linked wallet events
Charge payment when charges are settled through wallet outflow
```

### Not Usually Blocked

Inflows usually do not violate goal protection:

```text
I borrow money and receive it into a wallet.
Someone repays me into a wallet.
Client pays receivable into a wallet.
```

But an inflow can later become protected if the user allocates it to a goal. After that, reversing the inflow becomes an outflow and must respect goal protection.

### Correct Rule

Debt outflows must call the same wallet protection gate as expenses/transfers:

```text
requested_outflow <= wallet.free_to_use
```

If false:

```text
Reject normal action.
Require release/rebalance of goal funding or explicit borrowed-money/reconciliation flow.
```

### Final Rule

```text
Goals do not change debt balances.
Goals do constrain debt wallet outflows because they protect wallet money.
Debt code must treat wallet free-to-use as balance minus protected goal allocations.
```

---

## EC-024: Debt Reversal Must Be Dependency-Aware When Goal Funding Was Changed

**Status:** DESIGN_CONFIRMED
**Severity:** S1
**Area:** Debts / Goal Allocations / Reversal / Void / Immutable Ledger
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

Debt actions can interact with goal allocations over time. Later reversal/deletion can produce confusing states if the app tries to hard-delete or blindly reverse only part of the chain.

Example sequence:

```text
Debit: 10M
PS5 Goal protected: 8M
Free: 2M
```

User lends friend 5M.

To do that, user releases 3M from PS5:

```text
PS5 protected: 8M -> 5M
Debit outflow: -5M
Friend owes user: 5M
```

Later friend repays 3M to the same Debit wallet:

```text
Debit inflow: +3M
Friend still owes: 2M
```

User then reserves that 3M back to PS5:

```text
PS5 protected: 5M -> 8M
```

Now user tries to reverse the 3M repayment.

If reversed blindly:

```text
Debit decreases by 3M
PS5 still protected by 8M
```

This can break the wallet protection invariant:

```text
wallet protected amount <= owned positive balance
```

### Correct Behavior: Single Event Reversal

If user reverses only the 3M repayment, the app must check current wallet protection first.

If the repayment money is now protected for PS5, block and explain:

```text
This repayment money is now reserved for PS5.
To reverse the repayment, unreserve or move 3M of PS5 funding first.
```

Valid options:

```text
Unreserve 3M from PS5 and reverse repayment
Move 3M PS5 funding to another eligible wallet
Cancel
```

### Correct Behavior: Full Chain Rollback

Sometimes user wants to undo the whole fake/test scenario:

```text
Undo the debt as if this never happened.
```

Do not silently hard-delete everything.

Provide a dependency-aware preview:

```text
This will:
- reverse 3M repayment
- remove/void 5M lending event
- restore 3M PS5 funding that was released for lending
- remove/void the debt record
```

Then confirm:

```text
Reverse this financial chain?
```

### Link Goal Resolution To Debt Events

When lending touches protected goal money, the goal release/rebalance should be linked to the debt/lending event.

Example:

```text
GoalContribution.RETURN 3M
linked_event_id = debt lending FinancialEvent
reason/context = debt_lending_resolution
```

This allows the app to later understand:

```text
This PS5 unreserve happened because user lent money to friend.
```

Without this link, full rollback cannot safely restore goal funding.

### Immutable Ledger Rule

Prefer:

```text
void/reverse financial events
```

over:

```text
hard-delete financial history
```

Debt delete should become:

```text
void debt chain
```

or:

```text
archive debt
```

not "erase and hope all side effects disappear."

### Final Rule

```text
Single event reversal reverses only that event and must respect current goal protection.
Full rollback reverses the linked chain and must show a preview.
Any goal release/rebalance done to enable debt lending should be linked to the debt event that required it.
```

---

## EC-025: Bank Fees And Debt Charges Must Be Linked Without Being Merged

**Status:** DESIGN_CONFIRMED
**Severity:** S1
**Area:** Wallets / Debts / Charges / Bank Fees / Ledger
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

Wallet bank fee actions and debt charges look similar in the UI because both are "fees/charges", but they are not the same financial event.

Current difference:

```text
Wallet bank fee
-> money leaves wallet now
-> expense event exists now
-> wallet balance decreases now

Debt charge
-> obligation increases now
-> no wallet money moves yet
-> expense/income happens only when charge is paid/received
```

If Sarflog merges these concepts blindly, the app can double-count fees or record fake wallet movement.

### Real-World Examples

Immediate bank fee:

```text
Bank deducts 25k account maintenance fee from debit card.

Sarflog:
Debit wallet -25k
Expense category: Bank fees / interest
No debt charge needed
```

Debt/card charge added:

```text
Credit card adds 100k late fee to outstanding balance.

Sarflog:
Credit/debt obligation +100k
No wallet outflow yet
DebtCharge / DebtEvent: CHARGE_ADDED
```

Later payment:

```text
User pays 100k late fee from Debit wallet.

Sarflog:
Debit wallet -100k
Debt charge settled
Expense category: Debt charges / bank fee
```

### Decision

Do not create one generic "fee" model that hides the difference between paid-now fees and obligation-added charges.

Use three explicit flows:

```text
1. Fee deducted from wallet now
   -> Wallet outflow + expense

2. Fee/interest/penalty added to debt
   -> Debt charge only, no wallet movement

3. Existing debt charge paid from wallet
   -> Wallet outflow + debt charge settlement
```

### Product UX

Future bank fee/charge dialog should ask:

```text
What happened?

- Bank deducted this from my wallet
- Bank/lender added this to a debt or card balance
- I paid an existing debt charge
```

### Implementation Notes

Potential links:

```text
DebtCharge or DebtEvent may link to FinancialEvent when paid.
FinancialEvent / EntityLedger already can carry debt_id.
Wallet bank fee action may optionally accept debt_id only when it is paying/settling a debt-related charge.
```

### Final Rule

```text
Bank fee paid now is a wallet expense.
Debt charge added now is an obligation increase.
Debt charge payment later is a wallet outflow linked back to the debt.
Never count the same charge as both paid and unpaid.
```

---

## EC-026: Debts Can Be Settled With Assets, Not Only Wallet Money

**Status:** DESIGN_CONFIRMED
**Severity:** S1
**Area:** Debts / Assets / Non-Cash Settlement / Ledger
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

Current debt payments are wallet-centric. Real life allows debts to be settled with non-cash assets.

If Sarflog supports only wallet payments, users cannot accurately model cases where a debt is repaid by giving or receiving something valuable.

### Real-World Examples

They owe me, money was transferred:

```text
I lent friend 5M.
Friend cannot pay cash.
Friend gives me a phone worth 5M.

Sarflog:
Receivable debt -5M
Asset created: Phone, agreed value 5M
No wallet inflow
```

I owe, money was transferred:

```text
I borrowed 5M.
I repay by giving lender gold worth 5M.

Sarflog:
Debt payable -5M
Existing gold asset is transferred/closed
No wallet outflow
```

They owe me, no money transferred:

```text
Client owes me 10M for work.
Client gives me equipment valued at 10M.

Sarflog:
Receivable -10M
Asset created: Equipment, agreed value 10M
Potential income context depends on product scope
```

I owe, no money transferred:

```text
Friend paid my repair bill.
I settle by giving him my old laptop.

Sarflog:
Payable debt - agreed value
Laptop asset closed/transferred
No wallet outflow
```

### Decision

Debt settlement should eventually support settlement method:

```text
WALLET
ASSET
MIXED
```

### Critical Rule

Asset settlement amount must be explicit:

```text
settlement_amount = agreed value used to reduce debt
```

Do not silently assume:

```text
asset.current_value == debt settlement amount
```

because a user may settle a 5M debt with an asset whose estimated market value is 6M, or the parties may agree on a different value.

### Implementation Notes

Receiving an asset as repayment:

```text
Debt decreases
Asset increases
No WalletLedger
DebtEvent links to asset_id
```

Giving an asset to repay:

```text
Debt decreases
Asset status changes to transferred/used_for_debt_settlement
No WalletLedger unless there is also cash involved
DebtEvent links to asset_id
```

Mixed settlement:

```text
Debt decreases by total settlement
WalletLedger handles cash part
Asset link handles non-cash part
```

### Final Rule

```text
Debt payment does not always mean wallet payment.
Debt settlement can be cash, asset, or mixed.
Wallet balance changes only when wallet money actually moved.
```

---

## EC-027: Debt Categories, Subcategories, And Projects Must Depend On Debt Type

**Status:** DESIGN_CONFIRMED
**Severity:** S1
**Area:** Debts / Budgets / Subcategories / Projects / EntityLedger
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

Debts currently have broad `expense_category` and `income_source_id`, but the Budget system now supports subcategories and projects. Debt-created expense/income events can lose detail unless debt flows can carry those tags.

However, not every debt action should have category/project fields. Principal repayment is not the same as expense/income.

### Debt-Type Rules

#### I Owe + Money Transferred True

Example:

```text
Bank/friend lends me 5M cash.
I receive money in wallet.
I owe 5M.
```

Principal:

```text
Not income when received.
Not expense when repaid.
No expense subcategory for principal.
```

Charges/interest:

```text
Expense when paid.
Needs category/subcategory such as Debt Charges / Loan Interest.
May optionally link to project if the debt was project-specific.
```

#### I Owe + Money Transferred False

Example:

```text
Mechanic repaired my car for 500k.
I will pay next week.
```

This is a delayed expense.

Needs:

```text
expense_category
subcategory_id
project_id
project_subcategory_id
```

because the debt represents a real spending purpose.

#### They Owe Me + Money Transferred True

Example:

```text
I lend friend 5M from wallet.
Friend owes me 5M.
```

Principal:

```text
Not expense when lent.
Not income when repaid.
No income source needed for principal.
```

Charges/profit:

```text
May be income when received.
Needs income_source_id, e.g. Lending interest / Other income.
```

#### They Owe Me + Money Transferred False

Example:

```text
Client owes me for work already done.
No wallet outflow happened.
```

This is receivable/invoice-like.

Needs:

```text
income_source_id
possibly project/client context if supported
```

Do not force expense category fields here.

### Decision

Debt forms should not show all tags for every debt.

Show fields based on meaning:

```text
Delayed expense payable -> category/subcategory/project fields
Loan principal -> no expense category for principal
Charge/interest payment -> category/subcategory or income source
Receivable/invoice -> income source
```

### Implementation Notes

`EntityLedger` already supports:

```text
category
subcategory_id
project_id
project_subcategory_id
debt_id
income_source_id
```

Debt routes/services should populate those fields when a debt-created financial event actually represents expense or income meaning.

### Final Rule

```text
Debt principal is balance-sheet movement.
Debt charge/interest is expense or income.
Delayed expense debt needs budget taxonomy.
Receivable debt needs income/source taxonomy.
Do not ask users for category/source fields when the debt type does not use them.
```

---

## EC-028: Debt Lifecycle Needs A DebtEvent Ledger

**Status:** DESIGN_CONFIRMED
**Severity:** S0
**Area:** Debts / Ledger / Reversal / Charges / Payments / Assets
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

Debt state is currently spread across:

```text
debts.remaining_amount
debt_transactions
debt_charges
financial_events
entity_ledger
expense/income delete and update behavior
```

This makes reversals and cross-page edits fragile.

Examples of fragile behavior:

```text
Delete debt-linked income entry from Income page
-> debt may stay PAID incorrectly

Edit debt charge expense from Expenses page
-> debt math may not update safely

Add charge after debt is PAID
-> debt may need to reactivate

Settle debt with asset
-> current wallet-only transaction model is not enough
```

### Decision

Add a debt lifecycle ledger:

```text
debt_events
```

This is not a replacement for `FinancialEvent`.

It means:

```text
DebtEvent = what happened to the debt
FinancialEvent = wallet/expense/income/entity movement, if any
```

Some debt events have no wallet event.

### Proposed Shape

```text
debt_events
- id
- owner_id
- debt_id
- event_type
- amount
- principal_amount nullable
- charge_amount nullable
- date
- note
- financial_event_id nullable
- asset_id nullable
- debt_charge_id nullable
- reversed_event_id nullable
- created_at
```

Event types:

```text
CREATE
INITIAL_TRANSFER
CHARGE_ADDED
PAYMENT
ASSET_SETTLEMENT
PARTIAL_FORGIVE
FULL_FORGIVE
REFUND
REVERSAL
ARCHIVE
```

### Examples

Charge added:

```text
DebtEvent: CHARGE_ADDED 100k
FinancialEvent: none
WalletLedger: none
```

Charge paid:

```text
DebtEvent: PAYMENT 100k, charge_amount 100k
FinancialEvent: wallet outflow + expense
```

Asset settlement:

```text
DebtEvent: ASSET_SETTLEMENT 5M
FinancialEvent: none or asset-linked event depending final design
Asset: created/transferred/closed
```

Partial forgiveness:

```text
DebtEvent: PARTIAL_FORGIVE 2M
FinancialEvent: none
Debt remaining decreases
```

### Why Goals Do Not Need A New GoalEvent Table Now

Goals already have a ledger-like table:

```text
goal_contributions
- ALLOCATE
- RETURN
- CONSUME
```

So Goals already have the money-history shape that Debts are missing.

Useful goal improvement:

```text
View Details / View History
```

showing `goal_contributions`.

No separate `goal_events` table is needed for current goal money truth.

### Final Rule

```text
Debt lifecycle should be event-ledger driven.
DebtEvent records debt meaning.
FinancialEvent records actual financial movement when movement exists.
Debt remaining/status should be reconciled from debt events, not patched independently across routes.
```

---

## EC-029: CURRENTPROBLEMS Debt Items Need Consolidation Into Debt Ledger Refactor

**Status:** DESIGN_CONFIRMED
**Severity:** S1
**Area:** Debts / Current Problems / Refactor Planning
**Discovered on:** 2026-05-25
**Reported by:** User

### Problem

`CURRENTPROBLEMS.md` contains multiple debt issues that point to the same root problem: debt state is not governed by one lifecycle ledger.

Relevant open/refinement items:

```text
Cannot add charges to a debt marked PAID.
Debt can stay PAID after related charge/income/expense is deleted elsewhere.
Income source is not updating correctly for debt charge income.
Expense refunds may need to reduce debt impact.
Debt charges need clearer category/source behavior.
No-transfer I-owe debts may overlap with delayed/recurring expense behavior.
Charge income needs a reliable income source.
User needs guidance on when debt category/source fields matter.
Multi-category debt expense is still unresolved.
Payment form should hide category/source fields when not meaningful.
Debt Events architecture is already listed as a possible fix.
Partial debt forgiveness is needed.
Editing debt charge expense/income from Expenses/Income pages can break debt math.
Deleting a debt with linked financial entries needs a void/archive/reversal policy.
Debt details/history view is needed.
```

### Decision

These should not be fixed as scattered one-off patches.

Group them under the debt ledger refactor:

```text
DebtEvent
Debt payment/charge split
Debt-linked financial event protection
Debt reversal/void policy
Debt details/history UI
Debt category/subcategory/project rules
```

### Final Rule

```text
Debt bugs around charges, payments, deletion, income/expense edits, and forgiveness are symptoms of missing debt lifecycle ownership.
Fix the lifecycle model first, then update forms and pages around it.
```

---

## EC-030: Planned Purchase Goal Expenses Need Category Without Normal Monthly Budget Penalty

**Status:** FIXED
**Severity:** S1
**Area:** Goals / Planned Purchase / Budgets / ExpensePostingService / EntityLedger
**Discovered on:** 2026-05-26
**Reported by:** User

### Problem

A planned-purchase goal can be saved over several months, then completed as one real purchase.

Example:

```text
January-March:
User reserves money for Laptop Goal.

April:
User buys laptop for 9M.
Category: Electronics
```

If Sarflog counts the full 9M as normal April `Electronics` budget spending, the April budget looks broken:

```text
Electronics budget: 1M
Laptop goal purchase: 9M
Budget result: 8M over
```

That punishes correct planning. The user did not randomly overspend in April. They saved for a planned purchase across time.

### Correct Mental Model

These are separate dimensions:

```text
Category = what kind of expense happened.
Budget impact = whether it consumes the normal monthly spending limit.
Goal context = whether this was funded by planned goal money.
```

So the same real-world purchase can have two different budget meanings:

```text
Unplanned laptop purchase:
Category: Electronics
Budget impact: NORMAL
Counts against April Electronics budget.

Goal-funded laptop purchase:
Category: Electronics
Budget impact: GOAL_FUNDED_EXCLUDED
Shows as Electronics spending / goal-funded purchase.
Does not consume April's normal Electronics budget limit.
```

### Reserve Money Is Not Automatically The Same Rule

Do not blindly exclude every `goal_consume` expense from budgets.

`RESERVE` and `PLANNED_PURCHASE` currently both create real expenses through goal use flows, but they do not necessarily mean the same budget behavior.

For now:

```text
PLANNED_PURCHASE completion -> excluded from normal monthly budget limit.
RESERVE use -> unchanged until explicitly modeled.
```

Reason:

```text
Planned purchase is a known exceptional purchase saved for ahead of time.
Reserve use can mean emergency/monthly real spending and needs separate product decision.
```

### Expected Budget UI Later

Budget page should eventually be able to show:

```text
April Electronics Budget
Normal spending: 400k / 1M

Goal-funded purchases:
Laptop: 9M
```

Do not hide the laptop from analytics. It is still Electronics spending. Just do not treat it as ordinary monthly budget consumption.

### Implementation Direction

Short-term implementation can use a precise reference/budget-impact marker:

```text
FinancialEvent.reference_type = goal_planned_purchase
```

Budget calculations and budget-limit validation should exclude that marker from normal monthly budget spend.

Longer-term implementation may make this explicit on `EntityLedger`:

```text
EntityLedger.budget_impact = NORMAL | GOAL_FUNDED_EXCLUDED
EntityLedger.goal_id = nullable
```

### What To Implement

- [x] Mark planned-purchase goal expense events distinctly from reserve-use goal expenses.
- [x] Do not enforce normal category monthly budget limit for planned-purchase goal completion.
- [x] Do not enforce normal subcategory monthly limit for planned-purchase goal completion.
- [x] Keep category and optional subcategory on the posted expense for analytics/history.
- [x] Exclude planned-purchase goal expenses from normal budget spent calculations.
- [x] Exclude planned-purchase goal expenses from budget detail normal activity/counts.
- [x] Add tests that a normal unplanned laptop purchase counts against Electronics budget.
- [x] Add tests that a goal-funded laptop purchase is categorized as Electronics but does not consume Electronics budget.
- [x] Add tests that planned purchase can complete even when its category budget limit is lower than the purchase amount.

### Final Rule

```text
Budgets control ordinary monthly spending.
Goals fund exceptional planned purchases.
Categories describe what was bought.
Goal-funded planned purchases are real expenses, but not normal monthly-budget consumption.
```

### Final Resolution

Implemented with `FinancialEvent.reference_type = goal_planned_purchase` for planned-purchase goal completion expenses.

`ExpensePostingService` still writes category, budget, and optional subcategory linkage for the real expense, but skips normal monthly budget and subcategory limit enforcement for this specific planned-purchase marker.

Normal budget spent/detail queries exclude `goal_planned_purchase`, while ordinary unplanned expenses continue to count against monthly limits.

---

## EC-031: Meaning-Heavy Forms Should Become Question-Based Interactive Flows

**Status:** PARTIALLY IMPLEMENTED
**Severity:** S3
**Area:** UX / Forms / Goals / Debts / Wallets
**Discovered on:** 2026-05-26
**Reported by:** User

### Problem

Some Sarflog forms expose raw fields that are technically correct but mentally heavy for users.

Examples:

```text
intent
settlement_mode
wallet type
can_fund_goals
debt type
money_transferred
result_type
```

These are domain decisions, not just data entry. If they are presented only as select boxes and text inputs, users may not understand what real-world situation they are recording.

### Product Principle

Do not turn every form into a wizard.

Use fast forms for simple transaction capture:

```text
Quick add expense
Simple income
Simple transfer
Basic edit forms
```

Use interactive/question-based flows for meaning-heavy decisions:

```text
Goal creation
Reserve money
Record planned purchase
Debt creation
Wallet creation
Project creation
Installment creation
```

Rule:

```text
Simple transaction form = fast inputs.
Meaning-heavy financial decision = guided questions.
```

### Better UX Direction

Instead of showing raw technical choices:

```text
Settlement mode:
DIRECT
REIMBURSE_PAYMENT_WALLET
```

Ask the human question:

```text
How did you pay at checkout?

[The same wallet that reserved this goal money paid]
[Another wallet/card paid, but goal money should cover it]
```

Instead of exposing goal intent as a raw enum:

```text
intent = PLANNED_PURCHASE
```

Ask:

```text
What are you saving for?

[Keep money protected]
[Buy one planned item]
[Pay an obligation]
[Fund a bigger project]
```

### Scope Guard

This should be a targeted UX polish effort, not a full product redesign.

Recommended investment:

```text
2-4 days
```

Priority order:

```text
1. Goal create / reserve / record purchase
2. Debt create
3. Wallet create
```

Avoid spending weeks making every form decorative. The purpose is fewer wrong financial records, not visual novelty.

### What To Implement Later

- [ ] Identify confusing enum/select fields in goal flows.
- [ ] Replace planned-purchase settlement dropdown wording with question-style cards or segmented choices.
- [ ] Replace goal intent select with question-style intent choice cards.
- [ ] Apply the same pattern to debt creation after debt ledger refactor stabilizes.
- [ ] Apply the same pattern to wallet creation only for wallet-type and goal-funding eligibility decisions.
- [ ] Keep quick-add expense and simple income fast and compact.

### Final Rule

```text
If a field changes the meaning of real money, ask the user a real-world question.
If a field is routine data entry, keep it fast.
```

---

## EC-034 - Planned Purchase Dialog Should Be A Guided Story

**Status:** IMPLEMENTED
**Severity:** S2
**Area:** Goals / Savings / UX
**Discovered on:** 2026-05-27
**Reported by:** User

### Problem

The current planned-purchase dialog is technically correct but mentally heavy. It stacks amount, wallets, completion meaning, category, subcategory, asset result, and target adjustment in one modal.

That creates confusion because valid wallet choices depend on an earlier meaning decision:

```text
If reserved goal money paid:
  Show only wallets that funded this goal.

If a different wallet paid at checkout:
  Show normal payment wallets.
```

Asking for payment wallets before asking the meaning question can lead users into wrong choices.

### Product Principle

Use a guided storyline for meaning-heavy goal completion:

```text
1. Did you buy this planned item?
2. How did the purchase relate to the reserved goal money?
3. Which wallet(s) paid at checkout, and how much?
4. How should the purchase be classified?
5. Review and record.
```

### Important UI Rule

Final price should be derived from payment allocations, not typed separately.

```text
Debit paid: 6M
Cash paid: 4M
Final price = 10M
```

This avoids mismatch errors like:

```text
Amount paid: 10M
Payment split total: 9.8M
```

The API can still receive `amount`, but the frontend should compute it from `payment_allocations[]`.

### If User Says "No"

If the user says they have not bought the planned item yet:

```text
Do not create an expense.
Do not consume or return goal allocations.
Keep the goal active.
Close the purchase flow.
```

Friendly message:

```text
Come back after the real purchase happens. For clean wallet history, record large planned purchases with the real purchase date before recording later spending from the same wallet.
```

### Transaction Order Note

The app cannot force users to record real-life events immediately or in perfect order.

But large planned purchases can create balance/protection conflicts if users record later smaller spending first.

Example:

```text
Real life:
1. Laptop 5M from Debit
2. Taxi 50k from Debit

App entered:
1. Taxi 50k
2. Laptop 5M
```

If the wallet was tight, the second entry can fail because the current app balance no longer has enough room. The solution is not a fake pending purchase; the UI should explain that purchase date/order matters and let users record the real purchase date.

### Implementation Plan

- [x] Turn planned-purchase dialog into a step-by-step flow.
- [x] Ask "Did you buy this planned item?" first.
- [x] Ask completion meaning before wallet split.
- [x] Filter wallet choices based on completion meaning:
  - `GOAL_FUNDED`: only goal funding wallets.
  - `ACHIEVED_OUTSIDE_RESERVED_FUNDS`: only non-funding checkout wallets.
- [x] Derive final price from `payment_allocations[]`.
- [x] Keep category/subcategory/result after wallet/payment meaning.
- [x] Add final review step before submit.

### Code Impact

Frontend:

```text
Savings page planned-purchase dialog
  -> step state
  -> completion-mode question
  -> payment wallet filtering
  -> final price derived from payment_allocations[]
  -> review before submit
```

Backend/API:

```text
No new API shape is required for this checkpoint.
The existing goal purchase endpoint already accepts:
- completion_mode
- payment_allocations[]
- category/subcategory
- result_type
- adjust_target_to_purchase_amount
```

Validation:

```text
GOAL_FUNDED:
  payment wallets must be goal funding wallets
  payment amount from each wallet cannot exceed that wallet's unreleased goal funding

ACHIEVED_OUTSIDE_RESERVED_FUNDS:
  payment wallets must not be goal funding wallets
  reserved goal allocations are released by backend behavior
```

### Manual Transfer Rule

If the user wants reserved goal money to pay through a wallet that did not fund the goal, Sarflog must not invent a reimbursement.

Instead:

```text
1. Before checkout, use the separate "Prepare payment" action on the goal.
2. Move reserved goal money to the wallet that will pay.
3. Record a real wallet transfer.
4. Move this specific goal allocation label with that transfer.
5. After checkout, record the planned purchase as goal-funded from the new payment wallet.
```

Example:

```text
Before:
Savings: 10M
Laptop goal reserved from Savings: 10M
Debit: 0

User wants Debit to pay at checkout.

Preparation:
Transfer Savings -> Debit: 10M
Move Laptop goal allocation Savings -> Debit: 10M

After:
Savings: 0
Debit: 10M
Laptop goal reserved from Debit: 10M

Purchase:
Debit pays 10M
Laptop goal allocation consumed
Goal completed
```

Implemented as a goal-specific move endpoint:

```text
POST /goals/{goal_id}/allocations/move
```

This endpoint is intentionally goal-specific so moving money for `Laptop Goal` cannot accidentally move another protected goal from the same source wallet.

Important UX rule:

```text
Do not show this preparation action inside the post-purchase "Record purchase" wizard.

Prepare payment = before the real checkout.
Record purchase = after the real checkout.
```

---

## EC-032: Planned Purchase Goals Can Complete Into Installment Purchase Outcomes

**Status:** PARTIALLY IMPLEMENTED
**Severity:** S2
**Area:** Goals / Planned Purchase / Installments / Budget Impact / Taxonomy
**Discovered on:** 2026-05-26
**Reported by:** User

### Problem

`PLANNED_PURCHASE` currently mostly means:

```text
Save money -> buy item -> consume goal funds -> create expense/asset
```

That works for fully paid purchases, but real life has installment purchase cases:

```text
User saves for a phone/car/laptop.
At purchase time, user may pay only a down payment and create an installment plan.
Or user may keep the full saved amount protected and pay the store through installments over time.
```

These are real behaviors and should not be modeled as a separate goal intent.

### Key Decision

Do not add a new goal intent.

Keep:

```text
Goal intent = PLANNED_PURCHASE
```

Add future planned-purchase completion outcomes:

```text
1. Fully paid purchase
2. Down payment + installment
3. Full installment with reserved goal money
```

The goal does not become the installment. The goal money either pays now or becomes protected reserve for future installment payments.

### Flow Diagram

```text
PLANNED_PURCHASE GOAL
"I am saving for a phone/car/laptop"
        |
        v
Purchase day
        |
        +--> Fully paid purchase
        |       Wallet -10M
        |       Goal funding consumed
        |       Expense/asset created
        |
        +--> Down payment + installment
        |       Wallet -3M
        |       Goal funding consumed by 3M
        |       Installment obligation created for remaining 7M
        |       Optional asset created
        |
        +--> Full installment reserve
                Wallet unchanged at purchase time
                Goal funding becomes installment reserve
                Installment obligation created for 10M
                Monthly payments consume reserve over time
```

### Real-World Examples

#### Existing Installment Payment Goal

This is different and belongs under future `PAY_OBLIGATION` handling:

```text
Phone installment already exists.
Next payment: 400k

Goal: Save 400k for next phone payment
Intent: PAY_OBLIGATION
Linked installment: Phone

Use goal money -> pay existing installment payment
```

#### Down Payment + Installment

```text
Car price: 200M
Required initial payment: 50M
Financed amount: 150M

Goal: Car down payment
Intent: PLANNED_PURCHASE
Target: 50M

Completion:
Wallet -50M
Goal completed
Installment/loan created for 150M
Optional car asset created
```

#### Full Installment Reserve

```text
Phone price: 10M
User saved: 10M
Store offers 0% installment: 10 payments x 1M
```

The user may choose installment even though they have the money because they want to preserve liquidity, use 0% financing, keep money earning interest, or smooth cashflow.

Result:

```text
Savings Wallet: 10M
Phone Goal funding: 10M

After purchase:
Savings Wallet still 10M
Phone Goal completed/converted
Installment reserve: 10M
Installment remaining: 10M

Each month:
Wallet -1M
Installment remaining -1M
Installment reserve -1M
```

### Budget Impact Rule

A goal-funded large purchase should not destroy the normal monthly category budget.

Example:

```text
April Electronics budget: 1M
Phone goal saved over 8 months: 10M
Phone bought in April
```

Bad display:

```text
Electronics: 10M / 1M
Over budget by 9M
```

Better display:

```text
Electronics
Normal spending: 300k / 1M
Goal-funded planned purchase: Phone 10M
Electronics total analytics: 10.3M
```

Rule:

```text
Full goal-funded purchase:
  include in category analytics
  exclude from normal monthly budget enforcement
  show separately as goal-funded planned purchase

Installment payment:
  include in monthly cashflow / obligation planning
  show as monthly obligation or installment payment
```

Useful budget impact values:

```text
NORMAL
GOAL_FUNDED_EXCLUDED
MONTHLY_OBLIGATION
```

### Installment Taxonomy Rule

`Installment` is not a spending category.

Wrong:

```text
Category: Installments
```

Correct:

```text
Category: Electronics
Context: Installment payment
Linked installment: iPhone installment
Budget impact: Monthly obligation
```

Examples:

```text
Phone installment -> Electronics
Car installment -> Transport / Vehicle
Sofa installment -> Home / Furniture
Course installment -> Education
Medical installment -> Health
```

Installments should exist as:

```text
module/page/obligation type
```

not as:

```text
top-level budget category
```

### Final Model

Separate these dimensions:

```text
Category = what was bought
Payment method = how it was paid
Obligation link = what debt/installment it reduces
Budget impact = how monthly budget treats it
Funding context = normal / goal-funded / reserve-backed
```

### What To Implement Later

- [ ] Keep planned-purchase goal intent unchanged.
- [ ] Add completion outcome: fully paid purchase.
- [ ] Add completion outcome: down payment + installment.
- [ ] Add completion outcome: full installment reserve.
- [ ] Do not model `Installments` as a spending category.
- [ ] Ensure installment payments keep the real category of the purchased thing.
- [ ] Add budget impact distinction for monthly obligation payments.
- [ ] Show goal-funded purchases separately from normal monthly budget spend.
- [ ] Keep category analytics honest by including goal-funded and installment-related purchases.

### Final Rule

```text
Goal intent describes why money is being saved.
Completion outcome describes what happens at purchase time.
Installment describes financing/payment structure, not spending category.
```

## EC-033 - Planned Purchase Achieved Outside Reserved Funds

### Discovery

A planned-purchase goal can be achieved even when the reserved goal money did not actually pay for the purchase.

The two truths are separate:

```text
Goal purpose achieved != reserved goal money used
```

Example:

```text
Laptop Goal
Target: 10M
Reserved:
- Savings: 5M
- Cash: 3M
- Debit: 2M

Actual purchase:
- Debit paid 10M
```

The user now owns the laptop, so the goal should not remain active as "still saving for laptop". But if the user did not use the reserved goal money, Sarflog should not pretend that Savings/Cash paid for it.

### Completion Modes

```text
GOAL_FUNDED
- Reserved goal money paid for the purchase.
- Payment wallets must have enough reserved money in this goal.
- Expense is linked as goal-funded planned purchase.
- Goal allocations are consumed.
- Normal monthly budget enforcement is skipped, but category analytics keep the purchase.

ACHIEVED_OUTSIDE_RESERVED_FUNDS
- User bought the planned item with other money.
- Expense is recorded from the actual payment wallets.
- Goal is completed because the purpose was achieved.
- Reserved allocations are returned/unreserved.
- No wallet transfer is created.
- Expense is still excluded from normal monthly budget spending because the user had already saved enough to qualify it as a planned cross-period purchase.
```

### Transfer Rule

Sarflog must not create fake wallet transfers.

```text
Wallet transfer in Sarflog = real money physically moved between real wallets.
```

If a user really transfers Savings -> Debit before or after a purchase, that transfer should be recorded as a real wallet transfer, including any transfer fee if it exists.

If the user bought the item with other money and did not move the reserved goal money, use `ACHIEVED_OUTSIDE_RESERVED_FUNDS` and release the goal allocations instead.

### Real World Examples

```text
Case 1 - Goal funded
Savings reserved: 10M
Savings paid laptop: 10M
Result:
- Savings wallet -10M
- Goal allocation consumed 10M
- Goal completed as GOAL_FUNDED
```

```text
Case 2 - Achieved outside reserved funds
Savings reserved: 10M
Debit paid laptop: 10M
No Savings -> Debit transfer happened
Result:
- Debit wallet -10M
- Savings stays 10M
- Savings goal allocation returned/unreserved
- Goal completed as ACHIEVED_OUTSIDE_RESERVED_FUNDS
```

```text
Case 3 - User transferred first
Savings reserved: 10M
User physically transfers Savings -> Debit: 10M
User pays laptop from Debit: 10M
Correct app flow:
- Record real wallet transfer Savings -> Debit
- Rebalance/return/re-reserve goal funding as needed
- Record purchase from the wallet that now actually paid
```

### Implementation Notes

- [x] Add `goal.completion_mode`.
- [x] Add `GOAL_FUNDED` completion mode.
- [x] Add `ACHIEVED_OUTSIDE_RESERVED_FUNDS` completion mode.
- [x] Planned purchase goal-funded mode records `goal_planned_purchase` and consumes allocations.
- [x] Planned purchase outside-funds mode records `goal_achieved_outside_funds` and returns allocations.
- [x] Outside-funds mode does not create reimbursement transfers.
- [x] Outside-funds mode stays outside normal monthly budget enforcement because the purchase was goal-qualified before checkout.
- [x] Frontend asks the user a natural language question instead of exposing only settlement jargon.

### Budget Impact Correction

Budget treatment should be based on planning qualification, not physical payment wallet.

```text
If the planned-purchase goal was sufficiently funded before purchase:
  Exclude from ordinary monthly budget pressure.

Even if:
  A different wallet paid at checkout.
```

Reason:

```text
The user did not randomly overspend this month.
The user saved across time, then used a proxy/payment wallet at checkout.
```

Sarflog should still show the purchase in category analytics:

```text
Electronics total:
- Normal monthly spending
- Planned goal purchases
```

But the normal monthly Electronics limit should not be punished by a purchase that was already funded through a planned goal.

---

## EC-035 - Opinionated Planned Purchase Preparation Rule

**Status:** DECIDED
**Severity:** S1
**Area:** Goals / Planned Purchase / Wallet Preparation / Budget Impact
**Discovered on:** 2026-05-27
**Reported by:** User

### Final Decision

Sarflog should be opinionated:

```text
A planned-purchase goal becomes a goal-funded purchase only if the user prepares the payment wallet(s) before checkout.
```

This removes the reimbursement maze:

```text
No after-the-fact guessing.
No silent reimbursement transfers.
No fake "Savings paid Debit" if the real transfer never happened.
```

### Real-World Rule

```text
Prepare payment = before checkout
Record purchase = after checkout
```

If the user wants Wallet B to pay at checkout, but the goal money is in Wallet A, they must first use:

```text
Prepare payment
```

which records:

```text
Wallet A -> Wallet B real transfer
Move this goal's allocation label from Wallet A to Wallet B
```

Then the purchase can be recorded from Wallet B as a goal-funded purchase.

### Wallet Count Rule

Limit planned-purchase preparation to:

```text
maximum 3 payment wallets
```

Reasoning:

```text
1 wallet = normal case
2 wallets = common enough for cash + card or two accounts
3 wallets = realistic upper bound for a human checkout
4+ wallets = bookkeeping complexity that should not be first-class UX
```

This is a product cap, not a mathematical limit.

### Eligible Prepared Payment Wallets

Allowed for prepared goal-funded purchase:

```text
- Cash
- Debit with positive owned balance
- Savings wallet/account
- Prepaid/payment wallet backed by owned money
```

Not allowed:

```text
- Credit card
- Liability wallet
- Overdraft capacity
- Any borrowed-money source
```

Reason:

```text
Goal-funded purchase = owned money reserved for a purpose.
Credit/overdraft = borrowed capacity.
```

Allowing credit cards in goal-funded mode would mix saved money with debt and reopen reimbursement/debt complexity.

### Credit Card Case

If user pays with a credit card anyway:

```text
Do not allow it in prepared goal-funded mode.
```

Instead use the off-plan path:

```text
I bought this from an unplanned wallet/card
```

Result:

```text
- Goal can still be completed as planned-achieved/off-plan
- Real credit/card payment is recorded truthfully
- Reserved goal money is released or handled by explicit follow-up action
- No fake goal-funded payment is created
```

Later advanced feature:

```text
Pay by credit card and immediately repay from goal funds
```

This is not v1 because it requires credit liability + repayment modeling.

### Off-Plan Purchase Path

If user ignores preparation and buys from Wallet D/F:

```text
They cannot record it as goal-funded.
```

But Sarflog should still respect intent:

```text
The user planned and funded the purchase.
They broke the wallet-preparation rule, not necessarily the saving discipline.
```

So the goal flow can offer:

```text
I bought this from an unplanned wallet/card
```

This records:

```text
- Actual payment wallet(s)
- Goal completed as off-plan achieved
- Goal allocations released
- Purchase included in category analytics
- Purchase excluded from ordinary monthly budget enforcement because it was a funded planned purchase
```

Important:

```text
Do not add a global "exclude from budget" toggle to random expenses.
```

Budget exclusion should come from a real planned-purchase goal context, not a generic loophole.

### UX Shape

Record Purchase wizard should only offer:

```text
1. I paid from the prepared goal wallet(s)
2. I bought this from an unplanned wallet/card
```

If option 1:

```text
Only prepared/funding wallets appear.
Credit cards do not appear.
Max 3 payment rows.
```

If option 2:

```text
Explain that this completes the goal off-plan.
Ask for actual payment wallet(s).
Release reserved goal money.
Keep budget treatment as planned-purchase excluded.
```

### Implementation Notes

- [ ] Cap planned-purchase payment rows to 3.
- [ ] Ensure prepared goal-funded payment wallets exclude credit/liability/overdraft capacity.
- [ ] Rename off-plan UX from technical wording to human wording.
- [ ] Keep off-plan budget impact excluded only when linked to a sufficiently funded planned-purchase goal.
- [ ] Do not expose a global "exclude from monthly budget" toggle on ordinary expenses.
- [ ] Add tests for credit card rejection in goal-funded purchase flow.
- [ ] Add tests for off-plan purchase completion with credit card/non-funding wallet.

---

## EC-036 - Transfer And ATM Fees For Wallet Movements

**Status:** IDEA
**Severity:** S2
**Area:** Wallets / Transfers / Goals / Fees / Expenses
**Discovered on:** 2026-05-27
**Reported by:** User

### Problem

Sarflog has wallet transfers, cash withdrawals, and goal-payment preparation, but real money movement can have fees:

```text
- Online bank transfer fee
- Card-to-card transfer fee
- ATM cash withdrawal fee
- Currency conversion/transfer service fee
```

Example:

```text
User prepares Laptop Goal:
Savings -> Debit: 10M
Bank fee: 10k
```

If Sarflog records only:

```text
Savings -10M
Debit +10M
```

but the bank actually shows:

```text
Savings -10,010,000
Debit +10,000,000
```

wallet balances drift from reality.

### Correct Model

Transfer fee is not part of the transferred principal.

It is a separate financial cost attached to the transfer.

The product abstraction should be generic:

```text
Add fee
```

Do not create separate mechanics for:

```text
ATM fee
transfer fee
card-to-card fee
withdrawal fee
bank service fee
```

Those can be labels, categories, subcategories, or notes. The backend behavior should be one reusable linked-fee operation.

```text
Transfer principal:
Savings -10M
Debit +10M

Transfer fee:
Savings -10k
Expense category: Bank fees
```

For ATM withdrawal:

```text
Debit -> Cash: 1M
ATM fee from Debit: 10k
```

Reality:

```text
Debit -1,010,000
Cash +1,000,000
Bank fee expense 10,000
```

### Where This Belongs

Use one unified backend service if possible:

```text
WalletTransferService.transfer_with_optional_fee()
```

It should support:

```text
- Normal wallet transfer
- Goal prepare-payment transfer
- ATM withdrawal
- Card-to-card transfer
```

Fee fields:

```text
fee_amount
fee_wallet_id
fee_category = Bank Fees
fee_subcategory optional
fee_note optional
```

Default:

```text
fee_wallet_id = source_wallet_id
```

because fees usually leave the sending wallet/card.

### Goal Interaction

Goal allocation should move only with the transfer principal:

```text
Goal allocation moved: 10M
Fee: 10k normal expense
```

Do not count fee as goal-funded laptop money unless the user explicitly models a broader project or purchase cost later.

Example:

```text
Laptop goal target: 10M
Prepare payment:
Savings -> Debit: 10M
Fee: 10k

Laptop goal still prepared for 10M.
Bank fee appears separately.
```

### UX Placement

Wallets page:

```text
Transfer money
[ ] Add transfer fee
```

Goals page, Prepare payment dialog:

```text
Move goal money
[ ] Add transfer fee
```

ATM/cash withdrawal flow:

```text
Withdraw cash
[ ] Add ATM fee
```

### Implementation Notes

- [x] Add optional fee support to wallet transfer service.
- [x] Store fee as a real expense/financial event linked to the transfer.
- [x] Add fee fields to normal wallet transfer UI.
- [x] Add fee fields to goal Prepare payment UI.
- [ ] Add ATM fee support where cash withdrawals are modeled.
- [ ] Ensure fee affects monthly budget under Bank Fees unless excluded by an explicit future policy.
- [x] Add tests that transfer principal and fee do not get mixed.

---

## EC-037 - Multi-Wallet Planned Purchase Payment Preparation

**Status:** IMPLEMENTED
**Severity:** S1
**Area:** Goals / Planned Purchase / Wallet Transfers / UX
**Discovered on:** 2026-05-27
**Reported by:** User

### Problem

The current Prepare payment dialog is too narrow. It assumes:

```text
one goal-funded source wallet -> one target payment wallet
```

Real planned purchases can require a small routing plan:

```text
Goal funding currently in:
- Savings: 6M
- Cash: 4M

Checkout plan:
- Debit card: 7M
- Cash: 3M

Preparation:
- Savings -> Debit: 6M
- Cash -> Debit: 1M
- Cash keeps 3M reserved for direct checkout
```

Another realistic case:

```text
Goal funding currently in:
- Savings card: 5M
- Cash envelope: 3M
- Prepaid app wallet: 2M

Checkout plan:
- Debit card: 6M
- Cash: 2M
- Prepaid app wallet: 2M
```

The user must be able to move money from each funded source wallet into up to three real checkout wallets before purchase.

### Correct Rule

Prepare payment is not normal goal funding.

```text
Goal funding source list:
  only wallets allowed to reserve/fund goals

Prepare payment target list:
  active owned-money payment wallets
  same currency
  CASH / DEBIT / PRELOADED / SAVINGS allowed
  can_fund_goals NOT required
  CREDIT / liability / borrowed-money wallets excluded
```

Reason:

```text
The destination wallet is the checkout instrument, not a long-term savings container.
```

Real world:

```text
User saves in Savings, but store accepts only debit.
User saves in card account, but bazaar accepts cash.
User saves in multiple wallets, but checkout is split across debit + cash.
```

### Backend Shape

Use plural moves:

```text
moves: [
  { source_wallet_id, target_wallet_id, amount, fee_amount?, fee_wallet_id?, fee_note? },
  { source_wallet_id, target_wallet_id, amount, fee_amount?, fee_wallet_id?, fee_note? }
]
```

Rules:

```text
- Up to 3 target payment wallets.
- Up to 9 move rows for now.
- Each source -> target pair appears once.
- Sum moved from each source cannot exceed that source's unreleased goal funding.
- Each move creates a real wallet transfer.
- Each move returns goal funding from source and allocates the same amount to target.
- Optional fee is a linked bank-fee expense and is not part of goal money.
- All moves run in one transaction.
```

### UX Shape

The API remains a flat routing table, but the UI should be grouped by source wallet because that is how users think about preparation:

```text
Prepare checkout wallets

Source: Savings / 6M reserved
  -> Debit card          6M

Source: Cash / 4M reserved
  -> Debit card          1M

Cash remains prepared: 3M
```

Target wallets shown here should include owned payment wallets even when `goals: off`.

Grouped UI rules:

```text
- A source wallet appears once as a group.
- Each source group can spread money to up to 3 destination payment wallets.
- The whole dialog can still use up to 3 distinct destination payment wallets.
- Each source -> destination pair appears once.
- Each destination row can have its own transfer fee.
- The backend still receives flat `moves[]`; grouping is presentation only.
```

This avoids corrupting the accounting model:

```text
User mental model:
  Cash reserved 10M -> split to Debit1, Debit2, Debit3

Ledger/API truth:
  Cash -> Debit1
  Cash -> Debit2
  Cash -> Debit3
```

### Confirmation Dialog

Before submit, show a compact review:

```text
Prepare Laptop40 payment

Sarflog will record real wallet transfers and move this goal's reserved-money label with them.

Money movement
Cash -> Debit1        4,000,000 UZS
Cash -> Debit2        3,000,000 UZS
Cash -> Debit3        3,000,000 UZS

Transfer fees
Cash fee                 10,000 UZS
Debit3 fee                5,000 UZS

Goal result
Laptop40 prepared in:
Debit1                4,000,000 UZS
Debit2                3,000,000 UZS
Debit3                3,000,000 UZS

Fees are normal bank-fee expenses. They are not goal money.
```

### Implementation Notes

- [x] Backend accepts plural `moves`.
- [x] Backend keeps legacy single move payload temporarily normalized into `moves`.
- [x] Backend allows owned target payment wallets with goals off.
- [x] Backend rejects credit/liability target wallets.
- [x] Frontend renders grouped source wallets with multiple destination rows.
- [x] Frontend caps distinct target payment wallets at 3.
- [x] Frontend confirms real transfers, fees, and goal-label result before submit.
- [x] Tests cover multi-source/multi-target preparation.

## EC-038 - Reserve Goals Need Their Own Mental Model

**Status:** Pending execution  
**Area:** Goals / Reserve Intent / Set Money Aside / Budget Impact / Session Expenses / Savings Wallet Modeling

### Discovery

The current internal intent `RESERVE` is valid, but the user-facing name needs care.

Better wording:

```text
Internal enum:
RESERVE

User-facing creation option:
Set money aside

Goal type label:
Reserve fund
```

Reason:

```text
Reserve money
```

is technically correct, but less natural. Users understand the action better:

```text
I want to set money aside.
```

### Real World Existence

Reserve goals absolutely exist in real life. They are not "buy one item" goals.

Examples:

```text
Emergency fund
Medical reserve
Rent cushion
Family support reserve
Rainy-day money
Travel backup money
General savings buffer
"Do not touch this 5M unless needed"
```

Core meaning:

```text
Reserve goal = protected flexible money for uncertain future use.
```

This differs from planned purchase:

```text
Planned purchase = protected money for one known purchase.
Reserve fund = protected money for one or more uncertain future events.
```

### Wallet Reality

People do not always keep reserve money in a formal bank savings account.

Real examples:

```text
Emergency reserve:
- 5M in savings wallet
- 2M cash at home
- 1M on debit card

Rent cushion:
- 2M on debit wallet because rent is paid from that card

Family support reserve:
- 3M on debit
- 500k cash
```

Therefore Reserve goals should support the same wallet-backed allocation rule:

```text
Allowed funding sources:
- Savings
- Cash
- Debit
- Preloaded

Not allowed:
- Credit cards
- Liability wallets
- Overdraft capacity
```

Invariant:

```text
Wallet balance = real money
Reserve allocation = protected label on part of that wallet money
Free-to-spend = wallet balance - protected reserve allocations
```

### Lifecycle Rule

Reserve goals should not behave like completed purchase goals.

Reaching target means:

```text
Fully reserved
```

not:

```text
Done forever
```

A reserve fund can stay active for months or years and can be used multiple times.

Example:

```text
Medical Reserve target: 10M

June:
- Dental treatment: 800k
- Medicine: 300k
- Taxi to clinic: 80k

July:
- Car repair: 1.5M
```

After each use, the reserve funding decreases, but the goal can remain active.

### Multiple Expenses

Unlike `PLANNED_PURCHASE`, Reserve goals may fund more than one expense.

Correct rule:

```text
PLANNED_PURCHASE:
  one goal -> one purchase event

RESERVE:
  one goal -> many possible reserve-funded expenses over time
```

This creates a future need to connect Reserve goals to Session/Basket mode.

Real-world session example:

```text
Medical emergency session:
- Doctor fee
- Lab test
- Medicine
- Taxi
```

All rows are separate expenses, possibly different categories, but one reserve-funded event.

Implementation direction:

```text
Phase 1:
Use reserve for one expense.

Phase 2:
Use reserve for a basket/session of expenses.
```

Do not block the Reserve refactor on Session support, but design the model so Session can be added later.

### Budget Impact

Reserve-funded expenses should be included in analytics and cashflow, but usually excluded from normal monthly budget enforcement.

Example:

```text
Health monthly budget: 500k
Emergency reserve used for surgery: 4M
```

Bad display:

```text
Health: 4M / 500k
Over budget by 3.5M
```

This falsely says the user failed normal monthly health spending.

Better display:

```text
Health
Normal monthly spending: 300k / 500k
Reserve-funded spending: 4M
Total Health spending: 4.3M
```

Final budget rule:

```text
Normal expense:
  counts against monthly category budget

Planned purchase goal expense:
  excluded from normal monthly budget enforcement
  shown separately as goal-funded planned spending

Reserve-funded expense:
  excluded from normal monthly budget enforcement by default
  shown separately as reserve-funded spending
```

Analytics must remain honest:

```text
- Category reports include reserve-funded expenses.
- Cashflow includes reserve-funded expenses.
- Expense history includes reserve-funded expenses.
- Reserve drawdown report shows what consumed reserve money.
```

### Prepare Payment For Reserve Goals

Reserve goals should reuse a version of Prepare Payment, but with Reserve wording.

Real example:

```text
Emergency Reserve funded from Savings: 5M
Hospital accepts only debit card.
```

Correct flow:

```text
1. Prepare payment:
   Savings -> Debit: 1M
   Goal label moves with the money.

2. Pay hospital from Debit:
   Debit -1M
   Reserve allocation from Debit consumed.
```

Wording should not say "prepare purchase" for Reserve.

Better wording:

```text
Move reserve money before payment
```

or:

```text
Prepare reserve payment
```

Difference from Planned Purchase:

```text
Planned purchase:
  prepare for one final purchase.

Reserve:
  prepare for one reserve-funded expense or session.
```

### Savings Wallet Modeling

The current `SAVINGS` wallet type is useful, but real bank savings accounts can have extra properties:

```text
interest rate
interest payout schedule
withdrawal limits
minimum balance
lock/maturity period
early withdrawal penalty
```

This does not block Reserve goals.

Current rule:

```text
Savings wallet = owned money location
Reserve goal = purpose label on money
Interest income = income event into that wallet
```

Future improvement:

```text
Add optional savings-account properties to Savings wallets.
Do not merge Savings wallet behavior into Reserve goal behavior.
```

### Bridge From Broad Reserve To Specific Purpose

Reserve goals can naturally evolve into more specific plans.

This is a real-world lifecycle:

```text
Vague future need
-> protected reserve money
-> life becomes specific
-> move part of that reserve into a concrete goal/project/obligation
```

Example:

```text
Travel Reserve
Target: 50M
Funded: 50M

Later:
User decides to go to Bahamas.
Estimated cost: 30M.
```

Correct bridge:

```text
Travel Reserve: 50M -> 20M
Bahamas Trip: 0M -> 30M
```

Wallet balances do not change.

Only purpose labels change:

```text
Before:
Savings Wallet balance: 50M
Reserved for Travel Reserve: 50M

After:
Savings Wallet balance: 50M
Reserved for Travel Reserve: 20M
Reserved for Bahamas Trip: 30M
```

This must not create income, a wallet transfer, or duplicate money.

Other real-world examples:

```text
Medical Reserve -> Dental Treatment planned expense
Medical Reserve -> Surgery project
Repair Reserve -> Car Repair project
Opportunity Fund -> Small Business Launch project
General Reserve -> Wedding project
Travel Reserve -> Bahamas Trip project
```

Destination depends on shape:

```text
One known purchase/expense:
  Reserve -> Planned Purchase goal

Multiple related expenses:
  Reserve -> Fund Project goal or directly to Project funding

Existing repayment need:
  Reserve -> Pay Obligation goal
```

Fresh architecture insight:

```text
Do not model this as "change Reserve intent to Fund Project intent".
Model it as "reassign reserved funds to a more specific purpose".
```

Potential generic operation:

```text
Reassign reserved funds

source_goal_id
destination_type: GOAL | PROJECT | OBLIGATION
destination_id or create_new payload
amount
wallet_allocation_breakdown
```

For multi-wallet reserves:

```text
Travel Reserve: 50M
- Savings: 35M
- Debit: 15M

Move 30M to Bahamas:
- default option: choose wallet breakdown manually
- later shortcut: proportional split
```

Senior decision:

```text
Manual wallet selection is safer for first implementation.
Proportional split can be an optional helper later.
```

Potential UX wording:

```text
Use reserve for a specific plan
Move reserved money to a new purpose
Turn reserve into a project
```

Avoid user-facing wording:

```text
Reclassify allocation
Convert intent
```

This is valuable, but not a first Reserve MVP requirement.

Execution order:

```text
1. Make Reserve use work for single expenses.
2. Make Reserve prepare-payment wording correct.
3. Add Reserve -> specific goal/project bridge.
4. Later add Reserve -> Session/Basket usage.
```

### Implementation Notes

- [ ] Rename user-facing `Reserve money` wording to `Set money aside` / `Reserve fund`.
- [ ] Keep internal enum as `RESERVE`.
- [ ] Ensure Reserve goals can remain active after reaching target.
- [ ] Support multiple Reserve uses over time.
- [ ] Keep Reserve expenses linked to category/subcategory/project where applicable.
- [ ] Add budget-impact handling for reserve-funded spending separate from normal monthly budget enforcement.
- [ ] Reuse Prepare Payment for Reserve with reserve-specific wording.
- [ ] Later: add append-only `goal_activity_events` for non-money lifecycle history such as target changes, title changes, archive/restore, and status changes.
- [ ] Later: add `Reassign reserved funds` bridge from Reserve to a specific goal/project/obligation.
- [ ] Later: connect Reserve use to Basket/Session mode.
- [ ] Later: add optional savings-account wallet properties such as interest and withdrawal rules.

### Final Rule

```text
Reserve goals are protected flexible money.
They can be funded from multiple owned-money wallets.
They can fund multiple real expenses over time.
They should not be treated as one-purchase completion goals.
When a vague reserve becomes specific, move the protected allocation label to the new purpose without changing wallet balances.
Reserve-funded expenses remain visible in analytics, but should not punish normal monthly category budgets by default.
```

---

## EC-039 - Debts, Loans, And Installments Refactor Plan

**Status:** DESIGN_CONFIRMED
**Severity:** S0
**Area:** Debts / Loans / Installments / Assets / Wallets / Ledger / UX
**Discovered on:** 2026-05-31
**Reported by:** User

### Problem

The current Debts page is moving toward a serious obligation model, but the mental model can become confusing if the product exposes every financial subtype as a top-level concept.

Current user-facing concepts include:

```text
Debts
Installments
Loans
Mortgages
Car loans
Friend debts
Delayed expenses
Receivables
Charges
Assets/collateral
```

If these are modeled as separate financial truth systems, Sarflog will eventually duplicate balance logic across:

```text
debts.remaining_amount
debt_ledger_entries
installment_plans.remaining_amount
installment_payments
financial_events
wallet_ledger
entity_ledger
assets
```

That creates drift, especially when users edit, reverse, settle, partially pay, or close an obligation.

### Core Decision

Use one obligation truth model.

```text
Debt = obligation/receivable identity and cached state
DebtLedgerEntry = lifecycle and balance movement truth
FinancialEvent = real wallet/income/expense movement, if any
WalletLedger = actual wallet impact
EntityLedger = budget/income/project/debt classification
InstallmentPlan = purchase contract and schedule UX, not independent balance truth
Formal loan details = optional metadata, not balance truth
```

Do not add a separate loan balance engine.

Do not add a separate installment balance engine.

Do not add a duplicate `debt_events` table if `debt_ledger_entries` can be evolved into the canonical debt lifecycle ledger.

### Taxonomy Rule

The main accounting axes are:

```text
direction:
- I_OWE
- OWED_TO_ME

origin_kind:
- CASH_BORROWED
- CASH_LENT
- DEFERRED_EXPENSE
- SPLIT_REIMBURSEMENT
- RECEIVABLE_INCOME
- FINANCED_ASSET_PURCHASE
- IMPORTED_BALANCE

counterparty_kind:
- PERSON
- BANK
- COMPANY
- STORE
- GOVERNMENT
- OTHER

product_kind:
- INFORMAL_DEBT
- BANK_LOAN
- CAR_LOAN
- MORTGAGE
- STORE_INSTALLMENT
- SERVICE_PAY_LATER
- PERSONAL_REIMBURSEMENT
- CLIENT_RECEIVABLE
- OTHER
```

`product_kind` is descriptive metadata. It must not decide accounting behavior by itself.

Accounting behavior comes from:

```text
direction + origin_kind + lifecycle event
```

### Real-World Mapping

#### Friend Gives Me Cash

```text
I borrow 2M from Ali.
Ali gives me cash.
```

Sarflog:

```text
debt_type = OWING
origin_kind = CASH_BORROWED
counterparty_kind = PERSON
product_kind = INFORMAL_DEBT
wallet +2M
debt +2M
not income
```

#### Bank Cash Loan

```text
Bank gives me 20M into debit card.
I owe the bank.
```

Sarflog:

```text
debt_type = OWING
origin_kind = CASH_BORROWED
counterparty_kind = BANK
product_kind = BANK_LOAN
wallet +20M
debt +20M
not income
formal loan details optional
```

#### Bank Finances A Car

```text
Car price: 200M
Down payment: 50M
Bank pays seller 150M
I owe bank 150M
```

Sarflog:

```text
debt_type = OWING
origin_kind = FINANCED_ASSET_PURCHASE
counterparty_kind = BANK
product_kind = CAR_LOAN
wallet -50M if down payment was paid
asset = car
debt +150M
collateral_asset_id = car if applicable
```

No wallet inflow is required for the financed portion.

#### Mortgage

```text
Apartment price: 800M
Down payment: 200M
Mortgage: 600M
Monthly payment: 8M
```

Sarflog:

```text
debt_type = OWING
origin_kind = FINANCED_ASSET_PURCHASE
counterparty_kind = BANK
product_kind = MORTGAGE
linked_asset_id = apartment
collateral_asset_id = apartment
debt +600M
expected_payment_amount = 8M
next_due_date optional
```

Mortgage is a formal debt with a repayment schedule. It is not primarily an installment plan.

#### Mechanic Repair Pay Later

```text
Mechanic repaired my car for 500k.
I will pay next week.
```

Sarflog:

```text
debt_type = OWING
origin_kind = DEFERRED_EXPENSE
counterparty_kind = PERSON or COMPANY
product_kind = SERVICE_PAY_LATER
category = Transport / Repair
no wallet movement at creation
debt +500k
```

When paid:

```text
wallet -500k
debt -500k
expense/category meaning is applied because this was a delayed expense
```

#### Client Receivable

```text
Client owes me 5M for completed work.
No wallet money left me.
```

Sarflog:

```text
debt_type = OWED
origin_kind = RECEIVABLE_INCOME
counterparty_kind = COMPANY or PERSON
product_kind = CLIENT_RECEIVABLE
income_source_id required or strongly encouraged
debt/receivable +5M
no wallet movement at creation
```

When paid:

```text
wallet +5M
receivable -5M
income classification depends on income_source_id
```

### Table Refactor Direction

#### `debts`

Keep as the main obligation identity and current cached state.

Add:

```text
origin_kind
counterparty_kind
product_kind nullable
```

Keep:

```text
debt_type
counterparty_name
initial_amount
remaining_amount
status
date
expected_return_date
expense_category
expense_subcategory_id nullable
project_id nullable
project_subcategory_id nullable
income_source_id
```

Deferred expenses must carry category and subcategory when the covered thing is known.

Real examples:

```text
Friend paid my taxi.
direction = I_OWE
origin_kind = DEFERRED_EXPENSE
expense_category = Transport
expense_subcategory_id = Taxi
```

```text
Store installment for sofa.
direction = I_OWE
origin_kind = FINANCED_ASSET_PURCHASE
expense_category = Home
expense_subcategory_id = Furniture
linked_asset_id = Sofa asset, if user wants asset tracking
```

Do not use `Installments & Debt` as the real spending category. Installment is the payment/contract context; the thing bought still needs the real category.

As part of this refactor, demote `is_money_transferred` from a meaning-defining field to a derived/backward-compatible money-movement flag.

New records should derive wallet movement from:

```text
origin_kind
initial_wallet_allocations / financial event legs
linked asset or financed purchase context
```

Do not let `is_money_transferred` decide debt meaning anymore. It is not expressive enough for financed asset purchases.

Important example:

```text
Bank pays seller for my car.
No wallet money enters my hands.
But this is not the same as a mechanic delayed expense.
```

Both may look like `is_money_transferred=false` in the old model, but their meanings are different. That is why this refactor must introduce `origin_kind` now, not later.

#### `debt_formal_details`

Add a side table for formal loans and bank/company obligations.

```text
debt_formal_details
- debt_id PK/FK
- contract_number nullable
- institution_name nullable
- linked_asset_id nullable
- collateral_asset_id nullable
- collateral_note nullable
- expected_payment_amount nullable
- next_due_date nullable
- maturity_date nullable
- interest_rate nullable
- last_statement_balance nullable
- last_statement_date nullable
```

Rules:

```text
This table is metadata.
It does not own the balance.
Bank statement/user-confirmed balance remains the source of truth.
```

#### `debt_ledger_entries`

Evolve this into the canonical debt lifecycle ledger.

Existing useful fields:

```text
entry_type
amount_delta
principal_delta
charge_delta
financial_event_id
source_debt_transaction_id
source_debt_charge_id
reverses_entry_id
wallet_id
asset_id
extra_data
```

Potential additions:

```text
balance_after nullable
event_subtype nullable
source nullable  -- USER / SYSTEM / IMPORT
```

Use `event_subtype` to avoid enum explosion:

```text
entry_type = CHARGE
event_subtype = INTEREST / LATE_FEE / PENALTY / INSURANCE / LEGAL_FEE

entry_type = ADJUSTMENT
event_subtype = BALANCE_CORRECTION / STATEMENT_SYNC / TERMS_RESTRUCTURED

entry_type = FORGIVENESS
event_subtype = PERSONAL_FORGIVE / SETTLEMENT_DISCOUNT / WRITE_OFF

entry_type = ASSET_SETTLEMENT
event_subtype = ASSET_RECEIVED / ASSET_GIVEN / COLLATERAL_TAKEN
```

#### `debt_transactions`

Keep as the user-facing payment/receipt record if useful, but do not let it be the balance source.

Add allocation support:

```text
debt_transaction_wallet_allocations
- id
- debt_transaction_id
- wallet_id
- amount
```

One debt payment may touch multiple wallets.

Example:

```text
Car loan payment: 4M
- Debit: 2.5M
- Cash: 1.5M
```

#### `debt_charges`

Keep or merge into ledger later, but preserve the distinction:

```text
Debt charge added
-> obligation increases
-> no wallet movement yet

Debt charge paid
-> wallet outflow
-> charge settlement
```

Formal loans can use the same charge primitive for:

```text
interest
late fee
penalty
insurance fee
service fee
legal fee
collection fee
```

Do not build a calculation engine for these yet. Let users type the bank-confirmed values.

#### `debt_asset_settlements`

Add only when asset/collateral settlement is implemented.

```text
debt_asset_settlements
- id
- debt_id
- ledger_entry_id
- asset_id
- settlement_direction  -- RECEIVED_ASSET / GIVEN_ASSET / COLLATERAL_TAKEN
- settlement_amount
- note
```

Critical rule:

```text
settlement_amount is explicit.
Do not assume asset.current_value equals debt settlement amount.
```

Example:

```text
I owe bank 80M on car loan.
Bank repossesses car and applies 60M value.

Debt ledger:
ASSET_SETTLEMENT amount_delta = -60M

Asset:
status = repossessed / used_for_debt_settlement

Remaining debt:
20M
```

### Installment Refactor Direction

Do not remove installment tables.

Do demote them.

```text
InstallmentPlan is not the obligation.
Debt is the obligation.
InstallmentPlan is the purchase contract and schedule attached to the debt.
```

#### `installment_plans`

Modify to reference the underlying debt.

```text
installment_plans
- id
- debt_id FK
- item_name
- store_or_bank_name
- total_price
- down_payment
- purchase_category
- subcategory_id nullable
- project_id nullable
- linked_asset_id nullable
- months
- frequency
- start_date
```

Long-term, avoid treating `installment_plans.remaining_amount` as independent truth. Remaining obligation should come from `debts.remaining_amount`, reconciled from `debt_ledger_entries`.

#### `installment_payments`

Scheduled rows should become due buckets, not hard full-payment-only records.

```text
installment_payments
- id
- plan_id
- due_date
- amount_due
- amount_paid
- status  -- PENDING / PARTIAL / PAID / SKIPPED
- paid_date nullable
- financial_event_id nullable
- debt_ledger_entry_id nullable
```

#### `installment_payment_allocations`

Add actual payment allocation rows.

```text
installment_payment_allocations
- id
- plan_id
- payment_id
- financial_event_id
- debt_ledger_entry_id
- amount
- paid_date
```

This supports partial and advance payments.

Example:

```text
Phone installment:
12 months
450k per month
```

Partial payment:

```text
User pays 300k today.
Month 1 amount_due = 450k
Month 1 amount_paid = 300k
status = PARTIAL

User pays 150k next week.
Month 1 amount_paid = 450k
status = PAID
```

Advance payment:

```text
User pays 1M.

Apply oldest-first:
Month 1: 450k paid
Month 2: 450k paid
Month 3: 100k partial
```

Debt ledger:

```text
PAYMENT amount_delta = -1M
```

Wallet ledger:

```text
wallet -1M
```

### Installment Purchase Example

```text
Sofa price: 6M
Down payment: 400k
Remaining financed amount: 5.6M
12 monthly payments
Category: Home / Furniture
```

Creation:

```text
FinancialEvent:
wallet -400k
expense category = Home / Furniture

Debt:
debt_type = OWING
origin_kind = FINANCED_ASSET_PURCHASE
counterparty_kind = STORE
product_kind = STORE_INSTALLMENT
initial_amount = 5.6M

DebtLedgerEntry:
INITIAL +5.6M

InstallmentPlan:
contract/schedule for Sofa
linked to debt_id
```

Monthly payment:

```text
wallet -466k
debt -466k
installment due bucket paid/partial
expense category = Home / Furniture
budget impact = MONTHLY_OBLIGATION
```

Installment is context, not spending category.

### Formal Loan Actions

Formal loans should remain manual for math, but richer in lifecycle.

Supported lifecycle actions:

```text
Record payment
Add charge
Update confirmed balance
Change next due date / expected payment
Mark overdue / defaulted / in collection
Restructure terms
Settle / close
Collateral settlement
```

Examples:

```text
Bank adds 250k late fee.
-> DebtLedgerEntry CHARGE +250k
-> no wallet movement
```

```text
Bank app says remaining balance is 43.6M after payment.
User updates confirmed balance.
-> DebtLedgerEntry ADJUSTMENT / BALANCE_CORRECTION
```

```text
Bank accepts 40M to close a 50M debt.
-> wallet -40M
-> debt payment -40M
-> settlement discount -10M
-> status SETTLED
```

Use different UI wording by counterparty/formality:

```text
Personal debt: Forgive
Formal debt: Settlement discount / Write-off / Close as settled
```

### Status Refactor

Current statuses are too limited for formal obligations.

Consider:

```text
ACTIVE
OVERDUE
DEFAULTED
IN_COLLECTION
PAID
SETTLED
WRITTEN_OFF
ARCHIVED
```

Status is cached current state. Status history belongs in `debt_ledger_entries`.

### UI Refactor Direction

Keep the Debts page user-facing and workflow-based.

Do not expose the database taxonomy directly.

Recommended page shape:

```text
Debts & Installments

Tabs:
- I owe
- Owed to me
- Installments
```

Optional filters/badges:

```text
Borrowed money
Formal loan
Mortgage
Car loan
Delayed expense
Financed asset
Receivable
Personal payback
Installment purchase
```

Creation should become question-based:

```text
What are you adding?

1. I owe someone
   - I borrowed money / loan
   - Someone covered an expense for me
   - I financed an asset or purchase

2. Someone owes me
   - I lent money
   - Client/customer owes me
   - Personal payback

3. Installment purchase
   - Store/product installment
```

Product name for this UI pattern:

```text
Guided Debt Creation
```

It is also fair to call it a branching form, guided flow, or wizard. Avoid showing users raw technical enums like `origin_kind` and `product_kind`.

The current Debts tab already asks a small question around money transfer, but it is still one mostly flat form. The refactor should make the questions decide the branch first, then ask only fields that matter for that branch.

Example branch:

```text
What are you recording?
-> I owe someone
-> Someone covered an expense for me
-> What was covered?
   category = Transport
   subcategory = Taxi
-> Did wallet money move today?
   no
-> Result:
   create debt
   create ledger INITIAL
   no wallet ledger movement yet
   future payment becomes the actual outflow
```

Another branch:

```text
What are you recording?
-> I owe someone
-> Formal loan / borrowed money
-> Did money enter one of my wallets?
   yes, Debit card +20M
-> Result:
   create debt
   create ledger INITIAL
   create wallet inflow
```

Another branch:

```text
What are you recording?
-> Installment purchase
-> What did you buy?
   Phone, Electronics / Phone
-> Any down payment?
   300k from Cash
-> Schedule?
   12 monthly payments
-> Result:
   create debt
   create installment plan linked to debt
   create down-payment event if paid
   generate installment due buckets
```

Do not add a top-level Loans tab unless real usage proves users manage many formal loans.

Loans live under:

```text
I owe -> Formal loan
```

### Split With Friends Refactor

The expense creation form has "Split Bill" / "Friend splits". Today quick expense creation creates one `Debt` per friend and writes an initial debt ledger entry. Session draft finalization creates owed-to-me debts from draft splits, but the current code path needs to be brought to the same ledger discipline.

Target model:

```text
Expense paid by me
-> creates normal expense event and wallet outflow
-> each friend split creates an owed-to-me debt
-> each split debt uses origin_kind = SPLIT_REIMBURSEMENT
-> linked_event_id points to the original expense event
-> debt ledger gets INITIAL for that friend's share
```

Real example:

```text
Dinner total = 300k
I paid 300k from Card
Ali owes me 100k
Vali owes me 100k

Expense:
wallet -300k
category = Food / Restaurant

Debt Ali:
direction = OWED_TO_ME
origin_kind = SPLIT_REIMBURSEMENT
principal = 100k
linked_event_id = dinner event

Debt Vali:
direction = OWED_TO_ME
origin_kind = SPLIT_REIMBURSEMENT
principal = 100k
linked_event_id = dinner event
```

Repayment from Ali should not inflate income reports:

```text
Ali pays 50k cash now, 50k card later.
-> wallet +50k
-> debt -50k
-> wallet +50k
-> debt -50k
-> debt status PAID
-> reports can show reimbursement / net expense separately from income
```

Refactor requirements:

```text
1. Add SPLIT_REIMBURSEMENT as a first-class origin kind.
2. Ensure every split-created debt gets a debt ledger INITIAL entry.
3. Make quick expense split and session draft split use the same service.
4. Keep linked_event_id to the original expense event.
5. If the source expense is voided, refunded, or corrected, show dependency-aware debt effects before changing it.
6. If a split debt already has repayment history, do not silently edit/delete it from the source expense.
7. Let friend repayments be partial and multi-wallet.
8. In expense details, show "People who owe you" with each linked debt status.
```

This keeps the user's mental model simple: the split is born from an expense, but repayment is a debt lifecycle.

### Debt Detail And Storyline UI

The detail view should not be only payment history. It should be a debt story built from `debt_ledger_entries`, with transactions, charges, linked expense/income events, wallets, assets, and installment schedule shown as supporting context.

Recommended shape:

```text
Debt detail page or side sheet

Header:
- title / counterparty
- remaining balance
- status
- origin label
- next due date
- linked asset or source event

Tabs/sections:
- Overview
- Timeline
- Payments
- Charges
- Linked records
```

Timeline rows should translate ledger entries into human language:

```text
INITIAL
-> Created debt for 100k from dinner split.

PAYMENT
-> Ali paid 50k to Cash. Remaining 50k.

CHARGE
-> Bank added 250k late fee. Remaining 12.25M.

ADJUSTMENT
-> Balance corrected to match bank statement.

FORGIVENESS
-> 20k forgiven as personal settlement.

ASSET_SETTLEMENT
-> Collateral asset received and applied to debt.

REVERSAL
-> Previous payment reversed because source wallet event was voided.
```

For installment-backed debts, the story should show payment allocation, not only "paid/not paid":

```text
Phone installment:
Month 1 due = 450k
User pays 300k
-> installment bucket becomes PARTIAL
-> debt decreases by 300k
-> remaining due in bucket = 150k

One week later user pays 1M
-> 150k closes Month 1
-> 450k closes Month 2
-> 400k partially pays Month 3
```

This requires the API detail response to expose enriched ledger entries, not just raw enums. Raw fields can remain for debugging, but UI should render semantic copy.

### 2026-06-01 Follow-Up: Payment Plans, Categories, And Action Ownership

Recent product discussion added several important UX and architecture rules that should be treated as part of this refactor, not as vague future polish.

#### User-Facing Naming

`Installments` is technically understandable, but it can sound like only store "nasiya" purchases. The clearer user-facing umbrella is:

```text
EN: Payment plans
UZ: Bo'lib to'lash
Internal/domain: scheduled debt / repayment plan
```

Meaning:

```text
Payment plans = obligations with a schedule, due dates, upcoming/overdue tracking, partial payments, and advance payments.
Debts = flexible money owed / money owed to me, usually without a strict schedule.
```

Real examples:

```text
Sofa bought over 12 months -> Payment plan
Phone store installment -> Payment plan
Mortgage -> Payment plan
Auto loan with monthly schedule -> Payment plan
Education course paid over 6 months -> Payment plan
Friend lent me cash with no schedule -> Debt
Client owes me for work -> Debt
Bank cash loan with no schedule tracked -> Debt
Bank cash loan with monthly rows tracked -> Payment plan
```

Do not teach users that "payment plan" means only BNPL in the formal fintech sense. In this app, it means "I received something or took an obligation now, and I repay it over time."

#### Payment Plan Types

Add `plan_type` / `payment_plan_type` as UX/domain metadata for payment plans. This is not a new balance engine.

Recommended first set:

```text
STORE_INSTALLMENT
PRODUCT_FINANCING
MORTGAGE
AUTO_LOAN
BANK_LOAN
EDUCATION_LOAN
SERVICE_CONTRACT
OTHER
```

Rules:

```text
plan_type tells the UI what kind of obligation this is.
frequency tells the UI when payments repeat.
expense_category tells budgets what spending bucket is affected.
provider/counterparty tells who is owed.
DebtLedgerEntry remains the balance spine.
```

Do not make `plan_type` decide accounting behavior by itself. It should drive:

```text
default labels
icons
form helper copy
card badges
filters
suggested categories
linked debt product_kind
details-page wording
```

It should not yet drive:

```text
automatic interest calculation
amortization schedules
collateral enforcement
separate mortgage/car-loan balance logic
```

#### Category Suggestions From Plan Type

Yes, plan type can suggest a spending category, but it must remain editable. A plan type is not the same thing as a budget category.

Suggested defaults:

```text
MORTGAGE -> Housing
AUTO_LOAN -> Transport
EDUCATION_LOAN -> Education
STORE_INSTALLMENT / PRODUCT_FINANCING -> ask for the actual item category
SERVICE_CONTRACT -> suggest from service context, or let user choose
BANK_LOAN -> usually no default spending category unless the loan funded a known expense/asset
```

Important examples:

```text
Store-financed sofa:
plan_type = STORE_INSTALLMENT
expense_category = Home
subcategory = Furniture

Mortgage:
plan_type = MORTGAGE
expense_category = Housing

Education loan:
plan_type = EDUCATION_LOAN
expense_category = Education

Cash bank loan deposited to wallet:
plan_type = BANK_LOAN
origin_kind = CASH_BORROWED
principal repayment is balance-sheet movement, not expense
interest/fees can become expenses when paid
```

#### Category And Subcategory Requirements

Category and subcategory should be treated as real planning metadata for obligation flows that represent consumption, not as optional decoration.

Required/strongly encouraged rules:

```text
DEFERRED_EXPENSE:
- category required
- subcategory strongly encouraged
- project/project_subcategory optional when relevant

FINANCED_ASSET_PURCHASE / Payment Plan:
- category required
- subcategory strongly encouraged
- linked_asset optional when the item should be tracked as an asset

SPLIT_REIMBURSEMENT:
- inherit category/subcategory/project context from the source expense
- do not ask the user to recategorize each friend debt unless they override it intentionally

RECEIVABLE_INCOME:
- income_source required or strongly encouraged
- expense category/subcategory usually not applicable

CASH_BORROWED / CASH_LENT:
- expense category/subcategory usually not applicable
- only ask if the cash loan is explicitly tied to a known purchase/expense
```

Real examples:

```text
Mom paid dinner for me, I owe her 150k:
origin_kind = DEFERRED_EXPENSE
expense_category = Dining Out
expense_subcategory = Restaurant
debt +150k
no wallet movement at creation
future payment creates the actual outflow in Dining Out / Restaurant

Ikea sofa over 12 months:
plan_type = STORE_INSTALLMENT
origin_kind = FINANCED_ASSET_PURCHASE
expense_category = Home
expense_subcategory = Furniture
payment schedule tracks repayment

Education course paid over 6 months:
plan_type = EDUCATION_LOAN or SERVICE_CONTRACT
expense_category = Education
expense_subcategory = Courses
```

UI rule:

```text
If the flow creates a deferred expense or payment plan, ask "What was this for?" before asking only debt mechanics.
The answer should set category/subcategory.
Do not default these flows to Installments & Debt.
```

Technical rule:

```text
category = what life area/budget this belongs to
subcategory = the concrete spending lane inside that category
plan_type/product_kind = what kind of obligation this is
frequency = when payments repeat
counterparty/provider = who is owed
```

#### Frequency And Custom Schedules

Payment plans need more than monthly.

Recommended visible frequencies:

```text
WEEKLY
BIWEEKLY
MONTHLY
QUARTERLY
YEARLY
CUSTOM
```

`SEMIMONTHLY` is useful later, but it needs two due-day fields and should not be confused with `BIWEEKLY`.

Critical rule:

```text
Generated schedule rows should become the source of payment-plan due truth.
```

For custom schedules, prefer concrete editable rows over an overbuilt recurrence engine at first:

```text
User selects Custom.
UI generates or lets user enter due rows.
User reviews due date + amount for each row before save.
Payment allocation pays oldest open row first.
```

Rename confusing UI fields:

```text
months -> number of payments
monthly payment -> regular payment
```

This allows weekly, biweekly, quarterly, and custom plans without lying in the UI.

#### Formal Debt Creation Guardrail

Formal debts can exist in Debts when the user only wants to track a flexible balance. But if the obligation has a schedule, the product should guide the user to Payment Plans.

Debt creation should ask a branch question:

```text
Does this debt have scheduled payments?

Yes -> create a Payment Plan
No -> create a regular Debt
Not sure -> explain with examples
```

If the user chooses a formal debt type inside Debts, show a clear inline warning:

```text
If this loan has due dates or monthly payments, create it as a Payment Plan instead.
```

The warning should include a direct action:

```text
Create payment plan
```

This avoids users accidentally creating a regular debt when they meant mortgage, auto loan, bank loan schedule, or store financing.

#### Debt Tab Vs Payment Plan Tab Ownership

An installment/payment-plan-backed debt may appear in both places for visibility, but actions must have one owner.

Rules:

```text
Payment Plans owns scheduled payment, charge, partial payment, advance payment, and schedule-row allocation.
Debts may show the linked obligation as context/read-only summary.
Debts should not offer independent Record payment / Add charge actions for payment-plan-backed debts.
Debts should show "Managed in Payment Plans" and an "Open payment plan" action.
```

Why:

```text
If users can pay the same linked obligation from Debts and Payment Plans, debt balance and schedule rows can drift.
```

Real observed example:

```text
Sofa plan:
total_price = 6,000,000
down_payment = 400,000
underlying debt initial = 5,133,334
remaining debt = 3,183,334

Payment Plan tab progress used total_price.
Debts tab progress used debt principal/charges.
One payment was recorded through the Debts side.
Schedule rows no longer matched the debt ledger cleanly.
```

Resolution:

```text
Use one progress definition in both places, or clearly label different meanings.
Preferred card progress for Payment Plans:
paid toward plan / total plan amount, with down payment included if it was part of the plan purchase.

Debt balance:
remaining obligation from DebtLedgerEntry/debts.remaining_amount.

Do not show competing unlabeled percentages.
```

Also add a repair/reconciliation path:

```text
Find payments recorded directly against installment-linked debts.
Allocate them oldest-first to open schedule rows where possible.
Flag impossible cases for manual review.
```

#### Bidirectional Fee And Charge Entry

`Bank Fees & Interest` and `Debt Charges` should be available from the places where users naturally discover them, with guardrails.

Model:

```text
Expenses page = I already paid this cost.
Wallets page = a wallet/account/card produced the bank fee or interest.
Debt/Payment Plan page = the obligation changed, or a linked charge was paid.
```

`Bank Fees & Interest`:

```text
Can be created from Expenses when user manually records a paid fee.
Can be created from Wallets when the fee is wallet/account-specific.
Should point to wallet/account context when available.
```

`Debt Charges`:

```text
Can appear in Expenses for paid debt charges.
Linked debt charges should be created through Debt/Payment Plan services so the debt ledger stays correct.
Standalone debt-like charges without a tracked debt can still be normal expenses.
```

Keep the categories distinct:

```text
Debt Charges = interest, penalty, late fee, markup, legal/collection fee tied to a debt.
Bank Fees & Interest = bank account fee, card interest, overdraft interest, transfer fee, account maintenance fee.
```

For owed-to-me debts:

```text
Charge paid by counterparty should be income or receivable settlement context, not expense.
```

For I-owe debts:

```text
Charge paid by me should create an expense/income-classification leg as appropriate, separate from principal repayment.
```

#### Spending Category Taxonomy Cleanup

`Installments & Debt` is not a real spending category. It describes financing context, not what the user consumed.

Do not use it as a default category for new records.

Migration approach:

```text
Keep existing data readable.
Hide or demote `Installments & Debt` from normal category pickers.
For new financed purchases, require the real category: Home, Transport, Education, Electronics, etc.
For debt fees/interest, use Debt Charges or Bank Fees & Interest.
```

`Business / Work` should remain. It is a real user category for:

```text
freelance tools
client meetings
work travel
software
office supplies
business services
```

Long term, let users hide categories they do not use instead of deleting legitimate default categories.

Frontend category quality checklist:

```text
Travel must have an icon.
Charity must have an icon.
Animals & Pets must have an icon.
Bank Fees & Interest must be represented consistently if exposed in expense flows.
```

#### Implementation Notes From Current State

Current code already has most of the right primitives:

```text
DebtLedgerEntry
DebtTransaction
DebtTransactionWalletAllocation
InstallmentPaymentAllocation
FinancialEvent links
budget category fields on deferred expenses/payment-plan expenses
```

The remaining product risk is less about missing tables and more about ownership consistency:

```text
One service should create debt/payment-plan payments.
One service should split principal vs charge settlement.
One service should create expense/income events for paid charges.
One policy layer should decide which actions are available.
One UI owner should handle scheduled obligations.
```

Do not leave these as "eventual" cleanups if the current user flow already depends on them.

### What Not To Do

Avoid:

```text
separate loans table as balance source
separate installment balance truth
bank-grade interest calculation engine
forcing all debts into loan/product categories
asking category/source fields on every debt
using Installments as a spending category
using payment plan type as an expense category
allowing payment-plan-backed debts to be paid independently from the Debts tab
showing two unlabeled progress percentages for the same linked obligation
hard-deleting debt chains with wallet/goal/asset dependencies
```

### Execution Order

Recommended order:

```text
1. Stabilize debt ledger as source of truth.
2. Add origin_kind / counterparty_kind / product_kind to debts and demote is_money_transferred to compatibility/derived behavior.
3. Fix payment principal/charge split and create the correct expense/income events for paid charges.
4. Add deferred-expense category/subcategory/project fields.
5. Refactor split-with-friends to use SPLIT_REIMBURSEMENT and one shared ledger-writing service.
6. Add formal loan details table.
7. Add multi-wallet debt transaction allocations.
8. Link installment plans to an underlying debt.
9. Convert installment remaining balance and progress display to debt-backed truth or one clearly labeled plan-progress definition.
10. Add partial and advance installment payment allocation model.
11. Add payment_plan_type metadata and category suggestions.
12. Expand frequency support and make generated schedule rows the due-date truth.
13. Enforce action ownership: payment-plan-backed debts are managed from Payment Plans, not independent Debts actions.
14. Expose Bank Fees & Interest and Debt Charges bidirectionally with service guardrails.
15. Add repair/reconciliation for old payments made directly against installment-linked debts.
16. Add asset/collateral settlement flows.
17. Add debt detail/storyline UI backed by debt_ledger_entries.
18. Add guided creation UX with formal-debt schedule guardrails.
```

### Final Rule

```text
Loans are not a separate financial universe.
Loans are formal I-owe debts with optional metadata and stricter lifecycle language.

Installments are not a separate financial truth system.
Installments are purchase contracts and schedules attached to an underlying debt.

DebtLedgerEntry is the lifecycle spine.
FinancialEvent exists only when real wallet/income/expense movement happens.
Manual bank-statement-confirmed values are more trustworthy than premature calculation engines.
```

## EC-040 - Damage Or Loss Can Create A Debt

### Discovery

Some debts are created because property was damaged, lost, or destroyed.

This is not borrowed money, unpaid income, or "someone paid for me".

Real-world personal examples:

```text
I broke my friend's phone.
My friend says I owe 2M for repair/replacement.
```

```text
Someone scratched my laptop.
They owe me 1.5M compensation.
```

Real-world formal examples:

```text
I damaged a rental car.
The rental company says I owe 5M for the damage.
```

```text
An event guest damaged venue equipment.
The venue/company owes or charges compensation under a formal agreement.
```

```text
A courier company damaged my tracked item.
The company owes compensation for the loss.
```

### Modeling Decision

Add a debt origin:

```text
DAMAGE_COMPENSATION
```

Use it for both personal and formal relationships.

For `I owe someone`:

```text
Creation:
  DebtLedger INITIAL only
  No wallet movement today
  Category required because the future payment is an expense

Payment:
  EXPENSE / damage-compensation context
  Category = the real life area, such as Electronics, Transport, Home, Other, etc.
```

For `Someone owes me`:

```text
Creation:
  DebtLedger INITIAL only
  No wallet movement today
  No income source required

Payment received:
  DEBT_SETTLEMENT / damage-compensation context
  Not normal income
```

Reason:

```text
Compensation restores damaged value.
It should not inflate income analytics.
```

### UI Decision

Debt creation Step 3 should include:

```text
I owe someone:
  I damaged or lost something

Someone owes me:
  They damaged or lost something of mine
```

For formal relationship, the same option is valid:

```text
I damaged company/rental/provider property
Company/client/provider damaged my property
```

Keep the wording natural. Do not show enum names.

### Asset Bridge - Deferred

If the damaged item is tracked in Assets, future work can create a bridge:

```text
Asset -> Record damage claim -> Debt created
Debt -> linked damaged asset
Asset condition/status -> DAMAGED
```

Do not build the bridge now.

Possible future model:

```text
asset_incidents
- asset_id
- type: DAMAGE | LOSS | THEFT
- estimated_loss_amount
- repair_cost
- linked_debt_id
- status: open | repaired | settled
```

For now:

```text
Implement DAMAGE_COMPENSATION debt origin.
Do not implement asset status/condition changes yet.
```

### Progress Bar Bug

Current problem:

```text
Debt creation and payment-plan creation progress bars show the grey track,
but the filled progress is invisible.
```

Likely cause:

```text
Shared Progress component has no default indicator background.
Only places that pass indicatorClassName render correctly.
```

Fix:

```text
Progress indicator should default to bg-primary.
Callers can still override with indicatorClassName.
```

### Derived Payment Amounts

Debt and payment-plan payment forms should follow the same rule as debt creation:

```text
Ask wallet rows first.
Derive payment amount from the wallet row totals.
Show total payment amount as read-only.
```

Why:

```text
The user knows what came from each wallet.
The total should be computed by Sarflog.
This avoids mismatch between "total amount" and wallet allocation rows.
```

Apply this to:

```text
Debt Record Payment
Payment Plan Record Payment
Formal settlement payment amount should later follow the same pattern too,
with discount/write-down handled separately.
```

### Implementation Notes

- [x] Add `DAMAGE_COMPENSATION` to debt origin enum and migration.
- [x] Add debt creation UI options for personal and formal damage/loss.
- [x] For I-owe damage, require category.
- [x] For owed-to-me damage, do not require income source and do not post payment as income.
- [x] Fix shared progress component indicator color.
- [x] Derive Record Payment amount from wallet rows in debts.
- [x] Derive Record Payment amount from wallet rows in payment plans.
- [ ] Leave Asset -> Debt damage bridge for later.

## EC-041 - Credit Cards And Overdraft Wallets Should Appear As Wallet-Backed Obligations

### Problem

Credit cards and debit cards with overdraft can create real liabilities:

```text
Credit Card Wallet: -3M
Debit Overdraft Wallet: -700k
```

These feel like debts to the user and should be visible from the Debts / Obligations area.

But they should not be duplicated as normal `Debt` rows, because their source of truth is the wallet ledger.

### Decision

Model these as projected wallet-backed obligations:

```text
Wallet is the source of truth.
Debts / Obligations page displays the liability.
Repayment reuses wallet transfer logic.
```

Do not allow normal debt actions:

```text
No delete debt
No edit debt amount
No forgive balance
No formal settlement
No archive as normal debt
```

Allowed actions:

```text
Pay credit card
Cover overdraft
View wallet transactions
Add fee / interest
Correct wallet balance
```

### Real-World Examples

Credit card repayment:

```text
Credit card balance: -3M
Savings wallet: 5M

User pays 1M from Savings.

Wallet transfer:
Savings -1M
Credit Card +1M

Credit card liability becomes 2M.
```

This is not a new expense. The expense happened when the credit card was used.

Overdraft cover:

```text
Debit wallet balance: -700k
Cash wallet: 1M

User covers 700k from Cash.

Wallet transfer:
Cash -700k
Debit +700k

Debit overdraft becomes 0.
```

This is not a new expense. It is liability reduction.

### Backend Shape

Use shared wallet transfer logic, but expose intent-specific actions:

```text
Wallets page wording:
Transfer money

Debts page wording:
Pay credit card
Cover overdraft
```

Possible reference types:

```text
CREDIT_REPAYMENT
OVERDRAFT_REPAYMENT
```

These references make database inspection clearer than a generic transfer reference.

### Implementation Notes

- [ ] Add projected wallet-backed obligation cards to Debts / Obligations page.
- [ ] Reuse wallet transfer service for credit repayment and overdraft cover.
- [ ] Include transfer fee support through the same fee path used by wallet transfers.
- [ ] Block normal Debt CRUD/actions for projected wallet obligations.
- [ ] Add backend tests proving repayment is transfer/liability reduction, not expense.

## EC-042 - Wallet Transaction History Modal

### Problem

Wallets now participate in many flows:

```text
expenses
income
transfers
goal allocation
goal return
goal consumption
credit repayment
overdraft cover
fees
refunds
adjustments
debt payments
payment plan payments
```

Users need a clean way to inspect what happened inside a specific wallet without opening every feature page.

### Decision

Add a wallet transactions modal or drawer from each wallet card:

```text
Wallet -> View transactions
```

The modal should use wallet ledger as the source of truth and simplify display into:

```text
Inflow  = green
Outflow = red
Neutral/adjustment context shown by label
```

Do not expose raw enum-heavy language in the main row.

### UX Shape

Each row should answer:

```text
What happened?
How much entered or left this wallet?
When?
Which feature caused it?
```

Example rows:

```text
Laptop purchase              -8M     Outflow   Goal-funded purchase
Salary                       +12M    Inflow    Income
Transfer to Cash             -500k   Outflow   Wallet transfer
Credit card repayment        +1M     Inflow    Liability repayment
Bank fee                     -20k    Outflow   Fee
Goal reserve for Camera       0      Label moved, no wallet balance change
```

Important nuance:

```text
Goal allocation labels money but does not move wallet balance.
If wallet ledger has no money movement, show it as protected-label activity separately or omit it from pure balance transaction rows.
```

### Senior Take

This is a high-value UX feature because it builds user trust:

```text
Wallet balance is easier to audit.
Users can understand why balance changed.
Support/debugging becomes easier.
```

But it should not become a full accounting journal UI. Keep the first version simple:

```text
date
title
context label
amount signed for this wallet
balance after if available later
link/open related detail
```

### Implementation Notes

- [ ] Build wallet transaction modal/drawer from wallet card.
- [ ] Query wallet ledger entries for one wallet.
- [ ] Display signed wallet amount as green inflow / red outflow.
- [ ] Use friendly labels derived from event type and reference type.
- [ ] Add filters later: all / inflow / outflow / fees / transfers / expenses.
- [ ] Consider showing wallet balance after each row if ledger supports it or can compute it reliably.

## EC-043 - Pay Obligation Goals For Unscheduled I-Owe Debts

**Status:** NEW  
**Severity:** S1  
**Area:** Goals / Savings / Debts / Obligations / Wallets / API / UI  
**Discovered on:** 2026-06-04  
**Reported by:** User / AI Agent  

### Scenario

User has an unscheduled debt they owe to someone and wants to save toward it from the Goals page.

Example:

```text
Ali owes his friend 500k because the friend lent him money.

Ali creates a goal:
Intent: Pay obligation
Linked debt: Friend debt
Goal creation wording: Save for this debt
```

Ali may not save and pay the whole 500k at once.

Real sequence:

```text
Month 1:
Ali saves 200k from Debit A.
Next day, Ali pays 200k to his friend.
Debt remaining becomes 300k.
Goal consumes 200k linked to the debt payment.

Month 2:
Ali saves 300k from Debit B.
Next day, Ali pays 300k to his friend.
Debt remaining becomes 0.
Goal consumes 300k linked to the debt payment.
Debt is closed.
Goal is completed.
```

Another valid real sequence:

```text
Debt: 500k

Month 1:
Create a 100k partial payoff goal.
Save 100k.
Pay 100k.
Goal completes.

Month 2:
Create another 100k partial payoff goal for the same debt.
Save 100k.
Pay 100k.
Goal completes.
```

This is sequential payoff tracking, not five active goals competing against one debt.

### Steps to Reproduce

1. Create an `I owe` unscheduled debt for 500k.
2. Create a Goal with intent `PAY_OBLIGATION` linked to that debt.
3. Fund only part of the goal.
4. Record a partial debt payment using the saved goal money.
5. Later fund more money and record another debt payment.
6. Add a debt forgiveness or charge while a linked goal exists.

### Expected Behavior

Goal creation must use saving language:

```text
How much do you want to save for this debt?
```

Allowed creation choices:

```text
Save for the full remaining debt
Save a fixed amount toward this debt
```

The Goals page may drive the user flow:

```text
Goal page -> Prepare payment if needed -> Record debt payment using saved money
```

But the Debt service remains the source of truth for the actual payment:

```text
DebtLedgerEntry owns debt balance lifecycle.
DebtTransaction owns the debt payment record.
FinancialEvent / WalletLedger own real wallet movement.
GoalContributions only record that protected goal money was consumed for that payment.
```

For `PAY_OBLIGATION` goals, reaching 100% saved must not complete the goal by itself.

Correct states:

```text
Saved target reached -> Ready to pay
Saved money used in real debt payment -> Completed or partially consumed
Linked debt fully paid -> Full-balance goal completed
Fixed amount paid -> Fixed-amount goal completed
```

Only `I owe` debts should be supported for this intent. `Someone owes me` receivables are expected inflows, not savings goals.

For initial scope, this entry is about unscheduled debts only. Payment-plan-backed obligations have schedule ownership and should be handled separately.

### Actual Behavior

Current Goals UI already has the `PAY_OBLIGATION` intent label, but the action only navigates toward debts and does not define the domain behavior.

There is no explicit backend bridge that:

```text
validates a linked obligation goal
prepares payment wallets when saved money is in a different wallet
records the real debt payment through the debt service
consumes goal funding linked to the debt payment event
keeps goal completion based on payment, not only saving
```

### Why This Matters

If the goal is allowed to mutate debt balance directly, the app creates duplicate financial truth.

If the goal completes when it is merely funded, the user sees a paid-looking goal even though the friend has not received money.

If multiple active goals for one debt are allowed without ordering, forgiveness, charges, and outside payments create ambiguous target changes.

The core distinction must stay clear:

```text
Goal creation = save / protect / fund
Debt action = pay / record payment / reduce balance
Goal consumption = saved money was used for that debt payment
```

### Affected Modules

- Goals
- Savings
- Debts
- Wallets
- Debt Ledger
- Financial Events
- Goal Funding Service
- Obligations UI
- API Validation

### Related Invariants

- Wallet balances must follow wallet rules.
- Drafts are not final financial truth.
- Finalized expenses affect real financial records.
- Allocations/goals do not physically move wallet money unless a real transfer exists.
- Loan received is borrowed inflow, not earned income.
- DebtLedgerEntry is the lifecycle spine for debts.
- FinancialEvent exists only when real wallet/income/expense movement happens.

### Decision

Fix when implementing Goals -> Pay Obligation.

Domain decisions:

```text
1. PAY_OBLIGATION goals support only DebtType.OWING for now.
2. Start with unscheduled debts, not payment-plan-managed debts.
3. Goal creation must use "save" language, not "pay" language.
4. The user chooses a coverage mode:
   - SAVE_FULL_REMAINING_DEBT
   - SAVE_FIXED_AMOUNT_TOWARD_DEBT
5. For one linked debt, allow only one ACTIVE PAY_OBLIGATION goal at a time.
6. Allow multiple historical completed PAY_OBLIGATION goals for the same debt.
7. A second linked partial debt goal can be created only after the previous linked goal is paid/completed or archived/released.
8. Goal funding completion means "ready to pay", not "completed".
9. Goal completion requires saved money to be used in a real debt payment.
10. Debt payment must be recorded by the debt payment service.
11. Goal consumption must link to the debt payment financial event.
```

Sequential split tracking rule:

```text
Do not model five active 100k goals for one 500k debt.

Model:
one active 100k goal
pay it
complete it
then allow another active 100k goal
```

### Proposed Fix

Add Pay Obligation goal behavior around existing goal/debt links:

```text
Goals.linked_debt_id
Goals.intent = PAY_OBLIGATION
Goal coverage mode = full remaining debt or fixed amount
```

Suggested backend behavior:

```text
POST /goals/{goal_id}/pay-obligation

Validate:
- goal belongs to user
- goal.intent == PAY_OBLIGATION
- goal.linked_debt_id is present
- linked debt is DebtType.OWING
- linked debt is unscheduled / not payment-plan-managed
- goal has enough unreleased saved amount for requested goal-funded payment
- payment amount does not exceed debt remaining amount
- payment wallets are valid and active

Then:
- if saved goal money is not already in the payment wallet, require or perform explicit payment preparation transfer
- call the debt payment service to create DebtTransaction, DebtLedgerEntry, FinancialEvent, WalletLedger
- create GoalContributions CONSUME rows for the amount covered by saved goal funding
- link consumed goal entries to the debt payment event
- reconcile debt
- update goal state
```

Payment preparation rule:

```text
If goal funding wallet differs from payment wallet:
1. Prepare payment first with a real wallet transfer, or
2. Use a confirmed reimbursement-style settlement after payment.

Do not silently pretend protected goal money paid from a different wallet.
```

Completion rules:

```text
SAVE_FULL_REMAINING_DEBT:
- target follows linked debt remaining balance
- goal completes when linked debt remaining amount is 0 and saved goal money used for payments has been consumed

SAVE_FIXED_AMOUNT_TOWARD_DEBT:
- target is the user's chosen fixed amount
- goal completes when that fixed amount has been saved and used in real debt payment(s)
- target must never exceed linked debt remaining amount
```

Forgiveness rules:

```text
Full-balance goal:
- reduce target when debt is forgiven
- if saved/protected amount now exceeds needed amount, ask user to release or move the extra saved money

Fixed-amount goal:
- do not change target if debt remaining still covers the fixed goal target
- cap target if debt remaining becomes smaller than the unpaid fixed goal target
- if saved/protected amount now exceeds needed amount, ask user to release or move the extra saved money

Completed historical goals:
- do not mutate completed goals when later forgiveness happens
- future goal options use the new debt remaining amount
```

Charge rules:

```text
Full-balance goal:
- increase target when a new charge increases debt remaining balance

Fixed-amount goal:
- do not auto-increase target
- show that this goal covers only the chosen amount toward the larger debt

Completed historical goals:
- do not mutate completed goals when later charges happen
- future goal options use the new debt remaining amount
```

### UX Copy / Error Message

Goal creation:

```text
How much do you want to save for this debt?
```

Options:

```text
Save for the full remaining debt
Save a fixed amount toward this debt
```

Goal funded state:

```text
Saved and ready to pay
```

Payment action:

```text
Record debt payment using saved money
```

Payment preparation:

```text
Your saved money is in a different wallet. Prepare the payment wallet first.
```

One-active-goal guard:

```text
This debt already has an active savings goal. Complete, archive, or release that goal before creating another one for this debt.
```

Wrong debt type:

```text
Pay obligation goals are only for debts you owe. Money owed to you is an expected inflow, not a savings goal.
```

Over-target:

```text
This goal amount is higher than the remaining debt.
```

Forgiveness/excess saved money:

```text
This debt was reduced. You saved more than is now needed. Release the extra money or move it to another goal.
```

Charge notification:

```text
This debt increased. Your current savings goal still covers the amount you chose.
```

### Test Cases Needed

- [ ] API integration test: create `PAY_OBLIGATION` goal linked to `DebtType.OWING` unscheduled debt.
- [ ] API integration test: reject `PAY_OBLIGATION` goal linked to `DebtType.OWED`.
- [ ] API integration test: reject `PAY_OBLIGATION` goal linked to payment-plan-managed debt for this scope.
- [ ] API integration test: reject second active `PAY_OBLIGATION` goal for the same debt.
- [ ] API integration test: allow new linked partial goal after previous linked goal is paid/completed.
- [ ] API integration test: funding a debt goal to target does not mark it completed.
- [ ] API integration test: goal-funded partial debt payment creates debt transaction and consumes matching goal funding.
- [ ] API integration test: split debt payoff across multiple payments keeps full-balance goal active until debt reaches zero.
- [ ] API integration test: fixed-amount goal completes after fixed saved amount is paid toward debt.
- [ ] API integration test: full-balance goal target reduces after forgiveness.
- [ ] API integration test: fixed-amount goal target is unchanged after forgiveness if remaining debt still covers it.
- [ ] API integration test: fixed-amount goal target is capped after forgiveness if remaining debt becomes smaller than unpaid goal target.
- [ ] API integration test: full-balance goal target increases after debt charge.
- [ ] API integration test: fixed-amount goal target does not auto-increase after debt charge.
- [ ] API integration test: excess saved money after forgiveness requires release/move resolution.
- [ ] API integration test: payment wallet differs from funding wallet requires explicit preparation/settlement.
- [ ] API integration test: reversing/deleting a goal-funded debt payment reverses or blocks the linked goal consume effect.
- [ ] UI manual check: goal creation uses "save" language.
- [ ] UI manual check: funded obligation goal says "ready to pay", not "completed".
- [ ] UI manual check: Goals page can launch record debt payment using saved money.
- [ ] UI manual check: one-active-goal guard is understandable.

### Final Resolution

Not implemented yet.

### Notes

Do not touch wallet-backed obligations from EC-041 in this work. Credit cards and overdrafts are deferred until after the multicurrency layer.

Do not treat `PAY_OBLIGATION` as a planned purchase clone.

Important product language boundary:

```text
Goal creation = save
Goal funding = protected saved money
Debt payment = pay
Goal consume = saved money was used
```

Recommended mental model:

```text
one active savings intention per debt
many completed payoff milestones over time
one debt ledger truth
```

## EC-044 - Goal Creation Should Be A Guided Intent-First Flow

**Status:** NEW  
**Severity:** S2  
**Area:** Goals / Savings / UI / API Validation / UX Copy  
**Discovered on:** 2026-06-04  
**Reported by:** User / AI Agent  

### Scenario

User opens the Goals / Savings page and wants to create a new goal.

Current goal creation is a compact form:

```text
Name
Target
Intent
Target date
```

This was acceptable when goals were generic savings buckets, but goals now have different domain meanings:

```text
RESERVE = keep money protected
PLANNED_PURCHASE = save for one purchase lifecycle
PAY_OBLIGATION = save toward an I-owe debt
FUND_PROJECT = save toward a larger project/mission
```

The intent changes what the target means, what links are needed, how completion works, and which later actions are valid.

### Steps to Reproduce

1. Go to Goals / Savings page.
2. Use the current Create Goal card.
3. Enter a target amount before choosing or understanding the goal intent.
4. Choose `Pay obligation`, `Reserve`, `Planned purchase`, or `Fund project`.
5. Notice that the form still asks the same fields with generic wording.

### Expected Behavior

Goal creation should be a guided, question-based flow similar to debt and payment-plan creation.

Primary rule:

```text
Ask intent first.
Then ask only fields that matter for that intent.
Never make the user translate domain rules manually.
```

Recommended first step:

```text
What are you saving for?
```

Options:

```text
Keep money reserved
Buy something
Pay a debt
Fund a project
```

Branch examples:

```text
Keep money reserved:
- Ask what kind of reserve this is.
- Ask how much the user wants to keep protected.
- Ask when they want it ready, if relevant.

Buy something:
- Ask what the user is planning to buy.
- Ask target amount.
- Ask whether this may become an asset only when relevant.

Pay a debt:
- Show only unscheduled DebtType.OWING debts.
- Ask which debt the user is saving for.
- Ask "How much do you want to save for this debt?"
- Choices: save for full remaining debt or save a fixed amount.

Fund a project:
- Ask whether this should link to an existing project or start from a project idea.
- Ask the project funding target.
```

Goal creation must remain separate from goal funding.

Correct boundary:

```text
Goal creation = define intention
Goal funding = protect real wallet money
```

After creating a goal, do not force the funding dialog. Instead, show subtle guidance:

```text
Goal created. Reserve money when you are ready.
```

The UI may highlight the new goal's fund/reserve button briefly, but should not interrupt the user with a mandatory second modal.

### Actual Behavior

Current UI creates goals from a static sidebar/card form and does not branch by intent.

It asks for a target before establishing the goal meaning.

It does not yet guide `PAY_OBLIGATION` into debt selection or full-vs-fixed saving mode.

It does not explain that funding stays separate from creation.

### Why This Matters

Goals are now financial intentions with different lifecycle rules.

Bad goal creation UX creates downstream confusion:

```text
Reserve goals should not behave like completed purchase goals.
Pay obligation goals should not complete when merely funded.
Planned purchase goals complete through a real purchase event.
Fund project goals may graduate or release into project budgeting.
```

If users create the wrong goal shape, later wallet protection, completion, payment, and reporting behavior becomes confusing.

### Affected Modules

- Goals
- Savings page
- Goal creation UI
- Goal validation
- Goal links to debts/assets/projects
- Translations / UX copy

### Related Invariants

- Allocations/goals do not physically move wallet money unless a real transfer exists.
- Project planned amount and funded amount are different.
- Drafts are not final financial truth.
- Finalized expenses affect real financial records.
- DebtLedgerEntry is the lifecycle spine for debts.

### Decision

Rebuild goal creation as a guided intent-first dialog.

Decisions captured:

```text
1. Goal creation should be question-led like Debts and Payment Plans.
2. Step 1 asks "What are you saving for?"
3. Intent decides the remaining questions.
4. Goal creation must not ask wallet funding fields.
5. Funding remains a separate explicit action after the goal exists.
6. After creation, show subtle non-blocking guidance to reserve money.
7. Do not auto-open the funding dialog after creation.
8. Do not force the user to choose wallets during creation.
```

Recommended post-create behavior:

```text
Create goal
Close dialog
Show the new goal in the list
Briefly highlight the Reserve/Fund button
Show a small hint: "Goal created. Reserve money when you are ready."
```

Avoid:

```text
forced second modal
auto-opening funding dialog
blocking toast that demands action
wallet selection during goal creation
```

### Proposed Fix

Replace the static Create Goal card with a guided dialog.

Suggested generic steps:

```text
1. What are you saving for?
2. Intent-specific details
3. How much do you want to save?
4. When do you want it ready?
5. Review before creating
```

The target amount step must be intent-aware:

```text
Reserve:
  user enters target amount

Planned purchase:
  user enters expected purchase amount

Pay obligation:
  full remaining debt -> target derives from linked debt
  fixed amount -> user enters amount capped by debt remaining

Fund project:
  target is project funding target, not necessarily total project spending
```

### UX Copy / Error Message

Opening question:

```text
What are you saving for?
```

Post-create hint:

```text
Goal created. Reserve money when you are ready.
```

Creation/funding boundary:

```text
This creates the goal only. You can reserve wallet money after it exists.
```

Intent copy:

```text
Keep money reserved - Protect money for later use.
Buy something - Save for one specific purchase.
Pay a debt - Save toward a debt you owe.
Fund a project - Save for a larger mission with multiple costs.
```

### Test Cases Needed

- [ ] UI manual check: Create Goal opens guided dialog, not static sidebar form.
- [ ] UI manual check: Step 1 asks "What are you saving for?"
- [ ] UI manual check: intent branch asks only relevant fields.
- [ ] UI manual check: Reserve branch does not ask debt/project/purchase-only fields.
- [ ] UI manual check: Pay debt branch shows only eligible unscheduled I-owe debts.
- [ ] UI manual check: goal creation does not ask wallet funding rows.
- [ ] UI manual check: after creation, funding dialog is not forced open.
- [ ] UI manual check: new goal appears and fund/reserve action is subtly highlighted or hinted.
- [ ] API integration test: goal creation still validates linked records for intent-specific links.
- [ ] Regression test: existing goal list, funding, archive, restore, and delete actions still work.

### Final Resolution

Not implemented yet.

### Notes

Do not conflate guided goal creation with goal funding.

Goal creation should define the user's intention. Funding remains an explicit later act of protecting wallet money.

---

## EC-045 - Debt Savings Goals Need Backend-Owned Payment Rules

**Status:** FIXED  
**Severity:** S1  
**Area:** Goals / Debts / API  
**Discovered on:** 2026-06-04  
**Reported by:** User / AI Agent  

### Scenario

Ali owes a friend 500k.

He creates a savings goal for that debt, reserves 200k, pays 200k, then later reserves and pays the remaining 300k.

The system must treat these as real debt payments, not just savings progress.

Debt savings can be:

```text
Full remaining debt - goal follows the whole debt balance.
Fixed debt amount - goal tracks one partial payment target.
```

Debt balance can also change after the goal exists:

```text
Friend forgives 50k.
Friend adds a 100k charge.
Ali pays part of the debt outside the goal.
Debt payment is reversed or corrected.
```

### Steps to Reproduce

1. Create an active I-owe debt.
2. Create a Pay Obligation goal linked to that debt.
3. Reserve wallet money for the goal.
4. Record an actual debt payment from the goal.
5. Add charges, forgiveness, or outside debt payments.

### Expected Behavior

Backend must own the financial invariants.

Expected rules:

```text
Pay Obligation goals must link to an I-owe debt.
Debt must be open and have remaining balance.
Debt must not be managed by a payment plan.
Goal amount must not exceed the payable debt amount.
Only one active debt-savings goal can exist for the same debt.
Funding alone must not complete the goal.
Actual debt payment through the goal consumes reserved goal money and reduces debt balance.
Full-tracking goals follow charge, forgiveness, payment, reversal, and balance-correction changes.
Fixed-tracking goals stay fixed unless the debt can no longer support that target.
```

### Actual Behavior

Before the fix, the frontend guided users into a linked debt goal, but the backend only checked that the linked debt record existed.

Missing backend rules:

```text
No backend distinction between full debt tracking and fixed partial tracking.
No backend one-active-goal-per-debt invariant.
No goal-owned action to record the real debt payment.
Funding could look complete while the debt was still unpaid.
Debt charge/forgiveness changes did not adjust debt goal targets.
```

### Why This Matters

This is financial truth, not UI preference.

A user can call the API directly, submit from a stale tab, or hit another future UI path. If the backend does not enforce the invariant, debt goals can become inconsistent with debt balances.

The key boundary:

```text
Goal funding = reserved wallet money
Debt payment = real-world obligation reduced
```

Those must happen together only when the user actually makes the debt payment.

### Affected Modules

- Goals
- Debts
- Debt ledger
- Goal funding
- Wallet protection
- API schemas
- Alembic migrations
- Savings UI actions

### Related Invariants

- Wallet balances must follow wallet rules.
- Allocations/goals do not physically move wallet money unless a real transfer exists.
- DebtLedgerEntry is the lifecycle spine for debts.
- Goal funding must not be confused with real-world completion.
- One active partial debt goal per debt avoids overlapping payment targets.

### Decision

Backend must own the Pay Obligation goal rules.

Implementation decisions:

```text
1. Add debt_goal_tracking_mode to goals.
2. Supported modes are FULL_REMAINING_DEBT and FIXED_DEBT_AMOUNT.
3. Add linked_debt_transaction_id as the real-world completion anchor for debt goals.
4. Add backend validation for Pay Obligation goal creation/update.
5. Add a partial unique index: one active Pay Obligation goal per linked debt.
6. Add POST /goals/{goal_id}/pay-debt.
7. The endpoint records a real debt payment and consumes goal money in one transaction.
8. Debt payment logic lives in a debt payment service so debt ledger behavior stays centralized.
9. Full debt goals sync target amount after charges, forgiveness, outside payments, reversals, and balance adjustments.
10. Fixed debt goals do not grow with new charges; they only shrink if the debt can no longer support the fixed target.
```

### Proposed Fix

Backend changes:

```text
Models:
- DebtGoalTrackingMode enum
- goals.debt_goal_tracking_mode
- goals.linked_debt_transaction_id

Validation:
- Pay Obligation requires linked debt
- linked debt must be I-owe, open, unscheduled, and payable
- amount cannot exceed remaining debt
- duplicate active goal for same debt is blocked

Payment:
- POST /goals/{goal_id}/pay-debt
- validates reserved goal money exists in payment wallets
- records debt payment
- consumes goal funding
- reconciles debt balance
- completes goal only after actual debt payment covers the goal target

Sync:
- Full debt goal target = amount already paid through this goal + current remaining debt
- Fixed debt goal target stays fixed unless current debt balance makes it impossible
```

### UX Copy / Error Message

Natural UI actions should be:

```text
Reserve money
Prepare payment
Make payment
Unreserve
Archive
```

Avoid:

```text
Open debt
Pay obligation
backend field names
code-like labels
```

Backend error concepts:

```text
This debt already has an open savings goal.
Choose a debt you owe.
Choose an open debt with money left to pay.
This debt is managed by a payment plan.
This amount is higher than what can still be paid for this goal.
```

### Test Cases Needed

- [x] API test: full Pay Obligation goal infers FULL_REMAINING_DEBT.
- [x] API test: fixed Pay Obligation goal infers FIXED_DEBT_AMOUNT.
- [x] API test: duplicate active debt goal is rejected.
- [x] API test: goal debt payment consumes reserved goal money.
- [x] API test: goal debt payment reduces debt remaining amount.
- [x] API test: fixed debt goal completes after target payment.
- [x] API test: full debt goal target increases after a debt charge.
- [x] API test: full debt goal target decreases after debt forgiveness.
- [x] API test: Pay Obligation rejects owed-to-me debts.
- [x] API test: Pay Obligation rejects payment-plan-managed debts.
- [x] API test: full debt goal target syncs after reversal.
- [ ] UI manual check: debt goal card shows Prepare payment / Make payment, not Open debt.

### Final Resolution

Backend implementation added.

Verified in Docker:

```text
docker compose run --rm api pytest -q tests/test_goals.py::test_pay_obligation_goal_creation_validates_debt_and_duplicate_open_goal tests/test_goals.py::test_pay_obligation_goal_payment_consumes_goal_money_and_reduces_debt tests/test_goals.py::test_full_pay_obligation_goal_target_tracks_debt_charges_and_forgiveness

3 passed

docker compose run --rm api pytest -q tests/test_goals.py tests/test_debts.py tests/test_debt_action_routes.py tests/test_debt_policy.py

82 passed

docker compose run --rm api python -m alembic heads

e7b9c2d4a6f1 (head)

docker compose run --rm api python -m alembic upgrade head

applied a8d9c2e7f104 -> e7b9c2d4a6f1
```

Frontend action wiring still needs to replace the current `Open debt` action with `Prepare payment` and `Make payment` on debt savings goal cards.

### Notes

Do not treat 100 percent funded as debt-goal completion.

For debt goals, completion means the target amount was actually paid through the debt payment workflow, or the linked debt was closed.

---

## EC-046 - Planned Purchase Down Payment Should Bridge Into Payment Plan

**Status:** FIXED  
**Severity:** S2  
**Area:** Goals / Planned Purchase / Installments / Debts / UI / API  
**Discovered on:** 2026-06-06  
**Reported by:** User / AI Agent  

### Scenario

Ali wants to buy a laptop on installments.

Before checkout, Ali does not owe the store yet. He only needs to save the required down payment.

```text
Laptop total price: 10,000,000 UZS
Down payment needed today: 2,000,000 UZS
Remaining balance: 8,000,000 UZS over 8 months
```

Ali creates a planned purchase goal:

```text
Goal: Laptop down payment
Intent: Planned purchase
Target: 2,000,000 UZS
```

When Ali records the real purchase, Sarflog should ask whether the remaining balance became a payment plan.

### Steps to Reproduce

1. Create a Planned Purchase goal for a down payment.
2. Reserve the down payment amount.
3. Record the purchase.
4. User says the remaining balance is paid on installments.
5. User enters the full purchase price and schedule.

### Expected Behavior

Sarflog should complete the original planned purchase goal and create the new payment plan in the same transaction.

Expected flow:

```text
1. Record the down payment as the real purchase event.
2. Consume the reserved planned-purchase goal money.
3. Create an InstallmentPlan for the full purchase price.
4. Create the linked I-owe debt for the remaining balance.
5. Link the down payment event to the installment plan.
6. Optionally create a new Pay Obligation goal for the next scheduled payment.
```

The user should experience this as one guided continuation:

```text
You bought it.
The rest is now a payment plan.
Do you want to start saving for the next payment?
```

### Actual Behavior

Without this bridge, the user must manually leave the planned purchase flow, create a payment plan separately, then create a new Pay Obligation goal separately.

That is mechanically possible but emotionally wrong: the app does not follow the user's real-world story.

### Why This Matters

This feature makes the app feel more alive because it follows the user's actual financial sequence:

```text
Saving before checkout -> purchase happens -> obligation now exists -> save for next payment
```

The old goal should not be literally converted into a debt goal. It already did its job: preparing the down payment.

The cleaner model is:

```text
Completed Planned Purchase goal
        |
        v
New InstallmentPlan and linked debt
        |
        v
Optional new Pay Obligation goal for the next payment
```

### Affected Modules

- Goals
- Planned purchase flow
- Installments
- Debt ledger
- Goal funding
- Wallet ledger
- Savings UI

### Related Invariants

- Wallet balances must follow wallet rules.
- Finalized expenses affect real financial records.
- Allocations/goals do not physically move wallet money unless a real transfer exists.
- Goal funding must not be confused with real-world completion.
- Debt should exist only after the user actually takes on the obligation.

### Decision

Fix now for the down-payment bridge.

Implement only the practical v1:

```text
Planned purchase down payment -> new installment plan -> optional next-payment goal
```

Defer full-installment reserve behavior for later.

### Proposed Fix

Backend:

```text
- Extend planned purchase record payload with optional installment-plan details.
- Require full purchase price to be higher than the down payment.
- Create the down payment expense once, not twice.
- Create the installment plan in the same DB transaction.
- Link the existing down payment event to the installment plan.
- Create the payment-plan-managed debt for the remaining balance.
- Optionally create a Pay Obligation goal targeting the first unpaid installment.
```

Frontend:

```text
- Add a guided step in Record purchase: Did the rest become a payment plan?
- If yes, collect full price, store/lender name, months, frequency, and next-goal preference.
- Keep all copy human: no model or database words.
```

### UX Copy / Error Message

Suggested UI copy:

```text
Did you pay the rest over time?
```

```text
Sarflog will record today's down payment and create the monthly payment plan for what is left.
```

Backend error concepts:

```text
The full purchase price must be higher than today's payment.
Choose at least one future payment.
This type of loan should be created from Payment plans.
```

### Test Cases Needed

- [x] API integration test: planned purchase down payment creates installment plan.
- [x] API integration test: down payment event is not duplicated.
- [x] API integration test: linked debt equals full price minus down payment.
- [x] API integration test: optional next Pay Obligation goal targets first unpaid installment.
- [x] API integration test: total price equal to down payment is rejected.
- [x] Frontend build check.
- [ ] UI manual check: guided purchase flow stays readable on mobile.

### Final Resolution

Implemented.

Backend changes:

```text
- Planned purchase record-purchase payload accepts optional payment-plan details.
- The down payment expense is created once by the goal purchase flow.
- The new InstallmentPlan is created in the same transaction.
- The existing down payment event is linked to the new payment plan.
- The linked I-owe debt is created for the remaining balance.
- Optional next-payment Pay Obligation goal is created automatically.
```

Frontend changes:

```text
- Record purchase flow now asks whether the rest will be paid over time.
- If yes, the user enters full price, store/lender, payment count, frequency, and whether to create a next-payment goal.
```

Verified:

```text
python -m compileall app
docker compose exec -T api pytest -q tests/test_goals.py::test_planned_purchase_down_payment_creates_installment_plan_and_next_goal tests/test_goals.py::test_planned_purchase_installment_bridge_rejects_total_not_above_down_payment
docker compose exec -T api pytest -q tests/test_goals.py tests/test_installment_routes.py
npm.cmd run build
```

### Notes

Do not call this a literal goal conversion in backend code.

The UI may say "continue saving for monthly payments", but the domain should create a new goal so the original planned purchase history stays clean.


## EC-047 - Regular Debt CRUD Must Not Bypass Explicit Debt Actions

**Status:** DESIGN_CONFIRMED  
**Severity:** S0  
**Area:** Debts / API / UI / Ledger  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

User creates a regular I-owe debt, then later records payments, charges, forgiveness, settlement, or balance corrections.

After that history exists, generic edit/delete operations can become dangerous:

```text
Debt opened: 500k
Payment recorded: 200k
Remaining: 300k
User edits initial amount to 450k
```

The system may be able to recompute a number, but the real-world meaning becomes unclear:

```text
Was the opening amount wrong?
Did the lender forgive 50k?
Was this a balance correction?
Was a payment recorded incorrectly?
```

### Steps to Reproduce

1. Create a regular debt.
2. Record any real debt activity after creation.
3. Try to edit opening amount, status, category, classification, or delete the debt.

### Expected Behavior

Regular debts should evolve through explicit actions:

```text
Record payment
Add charge
Forgive balance
Correct balance
Settle formally
Reverse action
Archive / restore
```

Generic update should only edit safe metadata or correct pristine setup mistakes.

### Actual Behavior

The codebase has a good debt action layer, but generic `PATCH /debts/{id}` and `DELETE /debts/{id}` are still too broad.

Specific risks:

```text
- Status can be changed too generically.
- Initial amount can be adjusted after activity if remaining does not go negative.
- Hard delete can erase a debt and linked financial events if backend can reverse wallet effects.
- Formal details can be edited without fully going through policy-aware formal action rules.
```

### Why This Matters

Debt is not a normal editable row. It is a timeline of obligation facts.

If generic CRUD bypasses the action model, the user can accidentally destroy the story of the debt while the app still shows clean-looking numbers.

### Affected Modules

- Debts API
- Debt policy
- Debt ledger
- Financial events
- Wallet ledger
- Goals linked to debts
- Debt UI

### Related Invariants

- Wallet balances must follow wallet rules.
- Finalized expenses affect real financial records.
- Debt should be represented as an event timeline, not silent row mutation.
- Ledger history should remain audit-friendly.

### Decision

Fix before exposing richer regular debt edit/delete UI.

Rules:

```text
1. Generic debt update must not update status.
2. Paid status is automatic.
3. Forgiven status must come from forgiveness action.
4. Settled status must come from settlement action.
5. Archived/restored status must come from explicit archive/restore actions.
6. Initial amount can be corrected only while the debt is pristine.
7. Hard delete is only for pristine debts created by mistake.
8. Non-pristine debts should use reverse, correction, settlement, forgiveness, or archive.
```

Pristine means:

```text
- Only the original debt creation exists.
- No payments.
- No charges.
- No forgiveness.
- No settlement.
- No balance corrections.
- No reversals.
- No funded linked goal depending on the debt.
- Not managed by a payment plan.
```

### Proposed Fix

Backend:

```text
- Split generic update into safe metadata update.
- Add explicit Correct opening amount action, allowed only for pristine debts.
- Add explicit archive and restore endpoints using debt policy.
- Remove status from generic DebtUpdate.
- Harden delete with a pristine-debt guard.
- Gate formal asset/collateral/term edits through policy-aware actions.
```

Frontend:

```text
- Rename edit flow based on meaning: Edit details vs Correct opening amount.
- Do not show Delete once real debt history exists.
- Show Archive for closed debts.
- Use action buttons for real-world changes.
```

### UX Copy / Error Message

```text
This debt already has history. To keep the record clear, change the balance with a payment, charge, forgiveness, correction, or reversal.
```

```text
Opening amount can only be corrected before any debt activity is recorded.
```

```text
This debt cannot be deleted because it already has recorded activity. Archive it or reverse the specific action instead.
```

### Test Cases Needed

- [ ] Pristine debt can correct opening amount.
- [ ] Debt with payment cannot correct opening amount.
- [ ] Debt with charge cannot correct opening amount.
- [ ] Generic update cannot set status to ARCHIVED, PAID, FORGIVEN, or SETTLED.
- [ ] Archive action only works for closed debts.
- [ ] Restore action only works for archived debts.
- [ ] Non-pristine debt delete is blocked.
- [ ] Pristine debt delete reverses linked wallet event if needed.
- [ ] Payment-plan-managed debt cannot be edited or deleted through regular debt routes.

### Final Resolution

Not implemented yet.

### Notes

Do not treat initial amount changes as a normal field edit. It is either a pristine setup correction or it is the wrong action.


## EC-048 - Payment Plan CRUD Needs Lifecycle-Aware Boundaries

**Status:** DESIGN_CONFIRMED  
**Severity:** S1  
**Area:** Payment Plans / Debts / API / UI  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

Payment plan cards currently need update/delete behavior, but payment plans are more sensitive than normal records because they create and manage a linked debt plus a schedule.

Example:

```text
User creates a 12-month sofa plan.
User pays 3 rows.
Then user edits total price, row count, or start date.
```

Without strict rules, the visible schedule, debt balance, and wallet history can drift apart.

### Steps to Reproduce

1. Create a payment plan.
2. Record one or more payments or charges.
3. Try to change the financial schedule or delete the plan.

### Expected Behavior

Payment plan CRUD should depend on lifecycle state.

Pristine plan:

```text
- User can correct setup mistakes.
- User can delete the plan if no real activity exists.
```

Active plan with history:

```text
- User can edit safe metadata.
- User cannot silently rewrite the financial schedule.
- Financial changes must become explicit actions.
```

Closed plan:

```text
- User can archive.
- User should not delete meaningful history.
```

### Actual Behavior

Payment plan cards do not yet expose clear update/delete flows.

The missing product rule is not merely "add edit and delete buttons"; the missing rule is what those buttons are allowed to do.

### Why This Matters

A payment plan owns scheduled obligation truth.

If the user can freely edit amount, months, due dates, or delete after payments, the system can end up with:

```text
- Paid rows that no longer match the debt ledger.
- Debt balance that no longer matches schedule rows.
- Wallet history that cannot explain the plan.
- Goal targets that point to stale installment amounts.
```

### Affected Modules

- Payment Plans
- Installment payments
- Debt ledger
- Financial events
- Wallet ledger
- Goals linked to payment plans
- Payment plan UI

### Related Invariants

- Wallet balances must follow wallet rules.
- Finalized expenses affect real financial records.
- Payment-plan-managed debts are owned by the payment-plan layer.
- Scheduled obligation rows must reconcile with linked debt balance.

### Decision

Payment plans need update/delete, but with explicit boundaries.

Safe metadata update while not archived:

```text
- Item name
- Provider/store/bank name
- Notes
- Display labels
```

Conditionally editable before real activity:

```text
- Total price
- Down payment
- Payment count
- Frequency
- Start date
- Due dates
- Expense category/subcategory/project links
```

Not generic update after activity:

```text
- Total price
- Remaining balance
- Paid row amounts
- Payment count
- Schedule rewrite
- Linked debt status
```

After activity, these need explicit actions:

```text
- Add fee or penalty
- Record payment
- Undo payment
- Write off row
- Undo write-off
- Reschedule / restructure plan
- Correct balance
- Archive
```

### Proposed Fix

Backend:

```text
- Add update route with lifecycle checks.
- Add delete route only for pristine payment plans.
- Add archive route for closed or intentionally inactive plans.
- Treat schedule changes after activity as a future Reschedule/Restructure action, not generic update.
- Keep linked debt changes inside the payment-plan transaction boundary.
```

Frontend:

```text
- Show Edit details for safe metadata.
- Show Correct setup only for pristine plans.
- Hide Delete after real activity exists.
- Show Archive for closed plans.
- Explain why financial edits are locked after payments exist.
```

### UX Copy / Error Message

```text
This payment plan already has payment history. To keep the schedule and debt balance clear, use payment, fee, write-off, or reschedule actions instead.
```

```text
This plan can only be deleted before payments, fees, goals, or corrections are recorded.
```

### Test Cases Needed

- [ ] Pristine payment plan can update setup fields.
- [ ] Payment plan with payment history cannot update total price.
- [ ] Payment plan with charge history cannot update schedule shape.
- [ ] Payment plan with linked goal cannot be deleted.
- [ ] Pristine payment plan delete removes linked debt safely.
- [ ] Non-pristine payment plan delete is blocked.
- [ ] Archived payment plan is immutable except restore if supported.

### Final Resolution

Not implemented yet.

### Notes

Do not add CRUD buttons before the lifecycle policy exists. Otherwise the UI will invite dangerous actions.


## EC-049 - Payment Plan Payments Need Plan-Owned Reversal

**Status:** DESIGN_CONFIRMED  
**Severity:** S0  
**Area:** Payment Plans / Debts / Wallets / Goals / API / UI  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

Payment-plan history shows debt activity, but payment-plan payment rows do not have a proper reverse action.

Regular debt details can reverse debt ledger entries, but payment-plan-managed debts intentionally block generic debt actions.

### Steps to Reproduce

1. Create a payment plan.
2. Record a payment.
3. Open payment-plan details.
4. Try to undo the payment from payment-plan history.

### Expected Behavior

Payment plan payments should have a plan-owned undo/reverse action.

The action should update all affected layers together:

```text
- Installment payment rows
- Installment allocations
- Linked debt ledger entries
- Financial event
- Wallet ledger effect
- Goal funding consumption if involved
- Plan remaining amount
- Debt remaining amount
```

### Actual Behavior

The backend has debt ledger reversal for regular debts.

Payment-plan-managed debts are protected from generic debt reversal so the schedule does not desync from the debt.

That protection is correct, but the replacement payment-plan-specific reversal is missing.

### Why This Matters

One payment-plan payment is not just a debt ledger entry.

Example:

```text
Ali pays October installment: 1,333,333 UZS.
```

The app updates:

```text
- Wallet balance
- Financial event
- Debt balance
- Debt ledger
- October installment row
- Installment allocation rows
```

If only the debt ledger is reversed, the debt can reopen while the October row still says paid.

### Affected Modules

- Payment Plans
- Installment payments
- Installment allocations
- Debt ledger
- Financial events
- Wallet ledger
- Goal funding
- Payment plan details UI

### Related Invariants

- Wallet balances must follow wallet rules.
- Payment-plan-managed debts are owned by the payment-plan layer.
- Scheduled rows must reconcile with debt balance.
- Reversal must be dependency-aware.

### Decision

Do not enable generic debt ledger reverse for payment-plan-managed debts in the UI.

Build a payment-plan-owned reversal action.

Recommended action names:

```text
Undo payment
Undo write-off
```

Avoid showing generic "Reverse" as the primary user-facing label for payment-plan payments.

### Proposed Fix

Backend v1:

```text
- Add payment-plan payment reversal endpoint.
- Group reversal by debt transaction or installment allocation operation.
- Reverse wallet/financial event effects through an audit-preserving reversal event.
- Create reversal debt ledger entries or mark the original financial event as reversed consistently.
- Remove or reverse installment allocations.
- Reduce paid_amount on affected schedule rows.
- Recompute row statuses.
- Reconcile plan and linked debt.
- Sync linked Pay Obligation goals.
```

Better future shape:

```text
POST /installments/payment-operations/{operation_id}/reverse
```

This is cleaner than reversing a single schedule row because one payment can cover multiple rows.

### UX Copy / Error Message

```text
Undo this payment?
```

```text
Sarflog will put the money back in the app wallet, reopen the affected installment rows, and keep a reversal record.
```

```text
Only undo this if the real payment was recorded by mistake or was cancelled/refunded in real life.
```

### Test Cases Needed

- [ ] Reversing a payment-plan payment restores wallet balance.
- [ ] Reversing a payment-plan payment creates an audit reversal event.
- [ ] Reversing a payment-plan payment reopens affected installment rows.
- [ ] Reversing a multi-row payment reopens all affected rows correctly.
- [ ] Reversing a charge-component payment restores charge balance, not principal balance.
- [ ] Reversing a goal-funded payment restores goal state or blocks until a dependency-aware path exists.
- [ ] Generic debt ledger reverse remains blocked for payment-plan-managed debts.

### Final Resolution

Not implemented yet.

### Notes

Undo write-off already has a narrow row-specific route, but payment reversal needs an operation-level route because wallet money and debt events are involved.


## EC-050 - Reverse Policy Must Preserve Real Wallet Reality

**Status:** DESIGN_CONFIRMED  
**Severity:** S1  
**Area:** Debts / Payment Plans / Wallets / UI / API  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

User sees a Reverse or Undo action and may assume it is safe to use whenever they dislike a past event.

But reversing in the app changes wallet balances. That is only correct if the app record was wrong or the real-world payment was cancelled/refunded.

### Steps to Reproduce

1. Record a real debt or installment payment from a wallet.
2. Reverse it in the app even though the real bank/cash payment still happened.
3. App wallet balance no longer matches reality.

### Expected Behavior

Reverse should mean:

```text
This app record was wrong, or the real-world action was cancelled/reversed.
```

Reverse should not mean:

```text
I regret the payment.
I want to hide history.
The friend forgave money.
The store added a penalty.
The balance is different now.
```

Those should use explicit actions.

### Actual Behavior

Regular debt reversal exists, but the product policy and UI warnings need to be stricter.

Payment-plan reversal is not yet implemented as a plan-owned action.

### Why This Matters

Wallet balances are supposed to mirror real wallet balances.

Example:

```text
Ali paid 500k to a friend yesterday.
The money really left his bank.
If he reverses the app payment today, Sarflog adds 500k back.
Now Sarflog says the bank has 500k more than reality.
```

Correct action depends on reality:

```text
Payment was recorded by mistake -> reverse.
Bank payment failed -> reverse.
Friend returned the money -> record a real incoming/refund path.
Friend forgave debt -> forgive balance.
Store added penalty -> add charge.
Balance was entered wrong -> correct balance.
```

### Affected Modules

- Debts
- Payment Plans
- Wallet ledger
- Financial events
- Debt ledger
- UI confirmation dialogs

### Related Invariants

- Wallet balances must follow wallet rules.
- Finalized expenses affect real financial records.
- Reversal must be audit-preserving.
- App corrections must not desync from real-world money.

### Decision

Reverse should be conservative and explicit.

Ordering rule:

```text
- Encourage newest-first reversal everywhere.
- For payment plans, initially allow only latest payment-operation reversal.
- Older payment-plan reversal should be deferred until robust reallocation logic exists.
- For regular debts, older reversal may be allowed only if backend recalculation is safe and user confirms.
```

### Proposed Fix

Backend:

```text
- Keep audit-preserving reversal events.
- Add policy checks for dependency-aware reversal.
- For payment plans, restrict v1 reversal to latest payment operation.
- Block reversal when linked goals or later dependent actions cannot be safely updated.
```

Frontend:

```text
- Use "Undo payment" for payment operations.
- Use "Reverse action" for ledger actions.
- Show clear confirmation text about real-wallet reality.
- Encourage reversing the latest action first.
- Explain blocked older reversals instead of hiding them silently.
```

### UX Copy / Error Message

```text
Only undo this if the real payment was cancelled, failed, refunded, or recorded by mistake.
```

```text
This will put the money back in the app wallet. If the real wallet did not receive the money back, use another action instead.
```

```text
Undo newer payments first so the payment plan stays in order.
```

### Test Cases Needed

- [ ] Regular debt reversal creates audit reversal and adjusts wallet.
- [ ] Reversing an already reversed entry is blocked.
- [ ] Payment-plan older payment reversal is blocked in v1.
- [ ] Payment-plan latest payment reversal is allowed when no unsupported dependencies exist.
- [ ] Reversal confirmation copy appears before wallet-changing reversal.
- [ ] Goal-linked reversal either updates goal state safely or is blocked with explanation.

### Final Resolution

Not implemented yet.

### Notes

Reverse is not a delete button. It is a financial correction action.


## EC-051 - Debt And Payment Plan Activity Timelines Should Use One Storyline Model

**Status:** DESIGN_CONFIRMED  
**Severity:** S2  
**Area:** Debts / Payment Plans / UI  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

Debt details show activity as an oldest-to-newest storyline.

Payment plan details currently display debt activity newest-to-oldest in the side panel because the frontend reverses the backend activity list.

Payment plan history also lacks the same visual treatment and action clarity as debt details.

### Steps to Reproduce

1. Open a regular debt details modal.
2. Observe activity ordered oldest first with a storyline line.
3. Open a payment plan details modal.
4. Observe debt activity displayed newest first in a separate side list.

### Expected Behavior

Debt and payment-plan activity should use the same mental model:

```text
Oldest event at top
Newest event at bottom
Business date shown separately from recorded timestamp
Visual line connecting events
Action buttons shown only when valid
```

### Actual Behavior

Payment plan activity is less clear:

```text
- It reverses the activity order in the UI.
- It does not use the full storyline presentation.
- It does not expose a valid payment-plan-specific undo action.
- It can make the user think payment plans are less auditable than regular debts.
```

### Why This Matters

Users understand debts and payment plans as stories:

```text
Plan created
First payment made
Penalty added
Payment written off
Next payment made
```

Showing the latest event first is useful for feeds, but less useful for reconstructing an obligation timeline.

For audit-style modals, oldest-to-newest is easier to reason about.

### Affected Modules

- Debt details modal
- Payment plan details modal
- Debt activity schema
- Installment plan details endpoint
- Reversal UI

### Related Invariants

- Ledger history should remain audit-friendly.
- Business date and recorded timestamp have different meanings.
- Payment-plan-managed debts are owned by the payment-plan layer.

### Decision

Use storyline ordering for debt and payment plan detail modals.

Rules:

```text
- Details modals: oldest to newest.
- Feed/list previews: newest first is acceptable.
- Show Date for business date.
- Show Recorded for created_at timestamp in viewer-local timezone.
- Add vertical storyline line for payment-plan activity.
- Show Reverse/Undo only when the proper domain action exists and is allowed.
```

### Proposed Fix

Frontend:

```text
- Remove payment-plan `debtActivity.slice().reverse()` in details modal.
- Reuse or mirror the debt storyline UI for payment-plan activity.
- Add business date and recorded timestamp to payment-plan activity cards.
- Add plan-owned Undo payment button only after backend endpoint exists.
```

Backend:

```text
- Continue returning activity oldest-to-newest for details endpoints.
- Include enough reversal/action metadata for payment-plan-owned actions later.
```

### UX Copy / Error Message

```text
Storyline
```

```text
Date: Jun 6, 2026
Recorded: Jun 6, 2026, 7:32 PM
```

```text
Undo payment
```

### Test Cases Needed

- [ ] Payment plan details activity renders oldest-to-newest.
- [ ] Debt details activity remains oldest-to-newest.
- [ ] Payment plan activity shows Date and Recorded.
- [ ] Payment plan activity uses visual storyline line.
- [ ] Undo/Reverse buttons are disabled or hidden until a valid domain action exists.

### Final Resolution

Not implemented yet.

### Notes

History panels can be newest-first when they are a feed. Debt and payment-plan detail modals should be storylines.


## EC-052 - Commitment Intelligence Must Be A Layer Above The Core Model

**Status:** DESIGN_CONFIRMED  
**Severity:** S4  
**Area:** Product / Budgets / Goals / Projects / Debts / Income / Dashboard  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

Sarflog has a strong core financial model:

```text
Wallets = reality
Goals = protected money
Budgets = monthly behavior limits
Projects = multi-expense missions
Debts/installments = obligations
Income = future capacity
```

A later product idea suggested making Sarflog more "revolutionary" by showing how today's action affects tomorrow's commitments.

The risk is misreading that idea as a replacement for budgets/categories.

### Expected Behavior

Do not abandon the core model.

Build a Commitment Intelligence layer above it:

```text
Core model stays strict.
Intelligence layer explains commitment impact.
```

The product should help answer:

```text
Can I pay?
Should I spend?
What future commitment does this affect?
```

### Actual Behavior

Not implemented yet.

### Why This Matters

The product wedge is not just better expense tracking.

The wedge is:

```text
Sarflog knows which money is free,
which money is protected,
which money is expected,
and which future commitments are at risk.
```

That can make Sarflog feel like a financial decision engine without weakening the accounting model.

### Affected Modules

- Dashboard / Command Center
- Budgets
- Goals / Savings
- Debts
- Payment plans
- Income
- Projects
- Analytics

### Related Invariants

- Budgets remain monthly behavior limits.
- Goals remain wallet-backed hard protection.
- Expected income remains future planning support, not cash today.
- Debts and installments remain obligations.
- Projects remain scoped missions, not category replacements.

### Decision

Use this product direction:

```text
Sarflog explains how today's action affects tomorrow's commitments.
```

Do not replace:

```text
Categories
Monthly budgets
Subcategories
Project category tracking
Debt/installment ledgers
```

Add Commitment Intelligence as:

```text
Dashboard layer
Analytics layer
Warnings layer
Timeline layer
Later AI explanation layer
```

### Proposed Fix

When building the Command Center, add a visible "Commitment Intelligence v1" layer:

```text
- Financial Truth card
- Commitments snapshot
- Budget room explanation
- Upcoming obligations
- At-risk warnings
- Goal progress impact
- Future timeline v1
```

### UX Copy / Error Message

```text
You have 18.2M total.
9.2M is truly free.
14.7M monthly plan is waiting on salary.
All protected goals are safe.
Rent and phone installment are covered.
```

### Test Cases Needed

- [ ] Dashboard separates total wallet money from truly free money.
- [ ] Dashboard separates protected goal money from budget room.
- [ ] Dashboard shows future obligations without changing core ledgers.
- [ ] Dashboard does not replace category budgets with commitment groups.

### Final Resolution

Not implemented yet.

### Notes

See also `docs/PRODUCT.md`.


## EC-053 - Financial Truth Status Should Be Built Before Fancy Forecasts

**Status:** DESIGN_CONFIRMED  
**Severity:** S4  
**Area:** Budgets / Income / Goals / Debts / Payment Plans / Dashboard  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

The product needs a simple way to tell users whether their monthly plan is realistic.

An earlier idea called this a "Financial Truth Score."

### Expected Behavior

Do not make this a fake score out of 100.

Use clear statuses:

```text
Covered now
Covered, no cushion
Waiting on income
At risk
Underfunded
Borrowing pressure
```

### Actual Behavior

Not implemented yet as a unified product status.

### Why This Matters

Users need clear language more than a gamified score.

Example:

```text
Free money now:        9.2M
Expected salary:       8.0M
Monthly budgets:       14.7M
Debt/installments due: 2.0M
```

Sarflog should say:

```text
Your plan is realistic after salary.
5.5M of this month depends on expected income.
```

This is useful, concrete, and believable.

### Affected Modules

- Budget summary
- Income summary
- Debt/payment-plan due calculations
- Goal funding summary
- Command Center

### Related Invariants

- Expected income is classification support, not allocation.
- Goal-protected money is not free money.
- Credit limit is not budget room.
- Rollover is permission, not cash.

### Decision

Build Financial Truth status early as a deterministic backend/domain calculation.

Initial formula should stay simple:

```text
Planning capacity =
free money now
+ expected income
- known promises
- desired cushion
```

Then compare:

```text
monthly budgets total
vs
planning capacity
```

Do not auto-allocate expected salary to categories, goals, debts, or projects.

### Proposed Fix

Phase 1 should create the foundation:

```text
- Free money now
- Protected goal money
- Expected income
- Known promises
- Budget room
- Budget realism status
- Goal-funded vs normal spending separation
```

Phase 4 should expose it prominently in the Command Center.

### UX Copy / Error Message

```text
Covered now
```

```text
Your plan is covered, but it uses all free money. There is no cushion.
```

```text
Waiting on income
```

```text
This plan works if expected income arrives.
```

```text
Underfunded
```

```text
Your monthly plan exceeds free money, expected income, and known promises by 3M.
```

### Test Cases Needed

- [ ] Status is Covered now when budgets fit free money and cushion.
- [ ] Status is Covered, no cushion when budgets use all free money.
- [ ] Status is Waiting on income when budgets require expected income.
- [ ] Status is Underfunded when budgets exceed free money plus expected income after promises.
- [ ] Credit limit does not increase planning capacity.
- [ ] Goal-protected money does not increase free money.

### Final Resolution

Not implemented yet.

### Notes

Financial Truth status is the first useful intelligence layer. Avoid fake precision.


## EC-054 - Future Timeline And Opportunity Cost Need Narrow V1 Guardrails

**Status:** DESIGN_CONFIRMED  
**Severity:** S4  
**Area:** Dashboard / Budgets / Goals / Recurring / Debts / Payment Plans / UX  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

Two high-value product ideas were discussed:

```text
Future Timeline Engine
Dynamic Opportunity Cost
```

Both can make Sarflog feel much smarter, but both can become noisy or dishonest if implemented too early or too broadly.

### Expected Behavior

Timeline should show concrete future events:

```text
Jun 10 - Internet bill due
Jun 15 - Salary expected
Jun 18 - Phone installment due
Jun 24 - Laptop goal projected complete
Jul 1 - Rent due
```

Opportunity cost should only appear for meaningful cases:

```text
Large spending
Over-budget spending
Unsafe spending
Spending that threatens known obligations
Spending that threatens explicit goal commitments
```

### Actual Behavior

Not implemented yet.

### Why This Matters

The product should not warn on every small purchase.

Bad UX:

```text
Every coffee shows a scary warning.
```

Good UX:

```text
Restaurant: 1.5M
Entertainment budget left: 500k

This puts Entertainment 1M over plan.
If you keep your Laptop goal on track, reduce another category or add income.
```

Later, after goal projection is reliable:

```text
This may delay Laptop by 11 days.
```

### Affected Modules

- Dashboard / Command Center
- Budget warnings
- Expense creation/edit flows
- Recurring expenses
- Installments
- Debts
- Goals
- Income

### Related Invariants

- Do not invent fake precision.
- Do not claim exact goal delay until projection math is stable.
- Do not warn on every transaction.
- Budget categories remain the accounting/reporting layer.

### Decision

Build the future timeline after budget/income/debt/goal foundations are stable.

Build opportunity cost as a narrow v1:

```text
Explain budget impact first.
Explain commitment risk second.
Delay exact goal-date impact until projection math is honest.
```

### Proposed Fix

Phase 4 v1:

```text
- Show timeline of expected income, recurring bills, debts, installments, and goal target dates.
- Show deterministic risk labels.
- Show opportunity-cost warnings only on large or unsafe spending.
```

Phase 8 advanced:

```text
- AI-assisted explanations
- Smarter goal delay estimates
- Natural-language monthly summaries
- Probabilistic stress forecast only if the model becomes reliable
```

### UX Copy / Error Message

```text
This puts Entertainment 1M over plan.
Move room from another category or record anyway.
```

```text
Rent depends on expected salary arriving before Jul 1.
```

```text
This purchase may affect your Laptop goal. Projection will be shown after goal forecasts are enabled.
```

### Test Cases Needed

- [ ] Timeline includes expected income.
- [ ] Timeline includes recurring obligations.
- [ ] Timeline includes debt and installment due dates.
- [ ] Opportunity-cost warning is shown for over-budget spending.
- [ ] Opportunity-cost warning is not shown for every small safe expense.
- [ ] Goal-delay wording is not shown unless projection data exists.

### Final Resolution

Not implemented yet.

### Notes

Start deterministic. Add smarter explanations later.


## EC-055 - Revolutionary Product Ideas Need Roadmap Placement And Deferral Rules

**Status:** DESIGN_CONFIRMED  
**Severity:** S4  
**Area:** Roadmap / Product / Dashboard / AI / Input Intelligence  
**Discovered on:** 2026-06-07  
**Reported by:** User / AI Agent  

### Scenario

Several "10/10 product" ideas were discussed:

```text
Financial Truth status
Future Timeline Engine
Dynamic Opportunity Cost
Commitment-Based Finance
Intent-Based Transactions
Financial Stress Forecast
```

The risk is implementing them too early before the underlying math is stable.

### Expected Behavior

Roadmap placement should preserve correctness:

```text
Phase 1 makes Sarflog correct.
Phase 4 makes Sarflog feel brilliant.
Phase 7 improves input intelligence.
Phase 8 adds useful AI.
```

### Actual Behavior

Ideas are not yet fully placed in implementation roadmap artifacts.

### Why This Matters

If advanced insights are built before budgets, expected income, goals, debts, and payment plans are stable, the product may sound smart but be wrong.

Wrong smart-sounding guidance is worse than no guidance.

### Affected Modules

- ROADMAP.md
- Dashboard / Command Center
- Analytics
- Budgets
- Income
- Goals
- Debts
- Payment plans
- Expense drafts
- AI features

### Related Invariants

- Core accounting must remain strict.
- Intelligence must be explainable.
- AI should not compensate for weak domain math.
- Categories remain necessary for reports, budgets, subcategories, projects, and later business/tax-style analysis.

### Decision

Use this placement:

```text
Financial Truth status:
  Phase 1 backend foundation
  Phase 4 Command Center UI

Commitment-Based Finance:
  Phase 4 overlay/dashboard layer
  Not a replacement for categories

Future Timeline Engine:
  Phase 4 deterministic v1
  Phase 8 smarter version

Dynamic Opportunity Cost:
  Phase 4 narrow v1
  Phase 8 advanced version

Intent-Based Transactions:
  Phase 7
  Best paired with draft-based receipt, voice, and natural-language input

Financial Stress Forecast:
  Phase 4 rule-based warnings
  Phase 8 AI-assisted/probabilistic only if reliable
```

### Proposed Fix

Update roadmap language later to include:

```text
Commitment Intelligence v1
```

inside Phase 4 Command Center work.

Execution order:

```text
1. Budget room / Financial Truth status
2. Expected income integration
3. Recurring obligations and upcoming payments
4. Future timeline v1
5. Optional intent tags
6. Opportunity cost for big/unsafe spending
7. Stress forecast later
```

### What To Defer

```text
Full replacement of budgets with Survive/Grow/Enjoy
Probability-based stress forecasts
Warning on every transaction
AI diagnosis like "you have an impulse problem"
Complex opportunity-cost math for every small purchase
```

### UX Copy / Error Message

```text
Commitment Intelligence
```

```text
Sarflog explains how today's action affects tomorrow's commitments.
```

### Test Cases Needed

- [ ] ROADMAP.md includes Commitment Intelligence v1 under Command Center when roadmap is updated.
- [ ] Phase 1 implementation does not introduce AI/probabilistic forecasts.
- [ ] Intent tags remain optional.
- [ ] Commitment groups do not replace category budgets.
- [ ] Stress forecast wording remains rule-based until advanced model exists.

### Final Resolution

Not implemented yet.

### Notes

Phase 1 foundation should stay boring and correct. Phase 4 is where the differentiated product experience begins.

---

## EC-056 - Budget Cards Had Cramped, Noisy Action Controls

**Status:** FIXED  
**Severity:** S2  
**Area:** Budgets / UI  
**Discovered on:** 2026-06-08  
**Reported by:** User  

### Scenario

The desktop Budget cards showed too many visible actions at once:

```text
Preview
View
Subcategories
Update limit
Delete
```

The row became visually cramped, especially in a 3-column desktop card grid. The card also showed small signal pills like:

```text
7 recent entries
2 subcategories
1 project link
```

These signals added noise without giving enough useful context on the card itself.

### Expected Behavior

Budget cards should remain quick scanning surfaces:

```text
Category
Month
Spent / limit
Progress
Remaining
Status
```

Primary and secondary actions should be visually ordered instead of competing for attention.

### Actual Behavior

The card mixed summary data, preview behavior, CRUD actions, subcategory management, and destructive delete in one cramped action row. The `Preview` action was unclear and did not justify its place as a visible card action.

### Resolution

Implemented a cleaner desktop action model:

```text
Primary visible action:
- View Expenses

Overflow menu:
- View details
- Update limit
- Add sub-limit
- Delete budget
```

Additional UI cleanup:

- Removed the `Preview` card action.
- Removed the inline preview expansion behavior from Budget cards.
- Moved secondary/admin actions behind a `...` overflow menu.
- Separated destructive `Delete budget` inside the overflow menu.
- Made the bottom action rail appear on desktop hover/focus to reduce visual noise.
- Removed the small `x recent entries`, `x subcategories`, and `x project links` pills from Budget cards.
- Removed the card-level detail prefetch used only for those pills, reducing background request noise.

### Product Decision

Budget cards should not act like mini admin dashboards. They should show budget health and expose one obvious investigation path:

```text
View Expenses
```

Budget structure and configuration belong in deeper surfaces:

```text
View details
Update limit
Add sub-limit
Delete budget
```

### Remaining Follow-Up

- [ ] Build the real `View Expenses` modal for a monthly category budget.
- [ ] Convert `View details` from full-page behavior into a premium wide modal / sheet pattern.
- [ ] Refactor `Update limit` to respect expected-income planning capacity.
- [ ] Revisit delete rules so budget deletion aligns with linked expenses, sub-limits, refunds, and future planning rules.
- [ ] Rework sub-limits inside Budget Details instead of keeping them as a standalone lightweight create form.

### Test Cases Needed

- [ ] Budget card renders without signal pills.
- [ ] Budget card action rail appears on hover/focus on desktop.
- [ ] `View Expenses` opens the Expenses page filtered by budget category and month until the modal exists.
- [ ] Overflow menu contains details, update limit, add sub-limit, and separated destructive delete.
- [ ] Frontend build passes in Docker.

### Verification

```text
docker compose exec -T frontend npm run build
```

Passed on 2026-06-08.

---

## EC-108: Separate Quick Add Expense Form from Debt/Installment Payment Form

**Status:** DEFERRED  
**Severity:** S2  
**Area:** Expenses / Debts / Goals / UI  
**Discovered on:** 2026-06-09  
**Reported by:** User  

### Scenario

The user needs to log a payment. If all types of payments (everyday expenses, debt/installment payments, and goal-funded project spending) are stuffed into a single "Quick Add Expense" form, the cognitive load will be too high, and the form will be bloated with irrelevant toggles (e.g. "Is this a debt payment?", "Are you using a goal?").

### Expected Behavior

The global `+` button should offer context-driven entry points based on the user's mental state:
1. `+ Add Expense`: Simple form for normal cash flow.
2. `+ Pay Debt/Installment`: Specific form asking which liability is being paid, and if a Pay Obligation goal is covering it.
3. `+ Use Goal Money`: Specific form for capital events/project spending.

### Why This Matters

Reduces cognitive load, prevents miscategorization of debt payments as normal expenses, and clearly guides users through the complex interactions between Goals, Projects, and Debts without overwhelming them.

### Decision

Defer for future UI refactor.

---

## EC-109: Over-budget UX must never block expense entry

**Status:** DEFERRED  
**Severity:** S1  
**Area:** Expenses / Budgets / UI  
**Discovered on:** 2026-06-10  
**Reported by:** User  

### Scenario

User attempts to log an expense (e.g., $150 for Groceries) that exceeds the remaining budget limit for that category (e.g., $100 remaining).

### Expected Behavior

The system MUST NOT block the user from saving the expense. The system must accept the reality of the wallet transaction instantly. An inline, non-blocking warning should dynamically appear near the amount field (e.g., ⚠️ *"This will put Groceries $50 over limit."*), but the "Save" button must remain active and require only one tap.

### Why This Matters

Financial tracking apps must prioritize "Ledger Truth" (Wallet reality) over "Metadata" (Budget plans). Blocking a user at the checkout line from entering a real transaction causes data loss, inaccurate wallet balances, and user churn. The app is a mirror, not a prison warden.

### Decision

Defer for UI refactor of the Quick Add form.

---

## EC-110: Post-Save Actions for Over-budget Expenses

**Status:** DEFERRED  
**Severity:** S2  
**Area:** Expenses / Budgets / UI  
**Discovered on:** 2026-06-10  
**Reported by:** User  

### Scenario

Immediately after a user successfully records an expense that pushes a category into the red.

### Expected Behavior

The UI should display the updated status (e.g., "Groceries: $50 over") and immediately offer actionable paths to resolve the failed plan:
1. "Move $50 limit from another category" (Reallocation)
2. "Increase Groceries limit" (Changes the plan, which will then be validated against Free Cash)
3. "Reduce future spending" / "Leave over-budget" (Accepts the red status as a behavioral warning)

### Why This Matters

This creates a healthy psychological feedback loop. It allows the user to record reality frictionlessly, but immediately hands them the tools to either adapt their plan or accept the consequences of their spending.

### Decision

Defer for future UI refactor.

---

## EC-111: "Underfunded" term is semantically incorrect for budgets

**Status:** FIX_NOW  
**Severity:** S2  
**Area:** Budgets / UI / Copywriting  
**Discovered on:** 2026-06-10  
**Reported by:** User  

### Scenario

When the total sum of a user's Monthly Budget Limits exceeds their "Free Money Now" (available cash).

### Expected Behavior

The UI status should NOT use the term "Underfunded". It should use terms like "Over-Planned", "Exceeds Free Cash", or "Unbacked".

### Why This Matters

According to Sarflog philosophy, Budgets are "spending permissions," not physical envelopes of money. A permission cannot be "underfunded." Using the word "Underfunded" tricks the user into thinking they are using an Envelope Budgeting system and need to physically move cash around. The true issue is that their *planned promises* exceed their *wallet reality*. 

### Decision

Fix now. Update UI copy across all budget health dashboards to replace "Underfunded" with "Over-Planned" or "Exceeds Free Cash".

---

## EC-112: Soft-Close Project End Dates (Expense Tagging Rule)

**Status:** DEFERRED  
**Severity:** S2  
**Area:** Projects / Expenses / API  
**Discovered on:** 2026-06-10  
**Reported by:** User  

### Scenario

A project reaches its `end_date` (e.g., July 14th). On July 15th, the user needs to log a late receipt from July 14th to the project.

### Expected Behavior

Do not hard-block expense tagging based on the current calendar date (July 15th). Instead, the system must enforce a strict mathematical temporal rule: `expense_date` MUST be between the project's `start_date` and `end_date`. If the user backdates their expense to July 14th, it is accepted. If they try to log a July 15th expense to the project, the API/UI rejects it with: *"This expense falls outside the project dates."*

### Why This Matters

Real-world financial reporting often lags behind the calendar (e.g., delayed credit card charges, forgotten receipts). Hard-blocking tagging on the day after the project ends prevents retroactive forensics.

### Decision

Defer for backend/UI implementation of project tagging logic.

---

## EC-113: Symmetrical Validation for Start/End Date Updates

**Status:** DEFERRED  
**Severity:** S1  
**Area:** Projects / API / DB Validation  
**Discovered on:** 2026-06-10  
**Reported by:** User  

### Scenario

The user attempts to change the `start_date` or `end_date` of an ACTIVE project that already has expenses tagged to it.

### Expected Behavior

The system MUST enforce the following unbreakable invariant:
`Project Start Date` <= `Every Tagged Expense Date` <= `Project End Date`

- Moving start date backward or end date forward (expanding the window): Always allowed.
- Moving start date forward or end date backward (shrinking the window): Allowed, BUT the backend must validate that no existing tagged expenses fall outside the new boundary. If they do, block the update with a clear warning: *"You cannot change the start date to May 10th because you have an expense tagged on May 5th. Untag that expense first."*

### Why This Matters

Users frequently realize they are in a "project phase" only after it has begun (requiring retroactive start dates), or they experience delays (requiring extended end dates). Providing maximum flexibility while mathematically preventing orphan expenses is the hallmark of a premium tool.

### Decision

Defer for backend API implementation on Project update endpoints.

---

## EC-114: "Reopen to Edit" Pattern for Completed Projects

**Status:** DEFERRED  
**Severity:** S2  
**Area:** Projects / UI / Reports  
**Discovered on:** 2026-06-10  
**Reported by:** User  

### Scenario

A user wants to change the dates or add a forgotten expense to a project that has already been marked as "Completed" (and has generated its final wrap-up report).

### Expected Behavior

When `Status == COMPLETED`, the project's dates and expenses must be completely locked (read-only) to preserve the integrity of the historical report. To make changes, the user must explicitly click a "Reopen Project" button, which transitions the project back to `ACTIVE`. Only then can they adjust dates or add late expenses before marking it "Completed" again.

### Why This Matters

A "Finished" project should feel solid, safe, and immutable, giving the user closure. Allowing silent background edits to an archived project breaks trust in historical data. The explicit "Reopen" action creates a necessary psychological barrier, telling the user they are breaking the seal on a historical record.

### Decision

Defer for Project lifecycle UI/UX implementation.

---

## EC-115: The "Valid Budget Spent" Mathematical Backing Rule

**Status:** DEFERRED  
**Severity:** S1 (Critical Math Architecture)  
**Area:** Budgets / Core Math / API  
**Discovered on:** 2026-06-10  
**Reported by:** User / AI  

### Scenario

The system determines the global "Monthly Plan Backing Status" (Covered vs. Over-Planned) by checking if the total promised Budget Limits exceed the user's available backing. However, when a user spends money on a category, the money leaves their `Free Cash Now`. If the system compares static gross limits against the newly reduced `Free Cash Now`, perfectly planned normal spending triggers false "Over-Planned" alerts. Furthermore, if a user spends money in a category with a 0-limit, they steal from the free cash that was backing other categories.

### Expected Behavior

The system MUST calculate `Effective Backing` by adding only the money spent *within* the limits back into the free cash.

The absolute mathematical rule is:
1. `Valid Budget Spent` = `min(spent, limit)` (calculated per category).
2. `Effective Backing` = `Free Money Now` + `Expected Income` + `Total Valid Budget Spent`.
3. If `Total Limits` > `Effective Backing`, the plan is **OVER-PLANNED**.

### Why This Matters

This is the holy grail of budget mathematics.
- Normal spending within a limit: Wallet drops by X, `Valid Spent` increases by X. Effective backing stays completely stable. Plan remains **COVERED**.
- Overspending past a limit: Wallet drops by Y, `Valid Spent` increases by 0 (capped at limit). Effective backing drops by Y. Plan breaks and becomes **OVER-PLANNED**.
- Unbudgeted spending (0 limit): Wallet drops by Z, `Valid Spent` increases by 0 (min(Z, 0)). Effective backing drops by Z. Plan breaks and becomes **OVER-PLANNED**.

### Decision

A formal Implementation Plan has been created to rewrite the math in `budget_service.py` to use `min(spent, limit)` across `get_budget_plan_status`, `validate_budget_plan_capacity`, and `build_budget_month_summary`. Pending execution approval.

---

## EC-116: The 50/30/20 Rule Reporting Integration & Category Taxonomy

**Status:** DEFERRED  
**Severity:** S3  
**Area:** UI / Reports / Categories  
**Discovered on:** 2026-06-10  
**Reported by:** User / AI  

### Scenario

The user wishes to implement a 50/30/20 (Needs/Wants/Savings) high-level health check dashboard. To do this, the system must confidently group global `ExpenseCategory` ENUMs into these three super-categories without falling into "taxonomy traps". 

Additionally, the `INSTALLMENTS_DEBT` category is considered for removal. A debt/installment purchase should be categorized by its actual product (e.g., buying a phone on installment is `ELECTRONICS`, not `INSTALLMENTS_DEBT`). 

### Expected Behavior

1. Evaluate and safely deprecate/migrate the `INSTALLMENTS_DEBT` category if necessary.
2. Hardcode a mapping in the reporting service (or allow user overrides) to map categories to Needs, Wants, and Savings.
3. Generate a Health Check UI component (Pie chart or progress bar) on the dashboard showing the user's ratio for the current month against the 50/30/20 ideal.

### Decision

Defer for Reporting Dashboard design phase.

---

## EC-117: Graduating a "Fund Project" Goal Before 100% Completion

**Status:** RESOLVED (Conceptually)  
**Severity:** S3  
**Area:** Goals / Projects  
**Discovered on:** 2026-06-10  
**Reported by:** User  

### Scenario

A user creates a "Fund Project" goal for a Wedding with a target of 50M. After 8 months, they have only saved 40M, but the wedding begins tomorrow. They must graduate the goal into an Isolated Project right now, even though progress is only at 80%.

### Expected Behavior

The system MUST allow early graduation. 
When graduated early:
1. The Isolated Project is created with an initial stash of exactly the funded amount (40M).
2. The user can spend down the 40M stash. 
3. If the user eventually spends 45M on the project, the first 40M consumes the safe stash. The remaining 5M is "unfunded project overspending".
4. Because the 5M is unfunded, it will automatically consume the user's `Free Money Now` in their main wallet. This mathematically correct behavior will dynamically reduce the user's Effective Backing, turning their monthly budgets "Over-Planned" (as defined in EC-115).

### Why This Matters

This ensures the user is never stuck in a "Goal Prison." Life happens, timelines shift, and users must be able to deploy whatever money they have managed to save when the project actually starts. The system's core math perfectly handles the shortfall by bleeding the overspending into their normal monthly cash reserves.

### Decision

Ensure backend `Goal -> Project` graduation endpoints do not enforce `current_amount == target_amount`.

---

## EC-118: "Tick Up vs Tick Down" Visual Architecture for Projects

**Status:** DEFERRED  
**Severity:** S2  
**Area:** UI / Projects / Categories  
**Discovered on:** 2026-06-10  
**Reported by:** User / AI  

### Scenario

The system must visually represent spending progress differently depending on whether the user is tracking expenses against an analytical limit (Overlay) or spending down a pre-funded stash of cash (Isolated). 

### Expected Behavior

The UI must enforce the following strict visual directions:

**1. Overlay Projects (The Tracker)**
- **Direction:** Ticks UP (e.g., 0% -> 100%).
- **Metaphor:** A glass filling up towards a ceiling.
- **Why:** Overlay projects are analytical limits. The user starts with 0 spent and tries not to hit the maximum limit.

**2. Isolated Projects (The Stash)**
- **Direction (Overall Project):** Ticks DOWN (e.g., 100% -> 0%).
- **Metaphor:** A draining battery or pre-paid gift card.
- **Why:** The user spent months filling a Goal. The project represents the consumption of that reward.

**3. Subcategories inside an Isolated Project**
-  (`limit_amount` is set):** Ticks DOWN (e.g., Venue drops from 20M to 0). It acts as a strict sub-stash carved out of the overall stash.


**4. Overspending (Soft Limits)**
- If a subcategory limit is exceeded (e.g., 16M spent on a 15M limit), the system MUST NOT block the transaction.
- The UI drops the subcategory balance to a negative number (e.g., -1M Remaining) and turns it red. The overall project stash continues to deplete accurately.

### Why This Matters

This "Mini-Sarflog" architecture perfectly mirrors physical reality. It avoids "prison warden" hard-blocking while maintaining total psychological consistency between tracking restrictions (ticking up) and consuming rewards (ticking down).

### Decision

### Decision

Defer for Project Detail Screen UI implementation.

Ensure backend `Goal -> Project` graduation endpoints do not enforce `current_amount == target_amount`.

---

## EC-119: Deprecation of INSTALLMENTS_DEBT Category

**Status:** DEFERRED  
**Severity:** S3  
**Area:** DB Models / Enums  
**Discovered on:** 2026-06-11  
**Reported by:** User  

### Scenario
The system currently has `INSTALLMENTS_DEBT` as a global `ExpenseCategory` Enum. However, a debt or installment is merely a financing mechanism, not the actual nature of the expense. If a user buys a phone on installment, it is `ELECTRONICS`. If they take a loan for surgery, it is `HEALTH`.

### Expected Behavior
`INSTALLMENTS_DEBT` must be removed from the Enum list in the database. Debt tracking should rely on the actual category of the goods/services purchased. The financing mechanism (Debt/Installment) is handled by the `EntityLedger` or `FinancialEvent` relationships, not the category.

### Decision
Scheduled for removal in the next DB migration.

---

## EC-120: Subcategories - Custom User-Defined vs Hardcoded

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** Architecture / UI Strategy  
**Discovered on:** 2026-06-11  
**Reported by:** AI / User  

### Scenario
Should the system hardcode subcategories (e.g., "Coffee", "Uber", "Rent") or allow users to type and create whatever custom subcategories they want?

### Expected Behavior (The Strategy)
The system MUST use a hybrid approach:
1. **Hardcoded Global Categories:** The 20 high-level categories (`Groceries`, `Transport`, etc.) must remain hardcoded. This ensures macro-reporting, the 50/30/20 rule logic, and AI transaction categorization all function reliably across all users.
2. **Custom User-Created Subcategories:** Subcategories MUST be entirely user-generated. Every human lifestyle is different. If the app hardcodes "Coffee", a user who only drinks tea will feel the app is rigid. By letting the user type "My Morning Matcha" under `Dining Out`, they gain a massive sense of psychological ownership over their budget.

### Decision
Maintain the current schema where `UserSubcategory` is created dynamically by user input.

---

## EC-121: Subcategory Month-Specific Architecture (The Fix)

**Status:** DEFERRED  
**Severity:** S1 (Critical Architecture Flaw)  
**Area:** DB Architecture  
**Discovered on:** 2026-06-11  
**Reported by:** AI  

### Scenario
Currently, `UserSubcategory` holds the `monthly_limit` as a global property without tying it to a specific `budget_year` or `budget_month`. If a user edits their limit in August, it retroactively corrupts their June historical data.

### Expected Behavior
Subcategory tags must be separated from their financial limits using a standard Database Normalization pattern.
1. `UserSubcategory` becomes just a global dictionary of tags (Name, Category). `monthly_limit` is deleted.
2. A new `BudgetSubcategoryLimit` table is created. It links `budget_id` + `subcategory_id` + `monthly_limit`.
3. When a new month triggers lazy materialization, the backend copies the `BudgetSubcategoryLimit` rows from the previous month to the new month, keeping history perfectly intact.

### Decision
Requires a DB schema migration and API refactor to split the tag from the limit.

---

## EC-122: Subcategory Limit Invariant

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** Budgets / Math  
**Discovered on:** 2026-06-11  
**Reported by:** User  

### Scenario
A user has a parent category `Transport` with a 2M limit. They attempt to set subcategory limits of `Fuel` = 1.5M and `Taxi` = 1M (Total 2.5M).

### Expected Behavior
The sum of all Subcategory Limits inside a single month MUST NEVER exceed the Parent Category Limit. 
`sum(subcategory_limits) <= parent_category_limit`.
If `sum < parent`, the difference is the "Unallocated Category Buffer". If the user attempts to breach this invariant, the UI must block the limit adjustment and prompt them to increase the Parent Category Limit first.

---

## EC-123: Subcategory Overspending & Actionable UI

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** UI / Budgets  
**Discovered on:** 2026-06-11  
**Reported by:** User  

### Scenario
User has `Taxi` limit of 500k. They spend 700k on a taxi.

### Expected Behavior
1. **Never Block Reality:** The transaction is saved successfully.
2. **Visual Warning:** The `Taxi` subcategory bar turns red and shows `-200k Remaining`.
3. **Actionable UI (Mirroring EC-110):** The user is presented with inline options to resolve the math:
   - *Reallocate:* Move 200k from another subcategory (e.g., `Fuel`) into `Taxi`.
   - *Increase Parent Limit:* Increase the overall `Transport` category limit by 200k (which will pull from global `Free Money Now`), thereby increasing the buffer to cover the `Taxi` overspending.
   - *Ignore:* Leave it red.

---

## EC-124: Unspecified Subcategory Spending & Hierarchical Leakage

**Status:** RESOLVED (Conceptually)  
**Severity:** S1 (Core Math)  
**Area:** Budgets / Math  
**Discovered on:** 2026-06-11  
**Reported by:** User / AI  

### Scenario (The Extreme Case)
`Utilities` Parent Limit: 3M.
Sub-limits: Wifi (500k), Water (1.5M), Elec (1M). [Buffer = 0].
Actual Spending: Wifi (600k), Water (1M), Elec (1.2M), plus 500k spent on unspecified Utilities.
*Total Spent in Utilities: 3.3M.*

### Expected Behavior
1. **Allow Unspecified Spending:** Users are NEVER forced to pick a subcategory. Subcategories are optional micro-trackers. 500k spent directly on the parent `Utilities` category is perfectly legal.
2. **Hierarchical Math Resolution:**
   - *Inside the Category:* Wifi is red (-100k). Elec is red (-200k). Unspecified is raw spend (-500k). Water is green (+500k).
   - *Category Level:* Total limit (3M) is compared against Total Spent (3.3M). The Parent Category turns red (-300k Remaining).
   - *Global Level:* The `valid_budget_spent` rule (EC-115) engages. `min(3.3M spent, 3M limit) = 3M`. The 300k of overspending "leaks" out of the category and steals from the global `Free Money Now`, turning the entire global plan "Over-Planned".

### Why This Matters
This hierarchy perfectly contains chaos. Subcategory overspending first steals from the parent category's buffer (or other subcategories). Only when the *parent category itself* is breached does the damage leak out to the global wallet.

---

## EC-125: Subcategory Reallocation Boundaries

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** UI / Budgets  
**Discovered on:** 2026-06-11  
**Reported by:** User / AI  

### Scenario
User overspends on `Transport -> Taxi` and clicks the "Reallocate" UI button. Can they directly pull funds from `Groceries -> Meat` (cross-category), or must they only pull from `Transport -> Fuel` (intra-category)?

### Expected Behavior (The Strategy)
Subcategory reallocations must be **strictly confined to their own Parent Category (Intra-category only).**

**The Rules:**
1. **Sibling Cannibalism Only:** `Taxi` can only pull funds from the unallocated `Transport` buffer or from its sibling `Fuel`.
2. **The Parent Wall:** If `Transport` has no buffer and `Fuel` is empty, the user CANNOT directly pull from `Groceries -> Meat`. 
3. **Macro Escalation:** To fund `Taxi` in this scenario, the user must first escalate to the Parent level. They must reallocate from the `Groceries` Parent to the `Transport` Parent. Once `Transport` has new funds (a new buffer), they can assign it to `Taxi`.

### Why This Matters (Senior Engineering Reasoning)
If we allow cross-category subcategory moves (e.g., `Meat` -> `Taxi`), we are forced to silently mutate Parent Category limits in the background to prevent mathematical invariants (EC-122) from breaking. The user might move money from `Meat` to `Taxi` and be shocked later to see their overall `Groceries` limit dropped and their `Transport` limit increased. 
By enforcing the boundary, we strictly separate **Micro Decisions** (how I split my Transport money) from **Macro Decisions** (stealing food money to pay for transport). It keeps the UI honest, predictable, and mathematically bulletproof.

---

## EC-126: Budget Rollover Strategy

**Status:** RESOLVED (Conceptually)  
**Severity:** S3  
**Area:** Budgets  
**Discovered on:** 2026-06-11  
**Reported by:** User  

### Expected Behavior
Budget rollovers (auto-carrying unused limit to the next month) will **NOT** be shipped in v1. 
1. Unused budget room simply vanishes (returns to unallocated capacity).
2. Users can manually increase next month's limits if they wish.
3. If/when rollovers are introduced, they will strictly be for "Sinking Funds" (e.g., Car Maintenance that requires stacking limits for an inevitable big purchase) or "Variable Necessities" (e.g., Summer vs Winter electricity bills). Capped rollovers can be used for discretionary categories. 

### Why This Matters
Auto-rollovers can accidentally encourage lifestyle creep ("I saved 600k on groceries, so I deserve to feast next month"). By dropping unused limits, we force the user to make an intentional decision on what to do with the saved money (e.g., fund a goal).

---

## EC-127: Budgets ↔ Goals Mathematical Interplay

**Status:** RESOLVED (Conceptually)  
**Severity:** S1 (Core Math)  
**Area:** Wallets / Goals / Budgets  
**Discovered on:** 2026-06-11  
**Reported by:** User  

### The Golden Invariant
*Money allocated to a goal is mathematically protected and can no longer be spent on regular monthly purchases.*

### Expected Behavior
1. **Funding a Goal:** Locks money away. `Wallet Balance` stays the same, but `Protected Goal Money` increases, forcing `Free Money Now` to decrease.
2. **The Hard Block:** Goal funding is only allowed from **unallocated free money**. If a user tries to fund a goal with money already promised to a Monthly Budget Limit, the UI must warn/block: *"You only have 1M unallocated. To fund this goal with 2M, reduce budgets by 1M or add more income."*
3. **Goal Purchases:** If a user buys the laptop they saved for, it bypasses the Monthly Budgets completely. It drains the `Protected Goal Money` and drops the `Wallet Balance`. The Monthly Electronics budget is untouched.

---

## EC-128: Planning Capacity Formula (Inflows vs Debts)

**Status:** RESOLVED (Conceptually)  
**Severity:** S1 (Core Math)  
**Area:** Budgets / Math  
**Discovered on:** 2026-06-11  

### Expected Behavior
The Budget Planning Capacity formula must use `Expected Inflows`, not just `Expected Income`. 
Formula: `Planning Capacity = Free Money Now + Expected Inflows - Upcoming Debt Obligations`
1. **Expected Inflows:** Includes Salary, Receivables, AND Bank Microloans. Sarflog doesn't judge the source of cash. If a user takes a loan for liquidity, they can budget with it, but the UI must flag the dashboard as **Debt-Funded Plan**.
2. **Upcoming Debt Obligations:** Debts the user owes do NOT blindly subtract from capacity globally. They are treated depending on their bucket (See EC-131).

---

## EC-129: Unstructured Debt Repayments (OWED to User)

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** UX / Expected Inflows  
**Discovered on:** 2026-06-11  

### Expected Behavior
Personal loans owed to the user do not behave like bank amortization schedules. 
1. **The "How Much" Prompt:** When a debt has a due date this month, auto-prompt the user: "Bob owes 5M. How much do you expect him to pay this month?" User enters a partial amount (e.g., 1M). Only 1M is added to Expected Inflows.
2. **The Trust Penalty:** If Bob misses the 1M payment, the debt becomes `OVERDUE`. The 1M does NOT auto-rollover to the next month (to prevent giving the user fake money). The user must explicitly re-commit to trusting Bob next month.
3. **Open-Ended Debts:** If a debt has NO due date, Sarflog assumes 0 Expected Inflow and stays silent. It never nags. The user must manually click "Expect Payment" in the Debt module to trigger an inflow.

---

## EC-130: Realizing Expected Inflows (No Deletions)

**Status:** RESOLVED (Conceptually)  
**Severity:** S1 (Architecture)  
**Area:** DB / Expected Inflows  
**Discovered on:** 2026-06-11  

### Expected Behavior
When an Expected Inflow arrives, the database row MUST NOT be deleted. 
1. **State Transition:** The status transitions from `EXPECTED` to `RECEIVED`.
2. **Over-Realization:** If a user expected 2M but received 4M, the system creates a 4M Wallet transaction. The math flawlessly updates because the `RECEIVED` row stops contributing to Expected Inflows, and the Wallet Balance handles the new 4M reality. (Recommendation: Add `received_amount` or `linked_transaction_id` to the `ExpectedIncome` schema).

---

## EC-131: Upcoming Debts UX (Two Buckets)

**Status:** RESOLVED (Conceptually)  
**Severity:** S1  
**Area:** Budgets / UX  
**Discovered on:** 2026-06-11  

### Expected Behavior
Debts owed BY the user fall into two distinct architectural buckets:
1. **Bucket 1: Category-Linked Debts (Budget Consumers):** any `OWING` debt whose repayment will be recorded as an expense against a budget category. The repayment IS the expense, so it must be considered during monthly budget planning. Examples include `DEFERRED_EXPENSE`, `STORE_INSTALLMENT`, `FINANCED_ASSET_PURCHASE`, and any payable debt row with an `expense_category` or installment/payment-plan schedule that posts categorized expense payments. These act as **Minimum Required Category Limits** in the Budget Planner (e.g., "Minimum Groceries Limit: 500k due to Deferred Expense").
2. **Bucket 2: Cash-Only Debts (Wallet Drainers):** `CASH_BORROWED`, `INFORMAL_DEBT`. These are raw cash transfers. They trigger the "Pre-Flight Check": a global simulated reality warning showing that unallocated cash cannot cover the upcoming debt. Users can click `[Reserve X for Debt]` to instantly lock the money away and force budget compliance.

### G6 Clarification
Bucket 1 is classified by the repayment accounting route, not just by the debt label. If the future payment creates a categorized expense, it belongs in budget setup as a category floor. It must not be hidden inside a global debt deduction because budgets are monthly spending permissions and this payment consumes one of those permissions. Bucket 2 remains for payable debts whose repayment is a cash movement or debt settlement without a budget category.

---

## EC-132: Warning UI for OWING Debts

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** UX / Debts  
**Discovered on:** 2026-06-11  

### Expected Behavior
How the UI prompts the user to pay back debts they owe:
1. **With Deadline / Overdue:** Triggers a **Hard Warning** (Yellow Banner). "You owe 4M on July 4th. If you pay this, you will be over-planned."
2. **Without Deadline (Open-Ended):** Triggers a **Soft Suggestion**. At the bottom of the Budget Planner, a quiet "Debt Paydown Opportunities" list appears. It allows the user to optionally allocate spare unallocated cash to open-ended debts without screaming at them.

---

## EC-133: New Month Budget Initialization Flow

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** Budgets / UX  
**Discovered on:** 2026-06-11  

### Expected Behavior
On the 1st of the month, when the user opens the Budget page, they are presented with 3 setup modes:
1. **Plan from Scratch:** All categories start at 0. The user manually sets limits, bounded by their global Planning Capacity (`Free Money + Expected Inflows`).
2. **Copy Previous Month:** The exact limits from the previous month are copied over. **Important:** The system instantly runs the mathematical Pre-Flight Check. If the user's capacity dropped, or a new Debt Obligation exists this month, the dashboard immediately flashes warnings (e.g., "OVER-PLANNED" or "Cash Crunch Risk") so the user knows the copied lifestyle doesn't fit the new reality.
3. **Smart Auto-Fill (Recommended):** The system copies the previous month's limits, but **auto-adjusts** Category-Linked Debts (Bucket 1). Example: If June Electronics was 0, but July has a 1M TV installment due, the system copies June but forces the Electronics limit to 1M to satisfy the debt minimum, preventing the user from having to manually fix underfunded categories.

### G6 Clarification
The "1st of the month" and target budget month must be computed from the user's effective timezone. Backend routes must use the existing timezone helpers, such as `get_effective_user_timezone` and `today_in_tz`, instead of `date.today()` or server-local dates. The planner should behave according to the user's local calendar day, not the server's calendar day.

---

## EC-134: Credit Card Architecture & Single Source of Truth

**Status:** RESOLVED (Conceptually)  
**Severity:** S1 (Architecture)  
**Area:** Wallets / Debts  
**Discovered on:** 2026-06-11  

### Expected Behavior
Credit cards and debit cards with overdrafts must NOT automatically create shadow records in the `debts` table.
1. **The Architecture:** A Credit Card is simply a `Wallet` that is allowed to carry a negative balance. The negative `balance` IS the single source of truth for the debt.
2. **Repayments:** Paying off a credit card is done via a standard **Wallet Transfer** (e.g., from Humo to Credit Card), not a categorized expense or special debt repayment action.
3. **The Unified UI Trick:** To ensure the user sees all liabilities in one place, the "Debts" page UI dynamically queries and combines all formal records from the `debts` table WITH all `wallets` where `balance < 0`.

---

## EC-135: The Credit Card Float & Free Money Now

**Status:** RESOLVED (Conceptually)  
**Severity:** S1 (Core Math)  
**Area:** Budgets / Math  
**Discovered on:** 2026-06-11  

### Expected Behavior
Using a credit card to fund budgeted lifestyle expenses (The "Float") must not create Fake Wealth or force immediate repayment.
1. **Free Money Now Rule:** The calculation for `Free Money Now` must ONLY sum the balances of **Positive Wallets**. It strictly ignores negative wallet balances and available credit limits. This prevents negative cards from instantly destroying the user's budget capacity (which would block reality if they only plan to pay the minimum).
2. **The Float Solution:** When a user spends on a CC, their positive cash stays high, but they incur debt. During the 1st-of-month budget planning, the Pre-Flight Check detects the negative CC balance and flashes a warning: *"Your Credit Card balance is -10M. [ Reserve 10M for Full Payoff ] or [ Reserve Custom Amount ]."*
3. **Action:** The user manually inputs how much of their positive cash they are willing to lock away (Shadow Reserve) to pay the credit card statement. This accurately shrinks their `Free Money Now` capacity while respecting their choice to ride the float if they only pay the minimum.

---

## EC-136: Recurring Expenses Architecture

**Status:** RESOLVED (Conceptually)  
**Severity:** S2  
**Area:** Budgets / UI  
**Discovered on:** 2026-06-11  

### Expected Behavior
Recurring expenses must integrate smoothly into the Budget Planner and provide psychological "Latte Factor" projections to the user.
1. **Budget Integration:** A recurring expense behaves mathematically identical to a Category-Linked Debt (Bucket 1). During monthly budget setup, the system scans the `recurring_expenses` table. If a 100k Spotify sub is due in July, the Entertainment category displays: *"Minimum Recommended Limit: 100k."* The "Smart Auto-Fill" button will automatically set this floor to prevent accidental underfunding.
2. **Cost Projection UI:** On the details page for a recurring expense, the user sees the long-term cost of the habit across frequency-appropriate horizons. This is a psychological planning feature and must not mutate wallet, expense, budget, or debt truth.

### G6 Clarification
Recurring projection math should be exposed by a backend projection contract rather than duplicated as frontend-only arithmetic. The backend already owns recurring frequency, `next_due_date`, cycle behavior, user timezone, and schedule advancement rules, so it is the safer source for consistent projection totals across web, mobile, tests, and future timeline work. The frontend should render the returned default and custom projection rows.

Projection totals should be calculated by counting scheduled occurrences in the requested horizon and multiplying by the recurring amount. Use the same recurring date advancement semantics as the scheduler wherever possible. Anchor projections to the user's effective local date or the recurring template's next due date according to the API contract, but never to server-local `date.today()`.

Default projection matrix:

| Recurring frequency | Default projections to show | Reasoning |
| --- | --- | --- |
| `ONE_TIME` | One occurrence / due amount only | A one-time template has no habit curve; horizons should not imply repetition. |
| `DAILY` | 7 days, 14 days, 1 month, 3 months, 6 months, 12 months | Daily habits need short shock values plus longer habit cost. |
| `WEEKLY` | 1 month, 3 months, 6 months, 12 months | Weekly costs are too noisy at daily horizons; monthly and longer are useful. |
| `BIWEEKLY` | 1 month, 3 months, 6 months, 12 months | Biweekly obligations should show month-scale and longer impact. |
| `MONTHLY` | 3 months, 6 months, 12 months | Monthly subscriptions should avoid redundant 1-month projection equal to one payment. |
| `QUARTERLY` | 6 months, 12 months | Quarterly expenses need medium and annualized visibility. |
| `SEMI_ANNUALLY` | 12 months | Semi-annual expenses should show annual impact by default. |
| `YEARLY` | 12 months | Yearly expenses should show the annual due amount by default. |

Custom projection matrix:

| Recurring frequency | Custom projection units allowed | Examples |
| --- | --- | --- |
| `ONE_TIME` | none by default, or explicit one occurrence | "This bill costs 250k once." |
| `DAILY` | days, weeks, months, years | 4 days, 10 days, 299 days, 2 weeks, 18 months. |
| `WEEKLY` | weeks, months, years | 1 week, 2 weeks, 50 weeks, 6 months. |
| `BIWEEKLY` | weeks, months, years | 2 weeks, 10 weeks, 26 weeks, 12 months. |
| `MONTHLY` | months, years | 2 months, 5 months, 18 months, 2 years. |
| `QUARTERLY` | quarters, months, years | 1 quarter, 5 quarters, 18 months, 2 years. |
| `SEMI_ANNUALLY` | half-years, months, years | 1 half-year, 3 half-years, 24 months. |
| `YEARLY` | years, months | 1 year, 3 years, 30 months. |

Custom projections should be persisted per recurring expense if the user saves them, and may also be accepted as ad hoc request parameters for preview. Saved custom projection definitions are user preference metadata only; they must not affect budget floors, due dates, or posted expenses. Validation should cap extreme horizons to prevent expensive schedule simulation while still allowing practical values like 299 days or 50 weeks.

---

## EC-137: Replay Attack Token Rotation Bug

**Status:** NEEDS_FIX  
**Severity:** S1 (Security)  
**Area:** Backend / Auth  
**Discovered on:** 2026-06-11  

### Expected Behavior
When `rotate_refresh_token` in `oauth2.py` detects a Replay Attack (by finding a token in the `rotated_marker_key`), it MUST revoke the entire Token Family.

### Actual Behavior
The backend successfully detects the replay attack and throws a 401 error to the user/attacker who triggered it. However, it fails to lookup the `family_id` and delete the associated tokens. This means the newly rotated token (which could be in the hands of the hacker) remains perfectly valid, keeping the compromised session alive.

---

## EC-138: Root Frontend Route Overriding Authentication

**Status:** NEEDS_FIX  
**Severity:** S2 (UX)  
**Area:** Frontend / Routing  
**Discovered on:** 2026-06-11  

### Expected Behavior
When a user with a valid 7-day HttpOnly refresh cookie visits the app, they should automatically bypass the login screen and land on the `/dashboard`.

### Actual Behavior
1. `App.jsx` unconditionally runs `<Route path="/" element={<Navigate to="/sign-in" replace />} />`.
2. `Login.jsx` lacks a `useEffect` or conditional check to redirect `isLoggedIn()` users away from the login form. 
This causes users to believe they were logged out, even though the `silentRefresh()` background handshake was successful.

---

## EC-139: "Sign Out of All Devices" Feature

**Status:** ARCHITECTED (Needs API/UI wiring)  
**Severity:** S4 (Feature Idea)  
**Area:** Auth / Backend / UI  
**Discovered on:** 2026-06-11  

### Expected Behavior
Users should be able to click a button in Settings to kill all their active sessions on all devices (laptops, phones, etc.).

### Architecture Readiness
The backend architecture already perfectly supports this via Redis Token Families. The function `oauth2.revoke_all_user_tokens(user.id)` already exists and is used successfully during password resets. 
To implement: We just need to expose a new `POST /auth/logout-all-devices` API endpoint that calls this function, and wire it to a button in the frontend Settings page.

---

## EC-140: Mobile App Authentication Adapters

**Status:** DEFERRED (Phase 5)  
**Severity:** S3 (Architecture Prep)  
**Area:** Auth / API  
**Discovered on:** 2026-06-11  

### Expected Behavior
The current auth system relies heavily on `HttpOnly` cookies for XSS protection and Web redirects for Google OAuth. Native mobile apps (iOS/Android) struggle with both.

### Required Tweaks for Mobile Launch
1. **Refresh Token Delivery:** Modify `/sign-in` and `/refresh` to check for a `client_type=mobile` flag. If mobile, return the Refresh Token in the JSON body so the app can store it in the native iOS Keychain/Android Keystore instead of fighting with invisible cookies.
2. **Native Google SDK:** Add a new route (e.g., `POST /auth/google/mobile-login`) to accept a native Google ID Token directly from the iOS/Android SDK, skipping the browser redirect flow entirely.

---

## EC-141: Wallet Real-World Nuance Enhancements (V2 Roadmap)

**Status:** DEFERRED  
**Severity:** S4 (Feature Idea)  
**Area:** Wallets / UX / Backend  
**Discovered on:** 2026-06-11  

### Expected Behavior
While the current double-entry Wallet model mathematically supports revolving credit and checking accounts perfectly, it lacks some real-world clearing, billing, and metadata nuances that users expect from premium banking tools. 

### Required Enhancements for V2
1. **Pending vs. Posted Transactions:** Add `PENDING` to `FinancialEventStatus`. Real-world transactions don't post instantly. Adding this allows users to see their "Available Balance" (Pending + Posted) versus their "Cleared Balance" (Posted only), which is critical for bank reconciliation.
2. **Credit Card Statements:** Revolving debt has a statement cycle. To avoid interest, users only need to pay their "Statement Balance", not their entire negative `current_balance`. Add fields like `last_statement_balance`, `last_statement_date`, and `minimum_payment_due` to the Wallet model (or create a new `CreditCardStatement` model) to snapshot the balance at the `billing_cycle_start_day`.
3. **Interest Rates (APR / APY):** Add `interest_rate_bps` to the Wallet model. This allows for estimating savings growth on `SAVINGS` wallets and calculating interest charges on `CREDIT` wallets.
4. **Payment Network Metadata:** Add `network` or `issuer` fields (e.g., VISA, Mastercard, Amex, PayPal) to Wallets. This enables automatic rendering of premium UI icons.

---

## EC-142: E-Wallets, Interest Projections, and Bank Deposits (V2 Roadmap)

**Status:** DEFERRED  
**Severity:** S4 (Feature Idea)  
**Area:** Wallets / Debts / Assets / UX  
**Discovered on:** 2026-06-11  

### Scenario
As the system matures, tracking modern digital money (PayPal, Kaspi) and interest-bearing accounts (Loans, Fixed Deposits) needs explicit architectural support to avoid ledger drift and user confusion.

### Required Enhancements for V2
1. **E-Wallet integration:** Change `WalletType.PRELOADED` to `E_WALLET` (or add it). This maps better to the modern user's mental model (Venmo, PayPal, Kaspi, Apple Cash) which lack traditional banking constraints and clearing cycles, and often act as pass-throughs for other cards.
2. **Interest Projection Engine ("Smart Confirmation"):** Do NOT fully automate interest generation. Banks use complex, proprietary day-count conventions that cause automated ledgers to drift. Instead, build a "Projection Engine" that estimates the interest for Debts (Loans) or Savings and prompts the user: *"Your loan generated ~$15.50 in interest. Did this post?"* The user can adjust the exact cents and hit "Confirm" to manually create the `DebtCharge`. This keeps the ledger perfectly accurate without silent background drift.
3. **Fixed Term Deposits as Assets:** Liquid savings should remain `WalletType.SAVINGS`. However, Fixed Term Deposits (like a 12-month CD) lock the money away and should be tracked under `Assets`. Add an `apy` and `maturity_date` to the Asset model. The projection engine can prompt the user when the deposit matures to either reinvest or withdraw.
4. **Amortization Visualizer for Loans:** Bank loans are already perfectly modeled under `Debts`. A key UX win would be an amortization schedule visualizer that projects payoff dates based on current installment payments.

---

## EC-143: External APIs and Augmented Reconciliation (V3/V4 Roadmap)

**Status:** DEFERRED  
**Severity:** S4 (Feature Idea)  
**Area:** Assets / API / Data / UX  
**Discovered on:** 2026-06-11  

### Scenario
As the platform evolves, manual entry for highly volatile or standardized assets (crypto, stocks, precious metals) and tracking true purchasing power requires API automation, but without losing the immutable ledger trust.

### Required Enhancements for V3/V4
1. **Asset Pricing APIs (Crypto, Stocks, Metals):** Instead of manually updating `current_value` on liquid assets, fetch Friday closing prices via external APIs (e.g., CoinGecko, Yahoo Finance). To protect ledger truth and avoid intraday chart noise, use "Augmented Reconciliation": the system generates a notification (*"BTC is up 5%. Accept new valuation?"*), and if the user hits Accept, the system records a formal `ADJUSTMENT` event.
2. **Open Banking Integration:** When national regulations support standard open APIs, connect to local banks. Instead of auto-syncing (which causes ledger drift), use the same Augmented Reconciliation engine to fetch raw transactions and prompt the user: *"We found 3 new debit card swipes. Click to categorize and approve them."*
3. **Inflation / Purchasing Power Tracking:** A "Pro" wealth management feature. Connect to national CPI APIs to overlay an "Inflation line" on the Net Worth charts, showing the user their *real* purchasing power growth vs nominal growth.

---

## EC-144: Input Intelligence & "Trained Monster" Architecture (Phase 7 Roadmap)

**Status:** DEFERRED  
**Severity:** S4 (Architecture/Feature Idea)  
**Area:** Input / OCR / Voice / AI / Telegram  
**Discovered on:** 2026-06-12  

### Scenario
As the application expands to reduce manual entry friction (Phase 7), adding OCR, Voice, and NLP input pipelines risks creating "feature soup" (a "Wild Monster") where each input method has its own direct-to-database logic, causing duplicates and ledger corruption.

### The "Trained Monster" Unified Pipeline
To protect the immutable ledger from AI hallucinations and bad parses, ALL intelligent inputs must flow through a unified "Draft → Review → Finalize" pipeline. 
1. **The Translation Step:** Raw audio or image data is translated via STT (Whisper) or OCR (Google Vision) into raw text.
2. **The Intelligence Step (LLM):** An LLM parses the raw text and outputs standard structured JSON. This naturally handles multiple languages (Russian, Uzbek, English) without hardcoded localization.
3. **The Draft Step:** The JSON is saved to the `expense_drafts` table.
4. **The Finalization Step:** The user logs into the app, reviews the draft, edits any mistakes, and clicks "Confirm" to fire the single `finalizeExpense()` function, locking it into the ledger.

### Key Feature Concepts
1. **Voice as a Universal Command Center:** Voice input should NOT be restricted to expenses. The LLM prompt should be an "Intent Classifier" that routes the user's speech to Expenses, Income, Transfers, or Debts. (Start with Expenses for V1 to prevent scope creep).
2. **Basket Mode as a Session Draft:** Basket Mode (for shopping trips) is structurally just an `ExpenseSessionDraft`. Users can add items over the course of hours, and it remains open until they hit "Finalize", processing all drafted items into the final ledger at once.
3. **Telegram / WhatsApp Bot Integration:** Because the architecture relies on text-to-JSON parsing, integrating a Telegram Bot comes almost "for free". Users can text "korzinka 350k debit" to the bot, which passes the text to the exact same AI pipeline, queuing up a draft for them to review later in the mobile app.


---

## EC-145: "Over-Planned" Budget Status Without UI Explanation (Deferred Expense Debt Case)

**Status:** NEW  
**Severity:** S2  
**Area:** Budgets / Debts / UI / API  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario

When a user adds a debt (e.g., "Someone paid for me" / Personal deferred expense) for a specific category (e.g., Dining Out) that is due this month, the backend accurately reserves cash for it. This reduces `plan_backing` and can push the overall plan health to `Over-Planned`. 

However, the frontend UI completely fails to explain *why* the plan is over-planned, creating massive user confusion. Furthermore, the backend currently misclassifies this specific type of deferred categorical consumption as a generic cash reserve rather than a category floor.

### Steps to Reproduce

1. Have a budget with limited free money and existing valid budget spent.
2. Add a debt of type "I owe" (Reason: Someone paid for me / Personal deferred expense) with a specific category (e.g., Dining Out) for 200,000, due this month.
3. Check the budget status.

### Expected Behavior

- **Product Semantic:** A personal deferred expense with an expense category should be treated as a `category floor` (deferred categorical consumption), not a generic cash payback reserve.
- **UI Explainability:** The UI should show the bridge numbers that explain the budget status. It should display a "Dining Out" minimum floor and offer repair actions (e.g., create/increase Dining Out budget to cover the debt). 

### Actual Behavior

- **Product Semantic:** The frontend sends `product_kind: INFORMAL_DEBT`, and the backend treats it as a global `cash_obligation_reserve_total`.
- **UI Explainability:** The user's overall plan becomes Over-Planned, but the "Dining Out" category card does not show any pressure or turn red. The UI hides the bridge numbers (`valid budget spent` and `cash obligation reserves`), so the user sees `Free Money` and `Budget Total` and cannot mathematically reconcile why the status is `Over-Planned`.

### Why This Matters

The lack of UI explainability creates massive user confusion, as they cannot understand how the budget math is derived. The misclassification in the backend violates the G3/G6 design docs intended for category-linked payable debts.

### Affected Modules

- Budgets (Frontend UI)
- Budget Service (Backend)
- Debts/Obligations

### Decision

NEW / Investigating

### Proposed Fix

1. **G9 / Budget Plan Explainability:** Update the Budget UI in `Budgets.jsx` to expose the breakdown: `Available Backing = Free Money Now + Already Valid Budget Spent - Cash Obligation Reserves (Debts)`. Surface debt/recurring/category floor pressure.
2. **Backend Classification Cleanup:** Fix the budget service to treat `INFORMAL_DEBT` with a category as a category floor, not just a generic cash payback reserve.


---

## EC-146: Reserve Fund Goal Expenses Require Explicit Budget Impact Decision

**Status:** NEW  
**Severity:** S2  
**Area:** Budgets / Goals / UI  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
Reserve Fund goals (e.g., Emergency funds, Rent cushions) hold money for unexpected or lumpy expenses. When a user consumes money from a Reserve goal, the expense inherently could be standard size (which should hit the monthly budget) or catastrophic (which would destroy the monthly budget). 

Currently, the system either forces all Reserve goal expenses to hit the monthly budget or bypasses them silently, without user input.

### Expected Behavior
At the time of purchase/consumption from a Reserve goal, the UI must prompt the user with a toggle: "Count against monthly category budget?" so the user can decide whether this specific expense should pressure their monthly lifestyle limits.

### Decision
NEW / Investigating.

### Proposed Fix
Implement a toggle in the "Use Reserve" flow (`Savings.jsx`) that asks whether the expense should impact the budget. Pass this flag down to `post_expense_event` so it can respect `enforce_monthly_budget_limits` based on user intent.

---

## EC-147: Fund Project Goal Missing from UI Creation Flow

**Status:** NEW  
**Severity:** S2  
**Area:** Goals / Frontend  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
The backend fully supports the `GoalIntent.FUND_PROJECT` intent. However, the frontend `Savings.jsx` file does not list "Fund Project" in the `GOAL_CREATE_CHOICES` array. Users have no way to create a goal designed specifically to graduate into an isolated project.

### Expected Behavior
Users should see a 4th option, "Project fund" (or similar), when creating a goal, allowing them to accumulate money that will eventually be graduated into a project stash.

### Decision
NEW / Investigating.

### Proposed Fix
Add `FUND_PROJECT` to the `GOAL_CREATE_CHOICES` array in `Savings.jsx` and ensure it behaves correctly during the goal creation wizard.

---

## EC-148: Fund Project Graduation Action Missing from UI Cards

**Status:** NEW  
**Severity:** S2  
**Area:** Goals / Frontend  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
The `useGraduateGoalMutation` exists in `useGoalsMutations.js` and the backend `/{goal_id}/graduate` endpoint exists. However, `Savings.jsx` never imports the hook, nor does it render a "Graduate" button on `FUND_PROJECT` goal cards. 

### Expected Behavior
When a `FUND_PROJECT` goal has accumulated enough funds, the user should be able to click a "Graduate to Project" button on the card, opening a dialog to convert the goal into an isolated project and release the stash.

### Decision
NEW / Investigating.

### Proposed Fix
Wire up the `useGraduateGoalMutation` in `Savings.jsx`. Add a "Graduate" action button to the card that triggers the project creation/graduation flow.

---

## EC-149: Goal Graduation Backend Endpoint is Unsafe and Fails to Update Goal Status

**Status:** NEW  
**Severity:** S1  
**Area:** Goals / Backend API  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
The `/{goal_id}/graduate` API endpoint is designed to convert a `FUND_PROJECT` goal into an isolated project. However, the endpoint currently lacks an intent check, allowing a user to bypass UI rules and graduate *any* goal type (Reserve, Planned Purchase, Pay Obligation) into a project. Furthermore, once graduated, the endpoint does not update the `goal.status` to `GRADUATED`, leaving the goal active and open to further unintended allocations.

### Expected Behavior
The graduation endpoint should:
1. Reject any request where `goal.intent != GoalIntent.FUND_PROJECT` with a 400 Bad Request.
2. Automatically update the goal's status to `GoalStatus.GRADUATED` upon successful graduation, preventing further mutations on the goal side.

### Decision
NEW / Investigating.

### Proposed Fix
In `goals.py` `graduate_goal_to_project`, add the explicit intent validation check, and set `goal.status = models.GoalStatus.GRADUATED` before calling `db.commit()`.

---

## EC-150: Goal-Funded Isolated Projects Render Filling Progress Bars Instead of Depleting Stash

**Status:** NEW  
**Severity:** S3  
**Area:** Budgets / UI  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
According to PRD G7, Isolated Projects with a stash (Goal-funded) should "tick down" visually, starting full and draining as expenses are recorded against them. The hero number ("Available funding now") correctly ticks down, but the progress bars in `Budgets.jsx` render as filling bars (ticking up) toward 100%.

### Expected Behavior
Progress bars for goal-funded isolated projects should start at 100% and tick down toward 0% as the `remaining_funding` is depleted, visually representing a dwindling stash. Direct isolated projects (without a goal) correctly tick up as they represent a bounded spending cap without a pre-funded stash.

### Decision
NEW / Investigating.

### Proposed Fix
Update the progress bar math and styling in `Budgets.jsx` for the `isGoalFundedIsolated` path to reverse the visual direction, rendering a depleting bar.


---

## EC-151: Auto-Reimbursement Logic Creates User Confusion and Messy Ledger States

**Status:** NEW  
**Severity:** S1  
**Area:** Goals / Ledger / Backend  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
Historically, if a user paid for a goal from a wallet that did not fund the goal, the system attempted to generate automatic "reimbursement" transfers from the funding wallets to the payment wallet (e.g., `_settle_goal_funding_to_payment_wallets`). 

### Expected Behavior
The auto-reimbursement idea is rejected. It creates excessive, confusing auto-generated ledger entries that muddy the user's financial history. Instead, the system relies on a two-pronged philosophy:
1. **Pre-purchase:** The user uses the "Prepare Payment" UI to manually move funds to the intended payment wallet *before* buying.
2. **Post-purchase:** If the user already paid from a non-funding wallet, the system uses goal-specific fallback workflows (see EC-152) to release funds or record off-goal expenses, without ever generating automatic wallet-to-wallet transfers.

### Decision
NEW / Investigating.

### Proposed Fix
Identify and rip out any remaining auto-reimbursement or automatic transfer logic in the backend (like `_settle_goal_funding_to_payment_wallets`). 

---

## EC-152: Handling Off-Funding-Wallet Payments by Goal Type

**Status:** NEW  
**Severity:** S1  
**Area:** Goals / UI / Expense Routing  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
When a user bypasses "Prepare Payment" and makes a purchase from a wallet that did not fund the goal, the system must handle the expense according to the specific goal intent, without using auto-transfers.

### Expected Behavior
The system must provide fallback UX workarounds for each intent:
1. **Planned Purchase:** Already has a workaround UI (`ACHIEVED_OUTSIDE_RESERVED_FUNDS`). The expense hits the monthly budget, and the reserved funds remain locked until the user manually unreserves them (returning them to free balance).
2. **Reserve Fund:** Needs a similar workaround UI. If a user paid for a reserve need from a non-funding wallet, they record the expense, explicitly toggle if it hits the monthly budget (see EC-146), and the system releases the reserved funds to free balance (since the actual reserve cash wasn't used).
3. **Fund Project (Isolated):** If an expense is recorded for an isolated project from a non-funding wallet, the system should allow the expense to post against the project limit, and explicitly release the corresponding amount of goal stash back into the user's free balance.
4. **Pay Obligation:** Similar to Planned Purchase, if paid from a non-funding wallet, the debt is reduced, the expense hits the budget, and the reserved funds remain locked until the user returns them manually.

### Decision
NEW / Investigating.

### Proposed Fix
Map out and enforce these strict off-wallet payment rules in the UI and backend, ensuring no auto-transfers are triggered and the monthly budget is correctly impacted when the workaround is used.


---

## EC-153: The Unified Goal Payment Workaround Pattern (Overrides EC-151/152)

**Status:** NEW  
**Severity:** S1  
**Area:** Goals / UI / Expense Routing  
**Discovered on:** 2026-06-15  
**Reported by:** User / AI Agent  

### Scenario
When a user bypasses "Prepare Payment" and makes a purchase from a wallet that did not fund the goal, the system must follow a unified workaround pattern instead of the incorrect assumptions listed in EC-152. 

### Expected Behavior
For all three main intents (Planned Purchase, Reserve Fund, Fund Project), the UX flow is identical:
1. User goes to the goal and says "I already bought this / used this".
2. System records the expense with the correct budget rule per intent.
3. System explicitly releases the equivalent funds from the goal's funding wallet(s) back to Free Money.
4. No auto-transfers, no ghost transactions.

The budget rules differ by intent:
- **Planned Purchase:** `Hit Monthly Budget = False`. It is a pre-planned CapEx, and the financial impact was already absorbed when saving.
- **Reserve Fund:** `Hit Monthly Budget = Toggle`. It is a real unexpected OpEx, and the budget needs visibility, but the user must be given a toggle to opt out if the expense is catastrophic. (Restores the toggle idea from EC-146).
- **Fund Project:** `Hit Monthly Budget = False`. It is isolated by design, as the money was graduated into a stash.

### Decision
NEW / Investigating.

### Proposed Fix
1. Fix the dead `enforce_monthly_budget_limits` flag in `post_expense_event` so it actually works.
2. Add the "already paid" UI flow for Reserve Fund goals (releasing funds, hitting budget).
3. Add the "already paid" UI flow for Fund Project goals (releasing stash, bypassing budget).
4. Update Planned Purchase's `ACHIEVED_OUTSIDE_RESERVED_FUNDS` flow to ensure it correctly bypasses the monthly budget by passing the fixed flag.

---

## EC-154: Onboarding Must Use A Guided Quest Log Approach

**Status:** NEW
**Severity:** S4
**Area:** UI / Onboarding
**Discovered on:** 2026-06-16
**Reported by:** AI Agent

### Scenario

New users signing up for Sarflog face a massive abstraction cliff if presented with a generic wizard or form to setup their budget. Because Sarflog relies on a strict sequence of constraints (Wallets -> Goals -> Inflows -> Budgets), asking them to budget first results in Over-Planned errors, and hiding the UI in a wizard results in a lack of muscle memory (the YNAB problem).

### Expected Behavior

Onboarding should use an interactive Product Tour / Quest Log widget that directs the user to interact with the actual UI elements to build spatial memory. The correct sequence of quests must be:
1. **Reality Check**: Add a Wallet with real balance (establishes Free Money).
2. **Protections**: Create and fund a Goal or declare a Debt (locks money).
3. **Horizon**: Add an Expected Inflow or Recurring Expense (generates floors).
4. **Macro Plan**: Complete the Month Setup Wizard using Smart Auto-Fill based on the above.

### Why This Matters

Prevents early churn by avoiding overwhelming forms, prevents immediate system errors (Over-Planned), and builds long-term usage habits by teaching the actual geography of the application instead of abstracting it away.

### Decision

Defer. This is a high-level UI/UX architectural note for the future onboarding implementation phase.

---

## EC-155: Guided Tour Final Step Must Force Plan From Scratch

**Status:** NEW
**Severity:** S3
**Area:** UI / Onboarding / Budgets
**Discovered on:** 2026-06-17
**Reported by:** User / AI Agent

### Scenario

When a brand new user reaches the final step of the Guided Quest Log onboarding, they are directed to the Month Setup Screen to create their first budget.

### Expected Behavior

The Month Setup Screen must automatically default to Option 1: Plan from scratch (an empty spreadsheet draft) and hide/disable the Copy Previous Month and Smart Auto-fill options. Since the user has no prior months, offering these options is confusing and technically invalid.

### Why This Matters

Presenting history-dependent features to a user with zero history breaks trust and creates UI clutter. Defaulting to Plan From Scratch guarantees a seamless transition from the onboarding tour into their first budgeting session.

### Decision

Defer. This behavior must be integrated when building out G6/G22 onboarding flows.

---

## EC-156: Overlay Multi-Month Slicing and Rollover Eradication

**Status:** NEW  
**Severity:** S1  
**Area:** Projects / Budgets  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

User creates a project spanning multiple months (e.g., June 28 - July 5). They set a limit of 1M Transport. They then delay the trip entirely to July. Or, they finish the trip under budget on July 5 and delete/complete the project.

### Expected Behavior

- Overlay limits must be explicitly sliced per month (e.g., 200k June, 800k July). These act as Category Floors.
- Delaying a trip migrates the slices. A slice cannot be shrunk below `actual_spent`.
- Deleting/Completing a cross-month project after a month boundary has passed flushes the unspent limit back to the *origin month* (e.g., the 200k flushes back to June). This honors G12 (Eradicate Budget Rollovers) by not artificially inflating July's budget.

### Why This Matters

Treating limits globally causes temporal paradoxes. Slicing limits explicitly enforces the monthly envelope math and prevents fake money from rolling over into future months.

### Decision

Fix now. Implement Month-Scoped limits for projects (G24).

---

## EC-157: Overlay Subcategory Global Inheritance

**Status:** NEW  
**Severity:** S2  
**Area:** Projects / Budgets  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

User allocates 1M to Transport for a project. They want to set a 500k "Taxi" subcategory limit inside the project. However, the global monthly budget has no "Taxi" subcategory limit set up.

### Expected Behavior

The system intercepts the action and prompts: "You do not have a 'Taxi' subcategory limit in your global budget. Create it now so this project can inherit from it?" 100% of the project's subcategory limit must map to a global subcategory limit.

### Why This Matters

Allows strict inheritance. Prevents the "Orphaned Intent Trap" (G21) where users create custom text strings for project subcategories that break global reporting.

### Decision

Fix now. Subcategories strictly inherit from Global Budgets (G25).

---

## EC-158: Overlay Multi-Project Collision & Overbooking

**Status:** NEW  
**Severity:** S1  
**Area:** Projects / Budgets  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

August Global Transport Limit is 10M. User creates 3 projects reserving a total of 9M Transport for August. User attempts to create a 4th project reserving 2M Transport for August.

### Expected Behavior

System issues a Hard Block (Option A). "You only have 1M of unreserved Transport limit left in August. You cannot reserve 2M." The user must either reduce the project ambition or proactively reallocate (G14) their global budgets.

### Why This Matters

Allowing overbooking creates "fantasy plans" that violate the strict realism check of the app. Projects cannot silently inflate global budget limits.

### Decision

Fix now. Enforce global headroom validation on project limit creation (G25).

---

## EC-159: Overlay vs Global Overspending Consequences

**Status:** NEW  
**Severity:** S1  
**Area:** Projects / Expenses / Budgets  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

Global Transport is 4M. Project Transport reservation is 1M. General bucket has 3M. 
User spends 1.5M on the project. The project goes RED (1.5M / 1M).

### Expected Behavior

Because the total spent is 1.5M / 4M, the Global Transport category stays GREEN. The system allows the real-world expense to save. The consequence is that the user's General Bucket drops from 3M to 2.5M. They "stole" from their own future unreserved limit. If the general bucket was empty, the Global category would go RED, forcing a reallocation.

### Why This Matters

Preserves the reality-first ledger (never blocking an expense) while perfectly modeling the envelope math. The project micro-plan failed, but the macro-plan is safe unless the global limit is breached.

### Decision

Implement as designed. No blockers for project overspending (G24).

---

## EC-160: Overlay Ledger Integrity via Pristine Deletion

**Status:** NEW  
**Severity:** S1  
**Area:** Projects / Budgets  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

User creates a project and reserves 1M. They buy a 50k non-refundable ticket. The trip is canceled. They attempt to "Delete" the project.

### Expected Behavior

The system blocks the hard delete: "This project has 50k of reality attached to it." The user is forced to "Complete" the project early. This triggers an Auto-Sweep: the project's limit shrinks from 1M to 50k (the actual spent), and the remaining 950k reservation is instantly flushed back to the general budget. Hard deletion is only allowed if the project has 0 expenses (Pristine).

### Why This Matters

Erasing a project with expenses orphans the transactions, destroying historical context. The Auto-Sweep safely frees up liquidity while preserving history.

### Decision

Fix now. Enforce pristine deletes and auto-sweep completions (G26).

---

## EC-161: Just-In-Time (JIT) Project Allocation and Future Month Paradox

**Status:** NEW  
**Severity:** S1  
**Area:** Projects / Budgets / Onboarding  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

User creates a 3-month long project (e.g., June 15 - August 15). The Project Wizard previously tried to ask for July and August allocations right now. However, the user has not yet run the Month Setup Wizard (EC-155) for July, meaning they have 0 "Available July Limit" (or worse, the UI tricks them into budgeting money they don't have, breaking the G9 Realism Check).

### Expected Behavior

- **JIT Slicing:** The Project Creation Wizard must only ask for category limits for the *current active month* (June). It completely hides inputs for future unbudgeted months.
- **The Month Setup Hook:** When July 1st arrives and the user runs the standard Month Setup Wizard (EC-155), they establish their July reality using actual Free Money and G16 Category Floors.
- **The Allocation Prompt:** Upon finishing the July Setup, the system detects the active cross-month project and prompts: "You have an active project spanning into July. Would you like to allocate any of your new July limits to it?" The user then slices their *newly minted* July limits into the project, dynamically growing the project's overall scope.

### Why This Matters

This is the ultimate escape hatch from the "Pandora's Box" of future envelope budgeting. It mathematically enforces that a user cannot slice a pie that hasn't been baked yet. It perfectly honors the G9 formula, respects the G16 required floors, and drastically simplifies the Project Creation UI into a single-month view.

### Decision

Fix now. Implement JIT Slicing for Overlay projects and defer future month slicing to the Month Setup Wizard flow (G27).

---

## EC-162: Wallet Goal Collision & Protection Breaches

**Status:** NEW  
**Severity:** S1  
**Area:** Goals / Wallets / Expenses / UI  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

A user has 0 "Free Money" in a wallet, but holds funds protected by active Goals. They make a real-life purchase using that wallet, which drains the wallet balance below the protected amount. The system must process the expense (Reality is King) but cannot silently auto-deduct funds from goals because it cannot guess human intent (e.g., if a user breached multiple goals, which one did they intend to sacrifice?).

### Expected Behavior (The "Resolution Wizard")

The system implements a Hybrid UI approach (Inline Warning + Interception Modal) to force the user to manually balance the ledger before saving.

**Phase 1: Inline Warning (Before Save)**
When the user types the amount and selects the wallet in the Quick Add form, an inline warning appears below the wallet dropdown:
*⚠️ Exceeds Free Cash. This will dip into your protected goals.*

**Phase 2: Interception Modal (On Save)**
When the user clicks Save, a modal intercepts the action. The modal scales based on the complexity of the breach:

#### Scenario A: Single Wallet, Single Goal Breach (The "AC" Example)
*Real-world case:* User has 3M Cash protected for a "PS Goal". They use 5M Cash to buy an AC.
*Modal UI:*
> **⚠️ Protected Funds Warning**
> You only have 2M of Free Cash. This 5M expense will consume the 3M you saved for your **PS Goal**. 
> 
> **[Consume PS Funds & Save]** *(Primary Button - Red)*
> **[Cancel]** *(Secondary Button - Grey)*

#### Scenario B: Single Wallet, Multi-Goal Breach (The "Groceries" Example)
*Real-world case:* User has 5M Cash protected across 3 goals (Phone 1M, Laptop 2M, Vacation 2M). They spend 2M Cash on random Groceries.
*Modal UI:*
> **⚠️ Multiple Protections Breached!**
> This 2M expense leaves your Cash wallet with only 3M, but you have 5M protected across 3 goals. You must choose which goals to sacrifice to cover the 2M difference:
> 
> 📱 **Phone Goal** (1M protected) ------ Reduce by: `[ 0 ]`
> 💻 **Laptop Goal** (2M protected) ----- Reduce by: `[ 0 ]`
> 🏖️ **Vacation Goal** (2M protected) --- Reduce by: `[ 0 ]`
> 
> *Remaining to resolve: 2M* 
> 
> **[Save & Release Funds]** *(Disabled until Remaining hits 0)*
> **[Cancel]**

#### Scenario C: Multi-Wallet, Multi-Goal Breach (The "Massive TV" Example)
*Real-world case:* User buys a 4M TV, split 2M Cash and 2M Debit. Both wallets have 0 Free Money and multiple goals attached. Both wallets are breached.
*Modal UI (Grouped by Wallet):*
> **⚠️ Multiple Wallets Breached!**
> 
> 💵 **Cash Wallet (Needs 2M resolved):**
> 📱 Phone (1M) -------- Reduce by: `[ 1M ]`
> ⌚ Watch (1M) -------- Reduce by: `[ 1M ]`
> 👕 Clothes (1M) ------ Reduce by: `[ 0 ]`
> *(Cash Remaining to Resolve: 0)*
> 
> 💳 **Debit Wallet (Needs 2M resolved):**
> 🚗 Car (2M) ---------- Reduce by: `[ 2M ]`
> 🎮 PS (1M) ----------- Reduce by: `[ 0 ]`
> 🏖️ Vacation (1M) ----- Reduce by: `[ 0 ]`
> *(Debit Remaining to Resolve: 0)*
> 
> **[Save & Release Funds]** *(Lights up only when BOTH counters hit 0)*

### Why This Matters

This "Ask the Human" fallback prevents the system from making dangerous assumptions about goal priorities, prevents silent data corruption, and ensures the user takes absolute ownership of their financial trade-offs.

### Decision

Fix now. Implement the Hybrid Warning and Resolution Wizard flow for all expense creation/update routes.

---

## EC-163: Goal Fulfillment Interceptor vs. Protection Breach

**Status:** NEW  
**Severity:** S2  
**Area:** Expenses / Goals / UX  
**Discovered on:** 2026-06-17  
**Reported by:** User / AI Agent  

### Scenario

A user has saved money for a Goal (e.g., 20M for a Laptop). They purchase the laptop but carelessly use the generic "Quick Add" expense form instead of the dedicated "Goal Fulfillment" tab. Because the system sees a generic 20M expense draining the wallet, it mathematically triggers the "Protection Breach" warning (EC-162), panicking the user who thinks they are doing exactly what they saved for.

### Expected Behavior (The "Two-Layer Defense")

**Layer 1: Dedicated Goal UI Tab**
The Quick Add modal provides a segmented control: `[ Normal Expense ] | [ Goal / Debt Payment ]`. Organized users can click the Goal tab to perfectly pre-fill and consume protected funds without warnings.

**Layer 2: The Smart Interceptor (Fuzzy Matching)**
For careless users who stay on the `Normal Expense` tab, the system runs a pre-save check *before* triggering any Protection Breach warnings. 
- The system checks if the expense amount matches (or is very close to) an active Goal's protected amount within that wallet, or if the Title/Category matches the Goal's name.
- If a match is detected, the system intercepts the save with a helpful prompt:
  > **🎯 Goal Match Detected!**
  > You are recording a 20M expense for "Macbook". You currently have a **Laptop Goal** with 20M saved in this wallet. Did you finally buy it?
  > **[Yes, link to Laptop Goal & Complete It]** 
  > **[No, this is a random purchase. Save normally]** 

### Why This Matters

This interceptor acts as a smart filter. If the user clicks "Yes", the system retroactively converts the generic expense into a Goal Fulfillment, consuming the protected funds cleanly. If they click "No", the system proceeds to the standard EC-162 Protection Breach flow. This completely solves the "Careless User" problem while keeping the underlying mathematical protections flawless.

### Decision

Fix now. Implement the Hybrid UX (Dedicated Tab + Smart Interceptor) for all Quick Add flows to gracefully handle careless goal fulfillments.
