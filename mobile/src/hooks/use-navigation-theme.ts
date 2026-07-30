import { create } from 'zustand';

export type TabBarPreference = 'solid' | 'glass';

interface NavigationThemeState {
  tabBarPreference: TabBarPreference;
  setTabBarPreference: (preference: TabBarPreference) => void;
}

export const useNavigationTheme = create<NavigationThemeState>((set) => ({
  tabBarPreference: 'glass', // Default to glass
  setTabBarPreference: (preference) => set({ tabBarPreference: preference }),
}));
