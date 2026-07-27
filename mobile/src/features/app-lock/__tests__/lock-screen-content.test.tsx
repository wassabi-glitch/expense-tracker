import { render, screen } from '@testing-library/react-native';
import { LockScreenContent } from '../components/lock-screen-content';
import { useAppLockStore } from '../hooks/use-app-lock';

// Mock useTheme
jest.mock('@/hooks/use-theme', () => ({
  useTheme: () => ({
    colors: {
      screen: '#000000',
      textPrimary: '#FFFFFF',
      textSecondary: '#999999',
      surface: '#1A1A1A',
      borderSubtle: '#333333',
      borderControl: '#444444',
      brand: { action: '#22C55E', onAction: '#052E16' },
      status: { destructive: { main: '#EF4444' } },
    },
    mode: 'dark',
  }),
}));

// Mock the store
jest.mock('../hooks/use-app-lock', () => ({
  useAppLockStore: jest.fn(),
}));

const mockStore = {
  verifyAndUnlock: jest.fn().mockResolvedValue({ success: true, attemptsLeft: 5 }),
  authenticateWithBiometrics: jest.fn().mockResolvedValue(true),
  bioEnabled: true,
  bioAvailable: true,
  failedAttempts: 0,
  cooldownRemaining: 0,
  cooldownUntil: null,
  clearAllPinData: jest.fn(),
} as any;

describe('LockScreenContent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAppLockStore as unknown as jest.Mock).mockReturnValue(mockStore);
    mockStore.failedAttempts = 0;
    mockStore.cooldownUntil = null;
    mockStore.cooldownRemaining = 0;
    mockStore.verifyAndUnlock.mockResolvedValue({ success: true, attemptsLeft: 5 });
  });

  it('renders PIN entry title', async () => {
    await render(<LockScreenContent />);
    expect(screen.getByText('Enter your PIN')).toBeTruthy();
  });

  it('renders biometric button when enabled', async () => {
    await render(<LockScreenContent />);
    expect(screen.getByLabelText('Use fingerprint')).toBeTruthy();
  });

  it('hides biometric button when device lacks biometric hardware', async () => {
    (useAppLockStore as unknown as jest.Mock).mockReturnValue({
      ...mockStore,
      bioAvailable: false,
    });
    await render(<LockScreenContent />);
    expect(screen.queryByLabelText('Use fingerprint')).toBeNull();
  });

  it('shows cooldown UI when cooldown is active', async () => {
    (useAppLockStore as unknown as jest.Mock).mockReturnValue({
      ...mockStore,
      cooldownUntil: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      cooldownRemaining: 900,
    });
    await render(<LockScreenContent />);
    expect(screen.getByText('Too many attempts')).toBeTruthy();
  });

  it('does not show logout button on lock screen', async () => {
    await render(<LockScreenContent />);
    // Logout has been removed from lock screen as a security measure.
    // The lock screen should gate access — no account actions should be available.
    expect(screen.queryByLabelText('Sign out')).toBeNull();
  });
});
