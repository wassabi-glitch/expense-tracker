import { apiClient } from "./client";

export async function getRecurringExpenses() {
    const response = await apiClient.get("/recurring/");
    return response.data;
}

export async function createRecurringExpense(payload) {
    const response = await apiClient.post("/recurring/", payload);
    return response.data;
}

export async function updateRecurringExpense(id, payload) {
    const response = await apiClient.put(`/recurring/${id}`, payload);
    return response.data;
}

export async function deleteRecurringExpense(id) {
    const response = await apiClient.delete(`/recurring/${id}`);
    return response.data;
}

export async function patchRecurringActive(id, status) {
    const response = await apiClient.patch(`/recurring/${id}/toggle`, { status });
    return response.data;
}

export async function skipRecurringOccurrence(id, payload) {
    const response = await apiClient.post(`/recurring/occurrences/${id}/skip`, payload);
    return response.data;
}

export async function changeRecurringWallet(id, walletId) {
    const response = await apiClient.patch(`/recurring/${id}/change-wallet`, { wallet_id: walletId });
    return response.data;
}

export async function getRecurringEvents(id) {
    const response = await apiClient.get(`/recurring/${id}/events`);
    return response.data;
}

export async function getRecurringProjections(id) {
    const response = await apiClient.get(`/recurring/${id}/projections`);
    return response.data;
}

export async function previewRecurringProjections(id, horizons) {
    const response = await apiClient.post(`/recurring/${id}/projections/preview`, { horizons });
    return response.data;
}

export async function saveRecurringProjectionHorizons(id, horizons) {
    const response = await apiClient.put(`/recurring/${id}/projection-horizons`, { horizons });
    return response.data;
}

export async function getRecurringOccurrences(status) {
    const url = status ? `/recurring/occurrences?occurrence_status=${status}` : '/recurring/occurrences';
    const response = await apiClient.get(url);
    return response.data;
}

export async function confirmRecurringOccurrence(id, payload) {
    const response = await apiClient.post(`/recurring/occurrences/${id}/confirm`, payload);
    return response.data;
}
