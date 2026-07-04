import assert from "node:assert/strict";
import test from "node:test";

import {
  buildOverlayProjectPayload,
  getOverlayCategoryReservationRows,
  parseBudgetAmountInput,
} from "./overlayProjectWizard.js";

test("overlay reservation rows validate against current-month headroom only", () => {
  const rows = getOverlayCategoryReservationRows({
    selectedCategories: ["Travel", "Food"],
    categoryAllocations: {
      Travel: "500 000",
      Food: "300 000",
    },
    getCategoryHeadroom: (category) => ({
      budget: category === "Travel" ? { id: 10 } : null,
      reserved: category === "Travel" ? 100_000 : 0,
      headroom: category === "Travel" ? 400_000 : 0,
    }),
  });

  assert.equal(parseBudgetAmountInput("500 000"), 500_000);
  assert.equal(rows[0].isOverbooked, true);
  assert.equal(rows[0].isMissingBudget, false);
  assert.equal(rows[1].isMissingBudget, true);
});

test("overlay create payload uses one selected budget month for every reservation", () => {
  const payload = buildOverlayProjectPayload({
    title: " Summer trip ",
    description: " Cross-month overlay ",
    targetEstimate: 5_000_000,
    startDate: "2026-07-01",
    targetEndDate: "2026-08-28",
    budgetYear: 2026,
    budgetMonth: 7,
    categoryReservationRows: [
      { category: "Travel", amount: 500_000 },
      { category: "Food", amount: null },
    ],
    subcategoryReservations: [
      { category: "Travel", user_subcategory_id: 42, limit_amount: 200_000 },
    ],
  });

  assert.deepEqual(payload, {
    title: "Summer trip",
    description: "Cross-month overlay",
    target_estimate: 5_000_000,
    start_date: "2026-07-01",
    target_end_date: "2026-08-28",
    budget_year: 2026,
    budget_month: 7,
    category_reservations: [{ category: "Travel", limit_amount: 500_000 }],
    subcategory_reservations: [
      { category: "Travel", user_subcategory_id: 42, limit_amount: 200_000 },
    ],
  });
});
