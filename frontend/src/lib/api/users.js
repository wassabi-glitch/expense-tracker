import { apiClient } from "./client";

export async function getCurrentUser() {
    const response = await apiClient.get("/users/me");
    return response.data;
}

export async function togglePremium() {
    const response = await apiClient.post("/users/me/toggle-premium");
    return response.data;
}

export async function upsertOnboardingProfile({ life_statuses, wallets }) {
    const response = await apiClient.post("/users/me/onboarding", {
        life_statuses,
        wallets,
    });
    return response.data;
}

export async function updateBudgetRolloverPreference(budget_rollover_enabled) {
    const response = await apiClient.patch("/users/me/preferences/budget-rollover", {
        budget_rollover_enabled,
    });
    return response.data;
}
