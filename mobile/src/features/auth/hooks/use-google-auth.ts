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
              const msg = err?.response?.data?.detail;
              setError(msg || 'auth.generic_error');
            },
          }
        );
      } else {
        setError('google_id_token_missing');
      }
    } catch (err: any) {
      if (err.code === statusCodes.SIGN_IN_CANCELLED) {
        // user cancelled the login flow
      } else if (err.code === statusCodes.IN_PROGRESS) {
        // operation (e.g. sign in) is in progress already
      } else if (err.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
        setError('google_play_services_unavailable');
      } else {
        setError('google_auth_failed');
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
