import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/roadAheadMap.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const roadAheadMap = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`);

function mapWithPreviousRoadAheadHighlight() {
  const layers = new Set([
    'routelens-route-selected-casing',
    'routelens-route-selected',
    'routelens-drivebc-lines',
    'routelens-drivebc-selected-line',
    'routelens-road-ahead-fill',
    'routelens-road-ahead-line',
    'routelens-road-ahead-selected-fill',
    'routelens-road-ahead-selected-casing',
    'routelens-road-ahead-selected-line',
  ]);
  const sources = new Map(['routelens-routes', 'routelens-drivebc-regional', 'routelens-road-ahead'].map((id) => [id, {
    type: 'geojson', data: { type: 'FeatureCollection', features: [{ properties: { selected: true } }] },
    setData(data) { this.data = data; },
  }]));
  const operations = [];
  return {
    layers, sources, operations,
    getLayer: (id) => layers.has(id),
    removeLayer(id) { layers.delete(id); operations.push(`layer:${id}`); },
    getSource: (id) => sources.get(id),
    addSource(id, source) { sources.set(id, { type: source.type, data: source.data, setData(data) { this.data = data; } }); },
    removeSource(id) { sources.delete(id); operations.push(`source:${id}`); },
  };
}

test('selection then destination, route, and analysis transitions remove old highlight and preserve other map layers', () => {
  const map = mapWithPreviousRoadAheadHighlight();
  roadAheadMap.syncRoadAheadSource(map, { type: 'FeatureCollection', features: [{ properties: { selected: true } }] });
  assert.equal(map.sources.get('routelens-road-ahead').data.features[0].properties.selected, true, 'event selection creates highlight data');

  const empty = { type: 'FeatureCollection', features: [] };
  for (const transition of ['destination changed', 'routes regenerated', 'new route selected', 'analysis started']) {
    roadAheadMap.syncRoadAheadSource(map, empty);
    assert.equal(map.sources.has('routelens-road-ahead'), false, transition);
    assert.equal([...map.layers].some((id) => id.startsWith('routelens-road-ahead-')), false, transition);
    assert.equal(map.sources.has('routelens-routes'), true, transition);
    assert.equal(map.sources.has('routelens-drivebc-regional'), true, transition);
    assert.equal(map.layers.has('routelens-route-selected'), true, transition);
    assert.equal(map.layers.has('routelens-drivebc-lines'), true, transition);
  }

  roadAheadMap.syncRoadAheadSource(map, { type: 'FeatureCollection', features: [{ properties: { selected: false } }] });
  assert.equal(map.sources.get('routelens-road-ahead').data.features[0].properties.selected, false, 'new analysis starts unselected');
  assert.equal([...map.layers].some((id) => id.startsWith('routelens-road-ahead-')), false, 'old highlight layers do not survive reset');
  assert.equal(map.operations.filter((operation) => operation === 'source:routelens-road-ahead').length, 1);
});

test('Road Ahead teardown is idempotent for origin edits and later journey resets', () => {
  const map = mapWithPreviousRoadAheadHighlight();
  roadAheadMap.clearRoadAheadMapState(map);
  const firstTeardownCount = map.operations.length;
  roadAheadMap.clearRoadAheadMapState(map);
  assert.equal(map.operations.length, firstTeardownCount);
});
