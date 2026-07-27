import { useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CheckCircle2, Check, Circle, Eye, EyeOff, XCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { evaluatePasswordRules, resetPasswordSchema } from "./authSchemas.js";
import { AuthFormCard } from "@/components/AuthFormCard";
import { useResetPasswordMutation } from "./hooks/useAuthMutations";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Turnstile } from "@marsidev/react-turnstile";
import { useRateLimitGate } from "@/hooks/useRateLimitGate";

const localResetPasswordSchema = resetPasswordSchema.extend({
  captchaToken: z.string().optional()
});

export default function ResetPassword() {
  const { t } = useTranslation();
  const translateValidation = useCallback((message) => t(message, { defaultValue: message }), [t]);
  const navigate = useNavigate();
  const token = typeof window !== "undefined" ? (new URLSearchParams(window.location.search).get("token") || "") : "";

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [status, setStatus] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [isError, setIsError] = useState(false);

  const resetPasswordMutation = useResetPasswordMutation();
  const isSubmitting = resetPasswordMutation.isPending;
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setStatus("") });

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors }
  } = useForm({
    resolver: zodResolver(localResetPasswordSchema),
    defaultValues: { token, new_password: "", confirm_password: "", captchaToken: "" },
    mode: "onChange"
  });

  const passwordValue = watch("new_password");
  const passwordRules = evaluatePasswordRules(passwordValue || "");
  const passwordChecklist = [
    { id: "minLength", text: t("auth.passwordRuleMinLength"), ok: passwordRules.minLength },
    { id: "hasLowercase", text: t("auth.passwordRuleLowercase"), ok: passwordRules.hasLowercase },
    { id: "hasUppercase", text: t("auth.passwordRuleUppercase"), ok: passwordRules.hasUppercase },
    { id: "hasNumber", text: t("auth.passwordRuleNumber"), ok: passwordRules.hasNumber },
    { id: "hasSpecial", text: t("auth.passwordRuleSpecial"), ok: passwordRules.hasSpecial },
    { id: "noSpaces", text: t("auth.passwordRuleNoSpaces"), ok: passwordRules.noSpaces },
  ];

  const resetInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
  const disabledResetButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";

  const mapResetError = (message) => {
    const msg = String(message || "");
    const normalized = msg.toLowerCase();
    if (normalized === "auth.reset_token_invalid_or_expired" || normalized.includes("invalid or expired reset token")) {
      return t("auth.resetPasswordInvalidToken");
    }
    if (normalized === "auth.reset_password_rate_limited" || normalized.includes("too many password reset attempts")) {
      return t("auth.resetPasswordTooManyAttempts");
    }
    if (msg === "auth.idempotency_conflict_in_progress") {
      return t("auth.idempotencyConflict");
    }
    if (normalized === "auth.password_contains_email_local_part" || normalized.includes("password must not contain the email username part")) {
      return t("auth.validation.password.noEmailLocalPart");
    }
    return t(msg, { defaultValue: msg || t("auth.resetPasswordRequestFailed") });
  };

  async function onSubmit(data) {
    setStatus("");
    if (!token) {
      setStatus(t("auth.resetPasswordMissingToken", "Invalid or missing token"));
      setIsError(true);
      return;
    }

    try {
      const resData = await resetPasswordMutation.mutateAsync({ 
        token, 
        newPassword: data.new_password,
        captchaToken: data.captchaToken
      });
      const message = String(resData?.message || "");
      if (message.toLowerCase().includes("password reset successful") || message.toLowerCase().includes("sign in")) {
        setStatus(t("auth.resetPasswordSuccessRedirect"));
      } else {
        setStatus(message || t("auth.resetPasswordSuccessRedirect"));
      }
      setIsSuccess(true);
      setTimeout(() => navigate("/sign-in", { replace: true }), 3000);
    } catch (err) {
      onRateLimitError(err);
      setStatus(mapResetError(err.message));
      setIsError(true);
    }
  }

  if (isSuccess) {
    return (
      <AuthFormCard>
        <div className="flex flex-col items-center justify-center space-y-4 py-4">
          <div className="rounded-full bg-emerald-100 p-3 dark:bg-emerald-500/20">
            <CheckCircle2 className="h-12 w-12 text-emerald-600 dark:text-emerald-400" />
          </div>
          <h2 className="text-xl font-semibold">{t("common.success")}</h2>
          <p className="text-center text-sm text-muted-foreground px-2">
            {status}
          </p>
          <div className="pt-4 w-full">
            <Button className="h-11 w-full" onClick={() => navigate("/sign-in", { replace: true })}>
              {t("auth.continueToSignIn") || "Continue to Sign In"}
            </Button>
          </div>
        </div>
      </AuthFormCard>
    );
  }

  if (isError) {
    return (
      <AuthFormCard>
        <div className="flex flex-col items-center justify-center space-y-4 py-4">
          <div className="rounded-full bg-red-100 p-3 dark:bg-red-500/20">
            <XCircle className="h-12 w-12 text-red-600 dark:text-red-400" />
          </div>
          <h2 className="text-xl font-semibold">{t("auth.verifyEmailErrorTitle", "Link Expired or Invalid")}</h2>
          <p className="text-center text-sm text-muted-foreground px-2">
            {status}
          </p>
          <div className="pt-4 w-full">
            <Button className="h-11 w-full" onClick={() => navigate("/forgot-password", { replace: true })}>
              {t("auth.requestNewResetLink") || "Request new reset link"}
            </Button>
          </div>
        </div>
      </AuthFormCard>
    );
  }

  return (
    <AuthFormCard
      title={t("auth.resetPasswordTitle")}
      description={t("auth.resetPasswordDescription")}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-2">
        <div className="space-y-0.5">
          <div className="relative">
            <Input
              id="new_password"
              type={showPassword ? "text" : "password"}
              className={`${resetInputClass} pr-10 ${errors.new_password ? "border-red-500 focus-visible:border-red-500" : ""}`}
              placeholder={t("auth.newPassword")}
              {...register("new_password")}
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
            {errors.new_password && (
              <p className="text-xs text-red-500">{translateValidation(errors.new_password.message)}</p>
            )}
          </div>
          <ul className="space-y-1 pt-0.5">
            {passwordChecklist.map((rule) => (
              <li
                key={rule.id}
                className={`flex items-center gap-1.5 text-xs ${rule.ok ? "text-emerald-600" : "text-muted-foreground"}`}
              >
                {rule.ok ? (
                  <Check className="h-3 w-3 shrink-0" strokeWidth={2.25} />
                ) : (
                  <Circle className="h-3 w-3 shrink-0" strokeWidth={2.25} />
                )}
                <span>{rule.text}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-0.5">
          <div className="relative">
            <Input
              id="confirm_password"
              type={showConfirmPassword ? "text" : "password"}
              className={`${resetInputClass} pr-10 ${errors.confirm_password ? "border-red-500 focus-visible:border-red-500" : ""}`}
              placeholder={t("auth.confirmNewPassword")}
              {...register("confirm_password")}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword((v) => !v)}
              className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <div className="min-h-2.5">
            {errors.confirm_password && (
              <p className="text-xs text-red-500">{translateValidation(errors.confirm_password.message)}</p>
            )}
          </div>
        </div>

        <div className="flex justify-center min-h-[65px]">
          <Turnstile
            siteKey={import.meta.env.VITE_TURNSTILE_SITE_KEY || "1x00000000000000000000AA"}
            onSuccess={(token) => setValue("captchaToken", token)}
            onError={() => setValue("captchaToken", "")}
            onExpire={() => setValue("captchaToken", "")}
          />
        </div>

        <Button
          type="submit"
          className={`h-11 w-full ${disabledResetButtonCursorClass}`}
          disabled={isSubmitting || isRateLimited || !!errors.new_password || !!errors.confirm_password}
        >
          {isSubmitting ? (
            <span
              aria-label="Loading"
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
            />
          ) : (
            t("auth.savePassword")
          )}
        </Button>

        <div className="min-h-3">
          {!!status && !isSuccess && (
            <p className="text-xs text-center text-red-500">
              {status}
            </p>
          )}
        </div>
      </form>

      <div className="mt-1.5 text-center text-sm text-muted-foreground">
        <Link to="/forgot-password" className="underline font-medium text-foreground hover:text-foreground/80">
          {t("auth.requestNewResetLink")}
        </Link>
      </div>
    </AuthFormCard>
  );
}
