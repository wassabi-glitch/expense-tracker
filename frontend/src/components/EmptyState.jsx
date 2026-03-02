import React from "react";
import { Inbox } from "lucide-react";

export function EmptyState({ icon: Icon = Inbox, title, description, className = "", inline = false }) {
    if (inline) {
        return (
            <div className={`px-4 py-8 flex flex-col items-center gap-3 text-sm text-muted-foreground text-center ${className}`}>
                <Icon className="h-8 w-8 text-muted-foreground/50" />
                <div>
                    {title && <p className="font-medium text-foreground">{title}</p>}
                    {description && <p>{description}</p>}
                </div>
            </div>
        );
    }

    return (
        <div className={`flex flex-col items-center justify-center p-8 text-center border rounded-lg border-dashed bg-muted/20 ${className}`}>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/50 mb-4">
                <Icon className="h-6 w-6 text-muted-foreground" />
            </div>
            {title && <h3 className="text-lg font-semibold">{title}</h3>}
            {description && <p className="text-sm text-muted-foreground mt-1 max-w-sm">{description}</p>}
        </div>
    );
}
