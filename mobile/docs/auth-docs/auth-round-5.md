# Round 5: Session Control, Security Settings, and Release Hardening

**Status:** Planned
**Target:** Finalizing the Authentication Epic for V1 Release

## Mission
To finalize the authentication system by giving users total control over their active sessions, allowing them to change their credentials securely, protecting the app interface via local device biometrics, and proving the stability of the entire auth flow through rigorous end-to-end testing.

---

## 1. Backend Specifications (FastAPI & Redis)

### 1.1 Change Password Endpoint
- **Route:** `POST /auth/change-password`
- **Behavior:** 
  - Requires the user to be authenticated (Requires a valid Access JWT).
  - Accepts `current_password` and `new_password`.
  - Verifies the `current_password` against the hashed password in the database.
  - Hashes and updates the user's password to `new_password`.
  - *Crucially:* Automatically invokes the "Logout of all devices" logic to revoke all *other* active sessions, forcing any other devices to log back in with the new password.

### 1.2 Logout of All Devices Endpoint
- **Route:** `POST /auth/logout-all`
- **Behavior:**
  - Requires the user to be authenticated.
  - Queries Redis for all active refresh token families associated with the user's ID.
  - Deletes/blacklists all matching refresh token families from Redis.
  - This guarantees that no device (except potentially the one initiating the request, depending on UX decisions) can mint a new access token.

### 1.3 Redacted Security Auditing
- **Behavior:**
  - All critical auth endpoints (`/auth/change-password`, `/auth/logout-all`, `/auth/reset-password`) must log the event.
  - **Strict rule:** No passwords, raw tokens, or sensitive secrets may be logged. Only the User ID, action taken, and timestamp.

---

## 2. Frontend Specifications (Mobile Expo App)

### 2.1 Security Settings Screen
- **Location:** A new screen within the authenticated `(tabs)` or `(app)` group.
- **Components:**
  - A form to **Change Password** (inputs for Current Password, New Password, Confirm New Password).
  - A high-contrast, destructive button to **"Logout of all devices"** (with an alert confirmation dialog).
  - A toggle switch for **"App Lock (Biometrics/PIN)"**.

### 2.2 Biometric App Lock (expo-local-authentication)
- **Library:** `expo-local-authentication` and `expo-app-state`.
- **Behavior:**
  - If the user has toggled "App Lock" to ON:
    - Whenever the app mounts (starts up) or transitions from the background to the foreground (using React Native's `AppState`), it triggers a full-screen overlay that obscures financial data.
    - It prompts the iOS/Android OS to authenticate the user via FaceID, TouchID, or PIN.
    - Financial data is only revealed once `expo-local-authentication` returns a success signal.

### 2.3 Comprehensive Client Cleanup
- **Behavior:**
  - When a user logs out (or uses "Logout of all devices"), the client must reliably destroy all local traces of the session.
  - **Steps:**
    1. Call the backend logout route.
    2. Delete the Refresh Token from `Expo SecureStore`.
    3. Clear the React Query cache entirely (so the next user cannot press the back button to view cached financial data).
    4. Reset the `useAuthStore` global state.
    5. Navigate back to the `(auth)/sign-in` screen.

---

## 3. Release Hardening & Testing Specifications

### 3.1 E2E Testing (Maestro)
- Write explicit Maestro `.yaml` flows for the new Security Settings:
  - `auth-change-password.yaml`: Logs in, changes password, verifies success.
  - `auth-logout-all.yaml`: Verifies that clicking logout everywhere successfully kicks the user to the sign-in screen.
  
### 3.2 Localization Parity
- Ensure all new strings (Change Password, Biometric prompts, Logout everywhere, error messages) are fully translated in:
  - `en` (English)
  - `ru` (Russian)
  - `uz` (Uzbek)

## Definition of Done for Round 5
- [ ] A user can change their password securely by verifying their old one.
- [ ] A user can revoke all active sessions across all devices via Redis.
- [ ] A user can protect the app foreground with FaceID/TouchID/PIN.
- [ ] Logging out leaves zero financial data in the React Query cache or SecureStore.
- [ ] Maestro E2E tests pass for the new security features.
- [ ] All new UI strings are translated in 3 languages.
