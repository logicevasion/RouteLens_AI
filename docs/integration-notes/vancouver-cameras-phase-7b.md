# Vancouver Camera Catalogue — Phase 7B Evidence

**Status:** Assignment 7B implemented; pending human acceptance. This note records metadata and URL discovery only. It does not grant rights to retrieve, cache, display, proxy, or transmit camera image bytes. The separate image-rights uncertainty recorded in the [7A evidence](vancouver-cameras-phase-7a.md) remains in force.

## Source and pagination

The adapter uses the official City of Vancouver Explore API v2.1 endpoint:

`https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/web-cam-url-links/records`

The bounded live request used `limit=100`, offsets `0`, `100`, and `200`, and `order_by=mapid`. All three responses returned HTTP 200 and reported the same `total_count` of 219. Page sizes were 100, 100, and 19. No credentials were required or sent. The adapter checks page size against `total_count`, holds the total stable across pages, rejects repeated pages, and caps the feed at 10 pages and 1,000 rows. The current 219-row count is observed evidence, not a hardcoded expectation.

All 219 rows had `mapid`, `name`, `url`, and `geo_point_2d`; current row-level values contained 219 distinct map IDs, 219 distinct page URLs, and 219 distinct approximate points. The API response row has no `recordid` field. RouteLens therefore uses a stable SHA-256 fingerprint of the complete canonical source row as its source-record identifier.

The 7A aggregate query had reported 219 rows but 213 distinct map IDs. The complete live row scan in 7B found no repeated IDs, so that earlier aggregate discrepancy was not reproduced and does not establish six duplicate records. No duplicate semantics were observed in the current source snapshot. Synthetic regression cases cover future repeated IDs: rows with the same official page and exact approximate point merge deterministically while retaining map IDs, names, and source-row fingerprints; rows sharing an ID but differing by page or point remain separate and are marked as an ambiguous map-ID collision. Intersection IDs derive from the official page URL and approximate coordinates, never row order. Coordinates remain approximate catalogue locations.

## Page and directional-view contract

Raw HTML was inspected at representative official pages, including `cambie12.htm`, `cambie2East.htm`, and `mainKingsway7.htm`. The observed view structure is a `<div class="camera">` containing a `<p><strong>…</strong></p>` direction label and an `<img src="…">`. Relative `cameraimages/...` paths resolve against the official page URL. Absolute HTTPS image URLs are also accepted only on the verified host `trafficcams.vancouver.ca`. The page and image host relationship was verified from actual HTML; no image URL is inferred from a page slug or naming pattern.

The labels are preserved as source text and do not imply exact camera bearings or road-travel direction. Live examples included standard North/East/South/West labels and additional labels such as `South - Main St`, `South - Kingsway`, `West Approach`, `West Exit`, `Georgia St east`, and `Pender St east`. Main St and Kingsway exposes five slots, including two distinct South-labeled views. The final full live catalogue contained:

| Discovered slots per intersection | Intersections |
|---:|---:|
| 1 | 2 |
| 2 | 4 |
| 3 | 19 |
| 4 | 193 |
| 5 | 1 |

The live run inspected all 219 pages: 219 recognized, zero page failures, zero unrecognized structures, 844 directional slots, 844 discovered URLs, 844 HTTPS/host-validated URLs, and zero intersections without a discovered URL. Every URL host was `trafficcams.vancouver.ca`. These results mean URL metadata was present and structurally validated. No camera image bytes were requested, so image response, freshness, content type, dimensions, decoding, and current usability remain unverified and belong to 7C.

## Validation, cache, and limits

`backend/app/vancouver_cameras.py` provides Pydantic-owned intersection/view models, strict full-snapshot validation, deterministic reconciliation, HTML extraction, a reusable catalogue store, and a standalone CLI. Run from `backend/`:

```sh
.venv/bin/python -m app.vancouver_cameras
.venv/bin/python -m app.vancouver_cameras --refresh
```

The default cache is `data/cache/vancouver_cameras/catalogue.json` and is Git-ignored by the existing `data/cache/` rule. Cache TTL is 24 hours. The cache envelope records schema version 2 and the Explore query plus extractor identity. It is model- and URL-validated on read, atomically replaced only after complete metadata retrieval and typed catalogue validation, and retains the previous valid snapshot on refresh failure. On an unchanged intersection and unchanged official page URL, a failed page recheck may retain old discovered view metadata with `stale_previous_views`; identity or page-URL changes prevent carry-forward. Partial coverage remains available but is not reported as a healthy enrichment.

Bounds are 100 metadata rows per page, at most 10 pages/1,000 rows, 2 MiB per API response, 120 seconds for metadata acquisition, 512 KiB per HTML page, 12 seconds per request, four concurrent page requests by default, and 240 seconds for page inspection. Redirects and retries are disabled. At most 16 MiB is accepted for the cache. URL policy requires HTTPS, an exact allowlisted official host, no credentials or fragments, and bounded URL length. URLs are never used as filesystem paths. No new runtime dependency was introduced.

Offline fixtures are explicitly synthetic and based on the verified field/markup contracts. They cover duplicates, multiple and composite labels, relative and absolute paths, repeated views, unsupported structure, empty views, invalid/off-host URLs, pagination faults, stale fallback, cache compatibility, and refresh coalescing. Automated tests do not contact the City source.

**Rights boundary:** Metadata is attributed under Open Government Licence – Vancouver. Public visibility and successful URL validation do not establish permission to retrieve or redistribute camera frames. The human decision to defer further rights review for the private, noncommercial MVP remains documented; no claim of image-use authorization is made here.
