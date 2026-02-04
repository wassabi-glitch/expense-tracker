import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Download } from "lucide-react";

export default function ExportPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Export</h1>
          <p className="text-muted-foreground">Download your expenses as CSV.</p>
        </div>

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Export CSV</CardTitle>
            <CardDescription>Select a range and category.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            <input
              type="date"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <input
              type="date"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option>All categories</option>
              <option>Food</option>
              <option>Rent</option>
              <option>Utilities</option>
              <option>Transportation</option>
              <option>Entertainment</option>
            </select>
          </CardContent>
          <CardContent>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Download className="mr-2 h-4 w-4" /> Export CSV
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
