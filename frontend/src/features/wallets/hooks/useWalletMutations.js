import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/lib/context/ToastContext";
import { useTranslation } from "react-i18next";
import {
  createWallet,
  updateWallet,
  deleteWallet,
  transferFunds,
  setDefaultWallet,
  recordWalletFee,
  recordWalletInterest,
  reconcileWalletBalance
} from "@/lib/api";
import {
  invalidateWalletCreate,
  invalidateWalletMoneyMovement,
  invalidateWalletTransaction,
  invalidateWalletList,
} from "@/lib/cacheInvalidation";

export function useWalletMutations() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { t } = useTranslation();

  const createMutation = useMutation({
    mutationFn: createWallet,
    onSuccess: () => invalidateWalletCreate(queryClient),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateWallet(id, payload),
    onSuccess: () => invalidateWalletMoneyMovement(queryClient),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWallet,
    onSuccess: () => invalidateWalletMoneyMovement(queryClient),
  });

  const transferMutation = useMutation({
    mutationFn: transferFunds,
    onSuccess: () => invalidateWalletMoneyMovement(queryClient),
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id) => setDefaultWallet(id),
    onSuccess: () => invalidateWalletList(queryClient),
  });

  const recordFeeMutation = useMutation({
    mutationFn: ({ id, payload }) => recordWalletFee(id, payload),
    onSuccess: (data) => {
      invalidateWalletTransaction(queryClient);

      if (data?.warning) {
        toast.warning(t("common.warning"), t(data.warning));
      }
    },
  });

  const recordInterestMutation = useMutation({
    mutationFn: ({ id, payload }) => recordWalletInterest(id, payload),
    onSuccess: (data) => {
      invalidateWalletTransaction(queryClient);

      if (data?.warning) {
        toast.warning(t("common.warning"), t(data.warning));
      }
    },
  });

  const reconcileMutation = useMutation({
    mutationFn: ({ id, payload }) => reconcileWalletBalance(id, payload),
    onSuccess: () => invalidateWalletMoneyMovement(queryClient),
  });

  return {
    createMutation,
    updateMutation,
    deleteMutation,
    transferMutation,
    setDefaultMutation,
    recordFeeMutation,
    recordInterestMutation,
    reconcileMutation,
  };
}
