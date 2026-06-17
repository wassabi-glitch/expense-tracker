import { apiClient } from "../api/client";

export const getAssets = (params = {}) =>
  apiClient
    .get("/assets", {
      params: {
        limit: params.limit,
        skip: params.skip,
        search: params.search || undefined,
        status_filter: params.statusFilter || undefined,
      },
    })
    .then((res) => res.data);

export const getAsset = (id) => apiClient.get(`/assets/${id}`).then((res) => res.data);

export const createAsset = (payload) => apiClient.post("/assets", payload).then((res) => res.data);

export const updateAsset = (id, payload) => apiClient.put(`/assets/${id}`, payload).then((res) => res.data);

export const sellAsset = (id, payload) => apiClient.post(`/assets/${id}/sell`, payload).then((res) => res.data);

export const giftAsset = (id, payload) => apiClient.post(`/assets/${id}/gift`, payload).then((res) => res.data);

export const disposeAsset = (id, payload) => apiClient.post(`/assets/${id}/dispose`, payload).then((res) => res.data);

export const markAssetLost = (id, payload) => apiClient.post(`/assets/${id}/lost`, payload).then((res) => res.data);
