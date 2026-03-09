import { apiClient } from "./client";

export async function getBudgets() {
    const response = await apiClient.get("/budgets/");
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
    const response = await apiClient.patch(
        `/budgets/${encodeURIComponent(budget_year)}/${encodeURIComponent(budget_month)}/${encodeURIComponent(category)}`,
        { monthly_limit },
    );
    return response.data;
}

export async function deleteBudget(category, budget_year, budget_month) {
    const response = await apiClient.delete(
        `/budgets/${encodeURIComponent(budget_year)}/${encodeURIComponent(budget_month)}/${encodeURIComponent(category)}`,
    );
    return response.data;
}
