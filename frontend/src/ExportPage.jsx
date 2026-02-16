import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { LoadingSpinner } from "./components/ui/loading-spinner";
import { exportExpensesCsv, getCategories } from "./api";

const MIN_EXPENSE_DATE = "2020-01-01";

export default function ExportPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const [categories, setCategories] = useState([]);
  const [startDate, setStartDate] = useState(() => searchParams.get("start_date") || "");
  const [endDate, setEndDate] = useState(() => searchParams.get("end_date") || "");
  const [category, setCategory] = useState(() => searchParams.get("category") || "");
  const [sort, setSort] = useState(() => {
    const raw = searchParams.get("sort");
    return raw === "oldest" ? "oldest" : "newest";
  });

  const todayISO = useMemo(() => new Date().toISOString().split("T")[0], []);

  useEffect(() => {
    const loadMeta = async () => {
      setLoading(true);
      setError("");
      try {
        const list = await getCategories();
        setCategories(list || []);
      } catch (e) {
        setError(e.message || "Failed to load export options");
      } finally {
        setLoading(false);
      }
    };
    loadMeta();
  }, []);

  useEffect(() => {
    const next = new URLSearchParams();
    if (startDate) next.set("start_date", startDate);
    if (endDate) next.set("end_date", endDate);
    if (category) next.set("category", category);
    if (sort !== "newest") next.set("sort", sort);
    setSearchParams(next, { replace: true });
  }, [startDate, endDate, category, sort, setSearchParams]);

  const filterError = useMemo(() => {
    if (startDate && startDate < MIN_EXPENSE_DATE) return "Start date cannot be earlier than 2020-01-01.";
    if (endDate && endDate < MIN_EXPENSE_DATE) return "End date cannot be earlier than 2020-01-01.";
    if (startDate && endDate && startDate > endDate) return "Start date cannot be after end date.";
    return "";
  }, [startDate, endDate]);

  const handleExport = async () => {
    setError("");
    if (filterError) {
      setError(filterError);
      return;
    }

    setExporting(true);
    try {
      const { blob, filename } = await exportExpensesCsv({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        category: category || undefined,
        sort,
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message || "Failed to export CSV");
    } finally {
      setExporting(false);
    }
  };

  const handleReset = () => {
    setError("");
    setStartDate("");
    setEndDate("");
    setCategory("");
    setSort("newest");
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Export</h1>
          <p className="text-muted-foreground">Download your expenses as CSV.</p>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Card className="border-0 bg-card shadow-sm">
          <CardHeader>
            <CardTitle>Export CSV</CardTitle>
            <CardDescription>Filters are optional. Export will include matching expenses only.</CardDescription>
          </CardHeader>

          {loading ? (
            <CardContent>
              <div className="flex min-h-30 items-center justify-center">
                <LoadingSpinner className="h-8 w-8" />
              </div>
            </CardContent>
          ) : (
            <>
              <CardContent className="grid gap-3 md:grid-cols-4">
                <Input
                  type="date"
                  min={MIN_EXPENSE_DATE}
                  max={todayISO}
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
                <Input
                  type="date"
                  min={MIN_EXPENSE_DATE}
                  max={todayISO}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
                <select
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
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
                  onChange={(e) => setSort(e.target.value)}
                >
                  <option value="newest">Newest first</option>
                  <option value="oldest">Oldest first</option>
                </select>
              </CardContent>
              <CardContent className="flex items-center gap-3">
                <Button
                  className="bg-primary text-primary-foreground hover:bg-primary/90"
                  onClick={handleExport}
                  disabled={exporting || !!filterError}
                >
                  {exporting ? (
                    <>
                      <LoadingSpinner className="mr-2 h-4 w-4" />
                      Exporting...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" /> Export CSV
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleReset}
                  disabled={exporting}
                >
                  Reset
                </Button>
                {filterError && <p className="text-sm text-red-600">{filterError}</p>}
              </CardContent>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
