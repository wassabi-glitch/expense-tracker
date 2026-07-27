import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { signinSchema } from "./authSchemas.js";
import { AuthFormCard } from "@/components/AuthFormCard";
import { useForgotPasswordMutation } from "./hooks/useAuthMutations";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRateLimitGate } from "@/hooks/useRateLimitGate";

import { Turnstile } from "@marsidev/react-turnstile";

const forgotSchema = z.object({
  email: signinSchema.shape.email,
  captchaToken: z.string().optional()
});

export default function ForgotPassword() {
  const { t } = useTranslation();
  const translateValidation = useCallback((message) => t(message, { defaultValue: message }), [t]);
  
  const [status, setStatus] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const forgotPasswordMutation = useForgotPasswordMutation();
  const isSubmitting = forgotPasswordMutation.isPending;
  const { isRateLimited, onRateLimitError } = useRateLimitGate({ onExpire: () => setStatus("") });

  const initialEmail = typeof window !== "undefined" ? (new URLSearchParams(window.location.search).get("email") || "") : "";

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    formState: { errors }
  } = useForm({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: initialEmail, captchaToken: "" },
    mode: "onChange"
  });

  const forgotInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
  const disabledForgotButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";

  const mapForgotError = (message) => {
    const msg = String(message || "");
    const normalized = msg.toLowerCase();
    if (normalized === "auth.forgot_password_rate_limited" || normalized.includes("too many password reset requests")) {
      return t("auth.forgotPasswordTooManyRequests");
    }
    if (msg === "auth.idempotency_conflict_in_progress") {
      return t("auth.idempotencyConflict");
    }
    return t(msg, { defaultValue: msg || t("auth.forgotPasswordRequestFailed") });
  };

  async function onSubmit(data) {
    setStatus("");
    try {
      const resData = await forgotPasswordMutation.mutateAsync({
        email: data.email,
        captchaToken: data.captchaToken,
      });
      const message = String(resData?.message || "");
      if (
        message.toLowerCase().includes("if the account exists") ||
        message.toLowerCase().includes("check your email inbox")
      ) {
        setStatus(t("auth.forgotPasswordSuccess"));
      } else {
        setStatus(message || t("auth.forgotPasswordSuccess"));
      }
      setIsSuccess(true);
    } catch (err) {
      onRateLimitError(err);
      setStatus(mapForgotError(err.message));
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
            <Button variant="secondary" className="h-11 w-full" asChild>
              <Link to="/sign-in">{t("auth.backToSignIn")}</Link>
            </Button>
          </div>
        </div>
      </AuthFormCard>
    );
  }

  return (
    <AuthFormCard
      title={t("auth.forgotPasswordTitle")}
      description={t("auth.forgotPasswordDescription")}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-2">
        <div className="space-y-0.5">
          <Input
            id="email"
            type="email"
            placeholder={t("auth.email")}
            className={`${forgotInputClass} ${errors.email ? "border-red-500 focus-visible:border-red-500" : ""}`}
            {...register("email")}
          />
          <div className="min-h-2.5">
            {errors.email && (
              <p className="text-xs text-red-500">{translateValidation(errors.email.message)}</p>
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
          className={`h-11 w-full ${disabledForgotButtonCursorClass}`}
          disabled={isSubmitting || isRateLimited || !!errors.email}
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
          {!!status && !isSuccess && (
            <p className="text-xs text-center text-red-500">
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
