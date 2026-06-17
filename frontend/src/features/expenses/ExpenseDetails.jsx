import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Boxes, CalendarDays, Receipt, Wallet } from "lucide-react";
import { getExpenseDetail } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { formatDisplayDate } from "@/lib/format";
import { useTranslation } from "react-i18next";
import { localizeApiError } from "@/lib/errorMessages";
import { EmptyState } from "@/components/EmptyState";

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

export default function ExpenseDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { i18n, t } = useTranslation();
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();

  const detailQuery = useQuery({
    queryKey: ["expenses", "detail", id],
    queryFn: () => getExpenseDetail(id),
    enabled: !!id,
  });

  const detail = detailQuery.data;
  const totalWalletAllocated = useMemo(
    () => (detail?.wallet_allocations || []).reduce((sum, item) => sum + Number(item.amount || 0), 0),
    [detail?.wallet_allocations]
  );

  if (detailQuery.isLoading) {
    return <div className="flex h-[60vh] items-center justify-center"><LoadingSpinner className="h-8 w-8 text-primary" /></div>;
  }

  if (detailQuery.error || !detail) {
    return (
      <div className="w-full px-page py-8">
        <EmptyState
          icon={Receipt}
          title="Expense details unavailable"
          description={localizeApiError(detailQuery.error?.message, t) || detailQuery.error?.message || "Could not load this expense."}
        />
      </div>
    );
  }

  return (
    <div className="w-full space-y-6 px-page py-8">
      <PageHeader
        title={detail.title}
        description={detail.is_session ? "Session event details" : "Expense event details"}
      >
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </PageHeader>

      <div className="flex flex-wrap gap-2">
        <Badge variant="outline">{detail.transaction_type}</Badge>
        {detail.is_session ? <Badge>Session</Badge> : null}
        {detail.is_split ? <Badge variant="secondary">Multi-item</Badge> : null}
        {detail.merge_group_title ? <Badge variant="secondary">{detail.merge_group_title}</Badge> : null}
        {detail.project_title ? <Badge variant="secondary">{detail.project_title}</Badge> : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DetailStat title="Amount" value={<CurrencyAmount value={detail.amount} format="display" />} icon={Receipt} />
        <DetailStat title="Wallet legs" value={detail.wallet_count} icon={Wallet} />
        <DetailStat title="Item legs" value={detail.item_count} icon={Boxes} />
        <DetailStat title="Date" value={formatDisplayDate(detail.date, appLang)} icon={CalendarDays} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="shadow-sm">
          <CardHeader><CardTitle>Money movement</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(detail.wallet_allocations || []).length ? detail.wallet_allocations.map((allocation) => (
              <div key={`${allocation.wallet_id}-${allocation.amount}`} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                <div>
                  <p className="font-medium">{allocation.wallet?.name || `Wallet #${allocation.wallet_id}`}</p>
                  <p className="text-sm text-muted-foreground">Wallet leg</p>
                </div>
                <CurrencyAmount value={allocation.amount} format="display" />
              </div>
            )) : <p className="text-sm text-muted-foreground">No wallet allocations recorded.</p>}
            <div className="flex items-center justify-between border-t pt-3 text-sm text-muted-foreground">
              <span>Total allocated</span>
              <CurrencyAmount value={totalWalletAllocated} format="display" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader><CardTitle>Planning links</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Category</span>
              <span className="font-medium">{detail.category}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Subcategory</span>
              <span className="font-medium">{detail.subcategory_name || "None"}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Project</span>
              <span className="font-medium">{detail.project_title || "None"}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Budget month</span>
              <span className="font-medium">
                {detail.budget_year && detail.budget_month ? `${detail.budget_year}-${String(detail.budget_month).padStart(2, "0")}` : "None"}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Budget remaining</span>
              <span className="font-medium">
                {detail.budget_remaining != null ? <CurrencyAmount value={detail.budget_remaining} format="display" /> : "None"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="shadow-sm">
          <CardHeader><CardTitle>Items and allocations</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(detail.split_items || []).length ? detail.split_items.map((item) => (
              <div key={item.id} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                <div className="min-w-0">
                  <p className="font-medium">{item.label || detail.title}</p>
                  <p className="truncate text-sm text-muted-foreground">
                    {item.category}
                    {item.subcategory_id ? ` • subcategory #${item.subcategory_id}` : ""}
                    {item.project_id ? ` • project #${item.project_id}` : ""}
                  </p>
                </div>
                <CurrencyAmount value={item.amount} format="display" />
              </div>
            )) : (
              <p className="text-sm text-muted-foreground">This event has a single primary allocation.</p>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader><CardTitle>Relationships</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {detail.linked_asset ? (
              <div className="rounded-2xl border border-border bg-muted/20 p-3">
                <p className="font-medium">Linked asset</p>
                <p className="text-sm text-muted-foreground">{detail.linked_asset.title}</p>
              </div>
            ) : null}
            {detail.refund_parent ? (
              <div className="rounded-2xl border border-border bg-muted/20 p-3">
                <p className="font-medium">Refund parent</p>
                <p className="text-sm text-muted-foreground">{detail.refund_parent.title}</p>
              </div>
            ) : null}
            {detail.related_debts?.length ? (
              <div className="space-y-2">
                <p className="font-medium">Related debts</p>
                {detail.related_debts.map((debt) => (
                  <div key={debt.id} className="rounded-2xl border border-border bg-muted/20 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium">{debt.counterparty_name}</p>
                        <p className="text-sm text-muted-foreground">{debt.debt_type} • {debt.status}</p>
                      </div>
                      <CurrencyAmount value={debt.remaining_amount} format="display" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No linked debts, assets, or refund parent on this event.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {detail.refunds?.length ? (
        <Card className="shadow-sm">
          <CardHeader><CardTitle>Refunds</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {detail.refunds.map((refund) => (
              <div key={refund.id} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                <div>
                  <p className="font-medium">{refund.title}</p>
                  <p className="text-sm text-muted-foreground">{formatDisplayDate(refund.date, appLang)}</p>
                </div>
                <CurrencyAmount value={refund.amount} format="display" />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
