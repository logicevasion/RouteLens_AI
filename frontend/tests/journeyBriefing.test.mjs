import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import ts from 'typescript';

async function loadTypeScript(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`);
}
const briefing = await loadTypeScript('../src/journeyBriefing.ts');
const evidence = await loadTypeScript('../src/journeyEvidence.ts');
const vision = await loadTypeScript('../src/cameraVision.ts');
const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');
const attemptId = '11111111-1111-4111-8111-111111111111';
const secondAttemptId = '22222222-2222-4222-8222-222222222222';
const trip = () => ({ mode: 'drive', origin: { name: 'Richmond', latitude: 49.17, longitude: -123.14 }, destination: { name: 'Vancouver', latitude: 49.28, longitude: -123.12 }, selected_route: { candidate_id: 'route-1', geometry: { type: 'LineString', coordinates: [[-123.14, 49.17], [-123.12, 49.28]] }, distance_meters: 12000, duration_seconds: 900, label: 'Route 1' } });
const sourceStatus = (source, dataset_id, values = {}) => ({ source, dataset_id, success: true, available: true, fetched_at: '2026-10-11T12:03:00Z', cache_hit: false, refreshed: true, stale: false, cache_age_seconds: 0, error: null, records_received: 2, records_normalized: 2, records_skipped: 0, ...values });
const weatherStatus = (dataset_id) => ({ source: 'OpenWeather', dataset_id, success: true, available: true, fetched_at: '2026-10-11T12:03:00Z', stale: false, cache_stale: false });
const roadFinding = (id, classification, distance) => ({ event: { id: `event-${id}`, source: 'City of Vancouver Road Ahead', source_dataset_id: 'road-ahead-work', source_record_id: id, event_type: 'construction', title: `Road work ${id}`, description: 'Lane work', geometry: null, latitude: null, longitude: null, severity: null, status: 'active', schedule_text: null, restriction_text: null, observed_at: null, updated_at: null, source_url: 'https://example.invalid/source', relevance_reason: null, source_metadata: { raw: 'excluded' }, attribution: 'City of Vancouver' }, classification, distance_meters: distance, detail: { event_id: id, source_url: 'https://example.invalid/detail', availability: 'no_supported_fields', title: null, location: 'Main Street', description: null, status: null, schedule_text: null, restriction_text: null, exceptions: null, posted_text: null, updated_text: null, retrieved_at: null, from_cache: false, stale: false, error: null } });
const cameraResult = (status = 'available', direction = 'Northbound') => ({ observation: {
  schema_version: 'camera-observation-v1', prompt_version: 'camera-visual-observer-v2', status, failure_code: null,
  intersection_id: 'intersection-9', intersection_name: 'Main and 1st', street_names: ['Main', '1st'], distance_from_destination_metres: 250,
  official_camera_page_url: 'https://trafficcams.vancouver.ca/', source_name: 'City of Vancouver Open Data Portal', attribution: 'OGL Vancouver',
  included_views: [{ view_id: 'view-north', direction_label: direction, retrieved_at: '2026-10-11T12:02:00Z', source_capture_at: '2026-10-11T12:01:00Z', sha256: 'a'.repeat(64), snapshot_identity: 'private-cache-key', content_type: 'image/jpeg', width: 640, height: 480, byte_length: 2000 }, { view_id: 'view-south', direction_label: 'Southbound', retrieved_at: '2026-10-11T12:02:00Z', source_capture_at: null, sha256: 'b'.repeat(64), snapshot_identity: 'other', content_type: 'image/jpeg', width: 640, height: 480, byte_length: 2000 }],
  excluded_views: [], views: [{ view_id: 'view-north', road_surface: 'wet_looking', visibility: 'adequate', vehicle_activity: 'some_visible', conditions: ['visible_precipitation'], uncertainty: 'moderate', note: 'Surface appears wet.' }, { view_id: 'view-south', road_surface: 'dry_looking', visibility: 'adequate', vehicle_activity: 'none_visible', conditions: [], uncertainty: 'high', note: null }],
  intersection_summary: null, summary_evidence_view_ids: [], requested_model_id: 'google/gemma-4-31b-it', actual_provider_id: 'hidden-provider', actual_endpoint_id: 'hidden-endpoint', inferred_at: '2026-10-11T12:02:30Z', usage: { input_tokens: 10, output_tokens: 10, total_tokens: 20, cost_usd: 0.01, latency_ms: 5000 },
}, cache_reused: false, provider_error: null, semantic_error_code: null, semantic_mismatch: null });
const analysis = (overrides = {}) => ({
  trip: trip(), status: 'available', findings: [roadFinding('ra-1', 'direct_overlap', 25), ...Array.from({ length: 12 }, (_, i) => roadFinding(`ra-${i + 2}`, 'nearby', i + 50))],
  drivebc_findings: [{ ...roadFinding('bc-1', 'nearby', 80), event: { ...roadFinding('bc-1', 'nearby', 80).event, source: 'DriveBC Open511', source_dataset_id: 'drivebc-open511-active', source_record_id: 'bc-source-1' }, geometry_basis: 'point_proximity', source_evidence: { direction_assessment: 'undetermined', temporal_applicability: 'unknown', current_impact: 'not_established' } }], regional_events: [], unmatchable_events: [],
  source_statuses: [sourceStatus('City of Vancouver Road Ahead', 'road-ahead-work'), sourceStatus('DriveBC Open511', 'drivebc-open511-active')],
  destination_weather: {
    openweather_current: { status: weatherStatus('onecall4_current'), weather: { source: 'OpenWeather', product: 'onecall4_current', observed_at: '2026-10-11T12:00:00Z', fetched_at: '2026-10-11T12:03:00Z', temperature_c: 8, feels_like_c: null, condition: { code: 804, group: 'Clouds', description: 'overcast' }, humidity_pct: null, wind_speed_m_s: 2, wind_direction_deg: null, wind_gust_m_s: null, visibility_m: null, rain_1h_mm: null, snow_1h_mm: null } },
    openweather_forecast: { status: weatherStatus('onecall4_timeline_15min'), intervals: [0, 1, 2, 3, 4].map((n) => ({ source: 'OpenWeather', product: 'onecall4_timeline_15min', forecast_at: new Date(Date.parse('2026-10-11T12:15:00Z') + n * 15 * 60_000).toISOString(), fetched_at: '2026-10-11T12:03:00Z', precipitation_probability_pct: null, temperature_c: null, feels_like_c: null, condition: null, humidity_pct: null, wind_speed_m_s: null, visibility_m: null })), coverage: { continuous: false, expected_interval_count: 12, returned_interval_count: 5, first_interval_at: '2026-10-11T12:15:00Z', last_interval_at: '2026-10-11T13:15:00Z' } },
    eccc_status: { ...weatherStatus('swob-realtime'), source: 'ECCC GeoMet/SWOB' }, eccc_attribution: 'ECCC GeoMet/SWOB', eccc_observations: Array.from({ length: 4 }, (_, n) => ({ observation: { source: 'ECCC GeoMet/SWOB', station_id: `station-${n}`, station_name: 'Harbour', latitude: 49.29, longitude: -123.12, observed_at: '2026-10-11T11:45:00Z', retrieved_at: '2026-10-11T12:03:00Z', temperature: { value: 8, unit: '°C', source_field: 'air_temp', interval_seconds: null, quality_code: null }, relative_humidity: null, precipitation: [], wind_speed: null, wind_direction: null, snow_depth: null, attribution: 'ECCC GeoMet/SWOB' }, distance_meters: 1200 + n, observation_age_seconds: 1080, observation_stale: false, cache_stale: false, useful_measurements: ['temperature'], selection_reason: 'nearest' })),
  }, analyzed_at: '2026-10-11T12:03:00Z', summary: 'summary', ...overrides,
});
const makeBundle = (options = {}) => evidence.assembleJourneyEvidence({ trip: options.trip ?? trip(), attempt_id: attemptId, lifecycle_id: 44, assembled_at: '2026-10-11T12:04:00Z', analysis: { status: 'success', result: options.analysis ?? analysis(), error: null }, camera_vision: options.camera === undefined ? { lifecycle_id: 44, trip: trip(), camera_vision: { status: 'complete', result: cameraResult() } } : options.camera });

test('serializes a realistic Phase 9 bundle into the full backend request DTO', () => {
  const payload = briefing.serializeBriefingEvidence(makeBundle());
  assert.deepEqual(Object.keys(payload.sources), ['road_ahead', 'drivebc_open511', 'openweather_current', 'openweather_forecast', 'eccc_swob', 'camera_vision']);
  assert.equal(payload.request_schema_version, 'journey-briefing-request-v1');
  assert.equal(payload.analysis_status, 'success');
  assert.equal(payload.attempt_id, attemptId);
  assert.deepEqual(payload.journey.route, { candidate_id: 'route-1', label: 'Route 1', distance_meters: 12000 });
  assert.equal(payload.sources.road_ahead.findings[0].source_id, 'ra-1');
  assert.equal(payload.sources.road_ahead.findings[0].event_type, 'construction');
  assert.equal(payload.sources.drivebc_open511.findings[0].geometry_basis, 'point_proximity');
  assert.equal(payload.sources.openweather_current.observation.temperature_c.value, 8);
  assert.equal(payload.sources.openweather_current.observation.feels_like_c, null);
  assert.equal(payload.sources.openweather_forecast.intervals.length, 4);
  assert.equal(payload.sources.openweather_forecast.omitted_count, 1);
  assert.equal(payload.sources.eccc_swob.observations.length, 3);
  assert.equal(payload.sources.eccc_swob.omitted_count, 1);
  assert.equal(payload.sources.camera_vision.observation.direction_view.view_id, 'view-north');
  assert.equal(payload.sources.camera_vision.observation.direction_view.source_capture_at, '2026-10-11T12:01:00Z');
  assert.equal(payload.sources.road_ahead.findings.length, 12);
  assert.equal(payload.sources.road_ahead.omitted_count, 1);
  const encoded = JSON.stringify(payload);
  for (const forbidden of ['coordinates', 'trafficcams.vancouver.ca', 'snapshot_identity', 'data:image', 'private-cache-key', 'hidden-provider', 'source_metadata', '"geometry":']) assert.equal(encoded.includes(forbidden), false, forbidden);
  const validation = spawnSync('.venv/bin/python', ['-c', 'import sys,base64; from app.briefing_contracts import BriefingEvidenceRequestV1; BriefingEvidenceRequestV1.model_validate_json(base64.b64decode(sys.argv[1]))', Buffer.from(encoded).toString('base64')], { cwd: new URL('../../backend', import.meta.url), encoding: 'utf8' });
  assert.equal(validation.status, 0, validation.stderr || validation.stdout);
});

test('keeps failed source status and nullable OpenWeather and SWOB values without zeros', () => {
  const broken = analysis({ source_statuses: [sourceStatus('City of Vancouver Road Ahead', 'road-ahead-work', { success: false, available: false, error: 'timeout' }), sourceStatus('DriveBC Open511', 'drivebc-open511-active')] });
  const payload = briefing.serializeBriefingEvidence(makeBundle({ analysis: broken }));
  assert.equal(payload.sources.road_ahead.availability, 'failed');
  assert.equal(payload.sources.road_ahead.statuses[0].success, false);
  assert.equal(payload.sources.openweather_current.observation.feels_like_c, null);
  assert.equal(payload.sources.openweather_current.observation.wind_direction_deg, null);
  assert.equal(payload.sources.eccc_swob.observations[0].measurements.length, 1);
  assert.equal(payload.sources.eccc_swob.observations[0].measurements[0].value, 8);
});

test('camera emits only the matching selected direction and keeps unusable statuses explicit', () => {
  const payload = briefing.serializeBriefingEvidence(makeBundle());
  assert.equal(payload.sources.camera_vision.observation.direction_view.view_id, 'view-north');
  for (const [visionStatus, expected] of [['insufficient_evidence', 'insufficient_evidence'], ['unavailable', 'unavailable'], ['error', 'error']]) {
    const failed = briefing.serializeBriefingEvidence(makeBundle({ camera: { lifecycle_id: 44, trip: trip(), camera_vision: { status: 'complete', result: cameraResult(visionStatus) } } }));
    assert.equal(failed.sources.camera_vision.observation_status, expected);
    assert.equal(failed.sources.camera_vision.observation.direction_view, null);
    assert.equal(failed.sources.camera_vision.observation.summary, null);
  }
  assert.throws(() => briefing.serializeBriefingEvidence(makeBundle({ trip: { ...trip(), selected_route: { ...trip().selected_route, candidate_id: 'different-route' } } })), /Journey analysis trip does not match/);
});

test('rejects ineligible and identity-mismatched evidence', () => {
  const bundle = makeBundle();
  assert.throws(() => briefing.serializeBriefingEvidence({ ...bundle, readiness: { status: 'unknown', ready_for_briefing: false } }), /not eligible/);
  assert.throws(() => makeBundle({ camera: { lifecycle_id: 43, trip: trip(), camera_vision: { status: 'complete', result: cameraResult() } } }), /does not match/);
});

test('enforces backend text bounds, deterministic relevance ordering and the 32 KiB ceiling', () => {
  const bundle = makeBundle();
  const bounded = structuredClone(bundle);
  bounded.sources.road_ahead.findings[0].event.title = 't'.repeat(220);
  bounded.sources.road_ahead.findings[0].event.description = 'd'.repeat(400);
  const payload = briefing.serializeBriefingEvidence(bounded);
  assert.equal(payload.sources.road_ahead.findings[0].title.length, 160);
  assert.equal(payload.sources.road_ahead.findings[0].description.length, 320);
  assert.equal(payload.sources.road_ahead.findings[0].classification, 'direct_overlap');
  const fill = (index, source = 'road') => ({ ...roadFinding(`${source}-${index}`, 'nearby', index + 1), event: { ...roadFinding(`${source}-${index}`, 'nearby', index + 1).event,
    title: 't'.repeat(160), description: 'd'.repeat(320), severity: 's'.repeat(80), status: 'x'.repeat(80), schedule_text: 'q'.repeat(320), restriction_text: 'r'.repeat(320) },
    detail: { ...roadFinding(`${source}-${index}`, 'nearby', index + 1).detail, location: 'l'.repeat(160) } });
  const oversizedAnalysis = analysis({ findings: Array.from({ length: 12 }, (_, i) => fill(i)), drivebc_findings: Array.from({ length: 12 }, (_, i) => ({ ...fill(i, 'drivebc'), geometry_basis: 'linestring_proximity', source_evidence: { direction_assessment: 'd'.repeat(80), temporal_applicability: 't'.repeat(80), current_impact: 'i'.repeat(80) } })) });
  assert.throws(() => briefing.serializeBriefingEvidence(makeBundle({ analysis: oversizedAnalysis })), /32 KiB/);
});

test('initializing at camera start includes a t=5 result at t=20; initializing at t=20 excludes it', async () => {
  let now = 0;
  let finishCamera;
  let cutoffCallback;
  const clearedTimers = [];
  const cameraPending = new Promise((resolve) => { finishCamera = resolve; });
  const opportunity = briefing.createCameraOpportunity(cameraPending, 0, 15_000, () => now,
    (callback, delay) => { assert.equal(delay, 15_000); cutoffCallback = callback; return 1; },
    (timer) => clearedTimers.push(timer));

  now = 5_000;
  finishCamera(cameraResult());
  await Promise.resolve();
  assert.deepEqual(opportunity.settlement(), { status: 'settled_within_opportunity', settled_at: 5_000, value: cameraResult() });

  now = 20_000; // Analysis finishes after the absolute camera cutoff.
  const eligibleCamera = await opportunity.promise;
  const frozen = makeBundle({ camera: { lifecycle_id: 44, trip: trip(), camera_vision: { status: 'complete', result: eligibleCamera } } });
  assert.equal(frozen.sources.camera_vision.availability, 'available');
  assert.equal(cutoffCallback instanceof Function, true);
  assert.deepEqual(clearedTimers, [1], 'normal camera settlement clears the pending opportunity timer');

  const delayedInitialization = briefing.createCameraOpportunity(cameraPending, 0, 15_000, () => now,
    (_callback, delay) => { assert.equal(delay, 0); return 2; }, (timer) => clearedTimers.push(timer));
  assert.equal(await delayedInitialization.promise, null);
  assert.equal(delayedInitialization.settlement().status, 'settled_after_cutoff');
  const delayedSnapshot = makeBundle({ camera: { lifecycle_id: 44, trip: trip(), camera_vision: { status: 'pending' } } });
  assert.equal(delayedSnapshot.sources.camera_vision.availability, 'pending');
  assert.deepEqual(clearedTimers, [1, 2]);
});

test('camera still pending at cutoff freezes pending and later completion cannot change the snapshot', async () => {
  let now = 0;
  let finishCamera;
  let cutoffCallback;
  const cameraPending = new Promise((resolve) => { finishCamera = resolve; });
  const opportunity = briefing.createCameraOpportunity(cameraPending, 0, 15_000, () => now,
    (callback) => { cutoffCallback = callback; return 1; }, () => undefined);

  now = 15_000;
  cutoffCallback();
  cutoffCallback(); // Flush the deferred exact-boundary decision with no camera result.
  await Promise.resolve();
  assert.equal(await opportunity.promise, null);
  assert.deepEqual(opportunity.settlement(), { status: 'pending_at_cutoff' });

  const frozenRequest = briefing.serializeBriefingEvidence(makeBundle({ camera: {
    lifecycle_id: 44, trip: trip(), camera_vision: { status: 'pending' },
  } }));
  assert.equal(frozenRequest.sources.camera_vision.availability, 'pending');
  now = 15_001;
  finishCamera(cameraResult());
  await Promise.resolve();
  assert.equal(opportunity.settlement().status, 'settled_after_cutoff');
  assert.equal(frozenRequest.sources.camera_vision.availability, 'pending');
});

test('camera completion immediately before and exactly at the cutoff is included', async () => {
  for (const settledAt of [14_999, 15_000]) {
    let now = 0;
    let finishCamera;
    let cutoffCallback;
    const cameraPending = new Promise((resolve) => { finishCamera = resolve; });
    const opportunity = briefing.createCameraOpportunity(cameraPending, 0, 15_000, () => now,
      (callback) => { cutoffCallback = callback; return 1; }, () => undefined);
    now = settledAt;
    finishCamera(cameraResult());
    await Promise.resolve(); // Apply the inclusive <= cutoff rule before the timer callback.
    assert.equal((await opportunity.promise)?.observation.status, 'available');
    assert.equal(opportunity.settlement().status, 'settled_within_opportunity');
    cutoffCallback(); // A queued/late timer cannot override an observed timely settlement.
    assert.equal(opportunity.settlement().settled_at, settledAt);
  }

  let now = 15_000;
  let finishAtBoundary;
  let nextDeadlineTask;
  const boundaryPromise = new Promise((resolve) => { finishAtBoundary = resolve; });
  const boundaryOpportunity = briefing.createCameraOpportunity(boundaryPromise, 0, 15_000, () => now,
    (callback) => { nextDeadlineTask = callback; return 1; }, () => undefined);
  nextDeadlineTask(); // Deadline timer runs first at exactly t=15; it defers its decision one task.
  finishAtBoundary(cameraResult());
  await Promise.resolve();
  nextDeadlineTask();
  assert.equal((await boundaryOpportunity.promise)?.observation.status, 'available');
  assert.equal(boundaryOpportunity.settlement().status, 'settled_within_opportunity');
});

test('camera completion after cutoff is excluded even when analysis completes later', async () => {
  let now = 0;
  let finishCamera;
  let cutoffCallback;
  const cameraPending = new Promise((resolve) => { finishCamera = resolve; });
  const opportunity = briefing.createCameraOpportunity(cameraPending, 0, 15_000, () => now,
    (callback) => { cutoffCallback = callback; return 1; }, () => undefined);
  now = 15_000;
  cutoffCallback();
  cutoffCallback(); // Flush the deferred cutoff decision.
  await Promise.resolve();
  now = 15_001;
  finishCamera(cameraResult());
  await Promise.resolve();
  now = 20_000;
  assert.equal(await opportunity.promise, null);
  assert.equal(opportunity.settlement().status, 'settled_after_cutoff');
});

test('camera failure within the opportunity is frozen as bounded failure evidence', async () => {
  const failure = vision.unavailableCameraVision('provider_unavailable');
  const opportunity = briefing.createCameraOpportunity(Promise.resolve(failure), 100, 15_000, () => 200,
    () => 1, () => undefined);
  const received = await opportunity.promise;
  const payload = briefing.serializeBriefingEvidence(makeBundle({ camera: {
    lifecycle_id: 44, trip: trip(), camera_vision: { status: 'complete', result: received },
  } }));
  assert.equal(payload.sources.camera_vision.observation_status, 'unavailable');
  assert.equal(payload.sources.camera_vision.observation.direction_view, null);
});

test('analysis completing early waits only to the request-start cutoff, not a fresh 15 seconds', async () => {
  let now = 0;
  let finishCamera;
  let cutoffCallback;
  let scheduledDelay;
  const cameraPending = new Promise((resolve) => { finishCamera = resolve; });
  const opportunity = briefing.createCameraOpportunity(cameraPending, 0, 15_000, () => now,
    (callback, delay) => { cutoffCallback = callback; scheduledDelay = delay; return 1; }, () => undefined);
  now = 4_000; // Main analysis has completed; the opportunity timer was already running.
  const waitingForEvidence = opportunity.promise;
  assert.equal(scheduledDelay, 15_000);
  now = 14_999;
  finishCamera(cameraResult());
  assert.equal((await waitingForEvidence)?.observation.status, 'available');
  assert.equal(opportunity.settlement().settled_at, 14_999);
  cutoffCallback();
  assert.equal(opportunity.settlement().status, 'settled_within_opportunity');
});

test('a superseded attempt cannot retain its late camera result', async () => {
  let now = 0;
  let finishOldCamera;
  let cutoffCallback;
  const oldCamera = new Promise((resolve) => { finishOldCamera = resolve; });
  const oldOpportunity = briefing.createCameraOpportunity(oldCamera, 0, 15_000, () => now,
    (callback) => { cutoffCallback = callback; return 1; }, () => undefined);
  const current = { lifecycle_id: 45, trip: trip(), camera_vision: { status: 'pending' } };
  now = 15_000;
  cutoffCallback();
  cutoffCallback();
  await Promise.resolve();
  assert.equal(await oldOpportunity.promise, null);
  now = 16_000;
  finishOldCamera(cameraResult());
  await Promise.resolve();
  const oldResult = oldOpportunity.settlement().value;
  assert.equal(vision.retainCurrentCameraVision(current, 44, oldResult), current);
});

test('late camera completion does not trigger a second briefing request', async () => {
  let now = 0;
  let finishCamera;
  let cutoffCallback;
  const cameraPending = new Promise((resolve) => { finishCamera = resolve; });
  const opportunity = briefing.createCameraOpportunity(cameraPending, 0, 15_000, () => now,
    (callback) => { cutoffCallback = callback; return 1; }, () => undefined);
  now = 15_000;
  cutoffCallback();
  cutoffCallback();
  await Promise.resolve();
  const cameraAtFreeze = await opportunity.promise;
  const frozenRequest = briefing.serializeBriefingEvidence(makeBundle({ camera: cameraAtFreeze ? {
    lifecycle_id: 44, trip: trip(), camera_vision: { status: 'complete', result: cameraAtFreeze },
  } : { lifecycle_id: 44, trip: trip(), camera_vision: { status: 'pending' } } }));

  const reply = { contract_version: 'journey-briefing-v1', prompt_version: 'journey-briefing-prompt-v1', status: 'unavailable', failure_code: 'budget_exhausted', generated_at: '2026-10-11T12:05:00Z', attempt_id: attemptId, origin_name: 'Richmond', destination_name: 'Vancouver', requested_model: 'google/gemma-4-31b-it', returned_model: null, provider: null, overview: '', overview_evidence_refs: [], highlights: [], limitations: [], usage: { input_tokens: null, output_tokens: null, total_tokens: null, cost_usd: null, latency_ms: 0 } };
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return { ok: true, json: async () => reply }; };
  try {
    await briefing.startBriefingRequest(frozenRequest).promise;
    now = 15_001;
    finishCamera(vision.unavailableCameraVision('timeout'));
    await Promise.resolve();
    assert.equal(calls, 1);
    assert.equal(frozenRequest.sources.camera_vision.availability, 'pending');
    assert.equal(opportunity.settlement().status, 'settled_after_cutoff');
    assert.equal(opportunity.settlement().value.observation.failure_code, 'timeout');
  } finally { globalThis.fetch = originalFetch; }
});

test('camera opportunity supports cancellation and no-camera paths', async () => {
  const absent = briefing.createCameraOpportunity(null, 0);
  assert.equal(await absent.promise, null);
  assert.equal(absent.settlement().status, 'not_started');
  let cancelDeadline;
  const clearedTimers = [];
  const cancelled = briefing.createCameraOpportunity(new Promise(() => undefined), 0, 15_000, () => 1,
    (callback) => { cancelDeadline = callback; return 17; }, (timer) => clearedTimers.push(timer));
  cancelled.cancel();
  assert.equal(await cancelled.promise, null);
  assert.equal(cancelled.settlement().status, 'cancelled');
  assert.deepEqual(clearedTimers, [17], 'cancellation clears the pending opportunity timer');
  assert.equal(typeof cancelDeadline, 'function');

});

test('briefing transport posts once, validates response identity, and deadline cancellation is isolated', async () => {
  const request = briefing.serializeBriefingEvidence(makeBundle());
  const reply = { contract_version: 'journey-briefing-v1', prompt_version: 'journey-briefing-prompt-v1', status: 'unavailable', failure_code: 'budget_exhausted', generated_at: '2026-10-11T12:05:00Z', attempt_id: attemptId, origin_name: 'Richmond', destination_name: 'Vancouver', requested_model: 'google/gemma-4-31b-it', returned_model: null, provider: null, overview: '', overview_evidence_refs: [], highlights: [], limitations: [], usage: { input_tokens: null, output_tokens: null, total_tokens: null, cost_usd: null, latency_ms: 0 } };
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (url, init) => { calls += 1; assert.equal(url, '/api/briefings/generate'); assert.equal(init.method, 'POST'); assert.equal(JSON.parse(init.body).attempt_id, attemptId); return { ok: true, json: async () => reply }; };
  try {
    const controller = new AbortController();
    const result = await briefing.fetchBriefingEvidence(request, controller.signal);
    assert.equal(result.failure_code, 'budget_exhausted');
    assert.equal(calls, 1);
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ ...reply, attempt_id: secondAttemptId }) });
    await assert.rejects(briefing.fetchBriefingEvidence(request, new AbortController().signal), /invalid_response/);
  } finally { globalThis.fetch = original; }
  const controller = new AbortController();
  const originalAgain = globalThis.fetch;
  globalThis.fetch = (_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true }));
  try {
    const timed = briefing.startBriefingRequest(request, controller.signal, 5);
    await assert.rejects(timed.promise);
    assert.equal(timed.wasTimedOut(), true);
    assert.equal(controller.signal.aborted, false);
  } finally { globalThis.fetch = originalAgain; }
});

test('accepts briefing usage within the raised 1024-token output bound', () => {
  const result = briefing.normalizeBriefingResult({
    contract_version: 'journey-briefing-v1', prompt_version: 'journey-briefing-prompt-v1',
    status: 'available', failure_code: null, generated_at: '2026-10-11T12:05:00Z', attempt_id: attemptId,
    origin_name: 'Richmond', destination_name: 'Vancouver', requested_model: 'google/gemma-4-31b-it',
    returned_model: 'google/gemma-4-31b-it', provider: 'TestProvider', overview: 'Supported overview',
    overview_evidence_refs: ['ra-event-7'], highlights: [
      { category: 'camera', text: 'Camera interpretation was pending and was not included.', evidence_refs: [] },
      { category: 'weather', text: 'Destination weather data unavailable.', evidence_refs: [] },
      { category: 'road', text: 'Construction is reported nearby.', evidence_refs: ['ra-event-7'] },
    ], limitations: [],
    usage: { input_tokens: 120, output_tokens: 900, total_tokens: 1020, cost_usd: 0.001, latency_ms: 15000 },
  });

  assert.equal(result?.usage.output_tokens, 900);
  assert.equal(briefing.normalizeBriefingResult({ ...result, attempt_id: 44 }), null);
  assert.equal(briefing.normalizeBriefingResult({ ...result, attempt_id: '11111111-1111-1111-8111-111111111111' }), null);
});

test('accepts 300-character briefing highlights and rejects longer text', () => {
  const response = {
    contract_version: 'journey-briefing-v1', prompt_version: 'journey-briefing-prompt-v1',
    status: 'available', failure_code: null, generated_at: '2026-10-11T12:05:00Z', attempt_id: attemptId,
    origin_name: 'Richmond', destination_name: 'Vancouver', requested_model: 'google/gemma-4-31b-it',
    returned_model: 'google/gemma-4-31b-it', provider: 'TestProvider', overview: 'Supported overview',
    overview_evidence_refs: ['ra-event-7'],
    highlights: [
      { category: 'camera', text: 'x'.repeat(300), evidence_refs: ['camera-view-1'] },
      { category: 'weather', text: 'Destination weather data unavailable.', evidence_refs: [] },
      { category: 'road', text: 'No qualifying construction report is available in the current Road Ahead evidence.', evidence_refs: [] },
    ],
    limitations: [], usage: { input_tokens: 120, output_tokens: 900, total_tokens: 1020, cost_usd: 0.001, latency_ms: 15000 },
  };

  assert.equal(briefing.normalizeBriefingResult(response)?.highlights[0].text.length, 300);
  assert.equal(briefing.normalizeBriefingResult({ ...response, highlights: [{ ...response.highlights[0], text: 'x'.repeat(301) }, ...response.highlights.slice(1)] }), null);
  assert.equal(briefing.normalizeBriefingResult({ ...response, highlights: response.highlights.slice(0, 2) }), null);
  assert.equal(briefing.normalizeBriefingResult({ ...response, highlights: [...response.highlights, response.highlights[0]] }), null);
});

test('App owns one latched briefing request and invalidates/aborts its attempt with journey changes', () => {
  assert.equal((appSource.match(/startBriefingRequest\(/g) ?? []).length, 1);
  assert.match(appSource, /briefingAttempt\.current = attemptId;[\s\S]*?startBriefingRequest\(briefingRequest/);
  const analyzeJourney = appSource.slice(appSource.indexOf('async function analyzeJourney()'));
  const analysisResponse = analyzeJourney.indexOf("fetch('/api/trips/analyze'");
  const normalizedAnalysis = analyzeJourney.indexOf('normalizeJourneyAnalysis(await response.json())');
  const briefingDispatch = analyzeJourney.indexOf('startBriefingRequest(briefingRequest');
  const analysisFailureHandler = analyzeJourney.lastIndexOf('} catch (error) {');
  assert.ok(analysisResponse >= 0 && normalizedAnalysis > analysisResponse && briefingDispatch > normalizedAnalysis);
  assert.ok(analysisFailureHandler > briefingDispatch);
  assert.doesNotMatch(analyzeJourney.slice(analysisFailureHandler), /startBriefingRequest\(/);
  assert.match(appSource, /const frozenBundle = deriveCurrentJourneyEvidence\(\{[\s\S]*?camera_vision: matchingCamera/);
  const cameraRequestStart = analyzeJourney.indexOf('const cameraResultPromise = fetchCameraVision(');
  const opportunityStart = analyzeJourney.indexOf('const cameraOpportunity = createCameraOpportunity(cameraResultPromise, cameraInferenceStartedAt)');
  const analysisRequestStart = analyzeJourney.indexOf("fetch('/api/trips/analyze'");
  const analysisSuccess = analyzeJourney.indexOf("setAnalysisState({ status: 'success', result: analysis");
  const cameraResultConsumed = analyzeJourney.indexOf('const cameraResult = await cameraOpportunity.promise');
  assert.ok(cameraRequestStart >= 0, 'camera inference request starts');
  assert.ok(cameraRequestStart < opportunityStart, 'coordinator is created from the camera request');
  assert.ok(opportunityStart < analysisRequestStart, 'coordinator is initialized before journey analysis starts');
  assert.ok(analysisRequestStart < analysisSuccess && analysisSuccess < cameraResultConsumed,
    'the completed camera result is consumed after analysis succeeds');
  assert.match(appSource, /briefingController\.current\?\.abort\(\)/);
  assert.match(appSource, /setJourneyBriefingState\(\{ status: 'idle' \}\)/);
  assert.match(appSource, /briefingControllerValue\.signal\.aborted \|\| requestId !== analysisSequence\.current/);
});
