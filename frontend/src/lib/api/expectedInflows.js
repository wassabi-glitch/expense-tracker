import { apiClient } from "./client";

export async function getExpectedInflows(params = {}) {
    const response = await apiClient.get("/expected-inflows", { params });
    return Array.isArray(response.data) ? response.data : [];
}

export async function getExpectedInflow(id) {
    const response = await apiClient.get(`/expected-inflows/${id}`);
    return response.data;
}

export async function createExpectedInflow(payload) {
    const response = await apiClient.post("/expected-inflows", payload);
    return response.data;
}

export async function updateExpectedInflow(id, payload) {
    const response = await apiClient.patch(`/expected-inflows/${id}`, payload);
    return response.data;
}

export async function deleteExpectedInflow(id) {
    await apiClient.delete(`/expected-inflows/${id}`);
}

export async function realizeExpectedInflow(id, payload) {
    const response = await apiClient.post(`/expected-inflows/${id}/realize`, payload);
    return response.data;
}

export async function rescheduleExpectedInflow(id, payload) {
    const response = await apiClient.post(`/expected-inflows/${id}/reschedule`, payload);
    return response.data;
}

export async function cancelExpectedInflow(id, payload = {}) {
    const response = await apiClient.post(`/expected-inflows/${id}/cancel`, payload);
    return response.data;
}

export async function writeOffExpectedInflow(id, payload = {}) {
    const response = await apiClient.post(`/expected-inflows/${id}/write-off`, payload);
    return response.data;
}

export async function reverseExpectedInflowWriteOff(id, writeOffId, payload = {}) {
    const response = await apiClient.post(`/expected-inflows/${id}/write-offs/${writeOffId}/reverse`, payload);
    return response.data;
}

export async function reverseExpectedInflowReceipt(id, realizationId, payload = {}) {
    const response = await apiClient.post(`/expected-inflows/${id}/realizations/${realizationId}/reverse`, payload);
    return response.data;
}

export async function reopenExpectedInflow(id) {
    const response = await apiClient.post(`/expected-inflows/${id}/reopen`);
    return response.data;
}

export async function reconcileExpectedInflow(id) {
    const response = await apiClient.post(`/expected-inflows/${id}/reconcile`);
    return response.data;
}

export async function getExpectedInflowTimeline(params) {
    const response = await apiClient.get("/expected-inflows/timeline", { params });
    return Array.isArray(response.data) ? response.data : [];
}

export async function getCashflow(params) {
    const response = await apiClient.get("/expected-inflows/cashflow", { params });
    return Array.isArray(response.data) ? response.data : [];
}
