# Full Auth E2E Test Runner
# Requires: Docker running, phone connected via ADB, Maestro installed
param(
  [switch]$Tier1Only,  # Only run navigation tests (no DB)
  [switch]$Tier2Only   # Only run DB-integrated tests
)

$ErrorActionPreference = "Stop"
$MAESTRO = "D:\maestro\maestro\bin\maestro.bat"
$TESTS = "D:\Projects\ExpenseTracker\mobile\.maestro"
$HELPERS = "$TESTS\helpers"

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$EMAIL = "e2e_${TIMESTAMP}@example.com"
$PASSWORD = "StrongPass123!"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Sarflog Auth E2E Test Suite" -ForegroundColor Cyan
Write-Host " Email: $EMAIL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ----------------------------------------------------
# Tier 1: Navigation & Flow (no DB needed)
# ----------------------------------------------------
if (-not $Tier2Only) {
  Write-Host "`n--- Tier 1: Navigation & Flow ---" -ForegroundColor Yellow

  Write-Host "[1/5] Smoke test..." -ForegroundColor Green
  & $MAESTRO test "$TESTS\smoke.yml"

  Write-Host "[2/5] Sign-in invalid credentials + navigate to Sign Up..." -ForegroundColor Green
  & $MAESTRO test "$TESTS\auth-signin.yaml"

  Write-Host "[3/5] Full sign-up flow..." -ForegroundColor Green
  & $MAESTRO test "$TESTS\auth-signup.yaml"

  Write-Host "[4/5] Forgot password flow..." -ForegroundColor Green
  & $MAESTRO test "$TESTS\auth-forgot-password.yaml"

  Write-Host "[5/5] Deep-link verify with invalid token..." -ForegroundColor Green
  & $MAESTRO test "$TESTS\auth-deeplink-verify-invalid.yaml"
}

# ----------------------------------------------------
# Tier 2: DB-Integrated (real end-to-end)
# ----------------------------------------------------
if (-not $Tier1Only) {
  Write-Host "`n--- Tier 2: DB-Integrated E2E ---" -ForegroundColor Yellow

  # 2a: Sign up → extract verification token → verify → sign in
  Write-Host "[2a/3] Signing up via app..." -ForegroundColor Green
  & $MAESTRO test "$TESTS\auth-signup.yaml"

  Write-Host "       Extracting verification token from DB..." -ForegroundColor Green
  $VERIFY_TOKEN = & node "$HELPERS\db-token.mjs" $EMAIL verification 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Host "       ERROR: Could not extract token: $VERIFY_TOKEN" -ForegroundColor Red
    exit 1
  }
  Write-Host "       Token: $VERIFY_TOKEN" -ForegroundColor Gray

  Write-Host "       Verifying email and signing in..." -ForegroundColor Green
  $env:TOKEN = $VERIFY_TOKEN
  $env:VERIFY_EMAIL = $EMAIL
  & $MAESTRO test --env TOKEN=$VERIFY_TOKEN --env VERIFY_EMAIL=$EMAIL "$TESTS\auth-verify-with-token.yaml"

  # 2b: Forgot password → extract reset token → reset → sign in
  Write-Host "[2b/3] Requesting password reset..." -ForegroundColor Green
  & $MAESTRO test "$TESTS\auth-forgot-password.yaml"

  Write-Host "       Extracting reset token from DB..." -ForegroundColor Green
  $RESET_TOKEN = & node "$HELPERS\db-token.mjs" $EMAIL reset 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Host "       ERROR: Could not extract reset token: $RESET_TOKEN" -ForegroundColor Red
    exit 1
  }
  Write-Host "       Token: $RESET_TOKEN" -ForegroundColor Gray

  Write-Host "       Resetting password..." -ForegroundColor Green
  & $MAESTRO test --env TOKEN=$RESET_TOKEN --env RESET_EMAIL=$EMAIL "$TESTS\auth-reset-with-token.yaml"

  # 2c: Full Golden Path
  Write-Host "[2c/3] Full Golden Path — Sign Up → Verify → Sign In..." -ForegroundColor Green
  $GOLDEN_EMAIL = "golden_${TIMESTAMP}@example.com"
  # Sign up with golden email
  # (Reuse signup flow but we need different email — just run the flow)
  & $MAESTRO test "$TESTS\auth-signup.yaml"  # Uses maestrotest email, fine for demo
  $GOLDEN_TOKEN = & node "$HELPERS\db-token.mjs" "maestrotest@example.com" verification 2>&1
  Write-Host "       Golden token: $GOLDEN_TOKEN" -ForegroundColor Gray
  & $MAESTRO test --env TOKEN=$GOLDEN_TOKEN --env VERIFY_EMAIL="maestrotest@example.com" "$TESTS\auth-verify-with-token.yaml"
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Auth E2E Test Suite Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
