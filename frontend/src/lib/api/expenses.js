import { apiClient } from "./client";

function compactParams(params = {}) {
    return Object.fromEntries(
        Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""),
    );
}

function getFilenameFromDisposition(contentDisposition) {
    const fileNameMatch = /filename="?([^";]+)"?/i.exec(contentDisposition || "");
    return fileNameMatch?.[1] || "expenses.csv";
}

export async function getExpenses(params = {}) {
    const response = await apiClient.get("/expenses", { params: compactParams(params) });
    return response.data;
}

export async function deleteExpense(id) {
    const response = await apiClient.delete(`/expenses/${id}`);
    return response.data;
}

export async function createExpense(payload) {
    const response = await apiClient.post("/expenses/", payload);
    return response.data;
}

export async function updateExpense(id, payload) {
    const response = await apiClient.put(`/expenses/${id}`, payload);
    return response.data;
}

export async function exportExpensesCsv(params = {}) {
    const response = await apiClient.get("/expenses/export", {
        params: compactParams(params),
        responseType: "blob",
    });

    return {
        blob: response.data,
        filename: getFilenameFromDisposition(response.headers?.["content-disposition"]),
    };
}
