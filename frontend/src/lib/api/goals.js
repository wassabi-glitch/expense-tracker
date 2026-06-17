import { apiClient } from "./client";

export async function getGoals() {
  const response = await apiClient.get("/goals/");
  return response.data;
}

export async function getGoalFundingSummary() {
  const response = await apiClient.get("/goals/funding-summary");
  return response.data;
}

export async function getGoalActivity(goalId) {
  const response = await apiClient.get(`/goals/${goalId}/activity`);
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
  const response = await apiClient.post(`/goals/${goalId}/allocations`, payload);
  return response.data;
}

export async function returnFromGoal(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/allocations/return`, payload);
  return response.data;
}

export async function consumeGoalAllocation(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/allocations/consume`, payload);
  return response.data;
}

export async function moveGoalFunding(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/allocations/move`, payload);
  return response.data;
}

export async function useReserveGoal(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/use-reserve`, payload);
  return response.data;
}

export async function recordGoalPurchase(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/record-purchase`, payload);
  return response.data;
}

export async function recordGoalDebtPayment(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/pay-debt`, payload);
  return response.data;
}

export async function graduateGoalToProject(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/graduate`, payload);
  return response.data;
}

export async function releaseGoalToProject(goalId, payload) {
  const response = await apiClient.post(`/goals/${goalId}/release-to-project`, payload);
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
