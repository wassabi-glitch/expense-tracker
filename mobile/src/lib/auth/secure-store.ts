import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const REFRESH_TOKEN_KEY = 'sarflog_refresh_token';

// iOS handles keychain differently. We use 'SecureStore.WHEN_UNLOCKED' for standard protection
const secureStoreOptions: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.WHEN_UNLOCKED,
};

export async function saveRefreshToken(token: string): Promise<void> {
  if (Platform.OS === 'web') {
    // Just a fallback for web if accidentally used, though web uses HttpOnly cookies
    return;
  }
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token, secureStoreOptions);
}

export async function getRefreshToken(): Promise<string | null> {
  if (Platform.OS === 'web') {
    return null;
  }
  return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY, secureStoreOptions);
}

export async function deleteRefreshToken(): Promise<void> {
  if (Platform.OS === 'web') {
    return;
  }
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY, secureStoreOptions);
}
