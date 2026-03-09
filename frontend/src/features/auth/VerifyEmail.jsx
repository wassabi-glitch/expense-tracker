import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle2, Loader2, Mail, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useVerifyEmailMutation } from "./hooks/useAuthMutations";

export default function VerifyEmail() {
  const { t } = useTranslation();
  const token = useMemo(() => {
    if (typeof window === "undefined") return "";
    const params = new URLSearchParams(window.location.search);
    return params.get("token") || "";
  }, []);

  const [verifyStatus, setVerifyStatus] = useState("");
  const [verifyError, setVerifyError] = useState("");
  const didAutoVerifyRef = useRef(false);
  const disabledVerifyButtonCursorClass = "disabled:pointer-events-auto disabled:cursor-not-allowed";
  const verifyMutation = useVerifyEmailMutation();
  const isVerifying = verifyMutation.isPending;

  const mapVerifyError = (message) => {
    const msg = String(message || "");
    const normalized = msg.toLowerCase();
    if (normalized === "auth.verify_email_token_invalid_or_expired") {
      return t("auth.verifyEmailInvalidToken");
    }
    if (normalized.includes("invalid") && normalized.includes("expired")) {
      return t("auth.verifyEmailInvalidToken");
    }
    return t(msg, { defaultValue: msg || t("auth.verifyEmailFailed") });
  };

  async function handleVerify() {
    setVerifyStatus("");
    setVerifyError("");
    if (!token) {
      setVerifyError(t("auth.verifyEmailMissingToken"));
      return;
    }
    try {
      const data = await verifyMutation.mutateAsync(token);
      const message = String(data?.message || "");
      if (message.toLowerCase().includes("verified")) {
        setVerifyStatus(t("auth.verifyEmailSuccess"));
      } else {
        setVerifyStatus(message || t("auth.verifyEmailSuccess"));
      }
    } catch (err) {
      setVerifyError(mapVerifyError(err.message));
    }
  }

  useEffect(() => {
    if (token && !didAutoVerifyRef.current) {
      didAutoVerifyRef.current = true;
      handleVerify();
    }
    // Intentionally one-time per URL token in dev StrictMode too.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const state = isVerifying ? "loading" : verifyStatus ? "success" : verifyError ? "error" : "idle";
  const title =
    state === "success"
      ? t("auth.verifyEmailSuccessTitle")
      : state === "error"
        ? t("auth.verifyEmailErrorTitle")
        : state === "loading"
          ? t("auth.verifyingEmail")
          : t("auth.verifyEmailTitle");
  const description =
    state === "success"
      ? t("auth.verifyEmailSuccess")
      : state === "error"
        ? verifyError
        : state === "loading"
          ? t("auth.verifyEmailChecking")
          : t("auth.verifyEmailDescription");

  return (
    <div className="relative flex min-h-screen w-full items-start sm:items-center justify-center bg-white px-4 pt-12 pb-8 sm:pt-16 sm:pb-10">
      <Card className="w-full max-w-xl border-0 bg-transparent p-0 shadow-none">
        <div className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="mb-6 h-5" />

          <div className="mb-6 text-center">
            <div
              className={
                state === "success"
                  ? "mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-500 ring-1 ring-emerald-500/20"
                  : state === "error"
                    ? "mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10 text-red-500 ring-1 ring-red-500/20"
                    : "mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-zinc-500/10 text-zinc-400 ring-1 ring-zinc-500/20"
              }
            >
              {state === "success" ? (
                <CheckCircle2 className="h-9 w-9" />
              ) : state === "error" ? (
                <XCircle className="h-9 w-9" />
              ) : state === "loading" ? (
                <Loader2 className="h-8 w-8 animate-spin" />
              ) : (
                <Mail className="h-8 w-8" />
              )}
            </div>

            <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
            {state !== "success" && state !== "error" && (
              <p className="mt-2 text-sm text-muted-foreground">{description}</p>
            )}
          </div>

          <div className="space-y-2">
            {(state === "success" || state === "error") && (
              <div
                className={
                  state === "success"
                    ? "rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-3 text-left"
                    : "rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-left"
                }
              >
                <div className="flex items-start gap-2.5">
                  {state === "success" ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
                  ) : (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" aria-hidden="true" />
                  )}
                  <p
                    className={
                      state === "success"
                        ? "text-sm font-medium text-emerald-800"
                        : "text-sm font-medium text-red-800"
                    }
                  >
                    {description}
                  </p>
                </div>
              </div>
            )}

            {state !== "success" && (
              <Button
                onClick={handleVerify}
                type="button"
                className={`h-11 w-full ${disabledVerifyButtonCursorClass}`}
                disabled={isVerifying}
              >
                {isVerifying ? (
                  <span
                    aria-label="Loading"
                    className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                  />
                ) : (
                  t("auth.verifyEmailAction")
                )}
              </Button>
            )}

            {state === "error" && (
              <Button asChild variant="outline" className="h-11 w-full">
                <Link to="/resend-verification">{t("auth.resendVerificationAction")}</Link>
              </Button>
            )}

            {state === "success" && (
              <Button asChild className="h-11 w-full">
                <Link to="/sign-in">{t("auth.backToSignIn")}</Link>
              </Button>
            )}

            <div className="min-h-3" />
            {state !== "success" && (
              <p className="text-sm text-center text-muted-foreground">
                <Link
                  to="/sign-in"
                  className="underline font-medium text-foreground hover:text-foreground/80"
                >
                  {t("auth.backToSignIn")}
                </Link>
              </p>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
