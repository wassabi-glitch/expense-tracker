import { useQuery } from "@tanstack/react-query";
import { getCategories } from "@/lib/api";

export function useExportCategoriesQuery() {
    return useQuery({
        queryKey: ["meta", "categories"],
        queryFn: getCategories,
    });
}
