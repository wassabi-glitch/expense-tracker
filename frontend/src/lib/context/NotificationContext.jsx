import { createContext, useContext } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    getNotifications,
    markNotificationsRead,
    markAllNotificationsRead,
    deleteNotification,
} from "@/lib/api/notifications";

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
    const queryClient = useQueryClient();

    const notificationsQuery = useQuery({
        queryKey: ["notifications"],
        queryFn: () => getNotifications({ limit: 50 }),
        staleTime: 30000,
        enabled: true,
    });

    const markReadMutation = useMutation({
        mutationFn: (ids) => markNotificationsRead(ids),
        onMutate: async (ids) => {
            await queryClient.cancelQueries({ queryKey: ["notifications"] });
            const previous = queryClient.getQueryData(["notifications"]);
            queryClient.setQueryData(["notifications"], (old) => {
                if (!old) return old;
                return {
                    ...old,
                    items: old.items.map((n) =>
                        ids.includes(n.id) ? { ...n, is_read: true } : n
                    ),
                    unread_count: Math.max(0, old.unread_count - ids.length),
                };
            });
            return { previous };
        },
        onError: (_err, _vars, context) => {
            if (context?.previous) {
                queryClient.setQueryData(["notifications"], context.previous);
            }
        },
    });

    const markAllReadMutation = useMutation({
        mutationFn: () => markAllNotificationsRead(),
        onMutate: async () => {
            await queryClient.cancelQueries({ queryKey: ["notifications"] });
            const previous = queryClient.getQueryData(["notifications"]);
            queryClient.setQueryData(["notifications"], (old) => {
                if (!old) return old;
                return {
                    ...old,
                    items: old.items.map((n) => ({ ...n, is_read: true })),
                    unread_count: 0,
                };
            });
            return { previous };
        },
        onError: (_err, _vars, context) => {
            if (context?.previous) {
                queryClient.setQueryData(["notifications"], context.previous);
            }
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (id) => deleteNotification(id),
        onMutate: async (id) => {
            await queryClient.cancelQueries({ queryKey: ["notifications"] });
            const previous = queryClient.getQueryData(["notifications"]);
            queryClient.setQueryData(["notifications"], (old) => {
                if (!old) return old;
                const deleted = old.items.find((n) => n.id === id);
                return {
                    ...old,
                    items: old.items.filter((n) => n.id !== id),
                    total: old.total - 1,
                    unread_count: deleted && !deleted.is_read
                        ? Math.max(0, old.unread_count - 1)
                        : old.unread_count,
                };
            });
            return { previous };
        },
        onError: (_err, _vars, context) => {
            if (context?.previous) {
                queryClient.setQueryData(["notifications"], context.previous);
            }
        },
    });

    const notifications = notificationsQuery.data?.items || [];
    const unreadCount = notificationsQuery.data?.unread_count || 0;
    const isLoading = notificationsQuery.isLoading;

    const markAsRead = (ids) => markReadMutation.mutate(ids);
    const markAllAsRead = () => markAllReadMutation.mutate();
    const removeNotification = (id) => deleteMutation.mutate(id);
    const invalidateNotifications = () => queryClient.invalidateQueries({ queryKey: ["notifications"] });

    const getNotificationIcon = (type) => {
        switch (type) {
            case "budget_warning":
                return "⚠️";
            case "budget_exceeded":
                return "🚨";
            case "recurring_due":
                return "📅";
            case "goal_milestone":
                return "🎯";
            case "goal_completed":
                return "🎉";
            default:
                return "🔔";
        }
    };

    const getNotificationPriorityClass = (priority) => {
        switch (priority) {
            case "critical":
                return "bg-destructive/10 border-destructive/30 text-destructive";
            case "high":
                return "bg-orange-500/10 border-orange-500/30 text-orange-600 dark:text-orange-400";
            case "medium":
                return "bg-yellow-500/10 border-yellow-500/30 text-yellow-600 dark:text-yellow-400";
            case "low":
                return "bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400";
            default:
                return "bg-muted border-border";
        }
    };

    const value = {
        notifications,
        unreadCount,
        isLoading,
        markAsRead,
        markAllAsRead,
        removeNotification,
        getNotificationIcon,
        getNotificationPriorityClass,
        invalidateNotifications,
    };

    return (
        <NotificationContext.Provider value={value}>
            {children}
        </NotificationContext.Provider>
    );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useNotifications() {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error("useNotifications must be used within a NotificationProvider");
    }
    return context;
}
