/* eslint-disable react-hooks/exhaustive-deps */
import { useLocalSearchParams, useNavigation, useRouter } from 'expo-router';
import { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckEmailScreen } from '@/features/auth/screens/check-email-screen';
import { useResendVerificationMutation } from '@/features/auth/api/auth-mutations';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';
import { useToast } from 'heroui-native';
import { showErrorToast } from '@/lib/toast-utils';

export default function CheckEmailRoute() {
  const router = useRouter();
  const navigation = useNavigation();
  const { t } = useTranslation();
  const { toast } = useToast();
  const params = useLocalSearchParams<{ email?: string; sent?: string }>();
  const email = params.email || '';
  const sent = params.sent !== '0'; // default true, unless explicitly '0'

  const resendMutation = useResendVerificationMutation();
  const [cooldown, setCooldown] = useState(0);
  const { isRateLimited, onRateLimitError } = useRateLimitGate();
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // No email param means the user reached this screen without signing up.
  useEffect(() => {
    if (!email) {
      router.replace('/(auth)/sign-in');
    }
  }, [email]);

  // If we arrived from SignUp via push (with animation), remove SignUp from
  // the stack once the transition ends so device-back goes to SignIn, not
  // back to the already-submitted sign-up form.
  useEffect(() => {
    const nav = navigation as any;
    const state = nav.getState();
    if (!state?.routes) return;
    const unsubscribe = nav.addListener('transitionEnd', () => {
      const currentState = nav.getState();
      if (!currentState?.routes) return;
      const signUpIndex = currentState.routes.findIndex(
        (r: any) => r.name?.includes('sign-up'),
      );
      if (signUpIndex >= 0) {
        const newRoutes = [...currentState.routes];
        newRoutes.splice(signUpIndex, 1);
        const newIndex = currentState.index > signUpIndex ? currentState.index - 1 : currentState.index;
        nav.reset({
          ...currentState,
          routes: newRoutes,
          index: newIndex,
        });
      }
    });
    return unsubscribe;
  }, [navigation]);

  function startCooldown(duration = 60) {
    setCooldown(duration);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setCooldown((c) => {
        if (c <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          return 0;
        }
        return c - 1;
      });
    }, 1000);
  }

  // If initial signup delivery failed, jump straight into cooldown
  useEffect(() => {
    if (!sent && cooldown === 0) {
      startCooldown(60);
    }
  }, [sent]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const resendState = resendMutation.isPending
    ? 'pending'
    : cooldown > 0
      ? 'countdown'
      : 'default';

  return (
    <CheckEmailScreen
      resendState={resendState}
      resendCountdownSeconds={cooldown}
      isRateLimited={isRateLimited}
      initialSendFailed={!sent}
      onResendPress={() => {
        if (!email) return;
        resendMutation.mutate({ email }, {
          onSuccess: () => {
            startCooldown(60);
          },
          onError: (error) => {
            const wasRateLimited = (error as any)?.retryAfterSeconds > 0;
            onRateLimitError(error);
            if (wasRateLimited) {
              showErrorToast(toast, t('auth.checkEmail.errors.rateLimited'), 'top');
            } else {
              startCooldown(5);
              showErrorToast(toast, t('auth.checkEmail.errors.resendFailed'), 'top');
            }
          }
        });
      }}
      onBack={() => {
        router.replace('/(auth)/sign-in');
      }}
    />
  );
}
