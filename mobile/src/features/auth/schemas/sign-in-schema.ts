import { z } from 'zod';

export const signInSchema = z.object({
  email: z.string().trim().toLowerCase().email('auth.validation.email.invalid'),
  password: z.string().min(1, 'auth.validation.password.required'),
});

export type SignInValues = z.infer<typeof signInSchema>;
