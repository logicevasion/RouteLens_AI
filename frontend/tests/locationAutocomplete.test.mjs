import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
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
function mountAutocomplete(marker, fetch) {
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
    onSelect() {},
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
    input: findInput(render()),
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

function findInput(element) {
  if (element?.type === 'input') return element;
  for (const child of element?.children ?? []) {
    const input = findInput(child);
    if (input) return input;
  }
}

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
