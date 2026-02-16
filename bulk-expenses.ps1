$Email = "testuser3@gmail.com"
$Password = "helloTESTUSER32005!"
$ApiBase = "http://127.0.0.1:9000"

# LOGIN (gets JWT)
$loginBody = "username=$Email&password=$Password"
$loginRes = Invoke-RestMethod -Method Post -Uri "$ApiBase/users/sign-in" -Body $loginBody -ContentType "application/x-www-form-urlencoded"
$token = $loginRes.access_token

$headers = @{
  Authorization  = "Bearer $token"
  "Content-Type" = "application/json"
}

# EXPENSES
$expenses = @(
  @{ title = "Groceries"; amount = 85000; category = "Food"; description = "Weekly groceries"; date = "2026-02-01" },
  @{ title = "Taxi"; amount = 35000; category = "Transport"; description = "Ride to office"; date = "2026-02-01" },
  @{ title = "Electric bill"; amount = 120000; category = "Utilities"; description = "January electricity"; date = "2026-02-02" },
  @{ title = "Rent"; amount = 2500000; category = "Housing"; description = "February rent"; date = "2026-02-02" },
  @{ title = "Mobile data"; amount = 60000; category = "Utilities"; description = "Monthly plan"; date = "2026-02-03" },
  @{ title = "Lunch"; amount = 45000; category = "Food"; description = "Cafe lunch"; date = "2026-02-03" },
  @{ title = "Gym"; amount = 180000; category = "Other"; description = "Monthly membership"; date = "2026-02-04" },
  @{ title = "Movie tickets"; amount = 70000; category = "Entertainment"; description = "Cinema"; date = "2026-02-04" },
  @{ title = "Metro card"; amount = 25000; category = "Transport"; description = "Top up"; date = "2026-02-05" },
  @{ title = "Coffee"; amount = 18000; category = "Food"; description = "Morning coffee"; date = "2026-02-05" },
  @{ title = "Internet bill"; amount = 150000; category = "Utilities"; description = "Home internet"; date = "2026-02-06" },
  @{ title = "Groceries"; amount = 92000; category = "Food"; description = "Weekend groceries"; date = "2026-02-06" },
  @{ title = "Taxi"; amount = 40000; category = "Transport"; description = "Ride home"; date = "2026-02-03" },
  @{ title = "New headphones"; amount = 320000; category = "Other"; description = "Electronics"; date = "2026-02-02" },
  @{ title = "Dinner"; amount = 120000; category = "Food"; description = "Restaurant"; date = "2026-02-06" },
  @{ title = "Gas refill"; amount = 200000; category = "Transport"; description = "Fuel"; date = "2026-02-05" },
  @{ title = "Streaming subscription"; amount = 45000; category = "Entertainment"; description = "Monthly"; date = "2026-02-04" },
  @{ title = "Water bill"; amount = 50000; category = "Utilities"; description = "January water"; date = "2026-02-03" },
  @{ title = "Market vegetables"; amount = 38000; category = "Food"; description = "Local market"; date = "2026-02-04" },
  @{ title = "Home supplies"; amount = 68000; category = "Other"; description = "Cleaning items"; date = "2026-02-01" }
)

foreach ($exp in $expenses) {
  $json = $exp | ConvertTo-Json
  try {
    Invoke-RestMethod -Method Post -Uri "$ApiBase/expenses/" -Headers $headers -Body $json | Out-Null
    Write-Host "OK:" $exp.title
  }
  catch {
    Write-Host "FAIL:" $exp.title $_.Exception.Message
  }
}
