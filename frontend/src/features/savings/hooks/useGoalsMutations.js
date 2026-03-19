import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { archiveGoal, contributeToGoal, createGoal, deleteGoal, restoreGoal, returnFromGoal, updateGoal } from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";

async function invalidateGoalQueries(queryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["goals"] }),
    queryClient.invalidateQueries({ queryKey: ["savings"] }),
    queryClient.invalidateQueries({ queryKey: ["users", "me"] }),
    queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
    queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  ]);
}

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
      toast.success(
        t("toasts.goal.contributed"),
        t("toasts.goal.contributed_detail", { goal: data.title, amount: formatUzs(vars.payload.amount) })
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
