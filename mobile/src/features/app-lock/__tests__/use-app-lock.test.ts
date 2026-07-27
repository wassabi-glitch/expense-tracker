import { useAppLockStore } from '../hooks/use-app-lock';
import {
  savePinHash,
  deletePinHash,
  getPinHash,
  saveCooldownUntil,
  getCooldownUntil,
  deleteCooldownUntil,
  saveBioEnabled,
  getBioEnabled,
  deleteBioEnabled,
  deleteAllPinData,
  saveAppLockEnabled,
  getAppLockEnabled,
} from '@/lib/auth/pin-store';
import { hashPin } from '@/lib/auth/pin-hash';
import * as LocalAuthentication from 'expo-local-authentication';

// Mock pin-store
jest.mock('@/lib/auth/pin-store', () => ({
  savePinHash: jest.fn(),
  getPinHash: jest.fn().mockResolvedValue(null),
  deletePinHash: jest.fn(),
  saveCooldownUntil: jest.fn(),
  getCooldownUntil: jest.fn().mockResolvedValue(null),
  deleteCooldownUntil: jest.fn(),
  saveBioEnabled: jest.fn(),
  getBioEnabled: jest.fn().mockResolvedValue(false),
  deleteBioEnabled: jest.fn(),
  deleteAllPinData: jest.fn(),
  saveAppLockEnabled: jest.fn(),
  getAppLockEnabled: jest.fn().mockResolvedValue(true),
}));

// Mock pin-hash
jest.mock('@/lib/auth/pin-hash', () => ({
  hashPin: jest.fn().mockResolvedValue('mocked-hash'),
  verifyPin: jest.fn().mockImplementation((pin, stored) =>
    Promise.resolve(pin === '12345'),
  ),
}));

// Mock expo-local-authentication
jest.mock('expo-local-authentication', () => ({
  hasHardwareAsync: jest.fn().mockResolvedValue(true),
  isEnrolledAsync: jest.fn().mockResolvedValue(true),
  authenticateAsync: jest.fn().mockResolvedValue({ success: true }),
  supportedAuthenticationTypesAsync: jest.fn().mockResolvedValue([1, 2]),
}));

describe('useAppLockStore', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getPinHash as jest.Mock).mockResolvedValue(null);
    (getCooldownUntil as jest.Mock).mockResolvedValue(null);
    (getBioEnabled as jest.Mock).mockResolvedValue(false);
    // Reset store state
    useAppLockStore.setState({
      isInitialized: false,
      pinExists: false,
      isLocked: false,
      isSettingUp: false,
      bioEnabled: false,
      bioAvailable: false,
      failedAttempts: 0,
      cooldownUntil: null,
      cooldownRemaining: 0,
      cooldownIntervalId: null,
      passwordVerified: false,
      appLockEnabled: true,
      changePinMode: false,
    });
  });

  describe('initialize', () => {
    it('sets isSettingUp when no PIN exists', async () => {
      (getPinHash as jest.Mock).mockResolvedValue(null);

      await useAppLockStore.getState().initialize();

      expect(useAppLockStore.getState().isInitialized).toBe(true);
      expect(useAppLockStore.getState().pinExists).toBe(false);
      expect(useAppLockStore.getState().isSettingUp).toBe(true);
    });

    it('sets isLocked when PIN exists', async () => {
      (getPinHash as jest.Mock).mockResolvedValue('stored-hash');

      await useAppLockStore.getState().initialize();

      expect(useAppLockStore.getState().pinExists).toBe(true);
      expect(useAppLockStore.getState().isLocked).toBe(true);
      expect(useAppLockStore.getState().isSettingUp).toBe(false);
    });

    it('detects biometric availability', async () => {
      (LocalAuthentication.hasHardwareAsync as jest.Mock).mockResolvedValue(true);
      (LocalAuthentication.isEnrolledAsync as jest.Mock).mockResolvedValue(true);

      await useAppLockStore.getState().initialize();

      expect(useAppLockStore.getState().bioAvailable).toBe(true);
    });

    it('reads active cooldown from SecureStore', async () => {
      const futureTime = new Date(Date.now() + 15 * 60 * 1000).toISOString();
      (getCooldownUntil as jest.Mock).mockResolvedValue(futureTime);

      await useAppLockStore.getState().initialize();

      expect(useAppLockStore.getState().cooldownRemaining).toBeGreaterThan(0);
    });

    it('clears expired cooldown', async () => {
      const pastTime = new Date(Date.now() - 10 * 60 * 1000).toISOString();
      (getCooldownUntil as jest.Mock).mockResolvedValue(pastTime);

      await useAppLockStore.getState().initialize();

      expect(deleteCooldownUntil).toHaveBeenCalled();
      expect(useAppLockStore.getState().cooldownRemaining).toBe(0);
    });
  });

  describe('lock / unlock', () => {
    it('lock sets isLocked true and resets attempts', () => {
      useAppLockStore.setState({ failedAttempts: 3 });
      useAppLockStore.getState().lock();
      expect(useAppLockStore.getState().isLocked).toBe(true);
      expect(useAppLockStore.getState().failedAttempts).toBe(0);
    });

    it('unlock sets isLocked false and clears setup state', () => {
      useAppLockStore.setState({ isLocked: true, isSettingUp: true, failedAttempts: 2 });
      useAppLockStore.getState().unlock();
      expect(useAppLockStore.getState().isLocked).toBe(false);
      expect(useAppLockStore.getState().isSettingUp).toBe(false);
      expect(useAppLockStore.getState().failedAttempts).toBe(0);
    });
  });

  describe('verifyAndUnlock', () => {
    it('unlocks on correct PIN', async () => {
      (getPinHash as jest.Mock).mockResolvedValue('stored-hash');

      const result = await useAppLockStore.getState().verifyAndUnlock('12345');

      expect(result.success).toBe(true);
      expect(useAppLockStore.getState().isLocked).toBe(false);
    });

    it('increments failed attempts on wrong PIN', async () => {
      (getPinHash as jest.Mock).mockResolvedValue('stored-hash');
      useAppLockStore.setState({ isInitialized: true });

      const result = await useAppLockStore.getState().verifyAndUnlock('00000');

      expect(result.success).toBe(false);
      expect(result.attemptsLeft).toBe(4);
      expect(useAppLockStore.getState().failedAttempts).toBe(1);
    });

    it('triggers cooldown after 5 wrong attempts', async () => {
      (getPinHash as jest.Mock).mockResolvedValue('stored-hash');
      useAppLockStore.setState({ failedAttempts: 4, isInitialized: true });

      const result = await useAppLockStore.getState().verifyAndUnlock('00000');

      expect(result.success).toBe(false);
      expect(result.attemptsLeft).toBe(0);
      // PIN deleted and cooldown saved
      expect(deletePinHash).toHaveBeenCalled();
      expect(saveCooldownUntil).toHaveBeenCalled();
    });
  });

  describe('setPin', () => {
    it('hashes and stores PIN, unlocks the app', async () => {
      await useAppLockStore.getState().setPin('12345');

      expect(hashPin).toHaveBeenCalledWith('12345');
      expect(savePinHash).toHaveBeenCalledWith('mocked-hash');
      expect(useAppLockStore.getState().pinExists).toBe(true);
      expect(useAppLockStore.getState().isSettingUp).toBe(false);
      expect(useAppLockStore.getState().isLocked).toBe(false);
    });
  });

  describe('cooldown', () => {
    it('startCooldown deletes PIN and saves cooldown timestamp', async () => {
      await useAppLockStore.getState().startCooldown();

      expect(deletePinHash).toHaveBeenCalled();
      expect(saveCooldownUntil).toHaveBeenCalled();
      const cooldownArg = (saveCooldownUntil as jest.Mock).mock.calls[0][0];
      expect(new Date(cooldownArg).getTime()).toBeGreaterThan(Date.now() + 29 * 60 * 1000);
    });

    it('clearCooldown removes cooldown state', async () => {
      await useAppLockStore.getState().clearCooldown();

      expect(deleteCooldownUntil).toHaveBeenCalled();
      expect(useAppLockStore.getState().cooldownRemaining).toBe(0);
      expect(useAppLockStore.getState().cooldownUntil).toBeNull();
    });

    it('tickCooldown decrements remaining seconds', () => {
      useAppLockStore.setState({ cooldownRemaining: 60 });
      useAppLockStore.getState().tickCooldown();
      expect(useAppLockStore.getState().cooldownRemaining).toBe(59);
    });

    it('tickCooldown clears cooldown when expired', () => {
      useAppLockStore.setState({ cooldownRemaining: 1 });
      useAppLockStore.getState().tickCooldown();
      expect(deleteCooldownUntil).toHaveBeenCalled();
    });
  });

  describe('biometrics', () => {
    it('enableBio saves preference', async () => {
      await useAppLockStore.getState().enableBio();
      expect(saveBioEnabled).toHaveBeenCalledWith(true);
      expect(useAppLockStore.getState().bioEnabled).toBe(true);
    });

    it('disableBio removes preference', async () => {
      await useAppLockStore.getState().disableBio();
      expect(deleteBioEnabled).toHaveBeenCalled();
      expect(useAppLockStore.getState().bioEnabled).toBe(false);
    });

    it('authenticateWithBiometrics unlocks on success', async () => {
      (LocalAuthentication.authenticateAsync as jest.Mock).mockResolvedValue({ success: true });
      useAppLockStore.setState({ isLocked: true });

      const result = await useAppLockStore.getState().authenticateWithBiometrics();

      expect(result).toBe(true);
      expect(useAppLockStore.getState().isLocked).toBe(false);
      expect(LocalAuthentication.authenticateAsync).toHaveBeenCalledWith({
        promptMessage: 'Unlock Sarflog',
        disableDeviceFallback: true,
      });
    });

    it('authenticateWithBiometrics stays locked on failure', async () => {
      (LocalAuthentication.authenticateAsync as jest.Mock).mockResolvedValue({ success: false });
      useAppLockStore.setState({ isLocked: true });

      const result = await useAppLockStore.getState().authenticateWithBiometrics();

      expect(result).toBe(false);
      expect(useAppLockStore.getState().isLocked).toBe(true);
    });
  });

  describe('password verification', () => {
    it('markPasswordVerified sets flag', () => {
      useAppLockStore.getState().markPasswordVerified();
      expect(useAppLockStore.getState().passwordVerified).toBe(true);
    });

    it('unlock resets passwordVerified flag', () => {
      useAppLockStore.setState({ passwordVerified: true, isLocked: true });
      useAppLockStore.getState().unlock();
      expect(useAppLockStore.getState().passwordVerified).toBe(false);
    });
  });

  describe('toggleAppLock', () => {
    it('turns app lock on — keeps PIN, locks app', async () => {
      useAppLockStore.setState({ pinExists: true, appLockEnabled: false, isLocked: false });
      await useAppLockStore.getState().toggleAppLock(true);
      expect(saveAppLockEnabled).toHaveBeenCalledWith(true);
      expect(useAppLockStore.getState().appLockEnabled).toBe(true);
      expect(useAppLockStore.getState().isLocked).toBe(true);
    });

    it('turns app lock off — keeps PIN, unlocks app', async () => {
      useAppLockStore.setState({ pinExists: true, appLockEnabled: true, isLocked: true });
      await useAppLockStore.getState().toggleAppLock(false);
      expect(saveAppLockEnabled).toHaveBeenCalledWith(false);
      expect(useAppLockStore.getState().appLockEnabled).toBe(false);
      expect(useAppLockStore.getState().isLocked).toBe(false);
    });
  });

  describe('changePinMode', () => {
    it('startChangePin enters change PIN mode', () => {
      useAppLockStore.getState().startChangePin();
      expect(useAppLockStore.getState().changePinMode).toBe(true);
      expect(useAppLockStore.getState().isSettingUp).toBe(true);
    });

    it('finishChangePin exits change PIN mode', () => {
      useAppLockStore.setState({ changePinMode: true, isSettingUp: true });
      useAppLockStore.getState().finishChangePin();
      expect(useAppLockStore.getState().changePinMode).toBe(false);
      expect(useAppLockStore.getState().isSettingUp).toBe(false);
      expect(useAppLockStore.getState().isLocked).toBe(false);
    });
  });

  describe('cleanup', () => {
    it('clearAllPinData removes everything and resets state', async () => {
      useAppLockStore.setState({
        pinExists: true,
        isLocked: true,
        bioEnabled: true,
        isSettingUp: false,
      });

      await useAppLockStore.getState().clearAllPinData();

      expect(deleteAllPinData).toHaveBeenCalled();
      expect(useAppLockStore.getState().pinExists).toBe(false);
      expect(useAppLockStore.getState().isSettingUp).toBe(true);
      expect(useAppLockStore.getState().isLocked).toBe(false);
      expect(useAppLockStore.getState().bioEnabled).toBe(false);
    });
  });
});
