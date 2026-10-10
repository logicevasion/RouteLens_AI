import { useEffect, useRef, useState } from 'react';
import VancouverMap from './VancouverMap';
import LocationAutocomplete from './LocationAutocomplete';
import type { DestinationValidation, Location } from './locationTypes';

type BackendStatus = 'checking' | 'connected' | 'unavailable';

const statusLabels: Record<BackendStatus, string> = {
  checking: 'Checking backend',
  connected: 'Backend connected',
  unavailable: 'Backend unavailable',
};

const intelligenceSections = [
  {
    title: 'Destination conditions',
    icon: 'cloud',
    message: 'Conditions will appear here',
  },
  {
    title: 'Road and route context',
    icon: 'route',
    message: 'Road context available after journey selection',
  },
  {
    title: 'Transit context',
    icon: 'transit',
    message: 'Service alerts available after journey selection',
  },
  {
    title: 'Camera observations',
    icon: 'camera',
    message: 'Camera observations are not yet available',
  },
  {
    title: 'AI journey briefing',
    icon: 'spark',
    message: 'Analysis not yet available',
  },
] as const;

function SectionIcon({ name }: { name: (typeof intelligenceSections)[number]['icon'] }) {
  const common = {
    width: 17,
    height: 17,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.7,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true as const,
  };

  switch (name) {
    case 'cloud':
      return <svg {...common}><path d="M20 16.2A4.8 4.8 0 0 0 18 7h-1.2A7 7 0 1 0 4 16.3" /><path d="M8 19h.01M12 19h.01M16 19h.01" /></svg>;
    case 'route':
      return <svg {...common}><circle cx="6" cy="18" r="2" /><circle cx="18" cy="6" r="2" /><path d="M8 18h3a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3" /></svg>;
    case 'transit':
      return <svg {...common}><rect x="5" y="3" width="14" height="16" rx="3" /><path d="M8 19l-2 2m10-2 2 2M8 7h8M8 12h.01M16 12h.01M8 16h8" /></svg>;
    case 'camera':
      return <svg {...common}><path d="M14 5h-4l-2 3H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-3z" /><circle cx="12" cy="13" r="3" /></svg>;
    case 'spark':
      return <svg {...common}><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z" /><path d="m19 15 1 2 2 1-2 1-1 2-1-2-2-1 2-1z" /></svg>;
  }
}

type DestinationFeedback = {
  kind: 'pending' | 'error' | 'rejected';
  message: string;
};

function JourneyControls() {
  const [origin, setOrigin] = useState<Location | null>(null);
  const [destination, setDestination] = useState<Location | null>(null);
  const [destinationFeedback, setDestinationFeedback] = useState<DestinationFeedback | null>(null);
  const validationSequence = useRef(0);
  const validationController = useRef<AbortController | null>(null);

  useEffect(() => () => validationController.current?.abort(), []);

  function invalidateDestination() {
    validationSequence.current += 1;
    validationController.current?.abort();
    validationController.current = null;
    setDestination(null);
    setDestinationFeedback(null);
  }

  async function validateDestination(candidate: Location) {
    validationSequence.current += 1;
    const requestId = validationSequence.current;
    validationController.current?.abort();
    const controller = new AbortController();
    validationController.current = controller;
    setDestination(null);
    setDestinationFeedback({ kind: 'pending', message: 'Checking City of Vancouver boundary…' });

    try {
      const response = await fetch('/api/locations/validate-destination', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(candidate),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Validation unavailable');
      const result: unknown = await response.json();
      if (
        typeof result !== 'object' || result === null ||
        !('valid' in result) || typeof result.valid !== 'boolean' ||
        !('reason' in result) || (result.reason !== null && typeof result.reason !== 'string')
      ) throw new Error('Validation unavailable');
      const validation = result as DestinationValidation;
      if (validationSequence.current !== requestId) return;

      if (validation.valid) {
        setDestination(candidate);
        setDestinationFeedback(null);
      } else {
        setDestination(null);
        setDestinationFeedback({
          kind: 'rejected',
          message: validation.reason ?? 'Choose a destination inside the City of Vancouver.',
        });
      }
    } catch {
      if (controller.signal.aborted || validationSequence.current !== requestId) return;
      setDestination(null);
      setDestinationFeedback({
        kind: 'error',
        message: 'Destination could not be verified. Please try again.',
      });
    }
  }

  return (
    <section className="journey-controls" aria-labelledby="journey-title">
      <div className="journey-heading">
        <div>
          <p className="eyebrow">VANCOUVER · BRITISH COLUMBIA</p>
          <h1 id="journey-title">Your city, in context.</h1>
        </div>
        <span className="coming-badge">Route planning coming next</span>
      </div>

      <div className="journey-form" aria-label="Journey location inputs">
        <LocationAutocomplete
          id="journey-origin"
          label="ORIGIN"
          placeholder="Search Metro Vancouver"
          marker="origin-marker"
          selectedLocation={origin}
          onQueryEdit={() => setOrigin(null)}
          onSelect={setOrigin}
        />
        <span className="journey-arrow" aria-hidden="true">→</span>
        <LocationAutocomplete
          id="journey-destination"
          label="DESTINATION"
          placeholder="Search City of Vancouver"
          marker="destination-marker"
          selectedLocation={destination}
          statusKind={destinationFeedback?.kind}
          statusMessage={destinationFeedback?.message}
          onQueryEdit={invalidateDestination}
          onSelect={(candidate) => void validateDestination(candidate)}
        />
        <div className="mode-control" aria-label="Travel mode">
          <span className="field-label">MODE</span>
          <div className="mode-options">
            <button className="mode-active" type="button" disabled aria-pressed="true">Drive</button>
            <button type="button" disabled aria-pressed="false">Transit</button>
          </div>
        </div>
        <button className="analyze-button" type="button" disabled>
          <span aria-hidden="true">✦</span>
          Analyze journey
        </button>
      </div>
      {origin && destination && (
        <p className="selection-readiness" role="status">
          Origin and destination selected — route planning coming next.
        </p>
      )}
    </section>
  );
}

function IntelligencePanel() {
  return (
    <aside className="intelligence-panel" aria-labelledby="intelligence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">JOURNEY INTELLIGENCE</p>
          <h2 id="intelligence-title">Your journey</h2>
        </div>
        <span className="panel-status"><span /> Waiting for a journey</span>
      </div>

      <div className="journey-overview">
        <div className="overview-route" aria-hidden="true">
          <span className="overview-dot" />
          <span className="overview-line" />
          <span className="overview-pin" />
        </div>
        <div>
          <h3>No journey selected</h3>
          <p>Choose an origin and destination to see relevant city context.</p>
        </div>
      </div>

      <div className="intelligence-sections">
        {intelligenceSections.map((section) => (
          <section className="intelligence-section" key={section.title}>
            <div className="section-heading">
              <span className="section-icon"><SectionIcon name={section.icon} /></span>
              <h3>{section.title}</h3>
              <span className="section-chevron" aria-hidden="true">⌄</span>
            </div>
            <p className="empty-state">{section.message}</p>
          </section>
        ))}
      </div>
      <p className="panel-note">Live city information has not been loaded.</p>
    </aside>
  );
}

export default function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');

  useEffect(() => {
    const controller = new AbortController();

    async function checkBackend() {
      try {
        const response = await fetch('/api/health', { signal: controller.signal });
        if (!response.ok) throw new Error(`Health request returned ${response.status}`);

        const body: unknown = await response.json();
        const isHealthy =
          typeof body === 'object' && body !== null && 'status' in body && body.status === 'ok';
        setBackendStatus(isHealthy ? 'connected' : 'unavailable');
      } catch {
        if (!controller.signal.aborted) setBackendStatus('unavailable');
      }
    }

    void checkBackend();
    return () => controller.abort();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="RouteLens AI home">
          <span className="brand-mark" aria-hidden="true"><span /><span /><span /></span>
          <span>RouteLens<span className="brand-ai">AI</span></span>
        </a>
        <div className="topbar-meta">
          <span className="region-label"><span className="region-dot" /> Vancouver, BC</span>
          <div className={`backend-status status-${backendStatus}`} role="status" aria-live="polite">
            <span className="backend-dot" aria-hidden="true" />
            {statusLabels[backendStatus]}
          </div>
        </div>
      </header>

      <JourneyControls />

      <div className="workspace">
        <div className="map-workspace">
          <div className="map-caption"><span className="map-caption-dot" /> VANCOUVER OVERVIEW</div>
          <VancouverMap />
        </div>
        <IntelligencePanel />
      </div>
    </main>
  );
}
