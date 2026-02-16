import { cn } from "@/lib/utils";

function LoadingSpinner({ className }) {
  return (
    <div role="status" aria-live="polite" className={cn("inline-flex items-center justify-center", className)}>
      <span className="sr-only">Loading</span>
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
    </div>
  );
}

export { LoadingSpinner };
