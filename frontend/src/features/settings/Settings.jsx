import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { localizeApiError } from "@/lib/errorMessages";
import { useSettingsDataQuery } from "./hooks/useSettingsDataQuery";
import {
  useLogoutMutation,
  useUpdateBudgetRolloverPreferenceMutation,
} from "./hooks/useSettingsMutations";

const CURRENCY_KEY = "settings.currency";
const DATE_FORMAT_KEY = "settings.date_format";

function getStoredPreference(key, fallback) {
  const value = localStorage.getItem(key);
  return value || fallback;
}

export default function Settings() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [rolloverError, setRolloverError] = useState("");
  const [sessionError, setSessionError] = useState("");

  const savedCurrency = useMemo(() => getStoredPreference(CURRENCY_KEY, "UZS"), []);
  const savedDateFormat = useMemo(() => getStoredPreference(DATE_FORMAT_KEY, "YYYY-MM-DD"), []);

  const [logoutOpen, setLogoutOpen] = useState(false);
  const userQuery = useSettingsDataQuery();
  const logoutMutation = useLogoutMutation();
  const updateBudgetRolloverPreferenceMutation = useUpdateBudgetRolloverPreferenceMutation();
  const isUpdatingRollover = updateBudgetRolloverPreferenceMutation.isPending;
  const username = userQuery.data?.username || "";
  const email = userQuery.data?.email || "";
  const isPremium = !!userQuery.data?.is_premium;
  const rolloverPreferenceEnabled = userQuery.data?.profile?.budget_rollover_enabled !== false;
  const rolloverEnabled = isPremium && rolloverPreferenceEnabled;
  const profileError = userQuery.error
    ? localizeApiError(userQuery.error?.message, t) || userQuery.error?.message || t("settings.failedProfile")
    : "";

  const handleLogout = async () => {
    setSessionError("");
    try {
      await logoutMutation.mutateAsync();
      navigate("/sign-in", { replace: true });
    } catch (e) {
      setSessionError(
        localizeApiError(e?.message, t) || e?.message || t("settings.signOutFailed"),
      );
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{t("settings.title")}</h1>
          <p className="text-muted-foreground">{t("settings.subtitle")}</p>
        </div>

        {profileError && <p className="text-sm text-red-600">{profileError}</p>}

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("settings.profile")}</CardTitle>
            <CardDescription>{t("settings.profileDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input value={username} placeholder={t("auth.username")} readOnly disabled />
            <Input value={email} placeholder={t("auth.email")} type="email" readOnly disabled />
            <div className="md:col-span-2 flex gap-3">
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90" disabled>
                {t("common.save")}
              </Button>
              <Button variant="outline" disabled>
                {t("common.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("settings.password")}</CardTitle>
            <CardDescription>{t("settings.passwordDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input placeholder={t("settings.currentPassword")} type="password" disabled />
            <Input placeholder={t("settings.newPassword")} type="password" disabled />
            <div className="md:col-span-2">
              <Button variant="outline" disabled>
                {t("settings.updatePassword")}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("settings.preferences")}</CardTitle>
            <CardDescription>{t("settings.preferencesDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input value={savedCurrency === "UZS" ? "UZS - so'm" : savedCurrency} readOnly disabled />
            <Input value={savedDateFormat} readOnly disabled />
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("settings.premiumTitle")}</CardTitle>
            <CardDescription>{isPremium ? t("settings.premiumActiveDesc") : t("settings.premiumDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/premium")}>
              {isPremium ? t("settings.managePremium") : t("settings.viewPlans")}
            </Button>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("settings.budgetRolloverTitle")}</CardTitle>
            <CardDescription>{t("settings.budgetRolloverDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {isPremium ? t("settings.budgetRolloverPremiumHint") : t("settings.budgetRolloverPremiumOnly")}
              </p>
              {rolloverError && <p className="text-sm text-red-600">{rolloverError}</p>}
            </div>

            <div className="flex items-center justify-between gap-3 sm:justify-end">
              <Badge variant={rolloverEnabled ? "default" : "outline"}>
                {rolloverEnabled ? t("settings.budgetRolloverOn") : t("settings.budgetRolloverOff")}
              </Badge>

              <Switch
                checked={rolloverEnabled}
                disabled={!isPremium || isUpdatingRollover}
                onCheckedChange={async (nextValue) => {
                  setRolloverError("");
                  try {
                    await updateBudgetRolloverPreferenceMutation.mutateAsync(nextValue);
                  } catch (e) {
                    setRolloverError(
                      localizeApiError(e?.message, t) ||
                        e?.message ||
                        t("settings.budgetRolloverUpdateFailed"),
                    );
                  }
                }}
                aria-label={t("settings.budgetRolloverTitle")}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("settings.session")}</CardTitle>
            <CardDescription>{t("settings.sessionDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
            {sessionError && <p className="text-sm text-red-600 mb-3">{sessionError}</p>}
            <Button variant="destructive" onClick={() => setLogoutOpen(true)}>
              {t("common.signOut")}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Dialog open={logoutOpen} onOpenChange={setLogoutOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.signOutConfirmTitle")}</DialogTitle>
            <DialogDescription>{t("settings.signOutConfirmDesc")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLogoutOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" onClick={handleLogout}>
              {t("common.signOut")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div >
  );
}
