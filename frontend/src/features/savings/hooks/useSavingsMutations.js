import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { depositToSavings, withdrawFromSavings } from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";

async function invalidateSavingsQueries(queryClient) {
    await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["savings"] }),
        queryClient.invalidateQueries({ queryKey: ["users", "me"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    ]);
}

export function useDepositToSavingsMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: depositToSavings,
        onSuccess: async (data, variables) => {
            await invalidateSavingsQueries(queryClient);
            toast.success(
                t("toasts.savings.deposited"),
                t("toasts.savings.deposited_detail", { amount: formatUzs(variables.amount) })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.savings.failedToDeposit"), msg);
        },
    });
}

export function useWithdrawFromSavingsMutation() {
    const { t } = useTranslation();
    const queryClient = useQueryClient();
    const toast = useToast();

    return useMutation({
        mutationFn: withdrawFromSavings,
        onSuccess: async (data, variables) => {
            await invalidateSavingsQueries(queryClient);
            toast.success(
                t("toasts.savings.withdrawn"),
                t("toasts.savings.withdrawn_detail", { amount: formatUzs(variables.amount) })
            );
        },
        onError: (error) => {
            const msg = localizeApiError(error.message, t) || error.message;
            toast.error(t("toasts.savings.failedToWithdraw"), msg);
        },
    });
}
