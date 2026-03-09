import { useMutation } from "@tanstack/react-query";
import { exportExpensesCsv } from "@/lib/api";

export function useExportMutation() {
    return useMutation({
        mutationFn: exportExpensesCsv,
    });
}
