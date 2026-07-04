import assert from "node:assert/strict";
import test from "node:test";

import {
  buildIsolatedProjectPayload,
  getIsolatedCategoryAllocationRows,
  getIsolatedCategoryAllocationSummary,
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
    start_date: "2026-07-01",
    target_end_date: null,
  });
});
