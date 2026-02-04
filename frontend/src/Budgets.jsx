import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Progress } from "./components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./components/ui/dialog";
import { Plus } from "lucide-react";
import { useState } from "react";

const budgets = [
  { id: 1, category: "Food & Dining", spent: 275, limit: 500, color: "bg-amber-500" },
  { id: 2, category: "Rent & Utilities", spent: 1200, limit: 1200, color: "bg-blue-500" },
  { id: 3, category: "Transportation", spent: 95, limit: 300, color: "bg-rose-500" },
  { id: 4, category: "Entertainment", spent: 190, limit: 200, color: "bg-emerald-500" },
];

const categories = [
  "Food",
  "Rent",
  "Utilities",
  "Transportation",
  "Entertainment",
  "Health",
  "Savings",
  "Other",
];

export default function Budgets() {
  const [addOpen, setAddOpen] = useState(false);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedBudget, setSelectedBudget] = useState(null);
  const [newLimit, setNewLimit] = useState("");
  const [addCategory, setAddCategory] = useState("");
  const [addLimit, setAddLimit] = useState("");

  const openUpdate = (budget) => {
    setSelectedBudget(budget);
    setNewLimit(String(budget.limit));
    setUpdateOpen(true);
  };

  const openDelete = (budget) => {
    setSelectedBudget(budget);
    setDeleteOpen(true);
  };

  const openAdd = () => {
    setAddCategory("");
    setAddLimit("");
    setAddOpen(true);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Budgets</h1>
            <p className="text-muted-foreground">Set limits and track monthly progress.</p>
          </div>
          <Button className="bg-primary text-primary-foreground hover:bg-primary/90" onClick={openAdd}>
            <Plus className="mr-2 h-4 w-4" /> Add Budget
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {budgets.map((b) => {
            const percent = Math.min(Math.round((b.spent / b.limit) * 100), 100);
            return (
              <Card key={b.id} className="border-0 bg-card shadow-sm">
                <CardHeader className="space-y-1">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-base">{b.category}</CardTitle>
                      <CardDescription>
                        ${b.spent} of ${b.limit} used
                      </CardDescription>
                    </div>
                    <span className={`mt-1 h-2.5 w-2.5 rounded-full ${b.color}`} />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>{percent}% used</span>
                  </div>
                  <Progress value={percent} className="h-2" />
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => openUpdate(b)}
                    >
                      Update limit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      className="flex-1"
                      onClick={() => openDelete(b)}
                    >
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Inactive budgets</CardTitle>
            <CardDescription>Categories with no activity this month.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            No inactive budgets yet.
          </CardContent>
        </Card>
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
                <option value="" disabled>Select category</option>
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button onClick={() => setAddOpen(false)}>Add</Button>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setUpdateOpen(false)}>Cancel</Button>
            <Button onClick={() => setUpdateOpen(false)}>Save</Button>
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
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={() => setDeleteOpen(false)}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
