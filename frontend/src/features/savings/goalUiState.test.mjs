import assert from "node:assert/strict";
import test from "node:test";

import {
  GOAL_CREATE_CHOICE_COPY,
  buildFundProjectGraduationPayload,
  buildFundProjectNavigationState,
  buildGoalCreatePayload,
  getGoalCardUiState,
} from "./goalUiState.js";
import { GOAL_MUTATION_INVALIDATION_KEYS } from "./goalQueryInvalidation.js";

test("goal wizard does not expose frozen Fund Project intent", () => {
  assert.equal(
    GOAL_CREATE_CHOICE_COPY.some((choice) => choice.intent === "FUND_PROJECT"),
    false,
  );
  assert.equal(GOAL_CREATE_CHOICE_COPY.length, 3);
  assert.equal(
    GOAL_CREATE_CHOICE_COPY.every((choice) =>
      ["RESERVE", "PLANNED_PURCHASE", "PAY_OBLIGATION"].includes(choice.intent),
    ),
    true,
  );
});

test("goal creation payload builds correctly for active core intents", () => {
  assert.deepEqual(
    buildGoalCreatePayload({
      title: "Emergency fund",
      target_amount: 5_000_000,
      target_date: null,
      intent: "RESERVE",
    }),
    {
      title: "Emergency fund",
      target_amount: 5_000_000,
      target_date: null,
      intent: "RESERVE",
      currency: "UZS",
    },
  );

  assert.deepEqual(
    buildGoalCreatePayload({
      title: "New laptop",
      target_amount: 3_000_000,
      target_date: "2026-12-31",
      intent: "PLANNED_PURCHASE",
    }),
    {
      title: "New laptop",
      target_amount: 3_000_000,
      target_date: "2026-12-31",
      intent: "PLANNED_PURCHASE",
      currency: "UZS",
    },
  );
});

test("existing Fund Project cards are frozen read-only without saving actions", () => {
  const state = getGoalCardUiState(
    {
      id: 10,
      title: "Studio build",
      intent: "FUND_PROJECT",
      status: "ACTIVE",
      unreleased_amount: 750_000,
      funding_sources: [{ wallet_id: 1, unreleased_amount: 750_000 }],
    },
    { eligibleWalletCount: 2, canPreparePayment: true },
  );

  assert.equal(state.intentLabel, "Project fund");
  assert.equal(state.isReadOnly, true);
  assert.equal(state.canReserve, false);
  assert.equal(state.canUnreserve, false);
  assert.equal(state.canPreparePayment, false);
  assert.equal(state.canArchive, false);
  assert.equal(state.primaryAction, null);
  assert.match(state.intentDescription, /frozen/i);
});

test("graduated Fund Project cards remain read-only frozen history", () => {
  const state = getGoalCardUiState(
    {
      id: 10,
      title: "Studio build",
      intent: "FUND_PROJECT",
      status: "GRADUATED",
      linked_project_id: 44,
      unreleased_amount: 0,
      funding_sources: [{ wallet_id: 1, unreleased_amount: 0 }],
    },
    { eligibleWalletCount: 2, canPreparePayment: true },
  );

  assert.equal(state.isReadOnly, true);
  assert.equal(state.canReserve, false);
  assert.equal(state.canUnreserve, false);
  assert.equal(state.canPreparePayment, false);
  assert.equal(state.canArchive, false);
  assert.equal(state.primaryAction, null);
  assert.match(state.intentDescription, /frozen/i);
});

test("active core intents have correct primary actions", () => {
  const reserveState = getGoalCardUiState({
    intent: "RESERVE",
    status: "ACTIVE",
    unreleased_amount: 500_000,
    funding_sources: [{ wallet_id: 1, unreleased_amount: 500_000 }],
  });
  assert.equal(reserveState.primaryAction.kind, "use-reserve");

  const purchaseState = getGoalCardUiState({
    intent: "PLANNED_PURCHASE",
    status: "ACTIVE",
    unreleased_amount: 500_000,
    funding_sources: [{ wallet_id: 1, unreleased_amount: 500_000 }],
  });
  assert.equal(purchaseState.primaryAction.kind, "record-purchase");

  const obligationState = getGoalCardUiState({
    intent: "PAY_OBLIGATION",
    status: "ACTIVE",
    unreleased_amount: 500_000,
    funding_sources: [{ wallet_id: 1, unreleased_amount: 500_000 }],
  });
  assert.equal(obligationState.primaryAction.kind, "make-payment");
});

test("goal mutations refresh stale project, budget, wallet, and goal surfaces", () => {
  const keys = GOAL_MUTATION_INVALIDATION_KEYS.map((key) => key.join(":"));

  assert.equal(keys.includes("goals"), true);
  assert.equal(keys.includes("projects"), true);
  assert.equal(keys.includes("budgets"), true);
  assert.equal(keys.includes("wallets"), true);
  assert.equal(keys.includes("dashboard"), true);
});

test("invalid terminal actions stay disabled for non-project goal states", () => {
  const completedPurchase = getGoalCardUiState({
    intent: "PLANNED_PURCHASE",
    status: "COMPLETED",
    linked_expense_event_id: 99,
    unreleased_amount: 0,
    funding_sources: [],
  });

  assert.equal(completedPurchase.primaryAction.label, "Record purchase");
  assert.equal(completedPurchase.primaryAction.disabled, true);
});
