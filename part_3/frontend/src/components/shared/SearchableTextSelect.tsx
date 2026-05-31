import { useEffect, useMemo, useRef, useState } from "react";

interface SearchableTextSelectProps {
  label: string;
  value: string;
  options: string[];
  placeholder?: string;
  helperText?: string;
  errorText?: string;
  disabled?: boolean;
  className?: string;
  emptyLabel?: string;
  onChange: (value: string) => void;
}

function normalize(value: string) {
  return value.trim().toLocaleLowerCase("sv-SE");
}

export function SearchableTextSelect({
  label,
  value,
  options,
  placeholder = "Search and select...",
  helperText,
  errorText,
  disabled = false,
  className,
  emptyLabel = "All / no filter",
  onChange,
}: SearchableTextSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLLabelElement | null>(null);

  useEffect(() => {
    function closeOnOutsidePointer(event: PointerEvent) {
      if (!rootRef.current || rootRef.current.contains(event.target as Node)) return;
      setIsOpen(false);
    }

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => document.removeEventListener("pointerdown", closeOnOutsidePointer);
  }, []);

  const filteredOptions = useMemo(() => {
    const search = normalize(value);
    const uniqueOptions = Array.from(new Set(options.filter(Boolean))).sort((left, right) => left.localeCompare(right, "sv-SE"));
    if (!search) return uniqueOptions.slice(0, 30);
    const startsWith = uniqueOptions.filter((option) => normalize(option).startsWith(search));
    const includes = uniqueOptions.filter((option) => !normalize(option).startsWith(search) && normalize(option).includes(search));
    return [...startsWith, ...includes].slice(0, 30);
  }, [options, value]);

  return (
    <label ref={rootRef} className={["field smart-select", className, isOpen ? "is-open" : ""].filter(Boolean).join(" ")}>
      <span>{label}</span>
      <div className="smart-select-control">
        <input
          value={value}
          autoComplete="off"
          placeholder={placeholder}
          disabled={disabled}
          className={errorText ? "field-invalid" : undefined}
          onFocus={() => !disabled && setIsOpen(true)}
          onClick={() => !disabled && setIsOpen(true)}
          onChange={(event) => {
            onChange(event.target.value);
            if (!disabled) setIsOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setIsOpen(false);
              event.currentTarget.blur();
            }
          }}
        />
        {value && !disabled && (
          <button
            type="button"
            className="smart-select-clear"
            onClick={() => {
              onChange("");
              setIsOpen(false);
            }}
            aria-label={`Clear ${label}`}
          >
            Clear
          </button>
        )}
      </div>
      {helperText && <small className="field-help">{helperText}</small>}
      {errorText && <small className="field-error">{errorText}</small>}
      {isOpen && !disabled && (
        <div className="smart-select-options" role="listbox" aria-label={`${label} options`}>
          <button type="button" className="smart-select-option muted-option" onClick={() => { onChange(""); setIsOpen(false); }}>
            {emptyLabel}
          </button>
          {filteredOptions.length === 0 ? (
            <div className="smart-select-option muted-option">No matching option found. You can still type a value and apply filters.</div>
          ) : (
            filteredOptions.map((option) => (
              <button
                key={option}
                type="button"
                className="smart-select-option"
                onClick={() => {
                  onChange(option);
                  setIsOpen(false);
                }}
              >
                {option}
              </button>
            ))
          )}
        </div>
      )}
    </label>
  );
}
