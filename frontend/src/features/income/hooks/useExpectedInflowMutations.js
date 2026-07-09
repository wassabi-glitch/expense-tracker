import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  cancelExpectedInflow,
  createExpectedInflow,
  deleteExpectedInflow,
  realizeExpectedInflow,
  reopenExpectedInflow,
  rescheduleExpectedInflow,
  reverseExpectedInflowWriteOff,
  updateExpectedInflow,
  writeOffExpectedInflow,
} from "@/lib/api";
import { expectedInflowKeys } from "./useExpectedInflowQueries";
import { invalidateExpectedInflowViews } from "@/lib/cacheInvalidation";


async function invalidateExpectedInflowQueries(queryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: expectedInflowKeys.all }),
    invalidateExpectedInflowViews(queryClient),
  ]);
}


function useExpectedMutation(mutationFn) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => invalidateExpectedInflowQueries(queryClient),
  });
}


export function useSaveExpectedInflowMutation() {
  return useExpectedMutation(({ id, payload }) => (
    id ? updateExpectedInflow(id, payload) : createExpectedInflow(payload)
  ));
}

export function useRealizeExpectedInflowMutation() {
  return useExpectedMutation(({ id, payload }) => realizeExpectedInflow(id, payload));
}

export function useRescheduleExpectedInflowMutation() {
  return useExpectedMutation(({ id, payload }) => rescheduleExpectedInflow(id, payload));
}

export function useWriteOffExpectedInflowMutation() {
  return useExpectedMutation(({ id, payload }) => writeOffExpectedInflow(id, payload));
}

export function useCancelExpectedInflowMutation() {
  return useExpectedMutation((id) => cancelExpectedInflow(id));
}

export function useReopenExpectedInflowMutation() {
  return useExpectedMutation((id) => reopenExpectedInflow(id));
}

export function useDeleteExpectedInflowMutation() {
  return useExpectedMutation((id) => deleteExpectedInflow(id));
}

export function useReverseExpectedInflowWriteOffMutation() {
  return useExpectedMutation(({ id, writeOffId, payload }) => (
    reverseExpectedInflowWriteOff(id, writeOffId, payload)
  ));
}
