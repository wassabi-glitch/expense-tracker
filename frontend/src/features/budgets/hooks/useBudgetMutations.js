import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createBudget, deleteBudget, updateBudget } from "@/lib/api";

export function useCreateBudgetMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ category, monthlyLimit, budgetYear, budgetMonth }) =>
            createBudget(category, monthlyLimit, budgetYear, budgetMonth),
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
            ]);
        },
    });
}

export function useUpdateBudgetMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ category, monthlyLimit, budgetYear, budgetMonth }) =>
            updateBudget(category, monthlyLimit, budgetYear, budgetMonth),
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
            ]);
        },
    });
}

export function useDeleteBudgetMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ category, budgetYear, budgetMonth }) =>
            deleteBudget(category, budgetYear, budgetMonth),
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
            ]);
        },
    });
}
