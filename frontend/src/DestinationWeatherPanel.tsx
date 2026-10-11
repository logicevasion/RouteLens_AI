import type { AnalysisState, MeasuredValue } from './analysisTypes';
import { formatObservationAge, formatLocalTime } from './weather';
import { formatAge } from './roadAhead';

function statusLine(status: { available: boolean; stale: boolean; cache_age_seconds: number | null; fetched_at: string | null }, source: string) {
  if (!status.available) return `${source} source unavailable`;
  if (status.stale) return `Stale source data${formatAge(status.cache_age_seconds) ? ` · cache ${formatAge(status.cache_age_seconds)}` : ''}`;
  if (status.cache_age_seconds !== null) return `Last updated ${formatObservationAge(status.cache_age_seconds)}`;
  return status.fetched_at ? `Updated ${formatLocalTime(status.fetched_at)}` : 'Source available';
}

function WeatherMeasurement({ label, value }: { label: string; value: MeasuredValue | null }) {
  if (!value) return null;
  const interval = value.interval_seconds
    ? ` · ${value.interval_seconds === 600 ? '10 min' : value.interval_seconds === 3600 ? '1 hr' : `${Math.round(value.interval_seconds / 60)} min`} accumulation`
    : '';
  return <span className="weather-measurement"><b>{label}</b> {value.value} {value.unit}{interval}</span>;
}

export default function DestinationWeatherPanel({ analysis }: { analysis: AnalysisState }) {
  const weather = analysis.status === 'success' ? analysis.result.destination_weather : null;
  const current = weather?.openweather_current;
  const forecast = weather?.openweather_forecast;
  const eccc = weather?.eccc_status;
  const anyAvailable = Boolean(current?.status.available || forecast?.status.available || eccc?.available);

  return <section className="destination-weather-panel" aria-labelledby="destination-weather-title">
    <div className="weather-heading">
      <div><p className="eyebrow">DESTINATION CONTEXT</p><h3 id="destination-weather-title">Destination Weather</h3></div>
      {analysis.status === 'success' && <span className={`weather-badge${anyAvailable ? '' : ' weather-badge-muted'}`}>{anyAvailable ? 'Weather evidence' : 'Unavailable'}</span>}
    </div>
    {analysis.status === 'idle' && <p className="weather-state">Weather appears after you select a driving route and manually analyze the journey.</p>}
    {analysis.status === 'loading' && <p className="weather-state" role="status"><span className="map-spinner" aria-hidden="true" /> Loading destination weather with road context…</p>}
    {analysis.status === 'error' && <p className="weather-state">Analyze a selected journey to load destination weather.</p>}
    {analysis.status === 'success' && <>
      {!anyAvailable && <p className="weather-state weather-unavailable" role="status">Weather sources are unavailable. No weather condition can be inferred.</p>}
      <section className="weather-source-block" aria-label="OpenWeather current conditions">
        <div className="weather-subheading"><h4>Current Conditions</h4><span>OpenWeather</span></div>
        {current?.weather ? <>
          <div className="current-weather-main">
            <strong>{current.weather.temperature_c === null ? '—' : `${Math.round(current.weather.temperature_c)}°C`}</strong>
            <span>{current.weather.condition?.description ?? current.weather.condition?.group ?? 'Condition unavailable'}
              {current.weather.feels_like_c !== null && <small>Feels like {Math.round(current.weather.feels_like_c)}°C</small>}
            </span>
          </div>
          <div className="weather-metrics">
            {current.weather.humidity_pct !== null && <span>Humidity <b>{Math.round(current.weather.humidity_pct)}%</b></span>}
            {current.weather.wind_speed_m_s !== null && <span>Wind <b>{Math.round(current.weather.wind_speed_m_s * 3.6)} km/h</b></span>}
            {current.weather.visibility_m !== null && <span>Visibility <b>{(current.weather.visibility_m / 1000).toFixed(1)} km</b></span>}
          </div>
          <p className="weather-provenance">Observed {formatLocalTime(current.weather.observed_at)} · {statusLine(current.status, 'OpenWeather')}</p>
          {current.status.stale && <p className="weather-stale-note">Showing the last valid current conditions.</p>}
        </> : <p className="weather-state">{!current?.status.available ? 'Current conditions are unavailable.' : 'No current conditions returned.'}</p>}
      </section>

      <section className="weather-source-block" aria-label="OpenWeather next three hours forecast">
        <div className="weather-subheading"><h4>Next 3 Hours</h4><span>OpenWeather · 15 min</span></div>
        {forecast?.intervals.length ? <div className="forecast-strip">
          {forecast.intervals.map((interval) => <div className="forecast-point" key={interval.forecast_at}>
            <time dateTime={interval.forecast_at}>{formatLocalTime(interval.forecast_at)}</time>
            <b>{interval.temperature_c === null ? '—' : `${Math.round(interval.temperature_c)}°C`}</b>
            <span>{interval.condition?.description ?? interval.condition?.group ?? 'Forecast'}</span>
            <small>{interval.precipitation_probability_pct === null ? 'Chance unavailable' : `${Math.round(interval.precipitation_probability_pct)}% chance`}</small>
          </div>)}
        </div> : <p className="weather-state">Forecast intervals are unavailable.</p>}
        {forecast?.coverage && <p className="weather-provenance">{forecast.coverage.continuous
          ? `${forecast.coverage.returned_interval_count} forecast points through ${formatLocalTime(forecast.coverage.window_end)}`
          : `Forecast coverage incomplete · ${forecast.coverage.returned_interval_count} of ${forecast.coverage.expected_interval_count} expected points`}</p>}
        {forecast?.status.available && <p className={forecast.status.stale ? 'weather-stale-note' : 'weather-provenance'}>{statusLine(forecast.status, 'OpenWeather')}</p>}
      </section>

      <section className="weather-source-block" aria-label="ECCC nearby measured station observations">
        <div className="weather-subheading"><h4>Nearby Station Observations</h4><span>ECCC · measured</span></div>
        {weather?.eccc_observations.length ? <div className="station-list">
          {weather.eccc_observations.map(({ observation, distance_meters, observation_age_seconds, observation_stale, cache_stale }) => <article className="station-observation" key={observation.station_id}>
            <div className="station-title"><b>{observation.station_name ?? observation.station_id}</b><span>{(distance_meters / 1000).toFixed(1)} km from destination</span></div>
            <p className="weather-provenance">Observed {formatObservationAge(observation_age_seconds)} · {formatLocalTime(observation.observed_at)}{observation_stale ? ' · old observation' : ''}</p>
            <div className="weather-measurements">
              <WeatherMeasurement label="Temperature" value={observation.temperature} />
              <WeatherMeasurement label="Humidity" value={observation.relative_humidity} />
              {observation.precipitation.map((value) => <WeatherMeasurement key={value.source_field} label="Measured precipitation" value={value} />)}
              <WeatherMeasurement label="Wind speed" value={observation.wind_speed} />
              <WeatherMeasurement label="Wind direction" value={observation.wind_direction} />
              <WeatherMeasurement label="Snow depth" value={observation.snow_depth} />
            </div>
            {cache_stale && <p className="weather-stale-note">Regional station feed cache is stale.</p>}
          </article>)}
        </div> : <p className="weather-state">{eccc?.available
          ? 'Insufficient measured station coverage near this destination.'
          : 'ECCC station observations are unavailable.'}</p>}
        {eccc?.available && <p className={eccc.stale ? 'weather-stale-note' : 'weather-provenance'}>{statusLine(eccc, 'ECCC GeoMet/SWOB')}</p>}
        <p className="weather-attribution">{weather?.eccc_attribution}</p>
      </section>
    </>}
  </section>;
}
