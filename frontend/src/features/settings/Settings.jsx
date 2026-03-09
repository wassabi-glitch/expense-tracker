import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import { useLogoutMutation, useTogglePremiumMutation } from "./hooks/useSettingsMutations";

const CURRENCY_KEY = "settings.currency";
const DATE_FORMAT_KEY = "settings.date_format";

function getStoredPreference(key, fallback) {
  const value = localStorage.getItem(key);
  return value || fallback;
}

export default function Settings() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const savedCurrency = useMemo(() => getStoredPreference(CURRENCY_KEY, "UZS"), []);
  const savedDateFormat = useMemo(() => getStoredPreference(DATE_FORMAT_KEY, "YYYY-MM-DD"), []);

  const [logoutOpen, setLogoutOpen] = useState(false);
  const userQuery = useSettingsDataQuery();
  const logoutMutation = useLogoutMutation();
  const togglePremiumMutation = useTogglePremiumMutation();
  const isTogglingPremium = togglePremiumMutation.isPending;
  const username = userQuery.data?.username || "";
  const email = userQuery.data?.email || "";
  const isPremium = !!userQuery.data?.is_premium;
  const profileError = userQuery.error
    ? localizeApiError(userQuery.error?.message, t) || userQuery.error?.message || t("settings.failedProfile")
    : "";
  const displayError = error || profileError;

  const handleLogout = async () => {
    await logoutMutation.mutateAsync();
    navigate("/sign-in", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-8 space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{t("settings.title")}</h1>
          <p className="text-muted-foreground">{t("settings.subtitle")}</p>
        </div>

        {displayError && <p className="text-sm text-red-600">{displayError}</p>}

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

        {/* DEV ONLY PANEL */}
        <Card className="shadow-sm border-dashed border-primary">
          <CardHeader>
            <CardTitle>Developer Tools</CardTitle>
            <CardDescription>Temporary settings strictly for testing features locally</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
              <div>
                <h4 className="font-medium">Premium Status View</h4>
                <p className="text-sm text-muted-foreground">Force toggle `is_premium` to unlock or lock Recurring Expenses</p>
              </div>
              <Button
                variant={isPremium ? "default" : "secondary"}
                disabled={isTogglingPremium}
                onClick={async () => {
                  setError("");
                  try {
                    await togglePremiumMutation.mutateAsync();
                  } catch (e) {
                    setError(localizeApiError(e?.message, t) || `Failed to toggle premium: ${e?.message || ""}`.trim());
                  }
                }}
              >
                {isPremium ? "Premium Active (Click to Disable)" : "Free User (Click to Enable)"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>{t("settings.session")}</CardTitle>
            <CardDescription>{t("settings.sessionDesc")}</CardDescription>
          </CardHeader>
          <CardContent>
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
    </div>
  );
}
