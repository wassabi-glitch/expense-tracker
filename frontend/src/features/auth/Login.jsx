import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Link, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { getGoogleLoginUrl } from "@/lib/api";
import { signinSchema } from "./authSchemas.js";
import { AuthFormCard } from "@/components/AuthFormCard";
import { useSigninMutation } from "./hooks/useAuthMutations";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRateLimitGate } from "@/hooks/useRateLimitGate";

function GoogleIcon() {
    return (
        <svg
            aria-hidden="true"
            className="h-5 w-5"
            viewBox="0 0 18 18"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path
                fill="#4285F4"
                d="M17.64 9.2045c0-.638-.0573-1.2518-.1636-1.8409H9v3.4818h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2582h2.9086c1.7027-1.5673 2.6841-3.8741 2.6841-6.6155z"
            />
            <path
                fill="#34A853"
                d="M9 18c2.43 0 4.4673-.8059 5.9563-2.1791l-2.9086-2.2582c-.8059.54-1.8368.8591-3.0477.8591-2.3441 0-4.3282-1.5832-5.0359-3.7105H.9577v2.3327C2.4382 15.9832 5.4818 18 9 18z"
            />
            <path
                fill="#FBBC05"
                d="M3.9641 10.7105c-.18-.54-.2823-1.1168-.2823-1.7105s.1023-1.1705.2823-1.7105V4.9568H.9577C.3477 6.1718 0 7.5491 0 9s.3477 2.8282.9577 4.0432l3.0064-2.3327z"
            />
            <path
                fill="#EA4335"
                d="M9 3.5782c1.3214 0 2.5077.4541 3.4391 1.3459l2.5786-2.5786C13.4636.8946 11.4273 0 9 0 5.4818 0 2.4382 2.0168.9577 4.9568l3.0064 2.3327C4.6718 5.1614 6.6559 3.5782 9 3.5782z"
            />
        </svg>
    );
}

export default function Login() {
    const { t } = useTranslation();
    const translateValidation = useCallback((message) => t(message, { defaultValue: message }), [t]);
    
    const [showPassword, setShowPassword] = useState(false);
    const [status, setStatus] = useState("");
    const [showResendVerification, setShowResendVerification] = useState(false);
    
    const signinMutation = useSigninMutation();
    const isSubmitting = signinMutation.isPending;
    const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setStatus("") });
    const navigate = useNavigate();

    const {
        register,
        handleSubmit,
        setError,
        watch,
        formState: { errors }
    } = useForm({
        resolver: zodResolver(signinSchema),
        defaultValues: {
            email: "",
            password: "",
        },
        mode: "onChange"
    });

    const email = watch("email");

    const loginInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
    const disabledLoginButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";

    useEffect(() => {
        // Clean up a stray empty hash so URL stays /sign-in instead of /sign-in#
        if (window.location.hash === "#") {
            window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
        }

        const searchParams = new URLSearchParams(window.location.search);
        const errorParam = searchParams.get("error");
        if (errorParam) {
            setStatus(t(errorParam, { defaultValue: errorParam }));
            searchParams.delete("error");
            const newSearch = searchParams.toString();
            window.history.replaceState(null, "", `${window.location.pathname}${newSearch ? `?${newSearch}` : ""}`);
        }
    }, [t]);

    async function onSubmit(data) {
        setStatus("");
        setShowResendVerification(false);

        try {
            await signinMutation.mutateAsync({
                email: data.email,
                password: data.password,
            });
            navigate("/dashboard");
        } catch (err) {
            onRateLimitError(err);
            const msg = String(err?.message || "");
            if (msg === "auth.invalid_credentials" || msg.toLowerCase() === "invalid credentials") {
                setStatus(t("auth.invalidCredentials"));
                setError("email", { type: "server", message: "auth.invalidCredentials" });
                setError("password", { type: "server", message: "auth.invalidCredentials" });
                setShowResendVerification(false);
            } else if (msg === "auth.email_not_verified") {
                setStatus(t("auth.emailNotVerified"));
                setShowResendVerification(true);
            } else if (msg === "auth.login_rate_limited") {
                setStatus(t("auth.loginRateLimited"));
            } else if (msg === "auth.idempotency_conflict_in_progress") {
                setStatus(t("auth.loginIdempotencyConflictInProgress"));
            } else {
                setStatus(t(msg, { defaultValue: msg || t("auth.loginFailed") }));
            }
        }
    }

    return (
        <AuthFormCard title={t("auth.loginTitle")}>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-2">
                <Button type="button" variant="outline" className="h-11 w-full" asChild>
                    <a href={getGoogleLoginUrl()} className="inline-flex items-center justify-center gap-2">
                        <GoogleIcon />
                        <span>{t("auth.continueWithGoogle")}</span>
                    </a>
                </Button>

                <div className="relative py-0">
                    <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-border" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase tracking-wide text-muted-foreground">
                        <span className="bg-white px-3">{t("auth.or")}</span>
                    </div>
                </div>

                <div className="space-y-0.5">
                    <Input
                        id="email"
                        type="email"
                        placeholder={t("auth.email")}
                        className={`${loginInputClass} ${errors.email ? "border-red-500 focus-visible:border-red-500" : ""}`}
                        {...register("email")}
                    />
                    <div className="min-h-2.5">
                        {errors.email && (
                            <p className="text-xs text-red-500">
                                {translateValidation(errors.email.message)}
                            </p>
                        )}
                    </div>
                </div>

                <div className="space-y-0.5">
                    <div className="relative">
                        <Input
                            id="password"
                            type={showPassword ? "text" : "password"}
                            className={`${loginInputClass} pr-10 ${errors.password ? "border-red-500 focus-visible:border-red-500" : ""}`}
                            placeholder={t("auth.password")}
                            {...register("password")}
                        />
                        <button
                            type="button"
                            onClick={() => setShowPassword((v) => !v)}
                            className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
                            aria-label={showPassword ? "Hide password" : "Show password"}
                        >
                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                    </div>
                    <div className="min-h-2.5">
                        {errors.password && (
                            <p className="mt-1 text-xs text-red-500">
                                {translateValidation(errors.password.message)}
                            </p>
                        )}
                    </div>
                    <div className="mt-0.5">
                        <Link
                            to={email ? `/forgot-password?email=${encodeURIComponent(email)}` : "/forgot-password"}
                            className="text-[13px] text-gray-400 hover:underline active:underline focus-visible:underline"
                        >
                            {t("auth.forgotPassword")}
                        </Link>
                    </div>
                </div>

                <Button
                    type="submit"
                    className={`h-11 w-full ${disabledLoginButtonCursorClass}`}
                    disabled={isSubmitting || isRateLimited || !!errors.email || !!errors.password}
                >
                    {isSubmitting ? (
                        <span
                            aria-label="Loading"
                            className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                        />
                    ) : (
                        t("auth.signIn")
                    )}
                </Button>

                <div className="min-h-2.5">
                    {!!status && <p className="text-xs text-center text-red-500">{status}</p>}
                </div>

                {showResendVerification && (
                    <p className="text-sm text-center text-muted-foreground">
                        <Link
                            to={email ? `/resend-verification?email=${encodeURIComponent(email)}` : "/resend-verification"}
                            className="underline font-medium text-foreground hover:text-foreground/80"
                        >
                            {t("auth.resendVerificationAction")}
                        </Link>
                    </p>
                )}
            </form>

            <div className="mt-1.5 text-center text-sm text-muted-foreground">
                {t("auth.dontHaveAccount")}{" "}
                <Link to="/sign-up" className="underline font-medium text-foreground hover:text-foreground/80">
                    {t("auth.signUp")}
                </Link>
            </div>
        </AuthFormCard>
    );
}
