import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const weatherSource = await readFile(new URL('../src/weather.ts', import.meta.url), 'utf8');
const weatherJavascript = ts.transpileModule(weatherSource, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const weatherUrl = `data:text/javascript;base64,${Buffer.from(weatherJavascript).toString('base64')}`;
const source = await readFile(new URL('../src/roadAhead.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText.replace("from './weather'", `from '${weatherUrl}'`);
const roadAhead = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`);
const driveSource = await readFile(new URL('../src/drivebc.ts', import.meta.url), 'utf8');
const driveJavascript = ts.transpileModule(driveSource, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const drivebc = await import(`data:text/javascript;base64,${Buffer.from(driveJavascript).toString('base64')}`);

const line = { type: 'LineString', coordinates: [[-123.12, 49.27], [-123.11, 49.28]] };
const polygon = { type: 'Polygon', coordinates: [[[-123.12, 49.27], [-123.11, 49.27], [-123.11, 49.28], [-123.12, 49.27]]] };
const event = (id, geometry) => ({
  id, source: 'City of Vancouver Road Ahead', source_dataset_id: 'road-ahead-current-road-closures',
  source_record_id: id, event_type: 'road_closure', title: id, description: null, geometry,
  latitude: null, longitude: null, severity: null, status: null, schedule_text: null,
  restriction_text: null, observed_at: null, updated_at: null, source_url: null,
  relevance_reason: null, source_metadata: {}, attribution: 'City of Vancouver',
});
const finding = (id, classification, geometry, detail = {}) => ({
  event: event(id, geometry), classification, distance_meters: classification === 'nearby' ? 140 : 0,
  detail: { event_id: id, source_url: null, availability: 'unavailable', title: null, location: null,
    description: null, status: null, schedule_text: null, restriction_text: null, exceptions: null,
    posted_text: null, updated_text: null, retrieved_at: null, from_cache: false, stale: false, error: null,
    ...detail },
});

test('builds request with the explicit candidate, original geometry, and route units', () => {
  const route = { id: 'candidate-2', geometry: line, distance_meters: 8123.5, duration_seconds: 990, label: 'Alternate' };
  const trip = roadAhead.buildAnalysisRequest({ name: 'Richmond', latitude: 49.16, longitude: -123.14 },
    { name: 'Downtown Vancouver', latitude: 49.28, longitude: -123.12 }, route);
  assert.deepEqual(trip.selected_route, {
    candidate_id: 'candidate-2', geometry: line, distance_meters: 8123.5, duration_seconds: 990, label: 'Alternate',
  });
  assert.equal(trip.mode, 'drive');
});

test('requires canonical journey inputs and a valid explicitly selected route', () => {
  const origin = { name: 'Richmond', latitude: 49.16, longitude: -123.14 };
  const destination = { name: 'Vancouver', latitude: 49.28, longitude: -123.12 };
  const route = { id: 'candidate-2', geometry: line, distance_meters: 8123, duration_seconds: 990 };
  assert.equal(roadAhead.isAnalysisReady(origin, destination, null), false);
  assert.equal(roadAhead.isAnalysisReady(origin, null, route), false);
  assert.equal(roadAhead.isAnalysisReady(origin, destination, route), true);
  assert.equal(roadAhead.isAnalysisReady(origin, destination, { ...route, geometry: { type: 'LineString', coordinates: [[-123, 49]] } }), false);
});

test('rejects a late analysis response after the active journey identity changes', () => {
  assert.equal(roadAhead.isCurrentAnalysisRequest(7, 8, 'old-journey', 'new-journey'), false);
  assert.equal(roadAhead.isCurrentAnalysisRequest(8, 8, 'old-journey', 'new-journey'), false);
  assert.equal(roadAhead.isCurrentAnalysisRequest(8, 8, 'current-journey', 'current-journey'), true);
});

test('preserves supported event geometry, including mixed collections, under one event identity', () => {
  const multi = { type: 'MultiLineString', coordinates: [line.coordinates, [[-123.1, 49.28], [-123.09, 49.29]]] };
  const collection = { type: 'GeometryCollection', geometries: [line, polygon, multi] };
  const findings = [finding('line', 'direct_overlap', line), finding('multi', 'nearby', multi),
    finding('polygon', 'direct_overlap', polygon), finding('mixed', 'nearby', collection),
    finding('broken', 'nearby', { type: 'Point', coordinates: [-123.12, 49.27] }),
    finding('mixed-partial', 'nearby', { type: 'GeometryCollection', geometries: [line, { type: 'Polygon', coordinates: [] }] })];
  const geojson = roadAhead.roadAheadGeoJson(findings, 'road-ahead-current-road-closures:mixed');
  assert.equal(geojson.features.length, 6);
  assert.equal(geojson.features.find((item) => item.id.endsWith(':polygon')).geometry.type, 'Polygon');
  assert.equal(geojson.features.find((item) => item.id.endsWith(':mixed')).geometry.geometries.length, 3);
  assert.equal(geojson.features.find((item) => item.id.endsWith(':mixed')).properties.selected, true);
  assert.equal(geojson.features.find((item) => item.id.endsWith(':mixed-partial')).geometry.geometries.length, 1);
  assert.equal(geojson.features.filter((item) => item.id.endsWith(':mixed')).length, 1);
});

test('selects only the matching Road Ahead event for the dedicated map highlight and clears it', () => {
  const findings = [finding('direct', 'direct_overlap', line), finding('mixed', 'nearby', { type: 'GeometryCollection', geometries: [line, polygon] })];
  const selected = roadAhead.roadAheadGeoJson(findings, 'road-ahead-current-road-closures:mixed');
  assert.equal(selected.features.length, 2);
  assert.equal(selected.features.find((feature) => feature.id.endsWith(':mixed')).properties.selected, true);
  assert.equal(selected.features.find((feature) => feature.id.endsWith(':mixed')).geometry.geometries.length, 2);
  assert.equal(selected.features.find((feature) => feature.id.endsWith(':direct')).properties.selected, false);

  const cleared = roadAhead.roadAheadGeoJson(findings, null);
  assert.equal(cleared.features.every((feature) => feature.properties.selected === false), true);
});

test('computes map bounds across polygon and collection coordinates and ignores unusable geometry', () => {
  assert.deepEqual(roadAhead.eventBounds({ type: 'GeometryCollection', geometries: [line, polygon] }),
    [[-123.12, 49.27], [-123.11, 49.28]]);
  assert.deepEqual(roadAhead.eventBounds({ type: 'Point', coordinates: [-123, 49] }), [[-123, 49], [-123, 49]]);
});

test('normalizes API findings while preserving absent evidence and detail fallback', () => {
  const normalized = roadAhead.normalizeJourneyAnalysis({
    trip: { origin: {}, destination: {}, mode: 'drive', selected_route: { candidate_id: 'candidate-2', geometry: line, distance_meters: 1, duration_seconds: 1 } },
    status: 'partial', summary: 'Partial coverage.', analyzed_at: '2026-10-10T10:00:00Z', unmatchable_events: [],
    source_statuses: [{ source: 'City of Vancouver Road Ahead', dataset_id: 'road-ahead-current-road-closures', success: true,
      available: true, fetched_at: null, cache_hit: true, refreshed: false, stale: true, cache_age_seconds: 90000,
      error: null, records_received: 1, records_normalized: 1, records_skipped: 0 }],
    findings: [{ event: event('closure-1', line), classification: 'direct_overlap', distance_meters: 0,
      detail: { event_id: 'closure-1', source_url: null, availability: 'unavailable', title: null, location: null,
        description: null, status: null, schedule_text: null, restriction_text: null, exceptions: null, posted_text: null,
        updated_text: null, retrieved_at: null, from_cache: false, stale: false, error: 'timeout' } }],
  });
  assert.equal(normalized.status, 'partial');
  assert.equal(normalized.findings[0].event.status, null);
  assert.equal(normalized.findings[0].detail.availability, 'unavailable');
  assert.equal(normalized.source_statuses[0].stale, true);
  assert.deepEqual(normalized.drivebc_findings, []);
  assert.deepEqual(normalized.regional_events, []);
  assert.equal(roadAhead.normalizeJourneyAnalysis({ status: 'available' }), null);
});

test('normalizes DriveBC evidence and regional Point/LineString snapshots independently', () => {
  const regional = (id, geometry, extra = {}) => ({ ...event(id, geometry), source: 'DriveBC Open511', source_dataset_id: 'drivebc-open511-active', source_record_id: id, event_type: 'NEW_UNKNOWN_TYPE', severity: 'UNRECOGNIZED', attribution: 'DriveBC Open511', ...extra });
  const payload = {
    trip: { origin: {}, destination: {}, mode: 'drive', selected_route: { candidate_id: 'candidate-2', geometry: line, distance_meters: 1, duration_seconds: 1 } },
    status: 'available', summary: 'Road Ahead and DriveBC checked.', analyzed_at: '2026-10-10T10:00:00Z', findings: [], unmatchable_events: [],
    source_statuses: [{ source: 'DriveBC Open511', dataset_id: 'drivebc-open511-active', available: true, stale: true, success: false, fetched_at: null, cache_hit: true, refreshed: false, cache_age_seconds: 300, error: null, records_received: 3, records_normalized: 2, records_skipped: 1 }],
    drivebc_findings: [
      { event: regional('point', { type: 'Point', coordinates: [-123.12, 49.27] }), classification: 'nearby', distance_meters: 0, geometry_basis: 'point_proximity', source_evidence: { event_type: 'NEW_UNKNOWN_TYPE', severity: 'UNRECOGNIZED', status: 'ACTIVE', roads: [{ name: 'Marine Drive', direction: 'N' }], direction_assessment: 'undetermined', temporal_applicability: 'unknown', current_impact: 'not_established' } },
      { event: regional('bad', { type: 'Polygon', coordinates: [] }), classification: 'nearby', distance_meters: 1, geometry_basis: 'point_proximity' },
    ],
    regional_events: [regional('point', { type: 'Point', coordinates: [-123.12, 49.27] }), regional('line', line), regional('bad', { type: 'Point', coordinates: [NaN, 49] }), regional('unsupported', { type: 'Polygon', coordinates: [] })],
  };
  const normalized = roadAhead.normalizeJourneyAnalysis(payload);
  assert.equal(normalized.drivebc_findings.length, 1);
  assert.equal(normalized.drivebc_findings[0].geometry_basis, 'point_proximity');
  assert.equal(normalized.drivebc_findings[0].source_evidence.direction_assessment, 'undetermined');
  assert.equal(normalized.drivebc_findings[0].source_evidence.current_impact, 'not_established');
  assert.equal(normalized.drivebc_findings[0].event.severity, 'UNRECOGNIZED');
  assert.equal(normalized.regional_events.length, 4);
  assert.equal(normalized.regional_events[2].geometry, null);
  const geojson = roadAhead.regionalEventsGeoJson(normalized.regional_events, null);
  assert.equal(geojson.features.length, 2);
  assert.deepEqual(geojson.features.map((feature) => feature.geometry.type), ['Point', 'LineString']);
  assert.equal(roadAhead.sourceScopedEventId(normalized.regional_events[0]), 'drivebc-open511-active:point');
  const selected = roadAhead.regionalEventsGeoJson(normalized.regional_events, 'drivebc-open511-active:line');
  assert.equal(selected.features.find((feature) => feature.id.endsWith(':line')).properties.selected, true);
  assert.equal(normalized.source_statuses[0].stale, true);
});

test('keeps unavailable coverage distinct from a usable zero-match snapshot', () => {
  const payload = {
    trip: { origin: {}, destination: {}, mode: 'drive', selected_route: { candidate_id: 'candidate-2', geometry: line, distance_meters: 1, duration_seconds: 1 } },
    status: 'partial', summary: 'Coverage is partial.', analyzed_at: '2026-10-10T10:00:00Z', findings: [], drivebc_findings: [], regional_events: [], unmatchable_events: [],
    source_statuses: [{ source: 'DriveBC Open511', dataset_id: 'drivebc-open511-active-v1', success: false, available: false, stale: false, cache_hit: false, refreshed: false, fetched_at: null, cache_age_seconds: null, error: 'unavailable', records_received: 0, records_normalized: 0, records_skipped: 0 }],
  };
  const normalized = roadAhead.normalizeJourneyAnalysis(payload);
  assert.equal(normalized.status, 'partial');
  assert.equal(normalized.source_statuses[0].available, false);
  assert.equal(normalized.source_statuses[0].records_received, 0);
  assert.deepEqual(normalized.drivebc_findings, []);
  assert.deepEqual(normalized.regional_events, []);
});

test('uses conservative geometry wording and accepts only official Open511 detail URLs', () => {
  assert.equal(drivebc.driveBCRelationLabel('linestring_intersection'), 'Intersects route geometry');
  assert.equal(drivebc.driveBCRelationLabel('linestring_proximity'), 'Nearby road event');
  assert.equal(drivebc.driveBCRelationLabel('point_proximity'), 'Incident location near route');
  const url = 'https://api.open511.gov.bc.ca/events/event-123';
  assert.equal(drivebc.officialDriveBCUrl(url), url);
  assert.equal(drivebc.officialDriveBCUrl('http://api.open511.gov.bc.ca/events/event-123'), null);
  assert.equal(drivebc.officialDriveBCUrl('https://example.com/events/event-123'), null);
  assert.equal(drivebc.officialDriveBCUrl('https://api.open511.gov.bc.ca/events/event-123?next=https://example.com'), null);
});

test('accepts only official Road Ahead detail links and formats cache age conservatively', () => {
  const url = 'https://vanmapp1.vancouver.ca/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d';
  assert.equal(roadAhead.officialDetailUrl(url), url);
  assert.equal(roadAhead.officialDetailUrl('https://example.com/roadahead/events/details/14a078dc-e00d-4cd5-b930-770b52c1513d'), null);
  assert.equal(roadAhead.officialDetailUrl('javascript:alert(1)'), null);
  assert.equal(roadAhead.officialDetailUrl(`${url}?next=https://example.com`), null);
  assert.equal(roadAhead.formatAge(90000), '1d 1h old');
  assert.equal(roadAhead.formatAge(null), null);
});

test('uses cautious official-link wording when detail retrieval is unavailable or fails to parse', () => {
  const cautious = 'Open official Road Ahead detail (page may not be accessible) ↗';
  const normal = 'Open official Road Ahead detail ↗';
  assert.equal(roadAhead.officialDetailLinkLabel('unavailable'), cautious);
  assert.equal(roadAhead.officialDetailLinkLabel('parse_failed'), cautious);
  assert.equal(roadAhead.officialDetailLinkLabel('available'), normal);
  assert.equal(roadAhead.officialDetailLinkLabel('no_supported_fields'), normal);
});
