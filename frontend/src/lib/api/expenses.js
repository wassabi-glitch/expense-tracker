import { apiClient } from "./client";

function compactParams(params = {}) {
    return Object.fromEntries(
        Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""),
    );
}

function getFilenameFromDisposition(contentDisposition) {
    const fileNameMatch = /filename="?([^";]+)"?/i.exec(contentDisposition || "");
    return fileNameMatch?.[1] || "expenses.csv";
}

export async function getExpenses(params = {}) {
    const response = await apiClient.get("/expenses", { params: compactParams(params) });
    return response.data;
}

export async function getExpenseDetail(id) {
    const response = await apiClient.get(`/expenses/${id}/detail`);
    return response.data;
}

export async function deleteExpense(id) {
    const response = await apiClient.delete(`/expenses/${id}`);
    return response.data;
}

export async function createExpense(payload) {
    const response = await apiClient.post("/expenses/", payload);
    return response.data;
}

export async function updateExpense(id, payload) {
    const response = await apiClient.put(`/expenses/${id}`, payload);
    return response.data;
}

export async function exportExpensesCsv(params = {}) {
    const response = await apiClient.get("/expenses/export", {
        params: compactParams(params),
        responseType: "blob",
    });

    return {
        blob: response.data,
        filename: getFilenameFromDisposition(response.headers?.["content-disposition"]),
    };
}

export async function refundExpense({ id, ...payload }) {
    const response = await apiClient.post(`/expenses/${id}/refund`, payload);
    return response.data;
}

export async function splitExpense({ id, ...payload }) {
    const response = await apiClient.post(`/expenses/${id}/split`, payload);
    return response.data;
}

export async function markExpenseAsAsset({ id, ...payload }) {
    const response = await apiClient.post(`/expenses/${id}/mark-as-asset`, payload);
    return response.data;
}

export async function markExpenseAsRecurring({ id, ...payload }) {
    const response = await apiClient.post(`/expenses/${id}/mark-as-recurring`, payload);
    return response.data;
}

export async function getExpenseMergeGroups() {
    const response = await apiClient.get("/expenses/merge-groups");
    return response.data;
}

export async function createExpenseMergeGroup(payload) {
    const response = await apiClient.post("/expenses/merge-groups", payload);
    return response.data;
}

export async function addExpensesToMergeGroup(groupId, payload) {
    const response = await apiClient.post(`/expenses/merge-groups/${groupId}/items`, payload);
    return response.data;
}

export async function removeExpenseFromMergeGroup(groupId, expenseId) {
    const response = await apiClient.delete(`/expenses/merge-groups/${groupId}/items/${expenseId}`);
    return response.data;
}
