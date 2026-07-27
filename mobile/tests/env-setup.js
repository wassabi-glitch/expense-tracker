// Disable RNTL auto-cleanup so we control cleanup between renders
// This must be set before RNTL is imported in any test file.
process.env.RNTL_SKIP_AUTO_CLEANUP = 'true';
