import { StyleSheet, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useTheme } from '@/hooks/use-theme';
import { useAppLockStore } from '../hooks/use-app-lock';
import { LockScreenContent } from './lock-screen-content';
import { PinCreateFlow } from './pin-create-flow';
import { PasswordVerifyScreen } from './password-verify-screen';

/**
 * Full-screen overlay that sits above the entire app when locked.
 * Renders the correct child based on the app lock state machine:
 *
 * - isSettingUp                              → PinCreateFlow (first-time PIN setup)
 * - cooldown expired & password not verified → PasswordVerifyScreen
 * - isLocked (cooldown or normal)            → LockScreenContent
 * - otherwise                                → null (hidden, app visible)
 */
export function AppLockOverlay() {
  const { colors, mode } = useTheme();
  const {
    isLocked,
    isSettingUp,
    pinExists,
    cooldownRemaining,
    cooldownUntil,
    passwordVerified,
    failedAttempts,
    appLockEnabled,
    changePinMode,
  } = useAppLockStore();

  // Master toggle — when App Lock is disabled, no overlay at all
  if (!appLockEnabled && !changePinMode) return null;

  // Show overlay when locked OR when user needs to set up a PIN
  if (!isLocked && !isSettingUp) return null;

  const cooldownActive = cooldownUntil !== null && cooldownRemaining > 0;
  const cooldownExpired = cooldownUntil !== null && cooldownRemaining <= 0;
  const maxAttemptsReached = failedAttempts >= 5;
  const needsPasswordVerification =
    (cooldownExpired || (maxAttemptsReached && !cooldownActive)) &&
    !passwordVerified &&
    !pinExists;

  return (
    <View
      style={[styles.overlay, { backgroundColor: colors.screen }]}
      testID="app-lock-overlay"
    >
      <StatusBar style={mode === 'dark' ? 'light' : 'dark'} />

      {changePinMode ? (
        <PinCreateFlow hideBioOffer />
      ) : isSettingUp && !cooldownActive && !cooldownExpired ? (
        <PinCreateFlow />
      ) : needsPasswordVerification ? (
        <PasswordVerifyScreen />
      ) : (
        <LockScreenContent />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 9999, // above everything
    elevation: 9999, // Android
  },
});
