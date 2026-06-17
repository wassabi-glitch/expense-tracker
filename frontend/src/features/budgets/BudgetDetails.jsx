import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChartColumn, FolderKanban, Layers3, ReceiptText } from "lucide-react";
import { getBudgetDetail } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { EmptyState } from "@/components/EmptyState";
import { localizeApiError } from "@/lib/errorMessages";
import { useTranslation } from "react-i18next";

function DetailStat({ title, value, icon: Icon }) {
  return (
    <Card className="shadow-sm">
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{title}</p>
          <div className="mt-2 text-xl font-bold tracking-tight">{value}</div>
        </div>
        {Icon ? <Icon className="mt-0.5 h-5 w-5 text-muted-foreground" /> : null}
      </CardContent>
    </Card>
  );
}

export default function BudgetDetails() {
  const { budgetYear, budgetMonth, category } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const detailQuery = useQuery({
    queryKey: ["budgets", "detail", budgetYear, budgetMonth, category],
    queryFn: () => getBudgetDetail(Number(budgetYear), Number(budgetMonth), category),
    enabled: !!budgetYear && !!budgetMonth && !!category,
  });

  const detail = detailQuery.data;
  const subcategoryLimitTotal = useMemo(
    () => (detail?.subcategories || []).reduce((sum, item) => sum + Number(item.monthly_limit || 0), 0),
    [detail],
  );
  const subcategorySpentTotal = useMemo(
    () => (detail?.subcategories || []).reduce((sum, item) => sum + Number(item.spent || 0), 0),
    [detail],
  );
  const subcategoryBuffer = Math.max(Number(detail?.monthly_limit || 0) - subcategoryLimitTotal, 0);
  const unspecifiedSpent = Math.max(Number(detail?.spent || 0) - subcategorySpentTotal, 0);
  const effects = useMemo(
    () => [
      { label: "Base limit", value: detail?.monthly_limit ?? 0 },
      { label: "Rollover", value: detail?.rollover_amount ?? 0 },
      { label: "Cap trim", value: detail?.cap_trim_amount ?? 0 },
      { label: "Reallocated in", value: detail?.reallocated_in ?? 0 },
      { label: "Reallocated out", value: detail?.reallocated_out ?? 0 },
    ],
    [detail]
  );

  if (detailQuery.isLoading) {
    return <div className="flex h-[60vh] items-center justify-center"><LoadingSpinner className="h-8 w-8 text-primary" /></div>;
  }

  if (detailQuery.error || !detail) {
    return (
      <div className="w-full px-page py-8">
        <EmptyState
          icon={FolderKanban}
          title="Budget details unavailable"
          description={localizeApiError(detailQuery.error?.message, t) || detailQuery.error?.message || "Could not load this budget."}
        />
      </div>
    );
  }

  return (
    <div className="w-full space-y-6 px-page py-8">
      <PageHeader
        title={`${detail.category} budget`}
        description={`${detail.budget_year}-${String(detail.budget_month).padStart(2, "0")} planning detail`}
      >
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </PageHeader>

      <div className="flex flex-wrap gap-2">
        {detail.is_over_limit ? <Badge variant="destructive">Over limit</Badge> : <Badge>On track</Badge>}
        {(detail.subcategories || []).length ? <Badge variant="secondary">{detail.subcategories.length} subcategories</Badge> : null}
        {(detail.project_spending || []).length ? <Badge variant="secondary">{detail.project_spending.length} linked projects</Badge> : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DetailStat title="Base limit" value={<CurrencyAmount value={detail.monthly_limit} format="display" />} icon={Layers3} />
        <DetailStat title="Effective limit" value={<CurrencyAmount value={detail.effective_monthly_limit} format="display" />} icon={ChartColumn} />
        <DetailStat title="Spent" value={<CurrencyAmount value={detail.spent} format="display" />} icon={ReceiptText} />
        <DetailStat title="Remaining" value={<CurrencyAmount value={detail.remaining} format="display" />} icon={FolderKanban} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="shadow-sm">
          <CardHeader><CardTitle>Effect stack</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {effects.map((effect) => (
              <div key={effect.label} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                <span className="text-sm text-muted-foreground">{effect.label}</span>
                <CurrencyAmount value={effect.value} format="display" />
              </div>
            ))}
            <div className="flex items-center justify-between border-t pt-3 font-medium">
              <span>Effective available</span>
              <CurrencyAmount value={detail.effective_available} format="display" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader><CardTitle>Subcategory partitions</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-border bg-muted/20 p-3">
                <p className="text-sm text-muted-foreground">Parent buffer</p>
                <CurrencyAmount value={subcategoryBuffer} format="display" />
              </div>
              <div className="rounded-2xl border border-border bg-muted/20 p-3">
                <p className="text-sm text-muted-foreground">Unspecified parent spending</p>
                <CurrencyAmount value={unspecifiedSpent} format="display" />
              </div>
            </div>
            {(detail.subcategories || []).length ? detail.subcategories.map((subcategory) => (
              <div
                key={subcategory.id}
                className={`grid gap-2 rounded-2xl border p-3 sm:grid-cols-4 ${
                  subcategory.is_over_limit ? "border-destructive/40 bg-destructive/5" : "border-border bg-muted/20"
                }`}
              >
                <div className="sm:col-span-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{subcategory.name}</p>
                    {subcategory.is_over_limit ? <Badge variant="destructive">Needs repair</Badge> : null}
                  </div>
                  <p className="text-sm text-muted-foreground">{subcategory.is_active ? "Active" : "Inactive"}</p>
                </div>
                <div><p className="text-sm text-muted-foreground">Limit</p><CurrencyAmount value={subcategory.monthly_limit || 0} format="display" /></div>
                <div><p className="text-sm text-muted-foreground">Spent</p><CurrencyAmount value={subcategory.spent} format="display" /></div>
                <div><p className="text-sm text-muted-foreground">Remaining</p><CurrencyAmount value={subcategory.remaining || 0} format="display" /></div>
              </div>
            )) : <p className="text-sm text-muted-foreground">No subcategory partitions configured.</p>}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="shadow-sm">
          <CardHeader><CardTitle>Recent activity</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(detail.recent_activity || []).length ? detail.recent_activity.map((item) => (
              <div key={`${item.event_id}-${item.subcategory_id || "base"}`} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{item.title}</p>
                  <p className="truncate text-sm text-muted-foreground">
                    {item.transaction_type}
                    {item.subcategory_name ? ` • ${item.subcategory_name}` : ""}
                    {item.project_title ? ` • ${item.project_title}` : ""}
                    {item.is_session ? " • Session" : ""}
                  </p>
                </div>
                <CurrencyAmount value={item.amount} format="display" />
              </div>
            )) : <p className="text-sm text-muted-foreground">No linked activity yet.</p>}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader><CardTitle>Project overlay inside this budget</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(detail.project_spending || []).length ? detail.project_spending.map((project) => (
              <div key={project.project_id} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                <div>
                  <p className="font-medium">{project.project_title}</p>
                  <p className="text-sm text-muted-foreground">{project.is_isolated ? "Isolated" : "Overlay"}</p>
                </div>
                <CurrencyAmount value={project.spent} format="display" />
              </div>
            )) : <p className="text-sm text-muted-foreground">No project-linked spending in this budget.</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
