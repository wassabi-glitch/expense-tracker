import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { CalendarClock, MoveDownRight, MoveUpRight, ChevronUp, Trash2, Pencil, History, CreditCard, Landmark, Coins, Wallet as WalletIcon, Plus, HeartHandshake, Archive, RotateCcw, MoreHorizontal } from "lucide-react";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TitleTooltip } from "@/components/TitleTooltip";
import { ActionMenu, ActionMenuItem, ActionMenuDivider } from "@/components/ActionMenu";
import { cn } from "@/lib/utils";
import { formatDisplayDate, formatAmountInput, formatUzs } from "@/lib/format";
import { toISODateInTimeZone } from "@/lib/date";
import { useArchiveDebtMutation, useRecordDebtPaymentMutation, useAddChargeMutation, useForgiveDebtMutation, useRestoreDebtMutation } from "../hooks/useDebtsMutations";
import { EditDebtModal } from "./EditDebtModal";
import { DebtHistoryModal } from "./DebtHistoryModal";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { getWallets, getIncomeSources } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { getWalletStyle } from "@/lib/walletStyles";

const getWalletTypeIcon = (type) => {
  switch (type) {
    case "CASH": return Coins;
    case "CREDIT": return Landmark;
    case "DEBIT": return CreditCard;
    case "PRELOADED": return CreditCard;
    default: return WalletIcon;
  }
};

export function DebtCard({ debt, onDelete }) {
  const { t, i18n } = useTranslation();
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();

  const [isExpanded, setIsExpanded] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentWalletId, setPaymentWalletId] = useState("");
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [paymentIncomeSourceId, setPaymentIncomeSourceId] = useState("");

  // Add Charge state
  const [isChargeExpanded, setIsChargeExpanded] = useState(false);
  const [chargeAmount, setChargeAmount] = useState("");
  const [chargeReason, setChargeReason] = useState("");

  // Confirm dialogs
  const [forgiveOpen, setForgiveOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);

  // 3-dot action menu
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState(null);

  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets });
  const incomeSourcesQuery = useQuery({
    queryKey: ["incomeSources"],
    queryFn: getIncomeSources,
    enabled: isExpanded && debt.debt_type === "OWED"
  });
  const recordPaymentMutation = useRecordDebtPaymentMutation();
  const addChargeMutation = useAddChargeMutation();
  const forgiveMutation = useForgiveDebtMutation();
  const archiveMutation = useArchiveDebtMutation();
  const restoreMutation = useRestoreDebtMutation();

  const isDeleteDisabled = debt.has_archived_transactions === true;

  const deleteDisabledReason = isDeleteDisabled
    ? t("debts.delete.wallet_archived", { defaultValue: "Cannot delete: Linked wallet is archived." })
    : undefined;

  // ── Status flags ──
  const isArchived = debt.is_archived === true;
  const isClosed = debt.lifecycle_status === "CLOSED" || Number(debt.remaining_amount || 0) <= 0;
  const isActive = !isArchived && !isClosed;
  const isPaid = isClosed;
  const isIOwe = debt.debt_type === "OWING";
  const isMuted = isClosed || isArchived;

  const accentColor = isIOwe ? "text-destructive" : "text-emerald-500";
  const bgAccentColor = isIOwe ? "bg-destructive" : "bg-emerald-500";
  const IconComponent = isIOwe ? MoveUpRight : MoveDownRight;

  const totalObligation = (debt.initial_amount || 0) + (debt.total_charges || 0);
  const paidAmount = debt.total_paid || 0;
  const progress = Math.min(100, Math.max(0, (paidAmount / (totalObligation || 1)) * 100));

  const dueDate = debt.expected_return_date || null;
  const isOverdue = debt.time_status === "OVERDUE";

  // ── Handlers ──
  const handleSavePayment = async () => {
    if (!paymentAmount || paymentAmount === "0") return;
    const rawVal = paymentAmount.replace(/\s/g, '');
    const amountVal = Number(rawVal);
    if (!amountVal) return;

    try {
      await recordPaymentMutation.mutateAsync({
        amount: amountVal,
        wallet_id: paymentWalletId ? Number(paymentWalletId) : null,
        income_source_id: paymentIncomeSourceId ? Number(paymentIncomeSourceId) : null,
        debt_id: debt.id,
        date: toISODateInTimeZone()
      });
      setIsExpanded(false);
      setPaymentAmount("");
      setPaymentIncomeSourceId("");
    } catch (e) { /* handled */ }
  };

  const handleAddCharge = async () => {
    if (!chargeAmount || chargeAmount === "0") return;
    const rawVal = chargeAmount.replace(/\s/g, '');
    const amountVal = Number(rawVal);
    if (!amountVal) return;

    try {
      await addChargeMutation.mutateAsync({
        debtId: debt.id,
        payload: { amount: amountVal, reason: chargeReason || null }
      });
      setIsChargeExpanded(false);
      setChargeAmount("");
      setChargeReason("");
    } catch (e) { /* handled */ }
  };

  const handleForgive = async () => {
    try {
      await forgiveMutation.mutateAsync(debt.id);
      setForgiveOpen(false);
    } catch (e) { /* handled */ }
  };

  const handleArchive = async () => {
    try {
      await archiveMutation.mutateAsync(debt.id);
      setArchiveOpen(false);
    } catch (e) { /* handled */ }
  };

  const handleRestore = async () => {
    try {
      await restoreMutation.mutateAsync(debt.id);
    } catch (e) { /* handled */ }
  };

  const openActionMenu = useCallback((event) => {
    event.stopPropagation();
    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();
    const menuWidth = 240;
    const menuHeight = 180;
    const viewportPadding = 8;
    const fitsBelow = rect.bottom + 6 + menuHeight <= window.innerHeight - viewportPadding;
    const top = fitsBelow ? rect.bottom + 6 : rect.top - 6 - menuHeight;
    const left = Math.max(viewportPadding, Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - viewportPadding));
    setMenuPosition({ top, left });
    setMenuOpen(prev => !prev);
  }, []);

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    setMenuPosition(null);
  }, []);

  return (
    <div className={cn(
      "group relative flex flex-col rounded-3xl border border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.02),transparent)] transition-all duration-300 p-4 sm:p-5 overflow-hidden",
      isMuted && "opacity-60 grayscale-[0.3]",
      isArchived && "opacity-40 grayscale-[0.5]",
      !isMuted && "hover:-translate-y-0.5 hover:shadow-md"
    )}>
      <div className={cn("absolute top-0 left-0 w-32 h-32 rounded-full blur-3xl -ml-16 -mt-16 opacity-20 pointer-events-none transition-opacity group-hover:opacity-35", bgAccentColor)} />

      {/* ── Header: Title + Badge ── */}
      <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4 z-10 relative">
        <div className="order-2 sm:order-1 flex min-w-0 flex-1 flex-col items-center sm:items-start w-full overflow-hidden">
          <TitleTooltip title={debt.description || "N/A"}>
            <h3 className="w-full cursor-default truncate text-center text-base font-semibold text-foreground/90 sm:text-left">
              {debt.description || "N/A"}
            </h3>
          </TitleTooltip>

          <div className="mt-2 flex flex-col items-center sm:items-start gap-1 w-full overflow-hidden">
            <TitleTooltip title={debt.counterparty_name}>
              <div className="flex items-center gap-1.5 text-mobile-caption font-medium uppercase tracking-wider text-muted-foreground/80 border border-border/50 bg-muted/20 px-2 py-0.5 rounded-md w-fit max-w-full cursor-default">
                <span className={cn("flex items-center justify-center size-4 object-contain opacity-80", accentColor)}>
                  <IconComponent className="size-3" />
                </span>
                <span className="truncate">{debt.counterparty_name}</span>
              </div>
            </TitleTooltip>
            <div className="flex flex-col gap-1 sm:gap-1.5 pl-1.5 w-full mt-1">
              {debt.date && (
                <div className="flex items-center gap-3 text-[10px] sm:text-xs font-medium text-muted-foreground/70 tracking-widest uppercase">
                  <span className="w-16 sm:w-20 shrink-0">{t("debts.card.issued")}</span>
                  <span className="font-semibold text-muted-foreground/90 whitespace-nowrap">{formatDisplayDate(debt.date, appLang)}</span>
                </div>
              )}
              {debt.expected_return_date && (
                <div className="flex items-center gap-3 text-[10px] sm:text-xs font-medium text-muted-foreground/70 tracking-widest uppercase">
                  <span className="w-16 sm:w-20 shrink-0">{t("debts.card.due")}</span>
                  <span className={cn("flex items-center gap-1 font-semibold whitespace-nowrap", isOverdue ? "text-destructive" : "text-muted-foreground/90")}>
                    <CalendarClock className={cn("size-3 hidden sm:block", isOverdue && "text-destructive")} />
                    {formatDisplayDate(debt.expected_return_date, appLang)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="order-1 sm:order-2 flex items-center gap-2">
          <DebtStatusBadge debt={debt} t={t} />
        </div>
      </div>

      {/* ── Amount + Progress ── */}
      <div className="mt-5 z-10 relative">
        <div className="flex flex-wrap items-baseline gap-2">
          <CurrencyAmount
            value={debt.remaining_amount}
            format="display"
            className={cn("text-2xl font-bold tabular-nums flex items-baseline gap-1", isMuted ? "text-muted-foreground" : accentColor)}
            currencyClassName="text-sm font-medium opacity-60"
          />
          <span className="text-ui-micro font-medium text-muted-foreground/50 uppercase tracking-tighter">
            {t("debts.card.remaining")}
          </span>
        </div>
      </div>

      <div className="mt-4 space-y-2 z-10 relative">
        <div className="flex items-center justify-between">
          <span className="text-ui-micro font-medium text-muted-foreground/60 uppercase tracking-widest">{t("debts.card.progress")}</span>
          <span className={cn("text-xs font-bold tabular-nums", isPaid || progress === 100 ? "text-emerald-500" : "text-muted-foreground")}>{progress.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/40 shadow-inner">
          <div
            className="h-full bg-emerald-500 transition-[width] duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* ── Inline Action Buttons (Record Payment + Charge only) ── */}
      {(
        <div className="mt-6 flex flex-wrap items-center justify-between gap-2 sm:gap-3 z-10 relative border-t border-border/50 pt-4">
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {isActive && (
              <Button
                variant={isExpanded ? "default" : "outline"}
                className="h-9 rounded-md font-semibold px-4 text-xs tracking-tight shadow-sm transition-colors"
                onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); setIsChargeExpanded(false); }}
              >
                {t("debts.card.recordPayment")}
              </Button>
            )}

            {isActive && (
              <Button
                variant={isChargeExpanded ? "default" : "outline"}
                className="h-9 rounded-md font-semibold px-3 text-xs tracking-tight shadow-sm transition-colors"
                onClick={(e) => { e.stopPropagation(); setIsChargeExpanded(!isChargeExpanded); setIsExpanded(false); }}
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                {t("debts.card.addCharge", { defaultValue: "Charge" })}
              </Button>
            )}

            {isArchived && (
              <Button
                variant="outline"
                className="h-9 rounded-md font-semibold px-4 text-xs tracking-tight shadow-sm"
                onClick={(e) => { e.stopPropagation(); handleRestore(); }}
                disabled={restoreMutation.isPending}
              >
                <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                {t("debts.card.restore", { defaultValue: "Restore" })}
              </Button>
            )}
          </div>

          <div data-action-popover>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="h-8 w-8 text-muted-foreground/40 hover:text-foreground transition-colors"
              onPointerDown={(ev) => ev.stopPropagation()}
              onClick={openActionMenu}
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* ── Record Payment Panel ── */}
      {isExpanded && isActive && (
        <div className="mt-5 space-y-4 rounded-2xl border border-border bg-muted/25 p-4 z-10 relative shadow-sm animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-ui-micro text-muted-foreground/80">
              {isIOwe ? t("debts.card.recordMade") : t("debts.card.recordReceived")}
            </p>
            <Button type="button" variant="ghost" size="sm" className="h-8 rounded-md px-2.5 text-muted-foreground hover:text-foreground" onClick={() => setIsExpanded(false)}>
              <ChevronUp className="mr-1 h-4 w-4" />
              {t("common.close")}
            </Button>
          </div>

          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold">{t("debts.amountUzs")}</label>
              <div className="relative flex items-center">
                <Input type="text" inputMode="numeric" value={paymentAmount} placeholder={t("debts.amountPlaceholder")} onChange={(e) => setPaymentAmount(formatAmountInput(e.target.value, 15))} className="rounded-md pr-12 border border-border/80" />
                <span className="absolute right-4 text-mobile-caption font-medium text-muted-foreground uppercase tracking-widest pointer-events-none select-none">UZS</span>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold">{t("wallet.label", { defaultValue: "Wallet / Card" })}</label>
              <Select value={String(paymentWalletId)} onValueChange={setPaymentWalletId}>
                <SelectTrigger className="rounded-md border border-border/80">
                  <SelectValue placeholder={t("wallet.placeholder", { defaultValue: "Select Wallet" })} />
                </SelectTrigger>
                <SelectContent className="rounded-xl border-border shadow-2xl">
                  {walletsQuery.data?.filter(w => w.is_active).map(w => {
                    const Icon = getWalletTypeIcon(w.wallet_type);
                    const s = getWalletStyle(w.color);
                    return (
                      <SelectItem key={w.id} value={String(w.id)} className="rounded-lg focus:bg-primary/10 py-2.5">
                        <div className="flex items-center gap-3">
                          <div className={cn("flex h-8 w-10 items-center justify-center rounded-md shrink-0 shadow-sm", s.className)}>
                            <Icon className="h-4.5 w-4.5 text-white" />
                          </div>
                          <span className="font-bold truncate text-xs">{w.name}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>

            {(() => {
              const currentVal = Number(paymentAmount.replace(/\s/g, '')) || 0;
              const selectedWallet = walletsQuery.data?.find(w => String(w.id) === String(paymentWalletId));
              const isInsufficient = isIOwe && selectedWallet && selectedWallet.balance < currentVal;

              // Smart Threshold Logic
              const threshold = Math.max(0, (debt.remaining_amount || 0) - (debt.total_charges || 0));
              const isCrossingThreshold = currentVal > threshold;
              const isOverpayment = currentVal > (debt.remaining_amount || 0);
              const needsIncomeSource = !isIOwe && isCrossingThreshold;
              const isSaveDisabled = !paymentAmount || currentVal === 0 || !paymentWalletId || recordPaymentMutation.isPending || isInsufficient || isOverpayment || (needsIncomeSource && !paymentIncomeSourceId);

              return (
                <>
                  {/* Conditional Income Source Dropdown */}
                  {!isIOwe && isCrossingThreshold && (
                    <div className="space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
                      <label className="text-xs font-semibold flex items-center gap-1.5 text-emerald-500">
                        {t("income.sourceLabel", { defaultValue: "Income Source (Profit portion)" })}
                        <TitleTooltip title={t("debts.card.incomeSourceHint", { defaultValue: "This payment includes interest/charges which are counted as Income. Please select a source." })}>
                          <Plus className="h-3 w-3 cursor-help opacity-60" />
                        </TitleTooltip>
                      </label>
                      <Select value={String(paymentIncomeSourceId)} onValueChange={setPaymentIncomeSourceId}>
                        <SelectTrigger className="rounded-md border border-emerald-500/30 bg-emerald-500/5">
                          <SelectValue placeholder={t("income.sourcePlaceholder", { defaultValue: "Select Source" })} />
                        </SelectTrigger>
                        <SelectContent className="rounded-xl border-border shadow-2xl">
                          {incomeSourcesQuery.data?.filter(s => s.is_active).map(s => (
                            <SelectItem key={s.id} value={String(s.id)} className="rounded-lg py-2.5">
                              <span className="font-bold text-xs">{s.name}</span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {/* Read-only Category for Owing Interest */}
                  {isIOwe && isCrossingThreshold && (
                    <div className="space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
                      <label className="text-xs font-semibold text-destructive">{t("expenses.categoryLabel", { defaultValue: "Category (Interest/Fees portion)" })}</label>
                      <div className="flex h-10 w-full items-center px-3 rounded-md border border-destructive/20 bg-destructive/5 text-xs font-medium cursor-not-allowed opacity-80">
                        {t("expenses.categories.DEBT_CHARGES", { defaultValue: "Debt Charges" })}
                      </div>
                    </div>
                  )}

                  {paymentWalletId && currentVal > 0 && isInsufficient && (
                    <p className="text-[10px] font-medium text-amber-500 bg-amber-500/10 px-2 py-1 rounded-md animate-in fade-in slide-in-from-top-1">
                      ⚠️ {t("wallets.insufficientFunds", { defaultValue: "Insufficient funds in this wallet." })}
                    </p>
                  )}

                  {isOverpayment && (
                    <p className="text-[10px] font-medium text-destructive bg-destructive/10 px-2 py-1 rounded-md animate-in fade-in slide-in-from-top-1">
                      ⚠️ {t("debts.transaction.overpaymentWarning", { defaultValue: "Amount exceeds remaining balance." })}
                    </p>
                  )}

                  <Button
                    className={cn(
                      "w-full rounded-md font-semibold shadow-sm relative transition-all duration-200",
                      isOverpayment ? "bg-destructive/50 hover:bg-destructive/50 cursor-not-allowed" : ""
                    )}
                    disabled={isSaveDisabled}
                    onClick={handleSavePayment}
                  >
                    {recordPaymentMutation.isPending ? <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : t("debts.card.savePayment")}
                  </Button>
                </>
              );
            })()}
          </div>
        </div>
      )}

      {/* ── Add Charge Panel ── */}
      {isChargeExpanded && isActive && (
        <div className="mt-5 space-y-4 rounded-2xl border border-border bg-muted/25 p-4 z-10 relative shadow-sm animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-ui-micro text-muted-foreground/80">
              {t("debts.card.addChargeHint", { defaultValue: "Add interest, penalty, or additional fee" })}
            </p>
            <Button type="button" variant="ghost" size="sm" className="h-8 rounded-md px-2.5 text-muted-foreground hover:text-foreground" onClick={() => setIsChargeExpanded(false)}>
              <ChevronUp className="mr-1 h-4 w-4" />
              {t("common.close")}
            </Button>
          </div>

          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold">{t("debts.amountUzs")}</label>
              <div className="relative flex items-center">
                <Input type="text" inputMode="numeric" value={chargeAmount} placeholder="0" onChange={(e) => setChargeAmount(formatAmountInput(e.target.value, 15))} className="rounded-md pr-12 border border-border/80" />
                <span className="absolute right-4 text-mobile-caption font-medium text-muted-foreground uppercase tracking-widest pointer-events-none select-none">UZS</span>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold">{t("debts.card.chargeReason", { defaultValue: "Reason (optional)" })}</label>
              <Input type="text" value={chargeReason} placeholder={t("debts.card.chargeReasonPlaceholder", { defaultValue: "e.g. Interest, Late fee" })} onChange={(e) => setChargeReason(e.target.value)} className="rounded-md border border-border/80" maxLength={200} />
            </div>

            <Button className="w-full rounded-md font-semibold shadow-sm relative disabled:opacity-70 disabled:pointer-events-none" disabled={!chargeAmount || chargeAmount === "0" || addChargeMutation.isPending} onClick={handleAddCharge}>
              {addChargeMutation.isPending ? <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : t("debts.card.addChargeConfirm", { defaultValue: "Add Charge" })}
            </Button>
          </div>
        </div>
      )}

      {/* ── 3-dot Action Menu (portal) ── */}
      <ActionMenu isOpen={menuOpen} position={menuPosition} onClose={closeMenu}>
        <ActionMenuItem icon={History} label={t("debts.history.title", { defaultValue: "Payment History" })} onClick={() => { closeMenu(); setIsHistoryOpen(true); }} />

        {isActive && (
          <>
            <ActionMenuItem icon={Pencil} label={t("common.edit")} onClick={() => { closeMenu(); setIsEditOpen(true); }} />
            <ActionMenuItem icon={HeartHandshake} label={t("debts.card.forgive", { defaultValue: "Forgive Debt" })} onClick={() => { closeMenu(); setForgiveOpen(true); }} />
          </>
        )}

        <ActionMenuDivider />

        {isArchived ? (
          <ActionMenuItem icon={RotateCcw} label={t("debts.card.restore", { defaultValue: "Restore" })} onClick={() => { closeMenu(); handleRestore(); }} />
        ) : (
          <ActionMenuItem icon={Archive} label={t("debts.card.archive", { defaultValue: "Archive" })} onClick={() => { closeMenu(); setArchiveOpen(true); }} />
        )}
        <ActionMenuItem
          icon={Trash2}
          label={t("common.delete")}
          variant="destructive"
          disabled={isDeleteDisabled || isArchived}
          disabledReason={deleteDisabledReason}
          onClick={() => { closeMenu(); onDelete && onDelete(debt); }}
        />
      </ActionMenu>

      {/* ── Modals ── */}
      <EditDebtModal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} debt={debt} />
      <DebtHistoryModal isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} debtId={debt.id} debtName={debt.description || debt.counterparty_name} />

      <ConfirmDialog
        open={forgiveOpen}
        onOpenChange={setForgiveOpen}
        title={t("debts.forgive.title", { defaultValue: "Forgive Debt" })}
        description={t("debts.forgive.description", {
          name: debt.counterparty_name,
          amount: formatUzs(debt.remaining_amount),
          defaultValue: `Mark the remaining ${formatUzs(debt.remaining_amount)} as forgiven? No wallet balance will change.`
        })}
        onConfirm={handleForgive}
        confirmText={t("debts.forgive.confirm", { defaultValue: "Forgive" })}
        cancelText={t("common.cancel")}
        isConfirming={forgiveMutation.isPending}
      />

      <ConfirmDialog
        open={archiveOpen}
        onOpenChange={setArchiveOpen}
        title={t("debts.archive.title", { defaultValue: "Archive Debt" })}
        description={t("debts.archive.description", {
          name: debt.counterparty_name,
          defaultValue: `Archive this debt? It will be hidden from your main view until restored.`
        })}
        onConfirm={handleArchive}
        confirmText={t("debts.archive.confirm", { defaultValue: "Archive" })}
        cancelText={t("common.cancel")}
        isConfirming={archiveMutation.isPending}
      />
    </div>
  );
}

function DebtStatusBadge({ debt, t }) {
  const baseClasses = "inline-flex shrink-0 items-center justify-center rounded-full text-center font-medium leading-[1.3] transition-all duration-200 min-h-6 sm:min-h-7 md:min-h-8 px-2 sm:px-3 py-[3px] md:py-1 text-mobile-caption sm:text-xs md:text-xs whitespace-nowrap min-w-[70px]";

  if (debt.is_archived === true) {
    return <span className={cn(baseClasses, "border border-muted-foreground/25 bg-muted/30 text-muted-foreground")}>{t("debts.status.archived", { defaultValue: "Archived" })}</span>;
  }
  if (debt.lifecycle_status === "CLOSED" || Number(debt.remaining_amount || 0) <= 0) {
    return <span className={cn(baseClasses, "border border-emerald-500/35 bg-emerald-500/15 text-emerald-500")}>{t("debts.status.closed", { defaultValue: "Closed" })}</span>;
  }
  const isOverdue = debt.time_status === "OVERDUE";
  return (
    <span className={cn(baseClasses, isOverdue ? "border border-destructive/35 bg-destructive/15 text-destructive dark:text-red-400" : "border border-primary/35 bg-primary/15 text-primary dark:text-primary")}>
      {isOverdue ? t("debts.card.overdue") : t("debts.status.open", { defaultValue: "Open" })}
    </span>
  );
}
