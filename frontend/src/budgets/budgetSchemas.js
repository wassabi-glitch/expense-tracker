import { z } from "zod";

export const MIN_BUDGET_MONTH_ZOD = "2020-01";
export const MAX_BUDGET_AMOUNT = 999_999_999_999;
const MAX_BUDGET_AMOUNT_STR = String(MAX_BUDGET_AMOUNT);

function getMaxBudgetMonthZod() {
  const today = new Date();
  const year = today.getFullYear() + 5;
  const month = String(today.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

const budgetLimitSchema = z.preprocess(
  (value) => String(value ?? "").trim().replace(/\s+/g, ""),
  z
    .string()
    .refine((v) => v.length > 0, "budgets.validation.limit.required")
    .refine((v) => /^\d+$/.test(v), "budgets.validation.limit.invalid")
    .refine(
      (v) =>
        v.length < MAX_BUDGET_AMOUNT_STR.length ||
        (v.length === MAX_BUDGET_AMOUNT_STR.length && v <= MAX_BUDGET_AMOUNT_STR),
      "budgets.validation.limit.invalid"
    )
    .transform((v) => Number(v))
    .refine((v) => Number.isSafeInteger(v) && v > 0, "budgets.validation.limit.invalid")
);

const budgetCategorySchema = z
  .string()
  .transform((v) => v.trim())
  .refine((v) => v.length > 0, "budgets.validation.category.required");

const budgetMonthValueSchema = z
  .string()
  .trim()
  .refine((v) => v.length > 0, "budgets.validation.month.required")
  .refine((v) => /^\d{4}-\d{2}$/.test(v), "budgets.validation.month.invalid")
  .refine((v) => v >= MIN_BUDGET_MONTH_ZOD, "budgets.validation.month.tooEarly")
  .refine((v) => v <= getMaxBudgetMonthZod(), "budgets.validation.month.tooFar");

const budgetTargetSchema = z.object({
  category: z.string().min(1, "budgets.validation.target.required"),
  budgetYear: z.number().int().min(2020, "budgets.validation.target.required"),
  budgetMonth: z.number().int().min(1, "budgets.validation.target.required").max(12, "budgets.validation.target.required"),
});

export const budgetCreateFormSchema = z.object({
  category: budgetCategorySchema,
  monthly_limit: budgetLimitSchema,
  budget_month_value: budgetMonthValueSchema,
});

export const budgetUpdateFormSchema = z.object({
  monthly_limit: budgetLimitSchema,
}).and(budgetTargetSchema);

export const budgetDeleteFormSchema = budgetTargetSchema;

