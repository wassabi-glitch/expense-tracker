import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DebtsTab } from "./components/DebtsTab";
import { PaymentPlansTab } from "./components/PaymentPlansTab";

export default function Obligations() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => {
    return searchParams.get("tab") === "payment_plans" || searchParams.get("pay_plan") ? "payment_plans" : "debts";
  });

  useEffect(() => {
    const tab = searchParams.get("tab");
    const payPlan = searchParams.get("pay_plan");
    if (tab === "payment_plans" || payPlan) {
      setActiveTab("payment_plans");
    }
  }, [searchParams]);

  return (
    <div className="space-y-6 py-4">
      <PageHeader
        title={t("debts.title", { defaultValue: "Debts & Payment Plans" })}
        description={t("debts.description", { defaultValue: "Manage debts and scheduled payment plans" })}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
          <TabsTrigger value="debts">{t("debts.tabs.debts", { defaultValue: "Debts" })}</TabsTrigger>
          <TabsTrigger value="payment_plans">{t("debts.tabs.payment_plans", { defaultValue: "Payment Plans" })}</TabsTrigger>
        </TabsList>

        <TabsContent value="debts" className="mt-6">
          <DebtsTab />
        </TabsContent>

        <TabsContent value="payment_plans" className="mt-6 space-y-6">
          <PaymentPlansTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
