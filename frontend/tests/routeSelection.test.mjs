import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { setImmediate } from 'node:timers/promises';
import ts from 'typescript';
import * as jsxRuntime from 'react/jsx-runtime';

const src = new URL('../src/', import.meta.url);
const componentStubs = new Set(['./VancouverMap', './LocationAutocomplete', './RoadAheadPanel', './DestinationWeatherPanel', './JourneyStageLayout']);
const tsxModules = new Set(['./App', './ApiUsageDisclosure']);
const compiled = new Map();

// Run App and its controls/panel handlers with the real request builders and normalizers.
// Leaf components are stubs so the test can inspect map inputs without WebGL.
function mountApp(fetch) {
  let nextHook = 0;
  const hooks = [];
  const react = {
    useState(initial) {
      const index = nextHook++;
      if (!(index in hooks)) hooks[index] = initial;
      return [hooks[index], (value) => {
        hooks[index] = typeof value === 'function' ? value(hooks[index]) : value;
      }];
    },
    useRef(initial) {
      const index = nextHook++;
      hooks[index] ??= { current: initial };
      return hooks[index];
    },
    useMemo: (compute) => compute(),
    useEffect() {},
  };
  const modules = new Map();
  function load(name) {
    if (name === 'react') return react;
    if (name === 'react/jsx-runtime') return jsxRuntime;
    if (componentStubs.has(name)) return { default: name.slice(2) };
    if (modules.has(name)) return modules.get(name);
    if (!compiled.has(name)) {
      const fileName = `${name}.${tsxModules.has(name) ? 'tsx' : 'ts'}`;
      const source = readFileSync(new URL(fileName, src), 'utf8');
      const { outputText } = ts.transpileModule(source, {
        fileName,
        compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
      });
      compiled.set(name, new Function('exports', 'require', 'fetch', outputText));
    }
    const exports = {};
    compiled.get(name)(exports, load, fetch);
    modules.set(name, exports);
    return exports;
  }

  const App = load('./App').default;
  function render() {
    nextHook = 0;
    return [...elements(App())];
  }
  return {
    controls(id) { return render().find((element) => element.props.id === id).props; },
    button(className) { return render().find((element) => element.type === 'button' && element.props.className === className).props; },
    cards() { return render().filter((element) => element.props.className?.split(' ').includes('route-candidate')); },
    map() { return render().find((element) => element.type === 'VancouverMap').props; },
    stage() { return render().find((element) => element.type === 'JourneyStageLayout').props; },
    usage() { return render().find((element) => element.props.className === 'api-usage'); },
    status() { return render().find((element) => element.props.className === 'route-request-status').props.children.filter(Boolean).join(' '); },
    panel() {
      const panel = render().find((element) => element.type === 'aside' && element.props.className === 'intelligence-panel');
      const nodes = [...elements(panel)];
      const overview = nodes.find((element) => element.props.className === 'journey-overview');
      const heading = [...elements(overview)].find((element) => element.type === 'h3').props.children;
      const status = nodes.find((element) => element.props.className === 'panel-status').props.children;
      return { heading, status: status.filter((child) => typeof child === 'string').join('').trim() };
    },
  };
}

function* elements(node) {
  if (Array.isArray(node)) {
    for (const child of node) yield* elements(child);
  } else if (node?.props) {
    if (typeof node.type === 'function') {
      yield* elements(node.type(node.props));
    } else {
      yield node;
      yield* elements(node.props.children);
    }
  }
}

const origin = { name: 'Richmond', latitude: 49.16, longitude: -123.14 };
const destination = { name: 'Vancouver', latitude: 49.28, longitude: -123.12 };
const first = {
  id: 'provider-first', label: 'First', distance_meters: 12_000, duration_seconds: 1_200,
  geometry: { type: 'LineString', coordinates: [[-123.14, 49.16], [-123.12, 49.28]] },
};
const second = {
  id: 'provider-second', label: 'Second', distance_meters: 11_000, duration_seconds: 1_000,
  geometry: { type: 'LineString', coordinates: [[-123.14, 49.16], [-123.13, 49.21], [-123.12, 49.28]] },
};
const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });

async function setup() {
  const searches = [];
  const analyses = [];
  const usage = [];
  const app = mountApp((url, options) => {
    if (url === '/api/locations/validate-destination') return Promise.resolve(response({ valid: true, reason: null }));
    if (url === '/api/routes/driving' || url === '/api/trips/analyze') {
      const requests = url === '/api/routes/driving' ? searches : analyses;
      const { promise, resolve, reject } = Promise.withResolvers();
      requests.push({ body: JSON.parse(options.body), signal: options.signal, resolve, reject });
      return promise;
    }
    if (['/api/cameras/observe', '/api/cameras/nearest', '/api/cameras/nearby'].includes(url)) {
      return Promise.resolve(response({}, 503));
    }
    if (url === '/api/usage') {
      const { promise, resolve } = Promise.withResolvers();
      usage.push({ signal: options.signal, resolve });
      return promise;
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  app.controls('journey-origin').onSelect(origin);
  app.controls('journey-destination').onSelect(destination);
  await setImmediate();
  return { app, searches, analyses, usage };
}

const usageReport = {
  status: 'ok',
  start_date: '2026-10-28',
  end_date: '2026-11-26',
  providers: [
    { provider: 'maptiler', status: 'tracked', attempts: 12 },
    { provider: 'openrouteservice', status: 'tracked', attempts: 0 },
    { provider: 'vancouver_traffic_cameras', status: 'tracked', attempts: 3 },
    { provider: 'maptiler_map_resources', status: 'untracked', attempts: null },
  ],
};

function usageText(app, tag) {
  return [...elements(app.usage())].filter((node) => node.type === tag)
    .map((node) => [node.props.children].flat().join(''));
}

test('usage loads on opening and preserves route selection and on-demand analysis', async () => {
  const { app, searches, analyses, usage } = await setup();
  assert.deepEqual(usageText(app, 'summary'), ['API Usage']);
  assert.equal(app.usage().props.open, undefined);
  assert.equal(usage.length, 0);
  app.button('find-routes-button').onClick();
  searches[0].resolve(response({ routes: [first, second] }));
  await setImmediate();
  app.cards()[1].props.onClick();

  app.usage().props.onToggle({ currentTarget: { open: true } });
  assert.equal(usage.length, 1);
  assert.deepEqual(usageText(app, 'h2'), ['API Usage — Last 30 Days']);
  assert.ok(usageText(app, 'p').includes('Loading usage…'));
  usage[0].resolve(response(usageReport));
  await setImmediate();
  assert.ok(usageText(app, 'p').includes('2026-10-28 – 2026-11-26 (UTC)'));
  assert.deepEqual(usageText(app, 'dt'), [
    'MapTiler geocoding', 'openrouteservice', 'Vancouver camera images', 'MapTiler map resources',
  ]);
  assert.deepEqual(usageText(app, 'dd'), ['12', '0', '3', 'Untracked']);
  assert.ok(usageText(app, 'p').some((text) => text.includes('Camera counts cover image requests only.')));
  expectSelection(app, [first, second], second);
  assert.equal(analyses.length, 0);
  app.button('analyze-button').onClick();
  assert.equal(analyses[0].body.selected_route.candidate_id, second.id);
  assert.equal(app.stage().stage, 'understand');
  assert.equal(usage.length, 1);
  analyses[0].resolve(response({}, 503));
  await setImmediate();
});

test('usage shows errors and recovers on reopening, with explicit tracking states', async () => {
  const { app, usage } = await setup();
  const toggle = (open) => app.usage().props.onToggle({ currentTarget: { open } });
  toggle(true);
  usage[0].resolve(response({}, 503));
  await setImmediate();
  assert.ok(usageText(app, 'p').some((text) => text.includes('Could not load API usage')));
  toggle(false);
  assert.equal(usage[0].signal.aborted, true);
  toggle(true);
  assert.ok(usageText(app, 'p').includes('Loading usage…'));
  usage[1].resolve(response({ ...usageReport, status: 'degraded' }));
  await setImmediate();
  assert.ok(usageText(app, 'p').some((text) => text.includes('Counts may be incomplete')));
  assert.deepEqual(usageText(app, 'dd'), ['12', '0', '3', 'Untracked']);

  toggle(false);
  toggle(true);
  usage[2].resolve(response({
    ...usageReport,
    status: 'unavailable',
    providers: usageReport.providers.map((row) => row.status === 'tracked'
      ? { ...row, status: 'unavailable', attempts: null }
      : row),
  }));
  await setImmediate();
  assert.ok(usageText(app, 'p').includes('Usage tracking is currently unavailable.'));
  assert.deepEqual(usageText(app, 'dd'), ['Untracked']);
});

function expectSelection(app, candidates, selected) {
  assert.deepEqual(app.map().routes, candidates);
  assert.equal(app.map().selectedRouteId, selected?.id ?? null);
  const cards = app.cards();
  assert.equal(cards.length, candidates.length);
  for (const [index, card] of cards.entries()) {
    assert.equal(card.key, candidates[index].id);
    const pressed = candidates[index].id === selected?.id;
    assert.equal(card.props['aria-pressed'], pressed);
    assert.equal(card.props.className.split(' ').includes('route-candidate-selected'), pressed);
  }
  assert.equal(app.button('analyze-button').disabled, !selected);
}

for (const candidates of [[first], [first, second]]) {
  test(`selects the first of ${candidates.length} returned routes and analyzes it on demand`, async () => {
    const { app, searches, analyses } = await setup();
    assert.equal(app.button('find-routes-button').disabled, false);
    app.button('find-routes-button').onClick();
    searches[0].resolve(response({ routes: candidates }));
    await setImmediate();

    expectSelection(app, candidates, first);
    assert.equal(analyses.length, 0);
    app.button('analyze-button').onClick();
    assert.equal(analyses[0].body.selected_route.candidate_id, first.id);
    assert.deepEqual(analyses[0].body.selected_route.geometry, first.geometry);
    analyses[0].resolve(response({}, 503));
    await setImmediate();
  });
}

test('manual selection moves card and map emphasis and changes the analysis request', async () => {
  const { app, searches, analyses } = await setup();
  app.button('find-routes-button').onClick();
  searches[0].resolve(response({ routes: [first, second] }));
  await setImmediate();

  app.cards()[1].props.onClick();
  expectSelection(app, [first, second], second);
  app.button('analyze-button').onClick();
  assert.equal(analyses[0].body.selected_route.candidate_id, second.id);
  assert.deepEqual(analyses[0].body.selected_route.geometry, second.geometry);
  analyses[0].resolve(response({}, 503));
  await setImmediate();
});

for (const [outcome, finishSearch, expectedStatus] of [
  ['new routes', (request) => request.resolve(response({ routes: [second, first] })), /routes available/],
  ['empty response', (request) => request.resolve(response({ routes: [] })), /No usable routes/],
  ['HTTP failure', (request) => request.resolve(response({}, 503)), /temporarily unavailable/],
  ['network failure', (request) => request.reject(new Error('Offline')), /temporarily unavailable/],
]) {
  test(`a new search clears the previous selection and analysis before ${outcome}`, async () => {
    const { app, searches, analyses } = await setup();
    app.button('find-routes-button').onClick();
    searches[0].resolve(response({ routes: [first, second] }));
    await setImmediate();
    assert.deepEqual(app.panel(), { heading: 'Route selected', status: 'Route selected' });
    app.button('analyze-button').onClick();
    assert.equal(app.stage().stage, 'understand');
    assert.equal(app.stage().analysis.status, 'loading');

    app.button('find-routes-button').onClick();
    expectSelection(app, [], null);
    assert.match(app.status(), /Requesting driving alternatives/);
    const clearedPanel = { heading: 'No journey selected', status: 'Waiting for a journey' };
    assert.deepEqual(app.panel(), clearedPanel);
    assert.equal(app.stage().stage, 'plan');
    assert.equal(app.stage().analysis.status, 'idle');
    assert.equal(analyses[0].signal.aborted, true);

    analyses[0].resolve(response({
      trip: analyses[0].body, status: 'partial', findings: [],
      summary: 'Prior analysis', analyzed_at: '2026-11-23T12:00:00Z',
      source_statuses: [{ source: 'City of Vancouver Road Ahead', available: true }],
    }));
    finishSearch(searches[1]);
    await setImmediate();
    assert.equal(app.stage().analysis.status, 'idle');
    if (outcome === 'new routes') {
      expectSelection(app, [second, first], second);
    } else {
      expectSelection(app, [], null);
      assert.deepEqual(app.panel(), clearedPanel);
    }
    assert.equal(app.button('find-routes-button').disabled, false);
    assert.match(app.status(), expectedStatus);
  });
}

test('a superseded response body cannot replace the newer results or manual selection', async () => {
  const { app, searches } = await setup();
  app.button('find-routes-button').onClick();
  const oldBody = Promise.withResolvers();
  searches[0].resolve({ ok: true, json: () => oldBody.promise });
  await setImmediate();

  app.controls('journey-origin').onQueryEdit();
  assert.equal(searches[0].signal.aborted, true);
  app.controls('journey-origin').onSelect({ ...origin, name: 'Other origin' });
  app.button('find-routes-button').onClick();
  searches[1].resolve(response({ routes: [second, first] }));
  await setImmediate();
  expectSelection(app, [second, first], second);
  app.cards()[1].props.onClick();

  oldBody.resolve({ routes: [{ ...first, id: 'stale-route' }] });
  await setImmediate();
  expectSelection(app, [second, first], first);
});

for (const [failure, finishSearch] of [
  ['HTTP error', (request) => request.resolve(response({}, 503))],
  ['network rejection', (request) => request.reject(new Error('Offline'))],
]) {
  test(`a late ${failure} cannot replace newer route results or selection`, async () => {
    const { app, searches } = await setup();
    app.button('find-routes-button').onClick();
    app.controls('journey-origin').onQueryEdit();
    app.controls('journey-origin').onSelect({ ...origin, name: 'Other origin' });
    app.button('find-routes-button').onClick();
    searches[1].resolve(response({ routes: [second, first] }));
    await setImmediate();
    expectSelection(app, [second, first], second);

    finishSearch(searches[0]);
    await setImmediate();
    expectSelection(app, [second, first], second);
    assert.equal(app.status(), '2 routes available.');
  });
}

for (const input of ['origin', 'destination']) {
  test(`editing the ${input} discards an in-flight search without starting another`, async () => {
    const { app, searches } = await setup();
    app.button('find-routes-button').onClick();
    assert.match(app.status(), /Requesting driving alternatives/);

    app.controls(`journey-${input}`).onQueryEdit();
    assert.equal(searches[0].signal.aborted, true);
    assert.equal(app.status(), '');

    // This mock still resolves after abort so the test exercises stale-response handling.
    searches[0].resolve(response({ routes: [first, second] }));
    await setImmediate();
    assert.equal(searches.length, 1);
    expectSelection(app, [], null);
    assert.equal(app.status(), '');
    assert.equal(app.button('find-routes-button').disabled, true);
  });
}
