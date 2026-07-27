import { StyleSheet, Text, type TextProps } from 'react-native';

import { useTheme } from '@/hooks/use-theme';
import { fontFamilies, typography, type ThemeTextColorRole } from '@/theme';

export type ThemedTextProps = TextProps & {
  type?: 'default' | 'title' | 'small' | 'smallBold' | 'subtitle' | 'link' | 'linkPrimary' | 'code';
  themeColor?: ThemeTextColorRole;
};

export function ThemedText({ style, type = 'default', themeColor, ...rest }: ThemedTextProps) {
  const theme = useTheme();
  const color =
    themeColor === 'selectionContent'
      ? theme.colors.selection.content
      : theme.colors[themeColor ?? 'textPrimary'];

  return (
    <Text
      style={[
        { color },
        type === 'default' && styles.default,
        type === 'title' && styles.title,
        type === 'small' && styles.small,
        type === 'smallBold' && styles.smallBold,
        type === 'subtitle' && styles.subtitle,
        type === 'link' && styles.link,
        type === 'linkPrimary' && styles.linkPrimary,
        type === 'code' && styles.code,
        style,
      ]}
      {...rest}
    />
  );
}

const styles = StyleSheet.create({
  small: {
    ...typography.supporting,
  },
  smallBold: {
    ...typography.supporting,
    fontFamily: fontFamilies.semibold,
  },
  default: {
    ...typography.body,
  },
  title: {
    ...typography.title,
  },
  subtitle: {
    ...typography.title,
  },
  link: {
    ...typography.supporting,
    textDecorationLine: 'underline',
  },
  linkPrimary: {
    ...typography.supporting,
    fontFamily: fontFamilies.semibold,
    textDecorationLine: 'underline',
  },
  code: {
    fontFamily: fontFamilies.monospace,
    fontSize: 13,
    lineHeight: 18,
  },
});
