import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logout, togglePremium, updateBudgetRolloverPreference } from "@/lib/api";

export function useLogoutMutation() {
    return useMutation({
        mutationFn: logout,
    });
}

export function useTogglePremiumMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: togglePremium,
        onSuccess: async (updatedUser) => {
            queryClient.setQueryData(["users", "me"], updatedUser);
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["users", "me"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
        },
    });
}

export function useUpdateBudgetRolloverPreferenceMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (enabled) => updateBudgetRolloverPreference(enabled),
        onSuccess: async (updatedUser) => {
            queryClient.setQueryData(["users", "me"], updatedUser);
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["users", "me"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
            ]);
        },
    });
}
