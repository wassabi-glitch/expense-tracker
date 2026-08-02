import type { useToast } from 'heroui-native';

type ToastManager = ReturnType<typeof useToast>['toast'];

/**
 * Show a danger toast. Clears existing toasts first so only one is visible.
 * Defaults to 60 000 ms (1 minute) — long enough to read, short enough
 * that the user can just ignore it if they prefer.
 */
export function showErrorToast(
  toast: ToastManager,
  message: string,
  placement: 'top' | 'bottom',
  duration: number | 'persistent' = 60_000,
) {
  try {
    toast.hide('all');
    toast.show({
      variant: 'danger',
      label: message,
      placement,
      duration,
    });
  } catch {
    // SafeAreaProvider not mounted (e.g., test environment) — swallow silently.
  }
}
