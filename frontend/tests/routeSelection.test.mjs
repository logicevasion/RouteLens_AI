import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { setImmediate } from 'node:timers/promises';
import ts from 'typescript';
import * as jsxRuntime from 'react/jsx-runtime';

const src = new URL('../src/', import.meta.url);
const componentStubs = new Set(['./VancouverMap', './LocationAutocomplete', './RoadAheadPanel', './DestinationWeatherPanel', './JourneyStageLayout']);
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
      const fileName = `${name}.${name === './App' ? 'tsx' : 'ts'}`;
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
    status() { return render().find((element) => element.props.className === 'route-request-status').props.children.filter(Boolean).join(' '); },
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
    throw new Error(`Unexpected request: ${url}`);
  });
  app.controls('journey-origin').onSelect(origin);
  app.controls('journey-destination').onSelect(destination);
  await setImmediate();
  return { app, searches, analyses };
}

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
    app.button('analyze-button').onClick();
    assert.equal(app.stage().stage, 'understand');
    assert.equal(app.stage().analysis.status, 'loading');

    app.button('find-routes-button').onClick();
    expectSelection(app, [], null);
    assert.match(app.status(), /Requesting driving alternatives/);
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
    if (outcome === 'new routes') expectSelection(app, [second, first], second);
    else expectSelection(app, [], null);
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
