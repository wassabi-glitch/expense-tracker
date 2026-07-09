import { useCallback, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useBudgetsDataQuery } from "../hooks/useBudgetsDataQuery";
import { useSubcategoriesQuery } from "../hooks/useSubcategoriesQuery";
import {
  createProjectCategoryLimit,
  createProjectSubcategory,
  deleteProjectCategoryLimit,
  deleteProjectSubcategory,
  updateProjectCategoryLimit,
  updateProjectSubcategory,
} from "@/lib/api";
import { localizeApiError } from "@/lib/errorMessages";
import { formatAmountInput, formatUzs } from "@/lib/format";
import { CATEGORIES } from "@/lib/category";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tCategory(category) {
  return category;
}

const orderedCategoryOptions = CATEGORIES.slice().sort((a, b) =>
  a.localeCompare(b)
);

const maxBudgetAmountDigits = 12;

function parseBudgetAmountInput(value) {
  if (!value) return 0;
  const cleaned = String(value).replace(/\s+/g, "").replace(/,/g, "");
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : 0;
}

function formatBudgetAmountInput(raw) {
  return formatAmountInput(raw, maxBudgetAmountDigits);
}

function getBudgetActionErrorMessage(e, t, formatUzsFn) {
  if (e?.status === 429) {
    const wait = Number(e?.retryAfterSeconds || 0);
    if (Number.isFinite(wait) && wait > 0) {
      return t("budgets.tooManyWait", { seconds: wait });
    }
    return t("budgets.tooManySoon");
  }
  if (e?.detail?.code === "budgets.plan_exceeds_backing") {
    return t("budgets.planExceedsBacking", {
      defaultValue:
        "Cannot set this budget. Requested monthly budgets exceed valid backing by {{shortfall}}.",
      shortfall: formatUzsFn(Number(e.detail.shortfall || 0)),
    });
  }
  return localizeApiError(e?.message, t) || t("budgets.requestFailed");
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CategoryLimitEditor({
  project,
  projectIsIsolated,
  categoryBreakdown,
  monthYear,
  monthMonth,
  onMutation,
}) {
  const { t } = useTranslation();
  const [categoryValue, setCategoryValue] = useState("");
  const [categoryLimitValue, setCategoryLimitValue] = useState("");
  const [editingCategory, setEditingCategory] = useState("");
  const [editingCategoryLimit, setEditingCategoryLimit] = useState("");
  const [actionError, setActionError] = useState("");

  // Budget data for overlay headroom
  const budgetsQuery = useBudgetsDataQuery(
    { year: monthYear, month: monthMonth },
    { enabled: !projectIsIsolated }
  );
  const budgets = useMemo(() => budgetsQuery.data || [], [budgetsQuery.data]);

  const getOverlayCategoryHeadroom = useCallback(
    (category, excludeAmount = 0) => {
      const budget =
        budgets.find(
          (item) =>
            item.category === category &&
            Number(item.budgetYear) === Number(monthYear) &&
            Number(item.budgetMonth) === Number(monthMonth)
        ) || null;
      if (!budget) return { budget: null, headroom: 0 };
      const reserved = Number(budget.projectReservedAmount || 0);
      const headroom = Math.max(
        Number(budget.baseLimit || 0) - reserved + Number(excludeAmount || 0),
        0
      );
      return { budget, headroom };
    },
    [budgets, monthMonth, monthYear]
  );

  const categoryHeadroom = useMemo(() => {
    if (projectIsIsolated || !categoryValue) return null;
    return getOverlayCategoryHeadroom(categoryValue);
  }, [categoryValue, getOverlayCategoryHeadroom, projectIsIsolated]);

  const editingCategoryRow = useMemo(
    () =>
      categoryBreakdown.find((item) => item.category === editingCategory) ||
      null,
    [editingCategory, categoryBreakdown]
  );

  const editingCategoryHeadroom = useMemo(() => {
    if (projectIsIsolated || !editingCategory) return null;
    return getOverlayCategoryHeadroom(
      editingCategory,
      Number(editingCategoryRow?.limit_amount || 0)
    );
  }, [
    editingCategory,
    editingCategoryRow,
    getOverlayCategoryHeadroom,
    projectIsIsolated,
  ]);

  const categoryWouldOverbook =
    categoryHeadroom &&
    parseBudgetAmountInput(categoryLimitValue) > 0 &&
    parseBudgetAmountInput(categoryLimitValue) >
      Number(categoryHeadroom.headroom || 0);

  const editingCategoryWouldOverbook =
    editingCategoryHeadroom &&
    parseBudgetAmountInput(editingCategoryLimit) > 0 &&
    parseBudgetAmountInput(editingCategoryLimit) >
      Number(editingCategoryHeadroom.headroom || 0);

  const createMutation = useMutation({
    mutationFn: ({ projectId: pid, payload }) =>
      createProjectCategoryLimit(pid, payload),
    onSuccess: () => {
      setCategoryValue("");
      setCategoryLimitValue("");
      setActionError("");
      onMutation();
    },
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ projectId: pid, category: cat, payload }) =>
      updateProjectCategoryLimit(pid, cat, payload),
    onSuccess: () => {
      setEditingCategory("");
      setEditingCategoryLimit("");
      setActionError("");
      onMutation();
    },
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ projectId: pid, category: cat, budgetYear, budgetMonth }) =>
      deleteProjectCategoryLimit(pid, cat, { budgetYear, budgetMonth }),
    onSuccess: () => onMutation(),
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const handleCreate = async () => {
    if (createMutation.isPending) return;
    setActionError("");
    if (!categoryValue) {
      setActionError(
        t("projects.categoryRequired", { defaultValue: "Choose a category first" })
      );
      return;
    }
    const limitAmount = parseBudgetAmountInput(categoryLimitValue);
    if (
      categoryLimitValue &&
      (!Number.isFinite(limitAmount) || limitAmount <= 0)
    ) {
      setActionError(
        t("projects.categoryLimitInvalid", {
          defaultValue: "Category limit must be greater than zero",
        })
      );
      return;
    }
    if (!projectIsIsolated) {
      if (!categoryHeadroom?.budget) {
        setActionError(
          t("projects.overlayCategoryNeedsBudget", {
            defaultValue:
              "Add this category to the selected monthly budget before reserving it.",
          })
        );
        return;
      }
      if (categoryWouldOverbook) {
        setActionError(
          t("projects.overlayReservationOverbooked", {
            defaultValue:
              "Reservation exceeds available selected-month headroom.",
          })
        );
        return;
      }
    }
    try {
      await createMutation.mutateAsync({
        projectId: project.id,
        payload: {
          category: categoryValue,
          limit_amount: limitAmount,
          budget_year: monthYear,
          budget_month: monthMonth,
        },
      });
    } catch {
      /* error handled in onError */
    }
  };

  const handleUpdate = async () => {
    if (!editingCategory || updateMutation.isPending) return;
    setActionError("");
    const limitAmount = parseBudgetAmountInput(editingCategoryLimit);
    if (
      editingCategoryLimit &&
      (!Number.isFinite(limitAmount) || limitAmount <= 0)
    ) {
      setActionError(
        t("projects.categoryLimitInvalid", {
          defaultValue: "Category limit must be greater than zero",
        })
      );
      return;
    }
    if (!projectIsIsolated && editingCategoryWouldOverbook) {
      setActionError(
        t("projects.overlayReservationOverbooked", {
          defaultValue:
            "Reservation exceeds available selected-month headroom.",
        })
      );
      return;
    }
    try {
      await updateMutation.mutateAsync({
        projectId: project.id,
        category: editingCategory,
        payload: {
          limit_amount: limitAmount,
          budget_year: monthYear,
          budget_month: monthMonth,
        },
      });
    } catch {
      /* handled in onError */
    }
  };

  return (
    <div className="space-y-4">
      {/* Add category */}
      <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
        <p className="text-sm font-semibold">
          {projectIsIsolated
            ? t("projects.addCategoryFunding", {
                defaultValue: "Add parent category funding",
              })
            : t("projects.addCategoryLimit", {
                defaultValue: "Add project category",
              })}
        </p>
        <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto]">
          <Select
            value={categoryValue || undefined}
            onValueChange={setCategoryValue}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("expenses.category")} />
            </SelectTrigger>
            <SelectContent>
              {orderedCategoryOptions.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {tCategory(cat)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={categoryLimitValue}
            onChange={(e) =>
              setCategoryLimitValue(formatBudgetAmountInput(e.target.value))
            }
            inputMode="numeric"
            placeholder={
              projectIsIsolated
                ? t("projects.fundingAmount", {
                    defaultValue: "Funding amount",
                  })
                : t("projects.totalLimit", { defaultValue: "Limit amount" })
            }
          />
          <Button
            onClick={handleCreate}
            disabled={
              createMutation.isPending ||
              categoryWouldOverbook ||
              Boolean(
                categoryValue &&
                  !projectIsIsolated &&
                  !categoryHeadroom?.budget
              )
            }
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("common.add", { defaultValue: "Add" })}
          </Button>
        </div>
        {!projectIsIsolated && categoryValue ? (
          <p
            className={cn(
              "mt-3 text-sm",
              categoryWouldOverbook
                ? "text-destructive"
                : "text-muted-foreground"
            )}
          >
            {categoryHeadroom?.budget
              ? t("projects.overlayCategoryHeadroom", {
                  defaultValue:
                    "Available selected-month headroom: {{amount}}",
                  amount: formatUzs(categoryHeadroom.headroom || 0),
                })
              : t("projects.overlayCategoryNeedsBudget", {
                  defaultValue:
                    "Add this category to the selected monthly budget before reserving it.",
                })}
          </p>
        ) : null}
      </div>

      {/* Category list */}
      <div className="space-y-3">
        <p className="text-sm font-semibold">
          {projectIsIsolated
            ? t("projects.categoryFundingSection", {
                defaultValue: "Parent category funding",
              })
            : t("projects.categoryLimitsSection", {
                defaultValue: "Project categories",
              })}
        </p>
        {categoryBreakdown.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            {projectIsIsolated
              ? t("projects.noCategoryFundingYet", {
                  defaultValue:
                    "No category funding yet. Add one to distribute the isolated stash.",
                })
              : t("projects.noCategoryLimitsYet", {
                  defaultValue:
                    "No project categories yet. Add one to define structure and spending limits.",
                })}
          </div>
        ) : (
          categoryBreakdown.map((catRow) => (
            <div
              key={catRow.category}
              className="rounded-2xl border border-border/60 bg-background/80 p-4"
            >
              {editingCategory === catRow.category ? (
                <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto_auto]">
                  <div className="flex items-center rounded-md border border-border/60 bg-muted/15 px-3 text-sm font-medium">
                    {tCategory(catRow.category)}
                  </div>
                  <Input
                    value={editingCategoryLimit}
                    onChange={(e) =>
                      setEditingCategoryLimit(
                        formatBudgetAmountInput(e.target.value)
                      )
                    }
                    inputMode="numeric"
                  />
                  <Button
                    onClick={handleUpdate}
                    disabled={
                      updateMutation.isPending ||
                      editingCategoryWouldOverbook
                    }
                  >
                    {t("common.save")}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setEditingCategory("");
                      setEditingCategoryLimit("");
                    }}
                  >
                    {t("common.cancel")}
                  </Button>
                  {editingCategoryHeadroom ? (
                    <p
                      className={cn(
                        "lg:col-span-4 text-sm",
                        editingCategoryWouldOverbook
                          ? "text-destructive"
                          : "text-muted-foreground"
                      )}
                    >
                      {t("projects.overlayCategoryHeadroom", {
                        defaultValue:
                          "Available selected-month headroom: {{amount}}",
                        amount: formatUzs(
                          editingCategoryHeadroom.headroom || 0
                        ),
                      })}
                    </p>
                  ) : null}
                </div>
              ) : (
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <p className="font-medium">
                      {tCategory(catRow.category)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {projectIsIsolated && catRow.limit_amount
                        ? `${t("projects.funding", {
                            defaultValue: "Funding",
                          })}: ${formatUzs(catRow.limit_amount)} - `
                        : ""}
                      {t("budgets.spentLabel", {
                        defaultValue: "Spent",
                      })}
                      : {formatUzs(catRow.spent || 0)}
                      {catRow.limit_amount
                        ? ` · ${t("budgets.remainingLabel", {
                            defaultValue: "Remaining",
                          })}: ${formatUzs(catRow.remaining || 0)}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant={
                        catRow.is_over_limit ? "destructive" : "outline"
                      }
                    >
                      {catRow.limit_amount
                        ? formatUzs(catRow.limit_amount)
                        : t("projects.noLimit", {
                            defaultValue: "No limit",
                          })}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditingCategory(catRow.category);
                        setEditingCategoryLimit(
                          catRow.limit_amount
                            ? formatBudgetAmountInput(
                                String(catRow.limit_amount)
                              )
                            : ""
                        );
                      }}
                    >
                      {t("common.edit", { defaultValue: "Edit" })}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      onClick={() =>
                        deleteMutation.mutate({
                          projectId: project.id,
                          category: catRow.category,
                          budgetYear:
                            catRow.budget_year || monthYear,
                          budgetMonth:
                            catRow.budget_month || monthMonth,
                        })
                      }
                      disabled={deleteMutation.isPending}
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

      {actionError ? (
        <p className="text-sm text-red-600">{actionError}</p>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Subcategory editor (overlay global subcategory reservations)
// ---------------------------------------------------------------------------

function OverlaySubcategoryEditor({
  project,
  categoryBreakdown,
  monthYear,
  monthMonth,
  onMutation,
}) {
  const { t } = useTranslation();
  const [subcategoryCategory, setSubcategoryCategory] = useState("");
  const [subcategoryUserSubcategoryId, setSubcategoryUserSubcategoryId] =
    useState("");
  const [subcategoryLimit, setSubcategoryLimit] = useState("");
  const [editingSubcategoryId, setEditingSubcategoryId] = useState(null);
  const [editingSubcategoryLimit, setEditingSubcategoryLimit] = useState("");
  const [actionError, setActionError] = useState("");

  const budgetsQuery = useBudgetsDataQuery(
    { year: monthYear, month: monthMonth },
    { enabled: true }
  );
  const budgets = useMemo(() => budgetsQuery.data || [], [budgetsQuery.data]);

  const overlaySubcategoryBudget = useMemo(
    () =>
      budgets.find(
        (b) =>
          b.category === subcategoryCategory &&
          Number(b.budgetYear) === Number(monthYear) &&
          Number(b.budgetMonth) === Number(monthMonth)
      ) || null,
    [budgets, subcategoryCategory, monthYear, monthMonth]
  );

  const eligibleSubcategoriesQuery = useSubcategoriesQuery(
    overlaySubcategoryBudget?.id,
    {
      enabled:
        Boolean(overlaySubcategoryBudget?.id) && Boolean(subcategoryCategory),
    }
  );
  const eligibleSubcategories = useMemo(
    () => eligibleSubcategoriesQuery.data || [],
    [eligibleSubcategoriesQuery.data]
  );

  const editingSubcategoryRow = useMemo(
    () =>
      categoryBreakdown
        .flatMap((catRow) => catRow.subcategories || [])
        .find(
          (sub) => String(sub.id) === String(editingSubcategoryId)
        ) || null,
    [editingSubcategoryId, categoryBreakdown]
  );

  const editingSubcategoryCategory = editingSubcategoryRow?.category || "";

  const editingSubcategoryBudget = useMemo(
    () =>
      budgets.find(
        (b) =>
          b.category === editingSubcategoryCategory &&
          Number(b.budgetYear) === Number(monthYear) &&
          Number(b.budgetMonth) === Number(monthMonth)
      ) || null,
    [budgets, editingSubcategoryCategory, monthYear, monthMonth]
  );

  // Headroom helpers for overlay subcategories
  const getOverlaySubcategoryHeadroom = useCallback(
    (userSubcategoryId, excludeAmount = 0) => {
      if (!overlaySubcategoryBudget) return null;
      const sub = eligibleSubcategories.find(
        (s) => String(s.id) === String(userSubcategoryId)
      );
      if (!sub) return null;
      return {
        subcategory: sub,
        headroom: Math.max(
          Number(sub.monthly_limit || 0) -
            Number(sub.projectReservedAmount || 0) +
            Number(excludeAmount || 0),
          0
        ),
      };
    },
    [eligibleSubcategories, overlaySubcategoryBudget]
  );

  const getEditingSubcategoryHeadroom = useCallback(
    (userSubcategoryId, excludeAmount = 0) => {
      if (!editingSubcategoryBudget) return null;
      const budgetSubs = editingSubcategoryBudget?.subcategories || [];
      const sub = budgetSubs.find(
        (s) => String(s.user_subcategory_id) === String(userSubcategoryId)
      );
      if (!sub) return null;
      return {
        subcategory: sub,
        headroom: Math.max(
          Number(sub.monthly_limit || 0) -
            Number(sub.projectReservedAmount || 0) +
            Number(excludeAmount || 0),
          0
        ),
      };
    },
    [editingSubcategoryBudget]
  );

  const subcategoryHeadroom = useMemo(() => {
    if (!subcategoryUserSubcategoryId) return null;
    return getOverlaySubcategoryHeadroom(subcategoryUserSubcategoryId);
  }, [getOverlaySubcategoryHeadroom, subcategoryUserSubcategoryId]);

  const editingSubcategoryHeadroom = useMemo(() => {
    if (!editingSubcategoryRow?.user_subcategory_id) return null;
    return getEditingSubcategoryHeadroom(
      editingSubcategoryRow.user_subcategory_id,
      Number(editingSubcategoryRow?.limit_amount || 0)
    );
  }, [editingSubcategoryRow, getEditingSubcategoryHeadroom]);

  const subcategoryWouldOverbook =
    subcategoryHeadroom &&
    parseBudgetAmountInput(subcategoryLimit) > 0 &&
    parseBudgetAmountInput(subcategoryLimit) >
      Number(subcategoryHeadroom.headroom || 0);

  const editingSubcategoryWouldOverbook =
    editingSubcategoryHeadroom &&
    parseBudgetAmountInput(editingSubcategoryLimit) > 0 &&
    parseBudgetAmountInput(editingSubcategoryLimit) >
      Number(editingSubcategoryHeadroom.headroom || 0);

  const createMutation = useMutation({
    mutationFn: ({ projectId: pid, payload }) =>
      createProjectSubcategory(pid, payload),
    onSuccess: () => {
      setSubcategoryCategory("");
      setSubcategoryUserSubcategoryId("");
      setSubcategoryLimit("");
      setActionError("");
      onMutation();
    },
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ projectId: pid, subcategoryId: sid, payload }) =>
      updateProjectSubcategory(pid, sid, payload),
    onSuccess: () => {
      setEditingSubcategoryId(null);
      setEditingSubcategoryLimit("");
      setActionError("");
      onMutation();
    },
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ projectId: pid, subcategoryId: sid }) =>
      deleteProjectSubcategory(pid, sid),
    onSuccess: () => onMutation(),
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const handleCreate = async () => {
    if (createMutation.isPending) return;
    setActionError("");
    if (!subcategoryCategory) {
      setActionError(
        t("projects.categoryRequired", {
          defaultValue: "Choose a category first",
        })
      );
      return;
    }
    if (!subcategoryUserSubcategoryId) {
      setActionError(
        t("projects.globalSubcategoryRequired", {
          defaultValue: "Choose a monthly budget subcategory first",
        })
      );
      return;
    }
    const limitAmount = parseBudgetAmountInput(subcategoryLimit);
    if (!subcategoryLimit) {
      setActionError(
        t("projects.projectSubcategoryLimitInvalid", {
          defaultValue:
            "Project subcategory limit must be greater than zero",
        })
      );
      return;
    }
    if (!Number.isFinite(limitAmount) || limitAmount <= 0) {
      setActionError(
        t("projects.projectSubcategoryLimitInvalid", {
          defaultValue:
            "Project subcategory limit must be greater than zero",
        })
      );
      return;
    }
    if (subcategoryWouldOverbook) {
      setActionError(
        t("projects.overlayReservationOverbooked", {
          defaultValue:
            "Reservation exceeds available selected-month headroom.",
        })
      );
      return;
    }
    try {
      await createMutation.mutateAsync({
        projectId: project.id,
        payload: {
          category: subcategoryCategory,
          user_subcategory_id: Number(subcategoryUserSubcategoryId),
          limit_amount: limitAmount,
          budget_year: monthYear,
          budget_month: monthMonth,
        },
      });
    } catch {
      /* handled in onError */
    }
  };

  const handleUpdate = async () => {
    if (!editingSubcategoryId || updateMutation.isPending) return;
    setActionError("");
    const limitAmount = parseBudgetAmountInput(editingSubcategoryLimit);
    if (!editingSubcategoryLimit) {
      setActionError(
        t("projects.projectSubcategoryLimitInvalid", {
          defaultValue:
            "Project subcategory limit must be greater than zero",
        })
      );
      return;
    }
    if (!Number.isFinite(limitAmount) || limitAmount <= 0) {
      setActionError(
        t("projects.projectSubcategoryLimitInvalid", {
          defaultValue:
            "Project subcategory limit must be greater than zero",
        })
      );
      return;
    }
    if (!editingSubcategoryHeadroom?.subcategory) {
      setActionError(
        t("projects.overlaySubcategoryHeadroomLoading", {
          defaultValue: "Monthly subcategory headroom is still loading.",
        })
      );
      return;
    }
    if (editingSubcategoryWouldOverbook) {
      setActionError(
        t("projects.overlayReservationOverbooked", {
          defaultValue:
            "Reservation exceeds available selected-month headroom.",
        })
      );
      return;
    }
    try {
      await updateMutation.mutateAsync({
        projectId: project.id,
        subcategoryId: editingSubcategoryId,
        payload: { limit_amount: limitAmount },
      });
    } catch {
      /* handled in onError */
    }
  };

  const hasSubcategories = categoryBreakdown.some(
    (catRow) => (catRow.subcategories || []).length > 0
  );

  return (
    <div className="space-y-4">
      {/* Add overlay subcategory */}
      <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
        <p className="text-sm font-semibold">
          {t("projects.addOverlaySubcategory", {
            defaultValue: "Reserve a global monthly subcategory",
          })}
        </p>
        <div className="mt-3 grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)_180px_auto]">
          <Select
            value={subcategoryCategory || undefined}
            onValueChange={(value) => {
              setSubcategoryCategory(value);
              setSubcategoryUserSubcategoryId("");
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("expenses.category")} />
            </SelectTrigger>
            <SelectContent>
              {categoryBreakdown.map((catRow) => (
                <SelectItem key={catRow.category} value={catRow.category}>
                  {tCategory(catRow.category)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={subcategoryUserSubcategoryId || undefined}
            onValueChange={setSubcategoryUserSubcategoryId}
            disabled={
              !subcategoryCategory ||
              !overlaySubcategoryBudget ||
              eligibleSubcategories.length === 0
            }
          >
            <SelectTrigger>
              <SelectValue
                placeholder={t("projects.chooseGlobalSubcategory", {
                  defaultValue: "Choose monthly subcategory",
                })}
              />
            </SelectTrigger>
            <SelectContent>
              {eligibleSubcategories.map((sub) => (
                <SelectItem key={sub.id} value={String(sub.id)}>
                  {sub.name} · {formatUzs(sub.monthly_limit || 0)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={subcategoryLimit}
            onChange={(e) =>
              setSubcategoryLimit(formatBudgetAmountInput(e.target.value))
            }
            inputMode="numeric"
            placeholder={t("projects.reservationAmount", {
              defaultValue: "Reservation",
            })}
          />
          <Button
            onClick={handleCreate}
            disabled={
              createMutation.isPending || subcategoryWouldOverbook
            }
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("common.add", { defaultValue: "Add" })}
          </Button>
        </div>
        {subcategoryCategory && !overlaySubcategoryBudget ? (
          <p className="mt-3 text-sm text-muted-foreground">
            {t("projects.overlaySubcategoryNeedsBudget", {
              defaultValue:
                "Add this category to the selected monthly budget before reserving its subcategories.",
            })}
          </p>
        ) : null}
        {subcategoryCategory &&
        overlaySubcategoryBudget &&
        eligibleSubcategories.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">
            {t("projects.overlaySubcategoryNeedsLane", {
              defaultValue:
                "Add an eligible subcategory lane to this monthly budget first, or all current lanes are already attached.",
            })}
          </p>
        ) : null}
        {subcategoryHeadroom ? (
          <p
            className={cn(
              "mt-3 text-sm",
              subcategoryWouldOverbook
                ? "text-destructive"
                : "text-muted-foreground"
            )}
          >
            {t("projects.overlaySubcategoryHeadroom", {
              defaultValue: "Available lane headroom: {{amount}}",
              amount: formatUzs(subcategoryHeadroom.headroom || 0),
            })}
          </p>
        ) : null}
      </div>

      {/* Overlay subcategory list */}
      <div className="space-y-3">
        <p className="text-sm font-semibold">
          {t("projects.overlaySubcategoriesSection", {
            defaultValue: "Global subcategory reservations",
          })}
        </p>
        {!hasSubcategories ? (
          <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            {t("projects.noOverlaySubcategoriesYet", {
              defaultValue:
                "No global subcategory reservations for this month yet.",
            })}
          </div>
        ) : (
          categoryBreakdown.map((catRow) => (
            <div
              key={`${catRow.category}-overlay-subcategories`}
              className="rounded-2xl border border-border/60 bg-background/80 p-4"
            >
              <p className="text-sm font-semibold">
                {tCategory(catRow.category)}
              </p>
              <div className="mt-3 space-y-3">
                {(catRow.subcategories || []).map((sub) => (
                  <div
                    key={sub.id}
                    className="rounded-xl border border-border/50 bg-muted/15 p-3"
                  >
                    {editingSubcategoryId === sub.id ? (
                      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_auto_auto]">
                        <div className="flex min-h-9 items-center rounded-md border border-border/60 px-3 text-sm">
                          {sub.name}
                        </div>
                        <Input
                          value={editingSubcategoryLimit}
                          onChange={(e) =>
                            setEditingSubcategoryLimit(
                              formatBudgetAmountInput(e.target.value)
                            )
                          }
                          inputMode="numeric"
                        />
                        <Button
                          onClick={handleUpdate}
                          disabled={
                            updateMutation.isPending ||
                            editingSubcategoryWouldOverbook ||
                            Boolean(
                              !editingSubcategoryHeadroom?.subcategory
                            )
                          }
                        >
                          {t("common.save")}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setEditingSubcategoryId(null);
                            setEditingSubcategoryLimit("");
                          }}
                        >
                          {t("common.cancel")}
                        </Button>
                        {editingSubcategoryHeadroom ? (
                          <p
                            className={cn(
                              "lg:col-span-4 text-sm",
                              editingSubcategoryWouldOverbook
                                ? "text-destructive"
                                : "text-muted-foreground"
                            )}
                          >
                            {t("projects.overlaySubcategoryHeadroom", {
                              defaultValue:
                                "Available lane headroom: {{amount}}",
                              amount: formatUzs(
                                editingSubcategoryHeadroom.headroom || 0
                              ),
                            })}
                          </p>
                        ) : null}
                      </div>
                    ) : (
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div className="min-w-0">
                          <p className="font-medium">{sub.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatUzs(sub.limit_amount || 0)}
                            {` · ${t("budgets.spentLabel", {
                              defaultValue: "Spent",
                            })}: ${formatUzs(sub.spent || 0)}`}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditingSubcategoryId(sub.id);
                              setEditingSubcategoryLimit(
                                sub.limit_amount
                                  ? formatBudgetAmountInput(
                                      String(sub.limit_amount)
                                    )
                                  : ""
                              );
                            }}
                          >
                            {t("common.edit", {
                              defaultValue: "Edit",
                            })}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                            onClick={() =>
                              deleteMutation.mutate({
                                projectId: project.id,
                                subcategoryId: sub.id,
                              })
                            }
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            {t("common.delete", {
                              defaultValue: "Delete",
                            })}
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

      {actionError ? (
        <p className="text-sm text-red-600">{actionError}</p>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Isolated subcategory editor
// ---------------------------------------------------------------------------

function IsolatedSubcategoryEditor({
  project,
  categoryBreakdown,
  onMutation,
}) {
  const { t } = useTranslation();
  const [subcategoryCategory, setSubcategoryCategory] = useState("");
  const [subcategoryName, setSubcategoryName] = useState("");
  const [subcategoryLimit, setSubcategoryLimit] = useState("");
  const [subcategoryIsActive, setSubcategoryIsActive] = useState("true");
  const [editingSubcategoryId, setEditingSubcategoryId] = useState(null);
  const [editingSubcategoryName, setEditingSubcategoryName] = useState("");
  const [editingSubcategoryLimit, setEditingSubcategoryLimit] = useState("");
  const [editingSubcategoryIsActive, setEditingSubcategoryIsActive] =
    useState("true");
  const [actionError, setActionError] = useState("");

  const createMutation = useMutation({
    mutationFn: ({ projectId: pid, payload }) =>
      createProjectSubcategory(pid, payload),
    onSuccess: () => {
      setSubcategoryCategory("");
      setSubcategoryName("");
      setSubcategoryLimit("");
      setSubcategoryIsActive("true");
      setActionError("");
      onMutation();
    },
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ projectId: pid, subcategoryId: sid, payload }) =>
      updateProjectSubcategory(pid, sid, payload),
    onSuccess: () => {
      setEditingSubcategoryId(null);
      setEditingSubcategoryName("");
      setEditingSubcategoryLimit("");
      setEditingSubcategoryIsActive("true");
      setActionError("");
      onMutation();
    },
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const deleteMutation = useMutation({
    mutationFn: ({ projectId: pid, subcategoryId: sid }) =>
      deleteProjectSubcategory(pid, sid),
    onSuccess: () => onMutation(),
    onError: (e) => setActionError(getBudgetActionErrorMessage(e, t, formatUzs)),
  });

  const handleCreate = async () => {
    if (createMutation.isPending) return;
    setActionError("");
    if (!subcategoryCategory) {
      setActionError(
        t("projects.categoryRequired", {
          defaultValue: "Choose a category first",
        })
      );
      return;
    }
    if (!subcategoryName.trim()) {
      setActionError(
        t("projects.projectSubcategoryNameRequired", {
          defaultValue: "Project subcategory name is required",
        })
      );
      return;
    }
    const limitAmount = parseBudgetAmountInput(subcategoryLimit);
    try {
      await createMutation.mutateAsync({
        projectId: project.id,
        payload: {
          category: subcategoryCategory,
          name: subcategoryName.trim(),
          limit_amount: limitAmount,
          is_active: subcategoryIsActive === "true",
        },
      });
    } catch {
      /* handled in onError */
    }
  };

  const handleUpdate = async () => {
    if (!editingSubcategoryId || updateMutation.isPending) return;
    setActionError("");
    if (!editingSubcategoryName.trim()) {
      setActionError(
        t("projects.projectSubcategoryNameRequired", {
          defaultValue: "Project subcategory name is required",
        })
      );
      return;
    }
    const limitAmount = parseBudgetAmountInput(editingSubcategoryLimit);
    try {
      await updateMutation.mutateAsync({
        projectId: project.id,
        subcategoryId: editingSubcategoryId,
        payload: {
          name: editingSubcategoryName.trim(),
          limit_amount: limitAmount,
          is_active: editingSubcategoryIsActive === "true",
        },
      });
    } catch {
      /* handled in onError */
    }
  };

  const hasSubcategories = categoryBreakdown.some(
    (catRow) => (catRow.subcategories || []).length > 0
  );

  return (
    <div className="space-y-4">
      {/* Add isolated subcategory */}
      <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
        <p className="text-sm font-semibold">
          {t("projects.addProjectSubcategory", {
            defaultValue: "Add project subcategory",
          })}
        </p>
        <div className="mt-3 grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)_180px_140px_auto]">
          <Select
            value={subcategoryCategory || undefined}
            onValueChange={setSubcategoryCategory}
          >
            <SelectTrigger>
              <SelectValue placeholder={t("expenses.category")} />
            </SelectTrigger>
            <SelectContent>
              {categoryBreakdown.map((catRow) => (
                <SelectItem
                  key={catRow.category}
                  value={catRow.category}
                >
                  {tCategory(catRow.category)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            value={subcategoryName}
            onChange={(e) => setSubcategoryName(e.target.value)}
            placeholder={t("projects.projectSubcategoryName", {
              defaultValue: "Subcategory name",
            })}
          />
          <Input
            value={subcategoryLimit}
            onChange={(e) =>
              setSubcategoryLimit(
                formatBudgetAmountInput(e.target.value)
              )
            }
            inputMode="numeric"
            placeholder={t("projects.totalLimit", {
              defaultValue: "Limit amount",
            })}
          />
          <Select
            value={subcategoryIsActive}
            onValueChange={setSubcategoryIsActive}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="true">
                {t("common.active", { defaultValue: "Active" })}
              </SelectItem>
              <SelectItem value="false">
                {t("common.inactive", { defaultValue: "Inactive" })}
              </SelectItem>
            </SelectContent>
          </Select>
          <Button
            onClick={handleCreate}
            disabled={createMutation.isPending}
          >
            <Plus className="mr-2 h-4 w-4" />
            {t("common.add", { defaultValue: "Add" })}
          </Button>
        </div>
      </div>

      {/* Isolated subcategory list */}
      <div className="space-y-3">
        <p className="text-sm font-semibold">
          {t("projects.projectSubcategoriesSection", {
            defaultValue: "Project subcategories",
          })}
        </p>
        {!hasSubcategories ? (
          <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            {t("projects.noProjectSubcategoriesYet", {
              defaultValue: "No project subcategories yet.",
            })}
          </div>
        ) : (
          categoryBreakdown.map((catRow) => (
            <div
              key={`${catRow.category}-subcategories`}
              className="rounded-2xl border border-border/60 bg-background/80 p-4"
            >
              <p className="text-sm font-semibold">
                {tCategory(catRow.category)}
              </p>
              <div className="mt-3 space-y-3">
                {(catRow.subcategories || []).map((sub) => (
                  <div
                    key={sub.id}
                    className="rounded-xl border border-border/50 bg-muted/15 p-3"
                  >
                    {editingSubcategoryId === sub.id ? (
                      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_140px_auto_auto]">
                        <Input
                          value={editingSubcategoryName}
                          onChange={(e) =>
                            setEditingSubcategoryName(e.target.value)
                          }
                        />
                        <Input
                          value={editingSubcategoryLimit}
                          onChange={(e) =>
                            setEditingSubcategoryLimit(
                              formatBudgetAmountInput(e.target.value)
                            )
                          }
                          inputMode="numeric"
                        />
                        <Select
                          value={editingSubcategoryIsActive}
                          onValueChange={
                            setEditingSubcategoryIsActive
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="true">
                              {t("common.active", {
                                defaultValue: "Active",
                              })}
                            </SelectItem>
                            <SelectItem value="false">
                              {t("common.inactive", {
                                defaultValue: "Inactive",
                              })}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          onClick={handleUpdate}
                          disabled={updateMutation.isPending}
                        >
                          {t("common.save")}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setEditingSubcategoryId(null);
                            setEditingSubcategoryName("");
                            setEditingSubcategoryLimit("");
                            setEditingSubcategoryIsActive("true");
                          }}
                        >
                          {t("common.cancel")}
                        </Button>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div className="min-w-0">
                          <p className="font-medium">{sub.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {sub.is_active
                              ? t("common.active", {
                                  defaultValue: "Active",
                                })
                              : t("common.inactive", {
                                  defaultValue: "Inactive",
                                })}
                            {sub.limit_amount
                              ? ` · ${formatUzs(sub.limit_amount)}`
                              : ""}
                            {` · ${t("budgets.spentLabel", {
                              defaultValue: "Spent",
                            })}: ${formatUzs(sub.spent || 0)}`}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditingSubcategoryId(sub.id);
                              setEditingSubcategoryName(
                                sub.name || ""
                              );
                              setEditingSubcategoryLimit(
                                sub.limit_amount
                                  ? formatBudgetAmountInput(
                                      String(sub.limit_amount)
                                    )
                                  : ""
                              );
                              setEditingSubcategoryIsActive(
                                sub.is_active ? "true" : "false"
                              );
                            }}
                          >
                            {t("common.edit", {
                              defaultValue: "Edit",
                            })}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                            onClick={() =>
                              deleteMutation.mutate({
                                projectId: project.id,
                                subcategoryId: sub.id,
                              })
                            }
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            {t("common.delete", {
                              defaultValue: "Delete",
                            })}
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

      {actionError ? (
        <p className="text-sm text-red-600">{actionError}</p>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main exported component
// ---------------------------------------------------------------------------

export function ProjectStructureEditor({
  project,
  onMutationComplete,
  defaultMonthYear,
  defaultMonthMonth,
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const projectIsIsolated =
    project.project_type === "ISOLATED" || project.is_isolated;

  const categoryBreakdown = project.category_breakdown || [];

  const monthYear =
    defaultMonthYear || project.selected_budget_year || new Date().getFullYear();
  const monthMonth =
    defaultMonthMonth || project.selected_budget_month || 1;

  const handleMutation = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
      queryClient.invalidateQueries({
        queryKey: [
          "budgets",
          "month-summary",
          monthYear,
          monthMonth,
        ],
      }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
      queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
    if (onMutationComplete) onMutationComplete();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {t("projects.manageStructure", {
            defaultValue: "Manage structure",
          })}
        </h3>
        {!projectIsIsolated ? (
          <span className="text-sm text-muted-foreground">
            {t("projects.monthContext", { defaultValue: "Month" })}:{" "}
            {monthYear}-{String(monthMonth).padStart(2, "0")}
          </span>
        ) : null}
      </div>

      <CategoryLimitEditor
        project={project}
        projectIsIsolated={projectIsIsolated}
        categoryBreakdown={categoryBreakdown}
        monthYear={monthYear}
        monthMonth={monthMonth}
        onMutation={handleMutation}
      />

      {!projectIsIsolated ? (
        <OverlaySubcategoryEditor
          project={project}
          categoryBreakdown={categoryBreakdown}
          monthYear={monthYear}
          monthMonth={monthMonth}
          onMutation={handleMutation}
        />
      ) : (
        <IsolatedSubcategoryEditor
          project={project}
          categoryBreakdown={categoryBreakdown}
          onMutation={handleMutation}
        />
      )}
    </div>
  );
}

export default ProjectStructureEditor;
