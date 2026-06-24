import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { useConfigureBorrowingSurvivalMutation } from "../hooks/useBudgetMutations";
import { AlertCircle } from "lucide-react";
import { formatAmountInput } from "@/lib/format";

export function ConfigureSurvivalDialog({
    open,
    onOpenChange,
    budgetYear,
    budgetMonth,
    initialEnabled = false,
    initialCap = 0,
}) {
    const { t } = useTranslation();
    const [enabled, setEnabled] = useState(initialEnabled);
    const [monthlyCap, setMonthlyCap] = useState(initialCap || 0);
    const { mutate: configureSurvival, isPending } = useConfigureBorrowingSurvivalMutation();

    useEffect(() => {
        if (open) {
            setEnabled(initialEnabled);
            setMonthlyCap(initialCap || 0);
        }
    }, [open, initialEnabled, initialCap]);

    const handleSave = () => {
        configureSurvival(
            {
                budget_year: budgetYear,
                budget_month: budgetMonth,
                enabled,
                monthly_cap: parseInt(String(monthlyCap).replace(/\s/g, ""), 10) || 0,
            },
            {
                onSuccess: () => {
                    onOpenChange(false);
                },
            }
        );
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>{t("budgets.configureSurvivalTitle", { defaultValue: "Borrowing Survival Mode" })}</DialogTitle>
                    <DialogDescription>
                        {t("budgets.configureSurvivalDesc", {
                            defaultValue: "Protect your budget from unexpected borrowing pressure by capping how much you can spend from borrowed money.",
                        })}
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    <div className="flex items-center justify-between space-x-2 rounded-lg border p-4">
                        <div className="space-y-0.5">
                            <Label className="text-base">{t("budgets.survivalEnableLabel", { defaultValue: "Enable Survival Mode" })}</Label>
                            <p className="text-sm text-muted-foreground">
                                {t("budgets.survivalEnableHint", { defaultValue: "Actively enforce a cap on borrowed spending." })}
                            </p>
                        </div>
                        <Switch
                            checked={enabled}
                            onCheckedChange={setEnabled}
                        />
                    </div>

                    {enabled && (
                        <div className="space-y-3">
                            <Label htmlFor="monthly-cap">
                                {t("budgets.survivalCapLabel", { defaultValue: "Monthly Cap" })}
                            </Label>
                            <Input
                                id="monthly-cap"
                                inputMode="numeric"
                                value={monthlyCap}
                                onChange={(e) => setMonthlyCap(formatAmountInput(e.target.value))}
                                placeholder="0"
                                className="w-full"
                            />
                            <div className="flex items-start gap-2 rounded-md bg-purple-500/10 p-3 text-sm text-purple-700 dark:text-purple-400">
                                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                                <p>
                                    {t("budgets.survivalWarningText", {
                                        defaultValue: "If you exceed this cap, the Budget Workspace will aggressively warn you that your plan is at high risk.",
                                    })}
                                </p>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
                        {t("common.cancel", { defaultValue: "Cancel" })}
                    </Button>
                    <Button onClick={handleSave} disabled={isPending}>
                        {isPending ? t("common.saving", { defaultValue: "Saving..." }) : t("common.save", { defaultValue: "Save changes" })}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
