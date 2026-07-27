# Mobile Things to Consider

## Purpose

This file captures mobile-specific risks, decisions, edge cases, architectural constraints, testing obligations, and ideas that must not be lost between implementation sessions.

It complements the repository-level `docs/EDGE_CASES_AND_BUGS.md`. Entries imported from that file keep their original `EC-*` identifiers for traceability, but their mobile impact, decision point, acceptance criteria, and required tests are made explicit here.

## Working Rule

Do not leave an important mobile concern only in chat, memory, or an unfinished code comment. Capture it here, classify it, connect it to a milestone, and record the eventual decision.

An entry is not complete merely because code exists. Security-sensitive and user-visible entries become complete only after the required automated tests pass and the resolution is recorded.

---

## Status Labels

- `CAPTURED` — recorded but not yet evaluated.
- `RESEARCHING` — facts or platform behavior are still being verified.
- `BLOCKING` — must be resolved before the named milestone can proceed safely.
- `PLANNED` — accepted and assigned to a future implementation slice.
- `DECIDED` — architecture/product decision is recorded; implementation may remain.
- `IMPLEMENTING` — active work is in progress.
- `VERIFYING` — implementation exists but required tests or native verification remain.
- `VERIFIED` — implemented and covered by the required verification.
- `DEFERRED` — valid, intentionally postponed with a stated reason.
- `REJECTED` — intentionally not supported; rationale must be recorded.

## Priority Labels

- `P0` — security, financial truth, data loss, or release-blocking architecture.
- `P1` — blocks a core user journey or creates a high-probability broken experience.
- `P2` — important correctness, maintainability, accessibility, or product-quality concern.
- `P3` — useful improvement or later product capability.

## Type Labels

- `SECURITY`
- `AUTH`
- `API_CONTRACT`
- `ARCHITECTURE`
- `STATE`
- `LOCALIZATION`
- `ACCESSIBILITY`
- `TESTING`
- `NAVIGATION`
- `UX`
- `PERFORMANCE`
- `OPERATIONS`
- `PRODUCT_IDEA`

## Milestone Labels

- `FOUNDATION`
- `FIRST_AUTH_SLICE`
- `FIRST_FINANCIAL_SLICE`
- `PRIVATE_BETA`
- `PUBLIC_RELEASE`
- `LATER`

---

## Mobile Foundation Invariants

These rules should be treated as acceptance criteria across features:

1. Authentication secrets live in Expo SecureStore, never AsyncStorage, Zustand, logs, or query caches.
2. FastAPI records belong to TanStack Query. Zustand is reserved for concrete cross-screen client-only state.
3. Every API request sends the effective `X-Timezone`; user-facing date defaults and validation use that same timezone.
4. Startup navigation distinguishes `restoring`, `authenticated`, and `unauthenticated`; the app must not guess before token restoration finishes.
5. Uzbek, Russian, and English are implemented together. A feature with missing supported-language copy is not complete.
6. Visible copy, accessibility labels, hints, errors, empty states, notifications, and announcements use the same translation system.
7. English fallback is a recovery mechanism, not permission to merge missing Uzbek or Russian keys.
8. A product slice is not complete until its happy path and highest-risk failure path have automated coverage.
9. Financial calculations and authorization remain backend-owned. Mobile validation improves recovery but never replaces server validation.
10. Native behavior must be verified on both Android and iOS before public release when platform behavior can differ.
11. Compact phone-sized windows stay portrait; tablets and unfolded large screens must support rotation and responsive resizing.
12. Shared mobile window classes come from `src/layout/window-size.ts`; feature screens must not invent unnamed width or height breakpoints.

## Localization Definition of Done

For every user-visible mobile change:

- [ ] Translation keys are added to Uzbek, Russian, and English in the same change.
- [ ] The three locale files have identical key structures.
- [ ] No user-visible string is hard-coded in a screen, component, validation message, accessibility prop, notification, or toast.
- [ ] Interpolation and plural forms are used instead of assembling translated sentences from fragments.
- [ ] The selected language persists through AsyncStorage and is restored before the first stable screen renders.
- [ ] Device locale is used only as the initial default when the user has not selected a language.
- [ ] Dates, currency, and numbers use formatting associated with the selected language and effective user timezone.
- [ ] At least one test renders or exercises the changed behavior in a non-English language when layout or logic can differ.
- [ ] Each feature imports its real Uzbek, Russian, and English resources into the shared locale-parity contract test; CI rejects missing or unexpected keys.

## Testing Definition of Done

Choose the cheapest test that proves behavior at the correct boundary:

1. **Unit tests (Jest):** schemas, formatters, state transitions, query-key builders, error normalization, and timezone helpers.
2. **Component tests (React Native Testing Library):** forms, validation, loading/error/empty states, accessibility roles, and user interactions.
3. **Route integration tests (`expo-router/testing-library`):** auth guards, redirects, deep links, and navigation after mutations.
4. **API/query integration tests:** Axios client behavior, auth headers, `X-Timezone`, refresh handling, retries, cache invalidation, and backend error mapping. Use the installed MSW server; unhandled requests fail instead of contacting a real backend.
5. **Native E2E tests (Maestro):** a small set of release-critical journeys on EAS Android/iOS test builds, beginning with signup/verification, sign in, session restoration, language switching, and one financial write flow.

Testing rules:

- [ ] Test user-observable behavior rather than component internals.
- [ ] Include the happy path and highest-risk failure path in the same product slice.
- [ ] Do not rely on snapshots as the only proof of forms, money behavior, navigation, or translations.
- [ ] Reset query caches, stores, timers, and mocks between tests to prevent order dependence.
- [ ] Keep Expo Router tests outside `src/app`; files inside that directory are routes.
- [ ] A regression fix starts with or includes a test that fails without the fix.
- [ ] Flaky tests are defects. Quarantine requires an owner, reason, and removal condition.
- [ ] `npm run verify` passes locally and in GitHub CI: Expo dependency validation, TypeScript, lint, layout policy, Jest integration tests, and the coverage ratchet.
- [ ] The EAS Android and iOS Maestro workflow covers every release-critical journey introduced by the slice.
- [ ] No `.only`, skipped/disabled, or commented-out tests are committed; the test lint configuration enforces this rule.

---

# Entry Template

## MTC-000: Short title

**Status:** CAPTURED  
**Priority:** P2  
**Type:** ARCHITECTURE / UX / TESTING / ...  
**Milestone:** FOUNDATION / FIRST_AUTH_SLICE / ...  
**Area:** Auth / API / Navigation / Localization / ...  
**Source:** User / Agent / Test / `EC-*`  
**Captured on:** YYYY-MM-DD  

### Context

What fact, assumption, platform constraint, or existing behavior triggered this entry?

### Mobile Scenario

Describe the real user or system situation on Android/iOS.

### Risk / Why It Matters

State the concrete security, correctness, accessibility, maintenance, or UX consequence.

### Decision Needed

Write the unresolved decision as a question. If already decided, record the decision and rationale.

### Recommended Direction

Describe the smallest maintainable direction without pretending unresolved details are settled.

### Acceptance Criteria

- [ ] Observable outcome.
- [ ] Failure/recovery outcome.
- [ ] Platform or language requirement.

### Tests Required

- [ ] Unit test.
- [ ] Component or route integration test.
- [ ] Backend/API integration test.
- [ ] Native E2E test, if release-critical.

### Dependencies / Related Entries

- Related module, endpoint, ADR, PRD, or consideration.

### Resolution

Record the actual implementation, verification commands, and final decision when complete.

### Notes

Tradeoffs, rejected alternatives, and future follow-ups.

---

# Imported Authentication Considerations

## EC-137: Replay Attack Token Rotation Bug

**Status:** BLOCKING  
**Priority:** P0  
**Type:** SECURITY / AUTH  
**Milestone:** FIRST_AUTH_SLICE  
**Area:** Backend token rotation / Redis token families / Mobile session security  
**Source:** `docs/EDGE_CASES_AND_BUGS.md` EC-137  
**Source status:** NEEDS_FIX  
**Discovered on:** 2026-06-11  
**Imported on:** 2026-07-18  

### Context

The backend detects reuse of a rotated refresh token and returns `401`, but the source entry reports that the newly rotated token family is not fully revoked.

### Mobile Scenario

A mobile refresh token can remain valid for a long time in the device keychain/keystore. If an attacker replays an older family token while another party holds the newly rotated token, detecting only the reused token does not end the compromised session.

### Risk / Why It Matters

The system appears to detect a replay attack while leaving the useful attacker session alive. Mobile token delivery must not ship on top of an incomplete family-revocation guarantee.

### Decision Needed

How will token-family identity remain available at replay-detection time so the backend can revoke the whole family atomically and consistently?

### Recommended Direction

Resolve and regression-test family revocation before enabling mobile refresh-token delivery. Store enough non-secret rotation metadata to identify the family, revoke every active refresh token and marker in that family, and record a security event without logging raw tokens.

### Acceptance Criteria

- [ ] Reusing a rotated refresh token returns `401`.
- [ ] The newest refresh token in the same family also fails after replay detection.
- [ ] Unrelated token families for the user follow the explicitly chosen security policy.
- [ ] No raw access or refresh token is written to application logs.
- [ ] Concurrent refresh/replay behavior has a deterministic result.

### Tests Required

- [ ] Backend integration test: rotate once, replay the old token, then prove the new token is revoked.
- [ ] Backend concurrency test for simultaneous refresh attempts.
- [ ] Mobile auth test proving family-revoked responses clear SecureStore, query cache, and authenticated navigation state.

### Dependencies / Related Entries

- `app/oauth2.py`
- Redis token-family storage
- EC-140 mobile refresh-token delivery

### Resolution

Not yet resolved in this mobile log.

---

## EC-138: Root Route Must Not Override Restored Authentication

**Status:** PLANNED  
**Priority:** P1  
**Type:** AUTH / NAVIGATION / UX  
**Milestone:** FIRST_AUTH_SLICE  
**Area:** Startup auth restoration / Expo Router guards  
**Source:** `docs/EDGE_CASES_AND_BUGS.md` EC-138  
**Source status:** NEEDS_FIX for the web route  
**Discovered on:** 2026-06-11  
**Imported on:** 2026-07-18  

### Context

The web app can redirect `/` to sign-in before silent refresh finishes. The native app does not share that exact route implementation, but it can reproduce the same bug if navigation renders before SecureStore restoration and refresh resolution complete.

### Mobile Scenario

A returning user opens Sarflog with a valid stored session. The app briefly or permanently shows sign-in because the route guard treats “not restored yet” as “logged out.”

### Risk / Why It Matters

Users lose trust in session persistence, can see an avoidable authentication-screen flash, and may submit duplicate sign-in attempts while a valid session is being restored.

### Decision Needed

What single auth state machine owns startup restoration and when is Expo Router allowed to choose authenticated versus unauthenticated routes?

### Recommended Direction

Model at least `restoring`, `authenticated`, and `unauthenticated`. Keep the splash/loading boundary active during restoration. Route only after the state becomes stable, and make sign-in routes redirect authenticated users away.

### Acceptance Criteria

- [ ] A valid stored session opens the authenticated landing screen without showing sign-in.
- [ ] Missing, invalid, or revoked credentials end in the unauthenticated route group.
- [ ] Restoration failure clears unusable secrets and exposes a recoverable state.
- [ ] Deep links wait for restoration and then preserve their allowed destination.
- [ ] Sign-in cannot remain visible after authentication succeeds.

### Tests Required

- [ ] Auth-state unit tests for every restoration transition.
- [ ] Expo Router integration tests for valid, missing, expired, and revoked sessions.
- [ ] Maestro journey: close and reopen the app with an existing valid session.

### Dependencies / Related Entries

- Expo SecureStore token adapter
- Query cache lifecycle
- EC-137 replay response handling
- EC-140 mobile auth contract

### Resolution

Not yet implemented.

---

## EC-139: Sign Out of All Devices

**Status:** PLANNED  
**Priority:** P2  
**Type:** SECURITY / AUTH / UX  
**Milestone:** PRIVATE_BETA  
**Area:** Backend auth API / Mobile settings / Session cleanup  
**Source:** `docs/EDGE_CASES_AND_BUGS.md` EC-139  
**Source status:** ARCHITECTED; API/UI wiring needed  
**Discovered on:** 2026-06-11  
**Imported on:** 2026-07-18  

### Context

The backend already has `oauth2.revoke_all_user_tokens(user.id)` for password-reset flows, but the source entry reports no dedicated authenticated endpoint or settings action.

### Mobile Scenario

A user loses a phone, signs in on a shared device, or suspects account compromise and wants one action that ends every session, including the current mobile session.

### Risk / Why It Matters

Without a discoverable global sign-out action, a user cannot confidently recover from device loss or session exposure.

### Decision Needed

What confirmation, recent-authentication requirement, audit event, and response contract should surround global token-family revocation?

### Recommended Direction

Expose a protected `POST /auth/logout-all-devices` command that invokes the existing revocation primitive. After success, mobile must clear SecureStore, TanStack Query caches, and session-scoped Zustand state before returning to the unauthenticated route group.

### Acceptance Criteria

- [ ] The endpoint revokes all refresh-token families owned by the current user.
- [ ] The current device clears local authenticated state only after a defined success/recovery outcome.
- [ ] Other devices fail on their next refresh and return safely to sign-in.
- [ ] The destructive action has localized confirmation and outcome copy in all three languages.
- [ ] The backend emits an audit/security event without token contents.

### Tests Required

- [ ] Backend authorization and cross-user tests.
- [ ] Backend test proving two independent device families are both revoked.
- [ ] Mobile component test for confirmation, pending, success, and error states.
- [ ] Mobile integration test proving local secrets and caches are cleared.
- [ ] Maestro two-session journey when test infrastructure supports it.

### Dependencies / Related Entries

- Existing `oauth2.revoke_all_user_tokens`
- Mobile settings screen
- EC-137 token-family guarantees

### Resolution

Not yet implemented.

---

## EC-140: Mobile App Authentication Adapters

**Status:** BLOCKING  
**Priority:** P0  
**Type:** AUTH / API_CONTRACT / ARCHITECTURE  
**Milestone:** FIRST_AUTH_SLICE  
**Area:** Sign-in / Refresh / SecureStore / Native Google authentication  
**Source:** `docs/EDGE_CASES_AND_BUGS.md` EC-140  
**Source status:** DEFERRED in the original roadmap; active now that mobile implementation is beginning  
**Discovered on:** 2026-06-11  
**Imported on:** 2026-07-18  

### Context

The current web authentication flow relies on HttpOnly refresh cookies and browser redirects. Native Android/iOS clients need an explicit token-delivery and OAuth contract.

### Mobile Scenario

Sarflog signs in through the native app, stores a refresh credential in iOS Keychain or Android Keystore, rotates it through the API, restores the session after restart, and eventually accepts a native Google identity token without depending on a desktop-style redirect flow.

### Risk / Why It Matters

Treating native auth as a small Axios variation can leak tokens, create incompatible refresh behavior, duplicate auth state, or ship a Google flow that is not verifiable by the backend.

### Decision Needed

1. Should mobile use explicit mobile auth endpoints or a rigorously validated client-mode contract on shared endpoints?
2. What exact JSON schema delivers and rotates the mobile refresh token?
3. Which native Google integration will be used, and how will nonce, issuer, audience, email verification, and account linking be validated server-side?
4. How are token migration, logout, logout-all, device loss, and replay handled?

### Recommended Direction

Define the mobile auth contract before building the login screen. Return mobile refresh tokens only over TLS in an explicit response schema, store them only in Expo SecureStore, keep access tokens in memory where practical, serialize refresh attempts, and make replay/family revocation authoritative on the backend.

For Google authentication, accept a native Google ID token on a dedicated backend command and verify it server-side. Do not trust profile claims merely because the mobile SDK returned them.

### Acceptance Criteria

- [ ] Mobile sign-in and refresh response schemas are explicit and documented.
- [ ] Web cookie behavior remains backward-compatible and does not expose refresh tokens to browser JavaScript.
- [ ] Mobile refresh credentials are stored only through the SecureStore adapter.
- [ ] Concurrent `401` responses trigger one refresh operation rather than a refresh storm.
- [ ] Refresh rotation updates SecureStore atomically from the mobile client's perspective.
- [ ] Logout and revocation clear secrets, query caches, and session-scoped Zustand state.
- [ ] Google tokens are verified server-side for issuer, audience, expiry, nonce where applicable, and verified email/account-linking policy.
- [ ] Every auth and error message is available in Uzbek, Russian, and English.

### Tests Required

- [ ] Backend API tests for web-cookie and mobile-JSON contracts.
- [ ] Backend tests for invalid client mode, expired/replayed refresh tokens, and invalid Google tokens.
- [ ] SecureStore adapter unit tests with native calls mocked through Jest/jest-expo.
- [ ] Axios/query integration tests for token attachment, timezone header, single-flight refresh, retry, and logout.
- [ ] Expo Router integration tests for sign-in, restoration, expiration, and revocation navigation.
- [ ] Maestro journeys for password sign-in, restart restoration, logout, and later native Google sign-in.

### Dependencies / Related Entries

- EC-137 replay family revocation
- EC-138 startup auth routing
- EC-139 sign out of all devices
- Expo SecureStore
- Axios client and TanStack Query lifecycle
- Backend Google identity validation

### Resolution

Not yet implemented. This entry is now a foundation blocker rather than a distant mobile-launch note.
