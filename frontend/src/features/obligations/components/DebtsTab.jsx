import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDownLeft,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Archive,
  Banknote,
  Building2,
  CalendarDays,
  HandCoins,
  Landmark,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  UserRound,
  WalletCards,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SPENDING_CATEGORIES } from "@/lib/category";
import { getIncomeSources, getWallets } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatAmountInput, formatDisplayDate, formatUzs, parseAmountInput } from "@/lib/format";
import { toISODateInTimeZone } from "@/lib/date";
import { useArchiveDebtMutation, useCreateDebtMutation, useDeleteDebtMutation, usePayWalletBackedObligationMutation, useRestoreDebtMutation } from "../hooks/useDebtsMutations";
import { useDebtsQuery, useDebtsSummaryQuery } from "../hooks/useDebtsQueries";
import { DebtDetailsDialog } from "./DebtDetailsDialog";
import { EditDebtModal } from "./EditDebtModal";
import { MIN_SUPPORTED_USER_DATE } from "../obligationSchemas";
import {
  defaultWalletAllocation,
  normalizeWalletAllocations,
  WalletAllocationEditor,
  walletAllocationTotal,
} from "./WalletAllocationEditor";

const STATUS_OPTIONS = [
  { value: "OPEN", label: "Open" },
  { value: "CLOSED", label: "Closed" },
  { value: "OVERDUE", label: "Overdue" },
  { value: "ARCHIVED", label: "Archived" },
];
const DEBT_REASON_OPTIONS = {
  OWING: {
    PERSONAL: [
      {
        id: "PERSONAL_BORROWED",
        title: "I borrowed money",
        description: "Money entered your wallet, and you need to return it later.",
        icon: Banknote,
        origin_kind: "CASH_BORROWED",
        counterparty_kind: "PERSON",
        product_kind: "INFORMAL_DEBT",
        moneyMoved: true,
      },
      {
        id: "PERSONAL_DEFERRED_EXPENSE",
        title: "Someone paid for me",
        description: "No wallet changed now. This is something you need to pay back later.",
        icon: HandCoins,
        origin_kind: "DEFERRED_EXPENSE",
        counterparty_kind: "PERSON",
        product_kind: "INFORMAL_DEBT",
        moneyMoved: false,
        requiresExpenseCategory: true,
      },
      {
        id: "PERSONAL_DAMAGE_OWING",
        title: "I damaged or lost something",
        description: "No wallet changed now. You need to compensate someone later.",
        icon: ShieldAlert,
        origin_kind: "DAMAGE_COMPENSATION",
        counterparty_kind: "PERSON",
        product_kind: "PERSONAL_REIMBURSEMENT",
        moneyMoved: false,
        requiresExpenseCategory: true,
      },
    ],
    FORMAL: [
      {
        id: "FORMAL_BORROWED",
        title: "Bank or lender gave me money",
        description: "Borrowed money entered your wallet. It is not income.",
        icon: Landmark,
        origin_kind: "CASH_BORROWED",
        counterparty_kind: "BANK",
        product_kind: "BANK_LOAN",
        moneyMoved: true,
      },
      {
        id: "FORMAL_DEFERRED_EXPENSE",
        title: "Company or provider billed me",
        description: "No wallet changed now. You will pay this formal bill later.",
        icon: Building2,
        origin_kind: "DEFERRED_EXPENSE",
        counterparty_kind: "COMPANY",
        product_kind: "OTHER",
        moneyMoved: false,
        requiresExpenseCategory: true,
      },
      {
        id: "FORMAL_DAMAGE_OWING",
        title: "I damaged company property",
        description: "Rental, provider, venue, store, or company damage compensation.",
        icon: ShieldAlert,
        origin_kind: "DAMAGE_COMPENSATION",
        counterparty_kind: "COMPANY",
        product_kind: "OTHER",
        moneyMoved: false,
        requiresExpenseCategory: true,
      },
    ],
  },
  OWED: {
    PERSONAL: [
      {
        id: "PERSONAL_LENT",
        title: "I lent money",
        description: "Money left your wallet, and they need to return it.",
        icon: Banknote,
        origin_kind: "CASH_LENT",
        counterparty_kind: "PERSON",
        product_kind: "INFORMAL_DEBT",
        moneyMoved: true,
      },
      {
        id: "PERSONAL_UNPAID_INCOME",
        title: "They owe me for work or income",
        description: "No wallet changed now. You earned money that has not arrived yet.",
        icon: HandCoins,
        origin_kind: "RECEIVABLE_INCOME",
        counterparty_kind: "PERSON",
        product_kind: "CLIENT_RECEIVABLE",
        moneyMoved: false,
        requiresIncomeSource: true,
      },
      {
        id: "PERSONAL_DAMAGE_OWED",
        title: "They damaged or lost something of mine",
        description: "No wallet changed now. They owe compensation, not income.",
        icon: ShieldAlert,
        origin_kind: "DAMAGE_COMPENSATION",
        counterparty_kind: "PERSON",
        product_kind: "PERSONAL_REIMBURSEMENT",
        moneyMoved: false,
      },
    ],
    FORMAL: [
      {
        id: "FORMAL_LENT",
        title: "I formally lent money",
        description: "Money left your wallet under an agreement, and they need to return it.",
        icon: Landmark,
        origin_kind: "CASH_LENT",
        counterparty_kind: "COMPANY",
        product_kind: "OTHER",
        moneyMoved: true,
      },
      {
        id: "FORMAL_UNPAID_INCOME",
        title: "Company or client owes me",
        description: "No wallet changed now. This is unpaid invoice or contract income.",
        icon: Building2,
        origin_kind: "RECEIVABLE_INCOME",
        counterparty_kind: "COMPANY",
        product_kind: "CLIENT_RECEIVABLE",
        moneyMoved: false,
        requiresIncomeSource: true,
      },
      {
        id: "FORMAL_DAMAGE_OWED",
        title: "Company damaged my property",
        description: "Courier, provider, venue, or company owes compensation for damage or loss.",
        icon: ShieldAlert,
        origin_kind: "DAMAGE_COMPENSATION",
        counterparty_kind: "COMPANY",
        product_kind: "OTHER",
        moneyMoved: false,
      },
    ],
  },
};

function debtReasonOptions(direction, relationship) {
  return DEBT_REASON_OPTIONS[direction]?.[relationship] || [];
}

function activeArray(data) {
  return Array.isArray(data) ? data.filter((item) => item.is_active !== false) : [];
}

function kindIcon(debt) {
  if (debt.counterparty_kind === "BANK" || debt.product_kind === "BANK_LOAN") return Landmark;
  if (debt.counterparty_kind === "COMPANY" || debt.counterparty_kind === "STORE") return Building2;
  return UserRound;
}

function statusTone(debt) {
  if (debt.is_archived) return "muted";
  if (debt.lifecycle_status === "CLOSED" || Number(debt.remaining_amount || 0) <= 0) return "success";
  if (debt.time_status === "OVERDUE") return "danger";
  return "default";
}

function debtStatusLabel(debt) {
  if (debt.is_archived) return "Archived";
  if (debt.lifecycle_status === "CLOSED" || Number(debt.remaining_amount || 0) <= 0) return "Closed";
  if (debt.time_status === "OVERDUE") return "Overdue";
  return "Open";
}

function StatusBadge({ debt }) {
  const tone = statusTone(debt);
  return (
    <Badge
      variant={tone === "default" ? "default" : "outline"}
      className={cn(
        "rounded-md",
        tone === "success" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-300",
        tone === "danger" && "border-destructive/30 bg-destructive/10 text-destructive",
        tone === "info" && "border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-300",
        tone === "muted" && "text-muted-foreground"
      )}
    >
      {debtStatusLabel(debt)}
    </Badge>
  );
}

function SummaryTile({ icon: Icon, label, value, helper, tone = "default" }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        <Icon className={cn("h-4 w-4", tone === "danger" && "text-destructive", tone === "success" && "text-emerald-500", tone === "info" && "text-sky-500")} />
      </div>
      <p className="mt-3 text-2xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{helper}</p>
    </div>
  );
}

function DebtCreationDialog({ open, onOpenChange, wallets, incomeSources }) {
  const createMutation = useCreateDebtMutation();
  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState("OWING");
  const [relationship, setRelationship] = useState("PERSONAL");
  const [reasonId, setReasonId] = useState("PERSONAL_BORROWED");
  const [counterpartyName, setCounterpartyName] = useState("");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(toISODateInTimeZone());
  const [dueDate, setDueDate] = useState("");
  const [walletAllocations, setWalletAllocations] = useState(() => defaultWalletAllocation(activeArray(wallets)));
  const [expenseCategory, setExpenseCategory] = useState("");
  const [incomeSourceId, setIncomeSourceId] = useState("");
  const [error, setError] = useState("");

  const activeWallets = activeArray(wallets);
  const activeIncomeSources = activeArray(incomeSources);
  const reasonOptions = debtReasonOptions(direction, relationship);
  const selectedReason = reasonOptions.find((item) => item.id === reasonId) || reasonOptions[0];
  const moneyMoved = Boolean(selectedReason?.moneyMoved);
  const totalSteps = 6;
  const amountValue = parseAmountInput(amount);
  const walletTotal = walletAllocationTotal(walletAllocations);
  const debtAmount = moneyMoved ? walletTotal : amountValue;
  const defaultWalletId = activeWallets.find((wallet) => wallet.is_default)?.id || activeWallets[0]?.id;
  const stepProgress = Math.round((step / totalSteps) * 100);

  useEffect(() => {
    const nextOptions = debtReasonOptions(direction, relationship);
    if (!nextOptions.some((item) => item.id === reasonId)) {
      setReasonId(nextOptions[0]?.id || "");
    }
  }, [direction, relationship, reasonId]);

  useEffect(() => {
    if (!open || !defaultWalletId) return;
    setWalletAllocations((rows) => (rows.some((row) => row.wallet_id) ? rows : defaultWalletAllocation(activeWallets)));
  }, [open, defaultWalletId]);

  const resetForm = () => {
    setStep(1);
    setDirection("OWING");
    setRelationship("PERSONAL");
    setReasonId("PERSONAL_BORROWED");
    setCounterpartyName("");
    setTitle("");
    setAmount("");
    setDate(toISODateInTimeZone());
    setDueDate("");
    setWalletAllocations(defaultWalletAllocation(activeWallets));
    setExpenseCategory("");
    setIncomeSourceId("");
    setError("");
  };

  const handleOpenChange = (nextOpen) => {
    onOpenChange(nextOpen);
    if (!nextOpen) resetForm();
  };

  const dateError = () => {
    if (!date) return "Debt date is required.";
    if (date < MIN_SUPPORTED_USER_DATE) return "Date cannot be before 2020-01-01.";
    if (!dueDate) return "Due date is required.";
    if (dueDate < MIN_SUPPORTED_USER_DATE) return "Due date cannot be before 2020-01-01.";
    if (dueDate && date && dueDate < date) return "Expected date cannot be before the debt date.";
    return "";
  };

  const validateStep = (targetStep = step) => {
    if (targetStep === 1 && !direction) return "Choose who owes money.";
    if (targetStep === 2 && !relationship) return "Choose whether this is personal or formal.";
    if (targetStep === 3 && !selectedReason) return "Choose what created this debt.";
    if (targetStep === 4) {
      if (!counterpartyName.trim()) return direction === "OWING" ? "Tell Sarflog who you owe." : "Tell Sarflog who owes you.";
      if (moneyMoved && debtAmount <= 0) return "Add the wallet amount that moved.";
      if (!moneyMoved && debtAmount <= 0) return "Enter the amount owed.";
      if (selectedReason?.requiresExpenseCategory && !expenseCategory) return "Choose what this debt is really for.";
      if (selectedReason?.requiresIncomeSource && !incomeSourceId) return "Choose the income source this belongs to.";
    }
    if (targetStep === 5) return dateError();
    return "";
  };

  const goNext = () => {
    const message = validateStep();
    if (message) {
      setError(message);
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
      const message = validateStep(index);
      if (message) {
        setStep(index);
        setError(message);
        return;
      }
    }

    const normalizedWalletAllocations = moneyMoved ? normalizeWalletAllocations(walletAllocations) : [];
    const payload = {
      debt_type: direction,
      counterparty_name: counterpartyName.trim(),
      description: title.trim() || null,
      initial_amount: debtAmount,
      currency: "UZS",
      date,
      expected_return_date: dueDate,
      is_money_transferred: moneyMoved,
      initial_wallet_id: normalizedWalletAllocations.length === 1 ? normalizedWalletAllocations[0].wallet_id : null,
      initial_wallet_allocations: normalizedWalletAllocations,
      origin_kind: selectedReason.origin_kind,
      counterparty_kind: selectedReason.counterparty_kind,
      product_kind: selectedReason.product_kind,
      expense_category: selectedReason.requiresExpenseCategory ? expenseCategory : null,
      income_source_id: selectedReason.requiresIncomeSource ? Number(incomeSourceId) : null,
    };

    try {
      await createMutation.mutateAsync(payload);
      handleOpenChange(false);
    } catch (err) {
      setError(err?.message || "Failed to create debt.");
    }
  };

  const stepTitle = (() => {
    if (step === 1) return "Who owes money?";
    if (step === 2) return "Is this personal or formal?";
    if (step === 3) return "What created this debt?";
    if (step === 4) return "What happened today?";
    if (step === 5) return "When should this be settled?";
    return "Review before creating";
  })();

  const moneyImpactText = (() => {
    if (!selectedReason) return "";
    if (moneyMoved && direction === "OWING") return `${formatUzs(debtAmount)} UZS will be added to selected wallet(s). This is borrowed money, not income.`;
    if (moneyMoved && direction === "OWED") return `${formatUzs(debtAmount)} UZS will leave selected wallet(s). They owe you this money back.`;
    if (selectedReason.requiresExpenseCategory) return "No wallet changes today. You will record the payment later.";
    if (selectedReason.requiresIncomeSource) return "No wallet changes today. You will record the income when it arrives.";
    return "No wallet changes today.";
  })();

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-5xl p-0">
        <DialogHeader>
          <div className="border-b border-border px-6 py-5">
            <DialogTitle>Create debt</DialogTitle>
            <DialogDescription>Step {step} of {totalSteps}: {stepTitle}</DialogDescription>
            <Progress value={stepProgress} className="mt-4 h-2 bg-muted" />
          </div>
        </DialogHeader>

        <div className="max-h-[calc(100vh-13rem)] overflow-y-auto px-6 py-5">
          {step === 1 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {[
                { id: "OWING", title: "I owe someone", description: "You need to pay someone back.", icon: ArrowUpRight },
                { id: "OWED", title: "Someone owes me", description: "Someone needs to pay you back.", icon: ArrowDownLeft },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setDirection(item.id);
                      setError("");
                    }}
                    className={cn("rounded-lg border p-5 text-left transition-colors hover:border-primary/50", direction === item.id ? "border-primary bg-primary/10" : "border-border bg-card")}
                  >
                    <Icon className="h-5 w-5 text-primary" />
                    <p className="mt-3 text-lg font-semibold">{item.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
                  </button>
                );
              })}
            </div>
          ) : null}

          {step === 2 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {[
                { id: "PERSONAL", title: "Personal", description: "Friend, relative, neighbor, coworker, or another person.", icon: UserRound },
                { id: "FORMAL", title: "Formal", description: "Bank, company, store, client, provider, or written agreement.", icon: Landmark },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setRelationship(item.id);
                      setError("");
                    }}
                    className={cn("rounded-lg border p-5 text-left transition-colors hover:border-primary/50", relationship === item.id ? "border-primary bg-primary/10" : "border-border bg-card")}
                  >
                    <Icon className="h-5 w-5 text-primary" />
                    <p className="mt-3 text-lg font-semibold">{item.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
                  </button>
                );
              })}
            </div>
          ) : null}

          {step === 3 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {reasonOptions.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setReasonId(item.id);
                      setError("");
                    }}
                    className={cn("rounded-lg border p-5 text-left transition-colors hover:border-primary/50", reasonId === item.id ? "border-primary bg-primary/10" : "border-border bg-card")}
                  >
                    <Icon className="h-5 w-5 text-primary" />
                    <p className="mt-3 font-semibold">{item.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
                  </button>
                );
              })}
            </div>
          ) : null}

          {step === 4 ? (
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1">
                  <Label>{direction === "OWING" ? "Who do you owe?" : "Who owes you?"}</Label>
                  <Input value={counterpartyName} onChange={(event) => setCounterpartyName(event.target.value)} placeholder={relationship === "FORMAL" ? "Bank, company, store, client..." : "Friend, relative, neighbor..."} className="h-11 rounded-md text-base" />
                </div>
                <div className="space-y-1">
                  <Label>What is this about?</Label>
                  <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Short note users will recognize later" className="h-11 rounded-md text-base" />
                </div>
                <div className="space-y-1">
                  <Label>Debt date</Label>
                  <Input type="date" min={MIN_SUPPORTED_USER_DATE} value={date} onChange={(event) => setDate(event.target.value)} className="h-11 rounded-md text-base" />
                </div>
                <div className="space-y-1">
                  <Label>Total debt amount</Label>
                  <Input
                    value={moneyMoved ? `${formatUzs(debtAmount)} UZS` : amount}
                    onChange={(event) => setAmount(formatAmountInput(event.target.value, 15))}
                    inputMode="numeric"
                    placeholder="0"
                    readOnly={moneyMoved}
                    className="h-11 rounded-md text-base"
                  />
                  <p className="text-xs text-muted-foreground">
                    {moneyMoved ? "This total is calculated from the wallet rows below." : "No wallet changed today, so enter the debt amount directly."}
                  </p>
                </div>
              </div>

              {moneyMoved ? (
                <WalletAllocationEditor
                  wallets={activeWallets}
                  rows={walletAllocations}
                  onChange={setWalletAllocations}
                  expectedAmount={debtAmount}
                  disabled={createMutation.isPending}
                  title={direction === "OWING" ? "Wallets that received borrowed money" : "Wallets that sent money"}
                  description={direction === "OWING" ? "The total debt amount is calculated from these wallet inflows." : "The total debt amount is calculated from these wallet outflows."}
                  requireExact={false}
                  checkBalance={direction === "OWED"}
                />
              ) : null}

              {selectedReason?.requiresExpenseCategory ? (
                <div className="space-y-1">
                  <Label>What was this for?</Label>
                  <Select value={expenseCategory || undefined} onValueChange={setExpenseCategory}>
                    <SelectTrigger className="h-11 rounded-md text-base"><SelectValue placeholder="Choose the real category" /></SelectTrigger>
                    <SelectContent>
                      {SPENDING_CATEGORIES.map((category) => <SelectItem key={category} value={category}>{category}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">Use the life area of the purchase, not the fact that it became debt.</p>
                </div>
              ) : null}

              {selectedReason?.requiresIncomeSource ? (
                <div className="space-y-1">
                  <Label>Income source</Label>
                  <Select value={incomeSourceId || undefined} onValueChange={setIncomeSourceId}>
                    <SelectTrigger className="h-11 rounded-md text-base"><SelectValue placeholder="Choose where this income belongs" /></SelectTrigger>
                    <SelectContent>
                      {activeIncomeSources.map((source) => <SelectItem key={source.id} value={String(source.id)}>{source.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              ) : null}
            </div>
          ) : null}

          {step === 5 ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1">
                <Label>
                  {direction === "OWING"
                    ? "When do you expect to settle this?"
                    : "When do you expect to receive this?"}
                </Label>
                <Input type="date" min={date || MIN_SUPPORTED_USER_DATE} value={dueDate} onChange={(event) => setDueDate(event.target.value)} className="h-11 rounded-md text-base" />
                <p className="text-xs text-muted-foreground">Required. It keeps debt reports and reminders predictable.</p>
              </div>
            </div>
          ) : null}

          {step === 6 ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-primary/20 bg-primary/10 p-4">
                <p className="text-lg font-semibold">Review this debt</p>
                <p className="mt-1 text-sm text-muted-foreground">Only confirm if this matches what happened in real life.</p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <SummaryTile icon={direction === "OWING" ? ArrowUpRight : ArrowDownLeft} label="Debt" value={direction === "OWING" ? "You owe" : "Owed to you"} helper={`${counterpartyName || "No name"} - ${formatUzs(debtAmount)} UZS`} />
                <SummaryTile icon={relationship === "FORMAL" ? Landmark : UserRound} label="Relationship" value={relationship === "FORMAL" ? "Formal" : "Personal"} helper={selectedReason?.title || "No reason chosen"} />
                <SummaryTile icon={WalletCards} label="Money today" value={moneyMoved ? `${formatUzs(debtAmount)} UZS` : "No wallet change"} helper={moneyImpactText} />
                <SummaryTile icon={CalendarDays} label="Expected date" value={formatDisplayDate(dueDate, "en")} helper={date ? `Debt date ${formatDisplayDate(date, "en")}` : "No debt date"} />
              </div>
              <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
                <p className="font-semibold text-foreground">What Sarflog will do</p>
                <ul className="mt-2 space-y-1">
                  <li>Create a debt for {formatUzs(debtAmount)} UZS.</li>
                  {moneyMoved ? <li>Update selected wallet balance(s) now.</li> : <li>Leave wallet balances unchanged today.</li>}
                  {selectedReason?.requiresExpenseCategory ? <li>Remember this as a {expenseCategory || "chosen"} cost you will pay later.</li> : null}
                  {selectedReason?.requiresIncomeSource ? <li>Remember this as income that has not arrived yet.</li> : null}
                </ul>
              </div>
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
            <Button className="rounded-md" onClick={submit} disabled={createMutation.isPending}>
              Create debt
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function WalletObligationPayoffDialog({ debt, wallets, open, onOpenChange }) {
  const payoffMutation = usePayWalletBackedObligationMutation();
  const activeWallets = activeArray(wallets);
  const sourceWallets = activeWallets.filter((wallet) => wallet.id !== debt?.wallet_id);
  const [fromWalletId, setFromWalletId] = useState("");
  const [amount, setAmount] = useState("");
  const [feeAmount, setFeeAmount] = useState("");
  const [feeWalletId, setFeeWalletId] = useState("");
  const amountValue = parseAmountInput(amount);
  const feeAmountValue = parseAmountInput(feeAmount);

  useEffect(() => {
    if (!open) return;
    const defaultSource = sourceWallets.find((wallet) => wallet.is_default) || sourceWallets[0];
    setFromWalletId(defaultSource ? String(defaultSource.id) : "");
    setFeeWalletId(defaultSource ? String(defaultSource.id) : "");
    setAmount(formatAmountInput(String(debt?.remaining_amount || ""), 15));
    setFeeAmount("");
  }, [open, debt?.id, debt?.remaining_amount, wallets]);

  const handleSubmit = async () => {
    if (!debt?.wallet_id || !fromWalletId || amountValue <= 0) return;
    await payoffMutation.mutateAsync({
      walletId: debt.wallet_id,
      payload: {
        from_wallet_id: Number(fromWalletId),
        amount: amountValue,
        fee_amount: feeAmountValue > 0 ? feeAmountValue : null,
        fee_wallet_id: feeAmountValue > 0 && feeWalletId ? Number(feeWalletId) : null,
        date: toISODateInTimeZone(),
      },
    });
    onOpenChange(false);
  };

  const title = debt?.wallet_type === "CREDIT" ? "Pay credit card" : "Cover overdraft";
  const isInvalid = !fromWalletId || amountValue <= 0 || amountValue > Number(debt?.remaining_amount || 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Move money into {debt?.wallet_name || debt?.counterparty_name} as a wallet transfer.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>From wallet</Label>
            <Select value={fromWalletId} onValueChange={setFromWalletId}>
              <SelectTrigger className="rounded-md"><SelectValue placeholder="Choose source wallet" /></SelectTrigger>
              <SelectContent>
                {sourceWallets.map((wallet) => (
                  <SelectItem key={wallet.id} value={String(wallet.id)}>
                    {wallet.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Payoff amount</Label>
            <Input
              value={amount}
              inputMode="numeric"
              onChange={(event) => setAmount(formatAmountInput(event.target.value, 15))}
              className="rounded-md"
            />
            {amountValue > Number(debt?.remaining_amount || 0) ? (
              <p className="text-xs text-destructive">Amount cannot exceed the wallet-backed obligation balance.</p>
            ) : null}
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Transfer fee</Label>
              <Input
                value={feeAmount}
                inputMode="numeric"
                placeholder="Optional"
                onChange={(event) => setFeeAmount(formatAmountInput(event.target.value, 15))}
                className="rounded-md"
              />
            </div>
            <div className="space-y-2">
              <Label>Fee wallet</Label>
              <Select value={feeWalletId} onValueChange={setFeeWalletId} disabled={feeAmountValue <= 0}>
                <SelectTrigger className="rounded-md"><SelectValue placeholder="Same as source" /></SelectTrigger>
                <SelectContent>
                  {activeWallets.map((wallet) => (
                    <SelectItem key={wallet.id} value={String(wallet.id)}>
                      {wallet.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" className="rounded-md" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button className="rounded-md" onClick={handleSubmit} disabled={isInvalid || payoffMutation.isPending}>
            Pay off
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DebtRow({ debt, onOpen, onEdit, onArchive, onRestore, onDelete, onPayoff, isRestoring }) {
  const Icon = kindIcon(debt);
  const total = Number(debt.initial_amount || 0) + Number(debt.total_charges || 0);
  const paid = debt.total_paid || 0;
  const progress = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;
  const isOwing = debt.debt_type === "OWING";
  const isWalletObligation = debt.source_type === "WALLET";
  const isArchived = debt.is_archived === true;
  const RowIcon = isWalletObligation ? WalletCards : Icon;

  return (
    <Card className="rounded-lg border-border py-0 shadow-none">
      <CardContent className="p-4">
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_160px_190px_150px_auto] xl:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cn("flex h-9 w-9 items-center justify-center rounded-md border", isOwing ? "border-destructive/20 bg-destructive/10 text-destructive" : "border-emerald-500/20 bg-emerald-500/10 text-emerald-500")}>
                <RowIcon className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <p className="truncate font-semibold">{debt.description || debt.counterparty_name}</p>
                <p className="truncate text-sm text-muted-foreground">
                  {isWalletObligation ? `${debt.wallet_name || debt.counterparty_name} - wallet-backed liability` : `${debt.counterparty_name} - ${debt.product_kind || debt.origin_kind}`}
                </p>
              </div>
            </div>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">{isOwing ? "I owe" : "Owed to me"}</p>
            <p className={cn("font-semibold tabular-nums", isOwing ? "text-destructive" : "text-emerald-500")}>{formatUzs(debt.remaining_amount)} UZS</p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>

          <div className="space-y-1">
            <StatusBadge debt={debt} />
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <CalendarDays className="h-3 w-3" />
              {debt.expected_return_date ? formatDisplayDate(debt.expected_return_date, "en") : "No due date"}
            </p>
          </div>

          <div className="flex gap-2 xl:justify-end">
            {isWalletObligation ? (
              <Button variant="outline" className="rounded-md" onClick={() => onPayoff(debt)}>Pay off</Button>
            ) : (
              <>
                <Button variant="outline" className="rounded-md" onClick={() => onOpen(debt)}>Open</Button>
                {isArchived ? (
                  <Button
                    variant="outline"
                    size="icon"
                    className="rounded-md"
                    title="Restore debt"
                    disabled={isRestoring}
                    onClick={() => onRestore(debt)}
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                ) : (
                  <>
                    <Button variant="ghost" size="icon" className="rounded-md" title="Edit debt" onClick={() => onEdit(debt)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="rounded-md text-muted-foreground" title="Archive debt" onClick={() => onArchive(debt)}>
                      <Archive className="h-4 w-4" />
                    </Button>
                  </>
                )}
                <Button variant="ghost" size="icon" className="rounded-md text-muted-foreground hover:text-destructive" onClick={() => onDelete(debt)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function DebtsTab() {
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedDebt, setSelectedDebt] = useState(null);
  const [editTarget, setEditTarget] = useState(null);
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [payoffTarget, setPayoffTarget] = useState(null);
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("OPEN");
  const [search, setSearch] = useState("");

  const summaryQuery = useDebtsSummaryQuery();
  const debtQueryParams = useMemo(() => {
    const params = {
      debt_type: typeFilter === "ALL" ? undefined : typeFilter,
      search: search || undefined,
      limit: 100,
    };
    if (statusFilter === "OPEN") {
      params.lifecycle_status = "OPEN";
    } else if (statusFilter === "CLOSED") {
      params.lifecycle_status = "CLOSED";
    } else if (statusFilter === "OVERDUE") {
      params.lifecycle_status = "OPEN";
      params.time_status = "OVERDUE";
    } else if (statusFilter === "ARCHIVED") {
      params.archived = true;
      params.include_archived = true;
    }
    return params;
  }, [search, statusFilter, typeFilter]);

  const debtsQuery = useDebtsQuery(debtQueryParams);
  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const incomeSourcesQuery = useQuery({ queryKey: ["incomeSources"], queryFn: getIncomeSources });
  const archiveMutation = useArchiveDebtMutation();
  const restoreMutation = useRestoreDebtMutation();
  const deleteMutation = useDeleteDebtMutation();

  const debts = Array.isArray(debtsQuery.data?.items) ? debtsQuery.data.items : [];
  const summary = summaryQuery.data || {};
  const formalCount = debts.filter((debt) => ["BANK_LOAN", "CAR_LOAN", "MORTGAGE", "STORE_INSTALLMENT", "SERVICE_PAY_LATER"].includes(debt.product_kind)).length;
  const riskCount = debts.filter((debt) => debt.time_status === "OVERDUE" && !debt.is_archived).length;
  const wallets = useMemo(() => (Array.isArray(walletsQuery.data) ? walletsQuery.data : []), [walletsQuery.data]);
  const incomeSources = useMemo(() => (Array.isArray(incomeSourcesQuery.data) ? incomeSourcesQuery.data : []), [incomeSourcesQuery.data]);

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  const confirmArchive = async () => {
    if (!archiveTarget) return;
    await archiveMutation.mutateAsync(archiveTarget.id);
    setArchiveTarget(null);
  };

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <SummaryTile icon={ArrowUpRight} label="I owe" value={`${formatUzs(summary.total_i_owe || 0)} UZS`} helper="Open payable balance" tone="danger" />
        <SummaryTile icon={ArrowDownLeft} label="Owed to me" value={`${formatUzs(summary.total_owed_to_me || 0)} UZS`} helper="Open receivable balance" tone="success" />
        <SummaryTile icon={ShieldCheck} label="Formal debts" value={formalCount} helper="Loans, payment plans, provider contracts" tone="info" />
        <div className="rounded-lg border border-primary/20 bg-primary/10 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Create</p>
          <p className="mt-3 text-sm text-muted-foreground">Question-led entry keeps the model clean.</p>
          <Button className="mt-4 w-full rounded-md" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New debt
          </Button>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_210px_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search counterparty or title" className="rounded-md pl-9" />
          </div>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="rounded-md"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All directions</SelectItem>
              <SelectItem value="OWING">I owe</SelectItem>
              <SelectItem value="OWED">Owed to me</SelectItem>
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="rounded-md"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All statuses</SelectItem>
              {STATUS_OPTIONS.map((status) => <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <Badge variant={riskCount ? "destructive" : "outline"} className="h-10 rounded-md px-3">
            {riskCount} risk items
          </Badge>
        </div>
      </div>

      <div className="space-y-3">
        {debts.map((debt) => (
          <DebtRow
            key={debt.id}
            debt={debt}
            onOpen={setSelectedDebt}
            onEdit={setEditTarget}
            onArchive={setArchiveTarget}
            onRestore={(item) => restoreMutation.mutate(item.id)}
            onDelete={setDeleteTarget}
            onPayoff={setPayoffTarget}
            isRestoring={restoreMutation.isPending}
          />
        ))}
        {!debts.length && !debtsQuery.isLoading ? (
          <Card className="rounded-lg border-dashed py-0 shadow-none">
            <CardHeader>
              <CardTitle className="text-base">No debts match this view</CardTitle>
            </CardHeader>
            <CardContent className="pb-6 text-sm text-muted-foreground">
              Change filters or create a new debt from the real-world event that created the obligation.
            </CardContent>
          </Card>
        ) : null}
      </div>

      <DebtCreationDialog open={createOpen} onOpenChange={setCreateOpen} wallets={wallets} incomeSources={incomeSources} />
      <WalletObligationPayoffDialog
        debt={payoffTarget}
        wallets={wallets}
        open={!!payoffTarget}
        onOpenChange={(open) => !open && setPayoffTarget(null)}
      />
      <DebtDetailsDialog debt={selectedDebt} open={!!selectedDebt} onOpenChange={(open) => !open && setSelectedDebt(null)} />
      <EditDebtModal isOpen={!!editTarget} onClose={() => setEditTarget(null)} debt={editTarget} />
      <ConfirmDialog
        open={!!archiveTarget}
        onOpenChange={(open) => !open && setArchiveTarget(null)}
        title="Archive debt"
        description={archiveTarget ? `Archive ${archiveTarget.description || archiveTarget.counterparty_name}? It will be hidden from the main debts view until restored.` : ""}
        confirmText="Archive"
        cancelText="Cancel"
        onConfirm={confirmArchive}
        isConfirming={archiveMutation.isPending}
      />
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete debt"
        description={deleteTarget ? `Delete ${deleteTarget.description || deleteTarget.counterparty_name}? This is only allowed when the backend can safely reverse linked effects.` : ""}
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={confirmDelete}
        isConfirming={deleteMutation.isPending}
      />
    </div>
  );
}
