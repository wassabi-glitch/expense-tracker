import * as React from "react";

import { cn } from "@/lib/utils";

function Switch(
  {
    checked,
    defaultChecked = false,
    disabled = false,
    onCheckedChange,
    size = "md",
    className,
    ...props
  },
  ref
) {
  const isControlled = typeof checked === "boolean";
  const [internalChecked, setInternalChecked] = React.useState(defaultChecked);
  const isChecked = isControlled ? checked : internalChecked;

  const trackSizeClass = size === "sm" ? "h-5 w-9" : "h-6 w-11";
  const thumbSizeClass = size === "sm" ? "h-4 w-4" : "h-5 w-5";
  const thumbCheckedClass = size === "sm" ? "translate-x-4" : "translate-x-5";

  const toggle = () => {
    if (disabled) return;
    const next = !isChecked;
    if (!isControlled) setInternalChecked(next);
    onCheckedChange?.(next);
  };

  return (
    <button
      {...props}
      ref={ref}
      type="button"
      role="switch"
      aria-checked={isChecked}
      aria-disabled={disabled}
      disabled={disabled}
      onClick={toggle}
      className={cn(
        "relative inline-flex shrink-0 items-center rounded-full transition-colors",
        trackSizeClass,
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:cursor-not-allowed disabled:opacity-60",
        isChecked ? "bg-primary" : "bg-muted",
        className
      )}
    >
      <span className="sr-only">Toggle</span>
      <span
        aria-hidden="true"
        className={cn(
          "pointer-events-none inline-block transform rounded-full bg-background shadow-sm transition-transform",
          thumbSizeClass,
          isChecked ? thumbCheckedClass : "translate-x-0.5"
        )}
      />
    </button>
  );
}

const SwitchComponent = React.forwardRef(Switch);
SwitchComponent.displayName = "Switch";

export { SwitchComponent as Switch };
