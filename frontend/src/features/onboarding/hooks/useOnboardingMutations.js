import { useMutation, useQueryClient } from "@tanstack/react-query";
import { upsertOnboardingProfile } from "@/lib/api";

export function useOnboardingUpsertMutation() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ life_statuses, wallets }) =>
            upsertOnboardingProfile({ life_statuses, wallets }),
        onSuccess: (updatedUser) => {
            queryClient.setQueryData(["users", "me"], updatedUser);
        },
    });
}
