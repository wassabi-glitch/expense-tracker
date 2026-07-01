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
  if (msg === "payment_plans.update.setup_requires_pristine") {
    return t("payment_plans.errors.setupRequiresPristine", {
      defaultValue: "Recorded activity prevents changing financial history. You can still edit the plan name, provider, and category.",
    });
  }
  if (msg === "payment_plans.delete.pristine_required") {
    return t("payment_plans.errors.deletePristineRequired", {
      defaultValue: "This payment plan already has recorded activity, so it cannot be deleted.",
    });
  }
  if (msg === "payment_plans.archived_locked") {
    return t("payment_plans.errors.archivedLocked", {
      defaultValue: "Archived payment plans cannot be changed here.",
    });
  }
  if (msg === "payment_plans.validation.real_expense_category_required") {
    return t("payment_plans.errors.realCategoryRequired", {
      defaultValue: "Choose the real spending category for this payment plan.",
    });
  }
  if (msg === "payment_plans.write_rate_limited") {
    return t("payment_plans.errors.tooManySoon", {
      defaultValue: "Too many payment plan changes. Please wait a moment and try again.",
    });
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
  if (msg === "expenses.goal_protection_conflict") {
    return t("expenses.goalProtectionConflict", {
      defaultValue: "This wallet has money reserved for goals. Release or rebalance goal funding before spending it.",
    });
  }
  if (msg === "wallets.goal_protection_conflict") {
    return t("wallets.goalProtectionConflict", {
      defaultValue: "This wallet has money reserved for goals. Move or release goal funding before transferring it.",
    });
  }
  if (msg === "wallets.fee_goal_protection_conflict") {
    return t("wallets.feeGoalProtectionConflict", {
      defaultValue: "This fee would use money reserved for goals. Pay the fee from free money or move/release goal funding first.",
    });
  }
  if (msg === "wallets.archive_has_goal_allocations") {
    return t("wallets.archiveHasGoalAllocations", {
      defaultValue: "This wallet still has money reserved for goals. Move or release those allocations before archiving it.",
    });
  }
  if (msg === "wallets.goal_resolution_target_not_eligible") {
    return t("wallets.goalResolutionTargetNotEligible", {
      defaultValue: "The destination wallet cannot hold goal funding.",
    });
  }
  if (msg === "wallets.goal_resolution_currency_mismatch") {
    return t("wallets.goalResolutionCurrencyMismatch", {
      defaultValue: "Goal funding can only move to a wallet in the same currency.",
    });
  }
  if (msg === "wallets.goal_resolution_target_unavailable") {
    return t("wallets.goalResolutionTargetUnavailable", {
      defaultValue: "The destination wallet cannot support the moved goal allocation.",
    });
  }
  if (msg === "expenses.invalid_sort") {
    return t("expenses.requestFailed");
  }
  if (msg === "expenses.not_found") {
    return t("expenses.loadFailed");
  }
  if (msg === "expenses.has_refund_lock") {
    return t("expenses.has_refund_lock");
  }
  if (msg === "expenses.not_posted") {
    return t("expenses.notPosted", { defaultValue: "This expense has already been cancelled." });
  }
  if (msg === "expenses.session_void_not_supported") {
    return t("expenses.sessionVoidNotSupported", { defaultValue: "Session expenses need a dedicated cancellation flow." });
  }
  if (msg === "expenses.asset_link_lock") {
    return t("expenses.assetLinkLock", { defaultValue: "This expense is linked to an asset. Handle the asset first." });
  }
  if (msg === "expenses.linked_dependency_lock") {
    return t("expenses.linkedDependencyLock", { defaultValue: "This expense is linked to debt or payment_plan records and cannot be cancelled here." });
  }
  if (msg === "expenses.complex_event_not_supported") {
    return t("expenses.complexEventNotSupported", { defaultValue: "This action is not supported for grouped or session-style expenses yet." });
  }
  if (msg === "expenses.split_parent_locked") {
    return t("expenses.splitParentLocked", { defaultValue: "Already split. Breakdown editing is not available yet." });
  }
  if (msg === "expenses.asset_split_lock") {
    return t("expenses.assetSplitLock", { defaultValue: "Asset-linked expenses cannot be split with this flow." });
  }
  if (msg === "expenses.split_total_mismatch") {
    return t("expenses.split_total_mismatch", { defaultValue: "Split total must exactly match the expense amount." });
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
  if (msg === "budgets.subcategory_total_exceeds_parent") {
    return t("budgets.subcategoryTotalExceedsParent", {
      defaultValue: "Subcategory limits cannot exceed the parent category limit.",
    });
  }
  if (msg === "budgets.subcategory_reallocate_insufficient_buffer") {
    return t("budgets.subcategoryReallocateInsufficientBuffer", {
      defaultValue: "This parent budget does not have enough unassigned subcategory buffer.",
    });
  }
  if (msg === "budgets.subcategory_reallocate_insufficient_remaining") {
    return t("budgets.subcategoryReallocateInsufficientRemaining", {
      defaultValue: "The source subcategory does not have enough unspent room.",
    });
  }
  if (msg === "budgets.subcategory_category_mismatch") {
    return t("budgets.subcategoryCategoryMismatch", {
      defaultValue: "Subcategory changes must stay inside the same parent category.",
    });
  }
  if (msg === "budgets.plan_exceeds_backing") {
    return t("budgets.planExceedsBackingGeneric", {
      defaultValue: "Requested budgets exceed valid backing. Add expected income or lower the limit.",
    });
  }
  if (msg === "expected_income.month_mismatch") {
    return t("budgets.expectedIncomeMonthMismatch", {
      defaultValue: "Expected income date must be inside the selected budget month.",
    });
  }
  if (msg === "expected_income.not_found") {
    return t("budgets.expectedIncomeNotFound", {
      defaultValue: "Expected income item was not found.",
    });
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
  if (msg === "goals.insufficient_wallet_available_for_goal") {
    return t("savings.goals.insufficientWalletAvailable", { defaultValue: "This wallet does not have enough available money for that goal allocation." });
  }
  if (msg === "goals.wallet_not_eligible") {
    return t("savings.goals.walletNotEligible", { defaultValue: "This wallet is not eligible to fund goals." });
  }
  if (msg === "goals.currency_mismatch") {
    return t("savings.goals.currencyMismatch", { defaultValue: "Goal and wallet currencies must match." });
  }
  if (msg === "goals.insufficient_wallet_goal_balance") {
    return t("savings.goals.insufficientWalletGoalBalance", { defaultValue: "This wallet does not have enough funding in this goal." });
  }
  if (msg === "goals.release_exceeds_wallet_unreleased") {
    return t("savings.goals.releaseExceedsWalletUnreleased", { defaultValue: "Release amount exceeds this wallet's unreleased goal funding." });
  }
  if (msg === "goals.release_wallet_required") {
    return t("savings.goals.releaseWalletRequired", { defaultValue: "Choose the source wallet for this release." });
  }
  if (msg === "goals.currency_change_requires_zero_funding") {
    return t("savings.goals.currencyChangeRequiresZeroFunding", { defaultValue: "Return all goal funding before changing currency." });
  }
  if (msg === "goals.template_invalid") {
    return t("savings.goals.templateInvalid", { defaultValue: "Goal template can only contain letters, numbers, underscores, colons, or dashes." });
  }
  if (msg === "goals.intent_mismatch") {
    return t("savings.goals.intentMismatch", { defaultValue: "This action does not match the goal intent." });
  }
  if (msg === "goals.payment_wallet_not_funding_source") {
    return t("savings.goals.paymentWalletNotFundingSource", { defaultValue: "Goal-funded use requires paying from a wallet that reserved money for this goal." });
  }
  if (msg === "goals.payment_allocation_limit_exceeded") {
    return t("savings.goals.paymentAllocationLimitExceeded", { defaultValue: "Planned purchases can use up to 3 payment wallets." });
  }
  if (msg === "goals.goal_funded_payment_wallet_must_be_owned_money") {
    return t("savings.goals.goalFundedPaymentWalletMustBeOwnedMoney", { defaultValue: "Goal-funded purchases can only use prepared wallets backed by owned money. Use the unplanned-wallet path for credit cards." });
  }
  if (msg === "goals.goal_funded_payment_wallet_insufficient_owned_balance") {
    return t("savings.goals.goalFundedPaymentWalletInsufficientOwnedBalance", { defaultValue: "This prepared wallet no longer has enough owned money for the goal purchase." });
  }
  if (msg === "goals.planned_purchase_must_use_goal_funds") {
    return t("savings.goals.plannedPurchaseMustUseGoalFunds", { defaultValue: "Record Purchase must use this goal's reserved money. Create a normal expense if you do not want to use goal funds." });
  }
  if (msg === "goals.planned_purchase_goal_funded_requires_direct_payment") {
    return t("savings.goals.plannedPurchaseGoalFundedRequiresDirectPayment", { defaultValue: "Goal-funded purchase means the reserved wallet money paid directly. Choose the outside-funds option if different money paid." });
  }
  if (msg === "goals.achieved_outside_requires_non_funding_wallet") {
    return t("savings.goals.achievedOutsideRequiresNonFundingWallet", { defaultValue: "Different-wallet purchase cannot use a wallet that reserved this goal. Choose goal-funded mode if a reserved wallet paid." });
  }
  if (msg === "goals.completion_mode_invalid") {
    return t("savings.goals.completionModeInvalid", { defaultValue: "Choose how this planned purchase was completed." });
  }
  if (msg === "goals.purchase_target_adjustment_required") {
    return t("savings.goals.purchaseTargetAdjustmentRequired", { defaultValue: "Confirm the target update before completing this planned purchase." });
  }
  if (msg === "goals.completed_read_only") {
    return t("savings.goals.completedReadOnly", { defaultValue: "This goal has already been completed through a real payment." });
  }
  if (msg === "goals.purchase_already_recorded") {
    return t("savings.goals.purchaseAlreadyRecorded", { defaultValue: "This planned purchase has already been recorded." });
  }
  if (msg === "goals.allocation_exceeds_target") {
    return t("savings.goals.allocationExceedsTarget", { defaultValue: "This goal does not need that much more money." });
  }
  if (msg === "goals.allocation_duplicate_wallet") {
    return t("savings.goals.allocationDuplicateWallet", { defaultValue: "Each wallet can appear only once in the reserve action." });
  }
  if (msg === "goals.insufficient_goal_balance") {
    return t("savings.goals.insufficientGoalBalance");
  }
  if (msg === "goals.insufficient_unreleased_balance") {
    return t("savings.goals.insufficientUnreleasedBalance");
  }
  if (msg === "goals.project_already_exists") {
    return t("savings.goals.projectAlreadyExists");
  }
  if (msg === "goals.release_exceeds_unreleased") {
    return t("savings.goals.releaseExceedsUnreleased");
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
  if (msg === "projects.release_exceeds_total_limit") {
    return t("savings.goals.projectReleaseExceedsTotalLimit");
  }
  if (msg === "projects.not_active") {
    return t("savings.goals.projectNotActive");
  }
  if (msg === "projects.category_budget_month_required") {
    return t("projects.overlayCategoryNeedsBudget", {
      defaultValue: "Add this category to the selected monthly budget before reserving it.",
    });
  }
  if (msg === "projects.category_reservation_exceeds_parent_budget") {
    return t("projects.overlayReservationOverbooked", {
      defaultValue: "Reservation exceeds available selected-month headroom.",
    });
  }
  if (msg === "projects.subcategory_reservation_exceeds_monthly_lane") {
    return t("projects.overlaySubcategoryReservationOverbooked", {
      defaultValue: "Subcategory reservation exceeds the monthly lane's available headroom.",
    });
  }
  if (msg === "projects.release_before_start") {
    return t("savings.goals.releaseBeforeProjectStart");
  }
  if (msg === "projects.release_after_completion") {
    return t("savings.goals.releaseAfterProjectCompletion");
  }
  if (msg === "savings.virtual_savings_removed") {
    return t("savings.virtualSavingsRemoved", { defaultValue: "Virtual savings transfers were removed. Allocate directly from wallets to goals." });
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
