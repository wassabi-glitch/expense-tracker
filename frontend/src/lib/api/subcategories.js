import { apiClient } from "./client";

export async function getSubcategories(category) {
  const url = category ? `/subcategories?category=${category}` : '/subcategories';
  const response = await apiClient.get(url);
  return response.data;
}

export async function getTaxonomy() {
  const response = await apiClient.get('/subcategories/taxonomy');
  return response.data;
}

export async function createSubcategory(payload) {
  const response = await apiClient.post('/subcategories/', payload);
  return response.data;
}

export async function updateSubcategory({ id, payload }) {
  const response = await apiClient.patch(`/subcategories/${id}`, payload);
  return response.data;
}

export async function deleteSubcategory(id) {
  const response = await apiClient.delete(`/subcategories/${id}`);
  return response.data;
}

export async function mergeSubcategories(payload) {
  const response = await apiClient.post("/subcategories/merge", payload);
  return response.data;
}
