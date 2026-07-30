import { useState, useEffect } from 'react';
import { GoogleSignin, statusCodes } from '@react-native-google-signin/google-signin';
import { useGoogleNativeAuthMutation } from '../api/auth-mutations';
import { useAuthStore } from './use-auth-store';

export function useGoogleAuth() {
  const [error, setError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const { signIn } = useAuthStore();
  const googleNativeAuthMutation = useGoogleNativeAuthMutation();

  useEffect(() => {
    // We only pass webClientId to configure. The native Android SDK automatically 
    // derives the Android Client ID using the app's package name and SHA-1.
    GoogleSignin.configure({
      webClientId: process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID,
      offlineAccess: true,
    });
    setIsInitializing(false);
  }, []);

  const promptAsync = async () => {
    setError(null);
    try {
      await GoogleSignin.hasPlayServices();
      const response = await GoogleSignin.signIn();
      // GoogleSignin v16 returns { data: { idToken, user } }
      const idToken = response.data?.idToken;

      if (idToken) {
        googleNativeAuthMutation.mutate(
          { id_token: idToken },
          {
            onSuccess: async (data) => {
              await signIn(data.access_token, data.refresh_token);
            },
            onError: (err: any) => {
              const detail: string | undefined = err?.response?.data?.detail;
              if (!detail) {
                setError('generic');
                return;
              }
              // Strip 'auth.' prefix and convert snake_case to camelCase so
              // backend error codes (auth.google_id_token_invalid) match
              // translation keys (auth.signIn.errors.googleIdTokenInvalid).
              const key = detail.startsWith('auth.')
                ? detail.slice(5).replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())
                : detail;
              setError(key);
            },
          }
        );
      } else {
        setError('googleIdTokenMissing');
      }
    } catch (err: any) {
      if (err.code === statusCodes.SIGN_IN_CANCELLED) {
        // user cancelled the login flow
      } else if (err.code === statusCodes.IN_PROGRESS) {
        // operation (e.g. sign in) is in progress already
      } else if (err.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
        setError('googlePlayServicesUnavailable');
      } else {
        setError('googleAuthFailed');
      }
    }
  };

  return {
    isReady: !isInitializing,
    isLoading: googleNativeAuthMutation.isPending,
    error,
    promptAsync,
  };
}
