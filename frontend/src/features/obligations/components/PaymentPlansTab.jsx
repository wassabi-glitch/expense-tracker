import { createElement, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  CreditCard,
  Eye,
  Edit2,
  FileText,
  Layers3,
  Plus,
  ReceiptText,
  ShieldCheck,
  WalletCards,
  ShieldAlert,
  RotateCcw,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { SPENDING_CATEGORIES } from "@/lib/category";
import { getWallets } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatAmountInput, formatDisplayDate, formatUzs, parseAmountInput } from "@/lib/format";
import { toISODateInTimeZone } from "@/lib/date";
import {
  useAddPaymentPlanChargeMutation,
  useArchivePaymentPlanMutation,
  useCreatePaymentPlanMutation,
  useDeletePaymentPlanMutation,
  usePaymentPlanDetailsQuery,
  usePaymentPlansQuery,
  usePaymentPlanSummaryQuery,
  usePreviewPaymentPlanScheduleMutation,
  useRecordPaymentPlanPaymentMutation,
  useUnarchivePaymentPlanMutation,
  useUndoLatestPaymentPlanPaymentMutation,
  useUpdatePaymentPlanMutation,
  useWriteOffPaymentPlanPaymentMutation,
  useUndoPaymentPlanPaymentWriteOffMutation,
} from "../hooks/usePaymentPlans";
import {
  defaultWalletAllocation,
  normalizeWalletAllocations,
  WalletAllocationEditor,
  walletAllocationTotal,
} from "./WalletAllocationEditor";
import { MIN_SUPPORTED_USER_DATE } from "../obligationSchemas";

const PAYMENT_PLAN_TYPES = [
  {
    value: "STORE_INSTALLMENT",
    label: "Buy now, pay over time",
    helper: "Products from a store, marketplace, or finance partner.",
    category: "",
    itemQuestion: "What did you buy?",
    itemPlaceholder: "Phone, sofa, laptop, appliance...",
    providerLabel: "Store or seller",
    providerPlaceholder: "Store, marketplace, seller",
    totalLabel: "Total purchase price",
    upfrontLabel: "Down payment paid today",
    assetQuestion: "Do you want to track this item as an asset?",
    assetEligible: true,
  },
  {
    value: "BANK_LOAN",
    label: "Bank loan / microloan",
    helper: "A bank or lender gives you money, and you repay it on schedule.",
    category: "",
    itemQuestion: "What is this bank loan for?",
    itemPlaceholder: "Microloan, personal cash loan, business cash need...",
    providerLabel: "Bank or lender",
    providerPlaceholder: "Bank name",
    totalLabel: "Loan amount",
    upfrontLabel: "",
    assetEligible: false,
  },
  {
    value: "MORTGAGE",
    label: "Home loan / mortgage",
    helper: "A property loan with scheduled repayment.",
    category: "Housing",
    itemQuestion: "What property is this for?",
    itemPlaceholder: "Apartment, house, land...",
    providerLabel: "Bank or lender",
    providerPlaceholder: "Bank name",
    totalLabel: "Property price",
    upfrontLabel: "Down payment paid today",
    assetQuestion: "Do you want to track this property as an asset?",
    assetEligible: true,
  },
  {
    value: "AUTO_LOAN",
    label: "Vehicle loan",
    helper: "A car or vehicle bought with scheduled financing.",
    category: "Transport",
    itemQuestion: "What vehicle is this for?",
    itemPlaceholder: "Car, motorbike, truck...",
    providerLabel: "Bank, lender, or dealership",
    providerPlaceholder: "Bank, dealer, lender",
    totalLabel: "Vehicle price",
    upfrontLabel: "Down payment paid today",
    assetQuestion: "Do you want to track this vehicle as an asset?",
    assetEligible: true,
  },
  {
    value: "EDUCATION_LOAN",
    label: "Education payment plan",
    helper: "Tuition, course, university, or training paid over time.",
    category: "Education",
    itemQuestion: "What education is this for?",
    itemPlaceholder: "Course, university semester, bootcamp...",
    providerLabel: "School, provider, or lender",
    providerPlaceholder: "School, bank, course provider",
    totalLabel: "Tuition or course amount",
    upfrontLabel: "Upfront payment today",
    assetEligible: false,
  },
  {
    value: "SERVICE_CONTRACT",
    label: "Service contract",
    helper: "A service agreement paid over scheduled payments.",
    category: "",
    itemQuestion: "What service are you paying over time?",
    itemPlaceholder: "Medical service, repair plan, setup contract...",
    providerLabel: "Service provider",
    providerPlaceholder: "Company, clinic, provider",
    totalLabel: "Contract amount",
    upfrontLabel: "Upfront payment today",
    assetEligible: false,
  },
  {
    value: "OTHER",
    label: "Other scheduled payment",
    helper: "Use this when none of the other payment plan types fit.",
    category: "",
    itemQuestion: "What is this payment plan for?",
    itemPlaceholder: "Describe the obligation...",
    providerLabel: "Provider",
    providerPlaceholder: "Who is owed?",
    totalLabel: "Total amount",
    upfrontLabel: "Upfront payment today",
    assetEligible: false,
  },
];

const FREQUENCY_OPTIONS = [
  { value: "WEEKLY", label: "Weekly" },
  { value: "BIWEEKLY", label: "Biweekly" },
  { value: "MONTHLY", label: "Monthly" },
  { value: "QUARTERLY", label: "Quarterly" },
  { value: "YEARLY", label: "Yearly" },
];

function activeWallets(wallets = []) {
  return wallets.filter((wallet) => wallet.is_active !== false);
}

function remainingForPayment(payment) {
  return Math.max(0, Number(payment?.amount || 0) - Number(payment?.paid_amount || 0) - Number(payment?.written_off_amount || 0));
}

function writtenOffForPayment(payment) {
  return Math.max(0, Number(payment?.written_off_amount || 0));
}

function sortedPayments(payments = []) {
  return [...payments].sort((a, b) => `${a.due_date}-${a.id}`.localeCompare(`${b.due_date}-${b.id}`));
}

function unpaidPayments(plan) {
  return sortedPayments(plan?.payments || []).filter((payment) => payment.status !== "PAID" && payment.status !== "SKIPPED" && remainingForPayment(payment) > 0);
}

function isPristinePaymentPlan(plan) {
  return sortedPayments(plan?.payments || []).every((payment) => (
    Number(payment?.paid_amount || 0) === 0
    && Number(payment?.written_off_amount || 0) === 0
    && !payment?.event_id
    && !payment?.payment_plan_ledger_entry_id
    && !payment?.payment_plan_charge_id
    && (payment?.component_type || "PRINCIPAL") === "PRINCIPAL"
    && !(payment?.allocations || []).length
  ));
}

const LOCKED_SETUP_REASON = "Recorded activity prevents changing financial history.";
const LOCKED_DELETE_REASON = "Recorded activity prevents deleting this payment plan.";

function paymentStatusLabel(payment) {
  if (writtenOffForPayment(payment) > 0) return "WRITTEN OFF";
  return payment?.status || "PENDING";
}

function paymentStatusClass(payment) {
  if (writtenOffForPayment(payment) > 0) return "border-violet-500/30 bg-violet-500/10 text-violet-600 dark:text-violet-300";
  const status = payment?.status;
  if (status === "PAID") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300";
  if (status === "PARTIAL") return "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-300";
  if (status === "SKIPPED") return "border-muted bg-muted text-muted-foreground";
  return "border-border text-muted-foreground";
}

function paymentComponentLabel(payment) {
  return payment?.component_type === "CHARGE" ? "Fee or penalty" : "Scheduled payment";
}

function planStatusClass(status) {
  if (status === "PAID") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300";
  if (status === "ARCHIVED") return "border-muted bg-muted text-muted-foreground";
  return "border-primary/25 bg-primary/10 text-primary";
}

function frequencyLabel(frequency) {
  if (frequency === "BIWEEKLY") return "Biweekly";
  if (frequency === "QUARTERLY") return "Quarterly";
  if (frequency === "WEEKLY") return "Weekly";
  if (frequency === "YEARLY") return "Yearly";
  return "Monthly";
}

function paymentPlanTypeLabel(planType) {
  if (planType === "PRODUCT_FINANCING") return "Buy now, pay over time";
  return PAYMENT_PLAN_TYPES.find((type) => type.value === planType)?.label || "Payment plan";
}

function paymentPlanTypeConfig(planType) {
  if (planType === "PRODUCT_FINANCING") return PAYMENT_PLAN_TYPES[0];
  return PAYMENT_PLAN_TYPES.find((type) => type.value === planType) || PAYMENT_PLAN_TYPES[0];
}

function loanDisbursementWallets(wallets = []) {
  return activeWallets(wallets).filter((wallet) => (
    wallet.accounting_type === "ASSET"
    && ["CASH", "DEBIT", "SAVINGS"].includes(wallet.wallet_type)
  ));
}

function scheduledDueDate(startDate, frequency, index) {
  if (!startDate || !index) return "";
  const date = new Date(`${startDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "";
  if (frequency === "WEEKLY") date.setDate(date.getDate() + (7 * index));
  else if (frequency === "BIWEEKLY") date.setDate(date.getDate() + (14 * index));
  else if (frequency === "QUARTERLY") date.setMonth(date.getMonth() + (3 * index));
  else if (frequency === "YEARLY") date.setFullYear(date.getFullYear() + index);
  else date.setMonth(date.getMonth() + index);
  return date.toISOString().slice(0, 10);
}

function SummaryTile({ icon, label, value, helper, tone = "default" }) {
  const iconClassName = cn("h-4 w-4", tone === "success" && "text-emerald-500", tone === "danger" && "text-destructive", tone === "warn" && "text-amber-500");
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        {icon ? createElement(icon, { className: iconClassName }) : null}
      </div>
      <p className="mt-3 text-2xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{helper}</p>
    </div>
  );
}

function CreatePaymentPlanDialog({ open, onOpenChange, wallets }) {
  const mutation = useCreatePaymentPlanMutation();
  const previewMutation = usePreviewPaymentPlanScheduleMutation();
  const availableWallets = useMemo(() => activeWallets(wallets), [wallets]);
  const bankLoanWallets = useMemo(() => loanDisbursementWallets(wallets), [wallets]);
  const [step, setStep] = useState(1);
  const [previewData, setPreviewData] = useState(null);
  const [itemName, setItemName] = useState("");
  const [provider, setProvider] = useState("");
  const [planType, setPlanType] = useState("STORE_INSTALLMENT");
  const [totalPrice, setTotalPrice] = useState("");
  const [downPayment, setDownPayment] = useState("");
  const [paymentCount, setPaymentCount] = useState("12");
  const [frequency, setFrequency] = useState("MONTHLY");
  const [startDate, setStartDate] = useState(toISODateInTimeZone());
  const [category, setCategory] = useState("");
  const [trackAsset, setTrackAsset] = useState(false);
  const [assetValue, setAssetValue] = useState("");
  const [loanReceived, setLoanReceived] = useState(false);
  const [loanDisbursementWalletId, setLoanDisbursementWalletId] = useState("");
  const [walletAllocations, setWalletAllocations] = useState(() => defaultWalletAllocation(availableWallets));
  const [error, setError] = useState("");
  const defaultWalletId = availableWallets.find((wallet) => wallet.is_default)?.id || availableWallets[0]?.id;

  const config = paymentPlanTypeConfig(planType);
  const isBankLoan = planType === "BANK_LOAN";
  const isAssetEligible = Boolean(config.assetEligible);
  const totalSteps = isAssetEligible ? 6 : 5;
  const totalValue = parseAmountInput(totalPrice);
  const downValue = isBankLoan ? 0 : parseAmountInput(downPayment);
  const financedAmount = Math.max(totalValue - downValue, 0);
  const paymentCountValue = Number(paymentCount || 0);
  const regularPayment = paymentCountValue > 0 ? Math.floor(financedAmount / paymentCountValue) : 0;
  const finalDueDate = scheduledDueDate(startDate, frequency, Math.max(paymentCountValue - 1, 0));
  const needsWallet = downValue > 0;
  const allocationTotal = walletAllocationTotal(walletAllocations);
  const stepProgress = Math.round((step / totalSteps) * 100);

  useEffect(() => {
    if (!open || !defaultWalletId) return;
    setWalletAllocations((rows) => (rows.some((row) => row.wallet_id) ? rows : defaultWalletAllocation(availableWallets)));
  }, [open, defaultWalletId, availableWallets]);

  useEffect(() => {
    const suggestedCategory = paymentPlanTypeConfig(planType).category;
    if (suggestedCategory && !category) {
      setCategory(suggestedCategory);
    }
  }, [planType, category]);

  useEffect(() => {
    if (!isAssetEligible) {
      setTrackAsset(false);
      setAssetValue("");
    }
    if (isBankLoan) {
      setDownPayment("");
    } else {
      setLoanReceived(false);
      setLoanDisbursementWalletId("");
    }
  }, [isAssetEligible, isBankLoan]);

  useEffect(() => {
    if (!loanReceived) {
      setLoanDisbursementWalletId("");
      return;
    }
    if (!loanDisbursementWalletId && bankLoanWallets[0]?.id) {
      setLoanDisbursementWalletId(String(bankLoanWallets[0].id));
    }
  }, [loanReceived, loanDisbursementWalletId, bankLoanWallets]);

  // Ticket 2: Call backend schedule preview when reaching the review step.
  // The preview contract is the source of truth for generated rows, totals,
  // and the final due date.  Client-side math is only a provisional hint.
  useEffect(() => {
    if (step !== totalSteps || !open || !totalValue || !paymentCountValue) {
      setPreviewData(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const result = await previewMutation.mutateAsync({
          plan_type: planType,
          total_price: totalValue,
          down_payment: downValue,
          months: paymentCountValue,
          frequency,
          start_date: startDate,
          expense_category: category || undefined,
          schedule_model: "FLAT_TOTAL",
        });
        if (!cancelled) setPreviewData(result);
      } catch {
        if (!cancelled) setPreviewData(null);
      }
    })();
    return () => { cancelled = true; };
  }, [step, totalSteps, open, totalValue, downValue, paymentCountValue, frequency, startDate, category, planType]);

  const resetForm = () => {
    setStep(1);
    setItemName("");
    setProvider("");
    setPlanType("STORE_INSTALLMENT");
    setTotalPrice("");
    setDownPayment("");
    setPaymentCount("12");
    setFrequency("MONTHLY");
    setStartDate(toISODateInTimeZone());
    setCategory("");
    setTrackAsset(false);
    setAssetValue("");
    setLoanReceived(false);
    setLoanDisbursementWalletId("");
    setWalletAllocations(defaultWalletAllocation(availableWallets));
    setPreviewData(null);
    setError("");
  };

  const handleOpenChange = (nextOpen) => {
    onOpenChange(nextOpen);
    if (!nextOpen) resetForm();
  };

  const validateStep = (targetStep = step) => {
    if (targetStep === 1 && !planType) return "Choose what kind of payment plan this is.";
    if (targetStep === 2) {
      if (!itemName.trim()) return isBankLoan ? "Describe what this loan is for." : "Tell Sarflog what you received.";
      if (!category) return "Choose the real category for reports and budgets.";
    }
    if (targetStep === 3) {
      if (totalValue <= 0) return `${config.totalLabel} is required.`;
      if (!isBankLoan && downValue > totalValue) return "Upfront payment cannot exceed the total amount.";
      if (needsWallet && allocationTotal !== downValue) return "Wallet allocation must equal the upfront payment.";
      if (isBankLoan && loanReceived && !loanDisbursementWalletId) return "Choose which cash, debit, or savings wallet received the bank loan.";
    }
    if (targetStep === 4) {
      if (paymentCountValue <= 0) return "Number of payments must be greater than zero.";
      if (!startDate) return "Choose the first payment due date.";
      if (startDate < MIN_SUPPORTED_USER_DATE) return "First payment due date cannot be before 2020-01-01.";
      if (financedAmount <= 0) return "The amount left to repay must be greater than zero.";
    }
    return "";
  };

  const goNext = () => {
    const validationMessage = validateStep();
    if (validationMessage) {
      setError(validationMessage);
      return;
    }
    setError("");
    setStep((current) => Math.min(totalSteps, current + 1));
  };

  const goBack = () => {
    setError("");
    setStep((current) => Math.max(1, current - 1));
  };

  const submit = async () => {
    setError("");
    for (let index = 1; index <= totalSteps - 1; index += 1) {
      const validationMessage = validateStep(index);
      if (validationMessage) {
        setStep(index);
        setError(validationMessage);
        return;
      }
    }

    try {
      await mutation.mutateAsync({
        item_name: itemName.trim(),
        store_or_bank_name: provider.trim() || null,
        plan_type: planType,
        total_price: totalValue,
        down_payment: downValue,
        months: Number(paymentCount),
        frequency,
        start_date: startDate,
        category,
        expense_category: category,
        track_as_asset: trackAsset,
        asset_current_value: trackAsset ? parseAmountInput(assetValue || totalPrice) : null,
        wallet_allocations: needsWallet ? normalizeWalletAllocations(walletAllocations) : [],
        loan_disbursement_wallet_id: isBankLoan && loanReceived ? Number(loanDisbursementWalletId) : null,
      });
      handleOpenChange(false);
    } catch (err) {
      setError(err?.message || "Failed to create payment plan.");
    }
  };

  const stepTitle = (() => {
    if (step === 1) return "What kind of payment plan is this?";
    if (step === 2) return isBankLoan ? "What is this loan for?" : "What did you receive?";
    if (step === 3) return "What money moved today?";
    if (step === 4) return "How will you repay it?";
    if (isAssetEligible && step === 5) return "Should Sarflog track the asset?";
    return "Review before creating";
  })();

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-5xl p-0">
        <DialogHeader>
          <div className="border-b border-border px-6 py-5">
            <DialogTitle>Create payment plan</DialogTitle>
            <DialogDescription>Step {step} of {totalSteps}: {stepTitle}</DialogDescription>
            <Progress value={stepProgress} className="mt-4 h-2 bg-muted" />
          </div>
        </DialogHeader>

        <div className="max-h-[calc(100vh-13rem)] overflow-y-auto px-6 py-5">
          {step === 1 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {PAYMENT_PLAN_TYPES.map((type) => (
                <button
                  type="button"
                  key={type.value}
                  onClick={() => {
                    setPlanType(type.value);
                    setCategory(type.category || "");
                    setError("");
                  }}
                  className={cn(
                    "rounded-lg border p-4 text-left transition-colors hover:border-primary/50",
                    planType === type.value ? "border-primary bg-primary/10" : "border-border bg-card"
                  )}
                >
                  <p className="font-semibold">{type.label}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{type.helper}</p>
                </button>
              ))}
            </div>
          ) : null}

          {step === 2 ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1 md:col-span-2">
                <Label>{config.itemQuestion}</Label>
                <Input
                  value={itemName}
                  onChange={(event) => setItemName(event.target.value)}
                  placeholder={config.itemPlaceholder}
                  className="h-11 rounded-md text-base"
                />
              </div>
              <div className="space-y-1">
                <Label>{config.providerLabel}</Label>
                <Input
                  value={provider}
                  onChange={(event) => setProvider(event.target.value)}
                  placeholder={config.providerPlaceholder}
                  className="h-11 rounded-md text-base"
                />
              </div>
              <div className="space-y-1">
                <Label>Category</Label>
                <Select value={category || undefined} onValueChange={setCategory}>
                  <SelectTrigger className="h-11 rounded-md text-base"><SelectValue placeholder="Choose the real category" /></SelectTrigger>
                  <SelectContent>
                    {SPENDING_CATEGORIES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">Plan type explains financing. Category explains what life area this affects.</p>
              </div>
            </div>
          ) : null}

          {step === 3 ? (
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1">
                  <Label>{config.totalLabel}</Label>
                  <Input
                    value={totalPrice}
                    onChange={(event) => setTotalPrice(formatAmountInput(event.target.value, 15))}
                    inputMode="numeric"
                    className="h-11 rounded-md text-base"
                  />
                </div>
                {!isBankLoan ? (
                  <div className="space-y-1">
                    <Label>{config.upfrontLabel}</Label>
                    <Input
                      value={downPayment}
                      onChange={(event) => setDownPayment(formatAmountInput(event.target.value, 15))}
                      inputMode="numeric"
                      placeholder="0"
                      className="h-11 rounded-md text-base"
                    />
                  </div>
                ) : null}
              </div>

              {isBankLoan ? (
                <div className="rounded-lg border border-border bg-muted/15 p-4">
                  <p className="font-semibold">Did the bank already send this money to you?</p>
                  <p className="mt-1 text-sm text-muted-foreground">If yes, Sarflog records borrowed money entering a wallet. It is not income.</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <Button
                      type="button"
                      variant={loanReceived ? "default" : "outline"}
                      className="h-auto justify-start rounded-md p-4 text-left"
                      onClick={() => setLoanReceived(true)}
                    >
                      Yes, money entered my wallet
                    </Button>
                    <Button
                      type="button"
                      variant={!loanReceived ? "default" : "outline"}
                      className="h-auto justify-start rounded-md p-4 text-left"
                      onClick={() => setLoanReceived(false)}
                    >
                      No, just create the obligation
                    </Button>
                  </div>
                  {loanReceived ? (
                    <div className="mt-4 space-y-1">
                      <Label>Receiving wallet</Label>
                      <Select value={loanDisbursementWalletId || undefined} onValueChange={setLoanDisbursementWalletId}>
                        <SelectTrigger className="h-11 rounded-md text-base"><SelectValue placeholder="Choose cash, debit, or savings" /></SelectTrigger>
                        <SelectContent>
                          {bankLoanWallets.map((wallet) => (
                            <SelectItem key={wallet.id} value={String(wallet.id)}>
                              {wallet.name} / {wallet.wallet_type} / balance {formatUzs(wallet.current_balance ?? wallet.balance ?? 0)} UZS
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <p className="text-xs text-muted-foreground">Cash, debit, and savings wallets are allowed. Credit cards are borrowed capacity, not a receiving wallet for loan cash.</p>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {needsWallet ? (
                <WalletAllocationEditor
                  wallets={availableWallets}
                  rows={walletAllocations}
                  onChange={setWalletAllocations}
                  expectedAmount={downValue}
                  disabled={mutation.isPending}
                  title="Upfront payment wallets"
                  description="Only the upfront payment moves wallet money today."
                />
              ) : null}

              <div className="rounded-lg border border-border bg-card p-4">
                <p className="text-sm font-semibold">Amount left to repay</p>
                <p className="mt-2 text-2xl font-semibold tabular-nums">{formatUzs(financedAmount)} UZS</p>
                <p className="mt-1 text-xs text-muted-foreground">This becomes the plan-owned balance.</p>
              </div>
            </div>
          ) : null}

          {step === 4 ? (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_260px]">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-1">
                  <Label>Number of payments</Label>
                  <Input
                    value={paymentCount}
                    onChange={(event) => setPaymentCount(event.target.value.replace(/\D/g, ""))}
                    inputMode="numeric"
                    className="h-11 rounded-md text-base"
                  />
                </div>
                <div className="space-y-1">
                  <Label>Frequency</Label>
                  <Select value={frequency} onValueChange={setFrequency}>
                    <SelectTrigger className="h-11 rounded-md text-base"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {FREQUENCY_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>First payment due</Label>
                  <Input type="date" min={MIN_SUPPORTED_USER_DATE} value={startDate} onChange={(event) => setStartDate(event.target.value)} className="h-11 rounded-md text-base" />
                </div>
              </div>
              <div className="rounded-lg border border-border bg-muted/15 p-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">Calculated payment</p>
                <p className="mt-2 text-2xl font-semibold">{formatUzs(regularPayment)} UZS</p>
                <p className="mt-1 text-xs text-muted-foreground">Last row absorbs any rounding remainder.</p>
                <div className="mt-4 rounded-md border border-border bg-background p-3">
                  <p className="text-xs text-muted-foreground">Final due date</p>
                  <p className="mt-1 font-semibold">{finalDueDate ? formatDisplayDate(finalDueDate, "en") : "Not calculated yet"}</p>
                </div>
              </div>
            </div>
          ) : null}

          {isAssetEligible && step === 5 ? (
            <div className="rounded-lg border border-border bg-muted/15 p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-lg font-semibold">{config.assetQuestion}</p>
                  <p className="mt-1 text-sm text-muted-foreground">Use this for property, vehicles, or items you want to see later in Assets.</p>
                </div>
                <Switch checked={trackAsset} onCheckedChange={setTrackAsset} />
              </div>
              {trackAsset ? (
                <div className="mt-4 space-y-1">
                  <Label>Current asset value</Label>
                  <Input
                    value={assetValue}
                    onChange={(event) => setAssetValue(formatAmountInput(event.target.value, 15))}
                    placeholder={totalPrice || "0"}
                    className="h-11 rounded-md text-base"
                  />
                  <p className="text-xs text-muted-foreground">If left blank, Sarflog uses the total price.</p>
                </div>
              ) : null}
            </div>
          ) : null}

          {step === totalSteps ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-primary/20 bg-primary/10 p-4">
                <p className="text-lg font-semibold">Sarflog will create this payment plan</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {previewData
                    ? "Backend schedule preview confirms this plan. Review before saving."
                    : "Check this summary before the database is updated."}
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <SummaryTile icon={ReceiptText} label="Plan" value={paymentPlanTypeLabel(planType)} helper={itemName || "No item yet"} />
                <SummaryTile
                  icon={CreditCard}
                  label="Debt balance"
                  value={`${formatUzs(previewData?.total_to_pay ?? financedAmount)} UZS`}
                  helper={`${previewData?.payment_count ?? paymentCountValue || 0} ${frequencyLabel(previewData?.frequency ?? frequency).toLowerCase()} payments`}
                  tone="danger"
                />
                <SummaryTile icon={WalletCards} label="Money today" value={isBankLoan && loanReceived ? `${formatUzs(totalValue)} UZS in` : `${formatUzs(downValue)} UZS out`} helper={isBankLoan ? "Loan disbursement is borrowed money, not income" : "Only upfront payment moves today"} />
                <SummaryTile icon={Layers3} label="Category" value={category || "Not chosen"} helper={provider || "No provider"} />
              </div>
              {previewData?.rows?.length > 0 ? (
                <div className="rounded-lg border border-border bg-card p-4 text-sm">
                  <p className="font-semibold text-foreground">Generated schedule (backend preview)</p>
                  <div className="mt-2 max-h-48 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-border text-muted-foreground">
                          <th className="py-1 font-medium">Due</th>
                          <th className="py-1 font-medium">Principal</th>
                          <th className="py-1 font-medium">Charge</th>
                          <th className="py-1 font-medium">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.rows.map((row, i) => (
                          <tr key={i} className="border-b border-border/50">
                            <td className="py-1">{formatDisplayDate(row.due_date, "en")}</td>
                            <td className="py-1 tabular-nums">{formatUzs(row.principal_amount || row.amount || 0)}</td>
                            <td className="py-1 tabular-nums">{formatUzs(row.charge_amount || 0)}</td>
                            <td className="py-1 tabular-nums font-medium">{formatUzs((row.principal_amount || row.amount || 0) + (row.charge_amount || 0))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Total: {formatUzs(previewData.total_to_pay ?? 0)} UZS
                    {previewData.total_charges > 0 ? ` (${formatUzs(previewData.total_charges)} UZS charges)` : ""}
                    {" · "}Final due: {previewData.final_due_date ? formatDisplayDate(previewData.final_due_date, "en") : "N/A"}
                  </p>
                </div>
              ) : (
                <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
                  <p className="font-semibold text-foreground">Records created</p>
                  <ul className="mt-2 space-y-1">
                    <li>Plan-owned balance starts at {formatUzs(financedAmount)} UZS.</li>
                    <li>{paymentCountValue || 0} scheduled payment rows are generated from {startDate ? formatDisplayDate(startDate, "en") : "the first due date"}.</li>
                    {isBankLoan && loanReceived ? <li>Wallet receives {formatUzs(totalValue)} UZS as loan_disbursement.</li> : null}
                    {!isBankLoan && needsWallet ? <li>Upfront payment records {formatUzs(downValue)} UZS from selected wallet(s).</li> : null}
                    {trackAsset ? <li>Asset record is created for {itemName || "this item"}.</li> : null}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {error ? <p className="px-6 text-sm font-medium text-destructive">{error}</p> : null}
        <DialogFooter className="border-t border-border px-6 py-4">
          <Button variant="outline" className="rounded-md" onClick={() => handleOpenChange(false)}>Cancel</Button>
          {step > 1 ? (
            <Button variant="outline" className="rounded-md" onClick={goBack}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          ) : null}
          {step < totalSteps ? (
            <Button className="rounded-md" onClick={goNext}>
              Next
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button className="rounded-md" onClick={submit} disabled={mutation.isPending}>
              Create payment plan
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditPaymentPlanDialog({ plan, open, onOpenChange }) {
  const mutation = useUpdatePaymentPlanMutation();
  const [itemName, setItemName] = useState("");
  const [provider, setProvider] = useState("");
  const [category, setCategory] = useState("");
  const [totalPrice, setTotalPrice] = useState("");
  const [downPayment, setDownPayment] = useState("");
  const [paymentCount, setPaymentCount] = useState("");
  const [frequency, setFrequency] = useState("MONTHLY");
  const [startDate, setStartDate] = useState("");
  const [error, setError] = useState("");

  const isPristine = isPristinePaymentPlan(plan);
  const isArchived = plan?.status === "ARCHIVED";
  const config = paymentPlanTypeConfig(plan?.plan_type);
  const isBankLoan = plan?.plan_type === "BANK_LOAN";
  const totalValue = parseAmountInput(totalPrice);
  const downValue = isBankLoan ? 0 : parseAmountInput(downPayment);
  const paymentCountValue = Number(paymentCount || 0);
  const financedAmount = Math.max(totalValue - downValue, 0);
  const regularPayment = paymentCountValue > 0 ? Math.floor(financedAmount / paymentCountValue) : 0;
  const finalDueDate = scheduledDueDate(startDate, frequency, Math.max(paymentCountValue - 1, 0));

  useEffect(() => {
    if (!open || !plan) return;
    setItemName(plan.item_name || "");
    setProvider(plan.store_or_bank_name || "");
    setCategory(plan.expense_category || "");
    setTotalPrice(formatAmountInput(String(plan.total_price || ""), 15));
    setDownPayment(formatAmountInput(String(plan.down_payment || 0), 15));
    setPaymentCount(String(plan.months || plan.payment_count || ""));
    setFrequency(plan.frequency || "MONTHLY");
    setStartDate(plan.start_date || "");
    setError("");
  }, [open, plan]);

  const submit = async () => {
    if (!plan?.id || mutation.isPending) return;
    if (isArchived) {
      setError("Archived payment plans cannot be edited.");
      return;
    }
    if (!itemName.trim()) {
      setError("Name is required.");
      return;
    }
    if (!category) {
      setError("Choose the real category for reports and budgets.");
      return;
    }
    const payload = {
      item_name: itemName.trim(),
      store_or_bank_name: provider.trim() || null,
      expense_category: category,
    };
    if (isPristine) {
      if (totalValue <= 0) {
        setError(`${config.totalLabel} is required.`);
        return;
      }
      if (downValue > totalValue) {
        setError("Upfront payment cannot exceed the total amount.");
        return;
      }
      if (paymentCountValue <= 0) {
        setError("Number of payments must be greater than zero.");
        return;
      }
      if (!startDate) {
        setError("Choose the first payment due date.");
        return;
      }
      if (startDate < MIN_SUPPORTED_USER_DATE) {
        setError("First payment due date cannot be before 2020-01-01.");
        return;
      }
      if (financedAmount <= 0) {
        setError("The amount left to repay must be greater than zero.");
        return;
      }
      Object.assign(payload, {
        total_price: totalValue,
        down_payment: downValue,
        months: paymentCountValue,
        frequency,
        start_date: startDate,
      });
    }

    setError("");
    await mutation.mutateAsync({ planId: plan.id, payload });
    onOpenChange(false);
  };

  if (!plan) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl p-0">
        <DialogHeader className="border-b border-border px-6 py-5">
          <DialogTitle>Edit payment plan</DialogTitle>
          <DialogDescription>{plan.item_name} - plan-owned schedule</DialogDescription>
        </DialogHeader>

        <div className="max-h-[calc(100vh-13rem)] overflow-y-auto px-6 py-5">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1 md:col-span-2">
              <Label>{config.itemQuestion}</Label>
              <Input
                value={itemName}
                onChange={(event) => setItemName(event.target.value)}
                className="h-11 rounded-md text-base"
                disabled={isArchived || mutation.isPending}
              />
            </div>
            <div className="space-y-1">
              <Label>{config.providerLabel}</Label>
              <Input
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
                className="h-11 rounded-md text-base"
                disabled={isArchived || mutation.isPending}
              />
            </div>
            <div className="space-y-1">
              <Label>Category</Label>
              <Select value={category || undefined} onValueChange={setCategory} disabled={isArchived || mutation.isPending}>
                <SelectTrigger className="h-11 rounded-md text-base"><SelectValue placeholder="Choose the real category" /></SelectTrigger>
                <SelectContent>
                  {SPENDING_CATEGORIES.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="mt-5 rounded-lg border border-border bg-muted/15 p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <p className="font-semibold">Financial setup</p>
              {!isPristine ? (
                <Badge variant="outline" className="w-fit rounded-md border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300">
                  Locked
                </Badge>
              ) : null}
            </div>
            {!isPristine ? (
              <p className="mt-2 text-sm text-muted-foreground">{LOCKED_SETUP_REASON}</p>
            ) : null}

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div className="space-y-1">
                <Label>{config.totalLabel}</Label>
                <Input
                  value={totalPrice}
                  onChange={(event) => setTotalPrice(formatAmountInput(event.target.value, 15))}
                  inputMode="numeric"
                  className="h-11 rounded-md text-base"
                  disabled={!isPristine || isArchived || mutation.isPending}
                />
              </div>
              {!isBankLoan ? (
                <div className="space-y-1">
                  <Label>{config.upfrontLabel || "Down payment"}</Label>
                  <Input
                    value={downPayment}
                    onChange={(event) => setDownPayment(formatAmountInput(event.target.value, 15))}
                    inputMode="numeric"
                    className="h-11 rounded-md text-base"
                    disabled={!isPristine || isArchived || mutation.isPending}
                  />
                </div>
              ) : null}
              <div className="space-y-1">
                <Label>Number of payments</Label>
                <Input
                  value={paymentCount}
                  onChange={(event) => setPaymentCount(event.target.value.replace(/\D/g, ""))}
                  inputMode="numeric"
                  className="h-11 rounded-md text-base"
                  disabled={!isPristine || isArchived || mutation.isPending}
                />
              </div>
              <div className="space-y-1">
                <Label>Frequency</Label>
                <Select value={frequency} onValueChange={setFrequency} disabled={!isPristine || isArchived || mutation.isPending}>
                  <SelectTrigger className="h-11 rounded-md text-base"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FREQUENCY_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>First payment due</Label>
                <Input
                  type="date"
                  min={MIN_SUPPORTED_USER_DATE}
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  className="h-11 rounded-md text-base"
                  disabled={!isPristine || isArchived || mutation.isPending}
                />
              </div>
              <div className="rounded-md border border-border bg-background p-3">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Projected payment</p>
                <p className="mt-1 text-xl font-semibold tabular-nums">{formatUzs(regularPayment)} UZS</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {finalDueDate ? `Final due ${formatDisplayDate(finalDueDate, "en")}` : "Final due date not calculated"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {error ? <p className="px-6 text-sm font-medium text-destructive">{error}</p> : null}
        <DialogFooter className="border-t border-border px-6 py-4">
          <Button variant="outline" className="rounded-md" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>Cancel</Button>
          <Button className="rounded-md" onClick={submit} disabled={isArchived || mutation.isPending}>
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PaymentDialog({ plan, wallets, open, onOpenChange, preselectWalletId }) {
  const mutation = useRecordPaymentPlanPaymentMutation();
  const availableWallets = useMemo(() => activeWallets(wallets), [wallets]);
  const nextPayment = unpaidPayments(plan)[0];
  const defaultAmount = nextPayment
    ? remainingForPayment(nextPayment)
    : Math.min(Number(plan?.remaining_amount || 0), Number(plan?.regular_payment_amount || plan?.monthly_payment_amount || 0));
  const [paidDate, setPaidDate] = useState(toISODateInTimeZone());
  const [note, setNote] = useState("");
  const [walletAllocations, setWalletAllocations] = useState(() => defaultWalletAllocation(availableWallets));

  const allocationTotal = walletAllocationTotal(walletAllocations);
  const canSubmit = plan?.id && allocationTotal > 0 && allocationTotal <= Number(plan.remaining_amount || 0) && !mutation.isPending;

  useEffect(() => {
    if (!open) return;
    const defaultAmountText = defaultAmount ? formatAmountInput(String(defaultAmount), 15) : "";
    setPaidDate(toISODateInTimeZone());
    setNote("");
    setWalletAllocations(
      preselectWalletId
        ? [{ wallet_id: String(preselectWalletId), amount: defaultAmountText }]
        : defaultWalletAllocation(availableWallets, defaultAmountText)
    );
  }, [open, plan?.id, defaultAmount, preselectWalletId, availableWallets]);

  const submit = async () => {
    if (!canSubmit) return;
    await mutation.mutateAsync({
      planId: plan.id,
      payload: {
        amount: allocationTotal,
        paid_date: paidDate,
        note: note || null,
        wallet_allocations: normalizeWalletAllocations(walletAllocations),
      },
    });
    onOpenChange(false);
  };

  if (!plan) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-5xl p-0">
        <DialogHeader className="border-b border-border px-6 py-5">
          <DialogTitle>Record payment plan payment</DialogTitle>
          <DialogDescription>{plan.item_name} - remaining {formatUzs(plan.remaining_amount)} UZS</DialogDescription>
        </DialogHeader>

        <div className="max-h-[calc(100vh-14rem)] overflow-y-auto px-6 py-5">
          <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_210px]">
          <div className="space-y-1">
            <Label>Amount</Label>
            <Input
              value={`${formatUzs(allocationTotal)} UZS`}
              readOnly
              className="h-11 rounded-md text-base"
            />
            <p className="text-xs text-muted-foreground">This total is calculated from the wallet rows below.</p>
          </div>
          <div className="space-y-1">
            <Label>Paid date</Label>
            <Input type="date" value={paidDate} onChange={(event) => setPaidDate(event.target.value)} className="h-11 rounded-md text-base" />
          </div>
          <div className="md:col-span-2">
            <WalletAllocationEditor
              wallets={availableWallets}
              rows={walletAllocations}
              onChange={setWalletAllocations}
              expectedAmount={allocationTotal}
              disabled={mutation.isPending}
              requireExact={false}
            />
          </div>
          <div className="space-y-1 md:col-span-2">
            <Label>Note</Label>
            <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Receipt, provider note, confirmation..." className="min-h-24 rounded-md" />
          </div>
          </div>
        </div>

        <DialogFooter className="border-t border-border px-6 py-4">
          <Button variant="outline" className="rounded-md" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="h-11 rounded-md" disabled={!canSubmit} onClick={submit}>
            <WalletCards className="mr-2 h-4 w-4" />
            Record payment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ChargeDialog({ plan, open, onOpenChange }) {
  const mutation = useAddPaymentPlanChargeMutation();
  const [chargeType, setChargeType] = useState("FEE");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(toISODateInTimeZone());
  const [note, setNote] = useState("");
  const amountValue = parseAmountInput(amount);

  const submit = async () => {
    if (!plan?.id || amountValue <= 0) return;
    await mutation.mutateAsync({
      planId: plan.id,
      payload: {
        charge_type: chargeType,
        amount: amountValue,
        date,
        note: note || null,
      },
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Add payment plan charge</DialogTitle>
          <DialogDescription>Fees and penalties increase the plan-owned balance. The user pays them later through the schedule.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1">
            <Label>Type</Label>
            <Select value={chargeType} onValueChange={setChargeType}>
              <SelectTrigger className="rounded-md"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="FEE">Fee</SelectItem>
                <SelectItem value="PENALTY">Penalty</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Date</Label>
            <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} className="rounded-md" />
          </div>
          <div className="space-y-1 md:col-span-2">
            <Label>Amount</Label>
            <Input value={amount} onChange={(event) => setAmount(formatAmountInput(event.target.value, 15))} inputMode="numeric" className="rounded-md" />
          </div>
          <div className="space-y-1 md:col-span-2">
            <Label>Note</Label>
            <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Late fee, service fee, contract penalty..." className="min-h-20 rounded-md" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" className="rounded-md" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="rounded-md" disabled={amountValue <= 0 || mutation.isPending} onClick={submit}>
            Add charge
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PaymentPlanDetailsDialog({ plan, open, onOpenChange, onPay, onCharge, onEdit, onDelete }) {
  const { t } = useTranslation();
  const detailsQuery = usePaymentPlanDetailsQuery(plan?.id, { enabled: open && !!plan?.id });
  const writeOffMutation = useWriteOffPaymentPlanPaymentMutation();
  const undoWriteOffMutation = useUndoPaymentPlanPaymentWriteOffMutation();
  const undoLatestPaymentMutation = useUndoLatestPaymentPlanPaymentMutation();
  const details = detailsQuery.data;
  const currentPlan = details?.plan || plan;
  const payments = sortedPayments(currentPlan?.payments || []);
  const isPristine = isPristinePaymentPlan(currentPlan);
  const isArchived = currentPlan?.status === "ARCHIVED";

  if (!currentPlan) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-6xl p-0">
        <DialogHeader className="border-b border-border px-5 py-4">
          <DialogTitle className="flex items-center gap-2">
            <ReceiptText className="h-5 w-5 text-primary" />
            {currentPlan.item_name}
          </DialogTitle>
          <DialogDescription>{currentPlan.store_or_bank_name || "No provider"} - plan-owned schedule</DialogDescription>
        </DialogHeader>
        <div className="grid max-h-[calc(100vh-9rem)] overflow-hidden lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="overflow-y-auto p-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryTile icon={CreditCard} label="Remaining" value={`${formatUzs(currentPlan.remaining_amount)} UZS`} helper="Plan-owned balance" tone="danger" />
              <SummaryTile icon={Layers3} label="Rows" value={payments.length} helper="Scheduled obligations" />
              <SummaryTile icon={ShieldCheck} label="Status" value={currentPlan.status} helper="Schedule only" tone="success" />
            </div>

            <div className="mt-5 rounded-lg border border-border">
              <div className="grid grid-cols-[1fr_120px_100px_40px] gap-3 border-b border-border bg-muted/20 p-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <span>Due date</span>
                <span>Amount</span>
                <span>Status</span>
                <span className="text-right"></span>
              </div>
              <div className="divide-y divide-border">
                {payments.map((payment) => (
                  <div key={payment.id} className="grid grid-cols-[1fr_120px_100px_40px] items-center gap-3 p-3 text-sm">
                    <div>
                      <p className="font-medium">{formatDisplayDate(payment.due_date, "en")}</p>
                      <p className="text-xs text-muted-foreground">
                        Paid {formatUzs(payment.paid_amount || 0)} / {formatUzs(payment.amount)} UZS
                      </p>
                      {writtenOffForPayment(payment) > 0 && (
                        <p className="text-xs text-violet-600 dark:text-violet-300">
                          Written off {formatUzs(payment.written_off_amount)} UZS
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">{paymentComponentLabel(payment)}</p>
                    </div>
                    <span className="font-semibold tabular-nums">{formatUzs(remainingForPayment(payment))}</span>
                    <Badge variant="outline" className={cn("rounded-md", paymentStatusClass(payment))}>{paymentStatusLabel(payment)}</Badge>
                    <div className="text-right">
                      {payment.status === "PENDING" || payment.status === "PARTIAL" || payment.status === "PAID" ? (
                        <>
                          {payment.status !== "PAID" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-destructive"
                              title="Forgive / Write-off"
                              onClick={() => writeOffMutation.mutateAsync(payment.id)}
                              disabled={writeOffMutation.isPending || undoWriteOffMutation.isPending}
                            >
                              <ShieldAlert className="h-4 w-4" />
                            </Button>
                          )}
                          {payment.status === "PAID" && writtenOffForPayment(payment) > 0 && payment.payment_plan_ledger_entry_id && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-primary"
                              title="Undo Write-off"
                              onClick={() => undoWriteOffMutation.mutateAsync(payment.id)}
                              disabled={writeOffMutation.isPending || undoWriteOffMutation.isPending}
                            >
                              <RotateCcw className="h-4 w-4" />
                            </Button>
                          )}
                        </>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <aside className="overflow-y-auto border-t border-border bg-muted/10 p-5 lg:border-l lg:border-t-0">
            <div className="space-y-2">
              <Button className="w-full justify-start rounded-md" disabled={currentPlan.status === "PAID"} onClick={() => onPay(currentPlan)}>
                <WalletCards className="mr-2 h-4 w-4" />
                Record payment
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start rounded-md"
                disabled={undoLatestPaymentMutation.isPending}
                title={t("debts.reversal.undoPaymentWarning", {
                  defaultValue: "This will restore app wallet money only when the real payment failed, was cancelled, refunded, or was recorded by mistake.",
                })}
                onClick={() => {
                  const confirmed = window.confirm(t("debts.reversal.undoPaymentWarning", {
                    defaultValue: "This will restore app wallet money only when the real payment failed, was cancelled, refunded, or was recorded by mistake.",
                  }));
                  if (!confirmed) return;
                  undoLatestPaymentMutation.mutate(currentPlan.id);
                }}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                {t("debts.reversal.undoLatestPayment", { defaultValue: "Undo latest payment" })}
              </Button>
              <Button variant="outline" className="w-full justify-start rounded-md" onClick={() => onCharge(currentPlan)}>
                <Plus className="mr-2 h-4 w-4" />
                Add fee or penalty
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start rounded-md"
                disabled={isArchived}
                onClick={() => onEdit(currentPlan)}
              >
                <Edit2 className="mr-2 h-4 w-4" />
                Edit plan
              </Button>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="block">
                      <Button
                        variant="outline"
                        className="w-full justify-start rounded-md text-destructive hover:text-destructive"
                        disabled={!isPristine || isArchived}
                        onClick={() => onDelete(currentPlan)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete plan
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!isPristine || isArchived ? (
                    <TooltipContent>{isArchived ? "Archived payment plans cannot be deleted here." : LOCKED_DELETE_REASON}</TooltipContent>
                  ) : null}
                </Tooltip>
              </TooltipProvider>
            </div>

            <div className="mt-5">
              <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Plan activity</p>
              <p className="text-sm text-muted-foreground">Plan-owned payments, charges, write-offs, and undo entries appear in the schedule storyline.</p>
            </div>
          </aside>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function PaymentPlanCard({ plan, onOpen, onPay, onCharge, onEdit, onDelete }) {
  const payments = sortedPayments(plan.payments || []);
  const unpaid = unpaidPayments(plan);
  const nextPayment = unpaid[0];
  const totalAmount = Number(plan.total_price || 0);
  const remainingAmount = Number(plan.remaining_amount || 0);
  const paidAmount = Math.max(totalAmount - remainingAmount, 0);
  const progress = totalAmount > 0 ? Math.min(100, Math.round((paidAmount / totalAmount) * 100)) : 0;
  const paidRows = payments.filter((payment) => payment.status === "PAID").length;
  const today = toISODateInTimeZone();
  const overdueCount = unpaid.filter((payment) => payment.due_date < today).length;
  const nextAmount = nextPayment ? remainingForPayment(nextPayment) : 0;
  const isPristine = isPristinePaymentPlan(plan);
  const isArchived = Boolean(plan.archived_at);
  const lifecycleLabel = plan.lifecycle_status === "CLOSED" ? "Closed" : "Open";
  const timeStatusLabel = plan.time_status === "OVERDUE" ? "Overdue" : plan.time_status === "ON_TRACK" ? "On Track" : null;

  return (
    <Card className={cn("overflow-hidden rounded-lg border-border py-0 shadow-none transition-colors hover:border-primary/35", isArchived && "opacity-70")}>
      <CardContent className="p-0">
        <div className="grid xl:grid-cols-[minmax(220px,0.9fr)_minmax(380px,1.25fr)_minmax(240px,0.75fr)]">
          <section className="min-w-0 border-b border-border p-5 xl:border-b-0 xl:border-r">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-primary/20 bg-primary/10 text-primary">
                <ReceiptText className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <p className="max-w-full truncate text-lg font-semibold leading-6">{plan.item_name}</p>
                  {isArchived && (
                    <Badge variant="secondary" className="h-6 rounded-md px-2 text-[11px]">Archived</Badge>
                  )}
                  {!isArchived && (
                    <Badge variant="outline" className={cn("h-6 rounded-md px-2 text-[11px]", plan.lifecycle_status === "CLOSED" ? "border-green-300 bg-green-50 text-green-700" : "border-blue-300 bg-blue-50 text-blue-700")}>
                      {lifecycleLabel}
                    </Badge>
                  )}
                  {timeStatusLabel && !isArchived && (
                    <Badge variant="outline" className={cn("h-6 rounded-md px-2 text-[11px]", plan.time_status === "OVERDUE" ? "border-red-300 bg-red-50 text-red-700" : "border-emerald-300 bg-emerald-50 text-emerald-700")}>
                      {timeStatusLabel}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 truncate text-sm text-muted-foreground">
                  {plan.store_or_bank_name || "No provider"} - started {formatDisplayDate(plan.start_date, "en")}
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge variant="outline" className="rounded-md border-border bg-muted/20 text-xs font-medium text-muted-foreground">
                    {paymentPlanTypeLabel(plan.plan_type)}
                  </Badge>
                  <Badge variant="outline" className="rounded-md border-border bg-muted/20 text-xs font-medium text-muted-foreground">
                    {frequencyLabel(plan.frequency)}
                  </Badge>
                  <Badge variant="outline" className="rounded-md border-border bg-muted/20 text-xs font-medium text-muted-foreground">
                    {payments.length} rows
                  </Badge>
                  {overdueCount > 0 ? (
                    <Badge variant="destructive" className="rounded-md text-xs font-medium">
                      {overdueCount} overdue
                    </Badge>
                  ) : null}
                </div>
              </div>
            </div>
          </section>

          <section className="border-b border-border p-5 xl:border-b-0">
            <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_120px] sm:items-start">
              <div className="min-w-0">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Remaining balance</p>
                <p className="mt-1 break-words text-2xl font-semibold leading-tight tabular-nums sm:text-3xl">
                  {formatUzs(remainingAmount)} <span className="text-sm font-semibold text-muted-foreground">UZS</span>
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Paid {formatUzs(paidAmount)} of {formatUzs(totalAmount)} UZS
                </p>
              </div>
              <div className="rounded-md border border-border bg-muted/15 p-3 sm:text-right">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Progress</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums">{progress}%</p>
              </div>
            </div>

            <div className="mt-4 space-y-2">
              <Progress value={progress} className="h-2.5 bg-muted" indicatorClassName={(plan.lifecycle_status === "CLOSED") ? "bg-emerald-500" : "bg-primary"} />
              <div className="grid gap-px overflow-hidden rounded-md border border-border bg-border text-sm sm:grid-cols-3">
                <div className="bg-background p-3">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Schedule</p>
                  <p className="mt-1 font-semibold tabular-nums">{paidRows}/{payments.length} rows</p>
                </div>
                <div className="bg-background p-3">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{frequencyLabel(plan.frequency)} plan</p>
                  <p className="mt-1 font-semibold tabular-nums">{formatUzs(plan.regular_payment_amount || plan.monthly_payment_amount)} UZS</p>
                </div>
                <div className="bg-background p-3">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Open rows</p>
                  <p className="mt-1 font-semibold tabular-nums">{unpaid.length}</p>
                </div>
              </div>
            </div>
          </section>

          <aside className="flex min-h-full flex-col justify-between bg-muted/10 p-5">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Next payment</p>
              <p className={cn("mt-2 text-xl font-semibold leading-6", overdueCount > 0 && "text-destructive")}>
                {nextPayment ? formatDisplayDate(nextPayment.due_date, "en") : "No payment due"}
              </p>
              <p className="mt-2 text-lg font-semibold tabular-nums">
                {formatUzs(nextAmount)} <span className="text-xs font-semibold text-muted-foreground">UZS</span>
              </p>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-2">
              <Button variant="outline" className="h-10 rounded-md" onClick={() => onOpen(plan)}>
                <Eye className="h-4 w-4" />
                Open
              </Button>
              <Button className="h-10 rounded-md" disabled={!nextPayment || (plan.lifecycle_status === "CLOSED")} onClick={() => onPay(plan)}>
                <WalletCards className="h-4 w-4" />
                Pay
              </Button>
              <Button variant="outline" className="h-10 rounded-md" disabled={isArchived} onClick={() => onEdit(plan)}>
                <Edit2 className="h-4 w-4" />
                Edit
              </Button>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="block">
                      <Button
                        variant="outline"
                        className="h-10 w-full rounded-md text-destructive hover:text-destructive"
                        disabled={!isPristine || isArchived}
                        onClick={() => onDelete(plan)}
                      >
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {!isPristine || isArchived ? (
                    <TooltipContent>{isArchived ? "Archived payment plans cannot be deleted here." : LOCKED_DELETE_REASON}</TooltipContent>
                  ) : null}
                </Tooltip>
              </TooltipProvider>
              <Button variant="ghost" className="col-span-2 h-10 rounded-md border border-border bg-background/60" disabled={isArchived} onClick={() => onCharge(plan)}>
                <Plus className="h-4 w-4" />
                Charge
              </Button>
              {isArchived ? (
                <Button variant="outline" className="col-span-2 h-10 rounded-md" onClick={() => onRestore(plan)}>
                  <RotateCcw className="h-4 w-4" />
                  Restore
                </Button>
              ) : (
                <Button variant="ghost" className="col-span-2 h-10 rounded-md border border-border bg-background/60" onClick={() => onArchive(plan)}>
                  <FileText className="h-4 w-4" />
                  Archive
                </Button>
              )}
            </div>
          </aside>
        </div>
      </CardContent>
    </Card>
  );
}

export function PaymentPlansTab() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [createOpen, setCreateOpen] = useState(false);
  const [detailsPlan, setDetailsPlan] = useState(null);
  const [paymentPlan, setPaymentPlan] = useState(null);
  const [preselectWalletId, setPreselectWalletId] = useState(null);
  const [chargePlan, setChargePlan] = useState(null);
  const [editPlan, setEditPlan] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const summaryQuery = usePaymentPlanSummaryQuery();
  const plansQuery = usePaymentPlansQuery({ limit: 100 });
  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const deleteMutation = useDeletePaymentPlanMutation();
  const archiveMutation = useArchivePaymentPlanMutation();
  const unarchiveMutation = useUnarchivePaymentPlanMutation();

  const [showArchived, setShowArchived] = useState(false);

  const wallets = useMemo(() => (Array.isArray(walletsQuery.data) ? walletsQuery.data : []), [walletsQuery.data]);
  const plans = useMemo(() => (Array.isArray(plansQuery.data?.items) ? plansQuery.data.items : []), [plansQuery.data]);
  const displayedPlans = useMemo(() => showArchived ? plans : plans.filter(p => !p.archived_at), [plans, showArchived]);
  const summary = summaryQuery.data || {};

  useEffect(() => {
    const payPlanId = searchParams.get("pay_plan");
    const walletId = searchParams.get("wallet");
    if (payPlanId && plans.length > 0) {
      const planToPay = plans.find((p) => String(p.id) === payPlanId);
      if (planToPay) {
        setPaymentPlan(planToPay);
        if (walletId) setPreselectWalletId(walletId);
        setSearchParams((prev) => {
          prev.delete("pay_plan");
          prev.delete("wallet");
          return prev;
        }, { replace: true });
      }
    }
  }, [searchParams, plans, setSearchParams]);

  const confirmDelete = async () => {
    if (!deleteTarget?.id || !isPristinePaymentPlan(deleteTarget)) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    if (detailsPlan?.id === deleteTarget.id) setDetailsPlan(null);
    setDeleteTarget(null);
  };

  const handleArchive = async (plan) => {
    await archiveMutation.mutateAsync(plan.id);
    if (detailsPlan?.id === plan.id) setDetailsPlan(null);
  };

  const handleRestore = async (plan) => {
    await unarchiveMutation.mutateAsync(plan.id);
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <SummaryTile icon={CalendarClock} label="Upcoming" value={summary.pending_count || 0} helper={`${formatUzs(summary.pending_amount || 0)} UZS pending`} tone="warn" />
        <SummaryTile icon={CheckCircle2} label="Paid this month" value={summary.paid_count || 0} helper={`${formatUzs(summary.paid_amount || 0)} UZS paid`} tone="success" />
        <SummaryTile icon={CreditCard} label="Overdue" value={summary.overdue_count || 0} helper={`${formatUzs(summary.overdue_amount || 0)} UZS overdue`} tone="danger" />
        <div className="rounded-lg border border-primary/20 bg-primary/10 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Create</p>
          <p className="mt-3 text-sm text-muted-foreground">Contract first, payments later.</p>
          <Button className="mt-4 w-full rounded-md" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New payment plan
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <Label htmlFor="show-archived-filter" className="text-sm text-muted-foreground">Show archived</Label>
          <Switch id="show-archived-filter" checked={showArchived} onCheckedChange={setShowArchived} />
        </div>
      </div>

      <div className="space-y-3">
        {displayedPlans.map((plan) => (
          <PaymentPlanCard
            key={plan.id}
            plan={plan}
            onOpen={setDetailsPlan}
            onPay={setPaymentPlan}
            onCharge={setChargePlan}
            onEdit={setEditPlan}
            onDelete={setDeleteTarget}
            onArchive={handleArchive}
            onRestore={handleRestore}
          />
        ))}
        {!displayedPlans.length && !plansQuery.isLoading ? (
          <Card className="rounded-lg border-dashed py-0 shadow-none">
            <CardContent className="flex min-h-64 flex-col items-center justify-center gap-3 p-8 text-center">
              <FileText className="h-10 w-10 text-muted-foreground" />
              <div>
                <p className="font-semibold">No payment plans yet</p>
                <p className="text-sm text-muted-foreground">Create a plan for a phone, appliance, course, or store-financed purchase.</p>
              </div>
              <Button className="rounded-md" onClick={() => setCreateOpen(true)}>Create first payment plan</Button>
            </CardContent>
          </Card>
        ) : null}
      </div>

      <CreatePaymentPlanDialog open={createOpen} onOpenChange={setCreateOpen} wallets={wallets} />
      <EditPaymentPlanDialog open={!!editPlan} onOpenChange={(open) => !open && setEditPlan(null)} plan={editPlan} />
      <PaymentDialog open={!!paymentPlan} onOpenChange={(open) => { if (!open) { setPaymentPlan(null); setPreselectWalletId(null); } }} plan={paymentPlan} wallets={wallets} preselectWalletId={preselectWalletId} />
      <ChargeDialog open={!!chargePlan} onOpenChange={(open) => !open && setChargePlan(null)} plan={chargePlan} />
      <PaymentPlanDetailsDialog
        open={!!detailsPlan}
        onOpenChange={(open) => !open && setDetailsPlan(null)}
        plan={detailsPlan}
        onPay={setPaymentPlan}
        onCharge={setChargePlan}
        onEdit={setEditPlan}
        onDelete={setDeleteTarget}
      />
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete payment plan"
        description={deleteTarget ? `Delete ${deleteTarget.item_name}? This is only allowed before any recorded plan activity exists.` : ""}
        confirmText="Delete"
        cancelText="Cancel"
        isConfirming={deleteMutation.isPending}
        confirmDisabled={!deleteTarget || !isPristinePaymentPlan(deleteTarget)}
        onConfirm={confirmDelete}
      >
        {deleteTarget && !isPristinePaymentPlan(deleteTarget) ? (
          <p className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-300">
            {LOCKED_DELETE_REASON}
          </p>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}
