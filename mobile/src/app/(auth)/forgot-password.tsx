import { useRouter } from 'expo-router';
import { useState } from 'react';
import { ForgotPasswordScreen, ForgotPasswordState } from '@/features/auth/screens/forgot-password-screen';
import { useForgotPasswordMutation } from '@/features/auth/api/auth-mutations';
import { ForgotPasswordValues } from '@/features/auth/schemas/forgot-password-schema';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';

export default function ForgotPasswordRoute() {
  const router = useRouter();
  const [forgotPasswordState, setForgotPasswordState] = useState<ForgotPasswordState>('ready');
  const [formError, setFormError] = useState<string | undefined>(undefined);
  const forgotPasswordMutation = useForgotPasswordMutation();
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setFormError(undefined) });

  const handleSendLink = async (values: ForgotPasswordValues) => {
    setForgotPasswordState('loading');
    setFormError(undefined);

    try {
      await forgotPasswordMutation.mutateAsync(values);
      // Ghost user logic means it always succeeds if not rate limited
      setForgotPasswordState('success');
    } catch (error: any) {
      onRateLimitError(error);
      setForgotPasswordState('ready');
      const errorCode = error?.response?.data?.detail;
      if (errorCode === 'auth.forgot_password_rate_limited') {
        setFormError('auth.forgotPassword.errors.rateLimited');
      } else if (errorCode === 'auth.idempotency_conflict_in_progress') {
        setFormError('auth.forgotPassword.errors.idempotencyConflictInProgress');
      } else {
        setFormError('auth.forgotPassword.errors.generic');
      }
    }
  };

  const handleBackToSignIn = () => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace('/(auth)/sign-in');
    }
  };

  return (
    <ForgotPasswordScreen
      forgotPasswordState={forgotPasswordState}
      formError={formError}
      isRateLimited={isRateLimited}
      onBackToSignInPress={handleBackToSignIn}
      onSendLinkPress={handleSendLink}
    />
  );
}
