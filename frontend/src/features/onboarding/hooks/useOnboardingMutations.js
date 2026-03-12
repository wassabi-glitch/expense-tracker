import { useMutation, useQueryClient } from "@tanstack/react-query";
import { upsertOnboardingProfile } from "@/lib/api";

export function useOnboardingUpsertMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ life_status, initial_balance }) =>
            upsertOnboardingProfile({ life_status, initial_balance }),
        onSuccess: (updatedUser) => {
            queryClient.setQueryData(["users", "me"], updatedUser);
        },
    });
}
