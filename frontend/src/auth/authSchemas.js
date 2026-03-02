import { z } from "zod";

const usernameRegex = /^[A-Za-z0-9._]+$/;

const basePasswordSchema = z
  .string()
  .min(8, "auth.validation.password.min")
  .max(64, "auth.validation.password.max")
  .refine((v) => !v.includes(" "), "auth.validation.password.noSpaces")
  .refine((v) => /[a-z]/.test(v), "auth.validation.password.lowercase")
  .refine((v) => /[A-Z]/.test(v), "auth.validation.password.uppercase")
  .refine((v) => /\d/.test(v), "auth.validation.password.number")
  .refine((v) => /[^\w\s]/.test(v), "auth.validation.password.special");

function getEmailLocalPart(email) {
  const normalized = String(email || "").trim().toLowerCase();
  const atIndex = normalized.indexOf("@");
  return atIndex > 0 ? normalized.slice(0, atIndex) : "";
}

export function evaluatePasswordRules(password, email = "") {
  const value = String(password || "");
  const normalized = value.toLowerCase();
  const localPart = getEmailLocalPart(email);

  return {
    minLength: value.length >= 8,
    hasLowercase: /[a-z]/.test(value),
    hasUppercase: /[A-Z]/.test(value),
    hasNumber: /\d/.test(value),
    hasSpecial: /[^\w\s]/.test(value),
    noSpaces: !value.includes(" "),
    noEmailLocalPart: localPart ? !normalized.includes(localPart) : true,
    hasEmailLocalPart: Boolean(localPart),
  };
}

export function evaluateUsernameRules(username) {
  const value = String(username || "").trim();
  const hasValue = value.length > 0;

  return {
    hasValue,
    length: value.length >= 3 && value.length <= 32,
    noSpaces: !value.includes(" "),
    allowedChars: usernameRegex.test(value),
    edgeSeparators: hasValue ? ![".", "_"].includes(value[0]) && ![".", "_"].includes(value[value.length - 1]) : false,
    noConsecutiveSeparators: !value.includes("..") && !value.includes("__") && !value.includes("._") && !value.includes("_."),
    notOnlyNumbers: hasValue ? !/^\d+$/.test(value) : false,
  };
}

export const signinSchema = z.object({
  email: z.string().trim().toLowerCase().email("auth.validation.email.invalid"),
  password: z
    .string()
    .min(1, "auth.validation.password.required")
    .min(6, "auth.validation.password.loginMin"),
});

export const signupSchema = z.object({
  username: z
    .string()
    .trim()
    .min(3, "auth.validation.username.length")
    .max(32, "auth.validation.username.length")
    .refine((v) => !v.includes(" "), "auth.validation.username.noSpaces")
    .refine((v) => usernameRegex.test(v), "auth.validation.username.allowedChars")
    .refine(
      (v) => ![".", "_"].includes(v[0]) && ![".", "_"].includes(v[v.length - 1]),
      "auth.validation.username.edgeSeparators"
    )
    .refine(
      (v) => !v.includes("..") && !v.includes("__") && !v.includes("._") && !v.includes("_."),
      "auth.validation.username.consecutiveSeparators"
    )
    .refine((v) => !/^\d+$/.test(v), "auth.validation.username.notOnlyNumbers"),
  email: z.string().trim().toLowerCase().email("auth.validation.email.invalid"),
  password: basePasswordSchema,
}).refine(
  (data) => {
    const localPart = getEmailLocalPart(data.email);
    return !localPart || !data.password.toLowerCase().includes(localPart);
  },
  {
    message: "auth.validation.password.noEmailLocalPart",
    path: ["password"],
  }
);

export const resetPasswordSchema = z
  .object({
    token: z.string().trim().min(1, "auth.validation.reset.tokenRequired"),
    new_password: basePasswordSchema,
    confirm_password: z.string().min(1, "auth.validation.reset.confirmRequired"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "auth.validation.reset.passwordsMismatch",
    path: ["confirm_password"],
  });
