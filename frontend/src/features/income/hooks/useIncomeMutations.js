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
        onMutate: async ({ sourceId, isActive }) => {
            const keys = [
                ["income", "sources", true],
                ["income", "sources", false],
            ];

            await Promise.all(keys.map((queryKey) => queryClient.cancelQueries({ queryKey })));

            const previousByKey = keys.map((queryKey) => ({
                queryKey,
                data: queryClient.getQueryData(queryKey),
            }));

            for (const { queryKey } of previousByKey) {
                queryClient.setQueryData(queryKey, (old) => {
                    if (!Array.isArray(old)) return old;
                    return old.map((source) =>
                        source?.id === sourceId ? { ...source, is_active: isActive } : source,
                    );
                });
            }

            return { previousByKey };
        },
        onError: (_err, _vars, context) => {
            if (!context?.previousByKey) return;
            for (const entry of context.previousByKey) {
                queryClient.setQueryData(entry.queryKey, entry.data);
            }
        },
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
