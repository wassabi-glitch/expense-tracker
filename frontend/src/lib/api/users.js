import { apiClient } from "./client";

export async function getCurrentUser() {
    const response = await apiClient.get("/users/me");
    return response.data;
}

export async function togglePremium() {
    const response = await apiClient.post("/users/me/toggle-premium");
    return response.data;
}
