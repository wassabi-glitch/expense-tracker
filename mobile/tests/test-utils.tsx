import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  render,
  type RenderOptions,
  type RenderResult,
} from '@testing-library/react-native';
import { HeroUINativeProvider } from 'heroui-native/provider';
import type { PropsWithChildren, ReactElement } from 'react';

import { AppThemeProvider } from '@/providers/theme-provider';

const heroUITestConfig = {
  devInfo: { stylingPrinciples: false },
} as const;

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

type TestRenderResult = RenderResult & {
  queryClient: QueryClient;
};

export function renderWithProviders(
  ui: ReactElement,
  options: Omit<RenderOptions, 'wrapper'> = {},
): Promise<TestRenderResult> {
  const queryClient = createTestQueryClient();

  function TestProviders({ children }: PropsWithChildren) {
    return (
      <QueryClientProvider client={queryClient}>
        <AppThemeProvider>
          <HeroUINativeProvider config={heroUITestConfig}>{children}</HeroUINativeProvider>
        </AppThemeProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: TestProviders, ...options }).then((result) => ({
    ...result,
    queryClient,
  }));
}
