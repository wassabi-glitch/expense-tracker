import { createElement, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Archive,
  ArrowLeft,
  ArrowRightLeft,
  Banknote,
  BriefcaseBusiness,
  CalendarDays,
  CircleDollarSign,
  CreditCard,
  History,
  PiggyBank,
  Plus,
  RotateCcw,
  ShieldAlert,
  Target,
  Trash2,
  Wallet,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { getCurrentUser, getDebts, getPaymentPlans } from "@/lib/api";
import { getBudgets, getBudgetSubcategories } from "@/lib/api/budgets";
import { CATEGORIES } from "@/lib/category";
import { localizeApiError } from "@/lib/errorMessages";
import { formatAmountInput, formatDisplayDate, formatDisplayDateTime, formatUzs, parseAmountInput } from "@/lib/format";
import { toISODateInTimeZone } from "@/lib/date";
import { goalActionAmountSchema, goalAllocationsFormSchema, goalCreateFormSchema, goalDebtPaymentFormSchema, goalUseFormSchema } from "./savingsSchemas";
import {
  GOAL_CREATE_CHOICE_COPY,
  GOAL_INTENT_LABELS,
  buildFundProjectGraduationPayload,
  buildFundProjectNavigationState,
  buildGoalCreatePayload,
  getGoalCardUiState,
} from "./goalUiState";
import { useSavingsSummaryQuery } from "./hooks/useSavingsQueries";
import { useGoalActivityQuery, useGoalsQuery } from "./hooks/useGoalsQueries";
import {
  useArchiveGoalMutation,
  useContributeToGoalMutation,
  useCreateGoalMutation,
  useDeleteGoalMutation,
  useGraduateGoalMutation,
  useMoveGoalFundingMutation,
  useRecordGoalDebtPaymentMutation,
  useRecordGoalPurchaseMutation,
  useRestoreGoalMutation,
  useReturnFromGoalMutation,
  useUseReserveGoalMutation,
} from "./hooks/useGoalsMutations";

const GOAL_CREATE_ICONS = {
  RESERVE: ShieldAlert,
  PLANNED_PURCHASE: Target,
  PAY_OBLIGATION: ArrowRightLeft,
};

const GOAL_ACTION_ICONS = {
  "make-payment": CircleDollarSign,
  "graduate-project": BriefcaseBusiness,
  "open-project": BriefcaseBusiness,
};

const OBLIGATION_CREATE_CHOICES = [
  {
    type: "PAYMENT_PLAN",
    title: "Payment plan",
    description: "Scheduled payments for a phone, loan, course, home, vehicle, or service.",
    icon: CreditCard,
  },
  {
    type: "DEBT",
    title: "Debt",
    description: "Money you owe without a formal payment schedule.",
    icon: Banknote,
  },
];

const RESERVE_GOAL_TYPES = [
  { id: "emergency", title: "Emergency fund", description: "Money you do not want to touch unless something serious happens." },
  { id: "medical", title: "Medical reserve", description: "Money for treatment, medicine, appointments, or urgent care." },
  { id: "rent", title: "Rent cushion", description: "Money kept ready for rent or housing pressure." },
  { id: "family", title: "Family support", description: "Money set aside to help family when needed." },
  { id: "buffer", title: "General buffer", description: "Flexible money for whatever life throws at you." },
  { id: "custom", title: "Custom", description: "Name your own reason for setting money aside." },
];

const PURCHASE_STEPS = {
  CONFIRM_PURCHASE: 1,
  PAYMENT: 2,
  CLASSIFICATION: 3,
  PAYMENT_PLAN: 4,
  REVIEW: 5,
};

const PAYMENT_PLAN_FREQUENCIES = [
  { value: "WEEKLY", label: "Weekly" },
  { value: "BIWEEKLY", label: "Every two weeks" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "YEARLY", label: "Yearly" },
];

const MAX_PLANNED_PURCHASE_PAYMENT_WALLETS = 3;
const MAX_PREPARE_PAYMENT_TARGET_WALLETS = 3;
const MAX_PREPARE_PAYMENT_MOVE_ROWS = 9;
const OWNED_PAYMENT_WALLET_TYPES = ["CASH", "DEBIT", "PRELOADED", "SAVINGS"];

const walletIcon = {
  CASH: Banknote,
  DEBIT: CreditCard,
  CREDIT: CreditCard,
  PRELOADED: CreditCard,
  SAVINGS: PiggyBank,
};

function money(value) {
  return `${formatUzs(Number(value || 0))} UZS`;
}

function isOwnedPaymentWalletForCurrency(wallet, currency) {
  return Boolean(
    wallet &&
    wallet.is_active !== false &&
    wallet.currency === currency &&
    OWNED_PAYMENT_WALLET_TYPES.includes(wallet.wallet_type)
  );
}

function newMoveFundingDestination(sourceWalletId = "", targetWalletId = "") {
  return {
    row_id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    target_wallet_id: targetWalletId ? String(targetWalletId) : "",
    amount: "",
    has_fee: false,
    fee_amount: "",
    fee_wallet_id: sourceWalletId ? String(sourceWalletId) : "",
    fee_note: "",
  };
}

function newMoveFundingGroup(sourceWalletId = "", targetWalletId = "") {
  return {
    group_id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    source_wallet_id: sourceWalletId ? String(sourceWalletId) : "",
    destinations: [newMoveFundingDestination(sourceWalletId, targetWalletId)],
  };
}

function StatCard({ title, value, icon, tone = "default", caption }) {
  return (
    <Card className={cn("border-border shadow-sm", tone === "danger" && "border-destructive/40")}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {createElement(icon, {
          className: cn("h-4 w-4 text-muted-foreground", tone === "danger" && "text-destructive"),
        })}
      </CardHeader>
      <CardContent>
        <div className={cn("text-2xl font-semibold tabular-nums", tone === "danger" && "text-destructive")}>
          {money(value)}
        </div>
        {caption ? <p className="mt-2 text-xs text-muted-foreground">{caption}</p> : null}
      </CardContent>
    </Card>
  );
}

function WalletFundingCard({ wallet }) {
  const Icon = walletIcon[wallet.wallet_type] || Wallet;
  return (
    <Card className={cn("border-border", wallet.over_allocated_amount > 0 && "border-destructive/50")}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="rounded-md border border-border bg-muted/40 p-2">
              <Icon className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base">{wallet.wallet_name}</CardTitle>
              <CardDescription>{wallet.wallet_type} / {wallet.currency}</CardDescription>
            </div>
          </div>
          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-600">
            {wallet.eligible_for_goal_funding ? "Goal money" : "Prepared payment"}
          </span>
        </div>
      </CardHeader>
      <CardContent className="grid gap-2 text-sm">
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Balance</span>
          <span className="font-medium">{money(wallet.balance)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Reserved</span>
          <span className="font-medium">{money(wallet.allocated_to_goals)}</span>
        </div>
        {wallet.eligible_for_goal_funding ? (
          <div className="flex justify-between gap-3">
            <span className="text-muted-foreground">Free to reserve</span>
            <span className="font-medium">{money(wallet.available_for_goals)}</span>
          </div>
        ) : null}
        {wallet.over_allocated_amount > 0 ? (
          <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive">
            Reserved too much by {money(wallet.over_allocated_amount)}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function FundingSources({ goal }) {
  const sources = goal.funding_sources || [];
  if (!sources.length) {
    return <p className="text-sm text-muted-foreground">No wallet money reserved yet.</p>;
  }
  const sourceLabel = goal.intent === "RESERVE" ? "protected now" : "still reserved";
  return (
    <div className="space-y-2">
      {sources.map((source) => (
        <div key={source.wallet_id} className="flex items-center justify-between rounded-md border border-border bg-muted/20 px-3 py-2 text-sm">
          <div>
            <div className="font-medium">{source.wallet_name}</div>
            <div className="text-xs text-muted-foreground">{source.wallet_type} - {sourceLabel} {money(source.unreleased_amount)}</div>
          </div>
          <div className="font-semibold">{money(source.allocated_amount)}</div>
        </div>
      ))}
    </div>
  );
}

function intentLabel(intent) {
  return GOAL_INTENT_LABELS[intent] || String(intent || "RESERVE").replaceAll("_", " ").toLowerCase();
}

function formatGoalPercent(value) {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return 0;
  return Math.round(number);
}

function reserveGoalState(goal) {
  const target = Number(goal?.target_amount || 0);
  const protectedNow = Math.max(Number(goal?.unreleased_amount || 0), 0);
  const refillNeeded = Math.max(target - protectedNow, 0);
  const percent = target > 0 ? Math.min((protectedNow / target) * 100, 100) : 0;
  return {
    protectedNow,
    refillNeeded,
    usedFromReserve: Math.max(Number(goal?.consumed_amount || 0), 0),
    percent: formatGoalPercent(percent),
    label: refillNeeded > 0 ? "Refill needed" : "Fully reserved",
  };
}

function goalPrimaryMetric(goal) {
  if (goal.intent === "RESERVE") {
    const reserve = reserveGoalState(goal);
    return {
      label: reserve.label,
      amount: reserve.protectedNow,
      percent: reserve.percent,
    };
  }
  if (goal.status === "COMPLETED" && goal.intent === "PLANNED_PURCHASE") {
    return { label: "used", amount: Number(goal.consumed_amount || goal.target_amount || 0), percent: 100 };
  }
  return {
    label: "funded",
    amount: Number(goal.funded_amount || 0),
    percent: formatGoalPercent(goal.progress_percent),
  };
}

function goalCardStats(goal) {
  if (goal.intent === "RESERVE") {
    const reserve = reserveGoalState(goal);
    return [
      { label: "Refill needed", amount: reserve.refillNeeded },
      { label: "Used from reserve", amount: reserve.usedFromReserve },
      { label: "Protected now", amount: reserve.protectedNow },
    ];
  }
  return [
    { label: "Remaining", amount: Number(goal.remaining_amount || 0) },
    { label: "Already used", amount: Number(goal.released_amount || 0) },
    { label: "Still reserved", amount: Number(goal.unreleased_amount || 0) },
  ];
}

function activityAmountPrefix(type) {
  if (type === "RESERVED") return "+";
  if (["UNRESERVED", "GOAL_MONEY_USED", "RELEASED_TO_PROJECT"].includes(type)) return "-";
  return "";
}

function activityRoleLabel(role) {
  if (role === "from") return "From";
  if (role === "to") return "To";
  if (role === "paid_from") return "Paid from";
  if (role === "released_from") return "Released from";
  return "Wallet";
}

function defaultUseCategory(goal) {
  if (goal?.intent === "RESERVE") return "Health";
  return "Electronics";
}

function plannedPurchaseFundingRows(goal) {
  return (goal?.funding_sources || [])
    .filter((source) => Number(source.unreleased_amount || 0) > 0)
    .map((source) => ({
      wallet_id: String(source.wallet_id),
      amount: formatAmountInput(String(source.unreleased_amount)),
    }));
}

function createGoalDraftDefaults(intent = "RESERVE") {
  const reserve = RESERVE_GOAL_TYPES[0];
  return {
    intent,
    reserve_type: reserve.id,
    title: intent === "RESERVE" ? reserve.title : "",
    target_amount: "",
    target_date: "",
    obligation_type: "",
    linked_debt_id: "",
    debt_saving_mode: "FULL",
    fixed_debt_amount: "",
  };
}

export default function Savings() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
  const todayISO = useMemo(() => toISODateInTimeZone(), []);
  const userQuery = useQuery({ queryKey: ["users", "me"], queryFn: getCurrentUser });
  const isPremium = Boolean(userQuery.data?.is_premium);
  const budgetsQuery = useQuery({
    queryKey: ["budgets", "list"],
    queryFn: getBudgets,
    enabled: isPremium,
  });

  const summaryQuery = useSavingsSummaryQuery(isPremium);
  const goalsQuery = useGoalsQuery(isPremium);
  const createGoalMutation = useCreateGoalMutation();
  const allocateMutation = useContributeToGoalMutation();
  const returnMutation = useReturnFromGoalMutation();
  const useReserveMutation = useUseReserveGoalMutation();
  const recordPurchaseMutation = useRecordGoalPurchaseMutation();
  const recordDebtPaymentMutation = useRecordGoalDebtPaymentMutation();
  const moveGoalFundingMutation = useMoveGoalFundingMutation();
  const graduateGoalMutation = useGraduateGoalMutation();
  const archiveMutation = useArchiveGoalMutation();
  const restoreMutation = useRestoreGoalMutation();
  const deleteMutation = useDeleteGoalMutation();

  const [createGoalOpen, setCreateGoalOpen] = useState(false);
  const [createGoalStep, setCreateGoalStep] = useState(1);
  const [goalForm, setGoalForm] = useState(() => createGoalDraftDefaults(""));
  const [goalFormError, setGoalFormError] = useState("");
  const [fundingDialog, setFundingDialog] = useState(null);
  const [fundingRows, setFundingRows] = useState([]);
  const [fundingAmount, setFundingAmount] = useState("");
  const [fundingWalletId, setFundingWalletId] = useState("");
  const [fundingError, setFundingError] = useState("");
  const [useDialog, setUseDialog] = useState(null);
  const [prepareDialog, setPrepareDialog] = useState(null);
  const [useForm, setUseForm] = useState({
    amount: "",
    payment_allocations: [],
    category: "Electronics",
    subcategory_id: "",
    date: "",
    settlement_mode: "DIRECT",
    result_type: "EXPENSE_ONLY",
    asset_title: "",
    adjust_target_to_purchase_amount: false,
    payment_after_purchase: "PAID_IN_FULL",
    payment_plan_total_price: "",
    payment_plan_item_name: "",
    payment_plan_store_or_bank_name: "",
    payment_plan_months: "",
    payment_plan_frequency: "MONTHLY",
    create_next_payment_goal: true,
    next_payment_goal_title: "",
    next_payment_goal_target_date: "",
    note: "",
  });
  const [useError, setUseError] = useState("");
  const [purchaseStep, setPurchaseStep] = useState(PURCHASE_STEPS.CONFIRM_PURCHASE);
  const [moveFundingForm, setMoveFundingForm] = useState({
    groups: [],
    date: todayISO,
  });
  const [moveFundingError, setMoveFundingError] = useState("");
  const [moveFundingConfirmOpen, setMoveFundingConfirmOpen] = useState(false);
  const [activityGoal, setActivityGoal] = useState(null);
  const [graduateTarget, setGraduateTarget] = useState(null);
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const activityQuery = useGoalActivityQuery(activityGoal?.id, isPremium && Boolean(activityGoal?.id));

  const debtGoalOptionsQuery = useQuery({
    queryKey: ["debts", "goal-create-options"],
    queryFn: () => getDebts({ debt_type: "OWING", lifecycle_status: "OPEN", limit: 100 }),
    enabled: isPremium,
  });
  const paymentPlanGoalOptionsQuery = useQuery({
    queryKey: ["payment-plans", "goal-create-options"],
    queryFn: () => getPaymentPlans({ limit: 100 }),
    enabled: isPremium,
  });

  const summary = summaryQuery.data || {
    total_wallet_balance: 0,
    allocated_to_goals: 0,
    available_for_goals: 0,
    over_allocated_amount: 0,
    wallets: [],
  };
  const goals = goalsQuery.data || [];
  const budgetRows = useMemo(() => (
    Array.isArray(budgetsQuery.data) ? budgetsQuery.data : []
  ), [budgetsQuery.data]);
  const activeGoals = goals.filter((goal) => goal.status !== "ARCHIVED");
  const archivedGoals = goals.filter((goal) => goal.status === "ARCHIVED");
  const openDebtGoalIds = useMemo(() => new Set(
    activeGoals
      .filter((goal) => goal.status === "ACTIVE" && goal.intent === "PAY_OBLIGATION" && goal.linked_debt_id)
      .map((goal) => Number(goal.linked_debt_id))
  ), [activeGoals]);
  const debtGoalOptions = useMemo(() => {
    const items = Array.isArray(debtGoalOptionsQuery.data)
      ? debtGoalOptionsQuery.data
      : Array.isArray(debtGoalOptionsQuery.data?.items)
        ? debtGoalOptionsQuery.data.items
        : [];
    return items.filter((debt) => (
      Number(debt.remaining_amount || 0) > 0
    ));
  }, [debtGoalOptionsQuery.data]);
  const paymentPlanGoalOptions = useMemo(() => {
    const items = Array.isArray(paymentPlanGoalOptionsQuery.data)
      ? paymentPlanGoalOptionsQuery.data
      : Array.isArray(paymentPlanGoalOptionsQuery.data?.items)
        ? paymentPlanGoalOptionsQuery.data.items
        : [];
    return items.filter((plan) => Number(plan.remaining_amount || 0) > 0 && plan.status !== "ARCHIVED");
  }, [paymentPlanGoalOptionsQuery.data]);
  const standardDebtGoalOptions = debtGoalOptions;
  const selectedDebtOptions = goalForm.obligation_type === "PAYMENT_PLAN" ? paymentPlanGoalOptions : standardDebtGoalOptions;
  const selectedDebt = selectedDebtOptions.find((item) => String(item.id) === String(goalForm.linked_debt_id));
  const selectedDebtAlreadyHasGoal = selectedDebt ? openDebtGoalIds.has(Number(selectedDebt.id)) : false;
  const eligibleWallets = summary.wallets.filter((wallet) => wallet.eligible_for_goal_funding);
  const fundingSummaryWallets = summary.wallets.filter((wallet) =>
    wallet.eligible_for_goal_funding || Number(wallet.allocated_to_goals || 0) > 0
  );

  const selectedGoal = fundingDialog?.goal || null;
  const fundingMode = fundingDialog?.mode || "allocate";
  const fundingWallets = useMemo(() => {
    if (!selectedGoal) return [];
    if (fundingMode === "allocate") return eligibleWallets;
    const walletIds = new Set((selectedGoal.funding_sources || []).map((source) => source.wallet_id));
    return summary.wallets.filter((wallet) => walletIds.has(wallet.wallet_id));
  }, [eligibleWallets, fundingMode, selectedGoal, summary.wallets]);
  const selectedWallet = fundingWallets.find((wallet) => String(wallet.wallet_id) === String(fundingWalletId));
  const selectedSource = (selectedGoal?.funding_sources || []).find((source) => String(source.wallet_id) === String(fundingWalletId));
  const goalRemainingToFund = Math.max(Number(selectedGoal?.remaining_amount || 0), 0);
  const maxFundingAmount = fundingMode === "allocate"
    ? Math.min(Number(selectedWallet?.available_for_goals || 0), goalRemainingToFund)
    : Number(selectedSource?.unreleased_amount || 0);
  const fundingRowsTotal = fundingRows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0);
  const fundingRowWallet = (row) => eligibleWallets.find((wallet) => String(wallet.wallet_id) === String(row.wallet_id));
  const fundingRowMax = (row, index) => {
    const wallet = fundingRowWallet(row);
    const otherRowsTotal = fundingRows.reduce((sum, item, itemIndex) => (
      itemIndex === index ? sum : sum + parseAmountInput(item.amount)
    ), 0);
    return Math.max(Math.min(Number(wallet?.available_for_goals || 0), Math.max(goalRemainingToFund - otherRowsTotal, 0)), 0);
  };
  const selectedUseGoal = useDialog?.goal || null;
  const paymentWallets = summary.wallets;
  const paymentRows = useForm.payment_allocations || [];
  const paymentTotal = paymentRows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0);
  const isPlannedPurchase = selectedUseGoal?.intent === "PLANNED_PURCHASE";
  const isDebtGoalPayment = selectedUseGoal?.intent === "PAY_OBLIGATION";
  const isReserveUse = selectedUseGoal?.intent === "RESERVE";
  const goalFundingPaymentWalletIds = new Set((selectedUseGoal?.funding_sources || []).map((source) => String(source.wallet_id)));
  const paymentWalletsAllFundingSources = paymentRows.length > 0 && paymentRows.every((row) =>
    (selectedUseGoal?.funding_sources || []).some((source) => String(source.wallet_id) === String(row.wallet_id))
  );
  const paymentWalletsAllNonFundingSources = !isPlannedPurchase || useForm.settlement_mode !== "GOAL_BACKED_OFF_WALLET_PAYMENT" || paymentRows.every((row) =>
    !goalFundingPaymentWalletIds.has(String(row.wallet_id))
  );
  const paymentWalletIds = paymentRows.map((row) => String(row.wallet_id || ""));
  const paymentWalletRowsUnique = paymentWalletIds.length === new Set(paymentWalletIds).size;
  const isUseFromFundingSources = !isPlannedPurchase || useForm.settlement_mode === "DIRECT";
  const goalFundingAmountByWalletId = new Map(
    (selectedUseGoal?.funding_sources || []).map((source) => [String(source.wallet_id), Number(source.unreleased_amount || 0)])
  );
  const paymentRowsWithinFundingAmounts = !isUseFromFundingSources || paymentRows.every((row) => (
    parseAmountInput(row.amount) <= Number(goalFundingAmountByWalletId.get(String(row.wallet_id)) || 0)
  ));
  const paymentWalletOptions = selectedUseGoal?.intent === "PLANNED_PURCHASE" || selectedUseGoal?.intent === "PAY_OBLIGATION" || selectedUseGoal?.intent === "RESERVE"
    ? paymentWallets.filter((wallet) => {
      const isFundingWallet = goalFundingPaymentWalletIds.has(String(wallet.wallet_id));
      return isUseFromFundingSources
        ? isFundingWallet && isOwnedPaymentWalletForCurrency(wallet, selectedUseGoal.currency)
        : !isFundingWallet;
    })
    : paymentWallets;
  const paymentWalletRowLimit = selectedUseGoal?.intent === "PLANNED_PURCHASE"
    ? MAX_PLANNED_PURCHASE_PAYMENT_WALLETS
    : paymentWalletOptions.length;
  const paymentWalletRowsWithinLimit = paymentRows.length <= paymentWalletRowLimit;
  const selectedMoveGoal = prepareDialog?.goal || null;
  const moveFundingSourceOptions = (selectedMoveGoal?.funding_sources || [])
    .filter((source) => Number(source.unreleased_amount || 0) > 0);
  const moveFundingGroups = moveFundingForm.groups || [];
  const moveFundingRows = moveFundingGroups.flatMap((group, groupIndex) => (
    (group.destinations || []).map((destination, destinationIndex) => ({
      ...destination,
      source_wallet_id: group.source_wallet_id,
      group_index: groupIndex,
      destination_index: destinationIndex,
    }))
  ));
  const moveFundingTargetOptions = summary.wallets.filter((wallet) =>
    isOwnedPaymentWalletForCurrency(wallet, selectedMoveGoal?.currency)
  );
  const moveFundingWalletById = (walletId) => summary.wallets.find((wallet) =>
    String(wallet.wallet_id) === String(walletId)
  );
  const moveFundingTargetIds = new Set(
    moveFundingRows
      .map((row) => String(row.target_wallet_id || ""))
      .filter(Boolean)
  );
  const moveFundingTargetsWithinLimit = moveFundingTargetIds.size <= MAX_PREPARE_PAYMENT_TARGET_WALLETS;
  const moveFundingPairs = moveFundingRows.map((row) => `${row.source_wallet_id}:${row.target_wallet_id}`);
  const moveFundingPairsUnique = moveFundingPairs.length === new Set(moveFundingPairs).size;
  const moveFundingRowSource = (row) => moveFundingSourceOptions.find((source) =>
    String(source.wallet_id) === String(row.source_wallet_id)
  );
  const moveFundingGroupSource = (group) => moveFundingSourceOptions.find((source) =>
    String(source.wallet_id) === String(group.source_wallet_id)
  );
  const moveFundingGroupTargetOptions = (group, destinationIndex) => {
    const usedTargetIds = new Set((group.destinations || []).map((destination, index) => (
      index === destinationIndex ? "" : String(destination.target_wallet_id || "")
    )));
    return moveFundingTargetOptions.map((wallet) => ({
      ...wallet,
      disabled:
        String(wallet.wallet_id) === String(group.source_wallet_id) ||
        usedTargetIds.has(String(wallet.wallet_id)),
    }));
  };
  const moveFundingGroupMaxAmount = (group) => {
    const source = moveFundingGroupSource(group);
    if (!source) return 0;
    return Math.max(Number(source.unreleased_amount || 0), 0);
  };
  const moveFundingDestinationMaxAmount = (group, destinationIndex) => {
    const otherDestinationTotal = (group.destinations || []).reduce((sum, destination, index) => (
      index === destinationIndex ? sum : sum + parseAmountInput(destination.amount)
    ), 0);
    return Math.max(moveFundingGroupMaxAmount(group) - otherDestinationTotal, 0);
  };
  const moveFundingFeeWalletOptions = (row) => summary.wallets.filter((wallet) => (
    wallet.wallet_type !== "CASH" &&
    [row.source_wallet_id, row.target_wallet_id].includes(String(wallet.wallet_id))
  ));
  const moveFundingTotalMoved = moveFundingRows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0);
  const moveFundingTotalFees = moveFundingRows.reduce((sum, row) => (
    sum + (row.has_fee ? parseAmountInput(row.fee_amount) : 0)
  ), 0);
  const moveFundingPreparedByTarget = moveFundingRows.reduce((totals, row) => {
    const amount = parseAmountInput(row.amount);
    if (!row.target_wallet_id || amount <= 0) return totals;
    const key = String(row.target_wallet_id);
    return { ...totals, [key]: (totals[key] || 0) + amount };
  }, {});
  const moveFundingNetWalletChanges = moveFundingRows.reduce((totals, row) => {
    const amount = parseAmountInput(row.amount);
    if (amount > 0) {
      totals[String(row.source_wallet_id)] = (totals[String(row.source_wallet_id)] || 0) - amount;
      totals[String(row.target_wallet_id)] = (totals[String(row.target_wallet_id)] || 0) + amount;
    }
    if (row.has_fee) {
      const feeAmount = parseAmountInput(row.fee_amount);
      const feeWalletId = String(row.fee_wallet_id || row.source_wallet_id || "");
      if (feeWalletId && feeAmount > 0) {
        totals[feeWalletId] = (totals[feeWalletId] || 0) - feeAmount;
      }
    }
    return totals;
  }, {});
  const hasPreparePaymentRoute = (goal) => {
    const sources = (goal?.funding_sources || []).filter((source) => Number(source.unreleased_amount || 0) > 0);
    return sources.some((source) =>
      summary.wallets.some((wallet) =>
        isOwnedPaymentWalletForCurrency(wallet, goal.currency) &&
        String(wallet.wallet_id) !== String(source.wallet_id)
      )
    );
  };
  const useAmount = selectedUseGoal?.intent === "PLANNED_PURCHASE"
    ? paymentTotal
    : parseAmountInput(useForm.amount);
  const purchaseAmountDiffersFromTarget = selectedUseGoal?.intent === "PLANNED_PURCHASE" &&
    useAmount > 0 &&
    useAmount !== Number(selectedUseGoal?.target_amount || 0);
  const payment_planBridgeSelected = selectedUseGoal?.intent === "PLANNED_PURCHASE" &&
    useForm.payment_after_purchase === "PAYMENT_PLAN";
  const payment_planTotalPrice = parseAmountInput(useForm.payment_plan_total_price);
  const payment_planMonths = Number(useForm.payment_plan_months || 0);
  const payment_planRemainingAmount = Math.max(payment_planTotalPrice - paymentTotal, 0);
  const payment_planRegularPayment = payment_planMonths > 0
    ? Math.floor(payment_planRemainingAmount / payment_planMonths)
    : 0;
  const selectedUseBudget = useMemo(() => {
    if (!useForm.category) return null;
    const isoDate = useForm.date || todayISO;
    const [yearRaw, monthRaw] = String(isoDate).split("-");
    const year = Number(yearRaw);
    const month = Number(monthRaw);
    return budgetRows.find((budget) =>
      Number(budget.budget_year) === year &&
      Number(budget.budget_month) === month &&
      budget.category === useForm.category
    ) || null;
  }, [budgetRows, todayISO, useForm.category, useForm.date]);
  const subcategoriesQuery = useQuery({
    queryKey: ["budgets", "subcategories", selectedUseBudget?.id],
    queryFn: () => getBudgetSubcategories(selectedUseBudget.id),
    enabled: Boolean(isPremium && useDialog && selectedUseBudget?.id),
  });
  const useSubcategories = Array.isArray(subcategoriesQuery.data) ? subcategoriesQuery.data : [];

  const openFunding = (goal, mode) => {
    const wallets = mode === "allocate"
      ? eligibleWallets.filter((wallet) => wallet.available_for_goals > 0)
      : summary.wallets.filter((wallet) => (goal.funding_sources || []).some((source) => source.wallet_id === wallet.wallet_id));
    setFundingDialog({ goal, mode });
    setFundingWalletId(wallets[0] ? String(wallets[0].wallet_id) : "");
    setFundingRows(mode === "allocate" && wallets[0] ? [{ wallet_id: String(wallets[0].wallet_id), amount: "" }] : []);
    setFundingAmount("");
    setFundingError("");
  };

  const updateFundingRow = (index, patch) => {
    setFundingRows((rows) => rows.map((row, rowIndex) => (
      rowIndex === index ? { ...row, ...patch } : row
    )));
  };

  const addFundingRow = () => {
    const usedWalletIds = new Set(fundingRows.map((row) => String(row.wallet_id)));
    const nextWallet = eligibleWallets.find((wallet) =>
      Number(wallet.available_for_goals || 0) > 0 && !usedWalletIds.has(String(wallet.wallet_id))
    );
    if (!nextWallet) return;
    setFundingRows((rows) => [...rows, { wallet_id: String(nextWallet.wallet_id), amount: "" }]);
  };

  const removeFundingRow = (index) => {
    setFundingRows((rows) => rows.length <= 1 ? rows : rows.filter((_, rowIndex) => rowIndex !== index));
  };

  const openUseGoal = (goal) => {
    const firstSource = goal.funding_sources?.find((source) => Number(source.unreleased_amount || 0) > 0);
    const fallbackWallet = paymentWallets[0];
    const paymentWalletId = firstSource?.wallet_id || fallbackWallet?.wallet_id || "";
    const defaultAmount = formatAmountInput(String(goal.unreleased_amount || goal.target_amount || ""));
    const defaultPaymentRows = (goal.intent === "PLANNED_PURCHASE" || goal.intent === "PAY_OBLIGATION" || goal.intent === "RESERVE") && firstSource
      ? plannedPurchaseFundingRows(goal)
      : paymentWalletId ? [{ wallet_id: String(paymentWalletId), amount: defaultAmount }] : [];
    setUseDialog({ goal });
    setPurchaseStep(PURCHASE_STEPS.CONFIRM_PURCHASE);
    setUseForm({
      amount: defaultAmount,
      payment_allocations: defaultPaymentRows,
      category: defaultUseCategory(goal),
      subcategory_id: "",
      date: "",
      settlement_mode: "DIRECT",
      result_type: goal.intent === "PLANNED_PURCHASE" ? "EXPENSE_ONLY" : undefined,
      asset_title: "",
      adjust_target_to_purchase_amount: false,
      payment_after_purchase: "PAID_IN_FULL",
      payment_plan_total_price: "",
      payment_plan_item_name: goal.intent === "PLANNED_PURCHASE" ? goal.title : "",
      payment_plan_store_or_bank_name: "",
      payment_plan_months: "",
      payment_plan_frequency: "MONTHLY",
      create_next_payment_goal: true,
      next_payment_goal_title: goal.intent === "PLANNED_PURCHASE" ? `${goal.title} payment`.slice(0, 32) : "",
      next_payment_goal_target_date: "",
      note: "",
    });
    setUseError("");
  };

  const openPreparePayment = (goal) => {
    const firstSource = (goal.funding_sources || []).find((source) => Number(source.unreleased_amount || 0) > 0);
    const firstTarget = summary.wallets.find((wallet) =>
      firstSource &&
      String(wallet.wallet_id) !== String(firstSource.wallet_id) &&
      isOwnedPaymentWalletForCurrency(wallet, goal.currency)
    );
    setPrepareDialog({ goal });
    setMoveFundingForm({
      groups: firstSource ? [newMoveFundingGroup(firstSource.wallet_id, firstTarget?.wallet_id || "")] : [],
      date: todayISO,
    });
    setMoveFundingError("");
    setMoveFundingConfirmOpen(false);
  };

  const setPaymentRows = (rows) => {
    setUseForm((prev) => {
      return {
        ...prev,
        payment_allocations: rows,
        amount: selectedUseGoal?.intent === "PLANNED_PURCHASE" || selectedUseGoal?.intent === "PAY_OBLIGATION" || selectedUseGoal?.intent === "RESERVE"
          ? formatAmountInput(String(rows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0)))
          : prev.amount,
      };
    });
  };

  const setPlannedPurchaseSettlementMode = (mode) => {
    const defaultAmount = formatAmountInput(String(useAmount || selectedUseGoal?.target_amount || selectedUseGoal?.unreleased_amount || ""));
    const nextRows = mode === "DIRECT"
      ? plannedPurchaseFundingRows(selectedUseGoal)
      : paymentWallets.filter((w) => !goalFundingPaymentWalletIds.has(String(w.wallet_id))).slice(0, 1).map((w) => ({ wallet_id: String(w.wallet_id), amount: defaultAmount }));
    setUseForm((prev) => ({
      ...prev,
      settlement_mode: mode,
      payment_allocations: nextRows,
      amount: formatAmountInput(String(nextRows.reduce((sum, row) => sum + parseAmountInput(row.amount), 0))),
    }));
    setUseError("");
  };

  const updateMoveFundingGroup = (index, patch) => {
    setMoveFundingForm((prev) => ({
      ...prev,
      groups: (prev.groups || []).map((group, groupIndex) => (
        groupIndex === index ? { ...group, ...patch } : group
      )),
    }));
    setMoveFundingError("");
  };

  const updateMoveFundingDestination = (groupIndex, destinationIndex, patch) => {
    setMoveFundingForm((prev) => ({
      ...prev,
      groups: (prev.groups || []).map((group, index) => (
        index === groupIndex
          ? {
            ...group,
            destinations: (group.destinations || []).map((destination, itemIndex) => (
              itemIndex === destinationIndex ? { ...destination, ...patch } : destination
            )),
          }
          : group
      )),
    }));
    setMoveFundingError("");
  };

  const updateMoveFundingSource = (groupIndex, walletId) => {
    const nextTarget = moveFundingTargetOptions.find((wallet) =>
      String(wallet.wallet_id) !== String(walletId)
    );
    updateMoveFundingGroup(groupIndex, {
      source_wallet_id: walletId,
      destinations: [newMoveFundingDestination(walletId, nextTarget?.wallet_id || "")],
    });
  };

  const addMoveFundingGroup = () => {
    if (!selectedMoveGoal || moveFundingRows.length >= MAX_PREPARE_PAYMENT_MOVE_ROWS) return;
    const usedSourceIds = new Set(moveFundingGroups.map((group) => String(group.source_wallet_id || "")));
    const nextSource = moveFundingSourceOptions.find((source) =>
      Number(source.unreleased_amount || 0) > 0 && !usedSourceIds.has(String(source.wallet_id))
    );
    if (!nextSource) return;
    const nextTarget = moveFundingTargetOptions.find((wallet) =>
      nextSource && String(wallet.wallet_id) !== String(nextSource.wallet_id)
    );
    setMoveFundingForm((prev) => ({
      ...prev,
      groups: [...(prev.groups || []), newMoveFundingGroup(nextSource.wallet_id, nextTarget?.wallet_id || "")],
    }));
    setMoveFundingError("");
  };

  const removeMoveFundingGroup = (index) => {
    setMoveFundingForm((prev) => ({
      ...prev,
      groups: (prev.groups || []).length <= 1
        ? (prev.groups || [])
        : (prev.groups || []).filter((_, groupIndex) => groupIndex !== index),
    }));
    setMoveFundingError("");
  };

  const addMoveFundingDestination = (groupIndex) => {
    const group = moveFundingGroups[groupIndex];
    if (!group || (group.destinations || []).length >= MAX_PREPARE_PAYMENT_TARGET_WALLETS) return;
    if (moveFundingRows.length >= MAX_PREPARE_PAYMENT_MOVE_ROWS) return;
    const usedTargetIds = new Set((group.destinations || []).map((destination) => String(destination.target_wallet_id || "")));
    const nextTarget = moveFundingTargetOptions.find((wallet) =>
      String(wallet.wallet_id) !== String(group.source_wallet_id) &&
      !usedTargetIds.has(String(wallet.wallet_id))
    );
    if (!nextTarget) return;
    setMoveFundingForm((prev) => ({
      ...prev,
      groups: (prev.groups || []).map((item, index) => (
        index === groupIndex
          ? {
            ...item,
            destinations: [
              ...(item.destinations || []),
              newMoveFundingDestination(item.source_wallet_id, nextTarget.wallet_id),
            ],
          }
          : item
      )),
    }));
    setMoveFundingError("");
  };

  const removeMoveFundingDestination = (groupIndex, destinationIndex) => {
    setMoveFundingForm((prev) => ({
      ...prev,
      groups: (prev.groups || []).map((group, index) => (
        index === groupIndex
          ? {
            ...group,
            destinations: (group.destinations || []).length <= 1
              ? (group.destinations || [])
              : (group.destinations || []).filter((_, itemIndex) => itemIndex !== destinationIndex),
          }
          : group
      )),
    }));
    setMoveFundingError("");
  };

  const buildMoveGoalFundingPayload = () => {
    if (!selectedMoveGoal) return;
    if (!moveFundingRows.length) {
      setMoveFundingError("Add at least one movement row.");
      return null;
    }
    if (!moveFundingTargetsWithinLimit) {
      setMoveFundingError(`Prepare payment can use up to ${MAX_PREPARE_PAYMENT_TARGET_WALLETS} checkout wallets.`);
      return null;
    }
    if (!moveFundingPairsUnique) {
      setMoveFundingError("Each source-to-payment wallet pair can appear only once.");
      return null;
    }
    const sourceTotals = new Map();
    const moves = [];
    for (const row of moveFundingRows) {
      const amount = parseAmountInput(row.amount);
      const feeAmount = parseAmountInput(row.fee_amount);
      if (!row.source_wallet_id || !row.target_wallet_id) {
        setMoveFundingError("Choose both the current goal-money wallet and the checkout wallet in every row.");
        return null;
      }
      if (String(row.source_wallet_id) === String(row.target_wallet_id)) {
        setMoveFundingError("A row cannot move money into the same wallet.");
        return null;
      }
      if (!amount || amount <= 0) {
        setMoveFundingError("Enter an amount for every movement row.");
        return null;
      }
      const nextSourceTotal = (sourceTotals.get(String(row.source_wallet_id)) || 0) + amount;
      sourceTotals.set(String(row.source_wallet_id), nextSourceTotal);
      const source = moveFundingSourceOptions.find((item) => String(item.wallet_id) === String(row.source_wallet_id));
      if (nextSourceTotal > Number(source?.unreleased_amount || 0)) {
        setMoveFundingError("One source wallet is moving more than it has reserved for this goal.");
        return null;
      }
      if (row.has_fee && (!feeAmount || feeAmount <= 0)) {
        setMoveFundingError("Enter each transfer fee amount, or turn off Add fee for that row.");
        return null;
      }
      const move = {
        source_wallet_id: Number(row.source_wallet_id),
        target_wallet_id: Number(row.target_wallet_id),
        amount,
      };
      if (row.has_fee) {
        move.fee_amount = feeAmount;
        move.fee_wallet_id = Number(row.fee_wallet_id || row.source_wallet_id);
        move.fee_note = row.fee_note || "Payment preparation fee";
      }
      moves.push(move);
    }
    return {
      moves,
      date: moveFundingForm.date || todayISO,
      note: `Prepare ${selectedMoveGoal.title} goal payment`,
    };
  };

  const requestMoveGoalFundingConfirmation = () => {
    const payload = buildMoveGoalFundingPayload();
    if (!payload) return;
    setMoveFundingError("");
    setMoveFundingConfirmOpen(true);
  };

  const submitMoveGoalFunding = async () => {
    const payload = buildMoveGoalFundingPayload();
    if (!payload || !selectedMoveGoal) return;
    try {
      const result = await moveGoalFundingMutation.mutateAsync({
        goalId: selectedMoveGoal.id,
        payload,
      });
      const nextSource = (result.goal.funding_sources || []).find((source) => Number(source.unreleased_amount || 0) > 0);
      const nextTarget = summary.wallets.find((wallet) =>
        nextSource &&
        String(wallet.wallet_id) !== String(nextSource.wallet_id) &&
        isOwnedPaymentWalletForCurrency(wallet, result.goal.currency)
      );
      setMoveFundingForm({
        groups: nextSource ? [newMoveFundingGroup(nextSource.wallet_id, nextTarget?.wallet_id || "")] : [],
        date: todayISO,
      });
      setMoveFundingError("");
      setMoveFundingConfirmOpen(false);
      setPrepareDialog(null);
    } catch (error) {
      setMoveFundingError(localizeApiError(error?.message, t) || error?.message || "Request failed");
      setMoveFundingConfirmOpen(false);
    }
  };

  const updatePaymentRow = (index, patch) => {
    const rows = paymentRows.map((row, rowIndex) => (
      rowIndex === index ? { ...row, ...patch } : row
    ));
    setPaymentRows(rows);
  };

  const addPaymentRow = () => {
    const usedWalletIds = new Set(paymentRows.map((row) => String(row.wallet_id)));
    const nextWallet = paymentWalletOptions.find((wallet) => !usedWalletIds.has(String(wallet.wallet_id))) || paymentWalletOptions[0];
    if (!nextWallet) return;
    const remaining = Math.max(parseAmountInput(useForm.amount) - paymentTotal, 0);
    setPaymentRows([
      ...paymentRows,
      {
        wallet_id: String(nextWallet.wallet_id),
        amount: remaining > 0 ? formatAmountInput(String(remaining)) : "",
      },
    ]);
  };

  const removePaymentRow = (index) => {
    if (paymentRows.length <= 1) return;
    setPaymentRows(paymentRows.filter((_, rowIndex) => rowIndex !== index));
  };

  const resetCreateGoalFlow = () => {
    setCreateGoalStep(1);
    setGoalForm(createGoalDraftDefaults(""));
    setGoalFormError("");
  };

  const handleCreateGoalOpenChange = (open) => {
    setCreateGoalOpen(open);
    if (!open) resetCreateGoalFlow();
  };

  const selectCreateGoalIntent = (intent) => {
    setGoalForm(createGoalDraftDefaults(intent));
    setGoalFormError("");
  };

  const updateReserveType = (reserveType) => {
    const selected = RESERVE_GOAL_TYPES.find((item) => item.id === reserveType) || RESERVE_GOAL_TYPES[0];
    setGoalForm((prev) => ({
      ...prev,
      reserve_type: reserveType,
      title: prev.title && prev.title !== RESERVE_GOAL_TYPES.find((item) => item.id === prev.reserve_type)?.title
        ? prev.title
        : selected.title,
    }));
  };

  const createGoalTargetAmount = () => {
    if (goalForm.intent === "PAY_OBLIGATION") {
      if (goalForm.obligation_type === "PAYMENT_PLAN") {
        return Number(selectedDebt?.remaining_amount || 0);
      }
      if (goalForm.debt_saving_mode === "FULL") {
        return Number(selectedDebt?.remaining_amount || 0);
      }
      return parseAmountInput(goalForm.fixed_debt_amount);
    }
    return parseAmountInput(goalForm.target_amount);
  };

  const createGoalStepTitle = (() => {
    if (createGoalStep === 1) return "What are you saving for?";
    if (createGoalStep === 2) {
      if (goalForm.intent === "RESERVE") return "What kind of money are you setting aside?";
      if (goalForm.intent === "PLANNED_PURCHASE") return "What are you planning to buy?";
      if (goalForm.intent === "PAY_OBLIGATION") return "What kind of obligation is this?";
      return "Tell us more";
    }
    if (createGoalStep === 3) {
      if (goalForm.intent === "PAY_OBLIGATION") {
        return goalForm.obligation_type === "PAYMENT_PLAN"
          ? "Which payment plan are you saving for?"
          : "Which debt are you saving for?";
      }
      return "How much do you want to save?";
    }
    if (createGoalStep === 4) return goalForm.intent === "PAY_OBLIGATION" ? "How should this goal work?" : "When do you want this ready?";
    return "Review before creating";
  })();

  const validateCreateGoalStep = (step = createGoalStep) => {
    const title = goalForm.title.trim();
    const targetAmount = createGoalTargetAmount();
    if (step === 1 && !goalForm.intent) return "Choose what you are saving for.";
    if (step === 2) {
      if (goalForm.intent === "RESERVE" && !goalForm.reserve_type) return "Choose what kind of money you want to set aside.";
      if (goalForm.intent === "PAY_OBLIGATION") {
        if (!goalForm.obligation_type) return "Choose whether this is a payment plan or a debt.";
      }
      if (goalForm.intent !== "PAY_OBLIGATION") {
        if (!title) return "Give this goal a name.";
        if (title.length < 3 || title.length > 32) return "Use a name between 3 and 32 characters.";
      }
    }
    if (step === 3) {
      if (goalForm.intent === "PAY_OBLIGATION") {
        if (!goalForm.linked_debt_id) return goalForm.obligation_type === "PAYMENT_PLAN"
          ? "Choose the payment plan you want to save for."
          : "Choose the debt you want to save for.";
        if (selectedDebtAlreadyHasGoal) return "This obligation already has an open savings goal.";
        if (!title) return "Give this goal a name.";
        if (title.length < 3 || title.length > 32) return "Use a name between 3 and 32 characters.";
        return "";
      }
      if (targetAmount <= 0) return "Enter the amount you want to save.";
    }
    if (step === 4) {
      if (goalForm.intent === "PAY_OBLIGATION") {
        const remainingDebt = Number(selectedDebt?.remaining_amount || 0);
        if (!remainingDebt) return "Choose a debt with money still left to pay.";
        if (goalForm.obligation_type !== "PAYMENT_PLAN") {
          if (targetAmount <= 0) return "Enter the amount you want to save.";
          if (targetAmount > remainingDebt) return "This is higher than what is left on that debt.";
        }
      }
      if (goalForm.target_date && goalForm.target_date < "2020-01-01") return "Choose a later date.";
    }
    return "";
  };

  const goNextCreateGoalStep = () => {
    const message = validateCreateGoalStep();
    if (message) {
      setGoalFormError(message);
      return;
    }
    setGoalFormError("");
    setCreateGoalStep((current) => Math.min(5, current + 1));
  };

  const goBackCreateGoalStep = () => {
    setGoalFormError("");
    setCreateGoalStep((current) => Math.max(1, current - 1));
  };

  const submitGoal = async () => {
    for (let step = 1; step <= 4; step += 1) {
      const message = validateCreateGoalStep(step);
      if (message) {
        setCreateGoalStep(step);
        setGoalFormError(message);
        return;
      }
    }

    const targetAmount = createGoalTargetAmount();
    const parsed = goalCreateFormSchema.safeParse({
      title: goalForm.title,
      target_amount: targetAmount,
      target_date: goalForm.target_date || null,
      intent: goalForm.intent,
    });
    if (!parsed.success) {
      setGoalFormError(t(parsed.error.issues[0]?.message || "savings.validation.amount.invalid"));
      return;
    }

    const payload = buildGoalCreatePayload(parsed.data, { linkedDebtId: goalForm.linked_debt_id });

    try {
      setGoalFormError("");
      await createGoalMutation.mutateAsync(payload);
      handleCreateGoalOpenChange(false);
    } catch (error) {
      setGoalFormError(localizeApiError(error?.message, t) || error?.message || "Could not create this goal.");
    }
  };

  const submitFunding = async () => {
    if (!selectedGoal) return;
    if (fundingMode === "allocate") {
      const parsed = goalAllocationsFormSchema.safeParse({
        allocations: fundingRows.map((row) => ({
          wallet_id: row.wallet_id,
          amount: parseAmountInput(row.amount),
        })),
      });
      if (!parsed.success) {
        setFundingError(t(parsed.error.issues[0]?.message || "savings.validation.amount.invalid"));
        return;
      }
      const total = parsed.data.allocations.reduce((sum, item) => sum + item.amount, 0);
      if (total > goalRemainingToFund) {
        setFundingError("Total amount exceeds what this goal still needs.");
        return;
      }
      const exceedsWallet = parsed.data.allocations.some((item) => {
        const wallet = eligibleWallets.find((candidate) => Number(candidate.wallet_id) === Number(item.wallet_id));
        return item.amount > Number(wallet?.available_for_goals || 0);
      });
      if (exceedsWallet) {
        setFundingError("One wallet row exceeds that wallet's free-to-reserve amount.");
        return;
      }
      try {
        await allocateMutation.mutateAsync({ goalId: selectedGoal.id, payload: parsed.data });
        setFundingDialog(null);
      } catch (error) {
        setFundingError(localizeApiError(error?.message, t) || error?.message || "Request failed");
      }
      return;
    }
    const parsed = goalActionAmountSchema.safeParse({
      amount: parseAmountInput(fundingAmount),
      wallet_id: fundingWalletId,
    });
    if (!parsed.success) {
      setFundingError(t(parsed.error.issues[0]?.message || "savings.validation.amount.invalid"));
      return;
    }
    if (parsed.data.amount > maxFundingAmount) {
      setFundingError(
        fundingMode === "allocate"
          ? "Amount exceeds what this goal still needs or what this wallet can reserve."
          : "Amount is higher than the money still reserved in this wallet."
      );
      return;
    }
    try {
      const variables = { goalId: selectedGoal.id, payload: parsed.data };
      await returnMutation.mutateAsync(variables);
      setFundingDialog(null);
    } catch (error) {
      setFundingError(localizeApiError(error?.message, t) || error?.message || "Request failed");
    }
  };

  const submitUseGoal = async () => {
    if (!selectedUseGoal) return;
    if (!paymentWalletRowsUnique) {
      setUseError("Each payment wallet can appear only once.");
      return;
    }
    if (!paymentWalletRowsWithinLimit) {
      setUseError(`Planned purchases can use up to ${MAX_PLANNED_PURCHASE_PAYMENT_WALLETS} payment wallets.`);
      return;
    }
    if (selectedUseGoal.intent === "PAY_OBLIGATION") {
      if (paymentTotal <= 0) {
        setUseError("Add at least one payment wallet amount before making this payment.");
        return;
      }
      if (!paymentWalletsAllFundingSources) {
        setUseError("Debt payments from a goal must use wallets that have money reserved for this goal.");
        return;
      }
      if (!paymentRowsWithinFundingAmounts) {
        setUseError("One payment amount is higher than the goal money reserved in that wallet.");
        return;
      }
      const parsed = goalDebtPaymentFormSchema.safeParse({
        amount: paymentTotal,
        payment_allocations: paymentRows.map((row) => ({
          wallet_id: row.wallet_id,
          amount: parseAmountInput(row.amount),
        })),
        date: useForm.date || null,
        note: useForm.note,
      });
      if (!parsed.success) {
        setUseError(t(parsed.error.issues[0]?.message || "savings.validation.amount.invalid"));
        return;
      }
      const payload = {
        amount: parsed.data.amount,
        payment_allocations: parsed.data.payment_allocations,
      };
      if (parsed.data.date) payload.date = parsed.data.date;
      if (parsed.data.note) payload.note = parsed.data.note;
      try {
        await recordDebtPaymentMutation.mutateAsync({ goalId: selectedUseGoal.id, payload });
        setUseDialog(null);
      } catch (error) {
        setUseError(localizeApiError(error?.message, t) || error?.message || "Request failed");
      }
      return;
    }
    if (selectedUseGoal.intent === "RESERVE") {
      if (paymentTotal <= 0) {
        setUseError("Add at least one prepared reserve wallet amount before recording this payment.");
        return;
      }
      if (!paymentWalletsAllFundingSources) {
        setUseError("Reserve use must come from wallets that currently hold this reserve. Prepare payment first if another wallet will pay.");
        return;
      }
      if (!paymentRowsWithinFundingAmounts) {
        setUseError("One payment amount is higher than the reserve money in that wallet.");
        return;
      }
    }
    if (selectedUseGoal.intent === "PLANNED_PURCHASE" && useForm.settlement_mode === "DIRECT" && !paymentWalletsAllFundingSources) {
      setUseError("Goal-funded purchase means every payment wallet must be a wallet that reserved money for this goal.");
      return;
    }
    if (selectedUseGoal.intent === "PLANNED_PURCHASE" && useForm.settlement_mode === "GOAL_BACKED_OFF_WALLET_PAYMENT" && !paymentWalletsAllNonFundingSources) {
      setUseError("Off-wallet purchase cannot use a wallet that was prepared for this goal.");
      return;
    }
    if (selectedUseGoal.intent === "PLANNED_PURCHASE" && useForm.settlement_mode === "DIRECT" && !paymentRowsWithinFundingAmounts) {
      setUseError("One payment wallet amount is larger than the goal money reserved in that wallet.");
      return;
    }
    const parsed = goalUseFormSchema.safeParse({
      ...useForm,
      amount: selectedUseGoal.intent === "PLANNED_PURCHASE" || selectedUseGoal.intent === "RESERVE" ? paymentTotal : parseAmountInput(useForm.amount),
      payment_allocations: paymentRows.map((row) => ({
        wallet_id: row.wallet_id,
        amount: parseAmountInput(row.amount),
      })),
    });
    if (!parsed.success) {
      setUseError(t(parsed.error.issues[0]?.message || "savings.validation.amount.invalid"));
      return;
    }

    const payload = {
      amount: parsed.data.amount,
      payment_allocations: parsed.data.payment_allocations,
      category: parsed.data.category,
      settlement_mode: parsed.data.settlement_mode || "DIRECT",
    };
    if (parsed.data.subcategory_id) payload.subcategory_id = parsed.data.subcategory_id;
    if (parsed.data.date) payload.date = parsed.data.date;

    try {
      if (selectedUseGoal.intent === "RESERVE") {
        await useReserveMutation.mutateAsync({ goalId: selectedUseGoal.id, payload });
      } else if (selectedUseGoal.intent === "PLANNED_PURCHASE") {
        if (paymentTotal <= 0) {
          setUseError("Add at least one payment wallet amount before recording this purchase.");
          return;
        }
        if (parsed.data.amount !== Number(selectedUseGoal.target_amount || 0) && !parsed.data.adjust_target_to_purchase_amount) {
          setUseError("Confirm the target update before completing this planned purchase.");
          return;
        }
        if (payment_planBridgeSelected && !canContinuePaymentPlanStep) {
          setUseError("For a payment plan, the full price must be higher than today's payment and the number of payments must be valid.");
          return;
        }
        payload.result_type = parsed.data.result_type || "EXPENSE_ONLY";
        payload.adjust_target_to_purchase_amount = Boolean(parsed.data.adjust_target_to_purchase_amount);
        if (payload.result_type === "ASSET_PURCHASE" && parsed.data.asset_title?.trim()) {
          payload.asset_title = parsed.data.asset_title.trim();
        }
        if (payment_planBridgeSelected) {
          payload.payment_plan = {
            total_price: payment_planTotalPrice,
            item_name: (useForm.payment_plan_item_name || selectedUseGoal.title || "").trim(),
            months: payment_planMonths,
            frequency: useForm.payment_plan_frequency || "MONTHLY",
            create_next_payment_goal: Boolean(useForm.create_next_payment_goal),
          };
          if (useForm.payment_plan_store_or_bank_name?.trim()) {
            payload.payment_plan.store_or_bank_name = useForm.payment_plan_store_or_bank_name.trim();
          }
          if (useForm.next_payment_goal_title?.trim()) {
            payload.payment_plan.next_goal_title = useForm.next_payment_goal_title.trim();
          }
          if (useForm.next_payment_goal_target_date) {
            payload.payment_plan.next_goal_target_date = useForm.next_payment_goal_target_date;
          }
        }
        await recordPurchaseMutation.mutateAsync({ goalId: selectedUseGoal.id, payload });
      }
      setUseDialog(null);
    } catch (error) {
      setUseError(localizeApiError(error?.message, t) || error?.message || "Request failed");
    }
  };

  const handleIntentAction = (goal) => {
    if (goal.intent === "RESERVE" || goal.intent === "PLANNED_PURCHASE" || goal.intent === "PAY_OBLIGATION") {
      openUseGoal(goal);
      return;
    }
  };

  const canContinuePaymentStep = paymentRows.length > 0 &&
    paymentTotal > 0 &&
    paymentWalletRowsUnique &&
    paymentWalletRowsWithinLimit &&
    (!isUseFromFundingSources || (paymentWalletsAllFundingSources && paymentRowsWithinFundingAmounts)) &&
    (!isPlannedPurchase || useForm.settlement_mode !== "GOAL_BACKED_OFF_WALLET_PAYMENT" || paymentWalletsAllNonFundingSources);
  const canContinueClassificationStep = !purchaseAmountDiffersFromTarget || Boolean(useForm.adjust_target_to_purchase_amount);
  const canContinuePaymentPlanStep = !payment_planBridgeSelected || (
    payment_planTotalPrice > paymentTotal &&
    payment_planMonths > 0 &&
    Boolean(useForm.payment_plan_frequency)
  );

  const renderCreateGoalStep = () => {
    if (createGoalStep === 1) {
      return (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {GOAL_CREATE_CHOICE_COPY.map((choice) => {
            const Icon = GOAL_CREATE_ICONS[choice.intent] || Target;
            const selected = goalForm.intent === choice.intent;
            return (
              <button
                key={choice.intent}
                type="button"
                onClick={() => selectCreateGoalIntent(choice.intent)}
                className={cn(
                  "rounded-lg border p-4 text-left transition-colors hover:border-primary/50",
                  selected ? "border-primary bg-primary/10" : "border-border bg-card"
                )}
              >
                <Icon className="h-5 w-5 text-primary" />
                <p className="mt-3 font-semibold">{choice.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{choice.description}</p>
              </button>
            );
          })}
        </div>
      );
    }

    if (createGoalStep === 2 && goalForm.intent === "RESERVE") {
      return (
        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-2">
            {RESERVE_GOAL_TYPES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => updateReserveType(item.id)}
                className={cn(
                  "rounded-lg border p-4 text-left transition-colors hover:border-primary/50",
                  goalForm.reserve_type === item.id ? "border-primary bg-primary/10" : "border-border bg-card"
                )}
              >
                <p className="font-semibold">{item.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
              </button>
            ))}
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">What should we call it?</label>
            <Input
              value={goalForm.title}
              onChange={(event) => setGoalForm((prev) => ({ ...prev, title: event.target.value }))}
              placeholder="Emergency fund"
              className="h-11 rounded-md text-base"
            />
          </div>
        </div>
      );
    }

    if (createGoalStep === 2 && goalForm.intent === "PLANNED_PURCHASE") {
      return (
        <div className="space-y-2">
          <label className="text-sm font-medium">What are you planning to buy?</label>
          <Input
            value={goalForm.title}
            onChange={(event) => setGoalForm((prev) => ({ ...prev, title: event.target.value }))}
            placeholder="Laptop, phone, furniture..."
            className="h-11 rounded-md text-base"
          />
          <p className="text-xs text-muted-foreground">This goal is for one planned purchase. You will record the real purchase later.</p>
        </div>
      );
    }

    if (createGoalStep === 2 && goalForm.intent === "PAY_OBLIGATION") {
      return (
        <div className="grid gap-3 md:grid-cols-2">
          {OBLIGATION_CREATE_CHOICES.map((choice) => {
            const Icon = choice.icon;
            const selected = goalForm.obligation_type === choice.type;
            return (
              <button
                key={choice.type}
                type="button"
                onClick={() => {
                  setGoalForm((prev) => ({
                    ...prev,
                    obligation_type: choice.type,
                    linked_debt_id: "",
                    title: "",
                    debt_saving_mode: "FULL",
                    fixed_debt_amount: "",
                  }));
                  setGoalFormError("");
                }}
                className={cn(
                  "rounded-lg border p-4 text-left transition-colors hover:border-primary/50",
                  selected ? "border-primary bg-primary/10" : "border-border bg-card"
                )}
              >
                <Icon className="h-5 w-5 text-primary" />
                <p className="mt-5 text-lg font-semibold">{choice.title}</p>
                <p className="mt-2 text-sm text-muted-foreground">{choice.description}</p>
              </button>
            );
          })}
        </div>
      );
    }

    if (createGoalStep === 3) {
      if (goalForm.intent === "PAY_OBLIGATION") {
        const options = goalForm.obligation_type === "PAYMENT_PLAN" ? paymentPlanGoalOptions : standardDebtGoalOptions;
        const placeholder = goalForm.obligation_type === "PAYMENT_PLAN" ? "Choose a payment plan" : "Choose a debt";
        return (
          <div className="space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {goalForm.obligation_type === "PAYMENT_PLAN" ? "Which payment plan are you saving for?" : "Which debt are you saving for?"}
              </label>
              <Select
                value={goalForm.linked_debt_id || undefined}
                onValueChange={(value) => {
                  const debt = options.find((item) => String(item.id) === String(value));
                  setGoalForm((prev) => ({
                    ...prev,
                    linked_debt_id: value,
                    title: prev.title || (debt ? `Save for ${debt.counterparty_name}` : ""),
                  }));
                }}
              >
                <SelectTrigger className="h-11 rounded-md text-base">
                  <SelectValue placeholder={debtGoalOptionsQuery.isLoading ? "Loading..." : placeholder} />
                </SelectTrigger>
                <SelectContent>
                  {options.map((debt) => {
                    const blocked = openDebtGoalIds.has(Number(debt.id));
                    return (
                      <SelectItem key={debt.id} value={String(debt.id)} disabled={blocked}>
                        {debt.counterparty_name} / {money(debt.remaining_amount)} left{blocked ? " / already has a savings goal" : ""}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
              {!debtGoalOptionsQuery.isLoading && !options.length ? (
                <p className="text-sm text-muted-foreground">
                  {goalForm.obligation_type === "PAYMENT_PLAN"
                    ? "No open payment plans are ready for this kind of goal."
                    : "No open debts are ready for this kind of goal."}
                </p>
              ) : null}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">What should we call it?</label>
              <Input
                value={goalForm.title}
                onChange={(event) => setGoalForm((prev) => ({ ...prev, title: event.target.value }))}
                placeholder={goalForm.obligation_type === "PAYMENT_PLAN" ? "Save for phone payment" : "Save for my friend"}
                className="h-11 rounded-md text-base"
              />
            </div>
          </div>
        );
      }

      return (
        <div className="space-y-2">
          <label className="text-sm font-medium">How much do you want to save?</label>
          <Input
            inputMode="numeric"
            value={goalForm.target_amount}
            onChange={(event) => setGoalForm((prev) => ({ ...prev, target_amount: formatAmountInput(event.target.value) }))}
            placeholder="0"
            className="h-11 rounded-md text-base"
          />
          {goalForm.intent === "RESERVE" ? (
            <p className="text-xs text-muted-foreground">Reaching this amount means the money is fully set aside. The goal can stay open.</p>
          ) : (
            <p className="text-xs text-muted-foreground">Use the amount you expect to need for this purchase.</p>
          )}
        </div>
      );
    }

    if (createGoalStep === 4 && goalForm.intent === "PAY_OBLIGATION") {
      const remainingDebt = Number(selectedDebt?.remaining_amount || 0);

      if (goalForm.obligation_type === "PAYMENT_PLAN") {
        return (
          <div className="space-y-4">
            <div className="rounded-lg border border-primary/50 bg-primary/10 p-4">
              <p className="font-semibold text-primary">Next Payment Protector</p>
              <p className="mt-1 text-sm text-muted-foreground">
                This goal protects only the next unpaid scheduled payment. If you pay ahead outside this goal, Sarflog moves the target to the next remaining payment.
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">When do you want this ready?</label>
              <Input
                type="date"
                value={goalForm.target_date || ""}
                onChange={(event) => setGoalForm((prev) => ({ ...prev, target_date: event.target.value }))}
                className="h-11 rounded-md text-base"
              />
              <p className="text-xs text-muted-foreground">Optional. The next payment amount is set automatically.</p>
            </div>
          </div>
        );
      }

      return (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            {[
              {
                value: "FULL",
                title: "Save everything left",
                description: selectedDebt ? `Set this goal to ${money(remainingDebt)}.` : "Use the full amount left on the selected debt.",
              },
              {
                value: "FIXED",
                title: "Save a smaller amount",
                description: "Use this when you want to save for one partial payment.",
              },
            ].map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setGoalForm((prev) => ({ ...prev, debt_saving_mode: item.value }))}
                className={cn(
                  "rounded-lg border p-4 text-left transition-colors hover:border-primary/50",
                  goalForm.debt_saving_mode === item.value ? "border-primary bg-primary/10" : "border-border bg-card"
                )}
              >
                <p className="font-semibold">{item.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
              </button>
            ))}
          </div>
          {goalForm.debt_saving_mode === "FIXED" ? (
            <div className="space-y-2">
              <label className="text-sm font-medium">How much do you want to save this time?</label>
              <Input
                inputMode="numeric"
                value={goalForm.fixed_debt_amount}
                onChange={(event) => setGoalForm((prev) => ({ ...prev, fixed_debt_amount: formatAmountInput(event.target.value) }))}
                placeholder="0"
                className="h-11 rounded-md text-base"
              />
              <p className="text-xs text-muted-foreground">Keep it at or below {money(remainingDebt)}.</p>
            </div>
          ) : null}
          <div className="space-y-2">
            <label className="text-sm font-medium">When do you want this ready?</label>
            <Input
              type="date"
              value={goalForm.target_date || ""}
              onChange={(event) => setGoalForm((prev) => ({ ...prev, target_date: event.target.value }))}
              className="h-11 rounded-md text-base"
            />
            <p className="text-xs text-muted-foreground">Optional.</p>
          </div>
        </div>
      );
    }

    if (createGoalStep === 4 && goalForm.intent === "RESERVE") {
      return (
        <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
          <p className="font-semibold text-foreground">No deadline needed</p>
          <p className="mt-1">Reserve funds stay open as long as you want. You decide when to use the money.</p>
        </div>
      );
    }

    if (createGoalStep === 4) {
      return (
        <div className="space-y-2">
          <label className="text-sm font-medium">When do you want this ready?</label>
          <Input
            type="date"
            value={goalForm.target_date || ""}
            onChange={(event) => setGoalForm((prev) => ({ ...prev, target_date: event.target.value }))}
            className="h-11 rounded-md text-base"
          />
          <Button
            type="button"
            variant="ghost"
            className="rounded-md px-0 text-muted-foreground hover:text-foreground"
            onClick={() => setGoalForm((prev) => ({ ...prev, target_date: "" }))}
          >
            No deadline
          </Button>
        </div>
      );
    }

    const targetAmount = createGoalTargetAmount();
    const linkedDebtName = selectedDebt?.counterparty_name;
    const isSelectedPaymentPlan = goalForm.intent === "PAY_OBLIGATION" && goalForm.obligation_type === "PAYMENT_PLAN";
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-primary/20 bg-primary/10 p-4">
          <p className="text-lg font-semibold">{goalForm.title || "New goal"}</p>
          <p className="mt-1 text-sm text-muted-foreground">{GOAL_INTENT_LABELS[goalForm.intent]}</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Amount to save</p>
              <Target className="h-4 w-4 text-primary" />
            </div>
            <p className="mt-3 text-2xl font-semibold tabular-nums">
              {isSelectedPaymentPlan ? "Next payment" : `${formatUzs(targetAmount)} UZS`}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {isSelectedPaymentPlan
                ? `Sarflog will lock this to the next unpaid payment for ${linkedDebtName}.`
                : goalForm.intent === "PAY_OBLIGATION" && linkedDebtName
                  ? `For ${linkedDebtName}`
                  : "Funding stays separate"}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Ready by</p>
              <CalendarDays className="h-4 w-4 text-primary" />
            </div>
            <p className="mt-3 text-2xl font-semibold">{goalForm.target_date ? formatDisplayDate(goalForm.target_date, appLang) : "No deadline"}</p>
            <p className="mt-1 text-xs text-muted-foreground">You can change this later</p>
          </div>
        </div>
        <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
          <p className="font-semibold text-foreground">What Sarflog will do</p>
          <ul className="mt-2 space-y-1">
            <li>Create the goal.</li>
            {goalForm.intent === "PAY_OBLIGATION" ? <li>Connect it to the selected obligation.</li> : null}
            <li>Leave wallet money untouched until you reserve money yourself.</li>
          </ul>
        </div>
      </div>
    );
  };

  const renderPaymentWalletRows = ({ showFinalPrice = false, totalLabel = "" } = {}) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-medium">Payment wallets</label>
        <Button type="button" size="sm" variant="outline" onClick={addPaymentRow} disabled={!paymentWalletOptions.length || paymentRows.length >= paymentWalletOptions.length || paymentRows.length >= paymentWalletRowLimit}>
          <Plus className="mr-2 h-4 w-4" /> Add
        </Button>
      </div>
      <div className="space-y-2">
        {paymentRows.map((row, index) => (
          <div key={index} className="grid gap-2 rounded-md border border-border bg-muted/20 p-2 md:grid-cols-[1fr_160px_auto]">
            <Select
              value={String(row.wallet_id || "")}
              onValueChange={(value) => updatePaymentRow(index, { wallet_id: value })}
            >
              <SelectTrigger><SelectValue placeholder="Choose wallet" /></SelectTrigger>
              <SelectContent>
                {paymentWalletOptions.map((wallet) => {
                  const source = (selectedUseGoal?.funding_sources || []).find((item) => item.wallet_id === wallet.wallet_id);
                  return (
                    <SelectItem key={wallet.wallet_id} value={String(wallet.wallet_id)}>
                      {wallet.wallet_name} / {money(wallet.balance)}
                      {source ? ` / reserved ${money(source.unreleased_amount)}` : ""}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            <Input
              inputMode="numeric"
              value={row.amount || ""}
              onChange={(event) => updatePaymentRow(index, { amount: formatAmountInput(event.target.value) })}
            />
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => removePaymentRow(index)}
              disabled={paymentRows.length <= 1}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>
      <p className={cn("text-xs", paymentTotal > 0 ? "text-muted-foreground" : "text-destructive")}>
        {totalLabel || (showFinalPrice ? "Final price" : "Payment split total")}: {money(paymentTotal)}
      </p>
      {!paymentWalletRowsUnique ? (
        <p className="text-xs text-destructive">Each payment wallet can appear only once.</p>
      ) : null}
      {!paymentWalletRowsWithinLimit ? (
        <p className="text-xs text-destructive">
          {selectedUseGoal?.intent === "PLANNED_PURCHASE"
            ? `Planned purchase checkout can use up to ${MAX_PLANNED_PURCHASE_PAYMENT_WALLETS} payment wallets.`
            : "Add each payment wallet only once."}
        </p>
      ) : null}
      {isUseFromFundingSources && !paymentRowsWithinFundingAmounts ? (
        <p className="text-xs text-destructive">
          One row is higher than the goal money still reserved in that wallet.
        </p>
      ) : null}
      {isPlannedPurchase && useForm.settlement_mode === "GOAL_BACKED_OFF_WALLET_PAYMENT" && !paymentWalletsAllNonFundingSources ? (
        <p className="text-xs text-destructive">
          Off-wallet mode cannot use a wallet that reserved this goal. Choose goal-funded mode if a reserved wallet paid.
        </p>
      ) : null}
      {isPlannedPurchase && useForm.settlement_mode === "DIRECT" ? (
        <p className="text-xs text-muted-foreground">
          Goal-funded purchases only show prepared owned-money wallets for this goal. Credit cards and unplanned wallets are excluded.
        </p>
      ) : null}
      {isDebtGoalPayment ? (
        <p className="text-xs text-muted-foreground">
          Debt payments only show wallets with money reserved for this goal. Prepare payment first if the real payment will come from another wallet.
        </p>
      ) : null}
      {isReserveUse ? (
        <p className="text-xs text-muted-foreground">
          Reserve use only shows wallets currently holding this reserve. Prepare payment first if a different wallet will pay.
        </p>
      ) : null}
      {isPlannedPurchase && useForm.settlement_mode === "GOAL_BACKED_OFF_WALLET_PAYMENT" ? (
        <p className="text-xs text-muted-foreground">
          Off-wallet purchases hide the prepared goal wallets. Sarflog will complete the goal and consume the reserved money.
        </p>
      ) : null}
      {isPlannedPurchase && useForm.settlement_mode === "GOAL_BACKED_OFF_WALLET_PAYMENT" && !paymentWalletOptions.length ? (
        <p className="text-xs text-destructive">
          No different payment wallet is available. Choose goal-funded mode, or add another wallet first.
        </p>
      ) : null}
    </div>
  );

  const renderDebtPaymentFlow = () => (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
        <p className="font-medium">Record the real debt payment</p>
        <p className="mt-1 text-muted-foreground">
          Choose the wallet money that actually paid the person or company. Sarflog will use the reserved goal money and reduce the debt.
        </p>
        {selectedUseGoal?.payment_plan_target ? (
          <p className="mt-2 text-xs text-muted-foreground">
            This goal is currently saving for payment {selectedUseGoal.payment_plan_target.payment_number} of {selectedUseGoal.payment_plan_target.total_payments}
            {selectedUseGoal.payment_plan_target.due_date ? `, due ${formatDisplayDate(selectedUseGoal.payment_plan_target.due_date, appLang)}` : ""}.
          </p>
        ) : null}
      </div>
      {renderPaymentWalletRows({ totalLabel: "Amount to pay" })}
      <div className="grid gap-3 md:grid-cols-2">
        <div className="space-y-2">
          <label className="text-sm font-medium">Payment date</label>
          <Input
            type="date"
            value={useForm.date || ""}
            max={todayISO}
            onChange={(event) => setUseForm((prev) => ({ ...prev, date: event.target.value }))}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Note</label>
          <Input
            value={useForm.note || ""}
            maxLength={200}
            onChange={(event) => setUseForm((prev) => ({ ...prev, note: event.target.value }))}
            placeholder="Optional"
          />
        </div>
      </div>
      <div className="rounded-md border border-border bg-background/50 p-3 text-sm">
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Still reserved before payment</span>
          <span className="font-medium">{money(selectedUseGoal?.unreleased_amount)}</span>
        </div>
        <div className="mt-1 flex justify-between gap-3">
          <span className="text-muted-foreground">This payment</span>
          <span className="font-medium">{money(paymentTotal)}</span>
        </div>
        <div className="mt-1 flex justify-between gap-3">
          <span className="text-muted-foreground">Still reserved after payment</span>
          <span className="font-medium">{money(Math.max(Number(selectedUseGoal?.unreleased_amount || 0) - paymentTotal, 0))}</span>
        </div>
      </div>
      {!paymentWalletOptions.length ? (
        <p className="text-sm text-destructive">
          No prepared payment wallet is ready. Reserve money first, or use Prepare payment if the money is in a different wallet.
        </p>
      ) : null}
    </div>
  );

  const renderReserveUseFlow = () => (
    <div className="space-y-4">
      <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
        <p className="font-medium">Record the real reserve payment</p>
        <p className="mt-1 text-muted-foreground">
          Choose the prepared reserve wallet that actually paid. If another wallet needs to pay, prepare the payment before recording this.
        </p>
      </div>
      {renderPaymentWalletRows({ totalLabel: "Amount used from reserve" })}
      <div className="grid gap-3 md:grid-cols-2">
        <div className="space-y-2">
          <label className="text-sm font-medium">Payment date</label>
          <Input
            type="date"
            value={useForm.date || ""}
            max={todayISO}
            onChange={(event) => setUseForm((prev) => ({ ...prev, date: event.target.value, subcategory_id: "" }))}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Category</label>
          <Select value={useForm.category} onValueChange={(value) => setUseForm((prev) => ({ ...prev, category: value, subcategory_id: "" }))}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {CATEGORIES.map((category) => (
                <SelectItem key={category} value={category}>{category}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-2">
        <label className="text-sm font-medium">Subcategory</label>
        <Select
          value={useForm.subcategory_id || "__none__"}
          onValueChange={(value) => setUseForm((prev) => ({ ...prev, subcategory_id: value === "__none__" ? "" : value }))}
          disabled={!selectedUseBudget}
        >
          <SelectTrigger><SelectValue placeholder="Subcategory" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">None</SelectItem>
            {useSubcategories.map((subcategory) => (
              <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                {subcategory.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="rounded-md border border-border bg-background/50 p-3 text-sm">
        <div className="flex justify-between gap-3">
          <span className="text-muted-foreground">Still reserved before payment</span>
          <span className="font-medium">{money(selectedUseGoal?.unreleased_amount)}</span>
        </div>
        <div className="mt-1 flex justify-between gap-3">
          <span className="text-muted-foreground">This payment</span>
          <span className="font-medium">{money(paymentTotal)}</span>
        </div>
        <div className="mt-1 flex justify-between gap-3">
          <span className="text-muted-foreground">Still reserved after payment</span>
          <span className="font-medium">{money(Math.max(Number(selectedUseGoal?.unreleased_amount || 0) - paymentTotal, 0))}</span>
        </div>
      </div>
      {!paymentWalletOptions.length ? (
        <p className="text-sm text-destructive">
          No prepared reserve wallet is ready. Reserve money first, or use Prepare payment if the money is in a different wallet.
        </p>
      ) : null}
    </div>
  );

  const renderGoalActivity = () => {
    if (activityQuery.isLoading) {
      return (
        <div className="flex min-h-40 items-center justify-center">
          <LoadingSpinner />
        </div>
      );
    }
    if (activityQuery.isError) {
      return <p className="text-sm text-destructive">Could not load goal activity.</p>;
    }

    const items = activityQuery.data?.items || [];
    if (!items.length) {
      return <p className="text-sm text-muted-foreground">No activity yet.</p>;
    }

    return (
      <div className="relative space-y-4">
        <div className="absolute bottom-3 left-[10px] top-3 w-px bg-border" />
        {items.map((item) => {
          const prefix = activityAmountPrefix(item.type);
          const isPositive = prefix === "+";
          const isNegative = prefix === "-";
          const hasBusinessDate = Boolean(item.linked_event_id) || item.type === "RELEASED_TO_PROJECT";
          return (
            <div key={item.id} className="relative grid grid-cols-[22px_minmax(0,1fr)] gap-3">
              <span className={cn(
                "relative z-10 mt-5 h-3 w-3 justify-self-center rounded-full border bg-background",
                item.type === "GOAL_CREATED"
                  ? "border-muted-foreground"
                  : isPositive
                    ? "border-primary bg-primary"
                    : isNegative
                      ? "border-amber-300 bg-amber-300"
                      : "border-foreground bg-foreground"
              )} />
              <div className="rounded-md border border-border bg-card p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="font-medium">{item.title}</div>
                    {item.description ? (
                      <div className="mt-1 text-sm text-muted-foreground">{item.description}</div>
                    ) : null}
                    <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                      {hasBusinessDate ? (
                        <span>
                          <span className="font-medium text-foreground/70">Date:</span>{" "}
                          {formatDisplayDate(item.date, appLang)}
                        </span>
                      ) : null}
                      <span>
                        <span className="font-medium text-foreground/70">Recorded:</span>{" "}
                        {formatDisplayDateTime(item.created_at, appLang)}
                      </span>
                    </div>
                  </div>
                  {Number(item.amount || 0) > 0 ? (
                    <div className={cn(
                      "text-left font-semibold tabular-nums sm:text-right",
                      isPositive ? "text-primary" : isNegative ? "text-amber-300" : "text-foreground"
                    )}>
                      {prefix}{money(item.amount)}
                    </div>
                  ) : null}
                </div>
                {item.wallets?.length ? (
                  <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    {item.wallets.map((wallet, index) => (
                      <div key={`${item.id}-${wallet.role}-${wallet.wallet_id}-${index}`} className="flex justify-between gap-3 rounded-md bg-muted/25 px-3 py-2">
                        <span className="min-w-0 truncate text-muted-foreground">
                          {activityRoleLabel(wallet.role)}: {wallet.wallet_name}
                        </span>
                        <span className="shrink-0 font-medium">{money(wallet.amount)}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderPreparePaymentForm = () => {
    const hasMultipleSources = moveFundingSourceOptions.length > 1;
    const canAddSource =
      moveFundingSourceOptions.length > 1 &&
      moveFundingGroups.length < moveFundingSourceOptions.length &&
      moveFundingRows.length < MAX_PREPARE_PAYMENT_MOVE_ROWS;
    const prepareCopy = selectedMoveGoal?.intent === "PAY_OBLIGATION"
      ? "Move reserved money to the wallet that will pay this debt."
      : selectedMoveGoal?.intent === "RESERVE"
        ? "Move reserve money to the wallet that will make the urgent payment."
        : "Move reserved money to the wallet that will pay at checkout.";

    return (
      <div className="space-y-5">
        <div className="rounded-md bg-muted/25 px-4 py-3">
          <p className="text-sm font-medium">{prepareCopy}</p>
          <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <p className="text-xs text-muted-foreground">Reserved</p>
              <p className="font-semibold">{money(selectedMoveGoal?.unreleased_amount)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Preparing</p>
              <p className="font-semibold">{money(moveFundingTotalMoved)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Transfer fees</p>
              <p className="font-semibold">{money(moveFundingTotalFees)}</p>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          {moveFundingGroups.map((group, groupIndex) => {
            const source = moveFundingGroupSource(group);
            const usedSourceIds = new Set(moveFundingGroups.map((item, itemIndex) => (
              itemIndex === groupIndex ? "" : String(item.source_wallet_id || "")
            )));
            const groupMoved = (group.destinations || []).reduce((sum, destination) => (
              sum + parseAmountInput(destination.amount)
            ), 0);
            const groupRemaining = Math.max(moveFundingGroupMaxAmount(group) - groupMoved, 0);
            const canAddDestination = (group.destinations || []).length < MAX_PREPARE_PAYMENT_TARGET_WALLETS &&
              moveFundingRows.length < MAX_PREPARE_PAYMENT_MOVE_ROWS &&
              moveFundingTargetOptions.some((wallet) => (
                String(wallet.wallet_id) !== String(group.source_wallet_id) &&
                !(group.destinations || []).some((destination) => String(destination.target_wallet_id) === String(wallet.wallet_id))
              ));
            return (
              <div key={group.group_id || groupIndex} className="space-y-4 border-t border-border/70 pt-4 first:border-t-0 first:pt-0">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  {hasMultipleSources || moveFundingGroups.length > 1 ? (
                    <div className="min-w-0 flex-1 space-y-2">
                      <label className="text-sm font-medium">Money currently reserved in</label>
                      <Select value={group.source_wallet_id} onValueChange={(value) => updateMoveFundingSource(groupIndex, value)}>
                        <SelectTrigger className="w-full min-w-0">
                          <SelectValue placeholder="Choose wallet" />
                        </SelectTrigger>
                        <SelectContent className="max-w-[calc(100vw-2rem)]">
                          {moveFundingSourceOptions.map((source) => (
                            <SelectItem
                              key={source.wallet_id}
                              value={String(source.wallet_id)}
                              disabled={usedSourceIds.has(String(source.wallet_id))}
                            >
                              <span className="block max-w-full truncate">
                                {source.wallet_name} / reserved {money(source.unreleased_amount)}
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  ) : (
                    <div className="min-w-0 flex-1 rounded-md bg-muted/20 px-3 py-2 text-sm">
                      <p className="text-xs text-muted-foreground">Money currently reserved in</p>
                      <p className="truncate font-medium">{source?.wallet_name || "Wallet"}</p>
                    </div>
                  )}
                  {moveFundingGroups.length > 1 ? (
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      onClick={() => removeMoveFundingGroup(groupIndex)}
                      disabled={moveFundingGroups.length <= 1}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  ) : null}
                </div>

                <div className="space-y-4">
                  {(group.destinations || []).map((destination, destinationIndex) => {
                    const destinationMax = moveFundingDestinationMaxAmount(group, destinationIndex);
                    const feeOptions = moveFundingFeeWalletOptions({
                      ...destination,
                      source_wallet_id: group.source_wallet_id,
                    });
                    return (
                      <div key={destination.row_id || destinationIndex} className="space-y-3">
                        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto] md:items-end">
                          <div className="space-y-2">
                            <label className="text-sm font-medium">Wallet that will pay</label>
                            <Select
                              value={destination.target_wallet_id}
                              onValueChange={(value) => updateMoveFundingDestination(groupIndex, destinationIndex, { target_wallet_id: value })}
                            >
                              <SelectTrigger className="w-full min-w-0">
                                <SelectValue placeholder="Choose wallet" />
                              </SelectTrigger>
                              <SelectContent className="max-w-[calc(100vw-2rem)]">
                                {moveFundingGroupTargetOptions(group, destinationIndex).map((wallet) => (
                                  <SelectItem
                                    key={wallet.wallet_id}
                                    value={String(wallet.wallet_id)}
                                    disabled={wallet.disabled}
                                  >
                                    <span className="block max-w-full truncate">
                                      {wallet.wallet_name} / balance {money(wallet.balance)}
                                    </span>
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <label className="text-sm font-medium">Amount to prepare</label>
                            <Input
                              inputMode="numeric"
                              value={destination.amount}
                              onChange={(event) => updateMoveFundingDestination(groupIndex, destinationIndex, { amount: formatAmountInput(event.target.value) })}
                              placeholder={destinationMax ? money(destinationMax) : "0"}
                            />
                          </div>
                          <div className="flex gap-2">
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() => updateMoveFundingDestination(groupIndex, destinationIndex, { amount: formatAmountInput(String(destinationMax)) })}
                              disabled={!destinationMax}
                            >
                              Max
                            </Button>
                            {(group.destinations || []).length > 1 ? (
                              <Button
                                type="button"
                                size="icon"
                                variant="ghost"
                                onClick={() => removeMoveFundingDestination(groupIndex, destinationIndex)}
                                disabled={(group.destinations || []).length <= 1}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            ) : null}
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="h-8 px-0 text-muted-foreground hover:text-foreground"
                            onClick={() => updateMoveFundingDestination(groupIndex, destinationIndex, {
                              has_fee: !destination.has_fee,
                              fee_wallet_id: destination.fee_wallet_id || group.source_wallet_id,
                            })}
                          >
                            {destination.has_fee ? "Remove transfer fee" : "Add transfer fee"}
                          </Button>
                        </div>
                        {destination.has_fee ? (
                          <div className="grid gap-3 rounded-md bg-muted/20 p-3 md:grid-cols-[1fr_1fr]">
                            <div className="space-y-2">
                              <label className="text-sm font-medium">Fee amount</label>
                              <Input
                                inputMode="numeric"
                                value={destination.fee_amount}
                                onChange={(event) => updateMoveFundingDestination(groupIndex, destinationIndex, { fee_amount: formatAmountInput(event.target.value) })}
                                placeholder="0"
                              />
                            </div>
                            <div className="space-y-2">
                              <label className="text-sm font-medium">Fee paid from</label>
                              <Select
                                value={destination.fee_wallet_id || group.source_wallet_id}
                                onValueChange={(value) => updateMoveFundingDestination(groupIndex, destinationIndex, { fee_wallet_id: value })}
                              >
                                <SelectTrigger><SelectValue placeholder="Fee wallet" /></SelectTrigger>
                                <SelectContent>
                                  {feeOptions.map((wallet) => (
                                    <SelectItem key={wallet.wallet_id} value={String(wallet.wallet_id)}>
                                      {wallet.wallet_name}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2 md:col-span-2">
                              <label className="text-sm font-medium">Fee note</label>
                              <Input
                                value={destination.fee_note}
                                maxLength={200}
                                onChange={(event) => updateMoveFundingDestination(groupIndex, destinationIndex, { fee_note: event.target.value })}
                                placeholder="Bank transfer fee"
                              />
                            </div>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-muted/20 px-3 py-2 text-sm">
                  <span className="text-muted-foreground">
                    Moving {money(groupMoved)} / stays reserved {money(groupRemaining)}
                  </span>
                  {canAddDestination ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="px-0"
                      onClick={() => addMoveFundingDestination(groupIndex)}
                    >
                      <Plus className="mr-2 h-4 w-4" /> Add another payment wallet
                    </Button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        {canAddSource ? (
          <Button type="button" variant="outline" onClick={addMoveFundingGroup}>
            <Plus className="mr-2 h-4 w-4" /> Add another reserved wallet
          </Button>
        ) : null}

        <div className="space-y-2">
          <label className="text-sm font-medium">Transfer date</label>
          <Input
            type="date"
            value={moveFundingForm.date || todayISO}
            max={todayISO}
            onChange={(event) => {
              setMoveFundingForm((prev) => ({ ...prev, date: event.target.value }));
              setMoveFundingError("");
            }}
          />
        </div>

        {!moveFundingTargetsWithinLimit ? (
          <p className="text-sm text-destructive">
            Prepare payment can use up to {MAX_PREPARE_PAYMENT_TARGET_WALLETS} payment wallets.
          </p>
        ) : null}
        {!moveFundingPairsUnique ? (
          <p className="text-sm text-destructive">Each wallet pair can appear only once. Increase the existing amount instead.</p>
        ) : null}
        {moveFundingError ? <p className="text-sm text-destructive">{moveFundingError}</p> : null}
        {!moveFundingTargetOptions.length ? (
          <p className="text-sm text-destructive">
            No payment wallet is available. Add an active cash, debit, prepaid, or savings wallet in the same currency.
          </p>
        ) : null}
      </div>
    );
  };

  const preparePaymentCanReview =
    !moveGoalFundingMutation.isPending &&
    moveFundingRows.length > 0 &&
    moveFundingTargetsWithinLimit &&
    moveFundingPairsUnique &&
    moveFundingTotalMoved > 0;

  const renderPreparePaymentConfirmation = () => {
    const validRows = moveFundingRows.filter((row) => parseAmountInput(row.amount) > 0);
    const feeRows = validRows.filter((row) => row.has_fee && parseAmountInput(row.fee_amount) > 0);
    const walletChangeRows = Object.entries(moveFundingNetWalletChanges)
      .filter(([, amount]) => Number(amount) !== 0)
      .sort(([left], [right]) => Number(left) - Number(right));
    const preparedTargetRows = Object.entries(moveFundingPreparedByTarget)
      .filter(([, amount]) => Number(amount) > 0)
      .sort(([left], [right]) => Number(left) - Number(right));

    return (
      <div className="space-y-4">
        <div className="rounded-md border border-border bg-muted/20 p-3 text-sm text-muted-foreground">
          Sarflog will record real wallet transfers and move this goal's reserved-money label with them.
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">Money movement</p>
          {validRows.map((row) => {
            const source = moveFundingRowSource(row);
            const target = moveFundingWalletById(row.target_wallet_id);
            return (
              <div key={`${row.source_wallet_id}-${row.target_wallet_id}`} className="flex justify-between gap-3 rounded-md border border-border px-3 py-2 text-sm">
                <span>{source?.wallet_name || "Source"} {"->"} {target?.wallet_name || "Wallet"}</span>
                <span className="font-medium">{money(parseAmountInput(row.amount))}</span>
              </div>
            );
          })}
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">Transfer fees</p>
          {feeRows.length ? feeRows.map((row) => {
            const feeWallet = moveFundingWalletById(row.fee_wallet_id || row.source_wallet_id);
            return (
              <div key={`${row.source_wallet_id}-${row.target_wallet_id}-fee`} className="flex justify-between gap-3 rounded-md border border-border px-3 py-2 text-sm">
                <span>{feeWallet?.wallet_name || "Wallet"} fee</span>
                <span className="font-medium">{money(parseAmountInput(row.fee_amount))}</span>
              </div>
            );
          }) : (
            <p className="rounded-md border border-border px-3 py-2 text-sm text-muted-foreground">No transfer fees recorded.</p>
          )}
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">Wallet balance impact</p>
          {walletChangeRows.map(([walletId, amount]) => {
            const wallet = moveFundingWalletById(walletId);
            return (
              <div key={walletId} className="flex justify-between gap-3 rounded-md border border-border px-3 py-2 text-sm">
                <span>{wallet?.wallet_name || "Wallet"}</span>
                <span className={cn("font-medium", Number(amount) < 0 ? "text-destructive" : "text-primary")}>
                  {Number(amount) > 0 ? "+" : ""}{money(amount)}
                </span>
              </div>
            );
          })}
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium">{selectedMoveGoal?.title} prepared in</p>
          {preparedTargetRows.map(([walletId, amount]) => {
            const wallet = moveFundingWalletById(walletId);
            return (
              <div key={walletId} className="flex justify-between gap-3 rounded-md border border-border px-3 py-2 text-sm">
                <span>{wallet?.wallet_name || "Wallet"}</span>
                <span className="font-medium">{money(amount)}</span>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-muted-foreground">
          Fees are normal bank-fee expenses. They are not goal money.
        </p>
      </div>
    );
  };

  const renderPlannedPurchaseFlow = () => {
    if (!selectedUseGoal) return null;
    if (purchaseStep === PURCHASE_STEPS.CONFIRM_PURCHASE) {
      return (
        <div className="space-y-4">
          <div className="rounded-md border border-border bg-muted/20 p-4">
            <p className="text-sm font-medium">Did you buy this planned item?</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Record this only after the real purchase happened. If you have not bought it yet, the goal should stay active.
            </p>
            <p className="mt-3 text-xs text-muted-foreground">
              For clean wallet history, enter large planned purchases with the real purchase date before recording later spending from the same wallet.
            </p>
          </div>
        </div>
      );
    }

    if (purchaseStep === PURCHASE_STEPS.PAYMENT) {
      return (
        <div className="space-y-4">
          {isPlannedPurchase ? (
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                className={cn(
                  "rounded-md border p-2 text-left text-xs transition-colors",
                  useForm.settlement_mode === "DIRECT"
                    ? "border-primary bg-primary/10"
                    : "border-border bg-background hover:bg-muted/50"
                )}
                onClick={() => setPlannedPurchaseSettlementMode("DIRECT")}
              >
                <span className="block text-sm font-medium">I paid from goal wallet(s)</span>
                <span className="mt-0.5 block text-muted-foreground">The real checkout used goal wallets.</span>
              </button>
              <button
                type="button"
                className={cn(
                  "rounded-md border p-2 text-left text-xs transition-colors",
                  useForm.settlement_mode === "GOAL_BACKED_OFF_WALLET_PAYMENT"
                    ? "border-primary bg-primary/10"
                    : "border-border bg-background hover:bg-muted/50"
                )}
                onClick={() => setPlannedPurchaseSettlementMode("GOAL_BACKED_OFF_WALLET_PAYMENT")}
              >
                <span className="block text-sm font-medium">I paid from another wallet/card</span>
                <span className="mt-0.5 block text-muted-foreground">Goal money still backs the purchase.</span>
              </button>
            </div>
          ) : null}
          <div>
            <p className="text-sm font-medium">Which wallet or cash paid at checkout?</p>
            <p className="mt-1 text-xs text-muted-foreground">
              The final price is calculated from these payment rows.
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Purchase date</label>
            <Input
              type="date"
              value={useForm.date || ""}
              max={todayISO}
              onChange={(event) => setUseForm((prev) => ({ ...prev, date: event.target.value, subcategory_id: "" }))}
            />
          </div>
          {renderPaymentWalletRows({ showFinalPrice: true })}
          {isPlannedPurchase && useForm.settlement_mode === "DIRECT" && !paymentWalletsAllFundingSources ? (
            <p className="text-xs text-destructive">
              Goal-funded purchase means every payment wallet must be one of the wallets that reserved money for this goal.
            </p>
          ) : null}
        </div>
      );
    }

    if (purchaseStep === PURCHASE_STEPS.CLASSIFICATION) {
      return (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium">How should Sarflog classify this purchase?</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Planned purchases keep category detail, but do not consume the normal monthly budget limit.
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Category</label>
            <Select value={useForm.category} onValueChange={(value) => setUseForm((prev) => ({ ...prev, category: value, subcategory_id: "" }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((category) => (
                  <SelectItem key={category} value={category}>{category}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Subcategory</label>
            <Select
              value={useForm.subcategory_id || "__none__"}
              onValueChange={(value) => setUseForm((prev) => ({ ...prev, subcategory_id: value === "__none__" ? "" : value }))}
              disabled={!selectedUseBudget}
            >
              <SelectTrigger><SelectValue placeholder="Subcategory" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">None</SelectItem>
                {useSubcategories.map((subcategory) => (
                  <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                    {subcategory.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-3 rounded-md border border-border bg-muted/20 p-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Purchase result</label>
              <Select
                value={useForm.result_type || "EXPENSE_ONLY"}
                onValueChange={(value) => setUseForm((prev) => ({ ...prev, result_type: value }))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="EXPENSE_ONLY">Expense only</SelectItem>
                  <SelectItem value="ASSET_PURCHASE">Create asset from purchase</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {useForm.result_type === "ASSET_PURCHASE" ? (
              <div className="space-y-2">
                <label className="text-sm font-medium">Asset name</label>
                <Input
                  value={useForm.asset_title || ""}
                  placeholder={selectedUseGoal?.title || "Asset name"}
                  onChange={(event) => setUseForm((prev) => ({ ...prev, asset_title: event.target.value }))}
                />
              </div>
            ) : null}
          </div>
          {purchaseAmountDiffersFromTarget ? (
            <div className="rounded-md border border-border bg-background/70 p-3">
              <p className="text-sm font-medium">Final price differs from the goal target.</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Update this goal target from {money(selectedUseGoal?.target_amount)} to {money(useAmount)} and complete it as one purchase. Any leftover reserved money will be unreserved.
              </p>
              <label className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={Boolean(useForm.adjust_target_to_purchase_amount)}
                  onChange={(event) => setUseForm((prev) => ({ ...prev, adjust_target_to_purchase_amount: event.target.checked }))}
                />
                <span>Update target and complete this planned purchase.</span>
              </label>
            </div>
          ) : null}
        </div>
      );
    }

    if (purchaseStep === PURCHASE_STEPS.PAYMENT_PLAN) {
      return (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium">Will you pay any of the rest over time?</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Choose this when today's payment was only the down payment and the store or lender expects future payments.
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              {
                value: "PAID_IN_FULL",
                title: "No, this purchase is finished",
                description: "Today's checkout paid the full price.",
              },
              {
                value: "PAYMENT_PLAN",
                title: "Yes, I will pay the rest over time",
                description: "Sarflog will create the payment plan for what is left.",
              },
            ].map((option) => (
              <button
                key={option.value}
                type="button"
                className={cn(
                  "rounded-md border p-3 text-left transition-colors",
                  useForm.payment_after_purchase === option.value
                    ? "border-primary bg-primary/10"
                    : "border-border bg-background hover:bg-muted/50"
                )}
                onClick={() => setUseForm((prev) => ({
                  ...prev,
                  payment_after_purchase: option.value,
                  payment_plan_total_price: option.value === "PAYMENT_PLAN" && !prev.payment_plan_total_price
                    ? formatAmountInput(String(Math.max(paymentTotal, Number(selectedUseGoal?.target_amount || 0))))
                    : prev.payment_plan_total_price,
                  payment_plan_item_name: prev.payment_plan_item_name || selectedUseGoal?.title || "",
                }))}
              >
                <span className="block text-sm font-medium">{option.title}</span>
                <span className="mt-1 block text-xs text-muted-foreground">{option.description}</span>
              </button>
            ))}
          </div>

          {payment_planBridgeSelected ? (
            <div className="space-y-4 rounded-md border border-border bg-muted/20 p-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Full price</label>
                  <Input
                    inputMode="numeric"
                    value={useForm.payment_plan_total_price}
                    onChange={(event) => setUseForm((prev) => ({ ...prev, payment_plan_total_price: formatAmountInput(event.target.value) }))}
                    placeholder="0"
                  />
                  <p className="text-xs text-muted-foreground">Today's payment was {money(paymentTotal)}.</p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Number of future payments</label>
                  <Input
                    inputMode="numeric"
                    value={useForm.payment_plan_months}
                    onChange={(event) => setUseForm((prev) => ({ ...prev, payment_plan_months: event.target.value.replace(/\D/g, "").slice(0, 3) }))}
                    placeholder="12"
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">What did you buy?</label>
                  <Input
                    value={useForm.payment_plan_item_name}
                    onChange={(event) => setUseForm((prev) => ({ ...prev, payment_plan_item_name: event.target.value }))}
                    placeholder={selectedUseGoal?.title || "Laptop"}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Store or lender</label>
                  <Input
                    value={useForm.payment_plan_store_or_bank_name}
                    onChange={(event) => setUseForm((prev) => ({ ...prev, payment_plan_store_or_bank_name: event.target.value }))}
                    placeholder="Optional"
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">How often?</label>
                  <Select
                    value={useForm.payment_plan_frequency || "MONTHLY"}
                    onValueChange={(value) => setUseForm((prev) => ({ ...prev, payment_plan_frequency: value }))}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {PAYMENT_PLAN_FREQUENCIES.map((frequency) => (
                        <SelectItem key={frequency.value} value={frequency.value}>
                          {frequency.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="rounded-md bg-background/60 px-3 py-2 text-sm">
                  <p className="text-xs text-muted-foreground">Left after today</p>
                  <p className="mt-1 font-semibold">{money(payment_planRemainingAmount)}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    About {money(payment_planRegularPayment)} each time before final rounding.
                  </p>
                </div>
              </div>
              <label className="flex items-start gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={Boolean(useForm.create_next_payment_goal)}
                  onChange={(event) => setUseForm((prev) => ({ ...prev, create_next_payment_goal: event.target.checked }))}
                />
                <span>After this purchase, start a new goal for the next payment.</span>
              </label>
              {useForm.create_next_payment_goal ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">New goal name</label>
                    <Input
                      value={useForm.next_payment_goal_title}
                      maxLength={32}
                      onChange={(event) => setUseForm((prev) => ({ ...prev, next_payment_goal_title: event.target.value }))}
                      placeholder="Laptop payment"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Ready by</label>
                    <Input
                      type="date"
                      value={useForm.next_payment_goal_target_date || ""}
                      onChange={(event) => setUseForm((prev) => ({ ...prev, next_payment_goal_target_date: event.target.value }))}
                    />
                  </div>
                </div>
              ) : null}
              {payment_planTotalPrice > 0 && payment_planTotalPrice <= paymentTotal ? (
                <p className="text-xs text-destructive">The full price must be higher than today's payment.</p>
              ) : null}
            </div>
          ) : null}
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div>
          <p className="text-sm font-medium">Review purchase</p>
          <p className="mt-1 text-xs text-muted-foreground">Check the real payment and goal outcome before recording.</p>
        </div>
        <div className="grid gap-2 rounded-md border border-border bg-muted/20 p-3 text-sm">
          <div className="flex justify-between gap-3">
            <span className="text-muted-foreground">Goal</span>
            <span className="font-medium">{selectedUseGoal.title}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-muted-foreground">Final price</span>
            <span className="font-medium">{money(paymentTotal)}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-muted-foreground">Goal money</span>
            <span className="font-medium">
              {useForm.settlement_mode === "DIRECT" ? "Goal wallets paid" : "Goal-backed off-wallet payment"}
            </span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-muted-foreground">Category</span>
            <span className="font-medium">{useForm.category}</span>
          </div>
          <div className="flex justify-between gap-3">
            <span className="text-muted-foreground">After checkout</span>
            <span className="font-medium text-right">
              {payment_planBridgeSelected
                ? `${money(payment_planRemainingAmount)} left over ${payment_planMonths || 0} payments`
                : "Purchase finished"}
            </span>
          </div>
        </div>
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Payment split</p>
          {paymentRows.map((row, index) => {
            const wallet = paymentWalletOptions.find((item) => String(item.wallet_id) === String(row.wallet_id))
              || paymentWallets.find((item) => String(item.wallet_id) === String(row.wallet_id));
            return (
              <div key={index} className="flex justify-between gap-3 rounded-md border border-border px-3 py-2 text-sm">
                <span>{wallet?.wallet_name || "Wallet"}</span>
                <span className="font-medium">{money(parseAmountInput(row.amount))}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderPlannedPurchaseFooter = () => {
    if (purchaseStep === PURCHASE_STEPS.CONFIRM_PURCHASE) {
      return (
        <DialogFooter>
          <Button variant="outline" onClick={() => setUseDialog(null)}>Not yet</Button>
          <Button onClick={() => setPurchaseStep(PURCHASE_STEPS.PAYMENT)}>Yes, I bought it</Button>
        </DialogFooter>
      );
    }
    if (purchaseStep === PURCHASE_STEPS.REVIEW) {
      return (
        <DialogFooter>
          <Button variant="outline" onClick={() => setPurchaseStep(PURCHASE_STEPS.PAYMENT_PLAN)}>Back</Button>
          <Button onClick={submitUseGoal} disabled={recordPurchaseMutation.isPending || !canContinuePaymentStep || !canContinueClassificationStep || !canContinuePaymentPlanStep}>
            Record purchase
          </Button>
        </DialogFooter>
      );
    }
    const previousStep = Math.max(PURCHASE_STEPS.CONFIRM_PURCHASE, purchaseStep - 1);
    const nextStep = Math.min(PURCHASE_STEPS.REVIEW, purchaseStep + 1);
    const disabled = (
      (purchaseStep === PURCHASE_STEPS.PAYMENT && !canContinuePaymentStep) ||
      (purchaseStep === PURCHASE_STEPS.CLASSIFICATION && !canContinueClassificationStep) ||
      (purchaseStep === PURCHASE_STEPS.PAYMENT_PLAN && !canContinuePaymentPlanStep)
    );
    return (
      <DialogFooter>
        <Button variant="outline" onClick={() => setPurchaseStep(previousStep)}>Back</Button>
        <Button onClick={() => setPurchaseStep(nextStep)} disabled={disabled}>Continue</Button>
      </DialogFooter>
    );
  };

  if (userQuery.isLoading) {
    return <LoadingSpinner fullScreen />;
  }

  if (!isPremium) {
    return (
      <div className="space-y-6">
        <PageHeader title="Savings goals" description="Reserve real wallet money for future goals." />
        <Card>
          <CardHeader>
            <CardTitle>Premium feature</CardTitle>
            <CardDescription>Savings goals need premium access.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/premium")}>View plans</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isLoading = summaryQuery.isLoading || goalsQuery.isLoading;

  return (
    <div className="space-y-6">
      <PageHeader title="Savings goals" description="Reserve real wallet money for goals without counting the same money twice." />

      {isLoading ? <LoadingSpinner /> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Wallet balance" value={summary.total_wallet_balance} icon={Wallet} />
        <StatCard title="Reserved for goals" value={summary.allocated_to_goals} icon={Target} />
        <StatCard title="Free to reserve" value={summary.available_for_goals} icon={CircleDollarSign} />
        <StatCard
          title="Over-reserved"
          value={summary.over_allocated_amount}
          icon={ShieldAlert}
          tone={summary.over_allocated_amount > 0 ? "danger" : "default"}
          caption={summary.over_allocated_amount > 0 ? "Reduce reserved money or add money back." : "All reserved money is covered."}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Wallets with goal money</CardTitle>
              <CardDescription>Wallets that can reserve money or hold prepared payments.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              {fundingSummaryWallets.length ? fundingSummaryWallets.map((wallet) => (
                <WalletFundingCard key={wallet.wallet_id} wallet={wallet} />
              )) : (
                <p className="text-sm text-muted-foreground">No wallets are holding goal money.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Goals</CardTitle>
              <CardDescription>Goals show exactly which wallet money is reserved.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!activeGoals.length ? (
                <p className="text-sm text-muted-foreground">No active goals yet.</p>
              ) : activeGoals.map((goal) => {
                const metric = goalPrimaryMetric(goal);
                const cardStats = goalCardStats(goal);
                const goalUi = getGoalCardUiState(goal, {
                  eligibleWalletCount: eligibleWallets.length,
                  canPreparePayment: hasPreparePaymentRoute(goal),
                });
                const actionLabel = goalUi.primaryAction?.label;
                const ActionIcon = GOAL_ACTION_ICONS[goalUi.primaryAction?.kind] || ArrowRightLeft;
                const isReserveGoal = goal.intent === "RESERVE";
                return (
                  <Card key={goal.id} className="border-border">
                    <CardHeader className="pb-3">
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <CardTitle className="text-lg">{goal.title}</CardTitle>
                            <span className="rounded-full border border-border bg-muted/40 px-2 py-1 text-xs capitalize text-muted-foreground">
                              {goalUi.intentLabel}
                            </span>
                            <span className={cn(
                              "rounded-full border px-2 py-1 text-xs",
                              isReserveGoal && metric.label === "Fully reserved"
                                ? "border-primary/30 bg-primary/10 text-primary"
                                : isReserveGoal
                                  ? "border-amber-500/35 bg-amber-500/10 text-amber-300"
                                  : "border-border bg-muted/40 text-muted-foreground"
                            )}>
                              {isReserveGoal ? metric.label : goalUi.statusLabel}
                            </span>
                          </div>
                          <CardDescription>
                            Target {money(goal.target_amount)}
                            {goal.target_date ? ` / ${formatDisplayDate(goal.target_date, appLang)}` : ""}
                          </CardDescription>
                          <p className="mt-1 text-xs text-muted-foreground">{goalUi.intentDescription}</p>
                          {goal.payment_plan_target ? (
                            <p className="mt-1 text-xs text-muted-foreground">
                              Saving for payment {goal.payment_plan_target.payment_number} of {goal.payment_plan_target.total_payments}
                              {goal.payment_plan_target.due_date ? ` / due ${formatDisplayDate(goal.payment_plan_target.due_date, appLang)}` : ""}
                            </p>
                          ) : null}
                        </div>
                        <div className="text-left md:text-right">
                          {isReserveGoal ? <div className="text-xs text-muted-foreground">Protected now</div> : null}
                          <div className="text-lg font-semibold">{money(metric.amount)}</div>
                          <div className="text-xs text-muted-foreground">
                            {isReserveGoal ? `${metric.percent}% of target` : `${metric.percent}% ${metric.label}`}
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(metric.percent || 0, 100)}%` }} />
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid gap-3 text-sm md:grid-cols-3">
                        {cardStats.map((stat) => (
                          <div key={stat.label}>
                            <div className="text-muted-foreground">{stat.label}</div>
                            <div className="font-medium">{money(stat.amount)}</div>
                          </div>
                        ))}
                      </div>
                      <FundingSources goal={goal} />
                      {goalUi.isReadOnly ? (
                        <div className="rounded-md border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
                          This goal is read-only saving history. Add future funding through project top-ups.
                        </div>
                      ) : null}
                      <div className="flex flex-wrap gap-2">
                        <Button size="sm" onClick={() => openFunding(goal, "allocate")} disabled={!goalUi.canReserve}>
                          <Plus className="mr-2 h-4 w-4" /> Reserve money
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => openFunding(goal, "return")} disabled={!goalUi.canUnreserve}>
                          <RotateCcw className="mr-2 h-4 w-4" /> Unreserve
                        </Button>
                        {(goal.intent === "PLANNED_PURCHASE" || goal.intent === "PAY_OBLIGATION" || goal.intent === "RESERVE") && goal.status === "ACTIVE" ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openPreparePayment(goal)}
                            disabled={!goalUi.canPreparePayment}
                          >
                            <ArrowRightLeft className="mr-2 h-4 w-4" /> Prepare payment
                          </Button>
                        ) : null}
                        {actionLabel ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleIntentAction(goal)}
                            disabled={goalUi.primaryAction.disabled}
                          >
                            <ActionIcon className="mr-2 h-4 w-4" /> {actionLabel}
                          </Button>
                        ) : null}
                        <Button size="sm" variant="outline" onClick={() => setActivityGoal(goal)}>
                          <History className="mr-2 h-4 w-4" /> View activity
                        </Button>
                        {goalUi.canArchive ? (
                          <Button size="sm" variant="ghost" onClick={() => setArchiveTarget(goal)}>
                            <Archive className="mr-2 h-4 w-4" /> Archive
                          </Button>
                        ) : null}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </CardContent>
          </Card>

          {archivedGoals.length ? (
            <Card>
              <CardHeader>
                <CardTitle>Archived Goals</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {archivedGoals.map((goal) => (
                  <div key={goal.id} className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border px-3 py-2">
                    <div>
                      <div className="font-medium">{goal.title}</div>
                      <div className="text-sm text-muted-foreground">{money(goal.target_amount)}</div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => restoreMutation.mutate(goal.id)}>Restore</Button>
                      <Button size="icon" variant="ghost" onClick={() => setDeleteTarget(goal)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}
        </section>

        <aside className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Create goal</CardTitle>
              <CardDescription>Start with what you are saving for. Wallet money is reserved later.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  The goal is the plan. Reserving wallet money happens after the goal exists.
                </p>
                <Button type="button" className="w-full rounded-md" onClick={() => setCreateGoalOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  New goal
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>How this works</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex gap-2"><Wallet className="mt-0.5 h-4 w-4" /> Wallet balance is your real money.</div>
              <div className="flex gap-2"><Target className="mt-0.5 h-4 w-4" /> Reserved money still stays in its wallet.</div>
              <div className="flex gap-2"><BriefcaseBusiness className="mt-0.5 h-4 w-4" /> Spending plans stay separate from savings goals.</div>
            </CardContent>
          </Card>
        </aside>
      </div>

      <Dialog open={createGoalOpen} onOpenChange={handleCreateGoalOpenChange}>
        <DialogContent className="sm:max-w-4xl p-0">
          <DialogHeader>
            <div className="border-b border-border px-6 py-5">
              <DialogTitle>Create goal</DialogTitle>
              <DialogDescription>Step {createGoalStep} of 5: {createGoalStepTitle}</DialogDescription>
              <Progress value={(createGoalStep / 5) * 100} className="mt-4 h-2 bg-muted" />
            </div>
          </DialogHeader>
          <div className="max-h-[calc(100vh-13rem)] overflow-y-auto px-6 py-5">
            {renderCreateGoalStep()}
          </div>
          {goalFormError ? <p className="px-6 text-sm font-medium text-destructive">{goalFormError}</p> : null}
          <DialogFooter className="border-t border-border px-6 py-4">
            <Button variant="outline" className="rounded-md" onClick={() => handleCreateGoalOpenChange(false)}>Cancel</Button>
            {createGoalStep > 1 ? (
              <Button variant="outline" className="rounded-md" onClick={goBackCreateGoalStep}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
            ) : null}
            {createGoalStep < 5 ? (
              <Button className="rounded-md" onClick={goNextCreateGoalStep}>
                Next
              </Button>
            ) : (
              <Button className="rounded-md" onClick={submitGoal} disabled={createGoalMutation.isPending}>
                Create goal
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(fundingDialog)} onOpenChange={(open) => !open && setFundingDialog(null)}>
        <DialogContent className="sm:max-w-2xl p-0">
          <DialogHeader className="border-b border-border px-5 py-4 pr-12 sm:px-6">
            <DialogTitle>
              {fundingMode === "allocate" ? "Reserve money" : "Unreserve money"}
            </DialogTitle>
          </DialogHeader>
          <div className="max-h-[calc(100vh-12rem)] overflow-y-auto px-5 py-4 sm:px-6">
            <div className="space-y-4">
              <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
                <div className="font-medium">{selectedGoal?.title}</div>
                <div className="text-muted-foreground">
                  Maximum: {money(maxFundingAmount)}
                </div>
              </div>
              {fundingMode === "allocate" ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between gap-3">
                    <label className="text-sm font-medium">Wallet sources</label>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={addFundingRow}
                      disabled={fundingRows.length >= eligibleWallets.length}
                    >
                      <Plus className="mr-2 h-4 w-4" /> Add wallet
                    </Button>
                  </div>
                  {fundingRows.map((row, index) => {
                    const rowWallet = fundingRowWallet(row);
                    const rowMax = fundingRowMax(row, index);
                    const usedWalletIds = new Set(fundingRows.map((item, itemIndex) => (
                      itemIndex === index ? "" : String(item.wallet_id)
                    )));
                    return (
                      <div key={index} className="grid min-w-0 gap-3 rounded-md border border-border p-3 sm:grid-cols-[minmax(0,1fr)_10rem] sm:items-end">
                        <div className="min-w-0 space-y-2">
                          <label className="text-xs font-medium text-muted-foreground">Wallet</label>
                          <Select value={row.wallet_id} onValueChange={(value) => updateFundingRow(index, { wallet_id: value })}>
                            <SelectTrigger className="w-full min-w-0">
                              <SelectValue placeholder="Choose wallet" />
                            </SelectTrigger>
                            <SelectContent className="max-w-[calc(100vw-2rem)]">
                              {eligibleWallets.map((wallet) => (
                                <SelectItem
                                  key={wallet.wallet_id}
                                  value={String(wallet.wallet_id)}
                                  disabled={usedWalletIds.has(String(wallet.wallet_id))}
                                >
                                  <span className="block max-w-full truncate">
                                    {wallet.wallet_name} - free {money(wallet.available_for_goals)}
                                  </span>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="min-w-0 space-y-2">
                          <label className="text-xs font-medium text-muted-foreground">Amount</label>
                          <Input
                            inputMode="numeric"
                            value={row.amount}
                            onChange={(event) => updateFundingRow(index, { amount: formatAmountInput(event.target.value) })}
                            className="w-full"
                          />
                        </div>
                        <div className="flex gap-2 sm:col-span-2 sm:justify-end">
                          <Button type="button" variant="outline" onClick={() => updateFundingRow(index, { amount: formatAmountInput(String(rowMax)) })}>
                            Max
                          </Button>
                          <Button type="button" variant="ghost" size="icon" onClick={() => removeFundingRow(index)} disabled={fundingRows.length <= 1}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                        <div className="grid gap-1 text-xs text-muted-foreground sm:col-span-2 sm:grid-cols-3">
                          <span>Balance: {money(rowWallet?.balance)}</span>
                          <span>Already reserved: {money(rowWallet?.allocated_to_goals)}</span>
                          <span>Free to reserve: {money(rowWallet?.available_for_goals)}</span>
                        </div>
                      </div>
                    );
                  })}
                  <div className="rounded-md bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                    Selected: {money(fundingRowsTotal)} / Remaining after reserve: {money(Math.max(goalRemainingToFund - fundingRowsTotal, 0))}
                  </div>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Wallet</label>
                    <Select value={fundingWalletId} onValueChange={setFundingWalletId}>
                      <SelectTrigger className="w-full min-w-0">
                        <SelectValue placeholder="Choose wallet" />
                      </SelectTrigger>
                      <SelectContent className="max-w-[calc(100vw-2rem)]">
                        {fundingWallets.map((wallet) => (
                          <SelectItem key={wallet.wallet_id} value={String(wallet.wallet_id)}>
                            <span className="block max-w-full truncate">
                              {wallet.wallet_name} - still reserved {money(selectedGoal?.funding_sources?.find((source) => source.wallet_id === wallet.wallet_id)?.unreleased_amount)}
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Amount</label>
                    <div className="flex min-w-0 gap-2">
                      <Input
                        inputMode="numeric"
                        value={fundingAmount}
                        onChange={(event) => setFundingAmount(formatAmountInput(event.target.value))}
                        className="min-w-0 flex-1"
                      />
                      <Button type="button" variant="outline" className="shrink-0" onClick={() => setFundingAmount(formatAmountInput(String(maxFundingAmount)))}>Max</Button>
                    </div>
                  </div>
                </>
              )}
              {fundingError ? <p className="text-sm text-destructive">{fundingError}</p> : null}
            </div>
          </div>
          <DialogFooter className="border-t border-border px-5 py-4 sm:px-6">
            <Button variant="outline" onClick={() => setFundingDialog(null)}>Cancel</Button>
            <Button
              onClick={submitFunding}
              disabled={
                allocateMutation.isPending ||
                returnMutation.isPending ||
                (fundingMode === "allocate" ? !fundingRows.length : !fundingWalletId)
              }
            >
              {fundingMode === "allocate" ? "Reserve" : "Unreserve"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(prepareDialog)}
        onOpenChange={(open) => {
          if (!open) {
            setMoveFundingConfirmOpen(false);
            setPrepareDialog(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-2xl p-0">
          <DialogHeader className="border-b border-border px-5 py-4 pr-12 sm:px-6">
            <DialogTitle>Prepare payment</DialogTitle>
            <DialogDescription>
              {selectedMoveGoal?.title}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[calc(100vh-13rem)] overflow-y-auto px-5 py-4 sm:px-6">
            {renderPreparePaymentForm()}
          </div>
          <DialogFooter className="border-t border-border px-5 py-4 sm:px-6">
            <Button variant="outline" onClick={() => setPrepareDialog(null)}>Cancel</Button>
            <Button
              onClick={requestMoveGoalFundingConfirmation}
              disabled={!preparePaymentCanReview}
            >
              Review payment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={moveFundingConfirmOpen} onOpenChange={setMoveFundingConfirmOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Confirm payment prep</DialogTitle>
            <DialogDescription>
              {selectedMoveGoal?.title}
            </DialogDescription>
          </DialogHeader>
          {renderPreparePaymentConfirmation()}
          <DialogFooter>
            <Button variant="outline" onClick={() => setMoveFundingConfirmOpen(false)}>Back</Button>
            <Button onClick={submitMoveGoalFunding} disabled={moveGoalFundingMutation.isPending}>
              Confirm and move money
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(useDialog)} onOpenChange={(open) => !open && setUseDialog(null)}>
        <DialogContent className={selectedUseGoal?.intent === "PLANNED_PURCHASE" || selectedUseGoal?.intent === "PAY_OBLIGATION" ? "sm:max-w-2xl" : "sm:max-w-xl"}>
          <DialogHeader>
            <DialogTitle>
              {selectedUseGoal?.intent === "RESERVE"
                ? "Use reserve"
                : selectedUseGoal?.intent === "PAY_OBLIGATION"
                  ? "Make debt payment"
                  : "Record purchase"}
            </DialogTitle>
            <DialogDescription>
              {selectedUseGoal?.intent === "PLANNED_PURCHASE"
                ? `Step ${purchaseStep} of ${PURCHASE_STEPS.REVIEW} - ${selectedUseGoal?.title || ""}`
                : selectedUseGoal?.title}
            </DialogDescription>
          </DialogHeader>
          {selectedUseGoal?.intent === "PLANNED_PURCHASE" && purchaseStep > PURCHASE_STEPS.CONFIRM_PURCHASE ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-fit px-0 text-muted-foreground hover:text-foreground"
              onClick={() => setPurchaseStep(Math.max(PURCHASE_STEPS.CONFIRM_PURCHASE, purchaseStep - 1))}
            >
              Back to previous step
            </Button>
          ) : null}
          {selectedUseGoal?.intent === "PLANNED_PURCHASE" ? (
            <>
              <div className="space-y-4">
                {renderPlannedPurchaseFlow()}
                {useError ? <p className="text-sm text-destructive">{useError}</p> : null}
              </div>
              {renderPlannedPurchaseFooter()}
            </>
          ) : selectedUseGoal?.intent === "PAY_OBLIGATION" ? (
            <>
              <div className="space-y-4">
                {renderDebtPaymentFlow()}
                {useError ? <p className="text-sm text-destructive">{useError}</p> : null}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setUseDialog(null)}>Cancel</Button>
                <Button
                  onClick={submitUseGoal}
                  disabled={
                    recordDebtPaymentMutation.isPending ||
                    !paymentRows.length ||
                    paymentTotal <= 0 ||
                    !paymentWalletRowsUnique ||
                    !paymentRowsWithinFundingAmounts ||
                    !paymentWalletsAllFundingSources
                  }
                >
                  Make payment
                </Button>
              </DialogFooter>
            </>
          ) : (
            <>
              <div className="space-y-4">
                {renderReserveUseFlow()}
                {useError ? <p className="text-sm text-destructive">{useError}</p> : null}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setUseDialog(null)}>Cancel</Button>
                <Button
                  onClick={submitUseGoal}
                  disabled={
                    useReserveMutation.isPending ||
                    !paymentRows.length ||
                    paymentTotal <= 0 ||
                    !paymentWalletRowsUnique ||
                    !paymentRowsWithinFundingAmounts ||
                    !paymentWalletsAllFundingSources
                  }
                >
                  Record reserve use
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(activityGoal)} onOpenChange={(open) => !open && setActivityGoal(null)}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{activityGoal?.title ? `${activityGoal.title} activity` : "Goal activity"}</DialogTitle>
            <DialogDescription>
              {activityGoal ? intentLabel(activityGoal.intent) : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[calc(100vh-14rem)] overflow-y-auto pr-1">
            {renderGoalActivity()}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setActivityGoal(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={Boolean(graduateTarget)}
        onOpenChange={(open) => !open && setGraduateTarget(null)}
        title="Create project from goal"
        description="This turns the goal into a historical saving record. Its current reserved money becomes the isolated project stash, and future additions belong in project top-ups."
        confirmText="Create project"
        cancelText="Cancel"
        confirmVariant="default"
        isConfirming={graduateGoalMutation.isPending}
        onConfirm={async () => {
          const originGoal = graduateTarget;
          const project = await graduateGoalMutation.mutateAsync({
            goalId: originGoal.id,
            payload: buildFundProjectGraduationPayload(originGoal, todayISO),
          });
          setGraduateTarget(null);
          navigate("/budgets", { state: buildFundProjectNavigationState(project, originGoal) });
        }}
      >
        <div className="rounded-md border border-border bg-muted/20 p-3 text-sm">
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground">Project stash</span>
            <span className="font-medium">{money(graduateTarget?.unreleased_amount || 0)}</span>
          </div>
        </div>
      </ConfirmDialog>

      <ConfirmDialog
        open={Boolean(archiveTarget)}
        onOpenChange={(open) => !open && setArchiveTarget(null)}
        title="Archive goal"
        description="Money still reserved for this goal will be returned to its wallet."
        confirmText="Archive"
        cancelText="Cancel"
        isConfirming={archiveMutation.isPending}
        onConfirm={async () => {
          await archiveMutation.mutateAsync(archiveTarget.id);
          setArchiveTarget(null);
        }}
      />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete archived goal"
        description="This permanently removes the archived goal."
        confirmText="Delete"
        cancelText="Cancel"
        isConfirming={deleteMutation.isPending}
        onConfirm={async () => {
          await deleteMutation.mutateAsync(deleteTarget.id);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
