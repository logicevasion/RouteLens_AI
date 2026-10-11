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
