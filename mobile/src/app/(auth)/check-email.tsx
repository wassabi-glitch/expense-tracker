/* eslint-disable react-hooks/exhaustive-deps */
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState, useRef } from 'react';
import { CheckEmailScreen } from '@/features/auth/screens/check-email-screen';
import { useResendVerificationMutation } from '@/features/auth/api/auth-mutations';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';

export default function CheckEmailRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ email?: string; sent?: string }>();
  const email = params.email || '';
  const sent = params.sent !== '0'; // default true, unless explicitly '0'

  const resendMutation = useResendVerificationMutation();
  const [cooldown, setCooldown] = useState(0);
  const { isRateLimited, onRateLimitError } = useRateLimitGate();
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // If initial signup delivery failed, jump straight into cooldown
  useEffect(() => {
    if (!sent && cooldown === 0) {
      startCooldown();
    }
  }, [sent]);

  function startCooldown() {
    setCooldown(60);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setCooldown((c) => {
        if (c <= 1) {
          clearInterval(timerRef.current!);
          return 0;
        }
        return c - 1;
      });
    }, 1000);
  }

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
      onResendPress={() => {
        if (!email) return;
        resendMutation.mutate({ email }, {
          onSuccess: () => {
            startCooldown();
          },
          onError: (error) => {
            onRateLimitError(error);
            // Wait 5 seconds before allowing retry on error
            setCooldown(5);
            startCooldown();
          }
        });
      }}
      onBackToSignInPress={() => {
        router.push('/(auth)/sign-in');
      }}
    />
  );
}
