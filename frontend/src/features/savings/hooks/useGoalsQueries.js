import { useQuery } from "@tanstack/react-query";
import { getGoals } from "@/lib/api";

export function useGoalsQuery(enabled = true) {
  return useQuery({
    queryKey: ["goals", "list"],
    queryFn: getGoals,
    enabled,
  });
}
