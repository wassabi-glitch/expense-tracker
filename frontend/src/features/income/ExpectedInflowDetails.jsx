import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CalendarClock, Pencil } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { TriColorProgress } from "@/components/TriColorProgress";
import { getWallets } from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { toISODateInTimeZone } from "@/lib/date";
import { formatDisplayDate } from "@/lib/format";
import {
  ExpectedInflowEditorDialog,
  ReceiveExpectedInflowDialog,
  RescheduleExpectedInflowDialog,
  WriteOffExpectedInflowDialog,
} from "./ExpectedInflowDialogs";
import { ScheduleCard } from "./ScheduleCard";
import { UnifiedTimeline } from "./UnifiedTimeline";
import {
  useCancelExpectedInflowMutation,
  useRealizeExpectedInflowMutation,
  useRescheduleExpectedInflowMutation,
  useReverseExpectedInflowReceiptMutation,
  useReverseExpectedInflowWriteOffMutation,
  useSaveExpectedInflowMutation,
  useWriteOffExpectedInflowMutation,
} from "./hooks/useExpectedInflowMutations";
import { useExpectedInflowQuery } from "./hooks/useExpectedInflowQueries";


const DISPLAY_STATE_LABELS = {
  EXPECTED: "Expected",
  FULLY_RECEIVED: "Fully received",
  SETTLED: "Settled",
  WRITTEN_OFF: "Written off",
};


export default function ExpectedInflowDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const todayISO = toISODateInTimeZone();

  const detailQuery = useExpectedInflowQuery(id);
  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });

  const saveMutation = useSaveExpectedInflowMutation();
  const receiveMutation = useRealizeExpectedInflowMutation();
  const rescheduleMutation = useRescheduleExpectedInflowMutation();
  const writeOffMutation = useWriteOffExpectedInflowMutation();
  const reverseWriteOffMutation = useReverseExpectedInflowWriteOffMutation();
  const reverseReceiptMutation = useReverseExpectedInflowReceiptMutation();
  const cancelMutation = useCancelExpectedInflowMutation();

  const [editing, setEditing] = useState(false);
  const [receiving, setReceiving] = useState(null); // schedule or item
  const [rescheduling, setRescheduling] = useState(null);
  const [writingOff, setWritingOff] = useState(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [reverseReceiptId, setReverseReceiptId] = useState(null);
  const [reverseWriteOffId, setReverseWriteOffId] = useState(null);

  // Extract anchor schedule id from URL hash (#schedule-123)
  const anchorScheduleId = useMemo(() => {
    const hash = location.hash;
    if (hash.startsWith("#schedule-")) {
      return Number(hash.slice("#schedule-".length));
    }
    return null;
  }, [location.hash]);

  const item = detailQuery.data;

  // Clear hash after processing
  useEffect(() => {
    if (anchorScheduleId && item && location.hash) {
      // Small delay to let DOM render, then scroll
      const timer = setTimeout(() => {
        const el = document.getElementById(location.hash.slice(1));
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [anchorScheduleId, item, location.hash]);

  if (detailQuery.isLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center">
        <LoadingSpinner className="h-8 w-8" />
      </div>
    );
  }
  if (detailQuery.error || !item) {
    return (
      <div className="px-page py-8 text-destructive">
        {detailQuery.error?.message || "Expected inflow not found"}
      </div>
    );
  }

  const active = item.status === "OPEN";
  const pending =
    saveMutation.isPending ||
    receiveMutation.isPending ||
    rescheduleMutation.isPending ||
    writeOffMutation.isPending ||
    reverseWriteOffMutation.isPending ||
    reverseReceiptMutation.isPending ||
    cancelMutation.isPending;

  const run = async (operation, successMessage) => {
    try {
      await operation();
      toast.success(successMessage);
    } catch (error) {
      toast.error("Expected inflow action failed", error?.message);
    }
  };

  // All schedules sorted: active/pending first, then historical
  const sortedSchedules = useMemo(() => {
    const schedules = item.schedules || [];
    return [...schedules].sort((a, b) => {
      // Active first
      if (a.is_active !== b.is_active) return a.is_active ? -1 : 1;
      // Then by due date
      return a.due_date.localeCompare(b.due_date);
    });
  }, [item.schedules]);

  return (
    <div className="w-full space-y-7 px-page py-8">
      {/* Header with back nav */}
      <div className="flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3">
          <Button
            variant="ghost"
            className="-ml-3"
            onClick={() => navigate("/money-in/expected-inflow")}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Expected Inflows
          </Button>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold">{item.title}</h1>
            <Badge>{DISPLAY_STATE_LABELS[item.display_state] || item.display_state}</Badge>
            {item.is_rescheduled && <Badge variant="outline">Rescheduled</Badge>}
            {item.is_partially_written_off && <Badge variant="outline">Partially written off</Badge>}
            {item.is_overdue && <Badge variant="destructive">Overdue</Badge>}
          </div>
          <p className="text-sm text-muted-foreground">{item.source_label}</p>
        </div>

        {/* Top-level actions: only Edit + Cancel */}
        <div className="flex flex-wrap gap-2">
          <Button size="icon" variant="ghost" title="Edit" onClick={() => setEditing(true)} disabled={pending}>
            <Pencil className="h-4 w-4" />
          </Button>
          {active && item.received_amount === 0 && item.written_off_amount === 0 && (
            <Button variant="ghost" onClick={() => setConfirmCancel(true)} disabled={pending}>
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Summary metrics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="border-l-2 border-sky-500 px-3">
          <p className="text-xs uppercase text-muted-foreground">Expected</p>
          <CurrencyAmount value={item.original_amount} format="display" className="text-lg font-semibold" />
        </div>
        <div className="border-l-2 border-emerald-500 px-3">
          <p className="text-xs uppercase text-muted-foreground">Received</p>
          <CurrencyAmount value={item.received_amount} format="display" className="text-lg font-semibold" />
        </div>
        <div className="border-l-2 border-rose-500 px-3">
          <p className="text-xs uppercase text-muted-foreground">Written off</p>
          <CurrencyAmount value={item.written_off_amount} format="display" className="text-lg font-semibold" />
        </div>
        <div className="border-l-2 border-amber-500 px-3">
          <p className="text-xs uppercase text-muted-foreground">Outstanding</p>
          <CurrencyAmount value={item.outstanding_amount} format="display" className="text-lg font-semibold" />
        </div>
      </div>

      {/* Tri-color progress */}
      <TriColorProgress
        originalAmount={item.original_amount}
        receivedAmount={item.received_amount}
        writtenOffAmount={item.written_off_amount}
        outstandingAmount={item.outstanding_amount}
      />

      {/* Schedule cards — current and historical, with inline actions */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Schedules</h2>
        </div>
        {sortedSchedules.length === 0 ? (
          <p className="text-sm text-muted-foreground">No schedules.</p>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {sortedSchedules.map((schedule) => (
              <ScheduleCard
                key={schedule.id}
                schedule={schedule}
                promiseIsOpen={active}
                pending={pending}
                highlight={schedule.id === anchorScheduleId}
                onReceive={(s) => setReceiving(s)}
                onReschedule={(s) => setRescheduling(s)}
                onWriteOff={(s) => setWritingOff(s)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Unified timeline — replaces separate Activity, Schedule history, and Write-offs tables */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">History</h2>
        <UnifiedTimeline
          item={item}
          pending={pending}
          onReverseReceipt={(realizationId) => setReverseReceiptId(realizationId)}
          onReverseWriteOff={(writeOffId) => setReverseWriteOffId(writeOffId)}
        />
      </section>

      {/* Dialogs — target a specific schedule when launched from a ScheduleCard */}
      <ExpectedInflowEditorDialog
        open={editing}
        onOpenChange={setEditing}
        item={item}
        monthValue={String(item.next_due_date || todayISO).slice(0, 7)}
        todayISO={todayISO}
        sources={[]}
        debts={[]}
        expenses={[]}
        assets={[]}
        pending={saveMutation.isPending}
        onSubmit={(payload) => saveMutation.mutateAsync({ id: item.id, payload })}
      />

      <ReceiveExpectedInflowDialog
        item={item}
        open={Boolean(receiving)}
        onOpenChange={(open) => { if (!open) setReceiving(null); }}
        wallets={(walletsQuery.data || []).filter((w) => w.is_active)}
        todayISO={todayISO}
        pending={receiveMutation.isPending}
        targetSchedule={receiving}
        onSubmit={(payload) => receiveMutation.mutateAsync({ id: item.id, payload })}
      />

      <RescheduleExpectedInflowDialog
        item={item}
        open={Boolean(rescheduling)}
        onOpenChange={(open) => { if (!open) setRescheduling(null); }}
        todayISO={todayISO}
        pending={rescheduleMutation.isPending}
        targetSchedule={rescheduling}
        onSubmit={(payload) => rescheduleMutation.mutateAsync({ id: item.id, payload })}
      />

      <WriteOffExpectedInflowDialog
        item={item}
        open={Boolean(writingOff)}
        onOpenChange={(open) => { if (!open) setWritingOff(null); }}
        todayISO={todayISO}
        pending={writeOffMutation.isPending}
        targetSchedule={writingOff}
        onSubmit={(payload) => writeOffMutation.mutateAsync({ id: item.id, payload })}
      />

      <ConfirmDialog
        open={confirmCancel}
        onOpenChange={setConfirmCancel}
        title="Cancel expected inflow"
        description={item.title}
        onConfirm={() => run(() => cancelMutation.mutateAsync(item.id), "Expected inflow cancelled")}
      />

      <ConfirmDialog
        open={reverseReceiptId != null}
        onOpenChange={(open) => { if (!open) setReverseReceiptId(null); }}
        title="Reverse receipt"
        description="This will void the wallet transaction and restore the outstanding amount. The original receipt record will remain visible in the history."
        onConfirm={() =>
          run(
            () => reverseReceiptMutation.mutateAsync({ id: item.id, realizationId: reverseReceiptId, payload: {} }),
            "Receipt reversed",
          ).then(() => setReverseReceiptId(null))
        }
      />

      <ConfirmDialog
        open={reverseWriteOffId != null}
        onOpenChange={(open) => { if (!open) setReverseWriteOffId(null); }}
        title="Reverse write-off"
        description="This will restore the written-off amount as outstanding. The original write-off record will remain visible in the history."
        onConfirm={() =>
          run(
            () => reverseWriteOffMutation.mutateAsync({ id: item.id, writeOffId: reverseWriteOffId, payload: {} }),
            "Write-off reversed",
          ).then(() => setReverseWriteOffId(null))
        }
      />
    </div>
  );
}
