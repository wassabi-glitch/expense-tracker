/**
 * Budget Interceptor — shared detection and helpers (ADR-0009).
 *
 * The backend sends a structured detail code when a Budget Permission row
 * is missing for a category + month:
 *   HTTP 400  detail="expenses.budget_required"
 *
 * Detection MUST use this code, never a fragile localized message.
 */

/**
 * Return true when `error` represents a missing Budget Permission.
 * Accepts an Error-like object, a plain string, or null/undefined.
 */
export function isBudgetRequiredError(error) {
  const raw = String(error?.message ?? error ?? "");
  return (
    raw === "expenses.budget_required" ||
    raw.includes("expenses.budget_required")
  );
}

/**
 * Extract (year, month) from a YYYY-MM-DD date string.
 * Falls back to today's local year/month when the string is unparseable.
 */
export function extractBudgetMonth(dateString) {
  const [y, m] = String(dateString || "").split("-").map(Number);
  const now = new Date();
  return {
    budgetYear: Number.isFinite(y) ? y : now.getFullYear(),
    budgetMonth: Number.isFinite(m) ? m : now.getMonth() + 1,
  };
}
