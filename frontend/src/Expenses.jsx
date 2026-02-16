import { useEffect, useMemo, useRef, useState } from "react";
import { Plus, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Badge } from "./components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./components/ui/dialog";
import {
  createExpense,
  deleteExpense,
  getCategories,
  getExpenses,
  updateExpense,
} from "./api";

const PAGE_SIZE = 10;
const MIN_EXPENSE_DATE = "2020-01-01";

export default function Expenses() {
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
  const todayISO = useMemo(() => new Date().toISOString().split("T")[0], []);

  const [page, setPage] = useState(() => {
    const raw = Number(searchParams.get("page") || "1");
    return Number.isInteger(raw) && raw > 0 ? raw : 1;
  });
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
  const firstLoadRef = useRef(true);

  const dateFilterError = useMemo(() => {
    if (startDate && startDate > todayISO) return "Start date cannot be in the future.";
    if (endDate && endDate > todayISO) return "End date cannot be in the future.";
    if (startDate && endDate && startDate > endDate) return "Start date cannot be after end date.";
    return "";
  }, [startDate, endDate, todayISO]);

  const formatUzs = (value) => String(Number(value || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const getActionErrorMessage = (e) => {
    if (e?.status === 429) {
      const wait = Number(e?.retryAfterSeconds || 0);
      if (Number.isFinite(wait) && wait > 0) {
        return `Too many requests. Try again in ${wait} seconds.`;
      }
      return "Too many requests. Try again soon.";
    }
    return e?.message || "Request failed";
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

  async function loadExpenses({ initial = false } = {}) {
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
      setError(e.message || "Failed to load expenses");
    } finally {
      if (initial) {
        setLoading(false);
      } else {
        setIsFetching(false);
      }
    }
  }

  useEffect(() => {
    loadExpenses({ initial: firstLoadRef.current });
    if (firstLoadRef.current) firstLoadRef.current = false;
  }, [queryParams, dateFilterError]);

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
    setEditAmount(String(expense.amount ?? ""));
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

  const handleAdd = async () => {
    setActionError("");

    if (!addTitle.trim()) {
      setActionError("Title is required.");
      return;
    }
    if (!addCategory) {
      setActionError("Please select a category.");
      return;
    }
    const parsedAmount = Number(addAmount);
    if (!Number.isInteger(parsedAmount) || parsedAmount <= 0) {
      setActionError("Amount must be a positive whole number.");
      return;
    }
    if (!addDate) {
      setActionError("Please select a date.");
      return;
    }
    if (addDate < MIN_EXPENSE_DATE) {
      setActionError("Date cannot be earlier than 2020-01-01.");
      return;
    }

    try {
      await createExpense({
        title: addTitle.trim(),
        amount: parsedAmount,
        category: addCategory,
        description: addDescription.trim() || null,
        date: addDate,
      });
      setAddOpen(false);
      await loadExpenses();
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleEdit = async () => {
    setActionError("");

    if (!editExpense) return;

    if (!editTitle.trim()) {
      setActionError("Title is required.");
      return;
    }
    if (!editCategory) {
      setActionError("Please select a category.");
      return;
    }
    const parsedAmount = Number(editAmount);
    if (!Number.isInteger(parsedAmount) || parsedAmount <= 0) {
      setActionError("Amount must be a positive whole number.");
      return;
    }
    if (!editDate) {
      setActionError("Please select a date.");
      return;
    }
    if (editDate < MIN_EXPENSE_DATE) {
      setActionError("Date cannot be earlier than 2020-01-01.");
      return;
    }

    try {
      await updateExpense(editExpense.id, {
        title: editTitle.trim(),
        amount: parsedAmount,
        category: editCategory,
        description: editDescription.trim() || null,
        date: editDate,
      });
      setEditOpen(false);
      await loadExpenses();
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleDelete = async () => {
    setActionError("");

    if (!deleteTarget) return;

    try {
      await deleteExpense(deleteTarget.id);
      setDeleteOpen(false);
      await loadExpenses();
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Expenses</h1>
            <p className="text-muted-foreground">Track, filter, and update your spending.</p>
          </div>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90" onClick={openAdd}>
            <Plus className="mr-2 h-4 w-4" /> Add Expense
          </Button>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {actionError && <p className="text-sm text-red-600">{actionError}</p>}

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Filters</CardTitle>
            <CardDescription>Search or narrow down results.</CardDescription>
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
            <select
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                resetToFirstPage();
              }}
            >
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <select
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                resetToFirstPage();
              }}
            >
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="expensive">Highest amount</option>
              <option value="cheapest">Lowest amount</option>
            </select>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search"
                className="pl-9"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  resetToFirstPage();
                }}
              />
            </div>
            <Button variant="outline" onClick={resetFilters}>
              Reset
            </Button>
          </CardContent>
        </Card>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Recent expenses</CardTitle>
            <CardDescription>Latest activity</CardDescription>
          </CardHeader>
          <CardContent className="min-h-[320px]">
            {loading ? (
              <div className="space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-10 w-full animate-pulse rounded-md bg-muted" />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-180 text-sm">
                  <thead className="text-left text-muted-foreground">
                    <tr className="border-b">
                      <th className="px-3 py-2 font-medium">Date</th>
                      <th className="px-3 py-2 font-medium">Title</th>
                      <th className="px-3 py-2 font-medium">Amount</th>
                      <th className="px-3 py-2 font-medium">Category</th>
                      <th className="px-3 py-2 font-medium">Description</th>
                      <th className="px-3 py-2 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenses.map((expense) => (
                      <tr key={expense.id} className="border-b last:border-0">
                        <td className="px-3 py-3 text-muted-foreground">{expense.date}</td>
                        <td className="px-3 py-3 font-medium text-foreground">{expense.title}</td>
                        <td className="px-3 py-3 text-foreground">
                          {formatUzs(expense.amount)} UZS
                        </td>
                        <td className="px-3 py-3">
                          <Badge variant="secondary">{expense.category}</Badge>
                        </td>
                        <td className="px-3 py-3 text-muted-foreground">
                          {expense.description || "___"}
                        </td>
                        <td className="px-3 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <Button size="sm" variant="outline" onClick={() => openEdit(expense)}>Edit</Button>
                            <Button size="sm" variant="destructive" onClick={() => openDelete(expense)}>
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {expenses.length === 0 && (
                      <tr>
                        <td className="px-3 py-6 text-center text-sm text-muted-foreground" colSpan={6}>
                          No expenses found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
                {isFetching && null}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">Page {page}</p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="mr-1 h-4 w-4" /> Prev
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasNext || loading}
              onClick={() => setPage((p) => p + 1)}
            >
              Next <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add expense</DialogTitle>
            <DialogDescription>Fill the details and save.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Title</label>
              <Input value={addTitle} onChange={(e) => setAddTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Amount (UZS)</label>
              <Input
                type="number"
                min="0"
                step="1"
                inputMode="numeric"
                value={addAmount}
                onChange={(e) => setAddAmount(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "-" || e.key.toLowerCase() === "e") e.preventDefault();
                }}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={addCategory}
                onChange={(e) => setAddCategory(e.target.value)}
              >
                <option value="" disabled>
                  Select category
                </option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Date</label>
              <Input
                type="date"
                min={MIN_EXPENSE_DATE}
                max={todayISO}
                value={addDate}
                onChange={(e) => setAddDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Input value={addDescription} onChange={(e) => setAddDescription(e.target.value)} />
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAdd}>Add</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit expense</DialogTitle>
            <DialogDescription>Update the details and save.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-2">
              <label className="text-sm font-medium">Title</label>
              <Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Amount (UZS)</label>
              <Input
                type="number"
                min="0"
                step="1"
                inputMode="numeric"
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "-" || e.key.toLowerCase() === "e") e.preventDefault();
                }}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <select
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
              >
                <option value="" disabled>
                  Select category
                </option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Date</label>
              <Input
                type="date"
                min={MIN_EXPENSE_DATE}
                max={todayISO}
                value={editDate}
                onChange={(e) => setEditDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleEdit}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete expense</DialogTitle>
            <DialogDescription>
              {deleteTarget ? `This will remove \"${deleteTarget.title}\".` : ""}
            </DialogDescription>
          </DialogHeader>
          {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
