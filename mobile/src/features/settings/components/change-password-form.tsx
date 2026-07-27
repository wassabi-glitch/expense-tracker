import React, { useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { TextField } from 'heroui-native/text-field';
import { InputGroup } from 'heroui-native/input-group';
import { FieldError } from 'heroui-native/field-error';
import { Eye, EyeOff, Lock } from 'lucide-react-native';
import { darkColors, typography } from '@/theme';
import { useChangePasswordMutation } from '@/features/auth/api/auth-mutations';
import { useAuthStore } from '@/features/auth/hooks/use-auth-store';
import { useRateLimitGate } from '@/hooks/useRateLimitGate';

export type ChangePasswordFormProps = {
  formErrorOverride?: string | null;
  successMessageOverride?: string | null;
  isPendingOverride?: boolean;
};

export function ChangePasswordForm({
  formErrorOverride = null,
  successMessageOverride = null,
  isPendingOverride,
}: ChangePasswordFormProps = {}) {
  const { t } = useTranslation();
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [formErrorState, setFormErrorState] = useState<string | null>(null);
  const [successMessageState, setSuccessMessageState] = useState<string | null>(null);

  const formError = formErrorOverride ?? formErrorState;
  const successMessage = successMessageOverride ?? successMessageState;

  const changePasswordSchema = z.object({
    currentPassword: z.string().min(1, { message: t('auth.validation.required') }),
    newPassword: z.string()
      .min(8, { message: t('auth.validation.password.min') })
      .max(64, { message: t('auth.validation.password.max') })
      .regex(/[a-z]/, { message: t('auth.validation.password.lowercase') })
      .regex(/[A-Z]/, { message: t('auth.validation.password.uppercase') })
      .regex(/\d/, { message: t('auth.validation.password.number') })
      .regex(/[^\w\s]/, { message: t('auth.validation.password.special') }),
    confirmPassword: z.string(),
  }).refine((data) => data.newPassword === data.confirmPassword, {
    message: t('auth.validation.password.mismatch'),
    path: ['confirmPassword'],
  }).refine((data) => data.newPassword !== data.currentPassword, {
    message: t('auth.validation.password.must_differ'),
    path: ['newPassword'],
  });

  type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

  const { control, handleSubmit, formState: { errors }, reset } = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
    mode: 'onChange',
  });

  const changePasswordMutation = useChangePasswordMutation();
  const isPending = isPendingOverride !== undefined ? isPendingOverride : changePasswordMutation.isPending;

  const { isRateLimited, onRateLimitError } = useRateLimitGate({
    onExpire: () => setFormErrorState(null),
  });

  const onSubmit = async (values: ChangePasswordValues) => {
    setFormErrorState(null);
    setSuccessMessageState(null);
    try {
      const response = await changePasswordMutation.mutateAsync({
        current_password: values.currentPassword,
        new_password: values.newPassword,
      });
      await useAuthStore.getState().signIn(response.access_token, response.refresh_token);
      setSuccessMessageState(t('settings.changePasswordSuccess'));
      reset();
    } catch (e: any) {
      onRateLimitError(e);
      const msg = e?.response?.data?.detail || e?.message || t('common.errorOccurred');
      setFormErrorState(t(msg, { defaultValue: msg }));
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('settings.changePassword')}</Text>
      
      {formError && (
        <Text style={styles.errorText}>{t(formError, { defaultValue: formError })}</Text>
      )}

      {successMessage && (
        <Text style={styles.successText}>{successMessage}</Text>
      )}

      <View style={styles.formGroup}>
        <Controller
          control={control}
          name="currentPassword"
          render={({ field: { onChange, onBlur, value } }) => (
            <TextField isInvalid={!!errors.currentPassword}>
              <InputGroup>
                <InputGroup.Prefix isDecorative>
                  <Lock color={darkColors.textSecondary} size={20} />
                </InputGroup.Prefix>
                <InputGroup.Input
                  autoCapitalize="none"
                  autoCorrect={false}
                  onBlur={onBlur}
                  onChangeText={onChange}
                  placeholder={t('settings.currentPassword')}
                  secureTextEntry={!showCurrent}
                  testID="current-password-input"
                  value={value}
                />
                <InputGroup.Suffix>
                  <Button
                    accessibilityLabel={showCurrent ? t('auth.signIn.hidePassword') : t('auth.signIn.showPassword')}
                    isIconOnly
                    onPress={() => setShowCurrent(!showCurrent)}
                    size="md"
                    variant="ghost"
                  >
                    {showCurrent ? (
                      <EyeOff color={darkColors.textSecondary} size={20} />
                    ) : (
                      <Eye color={darkColors.textSecondary} size={20} />
                    )}
                  </Button>
                </InputGroup.Suffix>
              </InputGroup>
              <FieldError>{errors.currentPassword?.message}</FieldError>
            </TextField>
          )}
        />
      </View>

      <View style={styles.formGroup}>
        <Controller
          control={control}
          name="newPassword"
          render={({ field: { onChange, onBlur, value } }) => (
            <TextField isInvalid={!!errors.newPassword}>
              <InputGroup>
                <InputGroup.Prefix isDecorative>
                  <Lock color={darkColors.textSecondary} size={20} />
                </InputGroup.Prefix>
                <InputGroup.Input
                  autoCapitalize="none"
                  autoCorrect={false}
                  onBlur={onBlur}
                  onChangeText={onChange}
                  placeholder={t('settings.newPassword')}
                  secureTextEntry={!showNew}
                  testID="new-password-input"
                  value={value}
                />
                <InputGroup.Suffix>
                  <Button
                    accessibilityLabel={showNew ? t('auth.signIn.hidePassword') : t('auth.signIn.showPassword')}
                    isIconOnly
                    onPress={() => setShowNew(!showNew)}
                    size="md"
                    variant="ghost"
                  >
                    {showNew ? (
                      <EyeOff color={darkColors.textSecondary} size={20} />
                    ) : (
                      <Eye color={darkColors.textSecondary} size={20} />
                    )}
                  </Button>
                </InputGroup.Suffix>
              </InputGroup>
              <FieldError>{errors.newPassword?.message}</FieldError>
            </TextField>
          )}
        />
      </View>

      <View style={styles.formGroup}>
        <Controller
          control={control}
          name="confirmPassword"
          render={({ field: { onChange, onBlur, value } }) => (
            <TextField isInvalid={!!errors.confirmPassword}>
              <InputGroup>
                <InputGroup.Prefix isDecorative>
                  <Lock color={darkColors.textSecondary} size={20} />
                </InputGroup.Prefix>
                <InputGroup.Input
                  autoCapitalize="none"
                  autoCorrect={false}
                  onBlur={onBlur}
                  onChangeText={onChange}
                  placeholder={t('settings.confirmNewPassword')}
                  secureTextEntry={!showConfirm}
                  testID="confirm-password-input"
                  value={value}
                />
                <InputGroup.Suffix>
                  <Button
                    accessibilityLabel={showConfirm ? t('auth.signIn.hidePassword') : t('auth.signIn.showPassword')}
                    isIconOnly
                    onPress={() => setShowConfirm(!showConfirm)}
                    size="md"
                    variant="ghost"
                  >
                    {showConfirm ? (
                      <EyeOff color={darkColors.textSecondary} size={20} />
                    ) : (
                      <Eye color={darkColors.textSecondary} size={20} />
                    )}
                  </Button>
                </InputGroup.Suffix>
              </InputGroup>
              <FieldError>{errors.confirmPassword?.message}</FieldError>
            </TextField>
          )}
        />
      </View>

      <Button
        accessibilityLabel={t('settings.updatePassword')}
        accessibilityState={{ disabled: isPending, busy: isPending }}
        className="mt-4"
        isDisabled={isPending || isRateLimited}
        onPress={handleSubmit(onSubmit)}
        size="md"
        variant="primary"
      >
        <Button.Label>
          {t('settings.updatePassword')}
        </Button.Label>
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    backgroundColor: darkColors.screen,
    borderRadius: 8,
    marginBottom: 24,
  },
  title: {
    ...typography.title,
    color: darkColors.textPrimary,
    marginBottom: 16,
  },
  formGroup: {
    marginBottom: 12,
  },
  errorText: {
    color: '#ef4444',
    marginBottom: 16,
    textAlign: 'center',
  },
  successText: {
    color: '#22c55e',
    marginBottom: 16,
    textAlign: 'center',
  },
  buttonLabel: {
    color: darkColors.screen,
  }
});
