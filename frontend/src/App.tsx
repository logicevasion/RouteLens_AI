import { useEffect, useRef, useState } from 'react';
import VancouverMap from './VancouverMap';
import LocationAutocomplete from './LocationAutocomplete';
import type { DestinationValidation, Location } from './locationTypes';
import RoadAheadPanel from './RoadAheadPanel';
import DestinationWeatherPanel from './DestinationWeatherPanel';
import DestinationCameraPanel from './DestinationCameraPanel';
import { fetchDestinationCamera, isCurrentCameraRequest } from './cameras';
import type { CameraState } from './cameras';
import { buildAnalysisRequest, isAnalysisReady, isCurrentAnalysisRequest, normalizeJourneyAnalysis } from './roadAhead';
import type { AnalysisFinding, AnalysisState, DriveBCAnalysisFinding, RegionalEvent } from './analysisTypes';
import {
  routeColor,
  type DrivingRoutesRequest,
  type DrivingRoutesResponse,
  type RouteCandidate,
  type RouteRequestState,
  type RoutingApiError,
} from './routeTypes';

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
    title: 'Destination cameras',
    icon: 'camera',
    message: '',
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

const initialRouteState: RouteRequestState = {
  status: 'idle', candidates: [], selectedRoute: null, error: null, fitKey: 0,
};

const initialAnalysisState: AnalysisState = { status: 'idle', result: null, error: null };
const noAnalysisFindings: AnalysisFinding[] = [];
const noDriveBCFindings: DriveBCAnalysisFinding[] = [];
const noRegionalEvents: RegionalEvent[] = [];

function normalizeRoutes(value: unknown): DrivingRoutesResponse | null {
  if (typeof value !== 'object' || value === null || !('routes' in value) || !Array.isArray(value.routes)) {
    return null;
  }
  const routes = value.routes.filter((item): item is RouteCandidate => {
    if (typeof item !== 'object' || item === null) return false;
    const route = item as Partial<RouteCandidate>;
    return typeof route.id === 'string' && route.id.length > 0 &&
      typeof route.geometry === 'object' && route.geometry !== null &&
      route.geometry.type === 'LineString' && Array.isArray(route.geometry.coordinates) &&
      route.geometry.coordinates.length >= 2 && route.geometry.coordinates.every((point) =>
        Array.isArray(point) && point.length === 2 && Number.isFinite(point[0]) && Number.isFinite(point[1]) &&
        point[0] >= -180 && point[0] <= 180 && point[1] >= -90 && point[1] <= 90,
      ) && typeof route.distance_meters === 'number' && Number.isFinite(route.distance_meters) &&
      route.distance_meters > 0 && typeof route.duration_seconds === 'number' &&
      Number.isFinite(route.duration_seconds) && route.duration_seconds > 0 &&
      (route.label === undefined || route.label === null || typeof route.label === 'string');
  });
  return { routes };
}

function formatDistance(meters: number): string {
  const kilometres = meters / 1000;
  return `${kilometres.toLocaleString(undefined, { maximumFractionDigits: 1 })} km`;
}

function formatDuration(seconds: number): string {
  const minutes = Math.max(1, Math.round(seconds / 60));
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return hours > 0 ? `approximately ${hours} hr ${remainder} min` : `approximately ${minutes} min`;
}

function routingErrorMessage(error: RoutingApiError | null, status: number): string {
  switch (error?.detail?.code) {
    case 'no_route_found':
      return 'No drivable route was found for these locations. Try a different starting point.';
    case 'unsupported_destination':
      return error.detail.message ?? 'Choose a destination inside the City of Vancouver.';
    case 'routing_rate_limited':
      return 'Route service is busy. Please wait a moment and try again.';
    case 'routing_timeout':
      return 'Route service took too long to respond. Please try again.';
    case 'routing_not_configured':
    case 'routing_authentication_failed':
    case 'routing_provider_unavailable':
      return 'Driving routes are temporarily unavailable. Please try again.';
    default:
      return status >= 500
        ? 'Driving routes are temporarily unavailable. Please try again.'
        : 'Could not retrieve routes for this journey. Please try again.';
  }
}

type JourneyControlsProps = {
  origin: Location | null;
  destination: Location | null;
  onOriginChange: (location: Location | null) => void;
  onDestinationChange: (location: Location | null) => void;
  routeState: RouteRequestState;
  canFindRoutes: boolean;
  canAnalyze: boolean;
  analysisState: AnalysisState;
  onJourneyInputEdit: () => void;
  onFindRoutes: () => void;
  onAnalyze: () => void;
};

function JourneyControls({ origin, destination, onOriginChange, onDestinationChange, routeState, canFindRoutes, canAnalyze, analysisState, onJourneyInputEdit, onFindRoutes, onAnalyze }: JourneyControlsProps) {
  const [destinationFeedback, setDestinationFeedback] = useState<DestinationFeedback | null>(null);
  const validationSequence = useRef(0);
  const validationController = useRef<AbortController | null>(null);

  useEffect(() => () => validationController.current?.abort(), []);

  function invalidateDestination() {
    onJourneyInputEdit();
    validationSequence.current += 1;
    validationController.current?.abort();
    validationController.current = null;
    onDestinationChange(null);
    setDestinationFeedback(null);
  }

  async function validateDestination(candidate: Location) {
    onJourneyInputEdit();
    validationSequence.current += 1;
    const requestId = validationSequence.current;
    validationController.current?.abort();
    const controller = new AbortController();
    validationController.current = controller;
    onDestinationChange(null);
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
        onDestinationChange(candidate);
        setDestinationFeedback(null);
      } else {
        onDestinationChange(null);
        setDestinationFeedback({
          kind: 'rejected',
          message: validation.reason ?? 'Choose a destination inside the City of Vancouver.',
        });
      }
    } catch {
      if (controller.signal.aborted || validationSequence.current !== requestId) return;
      onDestinationChange(null);
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
        <span className="coming-badge">DRIVE ROUTE CONTEXT</span>
      </div>

      <div className="journey-form" aria-label="Journey location inputs">
        <LocationAutocomplete
          id="journey-origin"
          label="ORIGIN"
          placeholder="Search Metro Vancouver"
          marker="origin-marker"
          selectedLocation={origin}
          onQueryEdit={() => { onOriginChange(null); onJourneyInputEdit(); }}
          onSelect={onOriginChange}
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
        <button
          className="find-routes-button"
          type="button"
          disabled={!canFindRoutes || routeState.status === 'loading'}
          onClick={onFindRoutes}
        >
          {routeState.status === 'loading' ? <><span className="map-spinner" aria-hidden="true" /> Finding routes…</> : 'Find routes'}
        </button>
        <button className="analyze-button" type="button" disabled={!canAnalyze} onClick={onAnalyze}>
          {analysisState.status === 'loading' ? <><span className="map-spinner" aria-hidden="true" /> Analyzing…</> : <><span aria-hidden="true">✦</span> Analyze journey</>}
        </button>
      </div>
      <p className="route-request-status" role={routeState.status === 'error' ? 'alert' : 'status'} aria-live="polite">
        {routeState.status === 'loading' && 'Requesting driving alternatives…'}
        {routeState.status === 'empty' && 'No usable routes were returned. Check the locations and try again.'}
        {routeState.status === 'error' && routeState.error}
        {routeState.status === 'ready' && `${routeState.candidates.length} ${routeState.candidates.length === 1 ? 'route' : 'routes'} available. Select one below.`}
        {analysisState.status === 'loading' && 'Checking road sources and destination weather for the selected route. This may take a little while.'}
        {analysisState.status === 'error' && analysisState.error}
      </p>
    </section>
  );
}

type IntelligencePanelProps = {
  routeState: RouteRequestState;
  onSelectRoute: (route: RouteCandidate) => void;
  analysisState: AnalysisState;
  cameraState: CameraState;
  selectedEventId: string | null;
  onSelectFinding: (eventId: string) => void;
};

function IntelligencePanel({ routeState, onSelectRoute, analysisState, cameraState, selectedEventId, onSelectFinding }: IntelligencePanelProps) {
  return (
    <aside className="intelligence-panel" aria-labelledby="intelligence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">JOURNEY INTELLIGENCE</p>
          <h2 id="intelligence-title">Your journey</h2>
        </div>
        <span className="panel-status"><span /> {routeState.selectedRoute ? 'Route selected' : routeState.status === 'ready' ? 'Choose a route' : 'Waiting for a journey'}</span>
      </div>

      <div className="journey-overview">
        <div className="overview-route" aria-hidden="true">
          <span className="overview-dot" />
          <span className="overview-line" />
          <span className="overview-pin" />
        </div>
        <div>
          <h3>{routeState.selectedRoute ? 'Route selected' : routeState.status === 'ready' ? 'Choose a route' : 'No journey selected'}</h3>
          <p>{routeState.selectedRoute
            ? `${routeState.selectedRoute.label ?? 'Selected driving route'} is ready to analyze.`
            : routeState.status === 'ready'
              ? 'Select the candidate closest to your planned journey.'
              : 'Choose an origin and destination, then find driving routes.'}</p>
        </div>
      </div>

      {(routeState.status === 'loading' || routeState.status === 'ready' || routeState.status === 'empty' || routeState.status === 'error') && (
        <section className="route-selection" aria-labelledby="route-selection-title">
          <div className="route-selection-heading">
            <div>
              <p className="eyebrow">DRIVING ALTERNATIVES</p>
              <h3 id="route-selection-title">Choose your route</h3>
            </div>
            {routeState.status === 'ready' && <span>{routeState.candidates.length} available</span>}
          </div>
          {routeState.status === 'loading' && <p className="route-list-message" role="status">Loading route alternatives…</p>}
          {routeState.status === 'empty' && <p className="route-list-message">No usable routes were found. You can adjust your locations and try again.</p>}
          {routeState.status === 'error' && <p className="route-list-message">{routeState.error}</p>}
          {routeState.status === 'ready' && (
            <div className="route-candidate-list" role="group" aria-label="Driving route alternatives">
              {routeState.candidates.map((route, index) => {
                const selected = routeState.selectedRoute?.id === route.id;
                const label = route.label?.trim() || `Route ${index + 1}`;
                return (
                  <button
                    className={`route-candidate${selected ? ' route-candidate-selected' : ''}`}
                    type="button"
                    key={route.id}
                    aria-pressed={selected}
                    aria-label={`${label}, ${formatDistance(route.distance_meters)}, estimated driving time ${formatDuration(route.duration_seconds)}${selected ? ', selected' : ''}`}
                    onClick={() => onSelectRoute(route)}
                  >
                    <span className={`candidate-swatch${selected ? ' candidate-swatch-selected' : ''}`} style={{ backgroundColor: selected ? '#51d5cc' : routeColor(route.id) }} aria-hidden="true" />
                    <span className="candidate-copy">
                      <span className="candidate-title">{label}</span>
                      <span className="candidate-metadata">{formatDistance(route.distance_meters)} · {formatDuration(route.duration_seconds)} driving</span>
                    </span>
                    <span className="candidate-selection">{selected ? 'Selected' : 'Select'}</span>
                  </button>
                );
              })}
            </div>
          )}
        </section>
      )}

      <div className="intelligence-sections">
        {intelligenceSections.map((section) => section.title === 'Destination conditions' ? (
          <DestinationWeatherPanel key={section.title} analysis={analysisState} />
        ) : section.title === 'Destination cameras' ? (
          <DestinationCameraPanel key={section.title} camera={cameraState} />
        ) : section.title === 'Road and route context' ? (
          <RoadAheadPanel key={section.title} analysis={analysisState} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} />
        ) : (
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
      {analysisState.status !== 'success' && <p className="panel-note">Weather, road findings, and the regional DriveBC map layer load only when you choose Analyze journey.</p>}
    </aside>
  );
}

export default function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const [routeState, setRouteState] = useState<RouteRequestState>(initialRouteState);
  const [origin, setOrigin] = useState<Location | null>(null);
  const [destination, setDestination] = useState<Location | null>(null);
  const [analysisState, setAnalysisState] = useState<AnalysisState>(initialAnalysisState);
  const [cameraState, setCameraState] = useState<CameraState>({ status: 'idle' });
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const routingSequence = useRef(0);
  const routingController = useRef<AbortController | null>(null);
  const activePair = useRef<string | null>(null);
  const analysisSequence = useRef(0);
  const analysisController = useRef<AbortController | null>(null);
  const activeAnalysisKey = useRef<string | null>(null);
  const cameraSequence = useRef(0);
  const cameraController = useRef<AbortController | null>(null);
  const activeCameraKey = useRef<string | null>(null);

  const canFindRoutes = Boolean(origin && destination && routeState.status !== 'loading');
  const selectedRoute = routeState.status === 'ready' ? routeState.selectedRoute : null;
  const canAnalyze = isAnalysisReady(origin, destination, selectedRoute) && analysisState.status !== 'loading';

  function invalidateAnalysis() {
    analysisSequence.current += 1;
    analysisController.current?.abort();
    analysisController.current = null;
    activeAnalysisKey.current = null;
    cameraSequence.current += 1;
    cameraController.current?.abort();
    cameraController.current = null;
    activeCameraKey.current = null;
    setCameraState({ status: 'idle' });
    setAnalysisState(initialAnalysisState);
    setSelectedEventId(null);
  }

  function invalidateRoutes() {
    invalidateAnalysis();
    routingSequence.current += 1;
    routingController.current?.abort();
    routingController.current = null;
    activePair.current = null;
    setRouteState({ status: 'idle', candidates: [], selectedRoute: null, error: null, fitKey: routeState.fitKey });
  }

  async function findRoutes() {
    if (!origin || !destination) return;
    invalidateAnalysis();
    const request: DrivingRoutesRequest = { origin, destination };
    const requestPair = JSON.stringify(request);
    if (routingController.current && activePair.current === requestPair) return;

    routingSequence.current += 1;
    const requestId = routingSequence.current;
    routingController.current?.abort();
    const controller = new AbortController();
    routingController.current = controller;
    activePair.current = requestPair;
    setRouteState({ status: 'loading', candidates: [], selectedRoute: null, error: null, fitKey: routeState.fitKey });

    try {
      const response = await fetch('/api/routes/driving', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      });
      if (!response.ok) {
        let error: RoutingApiError | null = null;
        try { error = await response.json() as RoutingApiError; } catch { /* use safe status fallback */ }
        if (routingSequence.current !== requestId) return;
        if (error?.detail?.code === 'no_route_found') {
          setRouteState({ status: 'empty', candidates: [], selectedRoute: null, error: null, fitKey: routeState.fitKey });
        } else {
          setRouteState({ status: 'error', candidates: [], selectedRoute: null, error: routingErrorMessage(error, response.status), fitKey: routeState.fitKey });
        }
        return;
      }

      const normalized = normalizeRoutes(await response.json());
      if (routingSequence.current !== requestId) return;
      if (!normalized) {
        setRouteState({ status: 'error', candidates: [], selectedRoute: null, error: 'Route service returned an unreadable response. Please try again.', fitKey: routeState.fitKey });
      } else if (normalized.routes.length === 0) {
        setRouteState({ status: 'empty', candidates: [], selectedRoute: null, error: null, fitKey: routeState.fitKey });
      } else {
        setRouteState({ status: 'ready', candidates: normalized.routes, selectedRoute: null, error: null, fitKey: routeState.fitKey + 1 });
      }
    } catch {
      if (controller.signal.aborted || routingSequence.current !== requestId) return;
      setRouteState({ status: 'error', candidates: [], selectedRoute: null, error: 'Driving routes are temporarily unavailable. Please try again.', fitKey: routeState.fitKey });
    } finally {
      if (routingSequence.current === requestId) {
        routingController.current = null;
        activePair.current = null;
      }
    }
  }

  function selectRoute(route: RouteCandidate) {
    if (routeState.status === 'ready' && routeState.selectedRoute?.id !== route.id) invalidateAnalysis();
    setRouteState((current) => current.status === 'ready' && current.candidates.some((candidate) => candidate.id === route.id)
      ? { ...current, selectedRoute: current.candidates.find((candidate) => candidate.id === route.id) ?? null }
      : current);
  }

  async function analyzeJourney() {
    if (!origin || !destination || !selectedRoute || !canAnalyze || analysisController.current) return;
    const request = buildAnalysisRequest(origin, destination, selectedRoute);
    const requestKey = JSON.stringify(request);
    analysisSequence.current += 1;
    const requestId = analysisSequence.current;
    const controller = new AbortController();
    analysisController.current = controller;
    activeAnalysisKey.current = requestKey;
    cameraSequence.current += 1;
    cameraController.current?.abort();
    const cameraRequestId = cameraSequence.current;
    const cameraDisplayKey = `${requestKey}:${cameraRequestId}`;
    const cameraControllerValue = new AbortController();
    cameraController.current = cameraControllerValue;
    activeCameraKey.current = requestKey;
    setCameraState({ status: 'loading', requestKey: cameraDisplayKey });
    setAnalysisState({ status: 'loading', result: null, error: null });
    setSelectedEventId(null);

    void fetchDestinationCamera(destination, cameraControllerValue.signal).then((result) => {
      if (!isCurrentCameraRequest(requestKey, activeCameraKey.current, cameraRequestId, cameraSequence.current)) return;
      setCameraState({ status: 'success', requestKey: cameraDisplayKey, result });
    }).catch(() => {
      if (cameraControllerValue.signal.aborted || !isCurrentCameraRequest(requestKey, activeCameraKey.current, cameraRequestId, cameraSequence.current)) return;
      setCameraState({ status: 'error', requestKey: cameraDisplayKey });
    }).finally(() => {
      if (isCurrentCameraRequest(requestKey, activeCameraKey.current, cameraRequestId, cameraSequence.current)) {
        cameraController.current = null;
        activeCameraKey.current = null;
      }
    });

    try {
      const response = await fetch('/api/trips/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Road Ahead analysis is temporarily unavailable. Please try again.');
      const analysis = normalizeJourneyAnalysis(await response.json());
      if (!analysis || analysis.trip.selected_route.candidate_id !== selectedRoute.id) {
        throw new Error('Road Ahead analysis returned an unreadable result. Please analyze this route again.');
      }
      if (!isCurrentAnalysisRequest(requestId, analysisSequence.current, requestKey, activeAnalysisKey.current)) return;
      setAnalysisState({ status: 'success', result: analysis, error: null });
    } catch (error) {
      if (controller.signal.aborted || !isCurrentAnalysisRequest(requestId, analysisSequence.current, requestKey, activeAnalysisKey.current)) return;
      setAnalysisState({ status: 'error', result: null, error: error instanceof Error ? error.message : 'Road Ahead analysis is temporarily unavailable. Please try again.' });
    } finally {
      if (analysisSequence.current === requestId) {
        analysisController.current = null;
        activeAnalysisKey.current = null;
      }
    }
  }

  useEffect(() => () => {
    routingController.current?.abort();
    analysisController.current?.abort();
    cameraController.current?.abort();
  }, []);

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

      <JourneyControls
        origin={origin}
        destination={destination}
        onOriginChange={setOrigin}
        onDestinationChange={setDestination}
        routeState={routeState}
        canFindRoutes={canFindRoutes}
        canAnalyze={canAnalyze}
        analysisState={analysisState}
        onJourneyInputEdit={invalidateRoutes}
        onFindRoutes={() => void findRoutes()}
        onAnalyze={() => void analyzeJourney()}
      />

      <div className="workspace">
        <div className="map-workspace">
          <div className="map-caption"><span className="map-caption-dot" /> VANCOUVER OVERVIEW</div>
          <VancouverMap
            routes={routeState.status === 'ready' ? routeState.candidates : []}
            selectedRouteId={routeState.status === 'ready' ? routeState.selectedRoute?.id ?? null : null}
            fitKey={routeState.fitKey}
            findings={analysisState.status === 'success' ? analysisState.result.findings : noAnalysisFindings}
            drivebcFindings={analysisState.status === 'success' ? analysisState.result.drivebc_findings : noDriveBCFindings}
            regionalEvents={analysisState.status === 'success' ? analysisState.result.regional_events : noRegionalEvents}
            selectedEventId={selectedEventId}
            onSelectEvent={setSelectedEventId}
          />
        </div>
        <IntelligencePanel routeState={routeState} onSelectRoute={selectRoute} analysisState={analysisState} cameraState={cameraState} selectedEventId={selectedEventId} onSelectFinding={setSelectedEventId} />
      </div>
    </main>
  );
}
