import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Download, Plus, Wallet, TrendingUp, Layers, Crown } from "lucide-react";

const stats = [
  { label: "Total spent (month)", value: "$1,420", icon: Wallet },
  { label: "Remaining budget", value: "$580", icon: TrendingUp },
  { label: "Biggest category", value: "Rent & Utilities", icon: Crown },
  { label: "Avg daily spend", value: "$47", icon: Layers },
];

const budgets = [
  { id: 1, category: "Food & Dining", spent: 275, limit: 500, color: "bg-amber-500" },
  { id: 2, category: "Rent & Utilities", spent: 1200, limit: 1200, color: "bg-blue-500" },
  { id: 3, category: "Transportation", spent: 95, limit: 300, color: "bg-rose-500" },
  { id: 4, category: "Entertainment", spent: 190, limit: 200, color: "bg-emerald-500" },
];

const recentExpenses = [
  { id: 1, title: "Groceries", category: "Food", amount: "$42.50", date: "Jan 30" },
  { id: 2, title: "Electric bill", category: "Utilities", amount: "$90.00", date: "Jan 29" },
  { id: 3, title: "Metro pass", category: "Transport", amount: "$25.00", date: "Jan 28" },
  { id: 4, title: "Movie night", category: "Entertainment", amount: "$18.00", date: "Jan 27" },
];

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Container aligns with the Navbar limits */}
      <div className="container mx-auto px-4 py-8 space-y-8">

        {/* --- TOP BAR --- */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Your financial overview for <span className="font-medium text-foreground">January 2026</span>.
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" className="bg-background hover:bg-muted">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Expense
            </Button>
          </div>
        </div>

        {/* --- STATS GRID --- */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s, i) => {
            const Icon = s.icon;
            return (
              <Card key={i} className="shadow-sm">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {s.label}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{s.value}</div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* --- MAIN CONTENT --- */}
        <div className="grid gap-6 lg:grid-cols-3">

          {/* BUDGET STATUS (Takes up 2 cols) */}
          <Card className="lg:col-span-2 shadow-sm">
            <CardHeader>
              <CardTitle>Budget Status</CardTitle>
              <CardDescription>Monthly allocation by category</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {budgets.map((b) => {
                const percent = Math.min(Math.round((b.spent / b.limit) * 100), 100);
                return (
                  <div key={b.id} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${b.color}`} />
                        <span className="font-medium">{b.category}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">
                          ${b.spent} / ${b.limit}
                        </span>
                        <Badge
                          variant="outline"
                          className={percent >= 100 ? "text-destructive border-destructive/50" : "text-foreground"}
                        >
                          {percent}%
                        </Badge>
                      </div>
                    </div>
                    {/* Progress Bar with Theme Colors */}
                    <Progress value={percent} className="h-2" />
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* RECENT EXPENSES (Takes up 1 col) */}
          <Card className="shadow-sm flex flex-col">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest transactions</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 space-y-4">
              {recentExpenses.map((e) => (
                <div key={e.id} className="flex items-center justify-between border-b border-border pb-4 last:border-0 last:pb-0">
                  <div className="space-y-1">
                    <p className="text-sm font-medium leading-none">{e.title}</p>
                    <p className="text-xs text-muted-foreground">{e.category} • {e.date}</p>
                  </div>
                  <div className="font-semibold text-sm">{e.amount}</div>
                </div>
              ))}
            </CardContent>
            {/* Footer Action */}
            <div className="p-4 pt-0 mt-auto">
              <Button variant="ghost" className="w-full text-muted-foreground hover:text-foreground">
                View All Transactions
              </Button>
            </div>
          </Card>
        </div>

        {/* --- CHART SECTION --- */}
        <Card className="shadow-sm">
          <CardHeader className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Spending Trends</CardTitle>
              <CardDescription>Daily expenses over time</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="h-8">7 Days</Button>
              <Button size="sm" className="h-8 bg-primary text-primary-foreground hover:bg-primary/90">30 Days</Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[250px] w-full rounded-lg border border-dashed border-border bg-muted/30 flex flex-col items-center justify-center text-muted-foreground gap-2">
              <TrendingUp className="h-8 w-8 opacity-50" />
              <p className="text-sm">Chart visualization would go here</p>
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
