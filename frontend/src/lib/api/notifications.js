import { apiClient } from "./client";

export async function getNotifications({ is_read, limit = 20, offset = 0 } = {}) {
    const params = new URLSearchParams();
    if (is_read !== undefined) params.append("is_read", is_read);
    params.append("limit", limit);
    params.append("offset", offset);
    const response = await apiClient.get(`/notifications/?${params.toString()}`);
    return response.data;
}

export async function getUnreadCount() {
    const response = await apiClient.get("/notifications/unread-count");
    return response.data;
}

export async function markNotificationsRead(notificationIds) {
    const response = await apiClient.post("/notifications/mark-read", {
        notification_ids: notificationIds,
    });
    return response.data;
}

export async function markAllNotificationsRead() {
    const response = await apiClient.post("/notifications/mark-all-read");
    return response.data;
}

export async function deleteNotification(notificationId) {
    const response = await apiClient.delete(`/notifications/${notificationId}`);
    return response.data;
}

export async function deleteAllNotifications({ is_read = false } = {}) {
    const params = new URLSearchParams();
    params.append("is_read", is_read);
    const response = await apiClient.delete(`/notifications/?${params.toString()}`);
    return response.data;
}
