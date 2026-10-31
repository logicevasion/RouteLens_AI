import assert from 'node:assert/strict';
import { dirname, resolve } from 'node:path';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { createRequire, Module } from 'node:module';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const frontend = resolve(new URL('..', import.meta.url).pathname);
const appSource = readFileSync(resolve(frontend, 'src/App.tsx'), 'utf8');
const css = readFileSync(resolve(frontend, 'src/styles.css'), 'utf8');
const require = createRequire(new URL('../package.json', import.meta.url));
function compileTypescript(module, filename) {
  module._compile(ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText, filename);
}
require.extensions['.ts'] = compileTypescript;
require.extensions['.tsx'] = compileTypescript;
function load(path) {
  const filename = resolve(frontend, path);
  const module = new Module(filename);
  module.filename = filename;
  module.paths = Module._nodeModulePaths(dirname(filename));
  compileTypescript(module, filename);
  return module.exports;
}

const RoadAheadPanel = load('src/RoadAheadPanel.tsx').default;
const DestinationWeatherPanel = load('src/DestinationWeatherPanel.tsx').default;

function collectHostElements(node, tagName, found = []) {
  if (Array.isArray(node)) {
    node.forEach((child) => collectHostElements(child, tagName, found));
  } else if (node && typeof node === 'object' && 'type' in node && 'props' in node) {
    if (typeof node.type === 'function') collectHostElements(node.type(node.props), tagName, found);
    else {
      if (node.type === tagName) found.push(node);
      collectHostElements(node.props.children, tagName, found);
    }
  }
  return found;
}

const cityEvent = (id, title) => ({
  id, source: 'City of Vancouver', source_dataset_id: 'road-ahead-projects-under-construction', source_record_id: id,
  event_type: 'construction', title, description: null, geometry: { type: 'Point', coordinates: [-123.1, 49.2] },
  latitude: 49.2, longitude: -123.1, severity: null, status: null, schedule_text: null, restriction_text: null,
  observed_at: null, updated_at: null, source_url: null, relevance_reason: null, source_metadata: {}, attribution: 'City of Vancouver',
});
const analysis = {
  status: 'success', error: null, result: {
    status: 'partial', summary: 'Coverage may be incomplete.', analyzed_at: '2026-10-30T12:00:00Z',
    findings: [
      { event: cityEvent('direct-a', 'Direct route work'), classification: 'direct_overlap', distance_meters: 0, detail: {} },
      { event: cityEvent('nearby-a', 'Nearby local work'), classification: 'nearby', distance_meters: 180, detail: {} },
    ],
    drivebc_findings: [{ event: { ...cityEvent('drive-a', 'DriveBC closure'), source: 'DriveBC Open511', source_dataset_id: 'drivebc-open511-current', source_record_id: 'drive-a', attribution: 'DriveBC Open511' },
      classification: 'nearby', distance_meters: 600, geometry_basis: 'point_proximity', source_evidence: { roads: [], severity: null,
        event_type: 'closure', status: null, schedule_text: null, direction_assessment: 'undetermined', temporal_applicability: 'unknown',
        current_impact: 'not_established' } }],
    regional_events: [], source_statuses: [
      { dataset_id: 'road-ahead-projects-under-construction', source: 'Road Ahead', available: true, stale: false, cache_hit: false,
        refreshed: true, cache_age_seconds: null, fetched_at: null, records_received: 2 },
      { dataset_id: 'drivebc-open511-current', source: 'DriveBC', available: false, stale: false, cache_hit: false,
        refreshed: false, cache_age_seconds: null, fetched_at: null, records_received: 0 },
    ], unmatchable_events: [], destination_weather: null,
  },
};

test('Stage 2 orders summary, map and direct events, Experimental briefing, then collapsed support', () => {
  const summary = appSource.indexOf('<JourneyStageLayout');
  const workspace = appSource.indexOf('<div className={`workspace workspace-stage-${stage}`}');
  const briefing = appSource.indexOf('<BriefingCard briefingState={journeyBriefingState} />');
  const support = appSource.indexOf('<section className="supporting-information"');
  assert.ok(summary >= 0 && workspace > summary && briefing > workspace && support > briefing);
  assert.match(appSource, /<VancouverMap[\s\S]*?selectedEventId=\{activeSelectedEvent\}/);
  assert.match(appSource, /<RoadAheadPanel[\s\S]*?presentation="route"/);
  assert.match(appSource, /presentation="supporting"/);
  assert.match(css, /\.workspace-stage-understand \{ grid-template-columns: minmax\(0, 3fr\) minmax\(300px, 2fr\); \}/);
  assert.match(css, /\.workspace-stage-understand \.route-events-panel \{ max-height: min\(70vh, 820px\); min-height: 520px; overflow-y: auto;/);
  assert.match(css, /@media \(max-width: 760px\)[\s\S]*?\.workspace \{ display: flex; flex-direction: column/);
  assert.match(css, /\.app-shell-stage-understand \{ height: 100vh; height: 100dvh; min-height: 0; overflow-x: hidden; overflow-y: auto; \}/);
});

test('road events panel shows direct intersections and collapsed source-specific nearby and DriveBC sections', () => {
  const route = renderToStaticMarkup(require('react').createElement(RoadAheadPanel, {
    analysis, selectedEventId: 'road-ahead-projects-under-construction:direct-a', onSelectFinding() {}, presentation: 'route',
  }));
  assert.match(route, /Direct route work/);
  assert.match(route, /aria-pressed="true"/);
  assert.match(route, /ROAD EVENTS &amp; DISRUPTIONS/);
  assert.match(route, /On your route — City of Vancouver Road Ahead/);
  assert.match(route, /Nearby Road Ahead events \(1\)/);
  assert.match(route, /DriveBC Open511 \(1\)/);
  assert.match(route, /Nearby local work/);
  assert.match(route, /DriveBC closure/);
  assert.ok(route.indexOf('Direct route intersections') < route.indexOf('Nearby Road Ahead events (1)'));
  assert.ok(route.indexOf('Nearby Road Ahead events (1)') < route.indexOf('DriveBC Open511 (1)'));
  assert.ok(route.indexOf('Direct route intersections') < route.indexOf('<details class="route-event-disclosure">'));
  assert.match(route, /analysis-available/);
  assert.match(route, /DriveBC Open511 is unavailable/);
  assert.doesNotMatch(route, /<details[^>]*open/);
  assert.doesNotMatch(route, /route is clear|disruption-free roads/);

  const support = renderToStaticMarkup(require('react').createElement(RoadAheadPanel, {
    analysis, selectedEventId: 'drivebc-open511-current:drive-a', onSelectFinding() {}, presentation: 'supporting',
  }));
  assert.doesNotMatch(support, /Nearby local work|DriveBC closure|Nearby Road Ahead events|DriveBC Open511 · route-relevant findings/);
  assert.match(support, /Road Ahead · Projects under construction/);
  assert.match(support, /DriveBC · Open511 regional events/);
  assert.match(support, /Coverage from this dataset is reduced/);
  assert.match(support, /regional DriveBC events shown on map are separate from route findings/);
});

test('supporting sections use native closed disclosure controls and keep full forecast without repeating current summary', () => {
  const supportSections = appSource.slice(appSource.indexOf('<section className="supporting-information"'));
  assert.match(supportSections, /<details className="supporting-disclosure">\s*<summary>Full three-hour forecast and ECCC station observations/);
  assert.match(supportSections, /<summary>Detailed road source status and freshness/);
  assert.doesNotMatch(supportSections, /presentation="supporting"[\s\S]*?Nearby Road Ahead events|presentation="supporting"[\s\S]*?DriveBC closure/);
  assert.match(supportSections, /<summary>Regional map context/);
  assert.doesNotMatch(supportSections, /<details[^>]*open/);
  assert.match(supportSections, /supportingOnly/);
  assert.match(css, /\.supporting-disclosure > summary:focus-visible/);
  assert.match(css, /\.route-event-disclosure > summary:focus-visible/);
  assert.match(css, /\.workspace-stage-understand \.route-events-panel \{[^}]*overflow-y: auto/);

  const weather = { status: 'success', error: null, result: { destination_weather: {
    openweather_current: { weather: { temperature_c: 10, source: 'OpenWeather' }, status: { available: true, stale: false } },
    openweather_forecast: { intervals: [{ forecast_at: '2026-10-30T13:00:00Z', temperature_c: 11, feels_like_c: 9,
      humidity_pct: 80, wind_speed_m_s: 1, visibility_m: 4000, rain_1h_mm: 0.5, precipitation_probability_pct: 20,
      condition: { description: 'Cloudy' } }], coverage: null, status: { available: true, stale: false } },
    eccc_status: { available: true, stale: false }, eccc_observations: [], eccc_attribution: 'ECCC attribution',
  } } };
  const html = renderToStaticMarkup(require('react').createElement(DestinationWeatherPanel, { analysis: weather, supportingOnly: true }));
  assert.match(html, /Next 3 Hours/);
  assert.match(html, /Feels like 9°C/);
  assert.match(html, /ECCC · measured/);
  assert.doesNotMatch(html, /Current Conditions|10°C/);
});

test('all three source sections share event selection callbacks with the map and preserve their source semantics', () => {
  const panelSource = readFileSync(resolve(frontend, 'src/RoadAheadPanel.tsx'), 'utf8');
  assert.match(panelSource, /FindingGroup title="Direct route intersections"[\s\S]*?onSelectFinding=\{onSelectFinding\}/);
  assert.match(panelSource, /FindingGroup title="Nearby Road Ahead events"[\s\S]*?onSelectFinding=\{onSelectFinding\}/);
  assert.match(panelSource, /DriveBCGroup title="LineString intersections"[\s\S]*?onSelectFinding=\{onSelectFinding\}/);
  assert.match(panelSource, /DriveBCGroup title="Nearby or regional events"[\s\S]*?onSelectFinding=\{onSelectFinding\}/);
  assert.match(panelSource, /const id = sourceScopedEventId\(finding\.event\);[\s\S]*?onSelect=\{\(\) => onSelectFinding\(id\)\}/);
  assert.match(panelSource, /finding\.geometry_basis === 'linestring_intersection'/);
  assert.match(panelSource, /finding\.geometry_basis !== 'linestring_intersection'/);
  assert.match(panelSource, /An ACTIVE source status does not confirm an effect on traffic right now/);
  assert.match(appSource, /<VancouverMap[\s\S]*?onSelectEvent=\{setSelectedEventId\}/);
});

test('clicking a direct, nearby, or DriveBC finding emits its source-scoped map selection id', () => {
  const selected = [];
  const tree = RoadAheadPanel({ analysis, selectedEventId: null, onSelectFinding: (id) => selected.push(id), presentation: 'route' });
  for (const button of collectHostElements(tree, 'button')) button.props.onClick();
  assert.deepEqual(selected, [
    'road-ahead-projects-under-construction:direct-a',
    'road-ahead-projects-under-construction:nearby-a',
    'drivebc-open511-current:drive-a',
  ]);
});

test('zero direct intersections stay qualified and disclosure counts use returned source findings', () => {
  const zeroAnalysis = structuredClone(analysis);
  zeroAnalysis.result.findings = [];
  zeroAnalysis.result.drivebc_findings = [];
  const html = renderToStaticMarkup(require('react').createElement(RoadAheadPanel, {
    analysis: zeroAnalysis, selectedEventId: null, onSelectFinding() {}, presentation: 'route',
  }));
  assert.match(html, /No direct Road Ahead route intersections were identified in available datasets/);
  assert.match(html, /This does not confirm that the route is disruption-free/);
  assert.match(html, /Nearby Road Ahead events \(0\)/);
  assert.match(html, /DriveBC Open511 \(0\)/);
  assert.match(html, /No nearby Road Ahead events were returned/);
  assert.match(html, /DriveBC route findings could not be checked because the Open511 source is unavailable/);
  assert.doesNotMatch(html, /No events found\. The route is clear|No disruptions/);
});
