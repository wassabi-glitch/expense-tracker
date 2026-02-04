import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Badge } from "./components/ui/badge";
import { Plus, Search } from "lucide-react";

const expenses = [
  {
    id: 1,
    date: "2026-01-30",
    title: "Groceries",
    amount: "$42.50",
    category: "Food",
    description: "Weekly groceries",
  },
  {
    id: 2,
    date: "2026-01-29",
    title: "Electric bill",
    amount: "$90.00",
    category: "Utilities",
    description: "January bill",
  },
  {
    id: 3,
    date: "2026-01-28",
    title: "Metro pass",
    amount: "$25.00",
    category: "Transport",
    description: "Monthly pass",
  },
  {
    id: 4,
    date: "2026-01-27",
    title: "Movie night",
    amount: "$18.00",
    category: "Entertainment",
    description: "Cinema",
  },
];

export default function Expenses() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Expenses</h1>
          <p className="text-muted-foreground">Track, filter, and update your spending.</p>
        </div>
        <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
          <Plus className="mr-2 h-4 w-4" /> Add Expense
        </Button>
      </div>

      <Card className="border-0 bg-card shadow-sm">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Search or narrow down results.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <Input type="date" />
          <Input type="date" />
          <Input placeholder="Category" />
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Search" className="pl-9" />
          </div>
        </CardContent>
      </Card>

      <Card className="border-0 bg-card shadow-sm">
        <CardHeader>
          <CardTitle>Recent expenses</CardTitle>
          <CardDescription>Latest activity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
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
                    <td className="px-3 py-3 text-foreground">{expense.amount}</td>
                    <td className="px-3 py-3">
                      <Badge variant="secondary">{expense.category}</Badge>
                    </td>
                    <td className="px-3 py-3 text-muted-foreground">{expense.description}</td>
                    <td className="px-3 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="outline">Edit</Button>
                        <Button size="sm" variant="destructive">Delete</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
