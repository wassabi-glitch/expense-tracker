import { useQuery } from "@tanstack/react-query";
import { getBudgetExpectedIncomes, getBudgets, getBudgetMonthSummary, getThisMonthStats } from "@/lib/api";

export function useBudgetsDataQuery({ budgetYear, budgetMonth } = {}) {
    const budgetsQuery = useQuery({
        queryKey: ["budgets", "list"],
        queryFn: getBudgets,
    });

    const monthSummaryQuery = useQuery({
        queryKey: ["budgets", "month-summary", budgetYear, budgetMonth],
        queryFn: () => getBudgetMonthSummary(budgetYear, budgetMonth),
        enabled: Boolean(budgetYear && budgetMonth),
    });

    const expectedIncomesQuery = useQuery({
        queryKey: ["budgets", "expected-incomes", budgetYear, budgetMonth],
        queryFn: () => getBudgetExpectedIncomes(budgetYear, budgetMonth),
        enabled: Boolean(budgetYear && budgetMonth),
    });

    const statsQuery = useQuery({
        queryKey: ["budgets", "month-stats"],
        queryFn: getThisMonthStats,
    });

    return { budgetsQuery, monthSummaryQuery, expectedIncomesQuery, statsQuery };
}
