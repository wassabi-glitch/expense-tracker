import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addInstallmentCharge,
  createInstallmentPlan,
  getInstallmentPlanDetails,
  getInstallmentPlans,
  getInstallmentSummary,
  markInstallmentPaymentPaid,
  recordInstallmentPayment,
  undoLatestInstallmentPayment,
  writeOffInstallmentPayment,
  undoInstallmentPaymentWriteOff,
} from "@/lib/api";

function invalidateInstallmentSideEffects(queryClient) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: ["installments"] }),
    queryClient.invalidateQueries({ queryKey: ["debts"] }),
    queryClient.invalidateQueries({ queryKey: ["expenses"] }),
    queryClient.invalidateQueries({ queryKey: ["budgets"] }),
    queryClient.invalidateQueries({ queryKey: ["wallets"] }),
    queryClient.invalidateQueries({ queryKey: ["assets"] }),
    queryClient.invalidateQueries({ queryKey: ["users", "me"] }),
    queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
    queryClient.invalidateQueries({ queryKey: ["analytics"] }),
    queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  ]);
}

export function useInstallmentSummaryQuery() {
  return useQuery({
    queryKey: ["installments", "summary"],
    queryFn: () => getInstallmentSummary(),
  });
}

export function useInstallmentPlansQuery(params = {}) {
  return useQuery({
    queryKey: ["installments", params],
    queryFn: () => getInstallmentPlans(params),
  });
}

export function useInstallmentPlanDetailsQuery(planId, options = {}) {
  return useQuery({
    queryKey: ["installments", "details", planId],
    queryFn: () => getInstallmentPlanDetails(planId),
    enabled: !!planId,
    ...options,
  });
}

export function useCreateInstallmentPlanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createInstallmentPlan,
    onSuccess: async () => {
      await invalidateInstallmentSideEffects(queryClient);
    },
  });
}

export function useRecordInstallmentPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, payload }) => recordInstallmentPayment(planId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateInstallmentSideEffects(queryClient);
      if (variables?.planId) {
        await queryClient.invalidateQueries({ queryKey: ["installments", "details", variables.planId] });
      }
    },
  });
}

export function useMarkPaymentPaidMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paymentId, payload }) => markInstallmentPaymentPaid(paymentId, payload || {}),
    onSuccess: async () => {
      await invalidateInstallmentSideEffects(queryClient);
    },
  });
}

export function useAddInstallmentChargeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, payload }) => addInstallmentCharge(planId, payload),
    onSuccess: async (_data, variables) => {
      await invalidateInstallmentSideEffects(queryClient);
      if (variables?.planId) {
        await queryClient.invalidateQueries({ queryKey: ["installments", "details", variables.planId] });
      }
    },
  });
}

export function useWriteOffPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paymentId) => writeOffInstallmentPayment(paymentId),
    onSuccess: async () => {
      await invalidateInstallmentSideEffects(queryClient);
    },
  });
}

export function useUndoWriteOffPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paymentId) => undoInstallmentPaymentWriteOff(paymentId),
    onSuccess: async () => {
      await invalidateInstallmentSideEffects(queryClient);
    },
  });
}

export function useUndoLatestInstallmentPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId) => undoLatestInstallmentPayment(planId),
    onSuccess: async (_data, planId) => {
      await invalidateInstallmentSideEffects(queryClient);
      if (planId) {
        await queryClient.invalidateQueries({ queryKey: ["installments", "details", planId] });
      }
    },
  });
}
