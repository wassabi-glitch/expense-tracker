import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  addCharge,
  adjustDebtBalance,
  archiveDebt,
  createDebt,
  deleteDebt,
  deleteTransaction,
  forgiveDebt,
  forgiveDebtAmount,
  payWalletBackedObligation,
  recordPayment,
  restoreDebt,
  reverseDebtLedgerEntry,
  updateDebt,
  updateDebtFormalDetails,
} from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { formatUzs } from "@/lib/format";
import { localizeApiError } from "@/lib/errorMessages";
import { invalidateDebtViews } from "@/lib/cacheInvalidation";

export function useCreateDebtMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: createDebt,
    onSuccess: async (data) => {
      await invalidateDebtViews(queryClient);
      toast.success(
        t("debts.toasts.created"),
        t("debts.toasts.created_detail", { 
          title: data.counterparty_name, 
          amount: formatUzs(data.initial_amount)
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToCreate"), msg);
    },
  });
}

export function useRecordDebtPaymentMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (payload) => recordPayment(payload),
    onSuccess: async (data, payload) => {
      await invalidateDebtViews(queryClient);
      toast.success(
        t("debts.toasts.paymentRecorded"),
        t("debts.toasts.paymentRecorded_detail", { 
          amount: formatUzs(payload.amount)
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToRecordPayment"), msg);
    },
  });
}

export function useRecordDebtPaymentForDebtMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ debtId, payload }) => recordPayment({ debt_id: debtId, ...payload }),
    onSuccess: async (data, variables) => {
      await invalidateDebtViews(queryClient);
      if (variables?.debtId) {
        await queryClient.invalidateQueries({ queryKey: ["debts", "details", variables.debtId] });
      }
      toast.success(
        t("debts.toasts.paymentRecorded"),
        t("debts.toasts.paymentRecorded_detail", {
          amount: formatUzs(variables?.payload?.amount || 0),
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToRecordPayment"), msg);
    },
  });
}

export function usePayWalletBackedObligationMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ walletId, payload }) => payWalletBackedObligation(walletId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateDebtViews(queryClient);
      toast.success(
        t("debts.toasts.paymentRecorded"),
        t("debts.toasts.paymentRecorded_detail", {
          amount: formatUzs(variables?.payload?.amount || 0),
        })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToRecordPayment"), msg);
    },
  });
}

export function useUpdateDebtMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ debtId, payload }) => updateDebt(debtId, payload),
    onSuccess: async (data) => {
      await invalidateDebtViews(queryClient);
      toast.success(t("debts.toasts.updated"), data.counterparty_name);
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToUpdate"), msg);
    },
  });
}

export function useArchiveDebtMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (debtId) => archiveDebt(debtId),
    onSuccess: async (data) => {
      await invalidateDebtViews(queryClient);
      if (data?.id) {
        await queryClient.invalidateQueries({ queryKey: ["debts", "details", data.id] });
      }
      toast.success(t("debts.toasts.archived", { defaultValue: "Debt archived" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToArchive", { defaultValue: "Failed to archive debt" }), msg);
    },
  });
}

export function useRestoreDebtMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (debtId) => restoreDebt(debtId),
    onSuccess: async (data) => {
      await invalidateDebtViews(queryClient);
      if (data?.id) {
        await queryClient.invalidateQueries({ queryKey: ["debts", "details", data.id] });
      }
      toast.success(t("debts.toasts.restored", { defaultValue: "Debt restored" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToRestore", { defaultValue: "Failed to restore debt" }), msg);
    },
  });
}

export function useDeleteDebtMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (debtId) => deleteDebt(debtId),
    onSuccess: async () => {
      await invalidateDebtViews(queryClient);
      toast.success(t("debts.toasts.deleted"));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToDelete"), msg);
    },
  });
}

export function useDeleteTransactionMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (transactionId) => deleteTransaction(transactionId),
    onSuccess: async () => {
      await invalidateDebtViews(queryClient);
      toast.success(t("debts.toasts.transactionDeleted"));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToDeleteTransaction"), msg);
    },
  });
}

export function useAddChargeMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ debtId, payload }) => addCharge(debtId, payload),
    onSuccess: async (data) => {
      await invalidateDebtViews(queryClient);
      toast.success(
        t("debts.toasts.chargeAdded"),
        t("debts.toasts.chargeAdded_detail", { amount: formatUzs(data.amount) })
      );
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToAddCharge"), msg);
    },
  });
}

export function useForgiveDebtMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (debtId) => forgiveDebt(debtId),
    onSuccess: async () => {
      await invalidateDebtViews(queryClient);
      toast.success(t("debts.toasts.forgiven"));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToForgive"), msg);
    },
  });
}

export function useForgiveDebtAmountMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ debtId, payload }) => forgiveDebtAmount(debtId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateDebtViews(queryClient);
      if (variables?.debtId) {
        await queryClient.invalidateQueries({ queryKey: ["debts", "details", variables.debtId] });
      }
      toast.success(t("debts.toasts.forgiven"));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToForgive"), msg);
    },
  });
}

export function useAdjustDebtBalanceMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ debtId, payload }) => adjustDebtBalance(debtId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateDebtViews(queryClient);
      if (variables?.debtId) {
        await queryClient.invalidateQueries({ queryKey: ["debts", "details", variables.debtId] });
      }
      toast.success(t("debts.toasts.balanceAdjusted", { defaultValue: "Debt balance adjusted" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToAdjustBalance", { defaultValue: "Failed to adjust balance" }), msg);
    },
  });
}

export function useReverseDebtLedgerEntryMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ debtId, entryId, payload }) => reverseDebtLedgerEntry(debtId, entryId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateDebtViews(queryClient);
      if (variables?.debtId) {
        await queryClient.invalidateQueries({ queryKey: ["debts", "details", variables.debtId] });
      }
      toast.success(t("debts.toasts.reversed", { defaultValue: "Debt action reversed" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToReverse", { defaultValue: "Failed to reverse action" }), msg);
    },
  });
}

export function useUpdateDebtFormalDetailsMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ debtId, payload }) => updateDebtFormalDetails(debtId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateDebtViews(queryClient);
      if (variables?.debtId) {
        await queryClient.invalidateQueries({ queryKey: ["debts", "details", variables.debtId] });
      }
      toast.success(t("debts.toasts.formalDetailsUpdated", { defaultValue: "Debt details updated" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error, t) || error.message;
      toast.error(t("debts.toasts.failedToUpdate", { defaultValue: "Failed to update debt" }), msg);
    },
  });
}
