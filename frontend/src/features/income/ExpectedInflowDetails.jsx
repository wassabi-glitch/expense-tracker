import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  Pencil,
  RotateCcw,
  Split,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
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
import {
  useCancelExpectedInflowMutation,
  useRealizeExpectedInflowMutation,
  useRescheduleExpectedInflowMutation,
  useReverseExpectedInflowWriteOffMutation,
  useSaveExpectedInflowMutation,
  useWriteOffExpectedInflowMutation,
} from "./hooks/useExpectedInflowMutations";
import { useExpectedInflowQuery } from "./hooks/useExpectedInflowQueries";


const STATUS_LABELS = {
  EXPECTED: "Expected",
  PARTIALLY_RECEIVED: "Partially received",
  RESOLVED: "Resolved",
  CANCELLED: "Cancelled",
  WRITTEN_OFF: "Written off",
  SUPERSEDED: "Superseded",
};

export default function ExpectedInflowDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const todayISO = toISODateInTimeZone();
  const detailQuery = useExpectedInflowQuery(id);
  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const saveMutation = useSaveExpectedInflowMutation();
  const receiveMutation = useRealizeExpectedInflowMutation();
  const rescheduleMutation = useRescheduleExpectedInflowMutation();
  const writeOffMutation = useWriteOffExpectedInflowMutation();
  const reverseWriteOffMutation = useReverseExpectedInflowWriteOffMutation();
  const cancelMutation = useCancelExpectedInflowMutation();
  const [editing, setEditing] = useState(false);
  const [receiving, setReceiving] = useState(false);
  const [rescheduling, setRescheduling] = useState(false);
  const [writingOff, setWritingOff] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const item = detailQuery.data;

  if (detailQuery.isLoading) return <div className="flex min-h-64 items-center justify-center"><LoadingSpinner className="h-8 w-8" /></div>;
  if (detailQuery.error || !item) return <div className="px-page py-8 text-destructive">{detailQuery.error?.message || "Expected inflow not found"}</div>;

  const active = ["EXPECTED", "PARTIALLY_RECEIVED"].includes(item.status);
  const activeSchedules = item.schedules.filter((schedule) => schedule.is_active);
  const pending = saveMutation.isPending || receiveMutation.isPending || rescheduleMutation.isPending || writeOffMutation.isPending || reverseWriteOffMutation.isPending || cancelMutation.isPending;
  const run = async (operation, successMessage) => {
    try {
      await operation();
      toast.success(successMessage);
    } catch (error) {
      toast.error("Expected inflow action failed", error?.message);
    }
  };

  return (
    <div className="w-full space-y-7 px-page py-8">
      <div className="flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3">
          <Button variant="ghost" className="-ml-3" onClick={() => navigate("/money-in/expected-inflow")}><ArrowLeft className="mr-2 h-4 w-4" />Expected Inflows</Button>
          <div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-semibold">{item.title}</h1><Badge>{STATUS_LABELS[item.status]}</Badge>{item.is_rescheduled ? <Badge variant="outline">Rescheduled</Badge> : null}{item.is_partially_written_off ? <Badge variant="outline">Partially written off</Badge> : null}{item.is_overdue ? <Badge variant="destructive">Overdue</Badge> : null}</div>
          <p className="text-sm text-muted-foreground">{item.source_label}</p>
        </div>
        <div className="flex flex-wrap gap-2">{active ? <Button onClick={() => setReceiving(true)}><CheckCircle2 className="mr-2 h-4 w-4" />Receive</Button> : null}{active ? <Button variant="outline" onClick={() => setRescheduling(true)}><Split className="mr-2 h-4 w-4" />Reschedule</Button> : null}{active ? <Button variant="outline" onClick={() => setWritingOff(true)}>Write off</Button> : null}<Button size="icon" variant="ghost" title="Edit" onClick={() => setEditing(true)}><Pencil className="h-4 w-4" /></Button>{active && item.received_amount === 0 && item.written_off_amount === 0 ? <Button variant="ghost" onClick={() => setConfirmCancel(true)}>Cancel</Button> : null}</div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><div className="border-l-2 border-sky-500 px-3"><p className="text-xs uppercase text-muted-foreground">Expected</p><CurrencyAmount value={item.original_amount} format="display" className="text-lg font-semibold" /></div><div className="border-l-2 border-emerald-500 px-3"><p className="text-xs uppercase text-muted-foreground">Received</p><CurrencyAmount value={item.received_amount} format="display" className="text-lg font-semibold" /></div><div className="border-l-2 border-rose-500 px-3"><p className="text-xs uppercase text-muted-foreground">Written off</p><CurrencyAmount value={item.written_off_amount} format="display" className="text-lg font-semibold" /></div><div className="border-l-2 border-amber-500 px-3"><p className="text-xs uppercase text-muted-foreground">Outstanding</p><CurrencyAmount value={item.outstanding_amount} format="display" className="text-lg font-semibold" /></div></div>

      <section className="space-y-3"><div className="flex items-center gap-2"><CalendarClock className="h-5 w-5" /><h2 className="text-lg font-semibold">Current schedule</h2></div>{activeSchedules.length === 0 ? <p className="text-sm text-muted-foreground">No active schedules.</p> : <div className="grid gap-3 lg:grid-cols-2">{activeSchedules.map((schedule) => <Card key={schedule.id} className="rounded-lg"><CardContent className="space-y-2 p-4"><div className="flex items-center justify-between gap-3"><p className="font-medium">{formatDisplayDate(schedule.due_date)}</p><Badge variant="outline">{STATUS_LABELS[schedule.status]}</Badge></div><div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground"><span>Scheduled {schedule.amount}</span><span>Remaining {schedule.remaining_amount}</span><span>Received {schedule.received_amount}</span><span>Written off {schedule.written_off_amount}</span></div></CardContent></Card>)}</div>}</section>

      <section className="space-y-3"><h2 className="text-lg font-semibold">Schedule history</h2><div className="overflow-x-auto border-y border-border"><table className="w-full min-w-[720px] text-sm"><thead className="bg-muted/40 text-left text-muted-foreground"><tr><th className="px-3 py-2">Schedule</th><th className="px-3 py-2">Parent</th><th className="px-3 py-2">Due</th><th className="px-3 py-2">Amount</th><th className="px-3 py-2">Received</th><th className="px-3 py-2">Written off</th><th className="px-3 py-2">State</th></tr></thead><tbody>{item.schedules.map((schedule) => <tr key={schedule.id} className="border-t border-border"><td className="px-3 py-2">#{schedule.id}</td><td className="px-3 py-2">{schedule.parent_id ? `#${schedule.parent_id}` : "Original"}</td><td className="px-3 py-2">{formatDisplayDate(schedule.due_date)}</td><td className="px-3 py-2">{schedule.amount}</td><td className="px-3 py-2">{schedule.received_amount}</td><td className="px-3 py-2">{schedule.written_off_amount}</td><td className="px-3 py-2"><Badge variant="outline">{STATUS_LABELS[schedule.status]}</Badge></td></tr>)}</tbody></table></div></section>

      <section className="space-y-3"><h2 className="text-lg font-semibold">Activity</h2><div className="divide-y divide-border border-y border-border">{item.activity.map((activity) => <div key={activity.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium">{activity.activity_type.replaceAll("_", " ")}</p><p className="text-sm text-muted-foreground">{activity.note || (activity.schedule_id ? `Schedule #${activity.schedule_id}` : item.source_label)}</p></div><div className="text-right"><p>{activity.amount ?? ""}</p><p className="text-sm text-muted-foreground">{formatDisplayDate(activity.activity_date)}</p></div></div>)}</div></section>

      {item.write_offs.length > 0 ? <section className="space-y-3"><h2 className="text-lg font-semibold">Write-offs</h2><div className="divide-y divide-border border-y border-border">{item.write_offs.map((writeOff) => <div key={writeOff.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium">{writeOff.amount}</p><p className="text-sm text-muted-foreground">{writeOff.reason}</p></div>{writeOff.reversed_at ? <Badge variant="outline">Reversed</Badge> : <Button size="sm" variant="outline" disabled={pending} onClick={() => run(() => reverseWriteOffMutation.mutateAsync({ id: item.id, writeOffId: writeOff.id, payload: {} }), "Write-off reversed")}><RotateCcw className="mr-2 h-4 w-4" />Reverse</Button>}</div>)}</div></section> : null}

      <ExpectedInflowEditorDialog open={editing} onOpenChange={setEditing} item={item} monthValue={String(item.next_due_date || todayISO).slice(0, 7)} todayISO={todayISO} sources={[]} debts={[]} expenses={[]} assets={[]} pending={saveMutation.isPending} onSubmit={(payload) => saveMutation.mutateAsync({ id: item.id, payload })} />
      <ReceiveExpectedInflowDialog item={item} open={receiving} onOpenChange={setReceiving} wallets={(walletsQuery.data || []).filter((wallet) => wallet.is_active)} todayISO={todayISO} pending={receiveMutation.isPending} onSubmit={(payload) => receiveMutation.mutateAsync({ id: item.id, payload })} />
      <RescheduleExpectedInflowDialog item={item} open={rescheduling} onOpenChange={setRescheduling} todayISO={todayISO} pending={rescheduleMutation.isPending} onSubmit={(payload) => rescheduleMutation.mutateAsync({ id: item.id, payload })} />
      <WriteOffExpectedInflowDialog item={item} open={writingOff} onOpenChange={setWritingOff} todayISO={todayISO} pending={writeOffMutation.isPending} onSubmit={(payload) => writeOffMutation.mutateAsync({ id: item.id, payload })} />
      <ConfirmDialog open={confirmCancel} onOpenChange={setConfirmCancel} title="Cancel expected inflow" description={item.title} onConfirm={() => run(() => cancelMutation.mutateAsync(item.id), "Expected inflow cancelled")} />
    </div>
  );
}
