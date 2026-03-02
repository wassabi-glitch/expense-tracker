import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Link, useNavigate } from "react-router-dom";
import { Card } from "./components/ui/card";
import { getGoogleLoginUrl, signin } from "./api";
import { signinSchema } from "./auth/authSchemas.js";

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
    const translateValidation = (message) => t(message, { defaultValue: message });
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [status, setStatus] = useState("");
    const [fieldErrors, setFieldErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showResendVerification, setShowResendVerification] = useState(false);
    const navigate = useNavigate();
    const loginInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
    const disabledLoginButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";
    const signinParsed = useMemo(() => signinSchema.safeParse({ email, password }), [email, password]);
    const canSignIn = signinParsed.success && !isSubmitting;
    const liveSigninIssuesByField = useMemo(() => {
        if (signinParsed.success) return {};
        const next = {};
        signinParsed.error.issues.forEach((issue) => {
            const field = issue.path?.[0];
            if (field && !next[field]) next[field] = translateValidation(issue.message);
        });
        return next;
    }, [signinParsed, translateValidation]);

    useEffect(() => {
        // Clean up a stray empty hash so URL stays /sign-in instead of /sign-in#
        if (window.location.hash === "#") {
            window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
        }

    }, []);

    async function handleSubmit(e) {
        e.preventDefault();
        setStatus("");
        setFieldErrors({});

        const parsed = signinSchema.safeParse({ email, password });
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
            await signin(parsed.data.email, parsed.data.password);
            navigate("/dashboard");
        } catch (err) {
            const msg = String(err?.message || "");
            if (msg === "auth.invalid_credentials" || msg.toLowerCase() === "invalid credentials") {
                setStatus(t("auth.invalidCredentials"));
                setShowResendVerification(false);
            } else if (msg === "auth.email_not_verified") {
                setStatus(t("auth.emailNotVerified"));
                setShowResendVerification(true);
            } else if (msg === "auth.login_rate_limited") {
                setStatus(t("auth.loginRateLimited"));
            } else {
                setStatus(t(msg, { defaultValue: msg || t("auth.loginFailed") }));
            }
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div className="w-full min-h-screen lg:grid lg:grid-cols-2">

            {/* LEFT SIDE */}
            <div className="hidden lg:flex flex-col justify-between bg-zinc-950 text-white p-12 relative overflow-hidden h-full">

                {/* --- 1. THE MODERN PATTERN LAYER --- */}
                {/* This replaces the <img> tag. It's a subtle SVG pattern. */}
                <div
                    className="absolute inset-0 z-0 opacity-[0.15]"
                    style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='100%25' height='100%25' viewBox='0 0 100 100' preserveAspectRatio='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill='none' stroke='%23a1a1aa' stroke-width='0.5' d='M0 0 C 20 10, 40 30, 60 40 S 80 60, 100 100 M0 20 C 20 30, 40 50, 60 60 S 80 80, 100 120 M0 40 C 20 50, 40 70, 60 80 S 80 100, 100 140 M0 60 C 20 70, 40 90, 60 100 S 80 120, 100 160 M0 80 C 20 90, 40 110, 60 120 S 80 140, 100 180' vector-effect='non-scaling-stroke'/%3E%3C/svg%3E")`,
                        backgroundSize: "cover",
                        // Optional: Add a subtle pulse animation
                        // animation: "pulse 10s cubic-bezier(0.4, 0, 0.6, 1) infinite"
                    }}
                ></div>

                {/* --- Local texture replacement (no external request) --- */}
                <div className="absolute inset-0 z-0 bg-gradient-to-br from-transparent via-zinc-200/5 to-zinc-400/10"></div>


                {/* --- 2. TOP CONTENT (Branding) --- */}
                <div className="relative z-10 flex items-center gap-3">
                    <div className="h-8 w-8 bg-white rounded-sm flex items-center justify-center">
                        <span className="text-zinc-950 font-bold font-mono">/</span>
                    </div>
                    <span className="font-mono text-sm tracking-widest uppercase text-zinc-400">
                        ExpenseTracker_v1.0
                    </span>
                </div>

                {/* --- 3. BOTTOM CONTENT (Specs) --- */}
                <div className="relative z-10 space-y-6">
                    <h2 className="text-3xl font-bold leading-tight tracking-tighter">
                        Financial data infrastructure.
                    </h2>

                    <div className="grid grid-cols-2 gap-4 border-t border-zinc-800 pt-6">
                        {/* <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Stack</p>
                            <p className="font-medium text-sm">React + FastAPI</p>
                        </div>
                        <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Storage</p>
                            <p className="font-medium text-sm">Postgres Docker</p>
                        </div>
                        <div>
                            <p className="text-[10px] font-mono text-zinc-500 uppercase mb-1">Auth</p>
                            <p className="font-medium text-sm">JWT Secure</p>
                        </div> */}
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
            {/* RIGHT SIDE */}
            <div className="relative flex h-full min-h-screen w-full items-start lg:items-center justify-center bg-white px-4 pt-12 pb-8 sm:pt-16 sm:pb-10 lg:py-12">
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
                            <h1 className="text-3xl font-semibold tracking-tight">{t("auth.loginTitle")}</h1>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-2">
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
                                    value={email}
                                    onChange={(e) => {
                                        setEmail(e.target.value);
                                        setStatus("");
                                        setFieldErrors((prev) => ({ ...prev, email: "" }));
                                    }}
                                    className={loginInputClass}
                                    required
                                />
                                <div className="min-h-2.5">
                                    {((email.trim().length > 0 && liveSigninIssuesByField.email) || fieldErrors.email) && (
                                        <p className="text-xs text-red-500">
                                            {(email.trim().length > 0 && liveSigninIssuesByField.email) || fieldErrors.email}
                                        </p>
                                    )}
                                </div>
                            </div>

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
                                        className={`${loginInputClass} pr-10`}
                                        placeholder={t("auth.password")}
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
                                    {((password.length > 0 && liveSigninIssuesByField.password) || fieldErrors.password) && (
                                        <p className="text-xs text-red-500">
                                            {(password.length > 0 && liveSigninIssuesByField.password) || fieldErrors.password}
                                        </p>
                                    )}
                                </div>
                                <div className="-mt-2">
                                    <Link
                                        to={email ? `/forgot-password?email=${encodeURIComponent(email)}` : "/forgot-password"}
                                        className="text-xs text-muted-foreground underline hover:text-foreground"
                                    >
                                        {t("auth.forgotPassword")}
                                    </Link>
                                </div>
                            </div>

                            <Button
                                type="submit"
                                className={`h-11 w-full ${disabledLoginButtonCursorClass}`}
                                disabled={!canSignIn}
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
                    </div>
                </Card>
            </div>
        </div>
    )
}
