import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/cameraVision.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const vision = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`);
const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');

const trip = {
  origin: { name: 'Richmond', latitude: 49.16, longitude: -123.14 },
  destination: { name: 'Vancouver', latitude: 49.28, longitude: -123.12 }, mode: 'drive',
  selected_route: { candidate_id: 'selected-2', geometry: { type: 'LineString', coordinates: [[-123.14, 49.16], [-123.12, 49.28]] }, distance_meters: 9000, duration_seconds: 1000 },
};
const result = (overrides = {}) => ({
  observation: {
    schema_version: 'camera-observation-v1', prompt_version: 'camera-visual-observer-v2', status: 'partial', failure_code: null,
    intersection_id: 'cam-42', intersection_name: 'Main St & Broadway', street_names: ['Main St', 'Broadway'],
    distance_from_destination_metres: 210, official_camera_page_url: 'https://trafficcams.vancouver.ca/mainbroadway.htm',
    source_name: 'City of Vancouver Open Data Portal', attribution: 'Contains information licensed under the Open Government Licence – Vancouver.',
    included_views: [{ view_id: 'view-south', direction_label: 'South - Main St', retrieved_at: '2026-10-11T12:00:00Z', source_capture_at: null,
      sha256: 'a'.repeat(64), snapshot_identity: 'frame-snapshot-1', content_type: 'image/jpeg', width: 800, height: 464, byte_length: 24576 }],
    excluded_views: [], views: [{ view_id: 'view-south', road_surface: 'wet_looking', visibility: 'adequate', vehicle_activity: 'some_visible',
      conditions: [], uncertainty: 'moderate', note: 'Reflective pavement is visible.' }],
    intersection_summary: null, summary_evidence_view_ids: [], requested_model_id: 'google/gemma-4-31b-it',
    actual_provider_id: 'CoreWeave', actual_endpoint_id: null, inferred_at: '2026-10-11T12:00:03Z',
    usage: { input_tokens: 1200, output_tokens: 95, total_tokens: 1295, cost_usd: 0.0001, latency_ms: 3000 },
  }, cache_reused: false, provider_error: null, semantic_error_code: null, semantic_mismatch: null, ...overrides,
});

test('explicit Analyze Journey wiring calls vision once with the captured canonical Trip', async () => {
  assert.equal((appSource.match(/fetchCameraVision\(/g) ?? []).length, 1);
  assert.match(appSource, /const cameraResultPromise = fetchCameraVision\(request, visionRequestController\.signal\)/);
  assert.match(appSource, /onAnalyze=\{\(\) => void analyzeJourney\(\)\}/);
  assert.doesNotMatch(appSource.slice(appSource.indexOf('async function findRoutes()'), appSource.indexOf('function selectRoute')), /fetchCameraVision/);
  assert.match(appSource, /selectedCameraId=\{cameraState/); // markers remain display-only

  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (...args) => { calls.push(args); return { ok: true, json: async () => result() }; };
  try {
    const value = await vision.fetchCameraVision(trip, new AbortController().signal);
    assert.equal(calls.length, 1);
    assert.equal(calls[0][0], '/api/cameras/observe');
    assert.deepEqual(JSON.parse(calls[0][1].body), trip);
    assert.equal(value.observation.intersection_id, 'cam-42');
  } finally { globalThis.fetch = originalFetch; }
});

test('vision-specific deadline is 70 seconds and remains independent', () => {
  assert.equal(vision.CAMERA_VISION_TIMEOUT_MS, 70_000);
  assert.match(appSource, /startCameraVisionTimeout\(visionRequestController/);
  assert.match(appSource, /It never gates the road\/weather analysis or the Phase 7 gallery/);
  assert.match(appSource, /createCameraOpportunity\(cameraResultPromise, cameraInferenceStartedAt\)/);
});

test('page load and map or camera selection do not invoke the vision transport', () => {
  const triggerStart = appSource.indexOf('const cameraResultPromise = fetchCameraVision(');
  const analyzeStart = appSource.indexOf('async function analyzeJourney()');
  const analyzeEnd = appSource.indexOf('\n  useEffect(() => () => {', analyzeStart);
  assert.ok(triggerStart > analyzeStart && triggerStart < analyzeEnd);
  assert.match(appSource, /onSelectEvent=\{setSelectedEventId\}/);
  assert.match(appSource, /selectedCameraId=\{cameraState/);
});

test('retains validated visual observations separately from authoritative provenance', () => {
  const normalized = vision.normalizeCameraVisionResult(result());
  assert.equal(normalized.observation.included_views[0].direction_label, 'South - Main St');
  assert.equal(normalized.observation.included_views[0].source_capture_at, null);
  assert.equal(normalized.observation.included_views[0].retrieved_at, '2026-10-11T12:00:00Z');
  assert.equal(normalized.observation.views[0].road_surface, 'wet_looking');
  assert.equal(normalized.observation.actual_provider_id, 'CoreWeave');
  assert.equal(normalized.observation.usage.latency_ms, 3000);
  assert.equal(vision.normalizeCameraVisionResult({ ...result(), raw_response: 'secret' }).raw_response, undefined);
  assert.equal(vision.normalizeCameraVisionResult(result({ observation: { ...result().observation, views: [{ ...result().observation.views[0], note: 'data:image/jpeg;base64,AAAA' }] } })), null);
});

test('retains bounded integer-only identity mismatch diagnostics', () => {
  const mismatch = { expected_view_count: 4, actual_view_count: 3, first_mismatched_position: 3 };
  const accepted = vision.normalizeCameraVisionResult(result({ semantic_error_code: 'view_identity_or_order_mismatch', semantic_mismatch: mismatch }));
  assert.deepEqual(accepted.semantic_mismatch, mismatch);
  assert.equal(vision.normalizeCameraVisionResult(result({ semantic_mismatch: { ...mismatch, actual_view_count: 3.5 } })), null);
  assert.equal(vision.normalizeCameraVisionResult(result({ semantic_mismatch: { ...mismatch, view_id: 'model-id' } })).semantic_mismatch.view_id, undefined);
});

test('keeps source-declared unavailable outcomes bounded and never invents observations', async () => {
  const originalFetch = globalThis.fetch;
  for (const code of ['no_selected_intersection', 'no_eligible_frames', 'configuration_missing', 'budget_exhausted', 'timeout', 'invalid_model_output']) {
    globalThis.fetch = async () => ({ ok: true, json: async () => result({ observation: {
      ...result().observation, status: 'unavailable', failure_code: code, intersection_id: null,
      intersection_name: null, street_names: [], included_views: [], views: [],
    } }) });
    const received = await vision.fetchCameraVision(trip, new AbortController().signal);
    assert.equal(received.observation.failure_code, code);
    assert.deepEqual(received.observation.views, []);
  }
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ untrusted_provider_body: 'not accepted' }) });
  await assert.rejects(vision.fetchCameraVision(trip, new AbortController().signal), /result invalid/);
  globalThis.fetch = originalFetch;
});

test('attempt identity prevents superseded or changed-trip responses replacing current evidence', () => {
  const current = { lifecycle_id: 9, trip, camera_vision: { status: 'pending' } };
  const accepted = vision.normalizeCameraVisionResult(result());
  assert.equal(vision.isCurrentVisionAttempt(8, 9, 'trip-a', 'trip-a'), false);
  assert.equal(vision.isCurrentVisionAttempt(9, 9, 'trip-a', 'trip-b'), false);
  assert.equal(vision.isCurrentVisionAttempt(9, 9, 'trip-a', 'trip-a'), true);
  assert.equal(vision.retainCurrentCameraVision(current, 8, accepted), current);
  assert.equal(vision.retainCurrentCameraVision(current, 9, accepted).camera_vision.result.observation.intersection_id, 'cam-42');
  const newer = { ...current, lifecycle_id: 10, trip: { ...trip, destination: { ...trip.destination, latitude: 49.29 } } };
  assert.equal(vision.retainCurrentCameraVision(newer, 9, accepted), newer);
});

test('a 65-second successful response is retained and a superseded slow response cannot overwrite it', async () => {
  const originalFetch = globalThis.fetch;
  const pending = [];
  globalThis.fetch = () => new Promise((resolve) => pending.push(resolve));
  const resolveWith = (resolve, value) => resolve({ ok: true, json: async () => value });
  try {
    const oldRequest = vision.fetchCameraVision(trip, new AbortController().signal);
    const oldAttempt = 20;
    const activeTripKey = 'journey-new';
    let current = { lifecycle_id: 21, trip, camera_vision: { status: 'pending' } };
    const activeController = new AbortController();
    const newRequest = vision.fetchCameraVision(trip, activeController.signal);
    assert.equal(pending.length, 2);

    let scheduledDeadline;
    let deadlineCallback;
    let timeoutRecorded = false;
    let elapsedMs = 0;
    vision.startCameraVisionTimeout(activeController, () => { timeoutRecorded = true; }, (callback, delay) => {
      deadlineCallback = callback;
      scheduledDeadline = delay;
      return 1;
    });
    assert.equal(scheduledDeadline, 70_000);
    // Simulate 65 seconds passing: the vision-specific deadline has not expired.
    elapsedMs += 65_000;
    if (elapsedMs >= scheduledDeadline) deadlineCallback();
    assert.equal(timeoutRecorded, false);
    resolveWith(pending[1], result());
    const fresh = await newRequest;
    if (vision.isCurrentVisionAttempt(21, current.lifecycle_id, activeTripKey, activeTripKey)) {
      current = vision.retainCurrentCameraVision(current, 21, fresh);
    }
    assert.equal(current.camera_vision.result.observation.intersection_id, 'cam-42');
    assert.equal(timeoutRecorded, false);
    assert.equal(activeController.signal.aborted, false);
    assert.equal(typeof deadlineCallback, 'function');

    resolveWith(pending[0], result({ observation: { ...result().observation, intersection_id: 'stale-camera' } }));
    const stale = await oldRequest;
    if (vision.isCurrentVisionAttempt(oldAttempt, current.lifecycle_id, 'journey-old', activeTripKey)) {
      current = vision.retainCurrentCameraVision(current, oldAttempt, stale);
    }
    assert.equal(current.lifecycle_id, 21);
    assert.equal(current.camera_vision.result.observation.intersection_id, 'cam-42');
  } finally { globalThis.fetch = originalFetch; }
});

test('transport timeout and invalid responses settle to an internal bounded failure', () => {
  const timeout = vision.cameraVisionFailureResult(new Error('aborted'), true);
  const invalid = vision.cameraVisionFailureResult(new Error('Camera vision result invalid'), false);
  const unavailable = vision.cameraVisionFailureResult(new Error('Camera vision request unavailable'), false);
  assert.equal(timeout.observation.status, 'unavailable');
  assert.equal(timeout.observation.failure_code, 'timeout');
  assert.equal(invalid.observation.failure_code, 'invalid_model_output');
  assert.equal(unavailable.observation.failure_code, 'provider_unavailable');
  assert.equal(unavailable.observation.views.length, 0);
});
