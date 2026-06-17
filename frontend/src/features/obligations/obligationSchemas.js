import { z } from "zod";

export const MAX_DEBT_AMOUNT = 999_999_999_999;
const MAX_DEBT_AMOUNT_STR = String(MAX_DEBT_AMOUNT);

const amountSchema = z.preprocess(
  (value) => String(value ?? "").trim().replace(/\s+/g, ""),
  z
    .string()
    .refine((v) => v.length > 0, "debts.validation.amount.required")
    .refine((v) => /^\d+$/.test(v), "debts.validation.amount.invalid")
    .refine(
      (v) =>
        v.length < MAX_DEBT_AMOUNT_STR.length ||
        (v.length === MAX_DEBT_AMOUNT_STR.length && v <= MAX_DEBT_AMOUNT_STR),
      "debts.validation.amount.max"
    )
    .transform((v) => Number(v))
    .refine((v) => Number.isSafeInteger(v) && v > 0, "debts.validation.amount.invalid")
);

const optionalNonNegativeAmountSchema = z.preprocess(
  (value) => String(value ?? "").trim().replace(/\s+/g, ""),
  z
    .string()
    .optional()
    .nullable()
    .transform((v) => (v ? Number(v) : null))
    .refine((v) => v === null || (Number.isSafeInteger(v) && v >= 0), "debts.validation.amount.invalid")
);

const walletAllocationSchema = z.object({
  wallet_id: z.number().int().positive(),
  amount: amountSchema,
});

export const debtCreateFormSchema = z.object({
  counterparty_name: z
    .string()
    .transform((v) => v.trim())
    .refine((v) => v.length >= 1, "debts.validation.counterparty_name.required")
    .refine((v) => v.length <= 100, "debts.validation.counterparty_name.length"),
  initial_amount: amountSchema,
  debt_type: z.enum(["OWING", "OWED"], {
    errorMap: () => ({ message: "debts.validation.debt_type.invalid" }),
  }),
  origin_kind: z.enum([
    "CASH_BORROWED",
    "CASH_LENT",
    "DEFERRED_EXPENSE",
    "SPLIT_REIMBURSEMENT",
    "PERSONAL_REIMBURSEMENT",
    "RECEIVABLE_INCOME",
    "FINANCED_ASSET_PURCHASE",
    "DAMAGE_COMPENSATION",
    "IMPORTED_BALANCE",
  ]).optional(),
  counterparty_kind: z.enum(["PERSON", "BANK", "COMPANY", "STORE", "GOVERNMENT", "OTHER"]).optional(),
  product_kind: z.enum([
    "INFORMAL_DEBT",
    "BANK_LOAN",
    "CAR_LOAN",
    "MORTGAGE",
    "STORE_INSTALLMENT",
    "SERVICE_PAY_LATER",
    "PERSONAL_REIMBURSEMENT",
    "CLIENT_RECEIVABLE",
    "OTHER",
  ]).optional().nullable(),
  date: z.string().refine((v) => v.length > 0, "debts.validation.date.required"),
  expected_return_date: z.string().optional().nullable(),
  wallet_id: z.number().int().optional().nullable(),
  initial_wallet_id: z.number().int().optional().nullable(),
  initial_wallet_allocations: z.array(walletAllocationSchema).optional(),
  description: z.string().optional().nullable(),
  is_money_transferred: z.boolean().optional(),
  expense_category: z.string().optional().nullable(),
  expense_subcategory_id: z.number().int().optional().nullable(),
  project_id: z.number().int().optional().nullable(),
  project_subcategory_id: z.number().int().optional().nullable(),
  income_source_id: z.number().int().optional().nullable(),
}).superRefine((data, ctx) => {
  if (
    data.debt_type === "OWING" &&
    !data.is_money_transferred &&
    !(Array.isArray(data.initial_wallet_allocations) && data.initial_wallet_allocations.length > 0) &&
    !data.expense_category
  ) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["expense_category"],
      message: "debts.validation.expense_category.required",
    });
  }
});

export const debtUpdateFormSchema = z.object({
  counterparty_name: z
    .string()
    .transform((v) => v.trim())
    .refine((v) => v.length >= 1, "debts.validation.counterparty_name.required")
    .refine((v) => v.length <= 100, "debts.validation.counterparty_name.length")
    .optional(),
  description: z.string().optional().nullable(),
  date: z.string().optional().nullable(),
  expected_return_date: z.string().optional().nullable(),
  initial_amount: z.number().int().positive().max(MAX_DEBT_AMOUNT).optional(),
  status: z.enum([
    "ACTIVE",
    "OVERDUE",
    "DEFAULTED",
    "IN_COLLECTION",
    "PAID",
    "SETTLED",
    "FORGIVEN",
    "WRITTEN_OFF",
    "ARCHIVED",
  ]).optional(),
  origin_kind: z.enum([
    "CASH_BORROWED",
    "CASH_LENT",
    "DEFERRED_EXPENSE",
    "SPLIT_REIMBURSEMENT",
    "PERSONAL_REIMBURSEMENT",
    "RECEIVABLE_INCOME",
    "FINANCED_ASSET_PURCHASE",
    "DAMAGE_COMPENSATION",
    "IMPORTED_BALANCE",
  ]).optional(),
  counterparty_kind: z.enum(["PERSON", "BANK", "COMPANY", "STORE", "GOVERNMENT", "OTHER"]).optional(),
  product_kind: z.enum([
    "INFORMAL_DEBT",
    "BANK_LOAN",
    "CAR_LOAN",
    "MORTGAGE",
    "STORE_INSTALLMENT",
    "SERVICE_PAY_LATER",
    "PERSONAL_REIMBURSEMENT",
    "CLIENT_RECEIVABLE",
    "OTHER",
  ]).optional().nullable(),
  expense_category: z.string().optional().nullable(),
  expense_subcategory_id: z.number().int().optional().nullable(),
  project_id: z.number().int().optional().nullable(),
  project_subcategory_id: z.number().int().optional().nullable(),
  income_source_id: z.number().int().optional().nullable(),
});

export const debtPaymentFormSchema = z.object({
  amount: amountSchema,
  date: z.string().optional().nullable(),
  wallet_id: z.number().int().optional().nullable(),
  wallet_allocations: z.array(walletAllocationSchema).optional(),
  income_source_id: z.number().int().optional().nullable(),
  note: z.string().optional().nullable(),
});

export const debtForgivenessFormSchema = z.object({
  amount: amountSchema.optional().nullable(),
  date: z.string().optional().nullable(),
  note: z.string().optional().nullable(),
});

export const debtSettlementFormSchema = z.object({
  payment_amount: optionalNonNegativeAmountSchema,
  settlement_discount: optionalNonNegativeAmountSchema,
  date: z.string().optional().nullable(),
  note: z.string().optional().nullable(),
  wallet_allocations: z.array(walletAllocationSchema).optional(),
});

export const debtBalanceAdjustmentFormSchema = z.object({
  confirmed_balance: optionalNonNegativeAmountSchema.refine((v) => v !== null, "debts.validation.amount.required"),
  date: z.string().optional().nullable(),
  note: z.string().optional().nullable(),
});

export const debtFormalDetailsFormSchema = z.object({
  institution_name: z.string().max(100).optional().nullable(),
  contract_number: z.string().max(100).optional().nullable(),
  linked_asset_id: z.number().int().optional().nullable(),
  collateral_asset_id: z.number().int().optional().nullable(),
  statement_balance: optionalNonNegativeAmountSchema,
  statement_balance_date: z.string().optional().nullable(),
  next_due_date: z.string().optional().nullable(),
  annual_rate_bps: z.number().int().nonnegative().optional().nullable(),
  terms_summary: z.string().max(500).optional().nullable(),
});

export const installmentPaymentFormSchema = z.object({
  amount: amountSchema,
  paid_date: z.string().optional().nullable(),
  wallet_allocations: z.array(walletAllocationSchema),
  note: z.string().optional().nullable(),
});
