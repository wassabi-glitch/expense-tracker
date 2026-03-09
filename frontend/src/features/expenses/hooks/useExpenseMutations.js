import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createExpense, deleteExpense, updateExpense } from "@/lib/api";

export function useCreateExpenseMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: createExpense,
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["expenses"] });
        },
    });
}

export function useUpdateExpenseMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, payload }) => updateExpense(id, payload),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["expenses"] });
        },
    });
}

export function useDeleteExpenseMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id) => deleteExpense(id),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["expenses"] });
        },
    });
}
