import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';

const mapSource = await readFile(new URL('../src/VancouverMap.tsx', import.meta.url), 'utf8');
const roadAheadSource = await readFile(new URL('../src/roadAhead.ts', import.meta.url), 'utf8');
const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('selected route uses lavender while preserving its selected line width', () => {
  assert.match(mapSource, /'line-color': '#B794F6', 'line-width': 5\.5, 'line-opacity': 1/);
  assert.match(appSource, /selected \? '#B794F6' : routeColor\(route\.id\)/);
});

test('selected Road Ahead fill and line retain direct-overlap red and nearby yellow meaning', () => {
  assert.match(roadAheadSource, /classification: finding\.classification/);
  const semanticColor = /'line-color': \['case', \['==', \['get', 'classification'\], 'direct_overlap'\], '#ee7966', '#e5ba70'\]/;
  const semanticFill = /'fill-color': \['case', \['==', \['get', 'classification'\], 'direct_overlap'\], '#ee7966', '#e5ba70'\]/;
  assert.match(mapSource, semanticColor);
  assert.match(mapSource, semanticFill);
  assert.match(mapSource, /'line-width': 7, 'line-opacity': 1/);
});
