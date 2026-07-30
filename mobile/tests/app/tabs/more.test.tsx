import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import MoreTab from '@/app/(tabs)/more';
import { useThemePreference } from '@/hooks/use-theme';
import { useRouter } from 'expo-router';

// Mocks
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));
jest.mock('@/hooks/use-theme', () => ({
  useTheme: () => ({
    colors: { screen: '#000', surface: '#000', surfaceSubtle: '#111', textPrimary: '#FFF', textSecondary: '#CCC', borderSubtle: '#222', borderControl: '#333', brand: { action: 'green' } },
    typography: { title: {}, body: {}, caption: {}, buttonLabel: {} },
  }),
  useThemePreference: jest.fn(),
}));
jest.mock('expo-router', () => ({
  useRouter: jest.fn(),
}));
jest.mock('react-native-safe-area-context', () => ({
  useSafeAreaInsets: () => ({ top: 40, bottom: 20 }),
}));
jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Ionicons',
}));

describe('MoreTab Screen', () => {
  const setPreferenceMock = jest.fn();
  const routerPushMock = jest.fn();

  beforeEach(() => {
    (useThemePreference as jest.Mock).mockReturnValue({
      preference: 'system',
      setPreference: setPreferenceMock,
    });
    (useRouter as jest.Mock).mockReturnValue({
      push: routerPushMock,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly', async () => {
    const { getByText } = await render(<MoreTab />);
    // Check Top Bar Title
    expect(getByText('layout.tabs.more')).toBeTruthy();
    // Check Groups
    expect(getByText('moreScreen.groups.finances')).toBeTruthy();
    expect(getByText('moreScreen.groups.insights')).toBeTruthy();
    expect(getByText('moreScreen.groups.general')).toBeTruthy();
  });

  it('cycles theme preference on Appearance press', async () => {
    const { getByText } = await render(<MoreTab />);
    fireEvent.press(getByText('moreScreen.items.appearance'));
    expect(setPreferenceMock).toHaveBeenCalledWith('dark');
  });

  it('navigates on item press', async () => {
    const { getByText } = await render(<MoreTab />);
    fireEvent.press(getByText('moreScreen.items.settings'));
    expect(routerPushMock).toHaveBeenCalledWith('/settings');
  });
});
