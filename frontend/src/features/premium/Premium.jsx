import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { localizeApiError } from "@/lib/errorMessages";
import { useSettingsDataQuery } from "@/features/settings/hooks/useSettingsDataQuery";

const TELEGRAM_BOT_USERNAME = (import.meta.env.VITE_TELEGRAM_BOT_USERNAME || "").trim();

const PLANS = {
  BETA_MONTHLY: {
    price: 11990,
    compareAt: 19990,
    isHighlighted: false,
    periodKey: "perMonth",
    features: ["featureRollover", "featureRecurring", "featureSavingsGoals"],
  },
  BETA_YEARLY: {
    price: 79990,
    compareAt: 149990,
    isHighlighted: false,
    periodKey: "perYear",
    features: ["featureEverythingMonthly", "featureYearAccess", "featureUpcoming", "featurePriority"],
  },
  BETA_LIFETIME: {
    price: 109990,
    compareAt: 269990,
    isHighlighted: true,
    periodKey: "oneTime",
    features: ["featureEverythingYearly", "featureLifetime", "featureUpcoming", "featurePriority"],
  },
};

function formatUzs(amount) {
  try {
    return Number(amount || 0).toLocaleString();
  } catch {
    return String(amount || 0);
  }
}

export default function Premium() {
  const { t } = useTranslation();
  const userQuery = useSettingsDataQuery();
  const isPremium = !!userQuery.data?.is_premium;

  const [error, setError] = useState("");
  const [invoiceData, setInvoiceData] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const selectedPlanLabel = useMemo(() => {
    if (!invoiceData?.plan_id) return "";
    if (invoiceData.plan_id === "BETA_MONTHLY") return t("premium.monthlyTitle");
    if (invoiceData.plan_id === "BETA_YEARLY") return t("premium.yearlyTitle");
    return t("premium.lifetimeTitle");
  }, [invoiceData?.plan_id, t]);

  const handleUpgrade = async (planId) => {
    try {
      setIsGenerating(true);
      setError("");
      const { createInvoice } = await import("@/api/payments");
      const data = await createInvoice(planId);
      setInvoiceData(data);
    } catch (e) {
      setError(localizeApiError(e?.message, t) || e?.message || t("premium.invoiceCreateFailed"));
    } finally {
      setIsGenerating(false);
    }
  };

  const hasTelegramBotUsername = TELEGRAM_BOT_USERNAME.length > 0;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-40 left-1/2 h-130 w-130 -translate-x-1/2 rounded-full bg-primary/15 blur-3xl" />
          <div className="absolute -bottom-52 left-1/2 h-130 w-130 -translate-x-1/2 rounded-full bg-emerald-500/10 blur-3xl" />
        </div>

        <div className="container mx-auto px-4 py-10 space-y-10">
          <div className="relative space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-muted/50 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
              <Sparkles className="h-3.5 w-3.5" />
              {t("premium.earlyBetaTitle")}
            </div>
            <h1 className="text-4xl md:text-5xl font-semibold tracking-tight">{t("premium.title")}</h1>
            <p className="max-w-2xl text-muted-foreground">
              {t("premium.earlyBetaDesc")}
            </p>
          </div>

          {isPremium ? (
            <div className="relative rounded-3xl bg-linear-to-br from-emerald-500/15 to-primary/10 p-px shadow-[0_24px_60px_-30px_rgba(16,185,129,0.45)]">
              <div className="rounded-3xl bg-background/70 backdrop-blur px-7 py-8">
                <div className="text-sm font-medium text-primary">{t("premium.activeTitle")}</div>
                <div className="mt-2 text-2xl font-semibold">{t("premium.activeDesc")}</div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {error && <p className="text-sm text-red-600">{error}</p>}

              <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                {(["BETA_MONTHLY", "BETA_YEARLY", "BETA_LIFETIME"]).map((planId) => {
                  const plan = PLANS[planId];
                  const title =
                    planId === "BETA_MONTHLY"
                      ? t("premium.monthlyTitle")
                      : planId === "BETA_YEARLY"
                        ? t("premium.yearlyTitle")
                        : t("premium.lifetimeTitle");
                  const price = formatUzs(plan.price);
                  const compareAt = formatUzs(plan.compareAt);
                  const priceSuffix = t(`premium.${plan.periodKey}`);

                  return (
                    <button
                      key={planId}
                      type="button"
                      onClick={() => handleUpgrade(planId)}
                      disabled={isGenerating}
                      className={[
                        "group relative w-full text-left rounded-3xl p-6 sm:p-7 transition-all",
                        "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                        isGenerating ? "opacity-60 cursor-not-allowed" : "hover:-translate-y-0.5 hover:shadow-xl",
                        plan.isHighlighted ? "bg-linear-to-b from-primary/20 via-primary/10 to-emerald-500/10 shadow-[0_30px_80px_-45px_rgba(99,102,241,0.55)]" : "bg-muted/25 shadow-lg",
                      ].join(" ")}
                    >
                      <div className="space-y-6">
                        <div className="flex items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="text-lg font-semibold tracking-tight">{title}</div>
                            <div className="text-sm text-muted-foreground">{t("premium.activateHint")}</div>
                          </div>

                          {plan.isHighlighted && (
                            <span className="shrink-0 rounded-full bg-primary px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-primary-foreground shadow">
                              {t("premium.bestValue")}
                            </span>
                          )}
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-end gap-2">
                            <div className="text-3xl sm:text-4xl font-semibold tracking-tight">{price}</div>
                            <div className="pb-1 text-sm font-medium text-muted-foreground">{priceSuffix}</div>
                          </div>

                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                            <span className="line-through">{compareAt}</span>
                            <span className="text-muted-foreground">{priceSuffix}</span>
                            <span className="uppercase tracking-wide">{t("premium.afterLaunch")}</span>
                          </div>
                        </div>

                        <div className="space-y-2">
                          {plan.features.map((featureKey) => (
                            <div key={featureKey} className="flex items-center gap-2 text-sm text-muted-foreground">
                              <span className="grid h-5 w-5 place-items-center rounded-full bg-primary/12 text-primary">
                                <Check className="h-3.5 w-3.5" />
                              </span>
                              <span className="text-foreground/80">{t(`premium.${featureKey}`)}</span>
                            </div>
                          ))}
                        </div>

                        <div className="pt-1">
                          <div className="inline-flex w-full">
                            <span
                              className={[
                                "w-full rounded-full px-4 py-2 text-sm font-semibold text-center transition-colors",
                                plan.isHighlighted ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
                              ].join(" ")}
                            >
                              {t("premium.choosePlan")}
                            </span>
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>

              <p className="text-xs text-muted-foreground">
                {t("premium.sendReceiptHint")}
              </p>
            </div>
          )}
        </div>
      </div>

      <Dialog open={!!invoiceData} onOpenChange={(open) => !open && setInvoiceData(null)}>
        <DialogContent className="sm:max-w-md text-center">
          <DialogHeader>
            <DialogTitle className="text-center text-2xl font-bold">{t("premium.completePurchase")}</DialogTitle>
            <DialogDescription className="text-center text-base">
              {t("premium.selectedPlan", { plan: selectedPlanLabel })}
            </DialogDescription>
          </DialogHeader>

          <div className="bg-muted/30 p-5 rounded-xl flex flex-col items-center gap-4 my-1 border">
            <div className="text-sm text-muted-foreground">{t("premium.transferExact")}</div>

            <div className="bg-background border rounded-lg p-4 w-full text-center shadow-sm">
              <div className="text-3xl font-bold mb-1">
                {formatUzs(invoiceData?.amount)}{" "}
                <span className="text-lg text-muted-foreground font-normal">UZS</span>
              </div>
              <div className="text-sm text-muted-foreground mb-4">{t("premium.viaPaymeClick")}</div>

              <div className="text-sm text-muted-foreground uppercase tracking-widest mb-1">Uzcard</div>
              <div className="font-mono text-xl tracking-wider font-semibold text-primary">8600 1234 5678 9012</div>
              <div className="text-sm font-medium mt-1">E. Trackerov</div>
            </div>

            <p className="text-sm font-medium space-y-1">
              <span className="block text-muted-foreground">{t("premium.afterTransfer")}</span>
              <span className="block text-sm">{t("premium.sendReceiptHint")}</span>
            </p>

            <Button
              className="w-full h-12 text-md mt-1 shadow-md hover:scale-[1.02] transition-transform"
              disabled={!hasTelegramBotUsername}
              onClick={() => window.open(`https://t.me/${TELEGRAM_BOT_USERNAME}?start=${invoiceData?.order_code}`, "_blank")}
            >
              {t("premium.sendReceiptButton")}
            </Button>
            {!hasTelegramBotUsername && (
              <p className="text-xs text-red-600">
                {t("premium.telegramBotMissing", { defaultValue: "Telegram bot is not configured." })}
              </p>
            )}
            <div className="text-[11px] text-muted-foreground font-mono mt-1">
              {t("premium.orderId", { order: invoiceData?.order_code })}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
