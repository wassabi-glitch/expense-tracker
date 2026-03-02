import React from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./components/ui/dialog";
import {
  LayoutDashboard,
  Receipt,
  PiggyBank,
  LineChart,
  Download,
  Settings,
  Menu,
  CreditCard,
  LogOut,
  User,
  Sun,
  Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getCurrentUser, logout } from "./api";
import { APP_LANGUAGE_KEY } from "./i18n";
import { LanguageSelect } from "./components/ui/language-select";

const mainNavItems = [
  { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
  { to: "/expenses", labelKey: "nav.expenses", icon: Receipt },
  { to: "/budgets", labelKey: "nav.budgets", icon: PiggyBank },
  { to: "/analytics", labelKey: "nav.analytics", icon: LineChart },
];

const secondaryNavItems = [
  { to: "/export", labelKey: "nav.exportData", icon: Download },
  { to: "/settings", labelKey: "nav.settings", icon: Settings },
];

function useDarkMode() {
  const [isDark, setIsDark] = React.useState(() => {
    if (typeof window === "undefined") return false;
    const stored = localStorage.getItem("theme");
    if (stored === "dark") return true;
    if (stored === "light") return false;
    return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ?? false;
  });

  React.useEffect(() => {
    document.documentElement.classList.add("theme-switching");
    document.documentElement.classList.toggle("dark", isDark);
    localStorage.setItem("theme", isDark ? "dark" : "light");

    const id = window.setTimeout(() => {
      document.documentElement.classList.remove("theme-switching");
    }, 80);

    return () => {
      window.clearTimeout(id);
      document.documentElement.classList.remove("theme-switching");
    };
  }, [isDark]);

  return { isDark, toggle: () => setIsDark((v) => !v) };
}

function NavList({ onNavigate, compact = false }) {
  const { t } = useTranslation();

  const rowBase =
    "group relative rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-muted/70 hover:text-foreground";
  const rowLayout = "grid grid-cols-[40px_minmax(0,1fr)] items-center";
  const iconWrap = "h-9 w-10 grid place-items-center";
  const labelReveal =
    "block min-w-0 max-w-0 overflow-hidden whitespace-nowrap opacity-0 transition-[max-width,opacity] duration-200 group-hover/sidebar:max-w-[180px] group-hover/sidebar:opacity-100";

  // IMPORTANT: section headers reserve height always so nothing shifts in Y.
  // We only fade them out when compact (collapsed).
  const sectionHeaderBase =
    "mb-2 pl-6 pr-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground h-6 flex items-center";
  const sectionHeaderCompact =
    "max-w-0 overflow-hidden whitespace-nowrap opacity-0 transition-[max-width,opacity] duration-200 group-hover/sidebar:max-w-[180px] group-hover/sidebar:opacity-100";

  return (
    <div className="flex flex-col gap-6 py-6">
      <div>
        <div className={cn(sectionHeaderBase, compact && sectionHeaderCompact)}>
          {t("nav.platform")}
        </div>

        <div className="space-y-1">
          {mainNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  rowBase,
                  rowLayout,
                  isActive
                    ? "bg-muted/40 text-foreground ring-0 before:absolute before:left-1 before:top-2 before:bottom-2 before:w-0.5 before:rounded-full before:bg-primary"
                    : "text-muted-foreground"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span className={iconWrap}>
                    <item.icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground group-hover:text-foreground"
                      )}
                    />
                  </span>

                  <span className={cn(compact && labelReveal)}>
                    {t(item.labelKey)}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>

      <div>
        <div className={cn(sectionHeaderBase, compact && sectionHeaderCompact)}>
          {t("nav.tools")}
        </div>

        <div className="space-y-1">
          {secondaryNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  rowBase,
                  rowLayout,
                  isActive
                    ? "bg-muted/40 text-foreground ring-0 before:absolute before:left-1 before:top-2 before:bottom-2 before:w-0.5 before:rounded-full before:bg-primary"
                    : "text-muted-foreground"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span className={iconWrap}>
                    <item.icon
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground group-hover:text-foreground"
                      )}
                    />
                  </span>

                  <span className={cn(compact && labelReveal)}>
                    {t(item.labelKey)}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Layout() {
  const { t, i18n } = useTranslation();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [logoutOpen, setLogoutOpen] = React.useState(false);
  const [username, setUsername] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [language, setLanguage] = React.useState(() => {
    const raw = String(i18n.resolvedLanguage || "uz").toLowerCase();
    if (raw.startsWith("ru")) return "ru";
    if (raw.startsWith("en")) return "en";
    return "uz";
  });
  const { isDark, toggle } = useDarkMode();
  const navigate = useNavigate();

  React.useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        const user = await getCurrentUser();
        setUsername(user?.username || "");
        setEmail(user?.email || "");
      } catch {
        setUsername("");
        setEmail("");
      }
    };
    loadCurrentUser();
  }, []);

  const handleLogout = () => {
    setLogoutOpen(false);
    logout();
    // Defensive cleanup in case a dialog lock survives a route transition.
    document.body.style.pointerEvents = "";
    document.body.style.overflow = "";
    document.body.style.paddingRight = "";
    document.body.removeAttribute("data-scroll-locked");
    navigate("/sign-in", { replace: true });
  };

  const handleLanguageChange = async (nextLang) => {
    setLanguage(nextLang);
    await i18n.changeLanguage(nextLang);
    localStorage.setItem(APP_LANGUAGE_KEY, nextLang);
  };

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background">
      <header className="sticky top-0 z-50 flex h-16 items-center justify-between border-b bg-background/90 px-4 backdrop-blur lg:px-6">
        <div className="flex items-center gap-3">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden -ml-2 text-muted-foreground"
                aria-label={t("nav.openNavigation")}
              >
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>

            <SheetContent side="left" className="w-64 pt-10">
              <NavList onNavigate={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>

          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <CreditCard className="h-4 w-4" />
            </div>
            <span className="font-semibold tracking-tight">{t("appName")}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <LanguageSelect
            ariaLabel={t("common.language")}
            value={language}
            onChange={handleLanguageChange}
            buttonClassName="min-w-[74px]"
          />

          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            className="rounded-xl"
            aria-label={isDark ? t("nav.switchToLight") : t("nav.switchToDark")}
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>

          <div className="hidden text-right md:block">
            <p className="text-sm font-medium leading-none">
              {username || t("common.user")}
            </p>
            <p className="text-xs text-muted-foreground">
              {email || t("common.signedIn")}
            </p>
          </div>

          <div className="flex h-9 w-9 items-center justify-center rounded-full border bg-muted text-muted-foreground">
            <User className="h-5 w-5" />
          </div>
        </div>
      </header>

      <div className="relative flex flex-1 overflow-hidden">
        <aside className="group/sidebar relative hidden w-16 border-r bg-background lg:block">
          <div className="absolute inset-y-0 left-0 z-20 w-16 overflow-hidden border-r bg-background/90 shadow-none transition-[width,box-shadow,backdrop-filter,background-color] duration-200 group-hover/sidebar:w-64 group-hover/sidebar:bg-background/75 group-hover/sidebar:backdrop-blur-xl group-hover/sidebar:shadow-lg dark:bg-background/80 dark:group-hover/sidebar:bg-background/60">
            <div className="flex h-full flex-col">
              <div className="flex-1 overflow-y-auto overflow-x-hidden">
                <NavList compact />
              </div>

              <div className="border-t py-3">
                <button
                  type="button"
                  onClick={() => setLogoutOpen(true)}
                  className="w-full grid grid-cols-[40px_minmax(0,1fr)] items-center rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                >
                  <span className="h-9 w-10 grid place-items-center">
                    <LogOut className="h-4 w-4 shrink-0" />
                  </span>

                  <span className="block min-w-0 max-w-0 overflow-hidden whitespace-nowrap text-left opacity-0 transition-[max-width,opacity] duration-200 group-hover/sidebar:max-w-[180px] group-hover/sidebar:opacity-100">
                    {t("common.signOut")}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </aside>
        <main className="flex-1 overflow-y-auto px-4 pt-2 pb-4 lg:px-6 lg:pt-3 lg:pb-6">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
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


