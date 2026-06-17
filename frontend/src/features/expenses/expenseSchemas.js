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

const splitItemSchema = z.object({
  contact_name: z.string().trim().min(1, "expenses.splitNameRequired"),
  amount: coercePositiveInteger,
});

export const expenseFormSchema = z.object({
  title: titleSchema,
  amount: coercePositiveInteger,
  category: categorySchema,
  date: dateSchema,
  wallet_id: z.number().int().optional().nullable(),
  description: z.preprocess(
    (value) => (value == null ? "" : value),
    descriptionSchema
  ),
  splits: z.array(splitItemSchema).optional(),
}).refine(data => {
  if (data.splits && data.splits.length > 0) {
    const totalSplitAmt = data.splits.reduce((sum, s) => sum + (s.amount || 0), 0);
    return totalSplitAmt <= data.amount;
  }
  return true;
}, {
  message: "expenses.splitExceedsTotal",
  path: ["splits_total"]
});

export const expenseUpdateFormSchema = z.object({
  title: titleSchema,
  description: z.preprocess(
    (value) => (value == null ? "" : value),
    descriptionSchema
  ),
});

export const recurringExpenseFormSchema = z.object({
  title: titleSchema,
  amount: coercePositiveInteger,
  category: categorySchema,
  frequency: z.enum(["DAILY", "WEEKLY", "MONTHLY", "YEARLY", "ONE_TIME", "BIWEEKLY", "QUARTERLY", "SEMI_ANNUALLY"], {
    errorMap: () => ({ message: "expenses.frequencyRequired" })
  }),
  start_date: z
    .string()
    .trim()
    .refine((v) => v.length > 0, "expenses.dateRequired")
    .refine((v) => /^\d{4}-\d{2}-\d{2}$/.test(v), "expenses.dateRequired")
    .refine((v) => v >= MIN_EXPENSE_DATE_ZOD, "expenses.dateTooEarly")
    .refine((v) => {
      const parts = toISODateInTimeZone().split("-");
      const minStart = `${parts[0]}-${parts[1]}-01`;
      return v >= minStart;
    }, "recurring.startDateBeforeCurrentMonth"),
  wallet_id: z.number().int({ message: "wallets.required" }),
  description: z.preprocess(
    (value) => (value == null ? "" : value),
    descriptionSchema
  ),
});

export const recurringExpenseUpdateFormSchema = z.object({
  title: titleSchema,
  amount: coercePositiveInteger,
  category: categorySchema,
  wallet_id: z.number().int().optional().nullable(),
  description: z.preprocess(
    (value) => (value == null ? "" : value),
    descriptionSchema
  ),
});

export const refundSchema = z.object({
  amount: coercePositiveInteger,
  wallet_id: z.string().min(1, "expenses.walletRequired"),
});

