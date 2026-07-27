import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { ReactNode } from 'react';
import { Delete } from 'lucide-react-native';
import { useTheme } from '@/hooks/use-theme';
import { spacing, typography } from '@/theme';

export type PinPadProps = {
  onDigitPress?: (digit: number) => void;
  onDeletePress?: () => void;
  isDisabled?: boolean;
  /** Optional slot rendered in the bottom-left cell (replaces empty placeholder). Use for fingerprint icon. */
  biometricSlot?: ReactNode;
  /** Called when the biometric slot is pressed. Required when biometricSlot is provided for accessibility. */
  onBiometricPress?: () => void;
};

const DIGIT_ROWS = [
  [1, 2, 3],
  [4, 5, 6],
  [7, 8, 9],
  [-1, 0, -2], // -1 = empty, -2 = backspace
] as const;

/**
 * Custom 3×4 number pad for PIN entry.
 * Theme-aware — uses system light/dark colors.
 * Every button has a minimum 48×48 touch target per project accessibility rules.
 */
export function PinPad({
  onDigitPress = () => {},
  onDeletePress = () => {},
  isDisabled = false,
  biometricSlot = null,
  onBiometricPress = () => {},
}: PinPadProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  const keyBackground = colors.surface;
  const keyTextColor = colors.textPrimary;
  const keyPressedBackground = colors.borderSubtle;

  return (
    <View style={styles.container} accessibilityRole="none">
      {DIGIT_ROWS.map((row, rowIndex) => (
        <View key={rowIndex} style={styles.row}>
          {row.map((key) => {
            if (key === -1) {
              // Biometric slot or empty placeholder (bottom-left)
              if (biometricSlot) {
                return (
                  <Pressable
                    key="biometric"
                    accessibilityLabel={t(
                      'appLock.lockScreen.biometricButton',
                      { defaultValue: 'Use fingerprint' },
                    )}
                    accessibilityRole="button"
                    disabled={isDisabled}
                    onPress={() => onBiometricPress()}
                    style={({ pressed }) => [
                      styles.key,
                      {
                        backgroundColor: pressed
                          ? keyPressedBackground
                          : keyBackground,
                        opacity: isDisabled ? 0.4 : 1,
                      },
                    ]}
                  >
                    {biometricSlot}
                  </Pressable>
                );
              }
              return <View key="empty" style={styles.key} />;
            }

            if (key === -2) {
              // Backspace
              return (
                <Pressable
                  key="backspace"
                  accessibilityLabel={t(
                    'appLock.lockScreen.backspace',
                    { defaultValue: 'Delete last digit' },
                  )}
                  accessibilityRole="button"
                  disabled={isDisabled}
                  onPress={() => onDeletePress()}
                  style={({ pressed }) => [
                    styles.key,
                    {
                      backgroundColor: pressed
                        ? keyPressedBackground
                        : keyBackground,
                      opacity: isDisabled ? 0.4 : 1,
                    },
                  ]}
                >
                  <Delete
                    color={keyTextColor}
                    size={24}
                    strokeWidth={2}
                  />
                </Pressable>
              );
            }

            // Digit
            return (
              <Pressable
                key={key}
                accessibilityLabel={String(key)}
                accessibilityRole="button"
                disabled={isDisabled}
                onPress={() => onDigitPress(key)}
                style={({ pressed }) => [
                  styles.key,
                  {
                    backgroundColor: pressed
                      ? keyPressedBackground
                      : keyBackground,
                    opacity: isDisabled ? 0.4 : 1,
                  },
                ]}
              >
                <Text
                  style={[
                    typography.authTitle,
                    {
                      color: keyTextColor,
                      textAlign: 'center',
                    },
                  ]}
                >
                  {key}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
    alignItems: 'center',
  },
  row: {
    flexDirection: 'row',
    gap: spacing.md,
    justifyContent: 'center',
  },
  key: {
    width: 72,
    minWidth: 48,
    height: 60,
    minHeight: 48,
    borderRadius: 30,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
