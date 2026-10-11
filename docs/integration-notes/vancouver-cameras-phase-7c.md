# Vancouver Cameras — Assignment 7C

**Status:** Implemented; pending human acceptance. Phase 7 remains in progress. This note records the backend destination selector and current-frame retrieval contract. It does not establish image reuse rights beyond the human developer's stated private, noncommercial MVP development posture.

## Runtime behavior

`backend/app/camera_images.py` reuses the validated 7B `CameraIntersection`, `CameraView`, and `VancouverCameraCatalogueStore` contracts. The API accepts a canonical `Location`, then applies the existing City of Vancouver boundary validator before loading or requesting any camera data. The selector orders valid, enriched intersections by WGS84 geodesic distance, breaks ties by stable intersection identity, and considers at most 12 candidates within 2,000 m. Those are conservative initial caps because the approved planning documents do not set a numeric camera radius. Each selection has a maximum of 24 upstream image requests. It selects the first intersection with at least one newly retrieved or fresh cached usable frame and returns all usable views from that intersection only. It keeps partial views and falls back to the next candidate when all views at a nearer candidate fail.

Image URLs must come from a validated 7B view and use HTTPS on `trafficcams.vancouver.ca`. The retriever checks DNS answers for public IP addresses, refuses redirects outside the same validated official host/scheme/port boundary, limits redirects to two, and sets 3-second connect, 8-second read, and 10-second total per-view timeouts. Four requests may run simultaneously. Responses must be HTTP 200, have a supported JPEG/PNG/WebP content type matching decoded bytes, stay below 5 MiB, and decode successfully within 160×120 to 8192×8192 and 40 million pixels. No arbitrary-URL or filesystem-path input is accepted.

Frames are written to `backend/data/cache/vancouver_cameras/current/`, which is covered by the existing Git ignore rule for runtime caches. Stable SHA-256-derived names hold one `.img` and one metadata JSON file per intersection/view; replacement uses atomic per-file rename. Metadata includes validated source URL, source/view identity, retrieval time, dimensions, MIME type, byte length, and payload digest. It has no source capture timestamp because the API does not parse text embedded inside image pixels. Cache TTL defaults to 300 seconds and can be configured by `CAMERA_IMAGE_CACHE_TTL_SECONDS` from 60 to 900 seconds. A failed refresh can return the last valid frame as explicitly stale for at most 900 seconds after retrieval; stale-only evidence is returned separately with `status: "stale"` and does not qualify a fresh selected intersection. Obsolete catalogue views and cache records older than the stale limit are pruned during selection. No background polling or timestamped archive is used.

The image endpoint serves a cached, decoded, catalogue-matched frame only. References are deterministic opaque tokens under `/api/cameras/images/{token}`; the endpoint revalidates the token against the current validated catalogue and image metadata. It responds with the actual image MIME type, `nosniff`, and `private, max-age=60, must-revalidate` headers. The destination-camera operation does not invoke ORS or change `POST /api/trips/analyze`.

## Backend API

`POST /api/cameras/nearest` accepts:

```json
{
  "destination": {
    "name": "Downtown Vancouver",
    "latitude": 49.2827,
    "longitude": -123.1207
  }
}
```

It returns a typed status (`available`, `stale`, or `unavailable`), selected intersection metadata and attribution, variable-length fresh `views`, separately labeled `stale_views`, and bounded per-view failure codes and attempt counts. Image bytes are available only through each returned `image_reference`.

## Bounded live observation

On 2026-10-11, one request used the existing fresh, complete 7B catalogue snapshot (219 intersections); no metadata refresh was needed. For the canonical downtown coordinate above, the nearest usable intersection was **Hornby St and Robson St**, approximately **79.6 m** from the destination. Four upstream requests were made. All four returned HTTP 200 JPEGs; the recorded payload sizes were 326,623; 324,574; 372,238; and 391,413 bytes. Each decoded to 800×464. The observed request count matched the four attempted views, so no redirect occurred. A manually viewed sample displayed the City/intersection overlay and a timestamp within the image; no source-provided HTTP capture timestamp was parsed, and no placeholder detector or OCR was added. The four sampled views were partial-live validation of this intersection only, not a survey of all catalogue URLs or a guarantee of future availability.

A repeat selection during the same fresh-cache window returned the same stable intersection and its four frames with no upstream requests. The ASGI backend API returned HTTP 200 with the same intersection; its image endpoint returned HTTP 200, `image/jpeg`, the stored 326,623-byte frame, and the configured private cache headers. Offline tests cover image decoding failures, non-image and error responses, timeout, bounds, redirect policy, stale handling, concurrent coalescing, nearest-first fallback, partial views, and API delivery. No live failure/timeout behavior was induced against the City source.

## Limits

- The 2 km radius and 12-candidate/24-request caps are initial implementation settings, not approved source guarantees.
- The City open-data description says images update about every 5 minutes; camera pages say about every 10–15 minutes. The 300-second local cache TTL is a reuse interval and does not establish source refresh cadence.
- The single live sample showed a rendered timestamp, but the pipeline deliberately leaves `source_capture_at` unknown. The sample did not verify update cadence, all image hosts beyond the already validated official host, or all source-side error codes.
- The sample did not contain an obvious placeholder image. No deterministic placeholder fingerprint was supported by observed evidence.
- Image rights and external AI processing permissions remain unresolved; no image is sent to an AI provider.
