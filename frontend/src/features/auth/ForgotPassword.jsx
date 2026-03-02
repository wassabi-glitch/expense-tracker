import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { forgotPassword } from "@/lib/api";
import { signinSchema } from "./authSchemas.js";
import { AuthFormCard } from "@/components/AuthFormCard";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const translateValidation = (message) => t(message, { defaultValue: message });
  const initialEmail = useMemo(() => {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search);
    return params.get("email") || "";
  }, []);

  const [email, setEmail] = useState(initialEmail);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const forgotInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
  const disabledForgotButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";
  const emailParsed = useMemo(() => signinSchema.shape.email.safeParse(email), [email]);
  const emailLiveError = useMemo(() => {
    if (emailParsed.success || email.trim().length === 0) return "";
    return translateValidation(emailParsed.error.issues[0]?.message || "");
  }, [emailParsed, email, translateValidation]);
  const canSubmit = emailParsed.success && !isSubmitting && !status;
  const mapForgotError = (message) => {
    const msg = String(message || "");
    const normalized = msg.toLowerCase();
    if (normalized === "auth.forgot_password_rate_limited") {
      return t("auth.forgotPasswordTooManyRequests");
    }
    if (normalized.includes("too many password reset requests")) {
      return t("auth.forgotPasswordTooManyRequests");
    }
    return t(msg, { defaultValue: msg || t("auth.forgotPasswordRequestFailed") });
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
      const data = await forgotPassword(parsed.data);
      const message = String(data?.message || "");
      if (
        message.toLowerCase().includes("if the account exists") ||
        message.toLowerCase().includes("check your email inbox")
      ) {
        setStatus(t("auth.forgotPasswordSuccess"));
      } else {
        setStatus(message || t("auth.forgotPasswordSuccess"));
      }
    } catch (err) {
      setError(mapForgotError(err.message));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthFormCard
      title={t("auth.forgotPasswordTitle")}
      description={t("auth.forgotPasswordDescription")}
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
            className={forgotInputClass}
            required
          />
          <div className="min-h-2.5">
            {(emailLiveError || error) && (
              <p className="text-xs text-red-500">{emailLiveError || error}</p>
            )}
          </div>
        </div>

        <Button
          type="submit"
          className={`h-11 w-full ${disabledForgotButtonCursorClass}`}
          disabled={!canSubmit}
        >
          {isSubmitting ? (
            <span
              aria-label="Loading"
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
            />
          ) : (
            t("auth.sendResetLink")
          )}
        </Button>

        <div className="min-h-3">
          {!!status && (
            <p className="text-xs text-center text-emerald-600">
              {status}
            </p>
          )}
        </div>
      </form>

      <div className="mt-1.5 text-center text-sm text-muted-foreground">
        {t("auth.rememberedPassword")}{" "}
        <Link to="/sign-in" className="underline font-medium text-foreground hover:text-foreground/80">
          {t("auth.backToSignIn")}
        </Link>
      </div>
    </AuthFormCard>
  );
}
