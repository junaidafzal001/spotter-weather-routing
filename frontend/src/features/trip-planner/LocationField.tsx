import { useEffect, useId, useRef, useState } from "react";
import { useController, type Control } from "react-hook-form";
import { Loader2, MapPin, Navigation } from "lucide-react";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useLocationSuggest } from "../../hooks/useLocationSuggest";
import type { FormValues } from "./schema";
import { cn } from "../../components/ui";

interface LocationFieldProps {
  control: Control<FormValues>;
  name: "origin" | "destination";
  label: string;
  placeholder: string;
  error?: string;
}

export function LocationField({ control, name, label, placeholder, error }: LocationFieldProps) {
  const { field } = useController({ control, name });
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputId = useId();
  const listId = useId();

  const value = field.value ?? "";
  const debounced = useDebouncedValue(value, 350);
  const { data, isFetching } = useLocationSuggest(debounced);
  const suggestions = data?.data.suggestions ?? [];

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  const Icon = name === "origin" ? MapPin : Navigation;

  return (
    <div ref={containerRef} className="relative">
      <label htmlFor={inputId} className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted">
        <Icon size={13} className="text-slate-400" aria-hidden />
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type="text"
          autoComplete="off"
          role="combobox"
          aria-expanded={open && suggestions.length > 0}
          aria-controls={listId}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : undefined}
          value={value}
          placeholder={placeholder}
          className={cn(
            "w-full rounded-lg border bg-white px-3 py-2 pr-8 text-sm text-ink shadow-sm outline-none transition",
            "placeholder:text-slate-400 focus:border-brand focus:ring-2 focus:ring-brand/20",
            error ? "border-red-400" : "border-line",
          )}
          onChange={(event) => {
            field.onChange(event);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            // Let the option's click land before closing.
            window.setTimeout(() => setOpen(false), 120);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") setOpen(false);
          }}
        />
        {isFetching ? (
          <Loader2
            size={14}
            className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-slate-400"
            aria-hidden
          />
        ) : null}
      </div>
      {error ? (
        <p id={`${inputId}-error`} role="alert" className="mt-1 text-xs font-medium text-red-600">
          {error}
        </p>
      ) : null}

      {open && suggestions.length > 0 ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-line bg-white py-1 shadow-xl"
        >
          {suggestions.map((suggestion) => (
            <li key={suggestion.label}>
              <button
                type="button"
                role="option"
                aria-selected={false}
                className="block w-full px-3 py-2 text-left text-xs leading-snug text-slate-700 hover:bg-brand-soft"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  field.onChange(suggestion.label);
                  setOpen(false);
                }}
              >
                {suggestion.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
