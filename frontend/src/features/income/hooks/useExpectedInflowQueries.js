import { useQuery } from "@tanstack/react-query";

import { getCashflow, getExpectedInflow, getExpectedInflows } from "@/lib/api";


export const expectedInflowKeys = {
  all: ["expected-inflows"],
  list: (params) => ["expected-inflows", "list", params],
  detail: (id) => ["expected-inflows", "detail", Number(id)],
  cashflow: (params) => ["expected-inflows", "cashflow", params],
};


export function useExpectedInflowsQuery(params) {
  return useQuery({
    queryKey: expectedInflowKeys.list(params),
    queryFn: () => getExpectedInflows(params),
  });
}


export function useExpectedInflowQuery(id, enabled = true) {
  return useQuery({
    queryKey: expectedInflowKeys.detail(id),
    queryFn: () => getExpectedInflow(id),
    enabled: enabled && Boolean(id),
  });
}


export function useCashflowQuery(params, enabled = true) {
  return useQuery({
    queryKey: expectedInflowKeys.cashflow(params),
    queryFn: () => getCashflow(params),
    enabled,
  });
}
