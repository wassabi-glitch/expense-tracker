import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type PropsWithChildren } from 'react';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false, // We handle retries specifically per query if needed, or leave false for predictable dev behavior
      staleTime: 1000 * 60 * 5, // 5 minutes cache
    },
  },
});

export function AppQueryProvider({ children }: PropsWithChildren) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
