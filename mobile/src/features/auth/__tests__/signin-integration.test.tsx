import { screen, userEvent, waitFor } from '@testing-library/react-native';
import { http, HttpResponse } from 'msw';
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
    useLocalSearchParams: () => ({ error: 'auth.refresh_token_invalid' }),
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

describe('SignInRoute Integration', () => {
  jest.setTimeout(15000);

  it('displays session expired error if error parameter is passed', async () => {
    await renderWithProviders(<SignInRoute />);

    await waitFor(() => {
      expect(screen.getByText('auth.signIn.errors.sessionExpired')).toBeTruthy();
    });
  });

  it('handles sign in submission and MSW success', async () => {
    server.use(
      http.post('*/auth/mobile/sign-in', () => {
        return HttpResponse.json({
          access_token: 'test_access',
          refresh_token: 'test_refresh',
          token_type: 'bearer',
        });
      })
    );

    const user = userEvent.setup();
    await renderWithProviders(<SignInRoute />);
    
    const emailInput = screen.getByPlaceholderText('Enter your email');
    const passwordInput = screen.getByPlaceholderText('Enter your password');
    const signInButton = screen.getByRole('button', { name: 'Sign in' });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'Password123!');
    
    await waitFor(() => {
      expect(signInButton).toBeEnabled();
    });

    await user.press(signInButton);

    await waitFor(() => {
      // Assuming loading spinner is gone
      expect(screen.queryByRole('button', { name: 'Signing in...' })).toBeFalsy();
    });
  });
});
