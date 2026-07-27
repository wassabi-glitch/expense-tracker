import { useTranslation } from 'react-i18next';
import { View } from 'react-native';
import { Button } from '@/components/ui/button';
import { Spinner } from 'heroui-native/spinner';
import { CheckCircle2, AlertCircle, ShieldCheck } from 'lucide-react-native';

import { darkColors } from '@/theme';
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
};

export function VerifyAccountScreen({
  verifyState = 'ready',
  customErrorMessage,
  isRateLimited = false,
  previewTextScale = 1,
  onVerifyPress = () => {},
  onContinueToSignInPress = () => {},
  onRequestNewLinkPress = () => {},
}: VerifyAccountScreenProps) {
  const { t } = useTranslation();

  const isReady = verifyState === 'ready';
  const isLoading = verifyState === 'loading';
  const isSuccess = verifyState === 'success';
  const isError = verifyState === 'error';

  let title = t('auth.verifyAccount.readyTitle');
  let body = t('auth.verifyAccount.readyBody');
  let Icon = ShieldCheck;
  let iconColor: string = darkColors.textPrimary;

  if (isSuccess) {
    title = t('auth.verifyAccount.successTitle');
    body = t('auth.verifyAccount.successBody');
    Icon = CheckCircle2;
    iconColor = darkColors.status.success.main;
  } else if (isError) {
    title = t('auth.verifyAccount.errorTitle');
    body = customErrorMessage ? t(customErrorMessage) : t('auth.verifyAccount.errorBody');
    Icon = AlertCircle;
    iconColor = darkColors.status.destructive.main;
  }

  return (
    <AuthScreenLayout
      previewTextScale={previewTextScale}
      supportingText={body}
      title={title}
    >
      <View className="items-center justify-center py-6">
        <Icon color={iconColor} size={64} strokeWidth={1.5} />
      </View>

      <View className="gap-4 mt-2">
        {(isReady || isLoading) && (
          <Button
            accessibilityLabel={
              isLoading
                ? t('auth.verifyAccount.verifying')
                : t('auth.verifyAccount.verifyAccount')
            }
            accessibilityState={{ busy: isLoading, disabled: isLoading }}
            className="w-full"
            isDisabled={isLoading || isRateLimited}
            onPress={isLoading ? undefined : onVerifyPress}
            size="md"
            variant="primary"
          >
            {isLoading ? (
              <View className="flex-row items-center justify-center gap-2">
                <Spinner color={darkColors.brand?.onAction ?? '#052E16'} size="sm" />
                <Button.Label>{t('auth.verifyAccount.verifying')}</Button.Label>
              </View>
            ) : (
              t('auth.verifyAccount.verifyAccount')
            )}
          </Button>
        )}

        {isSuccess && (
          <Button
            className="w-full"
            onPress={onContinueToSignInPress}
            size="md"
            variant="primary"
          >
            {t('auth.verifyAccount.continueToSignIn')}
          </Button>
        )}

        {isError && (
          <Button
            className="w-full"
            onPress={onRequestNewLinkPress}
            size="md"
            variant="secondary"
          >
            <Button.Label style={{ color: darkColors.textPrimary }}>{t('auth.verifyAccount.requestNewLink')}</Button.Label>
          </Button>
        )}
      </View>
    </AuthScreenLayout>
  );
}
