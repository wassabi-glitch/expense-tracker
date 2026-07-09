import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  addPaymentPlanCharge,
  createPaymentPlan,
  deletePaymentPlan,
  getPaymentPlanDetails,
  getPaymentPlans,
  getPaymentPlanSummary,
  markPaymentPlanPaymentPaid,
  recordPaymentPlanPayment,
  undoLatestPaymentPlanPayment,
  updatePaymentPlan,
  writeOffPaymentPlanPayment,
  undoPaymentPlanPaymentWriteOff,
} from "@/lib/api";
import { useToast } from "@/lib/context/ToastContext";
import { localizeApiError } from "@/lib/errorMessages";
import { invalidatePaymentPlanViews } from "@/lib/cacheInvalidation";

export function usePaymentPlanSummaryQuery() {
  return useQuery({
    queryKey: ["payment_plans", "summary"],
    queryFn: () => getPaymentPlanSummary(),
  });
}

export function usePaymentPlansQuery(params = {}) {
  return useQuery({
    queryKey: ["payment_plans", params],
    queryFn: () => getPaymentPlans(params),
  });
}

export function usePaymentPlanDetailsQuery(planId, options = {}) {
  return useQuery({
    queryKey: ["payment_plans", "details", planId],
    queryFn: () => getPaymentPlanDetails(planId),
    enabled: !!planId,
    ...options,
  });
}

export function useCreatePaymentPlanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPaymentPlan,
    onSuccess: async () => {
      await invalidatePaymentPlanViews(queryClient);
    },
  });
}

export function useUpdatePaymentPlanMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ planId, payload }) => updatePaymentPlan(planId, payload),
    onSuccess: async (_data, variables) => {
      await invalidatePaymentPlanViews(queryClient);
      if (variables?.planId) {
        await queryClient.invalidateQueries({ queryKey: ["payment_plans", "details", variables.planId] });
      }
      toast.success(t("payment_plans.toasts.updated", { defaultValue: "Payment plan updated" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("payment_plans.toasts.failedToUpdate", { defaultValue: "Failed to update payment plan" }), msg);
    },
  });
}

export function useDeletePaymentPlanMutation() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: (planId) => deletePaymentPlan(planId),
    onSuccess: async () => {
      await invalidatePaymentPlanViews(queryClient);
      toast.success(t("payment_plans.toasts.deleted", { defaultValue: "Payment plan deleted" }));
    },
    onError: (error) => {
      const msg = localizeApiError(error.message, t) || error.message;
      toast.error(t("payment_plans.toasts.failedToDelete", { defaultValue: "Failed to delete payment plan" }), msg);
    },
  });
}

export function useRecordPaymentPlanPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, payload }) => recordPaymentPlanPayment(planId, payload),
    onSuccess: async (_data, variables) => {
      await invalidatePaymentPlanViews(queryClient);
      if (variables?.planId) {
        await queryClient.invalidateQueries({ queryKey: ["payment_plans", "details", variables.planId] });
      }
    },
  });
}

export function useMarkPaymentPlanPaymentPaidMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ paymentId, payload }) => markPaymentPlanPaymentPaid(paymentId, payload || {}),
    onSuccess: async () => {
      await invalidatePaymentPlanViews(queryClient);
    },
  });
}

export function useAddPaymentPlanChargeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, payload }) => addPaymentPlanCharge(planId, payload),
    onSuccess: async (_data, variables) => {
      await invalidatePaymentPlanViews(queryClient);
      if (variables?.planId) {
        await queryClient.invalidateQueries({ queryKey: ["payment_plans", "details", variables.planId] });
      }
    },
  });
}

export function useWriteOffPaymentPlanPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paymentId) => writeOffPaymentPlanPayment(paymentId),
    onSuccess: async () => {
      await invalidatePaymentPlanViews(queryClient);
    },
  });
}

export function useUndoPaymentPlanPaymentWriteOffMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paymentId) => undoPaymentPlanPaymentWriteOff(paymentId),
    onSuccess: async () => {
      await invalidatePaymentPlanViews(queryClient);
    },
  });
}

export function useUndoLatestPaymentPlanPaymentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId) => undoLatestPaymentPlanPayment(planId),
    onSuccess: async (_data, planId) => {
      await invalidatePaymentPlanViews(queryClient);
      if (planId) {
        await queryClient.invalidateQueries({ queryKey: ["payment_plans", "details", planId] });
      }
    },
  });
}
