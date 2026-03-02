import { z } from "zod";

const usernameRegex = /^[A-Za-z0-9._]+$/;

export const signinSchema = z.object({
    email: z
        .string()
        .trim()
        .toLowerCase()
        .email("Enter a valid email address"),
    password: z.string().min(1, "Password is required"),
});

export const signupSchema = z.object({
    username: z
        .string()
        .trim()
        .min(3, "Username must be 3-32 characters long")
        .max(32, "Username must be 3-32 characters long")
        .refine((v) => !v.includes(" "), "Username cannot contain spaces")
        .refine((v) => usernameRegex.test(v), "Username can only use letters, numbers, dots, and underscores")
        .refine((v) => ![".", "_"].includes(v[0]) && ![".", "_"].includes(v[v.length - 1]), "Username cannot start or end with . or _")
        .refine((v) => !v.includes("..") && !v.includes("__") && !v.includes("._") && !v.includes("_."), "Username cannot contain consecutive or mixed separators")
        .refine((v) => !/^\d+$/.test(v), "Username cannot be only numbers"),
    email: z
        .string()
        .trim()
        .toLowerCase()
        .email("Enter a valid email address"),
    password: z
        .string()
        .min(8, "Password too short (min 8)")
        .max(64, "Password too long (max 64)")
        .refine((v) => !v.includes(" "), "Password cannot contain spaces")
        .refine((v) => /[a-z]/.test(v), "Password must include a lowercase letter")
        .refine((v) => /[A-Z]/.test(v), "Password must include an uppercase letter")
        .refine((v) => /\d/.test(v), "Password must include a number")
        .refine((v) => /[^\w\s]/.test(v), "Password must include a special character"),
});

export const forgotPasswordSchema = z.object({
    email: z
        .string()
        .trim()
        .toLowerCase()
        .email("Enter a valid email address"),
});

export const resetPasswordSchema = z
    .object({
        token: z.string().trim().min(1, "Reset token is missing or invalid"),
        new_password: z
            .string()
            .min(8, "Password too short (min 8)")
            .max(64, "Password too long (max 64)")
            .refine((v) => !v.includes(" "), "Password cannot contain spaces")
            .refine((v) => /[a-z]/.test(v), "Password must include a lowercase letter")
            .refine((v) => /[A-Z]/.test(v), "Password must include an uppercase letter")
            .refine((v) => /\d/.test(v), "Password must include a number")
            .refine((v) => /[^\w\s]/.test(v), "Password must include a special character"),
        confirm_password: z.string(),
    })
    .refine((data) => data.new_password === data.confirm_password, {
        message: "Passwords do not match.",
        path: ["confirm_password"],
    });
