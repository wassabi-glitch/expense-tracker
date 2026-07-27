import { create } from 'zustand';
import { getRefreshToken, saveRefreshToken, deleteRefreshToken } from '@/lib/auth/secure-store';
import { setAccessToken, clearAuthState as clearClientAuth } from '@/lib/api/client';
import { deletePinHash, deleteCooldownUntil, deleteAllPinData } from '@/lib/auth/pin-store';
import { useAppLockStore } from '@/features/app-lock/hooks/use-app-lock';

type AuthStatus = 'restoring' | 'authenticated' | 'unauthenticated';

type AuthState = {
  status: AuthStatus;
  signIn: (accessToken: string, refreshToken: string) => Promise<void>;
  signOut: () => Promise<void>;
  signOutAll: () => Promise<void>;
  restoreSession: () => Promise<void>;
  setUnauthenticated: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  status: 'restoring',

  signIn: async (accessToken, refreshToken) => {
    setAccessToken(accessToken);
    await saveRefreshToken(refreshToken);
    set({ status: 'authenticated' });
  },

  signOut: async () => {
    clearClientAuth();
    await deleteRefreshToken();
    // Delete the PIN credential and any active cooldown so the next
    // account gets a clean slate. Bio preference and App Lock toggle
    // are device settings — those stay.
    await Promise.all([deletePinHash(), deleteCooldownUntil()]);
    // Reset in-memory AppLock state
    useAppLockStore.setState({
      isInitialized: false,
      pinExists: false,
      isLocked: false,
      isSettingUp: false,
      failedAttempts: 0,
      cooldownUntil: null,
      cooldownRemaining: 0,
      passwordVerified: false,
      changePinMode: false,
    });
    set({ status: 'unauthenticated' });
  },

  signOutAll: async () => {
    clearClientAuth();
    await deleteRefreshToken();
    await deleteAllPinData();
    // Reset AppLock in-memory state so next sign-in re-initialises
    // from SecureStore instead of using stale values.
    useAppLockStore.setState({
      isInitialized: false,
      pinExists: false,
      isLocked: false,
      isSettingUp: false,
      failedAttempts: 0,
      cooldownUntil: null,
      cooldownRemaining: 0,
      passwordVerified: false,
      changePinMode: false,
      bioEnabled: false,
    });
    set({ status: 'unauthenticated' });
  },
  
  setUnauthenticated: () => {
    // Force AppLock to re-initialise on next sign-in so it reads
    // the current state from SecureStore instead of using stale
    // in-memory values that may not match what's on disk.
    useAppLockStore.setState({ isInitialized: false });
    set({ status: 'unauthenticated' });
  },

  restoreSession: async () => {
    try {
      const token = await getRefreshToken();
      if (token) {
        // We have a refresh token. The API client will handle the actual refresh
        // when the first request is made, or we can consider it 'authenticated'
        // and let the interceptor handle it if it fails.
        // For a smoother experience, we mark as authenticated.
        set({ status: 'authenticated' });
      } else {
        set({ status: 'unauthenticated' });
      }
    } catch (e) {
      set({ status: 'unauthenticated' });
    }
  },
}));
