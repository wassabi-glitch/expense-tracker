export const radii = {
  small: 8,
  medium: 12,
  large: 16,
  extraLarge: 24,
  full: 9999,
} as const;

export type RadiusToken = keyof typeof radii;
