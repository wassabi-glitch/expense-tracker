import { Platform } from 'react-native';

import { contentMaxWidths } from '@/layout';

/** Temporary Expo scaffold inset; replace it when customer navigation is implemented. */
export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;

/** Backward-compatible alias for scaffold components using the standard content cap. */
export const MaxContentWidth = contentMaxWidths.standard;
