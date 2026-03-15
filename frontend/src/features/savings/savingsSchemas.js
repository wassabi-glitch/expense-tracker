import { z } from "zod";

export const MAX_SAVINGS_AMOUNT = 999_999_999_999;
const MAX_SAVINGS_AMOUNT_STR = String(MAX_SAVINGS_AMOUNT);

export const savingsTransferFormSchema = z.object({
  amount: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "savings.validation.amount.required")
      .refine((v) => /^\d+$/.test(v), "savings.validation.amount.invalid")
      .refine(
        (v) =>
          v.length < MAX_SAVINGS_AMOUNT_STR.length ||
          (v.length === MAX_SAVINGS_AMOUNT_STR.length && v <= MAX_SAVINGS_AMOUNT_STR),
        "savings.validation.amount.max"
      )
      .transform((v) => Number(v))
      .refine((v) => Number.isSafeInteger(v) && v > 0, "savings.validation.amount.invalid")
  ),
});

export const goalCreateFormSchema = z.object({
  title: z
    .string()
    .transform((v) => v.trim())
    .refine((v) => v.length >= 3, "expenses.validation.title.length")
    .refine((v) => v.length <= 32, "expenses.validation.title.length"),
  target_amount: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "savings.validation.amount.required")
      .refine((v) => /^\d+$/.test(v), "savings.validation.amount.invalid")
      .refine(
        (v) =>
          v.length < MAX_SAVINGS_AMOUNT_STR.length ||
          (v.length === MAX_SAVINGS_AMOUNT_STR.length && v <= MAX_SAVINGS_AMOUNT_STR),
        "savings.validation.amount.max"
      )
      .transform((v) => Number(v))
      .refine((v) => Number.isSafeInteger(v) && v > 0, "savings.validation.amount.invalid")
  ),
  target_date: z.string().optional().nullable(),
});

export const goalUpdateFormSchema = z.object({
  title: z
    .string()
    .transform((v) => v.trim())
    .refine((v) => v.length >= 3, "expenses.validation.title.length")
    .refine((v) => v.length <= 32, "expenses.validation.title.length"),
  target_amount: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "savings.validation.amount.required")
      .refine((v) => /^\d+$/.test(v), "savings.validation.amount.invalid")
      .refine(
        (v) =>
          v.length < MAX_SAVINGS_AMOUNT_STR.length ||
          (v.length === MAX_SAVINGS_AMOUNT_STR.length && v <= MAX_SAVINGS_AMOUNT_STR),
        "savings.validation.amount.max"
      )
      .transform((v) => Number(v))
      .refine((v) => Number.isSafeInteger(v) && v > 0, "savings.validation.amount.invalid")
  ),
  target_date: z.string().optional().nullable(),
});

export const goalActionAmountSchema = z.object({
  amount: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "savings.validation.amount.required")
      .refine((v) => /^\d+$/.test(v), "savings.validation.amount.invalid")
      .refine(
        (v) =>
          v.length < MAX_SAVINGS_AMOUNT_STR.length ||
          (v.length === MAX_SAVINGS_AMOUNT_STR.length && v <= MAX_SAVINGS_AMOUNT_STR),
        "savings.validation.amount.max"
      )
      .transform((v) => Number(v))
      .refine((v) => Number.isSafeInteger(v) && v > 0, "savings.validation.amount.invalid")
  ),
});
