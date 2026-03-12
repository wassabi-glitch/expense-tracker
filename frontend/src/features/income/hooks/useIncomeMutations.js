import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
    createIncomeEntry,
    createIncomeSource,
    deleteIncomeEntry,
    deleteIncomeSource,
    updateIncomeSourceActive,
    updateIncomeEntry,
    updateIncomeSource,
} from "@/lib/api";

async function invalidateIncomeDerivedQueries(queryClient) {
    await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["income"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
}

export function useCreateIncomeSourceMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: createIncomeSource,
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}

export function useUpdateIncomeSourceMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ sourceId, payload }) => updateIncomeSource(sourceId, payload),
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}

export function useDeleteIncomeSourceMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (sourceId) => deleteIncomeSource(sourceId),
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}

export function useToggleIncomeSourceActiveMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ sourceId, isActive }) => updateIncomeSourceActive(sourceId, isActive),
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}

export function useCreateIncomeEntryMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: createIncomeEntry,
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}

export function useUpdateIncomeEntryMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ entryId, payload }) => updateIncomeEntry(entryId, payload),
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}

export function useDeleteIncomeEntryMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (entryId) => deleteIncomeEntry(entryId),
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}
