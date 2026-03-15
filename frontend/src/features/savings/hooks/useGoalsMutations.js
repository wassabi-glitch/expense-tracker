import { useMutation, useQueryClient } from "@tanstack/react-query";
import { archiveGoal, contributeToGoal, createGoal, deleteGoal, restoreGoal, returnFromGoal, updateGoal } from "@/lib/api";

async function invalidateGoalQueries(queryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["goals"] }),
    queryClient.invalidateQueries({ queryKey: ["savings"] }),
    queryClient.invalidateQueries({ queryKey: ["users", "me"] }),
    queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
    queryClient.invalidateQueries({ queryKey: ["analytics"] }),
  ]);
}

export function useCreateGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createGoal,
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
    },
  });
}

export function useContributeToGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ goalId, payload }) => contributeToGoal(goalId, payload),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
    },
  });
}

export function useReturnFromGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ goalId, payload }) => returnFromGoal(goalId, payload),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
    },
  });
}

export function useUpdateGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ goalId, payload }) => updateGoal(goalId, payload),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
    },
  });
}

export function useArchiveGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (goalId) => archiveGoal(goalId),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
    },
  });
}

export function useRestoreGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (goalId) => restoreGoal(goalId),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
    },
  });
}

export function useDeleteGoalMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (goalId) => deleteGoal(goalId),
    onSuccess: async () => {
      await invalidateGoalQueries(queryClient);
    },
  });
}
