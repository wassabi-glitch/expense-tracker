import { useState } from "react";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export function InteractiveTooltip({
  content,
  children,
  className = "",
  contentClassName = "",
  side = "top",
}) {
  const [open, setOpen] = useState(false);

  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip open={open} onOpenChange={setOpen}>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={className}
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={() => setOpen(false)}
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onClick={() => setOpen((prev) => !prev)}
          >
            {children}
          </button>
        </TooltipTrigger>
        <TooltipContent side={side} className={contentClassName}>
          {content}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
