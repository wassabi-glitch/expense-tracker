import { palette } from './palette';
import type { ThemeColors } from './types';

/** Fixed presentation tokens for the deliberately dark authentication canvas. */
export const authPresentationColors = {
  canvas: palette.zinc950,
  gradient: [palette.zinc950, palette.green950, palette.zinc950] as const,
  glow: ['rgba(34, 197, 94, 0.12)', 'rgba(20, 83, 45, 0.06)', 'rgba(9, 9, 11, 0)'] as const,
  google: {
    background: '#131314',
    border: '#8E918F',
    foreground: '#E3E3E3',
  },
} as const;

export const lightColors = {
  screen: palette.zinc50,
  surface: palette.white,
  surfaceSubtle: palette.zinc100,
  textPrimary: palette.zinc900,
  textSecondary: palette.zinc600,
  borderSubtle: palette.zinc200,
  borderControl: palette.zinc500,
  brand: {
    action: palette.green500,
    onAction: palette.green950,
  },
  status: {
    destructive: {
      main: palette.red600,
      onMain: palette.white,
      subtle: palette.red50,
      onSubtle: palette.red800,
      border: palette.red200,
    },
    success: {
      main: palette.emerald700,
      onMain: palette.white,
      subtle: palette.emerald50,
      onSubtle: palette.emerald800,
      border: palette.emerald200,
    },
    warning: {
      main: palette.amber700,
      onMain: palette.white,
      subtle: palette.amber50,
      onSubtle: palette.amber800,
      border: palette.amber200,
    },
    information: {
      main: palette.blue600,
      onMain: palette.white,
      subtle: palette.blue50,
      onSubtle: palette.blue800,
      border: palette.blue200,
    },
  },
  button: {
    filledDisabled: {
      background: palette.zinc200,
      content: palette.zinc500,
    },
    primary: {
      default: { background: palette.green500, content: palette.green950 },
      pressed: { background: palette.green600, content: palette.green950 },
      loading: { background: palette.green500, content: palette.green950 },
      focusOutline: palette.green700,
    },
    secondary: {
      default: { background: palette.zinc200, content: palette.zinc900 },
      pressed: { background: palette.zinc300, content: palette.zinc900 },
      loading: { background: palette.zinc200, content: palette.zinc900 },
      focusOutline: palette.green700,
    },
    destructive: {
      default: { background: palette.red600, content: palette.white },
      pressed: { background: palette.red700, content: palette.white },
      loading: { background: palette.red600, content: palette.white },
      focusOutline: palette.red700,
    },
    ghost: {
      default: { background: palette.transparent, content: palette.zinc900 },
      pressed: { background: palette.zinc100, content: palette.zinc900 },
      loading: { background: palette.transparent, content: palette.zinc900 },
      disabled: { background: palette.transparent, content: palette.zinc500 },
      focusOutline: palette.green700,
    },
  },
  selection: {
    indicator: palette.green600,
    onIndicator: palette.green950,
    subtle: palette.green100,
    content: palette.green800,
    unselectedBackground: palette.transparent,
    unselectedBorder: palette.zinc500,
  },
} as const satisfies ThemeColors;

export const darkColors = {
  screen: palette.zinc950,
  surface: palette.zinc900,
  surfaceSubtle: palette.zinc800,
  textPrimary: palette.zinc50,
  textSecondary: palette.zinc400,
  borderSubtle: palette.zinc800,
  borderControl: palette.zinc500,
  brand: {
    action: palette.green500,
    onAction: palette.green950,
  },
  status: {
    destructive: {
      main: palette.red400,
      onMain: palette.red950,
      subtle: palette.red950,
      onSubtle: palette.red300,
      border: palette.red900,
    },
    success: {
      main: palette.emerald400,
      onMain: palette.emerald950,
      subtle: palette.emerald950,
      onSubtle: palette.emerald300,
      border: palette.emerald800,
    },
    warning: {
      main: palette.amber400,
      onMain: palette.amber950,
      subtle: palette.amber950,
      onSubtle: palette.amber300,
      border: palette.amber800,
    },
    information: {
      main: palette.blue400,
      onMain: palette.blue950,
      subtle: palette.blue950,
      onSubtle: palette.blue300,
      border: palette.blue800,
    },
  },
  button: {
    filledDisabled: {
      background: palette.zinc800,
      content: palette.zinc400,
    },
    primary: {
      default: { background: palette.green500, content: palette.green950 },
      pressed: { background: palette.green400, content: palette.green950 },
      loading: { background: palette.green500, content: palette.green950 },
      focusOutline: palette.green300,
    },
    secondary: {
      default: { background: palette.zinc800, content: palette.zinc50 },
      pressed: { background: palette.zinc700, content: palette.zinc50 },
      loading: { background: palette.zinc800, content: palette.zinc50 },
      focusOutline: palette.green300,
    },
    destructive: {
      default: { background: palette.red400, content: palette.red950 },
      pressed: { background: palette.red300, content: palette.red950 },
      loading: { background: palette.red400, content: palette.red950 },
      focusOutline: palette.red300,
    },
    ghost: {
      default: { background: palette.transparent, content: palette.zinc50 },
      pressed: { background: palette.zinc800, content: palette.zinc50 },
      loading: { background: palette.transparent, content: palette.zinc50 },
      disabled: { background: palette.transparent, content: palette.zinc400 },
      focusOutline: palette.green300,
    },
  },
  selection: {
    indicator: palette.green400,
    onIndicator: palette.green950,
    subtle: palette.green900,
    content: palette.green300,
    unselectedBackground: palette.transparent,
    unselectedBorder: palette.zinc400,
  },
} as const satisfies ThemeColors;
