import { useQuery } from "@tanstack/react-query";
import {
    getCurrentUser,
    getExpenses,
    getMonthToDateTrend,
    getRecurringExpenses,
    getThisMonthStats,
} from "@/lib/api";

export function useDashboardDataQuery({ monthStartIso, todayIso }) {
    const userQuery = useQuery({
        queryKey: ["users", "me"],
        queryFn: getCurrentUser,
    });

    const statsQuery = useQuery({
        queryKey: ["dashboard", "stats", monthStartIso, todayIso],
        queryFn: getThisMonthStats,
    });

    const recentExpensesQuery = useQuery({
        queryKey: ["dashboard", "recent-expenses", monthStartIso, todayIso],
        queryFn: () =>
            getExpenses({
                limit: 5,
                skip: 0,
                sort: "newest",
                start_date: monthStartIso,
                end_date: todayIso,
            }),
    });

    const recurringExpensesQuery = useQuery({
        queryKey: ["dashboard", "recurring"],
        queryFn: getRecurringExpenses,
        enabled: !!userQuery.data?.is_premium,
    });

    const trendQuery = useQuery({
        queryKey: ["dashboard", "month-to-date-trend", monthStartIso, todayIso],
        queryFn: getMonthToDateTrend,
    });

    return {
        userQuery,
        statsQuery,
        recentExpensesQuery,
        recurringExpensesQuery,
        trendQuery,
    };
}
