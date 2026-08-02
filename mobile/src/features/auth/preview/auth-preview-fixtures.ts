import type { SignInScreenProps } from '../screens/sign-in-screen';
import type { SignUpScreenProps } from '../screens/sign-up-screen';
import type { CheckEmailScreenProps } from '../screens/check-email-screen';
import type { VerifyAccountScreenProps } from '../screens/verify-account-screen';
import type { ForgotPasswordScreenProps } from '../screens/forgot-password-screen';
import type { ResetPasswordScreenProps } from '../screens/reset-password-screen';
import type { ChangePasswordFormProps } from '../../settings/components/change-password-form';

export type AuthPreviewFixture = {
  id: string;
  labelKey: string;
  screenProps: SignUpScreenProps;
  toastVariant?: 'danger' | 'success' | 'warning';
  toastLabel?: string;
};

const readyIdentity = {
  email: 'demo@example.com',
  username: 'demo.user',
};

const readyAccount = {
  ...readyIdentity,
  password: 'SafePass1!',
};

/**
 * Development-only visual states. Every fixture renders the production
 * SignUpScreen with inert callbacks; no fake service layer is introduced.
 */
export const authPreviewFixtures: readonly AuthPreviewFixture[] = [
  {
    id: 'identity-empty',
    labelKey: 'auth.preview.states.identityEmpty',
    screenProps: {},
  },
  {
    id: 'identity-partial',
    labelKey: 'auth.preview.states.identityPartial',
    screenProps: { initialValues: { email: 'demo@' } },
  },
  {
    id: 'identity-valid',
    labelKey: 'auth.preview.states.identityValid',
    screenProps: { initialValues: readyIdentity },
  },
  {
    id: 'identity-focused',
    labelKey: 'auth.preview.states.identityFocused',
    screenProps: { autoFocusField: 'email' },
  },
  {
    id: 'identity-error',
    labelKey: 'auth.preview.states.identityError',
    screenProps: {
      fieldErrors: { email: true, username: true },
      initialValues: { email: 'not-an-email', username: 'x' },
    },
  },
  {
    id: 'google-pressed',
    labelKey: 'auth.preview.states.googlePressed',
    screenProps: { googleState: 'pressed' },
  },
  {
    id: 'google-unavailable',
    labelKey: 'auth.preview.states.googleUnavailable',
    screenProps: { googleState: 'unavailable' },
  },
  {
    id: 'google-pending',
    labelKey: 'auth.preview.states.googlePending',
    screenProps: { googleState: 'pending' },
  },
  {
    id: 'google-error-id-token',
    labelKey: 'auth.preview.states.googleErrorIdToken',
    screenProps: {
      initialValues: readyIdentity,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.googleGeneric',
  },
  {
    id: 'password-untouched',
    labelKey: 'auth.preview.states.passwordUntouched',
    screenProps: { initialStep: 'password', initialValues: readyIdentity },
  },
  {
    id: 'password-partial',
    labelKey: 'auth.preview.states.passwordPartial',
    screenProps: {
      initialStep: 'password',
      initialValues: { ...readyIdentity, password: 'Safe' },
    },
  },
  {
    id: 'password-valid',
    labelKey: 'auth.preview.states.passwordValid',
    screenProps: { initialStep: 'password', initialValues: readyAccount },
  },
  {
    id: 'password-visible',
    labelKey: 'auth.preview.states.passwordVisible',
    screenProps: {
      initialPasswordVisible: true,
      initialStep: 'password',
      initialValues: readyAccount,
    },
  },
  {
    id: 'password-error',
    labelKey: 'auth.preview.states.passwordError',
    screenProps: {
      fieldErrors: { password: true },
      initialStep: 'password',
      initialValues: { ...readyIdentity, password: 'weak' },
    },
  },
  {
    id: 'create-pressed',
    labelKey: 'auth.preview.states.createPressed',
    screenProps: {
      createAccountState: 'pressed',
      initialStep: 'password',
      initialValues: readyAccount,
    },
  },
  {
    id: 'create-pending',
    labelKey: 'auth.preview.states.createPending',
    screenProps: {
      createAccountState: 'pending',
      initialStep: 'password',
      initialValues: readyAccount,
    },
  },
  {
    id: 'global-rate-limited',
    labelKey: 'auth.preview.states.globalRateLimited',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
      isRateLimited: true,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.globalRateLimited',
  },
  {
    id: 'captcha-failed',
    labelKey: 'auth.preview.states.captchaFailed',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.captchaFailed',
  },
  {
    id: 'rate-limited',
    labelKey: 'auth.preview.states.rateLimited',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
      isRateLimited: true,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.rateLimited',
  },
  {
    id: 'conflict',
    labelKey: 'auth.preview.states.conflict',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.conflict',
  },
  {
    id: 'idempotency-conflict',
    labelKey: 'auth.preview.states.idempotencyConflict',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.idempotencyConflictInProgress',
  },
  {
    id: 'disposable-email-blocked',
    labelKey: 'auth.preview.states.disposableEmailBlocked',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.disposableEmailBlocked',
  },
  {
    id: 'generic',
    labelKey: 'auth.preview.states.generic',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signUp.errors.generic',
  },
  {
    id: 'reduced-motion',
    labelKey: 'auth.preview.states.reducedMotion',
    screenProps: { initialValues: readyIdentity, reduceMotion: true },
  },
  {
    id: 'large-text',
    labelKey: 'auth.preview.states.largeText',
    screenProps: { initialValues: readyIdentity, previewTextScale: 1.5 },
  },
  {
    id: 'maximum-text',
    labelKey: 'auth.preview.states.maximumText',
    screenProps: {
      initialStep: 'password',
      initialValues: readyAccount,
      previewTextScale: 2,
    },
  },
] as const;

export type AuthPreviewSignInFixture = {
  id: string;
  labelKey: string;
  screenProps: SignInScreenProps;
  toastVariant?: 'danger' | 'success' | 'warning';
  toastLabel?: string;
};

export const authPreviewSignInFixtures: readonly AuthPreviewSignInFixture[] = [
  {
    id: 'signin-empty',
    labelKey: 'auth.preview.states.signInEmpty',
    screenProps: {},
  },
  {
    id: 'signin-partial',
    labelKey: 'auth.preview.states.signInPartial',
    screenProps: { initialValues: { email: 'demo@' } },
  },
  {
    id: 'signin-ready',
    labelKey: 'auth.preview.states.signInReady',
    screenProps: { initialValues: readyAccount },
  },
  {
    id: 'signin-password-visible',
    labelKey: 'auth.preview.states.passwordVisible',
    screenProps: { initialValues: readyAccount, initialPasswordVisible: true },
  },
  {
    id: 'signin-error',
    labelKey: 'auth.preview.states.signInError',
    screenProps: {
      fieldErrors: { email: true, password: true },
      initialValues: { email: 'invalid', password: '' },
    },
  },
  {
    id: 'signin-pending',
    labelKey: 'auth.preview.states.signInPending',
    screenProps: {
      initialValues: readyAccount,
      signInState: 'pending',
    },
  },
  {
    id: 'signin-invalid-credentials',
    labelKey: 'auth.preview.states.signInError',
    screenProps: {
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signIn.errors.invalidCredentials',
  },
  {
    id: 'signin-login-rate-limited',
    labelKey: 'auth.preview.states.rateLimited',
    screenProps: {
      initialValues: readyAccount,
      isRateLimited: true,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signIn.errors.loginRateLimited',
  },
  {
    id: 'signin-idempotency-conflict',
    labelKey: 'auth.preview.states.idempotencyConflict',
    screenProps: {
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signIn.errors.idempotencyConflictInProgress',
  },
  {
    id: 'signin-session-expired',
    labelKey: 'auth.preview.states.verifyError',
    screenProps: {
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signIn.errors.sessionExpired',
  },
  {
    id: 'signin-google-pressed',
    labelKey: 'auth.preview.states.googlePressed',
    screenProps: { initialValues: readyAccount, googleState: 'pressed' },
  },
  {
    id: 'signin-google-unavailable',
    labelKey: 'auth.preview.states.googleUnavailable',
    screenProps: { googleState: 'unavailable' },
  },
  {
    id: 'signin-google-pending',
    labelKey: 'auth.preview.states.googlePending',
    screenProps: { initialValues: readyAccount, googleState: 'pending' },
  },
  {
    id: 'signin-google-error',
    labelKey: 'auth.preview.states.googleErrorIdToken',
    screenProps: {
      initialValues: readyAccount,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signIn.errors.googleGeneric',
  },
  {
    id: 'signin-email-not-verified',
    labelKey: 'auth.preview.states.signInError',
    screenProps: {
      initialValues: readyAccount,
      showResendVerification: true,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.signIn.errors.emailNotVerified',
  },
  {
    id: 'signin-reduced-motion',
    labelKey: 'auth.preview.states.reducedMotion',
    screenProps: { initialValues: readyAccount, reduceMotion: true },
  },
  {
    id: 'signin-large-text',
    labelKey: 'auth.preview.states.largeText',
    screenProps: { initialValues: readyAccount, previewTextScale: 1.5 },
  },
  {
    id: 'signin-maximum-text',
    labelKey: 'auth.preview.states.maximumText',
    screenProps: { initialValues: readyAccount, previewTextScale: 2 },
  },
] as const;

export type AuthPreviewCheckEmailFixture = {
  id: string;
  labelKey: string;
  screenProps: CheckEmailScreenProps;
  toastVariant?: 'danger' | 'success' | 'warning';
  toastLabel?: string;
};

export const authPreviewCheckEmailFixtures: readonly AuthPreviewCheckEmailFixture[] = [
  {
    id: 'check-email-ready',
    labelKey: 'auth.preview.states.checkEmailReady',
    screenProps: {},
  },
  {
    id: 'check-email-send-failed',
    labelKey: 'auth.preview.states.checkEmailSendFailed',
    screenProps: {
      initialSendFailed: true,
      resendState: 'countdown',
      resendCountdownSeconds: 59,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.checkEmail.errors.resendFailed',
  },
  {
    id: 'check-email-countdown',
    labelKey: 'auth.preview.states.checkEmailCountdown',
    screenProps: { resendState: 'countdown', resendCountdownSeconds: 59 },
  },
  {
    id: 'check-email-pending',
    labelKey: 'auth.preview.states.checkEmailPending',
    screenProps: { resendState: 'pending' },
  },
  {
    id: 'check-email-resend-failed',
    labelKey: 'auth.preview.states.generic',
    screenProps: {
      resendState: 'countdown',
      resendCountdownSeconds: 5,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.checkEmail.errors.resendFailed',
  },
  {
    id: 'check-email-rate-limited',
    labelKey: 'auth.preview.states.rateLimited',
    screenProps: { isRateLimited: true },
    toastVariant: 'danger',
    toastLabel: 'auth.checkEmail.errors.rateLimited',
  },
] as const;

export type AuthPreviewVerifyAccountFixture = {
  id: string;
  labelKey: string;
  screenProps: VerifyAccountScreenProps;
};

export const authPreviewVerifyAccountFixtures: readonly AuthPreviewVerifyAccountFixture[] = [
  {
    id: 'verify-ready',
    labelKey: 'auth.preview.states.verifyReady',
    screenProps: { verifyState: 'ready' },
  },
  {
    id: 'verify-loading',
    labelKey: 'auth.preview.states.verifyLoading',
    screenProps: { verifyState: 'loading' },
  },
  {
    id: 'verify-success',
    labelKey: 'auth.preview.states.verifySuccess',
    screenProps: { verifyState: 'success' },
  },
  {
    id: 'verify-invalid-token',
    labelKey: 'auth.preview.states.verifyError',
    screenProps: { verifyState: 'error', customErrorMessage: 'auth.verifyAccount.invalidToken' },
  },
  {
    id: 'verify-rate-limited',
    labelKey: 'auth.preview.states.rateLimited',
    screenProps: { verifyState: 'error', customErrorMessage: 'auth.verifyAccount.rateLimited', isRateLimited: true },
  },
  {
    id: 'verify-missing-token',
    labelKey: 'auth.preview.states.verifyError',
    screenProps: { verifyState: 'error', customErrorMessage: 'auth.verifyAccount.missingToken' },
  },
] as const;

export type AuthPreviewForgotPasswordFixture = {
  id: string;
  labelKey: string;
  screenProps: ForgotPasswordScreenProps;
  toastVariant?: 'danger' | 'success' | 'warning';
  toastLabel?: string;
};

export const authPreviewForgotPasswordFixtures: readonly AuthPreviewForgotPasswordFixture[] = [
  {
    id: 'forgot-password-empty',
    labelKey: 'auth.preview.states.forgotPasswordEmpty',
    screenProps: {},
  },
  {
    id: 'forgot-password-ready',
    labelKey: 'auth.preview.states.forgotPasswordReady',
    screenProps: { initialValues: { email: 'john@example.com' } },
  },
  {
    id: 'forgot-password-pending',
    labelKey: 'auth.preview.states.forgotPasswordPending',
    screenProps: { initialValues: { email: 'john@example.com' }, forgotPasswordState: 'loading' },
  },
  {
    id: 'forgot-password-success',
    labelKey: 'auth.preview.states.verifySuccess',
    screenProps: { forgotPasswordState: 'success' },
  },
  {
    id: 'forgot-password-rate-limited',
    labelKey: 'auth.preview.states.rateLimited',
    screenProps: {
      initialValues: { email: 'john@example.com' },
      isRateLimited: true,
    },
    toastVariant: 'danger',
    toastLabel: 'auth.forgotPassword.errors.rateLimited',
  },
  {
    id: 'forgot-password-idempotency-conflict',
    labelKey: 'auth.preview.states.idempotencyConflict',
    screenProps: {
      initialValues: { email: 'john@example.com' },
    },
    toastVariant: 'danger',
    toastLabel: 'auth.forgotPassword.errors.idempotencyConflictInProgress',
  },
  {
    id: 'forgot-password-generic',
    labelKey: 'auth.preview.states.generic',
    screenProps: {
      initialValues: { email: 'john@example.com' },
    },
    toastVariant: 'danger',
    toastLabel: 'auth.forgotPassword.errors.generic',
  },
  {
    id: 'forgot-password-large-text',
    labelKey: 'auth.preview.states.largeText',
    screenProps: { initialValues: { email: 'john@example.com' }, previewTextScale: 1.5 },
  },
] as const;

export type AuthPreviewResetPasswordFixture = {
  id: string;
  labelKey: string;
  screenProps: ResetPasswordScreenProps;
  toastVariant?: 'danger' | 'success' | 'warning';
  toastLabel?: string;
};

export const authPreviewResetPasswordFixtures: readonly AuthPreviewResetPasswordFixture[] = [
  {
    id: 'reset-password-empty',
    labelKey: 'auth.preview.states.resetPasswordEmpty',
    screenProps: {},
  },
  {
    id: 'reset-password-missing-token',
    labelKey: 'auth.preview.states.verifyError',
    screenProps: {},
    toastVariant: 'danger',
    toastLabel: 'auth.resetPassword.errors.missingToken',
  },
  {
    id: 'reset-password-partial',
    labelKey: 'auth.preview.states.passwordPartial',
    screenProps: {},
  },
  {
    id: 'reset-password-ready',
    labelKey: 'auth.preview.states.resetPasswordReady',
    screenProps: {},
  },
  {
    id: 'reset-password-pending',
    labelKey: 'auth.preview.states.resetPasswordPending',
    screenProps: { resetPasswordState: 'loading' },
  },
  {
    id: 'reset-password-success',
    labelKey: 'auth.preview.states.verifySuccess',
    screenProps: { resetPasswordState: 'success' },
  },
  {
    id: 'reset-password-invalid-token',
    labelKey: 'auth.preview.states.verifyError',
    screenProps: { resetPasswordState: 'error', formError: 'auth.resetPassword.errors.invalidToken' },
  },
  {
    id: 'reset-password-rate-limited',
    labelKey: 'auth.preview.states.rateLimited',
    screenProps: {
      resetPasswordState: 'error',
      formError: 'auth.resetPassword.errors.rateLimited',
      isRateLimited: true,
    },
  },
  {
    id: 'reset-password-idempotency-conflict',
    labelKey: 'auth.preview.states.idempotencyConflict',
    screenProps: {
      resetPasswordState: 'error',
      formError: 'auth.resetPassword.errors.idempotencyConflictInProgress',
    },
  },
  {
    id: 'reset-password-generic',
    labelKey: 'auth.preview.states.generic',
    screenProps: { resetPasswordState: 'error', formError: 'auth.resetPassword.errors.generic' },
  },
  {
    id: 'reset-password-large-text',
    labelKey: 'auth.preview.states.largeText',
    screenProps: { previewTextScale: 1.5 },
  },
] as const;

export type AuthPreviewChangePasswordFixture = {
  id: string;
  labelKey: string;
  screenProps: ChangePasswordFormProps;
};

export const authPreviewChangePasswordFixtures: readonly AuthPreviewChangePasswordFixture[] = [
  {
    id: 'change-password-empty',
    labelKey: 'auth.preview.states.signInEmpty',
    screenProps: {},
  },
  {
    id: 'change-password-pending',
    labelKey: 'auth.preview.states.signInPending',
    screenProps: { isPendingOverride: true },
  },
  {
    id: 'change-password-success',
    labelKey: 'auth.preview.states.verifySuccess',
    screenProps: { successMessageOverride: 'settings.changePasswordSuccess' },
  },
  {
    id: 'change-password-incorrect-current',
    labelKey: 'auth.preview.states.signInError',
    screenProps: { formErrorOverride: 'auth.incorrect_current_password' },
  },
  {
    id: 'change-password-rate-limited',
    labelKey: 'auth.preview.states.rateLimited',
    screenProps: { formErrorOverride: 'auth.change_password_rate_limited' },
  },
  {
    id: 'change-password-google-only',
    labelKey: 'auth.preview.states.signInError',
    screenProps: { formErrorOverride: 'auth.google_only_cannot_change_password' },
  },
  {
    id: 'change-password-generic-error',
    labelKey: 'auth.preview.states.generic',
    screenProps: { formErrorOverride: 'common.errorOccurred' },
  },
] as const;

