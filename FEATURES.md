v1:
1.Goals
2.Payment integration
3.Notification system
4.Settings page refinement
5.Responsive UI refactor
6.Deployment

Roadmap v2:
1. Debts&Installments tracking
2. Recurring goal contributions and goals linked with expense creation
3. Custom categories & capped rollover
4. Receipt scanning
5. Natural language input & voice input
6. Premade templates for common expenses
7. Smart Insights & more analytics
8. Better onboarding and guidance
9. Shared wallets
10. Multi currency support
11. Subscription payment



Roadmap
Rule: maximum 2 concurrent feature tracks at any time.

Now → May 31
Track 1: Stabilization/tests for current system
Track 2: Multi-currency planning only

Output: bug fixes, test coverage, final multi-currency architecture document.

June 1 → June 14
Track 1: Multi-currency foundation
Track 2: Premade expense templates

Reason: templates are low-risk and mobile-friendly while multi-currency is deep backend work.

June 15 → June 30
Track 1: Mobile app foundation
Track 2: Better onboarding/guidance

Reason: onboarding should be designed together with mobile because your app is conceptually heavy.

July 1 → July 21
Track 1: Receipt scanning
Track 2: Continue mobile core screens

Receipt scanning should create ExpenseSessionDraft, not final expenses directly.

July 22 → August 5
Track 1: Smart insights + analytics
Track 2: Production hardening

Wait until multi-currency is stable because analytics depends on correct base-currency values.

August 6 → August 20
Track 1: Natural language input
Track 2: Voice input / mobile polish

Natural language and voice should also create drafts first, not final financial events directly.

Best Build Sequence

Current system stabilization
Multi-currency
Premade templates
Mobile foundation
Better onboarding/guidance
Receipt scanning
Smart insights
Natural language input
Voice input
Final production hardening
My recommendation: do not run multi-currency, receipt scanning, and mobile all at once. Keep concurrency to one deep architecture feature plus one lighter UX/product feature.


Stabilization:
1. Expenses & Recurring(3days 23rd May deadline)
2. Budgets & Projects & Goals&Savings & Wallets(4days 27th May deadline)
3. Income (2days 29th deadline)
4. Debts & Installments(2days 31st deadline)
5. Assets(2days 2nd June deadline)




















**100% YES. GPT nailed it.**

This is actually **THE** architectural insight that makes everything click.

---

## Why This Pattern Is So Powerful

### The Problem Most Finance Apps Have:

```
Manual entry → direct to database
Bank sync → direct to database  
OCR → direct to database
Voice → direct to database

Result: 
- No consistency
- No review step
- Mistakes become permanent
- No deduplication
- User has no control
```

**That's the "wild monster" — each feature is its own beast.**

---

### Your Pattern (The "Trained Monster"):

```
┌─────────────────────────────────────────────┐
│         INPUT PROVIDERS                     │
│  (External, potentially messy/wrong)        │
├─────────────────────────────────────────────┤
│  • Manual typing                            │
│  • Bank sync transaction                    │
│  • OCR receipt scan                         │
│  • Voice command                            │
│  • CSV import                               │
│  • Session basket                           │
│  • Split from friend                        │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│       CANDIDATE/DRAFT LAYER                 │
│    (Unconfirmed, reviewable)                │
├─────────────────────────────────────────────┤
│  • Draft expense                            │
│  • Draft session                            │
│  • Synced transaction (unmatched)           │
│  • OCR extraction                           │
│  • Voice parse result                       │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│       REVIEW/MATCH/CONFIRM LAYER            │
│    (Human-in-the-loop decision)             │
├─────────────────────────────────────────────┤
│  • User confirms draft                      │
│  • User edits category/project              │
│  • User matches to existing expense         │
│  • User marks as duplicate                  │
│  • User splits/merges                       │
│  • Auto-confirm if confidence high          │
└─────────────────┬───────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│       FINAL FINANCIAL RECORDS               │
│    (Immutable truth, locked)                │
├─────────────────────────────────────────────┤
│  • Confirmed expense                        │
│  • Wallet balance updated                   │
│  • Budget usage recorded                    │
│  • Project tracking updated                 │
│  • Timeline/analytics fed                   │
└─────────────────────────────────────────────┘
```

**This is elegant as fuck.**

---

## Why This Architecture Wins

### 1. **Consistency Across All Features**

Every input source follows the same flow:

```javascript
// Manual entry
createDraftExpense(manualInput) 
  → userConfirms() 
  → finalizeExpense()

// Bank sync
createDraftExpense(bankTransaction) 
  → userReviewsAndMatches() 
  → finalizeExpense()

// OCR
createDraftExpense(ocrExtraction) 
  → userEditsAndConfirms() 
  → finalizeExpense()

// Voice
createDraftExpense(voiceParse) 
  → userConfirms() 
  → finalizeExpense()
```

**Same finalization logic. Same validation. Same wallet updates. Same budget tracking.**

**You write it ONCE, it works for ALL inputs.**

---

### 2. **Protection Against Errors**

```
OCR thinks "Coffee - 450k" 
  → Draft: 450,000 UZS
  → User sees it: "WTF that's wrong"
  → User edits: 4,500 UZS
  → Confirms
  → Financial truth is correct

Bank sync imports "KORZINKA 300k" as "Entertainment"
  → Draft with wrong category
  → User reviews: "No, that's Groceries"
  → User fixes category
  → Confirms
  → Budget tracking is accurate
```

**Mistakes stay in draft layer. Financial truth is protected.**

---

### 3. **Deduplication Works Naturally**

```
User manually logs: "Coffee 15k" at 2:30pm

Bank sync imports: "COFFEE SHOP 15000" at 2:30pm

Draft layer detects:
  - Same amount
  - Same time (within 5 min)
  - Similar merchant

Shows user:
  "This looks like your manual entry. Match them?"
  [Yes - link them] [No - separate expense]

User clicks Yes
  → Manual expense gets sync_transaction_id
  → Draft is discarded
  → No duplicate in final records
```

**Deduplication happens in review layer, not as complex DB logic.**

---

### 4. **Confidence-Based Automation**

You can still be smart about when to skip review:

```javascript
function shouldAutoConfirm(draft) {
  // High confidence criteria
  if (draft.source === 'manual') return true;  // user typed it
  
  if (draft.source === 'bank_sync') {
    // Auto-confirm if matches known pattern
    if (draft.merchant === 'Netflix' && draft.amount === 49000) {
      return true;  // recurring subscription, same amount
    }
    
    if (draft.category_confidence > 0.95) {
      return true;  // AI is very confident
    }
  }
  
  return false;  // needs review
}

// In your code
const draft = createDraftFromBankSync(transaction);

if (shouldAutoConfirm(draft)) {
  finalizeExpense(draft);  // skip review
} else {
  addToReviewQueue(draft);  // user must confirm
}
```

**Smart automation where appropriate, human review where needed.**

---

## The Database Schema That Supports This

### Draft Table

```sql
CREATE TABLE expense_drafts (
  id SERIAL PRIMARY KEY,
  
  -- Source tracking
  source TEXT NOT NULL,  -- 'manual', 'bank_sync', 'ocr', 'voice', 'session'
  source_id TEXT,         -- external ID (bank transaction ID, OCR job ID, etc.)
  
  -- Draft data (same fields as expenses)
  title TEXT,
  amount DECIMAL,
  wallet_id INT,
  category_id INT,
  subcategory_id INT,
  expense_date DATE,
  
  -- Review state
  status TEXT DEFAULT 'pending_review',  -- 'pending_review', 'confirmed', 'rejected', 'matched'
  confidence FLOAT,       -- AI confidence score
  matched_expense_id INT, -- if matched to existing expense
  
  -- Metadata
  created_at TIMESTAMP,
  reviewed_at TIMESTAMP,
  reviewed_by_user_id INT
);
```

### Confirmed Expenses Table

```sql
CREATE TABLE expenses (
  id SERIAL PRIMARY KEY,
  
  -- Financial data (immutable once confirmed)
  title TEXT NOT NULL,
  amount DECIMAL NOT NULL,
  wallet_id INT NOT NULL,
  category_id INT,
  subcategory_id INT,
  expense_date DATE NOT NULL,
  
  -- Source tracking (where did this come from?)
  source TEXT,            -- 'manual', 'bank_sync', 'ocr', 'voice'
  source_draft_id INT,    -- links back to draft
  sync_transaction_id TEXT, -- bank transaction ID if synced
  
  -- Confirmation metadata
  confirmed_at TIMESTAMP NOT NULL,
  confirmed_by_user_id INT NOT NULL,
  
  -- Locked after creation (title/description editable only)
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

## The Code That Powers This

### Universal Draft Creator

```javascript
async function createDraft(source, data) {
  // Normalize input from any source
  const draft = {
    source: source,  // 'manual', 'bank_sync', 'ocr', etc.
    source_id: data.externalId,
    title: cleanTitle(data.title || data.description),
    amount: parseAmount(data.amount),
    wallet_id: data.walletId,
    category_id: await detectCategory(data),  // AI categorization
    expense_date: data.date || new Date(),
    confidence: data.confidence || 1.0,  // manual = 100% confidence
    status: 'pending_review'
  };
  
  // Check for duplicates
  const possibleMatch = await findSimilarExpense(draft);
  if (possibleMatch) {
    draft.matched_expense_id = possibleMatch.id;
    draft.status = 'needs_matching_decision';
  }
  
  // Save draft
  return await db.expense_drafts.create(draft);
}
```

---

### Universal Finalizer

```javascript
async function finalizeExpense(draft, userEdits = {}) {
  // Merge user edits with draft
  const finalData = {
    ...draft,
    ...userEdits,  // user can override anything
    source_draft_id: draft.id,
    confirmed_at: new Date(),
    confirmed_by_user_id: currentUser.id
  };
  
  // Start transaction
  await db.transaction(async (trx) => {
    // Create confirmed expense
    const expense = await trx.expenses.create(finalData);
    
    // Update wallet balance
    await trx.wallets.decrement(finalData.wallet_id, finalData.amount);
    
    // Update budget usage
    if (finalData.category_id) {
      await updateBudgetUsage(trx, finalData);
    }
    
    // Update project tracking
    if (finalData.project_id) {
      await updateProjectSpending(trx, finalData);
    }
    
    // Mark draft as confirmed
    await trx.expense_drafts.update(draft.id, {
      status: 'confirmed',
      reviewed_at: new Date()
    });
    
    // Delete draft after 30 days (audit trail)
    await trx.expense_drafts.scheduleDelete(draft.id, { after: '30 days' });
  });
  
  return expense;
}
```

**ONE finalization function. Works for ALL sources.**

---

## The UI This Enables

### Review Queue Screen

```
┌─────────────────────────────────────┐
│ Review Queue (3)                    │
├─────────────────────────────────────┤
│                                     │
│ 🏦 From Uzum Bank                   │
│ Korzinka - 300,000 UZS              │
│ Suggested: Shopping > Groceries     │
│ [Edit] [Match Existing] [Confirm]  │
│                                     │
├─────────────────────────────────────┤
│                                     │
│ 📸 From Receipt (OCR)               │
│ Samarkand Darvoza - 150,000 UZS     │
│ Suggested: Food > Restaurant        │
│ Confidence: 89%                     │
│ [Edit] [Delete] [Confirm]           │
│                                     │
├─────────────────────────────────────┤
│                                     │
│ 🎤 From Voice                       │
│ "Bought coffee fifteen thousand"    │
│ Coffee - 15,000 UZS                 │
│ Suggested: Food > Coffee            │
│ [Edit] [Confirm]                    │
│                                     │
└─────────────────────────────────────┘

[Confirm All (3)] [Review Later]
```

**Same UI for ALL draft types.**

---

## Why This Is "Trained Monster" Not "Wild Monster"

### Wild Monster (Bad):
```
Each feature has its own:
- Input validation
- Category detection
- Duplicate checking
- Wallet updating
- Budget tracking
- Error handling

= 6 features × 6 subsystems = 36 code paths to maintain
```

### Trained Monster (Good):
```
All features use shared:
- Draft creation layer
- Review/confirmation layer
- Finalization engine

= 6 features × 1 unified pipeline = 6 code paths to maintain
```

**6x reduction in complexity.**

---

## The Philosophy This Embodies

**GPT is absolutely right:**

> "Sarflog is not blindly automated. It is human-in-the-loop finance intelligence."

This is your **brand position**:

- **NOT:** "Fully automated finance tracking"
- **YES:** "Intelligent finance tracking with you in control"

**Users WANT control over their financial data.**

They don't want:
- ❌ "AI categorized this for you (wrongly)"
- ❌ "We imported 50 transactions (half are duplicates)"
- ❌ "OCR found these items (all wrong amounts)"

They want:
- ✅ "We found this. Does it look right?"
- ✅ "This matches your manual entry. Link them?"
- ✅ "We think this is groceries. Confirm or edit?"

**Your architecture enforces this philosophy at the code level.**

---

## What This Means Going Forward

### When You Add New Features:

**Ask:** "Does this produce a draft or final record?"

**If draft:**
```javascript
const draft = await createDraft('new_feature', data);
await addToReviewQueue(draft);
```

**If final:**
```javascript
await finalizeExpense(userConfirmedData);
```

**That's it. New feature integrated.**

---

### Examples:

**Bank Sync (Sept 2026):**
```javascript
// Import transactions
const transactions = await bankApi.getTransactions();

for (const txn of transactions) {
  // Create draft
  const draft = await createDraft('bank_sync', {
    externalId: txn.id,
    title: txn.description,
    amount: txn.amount,
    date: txn.date,
    confidence: 0.7  // needs review
  });
  
  // User reviews in queue
  // User confirms
  // finalizeExpense() handles the rest
}
```

**Voice Input (Future):**
```javascript
// User says: "I spent 50k on lunch"
const parsed = await voiceAPI.parse(audioBlob);

const draft = await createDraft('voice', {
  title: parsed.merchant || 'Lunch',
  amount: parsed.amount,
  category_id: await detectCategory(parsed),
  confidence: parsed.confidence
});

// Show confirmation screen
// User taps confirm
// Done
```

**CSV Import:**
```javascript
// User uploads bank CSV
const rows = parseCsv(file);

for (const row of rows) {
  await createDraft('csv_import', {
    title: row.description,
    amount: row.amount,
    date: row.date
  });
}

// All rows go to review queue
// User bulk confirms or edits
```

---

## The Final Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                  SARFLOG SPINE                      │
└─────────────────────────────────────────────────────┘

INPUT LAYER (Messy, external)
  ├─ Manual entry
  ├─ Bank sync
  ├─ OCR receipt
  ├─ Voice command
  ├─ CSV import
  ├─ Session basket
  └─ Friend split request
           ↓
DRAFT LAYER (Unconfirmed candidates)
  ├─ expense_drafts table
  ├─ Confidence scoring
  ├─ Duplicate detection
  └─ Category suggestion
           ↓
REVIEW LAYER (Human decision)
  ├─ Review queue UI
  ├─ Match/merge/edit options
  ├─ Auto-confirm high-confidence
  └─ User approval required
           ↓
FINALIZATION LAYER (Immutable truth)
  ├─ Create expense record
  ├─ Update wallet balance
  ├─ Record budget usage
  ├─ Track project spending
  └─ Feed analytics
           ↓
PRESENTATION LAYER (User sees results)
  ├─ Timeline view
  ├─ Budget dashboard
  ├─ Wallet balances
  ├─ Project tracking
  └─ Analytics/insights
```

**This is not a monster. This is a machine.**

---

## Bottom Line

**Yes, GPT is 100% right.**

This pattern is **THE architectural foundation** that makes your app scalable, maintainable, and user-friendly.

**Every feature you add plugs into this pipeline.**

**You're not building feature soup.**  
**You're building a coherent ingestion and confirmation engine.**

**That's the difference between a product and a platform.**


## Idea Triage: Savings, Goals, Budgets, Loans, Deposits

Purpose: separate useful architecture ideas from confusing or low-value ones.

### Canonical Diagram: Goals and Savings

Use this mental model:

```text
REAL MONEY LAYER

  +-------------------+      +-------------------+      +-------------------+
  | Cash Wallet       |      | Debit Wallet      |      | Savings Wallet    |
  | balance: 2M       |      | balance: 10M      |      | balance: 5M       |
  +-------------------+      +-------------------+      +-------------------+
            |                          |                          |
            | wallet_id                | wallet_id                | wallet_id
            v                          v                          v

PURPOSE / RESERVATION LAYER

  +--------------------------------------------------------------------------+
  | Goal Allocations                                                         |
  |                                                                          |
  | Laptop Goal:     1M from Cash Wallet + 3M from Savings Wallet            |
  | Emergency Goal:  2M from Debit Wallet                                    |
  +--------------------------------------------------------------------------+
                         |
                         v

GOAL LAYER

  +-------------------+      +-------------------+
  | Laptop Goal       |      | Emergency Goal    |
  | target: 10M       |      | target: 20M       |
  | funded: 4M        |      | funded: 2M        |
  +-------------------+      +-------------------+
```

Key interpretation:

```text
Wallet balance = real money.
Goal allocation = purpose label over real wallet money.
Goal allocation does not move money.
Goal allocation does not create extra money.
```

Per-wallet calculation:

```text
wallet.current_balance = real balance
wallet.allocated_to_goals = sum(goal allocations linked to this wallet)
wallet.unallocated_balance = current_balance - allocated_to_goals
```

Example:

```text
Savings Wallet balance: 5M
Allocated to Laptop: 3M
Unallocated/free: 2M
```

What counts as money:

```text
Total money/net position = wallet balances + assets - debts
Do not count goal allocations as extra money.
```

Wrong:

```text
wallets + goal allocations
```

Right:

```text
wallets explain where money is
goal allocations explain what some of that money is for
```

Savings naming:

```text
Savings Account = real wallet type.
Goal Reserve / Savings Vault = optional virtual planning layer.
```

Preferred future model:

```text
Wallet -> Goal Allocation -> Goal
```

Avoid unless deliberately needed:

```text
Wallet -> Savings Vault -> Goal
```

Goal lifecycle after funding:

```text
purchase_asset     -> create/link Asset
pay_debt           -> repay/link Debt
fund_installment   -> pay/link Installment
fund_project       -> release to/link Project
future_expense     -> create/link Expense
emergency_reserve  -> stays as reserve
general_savings    -> stays as reserve
```

This keeps the layers separate:

```text
Wallet = where money is.
Goal = why money is being saved.
Allocation = which wallet money is assigned to which goal.
Final action = what happens when saved money is actually used.
```

### Current Implementation Diagram: Savings and Goals

This is how the app works right now.

```text
STEP 1: USER DEPOSITS TO SAVINGS

  +-------------------+
  | Real Wallet       |
  | Debit/Cash/etc.   |
  | balance: 10M      |
  +-------------------+
            |
            | POST /savings/deposit 4M
            | wallet balance decreases
            v
  +-------------------+          +-----------------------------+
  | Real Wallet       |          | SavingsTransactions         |
  | balance: 6M       |          | type: DEPOSIT               |
  +-------------------+          | amount: 4M                  |
                                 | wallet_id: source wallet    |
                                 +-----------------------------+
                                                |
                                                v
                                 +-----------------------------+
                                 | Virtual Savings Cloud       |
                                 | free_savings_balance: 4M    |
                                 +-----------------------------+
```

```text
STEP 2: USER CONTRIBUTES TO A GOAL

  +-----------------------------+
  | Virtual Savings Cloud       |
  | free_savings_balance: 4M    |
  +-----------------------------+
              |
              | POST /goals/{id}/contribute 3M
              | no wallet movement here
              v
  +-----------------------------+          +-----------------------------+
  | GoalContributions           |          | Goal                        |
  | type: ALLOCATE              |--------->| Laptop Goal                 |
  | amount: 3M                  |          | funded_amount: 3M           |
  +-----------------------------+          +-----------------------------+
              |
              v
  +-----------------------------+
  | Savings Summary             |
  | free_savings_balance: 1M    |
  | locked_in_goals: 3M         |
  +-----------------------------+
```

```text
STEP 3: USER RETURNS MONEY FROM GOAL

  +-----------------------------+
  | Goal                        |
  | funded_amount: 3M           |
  +-----------------------------+
              |
              | POST /goals/{id}/return 1M
              | no wallet movement here
              v
  +-----------------------------+
  | GoalContributions           |
  | type: RETURN                |
  | amount: 1M                  |
  +-----------------------------+
              |
              v
  +-----------------------------+
  | Savings Summary             |
  | free_savings_balance: 2M    |
  | locked_in_goals: 2M         |
  +-----------------------------+
```

```text
STEP 4: USER WITHDRAWS FROM SAVINGS

  +-----------------------------+
  | Virtual Savings Cloud       |
  | free_savings_balance: 2M    |
  +-----------------------------+
              |
              | POST /savings/withdraw 2M
              | target wallet balance increases
              v
  +-------------------+          +-----------------------------+
  | Real Wallet       |          | SavingsTransactions         |
  | balance: +2M      |          | type: WITHDRAWAL            |
  +-------------------+          | amount: 2M                  |
                                 | wallet_id: target wallet    |
                                 +-----------------------------+
```

Current summary math:

```text
spendable_balance = sum(wallet.current_balance)

free_savings_balance =
  savings deposits
  - savings withdrawals
  - locked_in_goals

locked_in_goals =
  goal allocations
  - goal returns

total_balance =
  spendable_balance
  + free_savings_balance
  + locked_in_goals
```

Current mental model:

```text
Wallet -> Virtual Savings Cloud -> Goal Contribution -> Goal
```

Meaning:

```text
Savings is acting like a virtual wallet-like container.
Goal contributions draw from that virtual Savings container.
Goal contributions do not remember which real wallet the money originally came from.
```

Current model strength:

```text
simple user flow
clear free savings vs locked goals split
works because deposit removes money from spendable wallets
```

Current model weakness:

```text
physical money location becomes unclear after deposit
goal funding is not directly tied to source wallet
Savings can be confused with a real bank savings account
future Savings wallet type may conflict with virtual Savings
```

Comparison:

```text
Current:
Wallet -> Virtual Savings Cloud -> Goal

Preferred future:
Wallet -> Goal Allocation -> Goal
```

Most important difference:

```text
Current model moves money out of wallet into virtual Savings.
Preferred model keeps money in wallet and labels part of it for a goal.
```

### Keep: Wallets vs Goal Allocations

Core rule:

```text
Wallet = where money physically/account-wise exists.
Goal = what the user is saving for.
Goal allocation = virtual purpose label over part of a wallet balance.
```

Important:

```text
Goal allocations do not reduce wallet balance.
Goal allocations reduce unallocated/free balance inside that wallet.
Goal allocations must never be counted as extra money.
```

Best invariant:

```text
sum(goal_allocations for wallet) <= wallet.current_balance
```

If wallet balance later drops below allocations:

```text
wallet is over-allocated
user must reduce allocations or add money back
```

### Keep: Savings Account as Wallet Type

Add a real wallet/account type:

```text
SAVINGS
```

Meaning:

```text
money physically exists in a real savings account
```

This belongs beside:

```text
CASH
DEBIT
CREDIT
PRELOADED
SAVINGS
```

Do not confuse this with the current virtual Savings feature.

### Keep: Rename Virtual Savings Layer

The current Savings feature is closer to:

```text
Goal Reserve
Savings Vault
Reserve Pool
```

It is not a real bank savings account.

Long-term preferred model:

```text
Wallet -> Goal Allocation
```

Instead of:

```text
Wallet -> Savings Vault -> Goal
```

Reason: direct wallet allocations are cleaner and always show where goal money physically sits.

### Keep: Eligible Wallets Can Fund Goals

Goal funding should not be limited only to formal savings accounts.

Real people save through:

```text
bank savings accounts
cash envelopes
cash at home
USD cash
money mentally reserved inside debit cards
separate debit cards used as savings
```

Best model:

```text
wallet.can_fund_goals = true/false
```

Recommended defaults:

```text
Savings account: true
Cash reserve: true
Debit/checking: allowed if user enables it
Preloaded: allowed if user enables it
Credit: false
```

Credit should not fund goals because it is borrowed capacity, not owned saved money.

### Keep: Goal Intent

Goals should support intent so the app knows what a completed goal may become.

Possible goal intents:

```text
purchase_asset
pay_debt
fund_installment
fund_project
future_expense
emergency_reserve
general_savings
```

Rule:

```text
Not every goal must become another object.
Some goals stay as reserves forever.
```

Examples:

```text
Buy Laptop -> may become Asset or Expense
Pay Microloan -> links to Debt
Mortgage Down Payment -> links to Installment/Debt
Wedding -> may become Project
Emergency Fund -> stays as reserve
```

### Keep: Direct Goal Links to Assets, Debts, Installments, Projects

Useful lifecycle links:

```text
Goal -> Asset
Goal -> Debt
Goal -> Installment
Goal -> Project
Goal -> Expense
```

Use direct links when the goal is for one clear outcome:

```text
Pay off loan -> Debt
Mortgage down payment -> Installment/Debt
Buy gold -> Asset
Buy phone -> Expense or Asset
```

Use Project only for broader missions:

```text
Buying Apartment:
- down payment
- mortgage setup
- renovation
- furniture
- document fees
```

Project should group many related costs. It should not be forced into every goal flow.

### Canonical Diagram: Budgeting System

Use this mental model:

```text
REAL MONEY LAYER

  +-------------------+      +-------------------+      +-------------------+
  | Cash Wallet       |      | Debit Wallet      |      | Credit Wallet     |
  | balance: 2M       |      | balance: 10M      |      | balance: -1M      |
  +-------------------+      +-------------------+      +-------------------+
            |                          |                          |
            | pays expense             | pays expense             | pays expense
            v                          v                          v

FINANCIAL EVENT / LEDGER LAYER

  +--------------------------------------------------------------------------+
  | FinancialEvent: Grocery shopping                                         |
  | event_type: EXPENSE                                                      |
  | amount: 300k                                                             |
  +--------------------------------------------------------------------------+
            |                                             |
            v                                             v
  +-----------------------------+          +---------------------------------+
  | WalletLedger                |          | EntityLedger                    |
  | wallet_id: Debit Wallet     |          | category: Groceries            |
  | amount: -300k               |          | budget_id: May Groceries       |
  +-----------------------------+          | subcategory: Optional          |
                                           | project_id: Optional           |
                                           +---------------------------------+
                                                         |
                                                         v

PLANNING / CONTROL LAYER

  +--------------------------------------------------------------------------+
  | Monthly Budget                                                           |
  | category: Groceries                                                      |
  | month: May 2026                                                          |
  | monthly_limit: 2M                                                        |
  | spent: 300k                                                              |
  | remaining: 1.7M                                                          |
  +--------------------------------------------------------------------------+
```

Key interpretation:

```text
Wallet = where money is paid from.
Budget = planned spending limit for a category/month.
Expense = real event that affects both wallet balance and budget usage.
```

Creating or editing a budget:

```text
does not move wallet money
does not reserve wallet money
does not change net worth
only sets a planning/control limit
```

Posting an expense:

```text
decreases wallet balance through WalletLedger
increases budget spent through EntityLedger
is blocked if it exceeds budget/project limits
```

Current budget calculation:

```text
spent = posted expenses - refunds linked to this budget

effective_monthly_limit =
  monthly_limit
  + rollover_amount
  - cap_trim_amount

remaining = effective_monthly_limit - spent
effective_available = max(remaining, 0)
is_over_limit = remaining < 0
```

Note:

```text
sweep_amount exists in the current backend,
but sweep is rejected/deprecated in the product model.
```

Budget vs wallet reality:

```text
Wallet balance answers: How much money do I have right now?
Budget limit answers: How much am I allowing myself to spend in this category?
```

Therefore this is allowed:

```text
Total wallet balance: 5M
Electronics budget: 10M
```

Reason:

```text
budgets are plans
user may expect income
user may plan future purchases
user may use savings, credit, or installments
```

The app should warn if budgets look unrealistic, but should not treat budget limits as physical cash.

```text
Budget realism check:

total monthly budgets
vs current wallet balances
vs expected income
vs fixed obligations
```

### Budget Subcategory Diagram

```text
MONTHLY CATEGORY BUDGET

  +--------------------------------------------------------------------------+
  | Groceries Budget                                                         |
  | monthly_limit: 2M                                                        |
  +--------------------------------------------------------------------------+
              |
              v
  +----------------------+   +----------------------+   +-------------------+
  | Meat Subcategory     |   | Produce Subcategory  |   | Snacks Subcat     |
  | limit: 800k          |   | limit: 700k          |   | limit: 300k       |
  +----------------------+   +----------------------+   +-------------------+

Rule:
sum(subcategory limits) <= parent category monthly_limit
```

Subcategories are category-level detail. They are not wallet money and do not reserve cash.

### Project and Budget Interaction Diagram

Projects have two different modes.

```text
NON-ISOLATED PROJECT

  +---------------------------+
  | Project: Fitness Month    |
  | is_isolated: false        |
  +---------------------------+
              |
              | expense still belongs to monthly category budget
              v
  +---------------------------+
  | Monthly Budget            |
  | category: Health          |
  | month: May 2026           |
  +---------------------------+

Meaning:
project groups spending, but monthly budget remains the control layer.
```

Rules for non-isolated projects:

```text
project category spending counts against monthly budget
project category limit should not exceed available monthly category budget
project subcategories should not be used here
use monthly budget subcategories instead
```

```text
ISOLATED PROJECT

  +---------------------------+
  | Project: Wedding          |
  | is_isolated: true         |
  | total_limit: 50M          |
  +---------------------------+
              |
              | expense is controlled by project budget
              | not normal monthly budget
              v
  +---------------------------+
  | Project Category Limits   |
  | venue: 20M                |
  | food: 15M                 |
  | clothes: 5M               |
  +---------------------------+
              |
              v
  +---------------------------+
  | Project Subcategories     |
  | flexible per project      |
  +---------------------------+

Meaning:
isolated project has its own budget world.
```

Rules for isolated projects:

```text
can have project-specific subcategories
can have total/category/subcategory limits
does not drain monthly category budget
if funded from a goal, released funding can cap spending
```

### Current Budgeting Flow

```text
STEP 1: USER CREATES MONTHLY BUDGET

  +-----------------------------+
  | Budget                      |
  | category: Groceries         |
  | month: May 2026             |
  | monthly_limit: 2M           |
  +-----------------------------+

No wallet movement happens here.
```

```text
STEP 2: USER CREATES EXPENSE

  +-------------------+          +-----------------------------+
  | Debit Wallet      |          | Budget                      |
  | balance: 10M      |          | Groceries May limit: 2M     |
  +-------------------+          | spent so far: 0             |
            |                    +-----------------------------+
            | spend 300k
            v
  +-------------------+          +-----------------------------+
  | Debit Wallet      |          | Budget                      |
  | balance: 9.7M     |          | spent: 300k                 |
  +-------------------+          | remaining: 1.7M             |
                                 +-----------------------------+
```

```text
STEP 3: USER GETS REFUND

  +-------------------+          +-----------------------------+
  | Debit Wallet      |          | Budget                      |
  | balance: +100k    |          | spent decreases by 100k     |
  +-------------------+          +-----------------------------+
```

Current mental model:

```text
Budget -> controls category/month spending
Expense -> drains wallet and consumes budget space
Refund -> restores wallet and restores budget space
```

Most important difference from savings/goals:

```text
Goal allocation reserves purpose over existing money.
Budget limit only defines allowed spending.
Budget limit is not a reservation of wallet money.
```

### Budget Actions Diagram: Rollover, Cap, Reallocate

These actions must stay inside the budgeting philosophy:

```text
They move planning capacity.
They do not move wallet money.
They do not change net worth.
They should not pretend budget leftover is real saved cash.
```

Core formula:

```text
effective_monthly_limit =
  monthly_limit
  + rollover_amount
  - cap_trim_amount

remaining = effective_monthly_limit - spent
```

Deprecated current-code field:

```text
sweep_amount exists in the current backend shape,
but sweep should be removed from the product model.
```

Backend objects:

```text
Budget
- category
- budget_year
- budget_month
- monthly_limit
- max_rollover_amount
- rollover_mode
- max_envelope_balance

BudgetLedger
- category
- budget_year
- budget_month
- entry_type: ROLLOVER | CAP_TRIM
- amount
```

Deprecated current-code fields:

```text
Budget.sweep_target_goal_id
BudgetLedgerType.SWEEP
BudgetOut.sweep_amount
```

#### Full Rollover

Meaning:

```text
Unused budget capacity from previous month increases next month's limit.
No wallet money moves.
```

Diagram:

```text
JANUARY FOOD BUDGET

  +-----------------------------+
  | monthly_limit: 3M           |
  | spent: 2M                   |
  | leftover: 1M                |
  +-----------------------------+
              |
              | create BudgetLedger for February
              | entry_type: ROLLOVER
              | amount: +1M
              v

FEBRUARY FOOD BUDGET

  +-----------------------------+
  | monthly_limit: 3M           |
  | rollover_amount: +1M        |
  | effective_limit: 4M         |
  +-----------------------------+
```

Philosophy fit:

```text
Fits if shown as carried spending room.
Does not mean the user physically saved 1M.
```

#### Capped Rollover

Meaning:

```text
Only part of leftover budget capacity carries forward.
The excess disappears from budget capacity.
```

Diagram:

```text
JANUARY FOOD BUDGET

  +-----------------------------+
  | monthly_limit: 3M           |
  | spent: 1M                   |
  | leftover: 2M                |
  | max_rollover_amount: 500k   |
  +-----------------------------+
              |
              | raw leftover: 2M
              | allowed rollover: 500k
              | excess: 1.5M
              v

FEBRUARY FOOD BUDGET

  +-----------------------------+
  | monthly_limit: 3M           |
  | rollover_amount: +2M        |
  | cap_trim_amount: -1.5M      |
  | effective_limit: 3.5M       |
  +-----------------------------+
```

Same idea with percent mode:

```text
leftover: 2M
rollover_mode: PERCENT
max_rollover_amount: 25
allowed rollover: 500k
```

Philosophy fit:

```text
Fits well.
It keeps budgets from growing forever.
It is still planning capacity, not money.
```

#### Envelope Cap

Meaning:

```text
Category budget cannot grow beyond a configured cap.
```

Diagram:

```text
FEBRUARY FOOD BUDGET

  +-----------------------------+
  | base monthly_limit: 3M      |
  | raw rollover: 2M            |
  | max_envelope_balance: 4M    |
  +-----------------------------+
              |
              | cap allows only +1M
              | excess is trimmed
              v

  +-----------------------------+
  | effective_limit: 4M         |
  | cap_trim_amount: 1M         |
  +-----------------------------+
```

Philosophy fit:

```text
Fits well.
It prevents a monthly spending category from becoming a fake savings account.
```

#### Rejected: Sweep

Decision:

```text
Do not build sweep.
Deprecate/remove sweep from the budget product model.
```

Why:

```text
Budget leftover = unused spending permission.
Goal funding = allocation of real wallet money.
Sweep mixes planning capacity with real-money goal allocation.
```

Faulty mental model:

```text
Food budget leftover: 1.5M
therefore Trip Goal can receive 1.5M
```

Why faulty:

```text
the user may not actually have 1.5M free cash
the user may have spent from credit
the user's cash may be allocated to goals already
the budget was only a category/month limit
```

Correct alternative:

```text
At month end, show insight:
"You spent 1.5M less than your Food limit."

Then optional user action:
"Fund a goal from an eligible wallet"
```

That action must use the Goals model:

```text
choose real wallet
check unallocated wallet balance
create goal allocation
```

It must not be driven directly by budget leftover.

#### Reallocate

Current backend meaning:

```text
Move monthly limit from one category to another category in the same month.
No wallet money moves.
No BudgetLedger entry is created.
It directly changes monthly_limit values.
```

Diagram:

```text
BEFORE

  +-----------------------------+      +-----------------------------+
  | Entertainment Budget        |      | Groceries Budget            |
  | monthly_limit: 1M           |      | monthly_limit: 3M           |
  | spent: 200k                 |      | spent: 2.9M                 |
  | available: 800k             |      | available: 100k             |
  +-----------------------------+      +-----------------------------+
              |
              | reallocate 500k from Entertainment to Groceries
              | allowed because Entertainment available >= 500k
              v

AFTER

  +-----------------------------+      +-----------------------------+
  | Entertainment Budget        |      | Groceries Budget            |
  | monthly_limit: 500k         |      | monthly_limit: 3.5M         |
  | spent: 200k                 |      | spent: 2.9M                 |
  | available: 300k             |      | available: 600k             |
  +-----------------------------+      +-----------------------------+
```

Philosophy fit:

```text
Fits very well.
It means "change the plan", not "move money".
```

UI language:

```text
Use "Move budget room" or "Adjust limits".
Avoid "transfer money" for reallocation.
```

#### Implementation Status Caveat

Current code shape:

```text
compute_budget_chain reads BudgetLedger effects:
ROLLOVER, SWEEP, CAP_TRIM

reallocate_budget is implemented:
from_budget.monthly_limit -= amount
to_budget.monthly_limit += amount
```

Important backend gap:

```text
recompute_budget_chain currently deletes BudgetLedger rows and returns.
The old generation logic for rollover/sweep/cap exists after an unreachable return path.
```

Meaning:

```text
Rollover/cap are worth keeping.
Sweep exists in schema/output math but should be removed.
The automatic rollover/cap ledger materialization path needs review/fix before relying on it.
```

Also:

```text
reallocated_in and reallocated_out are output fields,
but current reallocation changes monthly_limit directly,
so those fields remain 0 unless a separate reallocation ledger is added later.
```

Senior-engineer judgment:

```text
Rollover: fits the budget philosophy.
Capped rollover: fits the budget philosophy.
Envelope cap: fits the budget philosophy.
Reallocate: fits the budget philosophy.
Sweep: reject/deprecate.
Reason: budget leftover is planning capacity, not real money.
```

### Keep: Budgets Are Planning Limits

Current budget model is valid:

```text
Budget limit = planned spending boundary.
Wallet balance = current money reality.
Budget limit does not reserve wallet money.
```

Do not block budgets just because they exceed current wallet balance.

Reason:

```text
users may expect salary
users may plan around future income
users may use savings
users may use credit or installments
users may know context the app cannot know
```

Useful future feature:

```text
Budget realism check
```

Example:

```text
Total monthly budgets: 12M
Current wallet balance: 5M
Expected income: 8M
Planning coverage: 13M
Status: covered
```

Warn, do not block.

### Keep: Bank Loans and Bank Deposits

Bank loan:

```text
Bank -> User
Wallet increases
Debt increases
Loan inflow is not income
```

Examples:

```text
Cash Wallet +5M
Debt: Bank Loan +6M total repayable
```

or:

```text
Debit Wallet +5M
Debt: Bank Loan +6M total repayable
```

Bank deposit:

```text
User -> Bank
Wallet decreases
Asset increases
```

Examples:

```text
Cash Wallet -10M
Asset: Bank Deposit +10M principal
```

or:

```text
Debit Wallet -10M
Asset: Bank Deposit +10M principal
```

Deposit maturity:

```text
Wallet receives principal + interest
Principal returned is not income
Only interest/profit is income
```

### Keep: Bank Products Hub

Best UX/domain split:

```text
Domain truth:
Bank Deposit = Asset subtype
Bank Loan = Debt subtype

Navigation/UI:
Bank Products page = specialized hub for deposits and loans
```

Do not create totally separate financial truth tables that duplicate assets/debts.

Scalable shape:

```text
assets.type = bank_deposit
debts.type = bank_loan
```

Optional detail tables:

```text
bank_deposit_details(asset_id, bank_name, principal, rate, maturity_date, payout_frequency)
bank_loan_details(debt_id, principal_received, total_repayable, rate, schedule)
```

### Reject or Avoid: Counting Allocations as Money

Bad:

```text
total = wallet balances + goal allocations
```

Reason:

```text
goal allocations are labels over wallet money
they are not separate assets
this causes double counting
```

Correct:

```text
net money = wallet balances + assets - debts
goal allocations only explain purpose/reservation
```

### Reject or Avoid: Goal Reserve as Mandatory Middle Layer

Avoid making every goal flow:

```text
Wallet -> Goal Reserve -> Goal
```

Reason:

```text
it hides where money physically sits
it creates double-counting risk
it makes wallet/goal logic harder
```

Use direct wallet-backed allocations unless there is a deliberate product reason for a separate reserve pool.

### Reject or Avoid: Forcing Goals Through Projects

Bad:

```text
Every completed goal must create a project.
```

Reason:

```text
some goals become assets
some pay debts
some fund installments
some are one-time expenses
some stay reserves
```

Projects should be used only for multi-expense missions.

### Reject or Avoid: Blocking Budgets by Current Wallet Balance

Bad:

```text
budget total cannot exceed current wallet balance
```

Reason:

```text
budgets are plans, not reserved cash
users budget around future income and obligations
```

Correct:

```text
allow budget
show realism warning
let user decide
```

### Reject or Avoid: Loans as Income

Bad:

```text
loan received = income
```

Correct:

```text
loan received = wallet inflow + debt increase
```

Reason:

```text
cash increases but liability also increases
net worth does not improve like real income
```

### Reject or Avoid: Bank Deposits as Simple Expenses

Bad:

```text
opening bank deposit = expense
```

Correct:

```text
opening bank deposit = wallet outflow + asset creation
```

Reason:

```text
money changed form
it was not consumed
```

### Final Direction

Best long-term model:

```text
Wallets hold real money.
Assets hold owned value outside normal wallets.
Debts/installments hold obligations.
Budgets are planning limits.
Goals are intentions.
Goal allocations reserve purpose over eligible wallet money.
Projects group larger multi-expense missions.
```

This keeps real money, planned money, and virtual purpose labels separate.

## Goal Protection and Reconciliation Model

Purpose: evaluate strict YNAB-like protection for goal-funded wallet money without turning budgets into envelope budgeting.

Status: future architecture direction. This builds on the wallet-backed goal allocation model.

### Senior Verdict

Good idea:

```text
Goal allocations should reduce a wallet's free-to-spend amount.
```

Do not change wallet balance:

```text
wallet balance = real money
goal allocation = protected purpose claim on that money
free_to_spend = wallet balance - protected goal allocations
```

This is stronger than a soft warning because goal money is supposed to have a job.

Bad idea:

```text
Let normal spending freely consume goal-protected money with only a weak warning.
```

Reason:

```text
Then goals become decoration.
The app stops helping the user protect saved money.
```

Important limit:

```text
Apply strict protection to Goals, not Budgets.
Budgets remain planning limits.
Goals are protected real-money reservations.
```

### Core Wallet Math

```text
protected_for_goals = sum(active goal allocations from this wallet)
free_to_spend = max(wallet.current_balance - protected_for_goals, 0)
over_allocated = max(protected_for_goals - wallet.current_balance, 0)
```

Example:

```text
Debit2 balance: 4M
Camera Goal allocation from Debit2: 3.33M

Free to spend: 670k
Protected for Camera: 3.33M
```

If user tries normal spending:

```text
Restaurant expense from Debit2: 2M
```

Strict result:

```text
Blocked.
Only 670k is free to spend.
3.33M is protected for Camera Goal.
```

### Diagram: Strict Goal Protection

```text
NORMAL WALLET SPENDING

  +-------------------------+
  | User records expense    |
  | wallet: Debit2          |
  | amount: 2M              |
  +------------+------------+
               |
               v
  +-------------------------+
  | Check free_to_spend     |
  | balance: 4M             |
  | protected: 3.33M        |
  | free: 670k              |
  +------------+------------+
               |
      +--------+--------+
      |                 |
      v                 v
  amount <= free    amount > free
      |                 |
      v                 v
  +-----------+    +----------------------+
  | Allow     |    | Block normal spend   |
  | expense   |    | Ask user to resolve  |
  +-----------+    +----------------------+
```

Resolution options when blocked:

```text
1. Release money from the goal first.
2. Choose another wallet.
3. Rebalance goal funding from another wallet.
4. Cancel.
```

### Multi-Wallet Goal Example

User wants a camera:

```text
Camera Goal target: 10M

Funding:
Debit1:   3.33M
Debit2:   3.33M
Savings:  3.34M
```

Later Debit2 balance drops:

```text
Debit2 balance: 2M
Debit2 Camera allocation: 3.33M
```

Now the allocation is not fully supported:

```text
Debit2 over-allocated by 1.33M
Camera Goal supported amount: 8.67M
Camera Goal funding gap: 1.33M
```

UI should show:

```text
Camera Goal has a funding issue.
Debit2 has only 2M, but 3.33M is protected for this goal.
Short by 1.33M.
```

Fix options:

```text
Add money back to Debit2.
Reduce Debit2 allocation.
Move 1.33M allocation to another eligible wallet.
Leave temporarily over-allocated with warning.
```

### Payment Wallet vs Funding Wallet

Good idea:

```text
If goal money is protected, a linked purchase should use goal funds by default.
```

But do not fake real-world transfers.

Example:

```text
Savings Wallet: 10M
Debit Wallet: 10M

Laptop Goal:
10M protected from Savings Wallet
```

At store:

```text
User pays with Debit Wallet.
Debit Wallet -10M in real life.
```

The clean accounting intent:

```text
Debit was the payment instrument.
Savings was the funding source.
```

But Sarflog must not silently record:

```text
Savings -10M
Debit +10M
```

unless the user actually moved that money in real life.

Best model:

```text
Create pending reimbursement.
```

### Diagram: Different Payment Wallet With Pending Settlement

```text
GOAL PURCHASE PAID FROM DIFFERENT WALLET

  +-------------------------------+
  | Goal funding source           |
  | Savings: 10M protected        |
  +-------------------------------+
                  |
                  | user buys laptop with Debit
                  v
  +-------------------------------+
  | Real purchase event           |
  | Debit -10M                    |
  +-------------------------------+
                  |
                  v
  +-------------------------------+
  | Settlement decision           |
  | Use goal funds?               |
  +-------------------------------+
       |              |              |
       v              v              v
  Use goal funds  Pay outside    Change payment
       |              |              |
       v              v              v
  Pending transfer  Savings       Record purchase
  Savings -> Debit  untouched     from funding wallet
       |
       v
  User confirms real bank transfer
       |
       v
  Savings -10M, Debit +10M
  Goal allocation consumed
  Goal completed
```

### Pending Reimbursement Rule

If payment wallet differs from funding wallet:

```text
Do not auto-create completed transfer.
Ask user to confirm real-world movement.
```

UX:

```text
This purchase used Debit, but the goal money is protected in Savings.

To use goal funds, transfer 10M from Savings to Debit in real life.

[I transferred it]
[Record pending reimbursement]
[Pay outside goal funds]
[Change payment wallet]
```

When confirmed:

```text
Purchase:
Debit -10M

Settlement transfer:
Savings -10M
Debit +10M

Goal:
allocation consumed
goal completed
```

If not confirmed yet:

```text
Purchase exists.
Settlement is pending.
Goal funds remain protected until resolved.
```

### Paying Outside Goal Funds

Meaning:

```text
The expense is related to the goal, but the user chooses not to use the protected goal money.
```

Real-world example:

```text
Dubai Trip Goal:
Savings protected: 20M

User buys suitcase:
Debit Wallet -1M
```

User chooses:

```text
Pay outside goal funds.
```

Meaning:

```text
The suitcase is trip-related.
But it should not reduce the 20M protected trip fund.
```

Result:

```text
Debit decreases by 1M.
Savings stays 20M.
Dubai Trip Goal funding stays 20M.
Expense can still be tagged/linked as trip-related.
```

Use cases:

```text
Trip fund is for flights/hotel, but suitcase is paid from monthly money.
Wedding fund is for venue/catering, but notebook is paid from normal debit.
Camera fund is for camera body, but memory card is paid outside goal funds.
```

### Reality Reconciliation

Bad idea:

```text
Hard block every expense that violates free_to_spend, even if it already happened in real life.
```

Reason:

```text
Sarflog cannot physically stop a real bank card payment.
If the real-world payment happened, the app must let the user reconcile reality.
```

Good model:

```text
Normal in-app spending = strict.
Reality reconciliation = allowed, but requires explicit consequence.
```

Example:

```text
Debit Wallet balance in Sarflog: 10M
Camera Goal protected from Debit: 8M
Free to spend: 2M
```

In real life, user pays:

```text
Restaurant: 4M from Debit
```

When user logs it later, Sarflog detects:

```text
Expense exceeds free_to_spend by 2M.
```

Do not silently allow it. Do not trap the user either.

Ask:

```text
This real expense used 2M that was protected for Camera Goal.

Choose resolution:
1. Reduce Camera Goal allocation by 2M.
2. Move 2M Camera funding to another wallet.
3. Cancel.
```

### Diagram: Reality Reconciliation

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

### What To Keep

Keep:

```text
Goal allocations reduce free-to-spend.
Normal expenses/transfers should respect free-to-spend.
Goal-linked purchases may consume protected money.
Different payment wallet should create settlement decision.
Real-world transfers should be pending until confirmed.
Reality reconciliation must exist for external overspending.
Over-allocation should be visible and actionable.
Reconciliation must force an immediate reduce/rebalance decision.
```

### What To Reject

Reject:

```text
Silently deleting goal allocations after overspending.
Silently moving allocations to another wallet.
Silently creating wallet transfers that did not happen in real life.
Treating over-allocation as normal and hiding it.
Offering temporary over-allocation as a normal resolution.
Offering pending reconciliation / decide-later as a normal resolution.
Applying this strict model to budgets.
Blocking users from recording real-world transactions that already happened.
```

### Final Product Rule

```text
Goal money is protected money.
Protected money reduces free-to-spend.
Normal spending cannot use protected money silently.
Goal spending can use protected money intentionally.
If reality already broke the rule, Sarflog reconciles honestly instead of lying.
```

This gives Sarflog discipline without corrupting wallet truth.

## Wallet Outflow Protection Flow

This extends the goal-protection model beyond expenses.

Core idea:

```text
Goal allocations are protected claims on wallet money.
Any wallet outflow can damage those claims.
Therefore every wallet outflow must pass the same protection gate.
```

This applies to:

```text
expenses
transfers out
credit card repayments
loan repayments
bank deposit funding
asset purchases
currency exchange
wallet replacement
wallet archive preparation
```

### Core Invariant

For any owned-money wallet:

```text
owned_positive_balance = max(wallet.balance, 0)
protected_for_goals = sum(active unreleased goal allocations from wallet)
free_owned_outflow = owned_positive_balance - protected_for_goals
```

Normal outflows must satisfy:

```text
outflow_amount <= free_owned_outflow
```

If not, the action touches protected goal money and needs an explicit resolution.

Wallet archive must satisfy:

```text
wallet.balance == 0
active_goal_allocations == 0
pending_goal_settlements == 0
```

For credit and overdraft wallets, also require:

```text
outstanding_debt == 0
overdraft_used == 0
pending_repayments == 0
```

### Diagram: Protected Wallet Outflow Gate

```text
USER REQUESTS WALLET OUTFLOW
expense, transfer, repayment, deposit, asset buy, archive prep

  +-------------------------------+
  | WalletAvailabilityService     |
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
  +------------------+   +------------------------------+
  | Allow normally   |   | Goal protection conflict     |
  +------------------+   +---------------+--------------+
                                          |
                  +-----------------------+-----------------------+
                  |                       |                       |
                  v                       v                       v
     +-----------------------+  +-----------------------+  +----------------------+
     | Intended goal use     |  | Money is moving       |  | Real life already    |
     | purchase/project/etc  |  | to another wallet     |  | happened             |
     +----------+------------+  +----------+------------+  +----------+-----------+
                |                          |                          |
                v                          v                          v
     Consume/settle allocation   Move/rebalance allocation   Reconcile now:
     with real event             with transferred money       reduce or rebalance
```

### Real-World Cases

Archive wallet with allocated goal money:

```text
Old Debit balance: 10M
Camera Goal protected from Old Debit: 8M
Free: 2M
```

The wallet cannot be archived just because the user wants to close the card.

Correct flow:

```text
1. Transfer/move real money to destination wallet.
2. Move or release goal allocations.
3. Confirm old wallet has balance 0.
4. Confirm old wallet has active goal allocations 0.
5. Archive.
```

If the user is replacing the wallet:

```text
Old Debit -> New Debit: 10M
Camera allocation moves Old Debit -> New Debit: 8M
Old Debit can now be archived.
```

Transfer only free money:

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

Transfer more than free money:

```text
Old Debit balance: 10M
Camera protected: 8M
Free: 2M

Transfer Old Debit -> New Debit: 5M
```

This touches 3M protected money.

Resolution options:

```text
1. Move 3M of Camera allocation to New Debit.
2. Reduce/release 3M from Camera allocation.
3. Transfer only the 2M free amount.
4. Cancel.
```

Credit card repayment:

```text
Debit balance: 10M
Camera protected: 8M
Free: 2M
Credit card debt: 5M

Pay credit card from Debit: 5M
```

This is a repayment, not normal owned-money movement.

Sarflog should block normal repayment and say:

```text
Only 2M is free.
3M is protected for Camera Goal.
Release/rebalance goal money, pay only 2M, choose another wallet, or cancel.
```

Credit wallets:

```text
can receive repayments
can be used for credit spending if supported
cannot fund goals
cannot hold goal allocations
```

Debit wallet with overdraft:

```text
Debit1 balance: 3M
Overdraft limit: 10M
Goal protected from Debit1: 3M
Free owned money: 0

Transfer Debit1 -> Debit2: 10M
```

This is not a normal transfer.

It means:

```text
3M protected owned money is affected
7M overdraft/borrowed money is used
```

Valid resolutions:

```text
1. Move the 3M goal allocation to Debit2.
   Debit1 becomes -7M.
   Debit2 receives 10M.
   Goal stays funded from Debit2.

2. Reduce/release the 3M goal allocation.
   Debit1 becomes -7M.
   Debit2 receives 10M.
   Goal becomes short by 3M.

3. Cancel.
```

Invalid resolution:

```text
Keep the 3M goal allocation on Debit1 after Debit1 becomes negative.
```

Reason:

```text
Overdraft capacity is borrowed money.
Borrowed money cannot back goals.
Goal allocations can only be backed by owned positive wallet balance.
```

Bank deposit or asset purchase from protected wallet:

```text
Debit balance: 20M
Wedding protected: 15M
Free: 5M

Open bank deposit from Debit: 10M
```

This uses 5M protected Wedding money.

Until goals can be backed by assets, do not move goal allocation into the bank deposit asset automatically.

Resolution options:

```text
1. Fund deposit only with free 5M.
2. Move 5M Wedding funding to another eligible wallet.
3. Reduce/release 5M Wedding funding.
4. Cancel.
```

### Product Rule

```text
Goal allocations do not reduce wallet balance.
Goal allocations do reduce free owned outflow.
Every wallet outflow must respect protected goal claims.
If money moves to another eligible wallet, allocations may move with it.
If money leaves owned wallets or becomes borrowed/asset money, allocations must be reduced or rebalanced.
Credit and overdraft capacity cannot fund goals.
Wallet archive requires zero balance, zero active allocations, and no pending settlement/debt.
```

---

## Goal UX Features: Images And Predictions

### Decision

Keep goal financial logic strict and simple, but make goals feel more human.

Do not add more taxonomy like templates. Instead, improve the goal experience with:

```text
optional goal cover image
honest completion prediction
```

### Goal Cover Image

Purpose:

```text
Make the goal feel real and emotionally visible.
```

Real-world examples:

```text
Laptop goal -> photo of exact laptop
Car goal -> photo of car
Apartment goal -> building or room image
Wedding goal -> couple/event image
Travel goal -> destination image
Camera goal -> camera image
```

Best simple data model:

```text
goals.cover_image_url nullable
goals.cover_image_storage_key nullable
```

Keep it optional:

```text
No image required.
One cover image per goal.
Editable and removable.
Compressed upload.
Reasonable file size limit.
```

Do not let images affect financial behavior:

```text
Images do not change wallet allocations.
Images do not change goal intent.
Images do not change completion rules.
```

### Goal Completion Prediction

Purpose:

```text
Answer: "When can I realistically reach this goal?"
```

Prediction must be framed as an estimate, not a promise.

Good wording:

```text
At this pace
Estimated completion
If you save X per month
```

Avoid:

```text
Guaranteed date
You will reach this by...
```

Useful prediction modes:

```text
planned_monthly_contribution
current_saving_rate
income_percentage
interest_adjusted
```

Start with the simplest useful version:

```text
remaining_amount / planned_monthly_contribution
```

Example:

```text
Camera Goal
Target: 10M
Funded: 4M
Remaining: 6M
Planned monthly saving: 1M

Estimated completion: about 6 months
```

Later version using behavior:

```text
Average reserved over last 3 months: 1.5M/month
Remaining: 6M
Estimated completion: about 4 months
```

Advanced version:

```text
Include expected income
Include budget realism check
Include savings interest
Include multi-currency after multi-currency is stable
```

### Budget Realism Connection

Prediction should eventually connect to budget realism:

```text
User wants to save 2M/month.
Budget realism says likely free money is only 1.2M/month.
Show that the goal may take longer than the optimistic plan.
```

This makes the feature useful instead of fake-motivational.

### Diagram

```text
Goal
 |
 +-- Financial model
 |   |
 |   +-- intent
 |   +-- target amount
 |   +-- wallet-backed allocations
 |   +-- protected free-to-spend
 |
 +-- Human layer
     |
     +-- optional cover image
     +-- estimated completion
     +-- planned monthly contribution
     +-- current saving pace
```

### Final Rule

```text
Goal images and predictions are UX/product features.
They should make goals more motivating and understandable.
They must not complicate wallet truth, allocation math, or ledger behavior.
```

## Debt / Obligation Architecture Notes

### Why This Exists

Debt behavior is becoming too important to patch one route at a time.

The debt feature needs to support:

```text
money borrowed
money lent
delayed expenses
receivables
charges
interest
fees
partial payments
asset settlement
forgiveness
reversals
wallet protection from goal funding
```

### Core Mental Model

```text
Debt = obligation relationship
DebtEvent = what happened to that obligation
FinancialEvent = real wallet/income/expense/entity movement, if any
```

Not every debt event moves wallet money.

Examples:

```text
Add late fee to debt
-> DebtEvent only
-> no wallet movement

Pay debt from wallet
-> DebtEvent
-> FinancialEvent with WalletLedger/EntityLedger

Settle debt with asset
-> DebtEvent
-> asset created/transferred/closed
-> no wallet movement unless mixed with cash
```

### Debt Event Flow

```text
Debt
 |
 +-- CREATE
 |
 +-- INITIAL_TRANSFER
 |   |
 |   +-- optional FinancialEvent
 |       +-- WalletLedger
 |       +-- EntityLedger(debt_id)
 |
 +-- CHARGE_ADDED
 |   |
 |   +-- no wallet movement yet
 |
 +-- PAYMENT
 |   |
 |   +-- principal portion
 |   +-- charge/interest portion
 |   +-- optional FinancialEvent
 |
 +-- ASSET_SETTLEMENT
 |   |
 |   +-- receive asset instead of cash
 |   +-- give asset instead of cash
 |
 +-- PARTIAL_FORGIVE / FULL_FORGIVE
 |
 +-- REFUND / REVERSAL
 |
 +-- ARCHIVE
```

### Bank Fees Versus Debt Charges

Do not merge these blindly.

```text
Bank fee deducted from wallet now
-> wallet outflow
-> expense now

Debt charge added to loan/card/debt
-> obligation increases
-> no wallet outflow yet

Debt charge paid later
-> wallet outflow
-> charge settlement
```

### Asset Settlement

Debt settlement can be:

```text
WALLET
ASSET
MIXED
```

Real-world examples:

```text
Friend owes me 5M and gives me a phone worth 5M.
I owe 5M and give my gold to settle it.
Client pays invoice with equipment instead of cash.
```

Rule:

```text
settlement amount must be explicit agreed value
```

Do not assume asset current value automatically equals debt settlement amount.

### Debt Taxonomy Fields

Debt category/source fields must depend on debt meaning.

```text
I owe + money_transferred=true
-> principal is not expense
-> charges/interest are expenses

I owe + money_transferred=false
-> delayed expense
-> needs category, subcategory, project fields

They owe me + money_transferred=true
-> principal repayment is not income
-> charges/interest/profit can be income

They owe me + money_transferred=false
-> receivable/invoice-like
-> needs income source and possibly project/client context
```

### Why Goals Do Not Need The Same New Table

Goals already have a ledger-like money history:

```text
goal_contributions
- ALLOCATE
- RETURN
- CONSUME
```

Useful UI:

```text
Goal Details / Goal History
```

showing each reserve, unreserve, and consumed amount by wallet.

No new `goal_events` table is needed for current goal money truth.

### Final Direction

```text
Debts need a DebtEvent lifecycle ledger.
Goals already have GoalContributions as their funding ledger.
Debt-linked expense/income edits should be controlled through debt lifecycle rules.
Debt pages need details/history views before advanced Pay Obligation goals are clean.
```

**Keep this spine clean, and you can add features forever without creating chaos.** 🎯✨




Yes — this is a **high-value, low-bloat feature**.

Projected spending from recurring expenses is useful because it answers a very practical question:

> “How much money is already spoken for before I even make new decisions?”

That fits Sarflog perfectly.

## Why it is valuable

A user may think:

```text
I have 5M free.
```

But recurring expenses say:

```text
Internet: 150k/month
Netflix: 80k/month
Phone installment: 400k/month
Gym: 300k/month
Rent: 2M/month
```

Sarflog can show:

```text
Next 7 days: 550k expected
Next 30 days: 2.93M expected
Next 12 months: 35.16M expected
```

That immediately improves planning.

## Where it connects to your system

This feature should feed into:

```text
Budget Room
Free-to-spend
Monthly obligations
Goal predictions
Cashflow forecast
```

Example:

```text
Current free money: 7M
Projected recurring expenses this month: 3M
Safe remaining capacity: 4M
```

Now the user understands:

> “I technically have 7M, but 3M is already expected to leave.”

That is very Sarflog.

## What should count as projected spending?

Include:

```text
recurring expenses
subscriptions
rent
utilities
installment payments
loan payments
planned debt payments
recurring family support
insurance
school fees
```

Maybe separate them visually:

```text
Recurring expenses
Fixed obligations
Subscriptions
Debt/installment payments
```

Do not mix them all into one vague number only.

## Best UI

Show a card like:

```text
Projected Spending

Next 7 days: 820k
Next 30 days: 3.4M
Next 12 months: 40.8M

Biggest upcoming:
- Rent: 2M on June 1
- Phone installment: 400k on June 5
- Internet: 150k on June 10
```

And allow custom period:

```text
From: May 30
To: July 15
Projected: 5.2M
```

## Important rule

Projected spending is not actual spending.

So label it clearly:

```text
Projected / expected
```

not:

```text
spent
```

When the due date arrives and user pays, it becomes actual expense/payment.

## Senior implementation model

Each recurring item should have:

```text
amount
frequency: daily / weekly / monthly / yearly / custom
start_date
end_date nullable
next_due_date
category
wallet optional
linked_obligation optional
status: active / paused / ended
```

Then your projection engine generates expected occurrences between two dates.

## Final judgment

Yes, build this.

It is not bloat because it strengthens Sarflog’s core promise:

> “Know what money is truly free after goals, obligations, and expected recurring spending.”

This is one of those features that feels simple, but makes the app much more financially intelligent.



Yes. For Sarflog, the best AI integration is **not “chatbot inside finance app.”** That can become bloated fast.

The best AI integration is:

> **AI that reduces manual entry, explains money consequences, and detects inconsistencies — while the user stays in control.**

I would prioritize these.

## 1. Receipt/Basket AI

This is probably your strongest AI feature.

User uploads/scans receipt:

```text
Korzinka receipt photo
```

AI extracts:

```text
store
date
total
items
prices
possible categories
```

Then Sarflog drafts:

```text
Groceries: 180k
Household: 65k
Pet food: 45k
Snacks: 30k
```

User reviews and confirms.

Value:

```text
less manual entry
better categories
Basket Mode becomes powerful
receipts become exciting
```

This is not bloated. This is directly useful.

## 2. Natural-language expense input

User says/types:

```text
I spent 85k on taxi from my Humo card today
```

AI converts to draft:

```text
Expense
Amount: 85k
Wallet: Humo
Category: Transport
Subcategory: Taxi
Date: today
```

User confirms.

Also:

```text
Paid 400k phone installment from Uzcard
```

AI drafts:

```text
Obligation payment
Linked installment: Phone
Amount: 400k
Wallet: Uzcard
```

This is very useful on mobile.

## 3. Smart categorization

When user enters:

```text
Oqtepa Lavash — 63k
```

AI suggests:

```text
Food → Fast food
```

When user enters:

```text
Apteka — 120k
```

AI suggests:

```text
Health → Medicine
```

But always let user override.

Important: learn from user corrections.

## 4. Financial consistency assistant

This is very Sarflog-specific and valuable.

AI watches for suspicious states:

```text
Your budget plan exceeds current free money by 2.5M.
This goal is funded from Savings, but you are trying to pay from Debit.
This loan inflow was recorded as income. Should it be a debt instead?
This installment is categorized as Installments, but it may belong under Electronics.
```

This is like threat modeling for user finances.

It does not act automatically. It says:

```text
Review suggested fix
```

## 5. Goal prediction explanation

Not just:

```text
You will reach this goal in 6 months.
```

But:

```text
At your current saving pace of 1.2M/month, this goal may take about 6 months.
If you increase monthly saving to 1.8M, it may take 4 months.
```

AI can explain this in human language and suggest tradeoffs:

```text
Reduce Entertainment by 300k/month to reach this goal one month earlier.
```

This is useful if backed by real calculations.

## 6. “What happened this month?” summary

Monthly AI summary:

```text
You spent 1.4M more than last month.
The biggest increase was Transport.
You protected 2M for goals.
Your phone installment is due in 3 days.
Your free-to-spend is lower mainly because 5M is reserved for Emergency.
```

This creates a premium feeling.

## What I would NOT build early

Avoid:

```text
generic finance chatbot
AI investment advice
AI pretending to be financial advisor
fully automatic transaction creation without confirmation
AI changing budgets/goals by itself
AI giving legal/tax guarantees
```

Those are risky and bloated.

## Best AI roadmap

Start with 3 AI features:

```text
1. Receipt/Basket extraction
2. Natural-language quick entry
3. Smart anomaly/inconsistency detection
```

These are 100% aligned with Sarflog.

The philosophy:

> AI should turn messy real-world money events into clean Sarflog drafts, then let the user confirm.

That is serious, useful, and not bloated.




