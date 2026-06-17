import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { DebtsTab } from "./components/DebtsTab";
import { InstallmentsTab } from "./components/InstallmentsTab";

export default function Obligations() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => {
    return searchParams.get("tab") === "installments" || searchParams.get("pay_plan") ? "installments" : "debts";
  });

  useEffect(() => {
    const tab = searchParams.get("tab");
    const payPlan = searchParams.get("pay_plan");
    if (tab === "installments" || payPlan) {
      setActiveTab("installments");
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
          <TabsTrigger value="installments">{t("debts.tabs.installments", { defaultValue: "Payment Plans" })}</TabsTrigger>
        </TabsList>

        <TabsContent value="debts" className="mt-6">
          <DebtsTab />
        </TabsContent>

        <TabsContent value="installments" className="mt-6 space-y-6">
          <InstallmentsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
