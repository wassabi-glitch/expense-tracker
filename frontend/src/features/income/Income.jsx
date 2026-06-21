import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowDownToLine,
  BriefcaseBusiness,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Landmark,
  PackageCheck,
  Plus,
  RotateCcw,
  Scale,
  Search,
  Trash2,
  Wallet,
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
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { getWallets } from "@/lib/api";
import { toISODateInTimeZone } from "@/lib/date";
import { useDebounce } from "@/hooks/useDebounce";
import {
  formatAmountInput,
  formatDisplayDate,
  formatDisplayDateTime,
  formatUzs,
  parseAmountInput,
} from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";
import { cn } from "@/lib/utils";
import { MAX_INCOME_AMOUNT, MAX_INCOME_NOTE_LENGTH } from "./incomeSchemas";
import { useIncomeSourcesQuery, useMoneyInQuery } from "./hooks/useIncomeQueries";
import { useCreateIncomeEntryMutation } from "./hooks/useIncomeMutations";
import { ExpectedInflowsPanel } from "./ExpectedInflowsPanel";

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
  { value: "expected", label: "Expected Inflows" },
];

const parsePageParam = (value) => {
  const raw = String(value ?? "").trim();
  if (!raw) return 1;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
};

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

function currentMonthValue(todayISO) {
  return String(todayISO || toISODateInTimeZone()).slice(0, 7);
}

function parseMonthValue(value, fallbackISO = toISODateInTimeZone()) {
  const fallback = currentMonthValue(fallbackISO);
  const raw = /^\d{4}-\d{2}$/.test(String(value || "")) ? String(value) : fallback;
  const [year, month] = raw.split("-").map(Number);
  return { value: raw, year, month };
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
  const { i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
  const todayISO = useMemo(() => toISODateInTimeZone(), []);
  const monthStartISO = useMemo(() => `${todayISO.slice(0, 7)}-01`, [todayISO]);
  const activeTab = location.pathname === "/money-in/expected-inflow" ? "expected" : "stream";
  const [kind, setKind] = useState(() => parseKindParam(searchParams.get("kind")));
  const [page, setPage] = useState(() => parsePageParam(searchParams.get("page")));
  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const debouncedSearch = useDebounce(search, 300);
  const [startDate, setStartDate] = useState(() => searchParams.get("start_date") || monthStartISO);
  const [endDate, setEndDate] = useState(() => searchParams.get("end_date") || todayISO);
  const [expectedMonth, setExpectedMonth] = useState(() => parseMonthValue(searchParams.get("expected_month"), todayISO).value);
  const [recordOpen, setRecordOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [expectedCreateToken, setExpectedCreateToken] = useState(() => searchParams.get("action") === "add" ? 1 : 0);

  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const sourcesQuery = useIncomeSourcesQuery(true);
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
  const wallets = activeWallets(walletsQuery.data);
  const defaultWalletId = useMemo(() => {
    const wallet = wallets.find((item) => item.is_default) || wallets[0];
    return wallet ? String(wallet.id) : "";
  }, [wallets]);

  const items = moneyInQuery.data?.items || [];
  const total = Number(moneyInQuery.data?.total || 0);
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const visibleAmount = items.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const planningAmount = items.reduce((sum, item) => sum + (item.counts_as_income ? Number(item.amount || 0) : 0), 0);
  const activeFilterCount = [debouncedSearch.trim(), kind !== "all", Boolean(startDate), Boolean(endDate)].filter(Boolean).length;
  const loading = moneyInQuery.isLoading || walletsQuery.isLoading || sourcesQuery.isLoading;
  const error = dateError || moneyInQuery.error?.message || walletsQuery.error?.message || sourcesQuery.error?.message || "";

  useEffect(() => {
    const next = new URLSearchParams();
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
    if (activeTab !== "expected") {
      navigate(`/money-in/expected-inflow?expected_month=${expectedMonth}`);
    }
    setExpectedCreateToken((value) => value + 1);
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
          if (value === "expected") {
            navigate(`/money-in/expected-inflow?expected_month=${expectedMonth}`);
            return;
          }
          resetToFirstPage();
          navigate("/money-in");
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
          <ExpectedInflowsPanel
            monthValue={expectedMonth}
            onMonthChange={(value) => setExpectedMonth(parseMonthValue(value, todayISO).value)}
            todayISO={todayISO}
            appLang={appLang}
            createToken={expectedCreateToken}
          />
        </TabsContent>
      </Tabs>

      <RecordIncomeDialog
        open={recordOpen}
        onOpenChange={setRecordOpen}
        wallets={wallets}
        sources={sourcesQuery.data || []}
        defaultWalletId={defaultWalletId}
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
