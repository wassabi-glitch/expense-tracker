import { act, screen, userEvent } from '@testing-library/react-native';

import i18next from '@/i18n';

import { server } from '../../../../tests/mocks/server';
import { renderWithProviders } from '../../../../tests/test-utils';

import { AuthPreviewScreen } from './auth-preview-screen';

describe('AuthPreviewScreen', () => {
  beforeEach(async () => {
    await i18next.changeLanguage('en');
  });

  it('cycles deterministic production-component fixtures without network activity', async () => {
    const requests: unknown[] = [];
    const recordRequest = (request: unknown) => requests.push(request);
    server.events.on('request:start', recordRequest);
    const user = userEvent.setup();

    try {
      await renderWithProviders(<AuthPreviewScreen />);
      expect(screen.getByText('Identity · Empty')).toBeOnTheScreen();

      await user.press(screen.getByRole('button', { name: 'Next preview state' }));
      expect(screen.getByText('Identity · Partial')).toBeOnTheScreen();
      expect(screen.getByLabelText('Email')).toHaveDisplayValue('demo@');

      await user.press(screen.getByRole('button', { name: 'Previous preview state' }));
      expect(screen.getByText('Identity · Empty')).toBeOnTheScreen();
      expect(requests).toHaveLength(0);
    } finally {
      server.events.removeListener('request:start', recordRequest);
    }
  });

  it('switches the real preview and production copy among all three languages', async () => {
    const user = userEvent.setup();
    await renderWithProviders(<AuthPreviewScreen />);

    await act(() => user.press(screen.getByRole('button', { name: 'RU' })));
    expect(
      await screen.findByRole('header', { name: 'Создайте аккаунт' }),
    ).toBeOnTheScreen();

    await act(() => user.press(screen.getByRole('button', { name: 'UZ' })));
    expect(
      await screen.findByRole('header', { name: 'Hisob yarating' }),
    ).toBeOnTheScreen();
  });
});
