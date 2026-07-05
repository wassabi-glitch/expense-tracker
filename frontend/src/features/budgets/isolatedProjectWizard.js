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

export function getIsolatedTopUpPreview({
  fundingLimit,
  allocatedFunding,
  walletAllocations,
}) {
  const topUpAmount = (walletAllocations || []).reduce(
    (sum, row) => sum + Number(row.amount || 0),
    0,
  );
  const nextFundingLimit = Number(fundingLimit || 0) + topUpAmount;
  const nextUnallocatedFunding = nextFundingLimit - Number(allocatedFunding || 0);
  return {
    topUpAmount,
    nextFundingLimit,
    nextUnallocatedFunding,
  };
}

export function buildIsolatedTopUpPayload({ walletAllocations }) {
  return {
    wallet_allocations: (walletAllocations || [])
      .filter((row) => Number(row.amount || 0) > 0)
      .map((row) => ({
        wallet_id: Number(row.wallet_id),
        amount: Number(row.amount),
      })),
  };
}

export function buildIsolatedCategoryAllocationPayload({ category, allocatedAmount }) {
  return {
    category,
    allocated_amount: Number(allocatedAmount),
  };
}

export function buildIsolatedSubcategoryAllocationPayload({
  category,
  allocatedAmount,
  name,
  userSubcategoryId,
}) {
  const payload = {
    category,
    allocated_amount: Number(allocatedAmount),
  };
  if (userSubcategoryId) {
    payload.user_subcategory_id = Number(userSubcategoryId);
  } else {
    payload.name = name.trim();
  }
  return payload;
}

export function buildIsolatedCategoryRebalancePayload({
  fromCategory,
  toCategory,
  amount,
}) {
  return {
    scope: "CATEGORY",
    from_category: fromCategory,
    to_category: toCategory,
    amount: Number(amount),
  };
}

export function buildIsolatedSubcategoryRebalancePayload({
  fromSubcategoryAllocationId,
  toSubcategoryAllocationId,
  amount,
}) {
  return {
    scope: "SUBCATEGORY",
    from_subcategory_allocation_id: Number(fromSubcategoryAllocationId),
    to_subcategory_allocation_id: Number(toSubcategoryAllocationId),
    amount: Number(amount),
  };
}

