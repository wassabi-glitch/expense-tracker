import { act, screen, userEvent } from '@testing-library/react-native';

import i18next from '@/i18n';

import { server } from '../../../../tests/mocks/server';
import { renderWithProviders } from '../../../../tests/test-utils';

import { SignUpScreen } from './sign-up-screen';

describe('SignUpScreen presentation flow', () => {
  beforeEach(async () => {
    await i18next.changeLanguage('en');
  });

  it('renders the complete inert identity state without prohibited UI or network activity', async () => {
    const requests: unknown[] = [];
    const recordRequest = (request: unknown) => requests.push(request);
    server.events.on('request:start', recordRequest);
    const user = userEvent.setup();

    try {
      const onGooglePress = jest.fn();
      await renderWithProviders(<SignUpScreen onGooglePress={onGooglePress} />);

      expect(screen.getByRole('header', { name: 'Create your account' })).toBeOnTheScreen();
      expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeOnTheScreen();
      expect(screen.getByLabelText('Email')).toBeOnTheScreen();
      expect(screen.getByLabelText('Username')).toBeOnTheScreen();
      expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Sign in' })).toBeOnTheScreen();
      expect(screen.queryByText(/Sarflog/i)).not.toBeOnTheScreen();
      expect(screen.queryByText(/step\s*[12]/i)).not.toBeOnTheScreen();

      await user.press(screen.getByRole('button', { name: 'Continue with Google' }));
      expect(onGooglePress).toHaveBeenCalledTimes(1);

      await user.press(screen.getByRole('button', { name: 'Sign in' }));
      expect(requests).toHaveLength(0);
    } finally {
      server.events.removeListener('request:start', recordRequest);
    }
  });

  it('gates progression and preserves identity and password values across back navigation', async () => {
    const user = userEvent.setup();
    await renderWithProviders(<SignUpScreen />);

    await user.type(screen.getByLabelText('Email'), 'demo@example.com');
    await user.type(screen.getByLabelText('Username'), 'demo.user');
    const continueButton = screen.getByRole('button', { name: 'Continue' });
    expect(continueButton).toBeEnabled();
    await user.press(continueButton);

    expect(screen.getByRole('header', { name: 'Create a password' })).toBeOnTheScreen();
    await user.type(screen.getByLabelText('Password'), 'SafePass1!');
    expect(screen.getByRole('button', { name: 'Create account' })).toBeEnabled();
    await user.press(screen.getByRole('button', { name: 'Back' }));

    expect(screen.getByLabelText('Email')).toHaveDisplayValue('demo@example.com');
    expect(screen.getByLabelText('Username')).toHaveDisplayValue('demo.user');
    await user.press(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.getByLabelText('Password')).toHaveDisplayValue('SafePass1!');
  });

  it('updates password rules, toggles visibility without value loss, and prevents duplicate creation', async () => {
    const onCreateAccount = jest.fn();
    const user = userEvent.setup();
    await renderWithProviders(
      <SignUpScreen
        initialStep="password"
        initialValues={{ email: 'demo@example.com', username: 'demo.user' }}
        onCreateAccount={onCreateAccount}
      />,
    );

    const passwordInput = screen.getByLabelText('Password');
    await user.type(passwordInput, 'SafePass1!');
    expect(screen.getByLabelText('8–64 characters. Satisfied')).toBeOnTheScreen();
    expect(screen.getByLabelText('Includes a special character. Satisfied')).toBeOnTheScreen();

    await user.press(screen.getByRole('button', { name: 'Show password' }));
    expect(screen.getByRole('button', { name: 'Hide password' })).toBeOnTheScreen();
    expect(passwordInput).toHaveDisplayValue('SafePass1!');

    const createButton = screen.getByRole('button', { name: 'Create account' });
    await user.press(createButton);
    await user.press(createButton);
    expect(onCreateAccount).toHaveBeenCalledTimes(1);
    expect(onCreateAccount).toHaveBeenCalledWith({
      email: 'demo@example.com',
      password: 'SafePass1!',
      username: 'demo.user',
    });
  });

  it('exposes pending, field-error, and reduced-motion states as usable UI', async () => {
    const { rerender } = await renderWithProviders(
      <SignUpScreen
        createAccountState="pending"
        initialStep="password"
        initialValues={{
          email: 'demo@example.com',
          password: 'SafePass1!',
          username: 'demo.user',
        }}
      />,
    );

    expect(screen.getByRole('button', { name: 'Creating account' })).toBeDisabled();

    await rerender(
      <SignUpScreen
        fieldErrors={{ email: true, username: true }}
        initialValues={{ email: 'wrong', username: 'x' }}
        key="identity-error"
        reduceMotion
      />,
    );
    expect(screen.getByText('Enter a valid email address.')).toBeOnTheScreen();
    expect(screen.getByText('Use 3–32 letters, numbers, dots, or underscores.')).toBeOnTheScreen();
  });

  it('renders the real Russian and Uzbek localized signup copy', async () => {
    const { rerender } = await renderWithProviders(<SignUpScreen />);

    await act(() => i18next.changeLanguage('ru'));
    await rerender(<SignUpScreen />);
    expect(
      await screen.findByRole('header', { name: 'Создайте аккаунт' }),
    ).toBeOnTheScreen();

    await act(() => i18next.changeLanguage('uz'));
    await rerender(<SignUpScreen />);
    expect(
      await screen.findByRole('header', { name: 'Hisob yarating' }),
    ).toBeOnTheScreen();
  });
});
