import { z } from "zod";
import { toISODateInTimeZone } from "@/lib/date";

export const MIN_EXPENSE_DATE_ZOD = "2020-01-01";
export const MAX_EXPENSE_AMOUNT = 999_999_999_999;
const MAX_EXPENSE_AMOUNT_STR = String(MAX_EXPENSE_AMOUNT);

const coercePositiveInteger = z.preprocess(
  (value) => String(value ?? "").trim().replace(/\s+/g, ""),
  z
    .string()
    .refine((v) => v.length > 0, "expenses.amountRequired")
    .refine((v) => /^\d+$/.test(v), "expenses.amountInvalid")
    .refine(
      (v) =>
        v.length < MAX_EXPENSE_AMOUNT_STR.length ||
        (v.length === MAX_EXPENSE_AMOUNT_STR.length && v <= MAX_EXPENSE_AMOUNT_STR),
      "expenses.amountTooLarge"
    )
    .transform((v) => Number(v))
    .refine((v) => Number.isSafeInteger(v) && v > 0, "expenses.amountInvalid")
);

const titleSchema = z
  .string()
  .transform((v) => v.trim())
  .refine((v) => v.length > 0, "expenses.titleRequired")
  .refine((v) => v.length >= 3 && v.length <= 32, "expenses.validation.title.length");

const categorySchema = z
  .string()
  .transform((v) => v.trim())
  .refine((v) => v.length > 0, "expenses.categoryRequired");

const dateSchema = z
  .string()
  .trim()
  .refine((v) => v.length > 0, "expenses.dateRequired")
  .refine((v) => /^\d{4}-\d{2}-\d{2}$/.test(v), "expenses.dateRequired")
  .refine((v) => v >= MIN_EXPENSE_DATE_ZOD, "expenses.dateTooEarly")
  .refine((v) => v <= toISODateInTimeZone(), "expenses.dateFuture");

const descriptionSchema = z
  .string()
  .transform((v) => v.trim())
  .refine((v) => v.length <= 500, "expenses.validation.description.max_length")
  .transform((v) => (v.length ? v : null))
  .nullable()
  .optional();

export const expenseFormSchema = z.object({
  title: titleSchema,
  amount: coercePositiveInteger,
  category: categorySchema,
  date: dateSchema,
  description: z.preprocess(
    (value) => (value == null ? "" : value),
    descriptionSchema
  ),
});

export const expenseUpdateFormSchema = z.object({
  title: titleSchema,
  amount: coercePositiveInteger,
  date: dateSchema,
  description: z.preprocess(
    (value) => (value == null ? "" : value),
    descriptionSchema
  ),
});
