import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { TrendingUp } from "lucide-react";

const summary = [
  { label: "Lifetime spent", value: "$12,480" },
  { label: "Avg transaction", value: "$32.40" },
  { label: "Total transactions", value: "386" },
];

const categories = [
  { name: "Food & Dining", total: "$3,240" },
  { name: "Rent & Utilities", total: "$5,100" },
  { name: "Transportation", total: "$1,120" },
  { name: "Entertainment", total: "$820" },
];

export default function Analytics() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Analytics</h1>
            <p className="text-muted-foreground">Understand your spending trends.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline">7 days</Button>
            <Button variant="outline">30 days</Button>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90">Custom range</Button>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {summary.map((item) => (
            <Card key={item.label} className="border-0 bg-card shadow-sm">
              <CardHeader className="space-y-1">
                <CardDescription>{item.label}</CardDescription>
                <CardTitle className="text-2xl">{item.value}</CardTitle>
              </CardHeader>
            </Card>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 border-0 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Daily trend</CardTitle>
              <CardDescription>Last 30 days</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 w-full rounded-lg border border-dashed border-border bg-muted/30 flex flex-col items-center justify-center text-muted-foreground gap-2">
                <TrendingUp className="h-8 w-8 opacity-50" />
                <p className="text-sm">Line chart goes here</p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 bg-card shadow-sm">
            <CardHeader>
              <CardTitle>Category breakdown</CardTitle>
              <CardDescription>Totals by category</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {categories.map((c) => (
                <div key={c.name} className="flex items-center justify-between">
                  <span className="text-sm text-foreground">{c.name}</span>
                  <span className="text-sm font-semibold">{c.total}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
