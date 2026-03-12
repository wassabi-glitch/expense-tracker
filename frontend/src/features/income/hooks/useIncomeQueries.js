import { useQuery } from "@tanstack/react-query";
import { getDashboardSummary, getIncomeEntries, getIncomeSources } from "@/lib/api";

export function useIncomeSourcesQuery(includeInactive = false) {
    return useQuery({
        queryKey: ["income", "sources", includeInactive],
        queryFn: () => getIncomeSources({ include_inactive: includeInactive }),
    });
}

export function useIncomeEntriesQuery(params, enabled = true) {
    return useQuery({
        queryKey: ["income", "entries", params],
        queryFn: () => getIncomeEntries(params),
        enabled,
        placeholderData: (previousData) => previousData,
    });
}

export function useIncomeMonthSummaryQuery() {
    return useQuery({
        queryKey: ["dashboard", "summary"],
        queryFn: getDashboardSummary,
    });
}

export function useIncomeMonthEntriesCountQuery(params, enabled = true) {
    return useQuery({
        queryKey: ["income", "entries", "month-count", params],
        queryFn: () => getIncomeEntries(params),
        enabled,
        placeholderData: (previousData) => previousData,
    });
}
