import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { test } from 'node:test';
import { createRequire, Module } from 'node:module';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const frontend = resolve(new URL('..', import.meta.url).pathname);
const require = createRequire(new URL('../package.json', import.meta.url));
function compileTypescript(module, filename) {
  const source = readFileSync(filename, 'utf8');
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
    },
  }).outputText;
  module._compile(compiled, filename);
}
require.extensions['.ts'] = compileTypescript;
require.extensions['.tsx'] = compileTypescript;

const componentPath = resolve(frontend, 'src/DestinationWeatherPanel.tsx');
const componentModule = new Module(componentPath);
componentModule.filename = componentPath;
componentModule.paths = Module._nodeModulePaths(dirname(componentPath));
compileTypescript(componentModule, componentPath);
const DestinationWeatherPanel = componentModule.exports.default;

function analysis(weather) {
  return {
    status: 'success', error: null, result: {
      destination_weather: weather,
      trip: { destination: { name: 'Vancouver' } }, findings: [{ event: { id: 'road-1' } }],
      drivebc_findings: [], regional_events: [], source_statuses: [], summary: 'Road findings retained',
      analyzed_at: '2026-10-11T12:00:00Z', status: 'available', unmatchable_events: [],
    },
  };
}

test('renders current conditions, actual forecast timestamps, and measured station age/distance', () => {
  const weather = {
    openweather_current: {
      weather: { temperature_c: 8.5, feels_like_c: 7, observed_at: '2026-10-11T12:00:00Z',
        condition: { description: 'overcast clouds' }, humidity_pct: 80, wind_speed_m_s: 2, visibility_m: 10000 },
      status: { available: true, stale: false, fetched_at: '2026-10-11T12:02:00Z', cache_age_seconds: 0 },
    },
    openweather_forecast: {
      intervals: [{ forecast_at: '2026-10-11T12:15:00Z', temperature_c: 8, precipitation_probability_pct: 30,
        condition: { description: 'light rain' } }],
      coverage: { continuous: false, returned_interval_count: 1, expected_interval_count: 12, window_end: '2026-10-11T15:00:00Z' },
      status: { available: true, stale: false, fetched_at: '2026-10-11T12:02:00Z' },
    },
    eccc_status: { available: true, stale: false, fetched_at: '2026-10-11T12:02:00Z' },
    eccc_observations: [{ observation: { station_id: 'station-1', station_name: 'Vancouver Harbour',
      observed_at: '2026-10-11T11:42:00Z', temperature: { value: 8, unit: '°C' }, relative_humidity: null,
      precipitation: [], wind_speed: null, wind_direction: null, snow_depth: null },
      distance_meters: 4200, observation_age_seconds: 1080, observation_stale: false, cache_stale: false }],
    eccc_attribution: 'Environment and Climate Change Canada GeoMet/SWOB',
  };
  const html = renderToStaticMarkup(require('react').createElement(DestinationWeatherPanel, { analysis: analysis(weather) }));
  assert.match(html, /Destination Weather/);
  assert.match(html, /8°C/);
  assert.match(html, /overcast clouds/);
  assert.match(html, /12:15/);
  assert.match(html, /30% precipitation probability/);
  assert.match(html, /Forecast coverage incomplete/);
  assert.match(html, /Vancouver Harbour/);
  assert.match(html, /4\.2 km from destination/);
  assert.match(html, /18 minutes ago/);
  assert.match(html, /ECCC · measured/);
  assert.doesNotMatch(html, /Measured precipitation/);
});

test('labels stale source data and independently unavailable products', () => {
  const weather = {
    openweather_current: { weather: null, status: { available: false, stale: false } },
    openweather_forecast: { intervals: [], coverage: null, status: { available: false, stale: false } },
    eccc_status: { available: true, stale: true, cache_age_seconds: 1200 }, eccc_observations: [],
    eccc_attribution: 'ECCC attribution',
  };
  const html = renderToStaticMarkup(require('react').createElement(DestinationWeatherPanel, { analysis: analysis(weather) }));
  assert.match(html, /Current conditions are unavailable/);
  assert.match(html, /Forecast intervals are unavailable/);
  assert.match(html, /Insufficient measured station coverage/);
  assert.match(html, /Stale source data/);
});

test('labels total weather failure without claiming fair conditions', () => {
  const weather = {
    openweather_current: { weather: null, status: { available: false, stale: false } },
    openweather_forecast: { intervals: [], coverage: null, status: { available: false, stale: false } },
    eccc_status: { available: false, stale: false }, eccc_observations: [], eccc_attribution: 'ECCC attribution',
  };
  const html = renderToStaticMarkup(require('react').createElement(DestinationWeatherPanel, { analysis: analysis(weather) }));
  assert.match(html, /Weather sources are unavailable/);
  assert.match(html, /No weather condition can be inferred/);
  assert.match(html, /ECCC station observations are unavailable/);
  assert.doesNotMatch(html, /clear weather/i);
});

test('primary summary shows only upcoming next-hour intervals and the closest eligible station', () => {
  const weather = {
    openweather_current: {
      weather: { source: 'OpenWeather', temperature_c: null, feels_like_c: null, observed_at: '2026-10-11T12:00:00Z',
        fetched_at: '2026-10-11T12:02:00Z', condition: null, humidity_pct: null, wind_speed_m_s: null, visibility_m: null },
      status: { available: true, stale: false, fetched_at: '2026-10-11T12:02:00Z' },
    },
    openweather_forecast: {
      intervals: ['11:45', '12:15', '12:45', '13:15'].map((time) => ({
        forecast_at: `2026-10-11T${time}:00Z`, fetched_at: '2026-10-11T12:02:00Z', source: 'OpenWeather',
        temperature_c: null, feels_like_c: null, condition: null, humidity_pct: null, wind_speed_m_s: null,
        visibility_m: null, precipitation_probability_pct: null,
      })),
      coverage: { evaluation_time: '2026-10-11T11:58:00Z', continuous: false, returned_interval_count: 4,
        expected_interval_count: 12, window_end: '2026-10-11T15:00:00Z', missing_intervals: [] },
      status: { available: true, stale: false, fetched_at: '2026-10-11T12:02:00Z' },
    },
    eccc_status: { available: true, stale: false, fetched_at: '2026-10-11T12:02:00Z' },
    eccc_observations: [
      { observation: { station_id: 'stale-nearest', station_name: 'Stale', observed_at: '2026-10-11T11:00:00Z' },
        distance_meters: 50, observation_stale: true, cache_stale: false, useful_measurements: ['temperature'], observation_age_seconds: 3600 },
      { observation: { station_id: 'not-useful', station_name: 'Empty', observed_at: '2026-10-11T11:55:00Z' },
        distance_meters: 100, observation_stale: false, cache_stale: false, useful_measurements: [], observation_age_seconds: 300 },
      { observation: { station_id: 'eligible', station_name: 'Fresh Station', observed_at: '2026-10-11T11:55:00Z',
        temperature: { value: 9, unit: '°C', source_field: 'temperature', interval_seconds: null, quality_code: null },
        relative_humidity: null, precipitation: [], wind_speed: null, wind_direction: null, snow_depth: null },
        distance_meters: 300, observation_stale: false, cache_stale: true, useful_measurements: ['temperature'], observation_age_seconds: 300 },
    ],
    eccc_attribution: 'Environment and Climate Change Canada GeoMet/SWOB',
  };
  const html = renderToStaticMarkup(require('react').createElement(DestinationWeatherPanel, {
    analysis: analysis(weather), presentation: 'primary', analysisAt: '2026-10-11T12:00:00Z',
  }));
  assert.match(html, /Next Hour/);
  assert.doesNotMatch(html, /11:45/);
  assert.match(html, /12:15/);
  assert.match(html, /12:45/);
  assert.doesNotMatch(html, /13:15/);
  assert.match(html, /Provider evaluation/);
  assert.match(html, /Fresh Station · eligible/);
  assert.match(html, /Regional station feed cache is stale/);
  assert.doesNotMatch(html, /Stale · stale-nearest|Empty · not-useful/);
  assert.match(html, /—/);
});

test('primary next-hour cards stay compact while supporting forecast retains detailed measurements', () => {
  const weather = {
    openweather_current: { weather: null, status: { available: false, stale: false } },
    openweather_forecast: {
      intervals: [{ forecast_at: '2026-10-11T12:15:00Z', fetched_at: '2026-10-11T12:00:00Z', source: 'OpenWeather',
        temperature_c: 9, feels_like_c: 9, condition: { code: 500, group: 'Rain', description: 'light rain showers' },
        humidity_pct: 84, wind_speed_m_s: 0.56, visibility_m: 4000, rain_1h_mm: 1.78,
        precipitation_probability_pct: 30 }],
      coverage: { evaluation_time: '2026-10-11T12:00:00Z', continuous: true, returned_interval_count: 1,
        expected_interval_count: 1, window_end: '2026-10-11T13:00:00Z', missing_intervals: [] },
      status: { available: true, stale: false, fetched_at: '2026-10-11T12:00:00Z' },
    },
    eccc_status: { available: false, stale: false }, eccc_observations: [], eccc_attribution: 'ECCC attribution',
  };
  const react = require('react');
  const primary = renderToStaticMarkup(react.createElement(DestinationWeatherPanel, {
    analysis: analysis(weather), presentation: 'primary', analysisAt: '2026-10-11T12:00:00Z',
  }));
  assert.match(primary, /12:15/);
  assert.match(primary, /9°C/);
  assert.match(primary, /light rain showers/);
  assert.match(primary, /30% precipitation probability/);
  assert.doesNotMatch(primary, /Feels like 9°C|Humidity 84%|Wind 2 km\/h|Visibility 4\.0 km|Rain 1\.78 mm/);
  assert.doesNotMatch(primary, /Feels like 9°C.*Humidity 84%.*Wind 2 km\/h/);

  const supporting = renderToStaticMarkup(react.createElement(DestinationWeatherPanel, { analysis: analysis(weather) }));
  assert.match(supporting, /Next 3 Hours/);
  assert.match(supporting, /Feels like 9°C/);
  assert.match(supporting, /Humidity 84%/);
  assert.match(supporting, /Wind 2 km\/h/);
  assert.match(supporting, /Visibility 4\.0 km/);
  assert.match(supporting, /Rain 1\.78 mm/);
});
