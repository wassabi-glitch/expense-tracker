// Final UI refinement and stability check - v1.0.1
import * as React from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
    Plus, Trash2, Pencil, MessageSquare, Search,
    ChevronLeft, ChevronRight, Circle, MoreHorizontal, Crown, FileText
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { TitleTooltip } from "@/components/TitleTooltip";
import { EmptyState } from "@/components/EmptyState";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { categoryIconMap, getCategoryBgClass, getCategoryColorClass, CATEGORIES } from "@/lib/category";
import { cn } from "@/lib/utils";
import { formatDisplayDate, formatAmountInput, formatMonthYear } from "@/lib/format";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { recurringExpenseFormSchema, recurringExpenseUpdateFormSchema, MIN_EXPENSE_DATE_ZOD } from "./expenseSchemas";
import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import { useRecurringDataQuery } from "./hooks/useRecurringDataQuery";
import { useRecurringCategoriesQuery } from "./hooks/useRecurringCategoriesQuery";
import {
    useCreateRecurringMutation,
    useDeleteRecurringMutation,
    useToggleRecurringMutation,
    useUpdateRecurringMutation,
} from "./hooks/useRecurringMutations";

import i18n from "../../i18n";

// Helper for localized date display, defined outside component to avoid closure/HMR issues
const _getAppLang = () => String(i18n.language || i18n.resolvedLanguage || "en").toLowerCase();
const _formatDisplayDateLocal = (dateStr) => formatDisplayDate(dateStr, _getAppLang());



// ── Column layout shared between header and rows ─────────────────────────────
// Title | Category | Frequency | Next Due | Amount | Active | Actions
const COL = "grid grid-cols-[minmax(0,1.75fr)_minmax(0,1.25fr)_minmax(0,1.05fr)_minmax(0,1.15fr)_minmax(0,1fr)_minmax(0,0.6fr)_minmax(0,0.25fr)] items-center gap-x-2 px-3";
const EMPTY_ARRAY = [];

export default function RecurringExpenses({ onAddClick, onCountUpdate }) {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [error, setError] = React.useState("");
    const [toggleCooldown, setToggleCooldown] = React.useState(false);
    const toggleCooldownTimerRef = React.useRef(null);
    const togglingRef = React.useRef(null);

    // Delete
    const [deleteOpen, setDeleteOpen] = React.useState(false);
    const [deleteTarget, setDeleteTarget] = React.useState(null);

    // Add
    const [addOpen, setAddOpen] = React.useState(false);
    const [actionError, setActionError] = React.useState("");

    // Edit
    const [editOpen, setEditOpen] = React.useState(false);
    const [editTarget, setEditTarget] = React.useState(null);
    const [editError, setEditError] = React.useState("");
    const [editTitle, setEditTitle] = React.useState("");
    const [editAmount, setEditAmount] = React.useState("");
    const [editCategory, setEditCategory] = React.useState("");
    const [editDescription, setEditDescription] = React.useState("");

    // Description preview
    const [descOpen, setDescOpen] = React.useState(false);
    const [descTarget, setDescTarget] = React.useState(null);
    const [recurringMenuForId, setRecurringMenuForId] = React.useState(null);
    const [recurringMenuPosition, setRecurringMenuPosition] = React.useState(null);

    // Inline toggle saving
    const [togglingId, setTogglingId] = React.useState(null);

    const [windowWidth, setWindowWidth] = React.useState(typeof window !== "undefined" ? window.innerWidth : 1280);
    React.useEffect(() => {
        const handleResize = () => setWindowWidth(window.innerWidth);
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, []);

    React.useEffect(() => {
        return () => {
            if (toggleCooldownTimerRef.current) {
                clearTimeout(toggleCooldownTimerRef.current);
            }
        };
    }, []);

    // Add form
    const [addTitle, setAddTitle] = React.useState("");
    const [addAmount, setAddAmount] = React.useState("");
    const [addCategory, setAddCategory] = React.useState("");
    const [addFrequency, setAddFrequency] = React.useState("MONTHLY");
    const [addStartDate, setAddStartDate] = React.useState("");
    const [addDescription, setAddDescription] = React.useState("");

    const [touchedAdd, setTouchedAdd] = React.useState({});
    const [touchedEdit, setTouchedEdit] = React.useState({});

    const [searchParams, setSearchParams] = useSearchParams();
    const [searchQuery, setSearchQuery] = React.useState(() => searchParams.get("r_search") || "");
    const [page, setPage] = React.useState(() => {
        const p = parseInt(searchParams.get("r_page"), 10);
        return p > 0 ? p : 1;
    });
    const PAGE_SIZE = 15;

    const tCategory = (name) => t(`categories.${name}`, { defaultValue: name });
    const appLang = _getAppLang();
    const todayISO = React.useMemo(() => toISODateInTimeZone(), []);
    const minStartDate = React.useMemo(() => {
        const parts = todayISO.split("-");
        if (parts.length < 2) return MIN_EXPENSE_DATE_ZOD;
        return `${parts[0]}-${parts[1]}-01`;
    }, [todayISO]);
    const { userQuery, recurringQuery, isPremium } = useRecurringDataQuery();
    const categoriesQuery = useRecurringCategoriesQuery(isPremium);
    const loading = userQuery.isLoading || (isPremium && (recurringQuery.isLoading || categoriesQuery.isLoading));
    const expenses = recurringQuery.data || EMPTY_ARRAY;
    const categories = categoriesQuery.data || EMPTY_ARRAY;
    const fetchError = userQuery.error || recurringQuery.error || categoriesQuery.error;
    const displayError = error || (fetchError
        ? localizeApiError(fetchError?.message, t) || fetchError?.message || t("recurring.loadFailed")
        : "");
    const filteredExpenses = React.useMemo(() => {
        const q = searchQuery.trim().toLowerCase();
        if (!q) return expenses;
        return expenses.filter((e) => e.title.toLowerCase().includes(q));
    }, [expenses, searchQuery]);

    const isBudgetRequiredError = (message) => {
        const msg = String(message || "").toLowerCase();
        return (
            msg === "expenses.budget_required" ||
            msg.includes("cannot create an expense for") ||
            msg.includes("cannot add expense for")
        );
    };

    const getAddActionErrorMessage = (e, options = {}) => {
        if (isBudgetRequiredError(e?.message)) {
            const category = options.category ? tCategory(options.category) : t("expenses.category");
            const monthLabel = options.startDate
                ? formatMonthYear(options.startDate, appLang)
                : t("recurring.startDate");
            return t("recurring.budgetRequiredForStartMonth", {
                category,
                month: monthLabel,
                defaultValue: "Cannot create this recurring template for {{category}} because no budget exists for {{month}}. Create that budget first.",
            });
        }
        return localizeApiError(e?.message, t) || e?.message || t("expenses.requestFailed");
    };
    const totalPages = Math.max(1, Math.ceil(filteredExpenses.length / PAGE_SIZE));
    const pagedExpenses = React.useMemo(
        () => filteredExpenses.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
        [filteredExpenses, page, PAGE_SIZE]
    );

    // Sync state to URL
    React.useEffect(() => {
        const next = new URLSearchParams();
        next.set("tab", "recurring");
        if (searchQuery.trim()) next.set("r_search", searchQuery.trim());
        if (page > 1) next.set("r_page", String(page));
        setSearchParams(next, { replace: true });
    }, [searchQuery, page, setSearchParams]);

    // Reset to page 1 when search changes (only if we're not already on page 1 to prevent loop)
    React.useEffect(() => {
        setPage(p => p !== 1 ? 1 : p);
    }, [searchQuery]);

    // Register the openAdd fn with the parent so the top-bar button can trigger it
    React.useEffect(() => {
        if (onAddClick) onAddClick(openAdd);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [onAddClick]);

    // Lift total expense count to parent for limit enforcement
    React.useEffect(() => {
        if (onCountUpdate) onCountUpdate(expenses.length);
    }, [expenses.length, onCountUpdate]);

    const addRecurringMutation = useCreateRecurringMutation();
    const editRecurringMutation = useUpdateRecurringMutation();
    const deleteRecurringMutation = useDeleteRecurringMutation();
    const toggleRecurringMutation = useToggleRecurringMutation();

    const isAdding = addRecurringMutation.isPending;
    const isEditing = editRecurringMutation.isPending;
    const isDeleting = deleteRecurringMutation.isPending;

    // Inline toggle — dedicated PATCH endpoint, no dialog needed
    const handleInlineToggle = React.useCallback(async (e, newValue) => {
        if (toggleCooldown) return;
        if (togglingRef.current) return;
        if (togglingId) return;

        togglingRef.current = true;
        setTogglingId(e.id);
        const previous = queryClient.getQueryData(["recurring", "list"]) || EMPTY_ARRAY;
        queryClient.setQueryData(
            ["recurring", "list"],
            previous.map((r) => (r.id === e.id ? { ...r, is_active: newValue } : r)),
        );
        try {
            await toggleRecurringMutation.mutateAsync({ id: e.id, is_active: newValue });
        } catch (err) {
            queryClient.setQueryData(["recurring", "list"], previous);

            if (err?.status === 429) {
                const waitSeconds = Number(err?.retryAfterSeconds || 2);
                const waitMs = Number.isFinite(waitSeconds) && waitSeconds > 0 ? waitSeconds * 1000 : 2000;

                setError("");
                setToggleCooldown(true);
                if (toggleCooldownTimerRef.current) {
                    clearTimeout(toggleCooldownTimerRef.current);
                }
                toggleCooldownTimerRef.current = setTimeout(() => {
                    setToggleCooldown(false);
                    toggleCooldownTimerRef.current = null;
                }, waitMs);
                return;
            }

            setError(localizeApiError(err?.message, t) || err?.message || t("recurring.toggleFailed"));
        } finally {
            setTogglingId(null);
            togglingRef.current = false;
        }
    }, [toggleCooldown, togglingId, queryClient, toggleRecurringMutation, t]);

    const handleDelete = async () => {
        if (isDeleting || !deleteTarget) return;
        try {
            await deleteRecurringMutation.mutateAsync(deleteTarget.id);
            setDeleteOpen(false);
        } catch (e) {
            setError(localizeApiError(e?.message, t) || e?.message || t("recurring.deleteFailed"));
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
        setEditOpen(true);
    };

    const openDesc = (e) => { setDescTarget(e); setDescOpen(true); };

    React.useEffect(() => {
        const onPointerDown = (event) => {
            const target = event.target;
            if (!(target instanceof HTMLElement)) return;
            if (target.closest("[data-action-popover]")) return;
            setRecurringMenuForId(null);
            setRecurringMenuPosition(null);
        };
        document.addEventListener("pointerdown", onPointerDown);
        return () => document.removeEventListener("pointerdown", onPointerDown);
    }, []);

    const openRecurringActions = (event, recurringExpense) => {
        const button = event.currentTarget;
        const rect = button instanceof HTMLElement ? button.getBoundingClientRect() : null;
        const menuWidth = 176;
        const menuHeight = 120;
        const viewportPadding = 8;
        setRecurringMenuForId((prev) => {
            if (prev === recurringExpense.id) {
                setRecurringMenuPosition(null);
                return null;
            }
            if (!rect) return null;
            const fitsBelow = rect.bottom + 6 + menuHeight <= window.innerHeight - viewportPadding;
            const top = fitsBelow ? rect.bottom + 6 : rect.top - 6 - menuHeight;
            const left = Math.max(
                viewportPadding,
                Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - viewportPadding)
            );
            setRecurringMenuPosition({ top, left });
            return recurringExpense.id;
        });
    };

    const editExpenseParsed = React.useMemo(() => recurringExpenseUpdateFormSchema.safeParse({
        title: editTitle, amount: editAmount, category: editCategory, description: editDescription,
    }), [editTitle, editAmount, editCategory, editDescription]);

    const editErrors = React.useMemo(() => {
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
            await editRecurringMutation.mutateAsync({
                id: editTarget.id,
                payload: {
                    title: parsed.data.title,
                    amount: parsed.data.amount,
                    category: parsed.data.category,
                    description: parsed.data.description ?? null,
                },
            });
            setEditOpen(false);
        } catch (e) {
            setEditError(localizeApiError(e.message, t) || e.message || t("recurring.updateFailed"));
        }
    };

    const addExpenseParsed = React.useMemo(() => recurringExpenseFormSchema.safeParse({
        title: addTitle, amount: addAmount, category: addCategory,
        frequency: addFrequency, start_date: addStartDate, description: addDescription,
    }), [addTitle, addAmount, addCategory, addFrequency, addStartDate, addDescription]);

    const addErrors = React.useMemo(() => {
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
            await addRecurringMutation.mutateAsync({
                title: parsed.data.title, amount: parsed.data.amount,
                category: parsed.data.category, frequency: parsed.data.frequency,
                start_date: parsed.data.start_date, description: parsed.data.description ?? null,
            });
            setAddOpen(false);
        } catch (e) {
            setActionError(getAddActionErrorMessage(e, {
                category: parsed.data.category,
                startDate: parsed.data.start_date,
            }));
        }
    };

    const selectTriggerClass = "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
    const selectContentClass = "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";


    if (userQuery.isLoading) {
        return (
            <Card className="shadow-sm">
                <CardContent className="min-h-80 flex items-center justify-center p-6">
                    <LoadingSpinner className="h-6 w-6" />
                </CardContent>
            </Card>
        );
    }

    if (!isPremium) {
        return (
            <Card className="overflow-hidden border-primary/25 bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.14),transparent_45%),linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,1))] shadow-sm dark:border-primary/30 dark:bg-[radial-gradient(circle_at_top_left,rgba(34,197,94,0.16),transparent_42%),linear-gradient(180deg,rgba(20,24,29,0.98),rgba(10,12,16,1))]">
                <CardContent className="flex flex-col gap-6 p-6 sm:p-8 lg:flex-row lg:items-center lg:justify-between">
                    <div className="space-y-3">
                        <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                            <Crown className="h-3.5 w-3.5" />
                            {t("recurring.premiumBadge")}
                        </div>
                        <div className="space-y-2">
                            <h3 className="text-2xl font-semibold tracking-tight">{t("recurring.premiumTitle")}</h3>
                            <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                                {t("recurring.premiumDesc")}
                            </p>
                        </div>
                    </div>
                    <Button className="h-11 rounded-2xl px-6 text-base" onClick={() => navigate("/premium")}>
                        {t("recurring.viewPlans")}
                    </Button>
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
                    {displayError && <p className="text-sm text-red-600 mb-4">{displayError}</p>}
                    {/* Search bar — only shown once data is loaded and there are templates */}
                    {!loading && expenses.length > 0 && (
                        <div className="relative mb-6 max-w-xs animate-in fade-in slide-in-from-left-4 duration-500">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder={t("expenses.search")}
                                className="w-full h-10 rounded-xl border border-input bg-background pl-10 pr-3 text-sm shadow-sm transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
                            />
                        </div>
                    )}

                    {/* 📱 Ultra-Mobile Native List View (< 500px) */}
                    <div className="min-[501px]:hidden divide-y divide-border/40 pb-4">
                        {loading ? (
                            <div className="flex justify-center py-10">
                                <LoadingSpinner className="h-6 w-6 text-primary" />
                            </div>
                        ) : expenses.length === 0 ? (
                            <EmptyState inline description={t("recurring.emptyDesc")} />
                        ) : filteredExpenses.length === 0 ? (
                            <EmptyState inline description={t("recurring.noSearchResults")} />
                        ) : (
                            pagedExpenses.map((e, index) => {
                                const Icon = categoryIconMap[e.category] || Circle;
                                const bgClass = getCategoryBgClass(e.category);
                                return (
                                    <div
                                        key={e.id}
                                        className="p-3 bg-card/40 border-b border-border/50 flex flex-col gap-3 group relative transition-all active:bg-muted/30"
                                        style={{ animationDelay: `${index * 40}ms` }}
                                    >
                                        {/* Row 1: Icon & Actions */}
                                        <div className="flex justify-between items-center w-full">
                                            <div className={cn("h-exp-icon w-exp-icon rounded-xl flex items-center justify-center shadow-sm shrink-0", bgClass)}>
                                                <Icon className="h-[50%] w-[50%]" />
                                            </div>

                                            <div className="flex items-center gap-0.5 bg-card/60 backdrop-blur-sm rounded-full border border-border/60 px-0.5 py-0.5 shadow-sm" data-action-popover>
                                                <Switch
                                                    size="xs"
                                                    className="origin-right scale-75 active:scale-[0.7]"
                                                    checked={e.is_active}
                                                    onCheckedChange={(val) => handleInlineToggle(e, val)}
                                                    disabled={toggleCooldown || togglingId === e.id}
                                                    onPointerDown={(ev) => ev.stopPropagation()}
                                                />
                                                <div className="w-[1px] h-3 bg-border/80 mx-0.5"></div>
                                                <Button
                                                    size="icon"
                                                    variant="ghost"
                                                    className="h-5 w-5 rounded-full hover:bg-muted/80 opacity-70"
                                                    onPointerDown={(ev) => ev.stopPropagation()}
                                                    onClick={(event) => {
                                                        event.stopPropagation();
                                                        openRecurringActions(event, e);
                                                    }}
                                                >
                                                    <MoreHorizontal className="h-3 w-3" />
                                                </Button>
                                            </div>
                                        </div>

                                        {/* Row 2: Identity (Title & Meta) */}
                                        <div className="flex flex-col mt-1">
                                            <h3 className="font-bold text-exp-title leading-tight text-foreground/90 break-words pr-2">
                                                {e.title}
                                            </h3>
                                            <div className="flex items-center gap-1.5 text-exp-detail font-medium text-muted-foreground mt-2 border-l-2 border-primary/20 pl-2">
                                                <span className="capitalize">{tCategory(e.category)}</span>
                                                <span>•</span>
                                                <span className="uppercase tracking-wider font-bold opacity-80">{t(`recurring.${e.frequency.toLowerCase()}`)}</span>
                                            </div>
                                        </div>

                                        {/* Row 3: Financial Pairs */}
                                        <div className="mt-3 flex flex-col gap-0 border border-border/50 rounded-xl overflow-hidden shadow-sm bg-muted/10">
                                            <div className="flex justify-between items-center px-3 py-2 border-b border-border/50">
                                                <span className="text-exp-detail font-black text-muted-foreground uppercase tracking-widest opacity-80">
                                                    {t("recurring.nextDue")}
                                                </span>
                                                <span className="text-[8px] font-bold text-foreground/90">
                                                    {formatDisplayDate(e.next_due_date, appLang)}
                                                </span>
                                            </div>
                                            <div className="flex justify-between items-center px-3 py-2 bg-card/40">
                                                <span className="text-exp-detail font-black text-muted-foreground uppercase tracking-widest opacity-80">
                                                    {t("expenses.amount")}
                                                </span>
                                                <CurrencyAmount
                                                    value={e.amount}
                                                    format="compact"
                                                    className="text-[calc(var(--title-size)*1.1)] font-black text-foreground tabular-nums tracking-tight"
                                                    currencyClassName="text-exp-detail font-bold opacity-50 ml-1"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    {/* 🎨 Mobile Gallery Card View (501px-639px) */}
                    <div className="hidden min-[501px]:block sm:hidden space-y-6">
                        {loading ? (
                            <div className="flex justify-center py-10">
                                <LoadingSpinner className="h-6 w-6 text-primary" />
                            </div>
                        ) : expenses.length === 0 ? (
                            <EmptyState inline description={t("recurring.emptyDesc")} />
                        ) : (
                            pagedExpenses.map((e, index) => {
                                const Icon = categoryIconMap[e.category] || Circle;
                                const bgClass = getCategoryBgClass(e.category);
                                return (
                                    <div
                                        key={e.id}
                                        className={cn(
                                            "group relative flex flex-col justify-between bg-card/40 border border-border/50 rounded-2xl p-6 transition-all duration-300",
                                            "hover:bg-card hover:shadow-2xl hover:-translate-y-1 hover:border-border/80",
                                            "active:scale-[0.98] [&:has([data-action-popover]:active)]:scale-100",
                                            "animate-in fade-in zoom-in-95 duration-500 fill-both"
                                        )}
                                        style={{ animationDelay: `${index * 50}ms` }}
                                    >
                                        <div className="flex items-start justify-between mb-5">
                                            <div className="flex items-center gap-3">
                                                <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center shadow-inner", bgClass)}>
                                                    <Icon className="h-5 w-5" />
                                                </div>
                                                <Badge
                                                    variant="secondary"
                                                    className={cn(
                                                        "px-2.5 py-0.5 text-[10px] font-bold capitalize bg-muted/50 border-none shrink-0",
                                                        getCategoryColorClass(e.category)
                                                    )}
                                                >
                                                    {tCategory(e.category)}
                                                </Badge>
                                            </div>
                                            <div className="flex flex-col items-end gap-1.5" data-action-popover>
                                                <div className="flex items-center gap-3">
                                                    <Switch
                                                        size="sm"
                                                        checked={e.is_active}
                                                        onCheckedChange={(val) => handleInlineToggle(e, val)}
                                                        disabled={toggleCooldown || togglingId === e.id}
                                                        onPointerDown={(ev) => ev.stopPropagation()}
                                                    />
                                                    <Button
                                                        type="button"
                                                        size="icon"
                                                        variant="ghost"
                                                        className="h-8 w-8 rounded-full opacity-40 group-hover:opacity-100 transition-all hover:bg-muted"
                                                        onPointerDown={(ev) => ev.stopPropagation()}
                                                        onClick={(event) => {
                                                            event.stopPropagation();
                                                            openRecurringActions(event, e);
                                                        }}
                                                    >
                                                        <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-4">
                                            <div className="space-y-1 min-w-0">
                                                <TitleTooltip title={e.title}>
                                                    <div className="font-bold text-xl tracking-tight text-foreground truncate cursor-default">
                                                        {e.title}
                                                    </div>
                                                </TitleTooltip>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/40 flex items-center gap-1.5">
                                                        {t(`recurring.${e.frequency.toLowerCase()}`)}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex items-center justify-between py-3 px-4 bg-muted/30 rounded-xl border border-border/5">
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40 leading-none mb-1">
                                                        {t("recurring.nextDue")}
                                                    </span>
                                                    <span className="text-sm font-bold text-foreground/80">
                                                        {formatDisplayDate(e.next_due_date, appLang)}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col text-right">
                                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40 leading-none mb-1">
                                                        {t("expenses.amount")}
                                                    </span>
                                                    <CurrencyAmount
                                                        value={e.amount}
                                                        format="display"
                                                        className="text-lg font-black text-foreground tabular-nums tracking-tight"
                                                        currencyClassName="text-[10px] font-bold opacity-40 ml-1.5"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    {/* 📱 SM/MD List View (640px - 1023px) */}
                    <div className="hidden sm:block lg:hidden space-y-4">
                        {loading ? (
                            <div className="flex justify-center py-12">
                                <LoadingSpinner className="h-8 w-8 text-primary" />
                            </div>
                        ) : expenses.length === 0 ? (
                            <EmptyState inline description={t("recurring.emptyDesc")} />
                        ) : filteredExpenses.length === 0 ? (
                            <EmptyState inline description={t("recurring.noSearchResults")} />
                        ) : (
                            <div className="divide-y divide-border/40">
                                {pagedExpenses.map((e, index) => {
                                    const Icon = categoryIconMap[e.category] || Circle;
                                    const bgClass = getCategoryBgClass(e.category);
                                    return (
                                        <div
                                            key={e.id}
                                            className={cn(
                                                "flex items-center justify-between gap-4 py-4 px-2 rounded-xl group",
                                                "hover:bg-muted/50 transition-all duration-300",
                                                "active:scale-[0.98] [&:has([data-action-popover]:active)]:scale-100",
                                                "animate-in fade-in slide-in-from-bottom-2 duration-500 fill-both"
                                            )}
                                            style={{ animationDelay: `${index * 40}ms` }}
                                        >
                                            <div className={cn("h-10 w-10 shrink-0 rounded-full flex items-center justify-center", bgClass)}>
                                                <Icon className="h-5 w-5" />
                                            </div>
                                            <div className="flex-1 min-w-0 space-y-1 pr-2">
                                                <TitleTooltip title={e.title}>
                                                    <div className="font-semibold text-sm text-foreground/90 leading-tight truncate">
                                                        {e.title}
                                                    </div>
                                                </TitleTooltip>
                                                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] font-medium text-muted-foreground/60">
                                                    <span className="capitalize">{tCategory(e.category)}</span>
                                                    <span>•</span>
                                                    <span>{t(`recurring.${e.frequency.toLowerCase()}`)}</span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4 shrink-0">
                                                <div className="text-right">
                                                    <CurrencyAmount
                                                        value={e.amount}
                                                        format="display"
                                                        className="font-bold text-sm tabular-nums text-foreground"
                                                        currencyClassName="text-[10px] ml-1 opacity-60"
                                                    />
                                                    <p className="text-[9px] font-medium text-muted-foreground/40 mt-0.5">
                                                        {t("recurring.nextDue")}: {formatDisplayDate(e.next_due_date, appLang)}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-2" data-action-popover>
                                                    <Switch
                                                        size="sm"
                                                        checked={e.is_active}
                                                        onCheckedChange={(val) => handleInlineToggle(e, val)}
                                                        disabled={toggleCooldown || togglingId === e.id}
                                                        onPointerDown={(ev) => ev.stopPropagation()}
                                                        className="scale-75"
                                                    />
                                                    <Button
                                                        type="button"
                                                        size="icon"
                                                        variant="ghost"
                                                        className="h-8 w-8 text-muted-foreground/40"
                                                        onPointerDown={(ev) => ev.stopPropagation()}
                                                        onClick={(event) => {
                                                            event.stopPropagation();
                                                            openRecurringActions(event, e);
                                                        }}
                                                    >
                                                        <MoreHorizontal className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* 🎨 LG Gallery View (1024px - 1279px) */}
                    <div className="hidden lg:grid xl:hidden lg:grid-cols-2 gap-6 pt-2">
                        {loading ? (
                            <div className="col-span-full flex justify-center py-20">
                                <LoadingSpinner className="h-8 w-8 text-primary" />
                            </div>
                        ) : expenses.length === 0 ? (
                            <div className="col-span-full">
                                <EmptyState inline description={t("recurring.emptyDesc")} />
                            </div>
                        ) : (
                            pagedExpenses.map((e, index) => {
                                const Icon = categoryIconMap[e.category] || Circle;
                                const bgClass = getCategoryBgClass(e.category);
                                return (
                                    <div
                                        key={e.id}
                                        className={cn(
                                            "group relative flex flex-col justify-between bg-card/40 border border-border/50 rounded-2xl p-6 transition-all duration-300",
                                            "hover:bg-card hover:shadow-2xl hover:-translate-y-1 hover:border-border/80",
                                            "active:scale-[0.98] [&:has([data-action-popover]:active)]:scale-100",
                                            "animate-in fade-in zoom-in-95 duration-500 fill-both"
                                        )}
                                        style={{ animationDelay: `${index * 50}ms` }}
                                    >
                                        <div className="flex items-center justify-between mb-5">
                                            <div className="flex items-center gap-3">
                                                <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center shadow-inner", bgClass)}>
                                                    <Icon className="h-5 w-5" />
                                                </div>
                                                <Badge
                                                    variant="secondary"
                                                    className={cn(
                                                        "px-2.5 py-0.5 text-[10px] font-bold capitalize bg-muted/50 border-none shrink-0",
                                                        getCategoryColorClass(e.category)
                                                    )}
                                                >
                                                    {tCategory(e.category)}
                                                </Badge>
                                            </div>
                                            <div className="flex flex-col items-end gap-1.5" data-action-popover>
                                                <div className="flex items-center gap-3">
                                                    <Switch
                                                        size="sm"
                                                        checked={e.is_active}
                                                        onCheckedChange={(val) => handleInlineToggle(e, val)}
                                                        disabled={toggleCooldown || togglingId === e.id}
                                                        onPointerDown={(ev) => ev.stopPropagation()}
                                                    />
                                                    <Button
                                                        type="button"
                                                        size="icon"
                                                        variant="ghost"
                                                        className="h-8 w-8 rounded-full opacity-40 group-hover:opacity-100 transition-all hover:bg-muted"
                                                        onPointerDown={(ev) => ev.stopPropagation()}
                                                        onClick={(event) => {
                                                            event.stopPropagation();
                                                            openRecurringActions(event, e);
                                                        }}
                                                    >
                                                        <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                                                    </Button>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-4">
                                            <div className="space-y-1 min-w-0">
                                                <TitleTooltip title={e.title}>
                                                    <div className="font-bold text-xl tracking-tight text-foreground truncate cursor-default">
                                                        {e.title}
                                                    </div>
                                                </TitleTooltip>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/40 flex items-center gap-1.5">
                                                        {t(`recurring.${e.frequency.toLowerCase()}`)}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="flex items-center justify-between py-3 px-4 bg-muted/30 rounded-xl border border-border/5">
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40 leading-none mb-1">
                                                        {t("recurring.nextDue")}
                                                    </span>
                                                    <span className="text-sm font-bold text-foreground/80">
                                                        {formatDisplayDate(e.next_due_date, appLang)}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col text-right">
                                                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/40 leading-none mb-1">
                                                        {t("expenses.amount")}
                                                    </span>
                                                    <CurrencyAmount
                                                        value={e.amount}
                                                        format="display"
                                                        className="text-lg font-black text-foreground tabular-nums tracking-tight"
                                                        currencyClassName="text-[10px] font-bold opacity-40 ml-1.5"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    <div className="hidden xl:block overflow-x-auto">
                        <div className="min-w-[860px] space-y-0">
                            {/* Header row */}
                            <div className={`${COL} border-b border-border py-3 text-[11px] uppercase tracking-widest font-bold text-muted-foreground/50`}>
                                <div className="text-left">{t("recurring.templateTitle")}</div>
                                <div className="text-center">{t("expenses.category")}</div>
                                <div className="text-center">{t("recurring.frequency")}</div>
                                <div className="text-center">{t("recurring.nextDue")}</div>
                                <div className="text-right">{t("expenses.amountUzs")}</div>
                                <div className="text-center">{t("recurring.active")}</div>
                                <div className="text-right" />
                            </div>

                            {loading ? (
                                <div className="flex justify-center px-4 py-10">
                                    <LoadingSpinner className="h-6 w-6" />
                                </div>
                            ) : expenses.length === 0 ? (
                                <EmptyState inline description={t("recurring.emptyDesc")} />
                            ) : filteredExpenses.length === 0 ? (
                                <EmptyState inline description={t("recurring.noSearchResults")} />
                            ) : (
                                pagedExpenses.map((e) => (
                                    <div key={e.id} className={`${COL} border-b border-border py-3 hover:bg-muted/50 dark:hover:bg-muted/30 active:bg-muted/70 dark:active:bg-muted/40 transition-colors duration-200`}>
                                        {/* Title */}
                                        <div className="min-w-0 self-center">
                                            <div className="min-w-0">
                                                <TitleTooltip title={e.title}>
                                                    <div className="font-semibold text-table-title text-foreground truncate cursor-default">
                                                        {e.title}
                                                    </div>
                                                </TitleTooltip>
                                                {e.description && (
                                                    <button
                                                        onClick={() => openDesc(e)}
                                                        className="text-[10px] text-muted-foreground/60 hover:text-primary transition-colors flex items-center gap-1 group/desc"
                                                    >
                                                        <MessageSquare className="h-3 w-3" />
                                                        <span className="truncate max-w-[120px]">{e.description}</span>
                                                    </button>
                                                )}
                                            </div>
                                        </div>

                                        <div className="text-center">
                                            <Badge variant="secondary" className={cn("px-2 py-0.5 rounded-full text-[10px] xl:text-[10px] 2xl:text[12px] font-bold capitalize bg-muted/50 border-none shrink-0", getCategoryColorClass(e.category))}>
                                                {tCategory(e.category)}
                                            </Badge>
                                        </div>

                                        {/* Frequency */}
                                        <div className="text-center">
                                            <span className="text-table-detail font-bold uppercase tracking-wider text-muted-foreground/60">
                                                {t(`recurring.${e.frequency.toLowerCase()}`)}
                                            </span>
                                        </div>

                                        {/* Next Due */}
                                        <div className="text-center">
                                            <span className="text-table-detail font-medium text-foreground/80">
                                                {formatDisplayDate(e.next_due_date, appLang)}
                                            </span>
                                        </div>

                                        {/* Amount */}
                                        <div className="text-right">
                                            <CurrencyAmount
                                                value={e.amount}
                                                format="display"
                                                className="flex justify-end gap-1 items-baseline text-table-amount font-black text-foreground tabular-nums tracking-tight"
                                                currencyClassName="text-table-detail font-bold opacity-40 ml-0.5"
                                            />
                                        </div>

                                        {/* Active */}
                                        <div className="flex justify-center" data-action-popover>
                                            <Switch
                                                size="xs"
                                                checked={e.is_active}
                                                onCheckedChange={(val) => handleInlineToggle(e, val)}
                                                disabled={toggleCooldown || togglingId === e.id}
                                                onPointerDown={(ev) => ev.stopPropagation()}
                                            />
                                        </div>

                                        {/* Actions */}
                                        <div className="text-right" data-action-popover>
                                            <Button
                                                type="button"
                                                size="icon"
                                                variant="ghost"
                                                className="h-8 w-8 rounded-full opacity-40 group-hover:opacity-100 transition-all hover:bg-muted"
                                                onPointerDown={(ev) => ev.stopPropagation()}
                                                onClick={(event) => {
                                                    event.stopPropagation();
                                                    openRecurringActions(event, e);
                                                }}
                                            >
                                                <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                                            </Button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        {/* Pagination controls for XL table */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between px-2 pt-6">
                                <p className="text-muted-foreground transition-all duration-200 text-pag font-medium">
                                    {t("expenses.page")} {page} / {totalPages || 1}
                                </p>
                                <div className="flex items-center gap-1.5">
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        className="h-pag-btn w-pag-btn rounded-lg"
                                        disabled={page === 1}
                                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                                    >
                                        <ChevronLeft className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        className="h-pag-btn w-pag-btn rounded-lg"
                                        disabled={page === totalPages}
                                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                    >
                                        <ChevronRight className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Pagination for Gallery/List Views */}
                    <div className="xl:hidden">
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between pt-8 border-t border-border/40 mt-6">
                                <p className="text-muted-foreground transition-all duration-200 text-pag font-medium">
                                    {t("expenses.page")} {page} / {totalPages || 1}
                                </p>
                                <div className="flex items-center gap-3">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className={cn(
                                            "h-pag-btn rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-muted",
                                            windowWidth < 640 ? "w-pag-btn px-0" : "px-4"
                                        )}
                                        disabled={page === 1}
                                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                                    >
                                        <ChevronLeft className={cn("h-3.5 w-3.5", windowWidth >= 640 ? "mr-2" : "")} />
                                        {windowWidth >= 640 && t("expenses.prev")}
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className={cn(
                                            "h-pag-btn rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-muted",
                                            windowWidth < 640 ? "w-pag-btn px-0" : "px-4"
                                        )}
                                        disabled={page === totalPages}
                                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                    >
                                        {windowWidth >= 640 && t("expenses.next")}
                                        <ChevronRight className={cn("h-3.5 w-3.5", windowWidth >= 640 ? "ml-2" : "")} />
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Float menu for actions */}
            {recurringMenuForId && recurringMenuPosition && (
                createPortal(
                    <div
                        data-action-popover
                        className="fixed z-[100] animate-in fade-in zoom-in-95 duration-200"
                        style={{ top: recurringMenuPosition.top, left: recurringMenuPosition.left }}
                    >
                        <Card className="w-44 shadow-2xl border-border/50 overflow-hidden bg-popover/90 backdrop-blur-xl">
                            <div className="p-1.5 space-y-0.5">
                                <button
                                    onClick={() => {
                                        const e = expenses.find(x => x.id === recurringMenuForId);
                                        if (e) openEdit(e);
                                        setRecurringMenuForId(null);
                                    }}
                                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-muted text-foreground/80 hover:text-foreground"
                                >
                                    <Pencil className="h-4 w-4 text-blue-500/70" />
                                    {t("expenses.edit")}
                                </button>
                                <button
                                    onClick={() => {
                                        const e = expenses.find(x => x.id === recurringMenuForId);
                                        if (e) openDelete(e);
                                        setRecurringMenuForId(null);
                                    }}
                                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-red-500/10 text-red-600/80 hover:text-red-600"
                                >
                                    <Trash2 className="h-4 w-4 text-red-500/70" />
                                    {t("expenses.delete")}
                                </button>
                                <div className="mx-2 my-1 border-t border-border/40" />
                                <button
                                    onClick={() => {
                                        const e = expenses.find(x => x.id === recurringMenuForId);
                                        if (e) openDesc(e);
                                        setRecurringMenuForId(null);
                                    }}
                                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-muted text-foreground/80 hover:text-foreground"
                                >
                                    <FileText className="h-4 w-4 text-muted-foreground/60" />
                                    {t("recurring.viewDetails")}
                                </button>
                            </div>
                        </Card>
                    </div>,
                    document.body
                )
            )}

            {/* Dialogs */}
            <ConfirmDialog
                open={deleteOpen}
                onOpenChange={setDeleteOpen}
                title={t("recurring.deleteTitle")}
                description={t("recurring.deleteDesc", { title: deleteTarget?.title })}
                onConfirm={handleDelete}
                loading={isDeleting}
                variant="destructive"
            />

            {/* Detailed Info Dialog */}
            <Dialog open={descOpen} onOpenChange={setDescOpen}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <div className="flex items-center gap-3 mb-2">
                            <div className={cn("h-10 w-10 rounded-xl flex items-center justify-center shadow-inner", getCategoryBgClass(descTarget?.category))}>
                                {(() => {
                                    const CategoryIcon = categoryIconMap[descTarget?.category] || Circle;
                                    return <CategoryIcon className="h-5 w-5" />;
                                })()}
                            </div>
                            <div>
                                <DialogTitle className="text-xl">{descTarget?.title}</DialogTitle>
                                <Badge variant="secondary" className="mt-1 font-bold">{tCategory(descTarget?.category)}</Badge>
                            </div>
                        </div>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">{t("recurring.frequency")}</p>
                                <p className="font-bold text-foreground/80 capitalize">{t(`recurring.${descTarget?.frequency.toLowerCase()}`)}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">{t("recurring.nextDue")}</p>
                                <p className="font-bold text-foreground/80">{formatDisplayDate(descTarget?.next_due_date, appLang)}</p>
                            </div>
                            <div className="space-y-1">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">{t("expenses.amount")}</p>
                                <CurrencyAmount value={descTarget?.amount} format="display" className="font-black text-lg" />
                            </div>
                            <div className="space-y-1">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">{t("recurring.active")}</p>
                                <Badge variant={descTarget?.is_active ? "success" : "secondary"} className="font-bold">
                                    {descTarget?.is_active ? t("recurring.statusActive") : t("recurring.statusPaused")}
                                </Badge>
                            </div>
                        </div>
                        {descTarget?.description ? (
                            <div className="space-y-2 pt-4 border-t border-border/40">
                                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">{t("expenses.description")}</p>
                                <p className="text-sm text-foreground/70 leading-relaxed whitespace-pre-wrap bg-muted/30 p-4 rounded-2xl border border-border/5">
                                    {descTarget.description}
                                </p>
                            </div>
                        ) : (
                            <div className="pt-4 border-t border-border/40">
                                <p className="text-xs italic text-muted-foreground/50">{t("expenses.noDescription")}</p>
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            {/* Add Dialog */}
            <Dialog open={addOpen} onOpenChange={setAddOpen}>
                <DialogContent className="sm:max-w-[480px]">
                    <DialogHeader>
                        <DialogTitle>{t("recurring.addDialogTitle")}</DialogTitle>
                        <DialogDescription>{t("recurring.addDialogDesc")}</DialogDescription>
                    </DialogHeader>
                    {actionError && <p className="text-xs text-red-600 mb-2">{actionError}</p>}
                    <div className="grid gap-2.5 py-2">
                        <div className="grid gap-1.5">
                            <label>{t("expenses.title")}</label>
                            <Input
                                value={addTitle}
                                onChange={(e) => setAddTitle(e.target.value)}
                                onBlur={() => setTouchedAdd(prev => ({ ...prev, title: true }))}
                                placeholder={t("expenses.titleCol")}
                                className={cn(addErrors.title && "border-red-500 focus-visible:ring-red-500")}
                            />
                            {addErrors.title && <p className="text-[11px] text-red-500 font-medium">{addErrors.title}</p>}
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="grid gap-1.5">
                                <label>{t("expenses.amount")}</label>
                                <div className="relative">
                                    <Input
                                        type="text"
                                        value={addAmount}
                                        onChange={(e) => setAddAmount(formatAmountInput(e.target.value))}
                                        onBlur={() => setTouchedAdd(prev => ({ ...prev, amount: true }))}
                                        placeholder="0"
                                        className={cn("pr-12 font-mono font-bold", addErrors.amount && "border-red-500 focus-visible:ring-red-500")}
                                    />
                                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground/50">UZS</span>
                                </div>
                                {addErrors.amount && <p className="text-[11px] text-red-500 font-medium">{addErrors.amount}</p>}
                            </div>

                            <div className="grid gap-1.5">
                                <label>{t("expenses.category")}</label>
                                <Select
                                    value={addCategory}
                                    onValueChange={(val) => setAddCategory(val)}
                                >
                                    <SelectTrigger className={cn(selectTriggerClass, addErrors.category && "border-red-500 focus-visible:ring-red-500")}>
                                        <SelectValue placeholder={t("expenses.selectCategory")} />
                                    </SelectTrigger>
                                    <SelectContent className={selectContentClass}>
                                        {CATEGORIES.map((cat) => (
                                            <SelectItem key={cat} value={cat}>
                                                <div className="flex items-center gap-2">
                                                    {(() => {
                                                        const CatIcon = categoryIconMap[cat] || Circle;
                                                        return <CatIcon className="h-3.5 w-3.5" />;
                                                    })()}
                                                    {tCategory(cat)}
                                                </div>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                {addErrors.category && <p className="text-[11px] text-red-500 font-medium">{addErrors.category}</p>}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="grid gap-1.5">
                                <label>{t("recurring.frequency")}</label>
                                <Select value={addFrequency} onValueChange={setAddFrequency}>
                                    <SelectTrigger className={selectTriggerClass}>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className={selectContentClass}>
                                        <SelectItem value="WEEKLY">{t("recurring.weekly")}</SelectItem>
                                        <SelectItem value="MONTHLY">{t("recurring.monthly")}</SelectItem>
                                        <SelectItem value="YEARLY">{t("recurring.yearly")}</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="grid gap-1.5">
                                <label>{t("recurring.startDate")}</label>
                                <Input
                                    type="date"
                                    min={minStartDate}
                                    value={addStartDate}
                                    onChange={(e) => setAddStartDate(e.target.value)}
                                    className="dark:color-scheme-dark"
                                />
                            </div>
                        </div>

                        <div className="grid gap-1.5">
                            <label>{t("expenses.description")} <span className="text-[10px] font-normal text-muted-foreground/50">({t("expenses.optional")})</span></label>
                            <Textarea
                                value={addDescription}
                                onChange={(e) => setAddDescription(e.target.value)}
                                placeholder={t("recurring.descriptionLabel")}
                                className="max-h-32 rounded-2xl"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setAddOpen(false)}>{t("common.cancel")}</Button>
                        <Button
                            onClick={handleAdd}
                            disabled={!canSubmitAddExpense}
                        >
                            {isAdding && <LoadingSpinner className="mr-2 h-4 w-4" />}
                            {t("expenses.add")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Edit Dialog */}
            <Dialog open={editOpen} onOpenChange={setEditOpen}>
                <DialogContent className="sm:max-w-[480px]">
                    <DialogHeader>
                        <DialogTitle>{t("recurring.editDialogTitle")}</DialogTitle>
                        <DialogDescription>{t("recurring.editDialogDesc")}</DialogDescription>
                    </DialogHeader>
                    {editError && <p className="text-xs text-red-600 mb-2">{editError}</p>}
                    <div className="grid gap-2.5 py-2">
                        <div className="grid gap-1.5">
                            <label>{t("expenses.title")}</label>
                            <Input
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onBlur={() => setTouchedEdit(prev => ({ ...prev, title: true }))}
                                placeholder={t("expenses.titleCol")}
                                className={cn(editErrors.title && "border-red-500 focus-visible:ring-red-500")}
                            />
                            {editErrors.title && <p className="text-[11px] text-red-500 font-medium">{editErrors.title}</p>}
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="grid gap-1.5">
                                <label>{t("expenses.amount")}</label>
                                <div className="relative">
                                    <Input
                                        type="text"
                                        value={editAmount}
                                        onChange={(e) => setEditAmount(formatAmountInput(e.target.value))}
                                        onBlur={() => setTouchedEdit(prev => ({ ...prev, amount: true }))}
                                        placeholder="0"
                                        className={cn("pr-12 font-mono font-bold", editErrors.amount && "border-red-500 focus-visible:ring-red-500")}
                                    />
                                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground/50">UZS</span>
                                </div>
                                {editErrors.amount && <p className="text-[11px] text-red-500 font-medium">{editErrors.amount}</p>}
                            </div>

                            <div className="grid gap-1.5">
                                <label>{t("expenses.category")}</label>
                                <Select
                                    value={editCategory}
                                    onValueChange={(val) => setEditCategory(val)}
                                >
                                    <SelectTrigger className={cn(selectTriggerClass, editErrors.category && "border-red-500 focus-visible:ring-red-500")}>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className={selectContentClass}>
                                        {CATEGORIES.map((cat) => (
                                            <SelectItem key={cat} value={cat}>
                                                <div className="flex items-center gap-2">
                                                    {(() => {
                                                        const CatIcon = categoryIconMap[cat] || Circle;
                                                        return <CatIcon className="h-3.5 w-3.5" />;
                                                    })()}
                                                    {tCategory(cat)}
                                                </div>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                {editErrors.category && <p className="text-[11px] text-red-500 font-medium">{editErrors.category}</p>}
                            </div>
                        </div>

                        <div className="grid gap-1.5">
                            <label>{t("expenses.description")} <span className="text-[10px] font-normal text-muted-foreground/50">({t("expenses.optional")})</span></label>
                            <Textarea
                                value={editDescription}
                                onChange={(e) => setEditDescription(e.target.value)}
                                placeholder={t("recurring.descriptionLabel")}
                                className="max-h-32 rounded-2xl"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setEditOpen(false)}>{t("common.cancel")}</Button>
                        <Button
                            onClick={handleEdit}
                            disabled={!canSubmitEditExpense}
                        >
                            {isEditing && <LoadingSpinner className="mr-2 h-4 w-4" />}
                            {t("recurring.saveChanges")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
