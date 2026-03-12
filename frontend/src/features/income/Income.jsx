import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Plus, Pencil, Trash2, Landmark, MoreHorizontal, FileText, ArrowUpRight, ChevronLeft, ChevronRight, ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { formatAmountDisplay, formatAmountInput, formatDisplayDate, formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";
import { toISODateInTimeZone } from "@/lib/date";
import {
  useIncomeEntriesQuery,
  useIncomeMonthEntriesCountQuery,
  useIncomeMonthSummaryQuery,
  useIncomeSourcesQuery,
} from "./hooks/useIncomeQueries";
import {
  incomeEntryFormSchema,
  incomeSourceFormSchema,
  MAX_INCOME_AMOUNT,
  MAX_INCOME_NOTE_LENGTH,
  MAX_INCOME_SOURCE_NAME_LENGTH,
} from "./incomeSchemas";
import {
  useCreateIncomeEntryMutation,
  useCreateIncomeSourceMutation,
  useDeleteIncomeEntryMutation,
  useDeleteIncomeSourceMutation,
  useToggleIncomeSourceActiveMutation,
  useUpdateIncomeEntryMutation,
  useUpdateIncomeSourceMutation,
} from "./hooks/useIncomeMutations";

const MAX_INCOME_AMOUNT_DIGITS = String(MAX_INCOME_AMOUNT).length;
const MAX_INCOME_AMOUNT_INPUT_LENGTH = formatUzs(MAX_INCOME_AMOUNT).length;
const EMPTY_ARRAY = [];
const INCOME_ENTRIES_PAGE_SIZE = 10;
const MAX_INCOME_SOURCES = 20;
const MAX_INCOME_ENTRIES_PER_MONTH = 300;

function parsePageParam(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return 1;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

function ActiveToggle({ checked, onChange, disabled, ariaLabel }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${checked ? "bg-primary" : "bg-muted-foreground/30"
        }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${checked ? "translate-x-4" : "translate-x-0.5"
          }`}
      />
    </button>
  );
}

function parseAmountInput(value) {
  const digits = String(value || "").replace(/\s/g, "");
  return Number(digits || 0);
}

export default function Income() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const todayISO = useMemo(() => toISODateInTimeZone(), []);
  const monthStartISO = useMemo(() => `${todayISO.slice(0, 7)}-01`, [todayISO]);
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();

  const [sourceFilter, setSourceFilter] = useState(() => searchParams.get("source_id") || "all");
  const [startDate, setStartDate] = useState(() => searchParams.get("start_date") || "");
  const [endDate, setEndDate] = useState(() => searchParams.get("end_date") || "");
  const [page, setPage] = useState(() => parsePageParam(searchParams.get("page")));
  const [sourceActionError, setSourceActionError] = useState("");
  const [entryActionError, setEntryActionError] = useState("");
  const [sourceWriteLocked, setSourceWriteLocked] = useState(false);
  const [entryWriteLocked, setEntryWriteLocked] = useState(false);
  const sourceRateLimitTimeoutRef = useRef(null);
  const entryRateLimitTimeoutRef = useRef(null);

  const [addSourceOpen, setAddSourceOpen] = useState(false);
  const [editSourceOpen, setEditSourceOpen] = useState(false);
  const [deleteSourceOpen, setDeleteSourceOpen] = useState(false);
  const [sourceName, setSourceName] = useState("");
  const [sourceEditName, setSourceEditName] = useState("");
  const [touchedAddSource, setTouchedAddSource] = useState({});
  const [touchedEditSource, setTouchedEditSource] = useState({});
  const [selectedSource, setSelectedSource] = useState(null);

  const [addEntryOpen, setAddEntryOpen] = useState(false);
  const [editEntryOpen, setEditEntryOpen] = useState(false);
  const [deleteEntryOpen, setDeleteEntryOpen] = useState(false);
  const [entryMenuForId, setEntryMenuForId] = useState(null);
  const [entryMenuPosition, setEntryMenuPosition] = useState(null);
  const [sourceMenuForId, setSourceMenuForId] = useState(null);
  const [sourcesCollapsed, setSourcesCollapsed] = useState(false);
  const [entryNoteOpen, setEntryNoteOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [entryAmount, setEntryAmount] = useState("");
  const [entryDate, setEntryDate] = useState(todayISO);
  const [entrySourceId, setEntrySourceId] = useState("none");
  const [entryNote, setEntryNote] = useState("");
  const [touchedAddEntry, setTouchedAddEntry] = useState({});
  const [touchedEditEntry, setTouchedEditEntry] = useState({});

  const dateFilterError = useMemo(() => {
    if (!startDate && !endDate) return "";
    if (!startDate || !endDate) return t("income.filtersBothDates");
    if (startDate > endDate) return t("income.filtersStartAfterEnd");
    return "";
  }, [startDate, endDate, t]);

  const entryParams = useMemo(
    () => ({
      limit: INCOME_ENTRIES_PAGE_SIZE,
      skip: (page - 1) * INCOME_ENTRIES_PAGE_SIZE,
      source_id: sourceFilter !== "all" ? Number(sourceFilter) : undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    }),
    [endDate, page, sourceFilter, startDate]
  );
  const monthEntryCountParams = useMemo(
    () => ({
      limit: 1,
      skip: 0,
      start_date: monthStartISO,
      end_date: todayISO,
    }),
    [monthStartISO, todayISO]
  );

  const sourcesQuery = useIncomeSourcesQuery(true);
  const entriesQuery = useIncomeEntriesQuery(entryParams, !dateFilterError);
  const monthSummaryQuery = useIncomeMonthSummaryQuery();
  const monthEntriesCountQuery = useIncomeMonthEntriesCountQuery(monthEntryCountParams);

  const createSourceMutation = useCreateIncomeSourceMutation();
  const updateSourceMutation = useUpdateIncomeSourceMutation();
  const deleteSourceMutation = useDeleteIncomeSourceMutation();
  const toggleSourceActiveMutation = useToggleIncomeSourceActiveMutation();
  const createEntryMutation = useCreateIncomeEntryMutation();
  const updateEntryMutation = useUpdateIncomeEntryMutation();
  const deleteEntryMutation = useDeleteIncomeEntryMutation();

  const loading = sourcesQuery.isLoading || entriesQuery.isLoading;
  const entriesFetching = entriesQuery.isFetching;
  const sources = sourcesQuery.data || EMPTY_ARRAY;
  const entries = entriesQuery.data?.items || EMPTY_ARRAY;
  const totalEntries = Number(entriesQuery.data?.total || 0);
  const currentMonthEntryCount = Number(monthEntriesCountQuery.data?.total || 0);
  const sourceLimitReached = sources.length >= MAX_INCOME_SOURCES;
  const entryMonthLimitReached = currentMonthEntryCount >= MAX_INCOME_ENTRIES_PER_MONTH;
  const localizeSourceName = useCallback((name) => {
    const keyMap = {
      "Allowance": "income.defaultSources.allowance",
      "Scholarship": "income.defaultSources.scholarship",
      "Part-time work": "income.defaultSources.partTimeWork",
      "Salary": "income.defaultSources.salary",
      "Bonus": "income.defaultSources.bonus",
      "Side income": "income.defaultSources.sideIncome",
      "Client payment": "income.defaultSources.clientPayment",
      "Freelance work": "income.defaultSources.freelanceWork",
      "Project income": "income.defaultSources.projectIncome",
      "Business income": "income.defaultSources.businessIncome",
      "Other revenue": "income.defaultSources.otherRevenue",
      "Support": "income.defaultSources.support",
      "Temporary income": "income.defaultSources.temporaryIncome",
      "Other income": "income.defaultSources.otherIncome",
    };
    const key = keyMap[String(name || "")];
    return key ? t(key) : name;
  }, [t]);
  const sourceNameById = useMemo(
    () => new Map(sources.map((s) => [s.id, localizeSourceName(s.name)])),
    [sources, localizeSourceName]
  );

  const activeSources = useMemo(() => sources.filter((s) => s.is_active), [sources]);
  const sourceIds = useMemo(() => new Set(sources.map((source) => source.id)), [sources]);
  const entryIds = useMemo(() => new Set(entries.map((entry) => entry.id)), [entries]);

  const monthIncomeTotal = Number(monthSummaryQuery.data?.income || 0);

  const firstError =
    localizeApiError(
      sourcesQuery.error?.message || entriesQuery.error?.message || monthEntriesCountQuery.error?.message,
      t
    ) ||
    sourcesQuery.error?.message ||
    entriesQuery.error?.message ||
    monthEntriesCountQuery.error?.message ||
    "";

  const addSourceParsed = useMemo(
    () => incomeSourceFormSchema.safeParse({ name: sourceName }),
    [sourceName]
  );

  const editSourceParsed = useMemo(
    () => incomeSourceFormSchema.safeParse({ name: sourceEditName }),
    [sourceEditName]
  );

  const entryParsed = useMemo(
    () =>
      incomeEntryFormSchema.safeParse({
        amount: entryAmount,
        date: entryDate,
        note: entryNote,
      }),
    [entryAmount, entryDate, entryNote]
  );

  const getLiveErrors = useCallback((parsed, touched) => {
    if (parsed.success) return {};
    const errs = {};
    parsed.error.issues.forEach((issue) => {
      const field = issue.path?.[0];
      if (!field || errs[field] || !touched[field]) return;
      errs[field] = t(issue.message, { defaultValue: issue.message });
    });
    return errs;
  }, [t]);

  const addSourceErrors = useMemo(
    () => getLiveErrors(addSourceParsed, touchedAddSource),
    [addSourceParsed, getLiveErrors, touchedAddSource]
  );
  const editSourceErrors = useMemo(
    () => getLiveErrors(editSourceParsed, touchedEditSource),
    [editSourceParsed, getLiveErrors, touchedEditSource]
  );
  const addEntryErrors = useMemo(
    () => getLiveErrors(entryParsed, touchedAddEntry),
    [entryParsed, getLiveErrors, touchedAddEntry]
  );
  const editEntryErrors = useMemo(
    () => getLiveErrors(entryParsed, touchedEditEntry),
    [entryParsed, getLiveErrors, touchedEditEntry]
  );

  const canSubmitAddSource = addSourceParsed.success && !createSourceMutation.isPending && !sourceLimitReached && !sourceWriteLocked;
  const canSubmitEditSource = editSourceParsed.success && !updateSourceMutation.isPending && !!selectedSource && !sourceWriteLocked;
  const canSubmitAddEntry = entryParsed.success && !createEntryMutation.isPending && !entryMonthLimitReached && !entryWriteLocked;
  const canSubmitEditEntry = entryParsed.success && !updateEntryMutation.isPending && !!selectedEntry && !entryWriteLocked;

  const armWriteRateLimitLock = useCallback((scope, retryAfterSeconds) => {
    const waitMs = Math.max(1000, Math.ceil(Number(retryAfterSeconds || 1) * 1000));
    if (scope === "source") {
      if (sourceRateLimitTimeoutRef.current) clearTimeout(sourceRateLimitTimeoutRef.current);
      setSourceWriteLocked(true);
      sourceRateLimitTimeoutRef.current = window.setTimeout(() => {
        setSourceWriteLocked(false);
        sourceRateLimitTimeoutRef.current = null;
      }, waitMs);
      return;
    }
    if (entryRateLimitTimeoutRef.current) clearTimeout(entryRateLimitTimeoutRef.current);
    setEntryWriteLocked(true);
    entryRateLimitTimeoutRef.current = window.setTimeout(() => {
      setEntryWriteLocked(false);
      entryRateLimitTimeoutRef.current = null;
    }, waitMs);
  }, []);

  useEffect(() => {
    const next = new URLSearchParams();
    if (sourceFilter !== "all") next.set("source_id", sourceFilter);
    if (startDate) next.set("start_date", startDate);
    if (endDate) next.set("end_date", endDate);
    if (page > 1) next.set("page", String(page));
    setSearchParams(next, { replace: true });
  }, [endDate, page, setSearchParams, sourceFilter, startDate]);

  useEffect(() => {
    const onPointerDown = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("[data-action-popover]")) return;
      setEntryMenuForId(null);
      setEntryMenuPosition(null);
      setSourceMenuForId(null);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  useEffect(() => () => {
    if (sourceRateLimitTimeoutRef.current) clearTimeout(sourceRateLimitTimeoutRef.current);
    if (entryRateLimitTimeoutRef.current) clearTimeout(entryRateLimitTimeoutRef.current);
  }, []);

  const resetEntryForm = () => {
    setEntryAmount("");
    setEntryDate(todayISO);
    setEntrySourceId("none");
    setEntryNote("");
  };

  const openAddSource = () => {
    setSourceActionError("");
    setSourceName("");
    setTouchedAddSource({});
    setAddSourceOpen(true);
  };

  const openEditSource = (source) => {
    setSourceActionError("");
    setSelectedSource(source);
    setSourceEditName(source.name || "");
    setTouchedEditSource({});
    setEditSourceOpen(true);
  };

  const openAddEntry = () => {
    setEntryActionError("");
    resetEntryForm();
    setTouchedAddEntry({});
    setAddEntryOpen(true);
  };

  const openEditEntry = (entry) => {
    setEntryActionError("");
    setSelectedEntry(entry);
    setEntryAmount(formatAmountInput(String(entry.amount || ""), MAX_INCOME_AMOUNT_DIGITS));
    setEntryDate(entry.date || todayISO);
    setEntrySourceId(entry.source_id ? String(entry.source_id) : "none");
    setEntryNote(entry.note || "");
    setTouchedEditEntry({});
    setEditEntryOpen(true);
  };

  const openDeleteEntry = (entry) => {
    setEntryActionError("");
    setSelectedEntry(entry);
    setDeleteEntryOpen(true);
  };

  const openEntryActions = (event, entry) => {
    setEntryActionError("");
    setSelectedEntry(entry);
    setSourceMenuForId(null);
    const button = event.currentTarget;
    const rect = button instanceof HTMLElement ? button.getBoundingClientRect() : null;
    const menuWidth = 176;
    const menuHeight = 120;
    const viewportPadding = 8;
    setEntryMenuForId((prev) => {
      if (prev === entry.id) {
        setEntryMenuPosition(null);
        return null;
      }
      if (!rect) return null;
      const fitsBelow = rect.bottom + 6 + menuHeight <= window.innerHeight - viewportPadding;
      const top = fitsBelow ? rect.bottom + 6 : rect.top - 6 - menuHeight;
      const left = Math.max(
        viewportPadding,
        Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - viewportPadding)
      );
      setEntryMenuPosition({ top, left });
      return entry.id;
    });
  };

  const openEntryNote = (entry) => {
    setSelectedEntry(entry);
    setEntryMenuForId(null);
    setEntryMenuPosition(null);
    setEntryNoteOpen(true);
  };

  const openDeleteSource = (source) => {
    setSourceActionError("");
    setSelectedSource(source);
    setSourceMenuForId(null);
    setDeleteSourceOpen(true);
  };

  const getRequestError = (e, fallbackKey = "income.requestFailed") =>
    localizeApiError(e?.message, t) || e?.message || t(fallbackKey);

  const handleCreateSource = async () => {
    if (createSourceMutation.isPending) return;
    if (!addSourceParsed.success) {
      setTouchedAddSource({ name: true });
      const firstIssue = addSourceParsed.error.issues[0];
      if (firstIssue?.message) setSourceActionError(t(firstIssue.message, { defaultValue: firstIssue.message }));
      return;
    }
    try {
      await createSourceMutation.mutateAsync({ name: sourceName.trim() });
      setAddSourceOpen(false);
    } catch (e) {
      const message = getRequestError(e);
      setSourceActionError(message);
      if (e?.status === 429) armWriteRateLimitLock("source", e?.retryAfterSeconds);
    }
  };

  const handleUpdateSource = async () => {
    if (updateSourceMutation.isPending || !selectedSource) return;
    if (!editSourceParsed.success) {
      setTouchedEditSource({ name: true });
      const firstIssue = editSourceParsed.error.issues[0];
      if (firstIssue?.message) setSourceActionError(t(firstIssue.message, { defaultValue: firstIssue.message }));
      return;
    }
    try {
      await updateSourceMutation.mutateAsync({
        sourceId: selectedSource.id,
        payload: { name: sourceEditName.trim() },
      });
      setEditSourceOpen(false);
    } catch (e) {
      const message = getRequestError(e);
      setSourceActionError(message);
      if (e?.status === 429) armWriteRateLimitLock("source", e?.retryAfterSeconds);
    }
  };

  const handleToggleSourceActive = async (source) => {
    if (toggleSourceActiveMutation.isPending) return;
    try {
      await toggleSourceActiveMutation.mutateAsync({
        sourceId: source.id,
        isActive: !source.is_active,
      });
    } catch (e) {
      setSourceActionError(getRequestError(e));
      if (e?.status === 429) armWriteRateLimitLock("source", e?.retryAfterSeconds);
    }
  };

  const handleDeleteSource = async () => {
    if (deleteSourceMutation.isPending || !selectedSource) return;
    try {
      await deleteSourceMutation.mutateAsync(selectedSource.id);
      setDeleteSourceOpen(false);
    } catch (e) {
      const message = getRequestError(e);
      setSourceActionError(message);
      if (e?.status === 429) armWriteRateLimitLock("source", e?.retryAfterSeconds);
    }
  };

  const buildEntryPayload = () => ({
    amount: parseAmountInput(entryAmount),
    date: entryDate,
    note: entryNote.trim() || null,
    source_id: entrySourceId === "none" ? null : Number(entrySourceId),
  });

  const handleCreateEntry = async () => {
    if (createEntryMutation.isPending) return;
    if (!entryParsed.success) {
      setTouchedAddEntry({ amount: true, date: true, note: true });
      const firstIssue = entryParsed.error.issues[0];
      if (firstIssue?.message) setEntryActionError(t(firstIssue.message, { defaultValue: firstIssue.message }));
      return;
    }
    try {
      await createEntryMutation.mutateAsync(buildEntryPayload());
      setAddEntryOpen(false);
    } catch (e) {
      const message = getRequestError(e);
      setEntryActionError(message);
      if (e?.status === 429) armWriteRateLimitLock("entry", e?.retryAfterSeconds);
    }
  };

  const handleUpdateEntry = async () => {
    if (updateEntryMutation.isPending || !selectedEntry) return;
    if (!entryParsed.success) {
      setTouchedEditEntry({ amount: true, date: true, note: true });
      const firstIssue = entryParsed.error.issues[0];
      if (firstIssue?.message) setEntryActionError(t(firstIssue.message, { defaultValue: firstIssue.message }));
      return;
    }
    try {
      await updateEntryMutation.mutateAsync({
        entryId: selectedEntry.id,
        payload: buildEntryPayload(),
      });
      setEditEntryOpen(false);
    } catch (e) {
      const message = getRequestError(e);
      setEntryActionError(message);
      if (e?.status === 429) armWriteRateLimitLock("entry", e?.retryAfterSeconds);
    }
  };

  const handleDeleteEntry = async () => {
    if (deleteEntryMutation.isPending || !selectedEntry) return;
    try {
      await deleteEntryMutation.mutateAsync(selectedEntry.id);
      setDeleteEntryOpen(false);
    } catch (e) {
      const message = getRequestError(e);
      setEntryActionError(message);
      if (e?.status === 429) armWriteRateLimitLock("entry", e?.retryAfterSeconds);
    }
  };

  const handleResetFilters = () => {
    setSourceFilter("all");
    setStartDate("");
    setEndDate("");
    setPage(1);
    setEntryMenuForId(null);
    setEntryMenuPosition(null);
    setSourceMenuForId(null);
  };

  const goPrevPage = () => {
    if (page <= 1 || loading || entriesFetching) return;
    setPage((current) => Math.max(1, current - 1));
  };

  const totalPages = Math.ceil(totalEntries / INCOME_ENTRIES_PAGE_SIZE);

  const goNextPage = () => {
    if (page >= (totalPages || 1) || loading || entriesFetching) return;
    setPage((current) => current + 1);
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-6">
        <PageHeader title={t("income.title")} description={t("income.subtitle")}>
          <Button
            variant="outline"
            onClick={openAddSource}
            disabled={sourceLimitReached || sourceWriteLocked}
            title={sourceLimitReached ? t("income.sourceLimitReached") : sourceWriteLocked ? t("income.sourcesTooManySoon") : undefined}
          >
            <Landmark className="mr-2 h-4 w-4" /> {t("income.addSource")}
          </Button>
          <Button
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            onClick={openAddEntry}
            disabled={entryMonthLimitReached || entryWriteLocked}
            title={entryMonthLimitReached ? t("income.entryMonthLimitReached") : entryWriteLocked ? t("income.entriesTooManySoon") : undefined}
          >
            <Plus className="mr-2 h-4 w-4" /> {t("income.addEntry")}
          </Button>
        </PageHeader>

        {firstError ? <p className="text-sm text-red-600">{firstError}</p> : null}

        <div className="grid gap-4 md:grid-cols-3">
          <Card className="shadow-sm md:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t("income.filtersTitle")}</CardTitle>
              <CardDescription>{t("income.filtersDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="pt-0 grid gap-3 md:grid-cols-4">
              <Input
                type="date"
                max={todayISO}
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  setPage(1);
                  setEntryMenuForId(null);
                  setEntryMenuPosition(null);
                  setSourceMenuForId(null);
                }}
              />
              <Input
                type="date"
                max={todayISO}
                value={endDate}
                onChange={(e) => {
                  setEndDate(e.target.value);
                  setPage(1);
                  setEntryMenuForId(null);
                  setEntryMenuPosition(null);
                  setSourceMenuForId(null);
                }}
              />
              <Select
                value={sourceFilter}
                onValueChange={(value) => {
                  setSourceFilter(value);
                  setPage(1);
                  setEntryMenuForId(null);
                  setEntryMenuPosition(null);
                  setSourceMenuForId(null);
                }}
              >
                <SelectTrigger className="w-full min-w-0">
                  <SelectValue className="truncate" />
                </SelectTrigger>
                <SelectContent position="popper" side="bottom" align="start" sideOffset={6}>
                  <SelectItem value="all">{t("income.allSources")}</SelectItem>
                  {sources.map((source) => (
                    <SelectItem key={source.id} value={String(source.id)}>
                      <span className="block max-w-[20rem] truncate" title={localizeSourceName(source.name)}>
                        {localizeSourceName(source.name)}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="outline"
                onClick={handleResetFilters}
                disabled={sourceFilter === "all" && !startDate && !endDate}
              >
                {t("common.reset")}
              </Button>
              {dateFilterError ? (
                <p className="md:col-span-4 text-sm text-red-600">{dateFilterError}</p>
              ) : null}
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{t("income.thisMonthTotal")}</CardTitle>
              <CardDescription>{t("income.thisMonthTotalDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              {monthSummaryQuery.isLoading ? (
                <div className="flex min-h-10 items-center">
                  <LoadingSpinner className="h-5 w-5" />
                </div>
              ) : (
                <p className="text-2xl font-semibold tabular-nums">{formatAmountDisplay(monthIncomeTotal)} UZS</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-start justify-between gap-3 pb-3">
            <div className="space-y-1.5">
              <CardTitle>{t("income.sourcesTitle")}</CardTitle>
              <CardDescription>
                {sourcesCollapsed
                  ? `${sources.length} ${t("income.sourcesTitle").toLowerCase()}`
                  : t("income.sourcesDesc")}
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-10 w-10 shrink-0 rounded-lg"
              aria-label={sourcesCollapsed ? `Expand ${t("income.sourcesTitle")}` : `Collapse ${t("income.sourcesTitle")}`}
              onClick={() => setSourcesCollapsed((current) => !current)}
            >
              <ChevronDown
                className={`h-5 w-5 transition-transform duration-200 ${sourcesCollapsed ? "-rotate-90" : "rotate-0"}`}
              />
            </Button>
          </CardHeader>
          <CardContent className={`pt-0 ${sourcesCollapsed ? "hidden" : ""}`}>
            {loading ? (
              <div className="flex min-h-[80px] items-center justify-center">
                <LoadingSpinner className="h-6 w-6" />
              </div>
            ) : sources.length === 0 ? (
              <EmptyState inline description={t("income.noSources")} />
            ) : (
              <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                {sources.map((source) => (
                  <div
                    key={source.id}
                    className="rounded-lg border border-border p-3 flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <p className="font-medium truncate">{localizeSourceName(source.name)}</p>
                      <p className="text-xs text-muted-foreground">
                        {source.is_active ? t("income.active") : t("income.inactive")}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <ActiveToggle
                        checked={source.is_active}
                        disabled={toggleSourceActiveMutation.isPending || sourceWriteLocked}
                        onChange={() => handleToggleSourceActive(source)}
                        ariaLabel={t("income.toggleSource")}
                      />
                      <div className="relative" data-action-popover>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            setEntryMenuForId(null);
                            setEntryMenuPosition(null);
                            setSourceMenuForId((prev) => (prev === source.id ? null : source.id));
                          }}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                        {sourceMenuForId === source.id && sourceIds.has(sourceMenuForId) && (
                          <div className="absolute right-0 top-full mt-1 z-30 w-44 rounded-md border border-border bg-popover p-1 shadow-lg">
                            <button
                              type="button"
                              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                              onClick={() => {
                                setSourceMenuForId(null);
                                openEditSource(source);
                              }}
                            >
                              <Pencil className="h-4 w-4" /> {t("common.edit")}
                            </button>
                            <button
                              type="button"
                              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-destructive/10"
                              onClick={() => openDeleteSource(source)}
                            >
                              <Trash2 className="h-4 w-4" /> {t("common.delete")}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle>{t("income.entriesTitle")}</CardTitle>
            <CardDescription>{t("income.entriesDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            {loading ? (
              <div className="flex min-h-[120px] items-center justify-center">
                <LoadingSpinner className="h-6 w-6" />
              </div>
            ) : entries.length === 0 ? (
              <EmptyState inline description={t("income.noEntries")} />
            ) : (
              <div
                className="overflow-x-auto"
                onScroll={() => {
                  if (entryMenuForId) {
                    setEntryMenuForId(null);
                    setEntryMenuPosition(null);
                  }
                }}
              >
                <div className="min-w-[760px] space-y-0">
                  <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.35fr)] gap-2 border-b border-border px-2 py-3 text-xs uppercase tracking-wide text-muted-foreground">
                    <div>{t("income.source")}</div>
                    <div>{t("income.date")}</div>
                    <div className="text-right">{t("income.amount")}</div>
                    <div className="text-right" />
                  </div>
                  {entries.map((entry) => (
                    <div
                      key={entry.id}
                      className="grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,0.35fr)] gap-2 border-b border-border px-2 py-3 items-center rounded-lg transition-all duration-300 hover:bg-muted/50 dark:hover:bg-muted/30"
                    >
                      <div className="text-sm truncate">
                        {entry.source_id ? sourceNameById.get(entry.source_id) || t("income.sourceDeleted") : t("income.noSource")}
                      </div>
                      <div className="text-sm">{formatDisplayDate(entry.date, appLang)}</div>
                      <div className="flex items-center justify-end gap-1.5 text-right font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
                        <ArrowUpRight className="h-4 w-4 shrink-0" />
                        <span>{formatAmountDisplay(entry.amount)} UZS</span>
                      </div>
                      <div className="relative flex justify-end" data-action-popover>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={(event) => openEntryActions(event, entry)}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {!loading && entries.length > 0 ? (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {t("expenses.page")} {page} / {totalPages || 1}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1 || loading || entriesFetching}
                    onClick={goPrevPage}
                  >
                    <ChevronLeft className="mr-1 h-4 w-4" /> {t("expenses.prev")}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= (totalPages || 1) || loading || entriesFetching}
                    onClick={goNextPage}
                  >
                    {t("expenses.next")} <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {entryMenuForId && entryIds.has(entryMenuForId) && entryMenuPosition && selectedEntry
        ? createPortal(
          <div
            data-action-popover
            className="fixed z-50 w-44 rounded-md border border-border bg-popover p-1 shadow-lg"
            style={{ top: `${entryMenuPosition.top}px`, left: `${entryMenuPosition.left}px` }}
          >
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
              onClick={() => openEntryNote(selectedEntry)}
            >
              <FileText className="h-4 w-4" /> {t("income.viewNote")}
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
              onClick={() => {
                setEntryMenuForId(null);
                setEntryMenuPosition(null);
                openEditEntry(selectedEntry);
              }}
            >
              <Pencil className="h-4 w-4" /> {t("common.edit")}
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-destructive hover:bg-destructive/10"
              onClick={() => {
                setEntryMenuForId(null);
                setEntryMenuPosition(null);
                openDeleteEntry(selectedEntry);
              }}
            >
              <Trash2 className="h-4 w-4" /> {t("common.delete")}
            </button>
          </div>,
          document.body
        )
        : null}

      <Dialog open={addSourceOpen} onOpenChange={setAddSourceOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("income.addSourceTitle")}</DialogTitle>
            <DialogDescription>{t("income.addSourceDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("income.sourceName")}</label>
            <Input
              value={sourceName}
              maxLength={MAX_INCOME_SOURCE_NAME_LENGTH}
              onChange={(e) => {
                setSourceName(e.target.value);
                setTouchedAddSource((prev) => ({ ...prev, name: true }));
              }}
              placeholder={t("income.sourceNamePlaceholder")}
            />
            {addSourceErrors.name ? <p className="text-xs text-red-600">{addSourceErrors.name}</p> : null}
            {sourceActionError ? <p className="text-xs text-red-600">{t(sourceActionError, { defaultValue: sourceActionError })}</p> : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddSourceOpen(false)} disabled={createSourceMutation.isPending}>
              {t("common.cancel")}
            </Button>
            <Button
              className="relative min-w-24 disabled:pointer-events-auto disabled:cursor-not-allowed"
              onClick={handleCreateSource}
              disabled={!canSubmitAddSource}
            >
              {createSourceMutation.isPending ? (
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

      <Dialog open={editSourceOpen} onOpenChange={setEditSourceOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("income.editSourceTitle")}</DialogTitle>
            <DialogDescription>{t("income.editSourceDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-sm font-medium">{t("income.sourceName")}</label>
            <Input
              value={sourceEditName}
              maxLength={MAX_INCOME_SOURCE_NAME_LENGTH}
              onChange={(e) => {
                setSourceEditName(e.target.value);
                setTouchedEditSource((prev) => ({ ...prev, name: true }));
              }}
            />
            {editSourceErrors.name ? <p className="text-xs text-red-600">{editSourceErrors.name}</p> : null}
            {sourceActionError ? <p className="text-xs text-red-600">{t(sourceActionError, { defaultValue: sourceActionError })}</p> : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditSourceOpen(false)} disabled={updateSourceMutation.isPending}>
              {t("common.cancel")}
            </Button>
            <Button
              className="relative min-w-24 disabled:pointer-events-auto disabled:cursor-not-allowed"
              onClick={handleUpdateSource}
              disabled={!canSubmitEditSource}
            >
              {updateSourceMutation.isPending ? (
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

      <ConfirmDialog
        open={deleteSourceOpen}
        onOpenChange={setDeleteSourceOpen}
        title={t("income.deleteSourceTitle")}
        description={t("income.deleteSourceDesc", {
          source: selectedSource ? localizeSourceName(selectedSource.name) : "",
        })}
        onConfirm={handleDeleteSource}
        confirmText={t("common.delete")}
        cancelText={t("common.cancel")}
        isConfirming={deleteSourceMutation.isPending}
        confirmDisabled={sourceWriteLocked}
        error={sourceActionError ? t(sourceActionError, { defaultValue: sourceActionError }) : ""}
      />

      <Dialog open={addEntryOpen} onOpenChange={setAddEntryOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("income.addEntryTitle")}</DialogTitle>
            <DialogDescription>{t("income.addEntryDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.amountUzs")}</label>
              <Input
                type="text"
                inputMode="numeric"
                maxLength={MAX_INCOME_AMOUNT_INPUT_LENGTH}
                value={entryAmount}
                onChange={(e) => {
                  setEntryAmount(formatAmountInput(e.target.value, MAX_INCOME_AMOUNT_DIGITS));
                  setTouchedAddEntry((prev) => ({ ...prev, amount: true }));
                }}
              />
              {addEntryErrors.amount ? <p className="text-xs text-red-600">{addEntryErrors.amount}</p> : null}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.source")}</label>
              <Select value={entrySourceId} onValueChange={setEntrySourceId}>
                <SelectTrigger className="w-full min-w-0">
                  <SelectValue className="truncate" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t("income.noSource")}</SelectItem>
                  {activeSources.map((source) => (
                    <SelectItem key={source.id} value={String(source.id)}>
                      <span className="block max-w-[20rem] truncate" title={localizeSourceName(source.name)}>
                        {localizeSourceName(source.name)}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.date")}</label>
              <Input
                type="date"
                min={monthStartISO}
                max={todayISO}
                value={entryDate}
                onChange={(e) => {
                  setEntryDate(e.target.value);
                  setTouchedAddEntry((prev) => ({ ...prev, date: true }));
                }}
              />
              {addEntryErrors.date ? <p className="text-xs text-red-600">{addEntryErrors.date}</p> : null}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.note")}</label>
              <Input
                value={entryNote}
                maxLength={MAX_INCOME_NOTE_LENGTH}
                placeholder={t("income.notePlaceholder")}
                onChange={(e) => {
                  setEntryNote(e.target.value);
                  setTouchedAddEntry((prev) => ({ ...prev, note: true }));
                }}
              />
              {addEntryErrors.note ? <p className="text-xs text-red-600">{addEntryErrors.note}</p> : null}
            </div>
            {entryActionError ? <p className="text-xs text-red-600">{t(entryActionError, { defaultValue: entryActionError })}</p> : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddEntryOpen(false)} disabled={createEntryMutation.isPending}>
              {t("common.cancel")}
            </Button>
            <Button
              className="relative min-w-24 disabled:pointer-events-auto disabled:cursor-not-allowed"
              onClick={handleCreateEntry}
              disabled={!canSubmitAddEntry}
            >
              {createEntryMutation.isPending ? (
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

      <Dialog open={editEntryOpen} onOpenChange={setEditEntryOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("income.editEntryTitle")}</DialogTitle>
            <DialogDescription>{t("income.editEntryDesc")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.amountUzs")}</label>
              <Input
                type="text"
                inputMode="numeric"
                maxLength={MAX_INCOME_AMOUNT_INPUT_LENGTH}
                value={entryAmount}
                onChange={(e) => {
                  setEntryAmount(formatAmountInput(e.target.value, MAX_INCOME_AMOUNT_DIGITS));
                  setTouchedEditEntry((prev) => ({ ...prev, amount: true }));
                }}
              />
              {editEntryErrors.amount ? <p className="text-xs text-red-600">{editEntryErrors.amount}</p> : null}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.source")}</label>
              <Select value={entrySourceId} onValueChange={setEntrySourceId}>
                <SelectTrigger className="w-full min-w-0">
                  <SelectValue className="truncate" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{t("income.noSource")}</SelectItem>
                  {activeSources.map((source) => (
                    <SelectItem key={source.id} value={String(source.id)}>
                      <span className="block max-w-[20rem] truncate" title={localizeSourceName(source.name)}>
                        {localizeSourceName(source.name)}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.date")}</label>
              <Input
                type="date"
                min={monthStartISO}
                max={todayISO}
                value={entryDate}
                onChange={(e) => {
                  setEntryDate(e.target.value);
                  setTouchedEditEntry((prev) => ({ ...prev, date: true }));
                }}
              />
              {editEntryErrors.date ? <p className="text-xs text-red-600">{editEntryErrors.date}</p> : null}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t("income.note")}</label>
              <Input
                value={entryNote}
                maxLength={MAX_INCOME_NOTE_LENGTH}
                placeholder={t("income.notePlaceholder")}
                onChange={(e) => {
                  setEntryNote(e.target.value);
                  setTouchedEditEntry((prev) => ({ ...prev, note: true }));
                }}
              />
              {editEntryErrors.note ? <p className="text-xs text-red-600">{editEntryErrors.note}</p> : null}
            </div>
            {entryActionError ? <p className="text-xs text-red-600">{t(entryActionError, { defaultValue: entryActionError })}</p> : null}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditEntryOpen(false)} disabled={updateEntryMutation.isPending}>
              {t("common.cancel")}
            </Button>
            <Button
              className="relative min-w-24 disabled:pointer-events-auto disabled:cursor-not-allowed"
              onClick={handleUpdateEntry}
              disabled={!canSubmitEditEntry}
            >
              {updateEntryMutation.isPending ? (
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

      <Dialog open={entryNoteOpen} onOpenChange={setEntryNoteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("income.noteTitle")}</DialogTitle>
            <DialogDescription>{t("income.note")}</DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-border bg-muted/30 p-3 text-sm text-foreground">
            {selectedEntry?.note?.trim() ? selectedEntry.note : t("income.noNote")}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEntryNoteOpen(false)}>
              {t("common.close")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteEntryOpen}
        onOpenChange={setDeleteEntryOpen}
        title={t("income.deleteEntryTitle")}
        description={t("income.deleteEntryDesc")}
        onConfirm={handleDeleteEntry}
        confirmText={t("common.delete")}
        cancelText={t("common.cancel")}
        isConfirming={deleteEntryMutation.isPending}
        confirmDisabled={entryWriteLocked}
        error={entryActionError ? t(entryActionError, { defaultValue: entryActionError }) : ""}
      />
    </div>
  );
}
