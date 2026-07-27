/**
 * Raw color ingredients used to build Sarflog's semantic themes.
 *
 * Keep this module private to `src/theme`. Product code should ask for a
 * semantic role from the active theme instead of importing a shade directly.
 */
export const palette = {
  transparent: 'transparent',
  white: '#FFFFFF',

  zinc50: '#FAFAFA',
  zinc100: '#F4F4F5',
  zinc200: '#E4E4E7',
  zinc300: '#D4D4D8',
  zinc400: '#A1A1AA',
  zinc500: '#71717A',
  zinc600: '#52525B',
  zinc700: '#3F3F46',
  zinc800: '#27272A',
  zinc900: '#18181B',
  zinc950: '#09090B',

  green100: '#DCFCE7',
  green300: '#86EFAC',
  green400: '#4ADE80',
  green500: '#22C55E',
  green600: '#16A34A',
  green700: '#15803D',
  green800: '#166534',
  green900: '#14532D',
  green950: '#052E16',

  red50: '#FEF2F2',
  red200: '#FECACA',
  red300: '#FCA5A5',
  red400: '#F87171',
  red600: '#DC2626',
  red700: '#B91C1C',
  red800: '#991B1B',
  red900: '#7F1D1D',
  red950: '#450A0A',

  emerald50: '#ECFDF5',
  emerald200: '#A7F3D0',
  emerald300: '#6EE7B7',
  emerald400: '#34D399',
  emerald700: '#047857',
  emerald800: '#065F46',
  emerald950: '#022C22',

  amber50: '#FFFBEB',
  amber200: '#FDE68A',
  amber300: '#FCD34D',
  amber400: '#FBBF24',
  amber700: '#B45309',
  amber800: '#92400E',
  amber950: '#451A03',

  blue50: '#EFF6FF',
  blue200: '#BFDBFE',
  blue300: '#93C5FD',
  blue400: '#60A5FA',
  blue600: '#2563EB',
  blue800: '#1E40AF',
  blue950: '#172554',
} as const;
