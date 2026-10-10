import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { Location } from './locationTypes';

type LocationAutocompleteProps = {
  id: string;
  label: string;
  placeholder: string;
  marker: 'origin-marker' | 'destination-marker';
  selectedLocation: Location | null;
  statusMessage?: string;
  statusKind?: 'pending' | 'error' | 'rejected';
  onQueryEdit: () => void;
  onSelect: (location: Location) => void;
};

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 300;

function normalizeQuery(query: string): string {
  return query.trim().replace(/\s+/g, ' ');
}

export default function LocationAutocomplete({
  id,
  label,
  placeholder,
  marker,
  selectedLocation,
  statusMessage,
  statusKind,
  onQueryEdit,
  onSelect,
}: LocationAutocompleteProps) {
  const listId = useId();
  const requestSequence = useRef(0);
  const suppressedQuery = useRef<string | null>(null);
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Location[]>([]);
  const [debouncing, setDebouncing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const normalizedQuery = normalizeQuery(query);

  useEffect(() => {
    const requestId = ++requestSequence.current;
    const queryToSearch = normalizedQuery;
    setSuggestions([]);
    setSearchError(null);
    setActiveIndex(-1);

    if (
      queryToSearch.length < MIN_QUERY_LENGTH ||
      selectedLocation?.name === queryToSearch ||
      suppressedQuery.current === queryToSearch
    ) {
      setDebouncing(false);
      setLoading(false);
      return;
    }

    setDebouncing(true);
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setDebouncing(false);
      setLoading(true);
      setIsOpen(true);
      void (async () => {
        try {
          const params = new URLSearchParams({ q: queryToSearch });
          const response = await fetch(`/api/geocoding/search?${params.toString()}`, {
            signal: controller.signal,
          });
          if (!response.ok) throw new Error('Search unavailable');
          const result: unknown = await response.json();
          if (!Array.isArray(result)) throw new Error('Search unavailable');
          if (requestSequence.current !== requestId) return;
          setSuggestions(result as Location[]);
        } catch {
          if (controller.signal.aborted || requestSequence.current !== requestId) return;
          setSuggestions([]);
          setSearchError('Location search is unavailable. Please try again.');
        } finally {
          if (!controller.signal.aborted && requestSequence.current === requestId) {
            setLoading(false);
          }
        }
      })();
    }, DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [normalizedQuery, selectedLocation]);

  function handleChange(value: string) {
    requestSequence.current += 1;
    suppressedQuery.current = null;
    setQuery(value);
    setSuggestions([]);
    setSearchError(null);
    setActiveIndex(-1);
    const canSearch = normalizeQuery(value).length >= MIN_QUERY_LENGTH;
    setDebouncing(canSearch);
    setIsOpen(canSearch);
    onQueryEdit();
  }

  function selectSuggestion(location: Location) {
    requestSequence.current += 1;
    suppressedQuery.current = normalizeQuery(location.name);
    setQuery(location.name);
    setSuggestions([]);
    setSearchError(null);
    setLoading(false);
    setActiveIndex(-1);
    setIsOpen(false);
    onSelect(location);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' && suggestions.length > 0) {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((current) => (current + 1) % suggestions.length);
    } else if (event.key === 'ArrowUp' && suggestions.length > 0) {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((current) => (current <= 0 ? suggestions.length - 1 : current - 1));
    } else if (event.key === 'Enter' && isOpen && activeIndex >= 0) {
      event.preventDefault();
      const activeSuggestion = suggestions[activeIndex];
      if (activeSuggestion) selectSuggestion(activeSuggestion);
    } else if (event.key === 'Escape') {
      setIsOpen(false);
      setActiveIndex(-1);
    }
  }

  const showSuggestions = Boolean(
    isOpen && !debouncing && (loading || searchError || suggestions.length > 0 || normalizedQuery.length >= MIN_QUERY_LENGTH),
  );

  return (
    <div className="location-autocomplete">
      <div className={`journey-field ${statusKind ? `field-${statusKind}` : ''}`}>
        <span className={`field-marker ${marker}`} aria-hidden="true" />
        <label className="field-copy" htmlFor={id}>
          <span className="field-label">{label}</span>
          <input
            id={id}
            className="location-input"
            type="text"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={showSuggestions}
            aria-controls={listId}
            aria-activedescendant={activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined}
            autoComplete="off"
            placeholder={placeholder}
            value={query}
            onChange={(event) => handleChange(event.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (normalizedQuery.length >= MIN_QUERY_LENGTH && (suggestions.length > 0 || loading || searchError)) {
                setIsOpen(true);
              }
            }}
            onBlur={(event) => {
              const wrapper = event.currentTarget.closest('.location-autocomplete');
              if (!wrapper?.contains(event.relatedTarget as Node | null)) {
                setIsOpen(false);
              }
            }}
          />
        </label>
        {loading && <span className="field-hint" role="status">Searching…</span>}
        {!loading && selectedLocation && <span className="field-hint selected-hint">Selected</span>}
      </div>

      {statusMessage && (
        <p className={`location-feedback feedback-${statusKind ?? 'error'}`} role="status" aria-live="polite">
          {statusMessage}
        </p>
      )}

      {showSuggestions && (
        <ul className="suggestion-list" id={listId} role="listbox" aria-label={`${label.toLowerCase()} suggestions`}>
          {loading && <li className="suggestion-message" role="status">Searching locations…</li>}
          {!loading && searchError && <li className="suggestion-message suggestion-error" role="status">{searchError}</li>}
          {!loading && !searchError && suggestions.length === 0 && (
            <li className="suggestion-message" role="status">No matching locations found.</li>
          )}
          {!loading && !searchError && suggestions.map((location, index) => (
            <li
              id={`${listId}-option-${index}`}
              className={`suggestion-option ${index === activeIndex ? 'suggestion-active' : ''}`}
              key={`${location.provider_id ?? `${location.latitude},${location.longitude}`}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selectSuggestion(location)}
              onMouseEnter={() => setActiveIndex(index)}
            >
              <span className="suggestion-name">{location.name}</span>
              {location.address && <span className="suggestion-address">{location.address}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
