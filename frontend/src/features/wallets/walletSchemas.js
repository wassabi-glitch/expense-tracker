import { z } from "zod";

export const walletFormSchema = z.object({
  name: z.string()
    .min(1, "onboarding.validation.walletName.required")
    .max(32, "common.validation.tooLong"),
  wallet_type: z.enum(["CASH", "DEBIT", "CREDIT", "PRELOADED", "SAVINGS"]).default("DEBIT"),
  accounting_type: z.enum(["ASSET", "LIABILITY"]).default("ASSET"),
  initial_balance: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "onboarding.validation.initialBalance.required")
      .refine((v) => /^-?\d+$/.test(v), "onboarding.validation.initialBalance.invalid")
      .transform((v) => Number(v))
  ),
  current_balance: z.number().optional(),
  
  // Overdraft Rules (Debit)
  has_overdraft: z.boolean().default(false),
  overdraft_limit: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .transform((v) => v === "" ? 0 : Number(v))
      .refine((v) => !isNaN(v) && v >= 0, "wallets.validation.limitInvalid")
  ).default(0),

  // Credit Card Rules
  credit_limit: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .transform((v) => v === "" ? 0 : Number(v))
      .refine((v) => !isNaN(v) && v >= 0, "wallets.validation.limitInvalid")
  ).default(0),
  allow_overlimit: z.boolean().default(false),
  can_fund_goals: z.boolean().default(false),
  
  color: z.string().default("default"),
}).refine((data) => {
  if (data.wallet_type === "CREDIT") {
    return data.credit_limit > 0;
  }
  return true;
}, {
  message: "wallets.validation.limitRequired",
  path: ["credit_limit"]
}).refine((data) => {
  if (data.wallet_type === "DEBIT" && data.has_overdraft) {
    return data.overdraft_limit > 0;
  }
  return true;
}, {
  message: "wallets.validation.limitRequired",
  path: ["overdraft_limit"]
}).refine((data) => {
  const initial = data.initial_balance;
  const mag = Math.abs(initial);
  
  if (initial < 0) {
    // 1. Credit Cards: Check allow_overlimit/credit_limit
    if (data.wallet_type === "CREDIT") {
      if (!data.allow_overlimit && mag > (data.credit_limit || 0)) {
        return false;
      }
      return true;
    } 
    
    // 2. Debit: Check has_overdraft and mandatory overdraft_limit
    if (data.wallet_type === "DEBIT") {
      if (!data.has_overdraft || mag > (data.overdraft_limit || 0)) {
        return false;
      }
      return true;
    }

    // 3. Preloaded: Check has_overdraft (limit is optional/soft)
    if (data.wallet_type === "PRELOADED") {
      if (!data.has_overdraft) return false;
      // If a limit is provided, enforce it; otherwise allow
      if (data.overdraft_limit > 0 && mag > data.overdraft_limit) return false;
      return true;
    }

    // 4. Cash (and safety): Never negative
    return false;
  }
  return true;
}, {
  message: "wallets.validation.balanceExceedsLimit",
  path: ["initial_balance"]
});

export const walletUpdateSchema = z.object({
  name: z.string()
    .min(1, "onboarding.validation.walletName.required")
    .max(32, "common.validation.tooLong"),
  color: z.string().default("default"),
  is_active: z.boolean().optional(),
  
  has_overdraft: z.boolean().optional(),
  overdraft_limit: z.preprocess(
    (value) => value === undefined ? undefined : String(value ?? "").trim().replace(/\s+/g, ""),
    z.string().optional().transform((v) => v === undefined ? undefined : (v === "" ? 0 : Number(v)))
  ),
  credit_limit: z.preprocess(
    (value) => value === undefined ? undefined : String(value ?? "").trim().replace(/\s+/g, ""),
    z.string().optional().transform((v) => v === undefined ? undefined : (v === "" ? 0 : Number(v)))
  ),
  allow_overlimit: z.boolean().optional(),
  can_fund_goals: z.boolean().optional(),
});

export const walletTransferSchema = z.object({
  from_wallet_id: z.number().positive("wallets.validation.sourceRequired"),
  to_wallet_id: z.number().positive("wallets.validation.targetRequired"),
  amount: z.preprocess(
    (value) => String(value ?? "").trim().replace(/\s+/g, ""),
    z
      .string()
      .refine((v) => v.length > 0, "expenses.amountRequired")
      .refine((v) => /^\d+$/.test(v) && Number(v) > 0, "expenses.amountInvalid")
      .transform((v) => Number(v))
  ),
  note: z.string().max(200).optional().nullable(),
  goal_resolution: z.enum(["MOVE_TO_DESTINATION", "RELEASE"]).optional(),
  fee_amount: z.preprocess(
    (value) => {
      const normalized = String(value ?? "").trim().replace(/\s+/g, "");
      return normalized.length ? normalized : undefined;
    },
    z
      .string()
      .refine((v) => /^\d+$/.test(v) && Number(v) > 0, "expenses.amountInvalid")
      .transform((v) => Number(v))
      .optional()
  ),
  fee_wallet_id: z.number().positive().optional(),
  fee_note: z.string().max(200).optional().nullable(),
});
