# OpenWeather Integration Readiness

**Checked:** 2026-10-09
**Status:** Live current and forecast access verified; account subscription and exact quota remain unverified.

## Configuration and Requests

The ignored local `.env` defines `OPENWEATHER_API_KEY`. Its value was not displayed, logged, or copied into artifacts. Requests used Vancouver coordinates (`lat=49.2827`, `lon=-123.1207`) with `units=metric` and the key in the required `appid` parameter.

The first current-weather attempt returned HTTP 401 (`Invalid API key`). A later retry with the current `.env` value succeeded, as did the forecast request. The successful responses were captured at 2026-10-09 22:19:53 UTC:

| Endpoint | Result | Fixture |
|---|---|---|
| `GET /data/2.5/weather` | HTTP 200; response `cod=200` | `fixtures/openweather/current_vancouver.json` |
| `GET /data/2.5/forecast` | HTTP 200; response `cod=200` | `fixtures/openweather/forecast_vancouver.json` |

The initial 401 followed by successful requests means the earlier rejection was temporary or the configured key changed/activated between attempts; the cause cannot be determined without exposing or comparing secret values. Both documented endpoints are accessible with the current local configuration.

## Observed Responses

The current response contains `coord`, `weather[]`, `main`, `visibility`, `wind`, `clouds`, `dt`, `sys`, `timezone`, and location identifiers. In this capture, `main` included temperature (15.04 °C), feels-like temperature (14.17 °C), min/max, pressure, and humidity (60%). Wind speed/direction/gust, cloudiness, visibility, and Unix observation time were present. `rain` and `snow` objects were absent; no explicit current precipitation amount of zero was returned.

The forecast response contained 40 entries spanning 2026-10-10 00:00 UTC through 2026-10-14 21:00 UTC. All 39 intervals were exactly 10,800 seconds (3 hours). Every entry included `dt`, `dt_txt`, `main`, `weather[]`, `clouds`, `wind`, `visibility`, `pop`, and `sys`. `main` included temperature, feels-like, humidity, and `dew_point`. `pop` ranged from 0 to 1; 34 entries explicitly returned zero. Five entries included a positive `rain.3h` amount; no entry included a `snow` object. Missing rain/snow fields remain missing evidence and must not be converted to measured zero.

These real responses establish current and near-term fields, UTC timestamps, and forecast cadence for the tested account. The forecast offers useful departure-time context through roughly five days, at three-hour resolution. Current weather is a point observation; its `dt` should be preserved separately from retrieval time. The current response also supplies a timezone offset (`-25200` seconds in this capture); forecast timestamps are UTC.

## Integration Guidance and Remaining Limits

- Use the coordinate-based current endpoint and 5 day / 3 hour forecast endpoint for the MVP. This retains OpenWeather as the structured current/near-term source alongside SWOB measurements and camera visual evidence.
- OpenWeather's API care guidance recommends at most one request per 10 minutes per location because the model update frequency is not higher than 10 minutes. Use an initial cache TTL of at least 600 seconds per location and reuse identical request parameters.
- The public pricing page lists the Current Weather and 5 day / 3 hour products in free access, with 60 calls/minute and 1,000,000 calls/month. This account's subscription, remaining quota, and any aggregated account usage were not inspected. Provider limits apply at account level across keys/products.
- Preserve the source's UTC timestamps and timezone metadata. With metric units, temperatures are Celsius, wind is metres/second, precipitation is millimetres, and visibility is metres; convert wind at the normalization boundary if RouteLens needs km/h.
- Treat optional precipitation objects as absent when omitted. Preserve explicit `pop=0` separately from missing `pop`, and do not infer current precipitation from forecast data.
- The existing planning documents identify attribution and ODbL/provider-term obligations. Recheck the terms applicable to the actual subscription before integration/release; this assignment did not establish the account's plan.

No provider behavior materially conflicts with the approved RouteLens weather role. The remaining uncertainty is account plan/quota and applicable terms, not basic endpoint access or observed schemas.

## Evidence Sources

- [Current Weather API](https://openweathermap.org/api/current)
- [5 day / 3 hour Forecast API](https://openweathermap.org/api/forecast5)
- [API care recommendations and account limits](https://openweathermap.org/appid)
- [Self-service API pricing and product availability](https://openweathermap.org/price)
