import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle2 } from "lucide-react";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Card } from "./components/ui/card";
import { resendVerification } from "./api";
import { signinSchema } from "./auth/authSchemas.js";

export default function ResendVerification() {
  const INITIAL_SIGNUP_COOLDOWN_SECONDS = 20;
  const { t } = useTranslation();
  const translateValidation = (message) => t(message, { defaultValue: message });
  const initialEmail = useMemo(() => {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search);
    return params.get("email") || "";
  }, []);
  const fromSignup = useMemo(() => {
    if (typeof window === "undefined") return false;
    const params = new URLSearchParams(window.location.search);
    return params.get("signup") === "1";
  }, []);

  const [email, setEmail] = useState(initialEmail);
  const [status, setStatus] = useState(fromSignup ? t("auth.signupCheckEmail") : "");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(
    fromSignup && initialEmail ? INITIAL_SIGNUP_COOLDOWN_SECONDS : 0
  );
  const resendInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
  const disabledResendButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";
  const emailParsed = useMemo(() => signinSchema.shape.email.safeParse(email), [email]);
  const emailLiveError = useMemo(() => {
    if (emailParsed.success || email.trim().length === 0) return "";
    return translateValidation(emailParsed.error.issues[0]?.message || "");
  }, [emailParsed, email, translateValidation]);
  const canSubmit = emailParsed.success && !isSubmitting && cooldownSeconds === 0;

  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const id = window.setTimeout(() => {
      setCooldownSeconds((s) => Math.max(0, s - 1));
    }, 1000);
    return () => window.clearTimeout(id);
  }, [cooldownSeconds]);

  const mapResendError = (err) => {
    const msg = String(err?.message || "");
    const normalized = msg.toLowerCase();
    if (normalized === "auth.resend_verification_rate_limited") {
      if (Number.isFinite(err?.retryAfterSeconds) && err.retryAfterSeconds > 0) {
        return t("auth.resendVerificationTooManyWait", { seconds: err.retryAfterSeconds });
      }
      return t("auth.resendVerificationTooManyRequests");
    }
    return t(msg, { defaultValue: msg || t("auth.resendVerificationFailed") });
  };

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setStatus("");
    const parsed = signinSchema.shape.email.safeParse(email);
    if (!parsed.success) {
      setError(translateValidation(parsed.error.issues[0]?.message || "auth.validation.email.invalid"));
      return;
    }
    setIsSubmitting(true);
    try {
      const data = await resendVerification(parsed.data);
      const message = String(data?.message || "");
      if (message.toLowerCase().includes("verification link") || message.toLowerCase().includes("email inbox")) {
        setStatus(t("auth.resendVerificationSuccess"));
      } else {
        setStatus(message || t("auth.resendVerificationSuccess"));
      }
      setCooldownSeconds(INITIAL_SIGNUP_COOLDOWN_SECONDS);
    } catch (err) {
      setError(mapResendError(err));
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
              <h1 className="text-3xl font-semibold tracking-tight">{t("auth.resendVerificationPageTitle")}</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {t("auth.resendVerificationPageDescription")}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-2">
              <div className="space-y-0.5">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setStatus("");
                  setError("");
                }}
                placeholder={t("auth.email")}
                className={resendInputClass}
                required
              />
                <div className="min-h-2.5">
                  {(emailLiveError || error) && (
                    <p className="text-xs text-red-500">{emailLiveError || error}</p>
                  )}
                </div>
              </div>

              {!!status && (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3 text-left">
                  <div className="flex items-start gap-2.5">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-emerald-800">{status}</p>
                      <p className="mt-0.5 text-xs text-emerald-700/90">
                        {t("auth.checkSpamFolder", { defaultValue: "Also check your spam/junk folder." })}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <Button
                type="submit"
                className={`h-11 w-full ${disabledResendButtonCursorClass}`}
                disabled={!canSubmit}
              >
                {isSubmitting
                  ? (
                    <span
                      aria-label="Loading"
                      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                    />
                  )
                  : cooldownSeconds > 0
                    ? t("auth.resendVerificationWait", {
                        seconds: cooldownSeconds,
                        defaultValue: `Wait ${cooldownSeconds}s before resending`,
                      })
                    : t("auth.resendVerificationAction")}
              </Button>
            </form>

            <div className="mt-1.5 text-center text-sm text-muted-foreground">
              <Link to="/sign-in" className="underline font-medium text-foreground hover:text-foreground/80">
                {t("auth.backToSignIn")}
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
