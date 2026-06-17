import React, { useState, useEffect, useMemo } from "react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Scale, 
  TrendingUp, 
  TrendingDown,
  Equal,
  ShieldCheck,
  Zap,
  AlertCircle
} from "lucide-react";
import { getWalletStyle } from "@/lib/walletStyles";
import { formatAmountInput, parseAmountInput } from "@/lib/format";
import { cn } from "@/lib/utils";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { CurrencyAmount } from "@/components/CurrencyAmount";

export function ReconcileDialog({ isOpen, onOpenChange, onSave, isPending, wallet, t }) {
  const [targetBalance, setTargetBalance] = useState("");
  const [balanceNature, setBalanceNature] = useState("OWNED"); // 'OWNED' (+) vs 'OWED' (-)
  const [note, setNote] = useState("");

  const isCredit = wallet?.wallet_type?.toUpperCase() === "CREDIT";

  const canOwe = isCredit || !!wallet?.has_overdraft;
  
  // Reset when opening
  useEffect(() => {
    if (isOpen && wallet) {
      setTargetBalance(formatAmountInput(Math.abs(wallet.current_balance)));
      // Only allow OWED if wallet supports it
      setBalanceNature((wallet.current_balance < 0 && canOwe) ? "OWED" : "OWNED");
      setNote("");
    }
  }, [isOpen, wallet, canOwe]);

  const stats = useMemo(() => {
    if (!wallet) return null;
    const current = wallet.current_balance;
    const inputMagnitude = parseAmountInput(targetBalance) || 0;
    const target = balanceNature === "OWED" ? -Math.abs(inputMagnitude) : Math.abs(inputMagnitude);
    const diff = target - current;
    
    // Limit Validation Logic (Sartlog Rule Set)
    let isViolated = false;
    let limitValue = 0;
    if (target < 0) {
      const mag = Math.abs(target);
      if (isCredit) {
        limitValue = wallet.credit_limit || 0;
        if (!wallet.allow_overlimit && mag > limitValue) isViolated = true;
      } else {
        const isPreloaded = wallet.wallet_type?.toUpperCase() === "PRELOADED";
        limitValue = wallet.overdraft_limit || 0;
        
        if (!wallet.has_overdraft) {
          isViolated = true; // Still strictly forbidden to have debt if switch is OFF
        } else {
          // If Debit: Limit must be checked. If Preloaded: Only check if limit > 0.
          if (isPreloaded) {
            if (limitValue > 0 && mag > limitValue) isViolated = true;
          } else {
            // Debit (or other has_overdraft types)
            if (mag > limitValue) isViolated = true;
          }
        }
      }
    }

    return { current, target, diff, inputMagnitude, isViolated, limitValue };
  }, [wallet, targetBalance, balanceNature, isCredit]);

  const handleSubmit = () => {
    if (!stats) return;
    
    onSave({
      target_balance: stats.target,
      note: note || null
    });
  };

  if (!wallet) return null;
  const s = getWalletStyle(wallet.color || "default");

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[440px] p-0 overflow-hidden border-none shadow-2xl rounded-3xl transition-all duration-300">
        <DialogHeader className="sr-only">
          <DialogTitle>{t("wallets.adjust_balance", { defaultValue: "Balance Sync" })}</DialogTitle>
          <DialogDescription>{t("wallets.reconcile_description", { defaultValue: "Sync your wallet balance with the real-world balance." })}</DialogDescription>
        </DialogHeader>

        <div className={cn("h-28 p-6 flex flex-col justify-end transition-all duration-500", s.className)}>
          <div className="flex justify-between items-center text-white">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-80">
                {t("wallets.adjust_balance", { defaultValue: "Balance Sync" })}
              </p>
              <h2 className="text-xl font-black truncate max-w-[200px]">{wallet.name}</h2>
            </div>
            <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-md">
              <Scale className="h-5 w-5 text-white" />
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-black">
              {t("wallets.reconcile_title", { defaultValue: "Reconcile Balance" })}
            </DialogTitle>
          </DialogHeader>

          {/* Balance Comparison Info */}
          <div className="grid grid-cols-2 gap-3 p-4 rounded-2xl bg-muted/30 border border-border/40">
            <div className="space-y-1">
              <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/60">{t("wallets.calculated_label", { defaultValue: "Calculated" })}</p>
              <CurrencyAmount 
                value={isCredit ? -wallet.current_balance : wallet.current_balance} 
                className="text-sm font-black" 
              />
            </div>
            <div className="space-y-1 border-l border-border/40 pl-3">
              <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/60">{t("wallets.adjustment_label", { defaultValue: "Adjustment" })}</p>
              <div className="flex items-center gap-1.5">
                {stats?.diff > 0 ? (
                   <TrendingUp className="h-3 w-3 text-emerald-500" />
                ) : stats?.diff < 0 ? (
                   <TrendingDown className="h-3 w-3 text-rose-500" />
                ) : (
                   <Equal className="h-3 w-3 text-muted-foreground/40" />
                )}
                <CurrencyAmount 
                  value={Math.abs(stats?.diff || 0)} 
                  className={cn(
                    "text-sm font-black tabular-nums",
                    stats?.diff > 0 ? "text-emerald-500" : stats?.diff < 0 ? "text-rose-500" : "text-muted-foreground"
                  )} 
                />
              </div>
            </div>
          </div>

          <div className="space-y-5">
            {canOwe && (
              <div className="space-y-3">
                <Label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                  {t("wallets.balance_nature", { defaultValue: "Balance Nature" })}
                </Label>
                <Tabs value={balanceNature} onValueChange={setBalanceNature}>
                  <TabsList className="grid w-full grid-cols-2 h-10 p-1 bg-muted/50 rounded-xl">
                    <TabsTrigger value="OWNED" className="text-[9px] font-black uppercase px-2">
                      <ShieldCheck className="h-3 w-3 mr-1" />
                      {isCredit ? t("wallets.balance_nature_own_credit", { defaultValue: "I Own (Overfill)" }) : t("wallets.balance_nature_own_asset", { defaultValue: "I Own (Asset)" })}
                    </TabsTrigger>
                    <TabsTrigger value="OWED" className="text-[9px] font-black uppercase px-2">
                      <Zap className="h-3 w-3 mr-1" />
                      {isCredit ? t("wallets.balance_nature_owe_debt", { defaultValue: "I Owe (Debt)" }) : t("wallets.balance_nature_owe_overdraft", { defaultValue: "I Owe (Overdraft)" })}
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="target" className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                {t("wallets.actual_balance_label", { defaultValue: "Current Physical Balance" })}
              </Label>
              <div className="relative">
                <Input 
                  id="target" 
                  value={targetBalance} 
                  maxLength={15}
                  onChange={(e) => setTargetBalance(formatAmountInput(e.target.value))}
                  autoFocus
                  placeholder="0"
                  className={cn(
                    "h-12 rounded-xl bg-muted/50 border-muted font-mono font-bold text-lg pr-12 transition-colors",
                    stats?.isViolated && "border-red-500/50 bg-red-50/5 dark:bg-red-500/5 text-red-500"
                  )}
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold text-muted-foreground/40">UZS</span>
              </div>
              
              {stats?.isViolated ? (
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-amber-500 bg-amber-500/10 px-2 py-1 rounded-lg animate-in fade-in slide-in-from-top-1">
                   <AlertCircle className="h-3 w-3" />
                   <span>{t("wallets.reconcile_limit_warning", { defaultValue: "Warning: new balance exceeds the allowed limit." })}</span>
                </div>
              ) : (
                <p className="text-[9px] font-medium text-muted-foreground/60 italic leading-tight">
                  {balanceNature === 'OWED' 
                    ? (isCredit
                      ? t("wallets.reconcile_owed_credit_help", { defaultValue: "Enter your total debt amount as a positive number." })
                      : t("wallets.reconcile_owed_overdraft_help", { defaultValue: "Enter the total amount of the overdraft balance." }))
                    : t("wallets.reconcile_owned_help", { defaultValue: "Enter the total amount you currently have available." })}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="note" className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                {t("expenses.note")} ({t("common.optional")})
              </Label>
              <Input 
                id="note" 
                value={note} 
                onChange={(e) => setNote(e.target.value)}
                className="h-11 rounded-xl bg-muted/50 border-muted placeholder:text-muted-foreground/40 text-sm"
              />
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button 
              onClick={handleSubmit} 
              disabled={isPending || stats?.diff === 0}
              className="w-full h-12 rounded-2xl font-black uppercase tracking-widest shadow-lg shadow-primary/20 bg-primary"
            >
              {isPending ? <LoadingSpinner size="sm" /> : t("common.confirm", { defaultValue: "Confirm" })}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
