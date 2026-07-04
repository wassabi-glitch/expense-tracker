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

export function getIsolatedSubcategoryAllocationSummary({
  category,
  categoryAllocationRows,
  subcategoryAllocations,
}) {
  const categoryRow = categoryAllocationRows.find((row) => row.category === category);
  const categoryLimit = categoryRow && categoryRow.amount !== null ? Number(categoryRow.amount) : 0;

  const allocatedAmount = (subcategoryAllocations || [])
    .filter((sub) => sub.category === category)
    .reduce((sum, sub) => sum + Number(sub.limit_amount || 0), 0);

  const unallocatedAmount = categoryLimit - allocatedAmount;
  return {
    allocatedAmount,
    unallocatedAmount,
    isOverAllocated: unallocatedAmount < 0,
    headroom: Math.max(0, unallocatedAmount),
  };
}

export function buildIsolatedProjectPayload({
  title,
  description,
  startDate,
  targetEndDate,
  walletAllocations,
  categoryAllocationRows,
  subcategoryAllocations = [],
}) {
  return {
    title: title.trim(),
    description: description.trim() || null,
    is_isolated: true,
    wallet_allocations: walletAllocations,
    category_allocations: categoryAllocationRows
      .filter((row) => row.amount !== null && row.amount > 0)
      .map((row) => ({ category: row.category, limit_amount: row.amount })),
    subcategory_allocations: subcategoryAllocations.map((sub) => ({
      category: sub.category,
      name: sub.name,
      limit_amount: Number(sub.limit_amount),
      is_active: true,
    })),
    start_date: startDate,
    target_end_date: targetEndDate || null,
  };
}

