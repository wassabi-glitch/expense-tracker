import * as React from "react";
import {
  Archive,
  ArrowDownLeft,
  ArrowLeftRight,
  BriefcaseBusiness,
  CalendarClock,
  Eye,
  FileSpreadsheet,
  MoreHorizontal,
  Pencil,
  PlusCircle,
  ReceiptText,
  ShieldX,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { Progress } from "@/components/ui/progress";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatCompactUzs } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Isolated project card: spend-down funding UX.
 *
 * Overlay cards fill up toward a limit.
 * Isolated cards tick down as remaining funding shrinks.
 *
 * Card shape (active):
 *   Remaining funding (hero)
 *   Spent of Funded (secondary)
 *   Spend-down bar (remaining / funding, filled = remaining portion)
 *   Ends <date>   [3-dot menu]
 *
 * Card shape (completed):
 *   Remaining at completion (hero)
 *   Spent of Funded (secondary)
 *   Read-only funding bar
 *   Completed <date>  [3-dot menu]
 */

function getProjectStatusLabel(status, t) {
  if (status === "STOPPED") return t("projects.statusPaused", { defaultValue: "Paused" });
  if (status === "COMPLETED") return t("projects.statusCompleted", { defaultValue: "Completed" });
  if (status === "ARCHIVED") return t("projects.statusArchived", { defaultValue: "Archived" });
  return t("projects.statusActive", { defaultValue: "Active" });
}

export function IsolatedProjectCard({
  project,
  onEditProperties,
  onManageStructure,
  onViewDetails,
  onReopen,
  todayIso,
  disabled = false,
}) {
  const { t } = useTranslation();

  const isolatedDetails = project.isolated || {};
  const fundingLimit = Number(isolatedDetails.funding_limit ?? project.total_limit ?? 0);
  const spent = Number(project.spent || 0);
  const remaining = Number(project.remaining ?? Math.max(0, fundingLimit - spent));
  const remainingFunding = Number(isolatedDetails.remaining_funding ?? project.remaining_funding ?? 0);
  const releasedFunding = Number(isolatedDetails.released_funding ?? project.released_funding ?? 0);
  const unassignedFunding = Number(isolatedDetails.unassigned_funding ?? 0);

  const projectStatus = project.status || "ACTIVE";
  const projectIsActive = projectStatus === "ACTIVE";
  const projectIsCompleted = projectStatus === "COMPLETED";
  const projectIsArchived = projectStatus === "ARCHIVED";
  const canModify = !projectIsCompleted && !projectIsArchived;
  const isGoalGraduated = Boolean(project.origin_goal_id);
  const hasUnassigned = canModify && unassignedFunding > 0;

  // Spend-down bar: filled portion = remaining / fundingLimit.
  // When funding drops, the filled portion shrinks.
  const spendDownPercent = fundingLimit > 0
    ? Math.max(0, Math.min(100, Math.round((remaining / fundingLimit) * 100)))
    : 0;

  // Over-budget (spent > funding) is a warning state.
  const isOverStash = remaining < 0;

  const spentFull = formatCompactUzs(spent);
  const fundedFull = formatCompactUzs(fundingLimit);

  const targetEndLabel = project.target_end_date
    ? project.target_end_date
    : t("projects.noTargetEndDate", { defaultValue: "No end date" });

  const isOverdue = project.target_end_date && project.target_end_date < todayIso && projectIsActive;

  return (
    <Card
      className={cn(
        "border border-border/70 bg-background/70 shadow-sm transition-all duration-300",
        projectIsArchived ? "opacity-60" : "opacity-100",
      )}
    >
      <CardHeader className="space-y-3 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-lg">
              <span className="block truncate">{project.title}</span>
            </CardTitle>
            <CardDescription className="mt-1">
              {t("projects.isolatedCardHelp", {
                defaultValue: "Wallet-backed funding that spends down over time.",
              })}
            </CardDescription>
          </div>
          <div className="flex shrink-0 items-start gap-2">
            <div className="flex flex-col items-end gap-2">
              <span className="rounded-full border border-border/60 bg-background px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                {getProjectStatusLabel(projectStatus, t)}
              </span>
              <span className="rounded-full border border-border/60 bg-muted/30 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-foreground">
                {t("projects.isolated", { defaultValue: "Isolated" })}
              </span>
              {isGoalGraduated ? (
                <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-primary">
                  {t("projects.goalFunded", { defaultValue: "Goal-funded" })}
                </span>
              ) : null}
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-full"
                  aria-label={t("common.actions", { defaultValue: "Actions" })}
                  disabled={disabled}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {/* Edit properties — always available for active/stopped */}
                {canModify ? (
                  <DropdownMenuItem onSelect={() => onEditProperties?.(project)}>
                    <Pencil className="mr-2 h-4 w-4" />
                    {t("common.edit", { defaultValue: "Edit properties" })}
                  </DropdownMenuItem>
                ) : null}

                {/* Top-up — available for active isolated projects */}
                {canModify ? (
                  <DropdownMenuItem disabled>
                    <PlusCircle className="mr-2 h-4 w-4" />
                    {t("projects.addTopUp", { defaultValue: "Add top-up" })}
                  </DropdownMenuItem>
                ) : null}

                {/* Allocate unassigned — available when there's unassigned funding */}
                {hasUnassigned ? (
                  <DropdownMenuItem disabled>
                    <ArrowDownLeft className="mr-2 h-4 w-4" />
                    {t("projects.allocateUnassignedFunding", { defaultValue: "Allocate unassigned funding" })}
                  </DropdownMenuItem>
                ) : (
                  <DropdownMenuItem disabled className="text-muted-foreground/50">
                    <ArrowDownLeft className="mr-2 h-4 w-4" />
                    {t("projects.allocateUnassignedFunding", { defaultValue: "Allocate unassigned funding" })}
                  </DropdownMenuItem>
                )}

                {/* Rebalance — always available for active */}
                {canModify ? (
                  <DropdownMenuItem disabled>
                    <ArrowLeftRight className="mr-2 h-4 w-4" />
                    {t("projects.rebalanceFunding", { defaultValue: "Rebalance funding" })}
                  </DropdownMenuItem>
                ) : null}

                {/* Manage structure — available for active/stopped */}
                {canModify ? (
                  <DropdownMenuItem onSelect={() => onManageStructure?.(project)}>
                    <BriefcaseBusiness className="mr-2 h-4 w-4" />
                    {t("projects.manageStructure", { defaultValue: "Manage structure" })}
                  </DropdownMenuItem>
                ) : null}

                {/* Archive — available for active/stopped (not completed) */}
                {projectIsActive ? (
                  <DropdownMenuItem disabled>
                    <Archive className="mr-2 h-4 w-4" />
                    {t("common.archive", { defaultValue: "Archive" })}
                  </DropdownMenuItem>
                ) : null}

                <DropdownMenuSeparator />

                {/* Completed/Archived lifecycle */}
                {projectIsCompleted || projectIsArchived ? (
                  <DropdownMenuItem onSelect={() => onReopen?.(project.id)}>
                    <ShieldX className="mr-2 h-4 w-4" />
                    {projectIsArchived
                      ? t("common.restore", { defaultValue: "Restore" })
                      : t("projects.reopenProject", { defaultValue: "Reopen / restore" })}
                  </DropdownMenuItem>
                ) : null}

                {/* Placeholder actions for future slices */}
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => onViewDetails?.(project)}>
                  <Eye className="mr-2 h-4 w-4" />
                  {t("projects.viewDetails", { defaultValue: "View details" })}
                </DropdownMenuItem>
                <DropdownMenuItem disabled className="text-muted-foreground/50">
                  <ReceiptText className="mr-2 h-4 w-4" />
                  {t("projects.wrapUpAndSweep", { defaultValue: "Wrap up and sweep" })}
                </DropdownMenuItem>
                <DropdownMenuItem disabled className="text-muted-foreground/50">
                  <FileSpreadsheet className="mr-2 h-4 w-4" />
                  {t("projects.viewFundingReport", { defaultValue: "View funding report" })}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Hero: Remaining funding */}
        <div className="rounded-2xl border border-border/60 bg-muted/15 p-4">
          <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            {projectIsCompleted
              ? t("projects.remainingAtCompletion", { defaultValue: "Remaining at completion" })
              : isOverdue
                ? t("projects.remainingFundingOverdue", { defaultValue: "Remaining project funding" })
                : t("projects.remainingFunding", { defaultValue: "Remaining funding" })}
          </p>
          <CurrencyAmount
            value={remaining}
            format="display"
            className={cn(
              "mt-1 text-2xl font-bold tracking-tight",
              isOverStash ? "text-destructive" : "text-foreground",
            )}
          />
          <p className="mt-1 text-sm text-muted-foreground">
            {formatCompactUzs(spent)} {t("projects.spentOf", { defaultValue: "spent of" })}{" "}
            {fundedFull} {t("projects.funded", { defaultValue: "funded" })}
          </p>
        </div>

        {/* Spend-down progress bar */}
        <div className="space-y-1">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-sm font-medium text-foreground">
              {projectIsCompleted
                ? t("projects.finalStashBar", { defaultValue: "Final project stash" })
                : t("projects.protectedProjectStash", { defaultValue: "Protected project stash" })}
            </span>
            <span className="text-sm text-muted-foreground">
              {t("budgets.usedOf", {
                spent: formatCompactUzs(spent),
                limit: formatCompactUzs(fundingLimit),
              })}{" "}
              UZS
            </span>
          </div>
          {fundingLimit > 0 ? (
            <Progress
              value={spendDownPercent}
              indicatorClassName={cn(
                "rounded-full duration-700 ease-out",
                isOverStash
                  ? "bg-destructive shadow-[0_0_10px_rgba(239,68,68,0.45)]"
                  : spendDownPercent <= 25
                    ? "bg-orange-500 dark:bg-orange-400 shadow-[0_0_10px_rgba(249,115,22,0.35)]"
                    : "bg-primary shadow-[0_0_10px_rgba(34,197,94,0.35)]",
              )}
              trackClassName={cn(
                "rounded-full",
                isOverStash ? "bg-destructive/20" : "bg-primary/20",
              )}
              className="h-2.5 rounded-full"
            />
          ) : null}
        </div>

        {/* Compact status line */}
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {project.target_end_date ? (
            <span className="rounded-full border border-border/60 bg-background px-2.5 py-1">
              {projectIsCompleted
                ? t("projects.completedDate", { defaultValue: "Completed" }) + ": " + project.target_end_date
                : t("projects.endsDate", { defaultValue: "Ends" }) + ": " + project.target_end_date}
            </span>
          ) : null}
          {isOverdue && !projectIsCompleted ? (
            <span className="rounded-full border border-amber-400/40 bg-amber-500/10 px-2.5 py-1 text-amber-700 dark:text-amber-300">
              {t("projects.overdue", { defaultValue: "Overdue" })}
            </span>
          ) : null}
          {hasUnassigned ? (
            <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-primary">
              {t("projects.unassignedChip", {
                defaultValue: "{{amount}} unassigned",
                amount: formatCompactUzs(unassignedFunding),
              })}
            </span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}