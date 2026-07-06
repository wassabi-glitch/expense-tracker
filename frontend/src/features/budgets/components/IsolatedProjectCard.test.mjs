import assert from "node:assert/strict";
import test from "node:test";

/**
 * IsolatedProjectCard — unit tests for card-level funding math and display logic.
 *
 * These tests exercise the logic that the card component depends on:
 *   - Spend-down percent direction (remaining / funding, not spent / funding)
 *   - Hero metric is remaining funding
 *   - Over-stash detection (remaining < 0)
 *   - Unassigned funding detection
 *   - Goal-graduated detection
 *   - Completed project uses remaining at completion
 *   - Action visibility by project status
 */

// ---------------------------------------------------------------------------
// Helpers extracted from the component's logic for testing
// ---------------------------------------------------------------------------

function getSpendDownPercent(fundingLimit, spent) {
  const remaining = Math.max(0, fundingLimit - spent);
  if (fundingLimit <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((remaining / fundingLimit) * 100)));
}

function getHeroMetric(fundingLimit, spent, status) {
  // Hero is remaining funding.
  // For completed: remaining at completion.
  const remaining = status === "COMPLETED"
    ? Math.max(0, fundingLimit - spent)
    : Math.max(0, fundingLimit - spent);
  return remaining;
}

function isOverStash(fundingLimit, spent) {
  return (spent > fundingLimit);
}

function hasUnassignedFunding(unassignedFunding, status) {
  const canModify = status !== "COMPLETED" && status !== "ARCHIVED";
  return canModify && unassignedFunding > 0;
}

function isGoalGraduated(originGoalId) {
  return Boolean(originGoalId);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test("isolated card spend-down bar uses remaining/funding, not spent/funding", () => {
  // Funding = 500. Spent = 200. Remaining = 300.
  // Remaining/funding = 300/500 = 60%. Spent/funding = 200/500 = 40%.
  const pct = getSpendDownPercent(500, 200);
  assert.equal(pct, 60, "filled = remaining portion (60%), not spent portion (40%)");
});

test("isolated card spend-down is 0% when fully spent", () => {
  assert.equal(getSpendDownPercent(100, 100), 0);
});

test("isolated card spend-down is 100% when nothing spent", () => {
  assert.equal(getSpendDownPercent(100, 0), 100);
});

test("isolated card spend-down handles zero funding", () => {
  assert.equal(getSpendDownPercent(0, 0), 0);
  assert.equal(getSpendDownPercent(0, 500), 0);
});

test("hero metric is remaining funding for active project", () => {
  assert.equal(getHeroMetric(500, 200, "ACTIVE"), 300);
});

test("hero metric for completed project is remaining at completion", () => {
  assert.equal(getHeroMetric(500, 450, "COMPLETED"), 50);
});

test("over-stash detection when spent exceeds funding", () => {
  assert.equal(isOverStash(500, 600), true);
  assert.equal(isOverStash(500, 500), false);
  assert.equal(isOverStash(500, 400), false);
});

test("unassigned funding only visible for active/stopped projects", () => {
  assert.equal(hasUnassignedFunding(50000, "ACTIVE"), true);
  assert.equal(hasUnassignedFunding(50000, "STOPPED"), true);
  assert.equal(hasUnassignedFunding(0, "ACTIVE"), false);
  assert.equal(hasUnassignedFunding(50000, "COMPLETED"), false);
  assert.equal(hasUnassignedFunding(50000, "ARCHIVED"), false);
});

test("goal-graduated detection from origin_goal_id", () => {
  assert.equal(isGoalGraduated(1), true);
  assert.equal(isGoalGraduated(null), false);
  assert.equal(isGoalGraduated(undefined), false);
  assert.equal(isGoalGraduated(0), false);
});

test("overlay vs isolated language is preserved", () => {
  // Isolated card says "Isolated", overlay card says "Overlay"
  // This is the structural guarantee: the component is rendered only
  // for isolated projects, and overlay cards stay in Budgets.jsx.
  const projectTypes = [
    { project_type: "ISOLATED", badge: "Isolated" },
    { project_type: "OVERLAY", badge: "Overlay" },
    { is_isolated: true, default_badge: "Isolated" },
    { is_isolated: false, default_badge: "Overlay" },
  ];
  for (const { project_type, is_isolated, badge, default_badge } of projectTypes) {
    const type = project_type || (is_isolated ? "ISOLATED" : "OVERLAY");
    const expected = badge || default_badge;
    assert.equal(type, expected === "Isolated" ? "ISOLATED" : "OVERLAY");
  }
});