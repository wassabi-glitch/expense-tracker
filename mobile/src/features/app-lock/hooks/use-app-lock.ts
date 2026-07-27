import { create } from 'zustand';
import { AppState } from 'react-native';
import * as LocalAuthentication from 'expo-local-authentication';
import { hashPin, verifyPin } from '@/lib/auth/pin-hash';
import {
  savePinHash,
  getPinHash,
  deletePinHash,
  saveCooldownUntil,
  getCooldownUntil,
  deleteCooldownUntil,
  saveBioEnabled,
  getBioEnabled,
  deleteBioEnabled,
  deleteAllPinData,
  saveAppLockEnabled,
  getAppLockEnabled,
} from '@/lib/auth/pin-store';
const COOLDOWN_MINUTES = 30;
const MAX_ATTEMPTS = 5;

/** Module-scoped cooldown timer helper (not exposed on the store). */
function startCooldownTimer(
  get: () => AppLockState,
  set: (partial: Partial<AppLockState>) => void,
) {
  const state = get();
  if (state.cooldownIntervalId) {
    clearInterval(state.cooldownIntervalId);
  }
  const id = setInterval(() => {
    const s = get();
    if (s.cooldownRemaining <= 1) {
      clearInterval(id);
      s.clearCooldown();
      return;
    }
    set({ cooldownRemaining: s.cooldownRemaining - 1 });
  }, 1000);
  set({ cooldownIntervalId: id });
}

export type AppLockState = {
  // Initialization
  isInitialized: boolean;

  // PIN state
  pinExists: boolean;

  // Lock state
  isLocked: boolean;
  isSettingUp: boolean; // true when authenticated but no PIN exists

  // Biometrics
  bioEnabled: boolean;
  bioAvailable: boolean;

  // Attempt tracking (in-memory, resets on app kill)
  failedAttempts: number;

  // Cooldown
  cooldownUntil: string | null; // ISO timestamp in SecureStore
  cooldownRemaining: number; // seconds left (for UI countdown)
  cooldownIntervalId: ReturnType<typeof setInterval> | null;

  // Password verification (after cooldown)
  passwordVerified: boolean;

  // App Lock master toggle (persisted)
  appLockEnabled: boolean;

  // Change PIN mode (triggers PinCreateFlow from settings)
  changePinMode: boolean;

  // Actions
  initialize: () => Promise<void>;
  lock: () => void;
  unlock: () => void;
  verifyAndUnlock: (pin: string) => Promise<{
    success: boolean;
    attemptsLeft: number;
  }>;
  authenticateWithBiometrics: () => Promise<boolean>;
  setPin: (pin: string) => Promise<void>;
  enableBio: () => Promise<void>;
  disableBio: () => Promise<void>;
  toggleAppLock: (enabled: boolean) => Promise<void>;
  startChangePin: () => void;
  finishChangePin: () => void;
  startCooldown: () => Promise<void>;
  clearCooldown: () => Promise<void>;
  tickCooldown: () => void;
  markPasswordVerified: () => void;
  resetAttempts: () => void;
  clearAllPinData: () => Promise<void>;
  setupAppStateListener: () => void;
  _onForeground: () => Promise<void>;
  _onBackground: () => void;
};

export const useAppLockStore = create<AppLockState>((set, get) => ({
  isInitialized: false,
  pinExists: false,
  isLocked: false,
  isSettingUp: false,
  bioEnabled: false,
  bioAvailable: false,
  failedAttempts: 0,
  cooldownUntil: null,
  cooldownRemaining: 0,
  cooldownIntervalId: null,
  passwordVerified: false,
  appLockEnabled: true,
  changePinMode: false,

  // ── Initialization ─────────────────────────────────────────

  initialize: async () => {
    // Check biometric availability
    const [hardware, enrolled] = await Promise.all([
      LocalAuthentication.hasHardwareAsync(),
      LocalAuthentication.isEnrolledAsync(),
    ]);
    const bioAvailable = hardware && enrolled;

    // Load stored state
    const [pinHash, cooldownUntil, bioEnabled, appLockEnabled] = await Promise.all([
      getPinHash(),
      getCooldownUntil(),
      getBioEnabled(),
      getAppLockEnabled(),
    ]);

    const pinExists = pinHash !== null;
    const now = Date.now();

    // Check if cooldown is still active
    let cooldownRemaining = 0;
    if (cooldownUntil) {
      const remaining = new Date(cooldownUntil).getTime() - now;
      cooldownRemaining = Math.max(0, Math.ceil(remaining / 1000));
    }

    // If cooldown expired, clear it
    if (cooldownUntil && cooldownRemaining <= 0) {
      await deleteCooldownUntil();
    }

    const activeCooldown = cooldownRemaining > 0;

    set({
      isInitialized: true,
      pinExists,
      bioEnabled: bioEnabled && bioAvailable,
      bioAvailable,
      appLockEnabled,
      cooldownUntil: activeCooldown ? cooldownUntil : null,
      cooldownRemaining,
      isLocked: pinExists && appLockEnabled, // lock only if PIN exists AND app lock is on
      isSettingUp: !pinExists, // show create PIN if no PIN set
      passwordVerified: false,
      failedAttempts: 0,
    });

    // If cooldown is active, start the countdown timer
    if (activeCooldown) {
      startCooldownTimer(get, set);
    }
  },

  // ── Lock / unlock ──────────────────────────────────────────

  lock: () => {
    set({
      isLocked: true,
      failedAttempts: 0,
    });
  },

  unlock: () => {
    set({
      isLocked: false,
      isSettingUp: false,
      failedAttempts: 0,
      passwordVerified: false,
    });
  },

  // ── PIN verification ───────────────────────────────────────

  verifyAndUnlock: async (pin: string) => {
    const state = get();
    const storedHash = await getPinHash();

    if (!storedHash) {
      // PIN was deleted from SecureStore (cooldown, signOutAll, or
      // account switch). Route the user to create a new PIN instead
      // of leaving them stuck on the lock screen.
      set({ isSettingUp: true, isLocked: false });
      return { success: false, attemptsLeft: 0 };
    }

    const isValid = await verifyPin(pin, storedHash);

    if (isValid) {
      get().unlock();
      return { success: true, attemptsLeft: MAX_ATTEMPTS };
    }

    // Wrong PIN
    const newAttempts = state.failedAttempts + 1;

    if (newAttempts >= MAX_ATTEMPTS) {
      // Max attempts reached — start cooldown
      await get().startCooldown();
      return { success: false, attemptsLeft: 0 };
    }

    set({ failedAttempts: newAttempts });
    return { success: false, attemptsLeft: MAX_ATTEMPTS - newAttempts };
  },

  // ── Biometrics ─────────────────────────────────────────────

  authenticateWithBiometrics: async () => {
    // Try biometric-only first (no device passcode fallback).
    // If the device doesn't support biometric-only auth, fall back
    // to allowing device passcode as a backup.
    const tryUnlock = () => {
      // Biometric is a stronger proof of identity than a 5-digit PIN.
      // If a cooldown was active, kill it — the real owner just proved
      // who they are. There is no security value in continuing to
      // punish a verified user for not knowing their PIN.
      if (get().cooldownUntil) {
        get().clearCooldown();
      }
      get().unlock();
    };

    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Unlock Sarflog',
        disableDeviceFallback: true,
      });

      if (result.success) {
        tryUnlock();
        return true;
      }
      return false;
    } catch {
      // biometric-only not supported on this device —
      // retry with device fallback enabled
      try {
        const result = await LocalAuthentication.authenticateAsync({
          promptMessage: 'Unlock Sarflog',
        });

        if (result.success) {
          tryUnlock();
          return true;
        }
        return false;
      } catch {
        return false;
      }
    }
  },

  // ── PIN management ─────────────────────────────────────────

  setPin: async (pin: string) => {
    const pinHash = await hashPin(pin);
    await savePinHash(pinHash);
    set({
      pinExists: true,
      isSettingUp: false,
      isLocked: false,
      failedAttempts: 0,
    });
  },

  enableBio: async () => {
    // Update store immediately so the UI responds without waiting for
    // SecureStore. If the write fails, revert.
    set({ bioEnabled: true });
    try {
      await saveBioEnabled(true);
    } catch {
      set({ bioEnabled: false });
    }
  },

  disableBio: async () => {
    // Update store immediately so the lock screen hides the fingerprint
    // icon without waiting for SecureStore. If the write fails, revert.
    set({ bioEnabled: false });
    try {
      await deleteBioEnabled();
    } catch {
      set({ bioEnabled: true });
    }
  },

  // ── App Lock master toggle ─────────────────────────────────

  toggleAppLock: async (enabled: boolean) => {
    // Update store immediately so the overlay responds without
    // waiting for SecureStore. Revert if the write fails.
    if (enabled) {
      set({ appLockEnabled: true, isLocked: true });
    } else {
      set({ appLockEnabled: false, isLocked: false, isSettingUp: false });
    }
    try {
      await saveAppLockEnabled(enabled);
    } catch {
      // Revert on failure
      if (enabled) {
        set({ appLockEnabled: false, isLocked: false });
      } else {
        set({ appLockEnabled: true, isLocked: true });
      }
    }
  },

  // ── Change PIN mode ────────────────────────────────────────

  startChangePin: () => {
    set({ changePinMode: true, isSettingUp: true });
  },

  finishChangePin: () => {
    set({ changePinMode: false, isSettingUp: false, isLocked: false });
  },

  // ── Cooldown ───────────────────────────────────────────────

  startCooldown: async () => {
    // Delete the old PIN — user must re-authenticate after cooldown
    await deletePinHash();

    const cooldownUntil = new Date(
      Date.now() + COOLDOWN_MINUTES * 60 * 1000,
    ).toISOString();
    await saveCooldownUntil(cooldownUntil);

    set({
      cooldownUntil,
      cooldownRemaining: COOLDOWN_MINUTES * 60,
      failedAttempts: MAX_ATTEMPTS,
      pinExists: false,
      passwordVerified: false,
    });

    startCooldownTimer(get, set);
  },

  clearCooldown: async () => {
    const state = get();
    if (state.cooldownIntervalId) {
      clearInterval(state.cooldownIntervalId);
    }
    await deleteCooldownUntil();
    set({
      cooldownUntil: null,
      cooldownRemaining: 0,
      cooldownIntervalId: null,
    });
  },

  tickCooldown: () => {
    const state = get();
    if (state.cooldownRemaining <= 1) {
      get().clearCooldown();
      return;
    }
    set({ cooldownRemaining: state.cooldownRemaining - 1 });
  },

  // ── Password verification ──────────────────────────────────

  markPasswordVerified: () => {
    // After cooldown recovery, route directly to create-PIN.
    // Don't stop at the lock screen — the PIN was already deleted.
    set({ passwordVerified: true, isSettingUp: true, isLocked: false });
  },

  // ── Attempt management ─────────────────────────────────────

  resetAttempts: () => {
    set({ failedAttempts: 0 });
  },

  // ── Cleanup ────────────────────────────────────────────────

  clearAllPinData: async () => {
    const state = get();
    if (state.cooldownIntervalId) {
      clearInterval(state.cooldownIntervalId);
    }
    await deleteAllPinData();
    set({
      pinExists: false,
      isSettingUp: true,
      isLocked: false,
      failedAttempts: 0,
      cooldownUntil: null,
      cooldownRemaining: 0,
      cooldownIntervalId: null,
      bioEnabled: false,
      passwordVerified: false,
      appLockEnabled: true,
      changePinMode: false,
    });
  },

  // ── AppState listener ──────────────────────────────────────

  setupAppStateListener: () => {
    const handleChange = (nextState: string) => {
      if (nextState === 'background' || nextState === 'inactive') {
        get()._onBackground();
      } else if (nextState === 'active') {
        get()._onForeground();
      }
    };

    AppState.addEventListener('change', handleChange);
  },

  _onForeground: async () => {
    const state = get();
    if (!state.isInitialized || !state.pinExists || !state.appLockEnabled) return;

    // If biometric is enabled, attempt auto-unlock
    let bioSucceeded = false;
    if (state.bioEnabled && state.bioAvailable) {
      bioSucceeded = await get().authenticateWithBiometrics();
      // If biometric succeeded, unlock() was called — we're unlocked.
      // If it failed, stay locked and show UI.
    }

    // Only re-lock if biometric didn't succeed
    if (!bioSucceeded) {
      set({ isLocked: true });
    }
  },

  _onBackground: () => {
    const state = get();
    if (!state.isInitialized || !state.pinExists || !state.appLockEnabled) return;
    // Lock immediately when going to background
    set({
      isLocked: true,
      failedAttempts: 0,
    });
  },
}));
