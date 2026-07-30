import React from 'react';
import { fireEvent } from '@testing-library/react-native';
import { SettingsScreen } from '@/features/settings/screens/settings-screen';
import { renderWithProviders } from '../../../../tests/test-utils';
import { useNavigationTheme } from '@/hooks/use-navigation-theme';
import i18n from 'i18next';

const mockChangeLanguage = jest.fn();
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (k: string) => k,
    i18n: { changeLanguage: mockChangeLanguage, language: 'en' },
  }),
}));

jest.mock('@react-native-google-signin/google-signin', () => ({
  GoogleSignin: {
    configure: jest.fn(),
    signOut: jest.fn(),
  },
}));

describe('SettingsScreen Tab Bar & Language Controls', () => {
  it('toggles tab bar preference', async () => {
    // Reset store before test
    useNavigationTheme.setState({ tabBarPreference: 'glass' });
    
    const { getAllByRole } = await renderWithProviders(<SettingsScreen />);
    
    // The first switch in Settings is the Tab Bar Appearance
    const switches = getAllByRole('switch'); 
    fireEvent(switches[0], 'valueChange', false);
    
    // Expect the Zustand store to be updated
    expect(useNavigationTheme.getState().tabBarPreference).toBe('solid');
  });

  it('changes language on button press', async () => {
    const { getByText } = await renderWithProviders(<SettingsScreen />);
    
    fireEvent.press(getByText('Русский'));
    expect(mockChangeLanguage).toHaveBeenCalledWith('ru');
    
    fireEvent.press(getByText("O'zbek"));
    expect(mockChangeLanguage).toHaveBeenCalledWith('uz');
  });
});
