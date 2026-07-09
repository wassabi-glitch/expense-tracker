import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
    createRecurringExpense,
    deleteRecurringExpense,
    patchRecurringActive,
    updateRecurringExpense,
    skipRecurringOccurrence,
    changeRecurringWallet,
    confirmRecurringOccurrence,
} from "@/lib/api/recurring";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";
import {
    invalidateRecurringViews,
    invalidateRecurringConfirmationViews,
} from "@/lib/cacheInvalidation";

export function useCreateRecurringMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: createRecurringExpense,
        onSuccess: async (data) => {
            await invalidateRecurringViews(queryClient);
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
            await invalidateRecurringViews(queryClient);
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
            await invalidateRecurringViews(queryClient);
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
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, status }) => patchRecurringActive(id, status),
        onSuccess: async () => {
            await invalidateRecurringViews(queryClient);
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToToggle"), msg);
        },
    });
}

export function useSkipRecurringMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ id, payload }) => skipRecurringOccurrence(id, payload),
        onSuccess: async () => {
            await invalidateRecurringViews(queryClient);
            toast.success(t("toasts.recurring.skipped"));
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToSkip"), msg);
        },
    });
}


export function useChangeRecurringWalletMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ id, walletId }) => changeRecurringWallet(id, walletId),
        onSuccess: async () => {
            await invalidateRecurringViews(queryClient);
            toast.success(t("toasts.recurring.walletChanged"));
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToChangeWallet"), msg);
        },
    });
}

export function useConfirmRecurringOccurrenceMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: ({ id, payload }) => confirmRecurringOccurrence(id, payload),
        onSuccess: async () => {
            await invalidateRecurringConfirmationViews(queryClient);
            toast.success(t("toasts.recurring.confirmed"));
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.recurring.failedToConfirm"), msg);
        },
    });
}
