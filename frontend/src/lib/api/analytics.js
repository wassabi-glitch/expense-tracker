import { apiClient } from "./client";

function compactParams(params = {}) {
    return Object.fromEntries(
        Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""),
    );
}

export async function getThisMonthStats() {
    const response = await apiClient.get("/analytics/this-month-stats");
    return response.data;
}

export async function getDashboardSummary() {
    const response = await apiClient.get("/analytics/dashboard-summary");
    return response.data;
}

export async function getDailyTrend(params = {}) {
    const response = await apiClient.get("/analytics/daily-trend", { params: compactParams(params) });
    return response.data;
}

export async function getAnalyticsHistory() {
    const response = await apiClient.get("/analytics/history");
    return response.data;
}

export async function getMonthToDateTrend() {
    const response = await apiClient.get("/analytics/month-to-date-trend");
    return response.data;
}

export async function getCategoryBreakdown(params = {}) {
    const response = await apiClient.get("/analytics/category-breakdown", { params: compactParams(params) });
    return response.data;
}
