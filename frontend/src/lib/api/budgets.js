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
