import { useTranslation } from "react-i18next";
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
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";

async function invalidateIncomeDerivedQueries(queryClient) {
    await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["income"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
        queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    ]);
}

export function useCreateIncomeSourceMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();
    return useMutation({
        mutationFn: createIncomeSource,
        onSuccess: async (data) => {
            await invalidateIncomeDerivedQueries(queryClient);
            toast.success(t("toasts.income.sourceCreated"), data.name);
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.income.failedToCreateSource"), msg);
        },
    });
}

export function useUpdateIncomeSourceMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();
    return useMutation({
        mutationFn: ({ sourceId, payload }) => updateIncomeSource(sourceId, payload),
        onSuccess: async (data) => {
            await invalidateIncomeDerivedQueries(queryClient);
            toast.success(t("toasts.income.sourceUpdated"), data.name);
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.income.failedToUpdateSource"), msg);
        },
    });
}

export function useDeleteIncomeSourceMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();
    return useMutation({
        mutationFn: (sourceId) => deleteIncomeSource(sourceId),
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
            toast.success(t("toasts.income.sourceDeleted"));
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.income.failedToDeleteSource"), msg);
        },
    });
}

export function useToggleIncomeSourceActiveMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();
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
        onError: (error, _vars, context) => {
            if (!context?.previousByKey) return;
            for (const entry of context.previousByKey) {
                queryClient.setQueryData(entry.queryKey, entry.data);
            }
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.income.failedToToggleSource"), msg);
        },
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
        },
    });
}

export function useCreateIncomeEntryMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();
    return useMutation({
        mutationFn: createIncomeEntry,
        onSuccess: async (data) => {
            await invalidateIncomeDerivedQueries(queryClient);
            toast.success(
                t("toasts.income.entryCreated"),
                t("toasts.income.entryCreated_detail", { amount: formatUzs(data.amount) })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.income.failedToCreateEntry"), msg);
        },
    });
}

export function useUpdateIncomeEntryMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();
    return useMutation({
        mutationFn: ({ entryId, payload }) => updateIncomeEntry(entryId, payload),
        onSuccess: async (data) => {
            await invalidateIncomeDerivedQueries(queryClient);
            toast.success(
                t("toasts.income.entryUpdated"),
                t("toasts.income.entryUpdated_detail", { amount: formatUzs(data.amount) })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.income.failedToUpdateEntry"), msg);
        },
    });
}

export function useDeleteIncomeEntryMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();
    return useMutation({
        mutationFn: (entryId) => deleteIncomeEntry(entryId),
        onSuccess: async () => {
            await invalidateIncomeDerivedQueries(queryClient);
            toast.success(t("toasts.income.entryDeleted"));
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.income.failedToDeleteEntry"), msg);
        },
    });
}
