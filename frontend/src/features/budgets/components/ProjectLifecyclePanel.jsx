import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  CalendarClock,
  PauseCircle,
  PlayCircle,
  RotateCcw,
  ShieldX,
  Trash2,
  Unlink,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { useToast } from "@/lib/context/ToastContext";
import { localizeApiError } from "@/lib/errorMessages";
import { formatUzs } from "@/lib/format";
import {
  completeProject,
  deleteProject,
  getProjectDeletePreview,
  reopenProject,
  resolveProjectDeletion,
  resumeProject,
  stopProject,
} from "@/lib/api";
import {
  PROJECT_DELETE_ACTIONS,
  shouldOpenProjectDeletionResolution,
  canSubmitCascadeVoid,
  buildProjectDeletionResolutionPayload,
} from "../projectDeletionResolution";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const LIFECYCLE_ACTIONS = {
  PAUSE: "PAUSE",
  RESUME: "RESUME",
  COMPLETE: "COMPLETE",
  REOPEN: "REOPEN",
  ARCHIVE: "ARCHIVE",
  DELETE: "DELETE",
};

function getLifecycleConfirmLabels(action, project, todayIso, t) {
  const isOverdue =
    project?.target_end_date && project.target_end_date < todayIso;
  const isStopped = project?.status === "STOPPED";

  switch (action) {
    case LIFECYCLE_ACTIONS.PAUSE:
      return {
        title: t("projects.pauseProjectTitle", { defaultValue: "Pause project" }),
        description: t("projects.pauseProjectDesc", {
          defaultValue:
            "{{title}} will stop accepting new project expenses, but its overlay reservations will stay held.",
          title: project?.title || "",
        }),
        confirmText: t("projects.pauseProject", { defaultValue: "Pause project" }),
        note: t("projects.pauseProjectHoldNote", {
          defaultValue:
            "Reserved limits stay held while project expenses are paused.",
        }),
      };
    case LIFECYCLE_ACTIONS.RESUME:
      return {
        title: t("projects.resumeProjectTitle", {
          defaultValue: "Resume project",
        }),
        description: t("projects.resumeProjectDesc", {
          defaultValue:
            "{{title}} will accept project expenses again.",
          title: project?.title || "",
        }),
        confirmText: t("projects.resumeProject", {
          defaultValue: "Resume project",
        }),
        note: t("projects.resumeProjectSpendNote", {
          defaultValue:
            "The project can receive linked expenses again after resume.",
        }),
      };
    case LIFECYCLE_ACTIONS.COMPLETE:
      return {
        title: isOverdue
          ? t("projects.wrapUpProjectTitle", {
              defaultValue: "Wrap up project",
            })
          : isStopped
            ? t("projects.completeProjectNowTitle", {
                defaultValue: "Complete project now",
              })
            : t("projects.completeProjectEarlyTitle", {
                defaultValue: "Complete project early",
              }),
        description: t("projects.completeProjectDesc", {
          defaultValue:
            "{{title}} will be marked completed. Unused current and future overlay reservations will be swept back to the parent budgets.",
          title: project?.title || "",
        }),
        confirmText: isOverdue
          ? t("projects.wrapUpProject", {
              defaultValue: "Wrap up project",
            })
          : isStopped
            ? t("projects.completeNow", { defaultValue: "Complete now" })
            : t("projects.completeEarly", {
                defaultValue: "Complete early",
              }),
        note: t("projects.completeProjectSweepNote", {
          defaultValue:
            "Current and future overlay reservations will be reduced to actual spending. Past months stay unchanged.",
        }),
      };
    case LIFECYCLE_ACTIONS.REOPEN:
      return {
        title: t("projects.reopenProjectTitle", {
          defaultValue: "Reopen project",
        }),
        description: t("projects.reopenProjectDesc", {
          defaultValue:
            "{{title}} will be restored to active status.",
          title: project?.title || "",
        }),
        confirmText: t("projects.reopenProject", {
          defaultValue: "Reopen project",
        }),
      };
    case LIFECYCLE_ACTIONS.ARCHIVE:
      return {
        title: t("projects.archiveProjectTitle", {
          defaultValue: "Archive project",
        }),
        description: t("projects.archiveProjectDesc", {
          defaultValue:
            "{{title}} will be hidden from daily planning. Linked expenses stay attached.",
          title: project?.title || "",
        }),
        confirmText: t("common.archive", { defaultValue: "Archive" }),
      };
    default:
      return {
        title: "",
        description: "",
        confirmText: "",
      };
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ProjectLifecyclePanel({
  project,
  todayIso,
  onMutationComplete,
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();

  const projectIsIsolated =
    project.project_type === "ISOLATED" || project.is_isolated;
  const status = project.status || "ACTIVE";
  const isActive = status === "ACTIVE";
  const isStopped = status === "STOPPED";
  const isCompleted = status === "COMPLETED";
  const isArchived = status === "ARCHIVED";

  // Confirm dialog state
  const [confirmAction, setConfirmAction] = useState(null);

  // Deletion resolution state
  const [deletionOpen, setDeletionOpen] = useState(false);
  const [deletionPreview, setDeletionPreview] = useState(null);
  const [deletionConfirmTitle, setDeletionConfirmTitle] = useState("");

  // Cache invalidation shared by all lifecycle mutations
  const invalidateQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["projects"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "detail"] }),
      queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
      queryClient.invalidateQueries({ queryKey: ["expenses"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
    if (onMutationComplete) onMutationComplete();
  };

  // Mutations
  const stopMutation = useMutation({
    mutationFn: stopProject,
    onSuccess: async () => {
      await invalidateQueries();
      toast.success(
        t("projects.paused", { defaultValue: "Project paused" })
      );
    },
    onError: (e) =>
      toast.error(
        t("projects.pauseFailed", { defaultValue: "Failed to pause" }),
        localizeApiError(e.message, t) || e.message
      ),
  });

  const resumeMutation = useMutation({
    mutationFn: resumeProject,
    onSuccess: async () => {
      await invalidateQueries();
      toast.success(
        t("projects.resumed", { defaultValue: "Project resumed" })
      );
    },
    onError: (e) =>
      toast.error(
        t("projects.resumeFailed", { defaultValue: "Failed to resume" }),
        localizeApiError(e.message, t) || e.message
      ),
  });

  const completeMutation = useMutation({
    mutationFn: () => completeProject(project.id),
    onSuccess: async () => {
      await invalidateQueries();
      toast.success(
        t("projects.completed", { defaultValue: "Project completed" })
      );
    },
    onError: (e) =>
      toast.error(
        t("projects.completeFailed", { defaultValue: "Failed to complete" }),
        localizeApiError(e.message, t) || e.message
      ),
  });

  const reopenMutation = useMutation({
    mutationFn: reopenProject,
    onSuccess: async () => {
      await invalidateQueries();
      toast.success(
        t("projects.reopened", { defaultValue: "Project reopened" })
      );
    },
    onError: (e) =>
      toast.error(
        t("projects.reopenFailed", { defaultValue: "Failed to reopen" }),
        localizeApiError(e.message, t) || e.message
      ),
  });

  const deletePreviewMutation = useMutation({
    mutationFn: getProjectDeletePreview,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      await invalidateQueries();
      toast.success(
        t("projects.deleted", { defaultValue: "Project deleted" })
      );
    },
  });

  const resolveDeletionMutation = useMutation({
    mutationFn: ({ payload }) =>
      resolveProjectDeletion(project.id, payload),
    onSuccess: async (_data, variables) => {
      await invalidateQueries();
      setDeletionOpen(false);
      setDeletionPreview(null);
      setDeletionConfirmTitle("");
      const isArchive =
        variables?.payload?.action === PROJECT_DELETE_ACTIONS.ARCHIVE;
      toast.success(
        t(isArchive ? "projects.archived" : "projects.deleted", {
          defaultValue: isArchive ? "Project archived" : "Project deleted",
        })
      );
    },
    onError: (e) =>
      toast.error(
        t("projects.deleteResolutionFailed", {
          defaultValue: "Failed to resolve deletion",
        }),
        localizeApiError(e.message, t) || e.message
      ),
  });

  const isMutationPending =
    stopMutation.isPending ||
    resumeMutation.isPending ||
    completeMutation.isPending ||
    reopenMutation.isPending ||
    deleteMutation.isPending ||
    resolveDeletionMutation.isPending;

  // ---- Handlers ----

  const handleConfirmAction = async () => {
    if (!confirmAction) return;
    const action = confirmAction;
    setConfirmAction(null);
    try {
      if (action === LIFECYCLE_ACTIONS.PAUSE) await stopMutation.mutateAsync(project.id);
      else if (action === LIFECYCLE_ACTIONS.RESUME) await resumeMutation.mutateAsync(project.id);
      else if (action === LIFECYCLE_ACTIONS.COMPLETE) await completeMutation.mutateAsync();
      else if (action === LIFECYCLE_ACTIONS.REOPEN) await reopenMutation.mutateAsync(project.id);
      // ARCHIVE handled via deletion resolution
    } catch {
      /* toast handled by mutation onError */
    }
  };

  const handleDeleteClick = async () => {
    try {
      const preview = await deletePreviewMutation.mutateAsync(project.id);
      if (shouldOpenProjectDeletionResolution(preview)) {
        setDeletionPreview(preview);
        setDeletionConfirmTitle("");
        setDeletionOpen(true);
        return;
      }
      await deleteMutation.mutateAsync(project.id);
    } catch (e) {
      toast.error(
        t("projects.deleteFailed", { defaultValue: "Failed to delete" }),
        localizeApiError(e.message, t) || e.message
      );
    }
  };

  const handleResolveDeletion = async (action) => {
    const payload = buildProjectDeletionResolutionPayload(
      action,
      project,
      deletionConfirmTitle
    );
    try {
      await resolveDeletionMutation.mutateAsync({ payload });
    } catch {
      /* toast handled by mutation onError */
    }
  };

  const linkedExpenseCount = Number(
    deletionPreview?.linked_expense_count || 0
  );
  const linkedExpenseTotal = Number(
    deletionPreview?.linked_expense_total || 0
  );
  const canCascade = canSubmitCascadeVoid(project, deletionConfirmTitle);

  const confirmLabels = confirmAction
    ? getLifecycleConfirmLabels(confirmAction, project, todayIso, t)
    : { title: "", description: "", confirmText: "" };

  return (
    <div className="space-y-4">
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {t("projects.lifecycleActions", {
              defaultValue: "Project actions",
            })}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {/* Pause — Active projects only */}
            {isActive && projectIsIsolated ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setConfirmAction(LIFECYCLE_ACTIONS.PAUSE)
                }
                disabled={isMutationPending}
              >
                <PauseCircle className="mr-2 h-4 w-4" />
                {t("projects.pauseProject", { defaultValue: "Pause project" })}
              </Button>
            ) : null}

            {/* Pause — Overlay active projects */}
            {isActive && !projectIsIsolated ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setConfirmAction(LIFECYCLE_ACTIONS.PAUSE)
                }
                disabled={isMutationPending}
              >
                <PauseCircle className="mr-2 h-4 w-4" />
                {t("projects.pauseProject", { defaultValue: "Pause project" })}
              </Button>
            ) : null}

            {/* Resume — Stopped projects */}
            {isStopped ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setConfirmAction(LIFECYCLE_ACTIONS.RESUME)
                }
                disabled={isMutationPending}
              >
                <PlayCircle className="mr-2 h-4 w-4" />
                {t("projects.resumeProject", {
                  defaultValue: "Resume project",
                })}
              </Button>
            ) : null}

            {/* Complete — Active or Stopped */}
            {isActive || isStopped ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setConfirmAction(LIFECYCLE_ACTIONS.COMPLETE)
                }
                disabled={isMutationPending}
              >
                <CalendarClock className="mr-2 h-4 w-4" />
                {t("projects.completeProject", {
                  defaultValue: "Complete project",
                })}
              </Button>
            ) : null}

            {/* Reopen — Completed or Archived */}
            {isCompleted || isArchived ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setConfirmAction(LIFECYCLE_ACTIONS.REOPEN)
                }
                disabled={isMutationPending}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                {isArchived
                  ? t("common.restore", { defaultValue: "Restore" })
                  : t("projects.reopenProject", {
                      defaultValue: "Reopen project",
                    })}
              </Button>
            ) : null}

            {/* Delete — always available, with resolution if needed */}
            <Button
              variant="outline"
              size="sm"
              className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={handleDeleteClick}
              disabled={isMutationPending}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t("common.delete", { defaultValue: "Delete" })}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Lifecycle confirmation dialog */}
      <ConfirmDialog
        open={!!confirmAction}
        onOpenChange={(open) => !open && setConfirmAction(null)}
        title={confirmLabels.title}
        description={confirmLabels.description}
        onConfirm={handleConfirmAction}
        confirmText={confirmLabels.confirmText}
        cancelText={t("common.cancel", { defaultValue: "Cancel" })}
        confirmVariant={
          confirmAction === LIFECYCLE_ACTIONS.COMPLETE
            ? "default"
            : "outline"
        }
        isConfirming={isMutationPending}
      >
        {confirmAction && project ? (
          <div className="rounded-md border border-border/70 bg-muted/20 p-3 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">{project.title}</p>
            {confirmLabels.note ? (
              <p className="mt-1">{confirmLabels.note}</p>
            ) : null}
          </div>
        ) : null}
      </ConfirmDialog>

      {/* Deletion resolution */}
      {deletionOpen ? (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 space-y-4">
          <div>
            <h4 className="font-semibold">
              {t("projects.deleteResolutionHeading", {
                defaultValue: "Resolve linked expenses",
              })}
            </h4>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("projects.deleteResolutionIntro", {
                defaultValue:
                  "{{title}} has linked expenses. Choose what should happen to them.",
                title: project.title,
              })}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border border-border/60 bg-background p-3 text-center">
              <p className="text-xs uppercase tracking-widest text-muted-foreground">
                {t("projects.linkedExpenses", {
                  defaultValue: "Linked expenses",
                })}
              </p>
              <p className="mt-1 text-2xl font-bold">{linkedExpenseCount}</p>
            </div>
            <div className="rounded-md border border-border/60 bg-background p-3 text-center">
              <p className="text-xs uppercase tracking-widest text-muted-foreground">
                {t("projects.linkedExpenseTotal", {
                  defaultValue: "Linked total",
                })}
              </p>
              <CurrencyAmount
                value={linkedExpenseTotal}
                format="display"
                className="mt-1 text-xl font-bold"
              />
            </div>
          </div>

          <div className="space-y-3">
            {/* Archive */}
            <div className="rounded-md border border-border/70 bg-background/70 p-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold">
                    {t("projects.archiveOption", {
                      defaultValue: "Archive project",
                    })}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("projects.archiveOptionDesc", {
                      defaultValue:
                        "Hide the project from daily planning while keeping linked expenses attached.",
                    })}
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() =>
                    handleResolveDeletion(PROJECT_DELETE_ACTIONS.ARCHIVE)
                  }
                  disabled={isMutationPending}
                >
                  <Archive className="mr-2 h-4 w-4" />
                  {t("common.archive", { defaultValue: "Archive" })}
                </Button>
              </div>
            </div>

            {/* Detach expenses */}
            <div className="rounded-md border border-border/70 bg-background/70 p-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="font-semibold">
                    {t("projects.detachExpensesOption", {
                      defaultValue: "Detach expenses",
                    })}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t("projects.detachExpensesOptionDesc", {
                      defaultValue:
                        "Keep the expenses in your budgets as standalone spending, then remove the project.",
                    })}
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() =>
                    handleResolveDeletion(
                      PROJECT_DELETE_ACTIONS.DETACH_EXPENSES
                    )
                  }
                  disabled={isMutationPending}
                >
                  <Unlink className="mr-2 h-4 w-4" />
                  {t("projects.detachExpenses", {
                    defaultValue: "Detach",
                  })}
                </Button>
              </div>
            </div>

            {/* Remove linked expenses and project */}
            <div className="rounded-md border border-destructive/35 bg-destructive/5 p-3">
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <ShieldX className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
                  <div className="min-w-0">
                    <p className="font-semibold text-destructive">
                      {t("projects.removeExpensesAndProject", {
                        defaultValue:
                          "Remove linked expenses and project",
                      })}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {t("projects.removeExpensesAndProjectDesc", {
                        defaultValue:
                          "These expenses will no longer count in your budgets or wallet balances. Accounting history is preserved for accuracy.",
                      })}
                    </p>
                  </div>
                </div>
                <Input
                  value={deletionConfirmTitle}
                  onChange={(e) => setDeletionConfirmTitle(e.target.value)}
                  placeholder={project.title || ""}
                  aria-label={t("projects.confirmProjectName", {
                    defaultValue: "Confirm project name",
                  })}
                />
                <Button
                  variant="destructive"
                  className="w-full sm:w-auto"
                  onClick={() =>
                    handleResolveDeletion(
                      PROJECT_DELETE_ACTIONS.CASCADE_VOID
                    )
                  }
                  disabled={isMutationPending || !canCascade}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  {t("projects.removeLinkedExpenses", {
                    defaultValue: "Remove linked expenses",
                  })}
                </Button>
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            onClick={() => {
              setDeletionOpen(false);
              setDeletionPreview(null);
              setDeletionConfirmTitle("");
            }}
            disabled={isMutationPending}
          >
            {t("common.cancel", { defaultValue: "Cancel" })}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export default ProjectLifecyclePanel;
