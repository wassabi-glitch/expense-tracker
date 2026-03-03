import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { Car, Gamepad2, Home, Trash2, Utensils, Wrench, Circle, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  createBudget,
  deleteBudget,
  getBudgets,
  getThisMonthStats,
  updateBudget,
  getCategories,
} from "@/lib/api";
import { budgetCreateFormSchema, budgetDeleteFormSchema, budgetUpdateFormSchema, MAX_BUDGET_AMOUNT } from "./budgetSchemas";
import { localizeApiError } from "@/lib/errorMessages";
import { categoryIconMap } from "@/lib/category";
import { formatUzs, formatCompactUzs, formatAmountInput, formatMonthYear, getFallbackMonthsLong, getDateLocale } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";

export default function Budgets() {
  const { t, i18n } = useTranslation();
  const today = new Date();
  const currentYear = today.getFullYear();
  const currentMonth = today.getMonth() + 1;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);

  const [addOpen, setAddOpen] = useState(false);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [isAddingBudget, setIsAddingBudget] = useState(false);
  const [isUpdatingBudget, setIsUpdatingBudget] = useState(false);
  const [isDeletingBudget, setIsDeletingBudget] = useState(false);
  const [animateProgress, setAnimateProgress] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  const showHistory = searchParams.get("history") === "true";
  const filterCategory = searchParams.get("category") || "all";
  const filterStatus = searchParams.get("status") || "all";
  const filterMonth = searchParams.get("month") || "all";
  const sortBy = searchParams.get("sort") || "newest";

  const updateSearchParam = (key, value, defaultValue = "all") => {
    setSearchParams(prev => {
      if (value === defaultValue || !value) {
        prev.delete(key);
      } else {
        prev.set(key, value);
      }
      return prev;
    }, { replace: true });
  };

  const setShowHistory = (updater) => {
    setSearchParams(prev => {
      const current = prev.get("history") === "true";
      const next = typeof updater === "function" ? updater(current) : updater;
      if (next) {
        prev.set("history", "true");
      } else {
        prev.delete("history");
        prev.delete("month");
      }
      return prev;
    }, { replace: true });
  };

  const setFilterCategory = (val) => updateSearchParam("category", val);
  const setFilterStatus = (val) => updateSearchParam("status", val);
  const setFilterMonth = (val) => updateSearchParam("month", val);
  const setSortBy = (val) => updateSearchParam("sort", val, "newest");

  const [selectedBudget, setSelectedBudget] = useState(null);
  const [newLimit, setNewLimit] = useState("");
  const [addCategory, setAddCategory] = useState("");
  const [addLimit, setAddLimit] = useState("");
  const [addBudgetYear, setAddBudgetYear] = useState(currentYear);
  const [addBudgetMonth, setAddBudgetMonth] = useState(currentMonth);
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
  const categorySortLocale = appLang.startsWith("uz")
    ? "uz-UZ"
    : appLang.startsWith("ru")
      ? "ru-RU"
      : "en-US";

  const tCategory = useCallback((name) => t(`categories.${name}`, { defaultValue: name }), [t]);
  const compareLocalizedCategory = useCallback((leftCategory, rightCategory) =>
    tCategory(leftCategory).localeCompare(tCategory(rightCategory), categorySortLocale, { sensitivity: "base" }),
    [tCategory, categorySortLocale]
  );
  const loadBudgetsPage = useCallback(async ({ showSpinner = true } = {}) => {
    if (showSpinner) setLoading(true);
    setAnimateProgress(false);
    setError("");
    try {
      const [budgetRows, stats, categoryList] = await Promise.all([
        getBudgets(),
        getThisMonthStats(),
        getCategories(),
      ]);

      setCategories(categoryList || []);
      const currentMonthStatusByCategory = new Map(
        (stats?.category_breakdown || []).map((item) => [
          item.category,
          {
            total: Number(item.total || 0),
            remaining: Number(item.remaining || 0),
            percentageUsed: Number(item.percentage_used || 0),
            budgetStatus: String(item.budget_status || ""),
          },
        ])
      );
      const merged = (budgetRows || []).map((b) => ({
        isCurrentMonth: Number(b.budget_year) === currentYear && Number(b.budget_month) === currentMonth,
        id: b.id,
        category: b.category,
        budgetYear: Number(b.budget_year),
        budgetMonth: Number(b.budget_month),
        limit: Number(b.monthly_limit || 0),
        spent: Number(b.spent || 0),
        remaining: Math.max(0, Number(b.monthly_limit || 0) - Number(b.spent || 0)),
        backendStatus:
          Number(b.budget_year) === currentYear && Number(b.budget_month) === currentMonth
            ? (currentMonthStatusByCategory.get(b.category)?.budgetStatus ?? "")
            : "",
      }));
      setBudgets(merged);
      requestAnimationFrame(() => setAnimateProgress(true));
    } catch (e) {
      setError(localizeApiError(e?.message, t) || t("budgets.loadFailed"));
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, [currentYear, currentMonth, t]);

  useEffect(() => {
    loadBudgetsPage();
  }, [loadBudgetsPage]);

  const sortedBudgets = useMemo(
    () =>
      [...budgets].sort((a, b) =>
        b.budgetYear - a.budgetYear ||
        b.budgetMonth - a.budgetMonth ||
        compareLocalizedCategory(a.category, b.category)
      ),
    [budgets, compareLocalizedCategory]
  );
  const visibleBudgets = useMemo(
    () =>
      showHistory
        ? sortedBudgets
        : sortedBudgets.filter((b) => b.budgetYear === currentYear && b.budgetMonth === currentMonth),
    [showHistory, sortedBudgets, currentYear, currentMonth]
  );

  const maxBudgetAmountDigits = String(MAX_BUDGET_AMOUNT).length;
  const maxBudgetAmountInputLength = formatUzs(MAX_BUDGET_AMOUNT).length;
  const monthLocale = getDateLocale(appLang);
  const fallbackMonthNames = getFallbackMonthsLong(appLang);

  const formatBudgetMonth = useCallback((year, month) => formatMonthYear(year, month, appLang), [appLang]);

  const formatBudgetAmountInput = (raw) => formatAmountInput(raw, maxBudgetAmountDigits);
  const budgetYearOptions = useMemo(() => {
    const minYear = 2020;
    const maxYear = currentYear + 5;
    return Array.from({ length: maxYear - minYear + 1 }, (_, i) => maxYear - i);
  }, [currentYear]);

  const budgetMonthOptions = useMemo(
    () =>
      Array.from({ length: 12 }, (_, i) => {
        const month = i + 1;
        return {
          value: month,
          label: (() => {
            const formatted = new Intl.DateTimeFormat(monthLocale, { month: "long" }).format(
              new Date(2024, i, 1)
            );
            return /M\d{2}/.test(formatted) ? fallbackMonthNames[i] : formatted;
          })(),
        };
      }),
    [monthLocale, fallbackMonthNames]
  );
  const visibleMonthOptions = useMemo(() => {
    const maxMonthForYear = addBudgetYear === currentYear + 5 ? currentMonth : 12;
    return budgetMonthOptions.filter((m) => m.value <= maxMonthForYear);
  }, [budgetMonthOptions, addBudgetYear, currentYear, currentMonth]);
  const tZodError = (parsed) => {
    const key = parsed?.error?.issues?.[0]?.message;
    return key ? t(key, { defaultValue: key }) : t("common.error", { defaultValue: "Invalid input" });
  };

  const getBudgetActionErrorMessage = (e) => {
    if (e?.status === 429) {
      const wait = Number(e?.retryAfterSeconds || 0);
      if (Number.isFinite(wait) && wait > 0) {
        return t("budgets.tooManyWait", { seconds: wait });
      }
      return t("budgets.tooManySoon");
    }
    return localizeApiError(e?.message, t) || t("budgets.requestFailed");
  };
  const selectTriggerClass =
    "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
  const selectContentClass =
    "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";
  const inputBaseClass =
    "dark:bg-input/30 border-input h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm";
  const deriveProgressStatus = (backendStatus, percent) => {
    if (backendStatus === "Over Limit") return "danger";
    if (backendStatus === "High Risk") return "highRisk";
    if (backendStatus === "Warning") return "warning";
    if (backendStatus === "On Track") return "healthy";
    if (percent >= 100) return "danger";
    if (percent >= 90) return "highRisk";
    if (percent >= 70) return "warning";
    return "healthy";
  };
  const budgetsWithDerived = useMemo(
    () =>
      visibleBudgets.map((b) => {
        const percent = b.limit > 0 ? Math.min(Math.round((b.spent / b.limit) * 100), 100) : 0;
        return {
          ...b,
          percent,
          progressStatus: deriveProgressStatus(b.backendStatus, percent),
          monthKey: `${b.budgetYear}-${String(b.budgetMonth).padStart(2, "0")}`,
        };
      }),
    [visibleBudgets]
  );
  const monthFilterOptions = useMemo(() => {
    const source = showHistory ? sortedBudgets : visibleBudgets;
    const seen = new Set();
    return source
      .map((b) => ({
        value: `${b.budgetYear}-${String(b.budgetMonth).padStart(2, "0")}`,
        label: formatBudgetMonth(b.budgetYear, b.budgetMonth),
      }))
      .filter((item) => {
        if (seen.has(item.value)) return false;
        seen.add(item.value);
        return true;
      });
  }, [showHistory, sortedBudgets, visibleBudgets, formatBudgetMonth]);
  const localizedCategoryOptions = useMemo(
    () => [...categories].sort((a, b) => compareLocalizedCategory(a, b)),
    [categories, compareLocalizedCategory]
  );
  const filteredBudgets = useMemo(() => {
    let rows = budgetsWithDerived;
    if (filterCategory !== "all") {
      rows = rows.filter((b) => b.category === filterCategory);
    }
    if (filterStatus !== "all") {
      rows = rows.filter((b) => b.progressStatus === filterStatus);
    }
    if (filterMonth !== "all") {
      rows = rows.filter((b) => b.monthKey === filterMonth);
    }
    const sorted = [...rows];
    sorted.sort((a, b) => {
      switch (sortBy) {
        case "oldest":
          return a.budgetYear - b.budgetYear || a.budgetMonth - b.budgetMonth || compareLocalizedCategory(a.category, b.category);
        case "percentDesc":
          return b.percent - a.percent || compareLocalizedCategory(a.category, b.category);
        case "percentAsc":
          return a.percent - b.percent || compareLocalizedCategory(a.category, b.category);
        case "remainingDesc":
          return b.remaining - a.remaining || compareLocalizedCategory(a.category, b.category);
        case "remainingAsc":
          return a.remaining - b.remaining || compareLocalizedCategory(a.category, b.category);
        case "limitDesc":
          return b.limit - a.limit || compareLocalizedCategory(a.category, b.category);
        case "limitAsc":
          return a.limit - b.limit || compareLocalizedCategory(a.category, b.category);
        case "category":
          return compareLocalizedCategory(a.category, b.category);
        default:
          return b.budgetYear - a.budgetYear || b.budgetMonth - a.budgetMonth || compareLocalizedCategory(a.category, b.category);
      }
    });
    return sorted;
  }, [budgetsWithDerived, filterCategory, filterStatus, filterMonth, sortBy, compareLocalizedCategory]);
  const resetBudgetFilters = () => {
    setSearchParams(prev => {
      prev.delete("category");
      prev.delete("status");
      prev.delete("month");
      prev.delete("sort");
      return prev;
    }, { replace: true });
  };

  const addBudgetFormParsed = useMemo(() => {
    const budgetMonthValue = `${addBudgetYear}-${String(addBudgetMonth).padStart(2, "0")}`;
    return budgetCreateFormSchema.safeParse({
      category: addCategory,
      monthly_limit: addLimit,
      budget_month_value: budgetMonthValue,
    });
  }, [addBudgetYear, addBudgetMonth, addCategory, addLimit]);
  const canSubmitAddBudget = addBudgetFormParsed.success && !isAddingBudget;


  const updateBudgetFormParsed = useMemo(
    () =>
      budgetUpdateFormSchema.safeParse({
        monthly_limit: newLimit,
        category: selectedBudget?.category ?? "",
        budgetYear: selectedBudget?.budgetYear,
        budgetMonth: selectedBudget?.budgetMonth,
      }),
    [newLimit, selectedBudget]
  );
  const canSubmitUpdateBudget = updateBudgetFormParsed.success && !isUpdatingBudget;

  const openUpdate = (budget) => {
    setActionError("");
    setSelectedBudget(budget);
    setNewLimit(formatBudgetAmountInput(String(budget.limit)));
    setUpdateOpen(true);
  };

  const openDelete = (budget) => {
    setActionError("");
    setSelectedBudget(budget);
    setDeleteOpen(true);
  };

  const openAdd = () => {
    setActionError("");
    setAddCategory("");
    setAddLimit("");
    setAddBudgetYear(currentYear);
    setAddBudgetMonth(currentMonth);
    setAddOpen(true);
  };

  async function handleAddBudget() {
    if (isAddingBudget) return;
    setActionError("");
    const budgetMonthValue = `${addBudgetYear}-${String(addBudgetMonth).padStart(2, "0")}`;
    const parsedForm = budgetCreateFormSchema.safeParse({
      category: addCategory,
      monthly_limit: addLimit,
      budget_month_value: budgetMonthValue,
    });
    if (!parsedForm.success) {
      return setActionError(tZodError(parsedForm));
    }
    const [yearStr, monthStr] = parsedForm.data.budget_month_value.split("-");
    const budgetYear = Number(yearStr);
    const budgetMonth = Number(monthStr);
    try {
      setIsAddingBudget(true);
      await createBudget(parsedForm.data.category, parsedForm.data.monthly_limit, budgetYear, budgetMonth);
      setAddOpen(false);
      await loadBudgetsPage({ showSpinner: false });
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    } finally {
      setIsAddingBudget(false);
    }
  }

  async function handleUpdateBudget() {
    if (isUpdatingBudget) return;
    setActionError("");
    const parsedForm = budgetUpdateFormSchema.safeParse({
      monthly_limit: newLimit,
      category: selectedBudget?.category ?? "",
      budgetYear: selectedBudget?.budgetYear,
      budgetMonth: selectedBudget?.budgetMonth,
    });
    if (!parsedForm.success) {
      return setActionError(tZodError(parsedForm));
    }
    try {
      setIsUpdatingBudget(true);
      await updateBudget(
        parsedForm.data.category,
        parsedForm.data.monthly_limit,
        parsedForm.data.budgetYear,
        parsedForm.data.budgetMonth
      );
      setUpdateOpen(false);
      await loadBudgetsPage({ showSpinner: false });
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    } finally {
      setIsUpdatingBudget(false);
    }
  }

  async function handleDeleteBudget() {
    if (isDeletingBudget) return;
    setActionError("");
    const parsedForm = budgetDeleteFormSchema.safeParse({
      category: selectedBudget?.category ?? "",
      budgetYear: selectedBudget?.budgetYear,
      budgetMonth: selectedBudget?.budgetMonth,
    });
    if (!parsedForm.success) {
      return setActionError(tZodError(parsedForm));
    }
    try {
      setIsDeletingBudget(true);
      await deleteBudget(parsedForm.data.category, parsedForm.data.budgetYear, parsedForm.data.budgetMonth);
      setDeleteOpen(false);
      await loadBudgetsPage({ showSpinner: false });
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    } finally {
      setIsDeletingBudget(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <PageHeader title={t("budgets.title")} description={t("budgets.subtitle")}>
          <Button variant="outline" onClick={() => setShowHistory((v) => !v)}>
            {showHistory ? t("budgets.hideHistory") : t("budgets.showHistory")}
          </Button>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90" onClick={openAdd}>
            <Plus className="mr-2 h-4 w-4" /> {t("budgets.addBudget")}
          </Button>
        </PageHeader>
        {!loading && !error && (
          <Card className="shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t("budgets.filtersTitle")}</CardTitle>
              <CardDescription>{t("budgets.filtersDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                <Select value={filterCategory} onValueChange={setFilterCategory}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="all">{t("budgets.filterCategoryAll")}</SelectItem>
                    {localizedCategoryOptions.map((c) => (
                      <SelectItem key={c} value={c}>
                        {tCategory(c)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="all">{t("budgets.filterStatusAll")}</SelectItem>
                    <SelectItem value="healthy">{t("budgets.status.onTrack")}</SelectItem>
                    <SelectItem value="warning">{t("budgets.status.closeToLimit")}</SelectItem>
                    <SelectItem value="highRisk">{t("budgets.status.highRisk")}</SelectItem>
                    <SelectItem value="danger">{t("budgets.status.overBudget")}</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterMonth} onValueChange={setFilterMonth} disabled={!showHistory}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="all">{t("budgets.filterMonthAll")}</SelectItem>
                    {monthFilterOptions.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="newest">{t("budgets.sort.newest")}</SelectItem>
                    <SelectItem value="oldest">{t("budgets.sort.oldest")}</SelectItem>
                    <SelectItem value="percentDesc">{t("budgets.sort.percentDesc")}</SelectItem>
                    <SelectItem value="percentAsc">{t("budgets.sort.percentAsc")}</SelectItem>
                    <SelectItem value="remainingDesc">{t("budgets.sort.remainingDesc")}</SelectItem>
                    <SelectItem value="remainingAsc">{t("budgets.sort.remainingAsc")}</SelectItem>
                    <SelectItem value="limitDesc">{t("budgets.sort.limitDesc")}</SelectItem>
                    <SelectItem value="limitAsc">{t("budgets.sort.limitAsc")}</SelectItem>
                    <SelectItem value="category">{t("budgets.sort.category")}</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline" onClick={resetBudgetFilters}>
                  {t("budgets.resetFilters")}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
        {loading && (
          <div className="flex min-h-30 items-center justify-center">
            <LoadingSpinner className="h-8 w-8" />
          </div>
        )}

        {!loading && !error && (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredBudgets.map((b) => {
              const percent = b.percent;
              const progressStatus = b.progressStatus;
              const progressTrackClass =
                progressStatus === "danger"
                  ? "bg-destructive/20 rounded-full"
                  : progressStatus === "highRisk"
                    ? "bg-orange-500/20 dark:bg-orange-400/20 rounded-full"
                    : progressStatus === "warning"
                      ? "bg-yellow-500/20 dark:bg-yellow-400/20 rounded-full"
                      : "bg-primary/20 rounded-full";
              const progressIndicatorClass =
                progressStatus === "danger"
                  ? "bg-destructive shadow-[0_0_10px_rgba(239,68,68,0.45)] rounded-full duration-700 ease-out"
                  : progressStatus === "highRisk"
                    ? "bg-orange-500 dark:bg-orange-400 shadow-[0_0_10px_rgba(249,115,22,0.35)] dark:shadow-[0_0_10px_rgba(251,146,60,0.35)] rounded-full duration-700 ease-out"
                    : progressStatus === "warning"
                      ? "bg-yellow-500 dark:bg-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.35)] dark:shadow-[0_0_10px_rgba(250,204,21,0.35)] rounded-full duration-700 ease-out"
                      : "bg-primary shadow-[0_0_10px_rgba(34,197,94,0.35)] rounded-full duration-700 ease-out";
              const statusBadgeClass =
                progressStatus === "danger"
                  ? "border border-destructive/30 bg-destructive/15 text-destructive dark:text-red-400"
                  : progressStatus === "highRisk"
                    ? "border border-orange-500/35 bg-orange-500/15 text-orange-700 dark:text-orange-400"
                    : progressStatus === "warning"
                      ? "border border-yellow-500/35 bg-yellow-500/15 text-yellow-700 dark:text-yellow-400"
                      : "border border-primary/35 bg-primary/15 text-primary dark:text-primary";
              const _iconColorClass =
                progressStatus === "danger"
                  ? "text-destructive dark:text-red-400"
                  : progressStatus === "highRisk"
                    ? "text-orange-600 dark:text-orange-400"
                    : progressStatus === "warning"
                      ? "text-yellow-600 dark:text-yellow-400"
                      : "text-primary dark:text-primary";
              const statusLabel =
                progressStatus === "danger"
                  ? t("budgets.status.overBudget")
                  : progressStatus === "highRisk"
                    ? t("budgets.status.highRisk")
                    : progressStatus === "warning"
                      ? t("budgets.status.closeToLimit")
                      : t("budgets.status.onTrack");
              const deltaAmount = Math.max(0, b.spent - b.limit);
              const useCompactAmounts = Math.max(b.spent, b.limit) >= 1_000_000_000;
              const spentLabel = useCompactAmounts ? formatCompactUzs(b.spent) : formatUzs(b.spent);
              const limitLabel = useCompactAmounts ? formatCompactUzs(b.limit) : formatUzs(b.limit);
              const usedOfLabel = t("budgets.usedOf", { spent: spentLabel, limit: limitLabel });
              return (
                <Card
                  key={b.id}
                  className={`group shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md ${b.isCurrentMonth ? "opacity-100" : "opacity-65 hover:opacity-100"}`}
                // "opacity-45 grayscale-[0.5] hover:opacity-100 hover:grayscale-0"
                >
                  <CardHeader className="space-y-3 pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                        {(() => {
                          const CategoryIcon = categoryIconMap[b.category] || Circle;
                          return <CategoryIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />;
                        })()}
                        <span>{tCategory(b.category)}</span>
                      </CardTitle>
                      <span
                        className={`inline-flex min-h-8 min-w-[86px] max-w-[96px] items-center justify-center rounded-full px-2 py-1 text-center text-[11px] font-medium leading-tight whitespace-normal sm:text-xs ${statusBadgeClass}`}
                      >
                        {statusLabel}
                      </span>
                    </div>
                    <CardDescription className="space-y-2">
                      <span className="block text-sm text-muted-foreground">{formatBudgetMonth(b.budgetYear, b.budgetMonth)}</span>
                      <span
                        className="block w-full overflow-hidden text-ellipsis whitespace-nowrap tabular-nums text-sm font-medium text-foreground sm:text-base"
                        title={usedOfLabel}
                      >
                        {usedOfLabel}
                      </span>
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5 pt-1">
                    <div className="flex items-center justify-between text-sm text-muted-foreground tabular-nums">
                      <span>{t("budgets.percentUsed", { percent })}</span>
                      <span>
                        {b.spent > b.limit
                          ? t("budgets.overBy", { amount: formatUzs(deltaAmount) })
                          : t("budgets.remaining", { amount: formatUzs(b.remaining) })}
                      </span>
                    </div>
                    <Progress
                      value={animateProgress ? percent : 0}
                      className="h-2"
                      trackClassName={progressTrackClass}
                      indicatorClassName={progressIndicatorClass}
                    />
                    <div className="flex gap-2 transition-opacity duration-200 md:opacity-85 md:group-hover:opacity-100">
                      <Button variant="outline" size="sm" className="flex-1" onClick={() => openUpdate(b)}>{t("budgets.updateLimit")}</Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="flex-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => openDelete(b)}
                      >
                        <Trash2 className="h-4 w-4" />
                        {t("budgets.delete")}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {!loading && !error && filteredBudgets.length === 0 && (
          <EmptyState
            title={t("budgets.emptyFilteredTitle")}
            description={t("budgets.emptyFilteredDesc")}
            className="my-10"
          />
        )}
      </div>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="py-16">
          <DialogHeader className="space-y-3 pb-2">
            <DialogTitle className="text-3xl font-bold tracking-tight">{t("budgets.addDialogTitle")}</DialogTitle>
            <DialogDescription>{t("budgets.addDialogDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            <div className="space-y-3">
              <label className="text-sm font-medium">{t("budgets.budgetMonthLabel")}</label>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-xs font-normal text-muted-foreground">{t("budgets.yearLabel")}</label>
                  <Select
                    value={String(addBudgetYear)}
                    onValueChange={(value) => {
                      const nextYear = Number(value);
                      setAddBudgetYear(nextYear);
                      const maxMonthForYear = nextYear === currentYear + 5 ? currentMonth : 12;
                      setAddBudgetMonth((prev) => Math.min(prev, maxMonthForYear));
                    }}
                  >
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent
                      className={selectContentClass}
                      position="popper"
                      side="bottom"
                    >
                      {budgetYearOptions.map((year) => (
                        <SelectItem key={year} value={String(year)}>
                          {year}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-normal text-muted-foreground">{t("budgets.monthLabel")}</label>
                  <Select value={String(addBudgetMonth)} onValueChange={(value) => setAddBudgetMonth(Number(value))}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent
                      className={selectContentClass}
                      position="popper"
                      side="bottom"
                    >
                      {visibleMonthOptions.map((option) => (
                        <SelectItem key={option.value} value={String(option.value)}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <label className="text-sm font-medium">{t("expenses.category")}</label>
              <Select value={addCategory || undefined} onValueChange={setAddCategory}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue placeholder={t("budgets.selectCategory")} />
                </SelectTrigger>
                <SelectContent
                  className={selectContentClass}
                  position="popper"
                  side="bottom"
                >
                  {localizedCategoryOptions.map((c) => (
                    <SelectItem key={c} value={c}>
                      {tCategory(c)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-3">
              <label className="text-sm font-medium">{t("budgets.monthlyLimit")}</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="off"
                maxLength={maxBudgetAmountInputLength}
                className={inputBaseClass}
                value={addLimit}
                onChange={(e) => setAddLimit(formatBudgetAmountInput(e.target.value))}
              />
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={isAddingBudget}>{t("common.cancel")}</Button>
            <Button
              onClick={handleAddBudget}
              disabled={!canSubmitAddBudget}
              className="relative min-w-[96px] disabled:pointer-events-auto disabled:cursor-not-allowed"
            >
              {isAddingBudget ? (
                <>
                  <span className="invisible">{t("expenses.add")}</span>
                  <span className="absolute inset-0 flex items-center justify-center">
                    <span
                      aria-label="Loading"
                      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                    />
                  </span>
                </>
              ) : (
                t("expenses.add")
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={updateOpen} onOpenChange={setUpdateOpen}>
        <DialogContent className="pt-8">
          <DialogHeader className="space-y-3 pb-2">
            <DialogTitle>{t("budgets.updateDialogTitle")}</DialogTitle>
            <DialogDescription>
              {selectedBudget
                ? `${t("budgets.updateDialogDesc", { category: tCategory(selectedBudget.category) })} (${formatBudgetMonth(selectedBudget.budgetYear, selectedBudget.budgetMonth)})`
                : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <label className="text-sm font-medium">{t("budgets.newLimit")}</label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="off"
              maxLength={maxBudgetAmountInputLength}
              className={inputBaseClass}
              value={newLimit}
              onChange={(e) => setNewLimit(formatBudgetAmountInput(e.target.value))}
            />
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUpdateOpen(false)} disabled={isUpdatingBudget}>{t("common.cancel")}</Button>
            <Button
              onClick={handleUpdateBudget}
              disabled={!canSubmitUpdateBudget}
              className={`relative min-w-24 ${!canSubmitUpdateBudget ? "cursor-not-allowed opacity-60" : ""}`}
            >
              {isUpdatingBudget ? (
                <>
                  <span className="invisible">{t("common.save")}</span>
                  <span className="absolute inset-0 flex items-center justify-center">
                    <span
                      aria-label="Loading"
                      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                    />
                  </span>
                </>
              ) : (
                t("common.save")
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={t("budgets.deleteDialogTitle")}
        description={
          selectedBudget
            ? `${t("budgets.deleteDialogDesc", { category: tCategory(selectedBudget.category) })} (${formatBudgetMonth(selectedBudget.budgetYear, selectedBudget.budgetMonth)})`
            : ""
        }
        onConfirm={handleDeleteBudget}
        confirmText={t("budgets.delete")}
        cancelText={t("common.cancel")}
        isConfirming={isDeletingBudget}
        error={actionError}
      />
    </div>
  );
}
