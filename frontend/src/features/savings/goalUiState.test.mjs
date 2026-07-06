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

test("goal wizard exposes Fund Project and creates the backend intent payload", () => {
  assert.equal(
    GOAL_CREATE_CHOICE_COPY.some((choice) => choice.intent === "FUND_PROJECT" && choice.title === "Fund a project"),
    true,
  );

  assert.deepEqual(
    buildGoalCreatePayload({
      title: "Kitchen remodel",
      target_amount: 5_000_000,
      target_date: "2026-09-30",
      intent: "FUND_PROJECT",
    }),
    {
      title: "Kitchen remodel",
      target_amount: 5_000_000,
      target_date: "2026-09-30",
      intent: "FUND_PROJECT",
      currency: "UZS",
    },
  );
});

test("active Fund Project cards expose saving actions and project graduation only", () => {
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
  assert.equal(state.canReserve, true);
  assert.equal(state.canUnreserve, true);
  assert.equal(state.canPreparePayment, false);
  assert.deepEqual(state.primaryAction, {
    kind: "graduate-project",
    label: "Create project",
    disabled: false,
  });
});

test("graduated Fund Project cards are read-only history with a project route", () => {
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

  assert.equal(state.statusLabel, "Graduated to project");
  assert.equal(state.isReadOnly, true);
  assert.equal(state.canReserve, false);
  assert.equal(state.canUnreserve, false);
  assert.equal(state.canPreparePayment, false);
  assert.equal(state.canArchive, false);
  assert.equal(state.primaryAction.kind, "open-project");
  assert.equal(state.primaryAction.label, "View project");
  assert.equal(state.primaryAction.disabled, false);
  assert.match(state.intentDescription, /project top-ups/);
});

test("graduation confirmation builds isolated-project payload and navigation state", () => {
  const goal = {
    id: 10,
    title: "Studio build",
    target_date: "2026-09-30",
  };

  assert.deepEqual(buildFundProjectGraduationPayload(goal, "2026-07-06"), {
    project_title: "Studio build",
    start_date: "2026-07-06",
    target_end_date: "2026-09-30",
    is_isolated: true,
  });

  assert.deepEqual(buildFundProjectNavigationState({ id: 44 }, goal), {
    projectId: 44,
    originGoalId: 10,
  });
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
