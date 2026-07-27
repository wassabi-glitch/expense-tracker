import { useWindowDimensions } from 'react-native';

import { responsiveLayoutMetrics } from './metrics';
import {
  getWindowHeightClass,
  getWindowWidthClass,
  windowBreakpoints,
} from './window-size';

type WindowDimensions = ReturnType<typeof useWindowDimensions>;

/** Converts the native window measurement into Sarflog's layout contract. */
export function getAdaptiveLayout({
  width,
  height,
  fontScale,
  scale,
}: WindowDimensions) {
  const widthClass = getWindowWidthClass(width);
  const heightClass = getWindowHeightClass(height);

  return {
    width,
    height,
    fontScale,
    pixelRatio: scale,
    widthClass,
    heightClass,
    metrics: responsiveLayoutMetrics[widthClass],
    prefersTwoPane:
      width >= windowBreakpoints.width.expanded && heightClass !== 'compact',
  } as const;
}

export function useAdaptiveLayout() {
  return getAdaptiveLayout(useWindowDimensions());
}
