import assert from "node:assert/strict";
import test from "node:test";

import {
  PROJECT_DELETE_ACTIONS,
  buildProjectDeletionResolutionPayload,
  canSubmitCascadeVoid,
  shouldOpenProjectDeletionResolution,
} from "./projectDeletionResolution.js";

test("non-pristine project delete opens the resolution flow", () => {
  assert.equal(shouldOpenProjectDeletionResolution({ is_pristine: false }), true);
  assert.equal(shouldOpenProjectDeletionResolution({ is_pristine: true }), false);
});

test("cascade void requires exact project title confirmation", () => {
  const project = { title: "June trip" };

  assert.equal(canSubmitCascadeVoid(project, ""), false);
  assert.equal(canSubmitCascadeVoid(project, "june trip"), false);
  assert.equal(canSubmitCascadeVoid(project, "June trip"), true);
});

test("resolution payload maps archive detach and cascade actions", () => {
  const project = { title: "June trip" };

  assert.deepEqual(
    buildProjectDeletionResolutionPayload(PROJECT_DELETE_ACTIONS.ARCHIVE, project),
    { action: "ARCHIVE" },
  );
  assert.deepEqual(
    buildProjectDeletionResolutionPayload(PROJECT_DELETE_ACTIONS.DETACH_EXPENSES, project),
    { action: "DETACH_EXPENSES" },
  );
  assert.deepEqual(
    buildProjectDeletionResolutionPayload(PROJECT_DELETE_ACTIONS.CASCADE_VOID, project, "June trip"),
    { action: "CASCADE_VOID", confirm_title: "June trip" },
  );
});
