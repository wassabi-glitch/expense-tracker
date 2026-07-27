import { z } from 'zod';

export const forgotPasswordSchema = z.object({
  email: z.string().min(1, 'auth.forgotPassword.errors.email').email('auth.forgotPassword.errors.email'),
});

export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;
