import { apiClient } from "./client";

export async function getInstallmentSummary() {
  const response = await apiClient.get("/installments/summary");
  return response.data;
}

export async function getInstallmentPlans(params = {}) {
  const { status, limit = 50, skip = 0 } = params;
  const response = await apiClient.get("/installments", {
    params: { status, limit, skip },
  });
  return response.data;
}

export async function getInstallmentPlan(planId) {
  const response = await apiClient.get(`/installments/${planId}`);
  return response.data;
}

export async function getInstallmentPlanDetails(planId) {
  const response = await apiClient.get(`/installments/${planId}/details`);
  return response.data;
}

export async function createInstallmentPlan(payload) {
  const response = await apiClient.post("/installments", payload);
  return response.data;
}

export async function recordInstallmentPayment(planId, payload) {
  const response = await apiClient.post(`/installments/${planId}/payments`, payload);
  return response.data;
}

export async function markInstallmentPaymentPaid(paymentId, payload = {}) {
  const response = await apiClient.post(`/installments/payments/${paymentId}/mark-paid`, payload);
  return response.data;
}

export async function writeOffInstallmentPayment(paymentId) {
  const response = await apiClient.post(`/installments/payments/${paymentId}/write-off`);
  return response.data;
}

export async function undoInstallmentPaymentWriteOff(paymentId) {
  const response = await apiClient.post(`/installments/payments/${paymentId}/undo-write-off`);
  return response.data;
}

export async function undoLatestInstallmentPayment(planId) {
  const response = await apiClient.post(`/installments/${planId}/payments/undo-latest`);
  return response.data;
}

export async function addInstallmentCharge(planId, payload) {
  const { wallet_allocations, ...chargePayload } = payload || {};
  const response = await apiClient.post(`/installments/${planId}/charges`, chargePayload);
  return response.data;
}

export async function deleteInstallmentPlan(planId) {
  const response = await apiClient.delete(`/installments/${planId}`);
  return response.data;
}
