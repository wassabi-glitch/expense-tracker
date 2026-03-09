import { useQuery } from "@tanstack/react-query";
import { getCurrentUser } from "@/lib/api";

export function useSettingsDataQuery() {
    return useQuery({
        queryKey: ["users", "me"],
        queryFn: getCurrentUser,
    });
}
