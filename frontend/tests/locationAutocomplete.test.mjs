import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { test } from 'node:test';

const source = readFileSync(resolve(new URL('../src/LocationAutocomplete.tsx', import.meta.url).pathname), 'utf8');

test('autocomplete sends the selected field role while keeping both fields on the same endpoint', () => {
  assert.match(source, /marker === 'destination-marker' \? 'destination' : 'origin'/);
  assert.match(source, /new URLSearchParams\(\{ q: queryToSearch, role \}\)/);
  assert.match(source, /fetch\(`\/api\/geocoding\/search\?\$\{params\.toString\(\)\}`/);
});
