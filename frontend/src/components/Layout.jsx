import React from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
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
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  LayoutDashboard,
  Sparkles,
  Menu,
  LogOut,
  User,
  Sun,
  Moon,
  HandCoins,
  PanelLeftClose,
  PanelLeftOpen,
  ArrowDownCircle,
} from "lucide-react";
import {
  IoReceiptOutline,
  IoCashOutline,
  IoPieChartOutline,
  IoWalletOutline,
  IoFlagOutline,
  IoBriefcaseOutline,
  IoStatsChartOutline,
  IoDownloadOutline,
  IoSettingsOutline,
} from "react-icons/io5";
import { cn } from "@/lib/utils";
import { getCurrentUser, logout } from "@/lib/api";
import { useSidebarStore } from "@/lib/store";
import { APP_LANGUAGE_KEY } from "@/i18n";
import { LanguageSelect } from "@/components/ui/language-select";
import { NotificationBell } from "@/components/NotificationBell";
import flowLockup from "@/assets/brand/sarflog-flow-lockup.svg";
import flowLockupDark from "@/assets/brand/sarflog-flow-lockup-dark.svg";

const mainNavItems = [
  { to: "/dashboard", labelKey: "nav.dashboard", icon: (props) => <LayoutDashboard {...props} strokeWidth={1.5} /> },
  { to: "/wallets", labelKey: "nav.wallets", icon: IoWalletOutline },
  { to: "/expenses", labelKey: "nav.expenses", icon: IoReceiptOutline },
  { to: "/money-in", labelKey: "nav.income", icon: (props) => <ArrowDownCircle {...props} strokeWidth={1.5} /> },
  { to: "/budgets", labelKey: "nav.budgets", icon: IoPieChartOutline },
  { to: "/savings", labelKey: "nav.savings", icon: IoFlagOutline },
  { to: "/assets", labelKey: "nav.assets", icon: IoBriefcaseOutline },
  { to: "/debts", labelKey: "nav.debts", icon: (props) => <HandCoins {...props} strokeWidth={1.5} /> },
  { to: "/analytics", labelKey: "nav.analytics", icon: (props) => <IoStatsChartOutline {...props} className={cn(props.className, "[&>*]:!stroke-[32px]")} /> },
];

const secondaryNavItems = [
  { to: "/export", labelKey: "nav.exportData", icon: IoDownloadOutline },
  { to: "/premium", labelKey: "nav.premium", icon: (props) => <Sparkles {...props} strokeWidth={1.5} /> },
  { to: "/settings", labelKey: "nav.settings", icon: IoSettingsOutline },
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

function NavList({ onNavigate, compact = false, isPremium = false, isPinned = false, isMobile = false }) {
  const { t } = useTranslation();
  const visibleMainNavItems = mainNavItems.filter((item) => !item.premiumOnly || isPremium);

  const rowBase =
    cn("group relative rounded-lg py-2 text-sm font-medium transition-colors hover:bg-black/5 hover:text-black dark:hover:bg-muted/70 dark:hover:text-foreground", isMobile ? "px-1" : "px-3");
  const rowLayout = "grid grid-cols-[40px_minmax(0,1fr)] items-center";
  const iconWrap = "h-9 w-10 grid place-items-center";
  const labelReveal = cn(
    "block min-w-0 overflow-hidden whitespace-nowrap transition-[max-width,opacity] duration-200",
    isPinned
      ? "max-w-[180px] opacity-100"
      : "max-w-0 opacity-0 group-hover/sidebar:max-w-[180px] group-hover/sidebar:opacity-100"
  );

  return (
    <div className={cn("flex flex-col h-full", isMobile ? "pt-2 pb-6 px-0" : "py-6")}>
      <div className="space-y-1 flex-1">
        {visibleMainNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                rowBase,
                rowLayout,
                isActive
                  ? `bg-black/5 dark:bg-muted/40 text-foreground ring-0 before:absolute ${isMobile ? "before:left-0" : "before:left-1"} before:top-2 before:bottom-2 before:w-0.5 ${isMobile ? "before:rounded-r-full" : "before:rounded-full"} before:bg-primary`
                  : "text-black dark:text-muted-foreground"
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
                        : "text-black dark:text-muted-foreground group-hover:text-black dark:group-hover:text-foreground"
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

      <div className="space-y-1 mt-6">
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
                  ? `bg-black/5 dark:bg-muted/40 text-foreground ring-0 before:absolute ${isMobile ? "before:left-0" : "before:left-1"} before:top-2 before:bottom-2 before:w-0.5 ${isMobile ? "before:rounded-r-full" : "before:rounded-full"} before:bg-primary`
                  : "text-black dark:text-muted-foreground"
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
                        : "text-black dark:text-muted-foreground group-hover:text-black dark:group-hover:text-foreground"
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
  );
}

export default function Layout() {
  const { t, i18n } = useTranslation();
  const { isPinned, togglePin } = useSidebarStore();
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
  const userQuery = useQuery({
    queryKey: ["users", "me"],
    queryFn: getCurrentUser,
  });
  const logoutMutation = useMutation({
    mutationFn: logout,
  });

  React.useEffect(() => {
    if (userQuery.data) {
      setUsername(userQuery.data?.username || "");
      setEmail(userQuery.data?.email || "");
      return;
    }
    if (userQuery.error) {
      setUsername("");
      setEmail("");
    }
  }, [userQuery.data, userQuery.error]);

  const handleLogout = async () => {
    setLogoutOpen(false);
    await logoutMutation.mutateAsync();
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
    <div className="flex h-dvh flex-col overflow-hidden bg-background lg:flex-row">
      {/* Desktop Sidebar */}
      <aside className={cn("group/sidebar relative hidden shrink-0 transition-[width] duration-200 lg:block", isPinned ? "w-64" : "w-16")}>
        <div className={cn(
          "absolute inset-y-0 left-0 z-20 flex h-full flex-col overflow-hidden bg-background/95 shadow-none transition-[width,box-shadow,backdrop-filter,background-color] duration-200",
          isPinned
            ? "w-64"
            : "w-16 group-hover/sidebar:w-64 group-hover/sidebar:bg-background/80 group-hover/sidebar:backdrop-blur-xl group-hover/sidebar:shadow-xl dark:bg-background/80 dark:group-hover/sidebar:bg-background/60"
        )}>
          {/* Logo Section (CSS Native) */}
          <div className="flex h-16 shrink-0 items-center px-4 lg:h-auto lg:pt-8 lg:pb-6">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
                S
              </div>
              <span className={cn(
                "whitespace-nowrap text-xl font-bold tracking-tight transition-[max-width,opacity] duration-200",
                isPinned ? "max-w-[180px] opacity-100" : "max-w-0 opacity-0 group-hover/sidebar:max-w-[180px] group-hover/sidebar:opacity-100"
              )}>
                Sarflog
              </span>
            </div>
          </div>

          <div className="flex-1 flex flex-col overflow-y-auto overflow-x-hidden [&::-webkit-scrollbar]:hidden [scrollbar-width:none] [-ms-overflow-style:none] pb-4">
            <NavList compact isPremium={!!userQuery.data?.is_premium} isPinned={isPinned} />
          </div>

          {/* Bottom Sidebar Utilities */}
          <div className="mt-auto flex flex-col py-2 px-2">
            <div className={cn(
              "flex gap-1 transition-all duration-200",
              isPinned ? "flex-row justify-between items-center" : "flex-col items-center group-hover/sidebar:flex-row group-hover/sidebar:justify-between"
            )}>
              <div className={cn(
                "flex items-center gap-1 transition-[flex-direction] duration-200",
                isPinned ? "flex-row order-last" : "flex-col order-first group-hover/sidebar:flex-row group-hover/sidebar:order-last"
              )}>
                <NotificationBell />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggle}
                  className="rounded-xl h-9 w-9 shrink-0"
                  aria-label={isDark ? t("nav.switchToLight") : t("nav.switchToDark")}
                >
                  {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
                </Button>
              </div>

              <button
                type="button"
                onClick={togglePin}
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-all active:scale-95 hover:bg-muted/70 hover:text-foreground shrink-0",
                  isPinned ? "order-first" : "order-last group-hover/sidebar:order-first"
                )}
                aria-label={isPinned ? t("nav.collapse", { defaultValue: "Collapse" }) : t("nav.expand", { defaultValue: "Expand" })}
              >
                {isPinned ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile Header (Hidden on LG) */}
        <header className="sticky top-0 z-50 flex h-14 w-full shrink-0 items-center border-b bg-background/90 backdrop-blur lg:hidden">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 md:px-6">
            <div className="flex items-center gap-3">
              <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                <SheetTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="-ml-2 text-muted-foreground"
                    aria-label={t("nav.openNavigation")}
                  >
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>

                <SheetContent side="left" className="w-[15rem] pt-8 flex flex-col h-full [&>button]:right-4 px-2">
                  <div className="flex h-12 shrink-0 items-center px-4 mb-0">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
                        S
                      </div>
                      <span className="text-xl font-bold tracking-tight">Sarflog</span>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto [&::-webkit-scrollbar]:hidden [scrollbar-width:none] [-ms-overflow-style:none]">
                    <NavList onNavigate={() => setMobileOpen(false)} isPremium={!!userQuery.data?.is_premium} isMobile />
                  </div>
                </SheetContent>
              </Sheet>

              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold text-sm">
                  S
                </div>
                <span className="text-lg font-bold tracking-tight">Sarflog</span>
              </div>
            </div>

            <div className="flex items-center gap-2 md:gap-3">
              <NotificationBell />

              <Button variant="ghost" size="icon" onClick={toggle} className="rounded-xl h-9 w-9 shrink-0">
                {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-2 rounded-full p-1 transition-all active:scale-95 hover:bg-muted/70">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-muted text-muted-foreground">
                      <User className="h-4 w-4" />
                    </div>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium leading-tight truncate">{username || t("common.user")}</p>
                      <p className="text-xs leading-tight text-muted-foreground truncate">{email || t("common.signedIn")}</p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => { setMobileOpen(false); navigate("/settings"); }}>
                    <IoSettingsOutline className="mr-2 h-4 w-4" />
                    {t("nav.settings")}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => { setMobileOpen(false); setLogoutOpen(true); }} className="text-destructive focus:bg-destructive/10 focus:text-destructive">
                    <LogOut className="mr-2 h-4 w-4 text-destructive" />
                    {t("common.signOut")}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>



        {/* Content Canvas */}
        <main className="mobile-page-scroll flex-1 overflow-y-auto pt-4 pb-4 lg:pt-8 lg:pb-8">
          <div className="mx-auto w-full max-w-7xl px-4 md:px-6 lg:px-8">
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


