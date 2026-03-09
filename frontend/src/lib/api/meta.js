import { apiClient } from "./client";

export async function getCategories() {
    const response = await apiClient.get("/meta/categories");
    return response.data;
}
