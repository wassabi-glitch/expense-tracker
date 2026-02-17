import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
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
import { differenceInCalendarDays } from "date-fns";

import { Button } from "./components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { Input } from "./components/ui/input";

import { getAnalyticsHistory, getCategoryBreakdown, getDailyTrend } from "./api";
import { toISODateInTimeZone } from "./lib/date";

// ------------------ formatters ------------------
const formatCompactUZS = (value) => {
  const num = Number(value || 0);
  if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return num;
};

const formatUzs = (value) =>
  String(Number(value || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

const formatLongDate = (iso) => {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return String(iso || "");
  return dt.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const fromISODate = (iso) => {
  // Safe parse for "YYYY-MM-DD" as local date
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
};

// ------------------ presets ------------------
const PRESETS = [
  { key: "7d", label: "7d", days: 7 },
  { key: "30d", label: "30d", days: 30 },
  { key: "90d", label: "90d", days: 90 },
  { key: "365d", label: "365d", days: 365 },
];
const MIN_ANALYTICS_DATE = "2020-01-01";

function buildQueryParams(range) {
  if (!range) return {};
  if (range.mode === "days") return { days: range.days };
  if (range.mode === "custom") return { start_date: range.startDate, end_date: range.endDate };
  return {};
}

export default function Analytics() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingCharts, setLoadingCharts] = useState(true);

  const [error, setError] = useState("");
  const [hint, setHint] = useState("");

  const [history, setHistory] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [categoryBreakdown, setCategoryBreakdown] = useState([]);

  // charts range (single source of truth)
  const [range, setRange] = useState(() => {
    const start = searchParams.get("start_date");
    const end = searchParams.get("end_date");
    if (start && end && start >= MIN_ANALYTICS_DATE && end >= MIN_ANALYTICS_DATE) {
      return { mode: "custom", startDate: start, endDate: end };
    }
    const rawDays = Number(searchParams.get("days") || "30");
    const allowedDays = [7, 30, 90, 365];
    const safeDays = allowedDays.includes(rawDays) ? rawDays : 30;
    return { mode: "days", days: safeDays };
  });

  // Native date inputs
  const [startInput, setStartInput] = useState(() => searchParams.get("start_date") || "");
  const [endInput, setEndInput] = useState(() => searchParams.get("end_date") || "");

  const todayISO = useMemo(() => toISODateInTimeZone(), []);

  // ------------------ load summary once ------------------
  useEffect(() => {
    const loadSummary = async () => {
      setLoadingSummary(true);
      setError("");
      try {
        const res = await getAnalyticsHistory();
        setHistory(res || null);
      } catch (e) {
        setError(e?.message || "Failed to load analytics summary");
      } finally {
        setLoadingSummary(false);
      }
    };
    loadSummary();
  }, []);

  // ------------------ load charts on range change ------------------
  useEffect(() => {
    const loadCharts = async () => {
      setLoadingCharts(true);
      setError("");
      try {
        const params = buildQueryParams(range);

        const [trendRes, categoryRes] = await Promise.all([
          getDailyTrend(params),
          getCategoryBreakdown(params),
        ]);

        setTrendData(trendRes || []);
        setCategoryBreakdown(categoryRes || []);
      } catch (e) {
        setError(e?.message || "Failed to load charts");
      } finally {
        setLoadingCharts(false);
      }
    };

    loadCharts();
  }, [range]);
  useEffect(() => {
    const next = new URLSearchParams();
    if (range.mode === "days") next.set("days", String(range.days));
    if (range.mode === "custom") {
      next.set("start_date", range.startDate);
      next.set("end_date", range.endDate);
    }
    setSearchParams(next, { replace: true });
  }, [range, setSearchParams]);

  // ------------------ derived data ------------------
  const summary = useMemo(() => {
    return [
      { label: "Lifetime spent", value: `${formatUzs(history?.total_spent_lifetime || 0)} UZS` },
      { label: "Avg transaction", value: `${formatUzs(history?.average_transaction || 0)} UZS` },
      { label: "Total transactions", value: `${history?.total_transaction || 0}` },
    ];
  }, [history]);

  const trendChartData = useMemo(() => {
    return (trendData || [])
      .map((d) => ({ date: d.date, amount: Number(d.amount || 0) }))
      .sort((a, b) => new Date(a.date) - new Date(b.date));
  }, [trendData]);

  const categoryChartData = useMemo(() => {
    return (categoryBreakdown || [])
      .map((c) => ({
        category: c.category,
        total: Number(c.total || 0),
        count: Number(c.count || 0),
      }))
      .sort((a, b) => b.total - a.total);
  }, [categoryBreakdown]);

  const rangeLabel = useMemo(() => {
    if (range.mode === "days") return `Last ${range.days} days`;
    if (range.mode === "custom") return `${range.startDate} -> ${range.endDate}`;
    return "";
  }, [range]);

  // ------------------ UI validation (prevent backend errors) ------------------
  const validateInputs = (startISO, endISO) => {
    // No noisy errors: return { ok, message }
    if (!startISO && !endISO) return { ok: false, message: "Pick both start and end date." };
    if (!startISO || !endISO) return { ok: false, message: "Provide both start and end date." };

    const start = fromISODate(startISO);
    const end = fromISODate(endISO);
    if (!start || !end) return { ok: false, message: "Invalid date." };
    if (startISO < MIN_ANALYTICS_DATE || endISO < MIN_ANALYTICS_DATE) {
      return { ok: false, message: "Dates earlier than 2020-01-01 are not allowed." };
    }

    // prevent future end date
    if (endISO > todayISO) return { ok: false, message: "End date cannot be in the future." };

    // start <= end
    if (start > end) return { ok: false, message: "Start date cannot be after end date." };

    // max 366 days inclusive
    const daysInclusive = differenceInCalendarDays(end, start) + 1;
    if (daysInclusive > 366) return { ok: false, message: "Max allowed range is 366 days." };

    return { ok: true, message: "" };
  };

  const inputsStatus = useMemo(() => validateInputs(startInput, endInput), [startInput, endInput, todayISO]);

  // ------------------ actions ------------------
  const applyPreset = (preset) => {
    setError("");
    setHint("");

    // Clear inputs (optional, makes UX clearer)
    setStartInput("");
    setEndInput("");
    setRange({ mode: "days", days: preset.days });
  };

  const applyCustom = () => {
    setError("");

    const check = validateInputs(startInput, endInput);
    if (!check.ok) {
      // No red errors if you prefer — keep this subtle hint instead
      setHint(check.message);
      return;
    }

    setHint("");
    setRange({
      mode: "custom",
      startDate: startInput,
      endDate: endInput,
    });
  };

  const resetAll = () => {
    setError("");
    setHint("");
    setStartInput("");
    setEndInput("");
    setRange({ mode: "days", days: 30 });
  };

  const isPresetActive = (preset) => {
    return range.mode === "days" && range.days === preset.days;
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        {/* Page title */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Analytics</h1>
          <p className="text-muted-foreground">Understand your spending trends.</p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {/* Lifetime stats (unfiltered) */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {loadingSummary && !history ? (
            <>
              <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
              <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
              <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
            </>
          ) : (
            summary.map((item) => (
              <Card key={item.label} className="border-0 bg-card shadow-sm">
                <CardHeader className="space-y-1">
                  <CardDescription>{item.label}</CardDescription>
                  <CardTitle className="text-2xl">{item.value}</CardTitle>
                </CardHeader>
              </Card>
            ))
          )}
        </div>

        {/* Filters card (like Expenses page) */}
        <Card className="border-0 bg-card shadow-sm">
          <CardHeader className="space-y-1">
            <CardTitle className="text-base">Filters</CardTitle>
            <CardDescription>Choose either a quick preset or a custom date range.</CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="space-y-1">
              <p className="text-sm font-medium">Quick presets</p>
              <p className="text-xs text-muted-foreground">
                Presets always use the last N days up to today.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <Button
                  key={p.key}
                  variant={isPresetActive(p) ? "default" : "outline"}
                  onClick={() => applyPreset(p)}
                  className="h-9 w-[72px]"
                >
                  {p.label}
                </Button>
              ))}
            </div>

            <div className="space-y-1">
              <p className="text-sm font-medium">Custom range</p>
              <p className="text-xs text-muted-foreground">
                Provide both dates, from 2020-01-01 to today, with a maximum of 366 days (inclusive).
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_auto] md:items-center">
              <Input
                type="date"
                value={startInput}
                onChange={(e) => {
                  setStartInput(e.target.value);
                  setHint("");
                }}
                min={MIN_ANALYTICS_DATE}
                max={todayISO}
              />
              <span className="text-muted-foreground text-sm">to</span>
              <Input
                type="date"
                value={endInput}
                onChange={(e) => {
                  setEndInput(e.target.value);
                  setHint("");
                }}
                min={startInput && startInput > MIN_ANALYTICS_DATE ? startInput : MIN_ANALYTICS_DATE}
                max={todayISO}
              />

              <Button
                className="h-9"
                onClick={applyCustom}
                disabled={!inputsStatus.ok}
                title={!inputsStatus.ok ? inputsStatus.message : "Apply date range"}
              >
                Apply
              </Button>

              <Button className="h-9" variant="outline" onClick={resetAll}>
                Reset
              </Button>
            </div>

            <div className="flex flex-col gap-1">
              <p className="text-sm text-muted-foreground">
                Range: <span className="font-medium text-foreground">{rangeLabel}</span>
              </p>
              <p className="text-xs text-muted-foreground">
                Active mode: {range.mode === "days" ? "Preset days" : "Custom range"}.
              </p>

              {/* subtle hint (not a backend error) */}
              {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
            </div>
          </CardContent>
        </Card>

        {/* Charts */}
        <div className="grid gap-6">
          {/* Daily trend */}
          <Card className="border-0 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Daily trend</CardTitle>
              <CardDescription>{rangeLabel}</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              {loadingCharts && trendChartData.length === 0 ? (
                <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
              ) : trendChartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">No trend data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendChartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="analyticsTrendFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="4 4" className="stroke-muted" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => formatLongDate(value)}
                      tick={{ fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      interval="preserveStartEnd"
                      minTickGap={28}
                    />
                    <YAxis
                      tickFormatter={(value) => formatCompactUZS(value)}
                      tick={{ fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      width={60}
                    />
                    <Tooltip
                      formatter={(value) => [`${formatUzs(value)} UZS`, "Amount"]}
                      labelFormatter={(label) => `Date: ${formatLongDate(label)}`}
                      contentStyle={{
                        borderRadius: 10,
                        border: "1px solid hsl(var(--border))",
                        background: "hsl(var(--background))",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="amount"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      fill="url(#analyticsTrendFill)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          {/* Category breakdown: full width + vertical bars */}
          <Card className="border-0 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Category breakdown</CardTitle>
              <CardDescription>{rangeLabel}</CardDescription>
            </CardHeader>
            <CardContent className="h-[340px]">
              {loadingCharts && categoryChartData.length === 0 ? (
                <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
              ) : categoryChartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">No category data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={categoryChartData}
                    layout="vertical"
                    margin={{ top: 10, right: 16, left: 40, bottom: 10 }}
                  >
                    <CartesianGrid strokeDasharray="4 4" className="stroke-muted" />

                    <YAxis
                      type="category"
                      dataKey="category"
                      tick={{ fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      width={120}
                    />

                    <XAxis
                      type="number"
                      tickFormatter={(value) => formatCompactUZS(value)}
                      tick={{ fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <Tooltip
                      cursor={{ fill: "hsl(var(--muted))", opacity: 0.25 }}
                      formatter={(value) => [`${formatUzs(value)} UZS`, "Total"]}
                      labelFormatter={(label) => `Category: ${label}`}
                      contentStyle={{
                        borderRadius: 10,
                        border: "1px solid hsl(var(--border))",
                        background: "hsl(var(--background))",
                      }}
                    />

                    <Bar dataKey="total" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} />
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



