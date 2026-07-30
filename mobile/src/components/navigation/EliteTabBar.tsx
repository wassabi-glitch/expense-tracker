import React from 'react';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useNavigationTheme } from '@/hooks/use-navigation-theme';
import { EliteSolidTabBar } from './EliteSolidTabBar';
import { EliteGlassTabBar } from './EliteGlassTabBar';

export function EliteTabBar(props: BottomTabBarProps) {
  const { tabBarPreference } = useNavigationTheme();

  if (tabBarPreference === 'glass') {
    return <EliteGlassTabBar {...props} />;
  }

  return <EliteSolidTabBar {...props} />;
}
