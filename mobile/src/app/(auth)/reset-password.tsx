import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { BackHandler } from 'react-native';
import { useTranslation } from 'react-i18next';
import { ResetPasswordScreen, ResetPasswordState } from '@/features/auth/screens/reset-password-screen';
import { useResetPasswordMutation } from '@/features/auth/api/auth-mutations';
import { ResetPasswordValues } from '@/features/auth/schemas/reset-password-schema';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';
import { useToast } from 'heroui-native';
import { showErrorToast } from '@/lib/toast-utils';

export default function ResetPasswordRoute() {
  const router = useRouter();
  const { t } = useTranslation();
  const { toast } = useToast();
  const { token } = useLocalSearchParams<{ token?: string }>();
  const [resetPasswordState, setResetPasswordState] = useState<ResetPasswordState>('ready');
  const [formError, setFormError] = useState<string | undefined>(undefined);
  const resetPasswordMutation = useResetPasswordMutation();
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setFormError(undefined) });

  // Deep-link screen — back goes to SignIn, not into the void.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      router.replace('/(auth)/sign-in');
      return true;
    });
    return () => sub.remove();
  }, []);

  // Missing-token error in ready state → top toast.
  // Error-page errors (rate limit, invalid token, etc.) replace the form
  // entirely so they don't need a toast on top.
  const prevFormError = useRef(formError);
  useEffect(() => {
    if (formError && resetPasswordState !== 'error' && formError !== prevFormError.current) {
      prevFormError.current = formError;
      showErrorToast(toast, formError, 'top');
    } else if (!formError) {
      prevFormError.current = undefined;
    }
  }, [formError, resetPasswordState]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleResetPassword = async (values: ResetPasswordValues) => {
    if (!token) {
      setFormError(t('auth.resetPassword.errors.missingToken'));
      return;
    }

    setResetPasswordState('loading');
    setFormError(undefined);

    try {
      await resetPasswordMutation.mutateAsync({
        token,
        new_password: values.password,
      });
      setResetPasswordState('success');
    } catch (error: any) {
      onRateLimitError(error);
      setResetPasswordState('ready');
      const errorCode = error?.response?.data?.detail;
      if (errorCode === 'auth.reset_password_rate_limited') {
        setFormError(t('auth.resetPassword.errors.rateLimited'));
        setResetPasswordState('error');
      } else if (errorCode === 'auth.idempotency_conflict_in_progress') {
        setFormError(t('auth.resetPassword.errors.idempotencyConflictInProgress'));
        setResetPasswordState('error');
      } else if (errorCode === 'auth.invalid_token') {
        setFormError(t('auth.resetPassword.errors.invalidToken'));
        setResetPasswordState('error');
      } else {
        setFormError(t('auth.resetPassword.errors.generic'));
        setResetPasswordState('error');
      }
    }
  };

  const handleContinueToSignIn = () => {
    router.replace('/(auth)/sign-in');
  };

  // Auto redirect on success
  useEffect(() => {
    if (resetPasswordState === 'success') {
      const timer = setTimeout(() => {
        handleContinueToSignIn();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [resetPasswordState]);

  const handleRequestNewLink = () => {
    router.replace('/(auth)/forgot-password');
  };

  return (
    <ResetPasswordScreen
      formError={formError}
      isRateLimited={isRateLimited}
      onBack={() => router.replace('/(auth)/sign-in')}
      onContinueToSignInPress={handleContinueToSignIn}
      onRequestNewLinkPress={handleRequestNewLink}
      onResetPasswordPress={handleResetPassword}
      resetPasswordState={resetPasswordState}
    />
  );
}
