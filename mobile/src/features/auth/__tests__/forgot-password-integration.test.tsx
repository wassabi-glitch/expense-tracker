import { screen, userEvent, waitFor } from '@testing-library/react-native';
import { http, HttpResponse } from 'msw';
import ForgotPasswordRoute from '@/app/(auth)/forgot-password';
import { server } from '../../../../tests/mocks/server';
import { renderWithProviders } from '../../../../tests/test-utils';

jest.mock('expo-router', () => {
  const actual = jest.requireActual('expo-router');
  return {
    ...actual,
    useRouter: () => ({
      push: jest.fn(),
      replace: jest.fn(),
      back: jest.fn(),
      canGoBack: jest.fn().mockReturnValue(true),
    }),
  };
});

describe('ForgotPasswordRoute Integration', () => {
  jest.setTimeout(15000);

  it('renders form and handles successful submission', async () => {
    server.use(
      http.post('*/auth/forgot-password', () => {
        return HttpResponse.json({ message: 'Email sent' });
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<ForgotPasswordRoute />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email');
    const sendButton = screen.getByRole('button', { name: 'Send reset link' });

    // Initial state: button should be disabled because email is empty
    expect(sendButton).toBeDisabled();

    await user.type(emailInput, 'test@example.com');
    
    await waitFor(() => {
      expect(sendButton).toBeEnabled();
    });

    await user.press(sendButton);

    // It should transition to success state
    await waitFor(() => {
      expect(screen.getByText('Link Sent!')).toBeTruthy();
      expect(screen.getByText('If the account exists, please check your email inbox for a link to complete the reset.')).toBeTruthy();
    });
  });

  it('displays rate limit error from backend', async () => {
    server.use(
      http.post('*/auth/forgot-password', () => {
        return HttpResponse.json(
          { detail: 'auth.forgot_password_rate_limited' },
          { status: 429 }
        );
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<ForgotPasswordRoute />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email');
    await user.type(emailInput, 'test@example.com');
    
    const sendButton = screen.getByRole('button', { name: 'Send reset link' });
    await waitFor(() => expect(sendButton).toBeEnabled());

    await user.press(sendButton);

    await waitFor(() => {
      expect(screen.getByText('Too many password reset requests. Please try again later.')).toBeTruthy();
    });
  });

  it('displays idempotency conflict error from backend', async () => {
    server.use(
      http.post('*/auth/forgot-password', () => {
        return HttpResponse.json(
          { detail: 'auth.idempotency_conflict_in_progress' },
          { status: 409 }
        );
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<ForgotPasswordRoute />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email');
    await user.type(emailInput, 'test@example.com');
    
    const sendButton = screen.getByRole('button', { name: 'Send reset link' });
    await waitFor(() => expect(sendButton).toBeEnabled());

    await user.press(sendButton);

    await waitFor(() => {
      expect(screen.getByText('Password reset request is already in progress. Please wait a moment.')).toBeTruthy();
    });
  });
});
