import { useTranslation } from "react-i18next";
import { AlertTriangle, Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatUzs, formatMonthYear } from "@/lib/format";

/**
 * Shared dialog for the Budget Interceptor repair flow (ADR-0009).
 *
 * Renders when a mutation fails with ``expenses.budget_required``.
 * The user creates a Budget Permission row with a monthly limit and the
 * original action is replayed automatically.
 */

export function BudgetRepairDialog({
  open,
  onOpenChange,
  repairPrompt,
  repairAmount,
  onAmountChange,
  repairPending,
  repairError,
  onClose,
  onCreateBudget,
}) {
  const { t } = useTranslation();

  if (!repairPrompt) return null;

  const monthLabel = formatMonthYear(
    `${repairPrompt.budgetYear}-${String(repairPrompt.budgetMonth).padStart(2, "0")}-01`,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>
            {t("expenses.createBudgetTitle", {
              defaultValue: "Create budget permission",
            })}
          </DialogTitle>
          <DialogDescription>
            {t("expenses.createBudgetDesc", {
              defaultValue:
                "No budget exists for {{category}} in {{month}}. Create one to allow this {{amount}} expense.",
              category: repairPrompt.categoryLabel ?? repairPrompt.category,
              month: monthLabel,
              amount: formatUzs(repairPrompt.suggestedAmount),
            })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Alert */}
          <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p>
                {t("expenses.createBudgetAlert", {
                  defaultValue:
                    "Your draft is preserved. Create a {{category}} budget for {{month}} to continue, or cancel to leave it unposted.",
                  category: repairPrompt.categoryLabel ?? repairPrompt.category,
                  month: monthLabel,
                })}
              </p>
            </div>
          </div>

          {/* Amount input */}
          <div className="rounded-lg border border-border/60 bg-muted/15 p-3">
            <p className="text-sm font-semibold">
              {t("budgets.monthlyLimit", { defaultValue: "Monthly limit" })}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("expenses.createBudgetHint", {
                defaultValue:
                  "Set the monthly spending limit for {{category}}. The expense amount is suggested as a starting point.",
                category: repairPrompt.categoryLabel ?? repairPrompt.category,
              })}
            </p>
            <div className="mt-3 grid gap-1.5">
              <label className="text-xs font-semibold">
                {t("expenses.amount", { defaultValue: "Amount" })}
              </label>
              <Input
                value={repairAmount}
                inputMode="numeric"
                onChange={(event) => onAmountChange(event.target.value)}
              />
            </div>
          </div>

          {repairError ? (
            <p className="text-sm font-medium text-red-500">{repairError}</p>
          ) : null}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="ghost" disabled={repairPending} onClick={onClose}>
            {t("common.cancel", { defaultValue: "Cancel" })}
          </Button>
          <Button
            disabled={repairPending || !repairAmount || Number(repairAmount) <= 0}
            onClick={onCreateBudget}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("budgets.create", { defaultValue: "Create budget" })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
