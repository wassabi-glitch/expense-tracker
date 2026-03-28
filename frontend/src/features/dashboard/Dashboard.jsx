import { useMemo, useState, useEffect } from "react";
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
import { Download, Plus, Wallet, TrendingUp, Layers, Circle, CalendarClock, HelpCircle } from "lucide-react";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { InteractiveTooltip } from "@/components/InteractiveTooltip";
import { cn } from "@/lib/utils";
import { categoryIconMap, getCategoryBgClass, getCategoryColorClass } from "@/lib/category";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  ReferenceDot,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import { formatPrettyDate, formatUzs, formatCompactUzs, shortMMDD } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { useDashboardDataQuery } from "./hooks/useDashboardDataQuery";

const EMPTY_ARRAY = [];

const getCategoryColor = (category) => {
  const colors = {
    "Groceries": "#10b981",
    "Dining Out": "#f97316",
    "Electronics": "#06b6d4",
    "Housing": "#3b82f6",
    "Utilities": "#eab308",
    "Subscriptions": "#a855f7",
    "Transport": "#0ea5e9",
    "Health": "#ef4444",
    "Personal care": "#6366f1",
    "Education": "#f59e0b",
    "Clothing": "#ec4899",
    "Family & Events": "#84cc16",
    "Entertainment": "#d946ef",
    "Installments & Debt": "#64748b",
    "Business / Work": "#14b8a6",
  };
  return colors[category] || "#94a3b8";
};

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const [activeTrendPoint, setActiveTrendPoint] = useState(null);
  const [activeBudgetStatusCategory, setActiveBudgetStatusCategory] = useState(null);
  const todayIso = toISODateInTimeZone();
  const [year, month] = todayIso.split("-");
  const monthStartIso = `${year}-${month}-01`;
  
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 640);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

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
      rawValue: Math.abs(summary.overall_balance),
      value: formatCompactUzs(Math.abs(summary.overall_balance)),
      fullValue: formatUzs(Math.abs(summary.overall_balance)),
      prefix: summary.overall_balance >= 0 ? "+" : "-",
      hint: t("dashboard.totalBalanceHint"),
      cardClassName: summary.overall_balance >= 0
        ? "border-border bg-card transition-all duration-300 hover:border-primary/40 active:border-primary/40 hover:shadow-[0_0_15px_rgba(34,197,94,0.1)] active:shadow-[0_0_15px_rgba(34,197,94,0.1)] active:scale-[0.98]"
        : "border-destructive/50 bg-card transition-all duration-300 hover:border-destructive active:border-destructive hover:shadow-[0_0_15px_rgba(239,68,68,0.1)] active:shadow-[0_0_15px_rgba(239,68,68,0.1)] active:scale-[0.98]",
      titleClassName: summary.overall_balance >= 0 ? "text-muted-foreground" : "text-destructive",
      iconClassName: "text-muted-foreground",
      valueClassName: summary.overall_balance >= 0 ? "text-primary" : "text-destructive animate-pulse",
      icon: Wallet,
    },
    {
      label: t("dashboard.incomeThisMonth", { defaultValue: "Income This Month" }),
      rawValue: summary.income,
      value: formatCompactUzs(summary.income),
      fullValue: formatUzs(summary.income),
      prefix: "",
      cardClassName: "border-border bg-card transition-all duration-300 hover:border-border/80 active:border-border/80 hover:shadow-sm active:shadow-sm active:scale-[0.98]",
      titleClassName: "text-muted-foreground",
      iconClassName: "text-muted-foreground",
      hint: t("dashboard.incomeHint"),
      valueClassName: "text-foreground",
      icon: Wallet,
    },
    {
      label: t("dashboard.spentThisMonth", { defaultValue: "Spent This Month" }),
      rawValue: summary.spent,
      value: formatCompactUzs(summary.spent),
      fullValue: formatUzs(summary.spent),
      prefix: "",
      cardClassName: "border-border bg-card transition-all duration-300 hover:border-border/80 active:border-border/80 hover:shadow-sm active:shadow-sm active:scale-[0.98]",
      titleClassName: "text-muted-foreground",
      iconClassName: "text-muted-foreground",
      hint: t("dashboard.spentHint"),
      valueClassName: "text-foreground",
      icon: TrendingUp,
    },
    {
      label: t("dashboard.remainingThisMonth", { defaultValue: "Remaining This Month" }),
      rawValue: Math.abs(summary.remaining),
      value: formatCompactUzs(Math.abs(summary.remaining)),
      fullValue: formatUzs(Math.abs(summary.remaining)),
      prefix: summary.remaining >= 0 ? "+" : "-",
      cardClassName: summary.remaining >= 0
        ? "border-border bg-card transition-all duration-300 hover:border-primary/40 active:border-primary/40 hover:shadow-[0_0_15px_rgba(34,197,94,0.1)] active:shadow-[0_0_15px_rgba(34,197,94,0.1)] active:scale-[0.98]"
        : "border-destructive/50 bg-card transition-all duration-300 hover:border-destructive active:border-destructive hover:shadow-[0_0_15px_rgba(239,68,68,0.1)] active:shadow-[0_0_15px_rgba(239,68,68,0.1)] active:scale-[0.98]",
      valueClassName: summary.remaining >= 0 ? "text-primary" : "text-destructive animate-pulse",
      titleClassName: summary.remaining >= 0 ? "text-muted-foreground" : "text-destructive",
      iconClassName: "text-muted-foreground",
      hint: t("dashboard.remainingHint"),
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
      <div className="container mx-auto px-4 py-8 xl:py-12 space-y-8 xl:space-y-12">
        <PageHeader title={t("dashboard.title")} description={t("dashboard.subtitle")}>
          <Button asChild variant="outline" className="bg-background hover:bg-muted h-8 sm:h-9 text-xs sm:text-sm px-3 sm:px-4">
            <Link to="/export">
              <Download className="mr-1 sm:mr-2 h-3.5 w-3.5 sm:h-4 sm:w-4" /> {t("dashboard.export")}
            </Link>
          </Button>
          <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm h-8 sm:h-9 text-xs sm:text-sm px-3 sm:px-4">
            <Link to="/expenses">
              <Plus className="mr-1 sm:mr-2 h-3.5 w-3.5 sm:h-4 sm:w-4" /> {t("dashboard.addExpense")}
            </Link>
          </Button>
        </PageHeader>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {/* Stats Grid */}
        <div className={cn(
          "grid gap-4 xl:grid-cols-4 xl:gap-6 2xl:gap-8",
          isMobile ? "grid-cols-1" : "grid-cols-2"
        )}>
          {statCards.map((s, i) => {
            const Icon = s.icon;
            const isTotalBalance = i === 0;
            
            // If mobile, we want Total Balance full width, and others in a special container?
            // Wait, the user said "total balance card covers full screen ... and below it you display the rest of the 3 cards in 1 row make it scrollable sideways"
            // This is easier to handle with a conditional outer wrap.
            if (isMobile && !isTotalBalance) return null;

            return (
              <Card 
                key={i} 
                className={cn(
                  "shadow-sm overflow-hidden relative transition-all duration-200 hover:shadow-md hover:bg-card/60 active:scale-[0.98] cursor-pointer", 
                  s.cardClassName,
                  isMobile && isTotalBalance && "w-full"
                )}
              >
                <CardHeader className={cn(
                  "flex flex-row items-center justify-between space-y-0 p-5 pb-0 w-full",
                  isMobile && "pt-4"
                )}>
                  <CardTitle className={cn("text-refined-label", s.titleClassName)}>
                    {s.label}
                  </CardTitle>
                  <Icon className={cn("size-icon-sm", s.iconClassName)} />
                </CardHeader>
                <CardContent className={cn("px-5 pb-5 pt-0", isMobile && "-mt-2")}>
                  <CurrencyAmount
                    value={s.rawValue}
                    prefix={s.prefix}
                    format="compact"
                    tooltip="always"
                    className="flex items-baseline gap-1.5 flex-wrap text-left outline-none"
                    valueClassName={cn("text-[24px] lg:text-[28px] font-bold tracking-tight tabular-nums break-words", s.valueClassName)}
                    currencyClassName="text-[10px] md:text-xs lg:text-sm opacity-70"
                    tooltipContent={`${s.prefix}${s.fullValue} UZS`}
                  />
                  {s.hint && (
                    isMobile ? (
                      <div className="absolute bottom-3 right-3">
                        <InteractiveTooltip content={s.hint}>
                          <HelpCircle className="h-4 w-4 text-muted-foreground/40 hover:text-muted-foreground/70 transition-colors cursor-help" />
                        </InteractiveTooltip>
                      </div>
                    ) : (
                      <p className="mt-2.5 text-ui-desc leading-relaxed text-muted-foreground/80 font-medium">
                        {s.hint}
                      </p>
                    )
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Mobile-only scrollable row for other cards */}
        {isMobile && (
          <div className="flex overflow-x-auto gap-4 -mx-4 px-4 pb-4 no-scrollbar scroll-smooth">
            {statCards.slice(1).map((s, i) => {
              const Icon = s.icon;
              return (
                <Card 
                  key={i} 
                  className={cn("shadow-sm overflow-hidden relative min-w-[260px] flex-shrink-0 transition-all duration-200 hover:shadow-md hover:bg-card/60 active:scale-[0.98] cursor-pointer", s.cardClassName)}
                >
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 p-5 pt-4 pb-0 w-full">
                    <CardTitle className={cn("text-refined-label", s.titleClassName)}>
                      {s.label}
                    </CardTitle>
                    <Icon className={cn("size-icon-sm", s.iconClassName)} />
                  </CardHeader>
                  <CardContent className="px-5 pb-5 pt-0 -mt-2">
                    <CurrencyAmount
                      value={s.rawValue}
                      prefix={s.prefix}
                      format="compact"
                      tooltip="always"
                      className="flex items-baseline gap-1.5 flex-wrap text-left outline-none"
                      valueClassName={cn("text-[24px] lg:text-[28px] font-bold tracking-tight tabular-nums break-words", s.valueClassName)}
                      currencyClassName="text-[10px] md:text-xs lg:text-sm mt-auto mb-1 opacity-70"
                      tooltipContent={`${s.prefix}${s.fullValue} UZS`}
                    />
                    {s.hint && (
                      <div className="absolute bottom-3 right-3">
                        <InteractiveTooltip content={s.hint}>
                          <HelpCircle className="h-4 w-4 text-muted-foreground/40 hover:text-muted-foreground/70 transition-colors cursor-help" />
                        </InteractiveTooltip>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
        {showZeroIncomeHint && (
          <p className="text-sm text-muted-foreground">{t("dashboard.zeroIncomeHint")}</p>
        )}

        <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-2 xl:gap-8 2xl:gap-10">
          <Card className="shadow-sm flex flex-col h-full overflow-hidden">
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
              {topBudgetBreakdown.map((item, index) => {
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


                const _isNear = progressStatus === "highRisk" || progressStatus === "warning";

                const CategoryIcon = categoryIconMap[item.category] || Circle;
                const iconColorClass = getCategoryColorClass(item.category);
                const categoryLabel = t(`categories.${item.category}`, { defaultValue: item.category });

                return (
                  <div
                    key={item.category}
                    className={cn(
                      "flex flex-col gap-2.5 group p-2 -mx-2 rounded-xl transition-colors duration-200",
                      "hover:bg-muted dark:hover:bg-muted/30 active:bg-muted/50 dark:active:bg-muted/40",
                      activeBudgetStatusCategory === item.category && "bg-muted dark:bg-muted/30",
                      "animate-in fade-in slide-in-from-bottom-2 duration-500 fill-both"
                    )}
                    style={{ animationDelay: `${index * 50}ms` }}
                    onMouseEnter={() => setActiveBudgetStatusCategory(item.category)}
                    onMouseLeave={() => setActiveBudgetStatusCategory(null)}
                    onTouchStart={() => setActiveBudgetStatusCategory(item.category)}
                    onClick={() => setActiveBudgetStatusCategory(item.category)}
                  >
                    <div className="flex items-center justify-between text-sm px-1">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <CategoryIcon className={cn("size-icon-sm shrink-0", iconColorClass)} aria-hidden="true" />
                        <InteractiveTooltip content={categoryLabel}>
                          <span className="font-medium text-foreground/90 truncate cursor-help">
                            {categoryLabel}
                          </span>
                        </InteractiveTooltip>
                      </div>
                      <div className="hidden min-[450px]:flex items-center justify-end shrink-0">
                        <InteractiveTooltip
                          content={`${formatUzs(item.total)} / ${formatUzs(item.budget_limit)} UZS`}
                          className={cn(
                            "flex items-baseline justify-end gap-1 min-w-[102px] sm:min-w-[140px] overflow-hidden text-ellipsis whitespace-nowrap text-right tabular-nums text-foreground",
                            hasHugeBudgetValues && "text-[13px]"
                          )}
                        >
                          <span className="font-bold tracking-tight">{formatCompactUzs(item.total)}</span>{" "}
                          <span className="font-medium text-muted-foreground/70 px-0.5">/</span>{" "}
                          <span className="font-bold tracking-tight">{formatCompactUzs(item.budget_limit)}</span>
                          <span className="text-[10px] font-medium text-muted-foreground/70 uppercase ml-0.5">UZS</span>
                        </InteractiveTooltip>
                      </div>
                    </div>
                    <Progress
                      value={loading ? 0 : percent}
                      className="h-2.5"
                      trackClassName={progressTrackClass}
                      indicatorClassName={progressIndicatorClass}
                    />
                    <div className="flex min-[450px]:hidden items-center justify-end px-1 mt-0.5">
                      <InteractiveTooltip
                        content={`${formatUzs(item.total)} / ${formatUzs(item.budget_limit)} UZS`}
                        className={cn(
                          "flex items-baseline justify-end gap-1 overflow-hidden text-ellipsis whitespace-nowrap text-right tabular-nums text-foreground",
                          hasHugeBudgetValues ? "text-xs" : "text-[13px]"
                        )}
                      >
                        <span className="font-bold tracking-tight">{formatCompactUzs(item.total)}</span>{" "}
                        <span className="font-medium text-muted-foreground/70 px-0.5">/</span>{" "}
                        <span className="font-bold tracking-tight">{formatCompactUzs(item.budget_limit)}</span>
                        <span className="text-[10px] font-medium text-muted-foreground/70 uppercase ml-0.5">UZS</span>
                      </InteractiveTooltip>
                    </div>
                  </div>
                );
              })}
            </CardContent>
            {!loading && topBudgetBreakdown.length > 0 && (
              <div className="px-5 pb-5 lg:pb-3 pt-3 lg:pt-1">
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
              {recentExpenses.map((e, index) => {
                const Icon = categoryIconMap[e.category] || Circle;
                const bgClass = getCategoryBgClass(e.category);
                return (
                  <div
                    key={e.id}
                    className={cn(
                      "flex items-center justify-between gap-4 border-b border-border/40 py-3 lg:py-2 px-2 -mx-2 rounded-xl hover:bg-muted dark:hover:bg-muted/30 active:bg-muted/50 dark:active:bg-muted/40 transition-colors duration-200 last:border-0",
                      "animate-in fade-in slide-in-from-bottom-2 duration-500 fill-both"
                    )}
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <div className={cn("size-icon-lg lg:size-icon-md shrink-0 rounded-full flex items-center justify-center transition-all duration-300", bgClass)}>
                      <Icon className="size-icon-sm lg:size-[16px]" />
                    </div>
                    <div className="space-y-0.5 flex-1 min-w-0 pr-2">
                      <TooltipProvider delayDuration={0}>
                        <UITooltip>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              className="max-w-full text-left truncate font-semibold text-ui-title lg:text-ui-desc text-foreground/90 leading-tight outline-none focus-visible:underline decoration-muted-foreground underline-offset-4 cursor-pointer block transition-all"
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
                      <p className="text-ui-detail lg:text-[10px] text-muted-foreground/80 font-medium truncate capitalize">
                        {t(`categories.${e.category}`, { defaultValue: e.category })}
                      </p>
                      <p className="text-[10px] lg:text-[9px] font-normal text-muted-foreground/50">
                        {formatPrettyDate(e.date, i18n.language)}
                      </p>
                    </div>
                    {Number(e.amount) >= 1_000_000 ? (
                      <InteractiveTooltip
                        content={`${formatUzs(e.amount)} UZS`}
                        className="flex items-baseline justify-end gap-1 font-semibold text-ui-title lg:text-ui-desc text-foreground/90 shrink-0 whitespace-nowrap"
                      >
                        <span>{formatCompactUzs(e.amount)}</span>
                        <span className="text-[10px] uppercase tracking-[0.08em] text-muted-foreground/70">UZS</span>
                      </InteractiveTooltip>
                    ) : (
                      <div className="flex items-baseline justify-end gap-1 font-semibold text-ui-title lg:text-ui-desc text-foreground/90 shrink-0 whitespace-nowrap">
                        <span>{formatUzs(e.amount)}</span>
                        <span className="text-[10px] uppercase tracking-[0.08em] text-muted-foreground/70">UZS</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </CardContent>
            {!loading && (
              <div className="px-5 pb-4 lg:pb-3 pt-2 lg:pt-1 shrink-0">
                <Button asChild variant="ghost" className="w-full text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors h-9 lg:h-8">
                  <Link to="/expenses">{t("dashboard.viewAllTransactions")}</Link>
                </Button>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="shadow-sm">
            <CardHeader className="p-4 sm:p-5 pb-2">
              <div className="flex flex-col gap-1">
                <CardTitle>{t("dashboard.spendingTrends")}</CardTitle>
                <CardDescription>
                  {t("dashboard.dailyTrendThisMonth")}
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="h-[280px] sm:h-[320px] xl:h-[350px] p-0 sm:p-6 sm:pt-0">
              {trendLoading ? (
                <div className="h-[220px] w-full animate-pulse rounded-lg bg-muted" />
              ) : chartData.length === 0 ? (
                <EmptyState inline description={t("dashboard.noTrendDataYet")} />
              ) : (
                <div className="h-full w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={chartData}
                      className="outline-none"
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
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




                      <XAxis
                        dataKey="day"
                        tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                        axisLine={false}
                        tickLine={false}
                        interval="preserveStartEnd"
                        minTickGap={16}
                        padding={{ left: 0, right: 8 }}
                      />

                      <YAxis
                        domain={[0, "auto"]}
                        tickFormatter={(v) => formatCompactUzs(v)}
                        tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                        axisLine={false}
                        tickLine={false}
                        width={60}
                      />

                      <Tooltip
                        cursor={{ stroke: "hsl(var(--primary))", strokeWidth: 1.5, strokeDasharray: "4 4" }}
                        content={({ active, payload, label }) => {
                          if (active && payload && payload.length) {
                            return (
                              <div className="rounded-xl border border-border/50 bg-background/95 p-2.5 shadow-xl backdrop-blur-md">
                                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">
                                  {formatPrettyDate(payload[0].payload.date, i18n.language)}
                                </p>
                                <div className="flex items-baseline gap-1.5">
                                  <span className="text-sm font-bold tabular-nums text-foreground">
                                    {payload[0].value >= 1_000_000_000 ? formatCompactUzs(payload[0].value) : formatUzs(payload[0].value)}
                                  </span>
                                  <span className="text-[9px] font-bold text-muted-foreground/70 uppercase tracking-widest">UZS</span>
                                </div>
                              </div>
                            );
                          }
                          return null;
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

          <div className="grid gap-6 lg:grid-cols-2 xl:gap-8 2xl:gap-10">
            <Card className="shadow-sm flex flex-col h-full">
              <CardHeader className="p-4 sm:p-5 pb-0 sm:pb-0">
                <CardTitle>{t("dashboard.categoryBreakdown")}</CardTitle>
                <CardDescription>{t("dashboard.currentMonthTotals")}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1 pt-0 pb-4 sm:pt-0">
                {loading ? (
                  <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
                ) : monthCategoryChartData.length === 0 ? (
                  <EmptyState inline description={t("dashboard.noCategoryDataYet")} />
                ) : (
                  <div
                    className="overflow-visible"
                    style={{ height: `${Math.max(300, monthCategoryChartData.length * 70)}px` }}
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={monthCategoryChartData}
                        layout="vertical"
                        className="outline-none"
                        margin={{ top: 5, right: 45, left: 10, bottom: 20 }}
                        barCategoryGap="20%"
                      >
                        <defs>
                          <linearGradient id="barGradient" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={1} />
                          </linearGradient>
                        </defs>
                        <XAxis 
                          type="number" 
                          tickFormatter={(value) => formatCompactUzs(value)}
                          tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          type="category"
                          dataKey="category"
                          hide
                        />

                        <Tooltip 
                          cursor={{ fill: "hsl(var(--primary))", opacity: 0.05 }}
                          content={({ active, payload, label }) => {
                            if (active && payload && payload.length) {
                              return (
                                <div className="rounded-xl border border-border/50 bg-background/95 p-2.5 shadow-xl backdrop-blur-md">
                                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">
                                    {t(`categories.${label}`, { defaultValue: label })}
                                  </p>
                                  <div className="flex items-baseline gap-1.5">
                                    <span className="text-sm font-bold tabular-nums text-foreground">
                                      {payload[0].value >= 1_000_000_000 ? formatCompactUzs(payload[0].value) : formatUzs(payload[0].value)}
                                    </span>
                                    <span className="text-[9px] font-bold text-muted-foreground/70 uppercase tracking-widest">UZS</span>
                                  </div>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />

                        <Bar
                          dataKey="total"
                          radius={[0, 4, 4, 0]}
                          barSize={24}
                          animationDuration={1500}
                        >
                          <LabelList
                            dataKey="category"
                            position="top"
                            offset={8}
                            content={({ x, y, value }) => (
                              <text
                                x={x}
                                y={y - 6}
                                fill="hsl(var(--muted-foreground) / 0.7)"
                                fontSize={10}
                                fontWeight={500}
                                className="tracking-tight"
                                textAnchor="start"
                              >
                                {t(`categories.${value}`, { defaultValue: value })}
                              </text>
                            )}
                          />
                          {monthCategoryChartData.map((entry, index) => (
                            <Cell 
                              key={`cell-${index}`} 
                              fill={getCategoryColor(entry.category)}
                            />
                          ))}
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
                    {recurringExpenses.map((e, index) => {
                      const Icon = categoryIconMap[e.category] || CalendarClock;
                      const bgClass = getCategoryBgClass(e.category);
                      return (
                        <div
                          key={e.id}
                          className={cn(
                            "flex items-center justify-between gap-4 border-b border-border/40 py-3 lg:py-2 px-2 -mx-2 rounded-xl hover:bg-muted dark:hover:bg-muted/30 active:bg-muted/50 dark:active:bg-muted/40 transition-colors duration-200 last:border-0",
                            "animate-in fade-in slide-in-from-bottom-2 duration-500 fill-both"
                          )}
                          style={{ animationDelay: `${index * 50}ms` }}
                        >
                          <div className={cn("size-icon-lg lg:size-icon-md shrink-0 rounded-full flex items-center justify-center transition-all duration-300", bgClass)}>
                            <Icon className="size-icon-sm lg:size-[16px]" />
                          </div>
                          <div className="space-y-0.5 flex-1 min-w-0 pr-2">
                            <div className="font-semibold text-ui-title lg:text-ui-desc text-foreground/90 leading-tight truncate transition-all">
                              {e.title}
                            </div>
                            <p className="text-ui-detail lg:text-[10px] text-muted-foreground/80 font-medium truncate capitalize">
                              {t(`categories.${e.category}`, { defaultValue: e.category })}
                            </p>
                            <p className="text-[10px] lg:text-[9px] font-normal text-muted-foreground/50">
                              {formatRelativeDue(e.days_until_due, e.next_due_date)}
                            </p>
                          </div>
                          <CurrencyAmount
                            value={e.amount}
                            format="display"
                            tooltip="compact"
                            className="flex items-baseline justify-end gap-1 font-semibold text-ui-title lg:text-ui-desc tabular-nums text-right shrink-0 whitespace-nowrap"
                            currencyClassName="text-[10px] lg:text-[9px]"
                          />
                        </div>
                      );
                    })}
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

