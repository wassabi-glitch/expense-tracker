import { useRef } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';
import { AppButton } from '@/components/ui/app-button';
import { FieldError } from 'heroui-native/field-error';
import { InputGroup } from 'heroui-native/input-group';
import { TextField } from 'heroui-native/text-field';
import { CheckCircle2, Mail } from 'lucide-react-native';

import { useAppTheme } from '@/providers/theme-provider';
import { palette } from '@/theme/palette';
import { AuthScreenLayout } from '../components/auth-screen-layout';
import { zodResolver } from '@hookform/resolvers/zod';
import { forgotPasswordSchema, ForgotPasswordValues } from '../schemas/forgot-password-schema';

export type ForgotPasswordState = 'ready' | 'loading' | 'success';

export type ForgotPasswordScreenProps = {
  initialValues?: Partial<ForgotPasswordValues>;
  forgotPasswordState?: ForgotPasswordState;
  formError?: string;
  isRateLimited?: boolean;
  previewTextScale?: number;
  onSendLinkPress?: (values: ForgotPasswordValues) => void;
  onBack?: () => void;
};

export function ForgotPasswordScreen({
  initialValues = {},
  forgotPasswordState = 'ready',
  formError,
  isRateLimited = false,
  previewTextScale = 1,
  onSendLinkPress = () => {},
  onBack = () => {},
}: ForgotPasswordScreenProps) {
  const { t } = useTranslation();
  const { colors } = useAppTheme();
  const sendHandledRef = useRef(false);

  const { control, watch, handleSubmit, formState } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: initialValues.email ?? '',
    },
    mode: 'onChange',
  });

  const email = watch('email');
  const formReady = !formState.errors.email && email.length > 0;
  const isPending = forgotPasswordState === 'loading';
  const isSuccess = forgotPasswordState === 'success';
  const sendDisabled = !formReady || isPending || isRateLimited;

  const handleSendLink = (values: ForgotPasswordValues) => {
    if (!formReady || isPending || sendHandledRef.current) return;
    sendHandledRef.current = true;
    onSendLinkPress(values);
  };

  const submitForm = handleSubmit(handleSendLink);

  if (isSuccess) {
    return (
      <AuthScreenLayout
        backLabel={t('common.back')}
        onBack={onBack}
        previewTextScale={previewTextScale}
        supportingText={t('auth.forgotPassword.successBody')}
        title={t('auth.forgotPassword.successTitle')}
      >
        <View className="items-center justify-center py-6">
          <CheckCircle2 color={palette.emerald400} size={64} strokeWidth={1.5} />
        </View>

        <View className="gap-4 mt-2">
          <AppButton
            className="w-full"
            onPress={onBack}
            size="md"
            variant="ghost"
          >
            {t('auth.forgotPassword.backToSignIn')}
          </AppButton>
        </View>
      </AuthScreenLayout>
    );
  }

  return (
    <AuthScreenLayout
      backLabel={t('common.back')}
      onBack={onBack}
      previewTextScale={previewTextScale}
      supportingText={t('auth.forgotPassword.body')}
      title={t('auth.forgotPassword.title')}
    >
      <View className="gap-6 mt-2">
        <View className="gap-4">
          <Controller
            control={control}
            name="email"
            render={({ field: { onBlur, onChange, value } }) => (
              <TextField isInvalid={!!formState.errors.email} isRequired>
                <InputGroup>
                  <InputGroup.Prefix isDecorative>
                    <Mail color={colors.textSecondary} size={16} />
                  </InputGroup.Prefix>
                  <InputGroup.Input
                    accessibilityLabel={t('auth.forgotPassword.emailLabel')}
                    autoCapitalize="none"
                    autoComplete="email"
                    inputMode="email"
                    keyboardType="email-address"
                    onBlur={onBlur}
                    onChangeText={onChange}
                    placeholder={t('auth.forgotPassword.emailPlaceholder')}
                    returnKeyType="done"
                    textContentType="emailAddress"
                    value={value}
                  />
                </InputGroup>
                {formState.errors.email ? (
                  <FieldError>
                    {t(formState.errors.email.message as any)}
                  </FieldError>
                ) : null}
              </TextField>
            )}
          />
        </View>

        <View className="gap-4 mt-2">
          <AppButton
            accessibilityLabel={
              isRateLimited
                ? (formError || t('auth.forgotPassword.errors.rateLimited'))
                : isPending
                  ? t('auth.forgotPassword.sendingLink')
                  : t('auth.forgotPassword.sendLink')
            }
            className="w-full"
            isDisabled={sendDisabled}
            isLoading={isPending && !isRateLimited}
            onPress={submitForm}
            size="md"
            variant={isRateLimited ? 'danger-soft' : 'primary'}
          >
            {isRateLimited
              ? (formError || t('auth.forgotPassword.errors.rateLimited'))
              : isPending
                ? t('auth.forgotPassword.sendingLink')
                : t('auth.forgotPassword.sendLink')}
          </AppButton>

          <AppButton
            className="w-full"
            onPress={onBack}
            size="md"
            variant="ghost"
          >
            {t('auth.forgotPassword.backToSignIn')}
          </AppButton>
        </View>
      </View>
    </AuthScreenLayout>
  );
}
