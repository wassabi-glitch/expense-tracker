import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { getDebtActions, getDebtDetails, getDebts, getDebtsSummary } from "@/lib/api";

export function useDebtsQuery(params = {}) {
  return useQuery({
    queryKey: ["debts", params],
    queryFn: () => getDebts(params),
    placeholderData: keepPreviousData,
  });
}

export function useDebtsSummaryQuery() {
  return useQuery({
    queryKey: ["debts", "summary"],
    queryFn: () => getDebtsSummary(),
  });
}

export function useDebtDetailsQuery(debtId, options = {}) {
  return useQuery({
    queryKey: ["debts", "details", debtId],
    queryFn: () => getDebtDetails(debtId),
    enabled: !!debtId,
    ...options,
  });
}

export function useDebtActionsQuery(debtId, options = {}) {
  return useQuery({
    queryKey: ["debts", "actions", debtId],
    queryFn: () => getDebtActions(debtId),
    enabled: !!debtId,
    ...options,
  });
}
