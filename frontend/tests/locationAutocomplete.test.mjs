import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { setImmediate } from 'node:timers/promises';
import ts from 'typescript';

const source = readFileSync(new URL('../src/LocationAutocomplete.tsx', import.meta.url), 'utf8');
const { outputText } = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    jsx: ts.JsxEmit.React,
    target: ts.ScriptTarget.ES2022,
  },
});

// Run the component's input handler and effect with just the hooks needed for this interaction.
function mountAutocomplete(marker, fetch, onSelect = () => {}) {
  const state = [];
  const refs = [];
  let stateIndex = 0;
  let refIndex = 0;
  let pendingEffect;
  let dependencies;
  let cleanup;
  let debounce;

  const react = {
    createElement: (type, props, ...children) => ({ type, props, children }),
    useId: () => 'autocomplete-list',
    useRef(initial) {
      const index = refIndex++;
      refs[index] ??= { current: initial };
      return refs[index];
    },
    useState(initial) {
      const index = stateIndex++;
      if (!(index in state)) state[index] = initial;
      return [state[index], (value) => { state[index] = value; }];
    },
    useEffect(effect, nextDependencies) {
      if (!dependencies || nextDependencies.some((value, index) => !Object.is(value, dependencies[index]))) {
        dependencies = nextDependencies;
        pendingEffect = effect;
      }
    },
  };
  const window = {
    setTimeout(callback) {
      debounce = callback;
    },
    clearTimeout() {
      debounce = undefined;
    },
  };
  const exports = {};
  new Function('exports', 'require', 'React', 'window', 'fetch', outputText)(
    exports, () => react, react, window, fetch,
  );
  const Component = exports.default;
  const props = {
    id: marker,
    label: marker,
    placeholder: 'Search',
    marker,
    selectedLocation: null,
    onQueryEdit() {},
    onSelect,
  };

  function render() {
    stateIndex = 0;
    refIndex = 0;
    const tree = Component(props);
    if (pendingEffect) {
      cleanup?.();
      cleanup = pendingEffect();
      pendingEffect = undefined;
    }
    return tree;
  }

  return {
    input: [...elements(render())].find(({ type }) => type === 'input'),
    render,
    search() {
      render();
      assert.equal(typeof debounce, 'function', 'typing should schedule a search');
      debounce();
    },
    unmount() {
      cleanup?.();
    },
  };
}

function* elements(element) {
  if (Array.isArray(element)) {
    for (const child of element) yield* elements(child);
  } else if (element?.type) {
    yield element;
    yield* elements(element.children);
  }
}

test('autocomplete displays the local quota message and can select a later successful result', async (t) => {
  const selected = [];
  const place = { name: 'Stanley Park', latitude: 49.3, longitude: -123.14 };
  const fetch = t.mock.fn(async () => ({ ok: true, status: 200, json: async () => [place] }));
  fetch.mock.mockImplementationOnce(async () => ({
    ok: false, status: 429, json: async () => ({ detail: { code: 'daily_quota_exhausted' } }),
  }));
  const autocomplete = mountAutocomplete('destination-marker', fetch, (location) => selected.push(location));
  t.after(() => autocomplete.unmount());

  autocomplete.input.props.onChange({ target: { value: 'Stanley' } });
  autocomplete.search();
  await setImmediate();
  assert.deepEqual(
    [...elements(autocomplete.render())].find(({ props }) => props?.role === 'status').children,
    ["Location search has reached today's usage limit. Please try again tomorrow."],
  );

  autocomplete.input.props.onChange({ target: { value: 'Stanley Park' } });
  autocomplete.search();
  await setImmediate();
  const option = [...elements(autocomplete.render())].find(({ props }) => props?.role === 'option');
  option.props.onClick();
  assert.deepEqual(selected, [place]);
  assert.equal([...elements(autocomplete.render())].some(({ props }) => props?.role === 'listbox'), false);
});

for (const [role, query] of [['destination', 'Stanley Park'], ['origin', 'A&B café #1']]) {
  test(`typing in the ${role} field sends role=${role}`, (t) => {
    const fetch = t.mock.fn(async () => ({ ok: true, json: async () => [] }));
    const autocomplete = mountAutocomplete(`${role}-marker`, fetch);
    t.after(() => autocomplete.unmount());

    autocomplete.input.props.onChange({ target: { value: query } });
    autocomplete.search();

    assert.equal(fetch.mock.calls.length, 1);
    const [request] = fetch.mock.calls[0].arguments;
    const url = new URL(request, 'http://localhost');
    assert.equal(url.pathname, '/api/geocoding/search');
    assert.equal(url.searchParams.get('q'), query);
    assert.equal(url.searchParams.get('role'), role);
  });
}
