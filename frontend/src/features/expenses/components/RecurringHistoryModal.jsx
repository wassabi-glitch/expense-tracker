import * as React from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { 
    History, CheckCircle2, AlertCircle, FastForward, 
    PlusCircle, RefreshCw, PlayCircle 
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useRecurringEventsQuery } from "../hooks/useRecurringEventsQuery";
import { cn } from "@/lib/utils";
import { formatDisplayDateTime, formatDisplayDate } from "@/lib/format";
import i18n from "../../../i18n";

const EVENT_CONFIG = {
    CREATED: { icon: PlusCircle, color: "text-blue-500", bg: "bg-blue-500/10" },
    PAID: { icon: CheckCircle2, color: "text-green-500", bg: "bg-green-500/10" },
    SKIPPED: { icon: FastForward, color: "text-slate-500", bg: "bg-slate-500/10" },
    FAILED: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-500/10" },
    UPDATED: { icon: RefreshCw, color: "text-amber-500", bg: "bg-amber-500/10" },
    RESUMED: { icon: PlayCircle, color: "text-indigo-500", bg: "bg-indigo-500/10" },
};

export function RecurringHistoryModal({ isOpen, onClose, recurringExpense }) {
    const { t } = useTranslation();
    const appLang = String(i18n.language || i18n.resolvedLanguage || "en").toLowerCase();
    
    const { data: events, isLoading } = useRecurringEventsQuery(
        recurringExpense?.id,
        isOpen
    );

    return (
        <Dialog open={isOpen} onOpenChange={(val) => !val && onClose()}>
            <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col p-0 overflow-hidden border-border/60 bg-card/95 backdrop-blur-xl">
                <DialogHeader className="p-6 pb-0">
                    <div className="flex items-center gap-3 mb-1">
                        <div className="p-2 rounded-xl bg-primary/10 text-primary">
                            <History className="h-5 w-5" />
                        </div>
                        <div>
                            <DialogTitle className="text-xl font-black tracking-tight">
                                {t("recurring.historyTitle", { defaultValue: "Expense Diary" })}
                            </DialogTitle>
                            <DialogDescription className="text-xs font-medium opacity-70">
                                {recurringExpense?.title}
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-12 gap-4">
                            <LoadingSpinner className="h-8 w-8 text-primary" />
                            <p className="text-sm font-medium text-muted-foreground animate-pulse">
                                {t("recurring.loadingDiary", { defaultValue: "Reading the diary..." })}
                            </p>
                        </div>
                    ) : !events || events.length === 0 ? (
                        <div className="text-center py-12">
                            <p className="text-sm text-muted-foreground">
                                {t("recurring.noHistory", { defaultValue: "No events recorded yet." })}
                            </p>
                        </div>
                    ) : (
                        <div className="relative space-y-6 before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-[2px] before:bg-gradient-to-b before:from-transparent before:via-border-foreground/20 before:to-transparent">
                            {events.map((event, idx) => {
                                const config = EVENT_CONFIG[event.event_type] || EVENT_CONFIG.UPDATED;
                                const Icon = config.icon;
                                
                                return (
                                    <div key={event.id} className="relative flex items-start gap-4 group">
                                        {/* Icon Node */}
                                        <div className={cn(
                                            "relative z-10 flex shrink-0 items-center justify-center h-10 w-10 rounded-xl border border-border/50 shadow-sm transition-colors duration-300",
                                            config.bg
                                        )}>
                                            <Icon className={cn("h-5 w-5", config.color)} />
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 pt-0.5">
                                            <div className="flex items-center justify-between gap-2 mb-1">
                                                <span className={cn("text-xs font-black uppercase tracking-widest", config.color)}>
                                                    {t(`recurring.event.${event.event_type.toLowerCase()}`, { defaultValue: event.event_type })}
                                                </span>
                                                <span className="text-[10px] font-bold text-muted-foreground opacity-60">
                                                    {formatDisplayDateTime(event.created_at, appLang)}
                                                </span>
                                            </div>
                                            
                                            <p className="text-sm font-medium text-foreground/90 leading-relaxed">
                                                {/* 
                                                    Prioritize translation keys for the description.
                                                    If it's a legacy record or complex update, fallback to metadata_notes.
                                                */}
                                                {t(`recurring.historyDescription.${event.event_type.toLowerCase()}`, { 
                                                    defaultValue: event.metadata_notes || t("recurring.noNotes", { defaultValue: "System update" })
                                                })}
                                            </p>

                                            {(event.old_next_due_date || event.new_next_due_date) && (
                                                <div className="mt-2 flex items-center gap-2 text-[10px] font-bold py-1 px-2 rounded bg-muted/30 w-fit border border-border/20">
                                                    {event.old_next_due_date && (
                                                        <>
                                                            <span className="text-muted-foreground line-through opacity-50">
                                                                {formatDisplayDate(event.old_next_due_date, appLang)}
                                                            </span>
                                                            <FastForward className="h-3 w-3 text-muted-foreground opacity-40" />
                                                        </>
                                                    )}
                                                    <span className="text-primary">
                                                        {event.new_next_due_date ? formatDisplayDate(event.new_next_due_date, appLang) : t("recurring.finished", { defaultValue: "Finished" })}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                <DialogFooter className="p-4 border-t border-border/30 bg-muted/10">
                    <Button 
                        variant="outline" 
                        onClick={onClose}
                        className="w-full sm:w-auto"
                    >
                        {t("common.close", { defaultValue: "Close" })}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
