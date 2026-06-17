import React from "react";
import { useTranslation } from "react-i18next";
import { Trash2, CreditCard, Landmark, Coins, Wallet as WalletIcon, Clock } from "lucide-react";
import { useDeleteTransactionMutation } from "../hooks/useDebtsMutations";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { formatUzs, formatDisplayDate, formatDisplayDateTime, getAppLang } from "@/lib/format";
import { useDebtDetailsQuery } from "../hooks/useDebtsQueries";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getWalletStyle } from "@/lib/walletStyles";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const getWalletTypeIcon = (type) => {
  switch (type) {
    case "CASH": return Coins;
    case "CREDIT": return Landmark;
    case "DEBIT": return CreditCard;
    case "PRELOADED": return CreditCard;
    default: return WalletIcon;
  }
};

export function DebtHistoryModal({ isOpen, onClose, debtId, debtName }) {
  const { t, i18n } = useTranslation();
  const appLang = getAppLang(i18n);

  const { data: debtDetails, isLoading } = useDebtDetailsQuery(debtId, { 
    enabled: isOpen && !!debtId 
  });
  
  const deleteMutation = useDeleteTransactionMutation();

  const transactions = debtDetails?.transactions || [];

  // Sort transactions newest first by ID (most reliable chronological order)
  const displayHistory = [...transactions].sort((a, b) => b.id - a.id);

  return (
    <Dialog open={isOpen} onOpenChange={(val) => !val && onClose()}>
      <DialogContent className="sm:max-w-2xl bg-background p-0 overflow-hidden border-border/40">
        <DialogHeader className="p-6 pb-4 border-b border-border/10 bg-muted/5">
          <DialogTitle className="text-center text-lg font-bold">
            {t("debts.history.title")}
          </DialogTitle>
          <DialogDescription className="text-center text-[10px] font-bold text-muted-foreground/40 uppercase tracking-widest">
            {debtName}
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-y-auto no-scrollbar divide-y divide-border/40">
          {isLoading && (
            <div className="flex flex-col items-center py-12 space-y-4">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-primary" />
              <p className="text-xs font-semibold text-muted-foreground animate-pulse">{t("common.loading")}</p>
            </div>
          )}
          
          {!isLoading && displayHistory.length === 0 && (
            <div className="py-20 flex flex-col items-center justify-center space-y-3 opacity-30">
              <Clock className="w-10 h-10 text-muted-foreground" />
              <p className="text-xs font-bold text-center max-w-[200px] uppercase tracking-tighter">
                {t("debts.history.empty", { defaultValue: "No payments recorded yet." })}
              </p>
            </div>
          )}

          {!isLoading && displayHistory.map((txn) => {
            const Icon = getWalletTypeIcon(txn.wallet?.wallet_type);
            const s = getWalletStyle(txn.wallet?.color);
            
            return (
              <div 
                key={txn.id} 
                className="flex items-center justify-between py-5 px-6 transition-colors hover:bg-muted/5 group"
              >
                {/* Left Side: Human Date & Method */}
                <div className="flex flex-col items-start space-y-2 min-w-0">
                  <p className="text-sm font-bold text-foreground/90 tracking-tight leading-none">
                    {formatDisplayDateTime(txn.created_at, appLang)}
                  </p>
                  <div className="flex items-center gap-2">
                    <div className={cn("flex h-4 w-4 items-center justify-center rounded-[3px] shadow-sm", s.className)}>
                      <Icon className="h-2.5 w-2.5 text-white" />
                    </div>
                    <span className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-tighter truncate max-w-[120px]">
                      {txn.wallet?.name || t("common.unknown")}
                    </span>
                  </div>
                </div>

                {/* Right Side: Amount & Action - Vertically Centered */}
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-sm font-black tabular-nums text-foreground leading-none">
                      {formatUzs(txn.amount)}
                      <span className="text-[10px] ml-1.5 opacity-40 font-bold uppercase tracking-widest">UZS</span>
                    </p>
                  </div>

                  <div className="flex items-center justify-center">
                    {(() => {
                      const isWalletArchived = txn.wallet?.is_active === false;
                      const disabledReason = isWalletArchived 
                        ? t("debts.transaction.wallet_archived", { defaultValue: "Cannot delete: Linked wallet is archived." })
                        : undefined;
                      
                      const btn = (
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={deleteMutation.isPending || isWalletArchived}
                          className={cn(
                            "h-8 w-8 rounded-full transition-all duration-300",
                            isWalletArchived ? "opacity-40 cursor-not-allowed" : "text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10"
                          )}
                          onClick={() => deleteMutation.mutate(txn.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      );

                      if (isWalletArchived && disabledReason) {
                        return (
                          <TooltipProvider>
                            <Tooltip delayDuration={0}>
                              <TooltipTrigger asChild>
                                <span className="block cursor-not-allowed">
                                  <span className="block pointer-events-none">{btn}</span>
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="left" align="center" className="max-w-[200px] text-center z-[200]">
                                <p className="text-xs">{disabledReason}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        );
                      }

                      return btn;
                    })()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
