import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useAuthStore } from '@/features/auth/hooks/use-auth-store';
import { useAppLockStore } from '@/features/app-lock/hooks/use-app-lock';
import { AppLockOverlay } from '@/features/app-lock/components/app-lock-overlay';

const AppLockContext = createContext<boolean>(false);

export function useAppLockContext() {
  return useContext(AppLockContext);
}

export type AppLockProviderProps = {
  children: ReactNode;
};

/**
 * Provider that wires the AppLock state machine to the auth lifecycle.
 * Activates only when the user is authenticated.
 * Sets up the AppState listener and renders the overlay when locked.
 */
export function AppLockProvider({ children }: AppLockProviderProps) {
  const authStatus = useAuthStore((s) => s.status);
  const { isInitialized, initialize, setupAppStateListener } = useAppLockStore();

  // Initialize app lock state when user becomes authenticated
  useEffect(() => {
    if (authStatus === 'authenticated' && !isInitialized) {
      initialize();
    }
  }, [authStatus, isInitialized, initialize]);

  // Set up AppState listener once initialized, and trigger
  // biometric on fresh launch (AppState doesn't fire an 'active'
  // event when the app first opens — _onForeground covers that gap).
  useEffect(() => {
    if (isInitialized) {
      setupAppStateListener();
      // Fresh launch into lock screen: attempt biometric auto-unlock
      const { _onForeground } = useAppLockStore.getState();
      _onForeground();
    }
  }, [isInitialized, setupAppStateListener]);

  // Only lock when authenticated; pass through during auth/restore
  const isActive = authStatus === 'authenticated' && isInitialized;

  return (
    <AppLockContext.Provider value={isActive}>
      {isActive && <AppLockOverlay />}
      {children}
    </AppLockContext.Provider>
  );
}
