import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ForgotPasswordScreen, ForgotPasswordState } from '@/features/auth/screens/forgot-password-screen';
import { useForgotPasswordMutation } from '@/features/auth/api/auth-mutations';
import { ForgotPasswordValues } from '@/features/auth/schemas/forgot-password-schema';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';
import { useToast } from 'heroui-native';
import { showErrorToast } from '@/lib/toast-utils';

export default function ForgotPasswordRoute() {
  const router = useRouter();
  const { t } = useTranslation();
  const { toast } = useToast();
  const [forgotPasswordState, setForgotPasswordState] = useState<ForgotPasswordState>('ready');
  const [formError, setFormError] = useState<string | undefined>(undefined);
  const forgotPasswordMutation = useForgotPasswordMutation();
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setFormError(undefined) });

  // Form errors → top toast.
  const prevFormError = useRef(formError);
  useEffect(() => {
    if (formError && formError !== prevFormError.current) {
      prevFormError.current = formError;
      showErrorToast(toast, formError, 'top');
    } else if (!formError) {
      prevFormError.current = undefined;
    }
  }, [formError]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSendLink = async (values: ForgotPasswordValues) => {
    setForgotPasswordState('loading');
    setFormError(undefined);

    try {
      await forgotPasswordMutation.mutateAsync(values);
      setForgotPasswordState('success');
    } catch (error: any) {
      onRateLimitError(error);
      setForgotPasswordState('ready');
      const errorCode = error?.response?.data?.detail;
      if (errorCode === 'auth.forgot_password_rate_limited') {
        setFormError(t('auth.forgotPassword.errors.rateLimited'));
      } else if (errorCode === 'auth.idempotency_conflict_in_progress') {
        setFormError(t('auth.forgotPassword.errors.idempotencyConflictInProgress'));
      } else {
        setFormError(t('auth.forgotPassword.errors.generic'));
      }
    }
  };

  return (
    <ForgotPasswordScreen
      forgotPasswordState={forgotPasswordState}
      formError={formError}
      isRateLimited={isRateLimited}
      onBack={() => router.replace('/(auth)/sign-in')}
      onSendLinkPress={handleSendLink}
    />
  );
}
