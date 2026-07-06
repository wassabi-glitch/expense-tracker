import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  archiveGoal,
  consumeGoalAllocation,
  contributeToGoal,
  createGoal,
  deleteGoal,
  graduateGoalToProject,
  moveGoalFunding,
  recordGoalDebtPayment,
  recordGoalPurchase,
  releaseGoalToProject,
  restoreGoal,
  returnFromGoal,
  updateGoal,
  useReserveGoal as postUseReserveGoal,
} from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";
import { invalidateGoalQueries } from "../goalQueryInvalidation";

export function useCreateGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: createGoal,
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.created"),
        t("toasts.goal.created_detail", { title: data.title, amount: formatUzs(data.target_amount) })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToCreate"), msg);
    },
  });
}

export function useContributeToGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => contributeToGoal(goalId, payload),
    onSuccess: async (data, vars) => {
      await invalidateGoalQueries(queryClient);
      const amount = (vars.payload.allocations || []).reduce((sum, item) => sum + Number(item.amount || 0), 0);
      toast.success(
        t("toasts.goal.contributed"),
        t("toasts.goal.contributed_detail", { goal: data.title, amount: formatUzs(amount) })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToContribute"), msg);
    },
  });
}

export function useReturnFromGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => returnFromGoal(goalId, payload),
    onSuccess: async (data, vars) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.returned"),
        t("toasts.goal.returned_detail", { goal: data.title, amount: formatUzs(vars.payload.amount) })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToReturn"), msg);
    },
  });
}

export function useConsumeGoalAllocationMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => consumeGoalAllocation(goalId, payload),
    onSuccess: async (data, vars) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.consumed", { defaultValue: "Goal funding used" }),
        t("toasts.goal.consumed_detail", {
          defaultValue: "{{amount}} was released from {{goal}}.",
          goal: data.title,
          amount: formatUzs(vars.payload.amount),
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToConsume", { defaultValue: "Failed to use goal funding" }), msg);
    },
  });
}

export function useMoveGoalFundingMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => moveGoalFunding(goalId, payload),
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.fundingMoved", { defaultValue: "Goal money moved" }),
        t("toasts.goal.fundingMoved_detail", {
          defaultValue: "{{amount}} was moved to the payment wallet.",
          amount: formatUzs(data.moved_amount),
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToMoveFunding", { defaultValue: "Failed to move goal money" }), msg);
    },
  });
}

export function useUseReserveGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => postUseReserveGoal(goalId, payload),
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.reserveUsed", { defaultValue: "Reserve use recorded" }),
        t("toasts.goal.reserveUsed_detail", {
          defaultValue: "{{covered}} was covered by reserved money.",
          covered: formatUzs(data.consumed_amount),
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToUseReserve", { defaultValue: "Failed to use reserve" }), msg);
    },
  });
}

export function useRecordGoalPurchaseMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => recordGoalPurchase(goalId, payload),
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      const covered = data.consumed_amount || 0;
      toast.success(
        t("toasts.goal.purchaseRecorded", { defaultValue: "Purchase recorded" }),
        covered > 0
          ? t("toasts.goal.purchaseRecorded_detail", {
              defaultValue: "{{covered}} was covered by goal money.",
              covered: formatUzs(covered),
            })
          : t("toasts.goal.purchaseRecordedReleased_detail", {
              defaultValue: "The planned purchase was completed and {{released}} was released.",
              released: formatUzs(data.released_amount),
            })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToRecordPurchase", { defaultValue: "Failed to record purchase" }), msg);
    },
  });
}

export function useRecordGoalDebtPaymentMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => recordGoalDebtPayment(goalId, payload),
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.debtPaymentRecorded", { defaultValue: "Debt payment recorded" }),
        t("toasts.goal.debtPaymentRecorded_detail", {
          defaultValue: "{{amount}} was paid from reserved goal money.",
          amount: formatUzs(data.consumed_amount),
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToRecordDebtPayment", { defaultValue: "Failed to record debt payment" }), msg);
    },
  });
}

export function useGraduateGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => graduateGoalToProject(goalId, payload),
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.graduated"),
        t("toasts.goal.graduated_detail", { title: data.title, amount: formatUzs(data.total_limit || 0) })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToGraduate"), msg);
    },
  });
}

export function useReleaseGoalToProjectMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => releaseGoalToProject(goalId, payload),
    onSuccess: async (data, vars) => {
      await invalidateGoalQueries(queryClient);
      toast.success(
        t("toasts.goal.released"),
        t("toasts.goal.released_detail", { goal: data.title, amount: formatUzs(vars.payload.amount) })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToRelease"), msg);
    },
  });
}

export function useUpdateGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ goalId, payload }) => updateGoal(goalId, payload),
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      toast.success(t("toasts.goal.updated"), data.title);
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToUpdate"), msg);
    },
  });
}

export function useArchiveGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (goalId) => archiveGoal(goalId),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
      toast.success(t("toasts.goal.archived"));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToArchive"), msg);
    },
  });
}

export function useRestoreGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (goalId) => restoreGoal(goalId),
    onSuccess: async (data) => {
      await invalidateGoalQueries(queryClient);
      toast.success(t("toasts.goal.restored"), data.title);
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToRestore"), msg);
    },
  });
}

export function useDeleteGoalMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (goalId) => deleteGoal(goalId),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
      toast.success(t("toasts.goal.deleted"));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("toasts.goal.failedToDelete"), msg);
    },
  });
}
