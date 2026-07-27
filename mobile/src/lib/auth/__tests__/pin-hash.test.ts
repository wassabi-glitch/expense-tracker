import { hashPin, verifyPin } from '../pin-hash';

// expo-crypto is available via the jest-expo preset but digestStringAsync
// may return unexpected results in test environment. We test the logic.
jest.mock('expo-crypto', () => {
  const actual = jest.requireActual('expo-crypto');
  return {
    ...actual,
    digestStringAsync: jest.fn().mockImplementation(
      (_algo: unknown, input: string) => {
        // Simple mock: prepend a prefix and produce a stable hex-like string
        const fakeHash = `sha256-${input}-${'00'.repeat(28)}`;
        return Promise.resolve(fakeHash);
      },
    ),
  };
});

describe('pin-hash', () => {
  describe('hashPin', () => {
    it('produces a consistent hash', async () => {
      const result = await hashPin('12345');
      const result2 = await hashPin('12345');
      expect(result).toBe(result2);
    });

    it('produces different hashes for different PINs', async () => {
      const a = await hashPin('12345');
      const b = await hashPin('54321');
      expect(a).not.toBe(b);
    });
  });

  describe('verifyPin', () => {
    it('returns true for a matching PIN', async () => {
      const stored = await hashPin('67890');
      const result = await verifyPin('67890', stored);
      expect(result).toBe(true);
    });

    it('returns false for a non-matching PIN', async () => {
      const stored = await hashPin('67890');
      const result = await verifyPin('11111', stored);
      expect(result).toBe(false);
    });

    it('returns false for a PIN with different length', async () => {
      const stored = await hashPin('67890');
      const result = await verifyPin('123456', stored);
      expect(result).toBe(false);
    });
  });
});
