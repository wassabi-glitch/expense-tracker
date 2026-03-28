import React from "react";

export function PageHeader({ title, description, children }) {
    return (
        <div className="flex flex-col gap-3 sm:gap-4 sm:flex-row sm:items-center sm:justify-between min-w-0">
            <div className="min-w-0">
                <h1 className="text-xl sm:text-3xl font-bold tracking-tight text-foreground">
                    {title}
                </h1>
                {description && (
                    <p className="text-xs sm:text-base text-muted-foreground mt-0.5 sm:mt-1 line-clamp-2">{description}</p>
                )}
            </div>
            {children && (
                <div className="flex items-center gap-2 shrink-0 [&>*]:!h-7 [&>*]:!text-[10px] [&>*]:!px-2.5 sm:[&>*]:!h-10 sm:[&>*]:!text-sm sm:[&>*]:!px-4 [&_svg]:!size-3 sm:[&_svg]:!size-4">
                    {children}
                </div>
            )}
        </div>
    );
}
