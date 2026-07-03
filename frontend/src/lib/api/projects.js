import { apiClient } from "./client";

function normalizeArrayPayload(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data?.results)) return data.results;
    if (Array.isArray(data?.data)) return data.data;
    return [];
}

function compactParams(params = {}) {
    return Object.fromEntries(
        Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""),
    );
}

export async function getProjects(params = {}) {
    const response = await apiClient.get("/projects", {
        params: compactParams({
            budget_year: params.budgetYear,
            budget_month: params.budgetMonth,
        }),
    });
    return normalizeArrayPayload(response.data);
}

export async function createProject(payload) {
    const response = await apiClient.post("/projects", payload);
    return response.data;
}

export async function createOverlayProject(payload) {
    const response = await apiClient.post("/projects/overlay", payload);
    return response.data;
}

export async function updateProject(projectId, payload) {
    const response = await apiClient.put(`/projects/${projectId}`, payload);
    return response.data;
}

export async function stopProject(projectId) {
    const response = await apiClient.post(`/projects/${projectId}/stop`);
    return response.data;
}

export async function resumeProject(projectId) {
    const response = await apiClient.post(`/projects/${projectId}/resume`);
    return response.data;
}

export async function completeProject(projectId, payload = {}) {
    const response = await apiClient.post(`/projects/${projectId}/complete`, payload);
    return response.data;
}

export async function reopenProject(projectId) {
    const response = await apiClient.post(`/projects/${projectId}/reopen`);
    return response.data;
}

export async function getProjectDeletePreview(projectId) {
    const response = await apiClient.get(`/projects/${projectId}/delete-preview`);
    return response.data;
}

export async function deleteProject(projectId) {
    const response = await apiClient.delete(`/projects/${projectId}`);
    return response.data;
}

export async function resolveProjectDeletion(projectId, payload) {
    const response = await apiClient.post(`/projects/${projectId}/delete-resolution`, payload);
    return response.data;
}

export async function createProjectCategoryLimit(projectId, payload) {
    const response = await apiClient.post(`/projects/${projectId}/category-limits`, payload);
    return response.data;
}

export async function updateProjectCategoryLimit(projectId, category, payload) {
    const response = await apiClient.put(`/projects/${projectId}/category-limits/${encodeURIComponent(category)}`, payload);
    return response.data;
}

export async function deleteProjectCategoryLimit(projectId, category, params = {}) {
    const response = await apiClient.delete(`/projects/${projectId}/category-limits/${encodeURIComponent(category)}`, {
        params: compactParams({
            budget_year: params.budgetYear,
            budget_month: params.budgetMonth,
        }),
    });
    return response.data;
}

export async function getProjectSubcategories(projectId, category) {
    const response = await apiClient.get(`/projects/${projectId}/subcategories`, {
        params: compactParams({ category }),
    });
    return normalizeArrayPayload(response.data);
}

export async function createProjectSubcategory(projectId, payload) {
    const response = await apiClient.post(`/projects/${projectId}/subcategories`, payload);
    return response.data;
}

export async function updateProjectSubcategory(projectId, subcategoryId, payload) {
    const response = await apiClient.put(`/projects/${projectId}/subcategories/${subcategoryId}`, payload);
    return response.data;
}

export async function deleteProjectSubcategory(projectId, subcategoryId) {
    const response = await apiClient.delete(`/projects/${projectId}/subcategories/${subcategoryId}`);
    return response.data;
}
