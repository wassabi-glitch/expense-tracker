import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { isLoggedIn } from "@/lib/api";

export default function NotFound() {
  const { t } = useTranslation();
  const authed = isLoggedIn();
  const target = authed ? "/dashboard" : "/sign-in";
  const label = authed ? t("notFound.backToDashboard") : t("notFound.goToSignIn");

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-4 text-center">
        <p className="text-sm font-medium text-muted-foreground">404</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">{t("notFound.title")}</h1>
        <p className="mt-3 text-muted-foreground">
          {t("notFound.description")}
        </p>
        <Button asChild className="mt-6">
          <Link to={target}>{label}</Link>
        </Button>
      </div>
    </div>
  );
}
