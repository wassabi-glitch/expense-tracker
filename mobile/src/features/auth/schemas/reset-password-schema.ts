import { z } from 'zod';

export const resetPasswordSchema = z.object({
  password: z.string().min(8, 'auth.resetPassword.errors.passwordTooShort'),
});

export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;
