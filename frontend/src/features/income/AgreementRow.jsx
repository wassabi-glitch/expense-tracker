import { useNavigate } from "react-router-dom";
import {
  CalendarClock,
  CircleDollarSign,
  Landmark,
  PackageCheck,
  ReceiptText,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { TriColorProgress } from "@/components/TriColorProgress";
import { cn } from "@/lib/utils";


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


/**
 * Agreement row — simple summary of contract completion.
 * No action buttons (Receive/Reschedule/Write off).
 * No leading with schedule due dates.
 * Clicking opens the parent details page.
 */
export function AgreementRow({ item }) {
  const navigate = useNavigate();
  const meta = DISPLAY_STATE_META[item.display_state] || { label: item.display_state, tone: "border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300" };
  const KindIcon = KIND_ICONS[item.kind] || CalendarClock;

  return (
    <Card className="rounded-lg border-border/70 shadow-sm cursor-pointer hover:bg-muted/30 transition-colors">
      <CardContent className="p-4">
        <button
          type="button"
          className="w-full min-w-0 space-y-3 text-left"
          onClick={() => navigate(`/money-in/expected-inflow/${item.id}`)}
        >
          {/* Header row */}
          <div className="flex flex-wrap items-center gap-2">
            <KindIcon className="h-4 w-4 text-muted-foreground" />
            <h3 className="font-semibold">{item.title}</h3>
            <Badge className={cn("border", meta.tone)}>{meta.label}</Badge>
            {item.is_rescheduled && <Badge variant="outline">Rescheduled</Badge>}
            {item.is_overdue && <Badge variant="destructive">Overdue</Badge>}
          </div>

          {/* Source label */}
          <p className="text-sm text-muted-foreground">{item.source_label}</p>

          {/* Completion math */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span>Agreement {item.original_amount.toLocaleString()}</span>
            <span>Received {item.received_amount.toLocaleString()}</span>
            {item.written_off_amount > 0 && (
              <span>Written off {item.written_off_amount.toLocaleString()}</span>
            )}
            <span>Outstanding {item.outstanding_amount.toLocaleString()}</span>
          </div>

          {/* Tri-color progress bar */}
          <TriColorProgress
            originalAmount={item.original_amount}
            receivedAmount={item.received_amount}
            writtenOffAmount={item.written_off_amount}
            outstandingAmount={item.outstanding_amount}
          />
        </button>
      </CardContent>
    </Card>
  );
}
