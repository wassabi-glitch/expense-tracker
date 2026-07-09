/**
 * Shared cache-side-effect behaviour for ledger-adjacent mutations.
 *
 * Each function represents a *named invalidation consequence*.
 * Mutation hooks call these instead of hand-writing broad invalidation
 * arrays.  When a new view is added, the consequence is updated in one
 * place — every caller inherits it.
 *
 * Compatibility: existing query-key spellings remain supported throughout
 * migration.  The module re-exports canonical keys from queryKeys.js.
 */

import {
  QK_EXPENSES,
  QK_WALLETS,
  QK_INCOME,
  QK_DEBTS,
  QK_ASSETS,
  QK_PROJECTS,
  QK_BUDGETS,
  QK_BUDGETS_DETAIL,
  QK_BUDGETS_MONTH_STATS,
  QK_DASHBOARD,
  QK_DASHBOARD_SUMMARY,
  QK_DASHBOARD_RECURRING,
  QK_ANALYTICS,
  QK_NOTIFICATIONS,
  QK_MONEY_IN,
  QK_RECURRING_LIST,
  QK_RECURRING_OCCURRENCES,
  QK_GOALS,
  QK_PAYMENT_PLANS,
  QK_PAYMENT_PLANS_LEGACY,
  QK_EXPECTED_INFLOWS,
  QK_USERS_ME,
} from "./queryKeys";

// Re-export for convenience
export { QK_EXPENSES, QK_WALLETS, QK_INCOME, QK_DEBTS, QK_ASSETS };
export { QK_PROJECTS, QK_BUDGETS, QK_BUDGETS_DETAIL, QK_BUDGETS_MONTH_STATS };
export { QK_DASHBOARD, QK_DASHBOARD_SUMMARY, QK_DASHBOARD_RECURRING };
export { QK_ANALYTICS, QK_NOTIFICATIONS, QK_MONEY_IN, QK_RECURRING_LIST };
export { QK_RECURRING_OCCURRENCES, QK_GOALS, QK_PAYMENT_PLANS, QK_PAYMENT_PLANS_LEGACY };
export { QK_EXPECTED_INFLOWS, QK_USERS_ME };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function invalidateKeys(queryClient, keys) {
  return Promise.all(
    keys.map((key) => queryClient.invalidateQueries({ queryKey: key }))
  );
}

// ---------------------------------------------------------------------------
// Named invalidation consequences
// ---------------------------------------------------------------------------

/**
 * Full ledger refresh — invalidates every view that reflects ledger truth
 * or plan health.  Use when the mutation affects multiple domains.
 *
 * Equivalent to the broad invalidations previously copied into each
 * Expense / Wallet / Income mutation hook.
 */
export function invalidateLedgerViews(queryClient) {
  return invalidateKeys(queryClient, [
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
    QK_BUDGETS_MONTH_STATS,
  ]);
}

/**
 * Expense-domain invalidation.
 * Refreshes expense lists, dashboard, wallets (balances), analytics,
 * budget month stats, notifications, and debts.
 */
export function invalidateExpenseViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_EXPENSES,
    QK_DASHBOARD,
    QK_DASHBOARD_SUMMARY,
    QK_WALLETS,
    QK_ANALYTICS,
    QK_BUDGETS_MONTH_STATS,
    QK_NOTIFICATIONS,
    QK_DEBTS,
  ]);
}

/**
 * Wallet creation invalidation.
 * Refreshes wallet list and dashboard summary only.
 */
export function invalidateWalletCreate(queryClient) {
  return invalidateKeys(queryClient, [QK_WALLETS, QK_DASHBOARD_SUMMARY]);
}

/**
 * Wallet-domain invalidation for money-movement mutations
 * (update, delete, transfer, reconcile).
 * Refreshes wallet list, dashboard summary, expenses, income, and debts.
 */
export function invalidateWalletMoneyMovement(queryClient) {
  return invalidateKeys(queryClient, [
    QK_WALLETS,
    QK_DASHBOARD_SUMMARY,
    QK_EXPENSES,
    QK_INCOME,
    QK_DEBTS,
  ]);
}

/**
 * Wallet transaction invalidation (fee, interest) — same as money
 * movement plus budget views.
 */
export function invalidateWalletTransaction(queryClient) {
  return invalidateKeys(queryClient, [
    QK_WALLETS,
    QK_DASHBOARD_SUMMARY,
    QK_EXPENSES,
    QK_INCOME,
    QK_DEBTS,
    QK_BUDGETS,
  ]);
}

/**
 * Narrow wallet-list-only invalidation — for mutations that only affect
 * wallet metadata (e.g. set-default).
 */
export function invalidateWalletList(queryClient) {
  return invalidateKeys(queryClient, [QK_WALLETS]);
}

/**
 * Income / money-in invalidation.
 */
export function invalidateIncomeViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_INCOME,
    QK_MONEY_IN,
    QK_DASHBOARD,
    QK_DASHBOARD_SUMMARY,
    QK_WALLETS,
    QK_ANALYTICS,
    QK_NOTIFICATIONS,
  ]);
}

/**
 * Budget-domain invalidation — refreshes project, budget, and analytics
 * views affected by project lifecycle or structure changes.
 */
export function invalidateProjectViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_PROJECTS,
    QK_BUDGETS,
    QK_BUDGETS_DETAIL,
    QK_BUDGETS_MONTH_STATS,
    QK_EXPENSES,
    QK_DASHBOARD,
    QK_ANALYTICS,
  ]);
}

/**
 * Debt-domain invalidation.
 * Refreshes debts, wallets, user profile, dashboard, analytics,
 * notifications, and income.
 */
export function invalidateDebtViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_DEBTS,
    QK_WALLETS,
    QK_USERS_ME,
    QK_DASHBOARD,
    QK_DASHBOARD_SUMMARY,
    QK_ANALYTICS,
    QK_NOTIFICATIONS,
    QK_INCOME,
  ]);
}

/**
 * Payment-Plan-domain invalidation.
 * Refreshes payment plans, expenses, budgets, wallets, goals, assets,
 * user profile, dashboard, analytics, and notifications.
 * Includes legacy payment-plans (dash) spelling for compatibility.
 */
export function invalidatePaymentPlanViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_PAYMENT_PLANS,
    QK_PAYMENT_PLANS_LEGACY,
    QK_EXPENSES,
    QK_BUDGETS,
    QK_BUDGETS_MONTH_STATS,
    QK_WALLETS,
    QK_GOALS,
    QK_ASSETS,
    QK_USERS_ME,
    QK_DASHBOARD,
    QK_DASHBOARD_SUMMARY,
    QK_ANALYTICS,
    QK_NOTIFICATIONS,
  ]);
}

/**
 * Goal-domain invalidation.
 * Refreshes goals, debts, payment plans, wallets, projects, budgets,
 * user profile, dashboard, analytics, and notifications.
 * Preserves protected real-money behaviour.
 */
export function invalidateGoalViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_GOALS,
    QK_DEBTS,
    QK_PAYMENT_PLANS,
    QK_WALLETS,
    QK_PROJECTS,
    QK_BUDGETS,
    QK_USERS_ME,
    QK_DASHBOARD,
    QK_ANALYTICS,
    QK_NOTIFICATIONS,
  ]);
}

/**
 * Asset-domain invalidation.
 * Refreshes assets, wallets, dashboard summary, expenses, and income.
 */
export function invalidateAssetViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_ASSETS,
    QK_WALLETS,
    QK_DASHBOARD_SUMMARY,
    QK_EXPENSES,
    QK_INCOME,
  ]);
}

/**
 * Budget-permission invalidation.
 * Refreshes budget lists, month summaries, month stats, and notifications.
 */
export function invalidateBudgetViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_BUDGETS,
    QK_BUDGETS_MONTH_STATS,
    QK_NOTIFICATIONS,
  ]);
}

/**
 * Expected-Inflow-domain invalidation.
 * Refreshes expected inflows, budgets, money-in, wallets, debts,
 * assets, and expenses.
 */
export function invalidateExpectedInflowViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_EXPECTED_INFLOWS,
    QK_BUDGETS,
    QK_MONEY_IN,
    QK_WALLETS,
    QK_DEBTS,
    QK_ASSETS,
    QK_EXPENSES,
  ]);
}

/**
 * Recurring-domain invalidation — base.
 * Refreshes recurring list, occurrences, and dashboard recurring.
 */
export function invalidateRecurringViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_RECURRING_LIST,
    QK_RECURRING_OCCURRENCES,
    QK_DASHBOARD_RECURRING,
  ]);
}

/**
 * Recurring confirmation invalidation.
 * When a recurring occurrence is confirmed into a real expense the wallet
 * balances and expense list must also refresh.
 */
export function invalidateRecurringConfirmationViews(queryClient) {
  return invalidateKeys(queryClient, [
    QK_RECURRING_LIST,
    QK_RECURRING_OCCURRENCES,
    QK_DASHBOARD_RECURRING,
    QK_WALLETS,
    QK_EXPENSES,
  ]);
}
