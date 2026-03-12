import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Progress } from "@/components/ui/progress";
import { Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Download, Plus, Wallet, TrendingUp, Layers, Circle, CalendarClock } from "lucide-react";
import { cn } from "@/lib/utils";
import { categoryIconMap } from "@/lib/category";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import { formatPrettyDate, formatUzs, formatUzsCard, formatCompactUzs, shortMMDD, formatAmountDisplay } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { useDashboardDataQuery } from "./hooks/useDashboardDataQuery";

const tooltipStyle = {
  borderRadius: 10,
  border: "1px solid hsl(var(--border))",
  background: "hsl(var(--background))",
  color: "hsl(var(--foreground))",
  boxShadow: "0 10px 30px rgba(0,0,0,0.12)",
};
const EMPTY_ARRAY = [];

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const [activeCategoryBar, setActiveCategoryBar] = useState(null);
  const [activeTrendPoint, setActiveTrendPoint] = useState(null);
  const [activeBudgetStatusCategory, setActiveBudgetStatusCategory] = useState(null);
  const todayIso = toISODateInTimeZone();
  const [year, month] = todayIso.split("-");
  const monthStartIso = `${year}-${month}-01`;

  const formatRelativeDue = (daysUntilDue, dueIso) => {
    const hasBackendDays = Number.isFinite(Number(daysUntilDue));
    let diffDays = hasBackendDays ? Number(daysUntilDue) : 0;
    if (!hasBackendDays && dueIso) {
      const todayIso = toISODateInTimeZone();
      const [ty, tm, td] = String(todayIso).split("-").map(Number);
      const [dy, dm, dd] = String(dueIso).split("-").map(Number);
      const todayUtc = new Date(Date.UTC(ty, (tm || 1) - 1, td || 1));
      const dueUtc = new Date(Date.UTC(dy, (dm || 1) - 1, dd || 1));
      diffDays = Math.round((dueUtc - todayUtc) / 86400000);
    }
    const absDays = Math.abs(diffDays);
    let relativeText;

    if (diffDays === 0) {
      relativeText = t("dashboard.relative.today");
    } else if (diffDays === 1) {
      relativeText = t("dashboard.relative.tomorrow");
    } else if (diffDays === -1) {
      relativeText = t("dashboard.relative.yesterday");
    } else if (absDays >= 14) {
      const weeks = Math.round(absDays / 7);
      relativeText =
        diffDays > 0
          ? t("dashboard.relative.inWeeks", { count: weeks })
          : t("dashboard.relative.weeksAgo", { count: weeks });
    } else {
      relativeText =
        diffDays > 0
          ? t("dashboard.relative.inDays", { count: absDays })
          : t("dashboard.relative.daysAgo", { count: absDays });
    }

    return t("dashboard.recurringDueRelative", { when: relativeText });
  };

  const {
    userQuery,
    summaryQuery,
    statsQuery,
    recentExpensesQuery,
    recurringExpensesQuery,
    trendQuery,
  } = useDashboardDataQuery({ monthStartIso, todayIso });

  const user = userQuery.data || null;
  const stats = statsQuery.data || null;
  const recentExpenses = recentExpensesQuery.data?.items || [];
  const recurringExpenses = useMemo(() => {
    const items = recurringExpensesQuery.data || EMPTY_ARRAY;
    return [...items]
      .sort((a, b) => new Date(a.next_due_date) - new Date(b.next_due_date))
      .slice(0, 5);
  }, [recurringExpensesQuery.data]);
  const trendData = trendQuery.data || EMPTY_ARRAY;
  const summary = summaryQuery.data || {
    income: 0,
    spent: 0,
    remaining: 0,
    daily_average: 0,
    overall_balance: 0,
  };
  const showZeroIncomeHint = !summaryQuery.isLoading && summary.income === 0;
  const loading =
    userQuery.isLoading ||
    summaryQuery.isLoading ||
    statsQuery.isLoading ||
    recentExpensesQuery.isLoading ||
    recurringExpensesQuery.isLoading;
  const trendLoading = trendQuery.isLoading;
  const firstError =
    userQuery.error ||
    summaryQuery.error ||
    statsQuery.error ||
    recentExpensesQuery.error ||
    recurringExpensesQuery.error ||
    trendQuery.error;
  const error = firstError ? localizeApiError(firstError?.message, t) || t("dashboard.loadError") : "";

  const derived = useMemo(() => {
    const categoryBreakdown = stats?.category_breakdown || [];
    const totalSpent = Number(stats?.total_expenses || 0);

    const remainingBudget = categoryBreakdown.reduce(
      (sum, item) => sum + Number(item.remaining || 0),
      0
    );

    const biggest = categoryBreakdown.reduce(
      (max, item) =>
        Number(item.total || 0) > Number(max?.total || 0) ? item : max,
      categoryBreakdown[0] || null
    );

    const dayOfMonth = Number(toISODateInTimeZone().split("-")[2] || 1);
    const avgDaily = dayOfMonth > 0 ? Math.round(totalSpent / dayOfMonth) : 0;

    return {
      totalSpent,
      remainingBudget,
      biggestCategory: biggest?.category || "-",
      avgDaily,
      categoryBreakdown,
    };
  }, [stats]);

  const statCards = [
    {
      label: t("dashboard.totalBalance", { defaultValue: "Total Balance" }),
      value: `${summary.overall_balance >= 0 ? "+" : "-"}${formatUzsCard(Math.abs(summary.overall_balance))} UZS`,
      valueClassName: summary.overall_balance >= 0 ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300",
      cardClassName: summary.overall_balance >= 0
        ? "border-emerald-400/70 bg-emerald-50/75 shadow-[0_0_16px_rgba(5,150,105,0.14)] dark:border-emerald-400/45 dark:bg-emerald-950/30 dark:shadow-[0_0_16px_rgba(52,211,153,0.12)]"
        : "border-red-400/70 bg-red-50/75 shadow-[0_0_16px_rgba(220,38,38,0.14)] dark:border-red-400/45 dark:bg-red-950/25 dark:shadow-[0_0_16px_rgba(248,113,113,0.12)]",
      titleClassName: summary.overall_balance >= 0 ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300",
      iconClassName: summary.overall_balance >= 0 ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300",
      icon: Wallet,
    },
    {
      label: t("dashboard.incomeThisMonth", { defaultValue: "Income This Month" }),
      value: `${formatUzsCard(summary.income)} UZS`,
      icon: Wallet,
    },
    {
      label: t("dashboard.spentThisMonth", { defaultValue: "Spent This Month" }),
      value: `${formatUzsCard(summary.spent)} UZS`,
      icon: TrendingUp,
    },
    {
      label: t("dashboard.remainingThisMonth", { defaultValue: "Remaining This Month" }),
      value: `${summary.remaining >= 0 ? "+" : "-"}${formatUzsCard(Math.abs(summary.remaining))} UZS`,
      valueClassName: summary.remaining >= 0 ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300",
      icon: summary.remaining >= 0 ? Layers : Wallet,
    },
  ];

  const chartData = useMemo(() => {
    const endDate = toISODateInTimeZone();
    const [year, month] = endDate.split("-");
    const startDate = `${year}-${month}-01`;

    const byDate = new Map(
      (trendData || []).map((d) => [d.date, Number(d.amount || 0)])
    );

    const result = [];
    let cursor = new Date(`${startDate}T00:00:00Z`);
    const end = new Date(`${endDate}T00:00:00Z`);

    while (cursor <= end) {
      const iso = cursor.toISOString().slice(0, 10);
      result.push({
        date: iso,
        day: shortMMDD(iso),
        amount: byDate.get(iso) ?? 0,
      });
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }

    return result;
  }, [trendData]);

  const monthCategoryChartData = useMemo(() => {
    return [...(derived.categoryBreakdown || [])]
      .map((item) => ({
        category: item.category,
        total: Number(item.total || 0),
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 6);
  }, [derived.categoryBreakdown]);
  const topBudgetBreakdown = useMemo(() => {
    return [...(derived.categoryBreakdown || [])]
      .sort(
        (a, b) =>
          Number(b.percentage_used || 0) - Number(a.percentage_used || 0) ||
          Number(b.total || 0) - Number(a.total || 0)
      )
      .slice(0, 5);
  }, [derived.categoryBreakdown]);
  const hiddenBudgetCount = Math.max(0, (derived.categoryBreakdown || []).length - topBudgetBreakdown.length);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-8">
        <PageHeader title={t("dashboard.title")} description={t("dashboard.subtitle")}>
          <Button asChild variant="outline" className="bg-background hover:bg-muted">
            <Link to="/export">
              <Download className="mr-2 h-4 w-4" /> {t("dashboard.export")}
            </Link>
          </Button>
          <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm">
            <Link to="/expenses">
              <Plus className="mr-2 h-4 w-4" /> {t("dashboard.addExpense")}
            </Link>
          </Button>
        </PageHeader>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((s, i) => {
            const Icon = s.icon;
            return (
              <Card key={i} className={cn("shadow-sm", s.cardClassName)}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
                  <CardTitle className={cn("text-sm font-medium text-muted-foreground", s.titleClassName)}>
                    {s.label}
                  </CardTitle>
                  <Icon className={cn("h-4 w-4 text-muted-foreground", s.iconClassName)} />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className={cn("text-2xl font-bold", s.valueClassName)}>{s.value}</div>
                </CardContent>
              </Card>
            );
          })}
        </div>
        {showZeroIncomeHint && (
          <p className="text-sm text-muted-foreground">{t("dashboard.zeroIncomeHint")}</p>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="shadow-sm lg:col-span-2">
            <CardHeader className="pb-4">
              <CardTitle>{t("dashboard.budgetStatus")}</CardTitle>
              <CardDescription>{t("dashboard.monthlyAllocation")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5 pt-0">
              {loading && (
                <div className="flex min-h-[120px] items-center justify-center">
                  <LoadingSpinner className="h-8 w-8" />
                </div>
              )}
              {!loading && derived.categoryBreakdown.length === 0 && (
                <EmptyState inline description={t("dashboard.noBudgetsYet")} />
              )}
              {topBudgetBreakdown.map((item) => {
                const percent = Number(item.percentage_used || 0);
                const _percentBadgeText = Math.round(percent) > 999 ? "999%+" : `${Math.round(percent)}%`;
                const hasHugeBudgetValues =
                  Number(item.total || 0) >= 1_000_000_000 ||
                  Number(item.budget_limit || 0) >= 1_000_000_000;
                const backendStatus = String(item.budget_status || "");
                const progressStatus =
                  backendStatus === "Over Limit" ? "danger" :
                    backendStatus === "High Risk" ? "highRisk" :
                      backendStatus === "Warning" ? "warning" :
                        backendStatus === "On Track" ? "healthy" :
                          percent >= 100 ? "danger" :
                            percent >= 90 ? "highRisk" :
                              percent >= 70 ? "warning" : "healthy";

                const progressTrackClass =
                  progressStatus === "danger" ? "bg-destructive/15 dark:bg-destructive/10 rounded-full" :
                    progressStatus === "highRisk" ? "bg-orange-500/20 dark:bg-orange-400/20 rounded-full" :
                      progressStatus === "warning" ? "bg-amber-500/20 dark:bg-amber-400/20 rounded-full" :
                        "bg-primary/20 rounded-full";

                const progressIndicatorClass =
                  progressStatus === "danger" ? "bg-destructive shadow-[0_0_16px_rgba(239,68,68,0.6)] dark:shadow-[0_0_16px_rgba(248,113,113,0.6)] rounded-full duration-1000 ease-out" :
                    progressStatus === "highRisk" ? "bg-orange-500 dark:bg-orange-400 shadow-[0_0_12px_rgba(249,115,22,0.4)] rounded-full duration-1000 ease-out" :
                      progressStatus === "warning" ? "bg-amber-500 dark:bg-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.4)] rounded-full duration-1000 ease-out" :
                        "bg-primary shadow-[0_0_14px_rgba(34,197,94,0.4)] rounded-full duration-1000 ease-out";

                const iconColorClass = "text-muted-foreground";

                const _isNear = progressStatus === "highRisk" || progressStatus === "warning";

                return (
                  <div
                    key={item.category}
                    className={cn(
                      "space-y-3 group p-2 -mx-2 rounded-xl transition-all duration-300",
                      "hover:bg-muted dark:hover:bg-muted/30",
                      activeBudgetStatusCategory === item.category && "bg-muted dark:bg-muted/30"
                    )}
                    onMouseEnter={() => setActiveBudgetStatusCategory(item.category)}
                    onMouseLeave={() => setActiveBudgetStatusCategory(null)}
                    onTouchStart={() => setActiveBudgetStatusCategory(item.category)}
                    onClick={() => setActiveBudgetStatusCategory(item.category)}
                  >
                    <div className="flex items-center justify-between text-sm px-1">
                      <div className="flex items-center gap-2.5">
                        {(() => {
                          const CategoryIcon = categoryIconMap[item.category] || Circle;
                          return <CategoryIcon className={`h-4 w-4 ${iconColorClass}`} aria-hidden="true" />;
                        })()}
                        <span className="font-semibold text-foreground/90">
                          {t(`categories.${item.category}`, { defaultValue: item.category })}
                        </span>
                      </div>
                      <div className="flex items-center justify-end">
                        <span
                          className={cn(
                            "inline-block min-w-[140px] overflow-hidden text-ellipsis whitespace-nowrap text-right tabular-nums text-foreground",
                            hasHugeBudgetValues && "text-[13px]"
                          )}
                          title={`${formatCompactUzs(item.total)} / ${formatCompactUzs(item.budget_limit)} UZS`}
                        >
                          <span className="font-semibold">{formatCompactUzs(item.total)}</span> /{" "}
                          <span className="font-semibold">{formatCompactUzs(item.budget_limit)}</span> UZS
                        </span>
                      </div>
                    </div>
                    <Progress
                      value={loading ? 0 : percent}
                      className="h-2.5"
                      trackClassName={progressTrackClass}
                      indicatorClassName={progressIndicatorClass}
                    />
                  </div>
                );
              })}
            </CardContent>
            {!loading && topBudgetBreakdown.length > 0 && (
              <div className="px-5 pb-5 pt-3">
                <Button asChild variant="ghost" className="w-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors">
                  <Link to="/budgets">
                    {hiddenBudgetCount > 0
                      ? t("dashboard.viewAllBudgetsWithCount", { count: hiddenBudgetCount, defaultValue: `View all budgets (+${hiddenBudgetCount})` })
                      : t("dashboard.viewAllBudgets", { defaultValue: "View all budgets" })}
                  </Link>
                </Button>
              </div>
            )}
          </Card>

          <Card className="shadow-sm flex flex-col h-full overflow-hidden">
            <CardHeader className="pb-3 shrink-0">
              <CardTitle>{t("dashboard.recentActivity")}</CardTitle>
              <CardDescription>{t("dashboard.latestTransactions")}</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col pt-0 pb-2">
              {loading && (
                <div className="flex min-h-[120px] items-center justify-center">
                  <LoadingSpinner className="h-8 w-8" />
                </div>
              )}
              {!loading && recentExpenses.length === 0 && (
                <EmptyState inline description={t("dashboard.noExpensesYet")} />
              )}
              {recentExpenses.map((e) => (
                <div
                  key={e.id}
                  className="flex-1 flex items-center justify-between gap-2 border-b border-border/40 p-2 -mx-2 rounded-xl hover:bg-muted dark:hover:bg-muted/30 transition-all duration-300 last:border-0"
                >
                  <div className="space-y-1 flex-1 min-w-0 pr-8">
                    <TooltipProvider delayDuration={0}>
                      <UITooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            className="max-w-full text-left truncate font-semibold text-foreground/90 leading-6 outline-none focus-visible:underline decoration-muted-foreground underline-offset-4 cursor-pointer block"
                            onClick={(ev) => ev.preventDefault()}
                          >
                            {e.title}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-[250px] sm:max-w-xs break-words">
                          {e.title}
                        </TooltipContent>
                      </UITooltip>
                    </TooltipProvider>
                    <p className="text-xs text-muted-foreground/80 font-medium truncate">
                      {t(`categories.${e.category}`, { defaultValue: e.category })}
                    </p>
                    <p className="hidden text-xs text-muted-foreground/80 font-medium truncate">
                      {t(`categories.${e.category}`, { defaultValue: e.category })} • {e.date}
                    </p>
                  </div>
                  <div className="font-semibold text-sm text-foreground/90 shrink-0 whitespace-nowrap">
                    {Number(e.amount) >= 1_000_000 ? formatCompactUzs(e.amount) : formatUzs(e.amount)} UZS
                  </div>
                </div>
              ))}
            </CardContent>
            {!loading && (
              <div className="px-5 pb-5 pt-3 shrink-0">
                <Button asChild variant="ghost" className="w-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors">
                  <Link to="/expenses">{t("dashboard.viewAllTransactions")}</Link>
                </Button>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="shadow-sm">
            <CardHeader className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>{t("dashboard.spendingTrends")}</CardTitle>
                <CardDescription>
                  {t("dashboard.dailyTrendThisMonth")}
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="min-h-[260px]">
              {trendLoading ? (
                <div className="h-[220px] w-full animate-pulse rounded-lg bg-muted" />
              ) : chartData.length === 0 ? (
                <EmptyState inline description={t("dashboard.noTrendDataYet")} />
              ) : (
                <div className="h-[240px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={chartData}
                      margin={{ top: 10, right: 16, left: 0, bottom: 10 }}
                      onMouseMove={(state) => {
                        const p = state?.activePayload?.[0]?.payload;
                        if (p) setActiveTrendPoint(p);
                      }}
                      onTouchMove={(state) => {
                        const p = state?.activePayload?.[0]?.payload;
                        if (p) setActiveTrendPoint(p);
                      }}
                      onClick={(state) => {
                        const p = state?.activePayload?.[0]?.payload;
                        if (p) setActiveTrendPoint(p);
                      }}
                      onMouseLeave={() => setActiveTrendPoint(null)}
                    >
                      <defs>
                        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.05} />
                        </linearGradient>
                      </defs>

                      <CartesianGrid strokeDasharray="4 4" className="stroke-muted" />

                      <XAxis
                        dataKey="day"
                        tick={{ fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                        interval="preserveStartEnd"
                        minTickGap={16}
                        padding={{ left: 8, right: 8 }}
                      />

                      <YAxis
                        domain={[0, "auto"]}
                        tickFormatter={(v) => formatCompactUzs(v)}
                        tick={{ fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                        width={64}
                      />

                      <Tooltip
                        cursor={{ stroke: "hsl(var(--primary))", strokeWidth: 1.5, strokeOpacity: 0.35 }}
                        contentStyle={tooltipStyle}
                        labelStyle={{ color: "hsl(var(--foreground))" }}
                        formatter={(value) => [
                          <span style={{ color: "hsl(var(--primary))", fontWeight: 600 }}>
                            {formatUzs(value)} UZS
                          </span>,
                          t("dashboard.amount"),
                        ]}
                        labelFormatter={(label, payload) => {
                          const full = payload?.[0]?.payload?.date;
                          return full ? formatPrettyDate(full, i18n.language) : label;
                        }}
                      />

                      <Area
                        type="monotone"
                        dataKey="amount"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        fill="url(#trendFill)"
                        dot={false}
                        activeDot={{ r: 5, stroke: "hsl(var(--background))", strokeWidth: 2 }}
                      />
                      {activeTrendPoint && (
                        <ReferenceDot
                          x={activeTrendPoint.day}
                          y={activeTrendPoint.amount}
                          r={5}
                          fill="hsl(var(--primary))"
                          stroke="hsl(var(--background))"
                          strokeWidth={2}
                        />
                      )}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            <Card className="shadow-sm flex flex-col h-full">
              <CardHeader className="pb-3">
                <CardTitle>{t("dashboard.categoryBreakdown")}</CardTitle>
                <CardDescription>{t("dashboard.currentMonthTotals")}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 pt-0 pb-4">
                {loading ? (
                  <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
                ) : monthCategoryChartData.length === 0 ? (
                  <EmptyState inline description={t("dashboard.noCategoryDataYet")} />
                ) : (
                  <div className="h-full min-h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={monthCategoryChartData}
                        layout="vertical"
                        margin={{ top: 2, right: 8, left: 8, bottom: 8 }}
                        barCategoryGap="20%"
                      >
                        <CartesianGrid strokeDasharray="4 4" className="stroke-muted" />
                        <XAxis
                          type="number"
                          tickFormatter={(value) => formatCompactUzs(value)}
                          tick={{ fontSize: 12 }}
                          axisLine={false}
                          tickLine={false}
                          width={60}
                        />
                        <YAxis
                          type="category"
                          dataKey="category"
                          tickFormatter={(value) =>
                            t(`categories.${value}`, { defaultValue: value })
                          }
                          tick={{ fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                          width={120}
                          interval={0}
                        />

                        <Tooltip
                          cursor={{ fill: "hsl(var(--primary))", fillOpacity: 0.08 }}
                          contentStyle={tooltipStyle}
                          labelStyle={{ color: "hsl(var(--foreground))" }}
                          labelFormatter={(label) =>
                            t(`categories.${label}`, { defaultValue: label })
                          }
                          formatter={(value) => [
                            <span style={{ color: "hsl(var(--primary))", fontWeight: 600 }}>
                              {formatUzs(value)} UZS
                            </span>,
                            t("dashboard.total"),
                          ]}
                        />

                        <Bar
                          dataKey="total"
                          fill="hsl(var(--primary))"
                          radius={[0, 6, 6, 0]}
                        >
                          {monthCategoryChartData.map((entry) => {
                            const isActive = activeCategoryBar === entry.category;
                            return (
                              <Cell
                                key={`cell-${entry.category}`}
                                stroke={isActive ? "hsl(var(--primary))" : "none"}
                                strokeWidth={isActive ? 2 : 0}
                                onMouseEnter={() => setActiveCategoryBar(entry.category)}
                                onMouseLeave={() => setActiveCategoryBar(null)}
                                onClick={() => setActiveCategoryBar(entry.category)}
                                style={{ transition: "opacity 160ms ease" }}
                              />
                            );
                          })}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Upcoming Recurring Charges Widget */}
            <Card className="shadow-sm flex flex-col h-full overflow-hidden">
              <CardHeader className="pb-3 shrink-0">
                <div className="flex items-center gap-2">
                  <CalendarClock className="h-5 w-5 text-primary" />
                  <CardTitle>{t("dashboard.upcomingRecurringTitle")}</CardTitle>
                </div>
                <CardDescription>{t("dashboard.upcomingRecurringSubtitle")}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col pt-0 pb-4">
                {!user?.is_premium ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-center space-y-3 py-6">
                    <div className="p-3 bg-amber-500/10 rounded-full">
                      <span className="text-2xl">✨</span>
                    </div>
                    <h4 className="font-semibold">{t("recurring.premiumTitle")}</h4>
                    <p className="text-sm text-muted-foreground">{t("recurring.premiumDesc")}</p>
                    <Button asChild variant="outline" size="sm" className="mt-2 text-primary hover:text-primary">
                      <Link to="/settings">{t("dashboard.learnMore")}</Link>
                    </Button>
                  </div>
                ) : loading ? (
                  <div className="flex-1 flex items-center justify-center">
                    <LoadingSpinner className="h-6 w-6" />
                  </div>
                ) : recurringExpenses.length === 0 ? (
                  <EmptyState inline description={t("dashboard.noUpcomingRecurring")} />
                ) : (
                  <div className="space-y-0 -mt-1">
                    {recurringExpenses.map((e) => (
                      <div
                        key={e.id}
                        className="flex items-center justify-between gap-2 border-b border-border/40 p-2 -mx-2 rounded-xl hover:bg-muted dark:hover:bg-muted/30 transition-all duration-300 last:border-0"
                      >
                        <div className="space-y-1 flex-1 min-w-0 pr-8">
                          <div className="font-medium leading-6 truncate pb-0.5">{e.title}</div>
                          <div className="text-xs text-muted-foreground/80 font-medium truncate">
                            {formatRelativeDue(e.days_until_due, e.next_due_date)}
                          </div>
                        </div>
                        <div className="font-semibold text-sm tabular-nums text-right shrink-0 whitespace-nowrap">
                          {formatAmountDisplay(e.amount)} <span className="text-xs font-normal text-muted-foreground">UZS</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

        </div>
      </div>
    </div>
  );
}

