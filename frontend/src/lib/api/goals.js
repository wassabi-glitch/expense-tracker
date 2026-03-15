import { apiClient } from "./client";

export async function getGoals() {
  const response = await apiClient.get("/goals/");
  return response.data;
}

export async function createGoal(payload) {
  const response = await apiClient.post("/goals/", payload);
  return response.data;
}

export async function updateGoal(goalId, payload) {
  const response = await apiClient.patch(`/goals/${goalId}`, payload);
  return response.data;
}

export async function contributeToGoal(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/contribute`, payload);
  return response.data;
}

export async function returnFromGoal(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/return`, payload);
  return response.data;
}

export async function archiveGoal(goalId) {
  const response = await apiClient.post(`/goals/${goalId}/archive`);
  return response.data;
}

export async function restoreGoal(goalId) {
  const response = await apiClient.post(`/goals/${goalId}/restore`);
  return response.data;
}

export async function deleteGoal(goalId) {
  const response = await apiClient.delete(`/goals/${goalId}`);
  return response.data;
}
