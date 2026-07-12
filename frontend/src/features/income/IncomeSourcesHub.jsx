import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  CircleDollarSign,
  Clock,
  Percent,
  TrendingUp,
  Wallet,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { getIncomeSources } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useIncomeSourceAnalyticsQuery } from "./hooks/useIncomeQueries";


function StatCard({ icon: Icon, label, value, sub, className }) {
  return (
    <Card className={cn("flex flex-col gap-1", className)}>
      <CardContent className="flex items-center gap-3 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold truncate">{value}</p>
          {sub != null ? <p className="text-xs text-muted-foreground">{sub}</p> : null}
        </div>
      </CardContent>
    </Card>
  );
}


function SourceDetail({ sourceId, sources, onBack }) {
  const { data: analytics, isLoading, isError } = useIncomeSourceAnalyticsQuery(sourceId);

  if (isLoading) return <LoadingSpinner />;
  if (isError || !analytics) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={onBack}><ArrowLeft className="mr-2 h-4 w-4" />Back</Button>
        <p className="text-sm text-destructive">Could not load source analytics.</p>
      </div>
    );
  }

  const source = sources.find((s) => s.id === sourceId);
  const sourceName = source?.name || analytics.name;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={onBack}><ArrowLeft className="h-5 w-5" /></Button>
        <div>
          <h2 className="text-xl font-semibold">{sourceName}</h2>
          <p className="text-sm text-muted-foreground">
            {analytics.is_active ? "Active income source" : "Inactive income source"}
          </p>
        </div>
        {!analytics.is_active ? (
          <Badge variant="secondary">Inactive</Badge>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Wallet}
          label="Lifetime expected"
          value={<CurrencyAmount amount={analytics.lifetime_expected} />}
          sub={`${analytics.promise_count} promise${analytics.promise_count !== 1 ? "s" : ""}`}
        />
        <StatCard
          icon={TrendingUp}
          label="Lifetime received"
          value={<CurrencyAmount amount={analytics.lifetime_received} />}
          sub={`${analytics.entry_count} income entr${analytics.entry_count !== 1 ? "ies" : "y"}`}
        />
        <StatCard
          icon={Clock}
          label="Outstanding"
          value={<CurrencyAmount amount={analytics.outstanding_expected} />}
        />
        <StatCard
          icon={Percent}
          label="Reliability"
          value={analytics.reliability_pct != null ? `${analytics.reliability_pct}%` : "—"}
          sub={analytics.reliability_pct != null
            ? (analytics.reliability_pct >= 90 ? "Highly reliable"
              : analytics.reliability_pct >= 50 ? "Moderate"
              : "Low reliability")
            : "No active promises"}
        />
      </div>

      {analytics.promise_ids.length > 0 ? (
        <Card>
          <CardHeader><CardTitle className="text-base">Linked expected inflows</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {analytics.promise_count} promise{analytics.promise_count !== 1 ? "s" : ""} linked —
              view details on the Expected Inflows page for full history.
            </p>
          </CardContent>
        </Card>
      ) : (
        <p className="text-sm text-muted-foreground">No expected inflows linked to this source yet.</p>
      )}
    </div>
  );
}


export function IncomeSourcesHub() {
  const [selectedSourceId, setSelectedSourceId] = useState(null);

  const sourcesQuery = useQuery({
    queryKey: ["income", "sources", true],
    queryFn: () => getIncomeSources({ include_inactive: true }),
  });

  if (sourcesQuery.isLoading) return <LoadingSpinner />;

  const sources = sourcesQuery.data || [];

  if (selectedSourceId) {
    return (
      <SourceDetail
        sourceId={selectedSourceId}
        sources={sources}
        onBack={() => setSelectedSourceId(null)}
      />
    );
  }

  if (sources.length === 0) {
    return (
      <EmptyState
        icon={CircleDollarSign}
        title="No income sources"
        description="Income sources will appear here when you create them. Add a source from the Money In page or when creating an expected inflow."
      />
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Income Sources</h2>
      <p className="text-sm text-muted-foreground">
        Select a source to see lifetime expected, received, outstanding, and reliability.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((source) => (
          <Card
            key={source.id}
            className="cursor-pointer transition-colors hover:bg-muted/50"
            onClick={() => setSelectedSourceId(source.id)}
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">{source.name}</CardTitle>
              {!source.is_active ? (
                <Badge variant="secondary">Inactive</Badge>
              ) : null}
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                Click to view analytics
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
