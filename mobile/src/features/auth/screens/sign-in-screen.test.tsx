import { screen, userEvent } from '@testing-library/react-native';
import i18next from '@/i18n';
import { renderWithProviders } from '../../../../tests/test-utils';
import { SignInScreen } from './sign-in-screen';

describe('SignInScreen', () => {
  beforeEach(async () => {
    await i18next.changeLanguage('en');
  });

  it('renders sign-in form correctly', async () => {
    await renderWithProviders(<SignInScreen />);

    expect(screen.getByRole('header', { name: 'Sign in to your account' })).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeOnTheScreen();
    expect(screen.getByPlaceholderText('Enter your email')).toBeOnTheScreen();
    expect(screen.getByPlaceholderText('Enter your password')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Create account' })).toBeOnTheScreen();
  });

  it('triggers onGooglePress when Google button is clicked', async () => {
    const onGooglePress = jest.fn();
    const user = userEvent.setup();
    await renderWithProviders(<SignInScreen onGooglePress={onGooglePress} />);

    await user.press(screen.getByRole('button', { name: 'Continue with Google' }));
    expect(onGooglePress).toHaveBeenCalledTimes(1);
  });

  it('triggers onSignInPress with valid credentials', async () => {
    const onSignInPress = jest.fn();
    const user = userEvent.setup();
    await renderWithProviders(<SignInScreen onSignInPress={onSignInPress} />);

    await user.type(screen.getByPlaceholderText('Enter your email'), 'demo@example.com');
    await user.type(screen.getByPlaceholderText('Enter your password'), 'Password123!');

    const signInButton = screen.getByRole('button', { name: 'Sign in' });
    expect(signInButton).toBeEnabled();

    await user.press(signInButton);
    expect(onSignInPress).toHaveBeenCalledTimes(1);
    expect(onSignInPress).toHaveBeenCalledWith({ email: 'demo@example.com', password: 'Password123!' });
  });

  it('shows pending state for Google and Sign In buttons', async () => {
    const { rerender } = await renderWithProviders(<SignInScreen googleState="pending" />);
    expect(screen.getByRole('button', { name: 'Continue with Google' }).props.accessibilityState.busy).toBe(true);

    await rerender(<SignInScreen signInState="pending" initialValues={{ email: 'demo@example.com', password: 'password123' }} />);
    expect(screen.getByLabelText('Sign in').props.accessibilityState.busy).toBe(true);
  });
});
