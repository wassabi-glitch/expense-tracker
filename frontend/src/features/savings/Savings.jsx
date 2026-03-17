import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ArrowDownLeft,
  Archive,
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  CarFront,
  ChevronUp,
  Crown,
  GraduationCap,
  Heart,
  House,
  Laptop,
  CalendarClock,
  Plane,
  Pencil,
  Smartphone,
  SquarePen,
  Shield,
  Sparkles,
  Target,
  Trash2,
  Wallet,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { getCurrentUser } from "@/lib/api";
import { localizeApiError } from "@/lib/errorMessages";
import { formatAmountDisplay, formatAmountInput, formatDisplayDate, formatUzs } from "@/lib/format";
import {
  goalActionAmountSchema,
  goalCreateFormSchema,
  goalUpdateFormSchema,
  MAX_SAVINGS_AMOUNT,
  savingsTransferFormSchema,
} from "./savingsSchemas";
import { useSavingsSummaryQuery } from "./hooks/useSavingsQueries";
import { useDepositToSavingsMutation, useWithdrawFromSavingsMutation } from "./hooks/useSavingsMutations";
import { useGoalsQuery } from "./hooks/useGoalsQueries";
import {
  useArchiveGoalMutation,
  useContributeToGoalMutation,
  useCreateGoalMutation,
  useDeleteGoalMutation,
  useRestoreGoalMutation,
  useReturnFromGoalMutation,
  useUpdateGoalMutation,
} from "./hooks/useGoalsMutations";

const QUICK_AMOUNTS = [100_000, 500_000, 1_000_000];
const GOAL_ACTION_CHIPS = [100_000, 250_000, 500_000];
const MAX_SAVINGS_AMOUNT_DIGITS = String(MAX_SAVINGS_AMOUNT).length;
const MAX_SAVINGS_AMOUNT_INPUT_LENGTH = formatUzs(MAX_SAVINGS_AMOUNT).length;
const MAX_ACTIVE_GOALS = 20;
const MAX_ARCHIVED_GOALS = 100;

const GOAL_TEMPLATES = [
  { key: "home", icon: House },
  { key: "car", icon: CarFront },
  { key: "wedding", icon: Heart },
  { key: "travel", icon: Plane },
  { key: "phone", icon: Smartphone },
  { key: "laptop", icon: Laptop },
  { key: "education", icon: GraduationCap },
  { key: "business", icon: BriefcaseBusiness },
  { key: "safety", icon: Shield },
  { key: "custom", icon: SquarePen },
];

function parseAmountInput(value) {
  const digits = String(value || "").replace(/\s/g, "");
  return Number(digits || 0);
}

function SummaryCard({ title, value, hint, accent = "default", icon }) {
  const IconComponent = icon;
  const isNegative = Number(value || 0) < 0;
  const absoluteValue = Math.abs(Number(value || 0));
  const prefix = isNegative ? "-" : "";

  const accentClasses = isNegative
    ? "border-border bg-card transition-all duration-300 hover:border-destructive/40 active:border-destructive/40 hover:shadow-[0_0_15px_rgba(239,68,68,0.1)] active:shadow-[0_0_15px_rgba(239,68,68,0.1)] active:scale-[0.98]"
    : accent === "primary"
      ? "border-border bg-card transition-all duration-300 hover:border-primary/40 active:border-primary/40 hover:shadow-[0_0_15px_rgba(34,197,94,0.1)] active:shadow-[0_0_15px_rgba(34,197,94,0.1)] active:scale-[0.98]"
      : "border-border bg-card transition-all duration-300 hover:border-border/80 active:border-border/80 hover:shadow-sm active:shadow-sm active:scale-[0.98]";

  const textClasses = isNegative
    ? "text-destructive dark:text-red-400"
    : accent === "primary"
      ? "text-primary"
      : "text-foreground";

  return (
    <Card className={`shadow-sm overflow-hidden ${accentClasses}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 p-5 w-full">
        <CardTitle className="text-sm font-medium text-muted-foreground w-full">
          {title}
        </CardTitle>
        <IconComponent className="h-4 w-4 text-muted-foreground shrink-0" />
      </CardHeader>
      <CardContent className="px-5 pb-5 pt-0">
        <CurrencyAmount
          value={absoluteValue}
          prefix={prefix}
          format="display"
          tooltip="always"
          className="flex w-full items-baseline gap-1.5 flex-wrap text-left outline-none"
          valueClassName={`text-2xl lg:text-3xl font-semibold tracking-tight tabular-nums break-words ${textClasses}`}
          currencyClassName="text-sm mt-auto mb-1"
          tooltipContent={`${prefix}${formatUzs(absoluteValue)} UZS`}
        />
        <div className="space-y-2 flex-1 min-w-0">
          <p className="text-sm text-muted-foreground break-words overflow-hidden text-ellipsis">{hint}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function GoalStatusBadge({ status, t }) {
  const normalized = String(status || "ACTIVE").toUpperCase();
  const classes =
    normalized === "COMPLETED"
      ? "border-primary/30 bg-primary/10 text-primary"
      : normalized === "ARCHIVED"
        ? "border-border bg-muted/40 text-muted-foreground"
        : "border-sky-500/30 bg-sky-500/10 text-sky-400";
  const labelKey =
    normalized === "COMPLETED"
      ? "savings.goalStatus.completed"
      : normalized === "ARCHIVED"
        ? "savings.goalStatus.archived"
        : "savings.goalStatus.active";

  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${classes}`}>{t(labelKey)}</span>;
}

function GoalTimeBadge({ timeState, t }) {
  if (!timeState) return null;
  const classes =
    timeState === "overdue"
      ? "border border-destructive/30 bg-destructive/10 text-destructive dark:text-red-400"
      : timeState === "due_soon"
        ? "border border-amber-500/35 bg-amber-500/10 text-amber-400"
        : "border border-primary/25 bg-primary/10 text-primary";
  return <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold leading-4 ${classes}`}>{t(`savings.goalTime.${timeState}`)}</span>;
}

export default function Savings() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();

  const [mode, setMode] = useState("deposit");
  const [amount, setAmount] = useState("");
  const [actionError, setActionError] = useState("");
  const [touchedTransfer, setTouchedTransfer] = useState(false);
  const [isTransferFocused, setIsTransferFocused] = useState(false);

  const [selectedTemplateKey, setSelectedTemplateKey] = useState(GOAL_TEMPLATES[0].key);
  const [goalTitle, setGoalTitle] = useState(() => t(`savings.goals.templates.${GOAL_TEMPLATES[0].key}`));
  const [goalAmount, setGoalAmount] = useState("");
  const [goalCreateError, setGoalCreateError] = useState("");
  const [touchedGoalCreate, setTouchedGoalCreate] = useState(false);
  const [isGoalCreateFocused, setIsGoalCreateFocused] = useState(false);
  const goalTitleInputRef = useRef(null);
  const goalAmountInputRef = useRef(null);
  const [goalDate, setGoalDate] = useState("");

  const [goalAction, setGoalAction] = useState({ goalId: null, mode: "contribute", amount: "" });
  const [goalActionError, setGoalActionError] = useState("");
  const [touchedGoalAction, setTouchedGoalAction] = useState(false);
  const [isGoalActionFocused, setIsGoalActionFocused] = useState(false);
  const [editGoal, setEditGoal] = useState(null);
  const [editGoalTitle, setEditGoalTitle] = useState("");
  const [editGoalAmount, setEditGoalAmount] = useState("");
  const [editGoalDate, setEditGoalDate] = useState("");
  const [editGoalError, setEditGoalError] = useState("");
  const [editGoalOpen, setEditGoalOpen] = useState(false);
  const [archiveGoalError, setArchiveGoalError] = useState("");
  const [deleteGoalError, setDeleteGoalError] = useState("");
  const [goalToArchive, setGoalToArchive] = useState(null);
  const [goalToDelete, setGoalToDelete] = useState(null);
  const [showArchived, setShowArchived] = useState(false);

  const userQuery = useQuery({
    queryKey: ["users", "me"],
    queryFn: getCurrentUser,
  });
  const isPremium = !!userQuery.data?.is_premium;
  const summaryQuery = useSavingsSummaryQuery(isPremium);
  const goalsQuery = useGoalsQuery(isPremium);
  const depositMutation = useDepositToSavingsMutation();
  const withdrawMutation = useWithdrawFromSavingsMutation();
  const createGoalMutation = useCreateGoalMutation();
  const contributeMutation = useContributeToGoalMutation();
  const returnMutation = useReturnFromGoalMutation();
  const updateGoalMutation = useUpdateGoalMutation();
  const archiveGoalMutation = useArchiveGoalMutation();
  const restoreGoalMutation = useRestoreGoalMutation();
  const deleteGoalMutation = useDeleteGoalMutation();

  const transferParsed = useMemo(() => savingsTransferFormSchema.safeParse({ amount }), [amount]);
  const createGoalParsed = useMemo(
    () => goalCreateFormSchema.safeParse({ title: goalTitle, target_amount: goalAmount, target_date: goalDate || null }),
    [goalAmount, goalDate, goalTitle]
  );
  const editGoalParsed = useMemo(
    () => goalUpdateFormSchema.safeParse({ title: editGoalTitle, target_amount: editGoalAmount, target_date: editGoalDate || null }),
    [editGoalAmount, editGoalDate, editGoalTitle]
  );
  const goalActionParsed = useMemo(
    () => goalActionAmountSchema.safeParse({ amount: goalAction.amount }),
    [goalAction.amount]
  );

  const transferAmountError = useMemo(() => {
    if (!touchedTransfer || transferParsed.success) return "";
    const firstIssue = transferParsed.error.issues[0];
    return firstIssue?.message ? t(firstIssue.message, { defaultValue: firstIssue.message }) : "";
  }, [t, touchedTransfer, transferParsed]);

  const createGoalErrorText = useMemo(() => {
    if (!touchedGoalCreate || createGoalParsed.success) return "";
    const firstIssue = createGoalParsed.error.issues[0];
    return firstIssue?.message ? t(firstIssue.message, { defaultValue: firstIssue.message }) : "";
  }, [createGoalParsed, t, touchedGoalCreate]);

  const goalActionErrorText = useMemo(() => {
    if (!touchedGoalAction || goalActionParsed.success) return "";
    const firstIssue = goalActionParsed.error.issues[0];
    return firstIssue?.message ? t(firstIssue.message, { defaultValue: firstIssue.message }) : "";
  }, [goalActionParsed, t, touchedGoalAction]);

  const loading = userQuery.isLoading || (isPremium && (summaryQuery.isLoading || goalsQuery.isLoading));
  const error =
    localizeApiError(userQuery.error?.message || summaryQuery.error?.message || goalsQuery.error?.message, t) ||
    userQuery.error?.message ||
    summaryQuery.error?.message ||
    goalsQuery.error?.message ||
    "";

  const summary = summaryQuery.data || {
    total_balance: 0,
    free_savings_balance: 0,
    locked_in_goals: 0,
    spendable_balance: 0,
  };
  const goals = goalsQuery.data || [];
  const activeGoals = goals.filter((goal) => goal.status !== "ARCHIVED");
  const archivedGoals = goals.filter((goal) => goal.status === "ARCHIVED");
  const activeGoalCount = goals.filter((goal) => goal.status === "ACTIVE").length;
  const activeGoalLimitReached = activeGoalCount >= MAX_ACTIVE_GOALS;
  const archivedGoalLimitReached = archivedGoals.length >= MAX_ARCHIVED_GOALS;

  const spendableBalance = Number(summary.spendable_balance || 0);
  const isSpendableNegative = spendableBalance < 0;
  const isDepositBlocked = mode === "deposit" && isSpendableNegative;
  const transferPanelAvailableAmount =
    mode === "deposit"
      ? Math.max(0, spendableBalance)
      : spendableBalance;
  const availableAmount =
    mode === "deposit"
      ? Math.max(0, spendableBalance)
      : Number(summary.free_savings_balance || 0);
  const isSubmittingTransfer = depositMutation.isPending || withdrawMutation.isPending;
  const canSubmitTransfer = transferParsed.success && parseAmountInput(amount) > 0 && !isSubmittingTransfer && !isDepositBlocked;
  const canSubmitCreateGoal = createGoalParsed.success && !createGoalMutation.isPending && !activeGoalLimitReached;
  const goalCreateHelperText = activeGoalLimitReached ? t("savings.goals.activeLimitReached") : t("savings.goals.createHint");

  const activeGoal = goals.find((goal) => goal.id === goalAction.goalId) || null;
  const goalActionAvailable =
    goalAction.mode === "contribute"
      ? Number(summary.free_savings_balance || 0)
      : Number(activeGoal?.funded_amount || 0);

  const handleTransferSubmit = async () => {
    setTouchedTransfer(true);
    setActionError("");
    if (!transferParsed.success) return;

    try {
      if (mode === "deposit") {
        await depositMutation.mutateAsync({ amount: transferParsed.data.amount });
      } else {
        await withdrawMutation.mutateAsync({ amount: transferParsed.data.amount });
      }
      setAmount("");
      setTouchedTransfer(false);
    } catch (e) {
      setActionError(localizeApiError(e?.message, t) || e?.message || t("savings.requestFailed"));
    }
  };

  const addQuickAmount = (value) => {
    setTouchedTransfer(true);
    setActionError("");
    const current = parseAmountInput(amount);
    setAmount(formatAmountInput(String(current + value), MAX_SAVINGS_AMOUNT_DIGITS));
  };

  const setQuickAmount = (value) => {
    setTouchedTransfer(true);
    setActionError("");
    setAmount(formatAmountInput(String(value), MAX_SAVINGS_AMOUNT_DIGITS));
  };

  const selectTemplate = (template) => {
    if (activeGoalLimitReached) return;
    setSelectedTemplateKey(template.key);
    setGoalTitle(template.key === "custom" ? "" : t(`savings.goals.templates.${template.key}`));
    setGoalDate("");
    setGoalCreateError("");
    if (template.key === "custom") {
      requestAnimationFrame(() => goalTitleInputRef.current?.focus());
    } else {
      requestAnimationFrame(() => goalAmountInputRef.current?.focus());
    }
  };

  const handleCreateGoal = async () => {
    setTouchedGoalCreate(true);
    setGoalCreateError("");
    if (activeGoalLimitReached) {
      setGoalCreateError(t("savings.goals.activeLimitReached"));
      return;
    }
    if (!createGoalParsed.success) return;

    try {
      await createGoalMutation.mutateAsync({
        title: createGoalParsed.data.title,
        target_amount: createGoalParsed.data.target_amount,
        target_date: createGoalParsed.data.target_date || null,
      });
      setGoalAmount("");
      setGoalDate("");
      setTouchedGoalCreate(false);
    } catch (e) {
      setGoalCreateError(localizeApiError(e?.message, t) || e?.message || t("savings.goals.requestFailed"));
    }
  };

  const openGoalAction = (goal, nextMode) => {
    setGoalActionError("");
    setTouchedGoalAction(false);
    setGoalAction((prev) =>
      prev.goalId === goal.id && prev.mode === nextMode
        ? { goalId: null, mode: "contribute", amount: "" }
        : { goalId: goal.id, mode: nextMode, amount: "" }
    );
  };

  const addGoalChip = (value) => {
    setTouchedGoalAction(true);
    setGoalActionError("");
    setGoalAction((prev) => {
      const current = parseAmountInput(prev.amount);
      return {
        ...prev,
        amount: formatAmountInput(String(current + value), MAX_SAVINGS_AMOUNT_DIGITS),
      };
    });
  };

  const setGoalChip = (value) => {
    setTouchedGoalAction(true);
    setGoalActionError("");
    setGoalAction((prev) => ({
      ...prev,
      amount: formatAmountInput(String(value), MAX_SAVINGS_AMOUNT_DIGITS),
    }));
  };

  const renderGoalAmount = (value, className = "") => (
    <CurrencyAmount
      value={value}
      format="display"
      tooltip="compact"
      className={`inline-flex items-baseline gap-1 ${className}`.trim()}
      valueClassName="font-medium"
      currencyClassName=""
    />
  );

  const openEditGoal = (goal) => {
    setEditGoal(goal);
    setEditGoalTitle(goal.title || "");
    setEditGoalAmount(formatAmountInput(String(goal.target_amount || ""), MAX_SAVINGS_AMOUNT_DIGITS));
    setEditGoalDate(goal.target_date || "");
    setEditGoalError("");
    setEditGoalOpen(true);
  };

  const handleEditGoal = async () => {
    if (!editGoal || !editGoalParsed.success || updateGoalMutation.isPending) return;
    setEditGoalError("");
    try {
      await updateGoalMutation.mutateAsync({
        goalId: editGoal.id,
        payload: {
          title: editGoalParsed.data.title,
          target_amount: editGoalParsed.data.target_amount,
          target_date: editGoalParsed.data.target_date || null,
        },
      });
      setEditGoalOpen(false);
    } catch (e) {
      setEditGoalError(localizeApiError(e?.message, t) || e?.message || t("savings.goals.requestFailed"));
    }
  };

  const handleArchiveGoal = async () => {
    if (!goalToArchive || archiveGoalMutation.isPending) return;
    setArchiveGoalError("");
    try {
      await archiveGoalMutation.mutateAsync(goalToArchive.id);
      setGoalToArchive(null);
    } catch (e) {
      setArchiveGoalError(localizeApiError(e?.message, t) || e?.message || t("savings.goals.requestFailed"));
    }
  };

  const handleRestoreGoal = async (goalId) => {
    if (activeGoalLimitReached) return;
    await restoreGoalMutation.mutateAsync(goalId);
  };

  const handleDeleteGoal = async () => {
    if (!goalToDelete || deleteGoalMutation.isPending) return;
    setDeleteGoalError("");
    try {
      await deleteGoalMutation.mutateAsync(goalToDelete.id);
      setGoalToDelete(null);
    } catch (e) {
      setDeleteGoalError(localizeApiError(e?.message, t) || e?.message || t("savings.goals.requestFailed"));
    }
  };

  const handleGoalActionSubmit = async (goalId) => {
    setTouchedGoalAction(true);
    setGoalActionError("");
    if (!goalActionParsed.success) return;

    try {
      if (goalAction.mode === "contribute") {
        await contributeMutation.mutateAsync({ goalId, payload: { amount: goalActionParsed.data.amount } });
      } else {
        await returnMutation.mutateAsync({ goalId, payload: { amount: goalActionParsed.data.amount } });
      }
      setGoalAction({ goalId: null, mode: "contribute", amount: "" });
      setTouchedGoalAction(false);
    } catch (e) {
      setGoalActionError(localizeApiError(e?.message, t) || e?.message || t("savings.goals.requestFailed"));
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] grid place-items-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return <p className="py-10 text-sm text-destructive">{error}</p>;
  }

  if (!isPremium) {
    return (
      <div className="space-y-6 py-4">
        <PageHeader title={t("savings.title")} description={t("savings.subtitle")} />
        <Card className="overflow-hidden border-primary/25 bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.14),transparent_45%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,1))] dark:border-primary/30 dark:bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.16),transparent_42%),linear-gradient(180deg,rgba(20,24,29,0.98),rgba(10,12,16,1))]">
          <CardContent className="flex flex-col gap-6 p-6 sm:p-8 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                <Crown className="h-3.5 w-3.5" />
                {t("savings.premiumBadge")}
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-semibold tracking-tight">{t("savings.premiumTitle")}</h2>
                <p className="max-w-2xl text-sm leading-6 text-muted-foreground">{t("savings.premiumDesc")}</p>
              </div>
            </div>
            <Button className="h-11 rounded-2xl px-6 text-base" onClick={() => navigate("/premium")}>
              {t("savings.viewPlans")}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 py-4">
      <PageHeader title={t("savings.title")} description={t("savings.subtitle")} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard title={t("savings.cards.totalBalance")} value={summary.total_balance} hint={t("savings.cards.totalBalanceHint")} icon={Sparkles} />
        <SummaryCard title={t("savings.cards.spendable")} value={summary.spendable_balance} hint={t("savings.cards.spendableHint")} icon={ArrowDownLeft} />
        <SummaryCard title={t("savings.cards.freeSavings")} value={summary.free_savings_balance} hint={t("savings.cards.freeSavingsHint")} accent="primary" icon={Wallet} />
        <SummaryCard title={t("savings.cards.lockedGoals")} value={summary.locked_in_goals} hint={t("savings.cards.lockedGoalsHint")} icon={ArrowRight} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
        <Card className="overflow-hidden">
          <CardHeader className="space-y-4">
            <div className="space-y-1.5">
              <CardTitle>{t("savings.transferTitle")}</CardTitle>
              <CardDescription>{t("savings.transferDesc")}</CardDescription>
            </div>
            <div>
              <div className="inline-flex rounded-2xl border border-border bg-muted/50 p-1">
                <button
                  type="button"
                  onClick={() => {
                    setMode("deposit");
                    setActionError("");
                  }}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${mode === "deposit" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                >
                  {t("savings.deposit")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode("withdraw");
                    setActionError("");
                  }}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${mode === "withdraw" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                >
                  {t("savings.withdraw")}
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 rounded-3xl border border-border/70 bg-[linear-gradient(180deg,rgba(34,197,94,0.08),transparent)] p-4 sm:p-5 md:grid-cols-[1.1fr_0.5fr_1.1fr] md:items-center">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  {mode === "deposit" ? t("savings.flow.spendable") : t("savings.flow.spendable")}
                </p>
                <CurrencyAmount
                  value={transferPanelAvailableAmount}
                  format="display"
                  tooltip="compact"
                  className="flex items-baseline gap-1.5 flex-wrap"
                  valueClassName="text-2xl font-semibold tabular-nums"
                  currencyClassName="text-sm"
                />
              </div>
              <div className="flex items-center justify-center">
                {mode === "deposit" ? (
                  <ArrowUpRight className="h-6 w-6 text-primary" />
                ) : (
                  <ArrowDownLeft className="h-6 w-6 text-primary" />
                )}
              </div>
              <div className="space-y-1 md:text-right">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{t("savings.flow.freeSavings")}</p>
                <CurrencyAmount
                  value={summary.free_savings_balance}
                  format="display"
                  tooltip="compact"
                  className="flex items-baseline gap-1.5 flex-wrap justify-end text-primary"
                  valueClassName="text-2xl font-semibold tabular-nums"
                  currencyClassName="text-sm opacity-80"
                />
              </div>
            </div>
            {mode === "deposit" && isSpendableNegative ? (
              <p className="text-sm text-amber-400">
                {t("savings.negativeSpendableHint")}
              </p>
            ) : null}

            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.8fr)]">
              <div className="space-y-3">
                <label className="text-sm font-medium">{t("savings.amountLabel")}</label>
                <div>
                  <Input
                    type="text"
                    inputMode="numeric"
                    maxLength={MAX_SAVINGS_AMOUNT_INPUT_LENGTH}
                    value={amount}
                    disabled={isDepositBlocked}
                    placeholder={t("savings.amountPlaceholder")}
                    onChange={(e) => {
                      setAmount(formatAmountInput(e.target.value, MAX_SAVINGS_AMOUNT_DIGITS));
                      setTouchedTransfer(true);
                      setActionError("");
                    }}
                    onFocus={() => setIsTransferFocused(true)}
                    onBlur={() => setIsTransferFocused(false)}
                    className={`h-14 rounded-2xl px-4 text-xl font-semibold tabular-nums ${isTransferFocused && transferAmountError ? "border-red-500 focus-visible:border-red-500" : ""}`}
                  />
                  {isTransferFocused && transferAmountError ? <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{transferAmountError}</p> : null}
                  {actionError ? <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{actionError}</p> : null}
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-muted/35 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  {mode === "deposit" ? t("savings.availableToMove") : t("savings.availableToWithdraw")}
                </p>
                <CurrencyAmount
                  value={availableAmount}
                  format="display"
                  tooltip="compact"
                  className="mt-2 flex items-baseline gap-1.5 flex-wrap"
                  valueClassName="text-2xl font-semibold tabular-nums"
                  currencyClassName="text-sm"
                />
                <p className="mt-2 text-sm text-muted-foreground">
                  {mode === "deposit" ? t("savings.depositHint") : t("savings.withdrawHint")}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {QUICK_AMOUNTS.map((chipAmount) => (
                <button
                  key={chipAmount}
                  type="button"
                  onClick={() => addQuickAmount(chipAmount)}
                  disabled={isDepositBlocked}
                  className="rounded-full border border-border bg-muted/40 px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-45"
                >
                  +{formatAmountDisplay(chipAmount)}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setQuickAmount(availableAmount)}
                disabled={isDepositBlocked}
                className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/15 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-45"
              >
                {t("savings.useMax")}
              </button>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted-foreground">
                {mode === "deposit" ? t("savings.depositCaption") : t("savings.withdrawCaption")}
              </p>
              <Button className="h-12 min-w-[200px] rounded-2xl text-base" disabled={!canSubmitTransfer} onClick={handleTransferSubmit}>
                {isSubmittingTransfer ? t("common.loading") : mode === "deposit" ? t("savings.moveToSavings") : t("savings.moveToBalance")}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader className="space-y-3">
            <div className="space-y-1.5">
              <CardTitle>{t("savings.goals.createTitle")}</CardTitle>
              <CardDescription>{t("savings.goals.createDesc")}</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-2.5 xl:grid-cols-3">
              {GOAL_TEMPLATES.map((template) => {
                const IconComponent = template.icon;
                const active = selectedTemplateKey === template.key;
                return (
                  <button
                    key={template.key}
                    type="button"
                    onClick={() => selectTemplate(template)}
                    disabled={activeGoalLimitReached}
                    title={activeGoalLimitReached ? t("savings.goals.activeLimitReached") : undefined}
                    className={`flex min-w-0 items-center gap-2.5 rounded-2xl border px-3 py-2.5 text-left transition-all disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-45 ${active ? "border-primary/45 bg-card shadow-[0_0_0_1px_rgba(34,197,94,0.14)]" : "border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.02),transparent)] hover:border-primary/20"}`}
                  >
                    <IconComponent className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <p className="min-w-0 truncate text-xs font-semibold leading-4 sm:text-sm">
                      {t(`savings.goals.templates.${template.key}`)}
                    </p>
                  </button>
                );
              })}
            </div>

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(220px,0.72fr)]">
              <div className="space-y-2">
                <label className="text-sm font-medium">{t("savings.goals.goalNameLabel")}</label>
                <Input
                  ref={goalTitleInputRef}
                  value={goalTitle}
                  maxLength={32}
                  disabled={activeGoalLimitReached}
                  onChange={(e) => {
                    setGoalTitle(e.target.value);
                    setTouchedGoalCreate(true);
                    setGoalCreateError("");
                  }}
                  className="h-12 rounded-2xl"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">{t("savings.goals.targetLabel")}</label>
                <div>
                  <Input
                    ref={goalAmountInputRef}
                    type="text"
                    inputMode="numeric"
                    maxLength={MAX_SAVINGS_AMOUNT_INPUT_LENGTH}
                    value={goalAmount}
                    disabled={activeGoalLimitReached}
                    placeholder={t("savings.amountPlaceholder")}
                    onChange={(e) => {
                      setGoalAmount(formatAmountInput(e.target.value, MAX_SAVINGS_AMOUNT_DIGITS));
                      setTouchedGoalCreate(true);
                      setGoalCreateError("");
                    }}
                    onFocus={() => setIsGoalCreateFocused(true)}
                    onBlur={() => setIsGoalCreateFocused(false)}
                    className={`h-12 rounded-2xl ${isGoalCreateFocused && createGoalErrorText ? "border-red-500 focus-visible:border-red-500" : ""}`}
                  />
                  {isGoalCreateFocused && createGoalErrorText ? <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{createGoalErrorText}</p> : null}
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("savings.goals.targetDateLabel")} ({t("common.optional")})
              </label>
              <Input
                type="date"
                value={goalDate}
                disabled={activeGoalLimitReached}
                onChange={(e) => {
                  setGoalDate(e.target.value);
                  setTouchedGoalCreate(true);
                  setGoalCreateError("");
                }}
                className="h-12 rounded-2xl"
              />
            </div>
            {goalCreateError ? <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{goalCreateError}</p> : null}
            <div className="flex items-center justify-between gap-4 rounded-2xl border border-border bg-muted/25 p-4">
              <p className={`text-sm ${activeGoalLimitReached ? "font-medium text-amber-400" : "text-muted-foreground"}`}>{goalCreateHelperText}</p>
              <Button
                className="h-11 rounded-2xl px-5"
                disabled={!canSubmitCreateGoal}
                title={activeGoalLimitReached ? t("savings.goals.activeLimitReached") : undefined}
                onClick={handleCreateGoal}
              >
                {createGoalMutation.isPending ? t("common.loading") : t("savings.goals.addGoal")}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>{t("savings.goals.listTitle")}</CardTitle>
          <CardDescription>{t("savings.goals.listDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          {goals.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-border bg-muted/20 p-8 text-center">
              <Target className="mx-auto h-6 w-6 text-primary" />
              <p className="mt-4 text-lg font-semibold">{t("savings.goals.emptyTitle")}</p>
              <p className="mt-2 text-sm text-muted-foreground">{t("savings.goals.emptyDesc")}</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid gap-4 xl:grid-cols-2">
              {activeGoals.map((goal) => {
                const progress = Math.max(0, Math.min(Number(goal.progress_percent || 0), 100));
                const isExpanded = goalAction.goalId === goal.id;
                const isContributeMode = goalAction.mode === "contribute";
                return (
                  <div key={goal.id} className="rounded-3xl border border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.02),transparent)] p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <h3 className="text-xl font-semibold tracking-tight">{goal.title}</h3>
                        <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-sm text-muted-foreground">
                          {appLang.startsWith("uz") ? (
                            <>
                              {renderGoalAmount(goal.target_amount)}
                              <span>{t("savings.goals.savedFrom")}</span>
                              {renderGoalAmount(goal.funded_amount)}
                              <span>{t("savings.goals.savedSuffix")}</span>
                            </>
                          ) : (
                            <>
                              {renderGoalAmount(goal.funded_amount)}
                              <span>{t("savings.goals.savedOf")}</span>
                              {renderGoalAmount(goal.target_amount)}
                            </>
                          )}
                        </div>
                          {goal.target_date ? (
                            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                              <CalendarClock className="h-3.5 w-3.5" />
                              <span className="font-medium text-muted-foreground/90">{t("savings.goals.deadlinePrefix")}</span>
                              <span>{formatDisplayDate(goal.target_date, appLang)}</span>
                              <GoalTimeBadge timeState={goal.time_state} t={t} />
                            </div>
                          ) : null}
                      </div>
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        <GoalStatusBadge status={goal.status} t={t} />
                      </div>
                    </div>

                    <div className="mt-5 space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{t("savings.goals.progress")}</span>
                        <span className="font-medium tabular-nums">{progress.toFixed(progress % 1 === 0 ? 0 : 1)}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-muted/60">
                        <div className="h-2 rounded-full bg-primary transition-[width] duration-300" style={{ width: `${progress}%` }} />
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                        <span className="flex flex-wrap items-baseline gap-1 text-muted-foreground">
                          {renderGoalAmount(goal.remaining_amount)}
                          <span>{t("savings.goals.remainingLabel")}</span>
                        </span>
                        <span className="flex flex-wrap items-baseline gap-1 font-medium text-primary">
                          {renderGoalAmount(goal.funded_amount)}
                          <span>{t("savings.goals.lockedLabel")}</span>
                        </span>
                      </div>
                    </div>

                    <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant={isExpanded && isContributeMode ? "default" : "outline"}
                          className="rounded-2xl"
                          onClick={() => openGoalAction(goal, "contribute")}
                        >
                          {t("savings.goals.contribute")}
                        </Button>
                        <Button
                          variant={isExpanded && !isContributeMode ? "default" : "outline"}
                          className="rounded-2xl"
                          onClick={() => openGoalAction(goal, "return")}
                        >
                          {t("savings.goals.return")}
                        </Button>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button variant="ghost" className="rounded-2xl text-muted-foreground" onClick={() => openEditGoal(goal)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          {t("common.edit")}
                        </Button>
                        <Button
                          variant="ghost"
                          className="rounded-2xl text-muted-foreground"
                          disabled={archivedGoalLimitReached}
                          title={archivedGoalLimitReached ? t("savings.goals.archivedLimitReached") : undefined}
                          onClick={() => {
                            setArchiveGoalError("");
                            setGoalToArchive(goal);
                          }}
                        >
                          <Archive className="mr-2 h-4 w-4" />
                          {t("savings.goals.archive")}
                        </Button>
                      </div>
                    </div>

                    {isExpanded ? (
                      <div className="mt-5 space-y-4 rounded-2xl border border-border bg-muted/25 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-medium">
                              {isContributeMode ? t("savings.goals.contributeDesc") : t("savings.goals.returnDesc")}
                            </p>
                            <p className="flex flex-wrap items-baseline gap-1 text-sm text-muted-foreground">
                              {renderGoalAmount(goalActionAvailable)}
                              <span>{t("savings.goals.availableNowLabel")}</span>
                            </p>
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-8 rounded-xl px-2.5 text-muted-foreground hover:text-foreground"
                            onClick={() => setGoalAction({ goalId: null, mode: "contribute", amount: "" })}
                          >
                            <ChevronUp className="mr-1 h-4 w-4" />
                            {t("common.close")}
                          </Button>
                        </div>
                        <div>
                          <Input
                            type="text"
                            inputMode="numeric"
                            maxLength={MAX_SAVINGS_AMOUNT_INPUT_LENGTH}
                            value={goalAction.amount}
                            placeholder={t("savings.amountPlaceholder")}
                            onChange={(e) => {
                              setGoalAction((prev) => ({
                                ...prev,
                                amount: formatAmountInput(e.target.value, MAX_SAVINGS_AMOUNT_DIGITS),
                              }));
                              setTouchedGoalAction(true);
                              setGoalActionError("");
                            }}
                            onFocus={() => setIsGoalActionFocused(true)}
                            onBlur={() => setIsGoalActionFocused(false)}
                            className={`h-12 rounded-2xl ${isGoalActionFocused && goalActionErrorText ? "border-red-500 focus-visible:border-red-500" : ""}`}
                          />
                          {isGoalActionFocused && goalActionErrorText ? <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{goalActionErrorText}</p> : null}
                          {goalActionError ? <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{goalActionError}</p> : null}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {GOAL_ACTION_CHIPS.map((chipAmount) => (
                            <button
                              key={chipAmount}
                              type="button"
                              onClick={() => addGoalChip(chipAmount)}
                              className="rounded-full border border-border bg-background px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
                            >
                              +{formatAmountDisplay(chipAmount)}
                            </button>
                          ))}
                          <button
                            type="button"
                            onClick={() => setGoalChip(goalActionAvailable)}
                            className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/15"
                          >
                            {t("savings.useMax")}
                          </button>
                        </div>
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="text-sm text-muted-foreground">
                            {isContributeMode ? t("savings.goals.contributeHint") : t("savings.goals.returnHint")}
                          </p>
                          <Button
                            className="rounded-2xl"
                            disabled={!goalActionParsed.success || contributeMutation.isPending || returnMutation.isPending}
                            onClick={() => handleGoalActionSubmit(goal.id)}
                          >
                            {contributeMutation.isPending || returnMutation.isPending
                              ? t("common.loading")
                              : isContributeMode
                                ? t("savings.goals.confirmContribute")
                                : t("savings.goals.confirmReturn")}
                          </Button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                );
              })}
              </div>
              {archivedGoals.length > 0 ? (
                <div className="space-y-4">
                  <Button variant="ghost" className="px-0 text-muted-foreground" onClick={() => setShowArchived((prev) => !prev)}>
                    {showArchived ? t("savings.goals.hideArchived") : t("savings.goals.showArchived", { count: archivedGoals.length })}
                  </Button>
                  {showArchived ? (
                    <div className="grid gap-4 xl:grid-cols-2">
                      {archivedGoals.map((goal) => (
                        <div key={goal.id} className="rounded-3xl border border-border bg-muted/10 p-5 opacity-80">
                          <div className="flex items-start justify-between gap-3">
                            <div className="space-y-1">
                              <h3 className="text-xl font-semibold tracking-tight">{goal.title}</h3>
                              <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-sm text-muted-foreground">
                                {appLang.startsWith("uz") ? (
                                  <>
                                    {renderGoalAmount(goal.target_amount)}
                                    <span>{t("savings.goals.savedFrom")}</span>
                                    {renderGoalAmount(goal.funded_amount)}
                                    <span>{t("savings.goals.savedSuffix")}</span>
                                  </>
                                ) : (
                                  <>
                                    {renderGoalAmount(goal.funded_amount)}
                                    <span>{t("savings.goals.savedOf")}</span>
                                    {renderGoalAmount(goal.target_amount)}
                                  </>
                                )}
                              </div>
                            </div>
                            <GoalStatusBadge status={goal.status} t={t} />
                          </div>
                          <div className="mt-5 flex flex-wrap gap-2">
                            <Button
                              variant="outline"
                              className="rounded-2xl"
                              onClick={() => handleRestoreGoal(goal.id)}
                              disabled={restoreGoalMutation.isPending || activeGoalLimitReached}
                              title={activeGoalLimitReached ? t("savings.goals.activeLimitReached") : undefined}
                            >
                              {t("savings.goals.restore")}
                            </Button>
                            <Button
                              variant="ghost"
                              className="rounded-2xl text-destructive"
                              onClick={() => {
                                setDeleteGoalError("");
                                setGoalToDelete(goal);
                              }}
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              {t("savings.goals.deletePermanent")}
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={editGoalOpen} onOpenChange={setEditGoalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("savings.goals.editTitle")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("savings.goals.goalNameLabel")}</label>
              <Input value={editGoalTitle} onChange={(e) => setEditGoalTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("savings.goals.targetLabel")}</label>
              <Input value={editGoalAmount} inputMode="numeric" onChange={(e) => setEditGoalAmount(formatAmountInput(e.target.value, MAX_SAVINGS_AMOUNT_DIGITS))} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("savings.goals.targetDateLabel")} ({t("common.optional")})
              </label>
              <Input type="date" value={editGoalDate} onChange={(e) => setEditGoalDate(e.target.value)} />
            </div>
            {editGoalError ? <p className="text-sm text-red-500">{editGoalError}</p> : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditGoalOpen(false)}>{t("common.cancel")}</Button>
            <Button onClick={handleEditGoal} disabled={!editGoalParsed.success || updateGoalMutation.isPending}>{t("common.save")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!goalToArchive}
        onOpenChange={(open) => {
          if (!open) {
            setGoalToArchive(null);
            setArchiveGoalError("");
          }
        }}
        title={t("savings.goals.archiveTitle")}
        description={t("savings.goals.archiveDesc")}
        onConfirm={handleArchiveGoal}
        confirmText={t("savings.goals.archive")}
        cancelText={t("common.cancel")}
        isConfirming={archiveGoalMutation.isPending}
        error={archiveGoalError}
      />

      <ConfirmDialog
        open={!!goalToDelete}
        onOpenChange={(open) => {
          if (!open) {
            setGoalToDelete(null);
            setDeleteGoalError("");
          }
        }}
        title={t("savings.goals.deletePermanentTitle")}
        description={t("savings.goals.deletePermanentDesc")}
        onConfirm={handleDeleteGoal}
        confirmText={t("savings.goals.deletePermanent")}
        cancelText={t("common.cancel")}
        isConfirming={deleteGoalMutation.isPending}
        error={deleteGoalError}
      />
    </div>
  );
}
