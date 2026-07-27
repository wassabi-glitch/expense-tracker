import { useQueryClient } from '@tanstack/react-query';
import { screen } from '@testing-library/react-native';
import { Text } from 'react-native';

import { renderWithProviders } from './test-utils';

function QueryClientProbe() {
  const queryClient = useQueryClient();
  const retriesAreDisabled =
    queryClient.getDefaultOptions().queries?.retry === false;

  return <Text>{retriesAreDisabled ? 'deterministic' : 'retrying'}</Text>;
}

test('provides an isolated query client with retries disabled', async () => {
  const view1 = await renderWithProviders(<QueryClientProbe />);

  expect(screen.getByText('deterministic')).toBeOnTheScreen();
  await view1.unmount();

  const view2 = await renderWithProviders(<QueryClientProbe />);

  expect(screen.getByText('deterministic')).toBeOnTheScreen();
  expect(view1.queryClient).not.toBe(view2.queryClient);
});
