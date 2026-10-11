# Vancouver Camera Source and Rights Validation (Assignment 7A)

**Verified:** 2026-10-11

**Status:** Research completed — pending human review. No camera images were requested or retained.

## 1. Official sources and access

- [Web Cam (URL links) dataset](https://opendata.vancouver.ca/explore/dataset/web-cam-url-links/), dataset identifier `web-cam-url-links`.
- [City traffic camera website](https://trafficcams.vancouver.ca/).
- [City traffic camera information](https://vancouver.ca/streets-transportation/traffic-cameras-data-and-signal-reports.aspx).
- [Open Government Licence – Vancouver](https://opendata.vancouver.ca/pages/licence/) and [City Terms of Use](https://vancouver.ca/your-government/terms-of-use.aspx).

The current structured access path is the public Opendatasoft Explore API v2.1:

```text
GET https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/web-cam-url-links
GET https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets/web-cam-url-links/records?limit=100&offset=0
```

The API returned HTTP 200 JSON with no API key or authentication header in two bounded live requests. The dataset metadata response reported `records_count: 219`; the records response reported `total_count: 219`. The official [Explore API v2.1 documentation](https://help.opendatasoft.com/apis/ods-explore-v2/) describes `limit`/`offset` paging, a maximum page size of 100 for records, and `total_count`; a complete 219-record snapshot therefore fits in three pages (offsets 0, 100, 200). Full pagination was not run in 7A.

## 2. Observed catalogue contract

Live dataset metadata reported `dataset_id: web-cam-url-links`, dataset UID `da_vcq98a`, publisher City of Vancouver, Open Government Licence – Vancouver, 219 records, and these fields:

| Field | API type | Observed role |
|---|---|---|
| `mapid` | text | City camera/map identifier, e.g. `TCM200` |
| `name` | text | Intersection or camera-location label |
| `url` | text | Official camera-page URL |
| `geom` | geo_shape | Point feature; sample geometry is GeoJSON `[longitude, latitude]` |
| `geo_point_2d` | geo_point_2d | `{ "lon": number, "lat": number }` |
| `geo_local_area` | text | City local-area label |

One sampled record was `TCM200`, “Burrard St and W Pender St”, with `url` `https://trafficcams.vancouver.ca/burrardpender.htm` and point `(-123.117829, 49.286589)`. API field counts returned 219 populated `mapid`, `name`, and `url` values. A filtered query for records with a null `mapid` or `geo_point_2d` returned zero records. The sampled row was well-formed; geometry validity and malformed URL checks across the full catalogue were not run.

**Identity discrepancy requiring 7B validation:** the live aggregate returned 219 rows but `count(distinct mapid) = 213`. A grouped-ID query returned 213 groups, each with count 1, which does not reconcile with the aggregate. No row-level full-catalogue scan was made, so the exact six-row discrepancy is unresolved. Do not assume `mapid` is unique until a complete ordered snapshot validates it; retain and report collisions rather than merging records by name or coordinate.

The `url` points to a camera/intersection page, not a single directional image. The dataset description says it contains links to official publicly available webcams, mostly traffic cameras, and that the City does not control what those cameras display. A catalogue row is therefore a location/page link that may expose multiple view slots; it is not one JPEG. The portal says locations are updated “from time to time” as operational priorities allow and calls coordinates approximate. It specifically warns the camera may be at a different place within the intersection. Use these coordinates only as approximate intersection ranking points; they do not establish a camera mount, road-surface point, view direction, or coverage.

The dataset metadata showed data modified `2026-09-21T13:47:24Z` and metadata processed `2026-10-11T13:47:27.593Z`. These are catalogue processing times, not image times.

## 3. Observed intersection-page contract

Five official pages were inspected through the City camera index:

| Page | Views exposed in page text |
|---|---:|
| [Burrard St and W Pender St](https://trafficcams.vancouver.ca/burrardPender.htm) | 4 |
| [Cambie St and W 12th Ave](https://trafficcams.vancouver.ca/cambie12.htm) | 4 |
| [Cambie St and W 2nd Ave – East intersection](https://trafficcams.vancouver.ca/cambie2East.htm) | 4 |
| [Trans Canada Hwy and E 1st Ave](https://trafficcams.vancouver.ca/transcanada01.htm) | 4 |
| [Boundary Rd and E 49th Ave](https://trafficcams.vancouver.ca/boundary49.htm) | 4 |

Each inspected page has an intersection title, a link back to the camera map, an update-frequency notice, and four labeled image slots: **North**, **East**, **South**, and **West**. The labels are observed as given; their precise semantics (camera viewing direction versus approach/traffic direction) are not documented in the page text. These samples expose four slots each, not proof that four current image responses are usable. No sample with a visibly missing/broken view was established.

The browser-readable page representation exposes image elements/alt labels but not their source URLs. Whether the source URLs are in server-rendered attributes or are constructed/retrieved by JavaScript was not established. No image URL naming pattern should be inferred from page slugs. A capitalization variation was observed between the camera-index link `burrardPender.htm` and the sampled catalogue `url` `burrardpender.htm`; use the exact catalogue URL and validate it without normalization.

## 4. Observed image contract and timing

The traffic-camera index and sampled pages state that displayed images update approximately every **10–15 minutes**. The open-data dataset description instead says webcam images update approximately every **5 minutes**. These are published estimates and differ; neither guarantees a newly retrieved frame is current. The page text provides no per-view capture timestamp.

No image response was requested because image-use rights are not established for RouteLens retrieval. Consequently, image status, redirect chain, final image host, content type, length, dimensions, image decoding, cache headers, repeated-byte behavior, placeholders, and actual available-view counts remain **untested**. The only verified page host is `trafficcams.vancouver.ca`; the image-serving host is unknown. Do not configure an image-host allowlist from page hostname assumptions.

## 5. Licensing and rights matrix

### Catalogue metadata

The dataset identifies the **Open Government Licence – Vancouver**. It grants a worldwide, royalty-free, perpetual, non-exclusive right to copy, modify, publish, adapt, distribute, or otherwise use covered Information for lawful purposes, including commercial use, subject to conditions. Attribute the source and link the licence where possible. Suggested fallback: “Contains information licensed under the Open Government Licence – Vancouver.” The licence excludes third-party rights the City is not authorized to license and official marks. The City portal also warns that data accuracy, completeness, and refresh frequency vary by dataset. The metadata may be cached and enriched with provenance under these terms; this does not extend the licence to separate image files.

### Camera-image actions

The [City Terms of Use](https://vancouver.ca/your-government/terms-of-use.aspx) grant a limited right to view, store, download, and use website content for personal, informational, non-commercial use (or with separate written authorization). They otherwise restrict copying, transmitting, displaying, reproducing, distributing, or redelivering site images through framing or other technology. They also prohibit repeated automated access where it could damage or overburden City systems. The camera-page footer links to these City terms. No image-specific open licence was found.

| Proposed action | Evidence status for RouteLens | Basis / limit |
|---|---|---|
| View images on the official City page | **Expressly permitted**, within the stated personal, informational, non-commercial scope | City Terms grant page viewing on a computer. This does not clear RouteLens embedding or onward use. |
| Programmatically download current bytes | **Not established / requires clarification** | The terms permit downloads only within their limited use grant and restrict copying/transmission; they do not clearly authorize RouteLens automated product retrieval. |
| Temporarily cache current frames | **Not established / requires clarification** | “Ephemeral” does not create permission. No image-cache grant or retention exception was found. |
| Proxy or serve image bytes from RouteLens | **Expressly restricted absent written authorization** | Terms restrict copying/transmitting and redelivering images using framing or other technology. |
| Embed/display images in the RouteLens frontend | **Not established / requires clarification** | Official-page viewing is allowed in a limited context; reuse/display within another application is not clearly granted and may be redelivery. |
| Send image content to a third-party vision provider | **Not established / requires clarification** | No AI-processing permission was found. Terms broadly restrict transmission/transfer; the OGL metadata licence does not cover the image. |
| Retain derived visual observations | **Not established / requires clarification** | Image-derived facts may raise different questions from image copying; the terms do not address RouteLens-derived observations. Obtain clarification for the intended product use. |
| Public demonstration or commercial redistribution of image bytes | **Expressly restricted absent written authorization** | The terms limit use to personal/informational/non-commercial purposes and restrict display, reproduction, distribution, and exploitation. |

This is a source-terms assessment, not a legal opinion. The conservative route is to request written City clarification covering automated acquisition, temporary cache, app display/proxy, derived observations, and any later third-party AI transfer. Until then, keep image functionality disabled. An official deep link may be shown only in a context consistent with the City's linking conditions; it does not authorize copying the image into RouteLens. Properly licensed or developer-owned imagery can support technical tests.

## 6. Recommended 7B catalogue/enrichment design

- Fetch the public API metadata and paged records using `limit`/`offset`; use returned `total_count`, expected page lengths, and a deterministic order. The 219-record size fits three requests at the documented maximum page size.
- Validate the full replacement before activation: required strings, finite WGS84 coordinates, valid official page URLs, stable ID collision checks, and record count against `total_count`. Keep every collision visible for review; do not merge by label or approximate point.
- Retain a source-scoped `mapid`, original name, approximate lon/lat, exact official page URL, `geo_local_area`, source/licence attribution, API data/metadata modification times, catalogue fetch time, enrichment check time, and per-view status.
- Model zero or more `directional_views`. Keep an unknown label as `null`; do not infer compass meaning. A discovered URL is a candidate, not proof of current usability. Record per-page/per-view failures without discarding good siblings, and do not mark an incompletely enriched snapshot complete.
- Treat removed records as removed only after a complete validated source snapshot. Activate a complete candidate catalogue atomically and retain the last valid catalogue on refresh failure.
- A 24-hour catalogue refresh is a reasonable conservative starting policy for local reuse because the provider describes location updates as occasional, not continuous. It is not a provider guarantee and does not establish image freshness. The number of page requests, permitted pace, and recheck cadence need City terms/approval before an enrichment run.
- Keep enrichment as a standalone, explicit operation outside journey analysis. No production scraper is authorized by this research assignment.

## 7. Recommended 7C selection/retrieval architecture

After written rights clearance and image-host discovery, rank approximate intersections from the canonical Vancouver destination by metre distance, with deterministic ID tie-breaks. Test a strict nearest-first budget; select the first intersection with at least one valid current image, then retain every usable view from that intersection only. Do not favor a farther intersection for having more views. Keep catalogue age, enrichment-check time, retrieval time, and source capture time distinct; report capture time only if the provider explicitly supplies it.

Do not fetch an image, implement a generic URL proxy, or expose a caller-supplied URL endpoint. A future fetcher should accept only stored, validated view IDs and URLs discovered through approved City pages. No image hostname is currently verified, so a restrictive image-host allowlist cannot yet be specified.

## 8. Security and ephemeral retention

Once authorized, constrain page and image requests to HTTPS and an explicit verified host allowlist; revalidate every redirect and reject loopback, private, link-local, and metadata-service targets. Bound timeouts, redirects, response bytes, image dimensions, decoder work, concurrency, retries, and requests per analysis; respect rate-limit responses such as 429 and any `Retry-After` guidance. Validate image signatures and successful decode rather than trusting a URL suffix or content-type header. Treat HTML/error responses and corrupt/oversized images as unavailable. Keep credentials out of camera URLs/logs and never render upstream HTML in the frontend.

Keep only the latest allowed frame per verified intersection/view ID in a short-lived overwrite-in-place cache; no timestamped image history, thumbnails archive, or training set. Cache policy is subordinate to permission and does not reduce the need for it. On refresh failure retain the last valid catalogue and show its age; on image failure preserve other valid views from the chosen intersection. No current frame, image cache, or historical sample was created in 7A.

## 9. Open questions, blockers, and evidence limits

- The `mapid` distinct-count discrepancy is unresolved and must be resolved from a complete row-level API snapshot before it is used as a unique key.
- Five page samples showed four labeled slots apiece; no fewer-view or broken-view example was confirmed.
- Image source URLs, hostnames, formats, redirects, headers, sizes, dimensions, per-view timestamps, placeholders, and repeat-response behavior were not observed because image bytes were not requested.
- The page's image URL extraction mechanism (static HTML attributes versus JavaScript) is unverified. Official page text alone is insufficient to implement a reliable parser.
- Published update estimates conflict (dataset: about 5 minutes; camera site: about 10–15 minutes) and are not measured freshness guarantees.
- Image rights for automated download, app display, temporary cache, proxying, derived observations, and external AI processing remain unresolved. Current terms contain broad limits that prevent treating public visibility or ephemeral storage as permission.
- Catalogue coordinates are approximate, and record accuracy/completeness can vary. Nearest selection will mean nearest to the catalogue's approximate location only.

## 10. Human decision gate before 7B/7C

Before 7B, decide whether to obtain written City permission for the required page access and intended image use, or to authorize a metadata-only 7B with camera-image functions disabled pending rights. Approve how 7B must handle the `mapid` discrepancy (including whether to block activation on collisions) and the page-enrichment request budget/pace. Before 7C, require verified image URL/host evidence, an approved host allowlist, and a clear decision on current-byte retrieval, cache, RouteLens display/proxy, and attribution. Phase 8 separately requires explicit permission for third-party vision processing and any derived-observation retention.

## Verification summary

- **Live-confirmed:** Two bounded official API requests returned HTTP 200 JSON; one additional filtered metadata request returned a sample record; aggregate metadata queries reported counts and the unresolved identity discrepancy. Five official intersection pages were inspected through the City camera index. No camera image bytes were fetched.
- **Officially documented:** Opendatasoft API v2.1 paging; OGL-Vancouver rights/attribution; City terms; approximate camera-location limitation; published catalogue and camera image update estimates.
- **Passed:** Fixture JSON syntax and provenance review; `git diff --check`; changed-file and credential/restricted-content hygiene review.
- **Not run:** Full 219-record pagination or row-level duplicate scan; image response checks; HTML-source/JavaScript inspection; fixtures beyond the one licensed metadata record; application tests/build/browser checks (documentation-only research).
- **Rights requiring clarification:** Automated image retrieval, cache, app display/proxy, third-party vision transmission, and derived observations.

## Evidence fixture

`fixtures/vancouver_cameras/catalogue_metadata_sample.json` contains one minimal OGL-Vancouver metadata record and retrieval provenance. No HTML or image fixtures were copied because the applicable City terms did not clearly authorize retaining them for this application.
