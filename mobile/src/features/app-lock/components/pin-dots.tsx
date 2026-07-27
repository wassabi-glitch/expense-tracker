import { useTranslation } from 'react-i18next';
import { StyleSheet, View } from 'react-native';
import { useTheme } from '@/hooks/use-theme';
import { radii, sizes, spacing } from '@/theme';

export type PinDotsProps = {
  /** Number of digits entered (0–5) */
  count: number;
  /** Total number of digits (default 5) */
  maxDigits?: number;
  /** Display error styling */
  isError?: boolean;
};

/**
 * Visual 5-dot indicator for PIN entry progress.
 * Theme-aware — uses system light/dark colors.
 */
export function PinDots({
  count,
  maxDigits = 5,
  isError = false,
}: PinDotsProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  const dotColor = isError
    ? colors.status.destructive.main
    : colors.brand.action;

  const unfilledColor = colors.borderSubtle;

  return (
    <View
      accessibilityLabel={t(
        'appLock.lockScreen.pinDotsLabel',
        { count, maxDigits },
      )}
      accessibilityRole="text"
      style={styles.row}
    >
      {Array.from({ length: maxDigits }, (_, i) => (
        <View
          key={i}
          style={[
            styles.dot,
            {
              backgroundColor: i < count ? dotColor : 'transparent',
              borderColor: i < count ? dotColor : unfilledColor,
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.md,
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: sizes.touchTarget.minimumHeight,
  },
  dot: {
    width: 16,
    height: 16,
    borderRadius: radii.full,
    borderWidth: 2,
  },
});
