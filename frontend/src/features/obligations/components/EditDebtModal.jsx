import React, { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useTranslation } from "react-i18next";
import { useUpdateDebtMutation } from "../hooks/useDebtsMutations";
import { useIncomeSourcesQuery } from "@/features/income/hooks/useIncomeQueries";
import { debtUpdateFormSchema } from "../obligationSchemas";
import { formatAmountInput } from "@/lib/format";
import { cn } from "@/lib/utils";
import { categoryIconMap, SPENDING_CATEGORIES, getCategoryColorClass, getCategoryBgClass } from "@/lib/category";
import { Circle } from "lucide-react";

export function EditDebtModal({ isOpen, onClose, debt }) {
  const { t } = useTranslation();
  const updateMutation = useUpdateDebtMutation();
  const incomeSourcesQuery = useIncomeSourcesQuery();

  const [formCreditor, setFormCreditor] = useState("");
  const [formTitle, setFormTitle] = useState("");
  const [formDate, setFormDate] = useState("");
  const [formDueDate, setFormDueDate] = useState("");
  const [formAmount, setFormAmount] = useState("");
  const [formExpenseCategory, setFormExpenseCategory] = useState("");
  const [formIncomeSourceId, setFormIncomeSourceId] = useState("");
  const [errors, setErrors] = useState({});

  const isActive = debt?.status === "ACTIVE";

  useEffect(() => {
    if (isOpen && debt) {
      setFormCreditor(debt.counterparty_name || "");
      setFormTitle(debt.description || "");
      setFormDate(debt.date || "");
      setFormDueDate(debt.expected_return_date || "");
      setFormAmount(debt.initial_amount ? formatAmountInput(String(debt.initial_amount)) : "");
      setFormExpenseCategory(debt.expense_category || "");
      setFormIncomeSourceId(debt.income_source_id ? String(debt.income_source_id) : "");
      setErrors({});
    }
  }, [isOpen, debt]);

  const handleSubmit = (e) => {
    e.preventDefault();

    const payload = {
      counterparty_name: formCreditor,
      description: formTitle || null,
      date: formDate || null,
      expected_return_date: formDueDate || null,
      expense_category: (!debt.is_money_transferred && debt.debt_type === "OWING" && formExpenseCategory) ? formExpenseCategory : null,
      income_source_id: (!debt.is_money_transferred && debt.debt_type === "OWED" && formIncomeSourceId) ? Number(formIncomeSourceId) : null,
    };

    if (!debt.is_money_transferred && debt.debt_type === "OWING" && !formExpenseCategory) {
      setErrors({ expense_category: t("debts.validation.expense_category.required", { defaultValue: "Expense category is required" }) });
      return;
    }

    // Only include initial_amount if it actually changed (and debt is ACTIVE)
    const rawAmount = Number(String(formAmount).replace(/\s/g, "")) || 0;
    if (isActive && rawAmount > 0 && rawAmount !== debt.initial_amount) {
      // Validate that the new principal + charges isn't less than what's already paid
      const totalObligation = debt.initial_amount + (debt.total_charges || 0);
      const paidAmount = totalObligation - debt.remaining_amount;
      const newTotalObligation = rawAmount + (debt.total_charges || 0);
      
      if (newTotalObligation < paidAmount) {
        setErrors({ initial_amount: t("debts.edit_amount.remaining_would_be_negative", { defaultValue: "Amount cannot be less than already paid" }) });
        return;
      }
      payload.initial_amount = rawAmount;
    }

    const result = debtUpdateFormSchema.safeParse(payload);
    if (!result.success) {
      const formatted = {};
      result.error.issues.forEach((issue) => {
        formatted[issue.path[0]] = t(issue.message);
      });
      setErrors(formatted);
      return;
    }

    updateMutation.mutate({ debtId: debt.id, payload: result.data }, {
      onSuccess: () => {
        onClose();
      }
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(val) => !val && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("debts.edit.title")}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <label className="text-mobile-caption font-semibold uppercase tracking-wider text-muted-foreground/80">
              {t("debts.creditor")}
            </label>
            <Input
              value={formCreditor}
              onChange={e => setFormCreditor(e.target.value)}
              className={cn("h-10 sm:h-12 !text-xs md:!text-sm input-refined", errors.counterparty_name && "border-red-500")}
            />
            {errors.counterparty_name && <p className="text-[10px] text-red-500 ml-1">{errors.counterparty_name}</p>}
          </div>

          <div className="space-y-1.5">
            <label className="text-mobile-caption font-semibold uppercase tracking-wider text-muted-foreground/80">
              {t("debts.titleField")}
            </label>
            <Input
              value={formTitle}
              onChange={e => setFormTitle(e.target.value)}
              className={cn("h-10 sm:h-12 !text-xs md:!text-sm input-refined", errors.description && "border-red-500")}
            />
            {errors.description && <p className="text-[10px] text-red-500 ml-1">{errors.description}</p>}
          </div>

          {/* Amount field — only editable for ACTIVE debts */}
          {isActive && (
            <div className="space-y-1.5">
              <label className="text-mobile-caption font-semibold uppercase tracking-wider text-muted-foreground/80">
                {debt?.debt_type === "OWING" 
                  ? t("debts.originalBorrowedAmount", { defaultValue: "Original Borrowed Amount" }) 
                  : t("debts.originalLentAmount", { defaultValue: "Original Lent Amount" })}
              </label>
              <div className="relative flex items-center">
                <Input
                  type="text"
                  inputMode="numeric"
                  value={formAmount}
                  onChange={e => setFormAmount(formatAmountInput(e.target.value, 15))}
                  className={cn("h-10 sm:h-12 !text-xs md:!text-sm input-refined pr-12", errors.initial_amount && "border-red-500")}
                  placeholder="0"
                />
                <span className="absolute right-4 text-mobile-caption font-medium text-muted-foreground uppercase tracking-widest pointer-events-none select-none">UZS</span>
              </div>
              {errors.initial_amount && <p className="text-[10px] text-red-500 ml-1">{errors.initial_amount}</p>}
              {debt.total_charges > 0 && (
                <p className="text-[10px] text-muted-foreground ml-1 mt-0.5">
                  + {new Intl.NumberFormat('en-US').format(debt.total_charges).replace(/,/g, ' ')} in charges = {new Intl.NumberFormat('en-US').format((Number(String(formAmount).replace(/\s/g, '')) || 0) + debt.total_charges).replace(/,/g, ' ')} Total Obligation
                </p>
              )}
              {debt.is_money_transferred && (
                <p className="text-[10px] text-amber-500/80 ml-1 mt-0.5 italic">
                  {t("debts.edit.amountWalletWarning", { defaultValue: "Changing this will also adjust your wallet balance." })}
                </p>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-mobile-caption font-semibold uppercase tracking-wider text-muted-foreground/80">
                {t("debts.issueDateField")}
              </label>
              <Input
                type="date"
                value={formDate}
                onChange={e => setFormDate(e.target.value)}
                className={cn("h-10 sm:h-12 !text-xs md:!text-sm input-refined", errors.date && "border-red-500")}
              />
              {errors.date && <p className="text-[10px] text-red-500 ml-1">{errors.date}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="text-mobile-caption font-semibold uppercase tracking-wider text-muted-foreground/80">
                {t("debts.dueDateOptionalField")}
              </label>
              <Input
                type="date"
                value={formDueDate}
                onChange={e => setFormDueDate(e.target.value)}
                className={cn("h-10 sm:h-12 !text-xs md:!text-sm input-refined", errors.expected_return_date && "border-red-500")}
              />
              {errors.expected_return_date && <p className="text-[10px] text-red-500 ml-1">{errors.expected_return_date}</p>}
            </div>
          </div>

          {!debt?.is_money_transferred && debt?.debt_type === "OWING" && (
            <div className="space-y-1.5">
              <label className="text-mobile-caption font-semibold uppercase tracking-wider text-muted-foreground/80">
                {t("debts.expenseCategoryRequired", { defaultValue: "Expense Category (Required)" })}
              </label>
              <Select
                value={formExpenseCategory}
                onValueChange={(val) => setFormExpenseCategory(val)}
              >
                <SelectTrigger className="w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black rounded-md border-border shadow-sm h-10 sm:h-12 !text-xs md:!text-sm">
                  <SelectValue placeholder={t("debts.selectCategory", { defaultValue: "Select a category..." })} />
                </SelectTrigger>
                <SelectContent className="rounded-xl border-border shadow-2xl max-h-60">
                  {SPENDING_CATEGORIES.map(c => {
                    const Icon = categoryIconMap[c] || Circle;
                    return (
                      <SelectItem key={c} value={c}>
                        <div className="flex items-center gap-2">
                          <div className={cn("p-1 rounded-md", getCategoryBgClass(c))}>
                            <Icon className={cn("h-4 w-4", getCategoryColorClass(c))} />
                          </div>
                          <span>{t(`categories.${c}`, { defaultValue: c })}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
              {errors.expense_category && <p className="text-[10px] text-red-500 ml-1">{errors.expense_category}</p>}
            </div>
          )}

          {!debt?.is_money_transferred && debt?.debt_type === "OWED" && (
            <div className="space-y-1.5">
              <label className="text-mobile-caption font-semibold uppercase tracking-wider text-muted-foreground/80">
                {t("debts.incomeSourceOptional", { defaultValue: "Income Source (Optional)" })}
              </label>
              <Select
                value={formIncomeSourceId || "none"}
                onValueChange={(val) => setFormIncomeSourceId(val === "none" ? "" : val)}
              >
                <SelectTrigger className="w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black rounded-md border-border shadow-sm h-10 sm:h-12 !text-xs md:!text-sm">
                  <SelectValue placeholder={t("debts.selectIncomeSource", { defaultValue: "Select an income source..." })} />
                </SelectTrigger>
                <SelectContent className="rounded-xl border-border shadow-2xl max-h-60">
                  <SelectItem value="none" className="text-muted-foreground">{t("common.none", { defaultValue: "None" })}</SelectItem>
                  {incomeSourcesQuery.data?.filter(s => s.is_active).map(s => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <DialogFooter className="pt-4 gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1 sm:flex-none"
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 sm:flex-none"
            >
              {t("common.save")}
            </Button>
          </DialogFooter>

        </form>
      </DialogContent>
    </Dialog>
  );
}
