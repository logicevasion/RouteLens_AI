import { useEffect, useMemo, useRef, useState } from 'react';
import VancouverMap from './VancouverMap';
import LocationAutocomplete from './LocationAutocomplete';
import type { DestinationValidation, Location } from './locationTypes';
import RoadAheadPanel from './RoadAheadPanel';
import DestinationWeatherPanel from './DestinationWeatherPanel';
import JourneyStageLayout from './JourneyStageLayout';
import { beginJourneyPresentation, initialJourneyPresentation, invalidateJourneyPresentation } from './presentation';
import type { JourneyPresentation } from './presentation';
import { fetchDestinationCamera, fetchNearbyCameras, isCurrentCameraRequest, isCurrentNearbyCameraRequest, shouldRequestSelectedCameraMarker } from './cameras';
import type { CameraState, NearbyCameraState } from './cameras';
import { activeSelectedEventId, buildAnalysisRequest, isAnalysisReady, isCurrentAnalysisRequest, normalizeJourneyAnalysis } from './roadAhead';
import type { AnalysisFinding, AnalysisState, DriveBCAnalysisFinding, RegionalEvent } from './analysisTypes';
import { cameraVisionFailureResult, fetchCameraVision, isCurrentVisionAttempt, retainCurrentCameraVision, startCameraVisionTimeout } from './cameraVision';
import type { JourneyCameraEvidence, JourneyEvidenceState } from './cameraVision';
import { createJourneyAttemptId, deriveCurrentJourneyEvidence } from './journeyEvidence';
import { createCameraOpportunity, serializeBriefingEvidence, startBriefingRequest } from './journeyBriefing';
import type { JourneyBriefingState } from './journeyBriefing';
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
        {routeState.status === 'ready' && `${routeState.candidates.length} ${routeState.candidates.length === 1 ? 'route' : 'routes'} available. Select one to continue.`}
        {analysisState.status === 'loading' && 'Checking road sources and destination weather for the selected route. This may take a little while.'}
        {analysisState.status === 'error' && analysisState.error}
      </p>
    </section>
  );
}

type IntelligencePanelProps = {
  stage: 'plan' | 'understand';
  routeState: RouteRequestState;
  onSelectRoute: (route: RouteCandidate) => void;
  analysisState: AnalysisState;
  selectedEventId: string | null;
  onSelectFinding: (eventId: string) => void;
};

function BriefingCard({ briefingState }: { briefingState: JourneyBriefingState }) {
  return <section className={`briefing-card briefing-card-${briefingState.status}`} aria-labelledby="briefing-title" aria-live="polite">
    <div className="briefing-heading"><div><p className="eyebrow">EXPERIMENTAL · AI ASSISTED · SOURCE GROUNDED</p><h3 id="briefing-title">AI Journey Briefing</h3></div>
      {briefingState.status === 'available' && <span className="briefing-badge">Ready</span>}
    </div>
    {briefingState.status === 'available' ? <>
      <p className="briefing-overview">{briefingState.result.overview}</p>
      {briefingState.result.highlights.length === 3 && <ul className="briefing-highlights">{briefingState.result.highlights.map((highlight, index) => <li key={`${highlight.category}-${index}`}>
        <span className={`briefing-category briefing-category-${highlight.category}`}>{highlight.category === 'camera' ? 'Camera conditions' : highlight.category === 'weather' ? 'Destination weather' : 'Construction'}</span><span>{highlight.text}</span>
      </li>)}</ul>}
      {briefingState.result.limitations.slice(0, 2).length > 0 && <p className="briefing-limitations">{briefingState.result.limitations.slice(0, 2).join(' ')}</p>}
    </> : briefingState.status === 'waiting_for_evidence' ? <p className="briefing-message">Preparing the available journey evidence for your briefing…</p>
      : briefingState.status === 'in_progress' ? <p className="briefing-message">Generating a briefing from the available journey evidence…</p>
        : briefingState.status === 'insufficient_evidence' ? <p className="briefing-message">Available source evidence is not sufficient to prepare a briefing. Deterministic journey evidence remains available.</p>
          : briefingState.status === 'idle' ? <p className="briefing-message">The experimental briefing appears here when available. Deterministic journey evidence remains available independently.</p>
            : <p className="briefing-message">The briefing is unavailable right now. Deterministic journey evidence remains available.</p>}
  </section>;
}

function IntelligencePanel({ stage, routeState, onSelectRoute, analysisState, selectedEventId, onSelectFinding }: IntelligencePanelProps) {
  if (stage === 'understand') return <RoadAheadPanel analysis={analysisState} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} presentation="route" />;
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

      {stage === 'plan' && routeState.status !== 'ready' && <p className="stage-guidance">Choose an origin and a Vancouver destination, then find routes. Select the route closest to your planned journey before analyzing it.</p>}

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
                    <span className={`candidate-swatch${selected ? ' candidate-swatch-selected' : ''}`} style={{ backgroundColor: selected ? '#B794F6' : routeColor(route.id) }} aria-hidden="true" />
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

    </aside>
  );
}

export default function App() {
  const [presentation, setPresentation] = useState<JourneyPresentation>(initialJourneyPresentation);
  const { stage } = presentation;
  const analysisAt = presentation.analysisAt ?? '';
  const appShellRef = useRef<HTMLElement | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const [routeState, setRouteState] = useState<RouteRequestState>(initialRouteState);
  const [origin, setOrigin] = useState<Location | null>(null);
  const [destination, setDestination] = useState<Location | null>(null);
  const [journeyEvidenceState, setJourneyEvidenceState] = useState<JourneyEvidenceState>({ attempt_id: null, lifecycle_id: null, trip: null, analysis: initialAnalysisState, camera_vision: null });
  // Internal 10D handoff: only a validated BriefingResultV1 is stored in the available states.
  const [journeyBriefingState, setJourneyBriefingState] = useState<JourneyBriefingState>({ status: 'idle' });
  const analysisState = journeyEvidenceState.analysis;
  function setAnalysisState(next: AnalysisState) {
    setJourneyEvidenceState((current) => ({ ...current, analysis: next }));
  }
  function setJourneyCameraEvidence(next: JourneyCameraEvidence | null | ((current: JourneyCameraEvidence | null) => JourneyCameraEvidence | null)) {
    setJourneyEvidenceState((current) => ({
      ...current,
      camera_vision: typeof next === 'function' ? next(current.camera_vision) : next,
    }));
  }
  const [cameraState, setCameraState] = useState<CameraState>({ status: 'idle' });
  const [nearbyCameraState, setNearbyCameraState] = useState<NearbyCameraState>({ status: 'idle' });
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const routingSequence = useRef(0);
  const routingController = useRef<AbortController | null>(null);
  const activePair = useRef<string | null>(null);
  const analysisSequence = useRef(0);
  const analysisController = useRef<AbortController | null>(null);
  const activeAnalysisKey = useRef<string | null>(null);
  const visionSequence = useRef(0);
  const visionController = useRef<AbortController | null>(null);
  const activeVisionKey = useRef<string | null>(null);
  const cameraSequence = useRef(0);
  const cameraController = useRef<AbortController | null>(null);
  const activeCameraKey = useRef<string | null>(null);
  const nearbyCameraSequence = useRef(0);
  const selectedGalleryIntersectionId = useRef<string | null>(null);
  const nearbyCameraResult = useRef<{ requestKey: string; cameras: string[] } | null>(null);
  const briefingController = useRef<AbortController | null>(null);
  const briefingAttempt = useRef<string | null>(null);
  const cameraOpportunityCancel = useRef<(() => void) | null>(null);

  const canFindRoutes = Boolean(origin && destination && routeState.status !== 'loading');
  const selectedRoute = routeState.status === 'ready' ? routeState.selectedRoute : null;
  const currentTrip = useMemo(
    () => origin && destination && selectedRoute ? buildAnalysisRequest(origin, destination, selectedRoute) : null,
    [origin, destination, selectedRoute],
  );
  // Phase 10's internal handoff is this typed, current-attempt value; it has no UI or request side effects.
  const journeyEvidenceBundle = useMemo(
    () => deriveCurrentJourneyEvidence(journeyEvidenceState, currentTrip, new Date().toISOString()),
    [journeyEvidenceState, currentTrip],
  );
  void journeyEvidenceBundle;
  void journeyBriefingState;
  const canAnalyze = isAnalysisReady(origin, destination, selectedRoute) && analysisState.status !== 'loading';
  const activeSelectedEvent = analysisState.status === 'success'
    ? activeSelectedEventId(selectedEventId, analysisState.result.findings, analysisState.result.drivebc_findings, analysisState.result.regional_events)
    : null;

  function invalidateAnalysis() {
    setPresentation(invalidateJourneyPresentation());
    briefingAttempt.current = null;
    briefingController.current?.abort();
    briefingController.current = null;
    cameraOpportunityCancel.current?.();
    cameraOpportunityCancel.current = null;
    setJourneyBriefingState({ status: 'idle' });
    analysisSequence.current += 1;
    analysisController.current?.abort();
    analysisController.current = null;
    activeAnalysisKey.current = null;
    visionSequence.current += 1;
    visionController.current?.abort();
    visionController.current = null;
    activeVisionKey.current = null;
    setJourneyEvidenceState({ attempt_id: null, lifecycle_id: null, trip: null, analysis: initialAnalysisState, camera_vision: null });
    setJourneyCameraEvidence(null);
    cameraSequence.current += 1;
    nearbyCameraSequence.current += 1;
    cameraController.current?.abort();
    cameraController.current = null;
    activeCameraKey.current = null;
    setCameraState({ status: 'idle' });
    setNearbyCameraState({ status: 'idle' });
    selectedGalleryIntersectionId.current = null;
    nearbyCameraResult.current = null;
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
    const attemptStartedAt = new Date().toISOString();
    setPresentation(beginJourneyPresentation(presentation, true, attemptStartedAt));
    const analyzedDestination = destination;
    const request = buildAnalysisRequest(origin, analyzedDestination, selectedRoute);
    const requestKey = JSON.stringify(request);
    analysisSequence.current += 1;
    const requestId = analysisSequence.current;
    const attemptId = createJourneyAttemptId();
    const capturedTripKey = requestKey;
    briefingAttempt.current = null;
    briefingController.current?.abort();
    briefingController.current = null;
    cameraOpportunityCancel.current?.();
    cameraOpportunityCancel.current = null;
    setJourneyBriefingState({ status: 'waiting_for_evidence', attempt_id: attemptId });
    visionSequence.current += 1;
    visionController.current?.abort();
    const visionAttemptId = visionSequence.current;
    const visionAttemptKey = `${requestKey}:${requestId}`;
    const visionRequestController = new AbortController();
    visionController.current = visionRequestController;
    activeVisionKey.current = visionAttemptKey;
    setJourneyEvidenceState({ attempt_id: attemptId, lifecycle_id: requestId, trip: request, analysis: { status: 'loading', result: null, error: null }, camera_vision: { lifecycle_id: requestId, trip: request, camera_vision: { status: 'pending' } } });
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

    // Vision is one independent request for this explicit Analyze Journey action.
    // It never gates the road/weather analysis or the Phase 7 gallery.
    let visionTimedOut = false;
    const cameraInferenceStartedAt = performance.now();
    const visionTimeout = startCameraVisionTimeout(visionRequestController, () => {
      visionTimedOut = true;
    });
    const cameraResultPromise = fetchCameraVision(request, visionRequestController.signal).then((result) => {
      if (!isCurrentVisionAttempt(visionAttemptId, visionSequence.current, visionAttemptKey, activeVisionKey.current)) return;
      setJourneyCameraEvidence((current) => retainCurrentCameraVision(current, requestId, result));
      return result;
    }).catch((error: unknown) => {
      if (!isCurrentVisionAttempt(visionAttemptId, visionSequence.current, visionAttemptKey, activeVisionKey.current)) return;
      if (visionRequestController.signal.aborted && !visionTimedOut) return;
      const fallback = cameraVisionFailureResult(error, visionTimedOut);
      setJourneyCameraEvidence((current) => retainCurrentCameraVision(current, requestId, fallback));
      return fallback;
    }).finally(() => {
      clearTimeout(visionTimeout);
      if (visionSequence.current === visionAttemptId) visionController.current = null;
    });
    const cameraOpportunity = createCameraOpportunity(cameraResultPromise, cameraInferenceStartedAt);
    cameraOpportunityCancel.current = cameraOpportunity.cancel;

    selectedGalleryIntersectionId.current = null;
    nearbyCameraResult.current = null;

    function loadNearbyCameras(selectedIntersectionId: string | null, preserveAvailableResult = false) {
      nearbyCameraSequence.current += 1;
      const nearbyRequestId = nearbyCameraSequence.current;
      void fetchNearbyCameras(analyzedDestination, selectedIntersectionId, cameraControllerValue.signal).then((result) => {
        if (!isCurrentNearbyCameraRequest(requestKey, activeCameraKey.current, cameraRequestId, cameraSequence.current, nearbyRequestId, nearbyCameraSequence.current)) return;
        setNearbyCameraState({ status: 'success', requestKey: cameraDisplayKey, result });
        nearbyCameraResult.current = { requestKey: cameraDisplayKey, cameras: result.cameras.map((camera) => camera.intersection_id) };
        const selectedId = selectedGalleryIntersectionId.current;
        if (selectedIntersectionId === null && shouldRequestSelectedCameraMarker(selectedId, nearbyCameraResult.current.cameras)) {
          loadNearbyCameras(selectedId, true);
        }
      }).catch(() => {
        if (cameraControllerValue.signal.aborted || !isCurrentNearbyCameraRequest(requestKey, activeCameraKey.current, cameraRequestId, cameraSequence.current, nearbyRequestId, nearbyCameraSequence.current)) return;
        if (!preserveAvailableResult) setNearbyCameraState({ status: 'error', requestKey: cameraDisplayKey });
      });
    }

    setNearbyCameraState({ status: 'loading', requestKey: cameraDisplayKey });
    loadNearbyCameras(null);

    void fetchDestinationCamera(analyzedDestination, cameraControllerValue.signal).then((result) => {
      if (!isCurrentCameraRequest(requestKey, activeCameraKey.current, cameraRequestId, cameraSequence.current)) return;
      setCameraState({ status: 'success', requestKey: cameraDisplayKey, result });
      const selectedId = result.intersection?.intersection_id ?? null;
      selectedGalleryIntersectionId.current = selectedId;
      const markers = nearbyCameraResult.current;
      if (markers?.requestKey === cameraDisplayKey && shouldRequestSelectedCameraMarker(selectedId, markers.cameras)) {
        loadNearbyCameras(selectedId, true);
      }
    }).catch(() => {
      if (cameraControllerValue.signal.aborted || !isCurrentCameraRequest(requestKey, activeCameraKey.current, cameraRequestId, cameraSequence.current)) return;
      setCameraState({ status: 'error', requestKey: cameraDisplayKey });
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
      if (analysisController.current === controller) analysisController.current = null;
      const cameraResult = await cameraOpportunity.promise;
      if (cameraOpportunityCancel.current === cameraOpportunity.cancel) cameraOpportunityCancel.current = null;
      if (!isCurrentAnalysisRequest(requestId, analysisSequence.current, capturedTripKey, activeAnalysisKey.current) || briefingAttempt.current === attemptId) return;
      const activeTripNow = origin && destination && routeState.status === 'ready' && routeState.selectedRoute
        ? buildAnalysisRequest(origin, destination, routeState.selectedRoute) : null;
      if (!activeTripNow || JSON.stringify(activeTripNow) !== capturedTripKey) return;
      const matchingCamera: JourneyCameraEvidence | null = cameraResult ? {
        lifecycle_id: requestId, trip: request, camera_vision: { status: 'complete', result: cameraResult },
      } : {
        lifecycle_id: requestId, trip: request, camera_vision: { status: 'pending' },
      };
      const frozenBundle = deriveCurrentJourneyEvidence({
        attempt_id: attemptId, lifecycle_id: requestId, trip: request, analysis: { status: 'success', result: analysis, error: null }, camera_vision: matchingCamera,
      }, request, new Date().toISOString());
      if (!frozenBundle) return;
      let briefingRequest;
      try {
        briefingRequest = serializeBriefingEvidence(frozenBundle);
      } catch {
        setJourneyBriefingState({ status: 'error', attempt_id: attemptId, failure_code: 'invalid_response' });
        return;
      }
      // Set the single-use latch before starting the only briefing transport call.
      briefingAttempt.current = attemptId;
      const briefingOperation = startBriefingRequest(briefingRequest, undefined, 35_000);
      const briefingControllerValue = briefingOperation.controller;
      briefingController.current = briefingControllerValue;
      setJourneyBriefingState({ status: 'in_progress', attempt_id: attemptId });
      try {
        const result = await briefingOperation.promise;
        if (briefingControllerValue.signal.aborted || requestId !== analysisSequence.current || briefingAttempt.current !== attemptId) return;
        setJourneyBriefingState(result.status === 'available'
          ? { status: 'available', attempt_id: attemptId, result }
          : result.status === 'insufficient_evidence'
            ? { status: 'insufficient_evidence', attempt_id: attemptId, result }
            : result.status === 'error'
              ? { status: 'error', attempt_id: attemptId, failure_code: result.failure_code ?? 'error' }
              : { status: 'unavailable', attempt_id: attemptId, failure_code: result.failure_code ?? 'provider_unavailable' });
      } catch (error) {
        const timedOut = briefingOperation.wasTimedOut();
        if (requestId !== analysisSequence.current || briefingAttempt.current !== attemptId || briefingControllerValue.signal.aborted && !timedOut) return;
        const message = error instanceof Error ? error.message : '';
        const code = timedOut || message === 'timeout' ? 'timeout' : message === 'invalid_response' ? 'invalid_response' : 'request_failed';
        setJourneyBriefingState({ status: code === 'timeout' ? 'unavailable' : 'error', attempt_id: attemptId, failure_code: code });
      } finally {
        if (briefingController.current === briefingControllerValue) briefingController.current = null;
      }
    } catch (error) {
      if (controller.signal.aborted || !isCurrentAnalysisRequest(requestId, analysisSequence.current, requestKey, activeAnalysisKey.current)) return;
      cameraOpportunity.cancel();
      if (cameraOpportunityCancel.current === cameraOpportunity.cancel) cameraOpportunityCancel.current = null;
      setAnalysisState({ status: 'error', result: null, error: error instanceof Error ? error.message : 'Road Ahead analysis is temporarily unavailable. Please try again.' });
      if (briefingAttempt.current !== attemptId) setJourneyBriefingState({ status: 'idle' });
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
    visionController.current?.abort();
    cameraController.current?.abort();
    cameraSequence.current += 1;
    nearbyCameraSequence.current += 1;
    activeCameraKey.current = null;
    activeVisionKey.current = null;
    visionSequence.current += 1;
    briefingController.current?.abort();
    cameraOpportunityCancel.current?.();
    briefingAttempt.current = null;
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

  useEffect(() => {
    if (stage === 'understand') {
      appShellRef.current?.scrollTo({ top: 0, behavior: 'auto' });
      window.scrollTo({ top: 0, behavior: 'auto' });
    }
  }, [stage]);

  return (
    <main ref={appShellRef} className={`app-shell app-shell-stage-${stage}`}>
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

      <JourneyStageLayout stage={stage} analysis={analysisState} camera={cameraState} analysisAt={analysisAt}>
        <div className={`workspace workspace-stage-${stage}`}>
          <div className="map-workspace">
            <div className="map-caption"><span className="map-caption-dot" /> VANCOUVER OVERVIEW</div>
            <VancouverMap
              routes={routeState.status === 'ready' ? routeState.candidates : []}
              selectedRouteId={routeState.status === 'ready' ? routeState.selectedRoute?.id ?? null : null}
              fitKey={routeState.fitKey}
              findings={analysisState.status === 'success' ? analysisState.result.findings : noAnalysisFindings}
              drivebcFindings={analysisState.status === 'success' ? analysisState.result.drivebc_findings : noDriveBCFindings}
              regionalEvents={analysisState.status === 'success' ? analysisState.result.regional_events : noRegionalEvents}
              selectedEventId={activeSelectedEvent}
              onSelectEvent={setSelectedEventId}
              cameraMarkers={nearbyCameraState.status === 'success' ? nearbyCameraState.result.cameras : []}
              selectedCameraId={cameraState.status === 'success' ? cameraState.result.intersection?.intersection_id ?? null : null}
            />
          </div>
          <IntelligencePanel stage={stage} routeState={routeState} onSelectRoute={selectRoute} analysisState={analysisState} selectedEventId={activeSelectedEvent} onSelectFinding={setSelectedEventId} />
        </div>
        {stage === 'understand' && <>
          <BriefingCard briefingState={journeyBriefingState} />
          <section className="supporting-information" aria-label="Supporting journey information">
            <h2>Supporting information</h2>
            <details className="supporting-disclosure">
              <summary>Full three-hour forecast and ECCC station observations</summary>
              <DestinationWeatherPanel analysis={analysisState} supportingOnly />
            </details>
            <details className="supporting-disclosure">
              <summary>Detailed road source status and freshness</summary>
              <RoadAheadPanel analysis={analysisState} selectedEventId={activeSelectedEvent} onSelectFinding={setSelectedEventId} presentation="supporting" />
            </details>
            <details className="supporting-disclosure">
              <summary>Regional map context</summary>
              {analysisState.status === 'success' ? <p className="supporting-hint">The map above retains regional DriveBC context and metadata-only nearby camera markers. Select a road event in its source-specific list to focus it on the map.</p>
                : <p className="supporting-hint">Regional DriveBC context appears on the map when journey analysis returns it. Transit mode remains deferred.</p>}
            </details>
          </section>
        </>}
      </JourneyStageLayout>
    </main>
  );
}
