import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { BackHandler } from 'react-native';
import { VerifyAccountScreen, VerifyAccountState } from '@/features/auth/screens/verify-account-screen';
import { useVerifyEmailMutation } from '@/features/auth/api/auth-mutations';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';

export default function VerifyEmailRoute() {
  const params = useLocalSearchParams<{ token?: string }>();
  const router = useRouter();
  const verifyMutation = useVerifyEmailMutation();
  const [localError, setLocalError] = useState(false);
  const { isRateLimited, onRateLimitError } = useRateLimitGate();

  const token = typeof params.token === 'string' ? params.token.trim() : '';

  // Deep-link screen — back goes to SignIn, not into the void.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      router.replace('/(auth)/sign-in');
      return true;
    });
    return () => sub.remove();
  }, []);

  let verifyState: VerifyAccountState = 'ready';
  let customErrorMessage: string | undefined;

  if (verifyMutation.isPending) {
    verifyState = 'loading';
  } else if (verifyMutation.isSuccess) {
    verifyState = 'success';
  } else if (verifyMutation.isError || localError) {
    verifyState = 'error';
    if (localError) {
      customErrorMessage = 'auth.verifyAccount.missingToken';
    } else {
      // @ts-expect-error axios response
      const msg = verifyMutation.error?.response?.data?.detail;
      if (msg === 'auth.verify_email_rate_limited') {
        customErrorMessage = 'auth.verifyAccount.rateLimited';
      } else if (msg === 'auth.verify_email_token_invalid_or_expired' || (msg && msg.includes('invalid'))) {
        customErrorMessage = 'auth.verifyAccount.invalidToken';
      }
    }
  }

  return (
    <VerifyAccountScreen
      customErrorMessage={customErrorMessage}
      verifyState={verifyState}
      isRateLimited={isRateLimited}
      onBack={() => router.replace('/(auth)/sign-in')}
      onVerifyPress={() => {
        if (!token) {
          setLocalError(true);
          return;
        }
        setLocalError(false);
        verifyMutation.mutate(
          { token },
          {
            onError: (error) => {
              onRateLimitError(error);
            },
          },
        );
      }}
      onContinueToSignInPress={() => {
        router.replace('/(auth)/sign-in');
      }}
      onRequestNewLinkPress={() => {
        router.replace('/(auth)/sign-in');
      }}
    />
  );
}
