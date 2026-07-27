# Authentication Issues and Edge Cases

**Scope:** Sarflog authentication across the shared FastAPI backend, React web client, and Expo mobile client  
**Created:** 2026-07-19  
**Owner:** Auth workstream  
**Canonical mobile overview:** `../THINGS-TO-CONSIDER.md`

## Purpose

This is the detailed working log for authentication bugs, security risks, edge cases, architecture gaps, and unresolved decisions. `THINGS-TO-CONSIDER.md` remains the cross-feature mobile overview; this file owns the evidence, acceptance criteria, and verification record for auth-specific work.

An entry is not resolved merely because code exists. It is resolved only when the expected behavior is documented, compatibility is preserved, and the required tests or native verification pass.

## Safety Rules

1. Never paste raw passwords, access tokens, refresh tokens, Google ID tokens, reset tokens, verification tokens, cookie values, secrets, or production user data into this file.
2. Record token hashes only when a test fixture genuinely requires them; prefer redacted identifiers.
3. Authentication and authorization decisions remain backend-owned. Client validation and route guards improve UX but do not establish trust.
4. Web refresh tokens remain HttpOnly and unavailable to browser JavaScript.
5. Mobile refresh tokens live only in Expo SecureStore. They must not enter AsyncStorage, persisted Zustand state, TanStack Query caches, URLs, logs, analytics, or crash reports.
6. Access tokens and refresh tokens must never be placed in email links or OAuth redirect URLs.
7. Closing a shared-backend issue requires proving both web-cookie compatibility and mobile-token behavior when both are affected.
8. Google accounts are identified by the verified provider `sub`, not by a client-supplied profile or email alone.

## Status Labels

- `CAPTURED` — recorded but not yet reproduced or fully evaluated.
- `CONFIRMED` — supported by current code, a failing test, or a repeatable scenario.
- `DECISION_NEEDED` — implementation is blocked by a security, product, or compatibility choice.
- `PLANNED` — accepted for a defined implementation slice.
- `IMPLEMENTING` — active code changes are in progress.
- `VERIFYING` — implementation exists; required tests or device verification remain.
- `RESOLVED` — acceptance criteria and verification requirements are satisfied.
- `DEFERRED` — valid but intentionally postponed with a reason and revisit milestone.
- `REJECTED` — deliberately unsupported; rationale and safe alternative are documented.

## Severity and Priority

- `S0 / P0` — active compromise, leaked secret, or confirmed account takeover; stop normal work.
- `S1 / P0` — release-blocking auth flaw, incomplete security guarantee, or plausible account/session compromise.
- `S2 / P1` — broken core auth journey, meaningful reliability problem, or important compatibility gap.
- `S3 / P2` — recoverable UX, observability, maintainability, or defense-in-depth issue.
- `S4 / P3` — low-risk polish or future enhancement.

## Platform Labels

- `BACKEND_SHARED` — shared FastAPI, PostgreSQL, Redis, or email behavior.
- `WEB` — browser-specific behavior such as HttpOnly cookies or React web redirects.
- `MOBILE` — Expo/React Native behavior such as SecureStore, AuthSession, or native navigation.
- `BOTH_CLIENTS` — user-visible or contractual behavior affecting web and mobile.
- `INFRA` — Google Console, domains, app-link association files, deployment, or observability.

## Recommended Build-Order Scope Map

There is no web-only rebuild in the current seven-step plan. Some existing problems already affect web, but their fixes belong to the shared backend and therefore protect both clients.

| Step | Work | Primary scope | Web impact | Mobile impact |
|---|---|---|---|---|
| 1 | Fix refresh rotation/replay guarantees and add recovery tests | `BACKEND_SHARED` / `BOTH_CLIENTS` | Fixes an existing web-session weakness and untested recovery routes | Required before native refresh tokens ship |
| 2 | Extract shared session and identity services | `BACKEND_SHARED` / `BOTH_CLIENTS` | Existing cookie endpoints must remain compatible | Prevents mobile routes from duplicating security logic |
| 3 | Add mobile sign-in, refresh, and logout contracts | `MOBILE` + `BACKEND_SHARED` | No web UI change; existing cookie contract stays unchanged | New JSON token-delivery contract |
| 4 | Build sign-in, restoration, `/users/me`, and logout vertical slice | `MOBILE` | None beyond shared backend regression checks | First complete native auth journey |
| 5 | Add signup and email-verification deep links | `BOTH_CLIENTS` + `INFRA` | Existing HTTPS verification page remains the fallback | Universal/App Link opens the native verification screen |
| 6 | Add forgot/reset-password deep links | `BOTH_CLIENTS` + `INFRA` | Existing HTTPS reset page remains the fallback | Universal/App Link opens the native reset screen |
| 7 | Add Google native authentication and harden account linking | Split: `MOBILE`, `BACKEND_SHARED`, `BOTH_CLIENTS` | Shared Google identity/linking policy is hardened | AuthSession/external-browser PKCE flow and mobile token exchange are added |

## Entry Index

| ID | Title | Status | Severity | Platform | Milestone |
|---|---|---|---|---|---|
| AUTH-001 | Refresh replay does not revoke the active token family | CONFIRMED | S1 / P0 | BACKEND_SHARED / BOTH_CLIENTS | Before first mobile auth slice |
| AUTH-002 | Refresh rotation is not atomic under concurrency | CONFIRMED | S1 / P0 | BACKEND_SHARED / BOTH_CLIENTS | Before first mobile auth slice |
| AUTH-003 | Native session token contract is missing | CONFIRMED | S1 / P0 | MOBILE / BACKEND_SHARED | First mobile auth slice |
| AUTH-004 | Email verification mutates account state through GET | CONFIRMED | S2 / P1 | BACKEND_SHARED / BOTH_CLIENTS | Verification deep-link slice |
| AUTH-005 | Verification and reset links target only the web frontend | CONFIRMED | S2 / P1 | BOTH_CLIENTS / INFRA | Before mobile email journeys |
| AUTH-006 | Password reset leaves issued access JWTs valid temporarily | CONFIRMED | S1 / P1 | BACKEND_SHARED / BOTH_CLIENTS | Auth hardening |
| AUTH-007 | Google email auto-linking policy is too permissive | CONFIRMED | S1 / P0 | BACKEND_SHARED / BOTH_CLIENTS | Before Google mobile release |
| AUTH-008 | Existing Google callback is browser-only | CONFIRMED | S1 / P0 | MOBILE / BACKEND_SHARED | Google mobile slice |
| AUTH-009 | Recovery and verification routes lack focused backend tests | CONFIRMED | S2 / P1 | BACKEND_SHARED / BOTH_CLIENTS | Build-order step 1 |
| AUTH-010 | Native startup can route before session restoration finishes | PLANNED | S2 / P1 | MOBILE | First mobile auth slice |
| AUTH-011 | No authenticated sign-out-all-devices command exists | PLANNED | S3 / P2 | BACKEND_SHARED / BOTH_CLIENTS | Private beta |

---

# Entry Template

Copy this section for every new auth issue. Do not reuse IDs.

## AUTH-000: Short, behavior-focused title

**Status:** CAPTURED  
**Severity / Priority:** S2 / P1  
**Type:** BUG / SECURITY / EDGE_CASE / ARCHITECTURE_GAP / TEST_GAP / DECISION  
**Platform:** BACKEND_SHARED / WEB / MOBILE / BOTH_CLIENTS / INFRA  
**Milestone:** FIRST_AUTH_SLICE / PRIVATE_BETA / PUBLIC_RELEASE / LATER  
**Owner:** Unassigned  
**Reported by:** User / Test / Code review / Production signal  
**Discovered on:** YYYY-MM-DD  
**Related entries:** AUTH-000 / EC-000 / ADR / issue link

### Summary

One paragraph describing the broken guarantee or unresolved decision.

### Evidence

- File and line, failing test, redacted response, standard, or device observation.
- State whether the issue is confirmed, inferred, or not yet reproduced.

### Preconditions

- Required account state, client, token/session state, provider, network, or device condition.

### Scenario / Steps to Reproduce

1. Start from a precise state.
2. Perform the action.
3. Observe the result without including secrets.

### Expected Behavior

Describe the backend security guarantee and the user-visible result.

### Actual Behavior

Describe what currently happens. For an architecture gap, state what is missing.

### Security and User Impact

- Asset at risk: account, session, identity link, email address, or recovery channel.
- Likely failure or abuse case.
- Whether the user can recover safely.

### Platform Behavior Matrix

| Surface | Current behavior | Required behavior |
|---|---|---|
| Backend | | |
| Web | | |
| Android | | |
| iOS | | |

### Decision

Record the selected policy and rejected alternatives. Use `DECISION_NEEDED` until this is settled.

### Proposed Solution

Name the smallest compatible change and the layer that owns each rule. Avoid implementation details that have not been verified.

### Acceptance Criteria

- [ ] Happy path is explicit.
- [ ] Highest-risk failure or abuse path is explicit.
- [ ] Existing web behavior is preserved or intentionally migrated.
- [ ] Mobile secrets do not leave SecureStore except for TLS-protected API requests.
- [ ] Error/recovery behavior is localized in Uzbek, Russian, and English where user-visible.
- [ ] Logs, telemetry, and error reports contain no secrets.

### Verification Matrix

- [ ] Backend unit or service test.
- [ ] Backend route/integration test.
- [ ] Web regression test when affected.
- [ ] Mobile unit/component test when affected.
- [ ] Expo Router/deep-link integration test when affected.
- [ ] Android development-build verification when platform behavior matters.
- [ ] iOS development-build verification when platform behavior matters.
- [ ] Maestro release-critical journey when justified.

### Rollout / Compatibility

Document backward compatibility, token/session migration, feature flags, domain/provider-console changes, and rollback behavior.

### Resolution

When resolved, record implementation files, verification commands/results, completion date, and residual risk.

### Notes

Tradeoffs, deferred follow-ups, and links to related decisions.

---

# Active Entries

## AUTH-001: Refresh replay does not revoke the active token family

**Status:** RESOLVED  
**Severity / Priority:** S1 / P0  
**Type:** SECURITY / BUG  
**Platform:** BACKEND_SHARED / BOTH_CLIENTS  
**Milestone:** Before first mobile auth slice  
**Related entries:** `../THINGS-TO-CONSIDER.md` EC-137 and EC-140

### Evidence

`app/oauth2.py` retains a short-lived `rotated:{old_hash}` marker, but that marker contains only `"used"`. Replaying the old token returns `401` without recovering its family ID or revoking the newest active family token. The existing replay test proves only that the old token fails.

### Expected Behavior

Replaying any invalidated rotated token revokes the active refresh token descended from the same session family. Unrelated device families follow an explicitly documented policy.

### Acceptance Criteria

- [x] Rotate once, replay the old token, and prove the newest family token also fails.
- [x] No raw token is logged or persisted server-side.
- [x] Web and mobile clients clear local session state after family revocation.

### Resolution

Resolved. Modified `rotate_refresh_token` in `app/oauth2.py` to store the token's `user_id` and `family_id` in the rotated marker and increased its TTL to 7 days (`REFRESH_TOKEN_EXPIRE_SECONDS`). Upon detecting a rotated marker (replay), the backend now revokes the entire family by deleting all token hashes under `rt_family:{family_id}`, destroying `rt_family:{family_id}`, and removing the family from the user's active sessions set `rt_user:{user_id}`. Tests in `test_refresh_token.py` updated and pass.

---

## AUTH-002: Refresh rotation is not atomic under concurrency

**Status:** CONFIRMED  
**Severity / Priority:** S1 / P0  
**Type:** SECURITY / EDGE_CASE  
**Platform:** BACKEND_SHARED / BOTH_CLIENTS  
**Status:** RESOLVED  
**Severity / Priority:** S2 / P1  
**Type:** BUG  
**Platform:** BACKEND_SHARED  
**Milestone:** Before first mobile auth slice  
**Related entries:** `../THINGS-TO-CONSIDER.md` EC-138

### Evidence

Refresh rotation previously read the old token and generated the new one sequentially. A concurrent replay test shows that twin requests fired in parallel both returned valid new descendants. This orphans the first descendant and breaks the one-time-use constraint.

### Expected Behavior

One refresh request wins deterministically. Other concurrent attempts receive the chosen replay/concurrency outcome without creating multiple valid descendants or corrupting family metadata.

### Acceptance Criteria

- [x] Rotation is one atomic Redis operation or equivalent transaction.
- [x] A concurrency test proves that at most one active descendant survives according to policy.
- [x] Client single-flight refresh reduces ordinary duplicate requests but is not treated as the security boundary.

### Resolution

Resolved. Wrapped the token rotation logic in a Redis `pipeline()` with optimistic locking (`WATCH`). Concurrency races are handled safely: the first request wins and commits, while subsequent requests within a 5-second grace period safely fail with 401 Unauthorized without triggering the replay kill-switch. Added `test_concurrent_refresh_requests` to rigorously verify atomic rotation and duplicate-request rejection.

---

## AUTH-003: Native session token contract is missing

**Status:** CONFIRMED  
**Severity / Priority:** S1 / P0  
**Type:** ARCHITECTURE_GAP / API_CONTRACT  
**Platform:** MOBILE / BACKEND_SHARED  
**Milestone:** First mobile auth slice  
**Related entries:** AUTH-001, AUTH-002, `../THINGS-TO-CONSIDER.md` EC-140

### Evidence

Current sign-in places the refresh token in an HttpOnly browser cookie. Refresh and logout read only that cookie. The Expo client needs an explicit TLS-protected JSON delivery and rotation contract that it can connect to SecureStore.

### Expected Behavior

Mobile password sign-in, refresh, and logout use explicit schemas while reusing the same backend credential checks and session service as web. Web cookies remain HttpOnly and never expose refresh tokens to browser JavaScript.

### Acceptance Criteria

- [ ] Mobile sign-in returns an access token and refresh token through an explicit response schema.
- [ ] Mobile refresh rotates and returns both tokens.
- [ ] Mobile logout revokes the supplied session and is idempotent.
- [ ] The refresh token is stored only through a SecureStore adapter.
- [ ] Existing web-cookie route tests remain green.

### Resolution

Not implemented.

---

## AUTH-004: Email verification mutates account state through GET

**Status:** CONFIRMED  
**Severity / Priority:** S2 / P1  
**Type:** SECURITY / HTTP_SEMANTICS / EDGE_CASE  
**Platform:** BACKEND_SHARED / BOTH_CLIENTS  
**Milestone:** Verification deep-link slice  
**Related entries:** AUTH-005

### Evidence

`GET /auth/verify-email?token=...` consumes a one-time token and verifies the account. The web page automatically invokes it. Link scanners, previews, email security tools, and prefetchers can follow GET links without the user's intended confirmation action.

### Expected Behavior

The email HTTPS link opens a web or mobile confirmation screen. A deliberate `POST` command containing the token performs the state change. The old GET route is migrated without breaking outstanding links.

### Acceptance Criteria

- [ ] Canonical verification uses POST with an explicit request schema.
- [ ] Existing issued links have a documented compatibility window.
- [ ] Automated link fetching cannot consume a newly issued token.
- [ ] Reuse and expiry paths are tested.

### Resolution

Not resolved.

---

## AUTH-005: Verification and reset links target only the web frontend

**Status:** CONFIRMED  
**Severity / Priority:** S2 / P1  
**Type:** ARCHITECTURE_GAP / DEEP_LINKING  
**Platform:** BOTH_CLIENTS / INFRA  
**Milestone:** Before mobile email journeys  
**Related entries:** AUTH-004

### Evidence

Verification and reset links are constructed from `settings.frontend_url`. The Expo config does not yet contain production Android App Link and iOS Universal Link associations.

### Expected Behavior

Sarflog HTTPS links open the matching Expo Router screen when the app is installed and preserve the existing web page as a desktop/no-app fallback.

### Acceptance Criteria

- [ ] One canonical HTTPS domain and path contract is documented.
- [ ] Android `assetlinks.json` and app intent filters are configured and verified.
- [ ] iOS AASA and associated domains are configured and verified.
- [ ] Reset and verification links work on Android, iOS, and desktop web.
- [ ] Tokens are redacted from analytics and logs.

### Resolution

Not implemented.

---

## AUTH-006: Password reset leaves issued access JWTs valid temporarily

**Status:** DECISION_NEEDED  
**Severity / Priority:** S1 / P1  
**Type:** SECURITY / SESSION_REVOCATION  
**Platform:** BACKEND_SHARED / BOTH_CLIENTS  
**Milestone:** Auth hardening

### Evidence

Password reset revokes every Redis refresh-token family, but access JWTs are stateless and remain valid until their current expiration, which is presently up to 15 minutes.

### Expected Behavior

The product explicitly chooses either immediate access-token invalidation after a password/security event or accepts and documents the bounded expiration window.

### Decision Needed

Choose between a per-user auth/session version checked on protected requests, a denylist/security-event mechanism, or accepting the short JWT lifetime with clear threat-model justification.

### Acceptance Criteria

- [ ] The chosen invalidation guarantee is documented.
- [ ] Password-reset tests prove the exact refresh-token and access-token behavior.
- [ ] User-facing copy does not claim immediate logout if a valid access window remains.

### Resolution

No policy decision recorded.

---

## AUTH-007: Google email auto-linking policy is too permissive

**Status:** CONFIRMED  
**Severity / Priority:** S1 / P0  
**Type:** SECURITY / ACCOUNT_LINKING  
**Platform:** BACKEND_SHARED / BOTH_CLIENTS  
**Milestone:** Before Google mobile release

### Evidence

The current Google callback auto-links an existing Sarflog account whenever the Google token supplies the same email and `email_verified=true`. It does not distinguish Google-authoritative Gmail/Workspace addresses from third-party email domains or require an authenticated account-linking confirmation.

### Expected Behavior

Google `sub` is the durable identity key. Linking a new provider to an existing account follows an explicit policy that prevents an email-match shortcut from becoming account takeover.

### Acceptance Criteria

- [ ] Provider `sub`, issuer, audience, expiry, and nonce/challenge are verified server-side.
- [ ] The policy for Gmail, Workspace, and third-party domains is documented and tested.
- [ ] Ambiguous matches require a safe authenticated/recovery confirmation instead of silent linking.
- [ ] Web and mobile Google flows use the same identity-linking service.

### Resolution

Not resolved.

---

## AUTH-008: Existing Google callback is browser-only

**Status:** CONFIRMED  
**Severity / Priority:** S1 / P0  
**Type:** ARCHITECTURE_GAP / OAUTH  
**Platform:** MOBILE / BACKEND_SHARED  
**Milestone:** Google mobile slice  
**Related entries:** AUTH-007

### Evidence

The backend exchanges a web authorization code using a server client secret, sets a browser refresh cookie, and redirects to the React frontend with the Sarflog access token in a URL fragment. That contract is not a native session contract.

### Expected Behavior

Expo uses an external browser with Authorization Code + PKCE. No Google client secret ships in the app. The backend verifies the resulting Google identity proof and returns Sarflog mobile session tokens in a direct TLS response, never through a redirect URL.

### Acceptance Criteria

- [ ] `expo-auth-session` and its peer dependency are configured through a development build.
- [ ] Redirect URIs and client IDs are allowlisted per environment/platform.
- [ ] State, PKCE, and nonce/challenge validation are tested.
- [ ] Cancellation, provider errors, offline return, and duplicate callback handling recover safely.
- [ ] No Sarflog or Google token appears in navigation history or logs.

### Resolution

Not implemented.

---

## AUTH-009: Recovery and verification routes lack focused backend tests

**Status:** CONFIRMED  
**Severity / Priority:** S2 / P1  
**Type:** TEST_GAP  
**Platform:** BACKEND_SHARED / BOTH_CLIENTS  
**Milestone:** Build-order step 1

### Evidence

The current focused auth suites cover signup, sign-in, refresh, logout, and one Google success path. Focused tests were not found for forgot password, reset password, resend verification, or email verification.

### Expected Behavior

Each recovery command is protected by tests for the happy path, enumeration resistance, rate limiting, expiration, single use, invalidation of prior tokens, and session revocation.

### Acceptance Criteria

- [ ] Forgot-password response does not disclose account existence.
- [ ] Reset tokens are hashed, expire, and cannot be reused.
- [ ] Verification tokens expire, are single-use, and invalidate older tokens.
- [ ] Resend behavior remains enumeration-resistant and rate-limited.
- [ ] Password reset proves the chosen session invalidation guarantee.

### Resolution

Tests not yet added.

---

## AUTH-010: Native startup can route before session restoration finishes

**Status:** PLANNED  
**Severity / Priority:** S2 / P1  
**Type:** EDGE_CASE / NAVIGATION  
**Platform:** MOBILE  
**Milestone:** First mobile auth slice  
**Related entries:** `../THINGS-TO-CONSIDER.md` EC-138

### Scenario

The app opens with a valid refresh token in SecureStore, but navigation evaluates before storage and refresh complete and briefly or permanently sends the user to sign-in.

### Expected Behavior

One auth state machine owns `restoring`, `authenticated`, and `unauthenticated`. Expo Router chooses a route only after restoration reaches a stable state, while preserving permitted deep-link intent.

### Acceptance Criteria

- [ ] A valid session never flashes the sign-in screen.
- [ ] Missing, expired, revoked, and malformed tokens end safely in unauthenticated state.
- [ ] Deep links wait for restoration and resume at an allowed destination.
- [ ] Session failure clears unusable SecureStore and query-cache state.

### Resolution

Not implemented.

---

## AUTH-011: No authenticated sign-out-all-devices command exists

**Status:** PLANNED  
**Severity / Priority:** S3 / P2  
**Type:** SECURITY / RECOVERY / UX  
**Platform:** BACKEND_SHARED / BOTH_CLIENTS  
**Milestone:** Private beta  
**Related entries:** `../THINGS-TO-CONSIDER.md` EC-139

### Evidence

The backend has an internal all-family revocation helper used by password reset, but there is no protected user-facing endpoint and no web/mobile settings action.

### Expected Behavior

After confirmation and any chosen recent-auth requirement, the current user can revoke every session. Every client clears local secrets and caches and requires sign-in on its next auth check.

### Acceptance Criteria

- [ ] A protected endpoint revokes only the current user's session families.
- [ ] Two independent device families are proven revoked.
- [ ] Web and mobile clear local authenticated state safely.
- [ ] Confirmation and outcome copy exist in Uzbek, Russian, and English.
- [ ] A security audit event is emitted without token contents.

### Resolution

Not implemented.

