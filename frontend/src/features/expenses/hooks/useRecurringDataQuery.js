import { useQuery } from "@tanstack/react-query";
import { getCurrentUser, getRecurringExpenses, getRecurringOccurrences } from "@/lib/api";

export function useRecurringDataQuery() {
    const userQuery = useQuery({
        queryKey: ["users", "me"],
        queryFn: getCurrentUser,
    });

    const isPremium = !!userQuery.data?.is_premium;

    const recurringQuery = useQuery({
        queryKey: ["recurring", "list"],
        queryFn: getRecurringExpenses,
        enabled: isPremium,
    });

    return { userQuery, recurringQuery, isPremium };
}

export function useRecurringOccurrencesQuery(status) {
    const userQuery = useQuery({
        queryKey: ["users", "me"],
        queryFn: getCurrentUser,
    });

    const isPremium = !!userQuery.data?.is_premium;

    return useQuery({
        queryKey: ["recurring", "occurrences", status],
        queryFn: () => getRecurringOccurrences(status),
        enabled: isPremium,
    });
}
