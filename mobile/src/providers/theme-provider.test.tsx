import { render, screen, userEvent } from '@testing-library/react-native';
import { Pressable, Text } from 'react-native';
import { Uniwind } from 'uniwind';

import {
  AppThemeProvider,
  useAppTheme,
  useAppThemePreference,
} from './theme-provider';
function ThemeProbe() {
  const theme = useAppTheme();
  const { preference, setPreference } = useAppThemePreference();

  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => setPreference('dark')}>
      <Text>{`${preference}:${theme.mode}`}</Text>
    </Pressable>
  );
}

test('allows the user to override the system appearance', async () => {
  const user = userEvent.setup();

  await render(
    <AppThemeProvider>
      <ThemeProbe />
    </AppThemeProvider>,
  );

  expect(screen.getByText('system:light')).toBeOnTheScreen();

  await user.press(screen.getByRole('button'));

  expect(screen.getByText('dark:dark')).toBeOnTheScreen();
  expect(Uniwind.setTheme).toHaveBeenLastCalledWith('dark');
});
