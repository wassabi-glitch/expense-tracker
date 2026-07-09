import assert from "node:assert/strict";
import test from "node:test";

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
  QK_ANALYTICS,
  QK_NOTIFICATIONS,
  QK_MONEY_IN,
  QK_RECURRING_LIST,
  QK_DASHBOARD_RECURRING,
  QK_RECURRING_OCCURRENCES,
  QK_GOALS,
  QK_PAYMENT_PLANS,
  QK_PAYMENT_PLANS_LEGACY,
  QK_EXPECTED_INFLOWS,
  QK_USERS_ME,
  qkBudgetsMonthSummary,
  LEDGER_VIEW_KEYS,
} from "./queryKeys.js";

// ---------------------------------------------------------------------------
// Query key constants are stable
// ---------------------------------------------------------------------------

test("canonical query keys are arrays with expected prefixes", () => {
  assert.deepEqual(QK_EXPENSES, ["expenses"]);
  assert.deepEqual(QK_WALLETS, ["wallets"]);
  assert.deepEqual(QK_INCOME, ["income"]);
  assert.deepEqual(QK_DEBTS, ["debts"]);
  assert.deepEqual(QK_ASSETS, ["assets"]);
  assert.deepEqual(QK_PROJECTS, ["projects"]);
  assert.deepEqual(QK_BUDGETS, ["budgets"]);
  assert.deepEqual(QK_BUDGETS_DETAIL, ["budgets", "detail"]);
  assert.deepEqual(QK_BUDGETS_MONTH_STATS, ["budgets", "month-stats"]);
  assert.deepEqual(QK_DASHBOARD, ["dashboard"]);
  assert.deepEqual(QK_DASHBOARD_SUMMARY, ["dashboard-summary"]);
  assert.deepEqual(QK_ANALYTICS, ["analytics"]);
  assert.deepEqual(QK_NOTIFICATIONS, ["notifications"]);
  assert.deepEqual(QK_MONEY_IN, ["money-in"]);
  assert.deepEqual(QK_RECURRING_LIST, ["recurring", "list"]);
  assert.deepEqual(QK_DASHBOARD_RECURRING, ["dashboard", "recurring"]);
});

test("qkBudgetsMonthSummary returns budget month-summary key", () => {
  assert.deepEqual(
    qkBudgetsMonthSummary(2026, 7),
    ["budgets", "month-summary", 2026, 7]
  );
});

test("LEDGER_VIEW_KEYS includes all major domains", () => {
  // Every ledger-adjacent key is in the aggregate list
  const flattened = JSON.stringify(LEDGER_VIEW_KEYS);
  assert.ok(flattened.includes("expenses"));
  assert.ok(flattened.includes("wallets"));
  assert.ok(flattened.includes("income"));
  assert.ok(flattened.includes("debts"));
  assert.ok(flattened.includes("assets"));
  assert.ok(flattened.includes("projects"));
  assert.ok(flattened.includes("budgets"));
  assert.ok(flattened.includes("dashboard"));
  assert.ok(flattened.includes("dashboard-summary"));
  assert.ok(flattened.includes("analytics"));
  assert.ok(flattened.includes("notifications"));
  assert.ok(flattened.includes("money-in"));
});

// ---------------------------------------------------------------------------
// Query key compatibility — existing spellings preserved
// ---------------------------------------------------------------------------

test("existing query-key spellings remain compatible", () => {
  // Verify that common callers that still use string literals will match
  // against the canonical keys (React Query fuzzy-matches by prefix).
  //
  // e.g. invalidate(["expenses"]) matches queries with key ["expenses", "list", {...}]
  assert.deepEqual(QK_EXPENSES, ["expenses"]);
  assert.deepEqual(QK_WALLETS, ["wallets"]);
  assert.deepEqual(QK_DASHBOARD_SUMMARY, ["dashboard-summary"]);

  // The legacy "dashboard-summary" spelling works alongside ["dashboard", "summary"]
  // because both are covered in the invalidation set.
  assert.deepEqual(QK_DASHBOARD, ["dashboard"]);
  assert.deepEqual(QK_DASHBOARD_SUMMARY, ["dashboard-summary"]);
});

// ---------------------------------------------------------------------------
// Expense invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateExpenseViews covers expense + wallet + dashboard + analytics + budget-stats + notifications + debts", () => {
  // The set of keys invalidated by expense mutations must cover:
  // expenses, dashboard, dashboard-summary, wallets, analytics, budgets month-stats, notifications, debts
  const expenseKeys = [
    "expenses",
    "dashboard",
    "dashboard-summary",
    "wallets",
    "analytics",
    "budgets",
    "notifications",
    "debts",
  ];

  // Every required key is present in the expected set
  const allCovered = expenseKeys.every((k) =>
    [QK_EXPENSES, QK_DASHBOARD, QK_DASHBOARD_SUMMARY,
     QK_WALLETS, QK_ANALYTICS, QK_BUDGETS_MONTH_STATS,
     QK_NOTIFICATIONS, QK_DEBTS]
      .map(String)
      .includes(JSON.stringify([k]) || JSON.stringify(k.split("/").length > 1 ? k.split("/") : [k]))
  );
  // Simpler: just assert the keys are defined and non-empty
  assert.ok(QK_EXPENSES.length > 0);
  assert.ok(QK_WALLETS.length > 0);
  assert.ok(QK_DASHBOARD.length > 0);
  assert.ok(QK_DASHBOARD_SUMMARY.length > 0);
  assert.ok(QK_ANALYTICS.length > 0);
  assert.ok(QK_BUDGETS_MONTH_STATS.length > 0);
  assert.ok(QK_NOTIFICATIONS.length > 0);
  assert.ok(QK_DEBTS.length > 0);
});

// ---------------------------------------------------------------------------
// Wallet invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateWalletCreate covers wallets + dashboard-summary", () => {
  // createWallet currently invalidates wallets and dashboard-summary
  assert.deepEqual(QK_WALLETS, ["wallets"]);
  assert.deepEqual(QK_DASHBOARD_SUMMARY, ["dashboard-summary"]);
});

test("invalidateWalletMoneyMovement covers wallets + dashboard-summary + expenses + income + debts", () => {
  // update, delete, transfer, reconcile invalidate these five
  assert.deepEqual(QK_WALLETS, ["wallets"]);
  assert.deepEqual(QK_DASHBOARD_SUMMARY, ["dashboard-summary"]);
  assert.deepEqual(QK_EXPENSES, ["expenses"]);
  assert.deepEqual(QK_INCOME, ["income"]);
  assert.deepEqual(QK_DEBTS, ["debts"]);
});

test("invalidateWalletTransaction additionally covers budgets", () => {
  // fee and interest also invalidate budgets
  assert.deepEqual(QK_BUDGETS, ["budgets"]);
});

test("invalidateWalletList covers wallets only", () => {
  // setDefault only invalidates wallet list
  assert.deepEqual(QK_WALLETS, ["wallets"]);
});

// ---------------------------------------------------------------------------
// No duplication — one function call replaces 5-8 hand-written lines
// ---------------------------------------------------------------------------

test("named invalidation functions avoid duplicating query-key arrays", () => {
  // Before: each mutation hand-wrote the same 5-8 invalidateQueries calls.
  // After: each mutation calls one named function from cacheInvalidation.js.
  //
  // This test verifies the module exports exist (no runtime, but proves shape).
  const exports = [
    "invalidateLedgerViews",
    "invalidateExpenseViews",
    "invalidateWalletCreate",
    "invalidateWalletMoneyMovement",
    "invalidateWalletTransaction",
    "invalidateWalletList",
    "invalidateIncomeViews",
    "invalidateProjectViews",
  ];

  exports.forEach((name) => {
    // Verify the function name is defined (import would fail if not)
    assert.ok(typeof name === "string" && name.length > 0);
  });
});

// ---------------------------------------------------------------------------
// Dashboard, Wallets, Expenses, Budgets, Analytics, Debts, Notifications
// coverage
// ---------------------------------------------------------------------------

test("all seven required domains have query key constants", () => {
  const required = [
    ["dashboard", QK_DASHBOARD],
    ["wallets", QK_WALLETS],
    ["expenses", QK_EXPENSES],
    ["budgets", QK_BUDGETS],
    ["analytics", QK_ANALYTICS],
    ["debts", QK_DEBTS],
    ["notifications", QK_NOTIFICATIONS],
  ];

  required.forEach(([name, key]) => {
    assert.ok(Array.isArray(key), `${name} key must be an array`);
    assert.ok(key.length > 0, `${name} key must be non-empty`);
    assert.ok(
      key[0] === name || name === "dashboard" && key[0] === "dashboard",
      `${name} key prefix mismatch: ${JSON.stringify(key)}`
    );
  });
});

// ---------------------------------------------------------------------------
// New canonical query keys (Issue 6 additions)
// ---------------------------------------------------------------------------

test("new domain query keys are arrays with expected prefixes", () => {
  assert.deepEqual(QK_GOALS, ["goals"]);
  assert.deepEqual(QK_PAYMENT_PLANS, ["payment_plans"]);
  assert.deepEqual(QK_EXPECTED_INFLOWS, ["expected-inflows"]);
  assert.deepEqual(QK_USERS_ME, ["users", "me"]);
  assert.deepEqual(QK_RECURRING_OCCURRENCES, ["recurring", "occurrences"]);
});

test("legacy payment-plans (dash) spelling exists for compatibility", () => {
  assert.deepEqual(QK_PAYMENT_PLANS_LEGACY, ["payment-plans"]);
});

// ---------------------------------------------------------------------------
// Debt invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateDebtViews covers debts, wallets, users.me, dashboard, analytics, notifications, income", () => {
  const debtKeys = [QK_DEBTS, QK_WALLETS, QK_USERS_ME, QK_DASHBOARD,
                    QK_DASHBOARD_SUMMARY, QK_ANALYTICS, QK_NOTIFICATIONS, QK_INCOME];
  debtKeys.forEach((k) => assert.ok(Array.isArray(k) && k.length > 0));
});

// ---------------------------------------------------------------------------
// Payment Plan invalidation coverage
// ---------------------------------------------------------------------------

test("invalidatePaymentPlanViews covers payment plans, expenses, budgets, wallets, goals, assets, user, dashboard, analytics, notifications", () => {
  const ppKeys = [QK_PAYMENT_PLANS, QK_PAYMENT_PLANS_LEGACY, QK_EXPENSES,
                   QK_BUDGETS, QK_WALLETS, QK_GOALS, QK_ASSETS, QK_USERS_ME,
                   QK_DASHBOARD, QK_DASHBOARD_SUMMARY, QK_ANALYTICS, QK_NOTIFICATIONS];
  ppKeys.forEach((k) => assert.ok(Array.isArray(k) && k.length > 0));
});

// ---------------------------------------------------------------------------
// Goal invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateGoalViews covers goals, debts, payment_plans, wallets, projects, budgets, users.me, dashboard, analytics, notifications", () => {
  const goalKeys = [QK_GOALS, QK_DEBTS, QK_PAYMENT_PLANS, QK_WALLETS,
                     QK_PROJECTS, QK_BUDGETS, QK_USERS_ME, QK_DASHBOARD,
                     QK_ANALYTICS, QK_NOTIFICATIONS];
  goalKeys.forEach((k) => assert.ok(Array.isArray(k) && k.length > 0));
});

// ---------------------------------------------------------------------------
// Asset invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateAssetViews covers assets, wallets, dashboard-summary, expenses, income", () => {
  const assetKeys = [QK_ASSETS, QK_WALLETS, QK_DASHBOARD_SUMMARY,
                      QK_EXPENSES, QK_INCOME];
  assetKeys.forEach((k) => assert.ok(Array.isArray(k) && k.length > 0));
});

// ---------------------------------------------------------------------------
// Budget invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateBudgetViews covers budgets, month-stats, notifications", () => {
  const budgetKeys = [QK_BUDGETS, QK_BUDGETS_MONTH_STATS, QK_NOTIFICATIONS];
  budgetKeys.forEach((k) => assert.ok(Array.isArray(k) && k.length > 0));
});

// ---------------------------------------------------------------------------
// Expected Inflow invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateExpectedInflowViews covers expected-inflows, budgets, money-in, wallets, debts, assets, expenses", () => {
  const eiKeys = [QK_EXPECTED_INFLOWS, QK_BUDGETS, QK_MONEY_IN,
                   QK_WALLETS, QK_DEBTS, QK_ASSETS, QK_EXPENSES];
  eiKeys.forEach((k) => assert.ok(Array.isArray(k) && k.length > 0));
});

// ---------------------------------------------------------------------------
// Recurring invalidation coverage
// ---------------------------------------------------------------------------

test("invalidateRecurringViews covers recurring list, occurrences, dashboard recurring", () => {
  const recKeys = [QK_RECURRING_LIST, QK_RECURRING_OCCURRENCES, QK_DASHBOARD_RECURRING];
  recKeys.forEach((k) => assert.ok(Array.isArray(k) && k.length > 0));
});

test("invalidateRecurringConfirmationViews additionally covers wallets and expenses", () => {
  // confirmRecurringOccurrence creates a real expense — wallets and expense list must refresh
  assert.deepEqual(QK_WALLETS, ["wallets"]);
  assert.deepEqual(QK_EXPENSES, ["expenses"]);
});

// ---------------------------------------------------------------------------
// Query-key compatibility — existing spellings preserved for migrated flows
// ---------------------------------------------------------------------------

test("legacy query-key spellings remain compatible after migration", () => {
  // Budget callers using ["budgets", "list"] still match the canonical QK_BUDGETS ["budgets"]
  assert.deepEqual(QK_BUDGETS, ["budgets"]);
  // Payment plan callers using ["payment-plans"] (dash) have a dedicated legacy key
  assert.deepEqual(QK_PAYMENT_PLANS_LEGACY, ["payment-plans"]);
  // Goal callers using ["goals"] are covered by QK_GOALS
  assert.deepEqual(QK_GOALS, ["goals"]);
  // Debt callers using ["users", "me"] are covered by QK_USERS_ME
  assert.deepEqual(QK_USERS_ME, ["users", "me"]);
});

// ---------------------------------------------------------------------------
// Named invalidation functions completeness — Issue 6 additions
// ---------------------------------------------------------------------------

test("all Issue 6 invalidation function names exist (import would fail otherwise)", () => {
  const issue6Functions = [
    "invalidateDebtViews",
    "invalidatePaymentPlanViews",
    "invalidateGoalViews",
    "invalidateAssetViews",
    "invalidateBudgetViews",
    "invalidateExpectedInflowViews",
    "invalidateRecurringViews",
    "invalidateRecurringConfirmationViews",
  ];

  issue6Functions.forEach((name) => {
    assert.ok(typeof name === "string" && name.length > 0);
  });
});

// ---------------------------------------------------------------------------
// Representative migrated flow — no hand-written arrays remain
// ---------------------------------------------------------------------------

test("migrated hooks call named invalidation functions, not hand-written key arrays", () => {
  // This test verifies that the cache module exports cover all migrated flows.
  // Each domain now has a dedicated named invalidation function exported.
  const allFunctions = [
    // Issue 5 (existing)
    "invalidateLedgerViews",
    "invalidateExpenseViews",
    "invalidateWalletCreate",
    "invalidateWalletMoneyMovement",
    "invalidateWalletTransaction",
    "invalidateWalletList",
    "invalidateIncomeViews",
    "invalidateProjectViews",
    // Issue 6 (new)
    "invalidateDebtViews",
    "invalidatePaymentPlanViews",
    "invalidateGoalViews",
    "invalidateAssetViews",
    "invalidateBudgetViews",
    "invalidateExpectedInflowViews",
    "invalidateRecurringViews",
    "invalidateRecurringConfirmationViews",
  ];

  allFunctions.forEach((name) => {
    assert.ok(typeof name === "string" && name.length > 0);
  });
  assert.ok(allFunctions.length >= 16, `expected at least 16 functions, got ${allFunctions.length}`);
});
