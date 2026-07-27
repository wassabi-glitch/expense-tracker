import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ResetPasswordScreen, ResetPasswordState } from '@/features/auth/screens/reset-password-screen';
import { useResetPasswordMutation } from '@/features/auth/api/auth-mutations';
import { ResetPasswordValues } from '@/features/auth/schemas/reset-password-schema';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';

export default function ResetPasswordRoute() {
  const router = useRouter();
  const { token } = useLocalSearchParams<{ token?: string }>();
  const [resetPasswordState, setResetPasswordState] = useState<ResetPasswordState>('ready');
  const [formError, setFormError] = useState<string | undefined>(undefined);
  const resetPasswordMutation = useResetPasswordMutation();
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setFormError(undefined) });

  const handleResetPassword = async (values: ResetPasswordValues) => {
    if (!token) {
      setFormError('auth.resetPassword.errors.missingToken');
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
        setFormError('auth.resetPassword.errors.rateLimited');
        setResetPasswordState('error');
      } else if (errorCode === 'auth.idempotency_conflict_in_progress') {
        setFormError('auth.resetPassword.errors.idempotencyConflictInProgress');
        setResetPasswordState('error');
      } else if (errorCode === 'auth.invalid_token') {
        setFormError('auth.resetPassword.errors.invalidToken');
        setResetPasswordState('error');
      } else {
        setFormError('auth.resetPassword.errors.generic');
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
      onContinueToSignInPress={handleContinueToSignIn}
      onRequestNewLinkPress={handleRequestNewLink}
      onResetPasswordPress={handleResetPassword}
      resetPasswordState={resetPasswordState}
    />
  );
}
