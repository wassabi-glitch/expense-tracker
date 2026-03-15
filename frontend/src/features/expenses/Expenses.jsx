import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Plus, Search, ChevronLeft, ChevronRight, Inbox, Trash2, MoreHorizontal, Pencil, FileText } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateExpenseMutation,
  useDeleteExpenseMutation,
  useUpdateExpenseMutation,
} from "./hooks/useExpenseMutations";
import { useExpenseCategoriesQuery } from "./hooks/useExpenseCategoriesQuery";
import { useExpensesQuery } from "./hooks/useExpensesQuery";
import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import {
  expenseFormSchema,
  expenseUpdateFormSchema,
  MAX_EXPENSE_AMOUNT,
} from "./expenseSchemas.js";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import RecurringExpenses from "./RecurringExpenses";

const PAGE_SIZE = 15;
const MIN_EXPENSE_DATE = "2020-01-01";
const MAX_EXPENSE_AMOUNT_DIGITS = String(MAX_EXPENSE_AMOUNT).length;
const ALL_CATEGORIES_SELECT = "__all_categories__";
const EMPTY_ARRAY = [];
const MAX_EXPENSES_PER_MONTH = 1000;
const LAST_EXPENSE_CATEGORY_STORAGE_KEY = "expenses.lastUsedCategory";

import { getCategoryBgClass, categoryIconMap, CATEGORIES } from "@/lib/category";
import { Circle } from "lucide-react";
import { formatAmountInput, formatDisplayDate, formatMonthYear } from "@/lib/format";

const parsePageParam = (value) => {
  const raw = String(value ?? "").trim();
  if (!raw) return 1;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
};

const getStoredLastExpenseCategory = () => {
  if (typeof window === "undefined") return "";
  try {
    return window.localStorage.getItem(LAST_EXPENSE_CATEGORY_STORAGE_KEY) || "";
  } catch {
    return "";
  }
};

const setStoredLastExpenseCategory = (category) => {
  if (!category || typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LAST_EXPENSE_CATEGORY_STORAGE_KEY, category);
  } catch {
    // Ignore storage failures and keep the form usable.
  }
};

export default function Expenses() {
  const { t, i18n } = useTranslation();
  const translateValidation = (message) => t(message, { defaultValue: message });
  const [searchParams, setSearchParams] = useSearchParams();
  const [actionError, setActionError] = useState("");

  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [category, setCategory] = useState(() => searchParams.get("category") || "");
  const [startDate, setStartDate] = useState(() => searchParams.get("start_date") || "");
  const [endDate, setEndDate] = useState(() => searchParams.get("end_date") || "");
  const [sort, setSort] = useState(() => searchParams.get("sort") || "newest");
  const todayISO = useMemo(() => toISODateInTimeZone(), []);

  const [page, setPage] = useState(() => parsePageParam(searchParams.get("page")));

  const [recurringCount, setRecurringCount] = useState(0);

  const [addOpen, setAddOpen] = useState(false);
  const VALID_TABS = ["one-time", "recurring"];
  const [activeTab, setActiveTabState] = useState(() => {
    const t = searchParams.get("tab");
    return VALID_TABS.includes(t) ? t : "one-time";
  });
  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (tab === "one-time") next.delete("tab");
      else next.set("tab", tab);
      return next;
    }, { replace: true });
  };
  const recurringAddRef = useRef(null);
  const [addTitle, setAddTitle] = useState("");
  const [addAmount, setAddAmount] = useState("");
  const [addCategory, setAddCategory] = useState("");
  const [addDescription, setAddDescription] = useState("");
  const [addDate, setAddDate] = useState("");
  const [touchedAdd, setTouchedAdd] = useState({});

  const [editOpen, setEditOpen] = useState(false);
  const [editExpense, setEditExpense] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDate, setEditDate] = useState("");
  const [touchedEdit, setTouchedEdit] = useState({});

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [descriptionTarget, setDescriptionTarget] = useState(null);
  const [expenseMenuForId, setExpenseMenuForId] = useState(null);
  const [expenseMenuPosition, setExpenseMenuPosition] = useState(null);

  const tCategory = (name) => t(`categories.${name}`, { defaultValue: name });
  const selectTriggerClass =
    "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
  const selectContentClass =
    "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";
  const appLang = String(i18n.language || i18n.resolvedLanguage || "en").toLowerCase();

  const _formatDisplayDateLocal = (value) => formatDisplayDate(value, appLang);
  const _formatMonthYearLocal = (value) => formatMonthYear(value, appLang);

  const queryParams = useMemo(() => {
    return {
      limit: PAGE_SIZE,
      skip: (page - 1) * PAGE_SIZE,
      search: search.trim() || undefined,
      category: category || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      sort,
    };
  }, [search, category, startDate, endDate, sort, page]);

  const currentMonthCountParams = useMemo(() => ({
    limit: 1,
    skip: 0,
    start_date: `${todayISO.slice(0, 7)}-01`,
    end_date: todayISO,
    sort: "newest",
  }), [todayISO]);

  const dateFilterError = useMemo(() => {
    if (startDate && startDate > todayISO) return t("expenses.startFuture");
    if (endDate && endDate > todayISO) return t("expenses.endFuture");
    if (startDate && endDate && startDate > endDate) return t("expenses.startAfterEnd");
    return "";
  }, [startDate, endDate, todayISO, t]);

  const expensesQuery = useExpensesQuery(queryParams, activeTab === "one-time" && !dateFilterError);
  const currentMonthCountQuery = useExpensesQuery(currentMonthCountParams, activeTab === "one-time");
  const categoriesQuery = useExpenseCategoriesQuery(activeTab === "one-time");

  const categories = categoriesQuery.data || EMPTY_ARRAY;
  const expenses = expensesQuery.data?.items || EMPTY_ARRAY;
  const total = Number(expensesQuery.data?.total || 0);
  const currentMonthExpenseCount = Number(currentMonthCountQuery.data?.total || 0);
  const expenseMonthLimitReached = currentMonthExpenseCount >= MAX_EXPENSES_PER_MONTH;
  const hasNext = expenses.length === PAGE_SIZE;
  const loading = expensesQuery.isLoading || categoriesQuery.isLoading;
  const isFetching = expensesQuery.isFetching || categoriesQuery.isFetching;
  const error = dateFilterError
    ? dateFilterError
    : (expensesQuery.error || categoriesQuery.error)
      ? localizeApiError(expensesQuery.error?.message || categoriesQuery.error?.message, t) ||
      expensesQuery.error?.message ||
      categoriesQuery.error?.message ||
      t("expenses.loadFailed")
      : "";

  const orderedCategories = useMemo(() => {
    const set = new Set(categories);
    const inOrder = CATEGORIES.filter((c) => set.has(c));
    const extras = [...set].filter((c) => !CATEGORIES.includes(c));
    return [...inOrder, ...extras];
  }, [categories]);

  const preferredAddCategory = useMemo(() => {
    const storedCategory = getStoredLastExpenseCategory();
    if (storedCategory && orderedCategories.includes(storedCategory)) return storedCategory;

    const recentCategory = expenses.find((item) => item?.category && orderedCategories.includes(item.category))?.category;
    return recentCategory || "";
  }, [expenses, orderedCategories]);

  const getActionErrorMessage = (e, options = {}) => {
    const rawMessage = String(e?.message || "");
    const msg = rawMessage.toLowerCase();
    const selectedCategory = options.category || "";
    const selectedDate = options.date || "";

    if (
      msg === "expenses.budget_required" ||
      msg.includes("cannot create an expense for") ||
      msg.includes("cannot add expense for")
    ) {
      if (selectedCategory) {
        if (selectedDate) {
          return t("expenses.budgetRequiredForMonth", {
            category: tCategory(selectedCategory),
            month: _formatMonthYearLocal(selectedDate),
          });
        }
        return t("expenses.budgetRequired", { category: tCategory(selectedCategory) });
      }
    }

    if (e?.status === 429) {
      const wait = Number(e?.retryAfterSeconds || 0);
      if (Number.isFinite(wait) && wait > 0) {
        return t("expenses.tooManyWait", { seconds: wait });
      }
      return t("expenses.tooManySoon");
    }
    return localizeApiError(e?.message, t) || e?.message || t("expenses.requestFailed");
  };

  useEffect(() => {
    const next = new URLSearchParams();
    if (activeTab === "recurring") {
      next.set("tab", "recurring");
      // Preserve recurring tab's own search and page state if present
      const currentSearch = searchParams.get("r_search");
      const currentPage = searchParams.get("r_page");
      if (currentSearch) next.set("r_search", currentSearch);
      if (currentPage && currentPage !== "1") next.set("r_page", currentPage);
    } else {
      if (search.trim()) next.set("search", search.trim());
      if (category) next.set("category", category);
      if (startDate) next.set("start_date", startDate);
      if (endDate) next.set("end_date", endDate);
      if (sort && sort !== "newest") next.set("sort", sort);
      if (page > 1) next.set("page", String(page));
    }
    setSearchParams(next, { replace: true });
  }, [search, category, startDate, endDate, sort, page, activeTab, searchParams, setSearchParams]);

  const resetToFirstPage = () => setPage(1);
  const resetFilters = () => {
    setSearch("");
    setCategory("");
    setStartDate("");
    setEndDate("");
    setSort("newest");
    setPage(1);
  };

  const openAdd = () => {
    setActionError("");
    setAddTitle("");
    setAddAmount("");
    setAddCategory(preferredAddCategory);
    setAddDescription("");
    setAddDate(todayISO);
    setTouchedAdd({});
    setAddOpen(true);
  };

  const openEdit = (expense) => {
    setActionError("");
    setEditExpense(expense);
    setEditTitle(expense.title || "");
    setEditAmount(formatAmountInput(String(expense.amount ?? "")));
    setEditCategory(expense.category || "");
    setEditDescription(expense.description || "");
    setEditDate(expense.date || "");
    setTouchedEdit({});
    setEditOpen(true);
  };

  const openDelete = (expense) => {
    setActionError("");
    setDeleteTarget(expense);
    setDeleteOpen(true);
  };

  const openDescription = (expense) => {
    setDescriptionTarget(expense);
    setDescriptionOpen(true);
  };

  useEffect(() => {
    const onPointerDown = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("[data-action-popover]")) return;
      setExpenseMenuForId(null);
      setExpenseMenuPosition(null);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  const openExpenseActions = (event, expense) => {
    setActionError("");
    const button = event.currentTarget;
    const rect = button instanceof HTMLElement ? button.getBoundingClientRect() : null;
    const menuWidth = 176;
    const menuHeight = 120;
    const viewportPadding = 8;
    setExpenseMenuForId((prev) => {
      if (prev === expense.id) {
        setExpenseMenuPosition(null);
        return null;
      }
      if (!rect) return null;
      const fitsBelow = rect.bottom + 6 + menuHeight <= window.innerHeight - viewportPadding;
      const top = fitsBelow ? rect.bottom + 6 : rect.top - 6 - menuHeight;
      const left = Math.max(
        viewportPadding,
        Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - viewportPadding)
      );
      setExpenseMenuPosition({ top, left });
      return expense.id;
    });
  };

  const goPrevPage = () => {
    if (loading || isFetching) return;
    if (page <= 1) return;
    setPage((p) => Math.max(1, p - 1));
  };

  const goNextPage = () => {
    if (loading || isFetching) return;
    if (!hasNext) return;
    setPage((p) => p + 1);
  };

  const addExpenseParsed = useMemo(
    () =>
      expenseFormSchema.safeParse({
        title: addTitle,
        amount: addAmount,
        category: addCategory,
        date: addDate,
        description: addDescription,
      }),
    [addTitle, addAmount, addCategory, addDate, addDescription]
  );

  const addErrors = useMemo(() => {
    if (addExpenseParsed.success) return {};
    const errs = {};
    addExpenseParsed.error.issues.forEach((issue) => {
      const field = issue.path[0];
      if (field && !errs[field] && touchedAdd[field]) {
        errs[field] = t(issue.message, { defaultValue: issue.message });
      }
    });
    return errs;
  }, [addExpenseParsed, t, touchedAdd]);

  const addExpenseMutation = useCreateExpenseMutation();
  const editExpenseMutation = useUpdateExpenseMutation();
  const deleteExpenseMutation = useDeleteExpenseMutation();

  const isAdding = addExpenseMutation.isPending;
  const isEditing = editExpenseMutation.isPending;
  const isDeleting = deleteExpenseMutation.isPending;
  const canSubmitAddExpense = addExpenseParsed.success && !isAdding && !expenseMonthLimitReached;

  const editExpenseParsed = useMemo(
    () =>
      expenseUpdateFormSchema.safeParse({
        title: editTitle,
        amount: editAmount,
        date: editDate,
        description: editDescription,
      }),
    [editTitle, editAmount, editDate, editDescription]
  );

  const editErrors = useMemo(() => {
    if (editExpenseParsed.success) return {};
    const errs = {};
    editExpenseParsed.error.issues.forEach((issue) => {
      const field = issue.path[0];
      if (field && !errs[field] && touchedEdit[field]) {
        errs[field] = t(issue.message, { defaultValue: issue.message });
      }
    });
    return errs;
  }, [editExpenseParsed, t, touchedEdit]);

  const canSubmitEditExpense = editExpenseParsed.success && !isEditing;

  const handleAdd = async () => {
    if (isAdding) return;
    const parsed = expenseFormSchema.safeParse({
      title: addTitle,
      amount: addAmount,
      category: addCategory,
      date: addDate,
      description: addDescription,
    });
    if (!parsed.success) {
      const firstIssue = parsed.error.issues[0];
      return setActionError(translateValidation(firstIssue?.message || t("expenses.requestFailed")));
    }

    try {
      await addExpenseMutation.mutateAsync({
        title: parsed.data.title,
        amount: parsed.data.amount,
        category: parsed.data.category,
        description: parsed.data.description ?? null,
        date: parsed.data.date,
      });
      setStoredLastExpenseCategory(parsed.data.category);
      setAddOpen(false);
    } catch (e) {
      setActionError(getActionErrorMessage(e, { category: parsed.data.category, date: parsed.data.date }));
    }
  };

  const handleEdit = async () => {
    if (isEditing) return;
    if (!editExpense) return;
    const parsed = expenseUpdateFormSchema.safeParse({
      title: editTitle,
      amount: editAmount,
      date: editDate,
      description: editDescription,
    });
    if (!parsed.success) {
      const firstIssue = parsed.error.issues[0];
      return setActionError(translateValidation(firstIssue?.message || t("expenses.requestFailed")));
    }

    try {
      await editExpenseMutation.mutateAsync({
        id: editExpense.id,
        payload: {
          title: parsed.data.title,
          amount: parsed.data.amount,
          description: parsed.data.description,
          date: parsed.data.date,
        },
      });
      setEditOpen(false);
    } catch (e) {
      setActionError(getActionErrorMessage(e, { category: editCategory, date: parsed.data.date }));
    }
  };

  const handleDelete = async () => {
    if (isDeleting) return;
    if (!deleteTarget) return;
    try {
      await deleteExpenseMutation.mutateAsync(deleteTarget.id);
      setDeleteOpen(false);
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const paginationControls = (
    <div className="flex items-center justify-between">
      <p className="text-sm text-muted-foreground">
        {t("expenses.page")} {page} / {totalPages || 1}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page === 1 || loading || isFetching}
          onClick={goPrevPage}
        >
          <ChevronLeft className="mr-1 h-4 w-4" /> {t("expenses.prev")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages || loading || isFetching}
          onClick={goNextPage}
        >
          {t("expenses.next")} <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <PageHeader title={t("expenses.title")} description={t("expenses.subtitle")}>
          {activeTab === "recurring" ? (
            <Button
              className="bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => recurringAddRef.current?.()}
              disabled={recurringCount >= 50}
              title={recurringCount >= 50 ? t("recurring.maxLimitReached") : undefined}
            >
              <Plus className="mr-2 h-4 w-4" /> {t("recurring.addTemplate")}
            </Button>
          ) : (
            <Button
              className="bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={openAdd}
              disabled={expenseMonthLimitReached}
              title={expenseMonthLimitReached ? t("expenses.monthLimitReached") : undefined}
            >
              <Plus className="mr-2 h-4 w-4" /> {t("expenses.addExpense")}
            </Button>
          )}
        </PageHeader>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full space-y-4 shadow-none">
          <TabsList className="grid w-full h-12 max-w-[400px] grid-cols-2 rounded-xl">
            <TabsTrigger value="one-time" className="rounded-lg">{t("expenses.oneTime", { defaultValue: "One-Time Expenses" })}</TabsTrigger>
            <TabsTrigger value="recurring" className="rounded-lg">{t("expenses.recurringTab", { defaultValue: "Recurring" })}</TabsTrigger>
          </TabsList>

          <TabsContent value="one-time" className="space-y-6 mt-4">

            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle>{t("expenses.filtersTitle")}</CardTitle>
                <CardDescription>{t("expenses.filtersDesc")}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-6">
                <Input
                  type="date"
                  max={todayISO}
                  value={startDate}
                  onChange={(e) => {
                    setStartDate(e.target.value);
                    resetToFirstPage();
                  }}
                />
                <Input
                  type="date"
                  max={todayISO}
                  min={startDate || undefined}
                  value={endDate}
                  onChange={(e) => {
                    setEndDate(e.target.value);
                    resetToFirstPage();
                  }}
                />
                <Select
                  value={category || ALL_CATEGORIES_SELECT}
                  onValueChange={(value) => {
                    setCategory(value === ALL_CATEGORIES_SELECT ? "" : value);
                    resetToFirstPage();
                  }}
                >
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value={ALL_CATEGORIES_SELECT}>{t("expenses.allCategories")}</SelectItem>
                    {orderedCategories.map((c) => {
                      const Icon = categoryIconMap[c] || Circle;
                      return (
                        <SelectItem key={c} value={c}>
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4 text-muted-foreground" />
                            <span>{tCategory(c)}</span>
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
                <Select
                  value={sort}
                  onValueChange={(value) => {
                    setSort(value);
                    resetToFirstPage();
                  }}
                >
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="newest">{t("expenses.newest")}</SelectItem>
                    <SelectItem value="oldest">{t("expenses.oldest")}</SelectItem>
                    <SelectItem value="expensive">{t("expenses.highestAmount")}</SelectItem>
                    <SelectItem value="cheapest">{t("expenses.lowestAmount")}</SelectItem>
                  </SelectContent>
                </Select>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder={t("expenses.search")}
                    className="pl-9"
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      resetToFirstPage();
                    }}
                  />
                </div>
                <Button variant="outline" onClick={resetFilters}>
                  {t("common.reset")}
                </Button>
              </CardContent>
            </Card>

            {/* ✅ Expenses Table */}
            <Card className="shadow-sm">
              <CardContent className="min-h-80 py-6">
                <div className="overflow-x-auto">
                  <div className="min-w-[920px] space-y-0">
                    <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,0.4fr)] items-center gap-x-2 border-b border-border px-3 py-3 text-xs uppercase tracking-wide text-muted-foreground">
                      <div className="text-left">{t("expenses.titleCol")}</div>
                      <div className="text-center">{t("expenses.category")}</div>
                      <div className="text-center">{t("expenses.date")}</div>
                      <div className="text-right">{t("expenses.amountUzs")}</div>
                      <div className="text-right" />
                    </div>

                    {loading ? (
                      <div className="flex justify-center px-4 py-10">
                        <LoadingSpinner className="h-6 w-6" />
                      </div>
                    ) : expenses.length === 0 ? (
                      <EmptyState
                        inline
                        description={t("expenses.noResults", { defaultValue: "No expenses found." })}
                      />
                    ) : (
                      expenses.map((e) => (
                        <div
                          key={e.id}
                          className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,0.4fr)] items-start gap-x-2 border-b border-border px-3 py-3 hover:bg-muted/50 dark:hover:bg-muted/30"
                        >
                          <div className="min-w-0 self-center">
                            <TooltipProvider delayDuration={0}>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button
                                    type="button"
                                    className="max-w-full text-left truncate font-medium text-foreground outline-none focus-visible:underline decoration-muted-foreground underline-offset-4 cursor-pointer"
                                    onClick={(e) => e.preventDefault()}
                                  >
                                    {e.title}
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent side="top" className="max-w-[250px] sm:max-w-xs break-words">
                                  {e.title}
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>

                          <div className="min-w-0 self-center flex justify-center">
                            <Badge variant="secondary" className={`max-w-full truncate ${getCategoryBgClass(e.category)}`}>
                              {tCategory(e.category)}
                            </Badge>
                          </div>

                          <div className="self-center text-center text-sm text-foreground whitespace-nowrap">
                            {_formatDisplayDateLocal(e.date)}
                          </div>

                          <CurrencyAmount
                            value={e.amount}
                            format="display"
                            tooltip="compact"
                            className="self-center flex justify-end gap-1 text-sm font-medium tabular-nums whitespace-nowrap"
                            currencyClassName="font-normal tracking-widest self-end pb-[1px]"
                          />

                          <div className="min-w-0">
                            <div className="flex justify-end" data-action-popover>
                              <Button
                                type="button"
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                onClick={(event) => openExpenseActions(event, e)}
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
                {totalPages > 1 && (
                  <div className="mt-4">{paginationControls}</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="recurring" className="space-y-6 mt-4">
            <RecurringExpenses
              onAddClick={(fn) => { recurringAddRef.current = fn; }}
              onCountUpdate={setRecurringCount}
            />
          </TabsContent>
        </Tabs>
      </div>

      {expenseMenuForId && expenseMenuPosition
        ? createPortal(
          <div
            data-action-popover
            className="fixed z-50 w-44 rounded-md border border-border bg-popover p-1 shadow-lg"
            style={{ top: `${expenseMenuPosition.top}px`, left: `${expenseMenuPosition.left}px` }}
          >
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
              onClick={() => {
                const expense = expenses.find((item) => item.id === expenseMenuForId);
                setExpenseMenuForId(null);
                setExpenseMenuPosition(null);
                if (expense) openDescription(expense);
              }}
            >
              <FileText className="h-4 w-4" />
              {t("expenses.viewDescription", { defaultValue: "View description" })}
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
              onClick={() => {
                const expense = expenses.find((item) => item.id === expenseMenuForId);
                setExpenseMenuForId(null);
                setExpenseMenuPosition(null);
                if (expense) openEdit(expense);
              }}
            >
              <Pencil className="h-4 w-4" />
              {t("common.edit", { defaultValue: "Edit" })}
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-destructive/10"
              onClick={() => {
                const expense = expenses.find((item) => item.id === expenseMenuForId);
                setExpenseMenuForId(null);
                setExpenseMenuPosition(null);
                if (expense) openDelete(expense);
              }}
            >
              <Trash2 className="h-4 w-4" />
              {t("common.delete", { defaultValue: "Delete" })}
            </button>
          </div>,
          document.body
        )
        : null}

      {/* Add Dialog */}
      <Dialog
        open={addOpen}
        onOpenChange={(open) => {
          setAddOpen(open);
          if (!open) setActionError("");
        }}
      >
        <DialogContent className="py-8">
          <DialogHeader className="space-y-3 pb-2">
            <DialogTitle className="text-3xl font-bold tracking-tight">{t("expenses.addDialogTitle")}</DialogTitle>
            <DialogDescription>{t("expenses.addDialogDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.titleCol")}</label>
              <div>
                <Input value={addTitle}
                  onChange={(e) => { setAddTitle(e.target.value); setTouchedAdd(p => ({ ...p, title: true })); }}
                  onBlur={() => setTouchedAdd(p => ({ ...p, title: true }))}
                  className={addErrors.title ? "border-red-500 focus-visible:border-red-500" : ""} />
                {addErrors.title && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.title}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.amountUzs")}</label>
              <div>
                <Input
                  type="text"
                  inputMode="numeric"
                  maxLength={15}
                  value={addAmount}
                  onChange={(e) => { setAddAmount(formatAmountInput(e.target.value)); setTouchedAdd(p => ({ ...p, amount: true })); }}
                  onBlur={() => setTouchedAdd(p => ({ ...p, amount: true }))}
                  onKeyDown={(e) => {
                    if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") {
                      e.preventDefault();
                    }
                  }}
                  className={addErrors.amount ? "border-red-500 focus-visible:border-red-500" : ""}
                />
                {addErrors.amount && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.amount}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.category")}</label>
              <div>
                <Select value={addCategory || undefined} onValueChange={(v) => { setAddCategory(v); setTouchedAdd(p => ({ ...p, category: true })); }}>
                  <SelectTrigger className={`${selectTriggerClass} ${addErrors.category ? "border-red-500 focus-visible:border-red-500" : ""}`} onBlur={() => setTouchedAdd(p => ({ ...p, category: true }))}>
                    <SelectValue placeholder={t("expenses.selectCategory")} />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    {orderedCategories.map((c) => {
                      const Icon = categoryIconMap[c] || Circle;
                      return (
                        <SelectItem key={c} value={c}>
                          <div className="flex flex-col gap-1 py-1">
                            <div className="flex items-center gap-2 font-medium">
                              <Icon className="h-4 w-4 text-muted-foreground" />
                              <span>{tCategory(c)}</span>
                            </div>
                            <span className="text-[10px] text-muted-foreground leading-tight">
                              {t(`categories_desc.${c}`)}
                            </span>
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
                {addErrors.category && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.category}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.date")}</label>
              <div>
                <Input
                  type="date"
                  min={MIN_EXPENSE_DATE}
                  max={todayISO}
                  value={addDate}
                  onChange={(e) => { setAddDate(e.target.value); setTouchedAdd(p => ({ ...p, date: true })); }}
                  onBlur={() => setTouchedAdd(p => ({ ...p, date: true }))}
                  className={addErrors.date ? "border-red-500 focus-visible:border-red-500" : ""}
                />
                {addErrors.date && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.date}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})
              </label>
              <div>
                <Textarea
                  className={`h-24 min-h-24 resize-none overflow-y-auto ${addErrors.description ? "border-red-500 focus-visible:border-red-500" : ""}`}
                  value={addDescription}
                  onChange={(e) => { setAddDescription(e.target.value); setTouchedAdd(p => ({ ...p, description: true })); }}
                  onBlur={() => setTouchedAdd(p => ({ ...p, description: true }))}
                />
                {addErrors.description && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.description}</p>}
                {actionError && <p className="text-[11px] leading-4 text-red-500 font-medium ml-0.5 mt-1">{actionError}</p>}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" disabled={isAdding} onClick={() => setAddOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              className="relative min-w-[96px] disabled:pointer-events-auto disabled:cursor-not-allowed"
              disabled={!canSubmitAddExpense}
              onClick={handleAdd}
            >
              {isAdding ? (
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

      {/* Edit Dialog */}
      <Dialog
        open={editOpen}
        onOpenChange={(open) => {
          setEditOpen(open);
          if (!open) setActionError("");
        }}
      >
        <DialogContent className="py-8">
          <DialogHeader className="space-y-3 pb-2">
            <DialogTitle className="text-3xl font-bold tracking-tight">{t("expenses.editDialogTitle")}</DialogTitle>
            <DialogDescription>{t("expenses.editDialogDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.titleCol")}</label>
              <div>
                <Input value={editTitle}
                  onChange={(e) => { setEditTitle(e.target.value); setTouchedEdit(p => ({ ...p, title: true })); }}
                  onBlur={() => setTouchedEdit(p => ({ ...p, title: true }))}
                  className={editErrors.title ? "border-red-500 focus-visible:border-red-500" : ""} />
                {editErrors.title && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{editErrors.title}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.amountUzs")}</label>
              <div>
                <Input
                  type="text"
                  inputMode="numeric"
                  maxLength={15}
                  value={editAmount}
                  onChange={(e) => { setEditAmount(formatAmountInput(e.target.value)); setTouchedEdit(p => ({ ...p, amount: true })); }}
                  onBlur={() => setTouchedEdit(p => ({ ...p, amount: true }))}
                  onKeyDown={(e) => {
                    if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") {
                      e.preventDefault();
                    }
                  }}
                  className={editErrors.amount ? "border-red-500 focus-visible:border-red-500" : ""}
                />
                {editErrors.amount && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{editErrors.amount}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.category")}</label>
              <Input value={tCategory(editCategory) || ""} disabled readOnly />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.date")}</label>
              <div>
                <Input
                  type="date"
                  min={MIN_EXPENSE_DATE}
                  max={todayISO}
                  value={editDate}
                  onChange={(e) => { setEditDate(e.target.value); setTouchedEdit(p => ({ ...p, date: true })); }}
                  onBlur={() => setTouchedEdit(p => ({ ...p, date: true }))}
                  className={editErrors.date ? "border-red-500 focus-visible:border-red-500" : ""}
                />
                {editErrors.date && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{editErrors.date}</p>}
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})
              </label>
              <div>
                <Textarea
                  className={`h-24 min-h-24 resize-none overflow-y-auto ${editErrors.description ? "border-red-500 focus-visible:border-red-500" : ""}`}
                  value={editDescription}
                  onChange={(e) => { setEditDescription(e.target.value); setTouchedEdit(p => ({ ...p, description: true })); }}
                  onBlur={() => setTouchedEdit(p => ({ ...p, description: true }))}
                />
                {editErrors.description && <p className="text-[11px] text-red-500 font-medium ml-0.5 mt-0.5">{editErrors.description}</p>}
              </div>
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" disabled={isEditing} onClick={() => setEditOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              className="relative min-w-24 disabled:pointer-events-auto disabled:cursor-not-allowed"
              disabled={!canSubmitEditExpense}
              onClick={handleEdit}
            >
              {isEditing ? (
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

      {/* Delete Dialog */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={(open) => {
          setDeleteOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.deleteDialogTitle")}
        description={
          deleteTarget
            ? t("expenses.deleteDialogDesc", { title: deleteTarget.title })
            : ""
        }
        onConfirm={handleDelete}
        confirmText={t("expenses.delete")}
        cancelText={t("common.cancel")}
        isConfirming={isDeleting}
        error={actionError}
      />

      {/* Description Modal */}
      <Dialog open={descriptionOpen} onOpenChange={setDescriptionOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("expenses.description")}</DialogTitle>
            <DialogDescription>
              {descriptionTarget?.title || t("expenses.titleCol")}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap wrap-break-word rounded-md border border-border bg-muted/30 p-3 text-sm text-foreground">
            {descriptionTarget?.description || "___"}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDescriptionOpen(false)}>
              {t("common.cancel")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

