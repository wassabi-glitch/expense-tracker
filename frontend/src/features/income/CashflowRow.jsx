import { useNavigate } from "react-router-dom";
import { CalendarClock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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


/**
 * Cashflow row — a single schedule chunk due in the selected month
 * with parent Promise context. Omits deep reschedule tree history.
 * Clicking navigates to the parent Promise details page, anchored to this schedule.
 */
export function CashflowRow({ item }) {
  const navigate = useNavigate();
  const meta = READ_STATE_META[item.read_state] || { label: item.read_state, tone: "border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300" };

  return (
    <Card className="rounded-lg border-border/70 shadow-sm cursor-pointer hover:bg-muted/30 transition-colors">
      <CardContent className="p-4">
        <button
          type="button"
          className="w-full min-w-0 space-y-2 text-left"
          onClick={() => navigate(`/money-in/expected-inflow/${item.promise_id}#schedule-${item.schedule_id}`)}
        >
          {/* Header: parent Promise title + due date */}
          <div className="flex flex-wrap items-center gap-2">
            <CalendarClock className="h-4 w-4 text-muted-foreground" />
            <h3 className="font-semibold">{item.promise_title}</h3>
            <Badge className={cn("border", meta.tone)}>{meta.label}</Badge>
            {item.is_overdue && <Badge variant="destructive">Overdue</Badge>}
          </div>

          {/* Source + due date */}
          <p className="text-sm text-muted-foreground">
            {item.source_label} &middot; Due {formatDisplayDate(item.due_date)}
          </p>

          {/* Amounts */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>Scheduled {item.amount.toLocaleString()}</span>
            <span>Received {item.received_amount.toLocaleString()}</span>
            <span>Remaining {item.remaining_amount.toLocaleString()}</span>
          </div>
        </button>
      </CardContent>
    </Card>
  );
}
