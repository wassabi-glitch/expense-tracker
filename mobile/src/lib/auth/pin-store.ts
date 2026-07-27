import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const PIN_HASH_KEY = 'sarflog_pin_hash';
const COOLDOWN_KEY = 'sarflog_pin_cooldown_until';
const BIO_ENABLED_KEY = 'sarflog_bio_enabled';
const APP_LOCK_ENABLED_KEY = 'sarflog_app_lock_enabled';

const secureStoreOptions: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.WHEN_UNLOCKED,
};

// ── PIN hash ──────────────────────────────────────────────────────

export async function savePinHash(hash: string): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.setItemAsync(PIN_HASH_KEY, hash, secureStoreOptions);
}

export async function getPinHash(): Promise<string | null> {
  if (Platform.OS === 'web') return null;
  return await SecureStore.getItemAsync(PIN_HASH_KEY, secureStoreOptions);
}

export async function deletePinHash(): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.deleteItemAsync(PIN_HASH_KEY, secureStoreOptions);
}

// ── Cooldown timestamp (ISO string, null when no active cooldown) ─

export async function saveCooldownUntil(iso: string): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.setItemAsync(COOLDOWN_KEY, iso, secureStoreOptions);
}

export async function getCooldownUntil(): Promise<string | null> {
  if (Platform.OS === 'web') return null;
  return await SecureStore.getItemAsync(COOLDOWN_KEY, secureStoreOptions);
}

export async function deleteCooldownUntil(): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.deleteItemAsync(COOLDOWN_KEY, secureStoreOptions);
}

// ── Biometric enabled flag ────────────────────────────────────────

export async function saveBioEnabled(enabled: boolean): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.setItemAsync(BIO_ENABLED_KEY, String(enabled), secureStoreOptions);
}

export async function getBioEnabled(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  const val = await SecureStore.getItemAsync(BIO_ENABLED_KEY, secureStoreOptions);
  return val === 'true';
}

export async function deleteBioEnabled(): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.deleteItemAsync(BIO_ENABLED_KEY, secureStoreOptions);
}

// ── Bulk cleanup (called on sign-out-all / forgot PIN) ────────────────

export async function deleteAllPinData(): Promise<void> {
  await Promise.all([
    deletePinHash(),
    deleteCooldownUntil(),
    deleteBioEnabled(),
    deleteAppLockEnabled(),
  ]);
}

// ── App Lock master toggle ─────────────────────────────────────────────

export async function saveAppLockEnabled(enabled: boolean): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.setItemAsync(APP_LOCK_ENABLED_KEY, String(enabled), secureStoreOptions);
}

export async function getAppLockEnabled(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  const val = await SecureStore.getItemAsync(APP_LOCK_ENABLED_KEY, secureStoreOptions);
  // Default to enabled when no stored preference exists (first launch)
  if (val === null) return true;
  return val === 'true';
}

export async function deleteAppLockEnabled(): Promise<void> {
  if (Platform.OS === 'web') return;
  await SecureStore.deleteItemAsync(APP_LOCK_ENABLED_KEY, secureStoreOptions);
}
