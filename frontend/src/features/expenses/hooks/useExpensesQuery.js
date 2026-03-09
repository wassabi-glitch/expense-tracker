import { useQuery } from "@tanstack/react-query";
import { getExpenses } from "@/lib/api";

export function useExpensesQuery(queryParams, enabled = true) {
    return useQuery({
        queryKey: ["expenses", queryParams],
        queryFn: () => getExpenses(queryParams),
        enabled,
        placeholderData: (previousData) => previousData,
    });
}
