import * as React from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export function ActionMenu({ isOpen, position, onClose, children, zIndex = 150 }) {
  React.useEffect(() => {
    if (!isOpen) return;
    const handlePointerDown = (event) => {
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      if (target.closest("[data-action-popover]")) return;
      onClose();
    };
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [isOpen, onClose]);

  if (!isOpen || !position) return null;

  return createPortal(
    <div
      data-action-popover
      className="fixed w-44 rounded-md border border-border bg-popover p-1 shadow-lg animate-in fade-in zoom-in-95 duration-200"
      style={{ top: `${position.top}px`, left: `${position.left}px`, zIndex }}
    >
      {children}
    </div>,
    document.body
  );
}

export function ActionMenuItem({ icon: Icon, label, onClick, variant = "default", className }) {
  const isDestructive = variant === "destructive";
  return (
    <button
      type="button"
      className={cn(
        "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors cursor-pointer",
        isDestructive
          ? "text-destructive hover:bg-destructive/10"
          : "hover:bg-muted text-foreground hover:text-foreground",
        className
      )}
      onClick={onClick}
    >
      {Icon && <Icon className="h-4 w-4 shrink-0" />} {label}
    </button>
  );
}

export function ActionMenuDivider() {
  return <div className="mx-2 my-1 border-t border-border/40" />;
}
