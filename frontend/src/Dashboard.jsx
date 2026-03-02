import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { LoadingSpinner } from "./components/ui/loading-spinner";
import { Progress } from "./components/ui/progress";
import { Download, Plus, Wallet, TrendingUp, Layers, Crown, Car, Gamepad2, Home, Utensils, Wrench, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

const categoryIconMap = {
  Food: Utensils,
  Transport: Car,
  Housing: Home,
  Entertainment: Gamepad2,
  Utilities: Wrench,
  Other: Circle,
};

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { getExpenses, getMonthToDateTrend, getThisMonthStats } from "./api";
import { toISODateInTimeZone } from "./lib/date";
import { localizeApiError } from "./lib/errorMessages";

const UZ_MONTHS_SHORT = [
  "Yan",
  "Fev",
  "Mar",
  "Apr",
  "May",
  "Iyn",
  "Iyl",
  "Avg",
  "Sen",
  "Okt",
  "Noy",
  "Dek",
];

const formatPrettyDate = (isoDate, locale, lang) => {
  if (!isoDate) return "";
  const date = new Date(isoDate);
  if (lang?.startsWith("uz")) {
    const d = date.getDate();
    const month = UZ_MONTHS_SHORT[date.getMonth()] || "";
    return `${d} ${month}`;
  }
  return date.toLocaleDateString(locale, { month: "short", day: "numeric" });
};

const formatUzs = (value) => {
  const num = Number(value || 0);
  if (num >= 1_000_000_000_000) {
    return `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
  }
  if (num >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
  }
  return String(num).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
};

const formatUzsCard = (value) => {
  const num = Number(value || 0);
  if (num >= 1_000_000_000_000) {
    return `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
  }
  return String(num).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
};

const formatCompactUZS = (value) => {
  const num = Number(value || 0);

  if (num >= 1_000_000_000_000)
    return `${(num / 1_000_000_000_000).toFixed(3).replace(/\.?0+$/, "")}T`;
  if (num >= 1_000_000_000)
    return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
  if (num >= 1_000_000)
    return `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (num >= 1_000)
    return `${(num / 1_000).toFixed(1).replace(/\.0$/, "")}K`;

  return num;
};

const shortMMDD = (iso) => String(iso || "").slice(5);

const tooltipStyle = {
  borderRadius: 10,
  border: "1px solid hsl(var(--border))",
  background: "hsl(var(--background))",
  color: "hsl(var(--foreground))",
  boxShadow: "0 10px 30px rgba(0,0,0,0.12)",
};

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const chartLocale = i18n.language?.startsWith("ru")
    ? "ru-RU"
    : i18n.language?.startsWith("uz")
      ? "uz-UZ"
      : "en-US";
  const [loading, setLoading] = useState(true);
  const [animateProgress, setAnimateProgress] = useState(false);
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);
  const [recentExpenses, setRecentExpenses] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [trendLoading, setTrendLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setAnimateProgress(false);
      setError("");
      try {
        const endDate = toISODateInTimeZone();
        const [year, month] = endDate.split("-");
        const startDate = `${year}-${month}-01`;

        const [statsRes, expensesRes] = await Promise.all([
          getThisMonthStats(),
          getExpenses({
            limit: 5,
            skip: 0,
            sort: "newest",
            start_date: startDate,
            end_date: endDate,
          }),
        ]);

        setStats(statsRes || null);
        setRecentExpenses(expensesRes || []);
        requestAnimationFrame(() => setAnimateProgress(true));
      } catch (e) {
        setError(localizeApiError(e?.message, t) || t("dashboard.loadError"));
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    const loadTrend = async () => {
      setTrendLoading(true);
      try {
        const res = await getMonthToDateTrend();
        setTrendData(res || []);
      } catch (e) {
        setError(localizeApiError(e?.message, t) || t("dashboard.trendError"));
      } finally {
        setTrendLoading(false);
      }
    };
    loadTrend();
  }, []);

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
      label: t("dashboard.totalSpentMonth"),
      value: `${formatUzsCard(derived.totalSpent)} UZS`,
      icon: Wallet,
    },
    {
      label: t("dashboard.remainingBudget"),
      value: `${formatUzsCard(derived.remainingBudget)} UZS`,
      icon: TrendingUp,
    },
    {
      label: t("dashboard.biggestCategory"),
      value: t(`categories.${derived.biggestCategory}`, { defaultValue: derived.biggestCategory }),
      icon: Crown,
    },
    {
      label: t("dashboard.avgDailySpend"),
      value: `${formatUzsCard(derived.avgDaily)} UZS`,
      icon: Layers,
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
    return (derived.categoryBreakdown || []).map((item) => ({
      category: item.category,
      total: Number(item.total || 0),
    }));
  }, [derived.categoryBreakdown]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{t("dashboard.title")}</h1>
            <p className="text-muted-foreground mt-1">
              {t("dashboard.subtitle")}
            </p>
          </div>
          <div className="flex gap-3">
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
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((s, i) => {
            const Icon = s.icon;
            return (
              <Card key={i} className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1.5">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {s.label}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="text-2xl font-bold">{s.value}</div>
                </CardContent>
              </Card>
            );
          })}
        </div>

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
                <p className="text-sm text-muted-foreground">{t("dashboard.noBudgetsYet")}</p>
              )}
              {derived.categoryBreakdown.map((item) => {
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
                  <div key={item.category} className="space-y-3 group hover:bg-muted/30 p-2 -mx-2 rounded-xl transition-all duration-300">
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
                          title={`${formatCompactUZS(item.total)} / ${formatCompactUZS(item.budget_limit)} UZS`}
                        >
                          <span className="font-semibold">{formatCompactUZS(item.total)}</span> /{" "}
                          <span className="font-semibold">{formatCompactUZS(item.budget_limit)}</span> UZS
                        </span>
                      </div>
                    </div>
                    <Progress
                      value={animateProgress ? percent : 0}
                      className="h-2.5"
                      trackClassName={progressTrackClass}
                      indicatorClassName={progressIndicatorClass}
                    />
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card className="shadow-sm flex flex-col h-full overflow-hidden">
            <CardHeader className="pb-4 shrink-0">
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
                <p className="text-sm text-muted-foreground">{t("dashboard.noExpensesYet")}</p>
              )}
              {recentExpenses.map((e) => (
                <div
                  key={e.id}
                  className="flex-1 flex items-center justify-between border-b border-border/40 py-2 last:border-0 last:pb-0"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground/90 leading-none">{e.title}</p>
                    <p className="text-xs text-muted-foreground/80 font-medium">
                      {t(`categories.${e.category}`, { defaultValue: e.category })} • {e.date}
                    </p>
                  </div>
                  <div className="font-semibold text-sm text-foreground/90">{formatUzs(e.amount)} UZS</div>
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
                <p className="text-sm text-muted-foreground">{t("dashboard.noTrendDataYet")}</p>
              ) : (
                <div className="h-[240px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 10 }}>
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
                        tickFormatter={(v) => formatCompactUZS(v)}
                        tick={{ fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                        width={64}
                      />

                      <Tooltip
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
                          return full ? formatPrettyDate(full, chartLocale, i18n.language) : label;
                        }}
                      />

                      <Area
                        type="monotone"
                        dataKey="amount"
                        stroke="hsl(var(--primary))"
                        strokeWidth={2}
                        fill="url(#trendFill)"
                        dot={false}
                        activeDot={{ r: 4 }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>{t("dashboard.categoryBreakdown")}</CardTitle>
              <CardDescription>{t("dashboard.currentMonthTotals")}</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              {loading ? (
                <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
              ) : monthCategoryChartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("dashboard.noCategoryDataYet")}</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={monthCategoryChartData} margin={{ top: 8, right: 8, left: 0, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="4 4" className="stroke-muted" />
                    <XAxis
                      dataKey="category"
                      tickFormatter={(value) =>
                        t(`categories.${value}`, { defaultValue: value })
                      }
                      tick={{ fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      interval="preserveStartEnd"
                      minTickGap={24}
                    />
                    <YAxis
                      tickFormatter={(value) => formatCompactUZS(value)}
                      tick={{ fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      width={60}
                    />

                    <Tooltip
                      cursor={false}
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

                    <Bar dataKey="total" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

