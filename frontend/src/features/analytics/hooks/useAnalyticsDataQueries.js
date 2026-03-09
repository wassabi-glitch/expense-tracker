import { useQuery } from "@tanstack/react-query";
import { getAnalyticsHistory, getCategoryBreakdown, getDailyTrend } from "@/lib/api";

const EMPTY_ARRAY = [];

export function useAnalyticsSummaryQuery() {
    return useQuery({
        queryKey: ["analytics", "history"],
        queryFn: getAnalyticsHistory,
    });
}

export function useAnalyticsChartsQuery(chartParams) {
    return useQuery({
        queryKey: ["analytics", "charts", chartParams],
        queryFn: async () => {
            const [trendRes, categoryRes] = await Promise.all([
                getDailyTrend(chartParams),
                getCategoryBreakdown(chartParams),
            ]);

            return {
                trendData: trendRes || EMPTY_ARRAY,
                categoryBreakdown: categoryRes || EMPTY_ARRAY,
            };
        },
    });
}
