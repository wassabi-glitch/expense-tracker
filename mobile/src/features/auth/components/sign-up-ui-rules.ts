export type PasswordRequirementKey =
  | 'length'
  | 'lowercase'
  | 'uppercase'
  | 'number'
  | 'special'
  | 'noSpaces'
  | 'excludesEmail';

export type PasswordRequirementState = Record<PasswordRequirementKey, boolean>;

const usernameCharacters = /^[A-Za-z0-9._]+$/;

export function isEligibleEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

export function isEligibleUsername(value: string) {
  const normalized = value.trim();

  return (
    normalized.length >= 3 &&
    normalized.length <= 32 &&
    usernameCharacters.test(normalized) &&
    !normalized.includes('..') &&
    !normalized.includes('__') &&
    !normalized.includes('._') &&
    !normalized.includes('_.') &&
    !['.', '_'].includes(normalized[0] ?? '') &&
    !['.', '_'].includes(normalized.at(-1) ?? '') &&
    !/^\d+$/.test(normalized)
  );
}

export function evaluatePasswordRequirements(
  password: string,
  email: string,
): PasswordRequirementState {
  const emailName = email.trim().toLowerCase().split('@')[0] ?? '';
  const normalizedPassword = password.toLowerCase();

  return {
    length: password.length >= 8 && password.length <= 64,
    lowercase: /[a-z]/.test(password),
    uppercase: /[A-Z]/.test(password),
    number: /\d/.test(password),
    special: /[^\w\s]/.test(password),
    noSpaces: password.length > 0 && !password.includes(' '),
    excludesEmail: emailName.length === 0 || !normalizedPassword.includes(emailName),
  };
}

export function arePasswordRequirementsMet(state: PasswordRequirementState) {
  return Object.values(state).every(Boolean);
}
