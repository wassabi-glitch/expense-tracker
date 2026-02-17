import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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
import { Download, Plus, Wallet, TrendingUp, Layers, Crown } from "lucide-react";

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

const formatPrettyDate = (isoDate) => {
  if (!isoDate) return "";
  const date = new Date(isoDate);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

const formatUzs = (value) =>
  String(Number(value || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

const formatCompactUZS = (value) => {
  const num = Number(value || 0);

  if (num >= 1_000_000_000)
    return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
  if (num >= 1_000_000)
    return `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (num >= 1_000)
    return `${(num / 1_000).toFixed(1).replace(/\.0$/, "")}K`;

  return num;
};

const categoryDotClass = {
  Food: "bg-amber-500",
  Transport: "bg-blue-500",
  Housing: "bg-violet-500",
  Entertainment: "bg-rose-500",
  Utilities: "bg-emerald-500",
  Other: "bg-slate-500",
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);
  const [recentExpenses, setRecentExpenses] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [trendLoading, setTrendLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
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
      } catch (e) {
        setError(e.message || "Failed to load dashboard");
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
        setError(e.message || "Failed to load trend data");
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
      biggestCategory: biggest?.category || "�",
      avgDaily,
      categoryBreakdown,
    };
  }, [stats]);

  const statCards = [
    {
      label: "Total spent (this month)",
      value: `${formatUzs(derived.totalSpent)} UZS`,
      icon: Wallet,
    },
    {
      label: "Remaining budget",
      value: `${formatUzs(derived.remainingBudget)} UZS`,
      icon: TrendingUp,
    },
    { label: "Biggest category", value: derived.biggestCategory, icon: Crown },
    {
      label: "Average daily spend",
      value: `${formatUzs(derived.avgDaily)} UZS`,
      icon: Layers,
    },
  ];

  const chartData = useMemo(() => {
    return (trendData || [])
      .map((d) => ({
        date: d.date,
        day: shortMMDD(d.date),
        amount: Number(d.amount || 0),
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date));
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
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Your financial overview for this month.
            </p>
          </div>
          <div className="flex gap-3">
            <Button asChild variant="outline" className="bg-background hover:bg-muted">
              <Link to="/export">
                <Download className="mr-2 h-4 w-4" /> Export
              </Link>
            </Button>
            <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm">
              <Link to="/expenses">
                <Plus className="mr-2 h-4 w-4" /> Add Expense
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
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {s.label}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{s.value}</div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="shadow-sm lg:col-span-2">
            <CardHeader>
              <CardTitle>Budget Status</CardTitle>
              <CardDescription>Monthly allocation by category</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {loading && (
                <div className="flex min-h-[120px] items-center justify-center">
                  <LoadingSpinner className="h-8 w-8" />
                </div>
              )}
              {!loading && derived.categoryBreakdown.length === 0 && (
                <p className="text-sm text-muted-foreground">No budgets yet.</p>
              )}
              {derived.categoryBreakdown.map((item) => {
                const percent = Number(item.percentage_used || 0);
                return (
                  <div key={item.category} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span
                          className={`h-2 w-2 rounded-full ${categoryDotClass[item.category] || "bg-slate-500"
                            }`}
                        />
                        <span className="font-medium">{item.category}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-foreground">
                          <span className="font-semibold">{formatCompactUZS(item.total)}</span> /{" "}
                          <span className="font-semibold">{formatCompactUZS(item.budget_limit)}</span> UZS
                        </span>

                        <Badge
                          variant={
                            percent >= 100 ? "destructive" : percent >= 90 ? "outline" : "secondary"
                          }
                        >
                          {Math.round(percent)}%
                        </Badge>
                      </div>
                    </div>
                    <Progress value={percent} className="h-2" />
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <Card className="shadow-sm flex flex-col">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest transactions</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 space-y-4">
              {loading && (
                <div className="flex min-h-[120px] items-center justify-center">
                  <LoadingSpinner className="h-8 w-8" />
                </div>
              )}
              {!loading && recentExpenses.length === 0 && (
                <p className="text-sm text-muted-foreground">No expenses yet.</p>
              )}
              {recentExpenses.map((e) => (
                <div
                  key={e.id}
                  className="flex items-center justify-between border-b border-border pb-4 last:border-0 last:pb-0"
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none">{e.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {e.category}  {e.date}
                    </p>
                  </div>
                  <div className="font-semibold text-sm">{formatUzs(e.amount)} UZS</div>
                </div>
              ))}
            </CardContent>
            <div className="p-4 pt-0 mt-auto">
              <Button asChild variant="ghost" className="w-full text-muted-foreground hover:text-foreground">
                <Link to="/expenses">View All Transactions</Link>
              </Button>
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="shadow-sm">
            <CardHeader className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Spending Trends</CardTitle>
                <CardDescription>
                  Daily trend from the 1st of this month to today
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="min-h-[260px]">
              {trendLoading ? (
                <div className="h-[220px] w-full animate-pulse rounded-lg bg-muted" />
              ) : chartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">No trend data yet.</p>
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
                          "Amount",
                        ]}
                        labelFormatter={(label, payload) => {
                          const full = payload?.[0]?.payload?.date;
                          return full ? formatPrettyDate(full) : label;
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
              <CardTitle>Category Breakdown</CardTitle>
              <CardDescription>Current month totals by category</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              {loading ? (
                <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
              ) : monthCategoryChartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">No category data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={monthCategoryChartData} margin={{ top: 8, right: 8, left: 0, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="4 4" className="stroke-muted" />
                    <XAxis
                      dataKey="category"
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
                      formatter={(value) => [
                        <span style={{ color: "hsl(var(--primary))", fontWeight: 600 }}>
                          {formatUzs(value)} UZS
                        </span>,
                        "Total",
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
