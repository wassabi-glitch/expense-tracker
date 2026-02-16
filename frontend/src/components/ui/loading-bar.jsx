import { cn } from "@/lib/utils";

function LoadingBar({ className }) {
  return (
    <div role="status" aria-live="polite" className={cn("w-full", className)}>
      <span className="sr-only">Loading</span>
      <div className="h-2 w-full overflow-hidden rounded-full bg-primary/20">
        <div className="h-full w-full animate-pulse bg-primary/70" />
      </div>
    </div>
  );
}

export { LoadingBar };
