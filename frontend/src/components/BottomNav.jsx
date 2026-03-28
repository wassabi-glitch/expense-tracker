import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { 
  LayoutDashboard, 
  Receipt, 
  PiggyBank, 
  MoreHorizontal 
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
  { to: "/budgets", labelKey: "nav.budgets", icon: PiggyBank },
  { to: "/expenses", labelKey: "nav.expenses", icon: Receipt },
  { to: "/more", labelKey: "nav.more", icon: MoreHorizontal },
];

export function BottomNav() {
  const { t } = useTranslation();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-[60] flex h-16 items-center justify-around border-t bg-background/80 px-2 pb-safe backdrop-blur-lg md:hidden">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            cn(
              "flex flex-col items-center gap-1 px-3 py-1 transition-colors",
              isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
            )
          }
        >
          <item.icon className="h-4.5 w-4.5 sm:h-5 sm:w-5 transition-transform active:scale-90" />
          <span className="text-[9px] sm:text-[10px] font-medium transition-opacity">{t(item.labelKey)}</span>
        </NavLink>
      ))}
    </nav>
  );
}
