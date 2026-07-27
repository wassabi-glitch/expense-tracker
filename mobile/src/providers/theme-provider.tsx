import { StatusBar } from 'expo-status-bar';
import { ThemeProvider as NavigationThemeProvider } from 'expo-router';
import { createContext, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react';
import { useColorScheme } from 'react-native';
import { Uniwind } from 'uniwind';

import {
  darkNavigationTheme,
  darkTheme,
  lightNavigationTheme,
  lightTheme,
  type AppTheme,
  type ThemePreference,
} from '@/theme';

type AppThemeContextValue = {
  theme: AppTheme;
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
};

const AppThemeContext = createContext<AppThemeContextValue | undefined>(undefined);

export function AppThemeProvider({ children }: PropsWithChildren) {
  const systemColorScheme = useColorScheme();
  const [preference, setPreference] = useState<ThemePreference>('system');
  const resolvedMode = preference === 'system' ? (systemColorScheme ?? 'light') : preference;
  const isDark = resolvedMode === 'dark';
  const theme = isDark ? darkTheme : lightTheme;
  const navigationTheme = isDark ? darkNavigationTheme : lightNavigationTheme;
  const contextValue = useMemo(
    () => ({ theme, preference, setPreference }),
    [preference, theme],
  );

  useEffect(() => {
    Uniwind.setTheme(preference);
  }, [preference]);

  return (
    <NavigationThemeProvider value={navigationTheme}>
      <AppThemeContext.Provider value={contextValue}>
        <StatusBar style={isDark ? 'light' : 'dark'} />
        {children}
      </AppThemeContext.Provider>
    </NavigationThemeProvider>
  );
}

export function useAppTheme() {
  const context = useContext(AppThemeContext);

  if (!context) {
    throw new Error('useAppTheme must be used inside AppThemeProvider.');
  }

  return context.theme;
}

export function useAppThemePreference() {
  const context = useContext(AppThemeContext);

  if (!context) {
    throw new Error('useAppThemePreference must be used inside AppThemeProvider.');
  }

  return {
    preference: context.preference,
    setPreference: context.setPreference,
  };
}
