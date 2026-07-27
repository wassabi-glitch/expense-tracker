import { screen, userEvent } from '@testing-library/react-native';
import { http, HttpResponse } from 'msw';

import VerifyEmailRoute from '@/app/(auth)/verify-email';
import { server } from '../../../../tests/mocks/server';
import { renderWithProviders } from '../../../../tests/test-utils';

const mockPush = jest.fn();
const mockReplace = jest.fn();
let mockParams = { token: 'mock-verify-token' };

jest.mock('expo-router', () => {
  const actual = jest.requireActual('expo-router');
  return {
    ...actual,
    useRouter: () => ({
      push: mockPush,
      replace: mockReplace,
    }),
    useLocalSearchParams: () => mockParams,
  };
});

describe('Auth Integration: VerifyEmailRoute', () => {
  jest.setTimeout(15000);
  beforeEach(() => {
    jest.clearAllMocks();
    mockParams = { token: 'mock-verify-token' };
  });

  it('renders in ready state and handles successful verification', async () => {
    const user = userEvent.setup();
    await renderWithProviders(<VerifyEmailRoute />);
    
    // Verify it doesn't auto-verify
    expect(screen.getByText('Ready to verify')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Verify my account' })).toBeEnabled();

    // Mock success response
    server.use(
      http.post('*/api/auth/verify-email', () => {
        return HttpResponse.json({ message: 'Verified' }, { status: 200 });
      })
    );

    // Press Verify
    const verifyButton = screen.getByRole('button', { name: 'Verify my account' });
    await user.press(verifyButton);

    // Wait for success UI
    const continueButton = await screen.findByRole('button', { name: 'Continue to sign in' });
    expect(continueButton).toBeTruthy();
    
    // Press continue
    await user.press(continueButton);
    expect(mockReplace).toHaveBeenCalledWith('/(auth)/sign-in');
  });

  it('displays error if the link is invalid or expired', async () => {
    const user = userEvent.setup();
    await renderWithProviders(<VerifyEmailRoute />);
    
    // Mock error response
    server.use(
      http.post('*/api/auth/verify-email', () => {
        return HttpResponse.json(
          { detail: 'auth.verify_email_token_invalid_or_expired' },
          { status: 400 }
        );
      })
    );

    // Press Verify
    const verifyButton = screen.getByRole('button', { name: 'Verify my account' });
    await user.press(verifyButton);

    // Wait for error UI
    const newLinkButton = await screen.findByRole('button', { name: 'Request new link' });
    expect(newLinkButton).toBeTruthy();

    // Press request new link
    await user.press(newLinkButton);
    expect(mockReplace).toHaveBeenCalledWith('/(auth)/sign-in');
  });

  it('immediately errors if no token is provided', async () => {
    mockParams = { token: '' };
    const user = userEvent.setup();
    await renderWithProviders(<VerifyEmailRoute />);
    
    // Press Verify
    const verifyButton = screen.getByRole('button', { name: 'Verify my account' });
    await user.press(verifyButton);

    // Wait for error UI
    const newLinkButton = await screen.findByRole('button', { name: 'Request new link' });
    expect(newLinkButton).toBeTruthy();
    
    // Request shouldn't have hit the server (or if it did, it's blocked, but the local check prevents it)
  });

  it('explicitly tests i18n fallback logic for rate limited error', async () => {
    const user = userEvent.setup();
    await renderWithProviders(<VerifyEmailRoute />);
    
    // Mock error response
    server.use(
      http.post('*/api/auth/verify-email', () => {
        return HttpResponse.json(
          { detail: 'auth.verify_email_rate_limited' },
          { status: 429 }
        );
      })
    );

    const verifyButton = screen.getByRole('button', { name: 'Verify my account' });
    await user.press(verifyButton);

    // Wait for the specific translated error text to appear in the UI
    const rateLimitedText = await screen.findByText('Too many verification attempts. Please wait a moment.');
    expect(rateLimitedText).toBeTruthy();
  });
});
