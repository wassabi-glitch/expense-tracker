import { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useTranslation } from "react-i18next";
import { Loader2, Eye, EyeOff } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useChangePasswordMutation } from "../hooks/useSettingsMutations";
import { localizeApiError } from "@/lib/errorMessages";
import { useRateLimitGate } from "@/hooks/useRateLimitGate";

const getPasswordSchema = (t) => z.object({
  currentPassword: z.string().min(1, { message: t("auth.validation.required") }),
  newPassword: z.string()
    .min(8, { message: t("auth.validation.password.min") })
    .max(64, { message: t("auth.validation.password.max") })
    .regex(/[a-z]/, { message: t("auth.validation.password.lowercase") })
    .regex(/[A-Z]/, { message: t("auth.validation.password.uppercase") })
    .regex(/\d/, { message: t("auth.validation.password.number") })
    .regex(/[^\w\s]/, { message: t("auth.validation.password.special") }),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: t("auth.validation.password.mismatch"),
  path: ["confirmPassword"],
}).refine((data) => data.newPassword !== data.currentPassword, {
  message: t("auth.validation.password.must_differ"),
  path: ["newPassword"],
});

export function ChangePasswordForm() {
  const { t } = useTranslation();
  const translateValidation = useCallback((message) => t(message, { defaultValue: message }), [t]);
  const [successMessage, setSuccessMessage] = useState("");
  const changePasswordMutation = useChangePasswordMutation();
  
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    clearErrors,
    reset,
    formState: { errors }
  } = useForm({
    resolver: zodResolver(getPasswordSchema(t)),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
    mode: "onChange"
  });

  const isSubmitting = changePasswordMutation.isPending;

  const { isRateLimited, onRateLimitError } = useRateLimitGate({
    onExpire: () => clearErrors("root"),
  });

  const inputClass = "h-11 focus-visible:ring-0 focus-visible:ring-offset-0 focus-visible:border-emerald-500 pr-10";

  const onSubmit = async (data) => {
    setSuccessMessage("");
    try {
      await changePasswordMutation.mutateAsync({
        current_password: data.currentPassword,
        new_password: data.newPassword,
      });
      setSuccessMessage(t("settings.changePasswordSuccess"));
      reset();
    } catch (error) {
      onRateLimitError(error);
      const message = localizeApiError(error.message, t) || error.message || t("common.errorOccurred");
      setError("root", { type: "server", message });
    }
  };

  return (
    <Card className="shadow-sm card-mobile">
      <CardHeader>
        <CardTitle>{t("settings.changePassword")}</CardTitle>
        <CardDescription>{t("settings.changePasswordDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-md">
          {errors.root && (
            <p className="text-sm font-medium text-red-500">
              {errors.root.message}
            </p>
          )}
          
          {successMessage && (
            <p className="text-sm font-medium text-green-600 dark:text-green-400">
              {successMessage}
            </p>
          )}

          <div className="space-y-1">
            <label htmlFor="currentPassword" className="text-sm font-medium">{t("settings.currentPassword")}</label>
            <div className="relative">
              <Input
                id="currentPassword"
                type={showCurrent ? "text" : "password"}
                placeholder="••••••••"
                className={`${inputClass} ${errors.currentPassword ? "border-red-500 focus-visible:border-red-500" : ""}`}
                {...register("currentPassword")}
              />
              <button
                type="button"
                onClick={() => setShowCurrent((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
              >
                {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.currentPassword && (
              <p className="text-xs text-red-500">
                {translateValidation(errors.currentPassword.message)}
              </p>
            )}
          </div>

          <div className="space-y-1">
            <label htmlFor="newPassword" className="text-sm font-medium">{t("settings.newPassword")}</label>
            <div className="relative">
              <Input
                id="newPassword"
                type={showNew ? "text" : "password"}
                placeholder="••••••••"
                className={`${inputClass} ${errors.newPassword ? "border-red-500 focus-visible:border-red-500" : ""}`}
                {...register("newPassword")}
              />
              <button
                type="button"
                onClick={() => setShowNew((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
              >
                {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.newPassword && (
              <p className="text-xs text-red-500">
                {translateValidation(errors.newPassword.message)}
              </p>
            )}
          </div>

          <div className="space-y-1">
            <label htmlFor="confirmPassword" className="text-sm font-medium">{t("settings.confirmNewPassword")}</label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirm ? "text" : "password"}
                placeholder="••••••••"
                className={`${inputClass} ${errors.confirmPassword ? "border-red-500 focus-visible:border-red-500" : ""}`}
                {...register("confirmPassword")}
              />
              <button
                type="button"
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground"
              >
                {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.confirmPassword && (
              <p className="text-xs text-red-500">
                {translateValidation(errors.confirmPassword.message)}
              </p>
            )}
          </div>

          <div className="pt-2">
            <Button 
              type="submit" 
              className="h-11 w-full sm:w-auto min-w-[150px]"
              disabled={isSubmitting || isRateLimited || !!errors.currentPassword || !!errors.newPassword || !!errors.confirmPassword}
            >
              {isSubmitting && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t("settings.updatePassword")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
