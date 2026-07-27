import { useRef } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';
import { Button } from '@/components/ui/button';
import { FieldError } from 'heroui-native/field-error';
import { InputGroup } from 'heroui-native/input-group';
import { Spinner } from 'heroui-native/spinner';
import { TextField } from 'heroui-native/text-field';
import { CheckCircle2, Mail } from 'lucide-react-native';

import { darkColors } from '@/theme';
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
  onBackToSignInPress?: () => void;
};

export function ForgotPasswordScreen({
  initialValues = {},
  forgotPasswordState = 'ready',
  formError,
  isRateLimited = false,
  previewTextScale = 1,
  onSendLinkPress = () => {},
  onBackToSignInPress = () => {},
}: ForgotPasswordScreenProps) {
  const { t } = useTranslation();
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
        previewTextScale={previewTextScale}
        supportingText={t('auth.forgotPassword.successBody')}
        title={t('auth.forgotPassword.successTitle')}
      >
        <View className="items-center justify-center py-6">
          <CheckCircle2 color={darkColors.status.success.main} size={64} strokeWidth={1.5} />
        </View>

        <View className="gap-4 mt-2">
          <Button
            className="w-full"
            onPress={onBackToSignInPress}
            size="md"
            variant="secondary"
          >
            <Button.Label style={{ color: darkColors.textPrimary }}>
              {t('auth.forgotPassword.backToSignIn')}
            </Button.Label>
          </Button>
        </View>
      </AuthScreenLayout>
    );
  }

  return (
    <AuthScreenLayout
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
                    <Mail color={darkColors.textSecondary} size={16} />
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

        {formError ? (
          <Text style={{ color: darkColors.status.destructive.main, fontSize: 14, fontWeight: '500', textAlign: 'center' }}>
            {t(formError as any)}
          </Text>
        ) : null}

        <View className="gap-4 mt-2">
          <Button
            accessibilityLabel={
              isPending
                ? t('auth.forgotPassword.sendingLink')
                : t('auth.forgotPassword.sendLink')
            }
            accessibilityState={{ busy: isPending, disabled: sendDisabled }}
            animation={isPending ? { scale: false, highlight: false } : undefined}
            className="w-full"
            isDisabled={sendDisabled}
            onPress={isPending ? undefined : submitForm}
            size="md"
            variant="primary"
          >
            {isPending ? (
              <View className="flex-row items-center justify-center gap-2">
                <Spinner color={darkColors.brand?.onAction ?? '#052E16'} size="sm" />
                <Button.Label>{t('auth.forgotPassword.sendingLink')}</Button.Label>
              </View>
            ) : (
              t('auth.forgotPassword.sendLink')
            )}
          </Button>

          <Button
            className="w-full"
            onPress={onBackToSignInPress}
            size="md"
            variant="ghost"
          >
            <Button.Label style={{ color: darkColors.textPrimary }}>
              {t('auth.forgotPassword.backToSignIn')}
            </Button.Label>
          </Button>
        </View>
      </View>
    </AuthScreenLayout>
  );
}
