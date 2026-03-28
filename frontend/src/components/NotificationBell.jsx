import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useNotifications } from "@/lib/context/NotificationContext";
import { NotificationList } from "@/components/NotificationList";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

export function NotificationBell() {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const { unreadCount } = useNotifications();

    const TriggerContent = (
        <>
            <Bell className={cn("h-5 w-5 transition-transform", (isOpen || mobileOpen) && "scale-90")} />
            {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 z-10 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white shadow">
                    {unreadCount > 9 ? "9+" : unreadCount}
                </span>
            )}
        </>
    );

    const TriggerButton = (props) => (
        <Button
            variant="ghost"
            size="icon"
            {...props}
            className={cn(
                "relative rounded-xl transition-colors",
                (isOpen || mobileOpen) && "bg-muted",
                props.className
            )}
            aria-label={t("notifications.title")}
        >
            {TriggerContent}
        </Button>
    );

    return (
        <div className="relative">
            {/* ── Mobile View: Sheet (Drawer style) ────── */}
            <div className="md:hidden">
                <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                    <SheetTrigger asChild>
                        <TriggerButton />
                    </SheetTrigger>
                    <SheetContent side="bottom" showCloseButton={false} className="h-[82vh] p-0 rounded-t-2xl overflow-hidden border-t shadow-2xl flex flex-col">
                        <NotificationList onClose={() => setMobileOpen(false)} />
                    </SheetContent>
                </Sheet>
            </div>

            {/* ── Desktop View: Dropdown ────────────────── */}
            <div className="hidden md:block">
                <TriggerButton onClick={() => setIsOpen(!isOpen)} />

                {isOpen && (
                    <>
                        {/* Backdrop to close */}
                        <div
                            className="fixed inset-0 z-40"
                            onClick={() => setIsOpen(false)}
                        />

                        {/* Dropdown panel */}
                        <div className="absolute right-0 top-full z-50 mt-2 w-[380px] animate-in fade-in-0 slide-in-from-top-2 duration-150">
                            <div className="rounded-xl border bg-background shadow-xl overflow-hidden max-h-[520px] flex flex-col">
                                <NotificationList className="flex-1 min-h-0" onClose={() => setIsOpen(false)} />
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
