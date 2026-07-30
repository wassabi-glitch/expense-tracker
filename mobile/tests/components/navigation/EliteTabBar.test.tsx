import React from 'react';
import { render } from '@testing-library/react-native';
import { EliteTabBar } from '@/components/navigation/EliteTabBar';
import { useNavigationTheme } from '@/hooks/use-navigation-theme';
import { View } from 'react-native';

jest.mock('@/hooks/use-navigation-theme', () => ({
  useNavigationTheme: jest.fn(),
}));

jest.mock('@/components/navigation/EliteGlassTabBar', () => {
  const { View } = require('react-native');
  return { EliteGlassTabBar: () => <View testID="glass-tab-bar" /> };
});

jest.mock('@/components/navigation/EliteSolidTabBar', () => {
  const { View } = require('react-native');
  return { EliteSolidTabBar: () => <View testID="solid-tab-bar" /> };
});

describe('EliteTabBar', () => {
  const mockProps: any = {
    state: { routes: [] },
    descriptors: {},
    navigation: {},
  };

  it('renders EliteGlassTabBar when preference is glass', async () => {
    (useNavigationTheme as unknown as jest.Mock).mockReturnValue({ tabBarPreference: 'glass' });
    const { getByTestId } = await render(<EliteTabBar {...mockProps} />);
    expect(getByTestId('glass-tab-bar')).toBeTruthy();
  });

  it('renders EliteSolidTabBar when preference is solid', async () => {
    (useNavigationTheme as unknown as jest.Mock).mockReturnValue({ tabBarPreference: 'solid' });
    const { getByTestId } = await render(<EliteTabBar {...mockProps} />);
    expect(getByTestId('solid-tab-bar')).toBeTruthy();
  });
});
