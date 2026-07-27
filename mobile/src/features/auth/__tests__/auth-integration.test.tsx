import { screen, userEvent, waitFor } from '@testing-library/react-native';
import { http, HttpResponse } from 'msw';

import SignUpRoute from '@/app/(auth)/sign-up';
import CheckEmailRoute from '@/app/(auth)/check-email';
import SignInRoute from '@/app/(auth)/sign-in';
import { server } from '../../../../tests/mocks/server';
import { renderWithProviders } from '../../../../tests/test-utils';

jest.mock('expo-router', () => {
  const actual = jest.requireActual('expo-router');
  return {
    ...actual,
    useRouter: () => ({
      push: jest.fn(),
      replace: jest.fn(),
      setParams: jest.fn(),
    }),
    useLocalSearchParams: jest.fn(() => ({ email: 'test@test.com', sent: '1' })),
  };
});

jest.mock('@react-native-google-signin/google-signin', () => ({
  GoogleSignin: {
    configure: jest.fn(),
    hasPlayServices: jest.fn().mockResolvedValue(true),
    signIn: jest.fn(),
    signOut: jest.fn().mockResolvedValue(true),
  },
  statusCodes: {
    SIGN_IN_CANCELLED: 'SIGN_IN_CANCELLED',
    IN_PROGRESS: 'IN_PROGRESS',
    PLAY_SERVICES_NOT_AVAILABLE: 'PLAY_SERVICES_NOT_AVAILABLE',
  },
}));

describe('Auth Integration: SignUp & CheckEmail', () => {
  jest.setTimeout(15000);
  describe('SignUpRoute', () => {
    it('creates an account and handles MSW success', async () => {
      const user = userEvent.setup();
      await renderWithProviders(<SignUpRoute />);
      
      const emailInput = screen.getByLabelText('Email');
      const usernameInput = screen.getByLabelText('Username');
      const continueButton = screen.getByRole('button', { name: 'Continue' });

      await user.type(emailInput, 'newuser@test.com');
      await user.type(usernameInput, 'new_user');
      await user.press(continueButton);

      const passwordInput = await screen.findByLabelText('Password');
      const createButton = screen.getByRole('button', { name: 'Create account' });

      await user.type(passwordInput, 'Valid123!Password');
      
      await waitFor(() => {
        expect(createButton).toBeEnabled();
      });

      await user.press(createButton);
      
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: 'Creating account…' })).toBeFalsy();
      });
    });

    it('displays error if username is already taken', async () => {
      const user = userEvent.setup();
      await renderWithProviders(<SignUpRoute />);
      
      await user.type(screen.getByLabelText('Email'), 'c@test.com');
      await user.type(screen.getByLabelText('Username'), 'conflict');
      const continueBtn = screen.getByRole('button', { name: 'Continue' });
      await waitFor(() => expect(continueBtn).toBeEnabled());
      await user.press(continueBtn);

      const passwordInput = await screen.findByLabelText('Password');
      await user.type(passwordInput, 'Valid123!Password');
      
      const createButton = screen.getByRole('button', { name: 'Create account' });
      await waitFor(() => expect(createButton).toBeEnabled());
      await user.press(createButton);

      await waitFor(() => {
        expect(screen.getByText('Use 3–32 letters, numbers, dots, or underscores.')).toBeTruthy();
      });
    });

    it('displays global rate limit error when backend returns auth.signup_global_rate_limited', async () => {
      server.use(
        http.post('*/sign-up', () => {
          return HttpResponse.json({ detail: 'auth.signup_global_rate_limited' }, { status: 429 });
        })
      );

      const user = userEvent.setup();
      await renderWithProviders(<SignUpRoute />);
      
      await user.type(screen.getByLabelText('Email'), 'rl@test.com');
      await user.type(screen.getByLabelText('Username'), 'ratelimit');
      const continueBtn = screen.getByRole('button', { name: 'Continue' });
      await waitFor(() => expect(continueBtn).toBeEnabled());
      await user.press(continueBtn);

      const passwordInput = await screen.findByLabelText('Password');
      await user.type(passwordInput, 'Valid123!Password');
      
      const createButton = screen.getByRole('button', { name: 'Create account' });
      await waitFor(() => expect(createButton).toBeEnabled());
      await user.press(createButton);

      await waitFor(() => {
        expect(screen.getByText('Too many sign-up attempts globally. Please try again later.')).toBeTruthy();
      });
    });

    it('displays idempotency conflict error when backend returns auth.idempotency_conflict_in_progress', async () => {
      server.use(
        http.post('*/sign-up', () => {
          return HttpResponse.json({ detail: 'auth.idempotency_conflict_in_progress' }, { status: 409 });
        })
      );

      const user = userEvent.setup();
      await renderWithProviders(<SignUpRoute />);
      
      await user.type(screen.getByLabelText('Email'), 'idem@test.com');
      await user.type(screen.getByLabelText('Username'), 'idempotent');
      const continueBtn = screen.getByRole('button', { name: 'Continue' });
      await waitFor(() => expect(continueBtn).toBeEnabled());
      await user.press(continueBtn);

      const passwordInput = await screen.findByLabelText('Password');
      await user.type(passwordInput, 'Valid123!Password');
      
      const createButton = screen.getByRole('button', { name: 'Create account' });
      await waitFor(() => expect(createButton).toBeEnabled());
      await user.press(createButton);

      await waitFor(() => {
        expect(screen.getByText('Sign-up is already in progress. Please wait a moment.')).toBeTruthy();
      });
    });

    it('displays disposable email error when backend returns auth.disposable_email_blocked', async () => {
      server.use(
        http.post('*/sign-up', () => {
          return HttpResponse.json({ detail: 'auth.disposable_email_blocked' }, { status: 400 });
        })
      );

      const user = userEvent.setup();
      await renderWithProviders(<SignUpRoute />);
      
      await user.type(screen.getByLabelText('Email'), 'test@mailinator.com');
      await user.type(screen.getByLabelText('Username'), 'spammer');
      const continueBtn = screen.getByRole('button', { name: 'Continue' });
      await waitFor(() => expect(continueBtn).toBeEnabled());
      await user.press(continueBtn);

      const passwordInput = await screen.findByLabelText('Password');
      await user.type(passwordInput, 'Valid123!Password');
      
      const createButton = screen.getByRole('button', { name: 'Create account' });
      await waitFor(() => expect(createButton).toBeEnabled());
      await user.press(createButton);

      await waitFor(() => {
        expect(screen.getByText('Registration with disposable email addresses is not allowed. Please use a real email.')).toBeTruthy();
      });
    });
  });

  describe('CheckEmailRoute', () => {
    it('handles resend mutation and starts cooldown', async () => {
      const user = userEvent.setup();
      await renderWithProviders(<CheckEmailRoute />);
      
      const resendButton = screen.getByRole('button', { name: 'Resend link' });
      await user.press(resendButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Resend link (60s)' })).toBeTruthy();
      });
    });

    it('displays session expired error when navigated to sign-in with sessionExpired error', async () => {
      const { useLocalSearchParams } = require('expo-router');
      useLocalSearchParams.mockReturnValue({ error: 'auth.refresh_token_invalid' });

      await renderWithProviders(<SignInRoute />);

      await waitFor(() => {
        expect(screen.getByText('Your session has expired or is invalid. Please sign in again.')).toBeTruthy();
      });
    });
  });

  describe('SignInRoute', () => {
    it('displays rate limit error when backend returns auth.login_rate_limited', async () => {
      server.use(
        http.post('*/auth/mobile/sign-in', () => {
          return HttpResponse.json({ detail: 'auth.login_rate_limited' }, { status: 429 });
        })
      );

      const user = userEvent.setup();
      await renderWithProviders(<SignInRoute />);

      await user.type(screen.getByPlaceholderText('Enter your email'), 'test@example.com');
      await user.type(screen.getByPlaceholderText('Enter your password'), 'Password123!');

      const signInButton = screen.getByRole('button', { name: 'Sign in' });
      await user.press(signInButton);

      await waitFor(() => {
        expect(screen.getByText('Too many login attempts. Please try again later.')).toBeTruthy();
      });
    });

    it('displays idempotency error when backend returns auth.idempotency_conflict_in_progress', async () => {
      server.use(
        http.post('*/auth/mobile/sign-in', () => {
          return HttpResponse.json({ detail: 'auth.idempotency_conflict_in_progress' }, { status: 409 });
        })
      );

      const user = userEvent.setup();
      await renderWithProviders(<SignInRoute />);

      await user.type(screen.getByPlaceholderText('Enter your email'), 'test@example.com');
      await user.type(screen.getByPlaceholderText('Enter your password'), 'Password123!');

      const signInButton = screen.getByRole('button', { name: 'Sign in' });
      await user.press(signInButton);

      await waitFor(() => {
        expect(screen.getByText('Sign-in is already in progress. Please wait a moment.')).toBeTruthy();
      });
    });
  });
});
