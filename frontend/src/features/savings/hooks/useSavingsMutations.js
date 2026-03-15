import { useMutation, useQueryClient } from "@tanstack/react-query";
import { depositToSavings, withdrawFromSavings } from "@/lib/api";

async function invalidateSavingsQueries(queryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["savings"] }),
    queryClient.invalidateQueries({ queryKey: ["users", "me"] }),
    queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
    queryClient.invalidateQueries({ queryKey: ["analytics"] }),
  ]);
}

export function useDepositToSavingsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: depositToSavings,
    onSuccess: async () => {
      await invalidateSavingsQueries(queryClient);
    },
  });
}

export function useWithdrawFromSavingsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: withdrawFromSavings,
    onSuccess: async () => {
      await invalidateSavingsQueries(queryClient);
    },
  });
}
