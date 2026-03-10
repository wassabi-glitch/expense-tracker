import { useMutation, useQueryClient } from "@tanstack/react-query";
import { upsertOnboardingProfile } from "@/lib/api";

export function useOnboardingUpsertMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ life_status, monthly_income_amount }) =>
            upsertOnboardingProfile({ life_status, monthly_income_amount }),
        onSuccess: (updatedUser) => {
            queryClient.setQueryData(["users", "me"], updatedUser);
        },
    });
}
