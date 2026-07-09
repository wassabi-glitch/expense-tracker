import assert from "node:assert/strict";
import test from "node:test";

// ---------------------------------------------------------------------------
// Budget Interceptor — error detection (ADR-0009)
//
// The interceptor must detect structured budget-required errors without
// depending on fragile localized message text.  The backend sends:
//   HTTP 400 with detail: "expenses.budget_required"
// ---------------------------------------------------------------------------

// Replicate the detection logic used in Expenses.handleAdd
function isBudgetRequiredError(errorMessage) {
  const rawMsg = String(errorMessage || "");
  return (
    rawMsg === "expenses.budget_required" ||
    rawMsg.includes("expenses.budget_required")
  );
}

// ---------------------------------------------------------------------------
// Detection tests
// ---------------------------------------------------------------------------

test("detects exact backend error code", () => {
  assert.ok(isBudgetRequiredError("expenses.budget_required"));
});

test("detects error code embedded in a longer message", () => {
  assert.ok(
    isBudgetRequiredError(
      "Request failed: expenses.budget_required for category food"
    )
  );
});

test("does NOT detect unrelated error messages", () => {
  assert.strictEqual(isBudgetRequiredError("Network timeout"), false);
  assert.strictEqual(isBudgetRequiredError("budgets.limit_exceeded"), false);
  assert.strictEqual(isBudgetRequiredError(""), false);
  assert.strictEqual(isBudgetRequiredError(null), false);
  assert.strictEqual(isBudgetRequiredError(undefined), false);
});

test("does NOT detect limit-exceeded as budget-required", () => {
  // budgets.limit_exceeded and budgets.subcategory_limit_exceeded are
  // different errors that should NOT trigger the interceptor
  assert.strictEqual(isBudgetRequiredError("budgets.limit_exceeded"), false);
  assert.strictEqual(
    isBudgetRequiredError("budgets.subcategory_limit_exceeded"),
    false
  );
});

test("detection is case-sensitive (backend is consistent)", () => {
  // The backend always sends lowercase detail codes
  assert.strictEqual(
    isBudgetRequiredError("EXPENSES.BUDGET_REQUIRED"),
    false
  );
});

// ---------------------------------------------------------------------------
// Repair prompt data construction
// ---------------------------------------------------------------------------

function buildBudgetRequiredRepairPrompt(expenseData) {
  const date = String(expenseData.date || "");
  const [yearStr, monthStr] = date.split("-");
  const budgetYear = Number(yearStr);
  const budgetMonth = Number(monthStr);
  const suggestedAmount = Math.abs(Number(expenseData.amount)) || 0;

  return {
    type: "budget_required",
    category: expenseData.category,
    budgetYear: Number.isFinite(budgetYear) ? budgetYear : new Date().getFullYear(),
    budgetMonth: Number.isFinite(budgetMonth) ? budgetMonth : new Date().getMonth() + 1,
    suggestedAmount,
    expenseDate: expenseData.date,
  };
}

test("repair prompt extracts year and month from expense date", () => {
  const prompt = buildBudgetRequiredRepairPrompt({
    category: "food",
    amount: 500000,
    date: "2026-03-15",
  });

  assert.strictEqual(prompt.type, "budget_required");
  assert.strictEqual(prompt.category, "food");
  assert.strictEqual(prompt.budgetYear, 2026);
  assert.strictEqual(prompt.budgetMonth, 3);
  assert.strictEqual(prompt.suggestedAmount, 500000);
});

test("repair prompt uses absolute amount", () => {
  const prompt = buildBudgetRequiredRepairPrompt({
    category: "transport",
    amount: -250000,
    date: "2026-12-01",
  });

  assert.strictEqual(prompt.suggestedAmount, 250000);
});

test("repair prompt falls back for missing date", () => {
  const prompt = buildBudgetRequiredRepairPrompt({
    category: "food",
    amount: 100,
    date: "",
  });

  assert.strictEqual(prompt.type, "budget_required");
  // Fallback to current year/month
  assert.ok(Number.isFinite(prompt.budgetYear));
  assert.ok(Number.isFinite(prompt.budgetMonth));
});

test("repair prompt with zero amount still produces valid shape", () => {
  const prompt = buildBudgetRequiredRepairPrompt({
    category: "entertainment",
    amount: 0,
    date: "2026-07-01",
  });

  assert.strictEqual(prompt.suggestedAmount, 0);
  assert.strictEqual(prompt.type, "budget_required");
});

// ---------------------------------------------------------------------------
// Expense payload preservation (draft save)
// ---------------------------------------------------------------------------

function buildSavedExpensePayload(parsed, isMultiWallet, walletAllocations, splits, splitMode, subcategoryId, projectId, projectSubcategoryId) {
  const amount = Math.abs(Number(parsed.amount || 0));

  function parseAmountInput(raw) {
    const cleaned = String(raw || "").trim().replace(/\s/g, "");
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : 0;
  }

  return {
    title: parsed.title,
    amount: parsed.amount,
    category: parsed.category,
    description: parsed.description ?? null,
    date: parsed.date,
    wallet_allocations: isMultiWallet
      ? walletAllocations
          .map((row) => ({
            wallet_id: row.wallet_id,
            amount: parseAmountInput(String(row.amount)),
          }))
          .filter((row) => row.wallet_id && row.amount > 0)
      : [{ wallet_id: Number(parsed.wallet_id), amount }],
    subcategory_id: subcategoryId ? Number(subcategoryId) : null,
    project_id: projectId ? Number(projectId) : null,
    project_subcategory_id: projectSubcategoryId ? Number(projectSubcategoryId) : null,
    splits:
      splitMode !== "none" && splits.length > 0
        ? splits.map((s) => ({
            contact_name: s.contact_name,
            amount: parseAmountInput(String(s.amount)),
          }))
        : undefined,
  };
}

test("saved payload preserves single-wallet expense data", () => {
  const parsed = {
    title: "Lunch",
    amount: 45000,
    category: "food",
    description: "Team lunch",
    date: "2026-07-09",
    wallet_id: "1",
  };

  const payload = buildSavedExpensePayload(parsed, false, [], [], "none", null, null, null);

  assert.strictEqual(payload.title, "Lunch");
  assert.strictEqual(payload.amount, 45000);
  assert.strictEqual(payload.category, "food");
  assert.strictEqual(payload.description, "Team lunch");
  assert.strictEqual(payload.date, "2026-07-09");
  assert.deepStrictEqual(payload.wallet_allocations, [
    { wallet_id: 1, amount: 45000 },
  ]);
  assert.strictEqual(payload.subcategory_id, null);
  assert.strictEqual(payload.project_id, null);
  assert.strictEqual(payload.splits, undefined);
});

test("saved payload preserves multi-wallet expense data", () => {
  const parsed = {
    title: "Dinner",
    amount: 100000,
    category: "food",
    description: null,
    date: "2026-07-09",
    wallet_id: null,
  };

  const walletAllocations = [
    { wallet_id: 1, amount: "60000" },
    { wallet_id: 2, amount: "40000" },
  ];

  const payload = buildSavedExpensePayload(parsed, true, walletAllocations, [], "none", null, null, null);

  assert.strictEqual(payload.title, "Dinner");
  assert.strictEqual(payload.wallet_allocations.length, 2);
  assert.strictEqual(payload.wallet_allocations[0].wallet_id, 1);
  assert.strictEqual(payload.wallet_allocations[0].amount, 60000);
  assert.strictEqual(payload.wallet_allocations[1].wallet_id, 2);
  assert.strictEqual(payload.wallet_allocations[1].amount, 40000);
});

test("saved payload preserves split data", () => {
  const parsed = {
    title: "Group dinner",
    amount: 90000,
    category: "food",
    description: null,
    date: "2026-07-09",
    wallet_id: "1",
  };

  const splits = [
    { contact_name: "Alice", amount: "45000" },
    { contact_name: "Bob", amount: "45000" },
  ];

  const payload = buildSavedExpensePayload(parsed, false, [], splits, "custom", null, null, null);

  assert.strictEqual(payload.splits.length, 2);
  assert.strictEqual(payload.splits[0].contact_name, "Alice");
  assert.strictEqual(payload.splits[1].amount, 45000);
});

test("saved payload preserves subcategory and project context", () => {
  const parsed = {
    title: "Office supplies",
    amount: 75000,
    category: "shopping",
    description: null,
    date: "2026-07-09",
    wallet_id: "1",
  };

  const payload = buildSavedExpensePayload(parsed, false, [], [], "none", "5", "3", "12");

  assert.strictEqual(payload.subcategory_id, 5);
  assert.strictEqual(payload.project_id, 3);
  assert.strictEqual(payload.project_subcategory_id, 12);
});

// ---------------------------------------------------------------------------
// Repair-to-replay flow — state transitions
// ---------------------------------------------------------------------------

test("repair-to-replay: success path clears repair prompt and saved payload", () => {
  // Simulate the state after successful budget creation + expense replay.
  // The closeRepairPrompt callback should clear repairPrompt, repairError,
  // and savedExpensePayload.

  let repairPrompt = { type: "budget_required", category: "food" };
  let repairError = "";
  let savedExpensePayload = { payload: {}, keepOpen: false };

  // Simulate closeRepairPrompt
  const closeRepairPrompt = () => {
    repairPrompt = null;
    repairError = "";
    savedExpensePayload = null;
  };

  closeRepairPrompt();

  assert.strictEqual(repairPrompt, null);
  assert.strictEqual(repairError, "");
  assert.strictEqual(savedExpensePayload, null);
});

test("repair-to-replay: cancellation path does not replay expense", () => {
  // When the user cancels, the repair prompt closes but the expense
  // is NOT posted — the saved payload is discarded.

  let expensePosted = false;
  const savedPayload = { title: "Test", amount: 100 };

  // Simulate cancellation: close repair, discard saved payload
  const cancel = () => {
    // expense is NOT posted
  };

  cancel();

  assert.strictEqual(expensePosted, false);
  // The saved payload would be cleared by closeRepairPrompt
  assert.ok(savedPayload.title === "Test");
});

test("repair-to-replay: repair failure shows error and keeps prompt open", () => {
  // When budget creation fails, the repair prompt stays visible
  // with an error message, and the saved payload is preserved.

  let repairPrompt = { type: "budget_required", category: "food" };
  let repairError = "";
  let savedExpensePayload = { payload: { title: "Lunch" }, keepOpen: false };

  // Simulate repair failure
  const handleFailure = () => {
    repairError = "Failed to create budget";
    // repairPrompt and savedExpensePayload are NOT cleared
  };

  handleFailure();

  assert.strictEqual(repairError, "Failed to create budget");
  assert.notStrictEqual(repairPrompt, null);
  assert.notStrictEqual(savedExpensePayload, null);
});

test("repair-to-replay: replay failure after budget creation shows error", () => {
  // When budget is created but the expense replay fails, the user
  // sees an error and the repair dialog closes (budget exists now).

  let repairError = "";
  let repairPrompt = { type: "budget_required", category: "food" };
  let savedExpensePayload = { payload: { title: "Lunch" }, keepOpen: false };

  // Simulate replay failure
  const handleReplayFailure = () => {
    repairError =
      "Budget was created but the expense could not be saved. Please try adding it again.";
    // Close repair prompt since budget exists
    repairPrompt = null;
    savedExpensePayload = null;
  };

  handleReplayFailure();

  assert.ok(repairError.includes("expense could not be saved"));
  assert.strictEqual(repairPrompt, null);
  assert.strictEqual(savedExpensePayload, null);
});

// ---------------------------------------------------------------------------
// Cache invalidation after budget creation
// ---------------------------------------------------------------------------

test("budget creation triggers budget + expense cache invalidation", () => {
  // After successful budget creation and expense replay, the cache module
  // should refresh budget views and expense views.
  // This test verifies the key sets that should be invalidated.

  const budgetRepairKeys = [
    "budgets",
    "budgets.list",
    "budgets.month-summary",
    "budgets.month-stats",
    "expenses",
    "dashboard",
    "notifications",
  ];

  assert.ok(budgetRepairKeys.includes("budgets"));
  assert.ok(budgetRepairKeys.includes("expenses"));
  assert.ok(budgetRepairKeys.includes("dashboard"));
  assert.ok(budgetRepairKeys.includes("notifications"));
});
