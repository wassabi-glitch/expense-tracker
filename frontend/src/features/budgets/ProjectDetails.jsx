import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  BriefcaseBusiness,
  CalendarClock,
  ChartColumn,
  FolderKanban,
  Layers3,
  ReceiptText,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { getProject } from "@/lib/api";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { CurrencyAmount } from "@/components/CurrencyAmount";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/EmptyState";
import { localizeApiError } from "@/lib/errorMessages";
import { formatCompactUzs, formatDisplayDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import { toISODateInTimeZone } from "@/lib/date";
import { ProjectStructureEditor } from "./components/ProjectStructureEditor";
import { ProjectLifecyclePanel } from "./components/ProjectLifecyclePanel";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function DetailStat({ title, value, icon: Icon }) {
  return (
    <Card className="shadow-sm">
      <CardContent className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="text-ui-micro uppercase tracking-widest text-muted-foreground">{title}</p>
          <div className="mt-2 text-xl font-bold tracking-tight">{value}</div>
        </div>
        {Icon ? <Icon className="mt-0.5 h-5 w-5 text-muted-foreground" /> : null}
      </CardContent>
    </Card>
  );
}

function getProjectTypeLabel(project, t) {
  if (project.project_type === "ISOLATED" || project.is_isolated) {
    return t("projects.isolated", { defaultValue: "Isolated" });
  }
  return t("projects.overlay", { defaultValue: "Overlay" });
}

function getProjectStatusLabel(status, t) {
  if (status === "STOPPED") return t("projects.statusPaused", { defaultValue: "Paused" });
  if (status === "COMPLETED") return t("projects.statusCompleted", { defaultValue: "Completed" });
  if (status === "ARCHIVED") return t("projects.statusArchived", { defaultValue: "Archived" });
  return t("projects.statusActive", { defaultValue: "Active" });
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ProjectDetails() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const todayIso = toISODateInTimeZone();

  const projectQuery = useQuery({
    queryKey: ["projects", "detail", Number(projectId)],
    queryFn: () => getProject(Number(projectId)),
    enabled: !!projectId,
  });

  const project = projectQuery.data;

  // Derived state
  const projectIsIsolated = project
    ? project.project_type === "ISOLATED" || project.is_isolated
    : false;

  const isolatedDetails = project?.isolated || {};
  const overlayDetails = project?.overlay || {};

  const fundingLimit = Number(
    isolatedDetails.funding_limit ?? project?.total_limit ?? 0
  );
  const spent = Number(project?.spent || 0);
  const remaining = Number(
    project?.remaining ?? Math.max(0, fundingLimit - spent)
  );
  const remainingFunding = Number(
    isolatedDetails.remaining_funding ?? project?.remaining_funding ?? 0
  );
  const releasedFunding = Number(
    isolatedDetails.released_funding ?? project?.released_funding ?? 0
  );

  const targetEstimate = Number(
    overlayDetails.target_estimate ?? project?.target_estimate ?? 0
  );
  const selectedMonthReserved = Number(
    overlayDetails.selected_month_reserved_amount ??
      project?.selected_month_reserved_amount ??
      0
  );
  const totalReservedScope = Number(
    overlayDetails.total_reserved_scope ?? project?.total_reserved_scope ?? 0
  );

  const spendDownPercent =
    fundingLimit > 0
      ? Math.max(0, Math.min(100, Math.round((remaining / fundingLimit) * 100)))
      : 0;

  const overlayReservedPercent =
    selectedMonthReserved > 0
      ? Math.min(
          100,
          Math.round((spent / selectedMonthReserved) * 100)
        )
      : 0;

  const categoryBreakdown = useMemo(
    () => project?.category_breakdown || [],
    [project?.category_breakdown]
  );

  // -----------------------------------------------------------------------
  // Loading state
  // -----------------------------------------------------------------------
  if (projectQuery.isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-primary" />
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Error / missing-project state
  // -----------------------------------------------------------------------
  if (projectQuery.error || !project) {
    return (
      <div className="w-full px-page py-8">
        <EmptyState
          icon={BriefcaseBusiness}
          title={t("projects.detailsUnavailable", {
            defaultValue: "Project details unavailable",
          })}
          description={
            localizeApiError(projectQuery.error?.message, t) ||
            projectQuery.error?.message ||
            t("projects.detailsNotFound", {
              defaultValue: "Could not load this project.",
            })
          }
        />
      </div>
    );
  }

  const projectStatus = project.status || "ACTIVE";
  const projectIsActive = projectStatus === "ACTIVE";
  const projectIsCompleted = projectStatus === "COMPLETED";
  const projectIsArchived = projectStatus === "ARCHIVED";
  const isGoalFunded = Boolean(project.origin_goal_id);

  return (
    <div className="w-full space-y-6 px-page py-8">
      {/* Header */}
      <PageHeader
        title={project.title}
        description={
          project.description ||
          t("projects.detailDesc", {
            defaultValue: "Project overview and financial state",
          })
        }
      >
        <Button variant="outline" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("common.back", { defaultValue: "Back" })}
        </Button>
      </PageHeader>

      {/* Badge row */}
      <div className="flex flex-wrap gap-2">
        <Badge variant="outline">
          {getProjectTypeLabel(project, t)}
        </Badge>
        <Badge
          className={cn(
            projectIsActive && "border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300",
            projectStatus === "STOPPED" &&
              "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
            projectIsCompleted &&
              "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
            projectIsArchived &&
              "border-zinc-500/30 bg-zinc-500/10 text-zinc-700 dark:text-zinc-300"
          )}
        >
          {getProjectStatusLabel(projectStatus, t)}
        </Badge>
        {isGoalFunded ? (
          <Badge className="border-primary/20 bg-primary/10 text-primary">
            {t("projects.goalFunded", { defaultValue: "Goal-funded" })}
          </Badge>
        ) : null}
        {categoryBreakdown.length > 0 ? (
          <Badge variant="secondary">
            {t("projects.categoryCount", {
              defaultValue: "{{count}} categories",
              count: categoryBreakdown.length,
            })}
          </Badge>
        ) : null}
      </div>

      {/* Dates row */}
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <CalendarClock className="h-4 w-4" />
          {t("projects.startDate", { defaultValue: "Start" })}:{" "}
          {formatDisplayDate(project.start_date)}
        </span>
        {project.target_end_date ? (
          <span className="flex items-center gap-1.5">
            <CalendarClock className="h-4 w-4" />
            {projectIsCompleted
              ? t("projects.completedDate", { defaultValue: "Completed" })
              : t("projects.targetEndDate", { defaultValue: "Target end" })}
            : {formatDisplayDate(project.target_end_date)}
          </span>
        ) : null}
        {project.completed_at ? (
          <span className="flex items-center gap-1.5">
            <CalendarClock className="h-4 w-4" />
            {t("projects.completedAt", { defaultValue: "Completed at" })}:{" "}
            {formatDisplayDate(project.completed_at)}
          </span>
        ) : null}
        {project.selected_budget_year && project.selected_budget_month ? (
          <span className="flex items-center gap-1.5">
            <CalendarClock className="h-4 w-4" />
            {t("projects.monthContext", { defaultValue: "Month context" })}:{" "}
            {project.selected_budget_year}-
            {String(project.selected_budget_month).padStart(2, "0")}
          </span>
        ) : null}
      </div>

      {/* Financial summary */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {projectIsIsolated ? (
          <>
            <DetailStat
              title={t("projects.remainingFunding", {
                defaultValue: "Remaining funding",
              })}
              value={
                <CurrencyAmount value={remaining} format="display" />
              }
              icon={Layers3}
            />
            <DetailStat
              title={t("projects.spentOfFunded", {
                defaultValue: "Spent of funded",
              })}
              value={
                <span className="text-lg">
                  {formatCompactUzs(spent)} / {formatCompactUzs(fundingLimit)}
                </span>
              }
              icon={ReceiptText}
            />
            <DetailStat
              title={t("projects.releasedFunding", {
                defaultValue: "Released funding",
              })}
              value={
                <CurrencyAmount value={releasedFunding} format="display" />
              }
              icon={ChartColumn}
            />
          </>
        ) : (
          <>
            <DetailStat
              title={t("projects.targetEstimate", {
                defaultValue: "Target estimate",
              })}
              value={
                targetEstimate > 0 ? (
                  <CurrencyAmount value={targetEstimate} format="display" />
                ) : (
                  <span className="text-muted-foreground">—</span>
                )
              }
              icon={Layers3}
            />
            <DetailStat
              title={t("projects.spentThisMonth", {
                defaultValue: "Spent this month",
              })}
              value={
                <CurrencyAmount value={spent} format="display" />
              }
              icon={ReceiptText}
            />
            <DetailStat
              title={t("projects.selectedMonthReserved", {
                defaultValue: "Month reserved",
              })}
              value={
                <CurrencyAmount
                  value={selectedMonthReserved}
                  format="display"
                />
              }
              icon={FolderKanban}
            />
          </>
        )}
      </div>

      {/* Progress visualization */}
      {projectIsIsolated && fundingLimit > 0 ? (
        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              {t("projects.protectedProjectStash", {
                defaultValue: "Protected project stash",
              })}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span>
                {formatCompactUzs(spent)}{" "}
                {t("budgets.usedOf", { defaultValue: "used of" })}{" "}
                {formatCompactUzs(fundingLimit)}
              </span>
              <span className="text-muted-foreground">
                {spendDownPercent}%{" "}
                {t("projects.remaining", { defaultValue: "remaining" })}
              </span>
            </div>
            <Progress
              value={spendDownPercent}
              indicatorClassName={cn(
                "rounded-full duration-700 ease-out",
                remaining < 0
                  ? "bg-destructive shadow-[0_0_10px_rgba(239,68,68,0.45)]"
                  : spendDownPercent <= 25
                    ? "bg-orange-500 dark:bg-orange-400"
                    : "bg-primary shadow-[0_0_10px_rgba(34,197,94,0.35)]"
              )}
              trackClassName="rounded-full bg-primary/20"
              className="h-2.5 rounded-full"
            />
          </CardContent>
        </Card>
      ) : null}

      {!projectIsIsolated && selectedMonthReserved > 0 ? (
        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              {t("projects.monthReservationProgress", {
                defaultValue: "This month reservation progress",
              })}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span>
                {formatCompactUzs(spent)}{" "}
                {t("budgets.usedOf", { defaultValue: "used of" })}{" "}
                {formatCompactUzs(selectedMonthReserved)}{" "}
                {t("projects.reserved", { defaultValue: "reserved" })}
              </span>
              <span className="text-muted-foreground">
                {overlayReservedPercent}%{" "}
                {t("projects.consumed", { defaultValue: "consumed" })}
              </span>
            </div>
            <Progress
              value={overlayReservedPercent}
              indicatorClassName={cn(
                "rounded-full duration-700 ease-out",
                overlayReservedPercent >= 100
                  ? "bg-destructive"
                  : "bg-primary"
              )}
              trackClassName="rounded-full bg-primary/20"
              className="h-2.5 rounded-full"
            />
          </CardContent>
        </Card>
      ) : null}

      {/* Category breakdown summary */}
      {categoryBreakdown.length > 0 ? (
        <Card className="shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              {t("projects.categoryBreakdown", {
                defaultValue: "Category breakdown",
              })}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {categoryBreakdown.map((row, idx) => {
                const rowLimit = Number(row.limit_amount || 0);
                const rowSpent = Number(row.spent || 0);
                const rowRemaining = Number(row.remaining ?? rowLimit - rowSpent);
                const rowPercent =
                  rowLimit > 0
                    ? Math.min(100, Math.round((rowSpent / rowLimit) * 100))
                    : 0;

                return (
                  <div
                    key={`${row.category}-${idx}`}
                    className="flex flex-col gap-1 rounded-md border border-border/60 bg-muted/20 p-3"
                  >
                    <div className="flex items-baseline justify-between gap-3 text-sm">
                      <span className="font-medium">{row.category}</span>
                      <span className="text-muted-foreground">
                        {formatCompactUzs(rowSpent)} / {formatCompactUzs(rowLimit)}
                      </span>
                    </div>
                    {rowLimit > 0 ? (
                      <Progress
                        value={rowPercent}
                        indicatorClassName={cn(
                          "rounded-full",
                          row.is_over_limit ? "bg-destructive" : "bg-primary"
                        )}
                        trackClassName="rounded-full bg-primary/15"
                        className="h-1.5 rounded-full"
                      />
                    ) : null}
                    {row.subcategories?.length > 0
                      ? row.subcategories.map((sub) => {
                          const subLimit = Number(sub.limit_amount || 0);
                          const subSpent = Number(sub.spent || 0);
                          return (
                            <div
                              key={sub.id}
                              className="ml-4 flex items-baseline justify-between gap-3 text-xs text-muted-foreground"
                            >
                              <span>{sub.name}</span>
                              <span>
                                {formatCompactUzs(subSpent)} / {formatCompactUzs(subLimit)}
                              </span>
                            </div>
                          );
                        })
                      : null}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Structure editing */}
      <Card className="shadow-sm">
        <CardContent className="pt-6">
          <ProjectStructureEditor
            project={project}
            onMutationComplete={() =>
              projectQuery.refetch()
            }
          />
        </CardContent>
      </Card>

      {/* Lifecycle actions & deletion resolution */}
      <ProjectLifecyclePanel
        project={project}
        todayIso={todayIso}
        onMutationComplete={() => projectQuery.refetch()}
      />
    </div>
  );
}
