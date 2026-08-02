import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { AppButton } from '@/components/ui/app-button';
import { CheckCircle2, AlertCircle, ShieldCheck } from 'lucide-react-native';
import { useAppTheme } from '@/providers/theme-provider';
import { palette } from '@/theme/palette';
import { AuthScreenLayout } from '../components/auth-screen-layout';

export type VerifyAccountState = 'ready' | 'loading' | 'success' | 'error';

export type VerifyAccountScreenProps = {
  verifyState?: VerifyAccountState;
  customErrorMessage?: string;
  isRateLimited?: boolean;
  previewTextScale?: number;
  onVerifyPress?: () => void;
  onContinueToSignInPress?: () => void;
  onRequestNewLinkPress?: () => void;
  onBack?: () => void;
};

export function VerifyAccountScreen({
  verifyState = 'ready',
  customErrorMessage,
  isRateLimited = false,
  previewTextScale = 1,
  onVerifyPress = () => {},
  onContinueToSignInPress = () => {},
  onRequestNewLinkPress = () => {},
  onBack = () => {},
}: VerifyAccountScreenProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();

  const isReady = verifyState === 'ready';
  const isLoading = verifyState === 'loading';
  const isSuccess = verifyState === 'success';
  const isError = verifyState === 'error';

  let title = t('auth.verifyAccount.readyTitle');
  let body = t('auth.verifyAccount.readyBody');
  let Icon = ShieldCheck;
  let iconColor: string = colors.textPrimary;

  if (isSuccess) {
    title = t('auth.verifyAccount.successTitle');
    body = t('auth.verifyAccount.successBody');
    Icon = CheckCircle2;
    iconColor = palette.emerald400;
  } else if (isError) {
    title = t('auth.verifyAccount.errorTitle');
    body = customErrorMessage ? t(customErrorMessage) : t('auth.verifyAccount.errorBody');
    Icon = AlertCircle;
    iconColor = colors.status.destructive.main;
  }

  return (
    <AuthScreenLayout
      backLabel={t('common.back')}
      onBack={onBack}
      previewTextScale={previewTextScale}
      supportingText={body}
      title={title}
    >
      <View className="items-center justify-center py-6">
        <Icon color={iconColor} size={64} strokeWidth={1.5} />
      </View>

      <View className="gap-4 mt-2">
        {(isReady || isLoading) && (
          <AppButton
            accessibilityLabel={
              isLoading
                ? t('auth.verifyAccount.verifying')
                : t('auth.verifyAccount.verifyAccount')
            }
            className="w-full"
            isDisabled={isRateLimited}
            isLoading={isLoading}
            onPress={onVerifyPress}
            size="md"
            variant="primary"
          >
            {isLoading
              ? t('auth.verifyAccount.verifying')
              : t('auth.verifyAccount.verifyAccount')}
          </AppButton>
        )}

        {isSuccess && (
          <AppButton
            className="w-full"
            onPress={onContinueToSignInPress}
            size="md"
            variant="primary"
          >
            {t('auth.verifyAccount.continueToSignIn')}
          </AppButton>
        )}

        {isError && (
          <AppButton
            className="w-full"
            onPress={onRequestNewLinkPress}
            size="md"
            variant="ghost"
          >
            {t('auth.verifyAccount.requestNewLink')}
          </AppButton>
        )}
      </View>
    </AuthScreenLayout>
  );
}
