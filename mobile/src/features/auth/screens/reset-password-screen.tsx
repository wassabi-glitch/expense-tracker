import { useMemo, useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Text, View } from 'react-native';
import { Button } from '@/components/ui/button';
import { FieldError } from 'heroui-native/field-error';
import { InputGroup } from 'heroui-native/input-group';
import { Spinner } from 'heroui-native/spinner';
import { TextField } from 'heroui-native/text-field';
import { AlertCircle, CheckCircle2, Eye, EyeOff, Lock } from 'lucide-react-native';

import { darkColors, sizes } from '@/theme';
import { AuthScreenLayout } from '../components/auth-screen-layout';
import { PasswordRequirementList } from '../components/password-requirement-list';
import { arePasswordRequirementsMet, evaluatePasswordRequirements } from '../components/sign-up-ui-rules';
import { zodResolver } from '@hookform/resolvers/zod';
import { resetPasswordSchema, ResetPasswordValues } from '../schemas/reset-password-schema';

export type ResetPasswordState = 'ready' | 'loading' | 'success' | 'error';

export type ResetPasswordScreenProps = {
  resetPasswordState?: ResetPasswordState;
  formError?: string; // used for non-global inline errors (e.g., rate limits) or just passed through
  isRateLimited?: boolean;
  previewTextScale?: number;
  onResetPasswordPress?: (values: ResetPasswordValues) => void;
  onContinueToSignInPress?: () => void;
  onRequestNewLinkPress?: () => void;
};

export function ResetPasswordScreen({
  resetPasswordState = 'ready',
  formError,
  isRateLimited = false,
  previewTextScale = 1,
  onResetPasswordPress = () => {},
  onContinueToSignInPress = () => {},
  onRequestNewLinkPress = () => {},
}: ResetPasswordScreenProps) {
  const { t } = useTranslation();
  const [passwordVisible, setPasswordVisible] = useState(false);
  const resetHandledRef = useRef(false);

  const { control, watch, handleSubmit, formState } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '' },
    mode: 'onChange',
  });

  const password = watch('password');
  const passwordRequirements = useMemo(() => evaluatePasswordRequirements(password, ''), [password]);
  const isPending = resetPasswordState === 'loading';
  const isSuccess = resetPasswordState === 'success';
  const isError = resetPasswordState === 'error';

  // Make sure all requirements are met
  const passwordReady = arePasswordRequirementsMet(passwordRequirements) && !formState.errors.password;
  const resetDisabled = !passwordReady || isPending || isRateLimited;

  const handleResetPassword = (values: ResetPasswordValues) => {
    if (!passwordReady || isPending || resetHandledRef.current) return;
    resetHandledRef.current = true;
    onResetPasswordPress(values);
  };

  const submitForm = handleSubmit(handleResetPassword);

  if (isSuccess || isError) {
    const title = isSuccess ? t('auth.resetPassword.successTitle') : t('auth.verifyAccount.errorTitle'); // "Link Expired or Invalid" or similar
    const body = isSuccess ? t('auth.resetPassword.successBody') : (formError ? t(formError as any) : t('auth.verifyAccount.errorBody'));
    const Icon = isSuccess ? CheckCircle2 : AlertCircle;
    const iconColor = isSuccess ? darkColors.status.success.main : darkColors.status.destructive.main;

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
          {isSuccess ? (
            <Button
              className="w-full"
              onPress={onContinueToSignInPress}
              size="md"
              variant="primary"
            >
              {t('auth.resetPassword.continueToSignIn')}
            </Button>
          ) : (
            <Button
              className="w-full"
              onPress={onRequestNewLinkPress}
              size="md"
              variant="secondary"
            >
              <Button.Label style={{ color: darkColors.textPrimary }}>
                {t('auth.verifyAccount.requestNewLink')}
              </Button.Label>
            </Button>
          )}
        </View>
      </AuthScreenLayout>
    );
  }

  return (
    <AuthScreenLayout
      previewTextScale={previewTextScale}
      supportingText={t('auth.resetPassword.body')}
      title={t('auth.resetPassword.title')}
    >
      <View className="gap-6 mt-2">
        <View className="gap-4">
          <Controller
            control={control}
            name="password"
            render={({ field: { onBlur, onChange, value } }) => (
              <TextField isInvalid={!!formState.errors.password} isRequired>
                <InputGroup>
                  <InputGroup.Prefix isDecorative>
                    <Lock color={darkColors.textSecondary} size={16} />
                  </InputGroup.Prefix>
                  <InputGroup.Input
                    accessibilityLabel={t('auth.resetPassword.passwordLabel')}
                    autoCapitalize="none"
                    autoComplete="new-password"
                    onBlur={onBlur}
                    onChangeText={onChange}
                    placeholder={t('auth.resetPassword.passwordPlaceholder')}
                    secureTextEntry={!passwordVisible}
                    textContentType="newPassword"
                    value={value}
                  />
                  <InputGroup.Suffix>
                    <Button
                      accessibilityLabel={
                        passwordVisible
                          ? t('auth.resetPassword.hidePassword')
                          : t('auth.resetPassword.showPassword')
                      }
                      isIconOnly
                      onPress={() => setPasswordVisible(!passwordVisible)}
                      size="md"
                      variant="ghost"
                    >
                      {passwordVisible ? (
                        <EyeOff
                          aria-hidden={true}
                          color={darkColors.textSecondary}
                          size={sizes.button.icon}
                        />
                      ) : (
                        <Eye
                          aria-hidden={true}
                          color={darkColors.textSecondary}
                          size={sizes.button.icon}
                        />
                      )}
                    </Button>
                  </InputGroup.Suffix>
                </InputGroup>
                {formState.errors.password ? (
                  <FieldError>
                    {t(formState.errors.password.message as any)}
                  </FieldError>
                ) : null}
              </TextField>
            )}
          />

          <PasswordRequirementList
            previewTextScale={previewTextScale}
            requirements={passwordRequirements}
            touched={password.length > 0}
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
                ? t('auth.resetPassword.resettingPassword')
                : t('auth.resetPassword.resetPassword')
            }
            accessibilityState={{ busy: isPending, disabled: resetDisabled }}
            animation={isPending ? { scale: false, highlight: false } : undefined}
            className="w-full"
            isDisabled={resetDisabled}
            onPress={isPending ? undefined : submitForm}
            size="md"
            variant="primary"
          >
            {isPending ? (
              <View className="flex-row items-center justify-center gap-2">
                <Spinner color={darkColors.brand?.onAction ?? '#052E16'} size="sm" />
                <Button.Label>{t('auth.resetPassword.resettingPassword')}</Button.Label>
              </View>
            ) : (
              t('auth.resetPassword.resetPassword')
            )}
          </Button>
        </View>
      </View>
    </AuthScreenLayout>
  );
}
