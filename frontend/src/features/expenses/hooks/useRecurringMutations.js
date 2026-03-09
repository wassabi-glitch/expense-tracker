import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
    createRecurringExpense,
    deleteRecurringExpense,
    patchRecurringActive,
    updateRecurringExpense,
} from "@/lib/api";

export function useCreateRecurringMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: createRecurringExpense,
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["recurring", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
        },
    });
}

export function useUpdateRecurringMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, payload }) => updateRecurringExpense(id, payload),
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["recurring", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
        },
    });
}

export function useDeleteRecurringMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: deleteRecurringExpense,
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["recurring", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
        },
    });
}

export function useToggleRecurringMutation() {
    return useMutation({
        mutationFn: ({ id, is_active }) => patchRecurringActive(id, is_active),
    });
}
