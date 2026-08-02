import { screen, userEvent } from '@testing-library/react-native';
import { Text } from 'react-native';

import { server } from '../../../../tests/mocks/server';
import { renderWithProviders } from '../../../../tests/test-utils';

import { AuthScreenLayout } from './auth-screen-layout';

describe('AuthScreenLayout', () => {
  it('renders the localized shell contract without branding, progress, or network activity', async () => {
    const requests: unknown[] = [];
    const recordRequest = (request: unknown) => requests.push(request);
    server.events.on('request:start', recordRequest);

    try {
      await renderWithProviders(
        <AuthScreenLayout supportingText="Supporting copy" title="Auth heading">
          <Text>Screen content</Text>
        </AuthScreenLayout>,
      );

      expect(screen.getByRole('header', { name: 'Auth heading' })).toBeOnTheScreen();
      expect(screen.getByText('Supporting copy')).toBeOnTheScreen();
      expect(screen.getByText('Screen content')).toBeOnTheScreen();
      expect(screen.getByTestId('auth-canvas-glow')).toBeOnTheScreen();
      expect(screen.queryByText(/Sarflog/i)).not.toBeOnTheScreen();
      expect(screen.queryByText(/step|progress/i)).not.toBeOnTheScreen();
      expect(requests).toHaveLength(0);
    } finally {
      server.events.removeListener('request:start', recordRequest);
    }
  });

  it('provides an optional accessible back action', async () => {
    const onBack = jest.fn();
    const user = userEvent.setup();
    await renderWithProviders(
      <AuthScreenLayout
        backLabel="Back"
        onBack={onBack}
        supportingText="Supporting copy"
        title="Auth heading"
      >
        <Text>Screen content</Text>
      </AuthScreenLayout>,
    );

    await user.press(screen.getByRole('button', { name: 'Back' }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
