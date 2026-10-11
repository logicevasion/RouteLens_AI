import assert from 'node:assert/strict';
import { dirname, resolve } from 'node:path';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { createRequire, Module } from 'node:module';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const frontend = resolve(new URL('..', import.meta.url).pathname);
const require = createRequire(new URL('../package.json', import.meta.url));
function compileTypescript(module, filename) {
  const source = readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  module._compile(compiled, filename);
}
require.extensions['.ts'] = compileTypescript;
require.extensions['.tsx'] = compileTypescript;
const componentPath = resolve(frontend, 'src/DestinationCameraPanel.tsx');
const componentModule = new Module(componentPath);
componentModule.filename = componentPath;
componentModule.paths = Module._nodeModulePaths(dirname(componentPath));
compileTypescript(componentModule, componentPath);
const DestinationCameraPanel = componentModule.exports.default;

const view = (index, direction = `Direction ${index}`, stale = false) => ({
  view_id: `view-${index}`, direction_label: direction,
  image_reference: `/api/cameras/images/${String(index).padStart(32, 'a')}`,
  retrieved_at: '2026-10-11T12:00:00Z', source_capture_at: null, cache_age_seconds: 180,
  stale, width: 800, height: 464, content_type: 'image/jpeg',
});
const intersection = {
  intersection_id: 'intersection-1', name: 'Hornby St and Robson St', latitude: 49.2819, longitude: -123.1211,
  distance_metres: 79.6, distance_is_approximate: true,
  official_page_url: 'https://trafficcams.vancouver.ca/hornbyrobson.htm',
  source: 'City of Vancouver Open Data Portal', attribution: 'Contains information licensed under the Open Government Licence – Vancouver.',
};
const cameraResult = (overrides = {}) => ({
  destination: { name: 'Downtown Vancouver', latitude: 49.2827, longitude: -123.1207 },
  status: 'available', intersection, views: [view(1, 'South - Main St')], stale_views: [],
  diagnostics: { candidates_attempted: 1, views_attempted: 4, views_succeeded: 1, views_failed: 3,
    fallback_used: false, catalogue_stale: false, failures: [] }, ...overrides,
});
const render = (camera) => renderToStaticMarkup(require('react').createElement(DestinationCameraPanel, { camera }));

test('shows an explicit no-analysis placeholder before any camera request', () => {
  const html = render({ status: 'idle' });
  assert.match(html, /Destination Cameras/);
  assert.match(html, /load when you choose Analyze journey/);
  assert.doesNotMatch(html, /<img/);
});

test('shows camera-specific loading and error states', () => {
  assert.match(render({ status: 'loading', requestKey: 'journey-a' }), /Finding nearby camera views/);
  assert.match(render({ status: 'error', requestKey: 'journey-a' }), /Camera images are temporarily unavailable/);
});

test('renders a one-view nearby intersection with attribution, safe link, and retrieval wording', () => {
  const html = render({ status: 'success', requestKey: 'journey-a', result: cameraResult() });
  assert.match(html, /Hornby St and Robson St/);
  assert.match(html, /Approximately 80 m from destination/);
  assert.match(html, /may not show the destination itself/);
  assert.match(html, /Official City of Vancouver camera page/);
  assert.match(html, /Source: City of Vancouver Open Data Portal/);
  assert.match(html, /Open Government Licence/);
  assert.match(html, /South - Main St/);
  assert.match(html, /Camera image retrieved at/);
  assert.match(html, /Retrieved about 3 minutes ago/);
  assert.match(html, /Camera capture time unavailable/);
  assert.match(html, /loading="lazy"/);
  assert.doesNotMatch(html, /Live now|Real-time feed/);
});

test('supports five views and retains complete composite source labels', () => {
  const directions = ['North', 'East', 'South - Main St', 'South - Kingsway', 'West Exit'];
  const html = render({ status: 'success', requestKey: 'journey-a', result: cameraResult({
    views: directions.map((label, index) => view(index + 1, label)), diagnostics: { ...cameraResult().diagnostics, views_failed: 0 },
  }) });
  for (const label of directions) assert.match(html, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  assert.equal((html.match(/<img/g) ?? []).length, 5);
});

test('renders partial availability without replacing failed views', () => {
  const html = render({ status: 'success', requestKey: 'journey-a', result: cameraResult({
    diagnostics: { ...cameraResult().diagnostics, views_failed: 2 },
  }) });
  assert.match(html, /Some directions were unavailable or stale during the nearby camera search/);
  assert.equal((html.match(/<img/g) ?? []).length, 1);
});

test('labels stale-only frames as degraded and preserves retrieval time', () => {
  const staleView = view(1, 'West Approach', true);
  const html = render({ status: 'success', requestKey: 'journey-a', result: cameraResult({
    status: 'stale', views: [], stale_views: [staleView],
  }) });
  assert.match(html, /Only cached camera images are available/);
  assert.match(html, /Cached image — may be outdated/);
  assert.match(html, /Retrieved about 3 minutes ago/);
  assert.match(html, /West Approach/);
});

test('reports no usable camera without affecting the rest of the journey UI', () => {
  const html = render({ status: 'success', requestKey: 'journey-a', result: cameraResult({
    status: 'unavailable', intersection: null, views: [], stale_views: [],
  }) });
  assert.match(html, /No usable camera images were found/);
  assert.doesNotMatch(html, /<img/);
});
