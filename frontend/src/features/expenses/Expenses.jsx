import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Plus, Search, ChevronLeft, ChevronRight, Inbox, Trash2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  createExpense,
  deleteExpense,
  getCategories,
  getExpenses,
  updateExpense,
} from "@/lib/api";
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

const PAGE_SIZE = 10;
const MIN_EXPENSE_DATE = "2020-01-01";
const MAX_EXPENSE_AMOUNT_DIGITS = String(MAX_EXPENSE_AMOUNT).length;
const ALL_CATEGORIES_SELECT = "__all_categories__";

import { getCategoryBgClass } from "@/lib/category";
import { formatAmountDisplay, formatAmountInput, formatDisplayDate, formatMonthYear } from "@/lib/format";

const parsePageParam = (value) => {
  const raw = String(value ?? "").trim();
  if (!raw) return 1;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
};

export default function Expenses() {
  const { t, i18n } = useTranslation();
  const translateValidation = (message) => t(message, { defaultValue: message });
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  const [expenses, setExpenses] = useState([]);
  const [categories, setCategories] = useState([]);

  const [search, setSearch] = useState(() => searchParams.get("search") || "");
  const [category, setCategory] = useState(() => searchParams.get("category") || "");
  const [startDate, setStartDate] = useState(() => searchParams.get("start_date") || "");
  const [endDate, setEndDate] = useState(() => searchParams.get("end_date") || "");
  const [sort, setSort] = useState(() => searchParams.get("sort") || "newest");
  const todayISO = useMemo(() => toISODateInTimeZone(), []);

  const [page, setPage] = useState(() => parsePageParam(searchParams.get("page")));
  const [hasNext, setHasNext] = useState(false);

  const [addOpen, setAddOpen] = useState(false);
  const [addTitle, setAddTitle] = useState("");
  const [addAmount, setAddAmount] = useState("");
  const [addCategory, setAddCategory] = useState("");
  const [addDescription, setAddDescription] = useState("");
  const [addDate, setAddDate] = useState("");

  const [editOpen, setEditOpen] = useState(false);
  const [editExpense, setEditExpense] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editDate, setEditDate] = useState("");

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isAdding, setIsAdding] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const [descriptionTarget, setDescriptionTarget] = useState(null);

  const firstLoadRef = useRef(true);
  const pageNavLockRef = useRef(false);

  const tCategory = (name) => t(`categories.${name}`, { defaultValue: name });
  const selectTriggerClass =
    "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
  const selectContentClass =
    "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();

  const _formatDisplayDateLocal = (value) => formatDisplayDate(value, appLang);
  const _formatMonthYearLocal = (value) => formatMonthYear(value, undefined, appLang);

  const dateFilterError = useMemo(() => {
    if (startDate && startDate > todayISO) return t("expenses.startFuture");
    if (endDate && endDate > todayISO) return t("expenses.endFuture");
    if (startDate && endDate && startDate > endDate) return t("expenses.startAfterEnd");
    return "";
  }, [startDate, endDate, todayISO, t]);

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

  const loadExpenses = useCallback(async ({ initial = false } = {}) => {
    if (initial) {
      setLoading(true);
    } else {
      setIsFetching(true);
    }
    setError("");
    setActionError("");

    if (dateFilterError) {
      setError(dateFilterError);
      if (initial) setLoading(false);
      setIsFetching(false);
      return;
    }

    try {
      const [expenseRows, categoryList] = await Promise.all([
        getExpenses(queryParams),
        getCategories(),
      ]);

      setExpenses(expenseRows || []);
      setCategories(categoryList || []);
      setHasNext((expenseRows || []).length === PAGE_SIZE);
    } catch (e) {
      setError(localizeApiError(e?.message, t) || e.message || t("expenses.loadFailed"));
    } finally {
      if (initial) {
        setLoading(false);
      } else {
        setIsFetching(false);
      }
      pageNavLockRef.current = false;
    }
  }, [queryParams, dateFilterError, t]);

  useEffect(() => {
    loadExpenses({ initial: firstLoadRef.current });
    if (firstLoadRef.current) firstLoadRef.current = false;
  }, [loadExpenses]);

  useEffect(() => {
    const next = new URLSearchParams();
    if (search.trim()) next.set("search", search.trim());
    if (category) next.set("category", category);
    if (startDate) next.set("start_date", startDate);
    if (endDate) next.set("end_date", endDate);
    if (sort && sort !== "newest") next.set("sort", sort);
    if (page > 1) next.set("page", String(page));
    setSearchParams(next, { replace: true });
  }, [search, category, startDate, endDate, sort, page, setSearchParams]);

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
    setAddCategory("");
    setAddDescription("");
    setAddDate("");
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

  const goPrevPage = () => {
    if (loading || isFetching || pageNavLockRef.current) return;
    if (page <= 1) return;
    pageNavLockRef.current = true;
    setPage((p) => Math.max(1, p - 1));
  };

  const goNextPage = () => {
    if (loading || isFetching || pageNavLockRef.current) return;
    if (!hasNext) return;
    pageNavLockRef.current = true;
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
  const canSubmitAddExpense = addExpenseParsed.success && !isAdding;

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
      setIsAdding(true);
      await createExpense({
        title: parsed.data.title,
        amount: parsed.data.amount,
        category: parsed.data.category,
        description: parsed.data.description ?? null,
        date: parsed.data.date,
      });
      setAddOpen(false);
      await loadExpenses();
    } catch (e) {
      setActionError(getActionErrorMessage(e, { category: parsed.data.category, date: parsed.data.date }));
    } finally {
      setIsAdding(false);
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
      setIsEditing(true);
      await updateExpense(editExpense.id, {
        title: parsed.data.title,
        amount: parsed.data.amount,
        description: parsed.data.description,
        date: parsed.data.date,
      });
      setEditOpen(false);
      await loadExpenses();
    } catch (e) {
      setActionError(getActionErrorMessage(e, { category: editCategory, date: parsed.data.date }));
    } finally {
      setIsEditing(false);
    }
  };

  const handleDelete = async () => {
    if (isDeleting) return;
    if (!deleteTarget) return;
    try {
      setIsDeleting(true);
      await deleteExpense(deleteTarget.id);
      setDeleteOpen(false);
      await loadExpenses();
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    } finally {
      setIsDeleting(false);
    }
  };

  const paginationControls = (
    <div className="flex items-center justify-between">
      <p className="text-sm text-muted-foreground">
        {t("expenses.page")} {page}
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
          disabled={!hasNext || loading || isFetching}
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
          <Button
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            onClick={openAdd}
          >
            <Plus className="mr-2 h-4 w-4" /> {t("expenses.addExpense")}
          </Button>
        </PageHeader>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {actionError && !addOpen && !editOpen && !deleteOpen && (
          <p className="text-sm text-red-600">{actionError}</p>
        )}

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
                {categories.map((c) => (
                  <SelectItem key={c} value={c}>
                    {tCategory(c)}
                  </SelectItem>
                ))}
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
                <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,2fr)] items-center gap-x-2 border-b border-border px-3 py-3 text-xs uppercase tracking-wide text-muted-foreground">
                  <div className="text-left">{t("expenses.titleCol")}</div>
                  <div className="text-center">{t("expenses.category")}</div>
                  <div className="text-center">{t("expenses.date")}</div>
                  <div className="text-right">{t("expenses.amountUzs")}</div>
                  <div className="text-right">
                    {t("common.actions", { defaultValue: "Actions" })}
                  </div>
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
                      className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,2fr)] items-start gap-x-2 border-b border-border px-3 py-3 hover:bg-muted/30"
                    >
                      <div className="min-w-0 self-center">
                        <div className="truncate font-medium text-foreground" title={e.title}>
                          {e.title}
                        </div>
                      </div>

                      <div className="min-w-0 self-center flex justify-center">
                        <Badge variant="secondary" className={`max-w-full truncate ${getCategoryBgClass(e.category)}`}>
                          {tCategory(e.category)}
                        </Badge>
                      </div>

                      <div className="self-center text-center text-sm text-foreground whitespace-nowrap">
                        {_formatDisplayDateLocal(e.date)}
                      </div>

                      <div className="self-center text-right text-sm font-medium tabular-nums whitespace-nowrap">
                        {formatAmountDisplay(e.amount)} UZS
                      </div>

                      <div className="min-w-0">
                        <div className="flex flex-wrap justify-end gap-1.5">
                          <Button
                            type="button"
                            variant="outline"
                            className="h-8 max-w-[8.5rem] truncate px-2 text-xs text-muted-foreground hover:bg-muted/40"
                            onClick={() => openDescription(e)}
                          >
                            {t("expenses.viewDescription", {
                              defaultValue: "View description",
                            })}
                          </Button>

                          <Button
                            type="button"
                            variant="outline"
                            className="h-8 px-2 text-xs"
                            onClick={() => openEdit(e)}
                          >
                            {t("common.edit", { defaultValue: "Edit" })}
                          </Button>

                          <Button
                            type="button"
                            variant="ghost"
                            className="h-8 px-2 text-xs text-destructive bg-destructive/10 hover:bg-destructive/20 hover:text-destructive active:bg-destructive/30"
                            onClick={() => openDelete(e)}
                          >
                            <Trash2 className="mr-1 h-3.5 w-3.5" />
                            {t("common.delete", { defaultValue: "Delete" })}
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="mt-4">{paginationControls}</div>
          </CardContent>
        </Card>
      </div>

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
              <Input value={addTitle} onChange={(e) => setAddTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.amountUzs")}</label>
              <Input
                type="text"
                inputMode="numeric"
                maxLength={15}
                value={addAmount}
                onChange={(e) => setAddAmount(formatAmountInput(e.target.value))}
                onKeyDown={(e) => {
                  if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") {
                    e.preventDefault();
                  }
                }}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.category")}</label>
              <Select value={addCategory || undefined} onValueChange={setAddCategory}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue placeholder={t("expenses.selectCategory")} />
                </SelectTrigger>
                <SelectContent className={selectContentClass} position="popper" side="bottom">
                  {categories.map((c) => (
                    <SelectItem key={c} value={c}>
                      {tCategory(c)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.date")}</label>
              <Input
                type="date"
                min={MIN_EXPENSE_DATE}
                max={todayISO}
                value={addDate}
                onChange={(e) => setAddDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})
              </label>
              <Textarea
                className="h-24 min-h-24 resize-none overflow-y-auto"
                value={addDescription}
                onChange={(e) => setAddDescription(e.target.value)}
              />
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
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
              <Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.amountUzs")}</label>
              <Input
                type="text"
                inputMode="numeric"
                maxLength={15}
                value={editAmount}
                onChange={(e) => setEditAmount(formatAmountInput(e.target.value))}
                onKeyDown={(e) => {
                  if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") {
                    e.preventDefault();
                  }
                }}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.category")}</label>
              <Input value={tCategory(editCategory) || ""} disabled readOnly />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("expenses.date")}</label>
              <Input
                type="date"
                min={MIN_EXPENSE_DATE}
                max={todayISO}
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})
              </label>
              <Textarea
                className="h-24 min-h-24 resize-none overflow-y-auto"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
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

