import { useState, useEffect, useMemo, useRef } from 'react';
import { BackHandler, View } from 'react-native';
import { Button } from '@/components/ui/button';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { SignInScreen } from '@/features/auth/screens/sign-in-screen';
import { useNativeSignInMutation, useResendVerificationMutation } from '@/features/auth/api/auth-mutations';
import { useAuthStore } from '@/features/auth/hooks/use-auth-store';
import { useGoogleAuth } from '@/features/auth/hooks/use-google-auth';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';
import { useAppThemePreference, useAppTheme } from '@/providers/theme-provider';
import { Moon, Sun } from 'lucide-react-native';
import { AppButton } from '@/components/ui/app-button';
import { useToast } from 'heroui-native';
import { showErrorToast } from '@/lib/toast-utils';

export default function SignInRoute() {
  const router = useRouter();
  const { t } = useTranslation();
  const params = useLocalSearchParams();
  const signInMutation = useNativeSignInMutation();
  const { signIn } = useAuthStore();
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState<string | undefined>();
  const { promptAsync, isReady, isLoading, error: googleError } = useGoogleAuth();
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setFormError(undefined) });
  const sessionErrorConsumed = useRef(false);
  const { preference, setPreference } = useAppThemePreference();
  const { mode, colors } = useAppTheme();
  const { toast } = useToast();
  const resendMutation = useResendVerificationMutation();
  const [resendEmail, setResendEmail] = useState<string>('');

  // Google auth errors → top toast (never inline form text).
  const prevGoogleError = useRef(googleError);
  useEffect(() => {
    if (googleError && googleError !== prevGoogleError.current) {
      prevGoogleError.current = googleError;
      showErrorToast(toast, t('auth.signIn.errors.googleGeneric'), 'top');
    } else if (!googleError) {
      prevGoogleError.current = null;
    }
  }, [googleError]); // eslint-disable-line react-hooks/exhaustive-deps

  // Session errors from expired tokens → toast.
  const sessionError = useMemo(() => {
    if (params.error && !sessionErrorConsumed.current) {
      sessionErrorConsumed.current = true;
      if (params.error === 'auth.refresh_token_invalid' || params.error === 'sessionExpired') {
        return t('auth.signIn.errors.sessionExpired');
      }
    }
    return undefined;
  }, [params.error]);

  // Form errors from sign-in mutation → top toast.
  const prevFormError = useRef(formError);
  useEffect(() => {
    if (formError && formError !== prevFormError.current) {
      prevFormError.current = formError;
      showErrorToast(toast, formError, 'top');
    } else if (!formError) {
      prevFormError.current = undefined;
    }
  }, [formError]); // eslint-disable-line react-hooks/exhaustive-deps

  // Session errors → top toast.
  const prevSessionError = useRef(sessionError);
  useEffect(() => {
    if (sessionError && sessionError !== prevSessionError.current) {
      prevSessionError.current = sessionError;
      showErrorToast(toast, sessionError, 'top');
    }
  }, [sessionError]); // eslint-disable-line react-hooks/exhaustive-deps

  const displayError = formError ?? sessionError;

  // SignIn is the auth root — hardware back should not exit the app.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => true);
    return () => sub.remove();
  }, []);

  return (
    <View style={{ flex: 1 }}>
      <SignInScreen
        formError={displayError}
        onCreateAccountPress={() => router.push('/(auth)/sign-up')}
        onSignInPress={async (values) => {
          setFieldErrors({});
          setFormError(undefined);
          setResendEmail('');
          try {
            const data = await signInMutation.mutateAsync(values);
            await signIn(data.access_token, data.refresh_token);
          } catch (e: any) {
            onRateLimitError(e);
            const msg = e?.response?.data?.detail;
            if (msg === 'auth.login_rate_limited') {
              setFormError(t('auth.signIn.errors.loginRateLimited'));
            } else if (msg === 'auth.idempotency_conflict_in_progress') {
              setFormError(t('auth.signIn.errors.idempotencyConflictInProgress'));
            } else if (msg === 'auth.invalid_credentials') {
              setFormError(t('auth.signIn.errors.invalidCredentials'));
            } else if (msg === 'auth.email_not_verified') {
              setResendEmail(values.email);
              setFormError(t('auth.signIn.errors.emailNotVerified'));
            } else {
              setFormError(t('auth.signIn.errors.generic'));
            }
          }
        }}
        signInState={signInMutation.isPending ? 'pending' : 'default'}
        googleState={isLoading ? 'pending' : (!isReady ? 'unavailable' : 'default')}
        onGooglePress={() => promptAsync()}
        fieldErrors={fieldErrors}
        isRateLimited={isRateLimited}
        showResendVerification={!!resendEmail}
        isResendingVerification={resendMutation.isPending}
        onResendVerificationPress={() => {
          if (!resendEmail) return;
          resendMutation.mutate({ email: resendEmail }, {
            onSuccess: () => {
              router.push({
                pathname: '/(auth)/check-email',
                params: { email: resendEmail },
              });
            },
            onError: () => {
              showErrorToast(toast, t('auth.checkEmail.errors.resendFailed'), 'top');
            },
          });
        }}
        onForgotPasswordPress={() => router.push('/(auth)/forgot-password')}
      />
      {__DEV__ && (
        <View style={{ position: 'absolute', top: 50, right: 20, zIndex: 50 }}>
          <AppButton 
            onPress={() => setPreference(mode === 'dark' ? 'light' : 'dark')} 
            size="sm" 
            variant="secondary"
            isIconOnly
          >
            {mode === 'dark' ? (
              <Sun color={colors.textPrimary} size={20} />
            ) : (
              <Moon color={colors.textPrimary} size={20} />
            )}
          </AppButton>
        </View>
      )}
    </View>
  );
}
