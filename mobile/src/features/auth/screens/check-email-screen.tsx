import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { Button } from '@/components/ui/button';
import { Spinner } from 'heroui-native/spinner';
import { Mailbox } from 'lucide-react-native';

import { darkColors } from '@/theme';
import { AuthScreenLayout } from '../components/auth-screen-layout';

export type CheckEmailActionState = 'default' | 'pending' | 'countdown';

export type CheckEmailScreenProps = {
  resendState?: CheckEmailActionState;
  resendCountdownSeconds?: number;
  isRateLimited?: boolean;
  previewTextScale?: number;
  onResendPress?: () => void;
  onBackToSignInPress?: () => void;
};

export function CheckEmailScreen({
  resendState = 'default',
  resendCountdownSeconds = 0,
  isRateLimited = false,
  previewTextScale = 1,
  onResendPress = () => {},
  onBackToSignInPress = () => {},
}: CheckEmailScreenProps) {
  const { t } = useTranslation();

  const isResending = resendState === 'pending';
  const isCountdown = resendState === 'countdown';
  const resendDisabled = isResending || isCountdown || isRateLimited;

  return (
    <AuthScreenLayout
      previewTextScale={previewTextScale}
      supportingText={t('auth.checkEmail.body')}
      title={t('auth.checkEmail.title')}
    >
      <View className="items-center justify-center py-6">
        <Mailbox color={darkColors.textPrimary} size={64} strokeWidth={1.5} />
      </View>

      <View className="gap-4 mt-2">
        <Button
          accessibilityLabel={
            isResending
              ? t('auth.checkEmail.resendingLink')
              : isCountdown
                ? t('auth.checkEmail.resendCountdown', { seconds: resendCountdownSeconds })
                : t('auth.checkEmail.resendLink')
          }
          accessibilityState={{ busy: isResending, disabled: resendDisabled }}
          className="w-full"
          isDisabled={resendDisabled}
          onPress={resendDisabled ? undefined : onResendPress}
          size="md"
          variant="secondary"
        >
          {isResending ? (
            <View className="flex-row items-center justify-center gap-2">
              <Spinner color={darkColors.textPrimary} size="sm" />
              <Button.Label style={{ color: darkColors.textPrimary }}>{t('auth.checkEmail.resendingLink')}</Button.Label>
            </View>
          ) : isCountdown ? (
            <Button.Label style={{ color: darkColors.textPrimary }}>{t('auth.checkEmail.resendCountdown', { seconds: resendCountdownSeconds })}</Button.Label>
          ) : (
            <Button.Label style={{ color: darkColors.textPrimary }}>{t('auth.checkEmail.resendLink')}</Button.Label>
          )}
        </Button>

        <Button
          className="w-full"
          onPress={onBackToSignInPress}
          size="md"
          variant="ghost"
        >
          <Button.Label style={{ color: darkColors.textPrimary }}>{t('auth.checkEmail.backToSignIn')}</Button.Label>
        </Button>
      </View>
    </AuthScreenLayout>
  );
}
