import { useQuery } from "@tanstack/react-query";
import { getGoalActivity, getGoals } from "@/lib/api";

export function useGoalsQuery(enabled = true) {
  return useQuery({
    queryKey: ["goals", "list"],
    queryFn: getGoals,
    enabled,
  });
}

export function useGoalActivityQuery(goalId, enabled = true) {
  return useQuery({
    queryKey: ["goals", goalId, "activity"],
    queryFn: () => getGoalActivity(goalId),
    enabled: Boolean(enabled && goalId),
  });
}
