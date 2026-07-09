import assert from "node:assert/strict";
import test from "node:test";

import {
  getAssetSaleOptions,
  getEarnedOptions,
  getReceivableOptions,
  getRefundOptions,
  getSourceOptions,
} from "./ExpectedInflowSourcePicker.js";

// ---------------------------------------------------------------------------
// EARNED
// ---------------------------------------------------------------------------

test("getEarnedOptions returns only active income sources", () => {
  const sources = [
    { id: 1, name: "Salary", is_active: true },
    { id: 2, name: "Freelance", is_active: false },
    { id: 3, name: "Side gig", is_active: true },
  ];

  const options = getEarnedOptions(sources);

  assert.equal(options.length, 2);
  assert.equal(options[0].id, 1);
  assert.equal(options[0].label, "Salary");
  assert.equal(options[0].isActive, true);
  assert.equal(options[1].id, 3);
  assert.equal(options[1].label, "Side gig");
});

test("getEarnedOptions handles wrapped payload (items key)", () => {
  const sources = { items: [{ id: 1, name: "Salary", is_active: true }] };

  const options = getEarnedOptions(sources);

  assert.equal(options.length, 1);
  assert.equal(options[0].label, "Salary");
});

test("getEarnedOptions returns empty array for empty input", () => {
  assert.deepEqual(getEarnedOptions([]), []);
  assert.deepEqual(getEarnedOptions(null), []);
  assert.deepEqual(getEarnedOptions(undefined), []);
});

test("getEarnedOptions generates fallback label when name is missing", () => {
  const sources = [{ id: 99, is_active: true }];

  const options = getEarnedOptions(sources);

  assert.equal(options[0].label, "Source #99");
});

// ---------------------------------------------------------------------------
// RECEIVABLE (Debts) — ADR-0018 lifecycle_status matching
// ---------------------------------------------------------------------------

test("getReceivableOptions returns open OWED debts with remaining amount > 0", () => {
  const debts = [
    { id: 1, debt_type: "OWED", lifecycle_status: "OPEN", remaining_amount: 5000, counterparty_name: "Alice" },
    { id: 2, debt_type: "OWING", lifecycle_status: "OPEN", remaining_amount: 3000, counterparty_name: "Bank" },
    { id: 3, debt_type: "OWED", lifecycle_status: "CLOSED", remaining_amount: 1000, counterparty_name: "Bob" },
    { id: 4, debt_type: "OWED", lifecycle_status: "OPEN", remaining_amount: 0, counterparty_name: "Carol" },
  ];

  const options = getReceivableOptions(debts);

  assert.equal(options.length, 1);
  assert.equal(options[0].id, 1);
  assert.equal(options[0].label, "Alice");
  assert.equal(options[0].remainingAmount, 5000);
});

test("getReceivableOptions does NOT depend on legacy ACTIVE status (ADR-0018)", () => {
  // A debt with lifecycle_status OPEN but a legacy status that is NOT "ACTIVE"
  // should still be included because lifecycle_status is the source of truth.
  const debts = [
    { id: 1, debt_type: "OWED", lifecycle_status: "OPEN", remaining_amount: 5000, counterparty_name: "Alice" },
  ];

  const options = getReceivableOptions(debts);

  assert.equal(options.length, 1);
  assert.equal(options[0].label, "Alice");
});

test("getReceivableOptions excludes CLOSED debts even if they would pass legacy ACTIVE (ADR-0018)", () => {
  const debts = [
    { id: 1, debt_type: "OWED", lifecycle_status: "CLOSED", remaining_amount: 5000, counterparty_name: "Bob" },
  ];

  const options = getReceivableOptions(debts);

  assert.equal(options.length, 0);
});

test("getReceivableOptions handles wrapped payload", () => {
  const debts = { items: [{ id: 1, debt_type: "OWED", lifecycle_status: "OPEN", remaining_amount: 100, counterparty_name: "Alice" }] };

  const options = getReceivableOptions(debts);

  assert.equal(options.length, 1);
});

test("getReceivableOptions generates fallback label", () => {
  const debts = [{ id: 42, debt_type: "OWED", lifecycle_status: "OPEN", remaining_amount: 100 }];

  const options = getReceivableOptions(debts);

  assert.equal(options[0].label, "Debt #42");
});

// ---------------------------------------------------------------------------
// REFUND — ADR-0018 feed unwrapping
// ---------------------------------------------------------------------------

test("getRefundOptions unwraps ExpenseFeedItemOut and excludes refund-type expenses", () => {
  const feedItems = [
    {
      type: "EXPENSE",
      expense: { id: 10, title: "Groceries", date: "2026-07-01", transaction_type: "EXPENSE" },
    },
    {
      type: "EXPENSE",
      expense: { id: 11, title: "Returned shoes", date: "2026-07-02", transaction_type: "REFUND" },
    },
    {
      type: "EXPENSE",
      expense: { id: 12, title: "Netflix", date: "2026-07-03", transaction_type: "EXPENSE" },
    },
  ];

  const options = getRefundOptions(feedItems);

  assert.equal(options.length, 2);
  assert.equal(options[0].id, 10);
  assert.equal(options[0].label, "Groceries (2026-07-01)");
  assert.equal(options[0].title, "Groceries");
  assert.equal(options[0].date, "2026-07-01");
  assert.equal(options[1].id, 12);
  assert.equal(options[1].label, "Netflix (2026-07-03)");
});

test("getRefundOptions excludes merge groups (only EXPENSE type)", () => {
  const feedItems = [
    { type: "MERGE_GROUP", merge_group: { id: 1, title: "Group" }, expense: null },
    { type: "EXPENSE", expense: { id: 10, title: "Coffee", date: "2026-07-01", transaction_type: "EXPENSE" } },
  ];

  const options = getRefundOptions(feedItems);

  assert.equal(options.length, 1);
  assert.equal(options[0].id, 10);
});

test("getRefundOptions excludes items with null expense", () => {
  const feedItems = [
    { type: "EXPENSE", expense: null },
    { type: "EXPENSE", expense: { id: 10, title: "Lunch", date: "2026-07-01", transaction_type: "EXPENSE" } },
  ];

  const options = getRefundOptions(feedItems);

  assert.equal(options.length, 1);
  assert.equal(options[0].id, 10);
});

test("getRefundOptions does NOT access event_type on the wrapper (ADR-0018)", () => {
  // The feed wrapper does not have event_type; the code must unwrap to
  // feedItem.expense.transaction_type.  If the old buggy code path were here
  // it would fail because event_type is undefined on the wrapper.
  const feedItems = [
    {
      type: "EXPENSE",
      // Deliberate: no top-level event_type — only transaction_type on inner expense
      expense: { id: 10, title: "Groceries", date: "2026-07-01", transaction_type: "EXPENSE" },
    },
  ];

  const options = getRefundOptions(feedItems);

  assert.equal(options.length, 1);
  assert.equal(options[0].label, "Groceries (2026-07-01)");
});

test("getRefundOptions generates stable label for expense without title", () => {
  const feedItems = [
    { type: "EXPENSE", expense: { id: 99, date: "2026-06-15", transaction_type: "EXPENSE" } },
  ];

  const options = getRefundOptions(feedItems);

  assert.equal(options[0].label, "Expense #99 (2026-06-15)");
});

test("getRefundOptions generates label for expense without date", () => {
  const feedItems = [
    { type: "EXPENSE", expense: { id: 50, title: "Mystery", transaction_type: "EXPENSE" } },
  ];

  const options = getRefundOptions(feedItems);

  assert.equal(options[0].label, "Mystery (no date)");
});

test("getRefundOptions handles wrapped payload", () => {
  const feedItems = {
    items: [
      { type: "EXPENSE", expense: { id: 10, title: "Groceries", date: "2026-07-01", transaction_type: "EXPENSE" } },
    ],
  };

  const options = getRefundOptions(feedItems);

  assert.equal(options.length, 1);
  assert.equal(options[0].label, "Groceries (2026-07-01)");
});

test("getRefundOptions returns empty for empty input", () => {
  assert.deepEqual(getRefundOptions([]), []);
  assert.deepEqual(getRefundOptions(null), []);
});

// ---------------------------------------------------------------------------
// ASSET SALE
// ---------------------------------------------------------------------------

test("getAssetSaleOptions returns only owned assets", () => {
  const assets = [
    { id: 1, name: "Laptop", status: "owned" },
    { id: 2, name: "Old phone", status: "sold" },
    { id: 3, name: "Camera", status: "owned" },
  ];

  const options = getAssetSaleOptions(assets);

  assert.equal(options.length, 2);
  assert.equal(options[0].id, 1);
  assert.equal(options[0].label, "Laptop");
  assert.equal(options[1].id, 3);
  assert.equal(options[1].label, "Camera");
});

test("getAssetSaleOptions handles wrapped payload", () => {
  const assets = { items: [{ id: 1, name: "Laptop", status: "owned" }] };

  const options = getAssetSaleOptions(assets);

  assert.equal(options.length, 1);
  assert.equal(options[0].label, "Laptop");
});

test("getAssetSaleOptions generates fallback label", () => {
  const assets = [{ id: 7, status: "owned" }];

  const options = getAssetSaleOptions(assets);

  assert.equal(options[0].label, "Asset #7");
});

// ---------------------------------------------------------------------------
// Convenience: getSourceOptions
// ---------------------------------------------------------------------------

test("getSourceOptions returns all four kinds keyed by name", () => {
  const sources = [{ id: 1, name: "Salary", is_active: true }];
  const debts = [{ id: 1, debt_type: "OWED", lifecycle_status: "OPEN", remaining_amount: 100, counterparty_name: "Alice" }];
  const expenses = [{ type: "EXPENSE", expense: { id: 10, title: "Groceries", date: "2026-07-01", transaction_type: "EXPENSE" } }];
  const assets = [{ id: 1, name: "Laptop", status: "owned" }];

  const result = getSourceOptions({ sources, debts, expenses, assets });

  assert.equal(result.EARNED.length, 1);
  assert.equal(result.EARNED[0].label, "Salary");
  assert.equal(result.RECEIVABLE.length, 1);
  assert.equal(result.RECEIVABLE[0].label, "Alice");
  assert.equal(result.REFUND.length, 1);
  assert.equal(result.REFUND[0].label, "Groceries (2026-07-01)");
  assert.equal(result.ASSET_SALE.length, 1);
  assert.equal(result.ASSET_SALE[0].label, "Laptop");
});

// ---------------------------------------------------------------------------
// ADR-0018 combined regression
// ---------------------------------------------------------------------------

test("ADR-0018 regression: receivable does not leak legacy ACTIVE status and refund unwraps feed", () => {
  // If the code regresses to debt.status === "ACTIVE" or expense.event_type,
  // these options would break because those fields are not present.
  const debts = [
    { id: 1, debt_type: "OWED", lifecycle_status: "OPEN", remaining_amount: 5000, counterparty_name: "Alice" },
  ];
  const expenses = [
    { type: "EXPENSE", expense: { id: 10, title: "Groceries", date: "2026-07-01", transaction_type: "EXPENSE" } },
  ];

  const receivable = getReceivableOptions(debts);
  const refund = getRefundOptions(expenses);

  assert.equal(receivable.length, 1);
  assert.equal(receivable[0].label, "Alice");
  assert.equal(refund.length, 1);
  assert.equal(refund[0].id, 10);
  assert.equal(refund[0].label, "Groceries (2026-07-01)");
});

test("ADR-0018 regression: refund never links to refund", () => {
  const feedItems = [
    { type: "EXPENSE", expense: { id: 1, title: "Original", date: "2026-07-01", transaction_type: "EXPENSE" } },
    { type: "EXPENSE", expense: { id: 2, title: "Refund of shoes", date: "2026-07-02", transaction_type: "REFUND" } },
    { type: "EXPENSE", expense: { id: 3, title: "Another refund", date: "2026-07-03", transaction_type: "REFUND" } },
  ];

  const options = getRefundOptions(feedItems);

  assert.equal(options.length, 1);
  assert.equal(options[0].id, 1);
  assert.equal(options[0].label, "Original (2026-07-01)");
});
