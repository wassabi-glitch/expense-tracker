import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '@/hooks/use-theme';
import { spacing, typography } from '@/theme';
import { Button } from '@/components/ui/button';
import { TextField } from 'heroui-native/text-field';
import { InputGroup } from 'heroui-native/input-group';
import { FieldError } from 'heroui-native/field-error';
import { Spinner } from 'heroui-native/spinner';
import { Lock } from 'lucide-react-native';
import { useVerifyPasswordMutation } from '@/features/auth/api/auth-mutations';
import { useAppLockStore } from '../hooks/use-app-lock';

/**
 * Password verification screen shown after 30-min cooldown expires.
 * User must enter their Sarflog password to prove identity before resetting PIN.
 * Theme-aware — uses system light/dark colors.
 */
export function PasswordVerifyScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const router = useRouter();
  const { markPasswordVerified } = useAppLockStore();

  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const verifyMutation = useVerifyPasswordMutation();
  const isPending = verifyMutation.isPending;

  const handleVerify = useCallback(async () => {
    setFormError(null);
    try {
      await verifyMutation.mutateAsync({ password });
      markPasswordVerified();
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      if (detail === 'auth.incorrect_password') {
        setFormError('appLock.passwordVerify.incorrectPassword');
      } else if (detail === 'auth.rate_limited') {
        setFormError('appLock.passwordVerify.rateLimited');
      } else if (detail === 'auth.idempotency_conflict_in_progress') {
        setFormError('appLock.passwordVerify.idempotencyConflict');
      } else {
        setFormError('appLock.passwordVerify.networkError');
      }
    }
  }, [password, verifyMutation, markPasswordVerified, t]);

  const handleForgotPassword = useCallback(() => {
    router.push('/(auth)/forgot-password');
  }, [router]);

  const formReady = password.length > 0;

  return (
    <View style={[styles.container, { backgroundColor: colors.screen }]}>
      <View style={styles.content}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>
          {t('appLock.passwordVerify.title')}
        </Text>

        <Text style={[styles.body, { color: colors.textSecondary }]}>
          {t('appLock.passwordVerify.body')}
        </Text>

        {/* Password field */}
        <View style={styles.fieldWrapper}>
          <TextField isInvalid={formError !== null}>
            <InputGroup>
              <InputGroup.Prefix isDecorative>
                <Lock color={colors.textSecondary} size={20} />
              </InputGroup.Prefix>
              <InputGroup.Input
                accessibilityLabel={t('appLock.passwordVerify.placeholder')}
                autoCapitalize="none"
                autoComplete="current-password"
                onChangeText={setPassword}
                placeholder={t('appLock.passwordVerify.placeholder')}
                returnKeyType="done"
                secureTextEntry
                textContentType="password"
                value={password}
              />
            </InputGroup>
            {formError ? (
              <FieldError>{t(formError as any)}</FieldError>
            ) : null}
          </TextField>
        </View>

        {/* Error text also shown as inline red */}
        {formError ? (
          <Text style={[styles.errorText, { color: colors.status.destructive.main }]}>
            {t(formError as any)}
          </Text>
        ) : null}

        {/* Verify button */}
        <Button
          className="w-full"
          isDisabled={!formReady || isPending}
          onPress={handleVerify}
          size="md"
          variant="primary"
        >
          {isPending ? (
            <View className="flex-row items-center justify-center gap-2">
              <Spinner size="sm" />
              <Button.Label>{t('appLock.passwordVerify.verify')}</Button.Label>
            </View>
          ) : (
            <Button.Label>{t('appLock.passwordVerify.verify')}</Button.Label>
          )}
        </Button>

        {/* Forgot password link */}
        <Pressable
          accessibilityRole="link"
          onPress={handleForgotPassword}
          style={styles.forgotLink}
        >
          <Text style={[styles.forgotLinkText, { color: colors.textSecondary }]}>
            {t('appLock.passwordVerify.forgotPassword')}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
  },
  content: {
    width: '100%',
    maxWidth: 400,
    gap: spacing.lg,
  },
  title: {
    ...typography.title,
    textAlign: 'center',
  },
  body: {
    ...typography.body,
    textAlign: 'center',
  },
  fieldWrapper: {
    width: '100%',
  },
  errorText: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  forgotLink: {
    alignItems: 'center',
    paddingVertical: spacing.sm,
    minHeight: 48,
    justifyContent: 'center',
  },
  forgotLinkText: {
    fontSize: 14,
    fontWeight: '500',
    textDecorationLine: 'underline',
  },
});
