# Signup Security & Architecture Tightening

This document outlines the security mechanisms, architectural decisions, and production-ready improvements for the signup module, as discussed during the system design review.

## 1. Rate Limiting Strategy

**Current Implementation (Good)**
*   **Algorithm:** Sliding Window Counter
*   **Limit:** 5 signups per 60 seconds, per IP address (`check_and_consume("signup", client_ip)`).
*   **Proof/Fact:** The sliding window interpolates the previous minute's weight, which prevents sudden bursts of traffic at the top of the minute (unlike a fixed window algorithm). It also fails open gracefully if Redis crashes, preventing a total system outage.

**Production Tightening Needed (Load Shedding)**
*   **Issue:** IP limits do not stop botnets using thousands of residential proxies. If a distributed attack occurs, the Postgres database could still be overwhelmed by thousands of unique IPs.
*   **Solution:** Implement a **Global Token Bucket** rate limit (`consume_token_bucket("signup_global", "global")`) set to something like 100 signups per minute globally. This acts as an absolute ceiling, shedding excess load to protect the database from melting down during an attack.

---

## 2. CAPTCHA Implementation

**Current Status:** Not implemented.

**Production Tightening Needed**
*   **Solution:** Cloudflare Turnstile (Invisible Mode).
*   **How it Works:** The frontend/mobile app renders a hidden Cloudflare widget. When the user taps "Sign Up", it silently analyzes device/network behavior and generates a secure token. The backend verifies this token with Cloudflare before touching the database.
*   **Failure Flow:** If Cloudflare is mildly suspicious, it dynamically pops up a "Verify you are human" checkbox. If it is certain it's a bot (or the check fails), the backend rejects the request with a `403 Forbidden` (e.g., `auth.captcha_failed`), and the mobile app displays: *"Security check failed. Please try again."*
*   **Developer Loop Fact:** CAPTCHA must be disabled in localhost via environment variables (e.g., `REQUIRE_CAPTCHA=false`) or by using Cloudflare's "always pass" dummy testing keys. This ensures local development and automated E2E tests (like Playwright) are not blocked.

---

## 3. Endpoint-Level Idempotency

**Current Status:** Handled well for email dispatch (using the raw token as the idempotency key for Resend), but missing for the signup HTTP endpoint itself.

**Production Tightening Needed**
*   **Issue:** Mobile networks are unreliable. If a user's network drops exactly after the database commits their account but before the `201 Created` response reaches their phone, the mobile app will automatically retry the request. Currently, this retry results in a confusing `409 Username already taken` error for the user.
*   **Solution:** The mobile client must generate an `Idempotency-Key` (UUID) header for the `POST /users/sign-up` request. The backend checks Redis. If that key was already processed successfully recently, the backend intercepts the request and instantly returns the cached `201 Created` response without touching the DB again.

---

## 4. Race Condition Handling

**Current Implementation (Excellent)**
*   **What is it?** A race condition happens when two identical requests hit the server at the exact same millisecond. Both check if the username exists, both see it is empty, and both try to insert it.
*   **How we handle it:** The system relies on the Postgres Database as the ultimate referee. Postgres enforces a `UNIQUE` constraint on the `username` and `email` columns.
*   **Proof/Fact:** In `app/routers/users.py`, the database insert is wrapped in a `try...except IntegrityError` block. When the second racing request tries to insert, Postgres throws an error, which the backend catches safely to return a `409 Conflict` instead of crashing with a `500 Internal Server Error`. No further tightening needed here.

---

## 5. Disposable Email Blocking

**Current Status:** Not implemented.

**Production Tightening Needed**
*   **Issue:** Fraudsters and automated scripts often use disposable email services (like `mailinator.com` or `10minutemail.com`) to create thousands of junk accounts, which inflates database size and analytics.
*   **Solution:** Integrate a static blocklist of known disposable domains, or use an API like ZeroBounce, to reject disposable emails at the endpoint level before they are processed by the database.

---

## 6. Email Verification Tightening

**Current Status:** Basic token checking and `is_verified` flagging is implemented.

**Production Tightening Needed**
*   **Rate Limiting:** `POST /auth/resend-verification` correctly uses the Sliding Window limit (`client_ip | email`). However, `POST /auth/verify-email` is missing IP-based rate limiting to prevent DoS attacks and token brute-forcing. **Solution:** Apply a global/IP sliding window limit of 5 requests per minute to `/auth/verify-email`.
*   **CAPTCHA:** **Not Recommended.** For resend, the rate limit acts as sufficient protection without adding friction. For verification clicks, the 48-byte URL-safe token has 256 bits of entropy and cannot be brute-forced. Asking a user to solve a CAPTCHA after clicking a link from their email ruins the onboarding UX.
*   **Idempotency & Race Conditions (Scanner Problem):** Currently, clicking the verification link twice yields a `400 Bad Request: Invalid or Expired Token`. Corporate email scanners (e.g., Microsoft Safe Links) often "click" links automatically to check for phishing before the user sees the email. When the user clicks the link seconds later, they receive an error. **Solution:** Make `verify-email` idempotent. If the token `used_at` is populated, check if the user is already `is_verified == True`. If yes, return `200 OK` (Already Verified) rather than a confusing error.
*   **Testing & Translations:** The backend error messages (e.g., `auth.verify_email_token_invalid_or_expired`) are translated in the frontend, but mobile Jest tests need to explicitly test the i18n mapping fallback logic to ensure robustness across languages.
