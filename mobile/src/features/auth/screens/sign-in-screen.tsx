/* eslint-disable @typescript-eslint/no-unused-vars, react-hooks/incompatible-library */
import { useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Image, StyleSheet, Text, View, Pressable } from 'react-native';
import { Button } from '@/components/ui/button';
import { FieldError } from 'heroui-native/field-error';
import { Input } from 'heroui-native/input';
import { InputGroup } from 'heroui-native/input-group';
import { Spinner } from 'heroui-native/spinner';
import { TextField } from 'heroui-native/text-field';
import { Eye, EyeOff, Lock, Mail } from 'lucide-react-native';

import {
  authPresentationColors,
  darkColors,
  sizes,
  spacing,
  typography,
} from '@/theme';

import { AuthScreenLayout, useAuthLayout } from '../components/auth-screen-layout';
import { zodResolver } from '@hookform/resolvers/zod';
import { signInSchema, SignInValues } from '../schemas/sign-in-schema';

export type SignInVisualState = 'default' | 'pressed' | 'unavailable' | 'pending';
export type SignInActionState = 'default' | 'pressed' | 'pending';


export type SignInScreenProps = {
  initialValues?: Partial<SignInValues>;
  initialPasswordVisible?: boolean;
  fieldErrors?: { email?: boolean; password?: boolean };
  formError?: string;
  googleState?: SignInVisualState;
  signInState?: SignInActionState;
  isRateLimited?: boolean;
  reduceMotion?: boolean;
  previewTextScale?: number;
  onSignInPress?: (values: SignInValues) => void;
  onGooglePress?: () => void;
  onCreateAccountPress?: () => void;
  onForgotPasswordPress?: () => void;
};

export function SignInScreen({
  initialValues = {},
  initialPasswordVisible = false,
  fieldErrors = {},
  formError,
  googleState = 'default',
  signInState = 'default',
  isRateLimited = false,
  reduceMotion = false,
  previewTextScale = 1,
  onSignInPress = () => { },
  onGooglePress = () => { },
  onCreateAccountPress = () => { },
  onForgotPasswordPress = () => { },
}: SignInScreenProps) {
  const { t } = useTranslation();
  const [passwordVisible, setPasswordVisible] = useState(initialPasswordVisible);
  const passwordInputRef = useRef<any>(null);
  const { scrollToEnd } = useAuthLayout();
  const signInHandledRef = useRef(false);

  const { control, getValues, watch, handleSubmit, formState } = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: {
      email: initialValues.email ?? '',
      password: initialValues.password ?? '',
    },
    mode: 'onChange',
  });

  const email = watch('email');
  const password = watch('password');

  const formReady = !formState.errors.email && !formState.errors.password && email.length > 0 && password.length > 0;

  const emailHasError = fieldErrors.email || formState.errors.email;
  const passwordHasError = fieldErrors.password || formState.errors.password;

  const googleDisabled = googleState === 'unavailable';
  const googlePending = googleState === 'pending';
  const isSigningIn = signInState === 'pending';

  const signInDisabled = !formReady || isRateLimited;

  const handleSignIn = (values: SignInValues) => {
    if (!formReady || isSigningIn || signInHandledRef.current) return;
    signInHandledRef.current = true;
    onSignInPress(values);
  };

  const submitForm = handleSubmit(handleSignIn);

  return (
    <AuthScreenLayout
      previewTextScale={previewTextScale}
      supportingText={t('auth.signIn.body')}
      title={t('auth.signIn.title')}
    >
      <View className="gap-6">
        <Button
          accessibilityLabel={t('auth.signIn.continueWithGoogle')}
          accessibilityState={{ disabled: googleDisabled, busy: googlePending }}
          animation={
            googlePending
              ? { scale: false, highlight: false }
              : undefined
          }
          className="w-full"
          isDisabled={googleDisabled}
          onPress={googlePending ? undefined : onGooglePress}
          size="md"
          style={googleState === 'pressed' ? styles.pressed : null}
          variant="ghost"
        >
          {googlePending ? (
            <Spinner color={darkColors.textPrimary} size="sm" />
          ) : (
            <>
              <Image
                aria-hidden={true}
                source={require('@/assets/images/auth/google-g.png')}
                style={styles.googleLogo}
              />
              <Button.Label style={styles.googleLabel}>
                {t('auth.signIn.continueWithGoogle')}
              </Button.Label>
            </>
          )}
        </Button>

        <View accessibilityRole="text" className="flex-row items-center gap-3">
          <View className="h-px flex-1" style={styles.divider} />
          <Text style={[typography.supporting, styles.dividerText]}>
            {t('auth.signIn.emailAlternative')}
          </Text>
          <View className="h-px flex-1" style={styles.divider} />
        </View>

        <View className="gap-4">
          <Controller
            control={control}
            name="email"
            render={({ field: { onBlur, onChange, value } }) => (
              <TextField isInvalid={!!emailHasError}>
                <InputGroup>
                  <InputGroup.Prefix isDecorative>
                    <Mail
                      color={darkColors.textSecondary}
                      size={16}
                    />
                  </InputGroup.Prefix>
                  <InputGroup.Input
                    accessibilityLabel={t('auth.signIn.emailPlaceholder')}
                    autoCapitalize="none"
                    autoComplete="email"
                    inputMode="email"
                    keyboardType="email-address"
                    onBlur={onBlur}
                    onChangeText={onChange}
                    placeholder={t('auth.signIn.emailPlaceholder')}
                    returnKeyType="next"
                    textContentType="emailAddress"
                    value={value}
                  />
                </InputGroup>
                {emailHasError ? (
                  <FieldError>
                    {formState.errors.email ? t(formState.errors.email.message as any) : t('auth.signIn.errors.email')}
                  </FieldError>
                ) : null}
              </TextField>
            )}
          />

          <View>
            <Controller
              control={control}
              name="password"
              render={({ field: { onBlur, onChange, value } }) => (
                <TextField isInvalid={!!passwordHasError}>
                  <InputGroup>
                    <InputGroup.Prefix isDecorative>
                      <Lock
                        color={darkColors.textSecondary}
                        size={16}
                      />
                    </InputGroup.Prefix>
                    <InputGroup.Input
                      accessibilityLabel={t('auth.signIn.passwordPlaceholder')}
                      autoCapitalize="none"
                      autoComplete="password"
                      onBlur={onBlur}
                      onChangeText={onChange}
                      placeholder={t('auth.signIn.passwordPlaceholder')}
                      secureTextEntry={!passwordVisible}
                      textContentType="password"
                      value={value}
                    />
                    <InputGroup.Suffix>
                      <Button
                        accessibilityLabel={
                          passwordVisible
                            ? t('auth.signIn.hidePassword')
                            : t('auth.signIn.showPassword')
                        }
                        isIconOnly
                        onPress={() => setPasswordVisible((visible) => !visible)}
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
                  {passwordHasError ? (
                    <FieldError>
                      {formState.errors.password ? t(formState.errors.password.message as any) : t('auth.signIn.errors.password')}
                    </FieldError>
                  ) : null}
                </TextField>
              )}
            />

            <Pressable
              accessibilityLabel={t('auth.signIn.forgotPassword')}
              className="mt-3 self-end"
              onPress={onForgotPasswordPress}
            >
              <Text style={{ color: darkColors.brand.action, fontSize: 13, fontWeight: '500' }}>
                {t('auth.signIn.forgotPassword')}
              </Text>
            </Pressable>
          </View>
        </View>

        {formError ? (
          <Text style={{ color: darkColors.status.destructive.main, fontSize: 14, fontWeight: '500', textAlign: 'center', marginTop: 16 }}>
            {t(formError as any)}
          </Text>
        ) : null}

        <Button
          accessibilityLabel={t('auth.signIn.signIn')}
          accessibilityState={{ busy: isSigningIn, disabled: signInDisabled }}
          animation={isSigningIn ? { scale: false, highlight: false } : undefined}
          className="w-full mt-8"
          isDisabled={signInDisabled}
          onPress={isSigningIn ? undefined : submitForm}
          size="md"
          style={signInState === 'pressed' ? styles.pressed : undefined}
        >
          {isSigningIn ? (
            <View className="flex-row items-center justify-center gap-2">
              <Spinner color={darkColors.brand?.onAction ?? '#052E16'} size="sm" />
              <Button.Label>{t('auth.signIn.signingIn')}</Button.Label>
            </View>
          ) : (
            t('auth.signIn.signIn')
          )}
        </Button>
      </View>

      <View className="mt-auto flex-row items-center justify-center gap-2">
        <Text style={[typography.supporting, styles.existingAccountText]}>
          {t('auth.signIn.noAccount')}
        </Text>
        <Button
          accessibilityLabel={t('auth.signIn.createAccount')}
          onPress={onCreateAccountPress}
          size="sm"
          variant="ghost"
        >
          <Button.Label style={styles.signInLabel}>
            {t('auth.signIn.createAccount')}
          </Button.Label>
        </Button>
      </View>
    </AuthScreenLayout>
  );
}

const styles = StyleSheet.create({
  googleLogo: {
    height: 18,
    width: 18,
  },
  googleLabel: {
    color: darkColors.textPrimary,
  },
  divider: {
    backgroundColor: darkColors.borderSubtle,
  },
  dividerText: {
    color: darkColors.textSecondary,
    fontSize: 14,
  },
  existingAccountText: {
    color: darkColors.textSecondary,
  },
  signInLabel: {
    color: darkColors.textPrimary,
    fontWeight: '600',
  },
  pressed: {
    opacity: 0.8,
  },
});
