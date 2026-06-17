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

export function useWalletMutations() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { t } = useTranslation();

  const createMutation = useMutation({
    mutationFn: createWallet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateWallet(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["income"] });
      queryClient.invalidateQueries({ queryKey: ["debts"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWallet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["income"] });
      queryClient.invalidateQueries({ queryKey: ["debts"] });
    },
  });

  const transferMutation = useMutation({
    mutationFn: transferFunds,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["income"] });
      queryClient.invalidateQueries({ queryKey: ["debts"] });
    },
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id) => setDefaultWallet(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
    },
  });

  const recordFeeMutation = useMutation({
    mutationFn: ({ id, payload }) => recordWalletFee(id, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["income"] });
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      
      if (data?.warning) {
        toast.warning(t("common.warning"), t(data.warning));
      }
    },
  });

  const recordInterestMutation = useMutation({
    mutationFn: ({ id, payload }) => recordWalletInterest(id, payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["income"] });
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });

      if (data?.warning) {
        toast.warning(t("common.warning"), t(data.warning));
      }
    },
  });

  const reconcileMutation = useMutation({
    mutationFn: ({ id, payload }) => reconcileWalletBalance(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      queryClient.invalidateQueries({ queryKey: ["income"] });
      queryClient.invalidateQueries({ queryKey: ["debts"] });
    },
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
