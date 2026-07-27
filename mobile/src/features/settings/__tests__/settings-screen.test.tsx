import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react-native';
import { http, HttpResponse } from 'msw';
import { SettingsScreen } from '../screens/settings-screen';
import { server } from '../../../../tests/mocks/server';
import { renderWithProviders } from '../../../../tests/test-utils';
import { useAuthStore } from '@/features/auth/hooks/use-auth-store';
import { saveRefreshToken } from '@/lib/auth/secure-store';
import { setAccessToken } from '@/lib/api/client';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

jest.mock('@react-native-google-signin/google-signin', () => ({
  GoogleSignin: {
    configure: jest.fn(),
    signOut: jest.fn().mockResolvedValue(true),
  },
}));

jest.mock('@/lib/auth/secure-store', () => ({
  ...jest.requireActual('@/lib/auth/secure-store'),
  getRefreshToken: jest.fn().mockResolvedValue('fake_refresh'),
}));

describe('SettingsScreen Integration', () => {
  beforeEach(async () => {
    setAccessToken('fake_access');
    useAuthStore.setState({ status: 'authenticated' });
  });

  afterEach(async () => {
    await act(async () => {
      useAuthStore.setState({ status: 'unauthenticated' });
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    server.resetHandlers();
  });

  beforeEach(() => {
    server.use(
      http.get('*/users/me', () => {
        return HttpResponse.json({ has_local_password: true });
      })
    );
  });

  it('renders correctly', async () => {
    await renderWithProviders(<SettingsScreen />);
    expect(await screen.findByTestId('btn-logout')).toBeTruthy();
    expect(await screen.findByTestId('btn-logout-all')).toBeTruthy();
  });

  it('handles sign out submission', async () => {
    let logoutCalled = false;
    server.use(
      http.post('*/auth/mobile/logout', () => {
        logoutCalled = true;
        return HttpResponse.json({ message: 'ok' });
      })
    );

    await renderWithProviders(<SettingsScreen />);
    
    const signOutButton = await screen.findByTestId('btn-logout');
    
    await act(async () => {
      fireEvent.press(signOutButton);
    });

    await waitFor(() => {
      expect(logoutCalled).toBe(true);
      expect(useAuthStore.getState().status).toBe('unauthenticated');
    });
  });

  it('handles sign out from all devices', async () => {
    let logoutAllCalled = false;
    server.use(
      http.post('*/auth/logout-all', () => {
        logoutAllCalled = true;
        return HttpResponse.json({ message: 'ok' });
      })
    );

    await renderWithProviders(<SettingsScreen />);
    
    const signOutAllButton = await screen.findByTestId('btn-logout-all');
    
    await act(async () => {
      fireEvent.press(signOutAllButton);
    });

    await waitFor(() => {
      expect(logoutAllCalled).toBe(true);
      expect(useAuthStore.getState().status).toBe('unauthenticated');
    });
  });
});
