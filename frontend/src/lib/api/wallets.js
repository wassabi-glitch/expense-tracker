import { apiClient } from "../api/client";

function normalizeArrayPayload(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

export const getWallets = () =>
  apiClient.get("/wallets").then((res) => normalizeArrayPayload(res.data));

export const getWalletTransactions = (walletId, params = {}) =>
  apiClient.get(`/wallets/${walletId}/transactions`, { params }).then((res) => res.data);

export const createWallet = (payload) => apiClient.post("/wallets", payload).then((res) => res.data);

export const updateWallet = (id, payload) => apiClient.patch(`/wallets/${id}`, payload).then((res) => res.data);

export const deleteWallet = (id) => apiClient.delete(`/wallets/${id}`).then((res) => res.data);

export const transferFunds = (payload) => apiClient.post("/wallets/transfer", payload).then((res) => res.data);

export const setDefaultWallet = (id) => apiClient.post(`/wallets/${id}/set-default`).then((res) => res.data);

export const recordWalletFee = (id, payload) => apiClient.post(`/wallets/${id}/fee`, payload).then((res) => res.data);
export const recordWalletInterest = (id, payload) => apiClient.post(`/wallets/${id}/interest`, payload).then((res) => res.data);

export const reconcileWalletBalance = (id, payload) => apiClient.post(`/wallets/${id}/reconcile`, payload).then((res) => res.data);
