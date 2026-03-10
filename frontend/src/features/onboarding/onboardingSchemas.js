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
  life_status: z.enum(LIFE_STATUS_OPTIONS, {
    message: "onboarding.validation.lifeStatus.required",
  }),
});

export const onboardingStepTwoSchema = z.object({
  monthly_income_amount: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "onboarding.validation.income.required")
      .refine((v) => /^\d+$/.test(v), "onboarding.validation.income.invalid")
      .refine(
        (v) =>
          v.length < MAX_INCOME_AMOUNT_STR.length ||
          (v.length === MAX_INCOME_AMOUNT_STR.length && v <= MAX_INCOME_AMOUNT_STR),
        "onboarding.validation.income.max"
      )
      .transform((v) => Number(v))
      .refine((v) => Number.isSafeInteger(v) && v >= 0, "onboarding.validation.income.invalid")
  ),
});

export const onboardingSchema = onboardingStepOneSchema.extend(
  onboardingStepTwoSchema.shape
);
