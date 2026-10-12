import type { AnalysisRequest, AnalysisState } from './analysisTypes';

export const CAMERA_VISION_TIMEOUT_MS = 70_000;

export function startCameraVisionTimeout(
  controller: AbortController,
  onTimeout: () => void,
  schedule: typeof setTimeout = setTimeout,
): ReturnType<typeof setTimeout> {
  return schedule(() => {
    onTimeout();
    controller.abort();
  }, CAMERA_VISION_TIMEOUT_MS);
}

export type VisionStatus = 'available' | 'partial' | 'insufficient_evidence' | 'unavailable' | 'error';
export type VisionFailureCode =
  | 'no_selected_intersection' | 'journey_context_mismatch' | 'no_eligible_frames' | 'stale_frames_only'
  | 'configuration_missing' | 'provider_unavailable' | 'rate_limited' | 'timeout' | 'provider_error'
  | 'invalid_model_output' | 'budget_exhausted' | 'insufficient_evidence';
export type CameraVisionObservation = {
  schema_version: string;
  prompt_version: string;
  status: VisionStatus;
  failure_code: VisionFailureCode | null;
  intersection_id: string | null;
  intersection_name: string | null;
  street_names: string[];
  distance_from_destination_metres: number | null;
  official_camera_page_url: string | null;
  source_name: string;
  attribution: string;
  included_views: Array<{
    view_id: string; direction_label: string | null; retrieved_at: string; source_capture_at: string | null;
    sha256: string; snapshot_identity: string; content_type: string; width: number; height: number; byte_length: number;
  }>;
  excluded_views: Array<{ view_id: string; direction_label: string | null; reason: 'missing' | 'stale' | 'invalid_or_mismatched' | 'oversized' }>;
  views: Array<{
    view_id: string;
    road_surface: 'dry_looking' | 'wet_looking' | 'snow_or_ice_looking' | 'unclear' | 'not_observable';
    visibility: 'adequate' | 'limited' | 'obscured' | 'not_observable';
    vehicle_activity: 'none_visible' | 'some_visible' | 'queue_apparent' | 'unclear' | 'not_observable';
    conditions: Array<'visible_precipitation' | 'fog_or_haze' | 'glare' | 'obstruction' | 'image_quality_limited'>;
    uncertainty: 'low' | 'moderate' | 'high';
    note: string | null;
  }>;
  intersection_summary: string | null;
  summary_evidence_view_ids: string[];
  requested_model_id: string;
  actual_provider_id: string | null;
  actual_endpoint_id: string | null;
  inferred_at: string | null;
  usage: { input_tokens: number | null; output_tokens: number | null; total_tokens: number | null; cost_usd: number | null; latency_ms: number | null };
};
export type CameraVisionResult = {
  observation: CameraVisionObservation;
  cache_reused: boolean;
  provider_error: { http_status: number; error_code: number | string | null; category: string; explanation: string | null } | null;
  semantic_error_code: 'view_identity_or_order_mismatch' | 'unknown_summary_evidence_view' | 'summary_evidence_relationship_invalid' | null;
  semantic_mismatch: { expected_view_count: number; actual_view_count: number; first_mismatched_position: number | null } | null;
};
export type JourneyCameraEvidence = {
  attempt_id: number;
  trip: AnalysisRequest;
  camera_vision: { status: 'pending' } | { status: 'complete'; result: CameraVisionResult };
};
export type JourneyEvidenceState = { analysis: AnalysisState; camera_vision: JourneyCameraEvidence | null };

const failureCodes: VisionFailureCode[] = [
  'no_selected_intersection', 'journey_context_mismatch', 'no_eligible_frames', 'stale_frames_only',
  'configuration_missing', 'provider_unavailable', 'rate_limited', 'timeout', 'provider_error',
  'invalid_model_output', 'budget_exhausted', 'insufficient_evidence',
];
const statuses: VisionStatus[] = ['available', 'partial', 'insufficient_evidence', 'unavailable', 'error'];
const surfaces = ['dry_looking', 'wet_looking', 'snow_or_ice_looking', 'unclear', 'not_observable'] as const;
const visibilities = ['adequate', 'limited', 'obscured', 'not_observable'] as const;
const activities = ['none_visible', 'some_visible', 'queue_apparent', 'unclear', 'not_observable'] as const;
const conditions = ['visible_precipitation', 'fog_or_haze', 'glare', 'obstruction', 'image_quality_limited'] as const;
const excludedReasons = ['missing', 'stale', 'invalid_or_mismatched', 'oversized'] as const;
const semanticCodes = ['view_identity_or_order_mismatch', 'unknown_summary_evidence_view', 'summary_evidence_relationship_invalid'] as const;
const providerCategories = ['account_model_provider_restriction', 'no_eligible_provider', 'unsupported_request_parameters', 'invalid_model_or_provider_identifier', 'other_provider_error', 'unknown'] as const;
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);
const isText = (value: unknown, max = 512): value is string => typeof value === 'string' && value.length <= max && !/^data:image\//i.test(value);
const nullableText = (value: unknown, max = 512): value is string | null => value === null || isText(value, max);
const isNumber = (value: unknown, min = 0, max = Number.MAX_SAFE_INTEGER): value is number => typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max;
const isDate = (value: unknown): value is string | null => value === null || (isText(value, 64) && Number.isFinite(Date.parse(value)));
const isOneOf = <T extends string>(value: unknown, values: readonly T[]): value is T => typeof value === 'string' && values.includes(value as T);

function normalizeObservation(value: unknown): CameraVisionObservation | null {
  if (!isRecord(value) || !isText(value.schema_version, 64) || !isText(value.prompt_version, 64) ||
      !isOneOf(value.status, statuses) || !(value.failure_code === null || isOneOf(value.failure_code, failureCodes)) ||
      !nullableText(value.intersection_id, 256) || !nullableText(value.intersection_name, 512) ||
      !Array.isArray(value.street_names) || !value.street_names.every((item) => isText(item, 256)) ||
      !(value.distance_from_destination_metres === null || isNumber(value.distance_from_destination_metres, 0, 1_000_000)) ||
      !nullableText(value.official_camera_page_url, 2048) || !isText(value.source_name, 256) || !isText(value.attribution, 512) ||
      !Array.isArray(value.included_views) || !Array.isArray(value.excluded_views) || !Array.isArray(value.views) ||
      !nullableText(value.intersection_summary, 240) || !Array.isArray(value.summary_evidence_view_ids) ||
      !value.summary_evidence_view_ids.every((item) => isText(item, 128)) || !isText(value.requested_model_id, 128) ||
      !nullableText(value.actual_provider_id, 128) || !nullableText(value.actual_endpoint_id, 128) || !isDate(value.inferred_at) ||
      !isRecord(value.usage)) return null;

  const included = value.included_views.map((item) => {
    if (!isRecord(item) || !isText(item.view_id, 128) || !nullableText(item.direction_label, 128) ||
        !isDate(item.retrieved_at) || item.retrieved_at === null || !isDate(item.source_capture_at) ||
        !/^[a-f0-9]{64}$/.test(String(item.sha256)) || !isText(item.snapshot_identity, 256) ||
        !isText(item.content_type, 128) || !isNumber(item.width, 1, 20_000) || !isNumber(item.height, 1, 20_000) ||
        !isNumber(item.byte_length, 1, 10 * 1024 * 1024)) return null;
    return { view_id: item.view_id, direction_label: item.direction_label, retrieved_at: item.retrieved_at,
      source_capture_at: item.source_capture_at, sha256: item.sha256, snapshot_identity: item.snapshot_identity,
      content_type: item.content_type, width: item.width, height: item.height, byte_length: item.byte_length };
  });
  const excluded = value.excluded_views.map((item) => {
    if (!isRecord(item) || !isText(item.view_id, 128) || !nullableText(item.direction_label, 128) || !isOneOf(item.reason, excludedReasons)) return null;
    return { view_id: item.view_id, direction_label: item.direction_label, reason: item.reason };
  });
  const views = value.views.map((item) => {
    if (!isRecord(item) || !isText(item.view_id, 128) || !isOneOf(item.road_surface, surfaces) ||
        !isOneOf(item.visibility, visibilities) || !isOneOf(item.vehicle_activity, activities) ||
        !Array.isArray(item.conditions) || !item.conditions.every((tag) => isOneOf(tag, conditions)) ||
        !isOneOf(item.uncertainty, ['low', 'moderate', 'high']) || !nullableText(item.note, 160)) return null;
    return { view_id: item.view_id, road_surface: item.road_surface, visibility: item.visibility,
      vehicle_activity: item.vehicle_activity, conditions: item.conditions, uncertainty: item.uncertainty, note: item.note };
  });
  const usage = value.usage;
  if (included.some((item) => item === null) || excluded.some((item) => item === null) || views.some((item) => item === null) ||
      ![usage.input_tokens, usage.output_tokens, usage.total_tokens].every((n) => n === null || isNumber(n, 0, 10_000_000)) ||
      !(usage.cost_usd === null || isNumber(usage.cost_usd, 0, 100)) || !(usage.latency_ms === null || isNumber(usage.latency_ms, 0, 300_000))) return null;
  return {
    schema_version: value.schema_version, prompt_version: value.prompt_version, status: value.status, failure_code: value.failure_code,
    intersection_id: value.intersection_id, intersection_name: value.intersection_name, street_names: value.street_names,
    distance_from_destination_metres: value.distance_from_destination_metres, official_camera_page_url: value.official_camera_page_url,
    source_name: value.source_name, attribution: value.attribution, included_views: included as CameraVisionObservation['included_views'],
    excluded_views: excluded as CameraVisionObservation['excluded_views'], views: views as CameraVisionObservation['views'],
    intersection_summary: value.intersection_summary, summary_evidence_view_ids: value.summary_evidence_view_ids,
    requested_model_id: value.requested_model_id, actual_provider_id: value.actual_provider_id,
    actual_endpoint_id: value.actual_endpoint_id, inferred_at: value.inferred_at,
    usage: { input_tokens: usage.input_tokens as number | null, output_tokens: usage.output_tokens as number | null,
      total_tokens: usage.total_tokens as number | null, cost_usd: usage.cost_usd as number | null, latency_ms: usage.latency_ms as number | null },
  };
}

export function normalizeCameraVisionResult(value: unknown): CameraVisionResult | null {
  if (!isRecord(value) || typeof value.cache_reused !== 'boolean') return null;
  const observation = normalizeObservation(value.observation);
  if (!observation) return null;
  let providerError: CameraVisionResult['provider_error'] = null;
  if (value.provider_error !== null) {
    const error = value.provider_error;
    if (!isRecord(error) || !isNumber(error.http_status, 100, 599) ||
        !(error.error_code === null || typeof error.error_code === 'number' || isText(error.error_code, 64)) ||
        !isOneOf(error.category, providerCategories) || !nullableText(error.explanation, 120)) return null;
    providerError = { http_status: error.http_status, error_code: error.error_code, category: error.category, explanation: error.explanation };
  }
  if (!(value.semantic_error_code === null || isOneOf(value.semantic_error_code, semanticCodes))) return null;
  let semanticMismatch: CameraVisionResult['semantic_mismatch'] = null;
  if (value.semantic_mismatch !== undefined && value.semantic_mismatch !== null) {
    const mismatch = value.semantic_mismatch;
    if (!isRecord(mismatch) || !Number.isInteger(mismatch.expected_view_count) || !isNumber(mismatch.expected_view_count, 0, 5) ||
        !Number.isInteger(mismatch.actual_view_count) || !isNumber(mismatch.actual_view_count, 0, 5) ||
        !(mismatch.first_mismatched_position === null ||
          (Number.isInteger(mismatch.first_mismatched_position) && isNumber(mismatch.first_mismatched_position, 1, 6)))) return null;
    semanticMismatch = { expected_view_count: mismatch.expected_view_count, actual_view_count: mismatch.actual_view_count,
      first_mismatched_position: mismatch.first_mismatched_position };
  }
  return { observation, cache_reused: value.cache_reused, provider_error: providerError, semantic_error_code: value.semantic_error_code,
    semantic_mismatch: semanticMismatch };
}

export async function fetchCameraVision(trip: AnalysisRequest, signal: AbortSignal): Promise<CameraVisionResult> {
  const response = await fetch('/api/cameras/observe', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(trip), signal,
  });
  if (!response.ok) throw new Error('Camera vision request unavailable');
  const result = normalizeCameraVisionResult(await response.json());
  if (!result) throw new Error('Camera vision result invalid');
  return result;
}

export function isCurrentVisionAttempt(attemptId: number, currentAttemptId: number, tripKey: string, activeTripKey: string | null): boolean {
  return attemptId === currentAttemptId && tripKey === activeTripKey;
}

export function unavailableCameraVision(failureCode: VisionFailureCode): CameraVisionResult {
  return {
    observation: {
      schema_version: 'camera-observation-v1', prompt_version: 'camera-visual-observer-v2', status: 'unavailable',
      failure_code: failureCode, intersection_id: null, intersection_name: null, street_names: [],
      distance_from_destination_metres: null, official_camera_page_url: null,
      source_name: 'City of Vancouver Open Data Portal', attribution: 'Contains information licensed under the Open Government Licence – Vancouver.',
      included_views: [], excluded_views: [], views: [], intersection_summary: null, summary_evidence_view_ids: [],
      requested_model_id: 'google/gemma-4-31b-it', actual_provider_id: null, actual_endpoint_id: null, inferred_at: null,
      usage: { input_tokens: null, output_tokens: null, total_tokens: null, cost_usd: null, latency_ms: null },
    },
    cache_reused: false, provider_error: null, semantic_error_code: null, semantic_mismatch: null,
  };
}

export function cameraVisionFailureResult(error: unknown, timedOut: boolean): CameraVisionResult {
  const failureCode: VisionFailureCode = timedOut ? 'timeout' :
    error instanceof Error && error.message === 'Camera vision result invalid' ? 'invalid_model_output' : 'provider_unavailable';
  return unavailableCameraVision(failureCode);
}

export function retainCurrentCameraVision(
  current: JourneyCameraEvidence | null,
  attemptId: number,
  result: CameraVisionResult,
): JourneyCameraEvidence | null {
  return current?.attempt_id === attemptId ? { ...current, camera_vision: { status: 'complete', result } } : current;
}
