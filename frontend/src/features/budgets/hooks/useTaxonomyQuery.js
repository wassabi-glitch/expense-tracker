import { useQuery } from "@tanstack/react-query";
import { getTaxonomy } from "../../../lib/api/subcategories";

export function useTaxonomyQuery() {
  return useQuery({
    queryKey: ["subcategories", "taxonomy"],
    queryFn: getTaxonomy,
    staleTime: 5 * 60 * 1000,
  });
}
