import type { DestinationWeather, WeatherSourceStatus } from './analysisTypes';

type RecordValue = Record<string, unknown>;
const isRecord = (value: unknown): value is RecordValue => typeof value === 'object' && value !== null && !Array.isArray(value);
const text = (value: unknown): string | null => typeof value === 'string' ? value : null;
const number = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null;
const numericCount = (value: unknown): number => typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : 0;

function sourceStatus(value: unknown, source: string, dataset: string): WeatherSourceStatus {
  const status = isRecord(value) ? value : {};
  return {
    source: text(status.source) ?? source,
    dataset_id: text(status.dataset_id) ?? dataset,
    success: status.success === true,
    available: status.available === true,
    fetched_at: text(status.fetched_at),
    cache_hit: status.cache_hit === true,
    refreshed: status.refreshed === true,
    stale: status.stale === true,
    cache_age_seconds: number(status.cache_age_seconds),
    error: text(status.error),
  };
}

function condition(value: unknown) {
  if (!isRecord(value)) return null;
  return { code: number(value.code), group: text(value.group), description: text(value.description) };
}

function coordinates(value: unknown) {
  if (!isRecord(value)) return null;
  const latitude = number(value.latitude);
  const longitude = number(value.longitude);
  return latitude === null || longitude === null ? null : { latitude, longitude };
}

function currentEvidence(value: unknown) {
  if (!isRecord(value) || typeof value.observed_at !== 'string' || typeof value.fetched_at !== 'string') return null;
  return {
    source: text(value.source) ?? 'OpenWeather', product: text(value.product) ?? 'onecall4_current',
    observed_at: value.observed_at, fetched_at: value.fetched_at,
    requested_coordinates: coordinates(value.requested_coordinates),
    provider_coordinates: coordinates(value.provider_coordinates),
    temperature_c: number(value.temperature_c), feels_like_c: number(value.feels_like_c),
    condition: condition(value.condition), humidity_pct: number(value.humidity_pct),
    wind_speed_m_s: number(value.wind_speed_m_s), wind_direction_deg: number(value.wind_direction_deg),
    wind_gust_m_s: number(value.wind_gust_m_s), visibility_m: number(value.visibility_m),
    rain_1h_mm: number(value.rain_1h_mm), snow_1h_mm: number(value.snow_1h_mm),
  };
}

function forecastInterval(value: unknown) {
  if (!isRecord(value) || typeof value.forecast_at !== 'string' || typeof value.fetched_at !== 'string') return null;
  return {
    source: text(value.source) ?? 'OpenWeather', product: text(value.product) ?? 'onecall4_timeline_15min',
    forecast_at: value.forecast_at, fetched_at: value.fetched_at,
    requested_coordinates: coordinates(value.requested_coordinates),
    precipitation_probability_pct: number(value.precipitation_probability_pct),
    temperature_c: number(value.temperature_c), feels_like_c: number(value.feels_like_c),
    condition: condition(value.condition), humidity_pct: number(value.humidity_pct),
    wind_speed_m_s: number(value.wind_speed_m_s), wind_direction_deg: number(value.wind_direction_deg),
    wind_gust_m_s: number(value.wind_gust_m_s), visibility_m: number(value.visibility_m),
    rain_1h_mm: number(value.rain_1h_mm), rain_3h_mm: number(value.rain_3h_mm),
    snow_1h_mm: number(value.snow_1h_mm), snow_3h_mm: number(value.snow_3h_mm),
  };
}

function measuredValue(value: unknown) {
  if (!isRecord(value) || number(value.value) === null || typeof value.unit !== 'string' || typeof value.source_field !== 'string') return null;
  return {
    value: value.value as number, unit: value.unit, source_field: value.source_field,
    interval_seconds: number(value.interval_seconds), quality_code: number(value.quality_code),
  };
}

function station(value: unknown) {
  if (!isRecord(value) || !isRecord(value.observation)) return null;
  const row = value.observation;
  if (typeof row.station_id !== 'string' || typeof row.observed_at !== 'string' || typeof row.retrieved_at !== 'string') return null;
  const stationIdentifiers = isRecord(row.station_identifiers)
    ? Object.fromEntries(Object.entries(row.station_identifiers).filter((entry): entry is [string, string] => typeof entry[1] === 'string'))
    : undefined;
  const precipitation = Array.isArray(row.precipitation) ? row.precipitation.map(measuredValue).filter((item) => item !== null) : [];
  const measurements = ['temperature', 'relative_humidity', 'wind_speed', 'wind_direction', 'snow_depth'] as const;
  const normalized = Object.fromEntries(measurements.map((key) => [key, measuredValue(row[key])])) as Record<(typeof measurements)[number], ReturnType<typeof measuredValue>>;
  return {
    observation: {
      source: text(row.source) ?? 'ECCC GeoMet/SWOB', station_id: row.station_id,
      ...(typeof row.source_record_id === 'string' ? { source_record_id: row.source_record_id } : {}),
      ...(stationIdentifiers ? { station_identifiers: stationIdentifiers } : {}),
      station_name: text(row.station_name), latitude: number(row.latitude), longitude: number(row.longitude),
      observed_at: row.observed_at, retrieved_at: row.retrieved_at,
      ...normalized, precipitation, attribution: text(row.attribution) ?? 'Environment and Climate Change Canada GeoMet/SWOB',
    },
    distance_meters: number(value.distance_meters) ?? 0,
    observation_age_seconds: numericCount(value.observation_age_seconds),
    observation_stale: value.observation_stale === true, cache_stale: value.cache_stale === true,
    useful_measurements: Array.isArray(value.useful_measurements) ? value.useful_measurements.filter((item): item is string => typeof item === 'string') : [],
    selection_reason: text(value.selection_reason) ?? '',
  };
}

export function unavailableDestinationWeather(): DestinationWeather {
  return {
    openweather_current: { weather: null, status: sourceStatus(null, 'OpenWeather', 'onecall4_current') },
    openweather_forecast: { intervals: [], coverage: null, status: sourceStatus(null, 'OpenWeather', 'onecall4_timeline_15min') },
    eccc_status: sourceStatus(null, 'ECCC GeoMet/SWOB', 'swob-realtime'), eccc_observations: [],
    eccc_attribution: 'Contains information licensed under the Open Government Licence – Canada. Source: Environment and Climate Change Canada GeoMet/SWOB.',
  };
}

export function normalizeDestinationWeather(value: unknown): DestinationWeather {
  if (!isRecord(value)) return unavailableDestinationWeather();
  const current = isRecord(value.openweather_current) ? value.openweather_current : {};
  const forecast = isRecord(value.openweather_forecast) ? value.openweather_forecast : {};
  const coverageValue = isRecord(forecast.coverage) ? forecast.coverage : null;
  const intervals = Array.isArray(forecast.intervals) ? forecast.intervals.map(forecastInterval).filter((item) => item !== null) : [];
  const stations = Array.isArray(value.eccc_observations) ? value.eccc_observations.map(station).filter((item) => item !== null) : [];
  return {
    openweather_current: {
      weather: currentEvidence(current.weather),
      status: sourceStatus(current.status, 'OpenWeather', 'onecall4_current'),
    },
    openweather_forecast: {
      intervals,
      coverage: coverageValue ? {
        evaluation_time: text(coverageValue.evaluation_time) ?? '', window_end: text(coverageValue.window_end) ?? '',
        first_interval_at: text(coverageValue.first_interval_at), last_interval_at: text(coverageValue.last_interval_at),
        expected_interval_count: numericCount(coverageValue.expected_interval_count),
        returned_interval_count: numericCount(coverageValue.returned_interval_count),
        missing_intervals: Array.isArray(coverageValue.missing_intervals) ? coverageValue.missing_intervals.filter((item): item is string => typeof item === 'string') : [],
        malformed_records: numericCount(coverageValue.malformed_records), duplicate_records: numericCount(coverageValue.duplicate_records),
        initial_page_only: coverageValue.initial_page_only === true, continuous: coverageValue.continuous === true,
      } : null,
      status: sourceStatus(forecast.status, 'OpenWeather', 'onecall4_timeline_15min'),
    },
    eccc_status: sourceStatus(value.eccc_status, 'ECCC GeoMet/SWOB', 'swob-realtime'),
    eccc_observations: stations,
    eccc_attribution: text(value.eccc_attribution) ?? unavailableDestinationWeather().eccc_attribution,
  };
}

export function formatObservationAge(seconds: number): string {
  if (seconds < 60) return 'under 1 minute ago';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours} hour${hours === 1 ? '' : 's'} ago`;
}

export function formatLocalTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}
