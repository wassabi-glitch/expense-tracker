# Epicspart2 Money-History Definition of Done

**Audience:** developers implementing new Epicspart2 money-history features.

**Purpose:** every ticket that touches money movement (expenses, income, debts, payment plans, assets, expected inflows, goals with contributions, transfers, reconciliation) must satisfy this standard before it is considered done.

This document is normative for Epicspart2. It distills Tickets 1–8 into a single checklist. Read it alongside [[0011-immutable-ledger-architecture]], [[0024-immutable-ledger-boundary-when-it-applies]], and [[0025-epicspart2-obligation-contract]].

---

## 1. The Wallet-Legs Test — When Append-Only History Applies

**Rule:** An operation must use append-only financial history if and only if it produces `WalletLedger` rows with non-zero amounts.

If money left or entered a wallet, the operation must never hard-delete or mutate the posted `FinancialEvent` in place. It must use one of the shared correction patterns (section 3).

If the operation did not touch a wallet, immutability is unnecessary — the row is metadata, planning intent, or a projection and can be updated or deleted directly.

### Examples

| Operation | Wallet legs? | Immutable? |
|-----------|-------------|------------|
| Post an expense | Yes — outflow | Append-only |
| Delete posted expense | Yes — wallet was touched | Void, don't hard-delete |
| Edit income amount | Yes — inflow changed | Correction repost |
| Edit income note | No — same legs | Update in place |
| Record debt payment | Yes — outflow | Append-only |
| Cancel debt payment | Yes — wallet was touched | Void the payment event |
| Delete pristine debt (no payments) | No | Delete directly |
| Undo payment plan payment | Yes — wallet was touched | Append reversal event |
| Delete budget | No — permission | Delete directly |
| Delete recurring template | No — intent | Archive/delete directly |
| Delete session draft | No — pre-posting | Delete directly |
| Archive goal (no contributions) | No — reservation | Archive directly |

### The one-line test

> **Did this operation produce wallet legs?** If yes → immutable. If no → mutable.

---

## 2. When Mutable Metadata Is Acceptable

**Rule:** Metadata fields that do not change wallet math may be updated in place without creating reversals or ledger entries.

### Always mutable (direct UPDATE)

- `title` on expenses, income, debt, payment plans
- `description` / `note` on any entity
- `counterparty_name` on debts
- `expected_return_date` on debts
- `color` on wallets
- `is_active` / `archived_at` on any entity

### Never mutable on posted events

- `amount` — use correction repost
- `wallet_id` / wallet allocation — use correction repost
- `category` — use correction repost
- `date` — use correction repost
- `source_id` / `income_source_id` — use correction repost

### The metadata test

> **Would this change alter the net wallet effect of any posted FinancialEvent?** If yes → immutable correction. If no → update in place.

---

## 3. The Four Correction Patterns

Every money-history feature must understand these four patterns and choose the correct one for each undo/correction operation.

| Pattern | What it does | When to use | Example |
|---------|-------------|-------------|---------|
| **Void** | Marks original VOIDED; appends a linked REVERSAL event with counter-balancing wallet and entity legs | Deleting posted money | `void_financial_event(db, event=event, ...)` |
| **Reversal** | Creates a new REVERSAL FinancialEvent linked to the original, negating every wallet and entity leg | Undoing a money event | `_create_financial_event_reversal(db, ...)` |
| **Correction repost** | Voids the original + posts a new POSTED event with corrected amounts, linked together | Changing amount, wallet, source, or date of posted income/expense | Route: `PUT /income/entries/{id}` with changed fields |
| **Current correction** | Records an adjustment in the current open period that references the closed period, without rewriting the closed period | Missed activity in a closed month | Reconciliation adjustment with note referencing the past period |

### How they differ

- **Void** is deletion — the original is VOIDED, net wallet effect is zero.
- **Reversal** is undo — same mechanism as void but may be triggered by an undo button rather than a delete button.
- **Correction repost** is edit — the original is voided AND a new corrected event is posted. Net wallet effect = corrected amount only.
- **Current correction** is a period-boundary adjustment — the closed period is untouched; a current-period entry absorbs the correction.

---

## 4. Wallet Epoch and User-Timezone Date Validation

### Wallet epoch

**Rule:** Every money-movement date must be validated against the wallet's creation date. No money can move through a wallet before that wallet existed.

- Same-day activity on the wallet creation date is allowed.
- The rule is per-wallet, not per-user.
- Multi-wallet operations must validate every touched wallet.
- Transfers must validate both source and destination wallets.

**Implementation seam:** `validate_wallet_epochs(db, wallet_ids={...}, event_date=...)` from `app.domains.ledger`.

### User-timezone dates

**Rule:** All user-facing date calculations must use the user's effective timezone.

- Use `get_effective_user_timezone` in FastAPI routes.
- Use `today_in_tz(user_tz)` for "today".
- Use `now_in_tz(user_tz)` for local-aware datetimes.
- The request timezone comes from `X-Timezone` header → user persisted tz → `settings.default_timezone` → UTC.

**Do not use:**
- `date.today()` or naive `datetime.now()` for user-visible business rules.
- Server-local dates.

### Closed-period behavior

- The current month is open for normal and reconciliation activity.
- A 5-day grace window allows month-end cleanup.
- Closed months reject direct backdated money entry.
- Missed closed-period activity becomes a current correction.

---

## 5. What Is NOT a Financial Ledger Event

The following entities are **planning, intent, permission, or pre-posting state** — not posted money. They must never be forced into the global financial ledger (`FinancialEvent` / `WalletLedger` / `EntityLedger`).

| Entity | Nature | Lifecycle |
|--------|--------|-----------|
| **Budget** | Monthly spending permission per category | Create, update, delete directly — no FinancialEvent |
| **Recurring template** | Draft schedule for future expenses | Create, archive, delete — only produces FinancialEvents when an occurrence is confirmed |
| **Session draft** | Pre-posting scratchpad for a multi-item expense | Create, edit, abandon, delete — only produces FinancialEvents when finalized |
| **Goal** (without contributions) | Reservation of intent to save | Create, archive, delete — only produces WalletLedger when contributions are made |
| **Expected inflow promise** | Cashflow planning projection | Create, update, archive — no wallet movement until realized |
| **Project** (without funding) | Organizational grouping | Create, update, archive — only produces FinancialEvents when funding is allocated |

### The test

> **Would deleting this entity erase a money fact from history?** If yes → it's a ledger event. If no → it's metadata or intent.

---

## 6. The Projections Rule

**Rule:** Current-state fields that summarize money history are projections. They must be computable from immutable ledger rows and must never be set directly without a corresponding ledger entry.

| Projection field | Computed from |
|-----------------|---------------|
| `wallet.current_balance` | `initial_balance + SUM(WalletLedger.amount)` |
| `debt.remaining_amount` | `SUM(DebtLedgerEntry.amount_delta) WHERE status = POSTED` |
| `payment_plan.remaining_amount` | `SUM(PaymentPlanLedgerEntry.amount_delta) WHERE status = POSTED` |

**Verification seam:** `verify_wallet_projection(db, wallet_id=...)` from `app.domains.ledger`.

Any test that touches wallet balances, debt balances, or payment plan balances should include a projection check to prove the current state matches the ledger history.

---

## 7. The Shared Seams

Every money-history feature must route money movement through these shared seams. Do not bypass them with manual row construction.

| Seam | Location | Purpose |
|------|----------|---------|
| `post_financial_event` | `app.domains.ledger` | Create any money event with wallet legs |
| `void_financial_event` | `app.domains.ledger` | Void a posted FinancialEvent (the shared reversal) |
| `post_expense_event` | `app.domains.posting` | Create expense-shaped events with budget, goal, epoch validation |
| `post_obligation_event` | `app.services.obligation_money_posting_service` | Delegate non-expense obligation events through the seam |
| `validate_wallet_epochs` | `app.domains.ledger` | Enforce per-wallet epoch boundaries |
| `verify_wallet_projection` | `app.domains.ledger` | Prove wallet balance matches ledger history |
| `create_debt_ledger_entry` | `app.domains.debt` | Append a row to the debt-specific ledger |
| `reconcile_debt` | `app.domains.debt` | Recompute debt remaining_amount from ledger |

---

## 8. Testing Checklist

Every Epicspart2 money-history ticket must include tests that cover these items. Not every test must be in the ticket's own test file — some are covered by existing regression suites — but the reviewer must be able to point to a passing test for each item.

### Money-movement tests

- [ ] **Create flow**: the new feature creates a POSTED `FinancialEvent` with `WalletLedger` and `EntityLedger` rows through the shared seam.
- [ ] **Wallet epoch**: the feature calls `validate_wallet_epochs` (or the posting seam calls it) and rejects dates before a wallet's creation.
- [ ] **User timezone**: dates use `user_timezone_today()` (tests) or `today_in_tz(user_tz)` (prod). A timezone-boundary test proves server date ≠ user date is handled correctly.
- [ ] **Future-date rejection**: if the feature accepts a date, future dates are rejected according to the user's local date.

### Immutability tests

- [ ] **No hard-delete**: the original `FinancialEvent` remains queryable after delete/undo/cancel. Status is VOIDED, not missing.
- [ ] **No in-place mutation**: amount, wallet, category, and date of the original POSTED event are unchanged after correction.
- [ ] **Reversal linkage**: the reversal event is linked to the original via `reverses_event_id` / `void_reversal_event_id`.
- [ ] **No double-application**: the net wallet effect after correction/void matches the expected projection (use `verify_wallet_projection`).

### Projection tests

- [ ] **Wallet balance**: after every create/void/correct flow, `verify_wallet_projection` is valid.
- [ ] **Remaining amount**: after every debt/payment-plan create/pay/reverse flow, `remaining_amount` matches the sum of the domain ledger entries.
- [ ] **No stale effects**: after a correction repost that changes a wallet, the old wallet has no residual effect.

### Non-money guardrail tests

- [ ] **Metadata-only edits**: updating title, description, note, or counterparty does not create new `FinancialEvent` or ledger rows.
- [ ] **Non-money entities**: budget, template, draft, and goal lifecycle operations do not create `FinancialEvent` rows.

### Existing regression suites

These test files encode the contract and should continue to pass:

- `tests/test_void_reversal_ledger.py` — shared void/reversal seam
- `tests/test_immutable_ledger_guardrails.py` — obligation guardrails (Ticket 7)
- `tests/test_wallet_projection_verification.py` — wallet projection (Ticket 8)
- `tests/test_income.py` — income correction reposts
- `tests/test_debt_charge_ledger.py` — debt posting seam
- `tests/test_payment_plan_ledger.py` — payment plan posting seam
- `tests/test_user_date_seam_timezone_boundary.py` — timezone boundaries

---

## References

- [[0011-immutable-ledger-architecture]] — Core decision: no hard deletes, reversal pattern, no amount mutations.
- [[0024-immutable-ledger-boundary-when-it-applies]] — The wallet-legs boundary: immutable iff wallet legs exist.
- [[0025-epicspart2-obligation-contract]] — Obligation-specific contract with PR checklist and forbidden patterns.
- `docs/epicspart2-tickets/tickets1-ledger-foundation.md` — Tickets 1–9 specification.
- `tests/test_immutable_ledger_guardrails.py` — Executable guardrails.
- `tests/test_wallet_projection_verification.py` — Projection verification tests.
