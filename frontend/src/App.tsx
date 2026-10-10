import { useEffect, useState } from 'react';
import VancouverMap from './VancouverMap';

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

function JourneyControls() {
  return (
    <section className="journey-controls" aria-labelledby="journey-title">
      <div className="journey-heading">
        <div>
          <p className="eyebrow">VANCOUVER · BRITISH COLUMBIA</p>
          <h1 id="journey-title">Your city, in context.</h1>
        </div>
        <span className="coming-badge">Journey tools coming soon</span>
      </div>

      <div className="journey-form" aria-label="Journey controls, coming soon">
        <label className="journey-field">
          <span className="field-marker origin-marker" aria-hidden="true" />
          <span className="field-copy">
            <span className="field-label">ORIGIN</span>
            <span className="field-placeholder">Metro Vancouver</span>
          </span>
          <span className="field-hint">Coming soon</span>
        </label>
        <span className="journey-arrow" aria-hidden="true">→</span>
        <label className="journey-field">
          <span className="field-marker destination-marker" aria-hidden="true" />
          <span className="field-copy">
            <span className="field-label">DESTINATION</span>
            <span className="field-placeholder">City of Vancouver</span>
          </span>
          <span className="field-hint">Coming soon</span>
        </label>
        <div className="mode-control" aria-label="Travel mode, coming soon">
          <span className="field-label">MODE</span>
          <div className="mode-options">
            <button type="button" disabled aria-pressed="false">Drive</button>
            <button type="button" disabled aria-pressed="false">Transit</button>
          </div>
        </div>
        <button className="analyze-button" type="button" disabled>
          <span aria-hidden="true">✦</span>
          Analyze journey
        </button>
      </div>
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
