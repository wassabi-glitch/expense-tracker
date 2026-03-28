import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { differenceInCalendarDays } from "date-fns";
import { Wallet, TrendingUp, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { CurrencyAmount } from "@/components/CurrencyAmount";

import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import { formatCompactUzs, formatUzs } from "@/lib/format";
import { useAnalyticsChartsQuery, useAnalyticsSummaryQuery } from "./hooks/useAnalyticsDataQueries";
const EMPTY_ARRAY = [];
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

const formatLongDate = (iso, locale, lang) => {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return String(iso || "");
  if (lang?.startsWith("uz")) {
    const d = dt.getDate();
    const month = UZ_MONTHS_SHORT[dt.getMonth()] || "";
    const y = dt.getFullYear();
    return `${d} ${month} ${y}`;
  }
  return dt.toLocaleDateString(locale, { month: "short", day: "numeric", year: "numeric" });
};

const fromISODate = (iso) => {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
};

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
  const { t, i18n } = useTranslation();
  const chartLocale = i18n.language?.startsWith("ru")
    ? "ru-RU"
    : i18n.language?.startsWith("uz")
      ? "uz-UZ"
      : "en-US";
  const [searchParams, setSearchParams] = useSearchParams();
  const [hint, setHint] = useState("");

  const [range, setRange] = useState(() => {
    const start = searchParams.get("start_date");
    const end = searchParams.get("end_date");
    if (start && end && start >= MIN_ANALYTICS_DATE && end >= MIN_ANALYTICS_DATE) return { mode: "custom", startDate: start, endDate: end };
    const rawDays = Number(searchParams.get("days") || "30");
    const allowedDays = [7, 30, 90, 365];
    const safeDays = allowedDays.includes(rawDays) ? rawDays : 30;
    return { mode: "days", days: safeDays };
  });

  const [startInput, setStartInput] = useState(() => searchParams.get("start_date") || "");
  const [endInput, setEndInput] = useState(() => searchParams.get("end_date") || "");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const todayISO = useMemo(() => toISODateInTimeZone(), []);

  const summaryQuery = useAnalyticsSummaryQuery();

  const chartParams = useMemo(() => buildQueryParams(range), [range]);
  const chartsQuery = useAnalyticsChartsQuery(chartParams);

  const history = summaryQuery.data || null;
  const trendData = chartsQuery.data?.trendData || EMPTY_ARRAY;
  const categoryBreakdown = chartsQuery.data?.categoryBreakdown || EMPTY_ARRAY;
  const loadingSummary = summaryQuery.isLoading;
  const loadingCharts = chartsQuery.isLoading || chartsQuery.isFetching;
  const error = (summaryQuery.error || chartsQuery.error)
    ? localizeApiError(summaryQuery.error?.message || chartsQuery.error?.message, t) ||
    summaryQuery.error?.message ||
    chartsQuery.error?.message ||
    t("analytics.chartsLoadFailed")
    : "";

  useEffect(() => {
    const next = new URLSearchParams();
    if (range.mode === "days") next.set("days", String(range.days));
    if (range.mode === "custom") {
      next.set("start_date", range.startDate);
      next.set("end_date", range.endDate);
    }
    setSearchParams(next, { replace: true });
  }, [range, setSearchParams]);

  const summaryCards = useMemo(() => [
    {
      titleKey: "analytics.lifetimeSpent",
      icon: Wallet,
      rawValue: history?.total_spent_lifetime || 0,
      tooltip: `${formatUzs(history?.total_spent_lifetime || 0)} UZS`
    },
    {
      titleKey: "analytics.avgTransaction",
      icon: TrendingUp,
      rawValue: history?.average_transaction || 0,
      tooltip: `${formatUzs(history?.average_transaction || 0)} UZS`
    },
    {
      titleKey: "analytics.totalTransactions",
      icon: Layers,
      rawValue: history?.total_transaction || 0,
      isRaw: true
    },
  ], [history, t]);
  
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

  const trendChartData = useMemo(() => (trendData || []).map((d) => ({ date: d.date, amount: Number(d.amount || 0) })).sort((a, b) => new Date(a.date) - new Date(b.date)), [trendData]);
  const categoryChartData = useMemo(() => (categoryBreakdown || []).map((c) => ({ category: c.category, total: Number(c.total || 0), count: Number(c.count || 0) })).sort((a, b) => b.total - a.total), [categoryBreakdown]);

  const rangeLabel = useMemo(() => {
    if (range.mode === "days") return t("analytics.lastDays", { days: range.days });
    if (range.mode === "custom") return t("analytics.rangeCustom", { start: range.startDate, end: range.endDate });
    return "";
  }, [range, t]);

  const validateInputs = useCallback((startISO, endISO) => {
    if (!startISO && !endISO) return { ok: false, message: t("analytics.hintPickBoth") };
    if (!startISO || !endISO) return { ok: false, message: t("analytics.hintProvideBoth") };
    const start = fromISODate(startISO);
    const end = fromISODate(endISO);
    if (!start || !end) return { ok: false, message: t("analytics.hintInvalidDate") };
    if (startISO < MIN_ANALYTICS_DATE || endISO < MIN_ANALYTICS_DATE) return { ok: false, message: t("analytics.hintTooEarly") };
    if (endISO > todayISO) return { ok: false, message: t("analytics.hintEndFuture") };
    if (start > end) return { ok: false, message: t("analytics.hintStartAfterEnd") };
    const daysInclusive = differenceInCalendarDays(end, start) + 1;
    if (daysInclusive > 366) return { ok: false, message: t("analytics.hintMaxRange") };
    return { ok: true, message: "" };
  }, [todayISO, t]);

  const inputsStatus = useMemo(() => validateInputs(startInput, endInput), [startInput, endInput, validateInputs]);
  const applyPreset = (preset) => { setHint(""); setStartInput(""); setEndInput(""); setRange({ mode: "days", days: preset.days }); };
  const applyCustom = () => {
    const check = validateInputs(startInput, endInput);
    if (!check.ok) return setHint(check.message);
    setHint("");
    setRange({ mode: "custom", startDate: startInput, endDate: endInput });
  };
  const resetAll = () => { setHint(""); setStartInput(""); setEndInput(""); setRange({ mode: "days", days: 30 }); };
  const isPresetActive = (preset) => range.mode === "days" && range.days === preset.days;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl sm:text-3xl font-bold tracking-tight text-foreground">{t("analytics.title")}</h1>
          <p className="text-xs sm:text-base text-muted-foreground mt-0.5 sm:mt-1">{t("analytics.subtitle")}</p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className={cn(
          "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
          isMobile ? "grid-cols-1" : "grid-cols-3"
        )}>
          {loadingSummary && !history ? (
            <>
              <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
              {!isMobile && (
                <>
                  <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
                  <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
                </>
              )}
            </>
          ) : summaryCards.map((card, idx) => {
            if (isMobile && idx !== 0) return null;
            return (
              <Card
                key={idx}
                className={cn(
                  "border-border/40 bg-card/40 shadow-sm transition-all duration-200 hover:shadow-md hover:bg-card/60 active:scale-[0.98] cursor-pointer",
                  isMobile && idx === 0 && "w-full"
                )}
              >
                <CardHeader className="p-4 flex flex-row items-center justify-between space-y-0 pb-1">
                  <CardTitle className="text-refined-label">
                    {t(card.titleKey)}
                  </CardTitle>
                  <card.icon className="h-3.5 w-3.5 text-muted-foreground/40" />
                </CardHeader>
                <CardContent className="p-4 pt-1">
                  {card.isRaw ? (
                    <div className="text-xl sm:text-2xl font-bold leading-none tabular-nums text-foreground">{card.rawValue}</div>
                  ) : (
                    <CurrencyAmount
                      value={card.rawValue}
                      format="compact"
                      tooltip="always"
                      className="flex items-baseline gap-1.5 flex-wrap outline-none"
                      valueClassName="text-xl sm:text-2xl font-bold tracking-tight tabular-nums text-foreground"
                      currencyClassName="text-xs opacity-70"
                      tooltipContent={card.tooltip}
                    />
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Mobile-only scrollable row for other cards */}
        {isMobile && !loadingSummary && history && (
          <div className="flex overflow-x-auto gap-4 -mx-4 px-4 pb-4 no-scrollbar scroll-smooth">
            {summaryCards.slice(1).map((card, idx) => (
              <Card
                key={idx}
                className="border-border/40 bg-card/40 shadow-sm transition-all duration-200 hover:shadow-md hover:bg-card/60 active:scale-[0.98] cursor-pointer min-w-[260px] flex-shrink-0"
              >
                <CardHeader className="p-4 pt-4 flex flex-row items-center justify-between space-y-0 pb-1">
                  <CardTitle className="text-refined-label">
                    {t(card.titleKey)}
                  </CardTitle>
                  <card.icon className="h-3.5 w-3.5 text-muted-foreground/40" />
                </CardHeader>
                  <CardContent className="p-4 pt-1">
                    {card.isRaw ? (
                      <div className="text-xl font-bold leading-none tabular-nums text-foreground">{card.rawValue}</div>
                    ) : (
                      <CurrencyAmount
                        value={card.rawValue}
                        format="compact"
                        tooltip="always"
                        className="flex items-baseline gap-1.5 flex-wrap outline-none"
                        valueClassName="text-xl font-bold tracking-tight tabular-nums text-foreground"
                        currencyClassName="text-xs opacity-70"
                        tooltipContent={card.tooltip}
                      />
                    )}
                  </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Card className="border-border/40 bg-card/40 shadow-sm" style={{ marginBottom: "var(--analytics-gap)" }}>
          <CardHeader className="p-4 sm:p-5 pb-2 sm:pb-1">
            <div className="flex flex-col gap-1">
              <CardTitle className="text-base font-semibold tracking-tight">{t("analytics.filtersTitle")}</CardTitle>
              <CardDescription className="text-ui-micro">{t("analytics.filtersDesc")}</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="p-4 sm:p-5 pt-0 space-y-4 sm:space-y-3">
            <div className="space-y-2.5">
              <p className="text-ui-micro">{t("analytics.quickPresets")}</p>
              <div className="flex flex-wrap gap-2">
                {PRESETS.map((p) => (
                  <Button
                    key={p.key}
                    variant={isPresetActive(p) ? "default" : "outline"}
                    onClick={() => applyPreset(p)}
                    className="btn-pill"
                  >
                    {p.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-3.5">
              <p className="text-ui-micro">{t("analytics.customRange")}</p>
              <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                <div className="grid gap-3 sm:flex sm:items-center flex-1">
                  <div className="relative flex-1 lg:max-w-[200px]">
                    <Input
                      type="date"
                      value={startInput}
                      onChange={(e) => { setStartInput(e.target.value); setHint(""); }}
                      min={MIN_ANALYTICS_DATE}
                      max={todayISO}
                      className="input-pill"
                    />
                  </div>
                  <span className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest text-center px-1 shrink-0">{t("analytics.to")}</span>
                  <div className="relative flex-1 lg:max-w-[200px]">
                    <Input
                      type="date"
                      value={endInput}
                      onChange={(e) => { setEndInput(e.target.value); setHint(""); }}
                      min={startInput && startInput > MIN_ANALYTICS_DATE ? startInput : MIN_ANALYTICS_DATE}
                      max={todayISO}
                      className="input-pill"
                    />
                  </div>
                </div>
                <div className="flex gap-2 lg:ml-2">
                  <Button
                    className="btn-pill-lg flex-1 sm:w-28 lg:w-32"
                    onClick={applyCustom}
                    disabled={!inputsStatus.ok}
                    title={!inputsStatus.ok ? inputsStatus.message : t("analytics.applyDateRange")}
                  >
                    {t("analytics.apply")}
                  </Button>
                  <Button
                    className="btn-pill-lg flex-1 sm:w-28 lg:w-32"
                    variant="outline"
                    onClick={resetAll}
                  >
                    {t("analytics.reset")}
                  </Button>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-1.5 border-t border-border/40 pt-4">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">{t("analytics.range")}:</span>
                <span className="text-[11px] font-bold text-foreground">{rangeLabel}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/60">{t("analytics.activeMode")}:</span>
                <span className="text-[11px] font-medium text-muted-foreground">{range.mode === "days" ? t("analytics.modePreset") : t("analytics.modeCustom")}</span>
              </div>
              {hint && <p className="text-[10px] font-medium text-amber-500 animate-in fade-in slide-in-from-left-1">{hint}</p>}
            </div>
          </CardContent>
        </Card>

        <div className="flex flex-col pb-8" style={{ gap: "var(--analytics-gap)" }}>
          <Card className="border-border/40 bg-card/40 shadow-sm overflow-hidden">
            <CardHeader className="p-4 sm:p-5">
              <div className="flex flex-col gap-1">
                <CardTitle className="text-base font-semibold tracking-tight">{t("analytics.dailyTrend")}</CardTitle>
                <span className="text-analytics-period">{rangeLabel}</span>
              </div>
            </CardHeader>
            <CardContent className="h-[280px] sm:h-[320px] p-0 sm:p-6 sm:pt-0">
              {loadingCharts && trendChartData.length === 0 ? (
                <div className="h-full w-full animate-pulse bg-muted/20" />
              ) : trendChartData.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-xs text-muted-foreground">{t("analytics.noTrendData")}</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="analyticsTrendFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                      </linearGradient>
                    </defs>

                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => formatLongDate(value, chartLocale, i18n.language)}
                      tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      interval="preserveStartEnd"
                      minTickGap={35}
                    />
                    <YAxis
                      tickFormatter={(value) => formatCompactUzs(value)}
                      tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      width={60}
                    />
                    <Tooltip
                      cursor={{ stroke: "hsl(var(--primary))", strokeWidth: 1, strokeDasharray: "4 4" }}
                      content={({ active, payload, label }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="rounded-xl border border-border/50 bg-background/95 p-2.5 shadow-xl backdrop-blur-md">
                              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-1">
                                {formatLongDate(label, chartLocale, i18n.language)}
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
                      fill="url(#analyticsTrendFill)"
                      animationDuration={1000}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/40 bg-card/40 shadow-sm overflow-hidden">
            <CardHeader className="p-4 sm:p-5 pb-0 sm:pb-0">
              <div className="flex flex-col gap-1">
                <CardTitle className="text-base font-semibold tracking-tight">{t("analytics.categoryBreakdown")}</CardTitle>
                <span className="text-analytics-period">{rangeLabel}</span>
              </div>
            </CardHeader>
            <CardContent 
              className="p-0 sm:p-6 sm:pt-0 overflow-visible"
              style={{ height: `${Math.max(300, categoryChartData.length * 70)}px` }}
            >
              {loadingCharts && categoryChartData.length === 0 ? (
                <div className="h-full w-full animate-pulse bg-muted/20" />
              ) : categoryChartData.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-xs text-muted-foreground">{t("analytics.noCategoryData")}</p>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart 
                    data={categoryChartData} 
                    layout="vertical" 
                    margin={{ top: 5, right: 30, left: 10, bottom: 20 }}
                    barCategoryGap="20%"
                  >
                    <defs>
                      <linearGradient id="analyticsBarGradient" x1="0" y1="0" x2="1" y2="0">
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
                              <p className="mt-1 text-[10px] text-muted-foreground/80 lowercase">
                                {payload[0].payload.count} {t(payload[0].payload.count === 1 ? "common.transaction" : "common.transactions")}
                              </p>
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
                      {categoryChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={getCategoryColor(entry.category)} />
                      ))}
                    </Bar>
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
