import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, Circle, Eye, EyeOff } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Card } from "./components/ui/card";
import { resetPassword } from "./api";
import { evaluatePasswordRules, resetPasswordSchema } from "./auth/authSchemas.js";

export default function ResetPassword() {
  const { t } = useTranslation();
  const translateValidation = (message) => t(message, { defaultValue: message });
  const navigate = useNavigate();
  const token = useMemo(() => {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search);
    return params.get("token") || "";
  }, []);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const resetInputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500";
  const disabledResetButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";
  const resetParsed = useMemo(
    () =>
      resetPasswordSchema.safeParse({
        token,
        new_password: password,
        confirm_password: confirmPassword,
      }),
    [token, password, confirmPassword]
  );
  const canSubmit = resetParsed.success && !isSubmitting && !status;
  const mapResetError = (message) => {
    const msg = String(message || "");
    const normalized = msg.toLowerCase();
    if (normalized === "auth.reset_token_invalid_or_expired") {
      return t("auth.resetPasswordInvalidToken");
    }
    if (normalized === "auth.reset_password_rate_limited") {
      return t("auth.resetPasswordTooManyAttempts");
    }
    if (normalized === "auth.password_contains_email_local_part") {
      return t("auth.validation.password.noEmailLocalPart");
    }
    if (normalized.includes("invalid or expired reset token")) {
      return t("auth.resetPasswordInvalidToken");
    }
    if (normalized.includes("too many password reset attempts")) {
      return t("auth.resetPasswordTooManyAttempts");
    }
    if (normalized.includes("password must not contain the email username part")) {
      return t("auth.validation.password.noEmailLocalPart");
    }
    return t(msg, { defaultValue: msg || t("auth.resetPasswordRequestFailed") });
  };
  const passwordRules = evaluatePasswordRules(password);
  const passwordChecklist = [
    { id: "minLength", text: t("auth.passwordRuleMinLength"), ok: passwordRules.minLength },
    { id: "hasLowercase", text: t("auth.passwordRuleLowercase"), ok: passwordRules.hasLowercase },
    { id: "hasUppercase", text: t("auth.passwordRuleUppercase"), ok: passwordRules.hasUppercase },
    { id: "hasNumber", text: t("auth.passwordRuleNumber"), ok: passwordRules.hasNumber },
    { id: "hasSpecial", text: t("auth.passwordRuleSpecial"), ok: passwordRules.hasSpecial },
    { id: "noSpaces", text: t("auth.passwordRuleNoSpaces"), ok: passwordRules.noSpaces },
  ];

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setStatus("");
    setFieldErrors({});

    if (!token) {
      setError(t("auth.resetPasswordMissingToken"));
      return;
    }

    const parsed = resetPasswordSchema.safeParse({
      token,
      new_password: password,
      confirm_password: confirmPassword,
    });
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
      const data = await resetPassword(token, password);
      const message = String(data?.message || "");
      if (message.toLowerCase().includes("password reset successful") || message.toLowerCase().includes("sign in")) {
        setStatus(t("auth.resetPasswordSuccessRedirect"));
      } else {
        setStatus(message || t("auth.resetPasswordSuccessRedirect"));
      }
      setTimeout(() => navigate("/sign-in", { replace: true }), 3000);
    } catch (err) {
      setError(mapResetError(err.message));
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
      <Card className="w-full max-w-md border-0 bg-transparent p-0 shadow-none">
        <div className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="mb-6 h-5" />

          <div className="mb-6 text-center">
            <div className="mb-5 flex items-center justify-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-foreground text-background">
                <span className="font-bold font-mono text-sm">/</span>
              </div>
              <span className="text-2xl font-semibold tracking-tight text-foreground">ExpenseTracker</span>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight">{t("auth.resetPasswordTitle")}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {t("auth.resetPasswordDescription")}
            </p>
          </div>

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
                    setError("");
                    setFieldErrors((prev) => ({ ...prev, new_password: "" }));
                  }}
                  className={`${resetInputClass} pr-10`}
                  placeholder={t("auth.newPassword")}
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
                {!!fieldErrors.new_password && (
                  <p className="text-xs text-red-500">{fieldErrors.new_password}</p>
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
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    setStatus("");
                    setError("");
                    setFieldErrors((prev) => ({ ...prev, confirm_password: "" }));
                  }}
                  className={`${resetInputClass} pr-10`}
                  placeholder={t("auth.confirmNewPassword")}
                  required
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
                {!!fieldErrors.confirm_password && (
                  <p className="text-xs text-red-500">{fieldErrors.confirm_password}</p>
                )}
              </div>
            </div>

            <Button
              type="submit"
              className={`h-11 w-full ${disabledResetButtonCursorClass}`}
              disabled={!canSubmit}
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
              {!!status && (
                <p className="text-xs text-center text-emerald-600">
                  {status}
                </p>
              )}
              {!!error && (
                <p className="text-xs text-center text-red-500">
                  {error}
                </p>
              )}
            </div>
          </form>

          <div className="mt-1.5 text-center text-sm text-muted-foreground">
            <Link to="/forgot-password" className="underline font-medium text-foreground hover:text-foreground/80">
              {t("auth.requestNewResetLink")}
            </Link>
          </div>
        </div>
      </Card>
      </div>
    </div>
  );
}
