import { useQuery } from "@tanstack/react-query";
import { getBudgetTimeline } from "@/lib/api/budgets";

export function useBudgetTimelineQuery(budgetYear, budgetMonth) {
    return useQuery({
        queryKey: ["budgets", "timeline", budgetYear, budgetMonth],
        queryFn: () => getBudgetTimeline(budgetYear, budgetMonth),
        enabled: Boolean(budgetYear && budgetMonth),
    });
}
