export const GOAL_MUTATION_INVALIDATION_KEYS = [
  ["goals"],
  ["debts"],
  ["payment_plans"],
  ["wallets"],
  ["projects"],
  ["budgets"],
  ["users", "me"],
  ["dashboard"],
  ["analytics"],
  ["notifications"],
];

export async function invalidateGoalQueries(queryClient) {
  await Promise.all(
    GOAL_MUTATION_INVALIDATION_KEYS.map((queryKey) =>
      queryClient.invalidateQueries({ queryKey })
    )
  );
}
