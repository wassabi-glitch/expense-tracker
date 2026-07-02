export function parseBudgetAmountInput(raw) {
  if (!raw) return null;
  const amount = Number(String(raw).replace(/\s+/g, ""));
  return Number.isFinite(amount) ? amount : null;
}

export function getOverlayCategoryAllocationRows({
  selectedCategories,
  categoryAllocations,
  getCategoryHeadroom,
}) {
  return selectedCategories.map((category) => {
    const amount = parseBudgetAmountInput(categoryAllocations[category]);
    const headroom = getCategoryHeadroom(category);
    return {
      category,
      amount,
      input: categoryAllocations[category] || "",
      ...headroom,
      isMissingBudget: !headroom.budget,
      isInvalidAmount: amount === null || amount <= 0,
      isOverbooked: amount !== null && amount > Number(headroom.headroom || 0),
    };
  });
}

export function buildOverlayProjectPayload({
  title,
  description,
  targetEstimate,
  startDate,
  targetEndDate,
  budgetYear,
  budgetMonth,
  categoryAllocationRows,
  subcategoryReservations,
}) {
  return {
    title: title.trim(),
    description: description.trim() || null,
    target_estimate: targetEstimate,
    start_date: startDate,
    target_end_date: targetEndDate || null,
    budget_year: budgetYear,
    budget_month: budgetMonth,
    category_reservations: categoryAllocationRows
      .filter((row) => row.amount !== null && row.amount > 0)
      .map((row) => ({ category: row.category, limit_amount: row.amount })),
    subcategory_reservations: subcategoryReservations.map((item) => ({
      category: item.category,
      user_subcategory_id: item.user_subcategory_id,
      limit_amount: item.limit_amount,
    })),
  };
}
