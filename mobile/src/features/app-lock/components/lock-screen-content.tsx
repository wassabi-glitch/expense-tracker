import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import { Fingerprint } from 'lucide-react-native';
import { useTheme } from '@/hooks/use-theme';
import { spacing, typography } from '@/theme';
import { useAppLockStore } from '../hooks/use-app-lock';
import { PinDots } from './pin-dots';
import { PinPad } from './pin-pad';

const WARNING_THRESHOLD = 3;
const MAX_ATTEMPTS = 5;

/**
 * Lock screen rendered when the app is locked.
 * Shows PIN dots + number pad + optional biometric button.
 * Theme-aware — uses system light/dark colors.
 */
export function LockScreenContent() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const {
    verifyAndUnlock,
    authenticateWithBiometrics,
    bioEnabled,
    bioAvailable,
    failedAttempts,
    cooldownRemaining,
    cooldownUntil,
  } = useAppLockStore();

  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const warningShownRef = useRef(false);
  const isInCooldown = cooldownUntil !== null && cooldownRemaining > 0;

  // Reset warning flag when attempts change
  useEffect(() => {
    if (failedAttempts < WARNING_THRESHOLD) {
      warningShownRef.current = false;
    }
  }, [failedAttempts]);

  // ── PIN entry ──────────────────────────────────────────────

  const handleDigit = useCallback(
    (digit: number) => {
      // Prevent racing submissions while a verification is in flight
      if (isVerifying) return;

      setError(null);
      const next = pin + String(digit);
      if (next.length > 5) return;
      setPin(next);

      if (next.length === 5) {
        setIsVerifying(true);
        verifyAndUnlock(next)
          .then(({ success, attemptsLeft }) => {
            if (success) {
              setPin('');
              setError(null);
              return;
            }

            if (attemptsLeft === 0) {
              // PIN was deleted (cooldown or signOutAll).
              // Clear the input and let the overlay route to the
              // correct screen — cooldown UI or PinCreateFlow.
              setPin('');
              return;
            }

            if (attemptsLeft === 1) {
              setError(t('appLock.lockScreen.lastTry'));
            } else {
              setError(
                t('appLock.lockScreen.wrongPin', { attempts: attemptsLeft }),
              );
            }

            if (
              failedAttempts + 1 >= WARNING_THRESHOLD &&
              !warningShownRef.current &&
              attemptsLeft > 0
            ) {
              warningShownRef.current = true;
              Alert.alert(
                t('appLock.warning.title'),
                t('appLock.warning.message'),
                [{ text: t('appLock.warning.dismiss') }],
              );
            }

            setPin('');
          })
          .catch(() => {
            // SecureStore read or hashing failed transiently — retry
            setError(t('appLock.lockScreen.verifyError'));
            setPin('');
          })
          .finally(() => {
            setIsVerifying(false);
          });
      }
    },
    [pin, verifyAndUnlock, failedAttempts, t, isVerifying],
  );

  const handleDelete = useCallback(() => {
    setError(null);
    if (pin.length > 0) {
      setPin(pin.slice(0, -1));
    }
  }, [pin]);

  // ── Biometric trigger ──────────────────────────────────────

  const handleBiometric = useCallback(() => {
    authenticateWithBiometrics();
  }, [authenticateWithBiometrics]);

  // ── Cooldown format ────────────────────────────────────────

  const formatCooldown = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  // ── Render cooldown state ──────────────────────────────────

  if (isInCooldown) {
    return (
      <View style={[styles.container, { backgroundColor: colors.screen }]}>
        <View style={styles.center}>
          <Text style={[styles.title, { color: colors.textPrimary }]}>
            {t('appLock.lockScreen.cooldownTitle')}
          </Text>
          <Text style={[styles.body, { color: colors.textSecondary }]}>
            {t('appLock.lockScreen.cooldownBody', {
              minutes: Math.floor(cooldownRemaining / 60),
              seconds: cooldownRemaining % 60,
            })}
          </Text>
          <Text
            style={[styles.timer, { color: colors.textPrimary }]}
            accessibilityLabel={`${Math.floor(cooldownRemaining / 60)} minutes ${cooldownRemaining % 60} seconds remaining`}
          >
            {formatCooldown(cooldownRemaining)}
          </Text>

          {/* Biometric still works during cooldown — only if user enabled it */}
          {bioEnabled && bioAvailable && (
            <View
              style={{
                width: 72,
                height: 60,
                borderRadius: 30,
                borderWidth: 1,
                borderColor: colors.borderControl,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Pressable
                accessibilityLabel={t('appLock.lockScreen.biometricButton')}
                accessibilityRole="button"
                onPress={handleBiometric}
                style={{
                  width: 72,
                  height: 60,
                  borderRadius: 30,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Fingerprint color={colors.brand.action} size={28} strokeWidth={2} />
              </Pressable>
            </View>
          )}
        </View>
      </View>
    );
  }

  // ── Render lock screen ─────────────────────────────────────

  return (
    <View style={[styles.container, { backgroundColor: colors.screen }]}>
      <View style={styles.center}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>
          {t('appLock.lockScreen.enterPin')}
        </Text>

        <View style={styles.dotsArea}>
          <PinDots count={pin.length} isError={error !== null} />
        </View>

        <View style={styles.errorArea}>
          {error ? (
            <Text style={[styles.errorText, { color: colors.status.destructive.main }]}>
              {error}
            </Text>
          ) : null}
        </View>

        <PinPad
          onDigitPress={handleDigit}
          onDeletePress={handleDelete}
          isDisabled={isVerifying}
          biometricSlot={
            bioEnabled && bioAvailable ? (
              <Fingerprint color={colors.brand.action} size={28} strokeWidth={2} />
            ) : null
          }
          onBiometricPress={handleBiometric}
        />
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
  center: {
    alignItems: 'center',
    gap: spacing.lg,
    width: '100%',
  },
  title: {
    ...typography.title,
    textAlign: 'center',
  },
  body: {
    ...typography.body,
    textAlign: 'center',
    maxWidth: 300,
  },
  timer: {
    ...typography.authTitle,
    fontSize: 40,
    textAlign: 'center',
    fontVariant: ['tabular-nums'],
  },
  dotsArea: {
    marginTop: spacing.lg,
  },
  errorArea: {
    minHeight: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
    paddingHorizontal: spacing.md,
  },
});
