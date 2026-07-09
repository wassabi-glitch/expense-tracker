import * as React from "react";
import { ActionMenu, ActionMenuItem, ActionMenuDivider } from "@/components/ActionMenu";
import { Plus, Search, ChevronLeft, ChevronRight, Inbox, Trash2, MoreHorizontal, Pencil, FileText, Undo2, Coins, CreditCard, Landmark, Wallet as WalletIcon, Users, User, X, Receipt, Package, Repeat, Rows3, GitMerge, Lock, RefreshCcw, AlertTriangle, ArrowRightLeft } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import {
  useCreateExpenseMutation,
  useCreateExpenseMergeGroupMutation,
  useDeleteExpenseMutation,
  useAddExpensesToMergeGroupMutation,
  useMarkExpenseAsAssetMutation,
  useMarkExpenseAsRecurringMutation,
  useRemoveExpenseFromMergeGroupMutation,
  useSplitExpenseMutation,
  useUpdateExpenseMutation,
  useRefundExpenseMutation,
} from "./hooks/useExpenseMutations";
import { useExpenseCategoriesQuery } from "./hooks/useExpenseCategoriesQuery";
import { useExpensesQuery } from "./hooks/useExpensesQuery";
import { NeedsConfirmationSection } from "./components/NeedsConfirmationSection";
import { toISODateInTimeZone } from "@/lib/date";
import { localizeApiError } from "@/lib/errorMessages";
import { cn } from "@/lib/utils";
import {
  getBudgets,
  getActiveSessionDraft,
  getBudgetSubcategories,
  getCurrentUser,
  getExpenseMergeGroups,
  getProjects,
  getProjectSubcategories,
  reallocateBudget,
  reallocateBudgetSubcategory,
  updateBudget,
  getWallets,
  createBudget,
} from "@/lib/api";
import {
  expenseFormSchema,
  expenseUpdateFormSchema,
  MAX_EXPENSE_AMOUNT,
  refundSchema,
} from "./expenseSchemas.js";
import { TitleTooltip } from "@/components/TitleTooltip";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import RecurringExpenses from "./RecurringExpenses";
import SessionComposer from "./SessionComposer";

const PAGE_SIZE = 15;
const MIN_EXPENSE_DATE = "2020-01-01";
const MAX_EXPENSE_AMOUNT_DIGITS = String(MAX_EXPENSE_AMOUNT).length;
const ALL_CATEGORIES_SELECT = "__all_categories__";
const EMPTY_ARRAY = [];
const MAX_EXPENSES_PER_MONTH = 1000;
const LAST_EXPENSE_CATEGORY_STORAGE_KEY = "expenses.lastUsedCategory";
const EXPENSE_FEED_VIEWS = ["all", "quick", "sessions", "groups", "refunds", "linked"];

import { getCategoryBgClass, getCategoryColorClass, categoryIconMap, CATEGORIES } from "@/lib/category";
import { Circle } from "lucide-react";
import { formatAmountInput, parseAmountInput, formatDisplayDate, formatMonthYear, formatUzs } from "@/lib/format";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useToast } from "@/lib/context/ToastContext";
import { useDebounce } from "@/hooks/useDebounce";


const parsePageParam = (value) => {
  const raw = String(value ?? "").trim();
  if (!raw) return 1;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
};

const getStoredLastExpenseCategory = () => {
  if (typeof window === "undefined") return "";
  try {
    return window.localStorage.getItem(LAST_EXPENSE_CATEGORY_STORAGE_KEY) || "";
  } catch {
    return "";
  }
};

const setStoredLastExpenseCategory = (category) => {
  if (!category || typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LAST_EXPENSE_CATEGORY_STORAGE_KEY, category);
  } catch {
    // Ignore storage failures and keep the form usable.
  }
};

function ResponsiveExpenseFormShell({
  compact,
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  dialogClassName = "sm:max-w-[480px]",
}) {
  if (compact) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side="bottom"
          className="max-h-[92vh] rounded-t-[28px] border-x-0 border-b-0 px-0 pb-0 pt-0 sm:max-h-[88vh]"
        >
          <SheetHeader className="border-b border-border/60 px-5 pb-4 pt-5 text-left">
            <SheetTitle>{title}</SheetTitle>
            <SheetDescription>{description}</SheetDescription>
          </SheetHeader>
          <div className="max-h-[calc(92vh-148px)] overflow-y-auto px-5 py-4 sm:max-h-[calc(88vh-148px)]">
            {children}
          </div>
          <SheetFooter className="border-t border-border/60 bg-background/95 px-5 pb-5 pt-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
            {footer}
          </SheetFooter>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={dialogClassName}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {children}
        <DialogFooter>{footer}</DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Expenses() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const translateValidation = (message) => t(message, { defaultValue: message });
  const [searchParams, setSearchParams] = useSearchParams();
  const [actionError, setActionError] = React.useState("");

  const userQuery = useQuery({
    queryKey: ["users", "me"],
    queryFn: getCurrentUser,
  });
  const isPremium = !!userQuery.data?.is_premium;

  const [search, setSearch] = React.useState(() => searchParams.get("search") || "");
  const debouncedSearch = useDebounce(search, 300);
  const [category, setCategory] = React.useState(() => searchParams.get("category") || "");
  const [startDate, setStartDate] = React.useState(() => searchParams.get("start_date") || "");
  const [endDate, setEndDate] = React.useState(() => searchParams.get("end_date") || "");
  const [sort, setSort] = React.useState(() => searchParams.get("sort") || "newest");
  const [feedView, setFeedView] = React.useState(() => {
    const value = searchParams.get("view") || "all";
    return EXPENSE_FEED_VIEWS.includes(value) ? value : "all";
  });
  const todayISO = React.useMemo(() => toISODateInTimeZone(), []);

  const [page, setPage] = React.useState(() => parsePageParam(searchParams.get("page")));

  const [recurringCount, setRecurringCount] = React.useState(0);
  const [addOpen, setAddOpen] = React.useState(false);
  const [sessionOpen, setSessionOpen] = React.useState(false);
  const VALID_TABS = ["one-time", "recurring"];
  const [activeTab, setActiveTabState] = React.useState(() => {
    const tabParam = searchParams.get("tab");
    return VALID_TABS.includes(tabParam) ? tabParam : "one-time";
  });
  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (tab === "one-time") next.delete("tab");
      else next.set("tab", tab);
      return next;
    }, { replace: true });
  };
  const activeSessionDraftQuery = useQuery({
    queryKey: ["expenses", "session-draft", "active"],
    queryFn: getActiveSessionDraft,
    enabled: activeTab === "one-time",
    staleTime: 15_000,
  });
  const recurringAddRef = React.useRef(null);
  const [addTitle, setAddTitle] = React.useState("");
  const [addAmount, setAddAmount] = React.useState("");
  const [addCategory, setAddCategory] = React.useState("");
  const [addDescription, setAddDescription] = React.useState("");
  const [addDate, setAddDate] = React.useState("");
  const [addWalletId, setAddWalletId] = React.useState("");
  const [addSubcategoryId, setAddSubcategoryId] = React.useState("");
  const [addProjectId, setAddProjectId] = React.useState("");
  const [addProjectSubcategoryId, setAddProjectSubcategoryId] = React.useState("");
  const [addWalletMode, setAddWalletMode] = React.useState("single");
  const [addWalletAllocations, setAddWalletAllocations] = React.useState([]);
  const [touchedAdd, setTouchedAdd] = React.useState({});
  const [repairPrompt, setRepairPrompt] = React.useState(null);
  const [repairSourceCategory, setRepairSourceCategory] = React.useState("");
  const [repairSourceSubcategoryId, setRepairSourceSubcategoryId] = React.useState("buffer");
  const [repairAmount, setRepairAmount] = React.useState("");
  const [repairError, setRepairError] = React.useState("");
  const [repairPending, setRepairPending] = React.useState(false);
  const [savedExpensePayload, setSavedExpensePayload] = React.useState(null);

  const [splitMode, setSplitMode] = React.useState("none");
  const [splits, setSplits] = React.useState([]);

  React.useEffect(() => {
    if (splitMode === "equally") {
      const total = parseAmountInput(addAmount) || 0;
      const splitAmt = Math.round(total / (splits.length + 1));
      const formattedAmt = formatAmountInput(String(splitAmt));
      
      const needsUpdate = splits.some(s => s.amount !== formattedAmt);
      if (needsUpdate) {
        setSplits(prev => prev.map(s => ({ ...s, amount: formattedAmt })));
      }
    }
  }, [addAmount, splitMode, splits]);

  const [editOpen, setEditOpen] = React.useState(false);
  const [editExpense, setEditExpense] = React.useState(null);
  const [editTitle, setEditTitle] = React.useState("");
  const [editCategory, setEditCategory] = React.useState("");
  const [editDescription, setEditDescription] = React.useState("");
  const [editDate, setEditDate] = React.useState("");
  const [editSubcategoryId, setEditSubcategoryId] = React.useState("");
  const [editProjectId, setEditProjectId] = React.useState("");
  const [touchedEdit, setTouchedEdit] = React.useState({});

  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState(null);
  const [correctOpen, setCorrectOpen] = React.useState(false);
  const [correctTarget, setCorrectTarget] = React.useState(null);

  const [refundOpen, setRefundOpen] = React.useState(false);
  const [refundTarget, setRefundTarget] = React.useState(null);
  const [refundWalletId, setRefundWalletId] = React.useState("");
  const [refundAmount, setRefundAmount] = React.useState("");

  const [assetOpen, setAssetOpen] = React.useState(false);
  const [assetTarget, setAssetTarget] = React.useState(null);
  const [assetTitle, setAssetTitle] = React.useState("");
  const [assetDescription, setAssetDescription] = React.useState("");
  const [assetCurrentValue, setAssetCurrentValue] = React.useState("");

  const [recurringOpen, setRecurringOpen] = React.useState(false);
  const [recurringTarget, setRecurringTarget] = React.useState(null);
  const [recurringFrequency, setRecurringFrequency] = React.useState("MONTHLY");
  const [recurringStartDate, setRecurringStartDate] = React.useState("");
  const [recurringWalletId, setRecurringWalletId] = React.useState("");
  const [recurringCycleBehavior, setRecurringCycleBehavior] = React.useState("FIXED");

  const [splitOpen, setSplitOpen] = React.useState(false);
  const [splitTarget, setSplitTarget] = React.useState(null);
  const [splitRows, setSplitRows] = React.useState([]);
  const [mergeOpen, setMergeOpen] = React.useState(false);
  const [mergeTarget, setMergeTarget] = React.useState(null);
  const [mergeMode, setMergeMode] = React.useState("create");
  const [mergeTitle, setMergeTitle] = React.useState("");
  const [mergeDescription, setMergeDescription] = React.useState("");
  const [mergeExistingGroupId, setMergeExistingGroupId] = React.useState("");
  const [mergeSelectedExpenseIds, setMergeSelectedExpenseIds] = React.useState([]);

  const [descriptionOpen, setDescriptionOpen] = React.useState(false);
  const [descriptionTarget, setDescriptionTarget] = React.useState(null);
  const [expenseMenuForId, setExpenseMenuForId] = React.useState(null);
  const [expenseMenuPosition, setExpenseMenuPosition] = React.useState(null);
  const [expandedGroupIds, setExpandedGroupIds] = React.useState(() => new Set());

  const [windowWidth, setWindowWidth] = React.useState(typeof window !== "undefined" ? window.innerWidth : 1280);
  const localIdRef = React.useRef(1);
  const nextLocalId = React.useCallback((prefix = "local") => `${prefix}-${localIdRef.current++}`, []);
  React.useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const tCategory = (name) => t(`categories.${name}`, { defaultValue: name });
  const selectTriggerClass =
    "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
  const selectContentClass =
    "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";
  const appLang = String(i18n.language || i18n.resolvedLanguage || "en").toLowerCase();

  const _formatDisplayDateLocal = (value) => formatDisplayDate(value, appLang);
  const _formatMonthYearLocal = (value) => formatMonthYear(value, appLang);

  const queryParams = React.useMemo(() => {
    return {
      limit: PAGE_SIZE,
      skip: (page - 1) * PAGE_SIZE,
      view: feedView,
      search: debouncedSearch.trim() || undefined,
      category: category || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      sort,
    };
  }, [debouncedSearch, category, startDate, endDate, sort, page, feedView]);

  const currentMonthCountParams = React.useMemo(() => ({
    limit: 1,
    skip: 0,
    start_date: `${todayISO.slice(0, 7)}-01`,
    end_date: todayISO,
    sort: "newest",
  }), [todayISO]);

  const dateFilterError = React.useMemo(() => {
    if (startDate && startDate > todayISO) return t("expenses.startFuture");
    if (endDate && endDate > todayISO) return t("expenses.endFuture");
    if (startDate && endDate && startDate > endDate) return t("expenses.startAfterEnd");
    return "";
  }, [startDate, endDate, todayISO, t]);

  const expensesQuery = useExpensesQuery(queryParams, activeTab === "one-time" && !dateFilterError);
  const currentMonthCountQuery = useExpensesQuery(currentMonthCountParams, activeTab === "one-time");
  const categoriesQuery = useExpenseCategoriesQuery(activeTab === "one-time");
  const budgetsQuery = useQuery({ queryKey: ["budgets"], queryFn: getBudgets, enabled: activeTab === "one-time", staleTime: 60_000 });
  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: getProjects, enabled: activeTab === "one-time", staleTime: 60_000 });
  const walletsQuery = useQuery({ queryKey: ["wallets"], queryFn: getWallets, enabled: activeTab === "one-time" });
  const mergeGroupsQuery = useQuery({
    queryKey: ["expenses", "merge-groups"],
    queryFn: getExpenseMergeGroups,
    enabled: activeTab === "one-time",
    staleTime: 30_000,
  });
  const categories = categoriesQuery.data || EMPTY_ARRAY;
  const feedItems = expensesQuery.data?.items || EMPTY_ARRAY;
  const expenses = React.useMemo(() => {
    return feedItems.flatMap((item) => {
      if (item?.type === "EXPENSE" && item.expense) return [item.expense];
      if (item?.type === "MERGE_GROUP" && item.merge_group?.items) return item.merge_group.items;
      return [];
    });
  }, [feedItems]);
  const total = Number(expensesQuery.data?.total || 0);
  const currentMonthExpenseCount = Number(currentMonthCountQuery.data?.total || 0);
  const expenseMonthLimitReached = currentMonthExpenseCount >= MAX_EXPENSES_PER_MONTH;
  const hasNext = expenses.length === PAGE_SIZE;
  const loading = expensesQuery.isLoading || categoriesQuery.isLoading || walletsQuery.isLoading;
  const isFetching = expensesQuery.isFetching || categoriesQuery.isFetching || walletsQuery.isFetching;
  const walletRows = Array.isArray(walletsQuery.data) ? walletsQuery.data : EMPTY_ARRAY;
  const mergeGroups = Array.isArray(mergeGroupsQuery.data) ? mergeGroupsQuery.data : EMPTY_ARRAY;
  const budgetRows = Array.isArray(budgetsQuery.data) ? budgetsQuery.data : EMPTY_ARRAY;
  const projectRows = Array.isArray(projectsQuery.data) ? projectsQuery.data : EMPTY_ARRAY;
  const operationalWallets = walletRows.filter(w => {
    const s = w.status || (w.is_active === false ? "ARCHIVED" : "ACTIVE");
    return s === "ACTIVE";
  });
  const [subcategoryOptionsByBudgetId, setSubcategoryOptionsByBudgetId] = React.useState({});
  const [projectSubcategoryOptionsByProjectCategory, setProjectSubcategoryOptionsByProjectCategory] = React.useState({});

  const getBudgetForCategoryAndDate = React.useCallback((categoryValue, isoDate) => {
    if (!categoryValue || !isoDate) return null;
    const [yearRaw, monthRaw] = String(isoDate).split("-");
    const year = Number(yearRaw);
    const month = Number(monthRaw);
    return budgetRows.find(
      (budget) => Number(budget.budget_year) === year
        && Number(budget.budget_month) === month
        && budget.category === categoryValue,
    ) || null;
  }, [budgetRows]);

  const addBudgetForCategory = React.useMemo(
    () => getBudgetForCategoryAndDate(addCategory, addDate || todayISO),
    [getBudgetForCategoryAndDate, addCategory, addDate, todayISO],
  );
  const addExpenseAmount = React.useMemo(() => parseAmountInput(addAmount) || 0, [addAmount]);
  const editBudgetForCategory = React.useMemo(
    () => getBudgetForCategoryAndDate(editCategory, editDate || todayISO),
    [getBudgetForCategoryAndDate, editCategory, editDate, todayISO],
  );
  const splitBudgetTargets = React.useMemo(() => {
    if (!splitOpen || !splitTarget) return EMPTY_ARRAY;
    const byId = new Map();
    splitRows.forEach((row) => {
      const rowCategory = row.category || splitTarget.category;
      const budget = getBudgetForCategoryAndDate(rowCategory, splitTarget.date || todayISO);
      if (budget) byId.set(budget.id, budget);
    });
    return Array.from(byId.values());
  }, [getBudgetForCategoryAndDate, splitOpen, splitRows, splitTarget, todayISO]);

  const addProject = React.useMemo(
    () => projectRows.find((project) => String(project.id) === String(addProjectId)) || null,
    [projectRows, addProjectId],
  );
  const editProject = React.useMemo(
    () => projectRows.find((project) => String(project.id) === String(editProjectId)) || null,
    [projectRows, editProjectId],
  );

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const targets = [addBudgetForCategory, editBudgetForCategory, ...splitBudgetTargets].filter(Boolean);
      const missing = targets.filter((budget) => subcategoryOptionsByBudgetId[budget.id] === undefined);
      if (!missing.length) return;
      try {
        const entries = await Promise.all(missing.map(async (budget) => [budget.id, await getBudgetSubcategories(budget.id)]));
        if (cancelled) return;
        setSubcategoryOptionsByBudgetId((prev) => {
          const next = { ...prev };
          entries.forEach(([budgetId, rows]) => {
            next[budgetId] = Array.isArray(rows) ? rows : [];
          });
          return next;
        });
      } catch {
        if (!cancelled) return;
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [addBudgetForCategory, editBudgetForCategory, splitBudgetTargets, subcategoryOptionsByBudgetId]);

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const targets = [
        addProject ? { projectId: addProject.id, category: addCategory } : null,
        editProject ? { projectId: editProject.id, category: editCategory } : null,
      ].filter((item) => item && item.category && item.projectId && item.projectId !== "" && item.projectId !== null);
      const missing = targets.filter(({ projectId, category }) => projectSubcategoryOptionsByProjectCategory[`${projectId}:${category}`] === undefined);
      if (!missing.length) return;
      try {
        const entries = await Promise.all(
          missing.map(async ({ projectId, category }) => [`${projectId}:${category}`, await getProjectSubcategories(projectId, category)]),
        );
        if (cancelled) return;
        setProjectSubcategoryOptionsByProjectCategory((prev) => {
          const next = { ...prev };
          entries.forEach(([key, rows]) => {
            next[key] = Array.isArray(rows) ? rows : [];
          });
          return next;
        });
      } catch {
        if (!cancelled) return;
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [addProject, addCategory, editProject, editCategory, projectSubcategoryOptionsByProjectCategory]);

  const getSubcategoryOptionsForBudget = React.useCallback(
    (budget) => (budget ? (subcategoryOptionsByBudgetId[budget.id] || EMPTY_ARRAY) : EMPTY_ARRAY),
    [subcategoryOptionsByBudgetId],
  );
  const addSelectedSubcategory = React.useMemo(() => {
    if (!addBudgetForCategory || !addSubcategoryId) return null;
    return getSubcategoryOptionsForBudget(addBudgetForCategory)
      .find((item) => String(item.id) === String(addSubcategoryId)) || null;
  }, [addBudgetForCategory, addSubcategoryId, getSubcategoryOptionsForBudget]);
  const addOverBudgetWarning = React.useMemo(() => {
    if (!addBudgetForCategory || !addCategory || addExpenseAmount <= 0 || addProject?.is_isolated) return null;
    const remaining = Number(addBudgetForCategory.remaining ?? 0);
    const projectedRemaining = remaining - addExpenseAmount;
    if (projectedRemaining >= 0) return null;
    return {
      type: "category",
      category: addCategory,
      budgetYear: Number(addBudgetForCategory.budget_year),
      budgetMonth: Number(addBudgetForCategory.budget_month),
      monthlyLimit: Number(addBudgetForCategory.monthly_limit || 0),
      overage: Math.abs(projectedRemaining),
      projectedRemaining,
    };
  }, [addBudgetForCategory, addCategory, addExpenseAmount, addProject]);
  const addSubcategoryWarning = React.useMemo(() => {
    if (!addBudgetForCategory || !addSelectedSubcategory || addExpenseAmount <= 0 || addProject?.is_isolated) return null;
    if (addSelectedSubcategory.remaining === null || addSelectedSubcategory.remaining === undefined) return null;
    const projectedRemaining = Number(addSelectedSubcategory.remaining || 0) - addExpenseAmount;
    if (projectedRemaining >= 0) return null;
    const subcategories = getSubcategoryOptionsForBudget(addBudgetForCategory);
    return {
      type: "subcategory",
      category: addCategory,
      budgetId: addBudgetForCategory.id,
      budgetYear: Number(addBudgetForCategory.budget_year),
      budgetMonth: Number(addBudgetForCategory.budget_month),
      monthlyLimit: Number(addBudgetForCategory.monthly_limit || 0),
      subcategoryId: addSelectedSubcategory.id,
      subcategoryName: addSelectedSubcategory.name,
      subcategories: subcategories.map((subcategory) => ({
        id: subcategory.id,
        name: subcategory.name,
        monthly_limit: subcategory.monthly_limit,
        remaining: subcategory.remaining,
      })),
      overage: Math.abs(projectedRemaining),
      projectedRemaining,
    };
  }, [addBudgetForCategory, addCategory, addSelectedSubcategory, addExpenseAmount, addProject, getSubcategoryOptionsForBudget]);
  const repairSourceBudgets = React.useMemo(() => {
    if (!repairPrompt || repairPrompt.type !== "category") return EMPTY_ARRAY;
    return budgetRows.filter((budget) => (
      Number(budget.budget_year) === Number(repairPrompt.budgetYear)
      && Number(budget.budget_month) === Number(repairPrompt.budgetMonth)
      && budget.category !== repairPrompt.category
      && Number(budget.effective_available ?? budget.remaining ?? 0) > 0
    ));
  }, [budgetRows, repairPrompt]);
  const repairSubcategorySources = React.useMemo(() => {
    if (!repairPrompt || repairPrompt.type !== "subcategory") {
      return { buffer: 0, siblings: EMPTY_ARRAY };
    }
    const subcategories = Array.isArray(repairPrompt.subcategories) ? repairPrompt.subcategories : EMPTY_ARRAY;
    const limitTotal = subcategories.reduce((sum, subcategory) => sum + Number(subcategory.monthly_limit || 0), 0);
    const siblings = subcategories
      .filter((subcategory) => String(subcategory.id) !== String(repairPrompt.subcategoryId))
      .filter((subcategory) => subcategory.monthly_limit !== null && subcategory.monthly_limit !== undefined)
      .map((subcategory) => ({
        ...subcategory,
        available: Math.max(Number(subcategory.remaining || 0), 0),
      }));
    return {
      buffer: Math.max(Number(repairPrompt.monthlyLimit || 0) - limitTotal, 0),
      siblings,
    };
  }, [repairPrompt]);
  const selectedRepairSubcategorySourceAvailable = React.useMemo(() => {
    if (!repairPrompt || repairPrompt.type !== "subcategory") return 0;
    if (repairSourceSubcategoryId === "buffer") return repairSubcategorySources.buffer;
    const sibling = repairSubcategorySources.siblings.find((subcategory) => String(subcategory.id) === String(repairSourceSubcategoryId));
    return Number(sibling?.available || 0);
  }, [repairPrompt, repairSourceSubcategoryId, repairSubcategorySources]);
  const repairAmountValue = React.useMemo(() => parseAmountInput(repairAmount) || 0, [repairAmount]);
  React.useEffect(() => {
    if (!repairPrompt) {
      setRepairSourceCategory("");
      setRepairSourceSubcategoryId("buffer");
      setRepairAmount("");
      setRepairError("");
      return;
    }
    if (repairPrompt.type === "budget_required") {
      setRepairAmount(formatAmountInput(String(repairPrompt.suggestedAmount || 0)));
      setRepairSourceCategory("");
      setRepairSourceSubcategoryId("buffer");
      setRepairError("");
      return;
    }
    setRepairAmount(formatAmountInput(String(repairPrompt.overage || 0)));
    if (repairPrompt.type === "subcategory") {
      setRepairSourceCategory("");
      const subcategories = Array.isArray(repairPrompt.subcategories) ? repairPrompt.subcategories : EMPTY_ARRAY;
      const limitTotal = subcategories.reduce((sum, subcategory) => sum + Number(subcategory.monthly_limit || 0), 0);
      const buffer = Math.max(Number(repairPrompt.monthlyLimit || 0) - limitTotal, 0);
      const firstSibling = subcategories
        .filter((subcategory) => String(subcategory.id) !== String(repairPrompt.subcategoryId))
        .filter((subcategory) => subcategory.monthly_limit !== null && subcategory.monthly_limit !== undefined)
        .find((subcategory) => Math.max(Number(subcategory.remaining || 0), 0) > 0);
      setRepairSourceSubcategoryId(buffer > 0 ? "buffer" : firstSibling ? String(firstSibling.id) : "buffer");
      setRepairError("");
      return;
    }
    setRepairSourceSubcategoryId("buffer");
    const firstSource = budgetRows.find((budget) => (
      Number(budget.budget_year) === Number(repairPrompt.budgetYear)
      && Number(budget.budget_month) === Number(repairPrompt.budgetMonth)
      && budget.category !== repairPrompt.category
      && Number(budget.effective_available ?? budget.remaining ?? 0) > 0
    ));
    setRepairSourceCategory(firstSource ? firstSource.category : "");
    setRepairError("");
  }, [budgetRows, repairPrompt]);
  const getProjectSubcategoryOptions = React.useCallback(
    (projectId, categoryValue) => {
      if (!projectId || !categoryValue) return EMPTY_ARRAY;
      return projectSubcategoryOptionsByProjectCategory[`${projectId}:${categoryValue}`] || EMPTY_ARRAY;
    },
    [projectSubcategoryOptionsByProjectCategory],
  );

  const defaultWalletId = React.useMemo(() => {
    const dw = operationalWallets.find(w => w.is_default);
    return dw ? String(dw.id) : "";
  }, [operationalWallets]);
  const error = dateFilterError
    ? dateFilterError
    : (expensesQuery.error || categoriesQuery.error)
      ? localizeApiError(expensesQuery.error?.message || categoriesQuery.error?.message, t) ||
      expensesQuery.error?.message ||
      categoriesQuery.error?.message ||
      t("expenses.loadFailed")
      : "";

  const orderedCategories = React.useMemo(() => {
    const set = new Set(categories);
    const inOrder = CATEGORIES.filter((c) => set.has(c));
    const extras = [...set].filter((c) => !CATEGORIES.includes(c));
    // Filter out Bank Fees & Interest to prevent users from adding them as general expenses.
    // They must use the wallet quick actions instead.
    return [...inOrder, ...extras].filter(c => c !== "Bank Fees & Interest");
  }, [categories]);

  const preferredAddCategory = React.useMemo(() => {
    const storedCategory = getStoredLastExpenseCategory();
    if (storedCategory && orderedCategories.includes(storedCategory)) return storedCategory;

    const recentCategory = expenses.find((item) => item?.category && orderedCategories.includes(item.category))?.category;
    return recentCategory || "";
  }, [expenses, orderedCategories]);

  const getActionErrorMessage = (e, options = {}) => {
    const rawMessage = String(e?.message || "");
    const msg = rawMessage.toLowerCase();
    const selectedCategory = options.category || "";
    const selectedDate = options.date || "";

    if (
      msg === "expenses.budget_required" ||
      msg.includes("cannot create an expense for") ||
      msg.includes("cannot add expense for")
    ) {
      if (selectedCategory) {
        if (selectedDate) {
          return t("expenses.budgetRequiredForMonth", {
            category: tCategory(selectedCategory),
            month: _formatMonthYearLocal(selectedDate),
          });
        }
        return t("expenses.budgetRequired", { category: tCategory(selectedCategory) });
      }
    }

    if (e?.status === 429) {
      const wait = Number(e?.retryAfterSeconds || 0);
      if (Number.isFinite(wait) && wait > 0) {
        return t("expenses.tooManyWait", { seconds: wait });
      }
      return t("expenses.tooManySoon");
    }
    return localizeApiError(e?.message, t) || e?.message || t("expenses.requestFailed");
  };

  React.useEffect(() => {
    const next = new URLSearchParams();
    if (activeTab === "recurring") {
      next.set("tab", "recurring");
      const currentSearch = searchParams.get("r_search");
      const currentPage = searchParams.get("r_page");
      if (currentSearch) next.set("r_search", currentSearch);
      if (currentPage && currentPage !== "1") next.set("r_page", currentPage);
    } else {
      if (feedView !== "all") next.set("view", feedView);
      if (debouncedSearch.trim()) next.set("search", debouncedSearch.trim());
      if (category) next.set("category", category);
      if (startDate) next.set("start_date", startDate);
      if (endDate) next.set("end_date", endDate);
      if (sort && sort !== "newest") next.set("sort", sort);
      if (page > 1) next.set("page", String(page));
    }
    setSearchParams(next, { replace: true });
  }, [debouncedSearch, category, startDate, endDate, sort, page, activeTab, feedView, searchParams, setSearchParams]);

  const resetToFirstPage = () => setPage(1);
  const resetFilters = () => {
    setSearch("");
    setCategory("");
    setStartDate("");
    setEndDate("");
    setSort("newest");
    setFeedView("all");
    setPage(1);
  };

  const openAdd = () => {
    setActionError("");
    setRepairPrompt(null);
    setSavedExpensePayload(null);
    setAddTitle("");
    setAddAmount("");
    setAddCategory(preferredAddCategory);
    setAddDescription("");
    setAddDate(todayISO);
    setAddWalletId(defaultWalletId);
    setAddSubcategoryId("");
    setAddProjectId("");
    setAddProjectSubcategoryId("");
    setAddWalletMode("single");
    setAddWalletAllocations(defaultWalletId ? [{ id: nextLocalId("wallet"), wallet_id: defaultWalletId, amount: "" }] : []);
    setTouchedAdd({});
    setSplitMode("none");
    setSplits([]);
    setAddOpen(true);
  };

  const prefillAddFromExpense = React.useCallback((expense) => {
    const walletAllocations = Array.isArray(expense?.wallet_allocations) ? expense.wallet_allocations : [];
    const isMultiWallet = walletAllocations.length > 1;
    const fallbackWalletId = expense?.wallet_id || defaultWalletId || "";

    setActionError("");
    setAddTitle(expense?.title || "");
    setAddAmount(formatAmountInput(String(expense?.amount || "")));
    setAddCategory(expense?.category || preferredAddCategory);
    setAddDescription(expense?.description || "");
    setAddDate(expense?.date || todayISO);
    setAddSubcategoryId(expense?.subcategory_id ? String(expense.subcategory_id) : "");
    setAddProjectId(expense?.project_id ? String(expense.project_id) : "");
    setAddProjectSubcategoryId(expense?.project_subcategory_id ? String(expense.project_subcategory_id) : "");
    setTouchedAdd({});
    setSplitMode("none");
    setSplits([]);

    if (isMultiWallet) {
      setAddWalletMode("multi");
      setAddWalletId("");
      setAddWalletAllocations(walletAllocations.map((allocation) => ({
        id: nextLocalId("wallet"),
        wallet_id: allocation?.wallet_id ? String(allocation.wallet_id) : "",
        amount: formatAmountInput(String(allocation?.amount || "")),
      })));
      return;
    }

    setAddWalletMode("single");
    setAddWalletId(fallbackWalletId ? String(fallbackWalletId) : "");
    setAddWalletAllocations(
      fallbackWalletId
        ? [{
            id: nextLocalId("wallet"),
            wallet_id: String(fallbackWalletId),
            amount: formatAmountInput(String(expense?.amount || "")),
          }]
        : [],
    );
  }, [defaultWalletId, nextLocalId, preferredAddCategory, todayISO]);

  const openEdit = (expense) => {
    setActionError("");
    setEditExpense(expense);
    setEditTitle(expense.title || "");
    setEditCategory(expense.category || "");
    setEditDescription(expense.description || "");
    setEditDate(expense.date || "");
    setEditSubcategoryId(expense.subcategory_id ? String(expense.subcategory_id) : "");
    setEditProjectId(expense.project_id ? String(expense.project_id) : "");
    setTouchedEdit({});
    setEditOpen(true);
  };

  const openDelete = (expense) => {
    setActionError("");
    setDeleteTarget(expense);
    setDeleteOpen(true);
  };

  const openCorrect = (expense) => {
    setActionError("");
    setCorrectTarget(expense);
    setCorrectOpen(true);
  };

  const openDescription = (expense) => {
    setDescriptionTarget(expense);
    setDescriptionOpen(true);
  };

  const openAsset = (expense) => {
    setAssetTarget(expense);
    setAssetTitle(expense?.title || "");
    setAssetDescription(expense?.description || "");
    setAssetCurrentValue(formatAmountInput(String(expense?.amount || "")));
    setAssetOpen(true);
  };

  const openRecurring = (expense) => {
    setRecurringTarget(expense);
    setRecurringFrequency("MONTHLY");
    setRecurringStartDate(expense?.date || todayISO);
    setRecurringWalletId(String(expense?.wallet_id || ""));
    setRecurringCycleBehavior("FIXED");
    setRecurringOpen(true);
  };

  const openSplit = (expense) => {
    if ((expense?.split_items?.length || 0) > 1) {
      setActionError(t("expenses.splitParentLocked", { defaultValue: "Already split. Breakdown editing is not available yet." }));
      return;
    }
    setSplitTarget(expense);
    setSplitRows([
      {
        id: `seed-${expense?.id}-1`,
        label: "",
        amount: "",
        category: expense?.category || "",
        subcategory_id: "",
      },
      {
        id: `seed-${expense?.id}-2`,
        label: "",
        amount: "",
        category: expense?.category || "",
        subcategory_id: "",
      },
    ]);
    setSplitOpen(true);
  };

  const openMerge = (expense) => {
    const candidateIds = expenses
      .filter((item) => item.id !== expense.id && item.transaction_type === "EXPENSE" && !item.merge_group_id)
      .map((item) => item.id);
    setMergeTarget(expense);
    setMergeMode(expense?.merge_group_id ? "remove" : "create");
    setMergeTitle("");
    setMergeDescription("");
    setMergeExistingGroupId("");
    setMergeSelectedExpenseIds(candidateIds.slice(0, 1));
    setMergeOpen(true);
  };

  React.useEffect(() => {
    const onPointerDown = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("[data-action-popover]")) return;
      setExpenseMenuForId(null);
      setExpenseMenuPosition(null);
    };
    const handleScroll = () => {
      if (expenseMenuForId !== null) {
        setExpenseMenuForId(null);
        setExpenseMenuPosition(null);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("scroll", handleScroll, true);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("scroll", handleScroll, true);
    };
  }, [expenseMenuForId]);

  const openExpenseActions = (event, expense) => {
    setActionError("");
    const button = event.currentTarget;
    const rect = button instanceof HTMLElement ? button.getBoundingClientRect() : null;
    const menuWidth = 176;
    const menuHeight = 120;
    const viewportPadding = 8;
    setExpenseMenuForId((prev) => {
      if (prev === expense.id) {
        setExpenseMenuPosition(null);
        return null;
      }
      if (!rect) return null;
      const fitsBelow = rect.bottom + 6 + menuHeight <= window.innerHeight - viewportPadding;
      const top = fitsBelow ? rect.bottom + 6 : rect.top - 6 - menuHeight;
      const left = Math.max(
        viewportPadding,
        Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - viewportPadding)
      );
      setExpenseMenuPosition({ top, left });
      return expense.id;
    });
  };

  const goPrevPage = () => {
    if (loading || isFetching) return;
    if (page <= 1) return;
    setPage((p) => Math.max(1, p - 1));
  };

  const goNextPage = () => {
    if (loading || isFetching) return;
    if (!hasNext) return;
    setPage((p) => p + 1);
  };

  const totalSplitAmount = React.useMemo(() => {
    return splits.reduce((sum, s) => sum + (parseAmountInput(String(s.amount)) || 0), 0);
  }, [splits]);

  const personalSpend = React.useMemo(() => {
    const total = parseAmountInput(addAmount) || 0;
    return Math.max(0, total - totalSplitAmount);
  }, [addAmount, totalSplitAmount]);

  const addExpenseParsed = React.useMemo(
    () =>
      expenseFormSchema.safeParse({
        title: addTitle,
        amount: addAmount,
        category: addCategory,
        date: addDate,
        wallet_id: addWalletId ? Number(addWalletId) : null,
        description: addDescription,
        splits: splitMode !== "none" && splits.length > 0 ? splits : undefined,
      }),
    [addTitle, addAmount, addCategory, addDate, addWalletId, addDescription, splitMode, splits]
  );

  const addErrors = React.useMemo(() => {
    if (addExpenseParsed.success) return {};
    const errs = {};
    addExpenseParsed.error.issues.forEach((issue) => {
      const pathKey = issue.path.join(".");
      if (issue.path[0] === "splits_total") {
        if (!errs[pathKey]) errs[pathKey] = t(issue.message, { defaultValue: issue.message });
      } else if (issue.path[0] === "splits") {
        if (!errs[pathKey] && touchedAdd[pathKey]) errs[pathKey] = t(issue.message, { defaultValue: issue.message });
      } else {
        const field = issue.path[0];
        if (field && !errs[field] && touchedAdd[field]) {
          errs[field] = t(issue.message, { defaultValue: issue.message });
        }
      }
    });
    return errs;
  }, [addExpenseParsed, t, touchedAdd]);

  const addExpenseMutation = useCreateExpenseMutation();
  const updateExpenseMutation = useUpdateExpenseMutation();
  const deleteExpenseMutation = useDeleteExpenseMutation();
  const refundExpenseMutation = useRefundExpenseMutation();
  const splitExpenseMutation = useSplitExpenseMutation();
  const markExpenseAsAssetMutation = useMarkExpenseAsAssetMutation();
  const markExpenseAsRecurringMutation = useMarkExpenseAsRecurringMutation();
  const createExpenseMergeGroupMutation = useCreateExpenseMergeGroupMutation();
  const addExpensesToMergeGroupMutation = useAddExpensesToMergeGroupMutation();
  const removeExpenseFromMergeGroupMutation = useRemoveExpenseFromMergeGroupMutation();

  const isAdding = addExpenseMutation.isPending;
  const isEditing = updateExpenseMutation.isPending;
  const isDeleting = deleteExpenseMutation.isPending;
  const canSubmitAddExpense = addExpenseParsed.success && !isAdding && !expenseMonthLimitReached;

  const editExpenseParsed = React.useMemo(
    () =>
      expenseUpdateFormSchema.safeParse({
        title: editTitle,
        description: editDescription,
      }),
    [editTitle, editDescription]
  );

  const editErrors = React.useMemo(() => {
    if (editExpenseParsed.success) return {};
    const errs = {};
    editExpenseParsed.error.issues.forEach((issue) => {
      const field = issue.path[0];
      if (field && !errs[field] && touchedEdit[field]) {
        errs[field] = t(issue.message, { defaultValue: issue.message });
      }
    });
    return errs;
  }, [editExpenseParsed, t, touchedEdit]);

  const canSubmitEditExpense = editExpenseParsed.success && !isEditing;

  const invalidateBudgetRepairQueries = React.useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["budgets"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
      queryClient.invalidateQueries({ queryKey: ["expenses"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    ]);
  }, [queryClient]);

  const handleAdd = async (keepOpen = false) => {
    if (isAdding) return;
    const parsed = expenseFormSchema.safeParse({
      title: addTitle,
      amount: addAmount,
      category: addCategory,
      date: addDate,
      description: addDescription,
      wallet_id: addWalletId ? Number(addWalletId) : null,
    });
    if (!parsed.success) {
      const firstIssue = parsed.error.issues[0];
      return setActionError(translateValidation(firstIssue?.message || t("expenses.requestFailed")));
    }

    const isMultiWallet = addWalletMode === "multi";
    const amount = Math.abs(parsed.data.amount);

    const walletAllocations = isMultiWallet
      ? addWalletAllocations
          .map((row) => ({
            wallet_id: row.wallet_id,
            amount: parseAmountInput(String(row.amount)),
          }))
          .filter((row) => row.wallet_id && row.amount > 0)
      : [];

    if (isMultiWallet) {
      const totalAllocated = walletAllocations.reduce((sum, row) => sum + row.amount, 0);
      if (walletAllocations.length < 2) {
        return setActionError(t("expenses.multiWalletNeedTwo", { defaultValue: "Add at least two wallet legs for multi-wallet quick add." }));
      }
      if (totalAllocated !== amount) {
        return setActionError(t("expenses.walletAllocationMismatch", { defaultValue: "Wallet allocations must exactly match the expense amount." }));
      }
    }

    const walletChecks = isMultiWallet
      ? walletAllocations
      : [{ wallet_id: parsed.data.wallet_id, amount }];

    for (const walletCheck of walletChecks) {
      if (!walletCheck.wallet_id) {
        return setActionError(t("expenses.walletRequired", { defaultValue: "Select a wallet for this expense." }));
      }
      const selectedWallet = walletRows.find(w => String(w.id) === String(walletCheck.wallet_id));
      if (!selectedWallet) continue;
      const potentialBalance = selectedWallet.current_balance - Math.abs(walletCheck.amount);
      const isCredit = selectedWallet.wallet_type?.toUpperCase() === "CREDIT";
      const isPreloaded = selectedWallet.wallet_type?.toUpperCase() === "PRELOADED";

      let floor = 0;
      if (isCredit) {
        floor = -selectedWallet.credit_limit;
        if (selectedWallet.allow_overlimit) floor = -Infinity;
      } else if (isPreloaded) {
        if (selectedWallet.has_overdraft) {
          floor = selectedWallet.overdraft_limit > 0 ? -selectedWallet.overdraft_limit : -Infinity;
        } else {
          floor = 0;
        }
      } else {
        floor = selectedWallet.has_overdraft ? -selectedWallet.overdraft_limit : 0;
      }

      const isBypassCategory = parsed.data.category === "Bank Fees & Interest";
      if (potentialBalance < floor && !isBypassCategory) {
        return setActionError(t("wallets.insufficientFunds"));
      }
    }

    try {
      const postSaveRepairWarning = addSubcategoryWarning || addOverBudgetWarning;
      await addExpenseMutation.mutateAsync({
        title: parsed.data.title,
        amount: parsed.data.amount,
        category: parsed.data.category,
        description: parsed.data.description ?? null,
        date: parsed.data.date,
        wallet_allocations: isMultiWallet
          ? walletAllocations
          : [{ wallet_id: Number(parsed.data.wallet_id), amount }],
        subcategory_id: addSubcategoryId ? Number(addSubcategoryId) : null,
        project_id: addProjectId ? Number(addProjectId) : null,
        project_subcategory_id: addProjectSubcategoryId ? Number(addProjectSubcategoryId) : null,
        splits: splitMode !== "none" && splits.length > 0 ? splits.map(s => ({ contact_name: s.contact_name, amount: parseAmountInput(String(s.amount)) })) : undefined,
      });
      setStoredLastExpenseCategory(parsed.data.category);
      if (postSaveRepairWarning) {
        await invalidateBudgetRepairQueries();
        setRepairPrompt({
          ...postSaveRepairWarning,
          categoryLabel: tCategory(postSaveRepairWarning.category),
        });
      }
      if (keepOpen === true) {
        setAddTitle("");
        setAddAmount("");
        setAddDescription("");
        setAddSubcategoryId("");
        setAddProjectId("");
        setAddProjectSubcategoryId("");
        setAddWalletMode("single");
        setAddWalletAllocations(defaultWalletId ? [{ id: nextLocalId("wallet"), wallet_id: defaultWalletId, amount: "" }] : []);
        setTouchedAdd({});
        setSplitMode("none");
        setSplits([]);
        toast.success(t("expenses.addSuccess", { defaultValue: "Expense saved!" }));
      } else {
        setAddOpen(false);
        toast.success(t("expenses.addSuccess", { defaultValue: "Expense added successfully" }));
      }
    } catch (e) {
      const rawMsg = String(e?.message || "");
      const isBudgetRequired = rawMsg === "expenses.budget_required"
        || rawMsg.includes("expenses.budget_required");

      if (isBudgetRequired) {
        const [budgetYear, budgetMonth] = String(parsed.data.date || "").split("-").map(Number);
        const payload = {
          title: parsed.data.title,
          amount: parsed.data.amount,
          category: parsed.data.category,
          description: parsed.data.description ?? null,
          date: parsed.data.date,
          wallet_allocations: isMultiWallet
            ? walletAllocations
            : [{ wallet_id: Number(parsed.data.wallet_id), amount }],
          subcategory_id: addSubcategoryId ? Number(addSubcategoryId) : null,
          project_id: addProjectId ? Number(addProjectId) : null,
          project_subcategory_id: addProjectSubcategoryId ? Number(addProjectSubcategoryId) : null,
          splits: splitMode !== "none" && splits.length > 0
            ? splits.map(s => ({ contact_name: s.contact_name, amount: parseAmountInput(String(s.amount)) }))
            : undefined,
        };
        const suggestedAmount = Math.abs(Number(parsed.data.amount)) || 0;
        setSavedExpensePayload({ payload, keepOpen });
        setRepairPrompt({
          type: "budget_required",
          category: parsed.data.category,
          categoryLabel: tCategory(parsed.data.category),
          budgetYear: Number.isFinite(budgetYear) ? budgetYear : new Date().getFullYear(),
          budgetMonth: Number.isFinite(budgetMonth) ? budgetMonth : (new Date().getMonth() + 1),
          suggestedAmount,
          expenseDate: parsed.data.date,
        });
        return;
      }

      setActionError(getActionErrorMessage(e, { category: parsed.data.category, date: parsed.data.date }));
    }
  };

  const handleEdit = async () => {
    if (isEditing) return;
    if (!editExpense) return;
    const parsed = expenseUpdateFormSchema.safeParse({
      title: editTitle,
      description: editDescription,
    });
    if (!parsed.success) {
      const firstIssue = parsed.error.issues[0];
      return setActionError(translateValidation(firstIssue?.message || t("expenses.requestFailed")));
    }

    try {
      await updateExpenseMutation.mutateAsync({
        id: editExpense.id,
        payload: {
          title: parsed.data.title,
          description: parsed.data.description,
        },
      });
      setEditOpen(false);
      toast.neutral(t("expenses.updateSuccess", { defaultValue: "Expense updated successfully" }));
    } catch (e) {
      setActionError(getActionErrorMessage(e, { category: editCategory, date: editDate }));
    }
  };

  const closeRepairPrompt = React.useCallback(() => {
    setRepairPrompt(null);
    setRepairError("");
    setSavedExpensePayload(null);
  }, []);

  const handleRepairReallocate = async () => {
    if (!repairPrompt || repairPending) return;
    if (repairPrompt.type === "subcategory") {
      if (!repairSourceSubcategoryId) {
        setRepairError(t("budgets.reallocateSourceRequired", { defaultValue: "Choose a source category." }));
        return;
      }
      if (!Number.isFinite(repairAmountValue) || repairAmountValue <= 0) {
        setRepairError(t("budgets.reallocateAmountRequired", { defaultValue: "Enter a positive amount." }));
        return;
      }
      if (selectedRepairSubcategorySourceAvailable < repairAmountValue) {
        setRepairError(
          t("expenses.subcategoryRepairSourceShort", {
            defaultValue: "Selected source only has {{amount}} available.",
            amount: formatUzs(selectedRepairSubcategorySourceAvailable),
          }),
        );
        return;
      }
      setRepairPending(true);
      setRepairError("");
      try {
        await reallocateBudgetSubcategory(repairPrompt.budgetId, {
          from_subcategory_id: repairSourceSubcategoryId === "buffer" ? null : Number(repairSourceSubcategoryId),
          to_subcategory_id: Number(repairPrompt.subcategoryId),
          amount: repairAmountValue,
        });
        await invalidateBudgetRepairQueries();
        toast.success(
          t("expenses.repairSaved", { defaultValue: "Budget repaired" }),
          t("expenses.subcategoryRepairReallocatedDetail", {
            defaultValue: "{{amount}} moved into {{subcategory}} inside {{category}}.",
            amount: formatUzs(repairAmountValue),
            subcategory: repairPrompt.subcategoryName,
            category: repairPrompt.categoryLabel,
          }),
        );
        closeRepairPrompt();
      } catch (e) {
        setRepairError(localizeApiError(e?.message, t) || e?.message || t("expenses.requestFailed"));
      } finally {
        setRepairPending(false);
      }
      return;
    }
    if (!repairSourceCategory) {
      setRepairError(t("budgets.reallocateSourceRequired", { defaultValue: "Choose a source category." }));
      return;
    }
    if (!Number.isFinite(repairAmountValue) || repairAmountValue <= 0) {
      setRepairError(t("budgets.reallocateAmountRequired", { defaultValue: "Enter a positive amount." }));
      return;
    }
    setRepairPending(true);
    setRepairError("");
    try {
      await reallocateBudget({
        budget_year: repairPrompt.budgetYear,
        budget_month: repairPrompt.budgetMonth,
        from_category: repairSourceCategory,
        to_category: repairPrompt.category,
        amount: repairAmountValue,
      });
      await invalidateBudgetRepairQueries();
      toast.success(
        t("expenses.repairSaved", { defaultValue: "Budget repaired" }),
        t("expenses.repairReallocatedDetail", {
          defaultValue: "{{amount}} moved into {{category}}.",
          amount: formatUzs(repairAmountValue),
          category: repairPrompt.categoryLabel,
        }),
      );
      closeRepairPrompt();
    } catch (e) {
      setRepairError(localizeApiError(e?.message, t) || e?.message || t("expenses.requestFailed"));
    } finally {
      setRepairPending(false);
    }
  };

  const handleRepairIncreaseLimit = async () => {
    if (!repairPrompt || repairPending) return;
    if (!Number.isFinite(repairAmountValue) || repairAmountValue <= 0) {
      setRepairError(t("budgets.reallocateAmountRequired", { defaultValue: "Enter a positive amount." }));
      return;
    }
    setRepairPending(true);
    setRepairError("");
    try {
      await updateBudget(
        repairPrompt.category,
        Number(repairPrompt.monthlyLimit || 0) + repairAmountValue,
        repairPrompt.budgetYear,
        repairPrompt.budgetMonth,
      );
      await invalidateBudgetRepairQueries();
      toast.success(
        t("expenses.repairSaved", { defaultValue: "Budget repaired" }),
        t("expenses.repairIncreasedDetail", {
          defaultValue: "{{category}} limit increased by {{amount}}.",
          amount: formatUzs(repairAmountValue),
          category: repairPrompt.categoryLabel,
        }),
      );
      closeRepairPrompt();
    } catch (e) {
      setRepairError(localizeApiError(e?.message, t) || e?.message || t("expenses.requestFailed"));
    } finally {
      setRepairPending(false);
    }
  };

  const handleRepairCreateBudget = async () => {
    if (!repairPrompt || repairPrompt.type !== "budget_required" || repairPending) return;
    const { category, budgetYear, budgetMonth, suggestedAmount } = repairPrompt;
    const limit = Number.isFinite(repairAmountValue) && repairAmountValue > 0
      ? repairAmountValue
      : Math.max(suggestedAmount, 1000);

    setRepairPending(true);
    setRepairError("");

    try {
      await createBudget(category, limit, budgetYear, budgetMonth);
      await invalidateBudgetRepairQueries();
    } catch (e) {
      setRepairError(localizeApiError(e?.message, t) || e?.message || t("expenses.requestFailed"));
      setRepairPending(false);
      return;
    }

    // Budget created — replay the original expense
    if (!savedExpensePayload) {
      closeRepairPrompt();
      setRepairPending(false);
      return;
    }

    const { payload, keepOpen } = savedExpensePayload;
    try {
      await addExpenseMutation.mutateAsync(payload);
      setStoredLastExpenseCategory(payload.category);
      closeRepairPrompt();
      if (keepOpen === true) {
        setAddTitle("");
        setAddAmount("");
        setAddDescription("");
        setAddSubcategoryId("");
        setAddProjectId("");
        setAddProjectSubcategoryId("");
        setAddWalletMode("single");
        setAddWalletAllocations(defaultWalletId ? [{ id: nextLocalId("wallet"), wallet_id: defaultWalletId, amount: "" }] : []);
        setTouchedAdd({});
        setSplitMode("none");
        setSplits([]);
        toast.success(t("expenses.addSuccess", { defaultValue: "Expense saved!" }));
      } else {
        setAddOpen(false);
        toast.success(t("expenses.addSuccess", { defaultValue: "Expense added successfully" }));
      }
    } catch (e) {
      setRepairError(
        t("expenses.replayAfterRepairFailed", {
          defaultValue: "Budget was created but the expense could not be saved. Please try adding it again.",
        })
      );
    } finally {
      setRepairPending(false);
    }
  };

  const handleDelete = async () => {
    if (isDeleting) return;
    if (!deleteTarget) return;
    try {
      const isRefund = deleteTarget?.transaction_type === "REFUND";
      await deleteExpenseMutation.mutateAsync(deleteTarget.id);
      setDeleteOpen(false);
      setDeleteTarget(null);
      toast.neutral(
        isRefund 
          ? t("expenses.refundVoided", { defaultValue: "Refund cancelled successfully" })
          : t("expenses.expenseVoided", { defaultValue: "Expense cancelled successfully" })
      );
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleRefund = async () => {
    if (refundExpenseMutation.isPending) return;
    if (!refundTarget) return;
    try {
      const amountNum = refundAmount ? parseAmountInput(refundAmount) : undefined;
      await refundExpenseMutation.mutateAsync({ 
        id: refundTarget.id, 
        destination_wallet_id: (refundWalletId && refundWalletId !== "") ? Number(refundWalletId) : undefined,
        amount: amountNum
      });
      setRefundOpen(false);
      setRefundTarget(null);
      setRefundWalletId("");
      setRefundAmount("");
      
      toast.success(t("expenses.refundSuccess", { defaultValue: "Refund issued successfully" }));
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleMarkAsAsset = async () => {
    if (!assetTarget || markExpenseAsAssetMutation.isPending) return;
    const currentValue = parseAmountInput(assetCurrentValue);
    if (!assetTitle.trim()) {
      setActionError(t("assets.titleRequired", { defaultValue: "Asset title is required" }));
      return;
    }
    if (!Number.isFinite(currentValue) || currentValue < 0) {
      setActionError(t("assets.currentValueInvalid", { defaultValue: "Current value must be zero or greater" }));
      return;
    }

    try {
      await markExpenseAsAssetMutation.mutateAsync({
        id: assetTarget.id,
        title: assetTitle.trim(),
        description: assetDescription.trim() || null,
        current_value: currentValue,
      });
      setAssetOpen(false);
      setAssetTarget(null);
      toast.success(t("assets.toastCreated", { defaultValue: "Asset created successfully" }));
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleCorrectFinancialDetails = async () => {
    if (isDeleting) return;
    if (!correctTarget) return;
    const target = correctTarget;

    try {
      await deleteExpenseMutation.mutateAsync(target.id);
      setCorrectOpen(false);
      setCorrectTarget(null);
      prefillAddFromExpense(target);
      setAddOpen(true);
      toast.neutral(t("expenses.correctStarted", {
        defaultValue: "Original expense cancelled. Review the pre-filled replacement.",
      }));
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleMarkAsRecurring = async () => {
    if (!recurringTarget || markExpenseAsRecurringMutation.isPending) return;
    if (!recurringStartDate) {
      setActionError(t("expenses.dateRequired", { defaultValue: "Date is required" }));
      return;
    }

    try {
      await markExpenseAsRecurringMutation.mutateAsync({
        id: recurringTarget.id,
        frequency: recurringFrequency,
        start_date: recurringStartDate,
        wallet_id: recurringWalletId ? Number(recurringWalletId) : null,
        cycle_behavior: recurringCycleBehavior,
      });
      setRecurringOpen(false);
      setRecurringTarget(null);
      toast.success(t("toasts.recurring.created", { defaultValue: "Recurring expense created" }));
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleSplitExpense = async () => {
    if (!splitTarget || splitExpenseMutation.isPending) return;
    const items = splitRows.map((row) => ({
      label: row.label.trim(),
      amount: parseAmountInput(row.amount),
      category: row.category || splitTarget.category,
      subcategory_id: row.subcategory_id ? Number(row.subcategory_id) : null,
    }));
    if (items.length < 2) {
      setActionError(t("expenses.splitNeedTwoRows", { defaultValue: "Add at least two split rows" }));
      return;
    }
    if (items.some((item) => !item.label || !item.category || !Number.isFinite(item.amount) || item.amount <= 0)) {
      setActionError(t("expenses.splitRowsInvalid", { defaultValue: "Each split row needs a label, category, and positive amount" }));
      return;
    }
    const splitTotal = items.reduce((sum, item) => sum + item.amount, 0);
    if (splitTotal !== Number(splitTarget.amount || 0)) {
      setActionError(
        t("expenses.split_total_mismatch", {
          defaultValue: "Split total must exactly match the expense amount",
        })
      );
      return;
    }

    try {
      await splitExpenseMutation.mutateAsync({
        id: splitTarget.id,
        items,
      });
      setSplitOpen(false);
      setSplitTarget(null);
      toast.success(t("expenses.splitSuccess", { defaultValue: "Expense split updated" }));
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const handleMergeExpense = async () => {
    if (!mergeTarget) return;
    try {
      if (mergeMode === "remove") {
        if (!mergeTarget.merge_group_id) {
          setActionError(t("expenses.merge_group_not_found", { defaultValue: "Merge group not found" }));
          return;
        }
        await removeExpenseFromMergeGroupMutation.mutateAsync({
          groupId: mergeTarget.merge_group_id,
          expenseId: mergeTarget.id,
        });
        toast.success(t("expenses.mergeRemoved", { defaultValue: "Expense removed from merge group" }));
      } else if (mergeMode === "add") {
        if (!mergeExistingGroupId) {
          setActionError(t("expenses.selectMergeGroup", { defaultValue: "Select a merge group" }));
          return;
        }
        await addExpensesToMergeGroupMutation.mutateAsync({
          groupId: Number(mergeExistingGroupId),
          payload: { expense_ids: [mergeTarget.id] },
        });
        toast.success(t("expenses.mergeAdded", { defaultValue: "Expense added to merge group" }));
      } else {
        const expenseIds = [mergeTarget.id, ...mergeSelectedExpenseIds];
        if (expenseIds.length < 2) {
          setActionError(t("expenses.merge_group_min_items", { defaultValue: "Select at least two expenses to merge" }));
          return;
        }
        if (!mergeTitle.trim()) {
          setActionError(t("expenses.mergeTitleRequired", { defaultValue: "Merge title is required" }));
          return;
        }
        await createExpenseMergeGroupMutation.mutateAsync({
          title: mergeTitle.trim(),
          description: mergeDescription.trim() || null,
          expense_ids: expenseIds,
        });
        toast.success(t("expenses.mergeCreated", { defaultValue: "Merge group created" }));
      }
      setMergeOpen(false);
      setMergeTarget(null);
    } catch (e) {
      setActionError(getActionErrorMessage(e));
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const paginationControls = (
    <div className="flex items-center justify-between">
      <p className="text-muted-foreground transition-all duration-200 text-pag font-medium">
        {t("expenses.page")} {page} / {totalPages || 1}
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page === 1 || loading || isFetching}
          onClick={goPrevPage}
          className="h-8 w-8 p-0 rounded-md"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages || loading || isFetching}
          onClick={goNextPage}
          className="h-8 w-8 p-0 rounded-md"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );

  const activeExpense = React.useMemo(() => 
    expenses.find(x => x.id === expenseMenuForId),
    [expenses, expenseMenuForId]
  );
  const isWalletLocked = activeExpense?.wallet?.is_active === false;
  const isSessionExpense = Boolean(activeExpense?.is_session);
  const hasMultipleWalletLegs = (activeExpense?.wallet_allocations?.length || 0) > 1;
  const hasMultipleSplitLegs = (activeExpense?.split_items?.length || 0) > 1;
  const isComplexLegacyExpense = isSessionExpense || hasMultipleWalletLegs || hasMultipleSplitLegs;
  const canCorrectExpenseRecord = React.useCallback((expense) => {
    if (!expense) return false;
    if (expense?.wallet?.is_active === false) return false;
    if (expense?.transaction_type !== "EXPENSE") return false;
    if (expense?.has_refund) return false;
    if (expense?.asset_id) return false;
    if (expense?.is_session) return false;
    if ((expense?.split_items?.length || 0) > 1) return false;
    if (expense?.merge_group_id) return false;
    if (expense?.date > todayISO) return false;
    return true;
  }, [todayISO]);
  const getCorrectExpenseDisabledReason = React.useCallback((expense) => {
    if (!expense) return undefined;
    if (expense?.wallet?.is_active === false) {
      return t("wallets.archived_locked", { defaultValue: "Wallet Archived" });
    }
    if (expense?.transaction_type !== "EXPENSE") {
      return t("expenses.onlyExpensesCanBeCorrected", { defaultValue: "Only expenses can be corrected with this flow." });
    }
    if (expense?.has_refund) {
      return t("expenses.has_refund_lock", { defaultValue: "This expense is locked because a refund has been issued. Delete the refund first." });
    }
    if (expense?.asset_id) {
      return t("expenses.assetCorrectionLock", { defaultValue: "Asset-linked expenses need a dedicated correction flow." });
    }
    if (expense?.is_session) {
      return t("expenses.sessionCorrectionLock", { defaultValue: "Session expenses should be corrected from session details." });
    }
    if ((expense?.split_items?.length || 0) > 1) {
      return t("expenses.splitCorrectionLock", { defaultValue: "Split expenses need a dedicated correction flow." });
    }
    if (expense?.merge_group_id) {
      return t("expenses.mergeCorrectionLock", { defaultValue: "Merged expenses should be removed from the merge before correction." });
    }
    if (expense?.date > todayISO) {
      return t("expenses.future_lock_notice", {
        defaultValue: "Time Lock: This expense is from your future. You can edit it once you reach this date locally.",
      });
    }
    return undefined;
  }, [t, todayISO]);
  const canEditExpense = !isWalletLocked && activeExpense?.transaction_type === "EXPENSE" && !activeExpense?.has_refund && activeExpense?.date <= todayISO;
  const canCorrectExpense = canCorrectExpenseRecord(activeExpense);
  const canRefundExpense = !isWalletLocked && activeExpense?.transaction_type === "EXPENSE" && !activeExpense?.is_fully_refunded && activeExpense?.date <= todayISO && !isComplexLegacyExpense && !activeExpense?.asset_id;
  const canMarkAsAsset = activeExpense?.transaction_type === "EXPENSE" && !activeExpense?.asset_id && !hasMultipleSplitLegs && !isSessionExpense && !activeExpense?.has_refund;
  const getMarkAsAssetDisabledReason = React.useCallback((expense) => {
    if (!expense) return undefined;
    if (expense?.transaction_type !== "EXPENSE") {
      return t("expenses.assetExpenseOnly", { defaultValue: "Only normal expenses can become assets." });
    }
    if (expense?.asset_id) {
      return t("expenses.alreadyAssetHint", { defaultValue: "This expense is already linked to an asset." });
    }
    if ((expense?.split_items?.length || 0) > 1) {
      return t("expenses.splitAssetLock", { defaultValue: "Split payments cannot be marked as one asset. Line-level assets need a dedicated flow." });
    }
    if (expense?.is_session) {
      return t("expenses.sessionAssetLock", { defaultValue: "Session assets need an item-level asset flow." });
    }
    if (expense?.has_refund) {
      return t("expenses.refundedAssetLock", { defaultValue: "Refunded expenses need refund-aware asset acquisition first." });
    }
    return undefined;
  }, [t]);
  const canMarkAsRecurring = Boolean(isPremium) && activeExpense?.transaction_type === "EXPENSE" && !hasMultipleSplitLegs;
  const canSplitExpense = activeExpense?.transaction_type === "EXPENSE" && !activeExpense?.has_refund && !isSessionExpense && !hasMultipleSplitLegs;
  const canMergeExpense = activeExpense?.transaction_type === "EXPENSE";
  const useBottomSheetForms = windowWidth < 1024;
  const activeSessionDraft = activeSessionDraftQuery.data;
  const activeFilterCount = [debouncedSearch.trim(), category, startDate, endDate, sort !== "newest" ? sort : ""].filter(Boolean).length;
  const visibleTotalAmount = React.useMemo(
    () => expenses.reduce((sum, item) => sum + Number(item.amount || 0), 0),
    [expenses]
  );
  const sessionCount = React.useMemo(
    () => expenses.filter((item) => item.is_session).length,
    [expenses]
  );
  const refundCount = React.useMemo(
    () => expenses.filter((item) => item.transaction_type === "REFUND").length,
    [expenses]
  );
  const addFormFooter = (
    <>
      <Button variant="outline" disabled={isAdding} onClick={() => setAddOpen(false)}>
        {t("common.cancel")}
      </Button>
      <Button
        variant="secondary"
        className="relative min-w-[140px] disabled:pointer-events-auto disabled:cursor-not-allowed"
        disabled={!canSubmitAddExpense}
        onClick={() => handleAdd(true)}
      >
        {isAdding ? (
          <span className="flex items-center justify-center">
            <span aria-label="Loading" className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-foreground/30 border-t-foreground" />
          </span>
        ) : (
          t("expenses.saveAndAddAnother", { defaultValue: "Save & Add Another" })
        )}
      </Button>
      <Button
        className="relative min-w-[96px] disabled:pointer-events-auto disabled:cursor-not-allowed"
        disabled={!canSubmitAddExpense}
        onClick={() => handleAdd(false)}
      >
        {isAdding ? (
          <>
            <span className="invisible">{t("expenses.add")}</span>
            <span className="absolute inset-0 flex items-center justify-center">
              <span
                aria-label="Loading"
                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
              />
            </span>
          </>
        ) : (
          t("expenses.add")
        )}
      </Button>
    </>
  );
  const editFormFooter = (
    <>
      <Button variant="outline" disabled={isEditing} onClick={() => setEditOpen(false)}>
        {t("common.cancel")}
      </Button>
      <Button
        className="relative min-w-24 disabled:pointer-events-auto disabled:cursor-not-allowed"
        disabled={!canSubmitEditExpense}
        onClick={handleEdit}
      >
        {isEditing ? (
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
    </>
  );
  const refundFooter = (
    <>
      <Button variant="outline" onClick={() => setRefundOpen(false)} disabled={refundExpenseMutation.isPending}>
        {t("common.cancel")}
      </Button>
      <Button
        variant="secondary"
        onClick={handleRefund}
        disabled={(() => {
          const remaining = refundTarget ? refundTarget.amount - (refundTarget.refunded_amount || 0) : 0;
          const current = parseAmountInput(refundAmount) || 0;
          const result = refundSchema.safeParse({
            amount: refundAmount,
            wallet_id: refundWalletId,
          });
          if (!result.success) return true;
          return current > remaining || refundExpenseMutation.isPending;
        })()}
      >
        {t("expenses.refund", { defaultValue: "Issue Refund" })}
      </Button>
    </>
  );
  const assetFooter = (
    <>
      <Button variant="outline" onClick={() => setAssetOpen(false)} disabled={markExpenseAsAssetMutation.isPending}>
        {t("common.cancel")}
      </Button>
      <Button onClick={handleMarkAsAsset} disabled={markExpenseAsAssetMutation.isPending}>
        {t("expenses.markAsAsset", { defaultValue: "Mark as Asset" })}
      </Button>
    </>
  );
  const recurringFooter = (
    <>
      <Button variant="outline" onClick={() => setRecurringOpen(false)} disabled={markExpenseAsRecurringMutation.isPending}>
        {t("common.cancel")}
      </Button>
      <Button onClick={handleMarkAsRecurring} disabled={markExpenseAsRecurringMutation.isPending}>
        {t("expenses.markAsRecurring", { defaultValue: "Mark as Recurring" })}
      </Button>
    </>
  );
  const splitFooter = (
    <>
      <Button variant="outline" onClick={() => setSplitOpen(false)} disabled={splitExpenseMutation.isPending}>
        {t("common.cancel")}
      </Button>
      <Button onClick={handleSplitExpense} disabled={splitExpenseMutation.isPending}>
        {t("expenses.splitExpense", { defaultValue: "Split Expense" })}
      </Button>
    </>
  );
  const mergeFooter = (
    <>
      <Button variant="outline" onClick={() => setMergeOpen(false)}>
        {t("common.cancel")}
      </Button>
      <Button
        onClick={handleMergeExpense}
        disabled={
          createExpenseMergeGroupMutation.isPending ||
          addExpensesToMergeGroupMutation.isPending ||
          removeExpenseFromMergeGroupMutation.isPending
        }
      >
        {mergeMode === "remove"
          ? t("expenses.removeFromMerge", { defaultValue: "Remove from Merge" })
          : mergeMode === "add"
            ? t("expenses.addToMerge", { defaultValue: "Add to Merge" })
            : t("expenses.createMerge", { defaultValue: "Create Merge" })}
      </Button>
    </>
  );
  const descriptionFooter = (
    <Button variant="outline" onClick={() => setDescriptionOpen(false)}>
      {t("common.close", { defaultValue: "Close" })}
    </Button>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="w-full px-page py-8 space-y-6">
        <PageHeader title={t("expenses.title")} description={t("expenses.subtitle")}>
          {activeTab === "recurring" ? (
            isPremium ? (
              <Button
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={() => recurringAddRef.current?.()}
                disabled={recurringCount >= 50}
                title={recurringCount >= 50 ? t("recurring.maxLimitReached") : undefined}
              >
                <Plus className="mr-2 h-4 w-4" /> {t("recurring.addTemplate")}
              </Button>
            ) : null
          ) : (
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
              <Button
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                onClick={openAdd}
                disabled={expenseMonthLimitReached}
                title={expenseMonthLimitReached ? t("expenses.monthLimitReached") : undefined}
              >
                <Plus className="mr-2 h-4 w-4" /> {t("expenses.quickAdd", { defaultValue: "Quick Add" })}
              </Button>
              <Button
                variant="outline"
                onClick={() => setSessionOpen(true)}
              >
                <Receipt className="mr-2 h-4 w-4" />
                {activeSessionDraft
                  ? t("expenses.resumeSessionCta", { defaultValue: "Resume Session" })
                  : t("expenses.startSession", { defaultValue: "Start Session" })}
              </Button>
            </div>
          )}
        </PageHeader>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full space-y-4 shadow-none">
          <TabsList className="grid w-full h-10 sm:h-12 grid-cols-2 rounded-xl">
            <TabsTrigger value="one-time" className="rounded-lg text-xs sm:text-sm">{t("expenses.oneTime", { defaultValue: "One-Time" })}</TabsTrigger>
            <TabsTrigger value="recurring" className="rounded-lg text-xs sm:text-sm">{t("expenses.recurringTab", { defaultValue: "Recurring" })}</TabsTrigger>
          </TabsList>

          <TabsContent value="one-time" className="space-y-6 mt-4">
            <div className="overflow-x-auto pb-1">
              <div className="flex min-w-max gap-2 rounded-2xl border border-border/70 bg-card/80 p-1 shadow-sm">
                {[
                  ["all", t("expenses.feedViewAll", { defaultValue: "All" })],
                  ["quick", t("expenses.feedViewQuick", { defaultValue: "Quick" })],
                  ["sessions", t("expenses.feedViewSessions", { defaultValue: "Sessions" })],
                  ["groups", t("expenses.feedViewGroups", { defaultValue: "Groups" })],
                  ["refunds", t("expenses.feedViewRefunds", { defaultValue: "Refunds" })],
                  ["linked", t("expenses.feedViewLinked", { defaultValue: "Linked" })],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => {
                      setFeedView(value);
                      setPage(1);
                    }}
                    className={cn(
                      "rounded-xl px-4 py-2 text-sm font-semibold transition-colors",
                      feedView === value
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <Card className="shadow-sm">
              <CardHeader>
                <CardTitle>{t("expenses.filtersTitle")}</CardTitle>
                <CardDescription>{t("expenses.filtersDesc")}</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
                <Input
                  type="date"
                  max={todayISO}
                  value={startDate}
                  onChange={(e) => {
                    setStartDate(e.target.value);
                    resetToFirstPage();
                  }}
                />
                <Input
                  type="date"
                  max={todayISO}
                  min={startDate || undefined}
                  value={endDate}
                  onChange={(e) => {
                    setEndDate(e.target.value);
                    resetToFirstPage();
                  }}
                />
                <Select
                  value={category || ALL_CATEGORIES_SELECT}
                  onValueChange={(value) => {
                    setCategory(value === ALL_CATEGORIES_SELECT ? "" : value);
                    resetToFirstPage();
                  }}
                >
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value={ALL_CATEGORIES_SELECT}>{t("expenses.allCategories")}</SelectItem>
                    {orderedCategories.map((c) => {
                      const Icon = categoryIconMap[c] || Circle;
                      return (
                        <SelectItem key={c} value={c}>
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4 text-muted-foreground" />
                            <span>{tCategory(c)}</span>
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
                <Select
                  value={sort}
                  onValueChange={(value) => {
                    setSort(value);
                    resetToFirstPage();
                  }}
                >
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="newest">{t("expenses.newest")}</SelectItem>
                    <SelectItem value="oldest">{t("expenses.oldest")}</SelectItem>
                    <SelectItem value="expensive">{t("expenses.highestAmount")}</SelectItem>
                    <SelectItem value="cheapest">{t("expenses.lowestAmount")}</SelectItem>
                  </SelectContent>
                </Select>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder={t("expenses.search")}
                    className="pl-9"
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      resetToFirstPage();
                    }}
                  />
                </div>
                <Button variant="outline" onClick={resetFilters}>
                  {t("common.reset")}
                </Button>
              </CardContent>
            </Card>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                    {t("expenses.visibleEvents", { defaultValue: "Visible events" })}
                  </p>
                  <p className="mt-2 text-2xl font-bold tracking-tight">{total}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("expenses.currentMonthCount", {
                      defaultValue: "{{count}} created this month",
                      count: currentMonthExpenseCount,
                    })}
                  </p>
                </CardContent>
              </Card>
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                    {t("expenses.visibleAmount", { defaultValue: "Visible amount" })}
                  </p>
                  <div className="mt-2">
                    <CurrencyAmount value={visibleTotalAmount} format="display" className="text-2xl font-bold tracking-tight" />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("expenses.refundCount", {
                      defaultValue: "{{count}} refunds in this view",
                      count: refundCount,
                    })}
                  </p>
                </CardContent>
              </Card>
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                    {t("expenses.sessionCount", { defaultValue: "Session events" })}
                  </p>
                  <p className="mt-2 text-2xl font-bold tracking-tight">{sessionCount}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("expenses.sessionCountHint", {
                      defaultValue: "Grouped purchase moments in this feed",
                    })}
                  </p>
                </CardContent>
              </Card>
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                    {t("expenses.filtersApplied", { defaultValue: "Filters applied" })}
                  </p>
                  <p className="mt-2 text-2xl font-bold tracking-tight">{activeFilterCount}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {activeFilterCount > 0
                      ? t("expenses.filtersAppliedHint", { defaultValue: "This feed is narrowed down." })
                      : t("expenses.filtersIdleHint", { defaultValue: "Showing your natural event flow." })}
                  </p>
                </CardContent>
              </Card>
            </div>

            {activeSessionDraft ? (
              <Card className="overflow-hidden border border-primary/15 bg-gradient-to-br from-primary/[0.08] via-background to-background shadow-sm">
                <CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                        {t("expenses.activeSessionBadge", { defaultValue: "Active session" })}
                      </Badge>
                      <Badge variant="outline" className="rounded-full px-3 py-1">
                        {activeSessionDraft.status}
                      </Badge>
                    </div>
                    <div className="space-y-1">
                      <h3 className="text-lg font-semibold tracking-tight text-foreground">
                        {activeSessionDraft.title || t("expenses.sessionWorkspace", { defaultValue: "Session workspace" })}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {activeSessionDraft.description || t("expenses.activeSessionHint", {
                          defaultValue: "Keep building this grouped purchase flow, then finalize when the items and wallet allocations are balanced.",
                        })}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5 lg:min-w-[32rem]">
                    <div className="rounded-2xl border border-border/60 bg-background/80 p-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        {t("expenses.sessionItems", { defaultValue: "Items" })}
                      </p>
                      <p className="mt-1 text-lg font-semibold">{activeSessionDraft.items?.length || 0}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-background/80 p-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        {t("expenses.walletSplits", { defaultValue: "Wallet splits" })}
                      </p>
                      <p className="mt-1 text-lg font-semibold">{activeSessionDraft.wallet_allocations?.length || 0}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-background/80 p-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        {t("expenses.friendSplits", { defaultValue: "Friend splits" })}
                      </p>
                      <p className="mt-1 text-lg font-semibold">{activeSessionDraft.splits?.length || 0}</p>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-background/80 p-3">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        {t("expenses.sessionPaid", { defaultValue: "Paid" })}
                      </p>
                      <div className="mt-1">
                        <CurrencyAmount value={activeSessionDraft.amount_paid || 0} format="compact" className="text-lg font-semibold" />
                      </div>
                    </div>
                    <div className="rounded-2xl border border-border/60 bg-background/80 p-3 sm:col-span-3 xl:col-span-1">
                      <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        {t("expenses.readyToFinalize", { defaultValue: "Ready" })}
                      </p>
                      <p className="mt-1 text-lg font-semibold">
                        {activeSessionDraft.can_finalize
                          ? t("common.yes", { defaultValue: "Yes" })
                          : t("common.no", { defaultValue: "No" })}
                      </p>
                      {activeSessionDraft.remaining_wallet_allocation != null ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {t("expenses.remaining", { defaultValue: "Remaining" })}: {activeSessionDraft.remaining_wallet_allocation}
                        </p>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row lg:justify-end">
                    <Button variant="outline" onClick={() => setSessionOpen(true)}>
                      {t("expenses.resumeSessionCta", { defaultValue: "Resume Session" })}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : null}

            <Card className="overflow-hidden border border-border/70 bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80">
              <CardHeader className="border-b border-border/60 bg-gradient-to-br from-muted/50 via-background to-background">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div className="space-y-1">
                    <CardTitle>{t("expenses.feedTitle", { defaultValue: "Event feed" })}</CardTitle>
                    <CardDescription>
                      {t("expenses.feedDesc", {
                        defaultValue: "A chronological view of expense events, sessions, and refunds.",
                      })}
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline" className="rounded-full px-3 py-1">
                      {t("expenses.feedSignal.wallet", { defaultValue: "Wallet flow" })}
                    </Badge>
                    <Badge variant="outline" className="rounded-full px-3 py-1">
                      {t("expenses.feedSignal.category", { defaultValue: "Planning signal" })}
                    </Badge>
                    <Badge variant="outline" className="rounded-full px-3 py-1">
                      {t("expenses.feedSignal.details", { defaultValue: "Details for depth" })}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="min-h-80 px-0 py-0">
                {loading ? (
                  <div className="flex justify-center px-4 py-20">
                    <LoadingSpinner className="h-8 w-8 text-primary" />
                  </div>
                ) : feedItems.length === 0 ? (
                  <div className="px-4 py-20 sm:px-6">
                    <EmptyState
                      inline
                      description={t("expenses.noResults", { defaultValue: "No expenses found." })}
                    />
                  </div>
                ) : (
                  <div className="divide-y divide-border/50">
                    {feedItems.map((feedItem, index) => {
                      if (feedItem?.type === "MERGE_GROUP" && feedItem.merge_group) {
                        const group = feedItem.merge_group;
                        const expanded = expandedGroupIds.has(group.id);
                        const children = Array.isArray(group.items) ? group.items : [];
                        return (
                          <div
                            key={`group-${group.id}`}
                            className="bg-gradient-to-br from-sky-500/5 via-background to-background"
                            style={{ animationDelay: `${index * 24}ms` }}
                          >
                            <button
                              type="button"
                              onClick={() => {
                                setExpandedGroupIds((prev) => {
                                  const next = new Set(prev);
                                  if (next.has(group.id)) next.delete(group.id);
                                  else next.add(group.id);
                                  return next;
                                });
                              }}
                              className="group block w-full px-4 py-4 text-left transition-colors hover:bg-sky-500/5 focus-visible:bg-sky-500/5 focus-visible:outline-none sm:px-6"
                            >
                              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                                <div className="flex min-w-0 gap-3 sm:gap-4">
                                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-sky-500/20 bg-sky-500/10 text-sky-400 shadow-sm">
                                    <GitMerge className="h-5 w-5" />
                                  </div>
                                  <div className="min-w-0 space-y-2">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <TitleTooltip title={group.title}>
                                        <span className="truncate text-base font-semibold tracking-tight text-foreground">
                                          {group.title}
                                        </span>
                                      </TitleTooltip>
                                      <Badge variant="outline" className="rounded-full border-sky-500/30 bg-sky-500/5 px-2.5 py-0.5 text-[10px] uppercase tracking-wide text-sky-500">
                                        {t("expenses.mergeFolderBadge", { defaultValue: "Folder" })}
                                      </Badge>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                      <span className="rounded-full bg-muted px-2.5 py-1">
                                        {t("expenses.mergeChildCount", {
                                          defaultValue: "{{count}} expenses",
                                          count: group.child_count,
                                        })}
                                      </span>
                                      {feedItem.matched_child_count !== group.child_count ? (
                                        <span className="rounded-full bg-sky-500/10 px-2.5 py-1 text-sky-500">
                                          {t("expenses.mergeMatchedCount", {
                                            defaultValue: "{{count}} matching",
                                            count: feedItem.matched_child_count,
                                          })}
                                        </span>
                                      ) : null}
                                      <span className="rounded-full bg-muted/60 px-2.5 py-1">
                                        {group.earliest_date === group.latest_date
                                          ? _formatDisplayDateLocal(group.latest_date)
                                          : `${_formatDisplayDateLocal(group.earliest_date)} - ${_formatDisplayDateLocal(group.latest_date)}`}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center justify-between gap-3 lg:justify-end">
                                  <div className="min-w-0 lg:text-right">
                                    <CurrencyAmount
                                      value={group.total_amount}
                                      format={windowWidth < 480 ? "compact" : "display"}
                                      tooltip="compact"
                                      className="flex items-baseline gap-1 text-lg font-bold tracking-tight lg:justify-end"
                                      currencyClassName="text-muted-foreground/70"
                                    />
                                    <p className="mt-1 text-xs text-muted-foreground">
                                      {expanded
                                        ? t("expenses.collapseFolder", { defaultValue: "Collapse folder" })
                                        : t("expenses.openFolder", { defaultValue: "Open folder" })}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            </button>
                            {expanded ? (
                              <div className="space-y-2 border-t border-sky-500/10 px-4 pb-4 sm:px-6">
                                {children.map((child) => (
                                  <div
                                    key={child.id}
                                    className="grid gap-3 rounded-2xl border border-border/60 bg-background/80 px-3 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
                                  >
                                    <button
                                      type="button"
                                      className="min-w-0 text-left"
                                      onClick={() => navigate(`/expenses/${child.id}`)}
                                    >
                                      <p className="truncate text-sm font-semibold text-foreground">{child.title}</p>
                                      <p className="mt-1 text-xs text-muted-foreground">
                                        {tCategory(child.category)} · {_formatDisplayDateLocal(child.date)}
                                      </p>
                                    </button>
                                    <div className="flex items-center justify-between gap-3 sm:justify-end">
                                      <CurrencyAmount value={child.amount} format="compact" className="text-sm font-bold" />
                                      <div data-action-popover>
                                        <Button
                                          type="button"
                                          size="icon"
                                          variant="ghost"
                                          className="h-8 w-8 rounded-full text-muted-foreground/60 hover:bg-muted hover:text-foreground"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            openExpenseActions(event, child);
                                          }}
                                        >
                                          <MoreHorizontal className="h-4 w-4" />
                                        </Button>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : null}
                          </div>
                        );
                      }

                      const e = feedItem?.expense;
                      if (!e) return null;
                      const Icon = categoryIconMap[e.category] || Circle;
                      const bgClass = getCategoryBgClass(e.category);
                      const isRefundTransaction = e.transaction_type === "REFUND";
                      const walletLegCount = e.wallet_allocations?.length || 0;
                      const itemLegCount = e.split_items?.length || 0;
                      const amountFormat = windowWidth < 480 ? "compact" : "display";
                      const _planningLabel = e.subcategory_name
                        ? `${tCategory(e.category)} · ${e.subcategory_name}`
                        : tCategory(e.category);
                      const primaryPlanningLabel = e.project_subcategory_name
                        ? `${tCategory(e.category)} · ${e.project_subcategory_name}`
                        : e.subcategory_name
                          ? `${tCategory(e.category)} · ${e.subcategory_name}`
                          : tCategory(e.category);
                      const eventSignals = [
                        e.project_title
                          ? {
                              key: "project",
                              label: e.project_title,
                              tone: "bg-primary/10 text-primary",
                            }
                          : null,
                        e.merge_group_title
                          ? {
                              key: "merge",
                              label: t("expenses.mergedSignal", {
                                defaultValue: "Merged in {{title}}",
                                title: e.merge_group_title,
                              }),
                              tone: "bg-sky-500/10 text-sky-500",
                            }
                          : null,
                        walletLegCount > 1
                          ? {
                              key: "wallets",
                              label: t("expenses.walletLegCountSignal", {
                                defaultValue: "{{count}} wallets",
                                count: walletLegCount,
                              }),
                              tone: "bg-muted text-foreground/80",
                            }
                          : null,
                        itemLegCount > 1
                          ? {
                              key: "items",
                              label: t("expenses.itemLegCountSignal", {
                                defaultValue: "{{count}} items",
                                count: itemLegCount,
                              }),
                              tone: "bg-muted text-foreground/80",
                            }
                          : null,
                        e.description
                          ? {
                              key: "description",
                              label: e.description,
                              tone: "bg-muted/60 text-muted-foreground",
                            }
                          : {
                              key: "fallback",
                              label: e.is_session
                                ? t("expenses.sessionSignal", { defaultValue: "Grouped spending event" })
                                : t("expenses.openDetailsSignal", { defaultValue: "Open details for wallet, links, and history" }),
                              tone: "bg-muted/60 text-muted-foreground",
                            },
                      ].filter(Boolean).slice(0, 3);
                      const primaryTone =
                        isRefundTransaction
                          ? "text-rose-500"
                          : e.is_fully_refunded
                            ? "text-muted-foreground"
                            : "text-foreground";

                      return (
                        <button
                          key={e.id}
                          type="button"
                          onClick={() => navigate(`/expenses/${e.id}`)}
                          className={cn(
                            "group block w-full text-left transition-colors duration-200",
                            "hover:bg-muted/40 focus-visible:bg-muted/40 focus-visible:outline-none",
                            e.is_fully_refunded && "opacity-75"
                          )}
                          style={{ animationDelay: `${index * 24}ms` }}
                        >
                          <div className="grid gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                            <div className="flex min-w-0 gap-3 sm:gap-4">
                              <div
                                className={cn(
                                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-border/50 shadow-sm",
                                  bgClass
                                )}
                              >
                                <Icon className="h-5 w-5" />
                              </div>
                              <div className="min-w-0 space-y-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <TitleTooltip title={e.title}>
                                    <span className="truncate text-base font-semibold tracking-tight text-foreground">
                                      {isRefundTransaction
                                        ? (e.title === "Partial Refund"
                                          ? t("expenses.partial_refund_title")
                                          : t("expenses.refund_title"))
                                        : e.title}
                                    </span>
                                  </TitleTooltip>
                                  {e.is_session ? (
                                    <Badge variant="secondary" className="rounded-full px-2.5 py-0.5 text-[10px] uppercase tracking-wide">
                                      {t("expenses.sessionBadge", { defaultValue: "Session" })}
                                    </Badge>
                                  ) : null}
                                  {isRefundTransaction ? (
                                    <Badge variant="outline" className="rounded-full border-rose-500/20 bg-rose-500/5 px-2.5 py-0.5 text-[10px] uppercase tracking-wide text-rose-500">
                                      {t("expenses.refund_badge", { defaultValue: "Refund" })}
                                    </Badge>
                                  ) : e.is_partially_refunded ? (
                                    <Badge variant="outline" className="rounded-full border-amber-500/20 bg-amber-500/5 px-2.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-500">
                                      {t("expenses.partial_refund_badge", { defaultValue: "Partial" })}
                                    </Badge>
                                  ) : e.is_fully_refunded ? (
                                    <Badge variant="outline" className="rounded-full px-2.5 py-0.5 text-[10px] uppercase tracking-wide">
                                      {t("expenses.refunded_badge", { defaultValue: "Refunded" })}
                                    </Badge>
                                  ) : null}
                                  {e.merge_group_title ? (
                                    <Badge variant="outline" className="rounded-full border-sky-500/30 bg-sky-500/5 px-2.5 py-0.5 text-[10px] uppercase tracking-wide text-sky-500">
                                      {t("expenses.mergedBadge", { defaultValue: "Merged" })}
                                    </Badge>
                                  ) : null}
                                </div>

                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                                  <span className="font-medium text-foreground/80">{primaryPlanningLabel}</span>
                                  <span className="hidden sm:inline text-border">•</span>
                                  <span>{_formatDisplayDateLocal(e.date)}</span>
                                  {e.wallet?.name ? (
                                    <>
                                      <span className="hidden md:inline text-border">•</span>
                                      <span className="hidden md:inline">{e.wallet.name}</span>
                                    </>
                                  ) : null}
                                </div>

                                {e.merge_group_title ? (
                                  <div className="flex items-start gap-2 rounded-2xl border border-sky-500/20 bg-sky-500/5 px-3 py-2 text-sm">
                                    <GitMerge className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" />
                                    <div className="min-w-0">
                                      <p className="font-medium text-sky-400">
                                        {t("expenses.mergedIntoGroup", {
                                          defaultValue: "Merged into {{title}}",
                                          title: e.merge_group_title,
                                        })}
                                      </p>
                                      <p className="truncate text-xs text-sky-100/60">
                                        {t("expenses.mergedHint", {
                                          defaultValue: "This expense now lives inside a combined event group.",
                                        })}
                                      </p>
                                    </div>
                                  </div>
                                ) : null}

                                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                  {eventSignals.map((signal) => (
                                    <span
                                      key={signal.key}
                                      className={cn("max-w-full truncate rounded-full px-2.5 py-1", signal.tone)}
                                    >
                                      {signal.label}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center justify-between gap-3 lg:justify-end">
                              <div className="min-w-0 lg:text-right">
                                <CurrencyAmount
                                  value={e.amount}
                                  format={amountFormat}
                                  tooltip="compact"
                                  className={cn(
                                    "flex items-baseline gap-1 text-lg font-bold tracking-tight lg:justify-end",
                                    primaryTone
                                  )}
                                  prefix={isRefundTransaction ? "+" : ""}
                                  currencyClassName="text-muted-foreground/70"
                                />
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {t("common.view", { defaultValue: "View" })} {t("common.details", { defaultValue: "details" })}
                                </p>
                              </div>

                              <div data-action-popover>
                                <Button
                                  type="button"
                                  size="icon"
                                  variant="ghost"
                                  className="h-9 w-9 rounded-full text-muted-foreground/60 transition-all hover:bg-muted hover:text-foreground"
                                  onPointerDown={(ev) => ev.stopPropagation()}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    openExpenseActions(event, e);
                                  }}
                                >
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}

                {totalPages > 1 && (
                  <div className="border-t border-border/60 px-4 py-5 sm:px-6">
                    {paginationControls}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="hidden shadow-sm border-none sm:border bg-transparent sm:bg-card">
              <CardContent className="min-h-80 py-4 sm:py-6 px-0 sm:px-6">
                <div className="space-y-0 lg:hidden text-muted-foreground transition-all duration-300">
                  {loading ? (
                    <div className="flex justify-center px-4 py-20">
                      <LoadingSpinner className="h-8 w-8 text-primary" />
                    </div>
                  ) : expenses.length === 0 ? (
                    <EmptyState
                      inline
                      description={t("expenses.noResults", { defaultValue: "No expenses found." })}
                    />
                  ) : (
                    <div className="divide-y divide-border/40">
                      {expenses.map((e, index) => {
                        const Icon = categoryIconMap[e.category] || Circle;
                        const bgClass = getCategoryBgClass(e.category);

                        const isRefunded = e.transaction_type === "REFUND";

                        return (
                          <div
                            key={e.id}
                            className={cn(
                              "flex items-center justify-between py-4 transition-all duration-300 px-page gap-rowg",
                              "hover:bg-muted/50 dark:hover:bg-muted/20",
                              "active:scale-[0.99] [&:has([data-action-popover]:active)]:scale-100",
                              "animate-in fade-in slide-in-from-bottom-2 duration-500 fill-both",
                              isRefunded && "opacity-50 grayscale transition-opacity hover:opacity-70"
                            )}
                            style={{ animationDelay: `${index * 30}ms` }}
                          >
                            <div className={cn(
                              "shrink-0 rounded-full flex items-center justify-center h-exp-icon w-exp-icon",
                              bgClass
                            )}>
                              <Icon className="h-[45%] w-[45%]" />
                            </div>

                            <div className="flex-1 min-w-0 pr-4 space-y-0.5">
                              <TitleTooltip title={e.title}>
                                <div className="flex items-center gap-2 font-semibold text-exp-title text-foreground/90 leading-tight truncate">
                                  {e.title}
                                  {isRefunded && (
                                    <Badge variant="outline" className="h-4 px-1 text-[8px] font-black uppercase text-rose-500 border-rose-500/20 bg-rose-500/5">
                                      {t("expenses.refunded_badge", { defaultValue: "Refunded" })}
                                    </Badge>
                                  )}
                                </div>
                              </TitleTooltip>
                              <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
                                <p className="text-exp-detail text-muted-foreground/80 font-medium truncate capitalize">
                                  {tCategory(e.category)}
                                </p>
                                <span className="hidden sm:inline text-muted-foreground/20">•</span>
                                <p className="text-exp-detail font-normal text-muted-foreground/50">
                                  {_formatDisplayDateLocal(e.date)}
                                </p>
                              </div>
                            </div>

                            <div className="flex flex-col items-end justify-between self-stretch shrink-0 gap-2 min-w-[70px]">
                              <div data-action-popover>
                                <Button
                                  type="button"
                                  size="icon"
                                  variant="ghost"
                                  className="h-8 w-8 -mr-1 -mt-1.5 text-muted-foreground/40 hover:text-foreground transition-colors"
                                  onPointerDown={(ev) => ev.stopPropagation()}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    openExpenseActions(event, e);
                                  }}
                                >
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </div>
                              <CurrencyAmount
                                value={e.amount}
                                format={windowWidth < 550 ? "compact" : "display"}
                                tooltip="compact"
                                className={cn(
                                  "font-bold text-exp-title tabular-nums text-right leading-none",
                                  isRefunded ? "text-rose-500" : "text-foreground"
                                )}
                                prefix={isRefunded ? "+" : ""}
                                currencyClassName="text-muted-foreground/70 ml-1.5"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div className="hidden lg:block overflow-x-auto">
                  <div className="min-w-[800px] space-y-0">
                    <div className="grid grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,0.4fr)] items-center gap-x-4 border-b border-border px-page py-3 text-mobile-micro uppercase tracking-widest font-bold text-muted-foreground/50">
                      <div className="text-left">{t("expenses.titleCol")}</div>
                      <div className="text-center">{t("expenses.category")}</div>
                      <div className="text-center">{t("expenses.date")}</div>
                      <div className="text-right">{t("expenses.amountUzs")}</div>
                      <div className="text-right" />
                    </div>

                    {loading ? (
                      <div className="flex justify-center px-4 py-20">
                        <LoadingSpinner className="h-8 w-8 text-primary" />
                      </div>
                    ) : expenses.length === 0 ? (
                      <div className="py-20">
                        <EmptyState
                          inline
                          description={t("expenses.noResults", { defaultValue: "No expenses found." })}
                        />
                      </div>
                    ) : (
                      <div className="divide-y divide-border/30">
                        {expenses.map((e, index) => {
                          const isRefundTransaction = e.transaction_type === "REFUND";
                          return (
                            <div
                              key={e.id}
                              className={cn(
                                "grid grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,0.4fr)] items-center gap-x-4 px-page py-3 hover:bg-muted/50 dark:hover:bg-muted/30 transition-colors duration-200 group",
                                e.is_fully_refunded && "opacity-60 grayscale-[0.4]"
                              )}
                              style={{ animationDelay: `${index * 30}ms` }}
                            >
                              <div className="min-w-0">
                                <TitleTooltip title={e.title}>
                                  <div className="flex items-center gap-2 text-table-title font-semibold text-foreground truncate cursor-default leading-6">
                                    {isRefundTransaction 
                                      ? (e.title === "Partial Refund" ? t("expenses.partial_refund_title") : t("expenses.refund_title"))
                                      : e.title}
                                    {isRefundTransaction && (
                                      <Badge variant="outline" className="h-4 px-1 text-[8px] font-black uppercase text-rose-500 border-rose-500/20 bg-rose-500/5">
                                        {t("expenses.refund_badge", { defaultValue: "Refund" })}
                                      </Badge>
                                    )}
                                    {e.is_fully_refunded && (
                                      <Badge variant="outline" className="h-4 px-1 text-[8px] font-black uppercase text-muted-foreground border-muted-foreground/20 bg-muted-foreground/5">
                                        {t("expenses.refunded_badge", { defaultValue: "Refunded" })}
                                      </Badge>
                                    )}
                                    {e.is_partially_refunded && (
                                      <Badge variant="outline" className="h-4 px-1 text-[8px] font-black uppercase text-amber-500 border-amber-500/20 bg-amber-500/5">
                                        {t("expenses.partial_refund_badge", { defaultValue: "Partial" })}
                                      </Badge>
                                    )}
                                  </div>
                                </TitleTooltip>
                                {isRefundTransaction && e.description && (
                                  <div className="text-[10px] text-muted-foreground/70 italic truncate mt-0.5 pl-0.5">
                                    {t("expenses.refund_for", { title: e.description, defaultValue: `for "${e.description}"` })}
                                  </div>
                                )}
                              </div>

                              <div className="flex justify-center">
                                <Badge
                                  variant="secondary"
                                  className={cn(
                                    "px-2 py-0.5 rounded-full text-mobile-caption xl:text-xs font-bold capitalize bg-muted/50 border-none shrink-0",
                                    getCategoryColorClass(e.category)
                                  )}
                                >
                                  {tCategory(e.category)}
                                </Badge>
                              </div>

                              <div className="text-center text-table-detail text-muted-foreground font-medium">
                                {_formatDisplayDateLocal(e.date)}
                              </div>

                              <CurrencyAmount
                                value={e.amount}
                                format="display"
                                tooltip="compact"
                                className={cn(
                                  "flex justify-end gap-1 items-baseline text-table-amount font-bold tabular-nums",
                                  isRefundTransaction ? "text-rose-500" : (e.is_fully_refunded ? "text-muted-foreground" : "text-foreground")
                                )}
                                prefix={isRefundTransaction ? "+" : ""}
                                currencyClassName="text-muted-foreground/70 font-medium ml-0.5"
                              />

                              <div className="flex justify-end" data-action-popover>
                                <Button
                                  type="button"
                                  size="icon"
                                  variant="ghost"
                                  className="h-8 w-8 rounded-full opacity-40 group-hover:opacity-100 transition-all hover:bg-muted"
                                  onPointerDown={(ev) => ev.stopPropagation()}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    openExpenseActions(event, e);
                                  }}
                                >
                                  <MoreHorizontal className="h-4 w-4 text-muted-foreground" />
                                </Button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {totalPages > 1 && (
                  <div className="pt-6 sm:pt-8 border-t border-border/40 mt-6 sm:mt-8">
                    {paginationControls}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="recurring" className="mt-4 space-y-4">
            <NeedsConfirmationSection />
            <RecurringExpenses
              onAddClick={(fn) => { recurringAddRef.current = fn; }}
              onCountUpdate={setRecurringCount}
            />
          </TabsContent>
        </Tabs>
      </div>

      <ActionMenu
        isOpen={Boolean(expenseMenuForId && expenseMenuPosition)}
        position={expenseMenuPosition}
        onClose={() => setExpenseMenuForId(null)}
        zIndex={100}
      >
        {isWalletLocked && (
          <>
            <div className="px-3 py-2 text-[10px] font-black uppercase tracking-tighter text-rose-500 bg-rose-500/5 rounded-md mb-1 border border-rose-500/10">
              {t("wallets.archived_locked", { defaultValue: "Wallet Archived" })}
            </div>
            <ActionMenuDivider />
          </>
        )}

        {activeExpense?.has_refund && (
          <>
            <div className="px-3 py-2 text-[10px] font-black uppercase tracking-tighter text-amber-500 bg-amber-500/5 rounded-md mb-1 border border-amber-500/10">
              {t("expenses.has_refund_lock_notice", { 
                defaultValue: "Locked: Refund Issued. Delete the refund first to modify this expense." 
              })}
            </div>
            <ActionMenuDivider />
          </>
        )}
        
        {activeExpense?.date > todayISO && (
          <>
            <div className="px-3 py-2 text-[10px] font-black uppercase tracking-tighter text-blue-500 bg-blue-500/5 rounded-md mb-1 border border-blue-500/10">
              {t("expenses.future_lock_notice", { 
                defaultValue: "Time Lock: This expense is from your future. You can edit it once you reach this date locally." 
              })}
            </div>
            <ActionMenuDivider />
          </>
        )}

        <ActionMenuItem
          icon={Receipt}
          label={t("common.view", { defaultValue: "View" })}
          onClick={() => {
            if (activeExpense) navigate(`/expenses/${activeExpense.id}`);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuDivider />
        <ActionMenuItem
          icon={FileText}
          label={t("expenses.description")}
          onClick={() => {
            if (activeExpense) openDescription(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={Pencil}
          label={t("expenses.edit")}
          disabled={!canEditExpense}
          disabledReason={
            isComplexLegacyExpense
              ? t("expenses.complexEventEditLock", { defaultValue: "Use Session details for grouped or multi-wallet events." })
              : undefined
          }
          onClick={() => {
            if (activeExpense) openEdit(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={RefreshCcw}
          label={t("expenses.correctFinancialDetails", { defaultValue: "Correct financial details" })}
          disabled={!canCorrectExpense}
          disabledReason={getCorrectExpenseDisabledReason(activeExpense)}
          onClick={() => {
            if (activeExpense) openCorrect(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={Rows3}
          label={t("expenses.splitExpense", { defaultValue: "Split Expense" })}
          disabled={!canSplitExpense}
          disabledReason={
            hasMultipleSplitLegs
              ? t("expenses.splitParentLocked", { defaultValue: "Already split. Breakdown editing is not available yet." })
              : isSessionExpense
              ? t("expenses.complex_event_not_supported", { defaultValue: "Session events cannot be split with this action." })
              : undefined
          }
          onClick={() => {
            if (activeExpense) openSplit(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={Package}
          label={
            activeExpense?.asset_id
              ? t("expenses.alreadyAsset", { defaultValue: "Already Linked to Asset" })
              : t("expenses.markAsAsset", { defaultValue: "Mark as Asset" })
          }
          disabled={!canMarkAsAsset}
          disabledReason={getMarkAsAssetDisabledReason(activeExpense)}
          onClick={() => {
            if (activeExpense) openAsset(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={GitMerge}
          label={
            activeExpense?.merge_group_id
              ? t("expenses.manageMerge", { defaultValue: "Manage Merge" })
              : t("expenses.merge", { defaultValue: "Merge" })
          }
          disabled={!canMergeExpense}
          onClick={() => {
            if (activeExpense) openMerge(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={Repeat}
          label={
            !isPremium
              ? t("expenses.premiumRequired", { defaultValue: "Premium Required" })
              : t("expenses.markAsRecurring", { defaultValue: "Mark as Recurring" })
          }
          disabled={!canMarkAsRecurring}
          disabledReason={
            hasMultipleSplitLegs
              ? t("expenses.splitRecurringLock", { defaultValue: "Recurring split payments need split-aware recurrence first." })
              : !isPremium
                ? t("recurring_expenses.premium_required", { defaultValue: "Recurring expenses require premium." })
                : undefined
          }
          onClick={() => {
            if (activeExpense) openRecurring(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={Undo2}
          label={(() => {
            if (activeExpense?.is_fully_refunded) return t("expenses.fully_refunded", { defaultValue: "Fully Refunded" });
            if (activeExpense?.is_partially_refunded) return t("expenses.refund_remaining", { defaultValue: "Refund Remaining" });
            return t("expenses.refund", { defaultValue: "Issue Refund" });
          })()}
          disabled={!canRefundExpense}
          disabledReason={
            activeExpense?.asset_id
              ? t("expenses.assetLinkLock", { defaultValue: "This expense is linked to an asset. Handle the asset first." })
              : hasMultipleSplitLegs
              ? t("expenses.splitRefundLock", { defaultValue: "Split payments need line-level refund behavior first." })
              : isComplexLegacyExpense
              ? t("expenses.complexRefundLock", { defaultValue: "Refund this grouped event from its dedicated detail workflow." })
              : undefined
          }
          onClick={() => {
            setRefundTarget(activeExpense);
            setRefundWalletId(activeExpense?.wallet_id?.toString() || "");
            setRefundOpen(true);
            setExpenseMenuForId(null);
          }}
        />
        <ActionMenuItem
          icon={Trash2}
          label={t("expenses.delete")}
          variant="destructive"
          disabled={isWalletLocked || activeExpense?.has_refund}
          onClick={() => {
            if (activeExpense) openDelete(activeExpense);
            setExpenseMenuForId(null);
          }}
        />
      </ActionMenu>

      <SessionComposer
        open={sessionOpen}
        onOpenChange={setSessionOpen}
        compact={useBottomSheetForms}
        categories={orderedCategories}
        wallets={operationalWallets}
        todayISO={todayISO}
        tCategory={tCategory}
      />

      {/* Add Dialog */}
      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={addOpen}
        onOpenChange={(open) => {
          setAddOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.addDialogTitle")}
        description={t("expenses.addDialogDesc")}
        footer={addFormFooter}
        dialogClassName="sm:max-w-[520px]"
      >
        <div className={cn("max-h-[60vh] overflow-y-auto pr-1", useBottomSheetForms && "max-h-none overflow-visible pr-0")}>
            <div className="grid gap-2.5 py-2">
              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("expenses.titleCol")}</label>
                <Input value={addTitle}
                  onChange={(e) => { setAddTitle(e.target.value); setTouchedAdd(p => ({ ...p, title: true })); }}
                  onBlur={() => setTouchedAdd(p => ({ ...p, title: true }))}
                  placeholder={t("expenses.titleCol")}
                  className={cn(addErrors.title ? "border-red-500 focus-visible:border-red-500" : "")} />
                {addErrors.title && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.title}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-1.5">
                  <label className="text-xs font-semibold">{t("expenses.amountUzs")}</label>
                  <div className="relative">
                    <Input
                      type="text"
                      inputMode="numeric"
                      maxLength={15}
                      value={addAmount}
                      onChange={(e) => { setAddAmount(formatAmountInput(e.target.value)); setTouchedAdd(p => ({ ...p, amount: true })); }}
                      onBlur={() => setTouchedAdd(p => ({ ...p, amount: true }))}
                      onKeyDown={(e) => {
                        if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") {
                          e.preventDefault();
                        }
                      }}
                      className={cn("pr-12", addErrors.amount ? "border-red-500 focus-visible:border-red-500" : "")}
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground/30">UZS</span>
                    {addErrors.amount && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.amount}</p>}
                  </div>
                </div>

                <div className="grid gap-1.5">
                  <label className="text-xs font-semibold">{t("expenses.category")}</label>
                  <Select value={addCategory || undefined} onValueChange={(v) => { setAddCategory(v); setTouchedAdd(p => ({ ...p, category: true })); }}>
                    <SelectTrigger className={cn(selectTriggerClass, addErrors.category ? "border-red-500 focus-visible:border-red-500" : "")} onBlur={() => setTouchedAdd(p => ({ ...p, category: true }))}>
                      <SelectValue placeholder={t("expenses.selectCategory")} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass} position="popper" side="bottom">
                      {orderedCategories.map((c) => {
                        const Icon = categoryIconMap[c] || Circle;
                        return (
                          <SelectItem key={c} value={c}>
                            <div className="flex items-center gap-2">
                              <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                              <span>{tCategory(c)}</span>
                            </div>
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  {addErrors.category && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.category}</p>}
                </div>
              </div>

              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("expenses.date")}</label>
                <Input
                  type="date"
                  min={MIN_EXPENSE_DATE}
                  max={todayISO}
                  value={addDate}
                  onChange={(e) => { setAddDate(e.target.value); setTouchedAdd(p => ({ ...p, date: true })); }}
                  onBlur={() => setTouchedAdd(p => ({ ...p, date: true }))}
                  className={cn(addErrors.date ? "border-red-500 focus-visible:border-red-500" : "")}
                />
                {addErrors.date && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.date}</p>}
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="grid gap-1.5">
                  <label className="text-xs font-semibold">{t("expenses.subcategory", { defaultValue: "Subcategory" })}</label>
                  <Select value={addSubcategoryId || "__none__"} onValueChange={(value) => setAddSubcategoryId(value === "__none__" ? "" : value)} disabled={!addBudgetForCategory}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("expenses.subcategory", { defaultValue: "Subcategory" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                      {getSubcategoryOptionsForBudget(addBudgetForCategory).map((subcategory) => (
                        <SelectItem key={subcategory.id} value={String(subcategory.id)}>{subcategory.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-1.5">
                  <label className="text-xs font-semibold">{t("expenses.project", { defaultValue: "Project" })}</label>
                  <Select value={addProjectId || "__none__"} onValueChange={(value) => {
                    const next = value === "__none__" ? "" : value;
                    setAddProjectId(next);
                    setAddProjectSubcategoryId("");
                  }}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("expenses.project", { defaultValue: "Project" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                      {projectRows.map((project) => (
                        <SelectItem key={project.id} value={String(project.id)}>{project.title}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-1.5">
                  <label className="text-xs font-semibold">{t("projects.projectSubcategory", { defaultValue: "Project subcategory" })}</label>
                  <Select
                    value={addProjectSubcategoryId || "__none__"}
                    onValueChange={(value) => setAddProjectSubcategoryId(value === "__none__" ? "" : value)}
                    disabled={!addProjectId || !addProject?.is_isolated}
                  >
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("projects.projectSubcategory", { defaultValue: "Project subcategory" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                      {getProjectSubcategoryOptions(addProjectId, addCategory).map((subcategory) => (
                        <SelectItem key={subcategory.id} value={String(subcategory.id)}>{subcategory.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {(addOverBudgetWarning || addSubcategoryWarning) ? (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-900 dark:text-amber-100">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    <div className="min-w-0 space-y-1">
                      {addOverBudgetWarning ? (
                        <p>
                          {t("expenses.overBudgetWarning", {
                            defaultValue: "This will put {{category}} {{amount}} over its limit.",
                            category: tCategory(addOverBudgetWarning.category),
                            amount: formatUzs(addOverBudgetWarning.overage),
                          })}
                        </p>
                      ) : null}
                      {addSubcategoryWarning ? (
                        <p>
                          {t("expenses.subcategoryOverBudgetWarning", {
                            defaultValue: "This will put {{subcategory}} {{amount}} over its subcategory limit.",
                            subcategory: addSubcategoryWarning.subcategoryName,
                            amount: formatUzs(addSubcategoryWarning.overage),
                          })}
                        </p>
                      ) : null}
                      <p className="text-xs text-amber-800/80 dark:text-amber-100/80">
                        {t("expenses.overBudgetWarningSaveStillAllowed", {
                          defaultValue: "Save stays available. You can repair the plan after recording the real transaction.",
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("wallet.label", { defaultValue: "Wallet / Card" })}</label>
                <div className="grid grid-cols-2 gap-2 rounded-xl bg-muted p-1">
                  <button
                    type="button"
                    className={cn("rounded-lg px-3 py-2 text-sm font-medium", addWalletMode === "single" ? "bg-background shadow-sm" : "text-muted-foreground")}
                    onClick={() => setAddWalletMode("single")}
                  >
                    {t("expenses.singleWallet", { defaultValue: "Single wallet" })}
                  </button>
                  <button
                    type="button"
                    className={cn("rounded-lg px-3 py-2 text-sm font-medium", addWalletMode === "multi" ? "bg-background shadow-sm" : "text-muted-foreground")}
                    onClick={() => {
                      setAddWalletMode("multi");
                        setAddWalletAllocations((prev) => prev.length ? prev : [
                        { id: nextLocalId("wallet"), wallet_id: defaultWalletId, amount: "" },
                        { id: nextLocalId("wallet"), wallet_id: "", amount: "" },
                      ]);
                    }}
                  >
                    {t("expenses.multiWallet", { defaultValue: "Multi-wallet" })}
                  </button>
                </div>
                {addWalletMode === "single" ? (
                  <Select
                    value={String(addWalletId || "")}
                    onValueChange={(val) => {
                      setAddWalletId(val);
                      setTouchedAdd(p => ({ ...p, wallet_id: true }));
                    }}
                  >
                    <SelectTrigger className={cn(selectTriggerClass, addErrors.wallet_id ? "border-red-500 focus-visible:border-red-500" : "")}>
                      <SelectValue placeholder={t("wallet.placeholder", { defaultValue: "Select Wallet" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {operationalWallets.map(w => (
                        <SelectItem key={w.id} value={String(w.id)}>{w.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="space-y-2 rounded-2xl border border-border/70 bg-muted/20 p-3">
                    {addWalletAllocations.map((allocation) => (
                      <div key={allocation.id} className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_160px_auto]">
                        <Select
                          value={String(allocation.wallet_id || "")}
                          onValueChange={(val) => setAddWalletAllocations((prev) => prev.map((row) => row.id === allocation.id ? { ...row, wallet_id: val } : row))}
                        >
                          <SelectTrigger className={selectTriggerClass}>
                            <SelectValue placeholder={t("wallet.placeholder", { defaultValue: "Select Wallet" })} />
                          </SelectTrigger>
                          <SelectContent className={selectContentClass}>
                            {operationalWallets.map((w) => (
                              <SelectItem key={w.id} value={String(w.id)}>{w.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Input
                          type="text"
                          inputMode="numeric"
                          value={allocation.amount}
                          onChange={(e) => setAddWalletAllocations((prev) => prev.map((row) => row.id === allocation.id ? { ...row, amount: formatAmountInput(e.target.value) } : row))}
                          placeholder={t("expenses.amount", { defaultValue: "Amount" })}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9"
                          onClick={() => setAddWalletAllocations((prev) => prev.length <= 2 ? prev : prev.filter((row) => row.id !== allocation.id))}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full"
                      onClick={() => setAddWalletAllocations((prev) => [...prev, { id: nextLocalId("wallet"), wallet_id: "", amount: "" }])}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      {t("expenses.addWalletLeg", { defaultValue: "Add wallet leg" })}
                    </Button>
                  </div>
                )}
                {addErrors.wallet_id && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.wallet_id}</p>}
              </div>

              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">
                  {t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})
                </label>
                <Textarea
                  className={`resize-none overflow-y-auto ${addErrors.description ? "border-red-500 focus-visible:border-red-500" : ""}`}
                  value={addDescription}
                  onChange={(e) => { setAddDescription(e.target.value); setTouchedAdd(p => ({ ...p, description: true })); }}
                  onBlur={() => setTouchedAdd(p => ({ ...p, description: true }))}
                />
                {addErrors.description && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{addErrors.description}</p>}
                {actionError && <p className="text-mobile-micro leading-4 text-red-500 font-medium ml-0.5 mt-1">{actionError}</p>}
              </div>

              {/* Split Bill UI */}
              <div className="pt-2">
                {splitMode === "none" ? (
                  <Button 
                    type="button" 
                    variant="ghost" 
                    className="w-full text-muted-foreground hover:text-foreground border border-dashed"
                    onClick={() => {
                      setSplitMode("exact");
                      setSplits([{ id: nextLocalId("split-person"), contact_name: "", amount: "" }]);
                    }}
                  >
                    <Users className="w-4 h-4 mr-2" />
                    {t("expenses.splitBillBtn", { defaultValue: "Split Bill" })}
                  </Button>
                ) : (
                  <div className="space-y-4 p-4 border rounded-xl bg-muted/20">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-primary" />
                        <span className="text-sm font-semibold">{t("expenses.splitBill", { defaultValue: "Split Bill" })}</span>
                      </div>
                      <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => {
                        setSplitMode("none");
                        setSplits([]);
                      }}>
                        {t("common.cancel")}
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 p-1 bg-muted rounded-lg">
                      <button 
                        type="button"
                        className={cn("text-xs font-medium py-1.5 rounded-md transition-colors", splitMode === "equally" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground")}
                        onClick={() => {
                          setSplitMode("equally");
                        }}
                      >
                        {t("expenses.splitEqually", { defaultValue: "Equally" })}
                      </button>
                      <button 
                        type="button"
                        className={cn("text-xs font-medium py-1.5 rounded-md transition-colors", splitMode === "exact" ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground")}
                        onClick={() => setSplitMode("exact")}
                      >
                        {t("expenses.splitExact", { defaultValue: "Exact Amounts" })}
                      </button>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                            <User className="w-3 h-3 text-primary" />
                          </div>
                          <span className="font-medium">{t("expenses.you", { defaultValue: "You" })}</span>
                        </div>
                        <span className="font-bold">{formatUzs(personalSpend)}</span>
                      </div>

                      {splits.map((split, index) => (
                        <div key={split.id} className="grid gap-1">
                          <div className="flex items-center gap-2">
                            <div className="flex-1">
                              <Input 
                                placeholder={t("expenses.splitNamePlaceholder", { defaultValue: "Name" })}
                                className={cn("h-8 text-xs w-full", addErrors[`splits.${index}.contact_name`] && touchedAdd[`splits.${index}.contact_name`] ? "border-red-500 focus-visible:border-red-500" : "")} 
                                value={split.contact_name}
                                onChange={(e) => {
                                  const newSplits = [...splits];
                                  newSplits[index].contact_name = e.target.value;
                                  setSplits(newSplits);
                                }}
                                onBlur={() => setTouchedAdd(p => ({ ...p, [`splits.${index}.contact_name`]: true }))}
                              />
                            </div>
                            <div className="flex-1 relative">
                              <Input 
                                placeholder={t("expenses.amount", { defaultValue: "Amount" })}
                                className={cn("h-8 text-xs w-full pr-10", addErrors[`splits.${index}.amount`] && touchedAdd[`splits.${index}.amount`] ? "border-red-500 focus-visible:border-red-500" : "")} 
                                type="text"
                                inputMode="numeric"
                                maxLength={15}
                                disabled={splitMode === "equally"}
                                value={split.amount}
                                onChange={(e) => {
                                  if (splitMode === "equally") return;
                                  const newSplits = [...splits];
                                  newSplits[index].amount = formatAmountInput(e.target.value);
                                  setSplits(newSplits);
                                }}
                                onBlur={() => setTouchedAdd(p => ({ ...p, [`splits.${index}.amount`]: true }))}
                                onKeyDown={(e) => {
                                  if (e.key === "-" || e.key === "." || e.key.toLowerCase() === "e") {
                                    e.preventDefault();
                                  }
                                }}
                              />
                              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-bold text-muted-foreground/30">UZS</span>
                            </div>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive shrink-0" onClick={() => {
                              const newSplits = splits.filter(s => s.id !== split.id);
                              setSplits(newSplits);
                            }}>
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                          {(addErrors[`splits.${index}.contact_name`] || addErrors[`splits.${index}.amount`]) && (
                            <p className="text-[10px] text-red-500 font-medium ml-0.5">
                              {addErrors[`splits.${index}.contact_name`] || addErrors[`splits.${index}.amount`]}
                            </p>
                          )}
                        </div>
                      ))}

                      {addErrors["splits_total"] && (
                        <p className="text-mobile-micro text-red-500 font-medium ml-0.5">{addErrors["splits_total"]}</p>
                      )}

                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm" 
                        className="w-full text-xs h-8 text-muted-foreground"
                        onClick={() => {
                          const newSplits = [...splits, { id: nextLocalId("split-person"), contact_name: "", amount: "" }];
                          setSplits(newSplits);
                        }}
                      >
                        <Plus className="w-3 h-3 mr-1" /> {t("expenses.addPerson", { defaultValue: "Add Person" })}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
        </div>
      </ResponsiveExpenseFormShell>

      <Dialog open={Boolean(repairPrompt)} onOpenChange={(open) => { if (!open) closeRepairPrompt(); }}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>
              {repairPrompt?.type === "budget_required"
                ? t("expenses.createBudgetTitle", { defaultValue: "Create budget permission" })
                : t("expenses.repairBudgetTitle", { defaultValue: "Repair budget plan" })}
            </DialogTitle>
            <DialogDescription>
              {repairPrompt
                ? repairPrompt.type === "budget_required"
                  ? t("expenses.createBudgetDesc", {
                      defaultValue: "No budget exists for {{category}} in {{month}}. Create one to allow this {{amount}} expense.",
                      category: repairPrompt.categoryLabel,
                      month: formatMonthYear(`${repairPrompt.budgetYear}-${String(repairPrompt.budgetMonth).padStart(2, "0")}-01`),
                      amount: formatUzs(repairPrompt.suggestedAmount),
                    })
                  : repairPrompt.type === "subcategory"
                    ? t("expenses.repairSubcategoryDesc", {
                        defaultValue: "{{subcategory}} is {{amount}} over after this expense.",
                        subcategory: repairPrompt.subcategoryName,
                        amount: formatUzs(repairPrompt.overage),
                      })
                    : t("expenses.repairBudgetDesc", {
                        defaultValue: "{{category}} is {{amount}} over after this expense.",
                        category: repairPrompt.categoryLabel,
                        amount: formatUzs(repairPrompt.overage),
                      })
                : ""}
            </DialogDescription>
          </DialogHeader>
          {repairPrompt ? (
            <div className="space-y-4">
              <div className={cn(
                "rounded-lg border p-3 text-sm",
                repairPrompt.type === "budget_required"
                  ? "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
                  : "border-destructive/30 bg-destructive/5 text-destructive"
              )}>
                <div className="flex items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <p>
                    {repairPrompt.type === "budget_required"
                      ? t("expenses.createBudgetAlert", {
                          defaultValue: "Your expense draft is preserved. Create a {{category}} budget for {{month}} to continue, or cancel to leave the expense unposted.",
                          category: repairPrompt.categoryLabel,
                          month: formatMonthYear(`${repairPrompt.budgetYear}-${String(repairPrompt.budgetMonth).padStart(2, "0")}-01`),
                        })
                      : repairPrompt.type === "subcategory"
                        ? t("expenses.repairSubcategoryRedState", {
                            defaultValue: "{{subcategory}} can stay red, or you can move room from {{category}} now.",
                            subcategory: repairPrompt.subcategoryName,
                            category: repairPrompt.categoryLabel,
                          })
                        : t("expenses.repairBudgetRedState", {
                            defaultValue: "{{category}} can stay red, or you can repair it now.",
                            category: repairPrompt.categoryLabel,
                          })}
                  </p>
                </div>
              </div>
              {repairPrompt.type === "budget_required" ? (
                <div className="rounded-lg border border-border/60 bg-muted/15 p-3">
                  <p className="text-sm font-semibold">
                    {t("budgets.monthlyLimit", { defaultValue: "Monthly limit" })}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t("expenses.createBudgetHint", {
                      defaultValue: "Set the monthly spending limit for {{category}}. The expense amount is suggested as a starting point.",
                      category: repairPrompt.categoryLabel,
                    })}
                  </p>
                  <div className="mt-3 grid gap-1.5">
                    <label className="text-xs font-semibold">{t("expenses.amount", { defaultValue: "Amount" })}</label>
                    <Input
                      value={repairAmount}
                      inputMode="numeric"
                      onChange={(event) => setRepairAmount(formatAmountInput(event.target.value))}
                    />
                  </div>
                </div>
              ) : repairPrompt.type === "subcategory" ? (
                <div className="rounded-lg border border-border/60 bg-muted/15 p-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold">{t("budgets.reallocateSubcategory", { defaultValue: "Reallocate inside parent" })}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t("budgets.reallocateSubcategoryHint", {
                          defaultValue: "Move room from this parent buffer or a sibling subcategory. Parent budgets are not changed here.",
                        })}
                      </p>
                    </div>
                    <Badge variant="outline" className="w-fit rounded-full">
                      {t("budgets.sameParentOnly", { defaultValue: "Same parent only" })}
                    </Badge>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_160px]">
                    <div className="grid gap-1.5">
                      <label className="text-xs font-semibold">{t("budgets.reallocateFrom", { defaultValue: "From" })}</label>
                      <Select value={repairSourceSubcategoryId || undefined} onValueChange={setRepairSourceSubcategoryId}>
                        <SelectTrigger className={selectTriggerClass}>
                          <SelectValue placeholder={t("budgets.reallocateFrom", { defaultValue: "From" })} />
                        </SelectTrigger>
                        <SelectContent className={selectContentClass}>
                          <SelectItem value="buffer" disabled={repairSubcategorySources.buffer <= 0}>
                            {t("budgets.parentBuffer", { defaultValue: "Parent buffer" })} ({formatUzs(repairSubcategorySources.buffer)})
                          </SelectItem>
                          {repairSubcategorySources.siblings.map((subcategory) => (
                            <SelectItem key={subcategory.id} value={String(subcategory.id)} disabled={subcategory.available <= 0}>
                              {subcategory.name} ({formatUzs(subcategory.available)})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid gap-1.5">
                      <label className="text-xs font-semibold">{t("expenses.amount", { defaultValue: "Amount" })}</label>
                      <Input
                        value={repairAmount}
                        inputMode="numeric"
                        onChange={(event) => setRepairAmount(formatAmountInput(event.target.value))}
                      />
                    </div>
                  </div>
                  {selectedRepairSubcategorySourceAvailable < repairAmountValue && repairAmountValue > 0 ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {t("expenses.subcategoryRepairInsufficientMicroRoom", {
                        defaultValue: "Selected same-parent source has {{amount}} available. Increase the parent limit or lower the reallocation amount.",
                        amount: formatUzs(selectedRepairSubcategorySourceAvailable),
                      })}
                    </p>
                  ) : null}
                </div>
              ) : (
                <>
                  <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_160px]">
                    <div className="grid gap-1.5">
                      <label className="text-xs font-semibold">{t("budgets.sourceCategory", { defaultValue: "Source category" })}</label>
                      <Select value={repairSourceCategory || undefined} onValueChange={setRepairSourceCategory}>
                        <SelectTrigger className={selectTriggerClass}>
                          <SelectValue placeholder={t("budgets.selectSourceCategory", { defaultValue: "Select category" })} />
                        </SelectTrigger>
                        <SelectContent className={selectContentClass}>
                          {repairSourceBudgets.map((budget) => (
                            <SelectItem key={budget.id} value={budget.category}>
                              {tCategory(budget.category)} ({formatUzs(Number(budget.effective_available ?? budget.remaining ?? 0))})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid gap-1.5">
                      <label className="text-xs font-semibold">{t("expenses.amount", { defaultValue: "Amount" })}</label>
                      <Input
                        value={repairAmount}
                        inputMode="numeric"
                        onChange={(event) => setRepairAmount(formatAmountInput(event.target.value))}
                      />
                    </div>
                  </div>
                  {repairSourceBudgets.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      {t("expenses.noRepairSourceBudget", {
                        defaultValue: "No other category has spare room for direct reallocation. Increase the limit or leave this red.",
                      })}
                    </p>
                  ) : null}
                </>
              )}
              {repairPrompt.type === "subcategory" && repairSubcategorySources.buffer <= 0 && repairSubcategorySources.siblings.every((subcategory) => subcategory.available <= 0) ? (
                <p className="text-sm text-muted-foreground">
                  {t("expenses.noSubcategoryRepairSource", {
                    defaultValue: "No parent buffer or sibling room is available. Increase the parent limit or leave this red.",
                  })}
                </p>
              ) : null}
              {repairError ? <p className="text-sm font-medium text-red-500">{repairError}</p> : null}
            </div>
          ) : null}
          <DialogFooter className="gap-2 sm:gap-2">
            <Button variant="ghost" disabled={repairPending} onClick={closeRepairPrompt}>
              {repairPrompt?.type === "budget_required"
                ? t("common.cancel", { defaultValue: "Cancel" })
                : t("expenses.leaveRed", { defaultValue: "Leave red" })}
            </Button>
            {repairPrompt?.type === "budget_required" ? (
              <Button disabled={repairPending || repairAmountValue <= 0} onClick={handleRepairCreateBudget}>
                <Plus className="mr-2 h-4 w-4" />
                {t("budgets.create", { defaultValue: "Create budget" })}
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  disabled={
                    repairPending
                    || repairAmountValue <= 0
                    || (repairPrompt?.type === "subcategory"
                      ? !repairSourceSubcategoryId || selectedRepairSubcategorySourceAvailable < repairAmountValue
                      : !repairSourceCategory)
                  }
                  onClick={handleRepairReallocate}
                >
                  <ArrowRightLeft className="mr-2 h-4 w-4" />
                  {t("budgets.reallocate", { defaultValue: "Reallocate" })}
                </Button>
                <Button disabled={repairPending || repairAmountValue <= 0} onClick={handleRepairIncreaseLimit}>
                  <Plus className="mr-2 h-4 w-4" />
                  {t("budgets.increaseLimit", { defaultValue: "Increase limit" })}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={editOpen}
        onOpenChange={(open) => {
          setEditOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.editDialogTitle")}
        description={t("expenses.editDialogDesc")}
        footer={editFormFooter}
        dialogClassName="sm:max-w-[520px]"
      >
        <div className={cn("max-h-[60vh] overflow-y-auto pr-1", useBottomSheetForms && "max-h-none overflow-visible pr-0")}>
            <div className="grid gap-2.5 py-2">
              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("expenses.titleCol")}</label>
                <Input value={editTitle}
                  onChange={(e) => { setEditTitle(e.target.value); setTouchedEdit(p => ({ ...p, title: true })); }}
                  onBlur={() => setTouchedEdit(p => ({ ...p, title: true }))}
                  placeholder={t("expenses.titleCol")}
                  className={cn(editErrors.title ? "border-red-500 focus-visible:border-red-500" : "")} />
                {editErrors.title && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{editErrors.title}</p>}
              </div>

              <div className="rounded-2xl border border-border/70 bg-muted/20 p-4">
                <div className="mb-3 flex flex-col gap-3 text-muted-foreground sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex items-start gap-2">
                    <Lock className="mt-0.5 h-4 w-4 shrink-0" />
                    <p className="text-xs leading-5">
                      {t("expenses.financialFieldsLockedCopy", {
                        defaultValue: "Financial details are locked to protect wallet history, budgets, and projects. If these are wrong, cancel the original and create a corrected replacement.",
                      })}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="w-full shrink-0 sm:w-auto"
                    disabled={!canCorrectExpenseRecord(editExpense)}
                    title={getCorrectExpenseDisabledReason(editExpense)}
                    onClick={() => {
                      if (!editExpense) return;
                      setEditOpen(false);
                      openCorrect(editExpense);
                    }}
                  >
                    <RefreshCcw className="mr-2 h-4 w-4" />
                    {t("expenses.correctFinancialDetailsShort", { defaultValue: "Correct details" })}
                  </Button>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="rounded-xl border border-border/60 bg-background/40 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{t("expenses.amountUzs")}</p>
                    <p className="mt-1 text-sm font-semibold">{formatUzs(editExpense?.amount || 0)} UZS</p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-background/40 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{t("expenses.category")}</p>
                    <p className="mt-1 text-sm font-semibold">{tCategory(editCategory) || "-"}</p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-background/40 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{t("expenses.date")}</p>
                    <p className="mt-1 text-sm font-semibold">{editDate ? formatDisplayDate(editDate, i18n.language) : "-"}</p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-background/40 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{t("wallet.label", { defaultValue: "Wallet / Card" })}</p>
                    <div className="mt-1 space-y-1 text-sm font-semibold">
                      {(editExpense?.wallet_allocations || []).length > 0 ? (
                        editExpense.wallet_allocations.map((allocation) => (
                          <p key={`${allocation.wallet_id}-${allocation.amount}`}>
                            {allocation.wallet?.name || t("wallet.label", { defaultValue: "Wallet" })}: {formatUzs(allocation.amount)} UZS
                          </p>
                        ))
                      ) : (
                        <p>{editExpense?.wallet?.name || "-"}</p>
                      )}
                    </div>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-background/40 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{t("expenses.subcategory", { defaultValue: "Subcategory" })}</p>
                    <p className="mt-1 text-sm font-semibold">
                      {getSubcategoryOptionsForBudget(editBudgetForCategory).find((item) => String(item.id) === String(editSubcategoryId))?.name || t("common.none", { defaultValue: "None" })}
                    </p>
                  </div>
                  <div className="rounded-xl border border-border/60 bg-background/40 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">{t("expenses.project", { defaultValue: "Project" })}</p>
                    <p className="mt-1 text-sm font-semibold">{editProject?.title || t("common.none", { defaultValue: "None" })}</p>
                  </div>
                </div>
              </div>

              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">
                  {t("expenses.description")} ({t("common.optional", { defaultValue: "Optional" })})
                </label>
                <Textarea
                  className={`resize-none overflow-y-auto ${editErrors.description ? "border-red-500 focus-visible:border-red-500" : ""}`}
                  value={editDescription}
                  onChange={(e) => { setEditDescription(e.target.value); setTouchedEdit(p => ({ ...p, description: true })); }}
                  onBlur={() => setTouchedEdit(p => ({ ...p, description: true }))}
                />
                {editErrors.description && <p className="text-mobile-micro text-red-500 font-medium ml-0.5 mt-0.5">{editErrors.description}</p>}
                {actionError && <p className="text-mobile-micro leading-4 text-red-500 font-medium ml-0.5 mt-1">{actionError}</p>}
              </div>
            </div>
        </div>
      </ResponsiveExpenseFormShell>

      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={splitOpen}
        onOpenChange={(open) => {
          setSplitOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.splitExpense", { defaultValue: "Split Expense" })}
        description={t("expenses.splitExpenseDesc", { defaultValue: "Break this expense into category child lines that must add up exactly." })}
        footer={splitFooter}
        dialogClassName="sm:max-w-[560px]"
      >
        <div className={cn("max-h-[60vh] overflow-y-auto pr-1", useBottomSheetForms && "max-h-none overflow-visible pr-0")}>
          <div className="space-y-3 py-2">
            {splitRows.map((row, index) => {
              const rowCategory = row.category || splitTarget?.category || "";
              const rowBudget = getBudgetForCategoryAndDate(rowCategory, splitTarget?.date || todayISO);
              const rowSubcategories = getSubcategoryOptionsForBudget(rowBudget);
              return (
              <div key={row.id} className="rounded-2xl border border-border/70 bg-muted/20 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("expenses.lineItem", { defaultValue: "Line Item" })} {index + 1}
                  </p>
                  {splitRows.length > 2 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-xs text-muted-foreground"
                      onClick={() => setSplitRows((prev) => prev.filter((item) => item.id !== row.id))}
                    >
                      <X className="mr-1 h-3 w-3" />
                      {t("common.remove", { defaultValue: "Remove" })}
                    </Button>
                  ) : null}
                </div>
                <div className="grid gap-3">
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold">{t("expenses.titleCol")}</label>
                    <Input
                      placeholder={t("expenses.splitLineTitlePlaceholder", { defaultValue: "What did this part pay for?" })}
                      value={row.label}
                      onChange={(e) => setSplitRows((prev) => prev.map((item) => item.id === row.id ? { ...item, label: e.target.value } : item))}
                    />
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="grid gap-1.5">
                      <label className="text-xs font-semibold">{t("expenses.amountUzs")}</label>
                      <Input
                        type="text"
                        inputMode="numeric"
                        placeholder="0"
                        value={row.amount}
                        onChange={(e) => setSplitRows((prev) => prev.map((item) => item.id === row.id ? { ...item, amount: formatAmountInput(e.target.value) } : item))}
                      />
                    </div>
                    <div className="grid gap-1.5">
                      <label className="text-xs font-semibold">{t("expenses.category")}</label>
                      <Select
                        value={rowCategory}
                        onValueChange={(value) => setSplitRows((prev) => prev.map((item) => item.id === row.id ? { ...item, category: value, subcategory_id: "" } : item))}
                      >
                        <SelectTrigger className={selectTriggerClass}>
                          <SelectValue placeholder={t("expenses.category")} />
                        </SelectTrigger>
                        <SelectContent className={selectContentClass}>
                          {orderedCategories.map((categoryName) => (
                            <SelectItem key={categoryName} value={categoryName}>
                              {tCategory(categoryName)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid gap-1.5">
                      <label className="text-xs font-semibold">{t("expenses.subcategory", { defaultValue: "Subcategory" })}</label>
                      <Select
                        value={row.subcategory_id || "__none__"}
                        onValueChange={(value) => setSplitRows((prev) => prev.map((item) => item.id === row.id ? { ...item, subcategory_id: value === "__none__" ? "" : value } : item))}
                      >
                        <SelectTrigger className={selectTriggerClass}>
                          <SelectValue placeholder={t("common.none", { defaultValue: "None" })} />
                        </SelectTrigger>
                        <SelectContent className={selectContentClass}>
                          <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                          {rowSubcategories.map((subcategory) => (
                            <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                              {subcategory.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              </div>
              );
            })}

            <div className="flex items-center justify-between rounded-2xl border border-dashed border-border/70 bg-background/80 p-3">
              <div>
                <p className="text-sm font-semibold">{t("expenses.splitTargetTotal", { defaultValue: "Target total" })}</p>
                <CurrencyAmount value={Number(splitTarget?.amount || 0)} format="display" className="text-sm text-muted-foreground" />
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold">{t("expenses.currentSplitTotal", { defaultValue: "Current split total" })}</p>
                <CurrencyAmount value={splitRows.reduce((sum, row) => sum + (parseAmountInput(row.amount) || 0), 0)} format="display" className="text-sm text-muted-foreground" />
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setSplitRows((prev) => [...prev, { id: nextLocalId("split-row"), label: "", amount: "", category: splitTarget?.category || "", subcategory_id: "" }])}
            >
              <Plus className="mr-2 h-4 w-4" />
              {t("expenses.addSplitRow", { defaultValue: "Add Split Row" })}
            </Button>
            {actionError ? <p className="text-mobile-micro leading-4 text-red-500 font-medium ml-0.5 mt-1">{actionError}</p> : null}
          </div>
        </div>
      </ResponsiveExpenseFormShell>

      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={assetOpen}
        onOpenChange={(open) => {
          setAssetOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.markAsAsset", { defaultValue: "Mark as Asset" })}
        description={t("expenses.markAsAssetDesc", { defaultValue: "Use this for owned items you want to track after purchase." })}
        footer={assetFooter}
        dialogClassName="sm:max-w-[520px]"
      >
        <div className={cn("max-h-[60vh] overflow-y-auto pr-1", useBottomSheetForms && "max-h-none overflow-visible pr-0")}>
          <div className="grid gap-3 py-2">
            <div className="rounded-2xl border border-border/70 bg-muted/25 p-3 text-sm text-muted-foreground">
              <p className="font-medium text-foreground">{t("assets.assetGuardrailTitle", { defaultValue: "Asset means you still own or control it." })}</p>
              <p className="mt-1">
                {t("assets.assetGuardrailBody", {
                  defaultValue: "Good examples: laptop, phone, bike, appliance, work chair, equipment. Avoid normal consumables or services like meals, taxi rides, rent, and subscriptions.",
                })}
              </p>
            </div>
            <div className="grid gap-1.5">
              <label className="text-xs font-semibold">{t("assets.title", { defaultValue: "Asset Title" })}</label>
              <Input value={assetTitle} onChange={(e) => setAssetTitle(e.target.value)} />
            </div>
            <div className="grid gap-1.5">
              <label className="text-xs font-semibold">{t("assets.currentValue", { defaultValue: "Current Value" })}</label>
              <Input type="text" inputMode="numeric" value={assetCurrentValue} onChange={(e) => setAssetCurrentValue(formatAmountInput(e.target.value))} />
            </div>
            <div className="grid gap-1.5">
              <label className="text-xs font-semibold">{t("expenses.description")}</label>
              <Textarea value={assetDescription} onChange={(e) => setAssetDescription(e.target.value)} className="resize-none" />
            </div>
            {actionError ? <p className="text-mobile-micro leading-4 text-red-500 font-medium ml-0.5 mt-1">{actionError}</p> : null}
          </div>
        </div>
      </ResponsiveExpenseFormShell>

      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={mergeOpen}
        onOpenChange={(open) => {
          setMergeOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.merge", { defaultValue: "Merge Expenses" })}
        description={t("expenses.mergeDesc", { defaultValue: "Group related expense events together without changing their accounting meaning." })}
        footer={mergeFooter}
        dialogClassName="sm:max-w-[620px]"
      >
        <div className={cn("max-h-[60vh] overflow-y-auto pr-1", useBottomSheetForms && "max-h-none overflow-visible pr-0")}>
          <div className="space-y-4 py-2">
            {mergeTarget ? (
              <div className="rounded-2xl border border-border/70 bg-muted/20 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("expenses.primaryExpense", { defaultValue: "Primary expense" })}</p>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{mergeTarget.title}</p>
                    <p className="text-sm text-muted-foreground">{tCategory(mergeTarget.category)}</p>
                  </div>
                  <CurrencyAmount value={mergeTarget.amount} format="display" />
                </div>
              </div>
            ) : null}

            {mergeTarget?.merge_group_id ? (
              <div className="rounded-2xl border border-border/70 bg-muted/20 p-4">
                <p className="font-medium">{t("expenses.alreadyInMerge", { defaultValue: "This expense already belongs to a merge group." })}</p>
                <p className="mt-1 text-sm text-muted-foreground">{mergeTarget.merge_group_title}</p>
                <p className="mt-3 text-sm text-muted-foreground">{t("expenses.removeMergeHint", { defaultValue: "You can remove it from the group here. Editing the group itself can be added next." })}</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-2 rounded-xl bg-muted p-1">
                  <button
                    type="button"
                    className={cn("rounded-lg px-3 py-2 text-sm font-medium", mergeMode === "create" ? "bg-background shadow-sm" : "text-muted-foreground")}
                    onClick={() => setMergeMode("create")}
                  >
                    {t("expenses.createMerge", { defaultValue: "Create New Group" })}
                  </button>
                  <button
                    type="button"
                    className={cn("rounded-lg px-3 py-2 text-sm font-medium", mergeMode === "add" ? "bg-background shadow-sm" : "text-muted-foreground")}
                    onClick={() => setMergeMode("add")}
                  >
                    {t("expenses.addToMerge", { defaultValue: "Add to Existing" })}
                  </button>
                </div>

                {mergeMode === "create" ? (
                  <>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="grid gap-1.5 sm:col-span-2">
                        <label className="text-xs font-semibold">{t("expenses.mergeTitle", { defaultValue: "Merge title" })}</label>
                        <Input value={mergeTitle} onChange={(e) => setMergeTitle(e.target.value)} />
                      </div>
                      <div className="grid gap-1.5 sm:col-span-2">
                        <label className="text-xs font-semibold">{t("expenses.description")}</label>
                        <Textarea value={mergeDescription} onChange={(e) => setMergeDescription(e.target.value)} className="resize-none" />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("expenses.chooseRelatedExpenses", { defaultValue: "Choose related expenses" })}</p>
                      {expenses
                        .filter((item) => item.id !== mergeTarget?.id && item.transaction_type === "EXPENSE" && !item.merge_group_id)
                        .map((item) => {
                          const checked = mergeSelectedExpenseIds.includes(item.id);
                          return (
                            <label key={item.id} className="flex cursor-pointer items-center justify-between rounded-xl border border-border/60 bg-background/80 px-3 py-2">
                              <div className="min-w-0">
                                <p className="truncate text-sm font-medium">{item.title}</p>
                                <p className="text-xs text-muted-foreground">{tCategory(item.category)}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <CurrencyAmount value={item.amount} format="compact" className="text-sm font-semibold" />
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => setMergeSelectedExpenseIds((prev) => checked ? prev.filter((id) => id !== item.id) : [...prev, item.id])}
                                />
                              </div>
                            </label>
                          );
                        })}
                    </div>
                  </>
                ) : (
                  <div className="grid gap-1.5">
                    <label className="text-xs font-semibold">{t("expenses.mergeGroup", { defaultValue: "Merge group" })}</label>
                    <Select value={mergeExistingGroupId || undefined} onValueChange={setMergeExistingGroupId}>
                      <SelectTrigger className={selectTriggerClass}>
                        <SelectValue placeholder={t("expenses.selectMergeGroup", { defaultValue: "Select merge group" })} />
                      </SelectTrigger>
                      <SelectContent className={selectContentClass}>
                        {mergeGroups.map((group) => (
                          <SelectItem key={group.id} value={String(group.id)}>
                            {group.title}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </>
            )}

            {actionError ? <p className="text-mobile-micro leading-4 text-red-500 font-medium ml-0.5 mt-1">{actionError}</p> : null}
          </div>
        </div>
      </ResponsiveExpenseFormShell>

      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={recurringOpen}
        onOpenChange={(open) => {
          setRecurringOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.markAsRecurring", { defaultValue: "Mark as Recurring" })}
        description={t("expenses.markAsRecurringDesc", { defaultValue: "Create a recurring schedule seeded from this expense." })}
        footer={recurringFooter}
        dialogClassName="sm:max-w-[520px]"
      >
        <div className={cn("max-h-[60vh] overflow-y-auto pr-1", useBottomSheetForms && "max-h-none overflow-visible pr-0")}>
          <div className="grid gap-3 py-2">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("expenses.frequency", { defaultValue: "Frequency" })}</label>
                <Select value={recurringFrequency} onValueChange={setRecurringFrequency}>
                  <SelectTrigger className={selectTriggerClass}><SelectValue /></SelectTrigger>
                  <SelectContent className={selectContentClass}>
                    {["DAILY","WEEKLY","BIWEEKLY","MONTHLY","QUARTERLY","SEMI_ANNUALLY","YEARLY"].map((frequency) => (
                      <SelectItem key={frequency} value={frequency}>{frequency.replaceAll("_", " ")}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("expenses.date")}</label>
                <Input type="date" min={MIN_EXPENSE_DATE} value={recurringStartDate} onChange={(e) => setRecurringStartDate(e.target.value)} />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">
                  {t("recurring.preferredWallet")}
                </label>
                <Select
                  value={recurringWalletId || "__none"}
                  onValueChange={(value) => setRecurringWalletId(value === "__none" ? "" : value)}
                >
                  <SelectTrigger className={selectTriggerClass}><SelectValue placeholder={t("wallet.placeholder", { defaultValue: "Select Wallet" })} /></SelectTrigger>
                  <SelectContent className={selectContentClass}>
                    <SelectItem value="__none">{t("recurring.noPreferredWallet")}</SelectItem>
                    {operationalWallets.map((wallet) => (
                      <SelectItem key={wallet.id} value={String(wallet.id)}>{wallet.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("recurring.cycleBehavior", { defaultValue: "Cycle Behavior" })}</label>
                <Select value={recurringCycleBehavior} onValueChange={setRecurringCycleBehavior}>
                  <SelectTrigger className={selectTriggerClass}><SelectValue /></SelectTrigger>
                  <SelectContent className={selectContentClass}>
                    <SelectItem value="FIXED">{t("recurring.fixed", { defaultValue: "Fixed" })}</SelectItem>
                    <SelectItem value="FLEXIBLE">{t("recurring.flexible", { defaultValue: "Flexible" })}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {actionError ? <p className="text-mobile-micro leading-4 text-red-500 font-medium ml-0.5 mt-1">{actionError}</p> : null}
          </div>
        </div>
      </ResponsiveExpenseFormShell>

      {/* Correct Financial Details Dialog */}
      <ConfirmDialog
        open={correctOpen}
        onOpenChange={(open) => {
          setCorrectOpen(open);
          if (!open) setActionError("");
        }}
        title={t("expenses.correctFinancialDetailsTitle", { defaultValue: "Correct financial details?" })}
        description={t("expenses.correctFinancialDetailsDesc", {
          defaultValue: "This will cancel \"{{title}}\" and open Quick Add with the same details pre-filled. You can then fix the amount, wallet, date, category, or project without rewriting everything.",
          title: correctTarget?.title,
        })}
        onConfirm={handleCorrectFinancialDetails}
        confirmText={t("expenses.correctFinancialDetailsConfirm", { defaultValue: "Cancel & pre-fill new" })}
        cancelText={t("common.cancel")}
        isConfirming={isDeleting}
        confirmDisabled={!canCorrectExpenseRecord(correctTarget)}
        error={actionError}
      >
        <div className="mt-4 rounded-2xl border border-border/70 bg-muted/20 p-3 text-sm text-muted-foreground">
          {t("expenses.correctFinancialDetailsAuditCopy", {
            defaultValue: "The original stays in audit history as cancelled. Reports and wallet balances will use the corrected replacement once you save it.",
          })}
        </div>
        {!canCorrectExpenseRecord(correctTarget) && (
          <p className="mt-3 text-sm font-semibold text-red-500">
            {getCorrectExpenseDisabledReason(correctTarget)}
          </p>
        )}
      </ConfirmDialog>

      {/* Delete Dialog */}
      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={(open) => {
          setDeleteOpen(open);
          if (!open) setActionError("");
        }}
        title={
          deleteTarget?.transaction_type === "REFUND"
            ? t("expenses.voidRefundTitle", { defaultValue: "Cancel refund" })
            : t("expenses.voidDialogTitle", { defaultValue: "Cancel expense" })
        }
        description={
          deleteTarget?.transaction_type === "REFUND"
            ? t("expenses.voidRefundDesc", { 
                defaultValue: "This will reverse \"{{title}}\" and keep an audit record.",
                title: deleteTarget?.title 
              })
            : (deleteTarget?.split_items?.length || 0) > 1
              ? t("expenses.voidSplitParentDesc", {
                  defaultValue: "This will reverse the entire payment \"{{title}}\", restore its wallet effect, remove its split breakdown, and keep an audit record.",
                  title: deleteTarget?.title,
                })
            : t("expenses.voidDialogDesc", { 
                defaultValue: "This will reverse \"{{title}}\", restore the wallet effect, and keep an audit record.",
                title: deleteTarget?.title 
              })
        }
        onConfirm={handleDelete}
        confirmText={t("expenses.voidConfirm", { defaultValue: "Cancel expense" })}
        cancelText={t("common.cancel")}
        isConfirming={isDeleting}
        confirmDisabled={Boolean(deleteTarget?.has_refund)}
        error={actionError}
      >
        {deleteTarget?.has_refund && (
          <p className="text-sm text-red-500 font-bold mt-4 animate-pulse">
            {t("expenses.has_refund_lock")}
          </p>
        )}
      </ConfirmDialog>

      {/* Refund Dialog */}
      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={refundOpen}
        onOpenChange={(open) => {
          setRefundOpen(open);
          if (!open) {
            setActionError("");
            setRefundAmount("");
          } else if (refundTarget) {
            const remaining = Math.max(0, refundTarget.amount - (refundTarget.refunded_amount || 0));
            setRefundAmount(formatAmountInput(String(remaining)));
            setRefundWalletId(String(refundTarget.wallet_id || ""));
          }
        }}
        title={t("expenses.refundDialogTitle", { defaultValue: "Issue Refund?" })}
        description={
          refundTarget
            ? t("expenses.refundDialogDesc_v2", {
                defaultValue: "This will reverse \"{{title}}\" and return the amount to your chosen wallet.",
                title: refundTarget.title
              })
            : t("expenses.refundDialogDesc", {
                defaultValue: "This will reverse the transaction and return the amount to your wallet."
              })
        }
        footer={refundFooter}
        dialogClassName="sm:max-w-[520px]"
      >
        <div className="grid gap-5 py-4">
          {refundTarget && (
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <div className="grid gap-1">
                  <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">
                    {t("expenses.refundAmount", { defaultValue: "Refund Amount" })}
                  </label>
                  <div className="relative">
                    <Input
                      value={refundAmount}
                      onChange={(e) => setRefundAmount(formatAmountInput(e.target.value))}
                      className={cn(
                        "h-10 text-lg font-mono font-bold pr-12 bg-muted/30 transition-colors",
                        (() => {
                          const remaining = refundTarget ? refundTarget.amount - (refundTarget.refunded_amount || 0) : 0;
                          const current = parseAmountInput(refundAmount) || 0;
                          return (current > remaining || (refundAmount !== "" && current <= 0)) ? "border-red-500 focus-visible:ring-red-500" : "border-amber-500/20";
                        })()
                      )}
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-muted-foreground/40">UZS</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">{t("expenses.remaining", { defaultValue: "Remaining" })}</p>
                  <p className="text-xs font-mono font-bold">
                    <CurrencyAmount value={Math.max(0, refundTarget.amount - (refundTarget.refunded_amount || 0))} format="display" />
                  </p>
                </div>
              </div>

              <div className="px-1 py-2">
                <Slider
                  value={[parseAmountInput(refundAmount) || 0]}
                  max={refundTarget.amount - (refundTarget.refunded_amount || 0)}
                  step={1}
                  onValueChange={(vals) => setRefundAmount(formatAmountInput(String(vals[0])))}
                  className="py-4"
                />
                <div className="flex justify-between mt-1">
                  <span className="text-[9px] font-bold text-muted-foreground uppercase">0%</span>
                  <span className="text-[9px] font-bold text-muted-foreground uppercase">100%</span>
                </div>
              </div>
            </div>
          )}

          <div className="grid gap-1.5 pt-2">
            <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">{t("expenses.depositInto", { defaultValue: "Deposit into:" })}</label>
            <Select value={refundWalletId} onValueChange={setRefundWalletId}>
              <SelectTrigger className="w-full h-11 bg-muted/30 border-amber-500/20">
                <SelectValue placeholder={t("expenses.selectWallet", { defaultValue: "Select wallet" })} />
              </SelectTrigger>
              <SelectContent>
                {operationalWallets.map((w) => {
                  const WalletTypeIcon = (() => {
                    switch (w.wallet_type) {
                      case "CASH": return Coins;
                      case "CREDIT": return Landmark;
                      case "PRELOADED": return WalletIcon;
                      default: return CreditCard;
                    }
                  })();
                  return (
                    <SelectItem key={w.id} value={w.id.toString()}>
                      <div className="flex items-center gap-2 text-left">
                        <div className="p-1.5 rounded-md bg-muted/50">
                          <WalletTypeIcon className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                        <span className="font-medium text-xs">{w.name}</span>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>
          {actionError && <p className="text-sm font-medium text-red-500">{actionError}</p>}
        </div>
      </ResponsiveExpenseFormShell>

      {/* Description Modal */}
      <ResponsiveExpenseFormShell
        compact={useBottomSheetForms}
        open={descriptionOpen}
        onOpenChange={setDescriptionOpen}
        title={t("expenses.description")}
        description={descriptionTarget?.title || t("expenses.titleCol")}
        footer={descriptionFooter}
        dialogClassName="sm:max-w-[560px]"
      >
          <div className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-border bg-muted/30 p-3 text-sm text-foreground">
            {descriptionTarget?.description || "___"}
          </div>
      </ResponsiveExpenseFormShell>
    </div>
  );
}
