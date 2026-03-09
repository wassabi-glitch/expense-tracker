import { useQuery } from "@tanstack/react-query";
import { getCategories } from "@/lib/api";

export function useRecurringCategoriesQuery(enabled) {
    return useQuery({
        queryKey: ["meta", "categories"],
        queryFn: getCategories,
        enabled,
    });
}
