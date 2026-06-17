import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import {
  ArrowDownToLine,
  BriefcaseBusiness,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Ban,
  CheckCircle2,
  Pencil,
  Landmark,
  PackageCheck,
  Plus,
  RotateCcw,
  Scale,
  Search,
  Trash2,
  Wallet,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import {
  createBudgetExpectedIncome,
  deleteBudgetExpectedIncome,
  getBudgetExpectedIncomes,
  getWallets,
  updateBudgetExpectedIncome,
} from "@/lib/api";
import { toISODateInTimeZone } from "@/lib/date";
import { useDebounce } from "@/hooks/useDebounce";
import {
  formatAmountInput,
  formatDisplayDate,
  formatDisplayDateTime,
  formatMonthYear,
  formatUzs,
  parseAmountInput,
} from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";
import { cn } from "@/lib/utils";
import { useToast } from "@/lib/context/ToastContext";
import { MAX_INCOME_AMOUNT, MAX_INCOME_NOTE_LENGTH } from "./incomeSchemas";
import { useIncomeSourcesQuery, useMoneyInQuery } from "./hooks/useIncomeQueries";
import { useCreateIncomeEntryMutation } from "./hooks/useIncomeMutations";

const PAGE_SIZE = 20;
const MAX_AMOUNT_DIGITS = String(MAX_INCOME_AMOUNT).length;

const KIND_OPTIONS = [
  { value: "all", label: "All" },
  { value: "income", label: "Income" },
  { value: "returned", label: "Returned" },
  { value: "borrowed", label: "Borrowed" },
  { value: "sold", label: "Sold" },
  { value: "adjustment", label: "Corrections" },
];

const MONEY_IN_TABS = [
  { value: "stream", label: "Money In" },
  { value: "expected", label: "Expected Income" },
];

const EXPECTED_STATUS_META = {
  EXPECTED: {
    label: "Expected",
    description: "Counts toward planning until the user changes it.",
    tone: "border-sky-500/25 bg-sky-500/10 text-sky-600 dark:text-sky-400",
  },
  RECEIVED: {
    label: "Received",
    description: "No longer counts as expected income.",
    tone: "border-emerald-500/25 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
  MISSED: {
    label: "Missed",
    description: "Removed from expected backing.",
    tone: "border-rose-500/25 bg-rose-500/10 text-rose-600 dark:text-rose-400",
  },
  CANCELLED: {
    label: "Cancelled",
    description: "Ignored for planning.",
    tone: "border-zinc-500/25 bg-zinc-500/10 text-zinc-600 dark:text-zinc-300",
  },
};

const parsePageParam = (value) => {
  const raw = String(value ?? "").trim();
  if (!raw) return 1;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
};

const parseTabParam = (value) => (
  MONEY_IN_TABS.some((option) => option.value === value) ? value : "stream"
);

const parseKindParam = (value) => {
  const raw = String(value || "all");
  return KIND_OPTIONS.some((option) => option.value === raw) ? raw : "all";
};

const KIND_META = {
  income: {
    label: "Income",
    description: "Earned money that supports your monthly plan.",
    icon: BriefcaseBusiness,
    tone: "border-emerald-500/25 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
  returned: {
    label: "Returned",
    description: "Money came back, but it is not new income.",
    icon: RotateCcw,
    tone: "border-sky-500/25 bg-sky-500/10 text-sky-600 dark:text-sky-400",
  },
  borrowed: {
    label: "Borrowed",
    description: "Cash entered a wallet and created an obligation.",
    icon: Landmark,
    tone: "border-amber-500/25 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  },
  sold: {
    label: "Sold",
    description: "Money from selling something you owned.",
    icon: PackageCheck,
    tone: "border-violet-500/25 bg-violet-500/10 text-violet-600 dark:text-violet-400",
  },
  adjustment: {
    label: "Correction",
    description: "A wallet balance correction or reconciliation.",
    icon: Scale,
    tone: "border-zinc-500/25 bg-zinc-500/10 text-zinc-600 dark:text-zinc-300",
  },
};

function activeWallets(wallets) {
  return (wallets || []).filter((wallet) => {
    const status = wallet.status || (wallet.is_active === false ? "ARCHIVED" : "ACTIVE");
    return status === "ACTIVE";
  });
}

function getKindMeta(kind) {
  return KIND_META[kind] || {
    label: "Money in",
    description: "Money entered one or more wallets.",
    icon: ArrowDownToLine,
    tone: "border-primary/25 bg-primary/10 text-primary",
  };
}

function getExpectedStatusMeta(status) {
  return EXPECTED_STATUS_META[status] || EXPECTED_STATUS_META.EXPECTED;
}

function currentMonthValue(todayISO) {
  return String(todayISO || toISODateInTimeZone()).slice(0, 7);
}

function parseMonthValue(value, fallbackISO = toISODateInTimeZone()) {
  const fallback = currentMonthValue(fallbackISO);
  const raw = /^\d{4}-\d{2}$/.test(String(value || "")) ? String(value) : fallback;
  const [year, month] = raw.split("-").map(Number);
  return { value: raw, year, month };
}

function getMonthBounds(monthValue) {
  const { year, month } = parseMonthValue(monthValue);
  const start = `${year}-${String(month).padStart(2, "0")}-01`;
  const end = new Date(year, month, 0);
  const endValue = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
  return { start, end: endValue };
}

function getDefaultDueDate(monthValue, todayISO) {
  const { start, end } = getMonthBounds(monthValue);
  if (todayISO >= start && todayISO <= end) return todayISO;
  return start;
}

function titleFor(item) {
  const title = String(item?.title || "").trim();
  if (title && title.toLowerCase() !== "income") return title;
  if (item?.source_name) return item.source_name;
  return getKindMeta(item?.kind).label;
}

function sourceFor(item) {
  if (item?.source_name) return item.source_name;
  if (item?.description) return item.description;
  if (item?.debt_id) return `Linked debt #${item.debt_id}`;
  if (item?.asset_id) return `Linked asset #${item.asset_id}`;
  return getKindMeta(item?.kind).description;
}

function walletSummary(wallets = []) {
  if (!wallets.length) return "No wallet details";
  if (wallets.length === 1) return wallets[0].wallet_name || "Wallet";
  if (wallets.length === 2) return `${wallets[0].wallet_name}, ${wallets[1].wallet_name}`;
  return `${wallets[0].wallet_name} + ${wallets.length - 1} wallets`;
}

function sumRows(rows) {
  return rows.reduce((total, row) => total + parseAmountInput(row.amount), 0);
}

function SummaryStat({ title, value, hint }) {
  return (
    <Card className="shadow-sm">
      <CardContent className="p-5">
        <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{title}</p>
        <div className="mt-2 text-2xl font-bold tracking-tight">{value}</div>
        {hint ? <p className="mt-1 text-sm text-muted-foreground">{hint}</p> : null}
      </CardContent>
    </Card>
  );
}

function MoneyInRow({ item, appLang, onOpen }) {
  const meta = getKindMeta(item.kind);
  const Icon = meta.icon;

  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      className="group w-full rounded-2xl border border-border/70 bg-background/70 p-4 text-left shadow-sm transition hover:border-primary/35 hover:bg-muted/25"
    >
      <div className="grid grid-cols-[auto_1fr_auto] items-start gap-4">
        <div className={cn("flex h-11 w-11 items-center justify-center rounded-2xl border", meta.tone)}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-base font-semibold tracking-tight">{titleFor(item)}</h3>
            <Badge className={cn("rounded-full border px-2.5 py-0.5", meta.tone)}>{meta.label}</Badge>
          </div>
          <p className="mt-1 truncate text-sm text-muted-foreground">
            {sourceFor(item)} / to {walletSummary(item.wallet_allocations)}
          </p>
          <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
            <CalendarDays className="h-3.5 w-3.5" />
            {formatDisplayDate(item.date, appLang)}
          </p>
        </div>
        <div className="min-w-[8rem] text-right">
          <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
            +{formatUzs(item.amount)} UZS
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {item.counts_as_income ? "Counts as income" : "Not income"}
          </p>
        </div>
      </div>
    </button>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/50 py-2 last:border-b-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="max-w-[62%] text-right text-sm font-medium">{value || "-"}</span>
    </div>
  );
}

function ExpectedIncomeRow({ item, appLang, onEdit, onDelete, onStatusChange, isUpdating }) {
  const meta = getExpectedStatusMeta(item.status);
  const sourceName = item.source?.name || "Source removed";
  const statusActions =
    item.status === "EXPECTED"
      ? [
          { status: "RECEIVED", label: "Received", icon: CheckCircle2, variant: "default" },
          { status: "MISSED", label: "Missed", icon: XCircle, variant: "outline" },
          { status: "CANCELLED", label: "Cancel", icon: Ban, variant: "outline" },
        ]
      : [
          { status: "EXPECTED", label: "Reopen", icon: RotateCcw, variant: "outline" },
        ];

  return (
    <div className="rounded-2xl border border-border/70 bg-background/75 p-4 shadow-sm">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-start">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-base font-semibold tracking-tight">{sourceName}</h3>
            <Badge className={cn("rounded-full border px-2.5 py-0.5", meta.tone)}>{meta.label}</Badge>
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
            <span>{formatDisplayDate(item.due_date, appLang)}</span>
            <span>/</span>
            <span>{meta.description}</span>
          </p>
          {item.note ? (
            <p className="mt-3 rounded-xl border border-border/50 bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
              {item.note}
            </p>
          ) : null}
        </div>

        <div className="flex flex-col gap-3 xl:min-w-[24rem] xl:items-end">
          <CurrencyAmount
            value={Number(item.amount || 0)}
            format="display"
            tooltip="compact"
            className="flex items-baseline gap-1 text-xl font-bold tracking-tight text-foreground xl:justify-end"
            currencyClassName="text-muted-foreground/70"
          />
          <div className="flex flex-wrap gap-2 xl:justify-end">
            {statusActions.map((action) => {
              const Icon = action.icon;
              return (
                <Button
                  key={action.status}
                  size="sm"
                  variant={action.variant}
                  className="rounded-2xl"
                  disabled={isUpdating}
                  onClick={() => onStatusChange(item, action.status)}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {action.label}
                </Button>
              );
            })}
            <Button size="icon" variant="ghost" className="rounded-2xl" onClick={() => onEdit(item)} disabled={isUpdating}>
              <Pencil className="h-4 w-4" />
              <span className="sr-only">Edit expected income</span>
            </Button>
            <Button size="icon" variant="ghost" className="rounded-2xl text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={() => onDelete(item)} disabled={isUpdating}>
              <Trash2 className="h-4 w-4" />
              <span className="sr-only">Delete expected income</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ExpectedIncomeDialog({
  open,
  onOpenChange,
  item,
  monthValue,
  sources,
  todayISO,
  appLang,
  onSubmit,
  isSubmitting,
}) {
  const mode = item ? "edit" : "create";
  const activeSources = useMemo(() => {
    const currentSourceId = Number(item?.source_id || 0);
    return (sources || []).filter((source) => source.is_active || source.id === currentSourceId);
  }, [item?.source_id, sources]);
  const { start, end } = useMemo(() => getMonthBounds(monthValue), [monthValue]);
  const [sourceId, setSourceId] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("EXPECTED");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setSourceId(item?.source_id ? String(item.source_id) : (activeSources[0]?.id ? String(activeSources[0].id) : ""));
    setAmount(item?.amount ? formatAmountInput(String(item.amount), MAX_AMOUNT_DIGITS) : "");
    setDueDate(item?.due_date || getDefaultDueDate(monthValue, todayISO));
    setNote(item?.note || "");
    setStatus(item?.status || "EXPECTED");
    setError("");
  }, [activeSources, item, monthValue, open, todayISO]);

  const amountValue = parseAmountInput(amount);
  const canSubmit =
    Boolean(sourceId) &&
    amountValue > 0 &&
    amountValue <= MAX_INCOME_AMOUNT &&
    dueDate >= start &&
    dueDate <= end &&
    !isSubmitting;

  const submit = async () => {
    setError("");
    if (!canSubmit) {
      setError("Choose a source, date, and positive amount inside the selected month.");
      return;
    }
    try {
      const { year, month } = parseMonthValue(monthValue);
      await onSubmit({
        source_id: Number(sourceId),
        amount: amountValue,
        due_date: dueDate,
        budget_year: year,
        budget_month: month,
        status,
        note: note.trim() || null,
      });
      onOpenChange(false);
    } catch (err) {
      setError(err?.message || "Expected income could not be saved.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? "Edit expected income" : "Add expected income"}</DialogTitle>
          <DialogDescription>
            Expected income supports planning for {formatMonthYear(monthValue, appLang)} until you manually change its status.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Source</label>
              <Select value={sourceId || undefined} onValueChange={setSourceId}>
                <SelectTrigger className="rounded-2xl">
                  <SelectValue placeholder="Income source" />
                </SelectTrigger>
                <SelectContent>
                  {activeSources.map((source) => (
                    <SelectItem key={source.id} value={String(source.id)}>{source.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {activeSources.length === 0 ? (
                <p className="text-xs text-muted-foreground">Create an active income source before adding expected income.</p>
              ) : null}
            </div>
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Amount</label>
              <Input
                inputMode="numeric"
                value={amount}
                onChange={(event) => setAmount(formatAmountInput(event.target.value, MAX_AMOUNT_DIGITS))}
                placeholder="0"
                className="rounded-2xl"
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Expected date</label>
              <Input
                type="date"
                min={start}
                max={end}
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
                className="rounded-2xl"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Status</label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="rounded-2xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(EXPECTED_STATUS_META).map(([value, meta]) => (
                    <SelectItem key={value} value={value}>{meta.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-sm text-muted-foreground">Note</label>
            <Input
              value={note}
              maxLength={MAX_INCOME_NOTE_LENGTH}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Optional"
              className="rounded-2xl"
            />
          </div>

          {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>Cancel</Button>
          <Button onClick={submit} disabled={!canSubmit}>{mode === "edit" ? "Save" : "Add expected"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MoneyInDetailsDialog({ item, appLang, open, onOpenChange }) {
  if (!item) return null;

  const meta = getKindMeta(item.kind);
  const Icon = meta.icon;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl p-0">
        <div className="border-b border-border/60 px-6 py-5">
          <DialogHeader>
            <div className="flex items-start gap-3">
              <div className={cn("flex h-11 w-11 items-center justify-center rounded-2xl border", meta.tone)}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <DialogTitle className="truncate text-2xl">{titleFor(item)}</DialogTitle>
                <DialogDescription>{meta.description}</DialogDescription>
              </div>
            </div>
          </DialogHeader>
        </div>

        <div className="max-h-[72vh] overflow-y-auto px-6 py-5">
          <div className="rounded-2xl border border-border bg-muted/20 p-4">
            <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">Amount received</p>
            <div className="mt-2 text-3xl font-bold text-emerald-600 dark:text-emerald-400">
              +{formatUzs(item.amount)} UZS
            </div>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-border bg-card p-4">
              <h3 className="mb-2 text-sm font-semibold">Timing</h3>
              <DetailRow label="Date" value={formatDisplayDate(item.date, appLang)} />
              <DetailRow label="Recorded" value={formatDisplayDateTime(item.created_at, appLang)} />
            </div>
            <div className="rounded-2xl border border-border bg-card p-4">
              <h3 className="mb-2 text-sm font-semibold">Planning treatment</h3>
              <DetailRow label="Type" value={meta.label} />
              <DetailRow label="Budget income" value={item.counts_as_income ? "Yes" : "No"} />
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-border bg-card p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <Wallet className="h-4 w-4 text-primary" />
              Money landed in
            </h3>
            <div className="space-y-2">
              {(item.wallet_allocations || []).map((wallet, index) => (
                <div
                  key={`${wallet.wallet_id}-${wallet.amount}-${index}`}
                  className="flex items-center justify-between gap-3 rounded-xl border border-border/50 bg-muted/20 px-3 py-2"
                >
                  <span className="min-w-0 truncate text-sm font-medium">{wallet.wallet_name}</span>
                  <span className="text-sm font-semibold">{formatUzs(wallet.amount)} UZS</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-border bg-card p-4">
            <h3 className="mb-2 text-sm font-semibold">Source and links</h3>
            <DetailRow label="Source" value={sourceFor(item)} />
            <DetailRow
              label="Original area"
              value={item.original_domain ? item.original_domain.replaceAll("_", " ") : "Money in"}
            />
            {item.debt_id ? <DetailRow label="Linked debt" value={`Debt #${item.debt_id}`} /> : null}
            {item.asset_id ? <DetailRow label="Linked asset" value={`Asset #${item.asset_id}`} /> : null}
          </div>
        </div>

        <DialogFooter className="border-t border-border/60 px-6 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RecordIncomeDialog({ open, onOpenChange, wallets, sources, defaultWalletId }) {
  const { t } = useTranslation();
  const todayISO = useMemo(() => toISODateInTimeZone(), []);
  const monthStartISO = useMemo(() => `${todayISO.slice(0, 7)}-01`, [todayISO]);
  const createIncome = useCreateIncomeEntryMutation();
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(todayISO);
  const [sourceId, setSourceId] = useState("none");
  const [note, setNote] = useState("");
  const [rows, setRows] = useState([{ wallet_id: defaultWalletId || "", amount: "" }]);
  const [error, setError] = useState("");

  const activeSources = useMemo(() => (sources || []).filter((source) => source.is_active), [sources]);
  const totalAmount = parseAmountInput(amount);
  const splitTotal = sumRows(rows);
  const remaining = Math.max(0, totalAmount - splitTotal);
  const walletIds = rows.map((row) => row.wallet_id).filter(Boolean);
  const duplicateWallet = new Set(walletIds).size !== walletIds.length;
  const canSubmit =
    totalAmount > 0 &&
    totalAmount <= MAX_INCOME_AMOUNT &&
    date >= monthStartISO &&
    date <= todayISO &&
    rows.every((row) => row.wallet_id && parseAmountInput(row.amount) > 0) &&
    splitTotal === totalAmount &&
    !duplicateWallet &&
    !createIncome.isPending;

  const reset = () => {
    setAmount("");
    setDate(toISODateInTimeZone());
    setSourceId("none");
    setNote("");
    setRows([{ wallet_id: defaultWalletId || "", amount: "" }]);
    setError("");
  };

  const handleOpenChange = (nextOpen) => {
    onOpenChange(nextOpen);
    if (!nextOpen) reset();
  };

  const updateRow = (index, patch) => {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  };

  const removeRow = (index) => {
    setRows((current) => (current.length <= 1 ? current : current.filter((_, rowIndex) => rowIndex !== index)));
  };

  const fillRemaining = (index) => {
    const otherTotal = rows.reduce(
      (sum, row, rowIndex) => (rowIndex === index ? sum : sum + parseAmountInput(row.amount)),
      0
    );
    updateRow(index, { amount: formatAmountInput(String(Math.max(0, totalAmount - otherTotal)), MAX_AMOUNT_DIGITS) });
  };

  const submit = async () => {
    setError("");
    if (!canSubmit) {
      setError(duplicateWallet ? "Choose each wallet only once." : "Make the wallet split match the income amount.");
      return;
    }
    try {
      const firstWalletId = Number(rows[0]?.wallet_id);
      await createIncome.mutateAsync({
        amount: totalAmount,
        date,
        note: note.trim(),
        source_id: sourceId === "none" ? null : Number(sourceId),
        wallet_id: Number.isFinite(firstWalletId) ? firstWalletId : null,
        wallet_allocations: rows.map((row) => ({
          wallet_id: Number(row.wallet_id),
          amount: parseAmountInput(row.amount),
        })),
      });
      handleOpenChange(false);
    } catch (err) {
      setError(localizeApiError(err?.message, t) || err?.message || "Failed to record income.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Record income</DialogTitle>
          <DialogDescription>Record earned money and choose where it landed.</DialogDescription>
        </DialogHeader>

        <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Amount</label>
              <Input
                inputMode="numeric"
                value={amount}
                onChange={(event) => setAmount(formatAmountInput(event.target.value, MAX_AMOUNT_DIGITS))}
                placeholder="0"
                className="rounded-2xl"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Date</label>
              <Input
                type="date"
                min={monthStartISO}
                max={todayISO}
                value={date}
                onChange={(event) => setDate(event.target.value)}
                className="rounded-2xl"
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Source</label>
              <Select value={sourceId} onValueChange={setSourceId}>
                <SelectTrigger className="rounded-2xl">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No source</SelectItem>
                  {activeSources.map((source) => (
                    <SelectItem key={source.id} value={String(source.id)}>{source.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Note</label>
              <Input
                value={note}
                maxLength={MAX_INCOME_NOTE_LENGTH}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Optional"
                className="rounded-2xl"
              />
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-muted/15 p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">Wallet split</h3>
                <p className="mt-1 text-sm text-muted-foreground">Use one wallet or split one income across several wallets.</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="rounded-2xl"
                onClick={() => setRows((current) => [...current, { wallet_id: "", amount: "" }])}
              >
                <Plus className="mr-2 h-4 w-4" />
                Wallet
              </Button>
            </div>
            <div className="space-y-2">
              {rows.map((row, index) => (
                <div key={index} className="grid gap-2 rounded-2xl border border-border/60 bg-background p-3 sm:grid-cols-[1fr_11rem_auto_auto]">
                  <Select value={row.wallet_id} onValueChange={(value) => updateRow(index, { wallet_id: value })}>
                    <SelectTrigger className="rounded-2xl">
                      <SelectValue placeholder="Wallet" />
                    </SelectTrigger>
                    <SelectContent>
                      {wallets.map((wallet) => (
                        <SelectItem key={wallet.id} value={String(wallet.id)}>{wallet.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    inputMode="numeric"
                    value={row.amount}
                    onChange={(event) => updateRow(index, { amount: formatAmountInput(event.target.value, MAX_AMOUNT_DIGITS) })}
                    placeholder="Amount"
                    className="rounded-2xl"
                  />
                  <Button variant="outline" size="sm" className="rounded-2xl" onClick={() => fillRemaining(index)}>Fill</Button>
                  <Button variant="ghost" size="icon-sm" disabled={rows.length <= 1} onClick={() => removeRow(index)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-border/60 bg-background px-3 py-2 text-sm">
              <span className="text-muted-foreground">Split total: {formatUzs(splitTotal)} UZS</span>
              <span className={cn("font-semibold", remaining === 0 && totalAmount > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>
                Remaining: {formatUzs(remaining)} UZS
              </span>
            </div>
          </div>
          {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={createIncome.isPending}>Cancel</Button>
          <Button onClick={submit} disabled={!canSubmit}>Record income</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Income() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
  const todayISO = useMemo(() => toISODateInTimeZone(), []);
  const monthStartISO = useMemo(() => `${todayISO.slice(0, 7)}-01`, [todayISO]);
  const [activeTab, setActiveTab] = useState(() => parseTabParam(searchParams.get("tab")));
  const [kind, setKind] = useState(() => parseKindParam(searchParams.get("kind")));
  const [page, setPage] = useState(() => parsePageParam(searchParams.get("page")));
  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const debouncedSearch = useDebounce(search, 300);
  const [startDate, setStartDate] = useState(() => searchParams.get("start_date") || monthStartISO);
  const [endDate, setEndDate] = useState(() => searchParams.get("end_date") || todayISO);
  const [expectedMonth, setExpectedMonth] = useState(() => parseMonthValue(searchParams.get("expected_month"), todayISO).value);
  const [recordOpen, setRecordOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [expectedDialogOpen, setExpectedDialogOpen] = useState(false);
  const [editingExpectedIncome, setEditingExpectedIncome] = useState(null);
  const [deletingExpectedIncome, setDeletingExpectedIncome] = useState(null);

  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const sourcesQuery = useIncomeSourcesQuery(true);
  const expectedMonthParts = useMemo(() => parseMonthValue(expectedMonth, todayISO), [expectedMonth, todayISO]);
  const expectedIncomesQuery = useQuery({
    queryKey: ["budgets", "expected-incomes", expectedMonthParts.year, expectedMonthParts.month],
    queryFn: () => getBudgetExpectedIncomes(expectedMonthParts.year, expectedMonthParts.month),
    enabled: activeTab === "expected",
  });
  const dateError = startDate && endDate && startDate > endDate ? "Start date must be before end date." : "";
  const moneyInParams = useMemo(
    () => ({
      kind,
      search: debouncedSearch.trim() || undefined,
      limit: PAGE_SIZE,
      skip: (page - 1) * PAGE_SIZE,
      start_date: startDate && endDate ? startDate : undefined,
      end_date: startDate && endDate ? endDate : undefined,
    }),
    [debouncedSearch, endDate, kind, page, startDate]
  );
  const moneyInQuery = useMoneyInQuery(moneyInParams, activeTab === "stream" && !dateError);
  const invalidateExpectedIncome = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["budgets", "expected-incomes"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
    ]);
  };
  const createExpectedIncomeMutation = useMutation({
    mutationFn: createBudgetExpectedIncome,
    onSuccess: async () => {
      await invalidateExpectedIncome();
      toast.success("Expected income added");
    },
    onError: (error) => {
      toast.error("Failed to add expected income", localizeApiError(error?.message, t) || error?.message);
    },
  });
  const updateExpectedIncomeMutation = useMutation({
    mutationFn: ({ id, payload }) => updateBudgetExpectedIncome(id, payload),
    onSuccess: async () => {
      await invalidateExpectedIncome();
      toast.success("Expected income updated");
    },
    onError: (error) => {
      toast.error("Failed to update expected income", localizeApiError(error?.message, t) || error?.message);
    },
  });
  const deleteExpectedIncomeMutation = useMutation({
    mutationFn: deleteBudgetExpectedIncome,
    onSuccess: async () => {
      await invalidateExpectedIncome();
      toast.success("Expected income deleted");
    },
    onError: (error) => {
      toast.error("Failed to delete expected income", localizeApiError(error?.message, t) || error?.message);
    },
  });
  const wallets = activeWallets(walletsQuery.data);
  const defaultWalletId = useMemo(() => {
    const wallet = wallets.find((item) => item.is_default) || wallets[0];
    return wallet ? String(wallet.id) : "";
  }, [wallets]);

  const items = moneyInQuery.data?.items || [];
  const expectedIncomes = Array.isArray(expectedIncomesQuery.data) ? expectedIncomesQuery.data : [];
  const total = Number(moneyInQuery.data?.total || 0);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const visibleAmount = items.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const planningAmount = items.reduce((sum, item) => sum + (item.counts_as_income ? Number(item.amount || 0) : 0), 0);
  const expectedOpenTotal = expectedIncomes
    .filter((item) => item.status === "EXPECTED")
    .reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const expectedReceivedTotal = expectedIncomes
    .filter((item) => item.status === "RECEIVED")
    .reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const expectedInactiveCount = expectedIncomes.filter((item) => item.status !== "EXPECTED").length;
  const activeFilterCount = [debouncedSearch.trim(), kind !== "all", Boolean(startDate), Boolean(endDate)].filter(Boolean).length;
  const loading = moneyInQuery.isLoading || walletsQuery.isLoading || sourcesQuery.isLoading;
  const expectedLoading = expectedIncomesQuery.isLoading || sourcesQuery.isLoading;
  const error = dateError || moneyInQuery.error?.message || walletsQuery.error?.message || sourcesQuery.error?.message || "";
  const expectedError = expectedIncomesQuery.error?.message || sourcesQuery.error?.message || "";

  useEffect(() => {
    const next = new URLSearchParams();
    if (activeTab !== "stream") next.set("tab", activeTab);
    if (activeTab === "stream" || page > 1) next.set("page", String(page));
    if (debouncedSearch.trim()) next.set("search", debouncedSearch.trim());
    if (kind !== "all") next.set("kind", kind);
    if (startDate) next.set("start_date", startDate);
    if (endDate) next.set("end_date", endDate);
    if (expectedMonth !== currentMonthValue(todayISO) || activeTab === "expected") next.set("expected_month", expectedMonth);
    setSearchParams(next, { replace: true });
  }, [activeTab, debouncedSearch, endDate, expectedMonth, kind, page, setSearchParams, startDate, todayISO]);

  useEffect(() => {
    if (activeTab === "stream" && !moneyInQuery.isFetching && page > totalPages) {
      setPage(totalPages);
    }
  }, [activeTab, moneyInQuery.isFetching, page, totalPages]);

  const resetToFirstPage = () => setPage(1);

  const resetFilters = () => {
    setKind("all");
    setSearch("");
    setStartDate(monthStartISO);
    setEndDate(todayISO);
    setPage(1);
  };

  const openCreateExpectedIncome = () => {
    setEditingExpectedIncome(null);
    setExpectedDialogOpen(true);
  };

  const openEditExpectedIncome = (item) => {
    setEditingExpectedIncome(item);
    setExpectedDialogOpen(true);
  };

  const handleExpectedSubmit = async (payload) => {
    if (editingExpectedIncome) {
      await updateExpectedIncomeMutation.mutateAsync({
        id: editingExpectedIncome.id,
        payload,
      });
      setEditingExpectedIncome(null);
      return;
    }
    await createExpectedIncomeMutation.mutateAsync(payload);
  };

  const handleExpectedStatusChange = async (item, status) => {
    await updateExpectedIncomeMutation.mutateAsync({
      id: item.id,
      payload: { status },
    });
  };

  const handleDeleteExpectedIncome = async () => {
    if (!deletingExpectedIncome) return;
    await deleteExpectedIncomeMutation.mutateAsync(deletingExpectedIncome.id);
    setDeletingExpectedIncome(null);
  };

  return (
    <div className="w-full px-page py-8 space-y-6">
      <PageHeader
        title="Money In"
        description="All money entering your wallets, with earned income separated from borrowed, returned, sold, and corrected money."
      >
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={openCreateExpectedIncome}>
            <CalendarDays className="mr-2 h-4 w-4" />
            Add expected
          </Button>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90" onClick={() => setRecordOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Record income
          </Button>
        </div>
      </PageHeader>

      <Tabs
        value={activeTab}
        onValueChange={(value) => {
          setActiveTab(value);
          if (value === "stream") resetToFirstPage();
        }}
        className="space-y-6"
      >
        <div className="overflow-x-auto pb-1">
          <TabsList className="min-w-max rounded-2xl border border-border/70 bg-card/80 p-1 shadow-sm">
            {MONEY_IN_TABS.map((option) => (
              <TabsTrigger key={option.value} value={option.value} className="rounded-xl px-4 py-2">
                {option.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <TabsContent value="stream" className="space-y-6">
          <div className="overflow-x-auto pb-1">
            <div className="flex min-w-max gap-2 rounded-2xl border border-border/70 bg-card/80 p-1 shadow-sm">
              {KIND_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    setKind(option.value);
                    resetToFirstPage();
                  }}
                  className={cn(
                    "rounded-xl px-4 py-2 text-sm font-semibold transition-colors",
                    kind === option.value
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Narrow the inflow stream by date and money type.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Input
            type="date"
            value={startDate}
            max={endDate || todayISO}
            onChange={(event) => {
              setStartDate(event.target.value);
              resetToFirstPage();
            }}
          />
          <Input
            type="date"
            value={endDate}
            min={startDate || undefined}
            max={todayISO}
            onChange={(event) => {
              setEndDate(event.target.value);
              resetToFirstPage();
            }}
          />
          <Select
            value={kind}
            onValueChange={(value) => {
              setKind(value);
              resetToFirstPage();
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {KIND_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                resetToFirstPage();
              }}
              placeholder="Search source, wallet, note..."
              className="pl-9"
            />
          </div>
          <Button variant="outline" onClick={resetFilters}>Reset</Button>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryStat title="Visible inflows" value={total} hint={`${items.length} rows on this page`} />
        <SummaryStat title="Visible amount" value={<CurrencyAmount value={visibleAmount} format="display" />} hint="Sum of rows shown now" />
        <SummaryStat title="Planning income" value={<CurrencyAmount value={planningAmount} format="display" />} hint="Earned income only" />
        <SummaryStat title="Filters applied" value={activeFilterCount} hint={activeFilterCount ? "This stream is narrowed down." : "Showing the natural stream."} />
      </div>

      {error ? (
        <Card className="border-red-500/20">
          <CardContent className="p-5 text-sm text-red-500">{error}</CardContent>
        </Card>
      ) : null}

      <Card className="overflow-hidden border border-border/70 bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <CardHeader className="border-b border-border/60 bg-gradient-to-br from-muted/50 via-background to-background">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-1">
              <CardTitle>Inflow stream</CardTitle>
              <CardDescription>Open a row for wallet split, source, recorded time, and linked records.</CardDescription>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="rounded-full px-3 py-1">
                Page {page} of {totalPages}
              </Badge>
              <Badge variant="outline" className="rounded-full px-3 py-1">
                {getKindMeta(kind).label}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-4 sm:p-6">
          {loading ? (
            <div className="flex min-h-40 items-center justify-center">
              <LoadingSpinner className="h-8 w-8" />
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={ClipboardList}
              title="No money in yet"
              description="Income, refunds, borrowed money, sales, and balance corrections will appear here."
              className="my-4"
            />
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <MoneyInRow key={item.id} item={item} appLang={appLang} onOpen={setSelectedItem} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Page {page} of {totalPages}
        </p>
        <div className="flex items-center gap-2">
          <Button variant="outline" className="rounded-2xl" disabled={page <= 1 || moneyInQuery.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>
            <ChevronLeft className="mr-2 h-4 w-4" />
            Prev
          </Button>
          <Button variant="outline" className="rounded-2xl" disabled={page >= totalPages || moneyInQuery.isFetching} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>
            Next
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
        </TabsContent>

        <TabsContent value="expected" className="space-y-6">
          <Card className="shadow-sm">
            <CardHeader>
              <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div className="space-y-1">
                  <CardTitle>Expected Income</CardTitle>
                  <CardDescription>Manual planning entries for money you expect, but have not recorded as wallet cash.</CardDescription>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    type="month"
                    value={expectedMonth}
                    min="2020-01"
                    onChange={(event) => setExpectedMonth(parseMonthValue(event.target.value, todayISO).value)}
                    className="w-44 rounded-2xl"
                  />
                  <Button className="rounded-2xl" onClick={openCreateExpectedIncome}>
                    <Plus className="mr-2 h-4 w-4" />
                    Add expected
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryStat title="Expected backing" value={<CurrencyAmount value={expectedOpenTotal} format="display" />} hint="Still counted for budget planning" />
            <SummaryStat title="Received status" value={<CurrencyAmount value={expectedReceivedTotal} format="display" />} hint="Marked received manually" />
            <SummaryStat title="Inactive items" value={expectedInactiveCount} hint="Missed, cancelled, or received" />
            <SummaryStat title="Month" value={formatMonthYear(expectedMonth, appLang)} hint={`${expectedIncomes.length} expected entries`} />
          </div>

          {expectedError ? (
            <Card className="border-red-500/20">
              <CardContent className="p-5 text-sm text-red-500">
                {localizeApiError(expectedError, t) || expectedError}
              </CardContent>
            </Card>
          ) : null}

          <Card className="overflow-hidden border border-border/70 bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80">
            <CardHeader className="border-b border-border/60 bg-gradient-to-br from-muted/50 via-background to-background">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                <div className="space-y-1">
                  <CardTitle>Expected income list</CardTitle>
                  <CardDescription>Change status manually when the expected income is resolved.</CardDescription>
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="rounded-full px-3 py-1">
                    {formatMonthYear(expectedMonth, appLang)}
                  </Badge>
                  <Badge variant="outline" className="rounded-full px-3 py-1">
                    Manual status
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-4 sm:p-6">
              {expectedLoading ? (
                <div className="flex min-h-40 items-center justify-center">
                  <LoadingSpinner className="h-8 w-8" />
                </div>
              ) : expectedIncomes.length === 0 ? (
                <EmptyState
                  icon={CalendarDays}
                  title="No expected income"
                  description="Add salary, freelance, or other earned income expected for this month."
                  className="my-4"
                />
              ) : (
                <div className="space-y-3">
                  {expectedIncomes.map((item) => (
                    <ExpectedIncomeRow
                      key={item.id}
                      item={item}
                      appLang={appLang}
                      onEdit={openEditExpectedIncome}
                      onDelete={setDeletingExpectedIncome}
                      onStatusChange={handleExpectedStatusChange}
                      isUpdating={updateExpectedIncomeMutation.isPending || deleteExpectedIncomeMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <RecordIncomeDialog
        open={recordOpen}
        onOpenChange={setRecordOpen}
        wallets={wallets}
        sources={sourcesQuery.data || []}
        defaultWalletId={defaultWalletId}
      />
      <ExpectedIncomeDialog
        open={expectedDialogOpen}
        onOpenChange={(nextOpen) => {
          setExpectedDialogOpen(nextOpen);
          if (!nextOpen) setEditingExpectedIncome(null);
        }}
        item={editingExpectedIncome}
        monthValue={expectedMonth}
        sources={sourcesQuery.data || []}
        todayISO={todayISO}
        appLang={appLang}
        onSubmit={handleExpectedSubmit}
        isSubmitting={createExpectedIncomeMutation.isPending || updateExpectedIncomeMutation.isPending}
      />
      <ConfirmDialog
        open={Boolean(deletingExpectedIncome)}
        onOpenChange={(open) => {
          if (!open) setDeletingExpectedIncome(null);
        }}
        title="Delete expected income"
        description={
          deletingExpectedIncome
            ? `${deletingExpectedIncome.source?.name || "This expected income"} will be removed from planning.`
            : "This expected income will be removed from planning."
        }
        onConfirm={handleDeleteExpectedIncome}
        confirmText="Delete"
        cancelText="Cancel"
        isConfirming={deleteExpectedIncomeMutation.isPending}
      />
      <MoneyInDetailsDialog
        item={selectedItem}
        appLang={appLang}
        open={Boolean(selectedItem)}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setSelectedItem(null);
        }}
      />
    </div>
  );
}
