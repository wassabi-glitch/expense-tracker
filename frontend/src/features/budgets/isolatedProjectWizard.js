import { parseBudgetAmountInput } from "./overlayProjectWizard.js";

export function getIsolatedCategoryAllocationRows({
  selectedCategories,
  categoryAllocations,
}) {
  return selectedCategories.map((category) => {
    const amount = parseBudgetAmountInput(categoryAllocations[category]);
    return {
      category,
      amount,
      input: categoryAllocations[category] || "",
      isInvalidAmount: amount === null || amount <= 0,
    };
  });
}

export function getIsolatedCategoryAllocationSummary({
  categoryAllocationRows,
  stashTotal,
}) {
  const allocatedAmount = categoryAllocationRows.reduce(
    (sum, row) => sum + Number(row.amount || 0),
    0,
  );
  const unallocatedAmount = Number(stashTotal || 0) - allocatedAmount;
  return {
    allocatedAmount,
    unallocatedAmount,
    isOverAllocated: unallocatedAmount < 0,
  };
}

export function buildIsolatedProjectPayload({
  title,
  description,
  startDate,
  targetEndDate,
  walletAllocations,
  categoryAllocationRows,
}) {
  return {
    title: title.trim(),
    description: description.trim() || null,
    is_isolated: true,
    wallet_allocations: walletAllocations,
    category_allocations: categoryAllocationRows
      .filter((row) => row.amount !== null && row.amount > 0)
      .map((row) => ({ category: row.category, limit_amount: row.amount })),
    start_date: startDate,
    target_end_date: targetEndDate || null,
  };
}
