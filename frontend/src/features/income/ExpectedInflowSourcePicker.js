/**
 * Expected Inflow Source Picker Read Model
 *
 * Provides normalized source options for the Expected Inflow editor.
 *
 * Owns:
 * - Backend payload unwrapping for feed-oriented expense data (ADR-0018)
 * - Debt lifecycle status rules (ADR-0018: use lifecycle_status, not legacy status)
 * - Source-kind filtering (active sources, open receivables, non-refund expenses, owned assets)
 * - Stable user-facing option labels
 *
 * The Expected Inflow editor should consume these normalized options
 * rather than raw backend payloads where practical.
 */

// ---------------------------------------------------------------------------
// Normalizers — each converts one raw backend item into a uniform picker option
// ---------------------------------------------------------------------------

function toEarnedOption(source) {
  return {
    id: source.id,
    label: source.name || `Source #${source.id}`,
    isActive: source.is_active,
    source,
  };
}

function toReceivableOption(debt) {
  return {
    id: debt.id,
    label: debt.counterparty_name || `Debt #${debt.id}`,
    remainingAmount: debt.remaining_amount,
    debt,
  };
}

function toRefundOption(feedItem) {
  // At this point feedItem.type === "EXPENSE" and feedItem.expense is non-null
  // and feedItem.expense.transaction_type !== "REFUND" (guaranteed by caller).
  const expense = feedItem.expense;
  const dateLabel = expense.date || "no date";
  const label = expense.title
    ? `${expense.title} (${dateLabel})`
    : `Expense #${expense.id} (${dateLabel})`;

  return {
    id: expense.id,
    label,
    date: expense.date,
    title: expense.title,
    expense,
  };
}

function toAssetSaleOption(asset) {
  return {
    id: asset.id,
    label: asset.name || `Asset #${asset.id}`,
    status: asset.status,
    asset,
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function asItems(data) {
  return Array.isArray(data) ? data : data?.items || [];
}

// ---------------------------------------------------------------------------
// Public API — one selector per source kind
// ---------------------------------------------------------------------------

/**
 * Earned income choices: active income sources.
 * Preserves current Expected Inflow creation behaviour.
 */
export function getEarnedOptions(sources) {
  return asItems(sources)
    .filter((s) => s.is_active)
    .map(toEarnedOption);
}

/**
 * Receivable choices: open Debts owed to the user with remaining amount > 0.
 *
 * Uses lifecycle_status === "OPEN" (per ADR-0018) instead of the legacy
 * status === "ACTIVE" string match.  Closed, settled, forgiven, and
 * written-off Debts are excluded.
 */
export function getReceivableOptions(debts) {
  return asItems(debts)
    .filter((d) => d.debt_type === "OWED")
    .filter((d) => d.lifecycle_status === "OPEN")
    .filter((d) => Number(d.remaining_amount || 0) > 0)
    .map(toReceivableOption);
}

/**
 * Refund choices: expenses eligible to be linked as a refund source.
 *
 * Unwraps the polymorphic ExpenseFeedItemOut wrapper (ADR-0018):
 *   - Keeps only items where type === "EXPENSE" (excludes merge groups)
 *   - Unwraps the inner expense via feedItem.expense
 *   - Excludes refund-type expenses (no refund-to-refund linking)
 *
 * Labels use the original expense title and date where available.
 */
export function getRefundOptions(expenses) {
  return asItems(expenses)
    .filter((item) => item.type === "EXPENSE")
    .filter((item) => item.expense != null)
    .filter((item) => item.expense.transaction_type !== "REFUND")
    .map(toRefundOption);
}

/**
 * Asset Sale choices: owned assets.
 * Preserves current Asset Sale behaviour.
 */
export function getAssetSaleOptions(assets) {
  return asItems(assets)
    .filter((a) => a.status === "owned")
    .map(toAssetSaleOption);
}

/**
 * Convenience: return all four option lists keyed by source kind.
 *
 * @param {{ sources, debts, expenses, assets }} raw — raw backend payloads
 * @returns {{ EARNED, RECEIVABLE, REFUND, ASSET_SALE }}
 */
export function getSourceOptions({ sources, debts, expenses, assets }) {
  return {
    EARNED: getEarnedOptions(sources),
    RECEIVABLE: getReceivableOptions(debts),
    REFUND: getRefundOptions(expenses),
    ASSET_SALE: getAssetSaleOptions(assets),
  };
}
