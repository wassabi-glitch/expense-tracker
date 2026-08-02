import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { AppButton } from '@/components/ui/app-button';
import { Mailbox } from 'lucide-react-native';
import { useAppTheme } from '@/providers/theme-provider';
import { AuthScreenLayout } from '../components/auth-screen-layout';

export type CheckEmailActionState = 'default' | 'pending' | 'countdown';

export type CheckEmailScreenProps = {
  resendState?: CheckEmailActionState;
  resendCountdownSeconds?: number;
  isRateLimited?: boolean;
  initialSendFailed?: boolean;
  previewTextScale?: number;
  onResendPress?: () => void;
  onBack?: () => void;
};

export function CheckEmailScreen({
  resendState = 'default',
  resendCountdownSeconds = 0,
  isRateLimited = false,
  initialSendFailed = false,
  previewTextScale = 1,
  onResendPress = () => {},
  onBack = () => {},
}: CheckEmailScreenProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  const isResending = resendState === 'pending';
  const isCountdown = resendState === 'countdown';
  const resendDisabled = isResending || isCountdown || isRateLimited;

  const body = initialSendFailed
    ? t('auth.checkEmail.bodyRetry')
    : t('auth.checkEmail.body');

  return (
    <AuthScreenLayout
      backLabel={t('common.back')}
      onBack={onBack}
      previewTextScale={previewTextScale}
      supportingText={body}
      title={t('auth.checkEmail.title')}
    >
      <View className="items-center justify-center py-6">
        <Mailbox color={colors.textPrimary} size={64} strokeWidth={1.5} />
      </View>

      <View className="gap-4 mt-2">
        <AppButton
          accessibilityLabel={
            isRateLimited
              ? t('auth.checkEmail.errors.rateLimited')
              : isResending
                ? t('auth.checkEmail.resendingLink')
                : isCountdown
                  ? t('auth.checkEmail.resendCountdown', { seconds: resendCountdownSeconds })
                  : t('auth.checkEmail.resendLink')
          }
          className="w-full"
          isDisabled={resendDisabled}
          isLoading={isResending && !isRateLimited}
          onPress={onResendPress}
          size="md"
          variant={isRateLimited ? 'danger-soft' : 'tertiary'}
        >
          {isRateLimited
            ? t('auth.checkEmail.errors.rateLimited')
            : isResending
              ? t('auth.checkEmail.resendingLink')
              : isCountdown
                ? t('auth.checkEmail.resendCountdown', { seconds: resendCountdownSeconds })
                : t('auth.checkEmail.resendLink')}
        </AppButton>

        <AppButton
          className="w-full"
          onPress={onBack}
          size="md"
          variant="ghost"
        >
          {t('auth.checkEmail.backToSignIn')}
        </AppButton>
      </View>
    </AuthScreenLayout>
  );
}
