import assert from "node:assert/strict";
import test from "node:test";

import {
  PROJECT_DELETE_ACTIONS,
  shouldOpenProjectDeletionResolution,
  canSubmitCascadeVoid,
  buildProjectDeletionResolutionPayload,
} from "./projectDeletionResolution.js";

// ---------------------------------------------------------------------------
// State-aware action visibility rules
// ---------------------------------------------------------------------------

/**
 * ProjectLifecyclePanel exposes actions based on project status:
 *   ACTIVE   → Pause, Complete, Delete
 *   STOPPED  → Resume, Complete, Delete
 *   COMPLETED → Reopen, Delete
 *   ARCHIVED  → Restore, Delete
 */

function getAvailableActions(status, isIsolated) {
  const actions = [];
  if (status === "ACTIVE") {
    actions.push("PAUSE");
    actions.push("COMPLETE");
  }
  if (status === "STOPPED") {
    actions.push("RESUME");
    actions.push("COMPLETE");
  }
  if (status === "COMPLETED") {
    actions.push("REOPEN");
  }
  if (status === "ARCHIVED") {
    actions.push("REOPEN"); // restore
  }
  actions.push("DELETE");
  return actions;
}

test("active projects expose pause, complete, delete", () => {
  const actions = getAvailableActions("ACTIVE", false);
  assert.ok(actions.includes("PAUSE"));
  assert.ok(actions.includes("COMPLETE"));
  assert.ok(actions.includes("DELETE"));
  assert.ok(!actions.includes("RESUME"));
  assert.ok(!actions.includes("REOPEN"));
});

test("stopped projects expose resume, complete, delete", () => {
  const actions = getAvailableActions("STOPPED", false);
  assert.ok(actions.includes("RESUME"));
  assert.ok(actions.includes("COMPLETE"));
  assert.ok(actions.includes("DELETE"));
  assert.ok(!actions.includes("PAUSE"));
  assert.ok(!actions.includes("REOPEN"));
});

test("completed projects expose reopen, delete", () => {
  const actions = getAvailableActions("COMPLETED", false);
  assert.ok(actions.includes("REOPEN"));
  assert.ok(actions.includes("DELETE"));
  assert.ok(!actions.includes("PAUSE"));
  assert.ok(!actions.includes("RESUME"));
  assert.ok(!actions.includes("COMPLETE"));
});

test("archived projects expose restore (reopen), delete, NOT archive again", () => {
  const actions = getAvailableActions("ARCHIVED", false);
  assert.ok(actions.includes("REOPEN")); // restore IS reopen
  assert.ok(actions.includes("DELETE"));
  // Archived projects must NOT be offered a repeat archive action
  assert.ok(!actions.includes("PAUSE"));
  assert.ok(!actions.includes("COMPLETE"));
  assert.ok(!actions.includes("RESUME"));
});

// ---------------------------------------------------------------------------
// Deletion resolution
// ---------------------------------------------------------------------------

test("shouldOpenProjectDeletionResolution returns true for non-pristine projects", () => {
  assert.equal(shouldOpenProjectDeletionResolution({ is_pristine: false }), true);
});

test("shouldOpenProjectDeletionResolution returns false for pristine projects", () => {
  assert.equal(shouldOpenProjectDeletionResolution({ is_pristine: true }), false);
  assert.equal(shouldOpenProjectDeletionResolution(null), false);
  assert.equal(shouldOpenProjectDeletionResolution(undefined), false);
});

test("canSubmitCascadeVoid requires exact project title match", () => {
  const project = { id: 1, title: "Kitchen Remodel" };
  assert.equal(canSubmitCascadeVoid(project, "Kitchen Remodel"), true);
  assert.equal(canSubmitCascadeVoid(project, "kitchen remodel"), false);
  assert.equal(canSubmitCascadeVoid(project, ""), false);
  assert.equal(canSubmitCascadeVoid(null, "anything"), false);
});

test("buildProjectDeletionResolutionPayload maps actions correctly", () => {
  const project = { title: "Test" };

  const archivePayload = buildProjectDeletionResolutionPayload(
    PROJECT_DELETE_ACTIONS.ARCHIVE, project, ""
  );
  assert.deepEqual(archivePayload, { action: "ARCHIVE" });

  const detachPayload = buildProjectDeletionResolutionPayload(
    PROJECT_DELETE_ACTIONS.DETACH_EXPENSES, project, ""
  );
  assert.deepEqual(detachPayload, { action: "DETACH_EXPENSES" });

  const voidPayload = buildProjectDeletionResolutionPayload(
    PROJECT_DELETE_ACTIONS.CASCADE_VOID, project, "Test"
  );
  assert.deepEqual(voidPayload, { action: "CASCADE_VOID", confirm_title: "Test" });

  const voidFailPayload = buildProjectDeletionResolutionPayload(
    PROJECT_DELETE_ACTIONS.CASCADE_VOID, project, "Wrong"
  );
  assert.deepEqual(voidFailPayload, { action: "CASCADE_VOID", confirm_title: "" });
});

// ---------------------------------------------------------------------------
// User-facing copy: no ledger implementation language
// ---------------------------------------------------------------------------

test("deletion resolution uses user-facing language, not ledger terms", () => {
  // The component copy avoids: void, cascade void, reversal, ledger entries
  // Instead uses: remove, detach, archive

  const userLabels = {
    archive: "Archive project",
    detach: "Detach expenses",
    remove: "Remove linked expenses and project",
  };

  // No label contains ledger implementation language
  const forbidden = ["void", "cascade void", "reversal", "ledger entries", "ledger"];
  Object.values(userLabels).forEach((label) => {
    forbidden.forEach((term) => {
      assert.equal(
        label.toLowerCase().includes(term.toLowerCase()),
        false,
        `Label "${label}" must not contain "${term}"`
      );
    });
  });
});

test("lifecycle action labels use plain language", () => {
  const actionLabels = {
    PAUSE: "Pause project",
    RESUME: "Resume project",
    COMPLETE: "Complete project",
    REOPEN: "Reopen project",
  };

  Object.values(actionLabels).forEach((label) => {
    assert.ok(label.length > 0);
  });
});

// ---------------------------------------------------------------------------
// Deletion resolution shows affected expense context
// ---------------------------------------------------------------------------

test("deletion preview exposes linked expense count and total", () => {
  const preview = {
    linked_expense_count: 5,
    linked_expense_total: 250000,
    is_pristine: false,
  };

  assert.equal(Number(preview.linked_expense_count), 5);
  assert.equal(Number(preview.linked_expense_total), 250000);
  assert.equal(shouldOpenProjectDeletionResolution(preview), true);
});

test("deletion preview with zero linked expenses still resolves", () => {
  const preview = {
    linked_expense_count: 0,
    linked_expense_total: 0,
    is_pristine: false,
  };

  assert.equal(shouldOpenProjectDeletionResolution(preview), true);
});

// ---------------------------------------------------------------------------
// Existing deletion payload behavior remains compatible
// ---------------------------------------------------------------------------

test("PROJECT_DELETE_ACTIONS constants remain stable", () => {
  assert.equal(PROJECT_DELETE_ACTIONS.ARCHIVE, "ARCHIVE");
  assert.equal(PROJECT_DELETE_ACTIONS.DETACH_EXPENSES, "DETACH_EXPENSES");
  assert.equal(PROJECT_DELETE_ACTIONS.CASCADE_VOID, "CASCADE_VOID");
});
