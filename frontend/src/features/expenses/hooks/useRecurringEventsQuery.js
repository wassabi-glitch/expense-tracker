import { useQuery } from "@tanstack/react-query";
import { getRecurringEvents } from "@/lib/api";

export function useRecurringEventsQuery(recurringId, enabled = false) {
    return useQuery({
        queryKey: ["recurring", recurringId, "events"],
        queryFn: () => getRecurringEvents(recurringId),
        enabled: !!recurringId && enabled,
        staleTime: 1000 * 60, // 1 minute cache
    });
}
