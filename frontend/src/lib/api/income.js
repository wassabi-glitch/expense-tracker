import { apiClient } from "./client";

function compactParams(params = {}) {
    return Object.fromEntries(
        Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""),
    );
}

export async function getIncomeSources(params = {}) {
    const response = await apiClient.get("/income/sources", { params: compactParams(params) });
    return response.data;
}

export async function createIncomeSource(payload) {
    const response = await apiClient.post("/income/sources", payload);
    return response.data;
}

export async function updateIncomeSource(sourceId, payload) {
    const response = await apiClient.patch(`/income/sources/${sourceId}`, payload);
    return response.data;
}

export async function deleteIncomeSource(sourceId) {
    const response = await apiClient.delete(`/income/sources/${sourceId}`);
    return response.data;
}

export async function updateIncomeSourceActive(sourceId, isActive) {
    const response = await apiClient.patch(`/income/sources/${sourceId}/active`, {
        is_active: isActive,
    });
    return response.data;
}

export async function getIncomeEntries(params = {}) {
    const response = await apiClient.get("/income/entries", { params: compactParams(params) });
    return response.data;
}

export async function createIncomeEntry(payload) {
    const response = await apiClient.post("/income/entries", payload);
    return response.data;
}

export async function updateIncomeEntry(entryId, payload) {
    const response = await apiClient.put(`/income/entries/${entryId}`, payload);
    return response.data;
}

export async function deleteIncomeEntry(entryId) {
    const response = await apiClient.delete(`/income/entries/${entryId}`);
    return response.data;
}
