import * as React from "react";
import { useTranslation } from "react-i18next";
import { Circle, CheckCircle2, ChevronRight, Check } from "lucide-react";
import { useRecurringOccurrencesQuery } from "../hooks/useRecurringDataQuery";
import { useConfirmRecurringOccurrenceMutation, useSkipRecurringMutation } from "../hooks/useRecurringMutations";
import { getWallets } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { categoryIconMap, getCategoryBgClass } from "@/lib/category";
import { cn } from "@/lib/utils";
import { formatDisplayDate, formatAmountInput, parseAmountInput } from "@/lib/format";
import { toISODateInTimeZone } from "@/lib/date";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { Plus, Trash2 } from "lucide-react";

export function NeedsConfirmationSection() {
    const { t } = useTranslation();
    const { data: occurrences } = useRecurringOccurrencesQuery("PENDING_CONFIRMATION");
    const { data: wallets } = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
    const confirmMutation = useConfirmRecurringOccurrenceMutation();
    const skipMutation = useSkipRecurringMutation();
    const isPremium = true; // Assumed since this is mounted in premium section

    const [confirmTarget, setConfirmTarget] = React.useState(null);
    const [confirmDate, setConfirmDate] = React.useState("");
    const [confirmAllocations, setConfirmAllocations] = React.useState([{ wallet_id: "", amount: "" }]);
    const [updateTemplate, setUpdateTemplate] = React.useState(false);

    if (!occurrences || occurrences.length === 0) return null;

    const walletRows = Array.isArray(wallets) ? wallets : [];
    const _getAppLang = () => String(t("lang") || "en").toLowerCase();

    const openConfirm = (occ) => {
        setConfirmTarget(occ);
        setConfirmDate(occ.scheduled_due_date);
        
        const defaultWallet = walletRows.find(w => w.is_default);
        setConfirmAllocations([{
            wallet_id: defaultWallet ? String(defaultWallet.id) : "",
            amount: formatAmountInput(String(occ.expected_amount))
        }]);
        setUpdateTemplate(false);
    };

    const handleAddAllocation = () => {
        setConfirmAllocations([...confirmAllocations, { wallet_id: "", amount: "" }]);
    };

    const handleRemoveAllocation = (idx) => {
        setConfirmAllocations(confirmAllocations.filter((_, i) => i !== idx));
    };

    const updateAllocation = (idx, field, value) => {
        const newAllocs = [...confirmAllocations];
        newAllocs[idx][field] = value;
        setConfirmAllocations(newAllocs);
    };

    const totalAmount = confirmAllocations.reduce((sum, a) => sum + Math.round(parseAmountInput(a.amount)), 0);
    const isValidAllocations = confirmAllocations.every(a => a.wallet_id && Math.round(parseAmountInput(a.amount)) > 0);

    const handleConfirm = async () => {
        if (!confirmTarget || !isValidAllocations) return;
        
        const payload = {
            actual_amount: totalAmount,
            actual_date: confirmDate,
            wallet_allocations: confirmAllocations.map(a => ({
                wallet_id: Number(a.wallet_id),
                amount: Math.round(parseAmountInput(a.amount))
            })),
            update_template_amount: updateTemplate
        };

        try {
            await confirmMutation.mutateAsync({ id: confirmTarget.id, payload });
            setConfirmTarget(null);
        } catch (e) {
            // Error is handled in mutation hook via toast
        }
    };

    const handleSkipQuick = async (occ) => {
        try {
            await skipMutation.mutateAsync({ 
                id: occ.id, 
                payload: { actual_date: occ.scheduled_due_date } 
            });
        } catch (e) {
            // Error is handled in mutation hook
        }
    };

    return (
        <div className="mb-6 space-y-3">
            <h3 className="text-lg font-semibold flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-amber-500" />
                {t("recurring.needsConfirmation", "Needs confirmation")} ({occurrences.length})
            </h3>
            
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {occurrences.map(occ => {
                    const Icon = categoryIconMap[occ.expected_category] || Circle;
                    const bgClass = getCategoryBgClass(occ.expected_category);

                    return (
                        <div key={occ.id} className="relative group overflow-hidden rounded-xl border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 transition-colors p-4 flex flex-col justify-between h-full min-h-[140px]">
                            <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-30 transition-opacity">
                                <Icon className="w-16 h-16" />
                            </div>
                            
                            <div className="relative z-10 space-y-1">
                                <div className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                                    {formatDisplayDate(occ.scheduled_due_date, _getAppLang())}
                                </div>
                                <h4 className="font-bold text-lg leading-tight line-clamp-1 pr-8">
                                    {occ.expected_title}
                                </h4>
                                <CurrencyAmount
                                    value={occ.expected_amount}
                                    format="compact"
                                    className="text-2xl font-black text-foreground tabular-nums tracking-tight mt-2"
                                    currencyClassName="text-sm font-bold opacity-50 ml-1"
                                />
                            </div>

                            <div className="relative z-10 mt-4 flex gap-2 w-full">
                                <Button 
                                    onClick={() => handleSkipQuick(occ)}
                                    variant="outline"
                                    className="flex-1 border-amber-500/30 text-amber-700 dark:text-amber-400 hover:bg-amber-500/10 rounded-lg"
                                >
                                    {t("common.skip", "Skip")}
                                </Button>
                                <Button 
                                    onClick={() => openConfirm(occ)}
                                    className="flex-[2] bg-amber-500 hover:bg-amber-600 text-white rounded-lg gap-2"
                                >
                                    <Check className="w-4 h-4" />
                                    {t("common.confirm", "Confirm")}
                                </Button>
                            </div>
                        </div>
                    );
                })}
            </div>

            <Dialog open={!!confirmTarget} onOpenChange={(open) => !open && setConfirmTarget(null)}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{t("recurring.confirmExpense", "Confirm Expense")}</DialogTitle>
                        <DialogDescription>
                            {confirmTarget?.expected_title}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4 py-4">
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-medium">{t("expenses.wallet", "Wallets & Amounts")}</label>
                                <span className="text-sm font-bold text-muted-foreground">
                                    Total: {formatAmountInput(String(totalAmount))} UZS
                                </span>
                            </div>
                            
                            <div className="space-y-3">
                                {confirmAllocations.map((alloc, idx) => (
                                    <div key={idx} className="flex items-center gap-2">
                                        <Select 
                                            value={alloc.wallet_id} 
                                            onValueChange={(val) => updateAllocation(idx, "wallet_id", val)}
                                        >
                                            <SelectTrigger className="flex-1">
                                                <SelectValue placeholder={t("expenses.selectWallet", "Select Wallet")} />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {walletRows.map((w) => (
                                                    <SelectItem key={w.id} value={String(w.id)}>
                                                        {w.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        
                                        <Input
                                            type="text"
                                            value={alloc.amount}
                                            onChange={(e) => updateAllocation(idx, "amount", formatAmountInput(e.target.value))}
                                            className="w-28 font-mono text-right"
                                            placeholder="Amount"
                                        />
                                        
                                        {confirmAllocations.length > 1 && (
                                            <Button 
                                                variant="ghost" 
                                                size="icon" 
                                                className="text-muted-foreground hover:text-red-500 shrink-0"
                                                onClick={() => handleRemoveAllocation(idx)}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        )}
                                    </div>
                                ))}
                            </div>
                            
                            <Button 
                                variant="outline" 
                                size="sm" 
                                className="w-full border-dashed"
                                onClick={handleAddAllocation}
                            >
                                <Plus className="w-4 h-4 mr-2" />
                                Add Wallet Split
                            </Button>
                        </div>
                        
                        <div className="space-y-2 pt-2">
                            <label className="text-sm font-medium">{t("common.date", "Date")}</label>
                            <Input
                                type="date"
                                value={confirmDate}
                                max={toISODateInTimeZone()}
                                onChange={(e) => setConfirmDate(e.target.value)}
                            />
                        </div>

                        <div className="flex items-center justify-between border rounded-lg p-3 mt-4">
                            <div className="space-y-0.5">
                                <label className="text-sm font-medium">{t("recurring.updateTemplateAmount", "Update template amount?")}</label>
                                <p className="text-xs text-muted-foreground">{t("recurring.updateTemplateAmountDesc", "Future occurrences will use this amount.")}</p>
                            </div>
                            <Switch checked={updateTemplate} onCheckedChange={setUpdateTemplate} />
                        </div>
                    </div>

                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="ghost" onClick={() => setConfirmTarget(null)}>
                            {t("common.cancel")}
                        </Button>
                        <Button 
                            onClick={handleConfirm}
                            disabled={confirmMutation.isPending || !isValidAllocations || !confirmDate || confirmDate > toISODateInTimeZone() || totalAmount <= 0}
                        >
                            {confirmMutation.isPending ? t("common.saving") : t("common.confirm")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
