import { useTranslation } from 'react-i18next';
import { Text, View } from 'react-native';
import { Check, Circle } from 'lucide-react-native';

import { spacing, typography } from '@/theme';
import { palette } from '@/theme/palette';
import { useAppTheme } from '@/providers/theme-provider';

import type {
  PasswordRequirementKey,
  PasswordRequirementState,
} from './sign-up-ui-rules';

const requirementOrder: PasswordRequirementKey[] = [
  'length',
  'lowercase',
  'uppercase',
  'number',
  'special',
  'noSpaces',
  'excludesEmail',
];

type PasswordRequirementListProps = {
  requirements: PasswordRequirementState;
  touched: boolean;
  previewTextScale?: number;
};

export function PasswordRequirementList({
  requirements,
  touched,
  previewTextScale = 1,
}: PasswordRequirementListProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  return (
    <View
      accessibilityLabel={t('auth.signUp.requirementsLabel')}
      className="gap-2"
    >
      <Text
        style={[
          typography.supporting,
          { color: colors.textPrimary, marginBottom: spacing.xxs },
          previewTextScale !== 1
            ? {
                fontSize: typography.supporting.fontSize * previewTextScale,
                lineHeight: typography.supporting.lineHeight * previewTextScale,
              }
            : null,
        ]}
      >
        {t('auth.signUp.requirementsLabel')}
      </Text>
      {requirementOrder.map((key) => {
        const isMet = touched && requirements[key];
        const label = t(`auth.signUp.rules.${key}`);
        const stateLabel = isMet
          ? t('auth.signUp.requirementMet')
          : t('auth.signUp.requirementUnmet');

        return (
          <View
            accessible
            accessibilityLabel={`${label}. ${stateLabel}`}
            className="flex-row items-center gap-3"
            key={key}
          >
            <View className="w-5 items-center justify-center">
              {isMet ? (
                <Check
                  accessibilityElementsHidden
                  color={palette.emerald400}
                  importantForAccessibility="no-hide-descendants"
                  size={16}
                />
              ) : (
                <Circle
                  accessibilityElementsHidden
                  color={colors.textSecondary}
                  importantForAccessibility="no-hide-descendants"
                  size={16}
                />
              )}
            </View>
            <Text
              style={[
                typography.supporting,
                {
                  flex: 1,
                  color: isMet ? colors.textPrimary : colors.textSecondary,
                },
                previewTextScale !== 1
                  ? {
                      fontSize: typography.supporting.fontSize * previewTextScale,
                      lineHeight: typography.supporting.lineHeight * previewTextScale,
                    }
                  : null,
              ]}
            >
              {label}
            </Text>
          </View>
        );
      })}
    </View>
  );
}
