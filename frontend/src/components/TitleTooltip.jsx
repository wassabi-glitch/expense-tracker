import { useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export const TitleTooltip = ({ title, children }) => {
  const [open, setOpen] = useState(false);
  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip open={open} onOpenChange={setOpen}>
        <TooltipTrigger asChild>
          <div
            className="w-fit max-w-full text-left outline-none cursor-default overflow-hidden"
            onClick={(e) => {
              e.stopPropagation();
              setOpen(true);
            }}
            onPointerDown={(e) => {
              e.stopPropagation();
            }}
          >
            {children}
          </div>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          sideOffset={5}
          className="max-w-[280px] break-words z-[50]"
          onPointerDown={(e) => e.stopPropagation()}
        >
          {title}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
