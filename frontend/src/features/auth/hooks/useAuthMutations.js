import { useMutation } from "@tanstack/react-query";
import {
    forgotPassword,
    resendVerification,
    resetPassword,
    signin,
    signup,
    verifyEmail,
} from "@/lib/api";

export function useSigninMutation() {
    return useMutation({
        mutationFn: ({ email, password }) => signin(email, password),
    });
}

export function useSignupMutation() {
    return useMutation({
        mutationFn: ({ username, email, password }) => signup(username, email, password),
    });
}

export function useForgotPasswordMutation() {
    return useMutation({
        mutationFn: ({ email, captchaToken }) => forgotPassword(email, captchaToken),
    });
}

export function useResetPasswordMutation() {
    return useMutation({
        mutationFn: ({ token, newPassword, captchaToken }) => resetPassword(token, newPassword, captchaToken),
    });
}

export function useResendVerificationMutation() {
    return useMutation({
        mutationFn: resendVerification,
    });
}

export function useVerifyEmailMutation() {
    return useMutation({
        mutationFn: verifyEmail,
    });
}
