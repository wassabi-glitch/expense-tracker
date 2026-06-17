# Expense Model

This is my current understanding of the **expense architecture** from:

- `app/models.py`
- `app/routers/expenses.py`
- `app/schemas.py`

I am writing this from the code, not from UI assumptions. If I misunderstand anything, correct this file and I will align the frontend to the corrected model.

---

## 1. Core philosophy

The real expense system is **event-ledger based**, not “one expense row = one wallet + one category”.

The core object is:

- `FinancialEvent`

Then that event fans out into two different ledger layers:

- `WalletLedger`
  - how money moved across wallet(s)
- `EntityLedger`
  - how the event was allocated across category / budget / subcategory / project / debt / income source

So the backend philosophy is:

- one real-world thing happened
- money movement is one concern
- planning / classification / relationships are another concern

That is a strong 3-pillar idea:

1. `FinancialEvent`
2. `WalletLedger`
3. `EntityLedger`

---

## 2. Main expense tables

### `FinancialEvent`

This is the parent event.

Relevant fields:

- `title`
- `description`
- `event_type`
- `is_session`
- `discount_amount`
- `linked_event_id`
- `merge_group_id`
- `date`

Meaning:

- `event_type`
  - tells whether this is an `EXPENSE` or `REFUND` event
- `is_session`
  - tells whether this event came from Basket/Session mode
- `linked_event_id`
  - used for event relationships like refund -> original expense
- `merge_group_id`
  - links this event into a merge group

### `WalletLedger`

This is the wallet-side money movement.

Relevant fields:

- `event_id`
- `wallet_id`
- `amount`

Meaning:

- negative amount = outflow from wallet
- positive amount = inflow into wallet

### `EntityLedger`

This is the planning / allocation / semantic side.

Relevant fields:

- `label`
- `amount`
- `original_amount`
- `category`
- `subcategory_id`
- `project_id`
- `budget_id`
- `debt_id`
- `income_source_id`

Meaning:

- this is where the event gets attached to:
  - category
  - parent budget
  - optional subcategory
  - optional project
  - optional debt relation
  - optional income source relation

This is why one event can become:

- a simple expense
- a split expense
- a session event with multiple item legs
- a merged historical context entry

---

## 3. What the current `GET /expenses` output means

`ExpenseOut` is already richer than old-style CRUD.

It includes:

- `wallet_allocations`
- `split_items`
- `merge_group_id`
- `merge_group_title`
- `is_session`
- `is_split`
- `asset_id`
- refund state fields:
  - `has_refund`
  - `refunded_amount`
  - `is_partially_refunded`
  - `is_fully_refunded`

So even the list endpoint is already admitting:

- one event may involve multiple wallets
- one event may involve multiple item legs
- one event may belong to a merge group
- one event may have asset linkage
- one event may have refund lifecycle

This means the frontend should not flatten the page back into:

- one expense = one row with one wallet

---

## 4. Current creation routes vs core architecture

This is the part that needs the most clarity.

### `POST /expenses/`

The current simple create route still behaves like a **legacy simple entry route**.

It accepts:

- `title`
- `amount`
- `category`
- `description`
- `date`
- `wallet_id`
- `subcategory_id`
- `project_id`
- optional `splits`

Important:

- it still resolves **one wallet**
- then calls `WalletService.record_transaction(...)`
- then updates the primary entity leg with optional subcategory / project

So today, in code reality:

- simple create is still a **single-wallet** entry route
- but the wider architecture is not single-wallet

That distinction matters.

### Basket / Session routes

The session flow is much closer to the deeper architecture.

It has:

- session draft header
- item rows
- wallet allocations
- split rows
- finalize into real event

That is where:

- multi-wallet
- multi-item
- richer grouped event capture

are implemented much more honestly right now.

---

## 5. Session / Basket model

There is a real session draft domain:

- `ExpenseSessionDraft`
- `ExpenseSessionDraftItem`
- `ExpenseSessionDraftWalletAllocation`
- `ExpenseSessionDraftSplit`

### `ExpenseSessionDraft`

Represents an in-progress grouped expense capture session.

Fields include:

- `title`
- `description`
- `date`
- `amount_paid`
- `status`
- `source_type`
- `finalized_event_id`

### `ExpenseSessionDraftItem`

Represents item-level spending inside the session.

Fields include:

- `label`
- `original_amount`
- `category`
- `subcategory_id`
- `project_id`
- `sort_order`

So session items already support:

- category
- subcategory
- project

at the item level.

### `ExpenseSessionDraftWalletAllocation`

Represents how the paid amount was split across wallets.

Fields:

- `wallet_id`
- `amount`

This is the clearest evidence that the expense architecture is not truly “single wallet only”.

### `ExpenseSessionDraftSplit`

Represents person-based split rows:

- `contact_name`
- `amount`

Meaning:

- “I paid 300k, but 100k belongs to Ali and 50k belongs to Sara”

---

## 6. Merge model

There is a real merge feature:

- `ExpenseMergeGroup`

Routes exist for:

- create merge group
- list merge groups
- get merge group
- update merge group
- add expenses to merge group
- remove expense from merge group
- delete merge group

This means merge is not just a visual tag.

It is a real organizational object with:

- title
- description
- child events
- refunded totals
- net amount

### Real-world example

You have 4 separate recorded expenses:

- Bread
- Meat
- Taxi home
- Paint thinner

Later you realize:

- “All of these belonged to Sunday Market Run”

You merge them into one merge group:

- `Sunday Market Run`

This does **not** rewrite accounting type.
It adds a contextual grouping layer.

---

## 7. Refund model

Refunds are not just flags.
They are real events.

Refund route:

- `POST /expenses/{id}/refund`

This creates a new `FinancialEvent` of type `REFUND` linked to the original expense.

Important rules:

- refund amount cannot exceed remaining refundable amount
- refund can target another wallet
- refund title becomes:
  - `Refund`
  - or `Partial Refund`

This means refund is a lifecycle event, not just a boolean.

### Real-world example

Original:

- Headphones
- 500k
- paid from Debit

Then store returns 200k to Cash.

Backend truth:

- original expense remains
- new refund event is created
- wallet inflow goes into Cash
- original expense becomes partially refunded

---

## 8. Split expense model

There are two different meanings of “split”.

### A. Friend / people split on simple create

Simple create route accepts `splits`.

That creates `Debt` rows, not `EntityLedger` item legs.

Meaning:

- “I paid for friends and they owe me back”

This is social / debt split.

### B. Allocation split route

There is also:

- `POST /expenses/{id}/split`

This rewrites the event’s `EntityLedger` rows into multiple item lines.

This is planning / allocation split.

It requires:

- total split amount must exactly match the event amount
- event must not be refund-locked
- event must be compatible with simple split handling

### Real-world example

Original:

- `Supermarket`
- 300k
- category `Groceries`

Then you split into:

- `Meat` 180k
- `Dairy` 70k
- `Vegetables` 50k

Now one expense event still exists, but the planning legs are itemized.

---

## 9. Mark-as-asset model

Route:

- `POST /expenses/{id}/mark-as-asset`

This creates an `Asset` whose:

- `origin_event_id = expense.id`
- `purchase_value = event amount`
- `current_value` can be overridden

### Real-world example

Expense:

- `Used Laptop`
- 4,000,000

Mark as asset:

- Asset title defaults from expense title
- origin expense remains the source of acquisition

So this is expense -> ownership lifecycle transition.

---

## 10. Mark-as-recurring model

Route:

- `POST /expenses/{id}/mark-as-recurring`

This seeds a recurring template from an existing expense.

Inputs include:

- `frequency`
- `start_date`
- `wallet_id`
- `cycle_behavior`

Important:

- premium required
- archived wallet rejected

### Real-world example

Expense:

- `Internet Bill`
- 120k

Mark as recurring:

- monthly
- start from this due date
- use same or chosen wallet

So this is expense -> recurring template transition.

---

## 11. Merge, refund, asset, recurring, split: expense actions that exist

From route inspection, the main per-expense action family currently includes:

- `View Details`
- `Update`
- `Delete`
- `Refund`
- `Split`
- `Mark as Asset`
- `Mark as Recurring`
- `Merge Group` participation

This is one reason a shallow CRUD action menu is not enough anymore.

---

## 12. Where the frontend still diverges from backend philosophy

This is my current understanding of the mismatch.

### A. Quick Add still reflects old create route too literally

The codebase architecture is event + wallet legs + entity legs.

But the current simple create route still only accepts one wallet.

So there is tension between:

- real architecture direction
- current simple route contract

I need your correction here:

### Question 1

Do you want:

- simple `Quick Add` to stay temporarily single-wallet because backend route still is

or

- simple `Quick Add` to be redesigned immediately around multi-wallet and then backend should be extended to support it directly?

### B. Merge action was missing in the UI

This was a real miss on my side.

Merge is definitely part of the expense action system and should be represented.

### C. Detail views matter more now

Because one expense can carry:

- wallet allocations
- split items
- merge context
- refund lifecycle
- asset linkage
- project/subcategory planning context

the list card should stay shallow and details should explain the full structure.

---

## 13. Real-world examples

### Example 1: Simple one-wallet expense

- Coffee
- 30k
- wallet: Cash
- category: Dining Out

Result:

- 1 `FinancialEvent`
- 1 `WalletLedger` outflow
- 1 `EntityLedger` category allocation

### Example 2: Same event, planning split

- Groceries
- 300k
- one wallet
- split into Meat / Dairy / Vegetables

Result:

- 1 `FinancialEvent`
- 1 wallet leg
- multiple entity legs

### Example 3: Session with multiple wallets

- Sunday Shopping
- items:
  - Bread
  - Coke
  - Football
- wallets:
  - Cash 80k
  - Debit 120k

Result:

- session draft objects first
- then finalized into one expense event
- multiple wallet legs
- multiple entity legs

### Example 4: Refund

- buy headphones for 500k
- receive 200k refund

Result:

- original expense event
- separate refund event linked back

### Example 5: Merge

- Bread
- Meat
- Taxi

Later grouped into:

- `Sunday Market Run`

Result:

- original events still exist
- merge group adds contextual layer

---

## 14. My current working conclusion

My current understanding is:

- **Expense architecture is event-based**
- **wallet movement and planning allocation are deliberately separated**
- **session mode already reflects the richer architecture better than simple create**
- **merge is a real organizational action, not just UI sugar**
- **refunds, asset conversion, recurring conversion, and split are all first-class lifecycle actions**

The main thing I still need your clarification on is:

- whether you consider the current simple create route a temporary legacy shim
- or whether you still want `Quick Add` to remain intentionally simpler than Session even long term

