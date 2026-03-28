import React from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { 
  Landmark,
  Wallet, 
  LineChart, 
  Download, 
  Sparkles, 
  Settings, 
  LogOut,
  ChevronRight,
  TrendingUp,
  CreditCard,
  UserCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const wealthItems = [
  { to: "/income", labelKey: "nav.income", icon: Landmark },
  { to: "/savings", labelKey: "nav.savings", icon: Wallet },
  { to: "/analytics", labelKey: "nav.analytics", icon: LineChart },
];

const utilityItems = [
  { to: "/export", labelKey: "nav.exportData", icon: Download },
  { to: "/settings", labelKey: "nav.settings", icon: Settings },
];

export function MobileMenuHub({ isOpen, onClose, onLogout, username, email }) {
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-x-0 top-16 z-[45] flex flex-col bg-background/95 backdrop-blur-md animate-in fade-in slide-in-from-bottom-5 duration-300 border-t" 
         style={{ height: 'calc(100dvh - 64px - 64px)' }}>
      
      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-4 pt-4 pb-8 space-y-6">
        
        {/* Navigation List (Nav Bar Style) */}
        <div className="grid gap-1">
          {[...wealthItems, ...utilityItems].map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className="flex items-center gap-4 px-4 py-3.5 rounded-2xl hover:bg-muted/50 active:bg-muted transition-colors group"
            >
              <item.icon className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
              <span className="flex-1 font-semibold text-[15px] text-foreground/80 group-hover:text-foreground transition-colors">
                {t(item.labelKey)}
              </span>
            </NavLink>
          ))}
        </div>

        {/* Premium Banner (Glassmorphism) */}
        <div className="relative overflow-hidden rounded-[32px] bg-gradient-to-br from-green-600 to-emerald-800 p-6 text-white shadow-xl shadow-green-900/10 border border-white/5 group active:scale-[0.98] transition-all cursor-pointer">
          <Sparkles className="absolute -right-4 -top-4 h-32 w-32 text-white/10 rotate-12" />
          <div className="relative z-10 space-y-4">
            <div className="space-y-1">
              <h4 className="text-xl font-black tracking-tight">Sarflog Premium</h4>
              <p className="text-sm font-medium text-white/80 max-w-[200px]">Unlock AI-powered insights and unlimited budgets.</p>
            </div>
            <Button className="bg-white text-emerald-800 hover:bg-white/90 rounded-2xl font-black text-xs px-6 h-10 shadow-lg">
              UPGRADE NOW
            </Button>
          </div>
        </div>

        {/* Sign Out (Simplified) */}
        <button
          onClick={() => { onClose(); onLogout(); }}
          className="w-full flex items-center gap-4 px-4 py-4 rounded-2xl hover:bg-destructive/5 active:bg-destructive/10 transition-all group"
        >
          <LogOut className="h-5 w-5 text-destructive/60 group-hover:text-destructive transition-colors" />
          <span className="font-bold text-[15px] text-destructive/80 group-hover:text-destructive uppercase tracking-wide">{t("common.signOut")}</span>
        </button>

        {/* Version Info (Subtle) */}
        <div className="text-center pt-2 pb-2 opacity-20">
          <p className="text-[10px] font-black uppercase tracking-[4px]">
            Sarflog v2.4.0
          </p>
        </div>

      </div>
    </div>
  );
}
