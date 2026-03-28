import React from "react";
import { useTranslation } from "react-i18next";
import {
  Bell,
  Check,
  CheckCheck,
  Trash2,
  AlertTriangle,
  AlertCircle,
  Info,
  BellOff,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useNotifications } from "@/lib/context/NotificationContext";
import { formatRelativeTime } from "@/lib/format";
import { formatMoneyBold } from "@/lib/formatMoney";

export function NotificationList({ onClose, className }) {
  const { t, i18n } = useTranslation();
  const {
    notifications,
    unreadCount,
    isLoading,
    markAsRead,
    markAllAsRead,
    removeNotification,
    getNotificationIcon,
    getNotificationPriorityClass,
  } = useNotifications();

  const handleNotificationClick = (notification) => {
    if (!notification.is_read) {
      markAsRead([notification.id]);
    }
  };

  const getPriorityAccent = (priority) => {
    switch (priority) {
      case "critical": return "border-l-destructive";
      case "high": return "border-l-orange-500";
      case "medium": return "border-l-yellow-500";
      default: return "border-l-transparent";
    }
  };

  const getPriorityIcon = (priority) => {
    switch (priority) {
      case "critical":
        return <AlertCircle className="h-3.5 w-3.5 text-destructive" />;
      case "high":
        return <AlertTriangle className="h-3.5 w-3.5 text-orange-500" />;
      case "medium":
        return <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />;
      default:
        return <Info className="h-3.5 w-3.5 text-muted-foreground" />;
    }
  };

  const getTranslatedPriority = (priority) =>
    t(`notifications.priority.${priority}`);

  const translateCategory = (category) =>
    t(`categories.${category}`, { defaultValue: category });

  const getTranslatedTitle = (notification) => {
    const { type, extra_data } = notification;
    if (type === "budget_exceeded" || type === "budget_warning") {
      const percentage = extra_data?.percentage || 0;
      let prefix = percentage >= 90
        ? t("notifications.titles.highRisk")
        : percentage >= 70
          ? t("notifications.titles.budgetWarning")
          : type === "budget_exceeded"
            ? t("notifications.titles.budgetExceeded")
            : t("notifications.titles.budgetWarning");
      return `${prefix}: ${translateCategory(extra_data?.category || "")}`;
    }
    if (type === "goal_completed" || type === "goal_milestone") {
      const prefix = type === "goal_completed"
        ? t("notifications.titles.goalReached")
        : t("notifications.titles.goalMilestone");
      return `${prefix}: ${extra_data?.goal_title || ""}`;
    }
    return notification.title;
  };

  const getTranslatedMessage = (notification) => {
    const d = notification.extra_data || {};
    const { type } = notification;
    if (type === "budget_exceeded")
      return t("notifications.messages.budget_exceeded_detail", {
        category: translateCategory(d.category || ""),
        over: (d.spent - d.limit)?.toLocaleString() || "0",
      });
    if (type === "budget_warning") {
      if (d.percentage >= 90)
        return t("notifications.messages.budget_warning_90", {
          category: translateCategory(d.category || ""),
          remaining: (d.limit - d.spent)?.toLocaleString() || "0",
        });
      if (d.percentage >= 70)
        return t("notifications.messages.budget_warning_70", {
          category: translateCategory(d.category || ""),
          remaining: (d.limit - d.spent)?.toLocaleString() || "0",
        });
      if (d.percentage >= 50)
        return t("notifications.messages.budget_warning_50", { category: translateCategory(d.category || "") });
    }
    if (type === "goal_completed")
      return t("notifications.messages.goal_completed_detail", { goal: d.goal_title || "" });
    if (type === "goal_milestone") {
      if (d.percentage >= 75)
        return t("notifications.messages.goal_milestone_75_detail", {
          goal: d.goal_title || "",
          remaining: (d.target_amount - d.funded_amount)?.toLocaleString() || "0",
        });
      if (d.percentage >= 50) return t("notifications.messages.goal_milestone_50_detail", { goal: d.goal_title || "" });
      if (d.percentage >= 25) return t("notifications.messages.goal_milestone_25_detail", { goal: d.goal_title || "" });
    }
    return notification.message;
  };

  const getTranslatedRelativeTime = (isoDate) => {
    const relativeTime = formatRelativeTime(isoDate);
    if (!relativeTime) return "";
    const lang = i18n.language || "en";
    const tr = {
      en: { "just now": t("common.justNow") || "just now", "m ago": "m ago", "h ago": "h ago", "d ago": "d ago" },
      ru: { "just now": t("common.justNow") || "только что", "m ago": "мин. назад", "h ago": "ч. назад", "d ago": "дн. назад" },
      uz: { "just now": t("common.justNow") || "hozir", "m ago": "daq. oldin", "h ago": "soat oldin", "d ago": "kun oldin" },
    };
    const lt = tr[lang] || tr.en;
    if (relativeTime === "just now") return lt["just now"];
    if (relativeTime.endsWith("m ago")) return relativeTime.replace("m ago", lt["m ago"]);
    if (relativeTime.endsWith("h ago")) return relativeTime.replace("h ago", lt["h ago"]);
    if (relativeTime.endsWith("d ago")) return relativeTime.replace("d ago", lt["d ago"]);
    return relativeTime;
  };

  return (
    <div className={cn("flex flex-col h-full bg-background", className)}>
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3 bg-muted/30">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-foreground/70" />
          <h3 className="font-semibold text-sm tracking-tight text-foreground">
            {t("notifications.title")}
          </h3>
          {unreadCount > 0 && (
            <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/15 px-1.5 text-[11px] font-semibold text-primary">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="icon"
              onClick={markAllAsRead}
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              title={t("notifications.markAllRead")}
            >
              <CheckCheck className="h-4 w-4" />
            </Button>
          )}
          {/* Mobile Close Button */}
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="md:hidden h-8 w-8 text-muted-foreground hover:text-foreground rounded-lg"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto overscroll-contain pb-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center gap-2 py-12 text-muted-foreground">
            <Bell className="h-7 w-7 animate-pulse opacity-40" />
            <p className="text-sm">{t("common.loading")}</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-muted-foreground">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <BellOff className="h-6 w-6 opacity-50" />
            </div>
            <div className="text-center px-6">
              <p className="text-sm font-medium text-foreground/60">{t("notifications.empty")}</p>
              <p className="text-xs mt-0.5 text-muted-foreground">You're all caught up!</p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-border/50">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                className={cn(
                  "group relative flex items-start gap-3 px-4 py-3.5 border-l-2 cursor-pointer transition-colors hover:bg-muted/40",
                  getPriorityAccent(notification.priority),
                  !notification.is_read
                    ? "bg-primary/[0.03]"
                    : "opacity-80 hover:opacity-100"
                )}
              >
                {/* Emoji icon */}
                <div className={cn(
                  "flex-shrink-0 flex h-9 w-9 items-center justify-center rounded-full text-lg",
                  !notification.is_read ? "bg-muted" : "bg-muted/60"
                )}>
                  {getNotificationIcon(notification.type)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 pr-6">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className={cn(
                      "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold border",
                      getNotificationPriorityClass(notification.priority)
                    )}>
                      {getPriorityIcon(notification.priority)}
                      {getTranslatedPriority(notification.priority)}
                    </span>
                    <p className="text-[10px] font-medium text-muted-foreground/70 uppercase tracking-wide">
                      {getTranslatedRelativeTime(notification.created_at)}
                    </p>
                  </div>

                  <p className={cn(
                    "text-sm leading-snug",
                    !notification.is_read ? "font-semibold text-foreground" : "font-medium text-foreground/80"
                  )}>
                    {getTranslatedTitle(notification)}
                  </p>

                  <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed line-clamp-2">
                    {formatMoneyBold(getTranslatedMessage(notification))}
                  </p>
                </div>

                {/* Unread dot */}
                {!notification.is_read && (
                  <span className="flex-shrink-0 mt-1.5 h-2 w-2 rounded-full bg-primary shadow-sm shadow-primary/30" />
                )}

                {/* Action buttons - Absolute on the right center */}
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 md:opacity-0 transition-opacity">
                   {!notification.is_read && (
                    <button
                      onClick={(e) => { e.stopPropagation(); markAsRead([notification.id]); }}
                      className="flex h-8 w-8 items-center justify-center rounded-full bg-background border shadow-sm text-muted-foreground hover:text-foreground"
                    >
                      <Check className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); removeNotification(notification.id); }}
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-background border shadow-sm text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                
                {/* Mobile version of buttons (always visible on very small screens if they overlap) */}
                <div className="md:hidden absolute right-1.5 bottom-1.5 flex items-center gap-1">
                   <button
                    onClick={(e) => { e.stopPropagation(); removeNotification(notification.id); }}
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-muted/40 text-muted-foreground"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer hint */}
      {notifications.length > 0 && (
        <div className="border-t px-4 py-2 bg-muted/20 text-center">
          <p className="text-[11px] text-muted-foreground font-medium">
            {t("notifications.totalCount", { count: notifications.length })}
          </p>
        </div>
      )}
    </div>
  );
}
