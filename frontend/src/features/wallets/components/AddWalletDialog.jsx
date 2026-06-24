import React, { useState, useEffect } from "react";
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
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Landmark,
  Coins,
  CreditCard,
  Wallet as WalletIcon,
  PiggyBank,
  Check,
  ChevronRight,
  Info,
  ShieldCheck,
  Zap,
  AlertCircle
} from "lucide-react";
import { WALLET_STYLES, WALLET_STYLE_KEYS, getWalletStyle } from "@/lib/walletStyles";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { formatAmountInput, parseAmountInput } from "@/lib/format";
import { cn } from "@/lib/utils";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { walletFormSchema } from "../walletSchemas";

export function AddWalletDialog({ isOpen, onOpenChange, onSave, isPending, t }) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: "",
    wallet_type: "DEBIT",
    accounting_type: "ASSET",
    initial_balance: "",
    balance_nature: "OWNED",
    has_overdraft: false,
    overdraft_limit: "",
    credit_limit: "",
    allow_overlimit: false,
    can_fund_goals: false,
    color: "default"
  });

  const [errors, setErrors] = useState({});

  // Reset when opening
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setFormData({
        name: "",
        wallet_type: "DEBIT",
        accounting_type: "ASSET",
        initial_balance: "",
        balance_nature: "OWNED",
        has_overdraft: false,
        overdraft_limit: "",
        credit_limit: "",
        allow_overlimit: false,
        can_fund_goals: false,
        color: "default"
      });
      setErrors({});
    }
  }, [isOpen]);

  const updateField = (field, value) => {
    setFormData(prev => {
      const newData = { ...prev, [field]: value };

      // Auto-set accounting type and balance nature based on wallet type
      if (field === "wallet_type") {
        newData.accounting_type = value === "CREDIT" ? "LIABILITY" : "ASSET";
        newData.balance_nature = value === "CREDIT" ? "OWED" : "OWNED";
        newData.can_fund_goals = value === "SAVINGS";
        // Reset limits when switching
        newData.overdraft_limit = "";
        newData.credit_limit = "";
        newData.has_overdraft = false;
      }

      // If user disables overdraft, we must reset balance nature to OWNED if it was OWED
      if (field === "has_overdraft" && !value && newData.wallet_type !== "CREDIT") {
        newData.balance_nature = "OWNED";
      }

      return newData;
    });
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleNext = () => {
    if (step === 1) {
      if (!formData.name) {
        setErrors({ name: t("wallets.nameRequired") });
        return;
      }
      setStep(2);
    }
  };

  const handleSubmit = () => {
    const magnitude = parseAmountInput(formData.initial_balance) || 0;
    const signedBalance = formData.balance_nature === "OWED" ? -Math.abs(magnitude) : Math.abs(magnitude);

    const payload = {
      ...formData,
      initial_balance: String(signedBalance)
    };

    // Validate using Zod
    const result = walletFormSchema.safeParse(payload);
    if (!result.success) {
      const formattedErrors = {};
      result.error.issues.forEach(issue => {
        formattedErrors[issue.path[0]] = t(issue.message);
      });
      setErrors(formattedErrors);
      return;
    }

    // IMPORTANT: Send the result.data which contains the transformed numbers, 
    // not the raw payload which contains strings with spaces.
    onSave(result.data);
  };

  const s = getWalletStyle(formData.color);

  const types = [
    { id: "CASH", label: t("wallets.type_cash"), icon: Coins, desc: t("wallets.type_cash_desc", { defaultValue: "Physical cash in hand" }) },
    { id: "DEBIT", label: t("wallets.type_debit"), icon: CreditCard, desc: t("wallets.type_debit_desc", { defaultValue: "Everyday bank money" }) },
    { id: "CREDIT", label: t("wallets.type_credit"), icon: Landmark, desc: t("wallets.type_credit_desc", { defaultValue: "Borrowed credit balance" }) },
    { id: "PRELOADED", label: t("wallets.type_prepaid"), icon: WalletIcon, desc: t("wallets.type_prepaid_desc", { defaultValue: "Transportation or gift balance" }) },
    { id: "SAVINGS", label: t("wallets.type_savings", { defaultValue: "Savings" }), icon: PiggyBank, desc: t("wallets.type_savings_desc", { defaultValue: "Real savings account or reserve wallet" }) },
  ];

  const isCredit = formData.wallet_type === "CREDIT";
  const canOwe = isCredit || formData.has_overdraft;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px] p-0 overflow-hidden border-none shadow-2xl rounded-3xl flex flex-col max-h-[90vh]">
        {/* Fixed Header */}
        <div className={cn("h-28 p-6 flex flex-col justify-end transition-all duration-500 shrink-0", s.className)}>
          <div className="flex justify-between items-center text-white">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-80">{formData.name || t("wallets.new_wallet_label", { defaultValue: "New Wallet" })}</p>
              <div className="flex items-center gap-2">
                <CurrencyAmount
                  value={(() => {
                    const mag = Math.abs(parseAmountInput(formData.initial_balance) || 0);
                    const backendVal = formData.balance_nature === "OWED" ? -mag : mag;
                    return isCredit ? -backendVal : backendVal;
                  })()}
                  className="text-2xl font-black tracking-tighter"
                />
              </div>
            </div>
            {types.find(t => t.id === formData.wallet_type)?.icon && (
              <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-md">
                {React.createElement(types.find(t => t.id === formData.wallet_type).icon, { className: "h-5 w-5 text-white" })}
              </div>
            )}
          </div>
        </div>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar">
          <DialogHeader>
            <DialogTitle className="text-xl font-black">
              {step === 1 ? t("wallets.addTitle") : t("wallets.formHint")}
            </DialogTitle>
          </DialogHeader>

          {step === 1 ? (
            <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
              <div className="space-y-2">
                <Label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{t("wallets.type_label", { defaultValue: "Wallet Type" })}</Label>
                <div className="grid grid-cols-2 gap-2">
                  {types.map((type) => (
                    <button
                      key={type.id}
                      onClick={() => updateField("wallet_type", type.id)}
                      className={cn(
                        "flex flex-col items-start p-3 rounded-2xl border-2 text-left transition-all group",
                        formData.wallet_type === type.id
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-muted hover:border-muted-foreground/30 hover:bg-muted/30"
                      )}
                    >
                      <type.icon className={cn("h-4 w-4 mb-2 transition-transform group-hover:scale-110", formData.wallet_type === type.id ? "text-primary" : "text-muted-foreground")} />
                      <span className="text-[10px] font-black uppercase tracking-tight">{type.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name" className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{t("wallets.wallet_name_label", { defaultValue: "Wallet Name" })}</Label>
                <Input
                  id="name" value={formData.name}
                  maxLength={32}
                  onChange={(e) => updateField("name", e.target.value)}
                  className={cn("h-11 rounded-xl bg-muted/50 border-muted placeholder:text-muted-foreground/40 text-sm", errors.name && "border-red-500")}
                />
                {errors.name && <p className="text-[10px] font-medium text-red-500">{errors.name}</p>}
              </div>

              <div className="space-y-3">
                <Label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{t("wallets.initial_balance_label", { defaultValue: "Initial Balance" })}</Label>

                <Tabs value={formData.balance_nature} onValueChange={(v) => updateField("balance_nature", v)}>
                  <TabsList className="grid w-full grid-cols-2 h-9 p-1 bg-muted/50 rounded-xl">
                    <TabsTrigger value="OWNED" className="text-[9px] font-black uppercase">
                      <ShieldCheck className="h-3 w-3 mr-1.5" />
                      {isCredit ? t("wallets.balance_nature_own_credit", { defaultValue: "Overpayment" }) : t("wallets.balance_nature_own_asset", { defaultValue: "Available Balance" })}
                    </TabsTrigger>
                    <TabsTrigger value="OWED" className="text-[9px] font-black uppercase" disabled={!canOwe}>
                      <Zap className="h-3 w-3 mr-1.5" />
                      {isCredit ? t("wallets.balance_nature_owe_debt", { defaultValue: "Amount Owed" }) : t("wallets.balance_nature_owe_overdraft", { defaultValue: "Overdraft Used" })}
                    </TabsTrigger>
                  </TabsList>
                </Tabs>

                <div className="relative">
                  <Input
                    id="balance" value={formData.initial_balance}
                    maxLength={15}
                    onChange={(e) => updateField("initial_balance", formatAmountInput(e.target.value))}
                    placeholder="0"
                    className={cn(
                      "h-11 rounded-xl bg-muted/50 border-muted font-mono font-bold text-lg pr-12",
                      errors.initial_balance && "border-red-500"
                    )}
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold text-muted-foreground/40">UZS</span>
                </div>
                {errors.initial_balance && (
                  <p className="text-[10px] font-medium text-red-500 animate-in fade-in slide-in-from-top-1 px-1">
                    {errors.initial_balance}
                  </p>
                )}
                {!canOwe && (formData.wallet_type === "DEBIT" || formData.wallet_type === "PRELOADED") && (
                  <p className="text-[9px] text-muted-foreground italic px-1 leading-tight">{t("wallets.overdraft_tip", { defaultValue: "Tip: Enable overdraft in the next step to allow negative balances." })}</p>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-5 animate-in fade-in slide-in-from-right-4 duration-300">
              {/* Conditional Morphing Section */}
              {(formData.wallet_type === "DEBIT" || formData.wallet_type === "PRELOADED") && (
                <div className={cn("p-4 rounded-2xl bg-muted/30 space-y-4 border transition-colors", errors.overdraft_limit ? "border-red-500/50" : "border-border/40")}>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-xs font-bold">{t("wallets.overdraft_limit_label")}</Label>
                      <p className="text-[10px] text-muted-foreground leading-tight">{t("wallets.overdraft_hint")}</p>
                    </div>
                    <Switch
                      checked={formData.has_overdraft}
                      onCheckedChange={(v) => updateField("has_overdraft", v)}
                    />
                  </div>
                  {formData.has_overdraft && (
                    <div className="space-y-2 animate-in slide-in-from-top-2">
                      <Label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 px-1">
                        {t("wallets.overdraft_limit_label", { defaultValue: "Overdraft Limit" })}
                      </Label>
                      <div className="relative">
                        <Input
                          value={formData.overdraft_limit}
                          maxLength={15}
                          onChange={(e) => updateField("overdraft_limit", formatAmountInput(e.target.value))}
                          className={cn("h-10 rounded-xl bg-background border-muted text-xs font-bold pr-12", errors.overdraft_limit && "border-red-500")}
                        />
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[9px] font-bold text-muted-foreground/40">UZS</span>
                      </div>
                      {errors.overdraft_limit && (
                        <div className="flex items-center gap-1 text-[9px] font-bold text-red-500 animate-in fade-in">
                          <AlertCircle className="h-2.5 w-2.5" />
                          <span>{errors.overdraft_limit}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {formData.wallet_type === "CREDIT" && (
                <div className={cn("p-4 rounded-2xl bg-muted/30 space-y-4 border transition-colors", errors.credit_limit ? "border-red-500/50" : "border-border/40")}>
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5">
                      <Label className="text-xs font-bold">{t("wallets.credit_limit_label")}</Label>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger><Info className="h-3 w-3 text-muted-foreground" /></TooltipTrigger>
                          <TooltipContent><p className="text-[10px] max-w-[200px]">{t("wallets.credit_limit_hint")}</p></TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </div>
                    <div className="relative">
                      <Input
                        value={formData.credit_limit}
                        maxLength={15}
                        onChange={(e) => updateField("credit_limit", formatAmountInput(e.target.value))}
                        className={cn("h-10 rounded-xl bg-background border-muted text-xs font-bold pr-12", errors.credit_limit && "border-red-500")}
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[9px] font-bold text-muted-foreground/40">UZS</span>
                    </div>
                    {errors.credit_limit && (
                      <div className="flex items-center gap-1 text-[9px] font-bold text-red-500 animate-in fade-in">
                        <AlertCircle className="h-2.5 w-2.5" />
                        <span>{errors.credit_limit}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <Label className="text-[10px] font-bold uppercase text-muted-foreground">{t("wallets.overlimit_label")}</Label>
                    <Switch
                      checked={formData.allow_overlimit}
                      onCheckedChange={(v) => updateField("allow_overlimit", v)}
                    />
                  </div>
                </div>
              )}

                <div className="flex items-center justify-between rounded-2xl border border-border/40 bg-muted/30 p-4">
                  <div className="space-y-0.5">
                    <Label className="text-xs font-bold">{t("wallets.can_fund_goals", { defaultValue: "Can fund goals" })}</Label>
                    <p className="text-[10px] text-muted-foreground leading-tight">
                      {t("wallets.can_fund_goals_hint", { defaultValue: "Allow this wallet's positive balance to be allocated to goals. Credit limits and overdrafts cannot fund goals." })}
                    </p>
                  </div>
                  <Switch
                    checked={formData.can_fund_goals}
                    onCheckedChange={(v) => updateField("can_fund_goals", v)}
                  />
                </div>

              <div className="space-y-4 pb-2">
                <Label className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{t("wallets.chooseStyle")}</Label>
                <div className="max-h-36 overflow-y-auto pr-1 custom-scrollbar">
                  <div className="grid grid-cols-5 gap-2 pt-2 pb-1">
                    {WALLET_STYLE_KEYS.map(key => (
                      <button
                        key={key}
                        onClick={() => updateField("color", key)}
                        className={cn(
                          "h-8 w-full rounded-xl transition-all flex items-center justify-center",
                          getWalletStyle(key).className,
                          formData.color === key ? "scale-110 shadow-lg" : "opacity-60 hover:opacity-100"
                        )}
                      >
                        {formData.color === key && <Check className="h-4 w-4 text-white" />}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Fixed Footer Buttons */}
        <div className="shrink-0 p-6 pt-2 border-t border-border/10 bg-background/50 backdrop-blur-sm">
          {step === 1 ? (
            <Button onClick={handleNext} className="w-full h-12 rounded-2xl font-black uppercase tracking-widest shadow-lg shadow-primary/20 bg-primary">
              {t("common.next", { defaultValue: "Next Step" })}
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <div className="flex w-full gap-3">
              <Button variant="ghost" onClick={() => setStep(1)} className="h-12 rounded-2xl flex-1 font-bold text-muted-foreground">{t("common.back")}</Button>
              <Button onClick={handleSubmit} disabled={isPending} className="h-12 rounded-2xl flex-[2] font-black uppercase tracking-widest shadow-xl shadow-primary/20 bg-primary">
                {isPending ? <LoadingSpinner size="sm" /> : t("common.create")}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
