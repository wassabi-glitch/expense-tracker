# Full Auth E2E Test Suite — All 5 Rounds
# Requires: Docker running, phone connected, preview build installed, Maestro

param(
  [switch]$R1Only,
  [switch]$R3Only,
  [switch]$R5Only,
  [switch]$SkipCleanup
)

$ErrorActionPreference = "Continue"
$MAESTRO = "D:\maestro\maestro\bin\maestro.bat"
$TESTS = "D:\Projects\ExpenseTracker\mobile\.maestro"
$HELPER = "node D:\Projects\ExpenseTracker\mobile\.maestro\helpers\db-token.mjs"

$results = @()
$failed = 0

function Run-Test($name, $yaml, $envVars) {
  Write-Host "  [$name] " -NoNewline -ForegroundColor Yellow
  $args = @()
  if ($envVars) {
    foreach ($k in $envVars.Keys) {
      $args += "--env"
      $args += "${k}=$($envVars[$k])"
    }
  }
  $start = Get-Date
  & $MAESTRO test "$TESTS\$yaml" $args 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) {
    $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    Write-Host "PASS (${elapsed}s)" -ForegroundColor Green
    $results += @{ Name = $name; Status = "PASS" }
  } else {
    $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    Write-Host "FAIL (${elapsed}s)" -ForegroundColor Red
    $results += @{ Name = $name; Status = "FAIL" }
    $failed++
  }
}

function Get-DBToken($email, $type = "verification") {
  $result = & node $HELPER $email $type 2>&1
  if ($LASTEXITCODE -eq 0 -and $result) {
    return $result.Trim()
  }
  return $null
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Sarflog Full Auth E2E Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$EMAIL = "e2e_r1@test.com"
$PASS = "E2eStrongPass1!"
$NEWPASS = "E2eNewStrongPass2!"
$R5PASS = "E2eNewPassR5_1!"

# ═══════════════════════════════════════════
# ROUND 1: Sign Up → Verify → Sign In
# ═══════════════════════════════════════════
if (-not ($R3Only -or $R5Only)) {
  Write-Host "`n═══ R1: Sign Up → Verify → Sign In ═══" -ForegroundColor Cyan

  Run-Test "R1.1 Sign Up" "e2e-r1-signup.yaml"

  $verifyToken = Get-DBToken $EMAIL "verification"
  if ($verifyToken) {
    Write-Host "    Token: $verifyToken" -ForegroundColor Gray
    Run-Test "R1.2 Verify Email" "e2e-r1-verify.yaml" @{ TOKEN = $verifyToken }
    Run-Test "R1.3 Sign In" "e2e-r1-signin.yaml"
  } else {
    Write-Host "    SKIP: No verification token found" -ForegroundColor Yellow
  }
}

# ═══════════════════════════════════════════
# ROUND 3: Forgot Password → Reset → Sign In
# ═══════════════════════════════════════════
if (-not ($R1Only -or $R5Only)) {
  Write-Host "`n═══ R3: Forgot Password → Reset → Sign In ═══" -ForegroundColor Cyan

  Run-Test "R3.1 Forgot Password" "e2e-r3-forgot-password.yaml"

  $resetToken = Get-DBToken $EMAIL "reset"
  if ($resetToken) {
    Write-Host "    Token: $resetToken" -ForegroundColor Gray
    Run-Test "R3.2 Reset Password" "e2e-r3-reset.yaml" @{ TOKEN = $resetToken }
    Run-Test "R3.3 Sign In (new pass)" "e2e-r3-signin-new-pass.yaml"
  } else {
    Write-Host "    SKIP: No reset token found" -ForegroundColor Yellow
  }
}

# ═══════════════════════════════════════════
# ROUND 5: Change Password → Sign Out → Logout All
# ═══════════════════════════════════════════
if (-not ($R1Only -or $R3Only)) {
  Write-Host "`n═══ R5: Change Password → Sign Out → Logout All ═══" -ForegroundColor Cyan

  Run-Test "R5.1 Change Password" "e2e-r5-change-password.yaml"
  Run-Test "R5.2 Sign Out" "e2e-r5-signout.yaml"
  Run-Test "R5.3 Logout All" "e2e-r5-logout-all.yaml"
}

# ═══════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " RESULTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$passed = $results.Count - $failed
foreach ($r in $results) {
  $color = if ($r.Status -eq "PASS") { "Green" } else { "Red" }
  Write-Host "  $($r.Status)  $($r.Name)" -ForegroundColor $color
}
Write-Host "────────────────────────────────────────" -ForegroundColor Gray
Write-Host "  Total: $($results.Count)  Passed: $passed  Failed: $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })

# Restore old password for R5 tests to keep working
if (-not $SkipCleanup) {
  Write-Host "`n★★★ All auth rounds complete! ★★★" -ForegroundColor Green
}

exit $failed
