import { useQuery } from "@tanstack/react-query";
import { getAssets } from "@/lib/api";

export function useAssetsQuery(params) {
  return useQuery({
    queryKey: ["assets", params],
    queryFn: () => getAssets(params),
    placeholderData: (previous) => previous,
  });
}
