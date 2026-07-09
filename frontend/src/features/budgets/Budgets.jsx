import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Trash2, Circle, Plus, BriefcaseBusiness, MoreHorizontal, Eye, Pencil, ReceiptText, ListTree, ChartColumn, FolderKanban, Layers3, ExternalLink, GitMerge, ArrowRightLeft, AlertTriangle, Shield, Check, ChevronsUpDown, CalendarClock, Archive, ArchiveRestore, Unlink, ShieldX, PauseCircle, PlayCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { InteractiveTooltip } from "@/components/InteractiveTooltip";
import { useBudgetCategoriesQuery } from "./hooks/useBudgetCategoriesQuery";
import { useBudgetsDataQuery } from "./hooks/useBudgetsDataQuery";
import {
  useCreateBudgetMutation,
  useDeleteBudgetMutation,
  useUpdateBudgetMutation,
  useReallocateBudgetMutation,
} from "./hooks/useBudgetMutations";
import { budgetCreateFormSchema, budgetDeleteFormSchema,  budgetUpdateFormSchema,
  MAX_BUDGET_AMOUNT,
} from "./budgetSchemas";
import { localizeApiError } from "@/lib/errorMessages";
import { EditProjectDialog } from "./components/EditProjectDialog";
import { IsolatedProjectCard } from "./components/IsolatedProjectCard";
import { categoryIconMap, CATEGORIES } from "@/lib/category";
import { formatUzs, formatCompactUzs, formatAmountInput, formatMonthYear, formatDisplayDate, getFallbackMonthsLong, getDateLocale } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { TitleTooltip } from "@/components/TitleTooltip";
import { cn } from "@/lib/utils";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  createBudgetSubcategory,
  createOverlayProject,
  createProject,
  createProjectCategoryLimit,
  createProjectSubcategory,
  completeProject,
  deleteBudgetSubcategory,
  deleteProject,
  deleteProjectCategoryLimit,
  deleteProjectSubcategory,
  getBudgetDetail,
  getExpenses,
  getBudgetSubcategories,
  getWallets,
  getProjectDeletePreview,
  getProjects,
  reopenProject,
  reallocateBudgetSubcategory,
  resumeProject,
  resolveProjectDeletion,
  stopProject,
  updateBudgetSubcategory,
  updateProjectCategoryLimit,
  updateProjectSubcategory,
} from "@/lib/api";
import { toISODateInTimeZone } from "@/lib/date";
import { useToast } from "@/lib/context/ToastContext";
import { Input } from "@/components/ui/input";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useSubcategoriesQuery } from "./hooks/useSubcategoriesQuery";
import { ConfigureSurvivalDialog } from "./components/ConfigureSurvivalDialog";
import { BudgetTimeline } from "./components/BudgetTimeline";
import { TaxonomyHub } from "./TaxonomyHub";
import { useTaxonomyQuery } from "./hooks/useTaxonomyQuery";
import {
  buildOverlayProjectPayload,
  getOverlayCategoryAllocationRows,
  parseBudgetAmountInput,
} from "./overlayProjectWizard";
import {
  buildIsolatedProjectPayload,
  getIsolatedCategoryAllocationRows,
  getIsolatedCategoryAllocationSummary,
  getIsolatedSubcategoryAllocationSummary,
} from "./isolatedProjectWizard";
import {
  PROJECT_DELETE_ACTIONS,
  buildProjectDeletionResolutionPayload,
  canSubmitCascadeVoid,
  shouldOpenProjectDeletionResolution,
} from "./projectDeletionResolution";

const EMPTY_ARRAY = [];
const PROJECT_LIFECYCLE_ACTIONS = {
  PAUSE: "PAUSE",
  RESUME: "RESUME",
  COMPLETE: "COMPLETE",
};

function getProjectStatusLabel(status, t) {
  if (status === "STOPPED") return t("projects.statusPaused", { defaultValue: "Paused" });
  if (status === "COMPLETED") return t("projects.statusCompleted", { defaultValue: "Completed" });
  if (status === "ARCHIVED") return t("projects.statusArchived", { defaultValue: "Archived" });
  return t("projects.statusActive", { defaultValue: "Active" });
}

function getPlanStatusMeta(status, t) {
  if (status === "covered_with_cushion") {
    return {
      label: t("budgets.planStatus.coveredWithCushion", { defaultValue: "Cash covered" }),
      tone: "text-emerald-600 dark:text-emerald-400",
      hint: t("budgets.planStatus.coveredWithCushionHint", {
        defaultValue: "Your monthly limits fit free money now and leave room.",
      }),
    };
  }
  if (status === "covered_no_cushion") {
    return {
      label: t("budgets.planStatus.coveredNoCushion", { defaultValue: "No cushion" }),
      tone: "text-amber-600 dark:text-amber-400",
      hint: t("budgets.planStatus.coveredNoCushionHint", {
        defaultValue: "Your monthly limits fit free money now, but leave no room.",
      }),
    };
  }
  if (status === "waiting_on_income") {
    return {
      label: t("budgets.planStatus.waitingOnIncome", { defaultValue: "Waiting on income" }),
      tone: "text-sky-600 dark:text-sky-400",
      hint: t("budgets.planStatus.waitingOnIncomeHint", {
        defaultValue: "Current cash is short, but expected earned income covers this plan.",
      }),
    };
  }
  if (status === "over_planned") {
    return {
      label: t("budgets.planStatus.overPlanned", { defaultValue: "Over-Planned" }),
      tone: "text-red-600 dark:text-red-400",
      hint: t("budgets.planStatus.overPlannedHint", {
        defaultValue: "Monthly limits exceed valid backing. Reduce limits or add expected earned income.",
      }),
    };
  }
  return {
    label: t("budgets.planStatus.unknown", { defaultValue: "Unknown status" }),
    tone: "text-muted-foreground",
    hint: t("budgets.planStatus.unknownHint", {
      defaultValue: "This budget plan status is not recognized yet.",
    }),
  };
}

function getBudgetMonthRange(budgetYear, budgetMonth) {
  const startDate = `${budgetYear}-${String(budgetMonth).padStart(2, "0")}-01`;
  const end = new Date(Number(budgetYear), Number(budgetMonth), 0);
  const endDate = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
  return { startDate, endDate };
}

function ResponsiveBudgetFormShell({
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
      <DialogContent
        className={cn(
          "max-h-[calc(100dvh-2rem)] grid-rows-[auto_minmax(0,1fr)_auto] overflow-hidden",
          dialogClassName,
        )}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="min-h-0 overflow-y-auto pr-1">
          {children}
        </div>
        <DialogFooter>{footer}</DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function BudgetDialogStat({ label, value, icon: Icon }) {
  return (
    <div className="flex min-w-0 items-start justify-between gap-3 rounded-lg border border-border/60 bg-muted/20 p-3">
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
        <div className="mt-1 min-w-0 text-base font-semibold tracking-tight text-foreground">
          {value}
        </div>
      </div>
      {Icon ? <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" /> : null}
    </div>
  );
}

function BudgetAmountRow({ label, value, prefix = "", tone = "" }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/70 px-3 py-2">
      <span className="min-w-0 truncate text-sm text-muted-foreground">{label}</span>
      <CurrencyAmount
        value={value}
        prefix={prefix}
        format="compact"
        tooltip="compact"
        className={cn("flex shrink-0 items-baseline gap-1 text-sm font-semibold", tone)}
        currencyClassName="text-muted-foreground/70"
      />
    </div>
  );
}

function getProjectType(project) {
  return project?.project_type || (project?.is_isolated ? "ISOLATED" : "OVERLAY");
}

function isIsolatedProject(project) {
  return getProjectType(project) === "ISOLATED";
}

function BudgetProjectReservationRow({ reservation, t }) {
  const reservedAmount = Number(reservation.reserved_amount || 0);
  const spent = Number(reservation.spent || 0);
  const remaining = Number(reservation.remaining || 0);
  const isOverLimit = Boolean(reservation.is_over_limit);
  const spentPercent = reservedAmount > 0 ? Math.min((spent / reservedAmount) * 100, 100) : 0;
  const statusLabel = isOverLimit
    ? t("budgets.reservationOver", { defaultValue: "Over reservation" })
    : t("budgets.reservationRemaining", { defaultValue: "Remaining" });

  return (
    <div
      className={cn(
        "space-y-3 rounded-lg border bg-background/70 p-3",
        isOverLimit ? "border-destructive/40 bg-destructive/5" : "border-border/60",
      )}
    >
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start">
        <div className="min-w-0">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold text-foreground">{reservation.project_title}</p>
            <Badge variant={isOverLimit ? "destructive" : "secondary"} className="rounded-full px-2 py-0 text-[10px]">
              {statusLabel}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("budgets.spendingPermissionReservation", { defaultValue: "Spending permission reservation" })}
          </p>
        </div>
        <CurrencyAmount
          value={Math.abs(remaining)}
          prefix={isOverLimit ? "+" : ""}
          format="compact"
          tooltip="compact"
          className={cn(
            "flex items-baseline gap-1 text-sm font-semibold sm:justify-end",
            isOverLimit ? "text-destructive" : "text-primary",
          )}
          currencyClassName="text-muted-foreground/70"
        />
      </div>
      <div className="space-y-2">
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full", isOverLimit ? "bg-destructive" : "bg-primary")}
            style={{ width: `${spentPercent}%` }}
          />
        </div>
        <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
          <span>
            {t("budgets.reserved", { defaultValue: "Reserved" })}: {formatCompactUzs(reservedAmount)}
          </span>
          <span>
            {t("budgets.actualSpent", { defaultValue: "Actual spent" })}: {formatCompactUzs(spent)}
          </span>
          <span className={cn("sm:text-right", isOverLimit ? "text-destructive" : "text-primary")}>
            {statusLabel}: {formatCompactUzs(Math.abs(remaining))}
          </span>
        </div>
      </div>
    </div>
  );
}

function BudgetExpenseFeedRow({ feedItem, t, tCategory, appLang, onOpenExpense }) {
  if (feedItem?.type === "MERGE_GROUP" && feedItem.merge_group) {
    const group = feedItem.merge_group;
    const dateLabel = group.earliest_date === group.latest_date
      ? formatDisplayDate(group.latest_date, appLang)
      : `${formatDisplayDate(group.earliest_date, appLang)} - ${formatDisplayDate(group.latest_date, appLang)}`;

    return (
      <div className="rounded-lg border border-sky-500/20 bg-sky-500/5 p-3">
        <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div className="flex min-w-0 gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-sky-500/20 bg-sky-500/10 text-sky-500">
              <GitMerge className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <p className="min-w-0 truncate text-sm font-semibold text-foreground">{group.title}</p>
                <Badge variant="outline" className="rounded-full border-sky-500/30 bg-sky-500/5 px-2 py-0 text-[10px] uppercase tracking-wide text-sky-500">
                  {t("expenses.mergeFolderBadge", { defaultValue: "Folder" })}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {t("expenses.mergeChildCount", {
                  defaultValue: "{{count}} expenses",
                  count: group.child_count,
                })}{" "}
                · {dateLabel}
              </p>
            </div>
          </div>
          <CurrencyAmount
            value={group.total_amount}
            format="compact"
            tooltip="compact"
            className="flex items-baseline gap-1 text-sm font-semibold sm:justify-end"
            currencyClassName="text-muted-foreground/70"
          />
        </div>
      </div>
    );
  }

  const expense = feedItem?.expense;
  if (!expense) return null;

  const Icon = categoryIconMap[expense.category] || Circle;
  const isRefund = expense.transaction_type === "REFUND";
  const title = isRefund
    ? (expense.title === "Partial Refund"
      ? t("expenses.partial_refund_title", { defaultValue: "Partial Refund" })
      : t("expenses.refund_title", { defaultValue: "Refund" }))
    : expense.title;

  return (
    <button
      type="button"
      onClick={() => onOpenExpense(expense.id)}
      className="block w-full rounded-lg border border-border/60 bg-background/70 p-3 text-left transition-colors hover:bg-muted/30 focus-visible:bg-muted/30 focus-visible:outline-none"
    >
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
        <div className="flex min-w-0 gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border/60 bg-muted/30 text-muted-foreground">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <p className="min-w-0 truncate text-sm font-semibold text-foreground">{title}</p>
              {expense.is_session ? (
                <Badge variant="secondary" className="rounded-full px-2 py-0 text-[10px] uppercase tracking-wide">
                  {t("expenses.sessionBadge", { defaultValue: "Session" })}
                </Badge>
              ) : null}
              {isRefund ? (
                <Badge variant="outline" className="rounded-full border-rose-500/20 bg-rose-500/5 px-2 py-0 text-[10px] uppercase tracking-wide text-rose-500">
                  {t("expenses.refund_badge", { defaultValue: "Refund" })}
                </Badge>
              ) : null}
            </div>
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {tCategory(expense.category)}
              {expense.subcategory_name ? ` · ${expense.subcategory_name}` : ""}
              {expense.project_title ? ` · ${expense.project_title}` : ""}
              {" · "}
              {formatDisplayDate(expense.date, appLang)}
            </p>
          </div>
        </div>
        <CurrencyAmount
          value={expense.amount}
          prefix={isRefund ? "+" : ""}
          format="compact"
          tooltip="compact"
          className={cn(
            "flex items-baseline gap-1 text-sm font-semibold sm:justify-end",
            isRefund && "text-rose-500",
          )}
          currencyClassName="text-muted-foreground/70"
        />
      </div>
    </button>
  );
}

function BudgetActivityRow({ item, t, appLang }) {
  const isRefund = item.transaction_type === "REFUND";
  return (
    <div className="grid gap-3 rounded-lg border border-border/60 bg-background/70 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-foreground">{item.title}</p>
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {formatDisplayDate(item.date, appLang)}
          {item.subcategory_name ? ` · ${item.subcategory_name}` : ""}
          {item.project_title ? ` · ${item.project_title}` : ""}
          {item.is_session ? ` · ${t("expenses.sessionBadge", { defaultValue: "Session" })}` : ""}
          {item.merge_group_title ? ` · ${item.merge_group_title}` : ""}
        </p>
      </div>
      <CurrencyAmount
        value={item.amount}
        prefix={isRefund ? "+" : ""}
        format="compact"
        tooltip="compact"
        className={cn("flex items-baseline gap-1 text-sm font-semibold sm:justify-end", isRefund && "text-rose-500")}
        currencyClassName="text-muted-foreground/70"
      />
    </div>
  );
}

export default function Budgets() {
  const [showSurvivalDialog, setShowSurvivalDialog] = React.useState(false);
  const [showCashBackingDetails, setShowCashBackingDetails] = React.useState(false);
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const todayIso = toISODateInTimeZone();
  const [currentYear, currentMonth] = todayIso.split("-").map(Number);
  const [actionError, setActionError] = React.useState("");
  const [viewMode, setViewMode] = React.useState("monthly_plan");
  const [windowWidth, setWindowWidth] = React.useState(typeof window !== "undefined" ? window.innerWidth : 1280);

  React.useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const [addOpen, setAddOpen] = React.useState(false);
  const [projectOpen, setProjectOpen] = React.useState(false);
  const [projectStructureOpen, setProjectStructureOpen] = React.useState(false);
  const [subcategoriesOpen, setSubcategoriesOpen] = React.useState(false);
  const [updateOpen, setUpdateOpen] = React.useState(false);
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [viewExpensesOpen, setViewExpensesOpen] = React.useState(false);
  const [viewDetailsOpen, setViewDetailsOpen] = React.useState(false);
  const [parentReallocateOpen, setParentReallocateOpen] = React.useState(false);
  const [parentReallocateSourceBudget, setParentReallocateSourceBudget] = React.useState(null);
  const [parentReallocateTargetCategory, setParentReallocateTargetCategory] = React.useState("");
  const [parentReallocateAmount, setParentReallocateAmount] = React.useState("");
  const [searchParams, setSearchParams] = useSearchParams();

  const showHistory = searchParams.get("history") === "true";
  const filterCategory = searchParams.get("category") || "all";
  const filterStatus = searchParams.get("status") || "all";
  const filterMonth = searchParams.get("month") || "all";
  const sortBy = searchParams.get("sort") || "newest";

  const updateSearchParam = (key, value, defaultValue = "all") => {
    setSearchParams(prev => {
      if (value === defaultValue || !value) {
        prev.delete(key);
      } else {
        prev.set(key, value);
      }
      return prev;
    }, { replace: true });
  };

  const setShowHistory = (updater) => {
    setSearchParams(prev => {
      const current = prev.get("history") === "true";
      const next = typeof updater === "function" ? updater(current) : updater;
      if (next) {
        prev.set("history", "true");
      } else {
        prev.delete("history");
        prev.delete("month");
      }
      return prev;
    }, { replace: true });
  };

  const setFilterCategory = (val) => updateSearchParam("category", val);
  const setFilterStatus = (val) => updateSearchParam("status", val);
  const setFilterMonth = (val) => updateSearchParam("month", val);
  const setSortBy = (val) => updateSearchParam("sort", val, "newest");

  const [selectedBudget, setSelectedBudget] = React.useState(null);
  const [expensesTargetBudget, setExpensesTargetBudget] = React.useState(null);
  const [detailsTargetBudget, setDetailsTargetBudget] = React.useState(null);
  const [newLimit, setNewLimit] = React.useState("");
  const [addCategory, setAddCategory] = React.useState("");
  const [addLimit, setAddLimit] = React.useState("");
  const [addBudgetYear, setAddBudgetYear] = React.useState(currentYear);
  const [addBudgetMonth, setAddBudgetMonth] = React.useState(currentMonth);
  const [projectTitle, setProjectTitle] = React.useState("");
  const [projectDescription, setProjectDescription] = React.useState("");
  const [projectIsIsolated, setProjectIsIsolated] = React.useState("true");
  const [projectWalletAllocations, setProjectWalletAllocations] = React.useState({});
  const [projectTargetEstimate, setProjectTargetEstimate] = React.useState("");
  const [projectStartDate, setProjectStartDate] = React.useState(
    `${currentYear}-${String(currentMonth).padStart(2, "0")}-01`
  );
  const [projectTargetEndDate, setProjectTargetEndDate] = React.useState("");
  const [projectWizardStep, setProjectWizardStep] = React.useState(1);
  const [projectSelectedCategories, setProjectSelectedCategories] = React.useState([]);
  const [projectCategoryAllocations, setProjectCategoryAllocations] = React.useState({});
  const [projectMicroCategory, setProjectMicroCategory] = React.useState("");
  const [projectMicroSubcategoryId, setProjectMicroSubcategoryId] = React.useState("");
  const [projectMicroLimit, setProjectMicroLimit] = React.useState("");
  const [projectSubcategoryReservations, setProjectSubcategoryReservations] = React.useState([]);
  const [projectIsolatedSubcategoryAllocations, setProjectIsolatedSubcategoryAllocations] = React.useState([]);
  const [returnToOverlayWizardAfterSubcategories, setReturnToOverlayWizardAfterSubcategories] = React.useState(false);
  const [projectStructureId, setProjectStructureId] = React.useState(null);
  const [projectCategoryValue, setProjectCategoryValue] = React.useState("");
  const [projectCategoryLimitValue, setProjectCategoryLimitValue] = React.useState("");
  const [editingProjectCategory, setEditingProjectCategory] = React.useState("");
  const [editingProjectCategoryLimit, setEditingProjectCategoryLimit] = React.useState("");

  const [editProjectModalProject, setEditProjectModalProject] = React.useState(null);
  const [projectDeletionTarget, setProjectDeletionTarget] = React.useState(null);
  const [projectDeletionPreview, setProjectDeletionPreview] = React.useState(null);
  const [projectDeletionOpen, setProjectDeletionOpen] = React.useState(false);
  const [projectDeletionConfirmTitle, setProjectDeletionConfirmTitle] = React.useState("");
  const [projectLifecycleTarget, setProjectLifecycleTarget] = React.useState(null);
  const [projectLifecycleAction, setProjectLifecycleAction] = React.useState(null);
  const [projectLifecycleOpen, setProjectLifecycleOpen] = React.useState(false);

  const [projectSubcategoryCategory, setProjectSubcategoryCategory] = React.useState("");
  const [projectSubcategoryUserSubcategoryId, setProjectSubcategoryUserSubcategoryId] = React.useState("");
  const [projectSubcategoryName, setProjectSubcategoryName] = React.useState("");
  const [projectSubcategoryLimit, setProjectSubcategoryLimit] = React.useState("");
  const [projectSubcategoryIsActive, setProjectSubcategoryIsActive] = React.useState("true");
  const [editingProjectSubcategoryId, setEditingProjectSubcategoryId] = React.useState(null);
  const [editingProjectSubcategoryUserSubcategoryId, setEditingProjectSubcategoryUserSubcategoryId] = React.useState("");
  const [editingProjectSubcategoryName, setEditingProjectSubcategoryName] = React.useState("");
  const [editingProjectSubcategoryLimit, setEditingProjectSubcategoryLimit] = React.useState("");
  const [editingProjectSubcategoryIsActive, setEditingProjectSubcategoryIsActive] = React.useState("true");
  const [subcategoryTargetBudget, setSubcategoryTargetBudget] = React.useState(null);
  const [subcategoryName, setSubcategoryName] = React.useState("");
  const [subcategoryExistingId, setSubcategoryExistingId] = React.useState(null);
  const [subcategoryComboboxOpen, setSubcategoryComboboxOpen] = React.useState(false);
  const [subcategoryLimit, setSubcategoryLimit] = React.useState("");
  const [subcategoryIsActive, setSubcategoryIsActive] = React.useState("true");
  const [editingSubcategoryId, setEditingSubcategoryId] = React.useState(null);
  const [editingSubcategoryName, setEditingSubcategoryName] = React.useState("");
  const [editingSubcategoryLimit, setEditingSubcategoryLimit] = React.useState("");
  const [editingSubcategoryIsActive, setEditingSubcategoryIsActive] = React.useState("true");
  const [reallocationTargetId, setReallocationTargetId] = React.useState("");
  const [reallocationSourceId, setReallocationSourceId] = React.useState("buffer");
  const [reallocationAmount, setReallocationAmount] = React.useState("");
  const appLang = String(i18n.resolvedLanguage || i18n.language || "en").toLowerCase();
  const categorySortLocale = appLang.startsWith("uz")
    ? "uz-UZ"
    : appLang.startsWith("ru")
      ? "ru-RU"
      : "en-US";

  const tCategory = React.useCallback((name) => t(`categories.${name}`, { defaultValue: name }), [t]);
  const compareLocalizedCategory = React.useCallback((leftCategory, rightCategory) =>
    tCategory(leftCategory).localeCompare(tCategory(rightCategory), categorySortLocale, { sensitivity: "base" }),
    [tCategory, categorySortLocale]
  );

  const summaryTarget = React.useMemo(() => {
    if (showHistory && filterMonth !== "all") {
      const [year, month] = filterMonth.split("-").map(Number);
      if (Number.isInteger(year) && Number.isInteger(month)) {
        return { year, month };
      }
    }
    return { year: currentYear, month: currentMonth };
  }, [currentMonth, currentYear, filterMonth, showHistory]);

  const { budgetsQuery, monthSummaryQuery, statsQuery } = useBudgetsDataQuery({
    budgetYear: summaryTarget.year,
    budgetMonth: summaryTarget.month,
  });
  const categoriesQuery = useBudgetCategoriesQuery();
  const globalSubcategoriesQuery = useSubcategoriesQuery(subcategoryTargetBudget?.category);
  const subcategoriesQuery = useQuery({
    queryKey: ["budgets", subcategoryTargetBudget?.id, "subcategories", "manage"],
    queryFn: () => getBudgetSubcategories(subcategoryTargetBudget?.id),
    enabled: Boolean(subcategoryTargetBudget?.id && subcategoriesOpen),
  });
  const projectsQuery = useQuery({
    queryKey: ["projects", summaryTarget.year, summaryTarget.month],
    queryFn: () => getProjects({ budgetYear: summaryTarget.year, budgetMonth: summaryTarget.month }),
    staleTime: 60_000,
  });
  const jitProjectsQuery = useQuery({
    queryKey: ["projects", "jit-overlay", currentYear, currentMonth],
    queryFn: () => getProjects({ budgetYear: currentYear, budgetMonth: currentMonth }),
    enabled: projectOpen && (summaryTarget.year !== currentYear || summaryTarget.month !== currentMonth),
    staleTime: 60_000,
  });
  const expensesTargetRange = React.useMemo(
    () =>
      expensesTargetBudget
        ? getBudgetMonthRange(expensesTargetBudget.budgetYear, expensesTargetBudget.budgetMonth)
        : null,
    [expensesTargetBudget],
  );
  const budgetExpensesQuery = useQuery({
    queryKey: [
      "budgets",
      "expense-feed",
      expensesTargetBudget?.category,
      expensesTargetBudget?.budgetYear,
      expensesTargetBudget?.budgetMonth,
    ],
    queryFn: () =>
      getExpenses({
        category: expensesTargetBudget.category,
        start_date: expensesTargetRange.startDate,
        end_date: expensesTargetRange.endDate,
        sort: "newest",
        limit: 100,
      }),
    enabled: Boolean(viewExpensesOpen && expensesTargetBudget && expensesTargetRange),
    staleTime: 15_000,
  });
  const budgetDetailsQuery = useQuery({
    queryKey: [
      "budgets",
      "detail",
      detailsTargetBudget?.budgetYear,
      detailsTargetBudget?.budgetMonth,
      detailsTargetBudget?.category,
    ],
    queryFn: () =>
      getBudgetDetail(
        detailsTargetBudget.budgetYear,
        detailsTargetBudget.budgetMonth,
        detailsTargetBudget.category,
      ),
    enabled: Boolean(viewDetailsOpen && detailsTargetBudget),
    staleTime: 15_000,
  });

  const loading = budgetsQuery.isLoading || statsQuery.isLoading || monthSummaryQuery.isLoading || categoriesQuery.isLoading;
  const error = (budgetsQuery.error || statsQuery.error || monthSummaryQuery.error || categoriesQuery.error)
    ? localizeApiError(
      budgetsQuery.error?.message || statsQuery.error?.message || monthSummaryQuery.error?.message || categoriesQuery.error?.message,
      t,
    ) || t("budgets.loadFailed")
    : "";

  const categories = categoriesQuery.data || EMPTY_ARRAY;
  const budgets = React.useMemo(() => {
    const budgetRows = budgetsQuery.data || [];
    const stats = statsQuery.data;
    const currentMonthStatusByCategory = new Map(
      (stats?.category_breakdown || []).map((item) => [
        item.category,
        {
          total: Number(item.total || 0),
          remaining: Number(item.remaining || 0),
          percentageUsed: Number(item.percentage_used || 0),
          budgetStatus: String(item.budget_status || ""),
        },
      ]),
    );

    return budgetRows.map((b) => ({
      isCurrentMonth: Number(b.budget_year) === currentYear && Number(b.budget_month) === currentMonth,
      id: b.id,
      category: b.category,
      budgetYear: Number(b.budget_year),
      budgetMonth: Number(b.budget_month),
      baseLimit: Number(b.monthly_limit || 0),
      effectiveLimit: Number(b.effective_monthly_limit || b.monthly_limit || 0),
      limit: Number(b.effective_monthly_limit || b.monthly_limit || 0),
      projectReservedAmount: Number(b.project_reserved_amount || 0),
      projectSpentAmount: Number(b.project_spent_amount || 0),
      freeGeneralLimit: Number(b.free_general_limit || 0),
      freeGeneralRemaining: Number(b.free_general_remaining || 0),
      spent: Number(b.spent || 0),
      remaining: Math.max(
        0,
        Number(b.effective_monthly_limit || b.monthly_limit || 0) - Number(b.spent || 0)
      ),
      backendStatus:
        Number(b.budget_year) === currentYear && Number(b.budget_month) === currentMonth
          ? (currentMonthStatusByCategory.get(b.category)?.budgetStatus ?? "")
          : "",
    }));
  }, [budgetsQuery.data, statsQuery.data, currentYear, currentMonth]);

  const projects = React.useMemo(
    () => (Array.isArray(projectsQuery.data) ? projectsQuery.data : []),
    [projectsQuery.data],
  );
  const jitProjects = React.useMemo(() => {
    if (summaryTarget.year === currentYear && summaryTarget.month === currentMonth) {
      return projects;
    }
    return Array.isArray(jitProjectsQuery.data) ? jitProjectsQuery.data : [];
  }, [currentMonth, currentYear, jitProjectsQuery.data, projects, summaryTarget.month, summaryTarget.year]);
  const managedSubcategories = React.useMemo(
    () => (Array.isArray(subcategoriesQuery.data) ? subcategoriesQuery.data : []),
    [subcategoriesQuery.data],
  );
  const managedSubcategoryLimitTotal = React.useMemo(
    () => managedSubcategories.reduce((sum, item) => sum + Number(item.monthly_limit || 0), 0),
    [managedSubcategories],
  );
  const managedSubcategorySpentTotal = React.useMemo(
    () => managedSubcategories.reduce((sum, item) => sum + Number(item.spent || 0), 0),
    [managedSubcategories],
  );
  const managedSubcategoryBuffer = Math.max(Number(subcategoryTargetBudget?.baseLimit || 0) - managedSubcategoryLimitTotal, 0);
  const managedUnspecifiedSpent = Math.max(Number(subcategoryTargetBudget?.spent || 0) - managedSubcategorySpentTotal, 0);
  const budgetExpenseFeedItems = React.useMemo(
    () => (Array.isArray(budgetExpensesQuery.data?.items) ? budgetExpensesQuery.data.items : []),
    [budgetExpensesQuery.data],
  );
  const budgetExpenseTotal = Number(budgetExpensesQuery.data?.total || 0);
  const budgetDetail = budgetDetailsQuery.data || null;
  const detailSubcategoryLimitTotal = React.useMemo(
    () => (budgetDetail?.subcategories || []).reduce((sum, item) => sum + Number(item.monthly_limit || 0), 0),
    [budgetDetail],
  );
  const detailSubcategorySpentTotal = React.useMemo(
    () => (budgetDetail?.subcategories || []).reduce((sum, item) => sum + Number(item.spent || 0), 0),
    [budgetDetail],
  );
  const detailSubcategoryBuffer = Math.max(Number(budgetDetail?.monthly_limit || 0) - detailSubcategoryLimitTotal, 0);
  const detailUnspecifiedSpent = Math.max(Number(budgetDetail?.spent || 0) - detailSubcategorySpentTotal, 0);
  const detailsEffects = React.useMemo(
    () => [
      {
        label: t("budgets.baseLimit", { defaultValue: "Base limit" }),
        value: budgetDetail?.monthly_limit ?? 0,
      },
      {
        label: t("budgets.capTrim", { defaultValue: "Cap trim" }),
        value: budgetDetail?.cap_trim_amount ?? 0,
      },
      {
        label: t("budgets.reallocatedIn", { defaultValue: "Reallocated in" }),
        value: budgetDetail?.reallocated_in ?? 0,
        prefix: "+",
      },
      {
        label: t("budgets.reallocatedOut", { defaultValue: "Reallocated out" }),
        value: budgetDetail?.reallocated_out ?? 0,
      },
    ],
    [budgetDetail, t],
  );
  const structureProject = React.useMemo(
    () => projects.find((project) => project.id === projectStructureId) || null,
    [projects, projectStructureId],
  );
  const structureProjectIsIsolated = structureProject ? isIsolatedProject(structureProject) : false;
  const structureProjectCategories = React.useMemo(
    () => Array.isArray(structureProject?.category_breakdown) ? structureProject.category_breakdown : [],
    [structureProject],
  );
  const selectedOverlayReservationTotalsByCategory = React.useMemo(() => {
    const totals = new Map();
    projects
      .filter((project) => !isIsolatedProject(project) && String(project.status || "").toUpperCase() === "ACTIVE")
      .forEach((project) => {
        (project.category_breakdown || []).forEach((categoryRow) => {
          if (
            Number(categoryRow.budget_year) !== Number(summaryTarget.year) ||
            Number(categoryRow.budget_month) !== Number(summaryTarget.month)
          ) {
            return;
          }
          totals.set(
            categoryRow.category,
            Number(totals.get(categoryRow.category) || 0) + Number(categoryRow.limit_amount || 0),
          );
        });
      });
    return totals;
  }, [projects, summaryTarget.month, summaryTarget.year]);
  const selectedOverlayReservationTotalsBySubcategory = React.useMemo(() => {
    const totals = new Map();
    projects
      .filter((project) => !isIsolatedProject(project) && String(project.status || "").toUpperCase() === "ACTIVE")
      .forEach((project) => {
        (project.category_breakdown || []).forEach((categoryRow) => {
          (categoryRow.subcategories || []).forEach((subcategory) => {
            if (
              Number(subcategory.budget_year) !== Number(summaryTarget.year) ||
              Number(subcategory.budget_month) !== Number(summaryTarget.month)
            ) {
              return;
            }
            const key = String(subcategory.user_subcategory_id || "");
            totals.set(key, Number(totals.get(key) || 0) + Number(subcategory.limit_amount || 0));
          });
        });
      });
    return totals;
  }, [projects, summaryTarget.month, summaryTarget.year]);
  const jitOverlayReservationTotalsByCategory = React.useMemo(() => {
    const totals = new Map();
    jitProjects
      .filter((project) => !isIsolatedProject(project) && String(project.status || "").toUpperCase() === "ACTIVE")
      .forEach((project) => {
        (project.category_breakdown || []).forEach((categoryRow) => {
          if (
            Number(categoryRow.budget_year) !== Number(currentYear) ||
            Number(categoryRow.budget_month) !== Number(currentMonth)
          ) {
            return;
          }
          totals.set(
            categoryRow.category,
            Number(totals.get(categoryRow.category) || 0) + Number(categoryRow.limit_amount || 0),
          );
        });
      });
    return totals;
  }, [currentMonth, currentYear, jitProjects]);
  const jitOverlayReservationTotalsBySubcategory = React.useMemo(() => {
    const totals = new Map();
    jitProjects
      .filter((project) => !isIsolatedProject(project) && String(project.status || "").toUpperCase() === "ACTIVE")
      .forEach((project) => {
        (project.category_breakdown || []).forEach((categoryRow) => {
          (categoryRow.subcategories || []).forEach((subcategory) => {
            if (
              Number(subcategory.budget_year) !== Number(currentYear) ||
              Number(subcategory.budget_month) !== Number(currentMonth)
            ) {
              return;
            }
            const key = String(subcategory.user_subcategory_id || "");
            totals.set(key, Number(totals.get(key) || 0) + Number(subcategory.limit_amount || 0));
          });
        });
      });
    return totals;
  }, [currentMonth, currentYear, jitProjects]);
  const getOverlayCategoryHeadroom = React.useCallback((category, excludeAmount = 0) => {
    const budget = budgets.find((item) =>
      item.category === category &&
      Number(item.budgetYear) === Number(summaryTarget.year) &&
      Number(item.budgetMonth) === Number(summaryTarget.month)
    ) || null;
    if (!budget) {
      return { budget: null, reserved: 0, headroom: 0 };
    }
    const reserved = Number(selectedOverlayReservationTotalsByCategory.get(category) ?? budget.projectReservedAmount ?? 0);
    const headroom = Math.max(Number(budget.baseLimit || 0) - reserved + Number(excludeAmount || 0), 0);
    return { budget, reserved, headroom };
  }, [budgets, selectedOverlayReservationTotalsByCategory, summaryTarget.month, summaryTarget.year]);
  const getJitOverlayCategoryHeadroom = React.useCallback((category) => {
    const budget = budgets.find((item) =>
      item.category === category &&
      Number(item.budgetYear) === Number(currentYear) &&
      Number(item.budgetMonth) === Number(currentMonth)
    ) || null;
    if (!budget) {
      return { budget: null, reserved: 0, headroom: 0 };
    }
    const reserved = Number(jitOverlayReservationTotalsByCategory.get(category) ?? budget.projectReservedAmount ?? 0);
    const headroom = Math.max(Number(budget.baseLimit || 0) - reserved, 0);
    return { budget, reserved, headroom };
  }, [budgets, currentMonth, currentYear, jitOverlayReservationTotalsByCategory]);
  const editingProjectSubcategoryRow = React.useMemo(
    () => structureProjectCategories
      .flatMap((categoryRow) => categoryRow.subcategories || [])
      .find((subcategory) => String(subcategory.id) === String(editingProjectSubcategoryId)) || null,
    [editingProjectSubcategoryId, structureProjectCategories],
  );
  const overlayProjectSubcategoryCategory = projectSubcategoryCategory || editingProjectSubcategoryRow?.category || "";
  const overlayProjectSubcategoryBudget = React.useMemo(
    () => budgets.find((budget) =>
      budget.category === overlayProjectSubcategoryCategory &&
      Number(budget.budgetYear) === Number(summaryTarget.year) &&
      Number(budget.budgetMonth) === Number(summaryTarget.month)
    ) || null,
    [budgets, overlayProjectSubcategoryCategory, summaryTarget.month, summaryTarget.year],
  );
  const projectMicroBudget = React.useMemo(
    () => budgets.find((budget) =>
      budget.category === projectMicroCategory &&
      Number(budget.budgetYear) === Number(currentYear) &&
      Number(budget.budgetMonth) === Number(currentMonth)
    ) || null,
    [budgets, currentMonth, currentYear, projectMicroCategory],
  );
  const projectMicroSubcategoriesQuery = useQuery({
    queryKey: ["budgets", projectMicroBudget?.id, "subcategories", "jit-overlay-project"],
    queryFn: () => getBudgetSubcategories(projectMicroBudget?.id),
    enabled: Boolean(projectOpen && projectIsIsolated === "false" && projectWizardStep === 4 && projectMicroBudget?.id),
  });
  const projectWalletsQuery = useQuery({
    queryKey: ["wallets"],
    queryFn: getWallets,
    enabled: Boolean(projectOpen && projectIsIsolated === "true"),
  });
  const overlayProjectSubcategoriesQuery = useQuery({
    queryKey: ["budgets", overlayProjectSubcategoryBudget?.id, "subcategories", "overlay-project"],
    queryFn: () => getBudgetSubcategories(overlayProjectSubcategoryBudget?.id),
    enabled: Boolean(
      projectStructureOpen &&
      structureProject &&
      !structureProjectIsIsolated &&
      overlayProjectSubcategoryBudget?.id
    ),
  });
  const overlayEligibleSubcategories = React.useMemo(() => {
    const assigned = new Set(
      structureProjectCategories
        .flatMap((categoryRow) => categoryRow.subcategories || [])
        .filter((subcategory) => subcategory.budget_year === summaryTarget.year && subcategory.budget_month === summaryTarget.month)
        .map((subcategory) => String(subcategory.user_subcategory_id || "")),
    );
    return (overlayProjectSubcategoriesQuery.data || []).filter((subcategory) => !assigned.has(String(subcategory.id)));
  }, [overlayProjectSubcategoriesQuery.data, structureProjectCategories, summaryTarget.month, summaryTarget.year]);
  const getOverlaySubcategoryHeadroom = React.useCallback((userSubcategoryId, excludeAmount = 0) => {
    const subcategory = (overlayProjectSubcategoriesQuery.data || []).find(
      (item) => String(item.id) === String(userSubcategoryId),
    );
    if (!subcategory) {
      return { subcategory: null, reserved: 0, headroom: 0 };
    }
    const key = String(userSubcategoryId || "");
    const reserved = Number(selectedOverlayReservationTotalsBySubcategory.get(key) || 0);
    const headroom = Math.max(Number(subcategory.monthly_limit || 0) - reserved + Number(excludeAmount || 0), 0);
    return { subcategory, reserved, headroom };
  }, [overlayProjectSubcategoriesQuery.data, selectedOverlayReservationTotalsBySubcategory]);
  const projectCategoryHeadroom = React.useMemo(
    () => (
      structureProject && !structureProjectIsIsolated && projectCategoryValue
        ? getOverlayCategoryHeadroom(projectCategoryValue)
        : null
    ),
    [getOverlayCategoryHeadroom, projectCategoryValue, structureProject, structureProjectIsIsolated],
  );
  const projectCategoryLimitAmount = parseBudgetAmountInput(projectCategoryLimitValue);
  const projectCategoryWouldOverbook = Boolean(
    projectCategoryHeadroom &&
    projectCategoryLimitAmount !== null &&
    projectCategoryLimitAmount > Number(projectCategoryHeadroom.headroom || 0)
  );
  const editingProjectCategoryRow = React.useMemo(
    () => structureProjectCategories.find((item) => item.category === editingProjectCategory) || null,
    [editingProjectCategory, structureProjectCategories],
  );
  const editingProjectCategoryHeadroom = React.useMemo(
    () => (
      structureProject && !structureProjectIsIsolated && editingProjectCategory
        ? getOverlayCategoryHeadroom(editingProjectCategory, Number(editingProjectCategoryRow?.limit_amount || 0))
        : null
    ),
    [editingProjectCategory, editingProjectCategoryRow, getOverlayCategoryHeadroom, structureProject, structureProjectIsIsolated],
  );
  const editingProjectCategoryLimitAmount = parseBudgetAmountInput(editingProjectCategoryLimit);
  const editingProjectCategoryWouldOverbook = Boolean(
    editingProjectCategoryHeadroom &&
    editingProjectCategoryLimitAmount !== null &&
    editingProjectCategoryLimitAmount > Number(editingProjectCategoryHeadroom.headroom || 0)
  );
  const projectSubcategoryHeadroom = React.useMemo(
    () => (
      structureProject && !structureProjectIsIsolated && projectSubcategoryUserSubcategoryId
        ? getOverlaySubcategoryHeadroom(projectSubcategoryUserSubcategoryId)
        : null
    ),
    [getOverlaySubcategoryHeadroom, projectSubcategoryUserSubcategoryId, structureProject, structureProjectIsIsolated],
  );
  const projectSubcategoryLimitAmount = parseBudgetAmountInput(projectSubcategoryLimit);
  const projectSubcategoryWouldOverbook = Boolean(
    projectSubcategoryHeadroom &&
    projectSubcategoryLimitAmount !== null &&
    projectSubcategoryLimitAmount > Number(projectSubcategoryHeadroom.headroom || 0)
  );
  const editingProjectSubcategoryHeadroom = React.useMemo(
    () => (
      structureProject && !structureProjectIsIsolated && editingProjectSubcategoryUserSubcategoryId
        ? getOverlaySubcategoryHeadroom(
            editingProjectSubcategoryUserSubcategoryId,
            Number(editingProjectSubcategoryRow?.limit_amount || 0),
          )
        : null
    ),
    [editingProjectSubcategoryRow, editingProjectSubcategoryUserSubcategoryId, getOverlaySubcategoryHeadroom, structureProject, structureProjectIsIsolated],
  );
  const editingProjectSubcategoryLimitAmount = parseBudgetAmountInput(editingProjectSubcategoryLimit);
  const editingProjectSubcategoryWouldOverbook = Boolean(
    editingProjectSubcategoryHeadroom &&
    editingProjectSubcategoryLimitAmount !== null &&
    editingProjectSubcategoryLimitAmount > Number(editingProjectSubcategoryHeadroom.headroom || 0)
  );

  const sortedBudgets = React.useMemo(
    () =>
      [...budgets].sort((a, b) =>
        b.budgetYear - a.budgetYear ||
        b.budgetMonth - a.budgetMonth ||
        compareLocalizedCategory(a.category, b.category)
      ),
    [budgets, compareLocalizedCategory]
  );

  const visibleBudgets = React.useMemo(
    () =>
      showHistory
        ? sortedBudgets
        : sortedBudgets.filter((b) => b.budgetYear === currentYear && b.budgetMonth === currentMonth),
    [showHistory, sortedBudgets, currentYear, currentMonth]
  );

  const maxBudgetAmountDigits = String(MAX_BUDGET_AMOUNT).length;
  const maxBudgetAmountInputLength = formatUzs(MAX_BUDGET_AMOUNT).length;
  const monthLocale = getDateLocale(appLang);
  const fallbackMonthNames = getFallbackMonthsLong(appLang);

  const formatBudgetMonth = React.useCallback((year, month) => formatMonthYear(year, month, appLang), [appLang]);

  const formatBudgetAmountInput = (raw) => formatAmountInput(raw, maxBudgetAmountDigits);
  const activeBudgetMonthLabel = formatBudgetMonth(currentYear, currentMonth);
  const isOverlayProjectDraft = projectIsIsolated === "false";
  const projectWalletRows = React.useMemo(() => {
    const wallets = Array.isArray(projectWalletsQuery.data) ? projectWalletsQuery.data : EMPTY_ARRAY;
    return wallets
      .filter((wallet) => wallet.is_active !== false && Number(wallet.owned_balance ?? wallet.current_balance ?? 0) > 0)
      .map((wallet) => {
        const input = projectWalletAllocations[String(wallet.id)] || "";
        const amount = parseBudgetAmountInput(input) || 0;
        const freeToAllocate = Number(wallet.free_to_allocate ?? Math.max(Number(wallet.current_balance || 0), 0));
        return {
          wallet,
          input,
          amount,
          freeToAllocate,
          isInvalidAmount: Boolean(input) && amount <= 0,
          isOverAllocated: amount > freeToAllocate,
        };
      });
  }, [projectWalletAllocations, projectWalletsQuery.data]);
  const projectWalletAllocationPayload = React.useMemo(
    () => projectWalletRows
      .filter((row) => row.amount > 0)
      .map((row) => ({ wallet_id: Number(row.wallet.id), amount: row.amount })),
    [projectWalletRows],
  );
  const projectDerivedStashTotal = React.useMemo(
    () => projectWalletAllocationPayload.reduce((sum, item) => sum + Number(item.amount || 0), 0),
    [projectWalletAllocationPayload],
  );
  const projectIsolatedFundingValid = projectWalletAllocationPayload.length > 0 &&
    projectWalletRows.every((row) => !row.isInvalidAmount && !row.isOverAllocated);
  const projectOverlayCategoryAllocationRows = React.useMemo(
    () => getOverlayCategoryAllocationRows({
      selectedCategories: projectSelectedCategories,
      categoryAllocations: projectCategoryAllocations,
      getCategoryHeadroom: getJitOverlayCategoryHeadroom,
    }),
    [getJitOverlayCategoryHeadroom, projectCategoryAllocations, projectSelectedCategories],
  );
  const projectIsolatedCategoryAllocationRows = React.useMemo(
    () => getIsolatedCategoryAllocationRows({
      selectedCategories: projectSelectedCategories,
      categoryAllocations: projectCategoryAllocations,
    }),
    [projectCategoryAllocations, projectSelectedCategories],
  );
  const projectCategoryAllocationRows = isOverlayProjectDraft
    ? projectOverlayCategoryAllocationRows
    : projectIsolatedCategoryAllocationRows;
  const projectIsolatedCategorySummary = React.useMemo(
    () => getIsolatedCategoryAllocationSummary({
      categoryAllocationRows: projectIsolatedCategoryAllocationRows,
      stashTotal: projectDerivedStashTotal,
    }),
    [projectDerivedStashTotal, projectIsolatedCategoryAllocationRows],
  );
  const projectOverlayStepOneValid = Boolean(projectTitle.trim() && projectStartDate) &&
    !(projectTargetEndDate && projectTargetEndDate < projectStartDate);
  const projectOverlayStepTwoValid = projectSelectedCategories.length > 0;
  const projectOverlayStepThreeValid = projectOverlayCategoryAllocationRows.length > 0 &&
    projectOverlayCategoryAllocationRows.every((row) => !row.isMissingBudget && !row.isInvalidAmount && !row.isOverbooked);
  const projectIsolatedStepOneValid = projectOverlayStepOneValid;
  const projectIsolatedStepTwoValid = projectIsolatedFundingValid;
  const projectIsolatedStepThreeValid = projectIsolatedCategoryAllocationRows.length > 0 &&
    projectIsolatedCategoryAllocationRows.every((row) => !row.isInvalidAmount) &&
    !projectIsolatedCategorySummary.isOverAllocated;
  const projectMicroSubcategories = React.useMemo(
    () => Array.isArray(projectMicroSubcategoriesQuery.data) ? projectMicroSubcategoriesQuery.data : [],
    [projectMicroSubcategoriesQuery.data],
  );
  const projectMicroNeedsMonthlyLane = Boolean(
    projectMicroCategory &&
    projectMicroBudget &&
    !projectMicroSubcategoriesQuery.isLoading &&
    projectMicroSubcategories.length === 0
  );
  const projectUsedMicroSubcategoryIds = React.useMemo(
    () => new Set(projectSubcategoryReservations.map((item) => String(item.user_subcategory_id))),
    [projectSubcategoryReservations],
  );
  const projectEligibleMicroSubcategories = React.useMemo(
    () => projectMicroSubcategories.filter((item) => !projectUsedMicroSubcategoryIds.has(String(item.id))),
    [projectMicroSubcategories, projectUsedMicroSubcategoryIds],
  );
  const projectMicroSelectedSubcategory = React.useMemo(
    () => projectMicroSubcategories.find((item) => String(item.id) === String(projectMicroSubcategoryId)) || null,
    [projectMicroSubcategories, projectMicroSubcategoryId],
  );
  const projectMicroSelectedHeadroom = React.useMemo(() => {
    if (!projectMicroSelectedSubcategory) {
      return { subcategory: null, reserved: 0, headroom: 0 };
    }
    const reserved = Number(jitOverlayReservationTotalsBySubcategory.get(String(projectMicroSelectedSubcategory.id)) || 0);
    return {
      subcategory: projectMicroSelectedSubcategory,
      reserved,
      headroom: Math.max(Number(projectMicroSelectedSubcategory.monthly_limit || 0) - reserved, 0),
    };
  }, [jitOverlayReservationTotalsBySubcategory, projectMicroSelectedSubcategory]);
  const projectMicroLimitAmount = parseBudgetAmountInput(projectMicroLimit);
  const projectMicroWouldOverbook = Boolean(
    projectMicroSelectedSubcategory &&
    projectMicroLimitAmount !== null &&
    projectMicroLimitAmount > Number(projectMicroSelectedHeadroom.headroom || 0)
  );

  const taxonomyQuery = useTaxonomyQuery();
  const projectIsolatedMicroSubcategories = React.useMemo(() => {
    if (!taxonomyQuery.data) return [];
    return taxonomyQuery.data.filter(tag => tag.category === projectMicroCategory && tag.is_active);
  }, [taxonomyQuery.data, projectMicroCategory]);

  const projectIsolatedUsedMicroSubcategoryIds = React.useMemo(
    () => new Set(projectIsolatedSubcategoryAllocations.map((item) => String(item.user_subcategory_id))),
    [projectIsolatedSubcategoryAllocations],
  );

  const projectIsolatedEligibleMicroSubcategories = React.useMemo(
    () => projectIsolatedMicroSubcategories.filter((item) => !projectIsolatedUsedMicroSubcategoryIds.has(String(item.id))),
    [projectIsolatedMicroSubcategories, projectIsolatedUsedMicroSubcategoryIds],
  );

  const projectIsolatedMicroSelectedSubcategory = React.useMemo(
    () => projectIsolatedMicroSubcategories.find((item) => String(item.id) === String(projectMicroSubcategoryId)) || null,
    [projectIsolatedMicroSubcategories, projectMicroSubcategoryId],
  );

  const projectIsolatedMicroSelectedHeadroom = React.useMemo(() => {
    if (!projectMicroCategory) return { headroom: 0, isOverAllocated: false };
    return getIsolatedSubcategoryAllocationSummary({
      category: projectMicroCategory,
      categoryAllocationRows: projectIsolatedCategoryAllocationRows,
      subcategoryAllocations: projectIsolatedSubcategoryAllocations,
    });
  }, [projectMicroCategory, projectIsolatedCategoryAllocationRows, projectIsolatedSubcategoryAllocations]);

  const projectIsolatedMicroWouldOverbook = Boolean(
    projectIsolatedMicroSelectedSubcategory &&
    projectMicroLimitAmount !== null &&
    projectMicroLimitAmount > Number(projectIsolatedMicroSelectedHeadroom.headroom || 0)
  );
  
  const projectIsolatedMicroNeedsTaxonomyCreate = projectMicroCategory && projectIsolatedMicroSubcategories.length === 0;
  const canAdvanceProjectWizard = isOverlayProjectDraft
    ? (
      projectWizardStep === 1 ? projectOverlayStepOneValid :
      projectWizardStep === 2 ? projectOverlayStepTwoValid :
      projectWizardStep === 3 ? projectOverlayStepThreeValid :
      true
    )
    : (
      projectWizardStep === 1 ? projectIsolatedStepOneValid :
      projectWizardStep === 2 ? projectIsolatedStepTwoValid :
      projectWizardStep === 3 ? projectIsolatedStepThreeValid :
      true
    );
  const projectCurrentMonthReservationTotal = React.useMemo(
    () => projectOverlayCategoryAllocationRows.reduce((sum, row) => sum + Number(row.amount || 0), 0),
    [projectOverlayCategoryAllocationRows],
  );
  const projectCurrentMonthMicroReservationTotal = React.useMemo(
    () => projectSubcategoryReservations.reduce((sum, item) => sum + Number(item.limit_amount || 0), 0),
    [projectSubcategoryReservations],
  );
  const overlayWizardSteps = React.useMemo(
    () => [
      t("projects.identityStep", { defaultValue: "Identity" }),
      t("projects.scopeStep", { defaultValue: "Scope" }),
      t("projects.allocateStep", { defaultValue: "Allocate" }),
      t("projects.reviewStep", { defaultValue: "Review" }),
    ],
    [t],
  );
  const isolatedWizardSteps = React.useMemo(
    () => [
      t("projects.identityStep", { defaultValue: "Identity" }),
      t("projects.walletQuarantineStep", { defaultValue: "Wallets" }),
      t("projects.parentCategoriesStep", { defaultValue: "Categories" }),
      t("projects.microStructureStep", { defaultValue: "Subcategories" }),
    ],
    [t],
  );
  const projectWizardSteps = isOverlayProjectDraft ? overlayWizardSteps : isolatedWizardSteps;
  const projectMaxWizardStep = projectWizardSteps.length;

  const budgetYearOptions = React.useMemo(() => {
    const minYear = 2020;
    const maxYear = currentYear + 5;
    return Array.from({ length: maxYear - minYear + 1 }, (_, i) => maxYear - i);
  }, [currentYear]);

  const budgetMonthOptions = React.useMemo(
    () =>
      Array.from({ length: 12 }, (_, i) => {
        const month = i + 1;
        return {
          value: month,
          label: (() => {
            const formatted = new Intl.DateTimeFormat(monthLocale, { month: "long" }).format(
              new Date(2024, i, 1)
            );
            return /M\d{2}/.test(formatted) ? fallbackMonthNames[i] : formatted;
          })(),
        };
      }),
    [monthLocale, fallbackMonthNames]
  );

  const visibleMonthOptions = React.useMemo(() => {
    const maxMonthForYear = addBudgetYear === currentYear + 5 ? currentMonth : 12;
    return budgetMonthOptions.filter((m) => m.value <= maxMonthForYear);
  }, [budgetMonthOptions, addBudgetYear, currentYear, currentMonth]);

  const tZodError = (parsed) => {
    const key = parsed?.error?.issues?.[0]?.message;
    return key ? t(key, { defaultValue: key }) : t("common.error", { defaultValue: "Invalid input" });
  };

  const getBudgetActionErrorMessage = (e) => {
    if (e?.status === 429) {
      const wait = Number(e?.retryAfterSeconds || 0);
      if (Number.isFinite(wait) && wait > 0) {
        return t("budgets.tooManyWait", { seconds: wait });
      }
      return t("budgets.tooManySoon");
    }
    if (e?.detail?.code === "budgets.plan_exceeds_backing") {
      return t("budgets.planExceedsBacking", {
        defaultValue: "Cannot set this budget. Requested monthly budgets exceed valid backing by {{shortfall}}.",
        shortfall: formatUzs(Number(e.detail.shortfall || 0)),
        attempted: formatUzs(Number(e.detail.attempted_total || 0)),
        backing: formatUzs(Number(e.detail.backing_total || 0)),
      });
    }
    return localizeApiError(e?.message, t) || t("budgets.requestFailed");
  };

  const selectTriggerClass = "w-full bg-white text-black dark:bg-black dark:text-white dark:hover:bg-black";
  const selectContentClass = "max-h-[190px] overflow-y-auto bg-white text-black dark:bg-black dark:text-white";
  const inputBaseClass = "dark:bg-input/30 border-input h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm";

  const deriveProgressStatus = (backendStatus, percent) => {
    if (backendStatus === "Over Limit") return "danger";
    if (backendStatus === "High Risk") return "highRisk";
    if (backendStatus === "Warning") return "warning";
    if (backendStatus === "On Track") return "healthy";
    if (percent >= 100) return "danger";
    if (percent >= 90) return "highRisk";
    if (percent >= 70) return "warning";
    return "healthy";
  };

  const budgetsWithDerived = React.useMemo(
    () =>
      visibleBudgets.map((b) => {
        const percent = b.limit > 0 ? Math.min(Math.round((b.spent / b.limit) * 100), 100) : 0;
        return {
          ...b,
          percent,
          progressStatus: deriveProgressStatus(b.backendStatus, percent),
          monthKey: `${b.budgetYear}-${String(b.budgetMonth).padStart(2, "0")}`,
        };
      }),
    [visibleBudgets]
  );

  const monthFilterOptions = React.useMemo(() => {
    const source = showHistory ? sortedBudgets : visibleBudgets;
    const seen = new Set();
    return source
      .map((b) => ({
        value: `${b.budgetYear}-${String(b.budgetMonth).padStart(2, "0")}`,
        label: formatBudgetMonth(b.budgetYear, b.budgetMonth),
      }))
      .filter((item) => {
        if (seen.has(item.value)) return false;
        seen.add(item.value);
        return true;
      });
  }, [showHistory, sortedBudgets, visibleBudgets, formatBudgetMonth]);

  const orderedCategoryOptions = React.useMemo(() => {
    const set = new Set(categories || []);
    const inOrder = CATEGORIES.filter((c) => set.has(c));
    const extras = [...set].filter((c) => !CATEGORIES.includes(c));
    return [...inOrder, ...extras];
  }, [categories]);

  const filteredBudgets = React.useMemo(() => {
    let rows = budgetsWithDerived;
    if (filterCategory !== "all") {
      rows = rows.filter((b) => b.category === filterCategory);
    }
    if (filterStatus !== "all") {
      rows = rows.filter((b) => b.progressStatus === filterStatus);
    }
    if (filterMonth !== "all") {
      rows = rows.filter((b) => b.monthKey === filterMonth);
    }
    const sorted = [...rows];
    sorted.sort((a, b) => {
      switch (sortBy) {
        case "oldest":
          return a.budgetYear - b.budgetYear || a.budgetMonth - b.budgetMonth || compareLocalizedCategory(a.category, b.category);
        case "percentDesc":
          return b.percent - a.percent || compareLocalizedCategory(a.category, b.category);
        case "percentAsc":
          return a.percent - b.percent || compareLocalizedCategory(a.category, b.category);
        case "remainingDesc":
          return b.remaining - a.remaining || compareLocalizedCategory(a.category, b.category);
        case "remainingAsc":
          return a.remaining - b.remaining || compareLocalizedCategory(a.category, b.category);
        case "limitDesc":
          return b.limit - a.limit || compareLocalizedCategory(a.category, b.category);
        case "limitAsc":
          return a.limit - b.limit || compareLocalizedCategory(a.category, b.category);
        case "category":
          return compareLocalizedCategory(a.category, b.category);
        default:
          return b.budgetYear - a.budgetYear || b.budgetMonth - a.budgetMonth || compareLocalizedCategory(a.category, b.category);
      }
    });
    return sorted;
  }, [budgetsWithDerived, filterCategory, filterStatus, filterMonth, sortBy, compareLocalizedCategory]);
  const planningSummary = React.useMemo(() => ({
    planned: filteredBudgets.reduce((sum, budget) => sum + Number(budget.effectiveLimit || 0), 0),
    spent: filteredBudgets.reduce((sum, budget) => sum + Number(budget.spent || 0), 0),
    remaining: filteredBudgets.reduce((sum, budget) => sum + Number(budget.remaining || 0), 0),
    atRisk: filteredBudgets.filter((budget) => budget.progressStatus === "warning" || budget.progressStatus === "highRisk" || budget.progressStatus === "danger").length,
  }), [filteredBudgets]);
  const monthSummary = monthSummaryQuery.data || null;
  const planStatusMeta = getPlanStatusMeta(monthSummary?.plan_status, t);
  const activePlanningFilterCount = React.useMemo(
    () => [filterCategory !== "all", filterStatus !== "all", filterMonth !== "all", sortBy !== "newest"].filter(Boolean).length,
    [filterCategory, filterStatus, filterMonth, sortBy]
  );
  const useBottomSheetForms = windowWidth < 1024;
  const resetBudgetFilters = () => {
    setSearchParams(prev => {
      prev.delete("category");
      prev.delete("status");
      prev.delete("month");
      prev.delete("sort");
      return prev;
    }, { replace: true });
  };

  const addBudgetFormParsed = React.useMemo(() => {
    const budgetMonthValue = `${addBudgetYear}-${String(addBudgetMonth).padStart(2, "0")}`;
    return budgetCreateFormSchema.safeParse({
      category: addCategory,
      monthly_limit: addLimit,
      budget_month_value: budgetMonthValue,
    });
  }, [addBudgetYear, addBudgetMonth, addCategory, addLimit]);

  const addBudgetMutation = useCreateBudgetMutation();
  const updateBudgetMutation = useUpdateBudgetMutation();
  const deleteBudgetMutation = useDeleteBudgetMutation();
  const reallocateBudgetMutation = useReallocateBudgetMutation();
  const invalidateProjectFinancialState = React.useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
      queryClient.invalidateQueries({ queryKey: ["expenses"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
  }, [queryClient, summaryTarget.month, summaryTarget.year]);

  const createProjectMutation = useMutation({
    mutationFn: createProject,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["wallets"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.created", { defaultValue: "Project created" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.failedToCreate", { defaultValue: "Failed to create project" }), msg);
    },
  });
  const createOverlayProjectMutation = useMutation({
    mutationFn: createOverlayProject,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", currentYear, currentMonth] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.created", { defaultValue: "Project created" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.failedToCreate", { defaultValue: "Failed to create project" }), msg);
    },
  });

  const isAddingBudget = addBudgetMutation.isPending;
  const isUpdatingBudget = updateBudgetMutation.isPending;
  const isDeletingBudget = deleteBudgetMutation.isPending;
  const isCreatingProject = createProjectMutation.isPending || createOverlayProjectMutation.isPending;
  const createProjectCategoryMutation = useMutation({
    mutationFn: ({ projectId, payload }) => createProjectCategoryLimit(projectId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.categoryLimitCreated", { defaultValue: "Project category added" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.categoryLimitCreateFailed", { defaultValue: "Failed to add project category" }), msg);
    },
  });
  const updateProjectCategoryMutation = useMutation({
    mutationFn: ({ projectId, category, payload }) => updateProjectCategoryLimit(projectId, category, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.categoryLimitUpdated", { defaultValue: "Project category updated" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.categoryLimitUpdateFailed", { defaultValue: "Failed to update project category" }), msg);
    },
  });
  const deleteProjectCategoryMutation = useMutation({
    mutationFn: ({ projectId, category, budgetYear, budgetMonth }) => (
      deleteProjectCategoryLimit(projectId, category, { budgetYear, budgetMonth })
    ),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.categoryLimitDeleted", { defaultValue: "Project category deleted" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.categoryLimitDeleteFailed", { defaultValue: "Failed to delete project category" }), msg);
    },
  });
  const createProjectSubcategoryMutation = useMutation({
    mutationFn: ({ projectId, payload }) => createProjectSubcategory(projectId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.projectSubcategoryCreated", { defaultValue: "Project subcategory created" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.projectSubcategoryCreateFailed", { defaultValue: "Failed to create project subcategory" }), msg);
    },
  });
  const updateProjectSubcategoryMutation = useMutation({
    mutationFn: ({ projectId, subcategoryId, payload }) => updateProjectSubcategory(projectId, subcategoryId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.projectSubcategoryUpdated", { defaultValue: "Project subcategory updated" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.projectSubcategoryUpdateFailed", { defaultValue: "Failed to update project subcategory" }), msg);
    },
  });
  const deleteProjectSubcategoryMutation = useMutation({
    mutationFn: ({ projectId, subcategoryId }) => deleteProjectSubcategory(projectId, subcategoryId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary", summaryTarget.year, summaryTarget.month] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      toast.success(t("projects.projectSubcategoryDeleted", { defaultValue: "Project subcategory deleted" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.projectSubcategoryDeleteFailed", { defaultValue: "Failed to delete project subcategory" }), msg);
    },
  });
  const projectDeletePreviewMutation = useMutation({
    mutationFn: getProjectDeletePreview,
  });
  const deleteProjectMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      await invalidateProjectFinancialState();
      toast.success(t("projects.deleted", { defaultValue: "Project deleted" }));
    },
  });
  const resolveProjectDeletionMutation = useMutation({
    mutationFn: ({ projectId, payload }) => resolveProjectDeletion(projectId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateProjectFinancialState();
      setProjectDeletionOpen(false);
      setProjectDeletionTarget(null);
      setProjectDeletionPreview(null);
      setProjectDeletionConfirmTitle("");
      const successKey = variables?.payload?.action === PROJECT_DELETE_ACTIONS.ARCHIVE
        ? "projects.archived"
        : "projects.deleted";
      const successDefault = variables?.payload?.action === PROJECT_DELETE_ACTIONS.ARCHIVE
        ? "Project archived"
        : "Project deleted";
      toast.success(t(successKey, { defaultValue: successDefault }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.deleteResolutionFailed", { defaultValue: "Failed to resolve project deletion" }), msg);
    },
  });
  const stopProjectMutation = useMutation({
    mutationFn: stopProject,
    onSuccess: async () => {
      await invalidateProjectFinancialState();
      setProjectLifecycleOpen(false);
      setProjectLifecycleTarget(null);
      setProjectLifecycleAction(null);
      toast.success(t("projects.paused", { defaultValue: "Project paused" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.pauseFailed", { defaultValue: "Failed to pause project" }), msg);
    },
  });
  const resumeProjectMutation = useMutation({
    mutationFn: resumeProject,
    onSuccess: async () => {
      await invalidateProjectFinancialState();
      setProjectLifecycleOpen(false);
      setProjectLifecycleTarget(null);
      setProjectLifecycleAction(null);
      toast.success(t("projects.resumed", { defaultValue: "Project resumed" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.resumeFailed", { defaultValue: "Failed to resume project" }), msg);
    },
  });
  const completeProjectMutation = useMutation({
    mutationFn: ({ projectId }) => completeProject(projectId),
    onSuccess: async () => {
      await invalidateProjectFinancialState();
      setProjectLifecycleOpen(false);
      setProjectLifecycleTarget(null);
      setProjectLifecycleAction(null);
      toast.success(t("projects.completed", { defaultValue: "Project completed" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.completeFailed", { defaultValue: "Failed to complete project" }), msg);
    },
  });
  const reopenProjectMutation = useMutation({
    mutationFn: reopenProject,
    onSuccess: async () => {
      await invalidateProjectFinancialState();
      toast.success(t("projects.restored", { defaultValue: "Project restored" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.restoreFailed", { defaultValue: "Failed to restore project" }), msg);
    },
  });
  const createSubcategoryMutation = useMutation({
    mutationFn: ({ budgetId, payload }) => createBudgetSubcategory(budgetId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", subcategoryTargetBudget?.id, "subcategories"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
      ]);
      toast.success(t("budgets.subcategoryCreated", { defaultValue: "Subcategory created" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("budgets.subcategoryCreateFailed", { defaultValue: "Failed to create subcategory" }), msg);
    },
  });
  const updateSubcategoryMutation = useMutation({
    mutationFn: ({ subcategoryId, budgetId, payload }) => updateBudgetSubcategory(subcategoryId, payload, budgetId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", subcategoryTargetBudget?.id, "subcategories"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
      ]);
      toast.success(t("budgets.subcategoryUpdated", { defaultValue: "Subcategory updated" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("budgets.subcategoryUpdateFailed", { defaultValue: "Failed to update subcategory" }), msg);
    },
  });
  const reallocateSubcategoryMutation = useMutation({
    mutationFn: ({ budgetId, payload }) => reallocateBudgetSubcategory(budgetId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", subcategoryTargetBudget?.id, "subcategories"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-summary"] }),
      ]);
      toast.success(t("budgets.subcategoryReallocated", { defaultValue: "Subcategory limit reallocated" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("budgets.subcategoryReallocateFailed", { defaultValue: "Failed to reallocate subcategory limit" }), msg);
    },
  });
  const deleteSubcategoryMutation = useMutation({
    mutationFn: ({ subcategoryId, budgetId }) => deleteBudgetSubcategory(subcategoryId, budgetId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["budgets"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", subcategoryTargetBudget?.id, "subcategories"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
      ]);
      toast.success(t("budgets.subcategoryDeleted", { defaultValue: "Subcategory deleted" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("budgets.subcategoryDeleteFailed", { defaultValue: "Failed to delete subcategory" }), msg);
    },
  });
  const canSubmitAddBudget = addBudgetFormParsed.success && !isAddingBudget;

  const updateBudgetFormParsed = React.useMemo(
    () =>
      budgetUpdateFormSchema.safeParse({
        monthly_limit: newLimit,
        category: selectedBudget?.category ?? "",
        budgetYear: selectedBudget?.budgetYear,
        budgetMonth: selectedBudget?.budgetMonth,
      }),
    [newLimit, selectedBudget]
  );
  const canSubmitUpdateBudget = updateBudgetFormParsed.success && !isUpdatingBudget;
  const isProjectDeletionPending = projectDeletePreviewMutation.isPending
    || deleteProjectMutation.isPending
    || resolveProjectDeletionMutation.isPending;
  const isProjectLifecyclePending = stopProjectMutation.isPending
    || resumeProjectMutation.isPending
    || completeProjectMutation.isPending
    || reopenProjectMutation.isPending;
  const projectDeletionLinkedCount = Number(projectDeletionPreview?.linked_expense_count || 0);
  const projectDeletionLinkedTotal = Number(projectDeletionPreview?.linked_expense_total || 0);
  const canCascadeVoidProject = canSubmitCascadeVoid(projectDeletionTarget, projectDeletionConfirmTitle);
  const projectLifecycleIsComplete = projectLifecycleAction === PROJECT_LIFECYCLE_ACTIONS.COMPLETE;
  const projectLifecycleIsPause = projectLifecycleAction === PROJECT_LIFECYCLE_ACTIONS.PAUSE;
  const projectLifecycleTargetIsStopped = projectLifecycleTarget?.status === "STOPPED";
  const projectLifecycleIsOverdue = Boolean(
    projectLifecycleTarget?.target_end_date && projectLifecycleTarget.target_end_date < todayIso
  );
  const projectLifecycleTitle = projectLifecycleIsComplete
    ? (
      projectLifecycleIsOverdue
        ? t("projects.wrapUpProjectTitle", { defaultValue: "Wrap up project" })
        : projectLifecycleTargetIsStopped
          ? t("projects.completeProjectNowTitle", { defaultValue: "Complete project now" })
          : t("projects.completeProjectEarlyTitle", { defaultValue: "Complete project early" })
    )
    : projectLifecycleIsPause
      ? t("projects.pauseProjectTitle", { defaultValue: "Pause project" })
      : t("projects.resumeProjectTitle", { defaultValue: "Resume project" });
  const projectLifecycleDescription = projectLifecycleIsComplete
    ? t("projects.completeProjectDesc", {
      defaultValue: "{{title}} will be marked completed. Unused current and future overlay reservations will be swept back to the parent budgets.",
      title: projectLifecycleTarget?.title || "",
    })
    : projectLifecycleIsPause
      ? t("projects.pauseProjectDesc", {
        defaultValue: "{{title}} will stop accepting new project expenses, but its overlay reservations will stay held.",
        title: projectLifecycleTarget?.title || "",
      })
      : t("projects.resumeProjectDesc", {
        defaultValue: "{{title}} will accept project expenses again.",
        title: projectLifecycleTarget?.title || "",
      });
  const projectLifecycleConfirmText = projectLifecycleIsComplete
    ? (
      projectLifecycleIsOverdue
        ? t("projects.wrapUpProject", { defaultValue: "Wrap up project" })
        : projectLifecycleTargetIsStopped
          ? t("projects.completeNow", { defaultValue: "Complete now" })
          : t("projects.completeEarly", { defaultValue: "Complete early" })
    )
    : projectLifecycleIsPause
      ? t("projects.pauseProject", { defaultValue: "Pause project" })
      : t("projects.resumeProject", { defaultValue: "Resume project" });
  const openExpectedIncomeDialog = () => {
    const targetMonth = `${summaryTarget.year}-${String(summaryTarget.month).padStart(2, "0")}`;
    navigate(`/money-in/expected-inflow?expected_month=${targetMonth}&action=add`);
  };

  const openBudgetExpenses = (budget) => {
    setExpensesTargetBudget(budget);
    setViewExpensesOpen(true);
  };

  const openBudgetDetails = (budget) => {
    setDetailsTargetBudget(budget);
    setViewDetailsOpen(true);
  };

  const openUpdate = (budget) => {
    setActionError("");
    setSelectedBudget(budget);
    setNewLimit(formatBudgetAmountInput(String(budget.baseLimit)));
    setUpdateOpen(true);
  };

  const openDelete = (budget) => {
    setActionError("");
    setSelectedBudget(budget);
    setDeleteOpen(true);
  };

  const closeProjectDeletionResolution = (open) => {
    setProjectDeletionOpen(open);
    if (!open) {
      setProjectDeletionTarget(null);
      setProjectDeletionPreview(null);
      setProjectDeletionConfirmTitle("");
    }
  };

  async function handleProjectDeleteClick(project) {
    setActionError("");
    try {
      const preview = await projectDeletePreviewMutation.mutateAsync(project.id);
      if (shouldOpenProjectDeletionResolution(preview)) {
        setProjectDeletionTarget(project);
        setProjectDeletionPreview(preview);
        setProjectDeletionConfirmTitle("");
        setProjectDeletionOpen(true);
        return;
      }
      await deleteProjectMutation.mutateAsync(project.id);
    } catch (error) {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("projects.deleteFailed", { defaultValue: "Failed to delete project" }), msg);
    }
  }

  async function handleResolveProjectDeletion(action) {
    if (!projectDeletionTarget) return;
    const payload = buildProjectDeletionResolutionPayload(
      action,
      projectDeletionTarget,
      projectDeletionConfirmTitle,
    );
    try {
      await resolveProjectDeletionMutation.mutateAsync({
        projectId: projectDeletionTarget.id,
        payload,
      });
    } catch {
      // Error toast is handled by the mutation.
    }
  }

  function openProjectLifecycleDialog(project, action) {
    setActionError("");
    setProjectLifecycleTarget(project);
    setProjectLifecycleAction(action);
    setProjectLifecycleOpen(true);
  }

  function closeProjectLifecycleDialog(open) {
    setProjectLifecycleOpen(open);
    if (!open) {
      setProjectLifecycleTarget(null);
      setProjectLifecycleAction(null);
    }
  }

  async function handleConfirmProjectLifecycle() {
    if (!projectLifecycleTarget || !projectLifecycleAction) return;
    const projectId = projectLifecycleTarget.id;
    try {
      if (projectLifecycleAction === PROJECT_LIFECYCLE_ACTIONS.PAUSE) {
        await stopProjectMutation.mutateAsync(projectId);
        return;
      }
      if (projectLifecycleAction === PROJECT_LIFECYCLE_ACTIONS.RESUME) {
        await resumeProjectMutation.mutateAsync(projectId);
        return;
      }
      await completeProjectMutation.mutateAsync({ projectId });
    } catch {
      // Error toast is handled by the mutation.
    }
  }

  const openAdd = () => {
    setActionError("");
    setAddCategory("");
    setAddLimit("");
    setAddBudgetYear(currentYear);
    setAddBudgetMonth(currentMonth);
    setAddOpen(true);
  };

  const openProject = () => {
    setActionError("");
    setProjectTitle("");
    setProjectDescription("");
    setProjectIsIsolated("true");
    setProjectWalletAllocations({});
    setProjectTargetEstimate("");
    setProjectStartDate(`${currentYear}-${String(currentMonth).padStart(2, "0")}-01`);
    setProjectTargetEndDate("");
    setProjectWizardStep(1);
    setProjectSelectedCategories([]);
    setProjectCategoryAllocations({});
    setProjectMicroCategory("");
    setProjectMicroSubcategoryId("");
    setProjectMicroLimit("");
    setProjectSubcategoryReservations([]);
    setProjectIsolatedSubcategoryAllocations([]);
    setReturnToOverlayWizardAfterSubcategories(false);
    setProjectOpen(true);
  };

  const openProjectStructure = (project) => {
    navigate(`/projects/${project.id}`);
  };

  const openSubcategories = (budget, repair = null) => {
    setActionError("");
    setSubcategoryTargetBudget(budget);
    setSubcategoryName("");
    setSubcategoryExistingId(null);
    setSubcategoryComboboxOpen(false);
    setSubcategoryLimit("");
    setSubcategoryIsActive("true");
    setEditingSubcategoryId(null);
    setEditingSubcategoryName("");
    setEditingSubcategoryLimit("");
    setEditingSubcategoryIsActive("true");
    setReallocationTargetId(repair?.targetId ? String(repair.targetId) : "");
    setReallocationSourceId("buffer");
    setReallocationAmount(repair?.amount ? formatBudgetAmountInput(String(repair.amount)) : "");
    setSubcategoriesOpen(true);
  };

  const openProjectMicroTaxonomy = () => {
    if (!projectMicroBudget) return;
    setActionError("");
    setReturnToOverlayWizardAfterSubcategories(true);
    setProjectOpen(false);
    openSubcategories(projectMicroBudget);
  };

  const closeSubcategories = () => {
    setSubcategoriesOpen(false);
    if (returnToOverlayWizardAfterSubcategories) {
      setReturnToOverlayWizardAfterSubcategories(false);
      setActionError("");
      setProjectWizardStep(4);
      setProjectOpen(true);
    }
  };

  const openParentReallocate = (budget) => {
    setActionError("");
    setParentReallocateSourceBudget(budget);
    setParentReallocateTargetCategory("");
    setParentReallocateAmount("");
    setParentReallocateOpen(true);
  };

  const toggleProjectCategory = (category) => {
    setProjectSelectedCategories((current) => {
      if (current.includes(category)) {
        const next = current.filter((item) => item !== category);
        setProjectCategoryAllocations((allocations) => {
          const rest = { ...allocations };
          delete rest[category];
          return rest;
        });
        setProjectSubcategoryReservations((items) => items.filter((item) => item.category !== category));
        setProjectIsolatedSubcategoryAllocations((items) => items.filter((item) => item.category !== category));
        if (projectMicroCategory === category) {
          setProjectMicroCategory("");
          setProjectMicroSubcategoryId("");
          setProjectMicroLimit("");
        }
        return next;
      }
      return [...current, category];
    });
  };

  const handleProjectWizardNext = () => {
    setActionError("");
    if (!canAdvanceProjectWizard) {
      setActionError(t("projects.overlayWizardIncomplete", { defaultValue: "Complete the current step before continuing." }));
      return;
    }
    setProjectWizardStep((step) => Math.min(step + 1, projectMaxWizardStep));
  };

  const handleProjectWizardBack = () => {
    setActionError("");
    setProjectWizardStep((step) => Math.max(step - 1, 1));
  };

  const handleAddProjectMicroReservation = () => {
    setActionError("");
    if (!projectMicroCategory || !projectMicroSubcategoryId || !projectMicroSelectedSubcategory) {
      setActionError(t("projects.globalSubcategoryRequired", { defaultValue: "Choose a monthly budget subcategory first" }));
      return;
    }
    if (!projectMicroLimitAmount || projectMicroLimitAmount <= 0) {
      setActionError(t("projects.projectSubcategoryLimitInvalid", { defaultValue: "Project subcategory limit must be greater than zero" }));
      return;
    }
    if (projectMicroWouldOverbook) {
      setActionError(t("projects.overlayReservationOverbooked", { defaultValue: "Reservation exceeds available selected-month headroom." }));
      return;
    }
    setProjectSubcategoryReservations((items) => [
      ...items,
      {
        category: projectMicroCategory,
        user_subcategory_id: Number(projectMicroSubcategoryId),
        name: projectMicroSelectedSubcategory.name,
        limit_amount: projectMicroLimitAmount,
      },
    ]);
    setProjectMicroSubcategoryId("");
    setProjectMicroLimit("");
  };

  const removeProjectMicroReservation = (userSubcategoryId) => {
    setProjectSubcategoryReservations((items) =>
      items.filter((item) => String(item.user_subcategory_id) !== String(userSubcategoryId))
    );
  };

  const addProjectIsolatedMicroReservation = () => {
    setActionError("");
    if (!projectMicroCategory || !projectIsolatedMicroSelectedSubcategory) {
      setActionError(t("projects.projectSubcategoryRequired", { defaultValue: "Please select a category and subcategory." }));
      return;
    }
    const amount = parseBudgetAmountInput(projectMicroLimit);
    if (!amount || amount <= 0) {
      setActionError(t("projects.projectSubcategoryLimitInvalid", { defaultValue: "Project subcategory limit must be greater than zero" }));
      return;
    }
    if (projectIsolatedMicroWouldOverbook) {
      setActionError(t("projects.isolatedReservationOverbooked", { defaultValue: "Reservation exceeds available category funding." }));
      return;
    }
    setProjectIsolatedSubcategoryAllocations((items) => [
      ...items,
      {
        category: projectMicroCategory,
        user_subcategory_id: Number(projectMicroSubcategoryId),
        name: projectIsolatedMicroSelectedSubcategory.name,
        limit_amount: amount,
      },
    ]);
    setProjectMicroSubcategoryId("");
    setProjectMicroLimit("");
  };

  const removeProjectIsolatedMicroReservation = (userSubcategoryId) => {
    setProjectIsolatedSubcategoryAllocations((items) =>
      items.filter((item) => String(item.user_subcategory_id) !== String(userSubcategoryId))
    );
  };

  async function handleCreateProjectCategoryLimit() {
    if (!structureProject || createProjectCategoryMutation.isPending) return;
    setActionError("");
    if (!projectCategoryValue) {
      setActionError(t("projects.categoryRequired", { defaultValue: "Choose a category first" }));
      return;
    }
    const limitAmount = parseBudgetAmountInput(projectCategoryLimitValue);
    if (projectCategoryLimitValue && (!Number.isFinite(limitAmount) || limitAmount <= 0)) {
      setActionError(t("projects.categoryLimitInvalid", { defaultValue: "Category limit must be greater than zero" }));
      return;
    }
    if (!structureProjectIsIsolated) {
      if (!projectCategoryHeadroom?.budget) {
        setActionError(t("projects.overlayCategoryNeedsBudget", { defaultValue: "Add this category to the selected monthly budget before reserving it." }));
        return;
      }
      if (projectCategoryWouldOverbook) {
        setActionError(t("projects.overlayReservationOverbooked", { defaultValue: "Reservation exceeds available selected-month headroom." }));
        return;
      }
    }
    try {
      await createProjectCategoryMutation.mutateAsync({
        projectId: structureProject.id,
        payload: {
          category: projectCategoryValue,
          limit_amount: limitAmount,
          budget_year: summaryTarget.year,
          budget_month: summaryTarget.month,
        },
      });
      setProjectCategoryValue("");
      setProjectCategoryLimitValue("");
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleUpdateProjectCategoryLimit() {
    if (!structureProject || !editingProjectCategory || updateProjectCategoryMutation.isPending) return;
    setActionError("");
    const limitAmount = parseBudgetAmountInput(editingProjectCategoryLimit);
    if (editingProjectCategoryLimit && (!Number.isFinite(limitAmount) || limitAmount <= 0)) {
      setActionError(t("projects.categoryLimitInvalid", { defaultValue: "Category limit must be greater than zero" }));
      return;
    }
    if (!structureProjectIsIsolated && editingProjectCategoryWouldOverbook) {
      setActionError(t("projects.overlayReservationOverbooked", { defaultValue: "Reservation exceeds available selected-month headroom." }));
      return;
    }
    try {
      await updateProjectCategoryMutation.mutateAsync({
        projectId: structureProject.id,
        category: editingProjectCategory,
        payload: {
          limit_amount: limitAmount,
          budget_year: summaryTarget.year,
          budget_month: summaryTarget.month,
        },
      });
      setEditingProjectCategory("");
      setEditingProjectCategoryLimit("");
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleCreateProjectSubcategory() {
    if (!structureProject || createProjectSubcategoryMutation.isPending) return;
    setActionError("");
    if (!projectSubcategoryCategory) {
      setActionError(t("projects.categoryRequired", { defaultValue: "Choose a category first" }));
      return;
    }
    if (structureProjectIsIsolated && !projectSubcategoryName.trim()) {
      setActionError(t("projects.projectSubcategoryNameRequired", { defaultValue: "Project subcategory name is required" }));
      return;
    }
    if (!structureProjectIsIsolated && !projectSubcategoryUserSubcategoryId) {
      setActionError(t("projects.globalSubcategoryRequired", { defaultValue: "Choose a monthly budget subcategory first" }));
      return;
    }
    const limitAmount = parseBudgetAmountInput(projectSubcategoryLimit);
    if (!structureProjectIsIsolated && !projectSubcategoryLimit) {
      setActionError(t("projects.projectSubcategoryLimitInvalid", { defaultValue: "Project subcategory limit must be greater than zero" }));
      return;
    }
    if (projectSubcategoryLimit && (!Number.isFinite(limitAmount) || limitAmount <= 0)) {
      setActionError(t("projects.projectSubcategoryLimitInvalid", { defaultValue: "Project subcategory limit must be greater than zero" }));
      return;
    }
    if (!structureProjectIsIsolated && projectSubcategoryWouldOverbook) {
      setActionError(t("projects.overlayReservationOverbooked", { defaultValue: "Reservation exceeds available selected-month headroom." }));
      return;
    }
    try {
      const payload = structureProjectIsIsolated
        ? {
            category: projectSubcategoryCategory,
            name: projectSubcategoryName.trim(),
            limit_amount: limitAmount,
            is_active: projectSubcategoryIsActive === "true",
          }
        : {
            category: projectSubcategoryCategory,
            user_subcategory_id: Number(projectSubcategoryUserSubcategoryId),
            limit_amount: limitAmount,
            budget_year: summaryTarget.year,
            budget_month: summaryTarget.month,
          };
      await createProjectSubcategoryMutation.mutateAsync({
        projectId: structureProject.id,
        payload,
      });
      setProjectSubcategoryCategory("");
      setProjectSubcategoryUserSubcategoryId("");
      setProjectSubcategoryName("");
      setProjectSubcategoryLimit("");
      setProjectSubcategoryIsActive("true");
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleUpdateProjectSubcategory() {
    if (!structureProject || !editingProjectSubcategoryId || updateProjectSubcategoryMutation.isPending) return;
    setActionError("");
    if (structureProjectIsIsolated && !editingProjectSubcategoryName.trim()) {
      setActionError(t("projects.projectSubcategoryNameRequired", { defaultValue: "Project subcategory name is required" }));
      return;
    }
    const limitAmount = parseBudgetAmountInput(editingProjectSubcategoryLimit);
    if (!structureProjectIsIsolated && !editingProjectSubcategoryLimit) {
      setActionError(t("projects.projectSubcategoryLimitInvalid", { defaultValue: "Project subcategory limit must be greater than zero" }));
      return;
    }
    if (editingProjectSubcategoryLimit && (!Number.isFinite(limitAmount) || limitAmount <= 0)) {
      setActionError(t("projects.projectSubcategoryLimitInvalid", { defaultValue: "Project subcategory limit must be greater than zero" }));
      return;
    }
    if (!structureProjectIsIsolated && !editingProjectSubcategoryHeadroom?.subcategory) {
      setActionError(t("projects.overlaySubcategoryHeadroomLoading", { defaultValue: "Monthly subcategory headroom is still loading." }));
      return;
    }
    if (!structureProjectIsIsolated && editingProjectSubcategoryWouldOverbook) {
      setActionError(t("projects.overlayReservationOverbooked", { defaultValue: "Reservation exceeds available selected-month headroom." }));
      return;
    }
    try {
      const payload = structureProjectIsIsolated
        ? {
            name: editingProjectSubcategoryName.trim(),
            limit_amount: limitAmount,
            is_active: editingProjectSubcategoryIsActive === "true",
          }
        : {
            user_subcategory_id: Number(editingProjectSubcategoryUserSubcategoryId),
            limit_amount: limitAmount,
            budget_year: summaryTarget.year,
            budget_month: summaryTarget.month,
          };
      await updateProjectSubcategoryMutation.mutateAsync({
        projectId: structureProject.id,
        subcategoryId: editingProjectSubcategoryId,
        payload,
      });
      setEditingProjectSubcategoryId(null);
      setEditingProjectSubcategoryUserSubcategoryId("");
      setEditingProjectSubcategoryName("");
      setEditingProjectSubcategoryLimit("");
      setEditingProjectSubcategoryIsActive("true");
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleAddBudget() {
    if (isAddingBudget) return;
    setActionError("");
    const budgetMonthValue = `${addBudgetYear}-${String(addBudgetMonth).padStart(2, "0")}`;
    const parsedForm = budgetCreateFormSchema.safeParse({
      category: addCategory,
      monthly_limit: addLimit,
      budget_month_value: budgetMonthValue,
    });
    if (!parsedForm.success) {
      return setActionError(tZodError(parsedForm));
    }
    const [yearStr, monthStr] = parsedForm.data.budget_month_value.split("-");
    const budgetYear = Number(yearStr);
    const budgetMonth = Number(monthStr);
    try {
      await addBudgetMutation.mutateAsync({
        category: parsedForm.data.category,
        monthlyLimit: parsedForm.data.monthly_limit,
        budgetYear,
        budgetMonth,
      });
      setAddOpen(false);
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleUpdateBudget() {
    if (isUpdatingBudget) return;
    setActionError("");
    const parsedForm = budgetUpdateFormSchema.safeParse({
      monthly_limit: newLimit,
      category: selectedBudget?.category ?? "",
      budgetYear: selectedBudget?.budgetYear,
      budgetMonth: selectedBudget?.budgetMonth,
    });
    if (!parsedForm.success) {
      return setActionError(tZodError(parsedForm));
    }
    try {
      await updateBudgetMutation.mutateAsync({
        category: parsedForm.data.category,
        monthlyLimit: parsedForm.data.monthly_limit,
        budgetYear: parsedForm.data.budgetYear,
        budgetMonth: parsedForm.data.budgetMonth,
      });
      setUpdateOpen(false);
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleDeleteBudget() {
    if (isDeletingBudget) return;
    setActionError("");
    const parsedForm = budgetDeleteFormSchema.safeParse({
      category: selectedBudget?.category ?? "",
      budgetYear: selectedBudget?.budgetYear,
      budgetMonth: selectedBudget?.budgetMonth,
    });
    if (!parsedForm.success) {
      return setActionError(tZodError(parsedForm));
    }
    try {
      await deleteBudgetMutation.mutateAsync({
        category: parsedForm.data.category,
        budgetYear: parsedForm.data.budgetYear,
        budgetMonth: parsedForm.data.budgetMonth,
      });
      setDeleteOpen(false);
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleCreateProject() {
    if (isCreatingProject) return;
    setActionError("");
    if (!projectTitle.trim()) {
      setActionError(t("projects.titleRequired", { defaultValue: "Project title is required" }));
      return;
    }
    if (!projectStartDate) {
      setActionError(t("projects.startDateRequired", { defaultValue: "Project start date is required" }));
      return;
    }
    const targetEstimate = projectTargetEstimate ? Number(String(projectTargetEstimate).replace(/\s+/g, "")) : null;
    if (projectTargetEstimate && (!Number.isFinite(targetEstimate) || targetEstimate <= 0)) {
      setActionError(t("projects.targetEstimateInvalid", { defaultValue: "Target estimate must be greater than zero" }));
      return;
    }
    if (projectTargetEndDate && projectTargetEndDate < projectStartDate) {
      setActionError(t("projects.target_end_before_start", { defaultValue: "Target end date cannot be before start date" }));
      return;
    }
    if (projectIsIsolated === "true" && !projectIsolatedFundingValid) {
      setActionError(t("projects.walletFundingRequired", { defaultValue: "Choose at least one wallet allocation that fits available free money." }));
      return;
    }
    if (projectIsIsolated === "true" && !projectIsolatedStepThreeValid) {
      setActionError(t("projects.isolatedCategoryAllocationsInvalid", { defaultValue: "Allocate the isolated stash across categories without exceeding the derived stash." }));
      return;
    }
    if (projectIsIsolated === "false") {
      if (!projectOverlayStepThreeValid) {
        setActionError(t("projects.overlayWizardIncomplete", { defaultValue: "Complete the current-month allocations before creating the project." }));
        return;
      }
      try {
        await createOverlayProjectMutation.mutateAsync(buildOverlayProjectPayload({
          title: projectTitle.trim(),
          description: projectDescription,
          targetEstimate,
          startDate: projectStartDate,
          targetEndDate: projectTargetEndDate,
          budgetYear: currentYear,
          budgetMonth: currentMonth,
          categoryAllocationRows: projectCategoryAllocationRows,
          subcategoryReservations: projectSubcategoryReservations,
        }));
        setProjectOpen(false);
      } catch (e) {
        setActionError(getBudgetActionErrorMessage(e));
      }
      return;
    }
    try {
      await createProjectMutation.mutateAsync(buildIsolatedProjectPayload({
        title: projectTitle.trim(),
        description: projectDescription,
        walletAllocations: projectWalletAllocationPayload,
        categoryAllocationRows: projectIsolatedCategoryAllocationRows,
        subcategoryAllocations: projectIsolatedSubcategoryAllocations,
        startDate: projectStartDate,
        targetEndDate: projectTargetEndDate,
      }));
      setProjectOpen(false);
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleCreateSubcategory() {
    if (!subcategoryTargetBudget || createSubcategoryMutation.isPending) return;
    setActionError("");
    if (!subcategoryName.trim()) {
      setActionError(t("budgets.subcategoryNameRequired", { defaultValue: "Subcategory name is required" }));
      return;
    }
    const monthlyLimit = subcategoryLimit ? Number(String(subcategoryLimit).replace(/\s+/g, "")) : null;
    if (subcategoryLimit && (!Number.isFinite(monthlyLimit) || monthlyLimit <= 0)) {
      setActionError(t("budgets.subcategoryLimitInvalid", { defaultValue: "Subcategory limit must be greater than zero" }));
      return;
    }
    try {
      await createSubcategoryMutation.mutateAsync({
        budgetId: subcategoryTargetBudget.id,
        payload: {
          category: subcategoryTargetBudget.category,
          name: subcategoryName.trim(),
          existing_id: subcategoryExistingId || undefined,
          monthly_limit: monthlyLimit,
          is_active: subcategoryIsActive === "true",
        },
      });
      setSubcategoryName("");
      setSubcategoryExistingId(null);
      setSubcategoryComboboxOpen(false);
      setSubcategoryLimit("");
      setSubcategoryIsActive("true");
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleUpdateSubcategory() {
    if (!editingSubcategoryId || updateSubcategoryMutation.isPending) return;
    setActionError("");
    if (!editingSubcategoryName.trim()) {
      setActionError(t("budgets.subcategoryNameRequired", { defaultValue: "Subcategory name is required" }));
      return;
    }
    const monthlyLimit = editingSubcategoryLimit ? Number(String(editingSubcategoryLimit).replace(/\s+/g, "")) : null;
    if (editingSubcategoryLimit && (!Number.isFinite(monthlyLimit) || monthlyLimit <= 0)) {
      setActionError(t("budgets.subcategoryLimitInvalid", { defaultValue: "Subcategory limit must be greater than zero" }));
      return;
    }
    try {
      await updateSubcategoryMutation.mutateAsync({
        subcategoryId: editingSubcategoryId,
        budgetId: subcategoryTargetBudget?.id,
        payload: {
          name: editingSubcategoryName.trim(),
          monthly_limit: monthlyLimit,
          is_active: editingSubcategoryIsActive === "true",
        },
      });
      setEditingSubcategoryId(null);
      setEditingSubcategoryName("");
      setEditingSubcategoryLimit("");
      setEditingSubcategoryIsActive("true");
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleReallocateSubcategory() {
    if (!subcategoryTargetBudget || reallocateSubcategoryMutation.isPending) return;
    setActionError("");
    const amount = reallocationAmount ? Number(String(reallocationAmount).replace(/\s+/g, "")) : 0;
    if (!reallocationTargetId || !Number.isFinite(amount) || amount <= 0) {
      setActionError(t("budgets.subcategoryReallocationInvalid", { defaultValue: "Choose a target subcategory and a positive amount." }));
      return;
    }
    try {
      await reallocateSubcategoryMutation.mutateAsync({
        budgetId: subcategoryTargetBudget.id,
        payload: {
          from_subcategory_id: reallocationSourceId === "buffer" ? null : Number(reallocationSourceId),
          to_subcategory_id: Number(reallocationTargetId),
          amount,
        },
      });
      setReallocationTargetId("");
      setReallocationSourceId("buffer");
      setReallocationAmount("");
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  async function handleParentReallocate() {
    if (!parentReallocateSourceBudget || reallocateBudgetMutation.isPending) return;
    setActionError("");
    const amount = parentReallocateAmount ? Number(String(parentReallocateAmount).replace(/\s+/g, "")) : 0;
    if (!parentReallocateTargetCategory || !Number.isFinite(amount) || amount <= 0) {
      setActionError(t("budgets.parentReallocationInvalid", { defaultValue: "Choose a target category and a positive amount." }));
      return;
    }
    if (amount > parentReallocateSourceBudget.remaining) {
      setActionError(t("budgets.parentReallocationInsufficient", { defaultValue: "Amount exceeds remaining available funds." }));
      return;
    }
    try {
      await reallocateBudgetMutation.mutateAsync({
        fromCategory: parentReallocateSourceBudget.category,
        toCategory: parentReallocateTargetCategory,
        amount,
        budgetYear: parentReallocateSourceBudget.budgetYear,
        budgetMonth: parentReallocateSourceBudget.budgetMonth,
      });
      setParentReallocateOpen(false);
    } catch (e) {
      setActionError(getBudgetActionErrorMessage(e));
    }
  }

  const addBudgetFooter = (
    <>
      <Button variant="outline" onClick={() => setAddOpen(false)} disabled={isAddingBudget}>
        {t("common.cancel")}
      </Button>
      <Button
        onClick={handleAddBudget}
        disabled={!canSubmitAddBudget}
        className="relative min-w-[96px] disabled:pointer-events-auto disabled:cursor-not-allowed"
      >
        {isAddingBudget ? (
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

  const createProjectFooter = (
    <>
      {projectWizardStep > 1 ? (
        <Button variant="outline" onClick={handleProjectWizardBack} disabled={isCreatingProject}>
          {t("common.back", { defaultValue: "Back" })}
        </Button>
      ) : (
        <Button variant="outline" onClick={() => setProjectOpen(false)} disabled={isCreatingProject}>
          {t("common.cancel")}
        </Button>
      )}
      {projectWizardStep < projectMaxWizardStep ? (
        <Button
          onClick={handleProjectWizardNext}
          disabled={!canAdvanceProjectWizard}
          className="min-w-[120px] disabled:pointer-events-auto disabled:cursor-not-allowed"
        >
          {t("common.next", { defaultValue: "Next" })}
        </Button>
      ) : (
        <Button
          onClick={handleCreateProject}
          disabled={
            isCreatingProject ||
            !projectTitle.trim() ||
            !projectStartDate ||
            (isOverlayProjectDraft && !projectOverlayStepThreeValid) ||
            (!isOverlayProjectDraft && (!projectIsolatedFundingValid || !projectIsolatedStepThreeValid))
          }
          className="relative min-w-[120px] disabled:pointer-events-auto disabled:cursor-not-allowed"
        >
          {isCreatingProject ? (
            <>
              <span className="invisible">{t("projects.create", { defaultValue: "Create Project" })}</span>
              <span className="absolute inset-0 flex items-center justify-center">
                <span
                  aria-label="Loading"
                  className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                />
              </span>
            </>
          ) : (
            t("projects.create", { defaultValue: "Create Project" })
          )}
        </Button>
      )}
    </>
  );

  const updateBudgetFooter = (
    <>
      <Button variant="outline" onClick={() => setUpdateOpen(false)} disabled={isUpdatingBudget}>
        {t("common.cancel")}
      </Button>
      <Button
        onClick={handleUpdateBudget}
        disabled={!canSubmitUpdateBudget}
        className={`relative min-w-24 ${!canSubmitUpdateBudget ? "cursor-not-allowed opacity-60" : ""}`}
      >
        {isUpdatingBudget ? (
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

  const parentReallocateFooter = (
    <>
      <Button variant="outline" onClick={() => setParentReallocateOpen(false)} disabled={reallocateBudgetMutation.isPending}>
        {t("common.cancel")}
      </Button>
      <Button
        onClick={handleParentReallocate}
        disabled={reallocateBudgetMutation.isPending || !parentReallocateTargetCategory || !parentReallocateAmount}
        className="relative min-w-24 disabled:pointer-events-auto disabled:cursor-not-allowed"
      >
        {reallocateBudgetMutation.isPending ? (
          <>
            <span className="invisible">{t("budgets.reallocate", { defaultValue: "Reallocate" })}</span>
            <span className="absolute inset-0 flex items-center justify-center">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            </span>
          </>
        ) : (
          t("budgets.reallocate", { defaultValue: "Reallocate" })
        )}
      </Button>
    </>
  );

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="w-full px-page py-8 space-y-6">
        <PageHeader title={t("budgets.title")} description={t("budgets.subtitle")}>
          <div className="flex bg-muted p-1 rounded-md">
            <Button
              variant={viewMode === "monthly_plan" ? "secondary" : "ghost"}
              className="text-sm h-8 px-4"
              onClick={() => setViewMode("monthly_plan")}
            >
              {t("budgets.modeMonthlyPlan", { defaultValue: "Monthly Plan" })}
            </Button>
            <Button
              variant={viewMode === "taxonomy" ? "secondary" : "ghost"}
              className="text-sm h-8 px-4"
              onClick={() => setViewMode("taxonomy")}
            >
              {t("budgets.modeTaxonomy", { defaultValue: "Taxonomy Hub" })}
            </Button>
          </div>
          {viewMode === "monthly_plan" && (
            <>
              <Button variant="outline" onClick={() => setShowHistory((v) => !v)}>
                {showHistory ? t("budgets.hideHistory") : t("budgets.showHistory")}
              </Button>
              <Button variant="outline" onClick={openProject}>
                <BriefcaseBusiness className="mr-2 h-4 w-4" /> {t("projects.create", { defaultValue: "Create Project" })}
              </Button>
              <Button variant="outline" onClick={() => setShowSurvivalDialog(true)}>
                <Shield className="mr-2 h-4 w-4" /> {t("budgets.configureSurvival", { defaultValue: "Survival Mode" })}
              </Button>
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90" onClick={openAdd}>
                <Plus className="mr-2 h-4 w-4" /> {t("budgets.addBudget")}
              </Button>
            </>
          )}
        </PageHeader>

        {viewMode === "taxonomy" ? (
          <TaxonomyHub />
        ) : (
          <>
            {!loading && !error && (
              <Card className="shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{t("budgets.filtersTitle")}</CardTitle>
                  <CardDescription>{t("budgets.filtersDesc")}</CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                <Select value={filterCategory} onValueChange={setFilterCategory}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="all">{t("budgets.filterCategoryAll")}</SelectItem>
                    {orderedCategoryOptions.map((c) => (
                      <SelectItem key={c} value={c}>
                        <span className="flex items-center gap-2">
                          {(() => {
                            const CategoryIcon = categoryIconMap[c] || Circle;
                            return <CategoryIcon className="h-4 w-4 text-muted-foreground" />;
                          })()}
                          <span>{tCategory(c)}</span>
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="all">{t("budgets.filterStatusAll")}</SelectItem>
                    <SelectItem value="healthy">{t("budgets.status.onTrack")}</SelectItem>
                    <SelectItem value="warning">{t("budgets.status.closeToLimit")}</SelectItem>
                    <SelectItem value="highRisk">{t("budgets.status.highRisk")}</SelectItem>
                    <SelectItem value="danger">{t("budgets.status.overBudget")}</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterMonth} onValueChange={setFilterMonth} disabled={!showHistory}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="all">{t("budgets.filterMonthAll")}</SelectItem>
                    {monthFilterOptions.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass} position="popper" side="bottom">
                    <SelectItem value="newest">{t("budgets.sort.newest")}</SelectItem>
                    <SelectItem value="oldest">{t("budgets.sort.oldest")}</SelectItem>
                    <SelectItem value="percentDesc">{t("budgets.sort.percentDesc")}</SelectItem>
                    <SelectItem value="percentAsc">{t("budgets.sort.percentAsc")}</SelectItem>
                    <SelectItem value="remainingDesc">{t("budgets.sort.remainingDesc")}</SelectItem>
                    <SelectItem value="remainingAsc">{t("budgets.sort.remainingAsc")}</SelectItem>
                    <SelectItem value="limitDesc">{t("budgets.sort.limitDesc")}</SelectItem>
                    <SelectItem value="limitAsc">{t("budgets.sort.limitAsc")}</SelectItem>
                    <SelectItem value="category">{t("budgets.sort.category")}</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  onClick={resetBudgetFilters}
                  className="md:col-span-2 xl:col-span-1"
                >
                  {t("budgets.resetFilters")}
                </Button>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-border bg-muted/30 px-3 py-1 text-[11px] font-medium text-muted-foreground">
                  {showHistory
                    ? t("budgets.historyModeChip", { defaultValue: "History mode on" })
                    : t("budgets.historyModeChipOff", { defaultValue: "Current month mode" })}
                </span>
                {filterCategory !== "all" ? (
                  <span className="rounded-full border border-border bg-background px-3 py-1 text-[11px] font-medium">
                    {t("budgets.filterCategoryChip", {
                      defaultValue: "Category: {{value}}",
                      value: tCategory(filterCategory),
                    })}
                  </span>
                ) : null}
                {filterStatus !== "all" ? (
                  <span className="rounded-full border border-border bg-background px-3 py-1 text-[11px] font-medium">
                    {t("budgets.filterStatusChip", {
                      defaultValue: "Status: {{value}}",
                      value:
                        filterStatus === "healthy"
                          ? t("budgets.status.onTrack")
                          : filterStatus === "warning"
                            ? t("budgets.status.closeToLimit")
                            : filterStatus === "highRisk"
                              ? t("budgets.status.highRisk")
                              : t("budgets.status.overBudget"),
                    })}
                  </span>
                ) : null}
                {showHistory && filterMonth !== "all" ? (
                  <span className="rounded-full border border-border bg-background px-3 py-1 text-[11px] font-medium">
                    {t("budgets.filterMonthChip", {
                      defaultValue: "Month: {{value}}",
                      value: monthFilterOptions.find((m) => m.value === filterMonth)?.label || filterMonth,
                    })}
                  </span>
                ) : null}
                {sortBy !== "newest" ? (
                  <span className="rounded-full border border-border bg-background px-3 py-1 text-[11px] font-medium">
                    {t("budgets.sortChip", { defaultValue: "Sorted view" })}
                  </span>
                ) : null}
              </div>
            </CardContent>
          </Card>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}
        {loading && (
          <div className="flex min-h-30 items-center justify-center">
            <LoadingSpinner className="h-8 w-8" />
          </div>
        )}

        {!loading && !error && (
          <>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                        {t("budgets.cashBacking", { defaultValue: "Cash backing" })}
                      </p>
                      <div className="mt-2">
                        <CurrencyAmount value={monthSummary?.cash_backing_total || 0} format="display" className="text-xl font-bold tracking-tight" />
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 flex">
                    <Button variant="link" className="h-auto p-0 text-sm font-medium text-primary" onClick={() => setShowCashBackingDetails(true)}>
                      {t("budgets.seeDetails", { defaultValue: "See details" })}
                    </Button>
                  </div>
                </CardContent>
              </Card>
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                        {t("budgets.expectedIncome", { defaultValue: "Expected inflows" })}
                      </p>
                      <div className="mt-2">
                        <CurrencyAmount value={monthSummary?.expected_income_remaining || 0} format="display" className="text-xl font-bold tracking-tight text-sky-600 dark:text-sky-400" />
                      </div>
                    </div>
                    <Button
                      type="button"
                      size="icon"
                      variant="outline"
                      className="h-8 w-8 shrink-0"
                      onClick={openExpectedIncomeDialog}
                      aria-label={t("budgets.addExpectedIncome", { defaultValue: "Add expected inflow" })}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {(monthSummary?.expected_income_items?.length || 0) > 0
                      ? t("budgets.expectedIncomeCount", {
                          defaultValue: "{{count}} scheduled inflows for this month.",
                          count: monthSummary.expected_income_items.length,
                        })
                      : t("budgets.expectedIncomeHint", {
                          defaultValue: "Expected inflows that can support this month's plan.",
                        })}
                  </p>
                </CardContent>
              </Card>
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                    {t("budgets.monthlyBudgetTotal", { defaultValue: "Monthly budget total" })}
                  </p>
                  <div className="mt-2">
                    <CurrencyAmount value={monthSummary?.monthly_effective_limit_total ?? planningSummary.planned} format="display" className="text-xl font-bold tracking-tight" />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("budgets.monthlyBudgetTotalHint", {
                      defaultValue: "Total monthly spending permission for this month.",
                    })}
                  </p>
                </CardContent>
              </Card>
              <Card className="shadow-sm">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                        {monthSummary?.backing_shortfall > 0 
                          ? t("budgets.backingShortfall", { defaultValue: "Backing shortfall" })
                          : t("budgets.planBackingRemaining", { defaultValue: "Plan backing remaining" })}
                      </p>
                      <div className="mt-2">
                        <CurrencyAmount
                          value={monthSummary?.backing_shortfall > 0 ? monthSummary.backing_shortfall : (monthSummary?.plan_backing_remaining || 0)}
                          format="display"
                          className={cn(
                            "text-xl font-bold tracking-tight",
                            monthSummary?.backing_shortfall > 0
                              ? "text-red-600 dark:text-red-400"
                              : "text-emerald-600 dark:text-emerald-400"
                          )}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center gap-2 border-t border-border/50 pt-3">
                    <div className={cn("h-2 w-2 rounded-full", planStatusMeta.tone.replace('text-', 'bg-').replace('dark:text-', 'dark:bg-'))} />
                    <p className="text-sm font-medium text-muted-foreground">
                      {planStatusMeta.label}
                    </p>
                  </div>
                </CardContent>
              </Card>

                {monthSummary?.borrowing_survival?.enabled && (
                  <Card className="shadow-sm border-purple-500/30 bg-purple-500/5">
                    <CardContent className="p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-ui-micro uppercase tracking-widest text-purple-700 dark:text-purple-400">
                            {t("budgets.borrowingSurvival", { defaultValue: "Borrowing Survival" })}
                          </p>
                          <div className="mt-2">
                            <CurrencyAmount value={monthSummary.borrowing_survival.borrowed_usage} format="display" className="text-xl font-bold tracking-tight text-purple-700 dark:text-purple-400" />
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">
                            {t("budgets.survivalCap", { defaultValue: "Cap" })}
                          </p>
                          <div className="mt-2">
                            <CurrencyAmount value={monthSummary.borrowing_survival.monthly_cap} format="display" className="text-sm font-medium tracking-tight text-muted-foreground" />
                          </div>
                        </div>
                      </div>
                      
                      <div className="mt-3 flex items-center justify-between text-sm">
                        <span className="text-purple-700/80 dark:text-purple-400/80">
                          {monthSummary.borrowing_survival.exceeded_amount > 0 
                            ? t("budgets.survivalExceeded", { defaultValue: "Cap exceeded by" })
                            : t("budgets.survivalRemaining", { defaultValue: "Remaining cap" })
                          }
                        </span>
                        <span className="font-medium text-purple-700 dark:text-purple-400">
                          {monthSummary.borrowing_survival.exceeded_amount > 0 
                            ? <CurrencyAmount value={monthSummary.borrowing_survival.exceeded_amount} />
                            : <CurrencyAmount value={monthSummary.borrowing_survival.remaining_cap} />
                          }
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

            {monthSummary?.plan_status === "waiting_on_income" || monthSummary?.plan_status === "over_planned" ? (
              <Card
                className={cn(
                  "border shadow-sm",
                  monthSummary.plan_status === "over_planned"
                    ? "border-red-500/30 bg-red-500/5"
                    : "border-sky-500/30 bg-sky-500/5",
                )}
              >
                <CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
                  <div className="space-y-1">
                    <p className={cn("text-sm font-semibold", planStatusMeta.tone)}>{planStatusMeta.label}</p>
                    <p className="text-sm text-muted-foreground">
                      {monthSummary.plan_status === "over_planned"
                        ? t("budgets.planNeedsRepairDesc", {
                            defaultValue: "This active plan exceeds valid backing by {{shortfall}}. Reduce limits or add expected earned income before increasing budgets.",
                            shortfall: formatUzs(Number(monthSummary.backing_shortfall || 0)),
                          })
                        : t("budgets.waitingOnIncomeDesc", {
                            defaultValue: "This plan is short on cash by {{cashGap}}, but expected income covers it.",
                            cashGap: formatUzs(Number(monthSummary.cash_gap_to_budget_total || 0)),
                          })}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" onClick={openExpectedIncomeDialog}>
                      <Plus className="mr-2 h-4 w-4" />
                      {t("budgets.addExpectedIncome", { defaultValue: "Add expected inflow" })}
                    </Button>
                    {monthSummary.plan_status === "over_planned" ? (
                      <Button variant="secondary" onClick={() => setSortBy("limitDesc")}>
                        {t("budgets.reviewLimits", { defaultValue: "Review limits" })}
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            ) : null}

            <Card className="overflow-hidden border border-border/70 bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80">
              <CardHeader className="border-b border-border/60 bg-gradient-to-br from-muted/40 via-background to-background">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
                  <div className="space-y-1">
                    <CardTitle>{t("budgets.timeline.title", { defaultValue: "Monthly Timeline" })}</CardTitle>
                    <CardDescription>
                      {t("budgets.timeline.desc", {
                        defaultValue: "Upcoming events and expected cash flows for this month.",
                      })}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 sm:p-6 bg-slate-50/50">
                <BudgetTimeline budgetYear={summaryTarget.year} budgetMonth={summaryTarget.month} />
              </CardContent>
            </Card>

            <Card className="overflow-hidden border border-border/70 bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80">
              <CardHeader className="border-b border-border/60 bg-gradient-to-br from-muted/40 via-background to-background">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
                  <div className="space-y-1">
                    <CardTitle>{t("projects.sectionTitle", { defaultValue: "Projects" })}</CardTitle>
                    <CardDescription>
                      {t("projects.sectionDesc", {
                        defaultValue: "Purpose-based spending containers that live alongside monthly category budgets.",
                      })}
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full border border-border bg-background px-3 py-1">
                      {t("projects.countChip", {
                        defaultValue: "{{count}} projects",
                        count: projects.length,
                      })}
                    </span>
                    <span className="rounded-full border border-border bg-background px-3 py-1">
                      {t("projects.createdFromBudgets", { defaultValue: "Create here, spend from Expenses" })}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 sm:p-6">
                {projectsQuery.isLoading ? (
                  <div className="flex min-h-24 items-center justify-center">
                    <LoadingSpinner className="h-6 w-6" />
                  </div>
                ) : projects.length === 0 ? (
                  <EmptyState
                    title={t("projects.emptyTitle", { defaultValue: "No projects yet" })}
                    description={t("projects.emptyDesc", {
                      defaultValue: "Create a project here when you need mission-based spending outside or alongside monthly budgets.",
                    })}
                    className="my-2"
                  />
                ) : (
                  <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                    {projects.map((project) => {
                      const projectIsIsolated = isIsolatedProject(project);
                      const overlayDetails = project.overlay || {};
                      const isolatedDetails = project.isolated || {};
                      const totalLimit = Number(isolatedDetails.funding_limit ?? project.total_limit ?? 0);
                      const spent = Number(project.spent || 0);
                      const remaining = Number(project.remaining || Math.max(0, totalLimit - spent));
                      const targetEstimate = Number(overlayDetails.target_estimate ?? project.target_estimate ?? 0);
                      const selectedMonthReserved = Number(overlayDetails.selected_month_reserved_amount ?? project.selected_month_reserved_amount ?? 0);
                      const totalReservedScope = Number(overlayDetails.total_reserved_scope ?? project.total_reserved_scope ?? 0);
                      const selectedMonthSpent = (project.category_breakdown || []).reduce(
                        (sum, item) => sum + Number(item.spent || 0),
                        0,
                      );
                      const selectedMonthRemaining = selectedMonthReserved - selectedMonthSpent;
                      const overlayReservedPercent = selectedMonthReserved > 0
                        ? Math.min(100, Math.round((selectedMonthSpent / selectedMonthReserved) * 100))
                        : 0;
                      const releasedFunding = Number(isolatedDetails.released_funding ?? project.released_funding ?? 0);
                      const remainingFunding = Number(isolatedDetails.remaining_funding ?? project.remaining_funding ?? 0);
                      const isGoalFundedIsolated = Boolean(projectIsIsolated && project.origin_goal_id);
                      const hasFundingLayer = isGoalFundedIsolated || releasedFunding > 0 || remainingFunding > 0;
                      const fundingGap = Math.max(0, totalLimit - releasedFunding);
                      const limitPercent = totalLimit > 0 ? Math.min(100, Math.round((spent / totalLimit) * 100)) : 0;
                      const fundingPercent = releasedFunding > 0 ? Math.min(100, Math.round((spent / releasedFunding) * 100)) : 0;

                      const currentMonthCategoryRows = (project.category_breakdown || []).filter(
                        (row) =>
                          Number(row.budget_year) === Number(summaryTarget.year) &&
                          Number(row.budget_month) === Number(summaryTarget.month) &&
                          Number(row.limit_amount || 0) > 0
                      );
                      const currentMonthCategories = currentMonthCategoryRows.map((c) => tCategory(c.category)).join(", ");
                      const projectStatus = project.status || "ACTIVE";
                      const projectIsActive = projectStatus === "ACTIVE";
                      const projectIsStopped = projectStatus === "STOPPED";
                      const projectIsCompleted = projectStatus === "COMPLETED";
                      const projectIsArchived = projectStatus === "ARCHIVED";
                      const projectCanModify = !projectIsCompleted && !projectIsArchived;
                      const projectCanComplete = projectIsActive || projectIsStopped;
                      const projectIsOverdue = Boolean(project.target_end_date && project.target_end_date < todayIso);
                      const projectReadyToWrap = projectCanComplete && projectIsOverdue;

                      if (projectIsIsolated) {
                        return (
                          <IsolatedProjectCard
                            key={project.id}
                            project={project}
                            onEditProperties={setEditProjectModalProject}
                            onManageStructure={openProjectStructure}
                            onReopen={(projectId) => navigate(`/projects/${projectId}`)}
                            todayIso={todayIso}
                            disabled={isProjectLifecyclePending}
                          />
                        );
                      }

                      return (
                        <Card key={project.id} className="border border-border/70 bg-background/70 shadow-sm">
                          <CardHeader className="space-y-3 pb-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <CardTitle className="text-lg">
                                  <span className="block truncate">{project.title}</span>
                                </CardTitle>
                                <CardDescription className="mt-1">
                                  {t("projects.overlayHelp", { defaultValue: "Overlay projects still count against monthly category budgets." })}
                                </CardDescription>
                              </div>
                              <div className="flex shrink-0 items-start gap-2">
                                <div className="flex flex-col items-end gap-2">
                                  <span className="rounded-full border border-border/60 bg-background px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                                    {getProjectStatusLabel(projectStatus, t)}
                                  </span>
                                  <span className="rounded-full border border-border/60 bg-muted/30 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-foreground">
                                    {t("projects.overlay", { defaultValue: "Overlay" })}
                                  </span>
                                </div>
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="icon"
                                      className="h-8 w-8 rounded-full"
                                      aria-label={t("common.actions", { defaultValue: "Actions" })}
                                    >
                                      <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end" className="w-56">
                                    {projectCanModify ? (
                                      <DropdownMenuItem onSelect={() => setEditProjectModalProject(project)}>
                                        <Pencil className="mr-2 h-4 w-4" />
                                        {t("common.edit", { defaultValue: "Edit properties" })}
                                      </DropdownMenuItem>
                                    ) : null}

                                    {projectCanModify ? (
                                      <DropdownMenuItem
                                        onSelect={() => openProjectStructure(project)}
                                        disabled={isProjectLifecyclePending}
                                      >
                                        <BriefcaseBusiness className="mr-2 h-4 w-4" />
                                        {projectIsIsolated
                                          ? t("projects.manageStructure", { defaultValue: "Manage structure" })
                                          : t("projects.adjustAllocation", { defaultValue: "Adjust allocation" })}
                                      </DropdownMenuItem>
                                    ) : null}

                                    {!projectIsIsolated && (projectIsActive || projectIsStopped || projectCanComplete || projectIsArchived) ? (
                                      <DropdownMenuItem
                                        onSelect={() => navigate(`/projects/${project.id}`)}
                                      >
                                        <CalendarClock className="mr-2 h-4 w-4" />
                                        {t("projects.manageProject", { defaultValue: "Manage project" })}
                                      </DropdownMenuItem>
                                    ) : null}

                                    {projectCanModify || projectIsArchived ? <DropdownMenuSeparator /> : null}
                                    <DropdownMenuItem
                                      variant="destructive"
                                      onSelect={() => navigate(`/projects/${project.id}`)}
                                    >
                                      <Trash2 className="mr-2 h-4 w-4" />
                                      {t("common.delete", { defaultValue: "Delete" })}
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            {isGoalFundedIsolated ? (
                              <div className="space-y-4">
                                <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4">
                                  <div className="flex items-center justify-between gap-3">
                                    <div>
                                      <p className="text-[10px] uppercase tracking-[0.16em] text-primary/80">
                                        {t("projects.availableFundingNow", { defaultValue: "Available funding now" })}
                                      </p>
                                      <CurrencyAmount value={remainingFunding} format="display" className="mt-1 text-2xl font-bold tracking-tight text-primary" />
                                    </div>
                                    <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-primary">
                                      {t("projects.goalFunded", { defaultValue: "Goal-funded" })}
                                    </span>
                                  </div>
                                  <p className="mt-2 text-sm text-muted-foreground">
                                    {t("projects.availableFundingNowHint", {
                                      defaultValue: "This is the released goal money the project can still spend right now.",
                                    })}
                                  </p>
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2">
                                  <div className="rounded-xl border border-border/60 bg-muted/15 p-3">
                                    <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                      {t("projects.releasedFunding", { defaultValue: "Released funding" })}
                                    </p>
                                    <CurrencyAmount value={releasedFunding} format="compact" className="mt-1 text-base font-semibold" />
                                  </div>
                                  <div className="rounded-xl border border-border/60 bg-muted/15 p-3">
                                    <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                      {t("projects.spentFromFunding", { defaultValue: "Spent from funding" })}
                                    </p>
                                    <CurrencyAmount value={spent} format="compact" className="mt-1 text-base font-semibold" />
                                  </div>
                                </div>

                                <div className="space-y-1">
                                  <div className="flex items-baseline justify-between gap-3">
                                    <span className="text-sm font-medium text-foreground">
                                      {t("projects.fundingMeter", { defaultValue: "Funding meter" })}
                                    </span>
                                    <span className="text-sm text-muted-foreground">
                                      {t("budgets.usedOf", { spent: formatCompactUzs(spent), limit: formatCompactUzs(releasedFunding) })} UZS
                                    </span>
                                  </div>
                                  {releasedFunding > 0 ? (
                                    <Progress
                                      value={fundingPercent}
                                      indicatorClassName="bg-primary rounded-full"
                                      trackClassName="bg-primary/15 rounded-full"
                                      className="h-2.5 rounded-full"
                                    />
                                  ) : null}
                                </div>

                                <div className="grid gap-3 sm:grid-cols-2">
                                  <div className="rounded-xl border border-border/60 bg-muted/15 p-3">
                                    <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                      {t("projects.plannedTotal", { defaultValue: "Planned total" })}
                                    </p>
                                    <CurrencyAmount value={totalLimit} format="compact" className="mt-1 text-base font-semibold" />
                                  </div>
                                  <div className="rounded-xl border border-border/60 bg-muted/15 p-3">
                                    <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                      {t("projects.fundingGap", { defaultValue: "Funding gap" })}
                                    </p>
                                    <CurrencyAmount value={fundingGap} format="compact" className="mt-1 text-base font-semibold" />
                                  </div>
                                </div>

                                <div className="space-y-1">
                                  <div className="flex items-baseline justify-between gap-3">
                                    <span className="text-sm font-medium text-foreground">
                                      {t("projects.planMeter", { defaultValue: "Plan meter" })}
                                    </span>
                                    <span className="text-sm text-muted-foreground">
                                      {totalLimit > 0
                                        ? `${t("budgets.usedOf", { spent: formatCompactUzs(spent), limit: formatCompactUzs(totalLimit) })} UZS`
                                        : t("projects.noTotalLimit", { defaultValue: "No total limit" })}
                                    </span>
                                  </div>
                                  <p className="text-sm text-muted-foreground">
                                    {t("budgets.remainingLabel", { defaultValue: "Remaining" })}: {formatCompactUzs(remaining)}
                                  </p>
                                  {totalLimit > 0 ? (
                                    <Progress
                                      value={limitPercent}
                                      indicatorClassName="bg-emerald-500 rounded-full"
                                      trackClassName="bg-emerald-500/15 rounded-full"
                                      className="h-2.5 rounded-full"
                                    />
                                  ) : null}
                                </div>
                              </div>
                            ) : !projectIsIsolated ? (
                              <div className="space-y-4">
                                {selectedMonthReserved > 0 ? (
                                  <div className="space-y-2">
                                    <div className="flex items-baseline justify-between gap-3">
                                      <span className="text-sm font-medium text-foreground">
                                        {t("projects.thisMonthAllocation", { defaultValue: "This month's allocation" })}
                                      </span>
                                      <span className="text-sm text-muted-foreground">
                                        {t("budgets.usedOf", { spent: formatCompactUzs(selectedMonthSpent), limit: formatCompactUzs(selectedMonthReserved) })} UZS
                                      </span>
                                    </div>
                                    <p className="text-sm font-medium">
                                      {selectedMonthRemaining >= 0 ? (
                                        <span className="text-emerald-600 dark:text-emerald-400">
                                          {formatCompactUzs(selectedMonthRemaining)} {t("projects.leftThisMonth", { defaultValue: "left this month" })}
                                        </span>
                                      ) : (
                                        <span className="text-red-600 dark:text-red-400">
                                          {formatCompactUzs(Math.abs(selectedMonthRemaining))} {t("projects.overThisMonth", { defaultValue: "over this month" })}
                                        </span>
                                      )}
                                    </p>
                                    <Progress
                                      value={overlayReservedPercent}
                                      indicatorClassName={selectedMonthRemaining >= 0 ? "bg-yellow-500 rounded-full" : "bg-red-500 rounded-full"}
                                      trackClassName={selectedMonthRemaining >= 0 ? "bg-yellow-500/15 rounded-full" : "bg-red-500/15 rounded-full"}
                                      className="h-2.5 rounded-full"
                                    />
                                  </div>
                                ) : (
                                  <div className="rounded-xl border border-dashed border-border/60 bg-muted/5 p-4 text-center">
                                    <p className="text-sm font-medium text-foreground">
                                      {t("projects.noMonthAllocation", { defaultValue: "No allocation this month" })}
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                      {t("projects.noAllocationDesc", { defaultValue: "This project has no spending slice for the selected month." })}
                                    </p>
                                  </div>
                                )}

                                {currentMonthCategories && (
                                  <div className="pt-2">
                                    <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                      {t("projects.mainPressure", { defaultValue: "Main pressure" })}
                                    </p>
                                    <p className="mt-1 text-sm font-medium text-foreground">
                                      {currentMonthCategories}
                                    </p>
                                  </div>
                                )}
                                
                                <div className="border-t border-border/50 pt-3 flex items-center justify-between text-xs text-muted-foreground">
                                  <span>{t("projects.totalSpent", { defaultValue: "Total spent" })}: {formatCompactUzs(spent)}</span>
                                  {targetEstimate > 0 && (
                                    <span>{t("projects.expectedCost", { defaultValue: "Expected cost" })}: {formatCompactUzs(targetEstimate)}</span>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <div className="space-y-1">
                                <div className="flex items-baseline justify-between gap-3">
                                  <CurrencyAmount value={spent} format="display" className="text-xl font-bold tracking-tight" />
                                  <span className="text-sm text-muted-foreground">
                                    {totalLimit > 0
                                      ? `${t("budgets.usedOf", { spent: formatCompactUzs(spent), limit: formatCompactUzs(totalLimit) })} UZS`
                                      : t("projects.noTotalLimit", { defaultValue: "No total limit" })}
                                  </span>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {t("budgets.remainingLabel", { defaultValue: "Remaining" })}: {formatCompactUzs(remaining)}
                                </p>
                                {totalLimit > 0 ? (
                                  <Progress
                                    value={limitPercent}
                                    indicatorClassName="bg-primary rounded-full"
                                    trackClassName="bg-primary/15 rounded-full"
                                    className="h-2.5 rounded-full"
                                  />
                                ) : null}
                              </div>
                            )}

                            {hasFundingLayer && !isGoalFundedIsolated ? (
                              <div className="grid gap-3 sm:grid-cols-2">
                                <div className="rounded-xl border border-border/60 bg-muted/15 p-3">
                                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                    {t("projects.releasedFunding", { defaultValue: "Released funding" })}
                                  </p>
                                  <CurrencyAmount value={releasedFunding} format="compact" className="mt-1 text-base font-semibold" />
                                </div>
                                <div className="rounded-xl border border-border/60 bg-muted/15 p-3">
                                  <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                    {t("projects.remainingFunding", { defaultValue: "Remaining funding" })}
                                  </p>
                                  <CurrencyAmount value={remainingFunding} format="compact" className="mt-1 text-base font-semibold" />
                                </div>
                              </div>
                            ) : null}

                            {projectIsIsolated && (
                              <>
                                <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                                  {project.start_date ? (
                                    <span className="rounded-full border border-border/60 bg-background px-2.5 py-1">
                                      {t("projects.startDate", { defaultValue: "Start date" })}: {project.start_date}
                                    </span>
                                  ) : null}
                                  {project.target_end_date ? (
                                    <span className="rounded-full border border-border/60 bg-background px-2.5 py-1">
                                      {t("projects.targetEndDate", { defaultValue: "Target end date" })}: {project.target_end_date}
                                    </span>
                                  ) : null}
                                  {Array.isArray(project.category_limits) && project.category_limits.length > 0 ? (
                                    <span className="rounded-full border border-border/60 bg-background px-2.5 py-1">
                                      {t("projects.categoryLimitsChip", {
                                        defaultValue: "{{count}} category limits",
                                        count: project.category_limits.length,
                                      })}
                                    </span>
                                  ) : null}
                                </div>

                                <div className="grid gap-2 sm:grid-cols-2">
                                  <div className="rounded-xl border border-border/60 bg-muted/15 p-3">
                                    <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                                      {t("projects.structureSignal", { defaultValue: "Structure" })}
                                    </p>
                                    <p className="mt-1 text-sm font-semibold">
                                      {t("projects.structureCounts", {
                                        defaultValue: "{{categories}} categories · {{subcategories}} subcategories",
                                        categories: project.category_breakdown?.length || 0,
                                        subcategories: (project.category_breakdown || []).reduce((sum, item) => sum + (item.subcategories?.length || 0), 0),
                                      })}
                                    </p>
                                  </div>
                                  <Button
                                    variant="outline"
                                    className="h-full min-h-16 rounded-xl"
                                    onClick={() => openProjectStructure(project)}
                                  >
                                    <BriefcaseBusiness className="mr-2 h-4 w-4" />
                                    {t("projects.manageStructure", { defaultValue: "Manage structure" })}
                                  </Button>
                                </div>
                              </>
                            )}

                            {!projectIsIsolated && projectReadyToWrap ? (
                              <div className="rounded-xl border border-amber-400/40 bg-amber-500/10 p-3">
                                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                                  <div className="min-w-0">
                                    <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">
                                      {t("projects.readyToWrap", { defaultValue: "Ready to wrap up" })}
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                      {t("projects.readyToWrapDesc", { defaultValue: "The target date has passed. Finish the project when late receipts are done." })}
                                    </p>
                                  </div>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    className="rounded-xl"
                                    onClick={() => openProjectLifecycleDialog(project, PROJECT_LIFECYCLE_ACTIONS.COMPLETE)}
                                    disabled={isProjectLifecyclePending}
                                  >
                                    <CalendarClock className="mr-2 h-4 w-4" />
                                    {t("projects.wrapUpProject", { defaultValue: "Wrap up project" })}
                                  </Button>
                                </div>
                              </div>
                            ) : null}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="overflow-hidden border border-border/70 bg-card/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/80">
              <CardHeader className="border-b border-border/60 bg-gradient-to-br from-muted/50 via-background to-background">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
                  <div className="space-y-1">
                    <CardTitle>{t("budgets.workspaceTitle", { defaultValue: "Planning workspace" })}</CardTitle>
                    <CardDescription>
                      {t("budgets.workspaceDesc", {
                        defaultValue: "Budget cards stay lightweight here. Use View Expenses for spending, and Details for planning depth.",
                      })}
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full border border-border bg-background px-3 py-1">
                      {showHistory
                        ? t("budgets.workspaceSignal.history", { defaultValue: "Historical mode" })
                        : t("budgets.workspaceSignal.current", { defaultValue: "Current month" })}
                    </span>
                    <span className="rounded-full border border-border bg-background px-3 py-1">
                      {t("budgets.workspaceSignal.filters", {
                        defaultValue: "{{count}} filters",
                        count: activePlanningFilterCount,
                      })}
                    </span>
                    <span className="rounded-full border border-border bg-background px-3 py-1">
                      {t("budgets.workspaceSignal.available", { defaultValue: "Budget room" })}
                    </span>
                    <span className="rounded-full border border-border bg-background px-3 py-1">
                      {t("budgets.workspaceSignal.details", { defaultValue: "Details for depth" })}
                    </span>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 sm:p-6">
                <div className="grid gap-6 grid-cols-1 md:grid-cols-2 2xl:grid-cols-3">
            {filteredBudgets.map((b) => {
              const percent = b.percent;
              const progressStatus = b.progressStatus;
              const progressTrackClass =
                progressStatus === "danger"
                  ? "bg-destructive/20 rounded-full"
                  : progressStatus === "highRisk"
                    ? "bg-orange-500/20 dark:bg-orange-400/20 rounded-full"
                    : progressStatus === "warning"
                      ? "bg-yellow-500/20 dark:bg-yellow-400/20 rounded-full"
                      : "bg-primary/20 rounded-full";
              const progressIndicatorClass =
                progressStatus === "danger"
                  ? "bg-destructive shadow-[0_0_10px_rgba(239,68,68,0.45)] rounded-full duration-700 ease-out"
                  : progressStatus === "highRisk"
                    ? "bg-orange-500 dark:bg-orange-400 shadow-[0_0_10px_rgba(249,115,22,0.35)] dark:shadow-[0_0_10px_rgba(251,146,60,0.35)] rounded-full duration-700 ease-out"
                    : progressStatus === "warning"
                      ? "bg-yellow-500 dark:bg-yellow-400 shadow-[0_0_10px_rgba(234,179,8,0.35)] dark:shadow-[0_0_10px_rgba(250,204,21,0.35)] rounded-full duration-700 ease-out"
                      : "bg-primary shadow-[0_0_10px_rgba(34,197,94,0.35)] rounded-full duration-700 ease-out";
              const statusBadgeClass =
                progressStatus === "danger"
                  ? "border border-destructive/30 bg-destructive/15 text-destructive dark:text-red-400"
                  : progressStatus === "highRisk"
                    ? "border border-orange-500/35 bg-orange-500/15 text-orange-700 dark:text-orange-400"
                    : progressStatus === "warning"
                      ? "border border-yellow-500/35 bg-yellow-500/15 text-yellow-700 dark:text-yellow-400"
                      : "border border-primary/35 bg-primary/15 text-primary dark:text-primary";
              const statusLabel =
                progressStatus === "danger"
                  ? t("budgets.status.overBudget")
                  : progressStatus === "highRisk"
                    ? t("budgets.status.highRisk")
                    : progressStatus === "warning"
                      ? t("budgets.status.closeToLimit")
                      : t("budgets.status.onTrack");
              const deltaAmount = Math.max(0, b.spent - b.effectiveLimit);
              const useCompactAmounts = Math.max(b.spent, b.effectiveLimit) >= 100_000_000;
              const spentLabel = useCompactAmounts ? formatCompactUzs(b.spent) : formatUzs(b.spent);
              const limitLabel = useCompactAmounts ? formatCompactUzs(b.effectiveLimit) : formatUzs(b.effectiveLimit);
              const remainingLabel = useCompactAmounts ? formatCompactUzs(b.remaining) : formatUzs(b.remaining);
              const spentFullLabel = formatUzs(b.spent);
              const limitFullLabel = formatUzs(b.effectiveLimit);
              const usedOfLabel = t("budgets.usedOf", { spent: spentLabel, limit: limitLabel });
              const floorData = monthSummary?.category_floors?.find(f => f.category === b.category);
              const hasFloorPressure = floorData && floorData.warning_gap > 0;
              return (
                <Card
                  key={b.id}
                  className={`mobile-stat-card w-full mx-auto group shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md active:scale-[0.98] active:-translate-y-0 active:shadow-sm focus-within:shadow-md ${b.isCurrentMonth ? "opacity-100" : "opacity-65 hover:opacity-100"}`}
                >
                  <CardHeader className="space-y-3 pt-4 pb-4 sm:pt-6 sm:pb-3 transition-all duration-200">
                    <div className={cn(
                      "flex gap-2.5 transition-all duration-200",
                      "flex-col-reverse items-center text-center sm:flex-row sm:items-start sm:justify-between"
                    )}>
                      <CardTitle className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden font-semibold transition-all duration-200 justify-center sm:justify-start pr-0 sm:pr-1 pb-1">
                        {(() => {
                          const CategoryIcon = categoryIconMap[b.category] || Circle;
                          return <CategoryIcon className="size-icon-sm text-muted-foreground" aria-hidden="true" />;
                        })()}
                        <TitleTooltip title={tCategory(b.category)}>
                          <div className={cn("font-bold tracking-tight truncate cursor-default transition-all duration-200 text-ui-title leading-normal", hasFloorPressure ? "text-amber-500 dark:text-amber-400" : "text-foreground")}>
                            {tCategory(b.category)}
                          </div>
                        </TitleTooltip>
                      </CardTitle>
                      <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-end">
                        {hasFloorPressure && (
                          <TooltipProvider>
                            <Tooltip delayDuration={300}>
                              <TooltipTrigger asChild>
                                <div className="flex items-center justify-center rounded-full bg-amber-500/10 p-1.5 cursor-help transition-colors hover:bg-amber-500/20">
                                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                                </div>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-[260px] space-y-1 text-sm">
                                <p className="font-semibold text-amber-500">{t("budgets.floorWarning", { defaultValue: "Limit below required floor" })}</p>
                                <p className="text-muted-foreground text-xs leading-tight">
                                  {t("budgets.floorGapDesc", { defaultValue: "Your monthly limit is short by {{amount}} to cover known obligations in this category.", amount: formatUzs(floorData.warning_gap) })}
                                </p>
                                {floorData.reasons?.length > 0 && (
                                  <div className="mt-2 space-y-1 border-t border-border/50 pt-2 text-xs">
                                    {floorData.reasons.map((r, i) => (
                                      <div key={i} className="flex justify-between gap-3">
                                        <span className="truncate text-muted-foreground">{r.title}</span>
                                        <span className="font-medium shrink-0">{formatUzs(r.amount)}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                <div className="mt-3 pt-2 border-t border-border/50 flex justify-end">
                                  <Button 
                                    size="sm" 
                                    variant="secondary" 
                                    className="w-full text-amber-600 bg-amber-500/10 hover:bg-amber-500/20"
                                    onClick={(e) => {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      updateBudgetMutation.mutateAsync({
                                        category: b.category,
                                        monthlyLimit: floorData.floor_amount,
                                        budgetYear: b.budgetYear,
                                        budgetMonth: b.budgetMonth
                                      });
                                    }}
                                    disabled={updateBudgetMutation.isPending}
                                  >
                                    {t("budgets.fixFloorLimit", { defaultValue: "Raise limit to {{amount}}", amount: formatUzs(floorData.floor_amount) })}
                                  </Button>
                                </div>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                        <span
                          className={cn(
                            "inline-flex shrink-0 items-center justify-center rounded-full text-center font-medium leading-[1.3] transition-all duration-200 min-h-6 sm:min-h-7 md:min-h-8 px-1.5 sm:px-2 md:px-3 py-[3px] md:py-1 text-mobile-caption sm:text-xs md:text-xs whitespace-nowrap md:whitespace-normal max-w-fit md:min-w-[70px] lg:min-w-[86px]",
                            statusBadgeClass
                          )}
                        >
                          {statusLabel}
                        </span>
                      </div>
                    </div>
                    <CardDescription className="space-y-2">
                      <span className="block text-sm text-muted-foreground">{formatBudgetMonth(b.budgetYear, b.budgetMonth)}</span>
                      <InteractiveTooltip
                        content={`${t("budgets.usedOf", { spent: spentFullLabel, limit: limitFullLabel })} UZS`}
                        className="flex w-full items-baseline gap-1 overflow-hidden text-ellipsis whitespace-nowrap tabular-nums font-medium text-foreground text-ui-desc"
                      >
                        <span className="truncate">{usedOfLabel}</span>
                        <span className="shrink-0 text-mobile-caption font-medium uppercase tracking-[0.08em] text-muted-foreground/70">
                          UZS
                        </span>
                      </InteractiveTooltip>
                      <div className="space-y-1 text-xs tabular-nums">
                        <div className="flex items-center justify-between gap-3 text-muted-foreground">
                          <span>{t("budgets.parentLimit", { defaultValue: "Parent limit" })}</span>
                          <CurrencyAmount
                            value={b.effectiveLimit}
                            format={useCompactAmounts ? "compact" : "full"}
                            tooltip="compact"
                            className="flex items-baseline gap-1"
                            valueClassName=""
                            currencyClassName="font-normal"
                          />
                        </div>
                        <div className="flex items-center justify-between gap-3 text-muted-foreground">
                          <span>{t("budgets.totalSpent", { defaultValue: "Total spent" })}</span>
                          <CurrencyAmount
                            value={b.spent}
                            format={useCompactAmounts ? "compact" : "full"}
                            tooltip="compact"
                            className="flex items-baseline gap-1"
                            valueClassName=""
                            currencyClassName="font-normal"
                          />
                        </div>
                        <div className="flex items-center justify-between gap-3 text-muted-foreground">
                          <span>{t("budgets.projectReserved", { defaultValue: "Project reserved" })}</span>
                          <CurrencyAmount
                            value={b.projectReservedAmount}
                            format={useCompactAmounts ? "compact" : "full"}
                            tooltip="compact"
                            className="flex items-baseline gap-1"
                            valueClassName=""
                            currencyClassName="font-normal"
                          />
                        </div>
                        <div className="flex items-center justify-between gap-3 text-muted-foreground">
                          <span>{t("budgets.freeGeneralLimit", { defaultValue: "Free general limit" })}</span>
                          <CurrencyAmount
                            value={b.freeGeneralLimit}
                            format={useCompactAmounts ? "compact" : "full"}
                            tooltip="compact"
                            className="flex items-baseline gap-1"
                            valueClassName=""
                            currencyClassName="font-normal"
                          />
                        </div>
                      </div>
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5 pt-2 pb-4 sm:pt-1 sm:pb-6 transition-all duration-200">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 tabular-nums text-muted-foreground transition-all duration-200 text-ui-detail sm:text-ui-desc">
                      <span>{t("budgets.percentUsed", { percent })}</span>
                      <span className={cn(
                        "whitespace-nowrap flex items-baseline gap-1 transition-all duration-200",
                        b.spent > b.effectiveLimit ? "font-semibold text-destructive animate-pulse" : ""
                      )}>
                        {b.spent > b.effectiveLimit ? (
                          <CurrencyAmount
                            value={deltaAmount}
                            prefix="-"
                            format={useCompactAmounts ? "compact" : "full"}
                            tooltip="compact"
                            className="flex items-baseline gap-1"
                            currencyClassName=""
                          />
                        ) : (
                          <InteractiveTooltip
                            content={`${formatUzs(b.remaining)} UZS ${t("budgets.remainingLabel")}`}
                            className="flex items-baseline gap-1"
                          >
                            <span>{remainingLabel}</span>
                            <span className="text-mobile-micro font-medium uppercase tracking-[0.08em] text-muted-foreground/65">
                              UZS
                            </span>
                            <span>{t("budgets.remainingLabel")}</span>
                          </InteractiveTooltip>
                        )}
                      </span>
                    </div>
                    <Progress
                      value={loading ? 0 : percent}
                      className="h-2"
                      trackClassName={progressTrackClass}
                      indicatorClassName={progressIndicatorClass}
                    />
                    <div className="mt-4 flex min-h-10 items-center justify-between gap-3 opacity-0 transition-all duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
                      <Button
                        variant="outline"
                        className="h-10 min-w-[150px] justify-center rounded-md px-4 text-sm font-semibold"
                        onClick={() => openBudgetExpenses(b)}
                      >
                        <ReceiptText className="mr-2 h-4 w-4" />
                        {t("budgets.viewExpenses", { defaultValue: "View Expenses" })}
                      </Button>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            type="button"
                            size="icon"
                            variant="ghost"
                            className="h-10 w-10 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                            aria-label={t("budgets.actions", { defaultValue: "Budget actions" })}
                          >
                            <MoreHorizontal className="h-5 w-5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-52">
                          <DropdownMenuItem onSelect={() => openBudgetDetails(b)}>
                            <Eye className="h-4 w-4" />
                            {t("budgets.viewDetails", { defaultValue: "View details" })}
                          </DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => openUpdate(b)}>
                            <Pencil className="h-4 w-4" />
                            {t("budgets.updateLimit")}
                          </DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => openSubcategories(b)}>
                            <ListTree className="h-4 w-4" />
                            {t("budgets.addSubLimit", { defaultValue: "Add sub-limit" })}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          {b.remaining > 0 && (
                            <DropdownMenuItem onSelect={() => openParentReallocate(b)}>
                              <ArrowRightLeft className="h-4 w-4" />
                              {t("budgets.reallocate", { defaultValue: "Reallocate limits" })}
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem variant="destructive" onSelect={() => openDelete(b)}>
                            <Trash2 className="h-4 w-4" />
                            {t("budgets.delete")}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {!loading && !error && filteredBudgets.length === 0 && (
          <EmptyState
            title={t("budgets.emptyFilteredTitle")}
            description={t("budgets.emptyFilteredDesc")}
            className="my-10"
          />
        )}
        </>
        )}
      </div>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={viewExpensesOpen}
        onOpenChange={(open) => {
          setViewExpensesOpen(open);
          if (!open) setExpensesTargetBudget(null);
        }}
        title={
          expensesTargetBudget
            ? t("budgets.viewExpensesTitle", {
                defaultValue: "{{category}} expenses",
                category: tCategory(expensesTargetBudget.category),
              })
            : t("budgets.viewExpenses", { defaultValue: "View Expenses" })
        }
        description={
          expensesTargetBudget
            ? t("budgets.viewExpensesDesc", {
                defaultValue: "{{month}} category activity linked to this budget.",
                month: formatBudgetMonth(expensesTargetBudget.budgetYear, expensesTargetBudget.budgetMonth),
              })
            : ""
        }
        footer={
          <>
            <Button variant="outline" onClick={() => setViewExpensesOpen(false)}>
              {t("common.close", { defaultValue: "Close" })}
            </Button>
            <Button
              onClick={() => {
                if (!expensesTargetBudget || !expensesTargetRange) return;
                setViewExpensesOpen(false);
                navigate(
                  `/expenses?category=${encodeURIComponent(expensesTargetBudget.category)}&start_date=${expensesTargetRange.startDate}&end_date=${expensesTargetRange.endDate}`,
                );
              }}
              disabled={!expensesTargetBudget || !expensesTargetRange}
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              {t("budgets.openExpensesPage", { defaultValue: "Open Expenses" })}
            </Button>
          </>
        }
        dialogClassName="sm:max-w-[900px]"
      >
        <div className={cn("space-y-4", useBottomSheetForms && "pb-1")}>
          {budgetExpensesQuery.isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner className="h-8 w-8 text-primary" />
            </div>
          ) : budgetExpensesQuery.error ? (
            <EmptyState
              inline
              icon={ReceiptText}
              title={t("budgets.viewExpensesUnavailable", { defaultValue: "Expenses unavailable" })}
              description={localizeApiError(budgetExpensesQuery.error?.message, t) || t("expenses.noResults", { defaultValue: "No expenses found." })}
            />
          ) : budgetExpenseFeedItems.length === 0 ? (
            <EmptyState
              inline
              icon={ReceiptText}
              title={t("budgets.noBudgetExpensesTitle", { defaultValue: "No expenses yet" })}
              description={t("budgets.noBudgetExpensesDesc", {
                defaultValue: "No expense activity was found for this category and month.",
              })}
            />
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
                <span>
                  {t("budgets.expenseCount", {
                    defaultValue: "{{count}} matching expenses",
                    count: budgetExpenseTotal,
                  })}
                </span>
                {budgetExpenseTotal > budgetExpenseFeedItems.length ? (
                  <span>
                    {t("budgets.expenseModalLimit", {
                      defaultValue: "Showing first {{count}}",
                      count: budgetExpenseFeedItems.length,
                    })}
                  </span>
                ) : null}
              </div>
              <div className="max-h-[58vh] space-y-2 overflow-y-auto pr-1">
                {budgetExpenseFeedItems.map((feedItem) => (
                  <BudgetExpenseFeedRow
                    key={
                      feedItem?.type === "MERGE_GROUP"
                        ? `group-${feedItem.merge_group?.id}`
                        : `expense-${feedItem.expense?.id}`
                    }
                    feedItem={feedItem}
                    t={t}
                    tCategory={tCategory}
                    appLang={appLang}
                    onOpenExpense={(expenseId) => {
                      setViewExpensesOpen(false);
                      navigate(`/expenses/${expenseId}`);
                    }}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </ResponsiveBudgetFormShell>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={viewDetailsOpen}
        onOpenChange={(open) => {
          setViewDetailsOpen(open);
          if (!open) setDetailsTargetBudget(null);
        }}
        title={
          detailsTargetBudget
            ? t("budgets.viewDetailsTitle", {
                defaultValue: "{{category}} details",
                category: tCategory(detailsTargetBudget.category),
              })
            : t("budgets.viewDetails", { defaultValue: "View details" })
        }
        description={
          detailsTargetBudget
            ? t("budgets.viewDetailsDesc", {
                defaultValue: "{{month}} budget health, limits, activity, and project overlays.",
                month: formatBudgetMonth(detailsTargetBudget.budgetYear, detailsTargetBudget.budgetMonth),
              })
            : ""
        }
        footer={
          <>
            <Button variant="outline" onClick={() => setViewDetailsOpen(false)}>
              {t("common.close", { defaultValue: "Close" })}
            </Button>
            {detailsTargetBudget ? (
              <Button
                onClick={() => {
                  setViewDetailsOpen(false);
                  openUpdate(detailsTargetBudget);
                }}
              >
                <Pencil className="mr-2 h-4 w-4" />
                {t("budgets.updateLimit", { defaultValue: "Update limit" })}
              </Button>
            ) : null}
          </>
        }
        dialogClassName="sm:max-w-[1040px]"
      >
        <div className={cn("space-y-5", useBottomSheetForms && "pb-1")}>
          {budgetDetailsQuery.isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner className="h-8 w-8 text-primary" />
            </div>
          ) : budgetDetailsQuery.error || !budgetDetail ? (
            <EmptyState
              inline
              icon={FolderKanban}
              title={t("budgets.detailsUnavailable", { defaultValue: "Budget details unavailable" })}
              description={localizeApiError(budgetDetailsQuery.error?.message, t) || t("budgets.loadFailed", { defaultValue: "Failed to load budgets" })}
            />
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                <Badge variant={budgetDetail.is_over_limit ? "destructive" : "secondary"} className="rounded-full px-3 py-1">
                  {budgetDetail.is_over_limit
                    ? t("budgets.status.overBudget", { defaultValue: "Over Budget" })
                    : t("budgets.status.onTrack", { defaultValue: "On Track" })}
                </Badge>
                <Badge variant="outline" className="rounded-full px-3 py-1">
                  {t("budgets.expenseCount", {
                    defaultValue: "{{count}} matching expenses",
                    count: budgetDetail.expense_count || 0,
                  })}
                </Badge>
                {(budgetDetail.subcategories || []).length ? (
                  <Badge variant="outline" className="rounded-full px-3 py-1">
                    {t("budgets.subcategoryCount", {
                      defaultValue: "{{count}} subcategories",
                      count: budgetDetail.subcategories.length,
                    })}
                  </Badge>
                ) : null}
                {(budgetDetail.project_reservations || []).length ? (
                  <Badge variant="outline" className="rounded-full px-3 py-1">
                    {t("budgets.projectReservationCount", {
                      defaultValue: "{{count}} active reservations",
                      count: budgetDetail.project_reservations.length,
                    })}
                  </Badge>
                ) : null}
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <BudgetDialogStat
                  label={t("budgets.baseLimit", { defaultValue: "Base limit" })}
                  value={<CurrencyAmount value={budgetDetail.monthly_limit} format="compact" tooltip="compact" className="flex items-baseline gap-1" />}
                  icon={Layers3}
                />
                <BudgetDialogStat
                  label={t("budgets.effectiveLimit", { defaultValue: "Effective limit" })}
                  value={<CurrencyAmount value={budgetDetail.effective_monthly_limit} format="compact" tooltip="compact" className="flex items-baseline gap-1" />}
                  icon={ChartColumn}
                />
                <BudgetDialogStat
                  label={t("budgets.spentLabel", { defaultValue: "Spent" })}
                  value={<CurrencyAmount value={budgetDetail.spent} format="compact" tooltip="compact" className="flex items-baseline gap-1" />}
                  icon={ReceiptText}
                />
                <BudgetDialogStat
                  label={t("budgets.remainingLabel", { defaultValue: "Remaining" })}
                  value={<CurrencyAmount value={budgetDetail.remaining} format="compact" tooltip="compact" className="flex items-baseline gap-1" />}
                  icon={FolderKanban}
                />
              </div>

              <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
                <section className="space-y-3 rounded-lg border border-border/60 bg-muted/10 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold">{t("budgets.effectStack", { defaultValue: "Effect stack" })}</h3>
                    <CurrencyAmount
                      value={budgetDetail.effective_available}
                      format="compact"
                      tooltip="compact"
                      className="flex items-baseline gap-1 text-sm font-semibold"
                      currencyClassName="text-muted-foreground/70"
                    />
                  </div>
                  <div className="space-y-2">
                    {detailsEffects.map((effect) => (
                      <BudgetAmountRow
                        key={effect.label}
                        label={effect.label}
                        value={effect.value}
                        prefix={effect.prefix || ""}
                        tone={effect.tone || ""}
                      />
                    ))}
                  </div>
                </section>

                <section className="space-y-3 rounded-lg border border-border/60 bg-muted/10 p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h3 className="text-sm font-semibold">{t("budgets.subcategoryPartitions", { defaultValue: "Subcategory partitions" })}</h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t("budgets.subcategoryMonthScopedHint", {
                          defaultValue: "These limits belong to this budget month only.",
                        })}
                      </p>
                    </div>
                    <div className="grid gap-1 text-right text-xs text-muted-foreground">
                      <span>
                        {t("budgets.parentBuffer", { defaultValue: "Parent buffer" })}: {formatUzs(detailSubcategoryBuffer)}
                      </span>
                      <span>
                        {t("budgets.unspecifiedSpending", { defaultValue: "Unspecified spending" })}: {formatUzs(detailUnspecifiedSpent)}
                      </span>
                    </div>
                  </div>
                  {(budgetDetail.subcategories || []).length ? (
                    <div className="space-y-2">
                      {budgetDetail.subcategories.map((subcategory) => (
                        <div
                          key={subcategory.id}
                          className={cn(
                            "grid gap-3 rounded-lg border bg-background/70 p-3 sm:grid-cols-[minmax(0,1fr)_auto_auto_auto_auto] sm:items-center",
                            subcategory.is_over_limit ? "border-destructive/40 bg-destructive/5" : "border-border/60",
                          )}
                        >
                          <div className="min-w-0">
                            <div className="flex min-w-0 flex-wrap items-center gap-2">
                              <p className="truncate text-sm font-semibold text-foreground">{subcategory.name}</p>
                              {subcategory.is_over_limit ? (
                                <Badge variant="destructive" className="rounded-full px-2 py-0 text-[10px]">
                                  {t("budgets.needsRepair", { defaultValue: "Needs repair" })}
                                </Badge>
                              ) : null}
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {subcategory.is_active
                                ? t("income.active", { defaultValue: "Active" })
                                : t("income.inactive", { defaultValue: "Inactive" })}
                            </p>
                          </div>
                          <CurrencyAmount value={subcategory.monthly_limit || 0} format="compact" tooltip="compact" className="flex items-baseline gap-1 text-sm font-semibold" />
                          <CurrencyAmount value={subcategory.spent || 0} format="compact" tooltip="compact" className="flex items-baseline gap-1 text-sm text-muted-foreground" />
                          <CurrencyAmount
                            value={subcategory.remaining || 0}
                            format="compact"
                            tooltip="compact"
                            className={cn(
                              "flex items-baseline gap-1 text-sm font-semibold",
                              subcategory.is_over_limit ? "text-destructive" : "text-primary",
                            )}
                          />
                          {subcategory.is_over_limit && detailsTargetBudget ? (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setViewDetailsOpen(false);
                                openSubcategories(detailsTargetBudget, {
                                  targetId: subcategory.id,
                                  amount: Math.abs(Number(subcategory.remaining || 0)),
                                });
                              }}
                            >
                              <ArrowRightLeft className="mr-2 h-4 w-4" />
                              {t("budgets.reallocate", { defaultValue: "Reallocate" })}
                            </Button>
                          ) : null}
                        </div>
                      ))}
                      {detailUnspecifiedSpent > 0 ? (
                        <div className="grid gap-3 rounded-lg border border-border/60 bg-background/70 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-foreground">
                              {t("budgets.unspecifiedParentSpending", { defaultValue: "Unspecified parent spending" })}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {t("budgets.unspecifiedParentSpendingHint", {
                                defaultValue: "Expenses saved directly to the parent category.",
                              })}
                            </p>
                          </div>
                          <CurrencyAmount
                            value={detailUnspecifiedSpent}
                            format="compact"
                            tooltip="compact"
                            className="flex items-baseline gap-1 text-sm font-semibold sm:justify-end"
                          />
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <p className="rounded-lg border border-dashed border-border bg-background/60 px-3 py-4 text-sm text-muted-foreground">
                      {t("budgets.noSubcategoriesYet", { defaultValue: "No subcategories configured yet." })}
                    </p>
                  )}
                </section>
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <section className="space-y-3 rounded-lg border border-border/60 bg-muted/10 p-4">
                  <h3 className="text-sm font-semibold">{t("budgets.recentActivity", { defaultValue: "Recent activity" })}</h3>
                  {(budgetDetail.recent_activity || []).length ? (
                    <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
                      {budgetDetail.recent_activity.map((item) => (
                        <BudgetActivityRow
                          key={`${item.event_id}-${item.subcategory_id || "base"}-${item.project_id || "none"}`}
                          item={item}
                          t={t}
                          appLang={appLang}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="rounded-lg border border-dashed border-border bg-background/60 px-3 py-4 text-sm text-muted-foreground">
                      {t("budgets.noLinkedActivityYet", { defaultValue: "No linked activity yet." })}
                    </p>
                  )}
                </section>

                <section className="space-y-3 rounded-lg border border-border/60 bg-muted/10 p-4">
                  <div className="flex flex-col gap-1">
                    <h3 className="text-sm font-semibold">{t("budgets.activeProjectReservations", { defaultValue: "Active project reservations" })}</h3>
                    <p className="text-xs text-muted-foreground">
                      {t("budgets.activeProjectReservationsHint", {
                        defaultValue: "Overlay projects reserve spending permission from this parent category for the selected month.",
                      })}
                    </p>
                  </div>
                  {(budgetDetail.project_reservations || []).length ? (
                    <div className="space-y-2">
                      {budgetDetail.project_reservations.map((reservation) => (
                        <BudgetProjectReservationRow
                          key={`${reservation.project_id}-${reservation.category}-${reservation.budget_year}-${reservation.budget_month}`}
                          reservation={reservation}
                          t={t}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="rounded-lg border border-dashed border-border bg-background/60 px-3 py-4 text-sm text-muted-foreground">
                      {t("budgets.noActiveProjectReservations", { defaultValue: "No active overlay reservations in this budget month." })}
                    </p>
                  )}
                </section>
              </div>
            </>
          )}
        </div>
      </ResponsiveBudgetFormShell>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={projectStructureOpen}
        onOpenChange={setProjectStructureOpen}
        title={t("projects.manageStructure", { defaultValue: "Manage structure" })}
        description={
          structureProject
            ? `${structureProject.title} · ${structureProjectIsIsolated
              ? t("projects.isolated", { defaultValue: "Isolated" })
              : t("projects.overlay", { defaultValue: "Overlay" })}`
            : t("projects.manageStructureDesc", {
                defaultValue: "Define project category funding or overlay reservations.",
              })
        }
        footer={
          <Button variant="outline" onClick={() => setProjectStructureOpen(false)}>
            {t("common.close", { defaultValue: "Close" })}
          </Button>
        }
        dialogClassName="sm:max-w-[960px]"
      >
        <div className={cn("space-y-4", useBottomSheetForms && "pb-1")}>
          <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
            <p className="text-sm font-semibold">
              {structureProjectIsIsolated
                ? t("projects.addCategoryFunding", { defaultValue: "Add parent category funding" })
                : t("projects.addCategoryLimit", { defaultValue: "Add project category" })}
            </p>
            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto]">
              <Select value={projectCategoryValue || undefined} onValueChange={setProjectCategoryValue}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue placeholder={t("expenses.category")} />
                </SelectTrigger>
                <SelectContent className={selectContentClass}>
                  {orderedCategoryOptions.map((category) => (
                    <SelectItem key={category} value={category}>{tCategory(category)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                value={projectCategoryLimitValue}
                onChange={(e) => setProjectCategoryLimitValue(formatBudgetAmountInput(e.target.value))}
                inputMode="numeric"
                placeholder={
                  structureProjectIsIsolated
                    ? t("projects.fundingAmount", { defaultValue: "Funding amount" })
                    : t("projects.totalLimit", { defaultValue: "Limit amount" })
                }
              />
              <Button
                onClick={handleCreateProjectCategoryLimit}
                disabled={
                  !structureProject ||
                  createProjectCategoryMutation.isPending ||
                  projectCategoryWouldOverbook ||
                  Boolean(projectCategoryValue && !structureProjectIsIsolated && !projectCategoryHeadroom?.budget)
                }
              >
                <Plus className="mr-2 h-4 w-4" />
                {t("common.add", { defaultValue: "Add" })}
              </Button>
            </div>
            {structureProject && !structureProjectIsIsolated && projectCategoryValue ? (
              <p className={cn("mt-3 text-sm", projectCategoryWouldOverbook ? "text-destructive" : "text-muted-foreground")}>
                {projectCategoryHeadroom?.budget
                  ? t("projects.overlayCategoryHeadroom", {
                      defaultValue: "Available selected-month headroom: {{amount}}",
                      amount: formatUzs(projectCategoryHeadroom.headroom || 0),
                    })
                  : t("projects.overlayCategoryNeedsBudget", {
                      defaultValue: "Add this category to the selected monthly budget before reserving it.",
                    })}
              </p>
            ) : null}
          </div>

          <div className="space-y-3">
            <p className="text-sm font-semibold">
              {structureProjectIsIsolated
                ? t("projects.categoryFundingSection", { defaultValue: "Parent category funding" })
                : t("projects.categoryLimitsSection", { defaultValue: "Project categories" })}
            </p>
            {structureProjectCategories.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
                {structureProjectIsIsolated
                  ? t("projects.noCategoryFundingYet", { defaultValue: "No category funding yet. Add one to distribute the isolated stash." })
                  : t("projects.noCategoryLimitsYet", { defaultValue: "No project categories yet. Add one to define structure and spending limits." })}
              </div>
            ) : (
              structureProjectCategories.map((categoryRow) => (
                <div key={categoryRow.category} className="rounded-2xl border border-border/60 bg-background/80 p-4">
                  {editingProjectCategory === categoryRow.category ? (
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto_auto]">
                      <div className="flex items-center rounded-md border border-border/60 bg-muted/15 px-3 text-sm font-medium">
                        {tCategory(categoryRow.category)}
                      </div>
                      <Input
                        value={editingProjectCategoryLimit}
                        onChange={(e) => setEditingProjectCategoryLimit(formatBudgetAmountInput(e.target.value))}
                        inputMode="numeric"
                      />
                      <Button
                        onClick={handleUpdateProjectCategoryLimit}
                        disabled={updateProjectCategoryMutation.isPending || editingProjectCategoryWouldOverbook}
                      >
                        {t("common.save")}
                      </Button>
                      <Button variant="outline" onClick={() => {
                        setEditingProjectCategory("");
                        setEditingProjectCategoryLimit("");
                      }}>
                        {t("common.cancel")}
                      </Button>
                      {editingProjectCategoryHeadroom ? (
                        <p className={cn("lg:col-span-4 text-sm", editingProjectCategoryWouldOverbook ? "text-destructive" : "text-muted-foreground")}>
                          {t("projects.overlayCategoryHeadroom", {
                            defaultValue: "Available selected-month headroom: {{amount}}",
                            amount: formatUzs(editingProjectCategoryHeadroom.headroom || 0),
                          })}
                        </p>
                      ) : null}
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div className="min-w-0">
                        <p className="font-medium">{tCategory(categoryRow.category)}</p>
                        <p className="text-sm text-muted-foreground">
                          {structureProjectIsIsolated && categoryRow.limit_amount
                            ? `${t("projects.funding", { defaultValue: "Funding" })}: ${formatUzs(categoryRow.limit_amount)} - `
                            : ""}
                          {t("budgets.spentLabel", { defaultValue: "Spent" })}: {formatUzs(categoryRow.spent || 0)}
                          {categoryRow.limit_amount ? ` · ${t("budgets.remainingLabel", { defaultValue: "Remaining" })}: ${formatUzs(categoryRow.remaining || 0)}` : ""}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={categoryRow.is_over_limit ? "destructive" : "outline"}>
                          {categoryRow.limit_amount ? formatUzs(categoryRow.limit_amount) : t("projects.noLimit", { defaultValue: "No limit" })}
                        </Badge>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingProjectCategory(categoryRow.category);
                            setEditingProjectCategoryLimit(categoryRow.limit_amount ? formatBudgetAmountInput(String(categoryRow.limit_amount)) : "");
                          }}
                        >
                          {t("common.edit", { defaultValue: "Edit" })}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => deleteProjectCategoryMutation.mutate({
                            projectId: structureProject.id,
                            category: categoryRow.category,
                            budgetYear: categoryRow.budget_year || summaryTarget.year,
                            budgetMonth: categoryRow.budget_month || summaryTarget.month,
                          })}
                          disabled={deleteProjectCategoryMutation.isPending}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          {t("common.delete", { defaultValue: "Delete" })}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {structureProject && !structureProjectIsIsolated ? (
            <>
              <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
                <p className="text-sm font-semibold">{t("projects.addOverlaySubcategory", { defaultValue: "Reserve a global monthly subcategory" })}</p>
                <div className="mt-3 grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)_180px_auto]">
                  <Select
                    value={projectSubcategoryCategory || undefined}
                    onValueChange={(value) => {
                      setProjectSubcategoryCategory(value);
                      setProjectSubcategoryUserSubcategoryId("");
                    }}
                  >
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("expenses.category")} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {structureProjectCategories.map((categoryRow) => (
                        <SelectItem key={categoryRow.category} value={categoryRow.category}>{tCategory(categoryRow.category)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={projectSubcategoryUserSubcategoryId || undefined}
                    onValueChange={setProjectSubcategoryUserSubcategoryId}
                    disabled={!projectSubcategoryCategory || !overlayProjectSubcategoryBudget || overlayEligibleSubcategories.length === 0}
                  >
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("projects.chooseGlobalSubcategory", { defaultValue: "Choose monthly subcategory" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {overlayEligibleSubcategories.map((subcategory) => (
                        <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                          {subcategory.name} · {formatUzs(subcategory.monthly_limit || 0)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    value={projectSubcategoryLimit}
                    onChange={(e) => setProjectSubcategoryLimit(formatBudgetAmountInput(e.target.value))}
                    inputMode="numeric"
                    placeholder={t("projects.reservationAmount", { defaultValue: "Reservation" })}
                  />
                  <Button
                    onClick={handleCreateProjectSubcategory}
                    disabled={!structureProject || createProjectSubcategoryMutation.isPending || projectSubcategoryWouldOverbook}
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    {t("common.add", { defaultValue: "Add" })}
                  </Button>
                </div>
                {projectSubcategoryCategory && !overlayProjectSubcategoryBudget ? (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {t("projects.overlaySubcategoryNeedsBudget", { defaultValue: "Add this category to the selected monthly budget before reserving its subcategories." })}
                  </p>
                ) : null}
                {projectSubcategoryCategory && overlayProjectSubcategoryBudget && overlayEligibleSubcategories.length === 0 ? (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {t("projects.overlaySubcategoryNeedsLane", { defaultValue: "Add an eligible subcategory lane to this monthly budget first, or all current lanes are already attached." })}
                  </p>
                ) : null}
                {projectSubcategoryHeadroom ? (
                  <p className={cn("mt-3 text-sm", projectSubcategoryWouldOverbook ? "text-destructive" : "text-muted-foreground")}>
                    {t("projects.overlaySubcategoryHeadroom", {
                      defaultValue: "Available lane headroom: {{amount}}",
                      amount: formatUzs(projectSubcategoryHeadroom.headroom || 0),
                    })}
                  </p>
                ) : null}
              </div>

              <div className="space-y-3">
                <p className="text-sm font-semibold">{t("projects.overlaySubcategoriesSection", { defaultValue: "Global subcategory reservations" })}</p>
                {structureProjectCategories.every((categoryRow) => (categoryRow.subcategories?.length || 0) === 0) ? (
                  <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
                    {t("projects.noOverlaySubcategoriesYet", { defaultValue: "No global subcategory reservations for this month yet." })}
                  </div>
                ) : (
                  structureProjectCategories.map((categoryRow) => (
                    <div key={`${categoryRow.category}-overlay-subcategories`} className="rounded-2xl border border-border/60 bg-background/80 p-4">
                      <p className="text-sm font-semibold">{tCategory(categoryRow.category)}</p>
                      <div className="mt-3 space-y-3">
                        {(categoryRow.subcategories || []).map((subcategory) => (
                          <div key={subcategory.id} className="rounded-xl border border-border/50 bg-muted/15 p-3">
                            {editingProjectSubcategoryId === subcategory.id ? (
                              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_auto_auto]">
                                <div className="flex min-h-9 items-center rounded-md border border-border/60 px-3 text-sm">
                                  {subcategory.name}
                                </div>
                                <Input value={editingProjectSubcategoryLimit} onChange={(e) => setEditingProjectSubcategoryLimit(formatBudgetAmountInput(e.target.value))} inputMode="numeric" />
                                <Button
                                  onClick={handleUpdateProjectSubcategory}
                                  disabled={
                                    updateProjectSubcategoryMutation.isPending ||
                                    editingProjectSubcategoryWouldOverbook ||
                                    Boolean(!structureProjectIsIsolated && !editingProjectSubcategoryHeadroom?.subcategory)
                                  }
                                >
                                  {t("common.save")}
                                </Button>
                                <Button variant="outline" onClick={() => {
                                  setEditingProjectSubcategoryId(null);
                                  setEditingProjectSubcategoryUserSubcategoryId("");
                                  setEditingProjectSubcategoryName("");
                                  setEditingProjectSubcategoryLimit("");
                                  setEditingProjectSubcategoryIsActive("true");
                                }}>
                                  {t("common.cancel")}
                                </Button>
                                {editingProjectSubcategoryHeadroom ? (
                                  <p className={cn("lg:col-span-4 text-sm", editingProjectSubcategoryWouldOverbook ? "text-destructive" : "text-muted-foreground")}>
                                    {t("projects.overlaySubcategoryHeadroom", {
                                      defaultValue: "Available lane headroom: {{amount}}",
                                      amount: formatUzs(editingProjectSubcategoryHeadroom.headroom || 0),
                                    })}
                                  </p>
                                ) : null}
                              </div>
                            ) : (
                              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                <div className="min-w-0">
                                  <p className="font-medium">{subcategory.name}</p>
                                  <p className="text-sm text-muted-foreground">
                                    {formatUzs(subcategory.limit_amount || 0)}
                                    {` · ${t("budgets.spentLabel", { defaultValue: "Spent" })}: ${formatUzs(subcategory.spent || 0)}`}
                                  </p>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setEditingProjectSubcategoryId(subcategory.id);
                                      setEditingProjectSubcategoryUserSubcategoryId(String(subcategory.user_subcategory_id || ""));
                                      setEditingProjectSubcategoryName(subcategory.name || "");
                                      setEditingProjectSubcategoryLimit(subcategory.limit_amount ? formatBudgetAmountInput(String(subcategory.limit_amount)) : "");
                                      setEditingProjectSubcategoryIsActive(subcategory.is_active ? "true" : "false");
                                    }}
                                  >
                                    {t("common.edit", { defaultValue: "Edit" })}
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                    onClick={() => deleteProjectSubcategoryMutation.mutate({ projectId: structureProject.id, subcategoryId: subcategory.id })}
                                    disabled={deleteProjectSubcategoryMutation.isPending}
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    {t("common.delete", { defaultValue: "Delete" })}
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          ) : null}

          {structureProjectIsIsolated ? (
            <>
              <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
                <p className="text-sm font-semibold">{t("projects.addProjectSubcategory", { defaultValue: "Add project subcategory" })}</p>
                <div className="mt-3 grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)_180px_140px_auto]">
                  <Select value={projectSubcategoryCategory || undefined} onValueChange={setProjectSubcategoryCategory}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("expenses.category")} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {structureProjectCategories.map((categoryRow) => (
                        <SelectItem key={categoryRow.category} value={categoryRow.category}>{tCategory(categoryRow.category)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    value={projectSubcategoryName}
                    onChange={(e) => setProjectSubcategoryName(e.target.value)}
                    placeholder={t("projects.projectSubcategoryName", { defaultValue: "Subcategory name" })}
                  />
                  <Input
                    value={projectSubcategoryLimit}
                    onChange={(e) => setProjectSubcategoryLimit(formatBudgetAmountInput(e.target.value))}
                    inputMode="numeric"
                    placeholder={t("projects.totalLimit", { defaultValue: "Limit amount" })}
                  />
                  <Select value={projectSubcategoryIsActive} onValueChange={setProjectSubcategoryIsActive}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      <SelectItem value="true">{t("common.active", { defaultValue: "Active" })}</SelectItem>
                      <SelectItem value="false">{t("common.inactive", { defaultValue: "Inactive" })}</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button onClick={handleCreateProjectSubcategory} disabled={!structureProject || createProjectSubcategoryMutation.isPending}>
                    <Plus className="mr-2 h-4 w-4" />
                    {t("common.add", { defaultValue: "Add" })}
                  </Button>
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-sm font-semibold">{t("projects.projectSubcategoriesSection", { defaultValue: "Project subcategories" })}</p>
                {structureProjectCategories.every((categoryRow) => (categoryRow.subcategories?.length || 0) === 0) ? (
                  <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
                    {t("projects.noProjectSubcategoriesYet", { defaultValue: "No project subcategories yet." })}
                  </div>
                ) : (
                  structureProjectCategories.map((categoryRow) => (
                    <div key={`${categoryRow.category}-subcategories`} className="rounded-2xl border border-border/60 bg-background/80 p-4">
                      <p className="text-sm font-semibold">{tCategory(categoryRow.category)}</p>
                      <div className="mt-3 space-y-3">
                        {(categoryRow.subcategories || []).map((subcategory) => (
                          <div key={subcategory.id} className="rounded-xl border border-border/50 bg-muted/15 p-3">
                            {editingProjectSubcategoryId === subcategory.id ? (
                              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_140px_auto_auto]">
                                <Input value={editingProjectSubcategoryName} onChange={(e) => setEditingProjectSubcategoryName(e.target.value)} />
                                <Input value={editingProjectSubcategoryLimit} onChange={(e) => setEditingProjectSubcategoryLimit(formatBudgetAmountInput(e.target.value))} inputMode="numeric" />
                                <Select value={editingProjectSubcategoryIsActive} onValueChange={setEditingProjectSubcategoryIsActive}>
                                  <SelectTrigger className={selectTriggerClass}><SelectValue /></SelectTrigger>
                                  <SelectContent className={selectContentClass}>
                                    <SelectItem value="true">{t("common.active", { defaultValue: "Active" })}</SelectItem>
                                    <SelectItem value="false">{t("common.inactive", { defaultValue: "Inactive" })}</SelectItem>
                                  </SelectContent>
                                </Select>
                                <Button onClick={handleUpdateProjectSubcategory} disabled={updateProjectSubcategoryMutation.isPending}>
                                  {t("common.save")}
                                </Button>
                                <Button variant="outline" onClick={() => {
                                  setEditingProjectSubcategoryId(null);
                                  setEditingProjectSubcategoryName("");
                                  setEditingProjectSubcategoryLimit("");
                                  setEditingProjectSubcategoryIsActive("true");
                                }}>
                                  {t("common.cancel")}
                                </Button>
                              </div>
                            ) : (
                              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                <div className="min-w-0">
                                  <p className="font-medium">{subcategory.name}</p>
                                  <p className="text-sm text-muted-foreground">
                                    {subcategory.is_active ? t("common.active", { defaultValue: "Active" }) : t("common.inactive", { defaultValue: "Inactive" })}
                                    {subcategory.limit_amount ? ` · ${formatUzs(subcategory.limit_amount)}` : ""}
                                    {` · ${t("budgets.spentLabel", { defaultValue: "Spent" })}: ${formatUzs(subcategory.spent || 0)}`}
                                  </p>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setEditingProjectSubcategoryId(subcategory.id);
                                      setEditingProjectSubcategoryName(subcategory.name || "");
                                      setEditingProjectSubcategoryLimit(subcategory.limit_amount ? formatBudgetAmountInput(String(subcategory.limit_amount)) : "");
                                      setEditingProjectSubcategoryIsActive(subcategory.is_active ? "true" : "false");
                                    }}
                                  >
                                    {t("common.edit", { defaultValue: "Edit" })}
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                    onClick={() => deleteProjectSubcategoryMutation.mutate({ projectId: structureProject.id, subcategoryId: subcategory.id })}
                                    disabled={deleteProjectSubcategoryMutation.isPending}
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    {t("common.delete", { defaultValue: "Delete" })}
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          ) : null}

          {actionError && <p className="text-sm text-red-600">{actionError}</p>}
        </div>
      </ResponsiveBudgetFormShell>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={projectOpen}
        onOpenChange={setProjectOpen}
        title={t("projects.create", { defaultValue: "Create Project" })}
        description={t("projects.createDesc", { defaultValue: "Create a purpose-based project budget alongside your monthly budgets." })}
        footer={createProjectFooter}
        dialogClassName="sm:max-w-[560px]"
      >
        <div className={cn("space-y-3", useBottomSheetForms && "pb-1")}>
          <div className="grid gap-2 text-xs sm:grid-cols-4">
              {projectWizardSteps.map((label, index) => {
                const step = index + 1;
                return (
                  <span
                    key={step}
                    className={cn(
                      "inline-flex min-h-8 items-center justify-center rounded-lg border px-2 text-center font-medium",
                      projectWizardStep === step
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border bg-muted/20 text-muted-foreground"
                    )}
                  >
                    {step}. {label}
                  </span>
                );
              })}
            </div>

          <div className="space-y-1.5">
            <label>{t("projects.title", { defaultValue: "Title" })}</label>
            <input
              type="text"
              autoComplete="off"
              className={inputBaseClass}
              value={projectTitle}
              onChange={(e) => setProjectTitle(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label>{t("expenses.description")}</label>
            <textarea
              className={cn(inputBaseClass, "min-h-[100px] resize-none py-2")}
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
            />
          </div>
          {projectWizardStep === 1 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label>{t("projects.mode", { defaultValue: "Mode" })}</label>
                <Select value={projectIsIsolated} onValueChange={(value) => {
                  setProjectIsIsolated(value);
                  setProjectWizardStep(1);
                }}>
                  <SelectTrigger className={selectTriggerClass}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className={selectContentClass}>
                    <SelectItem value="true">{t("projects.isolated", { defaultValue: "Isolated" })}</SelectItem>
                    <SelectItem value="false">{t("projects.overlay", { defaultValue: "Overlay" })}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {!isOverlayProjectDraft ? (
                <BudgetDialogStat
                  label={t("projects.derivedStash", { defaultValue: "Derived stash" })}
                  value={<CurrencyAmount value={projectDerivedStashTotal} format="compact" tooltip="compact" />}
                  icon={Shield}
                />
              ) : (
                <BudgetDialogStat
                  label={t("projects.activeBudgetMonth", { defaultValue: "Active month" })}
                  value={activeBudgetMonthLabel}
                  icon={CalendarClock}
                />
              )}
            </div>
          ) : null}
          {projectWizardStep === 1 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label>{t("projects.startDate", { defaultValue: "Start date" })}</label>
                <input
                  type="date"
                  className={inputBaseClass}
                  value={projectStartDate}
                  onChange={(e) => setProjectStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label>{t("projects.targetEndDate", { defaultValue: "Target end date" })}</label>
                <input
                  type="date"
                  className={inputBaseClass}
                  value={projectTargetEndDate}
                  onChange={(e) => setProjectTargetEndDate(e.target.value)}
                />
              </div>
            </div>
          ) : null}

          {isOverlayProjectDraft && projectWizardStep === 1 ? (
            <div className="space-y-1.5">
              <label>{t("projects.targetEstimate", { defaultValue: "Target estimate" })}</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="off"
                maxLength={maxBudgetAmountInputLength}
                className={inputBaseClass}
                value={projectTargetEstimate}
                onChange={(e) => setProjectTargetEstimate(formatBudgetAmountInput(e.target.value))}
                placeholder={t("projects.planningContextOnly", { defaultValue: "Planning context only" })}
              />
            </div>
          ) : null}

          {!isOverlayProjectDraft && projectWizardStep === 2 ? (
            <div className="space-y-3 rounded-lg border border-border/70 p-3">
              <div>
                <p className="text-sm font-semibold">{t("projects.walletQuarantine", { defaultValue: "Wallet quarantine" })}</p>
                <p className="text-xs text-muted-foreground">
                  {t("projects.walletQuarantineHint", { defaultValue: "Lock real free money from wallets. The project stash is derived from these rows." })}
                </p>
              </div>
              {projectWalletsQuery.isLoading ? (
                <div className="flex min-h-24 items-center justify-center">
                  <LoadingSpinner />
                </div>
              ) : projectWalletRows.length === 0 ? (
                <p className="rounded-lg border border-dashed border-border/70 p-3 text-sm text-muted-foreground">
                  {t("projects.noWalletFundingAvailable", { defaultValue: "No active wallet has positive owned money available for project funding." })}
                </p>
              ) : (
                <div className="space-y-2">
                  {projectWalletRows.map((row) => (
                    <div key={row.wallet.id} className="rounded-lg border border-border/70 p-3">
                      <div className="grid gap-2 sm:grid-cols-[1fr_160px] sm:items-center">
                        <div>
                          <p className="text-sm font-medium">{row.wallet.name}</p>
                          <p className={cn("text-xs", row.isOverAllocated ? "text-destructive" : "text-muted-foreground")}>
                            {t("projects.walletFundingAvailability", {
                              defaultValue: "{{free}} free of {{owned}} owned",
                              free: formatUzs(row.freeToAllocate),
                              owned: formatUzs(Number(row.wallet.owned_balance ?? row.wallet.current_balance ?? 0)),
                            })}
                          </p>
                          {(Number(row.wallet.protected_for_goals || 0) > 0 || Number(row.wallet.protected_for_projects || 0) > 0) ? (
                            <p className="text-xs text-muted-foreground">
                              {t("projects.walletProtectedAmounts", {
                                defaultValue: "{{goals}} protected for goals, {{projects}} protected for projects",
                                goals: formatUzs(Number(row.wallet.protected_for_goals || 0)),
                                projects: formatUzs(Number(row.wallet.protected_for_projects || 0)),
                              })}
                            </p>
                          ) : null}
                        </div>
                        <Input
                          value={row.input}
                          inputMode="numeric"
                          maxLength={maxBudgetAmountInputLength}
                          onChange={(e) => setProjectWalletAllocations((current) => ({
                            ...current,
                            [String(row.wallet.id)]: formatBudgetAmountInput(e.target.value),
                          }))}
                          className={cn(row.isOverAllocated && "border-destructive focus-visible:ring-destructive/30")}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="grid gap-2 sm:grid-cols-2">
                <BudgetDialogStat
                  label={t("projects.totalProjectStash", { defaultValue: "Total project stash" })}
                  value={<CurrencyAmount value={projectDerivedStashTotal} format="compact" tooltip="compact" />}
                  icon={Shield}
                />
                <BudgetDialogStat
                  label={t("projects.walletRows", { defaultValue: "Funding wallets" })}
                  value={projectWalletAllocationPayload.length}
                  icon={ListTree}
                />
              </div>
            </div>
          ) : null}

          {!isOverlayProjectDraft && projectWizardStep === 3 ? (
            <div className="space-y-3">
              <div>
                <p className="text-sm font-semibold">{t("projects.parentCategoryFunding", { defaultValue: "Parent category funding" })}</p>
                <p className="text-xs text-muted-foreground">
                  {t("projects.parentCategoryFundingHint", { defaultValue: "Distribute the derived project stash across global categories." })}
                </p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <BudgetDialogStat
                  label={t("projects.allocatedFunding", { defaultValue: "Allocated" })}
                  value={<CurrencyAmount value={projectIsolatedCategorySummary.allocatedAmount} format="compact" tooltip="compact" />}
                  icon={ListTree}
                />
                <BudgetDialogStat
                  label={t("projects.unallocatedFunding", { defaultValue: "Unallocated" })}
                  value={<CurrencyAmount value={projectIsolatedCategorySummary.unallocatedAmount} format="compact" tooltip="compact" />}
                  icon={Shield}
                />
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {orderedCategoryOptions.map((category) => {
                  const selected = projectSelectedCategories.includes(category);
                  return (
                    <button
                      type="button"
                      key={category}
                      onClick={() => toggleProjectCategory(category)}
                      className={cn(
                        "flex min-h-14 items-center justify-between rounded-lg border p-3 text-left text-sm transition",
                        selected ? "border-primary bg-primary/10" : "border-border/70 bg-muted/10 hover:bg-muted/30"
                      )}
                    >
                      <span className="block font-medium">{tCategory(category)}</span>
                      {selected ? <Check className="h-4 w-4 text-primary" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                    </button>
                  );
                })}
              </div>
              {projectIsolatedCategoryAllocationRows.length > 0 ? (
                <div className="space-y-2">
                  {projectIsolatedCategoryAllocationRows.map((row) => (
                    <div key={row.category} className="rounded-lg border border-border/70 p-3">
                      <div className="grid gap-2 sm:grid-cols-[1fr_160px] sm:items-center">
                        <div>
                          <p className="text-sm font-medium">{tCategory(row.category)}</p>
                          <p className={cn("text-xs", row.isInvalidAmount ? "text-destructive" : "text-muted-foreground")}>
                            {row.isInvalidAmount
                              ? t("projects.categoryFundingRequired", { defaultValue: "Enter a funding amount above zero." })
                              : t("projects.categoryFundingFromStash", { defaultValue: "Funded from the pooled stash." })}
                          </p>
                        </div>
                        <Input
                          value={row.input}
                          inputMode="numeric"
                          maxLength={maxBudgetAmountInputLength}
                          onChange={(e) => setProjectCategoryAllocations((current) => ({
                            ...current,
                            [row.category]: formatBudgetAmountInput(e.target.value),
                          }))}
                          className={cn(
                            (row.isInvalidAmount || projectIsolatedCategorySummary.isOverAllocated) &&
                            "border-destructive focus-visible:ring-destructive/30"
                          )}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
              {projectIsolatedCategorySummary.isOverAllocated ? (
                <p className="text-sm text-destructive">
                  {t("projects.isolatedCategoryOverAllocated", { defaultValue: "Category funding exceeds the derived project stash." })}
                </p>
              ) : null}
            </div>
          ) : null}

          {!isOverlayProjectDraft && projectWizardStep === 4 ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-border/70 p-3">
                <p className="text-sm font-semibold">{t("projects.microStructure", { defaultValue: "Micro structure" })}</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_140px_auto]">
                  <Select value={projectMicroCategory || undefined} onValueChange={(value) => {
                    setProjectMicroCategory(value);
                    setProjectMicroSubcategoryId("");
                    setProjectMicroLimit("");
                  }}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("projects.category", { defaultValue: "Category" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {projectSelectedCategories.map((category) => (
                        <SelectItem key={category} value={category}>{tCategory(category)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={projectMicroSubcategoryId || undefined}
                    onValueChange={setProjectMicroSubcategoryId}
                    disabled={!projectMicroCategory || projectIsolatedEligibleMicroSubcategories.length === 0}
                  >
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("projects.subcategory", { defaultValue: "Subcategory" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {projectIsolatedEligibleMicroSubcategories.map((subcategory) => (
                        <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                          {subcategory.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    value={projectMicroLimit}
                    inputMode="numeric"
                    maxLength={maxBudgetAmountInputLength}
                    onChange={(e) => setProjectMicroLimit(formatBudgetAmountInput(e.target.value))}
                    placeholder="0"
                    className={cn(projectIsolatedMicroWouldOverbook && "border-destructive focus-visible:ring-destructive/30")}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={addProjectIsolatedMicroReservation}
                    disabled={!projectMicroCategory || !projectIsolatedMicroSelectedSubcategory || !projectMicroLimit || projectIsolatedMicroWouldOverbook}
                  >
                    {t("common.add", { defaultValue: "Add" })}
                  </Button>
                </div>
                {projectIsolatedMicroNeedsTaxonomyCreate ? (
                  <div className="mt-2 flex items-center justify-between rounded-lg bg-muted/30 p-2 text-sm text-muted-foreground">
                    <span>
                      {t("projects.subcategoryTaxonomyCreateHint", { defaultValue: "You have no available subcategories for this category." })}
                    </span>
                    <Button type="button" variant="outline" onClick={() => setViewMode("taxonomy")}>
                      <ExternalLink className="mr-2 h-4 w-4" /> {t("budgets.manageSubcategories", { defaultValue: "Manage Subcategories" })}
                    </Button>
                  </div>
                ) : null}
                {projectIsolatedMicroSelectedSubcategory ? (
                  <p className={cn("mt-2 text-xs", projectIsolatedMicroWouldOverbook ? "text-destructive" : "text-muted-foreground")}>
                    {t("projects.availableHeadroom", {
                      defaultValue: "{{amount}} available",
                      amount: formatUzs(projectIsolatedMicroSelectedHeadroom.headroom || 0),
                    })}
                  </p>
                ) : null}
                {projectIsolatedSubcategoryAllocations.length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {projectIsolatedSubcategoryAllocations.map((item) => (
                      <div key={item.user_subcategory_id} className="flex items-center justify-between rounded-lg bg-muted/20 px-3 py-2 text-sm">
                        <span>{tCategory(item.category)} - {item.name}</span>
                        <span className="flex items-center gap-2">
                          <CurrencyAmount value={item.limit_amount} format="compact" tooltip="compact" />
                          <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeProjectIsolatedMicroReservation(item.user_subcategory_id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}

          {isOverlayProjectDraft && projectWizardStep === 2 ? (
            <div className="space-y-3">
              <p className="text-sm font-semibold">{t("projects.parentCategories", { defaultValue: "Parent categories" })}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {orderedCategoryOptions.map((category) => {
                  const selected = projectSelectedCategories.includes(category);
                  const headroom = getJitOverlayCategoryHeadroom(category);
                  return (
                    <button
                      type="button"
                      key={category}
                      onClick={() => toggleProjectCategory(category)}
                      className={cn(
                        "flex min-h-16 items-center justify-between rounded-lg border p-3 text-left text-sm transition",
                        selected ? "border-primary bg-primary/10" : "border-border/70 bg-muted/10 hover:bg-muted/30"
                      )}
                    >
                      <span>
                        <span className="block font-medium">{tCategory(category)}</span>
                        <span className={cn("text-xs", headroom.budget ? "text-muted-foreground" : "text-destructive")}>
                          {headroom.budget
                            ? t("projects.availableHeadroom", {
                                defaultValue: "{{amount}} available",
                                amount: formatUzs(headroom.headroom || 0),
                              })
                            : t("projects.overlayCategoryNeedsBudget", { defaultValue: "Add this category to the selected monthly budget before reserving it." })}
                        </span>
                      </span>
                      {selected ? <Check className="h-4 w-4 text-primary" /> : <Circle className="h-4 w-4 text-muted-foreground" />}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}

          {isOverlayProjectDraft && projectWizardStep === 3 ? (
            <div className="space-y-3">
              <div>
                <p className="text-sm font-semibold">{t("projects.currentMonthAllocation", { defaultValue: "Current-month allocation" })}</p>
                <p className="text-xs text-muted-foreground">
                  {t("projects.onlyActiveMonthAllocation", {
                    defaultValue: "Only {{month}} is allocated now. Future months stay untouched.",
                    month: activeBudgetMonthLabel,
                  })}
                </p>
              </div>
              <div className="space-y-2">
                {projectCategoryAllocationRows.map((row) => (
                  <div key={row.category} className="rounded-lg border border-border/70 p-3">
                    <div className="grid gap-2 sm:grid-cols-[1fr_160px] sm:items-center">
                      <div>
                        <p className="text-sm font-medium">{tCategory(row.category)}</p>
                        <p className={cn("text-xs", row.isMissingBudget || row.isOverbooked ? "text-destructive" : "text-muted-foreground")}>
                          {row.isMissingBudget
                            ? t("projects.overlayCategoryNeedsBudget", { defaultValue: "Add this category to the selected monthly budget before reserving it." })
                            : t("projects.availableHeadroom", {
                                defaultValue: "{{amount}} available",
                                amount: formatUzs(row.headroom || 0),
                              })}
                        </p>
                      </div>
                      <Input
                        value={row.input}
                        inputMode="numeric"
                        maxLength={maxBudgetAmountInputLength}
                        onChange={(e) => setProjectCategoryAllocations((current) => ({
                          ...current,
                          [row.category]: formatBudgetAmountInput(e.target.value),
                        }))}
                        className={cn(row.isOverbooked && "border-destructive focus-visible:ring-destructive/30")}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {isOverlayProjectDraft && projectWizardStep === 4 ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-border/70 p-3">
                <p className="text-sm font-semibold">{t("projects.microStructure", { defaultValue: "Micro structure" })}</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_140px_auto]">
                  <Select value={projectMicroCategory || undefined} onValueChange={(value) => {
                    setProjectMicroCategory(value);
                    setProjectMicroSubcategoryId("");
                    setProjectMicroLimit("");
                  }}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("projects.category", { defaultValue: "Category" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {projectSelectedCategories.map((category) => (
                        <SelectItem key={category} value={category}>{tCategory(category)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={projectMicroSubcategoryId || undefined}
                    onValueChange={setProjectMicroSubcategoryId}
                    disabled={!projectMicroBudget || projectEligibleMicroSubcategories.length === 0}
                  >
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue placeholder={t("projects.subcategory", { defaultValue: "Subcategory" })} />
                    </SelectTrigger>
                    <SelectContent className={selectContentClass}>
                      {projectEligibleMicroSubcategories.map((subcategory) => (
                        <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                          {subcategory.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    value={projectMicroLimit}
                    inputMode="numeric"
                    maxLength={maxBudgetAmountInputLength}
                    onChange={(e) => setProjectMicroLimit(formatBudgetAmountInput(e.target.value))}
                    className={cn(projectMicroWouldOverbook && "border-destructive focus-visible:ring-destructive/30")}
                  />
                  <Button type="button" onClick={handleAddProjectMicroReservation} disabled={!projectMicroSubcategoryId || projectMicroWouldOverbook}>
                    <Plus className="mr-2 h-4 w-4" /> {t("common.add", { defaultValue: "Add" })}
                  </Button>
                </div>
                {projectMicroCategory && projectMicroBudget && projectEligibleMicroSubcategories.length === 0 ? (
                  <div className="mt-3 flex flex-col gap-2 rounded-lg border border-dashed border-border/70 p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                    <span>
                      {projectMicroNeedsMonthlyLane
                        ? t("projects.subcategoryMonthlyLaneRequired", { defaultValue: "This month has no available subcategory lane for that category." })
                        : t("projects.subcategoryMonthlyLanesAlreadyAttached", { defaultValue: "All current monthly subcategory lanes for this category are already attached." })}
                    </span>
                    {projectMicroNeedsMonthlyLane ? (
                      <Button type="button" variant="outline" onClick={openProjectMicroTaxonomy}>
                        <ExternalLink className="mr-2 h-4 w-4" /> {t("budgets.manageSubcategories", { defaultValue: "Manage Subcategories" })}
                      </Button>
                    ) : null}
                  </div>
                ) : null}
                {projectMicroSelectedSubcategory ? (
                  <p className={cn("mt-2 text-xs", projectMicroWouldOverbook ? "text-destructive" : "text-muted-foreground")}>
                    {t("projects.availableHeadroom", {
                      defaultValue: "{{amount}} available",
                      amount: formatUzs(projectMicroSelectedHeadroom.headroom || 0),
                    })}
                  </p>
                ) : null}
                {projectSubcategoryReservations.length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {projectSubcategoryReservations.map((item) => (
                      <div key={item.user_subcategory_id} className="flex items-center justify-between rounded-lg bg-muted/20 px-3 py-2 text-sm">
                        <span>{tCategory(item.category)} - {item.name}</span>
                        <span className="flex items-center gap-2">
                          <CurrencyAmount value={item.limit_amount} format="compact" tooltip="compact" />
                          <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeProjectMicroReservation(item.user_subcategory_id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="rounded-lg border border-border/70 p-3">
                <p className="text-sm font-semibold">{t("projects.reviewCurrentReservations", { defaultValue: "Current-month reservations" })}</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <BudgetDialogStat
                    label={t("projects.reservedThisMonth", { defaultValue: "Reserved this month" })}
                    value={<CurrencyAmount value={projectCurrentMonthReservationTotal} format="compact" tooltip="compact" />}
                    icon={Shield}
                  />
                  <BudgetDialogStat
                    label={t("projects.subcategoryReservations", { defaultValue: "Subcategory reservations" })}
                    value={<CurrencyAmount value={projectCurrentMonthMicroReservationTotal} format="compact" tooltip="compact" />}
                    icon={ListTree}
                  />
                </div>
                <div className="mt-2 space-y-2">
                  {projectCategoryAllocationRows.map((row) => (
                    <div key={row.category} className="flex items-center justify-between text-sm">
                      <span>{tCategory(row.category)}</span>
                      <CurrencyAmount value={row.amount || 0} format="compact" tooltip="compact" />
                    </div>
                  ))}
                  {projectSubcategoryReservations.map((item) => (
                    <div key={`review-${item.user_subcategory_id}`} className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>{tCategory(item.category)} - {item.name}</span>
                      <CurrencyAmount value={item.limit_amount || 0} format="compact" tooltip="compact" />
                    </div>
                  ))}
                </div>
                <p className="mt-3 flex gap-2 text-xs text-muted-foreground">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  {t("projects.futureMonthsAllocatedLater", { defaultValue: "Future months will be allocated when those months are set up." })}
                </p>
              </div>
            </div>
          ) : null}

          {!isOverlayProjectDraft ? (
            <div className="rounded-lg border border-border/60 bg-muted/15 p-3 text-sm text-muted-foreground">
              {t("projects.isolatedHelp", { defaultValue: "Isolated projects keep this spending out of monthly budget pressure." })}
            </div>
          ) : null}
          {actionError && <p className="text-sm text-red-600">{actionError}</p>}
        </div>
      </ResponsiveBudgetFormShell>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={subcategoriesOpen}
        onOpenChange={(open) => {
          if (open) {
            setSubcategoriesOpen(true);
          } else {
            closeSubcategories();
          }
        }}
        title={t("budgets.manageSubcategories", { defaultValue: "Manage Subcategories" })}
        description={
          subcategoryTargetBudget
            ? `${tCategory(subcategoryTargetBudget.category)} • ${formatBudgetMonth(subcategoryTargetBudget.budgetYear, subcategoryTargetBudget.budgetMonth)}`
            : t("budgets.manageSubcategoriesDesc", { defaultValue: "Create and manage child partitions inside this parent budget." })
        }
        footer={
          <Button variant="outline" onClick={closeSubcategories}>
            {t("common.close", { defaultValue: "Close" })}
          </Button>
        }
        dialogClassName="sm:max-w-[720px]"
      >
        <div className={cn("space-y-4", useBottomSheetForms && "pb-1")}>
          <div className="grid gap-3 sm:grid-cols-3">
            <BudgetDialogStat
              label={t("budgets.parentBuffer", { defaultValue: "Parent buffer" })}
              value={<CurrencyAmount value={managedSubcategoryBuffer} format="compact" tooltip="compact" className="flex items-baseline gap-1" />}
              icon={Layers3}
            />
            <BudgetDialogStat
              label={t("budgets.subcategoryLimitTotal", { defaultValue: "Subcategory limits" })}
              value={<CurrencyAmount value={managedSubcategoryLimitTotal} format="compact" tooltip="compact" className="flex items-baseline gap-1" />}
              icon={ListTree}
            />
            <BudgetDialogStat
              label={t("budgets.unspecifiedSpending", { defaultValue: "Unspecified spending" })}
              value={<CurrencyAmount value={managedUnspecifiedSpent} format="compact" tooltip="compact" className="flex items-baseline gap-1" />}
              icon={ReceiptText}
            />
          </div>

          <div className="rounded-lg border border-border/60 bg-muted/15 p-4">
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
            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_180px_auto]">
              <Select value={reallocationSourceId} onValueChange={setReallocationSourceId}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue placeholder={t("budgets.reallocateFrom", { defaultValue: "From" })} />
                </SelectTrigger>
                <SelectContent className={selectContentClass}>
                  <SelectItem value="buffer">
                    {t("budgets.parentBuffer", { defaultValue: "Parent buffer" })} - {formatUzs(managedSubcategoryBuffer)}
                  </SelectItem>
                  {managedSubcategories
                    .filter((subcategory) => String(subcategory.id) !== String(reallocationTargetId) && subcategory.monthly_limit)
                    .map((subcategory) => (
                      <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                        {subcategory.name} - {formatUzs(Math.max(Number(subcategory.remaining || 0), 0))}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <Select value={reallocationTargetId || undefined} onValueChange={setReallocationTargetId}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue placeholder={t("budgets.reallocateTo", { defaultValue: "To" })} />
                </SelectTrigger>
                <SelectContent className={selectContentClass}>
                  {managedSubcategories.map((subcategory) => (
                    <SelectItem key={subcategory.id} value={String(subcategory.id)}>
                      {subcategory.name}
                      {subcategory.is_over_limit ? ` - ${t("budgets.needsRepair", { defaultValue: "Needs repair" })}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                value={reallocationAmount}
                onChange={(e) => setReallocationAmount(formatBudgetAmountInput(e.target.value))}
                placeholder={t("budgets.amount", { defaultValue: "Amount" })}
                inputMode="numeric"
              />
              <Button
                type="button"
                onClick={handleReallocateSubcategory}
                disabled={reallocateSubcategoryMutation.isPending || !reallocationTargetId || !reallocationAmount}
              >
                <ArrowRightLeft className="mr-2 h-4 w-4" />
                {t("budgets.reallocate", { defaultValue: "Reallocate" })}
              </Button>
            </div>
          </div>

          <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
            <p className="text-sm font-semibold">{t("budgets.addSubcategory", { defaultValue: "Add subcategory" })}</p>
            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_140px_auto]">
              <Popover open={subcategoryComboboxOpen} onOpenChange={setSubcategoryComboboxOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={subcategoryComboboxOpen}
                    className="justify-between"
                  >
                    {subcategoryName || t("budgets.subcategoryName", { defaultValue: "Subcategory name" })}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[300px] p-0" align="start">
                  <Command>
                    <CommandInput 
                      placeholder={t("budgets.searchSubcategories", { defaultValue: "Search subcategories..." })} 
                      value={subcategoryName}
                      onValueChange={(val) => {
                        setSubcategoryName(val);
                        setSubcategoryExistingId(null);
                      }}
                    />
                    <CommandList>
                      <CommandEmpty>
                        {subcategoryName.trim() ? (
                          <Button
                            variant="ghost"
                            className="w-full justify-start font-normal text-sm"
                            onClick={() => {
                              setSubcategoryExistingId(null);
                              setSubcategoryComboboxOpen(false);
                            }}
                          >
                            <Plus className="mr-2 h-4 w-4" />
                            {t("budgets.createNew", { defaultValue: "Create new" })}: &quot;{subcategoryName}&quot;
                          </Button>
                        ) : (
                          t("common.noResults", { defaultValue: "No results found." })
                        )}
                      </CommandEmpty>
                      {Array.isArray(globalSubcategoriesQuery.data) && globalSubcategoriesQuery.data.filter(
                        (tag) => !subcategoriesQuery.data?.some((existing) => existing.name.toLowerCase() === tag.name.toLowerCase())
                      ).length > 0 && (
                        <CommandGroup heading={t("budgets.existingTags", { defaultValue: "Existing Tags" })}>
                          {globalSubcategoriesQuery.data
                            .filter((tag) => !subcategoriesQuery.data?.some((existing) => existing.name.toLowerCase() === tag.name.toLowerCase()))
                            .map((tag) => (
                              <CommandItem
                                key={tag.id}
                                value={tag.name}
                                onSelect={() => {
                                  setSubcategoryName(tag.name);
                                  setSubcategoryExistingId(tag.id);
                                  setSubcategoryComboboxOpen(false);
                                }}
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    subcategoryExistingId === tag.id ? "opacity-100" : "opacity-0"
                                  )}
                                />
                                {tag.name}
                              </CommandItem>
                            ))}
                        </CommandGroup>
                      )}
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
              <Input
                value={subcategoryLimit}
                onChange={(e) => setSubcategoryLimit(formatBudgetAmountInput(e.target.value))}
                placeholder={t("budgets.monthlyLimit")}
                inputMode="numeric"
              />
              <Select value={subcategoryIsActive} onValueChange={setSubcategoryIsActive}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className={selectContentClass}>
                  <SelectItem value="true">{t("common.active", { defaultValue: "Active" })}</SelectItem>
                  <SelectItem value="false">{t("common.inactive", { defaultValue: "Inactive" })}</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={handleCreateSubcategory} disabled={createSubcategoryMutation.isPending || !subcategoryName.trim()}>
                <Plus className="mr-2 h-4 w-4" />
                {t("common.add", { defaultValue: "Add" })}
              </Button>
            </div>
          </div>

          <div className="space-y-3">
            {subcategoriesQuery.isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <LoadingSpinner className="h-4 w-4" />
                <span>{t("budgets.previewLoading", { defaultValue: "Loading planning preview..." })}</span>
              </div>
            ) : managedSubcategories.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("budgets.noSubcategoriesYet", { defaultValue: "No subcategories configured yet." })}</p>
            ) : (
              managedSubcategories.map((subcategory) => (
                <div
                  key={subcategory.id}
                  className={cn(
                    "rounded-2xl border bg-background/80 p-4",
                    subcategory.is_over_limit ? "border-destructive/40 bg-destructive/5" : "border-border/60",
                  )}
                >
                  {editingSubcategoryId === subcategory.id ? (
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_140px_auto_auto]">
                      <Input value={editingSubcategoryName} onChange={(e) => setEditingSubcategoryName(e.target.value)} />
                      <Input value={editingSubcategoryLimit} onChange={(e) => setEditingSubcategoryLimit(formatBudgetAmountInput(e.target.value))} inputMode="numeric" />
                      <Select value={editingSubcategoryIsActive} onValueChange={setEditingSubcategoryIsActive}>
                        <SelectTrigger className={selectTriggerClass}><SelectValue /></SelectTrigger>
                        <SelectContent className={selectContentClass}>
                          <SelectItem value="true">{t("common.active", { defaultValue: "Active" })}</SelectItem>
                          <SelectItem value="false">{t("common.inactive", { defaultValue: "Inactive" })}</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button onClick={handleUpdateSubcategory} disabled={updateSubcategoryMutation.isPending || !editingSubcategoryName.trim()}>
                        {t("common.save")}
                      </Button>
                      <Button variant="outline" onClick={() => setEditingSubcategoryId(null)}>
                        {t("common.cancel")}
                      </Button>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                          <p className="truncate font-medium">{subcategory.name}</p>
                          {subcategory.is_over_limit ? (
                            <Badge variant="destructive" className="rounded-full px-2 py-0 text-[10px]">
                              <AlertTriangle className="mr-1 h-3 w-3" />
                              {t("budgets.needsRepair", { defaultValue: "Needs repair" })}
                            </Badge>
                          ) : null}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {subcategory.is_active ? t("common.active", { defaultValue: "Active" }) : t("common.inactive", { defaultValue: "Inactive" })}
                          {subcategory.monthly_limit ? ` • ${formatUzs(subcategory.monthly_limit)}` : ""}
                          {` • ${t("budgets.spentLabel", { defaultValue: "Spent" })}: ${formatUzs(subcategory.spent || 0)}`}
                          {subcategory.remaining !== null && subcategory.remaining !== undefined
                            ? ` • ${t("budgets.remainingLabel", { defaultValue: "Remaining" })}: ${formatUzs(subcategory.remaining)}`
                            : ""}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {subcategory.is_over_limit ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setReallocationTargetId(String(subcategory.id));
                              setReallocationSourceId("buffer");
                              setReallocationAmount(formatBudgetAmountInput(String(Math.abs(Number(subcategory.remaining || 0)))));
                            }}
                          >
                            <ArrowRightLeft className="mr-2 h-4 w-4" />
                            {t("budgets.reallocate", { defaultValue: "Reallocate" })}
                          </Button>
                        ) : null}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingSubcategoryId(subcategory.id);
                            setEditingSubcategoryName(subcategory.name || "");
                            setEditingSubcategoryLimit(subcategory.monthly_limit ? formatBudgetAmountInput(String(subcategory.monthly_limit)) : "");
                            setEditingSubcategoryIsActive(subcategory.is_active ? "true" : "false");
                          }}
                        >
                          {t("common.edit", { defaultValue: "Edit" })}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => deleteSubcategoryMutation.mutate({ subcategoryId: subcategory.id, budgetId: subcategoryTargetBudget?.id })}
                          disabled={deleteSubcategoryMutation.isPending}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          {t("common.delete", { defaultValue: "Delete" })}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {actionError && <p className="text-sm text-red-600">{actionError}</p>}
        </div>
      </ResponsiveBudgetFormShell>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={addOpen}
        onOpenChange={setAddOpen}
        title={t("budgets.addDialogTitle")}
        description={t("budgets.addDialogDesc")}
        footer={addBudgetFooter}
      >
          <div className={cn("space-y-3", useBottomSheetForms && "pb-1")}>
            <div className="space-y-1.5">
              <label>{t("budgets.budgetMonthLabel")}</label>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-xs font-normal text-muted-foreground">{t("budgets.yearLabel")}</label>
                  <Select
                    value={String(addBudgetYear)}
                    onValueChange={(value) => {
                      const nextYear = Number(value);
                      setAddBudgetYear(nextYear);
                      const maxMonthForYear = nextYear === currentYear + 5 ? currentMonth : 12;
                      setAddBudgetMonth((prev) => Math.min(prev, maxMonthForYear));
                    }}
                  >
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent
                      className={selectContentClass}
                      position="popper"
                      side="bottom"
                    >
                      {budgetYearOptions.map((year) => (
                        <SelectItem key={year} value={String(year)}>
                          {year}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-normal text-muted-foreground">{t("budgets.monthLabel")}</label>
                  <Select value={String(addBudgetMonth)} onValueChange={(value) => setAddBudgetMonth(Number(value))}>
                    <SelectTrigger className={selectTriggerClass}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent
                      className={selectContentClass}
                      position="popper"
                      side="bottom"
                    >
                      {visibleMonthOptions.map((option) => (
                        <SelectItem key={option.value} value={String(option.value)}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <div className="space-y-1.5">
              <label>{t("expenses.category")}</label>
              <Select value={addCategory || undefined} onValueChange={setAddCategory}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue placeholder={t("budgets.selectCategory")} />
                </SelectTrigger>
                <SelectContent
                  className={selectContentClass}
                  position="popper"
                  side="bottom"
                >
                  {orderedCategoryOptions.map((c) => {
                    const Icon = categoryIconMap[c] || Circle;
                    return (
                      <SelectItem key={c} value={c}>
                        <div className="flex flex-col gap-1 py-1">
                          <div className="flex items-center gap-2 font-medium">
                            <Icon className="h-4 w-4 text-muted-foreground" />
                            <span>{tCategory(c)}</span>
                          </div>
                          <span className="text-mobile-caption text-muted-foreground leading-tight">
                            {t(`categories_desc.${c}`)}
                          </span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label>{t("budgets.monthlyLimit")}</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="off"
                maxLength={maxBudgetAmountInputLength}
                className={inputBaseClass}
                value={addLimit}
                onChange={(e) => setAddLimit(formatBudgetAmountInput(e.target.value))}
              />
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
      </ResponsiveBudgetFormShell>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={updateOpen}
        onOpenChange={setUpdateOpen}
        title={t("budgets.updateDialogTitle")}
        description={
          selectedBudget
            ? `${t("budgets.updateDialogDesc", { category: tCategory(selectedBudget.category) })} (${formatBudgetMonth(selectedBudget.budgetYear, selectedBudget.budgetMonth)})`
            : ""
        }
        footer={updateBudgetFooter}
      >
          <div className={cn("space-y-2", useBottomSheetForms && "pb-1")}>
            <label>{t("budgets.newLimit")}</label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="off"
              maxLength={maxBudgetAmountInputLength}
              className={inputBaseClass}
              value={newLimit}
              onChange={(e) => setNewLimit(formatBudgetAmountInput(e.target.value))}
            />
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
      </ResponsiveBudgetFormShell>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={parentReallocateOpen}
        onOpenChange={setParentReallocateOpen}
        title={t("budgets.reallocateDialogTitle", { defaultValue: "Reallocate Limits" })}
        description={
          parentReallocateSourceBudget
            ? t("budgets.reallocateDialogDesc", { category: tCategory(parentReallocateSourceBudget.category), defaultValue: "Move available limits to another category." })
            : ""
        }
        footer={parentReallocateFooter}
      >
          <div className={cn("space-y-4", useBottomSheetForms && "pb-1")}>
            <div className="space-y-1.5 rounded-lg border border-border/60 bg-muted/20 p-3">
              <p className="text-sm font-medium text-muted-foreground">{t("budgets.sourceAvailable", { defaultValue: "Available to move" })}</p>
              <CurrencyAmount
                value={parentReallocateSourceBudget?.remaining || 0}
                format="display"
                className="text-lg font-semibold text-foreground"
              />
            </div>
            <div className="space-y-1.5">
              <label>{t("budgets.targetCategory", { defaultValue: "Target Category" })}</label>
              <Select value={parentReallocateTargetCategory || undefined} onValueChange={setParentReallocateTargetCategory}>
                <SelectTrigger className={selectTriggerClass}>
                  <SelectValue placeholder={t("budgets.selectTargetCategory", { defaultValue: "Select target category..." })} />
                </SelectTrigger>
                <SelectContent className={selectContentClass} position="popper" side="bottom">
                  {orderedCategoryOptions.filter(c => c !== parentReallocateSourceBudget?.category).map((c) => {
                    const Icon = categoryIconMap[c] || Circle;
                    return (
                      <SelectItem key={c} value={c}>
                        <div className="flex flex-col gap-1 py-1">
                          <div className="flex items-center gap-2 font-medium">
                            <Icon className="h-4 w-4 text-muted-foreground" />
                            <span>{tCategory(c)}</span>
                          </div>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label>{t("budgets.amountToMove", { defaultValue: "Amount to move" })}</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="off"
                maxLength={maxBudgetAmountInputLength}
                className={inputBaseClass}
                value={parentReallocateAmount}
                onChange={(e) => setParentReallocateAmount(formatBudgetAmountInput(e.target.value))}
              />
            </div>
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </div>
      </ResponsiveBudgetFormShell>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={t("budgets.deleteDialogTitle")}
        description={
          selectedBudget
            ? `${t("budgets.deleteDialogDesc", { category: tCategory(selectedBudget.category) })} (${formatBudgetMonth(selectedBudget.budgetYear, selectedBudget.budgetMonth)})`
            : ""
        }
        onConfirm={handleDeleteBudget}
        confirmText={t("budgets.delete")}
        cancelText={t("common.cancel")}
        isConfirming={isDeletingBudget}
        error={actionError}
      />

      <ConfirmDialog
        open={projectLifecycleOpen}
        onOpenChange={closeProjectLifecycleDialog}
        title={projectLifecycleTitle}
        description={projectLifecycleDescription}
        onConfirm={handleConfirmProjectLifecycle}
        confirmText={projectLifecycleConfirmText}
        cancelText={t("common.cancel", { defaultValue: "Cancel" })}
        confirmVariant={projectLifecycleIsComplete ? "default" : "outline"}
        isConfirming={isProjectLifecyclePending}
      >
        {projectLifecycleTarget ? (
          <div className="rounded-md border border-border/70 bg-muted/20 p-3 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">{projectLifecycleTarget.title}</p>
            <p className="mt-1">
              {projectLifecycleIsComplete
                ? t("projects.completeProjectSweepNote", { defaultValue: "Current and future overlay reservations will be reduced to actual spending. Past months stay unchanged." })
                : projectLifecycleIsPause
                  ? t("projects.pauseProjectHoldNote", { defaultValue: "Reserved limits stay held while project expenses are paused." })
                  : t("projects.resumeProjectSpendNote", { defaultValue: "The project can receive linked expenses again after resume." })}
            </p>
          </div>
        ) : null}
      </ConfirmDialog>

      <ConfigureSurvivalDialog
        open={showSurvivalDialog}
        onOpenChange={setShowSurvivalDialog}
        budgetYear={summaryTarget.year}
        budgetMonth={summaryTarget.month}
        initialEnabled={monthSummary?.borrowing_survival?.enabled || false}
        initialCap={monthSummary?.borrowing_survival?.monthly_cap || 0}
      />

      <Dialog open={showCashBackingDetails} onOpenChange={setShowCashBackingDetails}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t("budgets.cashBackingDetailsTitle", { defaultValue: "Cash Backing Receipt" })}</DialogTitle>
            <DialogDescription>
              {t("budgets.cashBackingDetailsDesc", { defaultValue: "How your wallet balances translate into your plan's available cash backing." })}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 font-mono text-sm py-4">
            <div className="flex justify-between items-start group">
              <div className="space-y-1">
                <p className="font-medium">{t("budgets.receiptFreeMoney", { defaultValue: "Free money in wallets" })}</p>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{t("budgets.receiptFreeMoneyHint", { defaultValue: "Excluding protected goals" })}</p>
              </div>
              <CurrencyAmount value={monthSummary?.free_money_now || 0} format="display" className="font-semibold" />
            </div>
            
            <div className="flex justify-between items-start group">
              <div className="space-y-1">
                <p className="font-medium text-emerald-600 dark:text-emerald-400">+ {t("budgets.receiptSpent", { defaultValue: "Cash spent on budgets" })}</p>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{t("budgets.receiptSpentHint", { defaultValue: "Added back to prevent double counting" })}</p>
              </div>
              <CurrencyAmount value={monthSummary?.valid_budget_spent || 0} format="display" className="font-semibold text-emerald-600 dark:text-emerald-400" />
            </div>

            <div className="flex justify-between items-start group">
              <div className="space-y-1">
                <p className="font-medium text-amber-600 dark:text-amber-400">- {t("budgets.receiptObligations", { defaultValue: "Debt obligations" })}</p>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{t("budgets.receiptObligationsHint", { defaultValue: "Reserved for pure cash debts" })}</p>
              </div>
              <CurrencyAmount value={monthSummary?.cash_obligation_reserve_total || 0} format="display" className="font-semibold text-amber-600 dark:text-amber-400" />
            </div>

            <div className="border-t-2 border-dashed border-border pt-4">
              <div className="flex justify-between items-center text-base">
                <p className="font-bold">{t("budgets.receiptTotal", { defaultValue: "Total Cash Backing" })}</p>
                <CurrencyAmount value={monthSummary?.cash_backing_total || 0} format="display" className="font-bold" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCashBackingDetails(false)}>{t("common.close", { defaultValue: "Close" })}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ResponsiveBudgetFormShell
        compact={useBottomSheetForms}
        open={projectDeletionOpen}
        onOpenChange={closeProjectDeletionResolution}
        title={t("projects.deleteResolutionTitle", { defaultValue: "Delete project?" })}
        description={
          projectDeletionTarget
            ? t("projects.deleteResolutionDesc", {
                defaultValue: "{{title}} has linked expenses. Choose what should happen to them.",
                title: projectDeletionTarget.title,
              })
            : ""
        }
        footer={
          <Button
            variant="outline"
            onClick={() => closeProjectDeletionResolution(false)}
            disabled={isProjectDeletionPending}
          >
            {t("common.cancel", { defaultValue: "Cancel" })}
          </Button>
        }
      >
        <div className={cn("space-y-4", useBottomSheetForms && "pb-1")}>
          <div className="grid gap-3 sm:grid-cols-2">
            <BudgetDialogStat
              label={t("projects.linkedExpenses", { defaultValue: "Linked expenses" })}
              value={projectDeletionLinkedCount}
              icon={ReceiptText}
            />
            <BudgetDialogStat
              label={t("projects.linkedExpenseTotal", { defaultValue: "Linked total" })}
              value={`${formatUzs(projectDeletionLinkedTotal)} UZS`}
              icon={ChartColumn}
            />
          </div>

          <div className="space-y-3">
            <div className="rounded-md border border-border/70 bg-background/70 p-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold">{t("projects.archiveOption", { defaultValue: "Archive project" })}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("projects.archiveOptionDesc", { defaultValue: "Hide the project from daily planning while keeping linked expenses attached." })}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleResolveProjectDeletion(PROJECT_DELETE_ACTIONS.ARCHIVE)}
                  disabled={isProjectDeletionPending}
                >
                  <Archive className="mr-2 h-4 w-4" />
                  {t("common.archive", { defaultValue: "Archive" })}
                </Button>
              </div>
            </div>

            <div className="rounded-md border border-border/70 bg-background/70 p-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold">{t("projects.detachExpensesOption", { defaultValue: "Detach expenses" })}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("projects.detachExpensesOptionDesc", { defaultValue: "Keep the expenses in your budgets as standalone spending, then delete the project." })}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleResolveProjectDeletion(PROJECT_DELETE_ACTIONS.DETACH_EXPENSES)}
                  disabled={isProjectDeletionPending}
                >
                  <Unlink className="mr-2 h-4 w-4" />
                  {t("projects.detachExpenses", { defaultValue: "Detach" })}
                </Button>
              </div>
            </div>

            <div className="rounded-md border border-destructive/35 bg-destructive/5 p-3">
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <ShieldX className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
                  <div className="min-w-0">
                    <p className="font-semibold text-destructive">
                      {t("projects.cascadeVoidOption", { defaultValue: "Delete linked expenses and project" })}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {t("projects.cascadeVoidOptionDesc", { defaultValue: "These expenses will no longer count in your budgets or wallet balances. Accounting history is preserved for accuracy." })}
                    </p>
                  </div>
                </div>
                <Input
                  value={projectDeletionConfirmTitle}
                  onChange={(event) => setProjectDeletionConfirmTitle(event.target.value)}
                  placeholder={projectDeletionTarget?.title || ""}
                  aria-label={t("projects.confirmProjectName", { defaultValue: "Confirm project name" })}
                />
                <Button
                  type="button"
                  variant="destructive"
                  className="w-full sm:w-auto"
                  onClick={() => handleResolveProjectDeletion(PROJECT_DELETE_ACTIONS.CASCADE_VOID)}
                  disabled={isProjectDeletionPending || !canCascadeVoidProject}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("projects.deleteLinkedExpenses", { defaultValue: "Delete linked expenses" })}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </ResponsiveBudgetFormShell>

      <EditProjectDialog
        open={!!editProjectModalProject}
        onOpenChange={(open) => {
          if (!open) setEditProjectModalProject(null);
        }}
        project={editProjectModalProject}
      />
    </div>
  );
}





