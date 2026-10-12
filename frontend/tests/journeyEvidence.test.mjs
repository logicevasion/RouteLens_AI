import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

async function loadTypeScript(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8');
  const javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`);
}

const evidence = await loadTypeScript('../src/journeyEvidence.ts');
const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');
const weatherModule = await loadTypeScript('../src/weather.ts');
const trip = () => ({
  mode: 'drive', origin: { name: 'Richmond', latitude: 49.17, longitude: -123.14 },
  destination: { name: 'Vancouver', latitude: 49.28, longitude: -123.12 },
  selected_route: { candidate_id: 'route-1', geometry: { type: 'LineString', coordinates: [[-123.14, 49.17], [-123.12, 49.28]] }, distance_meters: 12000, duration_seconds: 900, label: 'Route 1' },
});
const sourceStatus = (source, dataset_id, values = {}) => ({
  source, dataset_id, success: true, available: true, fetched_at: '2026-10-11T12:03:00Z',
  cache_hit: false, refreshed: true, stale: false, cache_age_seconds: 0, error: null,
  records_received: 2, records_normalized: 2, records_skipped: 0, ...values,
});
const finding = (id, classification = 'nearby') => ({
  event: { id, source: 'City of Vancouver Road Ahead', source_dataset_id: 'road-ahead-work', source_record_id: `record-${id}`,
    event_type: 'construction', title: 'Road work', description: null, geometry: null, latitude: null, longitude: null,
    severity: null, status: 'active', schedule_text: null, restriction_text: null, observed_at: null, updated_at: null,
    source_url: null, relevance_reason: 'nearby', source_metadata: {}, attribution: 'City of Vancouver' },
  classification, distance_meters: 65, detail: { event_id: id, source_url: null, availability: 'no_supported_fields', title: null,
    location: null, description: null, status: null, schedule_text: null, restriction_text: null, exceptions: null,
    posted_text: null, updated_text: null, retrieved_at: null, from_cache: false, stale: false, error: null },
});
const weatherStatus = (dataset_id, values = {}) => ({
  source: dataset_id.startsWith('onecall') ? 'OpenWeather' : 'ECCC GeoMet/SWOB', dataset_id,
  success: true, available: true, fetched_at: '2026-10-11T12:03:00Z', cache_hit: false,
  refreshed: true, stale: false, cache_age_seconds: 0, error: null, ...values,
});
const fullWeather = () => ({
  openweather_current: { status: weatherStatus('onecall4_current'), weather: {
    source: 'OpenWeather', product: 'onecall4_current', observed_at: '2026-10-11T12:00:00Z', fetched_at: '2026-10-11T12:03:00Z',
    requested_coordinates: { latitude: 49.28, longitude: -123.12 }, provider_coordinates: { latitude: 49.28, longitude: -123.12 },
    temperature_c: 8, feels_like_c: 7, condition: { code: 804, group: 'Clouds', description: 'overcast' }, humidity_pct: 80,
    wind_speed_m_s: 2, wind_direction_deg: 180, wind_gust_m_s: null, visibility_m: 10000, rain_1h_mm: null, snow_1h_mm: null,
  } },
  openweather_forecast: { status: weatherStatus('onecall4_timeline_15min'), intervals: [{
    source: 'OpenWeather', product: 'onecall4_timeline_15min', forecast_at: '2026-10-11T12:15:00Z', fetched_at: '2026-10-11T12:03:00Z',
    requested_coordinates: { latitude: 49.28, longitude: -123.12 }, precipitation_probability_pct: 0, temperature_c: 8,
    feels_like_c: 7, condition: null, humidity_pct: 80, wind_speed_m_s: 2, wind_direction_deg: null,
    wind_gust_m_s: null, visibility_m: 10000, rain_1h_mm: null, rain_3h_mm: null, snow_1h_mm: null, snow_3h_mm: null,
  }], coverage: { evaluation_time: '2026-10-11T12:03:00Z', window_end: '2026-10-11T15:03:00Z', first_interval_at: '2026-10-11T12:15:00Z',
    last_interval_at: '2026-10-11T12:15:00Z', expected_interval_count: 1, returned_interval_count: 1, missing_intervals: [],
    malformed_records: 0, duplicate_records: 0, initial_page_only: false, continuous: true } },
  eccc_status: weatherStatus('swob-realtime'), eccc_attribution: 'ECCC GeoMet/SWOB', eccc_observations: [{
    observation: { source: 'ECCC GeoMet/SWOB', station_id: 'station-1', station_name: 'Harbour',
      source_record_id: 'record-123', station_identifiers: { climate_id: '1234567', wmo_id: '71234' }, latitude: 49.29, longitude: -123.12,
      observed_at: '2026-10-11T11:45:00Z', retrieved_at: '2026-10-11T12:03:00Z', temperature: { value: 8, unit: '°C', source_field: 'air_temp', interval_seconds: null, quality_code: null },
      relative_humidity: null, precipitation: [], wind_speed: null, wind_direction: null, snow_depth: null, attribution: 'ECCC GeoMet/SWOB' },
    distance_meters: 1200, observation_age_seconds: 1080, observation_stale: false, cache_stale: false,
    useful_measurements: ['temperature'], selection_reason: 'nearby station',
  }],
});
const analysis = (overrides = {}) => ({
  trip: trip(), status: 'available', findings: [finding('ra-1', 'direct_overlap')], drivebc_findings: [{
    event: { ...finding('bc-1').event, source: 'DriveBC Open511', source_dataset_id: 'drivebc-open511-active', source_record_id: 'bc-source-1', geometry: { type: 'Point', coordinates: [-123.12, 49.28] } },
    classification: 'nearby', distance_meters: 100, geometry_basis: 'point_proximity', enrichment_applicability: 'not_applicable',
    source_evidence: { event_type: 'incident', status: null, severity: null, event_subtypes: [], roads: [], schedule: null,
      schedule_text: null, direction_assessment: 'undetermined', temporal_applicability: 'unknown', current_impact: 'not_established' },
  }], regional_events: [{ id: 'map-only' }], unmatchable_events: [],
  source_statuses: [sourceStatus('City of Vancouver Road Ahead', 'road-ahead-work'), sourceStatus('DriveBC Open511', 'drivebc-open511-active')],
  destination_weather: fullWeather(), summary: 'source summary', analyzed_at: '2026-10-11T12:03:00Z', ...overrides,
});
const cameraResult = (status = 'available') => ({ observation: {
  schema_version: 'camera-observation-v1', prompt_version: 'camera-visual-observer-v2', status, failure_code: null,
  intersection_id: 'intersection-9', intersection_name: 'Main and 1st', street_names: ['Main', '1st'],
  distance_from_destination_metres: 250, official_camera_page_url: 'https://trafficcams.vancouver.ca/',
  source_name: 'City of Vancouver Open Data Portal', attribution: 'Open Government Licence – Vancouver',
  included_views: [{ view_id: 'view-north', direction_label: 'Northbound', retrieved_at: '2026-10-11T12:02:00Z', source_capture_at: '2026-10-11T12:01:00Z',
    sha256: 'a'.repeat(64), snapshot_identity: 'snapshot-1', content_type: 'image/jpeg', width: 640, height: 480, byte_length: 2000 }],
  excluded_views: [], views: [{ view_id: 'view-north', road_surface: 'wet_looking', visibility: 'adequate', vehicle_activity: 'some_visible',
    conditions: [], uncertainty: 'moderate', note: 'Surface appears wet.' }], intersection_summary: null, summary_evidence_view_ids: [],
  requested_model_id: 'google/gemma-4-31b-it', actual_provider_id: 'provider-a', actual_endpoint_id: 'endpoint-a', inferred_at: '2026-10-11T12:02:30Z',
  usage: { input_tokens: 10, output_tokens: 10, total_tokens: 20, cost_usd: 0.01, latency_ms: 5000 },
}, cache_reused: false, provider_error: null, semantic_error_code: null, semantic_mismatch: null });
const inputs = (overrides = {}) => ({ trip: trip(), attempt_id: 7, assembled_at: '2026-10-11T12:04:00Z',
  analysis: { status: 'success', result: analysis(), error: null },
  camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'complete', result: cameraResult() } }, ...overrides });

test('current lifecycle handoff binds successful analysis and pending camera to canonical route and attempt', () => {
  const state = { attempt_id: 7, trip: trip(), analysis: inputs().analysis,
    camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'pending' } } };
  const bundle = evidence.deriveCurrentJourneyEvidence(state, trip(), '2026-10-11T12:04:00Z');
  assert.equal(bundle.identity.attempt_id, 7);
  assert.deepEqual(bundle.identity.trip, trip());
  assert.equal(bundle.identity.trip.selected_route.candidate_id, 'route-1');
  assert.deepEqual(bundle.identity.trip.selected_route.geometry, trip().selected_route.geometry);
  assert.equal(bundle.identity.analyzed_at, '2026-10-11T12:03:00Z');
  assert.equal(bundle.assembled_at, '2026-10-11T12:04:00Z');
  assert.equal(bundle.readiness.status, 'partial');
  assert.equal(bundle.readiness.ready_for_briefing, true);
  assert.equal(bundle.sources.road_ahead.findings[0].event.id, 'ra-1');
  assert.equal(bundle.sources.openweather_current.weather.temperature_c, 8);

  const completed = evidence.deriveCurrentJourneyEvidence({ ...state, camera_vision: inputs().camera_vision }, trip(), '2026-10-11T12:05:00Z');
  assert.equal(completed.identity.attempt_id, bundle.identity.attempt_id);
  assert.equal(completed.sources.camera_vision.result.observation.intersection_id, 'intersection-9');
  assert.equal(completed.sources.road_ahead.findings[0].event.id, 'ra-1');
});

test('current lifecycle handoff drops invalidated, mismatched, failed, and superseded evidence', () => {
  const pending = { status: 'loading', result: null, error: null };
  assert.equal(evidence.deriveCurrentJourneyEvidence({ attempt_id: null, trip: null, analysis: pending, camera_vision: null }, trip(), '2026-10-11T12:04:00Z'), null);
  const staleCamera = { attempt_id: 6, trip: trip(), camera_vision: { status: 'complete', result: cameraResult() } };
  assert.equal(evidence.deriveCurrentJourneyEvidence({ attempt_id: 7, trip: trip(), analysis: inputs().analysis, camera_vision: staleCamera }, trip(), '2026-10-11T12:04:00Z'), null);
  const nextAttempt = evidence.deriveCurrentJourneyEvidence({ attempt_id: 8, trip: trip(), analysis: pending,
    camera_vision: { attempt_id: 8, trip: trip(), camera_vision: { status: 'pending' } } }, trip(), '2026-10-11T12:04:00Z');
  assert.equal(nextAttempt.identity.attempt_id, 8);
  assert.equal(nextAttempt.sources.camera_vision.availability, 'pending');
  assert.equal(nextAttempt.readiness.status, 'pending');
  assert.equal(nextAttempt.readiness.ready_for_briefing, false);
  const changed = trip();
  changed.destination.latitude += 0.01;
  assert.equal(evidence.deriveCurrentJourneyEvidence({ attempt_id: 7, trip: trip(), analysis: pending, camera_vision: null }, changed, '2026-10-11T12:04:00Z'), null);
  const failed = evidence.deriveCurrentJourneyEvidence({ attempt_id: 7, trip: trip(),
    analysis: { status: 'error', result: null, error: 'analysis failed' }, camera_vision: inputs().camera_vision }, trip(), '2026-10-11T12:04:00Z');
  assert.equal(failed.readiness.status, 'failed');
  assert.equal(failed.readiness.ready_for_briefing, false);
  assert.equal(failed.sources.road_ahead.availability, 'unknown');
});

test('App derives the handoff from lifecycle state without adding provider calls or UI', () => {
  assert.match(appSource, /deriveCurrentJourneyEvidence\(journeyEvidenceState, currentTrip/);
  assert.match(appSource, /attempt_id: requestId, trip: request, analysis: \{ status: 'loading'/);
  assert.match(appSource, /retainCurrentCameraVision\(current, requestId/);
  assert.match(appSource, /isCurrentAnalysisRequest\(requestId, analysisSequence\.current, requestKey, activeAnalysisKey\.current\)/);
  assert.match(appSource, /isCurrentVisionAttempt\(visionAttemptId, visionSequence\.current, visionAttemptKey, activeVisionKey\.current\)/);
  assert.match(appSource, /if \(routeState\.status === 'ready' && routeState\.selectedRoute\?\.id !== route\.id\) invalidateAnalysis\(\)/);
  assert.match(appSource, /async function findRoutes\(\) \{[\s\S]*?invalidateAnalysis\(\)/);
  assert.match(appSource, /setJourneyEvidenceState\(\{ attempt_id: null/);
  assert.equal((appSource.match(/fetchCameraVision\(/g) ?? []).length, 1);
  assert.doesNotMatch(evidence.deriveCurrentJourneyEvidence.toString(), /fetch\(|OpenRouter/i);
});

test('assembles distinct available road, weather, SWOB, and single-view camera sections', () => {
  const bundle = evidence.assembleJourneyEvidence(inputs());
  assert.equal(bundle.schema_version, 'journey-evidence-v1');
  assert.equal(bundle.readiness.status, 'ready');
  assert.equal(bundle.sources.road_ahead.findings[0].classification, 'direct_overlap');
  assert.equal(bundle.sources.drivebc_open511.findings[0].geometry_basis, 'point_proximity');
  assert.equal(bundle.sources.openweather_current.weather.observed_at, '2026-10-11T12:00:00Z');
  assert.equal(bundle.sources.openweather_forecast.intervals[0].forecast_at, '2026-10-11T12:15:00Z');
  assert.equal(bundle.sources.eccc_swob.observations[0].observation.source_record_id, 'record-123');
  assert.equal(bundle.sources.camera_vision.result.observation.included_views[0].direction_label, 'Northbound');
  assert.equal(bundle.sources.camera_vision.result.observation.included_views[0].sha256, 'a'.repeat(64));
  assert.equal(bundle.sources.camera_vision.result.observation.included_views.length, 1);
  assert.equal(bundle.sources.camera_vision.result.observation.included_views[0].retrieved_at, '2026-10-11T12:02:00Z');
  assert.equal(bundle.sources.camera_vision.result.observation.included_views[0].source_capture_at, '2026-10-11T12:01:00Z');
  assert.equal(bundle.sources.camera_vision.result.observation.inferred_at, '2026-10-11T12:02:30Z');
  assert.equal(bundle.sources.camera_vision.result.observation.distance_from_destination_metres, 250);
  assert.equal(bundle.sources.camera_vision.result.observation.views[0].view_id, 'view-north');
  assert.equal(bundle.sources.camera_vision.result.observation.views[0].road_surface, 'wet_looking');
  assert.equal(bundle.sources.camera_vision.result.observation.views[0].vehicle_activity, 'some_visible');
  assert.equal(bundle.sources.openweather_current.weather.rain_1h_mm, null);
  assert.equal(bundle.sources.road_ahead.findings[0].event.severity, null);
  assert.equal(bundle.sources.drivebc_open511.findings[0].source_evidence.current_impact, 'not_established');
  assert.equal('delay' in bundle.sources.camera_vision.result.observation, false);
  assert.equal('route_congestion' in bundle.sources.camera_vision.result.observation, false);
  assert.equal('regional_events' in bundle.sources, false);
});

test('keeps successful empty road findings distinct from source failures', () => {
  const noFindings = analysis({ findings: [], drivebc_findings: [] });
  const bundle = evidence.assembleJourneyEvidence(inputs({ analysis: { status: 'success', result: noFindings, error: null } }));
  assert.equal(bundle.sources.road_ahead.availability, 'empty');
  assert.equal(bundle.sources.drivebc_open511.availability, 'empty');
  assert.equal(bundle.readiness.status, 'ready');
  assert.equal(bundle.readiness.ready_for_briefing, true);
  const failed = analysis({ source_statuses: [sourceStatus('City of Vancouver Road Ahead', 'road-ahead-work', { success: false, available: false, error: 'unavailable' }),
    sourceStatus('DriveBC Open511', 'drivebc-open511-active', { success: false, available: false, error: 'unavailable' })] });
  const failedBundle = evidence.assembleJourneyEvidence(inputs({ analysis: { status: 'success', result: failed, error: null } }));
  assert.equal(failedBundle.sources.road_ahead.availability, 'failed');
  assert.equal(failedBundle.sources.drivebc_open511.availability, 'failed');
  assert.equal(failedBundle.sources.drivebc_open511.status.error, 'unavailable');
  assert.equal(failedBundle.sources.road_ahead.statuses[0].error, 'unavailable');
  assert.equal(failedBundle.sources.openweather_current.availability, 'available');
  assert.equal(failedBundle.sources.camera_vision.availability, 'available');
  assert.equal(failedBundle.readiness.status, 'partial');
});

test('keeps current observation and forecast target time in separate fields', () => {
  const bundle = evidence.assembleJourneyEvidence(inputs());
  assert.equal(bundle.sources.openweather_current.weather.observed_at, '2026-10-11T12:00:00Z');
  assert.equal(bundle.sources.openweather_forecast.intervals[0].forecast_at, '2026-10-11T12:15:00Z');
  assert.equal(bundle.sources.openweather_forecast.intervals[0].precipitation_probability_pct, 0);
});

test('retains SWOB station identity, source record, actual observation time, and identifiers', () => {
  const station = evidence.assembleJourneyEvidence(inputs()).sources.eccc_swob.observations[0].observation;
  assert.equal(station.station_id, 'station-1');
  assert.equal(station.source_record_id, 'record-123');
  assert.equal(station.observed_at, '2026-10-11T11:45:00Z');
  assert.deepEqual(station.station_identifiers, { climate_id: '1234567', wmo_id: '71234' });
});

test('preserves camera authoritative provenance separately from model observations', () => {
  const observation = evidence.assembleJourneyEvidence(inputs()).sources.camera_vision.result.observation;
  assert.equal(observation.intersection_id, 'intersection-9');
  assert.equal(observation.distance_from_destination_metres, 250);
  assert.equal(observation.included_views[0].view_id, 'view-north');
  assert.equal(observation.included_views[0].source_capture_at, '2026-10-11T12:01:00Z');
  assert.equal(observation.inferred_at, '2026-10-11T12:02:30Z');
  assert.equal(observation.views[0].road_surface, 'wet_looking');
});

test('camera pending and insufficient evidence do not create positive camera claims', () => {
  const pending = evidence.assembleJourneyEvidence(inputs({ camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'pending' } } }));
  assert.equal(pending.sources.camera_vision.availability, 'pending');
  assert.equal(pending.sources.camera_vision.result, null);
  const insufficientResult = cameraResult('insufficient_evidence');
  insufficientResult.observation.views = [{ view_id: 'view-north', road_surface: 'unclear', visibility: 'not_observable',
    vehicle_activity: 'unclear', conditions: [], uncertainty: 'high', note: null }];
  const insufficient = evidence.assembleJourneyEvidence(inputs({ camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'complete', result: insufficientResult } } }));
  assert.equal(insufficient.sources.camera_vision.availability, 'empty');
  assert.equal(insufficient.sources.camera_vision.result.observation.status, 'insufficient_evidence');
  assert.equal(insufficient.sources.camera_vision.result.observation.views[0].road_surface, 'unclear');
  assert.equal(insufficient.sources.camera_vision.result.observation.views[0].conditions.length, 0);
  assert.equal(insufficient.readiness.status, 'ready');
  const unavailableResult = cameraResult('unavailable');
  unavailableResult.observation.views = [];
  const unavailable = evidence.assembleJourneyEvidence(inputs({ camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'complete', result: unavailableResult } } }));
  assert.equal(unavailable.sources.camera_vision.availability, 'unavailable');
  assert.deepEqual(unavailable.sources.camera_vision.result.observation.views, []);
});

test('unknown missing sources and failed analysis are not represented as successful emptiness', () => {
  const unknown = evidence.assembleJourneyEvidence(inputs({ camera_vision: null }));
  assert.equal(unknown.sources.camera_vision.availability, 'unknown');
  assert.equal(unknown.readiness.status, 'partial');
  const failed = evidence.assembleJourneyEvidence(inputs({ analysis: { status: 'error', result: null, error: 'request failed' }, camera_vision: null }));
  assert.equal(failed.identity.analysis_status, 'failed');
  assert.equal(failed.identity.analysis_error, 'request failed');
  assert.equal(failed.identity.analyzed_at, null);
  assert.equal(failed.sources.road_ahead.availability, 'unknown');
  assert.equal(failed.readiness.status, 'failed');
  assert.equal(failed.readiness.ready_for_briefing, false);
  const pending = evidence.assembleJourneyEvidence(inputs({ analysis: { status: 'loading', result: null, error: null }, camera_vision: null }));
  assert.equal(pending.identity.analysis_status, 'pending');
  assert.equal(pending.readiness.status, 'pending');
  assert.equal(pending.readiness.ready_for_briefing, false);
  const notStarted = evidence.assembleJourneyEvidence(inputs({ analysis: { status: 'idle', result: null, error: null }, camera_vision: null }));
  assert.equal(notStarted.identity.analysis_status, 'unknown');
  assert.equal(notStarted.identity.analysis_error, null);
  assert.equal(notStarted.readiness.status, 'unknown');
  assert.equal(notStarted.readiness.ready_for_briefing, false);
});

test('camera pending or failed remains a usable partial bundle with road and weather evidence', () => {
  const pending = evidence.assembleJourneyEvidence(inputs({
    camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'pending' } },
  }));
  assert.equal(pending.readiness.status, 'partial');
  assert.equal(pending.readiness.ready_for_briefing, true);
  assert.equal(pending.sources.road_ahead.findings[0].event.id, 'ra-1');
  assert.equal(pending.sources.openweather_current.weather.temperature_c, 8);

  const timeoutResult = cameraResult('unavailable');
  timeoutResult.observation.failure_code = 'timeout';
  const timedOut = evidence.assembleJourneyEvidence(inputs({
    camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'complete', result: timeoutResult } },
  }));
  assert.equal(timedOut.readiness.status, 'partial');
  assert.equal(timedOut.readiness.ready_for_briefing, true);
  assert.equal(timedOut.sources.camera_vision.availability, 'unavailable');
  assert.equal(timedOut.sources.camera_vision.result.observation.failure_code, 'timeout');
  assert.equal(timedOut.sources.road_ahead.findings[0].event.id, 'ra-1');
  assert.equal(timedOut.sources.openweather_current.weather.temperature_c, 8);

  const providerFailureResult = cameraResult('error');
  providerFailureResult.observation.failure_code = 'provider_error';
  providerFailureResult.provider_error = { http_status: 503, error_code: 'unavailable', category: 'other_provider_error', explanation: 'provider unavailable' };
  const providerFailure = evidence.assembleJourneyEvidence(inputs({
    camera_vision: { attempt_id: 7, trip: trip(), camera_vision: { status: 'complete', result: providerFailureResult } },
  }));
  assert.equal(providerFailure.readiness.status, 'partial');
  assert.equal(providerFailure.sources.camera_vision.availability, 'failed');
  assert.equal(providerFailure.sources.camera_vision.result.provider_error.http_status, 503);
  assert.equal(providerFailure.sources.road_ahead.findings[0].event.id, 'ra-1');
  assert.equal(providerFailure.sources.openweather_current.weather.temperature_c, 8);
});

test('preserves canonical trip and selected route and rejects mismatched source identity', () => {
  const bundle = evidence.assembleJourneyEvidence(inputs());
  assert.deepEqual(bundle.identity.trip, trip());
  assert.equal(bundle.identity.trip.selected_route.candidate_id, 'route-1');
  const wrongTrip = trip(); wrongTrip.selected_route.candidate_id = 'other-route';
  assert.throws(() => evidence.assembleJourneyEvidence(inputs({ trip: wrongTrip })), /does not match/);
});

test('does not mutate inputs and produces deterministic output', () => {
  const source = inputs();
  const before = structuredClone(source);
  const first = evidence.assembleJourneyEvidence(source);
  const second = evidence.assembleJourneyEvidence(source);
  assert.deepEqual(source, before);
  assert.deepEqual(first, second);
});

test('weather normalization retains provider coordinates, amounts, and optional SWOB provenance', () => {
  const normalized = weatherModule.normalizeDestinationWeather({
    openweather_current: { weather: { observed_at: '2026-10-11T12:00:00Z', fetched_at: '2026-10-11T12:01:00Z',
      requested_coordinates: { latitude: 49.28, longitude: -123.12 }, provider_coordinates: { latitude: 49.281, longitude: -123.121 },
      rain_1h_mm: 1.2, snow_1h_mm: 0 }, status: { success: true, available: true } },
    openweather_forecast: { intervals: [{ forecast_at: '2026-10-11T12:15:00Z', fetched_at: '2026-10-11T12:01:00Z',
      requested_coordinates: { latitude: 49.28, longitude: -123.12 }, rain_3h_mm: 2, snow_1h_mm: 0 }], status: { success: true, available: true } },
    eccc_observations: [{ observation: { station_id: 'station-1', station_identifiers: { climate_id: '1234567' }, source_record_id: 'record-123',
      observed_at: '2026-10-11T11:45:00Z', retrieved_at: '2026-10-11T12:01:00Z' } }],
  });
  assert.deepEqual(normalized.openweather_current.weather.requested_coordinates, { latitude: 49.28, longitude: -123.12 });
  assert.deepEqual(normalized.openweather_current.weather.provider_coordinates, { latitude: 49.281, longitude: -123.121 });
  assert.equal(normalized.openweather_current.weather.rain_1h_mm, 1.2);
  assert.equal(normalized.openweather_current.weather.snow_1h_mm, 0);
  assert.equal(normalized.openweather_forecast.intervals[0].rain_3h_mm, 2);
  assert.equal(normalized.eccc_observations[0].observation.source_record_id, 'record-123');
  assert.deepEqual(normalized.eccc_observations[0].observation.station_identifiers, { climate_id: '1234567' });
  const legacy = weatherModule.normalizeDestinationWeather({ eccc_observations: [{ observation: { station_id: 'legacy', observed_at: '2026-10-11T11:00:00Z', retrieved_at: '2026-10-11T12:00:00Z' } }] });
  assert.equal(legacy.eccc_observations[0].observation.source_record_id, undefined);
});

test('successful sources with no usable weather values remain empty', () => {
  const result = analysis({ destination_weather: {
    openweather_current: { weather: null, status: weatherStatus('onecall4_current') },
    openweather_forecast: { intervals: [], coverage: null, status: weatherStatus('onecall4_timeline_15min') },
    eccc_status: weatherStatus('swob-realtime'), eccc_observations: [], eccc_attribution: 'ECCC GeoMet/SWOB',
  } });
  const bundle = evidence.assembleJourneyEvidence(inputs({ analysis: { status: 'success', result, error: null } }));
  assert.equal(bundle.sources.openweather_current.availability, 'empty');
  assert.equal(bundle.sources.openweather_forecast.availability, 'empty');
  assert.equal(bundle.sources.eccc_swob.availability, 'empty');
});

test('stale cached evidence after a refresh failure remains partial instead of empty', () => {
  const refreshFailure = { success: false, available: true, stale: true, cache_hit: true, refreshed: false };
  const result = analysis({ findings: [], drivebc_findings: [], source_statuses: [
    sourceStatus('City of Vancouver Road Ahead', 'road-ahead-work', refreshFailure),
    sourceStatus('DriveBC Open511', 'drivebc-open511-active', refreshFailure),
  ], destination_weather: {
    ...fullWeather(),
    openweather_current: { ...fullWeather().openweather_current, status: weatherStatus('onecall4_current', refreshFailure) },
  } });
  const bundle = evidence.assembleJourneyEvidence(inputs({ analysis: { status: 'success', result, error: null } }));
  assert.equal(bundle.sources.road_ahead.availability, 'partial');
  assert.equal(bundle.sources.drivebc_open511.availability, 'partial');
  assert.equal(bundle.sources.openweather_current.availability, 'partial');
  assert.equal(bundle.sources.openweather_current.status.stale, true);
  assert.equal(bundle.sources.road_ahead.statuses[0].stale, true);
});
