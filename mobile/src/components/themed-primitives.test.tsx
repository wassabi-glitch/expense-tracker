import { screen } from '@testing-library/react-native';

import { HintRow } from './hint-row';
import { ThemedText } from './themed-text';
import { ThemedView } from './themed-view';
import { lightTheme } from '@/theme';
import { renderWithProviders } from '../../tests/test-utils';

test('applies semantic theme colors to reusable text and surfaces', async () => {
  await renderWithProviders(
    <ThemedView testID="selection-surface" type="selectionSubtle">
      <ThemedText type="linkPrimary" themeColor="selectionContent">
        Review details
      </ThemedText>
    </ThemedView>,
  );

  expect(screen.getByTestId('selection-surface')).toHaveStyle({
    backgroundColor: lightTheme.colors.selection.subtle,
  });
  expect(screen.getByText('Review details')).toHaveStyle({
    color: lightTheme.colors.selection.content,
    textDecorationLine: 'underline',
  });
});

test('renders reusable hint content supplied by a caller', async () => {
  await renderWithProviders(
    <HintRow title="API boundary" hint="tests/mocks/server.ts" />,
  );

  expect(screen.getByText('API boundary')).toBeOnTheScreen();
  expect(screen.getByText('tests/mocks/server.ts')).toBeOnTheScreen();
});
