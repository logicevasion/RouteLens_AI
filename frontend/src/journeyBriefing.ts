import type { AnalysisRequest } from './analysisTypes';
import type { CameraVisionResult } from './cameraVision';
import type { JourneyEvidenceBundle, EvidenceAvailability } from './journeyEvidence';

export type BriefingAvailability = 'available' | 'insufficient_evidence' | 'unavailable' | 'error';
export type BriefingFailureCode = 'configuration_missing' | 'budget_exhausted' | 'timeout' | 'provider_unavailable' |
  'invalid_model_output' | 'duplicate_attempt' | 'error' | 'request_failed' | 'invalid_response';
export type BriefingHighlightV1 = { category: 'road' | 'weather' | 'camera' | 'general'; text: string; evidence_refs: string[] };
export type BriefingResultV1 = {
  contract_version: 'journey-briefing-v1'; prompt_version: 'journey-briefing-prompt-v1';
  status: BriefingAvailability; failure_code: BriefingFailureCode | null; generated_at: string; attempt_id: number;
  origin_name: string; destination_name: string; requested_model: 'google/gemma-4-31b-it';
  returned_model: string | null; provider: string | null; overview: string; overview_evidence_refs: string[];
  highlights: BriefingHighlightV1[]; limitations: string[];
  usage: { input_tokens: number | null; output_tokens: number | null; total_tokens: number | null; cost_usd: number | null; latency_ms: number };
};
export type JourneyBriefingState =
  | { status: 'idle' }
  | { status: 'waiting_for_evidence'; attempt_id: number }
  | { status: 'in_progress'; attempt_id: number }
  | { status: 'available'; attempt_id: number; result: BriefingResultV1 }
  | { status: 'insufficient_evidence'; attempt_id: number; result: BriefingResultV1 }
  | { status: 'unavailable' | 'error'; attempt_id: number; failure_code: BriefingFailureCode };

export type BriefingEvidenceRequestV1 = {
  request_schema_version: 'journey-briefing-request-v1'; bundle_schema_version: 'journey-evidence-v1';
  attempt_id: number; assembled_at: string; analyzed_at: string; analysis_status: 'success';
  journey: { mode: 'drive'; origin: PlaceV1; destination: PlaceV1; route: { candidate_id: string; label: string | null; distance_meters: number } };
  sources: {
    road_ahead: { availability: EvidenceAvailability; statuses: SourceStatusV1[]; findings: RoadFindingV1[]; omitted_count: number };
    drivebc_open511: { availability: EvidenceAvailability; status: SourceStatusV1 | null; findings: RoadFindingV1[]; omitted_count: number };
    openweather_current: { availability: EvidenceAvailability; status: SourceStatusV1 | null; observation: CurrentObservationV1 | null };
    openweather_forecast: { availability: EvidenceAvailability; status: SourceStatusV1 | null; coverage: ForecastCoverageV1 | null; intervals: ForecastIntervalV1[]; omitted_count: number };
    eccc_swob: { availability: EvidenceAvailability; status: SourceStatusV1 | null; attribution: string | null; observations: SwobObservationV1[]; omitted_count: number };
    camera_vision: { availability: EvidenceAvailability; observation_status: CameraStatusV1; observation: CameraObservationV1 | null };
  };
};
type PlaceV1 = { name: string; latitude: number; longitude: number };
type SourceStatusV1 = { source: string; dataset_id: string; success: boolean; available: boolean; fetched_at: string | null; stale: boolean; cache_stale: boolean | null };
type RoadFindingV1 = { source_id: string; title: string; description: string | null; classification: 'direct_overlap' | 'nearby'; distance_meters: number; location: string | null; severity: string | null; status: string | null; schedule_text: string | null; restriction_text: string | null; observed_at: string | null; updated_at: string | null; direction_assessment: string | null; temporal_applicability: string | null; current_impact: string | null; geometry_basis: 'linestring_intersection' | 'linestring_proximity' | 'point_proximity' | null };
type ConditionV1 = { code: number | null; group: 'clear' | 'clouds' | 'rain' | 'drizzle' | 'thunderstorm' | 'snow' | 'mist' | 'fog' | 'atmosphere' | 'unknown' | null; description: string | null };
type MeasurementV1 = { value: number; unit: string };
type CurrentObservationV1 = { source: 'OpenWeather'; product: 'onecall4_current'; observed_at: string; fetched_at: string; condition: ConditionV1 | null; temperature_c: MeasurementV1 | null; feels_like_c: MeasurementV1 | null; humidity_pct: number | null; wind_speed_m_s: number | null; wind_direction_deg: number | null; wind_gust_m_s: number | null; visibility_m: number | null; rain_1h_mm: number | null; snow_1h_mm: number | null };
type ForecastCoverageV1 = { continuous: boolean; expected_interval_count: number; returned_interval_count: number; first_interval_at: string | null; last_interval_at: string | null };
type ForecastIntervalV1 = { source: 'OpenWeather'; product: 'onecall4_timeline_15min'; forecast_at: string; fetched_at: string; condition: ConditionV1 | null; precipitation_probability_pct: number | null; temperature_c: MeasurementV1 | null; feels_like_c: MeasurementV1 | null; humidity_pct: number | null; wind_speed_m_s: number | null; wind_direction_deg: number | null; wind_gust_m_s: number | null; visibility_m: number | null; rain_1h_mm: number | null; rain_3h_mm: number | null; snow_1h_mm: number | null; snow_3h_mm: number | null };
type StationMeasurementV1 = { name: 'temperature' | 'relative_humidity' | 'precipitation' | 'wind_speed' | 'wind_direction' | 'snow_depth'; value: number; unit: string; source_field: string; interval_seconds: number | null; quality_code: number | null };
type SwobObservationV1 = { station_id: string; station_name: string | null; distance_meters: number; observed_at: string; retrieved_at: string; observation_age_seconds: number; observation_stale: boolean; cache_stale: boolean; measurements: StationMeasurementV1[] };
type CameraStatusV1 = 'available' | 'partial' | 'insufficient_evidence' | 'unavailable' | 'error' | 'pending' | 'unknown';
type CameraObservationV1 = { status: CameraStatusV1; intersection_name: string | null; street_names: string[]; distance_from_destination_meters: number | null; source_name: string | null; direction_view: { view_id: string; direction_label: string | null; retrieved_at: string; source_capture_at: string | null; road_surface: string; visibility: string; vehicle_activity: string; conditions: string[]; uncertainty: string; note: string | null } | null; summary: string | null; summary_evidence_view_ids: string[] };

const text = (value: string | null | undefined, max: number): string | null => {
  if (value == null) return null;
  const safe = value.replace(/https?:\/\/\S+/gi, '').replace(/data:image\/\S+/gi, '').trim();
  return safe ? safe.slice(0, max) : null;
};
const requiredText = (value: string | null | undefined, max: number, field: string): string => {
  const result = text(value, max);
  if (!result) throw new Error(`Briefing evidence is missing required ${field}`);
  return result;
};
const timestamp = (value: string | null, field: string): string | null => {
  if (value === null) return null;
  if (!Number.isFinite(Date.parse(value)) || !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)) throw new Error(`Briefing evidence has invalid ${field} timestamp`);
  return value;
};
const sourceStatus = (s: { source: string; dataset_id: string; success: boolean; available: boolean; fetched_at: string | null; stale: boolean; cache_stale?: boolean } | null): SourceStatusV1 | null => s ? {
  source: requiredText(s.source, 120, 'source name'), dataset_id: requiredText(s.dataset_id, 120, 'dataset ID'), success: s.success,
  available: s.available, fetched_at: timestamp(s.fetched_at, 'source fetch'), stale: s.stale, cache_stale: s.cache_stale ?? null,
} : null;
const availability = (value: EvidenceAvailability): EvidenceAvailability => value;
const boundedAvailability = (value: EvidenceAvailability, evidenceCount: number, serializedCount: number): EvidenceAvailability =>
  value === 'available' && evidenceCount > 0 && serializedCount === 0 ? 'partial' : value;
const measurement = (value: number | null | undefined, unit: string): MeasurementV1 | null => value == null ? null : { value, unit };
const conditionGroup = (group: string | null): ConditionV1['group'] => {
  if (group === null) return null;
  const normalized = group.toLowerCase();
  if (['clear', 'clouds', 'rain', 'drizzle', 'thunderstorm', 'snow', 'mist', 'fog', 'atmosphere'].includes(normalized)) return normalized as ConditionV1['group'];
  return 'unknown';
};
const condition = (value: { code: number | null; group: string | null; description: string | null } | null): ConditionV1 | null => value ? {
  code: value.code, group: conditionGroup(value.group), description: text(value.description, 120),
} : null;
type AnalysisFindingEvent = { source_record_id: string; title: string; description: string | null; severity: string | null; status: string | null; schedule_text: string | null; restriction_text: string | null; observed_at: string | null; updated_at: string | null };
type RoadInput = {
  event: AnalysisFindingEvent; classification: 'direct_overlap' | 'nearby'; distance_meters: number;
  detail?: { title?: string | null; location?: string | null; description?: string | null; status?: string | null; schedule_text?: string | null; restriction_text?: string | null };
  geometry_basis?: RoadFindingV1['geometry_basis'];
  source_evidence?: { direction_assessment: string; temporal_applicability: string; current_impact: string };
};
const sortedRoads = <T extends RoadInput>(rows: T[]) => [...rows].sort((a, b) => {
  const cls = Number(a.classification !== 'direct_overlap') - Number(b.classification !== 'direct_overlap');
  return cls || a.distance_meters - b.distance_meters || a.event.source_record_id.localeCompare(b.event.source_record_id);
});
function roadFinding(row: RoadInput): RoadFindingV1 {
  const e = row.event;
  return {
    source_id: e.source_record_id, title: requiredText(row.detail?.title ?? e.title, 160, 'road finding title'),
    description: text(row.detail?.description ?? e.description, 320), classification: row.classification,
    distance_meters: row.distance_meters, location: text(row.detail?.location, 160), severity: text(e.severity, 80),
    status: text(row.detail?.status ?? e.status, 80), schedule_text: text(row.detail?.schedule_text ?? e.schedule_text, 320),
    restriction_text: text(row.detail?.restriction_text ?? e.restriction_text, 320), observed_at: timestamp(e.observed_at, 'road observation'), updated_at: timestamp(e.updated_at, 'road update'),
    direction_assessment: text(row.source_evidence?.direction_assessment, 80),
    temporal_applicability: text(row.source_evidence?.temporal_applicability, 80),
    current_impact: text(row.source_evidence?.current_impact, 80), geometry_basis: row.geometry_basis ?? null,
  };
}

export function serializeBriefingEvidence(bundle: JourneyEvidenceBundle): BriefingEvidenceRequestV1 {
  if (bundle.schema_version !== 'journey-evidence-v1' || !bundle.readiness.ready_for_briefing || bundle.identity.analysis_status !== 'success' || !bundle.identity.analyzed_at) {
    throw new Error('Journey evidence is not eligible for briefing');
  }
  const trip = bundle.identity.trip;
  if (trip.mode !== 'drive' || trip.selected_route.distance_meters <= 0 || !Number.isInteger(bundle.identity.attempt_id) || bundle.identity.attempt_id < 0 || bundle.identity.attempt_id > 2_147_483_647) throw new Error('Journey evidence identity is invalid');
  const assembledAt = timestamp(bundle.assembled_at, 'assembly')!;
  const analyzedAt = timestamp(bundle.identity.analyzed_at, 'analysis')!;
  if (Date.parse(assembledAt) < Date.parse(analyzedAt)) throw new Error('Briefing evidence assembly predates analysis');
  const rawRoads = sortedRoads(bundle.sources.road_ahead.findings);
  const rawDrivebc = sortedRoads(bundle.sources.drivebc_open511.findings);
  const validSourceId = (id: string) => id.length <= 125 && /^[A-Za-z0-9_.-]+$/.test(id);
  const roads = rawRoads.filter((row) => validSourceId(row.event.source_record_id));
  const drivebc = rawDrivebc.filter((row) => validSourceId(row.event.source_record_id));
  const rawSwob = bundle.sources.eccc_swob.observations;
  const swob = rawSwob.filter((item) => item.observation.station_id.length <= 88 && /^[A-Za-z0-9_.-]+$/.test(item.observation.station_id));
  const forecast = [...bundle.sources.openweather_forecast.intervals].sort((a, b) => Date.parse(a.forecast_at) - Date.parse(b.forecast_at));
  const selectedRoads = roads.slice(0, 12).map(roadFinding);
  const selectedDrivebc = drivebc.slice(0, 12).map(roadFinding);
  const selectedForecast = forecast.slice(0, 4).map((v): ForecastIntervalV1 => ({
    source: 'OpenWeather', product: 'onecall4_timeline_15min', forecast_at: timestamp(v.forecast_at, 'forecast')!, fetched_at: timestamp(v.fetched_at, 'weather fetch')!,
    condition: condition(v.condition), precipitation_probability_pct: v.precipitation_probability_pct,
    temperature_c: measurement(v.temperature_c, '°C'), feels_like_c: measurement(v.feels_like_c, '°C'), humidity_pct: v.humidity_pct,
    wind_speed_m_s: v.wind_speed_m_s, wind_direction_deg: v.wind_direction_deg ?? null, wind_gust_m_s: v.wind_gust_m_s ?? null,
    visibility_m: v.visibility_m, rain_1h_mm: v.rain_1h_mm ?? null, rain_3h_mm: v.rain_3h_mm ?? null,
    snow_1h_mm: v.snow_1h_mm ?? null, snow_3h_mm: v.snow_3h_mm ?? null,
  }));
  const selectedSwob = swob.slice(0, 3).map((s): SwobObservationV1 => {
    const o = s.observation;
    const measurements: StationMeasurementV1[] = [];
    const add = (name: StationMeasurementV1['name'], value: typeof o.temperature) => { if (value) measurements.push({ name, value: value.value, unit: value.unit, source_field: requiredText(value.source_field, 120, 'SWOB source field'), interval_seconds: value.interval_seconds, quality_code: value.quality_code }); };
    add('temperature', o.temperature); add('relative_humidity', o.relative_humidity);
    o.precipitation.forEach((m) => { if (measurements.filter((item) => item.name === 'precipitation').length < 7) measurements.push({ name: 'precipitation', value: m.value, unit: m.unit, source_field: requiredText(m.source_field, 120, 'SWOB source field'), interval_seconds: m.interval_seconds, quality_code: m.quality_code }); });
    add('wind_speed', o.wind_speed); add('wind_direction', o.wind_direction); add('snow_depth', o.snow_depth);
    return { station_id: o.station_id, station_name: text(o.station_name, 120), distance_meters: s.distance_meters, observed_at: timestamp(o.observed_at, 'SWOB observation')!,
      retrieved_at: timestamp(o.retrieved_at, 'SWOB retrieval')!, observation_age_seconds: s.observation_age_seconds, observation_stale: s.observation_stale, cache_stale: s.cache_stale, measurements };
  });
  const current = bundle.sources.openweather_current.weather;
  const currentObservation: CurrentObservationV1 | null = current ? {
    source: 'OpenWeather', product: 'onecall4_current', observed_at: timestamp(current.observed_at, 'weather observation')!, fetched_at: timestamp(current.fetched_at, 'weather fetch')!,
    condition: condition(current.condition), temperature_c: measurement(current.temperature_c, '°C'), feels_like_c: measurement(current.feels_like_c, '°C'),
    humidity_pct: current.humidity_pct, wind_speed_m_s: current.wind_speed_m_s, wind_direction_deg: current.wind_direction_deg,
    wind_gust_m_s: current.wind_gust_m_s, visibility_m: current.visibility_m, rain_1h_mm: current.rain_1h_mm ?? null, snow_1h_mm: current.snow_1h_mm ?? null,
  } : null;
  const cameraResult = bundle.sources.camera_vision.result;
  const camera = cameraSection(bundle.sources.camera_vision.availability, cameraResult);
  const payload: BriefingEvidenceRequestV1 = {
    request_schema_version: 'journey-briefing-request-v1', bundle_schema_version: 'journey-evidence-v1', attempt_id: bundle.identity.attempt_id,
    assembled_at: bundle.assembled_at, analyzed_at: bundle.identity.analyzed_at, analysis_status: 'success',
    journey: { mode: 'drive', origin: place(trip.origin), destination: place(trip.destination), route: {
      candidate_id: requiredText(trip.selected_route.candidate_id, 128, 'route ID'), label: text(trip.selected_route.label, 120), distance_meters: trip.selected_route.distance_meters,
    } },
    sources: {
      road_ahead: { availability: boundedAvailability(availability(bundle.sources.road_ahead.availability), rawRoads.length, selectedRoads.length), statuses: bundle.sources.road_ahead.statuses.slice(0, 8).map((s) => sourceStatus(s)!), findings: selectedRoads, omitted_count: rawRoads.length - selectedRoads.length },
      drivebc_open511: { availability: boundedAvailability(availability(bundle.sources.drivebc_open511.availability), rawDrivebc.length, selectedDrivebc.length), status: sourceStatus(bundle.sources.drivebc_open511.status), findings: selectedDrivebc, omitted_count: rawDrivebc.length - selectedDrivebc.length },
      openweather_current: { availability: availability(bundle.sources.openweather_current.availability), status: sourceStatus(bundle.sources.openweather_current.status), observation: currentObservation },
      openweather_forecast: { availability: availability(bundle.sources.openweather_forecast.availability), status: sourceStatus(bundle.sources.openweather_forecast.status),
        coverage: bundle.sources.openweather_forecast.coverage ? { continuous: bundle.sources.openweather_forecast.coverage.continuous,
          expected_interval_count: bundle.sources.openweather_forecast.coverage.expected_interval_count,
          returned_interval_count: bundle.sources.openweather_forecast.coverage.returned_interval_count,
          first_interval_at: timestamp(bundle.sources.openweather_forecast.coverage.first_interval_at, 'forecast coverage'), last_interval_at: timestamp(bundle.sources.openweather_forecast.coverage.last_interval_at, 'forecast coverage') } : null,
        intervals: selectedForecast, omitted_count: forecast.length - selectedForecast.length },
      eccc_swob: { availability: boundedAvailability(availability(bundle.sources.eccc_swob.availability), rawSwob.length, selectedSwob.length), status: sourceStatus(bundle.sources.eccc_swob.status), attribution: text(bundle.sources.eccc_swob.attribution, 180), observations: selectedSwob, omitted_count: rawSwob.length - selectedSwob.length },
      camera_vision: camera,
    },
  };
  const bytes = new TextEncoder().encode(JSON.stringify(payload)).byteLength;
  if (bytes > 32 * 1024) throw new Error('Briefing evidence exceeds 32 KiB');
  return payload;
}
function place(location: AnalysisRequest['origin']): PlaceV1 { return { name: requiredText(location.name, 120, 'place name'), latitude: location.latitude, longitude: location.longitude }; }
function cameraSection(availabilityValue: EvidenceAvailability, result: CameraVisionResult | null): BriefingEvidenceRequestV1['sources']['camera_vision'] {
  if (!result) {
    const observation_status: CameraStatusV1 = availabilityValue === 'pending' ? 'pending' : availabilityValue === 'unavailable' ? 'unavailable' : availabilityValue === 'failed' ? 'error' : 'unknown';
    return { availability: availabilityValue, observation_status, observation: null };
  }
  const source = result.observation;
  let status: CameraStatusV1;
  if (source.status === 'available' || source.status === 'partial') status = source.status;
  else if (source.status === 'insufficient_evidence') status = 'insufficient_evidence';
  else if (source.status === 'unavailable' || source.status === 'error') status = source.status;
  else status = 'unknown';
  const included = source.included_views[0];
  const view = included ? source.views.find((candidate) => candidate.view_id === included.view_id) : undefined;
  const usable = (status === 'available' || status === 'partial') && included && view;
  if (usable) {
    const activeStatus: 'available' | 'partial' = status === 'partial' ? 'partial' : 'available';
    const summary = source.intersection_summary && source.summary_evidence_view_ids.length === 1 && source.summary_evidence_view_ids[0] === included.view_id ? text(source.intersection_summary, 240) : null;
    return { availability: activeStatus, observation_status: activeStatus, observation: {
      status: activeStatus, intersection_name: text(source.intersection_name, 120), street_names: source.street_names.slice(0, 2).map((x) => text(x, 120) ?? ''),
      distance_from_destination_meters: source.distance_from_destination_metres, source_name: text(source.source_name, 120), direction_view: {
        view_id: included.view_id, direction_label: text(included.direction_label, 80), retrieved_at: timestamp(included.retrieved_at, 'camera retrieval')!, source_capture_at: timestamp(included.source_capture_at, 'camera capture'),
        road_surface: view.road_surface, visibility: view.visibility, vehicle_activity: view.vehicle_activity, conditions: view.conditions.slice(0, 5), uncertainty: view.uncertainty, note: text(view.note, 160),
      }, summary, summary_evidence_view_ids: summary ? [included.view_id] : [],
    } };
  }
  if (status === 'available' || status === 'partial') status = 'insufficient_evidence';
  const availabilityStatus: EvidenceAvailability = status === 'insufficient_evidence' ? 'empty' : status === 'error' ? 'failed' : status === 'unknown' ? 'unknown' : 'unavailable';
  return { availability: availabilityStatus, observation_status: status, observation: { status, intersection_name: text(source.intersection_name, 120), street_names: source.street_names.slice(0, 2).map((x) => text(x, 120) ?? ''), distance_from_destination_meters: source.distance_from_destination_metres, source_name: text(source.source_name, 120), direction_view: null, summary: null, summary_evidence_view_ids: [] } };
}

export function normalizeBriefingResult(value: unknown): BriefingResultV1 | null {
  if (!value || typeof value !== 'object') return null;
  const v = value as Record<string, unknown>;
  const statuses = ['available', 'insufficient_evidence', 'unavailable', 'error'];
  const failures = ['configuration_missing', 'budget_exhausted', 'timeout', 'provider_unavailable', 'invalid_model_output', 'duplicate_attempt', 'error'];
  if (v.contract_version !== 'journey-briefing-v1' || v.prompt_version !== 'journey-briefing-prompt-v1' || !statuses.includes(String(v.status)) ||
      !(v.failure_code === null || failures.includes(String(v.failure_code))) || typeof v.generated_at !== 'string' || !Number.isFinite(Date.parse(v.generated_at)) ||
      !Number.isInteger(v.attempt_id) || typeof v.origin_name !== 'string' || v.origin_name.length > 120 || typeof v.destination_name !== 'string' || v.destination_name.length > 120 ||
      v.requested_model !== 'google/gemma-4-31b-it' || !(v.returned_model === null || typeof v.returned_model === 'string' && v.returned_model.length <= 120) || !(v.provider === null || typeof v.provider === 'string' && v.provider.length <= 80) ||
      typeof v.overview !== 'string' || !Array.isArray(v.overview_evidence_refs) || !Array.isArray(v.highlights) || !Array.isArray(v.limitations) || !v.usage || typeof v.usage !== 'object') return null;
  const usage = v.usage as Record<string, unknown>;
  const boundedInteger = (n: unknown, max: number) => n === null || typeof n === 'number' && Number.isInteger(n) && n >= 0 && n <= max;
  if (!boundedInteger(usage.input_tokens, 10_000_000) || !boundedInteger(usage.total_tokens, 10_000_000) ||
      !boundedInteger(usage.output_tokens, 512) ||
      !(usage.cost_usd === null || typeof usage.cost_usd === 'number' && Number.isFinite(usage.cost_usd) && usage.cost_usd >= 0 && usage.cost_usd <= 100) ||
      !Number.isInteger(usage.latency_ms) || (usage.latency_ms as number) < 0 || (usage.latency_ms as number) > 30_000) return null;
  if (v.overview.length > 360 || v.overview_evidence_refs.length > 4 || v.highlights.length > 4 || v.limitations.length > 12) return null;
  const highlights = v.highlights.map((h) => h && typeof h === 'object' ? h as Record<string, unknown> : null);
  if (highlights.some((h) => !h || !['road', 'weather', 'camera', 'general'].includes(String(h.category)) || typeof h.text !== 'string' || h.text.length > 220 || !Array.isArray(h.evidence_refs) || !h.evidence_refs.length || h.evidence_refs.length > 3 || !h.evidence_refs.every((x) => typeof x === 'string'))) return null;
  if (![...v.overview_evidence_refs, ...v.limitations].every((x) => typeof x === 'string') ||
      (v.status === 'available' && (!v.overview.trim() || v.overview_evidence_refs.length === 0)) ||
      (v.status === 'insufficient_evidence' && (v.overview !== '' || v.overview_evidence_refs.length > 0 || v.highlights.length > 0))) return null;
  return v as unknown as BriefingResultV1;
}

export async function fetchBriefingEvidence(request: BriefingEvidenceRequestV1, signal: AbortSignal): Promise<BriefingResultV1> {
  const response = await fetch('/api/briefings/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request), signal });
  if (!response.ok) throw new Error(response.status === 504 ? 'timeout' : 'request_failed');
  const result = normalizeBriefingResult(await response.json());
  if (!result) throw new Error('invalid_response');
  if (result.attempt_id !== request.attempt_id || result.origin_name !== request.journey.origin.name || result.destination_name !== request.journey.destination.name) throw new Error('invalid_response');
  return result;
}

export function createCameraOpportunity<T>(cameraResult: Promise<T> | null, startedAt: number, deadlineMs = 15_000,
  now: () => number = () => performance.now(), schedule: typeof setTimeout = setTimeout): { promise: Promise<T | null>; cancel: () => void } {
  if (!cameraResult) return { promise: Promise.resolve(null), cancel: () => undefined };
  const remaining = Math.max(0, deadlineMs - (now() - startedAt));
  if (remaining === 0) return { promise: Promise.resolve(null), cancel: () => undefined };
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let resolveDeadline: ((value: null) => void) | null = null;
  const deadline = new Promise<null>((resolve) => {
    resolveDeadline = resolve;
    timeout = schedule(() => resolve(null), remaining);
  });
  const promise = Promise.race([cameraResult, deadline]).finally(() => { if (timeout !== null) clearTimeout(timeout); timeout = null; });
  const cancel = () => { if (timeout !== null) clearTimeout(timeout); timeout = null; resolveDeadline?.(null); };
  return { promise, cancel };
}

export function waitForCameraOpportunity<T>(cameraResult: Promise<T> | null, startedAt: number, deadlineMs = 15_000,
  now: () => number = () => performance.now(), schedule: typeof setTimeout = setTimeout): Promise<T | null> {
  return createCameraOpportunity(cameraResult, startedAt, deadlineMs, now, schedule).promise;
}

export function startBriefingRequest(request: BriefingEvidenceRequestV1, signal?: AbortSignal, deadlineMs = 35_000): { promise: Promise<BriefingResultV1>; controller: AbortController; timeout: ReturnType<typeof setTimeout>; wasTimedOut: () => boolean } {
  const controller = new AbortController();
  let timedOut = false;
  const parentAbort = () => controller.abort();
  if (signal?.aborted) controller.abort(); else signal?.addEventListener('abort', parentAbort, { once: true });
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, deadlineMs);
  const promise = fetchBriefingEvidence(request, controller.signal).finally(() => {
    clearTimeout(timeout);
    signal?.removeEventListener('abort', parentAbort);
  });
  return { promise, controller, timeout, wasTimedOut: () => timedOut };
}
