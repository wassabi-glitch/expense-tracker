import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIsolatedCategoryAllocationPayload,
  buildIsolatedCategoryRebalancePayload,
  buildIsolatedProjectPayload,
  buildIsolatedSubcategoryAllocationPayload,
  buildIsolatedSubcategoryRebalancePayload,
  buildIsolatedTopUpPayload,
  getIsolatedCategoryAllocationRows,
  getIsolatedCategoryAllocationSummary,
  getIsolatedTopUpPreview,
} from "./isolatedProjectWizard.js";

test("isolated category allocations compare against derived stash instead of monthly headroom", () => {
  const rows = getIsolatedCategoryAllocationRows({
    selectedCategories: ["Travel", "Family & Events"],
    categoryAllocations: {
      Travel: "600 000",
      "Family & Events": "500 000",
    },
  });
  const summary = getIsolatedCategoryAllocationSummary({
    categoryAllocationRows: rows,
    stashTotal: 1_000_000,
  });

  assert.deepEqual(rows.map((row) => ({
    category: row.category,
    amount: row.amount,
    isInvalidAmount: row.isInvalidAmount,
  })), [
    { category: "Travel", amount: 600_000, isInvalidAmount: false },
    { category: "Family & Events", amount: 500_000, isInvalidAmount: false },
  ]);
  assert.equal(summary.allocatedAmount, 1_100_000);
  assert.equal(summary.unallocatedAmount, -100_000);
  assert.equal(summary.isOverAllocated, true);
});

test("isolated create payload sends wallet funding and parent category allocations together", () => {
  const payload = buildIsolatedProjectPayload({
    title: " Wedding ",
    description: " Family event ",
    startDate: "2026-07-01",
    targetEndDate: "",
    walletAllocations: [{ wallet_id: 1, amount: 1_000_000 }],
    categoryAllocationRows: [
      { category: "Family & Events", amount: 650_000 },
      { category: "Travel", amount: null },
    ],
  });

  assert.deepEqual(payload, {
    title: "Wedding",
    description: "Family event",
    is_isolated: true,
    wallet_allocations: [{ wallet_id: 1, amount: 1_000_000 }],
    category_allocations: [
      { category: "Family & Events", limit_amount: 650_000 },
    ],
    subcategory_allocations: [],
    start_date: "2026-07-01",
    target_end_date: null,
  });
});

test("isolated top-up preview lands new funding in unassigned stash", () => {
  const preview = getIsolatedTopUpPreview({
    fundingLimit: 1_000_000,
    allocatedFunding: 700_000,
    walletAllocations: [
      { wallet_id: 1, amount: 200_000 },
      { wallet_id: 2, amount: 300_000 },
    ],
  });
  const payload = buildIsolatedTopUpPayload({
    walletAllocations: [
      { wallet_id: 1, amount: 200_000 },
      { wallet_id: 2, amount: 300_000 },
      { wallet_id: 3, amount: 0 },
    ],
  });

  assert.deepEqual(preview, {
    topUpAmount: 500_000,
    nextFundingLimit: 1_500_000,
    nextUnallocatedFunding: 800_000,
  });
  assert.deepEqual(payload, {
    wallet_allocations: [
      { wallet_id: 1, amount: 200_000 },
      { wallet_id: 2, amount: 300_000 },
    ],
  });
});

test("isolated allocation and rebalance helpers use canonical allocation language", () => {
  assert.deepEqual(buildIsolatedCategoryAllocationPayload({
    category: "Housing",
    allocatedAmount: 250_000,
  }), {
    category: "Housing",
    allocated_amount: 250_000,
  });
  assert.deepEqual(buildIsolatedSubcategoryAllocationPayload({
    category: "Housing",
    name: " Plumbing ",
    allocatedAmount: 120_000,
  }), {
    category: "Housing",
    name: "Plumbing",
    allocated_amount: 120_000,
  });
  assert.deepEqual(buildIsolatedCategoryRebalancePayload({
    fromCategory: "Housing",
    toCategory: "Travel",
    amount: 75_000,
  }), {
    scope: "CATEGORY",
    from_category: "Housing",
    to_category: "Travel",
    amount: 75_000,
  });
  assert.deepEqual(buildIsolatedSubcategoryRebalancePayload({
    fromSubcategoryAllocationId: 3,
    toSubcategoryAllocationId: 4,
    amount: 25_000,
  }), {
    scope: "SUBCATEGORY",
    from_subcategory_allocation_id: 3,
    to_subcategory_allocation_id: 4,
    amount: 25_000,
  });
});
