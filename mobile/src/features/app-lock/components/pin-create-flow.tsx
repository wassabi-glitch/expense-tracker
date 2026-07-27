import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, Text, View } from 'react-native';
import * as LocalAuthentication from 'expo-local-authentication';
import { useTheme } from '@/hooks/use-theme';
import { spacing, typography } from '@/theme';
import { useAppLockStore } from '../hooks/use-app-lock';
import { PinDots } from './pin-dots';
import { PinPad } from './pin-pad';

export type PinCreateFlowProps = {
  /** When true, skips the biometric-enrollment popup (used for Change PIN from Settings). */
  hideBioOffer?: boolean;
};

type Phase = 'enter' | 'repeat';

/**
 * Two-phase PIN creation flow rendered inside the lock overlay.
 * Phase 1: Enter 5-digit PIN (auto-advance on 5th digit)
 * Phase 2: Repeat PIN (auto-advance on 5th digit)
 * On match: offer biometric enrollment if device supports it, then complete.
 * When hideBioOffer is true: skip offer, save directly.
 * On mismatch: show error, reset to Phase 1.
 */
export function PinCreateFlow({ hideBioOffer = false }: PinCreateFlowProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { setPin, enableBio, bioAvailable } = useAppLockStore();

  const [phase, setPhase] = useState<Phase>('enter');
  const [firstPin, setFirstPin] = useState('');
  const [repeatPin, setRepeatPin] = useState('');
  const [error, setError] = useState<string | null>(null);

  // ── PIN match → biometric offer → complete ────────────────

  const handlePinMatch = useCallback(
    async (pin: string) => {
      // When hideBioOffer is true (Change PIN from Settings), save immediately.
      // No biometric popup — the user configured that setting already.
      if (hideBioOffer) {
        await setPin(pin);
        // If this is a change-PIN flow, finish it
        const { finishChangePin, changePinMode } = useAppLockStore.getState();
        if (changePinMode) {
          finishChangePin();
        }
        return;
      }

      // Show biometric offer BEFORE saving the PIN.
      // The user stays on the create-PIN screen until they choose
      // "Later" or "Enable" — the app is never visible behind the prompt.
      if (bioAvailable) {
        Alert.alert(
          t('appLock.createPin.bioOfferTitle'),
          t('appLock.createPin.bioOfferMessage'),
          [
            {
              text: t('appLock.createPin.later'),
              style: 'cancel',
              onPress: async () => {
                await setPin(pin);
              },
            },
            {
              text: t('appLock.createPin.enable'),
              onPress: async () => {
                try {
                  const result =
                    await LocalAuthentication.authenticateAsync({
                      promptMessage: 'Enable biometric unlock',
                    });
                  if (result.success) {
                    await enableBio();
                  }
                } catch {
                  // User cancelled — that's fine
                }
                // Always proceed into the app after the choice
                await setPin(pin);
              },
            },
          ],
        );
      } else {
        // No biometric available — save PIN and enter app immediately
        await setPin(pin);
      }
    },
    [setPin, enableBio, bioAvailable, t, hideBioOffer],
  );

  // ── Digit entry / deletion handlers ───────────────────────

  const handleDelete = useCallback(() => {
    setError(null);
    const current = phase === 'enter' ? firstPin : repeatPin;
    const setter = phase === 'enter' ? setFirstPin : setRepeatPin;
    if (current.length > 0) {
      setter(current.slice(0, -1));
    }
  }, [phase, firstPin, repeatPin]);

  const handleDigitEnter = useCallback(
    (digit: number) => {
      setError(null);
      const current = phase === 'enter' ? firstPin : repeatPin;
      const setter = phase === 'enter' ? setFirstPin : setRepeatPin;
      const next = current + String(digit);

      if (next.length > 5) return;
      setter(next);

      // Auto-advance on 5th digit
      if (next.length === 5) {
        if (phase === 'enter') {
          // Move to repeat phase
          setTimeout(() => {
            setPhase('repeat');
          }, 300);
        } else {
          // Phase 2 complete — check match
          if (next === firstPin) {
            handlePinMatch(next);
          } else {
            // Mismatch — reset
            setError(t('appLock.createPin.pinMismatch'));
            setTimeout(() => {
              setPhase('enter');
              setFirstPin('');
              setRepeatPin('');
              setError(null);
            }, 800);
          }
        }
      }
    },
    [phase, firstPin, repeatPin, t, handlePinMatch],
  );

  // ── Render ────────────────────────────────────────────────

  const title =
    phase === 'enter'
      ? t('appLock.createPin.enterTitle')
      : t('appLock.createPin.repeatTitle');

  const currentDigits = phase === 'enter' ? firstPin : repeatPin;

  return (
    <View style={styles.container}>
      <Text style={[styles.title, { color: colors.textPrimary }]}>{title}</Text>

      <View style={styles.dotsArea}>
        <PinDots count={currentDigits.length} isError={error !== null} />
      </View>

      <View style={styles.errorArea}>
        {error ? <Text style={[styles.error, { color: colors.status.destructive.main }]}>{error}</Text> : null}
      </View>

      <PinPad
        onDigitPress={handleDigitEnter}
        onDeletePress={handleDelete}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
    gap: spacing.xl,
  },
  title: {
    ...typography.title,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  dotsArea: {
    marginBottom: spacing.sm,
  },
  errorArea: {
    minHeight: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  error: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
});
