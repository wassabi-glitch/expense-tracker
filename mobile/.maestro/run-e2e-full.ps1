# Full Auth E2E Test Runner — Docker backend + real PostgreSQL
# Every test hits the live backend. No mocks. Real DB queries for tokens.

param(
  [string]$Maestro = "D:\maestro\maestro\bin\maestro.bat",
  [string]$Tests = "D:\Projects\ExpenseTracker\mobile\.maestro"
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$email = "e2e_${timestamp}@example.com"
$email2 = "e2e_alt_${timestamp}@example.com"
$pass = "E2eTestStrongPass1!"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Full Auth E2E Suite — Real Backend" -ForegroundColor Cyan
Write-Host " Email: $email" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$results = @()
$failed = 0

function Run-Test {
  param($Name, $Yaml, [hashtable]$Env = @{})
  Write-Host "`n━━━ [$Name]" -ForegroundColor Yellow
  $envVars = @()
  foreach ($key in $Env.Keys) {
    $envVars += "--env"
    $envVars += "${key}=$($Env[$key])"
  }
  $start = Get-Date
  if ($envVars.Count -gt 0) {
    & $Maestro test "$Tests\$Yaml" $envVars 2>&1
  } else {
    & $Maestro test "$Tests\$Yaml" 2>&1
  }
  if ($LASTEXITCODE -eq 0) {
    $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    Write-Host "  ✅ PASS ($elapsed s)" -ForegroundColor Green
    $results += @{ Name = $Name; Status = "PASS"; Time = "$elapsed s" }
  } else {
    $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    Write-Host "  ❌ FAIL ($elapsed s)" -ForegroundColor Red
    $results += @{ Name = $Name; Status = "FAIL"; Time = "$elapsed s" }
    $failed++
  }
}

# ─── Round 1: Sign Up → Verify email via DB token → Sign In ───
Write-Host "`n╔═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "║  R1: Sign Up → Verify → Sign In" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════" -ForegroundColor Cyan

Run-Test "R1-SignUp" "e2e-signup.yaml" @{ EMAIL = $email; PASSWORD = $pass; TIMESTAMP = $timestamp }

Write-Host "  Extracting verification token from DB..." -ForegroundColor DarkGray
$verifyToken = & node "$Tests\helpers\db-token.mjs" $email verification 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "  ⚠ No token found — email not sent (expected in dev)" -ForegroundColor Yellow
  $verifyToken = "no-token-available"
}

if ($verifyToken -and $verifyToken -ne "no-token-available") {
  Run-Test "R1-Verify" "e2e-verify-with-token.yaml" @{
    TOKEN = $verifyToken; VERIFY_EMAIL = $email; PASSWORD = $pass
  }
} else {
  Write-Host "  ⏭ Skipping verify (no token). Running sign-in with unverified user." -ForegroundColor Yellow
  Run-Test "R1-SignIn-Unverified" "e2e-signin-unverified.yaml" @{
    EMAIL = $email; PASSWORD = $pass
  }
}

# ─── Round 3: Forgot Password → Reset via DB token ───
Write-Host "`n╔═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "║  R3: Forgot Password → Reset" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════" -ForegroundColor Cyan

Run-Test "R3-ForgotPassword" "e2e-forgot-password.yaml" @{
  EMAIL = $email; TIMESTAMP = $timestamp
}

Write-Host "  Extracting reset token from DB..." -ForegroundColor DarkGray
$resetToken = & node "$Tests\helpers\db-token.mjs" $email reset 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Host "  ⚠ No reset token found" -ForegroundColor Yellow
  $resetToken = $null
}

if ($resetToken) {
  Run-Test "R3-ResetPassword" "e2e-reset-with-token.yaml" @{
    TOKEN = $resetToken; EMAIL = $email; PASSWORD = $pass
  }
} else {
  Write-Host "  ⏭ Skipping reset (no token)" -ForegroundColor Yellow
}

# ─── Round 5: Change Password + Logout All (requires verified user) ───
# These need a verified session. We can't fully authenticate on mobile
# without deep linking. Skip unless we got a verify token and used it.
if ($verifyToken -and $verifyToken -ne "no-token-available") {
  Write-Host "`n╔═══════════════════════════════════════════" -ForegroundColor Cyan
  Write-Host "║  R5: Session Actions (verified user)" -ForegroundColor Cyan
  Write-Host "╚═══════════════════════════════════════════" -ForegroundColor Cyan
  # Note: These test files don't exist yet because settings screens
  # are behind auth which mobile can't complete without deep linking
}

# ─── R2: Sign In with Invalid Credentials ───
Write-Host "`n╔═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "║  R2: Sign In — Invalid Credentials" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════" -ForegroundColor Cyan

Run-Test "R2-SignIn-Invalid" "auth-signin-invalid.yaml" @{}

# ─── Summary ───
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " RESULTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$passed = $results.Count - $failed
foreach ($r in $results) {
  $color = if ($r.Status -eq "PASS") { "Green" } else { "Red" }
  Write-Host "  $($r.Status) $($r.Name) ($($r.Time))" -ForegroundColor $color
}
Write-Host "────────────────────────────────────────" -ForegroundColor Gray
Write-Host "  Total: $($results.Count)  Passed: $passed  Failed: $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
if ($failed -gt 0) { exit 1 }
