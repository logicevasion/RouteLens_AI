# OpenWeather Phase 6A Integration Validation

**Checked:** 2026-10-11 (UTC)

**Scope:** live integration validation and recommendations only; no production adapter, endpoint, UI, or journey integration was changed.

## Credential and request results

`OPENWEATHER_API_KEY` was present and non-placeholder in the ignored local `.env`. Its value was not displayed or copied into the repository. `.env` remains Git-ignored. All requests used the representative Vancouver coordinate `49.2827, -123.1207`, metric units, and a bounded single request per endpoint.

| Product | Official endpoint | Live result | Access and account notes |
|---|---|---:|---|
| Current Weather API | `GET https://api.openweathermap.org/data/2.5/weather` | HTTP 200, valid JSON | Access confirmed. OpenWeather lists current weather as free for everyone; this account's precise plan and update entitlement were not inspected. |
| 5 day / 3 hour Forecast API | `GET https://api.openweathermap.org/data/2.5/forecast` | HTTP 200, valid JSON | Access confirmed. OpenWeather lists this product as free for everyone; this account's precise plan and update entitlement were not inspected. |
| One Call API 4.0 current | `GET https://api.openweathermap.org/data/4.0/onecall/current` | HTTP 200, valid JSON | Access confirmed for this request. Product documentation says One Call 4.0 is only in the separate One Call by Call subscription: first 1,000 calls/day are free and further calls are charged. The account's subscription and billing settings were not inspected or changed. |
| One Call API 4.0 15-minute timeline | `GET https://api.openweathermap.org/data/4.0/onecall/timeline/15min` | HTTP 200, valid JSON | Access confirmed for this request; same separate subscription and billing caveat as above. Only the first response page was requested. |
| One Call API 3.0 | `GET https://api.openweathermap.org/data/3.0/onecall` | Not tested | Current OpenWeather pricing labels 3.0 deprecated. No request was made. |

No HTTP 401, 403, or 429 was returned. The initial network attempt was blocked before reaching the provider; the approved network-enabled retry produced the results above. Account-level plan, remaining quota, automatic billing configuration, and applicable terms remain unverified. No subscription was purchased or activated.

Official product documentation: [Current Weather](https://openweathermap.org/api/current), [5 day / 3 hour Forecast](https://openweathermap.org/api/forecast5), [One Call 4.0](https://openweathermap.org/api/one-call-4), [pricing and product availability](https://openweathermap.org/price), [API key and usage guidance](https://openweathermap.org/appid).

## Live response findings

The sanitized fixtures preserve the successful provider JSON structure. One Call timeline pagination URL fields are replaced with a redaction marker because provider-generated URLs may contain the credential.

### Current Weather API (`current_vancouver_phase6a.json`)

- `coord` returned the requested longitude/latitude; `dt` was Unix seconds in UTC (`2026-10-11T12:30:34Z`). `timezone` was a `-25200` second offset; there was no IANA timezone name.
- `main.temp` was 7.49 °C and `main.feels_like` 5.72 °C. The structured `weather[]` item contained `id`, `main`, `description`, and `icon` (`Clear` / `clear sky` in this sample).
- Humidity was 74%; wind had speed, direction, and gust; visibility was 10,000 m. These are provider current-condition fields, not an ECCC station measurement.
- `rain` and `snow` objects were absent. Absence means unknown/not returned, not zero precipitation.
- Retrieval time is not included by the provider and must be set by RouteLens separately from `dt`.

### 5 day / 3 hour Forecast (`forecast_vancouver_phase6a.json`)

- `city.coord` matched the representative coordinate; `city.timezone` was the same UTC offset. Each item had `dt` (Unix UTC seconds) and a local-formatted `dt_txt` string.
- The response had 40 forecast records from `2026-10-11T15:00:00Z` to `2026-10-16T12:00:00Z`; all 39 measured timestamp differences were exactly 10,800 seconds (3 hours).
- Every record had `main` (including temperature, feels-like and humidity), `weather[]` (`id`, `main`, `description`, `icon`), `wind` (speed m/s, direction degrees, gust where present), `pop`, and `clouds`. Visibility appeared on 39/40 records.
- `pop` was present for all 40 records and ranged from explicit 0 to 0.99 (fraction, so multiply by 100 for percent). Three records included `rain.3h` amounts in mm; `snow` was absent from all records. Do not turn absent amounts into zero.
- The next forecast point in this capture was about 2.5 hours after the current observation. A 3-hour step can show a useful near-term point but cannot resolve changes within that interval; the next point can be nearly three hours away.

### One Call 4.0 (`onecall4_current_vancouver_phase6a.json`, `onecall4_15min_vancouver_phase6a.json`)

- Current response returned top-level `lat`, `lon`, IANA `timezone` (`America/Vancouver`), `timezone_offset` (-25,200 seconds), and one item in `data[]`. Its `dt` was Unix UTC seconds (`2026-10-11T12:31:35Z`).
- Current `data[]` included temperature and feels-like (metric °C), weather condition structure, humidity, visibility (m), wind speed (m/s), direction and gust, pressure, cloud, dew point, and UV. Rain/snow and alert fields were absent in this sample.
- The 15-minute timeline returned 50 records spaced 900 seconds apart, from `2026-10-11T12:30:00Z` through `2026-10-12T00:45:00Z` (12.25 hours between the first and last record). `next` was present, so this is only the first page, not the product's full forecast horizon.
- Each observed timeline record had a `pop` value (all were explicit 0 in this live sample), temperature, feels-like, condition, humidity, wind, visibility, cloud, dew point, and UV. No rain/snow amount or alert field appeared in these records. This confirms a finer forecast timestamp and precipitation-probability field, not a precipitation amount in this response.

All numeric units above describe the `units=metric` requests: temperature °C, wind m/s, precipitation mm (with provider accumulation period retained), visibility metres, humidity percent, and `pop` as a 0–1 probability. Optional weather phenomena and measurements can be omitted rather than returned as `null`; normalizers should accept missing fields.

## Near-departure usefulness and sampling

The basic Current + Forecast products jointly provide current destination conditions and a five-day horizon. Their 3-hour intervals are coarse for the next one to three hours: they offer a forecast point, not minute-level transition timing. The observed current response and forecast response can be kept as separate evidence categories.

One Call 4.0's 15-minute timeline is materially more useful for short-horizon change detection. In this sample it supplied probability for each interval but no precipitation amount, and the first 50-record page covered only 12.25 hours. Pagination would add requests and must be bounded if adopted. Its subscription and billing dependency is a product decision, not required for the simpler basic-product contract.

Use one request coordinate: the canonical selected Vancouver destination. `49.2827, -123.1207` (Vancouver City Hall) is the representative validation point, not a hard-coded product destination. No live evidence here establishes a need for route-coordinate sampling. Keep SWOB station readings distinct from the coordinate-based OpenWeather response.

## Phase 6 recommendation

1. **Preferred cost-simple contract:** Current Weather API plus 5 day / 3 hour Forecast API. Both live requests returned HTTP 200 and both products are listed as free for everyone. This is two API products/requests per uncached destination analysis and accepts a 3-hour forecast resolution.
2. **Optional finer alternative:** One Call 4.0 current and 15-minute timeline endpoints also returned HTTP 200. Consider this only after confirming the account's One Call subscription, billing controls, applicable terms, and desired pagination/request budget. It is one product family but still separate current and forecast requests; it is not required for the datathon MVP if 3-hour forecasts are acceptable.
3. **Fields and normalization:** keep current provider condition separate from forecast intervals. Proposed current shape: source/product, requested coordinate, provider `observed_at`, RouteLens `retrieved_at`, optional timezone name/offset, temperature °C, feels-like °C, condition code/group/description, nullable rain/snow amount with source period, humidity %, wind speed normalized to km/h if following the existing conceptual model, direction degrees, gust, and visibility in km or metres with one explicit unit. Proposed forecast interval shape: UTC `forecast_at`, actual `interval_minutes` (180 or 15 only for the tested products), temperature/feels-like °C, condition, nullable `precipitation_probability_pct`, nullable amount/type and accumulation period, nullable wind/humidity/visibility, and source provenance. Retain absent values as `None` and preserve forecast-versus-current semantics.
4. **Cache:** start with a 600-second per-product TTL keyed by selected destination coordinate rounded to four decimals, product, units, and other response-affecting parameters. Reuse a fresh successful response across repeated analyses at the same key. On failed refresh, return the last schema-valid cache entry with its original provider timestamp, fetch time, stale age, and explicit stale status; if no valid cache exists, mark the source unavailable and leave weather unknown. Do not silently replace valid cache with malformed responses. Ten minutes is a conservative initial repeated-request guard and matches One Call 4.0's documented 10-minute update cadence. OpenWeather says update frequency for its other products depends on subscription; the local account's basic-product tier was not inspected, so revisit TTL after confirming the plan. Avoid persisting a weather database beyond the application cache.
5. **Next assignment:** after human review/approval of these product and shape recommendations, authorize Phase 6B for only the selected OpenWeather adapter, fixtures, cache behavior, and typed source status. Keep ECCC SWOB integration in its separate assignment.

OpenWeather is marked Yellow in RouteLens licensing notes. Recheck the active subscription's attribution, ODbL, and caching terms before release or broader use; no terms were changed or accepted as part of this validation.

## Unresolved questions

- What subscription/refresh tier is attached to the local account, and what are the remaining account-wide quotas and billing controls?
- Is One Call 4.0 an intentional active account entitlement, and are its terms acceptable for the datathon? The successful request establishes endpoint access at test time, not billing or licensing approval.
- Are 3-hour forecast steps sufficiently useful to the MVP, or should the human explicitly approve One Call 4.0's finer forecast and its separate product dependency?
- Which attribution wording/logo and ODbL obligations apply to the selected active subscription?

## Fixtures

- `fixtures/openweather/current_vancouver_phase6a.json` — live Current Weather response.
- `fixtures/openweather/forecast_vancouver_phase6a.json` — live 5 day / 3 hour Forecast response.
- `fixtures/openweather/onecall4_current_vancouver_phase6a.json` — live One Call 4.0 current response.
- `fixtures/openweather/onecall4_15min_vancouver_phase6a.json` — live first timeline page; pagination URL redacted.

## Assignment 6B adapter contract (implemented, pending human acceptance)

`backend/app/openweather.py` exposes `OpenWeatherClient.get_weather(latitude, longitude, evaluation_time=...)`. It returns separate `current` and `forecast` results, each with its own `WeatherSourceStatus`. Current evidence is a structured provider condition, not a station measurement. Timeline records retain explicit UTC target times and nullable fields; `pop` is represented as a percentage and is never converted to a precipitation amount or an observation.

The adapter calls only `GET /data/4.0/onecall/current` and `GET /data/4.0/onecall/timeline/15min` on `api.openweathermap.org`, with destination latitude/longitude, `units=metric`, and `appid`. It does not follow redirects or timeline pagination. Forecast evidence is windowed against the supplied UTC evaluation time for the next three hours. Coverage metadata reports returned bounds, expected 15-minute timestamps, gaps, duplicate/malformed record counts, and whether the expected timeline is continuous. A valid response with no intervals is distinguishable from a failed request through `success`, `available`, and coverage metadata.

Each product has its own 600-second cache keyed by product, metric units, response parameters, and coordinates rounded to four decimal places. Cached evidence retains the coordinates used for its original provider request; cache rounding does not claim meteorological precision. Current cache entries contain normalized typed evidence. Timeline cache entries contain only a validated and size-bounded response's weather fields, with provider pagination metadata omitted, so a fresh entry can be re-windowed for a new evaluation time. Replacement is validated and atomic; malformed responses do not replace prior valid entries. A failed refresh can return the last valid result with stale age and the refresh failure reason.

`OPENWEATHER_DAILY_REQUEST_LIMIT` defaults to 100 and accepts values from 1 through 100. A persistent UTC-day counter records each product request attempt before network I/O, uses an interprocess file lock and atomic mode-restricted state replacement, and fails closed on unreadable or corrupt state. This is application-level defense-in-depth only; it does not account for calls from other applications or API keys and is not permission to consume the account's separate 500-request allowance. The local state is stored under the ignored `backend/data/cache/openweather/` directory. The adapter also bounds HTTP timeouts and response bodies, sanitizes expected failures, and keeps credentials out of cache data and returned errors.

Assignment 6B used fixture-backed mocked tests only and made no live OpenWeather calls. It did not modify journey analysis or frontend behavior. Verification and the human review handoff are recorded in `PROJECT_STATE.md`.
