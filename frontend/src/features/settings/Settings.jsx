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
import { useLogoutMutation } from "./hooks/useSettingsMutations";

const CURRENCY_KEY = "settings.currency";
const DATE_FORMAT_KEY = "settings.date_format";

function getStoredPreference(key, fallback) {
  const value = localStorage.getItem(key);
  return value || fallback;
}

export default function Settings() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [sessionError, setSessionError] = useState("");

  const savedCurrency = useMemo(() => getStoredPreference(CURRENCY_KEY, "UZS"), []);
  const savedDateFormat = useMemo(() => getStoredPreference(DATE_FORMAT_KEY, "YYYY-MM-DD"), []);

  const [logoutOpen, setLogoutOpen] = useState(false);
  const userQuery = useSettingsDataQuery();
  const logoutMutation = useLogoutMutation();
  const username = userQuery.data?.username || "";
  const email = userQuery.data?.email || "";
  const isPremium = !!userQuery.data?.is_premium;
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
      <div className="w-full px-page py-8 space-y-8">
        <div className="pl-card sm:pl-0 sm:px-3 md:px-0">
          <h1 className="text-mobile-h1 sm:text-3xl font-bold tracking-tight text-foreground">{t("settings.title")}</h1>
          <p className="text-mobile-label sm:text-base text-muted-foreground mt-0.5 sm:mt-1">{t("settings.subtitle")}</p>
        </div>

        {profileError && <p className="text-sm text-red-600">{profileError}</p>}

        <Card className="shadow-sm card-mobile">
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

        <Card className="shadow-sm card-mobile">
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

        <Card className="shadow-sm card-mobile">
          <CardHeader>
            <CardTitle>{t("settings.preferences")}</CardTitle>
            <CardDescription>{t("settings.preferencesDesc")}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Input value={savedCurrency === "UZS" ? "UZS - so'm" : savedCurrency} readOnly disabled />
            <Input value={savedDateFormat} readOnly disabled />
          </CardContent>
        </Card>

        <Card className="shadow-sm card-mobile">
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

        <Card className="shadow-sm card-mobile">
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


