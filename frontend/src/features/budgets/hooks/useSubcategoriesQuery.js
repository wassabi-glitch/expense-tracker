import { useQuery } from "@tanstack/react-query";
import { getSubcategories } from "../../../lib/api/subcategories";

export function useSubcategoriesQuery(category) {
  return useQuery({
    queryKey: ["subcategories", category],
    queryFn: () => getSubcategories(category),
    enabled: !!category,
    staleTime: 5 * 60 * 1000,
  });
}
