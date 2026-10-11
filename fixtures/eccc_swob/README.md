# ECCC GeoMet SWOB fixture provenance

`swob_realtime_vancouver_observed.json` is a sanitized, live-derived excerpt from
the official `swob-realtime` GeoJSON collection. It contains the first 20
observations returned for bbox `-123.30,49.15,-122.85,49.35`, using
`datetime=2026-10-11T07:00:00Z/..`, `sortby=-date_tm-value`, and `limit=20`.
The GeoMet response timestamp was 2026-10-11 13:22:39Z and it reported 812
matched records; the fixture retains only those 20
records and their observed station IDs, coordinates, timestamps, and selected
measurement/value-unit/QA fields. Its collection counts are set to the excerpt
size for offline parser tests; it is not a complete regional snapshot.

The sample contains two station identities with repeated minute observations.
It records `air_temp` in °C, `rel_hum` in %, 10 m wind speed in km/h, 10 m wind
direction in degrees, and precipitation accumulation fields in mm. The live
sample returned explicit zero precipitation and a `snw_dpth` value of -1 cm
with QA -10; the adapter preserves zero accumulation and treats that negative
quality-coded snow value as unavailable. Feature URLs and station names are
public source metadata; no credentials or user data are present.

The source request and field interpretation were checked against the official
[GeoMet OGC API documentation](https://eccc-msc.github.io/open-data/msc-geomet/ogc_api_en/)
and the live [SWOB real-time collection](https://api.weather.gc.ca/collections/swob-realtime/items).
The official bbox order is west, south, east, north; the response geometry uses
GeoJSON coordinates in CRS84 longitude/latitude order.
