# Troubleshooting Guide

## Mobile app: "everything was working yesterday, today it's broken"

### Symptom 1: Expo dev build can't connect to Metro (red screen / connection error)

**Error:** `Java.net.ConnectException: Failed to connect to /192.168.1.xx:8081`

**Root cause:** Windows flipped your Wi-Fi network from Private to Public (happens silently after Windows Updates or network changes). Public profile blocks all inbound connections.

**Fix:**
1. Open **Settings → Network & Internet → Wi-Fi**
2. Click your connected network
3. Switch from **Public** to **Private**
4. Reload the app on your phone

---

### Symptom 2: Google Sign-In spinner spins for 2 minutes, then shows generic error

**Logs show:** `[GoogleAuth] Step 1-2 OK`, `[GoogleAuth] Step 3` never completes.

**Root cause:** The mobile app CAN reach Google's servers (gets idToken successfully) but CANNOT reach your PC's backend API on port 9000. This is Windows Firewall blocking the Docker port, even after fixing the Private/Public network profile.

**Why this happens:** Fixing the network profile auto-allows Node.js (Metro on port 8081) but does NOT auto-allow Docker Desktop Backend (API on port 9000). Docker uses a separate process for port forwarding.

**Fix:**
Run this in **PowerShell as Administrator**:
```powershell
netsh advfirewall firewall add rule name="Docker API Port 9000" dir=in action=allow protocol=TCP localport=9000
```

**Verification:** The sign-in should work instantly after adding this rule. No restart needed.

---

## Diagnostic checklist for "suddenly broken, nothing changed"

1. **Can the phone reach the PC at all?**
   - Test Metro: does the JS bundle load on the phone?
   - If no → Wi-Fi network profile flipped to Public (see Symptom 1)

2. **Can the phone reach the backend API?**
   - Check: `[GoogleAuth] Step 3` in Metro logs — does it hang?
   - Quick test: open phone browser → `http://192.168.1.xx:9000/` → should show "Welcome to your Expense Tracker API"
   - If no but desktop `curl localhost:9000` works → Windows Firewall blocking Docker port (see Symptom 2)

3. **Is the Docker database intact?**
   - Check for 500 errors in docker logs: `docker logs expense_api`
   - If `relation "X" does not exist` → migration not applied → `docker exec expense_api alembic upgrade head`

4. **Is the error message showing a raw translation key?**
   - If error text looks like `auth.signIn.errors.something` → error mapping is broken (key mismatch between backend error codes and translation keys)

---

## Error: raw translation key shown instead of error message

**Symptom:** User sees `auth.signIn.errors.auth.generic_error` instead of "Sign-in failed. Please try again."

**Root cause:** Backend error codes use `auth.snake_case` format. The mobile code wraps them in `auth.signIn.errors.${backendCode}` but the translation keys use `camelCase` without the `auth.` prefix.

**Fix location:**
- `mobile/src/features/auth/hooks/use-google-auth.ts` — maps backend error codes to translation keys
- `mobile/src/app/(auth)/sign-in.tsx` — maps backend error codes for email/password sign-in
- `mobile/src/i18n/locales/{en,ru,uz}/index.ts` — actual translation keys under `auth.signIn.errors.*`

**Rule:** Backend detail `auth.snake_case_error` → strip `auth.` prefix → convert to `camelCase` → translation key is `auth.signIn.errors.camelCase`.

---

## Date of this incident

2026-07-28 — Windows flipped Wi-Fi from Private to Public overnight, blocking Metro (8081) and Docker API (9000). Metro was fixed by switching back to Private. Docker API required an explicit firewall rule.
