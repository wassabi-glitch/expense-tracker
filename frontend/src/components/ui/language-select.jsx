import React from "react";
import { ChevronDown } from "lucide-react";

const DEFAULT_OPTIONS = [
  { value: "uz", label: "UZ" },
  { value: "ru", label: "RU" },
  { value: "en", label: "EN" },
];

export function LanguageSelect({
  value,
  onChange,
  options = DEFAULT_OPTIONS,
  className = "",
  buttonClassName = "",
  menuClassName = "",
  ariaLabel = "Language",
}) {
  const [open, setOpen] = React.useState(false);
  const rootRef = React.useRef(null);

  const active = options.find((o) => o.value === value) || options[0];

  React.useEffect(() => {
    const onDocClick = (e) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target)) setOpen(false);
    };
    const onEsc = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  const handlePick = (next) => {
    setOpen(false);
    if (next !== value) onChange(next);
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`flex h-9 items-center justify-center gap-1 rounded-md border border-input bg-background px-1.5 lg:px-2 text-center text-sm ${buttonClassName}`}
      >
        <span className="min-w-[2ch] text-center">{active.label}</span>
        <ChevronDown className="h-4 w-4 opacity-80" />
      </button>

      {open && (
        <div
          role="listbox"
          className={`absolute right-0 z-50 mt-1 min-w-full overflow-hidden rounded-md border border-border bg-popover shadow-md ${menuClassName}`}
        >
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handlePick(opt.value)}
              className={`block w-full px-3 py-2 text-center text-sm transition hover:bg-muted ${
                opt.value === value ? "bg-muted font-medium" : ""
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
