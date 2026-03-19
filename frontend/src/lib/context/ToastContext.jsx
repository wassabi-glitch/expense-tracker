import { createContext, useContext, useState, useCallback } from "react";
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatMoneyBold } from "@/lib/formatMoney";

const ToastContext = createContext(null);

const TOAST_LIMIT = 5;
const TOAST_DURATION = 5000;

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);

    const dismissToast = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const addToast = useCallback(({ title, description, type = "info", duration = TOAST_DURATION }) => {
        const id = Date.now() + Math.random();
        const newToast = { id, title, description, type, duration };

        setToasts((prev) => {
            return [newToast, ...prev].slice(0, TOAST_LIMIT);
        });

        if (duration > 0) {
            setTimeout(() => {
                dismissToast(id);
            }, duration);
        }

        return id;
    }, [dismissToast]);

    const toast = {
        success: (title, description) => addToast({ title, description, type: "success" }),
        error: (title, description) => addToast({ title, description, type: "error", duration: 8000 }),
        warning: (title, description) => addToast({ title, description, type: "warning" }),
        info: (title, description) => addToast({ title, description, type: "info" }),
        budgetAlert: (title, description, priority = "warning") => addToast({ title, description, type: priority }),
        custom: (options) => addToast(options),
    };

    return (
        <ToastContext.Provider value={{ toast, dismissToast }}>
            {children}
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        </ToastContext.Provider>
    );
}

function ToastContainer({ toasts, onDismiss }) {
    if (toasts.length === 0) return null;

    return (
        <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 w-80 sm:w-96">
            {toasts.map((t) => (
                <Toast key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
            ))}
        </div>
    );
}

function Toast({ toast, onDismiss }) {
    const icons = {
        success: <CheckCircle className="h-5 w-5 text-green-500" />,
        error: <AlertCircle className="h-5 w-5 text-destructive" />,
        warning: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
        info: <Info className="h-5 w-5 text-blue-500" />,
        critical: <AlertCircle className="h-5 w-5 text-destructive" />,
        high: <AlertTriangle className="h-5 w-5 text-orange-500" />,
        medium: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
        low: <Info className="h-5 w-5 text-blue-400" />,
    };

    const bgColors = {
        success: "border-green-500/50 bg-green-100 dark:bg-green-950 dark:border-green-700",
        error: "border-destructive/50 bg-red-100 dark:bg-red-950 dark:border-red-800",
        warning: "border-yellow-500/50 bg-yellow-100 dark:bg-yellow-950 dark:border-yellow-700",
        info: "border-blue-500/50 bg-blue-100 dark:bg-blue-950 dark:border-blue-700",
        critical: "border-destructive/50 bg-red-100 dark:bg-red-950 dark:border-red-800",
        high: "border-orange-500/50 bg-orange-100 dark:bg-orange-950 dark:border-orange-700",
        medium: "border-yellow-500/50 bg-yellow-100 dark:bg-yellow-950 dark:border-yellow-700",
        low: "border-blue-500/50 bg-blue-100 dark:bg-blue-950 dark:border-blue-700",
    };

    const icon = icons[toast.type] || icons.info;
    const bg = bgColors[toast.type] || bgColors.info;

    return (
        <div
            className={cn(
                "flex items-start gap-3 p-4 rounded-lg border shadow-lg animate-in slide-in-from-right-full",
                bg
            )}
        >
            <div className="flex-shrink-0 mt-0.5">{icon}</div>
            <div className="flex-1 min-w-0">
                {toast.title && (
                    <p className="text-sm font-medium text-foreground">{toast.title}</p>
                )}
                {toast.description && (
                    <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                        {formatMoneyBold(toast.description)}
                    </p>
                )}
            </div>
            <button
                onClick={onDismiss}
                className="flex-shrink-0 rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            >
                <X className="h-4 w-4" />
            </button>
        </div>
    );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error("useToast must be used within a ToastProvider");
    }
    return context.toast;
}
