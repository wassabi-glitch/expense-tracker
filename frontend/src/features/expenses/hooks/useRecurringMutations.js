import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
    createRecurringExpense,
    deleteRecurringExpense,
    patchRecurringActive,
    updateRecurringExpense,
} from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";

export function useCreateRecurringMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: createRecurringExpense,
        onSuccess: async (data) => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["recurring", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
            toast.success(
                t("toasts.recurring.created"),
                t("toasts.recurring.created_detail", { title: data.title, amount: formatUzs(data.amount) })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToCreate"), msg);
        },
    });
}

export function useUpdateRecurringMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ id, payload }) => updateRecurringExpense(id, payload),
        onSuccess: async (data) => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["recurring", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
            toast.success(
                t("toasts.recurring.updated"),
                t("toasts.recurring.updated_detail", { title: data.title, amount: formatUzs(data.amount) })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToUpdate"), msg);
        },
    });
}

export function useDeleteRecurringMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: deleteRecurringExpense,
        onSuccess: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: ["recurring", "list"] }),
                queryClient.invalidateQueries({ queryKey: ["dashboard", "recurring"] }),
            ]);
            toast.success(t("toasts.recurring.deleted"));
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToDelete"), msg);
        },
    });
}

export function useToggleRecurringMutation() {
    const { t } = useTranslation();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ id, is_active }) => patchRecurringActive(id, is_active),
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToToggle"), msg);
        },
    });
}
