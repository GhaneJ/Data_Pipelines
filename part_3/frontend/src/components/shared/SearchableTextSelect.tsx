import { useEffect, useId, useMemo, useRef, useState } from "react";

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
  const rootRef = useRef<HTMLDivElement | null>(null);
  const inputId = useId();

  useEffect(() => {
    function closeOnOutsidePointer(event: PointerEvent) {
      if (!rootRef.current || rootRef.current.contains(event.target as Node)) return;
      setIsOpen(false);
    }

    document.addEventListener("pointerdown", closeOnOutsidePointer, true);
    return () => document.removeEventListener("pointerdown", closeOnOutsidePointer, true);
  }, []);

  const filteredOptions = useMemo(() => {
    const search = normalize(value);
    const uniqueOptions = Array.from(new Set(options.filter(Boolean))).sort((left, right) => left.localeCompare(right, "sv-SE"));
    if (!search) return uniqueOptions.slice(0, 30);
    const startsWith = uniqueOptions.filter((option) => normalize(option).startsWith(search));
    const includes = uniqueOptions.filter((option) => !normalize(option).startsWith(search) && normalize(option).includes(search));
    return [...startsWith, ...includes].slice(0, 30);
  }, [options, value]);

  function chooseOption(nextValue: string) {
    onChange(nextValue);
    setIsOpen(false);
  }

  return (
    <div ref={rootRef} className={["field smart-select", className, isOpen ? "is-open" : ""].filter(Boolean).join(" ")}>
      <label htmlFor={inputId}>{label}</label>
      <div className="smart-select-control">
        <input
          id={inputId}
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
            if (event.key === "ArrowDown" && !disabled) {
              event.preventDefault();
              setIsOpen(true);
            }
          }}
        />
        {value && !disabled && (
          <button
            type="button"
            className="smart-select-clear"
            onClick={() => chooseOption("")}
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
          <button type="button" className="smart-select-option muted-option" onMouseDown={(event) => event.preventDefault()} onClick={() => chooseOption("")}>
            {emptyLabel}
          </button>
          {filteredOptions.length === 0 ? (
            <div className="smart-select-option muted-option">No matching option found. You can still type a value.</div>
          ) : (
            filteredOptions.map((option) => (
              <button
                key={option}
                type="button"
                className="smart-select-option"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => chooseOption(option)}
              >
                {option}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
