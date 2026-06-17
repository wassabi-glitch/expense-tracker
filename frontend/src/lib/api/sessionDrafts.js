import { apiClient } from "./client";

export async function getActiveSessionDraft() {
    try {
        const response = await apiClient.get("/expenses/session-drafts/active");
        return response.data;
    } catch (error) {
        if (error?.status === 404) return null;
        throw error;
    }
}

export async function createSessionDraft(payload) {
    const response = await apiClient.post("/expenses/session-drafts", payload);
    return response.data;
}

export async function updateSessionDraft(draftId, payload) {
    const response = await apiClient.put(`/expenses/session-drafts/${draftId}`, payload);
    return response.data;
}

export async function pauseSessionDraft(draftId) {
    const response = await apiClient.post(`/expenses/session-drafts/${draftId}/pause`);
    return response.data;
}

export async function resumeSessionDraft(draftId) {
    const response = await apiClient.post(`/expenses/session-drafts/${draftId}/resume`);
    return response.data;
}

export async function abandonSessionDraft(draftId) {
    const response = await apiClient.post(`/expenses/session-drafts/${draftId}/abandon`);
    return response.data;
}

export async function addSessionDraftItem(draftId, payload) {
    const response = await apiClient.post(`/expenses/session-drafts/${draftId}/items`, payload);
    return response.data;
}

export async function updateSessionDraftItem(draftId, itemId, payload) {
    const response = await apiClient.put(`/expenses/session-drafts/${draftId}/items/${itemId}`, payload);
    return response.data;
}

export async function deleteSessionDraftItem(draftId, itemId) {
    const response = await apiClient.delete(`/expenses/session-drafts/${draftId}/items/${itemId}`);
    return response.data;
}

export async function addSessionWalletAllocation(draftId, payload) {
    const response = await apiClient.post(`/expenses/session-drafts/${draftId}/wallet-allocations`, payload);
    return response.data;
}

export async function updateSessionWalletAllocation(draftId, allocationId, payload) {
    const response = await apiClient.put(`/expenses/session-drafts/${draftId}/wallet-allocations/${allocationId}`, payload);
    return response.data;
}

export async function deleteSessionWalletAllocation(draftId, allocationId) {
    const response = await apiClient.delete(`/expenses/session-drafts/${draftId}/wallet-allocations/${allocationId}`);
    return response.data;
}

export async function addSessionDraftSplit(draftId, payload) {
    const response = await apiClient.post(`/expenses/session-drafts/${draftId}/splits`, payload);
    return response.data;
}

export async function updateSessionDraftSplit(draftId, splitId, payload) {
    const response = await apiClient.put(`/expenses/session-drafts/${draftId}/splits/${splitId}`, payload);
    return response.data;
}

export async function deleteSessionDraftSplit(draftId, splitId) {
    const response = await apiClient.delete(`/expenses/session-drafts/${draftId}/splits/${splitId}`);
    return response.data;
}

export async function finalizeSessionDraft(draftId) {
    const response = await apiClient.post(`/expenses/session-drafts/${draftId}/finalize`);
    return response.data;
}
