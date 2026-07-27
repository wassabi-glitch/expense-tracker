import { useState, useMemo, useRef } from 'react';
import { View } from 'react-native';
import { Button } from '@/components/ui/button';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { SignInScreen } from '@/features/auth/screens/sign-in-screen';
import { useNativeSignInMutation } from '@/features/auth/api/auth-mutations';
import { useAuthStore } from '@/features/auth/hooks/use-auth-store';
import { useGoogleAuth } from '@/features/auth/hooks/use-google-auth';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';

export default function SignInRoute() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const signInMutation = useNativeSignInMutation();
  const { signIn } = useAuthStore();
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState<string | undefined>();
  const { promptAsync, isReady, isLoading, error: googleError } = useGoogleAuth();
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setFormError(undefined) });
  const sessionErrorConsumed = useRef(false);

  // Derive google/session errors from props without effects
  const googleFormError = useMemo(() => {
    if (googleError) return `auth.signIn.errors.${googleError}`;
    if (params.error && !sessionErrorConsumed.current) {
      sessionErrorConsumed.current = true;
      if (params.error === 'auth.refresh_token_invalid' || params.error === 'sessionExpired') {
        return 'auth.signIn.errors.sessionExpired';
      }
    }
    return undefined;
  }, [googleError, params.error]);

  const displayError = formError ?? googleFormError;

  return (
    <View style={{ flex: 1 }}>
      <SignInScreen
        formError={displayError}
        onCreateAccountPress={() => router.push('/(auth)/sign-up')}
        onSignInPress={async (values) => {
          setFieldErrors({});
          setFormError(undefined);
          try {
            const data = await signInMutation.mutateAsync(values);
            await signIn(data.access_token, data.refresh_token);
          } catch (e: any) {
            onRateLimitError(e);
            const msg = e?.response?.data?.detail;
            if (msg === 'auth.login_rate_limited') {
              setFormError('auth.signIn.errors.loginRateLimited');
            } else if (msg === 'auth.idempotency_conflict_in_progress') {
              setFormError('auth.signIn.errors.idempotencyConflictInProgress');
            } else {
              setFieldErrors({ email: true, password: true });
            }
          }
        }}
        signInState={signInMutation.isPending ? 'pending' : 'default'}
        googleState={isLoading ? 'pending' : (!isReady ? 'unavailable' : 'default')}
        onGooglePress={() => promptAsync()}
        fieldErrors={fieldErrors}
        isRateLimited={isRateLimited}
        onForgotPasswordPress={() => router.push('/(auth)/forgot-password')}
      />
      {__DEV__ && (
        <View style={{ position: 'absolute', top: 50, right: 20, zIndex: 50 }}>
          <Button onPress={() => router.push('/auth-preview')} size="sm" variant="secondary">
            <Button.Label>Preview Gallery</Button.Label>
          </Button>
        </View>
      )}
    </View>
  );
}
