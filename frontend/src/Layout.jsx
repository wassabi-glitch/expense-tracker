import React from "react"
import { Outlet, NavLink } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
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
} from "lucide-react"
import { cn } from "@/lib/utils"

// --- NAVIGATION ITEMS ---
const mainNavItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/expenses", label: "Expenses", icon: Receipt },
  { to: "/budgets", label: "Budgets", icon: PiggyBank },
  { to: "/analytics", label: "Analytics", icon: LineChart },
]

const secondaryNavItems = [
  { to: "/export", label: "Export Data", icon: Download },
  { to: "/settings", label: "Settings", icon: Settings },
]

// --- DARK MODE HOOK ---
function useDarkMode() {
  const [isDark, setIsDark] = React.useState(() => {
    if (typeof window === "undefined") return false
    const stored = localStorage.getItem("theme")
    if (stored === "dark") return true
    if (stored === "light") return false
    return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ?? false
  })

  React.useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark)
    localStorage.setItem("theme", isDark ? "dark" : "light")
  }, [isDark])

  return { isDark, toggle: () => setIsDark((v) => !v) }
}

// --- NAV COMPONENT (Reusable) ---
function NavList({ onNavigate }) {
  return (
    <div className="flex flex-col gap-6 py-6">
      {/* Main Group */}
      <div>
        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Platform
        </div>
        <div className="space-y-1">
          {mainNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                  "hover:bg-muted hover:text-foreground",
                  isActive
                    ? "bg-muted text-foreground ring-1 ring-border"
                    : "text-muted-foreground"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={cn(
                      "h-4 w-4 shrink-0 transition-colors",
                      isActive
                        ? "text-primary"
                        : "text-muted-foreground group-hover:text-foreground"
                    )}
                  />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>

      {/* Tools Group */}
      <div>
        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Tools
        </div>
        <div className="space-y-1">
          {secondaryNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                  "hover:bg-muted hover:text-foreground",
                  isActive
                    ? "bg-muted text-foreground ring-1 ring-border"
                    : "text-muted-foreground"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    className={cn(
                      "h-4 w-4 shrink-0 transition-colors",
                      isActive
                        ? "text-primary"
                        : "text-muted-foreground group-hover:text-foreground"
                    )}
                  />
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Layout() {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const { isDark, toggle } = useDarkMode()

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background">
      {/* TOP BAR */}
      <header className="sticky top-0 z-50 flex h-16 items-center justify-between border-b bg-background/90 px-4 backdrop-blur lg:px-6">
        {/* LEFT: Logo + Mobile Menu */}
        <div className="flex items-center gap-3">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden -ml-2 text-muted-foreground"
                aria-label="Open navigation"
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
            <span className="font-semibold tracking-tight">ExpenseTracker</span>
          </div>
        </div>

        {/* RIGHT: Theme + User */}
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            className="rounded-xl"
            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </Button>

          <div className="hidden text-right md:block">
            <p className="text-sm font-medium leading-none">Alex Johnson</p>
            <p className="text-xs text-muted-foreground">Premium Plan</p>
          </div>

          <div className="flex h-9 w-9 items-center justify-center rounded-full border bg-muted text-muted-foreground">
            <User className="h-5 w-5" />
          </div>
        </div>
      </header>

      {/* CONTENT AREA */}
      <div className="flex flex-1 overflow-hidden">
        {/* SIDEBAR (Desktop) */}
        <aside className="hidden w-64 flex-col border-r bg-background lg:flex">
          <div className="flex-1 overflow-y-auto px-4">
            <NavList />
          </div>

          <div className="border-t p-4">
            <Button
              variant="ghost"
              className="w-full justify-start text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </aside>

        {/* MAIN */}
        <main className="flex-1 overflow-y-auto px-4 pt-2 pb-4 lg:px-6 lg:pt-3 lg:pb-6">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
