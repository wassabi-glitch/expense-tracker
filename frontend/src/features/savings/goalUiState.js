export const GOAL_INTENT_LABELS = {
  RESERVE: "Reserve fund",
  PLANNED_PURCHASE: "Planned purchase",
  PAY_OBLIGATION: "Debt savings",
  FUND_PROJECT: "Project fund",
};

export const GOAL_INTENT_DESCRIPTIONS = {
  RESERVE: "Keep money protected for later.",
  PLANNED_PURCHASE: "Save for one specific purchase.",
  PAY_OBLIGATION: "Save toward a debt you owe.",
  FUND_PROJECT: "Save for a multi-expense project before it becomes an isolated project stash.",
};

export const GOAL_CREATE_CHOICE_COPY = [
  {
    intent: "RESERVE",
    title: "Set money aside",
    description: "Protect money for emergencies, cushions, or other flexible needs.",
  },
  {
    intent: "PLANNED_PURCHASE",
    title: "Buy something",
    description: "Save for one specific thing you plan to buy.",
  },
  {
    intent: "PAY_OBLIGATION",
    title: "Save toward a debt",
    description: "Prepare money for a debt you owe someone.",
  },
];

export function buildGoalCreatePayload(parsedGoal, { linkedDebtId } = {}) {
  const payload = {
    ...parsedGoal,
    currency: "UZS",
  };
  if (parsedGoal.intent === "PAY_OBLIGATION" && linkedDebtId) {
    payload.linked_debt_id = Number(linkedDebtId);
  }
  return payload;
}

export function buildFundProjectGraduationPayload(goal, todayISO) {
  return {
    project_title: goal.title,
    start_date: todayISO,
    target_end_date: goal.target_date || null,
    is_isolated: true,
  };
}

export function buildFundProjectNavigationState(project, originGoal) {
  return {
    projectId: project.id,
    originGoalId: originGoal.id,
  };
}

export function getGoalIntentAction(goal) {
  if (goal?.intent === "RESERVE") return { kind: "use-reserve", label: "Use reserve" };
  if (goal?.intent === "PLANNED_PURCHASE") return { kind: "record-purchase", label: "Record purchase" };
  if (goal?.intent === "PAY_OBLIGATION") return { kind: "make-payment", label: "Make payment" };
  if (goal?.intent === "FUND_PROJECT") return null;
  return null;
}

export function getGoalCardUiState(goal, { eligibleWalletCount = 0, canPreparePayment = false } = {}) {
  const status = goal?.status || "ACTIVE";
  const intent = goal?.intent || "RESERVE";
  const isActive = status === "ACTIVE";
  const unreleasedAmount = Number(goal?.unreleased_amount || 0);
  const fundingSourceCount = (goal?.funding_sources || []).length;
  const action = getGoalIntentAction(goal);
  const isFrozenFundProject = intent === "FUND_PROJECT";
  const isPlannedPurchaseRecorded = intent === "PLANNED_PURCHASE" && status === "COMPLETED" && Boolean(goal?.linked_expense_event_id);

  const primaryActionDisabled =
    !action ||
    isFrozenFundProject ||
    (intent === "PLANNED_PURCHASE" && (!isActive || isPlannedPurchaseRecorded || unreleasedAmount <= 0)) ||
    (intent === "RESERVE" && (!isActive || unreleasedAmount <= 0)) ||
    (intent === "PAY_OBLIGATION" && (!isActive || unreleasedAmount <= 0));

  return {
    intentLabel: GOAL_INTENT_LABELS[intent] || String(intent).replaceAll("_", " ").toLowerCase(),
    intentDescription: isFrozenFundProject
      ? "Fund Project is frozen. Existing records are read-only."
      : GOAL_INTENT_DESCRIPTIONS[intent] || "",
    statusLabel: status,
    canReserve: isActive && !isFrozenFundProject && eligibleWalletCount > 0,
    canUnreserve: isActive && !isFrozenFundProject && fundingSourceCount > 0,
    canPreparePayment:
      ["PLANNED_PURCHASE", "PAY_OBLIGATION", "RESERVE"].includes(intent) &&
      isActive &&
      unreleasedAmount > 0 &&
      fundingSourceCount > 0 &&
      canPreparePayment,
    canArchive: !isFrozenFundProject,
    isReadOnly: isFrozenFundProject || status === "ARCHIVED",
    primaryAction: action
      ? {
          ...action,
          disabled: primaryActionDisabled,
        }
      : null,
  };
}
