import { z } from "zod";
import { toISODateInTimeZone } from "@/lib/date";

export const MAX_INCOME_AMOUNT = 999_999_999_999;
export const MAX_INCOME_SOURCE_NAME_LENGTH = 32;
export const MAX_INCOME_NOTE_LENGTH = 200;
const MAX_INCOME_AMOUNT_STR = String(MAX_INCOME_AMOUNT);

const sourceNameSchema = z
  .string()
  .transform((v) => v.trim())
  .refine((v) => v.length > 0, "income.sourceNameRequired")
  .refine((v) => v.length <= MAX_INCOME_SOURCE_NAME_LENGTH, "income.sourceNameTooLong");

const amountSchema = z.preprocess(
  (value) => String(value ?? "").trim().replace(/\s+/g, ""),
  z
    .string()
    .refine((v) => v.length > 0, "income.amountRequired")
    .refine((v) => /^\d+$/.test(v), "income.amountInvalid")
    .refine(
      (v) =>
        v.length < MAX_INCOME_AMOUNT_STR.length ||
        (v.length === MAX_INCOME_AMOUNT_STR.length && v <= MAX_INCOME_AMOUNT_STR),
      "income.amountTooLarge"
    )
    .transform((v) => Number(v))
    .refine((v) => Number.isSafeInteger(v) && v > 0, "income.amountInvalid")
);

const dateSchema = z
  .string()
  .trim()
  .refine((v) => v.length > 0, "income.dateRequired")
  .refine((v) => /^\d{4}-\d{2}-\d{2}$/.test(v), "income.dateRequired")
  .refine((v) => {
    const todayISO = toISODateInTimeZone();
    const monthStartISO = `${todayISO.slice(0, 7)}-01`;
    return v >= monthStartISO;
  }, "income.dateCurrentMonthOnly")
  .refine((v) => v <= toISODateInTimeZone(), "income.dateFuture");

const noteSchema = z.preprocess(
  (value) => String(value ?? ""),
  z
    .string()
    .transform((v) => v.trim())
    .refine((v) => v.length <= MAX_INCOME_NOTE_LENGTH, "income.noteTooLong")
);

export const incomeSourceFormSchema = z.object({
  name: sourceNameSchema,
});

export const incomeEntryFormSchema = z.object({
  amount: amountSchema,
  date: dateSchema,
  note: noteSchema,
});

