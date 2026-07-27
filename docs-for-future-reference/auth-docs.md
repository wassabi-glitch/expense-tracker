# Authentication: Production & Staging Readiness

> [!IMPORTANT]
> This document serves as a backlog and technical debt register for authentication features that are intentionally deferred during local development but **must** be addressed before launching to staging or production environments.

## Pre-Launch Requirements Checklist

### 1. Mobile Deep Linking for Email Verification
- **Current State:** In development, we use Resend's testing domains/links. When a developer clicks the verification link, it typically opens in a desktop browser or mobile Safari/Chrome, rather than deep-linking back into the actual Expo app (since the device doesn't have verified App Links/Universal Links set up for localhost/dev domains).
- **Production Requirement:** Configure Android App Links (`assetlinks.json`) and iOS Universal Links (`apple-app-site-association`). Ensure that tapping the "Verify Email" button in a real Gmail/Mail app seamlessly redirects the user directly into the native mobile app, completing the verification lifecycle natively rather than stranding them in a mobile browser.
- **Priority:** High (Release Blocker)

### 2. Native Device Attestation (CAPTCHA Replacement)
- **Current State:** To prevent bot sign-ups and sign-ins, the mobile app currently embeds Cloudflare Turnstile inside a React Native `WebView`. While functional for an MVP, this is a technical hack that consumes excessive memory, limits Cloudflare's telemetry (causing higher visible challenge rates), and may draw scrutiny from App Store reviewers.
- **Production Requirement:** Strip out the `TurnstileWebView` from the mobile app. Implement native cryptographic device attestation APIs to prove the request originates from an untampered physical device running our legitimate binary:
  - **iOS:** Apple DeviceCheck / App Attest API
  - **Android:** Google Play Integrity API
- **Priority:** Medium (Required before large-scale public launch or if active botting occurs)

### 3. Opaque Rate Limit Button Disabling
- **Current State:** When a user hits an auth rate limit (Sign In, Sign Up, Forgot/Reset Password), the backend returns a `429` and the UI shows an error message, but the action buttons remain clickable.
- **Production Requirement:** Disable the submit buttons on the client side when a rate limit is hit to prevent spamming. Crucially, the client must **not** display a visible countdown timer or expose the exact reset duration to the user. The client can internally read the `Retry-After` header to know when to silently re-enable the button, but the UI must remain completely opaque about the backend cooldown mechanics to avoid giving attackers an informational advantage.
- **Priority:** Low/Medium (UX Polish and Anti-Abuse)

---

## Template for Future Additions

Copy the template below to document new production requirements:

### [Feature / Debt Name]
- **Current State:** [Describe how it works now in development and why it was built this way]
- **Production Requirement:** [Describe what needs to change for staging/production and the industry standard approach]
- **Priority:** [Low / Medium / High (Release Blocker)]
