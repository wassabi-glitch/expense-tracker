import { apiClient } from "./client";

function normalizeArrayPayload(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data?.results)) return data.results;
    if (Array.isArray(data?.data)) return data.data;
    return [];
}

export async function getBudgets() {
    const response = await apiClient.get("/budgets/");
    return normalizeArrayPayload(response.data);
}

export async function getBudgetDetail(budget_year, budget_month, category) {
    const response = await apiClient.get("/budgets/item/detail", {
        params: { budget_year, budget_month, category },
    });
    return response.data;
}

export async function getBudgetMonthSummary(budget_year, budget_month) {
    const response = await apiClient.get("/budgets/month-summary", {
        params: { budget_year, budget_month },
    });
    return response.data;
}

export async function getBudgetSubcategories(budgetId) {
    const response = await apiClient.get(`/budgets/${budgetId}/subcategories`);
    return normalizeArrayPayload(response.data);
}

export async function reallocateBudget(payload) {
    const response = await apiClient.post("/budgets/reallocate", payload);
    return normalizeArrayPayload(response.data);
}

export async function createBudgetSubcategory(budgetId, payload) {
    const response = await apiClient.post(`/budgets/${budgetId}/subcategories`, payload);
    return response.data;
}

export async function updateBudgetSubcategory(subcategoryId, payload, budgetId = null) {
    const response = await apiClient.patch(`/budgets/subcategories/${subcategoryId}`, payload, {
        params: budgetId ? { budget_id: budgetId } : undefined,
    });
    return response.data;
}

export async function reallocateBudgetSubcategory(budgetId, payload) {
    const response = await apiClient.post(`/budgets/${budgetId}/subcategories/reallocate`, payload);
    return response.data;
}

export async function deleteBudgetSubcategory(subcategoryId) {
    const response = await apiClient.delete(`/budgets/subcategories/${subcategoryId}`);
    return response.data;
}

export async function createBudget(category, monthly_limit, budget_year, budget_month) {
    const response = await apiClient.post("/budgets/", {
        category,
        monthly_limit,
        budget_year,
        budget_month,
    });
    return response.data;
}

export async function updateBudget(category, monthly_limit, budget_year, budget_month) {
    const params = new URLSearchParams({
        budget_year,
        budget_month,
        category,
    });
    const response = await apiClient.patch(
        `/budgets/item?${params.toString()}`,
        { monthly_limit },
    );
    return response.data;
}

export async function deleteBudget(category, budget_year, budget_month) {
    const params = new URLSearchParams({
        budget_year,
        budget_month,
        category,
    });
    const response = await apiClient.delete(
        `/budgets/item?${params.toString()}`,
    );
    return response.data;
}


export async function configureBorrowingSurvival(data) {
    const response = await apiClient.put(`/budgets/borrowing-survival`, data);
    return response.data;
}

export async function getBudgetTimeline(budget_year, budget_month) {
    const response = await apiClient.get("/budgets/timeline", {
        params: { budget_year, budget_month },
    });
    return response.data;
}

