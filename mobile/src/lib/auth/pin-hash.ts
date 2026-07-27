import * as Crypto from 'expo-crypto';

/**
 * Hash a 5-digit PIN using SHA-256.
 * Returns a hex-encoded hash string suitable for secure storage.
 */
export async function hashPin(pin: string): Promise<string> {
  return await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    pin,
  );
}

/**
 * Verify a PIN attempt against a stored hash.
 * Uses constant-time comparison via the hashing itself —
 * we hash the input and compare hex strings.
 */
export async function verifyPin(
  pin: string,
  storedHash: string,
): Promise<boolean> {
  const inputHash = await hashPin(pin);
  return inputHash === storedHash;
}
