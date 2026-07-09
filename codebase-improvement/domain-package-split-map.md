# Post-Deepening Domain Package Split Map

**Issue:** PRD 3 Issue 6
**Status:** DRAFT — requires human approval before file moves begin
**Date:** 2026-07-07

## 1. Current State

The backend currently has two flat directories:

- `app/services/` — 25+ files, some very large (budget_service.py = 2301 lines)
- `app/routers/` — 17+ files, mostly thin but with domain logic mixed in (goals.py = 2770 lines, debts.py = 2357 lines, expenses.py = 2407 lines)

Most routers import from 5–15 services, creating a dense import graph. Domain logic, permission checks, ledger posting, and reporting all live in the same namespace.

## 2. Proposed Domain Packages

Each package lives under `app/domains/` with a `__init__.py` that re-exports only the stable public interface. Internal modules get a leading underscore.

### 2.1 Ledger (`app/domains/ledger/`)

**Owns:** Immutable double-entry Financial Event records.
- `_models.py` — FinancialEvent, WalletLedger, EntityLedger (moved from models.py)
- `_ledger_service.py` — `post_financial_event`, `PostWalletLeg`, `PostEntityLeg` (moved from financial_event_ledger_service.py)
- `__init__.py` — exports `post_financial_event`, `PostWalletLeg`, `PostEntityLeg`

**Stable seam:** Everything that writes money goes through `post_financial_event`. No domain logic in the ledger — it's a pure recording engine.

**Dependencies:** None (leaf package).

**Tests:** `test_financial_event_ledger.py`, `test_session_finalize_ledger.py`, `test_void_reversal_ledger.py`, `test_refund_ledger.py`, `test_income_ledger.py`, `test_transfer_reconcile_ledger.py`

---

### 2.2 Posting (`app/domains/posting/`)

**Owns:** Expense posting orchestration — wallet allocation resolution, budget permission check, goal protection, subcategory/project link validation, and the `post_expense_event` service.
- `_models.py` — ExpenseCategory, TransactionType enums (moved from models.py)
- `_posting_service.py` — `post_expense_event`, `validate_real_expense_category`, `resolve_expense_wallet_allocations` (moved from expense_posting_service.py)
- `_category_policy.py` — `validate_active_expense_category` (moved from category_policy.py)
- `__init__.py` — exports `post_expense_event`, `ExpensePostingResult`

**Stable seam:** `post_expense_event(db, user_id, *, title, amount, category, expense_date, ...) -> ExpensePostingResult`

**Dependencies:** `ledger` (post_financial_event), `budget_permission` (check_budget_permission), `goals` (goal protection for outflow), `projects` (validate_session_item_links)

**Tests:** `test_expenses.py` (expense creation portion), `test_budget_permission.py`

---

### 2.3 Budget Permission (`app/domains/budget_permission/`)

**Owns:** Write-time spending permission — "can this user spend X in category Y this month?"
- `_permission_service.py` — `check_budget_permission`, `BudgetPermissionRequest` (moved from budget_permission_service.py)
- `__init__.py` — exports `check_budget_permission`, `BudgetPermissionRequest`

**Stable seam:** `check_budget_permission(db, BudgetPermissionRequest(...)) -> BudgetPermissionResult`

**Dependencies:** `ledger` (for reading historical spend), `projects` (isolated project bypass logic)

**Tests:** `test_budget_permission.py`, `test_cross_flow_budget_interceptor.py`

---

### 2.4 Budget Reporting (`app/domains/budget_reporting/`)

**Owns:** Read-time budget display — budget chain computation, month summaries, project budget views.
- `_budget_service.py` — `build_budget_out`, `compute_budget_chain`, `materialize_budget_for_month`, `recompute_budget_chain`, `validate_budget_limit`, `validate_subcategory_limit` (moved from budget_service.py)
- `__init__.py` — exports budget display functions

**Stable seam:** `compute_budget_chain(db, user_id, budgets) -> list[BudgetChain]`

**Dependencies:** `ledger`, `projects` (project budget resolution)

**Tests:** `test_budget.py`

---

### 2.5 Wallets (`app/domains/wallets/`)

**Owns:** Wallet balance management, transfers, reconciliation, value classification.
- `_models.py` — Wallet, WalletType, AccountingType (moved from models.py)
- `_wallet_service.py` — `WalletService.adjust_balance`, `WalletService.record_transaction`, `WalletService.transfer_funds`, `WalletService.reconcile_balance` (moved from wallet_service.py)
- `_value_service.py` — `classify_outflow`, `OutflowFundingBreakdown` (moved from wallet_value_service.py)
- `__init__.py` — exports `WalletService`

**Stable seam:** `WalletService.adjust_balance(db, wallet_id, amount_delta)`

**Dependencies:** `ledger` (post_financial_event)

**Tests:** `test_wallets.py`

---

### 2.6 Goals (`app/domains/goals/`)

**Owns:** Goal lifecycle — funding, allocation, release, consumption, progress tracking, obligation-pay goals.
- `_models.py` — Goals, GoalIntent, GoalStatus (moved from models.py)
- `_funding_service.py` — goal funding, allocation, release, progress (moved from goal_funding_service.py)
- `__init__.py` — exports `build_goal_with_progress`, goal funding helpers

**Stable seam:** `build_goal_with_progress(db, user_id, goal, funded_amount, ...)`

**Dependencies:** `wallets` (goal-protected balance queries)

**Tests:** `test_goals.py`

---

### 2.7 Projects (`app/domains/projects/`)

**Owns:** Project lifecycle — overlay projects, project budgets, project subcategories. **Frozen Isolated Project compatibility is quarantined here** (see Section 3).
- `_models.py` — Project, LegacyProjectSubcategory (moved from models.py)
- `_project_service.py` — `get_owned_project_or_404`, `is_isolated_project`, project CRUD helpers (moved from project_service.py)
- `_overlay_service.py` — overlay project budget behavior (moved from overlay_project_service.py)
- `_quarantine/` — Frozen Isolated Project compatibility contract (see Section 3)
- `__init__.py` — exports active project functions only; quarantine is opt-in

**Stable seam:** `get_owned_project_or_404(db, user_id, project_id) -> Project`, `is_isolated_project(project) -> bool`

**Dependencies:** `wallets` (project funding allocations), `budget_permission` (monthly-budget bypass for isolated projects)

**Tests:** `test_project_completion.py`, `test_project_deletion.py`, `test_project_date_migrations.py`, `test_project_isolated_*.py`

---

### 2.8 Debt (`app/domains/debt/`)

**Owns:** Open-ended running-balance obligations — debt CRUD, charges, payments, ledger entries, reconciliation, forgiveness, policy decisions. **Must NOT be merged with Payment Plans.**
- `_models.py` — Debt, DebtLedgerEntry, DebtTransaction, DebtCharge (moved from models.py)
- `_debt_service.py` — ledger entries, reconciliation, charge/paid queries (moved from debt_service.py)
- `_payment_service.py` — payment creation with wallet allocation, charge-vs-principal splitting (moved from debt_payment_service.py)
- `_policy.py` — `evaluate_debt_action`, `evaluate_ledger_entry_reversal`, `is_pristine_debt` (moved from debt_policy.py)
- `__init__.py` — exports debt service functions

**Stable seam:** `create_debt_payment(db, debt, *, amount, transaction_date, wallet_allocations, ...)`, `reconcile_debt(db, debt_id)`

**Dependencies:** `ledger`, `posting` (post_expense_event for expense-shaped payments), `wallets`, `goals` (sync_debt_goal_targets)

**Tests:** `test_debts.py`, `test_debt_action_routes.py`, `test_debt_policy.py`, `test_debt_charge_ledger.py`

---

### 2.9 Payment Plans (`app/domains/payment_plans/`)

**Owns:** Scheduled obligations with rows and waterfall behavior — plan CRUD, payment schedules, charge rows, payment marking, write-offs. **Must NOT be merged with Debt.**
- `_models.py` — PaymentPlan, PaymentPlanPayment, PaymentPlanLedgerEntry (moved from models.py)
- `__init__.py` — exports payment plan functions (currently inline in router; should be extracted)

**Stable seam:** `_create_payment_plan_expense_event(db, owner_id, *, title, amount, category, expense_date, ...)` — already delegates to `post_expense_event` through Posting domain.

**Dependencies:** `ledger`, `posting` (post_expense_event), `wallets`, `goals`

**Tests:** `test_payment_plan_routes.py`, `test_payment_plan_ledger.py`, `test_payment_plan_accounting_migration.py`

---

### 2.10 Income (`app/domains/income/`)

**Owns:** Income sources, income entries, expected inflows, inflow realization, rescheduling, write-offs.
- `_models.py` — IncomeSource, ExpectedIncome, ExpectedInflowPromise, ExpectedInflowRealization (moved from models.py)
- `_expected_inflow_service.py` — promise/schedule lifecycle, realization, reschedule, write-off (moved from expected_inflow_service.py)
- `__init__.py` — exports income functions

**Stable seam:** `create_promise(db, owner_id, payload, *, today)`, `realize_promise(db, owner_id, promise_id, payload, *, today)`

**Dependencies:** `ledger`, `posting` (for earned income), `debt` (for receivable income), `wallets`

**Tests:** `test_income.py`, `test_expected_inflows.py`, `test_income_ledger.py`

---

### 2.11 Recurring (`app/domains/recurring/`)

**Owns:** Recurring expense templates, occurrence confirmation, skip, scheduler behavior.
- `_models.py` — RecurringExpense, RecurringEvent (moved from models.py)
- `_occurrence_service.py` — `confirm_recurring_occurrence`, `skip_occurrence` (moved from recurring_occurrence_service.py)
- `_schedule_service.py` — `calculate_next_due_date`, `first_due_after` (moved from recurring_schedule_service.py)
- `__init__.py` — exports recurring functions

**Stable seam:** `confirm_recurring_occurrence(db, user_id, recurring_id, *, local_today)`

**Dependencies:** `posting` (post_expense_event for auto-record)

**Tests:** `test_recurring_expenses.py`

---

### 2.12 Session Drafts (`app/domains/session_drafts/`)

**Owns:** Session draft lifecycle — items, wallet allocations, splits, finalization.
- `_draft_service.py` — `finalize_session_draft`, `build_session_draft_out`, validation (moved from session_draft_service.py)
- `__init__.py` — exports draft functions

**Stable seam:** `finalize_session_draft(db, owner_id, draft_id, local_today) -> SessionFinalizeResult`

**Dependencies:** `ledger`, `posting`, `budget_permission`, `projects`

**Tests:** `test_session_finalize_ledger.py`

---

### 2.13 Reports (`app/domains/reports/`)

**Owns:** Analytics, export, timeline views.
- `_analytics_service.py` — analytics queries and computations
- `_export_service.py` — CSV export formatting
- `__init__.py` — exports report functions

**Dependencies:** `ledger` (read-only), `budget_reporting` (read-only)

**Tests:** `test_analytics.py`, `test_export.py`

---

### 2.14 Cross-Cutting (`app/crosscutting/`)

Not a domain, but shared infrastructure:
- `timezone.py` — timezone resolution (already exists)
- `oauth2.py` — authentication
- `session.py` — DB session management
- `redis_rate_limiter.py` — rate limiting
- `utils.py` — shared utilities (check_budget_alerts, etc.)
- `email_service.py` — email notifications
- `config.py` — settings

---

## 3. Frozen Isolated Project Quarantine

Per ADR-0022, Isolated Projects and Fund Project work are **frozen**. The quarantine lives at:

```
app/domains/projects/_quarantine/
    __init__.py        # re-exports only the compatibility surface
    _contract.py       # documents what stable core can ask
    _isolated.py       # moved from isolated_project_service.py
    _fund_project.py   # fund project goal graduation (frozen)
```

**Compatibility contract (allowed queries):**
1. `is_isolated_project(project: Project) -> bool` — needed by budget permission to decide monthly-budget bypass
2. Isolated project records remain readable where currently supported (list, detail views)
3. Overlay project behavior remains outside the quarantine (it's in the active `_overlay_service.py`)

**Explicitly NOT allowed (quarantine must reject):**
- New Isolated Project creation
- Fund Project graduation
- Top-ups, rebalancing, stash release, sweep
- Project-protection breach resolution
- New isolated micro-subcategory behavior

**Import rule:** Stable core modules (`posting`, `budget_permission`, `budget_reporting`) import ONLY from `app.domains.projects._quarantine.__init__`, never from `_isolated.py` directly. The compatibility surface is narrow and documented.

---

## 4. Compatibility Strategy

During the transition:
1. Each package's `__init__.py` exports the same symbols the old flat imports expect
2. `app/services/` retains thin compatibility re-exports:
   ```python
   # app/services/expense_posting_service.py (compat shim)
   from app.domains.posting import post_expense_event, ExpensePostingResult
   ```
3. `app/models.py` and `app/schemas.py` keep all model/schema definitions OR each domain package defines its own models with the central files importing from packages
4. Routes continue importing from `app.services.*` — the shim layer prevents breakage
5. Over 2–3 PRs, routes migrate to import from `app.domains.*` directly

**Rollback safety:** The compat shims mean any package split can be reverted by simply moving files back — no logic changes.

---

## 5. Migration Order (Dependency-Driven)

| Order | Package | Blocked By | Risk |
|-------|---------|------------|------|
| 1 | `ledger` | None (leaf) | Low — pure recording engine |
| 2 | `crosscutting` | None | Low — already self-contained |
| 3 | `wallets` | `ledger` | Medium — WalletService is widely used |
| 4 | `projects` (active only) | `wallets` | Medium — needs quarantine contract |
| 5 | `budget_permission` | `ledger`, `projects` | Medium |
| 6 | `budget_reporting` | `ledger`, `projects` | High — largest file (2301 lines) |
| 7 | `goals` | `wallets` | Medium |
| 8 | `posting` | `ledger`, `budget_permission`, `goals`, `projects` | Medium |
| 9 | `session_drafts` | `posting`, `budget_permission`, `projects` | Low |
| 10 | `debt` | `ledger`, `posting`, `wallets`, `goals` | Medium |
| 11 | `payment_plans` | `ledger`, `posting`, `wallets`, `goals` | Medium |
| 12 | `income` | `ledger`, `posting`, `debt`, `wallets` | Medium |
| 13 | `recurring` | `posting` | Low |
| 14 | `reports` | `ledger`, `budget_reporting` | Low |

---

## 6. Tests That Must Pass After Each Move

Each package split must keep these passing:

| Package | Key Test Suites |
|---------|----------------|
| `ledger` | `test_financial_event_ledger.py`, `test_*_ledger.py` |
| `wallets` | `test_wallets.py` |
| `budget_permission` | `test_budget_permission.py`, `test_cross_flow_budget_interceptor.py` |
| `budget_reporting` | `test_budget.py` |
| `goals` | `test_goals.py` |
| `posting` | `test_expenses.py` |
| `debt` | `test_debts.py`, `test_debt_action_routes.py`, `test_debt_policy.py`, `test_debt_charge_ledger.py` |
| `payment_plans` | `test_payment_plan_routes.py`, `test_payment_plan_ledger.py` |
| `income` | `test_income.py`, `test_expected_inflows.py`, `test_income_ledger.py` |
| `recurring` | `test_recurring_expenses.py` |
| All | `test_user_date_seam_timezone_boundary.py` |

---

## 7. Import Rules

1. **No circular imports.** Packages form a DAG. `ledger` is the root.
2. **Domain packages import from `crosscutting`** but never from each other's `_internal` modules.
3. **Routers import from `__init__.py`** of each domain package — never from `_internal` modules.
4. **Shared money-posting mechanics** stay in `posting` (expense posting) and `ledger` (event recording). Both Debt and Payment Plans delegate to these.
5. **Debt and Payment Plan MUST NOT share models, schemas, or lifecycle code.** They remain separate domains that both delegate to `posting`/`ledger` for the money movement part.
6. **Frozen Isolated Project internals** (`_quarantine/_isolated.py`) are NEVER imported directly by stable core. Always go through the quarantine `__init__.py`.

---

## 8. Approval Checklist

- [ ] Package boundaries follow stable domain seams (not file size)
- [ ] Expense Posting, Financial Event Ledger, Budget Permission, Budget Reporting, Wallets, Goals, Projects, Debt, Payment Plans, Income, Expected Inflows, Recurring, and Reports each have clear ownership
- [ ] Debt and Payment Plan remain separate domains
- [ ] Frozen Isolated Project behavior is not promoted into active core
- [ ] Compatibility export/transition strategy is defined (Section 4)
- [ ] Dependency order for package moves is defined (Section 5)
- [ ] Tests that must pass after each move are identified (Section 6)

---

**Human approval:** ☐ Approved / ☐ Changes requested

Signed: _____________ Date: _____________
