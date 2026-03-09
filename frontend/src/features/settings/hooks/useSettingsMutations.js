import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logout, togglePremium } from "@/lib/api";

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
