import {
  AlertTriangle,
  ArrowRightLeft,
  Ban,
  CheckCircle2,
  Clock,
  FileEdit,
  PlusCircle,
  RotateCcw,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { formatDisplayDate } from "@/lib/format";


const EVENT_CONFIG = {
  CREATED: {
    icon: PlusCircle,
    label: "Agreement created",
    tone: "text-sky-600 dark:text-sky-400",
  },
  RECEIVED: {
    icon: CheckCircle2,
    label: "Payment received",
    tone: "text-emerald-600 dark:text-emerald-400",
  },
  RECEIPT_REVERSED: {
    icon: RotateCcw,
    label: "Receipt reversed",
    tone: "text-amber-600 dark:text-amber-400",
  },
  RESCHEDULED: {
    icon: ArrowRightLeft,
    label: "Rescheduled",
    tone: "text-purple-600 dark:text-purple-400",
  },
  WRITTEN_OFF: {
    icon: XCircle,
    label: "Written off",
    tone: "text-rose-600 dark:text-rose-400",
  },
  WRITE_OFF_REVERSED: {
    icon: RotateCcw,
    label: "Write-off reversed",
    tone: "text-amber-600 dark:text-amber-400",
  },
  CANCELLED: {
    icon: Ban,
    label: "Cancelled",
    tone: "text-zinc-600 dark:text-zinc-400",
  },
  CLOSED: {
    icon: Clock,
    label: "Agreement closed",
    tone: "text-zinc-600 dark:text-zinc-400",
  },
  REOPENED: {
    icon: RotateCcw,
    label: "Agreement reopened",
    tone: "text-amber-600 dark:text-amber-400",
  },
};


/**
 * Build a unified timeline from the Promise activity list plus additional
 * structural events (write-offs with reversal status, close/reopen).
 *
 * Each event:
 *  - icon based on event type
 *  - user-facing label (no raw internal IDs)
 *  - date, amount (when applicable), context note
 */
function buildTimelineEvents(item) {
  const events = [];

  // 1. Creation
  events.push({
    id: `created-${item.id}`,
    type: "CREATED",
    date: item.created_at ? item.created_at.slice(0, 10) : null,
    amount: item.original_amount,
    note: item.note || null,
  });

  // 2. Receipts
  for (const realization of item.realizations || []) {
    events.push({
      id: `receipt-${realization.id}`,
      type: "RECEIVED",
      date: realization.received_date,
      amount: realization.actual_amount,
      note: realization.note || null,
    });
  }

  // 3. Write-offs (each write-off is one event; reversed ones get a follow-up)
  for (const writeOff of item.write_offs || []) {
    events.push({
      id: `write-off-${writeOff.id}`,
      type: "WRITTEN_OFF",
      date: writeOff.written_off_date,
      amount: writeOff.amount,
      note: writeOff.reason || null,
      scheduleId: writeOff.schedule_id,
    });
    if (writeOff.reversed_at) {
      events.push({
        id: `write-off-reversed-${writeOff.id}`,
        type: "WRITE_OFF_REVERSED",
        date: writeOff.reversed_at.slice(0, 10),
        amount: writeOff.amount,
        note: writeOff.reversal_note || "Write-off reversed",
        scheduleId: writeOff.schedule_id,
      });
    }
  }

  // 4. Reschedules (from schedule close_reason == "RESCHEDULED")
  for (const schedule of item.schedules || []) {
    if (schedule.close_reason === "RESCHEDULED") {
      events.push({
        id: `rescheduled-${schedule.id}`,
        type: "RESCHEDULED",
        date: schedule.updated_at ? schedule.updated_at.slice(0, 10) : null,
        amount: schedule.amount,
        note: `Due date was ${formatDisplayDate(schedule.due_date)}`,
        scheduleId: schedule.id,
      });
    }
  }

  // 5. Cancellation
  if (item.close_reason === "CANCELLED") {
    events.push({
      id: `cancelled-${item.id}`,
      type: "CANCELLED",
      date: item.closed_at ? item.closed_at.slice(0, 10) : null,
      note: item.note || null,
    });
  }

  // 6. Close event (auto-close)
  if (item.status === "CLOSED" && item.close_reason && item.close_reason !== "CANCELLED") {
    events.push({
      id: `closed-${item.id}`,
      type: "CLOSED",
      date: item.closed_at ? item.closed_at.slice(0, 10) : null,
      note: item.close_reason.replaceAll("_", " "),
    });
  }

  // Sort newest-first, with id tiebreaker
  events.sort((a, b) => {
    if (!a.date && !b.date) return 0;
    if (!a.date) return 1;
    if (!b.date) return -1;
    const dateCmp = b.date.localeCompare(a.date);
    if (dateCmp !== 0) return dateCmp;
    return a.id.localeCompare(b.id);
  });

  return events;
}


export function UnifiedTimeline({ item }) {
  const events = buildTimelineEvents(item);

  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No activity recorded.</p>;
  }

  return (
    <div className="relative space-y-0">
      {/* Vertical line */}
      <div className="absolute left-4 top-0 h-full w-px bg-border" />

      {events.map((event, i) => {
        const config = EVENT_CONFIG[event.type] || {
          icon: FileEdit,
          label: event.type.replaceAll("_", " "),
          tone: "text-muted-foreground",
        };
        const Icon = config.icon;

        return (
          <div key={event.id} className="relative flex gap-4 pb-5 pl-10">
            {/* Timeline dot */}
            <div
              className={`absolute left-2.5 mt-1 flex h-3 w-3 items-center justify-center rounded-full border-2 border-background ${config.tone.replace("text-", "bg-").replace("600", "500").replace("400", "500")}`}
            >
              <Icon className="absolute -left-4 -top-2.5 h-4 w-4" style={{ color: undefined }} />
            </div>

            {/* Content */}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <p className={`text-sm font-medium ${config.tone}`}>
                  {config.label}
                </p>
                {event.date && (
                  <span className="text-xs text-muted-foreground">
                    {formatDisplayDate(event.date)}
                  </span>
                )}
              </div>

              {event.amount != null && (
                <p className="text-sm">
                  <CurrencyAmount value={event.amount} format="display" />
                </p>
              )}

              {event.note && (
                <p className="text-sm text-muted-foreground">{event.note}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
