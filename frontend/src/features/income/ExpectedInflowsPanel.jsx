import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Ban,
  CalendarClock,
  CheckCircle2,
  CircleDollarSign,
  Eye,
  History,
  Landmark,
  PackageCheck,
  Pencil,
  Plus,
  ReceiptText,
  RotateCcw,
  Split,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { EmptyState } from "@/components/EmptyState";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getAssets, getDebts, getExpenses, getIncomeSources, getWallets } from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatDisplayDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  ExpectedInflowEditorDialog,
  ReceiveExpectedInflowDialog,
  RescheduleExpectedInflowDialog,
  WriteOffExpectedInflowDialog,
} from "./ExpectedInflowDialogs";
import {
  useCancelExpectedInflowMutation,
  useDeleteExpectedInflowMutation,
  useRealizeExpectedInflowMutation,
  useReopenExpectedInflowMutation,
  useRescheduleExpectedInflowMutation,
  useSaveExpectedInflowMutation,
  useWriteOffExpectedInflowMutation,
} from "./hooks/useExpectedInflowMutations";
import { useExpectedInflowsQuery } from "./hooks/useExpectedInflowQueries";


const DISPLAY_STATE_META = {
  EXPECTED: { label: "Expected", tone: "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300" },
  FULLY_RECEIVED: { label: "Fully received", tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" },
  SETTLED: { label: "Settled", tone: "border-purple-500/30 bg-purple-500/10 text-purple-700 dark:text-purple-300" },
  WRITTEN_OFF: { label: "Written off", tone: "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300" },
};

const KIND_ICONS = {
  EARNED: CircleDollarSign,
  RECEIVABLE: Landmark,
  REFUND: ReceiptText,
  ASSET_SALE: PackageCheck,
};

const normalizeItems = (data) => (Array.isArray(data) ? data : data?.items || []);

function InflowRow({ item, pending, onReceive, onReschedule, onWriteOff, onEdit, onCancel, onReopen, onDelete }) {
  const navigate = useNavigate();
  const meta = DISPLAY_STATE_META[item.display_state] || { label: item.display_state, tone: "border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300" };
  const KindIcon = KIND_ICONS[item.kind] || CalendarClock;
  const active = item.status === "OPEN";
  return (
    <Card className="rounded-lg border-border/70 shadow-sm">
      <CardContent className="p-4">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <button type="button" className="min-w-0 space-y-2 text-left" onClick={() => navigate(`/money-in/expected-inflow/${item.id}`)}>
            <div className="flex flex-wrap items-center gap-2">
              <KindIcon className="h-4 w-4 text-muted-foreground" />
              <h3 className="font-semibold">{item.title}</h3>
              <Badge className={cn("border", meta.tone)}>{meta.label}</Badge>
              {item.is_rescheduled ? <Badge variant="outline">Rescheduled</Badge> : null}
              {item.is_partially_written_off ? <Badge variant="outline">Partially written off</Badge> : null}
              {item.is_overdue ? <Badge variant="destructive">Overdue</Badge> : null}
            </div>
            <p className="text-sm text-muted-foreground">{item.source_label}</p>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span>{item.next_due_date ? `Next ${formatDisplayDate(item.next_due_date)}` : "No active schedule"}</span>
              <span>Expected {item.original_amount}</span>
              <span>Received {item.received_amount}</span>
              {item.written_off_amount > 0 ? <span>Written off {item.written_off_amount}</span> : null}
              <span>Outstanding {item.outstanding_amount}</span>
            </div>
          </button>
          <div className="flex flex-wrap items-center gap-2 lg:justify-end">
            <CurrencyAmount value={item.period_backing_amount} format="display" className="mr-2 font-semibold" />
            {active ? <Button size="sm" onClick={() => onReceive(item)} disabled={pending}><CheckCircle2 className="mr-2 h-4 w-4" />Receive</Button> : null}
            {active ? <Button size="sm" variant="outline" onClick={() => onReschedule(item)} disabled={pending}><Split className="mr-2 h-4 w-4" />Reschedule</Button> : null}
            {active ? <Button size="sm" variant="outline" onClick={() => onWriteOff(item)} disabled={pending}>Write off</Button> : null}
            <Button size="icon" variant="ghost" title="Open details" onClick={() => navigate(`/money-in/expected-inflow/${item.id}`)}><Eye className="h-4 w-4" /></Button>
            {active ? <Button size="icon" variant="ghost" title="Edit" onClick={() => onEdit(item)} disabled={pending}><Pencil className="h-4 w-4" /></Button> : null}
            {active && item.received_amount === 0 && item.written_off_amount === 0 ? <Button size="icon" variant="ghost" title="Cancel" onClick={() => onCancel(item)} disabled={pending}><Ban className="h-4 w-4" /></Button> : null}
            {!active && item.display_state !== "FULLY_RECEIVED" ? <Button size="icon" variant="ghost" title="Reopen" onClick={() => onReopen(item)} disabled={pending}><RotateCcw className="h-4 w-4" /></Button> : null}
            {item.is_pristine ? <Button size="icon" variant="ghost" title="Delete" className="text-destructive" onClick={() => onDelete(item)} disabled={pending}><Trash2 className="h-4 w-4" /></Button> : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ExpectedInflowsPanel({ monthValue, onMonthChange, todayISO, createToken = 0 }) {
  const toast = useToast();
  const [view, setView] = useState("active");
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
  const queryParams = useMemo(() => ({ budget_year: year, budget_month: month, view }), [month, view, year]);
  const inflowsQuery = useExpectedInflowsQuery(queryParams);
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
  const pending = [saveMutation, receiveMutation, rescheduleMutation, writeOffMutation, cancelMutation, reopenMutation, deleteMutation].some((mutation) => mutation.isPending);
  const inflows = inflowsQuery.data || [];
  const expectedTotal = inflows.reduce((sum, item) => sum + Number(item.period_scheduled_amount || 0), 0);
  const receivedTotal = inflows.reduce((sum, item) => sum + Number(item.received_amount || 0), 0);
  const backingTotal = inflows.reduce((sum, item) => sum + Number(item.period_backing_amount || 0), 0);
  const loading = inflowsQuery.isLoading || sourcesQuery.isLoading || debtsQuery.isLoading || expensesQuery.isLoading || assetsQuery.isLoading || walletsQuery.isLoading;

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
      <div className="flex flex-col gap-3 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between"><div className="flex items-center gap-2"><CalendarClock className="h-5 w-5" /><h2 className="text-lg font-semibold">Expected Inflows</h2></div><div className="flex flex-wrap items-center gap-2"><Input type="month" value={monthValue} min="2020-01" onChange={(event) => onMonthChange(event.target.value)} className="w-44" /><Button onClick={() => { setEditing(null); setFormOpen(true); }}><Plus className="mr-2 h-4 w-4" />Add expected</Button></div></div>
      <div className="grid gap-3 sm:grid-cols-3"><div className="border-l-2 border-sky-500 px-3 py-1"><p className="text-xs uppercase text-muted-foreground">Scheduled</p><CurrencyAmount value={expectedTotal} format="display" className="font-semibold" /></div><div className="border-l-2 border-emerald-500 px-3 py-1"><p className="text-xs uppercase text-muted-foreground">Received</p><CurrencyAmount value={receivedTotal} format="display" className="font-semibold" /></div><div className="border-l-2 border-amber-500 px-3 py-1"><p className="text-xs uppercase text-muted-foreground">Active backing</p><CurrencyAmount value={backingTotal} format="display" className="font-semibold" /></div></div>
      <Tabs value={view} onValueChange={setView}><TabsList><TabsTrigger value="active"><CalendarClock className="mr-2 h-4 w-4" />Active</TabsTrigger><TabsTrigger value="history"><History className="mr-2 h-4 w-4" />History</TabsTrigger></TabsList></Tabs>
      {inflowsQuery.error ? <p className="text-sm text-destructive">{inflowsQuery.error.message}</p> : null}
      {loading ? <div className="flex min-h-40 items-center justify-center"><LoadingSpinner className="h-8 w-8" /></div> : inflows.length === 0 ? <EmptyState icon={CalendarClock} title={view === "active" ? "No active expected inflows" : "No expected inflow history"} /> : <div className="space-y-3">{inflows.map((item) => <InflowRow key={item.id} item={item} pending={pending} onReceive={setReceiving} onReschedule={setRescheduling} onWriteOff={setWritingOff} onEdit={(row) => { setEditing(row); setFormOpen(true); }} onCancel={(row) => setConfirmAction({ type: "cancel", item: row })} onReopen={async (row) => { try { await reopenMutation.mutateAsync(row.id); toast.success("Expected inflow reopened"); } catch (error) { toast.error("Reopen failed", error?.message); } }} onDelete={(row) => setConfirmAction({ type: "delete", item: row })} />)}</div>}
      <ExpectedInflowEditorDialog open={formOpen} onOpenChange={setFormOpen} item={editing} monthValue={monthValue} todayISO={todayISO} sources={sourcesQuery.data} debts={debtsQuery.data} expenses={expensesQuery.data} assets={assetsQuery.data} pending={saveMutation.isPending} onSubmit={(payload) => saveMutation.mutateAsync({ id: editing?.id, payload })} />
      <ReceiveExpectedInflowDialog item={receiving} open={Boolean(receiving)} onOpenChange={(open) => !open && setReceiving(null)} wallets={normalizeItems(walletsQuery.data).filter((wallet) => wallet.is_active)} todayISO={todayISO} pending={receiveMutation.isPending} onSubmit={(payload) => receiveMutation.mutateAsync({ id: receiving.id, payload })} />
      <RescheduleExpectedInflowDialog item={rescheduling} open={Boolean(rescheduling)} onOpenChange={(open) => !open && setRescheduling(null)} todayISO={todayISO} pending={rescheduleMutation.isPending} onSubmit={(payload) => rescheduleMutation.mutateAsync({ id: rescheduling.id, payload })} />
      <WriteOffExpectedInflowDialog item={writingOff} open={Boolean(writingOff)} onOpenChange={(open) => !open && setWritingOff(null)} todayISO={todayISO} pending={writeOffMutation.isPending} onSubmit={(payload) => writeOffMutation.mutateAsync({ id: writingOff.id, payload })} />
      <ConfirmDialog open={Boolean(confirmAction)} onOpenChange={(open) => !open && setConfirmAction(null)} title={confirmAction?.type === "delete" ? "Delete expected inflow" : "Cancel expected inflow"} description={confirmAction?.item?.title || "Expected inflow"} onConfirm={runConfirmedAction} />
    </div>
  );
}
