import React, { useState, useEffect } from "react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Percent, 
  Receipt,
  AlertCircle
} from "lucide-react";
import { getWalletStyle } from "@/lib/walletStyles";
import { formatAmountInput, parseAmountInput } from "@/lib/format";
import { cn } from "@/lib/utils";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

export function QuickActionDialog({ isOpen, onOpenChange, onSave, isPending, wallet, actionType, t }) {
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  // Reset when opening
  useEffect(() => {
    if (isOpen) {
      setAmount("");
      setNote("");
      setError("");
    }
  }, [isOpen]);

  const handleSubmit = () => {
    const parsedAmount = parseAmountInput(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      setError(t("expenses.invalidAmount"));
      return;
    }
    
    onSave({
      action_type: actionType,
      amount: parsedAmount,
      note: note || null
    });
  };

  if (!wallet) return null;
  const s = getWalletStyle(wallet.color || "default");
  const isInterest = actionType === "INTEREST";
  const Icon = isInterest ? Percent : Receipt;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px] p-0 overflow-hidden border-none shadow-2xl rounded-3xl">
        <div className={cn("h-28 p-6 flex flex-col justify-end transition-all duration-500", s.className)}>
          <div className="flex justify-between items-center text-white">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-80">
                {isInterest ? t("wallets.action_interest") : t("wallets.action_fee")}
              </p>
              <h2 className="text-xl font-black truncate max-w-[200px]">{wallet.name}</h2>
            </div>
            <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-md">
              <Icon className="h-5 w-5 text-white" />
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          <DialogHeader>
            <DialogTitle className="text-xl font-black">
              {isInterest ? t("wallets.record_interest_title", { defaultValue: "Record Interest" }) : t("wallets.record_fee_title", { defaultValue: "Record Bank Fee" })}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="amount" className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
                {t("expenses.amount")}
              </Label>
              <div className="relative">
                <Input 
                  id="amount" 
                  value={amount} 
                  maxLength={15}
                  onChange={(e) => {
                    setAmount(formatAmountInput(e.target.value));
                    if (error) setError("");
                  }}
                  autoFocus
                  placeholder="0"
                  className={cn(
                    "h-12 rounded-xl bg-muted/50 border-muted font-mono font-bold text-lg pr-12",
                    error && "border-red-500"
                  )}
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold text-muted-foreground/40">UZS</span>
              </div>
              {error && (
                <p className="flex items-center gap-1 text-[10px] font-medium text-red-500 animate-in fade-in slide-in-from-top-1">
                  <AlertCircle className="h-3 w-3" />
                  {error}
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
                className="h-12 rounded-xl bg-muted/50 border-muted placeholder:text-muted-foreground/40"
              />
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button 
              onClick={handleSubmit} 
              disabled={isPending}
              className="w-full h-12 rounded-2xl font-black uppercase tracking-widest shadow-lg shadow-primary/20 bg-primary"
            >
              {isPending ? <LoadingSpinner size="sm" /> : t("common.save")}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
