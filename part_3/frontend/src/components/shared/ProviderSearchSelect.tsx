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
  helperText = "Search organization name and select one result.",
}: ProviderSearchSelectProps) {
  const [query, setQuery] = useState("");
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<ProviderSummary | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

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
    const timeout = window.setTimeout(async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await searchProviders({ q: searchText || undefined, limit: 10 });
        if (requestIdRef.current !== requestId) return;
        setProviders(result.items);
      } catch (err) {
        if (requestIdRef.current !== requestId) return;
        setError(err instanceof Error ? err.message : "Providers could not be loaded.");
      } finally {
        if (requestIdRef.current === requestId) setIsLoading(false);
      }
    }, 220);

    return () => window.clearTimeout(timeout);
  }, [query]);

  const selectionLabel = useMemo(() => {
    if (selectedProvider) return `${selectedProvider.utbildningsanordnare} · ID ${providerId(selectedProvider)}`;
    if (value) return `Selected provider ID ${value}`;
    return "No organization selected";
  }, [selectedProvider, value]);

  function selectProvider(provider: ProviderSummary) {
    setSelectedProvider(provider);
    setQuery(provider.utbildningsanordnare);
    setIsOpen(false);
    onChange(providerId(provider), provider);
  }

  function clearProvider() {
    setSelectedProvider(null);
    setQuery("");
    setIsOpen(true);
    onChange("", null);
  }

  return (
    <label className={`field provider-picker${isOpen ? " is-open" : ""}`}>
      <span>{label}</span>
      <div className="provider-combobox">
        <input
          value={query}
          required={required && !value}
          autoComplete="off"
          placeholder="Search provider organization"
          aria-label={`${label} search`}
          onFocus={() => setIsOpen(true)}
          onChange={(event) => {
            setQuery(event.target.value);
            setIsOpen(true);
            if (value) onChange("", null);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") setIsOpen(false);
          }}
        />
        {value && (
          <button type="button" className="provider-clear" onClick={clearProvider} aria-label="Clear selected provider">
            Clear
          </button>
        )}
      </div>
      <input type="hidden" value={value} required={required} readOnly />
      {helperText && <small className="field-help">{helperText}</small>}
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
          {isLoading && <div className="provider-option muted">Searching...</div>}
          {error && <div className="provider-option error-text">{error}</div>}
          {!isLoading && !error && providers.length === 0 && <div className="provider-option muted">No matches found.</div>}
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
