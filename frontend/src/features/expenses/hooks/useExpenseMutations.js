import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
    createExpense,
    deleteExpense,
    updateExpense,
    refundExpense,
    splitExpense,
    markExpenseAsAsset,
    markExpenseAsRecurring,
    createExpenseMergeGroup,
    addExpensesToMergeGroup,
    removeExpenseFromMergeGroup,
} from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { localizeApiError } from "@/lib/errorMessages";

// ... (keep helper functions)

export function useRefundExpenseMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: (payload) => refundExpense(payload),
        onSuccess: () => {},
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.expense.failedToRefund", { defaultValue: "Failed to Refund" }), msg);
        },
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
            // Also invalidate wallets as money moved back
            await queryClient.invalidateQueries({ queryKey: ["wallets"] });
        },
    });
}

export function useSplitExpenseMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: (payload) => splitExpense(payload),
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.expense.failedToUpdate", { defaultValue: "Failed to update expense" }), msg);
        },
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}

export function useMarkExpenseAsAssetMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: (payload) => markExpenseAsAsset(payload),
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("assets.toastCreateFailed", { defaultValue: "Failed to create asset" }), msg);
        },
        onSettled: async () => {
            await Promise.all([
                invalidateExpenseDerivedQueries(queryClient),
                queryClient.invalidateQueries({ queryKey: ["assets"] }),
            ]);
        },
    });
}

export function useMarkExpenseAsRecurringMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: (payload) => markExpenseAsRecurring(payload),
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToCreate", { defaultValue: "Failed to create recurring expense" }), msg);
        },
        onSettled: async () => {
            await Promise.all([
                invalidateExpenseDerivedQueries(queryClient),
                queryClient.invalidateQueries({ queryKey: ["recurring", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
        },
    });
}

export function useCreateExpenseMergeGroupMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: (payload) => createExpenseMergeGroup(payload),
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("expenses.mergeFailed", { defaultValue: "Failed to create merge group" }), msg);
        },
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}

export function useAddExpensesToMergeGroupMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ groupId, payload }) => addExpensesToMergeGroup(groupId, payload),
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("expenses.mergeFailed", { defaultValue: "Failed to update merge group" }), msg);
        },
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}

export function useRemoveExpenseFromMergeGroupMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ groupId, expenseId }) => removeExpenseFromMergeGroup(groupId, expenseId),
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("expenses.mergeFailed", { defaultValue: "Failed to update merge group" }), msg);
        },
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}

function toAmount(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
}

function getCurrentDayOfMonth() {
    return Math.max(1, new Date().getDate());
}

function applySummaryDelta(queryClient, deltaSpent) {
    if (!deltaSpent) return;

    queryClient.setQueriesData({ queryKey: ["dashboard", "summary"] }, (old) => {
        if (!old || typeof old !== "object") return old;

        const nextSpent = Math.max(0, toAmount(old.spent) + deltaSpent);
        const income = toAmount(old.income);

        return {
            ...old,
            spent: nextSpent,
            remaining: income - nextSpent,
            daily_average: Math.round(nextSpent / getCurrentDayOfMonth()),
        };
    });
}

function findExpenseAmountInCache(queryClient, expenseId) {
    const expenseQueries = queryClient.getQueriesData({ queryKey: ["expenses"] });

    for (const [, data] of expenseQueries) {
        const items = Array.isArray(data?.items) ? data.items : [];
        const match = items.find((item) => item?.id === expenseId);
        if (match) return toAmount(match.amount);
    }

    return null;
}

async function invalidateExpenseDerivedQueries(queryClient) {
    await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["expenses"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["wallets"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["notifications"] }),
        queryClient.invalidateQueries({ queryKey: ["debts"] }),
    ]);
}

export function useCreateExpenseMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: createExpense,
        onMutate: async (payload) => {
            await queryClient.cancelQueries({ queryKey: ["dashboard", "summary"] });
            const previousSummaries = queryClient.getQueriesData({ queryKey: ["dashboard", "summary"] });
            applySummaryDelta(queryClient, toAmount(payload?.amount));
            return { previousSummaries };
        },
        onError: (error, _variables, context) => {
            for (const [key, data] of context?.previousSummaries || []) {
                queryClient.setQueryData(key, data);
            }
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.expense.failedToCreate"), msg);
        },
        onSuccess: () => {},
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}

export function useUpdateExpenseMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ id, payload }) => updateExpense(id, payload),
        onMutate: async () => {
            await queryClient.cancelQueries({ queryKey: ["dashboard", "summary"] });
            const previousSummaries = queryClient.getQueriesData({ queryKey: ["dashboard", "summary"] });
            return { previousSummaries };
        },
        onError: (error, _variables, context) => {
            for (const [key, data] of context?.previousSummaries || []) {
                queryClient.setQueryData(key, data);
            }
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.expense.failedToUpdate"), msg);
        },
        onSuccess: () => {},
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}

export function useDeleteExpenseMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: (id) => deleteExpense(id),
        onMutate: async (id) => {
            await queryClient.cancelQueries({ queryKey: ["dashboard", "summary"] });
            const previousSummaries = queryClient.getQueriesData({ queryKey: ["dashboard", "summary"] });
            const previousAmount = findExpenseAmountInCache(queryClient, id);
            const deltaSpent = previousAmount === null ? 0 : -previousAmount;
            applySummaryDelta(queryClient, deltaSpent);
            return { previousSummaries };
        },
        onError: (error, _variables, context) => {
            for (const [key, data] of context?.previousSummaries || []) {
                queryClient.setQueryData(key, data);
            }
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.expense.failedToDelete"), msg);
        },
        onSuccess: () => {},
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}
