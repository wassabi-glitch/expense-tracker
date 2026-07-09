import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createBudget } from "@/lib/api";
import { isBudgetRequiredError } from "@/lib/budgetInterceptor";
import { invalidateBudgetViews } from "@/lib/cacheInvalidation";

/**
 * Shared Budget Interceptor hook (ADR-0009).
 *
 * Encapsulates the state and actions for the "budget required → create budget
 * → replay" repair flow.  Callers wire this into their mutation error handling
 * and render a BudgetRepairDialog to collect the monthly limit.
 *
 * Usage sketch:
 *
 *   const repair = useBudgetRepair();
 *
 *   // In your mutation's onError / catch:
 *   if (repair.isRequired(e)) {
 *     repair.open({
 *       category: "food",
 *       date: "2026-07-09",
 *       suggestedAmount: 45000,
 *       onReplay: async () => { await retryMyAction(); },
 *     });
 *   }
 *
 *   // In your JSX:
 *   <BudgetRepairDialog
 *     open={repair.isOpen}
 *     repairPrompt={repair.prompt}
 *     repairAmount={repairAmount}
 *     onAmountChange={setRepairAmount}
 *     repairPending={repair.pending}
 *     repairError={repair.error}
 *     onClose={repair.close}
 *     onCreateBudget={() => repair.createBudget(repairAmountValue)}
 *   />
 */

export function useBudgetRepair() {
  const queryClient = useQueryClient();

  const [prompt, setPrompt] = React.useState(null); // { category, budgetYear, budgetMonth, suggestedAmount }
  const [error, setError] = React.useState("");
  const [pending, setPending] = React.useState(false);
  const replayRef = React.useRef(null); // async function to replay after repair

  const isOpen = prompt !== null;

  /** Detect a budget_required error. */
  const isRequired = React.useCallback(
    (e) => isBudgetRequiredError(e),
    [],
  );

  /**
   * Open the repair flow.
   * `opts.onReplay` will be called after the budget is successfully created.
   */
  const open = React.useCallback((opts) => {
    setPrompt({
      category: opts.category,
      budgetYear: opts.budgetYear,
      budgetMonth: opts.budgetMonth,
      suggestedAmount: opts.suggestedAmount ?? 0,
      expenseDate: opts.date,
    });
    setError("");
    setPending(false);
    replayRef.current = opts.onReplay ?? null;
  }, []);

  /** Close the repair flow without creating a budget. */
  const close = React.useCallback(() => {
    setPrompt(null);
    setError("");
    setPending(false);
    replayRef.current = null;
  }, []);

  /**
   * Create the budget with the given monthly limit, then replay.
   * `limit` should be a positive integer (UZS).
   */
  const createBudgetAndReplay = React.useCallback(async (limit) => {
    if (!prompt) return;
    const finalLimit =
      Number.isFinite(limit) && limit > 0
        ? limit
        : Math.max(prompt.suggestedAmount, 1000);

    setPending(true);
    setError("");

    // 1. Create the missing budget
    try {
      await createBudget(
        prompt.category,
        finalLimit,
        prompt.budgetYear,
        prompt.budgetMonth,
      );
      await invalidateBudgetViews(queryClient);
    } catch (e) {
      const msg =
        e?.response?.data?.detail ||
        e?.message ||
        String(e);
      setError(msg);
      setPending(false);
      return;
    }

    // 2. Replay the original action
    if (replayRef.current) {
      try {
        await replayRef.current();
        close();
      } catch (_replayError) {
        // Budget was created but replay failed — close and let caller handle
        setError(
          "Budget was created but the action could not be replayed. Please try again.",
        );
        setPending(false);
        // Keep dialog open so the user sees the message
      }
    } else {
      close();
    }
  }, [prompt, queryClient, close]);

  return {
    /** Whether the repair dialog should be visible. */
    isOpen,
    /** The current repair prompt data (null when closed). */
    prompt,
    /** Whether a repair operation is in flight. */
    pending,
    /** The current repair error message (empty when no error). */
    error,
    /** Test whether an error is a budget_required error. */
    isRequired,
    /** Open the repair flow. */
    open,
    /** Close the repair flow (cancel). */
    close,
    /** Create the budget and replay the saved action. */
    createBudgetAndReplay,
  };
}
