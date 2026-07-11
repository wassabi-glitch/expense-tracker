import { useEffect, useRef } from "react";
import { CheckCircle2, Split } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { formatDisplayDate } from "@/lib/format";
import { cn } from "@/lib/utils";


const READ_STATE_META = {
  OUTSTANDING: { label: "Outstanding", tone: "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300" },
  PARTIAL: { label: "Partial", tone: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300" },
  FULLY_RECEIVED: { label: "Fully received", tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" },
  WRITTEN_OFF: { label: "Written off", tone: "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300" },
  SETTLED: { label: "Settled", tone: "border-purple-500/30 bg-purple-500/10 text-purple-700 dark:text-purple-300" },
  OVERDUE: { label: "Overdue", tone: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300" },
  SUPERSEDED: { label: "Superseded", tone: "border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300" },
  CANCELLED: { label: "Cancelled", tone: "border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300" },
};

const ACTIONABLE_STATES = new Set(["OUTSTANDING", "PARTIAL", "OVERDUE"]);


/**
 * Schedule card with inline action buttons.
 * Receive, Reschedule, and Write off buttons appear on the card they affect.
 * Inactive/superseded/cancelled/settled schedules hide invalid actions.
 * The card has id="schedule-{id}" for Cashflow row anchor navigation.
 */
export function ScheduleCard({
  schedule,
  promiseIsOpen,
  pending,
  onReceive,
  onReschedule,
  onWriteOff,
  highlight,
}) {
  const ref = useRef(null);
  const meta = READ_STATE_META[schedule.read_state] || { label: schedule.read_state, tone: "border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300" };
  const canAct = promiseIsOpen && ACTIONABLE_STATES.has(schedule.read_state);

  useEffect(() => {
    if (highlight && ref.current) {
      ref.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlight]);

  return (
    <Card
      ref={ref}
      id={`schedule-${schedule.id}`}
      className={cn(
        "rounded-lg border-border/70 shadow-sm transition-all",
        highlight && "ring-2 ring-sky-500 ring-offset-2",
      )}
    >
      <CardContent className="space-y-3 p-4">
        {/* Header: due date + state badge */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-medium">
            {formatDisplayDate(schedule.due_date)}
            {schedule.parent_id && (
              <span className="ml-2 text-xs text-muted-foreground">
                (rescheduled from #{schedule.parent_id})
              </span>
            )}
          </p>
          <Badge className={cn("border", meta.tone)}>{meta.label}</Badge>
        </div>

        {/* Amount breakdown */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span>Scheduled {schedule.amount.toLocaleString()}</span>
          <span>Remaining {schedule.remaining_amount.toLocaleString()}</span>
          <span>Received {schedule.received_amount.toLocaleString()}</span>
          {schedule.written_off_amount > 0 && (
            <span>Written off {schedule.written_off_amount.toLocaleString()}</span>
          )}
        </div>

        {/* Inline actions — only on active, actionable schedules when Promise is open */}
        {canAct && (
          <div className="flex flex-wrap gap-2 pt-1">
            <Button size="sm" onClick={() => onReceive(schedule)} disabled={pending}>
              <CheckCircle2 className="mr-2 h-4 w-4" />Receive
            </Button>
            <Button size="sm" variant="outline" onClick={() => onReschedule(schedule)} disabled={pending}>
              <Split className="mr-2 h-4 w-4" />Reschedule
            </Button>
            <Button size="sm" variant="outline" onClick={() => onWriteOff(schedule)} disabled={pending}>
              Write off
            </Button>
          </div>
        )}

        {schedule.note && (
          <p className="text-xs text-muted-foreground italic">{schedule.note}</p>
        )}
      </CardContent>
    </Card>
  );
}
