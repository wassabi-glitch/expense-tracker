import { DarkTheme as RouterDarkTheme, DefaultTheme as RouterLightTheme } from 'expo-router';

import { darkColors, lightColors } from './colors';
import { depth } from './elevation';
import { motion } from './motion';
import { radii } from './radii';
import { sizes } from './sizes';
import { spacing } from './spacing';
import { fontFamilies, fontWeights, typography } from './typography';

const sharedFoundation = {
  typography,
  fontFamilies,
  fontWeights,
  spacing,
  radii,
  sizes,
  motion,
  depth,
} as const;

export const lightTheme = {
  mode: 'light',
  colors: lightColors,
  ...sharedFoundation,
} as const;

export const darkTheme = {
  mode: 'dark',
  colors: darkColors,
  ...sharedFoundation,
} as const;

export type AppTheme = typeof lightTheme | typeof darkTheme;

/** Adapts Sarflog's colors to the navigation theme expected by Expo Router. */
export const lightNavigationTheme = {
  ...RouterLightTheme,
  colors: {
    ...RouterLightTheme.colors,
    primary: lightColors.selection.indicator,
    background: lightColors.screen,
    card: lightColors.surface,
    text: lightColors.textPrimary,
    border: lightColors.borderSubtle,
    notification: lightColors.status.information.main,
  },
};

export const darkNavigationTheme = {
  ...RouterDarkTheme,
  colors: {
    ...RouterDarkTheme.colors,
    primary: darkColors.selection.indicator,
    background: darkColors.screen,
    card: darkColors.surface,
    text: darkColors.textPrimary,
    border: darkColors.borderSubtle,
    notification: darkColors.status.information.main,
  },
};
