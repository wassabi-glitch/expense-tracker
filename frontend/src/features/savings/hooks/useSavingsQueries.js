import { useQuery } from "@tanstack/react-query";
import { getGoalFundingSummary } from "@/lib/api";

export function useSavingsSummaryQuery(enabled = true) {
  return useQuery({
    queryKey: ["goals", "funding-summary"],
    queryFn: getGoalFundingSummary,
    enabled,
  });
}
