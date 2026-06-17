import { apiClient } from "./client";

export async function getDebtsSummary() {
  const response = await apiClient.get("/debts/summary");
  return response.data;
}

export async function getDebts(params = {}) {
  const { debt_type, status, search, limit = 50, skip = 0 } = params;
  const response = await apiClient.get("/debts", {
    params: { debt_type, status, search, limit, skip },
  });
  return response.data;
}

export async function getDebt(debtId) {
  const response = await apiClient.get(`/debts/${debtId}`);
  return response.data;
}

export async function getDebtDetails(debtId) {
  const response = await apiClient.get(`/debts/${debtId}/details`);
  return response.data;
}

export async function getDebtActions(debtId) {
  const response = await apiClient.get(`/debts/${debtId}/actions`);
  return response.data;
}

export async function createDebt(payload) {
  const response = await apiClient.post("/debts", payload);
  return response.data;
}

export async function updateDebt(debtId, payload) {
  const response = await apiClient.patch(`/debts/${debtId}`, payload);
  return response.data;
}

export async function deleteDebt(debtId) {
  const response = await apiClient.delete(`/debts/${debtId}`);
  return response.data;
}

export async function getDebtPayments(debtId, params = {}) {
  // Backend returns transactions embedded on the details endpoint.
  const response = await apiClient.get(`/debts/${debtId}/details`, { params });
  return response.data.transactions || [];
}

function normalizeDebtPaymentPayload(payload = {}) {
  const { debtId: directDebtId, debt_id, wallet_id, ...rest } = payload;
  const walletAllocations = Array.isArray(payload.wallet_allocations)
    ? payload.wallet_allocations
    : wallet_id
      ? [{ wallet_id: Number(wallet_id), amount: Number(payload.amount) }]
      : [];

  return {
    debtId: directDebtId ?? debt_id,
    body: {
      ...rest,
      amount: Number(payload.amount),
      wallet_allocations: walletAllocations,
    },
  };
}

export async function recordDebtPayment(debtId, payload) {
  const response = await apiClient.post(`/debts/${debtId}/payments`, payload);
  return response.data;
}

export async function recordPayment(payload) {
  const { debtId, body } = normalizeDebtPaymentPayload(payload);
  if (!debtId) {
    const response = await apiClient.post("/debts/transactions", payload);
    return response.data;
  }
  return recordDebtPayment(debtId, body);
}

export async function payWalletBackedObligation(walletId, payload) {
  const response = await apiClient.post(`/debts/wallet-obligations/${walletId}/payoff`, payload);
  return response.data;
}

export async function updatePayment(debtId, paymentId, payload) {
  const response = await apiClient.patch(
    `/debts/transactions/${paymentId}`,
    payload
  );
  return response.data;
}

export async function deleteTransaction(transactionId) {
  const response = await apiClient.delete(`/debts/transactions/${transactionId}`);
  return response.data;
}

export async function addCharge(debtId, payload) {
  const response = await apiClient.post(`/debts/${debtId}/charges`, payload);
  return response.data;
}

export async function addDebtCharge(debtId, payload) {
  return addCharge(debtId, payload);
}

export async function forgiveDebt(debtId) {
  const response = await apiClient.post(`/debts/${debtId}/forgive`);
  return response.data;
}

export async function forgiveDebtAmount(debtId, payload = {}) {
  const response = await apiClient.post(`/debts/${debtId}/forgiveness`, payload);
  return response.data;
}

export async function settleDebt(debtId, payload) {
  const response = await apiClient.post(`/debts/${debtId}/settlements`, payload);
  return response.data;
}

export async function adjustDebtBalance(debtId, payload) {
  const response = await apiClient.post(`/debts/${debtId}/balance-adjustments`, payload);
  return response.data;
}

export async function reverseDebtLedgerEntry(debtId, entryId, payload = {}) {
  const response = await apiClient.post(`/debts/${debtId}/ledger/${entryId}/reverse`, payload);
  return response.data;
}

export async function updateDebtFormalDetails(debtId, payload) {
  const response = await apiClient.patch(`/debts/${debtId}/formal-details`, payload);
  return response.data;
}

export async function generateInstallments(debtId, payload) {
  const response = await apiClient.post(
    `/debts/${debtId}/generate-installments`,
    payload
  );
  return response.data;
}
