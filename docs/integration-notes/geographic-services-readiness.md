# Geographic Services Readiness — Assignment 0C

**Status:** Live access verified for this small readiness sample; human review pending. No application adapter or MapLibre rendering was implemented.

## MapTiler

Credential `MAPTILER_API_KEY` was found in the ignored local `.env`; its value was not displayed or saved. Authenticated requests to `GET https://api.maptiler.com/geocoding/{query}.json` succeeded for Downtown Vancouver, New Westminster Station, Metrotown, Richmond, and Vancouver City Hall. Requests used `country=ca`, `language=en`, `limit=5`, `autocomplete=true`, and a Vancouver-area `proximity`; refined searches added `bbox=-123.30,49.05,-122.65,49.35`, and POI/address type filters as applicable. A partial `New Westminster Sta` autocomplete query also returned the station. The API returned GeoJSON `FeatureCollection`s; selected features contain `place_name`, `place_type`, `center`, `geometry`, `properties`, and contextual administrative features. Point coordinates are `[longitude, latitude]`.

The results show why selection normalization must retain municipality/context and type information: a broad “Downtown Vancouver” query also surfaced Downtown Victoria and Downtown Eastside; a broad station query ranked the New Westminster municipality above the station; Metrotown ranked the mall above the station; and “Vancouver City Hall” without a full address initially returned a community garden. With a bounding box and more specific text, the intended features were available. The selected New Westminster Station result is spatially at the station but its POI tags/categories describe a post office, so POI metadata can still be imperfect. “Vancouver” text alone does not establish that a feature is inside the City of Vancouver. The observed result fields are sufficient to populate a candidate `Location`; final destination-boundary validation remains future work.

The MapTiler `streets-v4-dark` style request succeeded with style version 8 and 163 layers. Its referenced TileJSON, one Vancouver vector tile, all four sprite JSON resources, and valid glyph requests returned successfully. The style references `maptiler_planet_v4` vector tiles, sprites, and glyphs; dependent MapTiler resources require the configured key. The style structure uses a multi-sprite list and is structurally compatible with the current MapLibre style specification. This confirms resource access and style structure only; Phase 1 must verify actual browser rendering. The style's attribution credits MapTiler and OpenStreetMap. MapTiler documentation requires attribution; free-plan accounts also require the MapTiler logo, so the active plan's exact requirement should be confirmed before release. Sources: [MapTiler Geocoding API](https://docs.maptiler.com/cloud/api/geocoding/), [MapTiler Maps API](https://docs.maptiler.com/cloud/api/maps/), [MapTiler attribution guide](https://docs.maptiler.com/guides/map-design/attribution/add-attribution/), [MapLibre style specification](https://maplibre.org/maplibre-style-spec/).

## openrouteservice

Credential `OPENROUTESERVICE_API_KEY` was found in `.env`; its value was not displayed or saved. Three authenticated requests succeeded against `POST https://api.openrouteservice.org/v2/directions/driving-car/geojson`, using the `driving-car` profile, an Authorization header, and GeoJSON coordinates in `[longitude, latitude]` order from the selected MapTiler features. Requests set `units=m`, `instructions=false`, and `alternative_routes={"target_count":3,"share_factor":0.6,"weight_factor":1.4}`.

All three journeys returned three GeoJSON `LineString` features in a `FeatureCollection`, each with `properties.summary.distance` (metres), `duration` (seconds), and `way_points`; route geometry contained hundreds of coordinate pairs. Journey summaries were:

| Journey | Returned routes (distance / duration) |
|---|---|
| New Westminster Station → Downtown Vancouver | 21.40 km / 36.6 min; 22.03 km / 39.0 min; 21.46 km / 39.3 min |
| Metrotown → Vancouver City Hall | 11.66 km / 21.7 min; 11.62 km / 21.9 min; 11.63 km / 22.0 min |
| Richmond → Downtown Vancouver | 15.45 km / 28.6 min; 16.02 km / 29.5 min; 16.05 km / 29.7 min |

The alternatives are separate geometries, although the Metrotown alternatives have very similar distances and durations. No one-route result occurred in this sample, so fewer-than-requested behavior was not directly observed; do not assume three are always available. ORS documents a maximum of three alternative routes, and alternative-route requests have provider constraints, including a 100 km maximum route distance. Responses provide corridor geometry and summary metadata suitable for later `RouteCandidate`/`SelectedRoute` normalization; no turn-by-turn instructions were requested. The documented maximum supports the MVP's approximate one-to-three candidate expectation, subject to actual route availability. Source: [openrouteservice restrictions](https://openrouteservice.org/restrictions/) and [Directions API documentation](https://openrouteservice.org/dev/#/api-docs/directions).

## Configuration, usage, and evidence

The local configuration requires `MAPTILER_API_KEY` and `OPENROUTESERVICE_API_KEY`; `.env` is ignored by Git. No values are included in this note or fixtures. The small request sample produced no observed rate-limit response, but it does not establish either account's quota, remaining usage, or plan-specific terms. Check each account's current limits before production use. Preserve provider attribution and review the providers' applicable terms/licensing during release preparation; ORS route data is based on OpenStreetMap data and carries attribution obligations.

Actual sanitized response bodies are preserved in `fixtures/maptiler/` and `fixtures/openrouteservice/`. The MapTiler style fixture replaces credential-bearing URL values with `${MAPTILER_API_KEY}`; geocoding and ORS response bodies do not contain request credentials. Fixtures are observed API responses, not synthetic examples. No live service was used by fixture validation.
