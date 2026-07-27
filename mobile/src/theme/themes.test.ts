import {
  darkNavigationTheme,
  darkTheme,
  lightNavigationTheme,
  lightTheme,
} from './themes';

describe('application theme contracts', () => {
  test.each([
    [lightTheme, lightNavigationTheme],
    [darkTheme, darkNavigationTheme],
  ] as const)('maps product colors into the router theme', (theme, navigation) => {
    expect(navigation.colors).toMatchObject({
      primary: theme.colors.selection.indicator,
      background: theme.colors.screen,
      card: theme.colors.surface,
      text: theme.colors.textPrimary,
      border: theme.colors.borderSubtle,
      notification: theme.colors.status.information.main,
    });
  });

  test('shares non-color design tokens across light and dark modes', () => {
    expect(lightTheme.spacing).toBe(darkTheme.spacing);
    expect(lightTheme.typography).toBe(darkTheme.typography);
    expect(lightTheme.radii).toBe(darkTheme.radii);
  });
});
