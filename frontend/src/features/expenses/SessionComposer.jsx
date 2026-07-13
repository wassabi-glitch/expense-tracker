import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Pause, Play, Plus, Receipt, Trash2, Users, Wallet } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  abandonSessionDraft,
  addSessionDraftItem,
  addSessionDraftSplit,
  addSessionWalletAllocation,
  createSessionDraft,
  deleteSessionDraftItem,
  deleteSessionDraftSplit,
  deleteSessionWalletAllocation,
  finalizeSessionDraft,
  getBudgets,
  getBudgetSubcategories,
  getActiveSessionDraft,
  getProjects,
  getProjectSubcategories,
  pauseSessionDraft,
  resumeSessionDraft,
  updateSessionDraft,
  updateSessionDraftItem,
  updateSessionDraftSplit,
  updateSessionWalletAllocation,
} from "@/lib/api";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { localizeApiError } from "@/lib/errorMessages";
import { formatAmountInput, parseAmountInput } from "@/lib/format";
import { useToast } from "@/lib/context/ToastContext";
import { isBudgetRequiredError, extractBudgetMonth } from "@/lib/budgetInterceptor";
import { useBudgetRepair } from "@/features/budgets/hooks/useBudgetRepair";
import { BudgetRepairDialog } from "@/features/budgets/components/BudgetRepairDialog";

function ResponsiveSessionShell({ compact, open, onOpenChange, title, description, children, footer }) {
  if (compact) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="bottom" className="flex max-h-[94vh] flex-col rounded-t-[28px] border-x-0 border-b-0 px-0 pb-0 pt-0">
          <SheetHeader className="border-b border-border/60 px-5 pb-4 pt-5 text-left">
            <SheetTitle>{title}</SheetTitle>
            <SheetDescription>{description}</SheetDescription>
          </SheetHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
          <SheetFooter className="mt-auto border-t border-border/60 bg-background/95 px-5 pb-5 pt-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
            {footer}
          </SheetFooter>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[92vh] max-w-5xl flex-col overflow-hidden p-0">
        <DialogHeader className="border-b border-border/60 px-6 pb-4 pt-6">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          {children}
        </div>
        <DialogFooter className="mt-auto border-t border-border/60 bg-background/95 px-6 py-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 sm:justify-between">
          {footer}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function SessionComposer({
  open,
  onOpenChange,
  compact,
  categories,
  wallets,
  todayISO,
  tCategory,
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [actionError, setActionError] = React.useState("");
  const [repairAmount, setRepairAmount] = React.useState("");
  const budgetRepair = useBudgetRepair();

  // Pre-fill repair amount when the dialog opens
  React.useEffect(() => {
    if (budgetRepair.prompt) {
      setRepairAmount(formatAmountInput(String(budgetRepair.prompt.suggestedAmount || 0)));
    } else {
      setRepairAmount("");
    }
  }, [budgetRepair.prompt]);

  const [headerTitle, setHeaderTitle] = React.useState("");
  const [headerDescription, setHeaderDescription] = React.useState("");
  const [headerDate, setHeaderDate] = React.useState(todayISO);
  const [headerAmountPaid, setHeaderAmountPaid] = React.useState("");

  const [itemLabel, setItemLabel] = React.useState("");
  const [itemAmount, setItemAmount] = React.useState("");
  const [itemCategory, setItemCategory] = React.useState("");
  const [itemSubcategoryId, setItemSubcategoryId] = React.useState("");
  const [itemProjectId, setItemProjectId] = React.useState("");
  const [itemProjectSubcategoryId, setItemProjectSubcategoryId] = React.useState("");

  const [allocationWalletId, setAllocationWalletId] = React.useState("");
  const [allocationAmount, setAllocationAmount] = React.useState("");
  const [splitContactName, setSplitContactName] = React.useState("");
  const [splitAmount, setSplitAmount] = React.useState("");
  const [editingItemId, setEditingItemId] = React.useState(null);
  const [editingItemLabel, setEditingItemLabel] = React.useState("");
  const [editingItemAmount, setEditingItemAmount] = React.useState("");
  const [editingItemCategory, setEditingItemCategory] = React.useState("");
  const [editingItemSubcategoryId, setEditingItemSubcategoryId] = React.useState("");
  const [editingItemProjectId, setEditingItemProjectId] = React.useState("");
  const [editingItemProjectSubcategoryId, setEditingItemProjectSubcategoryId] = React.useState("");
  const [editingAllocationId, setEditingAllocationId] = React.useState(null);
  const [editingAllocationAmount, setEditingAllocationAmount] = React.useState("");
  const [editingSplitId, setEditingSplitId] = React.useState(null);
  const [editingSplitContactName, setEditingSplitContactName] = React.useState("");
  const [editingSplitAmount, setEditingSplitAmount] = React.useState("");

  const activeDraftQuery = useQuery({
    queryKey: ["expenses", "session-draft", "active"],
    queryFn: getActiveSessionDraft,
    enabled: open,
  });

  const draft = activeDraftQuery.data;
  const budgetsQuery = useQuery({
    queryKey: ["budgets"],
    queryFn: getBudgets,
    enabled: open,
    staleTime: 60_000,
  });
  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: getProjects,
    enabled: open,
    staleTime: 60_000,
  });
  const [subcategoryOptionsByBudgetId, setSubcategoryOptionsByBudgetId] = React.useState({});
  const [projectSubcategoryOptionsByProjectCategory, setProjectSubcategoryOptionsByProjectCategory] = React.useState({});

  const draftMonthBudgetByCategory = React.useMemo(() => {
    const rows = Array.isArray(budgetsQuery.data) ? budgetsQuery.data : [];
    const dateSource = draft?.date || headerDate || todayISO;
    const [yearRaw, monthRaw] = String(dateSource).split("-");
    const year = Number(yearRaw);
    const month = Number(monthRaw);
    const map = new Map();
    rows.forEach((budget) => {
      if (Number(budget.budget_year) === year && Number(budget.budget_month) === month) {
        map.set(budget.category, budget);
      }
    });
    return map;
  }, [budgetsQuery.data, draft?.date, headerDate, todayISO]);

  React.useEffect(() => {
    let cancelled = false;
    const loadSubcategories = async () => {
      const budgets = Array.from(draftMonthBudgetByCategory.values());
      const missing = budgets.filter((budget) => subcategoryOptionsByBudgetId[budget.id] === undefined);
      if (!missing.length) return;
      try {
        const entries = await Promise.all(
          missing.map(async (budget) => [budget.id, await getBudgetSubcategories(budget.id)])
        );
        if (cancelled) return;
        setSubcategoryOptionsByBudgetId((prev) => {
          const next = { ...prev };
          entries.forEach(([budgetId, subcategories]) => {
            next[budgetId] = subcategories;
          });
          return next;
        });
      } catch {
        if (!cancelled) {
          setSubcategoryOptionsByBudgetId((prev) => prev);
        }
      }
    };
    if (open && draftMonthBudgetByCategory.size > 0) {
      void loadSubcategories();
    }
    return () => {
      cancelled = true;
    };
  }, [open, draftMonthBudgetByCategory, subcategoryOptionsByBudgetId]);

  const getSubcategoryOptions = React.useCallback((category) => {
    const budget = draftMonthBudgetByCategory.get(category);
    if (!budget) return [];
    return subcategoryOptionsByBudgetId[budget.id] || [];
  }, [draftMonthBudgetByCategory, subcategoryOptionsByBudgetId]);

  const projectOptions = React.useMemo(
    () => (Array.isArray(projectsQuery.data) ? projectsQuery.data : []),
    [projectsQuery.data]
  );
  const projectById = React.useMemo(
    () => new Map(projectOptions.map((project) => [String(project.id), project])),
    [projectOptions],
  );
  const projectNameById = React.useMemo(
    () => new Map(projectOptions.map((project) => [project.id, project.title])),
    [projectOptions]
  );
  const subcategoryNameById = React.useMemo(() => {
    const map = new Map();
    Object.values(subcategoryOptionsByBudgetId).forEach((rows) => {
      (rows || []).forEach((item) => map.set(item.id, item.name));
    });
    return map;
  }, [subcategoryOptionsByBudgetId]);
  const projectSubcategoryNameById = React.useMemo(() => {
    const map = new Map();
    Object.values(projectSubcategoryOptionsByProjectCategory).forEach((rows) => {
      (rows || []).forEach((item) => map.set(item.id, item.name));
    });
    return map;
  }, [projectSubcategoryOptionsByProjectCategory]);

  const getProjectSubcategoryOptions = React.useCallback((projectId, category) => {
    if (!projectId || !category) return [];
    return projectSubcategoryOptionsByProjectCategory[`${projectId}:${category}`] || [];
  }, [projectSubcategoryOptionsByProjectCategory]);

  React.useEffect(() => {
    let cancelled = false;
    const draftTargets = (draft?.items || []).map((item) => ({
      projectId: item.project_id ? String(item.project_id) : "",
      category: item.category,
    }));
    const targets = [
      itemProjectId && itemCategory ? { projectId: itemProjectId, category: itemCategory } : null,
      editingItemProjectId && editingItemCategory ? { projectId: editingItemProjectId, category: editingItemCategory } : null,
      ...draftTargets,
    ].filter(Boolean);
    const missing = targets.filter(({ projectId, category }) => {
      const project = projectById.get(String(projectId));
      if (!project?.is_isolated) return false;
      return projectSubcategoryOptionsByProjectCategory[`${projectId}:${category}`] === undefined;
    });
    if (!open || !missing.length) return undefined;

    const loadProjectSubcategories = async () => {
      try {
        const entries = await Promise.all(
          missing.map(async ({ projectId, category }) => [
            `${projectId}:${category}`,
            await getProjectSubcategories(projectId, category),
          ]),
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
        if (cancelled) return;
      }
    };

    void loadProjectSubcategories();
    return () => {
      cancelled = true;
    };
  }, [
    open,
    draft?.items,
    itemProjectId,
    itemCategory,
    editingItemProjectId,
    editingItemCategory,
    projectById,
    projectSubcategoryOptionsByProjectCategory,
  ]);

  React.useEffect(() => {
    if (draft) {
      setHeaderTitle(draft.title || "");
      setHeaderDescription(draft.description || "");
      setHeaderDate(draft.date || todayISO);
      setHeaderAmountPaid(draft.amount_paid ? formatAmountInput(String(draft.amount_paid)) : "");
    } else if (open) {
      setHeaderTitle("");
      setHeaderDescription("");
      setHeaderDate(todayISO);
      setHeaderAmountPaid("");
    }
  }, [draft, todayISO, open]);

  const invalidateSessionAndExpenses = React.useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["expenses"] }),
      queryClient.invalidateQueries({ queryKey: ["wallets"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets"] }),
      queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft"] }),
    ]);
  }, [queryClient]);

  const createDraftMutation = useMutation({
    mutationFn: createSessionDraft,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      toast.neutral(t("expenses.sessionStarted", { defaultValue: "Session started" }));
    },
    onError: (error) => {
      setActionError(localizeApiError(error, t) || error.message);
    },
  });

  const updateDraftMutation = useMutation({
    mutationFn: ({ draftId, payload }) => updateSessionDraft(draftId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      toast.neutral(t("expenses.sessionUpdated", { defaultValue: "Session updated" }));
    },
    onError: (error) => {
      setActionError(localizeApiError(error, t) || error.message);
    },
  });

  const addItemMutation = useMutation({
    mutationFn: ({ draftId, payload }) => addSessionDraftItem(draftId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      setItemLabel("");
      setItemAmount("");
      setItemCategory("");
      setItemSubcategoryId("");
      setItemProjectId("");
      setItemProjectSubcategoryId("");
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const deleteItemMutation = useMutation({
    mutationFn: ({ draftId, itemId }) => deleteSessionDraftItem(draftId, itemId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const updateItemMutation = useMutation({
    mutationFn: ({ draftId, itemId, payload }) => updateSessionDraftItem(draftId, itemId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      setEditingItemId(null);
      setEditingItemLabel("");
      setEditingItemAmount("");
      setEditingItemCategory("");
      setEditingItemSubcategoryId("");
      setEditingItemProjectId("");
      setEditingItemProjectSubcategoryId("");
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const addAllocationMutation = useMutation({
    mutationFn: ({ draftId, payload }) => addSessionWalletAllocation(draftId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      setAllocationWalletId("");
      setAllocationAmount("");
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const deleteAllocationMutation = useMutation({
    mutationFn: ({ draftId, allocationId }) => deleteSessionWalletAllocation(draftId, allocationId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const updateAllocationMutation = useMutation({
    mutationFn: ({ draftId, allocationId, payload }) => updateSessionWalletAllocation(draftId, allocationId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      setEditingAllocationId(null);
      setEditingAllocationAmount("");
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const addSplitMutation = useMutation({
    mutationFn: ({ draftId, payload }) => addSessionDraftSplit(draftId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      setSplitContactName("");
      setSplitAmount("");
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const deleteSplitMutation = useMutation({
    mutationFn: ({ draftId, splitId }) => deleteSessionDraftSplit(draftId, splitId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const updateSplitMutation = useMutation({
    mutationFn: ({ draftId, splitId, payload }) => updateSessionDraftSplit(draftId, splitId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      setEditingSplitId(null);
      setEditingSplitContactName("");
      setEditingSplitAmount("");
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const pauseMutation = useMutation({
    mutationFn: pauseSessionDraft,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const resumeMutation = useMutation({
    mutationFn: resumeSessionDraft,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const abandonMutation = useMutation({
    mutationFn: abandonSessionDraft,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["expenses", "session-draft", "active"] });
      onOpenChange(false);
    },
    onError: (error) => setActionError(localizeApiError(error, t) || error.message),
  });

  const finalizeMutation = useMutation({
    mutationFn: finalizeSessionDraft,
    onSuccess: async () => {
      await invalidateSessionAndExpenses();
      toast.success(t("expenses.sessionFinalized", { defaultValue: "Session finalized" }));
      onOpenChange(false);
    },
    onError: (error) => {
      if (isBudgetRequiredError(error)) {
        // Extract category/date from the first draft item for repair context
        const firstItem = draft?.items?.[0];
        const category = firstItem?.category || "";
        const date = firstItem?.date || headerDate || todayISO;
        const amount = firstItem?.amount
          ? Math.abs(Number(firstItem.amount))
          : 0;
        const { budgetYear, budgetMonth } = extractBudgetMonth(date);
        budgetRepair.open({
          category,
          budgetYear,
          budgetMonth,
          suggestedAmount: amount,
          date,
          onReplay: async () => {
            await finalizeSessionDraft(draft.id);
          },
        });
        return;
      }
      setActionError(localizeApiError(error, t) || error.message);
    },
  });

  const handleCreateDraft = async () => {
    setActionError("");
    await createDraftMutation.mutateAsync({
      title: headerTitle.trim() || t("expenses.defaultSessionTitle", { defaultValue: "Shopping Session" }),
      description: headerDescription.trim() || null,
      date: headerDate,
      amount_paid: headerAmountPaid ? parseAmountInput(headerAmountPaid) : null,
      source_type: "MANUAL",
    });
  };

  const handleSaveHeader = async () => {
    if (!draft) return;
    setActionError("");
    await updateDraftMutation.mutateAsync({
      draftId: draft.id,
      payload: {
        title: headerTitle.trim(),
        description: headerDescription.trim() || null,
        date: headerDate,
        amount_paid: headerAmountPaid ? parseAmountInput(headerAmountPaid) : null,
      },
    });
  };

  const handleSavePaidAmount = async () => {
    if (!draft) return;
    setActionError("");
    const parsedAmount = parseAmountInput(headerAmountPaid);
    if (!headerAmountPaid || !Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setActionError(t("expenses.sessionPaidAmountRequired", {
        defaultValue: "Enter a paid amount greater than zero before saving it.",
      }));
      return;
    }

    await updateDraftMutation.mutateAsync({
      draftId: draft.id,
      payload: {
        amount_paid: parsedAmount,
      },
    });
  };

  const handleAddItem = async () => {
    if (!draft) return;
    setActionError("");
    await addItemMutation.mutateAsync({
      draftId: draft.id,
      payload: {
        label: itemLabel.trim(),
        original_amount: parseAmountInput(itemAmount),
        category: itemCategory,
        subcategory_id: itemSubcategoryId ? Number(itemSubcategoryId) : null,
        project_id: itemProjectId ? Number(itemProjectId) : null,
        project_subcategory_id: itemProjectSubcategoryId ? Number(itemProjectSubcategoryId) : null,
      },
    });
  };

  const handleAddAllocation = async () => {
    if (!draft) return;
    setActionError("");
    await addAllocationMutation.mutateAsync({
      draftId: draft.id,
      payload: {
        wallet_id: Number(allocationWalletId),
        amount: parseAmountInput(allocationAmount),
      },
    });
  };

  const handleAddSplit = async () => {
    if (!draft) return;
    setActionError("");
    await addSplitMutation.mutateAsync({
      draftId: draft.id,
      payload: {
        contact_name: splitContactName.trim(),
        amount: parseAmountInput(splitAmount),
      },
    });
  };

  const startEditingItem = (item) => {
    setEditingItemId(item.id);
    setEditingItemLabel(item.label || "");
    setEditingItemAmount(formatAmountInput(String(item.original_amount || "")));
    setEditingItemCategory(item.category || "");
    setEditingItemSubcategoryId(item.subcategory_id ? String(item.subcategory_id) : "");
    setEditingItemProjectId(item.project_id ? String(item.project_id) : "");
    setEditingItemProjectSubcategoryId(item.project_subcategory_id ? String(item.project_subcategory_id) : "");
  };

  const handleUpdateItem = async () => {
    if (!draft || !editingItemId) return;
    setActionError("");
    await updateItemMutation.mutateAsync({
      draftId: draft.id,
      itemId: editingItemId,
      payload: {
        label: editingItemLabel.trim(),
        original_amount: parseAmountInput(editingItemAmount),
        category: editingItemCategory,
        subcategory_id: editingItemSubcategoryId ? Number(editingItemSubcategoryId) : null,
        project_id: editingItemProjectId ? Number(editingItemProjectId) : null,
        project_subcategory_id: editingItemProjectSubcategoryId ? Number(editingItemProjectSubcategoryId) : null,
      },
    });
  };

  const startEditingAllocation = (allocation) => {
    setEditingAllocationId(allocation.id);
    setEditingAllocationAmount(formatAmountInput(String(allocation.amount || "")));
  };

  const handleUpdateAllocation = async () => {
    if (!draft || !editingAllocationId) return;
    setActionError("");
    await updateAllocationMutation.mutateAsync({
      draftId: draft.id,
      allocationId: editingAllocationId,
      payload: {
        amount: parseAmountInput(editingAllocationAmount),
      },
    });
  };

  const startEditingSplit = (split) => {
    setEditingSplitId(split.id);
    setEditingSplitContactName(split.contact_name || "");
    setEditingSplitAmount(formatAmountInput(String(split.amount || "")));
  };

  const handleUpdateSplit = async () => {
    if (!draft || !editingSplitId) return;
    setActionError("");
    await updateSplitMutation.mutateAsync({
      draftId: draft.id,
      splitId: editingSplitId,
      payload: {
        contact_name: editingSplitContactName.trim(),
        amount: parseAmountInput(editingSplitAmount),
      },
    });
  };

  const footer = draft ? (
    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
          {t("common.close", { defaultValue: "Close" })}
        </Button>
        <Button
          variant="outline"
          onClick={() => draft.status === "PAUSED" ? resumeMutation.mutate(draft.id) : pauseMutation.mutate(draft.id)}
          disabled={pauseMutation.isPending || resumeMutation.isPending || finalizeMutation.isPending}
          className="w-full sm:w-auto"
        >
          {draft.status === "PAUSED" ? <Play className="mr-2 h-4 w-4" /> : <Pause className="mr-2 h-4 w-4" />}
          {draft.status === "PAUSED"
            ? t("expenses.resumeSession", { defaultValue: "Resume" })
            : t("expenses.pauseSession", { defaultValue: "Pause" })}
        </Button>
      </div>
      <Button
        variant="secondary"
        onClick={() => finalizeMutation.mutate(draft.id)}
        disabled={!draft.can_finalize || finalizeMutation.isPending}
        className="w-full sm:w-auto"
      >
        <Receipt className="mr-2 h-4 w-4" />
        {t("expenses.finalizeSession", { defaultValue: "Finalize" })}
      </Button>
    </div>
  ) : (
    <div className="flex w-full flex-col gap-2 sm:flex-row sm:justify-between">
      <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
        {t("common.close", { defaultValue: "Close" })}
      </Button>
      <Button onClick={handleCreateDraft} disabled={createDraftMutation.isPending || !headerDate} className="w-full sm:w-auto">
        <Receipt className="mr-2 h-4 w-4" />
        {t("expenses.startSession", { defaultValue: "Start Session" })}
      </Button>
    </div>
  );

  return (
    <>
    <ResponsiveSessionShell
      compact={compact}
      open={open}
      onOpenChange={onOpenChange}
      title={draft ? t("expenses.sessionWorkspace", { defaultValue: "Session workspace" }) : t("expenses.startSession", { defaultValue: "Start Session" })}
      description={draft
        ? t("expenses.sessionWorkspaceDesc", { defaultValue: "Add items, allocate wallets, and finalize when the session is balanced." })
        : t("expenses.sessionStartDesc", { defaultValue: "Create a purchase session and build it out before finalizing." })}
      footer={footer}
    >
      {activeDraftQuery.isLoading ? (
        <div className="flex min-h-[240px] items-center justify-center">
          <LoadingSpinner className="h-8 w-8 text-primary" />
        </div>
      ) : (
        <div className="space-y-5">
          <Card className="shadow-sm">
            <CardContent className="grid gap-4 p-4 sm:grid-cols-2">
              <div className="grid gap-1.5 sm:col-span-2">
                <label className="text-xs font-semibold">{t("expenses.titleCol")}</label>
                <Input value={headerTitle} onChange={(e) => setHeaderTitle(e.target.value)} placeholder={t("expenses.sessionNamePlaceholder", { defaultValue: "Sunday Shopping" })} />
              </div>
              <div className="grid gap-1.5">
                <label className="text-xs font-semibold">{t("expenses.date")}</label>
                <Input type="date" min="2020-01-01" max={todayISO} value={headerDate} onChange={(e) => setHeaderDate(e.target.value)} />
              </div>
              <div className="grid gap-1.5 sm:col-span-2">
                <label className="text-xs font-semibold">{t("expenses.description")}</label>
                <Textarea value={headerDescription} onChange={(e) => setHeaderDescription(e.target.value)} className="resize-none" rows={3} />
              </div>
              {draft ? (
                <div className="sm:col-span-2 flex flex-wrap gap-2 border-t border-border/60 pt-2">
                  <Button variant="outline" onClick={handleSaveHeader} disabled={updateDraftMutation.isPending}>
                    {t("common.save")}
                  </Button>
                  <Button variant="ghost" className="text-destructive hover:text-destructive" onClick={() => abandonMutation.mutate(draft.id)} disabled={abandonMutation.isPending}>
                    {t("expenses.abandonSession", { defaultValue: "Abandon" })}
                  </Button>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {draft ? (
            <>
              <div className="space-y-4">
                <Card className="shadow-sm">
                  <CardContent className="space-y-4 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold">{t("expenses.sessionItems", { defaultValue: "Items" })}</p>
                        <p className="text-xs text-muted-foreground">{t("expenses.sessionItemsDesc", { defaultValue: "Each row becomes an item allocation inside the session." })}</p>
                      </div>
                      <Badge variant="secondary">{draft.items.length}</Badge>
                    </div>

                    <div className="rounded-2xl border border-border/60 bg-muted/15 p-3">
                      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_180px_220px]">
                        <div className="grid gap-1.5">
                          <label className="text-xs font-semibold">{t("expenses.itemLabel", { defaultValue: "Item label" })}</label>
                          <Input value={itemLabel} onChange={(e) => setItemLabel(e.target.value)} placeholder={t("expenses.itemLabel", { defaultValue: "Item label" })} />
                        </div>
                        <div className="grid gap-1.5">
                          <label className="text-xs font-semibold">{t("expenses.amount", { defaultValue: "Amount" })}</label>
                          <Input value={itemAmount} onChange={(e) => setItemAmount(formatAmountInput(e.target.value))} inputMode="numeric" placeholder="0" />
                        </div>
                        <div className="grid gap-1.5">
                          <label className="text-xs font-semibold">{t("expenses.category")}</label>
                          <Select value={itemCategory} onValueChange={(value) => {
                            setItemCategory(value);
                            setItemSubcategoryId("");
                            setItemProjectSubcategoryId("");
                          }}>
                            <SelectTrigger><SelectValue placeholder={t("expenses.category")} /></SelectTrigger>
                            <SelectContent>
                              {categories.map((category) => (
                                <SelectItem key={category} value={category}>{tCategory(category)}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
                        <div className="grid gap-1.5">
                          <label className="text-xs font-semibold">{t("expenses.subcategory", { defaultValue: "Subcategory" })}</label>
                          <Select value={itemSubcategoryId || "__none__"} onValueChange={(value) => setItemSubcategoryId(value === "__none__" ? "" : value)} disabled={!itemCategory}>
                            <SelectTrigger><SelectValue placeholder={t("expenses.subcategory", { defaultValue: "Subcategory" })} /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                              {getSubcategoryOptions(itemCategory).map((subcategory) => (
                                <SelectItem key={subcategory.id} value={String(subcategory.id)}>{subcategory.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="grid gap-1.5">
                          <label className="text-xs font-semibold">{t("expenses.project", { defaultValue: "Project" })}</label>
                          <Select value={itemProjectId || "__none__"} onValueChange={(value) => {
                            const next = value === "__none__" ? "" : value;
                            setItemProjectId(next);
                            setItemProjectSubcategoryId("");
                          }}>
                            <SelectTrigger><SelectValue placeholder={t("expenses.project", { defaultValue: "Project" })} /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                              {projectOptions.map((project) => (
                                <SelectItem key={project.id} value={String(project.id)}>{project.title}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="grid gap-1.5">
                          <label className="text-xs font-semibold">{t("projects.projectSubcategory", { defaultValue: "Project subcategory" })}</label>
                          <Select
                            value={itemProjectSubcategoryId || "__none__"}
                            onValueChange={(value) => setItemProjectSubcategoryId(value === "__none__" ? "" : value)}
                            disabled={!itemProjectId || !projectById.get(String(itemProjectId))?.is_isolated}
                          >
                            <SelectTrigger><SelectValue placeholder={t("projects.projectSubcategory", { defaultValue: "Project subcategory" })} /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                              {getProjectSubcategoryOptions(itemProjectId, itemCategory).map((subcategory) => (
                                <SelectItem key={subcategory.id} value={String(subcategory.id)}>{subcategory.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="grid gap-1.5 lg:self-end">
                          <span className="hidden text-xs font-semibold lg:block">&nbsp;</span>
                          <Button onClick={handleAddItem} disabled={!itemLabel.trim() || !itemAmount || !itemCategory || addItemMutation.isPending} className="w-full lg:w-auto">
                            <Plus className="mr-2 h-4 w-4" />
                            {t("common.add", { defaultValue: "Add" })}
                          </Button>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      {draft.items.map((item) => (
                        <div key={item.id} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                          {editingItemId === item.id ? (
                            <div className="grid w-full gap-3">
                              <div className="grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_180px_220px]">
                                <Input value={editingItemLabel} onChange={(e) => setEditingItemLabel(e.target.value)} />
                                <Input value={editingItemAmount} onChange={(e) => setEditingItemAmount(formatAmountInput(e.target.value))} inputMode="numeric" />
                                <Select value={editingItemCategory} onValueChange={(value) => {
                                  setEditingItemCategory(value);
                                  setEditingItemSubcategoryId("");
                                  setEditingItemProjectSubcategoryId("");
                                }}>
                                  <SelectTrigger><SelectValue /></SelectTrigger>
                                  <SelectContent>
                                    {categories.map((category) => (
                                      <SelectItem key={category} value={category}>{tCategory(category)}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto_auto]">
                                <Select value={editingItemSubcategoryId || "__none__"} onValueChange={(value) => setEditingItemSubcategoryId(value === "__none__" ? "" : value)} disabled={!editingItemCategory}>
                                  <SelectTrigger><SelectValue placeholder={t("expenses.subcategory", { defaultValue: "Subcategory" })} /></SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                                    {getSubcategoryOptions(editingItemCategory).map((subcategory) => (
                                      <SelectItem key={subcategory.id} value={String(subcategory.id)}>{subcategory.name}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <Select value={editingItemProjectId || "__none__"} onValueChange={(value) => {
                                  const next = value === "__none__" ? "" : value;
                                  setEditingItemProjectId(next);
                                  setEditingItemProjectSubcategoryId("");
                                }}>
                                  <SelectTrigger><SelectValue placeholder={t("expenses.project", { defaultValue: "Project" })} /></SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                                    {projectOptions.map((project) => (
                                      <SelectItem key={project.id} value={String(project.id)}>{project.title}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <Select
                                  value={editingItemProjectSubcategoryId || "__none__"}
                                  onValueChange={(value) => setEditingItemProjectSubcategoryId(value === "__none__" ? "" : value)}
                                  disabled={!editingItemProjectId || !projectById.get(String(editingItemProjectId))?.is_isolated}
                                >
                                  <SelectTrigger><SelectValue placeholder={t("projects.projectSubcategory", { defaultValue: "Project subcategory" })} /></SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="__none__">{t("common.none", { defaultValue: "None" })}</SelectItem>
                                    {getProjectSubcategoryOptions(editingItemProjectId, editingItemCategory).map((subcategory) => (
                                      <SelectItem key={subcategory.id} value={String(subcategory.id)}>{subcategory.name}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <Button onClick={handleUpdateItem} disabled={!editingItemLabel.trim() || !editingItemAmount || !editingItemCategory || updateItemMutation.isPending}>
                                  {t("common.save")}
                                </Button>
                                <Button variant="outline" onClick={() => setEditingItemId(null)}>
                                  {t("common.cancel")}
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="min-w-0">
                                <p className="truncate font-medium">{item.label}</p>
                                <p className="text-sm text-muted-foreground">
                                  {tCategory(item.category)}
                                  {item.subcategory_id ? ` • ${subcategoryNameById.get(item.subcategory_id) || `#${item.subcategory_id}`}` : ""}
                                  {item.project_id ? ` • ${projectNameById.get(item.project_id) || `#${item.project_id}`}` : ""}
                                  {item.project_subcategory_id ? ` • ${projectSubcategoryNameById.get(item.project_subcategory_id) || `#${item.project_subcategory_id}`}` : ""}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <CurrencyAmount value={item.adjusted_amount || item.original_amount} format="display" />
                                <Button variant="ghost" size="sm" onClick={() => startEditingItem(item)}>
                                  {t("common.edit", { defaultValue: "Edit" })}
                                </Button>
                                <Button variant="ghost" size="icon" onClick={() => deleteItemMutation.mutate({ draftId: draft.id, itemId: item.id })}>
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card className="shadow-sm">
                  <CardContent className="space-y-4 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold">{t("expenses.sessionWallets", { defaultValue: "Wallet allocations" })}</p>
                        <p className="text-xs text-muted-foreground">{t("expenses.sessionWalletsDesc", { defaultValue: "Match the paid amount across one or more wallets." })}</p>
                      </div>
                      <Badge variant={draft.remaining_wallet_allocation === 0 ? "secondary" : "outline"}>
                        {draft.remaining_wallet_allocation == null
                          ? t("expenses.sessionNoAmountPaid", { defaultValue: "Set amount paid" })
                          : `${t("expenses.remaining", { defaultValue: "Remaining" })}: ${draft.remaining_wallet_allocation}`}
                      </Badge>
                    </div>

                    <div className="grid gap-3 rounded-2xl border border-border/60 bg-muted/15 p-3 md:grid-cols-[220px_auto]">
                      <div className="grid gap-1.5">
                        <label className="text-xs font-semibold">{t("expenses.amountPaid", { defaultValue: "Amount paid" })}</label>
                        <Input
                          value={headerAmountPaid}
                          onChange={(e) => {
                            setHeaderAmountPaid(formatAmountInput(e.target.value));
                            setActionError("");
                          }}
                          inputMode="numeric"
                          placeholder="0"
                        />
                      </div>
                      <div className="flex items-end">
                        <Button variant="outline" onClick={handleSavePaidAmount} disabled={updateDraftMutation.isPending} className="w-full md:w-auto">
                          {t("expenses.savePaidAmount", { defaultValue: "Save paid amount" })}
                        </Button>
                      </div>
                    </div>

                    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto]">
                      <Select value={allocationWalletId} onValueChange={setAllocationWalletId}>
                        <SelectTrigger><SelectValue placeholder={t("wallet.placeholder", { defaultValue: "Select Wallet" })} /></SelectTrigger>
                        <SelectContent>
                          {wallets.map((wallet) => (
                            <SelectItem key={wallet.id} value={String(wallet.id)}>{wallet.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input value={allocationAmount} onChange={(e) => setAllocationAmount(formatAmountInput(e.target.value))} inputMode="numeric" placeholder={t("expenses.amount", { defaultValue: "Amount" })} />
                      <Button onClick={handleAddAllocation} disabled={!allocationWalletId || !allocationAmount || addAllocationMutation.isPending}>
                        <Wallet className="mr-2 h-4 w-4" />
                        {t("common.add", { defaultValue: "Add" })}
                      </Button>
                    </div>

                    <div className="space-y-2">
                      {draft.wallet_allocations.map((allocation) => (
                        <div key={allocation.id} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                          {editingAllocationId === allocation.id ? (
                            <div className="grid w-full gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto_auto]">
                              <div>
                                <p className="font-medium">{allocation.wallet?.name || `${t("wallet.label", { defaultValue: "Wallet" })} #${allocation.wallet_id}`}</p>
                                <p className="text-sm text-muted-foreground">{t("expenses.walletLeg", { defaultValue: "Wallet leg" })}</p>
                              </div>
                              <Input value={editingAllocationAmount} onChange={(e) => setEditingAllocationAmount(formatAmountInput(e.target.value))} inputMode="numeric" />
                              <Button onClick={handleUpdateAllocation} disabled={!editingAllocationAmount || updateAllocationMutation.isPending}>
                                {t("common.save")}
                              </Button>
                              <Button variant="outline" onClick={() => setEditingAllocationId(null)}>
                                {t("common.cancel")}
                              </Button>
                            </div>
                          ) : (
                            <>
                              <div>
                                <p className="font-medium">{allocation.wallet?.name || `${t("wallet.label", { defaultValue: "Wallet" })} #${allocation.wallet_id}`}</p>
                                <p className="text-sm text-muted-foreground">{t("expenses.walletLeg", { defaultValue: "Wallet leg" })}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <CurrencyAmount value={allocation.amount} format="display" />
                                <Button variant="ghost" size="sm" onClick={() => startEditingAllocation(allocation)}>
                                  {t("common.edit", { defaultValue: "Edit" })}
                                </Button>
                                <Button variant="ghost" size="icon" onClick={() => deleteAllocationMutation.mutate({ draftId: draft.id, allocationId: allocation.id })}>
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card className="shadow-sm">
                <CardContent className="space-y-4 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{t("expenses.sessionSplits", { defaultValue: "Friend splits" })}</p>
                      <p className="text-xs text-muted-foreground">{t("expenses.sessionSplitsDesc", { defaultValue: "Track who owes part of this grouped spend." })}</p>
                    </div>
                    <Badge variant="secondary">{draft.splits.length}</Badge>
                  </div>

                  <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto]">
                    <Input
                      value={splitContactName}
                      onChange={(e) => setSplitContactName(e.target.value)}
                      placeholder={t("expenses.contactName", { defaultValue: "Contact name" })}
                    />
                    <Input
                      value={splitAmount}
                      onChange={(e) => setSplitAmount(formatAmountInput(e.target.value))}
                      inputMode="numeric"
                      placeholder={t("expenses.amount", { defaultValue: "Amount" })}
                    />
                    <Button
                      onClick={handleAddSplit}
                      disabled={!splitContactName.trim() || !splitAmount || addSplitMutation.isPending}
                    >
                      <Users className="mr-2 h-4 w-4" />
                      {t("expenses.addSplit", { defaultValue: "Add split" })}
                    </Button>
                  </div>

                  <div className="space-y-2">
                    {draft.splits.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
                        {t("expenses.sessionSplitsEmpty", { defaultValue: "No split rows yet. Add one if part of this session should be repaid by someone else." })}
                      </div>
                    ) : (
                      draft.splits.map((split) => (
                        <div key={split.id} className="flex items-center justify-between rounded-2xl border border-border bg-muted/20 p-3">
                          {editingSplitId === split.id ? (
                            <div className="grid w-full gap-3 md:grid-cols-[minmax(0,1fr)_160px_auto_auto]">
                              <Input value={editingSplitContactName} onChange={(e) => setEditingSplitContactName(e.target.value)} />
                              <Input value={editingSplitAmount} onChange={(e) => setEditingSplitAmount(formatAmountInput(e.target.value))} inputMode="numeric" />
                              <Button onClick={handleUpdateSplit} disabled={!editingSplitContactName.trim() || !editingSplitAmount || updateSplitMutation.isPending}>
                                {t("common.save")}
                              </Button>
                              <Button variant="outline" onClick={() => setEditingSplitId(null)}>
                                {t("common.cancel")}
                              </Button>
                            </div>
                          ) : (
                            <>
                              <div className="min-w-0">
                                <p className="truncate font-medium">{split.contact_name}</p>
                                <p className="text-sm text-muted-foreground">{t("expenses.splitRepaymentHint", { defaultValue: "Expected repayment" })}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <CurrencyAmount value={split.amount} format="display" />
                                <Button variant="ghost" size="sm" onClick={() => startEditingSplit(split)}>
                                  {t("common.edit", { defaultValue: "Edit" })}
                                </Button>
                                <Button variant="ghost" size="icon" onClick={() => deleteSplitMutation.mutate({ draftId: draft.id, splitId: split.id })}>
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              <div className="grid gap-3 sm:grid-cols-3">
                <Card className="shadow-sm">
                  <CardContent className="p-4">
                    <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{t("expenses.originalTotal", { defaultValue: "Original total" })}</p>
                    <div className="mt-2"><CurrencyAmount value={draft.original_total} format="display" className="text-xl font-bold tracking-tight" /></div>
                  </CardContent>
                </Card>
                <Card className="shadow-sm">
                  <CardContent className="p-4">
                    <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{t("expenses.amountPaid", { defaultValue: "Amount paid" })}</p>
                    <div className="mt-2"><CurrencyAmount value={draft.amount_paid || 0} format="display" className="text-xl font-bold tracking-tight" /></div>
                  </CardContent>
                </Card>
                <Card className="shadow-sm">
                  <CardContent className="p-4">
                    <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{t("expenses.allocatedWalletTotal", { defaultValue: "Allocated wallets" })}</p>
                    <div className="mt-2"><CurrencyAmount value={draft.allocated_wallet_total} format="display" className="text-xl font-bold tracking-tight" /></div>
                    {draft.remaining_wallet_allocation != null ? (
                      <p className="mt-1 text-sm text-muted-foreground">
                        {t("expenses.remaining", { defaultValue: "Remaining" })}: {draft.remaining_wallet_allocation}
                      </p>
                    ) : null}
                  </CardContent>
                </Card>
                <Card className="shadow-sm">
                  <CardContent className="p-4">
                    <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{t("expenses.splitTotal", { defaultValue: "Friend splits" })}</p>
                    <div className="mt-2"><CurrencyAmount value={draft.split_total || 0} format="display" className="text-xl font-bold tracking-tight" /></div>
                  </CardContent>
                </Card>
                <Card className="shadow-sm sm:col-span-2 lg:col-span-1">
                  <CardContent className="p-4">
                    <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{t("expenses.canFinalize", { defaultValue: "Ready to finalize" })}</p>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant={draft.can_finalize ? "secondary" : "outline"}>
                        {draft.can_finalize ? t("common.ready", { defaultValue: "Ready" }) : t("common.pending", { defaultValue: "Pending" })}
                      </Badge>
                      <span className="text-sm text-muted-foreground">{draft.status}</span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {draft.can_finalize
                        ? t("expenses.sessionFinalizeHintReady", { defaultValue: "Items and wallet allocations are aligned." })
                        : t("expenses.sessionFinalizeHintPending", { defaultValue: "Keep adjusting items, paid amount, or wallet allocations until the session balances." })}
                    </p>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : (
            <Card className="border border-dashed shadow-sm">
              <CardContent className="flex min-h-[220px] flex-col items-center justify-center gap-3 p-6 text-center">
                <CalendarDays className="h-8 w-8 text-muted-foreground" />
                <div className="space-y-1">
                  <p className="font-medium">{t("expenses.sessionEmptyStateTitle", { defaultValue: "Create the session header first" })}</p>
                  <p className="text-sm text-muted-foreground">{t("expenses.sessionEmptyStateDesc", { defaultValue: "Once the draft exists, you can add items and wallet allocations." })}</p>
                </div>
              </CardContent>
            </Card>
          )}

          {actionError ? (
            <p className="text-sm font-medium text-red-500">{actionError}</p>
          ) : null}
        </div>
      )}
    </ResponsiveSessionShell>

      <BudgetRepairDialog
        open={budgetRepair.isOpen}
        onOpenChange={(open) => { if (!open) budgetRepair.close(); }}
        repairPrompt={budgetRepair.prompt}
        repairAmount={repairAmount}
        onAmountChange={(raw) => setRepairAmount(formatAmountInput(raw))}
        repairPending={budgetRepair.pending}
        repairError={budgetRepair.error}
        onClose={budgetRepair.close}
        onCreateBudget={() => budgetRepair.createBudgetAndReplay(parseAmountInput(repairAmount))}
      />
    </>
  );
}
