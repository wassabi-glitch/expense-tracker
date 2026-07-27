import { z } from 'zod';

const usernameRegex = /^[A-Za-z0-9._]+$/;

const basePasswordSchema = z
  .string()
  .min(8, 'auth.validation.password.min')
  .max(64, 'auth.validation.password.max')
  .refine((v) => !v.includes(' '), 'auth.validation.password.noSpaces')
  .refine((v) => /[a-z]/.test(v), 'auth.validation.password.lowercase')
  .refine((v) => /[A-Z]/.test(v), 'auth.validation.password.uppercase')
  .refine((v) => /\d/.test(v), 'auth.validation.password.number')
  .refine((v) => /[^\w\s]/.test(v), 'auth.validation.password.special');

function getEmailLocalPart(email: string) {
  const normalized = String(email || '').trim().toLowerCase();
  const atIndex = normalized.indexOf('@');
  return atIndex > 0 ? normalized.slice(0, atIndex) : '';
}

export const signUpSchema = z
  .object({
    username: z
      .string()
      .trim()
      .min(3, 'auth.validation.username.length')
      .max(32, 'auth.validation.username.length')
      .refine((v) => !v.includes(' '), 'auth.validation.username.noSpaces')
      .refine((v) => usernameRegex.test(v), 'auth.validation.username.allowedChars')
      .refine(
        (v) => !['.', '_'].includes(v[0] ?? '') && !['.', '_'].includes(v[v.length - 1] ?? ''),
        'auth.validation.username.edgeSeparators'
      )
      .refine(
        (v) => !v.includes('..') && !v.includes('__') && !v.includes('._') && !v.includes('_.'),
        'auth.validation.username.consecutiveSeparators'
      )
      .refine((v) => !/^\d+$/.test(v), 'auth.validation.username.notOnlyNumbers'),
    email: z.string().trim().toLowerCase().email('auth.validation.email.invalid'),
    password: basePasswordSchema,
  })
  .refine(
    (data) => {
      const localPart = getEmailLocalPart(data.email);
      return !localPart || !data.password.toLowerCase().includes(localPart);
    },
    {
      message: 'auth.validation.password.noEmailLocalPart',
      path: ['password'],
    }
  );

export type SignUpValues = z.infer<typeof signUpSchema>;
