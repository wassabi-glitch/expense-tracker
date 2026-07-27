import { spacing } from '@/theme';

import type { WindowWidthClass } from './window-size';

export type ResponsiveLayoutMetrics = {
  screenGutter: number;
  paneGap: number;
};

/** Layout spacing selected by the current available-window width class. */
export const responsiveLayoutMetrics = {
  compact: {
    screenGutter: spacing.md,
    paneGap: spacing.md,
  },
  medium: {
    screenGutter: spacing.lg,
    paneGap: spacing.lg,
  },
  expanded: {
    screenGutter: spacing.xl,
    paneGap: spacing.lg,
  },
} as const satisfies Record<WindowWidthClass, ResponsiveLayoutMetrics>;

/**
 * Content caps are selected by a screen's job, not automatically by device size.
 * A form should remain focused on a tablet; a true two-pane screen may grow wider.
 */
export const contentMaxWidths = {
  form: 560,
  standard: 800,
  twoPane: 1200,
} as const;
