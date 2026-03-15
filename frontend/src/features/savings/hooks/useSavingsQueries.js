import { useQuery } from "@tanstack/react-query";
import { getSavingsSummary } from "@/lib/api";

export function useSavingsSummaryQuery(enabled = true) {
  return useQuery({
    queryKey: ["savings", "summary"],
    queryFn: getSavingsSummary,
    enabled,
  });
}
