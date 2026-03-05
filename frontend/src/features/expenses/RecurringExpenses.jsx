import { useState, useEffect, useMemo, useCallback } from "react";
import { Plus, Trash2, Pencil, MessageSquare, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { EmptyState } from "@/components/EmptyState";
import { getCategoryBgClass } from "@/lib/category";
import { formatAmountDisplay, formatDisplayDate, formatAmountInput } from "@/lib/format";
import { getRecurringExpenses, deleteRecurringExpense, createRecurringExpense, updateRecurringExpense, patchRecurringActive, getCategories, getCurrentUser } from "@/lib/api";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { recurringExpenseFormSchema, recurringExpenseUpdateFormSchema, MIN_EXPENSE_DATE_ZOD } from "./expenseSchemas";
import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";

// Reusable pill toggle
function ActiveToggle({ checked, onChange, disabled }) {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
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

// ── Column layout shared between header and rows ─────────────────────────────
// Title | Category | Frequency | Next Due | Amount | Active | Actions
const COL = "grid grid-cols-[minmax(0,1.4fr)_minmax(0,0.9fr)_minmax(0,0.9fr)_minmax(0,0.9fr)_minmax(0,1fr)_80px_120px] items-center gap-x-2 px-3";

export default function RecurringExpenses({ onAddClick, onCountUpdate }) {
    const { t, i18n } = useTranslation();
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expenses, setExpenses] = useState([]);
    const [error, setError] = useState("");

    // Delete
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    // Add
    const [addOpen, setAddOpen] = useState(false);
    const [isAdding, setIsAdding] = useState(false);
    const [actionError, setActionError] = useState("");

    // Edit
    const [editOpen, setEditOpen] = useState(false);
    const [editTarget, setEditTarget] = useState(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editError, setEditError] = useState("");
    const [editTitle, setEditTitle] = useState("");
    const [editAmount, setEditAmount] = useState("");
    const [editCategory, setEditCategory] = useState("");
    const [editDescription, setEditDescription] = useState("");
    const [editIsActive, setEditIsActive] = useState(true);

    // Description preview
    const [descOpen, setDescOpen] = useState(false);
    const [descTarget, setDescTarget] = useState(null);

    // Inline toggle saving
    const [togglingId, setTogglingId] = useState(null);

    // Add form
    const [addTitle, setAddTitle] = useState("");
    const [addAmount, setAddAmount] = useState("");
    const [addCategory, setAddCategory] = useState("");
    const [addFrequency, setAddFrequency] = useState("MONTHLY");
    const [addStartDate, setAddStartDate] = useState("");
    const [addDescription, setAddDescription] = useState("");

    const [categories, setCategories] = useState([]);
    const [touchedAdd, setTouchedAdd] = useState({});
    const [touchedEdit, setTouchedEdit] = useState({});

    const [searchParams, setSearchParams] = useSearchParams();
    const [searchQuery, setSearchQuery] = useState(() => searchParams.get("r_search") || "");
    const [page, setPage] = useState(() => {
        const p = parseInt(searchParams.get("r_page"), 10);
        return p > 0 ? p : 1;
    });
    const PAGE_SIZE = 15;

    const tCategory = (name) => t(`categories.${name}`, { defaultValue: name });
    const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
    const todayISO = useMemo(() => toISODateInTimeZone(), []);
    const minStartDate = useMemo(() => {
        const parts = todayISO.split("-");
        if (parts.length < 2) return MIN_EXPENSE_DATE_ZOD;
        return `${parts[0]}-${parts[1]}-01`;
    }, [todayISO]);
    const filteredExpenses = useMemo(() => {
        const q = searchQuery.trim().toLowerCase();
        if (!q) return expenses;
        return expenses.filter((e) => e.title.toLowerCase().includes(q));
    }, [expenses, searchQuery]);
    const totalPages = Math.max(1, Math.ceil(filteredExpenses.length / PAGE_SIZE));
    const pagedExpenses = useMemo(
        () => filteredExpenses.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
        [filteredExpenses, page, PAGE_SIZE]
    );

    // Sync state to URL
    useEffect(() => {
        const next = new URLSearchParams();
        next.set("tab", "recurring");
        if (searchQuery.trim()) next.set("r_search", searchQuery.trim());
        if (page > 1) next.set("r_page", String(page));
        setSearchParams(next, { replace: true });
    }, [searchQuery, page, setSearchParams]);

    // Reset to page 1 when search changes (only if we're not already on page 1 to prevent loop)
    useEffect(() => {
        setPage(p => p !== 1 ? 1 : p);
    }, [searchQuery]);

    const loadExpenses = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const userRes = await getCurrentUser();
            setUser(userRes);
            if (!userRes?.is_premium) {
                setLoading(false);
                return;
            }
            const [data, catData] = await Promise.all([
                getRecurringExpenses(),
                getCategories()
            ]);
            setExpenses(data || []);
            setCategories(catData || []);
        } catch (e) {
            setError(e.message || t("recurring.loadFailed"));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadExpenses();
    }, [loadExpenses]);

    // Register the openAdd fn with the parent so the top-bar button can trigger it
    useEffect(() => {
        if (onAddClick) onAddClick(openAdd);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [onAddClick]);

    // Lift total expense count to parent for limit enforcement
    useEffect(() => {
        if (onCountUpdate) onCountUpdate(expenses.length);
    }, [expenses.length, onCountUpdate]);

    // Inline toggle — dedicated PATCH endpoint, no dialog needed
    const handleInlineToggle = useCallback(async (e, newValue) => {
        if (togglingId) return;
        setTogglingId(e.id);
        // Optimistic update
        setExpenses((prev) => prev.map((r) => r.id === e.id ? { ...r, is_active: newValue } : r));
        try {
            await patchRecurringActive(e.id, newValue);
        } catch (err) {
            // Rollback on failure
            setExpenses((prev) => prev.map((r) => r.id === e.id ? { ...r, is_active: e.is_active } : r));
            setError(err.message || t("recurring.toggleFailed"));
        } finally {
            setTogglingId(null);
        }
    }, [togglingId]);

    const handleDelete = async () => {
        if (isDeleting || !deleteTarget) return;
        try {
            setIsDeleting(true);
            await deleteRecurringExpense(deleteTarget.id);
            setDeleteOpen(false);
            await loadExpenses();
        } catch (e) {
            setError(e.message || t("recurring.deleteFailed"));
        } finally {
            setIsDeleting(false);
        }
    };

    const openDelete = (e) => { setDeleteTarget(e); setDeleteOpen(true); };

    const openAdd = () => {
        setActionError(""); setTouchedAdd({});
        setAddTitle(""); setAddAmount(""); setAddCategory("");
        setAddFrequency("MONTHLY"); setAddStartDate(todayISO); setAddDescription("");
        setAddOpen(true);
    };

    const openEdit = (e) => {
        setEditError(""); setEditTarget(e); setTouchedEdit({});
        setEditTitle(e.title);
        setEditAmount(formatAmountInput(String(e.amount)));
        setEditCategory(e.category);
        setEditDescription(e.description || "");
        setEditIsActive(e.is_active);
        setEditOpen(true);
    };

    const openDesc = (e) => { setDescTarget(e); setDescOpen(true); };

    const editExpenseParsed = useMemo(() => recurringExpenseUpdateFormSchema.safeParse({
        title: editTitle, amount: editAmount, category: editCategory, description: editDescription,
    }), [editTitle, editAmount, editCategory, editDescription]);

    const editErrors = useMemo(() => {
        if (editExpenseParsed.success) return {};
        const errors = {};
        editExpenseParsed.error.issues.forEach((issue) => {
            const field = issue.path[0];
            if (field && !errors[field] && touchedEdit[field]) {
                errors[field] = t(issue.message, { defaultValue: issue.message });
            }
        });
        return errors;
    }, [editExpenseParsed, t, touchedEdit]);

    const canSubmitEditExpense = editExpenseParsed.success && !isEditing;

    const handleEdit = async () => {
        if (isEditing || !editTarget) return;
        const parsed = editExpenseParsed;
        if (!parsed.success)
            return setEditError(parsed.error.issues[0]?.message || t("recurring.updateFailed"));
        try {
            setIsEditing(true);
            await updateRecurringExpense(editTarget.id, {
                title: parsed.data.title,
                amount: parsed.data.amount,
                category: parsed.data.category,
                description: parsed.data.description ?? null,
            });
            setEditOpen(false);
            await loadExpenses();
        } catch (e) {
            setEditError(localizeApiError(e.message, t) || e.message || t("recurring.updateFailed"));
        } finally {
            setIsEditing(false);
        }
    };

    const addExpenseParsed = useMemo(() => recurringExpenseFormSchema.safeParse({
        title: addTitle, amount: addAmount, category: addCategory,
        frequency: addFrequency, start_date: addStartDate, description: addDescription,
    }), [addTitle, addAmount, addCategory, addFrequency, addStartDate, addDescription]);

    const addErrors = useMemo(() => {
        if (addExpenseParsed.success) return {};
        const errors = {};
        addExpenseParsed.error.issues.forEach((issue) => {
            const field = issue.path[0];
            if (field && !errors[field] && touchedAdd[field]) {
                errors[field] = t(issue.message, { defaultValue: issue.message });
            }
        });
        return errors;
    }, [addExpenseParsed, t, touchedAdd]);

    const canSubmitAddExpense = addExpenseParsed.success && !isAdding;

    const handleAdd = async () => {
        if (isAdding) return;
        const parsed = addExpenseParsed;
        if (!parsed.success)
            return setActionError(parsed.error.issues[0]?.message || t("expenses.requestFailed"));
        try {
            setIsAdding(true);
            await createRecurringExpense({
                title: parsed.data.title, amount: parsed.data.amount,
                category: parsed.data.category, frequency: parsed.data.frequency,
                start_date: parsed.data.start_date, description: parsed.data.description ?? null,
            });
            setAddOpen(false);
            await loadExpenses();
        } catch (e) {
            setActionError(localizeApiError(e.message, t) || e.message || t("expenses.requestFailed"));
        } finally {
            setIsAdding(false);
        }
    };

    const selectTriggerClass = "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
    const selectContentClass = "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";
    const readonlyInputClass = "opacity-50 cursor-not-allowed pointer-events-none select-none";

    if (!user?.is_premium) {
        return (
            <Card className="shadow-sm">
                <CardContent className="min-h-80 flex flex-col items-center justify-center p-6 text-center space-y-4">
                    <div className="p-4 bg-amber-500/10 rounded-full mb-2"><span className="text-3xl">✨</span></div>
                    <h3 className="text-xl font-bold">{t("recurring.premiumTitle")}</h3>
                    <p className="text-muted-foreground max-w-sm">
                        {t("recurring.premiumDesc")}
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            <Card className="shadow-sm">
                <CardHeader>
                    <div className="space-y-2">
                        <CardTitle>{t("recurring.cardTitle")}</CardTitle>
                        <CardDescription>{t("recurring.cardDesc")}</CardDescription>
                    </div>
                </CardHeader>
                <CardContent className="min-h-80 pb-6">
                    {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
                    {/* Search bar — only shown once data is loaded and there are templates */}
                    {!loading && expenses.length > 0 && (
                        <div className="relative mb-4 max-w-xs">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder={t("expenses.search")}
                                className="w-full h-9 rounded-md border border-input bg-background pl-9 pr-3 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                            />
                        </div>
                    )}
                    <div className="overflow-x-auto">
                        <div className="min-w-[860px] space-y-0">
                            {/* Header row */}
                            <div className={`${COL} border-b border-border py-3 text-xs uppercase tracking-wide text-muted-foreground`}>
                                <div className="text-left">{t("recurring.templateTitle")}</div>
                                <div className="text-center">{t("expenses.category")}</div>
                                <div className="text-center">{t("recurring.frequency")}</div>
                                <div className="text-center">{t("recurring.nextDue")}</div>
                                <div className="text-right">{t("expenses.amountUzs")}</div>
                                <div className="text-center">{t("recurring.active")}</div>
                                <div className="text-right">{t("common.actions", { defaultValue: "Actions" })}</div>
                            </div>

                            {loading ? (
                                <div className="flex justify-center px-4 py-10">
                                    <LoadingSpinner className="h-6 w-6" />
                                </div>
                            ) : expenses.length === 0 ? (
                                <EmptyState inline description={t("recurring.emptyDesc")} />
                            ) : filteredExpenses.length === 0 ? (
                                <EmptyState inline description={t("recurring.noSearchResults", { defaultValue: "No templates match your search." })} />
                            ) : (
                                pagedExpenses.map((e) => (
                                    <div key={e.id} className={`${COL} border-b border-border py-3 hover:bg-muted/50 dark:hover:bg-muted/30 transition-colors`}>
                                        {/* Title */}
                                        <div className="min-w-0 self-center">
                                            <TooltipProvider delayDuration={0}>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <button
                                                            type="button"
                                                            className="max-w-full text-left truncate font-medium text-foreground outline-none focus-visible:underline decoration-muted-foreground underline-offset-4 cursor-pointer"
                                                            onClick={(e) => e.preventDefault()}
                                                        >
                                                            {e.title}
                                                        </button>
                                                    </TooltipTrigger>
                                                    <TooltipContent side="top" className="max-w-[250px] sm:max-w-xs break-words">
                                                        {e.title}
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        </div>

                                        {/* Category badge */}
                                        <div className="min-w-0 flex justify-center">
                                            <Badge variant="secondary" className={`max-w-full truncate ${getCategoryBgClass(e.category)}`}>
                                                {tCategory(e.category)}
                                            </Badge>
                                        </div>

                                        {/* Frequency */}
                                        <div className="text-center text-sm tabular-nums">
                                            {t(`recurring.${e.frequency.toLowerCase()}`, { defaultValue: e.frequency })}
                                        </div>

                                        {/* Next due */}
                                        <div className="text-center text-sm tabular-nums">{formatDisplayDate(e.next_due_date, appLang)}</div>

                                        {/* Amount */}
                                        <div className="text-right font-semibold tabular-nums">{formatAmountDisplay(e.amount)} UZS</div>

                                        {/* Active toggle (inline) */}
                                        <div className="flex justify-center">
                                            <ActiveToggle
                                                checked={e.is_active}
                                                onChange={(val) => handleInlineToggle(e, val)}
                                            />
                                        </div>

                                        {/* Actions */}
                                        <div className="flex justify-end gap-1">
                                            {/* Description button: always visible, dimmed when no description */}
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                title={e.description ? t("recurring.viewDescription") : t("recurring.noDescription")}
                                                disabled={!e.description}
                                                className={`h-8 px-2 text-xs hover:bg-muted/50 ${e.description ? "text-muted-foreground" : "text-muted-foreground/30"}`}
                                                onClick={() => openDesc(e)}
                                            >
                                                <MessageSquare className="h-3.5 w-3.5" />
                                            </Button>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                title={t("common.edit")}
                                                className="h-8 px-2 text-xs text-muted-foreground hover:bg-muted/50"
                                                onClick={() => openEdit(e)}
                                            >
                                                <Pencil className="h-3.5 w-3.5" />
                                            </Button>
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                title={t("common.delete")}
                                                className="h-8 px-2 text-xs text-destructive bg-destructive/10 hover:bg-destructive/20 hover:text-destructive"
                                                onClick={() => openDelete(e)}
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </Button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                    {/* Pagination footer */}
                    {!loading && totalPages > 1 && (
                        <div className="flex items-center justify-between pt-4 text-sm text-muted-foreground">
                            <span>{t("expenses.page")} {page} / {totalPages}</span>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                                    disabled={page <= 1}
                                >
                                    <ChevronLeft className="h-4 w-4 mr-1" />{t("expenses.prev")}
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                    disabled={page >= totalPages}
                                >
                                    {t("expenses.next")}<ChevronRight className="h-4 w-4 ml-1" />
                                </Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* ── Add Dialog ──────────────────────────────────────────────── */}
            <Dialog open={addOpen} onOpenChange={(open) => { setAddOpen(open); if (!open) setActionError(""); }}>
                <DialogContent className="py-8 border-border">
                    <DialogHeader className="space-y-3 pb-2">
                        <DialogTitle className="text-3xl font-bold tracking-tight">{t("recurring.addDialogTitle")}</DialogTitle>
                        <DialogDescription>{t("recurring.addDialogDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t("expenses.titleCol")}</label>
                            <div>
                                <Input value={addTitle}
                                    onChange={(e) => { setAddTitle(e.target.value); setTouchedAdd(p => ({ ...p, title: true })); }}
                                    onBlur={() => setTouchedAdd(p => ({ ...p, title: true }))}
                                    className={addErrors.title ? "border-red-500 focus-visible:border-red-500" : ""} />
                                {addErrors.title && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{addErrors.title}</p>}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t("expenses.amountUzs")}</label>
                            <div>
                                <Input type="text" inputMode="numeric" maxLength={19} value={addAmount}
                                    onChange={(e) => { setAddAmount(formatAmountInput(e.target.value)); setTouchedAdd(p => ({ ...p, amount: true })); }}
                                    onBlur={() => setTouchedAdd(p => ({ ...p, amount: true }))}
                                    onKeyDown={(e) => { if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") e.preventDefault(); }}
                                    className={addErrors.amount ? "border-red-500 focus-visible:border-red-500" : ""} />
                                {addErrors.amount && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{addErrors.amount}</p>}
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">{t("expenses.category")}</label>
                                <div>
                                    <Select value={addCategory || undefined} onValueChange={(v) => { setAddCategory(v); setTouchedAdd(p => ({ ...p, category: true })); }}>
                                        <SelectTrigger className={`${selectTriggerClass} ${addErrors.category ? "border-red-500 focus-visible:border-red-500" : ""}`} onBlur={() => setTouchedAdd(p => ({ ...p, category: true }))}>
                                            <SelectValue placeholder={t("expenses.selectCategory")} />
                                        </SelectTrigger>
                                        <SelectContent className={selectContentClass} position="popper" side="bottom">
                                            {categories.map((c) => <SelectItem key={c} value={c}>{tCategory(c)}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                    {addErrors.category && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{addErrors.category}</p>}
                                </div>
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">{t("recurring.frequency")}</label>
                                <Select value={addFrequency || undefined} onValueChange={setAddFrequency}>
                                    <SelectTrigger className={selectTriggerClass}><SelectValue placeholder={t("recurring.selectFrequency")} /></SelectTrigger>
                                    <SelectContent className={selectContentClass} position="popper" side="bottom">
                                        <SelectItem value="DAILY">{t("recurring.daily")}</SelectItem>
                                        <SelectItem value="WEEKLY">{t("recurring.weekly")}</SelectItem>
                                        <SelectItem value="MONTHLY">{t("recurring.monthly")}</SelectItem>
                                        <SelectItem value="YEARLY">{t("recurring.yearly")}</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t("recurring.startDate")}</label>
                            <div>
                                <Input type="date" min={minStartDate} value={addStartDate}
                                    onChange={(e) => { setAddStartDate(e.target.value); setTouchedAdd(p => ({ ...p, start_date: true })); }}
                                    onBlur={() => setTouchedAdd(p => ({ ...p, start_date: true }))}
                                    className={addErrors.start_date ? "border-red-500 focus-visible:border-red-500" : ""} />
                                {addErrors.start_date && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{addErrors.start_date}</p>}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})</label>
                            <div>
                                <Textarea
                                    className={`h-24 min-h-24 resize-none overflow-y-auto ${addErrors.description ? "border-red-500 focus-visible:border-red-500" : ""}`}
                                    value={addDescription}
                                    onChange={(e) => { setAddDescription(e.target.value); setTouchedAdd(p => ({ ...p, description: true })); }}
                                    onBlur={() => setTouchedAdd(p => ({ ...p, description: true }))}
                                />
                                {addErrors.description && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{addErrors.description}</p>}
                            </div>
                        </div>
                        {actionError && <p className="text-sm text-red-600">{t(actionError, { defaultValue: actionError })}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" disabled={isAdding} onClick={() => setAddOpen(false)}>{t("common.cancel")}</Button>
                        <Button className="relative min-w-[96px] disabled:pointer-events-auto disabled:cursor-not-allowed" disabled={!canSubmitAddExpense} onClick={handleAdd}>
                            {isAdding ? (
                                <><span className="invisible">{t("expenses.add")}</span>
                                    <span className="absolute inset-0 flex items-center justify-center">
                                        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                                    </span></>
                            ) : t("expenses.add")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Delete Confirm ──────────────────────────────────────────── */}
            <ConfirmDialog
                open={deleteOpen}
                onOpenChange={(open) => { if (!isDeleting) setDeleteOpen(open); }}
                title={t("recurring.deleteTitle")}
                description={t("recurring.deleteDesc")}
                confirmText={t("common.delete")}
                cancelText={t("common.cancel")}
                onConfirm={handleDelete}
                isDestructive={true}
                loading={isDeleting}
            />

            {/* ── Description Preview Modal ───────────────────────────────── */}
            <Dialog open={descOpen} onOpenChange={setDescOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{t("expenses.description")}</DialogTitle>
                        <DialogDescription>
                            {descTarget?.title || t("expenses.titleCol")}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap wrap-break-word rounded-md border border-border bg-muted/30 p-3 text-sm text-foreground">
                        {descTarget?.description || "___"}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDescOpen(false)}>
                            {t("common.cancel")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ── Edit Dialog ─────────────────────────────────────────────── */}
            <Dialog open={editOpen} onOpenChange={(open) => { setEditOpen(open); if (!open) setEditError(""); }}>
                <DialogContent className="py-8 border-border">
                    <DialogHeader className="space-y-3 pb-2">
                        <DialogTitle className="text-3xl font-bold tracking-tight">{t("recurring.editDialogTitle")}</DialogTitle>
                        <DialogDescription>{t("recurring.editDialogDesc")}</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-6">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t("expenses.titleCol")}</label>
                            <div>
                                <Input value={editTitle}
                                    onChange={(e) => { setEditTitle(e.target.value); setTouchedEdit(p => ({ ...p, title: true })); }}
                                    onBlur={() => setTouchedEdit(p => ({ ...p, title: true }))}
                                    className={editErrors.title ? "border-red-500 focus-visible:border-red-500" : ""} />
                                {editErrors.title && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{editErrors.title}</p>}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t("expenses.amountUzs")}</label>
                            <div>
                                <Input type="text" inputMode="numeric" maxLength={19} value={editAmount}
                                    onChange={(e) => { setEditAmount(formatAmountInput(e.target.value)); setTouchedEdit(p => ({ ...p, amount: true })); }}
                                    onBlur={() => setTouchedEdit(p => ({ ...p, amount: true }))}
                                    onKeyDown={(e) => { if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") e.preventDefault(); }}
                                    className={editErrors.amount ? "border-red-500 focus-visible:border-red-500" : ""} />
                                {editErrors.amount && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{editErrors.amount}</p>}
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">{t("expenses.category")}</label>
                                <div>
                                    <Select value={editCategory || undefined} onValueChange={(v) => { setEditCategory(v); setTouchedEdit(p => ({ ...p, category: true })); }}>
                                        <SelectTrigger className={`${selectTriggerClass} ${editErrors.category ? "border-red-500 focus-visible:border-red-500" : ""}`} onBlur={() => setTouchedEdit(p => ({ ...p, category: true }))}>
                                            <SelectValue placeholder={t("expenses.selectCategory")} />
                                        </SelectTrigger>
                                        <SelectContent className={selectContentClass} position="popper" side="bottom">
                                            {categories.map((c) => <SelectItem key={c} value={c}>{tCategory(c)}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                    {editErrors.category && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{editErrors.category}</p>}
                                </div>
                            </div>
                            {/* Frequency — read-only, greyed out */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-muted-foreground">{t("recurring.frequency")}</label>
                                <Input
                                    value={editTarget?.frequency ? t(`recurring.${editTarget.frequency.toLowerCase()}`, { defaultValue: editTarget.frequency }) : ""}
                                    disabled
                                    className="opacity-50 cursor-not-allowed"
                                />
                            </div>
                        </div>
                        {/* Start Date — read-only, greyed out */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">{t("recurring.startDate")}</label>
                            <Input
                                type="date"
                                value={editTarget?.start_date ?? ""}
                                disabled
                                className="opacity-50 cursor-not-allowed"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">{t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})</label>
                            <div>
                                <Textarea
                                    className={`h-24 min-h-24 resize-none overflow-y-auto ${editErrors.description ? "border-red-500 focus-visible:border-red-500" : ""}`}
                                    value={editDescription}
                                    onChange={(e) => { setEditDescription(e.target.value); setTouchedEdit(p => ({ ...p, description: true })); }}
                                    onBlur={() => setTouchedEdit(p => ({ ...p, description: true }))}
                                />
                                {editErrors.description && <p className="text-[11px] text-red-500 mt-0.5 font-medium ml-0.5">{editErrors.description}</p>}
                            </div>
                        </div>
                        {editError && <p className="text-sm text-red-600">{t(editError, { defaultValue: editError })}</p>}
                    </div>
                    <DialogFooter>
                        <Button variant="outline" disabled={isEditing} onClick={() => setEditOpen(false)}>{t("common.cancel")}</Button>
                        <Button className="relative min-w-[96px] disabled:pointer-events-auto disabled:cursor-not-allowed" disabled={!canSubmitEditExpense} onClick={handleEdit}>
                            {isEditing ? (
                                <><span className="invisible">{t("common.save")}</span>
                                    <span className="absolute inset-0 flex items-center justify-center">
                                        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                                    </span></>
                            ) : t("recurring.saveChanges")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
