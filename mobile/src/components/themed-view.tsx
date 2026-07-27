import { View, type ViewProps } from 'react-native';

import { useTheme } from '@/hooks/use-theme';
import type { ThemeSurfaceColorRole } from '@/theme';

export type ThemedViewProps = ViewProps & {
  type?: ThemeSurfaceColorRole;
};

export function ThemedView({ style, type = 'screen', ...otherProps }: ThemedViewProps) {
  const theme = useTheme();
  const backgroundColor =
    type === 'selectionSubtle' ? theme.colors.selection.subtle : theme.colors[type];

  return <View style={[{ backgroundColor }, style]} {...otherProps} />;
}
