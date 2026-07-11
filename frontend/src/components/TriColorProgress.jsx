import { cn } from "@/lib/utils";


/**
 * Tri-color progress bar showing received, written-off, and outstanding portions
 * of an agreement's original amount.
 *
 * Segments:
 *   - Received (green / emerald)
 *   - Written off (rose / red)
 *   - Outstanding (neutral / gray when partial, hidden when zero)
 *
 * The total never exceeds original_amount (100%).
 */
export function TriColorProgress({
  originalAmount,
  receivedAmount,
  writtenOffAmount,
  outstandingAmount,
  className,
}) {
  if (!originalAmount || originalAmount <= 0) return null;

  const total = Number(originalAmount);
  const received = Math.min(Number(receivedAmount || 0), total);
  const writtenOff = Math.min(Number(writtenOffAmount || 0), total - received);
  const outstanding = Math.min(Number(outstandingAmount || 0), total - received - writtenOff);

  const receivedPct = total > 0 ? (received / total) * 100 : 0;
  const writtenOffPct = total > 0 ? (writtenOff / total) * 100 : 0;
  const outstandingPct = total > 0 ? (outstanding / total) * 100 : 0;

  // Don't render zero-width segments
  const segments = [];
  if (receivedPct > 0) {
    segments.push({ pct: receivedPct, color: "bg-emerald-500", label: "Received" });
  }
  if (writtenOffPct > 0) {
    segments.push({ pct: writtenOffPct, color: "bg-rose-400", label: "Written off" });
  }
  if (outstandingPct > 0) {
    segments.push({ pct: outstandingPct, color: "bg-gray-200 dark:bg-gray-700", label: "Outstanding" });
  }

  if (segments.length === 0) return null;

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex h-2 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
        {segments.map((seg, i) => (
          <div
            key={seg.label}
            className={cn(
              seg.color,
              "transition-all duration-300",
              i === 0 && "rounded-l-full",
              i === segments.length - 1 && "rounded-r-full",
            )}
            style={{ width: `${seg.pct}%` }}
            title={`${seg.label}: ${seg.pct.toFixed(0)}%`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
        {received > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
            Received {received.toLocaleString()}
          </span>
        )}
        {writtenOff > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-rose-400" />
            Written off {writtenOff.toLocaleString()}
          </span>
        )}
        {outstanding > 0 && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-gray-400" />
            Outstanding {outstanding.toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
}
