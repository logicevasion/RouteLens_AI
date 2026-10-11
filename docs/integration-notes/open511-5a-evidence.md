# DriveBC Open511 Assignment 5A Evidence

**Observed:** 2026-10-11 (UTC)
**Scope:** Provider contract, regional query, representative source structure, and implementation verification. This note is not a guarantee of current provider availability or a human acceptance record.

## Official source and terms

- Official DriveBC guide: <https://api.open511.gov.bc.ca/help>
- Events endpoint: <https://api.open511.gov.bc.ca/events>
- Discovery endpoint: <https://api.open511.gov.bc.ca/>
- API Terms of Use: <https://www2.gov.bc.ca/gov/content/data/policy-standards/data-policies/open-data/api-terms-of-use-for-ogl-information>
- Open Government Licence – British Columbia: <https://www2.gov.bc.ca/gov/content/data/policy-standards/data-policies/open-data/open-government-licence-bc>

The guide identifies this as DriveBC's Open511 implementation, with Open511 schema `v1`; the live JSON response reported `meta.version: "v1"`. HTTPS `GET /events` succeeded without a key, token, or authorization header. Documentation examples use the same public interface and do not request credentials. The API Terms of Use say clients must use the documented means, acknowledge the source under OGL-BC, and recognize that the provider may change access limits without notice.

The guide says the information is governed by OGL-BC. The licence requires source acknowledgement and, where possible, a licence link. The normalized event attribution is: “Contains information licensed under the Open Government Licence – British Columbia. Source: DriveBC Open511 (Government of British Columbia).”

## Query and pagination contract

The implementation sends `GET https://api.open511.gov.bc.ca/events` with `format=json`, `status=ACTIVE`, `bbox=west,south,east,north`, `limit=100`, and `offset=0` initially. It does not send event-type or severity filters. The official guide documents `limit`/`offset`, a maximum limit of 500, and event collection pagination metadata with `pagination.offset` and optional `pagination.next_url`. The response envelope is `meta`, `events`, and `pagination`; live metadata included no total result count.

The adapter follows a validated same-host `next_url`, verifies the returned offset and schema version, and checks event identities across pages. If a full page has no next link, it probes the following offset to verify whether another page exists. It bounds each request to 12 seconds, total refresh time to 60 seconds, page size to 500, pages to 50, records to 5,000, and an individual response to 8 MiB. The source exposes no snapshot token or total count in the sampled response, so records could shift while offset pagination is in progress; duplicate and offset checks reduce but cannot eliminate that provider-side consistency limitation.

## Regional coverage evidence

The official guide uses `-123.45,48.99,-122.45,49.49` as its Greater Vancouver bbox example. The same box contains representative origin points for Richmond, Burnaby, New Westminster, Surrey, and North Vancouver, as well as the Highway 1 approach through Langley represented in current source records. It is retained as a configurable provisional default, not a universal Lower Mainland boundary. An Abbotsford origin lies beyond the east edge and is not covered as a complete regional origin scope.

As an additional repository-grounded check, every coordinate in the accepted Richmond-to-downtown, Metrotown-to-downtown, and New Westminster Station-to-downtown ORS route fixtures was within the provisional bbox (0 outside coordinates across the three fixtures). These checks confirm those sampled corridors only; the municipality reference-point assessment covers the other named origins.

The guide describes bbox results as events that “fall within” the box. In the live sample, one returned Point at `[-122.3815195, 49.05770406]` lay about 6.8 km east of the configured east bound. The source does not explain this point-filter discrepancy. The implementation therefore treats bbox as provider query scope, preserves returned source geometry, and makes no assertion that every event representative point is strictly inside the requested bounds. The sample is not evidence that the box omits supported Metro Vancouver origins.

## Live response sample

The official regional request returned HTTP 200 with 40 ACTIVE records, one populated page at `limit=100`, offset `0`, and no reported `next_url` or total. The response contained:

- 40 `CONSTRUCTION` event types;
- 13 `MAJOR` and 27 `MINOR` severities;
- 10 GeoJSON `Point` and 30 `LineString` geometries;
- timezone-offset `created` and `updated` timestamps;
- `roads` entries with names, from/to text, direction, and state;
- structured `schedule.intervals`, event subtype arrays, and source event URLs.

All 40 records normalized; zero were skipped. This single live sample does not demonstrate that other event types, `UNKNOWN`, or absent severities are absent from the source. Ingestion has no event-type or severity filter, and offline tests retain unknown and missing severity plus future-scheduled ACTIVE records.

`fixtures/open511/regional_active_observed.json` is a small sanitized live-derived structural sample. Event identifiers and descriptions are sanitized; field names, nesting, value forms, event status/severity, geometry types, roads, schedule, timestamps, and attribution-relevant provenance follow the observed source structure. The LineString fixture retains two observed source positions as a compact geometry illustration and is not presented as the source event's complete geometry. Multi-page and unusual-value cases are synthetic offline tests.

## Cache and live verification

The configurable implementation default is 600 seconds (10 minutes). Query identity hashes endpoint, schema version, ACTIVE status, canonical bbox, page size, and JSON format. Cache writes use a same-directory temporary file and atomic replace; the previous validated snapshot is retained on refresh, validation, timeout, or cache-write failure. A fresh regional snapshot is reused for subsequent calls.

The implemented adapter completed one live refresh and a second immediate call reused the cache. The first call returned 40 received/normalized, zero skipped, page count 1, and a timezone-aware fetched timestamp. The second call reported `cache_hit=true`, the same fetched timestamp, and age 0 seconds. A separate bounded attempt to force multiple live pages with a smaller limit received HTTP 429; no retry was made. Live multi-page retrieval is therefore not verified in this run, although provider paging is documented and exercised with offline mocked responses.
