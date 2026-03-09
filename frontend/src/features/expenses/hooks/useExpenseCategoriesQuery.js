import { useQuery } from "@tanstack/react-query";
import { getCategories } from "@/lib/api";

export function useExpenseCategoriesQuery(enabled = true) {
    return useQuery({
        queryKey: ["meta", "categories"],
        queryFn: getCategories,
        enabled,
    });
}
