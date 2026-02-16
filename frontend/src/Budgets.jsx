import { useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";

import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { LoadingSpinner } from "./components/ui/loading-spinner";
import { Progress } from "./components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./components/ui/dialog";
import {
  createBudget,
  deleteBudget,
  getBudgets,
  getThisMonthStats,
  updateBudget,
  getCategories,
} from "./api";

const categoryDotClass = {
  Food: "bg-amber-500",
  Transport: "bg-blue-500",
  Housing: "bg-violet-500",
  Entertainment: "bg-rose-500",
  Utilities: "bg-emerald-500",
  Other: "bg-slate-500",
};

export default function Budgets() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");

  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);

  const [addOpen, setAddOpen] = useState(false);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const [selectedBudget, setSelectedBudget] = useState(null);
  const [newLimit, setNewLimit] = useState("");
  const [addCategory, setAddCategory] = useState("");
  const [addLimit, setAddLimit] = useState("");

  async function loadBudgetsPage() {
    setLoading(true);
    setError("");

    try {
      const [budgetRows, stats, categoryList] = await Promise.all([
        getBudgets(),
        getThisMonthStats(),
        getCategories(),
      ]);

      setCategories(categoryList || []);

      const spentByCategory = new Map(
        (stats?.category_breakdown || []).map((item) => [item.category, Number(item.total || 0)])
      );

      const merged = (budgetRows || []).map((b) => ({
        id: b.id,
        category: b.category,
        limit: Number(b.monthly_limit || 0),
        spent: spentByCategory.get(b.category) ?? 0,
      }));

      setBudgets(merged);
    } catch (e) {
      setError(e.message || "Failed to load budgets");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBudgetsPage();
  }, []);

  const sortedBudgets = useMemo(() => {
    return [...budgets].sort((a, b) => a.category.localeCompare(b.category));
  }, [budgets]);

  const formatUzs = (value) => String(Number(value || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

  const openUpdate = (budget) => {
    setActionError("");
    setSelectedBudget(budget);
    setNewLimit(String(budget.limit));
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
    setAddOpen(true);
  };

  async function handleAddBudget() {
    setActionError("");

    if (!addCategory) {
      setActionError("Please select a category.");
      return;
    }

    const parsed = Number(addLimit);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setActionError("Monthly limit must be a positive whole number.");
      return;
    }

    try {
      await createBudget(addCategory, parsed);
      setAddOpen(false);
      await loadBudgetsPage();
    } catch (e) {
      setActionError(e.message || "Failed to add budget");
    }
  }

  async function handleUpdateBudget() {
    setActionError("");

    if (!selectedBudget) return;

    const parsed = Number(newLimit);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setActionError("Monthly limit must be a positive whole number.");
      return;
    }

    try {
      await updateBudget(selectedBudget.category, parsed);
      setUpdateOpen(false);
      await loadBudgetsPage();
    } catch (e) {
      setActionError(e.message || "Failed to update budget");
    }
  }

  async function handleDeleteBudget() {
    setActionError("");

    if (!selectedBudget) return;

    try {
      await deleteBudget(selectedBudget.category);
      setDeleteOpen(false);
      await loadBudgetsPage();
    } catch (e) {
      setActionError(e.message || "Failed to delete budget");
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Budgets</h1>
            <p className="text-muted-foreground">Set your monthly spending limits for this month.</p>
          </div>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90" onClick={openAdd}>
            <Plus className="mr-2 h-4 w-4" /> Add Budget
          </Button>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {loading && (
          <div className="flex min-h-[120px] items-center justify-center">
            <LoadingSpinner className="h-8 w-8" />
          </div>
        )}

        {!loading && !error && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sortedBudgets.map((b) => {
              const percent = b.limit > 0 ? Math.min(Math.round((b.spent / b.limit) * 100), 100) : 0;

              return (
                <Card key={b.id} className="border-0 bg-card shadow-sm">
                  <CardHeader className="space-y-1">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle className="text-base">{b.category}</CardTitle>
                        <CardDescription>
                          {formatUzs(b.spent)} UZS of {formatUzs(b.limit)} UZS used
                        </CardDescription>
                      </div>
                      <span
                        className={`mt-1 h-2.5 w-2.5 rounded-full ${categoryDotClass[b.category] || "bg-slate-500"}`}
                      />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>{percent}% used</span>
                    </div>
                    <Progress value={percent} className="h-2" />
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" className="flex-1" onClick={() => openUpdate(b)}>
                        Update limit
                      </Button>
                      <Button variant="destructive" size="sm" className="flex-1" onClick={() => openDelete(b)}>
                        Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {!loading && !error && sortedBudgets.length === 0 && (
          <Card className="border-0 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>No budgets yet</CardTitle>
              <CardDescription>Create your first category budget.</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add budget</DialogTitle>
            <DialogDescription>Select a category and set a monthly limit.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
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
              <label className="text-sm font-medium">Monthly limit</label>
              <input
                type="number"
                min="0"
                step="1"
                inputMode="numeric"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={addLimit}
                onChange={(e) => setAddLimit(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "-" || e.key.toLowerCase() === "e") e.preventDefault();
                }}
              />
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddBudget}>Add</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={updateOpen} onOpenChange={setUpdateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update budget limit</DialogTitle>
            <DialogDescription>
              {selectedBudget ? `Update limit for ${selectedBudget.category}.` : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-sm font-medium">New limit</label>
            <input
              type="number"
              min="0"
              step="1"
              inputMode="numeric"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={newLimit}
              onChange={(e) => setNewLimit(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "-" || e.key.toLowerCase() === "e") e.preventDefault();
              }}
            />
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUpdateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateBudget}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete budget</DialogTitle>
            <DialogDescription>
              {selectedBudget ? `This will remove the ${selectedBudget.category} budget.` : ""}
            </DialogDescription>
          </DialogHeader>
          {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteBudget}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
