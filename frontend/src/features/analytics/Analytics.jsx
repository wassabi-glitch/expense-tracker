import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
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

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import { useAnalyticsChartsQuery, useAnalyticsSummaryQuery } from "./hooks/useAnalyticsDataQueries";
const EMPTY_ARRAY = [];

const formatCompactUZS = (value) => {
  const num = Number(value || 0);
  if (num >= 1_000_000_000) return `${(num / 1_000_000_000).toFixed(1).replace(/\.0$/, "")}B`;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return num;
};

const formatUzs = (value) => String(Number(value || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
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

  const summary = useMemo(() => [
    { label: t("analytics.lifetimeSpent"), value: `${formatUzs(history?.total_spent_lifetime || 0)} UZS` },
    { label: t("analytics.avgTransaction"), value: `${formatUzs(history?.average_transaction || 0)} UZS` },
    { label: t("analytics.totalTransactions"), value: `${history?.total_transaction || 0}` },
  ], [history, t]);

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
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{t("analytics.title")}</h1>
          <p className="text-muted-foreground">{t("analytics.subtitle")}</p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {loadingSummary && !history ? (
            <>
              <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
              <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
              <div className="h-[110px] rounded-xl bg-muted animate-pulse" />
            </>
          ) : summary.map((item) => (
            <Card key={item.label} className="shadow-sm">
              <CardHeader className="space-y-1">
                <CardDescription>{item.label}</CardDescription>
                <CardTitle className="text-2xl">{item.value}</CardTitle>
              </CardHeader>
            </Card>
          ))}
        </div>

        <Card className="shadow-sm">
          <CardHeader className="space-y-1">
            <CardTitle className="text-base">{t("analytics.filtersTitle")}</CardTitle>
            <CardDescription>{t("analytics.filtersDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <p className="text-sm font-medium">{t("analytics.quickPresets")}</p>
              <p className="text-xs text-muted-foreground">{t("analytics.quickPresetsDesc")}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <Button key={p.key} variant={isPresetActive(p) ? "default" : "outline"} onClick={() => applyPreset(p)} className="h-9 w-[72px]">
                  {p.label}
                </Button>
              ))}
            </div>

            <div className="space-y-1">
              <p className="text-sm font-medium">{t("analytics.customRange")}</p>
              <p className="text-xs text-muted-foreground">{t("analytics.customRangeDesc")}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_auto] md:items-center">
              <Input type="date" value={startInput} onChange={(e) => { setStartInput(e.target.value); setHint(""); }} min={MIN_ANALYTICS_DATE} max={todayISO} />
              <span className="text-muted-foreground text-sm">{t("analytics.to")}</span>
              <Input type="date" value={endInput} onChange={(e) => { setEndInput(e.target.value); setHint(""); }} min={startInput && startInput > MIN_ANALYTICS_DATE ? startInput : MIN_ANALYTICS_DATE} max={todayISO} />
              <Button className="h-9" onClick={applyCustom} disabled={!inputsStatus.ok} title={!inputsStatus.ok ? inputsStatus.message : t("analytics.applyDateRange")}>
                {t("analytics.apply")}
              </Button>
              <Button className="h-9" variant="outline" onClick={resetAll}>{t("analytics.reset")}</Button>
            </div>

            <div className="flex flex-col gap-1">
              <p className="text-sm text-muted-foreground">{t("analytics.range")}: <span className="font-medium text-foreground">{rangeLabel}</span></p>
              <p className="text-xs text-muted-foreground">{t("analytics.activeMode")}: {range.mode === "days" ? t("analytics.modePreset") : t("analytics.modeCustom")}.</p>
              {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6">
          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>{t("analytics.dailyTrend")}</CardTitle>
              <CardDescription>{rangeLabel}</CardDescription>
            </CardHeader>
            <CardContent className="h-[300px]">
              {loadingCharts && trendChartData.length === 0 ? (
                <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
              ) : trendChartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("analytics.noTrendData")}</p>
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
                    <XAxis dataKey="date" tickFormatter={(value) => formatLongDate(value, chartLocale, i18n.language)} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} interval="preserveStartEnd" minTickGap={28} />
                    <YAxis tickFormatter={(value) => formatCompactUZS(value)} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} width={60} />
                    <Tooltip formatter={(value) => [`${formatUzs(value)} UZS`, t("analytics.amount")]} labelFormatter={(label) => `${t("analytics.date")}: ${formatLongDate(label, chartLocale, i18n.language)}`} contentStyle={{ borderRadius: 10, border: "1px solid hsl(var(--border))", background: "hsl(var(--background))" }} />
                    <Area type="monotone" dataKey="amount" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#analyticsTrendFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader>
              <CardTitle>{t("analytics.categoryBreakdown")}</CardTitle>
              <CardDescription>{rangeLabel}</CardDescription>
            </CardHeader>
            <CardContent className="h-[340px]">
              {loadingCharts && categoryChartData.length === 0 ? (
                <div className="h-full w-full animate-pulse rounded-lg bg-muted" />
              ) : categoryChartData.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("analytics.noCategoryData")}</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={categoryChartData} layout="vertical" margin={{ top: 10, right: 16, left: 40, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="4 4" className="stroke-muted" />
                    <YAxis
                      type="category"
                      dataKey="category"
                      tickFormatter={(value) => t(`categories.${value}`, { defaultValue: value })}
                      tick={{ fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      width={120}
                    />
                    <XAxis type="number" tickFormatter={(value) => formatCompactUZS(value)} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      cursor={{ fill: "hsl(var(--muted))", opacity: 0.25 }}
                      formatter={(value) => [`${formatUzs(value)} UZS`, t("analytics.total")]}
                      labelFormatter={(label) => `${t("analytics.category")}: ${t(`categories.${label}`, { defaultValue: label })}`}
                      contentStyle={{ borderRadius: 10, border: "1px solid hsl(var(--border))", background: "hsl(var(--background))" }}
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
