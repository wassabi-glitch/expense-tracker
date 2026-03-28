import React from "react";
import { cn } from "@/lib/utils";
import { Circle, MoreHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { EmptyState } from "@/components/ui/empty-state";
import TitleTooltip from "@/components/ui/title-tooltip";
import CurrencyAmount from "@/features/expenses/components/CurrencyAmount";
import { useTranslation } from "react-i18next";

const ExpenseGalleryView = ({ 
  expenses, 
  loading, 
  windowWidth, 
  categoryIconMap, 
  getCategoryBgClass, 
  getCategoryColorClass, 
  tCategory, 
  _formatDisplayDateLocal, 
  openExpenseActions 
}) => {
  const { t } = useTranslation();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
      {loading ? (
        <div className="col-span-full flex justify-center py-20">
          <LoadingSpinner className="h-8 w-8" />
        </div>
      ) : expenses.length === 0 ? (
        <div className="col-span-full">
          <EmptyState inline description={t("expenses.noResults")} />
        </div>
      ) : (
        expenses.map((e, index) => {
          const Icon = categoryIconMap[e.category] || Circle;
          const bgClass = getCategoryBgClass(e.category);
          return (
            <div
              key={e.id}
              className={cn(
                "bg-[linear-gradient(180deg,rgba(255,255,255,0.03),transparent)]",
                "dark:bg-[linear-gradient(180deg,rgba(255,255,255,0.01),transparent)]",
                "hover:-translate-y-0.5 hover:shadow-md",
                "active:scale-[0.98] active:-translate-y-0 active:shadow-sm [&:has([data-action-popover]:active)]:scale-100",
                "animate-in fade-in zoom-in-95 duration-500 fill-both"
              )}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-start justify-between mb-5">
                <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center shadow-inner", bgClass)}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex flex-col items-end gap-1.5">
                  <Badge
                    variant="secondary"
                    className={cn(
                      "px-2.5 py-0.5 text-[10px] font-bold capitalize tracking-wider bg-muted/50 border-none shrink-0",
                      getCategoryColorClass(e.category)
                    )}
                  >
                    {tCategory(e.category)}
                  </Badge>
                  <div data-action-popover>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="h-8 w-8 rounded-full opacity-40 group-hover:opacity-100 transition-all hover:bg-muted"
                      onPointerDown={(ev) => ev.stopPropagation()}
                      onClick={(event) => {
                        event.stopPropagation();
                        openExpenseActions(event, e);
                      }}
                    >
                      <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </div>
              </div>

              <div className="space-y-1.5 min-w-0">
                <TitleTooltip title={e.title}>
                  <div className="font-bold text-xl tracking-tight text-foreground truncate cursor-default w-full">
                    {e.title}
                  </div>
                </TitleTooltip>
                <p className="text-xs font-medium text-muted-foreground/60 flex items-center gap-2">
                  {_formatDisplayDateLocal(e.date)}
                </p>
              </div>

              <div className="pt-6 border-t border-border/10 mt-6 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/40">
                    {t("expenses.amount", { defaultValue: "Amount" })}
                  </span>
                </div>
                <div className="flex justify-end overflow-hidden">
                  <CurrencyAmount
                    value={e.amount}
                    format={windowWidth < 550 ? "compact" : "display"}
                    className="text-xl lg:text-2xl font-black text-foreground tabular-nums tracking-tight whitespace-nowrap"
                    currencyClassName="text-[12px] font-bold opacity-60 ml-2"
                  />
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};

export default ExpenseGalleryView;
