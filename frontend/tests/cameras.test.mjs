import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/cameras.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const cameras = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`);

const destination = { name: 'Vancouver City Centre', latitude: 49.2827, longitude: -123.1207 };
const view = (index, direction = `Direction ${index}`, overrides = {}) => ({
  view_id: `view-${index}`, direction_label: direction,
  image_reference: `/api/cameras/images/${String(index).padStart(32, 'a')}`,
  retrieved_at: '2026-10-11T12:00:00Z', source_capture_at: null, cache_age_seconds: 180,
  stale: false, width: 800, height: 464, content_type: 'image/jpeg', ...overrides,
});
const result = (overrides = {}) => ({
  destination, status: 'available',
  intersection: {
    intersection_id: 'intersection-1', name: 'Hornby St and Robson St', latitude: 49.2819,
    longitude: -123.1211, distance_metres: 79.6, distance_is_approximate: true,
    official_page_url: 'https://trafficcams.vancouver.ca/hornbyrobson.htm',
    source: 'City of Vancouver Traffic Cameras', attribution: 'Source: City of Vancouver Traffic Cameras',
  },
  views: [view(1, 'South - Main St')], stale_views: [],
  diagnostics: { candidates_attempted: 1, views_attempted: 4, views_succeeded: 1, views_failed: 3,
    fallback_used: false, catalogue_stale: false, failures: [] },
  ...overrides,
});
const marker = (id, overrides = {}) => ({ intersection_id: id, name: `Street ${id} and Avenue`, latitude: 49.2827,
  longitude: -123.1207, distance_metres: 100, official_page_url: `https://trafficcams.vancouver.ca/${id}.htm`,
  source: 'City of Vancouver Open Data Portal', attribution: 'Contains City open data.', ...overrides });

test('sends the canonical destination to the application camera API and normalizes the response', async () => {
  const originalFetch = globalThis.fetch;
  let request;
  globalThis.fetch = async (...args) => {
    request = args;
    return { ok: true, json: async () => result() };
  };
  try {
    const value = await cameras.fetchDestinationCamera(destination, new AbortController().signal);
    assert.equal(request[0], '/api/cameras/nearest');
    assert.equal(request[1].method, 'POST');
    assert.deepEqual(JSON.parse(request[1].body), { destination });
    assert.equal(value.intersection.name, 'Hornby St and Robson St');
    assert.equal(value.views[0].direction_label, 'South - Main St');
  } finally { globalThis.fetch = originalFetch; }
});

test('rejects image references that are not opaque backend tokens', () => {
  const invalid = result({ views: [view(1, 'North', { image_reference: 'https://trafficcams.vancouver.ca/frame.jpg' })] });
  assert.equal(cameras.normalizeDestinationCamera(invalid), null);
  assert.equal(cameras.normalizeDestinationCamera(result({ views: [view(1, 'North', { image_reference: '/api/cameras/images/../../secret' })] })), null);
});

test('rejects unexpected official source links and destination mismatches', async () => {
  assert.equal(cameras.normalizeDestinationCamera(result({
    intersection: { ...result().intersection, official_page_url: 'https://example.com/camera' },
  })), null);
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, json: async () => result({ destination: { ...destination, latitude: 49.3 } }) });
  try { await assert.rejects(cameras.fetchDestinationCamera(destination, new AbortController().signal)); }
  finally { globalThis.fetch = originalFetch; }
});

test('keeps camera HTTP failures isolated behind a camera-specific error', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, status: 503 });
  try { await assert.rejects(cameras.fetchDestinationCamera(destination, new AbortController().signal), /Camera service unavailable/); }
  finally { globalThis.fetch = originalFetch; }
});

test('guards destination changes, route changes, and repeated analysis request identities', () => {
  const a = JSON.stringify({ destination, route: 'a' });
  const b = JSON.stringify({ destination: { ...destination, latitude: 49.29 }, route: 'b' });
  assert.equal(cameras.isCurrentCameraRequest(a, a, 1, 1), true);
  assert.equal(cameras.isCurrentCameraRequest(a, b, 1, 2), false);
  assert.equal(cameras.isCurrentCameraRequest(a, a, 1, 2), false);
  assert.equal(cameras.isCurrentCameraRequest(a, null, 1, 1), false);
  assert.equal(cameras.isCurrentCameraImageEvent(`${a}:1`, `${a}:2`), false);
  assert.equal(cameras.isCurrentCameraImageEvent(`${a}:2`, `${a}:2`), true);
  assert.equal(cameras.isCurrentNearbyCameraRequest(a, a, 1, 1, 4, 4), true);
  assert.equal(cameras.isCurrentNearbyCameraRequest(a, a, 1, 1, 3, 4), false);
  assert.equal(cameras.isCurrentNearbyCameraRequest(a, b, 1, 2, 4, 4), false);
});

test('handles an image load error only for the active gallery request', () => {
  let unavailable = 0;
  cameras.handleCameraImageError('journey-a:old', 'journey-b:new', () => { unavailable += 1; });
  assert.equal(unavailable, 0);
  cameras.handleCameraImageError('journey-b:new', 'journey-b:new', () => { unavailable += 1; });
  assert.equal(unavailable, 1);
});

test('formats backend retrieval age without implying source capture time', () => {
  assert.equal(cameras.formatCameraAge(180), 'about 3 minutes ago');
  assert.equal(cameras.formatCameraAge(0), 'less than a minute ago');
  assert.equal(cameras.formatRetrievedAt('invalid'), 'time unavailable');
});

test('requests nearby metadata only from the explicit call with canonical destination and selected gallery identity', async () => {
  const originalFetch = globalThis.fetch;
  const records = [marker('camera-a')];
  let request;
  globalThis.fetch = async (...args) => {
    request = args;
    return { ok: true, json: async () => ({ destination, status: 'available', cameras: records }) };
  };
  try {
    const value = await cameras.fetchNearbyCameras(destination, 'camera-a', new AbortController().signal);
    assert.equal(request[0], '/api/cameras/nearby');
    assert.deepEqual(JSON.parse(request[1].body), { destination, selected_intersection_id: 'camera-a' });
    assert.equal(value.cameras[0].intersection_id, 'camera-a');
  } finally { globalThis.fetch = originalFetch; }
});

test('accepts fewer-than-four metadata records and typed unavailable state', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ destination, status: 'unavailable', cameras: [] }) });
  try { assert.deepEqual(await cameras.fetchNearbyCameras(destination, null, new AbortController().signal), { cameras: [] }); }
  finally { globalThis.fetch = originalFetch; }
});

test('rejects an invalid official link and responses above the marker cap', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ destination, status: 'available', cameras: [marker('bad', { official_page_url: 'https://example.com/camera' })] }) });
  try { await assert.rejects(cameras.fetchNearbyCameras(destination, null, new AbortController().signal)); }
  finally { globalThis.fetch = originalFetch; }
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ destination, status: 'available', cameras: Array.from({ length: 5 }, (_, index) => marker(`camera-${index}`)) }) });
  try { await assert.rejects(cameras.fetchNearbyCameras(destination, null, new AbortController().signal)); }
  finally { globalThis.fetch = originalFetch; }
});

test('camera marker clicks open only validated City pages directly and stop map propagation', () => {
  let prevented = false;
  let stopped = false;
  const opened = [];
  const event = {
    preventDefault() { prevented = true; },
    stopPropagation() { stopped = true; },
  };
  const url = 'https://trafficcams.vancouver.ca/hornbyrobson.htm';
  assert.equal(cameras.openOfficialCameraPage(event, url, (...args) => opened.push(args)), true);
  assert.equal(prevented, true);
  assert.equal(stopped, true);
  assert.deepEqual(opened, [[url, '_blank', 'noopener,noreferrer']]);
});

test('camera marker click rejects deceptive, credentialed, and non-HTTPS page URLs', () => {
  for (const url of [
    'https://trafficcams.vancouver.ca.example.com/camera.htm',
    'https://trafficcams.vancouver.ca@evil.example/camera.htm',
    'http://trafficcams.vancouver.ca/camera.htm',
    'https://user@trafficcams.vancouver.ca/camera.htm',
    'https://trafficcams.vancouver.ca:444/camera.htm',
  ]) {
    assert.equal(cameras.validatedOfficialCameraPageUrl(url), null, url);
  }
  let openCount = 0;
  cameras.openOfficialCameraPage({ preventDefault() {}, stopPropagation() {} }, 'javascript:alert(1)', () => { openCount += 1; });
  assert.equal(openCount, 0);
});

test('limits rendered metadata to four and marks the gallery intersection by stable ID', () => {
  const markers = Array.from({ length: 5 }, (_, index) => marker(`camera-${index}`));
  const rendered = cameras.cameraMarkersForMap(markers, 'camera-3');
  assert.equal(rendered.length, 4);
  assert.equal(rendered.filter((item) => item.selected).length, 1);
  assert.equal(rendered.find((item) => item.selected).camera.intersection_id, 'camera-3');
  assert.equal(cameras.shouldRequestSelectedCameraMarker('camera-4', rendered.map((item) => item.camera.intersection_id)), true);
  assert.equal(cameras.shouldRequestSelectedCameraMarker('camera-3', rendered.map((item) => item.camera.intersection_id)), false);
  assert.equal(cameras.shouldRequestSelectedCameraMarker(null, []), false);
});
