export const PROJECT_DELETE_ACTIONS = {
  ARCHIVE: "ARCHIVE",
  DETACH_EXPENSES: "DETACH_EXPENSES",
  CASCADE_VOID: "CASCADE_VOID",
};

export function shouldOpenProjectDeletionResolution(preview) {
  return Boolean(preview && preview.is_pristine === false);
}

export function canSubmitCascadeVoid(project, confirmTitle) {
  return Boolean(project?.title && confirmTitle === project.title);
}

export function buildProjectDeletionResolutionPayload(action, project, confirmTitle = "") {
  const payload = { action };
  if (action === PROJECT_DELETE_ACTIONS.CASCADE_VOID) {
    payload.confirm_title = canSubmitCascadeVoid(project, confirmTitle) ? confirmTitle : "";
  }
  return payload;
}
