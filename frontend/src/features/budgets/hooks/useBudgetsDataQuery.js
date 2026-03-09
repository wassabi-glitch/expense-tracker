import { useQuery } from "@tanstack/react-query";
import { getBudgets, getThisMonthStats } from "@/lib/api";

export function useBudgetsDataQuery() {
    const budgetsQuery = useQuery({
        queryKey: ["budgets", "list"],
        queryFn: getBudgets,
    });

    const statsQuery = useQuery({
        queryKey: ["budgets", "month-stats"],
        queryFn: getThisMonthStats,
    });

    return { budgetsQuery, statsQuery };
}
