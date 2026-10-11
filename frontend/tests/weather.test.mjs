import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/weather.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const weather = await import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`);

const validWeather = () => ({
  openweather_current: {
    weather: {
      source: 'OpenWeather', product: 'onecall4_current', observed_at: '2026-10-11T12:00:00Z', fetched_at: '2026-10-11T12:03:00Z',
      temperature_c: 8.5, feels_like_c: 6.5, condition: { code: 804, group: 'Clouds', description: 'overcast clouds' },
      humidity_pct: 80, wind_speed_m_s: 2, wind_direction_deg: 180, wind_gust_m_s: null, visibility_m: 10000,
    },
    status: { source: 'OpenWeather', dataset_id: 'onecall4_current', success: false, available: true, stale: true,
      cache_age_seconds: 900, fetched_at: '2026-10-11T12:03:00Z' },
  },
  openweather_forecast: {
    intervals: [
      { source: 'OpenWeather', product: 'onecall4_timeline_15min', forecast_at: '2026-10-11T12:15:00Z', fetched_at: '2026-10-11T12:03:00Z', temperature_c: 8, precipitation_probability_pct: 0 },
      { source: 'OpenWeather', product: 'onecall4_timeline_15min', forecast_at: '2026-10-11T12:45:00Z', fetched_at: '2026-10-11T12:03:00Z', temperature_c: null, precipitation_probability_pct: null },
    ],
    coverage: { evaluation_time: '2026-10-11T12:03:00Z', window_end: '2026-10-11T15:03:00Z', expected_interval_count: 12,
      returned_interval_count: 2, missing_intervals: ['2026-10-11T12:30:00Z'], continuous: false },
    status: { source: 'OpenWeather', dataset_id: 'onecall4_timeline_15min', available: true, stale: false },
  },
  eccc_status: { source: 'ECCC GeoMet/SWOB', dataset_id: 'swob-realtime', available: true, stale: false },
  eccc_observations: [{
    observation: {
      source: 'ECCC GeoMet/SWOB', station_id: 'station-1', station_name: 'Vancouver Harbour',
      latitude: 49.29, longitude: -123.12, observed_at: '2026-10-11T11:45:00Z', retrieved_at: '2026-10-11T12:03:00Z',
      temperature: { value: 8, unit: '°C', source_field: 'air_temp' },
      relative_humidity: null, precipitation: [], wind_speed: null, wind_direction: null, snow_depth: null,
      attribution: 'ECCC GeoMet/SWOB',
    },
    distance_meters: 4200, observation_age_seconds: 1080, observation_stale: false, cache_stale: false,
    useful_measurements: ['temperature'], selection_reason: 'fresh nearby station',
  }],
  eccc_attribution: 'Environment and Climate Change Canada GeoMet/SWOB',
});

test('normalizes current, forecast and station evidence as distinct sources', () => {
  const value = weather.normalizeDestinationWeather(validWeather());
  assert.equal(value.openweather_current.weather.temperature_c, 8.5);
  assert.equal(value.openweather_current.weather.condition.description, 'overcast clouds');
  assert.equal(value.openweather_forecast.intervals[0].precipitation_probability_pct, 0);
  assert.equal(value.openweather_forecast.intervals[1].precipitation_probability_pct, null);
  assert.equal(value.openweather_forecast.coverage.continuous, false);
  assert.equal(value.eccc_observations[0].distance_meters, 4200);
  assert.equal(value.eccc_observations[0].observation_age_seconds, 1080);
  assert.deepEqual(value.eccc_observations[0].observation.precipitation, []);
});

test('retains source staleness and does not invent missing station precipitation', () => {
  const value = weather.normalizeDestinationWeather(validWeather());
  assert.equal(value.openweather_current.status.stale, true);
  assert.equal(value.openweather_current.status.cache_age_seconds, 900);
  assert.equal(value.eccc_observations[0].observation.precipitation.length, 0);
  assert.equal(weather.formatObservationAge(1080), '18 minutes ago');
});

test('all weather unavailable remains explicit and unknown', () => {
  const value = weather.normalizeDestinationWeather({
    openweather_current: { status: { available: false } },
    openweather_forecast: { intervals: [], coverage: null, status: { available: false } },
    eccc_status: { available: false }, eccc_observations: [],
  });
  assert.equal(value.openweather_current.weather, null);
  assert.equal(value.openweather_current.status.available, false);
  assert.equal(value.openweather_forecast.status.available, false);
  assert.equal(value.eccc_status.available, false);
  assert.deepEqual(value.eccc_observations, []);
});
