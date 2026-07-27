import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Check, Circle, Eye, EyeOff } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Link, useNavigate } from "react-router-dom";
import { getGoogleLoginUrl } from "@/lib/api";
import { evaluatePasswordRules, signinSchema, signupSchema } from "./authSchemas.js";
import { AuthFormCard } from "@/components/AuthFormCard";
import { useSignupMutation } from "./hooks/useAuthMutations";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Turnstile } from "@marsidev/react-turnstile";
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

export default function Signup() {
    const { t } = useTranslation();
    const navigate = useNavigate();

    const [step, setStep] = useState(1);
    const [showPassword, setShowPassword] = useState(false);
    const [status, setStatus] = useState("");
    const [captchaToken, setCaptchaToken] = useState("");
    
    const signupMutation = useSignupMutation();
    const isSubmitting = signupMutation.isPending;
    const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setStatus("") });

    const {
        register,
        handleSubmit,
        watch,
        trigger,
        setError,
        formState: { errors }
    } = useForm({
        resolver: zodResolver(signupSchema),
        defaultValues: {
            email: "",
            username: "",
            password: "",
        },
        mode: "onChange"
    });

    const email = watch("email");
    const password = watch("password");
    
    const translateValidation = useCallback((message) => t(message, { defaultValue: message }), [t]);
    const passwordRules = evaluatePasswordRules(password || "", email || "");
    const passwordTouched = (password || "").length > 0;

    const passwordChecklist = [
        { id: "minLength", text: t("auth.passwordRuleMinLength"), ok: passwordRules.minLength },
        { id: "hasLowercase", text: t("auth.passwordRuleLowercase"), ok: passwordRules.hasLowercase },
        { id: "hasUppercase", text: t("auth.passwordRuleUppercase"), ok: passwordRules.hasUppercase },
        { id: "hasNumber", text: t("auth.passwordRuleNumber"), ok: passwordRules.hasNumber },
        { id: "hasSpecial", text: t("auth.passwordRuleSpecial"), ok: passwordRules.hasSpecial },
        { id: "noSpaces", text: t("auth.passwordRuleNoSpaces"), ok: passwordRules.noSpaces },
    ];
    if (passwordRules.hasEmailLocalPart) {
        passwordChecklist.push({
            id: "noEmailLocalPart",
            text: t("auth.passwordRuleNoEmailLocalPart"),
            ok: passwordRules.noEmailLocalPart,
        });
    }

    const signupInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
    const disabledSignupButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";

    async function handleContinue() {
        setStatus("");
        const isStepValid = await trigger(["email", "username"]);
        if (isStepValid) {
            setStep(2);
        }
    }

    async function onSubmit(data) {
        setStatus("");
        try {
            const result = await signupMutation.mutateAsync({
                username: data.username,
                email: data.email,
                password: data.password,
                captcha_token: captchaToken || undefined,
            });
            const sent = result.verification_email_sent !== false ? 1 : 0;
            navigate(`/resend-verification?signup=1&email=${encodeURIComponent(data.email)}&sent=${sent}`);
        } catch (err) {
            onRateLimitError(err);
            const msg = String(err?.message || "");
            const normalized = msg.toLowerCase();
            if (msg === "auth.username_already_taken" || normalized === "username already taken") {
                const usernameMsg = t("auth.usernameAlreadyTaken");
                setStatus(usernameMsg);
                setError("username", { type: "server", message: "auth.usernameAlreadyTaken" });
                setStep(1);
            } else if (msg === "auth.email_already_registered" || normalized === "email already registered") {
                const emailMsg = t("auth.emailAlreadyRegistered");
                setStatus(emailMsg);
                setError("email", { type: "server", message: "auth.emailAlreadyRegistered" });
                setStep(1);
            } else if (msg === "auth.signup_conflict" || normalized === "email or username already registered") {
                setStatus(t("auth.signupConflict"));
            } else if (msg === "auth.signup_rate_limited") {
                setStatus(t("auth.signupRateLimited"));
            } else if (msg === "auth.signup_global_rate_limited") {
                setStatus(t("auth.signupGlobalRateLimited"));
            } else if (msg === "auth.captcha_failed") {
                setStatus(t("auth.captchaFailed"));
            } else if (msg === "auth.idempotency_conflict_in_progress") {
                setStatus(t("auth.idempotencyConflictInProgress"));
            } else if (msg === "auth.disposable_email_blocked") {
                setStatus(t("auth.disposableEmailBlocked"));
                setError("email", { type: "server", message: "auth.disposableEmailBlocked" });
                setStep(1);
            } else {
                setStatus(t(msg, { defaultValue: msg || t("auth.signupFailed") }));
            }
        }
    }

    return (
        <AuthFormCard
            title={t("auth.welcomeToExpenseTracker")}
            backButton={
                step === 2 && (
                    <button
                        type="button"
                        onClick={() => {
                            setStep(1);
                            setStatus("");
                        }}
                        className="absolute left-4 top-4 sm:left-8 sm:top-8 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        <span>{t("common.back")}</span>
                    </button>
                )
            }
        >
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-2">
                {step === 1 ? (
                    <>
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
                                <span className="bg-card px-3">{t("auth.or")}</span>
                            </div>
                        </div>

                        <div className="space-y-0.5">
                            <Input
                                id="signup-email"
                                type="email"
                                placeholder={t("auth.email")}
                                className={`${signupInputClass} ${errors.email ? "border-red-500 focus-visible:border-red-500" : ""}`}
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
                            <Input
                                id="signup-username-step"
                                className={`${signupInputClass} ${errors.username ? "border-red-500 focus-visible:border-red-500" : ""}`}
                                placeholder={t("auth.username")}
                                {...register("username")}
                            />
                            <div className="min-h-2.5">
                                {errors.username && (
                                    <p className="text-xs text-red-500">
                                        {translateValidation(errors.username.message)}
                                    </p>
                                )}
                            </div>
                        </div>

                        <Button
                            className={`h-11 w-full ${disabledSignupButtonCursorClass}`}
                            type="button"
                            onClick={handleContinue}
                            disabled={!!errors.email || !!errors.username}
                        >
                            {t("auth.continue")}
                        </Button>
                    </>
                ) : (
                    <>
                        <div className="space-y-0.5">
                            <div className="relative">
                                <Input
                                    id="password"
                                    type={showPassword ? "text" : "password"}
                                    className={`${signupInputClass} pr-10 ${errors.password ? "border-red-500 focus-visible:border-red-500" : ""}`}
                                    placeholder={t("auth.createNewPasswordPlaceholder")}
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
                                    <p className="text-xs text-red-500">{translateValidation(errors.password.message)}</p>
                                )}
                            </div>
                            <ul className="grid grid-cols-1 gap-y-1 pt-1 sm:grid-cols-2 sm:gap-x-4">
                                {passwordChecklist.map((rule) => {
                                    const isMet = passwordTouched ? rule.ok : false;
                                    return (
                                        <li
                                            key={rule.id}
                                            className={`flex items-center gap-1.5 text-xs ${passwordTouched ? (rule.ok ? "text-emerald-600" : "text-muted-foreground") : "text-muted-foreground"}`}
                                        >
                                            {isMet ? (
                                                <Check className="h-3 w-3 shrink-0" strokeWidth={2.25} />
                                            ) : (
                                                <Circle className="h-3 w-3 shrink-0" strokeWidth={2.25} />
                                            )}
                                            <span>{rule.text}</span>
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>

                        <div className="flex justify-center">
                            <Turnstile
                                siteKey={import.meta.env.VITE_TURNSTILE_SITE_KEY || "1x00000000000000000000AA"}
                                onSuccess={(token) => setCaptchaToken(token)}
                                options={{ appearance: "interaction-only" }}
                            />
                        </div>

                        <Button
                            className={`h-11 w-full ${disabledSignupButtonCursorClass}`}
                            type="submit"
                            disabled={isSubmitting || isRateLimited || !!errors.password}
                        >
                            {isSubmitting ? (
                                <span
                                    aria-label="Loading"
                                    className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                                />
                            ) : (
                                t("auth.createAccount")
                            )}
                        </Button>
                    </>
                )}
                <div className="min-h-2.5">
                    {!!status && <p className="text-xs text-center text-red-500">{status}</p>}
                </div>
            </form>

            <div className="mt-1.5 text-center text-sm text-muted-foreground">
                {t("auth.alreadyHaveAccount")}{" "}
                <Link to="/sign-in" className="underline font-medium text-foreground hover:text-foreground/80">
                    {t("auth.signIn")}
                </Link>
            </div>
        </AuthFormCard>
    );
}
