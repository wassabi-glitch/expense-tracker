import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateProject } from "@/lib/api/projects";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle } from "lucide-react";

export function EditProjectDialog({ open, onOpenChange, project, onSuccess }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const projectIsIsolated = (project?.project_type || (project?.is_isolated ? "ISOLATED" : "OVERLAY")) === "ISOLATED";

  const [title, setTitle] = useState("");
  const [startDate, setStartDate] = useState("");
  const [targetEndDate, setTargetEndDate] = useState("");
  const [targetEstimate, setTargetEstimate] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (open && project) {
      setTitle(project.title || "");
      setStartDate(project.start_date || "");
      setTargetEndDate(project.target_end_date || "");
      setTargetEstimate((project.overlay?.target_estimate ?? project.target_estimate) ? String(project.overlay?.target_estimate ?? project.target_estimate) : "");
      setErrorMsg("");
    }
  }, [open, project]);

  const updateMutation = useMutation({
    mutationFn: (payload) => updateProject(project.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      onOpenChange(false);
      if (onSuccess) onSuccess();
    },
    onError: (err) => {
      // Handle the validation error smoothly.
      const detail = err?.response?.data?.detail;
      if (detail === "projects.cannot_strand_spent_slices") {
        setErrorMsg(t("projects.errors.cannotStrandSpentSlices", {
          defaultValue: "Cannot update dates: this would strand budget allocations that already have actual spending. Please expand the dates or remove the spending first."
        }));
      } else if (detail === "projects.start_after_linked_expense") {
        setErrorMsg(t("projects.errors.startAfterLinkedExpense", {
          defaultValue: "Start date cannot be after the earliest linked expense."
        }));
      } else if (detail === "projects.end_before_linked_expense") {
        setErrorMsg(t("projects.errors.endBeforeLinkedExpense", {
          defaultValue: "Target end date cannot be before the latest linked expense."
        }));
      } else {
        setErrorMsg(err?.response?.data?.detail || err.message);
      }
    },
  });

  const handleSubmit = () => {
    setErrorMsg("");
    const parsedTargetEstimate = targetEstimate ? Number(String(targetEstimate).replace(/\s+/g, "")) : null;
    if (targetEstimate && (!Number.isFinite(parsedTargetEstimate) || parsedTargetEstimate <= 0)) {
      setErrorMsg(t("projects.targetEstimateInvalid", { defaultValue: "Target estimate must be greater than zero." }));
      return;
    }
    const payload = {
      title,
      start_date: startDate || null,
      target_end_date: targetEndDate || null,
    };
    if (!projectIsIsolated) {
      payload.target_estimate = parsedTargetEstimate;
    }
    updateMutation.mutate(payload);
  };

  const hasDateChanges = project && (startDate !== (project.start_date || "") || targetEndDate !== (project.target_end_date || ""));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t("projects.editProperties", { defaultValue: "Edit Project Properties" })}</DialogTitle>
          <DialogDescription>
            {t("projects.editDesc", { defaultValue: "Update project title or timeline." })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {errorMsg && (
            <div className="flex items-start gap-2 rounded-md bg-destructive/15 p-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="edit-project-title">{t("projects.title", { defaultValue: "Project Title" })}</Label>
            <Input
              id="edit-project-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={updateMutation.isPending}
            />
          </div>

          {!projectIsIsolated && (
            <div className="space-y-2">
              <Label htmlFor="edit-project-target-estimate">
                {t("projects.targetEstimate", { defaultValue: "Target estimate" })}
                <span className="ml-1 text-muted-foreground font-normal">({t("common.optional", { defaultValue: "Optional" })})</span>
              </Label>
              <Input
                id="edit-project-target-estimate"
                type="text"
                inputMode="numeric"
                value={targetEstimate}
                onChange={(e) => setTargetEstimate(e.target.value)}
                disabled={updateMutation.isPending}
                placeholder={t("projects.planningContextOnly", { defaultValue: "Planning context only" })}
              />
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="edit-project-start">{t("projects.startDate", { defaultValue: "Start Date" })}</Label>
              <Input
                id="edit-project-start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                disabled={updateMutation.isPending}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-project-end">
                {t("projects.targetEndDate", { defaultValue: "Target End Date" })}
                <span className="ml-1 text-muted-foreground font-normal">({t("common.optional", { defaultValue: "Optional" })})</span>
              </Label>
              <Input
                id="edit-project-end"
                type="date"
                value={targetEndDate}
                onChange={(e) => setTargetEndDate(e.target.value)}
                disabled={updateMutation.isPending}
              />
            </div>
          </div>

          {hasDateChanges && !projectIsIsolated && (
            <div className="rounded-md bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
              <p className="font-semibold">{t("projects.dateChangeWarningTitle", { defaultValue: "Date Change Warning" })}</p>
              <p className="mt-1">
                {t("projects.dateChangeWarningDesc", {
                  defaultValue: "Changing project dates may remove allocations that fall outside the new window. If any removed month has actual spending, the update will be rejected to protect your history.",
                })}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={updateMutation.isPending}>
            {t("common.cancel", { defaultValue: "Cancel" })}
          </Button>
          <Button onClick={handleSubmit} disabled={updateMutation.isPending || !title.trim()}>
            {updateMutation.isPending ? t("common.saving", { defaultValue: "Saving..." }) : t("common.save", { defaultValue: "Save Changes" })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
