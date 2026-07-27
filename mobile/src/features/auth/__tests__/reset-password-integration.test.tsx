import { screen, userEvent, waitFor } from '@testing-library/react-native';
import { http, HttpResponse } from 'msw';
import ResetPasswordRoute from '@/app/(auth)/reset-password';
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
    }),
    useLocalSearchParams: () => ({ token: 'mock-token-123' }),
  };
});

describe('ResetPasswordRoute Integration', () => {
  jest.setTimeout(15000);

  it('renders form and handles successful submission', async () => {
    server.use(
      http.post('*/auth/reset-password', () => {
        return HttpResponse.json({ message: 'Password reset successfully' });
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<ResetPasswordRoute />);
    
    const passwordInput = screen.getByPlaceholderText('Enter new password');
    const submitButton = screen.getByRole('button', { name: 'Reset password' });

    // Initial state: button should be disabled because password is empty
    expect(submitButton).toBeDisabled();

    await user.type(passwordInput, 'ValidPass1!');
    
    await waitFor(() => {
      expect(submitButton).toBeEnabled();
    });

    await user.press(submitButton);

    // It should transition to success state
    await waitFor(() => {
      expect(screen.getByText('Password Reset!')).toBeTruthy();
      expect(screen.getByText('Your password has been reset successfully. Redirecting to sign in...')).toBeTruthy();
    });
  });

  it('displays rate limit error from backend', async () => {
    server.use(
      http.post('*/auth/reset-password', () => {
        return HttpResponse.json(
          { detail: 'auth.reset_password_rate_limited' },
          { status: 429 }
        );
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<ResetPasswordRoute />);
    
    const passwordInput = screen.getByPlaceholderText('Enter new password');
    await user.type(passwordInput, 'ValidPass1!');
    
    const submitButton = screen.getByRole('button', { name: 'Reset password' });
    await waitFor(() => expect(submitButton).toBeEnabled());

    await user.press(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Link Expired or Invalid')).toBeTruthy();
      expect(screen.getByText('Too many password reset attempts. Please try again later.')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Request new link' })).toBeTruthy();
    });
  });

  it('displays invalid token error from backend', async () => {
    server.use(
      http.post('*/auth/reset-password', () => {
        return HttpResponse.json(
          { detail: 'auth.invalid_token' },
          { status: 400 }
        );
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<ResetPasswordRoute />);
    
    const passwordInput = screen.getByPlaceholderText('Enter new password');
    await user.type(passwordInput, 'ValidPass1!');
    
    const submitButton = screen.getByRole('button', { name: 'Reset password' });
    await waitFor(() => expect(submitButton).toBeEnabled());

    await user.press(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Link Expired or Invalid')).toBeTruthy();
      expect(screen.getByText('Invalid or expired reset token.')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Request new link' })).toBeTruthy();
    });
  });

  it('displays idempotency conflict error from backend', async () => {
    server.use(
      http.post('*/auth/reset-password', () => {
        return HttpResponse.json(
          { detail: 'auth.idempotency_conflict_in_progress' },
          { status: 409 }
        );
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<ResetPasswordRoute />);
    
    const passwordInput = screen.getByPlaceholderText('Enter new password');
    await user.type(passwordInput, 'ValidPass1!');
    
    const submitButton = screen.getByRole('button', { name: 'Reset password' });
    await waitFor(() => expect(submitButton).toBeEnabled());

    await user.press(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Link Expired or Invalid')).toBeTruthy(); // verifyError title state
      expect(screen.getByText('Password reset is already in progress. Please wait a moment.')).toBeTruthy();
    });
  });
});
