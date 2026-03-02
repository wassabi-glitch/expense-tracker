import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { resendVerification } from "@/lib/api";
import { signinSchema } from "./authSchemas.js";
import { AuthFormCard } from "@/components/AuthFormCard";

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
    <AuthFormCard
      title={t("auth.resendVerificationPageTitle")}
      description={t("auth.resendVerificationPageDescription")}
    >

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
    </AuthFormCard>
  );
}
