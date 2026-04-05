import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import { useExportCategoriesQuery } from "./hooks/useExportCategoriesQuery";
import { useExportMutation } from "./hooks/useExportMutation";

const MIN_EXPENSE_DATE = "2020-01-01";
const ALL_CATEGORIES_SELECT = "__all_categories__";
const EMPTY_ARRAY = [];

export default function ExportPage() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [error, setError] = useState("");

  const [startDate, setStartDate] = useState(() => searchParams.get("start_date") || "");
  const [endDate, setEndDate] = useState(() => searchParams.get("end_date") || "");
  const [category, setCategory] = useState(() => searchParams.get("category") || "");
  const [sort, setSort] = useState(() => (searchParams.get("sort") === "oldest" ? "oldest" : "newest"));
  const [retrySeconds, setRetrySeconds] = useState(0);

  const todayISO = useMemo(() => toISODateInTimeZone(), []);
  const tCategory = (name) => t(`categories.${name}`, { defaultValue: name });
  const selectTriggerClass =
    "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
  const selectContentClass =
    "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";

  const categoriesQuery = useExportCategoriesQuery();
  const categories = categoriesQuery.data || EMPTY_ARRAY;
  const loading = categoriesQuery.isLoading;
  const exportMutation = useExportMutation();
  const exporting = exportMutation.isPending;

  useEffect(() => {
    if (retrySeconds <= 0) return;
    const interval = setInterval(() => {
      setRetrySeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [retrySeconds]);

  const metaError = categoriesQuery.error
    ? localizeApiError(categoriesQuery.error?.message, t) || categoriesQuery.error?.message || t("export.loadFailed")
    : "";
  const visibleActionError = retrySeconds === 0 && error === t("export.too_many_requests") ? "" : error;
  const displayError = visibleActionError || metaError;

  useEffect(() => {
    const next = new URLSearchParams();
    if (startDate) next.set("start_date", startDate);
    if (endDate) next.set("end_date", endDate);
    if (category) next.set("category", category);
    if (sort !== "newest") next.set("sort", sort);
    setSearchParams(next, { replace: true });
  }, [startDate, endDate, category, sort, setSearchParams]);

  const filterError = useMemo(() => {
    if (startDate && startDate < MIN_EXPENSE_DATE) return t("export.startTooEarly");
    if (endDate && endDate < MIN_EXPENSE_DATE) return t("export.endTooEarly");
    if (startDate && endDate && startDate > endDate) return t("export.startAfterEnd");
    return "";
  }, [startDate, endDate, t]);

  const handleExport = async () => {
    setError("");
    if (filterError) return setError(filterError);
    try {
      const { blob, filename } = await exportMutation.mutateAsync({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        category: category || undefined,
        sort,
        lang: i18n.language,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      if (e.status === 429) {
        const waitTime = e.retryAfterSeconds || 60;
        setRetrySeconds(waitTime);
        setError(t("export.too_many_requests"));
      } else {
        setError(localizeApiError(e?.message, t) || e.message || t("export.exportFailed"));
      }
    }
  };

  const handleReset = () => {
    setError("");
    setStartDate("");
    setEndDate("");
    setCategory("");
    setSort("newest");
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="w-full px-page py-8 space-y-6">
        <div className="pl-card sm:pl-0 sm:px-3 md:px-0">
          <h1 className="text-mobile-h1 sm:text-3xl font-bold tracking-tight text-foreground">{t("export.title")}</h1>
          <p className="text-mobile-label sm:text-base text-muted-foreground mt-0.5 sm:mt-1">{t("export.subtitle")}</p>
        </div>

        {displayError && <p className="text-sm text-red-600">{displayError}</p>}

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("export.cardTitle")}</CardTitle>
            <CardDescription>{t("export.cardDesc")}</CardDescription>
          </CardHeader>
          {loading ? (
            <CardContent>
              <div className="flex min-h-30 items-center justify-center">
                <LoadingSpinner className="h-8 w-8" />
              </div>
            </CardContent>
          ) : (
            <>
              <CardContent className="grid gap-3 md:grid-cols-4">
                <Input type="date" min={MIN_EXPENSE_DATE} max={todayISO} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                <Input type="date" min={MIN_EXPENSE_DATE} max={todayISO} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                <Select
                  value={category || ALL_CATEGORIES_SELECT}
                  onValueChange={(value) => setCategory(value === ALL_CATEGORIES_SELECT ? "" : value)}
                >
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value={ALL_CATEGORIES_SELECT}>{t("export.allCategories")}</SelectItem>
                    {categories.map((c) => (
                      <SelectItem key={c} value={c}>
                        {tCategory(c)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={sort} onValueChange={setSort}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="newest">{t("export.newestFirst")}</SelectItem>
                    <SelectItem value="oldest">{t("export.oldestFirst")}</SelectItem>
                  </SelectContent>
                </Select>
              </CardContent>
              <CardContent className="flex items-center gap-3">
                <span className={retrySeconds > 0 ? "cursor-not-allowed" : ""}>
                  <Button
                    className="min-w-[140px] bg-primary text-primary-foreground hover:bg-primary/90"
                    onClick={handleExport}
                    disabled={exporting || !!filterError || retrySeconds > 0}
                  >
                    {exporting ? (
                      <LoadingSpinner className="h-4 w-4" />
                    ) : (
                      <>
                        <Download className="mr-2 h-4 w-4" /> {t("export.exportCsv")}
                      </>
                    )}
                  </Button>
                </span>
                <Button variant="outline" onClick={handleReset} disabled={exporting}>
                  {t("common.reset")}
                </Button>
                {filterError && <p className="text-sm text-red-600">{filterError}</p>}
              </CardContent>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}



