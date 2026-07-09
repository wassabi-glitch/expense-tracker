/**
 * Canonical query-key constants for ledger-adjacent frontend data sets.
 *
 * Owns the naming convention so mutation hooks and query hooks share
 * one source of truth.  Avoids spelling drift (e.g. "dashboard-summary"
 * vs. ["dashboard","summary"]) that silently skips invalidation.
 *
 * Callers may still use ad-hoc keys for non-ledger data; the goal is to
 * cover the main views that reflect ledger truth or plan health.
 */

// ---------------------------------------------------------------------------
// Top-level domain keys
// ---------------------------------------------------------------------------

export const QK_EXPENSES = ["expenses"];
export const QK_WALLETS = ["wallets"];
export const QK_INCOME = ["income"];
export const QK_DEBTS = ["debts"];
export const QK_ASSETS = ["assets"];
export const QK_PROJECTS = ["projects"];
export const QK_BUDGETS = ["budgets"];
export const QK_GOALS = ["goals"];
export const QK_PAYMENT_PLANS = ["payment_plans"];
export const QK_EXPECTED_INFLOWS = ["expected-inflows"];
export const QK_USERS_ME = ["users", "me"];

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export const QK_DASHBOARD = ["dashboard"];
export const QK_DASHBOARD_SUMMARY = ["dashboard-summary"]; /* legacy — kept for compatibility */
export const QK_DASHBOARD_RECURRING = ["dashboard", "recurring"];

// ---------------------------------------------------------------------------
// Budget sub-keys
// ---------------------------------------------------------------------------

export const QK_BUDGETS_DETAIL = ["budgets", "detail"];
export const QK_BUDGETS_MONTH_STATS = ["budgets", "month-stats"];

/**
 * Return the canonical query key for a budget month-summary.
 * Compatible with existing callers that use:
 *   ["budgets", "month-summary", year, month]
 */
export function qkBudgetsMonthSummary(year, month) {
  return ["budgets", "month-summary", year, month];
}

// ---------------------------------------------------------------------------
// Money-in
// ---------------------------------------------------------------------------

export const QK_MONEY_IN = ["money-in"];

// ---------------------------------------------------------------------------
// Analytics & notifications
// ---------------------------------------------------------------------------

export const QK_ANALYTICS = ["analytics"];
export const QK_NOTIFICATIONS = ["notifications"];

// ---------------------------------------------------------------------------
// Recurring
// ---------------------------------------------------------------------------

export const QK_RECURRING_LIST = ["recurring", "list"];
export const QK_RECURRING_OCCURRENCES = ["recurring", "occurrences"];
export const QK_PAYMENT_PLANS_LEGACY = ["payment-plans"]; /* legacy dash spelling — kept for compatibility */

// ---------------------------------------------------------------------------
// Aggregates: the set of keys that every ledger mutation should refresh
// ---------------------------------------------------------------------------

/**
 * All top-level keys invalidated by a ledger-side-effect (Expense / Wallet
 * / Income / Debt / Payment Plan) mutation.
 *
 * Callers should use `invalidateLedgerViews` from cacheInvalidation.js
 * rather than copying this list.
 */
export const LEDGER_VIEW_KEYS = [
  QK_EXPENSES,
  QK_WALLETS,
  QK_INCOME,
  QK_DEBTS,
  QK_ASSETS,
  QK_PROJECTS,
  QK_BUDGETS,
  QK_BUDGETS_DETAIL,
  QK_DASHBOARD,
  QK_DASHBOARD_SUMMARY,
  QK_ANALYTICS,
  QK_NOTIFICATIONS,
  QK_MONEY_IN,
];
