import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { SignUpScreen, SignUpField } from '@/features/auth/screens/sign-up-screen';
import { useSignUpMutation } from '@/features/auth/api/auth-mutations';
import { useGoogleAuth } from '@/features/auth/hooks/use-google-auth';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';

export default function SignUpRoute() {
  const router = useRouter();
  const { t } = useTranslation();
  const signUpMutation = useSignUpMutation();
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<SignUpField, boolean>>>({});
  const [formError, setFormError] = useState<string | undefined>();
  const { promptAsync, isReady, isLoading, error: googleError } = useGoogleAuth();
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setFormError(undefined) });

  return (
    <SignUpScreen
      createAccountState={signUpMutation.isPending ? 'pending' : 'default'}
      googleState={isLoading ? 'pending' : (!isReady ? 'unavailable' : 'default')}
      fieldErrors={fieldErrors}
      formError={formError || (googleError ? String(t(`auth.signUp.errors.${googleError}` as any)) : undefined)}
      isRateLimited={isRateLimited}
      onSignInPress={() => router.push('/(auth)/sign-in')}
      onGooglePress={() => promptAsync()}
      onCreateAccount={(values) => {
        setFieldErrors({});
        setFormError(undefined);
        signUpMutation.mutate(values, {
          onSuccess: (data) => {
            const sentParam = data.verification_email_sent !== false ? '1' : '0';
            router.push({
              pathname: '/(auth)/check-email',
              params: { email: values.email, sent: sentParam },
            });
          },
          onError: (error) => {
            onRateLimitError(error);
            const data = error.response?.data as { detail?: string } | undefined;
            const msg = String(data?.detail || error.message || '').toLowerCase();
            if (msg.includes('username already taken') || msg === 'auth.username_already_taken') {
              setFieldErrors({ username: true });
            } else if (msg.includes('email already registered') || msg === 'auth.email_already_registered') {
              setFieldErrors({ email: true });
            } else if (msg === 'auth.signup_rate_limited') {
              setFormError(t('auth.signUp.errors.rateLimited'));
            } else if (msg === 'auth.signup_global_rate_limited') {
              setFormError(t('auth.signUp.errors.globalRateLimited'));
            } else if (msg === 'auth.signup_conflict' || msg.includes('email or username already registered')) {
              setFormError(t('auth.signUp.errors.conflict'));
            } else if (msg === 'auth.idempotency_conflict_in_progress') {
              setFormError(t('auth.signUp.errors.idempotencyConflictInProgress'));
            } else if (msg === 'auth.disposable_email_blocked') {
              setFormError(t('auth.signUp.errors.disposableEmailBlocked'));
            } else {
              setFormError(t('auth.signUp.errors.generic'));
            }
          },
        });
      }}
    />
  );
}
