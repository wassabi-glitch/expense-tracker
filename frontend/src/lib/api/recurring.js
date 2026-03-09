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

export async function patchRecurringActive(id, is_active) {
    const response = await apiClient.patch(`/recurring/${id}/active`, { is_active });
    return response.data;
}
