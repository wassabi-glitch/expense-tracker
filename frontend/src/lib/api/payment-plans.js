import { apiClient } from "./client";

export async function getPaymentPlanSummary() {
  const response = await apiClient.get("/payment-plans/summary");
  return response.data;
}

export async function getPaymentPlans(params = {}) {
  const { status, limit = 50, skip = 0 } = params;
  const response = await apiClient.get("/payment-plans", {
    params: { status, limit, skip },
  });
  return response.data;
}

export async function getPaymentPlan(planId) {
  const response = await apiClient.get(`/payment-plans/${planId}`);
  return response.data;
}

export async function getPaymentPlanDetails(planId) {
  const response = await apiClient.get(`/payment-plans/${planId}/details`);
  return response.data;
}

export async function createPaymentPlan(payload) {
  const response = await apiClient.post("/payment-plans", payload);
  return response.data;
}

export async function updatePaymentPlan(planId, payload) {
  const response = await apiClient.patch(`/payment-plans/${planId}`, payload);
  return response.data;
}

export async function recordPaymentPlanPayment(planId, payload) {
  const response = await apiClient.post(`/payment-plans/${planId}/payments`, payload);
  return response.data;
}

export async function markPaymentPlanPaymentPaid(paymentId, payload = {}) {
  const response = await apiClient.post(`/payment-plans/payments/${paymentId}/mark-paid`, payload);
  return response.data;
}

export async function writeOffPaymentPlanPayment(paymentId) {
  const response = await apiClient.post(`/payment-plans/payments/${paymentId}/write-off`);
  return response.data;
}

export async function undoPaymentPlanPaymentWriteOff(paymentId) {
  const response = await apiClient.post(`/payment-plans/payments/${paymentId}/undo-write-off`);
  return response.data;
}

export async function undoLatestPaymentPlanPayment(planId) {
  const response = await apiClient.post(`/payment-plans/${planId}/payments/undo-latest`);
  return response.data;
}

export async function addPaymentPlanCharge(planId, payload) {
  // eslint-disable-next-line no-unused-vars
  const { wallet_allocations, ...chargePayload } = payload || {};
  const response = await apiClient.post(`/payment-plans/${planId}/charges`, chargePayload);
  return response.data;
}

export async function deletePaymentPlan(planId) {
  const response = await apiClient.delete(`/payment-plans/${planId}`);
  return response.data;
}
