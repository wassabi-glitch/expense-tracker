import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createBudget, deleteBudget, updateBudget } from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";

export function useCreateBudgetMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ category, monthlyLimit, budgetYear, budgetMonth }) =>
            createBudget(category, monthlyLimit, budgetYear, budgetMonth),
        onSuccess: async (data) => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
                queryClient.invalidateQueries({ queryKey: ["notifications"] }),
            ]);
            toast.success(
                t("toasts.budget.created"),
                t("toasts.budget.created_detail", {
                    category: t(`categories.${data.category}`),
                    amount: formatUzs(data.monthly_limit),
                })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.budget.failedToCreate"), msg);
        },
    });
}

export function useUpdateBudgetMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ category, monthlyLimit, budgetYear, budgetMonth }) =>
            updateBudget(category, monthlyLimit, budgetYear, budgetMonth),
        onSuccess: async (data) => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
                queryClient.invalidateQueries({ queryKey: ["notifications"] }),
            ]);
            toast.success(
                t("toasts.budget.updated"),
                t("toasts.budget.updated_detail", {
                    category: t(`categories.${data.category}`),
                    amount: formatUzs(data.monthly_limit),
                })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.budget.failedToUpdate"), msg);
        },
    });
}

export function useDeleteBudgetMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ category, budgetYear, budgetMonth }) =>
            deleteBudget(category, budgetYear, budgetMonth),
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["budgets", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["budgets", "month-stats"] }),
                queryClient.invalidateQueries({ queryKey: ["notifications"] }),
            ]);
            toast.success(t("toasts.budget.deleted"));
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.budget.failedToDelete"), msg);
        },
    });
}
