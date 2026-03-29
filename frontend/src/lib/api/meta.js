import { apiClient } from "./client";

export async function getCategories() {
    const response = await apiClient.get("/meta/categories");
    const data = response.data;

    // Defensive normalization for occasional non-array payloads.
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.categories)) return data.categories;
    if (Array.isArray(data?.value)) return data.value;
    return [];
}
