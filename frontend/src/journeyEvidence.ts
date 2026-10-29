import type {
  AnalysisFinding, AnalysisRequest, AnalysisState, DriveBCAnalysisFinding, ForecastCoverage,
  ForecastInterval, SelectedStationObservation, SourceStatus, WeatherSourceStatus,
  CurrentWeatherEvidence, DestinationWeather, UnmatchableEvent,
} from './analysisTypes';
import type { CameraVisionResult, JourneyCameraEvidence } from './cameraVision';

export type EvidenceAvailability = 'available' | 'empty' | 'partial' | 'unavailable' | 'pending' | 'failed' | 'unknown';
export type BundleReadiness = 'ready' | 'partial' | 'unavailable' | 'pending' | 'failed' | 'unknown';

export type JourneyEvidenceSource<T> = { availability: EvidenceAvailability } & T;
export type RoadAheadEvidence = JourneyEvidenceSource<{
  statuses: SourceStatus[]; findings: AnalysisFinding[]; unmatchable_events: UnmatchableEvent[];
}>;
export type DriveBCEvidence = JourneyEvidenceSource<{
  status: SourceStatus | null; findings: DriveBCAnalysisFinding[];
}>;
export type OpenWeatherCurrentEvidence = JourneyEvidenceSource<{
  status: WeatherSourceStatus | null; weather: CurrentWeatherEvidence | null;
}>;
export type OpenWeatherForecastEvidence = JourneyEvidenceSource<{
  status: WeatherSourceStatus | null; intervals: ForecastInterval[]; coverage: ForecastCoverage | null;
}>;
export type EcccSwobEvidence = JourneyEvidenceSource<{
  status: WeatherSourceStatus | null; observations: SelectedStationObservation[]; attribution: string | null;
}>;
export type CameraVisionEvidenceSection = JourneyEvidenceSource<{ result: CameraVisionResult | null }>;

export type JourneyEvidenceBundle = {
  schema_version: 'journey-evidence-v1';
  assembled_at: string;
  identity: {
    attempt_id: string;
    trip: AnalysisRequest;
    analysis_status: 'success' | 'pending' | 'failed' | 'unknown';
    analysis_error: string | null;
    analyzed_at: string | null;
  };
  readiness: { status: BundleReadiness; ready_for_briefing: boolean };
  sources: {
    road_ahead: RoadAheadEvidence;
    drivebc_open511: DriveBCEvidence;
    openweather_current: OpenWeatherCurrentEvidence;
    openweather_forecast: OpenWeatherForecastEvidence;
    eccc_swob: EcccSwobEvidence;
    camera_vision: CameraVisionEvidenceSection;
  };
};

export type JourneyEvidenceInputs = {
  trip: AnalysisRequest;
  attempt_id: string;
  lifecycle_id: number;
  assembled_at: string;
  analysis: AnalysisState;
  camera_vision: JourneyCameraEvidence | null;
};

/** The single internal handoff: current active evidence, or null after journey invalidation. */
export function deriveCurrentJourneyEvidence(
  state: { attempt_id: string | null; lifecycle_id: number | null; trip: AnalysisRequest | null; analysis: AnalysisState; camera_vision: JourneyCameraEvidence | null },
  trip: AnalysisRequest | null,
  assembled_at: string,
): JourneyEvidenceBundle | null {
  if (state.attempt_id === null || state.lifecycle_id === null || !state.trip || !trip || tripIdentity(state.trip) !== tripIdentity(trip)) return null;
  try {
    return assembleJourneyEvidence({ trip, attempt_id: state.attempt_id, lifecycle_id: state.lifecycle_id, assembled_at, analysis: state.analysis, camera_vision: state.camera_vision });
  } catch {
    return null;
  }
}

const clone = <T>(value: T): T => structuredClone(value);

const uuidV4Pattern = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export function isJourneyAttemptId(value: unknown): value is string {
  return typeof value === 'string' && uuidV4Pattern.test(value);
}

export function createJourneyAttemptId(generate: () => string = () => globalThis.crypto.randomUUID()): string {
  const attemptId = generate();
  if (!isJourneyAttemptId(attemptId)) throw new Error('Journey attempt ID must be a canonical UUID v4');
  return attemptId;
}

function tripIdentity(trip: AnalysisRequest): string {
  const location = (value: AnalysisRequest['origin']) => [value.name, value.latitude, value.longitude, value.address ?? null, value.provider_id ?? null];
  const route = trip.selected_route;
  return JSON.stringify([
    trip.mode, location(trip.origin), location(trip.destination), route.candidate_id,
    route.geometry, route.distance_meters, route.duration_seconds, route.label ?? null,
  ]);
}

function validateInputs(inputs: JourneyEvidenceInputs): void {
  if (!isJourneyAttemptId(inputs.attempt_id) || !Number.isInteger(inputs.lifecycle_id) || inputs.lifecycle_id < 0) throw new Error('Journey evidence identity is invalid');
  if (!Number.isFinite(Date.parse(inputs.assembled_at))) throw new Error('Journey evidence assembled_at must be a timestamp');
  if (inputs.analysis.status === 'success' && tripIdentity(inputs.analysis.result.trip) !== tripIdentity(inputs.trip)) {
    throw new Error('Journey analysis trip does not match the canonical trip');
  }
  const camera = inputs.camera_vision;
  if (camera && (camera.lifecycle_id !== inputs.lifecycle_id || tripIdentity(camera.trip) !== tripIdentity(inputs.trip))) {
    throw new Error('Camera vision evidence does not match the journey attempt');
  }
}

function analysisOutcome(state: AnalysisState): JourneyEvidenceBundle['identity']['analysis_status'] {
  if (state.status === 'success') return 'success';
  if (state.status === 'loading') return 'pending';
  if (state.status === 'error') return 'failed';
  return 'unknown';
}

function statusAvailability(status: Pick<SourceStatus, 'success' | 'available' | 'error'> | null, hasEvidence: boolean): EvidenceAvailability {
  if (!status) return 'unknown';
  if (status.available && !status.success) return 'partial';
  if (status.available) return hasEvidence ? 'available' : 'empty';
  if (status.success) return hasEvidence ? 'available' : 'empty';
  if (status.error) return 'failed';
  return 'unavailable';
}

function aggregateRoadAvailability(statuses: SourceStatus[], findings: AnalysisFinding[]): EvidenceAvailability {
  if (statuses.length === 0) return 'unknown';
  const mapped = statuses.map((status) => statusAvailability(status, status.records_normalized > 0));
  if (mapped.every((status) => status === 'available' || status === 'empty')) return findings.length ? 'available' : 'empty';
  if (mapped.some((status) => status === 'available' || status === 'empty' || status === 'partial')) return 'partial';
  if (mapped.some((status) => status === 'failed')) return 'failed';
  return 'unavailable';
}

function weatherAvailability(status: WeatherSourceStatus | null, hasEvidence: boolean): EvidenceAvailability {
  return statusAvailability(status, hasEvidence);
}

function cameraAvailability(camera: JourneyCameraEvidence | null): EvidenceAvailability {
  if (!camera) return 'unknown';
  if (camera.camera_vision.status === 'pending') return 'pending';
  switch (camera.camera_vision.result.observation.status) {
    case 'available': return 'available';
    case 'partial': return 'partial';
    case 'insufficient_evidence': return 'empty';
    case 'unavailable': return 'unavailable';
    case 'error': return 'failed';
  }
}

function readiness(analysisStatus: JourneyEvidenceBundle['identity']['analysis_status'], states: EvidenceAvailability[]): JourneyEvidenceBundle['readiness'] {
  if (analysisStatus !== 'success') return { status: analysisStatus, ready_for_briefing: false };
  const complete = states.every((state) => state === 'available' || state === 'empty');
  return { status: complete ? 'ready' : 'partial', ready_for_briefing: true };
}

/** Assemble the already-normalized results for one explicit journey attempt. */
export function assembleJourneyEvidence(inputs: JourneyEvidenceInputs): JourneyEvidenceBundle {
  validateInputs(inputs);
  const analysis = inputs.analysis.status === 'success' ? inputs.analysis.result : null;
  const outcome = analysisOutcome(inputs.analysis);
  const weather: DestinationWeather | null = analysis?.destination_weather ?? null;
  const roadStatuses = analysis
    ? clone(analysis.source_statuses.filter((status) => !/drivebc|open511/i.test(`${status.source} ${status.dataset_id}`)))
    : [];
  const roadFindings = analysis ? clone(analysis.findings) : [];
  const drivebcStatus = analysis?.source_statuses.find((status) => /drivebc|open511/i.test(`${status.source} ${status.dataset_id}`)) ?? null;
  const drivebcFindings = analysis ? clone(analysis.drivebc_findings) : [];
  const currentStatus = weather ? clone(weather.openweather_current.status) : null;
  const current = weather ? clone(weather.openweather_current.weather) : null;
  const forecastStatus = weather ? clone(weather.openweather_forecast.status) : null;
  const intervals = weather ? clone(weather.openweather_forecast.intervals) : [];
  const coverage = weather ? clone(weather.openweather_forecast.coverage) : null;
  const swobStatus = weather ? clone(weather.eccc_status) : null;
  const observations = weather ? clone(weather.eccc_observations) : [];
  const camera = inputs.camera_vision?.camera_vision.status === 'complete'
    ? clone(inputs.camera_vision.camera_vision.result) : null;

  const sources: JourneyEvidenceBundle['sources'] = {
    road_ahead: {
      availability: analysis ? aggregateRoadAvailability(roadStatuses, roadFindings) : outcome === 'pending' ? 'pending' : 'unknown',
      statuses: roadStatuses, findings: roadFindings,
      unmatchable_events: analysis ? clone(analysis.unmatchable_events) : [],
    },
    drivebc_open511: {
      availability: analysis
        ? statusAvailability(drivebcStatus, drivebcFindings.length > 0) === 'available' && drivebcFindings.length === 0
          ? 'empty' : statusAvailability(drivebcStatus, drivebcFindings.length > 0)
        : outcome === 'pending' ? 'pending' : 'unknown',
      status: drivebcStatus ? clone(drivebcStatus) : null, findings: drivebcFindings,
    },
    openweather_current: {
      availability: analysis ? weatherAvailability(currentStatus, current !== null) : outcome === 'pending' ? 'pending' : 'unknown',
      status: currentStatus, weather: current,
    },
    openweather_forecast: {
      availability: analysis
        ? intervals.length > 0 && coverage && !coverage.continuous ? 'partial'
          : weatherAvailability(forecastStatus, intervals.length > 0)
        : outcome === 'pending' ? 'pending' : 'unknown',
      status: forecastStatus, intervals, coverage,
    },
    eccc_swob: {
      availability: analysis ? weatherAvailability(swobStatus, observations.length > 0) : outcome === 'pending' ? 'pending' : 'unknown',
      status: swobStatus, observations,
      attribution: weather?.eccc_attribution ?? null,
    },
    camera_vision: { availability: cameraAvailability(inputs.camera_vision), result: camera },
  };
  const states = Object.values(sources).map(({ availability }) => availability);
  return {
    schema_version: 'journey-evidence-v1', assembled_at: inputs.assembled_at,
    identity: {
      attempt_id: inputs.attempt_id, trip: clone(inputs.trip), analysis_status: outcome,
      analysis_error: inputs.analysis.status === 'error' ? inputs.analysis.error : null,
      analyzed_at: analysis?.analyzed_at ?? null,
    },
    readiness: readiness(outcome, states), sources,
  };
}
