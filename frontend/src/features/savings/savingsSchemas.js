import { z } from "zod";
import { toISODateInTimeZone } from "@/lib/date";

export const MAX_SAVINGS_AMOUNT = 999_999_999_999;
const MAX_SAVINGS_AMOUNT_STR = String(MAX_SAVINGS_AMOUNT);
const MAX_PLANNED_PURCHASE_PAYMENT_WALLETS = 3;

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
  intent: z.enum(["RESERVE", "PLANNED_PURCHASE", "PAY_OBLIGATION", "FUND_PROJECT"]).optional(),
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
  wallet_id: z.coerce.number().int().positive("savings.goals.walletRequired"),
});

export const goalAllocationsFormSchema = z.object({
  allocations: z.array(goalActionAmountSchema).min(1, "savings.goals.walletRequired"),
}).superRefine((data, ctx) => {
  const walletIds = data.allocations.map((item) => item.wallet_id);
  if (new Set(walletIds).size !== walletIds.length) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["allocations"],
      message: "goals.allocation_duplicate_wallet",
    });
  }
});

const goalPaymentAllocationSchema = z.object({
  wallet_id: z.coerce.number().int().positive("savings.goals.walletRequired"),
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

const optionalPositiveIdSchema = z.preprocess(
  (value) => {
    if (value === "" || value === "__none__" || value === null || value === undefined) return null;
    return Number(value);
  },
  z.number().int().positive().nullable().optional()
);

export const goalUseFormSchema = z.object({
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
  payment_allocations: z.array(goalPaymentAllocationSchema).min(1, "savings.goals.walletRequired"),
  category: z.string().min(1, "expenses.categoryRequired"),
  subcategory_id: optionalPositiveIdSchema,
  date: z
    .string()
    .optional()
    .nullable()
    .refine((v) => !v || v <= toISODateInTimeZone(), "expenses.dateFuture"),
  settlement_mode: z.enum(["DIRECT", "GOAL_BACKED_OFF_WALLET_PAYMENT"]),
  result_type: z.enum(["EXPENSE_ONLY", "ASSET_PURCHASE"]).optional(),
  asset_title: z.string().trim().optional(),
  adjust_target_to_purchase_amount: z.boolean().optional(),
}).superRefine((data, ctx) => {
  if (data.payment_allocations.length > MAX_PLANNED_PURCHASE_PAYMENT_WALLETS) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["payment_allocations"],
      message: "goals.payment_allocation_limit_exceeded",
    });
  }
  const total = data.payment_allocations.reduce((sum, item) => sum + item.amount, 0);
  if (total !== data.amount) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["payment_allocations"],
      message: "goals.payment_allocation_total_mismatch",
    });
  }
  const walletIds = data.payment_allocations.map((item) => item.wallet_id);
  if (new Set(walletIds).size !== walletIds.length) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["payment_allocations"],
      message: "goals.payment_allocation_duplicate",
    });
  }
});

export const goalDebtPaymentFormSchema = z.object({
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
  payment_allocations: z.array(goalPaymentAllocationSchema).min(1, "savings.goals.walletRequired"),
  date: z
    .string()
    .optional()
    .nullable()
    .refine((v) => !v || v <= toISODateInTimeZone(), "expenses.dateFuture"),
  note: z.string().trim().max(200).optional(),
}).superRefine((data, ctx) => {
  const total = data.payment_allocations.reduce((sum, item) => sum + item.amount, 0);
  if (total !== data.amount) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["payment_allocations"],
      message: "goals.payment_allocation_total_mismatch",
    });
  }
  const walletIds = data.payment_allocations.map((item) => item.wallet_id);
  if (new Set(walletIds).size !== walletIds.length) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["payment_allocations"],
      message: "goals.payment_allocation_duplicate",
    });
  }
});
