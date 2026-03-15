export function localizeApiError(message, t) {
  const raw = String(message || "");
  const msg = raw.toLowerCase();
  if (!msg) return "";

  if (msg === "auth.credentials_invalid" || msg.includes("could not validate credentials")) {
    return t("common.sessionExpired");
  }
  if (msg === "common.forbidden") {
    return t("common.forbidden");
  }
  if (msg.includes("failed to fetch") || msg.includes("networkerror")) {
    return t("common.networkError");
  }
  if (msg === "expenses.write_rate_limited") {
    return t("expenses.tooManySoon");
  }
  if (msg === "expenses.month_limit_reached") {
    return t("expenses.monthLimitReached");
  }
  if (msg === "recurring_expenses.write_rate_limited") {
    return t("recurring.tooManySoon");
  }
  if (msg === "recurring_expenses.max_limit_reached") {
    return t("recurring.maxLimitReached");
  }
  if (msg === "recurring_expenses.start_date_before_current_month") {
    return t("recurring.startDateBeforeCurrentMonth");
  }
  if (msg === "budgets.write_rate_limited") {
    return t("budgets.tooManySoon");
  }
  if (msg === "expenses.date_in_future") {
    return t("expenses.dateFuture");
  }
  if (msg === "expenses.date_too_early") {
    return t("expenses.dateTooEarly");
  }
  if (msg === "expenses.amount_too_large") {
    return t("expenses.amountTooLarge");
  }
  if (msg === "expenses.invalid_sort") {
    return t("expenses.requestFailed");
  }
  if (msg === "expenses.not_found") {
    return t("expenses.loadFailed");
  }
  if (msg === "budgets.already_exists") {
    return t("budgets.addFailed");
  }
  if (msg === "budgets.not_found") {
    return t("budgets.loadFailed");
  }
  if (msg === "budgets.has_linked_expenses") {
    return t("budgets.deleteBlockedLinkedExpenses");
  }
  if (msg === "analytics.range_both_or_days_required" || msg === "analytics.range_both_required") {
    return t("analytics.hintProvideBoth");
  }
  if (msg === "analytics.date_too_early") {
    return t("analytics.hintTooEarly");
  }
  if (msg === "analytics.end_date_in_future") {
    return t("analytics.hintEndFuture");
  }
  if (msg === "analytics.start_after_end") {
    return t("analytics.hintStartAfterEnd");
  }
  if (msg === "analytics.range_too_large") {
    return t("analytics.hintMaxRange");
  }
  if (msg === "analytics.days_min_1") {
    return t("analytics.hintInvalidDate");
  }
  if (msg === "income.source_exists") {
    return t("income.sourceExists");
  }
  if (msg === "income.source_limit_reached") {
    return t("income.sourceLimitReached");
  }
  if (msg === "income.sources_write_rate_limited") {
    return t("income.sourcesTooManySoon");
  }
  if (msg === "income.source_not_found") {
    return t("income.sourceNotFound");
  }
  if (msg === "income.source_inactive") {
    return t("income.sourceInactive");
  }
  if (msg === "income.entry_not_found") {
    return t("income.entryNotFound");
  }
  if (msg === "income.entry_month_limit_reached") {
    return t("income.entryMonthLimitReached");
  }
  if (msg === "income.entries_write_rate_limited") {
    return t("income.entriesTooManySoon");
  }
  if (msg === "income.date_range_both_required") {
    return t("income.dateRangeBothRequired");
  }
  if (msg === "income.start_after_end") {
    return t("income.startAfterEnd");
  }
  if (msg === "income.source_name_length") {
    return t("income.sourceNameTooLong");
  }
  if (msg === "income.note_too_long") {
    return t("income.noteTooLong");
  }
  if (msg === "income.date_too_early") {
    return t("income.dateTooEarly");
  }
  if (msg === "income.date_outside_current_month") {
    return t("income.dateCurrentMonthOnly");
  }
  if (msg === "income.amount_too_large") {
    return t("income.amountTooLarge");
  }
  if (msg === "savings.insufficient_spendable_balance") {
    return t("savings.insufficientSpendable");
  }
  if (msg === "savings.insufficient_free_savings_balance") {
    return t("savings.insufficientFree");
  }
  if (msg === "savings.write_rate_limited") {
    return t("savings.tooManySoon");
  }
  if (msg === "goals.not_found") {
    return t("savings.goals.notFound");
  }
  if (msg === "goals.write_rate_limited") {
    return t("savings.goals.tooManySoon");
  }
  if (msg === "goals.insufficient_free_savings_balance") {
    return t("savings.goals.insufficientFreeSavings");
  }
  if (msg === "goals.insufficient_goal_balance") {
    return t("savings.goals.insufficientGoalBalance");
  }
  if (msg === "goals.target_below_funded_amount") {
    return t("savings.goals.targetBelowFunded");
  }
  if (msg === "goals.archive_requires_zero_funded") {
    return t("savings.goals.archiveRequiresZeroFunded");
  }
  if (msg === "goals.delete_requires_archived") {
    return t("savings.goals.deleteRequiresArchived");
  }
  if (msg === "goals.delete_requires_zero_funded") {
    return t("savings.goals.deleteRequiresZeroFunded");
  }
  if (msg === "goals.restore_requires_archived") {
    return t("savings.goals.restoreRequiresArchived");
  }
  if (msg === "goals.archived_read_only") {
    return t("savings.goals.archivedReadOnly");
  }
  if (msg === "goals.active_limit_reached") {
    return t("savings.goals.activeLimitReached");
  }
  if (msg === "goals.archived_limit_reached") {
    return t("savings.goals.archivedLimitReached");
  }
  if (msg === "users.premium_required") {
    return t("common.premiumRequired");
  }
  if (msg === "users.profile_required") {
    return t("settings.failedProfile");
  }

  if (
    msg === "expenses.budget_required" ||
    msg.includes("cannot create an expense for") ||
    msg.includes("cannot add expense for")
  ) {
    const match = raw.match(/for\s+([A-Za-z]+)/i);
    const categoryRaw = match?.[1] || "";
    const categoryLabel = categoryRaw
      ? t(`categories.${categoryRaw}`, { defaultValue: categoryRaw })
      : t("expenses.category");
    return t("expenses.budgetRequired", { category: categoryLabel });
  }

  if (msg.includes(".")) {
    return t(raw, { defaultValue: "" });
  }

  if (msg.includes("exceeded maximum size") || msg.includes("out of range")) {
    return t("expenses.amountTooLarge");
  }

  return "";
}
