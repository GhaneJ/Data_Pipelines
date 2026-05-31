import { useEffect, useMemo, useRef, useState } from "react";
import { searchProviders } from "@/api/providers";
import type { ProviderSummary } from "@/api/types";

interface ProviderSearchSelectProps {
  value: string;
  onChange: (providerId: string, provider: ProviderSummary | null) => void;
  label?: string;
  required?: boolean;
  helperText?: string;
}

const MIN_PROVIDER_SEARCH_LENGTH = 1;
const PROVIDER_RESULT_LIMIT = 50;

function providerId(provider: ProviderSummary): string {
  return String(provider.provider_id);
}

function providerDescription(provider: ProviderSummary): string {
  const years = provider.first_year && provider.last_year ? `${provider.first_year}-${provider.last_year}` : "years unavailable";
  return `${provider.total_applications.toLocaleString("sv-SE")} applications · ${provider.approved_applications.toLocaleString("sv-SE")} approved · ${years}`;
}

export function ProviderSearchSelect({
  value,
  onChange,
  label = "Provider",
  required = false,
  helperText = "Search by provider organization name. Keep typing to narrow the result set.",
}: ProviderSearchSelectProps) {
  const [query, setQuery] = useState("");
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [totalMatches, setTotalMatches] = useState<number | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<ProviderSummary | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const rootRef = useRef<HTMLLabelElement | null>(null);

  useEffect(() => {
    function closeOnOutsidePointer(event: PointerEvent) {
      if (!rootRef.current || rootRef.current.contains(event.target as Node)) return;
      setIsOpen(false);
    }

    document.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => document.removeEventListener("pointerdown", closeOnOutsidePointer);
  }, []);

  useEffect(() => {
    if (!value) {
      setSelectedProvider(null);
      return;
    }
    if (selectedProvider && providerId(selectedProvider) === value) return;

    const match = providers.find((provider) => providerId(provider) === value);
    if (match) {
      setSelectedProvider(match);
      setQuery(match.utbildningsanordnare);
    }
  }, [providers, selectedProvider, value]);

  useEffect(() => {
    const requestId = ++requestIdRef.current;
    const searchText = query.trim();

    if (searchText.length < MIN_PROVIDER_SEARCH_LENGTH) {
      setProviders([]);
      setTotalMatches(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    const timeout = window.setTimeout(async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await searchProviders({ q: searchText, limit: PROVIDER_RESULT_LIMIT });
        if (requestIdRef.current !== requestId) return;
        setProviders(result.items);
        setTotalMatches(typeof result.total === "number" ? result.total : null);
      } catch (err) {
        if (requestIdRef.current !== requestId) return;
        setError(err instanceof Error ? err.message : "Providers could not be loaded.");
      } finally {
        if (requestIdRef.current === requestId) setIsLoading(false);
      }
    }, 180);

    return () => window.clearTimeout(timeout);
  }, [query]);

  const selectionLabel = useMemo(() => {
    if (selectedProvider) return `${selectedProvider.utbildningsanordnare} · ID ${providerId(selectedProvider)}`;
    if (value) return `Selected provider ID ${value}`;
    return "No organization selected";
  }, [selectedProvider, value]);

  function openOptions() {
    if (query.trim().length >= MIN_PROVIDER_SEARCH_LENGTH) setIsOpen(true);
  }

  function selectProvider(provider: ProviderSummary) {
    setSelectedProvider(provider);
    setQuery(provider.utbildningsanordnare);
    setIsOpen(false);
    onChange(providerId(provider), provider);
  }

  function clearProvider() {
    setSelectedProvider(null);
    setQuery("");
    setProviders([]);
    setTotalMatches(null);
    setIsOpen(false);
    onChange("", null);
  }

  const resultSummary = totalMatches === null
    ? null
    : totalMatches > providers.length
      ? `Showing ${providers.length} of ${totalMatches} matching providers. Keep typing to narrow.`
      : `${totalMatches} matching provider${totalMatches === 1 ? "" : "s"}.`;

  return (
    <label ref={rootRef} className={`field provider-picker${isOpen ? " is-open" : ""}`}>
      <span>{label}</span>
      <div className="provider-combobox">
        <input
          value={query}
          required={required && !value}
          autoComplete="off"
          placeholder="Search provider organization"
          aria-label={`${label} search`}
          onFocus={openOptions}
          onClick={openOptions}
          onChange={(event) => {
            const nextQuery = event.target.value;
            setQuery(nextQuery);
            setIsOpen(nextQuery.trim().length >= MIN_PROVIDER_SEARCH_LENGTH);
            if (value) onChange("", null);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setIsOpen(false);
              (event.currentTarget as HTMLInputElement).blur();
            }
          }}
        />
        {value && (
          <button type="button" className="provider-clear" onClick={clearProvider} aria-label="Clear selected provider">
            Clear
          </button>
        )}
      </div>
      {helperText && <small className="field-help">{helperText}</small>}
      <input type="hidden" value={value} required={required} readOnly />
      {selectedProvider && (
        <div className="selected-provider-card" aria-live="polite">
          <strong>{selectionLabel}</strong>
          <span>{providerDescription(selectedProvider)}</span>
        </div>
      )}
      {!selectedProvider && value && (
        <div className="selected-provider-card compact-selection" aria-live="polite">
          <strong>{selectionLabel}</strong>
        </div>
      )}
      {isOpen && (
        <div className="provider-options" role="listbox" aria-label="Provider search results">
          {isLoading && <div className="provider-option muted">Searching providers...</div>}
          {error && <div className="provider-option error-text">{error}</div>}
          {!isLoading && !error && resultSummary && <div className="provider-option provider-result-summary">{resultSummary}</div>}
          {!isLoading && !error && providers.length === 0 && <div className="provider-option muted">No matching provider found.</div>}
          {!isLoading && providers.map((provider) => (
            <button
              key={providerId(provider)}
              type="button"
              className="provider-option"
              onClick={() => selectProvider(provider)}
            >
              <strong>{provider.utbildningsanordnare}</strong>
              <span>{providerDescription(provider)}</span>
            </button>
          ))}
        </div>
      )}
    </label>
  );
}
