export type WindowWidthClass = 'compact' | 'medium' | 'expanded';
export type WindowHeightClass = 'compact' | 'regular';

/**
 * Available-window breakpoints, expressed in React Native's density-independent
 * layout units. These intentionally describe space, not device names.
 */
export const windowBreakpoints = {
  width: {
    medium: 600,
    expanded: 840,
  },
  height: {
    regular: 480,
  },
} as const;

export function getWindowWidthClass(width: number): WindowWidthClass {
  if (width < windowBreakpoints.width.medium) {
    return 'compact';
  }

  if (width < windowBreakpoints.width.expanded) {
    return 'medium';
  }

  return 'expanded';
}

export function getWindowHeightClass(height: number): WindowHeightClass {
  if (height < windowBreakpoints.height.regular) {
    return 'compact';
  }

  return 'regular';
}
