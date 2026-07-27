# Sarflog PIN & Biometric Lock — Full Architecture

> Last updated: 2026-07-26  
> Covers: `use-app-lock.ts`, `use-auth-store.ts`, `pin-store.ts`, `app-lock-overlay.tsx`, `app-lock-provider.tsx`, `lock-screen-content.tsx`, `pin-create-flow.tsx`, `pin-pad.tsx`, `pin-dots.tsx`, `password-verify-screen.tsx`, `settings-screen.tsx`, `client.ts`

---

## 1. Overview

The PIN and biometric system is a **device-local lock layer** that sits between authentication and app content. It uses a Zustand state machine backed by `expo-secure-store` (hardware-backed keystore). The system has three screens and a settings panel, all wired through a full-screen overlay.

### Key design principles

- **PIN is a device credential, not an account credential.** It protects local access to an authenticated session. It is never sent to the server.
- **Biometric is a user preference, not a credential.** It controls whether fingerprint unlock is offered. Enabling it requires explicit user consent.
- **App Lock is a master toggle.** Turning it off suppresses the lock screen but preserves the PIN in storage. Turning it back on resumes immediately.
- **The lock screen is a gate, not a destination.** No account actions (logout, settings) are available on it. The only paths through are correct PIN, biometric, or the cooldown recovery flow.
- **Optimistic UI updates.** All SecureStore writes happen after the in-memory store is updated. If the write fails, the store reverts. The UI never lies.

---

## 2. State Machine

### States

The `useAppLockStore` (Zustand) holds these key state fields:

| Field | Type | Persisted? | Meaning |
|---|---|---|---|
| `isInitialized` | `boolean` | No (in-memory) | Has `initialize()` completed? Reset to `false` on every sign-out path. |
| `pinExists` | `boolean` | No (derived) | Is a PIN hash present in SecureStore? |
| `isLocked` | `boolean` | No | Is the overlay currently locking the app? |
| `isSettingUp` | `boolean` | No | Should the overlay show `PinCreateFlow`? |
| `bioEnabled` | `boolean` | Yes (`sarflog_bio_enabled`) | Did the user consent to fingerprint unlock? |
| `bioAvailable` | `boolean` | No (derived from hardware) | Does the device have biometric hardware + enrolled fingerprints? |
| `appLockEnabled` | `boolean` | Yes (`sarflog_app_lock_enabled`) | Master toggle for the entire lock system. |
| `changePinMode` | `boolean` | No | Is the user changing their PIN from Settings? |
| `failedAttempts` | `number` | No (resets on app kill) | Consecutive wrong PIN count. |
| `cooldownUntil` | `string?` | Yes (`sarflog_pin_cooldown_until`) | ISO timestamp when the 30-min cooldown expires. |
| `cooldownRemaining` | `number` | No | Seconds left (for the countdown timer UI). |
| `passwordVerified` | `boolean` | No | Has the user verified their account password after cooldown? |

### SecureStore Keys

| Key | Type | Default | Purpose |
|---|---|---|---|
| `sarflog_pin_hash` | `string` (SHA-256) | `null` | The hashed 5-digit PIN. |
| `sarflog_pin_cooldown_until` | `string` (ISO) | `null` | When the cooldown expires. |
| `sarflog_bio_enabled` | `"true"` / `"false"` | `null` → treated as `false` | User consent for fingerprint unlock. |
| `sarflog_app_lock_enabled` | `"true"` / `"false"` | `null` → treated as `true` | Master toggle. |

All keys use `SecureStore.WHEN_UNLOCKED` accessibility (only readable when device is unlocked).

---

## 3. Screen Routing

The `AppLockOverlay` is a full-screen absolute-positioned view (z-index 9999) that renders one of four child screens based on the state machine:

```
AppLockOverlay
├── !appLockEnabled && !changePinMode  → null (hidden)
├── !isLocked && !isSettingUp          → null (hidden)
├── changePinMode                      → PinCreateFlow(hideBioOffer)
├── isSettingUp && !cooldown           → PinCreateFlow (normal)
├── needsPasswordVerification          → PasswordVerifyScreen
└── else                               → LockScreenContent
```

`needsPasswordVerification` = `(cooldownExpired || maxAttemptsReached) && !passwordVerified && !pinExists`

### Screen descriptions

**PinCreateFlow** — Two-step wizard. Step 1: enter 5-digit PIN. Step 2: confirm. On match, offers biometric enrollment (unless `hideBioOffer` is true, used for Change PIN from Settings). The `setPin()` call that saves the PIN is deferred until after the user chooses "Later" or "Enable" — the app is never visible behind the prompt.

**LockScreenContent** — Single gate screen. Shows PIN title, dot indicator, error area, and the `PinPad` (number pad). The fingerprint icon sits in the bottom-left slot of the number pad — icon only, no text, no border box. The fingerprint only renders when `bioEnabled && bioAvailable`. Auto-trigger on mount is handled by `AppLockProvider` calling `_onForeground()` after initialization.

**LockScreenContent (cooldown variant)** — When `isInCooldown`, the same component renders a countdown timer instead of the PIN entry UI. A standalone fingerprint button allows biometric bypass during cooldown.

**PasswordVerifyScreen** — After cooldown expires, the user must enter their Sarflog account password. On success, `markPasswordVerified()` routes directly to `PinCreateFlow` (sets `isSettingUp: true`, `isLocked: false`).

---

## 4. Security Flow: 5 Wrong PINs → Recovery

This is the hardened recovery path. It is the **only** way past the lock screen without knowing the PIN.

```
5 wrong PINs
  │
  ├── startCooldown()
  │     ├── deletePinHash()          ← PIN credential destroyed
  │     ├── saveCooldownUntil(now+30) ← persisted to SecureStore
  │     └── set({ pinExists: false, cooldownUntil, cooldownRemaining: 1800 })
  │
  ├── LockScreenContent renders cooldown UI
  │     ├── Countdown timer (mm:ss)
  │     └── Biometric bypass button (if bioEnabled)  ← biometric kills cooldown
  │
  ├── Cooldown expires (30 min)
  │     └── clearCooldown() → cooldownUntil: null
  │
  ├── AppLockOverlay: needsPasswordVerification → PasswordVerifyScreen
  │     └── User enters Sarflog account password
  │           └── POST /auth/verify-password
  │
  └── markPasswordVerified()
        └── set({ passwordVerified: true, isSettingUp: true, isLocked: false })
              └── Overlay routes to PinCreateFlow → new PIN created
```

### Biometric bypass during cooldown

If `bioEnabled` is true, the cooldown screen shows a fingerprint button. On success:

1. `authenticateWithBiometrics()` → `tryUnlock()`:
   - `get().clearCooldown()` — kills the cooldown (biometric = stronger proof than PIN)
   - `get().unlock()` — opens the app

The cooldown is killed because biometric authentication proves the user is the device owner through an inherence factor — something that cannot be guessed or brute-forced. There is no security value in continuing to punish a verified owner for not knowing their PIN.

---

## 5. AppState Lifecycle

```
App goes to background
  └── _onBackground()
        ├── Guard: isInitialized && pinExists && appLockEnabled
        └── set({ isLocked: true, failedAttempts: 0 })

App comes to foreground
  └── _onForeground()
        ├── Guard: isInitialized && pinExists && appLockEnabled
        ├── If bioEnabled && bioAvailable:
        │     └── authenticateWithBiometrics()
        │           ├── Success → unlock()  (isLocked: false, app opens)
        │           └── Fail    → isLocked stays true (lock screen shows)
        └── If !bioSucceeded: set({ isLocked: true })
```

**Important:** `_onForeground` is also called once by `AppLockProvider` after initialization to handle the case where the app launches directly into a locked state (AppState doesn't fire an 'active' event on initial launch).

Only **one** auto-trigger mechanism exists: `_onForeground`. There is no competing `useEffect` in `LockScreenContent`. This prevents race conditions where two `authenticateWithBiometrics()` calls conflict.

---

## 6. Sign-Out & Account Switching

Three paths set `status: 'unauthenticated'`. All three reset `isInitialized: false` so the AppLock store re-initializes from SecureStore on next sign-in.

### Path 1: `signOut()` — Regular sign-out (1 device)

```
signOut()
  ├── clearClientAuth()
  ├── deleteRefreshToken()
  ├── deletePinHash() + deleteCooldownUntil()   ← PIN credential wiped
  ├── AppLock reset: isInitialized=false, pinExists=false, ...
  └── set({ status: 'unauthenticated' })
```

**Keeps:** `sarflog_bio_enabled`, `sarflog_app_lock_enabled` (device preferences)  
**Next sign-in:** `initialize()` finds no PIN → `isSettingUp: true` → `PinCreateFlow` with bio offer

### Path 2: `signOutAll()` — Security action (all devices)

```
signOutAll()
  ├── clearClientAuth()
  ├── deleteRefreshToken()
  ├── deleteAllPinData()   ← PIN + cooldown + bio + appLock all wiped
  ├── AppLock reset: isInitialized=false, pinExists=false, bioEnabled=false, ...
  └── set({ status: 'unauthenticated' })
```

**Wipes everything.**  
**Next sign-in:** clean slate → `PinCreateFlow` with bio offer, `appLockEnabled` defaults to `true`

### Path 3: `setUnauthenticated()` — Token refresh failure (axios interceptor)

```
clearAuthState()  [called from 401 interceptor]
  ├── accessToken = null
  ├── deleteRefreshToken()
  └── setUnauthenticated()
        ├── AppLock: isInitialized = false
        └── set({ status: 'unauthenticated' })
```

**Does NOT delete PIN from SecureStore.** Only resets in-memory state.  
**Next sign-in:** `initialize()` reads SecureStore → finds existing PIN → `pinExists: true` → `LockScreenContent`. The PIN survives transient network/auth issues.

### Deletion policy summary

| Trigger | PIN hash | Cooldown | Bio pref | App Lock toggle |
|---|---|---|---|---|
| `signOut()` | ✅ Deleted | ✅ Deleted | ❌ Kept | ❌ Kept |
| `signOutAll()` | ✅ Deleted | ✅ Deleted | ✅ Deleted | ✅ Deleted |
| `setUnauthenticated()` | ❌ Kept | ❌ Kept | ❌ Kept | ❌ Kept |
| 5 wrong PINs | ✅ Deleted | Set 30min | ❌ Kept | ❌ Kept |
| `toggleAppLock(false)` | ❌ Kept | ❌ Kept | ❌ Kept | ❌ Kept |
| Biometric success during cooldown | (already gone) | ✅ Cleared | ❌ Kept | ❌ Kept |

---

## 7. Settings Screen Dependency Tree

```
App Lock [Toggle]
  │  Reads/writes: sarflog_app_lock_enabled
  │  ON:  resume lock screen (PIN already stored)
  │  OFF: suppress overlay (PIN stays, bio stays)
  │
  ├── WHEN ON:
  │     ├── Unlock with fingerprint [Toggle]  ← functional
  │     │     Reads/writes: sarflog_bio_enabled
  │     │     Optimistic: store updates first, SecureStore second
  │     │
  │     └── Change PIN [Button]               ← visible
  │           Opens PinCreateFlow(hideBioOffer=true)
  │           No biometric suggestion popup
  │
  └── WHEN OFF:
        ├── Unlock with fingerprint [Toggle]  ← grayed, non-interactive
        └── Change PIN [Button]               ← hidden
```

---

## 8. Optimistic SecureStore Pattern

All three toggle functions follow the same pattern to prevent UI-state-from-disk mismatches:

```
1. set({ storeValue: newValue })     ← update UI immediately
2. saveToSecureStore(newValue)        ← persist in background
3. If step 2 fails:                  ← revert on error
     set({ storeValue: oldValue })
```

Functions: `enableBio()`, `disableBio()`, `toggleAppLock()`.

This prevents the bug where a SecureStore write failure causes the toggle in Settings to visually update but the lock screen still shows the old state (because the in-memory store was never updated).

---

## 9. Component Tree

```
RootLayout
└── AuthGuard
    └── AppLockProvider
        ├── AppLockOverlay (z-index: 9999, absolute fill)
        │     ├── PinCreateFlow
        │     │     └── PinDots + PinPad
        │     ├── PasswordVerifyScreen
        │     └── LockScreenContent
        │           ├── PinDots (brand-green filled dots)
        │           └── PinPad (pill-shaped keys, 60px, radius 30, gap 16px)
        │                 └── biometricSlot: Fingerprint icon (bottom-left,
        │                     only when bioEnabled && bioAvailable)
        └── Stack (actual app content)
```

---

## 10. Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| **No logout button on lock screen** | It's a security bypass — a stealer can reach sign-in with one tap, then "Continue with Google" requires zero knowledge. The lock screen is a gate, not a destination. |
| **PIN survives regular sign-out** | The PIN is a device credential, not an account credential. Logging out ends the session but the device is still the same user's device. |
| **Biometric kills cooldown** | Fingerprint = inherence factor (can't be guessed). PIN cooldown = rate-limiter for knowledge factor. After biometric proof, the rate-limiter has no target. |
| **No logout on lock screen means no logout on lock screen means no logout on lock screen** | The cooldown recovery flow is the only path for forgotten PINs. It requires patience (30 min) + knowledge (account password). This is by design. |
| **`_onForeground` is the only auto-trigger** | One mechanism, no races. The `useEffect` in `LockScreenContent` was removed because it competed with `_onForeground` and both calls to `authenticateWithBiometrics()` conflicted. |
| **Optimistic updates for all SecureStore writes** | SecureStore can fail on real devices (keychain locked, low storage). The UI must reflect user intent immediately, revert on failure. |
| **`isInitialized` reset on all sign-out paths** | Prevents stale in-memory state from leaking between accounts. Forces `initialize()` to re-read SecureStore on every sign-in. |
| **Fingerprint icon-only, in number pad** | Matches iOS passcode pattern (no text, no box). The icon is a secondary affordance — primary interaction is PIN entry. |
| **Pill-shaped keys (60px, radius 30)** | Matches iOS passcode standard. Rounded shapes reduce subconscious friction for finance apps (contour bias). |

---

## 11. Test Coverage

33 tests across 3 suites in `src/features/app-lock/__tests__/`:

- **`use-app-lock.test.ts`** — All state machine transitions: initialize, lock/unlock, verifyAndUnlock (correct, wrong, cooldown trigger), biometrics (success, failure, cooldown kill), setPin, enableBio/disableBio, toggleAppLock (on/off), startChangePin/finishChangePin, clearAllPinData, password verification.
- **`pin-dots.test.tsx`** — Accessibility labels, error state rendering.
- **`lock-screen-content.test.tsx`** — PIN entry rendering, biometric visibility (shown when bioEnabled+bioAvailable, hidden when !bioAvailable), cooldown UI, no logout button on lock screen.

Locale parity: all `appLock.*` keys exist in `en`, `ru`, `uz` with zero missing or unexpected keys.

---

## 12. Files Reference

| File | Purpose |
|---|---|
| `src/features/app-lock/hooks/use-app-lock.ts` | Zustand state machine |
| `src/features/auth/hooks/use-auth-store.ts` | Auth store with sign-out/PIN deletion wiring |
| `src/lib/auth/pin-store.ts` | SecureStore CRUD for PIN, cooldown, bio, appLock |
| `src/lib/auth/pin-hash.ts` | SHA-256 hashing + constant-time comparison |
| `src/features/app-lock/components/app-lock-overlay.tsx` | Screen router (overlay) |
| `src/providers/app-lock-provider.tsx` | Lifecycle wiring (init, AppState, auto-trigger) |
| `src/features/app-lock/components/lock-screen-content.tsx` | Lock gate + cooldown UI |
| `src/features/app-lock/components/pin-create-flow.tsx` | Two-step PIN creation wizard |
| `src/features/app-lock/components/pin-pad.tsx` | 3×4 number pad with biometric slot |
| `src/features/app-lock/components/pin-dots.tsx` | 5-dot PIN progress indicator |
| `src/features/app-lock/components/password-verify-screen.tsx` | Post-cooldown account password gate |
| `src/features/settings/screens/settings-screen.tsx` | 3-item dependency tree |
| `src/lib/api/client.ts` | Axios interceptor → token refresh → `setUnauthenticated` |
