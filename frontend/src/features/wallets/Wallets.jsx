import React, { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  ArrowRightLeft,
  Pencil,
  Archive,
  ArrowRight,
  X,
  CreditCard,
  AlertCircle,
  Landmark,
  Coins,
  Wallet as WalletIcon,
  MoreVertical,
  History,
  Undo2,
  Scale,
  Star,
  Zap,
  Check,
  Target,
} from "lucide-react";

import { ActionMenu, ActionMenuItem, ActionMenuDivider } from "@/components/ActionMenu";
import { InteractiveTooltip } from "@/components/InteractiveTooltip";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { getWallets } from "@/lib/api";
import { useWalletMutations } from "./hooks/useWalletMutations";
import { WALLET_STYLE_KEYS, getWalletStyle } from "@/lib/walletStyles";
import { formatAmountInput, parseAmountInput } from "@/lib/format";
import { toISODateInTimeZone } from "@/lib/date";
import { cn } from "@/lib/utils";
import { localizeApiError } from "@/lib/errorMessages";
import { walletTransferSchema } from "./walletSchemas";
import { AddWalletDialog } from "./components/AddWalletDialog";
import { QuickActionDialog } from "./components/QuickActionDialog";
import { ReconcileDialog } from "./components/ReconcileDialog";
import { WalletTransactionsDialog } from "./components/WalletTransactionsDialog";

export default function Wallets() {
  const { t } = useTranslation();

  // -- Data Fetching --
  const { data: walletsRaw = [], isLoading } = useQuery({
    queryKey: ["wallets"],
    queryFn: getWallets,
  });
  const wallets = Array.isArray(walletsRaw) ? walletsRaw : [];
  const {
    createMutation,
    updateMutation,
    deleteMutation,
    transferMutation,
    setDefaultMutation,
    recordFeeMutation,
    recordInterestMutation,
    reconcileMutation
  } = useWalletMutations();

  // -- UI State --
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingWalletId, setEditingWalletId] = useState(null);
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [showArchived, setShowArchived] = useState(false);
  const [walletMenuForId, setWalletMenuForId] = useState(null);
  const [walletMenuPosition, setWalletMenuPosition] = useState(null);
  const [transactionsWalletId, setTransactionsWalletId] = useState(null);

  const [activeActionWalletId, setActiveActionWalletId] = useState(null);
  const [isQuickActionOpen, setIsQuickActionOpen] = useState(false);
  const [quickActionType, setQuickActionType] = useState(null);
  const [isReconcileOpen, setIsReconcileOpen] = useState(false);

  const activeActionWallet = useMemo(() =>
    wallets.find(w => w.id === activeActionWalletId),
    [wallets, activeActionWalletId]
  );
  const transactionsWallet = useMemo(() =>
    wallets.find(w => w.id === transactionsWalletId),
    [wallets, transactionsWalletId]
  );

  // -- Form States (Add/Edit) --
  const [name, setName] = useState("");
  const [balance, setBalance] = useState("");
  const [style, setStyle] = useState("default");
  const [touchedFields, setTouchedFields] = useState({});
  const [submitError, setSubmitError] = useState("");

  // -- Transfer States --
  const [fromWalletId, setFromWalletId] = useState("");
  const [toWalletId, setToWalletId] = useState("");
  const [transferAmount, setTransferAmount] = useState("");
  const [transferNote, setTransferNote] = useState("");
  const [transferHasFee, setTransferHasFee] = useState(false);
  const [transferFeeAmount, setTransferFeeAmount] = useState("");
  const [transferFeeWalletId, setTransferFeeWalletId] = useState("");
  const [transferFeeNote, setTransferFeeNote] = useState("");
  const [touchedTransfer, setTouchedTransfer] = useState(false);
  const [transferError, setTransferError] = useState("");
  const [transferConflict, setTransferConflict] = useState(null);

  const transferParsed = useMemo(() => {
    const payload = {
      from_wallet_id: Number(fromWalletId),
      to_wallet_id: Number(toWalletId),
      amount: transferAmount,
      note: transferNote || null,
    };
    if (transferHasFee) {
      payload.fee_amount = transferFeeAmount;
      payload.fee_wallet_id = Number(transferFeeWalletId || fromWalletId);
      payload.fee_note = transferFeeNote || null;
    }
    return walletTransferSchema.safeParse(payload);
  }, [fromWalletId, toWalletId, transferAmount, transferNote, transferHasFee, transferFeeAmount, transferFeeWalletId, transferFeeNote]);

  // -- Handlers --
  useEffect(() => {
    const onPointerDown = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("[data-action-popover]")) return;
      setWalletMenuForId(null);
      setWalletMenuPosition(null);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const openWalletActions = (event, wallet) => {
    const button = event.currentTarget;
    const rect = button instanceof HTMLElement ? button.getBoundingClientRect() : null;
    const menuWidth = 200;
    const menuHeight = 320;
    const viewportPadding = 8;
    setWalletMenuForId((prev) => {
      if (prev === wallet.id) {
        setWalletMenuPosition(null);
        return null;
      }
      if (!rect) return null;
      const fitsBelow = rect.bottom + 6 + menuHeight <= window.innerHeight - viewportPadding;
      const top = fitsBelow ? rect.bottom + 6 : rect.top - 6 - menuHeight;
      const left = Math.max(
        viewportPadding,
        Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - viewportPadding)
      );
      setWalletMenuPosition({ top, left });
      return wallet.id;
    });
  };

  const handleStartAdd = () => setIsAddDialogOpen(true);

  const handleCreate = async (formData) => {
    try {
      await createMutation.mutateAsync({
        name: formData.name,
        wallet_type: formData.wallet_type,
        accounting_type: formData.accounting_type,
        initial_balance: parseAmountInput(formData.initial_balance) || 0,
        has_overdraft: formData.has_overdraft,
        overdraft_limit: parseAmountInput(formData.overdraft_limit) || 0,
        credit_limit: parseAmountInput(formData.credit_limit) || 0,
        allow_overlimit: formData.allow_overlimit,
        can_fund_goals: formData.can_fund_goals,
        color: formData.color
      });
      setIsAddDialogOpen(false);
    } catch (err) { setSubmitError(localizeApiError(err.message, t)); }
  };

  const handleStartEdit = (w) => {
    setEditingWalletId(w.id);
    setName(w.name || "");
    setStyle(w.color || "default");
    setTouchedFields({});
    setSubmitError("");
  };

  const handleUpdate = async () => {
    try {
      await updateMutation.mutateAsync({
        id: editingWalletId,
        payload: {
          name,
          color: style
        }
      });
      setEditingWalletId(null);
    } catch (err) { setSubmitError(localizeApiError(err.message, t)); }
  };

  const handleSetDefault = async (walletId) => {
    try {
      await setDefaultMutation.mutateAsync(walletId);
    } catch (err) { /* silent fail or toast */ }
  };

  const handleToggleGoalFunding = async (wallet) => {
    try {
      await updateMutation.mutateAsync({
        id: wallet.id,
        payload: { can_fund_goals: !wallet.can_fund_goals }
      });
    } catch (err) {
      setSubmitError(localizeApiError(err.message, t));
    }
  };

  const handleQuickAction = async (formData) => {
    try {
      if (quickActionType === "FEE") {
        await recordFeeMutation.mutateAsync({
          id: activeActionWalletId,
          payload: { ...formData, action_type: "FEE" }
        });
      } else {
        await recordInterestMutation.mutateAsync({
          id: activeActionWalletId,
          payload: { ...formData, action_type: "INTEREST" }
        });
      }
      setIsQuickActionOpen(false);
    } catch (err) { /* err handled by mutation or global toast */ }
  };

  const handleReconcile = async (formData) => {
    try {
      await reconcileMutation.mutateAsync({
        id: activeActionWalletId,
        payload: formData
      });
      setIsReconcileOpen(false);
    } catch (err) { /* err handled */ }
  };
  const visibleWallets = useMemo(() => 
    wallets
      .filter(w => w.is_active !== false)
      .sort((a, b) => a.id - b.id),
    [wallets]
  );

  const archivedWallets = useMemo(() => 
    wallets
      .filter(w => w.is_active === false)
      .sort((a, b) => a.id - b.id),
    [wallets]
  );

  const operationalWallets = visibleWallets;

  const handleTransfer = async (goalResolution = null) => {
    setTouchedTransfer(true);
    if (!transferParsed.success) return;
    try {
      // Inject localized date to satisfy the backend schema & maintain timezone accuracy
      const payload = {
        ...transferParsed.data,
        date: toISODateInTimeZone()
      };
      if (goalResolution) payload.goal_resolution = goalResolution;
      await transferMutation.mutateAsync(payload);
      setTransferAmount(""); setTransferNote(""); setTransferHasFee(false); setTransferFeeAmount(""); setTransferFeeWalletId(""); setTransferFeeNote(""); setTouchedTransfer(false); setTransferError(""); setTransferConflict(null);
    } catch (err) {
      setTransferError(localizeApiError(err.message, t));
      setTransferConflict(["wallets.goal_protection_conflict", "wallets.fee_goal_protection_conflict"].includes(err?.detail?.code) ? err.detail : null);
    }
  };



  const sourceWallet = visibleWallets.find(w => String(w.id) === fromWalletId);
  const targetWallet = visibleWallets.find(w => String(w.id) === toWalletId);
  const feeWalletOptions = operationalWallets.filter((wallet) => wallet.wallet_type?.toUpperCase() !== "CASH");

  const transferFloorCheck = useMemo(() => {
    if (!transferParsed.success || !sourceWallet) return { safe: true };
    const amount = transferParsed.data.amount;
    const potentialBalance = sourceWallet.current_balance - amount;

    let floor = 0;
    const isCredit = sourceWallet.wallet_type?.toUpperCase() === "CREDIT";
    const isPreloaded = sourceWallet.wallet_type?.toUpperCase() === "PRELOADED";

    if (isCredit) {
      floor = -sourceWallet.credit_limit;
      if (sourceWallet.allow_overlimit) floor = -Infinity;
    } else if (isPreloaded) {
      floor = sourceWallet.has_overdraft ? (sourceWallet.overdraft_limit > 0 ? -sourceWallet.overdraft_limit : -Infinity) : 0;
    } else { // Debit
      floor = sourceWallet.has_overdraft ? -sourceWallet.overdraft_limit : 0;
    }

    return {
      safe: potentialBalance >= floor,
      isViolated: potentialBalance < floor
    };
  }, [transferParsed, sourceWallet]);


  const canTransfer = transferParsed.success && transferFloorCheck.safe && !transferMutation.isPending;

  if (isLoading) return <div className="flex h-[60vh] items-center justify-center"><LoadingSpinner className="h-8 w-8 text-primary" /></div>;

  return (
    <div className="w-full px-page py-8 space-y-6">
      <PageHeader title={t("wallets.cardTitle", { defaultValue: "My Wallets" })} description={t("wallets.cardDesc")}>
        <Button onClick={handleStartAdd} disabled={isAddDialogOpen}>
          <Plus className="mr-2 h-4 w-4" />
          {t("wallets.addAccount")}
        </Button>
      </PageHeader>

      {/* 🚀 Integrated Power-Transfer Console (High Density) */}
      <Card className="overflow-hidden border-none bg-muted/30 shadow-none ring-1 ring-border/40">
        <CardContent className="p-4 sm:p-6">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
            {/* Horizontal Mini-Card Logic */}
            <div className="flex flex-1 items-center justify-between gap-4">
              <div className="flex flex-1 flex-col gap-2">
                <span className="text-ui-micro font-bold uppercase tracking-widest text-muted-foreground/50">{t("wallets.from")}</span>
                <div className="flex items-center gap-3">
                  <Select value={fromWalletId} onValueChange={setFromWalletId}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={t("wallet.placeholder")} />
                    </SelectTrigger>
                    <SelectContent>
                      {operationalWallets.map(w => (
                        <SelectItem key={w.id} value={String(w.id)}>{w.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {sourceWallet && <MiniCardPreview wallet={sourceWallet} />}
                </div>
              </div>

              <div className="pt-6 text-primary/40 shrink-0">
                <ArrowRight className="h-6 w-6" />
              </div>

              <div className="flex flex-1 flex-col gap-2">
                <span className="text-ui-micro font-bold uppercase tracking-widest text-muted-foreground/50">{t("wallets.to")}</span>
                <div className="flex items-center gap-3">
                  <Select value={toWalletId} onValueChange={setToWalletId}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder={t("wallet.placeholder")} />
                    </SelectTrigger>
                    <SelectContent>
                      {operationalWallets.map(w => (
                        <SelectItem key={w.id} value={String(w.id)} disabled={String(w.id) === fromWalletId}>{w.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {targetWallet && <MiniCardPreview wallet={targetWallet} />}
                </div>
              </div>
            </div>

            {/* Amount & Confirm */}
            <div className="flex flex-col gap-4 lg:w-[320px] shrink-0">
              <div className="relative">
                <Input
                  value={transferAmount}
                  maxLength={15}
                  onChange={(e) => setTransferAmount(formatAmountInput(e.target.value))}
                  placeholder="0"
                  className={cn(
                    "pr-12 font-mono font-bold text-lg",
                    transferFloorCheck.isViolated && "border-red-500 text-red-500 focus-visible:ring-red-500"
                  )}
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground/30">UZS</span>
              </div>
              <div className="rounded-md border border-border/60 bg-background/40 p-3">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 text-left text-sm font-medium"
                  onClick={() => {
                    setTransferHasFee((prev) => !prev);
                    if (!transferFeeWalletId) setTransferFeeWalletId(fromWalletId);
                  }}
                >
                  <span>Add fee</span>
                  <span className={cn(
                    "rounded-full px-2 py-0.5 text-xs",
                    transferHasFee ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                  )}>
                    {transferHasFee ? "On" : "Off"}
                  </span>
                </button>
                {transferHasFee ? (
                  <div className="mt-3 grid gap-2">
                    <Input
                      value={transferFeeAmount}
                      maxLength={15}
                      inputMode="numeric"
                      onChange={(e) => setTransferFeeAmount(formatAmountInput(e.target.value))}
                      placeholder="Fee amount"
                    />
                    <Select value={transferFeeWalletId || fromWalletId} onValueChange={setTransferFeeWalletId}>
                      <SelectTrigger>
                        <SelectValue placeholder="Fee wallet" />
                      </SelectTrigger>
                      <SelectContent>
                        {feeWalletOptions.map((wallet) => (
                          <SelectItem key={wallet.id} value={String(wallet.id)}>
                            {wallet.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      value={transferFeeNote}
                      maxLength={200}
                      onChange={(e) => setTransferFeeNote(e.target.value)}
                      placeholder="Fee note"
                    />
                    <p className="text-xs text-muted-foreground">
                      The fee is recorded as a linked bank-fee expense. It must come from free money, not protected goal money.
                    </p>
                  </div>
                ) : null}
              </div>
              <Button
                className="w-full"
                disabled={!canTransfer}
                onClick={() => handleTransfer()}
              >
                {transferMutation.isPending ? <LoadingSpinner size="sm" /> : t("wallets.confirmTransfer")}
              </Button>
            </div>
          </div>
          {transferFloorCheck.isViolated && !transferError && (
            <p className="mt-3 text-xs font-medium text-red-500 flex items-center gap-1 animate-in fade-in slide-in-from-top-1">
              <AlertCircle className="h-3 w-3" /> {t("wallets.insufficientFunds")}
            </p>
          )}
          {transferError && <p className="mt-3 text-xs font-medium text-red-500 flex items-center gap-1 animate-in fade-in slide-in-from-top-1"><AlertCircle className="h-3 w-3" /> {transferError}</p>}
          {transferConflict && (
            <div className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
              <p className="font-medium">
                {t("wallets.goalProtectionConflictDetail", {
                  defaultValue: "{{protected}} is reserved for goals. This transfer needs {{required}} of that goal money to be resolved.",
                  protected: formatAmountInput(String(transferConflict.protected_for_goals || 0)),
                  required: formatAmountInput(String(transferConflict.required_goal_resolution_amount || transferConflict.protected_amount_touched || 0)),
                })}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={transferMutation.isPending}
                  onClick={() => handleTransfer("MOVE_TO_DESTINATION")}
                >
                  {t("wallets.moveGoalFunding", { defaultValue: "Move goal funding" })}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={transferMutation.isPending}
                  onClick={() => handleTransfer("RELEASE")}
                >
                  {t("wallets.releaseGoalFunding", { defaultValue: "Release goal funding" })}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 🚀 Main Grid (Active) */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {visibleWallets.map((wallet) => (
          editingWalletId === wallet.id ? (
            <LiveEditorCard
              key={wallet.id} mode="edit" name={name} style={style}
              setName={setName} setStyle={setStyle} onSave={handleUpdate}
              onCancel={() => setEditingWalletId(null)}
              isPending={updateMutation.isPending} t={t}
            />
          ) : (
            <WalletDisplayCard
              key={wallet.id} wallet={wallet}
              onOpenActions={(e) => openWalletActions(e, wallet)}
              t={t}
            />
          )
        ))}

        <button onClick={handleStartAdd} className="group flex h-[215px] flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-muted-foreground/20 bg-muted/5 transition-all hover:border-primary/40 hover:bg-primary/5 active:scale-95">
          <div className="rounded-full bg-muted-foreground/10 p-3 text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary"><Plus className="h-6 w-6" /></div>
          <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground group-hover:text-primary">{t("wallets.addAccount")}</span>
        </button>
      </div>

      {/* 🚀 Vault Section (Archived Collapsible) */}
      {archivedWallets.length > 0 && (
        <div className="space-y-4 pt-4">
          <Button
            variant="ghost"
            className="px-0 text-muted-foreground hover:bg-transparent hover:text-foreground"
            onClick={() => setShowArchived((prev) => !prev)}
          >
            {showArchived
              ? t("wallets.hideArchived", { defaultValue: "Hide Archived Wallets" })
              : t("wallets.showArchived", { count: archivedWallets.length, defaultValue: `Show Archived Wallets (${archivedWallets.length})` })
            }
          </Button>

          {showArchived && (
            <div className="grid gap-4 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {archivedWallets.map(wallet => (
                <WalletDisplayCard
                  key={wallet.id} wallet={wallet}
                  t={t}
                  onRestore={() => updateMutation.mutate({ id: wallet.id, payload: { is_active: true } })}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <AddWalletDialog
        isOpen={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        onSave={handleCreate}
        isPending={createMutation.isPending}
        t={t}
      />

      <ConfirmDialog
        open={!!archiveTarget}
        onOpenChange={(open) => !open && setArchiveTarget(null)}
        title={archiveTarget?.current_balance !== 0 ? t("wallets.archive_not_empty") : t("wallets.archiveTitle", { defaultValue: "Archive" })}
        description={archiveTarget?.current_balance !== 0
          ? t("wallets.archive_not_empty")
          : t("wallets.archiveWarning", { name: archiveTarget?.name, defaultValue: `Are you sure you want to archive ${archiveTarget?.name}? It will be moved to the Vault.` })}
        confirmDisabled={archiveTarget?.current_balance !== 0}
        confirmText={t("wallets.archiveButton", { defaultValue: "Archive" })}
        cancelText={t("common.cancel")}
        isConfirming={deleteMutation.isPending}
        onConfirm={async () => {
          try {
            await deleteMutation.mutateAsync(archiveTarget.id);
            setArchiveTarget(null);
            setEditingWalletId(null);
          } catch (e) {
            setSubmitError(localizeApiError(e.message, t));
          }
        }}
      />

      <ActionMenu
        isOpen={!!walletMenuForId}
        position={walletMenuPosition}
        onClose={() => setWalletMenuForId(null)}
        zIndex={200}
      >
        {(() => {
          const w = wallets.find(w => w.id === walletMenuForId);
          if (!w) return null;
          const isOperational = w.is_active !== false;
          const isCash = w.wallet_type === "CASH";

          return (
            <>
              {(!isCash) && (
                <>
                  <ActionMenuItem
                    icon={Zap}
                    disabled={!isOperational}
                    label={t("wallets.action_fee", { defaultValue: "Record Fee" })}
                    onClick={() => {
                      setActiveActionWalletId(walletMenuForId);
                      setQuickActionType("FEE");
                      setIsQuickActionOpen(true);
                      setWalletMenuForId(null);
                    }}
                  />
                  <ActionMenuItem
                    icon={Zap}
                    disabled={!isOperational}
                    label={t("wallets.action_interest", { defaultValue: "Record Interest" })}
                    onClick={() => {
                      setActiveActionWalletId(walletMenuForId);
                      setQuickActionType("INTEREST");
                      setIsQuickActionOpen(true);
                      setWalletMenuForId(null);
                    }}
                  />
                </>
              )}
              <ActionMenuItem
                icon={Undo2}
                disabled={!isOperational}
                label={t("wallets.action_refund", { defaultValue: "Issue Refund" })}
                onClick={() => {
                  window.location.href = "/expenses";
                  setWalletMenuForId(null);
                }}
              />
              <ActionMenuDivider />
              <ActionMenuItem
                icon={ArrowRightLeft}
                disabled={!isOperational}
                label={t("wallets.moveMoney")}
                onClick={() => {
                  setFromWalletId(String(walletMenuForId));
                  window.scrollTo({ top: 0, behavior: "smooth" });
                  setWalletMenuForId(null);
                }}
              />
              <ActionMenuItem
                icon={History}
                label={t("wallets.viewTransactions", { defaultValue: "View Transactions" })}
                onClick={() => {
                  setTransactionsWalletId(walletMenuForId);
                  setWalletMenuForId(null);
                }}
              />
              <ActionMenuItem
                icon={Scale}
                disabled={!isOperational}
                label={t("wallets.adjust_balance", { defaultValue: "Adjust Balance" })}
                onClick={() => {
                  setActiveActionWalletId(walletMenuForId);
                  setIsReconcileOpen(true);
                  setWalletMenuForId(null);
                }}
              />
              <ActionMenuItem
                icon={Star}
                label={t("wallets.set_default", { defaultValue: "Set as Default" })}
                onClick={() => {
                  handleSetDefault(walletMenuForId);
                  setWalletMenuForId(null);
                }}
              />
              {w.wallet_type !== "CREDIT" && (
                <ActionMenuItem
                  icon={Target}
                  disabled={!isOperational}
                  label={
                    w.can_fund_goals
                      ? t("wallets.disable_goal_funding", { defaultValue: "Disable Goal Funding" })
                      : t("wallets.enable_goal_funding", { defaultValue: "Enable Goal Funding" })
                  }
                  onClick={() => {
                    handleToggleGoalFunding(w);
                    setWalletMenuForId(null);
                  }}
                />
              )}
              <ActionMenuDivider />
              <ActionMenuItem
                icon={Pencil}
                label={t("common.edit", { defaultValue: "Edit Properties" })}
                onClick={() => {
                  handleStartEdit(w);
                  setWalletMenuForId(null);
                }}
              />
              <ActionMenuItem
                icon={Archive}
                variant="destructive"
                label={t("wallets.archiveButton", { defaultValue: "Archive" })}
                onClick={() => {
                  setArchiveTarget(w);
                  setWalletMenuForId(null);
                }}
              />
            </>
          );
        })()}
      </ActionMenu>

      <QuickActionDialog
        isOpen={isQuickActionOpen}
        onOpenChange={setIsQuickActionOpen}
        onSave={handleQuickAction}
        isPending={recordFeeMutation.isPending || recordInterestMutation.isPending}
        wallet={activeActionWallet}
        actionType={quickActionType}
        t={t}
      />

      <ReconcileDialog
        isOpen={isReconcileOpen}
        onOpenChange={setIsReconcileOpen}
        onSave={handleReconcile}
        isPending={reconcileMutation.isPending}
        wallet={activeActionWallet}
        t={t}
      />

      <WalletTransactionsDialog
        isOpen={!!transactionsWallet}
        onOpenChange={(open) => {
          if (!open) setTransactionsWalletId(null);
        }}
        wallet={transactionsWallet}
      />
    </div>
  );
}

// --- Visual Sub-Components ---

const getWalletTypeIcon = (type) => {
  switch (type) {
    case "CASH": return Coins;
    case "CREDIT": return Landmark;
    case "DEBIT": return CreditCard;
    case "PRELOADED": return CreditCard;
    case "SAVINGS": return WalletIcon;
    default: return WalletIcon;
  }
};

const getWalletTypeLabelKey = (type) => {
  if (!type) return "wallets.label";
  return type === "PRELOADED" ? "wallets.type_prepaid" : `wallets.type_${type.toLowerCase()}`;
};

function MiniCardPreview({ wallet }) {
  const s = getWalletStyle(wallet.color);
  const Icon = getWalletTypeIcon(wallet.wallet_type);

  return (
    <div className={cn(
      "hidden lg:flex relative h-12 w-16 items-center justify-center rounded-lg shadow-sm border border-white/10 shrink-0 opacity-90 transition-all hover:scale-110 overflow-hidden",
      s.className
    )}>
      <Icon className="h-5 w-5 text-white/80" />
    </div>
  );
}

function WalletDisplayCard({ wallet, onOpenActions, onRestore, t }) {
  const s = getWalletStyle(wallet.color);
  const isOperational = wallet.is_active !== false;
  const isArchived = wallet.is_active === false;

  const TypeIcon = getWalletTypeIcon(wallet.wallet_type);

  // Credit Analysis Logic
  const isCredit = wallet.wallet_type?.toUpperCase() === "CREDIT";
  const limitValue = isCredit ? wallet.credit_limit : (wallet.has_overdraft ? wallet.overdraft_limit : 0);
  const hasLimit = isOperational && limitValue > 0;

  // Debt is what we owe. For Credit info it's the mag of negative balance.
  // For Debit/Preloaded, debt is also the magnitude of negative balance.
  const signedBalance = wallet.current_balance;
  const debtMagnitude = Math.abs(Math.min(0, signedBalance));
  const isDebt = signedBalance < 0;

  const isOverlimit = debtMagnitude > limitValue;
  const overlimitAmount = isOverlimit ? debtMagnitude - limitValue : 0;
  const utilizationPercent = hasLimit ? Math.min(100, (debtMagnitude / limitValue) * 100) : 0;

  // Formatting for display:
  // Industry standard for Credit Cards on statements: 
  // Debt = Positive. Overfill = Negative.
  const displayBalance = isCredit ? -signedBalance : signedBalance;

  // Progress Bar Visibility Logic (Sartlog UX standard)
  // 1. Credit Card: Always show progress if limit > 0
  // 2. Debit/Preloaded: ONLY show progress if balance < 0 (isDebt)
  const showProgressBar = hasLimit && (isCredit || isDebt);

  // High-contrast coloring for the progress bar based on utilization
  let indicatorColor = "bg-white";
  if (isOverlimit || utilizationPercent >= 90) {
    indicatorColor = "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]";
  } else if (utilizationPercent >= 75) {
    indicatorColor = "bg-amber-400";
  }

  return (
    <Card className={cn(
      "group relative h-[215px] overflow-hidden border-none transition-all duration-300 shadow-md",
      s.className,
      isOperational ? "hover:scale-[1.02]" : "",
      isArchived && "grayscale opacity-50 cursor-not-allowed transition-all duration-500"
    )}>
      <CardContent className={cn("flex h-full flex-col p-6", isArchived && "pointer-events-none")}>
        <div className="flex items-start justify-between">
          <div className="flex flex-1 flex-col gap-2 text-white min-w-0">
            <InteractiveTooltip content={wallet.name} side="top">
              <div className="flex items-center gap-2 cursor-help">
                <TypeIcon className="h-5 w-5 opacity-80 shrink-0" />
                <h2 className="text-xl font-black tracking-tight truncate">{wallet.name}</h2>
              </div>
            </InteractiveTooltip>
            <div className="flex flex-wrap gap-1">
              {isArchived && <Badge variant="secondary" className="w-fit h-4 text-[8px] bg-black/40 text-white border-none uppercase tracking-tighter">{t("wallets.archivedBadge", { defaultValue: "Archived" })}</Badge>}
              {isOperational && wallet.has_overdraft && <Badge variant="secondary" className="w-fit h-4 text-[8px] bg-white/20 text-white border-none uppercase">{t("wallets.overdraft_badge", { defaultValue: "Overdraft" })}</Badge>}
              {isOperational && wallet.can_fund_goals && <Badge variant="secondary" className="w-fit h-4 text-[8px] bg-white/20 text-white border-none uppercase">{t("wallets.goal_funding_badge", { defaultValue: "Goals" })}</Badge>}
              <span className="text-[8px] font-black uppercase tracking-widest opacity-40 ml-1 mt-0.5">
                {wallet.wallet_type ? t(getWalletTypeLabelKey(wallet.wallet_type)) : t("wallets.label")}
              </span>
            </div>
          </div>

          {!isArchived && (
            <div data-action-popover className="relative z-10 flex shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
              <Button size="icon" variant="ghost" className="h-8 w-8 rounded-full bg-white/20 hover:bg-white/30 text-white" onClick={(e) => { e.stopPropagation(); onOpenActions(e); }}>
                <MoreVertical className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        <div className="mt-4 space-y-4 text-white">
          <div className="space-y-1">
            <CurrencyAmount value={displayBalance} format="display" className="text-3xl font-black tracking-tighter" />

            {hasLimit && (
              <div className="flex items-center justify-between text-[8px] font-black uppercase tracking-widest leading-none">
                {isOverlimit ? (
                  <div className="flex items-center gap-1 text-red-100 bg-red-600/40 px-1.5 py-0.5 rounded-full">
                    <AlertCircle className="h-2 w-2" />
                    <span>{isCredit ? t("wallets.overlimit_short", { defaultValue: "Overlimit" }) : t("wallets.overdraft_limit_exceeded", { defaultValue: "Overdraft limit exceeded" })} {t("wallets.by_amount", { defaultValue: "by" })} <CurrencyAmount value={overlimitAmount} includeCurrency={false} /> <span className="opacity-60 ml-0.5">UZS</span></span>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 opacity-60">
                    <span>{isCredit ? t("wallets.limit_short", { defaultValue: "Limit" }) : t("wallets.overdraft_limit_label", { defaultValue: "Overdraft Limit" })}</span>
                    <div className="flex items-baseline gap-0.5">
                      <CurrencyAmount value={limitValue} includeCurrency={false} />
                      <span className="text-[7px]">UZS</span>
                    </div>
                  </div>
                )}
                {showProgressBar && (
                  <span className={cn(
                    "px-1.5 py-0.5 rounded-md backdrop-blur-xs transition-colors font-black",
                    isOverlimit
                      ? "text-red-100 bg-red-600/40"
                      : "text-white bg-black/20 ring-1 ring-white/10"
                  )}>
                    {Math.round(utilizationPercent)}%
                  </span>
                )}
              </div>
            )}
          </div>

          {showProgressBar && (
            <Progress
              value={utilizationPercent}
              className="h-1.5"
              trackClassName="bg-white/20"
              indicatorClassName={cn("transition-all duration-500", indicatorColor)}
            />
          )}
        </div>

        <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
        {isOperational && wallet.is_default && <div className="pointer-events-none absolute top-4 right-4 h-2 w-2 rounded-full bg-white animate-pulse" />}
      </CardContent>

    </Card>
  );
}

function LiveEditorCard({ mode, name, balance, style, setName, setBalance, setStyle, onSave, onCancel, isPending, t }) {
  const s = getWalletStyle(style);
  return (
    <Card className={cn("relative h-auto sm:h-[215px] overflow-hidden border-none shadow-2xl ring-1 ring-white/20 transition-all duration-300", s.className)}>
      <CardContent className="flex h-full flex-col p-5">
        <div className="flex flex-1 flex-col gap-3.5">
          {/* Header Area (Inline Editable) */}
          <div className="space-y-0.5">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("wallets.unnamedWallet", { defaultValue: "New Wallet" })}
              maxLength={32}
              className="w-full h-auto p-0 border-none bg-transparent text-xl font-black tracking-tight text-white/90 placeholder:text-white/30 focus:outline-none focus:ring-0 shadow-none selection:bg-white/30"
            />
          </div>

          {/* Controls Area (Optimized for space) */}
          <div className="flex flex-col gap-2.5">
            {mode === "add" && (
              <Input
                value={balance}
                onChange={(e) => setBalance(formatAmountInput(e.target.value))}
                placeholder={t("wallet.initialBalance", { defaultValue: "Initial Balance" })}
                className="h-9 border-none bg-black/20 text-white placeholder:text-white/30 rounded-xl text-xs font-bold focus-visible:ring-1 focus-visible:ring-white/30"
              />
            )}

            <div className="flex items-center justify-between gap-4">
              <div className="grid grid-cols-7 gap-x-1.5 gap-y-1 rounded-xl bg-black/10 p-2 ring-1 ring-white/5">
                {WALLET_STYLE_KEYS.map(k => (
                  <button
                    key={k}
                    onClick={() => setStyle(k)}
                    className={cn(
                      "h-5 w-5 rounded-full border border-white/10 transition-all hover:scale-110",
                      getWalletStyle(k).className,
                      style === k ? "ring-2 ring-white scale-110 shadow-lg" : "opacity-40"
                    )}
                  />
                ))}
              </div>

              {/* Action Cluster */}
              <div className="flex items-center gap-2 shrink-0">
                <Button
                  variant="ghost"
                  onClick={onCancel}
                  className="h-8 w-8 rounded-full bg-black/20 hover:bg-black/40 text-white p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
                <Button
                  onClick={onSave}
                  disabled={isPending}
                  className="h-8 w-8 bg-white text-black hover:bg-white/90 rounded-full font-black p-0 shadow-xl"
                >
                  {isPending ? <LoadingSpinner size="sm" /> : <Check className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Decorative elements */}
        <div className="pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full bg-white/10 blur-2xl" />
      </CardContent>
    </Card>
  );
}
