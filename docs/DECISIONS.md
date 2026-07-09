# Sarflog Decisions

Short decision log for product and architecture choices that are considered settled enough to guide implementation.

## 2026-07-07 - Freeze Isolated Projects and Fund Project

### Decision

Freeze Isolated Projects and Fund Project until the core Sarflog app philosophy is stable.

Do not execute new isolated-project or Fund Project work from older epics, PRDs, or issue files. Existing code may remain if it does not distort core app flows.

### Rationale

Isolated Projects are not a small project feature. They introduce a second money engine that touches wallets, Free Money Now, monthly budgets, goals, expense entry, reports, wrap-up, and protection-breach resolution.

The current middle state is risky because it has wallet-backed project funding and category allocations, but does not yet have a complete first-class ledger model for isolated project stash consumption/release.

### Future Revisit

After the core app stabilizes, decide one of two paths:

```text
Remove Isolated Projects and Fund Project.
```

or:

```text
Promote Isolated Projects into a first-class protected-stash ledger.
```

See [ADR 0022](adr/0022-freeze-isolated-projects-and-fund-project.md).

## 2026-06-03 - Payment Plans Guided Create Flow

### Decision

Refactor **Create Payment Plan** first, before redesigning the whole Debts/Payment Plans page.

### Rationale

Creation is where users face the hardest concepts: plan type, what was bought/received, whether money moved today, repayment schedule, asset tracking, and budget category. Record Payment, Add Charge, and Details can be polished after the create flow is clear.

## 2026-06-03 - Payment Plan First Question

### Decision

The first guided question should be:

```text
What kind of payment plan is this?
```

Use these UI choices:

```text
Buy now, pay over time
Bank loan
Home loan / mortgage
Vehicle loan
Education payment plan
Service contract
Other scheduled payment
```

### Rationale

`Store installment` and `Product financing` are too detailed for the first UI choice. Users usually care that they received a product now and will repay over time, not whether the store or a finance partner funded it.

### Backend Mapping

```text
Buy now, pay over time -> STORE_INSTALLMENT
Bank loan -> BANK_LOAN
Home loan / mortgage -> MORTGAGE
Vehicle loan -> AUTO_LOAN
Education payment plan -> EDUCATION_LOAN
Service contract -> SERVICE_CONTRACT
Other scheduled payment -> OTHER
```

## 2026-06-03 - Payment Plan Step 2 Category Suggestions

### Decision

In Step 2, category should be suggested from payment plan type only when confidence is high.

### Rules

```text
Home loan / mortgage -> prefill Housing
Vehicle loan -> prefill Transport
Education payment plan -> prefill Education
```

For lower-confidence types, do not auto-select a category:

```text
Buy now, pay over time -> user chooses category
Bank loan -> user chooses category
Service contract -> user chooses category
Other scheduled payment -> user chooses category
```

### Rationale

Payment plan type describes financing structure. Category describes what life area or budget bucket the obligation belongs to. Some plan types imply category strongly, but bank loans, product purchases, and service contracts can belong to many categories.

## 2026-06-03 - Payment Plan Step 3 Money Structure

### Decision

Step 3 should ask for the payment plan money structure with context-aware wording.

### Rules

```text
Buy now, pay over time -> Total purchase price + down payment paid today
Bank loan / microloan -> Loan amount + optional received-wallet inflow
Home loan / mortgage -> Property price + down payment paid today
Vehicle loan -> Vehicle price + down payment paid today
Education payment plan -> Tuition/course amount + optional upfront payment
Service contract -> Contract amount + optional upfront payment
Other scheduled payment -> Total amount + optional upfront payment
```

The core calculation remains:

```text
remaining_amount = total_amount - upfront_payment
```

If upfront payment is greater than zero, ask which wallet(s) paid it. If upfront payment is zero, skip upfront wallet allocation.

### Bank Loan / Microloan Disbursement

Use this UI label:

```text
Bank loan / microloan
```

Backend mapping stays:

```text
Bank loan / microloan -> PaymentPlanType.BANK_LOAN
```

For bank loan / microloan, ask:

```text
Did the bank already send this money to you?
```

If yes, record it as a wallet inflow, not income.

Allowed receiving wallet types:

```text
CASH
DEBIT
SAVINGS
```

Do not allow:

```text
CREDIT
```

### Event Meaning

Loan disbursement should be modeled as borrowed money entering a wallet:

```text
FinancialEvent.event_type = DEBT_SETTLEMENT
FinancialEvent.reference_type = LOAN_DISBURSEMENT
WalletLedger.amount = +loan_amount
DebtLedgerEntry.entry_type = INITIAL
DebtLedgerEntry.event_subtype = LOAN_DISBURSEMENT
```

`LOAN_DISBURSEMENT` should be added as a clearer reference subtype instead of relying only on generic `DEBT_INITIAL`.

### Rationale

In Uzbekistan, users commonly say bank `kredit`, `mikroqarz`, or `iste'mol krediti`. The label must keep the word `Bank` to avoid confusion with informal friend/family debt. Bank loan money usually arrives into one cash/debit/savings destination; later splitting is a normal wallet transfer, not multiple loan disbursements.

## 2026-06-03 - Payment Plan Step 4 Repayment Schedule

### Decision

Step 4 should ask:

```text
How will you repay it?
```

Collect:

```text
number of payments
payment frequency
first payment due date
```

Sarflog calculates:

```text
regular payment amount
final due date / plan end date
```

### Rationale

This matches the current backend shape and keeps the form simple:

```text
payment_count + frequency + first_due_date -> payment schedule
```

Do not ask for a separate deadline date. The Payment Plan deadline is the last scheduled payment due date. A separate deadline would create duplicate truth and possible conflicts.

### Rule

```text
Payment Plans derive end date from schedule.
Regular Debts may have an expected return date/deadline.
```

## 2026-06-03 - Payment Plan Asset Step

### Decision

Only show asset tracking for payment plan types that can realistically create an owned asset.

### Asset-Eligible Types

```text
Buy now, pay over time
Home loan / mortgage
Vehicle loan
```

Do not show the asset step for:

```text
Bank loan / microloan
Education payment plan
Service contract
Other scheduled payment
```

### Rationale

Asset tracking is meaningful when the user receives an owned item/property/vehicle. Bank loans produce cash/borrowed funds, education usually buys a service/benefit, and service contracts usually buy consumed service rather than an owned asset.

### Rule

```text
Asset-eligible plans get an optional "Track as asset?" step.
Non-asset plans skip this step.
```

For asset-eligible plans, default asset fields can be:

```text
asset_name = plan item/name
current_value = total price
```

## 2026-06-03 - Payment Plan Final Review Step

### Decision

Every guided Payment Plan flow ends with a summary and confirmation step.

### Flow Shape

Asset-eligible plans:

```text
1. What kind of payment plan is this?
2. What did you receive?
3. Money structure
4. Repayment schedule
5. Track as asset?
6. Review plan
```

Non-asset plans:

```text
1. What kind of payment plan is this?
2. What is this obligation for?
3. Money structure / loan disbursement
4. Repayment schedule
5. Review plan
```

### Review Step Content

The review step should explain what Sarflog will create in plain language:

```text
linked debt amount
wallet inflow/outflow, if any
scheduled payment rows
category/subcategory/project context
asset creation, if selected
```

### Rationale

Payment plans create several connected records. A final confirmation step catches misunderstanding before the app writes debt, wallet, schedule, expense, and asset state.

## 2026-06-03 - Payment Plan Financial Event And Reference Types

### Decision

Use a strict separation:

```text
FinancialEvent.event_type = broad money behavior
FinancialEvent.reference_type = specific business reason for that money movement
DebtLedgerEntry.entry_type = debt balance lifecycle reason
```

### Debt Initial Versus Loan Disbursement

Use:

```text
DebtLedgerEntry.entry_type = INITIAL
```

whenever a debt/payment-plan obligation starts.

Use:

```text
FinancialEvent.reference_type = DEBT_INITIAL
```

only for a general/informal initial debt wallet movement, such as a friend lending the user cash or the user lending money to someone.

Use:

```text
FinancialEvent.reference_type = LOAN_DISBURSEMENT
```

when a bank/lender loan is paid out into the user's wallet.

### Rationale

`DEBT_INITIAL` means an initial debt-related wallet movement happened. It does not describe bank loan payout clearly enough.

`LOAN_DISBURSEMENT` means borrowed loan money entered the user's wallet and is not income.

Some payment plans start a debt without any wallet inflow. Example: store installment where the user receives a phone, not cash. In those cases, only the debt ledger gets an `INITIAL` entry; no `DEBT_INITIAL` financial event is needed for the financed remainder.

### Payment Plan Event Map

```text
Bank loan / microloan disbursement:
  FinancialEvent.event_type = DEBT_SETTLEMENT
  FinancialEvent.reference_type = LOAN_DISBURSEMENT
  WalletLedger.amount = +loan_amount
  DebtLedgerEntry.entry_type = INITIAL
  DebtLedgerEntry.event_subtype = LOAN_DISBURSEMENT
```

```text
General/informal money-transferred debt creation:
  FinancialEvent.event_type = DEBT_SETTLEMENT
  FinancialEvent.reference_type = DEBT_INITIAL
  WalletLedger.amount = positive if user borrowed, negative if user lent
  DebtLedgerEntry.entry_type = INITIAL
```

```text
Payment plan upfront/down payment:
  FinancialEvent.event_type = EXPENSE
  FinancialEvent.reference_type = INSTALLMENT_DOWN_PAYMENT
  WalletLedger.amount = -upfront_payment
```

```text
Payment plan scheduled payment:
  FinancialEvent.event_type = EXPENSE
  FinancialEvent.reference_type = INSTALLMENT_PAYMENT
  WalletLedger.amount = -payment_amount
  DebtLedgerEntry.entry_type = PAYMENT
```

```text
Debt/payment-plan principal repayment:
  FinancialEvent.event_type = DEBT_SETTLEMENT
  FinancialEvent.reference_type = DEBT_REPAYMENT
  DebtLedgerEntry.entry_type = PAYMENT
```

```text
Debt/payment-plan interest, penalty, or fee payment:
  FinancialEvent.event_type = EXPENSE
  FinancialEvent.reference_type = DEBT_CHARGE
  DebtLedgerEntry.entry_type = PAYMENT or CHARGE depending whether charge is created or paid
```

### Naming Note

`DEBT_SETTLEMENT` currently functions as a broad debt-principal wallet movement type, not only final payoff. A better future enum name would be `DEBT_FLOW` or `DEBT_PRINCIPAL_FLOW`, but that requires a DB enum migration and is not required for the Payment Plans guided flow.

## 2026-06-03 - Debt Creation Guided Flow

### Decision

Debt creation should use a guided flow with natural user wording and no technical enum/database language in the UI.

### Flow

```text
1. Who owes money?
   - I owe someone
   - Someone owes me

2. What kind of relationship is this?
   - Personal
   - Formal

3. What created this debt?
   Personal + I owe:
     - I borrowed money
     - Someone paid for me / I will pay later

   Personal + someone owes me:
     - I lent money
     - They owe me for unpaid income/work

   Formal + I owe:
     - Bank/lender gave me money
     - Company/provider billed me / I will pay later

   Formal + someone owes me:
     - I formally lent money
     - Company/client owes me unpaid income

4. Money impact today
   If wallet money moved:
     - Ask wallet rows.
     - Derive the total debt amount from wallet row totals.
     - Show total as read-only.

   If no wallet money moved:
     - Ask total amount directly.
     - Ask category for payable deferred expenses.
     - Ask income source for receivable unpaid income.

5. Expected date
   - Optional.
   - Uses existing expected_return_date field.
   - If provided, must not be before the debt date.

6. Review and confirm
   - Explain what wallet changes now.
   - Explain whether this is borrowed/lent money, expense-backed debt, or income-backed receivable.
   - Do not show transaction_type, reference_type, origin_kind, or other internal names to users.
```

### Event Map

```text
Personal + I owe + borrowed money:
  Creation: wallet +amount, DebtLedger INITIAL, FinancialEvent DEBT_SETTLEMENT / DEBT_INITIAL
  Principal repayment: DEBT_SETTLEMENT / DEBT_REPAYMENT
  Charge paid: EXPENSE / DEBT_CHARGE
```

```text
Personal + I owe + deferred expense:
  Creation: DebtLedger INITIAL only, category required, no wallet movement
  Principal payment: EXPENSE / DEBT_EXPENSE
  Charge paid: EXPENSE / DEBT_CHARGE
```

```text
Personal + someone owes me + I lent money:
  Creation: wallet -amount, DebtLedger INITIAL, FinancialEvent DEBT_SETTLEMENT / DEBT_INITIAL
  Principal repayment received: DEBT_SETTLEMENT / DEBT_REPAYMENT
  Charge received: INCOME / DEBT_CHARGE
```

```text
Personal + someone owes me + unpaid income:
  Creation: DebtLedger INITIAL only, income source required, no wallet movement
  Payment received: INCOME / DEBT_INCOME
  Late fee received: INCOME / DEBT_CHARGE
```

```text
Formal + I owe + borrowed money:
  Creation: wallet +amount, DebtLedger INITIAL, FinancialEvent DEBT_SETTLEMENT / LOAN_DISBURSEMENT
  Principal repayment: DEBT_SETTLEMENT / DEBT_REPAYMENT
  Interest/fee paid: EXPENSE / DEBT_CHARGE
```

```text
Formal + I owe + deferred bill:
  Creation: DebtLedger INITIAL only, category required, no wallet movement
  Principal payment: EXPENSE / DEBT_EXPENSE
  Penalty/fee paid: EXPENSE / DEBT_CHARGE
```

```text
Formal + someone owes me + formal lending:
  Creation: wallet -amount, DebtLedger INITIAL, FinancialEvent DEBT_SETTLEMENT / DEBT_INITIAL
  Principal repayment received: DEBT_SETTLEMENT / DEBT_REPAYMENT
  Interest received: INCOME / DEBT_CHARGE
```

```text
Formal + someone owes me + unpaid invoice:
  Creation: DebtLedger INITIAL only, income source required, no wallet movement
  Payment received: INCOME / DEBT_INCOME
  Late fee received: INCOME / DEBT_CHARGE
```

### Amount Rule

```text
If wallet rows exist:
  debt amount = sum(wallet rows)
  total amount is read-only in UI

If no wallet rows exist:
  user enters debt amount directly
```

This same derived-amount rule should later be applied to debt payments and payment-plan payments.
