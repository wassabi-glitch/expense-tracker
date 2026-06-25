import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createSubcategory, updateSubcategory, deleteSubcategory, mergeSubcategories } from "../../../lib/api/subcategories";

export function useTaxonomyMutations() {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: createSubcategory,
    onSuccess: () => {
      queryClient.invalidateQueries(["subcategories"]);
    },
  });

  const updateMutation = useMutation({
    mutationFn: updateSubcategory,
    onSuccess: () => {
      // Invalidate both the taxonomy hub and the active dropdown lists
      queryClient.invalidateQueries(["subcategories"]);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSubcategory,
    onSuccess: () => {
      queryClient.invalidateQueries(["subcategories"]);
    },
  });

  const mergeMutation = useMutation({
    mutationFn: mergeSubcategories,
    onSuccess: () => {
      queryClient.invalidateQueries(["subcategories"]);
    },
  });

  return {
    createMutation,
    updateMutation,
    deleteMutation,
    mergeMutation,
  };
}
