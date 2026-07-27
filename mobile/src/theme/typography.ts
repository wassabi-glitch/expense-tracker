import { Inter_400Regular } from '@expo-google-fonts/inter/400Regular';
import { Inter_600SemiBold } from '@expo-google-fonts/inter/600SemiBold';
import { Platform, type TextStyle } from 'react-native';

export const fontAssets = {
  Inter_400Regular,
  Inter_600SemiBold,
} as const;

export const fontFamilies = {
  regular: 'Inter_400Regular',
  semibold: 'Inter_600SemiBold',
  monospace:
    Platform.select({
      ios: 'ui-monospace',
      android: 'monospace',
      web: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    }) ?? 'monospace',
} as const;

export const fontWeights = {
  regular: 400,
  semibold: 600,
} as const;

const tabularNumerals: TextStyle['fontVariant'] = ['tabular-nums'];

export const typography = {
  authTitle: {
    fontFamily: fontFamilies.semibold,
    fontSize: 32,
    lineHeight: 40,
  },
  displayAmount: {
    fontFamily: fontFamilies.semibold,
    fontSize: 32,
    lineHeight: 40,
    fontVariant: tabularNumerals,
  },
  title: {
    fontFamily: fontFamilies.semibold,
    fontSize: 20,
    lineHeight: 28,
  },
  body: {
    fontFamily: fontFamilies.regular,
    fontSize: 16,
    lineHeight: 24,
  },
  supporting: {
    fontFamily: fontFamilies.regular,
    fontSize: 13,
    lineHeight: 18,
  },
  buttonLabel: {
    fontFamily: fontFamilies.semibold,
    fontSize: 16,
    lineHeight: 24,
  },
} as const satisfies Record<string, TextStyle>;

export type TypographyStyle = keyof typeof typography;
