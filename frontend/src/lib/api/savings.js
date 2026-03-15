import { apiClient } from "./client";

export async function getSavingsSummary() {
  const response = await apiClient.get("/savings/summary");
  return response.data;
}

export async function depositToSavings(payload) {
  const response = await apiClient.post("/savings/deposit", payload);
  return response.data;
}

export async function withdrawFromSavings(payload) {
  const response = await apiClient.post("/savings/withdraw", payload);
  return response.data;
}
