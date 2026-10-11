# Assignment 6C — ECCC SWOB evidence

## Official source and observed request

- GeoMet OGC API items endpoint: `https://api.weather.gc.ca/collections/swob-realtime/items`.
- Response: GeoJSON `FeatureCollection`; features contain `id`, `geometry` as a GeoJSON Point in CRS84 longitude/latitude order, and `properties`.
- Request filters verified from official documentation and a live response: `f=json`, `bbox` in west/south/east/north order, RFC 3339 `datetime`, `sortby` on `date_tm-value`, `offset`, and `limit`. Official documentation supports `bbox`, time filters, offset/limit paging, property selection, and sorting. A live query with property projection returned HTTP 400, so implementation uses bounded full records and rejects oversized pages.
- A live query for `bbox=-123.30,49.15,-122.85,49.35`, `datetime=2026-10-10T00:00:00Z/..`, descending observation-time sort, and `limit=10` returned HTTP 500. The corrected RFC 3339 window query succeeded. This isolated error is not evidence of source unavailability.
- A bounded live sample for the Vancouver bbox, start time `2026-10-11T07:00:00Z/..`, descending `date_tm-value`, and `limit=20` reported 812 matching records and 20 returned records across two station identities, with repeated one-minute reports. A separate same-day query response included station WEST VANCOUVER AUT. Sampling confirms sparse station coverage; the initial bbox is not comprehensive Lower Mainland coverage.

## Observed fields normalized

- Station identity prefers `msc_id-value`, then `clim_id-value`, `wmo_synop_id-value`, and `tc_id-value`; the source identities are retained. Station name uses `stn_nam-value`.
- Observation time is `date_tm-value` and was returned as UTC RFC 3339 text. Retrieval time is recorded independently.
- Coordinates come from `geometry.coordinates` as `[longitude, latitude, optional elevation]`; no external station catalogue is required.
- `air_temp` + `air_temp-uom=°C`; `rel_hum` + `%`.
- `pcpn_amt_pst10mts` and `pcpn_amt_pst1hr` use mm and preserve 600-second and 3600-second intervals. Explicit zero is retained; null, absent, or negative-quality values remain unknown.
- `avg_wnd_spd_10m_pst10mts` uses km/h and `avg_wnd_dir_10m_pst10mts` uses degrees; both preserve their 10-minute reporting window.
- `snw_dpth` uses cm. The live sample showed `-1` with QA `-10`; it is treated as unavailable, not snow depth. Visibility was not present in the retained live sample and is not normalized.
- Negative `<field>-qa` values are treated as unavailable. Unknown units are not converted. The adapter does not infer current precipitation from accumulation.

## Fetch, grouping, and cache

- Each refresh queries a six-hour interval ending at the request start time, orders by `date_tm-value` ascending, and uses GeoMet `limit=500`/`offset` pages. `SWOB_BBOX` and `SWOB_CACHE_TTL_SECONDS` configure the initial region and 600-second default TTL. The refresh is capped at 12 pages, 6,000 records, 8 MiB per response, and 75 seconds. Page counts must remain consistent before a regional snapshot is accepted.
- Realtime features group by the prioritized native station ID; the latest valid timestamp wins. Same-timestamp duplicates are resolved by lexicographically greatest source observation ID. Readings are never field-merged.
- Cache TTL is 600 seconds. Cache identity hashes source, collection, bbox, lookback, and page size. Validated cache writes use an fsynced temporary file plus atomic replace. Expected refresh errors retain a valid old snapshot and expose source-cache staleness separately from each observation's age.
- Destination selection uses haversine metres, rejects future readings beyond five minutes and stations without valid embedded coordinates or useful measurements, labels observations older than 90 minutes stale, and returns at most three stations. A caller may provide preferred measurement names, which rank first; otherwise freshness ranks before proximity. After the first candidate, it favors complementary measurement types. It does not interpolate station readings to the destination.

## Licensing and fixture

ECCC observations use OGL-Canada attribution: “Contains information licensed under the Open Government Licence – Canada. Source: Environment and Climate Change Canada GeoMet/SWOB.” The sanitized live-derived fixture and its excerpt counts are documented in [`fixtures/eccc_swob/README.md`](../../fixtures/eccc_swob/README.md).

This assignment does not modify the journey response, frontend, OpenWeather adapter, or road-source integrations.
