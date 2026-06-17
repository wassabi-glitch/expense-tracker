import { Card } from "@/components/ui/card";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { cn } from "@/lib/utils";

export function DebtSummaryCard({ title, value, hint, accent = "default", icon: IconComponent }) {
  const isNegative = accent === "destructive";
  const isPositive = accent === "primary";
  
  return (
    <Card className={cn(
      "group relative overflow-hidden transition-all duration-500 hover:shadow-2xl hover:-translate-y-1 border-none",
      "bg-linear-to-br from-card/80 to-card/40 backdrop-blur-xl shadow-xl ring-1 ring-white/10"
    )}>
      {/* Dynamic Background Aura */}
      <div className={cn(
        "absolute -right-12 -top-12 size-48 blur-3xl opacity-10 transition-opacity duration-700 group-hover:opacity-20",
        isNegative ? "bg-rose-500" : isPositive ? "bg-emerald-500" : "bg-primary"
      )} />

      <div className="relative p-6">
        <div className="flex items-start justify-between mb-6">
          <div className="space-y-1.5">
            <h3 className={cn(
              "text-[10px] font-black uppercase tracking-[0.2em]",
              isNegative ? "text-rose-500/80" : isPositive ? "text-emerald-400" : "text-muted-foreground"
            )}>
              {title}
            </h3>
            {hint && (
              <p className="text-[11px] text-muted-foreground/60 font-medium">
                {hint}
              </p>
            )}
          </div>
          
          <div className={cn(
            "flex size-11 items-center justify-center rounded-2xl shadow-lg ring-1 transition-all duration-500 group-hover:rotate-12",
            isNegative 
              ? "bg-rose-500/10 text-rose-500 ring-rose-500/20" 
              : isPositive 
                ? "bg-emerald-500/10 text-emerald-500 ring-emerald-500/20"
                : "bg-muted text-muted-foreground ring-border"
          )}>
            <IconComponent className="size-5" />
          </div>
        </div>

        <div className="space-y-1">
          <CurrencyAmount
            value={value}
            format="display"
            className="flex w-full items-baseline gap-2 text-left"
            valueClassName={cn(
              "text-3xl lg:text-4xl font-black tracking-tight tabular-nums",
              isNegative ? "text-rose-500" : isPositive ? "text-emerald-500" : "text-foreground"
            )}
            currencyClassName="text-sm font-bold opacity-40"
          />
          
        </div>
      </div>
    </Card>
  );
}
