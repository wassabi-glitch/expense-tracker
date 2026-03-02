import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Check, Circle, Eye, EyeOff } from "lucide-react";
import { z } from "zod";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Link, useNavigate } from "react-router-dom";
import { Card } from "./components/ui/card";
import { getGoogleLoginUrl, signup } from "./api";
import { evaluatePasswordRules, signinSchema, signupSchema } from "./auth/authSchemas.js";

const usernameRegex = /^[A-Za-z0-9._]+$/;
const signupStepOneSchema = z.object({
    email: signinSchema.shape.email,
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
});

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
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [status, setStatus] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [fieldErrors, setFieldErrors] = useState({});
    const stepBackTimerRef = useRef(null);
    const signupInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
    const disabledSignupButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";

    const translateValidation = (message) => t(message, { defaultValue: message });
    const passwordRules = evaluatePasswordRules(password, email);
    const passwordTouched = password.length > 0;

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

    const stepOneParsed = useMemo(
        () => signupStepOneSchema.safeParse({ email, username }),
        [email, username]
    );
    const stepOneIssuesByField = useMemo(() => {
        if (stepOneParsed.success) return {};
        const next = {};
        stepOneParsed.error.issues.forEach((issue) => {
            const field = issue.path?.[0];
            if (field && !next[field]) next[field] = translateValidation(issue.message);
        });
        return next;
    }, [stepOneParsed, translateValidation]);

    const fullSignupParsed = useMemo(
        () => signupSchema.safeParse({ username, email, password }),
        [username, email, password]
    );

    const canContinue = stepOneParsed.success;
    const canCreateAccount = fullSignupParsed.success && !isSubmitting;

    useEffect(() => {
        return () => {
            if (stepBackTimerRef.current) {
                clearTimeout(stepBackTimerRef.current);
            }
        };
    }, []);

    function delayReturnToStepOneWithFieldError(field, message) {
        if (step !== 2) return;
        if (stepBackTimerRef.current) {
            clearTimeout(stepBackTimerRef.current);
        }
        stepBackTimerRef.current = setTimeout(() => {
            setStep(1);
            setFieldErrors((prev) => ({ ...prev, [field]: message }));
            setStatus("");
            stepBackTimerRef.current = null;
        }, 1500);
    }

    function handleContinue(e) {
        e.preventDefault();
        setStatus("");
        setFieldErrors({});
        if (!stepOneParsed.success) {
            const nextErrors = {};
            stepOneParsed.error.issues.forEach((issue) => {
                const field = issue.path?.[0];
                if (field && !nextErrors[field]) nextErrors[field] = translateValidation(issue.message);
            });
            setFieldErrors(nextErrors);
            return;
        }
        setStep(2);
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setStatus("");
        setFieldErrors({});

        const parsed = signupSchema.safeParse({ username, email, password });
        if (!parsed.success) {
            const nextErrors = {};
            parsed.error.issues.forEach((issue) => {
                const field = issue.path?.[0];
                if (field && !nextErrors[field]) nextErrors[field] = translateValidation(issue.message);
            });
            setFieldErrors(nextErrors);
            return;
        }

        setIsSubmitting(true);
        try {
            await signup(parsed.data.username, parsed.data.email, parsed.data.password);
            navigate(`/resend-verification?signup=1&email=${encodeURIComponent(parsed.data.email)}`);
        } catch (err) {
            const msg = String(err?.message || "");
            const normalized = msg.toLowerCase();
            if (msg === "auth.username_already_taken" || normalized === "username already taken") {
                const usernameMsg = t("auth.usernameAlreadyTaken");
                setStatus(usernameMsg);
                delayReturnToStepOneWithFieldError("username", usernameMsg);
            } else if (msg === "auth.email_already_registered" || normalized === "email already registered") {
                const emailMsg = t("auth.emailAlreadyRegistered");
                setStatus(emailMsg);
                delayReturnToStepOneWithFieldError("email", emailMsg);
            } else if (msg === "auth.signup_conflict" || normalized === "email or username already registered") {
                setStatus(t("auth.signupConflict"));
            } else if (msg === "auth.signup_rate_limited") {
                setStatus(t("auth.signupRateLimited"));
            } else {
                setStatus(t(msg, { defaultValue: msg || t("auth.signupFailed") }));
            }
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="w-full min-h-screen lg:grid lg:grid-cols-2">
            <div className="hidden lg:flex flex-col justify-between bg-zinc-950 text-white p-12 relative overflow-hidden h-full">
                <div
                    className="absolute inset-0 z-0 opacity-[0.15]"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' viewBox='0 0 100 100' preserveAspectRatio='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='%23a1a1aa' stroke-width='0.5' d='M0 0 C 20 10, 40 30, 60 40 S 80 60, 100 100 M0 20 C 20 30, 40 50, 60 60 S 80 80, 100 120 M0 40 C 20 50, 40 70, 60 80 S 80 100, 100 140 M0 60 C 20 70, 40 90, 60 100 S 80 120, 100 160 M0 80 C 20 90, 40 110, 60 120 S 80 140, 100 180' vector-effect='non-scaling-stroke'/%3E%3C/svg%3E")`,
                        backgroundSize: "cover",
                    }}
                />
                <div className="absolute inset-0 z-0 bg-gradient-to-br from-transparent via-zinc-200/5 to-zinc-400/10" />

                <div className="relative z-10 flex items-center gap-3">
                    <div className="h-8 w-8 bg-white rounded-sm flex items-center justify-center">
                        <span className="text-zinc-950 font-bold font-mono">/</span>
                    </div>
                    <span className="font-mono text-sm tracking-widest uppercase text-zinc-400">
                        ExpenseTracker_v1.0
                    </span>
                </div>

                <div className="relative z-10 space-y-6">
                    <h2 className="text-3xl font-bold leading-tight tracking-tighter">
                        Financial data infrastructure.
                    </h2>
                    <div className="grid grid-cols-2 gap-4 border-t border-zinc-800 pt-6">
                        <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">{t("auth.status")}</p>
                            <div className="flex items-center gap-2">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                </span>
                                <p className="font-medium text-sm text-emerald-400">{t("auth.operational")}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div
                className="relative flex h-full min-h-screen w-full items-start lg:items-center justify-center bg-white px-4 pt-12 pb-8 sm:pt-16 sm:pb-10 lg:py-12"
            >
                {step === 2 && (
                    <button
                        type="button"
                        onClick={() => {
                            setStep(1);
                            setStatus("");
                            setFieldErrors({});
                        }}
                        className="absolute left-4 top-4 sm:left-8 sm:top-8 inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4" />
                                    <span>{t("common.back")}</span>
                    </button>
                )}
                <Card className="w-full max-w-md md:max-w-lg border-0 bg-transparent p-0 shadow-none">
                    <div className="px-6 py-6 sm:px-8 sm:py-8">
                        <div className="mb-6 h-5" />

                        <div className="mb-6 text-center">
                            <div className="mb-5 flex items-center justify-center gap-2.5">
                                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-foreground text-background">
                                    <span className="font-bold font-mono text-sm">/</span>
                                </div>
                                <span className="text-2xl font-semibold tracking-tight text-foreground">ExpenseTracker</span>
                            </div>
                            <h1 className="text-3xl font-semibold tracking-tight">{t("auth.welcomeToExpenseTracker")}</h1>
                        </div>

                        {step === 1 ? (
                            <form onSubmit={handleContinue} className="space-y-2">
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
                                        value={email}
                                        onChange={(e) => {
                                            setEmail(e.target.value);
                                            setStatus("");
                                            setFieldErrors((prev) => ({ ...prev, email: "" }));
                                        }}
                                        placeholder={t("auth.email")}
                                        className={signupInputClass}
                                        required
                                    />
                                    <div className="min-h-2.5">
                                        {((email.trim().length > 0 && stepOneIssuesByField.email) || fieldErrors.email) && (
                                            <p className="text-xs text-red-500">
                                                {(email.trim().length > 0 && stepOneIssuesByField.email) || fieldErrors.email}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                <div className="space-y-0.5">
                                    <Input
                                        id="signup-username-step"
                                        value={username}
                                        onChange={(e) => {
                                            setUsername(e.target.value);
                                            setStatus("");
                                            setFieldErrors((prev) => ({ ...prev, username: "" }));
                                        }}
                                        className={signupInputClass}
                                        placeholder={t("auth.username")}
                                        required
                                    />
                                    <div className="min-h-2.5">
                                        {((username.trim().length > 0 && stepOneIssuesByField.username) || fieldErrors.username) && (
                                            <p className="text-xs text-red-500">
                                                {(username.trim().length > 0 && stepOneIssuesByField.username) || fieldErrors.username}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                <Button
                                    className={`h-11 w-full ${disabledSignupButtonCursorClass}`}
                                    type="submit"
                                    disabled={!canContinue}
                                >
                                    {t("auth.continue")}
                                </Button>

                                <div className="min-h-2.5">
                                    {!!status && <p className="text-xs text-center text-red-500">{status}</p>}
                                </div>
                            </form>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-2">
                                <div className="space-y-0.5">
                                    <div className="relative">
                                        <Input
                                            id="password"
                                            type={showPassword ? "text" : "password"}
                                            value={password}
                                            onChange={(e) => {
                                                setPassword(e.target.value);
                                                setStatus("");
                                                setFieldErrors((prev) => ({ ...prev, password: "" }));
                                            }}
                                            className={`${signupInputClass} pr-10`}
                                            placeholder={t("auth.createNewPasswordPlaceholder")}
                                            required
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
                                        {!!fieldErrors.password && (
                                            <p className="text-xs text-red-500">{fieldErrors.password}</p>
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

                                <Button
                                    className={`h-11 w-full ${disabledSignupButtonCursorClass}`}
                                    type="submit"
                                    disabled={!canCreateAccount}
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

                                <div className="min-h-2.5">
                                    {!!status && <p className="text-xs text-center text-red-500">{status}</p>}
                                </div>
                            </form>
                        )}

                        <div className="mt-1.5 text-center text-sm text-muted-foreground">
                            {t("auth.alreadyHaveAccount")}{" "}
                            <Link to="/sign-in" className="underline font-medium text-foreground hover:text-foreground/80">
                                {t("auth.signIn")}
                            </Link>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}
