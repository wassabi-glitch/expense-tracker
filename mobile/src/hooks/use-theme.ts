import { useAppTheme, useAppThemePreference } from '@/providers/theme-provider';

export function useTheme() {
  return useAppTheme();
}

export function useThemePreference() {
  return useAppThemePreference();
}
