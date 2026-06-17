import { z } from "zod";

export const MAX_INCOME_AMOUNT = 999_999_999_999;
const MAX_INCOME_AMOUNT_STR = String(MAX_INCOME_AMOUNT);
export const MAX_INCOME_AMOUNT_DIGITS = MAX_INCOME_AMOUNT_STR.length;

export const LIFE_STATUS_OPTIONS = [
  "student",
  "employed",
  "self_employed",
  "business_owner",
  "unemployed",
];

export const onboardingStepOneSchema = z.object({
  life_statuses: z.array(z.enum(LIFE_STATUS_OPTIONS)).min(1, "onboarding.validation.lifeStatus.required"),
});

export const walletSchema = z.object({
  name: z.string().min(1, "onboarding.validation.walletName.required").max(50),
  initial_balance: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "onboarding.validation.initialBalance.required")
      .refine((v) => /^\d+$/.test(v), "onboarding.validation.initialBalance.invalid")
      .transform((v) => Number(v))
  ),
  color: z.string().default("default"),
});

export const onboardingStepTwoSchema = z.object({
  wallets: z.array(walletSchema).min(1, "onboarding.validation.wallets.required").max(20),
});

export const onboardingSchema = z.object({
  ...onboardingStepOneSchema.shape,
  ...onboardingStepTwoSchema.shape,
});
