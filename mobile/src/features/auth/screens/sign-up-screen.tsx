import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ElementRef,
} from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  AccessibilityInfo,
  Animated,
  findNodeHandle,
  Image,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Button } from '@/components/ui/button';
import { FieldError } from 'heroui-native/field-error';
import { InputGroup } from 'heroui-native/input-group';
import { Spinner } from 'heroui-native/spinner';
import { TextField } from 'heroui-native/text-field';
import { Eye, EyeOff, Lock, Mail, User } from 'lucide-react-native';

import {
  authPresentationColors,
  darkColors,
  motion,
  sizes,
  spacing,
  typography,
} from '@/theme';

import { AuthScreenLayout, useAuthLayout } from '../components/auth-screen-layout';
import { PasswordRequirementList } from '../components/password-requirement-list';
import {
  arePasswordRequirementsMet,
  evaluatePasswordRequirements,
} from '../components/sign-up-ui-rules';
import { zodResolver } from '@hookform/resolvers/zod';
import { signUpSchema } from '../schemas/sign-up-schema';
import { TurnstileWebView } from '../components/turnstile-webview';

export type SignUpStep = 'identity' | 'password';
export type SignUpField = 'email' | 'username' | 'password';
export type SignUpVisualState = 'default' | 'pressed' | 'unavailable' | 'pending';
export type CreateAccountVisualState = 'default' | 'pressed' | 'pending';

export type SignUpValues = {
  email: string;
  username: string;
  password: string;
  captcha_token?: string;
};

export type SignUpScreenProps = {
  initialStep?: SignUpStep;
  initialValues?: Partial<SignUpValues>;
  initialPasswordVisible?: boolean;
  autoFocusField?: SignUpField;
  fieldErrors?: Partial<Record<SignUpField, boolean>>;
  formError?: string;
  googleState?: SignUpVisualState;
  createAccountState?: CreateAccountVisualState;
  isRateLimited?: boolean;
  reduceMotion?: boolean;
  previewTextScale?: number;
  onGooglePress?: () => void;
  onContinue?: (values: Pick<SignUpValues, 'email' | 'username'>) => void;
  onCreateAccount?: (values: SignUpValues) => void;
  onSignInPress?: () => void;
  onIdentityBack?: () => void;
};

const inertAction = () => undefined;

function fieldErrorKey(field: SignUpField) {
  return `auth.signUp.errors.${field}` as const;
}

export function SignUpScreen({
  initialStep = 'identity',
  initialValues,
  initialPasswordVisible = false,
  autoFocusField,
  fieldErrors = {},
  formError,
  googleState = 'default',
  createAccountState = 'default',
  isRateLimited = false,
  reduceMotion = false,
  previewTextScale = 1,
  onGooglePress = inertAction,
  onContinue = inertAction,
  onCreateAccount = inertAction,
  onSignInPress = inertAction,
  onIdentityBack,
}: SignUpScreenProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<SignUpStep>(initialStep);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [passwordVisible, setPasswordVisible] = useState(initialPasswordVisible);
  const [captchaToken, setCaptchaToken] = useState<string | undefined>();
  const [touched, setTouched] = useState<Partial<Record<SignUpField, boolean>>>({});
  const [transition] = useState(() => new Animated.Value(1));
  const headingRef = useRef<ElementRef<typeof Text>>(null);
  const createHandledRef = useRef(false);
  const { control, getValues, handleSubmit, formState } = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    mode: 'onChange',
    defaultValues: {
      email: initialValues?.email ?? '',
      username: initialValues?.username ?? '',
      password: initialValues?.password ?? '',
    },
  });
  const [email = '', username = '', password = ''] = useWatch({
    control,
    name: ['email', 'username', 'password'],
  });


  const identityReady = !formState.errors.email && !formState.errors.username && email.length > 0 && username.length > 0;
  
  const passwordRequirements = useMemo(
    () => evaluatePasswordRequirements(password, email),
    [email, password],
  );
  const passwordReady = arePasswordRequirementsMet(passwordRequirements) && !formState.errors.password;
  const isCreating = createAccountState === 'pending';

  useEffect(() => {
    transition.setValue(0);
    Animated.timing(transition, {
      duration: reduceMotion ? motion.duration.fast : motion.duration.standard,
      easing: undefined,
      toValue: 1,
      useNativeDriver: true,
    }).start();

    const frame = requestAnimationFrame(() => {
      if (Platform.OS === 'web') return;

      const headingNode = findNodeHandle(headingRef.current);
      if (headingNode) {
        AccessibilityInfo.setAccessibilityFocus(headingNode);
      }
    });

    return () => cancelAnimationFrame(frame);
  }, [reduceMotion, step, transition]);

  useEffect(() => {
    createHandledRef.current = false;
  }, [email, password, username]);

  useEffect(() => {
    if (fieldErrors.email || fieldErrors.username) {
      if (step !== 'identity') {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setDirection(-1);
         
        setStep('identity');
      }
    }
  }, [fieldErrors.email, fieldErrors.username, step]);

  const translateX = transition.interpolate({
    inputRange: [0, 1],
    outputRange: [reduceMotion ? 0 : direction * 10, 0],
  });

  function markTouched(field: SignUpField) {
    setTouched((current) => ({ ...current, [field]: true }));
  }

  function moveToPassword() {
    if (!identityReady) return;
    const values = getValues();
    onContinue({ email: values.email, username: values.username });
    setDirection(1);
    setStep('password');
  }

  function returnToIdentity() {
    setDirection(-1);
    setStep('identity');
  }

  const handleCreate = (values: SignUpValues) => {
    if (!passwordReady || isCreating || createHandledRef.current) return;
    createHandledRef.current = true;
    onCreateAccount({ ...values, captcha_token: captchaToken });
  };

  // eslint-disable-next-line react-hooks/refs
  const createAccount = handleSubmit(handleCreate);

  const title =
    step === 'identity'
      ? t('auth.signUp.identityTitle')
      : t('auth.signUp.passwordTitle');
  const supportingText =
    step === 'identity'
      ? t('auth.signUp.identityBody')
      : t('auth.signUp.passwordBody');

  return (
    <AuthScreenLayout
      backLabel={
        step === 'password' || onIdentityBack ? t('common.back') : undefined
      }
      onBack={
        step === 'password'
          ? returnToIdentity
          : onIdentityBack
      }
      supportingText={supportingText}
      title={title}
      titleRef={headingRef}
      previewTextScale={previewTextScale}
    >
      <Animated.View
        style={[
          styles.animatedContent,
          {
            opacity: transition,
            transform: [{ translateX }],
          },
        ]}
      >
        {step === 'identity' ? (
          <IdentityState
            autoFocusField={autoFocusField}
            control={control}
            email={email}
            fieldErrors={fieldErrors}
            formErrors={formState.errors}
            googleState={googleState}
            identityReady={identityReady}
            onContinue={moveToPassword}
            onGooglePress={onGooglePress}
            onSignInPress={onSignInPress}
            onTouched={markTouched}
            touched={touched}
            username={username}
          />
        ) : (
          <PasswordState
            autoFocus={autoFocusField === 'password'}
            createAccountState={createAccountState}
            isRateLimited={isRateLimited}
            fieldError={Boolean(fieldErrors.password)}
            formError={formError || formState.errors.password?.message}
            isCreating={isCreating}
            onCreateAccount={createAccount}
            onToggleVisibility={() => setPasswordVisible((visible) => !visible)}
            onTouched={() => markTouched('password')}
            password={password}
            passwordReady={passwordReady}
            passwordRequirements={passwordRequirements}
            passwordVisible={passwordVisible}
            previewTextScale={previewTextScale}
            control={control}
            onCaptchaSuccess={setCaptchaToken}
          />
        )}
      </Animated.View>
    </AuthScreenLayout>
  );
}

type IdentityStateProps = {
  autoFocusField?: SignUpField;
  control: ReturnType<typeof useForm<SignUpValues>>['control'];
  email: string;
  username: string;
  fieldErrors: Partial<Record<SignUpField, boolean>>;
  formErrors: import('react-hook-form').FieldErrors<SignUpValues>;
  googleState: SignUpVisualState;
  identityReady: boolean;
  touched: Partial<Record<SignUpField, boolean>>;
  onTouched: (field: SignUpField) => void;
  onGooglePress: () => void;
  onContinue: () => void;
  onSignInPress: () => void;
};

function IdentityState({
  autoFocusField,
  control,
  email,
  username,
  fieldErrors,
  formErrors,
  googleState,
  identityReady,
  touched,
  onTouched,
  onGooglePress,
  onContinue,
  onSignInPress,
}: IdentityStateProps) {
  const { t } = useTranslation();
  const { scrollToEnd } = useAuthLayout();
  const emailInvalid =
    Boolean(fieldErrors.email) ||
    (Boolean(touched.email) && Boolean(formErrors.email));
  const usernameInvalid =
    Boolean(fieldErrors.username) ||
    (Boolean(touched.username) && Boolean(formErrors.username));
  const googleDisabled = googleState === 'unavailable';
  const googlePending = googleState === 'pending';

  return (
    <View className="gap-6">
      <Button
        accessibilityLabel={t('auth.signUp.continueWithGoogle')}
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
              {t('auth.signUp.continueWithGoogle')}
            </Button.Label>
          </>
        )}
      </Button>

      <View accessibilityRole="text" className="flex-row items-center gap-3">
        <View className="h-px flex-1" style={styles.divider} />
        <Text style={[typography.supporting, styles.dividerText]}>
          {t('auth.signUp.emailAlternative')}
        </Text>
        <View className="h-px flex-1" style={styles.divider} />
      </View>

      <View className="gap-4">
        <TextField isInvalid={emailInvalid} isRequired>
          <InputGroup>
            <InputGroup.Prefix isDecorative>
              <Mail color={darkColors.textSecondary} size={16} />
            </InputGroup.Prefix>
            <Controller
              control={control}
              name="email"
              render={({ field: { onChange, onBlur, value } }) => (
                <InputGroup.Input
                  accessibilityLabel={t('auth.signUp.emailLabel')}
                  autoCapitalize="none"
                  autoComplete="email"
                  autoFocus={autoFocusField === 'email'}
                  keyboardType="email-address"
                  onBlur={() => {
                    onTouched('email');
                    onBlur();
                  }}
                  onChangeText={onChange}
                  placeholder={t('auth.signUp.emailPlaceholder')}
                  returnKeyType="next"
                  value={value}
                />
              )}
            />
          </InputGroup>
          {emailInvalid && (fieldErrors.email || formErrors.email) ? (
            <FieldError>
              {formErrors.email
                ? t(formErrors.email.message as any)
                : t(fieldErrorKey('email'))}
            </FieldError>
          ) : null}
        </TextField>

        <TextField isInvalid={usernameInvalid} isRequired>
          <InputGroup>
            <InputGroup.Prefix isDecorative>
              <User color={darkColors.textSecondary} size={16} />
            </InputGroup.Prefix>
            <Controller
              control={control}
              name="username"
              render={({ field: { onChange, onBlur, value } }) => (
                <InputGroup.Input
                  accessibilityLabel={t('auth.signUp.usernameLabel')}
                  autoCapitalize="none"
                  autoComplete="username-new"
                  autoFocus={autoFocusField === 'username'}
                  onBlur={() => {
                    onTouched('username');
                    onBlur();
                  }}
                  onChangeText={onChange}
                  placeholder={t('auth.signUp.usernamePlaceholder')}
                  returnKeyType="done"
                  value={value}
                />
              )}
            />
          </InputGroup>
          {usernameInvalid && (fieldErrors.username || formErrors.username) ? (
            <FieldError>
              {formErrors.username
                ? t(formErrors.username.message as any)
                : t(fieldErrorKey('username'))}
            </FieldError>
          ) : null}
        </TextField>
      </View>

      <Button
        accessibilityLabel={t('auth.signUp.continue')}
        accessibilityState={{ disabled: !identityReady }}
        className="w-full"
        isDisabled={!identityReady}
        onPress={onContinue}
        size="md"
      >
        {t('auth.signUp.continue')}
      </Button>

      <View className="flex-row flex-wrap items-center justify-center gap-1">
        <Text style={[typography.supporting, styles.footerText]}>
          {t('auth.signUp.existingAccount')}
        </Text>
        <Button
          accessibilityLabel={t('auth.signUp.signIn')}
          onPress={onSignInPress}
          size="sm"
          variant="ghost"
        >
          {t('auth.signUp.signIn')}
        </Button>
      </View>
    </View>
  );
}

type PasswordStateProps = {
  autoFocus: boolean;
  control: ReturnType<typeof useForm<SignUpValues>>['control'];
  createAccountState: CreateAccountVisualState;
  isRateLimited?: boolean;
  fieldError: boolean;
  formError?: string;
  isCreating: boolean;
  password: string;
  passwordReady: boolean;
  passwordRequirements: ReturnType<typeof evaluatePasswordRequirements>;
  passwordVisible: boolean;
  previewTextScale: number;
  onCreateAccount: () => void;
  onToggleVisibility: () => void;
  onTouched: () => void;
  onCaptchaSuccess: (token: string) => void;
};

function PasswordState({
  autoFocus,
  control,
  createAccountState,
  isRateLimited = false,
  fieldError,
  formError,
  isCreating,
  password,
  passwordReady,
  passwordRequirements,
  passwordVisible,
  previewTextScale,
  onCreateAccount,
  onToggleVisibility,
  onTouched,
  onCaptchaSuccess,
}: PasswordStateProps) {
  const { t } = useTranslation();
  const { scrollToEnd } = useAuthLayout();
  const createDisabled = isCreating || !passwordReady || isRateLimited;

  return (
    <View className="gap-6">
      <Controller
        control={control}
        name="password"
        render={({ field: { onChange, value } }) => (
          <TextField isInvalid={fieldError} isRequired>
            <InputGroup>
              <InputGroup.Prefix isDecorative>
                <Lock color={darkColors.textSecondary} size={16} />
              </InputGroup.Prefix>
              <InputGroup.Input
                accessibilityLabel={t('auth.signUp.passwordLabel')}
                autoCapitalize="none"
                autoComplete="new-password"
                autoFocus={autoFocus}
                onBlur={onTouched}
                onChangeText={onChange}
                placeholder={t('auth.signUp.passwordPlaceholder')}
                secureTextEntry={!passwordVisible}
                value={value}
              />
              <InputGroup.Suffix>
                <Button
                  accessibilityLabel={
                    passwordVisible
                      ? t('auth.signUp.hidePassword')
                      : t('auth.signUp.showPassword')
                  }
                  isIconOnly
                  onPress={onToggleVisibility}
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
            {fieldError ? (
              <FieldError>{t(fieldErrorKey('password'))}</FieldError>
            ) : null}
          </TextField>
        )}
      />

      <PasswordRequirementList
        previewTextScale={previewTextScale}
        requirements={passwordRequirements}
        touched={password.length > 0}
      />

      <TurnstileWebView
        siteKey={process.env.EXPO_PUBLIC_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'}
        onSuccess={onCaptchaSuccess}
      />

      {formError ? (
        <Text style={{ color: darkColors.status.destructive.main, fontSize: 14, fontWeight: '500', textAlign: 'center', marginBottom: 16 }}>
          {t(formError as any)}
        </Text>
      ) : null}

      <Button
        accessibilityLabel={
          isCreating
            ? t('auth.signUp.creatingAccount')
            : t('auth.signUp.createAccount')
        }
        accessibilityState={{ busy: isCreating, disabled: createDisabled }}
        animation={
          isCreating
            ? { scale: false, highlight: false }
            : undefined
        }
        className="w-full"
        isDisabled={createDisabled}
        onPress={isCreating ? undefined : onCreateAccount}
        size="md"
        style={createAccountState === 'pressed' ? styles.pressed : undefined}
      >
        {isCreating ? (
          <View className="flex-row items-center justify-center gap-2">
            <Spinner color={darkColors.brand.onAction} size="sm" />
            <Button.Label>{t('auth.signUp.creatingAccount')}</Button.Label>
          </View>
        ) : (
          t('auth.signUp.createAccount')
        )}
      </Button>
    </View>
  );
}

const styles = StyleSheet.create({
  animatedContent: {
    flexGrow: 1,
  },
  googleLogo: {
    width: sizes.button.icon,
    height: sizes.button.icon,
  },
  googleLabel: {
    color: authPresentationColors.google.foreground,
  },
  pressed: {
    opacity: 0.78,
  },
  divider: {
    backgroundColor: darkColors.borderSubtle,
  },
  dividerText: {
    color: darkColors.textSecondary,
  },
  footerText: {
    color: darkColors.textSecondary,
    paddingVertical: spacing.xs,
  },
});
