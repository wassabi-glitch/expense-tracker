import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Ban,
  CalendarClock,
  Eye,
  FileText,
  History,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  Wallet,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { EmptyState } from "@/components/EmptyState";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getAssets, getDebts, getExpenses, getIncomeSources, getWallets } from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import {
  ExpectedInflowEditorDialog,
  ReceiveExpectedInflowDialog,
  RescheduleExpectedInflowDialog,
  WriteOffExpectedInflowDialog,
} from "./ExpectedInflowDialogs";
import { AgreementRow } from "./AgreementRow";
import { CashflowRow } from "./CashflowRow";
import {
  useCancelExpectedInflowMutation,
  useDeleteExpectedInflowMutation,
  useRealizeExpectedInflowMutation,
  useReopenExpectedInflowMutation,
  useRescheduleExpectedInflowMutation,
  useSaveExpectedInflowMutation,
  useWriteOffExpectedInflowMutation,
} from "./hooks/useExpectedInflowMutations";
import { useCashflowQuery, useExpectedInflowsQuery } from "./hooks/useExpectedInflowQueries";


const normalizeItems = (data) => (Array.isArray(data) ? data : data?.items || []);


export function ExpectedInflowsPanel({ monthValue, onMonthChange, todayISO, createToken = 0 }) {
  const toast = useToast();
  const [mainTab, setMainTab] = useState("agreements");
  const [view, setView] = useState("active"); // active/history for Agreements
  const [search, setSearch] = useState("");
  const [displayStateFilter, setDisplayStateFilter] = useState("all");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [receiving, setReceiving] = useState(null);
  const [rescheduling, setRescheduling] = useState(null);
  const [writingOff, setWritingOff] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);

  useEffect(() => {
    if (createToken > 0) {
      setEditing(null);
      setFormOpen(true);
    }
  }, [createToken]);

  const [year, month] = String(monthValue).split("-").map(Number);

  // Agreements query — no month filtering
  const agreementsParams = useMemo(() => ({
    view,
    ...(search.trim() ? { search: search.trim() } : {}),
    ...(displayStateFilter !== "all" ? { display_state: displayStateFilter } : {}),
  }), [view, search, displayStateFilter]);

  // Cashflow query — month-filtered schedule chunks
  const cashflowParams = useMemo(() => ({
    budget_year: year,
    budget_month: month,
  }), [year, month]);

  const agreementsQuery = useExpectedInflowsQuery(agreementsParams);
  const cashflowQuery = useCashflowQuery(cashflowParams, mainTab === "cashflow");

  const sourcesQuery = useQuery({ queryKey: ["income-sources", "expected"], queryFn: () => getIncomeSources({ include_inactive: true }) });
  const debtsQuery = useQuery({ queryKey: ["debts", "expected"], queryFn: () => getDebts({ debt_type: "OWED", lifecycle_status: "OPEN", limit: 100 }) });
  const expensesQuery = useQuery({ queryKey: ["expenses", "expected"], queryFn: () => getExpenses({ limit: 100, skip: 0 }) });
  const assetsQuery = useQuery({ queryKey: ["assets", "expected"], queryFn: () => getAssets({ limit: 100, statusFilter: "owned" }) });
  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });

  const saveMutation = useSaveExpectedInflowMutation();
  const receiveMutation = useRealizeExpectedInflowMutation();
  const rescheduleMutation = useRescheduleExpectedInflowMutation();
  const writeOffMutation = useWriteOffExpectedInflowMutation();
  const cancelMutation = useCancelExpectedInflowMutation();
  const reopenMutation = useReopenExpectedInflowMutation();
  const deleteMutation = useDeleteExpectedInflowMutation();
  const pending = [saveMutation, receiveMutation, rescheduleMutation, writeOffMutation, cancelMutation, reopenMutation, deleteMutation].some((m) => m.isPending);

  const loading = agreementsQuery.isLoading || sourcesQuery.isLoading || debtsQuery.isLoading || expensesQuery.isLoading || assetsQuery.isLoading || walletsQuery.isLoading;

  const agreements = agreementsQuery.data || [];
  const cashflowRows = cashflowQuery.data || [];

  // Summary for Cashflow tab
  const scheduledTotal = cashflowRows.reduce((sum, r) => sum + Number(r.amount || 0), 0);
  const receivedTotal = cashflowRows.reduce((sum, r) => sum + Number(r.received_amount || 0), 0);

  const runConfirmedAction = async () => {
    if (!confirmAction) return;
    try {
      if (confirmAction.type === "cancel") await cancelMutation.mutateAsync(confirmAction.item.id);
      if (confirmAction.type === "delete") await deleteMutation.mutateAsync(confirmAction.item.id);
      setConfirmAction(null);
      toast.success("Expected inflow updated");
    } catch (error) {
      toast.error("Expected inflow action failed", error?.message);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Expected Inflows</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {mainTab === "cashflow" && (
            <Input type="month" value={monthValue} min="2020-01" onChange={(e) => onMonthChange(e.target.value)} className="w-44" />
          )}
          <Button onClick={() => { setEditing(null); setFormOpen(true); }}>
            <Plus className="mr-2 h-4 w-4" />Add expected
          </Button>
        </div>
      </div>

      {/* Top-level tabs: Agreements | Cashflow */}
      <Tabs value={mainTab} onValueChange={setMainTab}>
        <TabsList>
          <TabsTrigger value="agreements"><FileText className="mr-2 h-4 w-4" />Agreements</TabsTrigger>
          <TabsTrigger value="cashflow"><Wallet className="mr-2 h-4 w-4" />Cashflow</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Agreements tab */}
      {mainTab === "agreements" && (
        <div className="space-y-4">
          {/* Search + filters */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search agreements..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={displayStateFilter} onValueChange={setDisplayStateFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All states" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All states</SelectItem>
                <SelectItem value="EXPECTED">Expected</SelectItem>
                <SelectItem value="FULLY_RECEIVED">Fully received</SelectItem>
                <SelectItem value="SETTLED">Settled</SelectItem>
                <SelectItem value="WRITTEN_OFF">Written off</SelectItem>
              </SelectContent>
            </Select>
            <Tabs value={view} onValueChange={setView}>
              <TabsList>
                <TabsTrigger value="active">Active</TabsTrigger>
                <TabsTrigger value="history"><History className="mr-2 h-4 w-4" />History</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {agreementsQuery.error ? (
            <p className="text-sm text-destructive">{agreementsQuery.error.message}</p>
          ) : loading ? (
            <div className="flex min-h-40 items-center justify-center"><LoadingSpinner className="h-8 w-8" /></div>
          ) : agreements.length === 0 ? (
            <EmptyState icon={FileText} title={view === "active" ? "No active agreements" : "No agreement history"} />
          ) : (
            <div className="space-y-3">
              {agreements.map((item) => (
                <AgreementRow key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Cashflow tab */}
      {mainTab === "cashflow" && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="border-l-2 border-sky-500 px-3 py-1">
              <p className="text-xs uppercase text-muted-foreground">Scheduled this month</p>
              <CurrencyAmount value={scheduledTotal} format="display" className="font-semibold" />
            </div>
            <div className="border-l-2 border-emerald-500 px-3 py-1">
              <p className="text-xs uppercase text-muted-foreground">Received this month</p>
              <CurrencyAmount value={receivedTotal} format="display" className="font-semibold" />
            </div>
          </div>

          {cashflowQuery.error ? (
            <p className="text-sm text-destructive">{cashflowQuery.error.message}</p>
          ) : cashflowQuery.isLoading ? (
            <div className="flex min-h-40 items-center justify-center"><LoadingSpinner className="h-8 w-8" /></div>
          ) : cashflowRows.length === 0 ? (
            <EmptyState icon={Wallet} title="No cashflow due this month" description="No schedule chunks are due in the selected month." />
          ) : (
            <div className="space-y-3">
              {cashflowRows.map((row) => (
                <CashflowRow key={`${row.promise_id}-${row.schedule_id}`} item={row} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Dialogs — shared across tabs */}
      <ExpectedInflowEditorDialog
        open={formOpen} onOpenChange={setFormOpen} item={editing}
        monthValue={monthValue} todayISO={todayISO}
        sources={sourcesQuery.data} debts={debtsQuery.data}
        expenses={expensesQuery.data} assets={assetsQuery.data}
        pending={saveMutation.isPending}
        onSubmit={(payload) => saveMutation.mutateAsync({ id: editing?.id, payload })}
      />
      <ReceiveExpectedInflowDialog
        item={receiving} open={Boolean(receiving)} onOpenChange={(open) => !open && setReceiving(null)}
        wallets={normalizeItems(walletsQuery.data).filter((w) => w.is_active)}
        todayISO={todayISO} pending={receiveMutation.isPending}
        onSubmit={(payload) => receiveMutation.mutateAsync({ id: receiving.id, payload })}
      />
      <RescheduleExpectedInflowDialog
        item={rescheduling} open={Boolean(rescheduling)} onOpenChange={(open) => !open && setRescheduling(null)}
        todayISO={todayISO} pending={rescheduleMutation.isPending}
        onSubmit={(payload) => rescheduleMutation.mutateAsync({ id: rescheduling.id, payload })}
      />
      <WriteOffExpectedInflowDialog
        item={writingOff} open={Boolean(writingOff)} onOpenChange={(open) => !open && setWritingOff(null)}
        todayISO={todayISO} pending={writeOffMutation.isPending}
        onSubmit={(payload) => writeOffMutation.mutateAsync({ id: writingOff.id, payload })}
      />
      <ConfirmDialog
        open={Boolean(confirmAction)} onOpenChange={(open) => !open && setConfirmAction(null)}
        title={confirmAction?.type === "delete" ? "Delete expected inflow" : "Cancel expected inflow"}
        description={confirmAction?.item?.title || "Expected inflow"}
        onConfirm={runConfirmedAction}
      />
    </div>
  );
}
