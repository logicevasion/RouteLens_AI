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
function load(relativePath) {
  const filename = resolve(frontend, relativePath);
  const module = new Module(filename);
  module.filename = filename;
  module.paths = Module._nodeModulePaths(dirname(filename));
  compileTypescript(module, filename);
  return module.exports;
}

const { nextHourForecast, closestEligibleStation } = load('src/weather.ts');
const { roadAheadSummary } = load('src/journeySummary.ts');
const { beginJourneyPresentation, invalidateJourneyPresentation, initialJourneyPresentation } = load('src/presentation.ts');
const { boundedCameraViewIndex } = load('src/cameras.ts');
const JourneyPrimarySummary = load('src/JourneyPrimarySummary.tsx').default;
const JourneyStageLayout = load('src/JourneyStageLayout.tsx').default;

const interval = (forecast_at) => ({ forecast_at });

test('next-hour forecast is timestamp based, sorted, bounded, and preserves gaps', () => {
  const selected = nextHourForecast([
    interval('2026-10-30T13:00:00Z'), interval('2026-10-30T11:45:00Z'),
    interval('2026-10-30T12:45:00Z'), interval('2026-10-30T12:15:00Z'),
    interval('2026-10-30T13:15:00Z'), interval('bad-time'),
  ], '2026-10-30T12:00:00Z');
  assert.deepEqual(selected.map((item) => item.forecast_at), [
    '2026-10-30T12:15:00Z', '2026-10-30T12:45:00Z', '2026-10-30T13:00:00Z',
  ]);
  assert.deepEqual(nextHourForecast([interval('2026-10-30T12:15:00Z')], 'invalid'), []);
});

test('closest ECCC station uses fresh useful measurements and station ID tie-break', () => {
  const observation = (station_id, distance_meters, observation_stale, useful_measurements) => ({
    observation: { station_id }, distance_meters, observation_stale, useful_measurements,
  });
  const closest = closestEligibleStation([
    observation('stale-close', 1, true, ['temperature']),
    observation('empty-close', 2, false, []),
    observation('station-z', 100, false, ['wind_speed']),
    observation('station-a', 100, false, ['temperature']),
  ]);
  assert.equal(closest.observation.station_id, 'station-a');
  assert.equal(closestEligibleStation([]), null);
});

test('Road Ahead count excludes nearby events and qualifies incomplete or unavailable sources', () => {
  const success = {
    status: 'success', error: null, result: {
      status: 'available', findings: [
        { classification: 'direct_overlap' }, { classification: 'nearby' }, { classification: 'direct_overlap' },
      ], source_statuses: [{ dataset_id: 'road-ahead-current-road-closures', available: true, stale: false }],
    },
  };
  assert.equal(roadAheadSummary(success).count, 2);
  assert.match(roadAheadSummary(success).message, /2 Road Ahead events intersect/);
  assert.equal(roadAheadSummary({ ...success, result: { ...success.result, status: 'partial' } }).status, 'available');
  const partial = { ...success, result: { ...success.result, status: 'partial', source_statuses: [
    ...success.result.source_statuses, { dataset_id: 'road-ahead-projects-under-construction', available: false, stale: false },
  ] } };
  assert.match(roadAheadSummary(partial).message, /partial or stale/);
  const unavailable = { ...success, result: { ...success.result, source_statuses: [
    { dataset_id: 'road-ahead-current-road-closures', available: false, stale: false },
  ] } };
  assert.equal(roadAheadSummary(unavailable).status, 'unavailable');
  const zero = { ...success, result: { ...success.result, findings: [] } };
  assert.match(roadAheadSummary(zero).message, /does not mean roads are clear/);
});

test('journey presentation enters after valid analysis and resets on invalidation', () => {
  assert.equal(beginJourneyPresentation(initialJourneyPresentation, false, 'now'), initialJourneyPresentation);
  const active = beginJourneyPresentation(initialJourneyPresentation, true, '2026-10-30T12:00:00Z');
  assert.deepEqual(active, { stage: 'understand', analysisAt: '2026-10-30T12:00:00Z' });
  assert.deepEqual(invalidateJourneyPresentation(), { stage: 'plan', analysisAt: null });
});

test('Analyze Journey commits the Stage 2 transition before the controller ref changes', () => {
  const appSource = readFileSync(resolve(frontend, 'src/App.tsx'), 'utf8');
  const analyzeStart = appSource.indexOf('async function analyzeJourney()');
  const analyzeEnd = appSource.indexOf('\n  useEffect(() => () => {', analyzeStart);
  const analyzeSource = appSource.slice(analyzeStart, analyzeEnd);
  assert.match(analyzeSource, /setPresentation\(beginJourneyPresentation\(presentation, true, attemptStartedAt\)\)/);
  assert.ok(analyzeSource.indexOf('setPresentation(beginJourneyPresentation') < analyzeSource.indexOf('analysisController.current = controller'));
  assert.doesNotMatch(analyzeSource, /setPresentation\(\(current\)\s*=>\s*beginJourneyPresentation\(current.*analysisController\.current/s);
});

test('application stage layout mounts the primary summary and retains workspace through Stage 1 to Stage 2 and back', () => {
  const React = require('react');
  const { readFileSync } = require('node:fs');
  const { renderToStaticMarkup } = require('react-dom/server');
  const analysis = { status: 'loading', result: null, error: null };
  const camera = { status: 'loading', requestKey: 'attempt-a' };
  const render = (state) => {
    const workspace = React.createElement('div', { className: `workspace workspace-stage-${state.stage}` },
      React.createElement('div', { className: 'map-workspace', role: 'application', 'aria-label': 'Interactive journey map' }, 'Map'),
      React.createElement('aside', { className: 'intelligence-panel' }, 'Choose your route · Road Ahead · DriveBC'));
    return renderToStaticMarkup(React.createElement(JourneyStageLayout, {
      stage: state.stage, analysis, camera, analysisAt: state.analysisAt ?? '',
    }, workspace));
  };

  const stage1 = render(initialJourneyPresentation);
  assert.doesNotMatch(stage1, /Understand Your Journey/);
  assert.match(stage1, /Interactive journey map/);
  assert.match(stage1, /Choose your route/);
  assert.match(stage1, /workspace-stage-plan/);

  const stage2State = beginJourneyPresentation(initialJourneyPresentation, true, '2026-10-30T12:00:00Z');
  const stage2 = render(stage2State);
  assert.ok(stage2.indexOf('Understand Your Journey') < stage2.indexOf('Interactive journey map'));
  assert.match(stage2, /Destination Cameras/);
  assert.match(stage2, /Destination Weather/);
  assert.match(stage2, /Checking route-intersecting Road Ahead events/);
  assert.match(stage2, /Interactive journey map/);
  assert.match(stage2, /Road Ahead · DriveBC/);
  assert.match(stage2, /workspace-stage-understand/);
  assert.doesNotMatch(stage2, /summary-anchor[^>]*hidden|style="display:none/);

  const returnedToStage1 = render(invalidateJourneyPresentation());
  assert.doesNotMatch(returnedToStage1, /Understand Your Journey/);
  assert.match(returnedToStage1, /Interactive journey map/);

  const css = readFileSync(resolve(frontend, 'src/styles.css'), 'utf8');
  assert.match(css, /\.app-shell-stage-understand \{ height: 100vh; height: 100dvh; min-height: 0; overflow-x: hidden; overflow-y: auto; \}/);
  assert.match(css, /\.workspace-stage-understand \{ height: auto; min-height: 0; flex: 0 0 auto; align-items: start; \}/);
  assert.match(css, /\.workspace-stage-understand \.map-workspace \{ height: min\(70vh, 820px\); min-height: 520px; \}/);
  assert.match(css, /\.workspace-stage-understand \.intelligence-panel \{ min-height: 0; overflow: visible; \}/);
  assert.match(css, /\.app-shell \{\s*display: flex;\s*width: 100%;\s*height: 100vh;\s*height: 100dvh;\s*min-height: 620px;\s*flex-direction: column;\s*overflow: hidden;/);
  assert.match(css, /\.workspace-stage-plan \{ grid-template-columns: minmax\(0, 65fr\) minmax\(330px, 35fr\); \}/);
  assert.match(css, /html, body, #root \{ height: auto; \}/);
  assert.match(css, /body \{ overflow: auto; \}/);
});

test('Stage 2 keeps header and journey controls before the summary and resets viewport to the top once', () => {
  const appSource = readFileSync(resolve(frontend, 'src/App.tsx'), 'utf8');
  const header = appSource.indexOf('<header className="topbar">');
  const controls = appSource.indexOf('<JourneyControls', header);
  const stageContent = appSource.indexOf('<JourneyStageLayout', controls);
  assert.ok(header >= 0 && controls > header && stageContent > controls);
  assert.doesNotMatch(appSource.slice(header, stageContent), /stage === 'understand'/);
  assert.match(appSource, /appShellRef\.current\?\.scrollTo\(\{ top: 0, behavior: 'auto' \}\)/);
  assert.match(appSource, /window\.scrollTo\(\{ top: 0, behavior: 'auto' \}\)/);
  assert.doesNotMatch(appSource, /scrollIntoView\(/);
  assert.match(appSource, /\}, \[stage\]\);/);
});

test('camera gallery index clamps safely for zero, one, and variable view counts', () => {
  assert.equal(boundedCameraViewIndex(10, 0), 0);
  assert.equal(boundedCameraViewIndex(-1, 1), 0);
  assert.equal(boundedCameraViewIndex(7, 5), 4);
  assert.equal(boundedCameraViewIndex(2.8, 5), 2);
});

test('primary summary presents settled camera evidence while deterministic analysis is still loading', () => {
  const camera = {
    status: 'success', requestKey: 'attempt-a', result: {
      status: 'available', intersection: {
        intersection_id: 'intersection-a', name: 'Main and Broadway', distance_metres: 250,
        official_page_url: 'https://trafficcams.vancouver.ca/example.htm', source: 'City of Vancouver', attribution: 'Camera source attribution',
      },
      views: [{ view_id: 'view-a', direction_label: 'Eastbound', image_reference: '/api/cameras/images/a',
        retrieved_at: '2026-10-30T12:00:00Z', source_capture_at: null, cache_age_seconds: 0,
        stale: false, width: 800, height: 464, content_type: 'image/jpeg' }],
      stale_views: [], diagnostics: { views_failed: 0, stale_views: 0, catalogue_stale: false },
    },
  };
  const html = renderToStaticMarkup(require('react').createElement(JourneyPrimarySummary, {
    analysis: { status: 'loading', result: null, error: null }, camera, analysisAt: '2026-10-30T12:00:00Z',
  }));
  assert.match(html, /Understand Your Journey/);
  assert.match(html, /Eastbound/);
  assert.match(html, /View 1 of 1/);
  assert.match(html, /Loading destination weather/);
  assert.match(html, /Checking route-intersecting Road Ahead events/);
  assert.doesNotMatch(html, /AI Journey Briefing/);
});

test('camera evidence stays visible when deterministic analysis fails', () => {
  const camera = {
    status: 'success', requestKey: 'attempt-b', result: {
      status: 'available', intersection: {
        intersection_id: 'intersection-b', name: 'Broadway and Main', distance_metres: 100,
        official_page_url: 'https://trafficcams.vancouver.ca/example.htm', source: 'City of Vancouver', attribution: 'Camera source attribution',
      },
      views: [{ view_id: 'view-b', direction_label: 'Westbound', image_reference: '/api/cameras/images/b',
        retrieved_at: '2026-10-30T12:00:00Z', source_capture_at: null, cache_age_seconds: 0,
        stale: false, width: 800, height: 464, content_type: 'image/jpeg' }],
      stale_views: [], diagnostics: { views_failed: 0, catalogue_stale: false },
    },
  };
  const html = renderToStaticMarkup(require('react').createElement(JourneyPrimarySummary, {
    analysis: { status: 'error', result: null, error: 'analysis unavailable' }, camera, analysisAt: '2026-10-30T12:00:00Z',
  }));
  assert.match(html, /Westbound/);
  assert.match(html, /analysis failed/);
  assert.match(html, /Weather is unavailable because journey analysis failed/);
});
