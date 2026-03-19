import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createExpense, deleteExpense, updateExpense } from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";

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
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
        queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["notifications"] }),
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
        onSuccess: (data) => {
            toast.success(
                t("toasts.expense.created"),
                t("toasts.expense.created_detail", { title: data.title, amount: formatUzs(data.amount) })
            );
        },
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
        onMutate: async ({ id, payload }) => {
            await queryClient.cancelQueries({ queryKey: ["dashboard", "summary"] });
            const previousSummaries = queryClient.getQueriesData({ queryKey: ["dashboard", "summary"] });
            const previousAmount = findExpenseAmountInCache(queryClient, id);
            const nextAmount = toAmount(payload?.amount);
            const deltaSpent = previousAmount === null ? 0 : nextAmount - previousAmount;
            applySummaryDelta(queryClient, deltaSpent);
            return { previousSummaries };
        },
        onError: (error, _variables, context) => {
            for (const [key, data] of context?.previousSummaries || []) {
                queryClient.setQueryData(key, data);
            }
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.expense.failedToUpdate"), msg);
        },
        onSuccess: (data) => {
            toast.success(
                t("toasts.expense.updated"),
                t("toasts.expense.updated_detail", { title: data.title, amount: formatUzs(data.amount) })
            );
        },
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
        onSuccess: () => {
            toast.success(t("toasts.expense.deleted"));
        },
        onSettled: async () => {
            await invalidateExpenseDerivedQueries(queryClient);
        },
    });
}
